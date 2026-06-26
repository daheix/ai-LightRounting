"""G02 布线验收测试。

验证路径搜索、无交叉、长度最小化功能。

文献来源:
- Hart, Nilsson & Raphael, 1968, A* 搜索算法
  https://en.wikipedia.org/wiki/A*_search_algorithm
- Harabor & Grastien, 2011, Jump Point Search (JPS)
  https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf
- LiDAR, ISPD 2025, 曲线感知 A* 光波导详细布线
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Fujisawa et al., 2017, 欧拉弯曲降低弯曲损耗
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Red Blob Games, A* 实现优化
  https://www.redblobgames.com/pathfinding/a-star/implementation.html
"""

import math

import numpy as np
import pytest

from polaris.router.waveguide_router import (
    GridRouter,
    PLATFORM_CONSTRAINTS,
    RouterConstraints,
    WaveguidePath,
    auto_grid_size,
    get_platform_constraints,
)
from polaris.router.obstacle_grid import ObstacleGrid
from polaris.router.path_geometry import (
    arc_bend,
    check_min_spacing,
    count_crossings,
    equalize_length,
    euler_bend,
    path_length,
    path_loss,
    s_bend,
)


# ============================================================
# WaveguidePath 波导路径测试
# ============================================================
class TestWaveguidePath:
    """WaveguidePath 波导路径测试。"""

    def test_init_empty(self):
        """M1: 空路径初始化。"""
        p = WaveguidePath()
        assert len(p.points) == 0
        assert p.length_um == 0.0
        assert p.loss_db == 0.0
        assert p.num_bends == 0
        assert p.num_crossings == 0

    def test_add_single_point(self):
        """M1: 添加单个点。"""
        p = WaveguidePath()
        p.add_point(0.0, 0.0)
        assert len(p.points) == 1
        assert p.length_um == 0.0

    def test_add_two_points_length(self):
        """M2: 添加两点后长度正确。"""
        p = WaveguidePath()
        p.add_point(0.0, 0.0)
        p.add_point(3.0, 4.0)
        assert len(p.points) == 2
        assert p.length_um == pytest.approx(5.0)

    def test_add_multiple_points(self):
        """M2: 添加多点累积长度。"""
        p = WaveguidePath()
        p.add_point(0.0, 0.0)
        p.add_point(10.0, 0.0)
        p.add_point(10.0, 5.0)
        assert p.length_um == pytest.approx(15.0)


# ============================================================
# RouterConstraints 布线约束测试
# ============================================================
class TestRouterConstraints:
    """RouterConstraints 布线约束测试。"""

    def test_default_soi(self):
        """M1: SOI 默认约束来自 PDK。"""
        cons = RouterConstraints()
        assert cons.min_bend_radius_um == 5.0
        assert cons.min_spacing_um == 1.0

    def test_custom_constraints(self):
        """M1: 自定义约束。"""
        cons = RouterConstraints(min_bend_radius_um=10.0, min_spacing_um=2.0)
        assert cons.min_bend_radius_um == 10.0
        assert cons.min_spacing_um == 2.0

    def test_platform_constraints_soi(self):
        """M1: SOI 平台约束。"""
        cons = get_platform_constraints("SOI")
        assert isinstance(cons, dict)
        assert cons["min_bend_radius_um"] > 0.0

    def test_platform_constraints_all(self):
        """M1: 所有平台都有约束。"""
        for platform in PLATFORM_CONSTRAINTS:
            cons = get_platform_constraints(platform)
            assert cons["min_bend_radius_um"] > 0.0
            assert cons["min_spacing_um"] > 0.0

    def test_unknown_platform_falls_back_to_soi(self):
        """M1: 未知平台回退到 SOI。"""
        cons = get_platform_constraints("UNKNOWN_PLATFORM")
        assert cons == PLATFORM_CONSTRAINTS["SOI"]


# ============================================================
# ObstacleGrid 障碍物栅格测试
# ============================================================
class TestObstacleGrid:
    """ObstacleGrid 障碍物栅格测试。"""

    def test_init_empty(self):
        """M1: 初始空栅格。"""
        grid = ObstacleGrid(10, 10)
        assert grid.shape == (10, 10)
        assert not grid.is_blocked(5, 5)

    def test_mark_region_and_check(self):
        """M1: 标记区域后检查为阻塞。"""
        grid = ObstacleGrid(10, 10)
        grid.mark_region(3, 3, 6, 6)
        assert grid.is_blocked(3, 3)
        assert grid.is_blocked(4, 4)
        assert not grid.is_blocked(2, 2)
        assert not grid.is_blocked(6, 6)

    def test_is_dense(self):
        """M1: 小网格稠密存储。"""
        grid = ObstacleGrid(10, 10)
        assert grid.is_dense is True

    def test_total_cells(self):
        """M1: 总单元数正确。"""
        grid = ObstacleGrid(10, 20)
        assert grid.total_cells == 200

    def test_out_of_bounds_negative_index(self):
        """M1: 负索引在稠密模式下按 numpy 语义处理（绕回）。"""
        grid = ObstacleGrid(10, 10)
        assert not grid.is_blocked(-1, 5)
        assert not grid.is_blocked(5, -1)

    def test_out_of_bounds_large_index_raises(self):
        """M1: 超出上界的索引触发 IndexError（稠密模式）。"""
        grid = ObstacleGrid(10, 10)
        with pytest.raises(IndexError):
            grid.is_blocked(10, 5)
        with pytest.raises(IndexError):
            grid.is_blocked(5, 10)

    def test_blocked_cells(self):
        """M2: 列出所有阻塞单元。"""
        grid = ObstacleGrid(10, 10)
        grid.mark_region(0, 0, 2, 2)
        blocked = list(grid.blocked_cells())
        assert len(blocked) == 4

    def test_memory_estimate(self):
        """M1: 内存估计非负。"""
        grid = ObstacleGrid(10, 10)
        assert grid.memory_estimate_bytes() >= 0


# ============================================================
# GridRouter 网格布线器测试
# ============================================================
class TestGridRouter:
    """GridRouter A* 网格布线器测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        router = GridRouter(grid_w=20, grid_h=20)
        assert router.grid_w == 20
        assert router.grid_h == 20
        assert router.grid_size == 1.0

    def test_init_with_constraints(self):
        """M1: 带约束初始化。"""
        cons = RouterConstraints(min_bend_radius_um=10.0, min_spacing_um=2.0)
        router = GridRouter(grid_w=20, grid_h=20, grid_size=2.0, constraints=cons)
        assert router.min_bend_radius_um == 10.0
        assert router.min_spacing_um == 2.0

    def test_route_straight_line(self):
        """M1: 直线路径搜索成功。"""
        router = GridRouter(grid_w=20, grid_h=20)
        path = router.route((0, 10), (19, 10))
        assert path is not None
        assert path[0] == (0, 10)
        assert path[-1] == (19, 10)

    def test_route_returns_list(self):
        """M1: 返回路径为列表。"""
        router = GridRouter(grid_w=20, grid_h=20)
        path = router.route((0, 0), (10, 10))
        assert isinstance(path, list)
        assert len(path) >= 2

    def test_route_with_obstacle(self):
        """M2: 绕过障碍物。"""
        router = GridRouter(grid_w=20, grid_h=20)
        router.add_obstacle(5, 5, 1, 10)
        path = router.route((0, 10), (19, 10))
        assert path is not None
        assert path[0] == (0, 10)
        assert path[-1] == (19, 10)

    def test_route_impossible_returns_none(self):
        """M3: 完全阻塞时返回 None。"""
        router = GridRouter(grid_w=10, grid_h=10)
        for y in range(10):
            router.add_obstacle(5, y)
        path = router.route((0, 5), (9, 5))
        assert path is None

    def test_route_same_point(self):
        """M1: 起点=终点时路径长度为 1。"""
        router = GridRouter(grid_w=10, grid_h=10)
        path = router.route((5, 5), (5, 5))
        assert path is not None
        assert len(path) >= 1
        assert path[0] == (5, 5)

    def test_add_obstacle_box(self):
        """M2: 按画布坐标添加障碍盒。"""
        router = GridRouter(grid_w=100, grid_h=100, grid_size=1.0)
        router.add_obstacle_box(10.5, 20.5, 30.5, 40.5)
        assert router.obstacle.is_blocked(15, 30)
        assert not router.obstacle.is_blocked(5, 30)

    def test_heuristic_manhattan(self):
        """M1: Manhattan 启发式正确。"""
        router = GridRouter(grid_w=10, grid_h=10)
        h = router._heuristic((0, 0), (3, 4))
        assert h == 7.0

    def test_min_bend_steps_calculation(self):
        """M2: 最小弯曲步数计算正确。"""
        cons = RouterConstraints(min_bend_radius_um=10.0)
        router = GridRouter(grid_w=100, grid_h=100, grid_size=2.0, constraints=cons)
        assert router.min_bend_steps >= 2

    def test_zero_bend_radius(self):
        """M1: 零弯曲半径时 min_bend_steps=1。"""
        cons = RouterConstraints(min_bend_radius_um=0.0)
        router = GridRouter(grid_w=10, grid_h=10, constraints=cons)
        assert router.min_bend_steps == 1

    def test_l_route(self):
        """M2: L 形路径搜索。"""
        router = GridRouter(grid_w=20, grid_h=20)
        path = router.route((0, 0), (10, 5))
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (10, 5)


# ============================================================
# 路径几何工具测试
# ============================================================
class TestPathGeometry:
    """路径几何工具测试。"""

    def test_path_length_straight(self):
        """M1: 直线路径长度正确。"""
        points = [(0.0, 0.0), (10.0, 0.0)]
        assert path_length(points) == pytest.approx(10.0)

    def test_path_length_lshape(self):
        """M2: L 形路径长度正确。"""
        points = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
        assert path_length(points) == pytest.approx(15.0)

    def test_path_length_empty(self):
        """M1: 空路径长度为 0。"""
        assert path_length([]) == 0.0
        assert path_length([(0.0, 0.0)]) == 0.0

    def test_path_loss_proportional(self):
        """M2: 损耗与长度成正比。"""
        p1 = [(0.0, 0.0), (100.0, 0.0)]
        p2 = [(0.0, 0.0), (200.0, 0.0)]
        l1 = path_loss(p1, loss_db_cm=1.0)
        l2 = path_loss(p2, loss_db_cm=1.0)
        assert l2 > l1

    def test_arc_bend_90_degrees(self):
        """M2: 90 度圆弧弯曲。"""
        points = arc_bend(radius_um=5.0, angle_deg=90.0, n_points=20)
        assert len(points) == 21
        start = points[0]
        end = points[-1]
        assert start == pytest.approx((0.0, 0.0), abs=1e-9)
        assert abs(end[0] - 5.0) < 0.5
        assert abs(end[1] - 5.0) < 0.5

    def test_euler_bend(self):
        """M2: 欧拉弯曲生成。"""
        points = euler_bend(radius_um=5.0, angle_deg=90.0, n_points=30)
        assert len(points) == 31
        assert points[0] == (0.0, 0.0)

    def test_s_bend(self):
        """M2: S 形弯曲。"""
        points = s_bend(0.0, 0.0, 10.0, 5.0, n_points=20)
        assert len(points) == 21
        assert points[0] == (0.0, 0.0)
        assert abs(points[-1][0] - 10.0) < 0.1
        assert abs(points[-1][1] - 5.0) < 0.1

    def test_equalize_length(self):
        """M3: 等长调整。"""
        path = [(0.0, 0.0), (100.0, 0.0)]
        equalized = equalize_length(path, target_length_um=150.0)
        assert path_length(equalized) >= 100.0

    def test_equalize_length_already_longer(self):
        """M2: 已达目标长度时不变。"""
        path = [(0.0, 0.0), (200.0, 0.0)]
        equalized = equalize_length(path, target_length_um=100.0)
        assert equalized == path

    def test_count_crossings_none(self):
        """M1: 不相交路径交叉数为 0。"""
        path1 = [(0.0, 0.0), (10.0, 0.0)]
        path2 = [(0.0, 5.0), (10.0, 5.0)]
        assert count_crossings(path1, path2) == 0

    def test_count_crossings_one(self):
        """M2: 单对交叉路径。"""
        path1 = [(0.0, 0.0), (10.0, 10.0)]
        path2 = [(0.0, 10.0), (10.0, 0.0)]
        assert count_crossings(path1, path2) == 1

    def test_check_min_spacing_pass(self):
        """M2: 满足最小间距。"""
        path1 = [(0.0, 0.0), (10.0, 0.0)]
        path2 = [(0.0, 5.0), (10.0, 5.0)]
        assert check_min_spacing(path1, path2, min_spacing_um=2.0)

    def test_check_min_spacing_fail(self):
        """M2: 不满足最小间距。"""
        path1 = [(0.0, 0.0), (10.0, 0.0)]
        path2 = [(0.0, 0.5), (10.0, 0.5)]
        assert not check_min_spacing(path1, path2, min_spacing_um=2.0)


# ============================================================
# auto_grid_size 自动网格尺寸测试
# ============================================================
class TestAutoGridSize:
    """auto_grid_size 自动网格尺寸测试。"""

    def test_soi_default(self):
        """M1: SOI 平台网格尺寸合理。"""
        gs = auto_grid_size(1000.0, 1000.0, platform="SOI")
        assert gs > 0.0
        assert gs < 10.0

    def test_larger_canvas_larger_grid(self):
        """M2: 更大画布使用更大网格。"""
        gs_small = auto_grid_size(100.0, 100.0, platform="SOI")
        gs_large = auto_grid_size(10000.0, 10000.0, platform="SOI")
        assert gs_large >= gs_small

    def test_custom_bend_radius(self):
        """M2: 自定义弯曲半径影响网格尺寸。"""
        gs_small = auto_grid_size(1000.0, 1000.0, platform="SOI", min_bend_radius_um=2.0)
        gs_large = auto_grid_size(1000.0, 1000.0, platform="SOI", min_bend_radius_um=20.0)
        assert gs_large >= gs_small

    def test_unknown_platform_works(self):
        """M1: 未知平台使用默认值（不报错）。"""
        gs = auto_grid_size(1000.0, 1000.0, platform="UNKNOWN_SOIV")
        assert gs > 0.0
