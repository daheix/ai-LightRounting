<<<<<<< HEAD
"""全局布线器（Global Router）—— P1-2 差距修复。

实现 Global-Detail 分层布线的全局层：GCell 粗网格 + RUDY 拥塞预估 +
Pattern Routing（L/Z-shape）+ GCell A* + Rip-up&Reroute。
=======
"""全局布线器（Global Router）—— P1-2 差距修复（第5轮）。

实现 Global-Detail 分层布线的全局层：在粗网格（GCell）上做拥塞预估、
网排序、全局路径分配，为详细布线（A*）提供途经点（waypoints）引导。

与商业工具对齐：
- Cadence Innovus New PRO：全局-详细分层布线
- Synopsys ICC2 Zroute：拥塞感知全局布线 + ML DRC 闭合
- LiDAR 2.0 (ISPD 2025)：分层曲线波导布线
  来源: https://arxiv.org/html/2505.17239v2

架构（对齐经典 EDA 全局布线流程）::

    Netlist + Placements
        ↓
    1. GCell 网格构建（粗网格，gcell_size = grid_size * N）
        ↓
    2. RUDY 拥塞预估（DREAMPlace DAC 2020）
        来源: https://arxiv.org/abs/2004.10746
        ↓
    3. 网排序（拥塞感知，难网优先）
        ↓
    4. 全局路径分配（GCell 级 A*，途经点提取）
        ↓
    5. 输出 waypoints 供详细布线（GridRouter）引导
>>>>>>> trae/solo-agent-pkVjID

来源:
- DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
- LiDAR 2.0 分层布线: https://arxiv.org/html/2505.17239v2
<<<<<<< HEAD
- FastGR Pattern Routing: IJCAI 2023
- Cadence Innovus 全局-详细分层
=======
- Cadence Innovus 全局-详细分层: https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
- 经典全局布线教材: "VLSI Physical Design: From Graph Partitioning to Timing Closure"
  https://link.springer.com/book/10.1007/978-90-481-9591-6
>>>>>>> trae/solo-agent-pkVjID
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

import numpy as np

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist, NetlistConnection


@dataclass
class GCell:
<<<<<<< HEAD
    """全局布线单元（Global Routing Cell），粗网格的一个单元。

    Attributes:
        gx, gy: GCell 索引。capacity: 容量。demand: 当前需求。
=======
    """全局布线单元（Global Routing Cell）。

    粗网格的一个单元，包含多个详细布线栅格。
    全局布线在 GCell 级别做路径规划，降低搜索空间复杂度。

    Attributes:
        gx: GCell x 索引。
        gy: GCell y 索引。
        capacity: GCell 容量（可容纳的布线数，基于面积估算）。
        demand: 当前需求（已分配的全局路径数）。
>>>>>>> trae/solo-agent-pkVjID
    """

    gx: int
    gy: int
    capacity: float = 1.0
    demand: float = 0.0

    @property
    def overflow(self) -> float:
        """溢出量（demand - capacity，>0 表示拥塞）。"""
        return max(0.0, self.demand - self.capacity)


@dataclass
class GlobalRoute:
    """一条连接的全局布线结果。

    Attributes:
<<<<<<< HEAD
        conn_idx: 连接索引。gcell_path: GCell 索引序列。
        waypoints: 途经点（μm）。estimated_length_um: 估计长度（μm）。
=======
        conn_idx: 连接索引（对应 netlist.connections 的下标）。
        gcell_path: GCell 索引序列 ``[(gx, gy), ...]``。
        waypoints: 途经点（μm 坐标），供详细布线引导。
        estimated_length_um: 估计长度（μm）。
>>>>>>> trae/solo-agent-pkVjID
    """

    conn_idx: int
    gcell_path: list[tuple[int, int]] = field(default_factory=list)
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    estimated_length_um: float = 0.0


@dataclass
<<<<<<< HEAD
class CurvyPatternConfig:
    """Curvy-Aware Pattern Routing 配置（*创新*，第74轮）。"""

    bend_loss_weight: float = 1.0
    bend_loss_per_corner_db: float = 0.05


@dataclass
=======
>>>>>>> trae/solo-agent-pkVjID
class GlobalRouterConfig:
    """全局布线器配置（规则 4：参数分组降低函数参数数）。

    Attributes:
<<<<<<< HEAD
        gcell_size_um: GCell 边长（μm）。capacity_per_gcell: 基础容量。
        max_rip_reroute_rounds: Rip-up&Reroute 最大轮数。
        congestion_weight: 拥塞代价权重。
=======
        gcell_size_um: GCell 边长（μm），通常为详细栅格的 4-10 倍。
            来源: 经典 EDA 全局布线 GCell 大小经验值。
        capacity_per_gcell: 每个 GCell 的基础容量（可容纳布线数）。
            来源: Innovus 全局布线容量模型。
        max_rip_reroute_rounds: 全局布线 Rip-up&Reroute 最大轮数。
        congestion_weight: 拥塞代价权重（A* 代价 = 长度 + congestion_weight * 拥塞）。
>>>>>>> trae/solo-agent-pkVjID
    """

    gcell_size_um: float = 50.0
    capacity_per_gcell: float = 4.0
    max_rip_reroute_rounds: int = 3
    congestion_weight: float = 2.0
<<<<<<< HEAD
    curvy_pattern: CurvyPatternConfig = field(default_factory=CurvyPatternConfig)
=======
>>>>>>> trae/solo-agent-pkVjID


@dataclass
class CanvasSize:
<<<<<<< HEAD
    """画布尺寸（降低 GlobalRouter.__init__ 参数个数，规则 4.1）。"""
=======
    """画布尺寸（降低 GlobalRouter.__init__ 参数个数，规则 4.1）。

    Attributes:
        width: 画布宽度（μm）。
        height: 画布高度（μm）。
    """
>>>>>>> trae/solo-agent-pkVjID

    width: float
    height: float


class GlobalRouter:
    """全局布线器（Global Router）—— P1-2 差距修复。

<<<<<<< HEAD
    GCell 粗网格 + RUDY 拥塞预估 + Pattern Routing + GCell A* + Rip-up&Reroute。
    对齐 Cadence Innovus / Synopsys ICC2。来源: DREAMPlace RUDY, LiDAR 2.0, FastGR。
=======
    在 GCell 粗网格上做拥塞预估、网排序、全局路径分配，输出途经点
    供详细布线（GridRouter）引导。对齐 Cadence Innovus / Synopsys ICC2
    的全局-详细分层布线架构。

    算法流程::

        1. 构建 GCell 网格（gcell_size_um × gcell_size_um）
        2. RUDY 拥塞预估（对每条连接的 bounding box 均匀分配需求）
        3. 网排序（拥塞感知，难网优先：曼哈顿距离 + 障碍密度降序）
        4. GCell 级 A*（代价 = 长度 + congestion_weight * 拥塞溢出）
        5. Rip-up & Reroute（拥塞溢出时移除冲突路径重布）
        6. 提取途经点（每个 GCell 中心 → waypoints）

    来源:
    - DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
    - LiDAR 2.0 分层布线: https://arxiv.org/html/2505.17239v2
    - Cadence Innovus 全局-详细分层
      https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
>>>>>>> trae/solo-agent-pkVjID
    """

    def __init__(
        self,
        net: Netlist,
        placements: dict[str, Placement],
        canvas: CanvasSize,
        config: GlobalRouterConfig | None = None,
    ) -> None:
<<<<<<< HEAD
        """初始化全局布线器。"""
=======
        """初始化全局布线器。

        Args:
            net: 网表（含连接列表）。
            placements: 器件放置结果（inst_id -> Placement）。
            canvas: 画布尺寸（宽 μm × 高 μm）。
            config: 全局布线配置（None 用默认）。
        """
>>>>>>> trae/solo-agent-pkVjID
        self.net = net
        self.placements = placements
        self.canvas_w = canvas.width
        self.canvas_h = canvas.height
        self.config = config or GlobalRouterConfig()
        self.gcell_size = self.config.gcell_size_um
        self.gw = max(1, int(self.canvas_w / self.gcell_size))
        self.gh = max(1, int(self.canvas_h / self.gcell_size))
<<<<<<< HEAD
=======
        # GCell 网格：capacity 和 demand
>>>>>>> trae/solo-agent-pkVjID
        self.capacity = np.full(
            (self.gh, self.gw), self.config.capacity_per_gcell, dtype=np.float64
        )
        self.demand = np.zeros((self.gh, self.gw), dtype=np.float64)
<<<<<<< HEAD
        self.obstacle_mask = self._build_obstacle_mask()

    def _build_obstacle_mask(self) -> np.ndarray:
        """构建器件障碍掩码（已放置器件占用的 GCell 标记为障碍）。"""
=======
        # 器件障碍标记（已放置器件占用的 GCell）
        self.obstacle_mask = self._build_obstacle_mask()

    def _build_obstacle_mask(self) -> np.ndarray:
        """构建器件障碍掩码（已放置器件占用的 GCell 标记为障碍）。

        Returns:
            布尔数组 ``(gh, gw)``，True 表示该 GCell 被器件占用。
        """
>>>>>>> trae/solo-agent-pkVjID
        mask = np.zeros((self.gh, self.gw), dtype=bool)
        for pl in self.placements.values():
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            gx0 = max(0, int(xmin / self.gcell_size))
            gy0 = max(0, int(ymin / self.gcell_size))
            gx1 = min(self.gw, int(np.ceil(xmax / self.gcell_size)))
            gy1 = min(self.gh, int(np.ceil(ymax / self.gcell_size)))
            mask[gy0:gy1, gx0:gx1] = True
        return mask

    def _port_to_gcell(self, x: float, y: float) -> tuple[int, int]:
<<<<<<< HEAD
        """将端口坐标 (μm) 转换为 GCell 索引 ``(gx, gy)``。"""
=======
        """将端口坐标 (μm) 转换为 GCell 索引。

        Args:
            x: x 坐标（μm）。
            y: y 坐标（μm）。

        Returns:
            ``(gx, gy)`` GCell 索引。
        """
>>>>>>> trae/solo-agent-pkVjID
        gx = min(self.gw - 1, max(0, int(x / self.gcell_size)))
        gy = min(self.gh - 1, max(0, int(y / self.gcell_size)))
        return (gx, gy)

    def _gcell_center(self, gx: int, gy: int) -> tuple[float, float]:
        """返回 GCell 中心坐标（μm）。"""
        return (
            (gx + 0.5) * self.gcell_size,
            (gy + 0.5) * self.gcell_size,
        )

    def _estimate_rudy_congestion(self) -> np.ndarray:
<<<<<<< HEAD
        """RUDY 拥塞预估（DREAMPlace DAC 2020，arxiv:2004.10746），归一化到 [0,1]。"""
=======
        """RUDY 拥塞预估（DREAMPlace DAC 2020）。

        对每条连接的 bounding box 均匀分配 1 单位布线需求到 GCell 网格。
        归一化到 [0, 1]。

        来源: https://arxiv.org/abs/2004.10746

        Returns:
            RUDY 拥塞图 ``(gh, gw)``，值域 [0, 1]。
        """
>>>>>>> trae/solo-agent-pkVjID
        rudy = np.zeros((self.gh, self.gw), dtype=np.float64)
        for conn in self.net.connections:
            start, end = self._conn_endpoints(conn)
            if start is None or end is None:
                continue
            sx, sy = start
            ex, ey = end
            gx0, gy0 = self._port_to_gcell(sx, sy)
            gx1, gy1 = self._port_to_gcell(ex, ey)
            xlo, xhi = min(gx0, gx1), max(gx0, gx1)
            ylo, yhi = min(gy0, gy1), max(gy0, gy1)
            w = max(1, xhi - xlo + 1)
            h = max(1, yhi - ylo + 1)
            # 均匀分配 1 单位需求到 bounding box
            rudy[ylo : yhi + 1, xlo : xhi + 1] += 1.0 / (w * h)
        # 归一化
        max_val = rudy.max()
        if max_val > 0:
            rudy = rudy / max_val
        return rudy

    def _conn_endpoints(
        self, conn: NetlistConnection
    ) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
<<<<<<< HEAD
        """获取连接的起止端口坐标（μm），端口不存在则为 None。"""
=======
        """获取连接的起止端口坐标（μm）。

        Args:
            conn: 网表连接。

        Returns:
            ``(start, end)``，若端口不存在则为 None。
        """
>>>>>>> trae/solo-agent-pkVjID
        start = self._port_abs(conn.src_instance, conn.src_port)
        end = self._port_abs(conn.dst_instance, conn.dst_port)
        return start, end

    def _port_abs(self, inst_id: str, port_name: str) -> tuple[float, float] | None:
<<<<<<< HEAD
        """获取实例某端口的绝对坐标（μm），实例/端口不存在返回 None。"""
=======
        """获取实例某端口的绝对坐标（μm）。

        Args:
            inst_id: 实例 ID。
            port_name: 端口名。

        Returns:
            ``(x, y)`` 或 None（实例/端口不存在）。
        """
>>>>>>> trae/solo-agent-pkVjID
        if inst_id not in self.placements:
            return None
        pl = self.placements[inst_id]
        ports = pl.port_positions()
        if port_name not in ports:
            return None
        return ports[port_name]

    def _sort_connections(self, rudy: np.ndarray) -> list[tuple[int, NetlistConnection, float]]:
<<<<<<< HEAD
        """拥塞感知网排序（难网优先）：曼哈顿距离 + RUDY 拥塞均值（降序）。"""
=======
        """拥塞感知网排序（难网优先）。

        排序键：曼哈顿距离 + bounding box 内 RUDY 拥塞均值（降序）。
        难网（长距离 + 高拥塞区域）先布，避免后续冲突。

        来源: 经典 EDA 全局布线网排序策略。

        Args:
            rudy: RUDY 拥塞图。

        Returns:
            排序后的 ``(conn_idx, conn, difficulty_score)`` 列表。
        """
>>>>>>> trae/solo-agent-pkVjID
        scored: list[tuple[int, NetlistConnection, float]] = []
        for idx, conn in enumerate(self.net.connections):
            start, end = self._conn_endpoints(conn)
            if start is None or end is None:
                continue
<<<<<<< HEAD
            dist = abs(start[0] - end[0]) + abs(start[1] - end[1])
=======
            # 曼哈顿距离（μm）
            dist = abs(start[0] - end[0]) + abs(start[1] - end[1])
            # bounding box 内 RUDY 均值
>>>>>>> trae/solo-agent-pkVjID
            gx0, gy0 = self._port_to_gcell(*start)
            gx1, gy1 = self._port_to_gcell(*end)
            xlo, xhi = min(gx0, gx1), max(gx0, gx1)
            ylo, yhi = min(gy0, gy1), max(gy0, gy1)
            rudy_mean = float(rudy[ylo : yhi + 1, xlo : xhi + 1].mean())
<<<<<<< HEAD
            score = dist + 100.0 * rudy_mean
            scored.append((idx, conn, score))
=======
            # 难度分数 = 距离 + 拥塞权重 * 拥塞
            score = dist + 100.0 * rudy_mean
            scored.append((idx, conn, score))
        # 降序：难网优先
>>>>>>> trae/solo-agent-pkVjID
        scored.sort(key=lambda x: -x[2])
        return scored

    @staticmethod
    def _reconstruct_path(
        goal: tuple[int, int],
        came_from: dict[tuple[int, int], tuple[int, int]],
    ) -> list[tuple[int, int]]:
<<<<<<< HEAD
        """从 came_from 字典重建 GCell 路径列表。"""
=======
        """从 came_from 字典重建路径。

        Args:
            goal: 终点 GCell。
            came_from: 前驱字典。

        Returns:
            GCell 路径列表。
        """
>>>>>>> trae/solo-agent-pkVjID
        path = [goal]
        cur = goal
        while cur in came_from:
            cur = came_from[cur]
            path.append(cur)
        path.reverse()
        return path

    def _astar_neighbors(
        self,
        x: int,
        y: int,
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
<<<<<<< HEAD
        """获取 A* 可扩展的邻居 GCell（跳过越界和障碍，起止 GCell 除外）。"""
=======
        """获取 A* 可扩展的邻居 GCell。

        跳过越界和障碍（起止 GCell 除外）。

        Args:
            x: 当前 GCell x。
            y: 当前 GCell y。
            goal: 终点 GCell（允许通过障碍）。

        Returns:
            可扩展邻居列表 [(nx, ny), ...]。
        """
>>>>>>> trae/solo-agent-pkVjID
        gx, gy = goal
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        neighbors: list[tuple[int, int]] = []
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= self.gw or ny < 0 or ny >= self.gh:
                continue
            # 障碍检查：起止 GCell 允许通过（端口必须可达）
            if self.obstacle_mask[ny, nx] and (nx, ny) != (gx, gy):
                continue
            neighbors.append((nx, ny))
        return neighbors

    def _compute_gcell_step_cost(self, nx: int, ny: int) -> float:
<<<<<<< HEAD
        """计算 GCell A* 步长代价（步长 + 拥塞惩罚）。"""
=======
        """计算 GCell A* 步长代价（步长 + 拥塞惩罚）。

        Args:
            nx: 邻居 GCell x 索引。
            ny: 邻居 GCell y 索引。

        Returns:
            步长代价。
        """
>>>>>>> trae/solo-agent-pkVjID
        step_cost = 1.0
        overflow = max(0.0, self.demand[ny, nx] - self.capacity[ny, nx])
        step_cost += self.config.congestion_weight * overflow
        return step_cost

    def _gcell_astar(
        self,
        start_gcell: tuple[int, int],
        goal_gcell: tuple[int, int],
    ) -> list[tuple[int, int]] | None:
<<<<<<< HEAD
        """GCell 级 A* 全局布线（4 方向，起止 GCell 允许通过障碍）。

        代价 = 步长 + congestion_weight * max(0, demand - capacity)。返回 GCell 路径或 None。
=======
        """GCell 级 A* 全局布线。

        代价 = 步长 + congestion_weight * max(0, demand - capacity)。
        4 方向移动（曼哈顿）。

        注意：起止 GCell（器件端口所在 GCell）即使被标记为障碍也允许通过，
        因为器件端口必须可达。

        Args:
            start_gcell: 起点 GCell。
            goal_gcell: 终点 GCell。

        Returns:
            GCell 路径 ``[(gx, gy), ...]`` 或 None（不可达）。
>>>>>>> trae/solo-agent-pkVjID
        """
        sx, sy = start_gcell
        gx, gy = goal_gcell
        if (sx, sy) == (gx, gy):
            return [(sx, sy)]
        pq = [(abs(sx - gx) + abs(sy - gy), 0.0, sx, sy)]
        came_from: dict = {}
        g_score: dict = {(sx, sy): 0.0}
        visited: set = set()

        while pq:
            _f, g, x, y = heapq.heappop(pq)
            if (x, y) in visited:
                continue
            visited.add((x, y))
            if (x, y) == (gx, gy):
                return self._reconstruct_path((x, y), came_from)
            for nx, ny in self._astar_neighbors(x, y, (gx, gy)):
                ng = g + self._compute_gcell_step_cost(nx, ny)
                if (nx, ny) in g_score and ng >= g_score[(nx, ny)]:
                    continue
                g_score[(nx, ny)] = ng
                came_from[(nx, ny)] = (x, y)
                h = abs(nx - gx) + abs(ny - gy)
                heapq.heappush(pq, (ng + h, ng, nx, ny))
        return None

    def _extract_waypoints(self, gcell_path: list[tuple[int, int]]) -> list[tuple[float, float]]:
<<<<<<< HEAD
        """从 GCell 路径提取途经点（每个 GCell 中心，μm 坐标）。"""
        return [self._gcell_center(gx, gy) for gx, gy in gcell_path]

    def _path_length_um(self, gcell_path: list[tuple[int, int]]) -> float:
        """估计 GCell 路径长度（μm）= 步数 * gcell_size。"""
=======
        """从 GCell 路径提取途经点（每个 GCell 中心，μm 坐标）。

        Args:
            gcell_path: GCell 索引序列。

        Returns:
            途经点列表（μm 坐标）。
        """
        return [self._gcell_center(gx, gy) for gx, gy in gcell_path]

    def _path_length_um(self, gcell_path: list[tuple[int, int]]) -> float:
        """估计 GCell 路径长度（μm）。

        Args:
            gcell_path: GCell 索引序列。

        Returns:
            估计长度（μm），= 步数 * gcell_size。
        """
>>>>>>> trae/solo-agent-pkVjID
        if len(gcell_path) <= 1:
            return 0.0
        return (len(gcell_path) - 1) * self.gcell_size

    def _update_demand(self, gcell_path: list[tuple[int, int]]) -> None:
<<<<<<< HEAD
        """将全局路径的需求累加到 GCell demand。"""
=======
        """将全局路径的需求累加到 GCell demand。

        Args:
            gcell_path: GCell 索引序列。
        """
>>>>>>> trae/solo-agent-pkVjID
        for gx, gy in gcell_path:
            self.demand[gy, gx] += 1.0

    def _reduce_demand(self, gcell_path: list[tuple[int, int]]) -> None:
<<<<<<< HEAD
        """移除全局路径的需求（Rip-up 阶段使用）。"""
=======
        """移除全局路径的需求（Rip-up 阶段使用）。

        Args:
            gcell_path: GCell 索引序列。
        """
>>>>>>> trae/solo-agent-pkVjID
        for gx, gy in gcell_path:
            self.demand[gy, gx] = max(0.0, self.demand[gy, gx] - 1.0)

    def _check_route_overflow(self, gcell_path: list[tuple[int, int]]) -> float:
<<<<<<< HEAD
        """计算路径拥塞溢出总量（demand - capacity 的正部分之和）。"""
=======
        """计算路径拥塞溢出总量。

        Args:
            gcell_path: GCell 路径。

        Returns:
            溢出总量（demand - capacity 的正部分之和）。
        """
>>>>>>> trae/solo-agent-pkVjID
        return sum(
            max(0.0, self.demand[gy, gx] - self.capacity[gy, gx])
            for gx, gy in gcell_path
        )

    def _route_single_connection(
        self,
        conn_idx: int,
        conn: NetlistConnection,
        results: dict[int, GlobalRoute],
        round_idx: int,
    ) -> None:
<<<<<<< HEAD
        """布线单个连接（Pattern Routing 优先 + A* 兜底 + Rip-up&Reroute）。"""
        start, end = self._conn_endpoints(conn)
        if start is None or end is None:
            return
=======
        """布线单个连接（含 Rip-up&Reroute 逻辑）。

        Args:
            conn_idx: 连接索引。
            conn: 连接对象。
            results: 布线结果字典（in-place 更新）。
            round_idx: 当前 Rip-up&Reroute 轮次（0 为首轮）。
        """
        start, end = self._conn_endpoints(conn)
        if start is None or end is None:
            return
        # 已布则跳过（非首轮）
>>>>>>> trae/solo-agent-pkVjID
        if conn_idx in results and round_idx > 0:
            gr = results[conn_idx]
            if self._check_route_overflow(gr.gcell_path) == 0:
                return
<<<<<<< HEAD
=======
            # 拥塞溢出：Rip-up 重布
>>>>>>> trae/solo-agent-pkVjID
            self._reduce_demand(gr.gcell_path)
            del results[conn_idx]
        start_gcell = self._port_to_gcell(*start)
        goal_gcell = self._port_to_gcell(*end)
<<<<<<< HEAD
        # Curvy-Aware Pattern Routing（优先选少弯路径），失败再 A*
        gcell_path = _pattern_route(
            start_gcell, goal_gcell, self.demand, self.capacity,
            self.config.curvy_pattern,
        )
        if gcell_path is None:
            gcell_path = self._gcell_astar(start_gcell, goal_gcell)
=======
        gcell_path = self._gcell_astar(start_gcell, goal_gcell)
>>>>>>> trae/solo-agent-pkVjID
        if gcell_path is None:
            return
        self._update_demand(gcell_path)
        waypoints = self._extract_waypoints(gcell_path)
        est_len = self._path_length_um(gcell_path)
        results[conn_idx] = GlobalRoute(
            conn_idx=conn_idx,
            gcell_path=gcell_path,
            waypoints=waypoints,
            estimated_length_um=est_len,
        )

    def route(self) -> list[GlobalRoute]:
<<<<<<< HEAD
        """执行全局布线（RUDY 预估 + 网排序 + GCell A* + Rip-up&Reroute）。"""
        rudy = self._estimate_rudy_congestion()
        sorted_conns = self._sort_connections(rudy)
=======
        """执行全局布线（含 RUDY 预估 + 网排序 + GCell A* + Rip-up&Reroute）。

        Returns:
            全局布线结果列表（每条连接一个 GlobalRoute）。
        """
        # 1. RUDY 拥塞预估
        rudy = self._estimate_rudy_congestion()
        # 2. 网排序（难网优先）
        sorted_conns = self._sort_connections(rudy)
        # 3. 逐连接 GCell A* + Rip-up&Reroute
>>>>>>> trae/solo-agent-pkVjID
        results: dict[int, GlobalRoute] = {}
        for _round in range(self.config.max_rip_reroute_rounds):
            for conn_idx, conn, _score in sorted_conns:
                self._route_single_connection(conn_idx, conn, results, _round)
<<<<<<< HEAD
=======
            # 检查总溢出
>>>>>>> trae/solo-agent-pkVjID
            total_overflow = float(np.maximum(self.demand - self.capacity, 0).sum())
            if total_overflow == 0:
                break
        return [results[idx] for idx in sorted(results.keys())]

    def congestion_map(self) -> np.ndarray:
<<<<<<< HEAD
        """返回当前 GCell 拥塞图（demand - capacity，>0 为拥塞）。"""
=======
        """返回当前 GCell 拥塞图（demand - capacity，>0 为拥塞）。

        Returns:
            拥塞图 ``(gh, gw)``，正值表示拥塞。
        """
>>>>>>> trae/solo-agent-pkVjID
        return self.demand - self.capacity


def run_global_routing(
    net: Netlist,
    placements: dict[str, Placement],
    canvas: CanvasSize,
    config: GlobalRouterConfig | None = None,
) -> list[GlobalRoute]:
<<<<<<< HEAD
    """便捷函数：执行全局布线并返回结果列表。"""
=======
    """便捷函数：执行全局布线并返回结果。

    Args:
        net: 网表。
        placements: 器件放置。
        canvas: 画布尺寸（宽 μm × 高 μm）。
        config: 全局布线配置（None 用默认）。

    Returns:
        全局布线结果列表。
    """
>>>>>>> trae/solo-agent-pkVjID
    router = GlobalRouter(net, placements, canvas, config)
    return router.route()


<<<<<<< HEAD
def _pattern_route(
    start: tuple[int, int], goal: tuple[int, int],
    demand: np.ndarray, capacity: np.ndarray, curvy: CurvyPatternConfig,
) -> list[tuple[int, int]] | None:
    """Curvy-Aware Pattern Routing（*创新*，第74轮：选最少弯曲路径）。"""
    n_gx, n_gy = demand.shape
    candidates: list[tuple[float, list[tuple[int, int]]]] = []
    for path in _gen_l_shape_paths(start, goal):
        if _path_valid_and_ok(path, demand, capacity, n_gx, n_gy):
            candidates.append((_path_cost(path, curvy), path))
    for path in _gen_z_shape_paths(start, goal):
        if _path_valid_and_ok(path, demand, capacity, n_gx, n_gy):
            candidates.append((_path_cost(path, curvy), path))
    if not candidates:
        return None
    return min(candidates, key=lambda x: x[0])[1]


def _path_cost(path: list[tuple[int, int]], curvy: CurvyPatternConfig) -> float:
    """路径代价 = 长度 + 弯曲损耗权重 × 弯曲数 × 单弯损耗（LiDAR ISPD 2025）。"""
    return len(path) + curvy.bend_loss_weight * _count_bends(path) * curvy.bend_loss_per_corner_db


def _count_bends(path: list[tuple[int, int]]) -> int:
    """统计路径中的转弯数（方向变化次数）。"""
    if len(path) < 3:
        return 0
    bends = 0
    for i in range(1, len(path) - 1):
        dx1 = path[i][0] - path[i-1][0]
        dy1 = path[i][1] - path[i-1][1]
        dx2 = path[i+1][0] - path[i][0]
        dy2 = path[i+1][1] - path[i][1]
        if dx1 != dx2 or dy1 != dy2:
            bends += 1
    return bends


def _gen_l_shape_paths(start: tuple[int, int], goal: tuple[int, int]) -> list[list[tuple[int, int]]]:
    """生成 L-shape 路径候选（单弯，两种方向）。"""
    sx, sy = start
    gx, gy = goal
    return [_fill_path([(sx, sy), (gx, sy), (gx, gy)]),
            _fill_path([(sx, sy), (sx, gy), (gx, gy)])]


def _gen_z_shape_paths(start: tuple[int, int], goal: tuple[int, int]) -> list[list[tuple[int, int]]]:
    """生成 Z-shape 路径候选（双弯，中点分割）。"""
    sx, sy = start
    gx, gy = goal
    mx, my = (sx + gx) // 2, (sy + gy) // 2
    return [_fill_path([(sx, sy), (mx, sy), (mx, gy), (gx, gy)]),
            _fill_path([(sx, sy), (sx, my), (gx, my), (gx, gy)])]


def _fill_path(corners: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """用线性插值填充拐角点之间的 GCell 序列。"""
    full: list[tuple[int, int]] = []
    for i in range(len(corners) - 1):
        _fill_segment(full, corners[i][0], corners[i][1], corners[i+1][0], corners[i+1][1])
    if full and full[-1] != corners[-1]:
        full.append(corners[-1])
    elif not full:
        full = list(corners)
    return full


def _fill_segment(
    full: list[tuple[int, int]],
    x1: int, y1: int, x2: int, y2: int,
) -> None:
    """填充单段路径（水平或垂直）到 full。"""
    if x1 == x2:
        for y in range(y1, y2, 1 if y2 > y1 else -1):
            if not full or full[-1] != (x1, y):
                full.append((x1, y))
    else:
        for x in range(x1, x2, 1 if x2 > x1 else -1):
            if not full or full[-1] != (x, y1):
                full.append((x, y1))


def _path_valid_and_ok(
    path: list[tuple[int, int]], demand: np.ndarray, capacity: np.ndarray,
    n_gx: int, n_gy: int,
) -> bool:
    """检查路径是否在边界内且无拥塞溢出。"""
    for gx, gy in path:
        if not (0 <= gx < n_gx and 0 <= gy < n_gy):
            return False
        if demand[gx, gy] + 1.0 > capacity[gx, gy]:
            return False
    return True


=======
>>>>>>> trae/solo-agent-pkVjID
__all__ = [
    "GCell",
    "GlobalRoute",
    "GlobalRouterConfig",
    "CanvasSize",
    "GlobalRouter",
    "run_global_routing",
]
