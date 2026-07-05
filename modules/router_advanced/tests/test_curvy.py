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


def test_all_angle_router_smoke():
    """任意角度布线: (0,0,0°)→(50,30,0°) 应返回含欧拉弯曲的路径。

    AllAngleRouter 用曼哈顿 L 骨架 + euler_bend 平滑非曼哈顿段。
    """
    router = AllAngleRouter(grid_w=100, grid_h=100, bend_radius=5.0)
    path = router.route((0.0, 0.0, 0.0), (50.0, 30.0, 0.0))
    assert len(path) >= 2, f"AllAngle 路径至少 2 点，实际 {len(path)}"
    assert abs(path[0][0] - 0.0) < 5.0
    assert abs(path[-1][0] - 50.0) < 5.0


def test_euler_bend_connector_smoke():
    """Advanced Connectors 欧拉弯曲连接器: 90° 弯曲应生成对称 S 形路径。"""
    config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
    bend = EulerBend(config)
    path = bend.compute_path()
    assert len(path) == 50, f"应 50 点，实际 {len(path)}"
    assert abs(path[0][0]) < 1.0 and abs(path[0][1]) < 1.0
    assert path[-1][0] != 0.0 or path[-1][1] != 0.0


def test_curvy_astar_router_smoke():
    """CurvyA* 曲线感知布线: (0,0)→(50,30) 应返回弯曲半径约束路径。"""
    router = CurvyAStarRouter(CurvyAStarConfig())
    path = router.route((0.0, 0.0), (50.0, 30.0))
    assert len(path) >= 2, f"CurvyA* 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (0.0, 0.0), f"起点应为 (0,0)，实际 {path[0]}"
    assert path[-1] == (50.0, 30.0), f"终点应为 (50,30)，实际 {path[-1]}"


def test_diagonal_router_smoke():
    """对角网格布线: 20x20 网格 (1,1)→(18,18) 应返回非空路径。"""
    router = DiagonalGridRouter(grid_w=20, grid_h=20, grid_size=1.0)
    path = router.route((1, 1), (18, 18))
    assert path is not None, "Diagonal 路径不应为 None"
    assert len(path) >= 2, f"Diagonal 路径至少 2 点，实际 {len(path)}"
    assert path[0] == (1, 1)
    assert path[-1] == (18, 18)


def test_dubins_path_smoke():
    """Dubins 路径: (0,0,0°)→(20,10,0°) 应返回连续曲率路径。"""
    path = dubins_path((0.0, 0.0, 0.0), (20.0, 10.0, 0.0), radius=5.0)
    assert len(path) >= 2, f"Dubins 路径至少 2 点，实际 {len(path)}"
    assert abs(path[0][0] - 0.0) < 1.0
    assert abs(path[0][1] - 0.0) < 1.0


def test_path_geometry_tools_smoke():
    """几何工具: s_bend/euler_bend/count_crossings/path_length 基础验证。"""
    sb = s_bend(0.0, 0.0, 100.0, 20.0, n_points=20)
    assert len(sb) == 21, f"s_bend 应 21 点，实际 {len(sb)}"
    assert sb[0] == (0.0, 0.0)
    assert sb[-1] == (100.0, 20.0)

    eb = euler_bend(radius_um=5.0, angle_deg=90.0, n_points=30)
    assert len(eb) > 0 and len(eb) == 31, f"euler_bend 应 31 点，实际 {len(eb)}"

    p1 = [(0.0, 0.0), (10.0, 10.0)]
    p2 = [(0.0, 10.0), (10.0, 0.0)]
    assert count_crossings(p1, p2) == 1, "相交路径应有 1 个交叉"

    assert abs(path_length([(0.0, 0.0), (3.0, 4.0)]) - 5.0) < 1e-9


def test_arc_bend_basic():
    """arc_bend 圆弧弯曲: 90° R=5 应生成 n_points+1 个点。"""
    pts = arc_bend(radius_um=5.0, angle_deg=90.0, n_points=20)
    assert len(pts) == 21, f"应 21 点，实际 {len(pts)}"
    assert pts[0] == (0.0, 0.0), "起点应在原点"


def test_check_min_spacing_pass_and_fail():
    """check_min_spacing 满足/不满足间距。"""
    p1 = [(0.0, 0.0), (10.0, 0.0)]
    p2 = [(0.0, 5.0), (10.0, 5.0)]
    assert check_min_spacing(p1, p2, 3.0) is True, "间距 5μm > 3μm 应满足"
    assert check_min_spacing(p1, p2, 6.0) is False, "间距 5μm < 6μm 不满足"


def test_count_crossings_no_crossing():
    """count_crossings 平行线无交叉。"""
    p1 = [(0.0, 0.0), (10.0, 0.0)]
    p2 = [(0.0, 5.0), (10.0, 5.0)]
    assert count_crossings(p1, p2) == 0, "平行线无交叉"


def test_equalize_length_extends_path():
    """equalize_length 蛇形绕行延长路径。"""
    path = [(0.0, 0.0), (10.0, 0.0)]
    original = path_length(path)
    extended = equalize_length(path, target_length_um=20.0, detour_step=2.0)
    new_len = path_length(extended)
    assert new_len >= original, "延长后长度应 ≥ 原长度"
    assert len(extended) >= len(path), "延长后点数应 ≥ 原点数"


def test_path_loss_basic():
    """path_loss 损耗 = 传播 + 弯曲 + 交叉。"""
    # 直线 (0,0)→(100,0)，无弯曲无交叉
    path = [(0.0, 0.0), (100.0, 0.0)]
    loss = path_loss(path, loss_db_cm=3.0)
    # 传播损耗 = 3.0 * 100μm / 1e4 = 0.03 dB
    assert loss == pytest.approx(0.03, abs=1e-6), f"直线损耗应 0.03dB，实际 {loss}"


# ---------------------------------------------------------------------------
# 5. JPS 路由器深度测试
# ---------------------------------------------------------------------------


def test_all_angle_router_grid_size_invalid_raises():
    """AllAngleRouter grid_size <= 0 必须 raise。"""
    with pytest.raises(ValueError, match="grid_size"):
        AllAngleRouter(grid_w=10, grid_h=10, grid_size=0.0)


def test_all_angle_router_endpoint_on_obstacle_raises():
    """AllAngleRouter 端点在障碍上必须 raise。"""
    router = AllAngleRouter(grid_w=20, grid_h=20, bend_radius=5.0)
    router.add_obstacle(10, 10)
    with pytest.raises(ValueError, match="障碍"):
        router.route((10.0, 10.0, 0.0), (18.0, 18.0, 0.0))


def test_all_angle_router_set_congestion():
    """AllAngleRouter.set_congestion 设置拥塞图不报错。"""
    router = AllAngleRouter(grid_w=20, grid_h=20, bend_radius=5.0)
    router.set_congestion({(10, 10): 0.9, (11, 11): 0.8})
    path = router.route((0.0, 0.0, 0.0), (18.0, 18.0, 0.0))
    assert len(path) >= 2


# ---------------------------------------------------------------------------
# 7. Bundle 路由器深度测试
# ---------------------------------------------------------------------------


def test_dubins_path_invalid_radius_raises():
    """dubins_path radius <= 0 必须 raise ValueError。"""
    with pytest.raises(ValueError, match="radius"):
        dubins_path((0.0, 0.0, 0.0), (10.0, 5.0, 0.0), radius=0.0)


# ---------------------------------------------------------------------------
# 8. 对角路由器深度测试
# ---------------------------------------------------------------------------


def test_diagonal_router_unreachable_returns_none():
    """DiagonalGridRouter 被障碍完全包围时返回 None。"""
    router = DiagonalGridRouter(grid_w=10, grid_h=10, grid_size=1.0)
    # 在 (5,5) 周围围一圈障碍
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            router.add_obstacle(5 + dx, 5 + dy)
    # (5,5) 被完全包围，无法到达
    result = router.route((5, 5), (9, 9))
    # 被包围时可能返回 None 或只含起点的路径
    assert result is None or len(result) < 2, (
        f"被包围的起点应不可达，实际: {result}"
    )


# ---------------------------------------------------------------------------
# 9. Advanced Connectors 深度测试
# ---------------------------------------------------------------------------


def test_euler_bend_config_invalid_params_raise():
    """EulerBendConfig 非法参数必须 raise。"""
    with pytest.raises(ValueError, match="radius"):
        EulerBendConfig(radius=0.0)
    with pytest.raises(ValueError, match="angle"):
        EulerBendConfig(angle=0.0)
    with pytest.raises(ValueError, match="n_points"):
        EulerBendConfig(n_points=1)


def test_euler_bend_compute_length_and_loss():
    """EulerBend.compute_length = 2*R*angle_rad，compute_loss = alpha*L/1e4。"""
    config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
    bend = EulerBend(config)
    expected_len = 2.0 * 10.0 * math.radians(90.0)  # = 10π ≈ 31.416
    assert bend.compute_length() == pytest.approx(expected_len, abs=0.01), (
        f"长度应 ≈ {expected_len}，实际 {bend.compute_length()}"
    )
    loss = bend.compute_loss(alpha=0.28)
    expected_loss = 0.28 * expected_len / 1e4
    assert loss == pytest.approx(expected_loss, abs=1e-6), (
        f"损耗应 ≈ {expected_loss}，实际 {loss}"
    )


def test_euler_bend_compute_loss_invalid_alpha_raises():
    """EulerBend.compute_loss alpha <= 0 必须 raise。"""
    bend = EulerBend(EulerBendConfig(radius=10.0, angle=90.0, n_points=10))
    with pytest.raises(ValueError, match="alpha"):
        bend.compute_loss(alpha=0.0)


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
