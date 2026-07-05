"""polaris-router-advanced 扩展测试（Advanced Connectors + Global + RL）。

从 test_router_advanced.py 拆分（R11 质量门禁，文件≤800行）。
覆盖: RFGSG/Bus/Bezier/CurvyA*/OptoDesigner/DRVFree/Commercial/
GdsfactoryStyle/Global/MultiLayer/Hybrid/OptoElectrical/RipReroute/RoutingEnv。

学术依据（R02 学术诚信，≥5 文献 URL）:
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
- Synopsys OptoDesigner Advanced Connectors Module
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- Ghione & Naldi 1987 共面波导阻抗公式
  https://doi.org/10.1109/TMTT.1987.1133623
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# R03 禁止 fall-back: gymnasium 不可用时跳过整个模块（不返回假数据）
pytest.importorskip("gymnasium")

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_POLARIS_SRC = str(Path(__file__).resolve().parents[3] / "src")
for _p in (_SRC, _POLARIS_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_router_advanced as pra  # noqa: E402,F401
from polaris_router_advanced import (  # noqa: E402
    AdaptiveCrossingInserter,
    BusRouter,
    CommercialRouter,
    CommercialRouterConfig,
    CongestionAwareNetOrdering,
    CurveType,
    CurvyAStarConfig,
    CurvyAStarRouter,
    DRVFreeValidator,
    ElectricalNet,
    GCell,
    GdsfactoryStyleRouter,
    GlobalRouterConfig,
    GridSpec,
    HighOrderBezierConnector,
    HybridNetConnection,
    HybridRouter,
    HybridRouterConfig,
    HybridRouteResult,
    LayerSpec,
    MultiLayerRouter,
    MultiLayerRouteResult,
    NetConnection,
    OptoDesignerAutorouter,
    OptoElectricalRouter,
    OTVSpec,
    GfPort,
    RFGSGRouter,
    RipRerouteConfig,
    GfRouteConfig,
    RoutingEnv,
    RoutingEnvConfig,
    TransitionSegment,
    WaveguidePath,
    WaveguideType,
    path_length,
    route_with_rip_reroute,
)


# ---------------------------------------------------------------------------
# 9. Advanced Connectors 深度测试（RFGSG / Bus / Bezier）
# ---------------------------------------------------------------------------


def test_rf_gsg_router_route_gsg():
    """RFGSGRouter.route_gsg 三导体共面波导。"""
    router = RFGSGRouter(signal_width=10.0, ground_width=20.0, gap=5.0)
    result = router.route_gsg((0.0, 0.0), (100.0, 0.0))
    assert "signal" in result
    assert "ground1" in result
    assert "ground2" in result
    assert len(result["signal"]) == 2
    assert result["signal"][0] == (0.0, 0.0)
    assert result["signal"][1] == (100.0, 0.0)


def test_rf_gsg_router_compute_impedance():
    """RFGSGRouter.compute_impedance 共面波导阻抗（Ghione & Naldi 1987）。"""
    router = RFGSGRouter(signal_width=10.0, ground_width=20.0, gap=5.0)
    z0 = router.compute_impedance()
    # CPW 阻抗应在合理范围（10-200 Ω）
    assert 10.0 < z0 < 200.0, f"阻抗 {z0} 超出合理范围"


def test_rf_gsg_router_invalid_params_raise():
    """RFGSGRouter 非正参数必须 raise。"""
    with pytest.raises(ValueError, match="signal_width"):
        RFGSGRouter(signal_width=0.0)
    with pytest.raises(ValueError, match="gap"):
        RFGSGRouter(gap=-1.0)


def test_rf_gsg_router_coincident_endpoints_raise():
    """RFGSGRouter 起终点重合必须 raise。"""
    router = RFGSGRouter()
    with pytest.raises(ValueError, match="重合"):
        router.route_gsg((5.0, 5.0), (5.0, 5.0))


def test_bus_router_serial_and_parallel():
    """BusRouter 串联和并联总线。"""
    router = BusRouter()
    devices = [
        {"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)},
        {"in_port": (10.0, 0.0), "out_port": (20.0, 0.0)},
    ]
    serial = router.route_bus(devices, bus_type="serial")
    assert len(serial) == 1, f"串联应 1 条路径，实际 {len(serial)}"
    assert len(serial[0]) == 4, "串联路径应 4 点（2 器件 × 2 端口）"

    parallel = router.route_bus(devices, bus_type="parallel")
    assert len(parallel) == 2, f"并联应 2 条路径，实际 {len(parallel)}"


def test_bus_router_empty_devices_raises():
    """BusRouter 空 devices 必须 raise。"""
    router = BusRouter()
    with pytest.raises(ValueError, match="devices"):
        router.route_bus([])


def test_bus_router_invalid_type_raises():
    """BusRouter 非法 bus_type 必须 raise。"""
    router = BusRouter()
    with pytest.raises(ValueError, match="bus_type"):
        router.route_bus(
            [{"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)}],
            bus_type="invalid",
        )


def test_high_order_bezier_connector_basic():
    """HighOrderBezierConnector 高阶贝塞尔曲线。"""
    conn = HighOrderBezierConnector(order=5)
    path = conn.compute_path(
        (0.0, 0.0), (50.0, 0.0), start_angle=0.0, end_angle=0.0
    )
    assert len(path) == 100, f"应 100 采样点，实际 {len(path)}"
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (50.0, 0.0)


def test_high_order_bezier_connector_invalid_order_raises():
    """HighOrderBezierConnector order < 2 必须 raise。"""
    with pytest.raises(ValueError, match="order"):
        HighOrderBezierConnector(order=1)


# ---------------------------------------------------------------------------
# 10. CurvyA* 深度测试
# ---------------------------------------------------------------------------


def test_curvy_astar_config_invalid_params_raise():
    """CurvyAStarConfig 非法参数必须 raise。"""
    with pytest.raises(ValueError, match="grid_size"):
        CurvyAStarConfig(grid_size=0.0)
    with pytest.raises(ValueError, match="bend_radius"):
        CurvyAStarConfig(bend_radius=-1.0)
    with pytest.raises(ValueError, match="n_directions"):
        CurvyAStarConfig(n_directions=7)


def test_curvy_astar_router_start_eq_end_raises():
    """CurvyAStarRouter 起终点重合必须 raise。"""
    router = CurvyAStarRouter(CurvyAStarConfig())
    with pytest.raises(ValueError, match="重合"):
        router.route((10.0, 10.0), (10.0, 10.0))


def test_curvy_astar_router_with_obstacles():
    """CurvyAStarRouter 带障碍物布线。"""
    router = CurvyAStarRouter(CurvyAStarConfig(n_directions=8))
    obstacles = [(20.0, 0.0, 5.0, 30.0)]  # 中间障碍墙
    path = router.route((0.0, 10.0), (50.0, 10.0), obstacles=obstacles)
    assert len(path) >= 2
    assert path[0] == (0.0, 10.0)
    assert path[-1] == (50.0, 10.0)


def test_curve_type_enum_values():
    """CurveType 枚举值验证。"""
    assert CurveType.EULER.value == "euler"
    assert CurveType.ARC.value == "arc"
    assert CurveType.BEZIER.value == "bezier"


# ---------------------------------------------------------------------------
# 11. OptoDesigner 组件深度测试
# ---------------------------------------------------------------------------


def test_adaptive_crossing_inserter_find_intersections():
    """AdaptiveCrossingInserter 查找交叉点。"""
    inserter = AdaptiveCrossingInserter()
    # 两条相交路径
    paths = [
        [(0.0, 0.0), (10.0, 10.0)],
        [(0.0, 10.0), (10.0, 0.0)],
    ]
    intersections = inserter.find_intersections(paths)
    assert len(intersections) == 1, f"应 1 个交叉，实际 {len(intersections)}"
    pi, pj, pt = intersections[0]
    assert pi == 0 and pj == 1
    assert abs(pt[0] - 5.0) < 1.0 and abs(pt[1] - 5.0) < 1.0


def test_adaptive_crossing_inserter_invalid_loss_raises():
    """AdaptiveCrossingInserter crossing_loss <= 0 必须 raise。"""
    with pytest.raises(ValueError, match="crossing_loss"):
        AdaptiveCrossingInserter(crossing_loss=0.0)


def test_congestion_aware_net_ordering_compute_rudy():
    """CongestionAwareNetOrdering.compute_rudy RUDY 拥塞图。"""
    ordering = CongestionAwareNetOrdering(grid_size=1.0)
    nets = [
        {"pins": [(0.0, 0.0), (10.0, 10.0)]},
    ]
    rudy = ordering.compute_rudy(nets)
    # bbox = [0,10]×[0,10] = 11×11 = 121 cells，density = 1/121
    assert rudy[(0, 0)] == pytest.approx(1.0 / 121, abs=1e-6)
    assert rudy[(10, 10)] == pytest.approx(1.0 / 121, abs=1e-6)


def test_congestion_aware_net_ordering_invalid_grid_size_raises():
    """CongestionAwareNetOrdering 非正 grid_size 必须 raise。"""
    with pytest.raises(ValueError, match="grid_size"):
        CongestionAwareNetOrdering(grid_size=0.0)


def test_optodesigner_manhattan_route():
    """OptoDesignerAutorouter.manhattan_route L 形布线。"""
    ar = OptoDesignerAutorouter()
    path = ar.manhattan_route((0.0, 0.0), (50.0, 30.0))
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (50.0, 30.0)


def test_optodesigner_length_defined_route():
    """OptoDesignerAutorouter.length_defined_route S 弯延长。

    S 弯采用 amp=excess/4 近似（Synopsys OptoDesigner Length-Defined Connector），
    实际路径长度大于直线距离、小于目标长度（几何近似特性，非精确等于 target）。
    """
    ar = OptoDesignerAutorouter()
    path = ar.length_defined_route((0.0, 0.0), (30.0, 0.0), target_length=40.0)
    assert len(path) == 4, f"S 弯应 4 点，实际 {len(path)}"
    actual = path_length(path)
    direct = 30.0
    assert actual > direct, f"S 弯延长后长度 {actual} 应 > 直线距离 {direct}"
    assert actual < 40.0, f"S 弯近似长度 {actual} 应 < 目标 40.0"


def test_optodesigner_length_defined_route_target_too_small_raises():
    """OptoDesignerAutorouter 目标长度 < 直线距离必须 raise。"""
    ar = OptoDesignerAutorouter()
    with pytest.raises(ValueError, match="target_length"):
        ar.length_defined_route((0.0, 0.0), (30.0, 0.0), target_length=20.0)


# ---------------------------------------------------------------------------
# 12. DRVFreeValidator 深度测试
# ---------------------------------------------------------------------------


def test_drv_free_validator_straight_path_no_violation():
    """DRVFreeValidator 直线路径无弯曲违规。"""
    validator = DRVFreeValidator(min_bend_radius=5.0, min_spacing=1.0)
    paths = [[(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]]
    result = validator.validate(paths)
    assert result["bend_violations"] == 0, "直线路径无弯曲违规"


def test_drv_free_validator_sharp_bend_detected():
    """DRVFreeValidator 急转弯（半径 < 5μm）应检测到违规。"""
    validator = DRVFreeValidator(min_bend_radius=5.0, min_spacing=1.0)
    # 直角弯: (0,0)→(1,0)→(1,1)，半径 ≈ 0.707μm < 5μm
    paths = [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]]
    result = validator.validate(paths)
    assert result["bend_violations"] >= 1, "急转弯应检测到弯曲违规"


def test_drv_free_validator_invalid_params_raise():
    """DRVFreeValidator 非正参数必须 raise。"""
    with pytest.raises(ValueError, match="min_bend_radius"):
        DRVFreeValidator(min_bend_radius=0.0, min_spacing=1.0)
    with pytest.raises(ValueError, match="min_spacing"):
        DRVFreeValidator(min_bend_radius=5.0, min_spacing=-1.0)


# ---------------------------------------------------------------------------
# 13. CommercialRouter 深度测试
# ---------------------------------------------------------------------------


def test_commercial_router_config_invalid_params_raise():
    """CommercialRouterConfig 非法参数必须 raise。"""
    with pytest.raises(ValueError, match="discretization_resolution"):
        CommercialRouterConfig(discretization_resolution=0.0)
    with pytest.raises(ValueError, match="n_directions"):
        CommercialRouterConfig(n_directions=7)
    with pytest.raises(ValueError, match="min_success_rate"):
        CommercialRouterConfig(min_success_rate=0.0)


def test_commercial_router_flex_connector():
    """CommercialRouter.flex_connector 弹性避障布线。"""
    cr = CommercialRouter()
    path = cr.flex_connector({"x": 0.0, "y": 0.0}, {"x": 50.0, "y": 30.0})
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (50.0, 30.0)


def test_commercial_router_sbend_connector():
    """CommercialRouter.sbend_connector S 弯贝塞尔连接器。"""
    cr = CommercialRouter()
    path = cr.sbend_connector({"x": 0.0, "y": 0.0}, {"x": 30.0, "y": 10.0})
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (30.0, 10.0)


def test_commercial_router_manhattan_connector():
    """CommercialRouter.manhattan_connector 曼哈顿 L 形布线。"""
    cr = CommercialRouter()
    path = cr.manhattan_connector({"x": 0.0, "y": 0.0}, {"x": 50.0, "y": 30.0})
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (50.0, 30.0)


def test_commercial_router_bundle_connector_mismatch_raises():
    """CommercialRouter.bundle_connector 端口数不匹配必须 raise。"""
    cr = CommercialRouter()
    with pytest.raises(ValueError, match="端口数不匹配"):
        cr.bundle_connector(
            [{"x": 0.0, "y": 0.0}],
            [{"x": 10.0, "y": 0.0}, {"x": 10.0, "y": 5.0}],
        )


def test_commercial_router_curvy_connector_invalid_type_raises():
    """CommercialRouter.curvy_connector 非法 curve_type 必须 raise。"""
    cr = CommercialRouter()
    with pytest.raises(ValueError, match="curve_type"):
        cr.curvy_connector(
            {"x": 0.0, "y": 0.0}, {"x": 20.0, "y": 10.0}, curve_type="invalid"
        )


def test_commercial_router_discretize_path():
    """CommercialRouter.discretize_path 折线重采样。"""
    cr = CommercialRouter(CommercialRouterConfig(discretization_resolution=1.0))
    path = [(0.0, 0.0), (10.0, 0.0)]
    result = cr.discretize_path(path)
    assert len(result) > 2, f"重采样后应 > 2 点，实际 {len(result)}"
    assert result[0] == (0.0, 0.0)
    assert result[-1] == (10.0, 0.0)


# ---------------------------------------------------------------------------
# 14. GdsfactoryStyleRouter 深度测试
# ---------------------------------------------------------------------------


def test_gf_router_route_sbend():
    """GdsfactoryStyleRouter.route_sbend S 弯布线。"""
    router = GdsfactoryStyleRouter()
    path = router.route_sbend(GfPort(0.0, 0.0), GfPort(30.0, 10.0))
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (30.0, 10.0)


def test_gf_router_route_manhattan():
    """GdsfactoryStyleRouter.route_manhattan Z 弯曼哈顿布线。"""
    router = GdsfactoryStyleRouter()
    # 水平相向端口
    path = router.route_manhattan(
        GfPort(0.0, 0.0, orientation=0.0),
        GfPort(50.0, 10.0, orientation=180.0),
    )
    assert len(path) >= 2
    assert path[0] == (0.0, 0.0)
    assert path[-1] == (50.0, 10.0)


def test_gf_router_route_bundle_mismatch_raises():
    """GdsfactoryStyleRouter.route_bundle 端口数不匹配必须 raise。"""
    router = GdsfactoryStyleRouter()
    with pytest.raises(ValueError, match="端口数不匹配"):
        router.route_bundle(
            [GfPort(0.0, 0.0)],
            [GfPort(50.0, 0.0), GfPort(50.0, 5.0)],
        )


def test_gf_router_route_fiber_array():
    """GdsfactoryStyleRouter.route_fiber_array 光纤阵列布线。"""
    router = GdsfactoryStyleRouter()
    pins = [GfPort(0.0, 0.0), GfPort(0.0, 5.0)]
    pouts = [GfPort(50.0, 0.0), GfPort(50.0, 5.0)]
    paths = router.route_fiber_array(pins, pouts)
    assert len(paths) == 2


def test_gf_router_route_cpw():
    """GdsfactoryStyleRouter.route_cpw 共面波导 GSG 布线。"""
    router = GdsfactoryStyleRouter()
    pins = [GfPort(0.0, 0.0, orientation=0.0)]
    pouts = [GfPort(50.0, 0.0, orientation=180.0)]
    paths = router.route_cpw(pins, pouts)
    # CPW: 每对端口生成 3 条路径（G-S-G）
    assert len(paths) == 3, f"CPW 应 3 条路径（GSG），实际 {len(paths)}"


def test_gf_router_compare_with_astar():
    """GdsfactoryStyleRouter.compare_with_astar 线长对比验证。"""
    router = GdsfactoryStyleRouter()
    gf_route = [(0.0, 0.0), (50.0, 0.0)]
    astar_route = [(0.0, 0.0), (50.0, 0.0)]
    result = router.compare_with_astar(gf_route, astar_route)
    assert "length_gdsfactory" in result
    assert "length_astar" in result
    assert "diff_ratio" in result
    assert "within_10_percent" in result
    assert result["diff_ratio"] == pytest.approx(0.0, abs=1e-9)


def test_gf_router_compare_with_astar_zero_length_raises():
    """GdsfactoryStyleRouter.compare_with_astar 零长 A* 路径必须 raise。"""
    router = GdsfactoryStyleRouter()
    with pytest.raises(ValueError, match="A\\*.*长度为 0"):
        router.compare_with_astar(
            [(0.0, 0.0), (10.0, 0.0)],
            [(5.0, 5.0)],  # 单点，长度 = 0
        )


def test_gf_route_config_invalid_raises():
    """GfRouteConfig.validate() 非法参数必须 raise（校验在 validate 方法，非 __post_init__）。"""
    config = GfRouteConfig(bend_radius=0.0)
    with pytest.raises(ValueError, match="bend_radius"):
        config.validate()
    config2 = GfRouteConfig(separation=-1.0)
    with pytest.raises(ValueError, match="separation"):
        config2.validate()


def test_gf_router_validate_bend_radius():
    """GdsfactoryStyleRouter.validate_bend_radius 弯曲半径合规校验。"""
    router = GdsfactoryStyleRouter(GfRouteConfig(bend_radius=5.0))
    # 直线路径无转弯，合规
    assert router.validate_bend_radius([(0.0, 0.0), (10.0, 0.0)]) is True


# ---------------------------------------------------------------------------
# 15. Global Router 深度测试
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
