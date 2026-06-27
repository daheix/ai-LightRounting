"""R21 OptoDesigner 商业级自动布线模块测试。

测试覆盖:
1. TestCommercialRouterConfig: 配置验证(4 个)
2. TestFlexConnector: FlexConnector 弹性连接器(3 个)
3. TestSbendConnector: S 弯连接器(2 个)
4. TestManhattanConnector: 曼哈顿连接器(3 个)
5. TestBundleConnector: 线束连接器(3 个)
6. TestCurvyConnector: 任意曲线连接器(3 个)
7. TestDiscretizeCurve: 1nm 离散化精度(3 个)
8. TestRouteAll: 批量布线(2 个)
9. TestRipUpReroute: rip-up-reroute(2 个)
10. Test500DevicesSuccessRate: 500 器件成功率 ≥95%(1 个)

来源:
- OptoDesigner Advanced Connectors:
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- OptoDesigner Arbitrary Curves(1nm 离散化):
  https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html
- LiDAR ISPD'25:
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import math

import pytest

from polaris.router.commercial_router import (
    CommercialRouter,
    CommercialRouterConfig,
)


# ---------------------------------------------------------------------------
# 1. TestCommercialRouterConfig — 配置验证
# ---------------------------------------------------------------------------
class TestCommercialRouterConfig:
    """商业级布线配置校验(禁止 fall-back 静默修正)。"""

    def test_default_config(self):
        """默认配置应满足商业级指标(1nm 离散化 + 10μm 弯曲半径)。"""
        cfg = CommercialRouterConfig()
        assert cfg.discretization_resolution == pytest.approx(1e-3)  # 1nm
        assert cfg.bend_radius == pytest.approx(10.0)
        assert cfg.grid_size == pytest.approx(1.0)
        assert cfg.n_directions == 16
        assert cfg.min_success_rate == pytest.approx(0.95)

    def test_invalid_resolution(self):
        """离散化精度非正应抛出 ValueError。"""
        with pytest.raises(ValueError):
            CommercialRouterConfig(discretization_resolution=0.0)
        with pytest.raises(ValueError):
            CommercialRouterConfig(discretization_resolution=-1e-3)

    def test_invalid_bend_radius_and_grid(self):
        """弯曲半径/网格尺寸非正应抛出 ValueError。"""
        with pytest.raises(ValueError):
            CommercialRouterConfig(bend_radius=0.0)
        with pytest.raises(ValueError):
            CommercialRouterConfig(grid_size=-1.0)

    def test_invalid_directions_and_success_rate(self):
        """方向数非法/成功率越界应抛出 ValueError。"""
        with pytest.raises(ValueError):
            CommercialRouterConfig(n_directions=7)
        with pytest.raises(ValueError):
            CommercialRouterConfig(min_success_rate=0.0)
        with pytest.raises(ValueError):
            CommercialRouterConfig(min_success_rate=1.5)
        with pytest.raises(ValueError):
            CommercialRouterConfig(max_ripup_iterations=0)


# ---------------------------------------------------------------------------
# 2. TestFlexConnector — FlexConnector 弹性连接器
# ---------------------------------------------------------------------------
class TestFlexConnector:
    """FlexConnector 弹性连接器测试(对标 OptoDesigner elastic connector)。"""

    def test_simple_route(self):
        """无障碍直线布线应返回有效路径。"""
        router = CommercialRouter()
        path = router.flex_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 0.0}
        )
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 0.0)

    def test_route_with_obstacles(self):
        """有障碍物时应绕行(路径不经过障碍区域)。"""
        router = CommercialRouter()
        obstacles = [(3.0, -2.0, 3.0, 4.0)]  # 阻塞 (3,−2)~(6,2)
        path = router.flex_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 0.0}, obstacles
        )
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 0.0)
        for px, py in path:
            assert not (3.0 <= px <= 6.0 and -2.0 <= py <= 2.0)

    def test_invalid_port_raises(self):
        """端口缺失坐标应抛出 ValueError(禁止 fall-back)。"""
        router = CommercialRouter()
        with pytest.raises(ValueError):
            router.flex_connector({"x": 0.0}, {"x": 10.0, "y": 0.0})
        with pytest.raises(ValueError):
            router.flex_connector({"x": 0.0, "y": 0.0}, {"y": 0.0})


# ---------------------------------------------------------------------------
# 3. TestSbendConnector — S 弯连接器
# ---------------------------------------------------------------------------
class TestSbendConnector:
    """S 弯连接器测试(三次贝塞尔曲线)。"""

    def test_sbend_endpoints(self):
        """S 弯应连接起终点。"""
        router = CommercialRouter()
        path = router.sbend_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 5.0}
        )
        assert len(path) >= 2
        assert path[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert path[-1] == pytest.approx((10.0, 5.0), abs=1e-9)

    def test_sbend_smooth(self):
        """S 弯应为平滑曲线(相邻点弦长 ≤ 1nm + 容差)。"""
        router = CommercialRouter()
        path = router.sbend_connector(
            {"x": 0.0, "y": 0.0}, {"x": 5.0, "y": 3.0}
        )
        res = router.config.discretization_resolution
        for i in range(len(path) - 1):
            d = math.hypot(path[i + 1][0] - path[i][0],
                           path[i + 1][1] - path[i][1])
            assert d <= res + 1e-9, f"相邻点距离 {d} > {res}"


# ---------------------------------------------------------------------------
# 4. TestManhattanConnector — 曼哈顿连接器
# ---------------------------------------------------------------------------
class TestManhattanConnector:
    """曼哈顿连接器测试(L 形/Z 形)。"""

    def test_l_shape_no_obstacle(self):
        """无障碍时应返回 L 形 Manhattan 路径。"""
        router = CommercialRouter()
        path = router.manhattan_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 5.0}
        )
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 5.0)
        # L 形应为 3 点:起点/拐点/终点
        assert len(path) == 3

    def test_z_shape_with_obstacle(self):
        """L 形被阻塞时应返回 Z 形路径。"""
        router = CommercialRouter()
        # 障碍物阻塞 L 形拐点 (10, 0) 附近
        obstacles = [(8.0, -1.0, 4.0, 3.0)]
        path = router.manhattan_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 5.0}, obstacles
        )
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 5.0)

    def test_fallback_to_flex(self):
        """L 形和 Z 形都被阻塞时回退到 flex(A* 避障,合法多策略)。"""
        router = CommercialRouter()
        # 大障碍物阻塞所有 Manhattan 形式
        obstacles = [(-5.0, -5.0, 30.0, 5.0), (-5.0, 0.0, 5.0, 20.0)]
        path = router.manhattan_connector(
            {"x": 0.0, "y": 0.0}, {"x": 20.0, "y": 15.0}, obstacles
        )
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (20.0, 15.0)


# ---------------------------------------------------------------------------
# 5. TestBundleConnector — 线束连接器
# ---------------------------------------------------------------------------
class TestBundleConnector:
    """线束连接器测试(多端口并行,sort_ports 避免交叉)。"""

    def test_bundle_basic(self):
        """3 对端口线束应返回 3 条路径。"""
        router = CommercialRouter()
        ports_in = [{"x": 0.0, "y": float(i)} for i in range(3)]
        ports_out = [{"x": 10.0, "y": float(i)} for i in range(3)]
        paths = router.bundle_connector(ports_in, ports_out)
        assert len(paths) == 3
        for path in paths:
            assert len(path) >= 2

    def test_bundle_sort_ports(self):
        """乱序输入应按 y 排序配对(避免线束内交叉)。"""
        router = CommercialRouter()
        ports_in = [{"x": 0.0, "y": 2.0}, {"x": 0.0, "y": 0.0},
                    {"x": 0.0, "y": 1.0}]
        ports_out = [{"x": 10.0, "y": 0.0}, {"x": 10.0, "y": 2.0},
                     {"x": 10.0, "y": 1.0}]
        paths = router.bundle_connector(ports_in, ports_out)
        assert len(paths) == 3
        # 排序后最低 y 配最低 y:(0,0)->(10,0)
        assert paths[0][0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert paths[0][-1] == pytest.approx((10.0, 0.0), abs=1e-9)

    def test_bundle_mismatch_raises(self):
        """端口数不匹配应抛出 ValueError(禁止 fall-back)。"""
        router = CommercialRouter()
        with pytest.raises(ValueError):
            router.bundle_connector(
                [{"x": 0.0, "y": 0.0}],
                [{"x": 10.0, "y": 0.0}, {"x": 10.0, "y": 1.0}],
            )
        with pytest.raises(ValueError):
            router.bundle_connector([], [])


# ---------------------------------------------------------------------------
# 6. TestCurvyConnector — 任意曲线连接器
# ---------------------------------------------------------------------------
class TestCurvyConnector:
    """任意曲线连接器测试(Euler 螺线/贝塞尔)。"""

    def test_euler_curve(self):
        """Euler 螺线应连接起终点。"""
        router = CommercialRouter()
        path = router.curvy_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 5.0}, "euler"
        )
        assert len(path) >= 2
        assert path[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert path[-1] == pytest.approx((10.0, 5.0), abs=1e-9)

    def test_bezier_curve(self):
        """贝塞尔曲线应连接起终点。"""
        router = CommercialRouter()
        path = router.curvy_connector(
            {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 5.0}, "bezier"
        )
        assert len(path) >= 2
        assert path[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert path[-1] == pytest.approx((10.0, 5.0), abs=1e-9)

    def test_invalid_curve_type(self):
        """非法曲线类型应抛出 ValueError。"""
        router = CommercialRouter()
        with pytest.raises(ValueError):
            router.curvy_connector(
                {"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 0.0}, "spline"
            )


# ---------------------------------------------------------------------------
# 7. TestDiscretizeCurve — 1nm 离散化精度
# ---------------------------------------------------------------------------
class TestDiscretizeCurve:
    """1nm 自适应曲线离散化精度测试。"""

    def test_resolution_1nm(self):
        """默认 1nm 离散化:相邻点弦长 ≤ 1nm。"""
        router = CommercialRouter()

        def line(t: float) -> tuple[float, float]:
            return (5.0 * t, 3.0 * t)  # 5μm 直线

        pts = router.discretize_curve(line, (0.0, 1.0))
        res = router.config.discretization_resolution
        for i in range(len(pts) - 1):
            d = math.hypot(pts[i + 1][0] - pts[i][0],
                           pts[i + 1][1] - pts[i][1])
            assert d <= res + 1e-9, f"相邻点距离 {d} > {res}"

    def test_custom_resolution(self):
        """自定义 100nm 离散化:相邻点弦长 ≤ 100nm。"""
        router = CommercialRouter()

        def arc(t: float) -> tuple[float, float]:
            return (5.0 * math.cos(t * math.pi / 2),
                    5.0 * math.sin(t * math.pi / 2))

        pts = router.discretize_curve(arc, (0.0, 1.0), resolution=0.1)
        for i in range(len(pts) - 1):
            d = math.hypot(pts[i + 1][0] - pts[i][0],
                           pts[i + 1][1] - pts[i][1])
            assert d <= 0.1 + 1e-9, f"相邻点距离 {d} > 0.1"

    def test_endpoints_preserved(self):
        """离散化应保留起终点。"""
        router = CommercialRouter()

        def curve(t: float) -> tuple[float, float]:
            return (10.0 * t, 5.0 * t * t)

        pts = router.discretize_curve(curve, (0.0, 1.0), resolution=0.5)
        assert pts[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert pts[-1] == pytest.approx((10.0, 5.0), abs=1e-9)


# ---------------------------------------------------------------------------
# 8. TestRouteAll — 批量布线
# ---------------------------------------------------------------------------
class TestRouteAll:
    """批量布线测试(500 器件成功率 ≥95%)。"""

    def test_route_all_basic(self):
        """10 条连接批量布线应全部成功。"""
        router = CommercialRouter()
        connections = [
            {
                "name": f"net_{i}",
                "port_in": {"x": float(i) * 10.0, "y": 0.0},
                "port_out": {"x": float(i) * 10.0 + 5.0, "y": 5.0},
            }
            for i in range(10)
        ]
        results = router.route_all([], connections)
        assert len(results) == 10
        for name, path in results.items():
            assert len(path) >= 2, f"网 {name} 路径点数不足"

    def test_route_all_empty(self):
        """空连接列表应返回空字典(非 fall-back)。"""
        router = CommercialRouter()
        results = router.route_all([], [])
        assert results == {}


# ---------------------------------------------------------------------------
# 9. TestRipUpReroute — rip-up-reroute
# ---------------------------------------------------------------------------
class TestRipUpReroute:
    """rip-up-reroute 冲突解决测试(LiDAR ISPD'25 §3.4)。"""

    def test_reroute_success(self):
        """无障碍时重布应成功,路径连接起终点。"""
        router = CommercialRouter()
        failed = [
            {
                "name": "reroute_1",
                "port_in": {"x": 0.0, "y": 0.0},
                "port_out": {"x": 10.0, "y": 0.0},
            }
        ]
        results = router.rip_up_reroute(failed, [])
        assert "reroute_1" in results
        path = results["reroute_1"]
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 0.0)

    def test_reroute_multiple(self):
        """多条失败连接重布应分别返回路径。"""
        router = CommercialRouter()
        failed = [
            {
                "name": f"r_{i}",
                "port_in": {"x": 0.0, "y": float(i) * 10.0},
                "port_out": {"x": 10.0, "y": float(i) * 10.0},
            }
            for i in range(3)
        ]
        results = router.rip_up_reroute(failed, [])
        assert len(results) == 3
        for path in results.values():
            assert len(path) >= 2


# ---------------------------------------------------------------------------
# 10. Test500DevicesSuccessRate — 500 器件成功率 ≥95%
# ---------------------------------------------------------------------------
class Test500DevicesSuccessRate:
    """500 器件布线成功率 ≥95% 测试(商业级指标)。"""

    def test_500_devices_success_rate(self):
        """500 个器件布线成功率应 ≥95%。"""
        # 用 grid_size=2.0 加速 A*,短连接降低单次布线开销
        config = CommercialRouterConfig(grid_size=2.0, n_directions=8)
        router = CommercialRouter(config)
        connections = []
        for i in range(500):
            x = float(i % 50) * 5.0
            y = float(i // 50) * 5.0
            connections.append({
                "name": f"net_{i}",
                "port_in": {"x": x, "y": y},
                "port_out": {"x": x + 3.0, "y": y + 3.0},
            })
        results = router.route_all([], connections)
        success_rate = len(results) / 500
        assert success_rate >= 0.95, (
            f"500 器件布线成功率 {success_rate:.2%} < 95%"
        )
        # 验证所有成功路径连接正确起终点
        for conn in connections:
            name = conn["name"]
            if name in results:
                path = results[name]
                assert len(path) >= 2, f"网 {name} 路径点数不足"
                assert path[0] == (conn["port_in"]["x"], conn["port_in"]["y"])
                assert path[-1] == (conn["port_out"]["x"], conn["port_out"]["y"])
