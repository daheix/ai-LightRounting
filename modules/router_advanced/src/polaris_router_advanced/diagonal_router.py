"""8 方向 A* 布线器（曲线感知，2025 增强）。

支持 8 方向移动（含 45° 对角线），生成更平滑的波导路径，
减少不必要的直角转弯，提升布线质量。

方法参考（方案检索，见项目规则 1.1）：
- LiDAR (ISPD 2025) curvy-aware A*（8 方向 + 弯曲半径约束）
  来源: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 分层曲线波导布线（非 Manhattan 状态）
  来源: https://arxiv.org/html/2505.17239v2
- A* 搜索算法（Hart, Nilsson & Raphael 1968）
  https://en.wikipedia.org/wiki/A*_search_algorithm

8 方向移动代价：
- 直行（E/W/N/S）：代价 1.0
- 对角线（NE/NW/SE/SW）：代价 sqrt(2) ≈ 1.414
弯曲半径约束：对角线方向切换时仍需满足 min_bend_steps。
"""

from __future__ import annotations

import heapq
import math

from .waveguide_router import GridRouter

# 8 方向移动：(dx, dy, direction_code, cost)
# 方向编码: 0=E, 1=W, 2=N, 3=S, 4=NE, 5=NW, 6=SE, 7=SW
_MOVES_8 = [
    (1, 0, 0, 1.0),  # E
    (-1, 0, 1, 1.0),  # W
    (0, 1, 2, 1.0),  # N
    (0, -1, 3, 1.0),  # S
    (1, 1, 4, math.sqrt(2)),  # NE
    (-1, 1, 5, math.sqrt(2)),  # NW
    (1, -1, 6, math.sqrt(2)),  # SE
    (-1, -1, 7, math.sqrt(2)),  # SW
]

# 方向角度（用于弯曲半径约束检查）
_DIR_ANGLE = {
    0: 0.0,
    1: math.pi,
    2: math.pi / 2,
    3: -math.pi / 2,
    4: math.pi / 4,
    5: 3 * math.pi / 4,
    6: -math.pi / 4,
    7: -3 * math.pi / 4,
}


class DiagonalGridRouter(GridRouter):
    """8 方向 A* 网格布线器（曲线感知，LiDAR 2025 方法）。

    继承 GridRouter 并扩展为 8 方向移动，支持对角线布线，
    生成更平滑的波导路径。

    来源:
    - LiDAR (ISPD 2025): https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - LiDAR 2.0: https://arxiv.org/html/2505.17239v2
    """

    def _heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        """8 方向启发式（切比雪夫距离 + 对角线代价）。"""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        # 切比雪夫距离：对角线步数 + 直行步数
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    def _get_neighbors(
        self,
        pos: tuple[int, int],
        state: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> list[tuple[int, int, int, int, float]]:
        """计算 8 方向邻居（含对角线，防止穿墙）。"""
        x, y = pos
        last_dir, straight = state
        neighbors: list[tuple[int, int, int, int, float]] = []
        for dx, dy, d, cost in _MOVES_8:
            nx, ny = x + dx, y + dy
            if not self._is_valid_move((nx, ny, d), (x, y), blocked):
                continue
            new_straight = self._compute_straight(d, last_dir, straight)
            if not self._check_bend_constraint(d, last_dir, straight):
                continue
            neighbors.append((nx, ny, d, new_straight, cost))
        return neighbors

    def _is_valid_move(
        self,
        move: tuple[int, int, int],
        origin: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> bool:
        """检查移动是否有效（边界 + 障碍 + 对角线穿墙）。"""
        nx, ny, d = move
        x, y = origin
        if not (0 <= nx < self.grid_w and 0 <= ny < self.grid_h):
            return False
        if self.obstacle[ny, nx] or (nx, ny) in blocked:
            return False
        # 对角线移动防止穿墙：检查两个相邻直行格是否被阻挡
        if d >= 4 and (self.obstacle[y, nx] or self.obstacle[ny, x]):
            return False
        return True

    def _compute_straight(self, d: int, last_dir: int, straight: int) -> int:
        """计算连续直行步数。"""
        return straight + 1 if d == last_dir else 1

    def _check_bend_constraint(
        self,
        d: int,
        last_dir: int,
        straight: int,
    ) -> bool:
        """检查弯曲半径约束（角度差越大需要更多直行步数）。"""
        is_turn = last_dir != -1 and d != last_dir
        if not is_turn:
            return True
        angle_diff = abs(_DIR_ANGLE[d] - _DIR_ANGLE[last_dir])
        angle_diff = min(angle_diff, 2 * math.pi - angle_diff)
        required_steps = max(
            self.min_bend_steps,
            int(angle_diff / (math.pi / 4)) * 2,
        )
        return straight >= required_steps

    def route(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        blocked: set[tuple[int, int]] | None = None,
    ) -> list[tuple[int, int]] | None:
        """8 方向 A* 搜索（返回网格坐标列表，失败返回 None）。"""
        blocked = blocked or set()
        orig_start, orig_goal = self._save_endpoints(start, goal)
        start_state = (start[0], start[1], -1, 0)
        # open set: (f, g, x, y, last_dir, straight)
        open_h: list[tuple[float, float, int, int, int, int]] = []
        heapq.heappush(open_h, (self._heuristic(start, goal), 0.0, start[0], start[1], -1, 0))
        g_score: dict[tuple[int, int, int, int], float] = {start_state: 0.0}
        came_from: dict[tuple[int, int, int, int], tuple[int, int, int, int] | None] = {
            start_state: None
        }
        while open_h:
            _f, g, x, y, last_dir, straight = heapq.heappop(open_h)
            if (x, y) == goal:
                self._restore_endpoints(start, goal, orig_start, orig_goal)
                return self._reconstruct_path_tuple(came_from, (x, y, last_dir, straight))
            for nx, ny, d, new_straight, cost in self._get_neighbors(
                (x, y), (last_dir, straight), blocked
            ):
                new_state = (nx, ny, d, new_straight)
                ng = g + cost
                if ng < g_score.get(new_state, float("inf")):
                    g_score[new_state] = ng
                    came_from[new_state] = (x, y, last_dir, straight)
                    nf = ng + self._heuristic((nx, ny), goal)
                    heapq.heappush(open_h, (nf, ng, nx, ny, d, new_straight))
        self._restore_endpoints(start, goal, orig_start, orig_goal)
        return None

    def _reconstruct_path_tuple(
        self,
        came_from: dict[tuple[int, int, int, int], tuple[int, int, int, int] | None],
        goal_state: tuple[int, int, int, int],
    ) -> list[tuple[int, int]]:
        """从 came_from 回溯重建路径（元组状态编码版本）。

        DiagonalGridRouter 用 ``(x, y, dir, straight)`` 元组作为状态键，
        与父类 GridRouter 的整数状态编码不同，因此需要独立实现。

        Args:
            came_from: 元组状态 → 前驱元组状态（或 None）。
            goal_state: 终点状态元组。

        Returns:
            网格坐标列表 ``[(x, y), ...]``。
        """
        states: list[tuple[int, int, int, int]] = []
        cur: tuple[int, int, int, int] | None = goal_state
        while cur is not None:
            states.append(cur)
            cur = came_from.get(cur)
        states.reverse()
        return [(s[0], s[1]) for s in states]


__all__ = ["DiagonalGridRouter"]
