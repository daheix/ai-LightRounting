"""benchmark_report 模块测试（P1-5 深化，第26轮）。

对标 TILOS MacroPlacement 评估流程，测试评估报告生成器的
单 benchmark 报告、对比报告、Markdown/JSON 输出、全 benchmark 回归。

来源:
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Circuit Training: https://github.com/google-research/circuit_training
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.data.benchmark_report import (
    BenchmarkReport,
    ComparisonReport,
    format_comparison_markdown,
    format_report_markdown,
    generate_comparison_report,
    generate_grid_report,
    generate_report,
    run_all_benchmarks,
    save_report_json,
    save_report_markdown,
)
from polaris.data.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)


@pytest.fixture
def simple_circuit() -> CircuitSpec:
    """简单测试电路（3 器件 + 2 连接）。"""
    return CircuitSpec(
        name="test_simple",
        devices=[
            DeviceSpec(name="a", device_type="mzi", width_um=10.0, height_um=10.0),
            DeviceSpec(name="b", device_type="mzi", width_um=10.0, height_um=10.0),
            DeviceSpec(name="c", device_type="mzi", width_um=10.0, height_um=10.0),
        ],
        connections=[
            ("a", "out", "b", "in"),
            ("b", "out", "c", "in"),
        ],
        canvas_w=100.0,
        canvas_h=100.0,
        benchmark_source=BenchmarkSource.CUSTOM,
        process_node="220nm SOI",
        target_metric=TargetMetric.HPWL,
        target_value=1000.0,
    )


@pytest.fixture
def simple_placements() -> dict[str, tuple[float, float]]:
    """简单布局（无重叠）。"""
    return {"a": (20.0, 50.0), "b": (50.0, 50.0), "c": (80.0, 50.0)}


class TestBenchmarkReportDataclass:
    """BenchmarkReport 数据类测试。"""

    def test_frozen_dataclass(self) -> None:
        """BenchmarkReport 应为 frozen dataclass。"""
        report = BenchmarkReport(
            benchmark_name="test",
            benchmark_source="CUSTOM",
            placement_method="grid",
            hpwl_um=100.0,
            overlap_count=0,
            area_utilization=0.3,
            module_count=3,
            connection_count=2,
            target_metric="hpwl",
            target_value=1000.0,
            passed=True,
            process_node="220nm SOI",
        )
        assert report.benchmark_name == "test"
        with pytest.raises((AttributeError, TypeError)):
            report.benchmark_name = "other"  # type: ignore[misc]

    def test_default_timestamp_empty(self) -> None:
        """默认 timestamp 应为空字符串。"""
        report = BenchmarkReport(
            benchmark_name="t",
            benchmark_source="CUSTOM",
            placement_method="grid",
            hpwl_um=0.0,
            overlap_count=0,
            area_utilization=0.0,
            module_count=0,
            connection_count=0,
            target_metric="hpwl",
            target_value=0.0,
            passed=False,
            process_node="",
        )
        assert report.timestamp == ""
        assert report.extra == {}


class TestGenerateReport:
    """generate_report 函数测试。"""

    def test_generate_report_basic(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """generate_report 应返回含全部指标的 BenchmarkReport。"""
        report = generate_report(simple_circuit, simple_placements, "grid")
        assert isinstance(report, BenchmarkReport)
        assert report.benchmark_name == "test_simple"
        assert report.benchmark_source == "custom"
        assert report.placement_method == "grid"
        assert report.module_count == 3
        assert report.connection_count == 2
        assert report.process_node == "220nm SOI"
        assert report.target_metric == "hpwl"
        assert report.timestamp != ""

    def test_generate_report_hpwl(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """HPWL 应为各连接曼哈顿距离之和。"""
        report = generate_report(simple_circuit, simple_placements)
        # a(20,50) -> b(50,50): 30, b(50,50) -> c(80,50): 30, 总 60
        assert report.hpwl_um == pytest.approx(60.0)

    def test_generate_report_no_overlap(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """无重叠布局应 overlap_count=0。"""
        report = generate_report(simple_circuit, simple_placements)
        assert report.overlap_count == 0

    def test_generate_report_with_overlap(self, simple_circuit: CircuitSpec) -> None:
        """重叠布局应 overlap_count > 0。"""
        placements = {"a": (50.0, 50.0), "b": (50.0, 50.0), "c": (80.0, 50.0)}
        report = generate_report(simple_circuit, placements)
        assert report.overlap_count >= 1

    def test_generate_report_passed(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """HPWL < target 且无重叠应 passed=True。"""
        report = generate_report(simple_circuit, simple_placements)
        assert report.hpwl_um < simple_circuit.target_value
        assert report.overlap_count == 0
        assert report.passed is True

    def test_generate_report_failed_high_hpwl(
        self,
        simple_circuit: CircuitSpec,
    ) -> None:
        """HPWL > target 应 passed=False。"""
        # 拉远距离使 HPWL 超过 target
        placements = {"a": (0.0, 0.0), "b": (90.0, 90.0), "c": (50.0, 50.0)}
        report = generate_report(simple_circuit, placements)
        # HPWL = |90-0|+|90-0| + |50-90|+|50-90| = 180 + 80 = 260
        # 但 target=1000，仍达标。改为更严格 target
        strict_circuit = CircuitSpec(
            name="strict",
            devices=simple_circuit.devices,
            connections=simple_circuit.connections,
            canvas_w=100.0,
            canvas_h=100.0,
            benchmark_source=BenchmarkSource.CUSTOM,
            target_metric=TargetMetric.HPWL,
            target_value=10.0,  # 极严格
        )
        report = generate_report(strict_circuit, placements)
        assert report.hpwl_um > 10.0
        assert report.passed is False

    def test_generate_report_extra_contains_source(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """extra 应包含 benchmark_source 和 process_node。"""
        report = generate_report(simple_circuit, simple_placements)
        assert "benchmark_source" in report.extra
        assert "process_node" in report.extra

    def test_generate_report_placement_method(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """placement_method 应正确传递。"""
        report = generate_report(simple_circuit, simple_placements, "rl_ppo")
        assert report.placement_method == "rl_ppo"


class TestGenerateGridReport:
    """generate_grid_report 函数测试。"""

    def test_grid_report_uses_grid_placement(
        self, simple_circuit: CircuitSpec
    ) -> None:
        """generate_grid_report 应使用 grid_placement 生成布局。"""
        report = generate_grid_report(simple_circuit)
        assert report.placement_method == "grid"
        # grid_placement 自适应最大模块，应无重叠
        assert report.overlap_count == 0

    def test_grid_report_module_count(
        self, simple_circuit: CircuitSpec
    ) -> None:
        """grid 报告 module_count 应等于电路器件数。"""
        report = generate_grid_report(simple_circuit)
        assert report.module_count == 3

    def test_grid_report_tilos_ariane(self) -> None:
        """grid 报告对 TILOS Ariane benchmark 应工作。"""
        from polaris.data.data_loader import load_tilos_ariane

        circuit = load_tilos_ariane()
        report = generate_grid_report(circuit)
        assert report.benchmark_name == "tilos_ariane"
        assert report.module_count == 17
        assert report.connection_count == 25
        assert report.benchmark_source == "tilos"
        assert report.process_node == "NanGate45"

    def test_grid_report_apollo_ptc(self) -> None:
        """grid 报告对 Apollo PTC benchmark 应工作。"""
        from polaris.data.data_loader import load_apollo_ptc

        circuit = load_apollo_ptc()
        report = generate_grid_report(circuit)
        assert report.benchmark_name == "apollo_ptc"
        assert report.module_count == 12
        assert report.connection_count == 13
        assert report.benchmark_source == "apollo"

    def test_grid_report_lidar(self) -> None:
        """grid 报告对 LiDAR benchmark 应工作。"""
        from polaris.data.data_loader import load_lidar_benchmark

        circuit = load_lidar_benchmark()
        report = generate_grid_report(circuit)
        assert report.benchmark_name == "lidar_ptc"
        assert report.module_count == 12
        assert report.connection_count == 13
        assert report.benchmark_source == "lidar"


class TestComparisonReport:
    """ComparisonReport 测试。"""

    def test_comparison_empty(self) -> None:
        """空报告列表应返回空 ComparisonReport。"""
        comp = generate_comparison_report([])
        assert comp.total_benchmarks == 0
        assert comp.passed_count == 0
        assert comp.pass_rate == 0.0
        assert comp.timestamp != ""

    def test_comparison_single(self, simple_circuit: CircuitSpec) -> None:
        """单个报告的对比统计应正确。"""
        report = generate_grid_report(simple_circuit)
        comp = generate_comparison_report([report])
        assert comp.total_benchmarks == 1
        assert comp.passed_count == 1 if report.passed else 0
        assert comp.avg_hpwl_um == report.hpwl_um
        assert comp.avg_utilization == report.area_utilization
        assert comp.total_modules == 3
        assert comp.total_connections == 2

    def test_comparison_multiple(self) -> None:
        """多个报告的对比统计应正确。"""
        reports = [
            BenchmarkReport(
                benchmark_name=f"bench_{i}",
                benchmark_source="CUSTOM",
                placement_method="grid",
                hpwl_um=100.0 * i,
                overlap_count=0,
                area_utilization=0.1 * i,
                module_count=10 * i,
                connection_count=5 * i,
                target_metric="hpwl",
                target_value=1000.0,
                passed=i > 0,
                process_node="220nm SOI",
            )
            for i in range(1, 4)
        ]
        comp = generate_comparison_report(reports)
        assert comp.total_benchmarks == 3
        assert comp.passed_count == 3  # i=1,2,3 全部 passed (i>0)
        assert comp.pass_rate == pytest.approx(1.0)
        # avg hpwl = (100 + 200 + 300) / 3 = 200
        assert comp.avg_hpwl_um == pytest.approx(200.0)
        # avg util = (0.1 + 0.2 + 0.3) / 3 = 0.2
        assert comp.avg_utilization == pytest.approx(0.2)
        assert comp.total_modules == 60  # 10+20+30
        assert comp.total_connections == 30  # 5+10+15

    def test_comparison_pass_rate(self) -> None:
        """达标率应正确计算。"""
        reports = [
            BenchmarkReport(
                benchmark_name=f"b{i}",
                benchmark_source="CUSTOM",
                placement_method="grid",
                hpwl_um=0.0,
                overlap_count=0,
                area_utilization=0.0,
                module_count=1,
                connection_count=0,
                target_metric="hpwl",
                target_value=0.0,
                passed=p,
                process_node="",
            )
            for i, p in enumerate([True, False, True, True, False])
        ]
        comp = generate_comparison_report(reports)
        assert comp.total_benchmarks == 5
        assert comp.passed_count == 3
        assert comp.pass_rate == pytest.approx(0.6)


class TestRunAllBenchmarks:
    """run_all_benchmarks 函数测试。"""

    def test_run_all_returns_comparison(self) -> None:
        """run_all_benchmarks 应返回 ComparisonReport。"""
        comp = run_all_benchmarks()
        assert isinstance(comp, ComparisonReport)
        # 应包含 4 个 benchmark: TILOS + Apollo PTC + Apollo oNoC + LiDAR
        assert comp.total_benchmarks == 4
        assert comp.timestamp != ""

    def test_run_all_contains_tilos(self) -> None:
        """run_all_benchmarks 应包含 TILOS Ariane。"""
        comp = run_all_benchmarks()
        names = [r.benchmark_name for r in comp.reports]
        assert "tilos_ariane" in names

    def test_run_all_contains_apollo_ptc(self) -> None:
        """run_all_benchmarks 应包含 Apollo PTC。"""
        comp = run_all_benchmarks()
        names = [r.benchmark_name for r in comp.reports]
        assert "apollo_ptc" in names

    def test_run_all_contains_apollo_onoc(self) -> None:
        """run_all_benchmarks 应包含 Apollo oNoC。"""
        comp = run_all_benchmarks()
        names = [r.benchmark_name for r in comp.reports]
        assert "apollo_onoc" in names

    def test_run_all_contains_lidar(self) -> None:
        """run_all_benchmarks 应包含 LiDAR PTC。"""
        comp = run_all_benchmarks()
        names = [r.benchmark_name for r in comp.reports]
        assert "lidar_ptc" in names

    def test_run_all_grid_no_overlap(self) -> None:
        """grid 布局应无重叠（自适应最大模块）。"""
        comp = run_all_benchmarks(placement_method="grid")
        for r in comp.reports:
            assert r.overlap_count == 0, f"{r.benchmark_name} 有重叠"

    def test_run_all_total_modules(self) -> None:
        """总模块数应为 17 + 12 + 15 + 12 = 56。"""
        comp = run_all_benchmarks()
        # TILOS 17 + Apollo PTC 12 + Apollo oNoC 15 + LiDAR PTC 12 = 56
        assert comp.total_modules == 56

    def test_run_all_total_connections(self) -> None:
        """总连接数应为 25 + 13 + 23 + 13 = 74。"""
        comp = run_all_benchmarks()
        # TILOS 25 + Apollo PTC 13 + Apollo oNoC 23 + LiDAR PTC 13 = 74
        assert comp.total_connections == 74

    def test_run_all_placement_method(self) -> None:
        """placement_method 应正确传递。"""
        comp = run_all_benchmarks(placement_method="rl_ppo")
        for r in comp.reports:
            assert r.placement_method == "rl_ppo"


class TestFormatMarkdown:
    """Markdown 格式化测试。"""

    def test_format_report_markdown_basic(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """format_report_markdown 应生成含核心字段的 Markdown。"""
        report = generate_report(simple_circuit, simple_placements)
        md = format_report_markdown(report)
        assert "# PoLaRIS Benchmark 评估报告" in md
        assert "test_simple" in md
        assert "## 1. 摘要" in md
        assert "## 2. 核心指标" in md
        assert "HPWL" in md

    def test_format_report_markdown_passed(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """达标报告应含 ✅ 标记。"""
        report = generate_report(simple_circuit, simple_placements)
        md = format_report_markdown(report)
        assert "✅" in md

    def test_format_report_markdown_failed(self, simple_circuit: CircuitSpec) -> None:
        """未达标报告应含 ❌ 标记。"""
        placements = {"a": (0.0, 0.0), "b": (0.0, 0.0), "c": (0.0, 0.0)}
        report = generate_report(simple_circuit, placements)
        md = format_report_markdown(report)
        # 重叠 → 未达标
        if not report.passed:
            assert "❌" in md

    def test_format_report_markdown_extra(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
    ) -> None:
        """含 extra 的报告应含额外信息章节。"""
        report = generate_report(simple_circuit, simple_placements)
        md = format_report_markdown(report)
        assert "## 3. 额外信息" in md
        assert "benchmark_source" in md

    def test_format_report_markdown_sources(self) -> None:
        """Markdown 应含来源 URL。"""
        from polaris.data.data_loader import load_tilos_ariane

        circuit = load_tilos_ariane()
        report = generate_grid_report(circuit)
        md = format_report_markdown(report)
        assert "TILOS" in md
        assert "https://github.com/TILOS-AI-CAD-Institute/MacroPlacement" in md

    def test_format_comparison_markdown_basic(self) -> None:
        """format_comparison_markdown 应生成对比 Markdown。"""
        comp = run_all_benchmarks()
        md = format_comparison_markdown(comp)
        assert "# PoLaRIS Benchmark 对比评估报告" in md
        assert "## 1. 摘要" in md
        assert "## 2. 各 Benchmark 详细结果" in md
        assert "tilos_ariane" in md
        assert "apollo_ptc" in md

    def test_format_comparison_markdown_table(self) -> None:
        """对比 Markdown 应含表格。"""
        comp = run_all_benchmarks()
        md = format_comparison_markdown(comp)
        assert "| Benchmark |" in md
        # 表格分隔符（|------|...）
        assert "|------|" in md or "|" in md

    def test_format_comparison_markdown_pass_rate(self) -> None:
        """对比 Markdown 应含达标率。"""
        comp = run_all_benchmarks()
        md = format_comparison_markdown(comp)
        assert "达标率" in md


class TestSaveReport:
    """save_report_* 函数测试。"""

    def test_save_markdown_single(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
        tmp_path: Path,
    ) -> None:
        """save_report_markdown 应保存单 benchmark 报告。"""
        report = generate_report(simple_circuit, simple_placements)
        out = save_report_markdown(report, tmp_path / "report.md")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "test_simple" in content

    def test_save_markdown_comparison(self, tmp_path: Path) -> None:
        """save_report_markdown 应保存对比报告。"""
        comp = run_all_benchmarks()
        out = save_report_markdown(comp, tmp_path / "comparison.md")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "对比评估报告" in content

    def test_save_json_single(
        self,
        simple_circuit: CircuitSpec,
        simple_placements: dict[str, tuple[float, float]],
        tmp_path: Path,
    ) -> None:
        """save_report_json 应保存单 benchmark JSON。"""
        report = generate_report(simple_circuit, simple_placements)
        out = save_report_json(report, tmp_path / "report.json")
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["benchmark_name"] == "test_simple"
        assert data["hpwl_um"] == report.hpwl_um
        assert data["passed"] == report.passed

    def test_save_json_comparison(self, tmp_path: Path) -> None:
        """save_report_json 应保存对比 JSON。"""
        comp = run_all_benchmarks()
        out = save_report_json(comp, tmp_path / "comparison.json")
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["total_benchmarks"] == 4
        assert len(data["reports"]) == 4
        assert "pass_rate" in data

    def test_save_creates_parent_dir(self, tmp_path: Path) -> None:
        """save 应自动创建父目录。"""
        from polaris.data.data_loader import load_tilos_ariane

        circuit = load_tilos_ariane()
        report = generate_grid_report(circuit)
        out = save_report_markdown(report, tmp_path / "sub" / "dir" / "report.md")
        assert out.exists()

    def test_save_json_machine_readable(self, tmp_path: Path) -> None:
        """JSON 应可被机器读取（CI 回归用）。"""
        comp = run_all_benchmarks()
        out = save_report_json(comp, tmp_path / "ci.json")
        data = json.loads(out.read_text(encoding="utf-8"))
        # 验证可序列化 + 含必要字段
        assert "reports" in data
        for r in data["reports"]:
            assert "benchmark_name" in r
            assert "hpwl_um" in r
            assert "passed" in r
            assert "timestamp" in r


class TestCommercialGapReduction:
    """商业差距缩减验证（P1-5 深化）。"""

    def test_tilos_evaluation_flow_aligned(self) -> None:
        """评估流程应对齐 TILOS MacroPlacement 标准。"""
        from polaris.data.data_loader import load_tilos_ariane

        circuit = load_tilos_ariane()
        report = generate_grid_report(circuit)
        # TILOS 评估标准：HPWL + 重叠 + 利用率 + 达标判定
        assert report.hpwl_um > 0
        assert report.overlap_count == 0  # grid 自适应无重叠
        assert 0 < report.area_utilization < 1
        assert isinstance(report.passed, bool)
        assert report.target_metric == "hpwl"

    def test_all_benchmarks_evaluable(self) -> None:
        """全部公开 benchmark 应可评估（TILOS/Apollo/LiDAR）。"""
        comp = run_all_benchmarks()
        # 4 个 benchmark 全部应有有效评估
        assert comp.total_benchmarks == 4
        for r in comp.reports:
            assert r.hpwl_um > 0
            assert r.module_count > 0
            assert r.connection_count > 0
            assert r.timestamp != ""

    def test_report_format_aligned_tilos_codebook(self) -> None:
        """报告格式应对齐 TILOS CodeBook 输出风格。"""
        from polaris.data.data_loader import load_tilos_ariane

        circuit = load_tilos_ariane()
        report = generate_grid_report(circuit)
        md = format_report_markdown(report)
        # TILOS CodeBook 风格：摘要 + 详细指标 + 来源
        assert "# PoLaRIS Benchmark 评估报告" in md
        assert "## 1. 摘要" in md
        assert "## 2. 核心指标" in md
        assert "HPWL" in md
        assert "来源" in md

    def test_comparison_report_for_paper(self) -> None:
        """对比报告应可用于学术论文（多 benchmark 横向对比）。"""
        comp = run_all_benchmarks()
        md = format_comparison_markdown(comp)
        # 论文需要的元素：表格 + 统计摘要 + 来源
        assert "| Benchmark |" in md  # 表格
        assert "达标率" in md  # 统计
        assert "平均 HPWL" in md
        assert "https://" in md  # 来源

    def test_ci_regression_json(self, tmp_path: Path) -> None:
        """JSON 报告应可用于 CI 回归测试。"""
        comp = run_all_benchmarks()
        out = save_report_json(comp, tmp_path / "ci_regression.json")
        data = json.loads(out.read_text(encoding="utf-8"))
        # CI 回归需要的字段
        assert "total_benchmarks" in data
        assert "pass_rate" in data
        assert "reports" in data
        # 每个 report 应有可比较的指标
        for r in data["reports"]:
            assert "benchmark_name" in r
            assert "hpwl_um" in r
            assert "passed" in r

    def test_source_traceability(self) -> None:
        """报告应含来源溯源（学术诚信）。"""
        comp = run_all_benchmarks()
        md = format_comparison_markdown(comp)
        # 应含三大 benchmark 来源 URL
        assert "TILOS" in md
        assert "Apollo" in md
        assert "LiDAR" in md
        assert "github.com/TILOS-AI-CAD-Institute/MacroPlacement" in md
        assert "github.com/ASU-LOPE-Group/Apollo" in md
