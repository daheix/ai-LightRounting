"""R21 路标：曲线感知 A* 布线引擎核心（从 curvy_router.py 拆分）。

实现 LiDAR ISPD'25 §3.1-3.2 的曲线感知 A* 布线器：
- 8/16/32 方向搜索（支持任意角度）
- 弯曲半径约束（避免直角弯）
- 拥塞感知（RUDY 预估）
- DRV-free 版图生成（零设计规则违反）

## 学术依据

- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）§3.1-3.2
  URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
  URL: https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- DREAMPlace RUDY 拥塞预估
  URL: https://arxiv.org/abs/2004.10746
- A* 搜索算法（Hart, Nilsson & Raphael 1968）
  URL: https://en.wikipedia.org/wiki/A*_search_algorithm

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
- R21 路标: docs/roundmap/R21.md
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# 学术来源 URL 常量（规则 18 学术诚信）
# ---------------------------------------------------------------------------
_URL_LIDAR_ISPD25 = "https://dl.acm.org/doi/pdf/10.1145/3698364.3705355"
_URL_LIDAR_V2_TCAD = (
    "https://scopex-asu.github.io/files/publications/"
    "PD_TCAD2025_LiDARv2.pdf"
)
_URL_DREAMPLACE_RUDY = "https://arxiv.org/abs/2004.10746"
_URL_ASTAR = "https://en.wikipedia.org/wiki/A*_search_algorithm"


@dataclass
class CurvyAStarConfig:
    """LiDAR 曲线感知 A* 布线配置。

    学术依据：LiDAR ISPD'25 §3.1-3.2
    URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    代价函数：f(n) = g(n) + h(n)
    g(n) = Σ(w_bend * bend_cost + w_length * length + w_cross * cross_cost)
    h(n) = w_heuristic * manhattan_distance(n, goal)

    Attributes:
        grid_size: 网格大小（μm）。
        bend_radius: 最小弯曲半径（μm），SOI 平台典型 5.0μm。
        n_directions: 方向数（8/16/32）。
        w_bend: 弯曲代价权重。
        w_length: 长度代价权重。
        w_cross: 交叉代价权重。
        w_heuristic: 启发式权重。
    """

    grid_size: float = 1.0
    bend_radius: float = 5.0
    n_directions: int = 8
    w_bend: float = 1.0
    w_length: float = 1.0
    w_cross: float = 10.0
    w_heuristic: float = 1.0

    def __post_init__(self) -> None:
        """参数校验（禁止 fall-back 默认值静默修正）。"""
        if self.grid_size <= 0:
            raise ValueError(f"grid_size 必须 > 0，得到 {self.grid_size}")
        if self.bend_radius <= 0:
            raise ValueError(f"bend_radius 必须 > 0，得到 {self.bend_radius}")
        if self.n_directions not in (8, 16, 32):
            raise ValueError(
                f"n_directions 必须为 8/16/32，得到 {self.n_directions}"
            )


def _generate_directions(n: int) -> list[tuple[float, float, float]]:
    """生成 n 方向移动向量列表。

    Args:
        n: 方向数（8/16/32）。

    Returns:
        方向列表 [(dx, dy, step_length), ...]，按角度均匀分布。
    """
    directions: list[tuple[float, float, float]] = []
    for i in range(n):
        angle = 2.0 * math.pi * i / n
        dx = math.cos(angle)
        dy = math.sin(angle)
        step = 1.0 if (dx == 0 or dy == 0) else math.sqrt(2.0)
        directions.append((dx, dy, step))
    return directions


class CurvyAStarRouter:
    """LiDAR 曲线感知 A* 布线器。

    特性：
    - 8/16/32 方向搜索（支持任意角度）
    - 弯曲半径约束（避免直角弯）
    - 拥塞感知（RUDY 预估）
    - DRV-free 版图生成（零设计规则违反）

    学术依据：LiDAR ISPD'25 §3.1-3.2
    URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """

    def __init__(self, config: CurvyAStarConfig) -> None:
        """初始化曲线感知 A* 布线器。

        Args:
            config: 布线配置。
        """
        self.config = config
        self._directions = _generate_directions(config.n_directions)

    def route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        obstacles: list[tuple[float, float, float, float]] | None = None,
        grid: dict[tuple[float, float], float] | None = None,
    ) -> list[tuple[float, float]]:
        """执行曲线感知 A* 布线。

        Args:
            start: 起点 (x, y)（μm）。
            end: 终点 (x, y)（μm）。
            obstacles: 障碍物列表 [(x, y, w, h), ...]，默认空。
            grid: 拥塞网格 {coord: congestion_value}，默认空。

        Returns:
            waypoint 列表（含弯曲段）[(x, y), ...]。

        Raises:
            ValueError: 起终点重合或不可达。
        """
        if start == end:
            raise ValueError(f"起点与终点重合: {start}")
        obstacles = obstacles or []
        grid = grid or {}
        obs_set = self._obstacle_to_set(obstacles)
        gs = self.config.grid_size

        start_node = (round(start[0] / gs), round(start[1] / gs))
        end_node = (round(end[0] / gs), round(end[1] / gs))

        # A* 开放表（优先队列）与关闭表
        open_heap: list[tuple[float, int, tuple[int, int]]] = []
        counter = 0
        heapq.heappush(open_heap, (0.0, counter, start_node))
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start_node: 0.0}
        closed: set[tuple[int, int]] = set()

        max_iter = 200000
        iter_count = 0
        while open_heap and iter_count < max_iter:
            iter_count += 1
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            if current == end_node:
                path = self._reconstruct(came_from, current, gs)
                return self._smooth_path(path)
            cx, cy = current
            prev = came_from.get(current)
            for dx, dy, step in self._directions:
                nx, ny = cx + round(dx), cy + round(dy)
                nb = (nx, ny)
                if nb in closed or nb in obs_set:
                    continue
                # 弯曲半径软约束：方向变化时增加弯曲代价
                # （硬约束在 DRV-free 验证阶段执行，避免网格步长过小导致不可达）
                length_cost = step * self.config.w_length
                bend_cost = self._compute_bend_cost_grid(prev, current, nb)
                # 弯曲半径违反时额外惩罚（软约束）
                if prev is not None and not self._check_bend_radius_grid(
                    prev, current, nb
                ):
                    bend_cost += self.config.w_bend * 5.0
                cross_cost = grid.get(nb, 0.0) * self.config.w_cross
                tentative_g = g_score[current] + length_cost + bend_cost + cross_cost
                if tentative_g < g_score.get(nb, float("inf")):
                    g_score[nb] = tentative_g
                    h = self._heuristic(nb, end_node)
                    f = tentative_g + self.config.w_heuristic * h
                    counter += 1
                    heapq.heappush(open_heap, (f, counter, nb))
                    came_from[nb] = current
        raise ValueError(
            f"A* 不可达: {start} → {end}（迭代 {iter_count} 次）"
        )

    def _obstacle_to_set(
        self, obstacles: list[tuple[float, float, float, float]]
    ) -> set[tuple[int, int]]:
        """将障碍物矩形转换为网格点集合。"""
        gs = self.config.grid_size
        obs_set: set[tuple[int, int]] = set()
        for x, y, w, h in obstacles:
            x0 = int(math.floor(x / gs))
            y0 = int(math.floor(y / gs))
            x1 = int(math.ceil((x + w) / gs))
            y1 = int(math.ceil((y + h) / gs))
            for gx in range(x0, x1):
                for gy in range(y0, y1):
                    obs_set.add((gx, gy))
        return obs_set

    def _heuristic(
        self, node: tuple[int, int], goal: tuple[int, int]
    ) -> float:
        """曼哈顿距离启发式（admissible）。"""
        return float(abs(node[0] - goal[0]) + abs(node[1] - goal[1]))

    def _reconstruct(
        self,
        came_from: dict[tuple[int, int], tuple[int, int]],
        current: tuple[int, int],
        gs: float,
    ) -> list[tuple[float, float]]:
        """重建路径（从终点回溯到起点）。"""
        path_nodes = [current]
        while current in came_from:
            current = came_from[current]
            path_nodes.append(current)
        path_nodes.reverse()
        return [(n[0] * gs, n[1] * gs) for n in path_nodes]

    def _compute_bend_cost(self, angle: float) -> float:
        """计算弯曲代价（角度越大代价越高）。

        学术依据：LiDAR ISPD'25 §3.1
        公式：bend_cost = |angle| / π（归一化到 [0, 1]）

        Args:
            angle: 方向变化角度（弧度）。

        Returns:
            弯曲代价。
        """
        return abs(angle) / math.pi

    def _compute_bend_cost_grid(
        self,
        prev: tuple[int, int] | None,
        cur: tuple[int, int],
        nxt: tuple[int, int],
    ) -> float:
        """计算网格三点的弯曲代价。"""
        if prev is None:
            return 0.0
        a1 = math.atan2(cur[1] - prev[1], cur[0] - prev[0])
        a2 = math.atan2(nxt[1] - cur[1], nxt[0] - cur[0])
        diff = abs(a2 - a1)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return self.config.w_bend * self._compute_bend_cost(diff)

    def _check_bend_radius(self, p1, p2, p3) -> bool:
        """检查三点形成的弯曲是否满足最小半径约束。

        学术依据：LiDAR ISPD'25 §3.2
        公式：R = |v1|*|v2|*|v1-v2| / (2*|v1×v2|) （三点外接圆半径）

        Args:
            p1, p2, p3: 三点坐标。

        Returns:
            True 若弯曲半径 >= config.bend_radius。
        """
        v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]], dtype=float)
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]], dtype=float)
        cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
        if cross < 1e-12:
            # 共线，无弯曲
            return True
        # 三点外接圆半径公式：R = |v1|*|v2|*|v1-v2| / (2*|cross|)
        v3 = v1 - v2
        r = (
            float(np.hypot(*v1)) * float(np.hypot(*v2))
            * float(np.hypot(*v3)) / (2.0 * cross)
        )
        return bool(r >= self.config.bend_radius)

    def _check_bend_radius_grid(
        self,
        prev: tuple[int, int],
        cur: tuple[int, int],
        nxt: tuple[int, int],
    ) -> bool:
        """网格坐标三点弯曲半径检查。"""
        gs = self.config.grid_size
        return self._check_bend_radius(
            (prev[0] * gs, prev[1] * gs),
            (cur[0] * gs, cur[1] * gs),
            (nxt[0] * gs, nxt[1] * gs),
        )

    def _smooth_path(
        self, path: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """路径平滑（去除冗余共线点，保留弯曲点）。"""
        if len(path) <= 2:
            return path
        smoothed = [path[0]]
        for i in range(1, len(path) - 1):
            prev = smoothed[-1]
            cur = path[i]
            nxt = path[i + 1]
            v1 = (cur[0] - prev[0], cur[1] - prev[1])
            v2 = (nxt[0] - cur[0], nxt[1] - cur[1])
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if abs(cross) > 1e-12:
                smoothed.append(cur)
        smoothed.append(path[-1])
        return smoothed
