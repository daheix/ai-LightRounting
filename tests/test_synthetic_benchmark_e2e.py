"""合成 benchmark 端到端测试（第10轮 P1-5 优化）。

验证合成 benchmark 能完整走完：生成 → 布局 → 布线 → 评估 流程，
打通数据加载→布局环境→布线环境→指标汇总的完整链路。

来源:
- TILOS Ariane: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo PTC/oNoC: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import numpy as np

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.router.routing_env import RoutingEnv, RoutingEnvConfig


def _run_floorplan(net, devices, canvas_w=500.0, canvas_h=500.0, grid_size=20.0):
    """运行布局环境，返回 placements。"""
    env = FloorplanEnv(net, devices, canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size)
    env.reset()
    n_devices = len(devices)
    for _ in range(n_devices):
        action = np.array([env.grid_w // 2, env.grid_h // 2, 0], dtype=np.int64)
        env.step(action)
    return env


def _run_routing(net, placements, canvas_w=500.0, canvas_h=500.0, grid_size=5.0):
    """运行布线环境，返回 metrics。"""
    cfg = RoutingEnvConfig(canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size)
    env = RoutingEnv(net, placements, config=cfg)
    env.reset()
    n_conns = len(net.connections)
    for _ in range(n_conns):
        action = np.zeros(3, dtype=np.float32)
        env.step(action)
    return env.total_metrics()


class TestSyntheticBenchmarkEndToEnd:
    """合成 benchmark 端到端测试（第10轮 P1-5 优化）。"""

    def test_lidar_end_to_end(self):
        """LiDAR 合成 benchmark 端到端：生成→布局→布线→评估。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 4
        assert len(net.connections) == 3

        # 布局
        fp_env = _run_floorplan(net, devices, canvas_w=500.0, canvas_h=500.0, grid_size=20.0)
        assert len(fp_env.state.placements) > 0

        # 布线
        metrics = _run_routing(
            net,
            fp_env.state.placements,
            canvas_w=500.0,
            canvas_h=500.0,
            grid_size=5.0,
        )
        assert "total_loss_db" in metrics
        assert "total_length_um" in metrics
        assert "num_routed" in metrics
        assert "num_connections" in metrics
        assert metrics["num_connections"] == 3

    def test_apollo_ptc_end_to_end(self):
        """Apollo PTC 合成 benchmark 端到端。"""
        circuit = generate_synthetic_benchmark("apollo_ptc", num_devices=5)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 5

        fp_env = _run_floorplan(net, devices, canvas_w=800.0, canvas_h=600.0, grid_size=20.0)
        assert len(fp_env.state.placements) > 0

        metrics = _run_routing(
            net,
            fp_env.state.placements,
            canvas_w=800.0,
            canvas_h=600.0,
            grid_size=5.0,
        )
        assert metrics["num_connections"] == 3  # 5-2=3 交叉连接

    def test_apollo_onoc_end_to_end(self):
        """Apollo oNoC 合成 benchmark 端到端。"""
        circuit = generate_synthetic_benchmark("apollo_onoc", num_devices=6)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 6

        fp_env = _run_floorplan(net, devices, canvas_w=1200.0, canvas_h=1200.0, grid_size=30.0)
        assert len(fp_env.state.placements) > 0

        metrics = _run_routing(
            net,
            fp_env.state.placements,
            canvas_w=1200.0,
            canvas_h=1200.0,
            grid_size=5.0,
        )
        assert metrics["num_connections"] == 5  # 6-1=5 星型连接

    def test_tilos_ariane_end_to_end(self):
        """TILOS Ariane 合成 benchmark 端到端。"""
        circuit = generate_synthetic_benchmark("tilos_ariane", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 4

        fp_env = _run_floorplan(net, devices, canvas_w=1000.0, canvas_h=1000.0, grid_size=25.0)
        assert len(fp_env.state.placements) > 0

        metrics = _run_routing(
            net,
            fp_env.state.placements,
            canvas_w=1000.0,
            canvas_h=1000.0,
            grid_size=5.0,
        )
        assert metrics["num_connections"] == 3  # 4-1=3 链式连接


class TestSyntheticBenchmarkWithGlobalRouter:
    """合成 benchmark + 全局布线器端到端测试。"""

    def test_lidar_with_global_router(self):
        """LiDAR 合成 benchmark 启用全局布线器端到端。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=3)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)

        fp_env = _run_floorplan(net, devices, canvas_w=500.0, canvas_h=500.0, grid_size=20.0)

        cfg = RoutingEnvConfig(
            canvas_w=500.0,
            canvas_h=500.0,
            grid_size=5.0,
            use_global_router=True,
            global_router_gcell_size_um=50.0,
        )
        r_env = RoutingEnv(net, fp_env.state.placements, config=cfg)
        obs, _info = r_env.reset()
        assert "global_congestion" in obs
        assert r_env._global_routes is not None
        assert len(r_env._global_routes) > 0

        # 完整布线
        n_conns = len(net.connections)
        for _ in range(n_conns):
            action = np.zeros(3, dtype=np.float32)
            _obs, _r, terminated, _tr, info = r_env.step(action)
            assert "global_waypoints" in info
            if terminated:
                break

        metrics = r_env.total_metrics()
        assert metrics["num_connections"] == 2  # 3-1=2 链式连接

    def test_apollo_onoc_with_global_router(self):
        """Apollo oNoC 合成 benchmark 启用全局布线器端到端。"""
        circuit = generate_synthetic_benchmark("apollo_onoc", num_devices=5)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)

        fp_env = _run_floorplan(net, devices, canvas_w=1200.0, canvas_h=1200.0, grid_size=30.0)

        cfg = RoutingEnvConfig(
            canvas_w=1200.0,
            canvas_h=1200.0,
            grid_size=5.0,
            use_global_router=True,
            global_router_gcell_size_um=100.0,
        )
        r_env = RoutingEnv(net, fp_env.state.placements, config=cfg)
        obs, _info = r_env.reset()
        assert "global_congestion" in obs

        n_conns = len(net.connections)
        for _ in range(n_conns):
            action = np.zeros(3, dtype=np.float32)
            r_env.step(action)

        metrics = r_env.total_metrics()
        assert metrics["num_connections"] == 4  # 5-1=4 星型连接


class TestSyntheticBenchmarkMetrics:
    """合成 benchmark 指标验证测试。"""

    def test_metrics_are_non_negative(self):
        """布线指标为非负数。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=3)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        fp_env = _run_floorplan(net, devices, canvas_w=500.0, canvas_h=500.0, grid_size=20.0)
        metrics = _run_routing(
            net, fp_env.state.placements, canvas_w=500.0, canvas_h=500.0, grid_size=5.0
        )
        assert metrics["total_loss_db"] >= 0.0
        assert metrics["total_length_um"] >= 0.0
        assert metrics["max_congestion"] >= 0.0

    def test_num_routed_le_num_connections(self):
        """已布线数 <= 总连接数。"""
        circuit = generate_synthetic_benchmark("apollo_ptc", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        fp_env = _run_floorplan(net, devices, canvas_w=800.0, canvas_h=600.0, grid_size=20.0)
        metrics = _run_routing(
            net, fp_env.state.placements, canvas_w=800.0, canvas_h=600.0, grid_size=5.0
        )
        assert metrics["num_routed"] <= metrics["num_connections"]

    def test_routing_success_rate(self):
        """布线成功率 = num_routed / num_connections，应在 [0, 1]。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=5)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        fp_env = _run_floorplan(net, devices, canvas_w=500.0, canvas_h=500.0, grid_size=20.0)
        metrics = _run_routing(
            net, fp_env.state.placements, canvas_w=500.0, canvas_h=500.0, grid_size=5.0
        )
        if metrics["num_connections"] > 0:
            success_rate = metrics["num_routed"] / metrics["num_connections"]
            assert 0.0 <= success_rate <= 1.0
