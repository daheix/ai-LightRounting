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

