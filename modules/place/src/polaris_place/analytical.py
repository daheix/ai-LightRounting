"""解析法布局器主入口（polaris-place 子模块）。

迁移自 ``src/polaris/engine/analytical_placer.py`` 与
``src/polaris/engine/legalization.py`` 的 DREAMPlace 风格解析法布局算法，
适配 polaris-place 的 ``circuit dict`` 接口（与 polaris-core 一致），
仅依赖 numpy（R04: 不参与 GPU）。

## 模块拆分（R11 质量门禁：单文件 ≤800 行）

本文件原 1480 行（最严重单文件技术债），已按功能拆分为:
- ``metrics.py``: HPWL/密度梯度/Tarjan SCC/拓扑深度
- ``legalize.py``: FFDH 合法化 + 1D 最近合法位置搜索 + 共享常量
- ``align.py``: 端口对齐后处理（_align_d2_global + _align_ports）
- ``residual.py``: 残余违规成对双向修复（_residual_pair_fix 已拆子函数）
- ``analytical.py``（本文件）: 主入口（FFDH 调度 + 配置 + Adam 优化器）

为保持向后兼容，所有内部函数（``_tarjan_scc`` 等）通过 ``from ... import``
重新绑定到本模块命名空间，``from polaris_place.analytical import X`` 仍可用。

## 算法核心（DREAMPlace, UT Austin DAC 2019 / TCAD 2020）

将布局问题转化为连续优化::

    1. 加权平均初始布局（基于连接拓扑）
    2. for iter in range(max_iterations):
         a. 计算平滑 HPWL 梯度（log-sum-exp 近似 max/min）
         b. 计算密度惩罚梯度（高斯核/成对排斥力，避免重叠）
         c. Adam 优化器更新坐标
         d. 收敛判定
    3. FFDH 合法化（消除重叠，自适应行高）
    4. 中心坐标 → 左下角坐标 {name: {x, y, w, h}}

## 输出约定

与 ``modules/_c_abi/polaris_types.h`` 中 ``polaris_placement_t`` 一致：
``x, y`` 为器件**左下角**坐标（μm），``w, h`` 为宽高。HPWL 计算用中心坐标
``x + w/2, y + h/2``。

## 来源（R02 学术诚信）

- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020 (Lin et al.): https://arxiv.org/abs/2004.10746
- DREAMPlace 开源: https://github.com/limbo018/DREAMPlace
- log-sum-exp 平滑: Nesterov 2005 "Smooth minimization of non-smooth functions"
- log-sum-exp 数值稳定 trick: Blanchard et al. arXiv:2106.14588
  https://arxiv.org/abs/2106.14588
- Adam 优化器: Kingma & Ba 2014 https://arxiv.org/abs/1412.6980
- FFDH 合法化: Coffman et al. SIAM J. Comput. 9(4) 1980
  https://epubs.siam.org/doi/10.1137/0209062
- HPWL 指标: Kahng & Lienig "VLSI Placement" IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

# 从拆分后的子模块导入（保持 from polaris_place.analytical import X 兼容）
from polaris_place.metrics import (
    _compute_hpwl_pos,
    _condensation_dag,
    _density_gradient,
    _smooth_hpwl_gradient,
    _tarjan_scc,
    _topological_depth,
)
from polaris_place.legalize import (
    _ALIGN_MIN_SPACING,
    _ALIGN_PORT_TOL_UM,
    _find_nearest_legal_pos_1d,
    _legalize,
)
from polaris_place.align import (
    _align_d2_global,
    _align_ports,
    _find_port_in_dev,
    _no_overlap_at,
)
from polaris_place.residual import _residual_pair_fix

logger = logging.getLogger(__name__)

__all__ = ["AnalyticalConfig", "place_analytical"]


@dataclass
class AnalyticalConfig:
    """解析法布局器配置（参数来源 DREAMPlace TCAD 2020 默认值）。

    Attributes:
        gamma: log-sum-exp 平滑系数（越小越接近真实 HPWL，越大越平滑）。
            来源: DREAMPlace 默认 gamma=4.0（TCAD 2020）。
        density_weight: 密度惩罚权重（越大越强制无重叠）。
            来源: DREAMPlace 默认 density_weight=1.0e-3（TCAD 2020）。
        learning_rate: Adam 优化器学习率。
            来源: DREAMPlace 默认 lr=0.01（TCAD 2020）。
        max_iterations: 最大迭代次数。
            来源: PoLaRIS 默认 200 迭代（DREAMPlace 参考值 1000，
            Lin et al., TCAD 2020, https://arxiv.org/abs/1904.11520）。
        density_bandwidth: 密度场带宽（μm），距离 < bandwidth 的器件对施加排斥力。
            来源: DREAMPlace 默认 = 平均器件尺寸量级。
        convergence_threshold: 收敛阈值（HPWL 变化 < 阈值则提前停止）。
        seed: 随机种子（DREAMPlace 可复现性约定，torch.manual_seed 对齐）。
    """

    gamma: float = 4.0
    density_weight: float = 1.0e-3
    learning_rate: float = 0.01
    max_iterations: int = 200
    density_bandwidth: float = 10.0
    convergence_threshold: float = 1.0
    seed: int = 42


def _parse_circuit(circuit: dict) -> tuple:
    """解析 circuit dict 为布局器内部数组表示。

    Args:
        circuit: polaris-core 风格 circuit dict。

    Returns:
        ``(names, widths, heights, connections, canvas_w, canvas_h)``。
        connections 为索引化 ``[(src_idx, dst_idx), ...]``。

    Raises:
        RuntimeError: circuit 结构不完整（R03 禁止 fall-back）。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    for key in ("name", "devices", "connections", "canvas_w", "canvas_h"):
        if key not in circuit:
            raise RuntimeError(f"circuit 缺少必要字段: {key}")
    devices = circuit["devices"]
    names = [d["name"] for d in devices]
    widths = np.array([float(d["width_um"]) for d in devices], dtype=np.float64)
    heights = np.array([float(d["height_um"]) for d in devices], dtype=np.float64)
    name_to_idx = {nm: i for i, nm in enumerate(names)}
    connections: list[tuple[int, int]] = []
    for conn in circuit["connections"]:
        d1, _p1, d2, _p2 = conn
        if d1 in name_to_idx and d2 in name_to_idx:
            connections.append((name_to_idx[d1], name_to_idx[d2]))
    canvas_w = float(circuit["canvas_w"])
    canvas_h = float(circuit["canvas_h"])
    if canvas_w <= 0 or canvas_h <= 0:
        raise RuntimeError(
            f"画布尺寸必须为正: canvas_w={canvas_w}, canvas_h={canvas_h}"
            f"（R03 禁止 fall-back）"
        )
    return names, widths, heights, connections, canvas_w, canvas_h


def _initial_placement(
    n: int,
    connections: list[tuple[int, int]],
    canvas_w: float,
    canvas_h: float,
    seed: int,
) -> np.ndarray:
    """加权平均初始布局（DREAMPlace TCAD 2020 §III-A）。

    每个器件初始位置 = 连接对端的加权平均 + 画布中心偏移；无连接的器件放
    画布中心。使用固定种子 RNG 保证可复现（DREAMPlace torch.manual_seed 约定）。

    Args:
        n: 器件数。
        connections: 索引化连接列表。
        canvas_w: 画布宽。
        canvas_h: 画布高。
        seed: 随机种子。

    Returns:
        初始坐标 ``(n, 2)``，列 0=x，列 1=y（中心坐标）。
    """
    pos = np.zeros((n, 2), dtype=np.float64)
    cx, cy = canvas_w / 2.0, canvas_h / 2.0
    neighbor_cnt = np.zeros(n, dtype=np.float64)
    for src, dst in connections:
        neighbor_cnt[src] += 1
        neighbor_cnt[dst] += 1
    rng = np.random.default_rng(seed)
    for i in range(n):
        if neighbor_cnt[i] == 0:
            pos[i] = [cx, cy]
        else:
            # 固定种子扰动，避免全重合
            pos[i] = [cx + rng.uniform(-10, 10), cy + rng.uniform(-10, 10)]
    # 迭代加权平均（3 轮收敛）
    for _ in range(3):
        new_pos = pos.copy()
        for src, dst in connections:
            new_pos[src] += pos[dst]
            new_pos[dst] += pos[src]
        for i in range(n):
            if neighbor_cnt[i] > 0:
                new_pos[i] /= neighbor_cnt[i] + 1.0
        pos = new_pos
    pos[:, 0] = np.clip(pos[:, 0], 0.0, canvas_w)
    pos[:, 1] = np.clip(pos[:, 1], 0.0, canvas_h)
    return pos


def _adam_step(
    pos: np.ndarray,
    grad: np.ndarray,
    m: np.ndarray,
    v: np.ndarray,
    t: int,
    lr: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Adam 优化器一步更新（Kingma & Ba 2014）。

    Args:
        pos: 当前坐标。
        grad: 梯度（最小化方向，已含正负号）。
        m: 一阶矩。
        v: 二阶矩。
        t: 时间步。
        lr: 学习率。

    Returns:
        ``(new_pos, new_m, new_v)``。
    """
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    new_m = beta1 * m + (1 - beta1) * grad
    new_v = beta2 * v + (1 - beta2) * grad * grad
    m_hat = new_m / (1 - beta1**t)
    v_hat = new_v / (1 - beta2**t)
    new_pos = pos - lr * m_hat / (np.sqrt(v_hat) + eps)
    return new_pos, new_m, new_v


def place_analytical(
    circuit: dict,
    config: AnalyticalConfig | None = None,
) -> dict[str, dict[str, float]]:
    """执行解析法布局（DREAMPlace warm-start + FFDH 合法化 + 端口对齐）。

    流程: 初始布局 → 梯度下降（平滑 HPWL + 密度惩罚 + Adam）→ FFDH 合法化
    → 中心坐标转左下角坐标 → 端口对齐后处理（*创新*）。

    Args:
        circuit: polaris-core 风格 circuit dict。
        config: 布局器配置（None 用默认）。

    Returns:
        布局字典 ``{name: {x, y, w, h}}``，``x, y`` 为左下角坐标（μm），
        ``w, h`` 为器件宽高。保证无重叠且在画布内。

    Raises:
        RuntimeError: circuit 结构非法或优化发散（R03 禁止 fall-back）。
    """
    cfg = config or AnalyticalConfig()
    names, widths, heights, connections, canvas_w, canvas_h = _parse_circuit(circuit)
    n = len(names)
    if n == 0:
        return {}

    # 1. 初始布局
    pos = _initial_placement(n, connections, canvas_w, canvas_h, cfg.seed)
    m = np.zeros_like(pos)
    v = np.zeros_like(pos)
    prev_hpwl = float("inf")

    # 2. 梯度下降主循环
    for t in range(1, cfg.max_iterations + 1):
        hpwl_grad = _smooth_hpwl_gradient(pos, connections, cfg.gamma)
        dens_grad = _density_gradient(pos, n, cfg.density_bandwidth)
        total_grad = hpwl_grad + cfg.density_weight * dens_grad
        pos, m, v = _adam_step(pos, total_grad, m, v, t, cfg.learning_rate)
        pos[:, 0] = np.clip(pos[:, 0], 0.0, canvas_w)
        pos[:, 1] = np.clip(pos[:, 1], 0.0, canvas_h)
        if t % 10 == 0:
            cur_hpwl = _compute_hpwl_pos(pos, connections)
            if abs(prev_hpwl - cur_hpwl) < cfg.convergence_threshold:
                break
            prev_hpwl = cur_hpwl

    # 3. FFDH 合法化（消除重叠 + 保证信号流方向 x 递增）
    centers = _legalize(pos, widths, heights, names, canvas_w, connections)

    # 4. 中心坐标 → 左下角坐标（与 polaris_placement_t 一致）
    placements: dict[str, dict[str, float]] = {}
    for i, nm in enumerate(names):
        cx, cy = centers[nm]
        w = float(widths[i])
        h = float(heights[i])
        x = cx - w / 2.0
        y = cy - h / 2.0
        # 边界裁剪（保证在画布内）
        x = max(0.0, min(x, canvas_w - w))
        y = max(0.0, min(y, canvas_h - h))
        placements[nm] = {"x": x, "y": y, "w": w, "h": h}

    # 5. 端口对齐后处理（*创新*，减少 PORT_ALIGNMENT DRC 违规）
    # FFDH 只保证无重叠和拓扑序，不考虑端口对齐；本步骤对每个连接调整
    # 下游器件位置使端口对齐，重叠冲突时保持原位置（不破坏 FFDH 保证）
    placements = _align_ports(placements, circuit, canvas_w, canvas_h)
    return placements
