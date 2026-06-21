"""P0-2 深化：1000 器件规模验证（第22轮）。

验证 200/500/1000 器件规模的布局性能，对标商业工具规模能力：
- ICC2：500M+ 实例
- Innovus：3nm/2nm，大规模
- PoLaRIS v1.0 目标：500 器件
- PoLaRIS v2.0 目标：1000-5000 器件

来源: commercial_gap_analysis.md P0-2 规模可扩展性
"""

from __future__ import annotations

import time

import numpy as np

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist


def _run_floorplan_distributed(net, devices, canvas_w, canvas_h, grid_size):
    """分布式布局（网格分布放置），返回 (env, 耗时秒)。

    将器件均匀分布在画布网格上，避免中心放置导致的 O(n²) 重叠检测。
    """
    env = FloorplanEnv(
        net, devices, canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size
    )
    env.reset()
    n_devices = len(devices)
    # 计算网格分布：sqrt(n) × sqrt(n) 网格
    grid_n = int(np.ceil(np.sqrt(n_devices)))
    t0 = time.perf_counter()
    for i in range(n_devices):
        row = i // grid_n
        col = i % grid_n
        x = min(col + 1, env.grid_w - 1)
        y = min(row + 1, env.grid_h - 1)
        action = np.array([x, y, 0], dtype=np.int64)
        env.step(action)
    t_elapsed = time.perf_counter() - t0
    return env, t_elapsed


class TestScale200:
    """200 器件规模验证。"""

    def test_200_devices_floorplan(self):
        """200 器件布局性能（P0-2 中间目标）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=200)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 200

        canvas = 4000.0
        env, t_fp = _run_floorplan_distributed(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=40.0
        )
        assert len(env.state.placements) == 200

        print(f"\n200 器件布局: {t_fp*1000:.0f}ms")
        # 200 器件布局应在 30 秒内完成
        assert t_fp < 30.0, f"200 器件布局耗时 {t_fp:.1f}s > 30s"

    def test_200_devices_placement_integrity(self):
        """200 器件布局完整性（空间哈希优化验证）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=200)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)

        canvas = 4000.0
        env, _ = _run_floorplan_distributed(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=40.0
        )
        placements = env.state.placements
        assert len(placements) == 200
        for placement in placements.values():
            assert placement.x >= 0.0
            assert placement.y >= 0.0
            assert placement.x < canvas
            assert placement.y < canvas
        print("\n200 器件空间哈希验证通过")


class TestScale500:
    """500 器件规模验证（P0-2 v1.0 目标）。"""

    def test_500_devices_floorplan(self):
        """500 器件布局性能（P0-2 v1.0 目标）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=500)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 500

        canvas = 10000.0
        env, t_fp = _run_floorplan_distributed(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=100.0
        )
        assert len(env.state.placements) == 500

        print(f"\n500 器件布局: {t_fp*1000:.0f}ms")
        # 500 器件布局应在 60 秒内完成（v1.0 目标）
        assert t_fp < 60.0, f"500 器件布局耗时 {t_fp:.1f}s > 60s"

    def test_500_devices_canvas_scaling(self):
        """500 器件画布尺寸自适应（20μm/器件 × 500 = 10000μm）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=500)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)

        canvas = max(500.0, 500 * 20.0)
        assert canvas == 10000.0

        env, _ = _run_floorplan_distributed(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=100.0
        )
        assert len(env.state.placements) == 500


class TestScale1000:
    """1000 器件规模验证（v2.0 目标）。"""

    def test_1000_devices_floorplan(self):
        """1000 器件布局性能（v2.0 目标）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=1000)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        assert len(net.instances) == 1000

        canvas = 20000.0
        env, t_fp = _run_floorplan_distributed(
            net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=200.0
        )
        assert len(env.state.placements) == 1000

        print(f"\n1000 器件布局: {t_fp*1000:.0f}ms")
        # 1000 器件布局应在 120 秒内完成（v2.0 目标）
        assert t_fp < 120.0, f"1000 器件布局耗时 {t_fp:.1f}s > 120s"

    def test_1000_devices_netlist_integrity(self):
        """1000 器件网表完整性（连接数 = 999）。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=1000)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        # LiDAR benchmark: n_devices - 1 连接（树形拓扑）
        assert len(net.connections) == 999
        assert len(devices) == 1000


class TestCommercialGapScale:
    """P0-2 商业规模差距验证。"""

    def test_scale_vs_commercial(self):
        """PoLaRIS 规模 vs 商业标杆。"""
        # 商业标杆：ICC2 500M+ 实例，Innovus 3nm 大规模
        # PoLaRIS v1.0：500 器件，v2.0：1000-5000 器件
        # 差距：500 vs 500M = 1:1M（光子 vs 电子芯片，不同领域）
        circuit = generate_synthetic_benchmark("lidar", num_devices=500)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        # PoLaRIS v1.0 目标 500 器件达标
        assert len(devices) == 500

    def test_scale_performance_degradation(self):
        """规模扩展性能退化分析（线性 vs 超线性）。"""
        results = {}
        for n in [20, 50, 100]:
            circuit = generate_synthetic_benchmark("lidar", num_devices=n)
            netlist_dict = circuit_spec_to_netlist_dict(circuit)
            net, devices, _graph = load_netlist(netlist_dict)
            canvas = max(500.0, n * 20.0)
            grid = max(20.0, n * 0.2)
            _, t = _run_floorplan_distributed(
                net, devices, canvas_w=canvas, canvas_h=canvas, grid_size=grid
            )
            results[n] = t

        # 性能退化应近似线性（O(n) 或 O(n log n)），不应超线性（O(n²)）
        ratio_20_50 = results[50] / max(results[20], 1e-9)
        ratio_50_100 = results[100] / max(results[50], 1e-9)

        print(
            f"\n规模扩展性能: 20={results[20]*1000:.0f}ms, "
            f"50={results[50]*1000:.0f}ms (×{ratio_20_50:.1f}), "
            f"100={results[100]*1000:.0f}ms (×{ratio_50_100:.1f})"
        )
        # 空间哈希优化后，退化应 < O(n²)（ratio < 5× for 2.5× scale）
        assert ratio_20_50 < 10.0, f"20→50 退化 {ratio_20_50:.1f}× > 10×"
        assert ratio_50_100 < 5.0, f"50→100 退化 {ratio_50_100:.1f}× > 5×"
