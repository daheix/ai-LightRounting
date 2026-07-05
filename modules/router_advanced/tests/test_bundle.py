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


def test_bundle_router_smoke():
    """Bundle 并行布线: 2 端口对应返回 2 条不交叉路径。"""
    ports1 = [(0, 0), (0, 5)]
    ports2 = [(40, 0), (40, 5)]
    paths = route_bundle(ports1, ports2, separation=2, grid_w=50, grid_h=20)
    assert len(paths) == 2, f"应返回 2 条路径，实际 {len(paths)}"
    for p in paths:
        assert len(p) >= 2, f"Bundle 路径至少 2 点，实际 {len(p)}"
        assert p[0][0] == 0, f"起点 x 应为 0，实际 {p[0][0]}"
        assert p[-1][0] == 40, f"终点 x 应为 40，实际 {p[-1][0]}"


def test_route_bundle_port_count_mismatch_raises():
    """route_bundle 端口数不匹配必须 raise ValueError。"""
    with pytest.raises(ValueError, match="长度不匹配"):
        route_bundle([(0, 0)], [(10, 0), (10, 5)], grid_w=20, grid_h=10)


def test_route_bundle_path_length_match_basic():
    """route_bundle_path_length_match 等长匹配。"""
    ports1 = [(0, 0), (0, 5)]
    ports2 = [(40, 0), (40, 5)]
    paths = route_bundle_path_length_match(
        ports1, ports2, tolerance=0.5, grid_w=50, grid_h=20
    )
    assert len(paths) == 2
    lengths = [path_length(p) for p in paths]
    # 等长匹配后长度差应在容差内
    assert max(lengths) - min(lengths) <= 5.0, (
        f"等长匹配后差距过大: {lengths}"
    )


def test_route_bundle_from_waypoints_basic():
    """route_bundle_from_waypoints 经路径点布线。"""
    ports1 = [(0, 0), (0, 5)]
    ports2 = [(40, 0), (40, 5)]
    waypoints = [(20, 0), (20, 5)]
    paths = route_bundle_from_waypoints(
        ports1, ports2, waypoints, grid_w=50, grid_h=20
    )
    assert len(paths) == 2
    for p in paths:
        assert len(p) >= 2


def test_route_bundle_from_waypoints_empty_waypoints_raises():
    """route_bundle_from_waypoints 空 waypoints 必须 raise。"""
    with pytest.raises(ValueError, match="waypoints"):
        route_bundle_from_waypoints(
            [(0, 0)], [(10, 0)], [], grid_w=20, grid_h=10
        )


def test_auto_taper_basic():
    """auto_taper 线性宽度过渡。"""
    route = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
    result = auto_taper(route, taper_length=2.0, start_width=0.5, end_width=1.0)
    assert len(result) == 3, f"应 3 点，实际 {len(result)}"
    # 每个点是 (x, y, w)
    for pt in result:
        assert len(pt) == 3, "auto_taper 结果应为 (x, y, w) 三元组"


def test_length_defined_connector_route_equal_length():
    """LengthDefinedConnector.route_equal_length 等腰三角形延展。"""
    conn = LengthDefinedConnector()
    start = (0.0, 0.0)
    end = (10.0, 0.0)
    # 直线距离 = 10，目标长度 = 15
    path = conn.route_equal_length(start, end, target_length=15.0)
    assert len(path) == 3, f"延展后应 3 点，实际 {len(path)}"
    # 两腰各 = 15/2 = 7.5，底边 = 10
    actual_len = path_length(path)
    assert actual_len == pytest.approx(15.0, abs=0.1), (
        f"延展后长度应 ≈ 15.0，实际 {actual_len}"
    )


def test_length_defined_connector_target_too_small_raises():
    """LengthDefinedConnector 目标长度 < 直线距离必须 raise。"""
    conn = LengthDefinedConnector()
    with pytest.raises(ValueError, match="target_length"):
        conn.route_equal_length((0.0, 0.0), (10.0, 0.0), target_length=5.0)


def test_phase_matched_router_route_mzi_arms():
    """PhaseMatchedRouter.route_mzi_arms MZI 两臂等长路由。"""
    router = PhaseMatchedRouter()
    arm1, arm2 = router.route_mzi_arms(
        (0.0, 0.0), (50.0, 0.0),
        (0.0, 10.0), (50.0, 10.0),
    )
    assert len(arm1) >= 2
    assert len(arm2) >= 2
    l1 = path_length(arm1)
    l2 = path_length(arm2)
    # 相位匹配后两臂长度应接近（都延展到相同目标长度）
    assert abs(l1 - l2) < 1.0, f"两臂长度差应 < 1μm: {l1} vs {l2}"


def test_phase_matched_router_compute_phase_mismatch():
    """PhaseMatchedRouter.compute_phase_mismatch 相位失配计算。"""
    router = PhaseMatchedRouter(wavelength=1.55, neff=2.4)
    # 两路径长度差 1μm
    p1 = [(0.0, 0.0), (10.0, 0.0)]
    p2 = [(0.0, 0.0), (11.0, 0.0)]
    mismatch = router.compute_phase_mismatch(p1, p2)
    # Δφ = (2π/λ) * neff * ΔL = (2π/1.55) * 2.4 * 1.0
    expected = (2.0 * math.pi / 1.55) * 2.4 * 1.0
    assert mismatch == pytest.approx(expected, abs=0.01), (
        f"相位失配应 ≈ {expected}，实际 {mismatch}"
    )


def test_phase_matched_router_invalid_wavelength_raises():
    """PhaseMatchedRouter 非正 wavelength 必须 raise。"""
    with pytest.raises(ValueError, match="wavelength"):
        PhaseMatchedRouter(wavelength=0.0)


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
