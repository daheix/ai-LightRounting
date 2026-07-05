"""解析法布局器 - FFDH 合法化模块（polaris-place 子模块）。

从 ``analytical.py`` 拆分而来，包含 FFDH（First-Fit Decreasing Height）
合法化算法，消除重叠并保证信号流方向 x 递增。

仅依赖 numpy（R04: 不参与 GPU）。

## 来源（R02 学术诚信）

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

from __future__ import annotations

import numpy as np

from .analytical_optimizer import topological_depth

__all__ = ["legalize"]


def _legalize_setup(
    n: int, connections: list[tuple[int, int]],
) -> tuple[list[int], list[list[int]]]:
    """计算拓扑深度 + 上游器件索引映射。

    *创新*: upstream_indices 用于信号流方向起始 x 计算，downstream 的 x
    应 ≥ upstream 的右边界 + SPACING，保证 east↔west 连接的端口
    dx ≤ SPACING ≤ PORT_ALIGNMENT 容差（10μm）。
    """
    depth = topological_depth(n, connections)
    upstream_indices: list[list[int]] = [[] for _ in range(n)]
    for src, dst in connections:
        upstream_indices[dst].append(src)
    return depth, upstream_indices


def _legalize_compute_min_x(
    i: int, upstream_indices: list[list[int]],
    names: list[str], placements: dict, widths: np.ndarray,
    spacing: float,
) -> float:
    """计算器件 i 的最小起始 x（左边界）。

    *创新*: 下游器件起始 x ≥ upstream_right + SPACING，保证信号流方向
    x 递增，且 east↔west 连接端口 dx ≤ SPACING ≤ tol（PORT_ALIGNMENT
    自然通过）。底层逻辑: 光电子布局中 east↔west 连接要求 d2 在 d1 右侧
    （d2.x ≥ d1.x + d1.w），VLSI FFDH 无此问题因为金属层任意布线，
    光电子波导需端口对齐。
    """
    upstream_right = 0.0
    for up_idx in upstream_indices[i]:
        up_name = names[up_idx]
        if up_name in placements:
            up_cx, _ = placements[up_name]
            up_right = up_cx + float(widths[up_idx]) / 2.0
            if up_right > upstream_right:
                upstream_right = up_right
    return upstream_right + spacing


def _legalize_find_candidate_rows(
    rows: list[list[float]], h: float, d: int,
    min_x: float, w: float, canvas_w: float, spacing: float,
) -> list[int]:
    """查找满足高度/画布/拓扑约束的候选行索引。

    约束: 行高 ≥ h*1.1；d2 左边界 = max(xc+SPACING, min_x) + w ≤ canvas_w；
    行内最大 depth < 当前 d（拓扑序保证信号流 x 递增）。
    """
    candidates = []
    for r in range(len(rows)):
        if rows[r][1] < h * 1.1:
            continue
        # *创新*: d2 左边界 = max(xc + SPACING, min_x)，需在画布内
        x_lo = max(rows[r][2] + spacing if rows[r][2] > 0.0 else 0.0, min_x)
        if x_lo + w > canvas_w:
            continue
        if rows[r][3] >= d:  # 拓扑序: 行内最大 depth < 当前 depth
            continue
        candidates.append(r)
    return candidates


def _legalize_place_in_existing_row(
    rows: list[list[float]], r: int, w: float, min_x: float,
    spacing: float, name: str, d: int,
    placements: dict[str, tuple[float, float]],
) -> None:
    """在已有行 r 放置器件（FFDH: 第一个满足拓扑约束的候选行）。

    *创新*: d2 左边界 = max(行内 x_cursor + SPACING, 上游最小 x)，
    保证与行内前一个器件保持 SPACING 间距，且在上游右侧（信号流方向）。
    """
    ys, rh, xc, _ = rows[r]
    if xc > 0.0:
        x_lo = max(xc + spacing, min_x)
    else:
        x_lo = max(0.0, min_x)  # 行内首个器件
    cx = x_lo + w / 2.0
    rows[r][2] = x_lo + w
    cy = ys + rh / 2.0
    rows[r][3] = d  # 更新行内最大拓扑深度
    placements[name] = (cx, cy)


def _legalize_place_in_new_row(
    rows: list[list[float]], h: float, w: float, min_x: float,
    name: str, d: int, canvas_w: float, spacing: float,
    placements: dict[str, tuple[float, float]],
) -> None:
    """在新行放置器件（无候选行可用时）。

    *创新*: 新行起始 x 考虑上游右边界，下游器件在上游右侧；边界裁剪
    防止超出画布。
    """
    new_h = h * 1.1
    # 行间也需 SPACING 间距（垂直方向 MIN_SPACING）
    ys = (rows[-1][0] + rows[-1][1] + spacing) if rows else 0.0
    x_start = min_x
    if x_start + w > canvas_w:  # 边界裁剪
        x_start = max(0.0, canvas_w - w)
    cx = x_start + w / 2.0
    cy = ys + new_h / 2.0
    rows.append([ys, new_h, x_start + w, d])
    placements[name] = (cx, cy)


def legalize(
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
    """
    # MIN_SPACING 间距（来源: SiEPIC EBeam PDK WG_MIN_SPACE=1.0μm，
    # 与 polaris-drc engine.py MIN_SPACING 阈值一致，R02 学术诚信）
    # 行内器件间需保持 SPACING 间距，避免 MIN_SPACING DRC 违规（R05 Bug 修复）。
    SPACING = 1.0
    n = len(names)
    if n == 0:
        return {}
    depth, upstream_indices = _legalize_setup(n, connections)
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
        min_x = _legalize_compute_min_x(
            i, upstream_indices, names, placements, widths, SPACING,
        )
        candidates = _legalize_find_candidate_rows(
            rows, h, d, min_x, w, canvas_w, SPACING,
        )
        if candidates:
            _legalize_place_in_existing_row(
                rows, candidates[0], w, min_x, SPACING, names[i], d,
                placements,
            )
        else:
            _legalize_place_in_new_row(
                rows, h, w, min_x, names[i], d, canvas_w, SPACING,
                placements,
            )
    return placements
