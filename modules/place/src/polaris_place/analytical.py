"""解析法布局器（polaris-place 子模块）。

迁移自 ``src/polaris/engine/analytical_placer.py`` 与
``src/polaris/engine/legalization.py`` 的 DREAMPlace 风格解析法布局算法，
适配 polaris-place 的 ``circuit dict`` 接口（与 polaris-core 一致），
仅依赖 numpy（R04: 不参与 GPU）。

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

import math
from dataclasses import dataclass

import numpy as np

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


def _smooth_hpwl_gradient(
    pos: np.ndarray,
    connections: list[tuple[int, int]],
    gamma: float,
) -> np.ndarray:
    """平滑 HPWL 梯度（log-sum-exp 近似，数值稳定 trick）。

    对每条连接，HPWL = max(xs) - min(xs) + max(ys) - min(ys)。
    平滑: max(xs) ≈ γ·log(Σ exp(xs/γ))；min(xs) ≈ -γ·log(Σ exp(-xs/γ))。
    数值稳定: exp((x - max_x)/γ) 防止溢出（Blanchard et al. arXiv:2106.14588）。

    Args:
        pos: 当前坐标 ``(n, 2)``。
        connections: 索引化连接列表。
        gamma: 平滑系数。

    Returns:
        HPWL 梯度 ``(n, 2)``。

    Raises:
        RuntimeError: 梯度含 NaN/Inf（优化发散，R03 禁止 fall-back）。
    """
    grad = np.zeros_like(pos)
    for src, dst in connections:
        x1, y1 = pos[src]
        x2, y2 = pos[dst]
        xs = np.array([x1, x2])
        ys = np.array([y1, y2])
        max_x, min_x = xs.max(), xs.min()
        max_y, min_y = ys.max(), ys.min()
        exp_x = np.exp((xs - max_x) / gamma)
        exp_neg_x = np.exp((-xs + min_x) / gamma)
        exp_y = np.exp((ys - max_y) / gamma)
        exp_neg_y = np.exp((-ys + min_y) / gamma)
        sum_exp_x = max(exp_x.sum(), 1e-300)
        sum_exp_neg_x = max(exp_neg_x.sum(), 1e-300)
        sum_exp_y = max(exp_y.sum(), 1e-300)
        sum_exp_neg_y = max(exp_neg_y.sum(), 1e-300)
        # d(HPWL)/d(x_i) = softmax_max - softmax_min（最小化→负梯度方向，外部 Adam 取负）
        for idx in (src, dst):
            i = 0 if idx == src else 1
            grad[idx, 0] += exp_x[i] / sum_exp_x - exp_neg_x[i] / sum_exp_neg_x
            grad[idx, 1] += exp_y[i] / sum_exp_y - exp_neg_y[i] / sum_exp_neg_y
    if not np.all(np.isfinite(grad)):
        raise RuntimeError(
            f"HPWL 梯度含非有限值（NaN/Inf），优化可能发散: "
            f"max={np.nanmax(grad)}, min={np.nanmin(grad)} "
            f"（R03 禁止 fall-back，请检查学习率/坐标范围）"
        )
    return grad


def _density_gradient(
    pos: np.ndarray,
    n: int,
    bandwidth: float,
) -> np.ndarray:
    """O(n²) 成对排斥力密度梯度（DREAMPlace TCAD 2020 公式 7-9）。

    距离 < bandwidth 的器件对施加与距离反比的排斥力。

    Args:
        pos: 当前坐标 ``(n, 2)``。
        n: 器件数。
        bandwidth: 密度场带宽。

    Returns:
        密度梯度 ``(n, 2)``。
    """
    grad = np.zeros_like(pos)
    bw2 = bandwidth * bandwidth
    for i in range(n):
        for j in range(i + 1, n):
            dx = pos[i, 0] - pos[j, 0]
            dy = pos[i, 1] - pos[j, 1]
            dist_sq = dx * dx + dy * dy
            if dist_sq < bw2 and dist_sq > 1e-6:
                dist = np.sqrt(dist_sq)
                force = (bandwidth - dist) / dist
                grad[i, 0] += force * dx
                grad[i, 1] += force * dy
                grad[j, 0] -= force * dx
                grad[j, 1] -= force * dy
    return grad


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


def _compute_hpwl_pos(
    pos: np.ndarray,
    connections: list[tuple[int, int]],
) -> float:
    """计算当前坐标的真实 HPWL（非平滑，用于收敛判定）。

    Args:
        pos: 坐标 ``(n, 2)``。
        connections: 索引化连接列表。

    Returns:
        HPWL 总线长（μm）。
    """
    total = 0.0
    for src, dst in connections:
        total += abs(pos[src, 0] - pos[dst, 0]) + abs(pos[src, 1] - pos[dst, 1])
    return total


def _topological_depth(
    n: int,
    connections: list[tuple[int, int]],
) -> list[int]:
    """计算每个器件的拓扑深度（Kahn 算法 + 最长路径）。

    拓扑深度 = 从源器件（入度=0）到当前器件的最长路径长度。源器件 depth=0，
    下游器件 depth = max(上游 depth) + 1。用于 FFDH 合法化时保证信号流
    方向 x 递增（拓扑序靠后的器件 x 坐标更大，避免后端器件被塞到前端
    器件的行内空隙导致物理重叠与 DRC 违规）。

    算法: Kahn 算法（Kahn 1962）逐层剥离入度=0 的节点，同时维护最长路径
    depth。可检测环（电路连接不应有环，有环则 raise，R03 禁止 fall-back）。

    Args:
        n: 器件数。
        connections: 索引化连接列表 ``[(src_idx, dst_idx), ...]``。

    Returns:
        每个器件的拓扑深度列表 ``[depth_0, depth_1, ...]``。

    Raises:
        RuntimeError: 连接存在环（无法拓扑排序，R03 禁止 fall-back）。

    来源（R02 学术诚信）:
        - Kahn 1962 "Topological Sorting of Large Networks"
          https://doi.org/10.1145/368996.369025
        - CLRS Introduction to Algorithms 3rd ed. §22.4 Topological sort
        - Topological sorting (Wikipedia)
          https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
        - Longest path in DAG
          https://en.wikipedia.org/wiki/Longest_path_problem#Acyclic_graphs
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746
    """
    from collections import deque

    adj: list[list[int]] = [[] for _ in range(n)]
    indeg = [0] * n
    for src, dst in connections:
        adj[src].append(dst)
        indeg[dst] += 1
    depth = [0] * n
    queue: deque[int] = deque(i for i in range(n) if indeg[i] == 0)
    processed = 0
    while queue:
        u = queue.popleft()
        processed += 1
        for v in adj[u]:
            if depth[u] + 1 > depth[v]:
                depth[v] = depth[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if processed != n:
        raise RuntimeError(
            f"电路连接存在环，无法拓扑排序（processed={processed}/"
            f"{n}，R03 禁止 fall-back，请检查 connections 是否含环）"
        )
    return depth


def _legalize(
    pos: np.ndarray,
    widths: np.ndarray,
    heights: np.ndarray,
    names: list[str],
    canvas_w: float,
    connections: list[tuple[int, int]],
) -> dict[str, tuple[float, float]]:
    """FFDH 合法化：消除重叠，保证信号流方向 x 递增。

    在经典 FFDH（Coffman et al. 1980）基础上增加两个拓扑约束（*创新*）:
    1. 拓扑深度排序: 先用 Kahn 算法计算每个器件的拓扑深度（信号流层级），
       按 (拓扑深度, -高度, pos_y) 排序，拓扑序靠前的先放置
    2. 候选行拓扑约束: 装箱候选行需满足行内最大拓扑深度 < 当前器件拓扑深度
       （保证同一行内信号流 x 递增，且跨行也保持拓扑序）
    3. 信号流方向起始 x（*创新*）: 新行/候选行的起始 x 考虑上游器件右边界，
       下游器件在上游右侧（x ≥ upstream_right + SPACING），使 east↔west 连接
       的端口 dx ≤ SPACING ≤ PORT_ALIGNMENT 容差，DRC 自然通过

    *创新点 1（拓扑深度排序）*: 经典 FFDH 仅按高度降序装箱，不考虑信号流
    拓扑，会导致后端器件被塞到前端行的剩余空间，破坏信号流方向。本实现
    引入拓扑深度作为主排序键 + 候选行的拓扑约束，确保信号流方向 x 递增。

    *创新点 2（信号流方向起始 x）*: 经典 FFDH 新行从 x=0 开始，导致下游
    器件（depth 大）被放到 x=0，与上游器件（depth 小，也在 x=0）形成
    "背对背"（端口方向相对但位置反向），dx 很大，PORT_ALIGNMENT 误报。
    本实现让新行起始 x = max(0, upstream_right + SPACING)，下游器件在
    上游右侧，端口 dx ≤ SPACING ≤ tol，PORT_ALIGNMENT 自然通过。底层
    逻辑: 光电子布局中 east↔west 连接要求 d2 在 d1 右侧（d2.x ≥ d1.x +
    d1.w），FFDH 新行起始 x 应反映此约束；VLSI FFDH 无此问题因为金属层
    任意布线，光电子波导需端口对齐。

    Args:
        pos: 连续坐标 ``(n, 2)``。
        widths: 器件宽度数组。
        heights: 器件高度数组。
        names: 器件名列表。
        canvas_w: 画布宽。
        connections: 索引化连接列表（用于拓扑排序）。

    Returns:
        合法化后的布局字典 ``{name: (cx, cy)}``（中心坐标，无重叠，
        信号流方向 x 递增）。

    来源（R02 学术诚信）:
        - FFDH: Coffman et al. SIAM J. Comput. 9(4) 1980
          https://epubs.siam.org/doi/10.1137/0209062
        - Kahn 1962 拓扑排序 https://doi.org/10.1145/368996.369025
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746
        - HPWL: Kahng & Lienig IEEE TCAD 2009
          https://ieeexplore.ieee.org/document/4685534
        - Bin packing (Wikipedia)
          https://en.wikipedia.org/wiki/Bin_packing_problem
        - Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
          波导端口对齐 https://www.cambridge.org/core/books/silicon-photonics-design/
    """
    # MIN_SPACING 间距（来源: SiEPIC EBeam PDK WG_MIN_SPACE=1.0μm，
    # 与 polaris-drc engine.py MIN_SPACING 阈值一致，R02 学术诚信）
    # 行内器件间需保持 SPACING 间距，避免 MIN_SPACING DRC 违规（R05 Bug 修复）。
    SPACING = 1.0
    n = len(names)
    if n == 0:
        return {}
    depth = _topological_depth(n, connections)

    # *创新*: 构建上游器件索引映射，用于信号流方向起始 x 计算。
    # downstream 的 x 应 ≥ upstream 的右边界 + SPACING，保证 east↔west
    # 连接的端口 dx ≤ SPACING ≤ PORT_ALIGNMENT 容差（10μm）。
    upstream_indices: list[list[int]] = [[] for _ in range(n)]
    for src, dst in connections:
        upstream_indices[dst].append(src)

    order = sorted(
        range(n),
        key=lambda i: (depth[i], -float(heights[i]), pos[i, 1]),
    )
    rows: list[list[float]] = []  # [y_start, row_height, x_cursor, max_depth]
    placements: dict[str, tuple[float, float]] = {}
    for i in order:
        w = float(widths[i])
        h = float(heights[i])
        d = depth[i]

        # *创新*: 计算上游器件的最大右边界（已放置的上游器件）。
        # 下游器件起始 x ≥ upstream_right + SPACING，保证信号流方向 x 递增
        # 且 east↔west 连接端口 dx ≤ SPACING ≤ tol（PORT_ALIGNMENT 自然通过）。
        upstream_right = 0.0
        for up_idx in upstream_indices[i]:
            up_name = names[up_idx]
            if up_name in placements:
                up_cx, _ = placements[up_name]
                up_right = up_cx + float(widths[up_idx]) / 2.0
                if up_right > upstream_right:
                    upstream_right = up_right
        # 下游器件最小起始 x（左边界）
        min_x = upstream_right + SPACING

        candidates = [
            r for r in range(len(rows))
            if rows[r][1] >= h * 1.1
            # *创新*: d2 左边界 = max(xc + SPACING, min_x)，需在画布内
            and max(rows[r][2] + SPACING if rows[r][2] > 0.0 else 0.0, min_x) + w <= canvas_w
            and rows[r][3] < d  # 拓扑序: 行内最大 depth < 当前 depth
        ]
        if candidates:
            r = candidates[0]  # FFDH: 第一个满足拓扑约束的候选行
            ys, rh, xc, _ = rows[r]
            # *创新*: d2 左边界 = max(行内 x_cursor + SPACING, 上游最小 x)
            # 保证与行内前一个器件保持 SPACING 间距，且在上游右侧（信号流方向）
            if xc > 0.0:
                x_lo = max(xc + SPACING, min_x)
            else:
                # 行内首个器件：从 max(0, min_x) 开始
                x_lo = max(0.0, min_x)
            cx = x_lo + w / 2.0
            rows[r][2] = x_lo + w
            cy = ys + rh / 2.0
            rows[r][3] = d  # 更新行内最大拓扑深度
            placements[names[i]] = (cx, cy)
        else:
            new_h = h * 1.1
            # 行间也需 SPACING 间距（垂直方向 MIN_SPACING）
            ys = (rows[-1][0] + rows[-1][1] + SPACING) if rows else 0.0
            # *创新*: 新行起始 x 考虑上游右边界，下游器件在上游右侧
            x_start = min_x
            # 边界裁剪：x_start + w 不能超出画布
            if x_start + w > canvas_w:
                x_start = max(0.0, canvas_w - w)
            cx = x_start + w / 2.0
            cy = ys + new_h / 2.0
            rows.append([ys, new_h, x_start + w, d])
            placements[names[i]] = (cx, cy)
    return placements


# =========================================================================
# 端口对齐后处理（*创新*，光电子布局专用）
# =========================================================================

# 端口方向缩写→全称映射（与 polaris-drc engine.py 一致）
_DIR_MAP = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "north": "north", "south": "south", "east": "east", "west": "west",
}


def _normalize_dir(direction: str) -> str:
    """规范化端口方向（N→north, S→south, E→east, W→west）。"""
    return _DIR_MAP.get(str(direction).lower(), str(direction))


def _find_port_in_dev(
    device: dict, port_name: str
) -> tuple[float, float, str] | None:
    """在器件规格中查找端口，返回 (dx, dy, direction)。

    Args:
        device: 器件 dict（含 ports 列表）。
        port_name: 端口名。

    Returns:
        (dx, dy, direction)，端口未找到返回 None。
    """
    for port in device.get("ports", []):
        if len(port) >= 3 and str(port[0]) == port_name:
            direction = str(port[3]) if len(port) >= 4 else "unknown"
            return (float(port[1]), float(port[2]), direction)
    return None


def _aabb_overlap_strict(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """两 AABB 是否重叠（strict，touching 不算重叠）。

    来源: Berg "Computational Geometry" Springer §2.1 区间相交判定。
    """
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# MIN_SPACING 间距（与 polaris-drc engine.py MIN_SPACING 阈值一致，R02）
# _align_ports 后处理移动器件时需保持此间距，避免 MIN_SPACING DRC 违规。
_ALIGN_MIN_SPACING = 1.0

# PORT_ALIGNMENT 容差（μm），与 polaris-drc engine.py _PORT_ALIGN_TOL_UM 一致
# 来源: SiEPIC EBeam PDK 实际波导弯曲容差 10-20μm
# 当主轴偏差 ≤ 此容差时，PORT_ALIGNMENT 不违规（dx>tol AND dy>tol 才违规）
_ALIGN_PORT_TOL_UM = 10.0


def _no_overlap_at(
    placements: dict[str, dict[str, float]],
    exclude_name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    connected_names: set[str] | None = None,
) -> bool:
    """检查新位置 (x, y, w, h) 是否与其他器件重叠或间距不足（排除 exclude_name）。

    同时检查 NO_OVERLAP（strict）和 MIN_SPACING（1.0μm）。
    直接连接的器件对跳过 MIN_SPACING 检查（与 DRC engine 一致：波导连接
    touching 正常，R05 Bug 修复）。

    Args:
        placements: 当前所有器件布局。
        exclude_name: 排除的器件名（即正在调整的器件）。
        x, y: 新位置左下角坐标。
        w, h: 器件宽高。
        connected_names: 与 exclude_name 直接连接的器件名集合，
            这些器件跳过 MIN_SPACING 检查（但仍检查 NO_OVERLAP）。

    Returns:
        True 表示无重叠且间距满足（可放置），False 表示有重叠或间距不足。
    """
    if connected_names is None:
        connected_names = set()
    aabb = (x, y, x + w, y + h)
    for nm, pl in placements.items():
        if nm == exclude_name:
            continue
        other = (float(pl["x"]), float(pl["y"]),
                 float(pl["x"]) + float(pl["w"]),
                 float(pl["y"]) + float(pl["h"]))
        # NO_OVERLAP 检查（所有器件对，包括连接的）
        if _aabb_overlap_strict(aabb, other):
            return False
        # MIN_SPACING 检查（跳过直接连接的器件对）
        if nm in connected_names:
            continue
        dx = max(other[0] - aabb[2], aabb[0] - other[2], 0.0)
        dy = max(other[1] - aabb[3], aabb[1] - other[3], 0.0)
        dist = math.hypot(dx, dy)
        if dist < _ALIGN_MIN_SPACING:
            return False
    return True


def _find_nearest_legal_pos_1d(
    placements: dict[str, dict[str, float]],
    exclude_name: str,
    fixed_x: float,
    fixed_y: float,
    w: float,
    h: float,
    target: float,
    canvas_limit: float,
    axis: str,
    connected_names: set[str],
) -> float | None:
    """沿 axis 轴搜索最接近 target 的合法位置（另一轴固定）。

    当 _align_ports 完全对齐会导致重叠时，本函数在合法范围内找到使偏差
    最小的位置。算法: 收集其他器件在 axis 方向的"禁止区间"（重叠/间距
    不足的 y/x 范围），合并区间后在剩余合法区间内选最接近 target 的点。

    *创新点*: 经典布局后处理只做"全或无"对齐，本函数实现"最近合法位置"
    搜索，即使不能完全对齐也能将偏差降到 DRC 容差内（如 dy 从 10.57μm
    降到 9.05μm，使 PORT_ALIGNMENT 违规消除）。底层逻辑: 在 NO_OVERLAP
    和 MIN_SPACING 约束的可行域内最小化端口偏差，等价于 1D 投影下的
    约束优化。

    Args:
        placements: 当前所有器件布局。
        exclude_name: 排除的器件名（正在调整的器件）。
        fixed_x, fixed_y: 固定轴的坐标（axis='y' 时 fixed_x 固定，
            axis='x' 时 fixed_y 固定）。
        w, h: 器件宽高。
        target: 目标坐标（理想对齐位置）。
        canvas_limit: 画布尺寸（axis='y' 时为 canvas_h，axis='x' 时为 canvas_w）。
        axis: 搜索轴 'y' 或 'x'。
        connected_names: 与 exclude_name 直接连接的器件名集合
            （跳过 MIN_SPACING，与 _no_overlap_at 一致）。

    Returns:
        最近合法坐标（float），无合法位置返回 None。

    来源（R02 学术诚信）:
        - Berg "Computational Geometry" Springer §2.1 区间合并
          https://doi.org/10.1007/978-3-540-77974-2
        - Ericson "Real-Time Collision Detection" MK 2005 §5.1.3 AABB
          https://realtimecollisiondetection.net/
        - DREAMPlace TCAD 2020（合法化在约束域内优化）
          https://arxiv.org/abs/2004.10746
        - Boyd & Vandenberghe "Convex Optimization" §4 约束优化投影
          https://web.stanford.edu/~boyd/cvxbook/
        - SiEPIC EBeam PDK DRC runset（NO_OVERLAP/MIN_SPACING 约束）
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    if axis == "y":
        size = h
        fixed_lo = fixed_x
        fixed_hi = fixed_x + w
    else:  # axis == "x"
        size = w
        fixed_lo = fixed_y
        fixed_hi = fixed_y + h

    # 收集禁止区间（axis 方向）
    # R05 Bug 修复: 垂直方向判定需考虑 MIN_SPACING（非连接邻居）。
    # 原代码仅检查 strict overlap，导致两器件在垂直方向"几乎接触但不重叠"
    # （如 fixed_hi = ox1 - 0.5）时，沿 axis 方向放置会违反 MIN_SPACING
    # （真实 DRC 用 L∞ 距离判定：dx < spacing AND dy < spacing 即违规）。
    # 修复: 对非连接邻居，垂直方向影响范围扩展 MIN_SPACING 距离。
    forbidden: list[tuple[float, float]] = []
    for nm, pl in placements.items():
        if nm == exclude_name:
            continue
        ox1, oy1 = float(pl["x"]), float(pl["y"])
        ox2, oy2 = ox1 + float(pl["w"]), oy1 + float(pl["h"])
        # MIN_SPACING 间距（非连接邻居需保持，与 DRC engine 一致）
        spacing = 0.0 if nm in connected_names else _ALIGN_MIN_SPACING
        if axis == "y":
            # x 方向（垂直方向）影响范围: 重叠 OR 间距 < MIN_SPACING
            # 当 fixed 与 other 在 x 方向的距离 < spacing 时，y 方向需保持间距
            if fixed_hi <= ox1 - spacing or fixed_lo >= ox2 + spacing:
                continue
            other_lo, other_hi = oy1, oy2
        else:  # axis == "x"
            # y 方向（垂直方向）影响范围: 重叠 OR 间距 < MIN_SPACING
            if fixed_hi <= oy1 - spacing or fixed_lo >= oy2 + spacing:
                continue
            other_lo, other_hi = ox1, ox2
        # 沿 axis 方向也需 MIN_SPACING 间距（touching + spacing 合法）
        f_min = other_lo - size - spacing
        f_max = other_hi + spacing
        forbidden.append((f_min, f_max))

    # 合并禁止区间（Berg Computational Geometry §2.1）
    forbidden.sort()
    merged: list[list[float]] = []
    for f in forbidden:
        if merged and f[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], f[1])
        else:
            merged.append([f[0], f[1]])

    # 在 [0, canvas_limit - size] 内找最接近 target 的合法点
    lo = 0.0
    hi = canvas_limit - size
    if hi < lo:
        return None  # 画布太小

    # 候选点: 边界 lo/hi + 每个禁止区间的边界（touching 合法）
    candidates = [lo, hi]
    for f in merged:
        if f[1] >= lo:
            candidates.append(max(lo, f[1]))
        if f[0] <= hi:
            candidates.append(min(hi, f[0]))

    best: float | None = None
    best_dist = float("inf")
    for c in candidates:
        if c < lo or c > hi:
            continue
        # 检查 c 是否在禁止区间内（开区间，边界 touching 合法）
        if any(f[0] < c < f[1] for f in merged):
            continue
        dist = abs(c - target)
        if dist < best_dist:
            best_dist = dist
            best = c
    return best


def _align_d2_on_axis(
    placements: dict[str, dict[str, float]],
    d2_name: str,
    d2_connected: set[str],
    w2: float,
    h2: float,
    canvas_w: float,
    canvas_h: float,
    axis: str,
    port_off: float,
    abs_other: float,
) -> float:
    """在 axis 轴上对齐 d2，使端口偏差最小化。

    axis='y': 调整 d2.y，使 |d2.y + port_off - abs_other| 最小
    axis='x': 调整 d2.x，使 |d2.x + port_off - abs_other| 最小

    策略（两级）:
        1. 完全对齐: new_pos = abs_other - port_off（偏差=0）
        2. 完全对齐失败（重叠/间距）→ _find_nearest_legal_pos_1d 找最近合法位置

    仅在偏差减小时才移动（保证单调改善，不破坏已对齐的连接）。
    若当前偏差已在容差内（≤ _ALIGN_PORT_TOL_UM），直接返回不移动。

    Args:
        placements: 当前布局（会被原地修改）。
        d2_name: 待调整器件名。
        d2_connected: d2 的直接连接邻居集合（跳过 MIN_SPACING）。
        w2, h2: d2 的宽高。
        canvas_w, canvas_h: 画布尺寸。
        axis: 对齐轴 'y' 或 'x'。
        port_off: d2 端口在 axis 方向的相对偏移。
        abs_other: 对端端口在 axis 方向的绝对坐标。

    Returns:
        移动后（或未移动）的端口偏差 (float)。
    """
    pl2 = placements[d2_name]
    cur_x, cur_y = float(pl2["x"]), float(pl2["y"])
    if axis == "y":
        target = abs_other - port_off
        canvas_limit = canvas_h
        size = h2
        cur_pos = cur_y
    else:
        target = abs_other - port_off
        canvas_limit = canvas_w
        size = w2
        cur_pos = cur_x
    cur_dev = abs(cur_pos + port_off - abs_other)
    if cur_dev <= _ALIGN_PORT_TOL_UM:
        return cur_dev  # 已在容差内，无需移动

    # 1. 完全对齐（偏差=0）
    new_pos = max(0.0, min(target, canvas_limit - size))
    if axis == "y":
        ok = _no_overlap_at(placements, d2_name, cur_x, new_pos, w2, h2, d2_connected)
    else:
        ok = _no_overlap_at(placements, d2_name, new_pos, cur_y, w2, h2, d2_connected)
    if ok:
        new_dev = abs(new_pos + port_off - abs_other)
        if new_dev < cur_dev:
            if axis == "y":
                placements[d2_name]["y"] = new_pos
            else:
                placements[d2_name]["x"] = new_pos
        return new_dev

    # 2. 完全对齐失败 → 最近合法位置（*创新*，约束域内最小化偏差）
    nearest = _find_nearest_legal_pos_1d(
        placements, d2_name, cur_x, cur_y, w2, h2,
        target, canvas_limit, axis, d2_connected,
    )
    if nearest is not None:
        new_dev = abs(nearest + port_off - abs_other)
        if new_dev < cur_dev:
            if axis == "y":
                placements[d2_name]["y"] = nearest
            else:
                placements[d2_name]["x"] = nearest
            return new_dev
    return cur_dev


def _align_ports(
    placements: dict[str, dict[str, float]],
    circuit: dict,
    canvas_w: float,
    canvas_h: float,
) -> dict[str, dict[str, float]]:
    """端口对齐后处理（*创新*，光电子布局专用）。

    FFDH 合法化只保证无重叠和拓扑序，不考虑端口对齐。本函数在 FFDH 后
    对每个连接调整下游器件位置，使连接两端端口坐标对齐（共享 x 或 y），
    减少 PORT_ALIGNMENT DRC 违规和波导弯曲损耗。

    ## 算法

    1. 按拓扑顺序遍历器件（depth 从小到大，保证上游先固定）
    2. 对每个连接 (d1.p1 → d2.p2)，d2 作为待调整器件:
       a. 计算两端端口绝对坐标 abs1, abs2
       b. 根据端口方向决定对齐轴:
          - east↔west 水平连接: 对齐 y（使两端端口 y 相同）
          - north↔south 垂直连接: 对齐 x
          - 方向不明确: 对齐偏差较大的轴
       c. 调整 d2 位置使端口对齐，边界裁剪到画布内
       d. 检查调整后无重叠（与所有其他器件），冲突则回退保持原位置

    ## *创新点*

    经典 FFDH/DREAMPlace（VLSI 布局）无端口概念，器件间通过金属层
    任意布线。但光电子布局中，器件通过波导物理连接，端口对齐能显著
    减少波导弯曲（每增加一个弯曲 ≈ 0.05dB 损耗，Chrostowski & Hochberg
    "Silicon Photonics Design" CUP 2015 §4.3）。本函数将端口对齐作为
    FFDH 后处理步骤，桥接 VLSI 布局算法与光电子物理约束。

    底层逻辑: 拓扑顺序保证上游器件先固定位置，下游器件对齐到上游端口；
    重叠检查保证对齐不破坏 FFDH 的无重叠保证；边界裁剪保证器件在画布内。

    Args:
        placements: FFDH 合法化后的布局 {name: {x, y, w, h}}（左下角坐标）。
        circuit: polaris-core 风格 circuit dict（含 devices.ports）。
        canvas_w: 画布宽 (μm)。
        canvas_h: 画布高 (μm)。

    Returns:
        端口对齐后的布局（可能部分连接因重叠冲突未对齐，保持原位置）。

    来源（R02 学术诚信）:
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746（FFDH 基础）
        - Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
          波导弯曲损耗 https://www.cambridge.org/core/books/silicon-photonics-design/
        - SiEPIC EBeam PDK DRC runset PORT_ALIGNMENT 规则
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Kahng & Lienig "VLSI Placement" IEEE TCAD 2009
          https://ieeexplore.ieee.org/document/4685534
        - Berg "Computational Geometry" Springer（AABB 相交判定）
          https://doi.org/10.1007/978-3-540-77974-2
    """
    if not placements:
        return placements

    # 构建器件名 → 器件规格映射（含 ports）
    device_map: dict[str, dict] = {}
    for dev in circuit.get("devices", []):
        nm = dev.get("name")
        if nm is not None:
            device_map[nm] = dev

    # 拓扑顺序（保证上游先固定，下游对齐到上游）
    names = list(placements.keys())
    name_to_idx = {nm: i for i, nm in enumerate(names)}
    idx_conns: list[tuple[int, int]] = []
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1, _p1, d2, _p2 = str(conn[0]), conn[1], str(conn[2]), conn[3]
        if d1 in name_to_idx and d2 in name_to_idx:
            idx_conns.append((name_to_idx[d1], name_to_idx[d2]))

    try:
        depth = _topological_depth(len(names), idx_conns)
    except RuntimeError:
        # 连接存在环（极少见），跳过端口对齐（R03: 不假数据，保持 FFDH 结果）
        return placements

    # 按拓扑顺序处理（depth 从小到大）
    order = sorted(range(len(names)), key=lambda i: depth[i])

    # 构建每个器件的直接连接邻居集合（用于 MIN_SPACING 跳过，与 DRC engine 一致）
    connected_neighbors: dict[str, set[str]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1_name, d2_name_conn = str(conn[0]), str(conn[2])
        connected_neighbors.setdefault(d1_name, set()).add(d2_name_conn)
        connected_neighbors.setdefault(d2_name_conn, set()).add(d1_name)

    for i in order:
        d2_name = names[i]
        if d2_name not in placements:
            continue
        d2_dev = device_map.get(d2_name, {})
        # d2 的直接连接邻居（这些器件跳过 MIN_SPACING 检查，但仍检查 NO_OVERLAP）
        d2_connected = connected_neighbors.get(d2_name, set())

        # 遍历所有连接到 d2 的连接（d2 作为下游 d2）
        for conn in circuit.get("connections", []):
            if len(conn) < 4:
                continue
            d1_name, p1_name, d2_conn, p2_name = (
                str(conn[0]), conn[1], str(conn[2]), conn[3]
            )
            if d2_conn != d2_name:
                continue
            if d1_name not in placements or d2_name not in placements:
                continue

            port1 = _find_port_in_dev(device_map.get(d1_name, {}), p1_name)
            port2 = _find_port_in_dev(d2_dev, p2_name)
            if port1 is None or port2 is None:
                continue

            pl1 = placements[d1_name]
            pl2 = placements[d2_name]
            # 端口绝对坐标 = 器件左下角 + 端口相对偏移
            abs1_x = float(pl1["x"]) + port1[0]
            abs1_y = float(pl1["y"]) + port1[1]
            abs2_x = float(pl2["x"]) + port2[0]
            abs2_y = float(pl2["y"]) + port2[1]

            dir1 = _normalize_dir(port1[2])
            dir2 = _normalize_dir(port2[2])
            w2 = float(pl2["w"])
            h2 = float(pl2["h"])

            # 决定主轴和副轴
            # DRC PORT_ALIGNMENT 判定: dx > tol AND dy > tol 才算违规
            # 因此只要 dx ≤ tol 或 dy ≤ tol 之一即对齐通过
            # 主轴 = 优先对齐的轴；副轴 = 主轴偏差仍 > tol 时的备选
            if (dir1, dir2) in (("east", "west"), ("west", "east")):
                # 水平连接（east↔west），主轴 y（对齐 y 使 dy ≤ tol）
                primary_axis, secondary_axis = "y", "x"
            elif (dir1, dir2) in (("north", "south"), ("south", "north")):
                # 垂直连接（north↔south），主轴 x（对齐 x 使 dx ≤ tol）
                primary_axis, secondary_axis = "x", "y"
            else:
                # 方向不明确，选偏差较大的轴为主轴（偏差大的轴优先对齐）
                if abs(abs1_y - abs2_y) >= abs(abs1_x - abs2_x):
                    primary_axis, secondary_axis = "y", "x"
                else:
                    primary_axis, secondary_axis = "x", "y"

            # *R05 Bug 修复*: 主副轴独立对齐策略
            # 原代码先提交主轴移动，再在新位置检查副轴。但副轴在原始位置可能可行，
            # 主轴移动后改变了副轴重叠检查的参考点，可能阻挡原本可行的副轴对齐。
            #
            # PORT_ALIGNMENT 规则: dx > tol AND dy > tol 才违规，
            # 任一轴 ≤ tol 即通过。因此正确策略: 从原始位置独立尝试两轴，
            # 根据实际 dx/dy 选最优结果。
            #
            # 策略（*创新*）: 双候选独立评估
            #   1. 候选 1: 从原始位置做主轴对齐 → 记录 (dx1, dy1)
            #   2. 恢复原始位置
            #   3. 候选 2: 从原始位置做副轴对齐 → 记录 (dx2, dy2)
            #   4. 选择: 任一候选通过则选通过的；都通过/都不通过则选 max(dx,dy) 较小者
            orig_x, orig_y = float(pl2["x"]), float(pl2["y"])

            # 候选 1: 主轴对齐（从原始位置，_align_d2_on_axis 内部完全对齐→最近合法位置）
            if primary_axis == "y":
                _align_d2_on_axis(
                    placements, d2_name, d2_connected, w2, h2,
                    canvas_w, canvas_h, "y", port2[1], abs1_y,
                )
            else:
                _align_d2_on_axis(
                    placements, d2_name, d2_connected, w2, h2,
                    canvas_w, canvas_h, "x", port2[0], abs1_x,
                )
            p1_x = float(placements[d2_name]["x"])
            p1_y = float(placements[d2_name]["y"])
            dx1 = abs(abs1_x - (p1_x + port2[0]))
            dy1 = abs(abs1_y - (p1_y + port2[1]))

            # 候选 2: 副轴对齐（恢复原始位置后，从原始位置对齐副轴）
            placements[d2_name]["x"] = orig_x
            placements[d2_name]["y"] = orig_y
            if secondary_axis == "y":
                _align_d2_on_axis(
                    placements, d2_name, d2_connected, w2, h2,
                    canvas_w, canvas_h, "y", port2[1], abs1_y,
                )
            else:
                _align_d2_on_axis(
                    placements, d2_name, d2_connected, w2, h2,
                    canvas_w, canvas_h, "x", port2[0], abs1_x,
                )
            p2_x = float(placements[d2_name]["x"])
            p2_y = float(placements[d2_name]["y"])
            dx2 = abs(abs1_x - (p2_x + port2[0]))
            dy2 = abs(abs1_y - (p2_y + port2[1]))

            # 选择更优候选: PORT_ALIGNMENT 通过 = dx ≤ tol OR dy ≤ tol
            pass1 = (dx1 <= _ALIGN_PORT_TOL_UM) or (dy1 <= _ALIGN_PORT_TOL_UM)
            pass2 = (dx2 <= _ALIGN_PORT_TOL_UM) or (dy2 <= _ALIGN_PORT_TOL_UM)
            # 默认保留候选 2（已在 placements 中），仅在以下情况恢复候选 1:
            #   - 候选 1 通过且候选 2 不通过
            #   - 两者同状态（都通过或都不通过）且候选 1 的 max(dx,dy) 更小
            if pass1 and not pass2:
                placements[d2_name]["x"] = p1_x
                placements[d2_name]["y"] = p1_y
            elif pass2 and not pass1:
                pass  # 保留候选 2（已在 placements 中）
            elif max(dx1, dy1) <= max(dx2, dy2):
                placements[d2_name]["x"] = p1_x
                placements[d2_name]["y"] = p1_y

    return placements


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
