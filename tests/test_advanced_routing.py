"""R10 路标：advanced_routing 单元测试。

覆盖 JPS、Bundle、AllAngle、Dubins、AutoTaper、PathLengthMatch、
自适应交叉插入等 7 个功能模块 + 1 个集成测试。

测试原则（规则 14.1）：禁止 fall-back，所有错误路径必须 raise。
"""

from __future__ import annotations

import math

import pytest

from polaris.router.advanced_routing import (
    AllAngleRouter,
    BundleRouteResult,
    JPSRouter,
    adaptive_crossing_insertion,
    auto_taper,
    dubins_path,
    route_bundle,
    route_bundle_path_length_match,
)


# 1. JPS (Jump Point Search) 测试
class TestJPSRouter:
    """JPS 布线器测试（Harabor & Grastien AAAI 2011）。"""

    def test_basic_horizontal_route(self):
        """水平直行布线。"""
        router = JPSRouter(20, 20)
        path = router.route((0, 0), (10, 0))
        assert path[0] == (0, 0)
        assert path[-1] == (10, 0)
        assert len(path) == 11  # 0→10 共 11 个点

    def test_basic_vertical_route(self):
        """垂直直行布线。"""
        router = JPSRouter(20, 20)
        path = router.route((0, 0), (0, 10))
        assert path[0] == (0, 0)
        assert path[-1] == (0, 10)
        assert len(path) == 11

    def test_l_shaped_route(self):
        """L 形布线（含一次转弯）。"""
        router = JPSRouter(20, 20)
        path = router.route((0, 0), (10, 10))
        assert path[0] == (0, 0)
        assert path[-1] == (10, 10)
        manhattan = sum(
            abs(path[i][0] - path[i - 1][0]) + abs(path[i][1] - path[i - 1][1])
            for i in range(1, len(path))
        )
        assert manhattan >= 20

    def test_obstacle_avoidance(self):
        """障碍物绕行。"""
        router = JPSRouter(20, 20)
        router.add_obstacle(5, 0, 1, 12)  # 留 (5, 12) 通道
        path = router.route((0, 5), (10, 5))
        assert path[0] == (0, 5)
        assert path[-1] == (10, 5)
        for x, y in path:
            assert not (x == 5 and 0 <= y <= 11)

    def test_no_path_raises(self):
        """无可行路径必须 raise RuntimeError（禁止 fall-back）。"""
        router = JPSRouter(10, 10)
        router.add_obstacle(5, 0, 1, 10)
        with pytest.raises(RuntimeError, match="JPS 无可行路径"):
            router.route((0, 5), (9, 5))

    def test_start_on_obstacle_raises(self):
        """起点在障碍上必须 raise ValueError。"""
        router = JPSRouter(10, 10)
        router.add_obstacle(0, 0)
        with pytest.raises(ValueError, match="起点"):
            router.route((0, 0), (9, 9))

    def test_goal_on_obstacle_raises(self):
        """终点在障碍上必须 raise ValueError。"""
        router = JPSRouter(10, 10)
        router.add_obstacle(9, 9)
        with pytest.raises(ValueError, match="终点"):
            router.route((0, 0), (9, 9))

    def test_invalid_params_raises(self):
        """无效参数必须 raise ValueError。"""
        with pytest.raises(ValueError, match="网格尺寸"):
            JPSRouter(0, 10)
        with pytest.raises(ValueError, match="网格尺寸"):
            JPSRouter(10, -1)
        with pytest.raises(ValueError, match="min_bend_steps"):
            JPSRouter(10, 10, min_bend_steps=0)


# 2. Bundle 布线测试
class TestRouteBundle:
    """Bundle 布线测试（对标 gdsfactory route_bundle）。"""

    def test_basic_bundle(self):
        """基本多端口对布线。"""
        ports1 = [(0, 0), (0, 5), (0, 10)]
        ports2 = [(20, 0), (20, 5), (20, 10)]
        result = route_bundle(ports1, ports2, 25, 25, separation=2)
        assert result.success
        assert len(result.routes) == 3
        for route in result.routes:
            assert len(route) > 0
            assert route[0] in ports1
            assert route[-1] in ports2

    def test_port_mismatch_raises(self):
        """端口数量不匹配必须 raise ValueError。"""
        with pytest.raises(ValueError, match="长度不匹配"):
            route_bundle([(0, 0)], [(10, 0), (10, 5)], 20, 20)

    def test_bundle_with_obstacles(self):
        """带障碍的 bundle 布线。"""
        ports1 = [(0, 0), (0, 10)]
        ports2 = [(20, 0), (20, 10)]
        obstacles = [(10, 0, 1, 15)]
        result = route_bundle(ports1, ports2, 25, 25, separation=2, obstacles=obstacles)
        assert isinstance(result, BundleRouteResult)
        assert len(result.routes) == 2

    def test_bundle_result_structure(self):
        """BundleRouteResult 数据结构完整性。"""
        result = route_bundle([(0, 0)], [(10, 0)], 15, 15)
        assert hasattr(result, "routes")
        assert hasattr(result, "port_pairs")
        assert hasattr(result, "success")
        assert hasattr(result, "failed_pairs")
        assert result.port_pairs == [((0, 0), (10, 0))]


# 3. 非曼哈顿布线（All-Angle）测试
class TestAllAngleRouter:
    """AllAngle 布线器测试（LiDAR ISPD 2025）。"""

    def test_basic_all_angle(self):
        """基本非曼哈顿布线。"""
        router = AllAngleRouter(20, 20)
        path = router.route_all_angle((0.0, 0.0), (10.0, 10.0))
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 10.0)

    def test_diagonal_route(self):
        """对角线布线（45°）。"""
        router = AllAngleRouter(20, 20)
        path = router.route_all_angle((0.0, 0.0), (8.0, 8.0))
        assert len(path) >= 2
        actual = sum(
            math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            for i in range(1, len(path))
        )
        assert actual <= 16 + 0.01  # 曼哈顿距离 16

    def test_no_path_raises(self):
        """无可行路径必须 raise RuntimeError。"""
        router = AllAngleRouter(10, 10)
        router.add_obstacle(5, 0, 1, 10)
        with pytest.raises(RuntimeError, match="AllAngle 无可行路径"):
            router.route_all_angle((0.0, 5.0), (9.0, 5.0))

    def test_start_on_obstacle_raises(self):
        """起点在障碍上必须 raise ValueError。"""
        router = AllAngleRouter(10, 10)
        router.add_obstacle(0, 0)
        with pytest.raises(ValueError, match="起点"):
            router.route_all_angle((0.0, 0.0), (9.0, 9.0))

    def test_invalid_params_raises(self):
        """无效参数必须 raise ValueError。"""
        with pytest.raises(ValueError, match="网格尺寸"):
            AllAngleRouter(0, 10)
        with pytest.raises(ValueError, match="min_bend_steps"):
            AllAngleRouter(10, 10, min_bend_steps=0)


# 4. Dubins Path 测试
class TestDubinsPath:
    """Dubins path 测试（Dubins 1957）。"""

    def test_basic_dubins(self):
        """基本 Dubins 路径。"""
        path = dubins_path((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), radius=2.0)
        assert len(path) >= 2
        assert math.isclose(path[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(path[0][1], 0.0, abs_tol=1e-6)
        assert math.isclose(path[-1][0], 10.0, abs_tol=1e-1)
        assert math.isclose(path[-1][1], 0.0, abs_tol=1e-1)

    def test_invalid_radius_raises(self):
        """无效半径必须 raise ValueError。"""
        with pytest.raises(ValueError, match="radius"):
            dubins_path((0, 0, 0), (10, 0, 0), radius=0)
        with pytest.raises(ValueError, match="radius"):
            dubins_path((0, 0, 0), (10, 0, 0), radius=-1.0)

    def test_turn_path(self):
        """转弯路径（90°）。"""
        path = dubins_path((0.0, 0.0, 0.0), (5.0, 5.0, 90.0), radius=2.0)
        assert len(path) >= 2
        assert math.isclose(path[-1][0], 5.0, abs_tol=1.0)
        assert math.isclose(path[-1][1], 5.0, abs_tol=1.0)

    def test_path_continuity(self):
        """路径连续性（相邻点距离合理）。"""
        path = dubins_path((0.0, 0.0, 0.0), (10.0, 5.0, 45.0), radius=3.0)
        for i in range(1, len(path)):
            dist = math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            assert dist < 5.0


# 5. Auto Taper 测试
class TestAutoTaper:
    """Auto Taper 测试（对标 gdsfactory）。"""

    def test_basic_taper(self):
        """基本锥形过渡。"""
        route = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
        result = auto_taper(route, taper_length=5.0, start_width=0.5, end_width=1.0)
        assert len(result) == 5
        assert math.isclose(result[0][2], 0.5, abs_tol=0.01)
        assert math.isclose(result[2][2], 1.0, abs_tol=0.01)

    def test_empty_route(self):
        """空路径返回空列表。"""
        assert auto_taper([], taper_length=5.0) == []

    def test_short_route(self):
        """短路径（总长 < 2×taper_length）退化处理。"""
        route = [(0.0, 0.0), (1.0, 0.0)]
        result = auto_taper(route, taper_length=10.0, start_width=0.5, end_width=1.0)
        assert len(result) == 2
        assert result[0][2] <= result[1][2] + 0.01

    def test_zero_taper_length(self):
        """taper_length=0 时全部使用 end_width。"""
        route = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        result = auto_taper(route, taper_length=0, start_width=0.5, end_width=1.0)
        for _, _, w in result:
            assert math.isclose(w, 1.0)


# 6. Path Length Match 测试
class TestPathLengthMatch:
    """等长匹配布线测试（对标 gdsfactory route_bundle_path_length_match）。"""

    def test_basic_length_match(self):
        """基本等长匹配。"""
        ports1 = [(0, 0), (0, 10)]
        ports2 = [(20, 0), (20, 10)]
        result = route_bundle_path_length_match(ports1, ports2, 25, 25, separation=2)
        assert result.success
        lengths = []
        for route in result.routes:
            if route:
                length = sum(
                    abs(route[i][0] - route[i - 1][0]) + abs(route[i][1] - route[i - 1][1])
                    for i in range(1, len(route))
                )
                lengths.append(length)
        if len(lengths) >= 2:
            assert max(lengths) - min(lengths) <= 5.0

    def test_failed_bundle_passthrough(self):
        """bundle 失败时直接返回（不添加绕线）。"""
        obstacles = [(5, 0, 1, 20)]
        result = route_bundle_path_length_match(
            [(0, 0)], [(10, 0)], 15, 20, separation=1, obstacles=obstacles
        )
        assert not result.success


# 7. 自适应交叉插入测试（创新）
class TestAdaptiveCrossing:
    """自适应交叉插入测试（创新功能）。"""

    def test_no_crossings(self):
        """无交叉时返回原路径。"""
        route = [(0, 0), (5, 0), (10, 0)]
        other = [(0, 5), (5, 5), (10, 5)]
        assert adaptive_crossing_insertion(route, [other]) == route

    def test_insert_crossing_when_cheap(self):
        """交叉代价低时插入交叉（保持原路径）。"""
        route = [(0, 0), (5, 0), (10, 0)]
        other = [(5, -5), (5, 0), (5, 5)]
        result = adaptive_crossing_insertion(route, [other], crossing_cost=1.0, detour_cost=10.0)
        assert result == route

    def test_bypass_when_detour_cheap(self):
        """绕行代价低时绕行（插入 U 形点）。"""
        route = [(0, 0), (5, 0), (10, 0)]
        other = [(5, -5), (5, 0), (5, 5)]
        result = adaptive_crossing_insertion(route, [other], crossing_cost=100.0, detour_cost=1.0)
        assert len(result) > len(route)

    def test_empty_and_no_other(self):
        """空路径与无其他路径的边界情况。"""
        assert adaptive_crossing_insertion([], [[(1, 1)]]) == []
        route = [(0, 0), (5, 0)]
        assert adaptive_crossing_insertion(route, []) == route


# 8. R10 集成测试
class TestR10Integration:
    """R10 路标集成测试：验证全部 7 个模块协同工作。"""

    def test_all_modules_importable(self):
        """全部 7 个模块可导入。"""
        from polaris.router.advanced_routing import (
            AllAngleRouter,
            BundleRouteResult,
            JPSRouter,
            adaptive_crossing_insertion,
            auto_taper,
            dubins_path,
            route_bundle,
            route_bundle_path_length_match,
        )

        assert callable(JPSRouter)
        assert callable(AllAngleRouter)
        assert callable(route_bundle)
        assert callable(dubins_path)
        assert callable(auto_taper)
        assert callable(route_bundle_path_length_match)
        assert callable(adaptive_crossing_insertion)
        assert BundleRouteResult is not None

    def test_jps_to_taper_pipeline(self):
        """JPS 布线 → Auto Taper 流水线。"""
        router = JPSRouter(30, 30)
        path = router.route((0, 0), (20, 10))
        float_path = [(float(x), float(y)) for x, y in path]
        tapered = auto_taper(float_path, taper_length=5.0, start_width=0.5, end_width=1.0)
        assert len(tapered) == len(float_path)
        for _x, _y, w in tapered:
            assert 0.5 - 0.01 <= w <= 1.0 + 0.01

    def test_bundle_to_crossing_pipeline(self):
        """Bundle 布线 → 自适应交叉流水线。"""
        ports1 = [(0, 0), (0, 10)]
        ports2 = [(20, 0), (20, 10)]
        bundle = route_bundle(ports1, ports2, 25, 25, separation=2)
        assert bundle.success
        if len(bundle.routes) >= 2 and bundle.routes[0] and bundle.routes[1]:
            result = adaptive_crossing_insertion(
                bundle.routes[0], [bundle.routes[1]], crossing_cost=5.0, detour_cost=1.0
            )
            assert isinstance(result, list)

    def test_dubins_standalone(self):
        """Dubins path 独立可用。"""
        path = dubins_path((0.0, 0.0, 0.0), (15.0, 5.0, 30.0), radius=3.0)
        assert len(path) >= 2
        assert math.isclose(path[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(path[0][1], 0.0, abs_tol=1e-6)

    def test_no_fallback_design(self):
        """验证无 fall-back 设计：所有错误路径必须 raise（规则 14.1）。"""
        router = JPSRouter(10, 10)
        router.add_obstacle(5, 0, 1, 10)
        with pytest.raises(RuntimeError):
            router.route((0, 5), (9, 5))
        router2 = AllAngleRouter(10, 10)
        router2.add_obstacle(5, 0, 1, 10)
        with pytest.raises(RuntimeError):
            router2.route_all_angle((0.0, 5.0), (9.0, 5.0))
        with pytest.raises(ValueError):
            dubins_path((0, 0, 0), (10, 0, 0), radius=0)
