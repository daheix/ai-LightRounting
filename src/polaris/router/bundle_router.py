"""Bundle 布线（R10 路标）—— gdsfactory routing strategies 对齐。

实现多端口对并行布线、等长匹配、路径点布线、自动 taper、Dubins path。

学术来源:
- gdsfactory routing strategies:
  https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
- LiDAR (ISPD 2025) 曲线感知详细布线:
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Dubins, "On Curves of Minimal Length with a Constraint on Average Curvature",
  American J. Math. 1957, 79(3):497-516
  https://www.jstor.org/stable/2372560
- Shkel & Lumelsky, "Classification of the Dubins set",
  Robot. Auton. Syst. 2001, 34(2-3):179-202

无 fall-back 设计（规则 14.1）：所有错误必须 raise，禁止返回部分结果。
"""

from __future__ import annotations

import math

from polaris.router.jps_router import JPSRouter
from polaris.router.path_geometry import equalize_length, path_length

__all__ = [
    "route_bundle",
    "route_bundle_path_length_match",
    "route_bundle_from_waypoints",
    "auto_taper",
    "dubins_path",
]

_TWO_PI = 2.0 * math.pi


def _mod2pi(x: float) -> float:
    """将角度归一化到 [0, 2π)。"""
    return x % _TWO_PI


def _infer_grid(ports1, ports2, margin: int = 5) -> tuple[int, int]:
    """从端口坐标推断网格尺寸（max + margin）。"""
    all_pts = list(ports1) + list(ports2)
    max_x = max(p[0] for p in all_pts) + margin
    max_y = max(p[1] for p in all_pts) + margin
    return max_x, max_y


def _sort_ports(
    ports1: list[tuple[int, int]], ports2: list[tuple[int, int]]
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """端口排序（对齐 gdsfactory sort_ports 逻辑）。

    按 y 坐标分别排序 ports1 和 ports2，使配对端口不交叉。
    乱序输入也能正确配对（最低 y 配最低 y，最高 y 配最高 y）。

    来源: gdsfactory sort_ports 按 bundle 轴的垂直方向排序
    https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
    """
    s1 = sorted(ports1, key=lambda p: p[1])
    s2 = sorted(ports2, key=lambda p: p[1])
    return s1, s2


def _add_path_buffer(
    blocked: set[tuple[int, int]], path: list[tuple[int, int]], separation: int
) -> None:
    """将路径点 + separation 缓冲区加入 blocked 集合（防碰撞）。"""
    for px, py in path:
        for dx in range(-separation, separation + 1):
            for dy in range(-separation, separation + 1):
                blocked.add((px + dx, py + dy))


def _apply_blocked_to_router(
    router: JPSRouter,
    blocked: set[tuple[int, int]],
    all_ports: set[tuple[int, int]],
) -> None:
    """将 blocked 点（非端口）应用到路由器障碍栅格。"""
    w, h = router.grid_w, router.grid_h
    for bp in blocked:
        if bp not in all_ports and 0 <= bp[0] < w and 0 <= bp[1] < h:
            router.obstacle.set(bp[0], bp[1], 1)


def _make_router(router, kwargs) -> JPSRouter:
    """创建或复用路由器。"""
    if router is not None:
        return router
    grid_w = kwargs.get("grid_w")
    grid_h = kwargs.get("grid_h")
    if grid_w is None or grid_h is None:
        raise ValueError("router=None 时必须提供 grid_w 和 grid_h")
    return JPSRouter(int(grid_w), int(grid_h), 1.0, None)


def route_bundle(
    ports1: list[tuple[int, int]],
    ports2: list[tuple[int, int]],
    router: JPSRouter | None = None,
    separation: float = 2.0,
    **kwargs,
) -> list[list[tuple[int, int]]]:
    """多端口对并行布线（对标 gdsfactory route_bundle）。

    端口排序（按 y 配对避免交叉）→ 逐对 JPS 布线 → separation 约束（防碰撞）。
    已布路径的 separation 缓冲区标记为障碍，确保后续路径不靠近。

    Args:
        ports1: 起始端口列表 [(x, y), ...]。
        ports2: 终止端口列表 [(x, y), ...]。
        router: 自定义路由器（需有 route(start, goal) 方法和 obstacle 属性）。
                None 时用 JPSRouter（需在 kwargs 提供 grid_w, grid_h）。
        separation: 波导间距（网格步数，向下取整）。
        **kwargs: grid_w, grid_h（router=None 时必需）。

    Returns:
        路径列表 [[(x, y), ...], ...]，顺序对应排序后的端口对。

    Raises:
        ValueError: 端口数量不匹配 / 缺少 grid_w, grid_h。
        RuntimeError: 某对端口无可行路径（无 fall-back，直接传播）。
    """
    if len(ports1) != len(ports2):
        raise ValueError(
            f"ports1 和 ports2 长度不匹配: {len(ports1)} != {len(ports2)}"
        )
    if not ports1:
        return []
    r = _make_router(router, kwargs)
    sep = max(0, int(separation))
    sorted1, sorted2 = _sort_ports(ports1, ports2)
    blocked: set[tuple[int, int]] = set()
    all_ports = set(ports1) | set(ports2)
    routes: list[list[tuple[int, int]]] = []
    for p1, p2 in zip(sorted1, sorted2, strict=False):
        _apply_blocked_to_router(r, blocked, all_ports)
        path = r.route(p1, p2)  # 失败会 raise RuntimeError（无 fall-back）
        routes.append(path)
        if sep > 0:
            _add_path_buffer(blocked, path, sep)
    return routes


def route_bundle_path_length_match(
    ports1: list[tuple[int, int]],
    ports2: list[tuple[int, int]],
    tolerance: float = 0.5,
    **kwargs,
) -> list[list[tuple[float, float]]]:
    """等长匹配布线（对标 gdsfactory route_bundle_path_length_match）。

    在 route_bundle 基础上，对短路径用 equalize_length 添加蛇形绕行，
    使所有路径长度趋于一致（容差 tolerance）。

    Args:
        ports1: 起始端口列表。
        ports2: 终止端口列表。
        tolerance: 长度匹配容差（μm）。
        **kwargs: 传递给 route_bundle（router, separation, grid_w, grid_h 等）。

    Returns:
        等长匹配后的路径列表（float 坐标）。

    Raises:
        ValueError/RuntimeError: 同 route_bundle。
    """
    routes = route_bundle(ports1, ports2, **kwargs)
    if not routes:
        return []
    float_routes = [[(float(x), float(y)) for x, y in r] for r in routes]
    lengths = [path_length(r) for r in float_routes]
    target = max(lengths)
    detour_step = max(0.25, tolerance / 2.0)
    result: list[list[tuple[float, float]]] = []
    for route, length in zip(float_routes, lengths, strict=False):
        if length < target - tolerance:
            result.append(equalize_length(route, target, detour_step))
        else:
            result.append(route)
    return result


def route_bundle_from_waypoints(
    ports1: list[tuple[int, int]],
    ports2: list[tuple[int, int]],
    waypoints: list[tuple[int, int]],
    **kwargs,
) -> list[list[tuple[int, int]]]:
    """从路径点布线（对标 gdsfactory route_bundle_from_waypoints）。

    每对端口通过共享的 waypoints 序列连接：
    p1 → wp1 → wp2 → ... → wpN → p2，分段 JPS 布线后拼接。

    Args:
        ports1: 起始端口列表。
        ports2: 终止端口列表。
        waypoints: 中间路径点列表 [(x, y), ...]。
        **kwargs: 传递给 _make_router（router, grid_w, grid_h 等）。

    Returns:
        路径列表，每条路径经过所有 waypoints。

    Raises:
        ValueError: 端口数量不匹配 / waypoints 为空 / 缺少 grid_w, grid_h。
        RuntimeError: 任一分段无可行路径。
    """
    if len(ports1) != len(ports2):
        raise ValueError(
            f"ports1 和 ports2 长度不匹配: {len(ports1)} != {len(ports2)}"
        )
    if not waypoints:
        raise ValueError("waypoints 不能为空")
    if not ports1:
        return []
    r = _make_router(kwargs.get("router"), kwargs)
    routes: list[list[tuple[int, int]]] = []
    for p1, p2 in zip(ports1, ports2, strict=False):
        full_wps = [p1] + list(waypoints) + [p2]
        path: list[tuple[int, int]] = []
        for i in range(len(full_wps) - 1):
            seg = r.route(full_wps[i], full_wps[i + 1])
            if i > 0:
                seg = seg[1:]  # 去掉重复的连接点
            path.extend(seg)
        routes.append(path)
    return routes


def auto_taper(
    route: list[tuple[float, float]],
    taper_length: float = 5.0,
    start_width: float = 0.5,
    end_width: float = 1.0,
) -> list[tuple[float, float, float]]:
    """自动在端口与布线间插入 taper（线性宽度过渡）。

    在路径两端各 taper_length 长度内，宽度从 start_width 线性过渡到 end_width，
    中间段保持 end_width。对标 gdsfactory auto_taper。

    来源: https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html

    Args:
        route: 路径点列表 [(x, y), ...]。
        taper_length: taper 段长度（μm）。
        start_width: 端口宽度（μm）。
        end_width: 布线宽度（μm）。

    Returns:
        带 width 的路径 [(x, y, w), ...]。
    """
    if not route:
        return []
    n = len(route)
    if taper_length <= 0:
        return [(x, y, end_width) for x, y in route]
    cum_lens = [0.0]
    for i in range(1, n):
        cum_lens.append(
            cum_lens[-1]
            + math.hypot(route[i][0] - route[i - 1][0], route[i][1] - route[i - 1][1])
        )
    total = cum_lens[-1]
    dw = end_width - start_width
    if total < 2 * taper_length:
        # 路径太短：按索引比例线性过渡
        return [
            (x, y, start_width + dw * (i / max(1, n - 1)))
            for i, (x, y) in enumerate(route)
        ]
    result: list[tuple[float, float, float]] = []
    for i, (x, y) in enumerate(route):
        cl = cum_lens[i]
        if cl <= taper_length:
            w = start_width + dw * (cl / taper_length)
        elif cl >= total - taper_length:
            w = start_width + dw * ((total - cl) / taper_length)
        else:
            w = end_width
        result.append((x, y, w))
    return result


# ---------------------------------------------------------------------------
# Dubins Path（曲率约束最短路径，Dubins 1957）
# ---------------------------------------------------------------------------
def dubins_path(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float = 5.0,
) -> list[tuple[float, float]]:
    """Dubins path 曲线布线（曲率约束最短路径）。

    3 段组成（CSC/CCC），C=圆弧 S=直线。6 种组合：LSL/LSR/RSL/RSR/RLR/LRL，
    取最短者。

    学术来源: Dubins, "On Curves of Minimal Length with a Constraint on
    Average Curvature", American J. Math. 1957, 79(3):497-516.
    实现参考: Shkel & Lumelsky, "Classification of the Dubins set",
    Robot. Auton. Syst. 2001.

    Args:
        start: 起点位姿 (x, y, theta_deg)。
        end: 终点位姿 (x, y, theta_deg)。
        radius: 最小转弯半径（μm）。

    Returns:
        路径点列表 [(x, y), ...]。

    Raises:
        ValueError: radius <= 0。
        RuntimeError: 无可行解（6 种组合均无效）。
    """
    if radius <= 0:
        raise ValueError(f"radius 必须 > 0: {radius}")
    x1, y1, t1 = start
    x2, y2, t2 = end
    t1_rad = math.radians(t1)
    t2_rad = math.radians(t2)
    dx = (x2 - x1) / radius
    dy = (y2 - y1) / radius
    d = math.hypot(dx, dy)
    theta = math.atan2(dy, dx)
    alpha = _mod2pi(t1_rad - theta)
    beta = _mod2pi(t2_rad - theta)
    candidates = _dubins_candidates(alpha, beta, d)
    if not candidates:
        raise RuntimeError(f"Dubins path 无可行解: {start} → {end}")
    best = min(candidates, key=lambda c: c[0])
    _total, path_type, t, p, q = best
    return _dubins_generate(path_type, t, p, q, radius, x1, y1, t1_rad)


def _dubins_candidates(
    alpha: float, beta: float, d: float
) -> list[tuple[float, str, float, float, float]]:
    """计算 6 种 Dubins 路径候选（Shkel & Lumelsky 2001, Algorithm 1）。

    返回 [(total_len, type, t, p, q), ...]，total_len 为归一化总长（弧度）。
    """
    ca, cb = math.cos(alpha), math.cos(beta)
    sa, sb = math.sin(alpha), math.sin(beta)
    cab = math.cos(alpha - beta)
    cands: list[tuple[float, str, float, float, float]] = []

    def add_csc(name, p_sq, tmp_fn, t_fn, q_fn):
        if p_sq >= 0:
            p = math.sqrt(p_sq)
            tmp = tmp_fn(p)
            t, q = _mod2pi(t_fn(tmp)), _mod2pi(q_fn(tmp))
            cands.append((t + p + q, name, t, p, q))

    def add_ccc(name, val, tmp_val, t_fn, q_fn):
        if abs(val) <= 1:
            p = _mod2pi(_TWO_PI - math.acos(val))
            t, q = _mod2pi(t_fn(tmp_val, p)), _mod2pi(q_fn(tmp_val, p))
            cands.append((t + p + q, name, t, p, q))

    # fmt: off
    add_csc("LSL", 2 + d**2 - 2*cab + 2*d*(sa - sb),
            lambda p: math.atan2(cb - ca, d + sa - sb),
            lambda t: -alpha + t, lambda t: beta - t)
    add_csc("RSR", 2 + d**2 - 2*cab + 2*d*(sb - sa),
            lambda p: math.atan2(ca - cb, d - sa + sb),
            lambda t: alpha - t, lambda t: -beta + t)
    add_csc("LSR", -2 + d**2 + 2*cab + 2*d*(sa + sb),
            lambda p: math.atan2(-ca - cb, d + sa + sb) - math.atan2(-2.0, p),
            lambda t: -alpha + t, lambda t: -beta + t)
    add_csc("RSL", -2 + d**2 + 2*cab - 2*d*(sa + sb),
            lambda p: math.atan2(ca + cb, d - sa - sb) - math.atan2(2.0, p),
            lambda t: alpha - t, lambda t: beta - t)
    add_ccc("RLR", (6 - d**2 + 2*cab + 2*d*(sa - sb)) / 8,
            math.atan2(ca - cb, d - sa + sb),
            lambda t, p: alpha - t + p/2, lambda t, p: beta - t + p/2)
    add_ccc("LRL", (6 - d**2 + 2*cab + 2*d*(sb - sa)) / 8,
            math.atan2(-ca + cb, d + sa - sb),
            lambda t, p: -alpha + t - p/2, lambda t, p: -beta + t - p/2)
    # fmt: on
    return cands


def _dubins_generate(
    path_type: str,
    t: float,
    p: float,
    q: float,
    radius: float,
    x0: float,
    y0: float,
    theta0: float,
) -> list[tuple[float, float]]:
    """生成 Dubins 路径点（中点法近似圆弧积分）。

    L=左转（逆时针），R=右转（顺时针），S=直行。
    """
    pts: list[tuple[float, float]] = [(x0, y0)]
    x, y, theta = x0, y0, theta0
    seg_lens = [t * radius, p * radius, q * radius]
    for i, seg_type in enumerate(path_type):
        seg_len = seg_lens[i]
        if seg_len < 1e-9:
            continue
        n_pts = max(2, int(seg_len))
        dlen = seg_len / n_pts
        for _ in range(n_pts):
            if seg_type == "S":
                x += dlen * math.cos(theta)
                y += dlen * math.sin(theta)
            else:
                dtheta = dlen / radius if seg_type == "L" else -dlen / radius
                phi = theta + dtheta / 2
                x += dlen * math.cos(phi)
                y += dlen * math.sin(phi)
                theta += dtheta
            pts.append((x, y))
    return pts
