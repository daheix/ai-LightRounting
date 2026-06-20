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
    assert sin["min_bend_radius_um"] == 50.0
    inp = get_platform_constraints("InP")
    assert inp["min_bend_radius_um"] == 100.0


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
    # SiN: w=1.0, R=50 → max(1.2, 25.0, 2.5) = 25.0
    assert gs == pytest.approx(25.0)


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
