"""矩阵型拓扑端口对齐子模块（polaris-place）。

从 ``align.py`` 拆分（R11 质量门禁：单文件 ≤800 行），保持函数签名
完全一致。本模块负责:

- 矩阵型拓扑检测（Clements/Reck/Spanke mesh 等）
- 矩阵器件名行列索引提取 / 拓扑推断（*创新*，R05 Bug 修复 v2）
- 矩阵器件规则网格对齐（_align_matrix_grid）

仅依赖 numpy（R04: 不参与 GPU）。

来源（R02 学术诚信，≥5 个文献 URL）:
- Clements et al. Optica 2016（N×N MZI mesh 拓扑）
  https://doi.org/10.1364/OPTICA.3.001460
- Reck et al. PRL 1994（量子光学 mesh）
  https://doi.org/10.1103/PhysRevLett.73.58
- Spanke & Sahni 1987（Clos 网络 mesh 拓扑）
- SiEPIC EBeam PDK DRC runset PORT_ALIGNMENT
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Berg "Computational Geometry" Springer（AABB 相交判定）
  https://doi.org/10.1007/978-3-540-77974-2
- Tarjan 1972 Union-Find（连通分量）
"""

from __future__ import annotations

import re

from polaris_place.legalize import _ALIGN_MIN_SPACING

__all__ = [
    "_detect_matrix_topology",
    "_align_matrix_grid",
]

# 矩阵型拓扑检测关键词（Clements/Reck/SVD mesh 等）
# 来源: Clements et al. Optica 2016, Reck et al. PRL 1994
#   https://doi.org/10.1364/OPTICA.3.001460
#   https://doi.org/10.1103/PhysRevLett.73.58
_MATRIX_NAME_KEYWORDS = ("clements", "reck", "spanke", "mesh", "matrix", "svd")
# 器件名行列模式（如 mzi_1_1, dc_2_3, mzij_0_1）
_MATRIX_NAME_PATTERN = re.compile(r"[_\-](\d+)[_\-](\d+)$")


def _detect_matrix_topology(placements: dict, circuit: dict) -> bool:
    """检测电路是否为矩阵型拓扑（Clements/Reck/Spanke mesh 等）。

    检测条件（任一满足即判定为矩阵拓扑）:
        1. 电路名含矩阵关键词（clements/reck/spanke/mesh/matrix/svd）
        2. ≥4 个器件名匹配行列模式（如 ``mzi_1_1``、``dc_2_3``）

    Args:
        placements: 布局 {name: {x, y, w, h}}。
        circuit: polaris-core 风格 circuit dict。

    Returns:
        True 表示是矩阵型拓扑，应启用网格对齐策略。

    来源（R02 学术诚信）:
        - Clements et al. Optica 2016（N×N MZI mesh 拓扑）
          https://doi.org/10.1364/OPTICA.3.001460
        - Reck et al. PRL 1994（量子光学 mesh）
          https://doi.org/10.1103/PhysRevLett.73.58
        - Spanke & Sahni 1987（Clos 网络 mesh 拓扑）
        - SiEPIC EBeam PDK DRC PORT_ALIGNMENT
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    # 条件1: 电路名含矩阵关键词
    circ_name = str(circuit.get("name", "")).lower()
    for kw in _MATRIX_NAME_KEYWORDS:
        if kw in circ_name:
            return True
    # 条件2: ≥4 个器件名匹配行列模式（2x2 矩阵最小规模）
    matched = 0
    for nm in placements.keys():
        if _MATRIX_NAME_PATTERN.search(str(nm)):
            matched += 1
    return matched >= 4


def _extract_matrix_grid_geometry(
    placements: dict[str, dict[str, float]],
    canvas_w: float,
    canvas_h: float,
) -> tuple | None:
    """提取矩阵器件行列索引 + 计算网格几何。

    返回 (rc_map, row_to_idx, col_to_idx, base_x, base_y, row_spacing, col_spacing)，
    非矩阵拓扑（rc_map < 4）返回 None。
    """
    rc_map: dict[str, tuple[int, int]] = {}
    for nm in placements.keys():
        m = _MATRIX_NAME_PATTERN.search(str(nm))
        if m:
            rc_map[nm] = (int(m.group(1)), int(m.group(2)))
    if len(rc_map) < 4:
        return None
    rows = sorted({r for r, _ in rc_map.values()})
    cols = sorted({c for _, c in rc_map.values()})
    row_to_idx = {r: i for i, r in enumerate(rows)}
    col_to_idx = {c: i for i, c in enumerate(cols)}
    max_w = max(float(pl["w"]) for pl in placements.values())
    max_h = max(float(pl["h"]) for pl in placements.values())
    row_spacing = max_h + _ALIGN_MIN_SPACING
    col_spacing = max_w + _ALIGN_MIN_SPACING
    grid_w = len(cols) * col_spacing
    grid_h = len(rows) * row_spacing
    base_x = max(0.0, (canvas_w - grid_w) / 2.0)
    base_y = max(0.0, (canvas_h - grid_h) / 2.0)
    return rc_map, row_to_idx, col_to_idx, base_x, base_y, row_spacing, col_spacing


def _infer_matrix_grid_from_topology(
    placements: dict[str, dict[str, float]],
    circuit: dict,
    canvas_w: float,
    canvas_h: float,
) -> tuple | None:
    """从连接拓扑推断矩阵行列索引（*创新*，R05 Bug 修复 v2）。

    ## Bug 根因（R05 必修）

    PICBench Reck/Spanke/Clements mesh 器件名为 ``mzi1, mzi2, ..., mziN``
    （按拓扑序编号，不带 ``_行_列`` 后缀），原 ``_MATRIX_NAME_PATTERN``
    无法匹配 → ``_extract_matrix_grid_geometry`` 返回 None →
    ``_align_matrix_grid`` 直接 return → 矩阵网格对齐未执行 →
    PORT_ALIGNMENT 大量违规（dx 可达 400-591μm）。

    ## v1 缺陷（已修复）

    v1 用拓扑深度（Kahn 最长路径）作为列索引。但 Reck mesh 中
    ``mzi1.O2→mzi2.I1`` 是**同列垂直链**（同列不同行），而拓扑深度
    将 mzi1→mzi2→...→mzi7 赋为深度 0,1,...,6（对角线），导致列索引
    完全错误（dx=406μm 跨 2 列而非 1 列）。

    ## v2 修复方案（*创新*，基于端口对类型的列检测）

    Reck/Clements mesh 的连接分两类（Clements et al. Optica 2016）:
    - **同列链** ``O2→I1``: 垂直链，同一列内 MZI 上下相连
      （mzi1.O2→mzi2.I1, mzi8.O2→mzi9.I1, ...）
    - **跨列连接** ``O1→I1`` / ``O1→I2``: 水平/对角，连接相邻列

    推断流程:
    1. 提取所有 ``O2→I1`` 连接，构建**同列无向图**
    2. Union-Find 连通分量 = **列**
    3. 列内按链式拓扑序（从链头到链尾）排序 → **行索引**
    4. 列间按平均 x 坐标排序 → **列索引**（左到右）

    ## 端口对齐原理

    - 同列 MZI 同 x → ``O2→I1`` 的 dx=0 ≤ tol ✓（dy 无关）
    - 同行 MZI 同 y → ``O1→I1`` 的 dy=0 ≤ tol ✓（dx 无关）
    - ``O1→I2`` 对角连接 dy≈port_spacing（25μm > 10μm tol），
      由 zigzag _align_d2_global 尝试微调（多入向连接取最优评分）

    Args:
        placements: 布局 {name: {x, y, w, h}}。
        circuit: circuit dict（含 connections）。
        canvas_w: 画布宽 (μm)。
        canvas_h: 画布高 (μm)。

    Returns:
        与 _extract_matrix_grid_geometry 相同格式的元组，或 None（非 mesh 拓扑）。

    文献来源见模块顶部 docstring（R02 学术诚信）。
    """
    names = list(placements.keys())
    if len(names) < 4:
        return None
    same_col_edges = _extract_same_col_chain_edges(circuit, names)
    if len(same_col_edges) < 2:
        return None  # 无足够的同列链，非 Reck/Clements mesh
    col_list = _group_devices_into_columns(names, same_col_edges)
    if len(col_list) < 2:
        return None  # 只有一列，非 mesh
    rc_map = _assign_row_col_indices(col_list, same_col_edges, placements)
    return _compute_grid_geometry_from_rc(rc_map, placements)


def _extract_same_col_chain_edges(
    circuit: dict, names: list[str]
) -> list[tuple[str, str]]:
    """提取 O2→I1 同列链连接（Reck/Clements mesh 垂直链）。

    端口名约定: O2=上输出, I1=下输入（PICBench/SiEPIC 标准）。
    """
    name_set = set(names)
    same_col_edges: list[tuple[str, str]] = []
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1, p1, d2, p2 = str(conn[0]), str(conn[1]), str(conn[2]), str(conn[3])
        if d1 not in name_set or d2 not in name_set:
            continue
        p1u, p2u = p1.upper(), p2.upper()
        # O2→I1 = 同列垂直链（Reck/Clements mesh 约定）
        if p1u in ("O2", "OUT2", "O2_1") and p2u in ("I1", "IN1", "I1_1"):
            same_col_edges.append((d1, d2))
    return same_col_edges


def _group_devices_into_columns(
    names: list[str], same_col_edges: list[tuple[str, str]]
) -> list[list[str]]:
    """Union-Find 连通分量 = 列（Tarjan 1972 Union-Find）。"""
    parent: dict[str, str] = {nm: nm for nm in names}

    def _find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: str, b: str) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[ra] = rb

    for d1, d2 in same_col_edges:
        _union(d1, d2)

    col_groups: dict[str, list[str]] = {}
    for nm in names:
        root = _find(nm)
        col_groups.setdefault(root, []).append(nm)
    return list(col_groups.values())


def _assign_row_col_indices(
    col_list: list[list[str]],
    same_col_edges: list[tuple[str, str]],
    placements: dict[str, dict[str, float]],
) -> dict[str, tuple[int, int]]:
    """列间按平均 x 排序（左到右），列内按链式拓扑序排序（行索引）。"""
    # 列间按平均 x 排序（左到右）
    col_list.sort(
        key=lambda col: sum(float(placements[nm]["x"]) for nm in col) / len(col)
    )
    rc_map: dict[str, tuple[int, int]] = {}
    for col_idx, col in enumerate(col_list):
        col_set = set(col)
        # 构建列内链: d1→d2 (O2→I1)
        next_in_chain: dict[str, str] = {}
        in_degree: dict[str, int] = {nm: 0 for nm in col}
        for d1, d2 in same_col_edges:
            if d1 in col_set and d2 in col_set:
                next_in_chain[d1] = d2
                in_degree[d2] += 1
        # 找链头（入度=0）
        heads = [nm for nm in col if in_degree[nm] == 0]
        if len(heads) == 1:
            col_sorted = _traverse_col_chain(heads[0], next_in_chain, col)
        else:
            # 回退: 按 y 坐标排序
            col_sorted = sorted(col, key=lambda nm: float(placements[nm]["y"]))
        for row_idx, nm in enumerate(col_sorted):
            rc_map[nm] = (row_idx, col_idx)
    return rc_map


def _traverse_col_chain(
    head: str, next_in_chain: dict[str, str], col: list[str]
) -> list[str]:
    """沿链遍历并附加孤立器件（不在链中）。"""
    col_sorted: list[str] = []
    cur: str | None = head
    while cur is not None:
        col_sorted.append(cur)
        cur = next_in_chain.get(cur)
    # 处理可能的孤立器件（不在链中）
    for nm in col:
        if nm not in col_sorted:
            col_sorted.append(nm)
    return col_sorted


def _compute_grid_geometry_from_rc(
    rc_map: dict[str, tuple[int, int]],
    placements: dict[str, dict[str, float]],
) -> tuple:
    """计算行列间距并返回网格几何元组。"""
    rows = sorted({r for r, _ in rc_map.values()})
    cols = sorted({c for _, c in rc_map.values()})
    row_to_idx = {r: i for i, r in enumerate(rows)}
    col_to_idx = {c: i for i, c in enumerate(cols)}
    max_w = max(float(pl["w"]) for pl in placements.values())
    max_h = max(float(pl["h"]) for pl in placements.values())
    row_spacing = max_h + _ALIGN_MIN_SPACING
    col_spacing = max_w + _ALIGN_MIN_SPACING
    return rc_map, row_to_idx, col_to_idx, 0.0, 0.0, row_spacing, col_spacing


def _collect_connected_neighbors(circuit: dict) -> dict[str, set[str]]:
    """收集直接连接的邻居（MIN_SPACING 跳过，与 DRC engine 一致）。"""
    connected_neighbors: dict[str, set[str]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1, d2 = str(conn[0]), str(conn[2])
        connected_neighbors.setdefault(d1, set()).add(d2)
        connected_neighbors.setdefault(d2, set()).add(d1)
    return connected_neighbors


def _place_matrix_devices(
    placements: dict[str, dict[str, float]],
    rc_map: dict[str, tuple[int, int]],
    row_to_idx: dict, col_to_idx: dict,
    base_x: float, base_y: float,
    row_spacing: float, col_spacing: float,
    canvas_w: float, canvas_h: float,
    connected_neighbors: dict[str, set[str]],
) -> None:
    """按行列索引直接放置矩阵器件到规则网格位置（*R05 修复*）。

    ## v1 缺陷（已修复）

    v1 逐个放置器件时检查 _no_overlap_at，若与未移动的 FFDH 残留器件
    位置重叠则跳过。但 FFDH 残留位置散乱，导致大量器件被跳过，
    网格不完整（y range 仅 179μm 而非预期的 357μm）。

    ## v2 修复

    网格本身是规则的（row_spacing/col_spacing = 器件尺寸 + MIN_SPACING），
    同列同 x、同行同 y，按定义不会重叠。直接分配所有器件到目标位置，
    不检查重叠。后续 zigzag 会处理任何残余问题。

    来源（R02）: Clements et al. Optica 2016（规则网格布局）
        https://doi.org/10.1364/OPTICA.3.001460
    """
    for nm, (r, c) in rc_map.items():
        ri = row_to_idx[r]
        ci = col_to_idx[c]
        target_x = base_x + ci * col_spacing
        target_y = base_y + ri * row_spacing
        # 边界检查（画布已自适应扩大，正常不会越界）
        w = float(placements[nm]["w"])
        h = float(placements[nm]["h"])
        if target_x < 0.0:
            target_x = 0.0
        if target_y < 0.0:
            target_y = 0.0
        if target_x + w > canvas_w:
            target_x = max(0.0, canvas_w - w)
        if target_y + h > canvas_h:
            target_y = max(0.0, canvas_h - h)
        placements[nm]["x"] = target_x
        placements[nm]["y"] = target_y


def _align_matrix_grid(
    placements: dict[str, dict[str, float]],
    circuit: dict,
    canvas_w: float,
    canvas_h: float,
) -> None:
    """矩阵型拓扑器件按行列网格对齐（*创新*，R05 Bug 修复）。

    Clements/Reck mesh 中器件以行列网格排列，相邻行列器件端口 y 坐标
    需对齐以减少 PORT_ALIGNMENT 违规。本函数按器件名提取行列索引，
    将器件重新排列到规则网格位置，使同行器件 y 对齐、同列器件 x 等距。

    算法:
    1. 从器件名提取 (row, col) 索引；若器件名不含行列索引（如 PICBench
       的 mzi1/mzi2/...），从连接拓扑推断（``_infer_matrix_grid_from_
       topology``）
    2. 行列重映射为密集索引（0..n-1）
    3. 计算行列间距: ``row_spacing = max(h) + MIN_SPACING``
    4. 画布自适应: 网格超出当前画布则扩大画布（R03 合规，非 fall-back）
    5. 基准位置居中，按行列顺序放置器件

    *创新点*: 经典 FFDH/DREAMPlace 不识别矩阵拓扑，端口 y 坐标散乱
    导致 PORT_ALIGNMENT 违规。本函数利用行列索引直接重建规则网格。

    Args:
        placements: 布局（in-place 修改）。
        circuit: polaris-core 风格 circuit dict（canvas_w/canvas_h 可能
            被 in-place 扩大以适应网格，供后续 stage route/drc 使用）。
        canvas_w: 画布宽 (μm)。
        canvas_h: 画布高 (μm)。

    文献来源见模块顶部 docstring（R02 学术诚信）。
    """
    # 优先用器件名行列索引，其次从拓扑推断
    geometry = _extract_matrix_grid_geometry(placements, canvas_w, canvas_h)
    if geometry is None:
        geometry = _infer_matrix_grid_from_topology(
            placements, circuit, canvas_w, canvas_h
        )
    if geometry is None:
        return  # 非矩阵型拓扑，跳过
    rc_map, row_to_idx, col_to_idx, base_x, base_y, row_spacing, col_spacing = geometry

    # 画布自适应扩大: 网格超出当前画布时，扩大画布（与 DRC DENSITY_MIN
    # 自适应一致，R03 合规）。大矩阵（如 8x8 mesh 28 个 MZI）需要更大画布。
    n_cols = len(col_to_idx)
    n_rows = len(row_to_idx)
    grid_w = n_cols * col_spacing
    grid_h = n_rows * row_spacing
    if grid_w > canvas_w or grid_h > canvas_h:
        canvas_w = max(canvas_w, grid_w + col_spacing)
        canvas_h = max(canvas_h, grid_h + row_spacing)
        circuit["canvas_w"] = float(canvas_w)
        circuit["canvas_h"] = float(canvas_h)
    base_x = max(0.0, (canvas_w - grid_w) / 2.0)
    base_y = max(0.0, (canvas_h - grid_h) / 2.0)

    connected_neighbors = _collect_connected_neighbors(circuit)
    _place_matrix_devices(
        placements, rc_map, row_to_idx, col_to_idx, base_x, base_y,
        row_spacing, col_spacing, canvas_w, canvas_h, connected_neighbors,
    )
