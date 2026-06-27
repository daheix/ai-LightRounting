"""R10 gdsfactory 风格布线策略单元测试。

覆盖 GdsfactoryStyleRouter 的 5 种布线策略 + 配置校验 + A* 对比 +
无交叉验证 + 弯曲半径合规 + 无 fall-back（R03）AST 检查。

测试原则（规则 14.1）：禁止 fall-back，所有错误路径必须 raise。
测试用真实布线场景，禁止假数据。
"""

from __future__ import annotations

import ast
import math

import pytest

from polaris.router.gdsfactory_style import (
    GdsfactoryStyleRouter,
    Port,
    RouteConfig,
)
from polaris.router.path_geometry import count_crossings, path_length
from polaris.router.waveguide_router import GridRouter, RouterConstraints


# ---------------------------------------------------------------------------
# 1. 配置校验
# ---------------------------------------------------------------------------
def test_config_validation():
    """配置合法性校验：非法参数必须 raise ValueError（禁止 fall-back）。"""
    with pytest.raises(ValueError, match="bend_radius"):
        RouteConfig(bend_radius=-1.0).validate()
    with pytest.raises(ValueError, match="separation"):
        RouteConfig(separation=0.0).validate()
    with pytest.raises(ValueError, match="fiber_array_pitch"):
        RouteConfig(fiber_array_pitch=0.0).validate()
    with pytest.raises(ValueError, match="cpw_gap"):
        RouteConfig(cpw_gap=-5.0).validate()
    with pytest.raises(ValueError, match="n_points_bend"):
        RouteConfig(n_points_bend=1).validate()
    with pytest.raises(ValueError, match="grid_size"):
        RouteConfig(grid_size=0.0).validate()
    # 构造器同样触发校验
    with pytest.raises(ValueError):
        GdsfactoryStyleRouter(RouteConfig(bend_radius=0.0))
    # 合法配置不抛异常
    cfg = RouteConfig(bend_radius=5.0, separation=2.0, cpw_gap=20.0)
    cfg.validate()


# ---------------------------------------------------------------------------
# 2. 光纤阵列布线
# ---------------------------------------------------------------------------
def test_route_fiber_array():
    """光纤阵列布线：芯片端口 50μm pitch 对齐光纤阵列 127μm pitch。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    ports_in = [Port(0, 0, 0), Port(0, 50, 0), Port(0, 100, 0)]
    ports_out = [Port(500, 0, 180), Port(500, 127, 180), Port(500, 254, 180)]
    routes = router.route_fiber_array(ports_in, ports_out)
    assert len(routes) == 3
    for r in routes:
        assert len(r) > 0
        assert math.isclose(r[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(r[-1][0], 500.0, abs_tol=1e-6)
    # 端口数不匹配必须 raise
    with pytest.raises(ValueError, match="端口数不匹配"):
        router.route_fiber_array(ports_in, ports_out[:2])


# ---------------------------------------------------------------------------
# 3. bundle 布线
# ---------------------------------------------------------------------------
def test_route_bundle():
    """bundle 布线：多线束并行 river routing，端口按 y 排序配对。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    ports_in = [Port(0, 0, 0), Port(0, 20, 0), Port(0, 40, 0)]
    ports_out = [Port(100, 0, 180), Port(100, 20, 180), Port(100, 40, 180)]
    routes = router.route_bundle(ports_in, ports_out)
    assert len(routes) == 3
    for r in routes:
        assert len(r) >= 2
        assert math.isclose(r[0][0], 0.0, abs_tol=1e-6)
        assert math.isclose(r[-1][0], 100.0, abs_tol=1e-6)
    # 端口数不匹配必须 raise
    with pytest.raises(ValueError, match="端口数不匹配"):
        router.route_bundle(ports_in, ports_out[:1])


# ---------------------------------------------------------------------------
# 4. S 弯布线
# ---------------------------------------------------------------------------
def test_route_sbend():
    """S 弯布线：三次贝塞尔曲线连接错位端口，起终点精确对齐。"""
    router = GdsfactoryStyleRouter(RouteConfig(n_points_bend=30))
    route = router.route_sbend(Port(0, 0, 0), Port(20, 5, 180))
    assert len(route) >= 2
    assert math.isclose(route[0][0], 0.0, abs_tol=1e-6)
    assert math.isclose(route[0][1], 0.0, abs_tol=1e-6)
    assert math.isclose(route[-1][0], 20.0, abs_tol=1e-6)
    assert math.isclose(route[-1][1], 5.0, abs_tol=1e-6)
    # S 弯线长应介于直线和曼哈顿距离之间
    straight = math.hypot(20, 5)
    manhattan = 20 + 5
    length = path_length(route)
    assert straight - 0.01 <= length <= manhattan + 0.01


# ---------------------------------------------------------------------------
# 5. 曼哈顿布线
# ---------------------------------------------------------------------------
def test_route_manhattan():
    """曼哈顿布线：Z 弯折线，线长 = 曼哈顿距离。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    route = router.route_manhattan(Port(0, 0, 0), Port(20, 10, 180))
    assert route[0] == (0, 0)
    assert route[-1] == (20, 10)
    # Z 弯线长 = 曼哈顿距离 = 30
    assert math.isclose(path_length(route), 30.0, abs_tol=1e-6)
    # 同轴直行退化为直线
    direct = router.route_manhattan(Port(0, 0, 0), Port(30, 0, 180))
    assert math.isclose(path_length(direct), 30.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# 6. 共面波导布线
# ---------------------------------------------------------------------------
def test_route_cpw():
    """CPW 布线：每个信号对生成 G-S-G 三线组，间距 = cpw_gap。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0, cpw_gap=20.0))
    ports_in = [Port(0, 0, 0)]
    ports_out = [Port(100, 0, 180)]
    routes = router.route_cpw(ports_in, ports_out)
    assert len(routes) == 3  # G-S-G 三线组
    # 三条线起点 y 分别为 -20, 0, +20
    ys = sorted(r[0][1] for r in routes)
    assert math.isclose(ys[0], -20.0, abs_tol=1e-6)
    assert math.isclose(ys[1], 0.0, abs_tol=1e-6)
    assert math.isclose(ys[2], 20.0, abs_tol=1e-6)
    # 端口数不匹配必须 raise
    with pytest.raises(ValueError, match="端口数不匹配"):
        router.route_cpw(ports_in, ports_out + [Port(100, 50, 180)])


def _manhattanize(path):
    """将 JPS 重建产生的对角线段还原为曼哈顿 L 形折线。

    GridRouter 的 JPS-Bend 重建在转弯处只保留拐角点，产生对角线段
    （欧氏长 < 真实网格步长）。本函数将对角段拆为 L 形（先 x 后 y），
    恢复路径的真实曼哈顿长度，保证与 gdsfactory 曼哈顿路由公平对比。
    """
    if len(path) < 2:
        return list(path)
    result = [path[0]]
    for i in range(1, len(path)):
        px, py = path[i - 1]
        cx, cy = path[i]
        if math.isclose(px, cx, abs_tol=1e-9) or math.isclose(py, cy, abs_tol=1e-9):
            result.append(path[i])  # 已轴对齐
        else:
            result.append((cx, py))  # L 形拐角：先 x 后 y
            result.append((cx, cy))
    return result


# ---------------------------------------------------------------------------
# 7. 与 PoLaRIS A* 对比（线长差距 < 10%）
# ---------------------------------------------------------------------------
def test_compare_with_astar():
    """gdsfactory 曼哈顿策略 vs PoLaRIS A* 线长对比（差距 < 10%）。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    gf_route = router.route_manhattan(Port(0, 0, 0), Port(20, 10, 180))
    # PoLaRIS A* 网格布线（无弯曲约束，允许任意转弯）
    grid = GridRouter(25, 25, 1.0, RouterConstraints(min_bend_radius_um=0.0))
    gpath = grid.route((0, 0), (20, 10))
    assert gpath is not None
    # 将 JPS 对角重建还原为忠实曼哈顿折线（恢复真实网格步长）
    astar_route = _manhattanize([(float(x), float(y)) for x, y in gpath])
    result = router.compare_with_astar(gf_route, astar_route)
    assert result["within_10_percent"] is True
    assert result["diff_ratio"] < 0.10
    # A* 路径为 0 必须 raise（禁止 fall-back）
    with pytest.raises(ValueError, match="A\\* 路径长度为 0"):
        router.compare_with_astar(gf_route, [(0.0, 0.0)])


# ---------------------------------------------------------------------------
# 8. bundle 布线无交叉
# ---------------------------------------------------------------------------
def test_no_crossing():
    """bundle 布线无交叉：river routing 保证端口顺序一致无交叉。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    # 错位端口，y 范围不重叠
    ports_in = [Port(0, 0, 0), Port(0, 30, 0)]
    ports_out = [Port(100, 10, 180), Port(100, 40, 180)]
    routes = router.route_bundle(ports_in, ports_out)
    assert len(routes) == 2
    # 显式验证无交叉
    assert count_crossings(routes[0], routes[1]) == 0
    # 交叉场景必须 raise RuntimeError（禁止 fall-back）


# ---------------------------------------------------------------------------
# 9. 弯曲半径合规
# ---------------------------------------------------------------------------
def test_bend_radius():
    """弯曲半径合规：转弯处入段/出段 >= bend_radius。"""
    # 合规场景：段长 10 >= bend_radius 5
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    route = router.route_manhattan(Port(0, 0, 0), Port(20, 10, 180))
    assert router.validate_bend_radius(route) is True
    # 违规场景：bend_radius=15 > 段长 10，必须 raise
    strict_router = GdsfactoryStyleRouter(RouteConfig(bend_radius=15.0))
    with pytest.raises(ValueError, match="转弯段长度不足"):
        strict_router.validate_bend_radius(route)
    # 短路径（< 3 点）直接通过
    assert router.validate_bend_radius([(0.0, 0.0), (1.0, 0.0)]) is True


# ---------------------------------------------------------------------------
# 10. 端口归一化 + 无 fall-back AST 检查（R03）
# ---------------------------------------------------------------------------
def test_port_normalization():
    """端口归一化：支持 Port/dict/tuple，非法类型 raise。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    # dict 端口
    r1 = router.route_sbend({"x": 0, "y": 0}, {"x": 10, "y": 5})
    assert math.isclose(r1[0][0], 0.0, abs_tol=1e-6)
    # tuple 端口
    r2 = router.route_sbend((0, 0), (10, 5))
    assert math.isclose(r2[-1][0], 10.0, abs_tol=1e-6)
    # dict 缺键必须 raise
    with pytest.raises(ValueError, match="缺少必需键"):
        router.route_sbend({"x": 0}, (10, 5))
    # 非法类型必须 raise
    with pytest.raises(TypeError, match="不支持的端口类型"):
        router.route_sbend(123, (10, 5))
    # 空端口列表必须 raise
    with pytest.raises(ValueError, match="端口列表为空"):
        router.route_bundle([], [])


def test_no_fallback_ast():
    """AST 检查：源文件中无 except:pass fall-back（规则 14.1）。"""
    from polaris.router import gdsfactory_style

    with open(gdsfactory_style.__file__) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for child in ast.walk(node):
                if isinstance(child, ast.Pass):
                    pytest.fail(
                        f"{gdsfactory_style.__name__} 中存在 except:pass fall-back"
                    )


def test_five_strategies_complete():
    """5 种布线策略齐全（对标 gdsfactory routing API）。"""
    router = GdsfactoryStyleRouter(RouteConfig(bend_radius=5.0))
    strategies = [
        "route_fiber_array",
        "route_bundle",
        "route_sbend",
        "route_manhattan",
        "route_cpw",
    ]
    for name in strategies:
        assert hasattr(router, name), f"缺少布线策略: {name}"
    # 文献 URL 数量 >= 5（R02 学术诚信）
    import inspect

    src = inspect.getsource(gdsfactory_style_module())
    url_count = src.count("https://")
    assert url_count >= 5, f"文献 URL 数量 {url_count} < 5"


def gdsfactory_style_module():
    """返回 gdsfactory_style 模块对象（供 inspect）。"""
    from polaris.router import gdsfactory_style

    return gdsfactory_style
