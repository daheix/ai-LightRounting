"""波导约束布线器测试（Task 11）。"""

from __future__ import annotations

import pytest

from polaris.router.waveguide_router import (
    GridRouter,
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
    router = GridRouter(50, 50, grid_size=1.0, min_bend_radius_um=5.0)
    path = router.route((0, 0), (40, 40))
    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (40, 40)


def test_grid_router_obstacle_avoidance():
    router = GridRouter(50, 50, grid_size=1.0, min_bend_radius_um=5.0)
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
        (0, 0), (100, 100), platform="SOI",
        grid_size=2.0, canvas_w=500, canvas_h=500,
    )
    assert isinstance(wp, WaveguidePath)
    assert wp.length_um > 0
    assert wp.loss_db >= 0
    assert len(wp.points) >= 2


def test_route_connection_with_obstacles():
    wp = route_connection(
        (0, 0), (100, 100), platform="SOI",
        grid_size=2.0, canvas_w=500, canvas_h=500,
        obstacles=[(40, 40, 60, 60)],
    )
    assert wp.length_um > 0


def test_route_connection_equal_length():
    wp = route_connection(
        (0, 0), (50, 0), platform="SOI",
        grid_size=2.0, canvas_w=500, canvas_h=500,
        target_length_um=200.0,
    )
    assert wp.length_um >= 200.0
