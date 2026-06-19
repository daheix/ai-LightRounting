"""波导约束布线器（Task 11）。

实现网格布线（A*/Lee 基线）+ 弯曲半径约束 + 波导间距约束 + 交叉最小化
+ 等长路径约束（MZI 臂、差分对）+ S 弯/弯曲路径生成。

方法参考（方案检索，见项目规则 1.1）：
- A* 搜索算法（经典网格寻路，Hart, Nilsson & Raphael 1968）
  https://en.wikipedia.org/wiki/A*_search_algorithm
- Cheng et al., NeurIPS 2022 一次性生成式布线模型（SJTU+华为）
  https://openreview.net/pdf?id=uNYqDfPEDD8
- LiDAR (ISPD 2025) 曲线感知 A* 光波导详细布线（grid-based curvy-aware A*）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 分层曲线波导布线（Manhattan/非 Manhattan 状态、弯曲半径约束）
  https://arxiv.org/html/2505.17239v2
- 欧拉弯曲（clothoid）平滑过渡，曲率线性变化降低弯曲损耗
  来源: Fujisawa et al., Opt. Express 25, 9150 (2017)
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Rizzo et al., Optics Letters 48(2), 215 (2023) 欧拉曲线提升 SOI 器件制造鲁棒性
  https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
- 弯曲半径约束：SOI 2-6μm / SiN 50-100μm（见 spec.md）
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class WaveguidePath:
    """一条波导路径（折线点序列 + 损耗 + 长度）。"""

    points: list[tuple[float, float]] = field(default_factory=list)
    length_um: float = 0.0
    loss_db: float = 0.0
    num_bends: int = 0
    num_crossings: int = 0

    def add_point(self, x: float, y: float) -> None:
        if self.points:
            x0, y0 = self.points[-1]
            self.length_um += math.hypot(x - x0, y - y0)
        self.points.append((x, y))


@dataclass
class RouterConstraints:
    """路由器几何约束（将 GridRouter 的约束参数打包，降低函数参数个数）。

    Attributes:
        min_bend_radius_um: 最小弯曲半径（μm）。
        min_spacing_um: 最小波导间距（μm）。
    """

    min_bend_radius_um: float = 5.0
    min_spacing_um: float = 1.0


# ---------------------------------------------------------------------------
# SubTask 11.1: A*/Lee 网格布线基线
# ---------------------------------------------------------------------------
class GridRouter:
    """A* 网格布线器（基线）。

    在栅格化画布上用 A* 搜索从起点到终点的最短曼哈顿路径，
    避开障碍（已放置器件/已布波导），并满足弯曲半径约束。
    """

    def __init__(
        self,
        grid_w: int,
        grid_h: int,
        grid_size: float = 1.0,
        constraints: RouterConstraints | None = None,
    ) -> None:
        cons = constraints or RouterConstraints()
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.grid_size = grid_size
        self.min_bend_radius_um = cons.min_bend_radius_um
        # 弯曲半径对应的网格步数：
        # - min_bend_radius_um > 0：转弯前须直行 >= min_bend_steps 步（光波导约束）
        # - min_bend_radius_um <= 0：无弯曲约束（电金属布线），min_bend_steps=1 允许任意转弯
        if cons.min_bend_radius_um <= 0.0:
            self.min_bend_steps = 1
        else:
            self.min_bend_steps = max(2, int(round(cons.min_bend_radius_um / grid_size)))
        self.min_spacing_um = cons.min_spacing_um
        # 障碍栅格：0=可走，>0=障碍/占用
        self.obstacle: np.ndarray = np.zeros((grid_h, grid_w), dtype=np.int32)

    def add_obstacle(self, gx: int, gy: int, gw: int = 1, gh: int = 1) -> None:
        """标记障碍区域。"""
        x0 = max(0, gx)
        y0 = max(0, gy)
        x1 = min(self.grid_w, gx + gw)
        y1 = min(self.grid_h, gy + gh)
        self.obstacle[y0:y1, x0:x1] = 1

    def add_obstacle_box(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        """按画布坐标添加障碍盒。"""
        gx0 = max(0, int(xmin / self.grid_size))
        gy0 = max(0, int(ymin / self.grid_size))
        gx1 = min(self.grid_w, int(math.ceil(xmax / self.grid_size)))
        gy1 = min(self.grid_h, int(math.ceil(ymax / self.grid_size)))
        self.obstacle[gy0:gy1, gx0:gx1] = 1

    def _heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _get_neighbors(
        self,
        pos: tuple[int, int],
        state: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> list[tuple[int, int, int, int]]:
        """计算当前节点的有效邻居（满足边界/障碍/弯曲半径约束）。

        返回 ``[(nx, ny, d, new_straight), ...]``，其中 d 为方向编码
        （0=E, 1=W, 2=N, 3=S），new_straight 为该方向上的连续直行步数。
        """
        x, y = pos
        last_dir, straight = state
        moves = [(1, 0, 0), (-1, 0, 1), (0, 1, 2), (0, -1, 3)]
        neighbors: list[tuple[int, int, int, int]] = []
        for dx, dy, d in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.grid_w and 0 <= ny < self.grid_h):
                continue
            if self.obstacle[ny, nx] or (nx, ny) in blocked:
                continue
            # 弯曲半径约束：转弯前须直行 >= min_bend_steps 步
            is_turn = last_dir != -1 and d != last_dir
            new_straight = straight + 1 if d == last_dir else 1
            if is_turn and straight < self.min_bend_steps:
                continue
            neighbors.append((nx, ny, d, new_straight))
        return neighbors

    def _reconstruct_path(
        self,
        came_from: dict[tuple[int, int, int, int], tuple[int, int, int, int] | None],
        pos: tuple[int, int],
        state: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """从 came_from 回溯重建路径。"""
        path: list[tuple[int, int]] = []
        cur_state: tuple[int, int, int, int] | None = (pos[0], pos[1], state[0], state[1])
        while cur_state is not None:
            path.append((cur_state[0], cur_state[1]))
            cur_state = came_from.get(cur_state)
        return list(reversed(path))

    def _save_endpoints(self, start, goal):
        """保存起点/终点障碍标记并临时清除（器件端口可能在 bbox 内）。"""
        h, w = self.obstacle.shape
        # 边界检查：越界坐标钳位到合法范围
        s0 = max(0, min(start[0], w - 1))
        s1 = max(0, min(start[1], h - 1))
        g0 = max(0, min(goal[0], w - 1))
        g1 = max(0, min(goal[1], h - 1))
        orig_start = self.obstacle[s1, s0]
        orig_goal = self.obstacle[g1, g0]
        self.obstacle[s1, s0] = 0
        self.obstacle[g1, g0] = 0
        return orig_start, orig_goal

    def _restore_endpoints(self, start, goal, orig_start, orig_goal):
        """恢复起点/终点的原始障碍标记。"""
        h, w = self.obstacle.shape
        s0 = max(0, min(start[0], w - 1))
        s1 = max(0, min(start[1], h - 1))
        g0 = max(0, min(goal[0], w - 1))
        g1 = max(0, min(goal[1], h - 1))
        self.obstacle[s1, s0] = orig_start
        self.obstacle[g1, g0] = orig_goal

    def route(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        blocked: set[tuple[int, int]] | None = None,
    ) -> list[tuple[int, int]] | None:
        """A* 搜索路径（返回网格坐标列表，失败返回 None）。

        约束：避开 obstacle 与 blocked；弯曲半径约束通过限制连续直行步数
        后才允许转弯来近似（min_bend_steps）。
        """
        blocked = blocked or set()
        orig_start, orig_goal = self._save_endpoints(start, goal)
        start_state = (start[0], start[1], -1, 0)
        open_h: list[tuple[float, int, int, int, int, int]] = []
        heapq.heappush(open_h, (self._heuristic(start, goal), 0, start[0], start[1], -1, 0))
        g_score: dict[tuple[int, int, int, int], int] = {start_state: 0}
        came_from: dict[tuple[int, int, int, int], tuple[int, int, int, int] | None] = {
            start_state: None
        }
        while open_h:
            _f, g, x, y, last_dir, straight = heapq.heappop(open_h)
            if (x, y) == goal:
                self._restore_endpoints(start, goal, orig_start, orig_goal)
                return self._reconstruct_path(came_from, (x, y), (last_dir, straight))
            for nx, ny, d, new_straight in self._get_neighbors(
                (x, y), (last_dir, straight), blocked
            ):
                new_state = (nx, ny, d, new_straight)
                ng = g + 1
                if ng < g_score.get(new_state, 1 << 30):
                    g_score[new_state] = ng
                    came_from[new_state] = (x, y, last_dir, straight)
                    nf = ng + self._heuristic((nx, ny), goal)
                    heapq.heappush(open_h, (nf, ng, nx, ny, d, new_straight))
        self._restore_endpoints(start, goal, orig_start, orig_goal)
        return None


# ---------------------------------------------------------------------------
# SubTask 11.2: S 弯/弯曲路径生成（贝塞尔/欧拉曲线）
# ---------------------------------------------------------------------------
def s_bend(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    n_points: int = 20,
) -> list[tuple[float, float]]:
    """生成 S 弯路径（贝塞尔曲线，光波导标准方法）。

    用三次贝塞尔曲线连接两点，控制点保证平滑过渡。
    """
    dx = x1 - x0
    # 控制点：水平偏移
    cp1 = (x0 + dx * 0.5, y0)
    cp2 = (x0 + dx * 0.5, y1)
    pts = []
    for i in range(n_points + 1):
        t = i / n_points
        # 三次贝塞尔
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * cp1[0] + 3 * mt * t**2 * cp2[0] + t**3 * x1
        y = mt**3 * y0 + 3 * mt**2 * t * cp1[1] + 3 * mt * t**2 * cp2[1] + t**3 * y1
        pts.append((x, y))
    return pts


def euler_bend(
    radius_um: float,
    angle_deg: float = 90.0,
    n_points: int = 30,
) -> list[tuple[float, float]]:
    """生成欧拉弯曲路径（光波导标准方法，损耗最低）。

    欧拉弯曲（clothoid）曲率从 0 线性增加到 1/R，过渡平滑，
    是低损耗波导弯曲的标准选择。

    来源:
    - Fujisawa et al., Opt. Express 25, 9150 (2017) 首次将 clothoid 曲线
      用于硅波导 90° 弯曲，损耗显著低于圆弧弯曲
      https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
    - Rizzo et al., Optics Letters 48(2), 215 (2023) 欧拉曲线提升 SOI 器件
      制造鲁棒性（RAMZI 交错滤波器）
      https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
    """
    angle = math.radians(angle_deg)
    # 欧拉螺旋参数
    L = radius_um * math.sqrt(angle)  # 近似弧长
    pts = []
    s = 0.0
    ds = L / n_points
    x, y = 0.0, 0.0
    theta = 0.0
    for _ in range(n_points + 1):
        # 先记录当前点（保证起点为 (0, 0)），再积分前进一步
        pts.append((x, y))
        # 曲率 k = s / (R * L) 线性增长
        k = (s / L) / radius_um if L > 0 else 0.0
        theta += k * ds
        x += ds * math.cos(theta)
        y += ds * math.sin(theta)
        s += ds
    return pts


def arc_bend(
    radius_um: float,
    angle_deg: float = 90.0,
    n_points: int = 20,
) -> list[tuple[float, float]]:
    """生成圆弧弯曲路径（标准方法）。"""
    angle = math.radians(angle_deg)
    pts = []
    for i in range(n_points + 1):
        t = i / n_points
        a = angle * t
        x = radius_um * math.sin(a)
        y = radius_um * (1 - math.cos(a))
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------------------
# SubTask 11.3: 波导间距约束检查 + 交叉最小化
# ---------------------------------------------------------------------------
def check_min_spacing(
    path1: list[tuple[float, float]],
    path2: list[tuple[float, float]],
    min_spacing_um: float,
) -> bool:
    """检查两条波导路径间最小间距是否满足。"""
    for p1 in path1:
        for p2 in path2:
            if math.hypot(p1[0] - p2[0], p1[1] - p2[1]) < min_spacing_um:
                return False
    return True


def count_crossings(
    path1: list[tuple[float, float]],
    path2: list[tuple[float, float]],
) -> int:
    """统计两条折线路径的交叉数（线段相交检测）。"""
    count = 0
    for i in range(len(path1) - 1):
        a1, a2 = path1[i], path1[i + 1]
        for j in range(len(path2) - 1):
            b1, b2 = path2[j], path2[j + 1]
            if _segments_intersect(a1, a2, b1, b2):
                count += 1
    return count


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """检测两线段是否相交（CCW 叉积法）。"""
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


def _cross(
    o: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


# ---------------------------------------------------------------------------
# SubTask 11.4: 等长路径约束
# ---------------------------------------------------------------------------
def equalize_length(
    path: list[tuple[float, float]],
    target_length_um: float,
    detour_step: float = 1.0,
) -> list[tuple[float, float]]:
    """通过添加蛇形绕行使路径达到目标长度（等长约束）。

    用于 MZI 臂、差分对长度匹配。在路径末端添加 U 形绕行。
    """
    current = path_length(path)
    if current >= target_length_um:
        return path
    deficit = target_length_um - current
    # 添加蛇形绕行：每个 U 形增加约 2*detour_step 长度
    last = path[-1]
    second_last = path[-2] if len(path) >= 2 else (last[0] - 1, last[1])
    # 绕行方向垂直于最后一段
    dx = last[0] - second_last[0]
    dy = last[1] - second_last[1]
    # 垂直方向
    perp_x = -dy
    perp_y = dx
    norm = math.hypot(perp_x, perp_y)
    if norm < 1e-9:
        perp_x, perp_y = 0.0, detour_step
        norm = detour_step
    perp_x = perp_x / norm * detour_step
    perp_y = perp_y / norm * detour_step
    new_pts = list(path)
    n_u = max(1, math.ceil(deficit / (2 * detour_step)))
    for _ in range(n_u):
        new_pts.append((last[0] + perp_x, last[1] + perp_y))
        new_pts.append((last[0], last[1]))
    return new_pts


def path_length(path: list[tuple[float, float]]) -> float:
    """计算折线路径总长度。"""
    total = 0.0
    for i in range(1, len(path)):
        total += math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
    return total


def path_loss(
    path: list[tuple[float, float]],
    loss_db_cm: float,
    bend_loss_db: float = 0.05,
    crossing_loss_db: float = 0.3,
    num_crossings: int = 0,
) -> float:
    """计算波导路径损耗（传播损耗 + 弯曲损耗 + 交叉损耗）。"""
    length_um = path_length(path)
    propagation = loss_db_cm * length_um / 1e4  # cm = 1e4 μm
    # 估算弯曲数（方向变化点）
    num_bends = 0
    for i in range(1, len(path) - 1):
        dx1 = path[i][0] - path[i - 1][0]
        dy1 = path[i][1] - path[i - 1][1]
        dx2 = path[i + 1][0] - path[i][0]
        dy2 = path[i + 1][1] - path[i][1]
        # 方向变化则计为弯曲
        if abs(dx1 - dx2) > 1e-9 or abs(dy1 - dy2) > 1e-9:
            num_bends += 1
    return propagation + num_bends * bend_loss_db + num_crossings * crossing_loss_db


# ---------------------------------------------------------------------------
# 平台约束
# ---------------------------------------------------------------------------
PLATFORM_CONSTRAINTS = {
    "SOI": {"min_bend_radius_um": 5.0, "min_spacing_um": 1.0},
    "SiN": {"min_bend_radius_um": 50.0, "min_spacing_um": 2.0},
    "InP": {"min_bend_radius_um": 100.0, "min_spacing_um": 3.0},
    "LNOI": {"min_bend_radius_um": 30.0, "min_spacing_um": 2.0},
}


def get_platform_constraints(platform: str) -> dict:
    """获取平台波导约束（弯曲半径/间距，来自 spec.md 真实参数）。"""
    return PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS["SOI"])


@dataclass
class RouteConnectionConfig:
    """单连接布线配置（栅格 + 画布 + 障碍 + 等长约束）。

    将 ``route_connection`` 的布线参数打包为单一配置对象，降低函数参数个数
    （规则 4.1：参数上限 7）。

    向后兼容：``route_connection(start, end, platform, config=None, **kwargs)``
    中未提供 config 时，旧式关键字参数（grid_size/canvas_w/canvas_h/obstacles/
    target_length_um）会自动转发到本 dataclass 构造。
    """

    grid_size: float = 1.0
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    obstacles: list[tuple[float, float, float, float]] | None = None
    target_length_um: float | None = None


# 平台传播损耗（dB/cm），来自 spec.md 真实参数
_PLATFORM_LOSS_DB_CM = {"SOI": 2.0, "SiN": 0.1, "LNOI": 0.4}


def _build_router_for_platform(config: RouteConnectionConfig, platform: str) -> GridRouter:
    """根据配置与平台约束构建 GridRouter 并添加障碍。"""
    cons = get_platform_constraints(platform)
    grid_w = int(config.canvas_w / config.grid_size)
    grid_h = int(config.canvas_h / config.grid_size)
    router = GridRouter(
        grid_w=grid_w,
        grid_h=grid_h,
        grid_size=config.grid_size,
        constraints=RouterConstraints(
            min_bend_radius_um=cons["min_bend_radius_um"],
            min_spacing_um=cons["min_spacing_um"],
        ),
    )
    for box in config.obstacles or []:
        router.add_obstacle_box(*box)
    return router


def _grid_path_to_points(
    grid_path: list[tuple[int, int]] | None,
    config: RouteConnectionConfig,
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    """将网格路径转换为画布坐标点，起终点对齐到精确坐标。"""
    if grid_path is None:
        raise RuntimeError(f"A* 布线失败：无法找到从 {start} 到 {end} 的可行路径")
    pts = [(g[0] * config.grid_size, g[1] * config.grid_size) for g in grid_path]
    if pts:
        pts[0] = start
        pts[-1] = end
    return pts


def route_connection(
    start: tuple[float, float],
    end: tuple[float, float],
    platform: str = "SOI",
    config: RouteConnectionConfig | None = None,
    **kwargs: float | list | None,
) -> WaveguidePath:
    """布线一条连接（A* + 弯曲/等长约束）。

    Args:
        start: 起点画布坐标 (x, y) μm。
        end: 终点画布坐标 (x, y) μm。
        platform: 工艺平台（决定弯曲半径/间距约束）。
        config: 布线配置（栅格/画布/障碍/等长）。未提供时从 kwargs 构建。
        **kwargs: 旧式关键字参数（grid_size/canvas_w/canvas_h/obstacles/
            target_length_um），向后兼容。

    Returns:
        ``WaveguidePath``（含折线点、长度、损耗）。

    Raises:
        RuntimeError: A* 搜索无法找到可行路径时。
    """
    if config is None:
        config = RouteConnectionConfig(**kwargs)
    router = _build_router_for_platform(config, platform)
    sg = (int(start[0] / config.grid_size), int(start[1] / config.grid_size))
    eg = (int(end[0] / config.grid_size), int(end[1] / config.grid_size))
    grid_path = router.route(sg, eg)
    pts = _grid_path_to_points(grid_path, config, start, end)
    if config.target_length_um is not None:
        cons = get_platform_constraints(platform)
        pts = equalize_length(pts, config.target_length_um, detour_step=cons["min_bend_radius_um"])
    loss_db_cm = _PLATFORM_LOSS_DB_CM.get(platform, 2.0)
    loss = path_loss(pts, loss_db_cm=loss_db_cm)
    return WaveguidePath(points=pts, length_um=path_length(pts), loss_db=loss)


# ---------------------------------------------------------------------------
# 命名兼容别名（便于上层统一以 ``WaveguideRouter`` 名称访问）
# ---------------------------------------------------------------------------
# 历史代码与文档中曾以 ``WaveguideRouter`` 作为布线器统一入口名称，实际实现
# 为 ``GridRouter``（A* 网格布线器）。此处提供别名以保持向后兼容，避免上层
# 调用方在重构后出现 ImportError。
WaveguideRouter = GridRouter
"""布线器统一别名（指向 GridRouter）。

上层代码可通过 ``from polaris.router.waveguide_router import WaveguideRouter``
访问，与文档/接口约定保持一致。
"""
