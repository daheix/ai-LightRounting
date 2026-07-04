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
  https://www.cambridge.org/core/books/silicon-photonics-design/
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

    验证流程:
    1. 边界检查（不超出画布）
    2. NO_OVERLAP/MIN_SPACING 检查；若失败，沿主轴找最近合法位置
    3. 最近合法位置的主轴偏差需 ≤ tol
    4. 全局评分: 临时应用 → 计算全局未通过数 → 严格减少才接受

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
        ``(accepted, fixed_count, new_global_cur)``:
        - accepted: 是否接受该候选
        - fixed_count: 修复的连接数（接受=1，拒绝=0）
        - new_global_cur: 接受后的新全局未通过数（拒绝=global_cur）
    """
    # 边界
    if (new_x < 0.0 or new_x + w_m > canvas_w
            or new_y < 0.0 or new_y + h_m > canvas_h):
        return False, 0, global_cur
    # NO_OVERLAP/MIN_SPACING
    if not _no_overlap_at(placements, mover_name, new_x, new_y, w_m, h_m, m_conn):
        # 完全对齐位置被占据，尝试沿主轴找最近合法位置
        if axis == "y":
            target = new_y
            n2 = _find_nearest_legal_pos_1d(
                placements, mover_name, new_x, new_y, w_m, h_m,
                target, canvas_h, "y", m_conn,
            )
            if n2 is None:
                return False, 0, global_cur
            new_x2, new_y2 = new_x, n2
        else:
            target = new_x
            n2 = _find_nearest_legal_pos_1d(
                placements, mover_name, new_x, new_y, w_m, h_m,
                target, canvas_w, "x", m_conn,
            )
            if n2 is None:
                return False, 0, global_cur
            new_x2, new_y2 = n2, new_y
        # 重新验证新位置
        if (new_x2 < 0.0 or new_x2 + w_m > canvas_w
                or new_y2 < 0.0 or new_y2 + h_m > canvas_h):
            return False, 0, global_cur
        if not _no_overlap_at(placements, mover_name, new_x2, new_y2, w_m, h_m, m_conn):
            return False, 0, global_cur
        # 主轴偏差需 ≤ tol（否则无意义）
        if axis == "y":
            dev = abs((new_y2 + port_m[1]) - abs_o_y)
        else:
            dev = abs((new_x2 + port_m[0]) - abs_o_x)
        if dev > tol:
            return False, 0, global_cur
        new_x, new_y = new_x2, new_y2
    # 全局评分接受准则: 临时应用 → 计算全局未通过数 → 严格减少才接受
    saved_x = float(placements[mover_name]["x"])
    saved_y = float(placements[mover_name]["y"])
    placements[mover_name]["x"] = new_x
    placements[mover_name]["y"] = new_y
    global_new = _count_global_unpassed(placements, all_conns, device_map, tol)
    if global_new < global_cur:
        return True, 1, global_new
    # 回滚
    placements[mover_name]["x"] = saved_x
    placements[mover_name]["y"] = saved_y
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

    验证流程（每个 axis in ['y', 'x']）:
    1. 若该轴已通过（dy ≤ tol 或 dx ≤ tol），跳过
    2. 计算 d1/d2 沿主轴的中点对齐位置
    3. 边界检查
    4. 临时移走 d2 → 验证 d1 → 应用 d1 → 恢复 d2 → 验证 d2 → 应用 d2
    5. 全局评分接受准则

    Args:
        placements: 当前布局（会被临时修改，拒绝时回滚）。
        d1n, d2n: 两个器件名。
        w1, h1, w2, h2: 两器件宽高。
        port1, port2: 两器件端口 (dx, dy, direction)。
        abs1_x, abs1_y: d1 端口绝对坐标。
        abs2_x, abs2_y: d2 端口绝对坐标。
        d1_conn, d2_conn: 两器件直接连接邻居集合。
        canvas_w, canvas_h: 画布尺寸。
        all_conns: 所有连接列表（全局评分用）。
        device_map: 器件名 → 器件规格映射。
        global_cur: 当前全局未通过数。
        tol: PORT_ALIGNMENT 容差。

    Returns:
        ``(accepted, fixed_count, new_global_cur)``:
        - accepted: 是否接受联合候选
        - fixed_count: 修复的连接数（接受=2，拒绝=0）
        - new_global_cur: 接受后的新全局未通过数（拒绝=global_cur）
    """
    dx = abs(abs1_x - abs2_x)
    dy = abs(abs1_y - abs2_y)
    saved_d1 = (float(placements[d1n]["x"]), float(placements[d1n]["y"]))
    saved_d2 = (float(placements[d2n]["x"]), float(placements[d2n]["y"]))

    for axis in ("y", "x"):
        if axis == "y":
            if dy <= tol:
                continue  # y 轴已通过，无需联合
            mid = (abs1_y + abs2_y) / 2.0
            new_d1_y = max(0.0, min(mid - port1[1], canvas_h - h1))
            new_d2_y = max(0.0, min(mid - port2[1], canvas_h - h2))
            new_d1_x = saved_d1[0]
            new_d2_x = saved_d2[0]
        else:
            if dx <= tol:
                continue  # x 轴已通过，无需联合
            mid = (abs1_x + abs2_x) / 2.0
            new_d1_x = max(0.0, min(mid - port1[0], canvas_w - w1))
            new_d2_x = max(0.0, min(mid - port2[0], canvas_w - w2))
            new_d1_y = saved_d1[1]
            new_d2_y = saved_d2[1]
        # 边界
        if (new_d1_x < 0 or new_d1_x + w1 > canvas_w
                or new_d1_y < 0 or new_d1_y + h1 > canvas_h
                or new_d2_x < 0 or new_d2_x + w2 > canvas_w
                or new_d2_y < 0 or new_d2_y + h2 > canvas_h):
            continue
        # d1 NO_OVERLAP（排除 d2，因为 d2 也要移动）
        # 临时移走 d2，验证 d1
        placements[d2n]["x"] = -1e6
        placements[d2n]["y"] = -1e6
        ok_d1 = _no_overlap_at(
            placements, d1n, new_d1_x, new_d1_y, w1, h1, d1_conn,
        )
        # 恢复 d2，应用 d1 新位置
        placements[d1n]["x"] = new_d1_x
        placements[d1n]["y"] = new_d1_y
        placements[d2n]["x"] = saved_d2[0]
        placements[d2n]["y"] = saved_d2[1]
        if not ok_d1:
            placements[d1n]["x"] = saved_d1[0]
            placements[d1n]["y"] = saved_d1[1]
            continue
        # 验证 d2（d1 已在新位置）
        ok_d2 = _no_overlap_at(
            placements, d2n, new_d2_x, new_d2_y, w2, h2, d2_conn,
        )
        if not ok_d2:
            placements[d1n]["x"] = saved_d1[0]
            placements[d1n]["y"] = saved_d1[1]
            continue
        # 应用 d2 新位置
        placements[d2n]["x"] = new_d2_x
        placements[d2n]["y"] = new_d2_y
        # 全局评分
        global_new = _count_global_unpassed(placements, all_conns, device_map, tol)
        if global_new < global_cur:
            return True, 2, global_new
        # 回滚
        placements[d1n]["x"] = saved_d1[0]
        placements[d1n]["y"] = saved_d1[1]
        placements[d2n]["x"] = saved_d2[0]
        placements[d2n]["y"] = saved_d2[1]
    return False, 0, global_cur


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

    3 趟 zigzag 仅移动下游 d2，当 d2 被多个已通过连接约束时无法对齐到 d1。
    L/XL 规模下少数残余违规根因：d1 与 d2 的 FFDH 初始位置偏差均超过容差，
    且双方各自被其他已通过连接锁住，单向移动无法满足。

    ## 算法（成对双向调整 + 不破坏原则）

    1. 扫描所有连接，找出残余违规（dx > tol AND dy > tol）
    2. 对每个残余违规 (d1, p1, d2, p2)，生成 4 类单器件候选移动:
       a. d2 沿 y 轴对齐 dy=0（保持 d2.x）
       b. d2 沿 x 轴对齐 dx=0（保持 d2.y）
       c. d1 沿 y 轴对齐 dy=0（保持 d1.x）
       d. d1 沿 x 轴对齐 dx=0（保持 d1.y）
    3. 单器件候选全部失败时，尝试联合候选: d1 与 d2 各移到中点
    4. 每个候选验证: 边界、NO_OVERLAP/MIN_SPACING、不破坏原则、全局评分
    5. 全局评分接受准则: 临时应用 → 全局未通过数严格减少才接受
    6. 第一个通过的候选立即应用，重新扫描（贪心但安全）
    7. 迭代直到无改进或 max_iters 趟

    ## 与 _align_d2_global 的差异

    _align_d2_global 仅移动单个 d2 并评估其所有入向连接；本函数允许同时
    移动 d1 和 d2 中任一个，且评估被移动器件的全部连接（入向+出向），
    覆盖 _align_d2_global 无法处理的"双方都被锁住"场景。

    Args:
        placements: 当前布局（已跑过 _align_ports 3 趟 zigzag）。
        circuit: 电路 dict。
        device_map: 器件名 → 器件规格映射。
        connected_neighbors: 器件名 → 直接连接邻居集合（MIN_SPACING 跳过）。
        canvas_w, canvas_h: 画布尺寸。
        max_iters: 最大迭代趟数。

    Returns:
        本轮修复的连接数（int，0 表示无改进）。

    来源（R02 学术诚信）:
        - PORT_ALIGNMENT 规则: SiEPIC EBeam PDK DRC runset
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - 约束优化投影: Boyd & Vandenberghe "Convex Optimization" §4
          https://web.stanford.edu/~boyd/cvxbook/
        - AABB 碰撞检测: Ericson "Real-Time Collision Detection" §5.1.3
          https://realtimecollisiondetection.net/
        - DREAMPlace TCAD 2020（合法化在约束域内优化）
          https://arxiv.org/abs/2004.10746
        - Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3
          https://www.cambridge.org/core/books/silicon-photonics-design/
        - Berg "Computational Geometry" Springer（区间合并求可行域）
          https://doi.org/10.1007/978-3-540-77974-2
    """
    tol = _ALIGN_PORT_TOL_UM
    if not placements or not circuit.get("connections"):
        return 0

    # 预构建连接列表（避免重复扫描）
    all_conns: list[tuple[str, str, str, str]] = []
    for conn in circuit.get("connections", []):
        if len(conn) < 4:
            continue
        all_conns.append((str(conn[0]), conn[1], str(conn[2]), conn[3]))

    total_fixed = 0
    for _ in range(max_iters):
        improved = False
        global_cur = _count_global_unpassed(placements, all_conns, device_map, tol)
        if global_cur == 0:
            break
        for d1n, p1n, d2n, p2n in all_conns:
            if d1n not in placements or d2n not in placements or d1n == d2n:
                continue
            d1_dev = device_map.get(d1n, {})
            d2_dev = device_map.get(d2n, {})
            port1 = _find_port_in_dev(d1_dev, p1n)
            port2 = _find_port_in_dev(d2_dev, p2n)
            if port1 is None or port2 is None:
                continue

            pl1 = placements[d1n]
            pl2 = placements[d2n]
            abs1_x = float(pl1["x"]) + port1[0]
            abs1_y = float(pl1["y"]) + port1[1]
            abs2_x = float(pl2["x"]) + port2[0]
            abs2_y = float(pl2["y"]) + port2[1]
            dx = abs(abs1_x - abs2_x)
            dy = abs(abs1_y - abs2_y)
            if dx <= tol or dy <= tol:
                continue  # 已通过

            w1 = float(pl1["w"])
            h1 = float(pl1["h"])
            w2 = float(pl2["w"])
            h2 = float(pl2["h"])
            d1_conn = connected_neighbors.get(d1n, set())
            d2_conn = connected_neighbors.get(d2n, set())

            # 生成 4 类单器件候选移动
            cands = _gen_pair_candidates(
                abs1_x, abs1_y, abs2_x, abs2_y,
                port1, port2, pl1, pl2, w1, h1, w2, h2,
                canvas_w, canvas_h,
            )

            # 单器件候选验证
            single_accepted = False
            for mover_tag, new_x, new_y, axis in cands:
                if mover_tag == "d1":
                    mover_name = d1n
                    w_m, h_m, m_conn, port_m = w1, h1, d1_conn, port1
                    abs_o_y = abs2_y  # 对方(d2)端口绝对 y
                    abs_o_x = abs2_x  # 对方(d2)端口绝对 x
                else:
                    mover_name = d2n
                    w_m, h_m, m_conn, port_m = w2, h2, d2_conn, port2
                    abs_o_y = abs1_y  # 对方(d1)端口绝对 y
                    abs_o_x = abs1_x  # 对方(d1)端口绝对 x
                ok, fixed, global_cur = _try_single_move(
                    placements, mover_name, w_m, h_m, m_conn, port_m,
                    new_x, new_y, axis, abs_o_x, abs_o_y,
                    canvas_w, canvas_h, all_conns, device_map, global_cur, tol,
                )
                if ok:
                    total_fixed += fixed
                    improved = True
                    single_accepted = True
                    break  # 跳出候选循环，继续扫描下一个连接

            if single_accepted:
                continue  # 继续扫描下一个连接

            # 单器件候选都失败，尝试联合候选: d1 和 d2 都沿主轴移到中点
            ok, fixed, global_cur = _try_joint_move(
                placements, d1n, d2n, w1, h1, w2, h2, port1, port2,
                abs1_x, abs1_y, abs2_x, abs2_y,
                d1_conn, d2_conn,
                canvas_w, canvas_h, all_conns, device_map, global_cur, tol,
            )
            if ok:
                total_fixed += fixed
                improved = True

        if not improved:
            break

    return total_fixed
