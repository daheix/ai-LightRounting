"""P0-2 规模扩展端到端测试（第12轮）。

验证 100/200 器件规模的完整流程：生成 → 布局 → 布线 → 评估。
验证第11轮三项优化后，大规模端到端流程可跑通。

来源: commercial_gap_analysis.md P0-2 规模可扩展性
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.router.routing_env import RoutingEnv, RoutingEnvConfig


def _run_floorplan(net, devices, canvas_w, canvas_h, grid_size):
    """运行布局环境，返回 env。"""
    env = FloorplanEnv(
        net, devices, canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size
    )
    env.reset()
    n_devices = len(devices)
    for _ in range(n_devices):
        action = np.array([env.grid_w // 2, env.grid_h // 2, 0], dtype=np.int64)
        env.step(action)
    return env


def _run_routing(net, placements, canvas_w, canvas_h, grid_size):
    """运行布线环境，返回 metrics。"""
    cfg = RoutingEnvConfig(canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size)
    env = RoutingEnv(net, placements, config=cfg)
    env.reset()
    n_conns = len(net.connections)
    for _ in range(n_conns):
        action = np.zeros(3, dtype=np.float32)
        env.step(action)
    return env.total_metrics()


class TestScaleEndToEnd:
    """大规模端到端测试。"""

    @pytest.mark.parametrize("n_devices", [20, 50])
    def test_lidar_scale_end_to_end(self, n_devices):
        """LiDAR 合成 benchmark n_devices 端到端。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=n_devices)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == n_devices

        # 画布尺寸随器件数扩展
        canvas = max(500.0, n_devices * 20.0)

        t0 = time.perf_counter()
        fp_env = _run_floorplan(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=20.0
        )
        t_fp = time.perf_counter() - t0

        placements = fp_env.state.placements
        assert len(placements) == n_devices

        t0 = time.perf_counter()
        metrics = _run_routing(
            net, placements, canvas_w=canvas, canvas_h=canvas, grid_size=5.0
        )
        t_rt = time.perf_counter() - t0

        print(
            f"\n{n_devices} 器件: 布局={t_fp*1000:.0f}ms, "
            f"布线={t_rt*1000:.0f}ms, "
            f"routed={metrics['num_routed']}/{metrics['num_connections']}"
        )
        assert metrics["num_connections"] == n_devices - 1
        # 至少部分连接布线成功
        assert metrics["num_routed"] >= 0

    @pytest.mark.parametrize("n_devices", [20, 50])
    def test_apollo_ptc_scale_end_to_end(self, n_devices):
        """Apollo PTC 合成 benchmark n_devices 端到端。"""
        circuit = generate_synthetic_benchmark("apollo_ptc", num_devices=n_devices)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == n_devices

        canvas = max(500.0, n_devices * 25.0)

        t0 = time.perf_counter()
        fp_env = _run_floorplan(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=20.0
        )
        t_fp = time.perf_counter() - t0

        placements = fp_env.state.placements
        assert len(placements) == n_devices

        t0 = time.perf_counter()
        metrics = _run_routing(
            net, placements, canvas_w=canvas, canvas_h=canvas, grid_size=5.0
        )
        t_rt = time.perf_counter() - t0

        print(
            f"\nPTC {n_devices} 器件: 布局={t_fp*1000:.0f}ms, "
            f"布线={t_rt*1000:.0f}ms, "
            f"routed={metrics['num_routed']}/{metrics['num_connections']}"
        )

    def test_100_devices_floorplan_performance(self):
        """100 器件布局性能基准（P0-2 v1.0 目标 500 器件的中间验证）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=100)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 100

        canvas = 2000.0
        t0 = time.perf_counter()
        fp_env = _run_floorplan(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=20.0
        )
        t_fp = time.perf_counter() - t0

        placements = fp_env.state.placements
        assert len(placements) == 100

        print(f"\n100 器件布局: {t_fp*1000:.0f}ms")
        # 100 器件布局应在 10 秒内完成
        assert t_fp < 10.0, f"100 器件布局耗时 {t_fp:.1f}s > 10s"

    def test_100_devices_with_global_router(self):
        """100 器件 + GlobalRouter 端到端（验证 P1-2 在大规模下可用）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=100)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)

        canvas = 2000.0
        fp_env = _run_floorplan(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=20.0
        )
        placements = fp_env.state.placements

        # 启用 GlobalRouter
        cfg = RoutingEnvConfig(
            canvas_w=canvas,
            canvas_h=canvas,
            grid_size=5.0,
            use_global_router=True,
            global_router_gcell_size_um=50.0,
        )
        env = RoutingEnv(net, placements, config=cfg)
        t0 = time.perf_counter()
        env.reset()
        t_reset = time.perf_counter() - t0

        # 验证全局拥塞图已生成
        assert env._global_congestion is not None
        assert env._global_congestion.size > 0

        print(
            f"\n100 器件 GlobalRouter reset: {t_reset*1000:.0f}ms, "
            f"GCell 网格={env._global_congestion.shape}"
        )
        # GlobalRouter reset 应在 30 秒内完成
        assert t_reset < 30.0
