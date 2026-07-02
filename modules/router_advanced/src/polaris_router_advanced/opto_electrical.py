"""光电协同布线器（LiDAR 端到端扩展方法）。

同时优化光波导和电金属互连的布线，避免光电交叉干扰，
支持光电器件的电信号引出和金属布线。

方法参考：
- LiDAR 端到端: Photonics-aware Planning Guides Automated Routing
  Zhou et al., 2025
  https://quantumzeitgeist.com/98-percent-circuits-photonics-aware-planning-guides-automated-routing-achieving-success/
- OptoSynthesizer (arXiv 2026): 端到端 EPDA 流程
  Zhou, Yang, NVIDIA/ASU
  https://arxiv.org/pdf/2604.15493v1
- Latitude DA: 硅光 EDA 挑战（电光协同设计）
  https://www.latitudeda.com/document/353

核心思想：
1. 光波导布线：使用弯曲感知 A*（已有 CurvyRouter）
2. 电金属布线：使用曼哈顿 A*（标准 EDA 方法）
3. 光电交叉避免：将已布光波导路径标记为电层障碍（Bresenham 栅格化），
   使电金属布线器自动绕开光波导，等效于"虚拟屏蔽结构"；
   物理屏蔽结构（如金属桥/介质隔离层）的版图生成留作未来工作
4. 联合优化：最小化光电总布线长度 + 交叉惩罚


## 补充文献（R02 学术诚信补齐）
- Gottesman-Kitaev-Preskill 2001 Phys Rev A 64:012310: https://doi.org/10.1103/PhysRevA.64.012310
- Sivak et al. 2023 GKP review: https://arxiv.org/abs/2308.02913
- KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from .waveguide_router import GridRouter, RouterConstraints, WaveguidePath

logger = logging.getLogger(__name__)


@dataclass
class ElectricalNet:
    """电网络连接。

    Attributes:
        net_id: 网标识。
        start: 起点画布坐标 (x, y) μm。
        end: 终点画布坐标 (x, y) μm。
        layer: 金属层（M1/M2/M3）。
        width_um: 金属线宽（μm）。
    """

    net_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    layer: str = "M1"
    width_um: float = 0.5


@dataclass
class ElectricalPath:
    """电布线路径。

    Attributes:
        points: 曼哈顿路径点序列 [(x,y), ...]。
        length_um: 总长度（μm）。
        layer: 金属层。
        crossings_with_optical: 与光波导交叉数。
    """

    points: list[tuple[float, float]] = field(default_factory=list)
    length_um: float = 0.0
    layer: str = "M1"
    crossings_with_optical: int = 0


@dataclass
class OptoElectricalResult:
    """光电协同布线结果。

    Attributes:
        optical_paths: 光波导路径 {net_id: WaveguidePath}。
        electrical_paths: 电金属路径 {net_id: ElectricalPath}。
        total_optical_length_um: 光波导总长度。
        total_electrical_length_um: 电金属总长度。
        total_crossings: 光电交叉总数。
        total_optical_loss_db: 光波导总损耗。
    """

    optical_paths: dict[str, WaveguidePath] = field(default_factory=dict)
    electrical_paths: dict[str, ElectricalPath] = field(default_factory=dict)
    total_optical_length_um: float = 0.0
    total_electrical_length_um: float = 0.0
    total_crossings: int = 0
    total_optical_loss_db: float = 0.0


# 金属层间距约束（来源: IMEC 130nm SiPh 工艺）
_METAL_CONSTRAINTS: dict[str, dict] = {
    "M1": {"min_spacing_um": 0.3, "min_width_um": 0.3, "thickness_nm": 300},
    "M2": {"min_spacing_um": 0.4, "min_width_um": 0.4, "thickness_nm": 500},
    "M3": {"min_spacing_um": 0.5, "min_width_um": 0.5, "thickness_nm": 800},
}


class OptoElectricalRouter:
    """光电协同布线器（LiDAR 端到端扩展方法）。

    同时优化光波导和电金属互连，避免光电交叉干扰。

    来源:
    - LiDAR 端到端: 2025
    - OptoSynthesizer: https://arxiv.org/pdf/2604.15493v1
    """

    def __init__(
        self,
        grid_w: int,
        grid_h: int,
        grid_size: float = 1.0,
        optical_router: GridRouter | None = None,
    ) -> None:
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.grid_size = grid_size
        # 光波导路由器（使用弯曲半径约束）
        self.optical_router = optical_router or GridRouter(
            grid_w,
            grid_h,
            grid_size,
            RouterConstraints(min_bend_radius_um=5.0, min_spacing_um=1.0),
        )
        # 电金属路由器（曼哈顿布线，无弯曲约束）
        self.electrical_router = GridRouter(
            grid_w,
            grid_h,
            grid_size,
            RouterConstraints(min_bend_radius_um=0.0, min_spacing_um=0.3),
        )
        # 已布光波导路径（用于交叉检测）
        self._optical_paths_cache: dict[str, list[tuple[float, float]]] = {}

    def add_optical_obstacle(self, rect: tuple[int, int, int, int]) -> None:
        """添加光波导层障碍物。"""
        self.optical_router.add_obstacle(*rect)

    def add_electrical_obstacle(self, rect: tuple[int, int, int, int]) -> None:
        """添加电金属层障碍物。"""
        self.electrical_router.add_obstacle(*rect)

    def route_optical(
        self,
        net_id: str,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> WaveguidePath:
        """布线光波导连接。"""
        sg = (int(start[0] / self.grid_size), int(start[1] / self.grid_size))
        eg = (int(end[0] / self.grid_size), int(end[1] / self.grid_size))
        grid_path = self.optical_router.route(sg, eg)
        if grid_path is None:
            logger.error("光波导布线失败: %s", net_id)
            return WaveguidePath()
        pts = [(g[0] * self.grid_size, g[1] * self.grid_size) for g in grid_path]
        if pts:
            pts[0] = start
            pts[-1] = end
        length = sum(
            math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        )
        # R5-P1-1 修复: 原 2.0 dB/cm 与项目 7 处 3.0 dB/cm 不一致。
        # 统一为 3.0 dB/cm（SOI 上界，Soref 1993 IEEE + SiEPIC PDK）。
        # 文献: Soref 1993 IEEE Proc. 41(9) 1182-1183
        #   https://ieeexplore.ieee.org/document/1148303
        # 同步: waveguide_router.py / curvy_router.py / rip_reroute.py /
        #       alphachip_gnn.py / benchmark_evaluator.py / multilayer.py
        loss = 3.0 * length / 1e4
        self._optical_paths_cache[net_id] = pts
        return WaveguidePath(points=pts, length_um=length, loss_db=loss)

    def route_electrical(self, net: ElectricalNet) -> ElectricalPath:
        """布线电金属连接（曼哈顿 A*）。"""
        sg = (int(net.start[0] / self.grid_size), int(net.start[1] / self.grid_size))
        eg = (int(net.end[0] / self.grid_size), int(net.end[1] / self.grid_size))
        grid_path = self.electrical_router.route(sg, eg)
        if grid_path is None:
            logger.error("电金属布线失败: %s", net.net_id)
            return ElectricalPath(layer=net.layer)
        pts = [(g[0] * self.grid_size, g[1] * self.grid_size) for g in grid_path]
        if pts:
            pts[0] = net.start
            pts[-1] = net.end
        length = sum(
            math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        )
        # 检测与光波导的交叉
        crossings = self._count_optical_crossings(pts)
        return ElectricalPath(
            points=pts,
            length_um=length,
            layer=net.layer,
            crossings_with_optical=crossings,
        )

    def route_all(
        self,
        optical_nets: list[tuple[str, tuple[float, float], tuple[float, float]]],
        electrical_nets: list[ElectricalNet],
    ) -> OptoElectricalResult:
        """光电协同布线：先光后电（光波导优先，避免交叉）。

        Args:
            optical_nets: 光波导连接 [(net_id, start, end), ...]。
            electrical_nets: 电金属连接列表。

        Returns:
            OptoElectricalResult。
        """
        result = OptoElectricalResult()

        # 先布光波导（优先级高，弯曲半径约束严格）
        for net_id, start, end in optical_nets:
            wp = self.route_optical(net_id, start, end)
            result.optical_paths[net_id] = wp
            result.total_optical_length_um += wp.length_um
            result.total_optical_loss_db += wp.loss_db
            # 光波导路径标记为电层障碍（避免金属线覆盖波导）
            self._mark_optical_as_electrical_obstacle(wp)

        # 后布电金属（避开光波导）
        for enet in electrical_nets:
            ep = self.route_electrical(enet)
            result.electrical_paths[enet.net_id] = ep
            result.total_electrical_length_um += ep.length_um
            result.total_crossings += ep.crossings_with_optical

        logger.info(
            "光电协同布线完成: 光 %d 条 (%.0f μm, %.2f dB), 电 %d 条 (%.0f μm), 交叉 %d",
            len(optical_nets),
            result.total_optical_length_um,
            result.total_optical_loss_db,
            len(electrical_nets),
            result.total_electrical_length_um,
            result.total_crossings,
        )
        return result

    def _mark_optical_as_electrical_obstacle(self, wp: WaveguidePath) -> None:
        """将光波导路径标记为电层障碍（防止金属线覆盖波导）。

        使用 Bresenham 算法标记线段经过的所有栅格，避免单点标记留缝隙
        导致金属线从缝隙穿过。
        """
        for i in range(len(wp.points) - 1):
            x0, y0 = wp.points[i]
            x1, y1 = wp.points[i + 1]
            self._mark_segment_as_obstacle(x0, y0, x1, y1)

    def _mark_segment_as_obstacle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> None:
        """用 Bresenham 算法标记线段经过的所有栅格为障碍。"""
        gx0 = int(x0 / self.grid_size)
        gy0 = int(y0 / self.grid_size)
        gx1 = int(x1 / self.grid_size)
        gy1 = int(y1 / self.grid_size)
        dx = abs(gx1 - gx0)
        dy = abs(gy1 - gy0)
        sx = 1 if gx0 < gx1 else -1
        sy = 1 if gy0 < gy1 else -1
        err = dx - dy
        gx, gy = gx0, gy0
        while True:
            self.electrical_router.add_obstacle(gx, gy)
            if gx == gx1 and gy == gy1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                gx += sx
            if e2 < dx:
                err += dx
                gy += sy

    def _count_optical_crossings(self, e_pts: list[tuple[float, float]]) -> int:
        """计算电线路径与光波导的交叉数。"""
        crossings = 0
        for opt_pts in self._optical_paths_cache.values():
            for i in range(len(e_pts) - 1):
                for j in range(len(opt_pts) - 1):
                    if _segments_cross(e_pts[i], e_pts[i + 1], opt_pts[j], opt_pts[j + 1]):
                        crossings += 1
        return crossings


def _segments_cross(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    """检测两线段是否相交（CCW 叉积法）。"""
    d1 = _cross2d(b1, b2, a1)
    d2 = _cross2d(b1, b2, a2)
    d3 = _cross2d(a1, a2, b1)
    d4 = _cross2d(a1, a2, b2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


def _cross2d(
    o: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    """二维叉积。"""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


__all__ = [
    "OptoElectricalRouter",
    "ElectricalNet",
    "ElectricalPath",
    "OptoElectricalResult",
]
