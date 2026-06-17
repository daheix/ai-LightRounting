"""波导约束布线器（Task 11）。

实现 A* 网格布线 + 弯曲半径/间距/等长约束检查 + S 弯（欧拉/正弦）生成。
采用 Manhattan 风格直角布线（光波导版图常用），代价函数综合路径长度、
弯曲惩罚与交叉惩罚，避开放置好的器件与已布线路径。

来源（方案检索，见项目规则 1.1）：
- A* 搜索算法（经典网格寻路）
  https://en.wikipedia.org/wiki/A*_search_algorithm
- NeurIPS 2022 Cheng et al. 策略梯度 + 生成式布线（SJTU+华为）
  https://openreview.net/pdf?id=uNYqDfPEDD8
- LiDAR (ISPD 2025) 曲线感知 A* 光波导详细布线（grid-based curvy-aware A*）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 分层曲线波导布线（Manhattan/非 Manhattan 状态、弯曲半径约束）
  https://arxiv.org/html/2505.17239v2
- 欧拉弯曲（clothoid）平滑过渡，曲率线性变化降低弯曲损耗
  https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/EulerWaveguideBend.html
- Fujisawa et al. Euler 弯曲较圆形弯曲损耗更低
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Rizzo et al. Optics Letters 2023 欧拉曲线提升 SOI 器件制造鲁棒性
  https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Iterable
from dataclasses import dataclass

from polaris.engine.floorplan_env import FloorplanState, Placement
from polaris.engine.netlist import Netlist

# 每个直角弯曲的估算损耗（dB），SOI 弯曲典型 0.005-0.01 dB
_BEND_LOSS_DB = 0.005


@dataclass
class Route:
    """单条布线路径。

    Attributes:
        net_id: 连接 ID（如 ``"n0"``）。
        path: 路径点序列（μm，物理坐标）。
        length: 总长度（μm）。
        num_bends: 弯曲数（方向改变点数）。
        num_crossings: 与其他路径的交叉数。
        loss_db: 估算损耗（dB，含弯曲损耗 + 交叉损耗）。
        is_equalized: 是否已做等长处理。
    """

    net_id: str
    path: list[tuple[float, float]]
    length: float
    num_bends: int
    num_crossings: int
    loss_db: float
    is_equalized: bool = False


class WaveguideRouter:
    """波导约束布线器（A* + 弯曲半径/间距/等长约束）。

    网格化 A* 搜索：网格坐标用整数，物理坐标由 ``grid_size`` 缩放。
    代价 = 步数 + 弯曲惩罚 + 交叉惩罚，启发函数为曼哈顿距离。
    障碍物（器件包围盒）以网格点集合存储，已布线路径作为软障碍（可交叉但受罚）。

    Args:
        grid_size: 网格大小（μm）。
        min_bend_radius: 最小弯曲半径（SOI 5μm，SiN 50μm）。
        min_spacing: 最小波导间距（SOI 1μm，SiN 2μm）。
        crossing_loss_db: 交叉损耗（dB，典型 0.3）。
    """

    def __init__(
        self,
        grid_size: float = 1.0,
        min_bend_radius: float = 5.0,
        min_spacing: float = 1.0,
        crossing_loss_db: float = 0.3,
    ) -> None:
        self.grid_size = float(grid_size)
        self.min_bend_radius = float(min_bend_radius)
        self.min_spacing = float(min_spacing)
        self.crossing_loss_db = float(crossing_loss_db)
        # A* 代价权重（网格步数单位）
        self.bend_penalty = 2.0  # 方向改变时的弯曲惩罚
        self.crossing_penalty = 10.0  # 进入已布线网格点的交叉惩罚

    # ------------------------------------------------------------------
    # 网格坐标转换
    # ------------------------------------------------------------------
    def _to_grid(self, p: tuple[float, float]) -> tuple[int, int]:
        """物理坐标 -> 网格整数坐标。"""
        return (
            int(round(p[0] / self.grid_size)),
            int(round(p[1] / self.grid_size)),
        )

    def _to_phys(self, gp: tuple[int, int]) -> tuple[float, float]:
        """网格整数坐标 -> 物理坐标。"""
        return (gp[0] * self.grid_size, gp[1] * self.grid_size)

    # ------------------------------------------------------------------
    # 主布线入口：为网表中所有连接生成波导路径
    # ------------------------------------------------------------------
    def route(
        self,
        netlist: Netlist,
        placements: dict[str, Placement] | FloorplanState,
    ) -> list[Route]:
        """为网表中所有连接生成波导路径。

        逐连接布线：每条连接的起止端口由 ``placements`` 的端口绝对坐标确定，
        已布线路径作为软障碍（可交叉但受交叉惩罚）以减少冲突。

        Args:
            netlist: 解析后的网表。
            placements: ``instance_id -> Placement`` 映射，或 ``FloorplanState``。

        Returns:
            每条连接对应的 ``Route`` 列表。
        """
        if isinstance(placements, FloorplanState):
            placements = placements.placements

        # 器件包围盒 -> 硬障碍网格点
        base_obstacles = self._build_obstacles(placements)
        # 已布线路径的网格点（软障碍）与线段（用于交叉计数）
        routed_points: set[tuple[int, int]] = set()
        routed_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

        routes: list[Route] = []
        for idx, conn in enumerate(netlist.connections):
            src_pl = placements.get(conn.src_instance)
            dst_pl = placements.get(conn.dst_instance)
            if src_pl is None or dst_pl is None:
                continue
            src_ports = src_pl.port_positions()
            dst_ports = dst_pl.port_positions()
            if conn.src_port not in src_ports or conn.dst_port not in dst_ports:
                continue
            start = src_ports[conn.src_port]
            end = dst_ports[conn.dst_port]

            route_obj = self.route_single(
                start,
                end,
                base_obstacles,
                soft=routed_points,
                net_id=f"n{idx}",
            )
            # 统计与已有路径的交叉数并重算损耗
            route_obj.num_crossings = self._count_crossings(route_obj.path, routed_segments)
            route_obj.loss_db = self._compute_loss(route_obj)
            routes.append(route_obj)

            # 将本路径加入已布线集合，供后续连接避让/计交叉
            for gp in self._path_grid_points(route_obj.path):
                routed_points.add(gp)
            routed_segments.extend(self._path_segments(route_obj.path))

        return routes

    def _build_obstacles(self, placements: dict[str, Placement]) -> set[tuple[int, int]]:
        """将所有已放置器件的包围盒栅格化为障碍网格点集合。"""
        obs: set[tuple[int, int]] = set()
        for pl in placements.values():
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            gi0 = int(math.floor(xmin / self.grid_size))
            gj0 = int(math.floor(ymin / self.grid_size))
            gi1 = int(math.ceil(xmax / self.grid_size))
            gj1 = int(math.ceil(ymax / self.grid_size))
            for gx in range(gi0, gi1 + 1):
                for gy in range(gj0, gj1 + 1):
                    obs.add((gx, gy))
        return obs

    # ------------------------------------------------------------------
    # A* 单条布线
    # ------------------------------------------------------------------
    def route_single(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        obstacles: Iterable[tuple[int, int]],
        soft: Iterable[tuple[int, int]] | None = None,
        net_id: str = "",
    ) -> Route:
        """A* 算法布线单条连接。

        Args:
            start: 起点物理坐标（μm）。
            end: 终点物理坐标（μm）。
            obstacles: 硬障碍网格点集合（整数坐标，不可进入）。
            soft: 软障碍网格点集合（整数坐标，可进入但受交叉惩罚）。
            net_id: 连接 ID。

        Returns:
            布线结果 ``Route``。
        """
        sg = self._to_grid(start)
        eg = self._to_grid(end)

        blocked = set(obstacles)
        # 起终点必须可达：从障碍中移除
        blocked.discard(sg)
        blocked.discard(eg)
        soft_set = set(soft) if soft is not None else set()

        # 4 方向移动（Manhattan 风格）：(dx, dy, dir_id)
        moves = ((1, 0, 0), (0, -1, 1), (-1, 0, 2), (0, 1, 3))

        def heuristic(p: tuple[int, int]) -> int:
            return abs(p[0] - eg[0]) + abs(p[1] - eg[1])

        # 状态: (gx, gy, dir)，dir=-1 表示起点（无进入方向）
        start_state = (sg[0], sg[1], -1)
        # 堆元素: (f, g, counter, state)，counter 保证不比较 state
        counter = 0
        open_heap: list[tuple[float, float, int, tuple[int, int, int]]] = [
            (float(heuristic(sg)), 0.0, counter, start_state)
        ]
        g_score: dict[tuple[int, int, int], float] = {start_state: 0.0}
        came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}

        found: tuple[int, int, int] | None = None
        while open_heap:
            f, g, _, state = heapq.heappop(open_heap)
            if g > g_score.get(state, float("inf")):
                continue
            cx, cy, cdir = state
            if (cx, cy) == eg:
                found = state
                break
            for dx, dy, ndir in moves:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in blocked:
                    continue
                bend_cost = self.bend_penalty if (cdir != -1 and ndir != cdir) else 0.0
                cross_cost = self.crossing_penalty if (nx, ny) in soft_set else 0.0
                ng = g + 1.0 + bend_cost + cross_cost
                nstate = (nx, ny, ndir)
                if ng < g_score.get(nstate, float("inf")):
                    g_score[nstate] = ng
                    came_from[nstate] = state
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (ng + heuristic((nx, ny)), ng, counter, nstate),
                    )

        if found is None:
            # 回退：直连（可能穿过障碍，仅作兜底）
            grid_path = [sg, eg]
        else:
            grid_path = self._reconstruct(came_from, found)

        # 转物理坐标并简化共线点
        phys_path = [self._to_phys(gp) for gp in grid_path]
        phys_path = self._simplify(phys_path)
        # 用精确端口坐标覆盖首尾
        if phys_path:
            phys_path[0] = (float(start[0]), float(start[1]))
            phys_path[-1] = (float(end[0]), float(end[1]))
        return self._build_route(net_id, phys_path)

    def _reconstruct(
        self,
        came_from: dict[tuple[int, int, int], tuple[int, int, int]],
        end_state: tuple[int, int, int],
    ) -> list[tuple[int, int]]:
        """从 A* came_from 重建网格路径。"""
        path: list[tuple[int, int, int]] = [end_state]
        s = end_state
        while s in came_from:
            s = came_from[s]
            path.append(s)
        path.reverse()
        return [(s[0], s[1]) for s in path]

    def _simplify(self, pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """移除共线中间点，保留弯曲点。"""
        if len(pts) <= 2:
            return list(pts)
        out: list[tuple[float, float]] = [pts[0]]
        for i in range(1, len(pts) - 1):
            if not self._collinear(out[-1], pts[i], pts[i + 1]):
                out.append(pts[i])
        out.append(pts[-1])
        return out

    def _collinear(
        self, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
    ) -> bool:
        """三点共线判定（允许浮点误差）。"""
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return abs(cross) < 1e-9

    def _build_route(self, net_id: str, phys_path: list[tuple[float, float]]) -> Route:
        """由物理路径构造 ``Route``（不含交叉统计，交叉在 route() 中补算）。"""
        length = self._path_length(phys_path)
        num_bends = self._count_bends(phys_path)
        loss_db = num_bends * _BEND_LOSS_DB
        return Route(
            net_id=net_id,
            path=phys_path,
            length=length,
            num_bends=num_bends,
            num_crossings=0,
            loss_db=loss_db,
            is_equalized=False,
        )

    def _path_length(self, pts: list[tuple[float, float]]) -> float:
        """计算折线总长度（μm）。"""
        total = 0.0
        for i in range(1, len(pts)):
            total += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        return total

    def _count_bends(self, pts: list[tuple[float, float]]) -> int:
        """统计方向改变点数（弯曲数）。"""
        if len(pts) < 3:
            return 0
        count = 0
        for i in range(1, len(pts) - 1):
            if not self._collinear(pts[i - 1], pts[i], pts[i + 1]):
                count += 1
        return count

    # ------------------------------------------------------------------
    # S 弯生成（欧拉/正弦平滑过渡）
    # ------------------------------------------------------------------
    def generate_s_bend(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        min_radius: float,
    ) -> list[tuple[float, float]]:
        """生成 S 弯（正弦曲线过渡，曲率连续，满足最小弯曲半径）。

        采用正弦 S 弯 ``y = h/2 * (1 - cos(pi*t))``，其最小曲率半径为
        ``R_min = 2*L^2 / (|h|*pi^2)``（L 为纵向跨度，h 为横向偏移）。
        若实际纵向距离不足以满足 ``min_radius``，则延长纵向跨度至所需最小值
        （来源：Tidy3D Euler 弯曲示例，clothoid/正弦过渡曲率连续）。

        Args:
            start: 起点（μm）。
            end: 终点（μm）。
            min_radius: 最小弯曲半径（μm）。

        Returns:
            S 弯采样点序列（μm）。
        """
        x0, y0 = start
        x1, y1 = end
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return [(x0, y0)]
        # 选择主方向（位移较大的轴为纵向）
        if abs(dx) >= abs(dy):
            return self._s_bend_axis(x0, y0, dx, dy, min_radius, horizontal=True)
        return self._s_bend_axis(x0, y0, dy, dx, min_radius, horizontal=False)

    def _s_bend_axis(
        self,
        x0: float,
        y0: float,
        longitudinal: float,
        lateral: float,
        min_radius: float,
        horizontal: bool,
    ) -> list[tuple[float, float]]:
        """在主方向为纵向的局部坐标系下生成正弦 S 弯。"""
        if abs(lateral) < 1e-9:
            # 无横向偏移，直线
            return [(x0, y0), (x0 + longitudinal if horizontal else x0,
                               y0 if horizontal else y0 + longitudinal)]
        # 正弦 S 弯最小半径 R = 2*L^2 / (|h|*pi^2) -> L_min = sqrt(R*|h|*pi^2/2)
        l_min = math.sqrt(min_radius * abs(lateral) * math.pi**2 / 2.0)
        l_eff = max(abs(longitudinal), l_min)
        n = max(32, int(l_eff / self.grid_size) + 1)
        sign = 1.0 if longitudinal >= 0 else -1.0
        pts: list[tuple[float, float]] = []
        for i in range(n + 1):
            t = i / n
            # 正弦过渡：横向位移 h/2*(1-cos(pi*t))，纵向位移 L*t
            off = lateral * 0.5 * (1.0 - math.cos(math.pi * t))
            along = sign * l_eff * t
            if horizontal:
                pts.append((x0 + along, y0 + off))
            else:
                pts.append((x0 + off, y0 + along))
        return pts

    # ------------------------------------------------------------------
    # 弯曲半径检查
    # ------------------------------------------------------------------
    def check_bend_radius(
        self, path: list[tuple[float, float]], min_radius: float
    ) -> bool:
        """检查路径所有弯曲点是否满足最小弯曲半径。

        对每个弯曲点（方向改变点），用其与前后邻点构成三角形的外接圆半径
        作为等效弯曲半径；要求所有弯曲点半径 >= ``min_radius``。
        共线三点视为无弯曲（半径无穷大，跳过）。

        Args:
            path: 路径点序列（μm）。
            min_radius: 最小弯曲半径（μm）。

        Returns:
            全部满足返回 True，否则 False。
        """
        if len(path) < 3:
            return True
        for i in range(1, len(path) - 1):
            r = self._circumradius(path[i - 1], path[i], path[i + 1])
            if r is None:
                continue  # 共线，无弯曲
            if r < min_radius:
                return False
        return True

    def _circumradius(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
    ) -> float | None:
        """计算三点外接圆半径（共线返回 None）。"""
        ab = math.hypot(b[0] - a[0], b[1] - a[1])
        bc = math.hypot(c[0] - b[0], c[1] - b[1])
        ca = math.hypot(a[0] - c[0], a[1] - c[1])
        area = 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if area < 1e-12:
            return None  # 共线
        return (ab * bc * ca) / (4.0 * area)

    # ------------------------------------------------------------------
    # 间距检查
    # ------------------------------------------------------------------
    def check_spacing(
        self,
        path: list[tuple[float, float]],
        other_paths: list[list[tuple[float, float]]],
        min_spacing: float,
    ) -> bool:
        """检查路径间距是否满足最小间距。

        对 ``path`` 与每条 ``other_paths`` 采样后逐点比较最小距离，
        要求任意两条路径间距 >= ``min_spacing``。

        Args:
            path: 待检查路径（μm）。
            other_paths: 其他路径列表（μm）。
            min_spacing: 最小间距（μm）。

        Returns:
            全部满足返回 True，否则 False。
        """
        if len(path) < 2:
            return True
        samples = self._sample_path(path)
        for other in other_paths:
            if len(other) < 2:
                continue
            other_samples = self._sample_path(other)
            for p in samples:
                for q in other_samples:
                    if math.hypot(p[0] - q[0], p[1] - q[1]) < min_spacing - 1e-9:
                        return False
        return True

    def _sample_path(
        self, pts: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """沿折线按网格步长采样点。"""
        step = self.grid_size
        out: list[tuple[float, float]] = []
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            seg_len = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(seg_len / step) + 1)
            for j in range(n):
                t = j / n
                out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        out.append(pts[-1])
        return out

    # ------------------------------------------------------------------
    # 等长处理（MZI 臂、差分对）
    # ------------------------------------------------------------------
    def equalize_length(
        self,
        paths: list[Route],
        target_length: float,
    ) -> list[Route]:
        """等长处理：通过在末端添加蛇形延长使各路径长度趋近 ``target_length``。

        对短于 ``target_length`` 的路径，在其末端沿原方向追加蛇形齿，
        每齿增加 ``3*d`` 长度（垂直 d + 沿向 d + 垂直 d），总延长精确等于
        ``target_length - length``。已达到目标长度的路径保持不变。

        Args:
            paths: 待等长的路径列表。
            target_length: 目标长度（μm）。

        Returns:
            等长处理后的新 ``Route`` 列表（``is_equalized=True``）。
        """
        result: list[Route] = []
        for r in paths:
            if r.length >= target_length - 1e-9:
                result.append(r)
                continue
            extra = target_length - r.length
            new_path = self._extend_path(r.path, extra)
            new_route = Route(
                net_id=r.net_id,
                path=new_path,
                length=self._path_length(new_path),
                num_bends=self._count_bends(new_path),
                num_crossings=r.num_crossings,
                loss_db=r.loss_db,
                is_equalized=True,
            )
            result.append(new_route)
        return result

    def _extend_path(
        self, path: list[tuple[float, float]], extra: float
    ) -> list[tuple[float, float]]:
        """在路径末端沿原方向追加蛇形齿，精确延长 ``extra`` 长度。"""
        if extra <= 1e-9 or len(path) < 2:
            return list(path)
        last = path[-1]
        prev = path[-2]
        dx = last[0] - prev[0]
        dy = last[1] - prev[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            return list(path)
        ux, uy = dx / L, dy / L  # 沿向单位向量
        px, py = -uy, ux  # 垂直单位向量
        # 每齿增加 3*d 长度，限制单齿幅度避免过大凸起
        max_d = max(self.min_spacing * 4.0, self.grid_size * 4.0)
        n = max(1, int(math.ceil(extra / (3.0 * max_d))))
        d = extra / (3.0 * n)
        new_pts: list[tuple[float, float]] = []
        cur = last
        for k in range(n):
            sign = 1.0 if k % 2 == 0 else -1.0
            p1 = (cur[0] + px * d * sign, cur[1] + py * d * sign)
            p2 = (p1[0] + ux * d, p1[1] + uy * d)
            p3 = (p2[0] - px * d * sign, p2[1] - py * d * sign)
            new_pts.extend([p1, p2, p3])
            cur = p3
        return list(path) + new_pts

    # ------------------------------------------------------------------
    # 交叉计数与线段相交
    # ------------------------------------------------------------------
    def _count_crossings(
        self,
        path: list[tuple[float, float]],
        segments: list[tuple[tuple[float, float], tuple[float, float]]],
    ) -> int:
        """统计 ``path`` 的线段与 ``segments`` 的相交数（不含共线重叠）。"""
        if len(path) < 2 or not segments:
            return 0
        count = 0
        my_segs = self._path_segments(path)
        for s1 in my_segs:
            for s2 in segments:
                if self._segments_cross(s1, s2):
                    count += 1
        return count

    def _path_segments(
        self, pts: list[tuple[float, float]]
    ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """将路径点序列转为相邻线段列表。"""
        return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]

    def _segments_cross(
        self,
        s1: tuple[tuple[float, float], tuple[float, float]],
        s2: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        """判断两线段是否规范相交（跨立测试）。"""
        (x1, y1), (x2, y2) = s1
        (x3, y3), (x4, y4) = s2
        d1 = self._orient(x3, y3, x4, y4, x1, y1)
        d2 = self._orient(x3, y3, x4, y4, x2, y2)
        d3 = self._orient(x1, y1, x2, y2, x3, y3)
        d4 = self._orient(x1, y1, x2, y2, x4, y4)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False

    def _orient(
        self, ax: float, ay: float, bx: float, by: float, cx: float, cy: float
    ) -> float:
        """叉积 (b-a) x (c-a)，>0 左转，<0 右转，=0 共线。"""
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    def _compute_loss(self, route: Route) -> float:
        """估算损耗 = 弯曲损耗 + 交叉损耗。"""
        return route.num_bends * _BEND_LOSS_DB + route.num_crossings * self.crossing_loss_db

    def _path_grid_points(
        self, phys_path: list[tuple[float, float]]
    ) -> list[tuple[int, int]]:
        """将物理路径转为覆盖的网格点列表（Bresenham 连线）。"""
        pts: list[tuple[int, int]] = []
        for i in range(len(phys_path) - 1):
            a = self._to_grid(phys_path[i])
            b = self._to_grid(phys_path[i + 1])
            pts.extend(self._grid_line(a, b))
        return pts

    def _grid_line(
        self, a: tuple[int, int], b: tuple[int, int]
    ) -> list[tuple[int, int]]:
        """Bresenham 算法枚举两网格点间所有网格点。"""
        x0, y0 = a
        x1, y1 = b
        pts: list[tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            pts.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return pts
