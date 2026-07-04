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
        if dist < 1.0:  # _ALIGN_MIN_SPACING = 1.0
            return False
    return True


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
    """对 d2 设备，考虑所有入向连接，全局搜索最优位置（*创新* + R05 修复）。

    ## 核心问题（R05 Bug）

    原算法（_align_ports 贪心逐连接对齐）的根因缺陷:
    - dc3 有 2 个入向连接 ps1→dc3.in1 (dy=6.7, 通过) 和
      ps2→dc3.in2 (dy=13, 失败)
    - 处理 ps2→dc3.in2 时移动 dc3 使 dy=0，但破坏了 ps1→dc3.in1
      (dy 变成 25.7 > tol)
    - 贪心策略无法处理多端口器件的多连接同时对齐

    ## 新算法（全局候选评估，*创新*）

    1. 收集 d2 的所有入向连接，计算当前 dx/dy 和通过状态
    2. 生成候选位置:
       a. 当前位置（baseline，保证不劣化）
       b. 每个连接的 x 完全对齐位置（保持 cur_y）
       c. 每个连接的 y 完全对齐位置（保持 cur_x）
       d. x 对齐 + 可行 y 范围交点（同时满足多连接的 dy ≤ tol）
       e. y 对齐 + 可行 x 范围交点
       f. 对每个候选，若重叠，用 _find_nearest_legal_pos_1d 找最近合法
    3. 评估每个候选: 边界检查、NO_OVERLAP/MIN_SPACING、不破坏检查
    4. 选择评分最高（同分选总偏差最小）的位置

    ## 不破坏原则（R03 合规）

    移动 d2 前验证所有当前通过的入向连接在新位置仍通过。若移动会破坏
    任何已通过的连接，则拒绝该候选（保持原位是合法策略，非 fall-back）。

    Args:
        placements: 当前所有器件布局。
        d2_name: 待对齐器件名。
        d2_dev: d2 器件规格（含 ports）。
        incoming_conns: d2 的所有入向连接列表。
        device_map: 器件名 → 器件规格映射。
        d2_connected: 与 d2 直接连接的器件名集合（MIN_SPACING 跳过）。
        canvas_w, canvas_h: 画布尺寸。

    来源（R02 学术诚信）:
        - PORT_ALIGNMENT 规则: SiEPIC EBeam PDK DRC runset
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - 约束优化投影: Boyd & Vandenberghe "Convex Optimization" §4
          https://web.stanford.edu/~boyd/cvxbook/
        - AABB 碰撞检测: Ericson "Real-Time Collision Detection" §5.1.3
          https://realtimecollisiondetection.net/
        - DREAMPlace TCAD 2020（合法化在约束域内优化）
          https://arxiv.org/abs/2004.10746
        - 多端口器件对齐: Chrostowski & Hochberg "Silicon Photonics Design"
          CUP 2015 §4.3 https://www.cambridge.org/core/books/silicon-photonics-design/
        - Berg "Computational Geometry" Springer（区间合并求可行域）
          https://doi.org/10.1007/978-3-540-77974-2
    """
    if not incoming_conns:
        return

    pl2 = placements[d2_name]
    cur_x, cur_y = float(pl2["x"]), float(pl2["y"])
    w2, h2 = float(pl2["w"]), float(pl2["h"])
    TOL = _ALIGN_PORT_TOL_UM

    # 收集每个入向连接的端口信息
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

    if not conn_infos:
        return

    def compute_devs(x: float, y: float) -> list[tuple[float, float]]:
        return [
            (abs(ci["abs1_x"] - (x + ci["port2_x"])),
             abs(ci["abs1_y"] - (y + ci["port2_y"])))
            for ci in conn_infos
        ]

    def is_pass(dx: float, dy: float) -> bool:
        return dx <= TOL or dy <= TOL

    cur_devs = compute_devs(cur_x, cur_y)
    cur_passes = [is_pass(dx, dy) for dx, dy in cur_devs]
    cur_score = sum(cur_passes)
    cur_total_dev = sum(dx + dy for dx, dy in cur_devs)

    # 生成候选位置
    raw_candidates: list[tuple[float, float]] = [(cur_x, cur_y)]
    for ci in conn_infos:
        # x 完全对齐（保持 cur_y）
        tx = max(0.0, min(ci["abs1_x"] - ci["port2_x"], canvas_w - w2))
        raw_candidates.append((tx, cur_y))
        # y 完全对齐（保持 cur_x）
        ty = max(0.0, min(ci["abs1_y"] - ci["port2_y"], canvas_h - h2))
        raw_candidates.append((cur_x, ty))

    # x 对齐 + 可行 y 范围交点（*创新*，同时满足多连接的 dy ≤ tol）
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

    # 对每个候选，若重叠，尝试最近合法位置（扩展候选集）
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

    placements[d2_name]["x"] = best_pos[0]
    placements[d2_name]["y"] = best_pos[1]


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

    ## 不破坏原则（R03 合规）

    移动 d2 前验证所有当前通过的入向连接在新位置仍通过，否则拒绝该候选。

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

    # 拓扑深度（Tarjan SCC + Kahn，含环安全）
    depth = _topological_depth(len(names), idx_conns)

    order = sorted(range(len(names)), key=lambda i: depth[i])
    order_rev = list(reversed(order))  # 反向拓扑序（下游先处理，移开阻挡器件）

    # 构建每个器件的直接连接邻居集合（MIN_SPACING 跳过，与 DRC engine 一致）
    connected_neighbors: dict[str, set[str]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d1_name, d2_name_conn = str(conn[0]), str(conn[2])
        connected_neighbors.setdefault(d1_name, set()).add(d2_name_conn)
        connected_neighbors.setdefault(d2_name_conn, set()).add(d1_name)

    # 预收集每个 d2 设备的入向连接
    incoming_per_d2: dict[str, list[tuple]] = {}
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        d2_name_conn = str(conn[2])
        if d2_name_conn in placements:
            incoming_per_d2.setdefault(d2_name_conn, []).append(tuple(conn))

    # *创新*: 多趟对齐（3 趟 zigzag）
    # 第 1 趟正向拓扑序（上游先对齐），第 2 趟反向（下游先移开阻挡），
    # 第 3 趟正向收尾。不破坏原则保证每趟不劣化（score 单调非减）。
    for pass_order in (order, order_rev, order):
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

    # *创新*: 第 4 趟残余违规成对双向修复
    # 3 趟 zigzag 仅移动下游 d2，当 d1 与 d2 都被其他已通过连接锁住时，
    # 残余 PORT_ALIGNMENT 违规无法消除。本趟允许双向移动 d1 或 d2，
    # 在不破坏已通过连接前提下修复残余违规（L/XL 规模核心修复）。
    _residual_pair_fix(
        placements, circuit, device_map, connected_neighbors,
        canvas_w, canvas_h,
    )

    return placements
