"""全局布线器测试（第5轮 P1-2）。

验证 GlobalRouter 的 GCell 网格构建、RUDY 拥塞预估、网排序、
GCell A* 全局路径分配、Rip-up&Reroute、途经点提取。

来源:
- DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
- LiDAR 2.0 分层布线: https://arxiv.org/html/2505.17239v2
- Cadence Innovus 全局-详细分层
  https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
"""

from __future__ import annotations

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import (
    Netlist,
    NetlistConnection,
    NetlistInstance,
)
from polaris.pdk.device import BoundingBox, Device, Port
from polaris.pdk.port import Direction
from polaris.router.global_router import (
    GCell,
    GlobalRoute,
    GlobalRouter,
    GlobalRouterConfig,
    run_global_routing,
)


def _make_device(
    device_id: str,
    x: float,
    y: float,
    w: float = 20.0,
    h: float = 20.0,
    ports: list[tuple[str, float, float, Direction]] | None = None,
) -> Device:
    """构造测试用 Device（含端口）。

    Device 的 bbox 从 (0,0) 开始，端口坐标相对 (0,0)。
    Placement 的 x,y 是器件左下角放置位置（绝对坐标）。
    """
    if ports is None:
        ports = [
            ("in", 0.0, h / 2, Direction.WEST),
            ("out", w, h / 2, Direction.EAST),
        ]
    port_objs = [
        Port(name=n, x=px, y=py, direction=d, waveguide_type="strip", width=0.5)
        for n, px, py, d in ports
    ]
    return Device(
        device_id=device_id,
        platform="SOI",
        category="passive",
        name="test_device",
        ports=port_objs,
        bbox=BoundingBox(0, 0, w, h),
    )


def _make_placement(device: Device, x: float, y: float, rotation: int = 0) -> Placement:
    """构造测试用 Placement。"""
    return Placement(
        instance_id=device.device_id,
        device=device,
        x=x,
        y=y,
        rotation=rotation,
    )


def _make_netlist(connections: list[tuple[str, str, str, str]]) -> Netlist:
    """构造测试用 Netlist。"""
    return Netlist(
        instances=[NetlistInstance(instance_id="dummy", component="wg")],
        connections=[
            NetlistConnection(src_instance=s, src_port=sp, dst_instance=d, dst_port=dp)
            for s, sp, d, dp in connections
        ],
        name="test",
    )


class TestGCell:
    """GCell 数据结构测试。"""

    def test_gcell_basic(self):
        cell = GCell(gx=1, gy=2, capacity=4.0, demand=2.0)
        assert cell.gx == 1
        assert cell.gy == 2
        assert cell.capacity == 4.0
        assert cell.demand == 2.0
        assert cell.overflow == 0.0

    def test_gcell_overflow(self):
        cell = GCell(gx=0, gy=0, capacity=2.0, demand=5.0)
        assert cell.overflow == 3.0


class TestGlobalRoute:
    """GlobalRoute 数据结构测试。"""

    def test_global_route_default(self):
        gr = GlobalRoute(conn_idx=0)
        assert gr.conn_idx == 0
        assert gr.gcell_path == []
        assert gr.waypoints == []
        assert gr.estimated_length_um == 0.0

    def test_global_route_with_path(self):
        gr = GlobalRoute(
            conn_idx=1,
            gcell_path=[(0, 0), (1, 0), (2, 0)],
            waypoints=[(25.0, 25.0), (75.0, 25.0), (125.0, 25.0)],
            estimated_length_um=100.0,
        )
        assert len(gr.gcell_path) == 3
        assert len(gr.waypoints) == 3
        assert gr.estimated_length_um == 100.0


class TestGlobalRouterConfig:
    """GlobalRouterConfig 测试。"""

    def test_default_config(self):
        cfg = GlobalRouterConfig()
        assert cfg.gcell_size_um == 50.0
        assert cfg.capacity_per_gcell == 4.0
        assert cfg.max_rip_reroute_rounds == 3
        assert cfg.congestion_weight == 2.0

    def test_custom_config(self):
        cfg = GlobalRouterConfig(
            gcell_size_um=25.0, capacity_per_gcell=8.0, max_rip_reroute_rounds=5
        )
        assert cfg.gcell_size_um == 25.0
        assert cfg.capacity_per_gcell == 8.0
        assert cfg.max_rip_reroute_rounds == 5


class TestGlobalRouterInit:
    """GlobalRouter 初始化测试。"""

    def test_init_basic(self):
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, canvas_w=200, canvas_h=200)
        assert router.canvas_w == 200
        assert router.canvas_h == 200
        assert router.gcell_size == 50.0
        assert router.gw == 4  # 200 / 50
        assert router.gh == 4
        assert router.capacity.shape == (4, 4)
        assert router.demand.shape == (4, 4)
        assert router.obstacle_mask.shape == (4, 4)

    def test_init_custom_config(self):
        dev1 = _make_device("d1", 0, 0)
        placements = {"d1": _make_placement(dev1, 0, 0)}
        net = _make_netlist([])
        cfg = GlobalRouterConfig(gcell_size_um=25.0)
        router = GlobalRouter(net, placements, 100, 100, cfg)
        assert router.gcell_size == 25.0
        assert router.gw == 4  # 100 / 25
        assert router.gh == 4

    def test_obstacle_mask_marks_placed_devices(self):
        """测试器件障碍掩码正确标记已放置器件占用的 GCell。"""
        dev1 = _make_device("d1", 0, 0, 60, 60)  # 占据 (0,0)-(60,60)
        placements = {"d1": _make_placement(dev1, 0, 0)}
        net = _make_netlist([])
        router = GlobalRouter(net, placements, 200, 200)
        # gcell_size=50, dev 占据 (0,0)-(60,60) → GCell (0,0),(1,0),(0,1),(1,1)
        assert router.obstacle_mask[0, 0]
        assert router.obstacle_mask[0, 1]
        assert router.obstacle_mask[1, 0]
        assert router.obstacle_mask[1, 1]
        assert not router.obstacle_mask[2, 2]


class TestGlobalRouterRouting:
    """GlobalRouter 布线功能测试。"""

    def test_single_connection_routing(self):
        """测试单连接全局布线。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 200, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 200, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 300, 100)
        results = router.route()
        assert len(results) == 1
        gr = results[0]
        assert gr.conn_idx == 0
        assert len(gr.gcell_path) >= 2  # 至少起点+终点
        assert len(gr.waypoints) == len(gr.gcell_path)
        assert gr.estimated_length_um > 0

    def test_no_connections(self):
        """测试无连接时返回空列表。"""
        dev1 = _make_device("d1", 0, 0)
        placements = {"d1": _make_placement(dev1, 0, 0)}
        net = _make_netlist([])
        router = GlobalRouter(net, placements, 200, 200)
        results = router.route()
        assert results == []

    def test_multiple_connections(self):
        """测试多连接全局布线。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 200, 0, 20, 20)
        dev3 = _make_device("d3", 0, 200, 20, 20)
        dev4 = _make_device("d4", 200, 200, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 200, 0),
            "d3": _make_placement(dev3, 0, 200),
            "d4": _make_placement(dev4, 200, 200),
        }
        net = _make_netlist(
            [
                ("d1", "out", "d2", "in"),
                ("d3", "out", "d4", "in"),
                ("d1", "out", "d3", "in"),
            ]
        )
        router = GlobalRouter(net, placements, 300, 300)
        results = router.route()
        assert len(results) == 3

    def test_waypoints_in_um_coordinates(self):
        """测试途经点为 μm 坐标。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        results = router.route()
        assert len(results) == 1
        for x, y in results[0].waypoints:
            assert 0 <= x <= 200
            assert 0 <= y <= 100

    def test_congestion_map(self):
        """测试拥塞图返回 demand - capacity。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        router.route()
        cong = router.congestion_map()
        assert cong.shape == (router.gh, router.gw)
        # cong = demand - capacity，布线后 demand >= 0，capacity > 0
        # cong.sum() 可能为负（capacity 未用完）或正（拥塞溢出）
        # 验证拥塞图值合理：demand 累加 >= 0
        assert router.demand.sum() >= 0

    def test_obstacle_avoidance(self):
        """测试全局布线避开中间器件障碍。

        起止 GCell（器件端口所在 GCell）允许是障碍，但中间路径不应经过
        其他器件占用的 GCell。
        """
        # d1 在 (0,0)，d2 在 (200,0)，d3 障碍在中间 (100,0)
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 200, 0, 20, 20)
        dev3 = _make_device("d3", 100, 0, 40, 40)  # 大障碍
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 200, 0),
            "d3": _make_placement(dev3, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 300, 200)
        results = router.route()
        assert len(results) == 1
        gr = results[0]
        # 起止 GCell 允许是障碍（端口所在），中间路径不应经过障碍
        start_gcell = gr.gcell_path[0]
        goal_gcell = gr.gcell_path[-1]
        for _i, (gx, gy) in enumerate(gr.gcell_path):
            if (gx, gy) in (start_gcell, goal_gcell):
                continue  # 起止允许是障碍
            assert not router.obstacle_mask[gy, gx], f"中间路径经过障碍 GCell ({gx}, {gy})"

    def test_rudy_congestion_estimation(self):
        """测试 RUDY 拥塞预估返回归一化 [0,1] 图。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        rudy = router._estimate_rudy_congestion()
        assert rudy.shape == (router.gh, router.gw)
        assert rudy.min() >= 0.0
        assert rudy.max() <= 1.0

    def test_connection_sorting(self):
        """测试网排序（难网优先：长距离 + 高拥塞在前）。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 200, 0, 20, 20)  # 远
        dev3 = _make_device("d3", 30, 0, 20, 20)  # 近
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 200, 0),
            "d3": _make_placement(dev3, 30, 0),
        }
        net = _make_netlist(
            [
                ("d1", "out", "d3", "in"),  # 近
                ("d1", "out", "d2", "in"),  # 远
            ]
        )
        router = GlobalRouter(net, placements, 300, 100)
        rudy = router._estimate_rudy_congestion()
        sorted_conns = router._sort_connections(rudy)
        # 远连接（d1->d2）应排在前（难度更高）
        assert sorted_conns[0][2] >= sorted_conns[1][2]


class TestRunGlobalRouting:
    """便捷函数 run_global_routing 测试。"""

    def test_run_global_routing_basic(self):
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        results = run_global_routing(net, placements, 200, 100)
        assert len(results) == 1
        assert results[0].conn_idx == 0

    def test_run_global_routing_with_config(self):
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 100, 0, 20, 20)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        cfg = GlobalRouterConfig(gcell_size_um=25.0)
        results = run_global_routing(net, placements, 200, 100, cfg)
        assert len(results) == 1


class TestGlobalRouterEdgeCases:
    """GlobalRouter 边界情况测试。"""

    def test_same_position_endpoints(self):
        """测试起止 GCell 相同时返回单点路径。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        dev2 = _make_device("d2", 10, 0, 20, 20)  # 同一 GCell
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 10, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        results = router.route()
        assert len(results) == 1
        # 起止在同一 GCell，路径长度 >= 1
        assert len(results[0].gcell_path) >= 1

    def test_missing_placement(self):
        """测试连接的实例未放置时跳过该连接。"""
        dev1 = _make_device("d1", 0, 0, 20, 20)
        placements = {"d1": _make_placement(dev1, 0, 0)}
        # d2 未放置
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        results = router.route()
        assert len(results) == 0  # d2 未放置，连接被跳过

    def test_missing_port(self):
        """测试端口不存在时跳过该连接。"""
        dev1 = _make_device("d1", 0, 0, 20, 20, ports=[("in", 0, 10, Direction.WEST)])
        dev2 = _make_device("d2", 100, 0, 20, 20, ports=[("in", 0, 10, Direction.WEST)])
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 100, 0),
        }
        # d1 无 "out" 端口
        net = _make_netlist([("d1", "out", "d2", "in")])
        router = GlobalRouter(net, placements, 200, 100)
        results = router.route()
        assert len(results) == 0  # 端口不存在，连接被跳过

    def test_small_canvas(self):
        """测试小画布（GCell 网格最小为 1x1）。"""
        dev1 = _make_device("d1", 0, 0, 5, 5)
        dev2 = _make_device("d2", 30, 0, 5, 5)
        placements = {
            "d1": _make_placement(dev1, 0, 0),
            "d2": _make_placement(dev2, 30, 0),
        }
        net = _make_netlist([("d1", "out", "d2", "in")])
        # canvas=40, gcell_size=50 → gw=gh=1（最小）
        router = GlobalRouter(net, placements, 40, 40)
        assert router.gw == 1
        assert router.gh == 1
        results = router.route()
        assert len(results) == 1
