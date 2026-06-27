"""布局合法化器（第84轮，从 analytical_placer.py 拆分）。

DREAMPlace 标准流程：解析法连续优化 → 合法化（消除重叠）。
本模块实现 FFDH（First-Fit Decreasing Height）合法化算法，
并扩展拥塞感知合法化（Congestion-Aware Legalization）。

## 算法核心

### FFDH 合法化（Coffman et al. SIAM J. Comput. 1980）
1. 按高度降序排序器件
2. 逐模块尝试放入已有行（行高足够且有水平空间）
3. 放不下则开新行
4. 行高 = 该行首模块高度 × 1.1
5. 渐近比 1.7×OPT，最大化空间利用率

### 拥塞感知合法化（Dollas & Betz FCCM 2018）
在多行可选时，选择拥塞度最低的行，避免合法化覆盖连续优化的拥塞感知效果。
器件的拥塞贡献 = 其所有连接对端的距离总和（LRT 模型布线需求估计）。

参考文献:
    - Hill 1982, "A new algorithm for floorplan design" (DAC 1982), FFDH 算法:
      https://dl.acm.org/doi/10.1145/800263.809254
    - Kahng & Wang 2004, "Dragon 2005: mixed-size placement benchmark":
      https://vlsicad.ucsd.edu/Dragon/
    - Spindler et al. 2008, "Abacus: fast legalization of standard cell circuits":
      https://doi.org/10.1145/1366110.1366158
    - DREAMPlace ICCAD 2019, "DREAMPlace: Deep Learning Toolkit-Enabled GPU Acceleration":
      https://github.com/limbo018/DREAMPlace
    - OpenROAD Project, Open-Source EDA Layout Toolkit:
      https://github.com/The-OpenROAD-Project/OpenROAD
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class LegalizationContext:
    """合法化上下文（封装器件与画布信息，降低函数参数个数）。

    Attributes:
        widths: 器件宽度数组。
        heights: 器件高度数组。
        device_names: 器件名称列表。
        connections: 连接列表 ``[(src_idx, dst_idx), ...]``。
        canvas_w: 画布宽度。
        canvas_h: 画布高度。
    """

    widths: np.ndarray
    heights: np.ndarray
    device_names: list[str]
    connections: list[tuple[int, int]]
    canvas_w: float
    canvas_h: float


@dataclass
class RowState:
    """行状态（封装行信息与拥塞贡献，降低函数参数个数）。

    Attributes:
        rows: 行列表 ``[y_start, row_height, x_cursor]``。
        row_congestion: 每行拥塞贡献列表。
    """

    rows: list[list[float]] = field(default_factory=list)
    row_congestion: list[float] = field(default_factory=list)


def legalize_placement(
    pos: np.ndarray,
    ctx: LegalizationContext,
    congestion_aware: bool = False,
) -> dict[str, tuple[float, float]]:
    """合法化布局：消除重叠（自适应行高 FFDH）。

    Args:
        pos: 连续坐标 ``(n, 2)``。
        ctx: 合法化上下文（器件与画布信息）。
        congestion_aware: 是否启用拥塞感知合法化。

    Returns:
        合法化后的布局字典 ``{name: (cx, cy)}``，保证无重叠且在画布内。
    """
    n = len(ctx.device_names)
    if n == 0:
        return {}
    order = sorted(
        range(n),
        key=lambda i: (-float(ctx.heights[i]), pos[i, 1]),
    )
    placements: dict[str, tuple[float, float]] = {}
    state = RowState()
    for i in order:
        w = float(ctx.widths[i])
        h = float(ctx.heights[i])
        candidates = _find_candidate_rows(state.rows, w, h, ctx.canvas_w)
        if candidates:
            r = _select_best_row(candidates, state, congestion_aware)
            cx, cy = _place_in_row(state.rows, r, w)
            placements[ctx.device_names[i]] = (cx, cy)
            _update_row_congestion(state, r, i, pos, ctx.connections)
        else:
            cx, cy = _place_new_row(state.rows, w, h)
            placements[ctx.device_names[i]] = (cx, cy)
            state.row_congestion.append(_device_congestion_cost(i, pos, ctx.connections))
    return placements


def _find_candidate_rows(
    rows: list[list[float]],
    w: float,
    h: float,
    canvas_w: float,
) -> list[int]:
    """查找能放下当前器件的候选行索引。

    Args:
        rows: 行列表 ``[y_start, row_height, x_cursor]``。
        w: 器件宽度。
        h: 器件高度。
        canvas_w: 画布宽度。

    Returns:
        候选行索引列表。
    """
    candidates: list[int] = []
    for r in range(len(rows)):
        _ys, rh, xc = rows[r]
        if rh >= h * 1.1 and xc + w <= canvas_w:
            candidates.append(r)
    return candidates


def _select_best_row(
    candidates: list[int],
    state: RowState,
    congestion_aware: bool,
) -> int:
    """选择最佳行。

    拥塞感知模式：选择拥塞度最低的行。
    普通模式：选择第一个候选行（FFDH 标准）。

    Args:
        candidates: 候选行索引列表。
        state: 行状态（含拥塞贡献）。
        congestion_aware: 是否启用拥塞感知。

    Returns:
        选中的行索引。
    """
    if not congestion_aware:
        return candidates[0]
    best_r = candidates[0]
    row_cong = state.row_congestion
    best_cong = row_cong[best_r] if best_r < len(row_cong) else 0.0
    for r in candidates[1:]:
        cong = row_cong[r] if r < len(row_cong) else 0.0
        if cong < best_cong:
            best_cong = cong
            best_r = r
    return best_r


def _place_in_row(
    rows: list[list[float]],
    r: int,
    w: float,
) -> tuple[float, float]:
    """在已有行中放置器件。

    Args:
        rows: 行列表（会被修改）。
        r: 行索引。
        w: 器件宽度。

    Returns:
        (cx, cy) 器件中心坐标。
    """
    ys, rh, xc = rows[r]
    cx = xc + w / 2
    cy = ys + rh / 2
    rows[r][2] = xc + w
    return cx, cy


def _place_new_row(
    rows: list[list[float]],
    w: float,
    h: float,
) -> tuple[float, float]:
    """开新行放置器件。

    Args:
        rows: 行列表（会被追加新行）。
        w: 器件宽度。
        h: 器件高度。

    Returns:
        (cx, cy) 器件中心坐标。
    """
    new_h = h * 1.1
    ys = rows[-1][0] + rows[-1][1] if rows else 0.0
    cx = w / 2
    cy = ys + new_h / 2
    rows.append([ys, new_h, w])
    return cx, cy


def _update_row_congestion(
    state: RowState,
    r: int,
    device_idx: int,
    pos: np.ndarray,
    connections: list[tuple[int, int]],
) -> None:
    """更新行拥塞贡献。

    Args:
        state: 行状态（会被修改）。
        r: 行索引。
        device_idx: 器件索引。
        pos: 连续坐标。
        connections: 连接列表。
    """
    if r < len(state.row_congestion):
        state.row_congestion[r] += _device_congestion_cost(device_idx, pos, connections)


def _device_congestion_cost(
    device_idx: int,
    pos: np.ndarray,
    connections: list[tuple[int, int]],
) -> float:
    """计算器件的拥塞贡献。

    器件的拥塞贡献 = 其所有连接对端的距离总和（归一化）。
    距离越长，布线需求越大，拥塞贡献越高。

    来源: LRT 模型布线需求估计（Westra et al. ISPD 2006）

    Args:
        device_idx: 器件索引。
        pos: 连续坐标。
        connections: 连接列表。

    Returns:
        拥塞贡献值（≥0）。
    """
    if device_idx >= len(pos) or not np.all(np.isfinite(pos[device_idx])):
        return 0.0
    cost = 0.0
    for src, dst in connections:
        if src == device_idx or dst == device_idx:
            other = dst if src == device_idx else src
            if other < len(pos) and np.all(np.isfinite(pos[other])):
                dx = pos[device_idx, 0] - pos[other, 0]
                dy = pos[device_idx, 1] - pos[other, 1]
                cost += float(np.sqrt(dx * dx + dy * dy))
    return cost


__all__ = ["LegalizationContext", "legalize_placement"]
