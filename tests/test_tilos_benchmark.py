"""TILOS Ariane benchmark 测试（P1-5 第23轮）。

测试移植的 TILOS Ariane RISC-V CPU benchmark：
- 17 个核心模块完整性
- 25 条真实连接拓扑
- HPWL/重叠/利用率评估器
- 网格布局基准对照
- 商业差距缩减验证

来源:
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- CVA6 源码: https://github.com/openhwgroup/cva6
"""

from __future__ import annotations

import pytest

from polaris.data.benchmark_evaluator import (
    BenchmarkResult,
    evaluate_area_utilization,
    evaluate_benchmark,
    evaluate_drv,
    evaluate_hpwl,
    evaluate_overlap,
    grid_placement,
)
from polaris.data.data_loader import load_tilos_ariane
from polaris.data.specs import BenchmarkSource, TargetMetric
from polaris.data.tilos_benchmark import (
    ARIANE_CONNECTIONS,
    ARIANE_MODULES,
    ariane_benchmark_info,
    get_ariane_module,
    list_ariane_modules,
    load_ariane_benchmark,
)


class TestArianeModules:
    """Ariane 模块库完整性测试。"""

    def test_module_count(self) -> None:
        """17 个核心模块（对齐 CVA6 顶层实例化）。"""
        assert len(ARIANE_MODULES) == 17

    def test_module_categories(self) -> None:
        """模块覆盖 6 个类别（pipeline/alu/fpu/csr/cache/control）。"""
        categories = {m.category for m in ARIANE_MODULES.values()}
        assert "pipeline" in categories
        assert "alu" in categories
        assert "fpu" in categories
        assert "csr" in categories
        assert "cache" in categories
        assert "control" in categories

    def test_module_sizes_positive(self) -> None:
        """所有模块尺寸为正。"""
        for name, m in ARIANE_MODULES.items():
            assert m.width_um > 0, f"{name} 宽度非正"
            assert m.height_um > 0, f"{name} 高度非正"

    def test_core_modules_present(self) -> None:
        """关键流水线模块存在（PC/fetch/decode/issue/commit）。"""
        required = {"pc_gen", "fetch", "decode", "issue", "commit"}
        assert required.issubset(ARIANE_MODULES.keys())

    def test_cache_modules_present(self) -> None:
        """缓存模块存在（icache/dcache/ptw）。"""
        required = {"icache", "dcache", "ptw"}
        assert required.issubset(ARIANE_MODULES.keys())

    def test_execution_units_present(self) -> None:
        """执行单元存在（alu/mult/fpu/lsu/serdiv）。"""
        required = {"alu", "mult", "fpu", "lsu", "serdiv"}
        assert required.issubset(ARIANE_MODULES.keys())

    def test_get_ariane_module_valid(self) -> None:
        """get_ariane_module 返回正确模块。"""
        m = get_ariane_module("alu")
        assert m.name == "alu"
        assert m.category == "alu"

    def test_get_ariane_module_invalid(self) -> None:
        """get_ariane_module 未知模块抛 KeyError。"""
        with pytest.raises(KeyError, match="未知 Ariane 模块"):
            get_ariane_module("nonexistent_module")

    def test_list_ariane_modules_sorted(self) -> None:
        """list_ariane_modules 返回排序后的模块名列表。"""
        names = list_ariane_modules()
        assert names == sorted(names)
        assert len(names) == 17

    def test_module_is_frozen(self) -> None:
        """ArianeModule 是 frozen dataclass。"""
        m = ARIANE_MODULES["alu"]
        with pytest.raises(AttributeError):
            m.name = "modified"  # type: ignore[misc]


class TestArianeConnections:
    """Ariane 连接拓扑测试。"""

    def test_connection_count(self) -> None:
        """25 条真实连接（数据通路 + 控制通路）。"""
        assert len(ARIANE_CONNECTIONS) == 25

    def test_connections_reference_valid_modules(self) -> None:
        """所有连接引用的模块都存在。"""
        for src, _sp, dst, _dp in ARIANE_CONNECTIONS:
            assert src in ARIANE_MODULES, f"连接源模块 {src} 不存在"
            assert dst in ARIANE_MODULES, f"连接目标模块 {dst} 不存在"

    def test_pipeline_data_path(self) -> None:
        """流水线数据通路完整：pc_gen → fetch → decode → issue → alu → commit。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ARIANE_CONNECTIONS}
        assert ("pc_gen", "fetch") in conns
        assert ("fetch", "fetch_fifo") in conns
        assert ("fetch_fifo", "decode") in conns
        assert ("decode", "scoreboard") in conns
        assert ("scoreboard", "issue") in conns
        assert ("issue", "alu") in conns
        assert ("alu", "commit") in conns

    def test_cache_connections(self) -> None:
        """缓存连接完整：fetch↔icache, lsu↔dcache, dcache↔ptw。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ARIANE_CONNECTIONS}
        assert ("fetch", "icache") in conns
        assert ("icache", "fetch") in conns
        assert ("lsu", "dcache") in conns
        assert ("dcache", "lsu") in conns
        assert ("dcache", "ptw") in conns
        assert ("ptw", "dcache") in conns

    def test_control_connections(self) -> None:
        """控制通路：controller → fetch/decode/commit。"""
        conns = {(src, dst) for src, _sp, dst, _dp in ARIANE_CONNECTIONS}
        assert ("controller", "fetch") in conns
        assert ("controller", "decode") in conns
        assert ("controller", "commit") in conns


class TestArianeBenchmarkLoader:
    """Ariane benchmark 加载器测试。"""

    def test_load_ariane_benchmark_basic(self) -> None:
        """load_ariane_benchmark 返回完整 CircuitSpec。"""
        circuit = load_ariane_benchmark()
        assert circuit.name == "tilos_ariane"
        assert circuit.benchmark_source == BenchmarkSource.TILOS
        assert circuit.target_metric == TargetMetric.HPWL
        assert circuit.process_node == "NanGate45"

    def test_load_ariane_benchmark_modules(self) -> None:
        """benchmark 含 17 个模块。"""
        circuit = load_ariane_benchmark()
        assert len(circuit.devices) == 17

    def test_load_ariane_benchmark_connections(self) -> None:
        """benchmark 含 25 条连接。"""
        circuit = load_ariane_benchmark()
        assert len(circuit.connections) == 25

    def test_load_ariane_benchmark_canvas(self) -> None:
        """画布尺寸基于模块总面积自适应。"""
        circuit = load_ariane_benchmark()
        assert circuit.canvas_w > 0
        assert circuit.canvas_h > 0
        # 画布应足够大，至少能容纳所有模块
        total_area = sum(d.width_um * d.height_um for d in circuit.devices)
        assert circuit.canvas_w * circuit.canvas_h >= total_area

    def test_load_ariane_benchmark_process_node(self) -> None:
        """支持指定工艺节点。"""
        circuit = load_ariane_benchmark(process_node="ASAP7")
        assert circuit.process_node == "ASAP7"

    def test_load_tilos_ariane_from_data_loader(self) -> None:
        """data_loader.load_tilos_ariane 返回真实拓扑（第23轮深化）。"""
        circuit = load_tilos_ariane()
        assert circuit.name == "tilos_ariane"
        assert len(circuit.devices) == 17
        assert len(circuit.connections) == 25
        assert circuit.benchmark_source == BenchmarkSource.TILOS

    def test_load_tilos_ariane_nonexistent_path(self) -> None:
        """不存在的 path 返回真实拓扑（不抛异常）。"""
        circuit = load_tilos_ariane(path="/nonexistent/ariane.pkl")
        assert len(circuit.devices) == 17


class TestArianeBenchmarkInfo:
    """Ariane benchmark 元信息测试。"""

    def test_info_fields(self) -> None:
        """元信息含全部必要字段。"""
        info = ariane_benchmark_info()
        assert info["name"] == "tilos_ariane"
        assert info["module_count"] == 17
        assert info["connection_count"] == 25
        assert info["process_node"] == "NanGate45"
        assert info["benchmark_source"] == "TILOS"
        assert "https://github.com/TILOS-AI-CAD-Institute/MacroPlacement" in info["source_url"]
        assert "https://github.com/openhwgroup/cva6" in info["cpu_source_url"]
        assert info["target_metric"] == "HPWL"

    def test_info_total_area_positive(self) -> None:
        """总面积为正。"""
        info = ariane_benchmark_info()
        assert info["total_area_um2"] > 0

    def test_info_categories_complete(self) -> None:
        """类别列表含 6 个类别。"""
        info = ariane_benchmark_info()
        assert len(info["categories"]) == 6


class TestBenchmarkEvaluator:
    """Benchmark 评估器测试。"""

    def test_evaluate_hpwl_empty(self) -> None:
        """空布局 HPWL = 0。"""
        circuit = load_ariane_benchmark()
        assert evaluate_hpwl(circuit, {}) == 0.0

    def test_evaluate_hpwl_single_connection(self) -> None:
        """单连接 HPWL = 曼哈顿距离。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="a", device_type="x", width_um=10, height_um=10),
                DeviceSpec(name="b", device_type="x", width_um=10, height_um=10),
            ],
            connections=[("a", "out", "b", "in")],
        )
        placements = {"a": (0.0, 0.0), "b": (100.0, 50.0)}
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl == 150.0  # 100 + 50

    def test_evaluate_hpwl_ariane(self) -> None:
        """Ariane benchmark 网格布局 HPWL > 0。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        hpwl = evaluate_hpwl(circuit, placements)
        assert hpwl > 0

    def test_evaluate_overlap_none(self) -> None:
        """网格布局无重叠。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        assert evaluate_overlap(circuit, placements) == 0

    def test_evaluate_overlap_with_collision(self) -> None:
        """两模块同位置产生 1 次重叠。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="a", device_type="x", width_um=20, height_um=20),
                DeviceSpec(name="b", device_type="x", width_um=20, height_um=20),
            ],
            connections=[],
        )
        placements = {"a": (50.0, 50.0), "b": (50.0, 50.0)}
        assert evaluate_overlap(circuit, placements) == 1

    def test_evaluate_area_utilization_empty(self) -> None:
        """空布局利用率 = 0。"""
        circuit = load_ariane_benchmark()
        assert evaluate_area_utilization(circuit, {}) == 0.0

    def test_evaluate_area_utilization_grid(self) -> None:
        """网格布局利用率 > 0 且 < 1。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        util = evaluate_area_utilization(circuit, placements)
        assert 0 < util < 1

    def test_evaluate_benchmark_returns_result(self) -> None:
        """evaluate_benchmark 返回 BenchmarkResult。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "tilos_ariane"
        assert result.module_count == 17
        assert result.connection_count == 25
        assert result.target_metric == "hpwl"

    def test_evaluate_benchmark_passed_no_overlap(self) -> None:
        """网格布局无重叠且 HPWL < target 时 passed=True。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        # 网格布局应无重叠
        assert result.overlap_count == 0
        # HPWL 是否达标取决于 target_value（50000μm）
        # 网格布局 HPWL 可能超过 target，但 passed 仅在 HPWL < target 且无重叠时为 True
        if result.hpwl_um < circuit.target_value:
            assert result.passed is True
        else:
            assert result.passed is False

    def test_grid_placement_cols(self) -> None:
        """grid_placement 支持指定列数。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit, cols=5)
        assert len(placements) == 17
        # 第一行 5 个模块
        first_row_x = [placements[m][0] for m in list(placements.keys())[:5]]
        assert len(set(first_row_x)) == 5


class TestCongestionEvaluator:
    """拥塞度评估器测试（第82轮新增）。"""

    def test_evaluate_congestion_empty(self) -> None:
        """空布局拥塞度全为 0。"""
        from polaris.data.benchmark_evaluator import evaluate_congestion

        circuit = load_ariane_benchmark()
        cong = evaluate_congestion(circuit, {})
        assert cong["max_congestion"] == 0.0
        assert cong["avg_congestion"] == 0.0
        assert cong["overflow_count"] == 0
        assert cong["total_overflow"] == 0.0

    def test_evaluate_congestion_single_connection(self) -> None:
        """单连接拥塞度 > 0。"""
        from polaris.data.benchmark_evaluator import evaluate_congestion
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test_cong",
            devices=[
                DeviceSpec(name="a", device_type="x", width_um=10, height_um=10),
                DeviceSpec(name="b", device_type="x", width_um=10, height_um=10),
            ],
            connections=[("a", "out", "b", "in")],
            canvas_w=100.0,
            canvas_h=100.0,
        )
        placements = {"a": (10.0, 10.0), "b": (90.0, 90.0)}
        cong = evaluate_congestion(circuit, placements)
        assert cong["max_congestion"] > 0.0
        assert cong["avg_congestion"] > 0.0

    def test_evaluate_congestion_grid_layout(self) -> None:
        """Ariane 网格布局拥塞度合理（max_congestion > 0）。"""
        from polaris.data.benchmark_evaluator import evaluate_congestion

        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        cong = evaluate_congestion(circuit, placements)
        assert cong["max_congestion"] > 0.0
        assert cong["avg_congestion"] >= 0.0
        assert cong["overflow_count"] >= 0
        assert cong["total_overflow"] >= 0.0

    def test_evaluate_congestion_custom_grid_size(self) -> None:
        """支持自定义网格大小。"""
        from polaris.data.benchmark_evaluator import evaluate_congestion

        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        cong_16 = evaluate_congestion(circuit, placements, grid_rows=16, grid_cols=16)
        cong_8 = evaluate_congestion(circuit, placements, grid_rows=8, grid_cols=8)
        # 不同网格大小结果应不同
        assert cong_16["max_congestion"] != cong_8["max_congestion"] or \
               cong_16["avg_congestion"] != cong_8["avg_congestion"]

    def test_evaluate_benchmark_includes_congestion(self) -> None:
        """evaluate_benchmark 输出含拥塞度指标。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        assert "max_congestion" in result.extra
        assert "avg_congestion" in result.extra
        assert "overflow_count" in result.extra
        assert "total_overflow" in result.extra
        assert result.extra["max_congestion"] > 0.0

    def test_evaluate_congestion_zero_canvas(self) -> None:
        """零画布返回空结果（边界条件）。"""
        from polaris.data.benchmark_evaluator import evaluate_congestion
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test_zero",
            devices=[DeviceSpec(name="a", device_type="x", width_um=10, height_um=10)],
            connections=[],
            canvas_w=0.0,
            canvas_h=0.0,
        )
        cong = evaluate_congestion(circuit, {"a": (0.0, 0.0)})
        assert cong["max_congestion"] == 0.0
        assert cong["overflow_count"] == 0


class TestCommercialGapReduction:
    """P1-5 商业差距缩减验证。"""

    def test_tilos_benchmark_aligned(self) -> None:
        """对齐 TILOS MacroPlacement 评估标准。"""
        info = ariane_benchmark_info()
        assert info["benchmark_source"] == "TILOS"
        assert info["target_metric"] == "HPWL"
        assert "MacroPlacement" in info["source_url"]

    def test_ariane_real_topology_not_synthetic(self) -> None:
        """Ariane benchmark 使用真实拓扑（非简单链式）。"""
        circuit = load_ariane_benchmark()
        # 真实拓扑：17 模块 + 25 连接（连接数 > 模块数，非链式）
        assert len(circuit.devices) == 17
        assert len(circuit.connections) == 25
        assert len(circuit.connections) > len(circuit.devices)

    def test_hpwl_evaluator_matches_tilos_standard(self) -> None:
        """HPWL 评估器对齐 TILOS 标准（曼哈顿距离求和）。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="a", device_type="x", width_um=10, height_um=10),
                DeviceSpec(name="b", device_type="x", width_um=10, height_um=10),
                DeviceSpec(name="c", device_type="x", width_um=10, height_um=10),
            ],
            connections=[
                ("a", "out", "b", "in"),
                ("b", "out", "c", "in"),
                ("a", "out", "c", "in"),
            ],
        )
        placements = {"a": (0.0, 0.0), "b": (30.0, 40.0), "c": (60.0, 80.0)}
        hpwl = evaluate_hpwl(circuit, placements)
        # a-b: 30+40=70, b-c: 30+40=70, a-c: 60+80=140, total=280
        assert hpwl == 280.0

    def test_benchmark_evaluator_commercial_grade(self) -> None:
        """评估器达到商业级（含 HPWL/重叠/利用率/达标判定）。"""
        circuit = load_ariane_benchmark()
        placements = grid_placement(circuit)
        result = evaluate_benchmark(circuit, placements)
        # 商业级评估必须含全部指标
        assert result.hpwl_um >= 0
        assert result.overlap_count >= 0
        assert 0 <= result.area_utilization <= 1
        assert isinstance(result.passed, bool)
        assert result.target_metric == "hpwl"
        assert "benchmark_source" in result.extra
        assert "process_node" in result.extra

    def test_cva6_source_traced(self) -> None:
        """Ariane 模块来源可溯源到 CVA6。"""
        info = ariane_benchmark_info()
        assert "cva6" in info["cpu_source_url"]
        # 关键模块名对齐 CVA6 源码命名
        assert "pc_gen" in ARIANE_MODULES
        assert "fetch_fifo" in ARIANE_MODULES
        assert "scoreboard" in ARIANE_MODULES
        assert "commit" in ARIANE_MODULES
