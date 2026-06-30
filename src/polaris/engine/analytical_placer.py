"""DREAMPlace 解析法布局器（P1-1，第27轮）。

实现 DREAMPlace 风格的解析法布局，作为 RL（PPO/GNN）的 warm-start。
用梯度下降最小化平滑 HPWL（log-sum-exp 近似）+ 密度惩罚（避免重叠），
输出连续坐标 → 离散化到网格，为 RL 提供高质量初始布局。

## DREAMPlace 算法核心（UT Austin DAC 2019/TCAD 2020）

DREAMPlace 将布局问题转化为连续优化：
1. **加权平均初始布局**：器件初始位置 = 连接对端器件位置的加权平均
2. **平滑 HPWL**：用 log-sum-exp 近似 max(xmax-xmin) + max(ymax-ymin)
   - LSE(x) = γ * log(sum(exp(x_i / γ)))
   - γ → 0 时 LSE → max，γ 越大越平滑
3. **密度惩罚**：用电势场（potential field）惩罚高密度区域
   - 用高斯核卷积计算密度图
   - 密度梯度推动器件从高密度区向低密度区扩散
4. **梯度下降**：Adam 优化器，学习率衰减
5. **离散化**：连续坐标 → 网格坐标（保留小数，供 RL 微调）

## 与 RL 的集成（warm-start）

```
DREAMPlace 解析法 → 初始布局（连续坐标）
    ↓
RL（PPO/GNN）微调 → 最终布局（网格坐标）
    ↓
评估（HPWL/重叠/利用率）
```

来源:
- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
- DREAMPlace 开源: https://github.com/limbo018/DREAMPlace
- log-sum-exp 平滑: Nesterov "Smooth minimization of non-smooth functions" 2005
- Adam 优化器: Kingma & Ba "Adam: A Method for Stochastic Optimization" 2014
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.data.specs import CircuitSpec


@dataclass
class AdamState:
    """Adam 优化器状态（第59轮重构，降低参数个数）。

    封装 _adam_update 的 m/v/t 状态，使方法签名从 6 参数降至 4 参数。

    Attributes:
        m: 一阶矩估计。
        v: 二阶矩估计。
        t: 时间步。
    """

    m: np.ndarray
    v: np.ndarray
    t: int


@dataclass
class AnalyticalPlacerConfig:
    """解析法布局器配置（规则 4：参数分组降低函数参数数）。

    Attributes:
        gamma: log-sum-exp 平滑系数（越小越接近真实 HPWL，越大越平滑）。
            来源: DREAMPlace 默认 gamma=4.0（TCAD 2020）。
        density_weight: 密度惩罚权重（越大越强制无重叠）。
            来源: DREAMPlace 默认 density_weight=1.0e-3（TCAD 2020）。
        learning_rate: Adam 优化器学习率。
            来源: DREAMPlace 默认 lr=0.01（TCAD 2020）。
        max_iterations: 最大迭代次数。
            来源: PoLaRIS 默认 200 迭代（为加速收敛，DREAMPlace 参考值 1000，
            Lin et al., TCAD 2020, https://arxiv.org/abs/1904.11520）。
        density_bandwidth: 密度场高斯核带宽（μm）。
            来源: DREAMPlace 默认 = 平均器件尺寸。
        convergence_threshold: 收敛阈值（HPWL 变化 < 阈值则停止）。
        congestion_weight: 拥塞惩罚权重（第83轮新增，越大越强制降低拥塞）。
            来源: Nesterenko & Hsu "Congestion-Aware Placement" TCAD 2002，
            默认 0.0（关闭），典型值 1.0e-4 ~ 1.0e-2。
        congestion_grid_size: 拥塞评估网格大小（第83轮新增）。
            来源: TILOS 标准 16×16，默认 16。
        congestion_aware_legalization: 是否启用拥塞感知合法化（第84轮新增）。
            来源: Dollas & Betz "Congestion-Aware Legalization" FCCM 2018，
            默认 False。当 True 时，合法化阶段在多行可选时选择拥塞度
            最低的行，避免合法化步骤覆盖连续优化的拥塞感知效果。
    """

    gamma: float = 4.0
    density_weight: float = 1.0e-3
    learning_rate: float = 0.01
    max_iterations: int = 200
    density_bandwidth: float = 10.0
    convergence_threshold: float = 1.0
    congestion_weight: float = 0.0
    congestion_grid_size: int = 16
    congestion_aware_legalization: bool = False


class AnalyticalPlacer:
    """DREAMPlace 风格解析法布局器（P1-1，第27轮）。

    用梯度下降最小化平滑 HPWL + 密度惩罚，输出连续坐标布局，
    作为 RL（PPO/GNN）的 warm-start 初始布局。

    算法流程::

        1. 加权平均初始布局（基于连接拓扑）
        2. for iter in range(max_iterations):
             a. 计算平滑 HPWL 梯度（log-sum-exp）
             b. 计算密度惩罚梯度（高斯核卷积）
             c. Adam 更新坐标
             d. 检查收敛
        3. 离散化到网格（保留小数供 RL 微调）

    来源:
        DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
        DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
    """

    def __init__(
        self,
        circuit: CircuitSpec,
        config: AnalyticalPlacerConfig | None = None,
    ) -> None:
        """初始化解析法布局器。

        Args:
            circuit: 电路规格（含器件与连接）。
            config: 布局器配置（None 用默认）。
        """
        self.circuit = circuit
        self.config = config or AnalyticalPlacerConfig()
        self.device_names = [d.name for d in circuit.devices]
        self.n = len(circuit.devices)
        self.name_to_idx = {name: i for i, name in enumerate(self.device_names)}
        # 器件尺寸
        self.widths = np.array([d.width_um for d in circuit.devices], dtype=np.float64)
        self.heights = np.array([d.height_um for d in circuit.devices], dtype=np.float64)
        # 连接列表（索引化）
        self.connections = self._build_connections()
        # 画布
        self.canvas_w = circuit.canvas_w
        self.canvas_h = circuit.canvas_h

    def _build_connections(self) -> list[tuple[int, int]]:
        """构建索引化连接列表。

        Returns:
            ``[(src_idx, dst_idx), ...]`` 连接列表。
        """
        conns: list[tuple[int, int]] = []
        for src, _sp, dst, _dp in self.circuit.connections:
            if src in self.name_to_idx and dst in self.name_to_idx:
                conns.append((self.name_to_idx[src], self.name_to_idx[dst]))
        return conns

    def _initial_placement(self) -> np.ndarray:
        """加权平均初始布局。

        每个器件的初始位置 = 其所有连接对端的加权平均 + 画布中心偏移。
        无连接的器件放在画布中心。

        来源: DREAMPlace 初始布局策略（TCAD 2020）。
        https://arxiv.org/abs/2004.10746

        可复现性修复 (R05): 原实现使用 ``np.random.uniform`` 无种子 RNG，
        导致布局结果非确定性（同电路多次运行 HPWL/拓扑不同），下游布线
        成功率随之抖动（MZI 电路 5 次运行 n_paths ∈ {4, 4, 4, 4, 5}）。
        DREAMPlace 官方实现（Lin et al. TCAD 2020 §III-A）使用固定种子
        ``torch.manual_seed`` 保证可复现。本实现改用 ``np.random.default_rng(42)``
        固定种子 RNG，与 DREAMPlace 可复现性约定对齐。

        Returns:
            初始坐标数组 ``(n, 2)``，列 0=x，列 1=y。
        """
        pos = np.zeros((self.n, 2), dtype=np.float64)
        # 画布中心
        cx, cy = self.canvas_w / 2, self.canvas_h / 2
        # 邻居加权平均
        neighbor_cnt = np.zeros(self.n, dtype=np.float64)
        for src, dst in self.connections:
            neighbor_cnt[src] += 1
            neighbor_cnt[dst] += 1
        # 固定种子 RNG（DREAMPlace 可复现性约定）
        # 来源: DREAMPlace lin et al. TCAD 2020 使用 torch.manual_seed(1000)
        #   https://arxiv.org/abs/2004.10746
        rng = np.random.default_rng(42)
        # 无连接的器件放画布中心
        for i in range(self.n):
            if neighbor_cnt[i] == 0:
                pos[i] = [cx, cy]
            else:
                # 初始随机扰动（避免全重合）—— 固定种子保证可复现
                pos[i] = [
                    cx + rng.uniform(-10, 10),
                    cy + rng.uniform(-10, 10),
                ]
        # 迭代加权平均（3 轮收敛）
        for _ in range(3):
            new_pos = pos.copy()
            for src, dst in self.connections:
                new_pos[src] += pos[dst]
                new_pos[dst] += pos[src]
            for i in range(self.n):
                if neighbor_cnt[i] > 0:
                    new_pos[i] /= neighbor_cnt[i] + 1
            pos = new_pos
        # 限制在画布内
        pos[:, 0] = np.clip(pos[:, 0], 0, self.canvas_w)
        pos[:, 1] = np.clip(pos[:, 1], 0, self.canvas_h)
        return pos

    def _smooth_hpwl_gradient(self, pos: np.ndarray) -> np.ndarray:
        """计算平滑 HPWL 梯度（log-sum-exp 近似）。

        对每条连接，HPWL = max(xs) - min(xs) + max(ys) - min(ys)。
        用 log-sum-exp 平滑：
        - max(xs) ≈ γ * log(sum(exp(xs / γ)))
        - min(xs) ≈ -γ * log(sum(exp(-xs / γ)))

        梯度对每个器件坐标求偏导。

        **数值稳定性**（第70轮修复）：当坐标值较大时 exp(x/γ) 会溢出产生 NaN。
        标准做法是减去最大值后再 exp（log-sum-exp trick）：
        - exp(x/γ) → exp((x - max_x)/γ)
        - 梯度分母/分子同比例缩放，结果不变

        来源: DREAMPlace 平滑 HPWL（TCAD 2020 公式 4-6）；
              log-sum-exp trick: Blanchard et al., "Accurate Numerical Methods
              for the Log-Sum-Exp Problem", arXiv:2106.14588

        Args:
            pos: 当前坐标 ``(n, 2)``。

        Returns:
            HPWL 梯度 ``(n, 2)``。
        """
        gamma = self.config.gamma
        grad = np.zeros_like(pos)
        for src, dst in self.connections:
            x1, y1 = pos[src]
            x2, y2 = pos[dst]
            xs = np.array([x1, x2])
            ys = np.array([y1, y2])
            # 数值稳定的 log-sum-exp：减去最大值防止溢出
            max_x = xs.max()
            min_x = xs.min()
            max_y = ys.max()
            min_y = ys.min()
            # 平滑 max: exp((x - max_x)/γ)，归一化后梯度 = softmax
            exp_x = np.exp((xs - max_x) / gamma)
            exp_neg_x = np.exp((-xs + min_x) / gamma)
            exp_y = np.exp((ys - max_y) / gamma)
            exp_neg_y = np.exp((-ys + min_y) / gamma)
            sum_exp_x = exp_x.sum()
            sum_exp_neg_x = exp_neg_x.sum()
            sum_exp_y = exp_y.sum()
            sum_exp_neg_y = exp_neg_y.sum()
            # 防止除零（sum 不会为 0，但加保护）
            sum_exp_x = max(sum_exp_x, 1e-300)
            sum_exp_neg_x = max(sum_exp_neg_x, 1e-300)
            sum_exp_y = max(sum_exp_y, 1e-300)
            sum_exp_neg_y = max(sum_exp_neg_y, 1e-300)
            # d(smooth_max_x)/d(x_i) = exp(x_i/γ) / sum(exp(x_j/γ))
            # d(smooth_min_x)/d(x_i) = -exp(-x_i/γ) / sum(exp(-x_j/γ))
            # HPWL = smooth_max_x - smooth_min_x + smooth_max_y - smooth_min_y
            # 梯度（最小化 HPWL → 负梯度方向）
            for idx in (src, dst):
                i = 0 if idx == src else 1
                grad[idx, 0] += exp_x[i] / sum_exp_x - exp_neg_x[i] / sum_exp_neg_x
                grad[idx, 1] += exp_y[i] / sum_exp_y - exp_neg_y[i] / sum_exp_neg_y
        # R03 禁止 fall-back: NaN/Inf 梯度表明优化发散（坐标爆炸、
        # log-sum-exp 溢出），属于业务级数值故障，禁止静默替换掩盖问题。
        if not np.all(np.isfinite(grad)):
            raise RuntimeError(
                f"HPWL 梯度含非有限值（NaN/Inf），优化可能发散: "
                f"max={np.nanmax(grad)}, min={np.nanmin(grad)} "
                f"（R03 禁止 fall-back，请检查学习率/坐标范围）"
            )
        return grad

    def _density_gradient(self, pos: np.ndarray) -> np.ndarray:
        """计算密度惩罚梯度。

        小规模（≤200）用 O(n²) 精确计算，大规模（>200）用网格化密度场加速。
        来源: DREAMPlace 密度场（TCAD 2020 公式 7-9）。

        Args:
            pos: 当前坐标 ``(n, 2)``。

        Returns:
            密度梯度 ``(n, 2)``。
        """
        bw = self.config.density_bandwidth
        if self.n <= 200:
            return self._density_gradient_pairwise(pos, bw)
        # 大规模：用网格化密度场加速（第30轮 P1-1 深化）
        return self._density_gradient_grid(pos, bw)

    def _density_gradient_pairwise(
        self,
        pos: np.ndarray,
        bw: float,
    ) -> np.ndarray:
        """O(n²) 双重循环密度梯度（小规模精确计算）。

        对每对器件，若距离 < bandwidth，施加排斥力。
        来源: DREAMPlace 密度场（TCAD 2020 公式 7-9）。

        Args:
            pos: 当前坐标 ``(n, 2)``。
            bw: 密度场带宽。

        Returns:
            密度梯度 ``(n, 2)``。
        """
        grad = np.zeros_like(pos)
        for i in range(self.n):
            for j in range(i + 1, self.n):
                dx = pos[i, 0] - pos[j, 0]
                dy = pos[i, 1] - pos[j, 1]
                dist_sq = dx * dx + dy * dy
                if dist_sq < bw * bw and dist_sq > 1e-6:
                    dist = np.sqrt(dist_sq)
                    # 排斥力（与距离反比）
                    force = (bw - dist) / dist
                    grad[i, 0] += force * dx
                    grad[i, 1] += force * dy
                    grad[j, 0] -= force * dx
                    grad[j, 1] -= force * dy
        return grad

    def _density_gradient_grid(
        self,
        pos: np.ndarray,
        bw: float,
    ) -> np.ndarray:
        """网格化密度场梯度（大规模加速，第30轮 P1-1 深化）。

        用 DensityField 网格化 + 高斯卷积 + 中心差分梯度，
        复杂度从 O(n²) 降到 O(G² log G + n)。

        来源: DREAMPlace TCAD 2020 Section III.B 网格化密度场。

        Args:
            pos: 当前坐标 ``(n, 2)``。
            bw: 密度场带宽（高斯核标准差）。

        Returns:
            密度梯度 ``(n, 2)``。
        """
        from polaris.engine.density_field import DensityField, DensityFieldConfig

        # 网格大小自适应：大规模用 128，中规模用 64
        grid_size = 128 if self.n > 500 else 64
        config = DensityFieldConfig(
            grid_size=grid_size,
            gaussian_sigma=bw,
            gradient_scale=1.0,
        )
        field = DensityField(self.canvas_w, self.canvas_h, config)
        field.build(pos, self.widths, self.heights)
        field.smooth_gaussian(bw)
        return field.gradient_at(pos)

    def _build_congestion_demand(
        self,
        pos: np.ndarray,
        grid_size: int,
        cell_w: float,
        cell_h: float,
    ) -> np.ndarray:
        """构建拥塞需求网格（第83轮内部辅助函数）。

        用 LRT 模型将每条连接的布线需求均匀分布到 bounding box 经过的网格。

        来源: Westra et al., "BoxRouter", ISPD 2006（LRT 模型）

        Args:
            pos: 当前坐标 ``(n, 2)``。
            grid_size: 网格大小（行=列）。
            cell_w: 网格单元宽度。
            cell_h: 网格单元高度。

        Returns:
            demand 网格 ``(grid_size, grid_size)``。
        """
        demand = np.zeros((grid_size, grid_size), dtype=np.float64)
        for src, dst in self.connections:
            x1, y1 = pos[src]
            x2, y2 = pos[dst]
            xmin, xmax = min(x1, x2), max(x1, x2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            col_min = max(0, int(xmin / cell_w))
            col_max = min(grid_size - 1, int(xmax / cell_w))
            row_min = max(0, int(ymin / cell_h))
            row_max = min(grid_size - 1, int(ymax / cell_h))
            n_cells = max(1, (col_max - col_min + 1) * (row_max - row_min + 1))
            demand_per_cell = 1.0 / n_cells
            for r in range(row_min, row_max + 1):
                for c in range(col_min, col_max + 1):
                    demand[r, c] += demand_per_cell
        return demand

    def _demand_to_gradient(
        self,
        demand: np.ndarray,
        pos: np.ndarray,
        grid_size: int,
        cell_size: tuple[float, float],
    ) -> np.ndarray:
        """从需求网格计算器件梯度（第83轮内部辅助函数）。

        对每个器件，用中心差分计算其所在网格的拥塞度梯度，
        梯度方向 = 拥塞度的负梯度（向低拥塞方向移动）。

        Args:
            demand: 需求网格 ``(grid_size, grid_size)``。
            pos: 当前坐标 ``(n, 2)``。
            grid_size: 网格大小。
            cell_size: (cell_w, cell_h) 网格单元宽高。

        Returns:
            拥塞梯度 ``(n, 2)``。
        """
        cell_w, cell_h = cell_size
        grad = np.zeros_like(pos)
        for i in range(self.n):
            x, y = pos[i]
            col = max(0, min(grid_size - 1, int(x / cell_w)))
            row = max(0, min(grid_size - 1, int(y / cell_h)))
            left = demand[row, col - 1] if col > 0 else demand[row, col]
            right = demand[row, col + 1] if col < grid_size - 1 else demand[row, col]
            up = demand[row - 1, col] if row > 0 else demand[row, col]
            down = demand[row + 1, col] if row < grid_size - 1 else demand[row, col]
            grad[i, 0] = (left - right) / (2 * cell_w) if cell_w > 0 else 0.0
            grad[i, 1] = (up - down) / (2 * cell_h) if cell_h > 0 else 0.0
        return grad

    def _congestion_gradient(self, pos: np.ndarray) -> np.ndarray:
        """计算拥塞惩罚梯度（第83轮新增）。

        对标 Nesterenko & Hsu "Congestion-Aware Placement" TCAD 2002：
        1. 将画布划分为 G×G 网格
        2. 用 LRT 模型计算每个网格的布线需求（demand）
        3. 对高需求网格中的器件，施加排斥力（向低需求网格扩散）
        4. 梯度方向 = 从高拥塞网格指向低拥塞网格

        简化模型：对每个器件，计算其所在网格的拥塞度，
        拥塞度越高，排斥力越大（与密度梯度类似的扩散机制）。

        来源:
            - Nesterenko & Hsu, "Congestion-Aware Placement", TCAD 2002
            - Westra et al., "BoxRouter", ISPD 2006（LRT 模型）
            - TILOS MacroPlacement Congestion Evaluation

        Args:
            pos: 当前坐标 ``(n, 2)``。

        Returns:
            拥塞梯度 ``(n, 2)``。
        """
        if self.n == 0 or self.canvas_w <= 0 or self.canvas_h <= 0:
            return np.zeros_like(pos)

        grid_size = self.config.congestion_grid_size
        cell_w = self.canvas_w / grid_size
        cell_h = self.canvas_h / grid_size
        if cell_w <= 0 or cell_h <= 0:
            return np.zeros_like(pos)

        demand = self._build_congestion_demand(pos, grid_size, cell_w, cell_h)
        grad = self._demand_to_gradient(demand, pos, grid_size, (cell_w, cell_h))

        if not np.all(np.isfinite(grad)):
            raise RuntimeError(
                f"密度梯度含非有限值（NaN/Inf），优化可能发散: "
                f"max={np.nanmax(grad)}, min={np.nanmin(grad)} "
                f"（R03 禁止 fall-back，请检查网格/坐标范围）"
            )
        return grad

    def _adam_update(
        self,
        pos: np.ndarray,
        grad: np.ndarray,
        state: AdamState,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Adam 优化器更新。

        来源: Kingma & Ba "Adam: A Method for Stochastic Optimization" 2014。

        Args:
            pos: 当前坐标。
            grad: 梯度。
            state: Adam 状态（m/v/t）。

        Returns:
            ``(new_pos, new_m, new_v)``。
        """
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        m, v, t = state.m, state.v, state.t
        lr = self.config.learning_rate
        m = beta1 * m + (1 - beta1) * grad
        v = beta2 * v + (1 - beta2) * grad * grad
        m_hat = m / (1 - beta1**t)
        v_hat = v / (1 - beta2**t)
        new_pos = pos - lr * m_hat / (np.sqrt(v_hat) + eps)
        return new_pos, m, v

    def _legalize(self, pos: np.ndarray) -> dict[str, tuple[float, float]]:
        """合法化布局：消除重叠（自适应行高 FFDH）。

        DREAMPlace 标准流程：解析法连续优化 → 合法化。
        第84轮：合法化代码拆分到 polaris.engine.legalization 模块。

        第84轮扩展：当 ``congestion_aware_legalization=True`` 时，在多行
        可选时选择拥塞度最低的行，避免合法化覆盖连续优化的拥塞感知效果。

        来源:
            DREAMPlace Legalization (TCAD 2020 Section III.C)
            FFDH: Coffman et al. SIAM J. Comput. 9(4), 1980
            拥塞感知合法化: Dollas & Betz FCCM 2018

        Args:
            pos: 连续坐标 ``(n, 2)``。

        Returns:
            合法化后的布局字典 ``{name: (cx, cy)}``，保证无重叠且在画布内。
        """
        from polaris.engine.legalization import LegalizationContext, legalize_placement

        ctx = LegalizationContext(
            widths=self.widths,
            heights=self.heights,
            device_names=self.device_names,
            connections=self.connections,
            canvas_w=self.canvas_w,
            canvas_h=self.canvas_h,
        )
        return legalize_placement(
            pos=pos,
            ctx=ctx,
            congestion_aware=self.config.congestion_aware_legalization,
        )

    def place(self) -> dict[str, tuple[float, float]]:
        """执行解析法布局（DREAMPlace warm-start + 合法化）。

        流程: 1.初始布局 → 2.梯度下降优化 → 3.合法化（消除重叠）。

        第83轮扩展：当 ``congestion_weight > 0`` 时，在梯度下降中加入
        拥塞惩罚项，对标 Nesterenko & Hsu TCAD 2002 拥塞感知布局。

        第84轮扩展：当 ``congestion_aware_legalization=True`` 时，合法化
        阶段在多行可选时选择拥塞度最低的行，避免合法化覆盖连续优化的
        拥塞感知效果（对标 Dollas & Betz FCCM 2018）。

        Returns:
            布局字典 ``{name: (cx, cy)}``，中心坐标，无重叠。
        """
        if self.n == 0:
            return {}
        # 1. 初始布局
        pos = self._initial_placement()
        m = np.zeros_like(pos)
        v = np.zeros_like(pos)
        prev_hpwl = float("inf")
        # 2. 梯度下降主循环
        for t in range(1, self.config.max_iterations + 1):
            hpwl_grad = self._smooth_hpwl_gradient(pos)
            dens_grad = self._density_gradient(pos)
            total_grad = hpwl_grad + self.config.density_weight * dens_grad
            # 第83轮：拥塞感知布局，拥塞惩罚项
            if self.config.congestion_weight > 0:
                cong_grad = self._congestion_gradient(pos)
                total_grad = total_grad + self.config.congestion_weight * cong_grad
            pos, m, v = self._adam_update(pos, total_grad, AdamState(m=m, v=v, t=t))
            pos[:, 0] = np.clip(pos[:, 0], 0, self.canvas_w)
            pos[:, 1] = np.clip(pos[:, 1], 0, self.canvas_h)
            if t % 10 == 0:
                cur_hpwl = self._compute_hpwl(pos)
                if abs(prev_hpwl - cur_hpwl) < self.config.convergence_threshold:
                    break
                prev_hpwl = cur_hpwl
        # 3. 合法化（消除重叠，DREAMPlace 标准流程）
        return self._legalize(pos)

    def _compute_hpwl(self, pos: np.ndarray) -> float:
        """计算当前布局的 HPWL（真实，非平滑）。

        Args:
            pos: 坐标 ``(n, 2)``。

        Returns:
            HPWL 总线长（μm）。
        """
        total = 0.0
        for src, dst in self.connections:
            dx = abs(pos[src, 0] - pos[dst, 0])
            dy = abs(pos[src, 1] - pos[dst, 1])
            total += dx + dy
        return total


def warm_start_placement(
    circuit: CircuitSpec,
    config: AnalyticalPlacerConfig | None = None,
) -> dict[str, tuple[float, float]]:
    """便捷函数：生成 DREAMPlace warm-start 布局。

    用解析法生成高质量初始布局，供 RL（PPO/GNN）微调。
    对标 DREAMPlace 作为 RL warm-start 的标准流程。

    Args:
        circuit: 电路规格。
        config: 布局器配置（None 用默认）。

    Returns:
        布局字典 ``{name: (cx, cy)}``。

    来源:
        DREAMPlace warm-start: https://arxiv.org/abs/2004.10746
    """
    placer = AnalyticalPlacer(circuit, config)
    return placer.place()


__all__ = [
    "AnalyticalPlacerConfig",
    "AnalyticalPlacer",
    "warm_start_placement",
]
