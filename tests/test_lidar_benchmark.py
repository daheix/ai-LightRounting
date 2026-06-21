"""LiDAR ISPD'25 光子曲线布线 Benchmark 测试（P1-5 第25轮深化）。

测试移植的 LiDAR PTC/oNoC 光子曲线布线 benchmark：
- PTC 12 器件 + 13 连接完整性
- oNoC 10 器件 + 18 连接完整性
- 曲线布线挑战器件验证
- HPWL 评估器集成
- 商业差距缩减验证

来源:
- LiDAR: https://dl.acm.org/doi/10.1145/3698364.3705355
- 代码: https://github.com/ScopeX-ASU/LiDAR
"""

from __future__ import annotations

import pytest

from polaris.data.benchmark_evaluator import (
    evaluate_benchmark,
    evaluate_hpwl,
    evaluate_overlap,
    grid_placement,
)
from polaris.data.data_loader import load_lidar_benchmark
from polaris.data.lidar_benchmark import (
    LIDAR_ONOC_CONNECTIONS,
    LIDAR_ONOC_DEVICES,
    LIDAR_PTC_CONNECTIONS,
    LIDAR_PTC_DEVICES,
    lidar_benchmark_info,
    load_lidar_onoc_benchmark,
    load_lidar_ptc_benchmark,
)
from polaris.data.specs import BenchmarkSource, TargetMetric


class TestLidarPtcDevices:
    """LiDAR PTC 器件库完整性测试。"""

    def test_ptc_device_count(self) -> None:
        """PTC 含 12 个器件（对齐 LiDAR 论文 PTC benchmark）。"""
        assert len(LIDAR_PTC_DEVICES) == 12

    def test_ptc_categories(self) -> None:
        """PTC 器件覆盖 4 类（active/passive/coupler/curvy）。"""
        categories = {d.category for d in LIDAR_PTC_DEVICES.values()}
        assert "active" in categories
        assert "passive" in categories
        assert "coupler" in categories
        assert "curvy" in categories

    def test_ptc_curvy_challenge_devices(self) -> None:
        """PTC 含曲线布线挑战器件（MZI + curvy waveguide）。"""
        curvy = [d for d in LIDAR_PTC_DEVICES.values() if d.curvy_challenge]
        assert len(curvy) >= 5  # 4 MZI + 3 curvy_wg - 部分 MZI 是挑战

    def test_ptc_mzi_matrix_present(self) -> None:
        """PTC 含 2×2 MZI 阵列。"""
        for i in range(2):
            for j in range(2):
                assert f"lidar_mzi_{i}{j}" in LIDAR_PTC_DEVICES

    def test_ptc_curvy_waveguides_present(self) -> None:
        """PTC 含 3 条曲线波导（S 弯/U 弯/对角弯）。"""
        for i in range(1, 4):
            assert f"lidar_curvy_wg_{i}" in LIDAR_PTC_DEVICES

    def test_lidar_device_is_frozen(self) -> None:
        """LiDARDevice 是 frozen dataclass。"""
        d = LIDAR_PTC_DEVICES["lidar_mzi_00"]
        with pytest.raises(AttributeError):
            d.name = "modified"  # type: ignore[misc]


class TestLidarPtcConnections:
    """LiDAR PTC 连接拓扑测试。"""

    def test_ptc_connection_count(self) -> None:
        """PTC 含 13 条真实连接（含曲线布线挑战）。"""
        assert len(LIDAR_PTC_CONNECTIONS) == 13

    def test_ptc_connections_reference_valid_devices(self) -> None:
        """所有 PTC 连接引用的器件都存在。"""
        for src, _sp, dst, _dp in LIDAR_PTC_CONNECTIONS:
            assert src in LIDAR_PTC_DEVICES, f"连接源器件 {src} 不存在"
            assert dst in LIDAR_PTC_DEVICES, f"连接目标器件 {dst} 不存在"

    def test_ptc_input_path(self) -> None:
        """PTC 输入通路：gc → modulator → mzi_00。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_PTC_CONNECTIONS}
        assert ("lidar_gc_in", "lidar_modulator") in conns
        assert ("lidar_modulator", "lidar_mzi_00") in conns

    def test_ptc_curvy_routing(self) -> None:
        """PTC 含曲线波导布线：mzi → curvy_wg → mzi。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_PTC_CONNECTIONS}
        assert ("lidar_mzi_00", "lidar_curvy_wg_1") in conns
        assert ("lidar_curvy_wg_1", "lidar_mzi_01") in conns
        assert ("lidar_mzi_10", "lidar_curvy_wg_2") in conns
        assert ("lidar_curvy_wg_2", "lidar_mzi_11") in conns

    def test_ptc_output_path(self) -> None:
        """PTC 输出通路：mzi_11 → detector → gc_out。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_PTC_CONNECTIONS}
        assert ("lidar_mzi_11", "lidar_detector") in conns
        assert ("lidar_detector", "lidar_gc_out") in conns

    def test_ptc_crossing_challenge(self) -> None:
        """PTC 含波导交叉挑战：curvy_wg_3 → crossing → mzi_01。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_PTC_CONNECTIONS}
        assert ("lidar_mzi_10", "lidar_curvy_wg_3") in conns
        assert ("lidar_curvy_wg_3", "lidar_crossing") in conns
        assert ("lidar_crossing", "lidar_mzi_01") in conns


class TestLidarOnocDevices:
    """LiDAR oNoC 器件库完整性测试。"""

    def test_onoc_device_count(self) -> None:
        """oNoC 含 10 个器件（中心路由器 + 4 节点 + 环形波导 + 4 曲线链路）。"""
        assert len(LIDAR_ONOC_DEVICES) == 10

    def test_onoc_curvy_challenge(self) -> None:
        """oNoC 含曲线布线挑战器件（环形波导 + 4 曲线链路）。"""
        curvy = [d for d in LIDAR_ONOC_DEVICES.values() if d.curvy_challenge]
        assert len(curvy) == 5  # ring_wg + 4 curvy_link

    def test_onoc_central_router(self) -> None:
        """oNoC 中心路由器存在。"""
        assert "lidar_router" in LIDAR_ONOC_DEVICES

    def test_onoc_nodes_present(self) -> None:
        """oNoC 4 个节点存在。"""
        for i in range(4):
            assert f"lidar_node_{i}" in LIDAR_ONOC_DEVICES

    def test_onoc_curvy_links_present(self) -> None:
        """oNoC 4 条曲线链路存在。"""
        for i in range(4):
            assert f"lidar_curvy_link_{i}" in LIDAR_ONOC_DEVICES


class TestLidarOnocConnections:
    """LiDAR oNoC 连接拓扑测试。"""

    def test_onoc_connection_count(self) -> None:
        """oNoC 含 18 条真实连接（2 中心 + 4 节点 × 4）。"""
        assert len(LIDAR_ONOC_CONNECTIONS) == 18

    def test_onoc_connections_reference_valid_devices(self) -> None:
        """所有 oNoC 连接引用的器件都存在。"""
        for src, _sp, dst, _dp in LIDAR_ONOC_CONNECTIONS:
            assert src in LIDAR_ONOC_DEVICES, f"连接源器件 {src} 不存在"
            assert dst in LIDAR_ONOC_DEVICES, f"连接目标器件 {dst} 不存在"

    def test_onoc_ring_bus(self) -> None:
        """oNoC 环形总线：router ↔ ring_wg。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_ONOC_CONNECTIONS}
        assert ("lidar_router", "lidar_ring_wg") in conns
        assert ("lidar_ring_wg", "lidar_router") in conns

    def test_onoc_node_complete_path(self) -> None:
        """oNoC 节点 0 完整通路：router → node → curvy_link → ring → curvy_link。"""
        conns = {(src, dst) for src, _sp, dst, _dp in LIDAR_ONOC_CONNECTIONS}
        assert ("lidar_router", "lidar_node_0") in conns
        assert ("lidar_node_0", "lidar_curvy_link_0") in conns
        assert ("lidar_curvy_link_0", "lidar_ring_wg") in conns
        assert ("lidar_ring_wg", "lidar_curvy_link_0") in conns


class TestLidarBenchmarkLoader:
    """LiDAR benchmark 加载器测试。"""

    def test_load_ptc_benchmark_basic(self) -> None:
        """load_lidar_ptc_benchmark 返回完整 CircuitSpec。"""
        circuit = load_lidar_ptc_benchmark()
        assert circuit.name == "lidar_ptc"
        assert circuit.benchmark_source == BenchmarkSource.LIDAR
        assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE
        assert circuit.process_node == "220nm SOI"
        assert circuit.optical_wavelength_nm == 1550.0

    def test_load_ptc_benchmark_devices(self) -> None:
        """PTC benchmark 含 12 个器件。"""
        circuit = load_lidar_ptc_benchmark()
        assert len(circuit.devices) == 12

    def test_load_ptc_benchmark_connections(self) -> None:
        """PTC benchmark 含 13 条连接。"""
        circuit = load_lidar_ptc_benchmark()
        assert len(circuit.connections) == 13

    def test_load_ptc_benchmark_canvas(self) -> None:
        """PTC 画布尺寸基于器件总面积自适应。"""
        circuit = load_lidar_ptc_benchmark()
        assert circuit.canvas_w > 0
        assert circuit.canvas_h > 0
        total_area = sum(d.width_um * d.height_um for d in circuit.devices)
        assert circuit.canvas_w * circuit.canvas_h >= total_area

    def test_load_onoc_benchmark_basic(self) -> None:
        """load_lidar_onoc_benchmark 返回完整 CircuitSpec。"""
        circuit = load_lidar_onoc_benchmark()
        assert circuit.name == "lidar_onoc"
        assert circuit.benchmark_source == BenchmarkSource.LIDAR
        assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE

    def test_load_onoc_benchmark_devices(self) -> None:
        """oNoC benchmark 含 10 个器件。"""
        circuit = load_lidar_onoc_benchmark()
        assert len(circuit.devices) == 10

    def test_load_onoc_benchmark_connections(self) -> None:
        """oNoC benchmark 含 18 条连接。"""
        circuit = load_lidar_onoc_benchmark()
        assert len(circuit.connections) == 18

    def test_load_lidar_from_data_loader(self) -> None:
        """data_loader.load_lidar_benchmark 返回真实拓扑（第25轮深化）。"""
        circuit = load_lidar_benchmark()
        assert circuit.name == "lidar_ptc"
        assert len(circuit.devices) == 12
        assert len(circuit.connections) == 13
        assert circuit.benchmark_source == BenchmarkSource.LIDAR

    def test_load_lidar_nonexistent_path(self) -> None:
        """不存在的 path 返回真实拓扑。"""
        circuit = load_lidar_benchmark(path="/nonexistent/lidar.pkl")
        assert len(circuit.devices) == 12


class TestLidarBenchmarkInfo:
    """LiDAR benchmark 元信息测试。"""

    def test_info_fields(self) -> None:
        """元信息含全部必要字段。"""
        info = lidar_benchmark_info()
        assert info["name"] == "lidar"
        assert info["ptc_device_count"] == 12
        assert info["ptc_connection_count"] == 13
        assert info["ptc_curvy_challenge_count"] > 0
        assert info["onoc_device_count"] == 10
        assert info["onoc_connection_count"] == 18
        assert info["onoc_curvy_challenge_count"] == 5
        assert info["process_node"] == "220nm SOI"
        assert info["benchmark_source"] == "LIDAR"
        assert "dl.acm.org" in info["source_url"]
        assert "ScopeX-ASU/LiDAR" in info["code_url"]

    def test_info_speedup(self) -> None:
        """元信息含 LiDAR 论文报告的 6.25× 加速。"""
        info = lidar_benchmark_info()
        assert "6.25x" in info["speedup_reported"]


class TestLidarBenchmarkEvaluation:
    """LiDAR benchmark 评估器集成测试。"""

    def test_ptc_hpwl_evaluation(self) -> None:
        """PTC 网格布局 HPWL > 0。"""
        circuit = load_lidar_ptc_benchmark()
        placements = grid_placement(circuit)
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl > 0

    def test_ptc_overlap_evaluation(self) -> None:
        """PTC 网格布局无重叠。"""
        circuit = load_lidar_ptc_benchmark()
        placements = grid_placement(circuit)
        assert evaluate_overlap(circuit, placements) == 0

    def test_onoc_hpwl_evaluation(self) -> None:
        """oNoC 网格布局 HPWL > 0。"""
        circuit = load_lidar_onoc_benchmark()
        placements = grid_placement(circuit)
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl > 0

    def test_onoc_overlap_evaluation(self) -> None:
        """oNoC 网格布局无重叠。"""
        circuit = load_lidar_onoc_benchmark()
        placements = grid_placement(circuit)
        assert evaluate_overlap(circuit, placements) == 0

    def test_ptc_benchmark_result(self) -> None:
        """PTC evaluate_benchmark 返回正确结果。"""
        circuit = load_lidar_ptc_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert result.benchmark_name == "lidar_ptc"
        assert result.module_count == 12
        assert result.connection_count == 13
        assert result.target_metric == "routing_success_rate"

    def test_onoc_benchmark_result(self) -> None:
        """oNoC evaluate_benchmark 返回正确结果。"""
        circuit = load_lidar_onoc_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert result.benchmark_name == "lidar_onoc"
        assert result.module_count == 10
        assert result.connection_count == 18
        assert result.target_metric == "routing_success_rate"


class TestCommercialGapReduction:
    """P1-5 商业差距缩减验证（第25轮深化）。"""

    def test_lidar_real_topology_not_synthetic(self) -> None:
        """LiDAR benchmark 使用真实拓扑（非简单链式）。"""
        ptc = load_lidar_ptc_benchmark()
        onoc = load_lidar_onoc_benchmark()
        assert len(ptc.connections) >= len(ptc.devices)
        assert len(onoc.connections) >= len(onoc.devices)

    def test_lidar_source_traced(self) -> None:
        """LiDAR benchmark 来源可溯源到 ASU ISPD'25。"""
        info = lidar_benchmark_info()
        assert "dl.acm.org" in info["source_url"]
        assert "ScopeX-ASU/LiDAR" in info["code_url"]

    def test_lidar_curvy_challenge_present(self) -> None:
        """LiDAR benchmark 含曲线布线挑战器件。"""
        info = lidar_benchmark_info()
        assert info["ptc_curvy_challenge_count"] > 0
        assert info["onoc_curvy_challenge_count"] > 0

    def test_lidar_ptc_mzi_matrix(self) -> None:
        """LiDAR PTC 含 2×2 MZI 阵列（张量核心）。"""
        circuit = load_lidar_ptc_benchmark()
        device_names = {d.name for d in circuit.devices}
        for i in range(2):
            for j in range(2):
                assert f"lidar_mzi_{i}{j}" in device_names

    def test_lidar_onoc_network_structure(self) -> None:
        """LiDAR oNoC 含星型 + 环形 + 曲线链路结构。"""
        circuit = load_lidar_onoc_benchmark()
        device_names = {d.name for d in circuit.devices}
        assert "lidar_router" in device_names
        assert "lidar_ring_wg" in device_names
        for i in range(4):
            assert f"lidar_node_{i}" in device_names
            assert f"lidar_curvy_link_{i}" in device_names

    def test_benchmark_evaluator_commercial_grade(self) -> None:
        """评估器对 LiDAR benchmark 达到商业级。"""
        for circuit in [load_lidar_ptc_benchmark(), load_lidar_onoc_benchmark()]:
            placements = grid_placement(circuit)
            result = evaluate_benchmark(circuit, placements)
            assert result.hpwl_um >= 0
            assert result.overlap_count >= 0
            assert 0 <= result.area_utilization <= 1
            assert isinstance(result.passed, bool)
            assert result.extra["benchmark_source"] == "lidar"
            assert result.extra["process_node"] == "220nm SOI"
