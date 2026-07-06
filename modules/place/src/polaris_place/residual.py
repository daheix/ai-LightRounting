"""残余 PORT_ALIGNMENT 违规成对双向修复子模块（polaris-place）。

从 ``analytical.py`` 拆分（R11 质量门禁：单文件 ≤800 行 / 函数 ≤80 行）。
原 ``_residual_pair_fix`` 单函数 293 行（远超 80 行限制），本模块将其
拆分为 4 个子函数 + 1 个主调度函数，保持函数签名不变。

模块结构:
- ``_count_global_unpassed``: 全局未通过 PORT_ALIGNMENT 连接数（评分函数）
- ``_gen_pair_candidates``: 生成 4 类单器件候选移动（d1/d2 × x/y 轴）
- ``_try_single_move``: 单器件候选验证（边界/NO_OVERLAP/最近合法位置/全局评分）
- ``_try_joint_move``: 联合候选验证（d1 与 d2 各移到中点）
- ``_residual_pair_fix``: 主调度（max_iters 趟扫描，全局评分单调非增）

仅依赖 numpy（R04: 不参与 GPU）。

来源（R02 学术诚信，≥5 个文献 URL）:
- PORT_ALIGNMENT 规则: SiEPIC EBeam PDK DRC runset
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 约束优化投影: Boyd & Vandenberghe "Convex Optimization" §4
  https://web.stanford.edu/~boyd/cvxbook/
- AABB 碰撞检测: Ericson "Real-Time Collision Detection" §5.1.3
  https://realtimecollisiondetection.net/
- DREAMPlace TCAD 2020（合法化在约束域内优化）
  https://arxiv.org/abs/2004.10746
- Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Berg "Computational Geometry" Springer（区间合并求可行域）
  https://doi.org/10.1007/978-3-540-77974-2
"""

from __future__ import annotations

from polaris_place.align import _find_port_in_dev, _no_overlap_at
from polaris_place.legalize import (
    _ALIGN_PORT_TOL_UM,
    _find_nearest_legal_pos_1d,
)

__all__ = ["_residual_pair_fix"]


def _count_global_unpassed(
    placements: dict[str, dict[str, float]],
    all_conns: list[tuple[str, str, str, str]],
    device_map: dict[str, dict],
    tol: float,
) -> int:
    """统计当前全局未通过 PORT_ALIGNMENT 的连接数。

    全局评分函数: 接受候选移动的充要条件是全局未通过数严格减少。
    这避免了"修复 A 破坏 B、修复 B 破坏 A"的局部振荡（每次移动
    要求全局改善，单调收敛）。

    Args:
        placements: 当前布局。
        all_conns: 所有连接列表 ``[(d1n, p1n, d2n, p2n), ...]``。
        device_map: 器件名 → 器件规格映射。
        tol: PORT_ALIGNMENT 容差。

    Returns:
        全局未通过连接数。
    """
    count = 0
    for d1n, p1n, d2n, p2n in all_conns:
        if d1n not in placements or d2n not in placements:
            continue
        port1 = _find_port_in_dev(device_map.get(d1n, {}), p1n)
        port2 = _find_port_in_dev(device_map.get(d2n, {}), p2n)
        if port1 is None or port2 is None:
            continue
        pl1 = placements[d1n]
        pl2 = placements[d2n]
        dx = abs((float(pl1["x"]) + port1[0]) - (float(pl2["x"]) + port2[0]))
        dy = abs((float(pl1["y"]) + port1[1]) - (float(pl2["y"]) + port2[1]))
        if dx > tol and dy > tol:
            count += 1
    return count


def _gen_pair_candidates(
    abs1_x: float, abs1_y: float,
    abs2_x: float, abs2_y: float,
    port1: tuple[float, float, str],
    port2: tuple[float, float, str],
    pl1: dict[str, float], pl2: dict[str, float],
    w1: float, h1: float, w2: float, h2: float,
    canvas_w: float, canvas_h: float,
) -> list[tuple[str, float, float, str]]:
    """生成 4 类单器件候选移动: (mover, new_x, new_y, axis)。

    mover='d1' 表示移动 d1，'d2' 表示移动 d2。
    axis='y' 表示主偏差轴为 y（目标 dy ≤ tol），'x' 同理。

    候选生成规则:
    - d2 沿 y 轴对齐 dy=0（保持 d2.x）
    - d2 沿 x 轴对齐 dx=0（保持 d2.y）
    - d1 沿 y 轴对齐 dy=0（保持 d1.x）
    - d1 沿 x 轴对齐 dx=0（保持 d1.y）
    """
    cands: list[tuple[str, float, float, str]] = []
    d1_x, d1_y = float(pl1["x"]), float(pl1["y"])
    d2_x, d2_y = float(pl2["x"]), float(pl2["y"])
    # d2 沿 y 轴对齐 dy=0（保持 d2.x）
    ty = max(0.0, min(abs1_y - port2[1], canvas_h - h2))
    cands.append(("d2", d2_x, ty, "y"))
    # d2 沿 x 轴对齐 dx=0（保持 d2.y）
    tx = max(0.0, min(abs1_x - port2[0], canvas_w - w2))
    cands.append(("d2", tx, d2_y, "x"))
    # d1 沿 y 轴对齐 dy=0（保持 d1.x）
    ty = max(0.0, min(abs2_y - port1[1], canvas_h - h1))
    cands.append(("d1", d1_x, ty, "y"))
    # d1 沿 x 轴对齐 dx=0（保持 d1.y）
    tx = max(0.0, min(abs2_x - port1[0], canvas_w - w1))
    cands.append(("d1", tx, d1_y, "x"))
    return cands


def _resolve_single_move_overlap(
    placements: dict,
    mover_name: str,
    new_x: float, new_y: float,
    w_m: float, h_m: float,
    m_conn: set,
    port_m: tuple,
    axis: str,
    abs_o_x: float, abs_o_y: float,
    canvas_w: float, canvas_h: float,
    tol: float,
) -> tuple[float, float] | None:
    """NO_OVERLAP 失败时，沿主轴找最近合法位置并重新验证。

    Returns:
        (new_x, new_y) 若找到合法位置，None 否则。
    """
    if axis == "y":
        target = new_y
        n2 = _find_nearest_legal_pos_1d(
            placements, mover_name, new_x, new_y, w_m, h_m,
            target, canvas_h, "y", m_conn,
        )
        if n2 is None:
            return None
        new_x2, new_y2 = new_x, n2
    else:
        target = new_x
        n2 = _find_nearest_legal_pos_1d(
            placements, mover_name, new_x, new_y, w_m, h_m,
            target, canvas_w, "x", m_conn,
        )
        if n2 is None:
            return None
        new_x2, new_y2 = n2, new_y
    if (new_x2 < 0.0 or new_x2 + w_m > canvas_w
            or new_y2 < 0.0 or new_y2 + h_m > canvas_h):
        return None
    if not _no_overlap_at(placements, mover_name, new_x2, new_y2, w_m, h_m, m_conn):
        return None
    # 主轴偏差需 ≤ tol（否则无意义）
    if axis == "y":
        dev = abs((new_y2 + port_m[1]) - abs_o_y)
    else:
        dev = abs((new_x2 + port_m[0]) - abs_o_x)
    if dev > tol:
        return None
    return new_x2, new_y2


def _try_single_move(
    placements: dict[str, dict[str, float]],
    mover_name: str,
    w_m: float, h_m: float,
    m_conn: set[str],
    port_m: tuple[float, float, str],
    new_x: float, new_y: float,
    axis: str,
    abs_o_x: float, abs_o_y: float,
    canvas_w: float, canvas_h: float,
    all_conns: list[tuple[str, str, str, str]],
    device_map: dict[str, dict],
    global_cur: int,
    tol: float,
) -> tuple[bool, int, int]:
    """尝试单器件候选移动，全局评分接受准则。

    验证: 边界 → NO_OVERLAP/MIN_SPACING（失败则沿主轴找最近合法位置）→ 全局评分严格减少才接受。

    Args:
        placements: 当前布局（会被临时修改，拒绝时回滚）。
        mover_name: 被移动器件名。
        w_m, h_m: 被移动器件宽高。
        m_conn: 被移动器件的直接连接邻居集合（MIN_SPACING 跳过）。
        port_m: 被移动器件的端口 (dx, dy, direction)。
        new_x, new_y: 候选新位置（左下角）。
        axis: 主偏差轴 'y' 或 'x'。
        abs_o_x, abs_o_y: 对方端口的绝对坐标。
        canvas_w, canvas_h: 画布尺寸。
        all_conns: 所有连接列表（全局评分用）。
        device_map: 器件名 → 器件规格映射。
        global_cur: 当前全局未通过数。
        tol: PORT_ALIGNMENT 容差。

    Returns:
        ``(accepted, fixed_count, new_global_cur)``。
    """
    # 边界
    if (new_x < 0.0 or new_x + w_m > canvas_w
            or new_y < 0.0 or new_y + h_m > canvas_h):
        return False, 0, global_cur
    # NO_OVERLAP/MIN_SPACING（失败则沿主轴找最近合法位置）
    if not _no_overlap_at(placements, mover_name, new_x, new_y, w_m, h_m, m_conn):
        resolved = _resolve_single_move_overlap(
            placements, mover_name, new_x, new_y, w_m, h_m, m_conn,
            port_m, axis, abs_o_x, abs_o_y, canvas_w, canvas_h, tol,
        )
        if resolved is None:
            return False, 0, global_cur
        new_x, new_y = resolved
    # 全局评分接受准则: 临时应用 → 计算全局未通过数 → 严格减少才接受
    saved_x = float(placements[mover_name]["x"])
    saved_y = float(placements[mover_name]["y"])
    placements[mover_name]["x"] = new_x
    placements[mover_name]["y"] = new_y
    global_new = _count_global_unpassed(placements, all_conns, device_map, tol)
    if global_new < global_cur:
        return True, 1, global_new
    placements[mover_name]["x"] = saved_x
    placements[mover_name]["y"] = saved_y
    return False, 0, global_cur


def _try_joint_move_one_axis(
    axis: str,
    placements: dict,
    d1n: str, d2n: str,
    w1: float, h1: float, w2: float, h2: float,
    port1: tuple, port2: tuple,
    abs1_x: float, abs1_y: float,
    abs2_x: float, abs2_y: float,
    d1_conn: set, d2_conn: set,
    canvas_w: float, canvas_h: float,
    all_conns: list, device_map: dict,
    global_cur: int, tol: float,
    saved_d1: tuple, saved_d2: tuple,
    dx: float, dy: float,
) -> tuple[bool, int, int] | None:
    """单轴联合移动: d1/d2 沿主轴移到中点并全局评分。

    Returns:
        (accepted, fixed, new_global) 或 None（该轴已通过，跳过）。
    """
    if axis == "y":
        if dy <= tol:
            return None
        mid = (abs1_y + abs2_y) / 2.0
        new_d1_y = max(0.0, min(mid - port1[1], canvas_h - h1))
        new_d2_y = max(0.0, min(mid - port2[1], canvas_h - h2))
        new_d1_x = saved_d1[0]
        new_d2_x = saved_d2[0]
    else:
        if dx <= tol:
            return None
        mid = (abs1_x + abs2_x) / 2.0
        new_d1_x = max(0.0, min(mid - port1[0], canvas_w - w1))
        new_d2_x = max(0.0, min(mid - port2[0], canvas_w - w2))
        new_d1_y = saved_d1[1]
        new_d2_y = saved_d2[1]
    if (new_d1_x < 0 or new_d1_x + w1 > canvas_w
            or new_d1_y < 0 or new_d1_y + h1 > canvas_h
            or new_d2_x < 0 or new_d2_x + w2 > canvas_w
            or new_d2_y < 0 or new_d2_y + h2 > canvas_h):
        return False, 0, global_cur
    # 临时移走 d2，验证 d1，再恢复 d2 并应用 d1
    placements[d2n]["x"] = -1e6
    placements[d2n]["y"] = -1e6
    ok_d1 = _no_overlap_at(placements, d1n, new_d1_x, new_d1_y, w1, h1, d1_conn)
    placements[d1n]["x"] = new_d1_x
    placements[d1n]["y"] = new_d1_y
    placements[d2n]["x"] = saved_d2[0]
    placements[d2n]["y"] = saved_d2[1]
    if not ok_d1:
        placements[d1n]["x"] = saved_d1[0]
        placements[d1n]["y"] = saved_d1[1]
        return False, 0, global_cur
    # 验证 d2（d1 已在新位置）
    ok_d2 = _no_overlap_at(placements, d2n, new_d2_x, new_d2_y, w2, h2, d2_conn)
    if not ok_d2:
        placements[d1n]["x"] = saved_d1[0]
        placements[d1n]["y"] = saved_d1[1]
        return False, 0, global_cur
    placements[d2n]["x"] = new_d2_x
    placements[d2n]["y"] = new_d2_y
    global_new = _count_global_unpassed(placements, all_conns, device_map, tol)
    if global_new < global_cur:
        return True, 2, global_new
    placements[d1n]["x"] = saved_d1[0]
    placements[d1n]["y"] = saved_d1[1]
    placements[d2n]["x"] = saved_d2[0]
    placements[d2n]["y"] = saved_d2[1]
    return False, 0, global_cur


def _try_joint_move(
    placements: dict[str, dict[str, float]],
    d1n: str, d2n: str,
    w1: float, h1: float, w2: float, h2: float,
    port1: tuple[float, float, str],
    port2: tuple[float, float, str],
    abs1_x: float, abs1_y: float,
    abs2_x: float, abs2_y: float,
    d1_conn: set[str], d2_conn: set[str],
    canvas_w: float, canvas_h: float,
    all_conns: list[tuple[str, str, str, str]],
    device_map: dict[str, dict],
    global_cur: int,
    tol: float,
) -> tuple[bool, int, int]:
    """尝试联合候选移动: d1 和 d2 都沿主轴移到中点。

    *创新*: 当单器件移动会破坏其他连接时，两者各移动一半可使 dy=0
    （或 dx=0）同时减少对各自其他连接的破坏（位移减半）。
    逐轴尝试 y/x，调用 _try_joint_move_one_axis 执行单轴评估。

    Returns:
        ``(accepted, fixed_count, new_global_cur)``：接受=2，拒绝=0。
    """
    dx = abs(abs1_x - abs2_x)
    dy = abs(abs1_y - abs2_y)
    saved_d1 = (float(placements[d1n]["x"]), float(placements[d1n]["y"]))
    saved_d2 = (float(placements[d2n]["x"]), float(placements[d2n]["y"]))
    for axis in ("y", "x"):
        result = _try_joint_move_one_axis(
            axis, placements, d1n, d2n, w1, h1, w2, h2, port1, port2,
            abs1_x, abs1_y, abs2_x, abs2_y, d1_conn, d2_conn,
            canvas_w, canvas_h, all_conns, device_map,
            global_cur, tol, saved_d1, saved_d2, dx, dy,
        )
        if result is not None and result[0]:
            return result
    return False, 0, global_cur


def _collect_residual_conns(circuit: dict) -> list:
    """预构建连接列表（避免重复扫描）。"""
    all_conns: list[tuple[str, str, str, str]] = []
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        all_conns.append((str(conn[0]), conn[1], str(conn[2]), conn[3]))
    return all_conns


def _try_fix_one_residual_conn(
    d1n: str, p1n: str, d2n: str, p2n: str,
    placements: dict,
    device_map: dict,
    connected_neighbors: dict,
    canvas_w: float, canvas_h: float,
    all_conns: list,
    global_cur: int,
    tol: float,
) -> tuple[int, int]:
    """对单个残余违规连接尝试所有候选移动（4 单器件 + 1 联合）。

    Returns:
        ``(fixed, new_global_cur)``: fixed=修复数(0/1/2)。
    """
    if d1n not in placements or d2n not in placements or d1n == d2n:
        return 0, global_cur
    port1 = _find_port_in_dev(device_map.get(d1n, {}), p1n)
    port2 = _find_port_in_dev(device_map.get(d2n, {}), p2n)
    if port1 is None or port2 is None:
        return 0, global_cur
    pl1, pl2 = placements[d1n], placements[d2n]
    abs1_x = float(pl1["x"]) + port1[0]
    abs1_y = float(pl1["y"]) + port1[1]
    abs2_x = float(pl2["x"]) + port2[0]
    abs2_y = float(pl2["y"]) + port2[1]
    dx = abs(abs1_x - abs2_x)
    dy = abs(abs1_y - abs2_y)
    if dx <= tol or dy <= tol:
        return 0, global_cur  # 已通过
    w1, h1 = float(pl1["w"]), float(pl1["h"])
    w2, h2 = float(pl2["w"]), float(pl2["h"])
    d1_conn = connected_neighbors.get(d1n, set())
    d2_conn = connected_neighbors.get(d2n, set())
    cands = _gen_pair_candidates(
        abs1_x, abs1_y, abs2_x, abs2_y, port1, port2,
        pl1, pl2, w1, h1, w2, h2, canvas_w, canvas_h,
    )
    for mover_tag, new_x, new_y, axis in cands:
        if mover_tag == "d1":
            mover_name = d1n
            w_m, h_m, m_conn, port_m = w1, h1, d1_conn, port1
            abs_o_y, abs_o_x = abs2_y, abs2_x
        else:
            mover_name = d2n
            w_m, h_m, m_conn, port_m = w2, h2, d2_conn, port2
            abs_o_y, abs_o_x = abs1_y, abs1_x
        ok, fixed, global_cur = _try_single_move(
            placements, mover_name, w_m, h_m, m_conn, port_m,
            new_x, new_y, axis, abs_o_x, abs_o_y,
            canvas_w, canvas_h, all_conns, device_map, global_cur, tol,
        )
        if ok:
            return fixed, global_cur
    ok, fixed, global_cur = _try_joint_move(
        placements, d1n, d2n, w1, h1, w2, h2, port1, port2,
        abs1_x, abs1_y, abs2_x, abs2_y, d1_conn, d2_conn,
        canvas_w, canvas_h, all_conns, device_map, global_cur, tol,
    )
    return (fixed, global_cur) if ok else (0, global_cur)


def _residual_pair_fix(
    placements: dict[str, dict[str, float]],
    circuit: dict,
    device_map: dict[str, dict],
    connected_neighbors: dict[str, set[str]],
    canvas_w: float,
    canvas_h: float,
    max_iters: int = 4,
) -> int:
    """残余 PORT_ALIGNMENT 违规成对双向修复（*创新*）。

    3 趟 zigzag 仅移动下游 d2；当 d2 被多个已通过连接约束时无法对齐到 d1。
    本函数允许同时移动 d1 和 d2 中任一个，覆盖"双方都被锁住"场景。
    算法: 扫描残余违规 → 4 类单器件候选 → 联合候选 → 全局评分严格减少才接受。
    迭代直到无改进或 max_iters 趟。

    Args:
        placements: 当前布局（已跑过 _align_ports 3 趟 zigzag）。
        circuit: 电路 dict。
        device_map: 器件名 → 器件规格映射。
        connected_neighbors: 器件名 → 直接连接邻居集合（MIN_SPACING 跳过）。
        canvas_w, canvas_h: 画布尺寸。
        max_iters: 最大迭代趟数。

    Returns:
        本轮修复的连接数（int，0 表示无改进）。

    来源（R02）: SiEPIC EBeam PDK DRC runset https://github.com/SiEPIC/SiEPIC_EBeam_PDK ;
        Boyd & Vandenberghe "Convex Optimization" §4 https://web.stanford.edu/~boyd/cvxbook/ ;
        Ericson "Real-Time Collision Detection" §5.1.3 https://realtimecollisiondetection.net/ ;
        DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746 ;
        Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3 https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731 ;
        Berg "Computational Geometry" Springer https://doi.org/10.1007/978-3-540-77974-2
    """
    tol = _ALIGN_PORT_TOL_UM
    if not placements or not circuit.get("connections"):
        return 0
    all_conns = _collect_residual_conns(circuit)
    total_fixed = 0
    for _ in range(max_iters):
        improved = False
        global_cur = _count_global_unpassed(placements, all_conns, device_map, tol)
        if global_cur == 0:
            break
        for d1n, p1n, d2n, p2n in all_conns:
            fixed, global_cur = _try_fix_one_residual_conn(
                d1n, p1n, d2n, p2n, placements, device_map,
                connected_neighbors, canvas_w, canvas_h,
                all_conns, global_cur, tol,
            )
            if fixed > 0:
                total_fixed += fixed
                improved = True
        if not improved:
            break
    return total_fixed
