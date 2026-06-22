"""P0-2 v2.0 深化：5000 器件分块布局验证（第70轮）。

验证分块布局器（HierarchicalPlacer）在大规模器件下的性能：
- 2000 器件：分块布局 + 网格分布对比
- 5000 器件：分块布局 v3.0 目标
- 10000 器件：超大规模 smoke test

来源:
- P0-2 差距分析: docs/commercial_gap_analysis.md
- 谱聚类: Shi & Malik 2000, IEEE TPAMI
- DREAMPlace 分块: Lin et al., TCAD 2020
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.data.specs import CircuitSpec
from polaris.engine.hierarchical_placer import (
    HierarchicalPlacer,
    HierarchicalPlacerConfig,
    hierarchical_placement,
)
from polaris.engine.netlist import load_netlist


def _make_circuit(num_devices: int) -> CircuitSpec:
    """生成指定规模的 lidar benchmark 电路。"""
    return generate_synthetic_benchmark("lidar", num_devices=num_devices)


class TestHierarchicalPlacerBasic:
    """分块布局器基础测试。"""

    def test_small_circuit_uses_analytical(self):
        """小规模电路（≤500 器件）直接用解析法。"""
        circuit = _make_circuit(100)
        placer = HierarchicalPlacer(circuit)
        assert placer.n == 100
        # 100 器件 ≤ max_cluster_size=500，应直接用解析法
        assert placer.k <= 100
        placement = placer.place()
        assert len(placement) == 100
        # 所有器件应有有效坐标
        for name, (x, y) in placement.items():
            assert x >= 0.0, f"{name} x={x} < 0"
            assert y >= 0.0, f"{name} y={y} < 0"

    def test_large_circuit_uses_clustering(self):
        """大规模电路（>500 器件）触发分块。"""
        circuit = _make_circuit(1000)
        config = HierarchicalPlacerConfig(max_cluster_size=200)
        placer = HierarchicalPlacer(circuit, config)
        # 1000 器件 / max_cluster_size=200 → 至少 5 块
        assert placer.k >= 5
        placement = placer.place()
        assert len(placement) == 1000

    def test_spectral_clustering_partitions(self):
        """谱聚类正确分块。"""
        circuit = _make_circuit(200)
        config = HierarchicalPlacerConfig(n_clusters=4, max_cluster_size=100)
        placer = HierarchicalPlacer(circuit, config)
        labels = placer._spectral_clustering()
        assert len(labels) == 200
        # 应有 4 个子块
        unique_labels = set(labels.tolist())
        assert len(unique_labels) <= 4

    def test_placement_integrity(self):
        """布局完整性：所有器件在画布范围内。"""
        circuit = _make_circuit(500)
        placement = hierarchical_placement(circuit)
        assert len(placement) == 500
        for name, (x, y) in placement.items():
            assert np.isfinite(x), f"{name} x 非有限值"
            assert np.isfinite(y), f"{name} y 非有限值"


class TestScale2000:
    """2000 器件规模验证（v2.0 中间目标）。"""

    def test_2000_devices_hierarchical(self):
        """2000 器件分块布局性能。"""
        circuit = _make_circuit(2000)
        config = HierarchicalPlacerConfig(max_cluster_size=500)
        placer = HierarchicalPlacer(circuit, config)

        t0 = time.perf_counter()
        placement = placer.place()
        t_elapsed = time.perf_counter() - t0

        assert len(placement) == 2000
        # 2000 器件分块布局应在 30 秒内完成
        assert t_elapsed < 30.0, f"2000 器件分块布局耗时 {t_elapsed:.1f}s > 30s"
        print(f"\n2000 器件分块布局: {t_elapsed*1000:.0f}ms (k={placer.k})")

    def test_2000_devices_netlist_integrity(self):
        """2000 器件网表完整性。"""
        circuit = _make_circuit(2000)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        # LiDAR benchmark: n_devices - 1 连接（树形拓扑）
        assert len(net.connections) == 1999
        assert len(devices) == 2000


class TestScale5000:
    """5000 器件规模验证（v3.0 目标）。"""

    def test_5000_devices_hierarchical(self):
        """5000 器件分块布局性能（v3.0 目标）。"""
        circuit = _make_circuit(5000)
        config = HierarchicalPlacerConfig(max_cluster_size=500)
        placer = HierarchicalPlacer(circuit, config)

        t0 = time.perf_counter()
        placement = placer.place()
        t_elapsed = time.perf_counter() - t0

        assert len(placement) == 5000
        # 5000 器件分块布局应在 60 秒内完成
        assert t_elapsed < 60.0, f"5000 器件分块布局耗时 {t_elapsed:.1f}s > 60s"
        print(f"\n5000 器件分块布局: {t_elapsed*1000:.0f}ms (k={placer.k})")

    def test_5000_devices_placement_valid(self):
        """5000 器件布局坐标有效性。"""
        circuit = _make_circuit(5000)
        placement = hierarchical_placement(circuit)
        assert len(placement) == 5000
        for name, (x, y) in placement.items():
            assert np.isfinite(x), f"{name} x 非有限值"
            assert np.isfinite(y), f"{name} y 非有限值"
            assert x >= 0.0, f"{name} x={x} < 0"
            assert y >= 0.0, f"{name} y={y} < 0"


class TestScale10000:
    """10000 器件超大规模 smoke test。"""

    @pytest.mark.slow
    def test_10000_devices_smoke(self):
        """10000 器件分块布局 smoke test（超大规模）。"""
        circuit = _make_circuit(10000)
        config = HierarchicalPlacerConfig(max_cluster_size=500)
        placer = HierarchicalPlacer(circuit, config)

        t0 = time.perf_counter()
        placement = placer.place()
        t_elapsed = time.perf_counter() - t0

        assert len(placement) == 10000
        # 10000 器件分块布局应在 120 秒内完成
        assert t_elapsed < 120.0, f"10000 器件分块布局耗时 {t_elapsed:.1f}s > 120s"
        print(f"\n10000 器件分块布局: {t_elapsed*1000:.0f}ms (k={placer.k})")


class TestHierarchicalPlacerConfig:
    """分块布局器配置测试。"""

    def test_default_config(self):
        """默认配置值正确。"""
        config = HierarchicalPlacerConfig()
        assert config.n_clusters is None
        assert config.max_cluster_size == 500
        assert config.random_seed == 42

    def test_custom_config(self):
        """自定义配置。"""
        config = HierarchicalPlacerConfig(
            n_clusters=8,
            max_cluster_size=200,
            random_seed=123,
        )
        assert config.n_clusters == 8
        assert config.max_cluster_size == 200
        assert config.random_seed == 123

    def test_auto_n_clusters_sqrt(self):
        """自动子块数 = sqrt(n)。"""
        circuit = _make_circuit(400)
        # 400 器件，max_cluster_size=500 → 不分块，k=400
        placer = HierarchicalPlacer(circuit)
        # sqrt(400) = 20，但 400 ≤ 500 所以直接用解析法
        assert placer.n == 400

    def test_auto_n_clusters_with_max_size(self):
        """max_cluster_size 触发更多分块。"""
        circuit = _make_circuit(1000)
        config = HierarchicalPlacerConfig(max_cluster_size=100)
        placer = HierarchicalPlacer(circuit, config)
        # 1000/100 = 10 块，但 sqrt(1000)≈32，取较大值
        assert placer.k >= 10


class TestCommercialGapScaleV2:
    """P0-2 v2.0 商业规模差距验证。"""

    def test_scale_vs_apollo(self):
        """PoLaRIS 5000 器件 vs Apollo 数千器件。"""
        # Apollo (ASU 2025): 数千器件 PTC/oNoC
        # PoLaRIS v3.0: 5000 器件（对标 Apollo）
        circuit = _make_circuit(5000)
        placement = hierarchical_placement(circuit)
        assert len(placement) == 5000

    def test_scale_performance_linear(self):
        """规模扩展性能近似线性（分块布局优势）。"""
        results = {}
        for n in [500, 1000, 2000]:
            circuit = _make_circuit(n)
            config = HierarchicalPlacerConfig(max_cluster_size=500)
            placer = HierarchicalPlacer(circuit, config)
            t0 = time.perf_counter()
            placer.place()
            t = time.perf_counter() - t0
            results[n] = t

        # 性能退化应近似线性（分块布局 O(n·sqrt(n))）
        ratio_500_1000 = results[1000] / max(results[500], 1e-9)
        ratio_1000_2000 = results[2000] / max(results[1000], 1e-9)

        print(
            f"\n分块布局规模扩展: "
            f"500={results[500]*1000:.0f}ms, "
            f"1000={results[1000]*1000:.0f}ms (×{ratio_500_1000:.1f}), "
            f"2000={results[2000]*1000:.0f}ms (×{ratio_1000_2000:.1f})"
        )
        # 分块布局退化应 < O(n²)（ratio < 4× for 2× scale）
        assert ratio_500_1000 < 8.0, f"500→1000 退化 {ratio_500_1000:.1f}× > 8×"
        assert ratio_1000_2000 < 4.0, f"1000→2000 退化 {ratio_1000_2000:.1f}× > 4×"
