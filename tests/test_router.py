"""波导约束布线器单元测试（Task 11）。

覆盖 A* 单条布线、弯曲半径检查（满足/不满足）、间距检查、S 弯生成、
等长处理、Route 数据类字段、多条连接布线不冲突。
"""

from __future__ import annotations

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist, NetlistConnection, NetlistInstance
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.router import Route, WaveguideRouter


# ---------------------------------------------------------------------------
# 辅助构造
# ---------------------------------------------------------------------------
def _make_device(
    dev_id: str, ports: list[Port], bbox: BoundingBox
) -> Device:
    """构造测试用 Device（SOI 平台）。"""
    return Device(
        device_id=dev_id,
        platform="SOI",
        category="passive",
        name="test_dev",
        ports=ports,
        bbox=bbox,
    )


def _straight_device(dev_id: str, length: float = 10.0) -> Device:
    """构造一个含 in/out 端口的直波导状测试器件（包围盒 0..length, 0..10）。"""
    ports = [
        Port(name="in", x=0.0, y=5.0, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
        Port(name="out", x=length, y=5.0, direction=Direction.EAST,
             waveguide_type="strip", width=0.5),
    ]
    bbox = BoundingBox(xmin=0.0, ymin=0.0, xmax=length, ymax=10.0)
    return _make_device(dev_id, ports, bbox)


# ---------------------------------------------------------------------------
# Route 数据类字段
# ---------------------------------------------------------------------------
def test_route_dataclass_fields() -> None:
    """Route 应正确创建并暴露所有字段。"""
    r = Route(
        net_id="n0",
        path=[(0.0, 0.0), (10.0, 0.0)],
        length=10.0,
        num_bends=0,
        num_crossings=0,
        loss_db=0.0,
        is_equalized=False,
    )
    assert r.net_id == "n0"
    assert r.path == [(0.0, 0.0), (10.0, 0.0)]
    assert r.length == 10.0
    assert r.num_bends == 0
    assert r.num_crossings == 0
    assert r.loss_db == 0.0
    assert r.is_equalized is False


def test_route_default_is_equalized_false() -> None:
    """Route.is_equalized 默认应为 False。"""
    r = Route(
        net_id="n1", path=[(0.0, 0.0)], length=0.0,
        num_bends=0, num_crossings=0, loss_db=0.0,
    )
    assert r.is_equalized is False


# ---------------------------------------------------------------------------
# A* 单条布线
# ---------------------------------------------------------------------------
def test_astar_finds_straight_path() -> None:
    """A* 单条布线应能找到无障碍直线路径。"""
    router = WaveguideRouter(grid_size=1.0, min_bend_radius=5.0)
    route = router.route_single((0.0, 0.0), (10.0, 0.0), obstacles=set())
    assert len(route.path) >= 2
    assert route.path[0] == (0.0, 0.0)
    assert route.path[-1] == (10.0, 0.0)
    # 直线路径长度应接近 10
    assert abs(route.length - 10.0) < 1e-6
    assert route.num_bends == 0


def test_astar_routes_around_obstacle() -> None:
    """A* 应绕开障碍物找到路径（路径长度大于直线距离）。"""
    router = WaveguideRouter(grid_size=1.0, min_bend_radius=5.0)
    # 在直线路径中央放置障碍点
    obstacles = {(5, 0), (5, 1)}
    route = router.route_single((0.0, 0.0), (10.0, 0.0), obstacles=obstacles)
    assert len(route.path) >= 2
    assert route.path[0] == (0.0, 0.0)
    assert route.path[-1] == (10.0, 0.0)
    # 绕路后长度应大于直线距离 10
    assert route.length > 10.0
    # 路径不应穿过障碍网格点
    grid_pts = set(router._path_grid_points(route.path))
    assert (5, 0) not in grid_pts


def test_astar_returns_route_object() -> None:
    """route_single 应返回 Route 实例且 net_id 正确。"""
    router = WaveguideRouter()
    route = router.route_single((0.0, 0.0), (5.0, 5.0), obstacles=set(), net_id="net42")
    assert isinstance(route, Route)
    assert route.net_id == "net42"


# ---------------------------------------------------------------------------
# 弯曲半径检查
# ---------------------------------------------------------------------------
def test_check_bend_radius_satisfied() -> None:
    """长臂直角弯曲应满足最小弯曲半径。"""
    router = WaveguideRouter(min_bend_radius=5.0)
    # (0,0)->(10,0)->(10,10)：外接圆半径 = 5*sqrt(2) ≈ 7.07 >= 5
    path = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    assert router.check_bend_radius(path, min_radius=5.0) is True


def test_check_bend_radius_violated() -> None:
    """短臂直角弯曲应不满足最小弯曲半径。"""
    router = WaveguideRouter(min_bend_radius=5.0)
    # (0,0)->(2,0)->(2,2)：外接圆半径 = sqrt(2) ≈ 1.41 < 5
    path = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]
    assert router.check_bend_radius(path, min_radius=5.0) is False


def test_check_bend_radius_collinear_ok() -> None:
    """共线路径（无弯曲）应满足任意最小弯曲半径。"""
    router = WaveguideRouter()
    path = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
    assert router.check_bend_radius(path, min_radius=5.0) is True


# ---------------------------------------------------------------------------
# 间距检查
# ---------------------------------------------------------------------------
def test_check_spacing_satisfied() -> None:
    """平行波导间距足够时应通过间距检查。"""
    router = WaveguideRouter(min_spacing=1.0)
    path = [(0.0, 0.0), (10.0, 0.0)]
    other = [[(0.0, 2.0), (10.0, 2.0)]]
    assert router.check_spacing(path, other, min_spacing=1.0) is True


def test_check_spacing_violated() -> None:
    """平行波导间距不足时应不通过间距检查。"""
    router = WaveguideRouter(min_spacing=1.0)
    path = [(0.0, 0.0), (10.0, 0.0)]
    other = [[(0.0, 0.3), (10.0, 0.3)]]
    assert router.check_spacing(path, other, min_spacing=1.0) is False


# ---------------------------------------------------------------------------
# S 弯生成
# ---------------------------------------------------------------------------
def test_s_bend_satisfies_min_bend_radius() -> None:
    """S 弯生成应满足最小弯曲半径。"""
    router = WaveguideRouter(grid_size=0.5, min_bend_radius=5.0)
    pts = router.generate_s_bend((0.0, 0.0), (20.0, 5.0), min_radius=5.0)
    assert len(pts) >= 3
    assert pts[0] == (0.0, 0.0)
    # 末端 y 应对齐到目标偏移
    assert abs(pts[-1][1] - 5.0) < 1e-6
    # 检查弯曲半径满足
    assert router.check_bend_radius(pts, min_radius=5.0) is True


def test_s_bend_collinear_returns_straight() -> None:
    """无横向偏移时 S 弯应退化为直线。"""
    router = WaveguideRouter()
    pts = router.generate_s_bend((0.0, 0.0), (10.0, 0.0), min_radius=5.0)
    assert pts == [(0.0, 0.0), (10.0, 0.0)]


def test_s_bend_vertical() -> None:
    """纵向 S 弯（主方向为 y）应生成平滑曲线且满足弯曲半径。"""
    router = WaveguideRouter(grid_size=0.5, min_bend_radius=5.0)
    pts = router.generate_s_bend((0.0, 0.0), (5.0, 20.0), min_radius=5.0)
    assert len(pts) >= 3
    assert pts[0] == (0.0, 0.0)
    assert router.check_bend_radius(pts, min_radius=5.0) is True


# ---------------------------------------------------------------------------
# 等长处理
# ---------------------------------------------------------------------------
def test_equalize_length_matches_target() -> None:
    """等长处理后两条路径长度差应小于阈值。"""
    router = WaveguideRouter()
    short = Route(
        net_id="a", path=[(0.0, 0.0), (10.0, 0.0)], length=10.0,
        num_bends=0, num_crossings=0, loss_db=0.0,
    )
    long = Route(
        net_id="b", path=[(0.0, 0.0), (20.0, 0.0)], length=20.0,
        num_bends=0, num_crossings=0, loss_db=0.0,
    )
    target = max(short.length, long.length)
    result = router.equalize_length([short, long], target_length=target)
    assert len(result) == 2
    # 短路径被延长，长路径不变
    assert result[0].is_equalized is True
    assert result[1].is_equalized is False
    # 长度差应小于阈值
    diff = abs(result[0].length - result[1].length)
    assert diff < 1.0, f"等长后长度差 {diff} 过大"


def test_equalize_length_no_change_when_already_long() -> None:
    """已达目标长度的路径不应被延长。"""
    router = WaveguideRouter()
    r = Route(
        net_id="a", path=[(0.0, 0.0), (30.0, 0.0)], length=30.0,
        num_bends=0, num_crossings=0, loss_db=0.0,
    )
    result = router.equalize_length([r], target_length=20.0)
    assert result[0].length == 30.0
    assert result[0].is_equalized is False


# ---------------------------------------------------------------------------
# 多条连接布线不冲突
# ---------------------------------------------------------------------------
def _build_two_connection_netlist() -> tuple[Netlist, dict[str, Placement]]:
    """构建两条互不干扰连接的网表与放置（分处不同 y 区域）。"""
    dev1 = _straight_device("d1", length=10.0)
    dev2 = _straight_device("d2", length=10.0)
    dev3 = _straight_device("d3", length=10.0)
    dev4 = _straight_device("d4", length=10.0)
    placements = {
        "d1": Placement(instance_id="d1", device=dev1, x=0.0, y=0.0, rotation=0),
        "d2": Placement(instance_id="d2", device=dev2, x=50.0, y=0.0, rotation=0),
        "d3": Placement(instance_id="d3", device=dev3, x=0.0, y=40.0, rotation=0),
        "d4": Placement(instance_id="d4", device=dev4, x=50.0, y=40.0, rotation=0),
    }
    net = Netlist(
        instances=[
            NetlistInstance(instance_id="d1", component="test_dev"),
            NetlistInstance(instance_id="d2", component="test_dev"),
            NetlistInstance(instance_id="d3", component="test_dev"),
            NetlistInstance(instance_id="d4", component="test_dev"),
        ],
        connections=[
            NetlistConnection(src_instance="d1", src_port="out",
                              dst_instance="d2", dst_port="in"),
            NetlistConnection(src_instance="d3", src_port="out",
                              dst_instance="d4", dst_port="in"),
        ],
    )
    return net, placements


def test_route_multiple_connections_no_conflict() -> None:
    """多条连接布线应全部成功且路径有效。"""
    net, placements = _build_two_connection_netlist()
    router = WaveguideRouter(grid_size=1.0, min_bend_radius=5.0, min_spacing=1.0)
    routes = router.route(net, placements)
    assert len(routes) == 2
    for r in routes:
        assert isinstance(r, Route)
        assert len(r.path) >= 2
        assert r.length > 0.0
    # 两条路径分处不同 y 区域，应满足间距约束
    assert router.check_spacing(
        routes[0].path, [routes[1].path], min_spacing=1.0
    ) is True


def test_route_single_connection_endpoints_match_ports() -> None:
    """单连接布线起止点应与端口绝对坐标一致。"""
    net, placements = _build_two_connection_netlist()
    router = WaveguideRouter(grid_size=1.0)
    routes = router.route(net, placements)
    r = routes[0]
    src_port = placements["d1"].port_positions()["out"]
    dst_port = placements["d2"].port_positions()["in"]
    assert r.path[0] == src_port
    assert r.path[-1] == dst_port


def test_route_accepts_floorplan_state() -> None:
    """route 应接受 FloorplanState 作为 placements 参数。"""
    from polaris.engine.floorplan_env import FloorplanState

    net, placements = _build_two_connection_netlist()
    state = FloorplanState(placements=dict(placements), canvas_w=200.0,
                           canvas_h=200.0, grid_size=1.0)
    router = WaveguideRouter(grid_size=1.0)
    routes = router.route(net, state)
    assert len(routes) == 2
    assert all(len(r.path) >= 2 for r in routes)
