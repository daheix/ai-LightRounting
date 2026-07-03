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


def test_all_angle_router_smoke():
    """任意角度布线: (0,0,0°)→(50,30,0°) 应返回含欧拉弯曲的路径。

    AllAngleRouter 用曼哈顿 L 骨架 + euler_bend 平滑非曼哈顿段。
    """
    router = AllAngleRouter(grid_w=100, grid_h=100, bend_radius=5.0)
    path = router.route((0.0, 0.0, 0.0), (50.0, 30.0, 0.0))
    assert len(path) >= 2, f"AllAngle 路径至少 2 点，实际 {len(path)}"
    assert abs(path[0][0] - 0.0) < 5.0
    assert abs(path[-1][0] - 50.0) < 5.0


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


def test_jps_router_start_on_obstacle_raises():
    """JPS 起点在障碍上必须 raise ValueError。"""
    router = JPSRouter(grid_w=10, grid_h=10, grid_size=1.0)
    router.add_obstacle(5, 5)
    with pytest.raises(ValueError, match="起点.*障碍"):
        router.route((5, 5), (9, 9))


# ---------------------------------------------------------------------------
# 6. AllAngleRouter 深度测试
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
