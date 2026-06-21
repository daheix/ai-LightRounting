"""合成 benchmark 生成测试（第9轮 P1-5）。

验证 generate_synthetic_benchmark() 能正确生成 4 种 benchmark 类型的
合成 CircuitSpec，含器件、连接、元数据，可用于 CI 回归测试。

来源:
- TILOS Ariane: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo PTC/oNoC: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import pytest

from polaris.data.data_loader import generate_synthetic_benchmark
from polaris.data.specs import BenchmarkSource, CircuitSpec, TargetMetric


class TestGenerateSyntheticBenchmark:
    """合成 benchmark 生成测试。"""

    def test_tilos_ariane_synthetic(self):
        """TILOS Ariane 合成 benchmark 生成。"""
        circuit = generate_synthetic_benchmark("tilos_ariane", num_devices=5)
        assert isinstance(circuit, CircuitSpec)
        assert circuit.benchmark_source == BenchmarkSource.TILOS
        assert circuit.name == "tilos_ariane_synthetic"
        assert circuit.process_node == "NanGate45"
        assert circuit.target_metric == TargetMetric.HPWL
        assert len(circuit.devices) == 5
        assert len(circuit.connections) == 4  # 链式连接 n-1

    def test_apollo_ptc_synthetic(self):
        """Apollo PTC 合成 benchmark 生成。"""
        circuit = generate_synthetic_benchmark("apollo_ptc", num_devices=6)
        assert isinstance(circuit, CircuitSpec)
        assert circuit.benchmark_source == BenchmarkSource.APOLLO
        assert circuit.name == "apollo_ptc_synthetic"
        assert circuit.process_node == "220nm SOI"
        assert circuit.target_metric == TargetMetric.INSERTION_LOSS_DB
        assert len(circuit.devices) == 6
        assert len(circuit.connections) == 4  # 交叉连接 n-2

    def test_apollo_onoc_synthetic(self):
        """Apollo oNoC 合成 benchmark 生成。"""
        circuit = generate_synthetic_benchmark("apollo_onoc", num_devices=8)
        assert isinstance(circuit, CircuitSpec)
        assert circuit.benchmark_source == BenchmarkSource.APOLLO
        assert circuit.name == "apollo_onoc_synthetic"
        assert circuit.process_node == "220nm SOI"
        assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE
        assert len(circuit.devices) == 8
        assert len(circuit.connections) == 7  # 星型连接 n-1

    def test_lidar_synthetic(self):
        """LiDAR 合成 benchmark 生成。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=10)
        assert isinstance(circuit, CircuitSpec)
        assert circuit.benchmark_source == BenchmarkSource.LIDAR
        assert circuit.name == "lidar_ispd25_synthetic"
        assert circuit.process_node == "220nm SOI"
        assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE
        assert len(circuit.devices) == 10
        assert len(circuit.connections) == 9  # 链式连接 n-1

    def test_default_num_devices(self):
        """默认 num_devices=10。"""
        circuit = generate_synthetic_benchmark("tilos_ariane")
        assert len(circuit.devices) == 10

    def test_invalid_benchmark_type_raises(self):
        """不支持的 benchmark 类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="不支持的 benchmark 类型"):
            generate_synthetic_benchmark("invalid_type")


class TestSyntheticBenchmarkStructure:
    """合成 benchmark 结构完整性测试。"""

    def test_devices_have_ports(self):
        """合成器件含 in/out 端口。"""
        circuit = generate_synthetic_benchmark("tilos_ariane", num_devices=3)
        for dev in circuit.devices:
            assert len(dev.ports) >= 2
            port_names = [p[0] for p in dev.ports]
            assert "in" in port_names
            assert "out" in port_names

    def test_connections_reference_valid_devices(self):
        """连接引用的器件名在 devices 列表中存在。"""
        circuit = generate_synthetic_benchmark("apollo_ptc", num_devices=5)
        dev_names = {d.name for d in circuit.devices}
        for src, _sp, dst, _dp in circuit.connections:
            assert src in dev_names, f"连接源器件 {src} 不在器件列表中"
            assert dst in dev_names, f"连接目标器件 {dst} 不在器件列表中"

    def test_connections_reference_valid_ports(self):
        """连接引用的端口名在器件端口列表中存在。"""
        circuit = generate_synthetic_benchmark("lidar", num_devices=4)
        dev_port_map = {d.name: {p[0] for p in d.ports} for d in circuit.devices}
        for src, sp, dst, dp in circuit.connections:
            assert sp in dev_port_map[src], f"端口 {sp} 不在器件 {src} 中"
            assert dp in dev_port_map[dst], f"端口 {dp} 不在器件 {dst} 中"

    def test_canvas_dimensions_positive(self):
        """画布尺寸为正数。"""
        for btype in ["tilos_ariane", "apollo_ptc", "apollo_onoc", "lidar"]:
            circuit = generate_synthetic_benchmark(btype, num_devices=3)
            assert circuit.canvas_w > 0
            assert circuit.canvas_h > 0

    def test_optical_wavelength_for_photonics(self):
        """光子 benchmark 工作波长为 1550nm。"""
        for btype in ["apollo_ptc", "apollo_onoc", "lidar"]:
            circuit = generate_synthetic_benchmark(btype, num_devices=3)
            assert circuit.optical_wavelength_nm == 1550.0


class TestSyntheticBenchmarkToNetlist:
    """合成 benchmark 转 netlist 测试。"""

    def test_synthetic_benchmark_convertible_to_netlist_dict(self):
        """合成 benchmark 可转换为 netlist dict。"""
        from polaris.data.data_loader import circuit_spec_to_netlist_dict

        circuit = generate_synthetic_benchmark("lidar", num_devices=3)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        assert "name" in netlist_dict
        assert "instances" in netlist_dict
        assert "connections" in netlist_dict
        assert len(netlist_dict["instances"]) == 3
        assert len(netlist_dict["connections"]) == 2

    def test_synthetic_benchmark_netlist_dict_parseable(self):
        """合成 benchmark 转换的 netlist dict 可被 parse_netlist 解析。"""
        from polaris.data.data_loader import circuit_spec_to_netlist_dict
        from polaris.engine.netlist import parse_netlist

        circuit = generate_synthetic_benchmark("lidar", num_devices=3)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net = parse_netlist(netlist_dict)
        assert len(net.instances) == 3
        assert len(net.connections) == 2
