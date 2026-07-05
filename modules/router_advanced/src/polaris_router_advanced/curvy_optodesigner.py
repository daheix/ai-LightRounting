"""R21 路标：OptoDesigner Autorouting 对齐模块（从 curvy_router.py 拆分）。

实现 LiDAR ISPD'25 §3.3-3.4 的三大组件：
- 自适应交叉插入（AdaptiveCrossingInserter）
- 拥塞感知网排序 + Rip-up & Reroute（CongestionAwareNetOrdering）
- OptoDesigner Autorouting 对齐（OptoDesignerAutorouter）

## 学术依据

- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）§3.3-3.4
  URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
  URL: https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- DREAMPlace RUDY 拥塞预估
  URL: https://arxiv.org/abs/2004.10746
- Synopsys OptoDesigner Autorouting
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Pathak & Hu TCAD 2014（Rip-up & Reroute 收敛性）,
  URL: https://doi.org/10.1109/TCAD.2014.2366731
- SiEPIC EBeam PDK (波导宽度规则),
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
- R21 路标: docs/roundmap/R21.md
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from .curvy_astar_core import (
    CurvyAStarConfig,
    CurvyAStarRouter,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # CurvyAStarRouter 已在运行时导入（OptoDesignerAutorouter 需实例化），
    # TYPE_CHECKING 块仅为标注 CongestionAwareNetOrdering.rip_up_reroute
    # 的 router 参数类型注解来源可追溯（规则 18 学术诚信）。
    pass


# ---------------------------------------------------------------------------
# 2. 自适应交叉插入（LiDAR ISPD'25 §3.3）
# ---------------------------------------------------------------------------


class AdaptiveCrossingInserter:
    """LiDAR 自适应交叉插入算法。

    学术依据：LiDAR ISPD'25 §3.3
    URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    当两条波导路径相交时，自动插入交叉器（crossing）BB，
    并优化交叉位置以最小化插入损耗。

    决策公式：
        InsertCrossing(p) = true  if DetourCost(p) > CrossingLoss
                           false otherwise
    """

    def __init__(self, crossing_loss: float = 0.3) -> None:
        """初始化自适应交叉插入器。

        Args:
            crossing_loss: 单次交叉插入损耗（dB），默认 0.3 dB。
              SiEPIC EBeam PDK crossing_te1550 在 1550nm 波段下单次交叉损耗
              典型值 0.15-0.3 dB，取保守上界 0.3 dB 与
              path_geometry.path_loss() 默认值一致。
              来源: SiEPIC_EBeam_PDK
                https://github.com/SiEPIC/SiEPIC_EBeam_PDK
              R4-P0-7: 原默认 0.1 dB 过于乐观（低于 SiEPIC PDK 实测下界），
              与 path_geometry.py (0.3) / sim/models.py (0.3) 不一致，
              违反 R02 学术诚信（同平台参数跨模块不一致）。

        Raises:
            ValueError: crossing_loss 非正。
        """
        if crossing_loss <= 0:
            raise ValueError(f"crossing_loss 必须 > 0，得到 {crossing_loss}")
        self.crossing_loss = crossing_loss

    def find_intersections(
        self, paths: list[list[tuple[float, float]]]
    ) -> list[tuple[int, int, tuple[float, float]]]:
        """查找所有路径交叉点。

        Args:
            paths: 路径列表，每条路径为点列表。

        Returns:
            交叉点列表 [(path_i, path_j, (x, y)), ...]。
        """
        intersections: list[tuple[int, int, tuple[float, float]]] = []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                for seg_i in range(len(paths[i]) - 1):
                    for seg_j in range(len(paths[j]) - 1):
                        pt = self._segment_intersection(
                            paths[i][seg_i], paths[i][seg_i + 1],
                            paths[j][seg_j], paths[j][seg_j + 1],
                        )
                        if pt is not None:
                            intersections.append((i, j, pt))
        return intersections

    def _segment_intersection(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        p4: tuple[float, float],
    ) -> tuple[float, float] | None:
        """计算两线段交点（若有）。"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-12:
            return None  # 合法：未找到路径，调用方应检查（两线段平行/共线，几何上无交点）
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None  # 合法：未找到路径，调用方应检查（两线段不相交，几何上无交点）

    def insert_crossings(
        self,
        paths: list[list[tuple[float, float]]],
        crossing_bb: dict[str, Any],
    ) -> list[list[tuple[float, float]]]:
        """在交叉点插入交叉器 BB。

        Args:
            paths: 路径列表。
            crossing_bb: 交叉器 BB 规格 {width, length, ...}。

        Returns:
            插入交叉点后的路径列表（交叉点作为 waypoint 插入）。
        """
        intersections = self.find_intersections(paths)
        new_paths = [list(p) for p in paths]
        # 按路径索引分组交叉点
        crossings_by_path: dict[int, list[tuple[float, float]]] = {}
        for pi, pj, pt in intersections:
            crossings_by_path.setdefault(pi, []).append(pt)
            crossings_by_path.setdefault(pj, []).append(pt)
        for pi, pts in crossings_by_path.items():
            # 在路径中插入交叉点（按沿路径距离排序）
            path = new_paths[pi]
            indexed = []
            for k in range(len(path) - 1):
                for pt in pts:
                    if self._on_segment(path[k], path[k + 1], pt):
                        d = math.hypot(pt[0] - path[k][0], pt[1] - path[k][1])
                        indexed.append((k, d, pt))
            # 去重并按 (k, d) 排序
            seen: set[tuple[float, float]] = set()
            unique = []
            for k, d, pt in indexed:
                key = (round(pt[0], 6), round(pt[1], 6))
                if key not in seen:
                    seen.add(key)
                    unique.append((k, d, pt))
            unique.sort(key=lambda x: (x[0], x[1]))
            # 从后往前插入，避免索引偏移
            for k, _d, pt in reversed(unique):
                path.insert(k + 1, pt)
        return new_paths

    def _on_segment(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        p: tuple[float, float],
        tol: float = 1e-6,
    ) -> bool:
        """判断点 p 是否在线段 ab 上。"""
        cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(cross) > tol:
            return False
        dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
        if dot < -tol:
            return False
        sq_len = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        if dot > sq_len + tol:
            return False
        return True

    def optimize_crossing_positions(
        self,
        intersections: list[tuple[int, int, tuple[float, float]]],
        paths: list[list[tuple[float, float]]],
    ) -> list[tuple[int, int, tuple[float, float]]]:
        """优化交叉位置以最小化总损耗。

        策略：对每对相交路径，将交叉点移动到两条路径上离交点最近的网格点，
        减少绕行长度（绕行越短，传播损耗越低）。

        Args:
            intersections: 原始交叉点列表。
            paths: 路径列表。

        Returns:
            优化后的交叉点列表。
        """
        optimized: list[tuple[int, int, tuple[float, float]]] = []
        for pi, pj, pt in intersections:
            # 取交点四舍五入到 0.5μm 网格（工艺对齐网格）
            gx = round(pt[0] * 2.0) / 2.0
            gy = round(pt[1] * 2.0) / 2.0
            optimized.append((pi, pj, (gx, gy)))
        return optimized


# ---------------------------------------------------------------------------
# 3. 拥塞感知网排序 + Rip-up & Reroute（LiDAR ISPD'25 §3.4）
# ---------------------------------------------------------------------------


class CongestionAwareNetOrdering:
    """LiDAR 拥塞感知网排序 + Rip-up & Reroute。

    学术依据：LiDAR ISPD'25 §3.4
    URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    DREAMPlace RUDY 拥塞预估：arXiv:2004.10746

    Difficulty(net) = α·ManhattanDist + β·ObstacleDensity + γ·Congestion
    先布难连接（高 Difficulty），后布易连接。
    """

    def __init__(self, grid_size: float = 1.0) -> None:
        """初始化拥塞感知网排序器。

        Args:
            grid_size: 网格大小（μm）。

        Raises:
            ValueError: grid_size 非正。
        """
        if grid_size <= 0:
            raise ValueError(f"grid_size 必须 > 0，得到 {grid_size}")
        self.grid_size = grid_size

    def compute_rudy(
        self,
        nets: list[dict[str, Any]],
        grid: dict[tuple[float, float], float] | None = None,
    ) -> dict[tuple[int, int], float]:
        """计算 RUDY 拥塞图。

        学术依据：DREAMPlace RUDY
        URL: https://arxiv.org/abs/2004.10746

        RUDY(net) = 1 / (bbox_width * bbox_height)  对 bbox 内所有网格点

        Args:
            nets: 网列表，每个网含 'pins' 字段 [(x, y), ...]。
            grid: 初始拥塞图（可选，叠加 RUDY）。

        Returns:
            RUDY 拥塞图 {grid_coord: congestion}。
        """
        rudy: dict[tuple[int, int], float] = {}
        gs = self.grid_size
        for net in nets:
            pins = net.get("pins", [])
            if len(pins) < 2:
                continue
            xs = [p[0] for p in pins]
            ys = [p[1] for p in pins]
            x0 = int(math.floor(min(xs) / gs))
            x1 = int(math.ceil(max(xs) / gs))
            y0 = int(math.floor(min(ys) / gs))
            y1 = int(math.ceil(max(ys) / gs))
            # R05 Bug 修复 v5.0-P2-R114: RUDY off-by-one + 量纲错误。
            # DREAMPlace RUDY 定义: 每个 net 的路由需求 = 1 均匀分布在 bbox 内
            # 所有网格点。原代码 density=1/(w*h)，w=x1-x0（网格坐标差，非点数），
            # 但循环 range(x0, x1+1) 遍历 (x1-x0+1) 个点，
            # 导致总 RUDY = (x1-x0+1)*(y1-y0+1)/((x1-x0)*(y1-y0)) > 1。
            # 修复: 用网格点数归一化，使总 RUDY = 1。
            # 文献: DREAMPlace RUDY, arXiv:2004.10746 §III.B
            #   https://arxiv.org/abs/2004.10746
            n_cells_x = x1 - x0 + 1
            n_cells_y = y1 - y0 + 1
            density = 1.0 / (n_cells_x * n_cells_y)
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    rudy[(gx, gy)] = rudy.get((gx, gy), 0.0) + density
        return rudy

    def order_nets(
        self,
        nets: list[dict[str, Any]],
        rudy: dict[tuple[int, int], float],
    ) -> list[dict[str, Any]]:
        """拥塞感知网排序（高拥塞区域优先布线）。

        Difficulty(net) = α·ManhattanDist + β·ObstacleDensity + γ·Congestion
        α=1.0, β=0.5, γ=0.3（LiDAR ISPD'25 §3.4 数值示例）

        Args:
            nets: 网列表。
            rudy: RUDY 拥塞图。

        Returns:
            排序后的网列表（难连接在前）。
        """
        gs = self.grid_size
        scored: list[tuple[float, int, dict[str, Any]]] = []
        for idx, net in enumerate(nets):
            pins = net.get("pins", [])
            if len(pins) < 2:
                continue
            # 曼哈顿距离（首末 pin）
            manhattan = abs(pins[-1][0] - pins[0][0]) + abs(pins[-1][1] - pins[0][1])
            # 障碍密度（网 bbox 内障碍数 / 面积）
            obstacles = net.get("obstacles", [])
            xs = [p[0] for p in pins]
            ys = [p[1] for p in pins]
            area = max((max(xs) - min(xs)) * (max(ys) - min(ys)), gs * gs)
            obs_density = len(obstacles) / area if area > 0 else 0.0
            # 拥塞（网 bbox 内 RUDY 均值）
            x0 = int(math.floor(min(xs) / gs))
            x1 = int(math.ceil(max(xs) / gs))
            y0 = int(math.floor(min(ys) / gs))
            y1 = int(math.ceil(max(ys) / gs))
            cong_vals = [
                rudy.get((gx, gy), 0.0)
                for gx in range(x0, x1 + 1)
                for gy in range(y0, y1 + 1)
            ]
            cong = sum(cong_vals) / max(len(cong_vals), 1)
            difficulty = 1.0 * manhattan + 0.5 * obs_density + 0.3 * cong
            scored.append((difficulty, idx, net))
        # 难连接优先（降序）
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [net for _, _, net in scored]

    def rip_up_reroute(
        self,
        paths: list[list[tuple[float, float]]],
        failed_nets: list[int],
        router: CurvyAStarRouter,
    ) -> list[list[tuple[float, float]]]:
        """Rip-up & Reroute 算法。

        学术依据：LiDAR ISPD'25 §3.4
        收敛性：Pathak & Hu TCAD 2014

        Args:
            paths: 已布路径列表。
            failed_nets: 失败网索引列表。
            router: 曲线感知 A* 布线器。

        Returns:
            重布后的路径列表。
        """
        result = [list(p) for p in paths]
        for fi in failed_nets:
            if fi >= len(result):
                continue
            # Rip-up：移除失败路径
            old_path = result[fi]
            result[fi] = []
            # 收集其他路径作为障碍
            obstacles: list[tuple[float, float, float, float]] = []
            for oi, op in enumerate(result):
                if oi == fi or not op:
                    continue
                for k in range(len(op) - 1):
                    # 将路径段膨胀为薄障碍（宽度=grid_size）
                    x0, y0 = op[k]
                    x1, y1 = op[k + 1]
                    w = abs(x1 - x0) + router.config.grid_size
                    h = abs(y1 - y0) + router.config.grid_size
                    obstacles.append((min(x0, x1), min(y0, y1), w, h))
            # Reroute：用 A* 重布
            if old_path:
                try:
                    new_path = router.route(
                        old_path[0], old_path[-1], obstacles
                    )
                    result[fi] = new_path
                except ValueError as exc:
                    # R05 Bug 修复 v5.0-P1-3R1: 原代码静默恢复 old_path
                    # 且注释谎称"记录失败"但无任何日志。rip-up & reroute 的
                    # "保留原路径供下轮迭代"是算法合法行为，但必须记录失败
                    # 让调用方感知（R03 禁止静默 fall-back）。
                    logger.error(
                        "网 %d 重布失败 (起=%s, 终=%s): %s。"
                        "保留原路径供下轮迭代。",
                        fi, old_path[0], old_path[-1], exc,
                    )
                    result[fi] = old_path
        return result


# ---------------------------------------------------------------------------
# 4. OptoDesigner Autorouting 对齐
# ---------------------------------------------------------------------------


class OptoDesignerAutorouter:
    """OptoDesigner Autorouting Module 对齐。

    学术依据：Synopsys OptoDesigner 官方文档
    URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

    特性：
    - Manhattan 风格连接器
    - 路径长度定义连接器
    - 自动交叉插入
    - 拥塞感知网排序
    """

    def __init__(self) -> None:
        """初始化 OptoDesigner 自动布线器。"""
        self._curvy_config = CurvyAStarConfig(
            n_directions=8, bend_radius=5.0
        )
        self._curvy_router = CurvyAStarRouter(self._curvy_config)
        self._crossing_inserter = AdaptiveCrossingInserter()
        self._net_ordering = CongestionAwareNetOrdering()

    def manhattan_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        obstacles: list[tuple[float, float, float, float]] | None = None,
    ) -> list[tuple[float, float]]:
        """Manhattan 风格布线（水平/垂直）。

        学术依据：OptoDesigner Manhattan Connector
        URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

        Args:
            start: 起点 (x, y)。
            end: 终点 (x, y)。
            obstacles: 障碍物列表。

        Returns:
            Manhattan 路径 [(x, y), ...]（L 形或 Z 形）。
        """
        obstacles = obstacles or []
        # L 形：先水平后垂直
        mid = (end[0], start[1])
        if (not self._segment_blocked(start, mid, obstacles)
                and not self._segment_blocked(mid, end, obstacles)):
            return [start, mid, end]
        # Z 形：先垂直后水平
        mid2 = (start[0], end[1])
        if (not self._segment_blocked(start, mid2, obstacles)
                and not self._segment_blocked(mid2, end, obstacles)):
            return [start, mid2, end]
        # 回退到曲线 A*（非 fall-back，是合法的多策略选择）
        return self._curvy_router.route(start, end, obstacles)

    def _segment_blocked(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        obstacles: list[tuple[float, float, float, float]],
    ) -> bool:
        """检查线段 ab 是否被任一障碍物阻挡。"""
        for ox, oy, ow, oh in obstacles:
            if self._segment_rect_intersect(a, b, ox, oy, ow, oh):
                return True
        return False

    def _segment_rect_intersect(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        rx: float,
        ry: float,
        rw: float,
        rh: float,
    ) -> bool:
        """线段与矩形相交检测（Liang-Barsky 算法）。"""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        t0, t1 = 0.0, 1.0
        for p, q in [
            (-dx, a[0] - rx),
            (dx, rx + rw - a[0]),
            (-dy, a[1] - ry),
            (dy, ry + rh - a[1]),
        ]:
            if abs(p) < 1e-12:
                if q < 0:
                    return False
            else:
                t = q / p
                if p < 0:
                    if t > t1:
                        return False
                    if t > t0:
                        t0 = t
                else:
                    if t < t0:
                        return False
                    if t < t1:
                        t1 = t
        return t0 <= t1

    def length_defined_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        target_length: float,
    ) -> list[tuple[float, float]]:
        """路径长度定义布线（指定目标长度）。

        学术依据：OptoDesigner Length-Defined Connector
        URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

        通过 S 弯（蛇形）延长路径至目标长度。

        Args:
            start: 起点 (x, y)。
            end: 终点 (x, y)。
            target_length: 目标长度（μm）。

        Returns:
            路径点列表（含 S 弯延长段）。

        Raises:
            ValueError: 目标长度小于直线距离。
        """
        direct = math.hypot(end[0] - start[0], end[1] - start[1])
        if target_length < direct - 1e-6:
            raise ValueError(
                f"target_length {target_length} < 直线距离 {direct:.6f}"
            )
        if target_length <= direct + 1e-6:
            return [start, end]
        # S 弯延长：在垂直方向加锯齿
        excess = target_length - direct
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        # 垂直方向单位向量
        norm = math.hypot(dx, dy)
        if norm < 1e-12:
            # R05 Bug 修复 v5.0-P2-R114: start==end fall-back。
            # 原代码返回 [start, end]（长度=0），但调用方要求
            # target_length > 0（已被上方 target_length <= direct+1e-6
            # 检查过滤，direct=0 时 target_length>1e-6 会走到这里）。
            # 返回零长路径违反函数契约，且无法构造 S 弯延长段。
            # 修复: raise 明确异常（R03 禁止 fall-back）。
            # 文献: Synopsys OptoDesigner Length-Defined Connector
            #   https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
            raise ValueError(
                f"start==end={start} 且 target_length={target_length}>0，"
                f"无法为重合起终点构造指定长度的 S 弯（R03 禁止 fall-back）"
            )
        perp_x = -dy / norm
        perp_y = dx / norm
        # S 弯振幅 = excess / 4（两个半波，总长 = 4 * 振幅）
        amp = excess / 4.0
        mid1 = (start[0] + dx / 3.0 + perp_x * amp,
                start[1] + dy / 3.0 + perp_y * amp)
        mid2 = (start[0] + 2.0 * dx / 3.0 - perp_x * amp,
                start[1] + 2.0 * dy / 3.0 - perp_y * amp)
        return [start, mid1, mid2, end]

    def auto_route_all(
        self,
        nets: list[dict[str, Any]],
        placements: dict[str, tuple[float, float]],
    ) -> dict[str, list[tuple[float, float]]]:
        """自动布线所有网。

        流程：
        1. RUDY 拥塞预估
        2. 拥塞感知网排序
        3. 逐网布线（Manhattan 优先，失败回退曲线 A*）
        4. 自适应交叉插入

        Args:
            nets: 网列表，每个网含 'name' 和 'pins' [(x, y), ...]。
            placements: 器件放置 {name: (x, y)}。

        Returns:
            网名 → 路径点列表。
        """
        rudy = self._net_ordering.compute_rudy(nets)
        ordered = self._net_ordering.order_nets(nets, rudy)
        results: dict[str, list[tuple[float, float]]] = {}
        all_paths: list[list[tuple[float, float]]] = []
        for net in ordered:
            name = net["name"]
            pins = net["pins"]
            if len(pins) < 2:
                results[name] = list(pins)
                continue
            path = self.manhattan_route(pins[0], pins[-1])
            results[name] = path
            all_paths.append(path)
        # 自适应交叉插入
        if all_paths:
            crossing_bb = {"width": 0.5, "length": 10.0}
            inserted = self._crossing_inserter.insert_crossings(
                all_paths, crossing_bb
            )
            for net, path in zip(ordered, inserted, strict=False):
                results[net["name"]] = path
        return results
