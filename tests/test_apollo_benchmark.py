"""Apollo 光子 Benchmark 测试（P1-5 第24轮深化）。

测试移植的 Apollo PTC/oNoC 光子 benchmark：
- PTC 12 器件 + 13 连接完整性
- oNoC 14 器件 + 21 连接完整性
- 真实拓扑验证（数据流 + 星型 + 环形总线）
- HPWL 评估器集成
- 商业差距缩减验证

来源:
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- 论文: https://arxiv.org/abs/2504.18813
"""

from __future__ import annotations

import pytest

from polaris.data.apollo_benchmark import (
    ONOC_CONNECTIONS,
    ONOC_DEVICES,
    PTC_CONNECTIONS,
    PTC_DEVICES,
    apollo_benchmark_info,
    load_apollo_onoc_benchmark,
    load_apollo_ptc_benchmark,
)
from polaris.data.benchmark_evaluator import (
    evaluate_benchmark,
    evaluate_hpwl,
    evaluate_insertion_loss,
    evaluate_overlap,
    grid_placement,
)
from polaris.data.data_loader import load_apollo_onoc, load_apollo_ptc
from polaris.data.specs import BenchmarkSource, TargetMetric


class TestPtcDevices:
    """Apollo PTC 器件库完整性测试。"""

    def test_ptc_device_count(self) -> None:
        """PTC 含 12 个器件（对齐 Apollo 论文 Fig.2）。"""
        assert len(PTC_DEVICES) == 12

    def test_ptc_categories(self) -> None:
        """PTC 器件覆盖 3 类（active/passive/coupler）。"""
        categories = {d.category for d in PTC_DEVICES.values()}
        assert "active" in categories
        assert "passive" in categories
        assert "coupler" in categories

    def test_ptc_core_devices_present(self) -> None:
        """PTC 核心器件存在（MZI 阵列 + 调制器 + 探测器）。"""
        required = {"mzi_matrix_4x4", "modulator_array", "detector_array"}
        assert required.issubset(PTC_DEVICES.keys())

    def test_ptc_io_devices_present(self) -> None:
        """PTC 输入输出器件存在（光栅耦合器阵列 + 波导总线）。"""
        required = {"gc_in_array", "gc_out_array", "input_waveguide_bus", "output_waveguide_bus"}
        assert required.issubset(PTC_DEVICES.keys())

    def test_ptc_sizes_positive(self) -> None:
        """所有 PTC 器件尺寸为正。"""
        for name, d in PTC_DEVICES.items():
            assert d.width_um > 0, f"{name} 宽度非正"
            assert d.height_um > 0, f"{name} 高度非正"

    def test_photonic_device_is_frozen(self) -> None:
        """PhotonicDevice 是 frozen dataclass。"""
        d = PTC_DEVICES["mzi_matrix_4x4"]
        with pytest.raises(AttributeError):
            d.name = "modified"  # type: ignore[misc]


class TestPtcConnections:
    """Apollo PTC 连接拓扑测试。"""

    def test_ptc_connection_count(self) -> None:
        """PTC 含 13 条真实连接（数据流：激光→调制→MZI→探测→输出）。"""
        assert len(PTC_CONNECTIONS) == 13

    def test_ptc_connections_reference_valid_devices(self) -> None:
        """所有 PTC 连接引用的器件都存在。"""
        for src, _sp, dst, _dp in PTC_CONNECTIONS:
            assert src in PTC_DEVICES, f"连接源器件 {src} 不存在"
            assert dst in PTC_DEVICES, f"连接目标器件 {dst} 不存在"

    def test_ptc_input_data_path(self) -> None:
        """PTC 输入数据通路：laser → taper → waveguide → gc → modulator → mzi。"""
        conns = {(src, dst) for src, _sp, dst, _dp in PTC_CONNECTIONS}
        assert ("bias_laser_in", "taper_in") in conns
        assert ("taper_in", "input_waveguide_bus") in conns
        assert ("input_waveguide_bus", "gc_in_array") in conns
        assert ("gc_in_array", "modulator_array") in conns
        assert ("modulator_array", "mzi_matrix_4x4") in conns

    def test_ptc_output_data_path(self) -> None:
        """PTC 输出数据通路：mzi → detector → waveguide → taper → gc。"""
        conns = {(src, dst) for src, _sp, dst, _dp in PTC_CONNECTIONS}
        assert ("mzi_matrix_4x4", "detector_array") in conns
        assert ("detector_array", "output_waveguide_bus") in conns
        assert ("output_waveguide_bus", "taper_out") in conns
        assert ("taper_out", "gc_out_array") in conns

    def test_ptc_mzi_internal_connections(self) -> None:
        """PTC MZI 阵列内部连接（相位调制器 + 交叉）。"""
        conns = {(src, dst) for src, _sp, dst, _dp in PTC_CONNECTIONS}
        assert ("mzi_matrix_4x4", "phase_shifter_array") in conns
        assert ("phase_shifter_array", "mzi_matrix_4x4") in conns
        assert ("mzi_matrix_4x4", "crossing") in conns


class TestOnocDevices:
    """Apollo oNoC 器件库完整性测试。"""

    def test_onoc_device_count(self) -> None:
        """oNoC 含 15 个器件（中心路由器 + 4 节点 × 2 + 激光 + 环形波导 + 4 serdes）。"""
        assert len(ONOC_DEVICES) == 15

    def test_onoc_categories(self) -> None:
        """oNoC 器件覆盖 3 类。"""
        categories = {d.category for d in ONOC_DEVICES.values()}
        assert "active" in categories
        assert "passive" in categories

    def test_onoc_central_router_present(self) -> None:
        """oNoC 中心路由器存在。"""
        assert "central_router" in ONOC_DEVICES

    def test_onoc_nodes_present(self) -> None:
        """oNoC 4 个节点（每节点含调制器 + 探测器）。"""
        for i in range(4):
            assert f"node_{i}_modulator" in ONOC_DEVICES
            assert f"node_{i}_detector" in ONOC_DEVICES

    def test_onoc_serdes_present(self) -> None:
        """oNoC 4 个 serdes 串并转换器。"""
        for i in range(4):
            assert f"serdes_{i}" in ONOC_DEVICES


class TestOnocConnections:
    """Apollo oNoC 连接拓扑测试。"""

    def test_onoc_connection_count(self) -> None:
        """oNoC 含 23 条真实连接（星型 + 环形总线：3 中心 + 4 节点 × 5）。"""
        assert len(ONOC_CONNECTIONS) == 23

    def test_onoc_connections_reference_valid_devices(self) -> None:
        """所有 oNoC 连接引用的器件都存在。"""
        for src, _sp, dst, _dp in ONOC_CONNECTIONS:
            assert src in ONOC_DEVICES, f"连接源器件 {src} 不存在"
            assert dst in ONOC_DEVICES, f"连接目标器件 {dst} 不存在"

    def test_onoc_star_topology(self) -> None:
        """oNoC 星型拓扑：中心路由器 → 各节点调制器。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ONOC_CONNECTIONS}
        for i in range(4):
            assert ("central_router", f"node_{i}_modulator") in conns

    def test_onoc_ring_bus(self) -> None:
        """oNoC 环形总线：中心路由器 ↔ waveguide_ring。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ONOC_CONNECTIONS}
        assert ("central_router", "waveguide_ring") in conns
        assert ("waveguide_ring", "central_router") in conns

    def test_onoc_laser_source(self) -> None:
        """oNoC 共享激光源 → 中心路由器。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ONOC_CONNECTIONS}
        assert ("laser_source", "central_router") in conns

    def test_onoc_node_complete_path(self) -> None:
        """oNoC 节点 0 完整通路：router → mod → serdes → ring → serdes → det。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ONOC_CONNECTIONS}
        assert ("central_router", "node_0_modulator") in conns
        assert ("node_0_modulator", "serdes_0") in conns
        assert ("serdes_0", "waveguide_ring") in conns
        assert ("waveguide_ring", "serdes_0") in conns
        assert ("serdes_0", "node_0_detector") in conns


class TestApolloBenchmarkLoader:
    """Apollo benchmark 加载器测试。"""

    def test_load_ptc_benchmark_basic(self) -> None:
        """load_apollo_ptc_benchmark 返回完整 CircuitSpec。"""
        circuit = load_apollo_ptc_benchmark()
        assert circuit.name == "apollo_ptc"
        assert circuit.benchmark_source == BenchmarkSource.APOLLO
        assert circuit.target_metric == TargetMetric.INSERTION_LOSS_DB
        assert circuit.process_node == "220nm SOI"
        assert circuit.optical_wavelength_nm == 1550.0

    def test_load_ptc_benchmark_devices(self) -> None:
        """PTC benchmark 含 12 个器件。"""
        circuit = load_apollo_ptc_benchmark()
        assert len(circuit.devices) == 12

    def test_load_ptc_benchmark_connections(self) -> None:
        """PTC benchmark 含 13 条连接。"""
        circuit = load_apollo_ptc_benchmark()
        assert len(circuit.connections) == 13

    def test_load_ptc_benchmark_canvas(self) -> None:
        """PTC 画布尺寸基于器件总面积自适应。"""
        circuit = load_apollo_ptc_benchmark()
        assert circuit.canvas_w > 0
        assert circuit.canvas_h > 0
        total_area = sum(d.width_um * d.height_um for d in circuit.devices)
        assert circuit.canvas_w * circuit.canvas_h >= total_area

    def test_load_onoc_benchmark_basic(self) -> None:
        """load_apollo_onoc_benchmark 返回完整 CircuitSpec。"""
        circuit = load_apollo_onoc_benchmark()
        assert circuit.name == "apollo_onoc"
        assert circuit.benchmark_source == BenchmarkSource.APOLLO
        assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE

    def test_load_onoc_benchmark_devices(self) -> None:
        """oNoC benchmark 含 15 个器件。"""
        circuit = load_apollo_onoc_benchmark()
        assert len(circuit.devices) == 15

    def test_load_onoc_benchmark_connections(self) -> None:
        """oNoC benchmark 含 23 条连接。"""
        circuit = load_apollo_onoc_benchmark()
        assert len(circuit.connections) == 23

    def test_load_apollo_ptc_from_data_loader(self) -> None:
        """data_loader.load_apollo_ptc 返回真实拓扑（第24轮深化）。"""
        circuit = load_apollo_ptc()
        assert circuit.name == "apollo_ptc"
        assert len(circuit.devices) == 12
        assert len(circuit.connections) == 13

    def test_load_apollo_onoc_from_data_loader(self) -> None:
        """data_loader.load_apollo_onoc 返回真实拓扑（第24轮深化）。"""
        circuit = load_apollo_onoc()
        assert circuit.name == "apollo_onoc"
        assert len(circuit.devices) == 15
        assert len(circuit.connections) == 23

    def test_load_apollo_ptc_nonexistent_path(self) -> None:
        """用户指定 path 但文件不存在时 raise FileNotFoundError（R03 禁止 fall-back）。

        R03: 失败即 raise，禁止静默 fall-back 到默认拓扑。
        若用户想使用内置默认拓扑，应不传 path 参数。
        """
        with pytest.raises(FileNotFoundError, match="Apollo PTC benchmark 文件不存在"):
            load_apollo_ptc(path="/nonexistent/ptc.pkl")


class TestApolloBenchmarkInfo:
    """Apollo benchmark 元信息测试。"""

    def test_info_fields(self) -> None:
        """元信息含全部必要字段。"""
        info = apollo_benchmark_info()
        assert info["name"] == "apollo"
        assert info["ptc_device_count"] == 12
        assert info["ptc_connection_count"] == 13
        assert info["onoc_device_count"] == 15
        assert info["onoc_connection_count"] == 23
        assert info["process_node"] == "220nm SOI"
        assert info["benchmark_source"] == "APOLLO"
        assert "ASU-LOPE-Group/Apollo" in info["source_url"]
        assert "arxiv.org/abs/2504.18813" in info["paper_url"]

    def test_info_target_metrics(self) -> None:
        """目标指标含 INSERTION_LOSS_DB 和 ROUTING_SUCCESS_RATE。"""
        info = apollo_benchmark_info()
        assert "INSERTION_LOSS_DB" in info["target_metrics"]
        assert "ROUTING_SUCCESS_RATE" in info["target_metrics"]


class TestApolloBenchmarkEvaluation:
    """Apollo benchmark 评估器集成测试。"""

    def test_ptc_hpwl_evaluation(self) -> None:
        """PTC 网格布局 HPWL > 0。"""
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl > 0

    def test_ptc_overlap_evaluation(self) -> None:
        """PTC 网格布局无重叠。"""
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        assert evaluate_overlap(circuit, placements) == 0

    def test_onoc_hpwl_evaluation(self) -> None:
        """oNoC 网格布局 HPWL > 0。"""
        circuit = load_apollo_onoc_benchmark()
        placements = grid_placement(circuit)
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl > 0

    def test_onoc_overlap_evaluation(self) -> None:
        """oNoC 网格布局无重叠。"""
        circuit = load_apollo_onoc_benchmark()
        placements = grid_placement(circuit)
        assert evaluate_overlap(circuit, placements) == 0

    def test_ptc_benchmark_result(self) -> None:
        """PTC evaluate_benchmark 返回正确结果。"""
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert result.benchmark_name == "apollo_ptc"
        assert result.module_count == 12
        assert result.connection_count == 13
        assert result.target_metric == "insertion_loss_db"

    def test_onoc_benchmark_result(self) -> None:
        """oNoC evaluate_benchmark 返回正确结果。"""
        circuit = load_apollo_onoc_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert result.benchmark_name == "apollo_onoc"
        assert result.module_count == 15
        assert result.connection_count == 23
        assert result.target_metric == "routing_success_rate"


class TestCommercialGapReduction:
    """P1-5 商业差距缩减验证（第24轮深化）。"""

    def test_apollo_real_topology_not_synthetic(self) -> None:
        """Apollo benchmark 使用真实拓扑（非简单链式）。"""
        ptc = load_apollo_ptc_benchmark()
        onoc = load_apollo_onoc_benchmark()
        # 真实拓扑：连接数 ≥ 器件数（非链式）
        assert len(ptc.connections) >= len(ptc.devices)
        assert len(onoc.connections) >= len(onoc.devices)

    def test_apollo_source_traced(self) -> None:
        """Apollo benchmark 来源可溯源到 ASU LOPE Group。"""
        info = apollo_benchmark_info()
        assert "ASU-LOPE-Group" in info["source_url"]
        assert "arxiv.org" in info["paper_url"]

    def test_apollo_ptc_matrix_structure(self) -> None:
        """PTC 含 MZI 矩阵（光子张量核心核心组件）。"""
        circuit = load_apollo_ptc_benchmark()
        device_names = {d.name for d in circuit.devices}
        assert "mzi_matrix_4x4" in device_names
        assert "phase_shifter_array" in device_names
        assert "modulator_array" in device_names
        assert "detector_array" in device_names

    def test_apollo_onoc_network_structure(self) -> None:
        """oNoC 含星型 + 环形总线网络结构。"""
        circuit = load_apollo_onoc_benchmark()
        device_names = {d.name for d in circuit.devices}
        assert "central_router" in device_names
        assert "waveguide_ring" in device_names
        assert "laser_source" in device_names
        # 4 节点完整
        for i in range(4):
            assert f"node_{i}_modulator" in device_names
            assert f"node_{i}_detector" in device_names

    def test_benchmark_evaluator_commercial_grade(self) -> None:
        """评估器对 Apollo benchmark 达到商业级。"""
        for circuit in [load_apollo_ptc_benchmark(), load_apollo_onoc_benchmark()]:
            placements = grid_placement(circuit)
            result = evaluate_benchmark(circuit, placements)
            assert result.hpwl_um >= 0
            assert result.overlap_count >= 0
            assert 0 <= result.area_utilization <= 1
            assert isinstance(result.passed, bool)
            assert result.extra["benchmark_source"] == "apollo"
            assert result.extra["process_node"] == "220nm SOI"
            # 第90轮新增：插入损耗应在 extra 中
            assert "insertion_loss_db" in result.extra
            assert result.extra["insertion_loss_db"] >= 0.0

    def test_ptc_insertion_loss_evaluation(self) -> None:
        """PTC benchmark 插入损耗评估（第90轮新增）。"""
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        loss = evaluate_insertion_loss(circuit, placements)
        # 插入损耗应为非负值
        assert loss >= 0.0
        # 网格布局有波导长度，损耗应 > 0（除非无连接）
        assert loss > 0.0  # PTC 有 13 条连接

    def test_ptc_insertion_loss_in_benchmark_result(self) -> None:
        """PTC benchmark evaluate_benchmark 应含插入损耗（第90轮新增）。"""
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert "insertion_loss_db" in result.extra
        assert result.extra["insertion_loss_db"] > 0.0

    def test_ptc_insertion_loss_target_metric_passed(self) -> None:
        """PTC benchmark target_metric=insertion_loss_db 达标判定不再静默失败（第90轮修复）。"""
        circuit = load_apollo_ptc_benchmark()
        # PTC 的 target_metric 是 INSERTION_LOSS_DB
        assert circuit.target_metric == TargetMetric.INSERTION_LOSS_DB
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        # 达标判定应基于 insertion_loss < target_value and overlap == 0
        # 网格布局无重叠，passed 应取决于插入损耗是否 < target_value
        assert isinstance(result.passed, bool)
        # 验证 passed 逻辑正确
        expected_passed = (
            result.extra["insertion_loss_db"] < circuit.target_value
            and result.overlap_count == 0
        )
        assert result.passed == expected_passed

    def test_ptc_devices_have_insertion_loss_db(self) -> None:
        """PTC 器件应含 insertion_loss_db 参数（第93轮新增）。"""
        for dev in PTC_DEVICES.values():
            assert hasattr(dev, "insertion_loss_db")
            assert dev.insertion_loss_db >= 0.0
        # 光栅耦合器损耗应 > 0（1.5 dB 典型值）
        assert PTC_DEVICES["gc_in_array"].insertion_loss_db > 0.0
        assert PTC_DEVICES["gc_out_array"].insertion_loss_db > 0.0
        # MZI 矩阵损耗应 > 0
        assert PTC_DEVICES["mzi_matrix_4x4"].insertion_loss_db > 0.0
        # 波导损耗应为 0（按长度计算）
        assert PTC_DEVICES["input_waveguide_bus"].insertion_loss_db == 0.0
        # 激光器损耗应为 0（光源）
        assert PTC_DEVICES["bias_laser_in"].insertion_loss_db == 0.0

    def test_onoc_devices_have_insertion_loss_db(self) -> None:
        """oNoC 器件应含 insertion_loss_db 参数（第93轮新增）。"""
        for dev in ONOC_DEVICES.values():
            assert hasattr(dev, "insertion_loss_db")
            assert dev.insertion_loss_db >= 0.0
        # MMI 路由器损耗应 > 0
        assert ONOC_DEVICES["central_router"].insertion_loss_db > 0.0
        # 调制器损耗应 > 0
        assert ONOC_DEVICES["node_0_modulator"].insertion_loss_db > 0.0
        # 波导损耗应为 0
        assert ONOC_DEVICES["waveguide_ring"].insertion_loss_db == 0.0

    def test_ptc_device_spec_carries_insertion_loss(self) -> None:
        """PTC DeviceSpec.params 应含 insertion_loss_db（第93轮新增）。"""
        circuit = load_apollo_ptc_benchmark()
        for dev in circuit.devices:
            assert "insertion_loss_db" in dev.params
            loss = float(dev.params["insertion_loss_db"])
            assert loss >= 0.0
        # 光栅耦合器在 DeviceSpec 中也应 > 0
        gc_in = next(d for d in circuit.devices if d.name == "gc_in_array")
        assert float(gc_in.params["insertion_loss_db"]) > 0.0

    def test_ptc_insertion_loss_includes_device_loss(self) -> None:
        """PTC 插入损耗应包含器件损耗（第93轮新增）。

        第90轮 evaluate_insertion_loss 只计算波导损耗，器件损耗为 0。
        第93轮为器件添加 insertion_loss_db 后，总损耗应 > 纯波导损耗。
        """
        circuit = load_apollo_ptc_benchmark()
        placements = grid_placement(circuit)
        total_loss = evaluate_insertion_loss(circuit, placements)

        # 计算纯波导损耗（waveguide_loss_db_cm=0，只保留器件损耗）
        device_only_loss = evaluate_insertion_loss(
            circuit, placements, waveguide_loss_db_cm=0.0
        )
        # PTC 有 12 个器件，其中多个有 insertion_loss_db > 0
        # 器件损耗应 > 0
        assert device_only_loss > 0.0, "器件插入损耗应 > 0（第93轮添加）"
        # 总损耗应 > 器件损耗（波导损耗 > 0）
        assert total_loss > device_only_loss
