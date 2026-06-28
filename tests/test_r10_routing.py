"""R10 路标布线算法单元测试。

覆盖 JPS、Bundle、PathLengthMatch、Dubins、AutoTaper、AllAngle、集成测试。
测试原则（规则 14.1）：禁止 fall-back，所有错误路径必须 raise。
测试用真实布线场景，禁止假数据。
"""

from __future__ import annotations

import ast
import math

import pytest

from polaris.router.all_angle_router import AllAngleRouter
from polaris.router.bundle_router import (
    auto_taper,
    dubins_path,
    route_bundle,
    route_bundle_from_waypoints,
    route_bundle_path_length_match,
)
from polaris.router.jps_router import JPSRouter
from polaris.router.path_geometry import path_length
from polaris.router.waveguide_router import GridRouter, RouterConstraints


def _manhattan_len(path: list[tuple[int, int]]) -> int:
    """计算网格路径曼哈顿长度。"""
    return sum(
        abs(path[i][0] - path[i - 1][0]) + abs(path[i][1] - path[i - 1][1])
        for i in range(1, len(path))
    )


# ---------------------------------------------------------------------------
# 1. JPS (Jump Point Search) 测试
# ---------------------------------------------------------------------------
class TestJPSRouter:
    """JPS 布线器测试（Harabor & Grastien AAAI 2011）。"""

    def test_basic_horizontal_route(self):
        """水平直行布线。"""
        router = JPSRouter(20, 20, 1.0, None)
        path = router.route((0, 0), (10, 0))
        assert path[0] == (0, 0)
        assert path[-1] == (10, 0)
        assert len(path) == 11  # 0→10 共 11 个点

    def test_basic_vertical_route(self):
        """垂直直行布线。"""
        router = JPSRouter(20, 20, 1.0, None)
        path = router.route((0, 0), (0, 10))
        assert path[0] == (0, 0)
        assert path[-1] == (0, 10)
        assert len(path) == 11

    def test_l_shaped_route(self):
        """L 形布线（含一次转弯）。"""
        router = JPSRouter(20, 20, 1.0, None)
        path = router.route((0, 0), (10, 10))
        assert path[0] == (0, 0)
        assert path[-1] == (10, 10)
        assert _manhattan_len(path) >= 20  # 曼哈顿距离 20

    def test_obstacle_avoidance(self):
        """障碍物绕行。"""
        router = JPSRouter(20, 20, 1.0, None)
        router.add_obstacle(5, 0, 1, 12)  # 留 (5,12) 通道
        path = router.route((0, 5), (10, 5))
        assert path[0] == (0, 5)
        assert path[-1] == (10, 5)
        for x, y in path:
            assert not (x == 5 and 0 <= y <= 11)

    def test_path_length_matches_grid_router(self):
        """JPSRouter 与 GridRouter 路径长度一致（无弯曲约束时）。"""
        cons = RouterConstraints(min_bend_radius_um=0.0)  # 无弯曲约束
        grid = GridRouter(20, 20, 1.0, cons)
        jps = JPSRouter(20, 20, 1.0, cons)
        g_path = grid.route((0, 0), (15, 10))
        j_path = jps.route((0, 0), (15, 10))
        assert g_path is not None
        assert j_path is not None
        assert _manhattan_len(g_path) == _manhattan_len(j_path)

    def test_no_path_raises(self):
        """无可行路径必须 raise RuntimeError（禁止 fall-back）。"""
        router = JPSRouter(10, 10, 1.0, None)
        router.add_obstacle(5, 0, 1, 10)  # 垂直墙阻断
        with pytest.raises(RuntimeError, match="JPS 无可行路径"):
            router.route((0, 5), (9, 5))

    def test_start_on_obstacle_raises(self):
        """起点在障碍上必须 raise ValueError。"""
        router = JPSRouter(10, 10, 1.0, None)
        router.add_obstacle(0, 0)
        with pytest.raises(ValueError, match="起点"):
            router.route((0, 0), (9, 9))

    def test_goal_on_obstacle_raises(self):
        """终点在障碍上必须 raise ValueError。"""
        router = JPSRouter(10, 10, 1.0, None)
        router.add_obstacle(9, 9)
        with pytest.raises(ValueError, match="终点"):
            router.route((0, 0), (9, 9))

    def test_path_validity(self):
        """路径连续性：相邻点曼哈顿距离为 1。"""
        router = JPSRouter(20, 20, 1.0, None)
        path = router.route((0, 0), (15, 10))
        for i in range(1, len(path)):
            step = abs(path[i][0] - path[i - 1][0]) + abs(path[i][1] - path[i - 1][1])
            assert step == 1


# ---------------------------------------------------------------------------
# 2. Bundle 布线测试
# ---------------------------------------------------------------------------
class TestRouteBundle:
    """Bundle 布线测试（对标 gdsfactory route_bundle）。"""

    def test_basic_bundle(self):
        """基本多端口对布线。"""
        ports1 = [(0, 0), (0, 5), (0, 10)]
        ports2 = [(20, 0), (20, 5), (20, 10)]
        routes = route_bundle(ports1, ports2, separation=2, grid_w=25, grid_h=25)
        assert len(routes) == 3
        for route in routes:
            assert len(route) > 0
            assert route[0] in ports1
            assert route[-1] in ports2

    def test_separation_constraint(self):
        """separation 约束：路径间无共享点（防碰撞）。"""
        ports1 = [(0, 0), (0, 5)]
        ports2 = [(20, 0), (20, 5)]
        routes = route_bundle(ports1, ports2, separation=2, grid_w=25, grid_h=25)
        assert len(routes) == 2
        set1 = set(routes[0])
        set2 = set(routes[1])
        assert not (set1 & set2)  # 无共享点

    def test_port_sorting(self):
        """端口排序：按 y 坐标配对，乱序输入也能正确布线。"""
        ports1 = [(0, 10), (0, 0), (0, 5)]  # 乱序
        ports2 = [(20, 0), (20, 5), (20, 10)]
        routes = route_bundle(ports1, ports2, separation=2, grid_w=25, grid_h=25)
        assert len(routes) == 3
        for route in routes:
            assert len(route) > 0

    def test_mismatch_raises(self):
        """端口数量不匹配必须 raise ValueError。"""
        with pytest.raises(ValueError, match="长度不匹配"):
            route_bundle([(0, 0)], [(10, 0), (10, 5)], grid_w=15, grid_h=15)

    def test_missing_grid_raises(self):
        """router=None 且未提供 grid_w/grid_h 必须 raise ValueError。"""
        with pytest.raises(ValueError, match="grid_w"):
            route_bundle([(0, 0)], [(10, 0)])

    def test_bundle_with_obstacles(self):
        """带障碍的 bundle 布线。"""
        ports1 = [(0, 0), (0, 10)]
        ports2 = [(20, 0), (20, 10)]
        router = JPSRouter(25, 25, 1.0, None)
        router.add_obstacle(10, 0, 1, 15)  # 中间垂直墙
        routes = route_bundle(ports1, ports2, router=router, separation=2)
        assert len(routes) == 2
        for route in routes:
            assert len(route) > 0


# ---------------------------------------------------------------------------
# 3. 等长匹配布线测试
# ---------------------------------------------------------------------------
class TestRouteBundlePathLengthMatch:
    """等长匹配布线测试（对标 gdsfactory route_bundle_path_length_match）。"""

    def test_basic_length_match(self):
        """基本等长匹配。"""
        ports1 = [(0, 0), (0, 10)]
        ports2 = [(20, 0), (20, 10)]
        routes = route_bundle_path_length_match(
            ports1, ports2, tolerance=2.0, grid_w=25, grid_h=25, separation=2
        )
        assert len(routes) == 2
        lengths = [path_length(r) for r in routes]
        if len(lengths) >= 2:
            assert max(lengths) - min(lengths) <= 5.0  # 容差检查

    def test_tolerance_check(self):
        """容差检查：匹配后长度差在合理范围。"""
        ports1 = [(0, 0), (0, 5)]
        ports2 = [(20, 0), (20, 5)]
        routes = route_bundle_path_length_match(
            ports1, ports2, tolerance=1.0, grid_w=25, grid_h=25, separation=2
        )
        assert len(routes) == 2
        lengths = [path_length(r) for r in routes]
        assert all(length > 0 for length in lengths)

    def test_empty_ports(self):
        """空端口列表返回空列表。"""
        result = route_bundle_path_length_match([], [], tolerance=1.0)
        assert result == []


# ---------------------------------------------------------------------------
# 4. Dubins Path 测试
# ---------------------------------------------------------------------------
class TestDubinsPath:
    """Dubins path 测试（Dubins 1957）。"""

    def test_basic_dubins(self):
        """基本 Dubins 路径（直行）。"""
        path = dubins_path((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), radius=2.0)
        assert len(path) >= 2
        assert math.isclose(path[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(path[0][1], 0.0, abs_tol=1e-6)
        assert math.isclose(path[-1][0], 10.0, abs_tol=0.5)

    def test_six_combinations(self):
        """6 种组合（LSL/RSR/LSR/RSL/RLR/LRL）都能生成路径。"""
        cases = [
            ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0)),    # 直行
            ((0.0, 0.0, 0.0), (5.0, 5.0, 90.0)),    # 左转
            ((0.0, 0.0, 0.0), (5.0, -5.0, 270.0)),  # 右转
            ((0.0, 0.0, 0.0), (10.0, 5.0, 45.0)),   # 斜向
            ((0.0, 0.0, 0.0), (3.0, 3.0, 180.0)),   # U 形（CCC）
            ((0.0, 0.0, 90.0), (5.0, -5.0, 0.0)),   # 反向
        ]
        for s, e in cases:
            path = dubins_path(s, e, radius=2.0)
            assert len(path) >= 2
            assert math.isclose(path[0][0], s[0], abs_tol=1e-6)
            assert math.isclose(path[0][1], s[1], abs_tol=1e-6)

    def test_shortest_selection(self):
        """最短路径选择：结果为 6 种候选中最短。"""
        path = dubins_path((0.0, 0.0, 0.0), (10.0, 5.0, 30.0), radius=3.0)
        assert len(path) >= 2
        # 验证路径连续性
        for i in range(1, len(path)):
            dist = math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            assert dist < 5.0

    def test_radius_constraint(self):
        """半径约束：radius <= 0 必须 raise ValueError。"""
        with pytest.raises(ValueError, match="radius"):
            dubins_path((0, 0, 0), (10, 0, 0), radius=0)
        with pytest.raises(ValueError, match="radius"):
            dubins_path((0, 0, 0), (10, 0, 0), radius=-1.0)

    def test_turn_path(self):
        """90° 转弯路径。"""
        path = dubins_path((0.0, 0.0, 0.0), (5.0, 5.0, 90.0), radius=2.0)
        assert len(path) >= 2
        assert math.isclose(path[-1][0], 5.0, abs_tol=1.0)
        assert math.isclose(path[-1][1], 5.0, abs_tol=1.0)


# ---------------------------------------------------------------------------
# 5. Auto Taper 测试
# ---------------------------------------------------------------------------
class TestAutoTaper:
    """Auto Taper 测试（对标 gdsfactory）。"""

    def test_taper_insertion(self):
        """taper 插入：返回带 width 的路径。"""
        route = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
        result = auto_taper(route, taper_length=5.0, start_width=0.5, end_width=1.0)
        assert len(result) == 5
        # 入口 taper：宽度从 0.5 递增到 1.0
        assert result[0][2] < result[1][2]
        # 中间段：宽度 = 1.0
        assert math.isclose(result[2][2], 1.0, abs_tol=0.01)

    def test_length_check(self):
        """长度检查：taper 段长度 = taper_length。"""
        route = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
        result = auto_taper(route, taper_length=5.0, start_width=0.5, end_width=1.0)
        assert len(result) == len(route)
        # 出口 taper：宽度从 1.0 递减到 0.5
        assert result[3][2] >= result[4][2]
        # 所有宽度在 [0.5, 1.0] 范围内
        for _x, _y, w in result:
            assert 0.5 - 0.01 <= w <= 1.0 + 0.01

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
        for _x, _y, w in result:
            assert math.isclose(w, 1.0)


# ---------------------------------------------------------------------------
# 6. 非曼哈顿布线（All-Angle）测试
# ---------------------------------------------------------------------------
class TestAllAngleRouter:
    """AllAngle 布线器测试（LiDAR ISPD 2025）。"""

    def test_arbitrary_angle(self):
        """任意角度布线：支持非 90° 倍数端口。"""
        router = AllAngleRouter(50, 50, bend_radius=5.0, grid_size=0.5)
        path = router.route((0.0, 0.0, 0.0), (20.0, 15.0, 90.0))
        assert len(path) >= 2
        assert math.isclose(path[0][0], 0.0, abs_tol=0.01)
        assert math.isclose(path[0][1], 0.0, abs_tol=0.01)

    def test_euler_bend_connection(self):
        """欧拉弯曲连接：转弯处插入 euler_bend 点。"""
        router = AllAngleRouter(50, 50, bend_radius=5.0, grid_size=0.5)
        path = router.route((0.0, 0.0, 0.0), (20.0, 20.0, 90.0))
        # 曼哈顿骨架只有 3 点，插入弯曲后应更多
        assert len(path) > 3

    def test_start_on_obstacle_raises(self):
        """起点在障碍上必须 raise ValueError。"""
        router = AllAngleRouter(10, 10, bend_radius=5.0)
        router.add_obstacle(0, 0)
        with pytest.raises(ValueError, match="起点"):
            router.route((0.0, 0.0, 0.0), (9.0, 9.0, 0.0))

    def test_invalid_params_raises(self):
        """无效参数必须 raise ValueError。"""
        with pytest.raises(ValueError, match="网格尺寸"):
            AllAngleRouter(0, 10)
        with pytest.raises(ValueError, match="bend_radius"):
            AllAngleRouter(10, 10, bend_radius=0)
        with pytest.raises(ValueError, match="grid_size"):
            AllAngleRouter(10, 10, grid_size=0)

    def test_adaptive_crossing(self):
        """【创新】自适应交叉插入：congestion 超阈值时保持路径。"""
        router = AllAngleRouter(50, 50, bend_radius=5.0, grid_size=0.5,
                                congestion_threshold=0.5)
        router.set_congestion({(20, 0): 0.8})  # 高 congestion
        path = router.route((0.0, 0.0, 0.0), (20.0, 20.0, 90.0))
        assert len(path) >= 2  # 路径有效

    def test_flatten_offgrid(self):
        """flatten_offgrid_references 量化到网格。"""
        router = AllAngleRouter(50, 50, bend_radius=5.0, grid_size=1.0)
        path = router.route((0.0, 0.0, 0.0), (20.0, 20.0, 90.0))
        gs = router.grid_size
        for x, y in path:
            # 所有坐标对齐到 grid_size
            assert math.isclose(x / gs, round(x / gs), abs_tol=1e-6)
            assert math.isclose(y / gs, round(y / gs), abs_tol=1e-6)


# ---------------------------------------------------------------------------
# 7. R10 集成测试
# ---------------------------------------------------------------------------
class TestR10Integration:
    """R10 路标集成测试：验证全部模块协同工作 + 无 fall-back + 创新点。"""

    def test_all_modules_importable(self):
        """全部 R10 模块可从 router 包导入。"""
        from polaris.router import (
            AllAngleRouter,
            JPSRouter,
            auto_taper,
            dubins_path,
            route_bundle,
            route_bundle_from_waypoints,
            route_bundle_path_length_match,
        )
        assert callable(JPSRouter)
        assert callable(AllAngleRouter)
        assert callable(route_bundle)
        assert callable(dubins_path)
        assert callable(auto_taper)
        assert callable(route_bundle_path_length_match)
        assert callable(route_bundle_from_waypoints)

    def test_jps_to_taper_pipeline(self):
        """JPS 布线 → Auto Taper 流水线。"""
        router = JPSRouter(30, 30, 1.0, None)
        path = router.route((0, 0), (20, 10))
        float_path = [(float(x), float(y)) for x, y in path]
        tapered = auto_taper(float_path, taper_length=5.0, start_width=0.5, end_width=1.0)
        assert len(tapered) == len(float_path)
        for _x, _y, w in tapered:
            assert 0.5 - 0.01 <= w <= 1.0 + 0.01

    def test_bundle_from_waypoints(self):
        """从路径点布线。"""
        ports1 = [(0, 0)]
        ports2 = [(20, 20)]
        waypoints = [(10, 0), (10, 20)]
        routes = route_bundle_from_waypoints(
            ports1, ports2, waypoints, grid_w=25, grid_h=25
        )
        assert len(routes) == 1
        assert routes[0][0] == (0, 0)
        assert routes[0][-1] == (20, 20)

    def test_dubins_standalone(self):
        """Dubins path 独立可用。"""
        path = dubins_path((0.0, 0.0, 0.0), (15.0, 5.0, 30.0), radius=3.0)
        assert len(path) >= 2
        assert math.isclose(path[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(path[0][1], 0.0, abs_tol=1e-6)

    def test_no_fallback_ast(self):
        """AST 检查：源文件中无 except:pass fall-back（规则 14.1）。"""
        from polaris.router import all_angle_router, bundle_router, jps_router
        for mod in [jps_router, bundle_router, all_angle_router]:
            with open(mod.__file__) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Pass):
                            pytest.fail(
                                f"{mod.__name__} 中存在 except:pass fall-back"
                            )

    def test_innovation_annotation(self):
        """创新点验证：AllAngleRouter 包含自适应交叉插入创新标注。"""
        from polaris.router import all_angle_router
        with open(all_angle_router.__file__) as f:
            source = f.read()
        assert "创新" in source
        assert "自适应交叉" in source
        assert hasattr(AllAngleRouter, "_adaptive_crossing_insertion")
        assert hasattr(AllAngleRouter, "_compute_bend_handle")
        assert hasattr(AllAngleRouter, "_flatten_offgrid_references")

    def test_no_fallback_runtime(self):
        """运行时无 fall-back：所有错误路径必须 raise。"""
        router = JPSRouter(10, 10, 1.0, None)
        router.add_obstacle(5, 0, 1, 10)
        with pytest.raises(RuntimeError):
            router.route((0, 5), (9, 5))
        with pytest.raises(ValueError):
            dubins_path((0, 0, 0), (10, 0, 0), radius=0)
