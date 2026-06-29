"""波导约束布线器测试（Task 11 + C3 稀疏网格 + 动态 grid_size）。"""

from __future__ import annotations

import pytest

from polaris.router.obstacle_grid import ObstacleGrid, auto_grid_size
from polaris.router.waveguide_router import (
    GridRouter,
    RouteConnectionConfig,
    RouterConstraints,
    WaveguidePath,
    arc_bend,
    check_min_spacing,
    count_crossings,
    equalize_length,
    euler_bend,
    get_platform_constraints,
    path_length,
    path_loss,
    route_connection,
    route_curvy_connection,
    s_bend,
)


def test_grid_router_basic_path():
    router = GridRouter(
        50,
        50,
        grid_size=1.0,
        constraints=RouterConstraints(min_bend_radius_um=5.0),
    )
    path = router.route((0, 0), (40, 40))
    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (40, 40)


def test_grid_router_obstacle_avoidance():
    router = GridRouter(
        50,
        50,
        grid_size=1.0,
        constraints=RouterConstraints(min_bend_radius_um=5.0),
    )
    router.add_obstacle(20, 20, 5, 5)
    path = router.route((0, 0), (40, 40))
    assert path is not None
    # 路径不应穿过障碍区
    for x, y in path:
        assert not (20 <= x < 25 and 20 <= y < 25)


def test_grid_router_unreachable_returns_none():
    router = GridRouter(10, 10, grid_size=1.0)
    # 用障碍完全围堵终点
    for x in range(10):
        router.add_obstacle(x, 5, 1, 1)
    path = router.route((0, 0), (5, 8))
    assert path is None


def test_s_bend_endpoints():
    pts = s_bend(0, 0, 10, 5, n_points=20)
    assert pts[0] == (0, 0)
    assert pts[-1] == (10, 5)
    assert len(pts) == 21


def test_euler_bend_points():
    pts = euler_bend(5.0, 90.0, n_points=30)
    assert len(pts) == 31
    assert pts[0] == (0, 0)


def test_euler_bend_90deg_turn_angle_regression():
    """回归测试：90° Euler 弯曲必须实际转过 90°（弧长 ≈ π*R）。

    历史 Bug: 旧公式 L = R*sqrt(angle) 对 90° 弯曲只转 35.9°（数学错误）。
    正确公式（clothoid 定义）: k(s)=s/(R*L), θ=L/(2R), 故 L=2*R*θ。
    对 90° (θ=π/2): L = π*R ≈ 3.14159*R。

    来源:
    - Flexcompute Tidy3D EulerWaveguideBend: clothoid 公式 RL=A², θ=L/(2R)
      https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html
    - R05 发现 Bug 必须修复并附回归测试
    """
    import math

    R = 5.0
    pts = euler_bend(R, 90.0, n_points=200)
    # 弧长 ≈ π*R
    arc = sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    expected_L = math.pi * R
    assert abs(arc - expected_L) / expected_L < 0.02, (
        f"90° Euler 弧长 {arc:.4f} 偏离 π*R={expected_L:.4f} 超过 2%"
    )
    # 终点切线方向应接近 90°
    dx = pts[-1][0] - pts[-2][0]
    dy = pts[-1][1] - pts[-2][1]
    final_angle = math.degrees(math.atan2(dy, dx))
    assert abs(final_angle - 90.0) < 3.0, (
        f"90° Euler 终点切线 {final_angle:.2f}° 偏离 90° 超过 3°"
    )


def test_arc_bend_endpoints():
    pts = arc_bend(5.0, 90.0, n_points=20)
    assert pts[0] == (0, 0)
    # 90度圆弧终点
    assert abs(pts[-1][0] - 5.0) < 0.1
    assert abs(pts[-1][1] - 5.0) < 0.1


def test_check_min_spacing_satisfied():
    p1 = [(0, 0), (10, 0)]
    p2 = [(0, 5), (10, 5)]
    assert check_min_spacing(p1, p2, min_spacing_um=2.0)


def test_check_min_spacing_violated():
    p1 = [(0, 0), (10, 0)]
    p2 = [(0, 0.5), (10, 0.5)]
    assert not check_min_spacing(p1, p2, min_spacing_um=2.0)


def test_count_crossings_none():
    p1 = [(0, 0), (10, 0)]
    p2 = [(0, 5), (10, 5)]
    assert count_crossings(p1, p2) == 0


def test_count_crossings_one():
    p1 = [(0, 0), (10, 10)]
    p2 = [(0, 10), (10, 0)]
    assert count_crossings(p1, p2) == 1


def test_equalize_length_increases():
    pts = [(0, 0), (10, 0), (20, 0)]
    original = path_length(pts)
    eq = equalize_length(pts, 50.0, detour_step=2.0)
    assert path_length(eq) >= 50.0
    assert path_length(eq) > original


def test_equalize_length_no_change_if_already_long():
    pts = [(0, 0), (100, 0)]
    eq = equalize_length(pts, 50.0, detour_step=2.0)
    assert eq == pts  # 已超过目标，不变


def test_path_length():
    pts = [(0, 0), (3, 0), (3, 4)]
    assert path_length(pts) == pytest.approx(7.0)


def test_path_loss():
    pts = [(0, 0), (100, 0)]  # 100μm = 0.01cm
    loss = path_loss(pts, loss_db_cm=2.0, bend_loss_db=0.0, crossing_loss_db=0.0)
    assert loss == pytest.approx(0.02)  # 2 dB/cm * 0.01cm


def test_get_platform_constraints():
    soi = get_platform_constraints("SOI")
    assert soi["min_bend_radius_um"] == 5.0
    sin = get_platform_constraints("SiN")
    # SiN: LIGENTEC AN800 SiN 平台弯曲半径 ≥100μm
    # 来源: waveguide_router.py PLATFORM_CONSTRAINTS 注释（文献溯源）
    assert sin["min_bend_radius_um"] == 100.0
    inp = get_platform_constraints("InP")
    # InP: InP 有源波导低折射率差平台弯曲半径 ≥250μm
    # 来源: Soares et al., Appl. Sci. 2019, https://doi.org/10.3390/app9081588
    assert inp["min_bend_radius_um"] == 250.0
    lnoi = get_platform_constraints("LNOI")
    # LNOI: HyperLight LNOI X-cut 产品规格保守值 80μm
    # 来源: https://www.hyperlightcorp.com/; doi:10.1038/s41377-024-01389-6
    assert lnoi["min_bend_radius_um"] == 80.0


def test_route_connection_basic():
    wp = route_connection(
        (0, 0),
        (100, 100),
        platform="SOI",
        grid_size=2.0,
        canvas_w=500,
        canvas_h=500,
    )
    assert isinstance(wp, WaveguidePath)
    assert wp.length_um > 0
    assert wp.loss_db >= 0
    assert len(wp.points) >= 2


def test_route_connection_with_obstacles():
    wp = route_connection(
        (0, 0),
        (100, 100),
        platform="SOI",
        grid_size=2.0,
        canvas_w=500,
        canvas_h=500,
        obstacles=[(40, 40, 60, 60)],
    )
    assert wp.length_um > 0


def test_route_connection_equal_length():
    wp = route_connection(
        (0, 0),
        (50, 0),
        platform="SOI",
        grid_size=2.0,
        canvas_w=500,
        canvas_h=500,
        target_length_um=200.0,
    )
    assert wp.length_um >= 200.0


# =============================================================================
# C3: 稀疏网格 + 动态 grid_size 测试
# =============================================================================


def test_auto_grid_size_small_canvas():
    """小画布应返回弯曲半径约束下的 grid_size。"""
    gs = auto_grid_size(canvas_w=500.0, canvas_h=500.0, platform="SOI")
    # SOI: w=0.5, R=5 → max(0.6, 2.5, 0.25) = 2.5
    assert gs == pytest.approx(2.5)


def test_auto_grid_size_large_canvas():
    """大画布应返回计算可扩展性约束下的 grid_size。"""
    gs = auto_grid_size(canvas_w=5000.0, canvas_h=5000.0, platform="SOI")
    # SOI: w=0.5, R=5 → max(0.6, 2.5, 2.5) = 2.5
    assert gs == pytest.approx(2.5)
    # 验证总单元数在合理范围（≤ 4M）
    total_cells = (5000 / gs) * (5000 / gs)
    assert total_cells <= 4_000_000


def test_auto_grid_size_sin_platform():
    """SiN 平台弯曲半径更大，grid_size 应更大。"""
    gs = auto_grid_size(canvas_w=5000.0, canvas_h=5000.0, platform="SiN")
    # SiN: w=1.0, R=100（LIGENTEC AN800 SiN 平台，文献溯源）→ max(1.2, 50.0, 5.0) = 50.0
    assert gs == pytest.approx(50.0)


def test_auto_grid_size_invalid_canvas():
    """非正画布尺寸应抛出 ValueError。"""
    with pytest.raises(ValueError):
        auto_grid_size(canvas_w=0, canvas_h=100)
    with pytest.raises(ValueError):
        auto_grid_size(canvas_w=100, canvas_h=-1)


def test_obstacle_grid_dense_mode():
    """小栅格应使用稠密存储。"""
    grid = ObstacleGrid(100, 100)
    assert grid.is_dense is True
    assert grid.shape == (100, 100)
    assert grid.total_cells == 10_000
    # 初始无障碍
    assert grid.is_blocked(50, 50) is False
    assert grid.get(50, 50) == 0


def test_obstacle_grid_sparse_mode():
    """大栅格应自动切换到稀疏存储。"""
    # 3000×3000 = 9M 单元 > 4M 阈值
    grid = ObstacleGrid(3000, 3000)
    assert grid.is_dense is False
    assert grid.shape == (3000, 3000)
    assert grid.total_cells == 9_000_000
    # 初始无障碍
    assert grid.is_blocked(100, 100) is False
    # 标记障碍
    grid.set(100, 100, 1)
    assert grid.is_blocked(100, 100) is True
    assert grid.get(100, 100) == 1
    # 清除障碍
    grid.set(100, 100, 0)
    assert grid.is_blocked(100, 100) is False


def test_obstacle_grid_mark_region_dense():
    """稠密模式标记矩形区域。"""
    grid = ObstacleGrid(50, 50)
    grid.mark_region(10, 10, 20, 20)
    for x in range(10, 20):
        for y in range(10, 20):
            assert grid.is_blocked(x, y) is True
    # 区域外无障碍
    assert grid.is_blocked(5, 5) is False
    assert grid.is_blocked(25, 25) is False


def test_obstacle_grid_mark_region_sparse():
    """稀疏模式标记矩形区域。"""
    grid = ObstacleGrid(3000, 3000)
    grid.mark_region(100, 100, 110, 110)
    for x in range(100, 110):
        for y in range(100, 110):
            assert grid.is_blocked(x, y) is True
    assert grid.is_blocked(50, 50) is False


def test_obstacle_grid_mark_region_clamped():
    """标记区域超出边界应被钳位。"""
    grid = ObstacleGrid(20, 20)
    # 超出右下边界
    grid.mark_region(15, 15, 30, 30)
    for x in range(15, 20):
        for y in range(15, 20):
            assert grid.is_blocked(x, y) is True
    # 不应影响负坐标（已钳位到 0）
    assert grid.is_blocked(0, 0) is False


def test_obstacle_grid_memory_estimate():
    """内存估算应返回合理值。"""
    dense = ObstacleGrid(100, 100)
    dense.mark_region(0, 0, 10, 10)
    # 稠密：100×100×4 = 40000 字节
    assert dense.memory_estimate_bytes() == 40_000

    sparse = ObstacleGrid(3000, 3000)
    sparse.mark_region(0, 0, 10, 10)
    # 稀疏：100 个障碍 × 72 字节 = 7200 字节
    assert sparse.memory_estimate_bytes() == 7200


def test_grid_router_with_sparse_obstacle():
    """GridRouter 在大栅格下应自动使用稀疏存储并正确路由。"""
    # 3000×3000 = 9M 单元 → 稀疏模式
    router = GridRouter(
        3000,
        3000,
        grid_size=1.0,
        constraints=RouterConstraints(min_bend_radius_um=5.0),
    )
    assert router.obstacle.is_dense is False
    # 添加障碍
    router.add_obstacle(1500, 1500, 100, 100)
    # 路由应绕过障碍
    path = router.route((100, 100), (2900, 2900))
    assert path is not None
    assert path[0] == (100, 100)
    assert path[-1] == (2900, 2900)
    # 路径不应穿过障碍区
    for x, y in path:
        assert not (1500 <= x < 1600 and 1500 <= y < 1600)


def test_route_connection_with_auto_grid():
    """route_connection 启用 auto_grid 应正确路由。"""
    config = RouteConnectionConfig(
        canvas_w=5000.0,
        canvas_h=5000.0,
        auto_grid=True,
    )
    wp = route_connection(
        (0, 0),
        (1000, 1000),
        platform="SOI",
        config=config,
    )
    assert isinstance(wp, WaveguidePath)
    assert wp.length_um > 0
    assert len(wp.points) >= 2


def test_route_connection_auto_grid_large_canvas():
    """大画布 auto_grid 应避免内存爆炸（5000×5000 μm）。"""
    config = RouteConnectionConfig(
        canvas_w=5000.0,
        canvas_h=5000.0,
        auto_grid=True,
        obstacles=[(2000, 2000, 2100, 2100)],
    )
    wp = route_connection(
        (100, 100),
        (4900, 4900),
        platform="SOI",
        config=config,
    )
    assert wp.length_um > 0
    # 路径应绕过障碍
    for x, y in wp.points:
        assert not (2000 <= x <= 2100 and 2000 <= y <= 2100)


def test_route_connection_auto_grid_vs_fixed():
    """auto_grid 与固定 grid_size 在小画布上结果应一致（同 grid_size）。"""
    # SOI 500×500 画布：auto_grid_size = max(0.6, 2.5, 0.25) = 2.5
    wp_auto = route_connection(
        (0, 0),
        (100, 100),
        platform="SOI",
        config=RouteConnectionConfig(canvas_w=500.0, canvas_h=500.0, auto_grid=True),
    )
    wp_fixed = route_connection(
        (0, 0),
        (100, 100),
        platform="SOI",
        config=RouteConnectionConfig(canvas_w=500.0, canvas_h=500.0, grid_size=2.5),
    )
    # 两者 grid_size 相同，路径长度应接近
    assert wp_auto.length_um == pytest.approx(wp_fixed.length_um, rel=1e-6)


# ---------------------------------------------------------------------------
# 阶段F2：弯曲感知布线（curvy-aware routing）测试
# 来源: LiDAR ISPD'25 https://dl.acm.org/doi/10.1145/3698364.3705355
# ---------------------------------------------------------------------------


def test_route_curvy_connection_euler():
    """弯曲感知布线（欧拉弯曲）输出平滑路径。"""
    config = RouteConnectionConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    wp = route_curvy_connection(
        (10, 10), (150, 100), platform="SOI", config=config, curve_type="euler"
    )
    assert wp.points[0] == (10, 10)
    assert wp.points[-1] == (150, 100)
    assert wp.length_um > 0
    assert wp.loss_db >= 0
    # 弯曲路径点数应多于直线段数（平滑后采样点密集）
    assert len(wp.points) > 3


def test_route_curvy_connection_arc():
    """弯曲感知布线（圆弧弯曲）输出平滑路径。"""
    config = RouteConnectionConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    wp = route_curvy_connection(
        (10, 10), (150, 100), platform="SOI", config=config, curve_type="arc"
    )
    assert wp.points[0] == (10, 10)
    assert wp.points[-1] == (150, 100)
    assert wp.length_um > 0


def test_route_curvy_connection_with_obstacles():
    """弯曲感知布线绕过障碍物。"""
    config = RouteConnectionConfig(
        canvas_w=200.0,
        canvas_h=200.0,
        grid_size=5.0,
        obstacles=[(60, 40, 80, 80)],  # 中间障碍
    )
    wp = route_curvy_connection(
        (10, 10), (150, 100), platform="SOI", config=config, curve_type="euler"
    )
    assert wp.points[0] == (10, 10)
    assert wp.points[-1] == (150, 100)
    assert wp.length_um > 0


def test_route_curvy_connection_sin_platform():
    """SiN 平台弯曲感知布线（不同弯曲半径约束）。"""
    config = RouteConnectionConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    wp = route_curvy_connection(
        (10, 10), (150, 100), platform="SiN", config=config, curve_type="euler"
    )
    assert wp.points[0] == (10, 10)
    assert wp.points[-1] == (150, 100)


def test_route_curvy_vs_straight_loss():
    """弯曲布线与直角布线均能成功且损耗为正（弯曲路径更长但转弯损耗低）。"""
    config = RouteConnectionConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    wp_curvy = route_curvy_connection(
        (10, 10), (150, 100), platform="SOI", config=config, curve_type="euler"
    )
    wp_straight = route_connection((10, 10), (150, 100), platform="SOI", config=config)
    # 两者都应成功布线且损耗为正
    assert wp_curvy.loss_db > 0
    assert wp_straight.loss_db > 0
    # 弯曲布线路径点数应更多（平滑采样）
    assert len(wp_curvy.points) >= len(wp_straight.points)


def test_route_curvy_connection_invalid_curve_type_defaults_euler():
    """无效 curve_type 回退到 euler。"""
    config = RouteConnectionConfig(canvas_w=200.0, canvas_h=200.0, grid_size=5.0)
    wp = route_curvy_connection(
        (10, 10), (150, 100), platform="SOI", config=config, curve_type="invalid"
    )
    assert wp.points[0] == (10, 10)
    assert wp.points[-1] == (150, 100)


# =============================================================================
# R3-P2-3 回归测试（v4.1）：hybrid_router/curvy_router fall-back 消除
# 旧 Bug:
#   1. hybrid_router._get_transition_loss/length 用 .get(key, 0.1/15.0) 静默 fall-back
#   2. hybrid_router._route_single_type 失败返回 total_loss_db=999.0 哨兵值
#   3. curvy_router.route_curvy 失败返回 loss_db=999.0 哨兵值
# 修复: 全部改为 raise RuntimeError/KeyError（R03 禁止 fall-back）
# =============================================================================


class TestR3P23HybridRouterFallbackRemoved:
    """R3-P2-3: hybrid_router 静默 fall-back 与 999.0 哨兵值已消除。"""

    def test_get_transition_loss_raises_on_missing_pair(self):
        """R3-P2-3: 缺失过渡对应 raise KeyError，不再返回魔数 0.1。"""
        from polaris.router.hybrid_router import (
            WaveguideType,
            _WG_TYPE_PROPS,
            _get_transition_loss,
        )
        # 所有 6 个过渡对（3×2）都应在 _WG_TYPE_PROPS 中定义
        for from_t in WaveguideType:
            for to_t in WaveguideType:
                if from_t == to_t:
                    continue
                # 不应 raise（补全后所有对都已定义）
                loss = _get_transition_loss(from_t, to_t)
                assert 0.0 < loss < 1.0, f"{from_t}→{to_t} 损耗异常: {loss}"

    def test_get_transition_length_no_magic_default(self):
        """R3-P2-3: 过渡长度不再有魔数 15.0 默认值。"""
        from polaris.router.hybrid_router import (
            WaveguideType,
            _get_transition_length,
        )
        for from_t in WaveguideType:
            for to_t in WaveguideType:
                if from_t == to_t:
                    continue
                length = _get_transition_length(from_t, to_t)
                assert 0.0 < length < 100.0, f"{from_t}→{to_t} 长度异常: {length}"

    def test_route_single_type_raises_on_failure(self):
        """R3-P2-3: 同类型布线失败应 raise，不再返回 999.0 哨兵值。"""
        from polaris.router.hybrid_router import (
            HybridNetConnection,
            HybridRouter,
            WaveguideType,
        )
        # 构造不可达场景：1x1 网格 + 起止点相同但被障碍包围
        router = HybridRouter(grid_w=3, grid_h=3, grid_size=1.0)
        # 添加障碍阻断所有路径
        router.add_obstacle(WaveguideType.RIDGE, (1, 0, 1, 2))
        router.add_obstacle(WaveguideType.RIDGE, (0, 1, 2, 1))
        net = HybridNetConnection(
            net_id="test_fail",
            start=(0.0, 0.0),
            end=(2.0, 2.0),
            wg_type_start=WaveguideType.RIDGE,
            wg_type_end=WaveguideType.RIDGE,
        )
        with pytest.raises(RuntimeError, match="R03 禁止 fall-back"):
            router.route(net)

    def test_route_mixed_type_raises_on_failure(self):
        """R3-P2-3: 混合类型布线失败应 raise，不再 fall-back 到单一类型。"""
        from polaris.router.hybrid_router import (
            HybridNetConnection,
            HybridRouter,
            WaveguideType,
        )
        router = HybridRouter(grid_w=3, grid_h=3, grid_size=1.0)
        # 阻断 RIDGE 和 BURIED 的所有路径
        router.add_obstacle(WaveguideType.RIDGE, (1, 0, 1, 2))
        router.add_obstacle(WaveguideType.BURIED, (1, 0, 1, 2))
        net = HybridNetConnection(
            net_id="test_mixed_fail",
            start=(0.0, 0.0),
            end=(2.0, 2.0),
            wg_type_start=WaveguideType.RIDGE,
            wg_type_end=WaveguideType.BURIED,
        )
        with pytest.raises(RuntimeError, match="R03 禁止 fall-back"):
            router.route(net)


class TestR3P23CurvyRouterFallbackRemoved:
    """R3-P2-3: curvy_router.route_curvy 失败应 raise，不再返回 999.0 哨兵值。"""

    def test_route_curvy_raises_on_failure(self):
        """R3-P2-3: 弯曲布线失败应 raise RuntimeError。"""
        from polaris.router.curvy_router import CurvyRouteConfig, CurvyRouter

        # 构造不可达场景：3x3 网格，中心被障碍完全阻断
        config = CurvyRouteConfig(grid_w=3, grid_h=3, grid_size=1.0)
        router = CurvyRouter(config)
        # 添加十字障碍阻断所有路径（add_obstacle 签名: gx, gy, gw, gh）
        router.add_obstacle(1, 0, 1, 3)  # 竖直障碍 (x=1, 全高)
        router.add_obstacle(0, 1, 3, 1)  # 水平障碍 (y=1, 全宽)

        with pytest.raises(RuntimeError, match="R03 禁止 fall-back"):
            router.route_curvy((0, 0), (2, 2))
