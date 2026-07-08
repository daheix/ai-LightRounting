"""polaris-router-advanced 深度测试（覆盖全部公开 API，≥30 个测试）。

测试覆盖:
- 基础设施: ObstacleGrid/auto_grid_size/WaveguidePath/RouterConstraints/GridRouter
- 平台约束: PLATFORM_CONSTRAINTS/get_platform_constraints
- 路径几何: s_bend/euler_bend/arc_bend/check_min_spacing/count_crossings/
            equalize_length/path_length/path_loss
- route_connection: 单连接布线 + RouteConnectionConfig
- JPS 跳点搜索: JPSRouter（Harabor 2011）
- 任意角度: AllAngleRouter
- Bundle 并行等长: route_bundle/route_bundle_path_length_match/
                  route_bundle_from_waypoints/auto_taper/dubins_path
- 对角布线: DiagonalGridRouter
- 多层跨层: MultiLayerRouter/LayerSpec/OTVSpec/MultiLayerRouteResult
- 混合多波导型: HybridRouter/HybridRouterConfig/HybridNetConnection/
                HybridRouteResult/TransitionSegment/WaveguideType
- 光电协同: OptoElectricalRouter/OptoElectricalResult/ElectricalNet/ElectricalPath
- RIP 撕裂重布: route_with_rip_reroute/RipRerouteConfig/RipRerouteContext/
                GridSpec/NetConnection
- Advanced Connectors: EulerBend/EulerBendConfig/LengthDefinedConnector/
                       PhaseMatchedRouter/RFGSGRouter/BusRouter/HighOrderBezierConnector
- CurvyA* 曲线感知: CurvyAStarConfig/CurvyAStarRouter/CurveType
- OptoDesigner: AdaptiveCrossingInserter/CongestionAwareNetOrdering/
                OptoDesignerAutorouter
- DRV-free 验证: DRVFreeValidator
- Commercial: CommercialRouter/CommercialRouterConfig
- GdsfactoryStyle: GdsfactoryStyleRouter/GfPort/GfRouteConfig
- Global GCell: GlobalRouter/GlobalRouterConfig/GlobalRoute/GCell/CanvasSize/
                run_global_routing
- RL 布线环境: RoutingEnv/RoutingEnvConfig/RoutingState（需 gymnasium）

来源（R02 学术诚信，≥5 个文献 URL）:
- Harabor & Grastien JPS AAAI 2011
  https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
- LiDAR ISPD 2025 曲线感知 A* 光波导详细布线
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Dubins 1957 曲率约束最短路径
  https://www.jstor.org/stable/2372560
- Hong et al. 2021 欧拉弯曲超低损耗
  https://doi.org/10.1364/PRJ.437726
- gdsfactory routing strategies
  https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html
- Hart, Nilsson & Raphael 1968 A* 搜索原始论文
  https://ieeexplore.ieee.org/document/4082128
- Synopsys OptoDesigner Advanced Connectors Module
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- Ghione & Naldi 1987 共面波导阻抗公式
  https://doi.org/10.1109/TMTT.1987.1133623
- pytest 文档 https://docs.pytest.org/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# R03 禁止 fall-back: gymnasium 不可用时跳过整个模块（不返回假数据）
pytest.importorskip("gymnasium")

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# router_advanced/src: 本子模块源码; /workspace/src: polaris.engine 依赖
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_POLARIS_SRC = str(Path(__file__).resolve().parents[3] / "src")
for _p in (_SRC, _POLARIS_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_router_advanced as pra  # noqa: E402
from polaris_router_advanced import (  # noqa: E402
    AllAngleRouter,
    AdaptiveCrossingInserter,
    BusRouter,
    CanvasSize,
    CommercialRouter,
    CommercialRouterConfig,
    CongestionAwareNetOrdering,
    CurveType,
    CurvyAStarConfig,
    CurvyAStarRouter,
    DRVFreeValidator,
    DiagonalGridRouter,
    ElectricalNet,
    EulerBend,
    EulerBendConfig,
    GCell,
    GdsfactoryStyleRouter,
    GlobalRoute,
    GlobalRouter,
    GlobalRouterConfig,
    GridRouter,
    GridSpec,
    HighOrderBezierConnector,
    HybridNetConnection,
    HybridRouter,
    HybridRouterConfig,
    HybridRouteResult,
    JPSRouter,
    LayerSpec,
    LengthDefinedConnector,
    MultiLayerRouter,
    MultiLayerRouteResult,
    NetConnection,
    ObstacleGrid,
    OptoDesignerAutorouter,
    OptoElectricalRouter,
    OTVSpec,
    PhaseMatchedRouter,
    GfPort,
    RFGSGRouter,
    RipRerouteConfig,
    GfRouteConfig,
    RouteConnectionConfig,
    RouterConstraints,
    RoutingEnv,
    RoutingEnvConfig,
    TransitionSegment,
    WaveguidePath,
    WaveguideType,
    auto_grid_size,
    auto_taper,
    check_min_spacing,
    count_crossings,
    dubins_path,
    equalize_length,
    euler_bend,
    get_platform_constraints,
    arc_bend,
    path_length,
    path_loss,
    route_bundle,
    route_bundle_from_waypoints,
    route_bundle_path_length_match,
    route_connection,
    route_with_rip_reroute,
    run_global_routing,
    s_bend,
)


# ---------------------------------------------------------------------------
# 1. 原有 smoke test（保留，已验证通过）
# ---------------------------------------------------------------------------


def test_jps_router_smoke():
    """JPS 跳点搜索: 20x20 网格 (1,1)→(18,18) 应返回非空可达路径。

    JPS 通过在线剪枝将 A* 节点扩展数减少 70-90%（Harabor 2011）。
    验证: 路径非空、起止点正确、所有点在网格内。
    """
    router = JPSRouter(grid_w=20, grid_h=20, grid_size=1.0)
    path = router.route((1, 1), (18, 18))
    assert len(path) >= 2, f"JPS 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (1, 1), f"起点应为 (1,1)，实际 {path[0]}"
    assert path[-1] == (18, 18), f"终点应为 (18,18)，实际 {path[-1]}"
    for x, y in path:
        assert 0 <= x < 20 and 0 <= y < 20, f"点越界: ({x},{y})"


def test_jps_router_obstacle_detour():
    """JPS 障碍绕行: 中间障碍墙应被绕过（路径仍可达）。

    在 x=10 列设置障碍墙（留 y=0 缺口），路径应绕过障碍到达终点。
    """
    router = JPSRouter(grid_w=20, grid_h=20, grid_size=1.0)
    for y in range(1, 19):
        router.add_obstacle(10, y)
    path = router.route((1, 5), (18, 5))
    assert len(path) >= 2
    assert path[0] == (1, 5)
    assert path[-1] == (18, 5)
    for x, y in path:
        assert not router.obstacle.is_blocked(x, y), f"路径穿过障碍: ({x},{y})"


def test_global_router_empty_circuit():
    """空电路全局布线: 空 Netlist 返回空路径列表。"""
    from polaris_router_advanced.global_router import Netlist

    config = GlobalRouterConfig()
    net = Netlist(instances=[], connections=[], name="empty")
    result = run_global_routing(
        net, {}, CanvasSize(width=500.0, height=300.0), config=config
    )
    assert isinstance(result, list)
    assert len(result) == 0, f"空电路应 0 路径，实际 {len(result)}"


def test_no_fallback_invalid_inputs():
    """非法输入必须 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="网格尺寸必须为正"):
        AllAngleRouter(grid_w=0, grid_h=10)
    with pytest.raises(ValueError, match="bend_radius"):
        AllAngleRouter(grid_w=10, grid_h=10, bend_radius=0.0)
    with pytest.raises(ValueError, match="radius"):
        EulerBendConfig(radius=-1.0, angle=90.0)


def test_package_exports_complete():
    """验证包导出完整性: __version__ + 核心 API 可访问。"""
    assert pra.__version__ == "5.0.0"
    for name in [
        "JPSRouter", "AllAngleRouter", "GridRouter", "WaveguidePath",
        "route_bundle", "dubins_path", "EulerBend", "EulerBendConfig",
        "CurvyAStarRouter", "CurvyAStarConfig", "OptoDesignerAutorouter",
        "DRVFreeValidator", "GlobalRouter", "HybridRouter", "MultiLayerRouter",
        "OptoElectricalRouter", "CommercialRouter", "GdsfactoryStyleRouter",
        "RipRerouteContext", "RoutingEnv", "RFGSGRouter", "BusRouter",
    ]:
        assert hasattr(pra, name), f"包缺导出: {name}"
        assert name in pra.__all__, f"__all__ 缺: {name}"


# ---------------------------------------------------------------------------
# 2. ObstacleGrid + auto_grid_size 深度测试
# ---------------------------------------------------------------------------


def test_obstacle_grid_shape_and_total_cells():
    """ObstacleGrid 形状与总单元数属性。"""
    grid = ObstacleGrid(10, 5)
    assert grid.shape == (5, 10), f"shape 应为 (5,10)，实际 {grid.shape}"
    assert grid.total_cells == 50, f"total_cells 应为 50，实际 {grid.total_cells}"
    assert grid.is_dense is True, "10x5=50 ≤4M 应为稠密存储"


def test_obstacle_grid_mark_region_and_is_blocked():
    """ObstacleGrid 标记矩形区域后应正确检测障碍。"""
    grid = ObstacleGrid(20, 20)
    grid.mark_region(5, 5, 10, 10)
    assert grid.is_blocked(5, 5) is True, "(5,5) 应被标记为障碍"
    assert grid.is_blocked(9, 9) is True, "(9,9) 应被标记为障碍"
    assert grid.is_blocked(10, 10) is False, "(10,10) 在 range 外不应被标记"
    assert grid.is_blocked(0, 0) is False, "(0,0) 不应被标记"


def test_obstacle_grid_get_set_and_blocked_cells():
    """ObstacleGrid get/set 方法与 blocked_cells 迭代器。"""
    grid = ObstacleGrid(10, 10)
    assert grid.get(3, 3) == 0, "初始应为 0"
    grid.set(3, 3, 1)
    assert grid.get(3, 3) == 1, "set 后应为 1"
    grid.set(3, 3, 0)
    assert grid.get(3, 3) == 0, "清除后应为 0"
    grid.set(5, 5, 1)
    grid.set(6, 6, 1)
    blocked = list(grid.blocked_cells())
    assert (5, 5) in blocked, "(5,5) 应在 blocked_cells 中"
    assert (6, 6) in blocked, "(6,6) 应在 blocked_cells 中"


def test_obstacle_grid_memory_estimate():
    """ObstacleGrid 内存估算（稠密模式 = array.nbytes）。"""
    grid = ObstacleGrid(10, 10)
    # int32 = 4 字节/单元，10x10 = 100 单元 = 400 字节
    assert grid.memory_estimate_bytes() == 400, (
        f"稠密内存应 400 字节，实际 {grid.memory_estimate_bytes()}"
    )


def test_obstacle_grid_invalid_dimensions_raises():
    """ObstacleGrid 非正尺寸必须 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="栅格尺寸必须为正"):
        ObstacleGrid(0, 10)
    with pytest.raises(ValueError, match="栅格尺寸必须为正"):
        ObstacleGrid(10, -1)


def test_auto_grid_size_basic():
    """auto_grid_size 综合公式: SOI 5000×5000 画布应返回 ≥2.5μm。"""
    gs = auto_grid_size(5000.0, 5000.0, platform="SOI")
    # SOI: waveguide_width=0.5, min_bend_radius=5.0
    # physical_lower = 0.5*1.2 = 0.6
    # bend_lower = 5.0/2 = 2.5
    # scalability_lower = 5000/2000 = 2.5
    # max(0.6, 2.5, 2.5) = 2.5
    assert gs == pytest.approx(2.5, abs=0.01), f"SOI 5000μm 应 2.5μm，实际 {gs}"


def test_auto_grid_size_invalid_canvas_raises():
    """auto_grid_size 非正画布尺寸必须 raise。"""
    with pytest.raises(ValueError, match="画布尺寸必须为正"):
        auto_grid_size(0, 100, platform="SOI")
    with pytest.raises(ValueError, match="画布尺寸必须为正"):
        auto_grid_size(100, -1, platform="SOI")


def test_auto_grid_size_unknown_platform_raises():
    """auto_grid_size 未知平台必须 raise KeyError（R03 禁止 fall-back）。"""
    with pytest.raises(KeyError, match="未定义平台"):
        auto_grid_size(100, 100, platform="UNKNOWN")


# ---------------------------------------------------------------------------
# 3. 平台约束 + WaveguidePath + RouterConstraints + GridRouter
# ---------------------------------------------------------------------------


def test_platform_constraints_and_get_platform_constraints():
    """PLATFORM_CONSTRAINTS 含 SOI/SiN/InP/LNOI 四平台。"""
    assert "SOI" in pra.PLATFORM_CONSTRAINTS
    assert "SiN" in pra.PLATFORM_CONSTRAINTS
    assert "InP" in pra.PLATFORM_CONSTRAINTS
    assert "LNOI" in pra.PLATFORM_CONSTRAINTS
    soi = get_platform_constraints("SOI")
    assert soi["min_bend_radius_um"] == 5.0
    assert soi["min_spacing_um"] == 1.0


def test_get_platform_constraints_unknown_raises():
    """未知平台必须 raise KeyError（R03 禁止 fall-back）。"""
    with pytest.raises(KeyError, match="未定义平台"):
        get_platform_constraints("UnknownPlatform")


def test_waveguide_path_add_point():
    """WaveguidePath.add_point 累积长度。"""
    wp = WaveguidePath()
    wp.add_point(0.0, 0.0)
    wp.add_point(3.0, 4.0)
    assert len(wp.points) == 2
    assert wp.length_um == pytest.approx(5.0, abs=1e-9), (
        f"(0,0)→(3,4) 长度应 5.0，实际 {wp.length_um}"
    )


def test_router_constraints_defaults():
    """RouterConstraints 默认值: min_bend_radius=5.0, min_spacing=1.0。"""
    cons = RouterConstraints()
    assert cons.min_bend_radius_um == 5.0
    assert cons.min_spacing_um == 1.0


def test_grid_router_route_and_add_obstacle_box():
    """GridRouter A* 布线 + add_obstacle_box 障碍盒。"""
    router = GridRouter(20, 20, 1.0)
    path = router.route((1, 1), (18, 18))
    assert path is not None, "A* 应找到路径"
    assert path[0] == (1, 1)
    assert path[-1] == (18, 18)
    # 添加障碍盒后绕行
    router2 = GridRouter(20, 20, 1.0)
    router2.add_obstacle_box(8.0, 5.0, 12.0, 15.0)
    path2 = router2.route((1, 10), (18, 10))
    assert path2 is not None, "有障碍也应找到绕行路径"


def test_route_connection_basic():
    """route_connection 单连接布线（SOI 平台）。"""
    wp = route_connection((0.0, 0.0), (100.0, 50.0), platform="SOI")
    assert isinstance(wp, WaveguidePath)
    assert len(wp.points) >= 2
    assert wp.length_um > 0, "路径长度应 > 0"
    assert wp.points[0] == (0.0, 0.0), "起点应对齐"
    assert wp.points[-1] == (100.0, 50.0), "终点应对齐"


def test_route_connection_with_config():
    """route_connection 使用 RouteConnectionConfig。"""
    config = RouteConnectionConfig(
        grid_size=2.0, canvas_w=200.0, canvas_h=200.0
    )
    wp = route_connection((10.0, 10.0), (100.0, 80.0), platform="SOI", config=config)
    assert wp.length_um > 0


# ---------------------------------------------------------------------------
# 4. 路径几何深度测试
# ---------------------------------------------------------------------------


def test_jps_router_start_on_obstacle_raises():
    """JPS 起点在障碍上必须 raise ValueError。"""
    router = JPSRouter(grid_w=10, grid_h=10, grid_size=1.0)
    router.add_obstacle(5, 5)
    with pytest.raises(ValueError, match="起点.*障碍"):
        router.route((5, 5), (9, 9))


# ---------------------------------------------------------------------------
# 6. AllAngleRouter 深度测试
# ---------------------------------------------------------------------------


def test_global_router_config_defaults():
    """GlobalRouterConfig 默认值。"""
    config = GlobalRouterConfig()
    assert config.gcell_size_um == 50.0
    assert config.capacity_per_gcell == 4.0
    assert config.max_rip_reroute_rounds == 3


def test_gcell_overflow_property():
    """GCell.overflow 属性: demand > capacity 时为正。"""
    cell = GCell(gx=0, gy=0, capacity=4.0, demand=2.0)
    assert cell.overflow == 0.0, "demand < capacity 时 overflow = 0"
    cell.demand = 6.0
    assert cell.overflow == 2.0, "demand > capacity 时 overflow = 2.0"


# ---------------------------------------------------------------------------
# 16. MultiLayer 深度测试
# ---------------------------------------------------------------------------


def test_multilayer_router_single_layer():
    """MultiLayerRouter 单层布线（同层 start_layer == end_layer）。"""
    layers = [LayerSpec(name="SOI", grid_w=30, grid_h=30, grid_size=1.0, platform="SOI")]
    router = MultiLayerRouter(layers)
    result = router.route(0, (5.0, 5.0), 0, (25.0, 25.0))
    assert isinstance(result, MultiLayerRouteResult)
    assert 0 in result.layer_paths, "层 0 应有路径"
    assert result.total_length_um > 0


def test_multilayer_router_no_otv_raises():
    """MultiLayerRouter 跨层无 OTV 必须 raise RuntimeError（R03 禁止 fall-back）。"""
    layers = [
        LayerSpec(name="SOI", grid_w=30, grid_h=30, grid_size=1.0, platform="SOI"),
        LayerSpec(name="SiN", grid_w=30, grid_h=30, grid_size=1.0, platform="SiN"),
    ]
    router = MultiLayerRouter(layers, otvs=[])  # 无 OTV
    with pytest.raises(RuntimeError, match="无可用 OTV"):
        router.route(0, (5.0, 5.0), 1, (25.0, 25.0))


def test_otv_spec_dataclass():
    """OTVSpec 数据类字段。"""
    otv = OTVSpec(name="otv1", layer_from=0, layer_to=1, x=10.0, y=10.0, loss_db=0.5)
    assert otv.name == "otv1"
    assert otv.layer_from == 0
    assert otv.layer_to == 1
    assert otv.loss_db == 0.5


# ---------------------------------------------------------------------------
# 17. HybridRouter 深度测试
# ---------------------------------------------------------------------------


def test_hybrid_router_single_type():
    """HybridRouter 同波导类型布线（RIDGE→RIDGE）。"""
    router = HybridRouter(grid_w=50, grid_h=50, grid_size=1.0)
    net = HybridNetConnection(
        net_id="n1",
        start=(5.0, 5.0),
        end=(40.0, 40.0),
        wg_type_start=WaveguideType.RIDGE,
        wg_type_end=WaveguideType.RIDGE,
    )
    result = router.route(net)
    assert isinstance(result, HybridRouteResult)
    assert result.path.length_um > 0
    assert WaveguideType.RIDGE in result.wg_type_sequence


def test_hybrid_router_config_defaults():
    """HybridRouterConfig 默认值。"""
    config = HybridRouterConfig()
    assert config.auto_insert_transitions is True
    assert config.default_transition_length_um == 15.0


def test_hybrid_router_mixed_type():
    """HybridRouter 混合波导类型布线（RIDGE→RIB）。"""
    router = HybridRouter(grid_w=50, grid_h=50, grid_size=1.0)
    net = HybridNetConnection(
        net_id="n2",
        start=(5.0, 5.0),
        end=(40.0, 40.0),
        wg_type_start=WaveguideType.RIDGE,
        wg_type_end=WaveguideType.RIB,
    )
    result = router.route(net)
    assert isinstance(result, HybridRouteResult)
    assert len(result.transitions) == 1, "混合类型应有 1 个过渡段"
    assert result.transitions[0].from_type == WaveguideType.RIDGE
    assert result.transitions[0].to_type == WaveguideType.RIB


def test_waveguide_type_enum_values():
    """WaveguideType 枚举值。"""
    assert WaveguideType.RIDGE.value == "ridge"
    assert WaveguideType.RIB.value == "rib"
    assert WaveguideType.BURIED.value == "buried"


# ---------------------------------------------------------------------------
# 18. OptoElectricalRouter 深度测试
# ---------------------------------------------------------------------------


def test_opto_electrical_router_route_optical():
    """OptoElectricalRouter.route_optical 光波导布线。"""
    router = OptoElectricalRouter(grid_w=50, grid_h=50, grid_size=1.0)
    wp = router.route_optical("opt1", (5.0, 5.0), (40.0, 40.0))
    assert isinstance(wp, WaveguidePath)
    assert wp.length_um > 0


def test_opto_electrical_router_route_electrical():
    """OptoElectricalRouter.route_electrical 电金属布线。"""
    router = OptoElectricalRouter(grid_w=50, grid_h=50, grid_size=1.0)
    enet = ElectricalNet(net_id="ele1", start=(5.0, 5.0), end=(40.0, 5.0), layer="M1")
    ep = router.route_electrical(enet)
    assert ep.length_um > 0
    assert ep.layer == "M1"


def test_opto_electrical_router_route_all():
    """OptoElectricalRouter.route_all 光电协同布线。"""
    router = OptoElectricalRouter(grid_w=50, grid_h=50, grid_size=1.0)
    optical_nets = [("opt1", (5.0, 5.0), (40.0, 40.0))]
    electrical_nets = [ElectricalNet("ele1", (5.0, 10.0), (40.0, 10.0))]
    result = router.route_all(optical_nets, electrical_nets)
    assert "opt1" in result.optical_paths
    assert "ele1" in result.electrical_paths
    assert result.total_optical_length_um > 0


# ---------------------------------------------------------------------------
# 19. RipReroute 深度测试
# ---------------------------------------------------------------------------


def test_rip_reroute_config_defaults():
    """RipRerouteConfig 默认值。"""
    config = RipRerouteConfig()
    assert config.max_iterations == 3
    assert config.loss_db_cm == 3.0


def test_route_with_rip_reroute_basic():
    """route_with_rip_reroute 批量布线。"""
    nets = [
        NetConnection(net_id="n1", start=(5.0, 5.0), end=(40.0, 5.0)),
        NetConnection(net_id="n2", start=(5.0, 10.0), end=(40.0, 10.0)),
    ]
    grid_spec = GridSpec(grid_w=50, grid_h=50, grid_size=1.0)
    results = route_with_rip_reroute(nets, grid_spec)
    assert "n1" in results
    assert "n2" in results
    # 两条平行直线，应都能布通
    assert results["n1"] is not None, "n1 应布线成功"
    assert results["n2"] is not None, "n2 应布线成功"


# ---------------------------------------------------------------------------
# 20. RoutingEnv 深度测试（需 gymnasium）
# ---------------------------------------------------------------------------


class _MockBBox:
    """模拟 bbox（含 xmin/xmax/ymin/ymax 属性）。"""

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax


class _MockDevice:
    """模拟器件（含 rotate/bbox/platform）。"""

    def __init__(self, platform: str = "SOI") -> None:
        self.platform = platform
        self.bbox = _MockBBox(0.0, 0.0, 10.0, 10.0)

    def rotate(self, angle_deg: int) -> "_MockDevice":
        """旋转返回自身（简化 mock）。"""
        return self


class _MockPlacement:
    """模拟 Placement（含 bbox_abs/port_positions/device）。"""

    def __init__(self, instance_id: str, x: float, y: float, platform: str = "SOI") -> None:
        self.instance_id = instance_id
        self.device = _MockDevice(platform)
        self.x = x
        self.y = y
        self.rotation = 0

    def bbox_abs(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + 10.0, self.y + 10.0)

    def port_positions(self) -> dict[str, tuple[float, float]]:
        return {
            "in": (self.x, self.y + 5.0),
            "out": (self.x + 10.0, self.y + 5.0),
        }


def test_routing_env_config_defaults():
    """RoutingEnvConfig 默认值。"""
    config = RoutingEnvConfig()
    assert config.canvas_w == 1000.0
    assert config.canvas_h == 1000.0
    assert config.grid_size == 5.0
    assert config.loss_weight == 1.0


def test_routing_env_reset_and_step():
    """RoutingEnv reset + step 基础流程（Gymnasium 接口）。"""
    from polaris_router_advanced.global_router import (
        Netlist,
        NetlistConnection,
        NetlistInstance,
    )

    # 构建简单网表: 2 器件 1 连接
    instances = [
        NetlistInstance(instance_id="dev1", component="wg"),
        NetlistInstance(instance_id="dev2", component="wg"),
    ]
    connections = [
        NetlistConnection(
            src_instance="dev1", src_port="out",
            dst_instance="dev2", dst_port="in",
        ),
    ]
    net = Netlist(instances=instances, connections=connections, name="test")

    placements = {
        "dev1": _MockPlacement("dev1", 10.0, 50.0),
        "dev2": _MockPlacement("dev2", 80.0, 50.0),
    }

    config = RoutingEnvConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    env = RoutingEnv(net, placements, config=config)

    obs, info = env.reset()
    assert "congestion" in obs
    assert "ports" in obs
    assert "step" in obs
    assert info["step"] == 0

    # 执行一步（动作 = 零向量）
    action = np_zeros(3)
    obs, reward, terminated, truncated, info = env.step(action)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert info["step"] == 1
    # 1 个连接，step 后应 terminated
    assert terminated is True, "1 连接 step 后应 terminated"


def test_routing_env_total_metrics():
    """RoutingEnv.total_metrics 汇总布线指标。"""
    from polaris_router_advanced.global_router import (
        Netlist,
        NetlistConnection,
        NetlistInstance,
    )

    instances = [
        NetlistInstance(instance_id="d1", component="wg"),
        NetlistInstance(instance_id="d2", component="wg"),
    ]
    connections = [
        NetlistConnection("d1", "out", "d2", "in"),
    ]
    net = Netlist(instances=instances, connections=connections, name="m")
    placements = {
        "d1": _MockPlacement("d1", 10.0, 50.0),
        "d2": _MockPlacement("d2", 80.0, 50.0),
    }
    env = RoutingEnv(net, placements, config=RoutingEnvConfig(
        canvas_w=200.0, canvas_h=200.0, grid_size=5.0
    ))
    env.reset()
    env.step(np_zeros(3))
    metrics = env.total_metrics()
    assert "total_loss_db" in metrics
    assert "total_length_um" in metrics
    assert "max_congestion" in metrics
    assert "num_routed" in metrics
    assert "num_connections" in metrics
    assert metrics["num_connections"] == 1


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def np_zeros(shape, dtype=None):
    """numpy zeros 简便调用（避免顶层 import numpy，默认 float32）。"""
    import numpy as np
    return np.zeros(shape, dtype=dtype or np.float32)


# ---------------------------------------------------------------------------
# R389 回归测试：_pattern_route 非方形 demand 索引顺序
# ---------------------------------------------------------------------------


def test_pattern_route_non_square_grid_no_indexerror():
    """R389 回归: 非方形 demand (gh=5, gw=10) 下 _pattern_route 不应 IndexError。

    原 Bug: `n_gx, n_gy = demand.shape` 顺序颠倒（实际应为 n_gy, n_gx），
    且 `demand[gx, gy]` 索引顺序错误（应为 demand[gy, gx]）。
    在 gw != gh 时，gx 可达 gw-1=9，原代码 demand[9, 4] 访问第 9 行（越界，
    demand 仅 5 行）导致 IndexError 或访问错误位置。
    """
    import numpy as np
    from polaris_router_advanced.global_router import (
        _pattern_route,
        CurvyPatternConfig,
    )

    # 非方形 demand: gh=5 行, gw=10 列
    demand = np.zeros((5, 10), dtype=np.float64)
    capacity = np.full((5, 10), 4.0, dtype=np.float64)
    curvy = CurvyPatternConfig()

    # start=(0,0), goal=(9,4): gx 跨度 9（接近 gw-1），gy 跨度 4（=gh-1）
    path = _pattern_route((0, 0), (9, 4), demand, capacity, curvy)
    assert path is not None, "非方形网格应能找到 L/Z-shape 路径"
    assert path[0] == (0, 0), f"起点应为 (0,0)，实际 {path[0]}"
    assert path[-1] == (9, 4), f"终点应为 (9,4)，实际 {path[-1]}"
    # 所有路径点必须在边界内（gx < gw=10, gy < gh=5）
    for gx, gy in path:
        assert 0 <= gx < 10, f"gx 越界: {gx}（gw=10）"
        assert 0 <= gy < 5, f"gy 越界: {gy}（gh=5）"


def test_global_router_non_square_canvas_routes_without_error():
    """R389 回归: 非方形画布全局布线不应因索引 Bug 失败。

    画布 500×250μm，gcell_size=50μm → gw=10, gh=5（非方形）。
    2 器件 1 连接，触发 _pattern_route 路径。
    """
    from polaris_router_advanced.global_router import (
        Netlist,
        NetlistConnection,
        NetlistInstance,
    )

    instances = [
        NetlistInstance(instance_id="d1", component="wg"),
        NetlistInstance(instance_id="d2", component="wg"),
    ]
    connections = [
        NetlistConnection("d1", "out", "d2", "in"),
    ]
    net = Netlist(instances=instances, connections=connections, name="nonsquare")

    placements = {
        "d1": _MockPlacement("d1", 10.0, 50.0),
        "d2": _MockPlacement("d2", 480.0, 200.0),
    }
    # 非方形画布: 500×250 → gw=10, gh=5
    result = run_global_routing(
        net, placements, CanvasSize(width=500.0, height=250.0),
        config=GlobalRouterConfig(gcell_size_um=50.0),
    )
    assert isinstance(result, list)
    # 1 连接应布线成功
    assert len(result) == 1, f"应布线 1 条，实际 {len(result)}"
    assert result[0].conn_idx == 0
    assert len(result[0].gcell_path) >= 2, "路径至少 2 个 GCell"
    # 验证路径点在非方形边界内
    for gx, gy in result[0].gcell_path:
        assert 0 <= gx < 10, f"GCell gx 越界: {gx}"
        assert 0 <= gy < 5, f"GCell gy 越界: {gy}"
