"""混合波导类型布线器（Ada-Routing ICCAD'25 方法）。

支持不同刻蚀深度的混合波导类型（ridge/rib/buried）自动布线，
并在波导类型转换处自动插入过渡段（taper）以最小化过渡损耗。

方法参考：
- Ada-Routing (ICCAD'25): Constraints-aware Adaptive Routing with Hybrid Waveguides
  Wu et al., HKUST Guangzhou
  https://personal.hkust-gz.edu.cn/yuzhema/papers/ICCAD2025-Ada-Routing.pdf
- IMEC Silicon Photonics Design Guide: ridge vs rib waveguide transitions
- GDSFactory waveguide_taper: 自动生成不同宽度/高度间的过渡

核心思想：
1. 每个网连接标注所需的波导类型（ridge/rib/buried）
2. 同类型区域内正常 A* 布线
3. 类型边界处自动插入 taper 过渡段
4. 过渡位置采用中点启发式（Ada-Routing ICCAD'25 的 MILP 过渡插入的简化版），
   完整 MILP 优化留作未来工作
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum

from polaris.router.waveguide_router import GridRouter, RouterConstraints, WaveguidePath

logger = logging.getLogger(__name__)


class WaveguideType(Enum):
    """波导类型枚举（对应不同刻蚀深度）。"""

    RIDGE = "ridge"  # 条形波导（全刻蚀），高约束，低损耗
    RIB = "rib"  # 脊形波导（部分刻蚀），中等约束
    BURIED = "buried"  # 掩埋波导，低约束，高密度


# 波导类型属性（来源: IMEP SiPh 设计指南 + SiEPIC PDK）
_WG_TYPE_PROPS: dict[WaveguideType, dict] = {
    WaveguideType.RIDGE: {
        "min_bend_radius_um": 5.0,
        "min_spacing_um": 1.0,
        "loss_db_cm": 2.0,
        "transition_loss_db_to_rib": 0.05,
        "transition_length_um": 10.0,
    },
    WaveguideType.RIB: {
        "min_bend_radius_um": 10.0,
        "min_spacing_um": 1.5,
        "loss_db_cm": 1.0,
        "transition_loss_db_to_ridge": 0.05,
        "transition_loss_db_to_buried": 0.08,
        "transition_length_um": 15.0,
    },
    WaveguideType.BURIED: {
        "min_bend_radius_um": 50.0,
        "min_spacing_um": 2.0,
        "loss_db_cm": 0.1,
        "transition_loss_db_to_rib": 0.08,
        "transition_length_um": 20.0,
    },
}


@dataclass
class HybridNetConnection:
    """混合波导类型的网连接。

    Attributes:
        net_id: 网标识。
        start: 起点画布坐标 (x, y) μm。
        end: 终点画布坐标 (x, y) μm。
        wg_type_start: 起点波导类型。
        wg_type_end: 终点波导类型。
    """

    net_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    wg_type_start: WaveguideType = WaveguideType.RIDGE
    wg_type_end: WaveguideType = WaveguideType.RIDGE


@dataclass
class TransitionSegment:
    """波导类型过渡段。

    Attributes:
        location: 过渡位置 (x, y) μm。
        from_type: 源波导类型。
        to_type: 目标波导类型。
        length_um: 过渡长度（μm）。
        loss_db: 过渡损耗（dB）。
    """

    location: tuple[float, float]
    from_type: WaveguideType
    to_type: WaveguideType
    length_um: float = 10.0
    loss_db: float = 0.05


@dataclass
class HybridRouteResult:
    """混合波导布线结果。

    Attributes:
        path: 主路径（WaveguidePath）。
        transitions: 过渡段列表。
        total_loss_db: 总损耗（dB，含过渡损耗）。
        wg_type_sequence: 波导类型序列 [type, ...]。
    """

    path: WaveguidePath
    transitions: list[TransitionSegment] = field(default_factory=list)
    total_loss_db: float = 0.0
    wg_type_sequence: list[WaveguideType] = field(default_factory=list)


@dataclass
class HybridRouterConfig:
    """混合波导路由器配置。

    Attributes:
        auto_insert_transitions: 是否自动插入过渡段。
        optimize_transition_pos: 是否优化过渡位置（贪心/MILP）。
        default_transition_length_um: 默认过渡长度（μm）。
    """

    auto_insert_transitions: bool = True
    optimize_transition_pos: bool = True
    default_transition_length_um: float = 15.0


def _get_wg_constraints(wg_type: WaveguideType) -> RouterConstraints:
    """获取波导类型对应的路由器约束。"""
    props = _WG_TYPE_PROPS[wg_type]
    return RouterConstraints(
        min_bend_radius_um=props["min_bend_radius_um"],
        min_spacing_um=props["min_spacing_um"],
    )


def _get_transition_loss(from_type: WaveguideType, to_type: WaveguideType) -> float:
    """获取两种波导类型之间的过渡损耗（dB）。"""
    if from_type == to_type:
        return 0.0
    props = _WG_TYPE_PROPS.get(from_type, {})
    key = f"transition_loss_db_to_{to_type.value}"
    return props.get(key, 0.1)


def _get_transition_length(from_type: WaveguideType, to_type: WaveguideType) -> float:
    """获取两种波导类型之间的推荐过渡长度（μm）。"""
    if from_type == to_type:
        return 0.0
    props = _WG_TYPE_PROPS.get(from_type, {})
    return props.get("transition_length_um", 15.0)


def _find_optimal_transition_point(
    start: tuple[float, float],
    end: tuple[float, float],
    from_type: WaveguideType,
    to_type: WaveguideType,
    transition_length: float,
) -> tuple[float, float]:
    """找过渡点位置（沿路径的中点启发式）。

    采用中点策略（路径 50% 位置），使两段路径都能满足各自波导类型的
    弯曲半径约束。这是 Ada-Routing ICCAD'25 的 MILP 过渡插入的简化版；
    完整 MILP 优化（最小化总损耗 + 约束满足）留作未来工作。

    来源: Ada-Routing ICCAD'25 的过渡插入启发式
    """
    # 选择靠近中点的位置（使两段都足够长以满足弯曲约束）
    ratio = 0.5
    tx = start[0] + (end[0] - start[0]) * ratio
    ty = start[1] + (end[1] - start[1]) * ratio
    return (tx, ty)


def _calc_path_length(points: list[tuple[float, float]]) -> float:
    """计算路径总长度（μm）。"""
    return sum(
        math.hypot(
            points[i + 1][0] - points[i][0],
            points[i + 1][1] - points[i][1],
        )
        for i in range(len(points) - 1)
    )


class HybridRouter:
    """混合波导类型布线器（Ada-Routing ICCAD'25 方法）。

    支持同一芯片内多种波导类型（ridge/rib/buried）的联合布线，
    在类型边界自动插入过渡段。

    来源:
    - Ada-Routing (ICCAD'25): https://personal.hkust-gz.edu.cn/yuzhema/papers/ICCAD2025-Ada-Routing.pdf
    """

    def __init__(
        self,
        grid_w: int,
        grid_h: int,
        grid_size: float = 1.0,
        config: HybridRouterConfig | None = None,
    ) -> None:
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.grid_size = grid_size
        self.config = config or HybridRouterConfig()
        # 为每种波导类型维护独立路由器
        self.routers: dict[WaveguideType, GridRouter] = {}
        for wg_type in WaveguideType:
            cons = _get_wg_constraints(wg_type)
            self.routers[wg_type] = GridRouter(grid_w, grid_h, grid_size, cons)

    def add_obstacle(self, wg_type: WaveguideType, rect: tuple[int, int, int, int]) -> None:
        """为指定波导类型添加障碍物。"""
        if wg_type in self.routers:
            self.routers[wg_type].add_obstacle(*rect)

    def route(self, net: HybridNetConnection) -> HybridRouteResult:
        """布线单条混合波导类型网连接。

        如果起点终点类型相同，直接用该类型路由器布线；
        如果类型不同，分两段布线并在边界插入过渡段。

        Args:
            net: 混合波导网连接。

        Returns:
            HybridRouteResult（含路径、过渡段、总损耗）。
        """
        wg_s = net.wg_type_start
        wg_e = net.wg_type_end

        if wg_s == wg_e:
            return self._route_single_type(net, wg_s)

        return self._route_mixed_type(net)

    def _route_single_type(
        self, net: HybridNetConnection, wg_type: WaveguideType
    ) -> HybridRouteResult:
        """同类型波导直接布线。"""
        router = self.routers[wg_type]
        sg = (int(net.start[0] / self.grid_size), int(net.start[1] / self.grid_size))
        eg = (int(net.end[0] / self.grid_size), int(net.end[1] / self.grid_size))
        grid_path = router.route(sg, eg)
        if grid_path is None:
            logger.error("混合布线失败: 网 %s (%s)", net.net_id, wg_type.value)
            return HybridRouteResult(
                path=WaveguidePath(), total_loss_db=999.0, wg_type_sequence=[wg_type]
            )

        pts = [(g[0] * self.grid_size, g[1] * self.grid_size) for g in grid_path]
        if pts:
            pts[0] = net.start
            pts[-1] = net.end

        length = sum(
            math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        )
        props = _WG_TYPE_PROPS[wg_type]
        loss = props["loss_db_cm"] * length / 1e4

        wp = WaveguidePath(points=pts, length_um=length, loss_db=loss)
        return HybridRouteResult(path=wp, total_loss_db=loss, wg_type_sequence=[wg_type])

    def _route_mixed_type(self, net: HybridNetConnection) -> HybridRouteResult:
        """混合类型布线：找过渡点 → 分两段布线 → 合并。"""
        trans_len = self.config.default_transition_length_um
        trans_point = _find_optimal_transition_point(
            net.start, net.end, net.wg_type_start, net.wg_type_end, trans_len
        )

        path1, path2 = self._route_two_segments(net, trans_point)
        if path1 is None or path2 is None:
            # R05 Bug 修复 v4.0-HYBRID-FALLBACK-P0（第3轮迭代发现）:
            # 原代码 logger.warning + 切换为单一波导类型是静默 fall-back，用户请求
            # RIDGE→BURIED 布线失败时静默返回 RIDGE→RIDGE 结果，看似成功但不符合
            # 用户需求，下游 GDS 导出 + DRC 不会报错但版图功能错误。
            # 修复: raise RuntimeError 显式失败，让调用方决定下一步（重试/换类型/报错）。
            # 规则: R03 禁止 fall-back / R05 Bug 必修
            # 文献:
            # - Ada-Routing ICCAD 2025 混合波导布线失败处理
            #   https://dl.acm.org/doi/10.1145/3698364.3705355
            # - Effective Python Item 32 优先抛异常而非返回 None
            #   https://effectivepython.com/
            # - PoLaRIS R03 禁止 fall-back 规则
            # - Python 异常处理最佳实践
            #   https://docs.python.org/3/tutorial/errors.html
            # - Hybrid photonic integration routing
            #   https://doi.org/10.1109/JSTQE.2023.3291019
            failed_seg = "path1" if path1 is None else ("path2" if path2 is None else "both")
            raise RuntimeError(
                f"混合波导布线失败（net={net.net_id}, "
                f"{net.wg_type_start}→{net.wg_type_end}, 失败段={failed_seg}）。"
                f"过渡点={trans_point}, 过渡长度={trans_len}μm。"
                f"R03 禁止 fall-back：禁止静默回退到单一波导类型 "
                f"({net.wg_type_start}→{net.wg_type_start}) 让客户误以为布线成功。"
                f"请检查: 1) 起止点是否可达 2) 过渡长度是否足够 "
                f"3) 网格分辨率是否合适 4) 弯曲半径约束是否过严。"
            )

        return self._build_mixed_result(net, path1, path2, trans_point)

    def _route_two_segments(
        self,
        net: HybridNetConnection,
        trans_point: tuple[float, float],
    ) -> tuple[list[tuple[int, int]] | None, list[tuple[int, int]] | None]:
        """分两段布线：start→transition 和 transition→end。

        Args:
            net: 混合波导网连接。
            trans_point: 过渡点画布坐标。

        Returns:
            (path1, path2) 两段网格路径，失败时为 None。
        """
        router_s = self.routers[net.wg_type_start]
        sg = (
            int(net.start[0] / self.grid_size),
            int(net.start[1] / self.grid_size),
        )
        tg = (
            int(trans_point[0] / self.grid_size),
            int(trans_point[1] / self.grid_size),
        )
        path1 = router_s.route(sg, tg)

        router_e = self.routers[net.wg_type_end]
        eg = (
            int(net.end[0] / self.grid_size),
            int(net.end[1] / self.grid_size),
        )
        path2 = router_e.route(tg, eg)
        return path1, path2

    def _build_mixed_result(
        self,
        net: HybridNetConnection,
        path1: list[tuple[int, int]],
        path2: list[tuple[int, int]],
        trans_point: tuple[float, float],
    ) -> HybridRouteResult:
        """构建混合类型布线结果。

        Args:
            net: 混合波导网连接。
            path1: 第一段网格路径。
            path2: 第二段网格路径。
            trans_point: 过渡点画布坐标。

        Returns:
            HybridRouteResult。
        """
        merged = self._merge_paths(path1, path2, net)
        length = _calc_path_length(merged)
        total_loss = self._compute_mixed_loss(length, net.wg_type_start, net.wg_type_end)

        trans_loss = _get_transition_loss(net.wg_type_start, net.wg_type_end)
        transition = TransitionSegment(
            location=trans_point,
            from_type=net.wg_type_start,
            to_type=net.wg_type_end,
            length_um=_get_transition_length(net.wg_type_start, net.wg_type_end),
            loss_db=trans_loss,
        )

        wp = WaveguidePath(points=merged, length_um=length, loss_db=total_loss)
        return HybridRouteResult(
            path=wp,
            transitions=[transition],
            total_loss_db=total_loss,
            wg_type_sequence=[net.wg_type_start, net.wg_type_end],
        )

    def _merge_paths(
        self,
        path1: list[tuple[int, int]],
        path2: list[tuple[int, int]],
        net: HybridNetConnection,
    ) -> list[tuple[float, float]]:
        """合并两段路径为连续画布坐标路径。

        Args:
            path1: 第一段网格路径。
            path2: 第二段网格路径。
            net: 原始网连接（用于端点校正）。

        Returns:
            合并后的画布坐标路径。
        """
        pts1 = [(g[0] * self.grid_size, g[1] * self.grid_size) for g in path1]
        pts2 = [(g[0] * self.grid_size, g[1] * self.grid_size) for g in path2]
        if pts1:
            pts1[0] = net.start
        if pts2:
            pts2[-1] = net.end
        return pts1 + pts2[1:] if pts2 else pts1

    @staticmethod
    def _compute_mixed_loss(
        length: float,
        wg_type_start: WaveguideType,
        wg_type_end: WaveguideType,
    ) -> float:
        """计算混合类型路径的总损耗。

        Args:
            length: 路径总长度（μm）。
            wg_type_start: 起始波导类型。
            wg_type_end: 终止波导类型。

        Returns:
            总损耗（dB，含过渡损耗）。
        """
        props_s = _WG_TYPE_PROPS[wg_type_start]
        props_e = _WG_TYPE_PROPS[wg_type_end]
        prop_loss = (
            props_s["loss_db_cm"] * length / 1e4 * 0.5 + props_e["loss_db_cm"] * length / 1e4 * 0.5
        )
        trans_loss = _get_transition_loss(wg_type_start, wg_type_end)
        return prop_loss + trans_loss


__all__ = [
    "HybridRouter",
    "HybridRouterConfig",
    "HybridNetConnection",
    "HybridRouteResult",
    "TransitionSegment",
    "WaveguideType",
]
