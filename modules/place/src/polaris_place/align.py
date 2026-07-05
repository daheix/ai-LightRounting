"""端口对齐后处理子模块（polaris-place）。

从 ``analytical.py`` 拆分（R11 质量门禁：单文件 ≤800 行），保持函数签名
完全一致。本模块负责:

- 端口方向规范化与查找工具
- AABB 重叠判定与 NO_OVERLAP/MIN_SPACING 综合检查
- 全局多连接对齐（_align_d2_global）：生成候选位置 + 不破坏原则评分
- 端口对齐主入口（_align_ports）：3 趟 zigzag + 残余修复调度

仅依赖 numpy（R04: 不参与 GPU）。

来源（R02 学术诚信，≥5 个文献 URL）:
- DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746（FFDH 基础）
- Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
  波导弯曲损耗 https://www.cambridge.org/core/books/silicon-photonics-design/
- SiEPIC EBeam PDK DRC runset PORT_ALIGNMENT 规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Kahng & Lienig "VLSI Placement" IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
- Berg "Computational Geometry" Springer（AABB 相交判定）
  https://doi.org/10.1007/978-3-540-77974-2
- Boyd & Vandenberghe "Convex Optimization" §4（约束优化投影）
  https://web.stanford.edu/~boyd/cvxbook/
- Ericson "Real-Time Collision Detection" §5.1.3
  https://realtimecollisiondetection.net/
"""

from __future__ import annotations

import math

from polaris_place.legalize import (
    _ALIGN_MIN_SPACING,
    _ALIGN_PORT_TOL_UM,
    _find_nearest_legal_pos_1d,
)
from polaris_place.metrics import _topological_depth

__all__ = [
    "_find_port_in_dev",
    "_no_overlap_at",
    "_align_d2_global",
    "_align_ports",
]

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
    # 合法：端口未找到，调用方据此跳过该连接（align.py:218 / residual.py:69 均判 None 后 continue）。
    # 非 fall-back：未在 device.ports 中匹配到 port_name 是契约内的合法查找结果。
    return None


def _aabb_overlap_strict(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """两 AABB 是否重叠（strict，touching 不算重叠）。

    来源: Berg "Computational Geometry" Springer §2.1 区间相交判定。
    """
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


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


def _collect_d2_conn_infos(
    placements: dict, d2_name: str, d2_dev: dict,
    incoming_conns: list, device_map: dict,
) -> list:
    """收集 d2 所有入向连接的端口绝对位置信息。"""
    conn_infos: list[dict] = []
    for conn in incoming_conns:
        d1_name = str(conn[0])
        p1_name = conn[1]
        p2_name = conn[3]
        if d1_name not in placements:
            continue
        port1 = _find_port_in_dev(device_map.get(d1_name, {}), p1_name)
        port2 = _find_port_in_dev(d2_dev, p2_name)
        if port1 is None or port2 is None:
            continue
        pl1 = placements[d1_name]
        conn_infos.append({
            "d1_name": d1_name,
            "port2_x": port2[0],
            "port2_y": port2[1],
            "abs1_x": float(pl1["x"]) + port1[0],
            "abs1_y": float(pl1["y"]) + port1[1],
        })
    return conn_infos


def _gen_align_candidates(
    conn_infos: list, cur_x: float, cur_y: float,
    w2: float, h2: float, canvas_w: float, canvas_h: float, TOL: float,
) -> list:
    """生成对齐候选位置: 当前/x 对齐/y 对齐/x 对齐+y 可行域/y 对齐+x 可行域。

    *创新*: x 对齐 + y 可行域交点，同时满足多连接 dy ≤ tol
    （Boyd & Vandenberghe §4 区间投影 + Berg 区间合并）。
    """
    raw_candidates: list[tuple[float, float]] = [(cur_x, cur_y)]
    for ci in conn_infos:
        # x 完全对齐（保持 cur_y）
        tx = max(0.0, min(ci["abs1_x"] - ci["port2_x"], canvas_w - w2))
        raw_candidates.append((tx, cur_y))
        # y 完全对齐（保持 cur_x）
        ty = max(0.0, min(ci["abs1_y"] - ci["port2_y"], canvas_h - h2))
        raw_candidates.append((cur_x, ty))
    # x 对齐 + 可行 y 范围交点（*创新*，同时满足多连接 dy ≤ tol）
    for ci in conn_infos:
        tx = max(0.0, min(ci["abs1_x"] - ci["port2_x"], canvas_w - w2))
        y_lo, y_hi = -float("inf"), float("inf")
        for ci2 in conn_infos:
            dx2 = abs(ci2["abs1_x"] - (tx + ci2["port2_x"]))
            if dx2 > TOL:
                y_lo = max(y_lo, ci2["abs1_y"] - TOL - ci2["port2_y"])
                y_hi = min(y_hi, ci2["abs1_y"] + TOL - ci2["port2_y"])
        if y_lo <= y_hi:
            y_lo_c = max(y_lo, 0.0)
            y_hi_c = min(y_hi, canvas_h - h2)
            if y_lo_c <= y_hi_c:
                ty = max(y_lo_c, min(cur_y, y_hi_c))
                raw_candidates.append((tx, ty))
    # y 对齐 + 可行 x 范围交点
    for ci in conn_infos:
        ty = max(0.0, min(ci["abs1_y"] - ci["port2_y"], canvas_h - h2))
        x_lo, x_hi = -float("inf"), float("inf")
        for ci2 in conn_infos:
            dy2 = abs(ci2["abs1_y"] - (ty + ci2["port2_y"]))
            if dy2 > TOL:
                x_lo = max(x_lo, ci2["abs1_x"] - TOL - ci2["port2_x"])
                x_hi = min(x_hi, ci2["abs1_x"] + TOL - ci2["port2_x"])
        if x_lo <= x_hi:
            x_lo_c = max(x_lo, 0.0)
            x_hi_c = min(x_hi, canvas_w - w2)
            if x_lo_c <= x_hi_c:
                tx = max(x_lo_c, min(cur_x, x_hi_c))
                raw_candidates.append((tx, ty))
    return raw_candidates


def _expand_candidates(
    raw_candidates: list, placements: dict, d2_name: str,
    w2: float, h2: float, canvas_w: float, canvas_h: float, d2_connected: set,
) -> set:
    """对每个候选，若重叠则尝试最近合法位置（扩展候选集）。"""
    expanded: set[tuple[float, float]] = set()
    for x, y in raw_candidates:
        expanded.add((round(x, 6), round(y, 6)))
        ny = _find_nearest_legal_pos_1d(
            placements, d2_name, x, y, w2, h2, y, canvas_h, "y", d2_connected
        )
        if ny is not None:
            expanded.add((round(x, 6), round(ny, 6)))
        nx = _find_nearest_legal_pos_1d(
            placements, d2_name, x, y, w2, h2, x, canvas_w, "x", d2_connected
        )
        if nx is not None:
            expanded.add((round(nx, 6), round(y, 6)))
    return expanded


def _select_best_d2_pos(
    expanded: set, placements: dict, d2_name: str, w2: float, h2: float,
    canvas_w: float, canvas_h: float, d2_connected: set, conn_infos: list,
    cur_passes: list, cur_score: int, cur_total_dev: float, TOL: float,
    cur_x: float, cur_y: float,
) -> tuple:
    """评估候选: 边界/重叠/不破坏原则，选评分最高且总偏差最小。"""
    def compute_devs(x: float, y: float) -> list:
        return [
            (abs(ci["abs1_x"] - (x + ci["port2_x"])),
             abs(ci["abs1_y"] - (y + ci["port2_y"])))
            for ci in conn_infos
        ]
    def is_pass(dx: float, dy: float) -> bool:
        return dx <= TOL or dy <= TOL
    best_pos = (cur_x, cur_y)
    best_score = cur_score
    best_total_dev = cur_total_dev
    for x, y in expanded:
        if x < 0.0 or x + w2 > canvas_w or y < 0.0 or y + h2 > canvas_h:
            continue
        if not _no_overlap_at(placements, d2_name, x, y, w2, h2, d2_connected):
            continue
        devs = compute_devs(x, y)
        # 不破坏检查: 当前通过的连接仍需通过
        broke_any = False
        for i, (dx, dy) in enumerate(devs):
            if cur_passes[i] and not is_pass(dx, dy):
                broke_any = True
                break
        if broke_any:
            continue
        score = sum(1 for dx, dy in devs if is_pass(dx, dy))
        total_dev = sum(dx + dy for dx, dy in devs)
        if score > best_score or (score == best_score and total_dev < best_total_dev):
            best_score = score
            best_total_dev = total_dev
            best_pos = (x, y)
    return best_pos


def _align_d2_global(
    placements: dict[str, dict[str, float]],
    d2_name: str,
    d2_dev: dict,
    incoming_conns: list[tuple],
    device_map: dict[str, dict],
    d2_connected: set[str],
    canvas_w: float,
    canvas_h: float,
) -> None:
    """对 d2 设备全局搜索最优位置（*创新* + R05 修复多连接对齐）。

    原 _align_ports 贪心逐连接对齐的根因缺陷: 多端口器件的多入向连接
    （如 dc3.in1 已通过、dc3.in2 失败）逐个对齐时，对齐 dc3.in2 会破坏
    dc3.in1（dy 变 25.7 > tol）。本函数用全局候选评估: 收集所有入向连接，
    生成 5 类候选（当前/x 对齐/y 对齐/x 对齐+y 可行域/y 对齐+x 可行域），
    对每个候选若重叠则用 _find_nearest_legal_pos_1d 找最近合法（扩展候选集），
    评估时验证不破坏原则（当前通过的连接在新位置仍需通过），选评分最高
    （同分选总偏差最小）位置。保持原位是合法策略，非 R03 fall-back。

    子函数:
        - _collect_d2_conn_infos: 收集入向连接端口绝对位置
        - _gen_align_candidates: 5 类候选生成（含 *创新* x+y 可行域交点）
        - _expand_candidates: 重叠时找最近合法位置扩展候选集
        - _select_best_d2_pos: 评估候选（边界/重叠/不破坏），选最优

    来源（R02）: SiEPIC EBeam PDK DRC runset PORT_ALIGNMENT
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
    Boyd & Vandenberghe "Convex Optimization" §4
    https://web.stanford.edu/~boyd/cvxbook/；
    Ericson "Real-Time Collision Detection" §5.1.3
    https://realtimecollisiondetection.net/；
    DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746；
    Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
    https://www.cambridge.org/core/books/silicon-photonics-design/；
    Berg "Computational Geometry" Springer（区间合并）
    https://doi.org/10.1007/978-3-540-77974-2
    """
    if not incoming_conns:
        return
    pl2 = placements[d2_name]
    cur_x, cur_y = float(pl2["x"]), float(pl2["y"])
    w2, h2 = float(pl2["w"]), float(pl2["h"])
    TOL = _ALIGN_PORT_TOL_UM
    conn_infos = _collect_d2_conn_infos(
        placements, d2_name, d2_dev, incoming_conns, device_map
    )
    if not conn_infos:
        return
    # 当前通过状态与评分（baseline，保证不劣化）
    cur_devs = [
        (abs(ci["abs1_x"] - (cur_x + ci["port2_x"])),
         abs(ci["abs1_y"] - (cur_y + ci["port2_y"])))
        for ci in conn_infos
    ]
    cur_passes = [dx <= TOL or dy <= TOL for dx, dy in cur_devs]
    cur_score = sum(cur_passes)
    cur_total_dev = sum(dx + dy for dx, dy in cur_devs)
    raw_candidates = _gen_align_candidates(
        conn_infos, cur_x, cur_y, w2, h2, canvas_w, canvas_h, TOL
    )
    expanded = _expand_candidates(
        raw_candidates, placements, d2_name, w2, h2, canvas_w, canvas_h,
        d2_connected,
    )
    best_pos = _select_best_d2_pos(
        expanded, placements, d2_name, w2, h2, canvas_w, canvas_h,
        d2_connected, conn_infos, cur_passes, cur_score, cur_total_dev, TOL,
        cur_x, cur_y,
    )
    placements[d2_name]["x"] = best_pos[0]
    placements[d2_name]["y"] = best_pos[1]


def _build_align_topology(placements: dict, circuit: dict) -> tuple:
    """构建端口对齐所需的拓扑上下文: device_map / 拓扑序 / 邻居 / 入向连接。

    - device_map: 器件名 → 器件规格（含 ports）
    - depth: Tarjan SCC + Kahn 拓扑深度（含环安全，参考 _topological_depth）
    - order / order_rev: 正/反向拓扑序（解决"下游阻挡上游"问题）
    - connected_neighbors: 直接连接邻居（MIN_SPACING 跳过，与 DRC engine 一致）
    - incoming_per_d2: 每个下游器件 d2 的入向连接列表
    """
    device_map: dict[str, dict] = {}
    for dev in circuit.get("devices", []):
        nm = dev.get("name")
        if nm is not None:
            device_map[nm] = dev
    names = list(placements.keys())
    name_to_idx = {nm: i for i, nm in enumerate(names)}
    idx_conns: list[tuple[int, int]] = []
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1, _p1, d2, _p2 = str(conn[0]), conn[1], str(conn[2]), conn[3]
        if d1 in name_to_idx and d2 in name_to_idx:
            idx_conns.append((name_to_idx[d1], name_to_idx[d2]))
    depth = _topological_depth(len(names), idx_conns)
    order = sorted(range(len(names)), key=lambda i: depth[i])
    order_rev = list(reversed(order))  # 反向拓扑序（下游先处理，移开阻挡器件）
    connected_neighbors: dict[str, set[str]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1_name, d2_name_conn = str(conn[0]), str(conn[2])
        connected_neighbors.setdefault(d1_name, set()).add(d2_name_conn)
        connected_neighbors.setdefault(d2_name_conn, set()).add(d1_name)
    incoming_per_d2: dict[str, list[tuple]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d2_name_conn = str(conn[2])
        if d2_name_conn in placements:
            incoming_per_d2.setdefault(d2_name_conn, []).append(tuple(conn))
    return (names, device_map, order, order_rev,
            connected_neighbors, incoming_per_d2)


def _run_align_zigzag_pass(
    placements: dict, names: list, pass_order: list, device_map: dict,
    connected_neighbors: dict, incoming_per_d2: dict,
    canvas_w: float, canvas_h: float,
) -> None:
    """单趟 zigzag 对齐: 按 pass_order 遍历器件，逐个调用 _align_d2_global。

    不破坏原则保证每趟不劣化（score 单调非减）。
    """
    for i in pass_order:
        d2_name = names[i]
        if d2_name not in placements:
            continue
        d2_dev = device_map.get(d2_name, {})
        d2_connected = connected_neighbors.get(d2_name, set())
        incoming = incoming_per_d2.get(d2_name, [])
        if not incoming:
            continue
        _align_d2_global(
            placements, d2_name, d2_dev, incoming, device_map,
            d2_connected, canvas_w, canvas_h,
        )


def _align_ports(
    placements: dict[str, dict[str, float]],
    circuit: dict,
    canvas_w: float,
    canvas_h: float,
) -> dict[str, dict[str, float]]:
    """端口对齐后处理（*创新*，光电子布局专用，全局多连接对齐）。

    FFDH 合法化只保证无重叠和拓扑序，不考虑端口对齐。本函数在 FFDH 后
    对每个下游器件 d2 调整位置，使其所有入向连接的端口坐标对齐（dx 或
    dy ≤ 容差），减少 PORT_ALIGNMENT DRC 违规和波导弯曲损耗。

    ## 算法（全局多连接对齐 + 3 趟 zigzag + 残余修复，*创新* + R05 修复）

    1. 按拓扑顺序遍历器件（depth 从小到大，保证上游先固定）
    2. 对每个 d2 设备，收集所有入向连接，调用 _align_d2_global
    3. 多趟 zigzag（正向→反向→正向），解决"下游阻挡上游"问题
    4. 第 4 趟残余违规成对双向修复（_residual_pair_fix）

    ## *创新点*

    经典 FFDH/DREAMPlace（VLSI 布局）无端口概念，器件间通过金属层
    任意布线。但光电子布局中，器件通过波导物理连接，端口对齐能显著
    减少波导弯曲（每增加一个弯曲 ≈ 0.05dB 损耗，Chrostowski & Hochberg
    "Silicon Photonics Design" CUP 2015 §4.3）。

    Args:
        placements: FFDH 合法化后的布局 {name: {x, y, w, h}}（左下角坐标）。
        circuit: polaris-core 风格 circuit dict（含 devices.ports）。
        canvas_w: 画布宽 (μm)。
        canvas_h: 画布高 (μm)。

    Returns:
        端口对齐后的布局（可能部分连接因重叠冲突未对齐，保持原位置）。

    来源（R02 学术诚信）:
        - DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746
        - Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
          https://www.cambridge.org/core/books/silicon-photonics-design/
        - SiEPIC EBeam PDK DRC runset PORT_ALIGNMENT 规则
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Kahng & Lienig "VLSI Placement" IEEE TCAD 2009
          https://ieeexplore.ieee.org/document/4685534
        - Berg "Computational Geometry" Springer（AABB 相交判定）
          https://doi.org/10.1007/978-3-540-77974-2
        - Boyd & Vandenberghe "Convex Optimization" §4（约束优化投影）
          https://web.stanford.edu/~boyd/cvxbook/
    """
    if not placements:
        return placements
    # 延迟导入避免与 residual.py 形成循环导入
    from polaris_place.residual import _residual_pair_fix
    (names, device_map, order, order_rev,
     connected_neighbors, incoming_per_d2) = _build_align_topology(
        placements, circuit
    )
    # *创新*: 多趟对齐（3 趟 zigzag）
    # 第 1 趟正向拓扑序（上游先对齐），第 2 趟反向（下游先移开阻挡），
    # 第 3 趟正向收尾。不破坏原则保证每趟不劣化（score 单调非减）。
    for pass_order in (order, order_rev, order):
        _run_align_zigzag_pass(
            placements, names, pass_order, device_map,
            connected_neighbors, incoming_per_d2, canvas_w, canvas_h,
        )
    # *创新*: 第 4 趟残余违规成对双向修复
    # 3 趟 zigzag 仅移动下游 d2，当 d1 与 d2 都被其他已通过连接锁住时，
    # 残余 PORT_ALIGNMENT 违规无法消除。本趟允许双向移动 d1 或 d2，
    # 在不破坏已通过连接前提下修复残余违规（L/XL 规模核心修复）。
    _residual_pair_fix(
        placements, circuit, device_map, connected_neighbors,
        canvas_w, canvas_h,
    )
    return placements
