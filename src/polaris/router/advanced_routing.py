"""R10 路标：gdsfactory routing strategies 对齐。

实现 JPS、Bundle、非曼哈顿、Dubins、Auto Taper、Length Match、自适应交叉。
来源:
- JPS: Harabor & Grastien AAAI 2011, https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
- Curvy A*: LiDAR ISPD 2025, https://dl.acm.org/doi/pdf/10.1145/3698364/3705355
- A*: Hart/Nilsson/Raphael 1968, https://ieeexplore.ieee.org/document/4082128
- Dubins 1957 Am. J. Math. 79(3):497-516; Dubins set: Shkel & Lumelsky 2001
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

__all__ = [
    "AllAngleRouter",
    "BundleRouteResult",
    "JPSRouter",
    "adaptive_crossing_insertion",
    "auto_taper",
    "dubins_path",
    "route_bundle",
    "route_bundle_path_length_match",
]

# 4 方向向量（JPS 标准 4-邻接）：E, W, N, S
_DIRS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
# 8 方向向量（AllAngle 用）：E, W, N, S, NE, NW, SE, SW
_DIRS_8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))
_TWO_PI = 2.0 * math.pi


def _mod2pi(x: float) -> float:
    """将角度归一化到 [0, 2π)。"""
    return x % _TWO_PI


class _GridRouterBase:
    """网格布线器基类（共享障碍管理与边界检查）。所有错误必须 raise，禁止 fall-back。"""

    def __init__(self, grid_width: int, grid_height: int, min_bend_steps: int = 2):
        if grid_width <= 0 or grid_height <= 0:
            raise ValueError(f"网格尺寸必须为正数: {grid_width}x{grid_height}")
        if min_bend_steps < 1:
            raise ValueError(f"min_bend_steps 必须 >= 1: {min_bend_steps}")
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.min_bend_steps = min_bend_steps
        self._obstacles: set[tuple[int, int]] = set()

    def add_obstacle(self, gx: int, gy: int, gw: int = 1, gh: int = 1) -> None:
        """添加障碍（矩形区域）。"""
        for x in range(gx, gx + gw):
            for y in range(gy, gy + gh):
                if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                    self._obstacles.add((x, y))

    def _is_blocked(self, x: int, y: int) -> bool:
        """检查网格点是否为障碍或越界。"""
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return True
        return (x, y) in self._obstacles


# 1.1 JPS (Jump Point Search) 剪枝加速 A*
class JPSRouter(_GridRouterBase):
    """Jump Point Search 布线器（Harabor & Grastien AAAI 2011）。

    通过在线剪枝网格图，将 A* 节点扩展数减少 70-90%。
    来源: https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
    """

    def _is_forced_neighbor(self, x: int, y: int, dx: int, dy: int) -> bool:
        """检查强制邻居（Harabor 2011 §3.1）。"""
        if dx != 0 and dy == 0:
            return (self._is_blocked(x - dx, y - 1) and not self._is_blocked(x, y - 1)) or (
                self._is_blocked(x - dx, y + 1) and not self._is_blocked(x, y + 1)
            )
        if dy != 0 and dx == 0:
            return (self._is_blocked(x - 1, y - dy) and not self._is_blocked(x - 1, y)) or (
                self._is_blocked(x + 1, y - dy) and not self._is_blocked(x + 1, y)
            )
        return False

    def _jump(
        self, x: int, y: int, dx: int, dy: int, goal: tuple[int, int]
    ) -> tuple[int, int] | None:
        """跳跃扩展（JPS 核心）。遇障碍时返回前一个有效点作为边缘跳点。"""
        nx, ny = x + dx, y + dy
        if self._is_blocked(nx, ny):
            return None
        if (nx, ny) == goal or self._is_forced_neighbor(nx, ny, dx, dy):
            return (nx, ny)
        if (dx != 0 and dy == 0 and nx == goal[0]) or (dy != 0 and dx == 0 and ny == goal[1]):
            return (nx, ny)
        result = self._jump(nx, ny, dx, dy, goal)
        return (nx, ny) if result is None else result

    def _prune_directions(self, x: int, y: int, dx: int, dy: int) -> list[tuple[int, int]]:
        """JPS 剪枝规则生成候选方向（含障碍边缘绕行）。"""
        directions: list[tuple[int, int]] = []
        if dx != 0 and dy == 0:
            directions.append((dx, 0))
            if self._is_blocked(x - dx, y - 1) and not self._is_blocked(x, y - 1):
                directions.append((0, -1))
            if self._is_blocked(x - dx, y + 1) and not self._is_blocked(x, y + 1):
                directions.append((0, 1))
            if self._is_blocked(x + dx, y):  # 前方阻塞：添加垂直绕行
                for pd in ((0, -1), (0, 1)):
                    if not self._is_blocked(x + pd[0], y + pd[1]) and pd not in directions:
                        directions.append(pd)
        elif dy != 0 and dx == 0:
            directions.append((0, dy))
            if self._is_blocked(x - 1, y - dy) and not self._is_blocked(x - 1, y):
                directions.append((-1, 0))
            if self._is_blocked(x + 1, y - dy) and not self._is_blocked(x + 1, y):
                directions.append((1, 0))
            if self._is_blocked(x, y + dy):  # 前方阻塞：添加水平绕行
                for pd in ((-1, 0), (1, 0)):
                    if not self._is_blocked(x + pd[0], y + pd[1]) and pd not in directions:
                        directions.append(pd)
        else:
            directions = list(_DIRS_4)
        return directions

    def _get_jump_successors(
        self, x: int, y: int, parent: tuple[int, int] | None, goal: tuple[int, int]
    ) -> list[tuple[int, int]]:
        """获取跳跃后继（JPS 剪枝 + 目标对齐转向）。"""
        if parent is None:
            directions = list(_DIRS_4)
        else:
            px, py = parent
            dx = 0 if x == px else (1 if x > px else -1)
            dy = 0 if y == py else (1 if y > py else -1)
            directions = self._prune_directions(x, y, dx, dy)
        if x == goal[0] and y != goal[1]:
            td = 1 if goal[1] > y else -1
            if (0, td) not in directions:
                directions.append((0, td))
        elif y == goal[1] and x != goal[0]:
            td = 1 if goal[0] > x else -1
            if (td, 0) not in directions:
                directions.append((td, 0))
        successors: list[tuple[int, int]] = []
        for ddx, ddy in directions:
            jp = self._jump(x, y, ddx, ddy, goal)
            if jp is not None:
                successors.append(jp)
        return successors

    def route(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        """JPS 布线，返回路径。Raises RuntimeError(无可行路径)/ValueError(越界/障碍)。"""
        if self._is_blocked(*start):
            raise ValueError(f"起点 {start} 在障碍上或越界")
        if self._is_blocked(*goal):
            raise ValueError(f"终点 {goal} 在障碍上或越界")

        def h(p: tuple[int, int]) -> int:
            return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

        open_h: list[tuple[int, int, tuple[int, int]]] = []
        heapq.heappush(open_h, (h(start), 0, start))
        g_score: dict[tuple[int, int], int] = {start: 0}
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while open_h:
            _f, g, cur = heapq.heappop(open_h)
            if cur == goal:
                path: list[tuple[int, int]] = []
                node: tuple[int, int] | None = cur
                while node is not None:
                    path.append(node)
                    node = came_from[node]
                path.reverse()
                return self._fill_path(path)
            parent = came_from[cur]
            for succ in self._get_jump_successors(cur[0], cur[1], parent, goal):
                step = abs(succ[0] - cur[0]) + abs(succ[1] - cur[1])
                ng = g + step
                if ng < g_score.get(succ, 1 << 30):
                    g_score[succ] = ng
                    came_from[succ] = cur
                    heapq.heappush(open_h, (ng + h(succ), ng, succ))
        raise RuntimeError(f"JPS 无可行路径: {start} → {goal}")

    def _fill_path(self, jump_points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """补全 jump points 之间的直行段中间点。"""
        if len(jump_points) <= 1:
            return list(jump_points)
        path: list[tuple[int, int]] = [jump_points[0]]
        for i in range(1, len(jump_points)):
            px, py = jump_points[i - 1]
            cx, cy = jump_points[i]
            steps = max(abs(cx - px), abs(cy - py))
            dx = 0 if cx == px else (1 if cx > px else -1)
            dy = 0 if cy == py else (1 if cy > py else -1)
            for s in range(1, steps + 1):
                path.append((px + dx * s, py + dy * s))
        return path


# 1.2 Bundle 布线（多端口对并行布线）
@dataclass
class BundleRouteResult:
    """Bundle 布线结果。"""

    routes: list[list[tuple[int, int]]]
    port_pairs: list[tuple[tuple[int, int], tuple[int, int]]]
    success: bool
    failed_pairs: list[int]


def _add_path_buffer(
    blocked: set[tuple[int, int]], path: list[tuple[int, int]], separation: int
) -> None:
    """将路径点 + separation 缓冲区加入 blocked 集合。"""
    for px, py in path:
        for dx in range(-separation, separation + 1):
            for dy in range(-separation, separation + 1):
                blocked.add((px + dx, py + dy))


def route_bundle(
    ports1: list[tuple[int, int]],
    ports2: list[tuple[int, int]],
    grid_width: int,
    grid_height: int,
    separation: int = 3,
    min_bend_steps: int = 2,
    obstacles: list[tuple[int, int, int, int]] | None = None,
) -> BundleRouteResult:
    """多端口对并行布线（对标 gdsfactory route_bundle）。

    端口排序（按 y 配对避免交叉）→ 逐对布线 → separation 约束。
    来源: https://gdsfactory.github.io/gdsfactory/
    Raises: ValueError: ports1/ports2 长度不匹配。
    """
    if len(ports1) != len(ports2):
        raise ValueError(f"ports1 和 ports2 长度不匹配: {len(ports1)} != {len(ports2)}")
    n = len(ports1)
    order = sorted(range(n), key=lambda i: ports1[i][1])
    routes: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    failed_pairs: list[int] = []
    blocked: set[tuple[int, int]] = set()
    all_ports = set(ports1) | set(ports2)  # 端口点不加入 blocked，确保布线可达
    for idx in order:
        p1, p2 = ports1[idx], ports2[idx]
        temp_router = JPSRouter(grid_width, grid_height, min_bend_steps)
        for obs in obstacles or []:
            temp_router.add_obstacle(*obs)
        temp_router._obstacles.update(bp for bp in blocked if bp not in all_ports)
        try:
            path = temp_router.route(p1, p2)
            routes[idx] = path
            _add_path_buffer(blocked, path, separation)
        except RuntimeError:
            failed_pairs.append(idx)
    return BundleRouteResult(routes, list(zip(ports1, ports2)), not failed_pairs, failed_pairs)


# 1.3 非曼哈顿布线（All-Angle Routing）
class AllAngleRouter(_GridRouterBase):
    """非曼哈顿布线器（对标 gdsfactory route_bundle_all_angle）。

    支持任意角度端口布线，使用 8-邻接 A* 算法 + 弯曲半径约束。
    来源: LiDAR ISPD 2025, https://dl.acm.org/doi/pdf/10.1145/3698364/3705355
    """

    def route_all_angle(
        self,
        start: tuple[float, float],
        goal: tuple[float, float],
        start_angle: float = 0.0,
        goal_angle: float = 0.0,
    ) -> list[tuple[float, float]]:
        """非曼哈顿布线（8-邻接 A* + 角度约束）。Raises RuntimeError/ValueError。"""
        sx, sy = int(round(start[0])), int(round(start[1]))
        gx, gy = int(round(goal[0])), int(round(goal[1]))
        if self._is_blocked(sx, sy):
            raise ValueError(f"起点 {start} 在障碍上或越界")
        if self._is_blocked(gx, gy):
            raise ValueError(f"终点 {goal} 在障碍上或越界")
        sqrt2 = math.sqrt(2)

        def h(x: int, y: int) -> float:
            dx = abs(x - gx)
            dy = abs(y - gy)
            return (dx + dy) + (sqrt2 - 2) * min(dx, dy)

        start_state = (sx, sy, -1, 0)
        open_h: list[tuple[float, float, tuple]] = []
        heapq.heappush(open_h, (h(sx, sy), 0.0, start_state))
        g_score: dict[tuple, float] = {start_state: 0.0}
        came_from: dict[tuple, tuple | None] = {start_state: None}
        while open_h:
            _f, g, cur = heapq.heappop(open_h)
            x, y, last_dir, straight = cur
            if (x, y) == (gx, gy):
                states: list[tuple] = []
                node: tuple | None = cur
                while node is not None:
                    states.append(node)
                    node = came_from[node]
                states.reverse()
                return [(float(s[0]), float(s[1])) for s in states]
            for d, (dx, dy) in enumerate(_DIRS_8):
                cost = sqrt2 if dx != 0 and dy != 0 else 1.0
                nx, ny = x + dx, y + dy
                if self._is_blocked(nx, ny):
                    continue
                if dx != 0 and dy != 0:
                    # 对角线移动防止穿墙：检查两个相邻直行格
                    if self._is_blocked(x + dx, y) or self._is_blocked(x, y + dy):
                        continue
                is_turn = last_dir != -1 and d != last_dir
                new_straight = straight + 1 if d == last_dir else 1
                if is_turn and straight < self.min_bend_steps:
                    continue
                new_straight = min(new_straight, self.min_bend_steps)
                new_state = (nx, ny, d, new_straight)
                ng = g + cost
                if ng < g_score.get(new_state, float("inf")):
                    g_score[new_state] = ng
                    came_from[new_state] = cur
                    heapq.heappush(open_h, (ng + h(nx, ny), ng, new_state))
        raise RuntimeError(f"AllAngle 无可行路径: {start} → {goal}")


# 1.4 Dubins Path
def dubins_path(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float = 5.0,
) -> list[tuple[float, float]]:
    """Dubins path 曲线布线（曲率约束最短路径）。

    3 段组成（CSC/CCC），C=圆弧 S=直线。6 种：LSL/LSR/RSL/RSR/RLR/LRL。
    来源: Dubins 1957, Am. J. Math. 79(3):497-516。
    Raises: ValueError(radius<=0), RuntimeError(无可行解)。
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
    """计算 6 种 Dubins 路径候选（Shkel & Lumelsky 2001, Algorithm 1）。"""
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
    add_csc("LSL", 2+d**2-2*cab+2*d*(sa-sb),
            lambda p: math.atan2(cb-ca, d+sa-sb),
            lambda t: -alpha+t, lambda t: beta-t)
    add_csc("RSR", 2+d**2-2*cab+2*d*(sb-sa),
            lambda p: math.atan2(ca-cb, d-sa+sb),
            lambda t: alpha-t, lambda t: -beta+t)
    add_csc("LSR", -2+d**2+2*cab+2*d*(sa+sb),
            lambda p: math.atan2(-ca-cb, d+sa+sb)-math.atan2(-2.0, p),
            lambda t: -alpha+t, lambda t: -beta+t)
    add_csc("RSL", -2+d**2+2*cab-2*d*(sa+sb),
            lambda p: math.atan2(ca+cb, d-sa-sb)-math.atan2(2.0, p),
            lambda t: alpha-t, lambda t: beta-t)
    add_ccc("RLR", (6-d**2+2*cab+2*d*(sa-sb))/8,
            math.atan2(ca-cb, d-sa+sb),
            lambda t, p: alpha-t+p/2, lambda t, p: beta-t+p/2)
    add_ccc("LRL", (6-d**2+2*cab+2*d*(sb-sa))/8,
            math.atan2(-ca+cb, d+sa-sb),
            lambda t, p: -alpha+t-p/2, lambda t, p: -beta+t-p/2)
    # fmt: on
    return cands


def _dubins_generate(
    path_type: str, t: float, p: float, q: float, radius: float, x0: float, y0: float, theta0: float
) -> list[tuple[float, float]]:
    """生成 Dubins 路径点（中点法近似圆弧）。"""
    pts: list[tuple[float, float]] = [(x0, y0)]
    x, y, theta = x0, y0, theta0
    for i, seg_type in enumerate(path_type):
        seg_len = [t, p, q][i] * radius
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


# 1.5 Auto Taper
def auto_taper(
    route: list[tuple[float, float]],
    taper_length: float = 10.0,
    start_width: float = 0.5,
    end_width: float = 1.0,
) -> list[tuple[float, float, float]]:
    """自动在端口与布线间插入 taper（线性过渡）。

    来源: https://gdsfactory.github.io/gdsfactory/
    Returns: 带 width 的路径 [(x, y, w), ...]。
    """
    if not route:
        return []
    n = len(route)
    if taper_length <= 0:
        return [(x, y, end_width) for x, y in route]
    cum_lens = [0.0]
    for i in range(1, n):
        cum_lens.append(
            cum_lens[-1] + math.hypot(route[i][0] - route[i - 1][0], route[i][1] - route[i - 1][1])
        )
    total_len = cum_lens[-1]
    dw = end_width - start_width

    def _width(cl: float) -> float:
        if total_len < 2 * taper_length:
            return start_width + dw * 0.5  # 退化情况：均匀过渡
        if cl <= taper_length:
            return start_width + dw * (cl / taper_length)
        if cl >= total_len - taper_length:
            return start_width + dw * ((total_len - cl) / taper_length)
        return end_width

    if total_len < 2 * taper_length:
        # 路径太短：按索引比例线性过渡
        return [(x, y, start_width + dw * (i / max(1, n - 1))) for i, (x, y) in enumerate(route)]
    return [(x, y, _width(cum_lens[i])) for i, (x, y) in enumerate(route)]


# 1.6 Path Length Match（等长匹配）
def _grid_path_len(path: list[tuple[int, int]]) -> int:
    """计算网格路径曼哈顿长度。"""
    return (
        sum(
            abs(path[i][0] - path[i - 1][0]) + abs(path[i][1] - path[i - 1][1])
            for i in range(1, len(path))
        )
        if len(path) >= 2
        else 0
    )


def _add_detour(
    path: list[tuple[int, int]], deficit: int, max_detour: int
) -> list[tuple[int, int]]:
    """在路径末尾添加蛇形绕线（U 形）使长度增加 deficit。"""
    if deficit <= 0 or not path:
        return list(path)
    new_path = list(path)
    last = new_path[-1]
    sl = new_path[-2] if len(new_path) >= 2 else (last[0] - 1, last[1])
    dx, dy = last[0] - sl[0], last[1] - sl[1]
    perp = (0, 1) if dx != 0 else (1, 0)
    for _ in range(0, min(deficit, max_detour), 4):
        new_path.extend(
            [
                (last[0] + perp[0], last[1] + perp[1]),
                (last[0] - dx + perp[0], last[1] - dy + perp[1]),
                (last[0] - dx, last[1] - dy),
                (last[0], last[1]),
            ]
        )
    return new_path


def route_bundle_path_length_match(
    ports1: list[tuple[int, int]],
    ports2: list[tuple[int, int]],
    grid_width: int,
    grid_height: int,
    separation: int = 3,
    min_bend_steps: int = 2,
    tolerance: float = 1.0,
    max_detour: int = 100,
    obstacles: list[tuple[int, int, int, int]] | None = None,
) -> BundleRouteResult:
    """等长匹配布线（对标 gdsfactory route_bundle_path_length_match）。

    在 bundle 布线基础上，对短路径添加蛇形绕线使所有路径长度一致。
    来源: https://gdsfactory.github.io/gdsfactory/
    """
    bundle = route_bundle(
        ports1, ports2, grid_width, grid_height, separation, min_bend_steps, obstacles
    )
    if not bundle.success:
        return bundle
    lengths = [_grid_path_len(r) for r in bundle.routes]
    target = max(lengths) if lengths else 0
    for i, route in enumerate(bundle.routes):
        if not route:
            continue
        deficit = target - lengths[i]
        if deficit <= tolerance:
            continue
        bundle.routes[i] = _add_detour(route, int(deficit), max_detour)
    return bundle


# 1.7 自适应交叉插入（创新）
def adaptive_crossing_insertion(
    route: list[tuple[int, int]],
    other_routes: list[list[tuple[int, int]]],
    crossing_cost: float = 5.0,
    detour_cost: float = 1.0,
) -> list[tuple[int, int]]:
    """自适应交叉插入（创新）。

    【创新】gdsfactory 无此功能，PoLaRIS 用启发式决策。
    支持理论: PoLaRIS arXiv:2507.22301 "adaptive crossing insertion"。
    绕行代价 > 交叉代价时插入交叉器件，否则绕行。
    """
    if not route:
        return []
    if not other_routes:
        return list(route)
    route_set = set(route)
    crossing_points: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for other in other_routes:
        for pt in other:
            if pt in route_set and pt not in seen:
                crossing_points.append(pt)
                seen.add(pt)
    n_crossings = len(crossing_points)
    if n_crossings == 0:
        return list(route)
    # 决策：绕行代价 = 每个交叉 U 形绕行 4 步 × detour_cost
    total_detour_cost = n_crossings * 4 * detour_cost
    total_crossing_cost = n_crossings * crossing_cost
    if total_detour_cost > total_crossing_cost:
        # 插入交叉：保持原路径（波导交叉器件直接穿过）
        return list(route)
    # 绕行：在交叉点处 U 形绕开
    return _bypass_crossings(list(route), crossing_points)


def _bypass_crossings(
    route: list[tuple[int, int]], crossings: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """在交叉点处插入 U 形绕行点（prev→bypass1→bypass2→bypass3→nxt）。"""
    result = list(route)
    for cp in reversed(crossings):
        idx = next((i for i in range(len(result) - 1, -1, -1) if result[i] == cp), -1)
        if idx <= 0 or idx >= len(result) - 1:
            continue
        prev, nxt = result[idx - 1], result[idx + 1]
        perp = (0, 1) if (cp[0] - prev[0]) != 0 else (1, 0)
        result[idx] = (prev[0] + perp[0], prev[1] + perp[1])
        result.insert(idx + 1, (cp[0] + perp[0], cp[1] + perp[1]))
        result.insert(idx + 2, (nxt[0] + perp[0], nxt[1] + perp[1]))
    return result
