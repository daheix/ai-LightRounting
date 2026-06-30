"""R334 GDSII 批处理流水线工具测试。

覆盖:
- run_batch_pipeline: 多文件批处理、自定义步骤、文件不存在处理
- generate_pipeline_report: text/markdown/json 报告
- R03 错误处理
- R02 学术诚信
- 集成测试（与 R323/R331/R332/R329 联动）
- 数据类测试

来源:
- EDA 流水线: https://www.cadence.com/en_US/home/tools.html
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- KLayout 批处理: https://www.klayout.de/doc-qt5/programming/
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_batch_pipeline import (
    SUPPORTED_STEPS,
    FilePipelineResult,
    PipelineReport,
    StepResult,
    generate_pipeline_report,
    run_batch_pipeline,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_gds(path: Path, cell_name: str, layer: int = 1,
              with_text: bool = False) -> Path:
    """创建简单 GDSII 文件。"""
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(cell_name)
    li = ly.layer(layer, 0)
    pts = [
        db.Point(0, 0), db.Point(10000, 0),
        db.Point(10000, 5000), db.Point(0, 5000),
    ]
    top.shapes(li).insert(db.Polygon(pts))
    if with_text:
        li_text = ly.layer(10, 0)
        text = db.Text("label_1", db.Trans(db.Point(5000, 2500)))
        top.shapes(li_text).insert(text)
    ly.write(str(path))
    return path


@pytest.fixture
def gds_a(tmp_path: Path) -> Path:
    """GDSII 文件 A（含文本）。"""
    return _make_gds(tmp_path / "a.gds", "CELL_A", layer=1, with_text=True)


@pytest.fixture
def gds_b(tmp_path: Path) -> Path:
    """GDSII 文件 B（含文本）。"""
    return _make_gds(tmp_path / "b.gds", "CELL_B", layer=2, with_text=True)


@pytest.fixture
def gds_c(tmp_path: Path) -> Path:
    """GDSII 文件 C（无文本）。"""
    return _make_gds(tmp_path / "c.gds", "CELL_C", layer=3, with_text=False)


# =============================================================================
# TestRunBatchPipeline: 基本批处理
# =============================================================================
class TestRunBatchPipeline:
    """run_batch_pipeline 函数测试。"""

    def test_returns_report(self, gds_a: Path) -> None:
        """返回 PipelineReport。"""
        report = run_batch_pipeline([gds_a])
        assert isinstance(report, PipelineReport)

    def test_single_file(self, gds_a: Path) -> None:
        """单文件批处理。"""
        report = run_batch_pipeline([gds_a])
        assert report.total_files == 1
        assert len(report.file_results) == 1

    def test_multiple_files(self, gds_a: Path, gds_b: Path, gds_c: Path) -> None:
        """多文件批处理。"""
        report = run_batch_pipeline([gds_a, gds_b, gds_c])
        assert report.total_files == 3
        assert len(report.file_results) == 3

    def test_default_steps_all(self, gds_a: Path) -> None:
        """默认执行全部 4 步骤。"""
        report = run_batch_pipeline([gds_a])
        assert len(report.steps_requested) == 4
        assert set(report.steps_requested) == set(SUPPORTED_STEPS)

    def test_custom_steps_single(self, gds_a: Path) -> None:
        """自定义单步骤。"""
        report = run_batch_pipeline([gds_a], steps=["statistics"])
        assert report.steps_requested == ["statistics"]
        assert report.total_steps_executed == 1

    def test_custom_steps_subset(self, gds_a: Path) -> None:
        """自定义步骤子集。"""
        report = run_batch_pipeline(
            [gds_a], steps=["statistics", "ports"]
        )
        assert report.steps_requested == ["statistics", "ports"]
        assert report.total_steps_executed == 2

    def test_total_steps_executed(self, gds_a: Path, gds_b: Path) -> None:
        """步骤执行总数 = 文件数 × 步骤数。"""
        report = run_batch_pipeline([gds_a, gds_b])
        assert report.total_steps_executed == 2 * 4

    def test_file_result_fields(self, gds_a: Path) -> None:
        """FilePipelineResult 字段完整。"""
        report = run_batch_pipeline([gds_a])
        fr = report.file_results[0]
        assert isinstance(fr, FilePipelineResult)
        assert fr.file_path == str(gds_a)
        assert fr.file_exists is True
        assert len(fr.steps) == 4

    def test_step_result_fields(self, gds_a: Path) -> None:
        """StepResult 字段完整。"""
        report = run_batch_pipeline([gds_a], steps=["statistics"])
        sr = report.file_results[0].steps[0]
        assert isinstance(sr, StepResult)
        assert sr.step_name == "statistics"
        assert sr.success is True
        assert "total_cells" in sr.summary

    def test_statistics_summary(self, gds_a: Path) -> None:
        """statistics 步骤摘要。"""
        report = run_batch_pipeline([gds_a], steps=["statistics"])
        sr = report.file_results[0].steps[0]
        assert sr.success
        assert "total_cells" in sr.summary
        assert "total_polygons" in sr.summary
        assert "total_layers" in sr.summary
        assert "total_area_um2" in sr.summary

    def test_ports_summary(self, gds_a: Path) -> None:
        """ports 步骤摘要。"""
        report = run_batch_pipeline([gds_a], steps=["ports"])
        sr = report.file_results[0].steps[0]
        assert sr.success
        assert "port_count" in sr.summary
        assert "matched_count" in sr.summary

    def test_texts_summary(self, gds_a: Path) -> None:
        """texts 步骤摘要。"""
        report = run_batch_pipeline([gds_a], steps=["texts"])
        sr = report.file_results[0].steps[0]
        assert sr.success
        assert "text_count" in sr.summary
        assert sr.summary["text_count"] == 1  # gds_a 有 1 个 text

    def test_precheck_summary(self, gds_a: Path) -> None:
        """precheck 步骤摘要。"""
        report = run_batch_pipeline([gds_a], steps=["precheck"])
        sr = report.file_results[0].steps[0]
        assert sr.success
        assert "passed" in sr.summary
        assert "warning_count" in sr.summary
        assert "error_count" in sr.summary

    def test_success_count(self, gds_a: Path) -> None:
        """成功步骤计数。"""
        report = run_batch_pipeline([gds_a])
        fr = report.file_results[0]
        assert fr.success_count == 4
        assert fr.fail_count == 0

    def test_total_success_files(self, gds_a: Path, gds_b: Path) -> None:
        """全成功文件数。"""
        report = run_batch_pipeline([gds_a, gds_b])
        assert report.total_success_files == 2
        assert report.total_fail_files == 0

    def test_input_files_recorded(self, gds_a: Path, gds_b: Path) -> None:
        """input_files 正确记录。"""
        report = run_batch_pipeline([gds_a, gds_b])
        assert report.input_files == [str(gds_a), str(gds_b)]

    def test_steps_requested_recorded(self, gds_a: Path) -> None:
        """steps_requested 正确记录。"""
        report = run_batch_pipeline([gds_a], steps=["ports", "texts"])
        assert report.steps_requested == ["ports", "texts"]


# =============================================================================
# TestFileNotFound: 文件不存在处理
# =============================================================================
class TestFileNotFound:
    """文件不存在时的处理（不中断流水线）。"""

    def test_nonexistent_file_marked(self, gds_a: Path) -> None:
        """不存在的文件被标记为 file_exists=False。"""
        report = run_batch_pipeline([gds_a, "/nonexistent.gds"])
        assert report.file_results[1].file_exists is False
        assert report.file_results[0].file_exists is True

    def test_nonexistent_file_all_steps_fail(self, gds_a: Path) -> None:
        """不存在的文件所有步骤都失败。"""
        report = run_batch_pipeline(["/nonexistent.gds"])
        fr = report.file_results[0]
        assert fr.fail_count == 4
        assert fr.success_count == 0
        for sr in fr.steps:
            assert sr.success is False
            assert "文件不存在" in sr.error_message

    def test_partial_nonexistent(self, gds_a: Path, gds_b: Path) -> None:
        """部分文件不存在不影响其他文件。"""
        report = run_batch_pipeline([gds_a, "/missing.gds", gds_b])
        assert report.total_files == 3
        assert report.file_results[0].file_exists is True
        assert report.file_results[1].file_exists is False
        assert report.file_results[2].file_exists is True

    def test_total_fail_files_with_missing(self, gds_a: Path) -> None:
        """有缺失文件时 total_fail_files 正确。"""
        report = run_batch_pipeline([gds_a, "/missing.gds"])
        assert report.total_success_files == 1
        assert report.total_fail_files == 1


# =============================================================================
# TestGeneratePipelineReport: 报告生成
# =============================================================================
class TestGeneratePipelineReport:
    """generate_pipeline_report 函数测试。"""

    def test_text_report(self, gds_a: Path, gds_b: Path) -> None:
        """text 格式报告。"""
        report = generate_pipeline_report(
            [gds_a, gds_b], output_format="text"
        )
        assert "GDSII 批处理流水线综合报告" in report
        assert "文件总数" in report
        # 报告含文件路径
        assert str(gds_a) in report
        assert str(gds_b) in report

    def test_markdown_report(self, gds_a: Path) -> None:
        """markdown 格式报告。"""
        report = generate_pipeline_report(
            [gds_a], output_format="markdown"
        )
        assert "# GDSII 批处理流水线综合报告" in report
        assert "| 步骤 | 状态 | 摘要 |" in report

    def test_json_report(self, gds_a: Path, gds_b: Path) -> None:
        """json 格式报告。"""
        report_str = generate_pipeline_report(
            [gds_a, gds_b], output_format="json"
        )
        data = json.loads(report_str)
        assert data["total_files"] == 2
        assert len(data["file_results"]) == 2

    def test_json_report_structure(self, gds_a: Path) -> None:
        """json 报告结构完整。"""
        report_str = generate_pipeline_report(
            [gds_a], output_format="json"
        )
        data = json.loads(report_str)
        assert "total_files" in data
        assert "steps_requested" in data
        assert "file_results" in data
        fr = data["file_results"][0]
        assert "file_path" in fr
        assert "file_exists" in fr
        assert "steps" in fr
        sr = fr["steps"][0]
        assert "step_name" in sr
        assert "success" in sr
        assert "summary" in sr

    def test_text_report_with_failure(self, gds_a: Path) -> None:
        """text 报告含失败步骤。"""
        report = generate_pipeline_report(
            [gds_a, "/missing.gds"], output_format="text"
        )
        assert "文件不存在" in report

    def test_unsupported_format_raises(self, gds_a: Path) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_pipeline_report([gds_a], output_format="xml")


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_empty_input_paths(self, tmp_path: Path) -> None:
        """空 input_paths raise ValueError。"""
        with pytest.raises(ValueError, match="input_paths 不能为空"):
            run_batch_pipeline([])

    def test_empty_steps(self, gds_a: Path) -> None:
        """空 steps raise ValueError。"""
        with pytest.raises(ValueError, match="steps 不能为空"):
            run_batch_pipeline([gds_a], steps=[])

    def test_invalid_step_name(self, gds_a: Path) -> None:
        """不支持的步骤名 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的步骤"):
            run_batch_pipeline([gds_a], steps=["invalid_step"])

    def test_partial_invalid_step(self, gds_a: Path) -> None:
        """部分不支持的步骤名 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的步骤"):
            run_batch_pipeline([gds_a], steps=["statistics", "bad_step"])

    def test_unsupported_format_xml(self, gds_a: Path) -> None:
        """XML 格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_pipeline_report([gds_a], output_format="xml")

    def test_unsupported_format_html(self, gds_a: Path) -> None:
        """HTML 格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_pipeline_report([gds_a], output_format="html")


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信（R02）
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_cadence_url(self) -> None:
        """docstring 含 Cadence EDA 文档 URL。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "cadence.com" in m.__doc__

    def test_docstring_has_gdsfactory_url(self) -> None:
        """docstring 含 gdsfactory 文档 URL。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "gdsfactory.github.io" in m.__doc__

    def test_docstring_has_klayout_url(self) -> None:
        """docstring 含 KLayout 文档 URL。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "klayout.de" in m.__doc__

    def test_docstring_has_calibre_url(self) -> None:
        """docstring 含 Calibre DRC 文档 URL。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "mentor.com" in m.__doc__

    def test_docstring_has_siepic_url(self) -> None:
        """docstring 含 SiEPIC PDK URL。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "SiEPIC" in m.__doc__

    def test_docstring_has_5_plus_urls(self) -> None:
        """docstring 含 ≥5 个文献 URL（R02 要求）。"""
        from polaris.verification import gdsii_batch_pipeline as m
        doc = m.__doc__
        url_count = doc.count("https://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5"

    def test_docstring_has_r_compliance(self) -> None:
        """docstring 含规则合规声明。"""
        from polaris.verification import gdsii_batch_pipeline as m
        assert "R01" in m.__doc__
        assert "R02" in m.__doc__
        assert "R03" in m.__doc__
        assert "R05" in m.__doc__
        assert "R11" in m.__doc__

    def test_supported_steps_constant(self) -> None:
        """SUPPORTED_STEPS 常量含 4 个步骤。"""
        assert len(SUPPORTED_STEPS) == 4
        assert "statistics" in SUPPORTED_STEPS
        assert "ports" in SUPPORTED_STEPS
        assert "texts" in SUPPORTED_STEPS
        assert "precheck" in SUPPORTED_STEPS


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_pipeline_with_all_step_types(self, gds_a: Path) -> None:
        """流水线执行全部 4 种步骤。"""
        report = run_batch_pipeline([gds_a])
        fr = report.file_results[0]
        step_names = [sr.step_name for sr in fr.steps]
        assert step_names == ["statistics", "ports", "texts", "precheck"]

    def test_pipeline_statistics_matches_direct_call(
        self, gds_a: Path
    ) -> None:
        """流水线 statistics 结果与直接调用一致。"""
        from polaris.verification.gdsii_statistics import (
            generate_gdsii_statistics,
        )
        direct = generate_gdsii_statistics(gds_a)
        report = run_batch_pipeline([gds_a], steps=["statistics"])
        pipeline_result = report.file_results[0].steps[0].summary
        assert pipeline_result["total_cells"] == direct.total_cells

    def test_pipeline_texts_matches_direct_call(self, gds_a: Path) -> None:
        """流水线 texts 结果与直接调用一致。"""
        from polaris.verification.gdsii_text_label_extractor import (
            extract_text_labels,
        )
        direct = extract_text_labels(gds_a)
        report = run_batch_pipeline([gds_a], steps=["texts"])
        pipeline_result = report.file_results[0].steps[0].summary
        assert pipeline_result["text_count"] == direct.total_count

    def test_pipeline_with_merge(self, gds_a: Path, gds_b: Path,
                                 tmp_path: Path) -> None:
        """合并后再批处理。"""
        from polaris.verification.gdsii_layout_merger import merge_gdsii

        merged = tmp_path / "merged.gds"
        merge_gdsii([gds_a, gds_b], merged)

        report = run_batch_pipeline([merged], steps=["statistics"])
        assert report.total_files == 1
        assert report.file_results[0].file_exists is True

    def test_pipeline_string_paths(self, gds_a: Path) -> None:
        """字符串路径输入。"""
        report = run_batch_pipeline([str(gds_a)])
        assert report.total_files == 1
        assert report.file_results[0].file_exists is True

    def test_pipeline_consistency_across_runs(self, gds_a: Path) -> None:
        """多次运行结果一致。"""
        r1 = run_batch_pipeline([gds_a])
        r2 = run_batch_pipeline([gds_a])
        assert r1.total_files == r2.total_files
        assert r1.total_step_success == r2.total_step_success


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_step_result_default(self) -> None:
        """StepResult 默认值。"""
        sr = StepResult(step_name="test", success=True)
        assert sr.step_name == "test"
        assert sr.success is True
        assert sr.error_message == ""
        assert sr.summary == {}

    def test_step_result_failure(self) -> None:
        """StepResult 失败状态。"""
        sr = StepResult(
            step_name="test", success=False, error_message="error"
        )
        assert sr.success is False
        assert sr.error_message == "error"

    def test_file_pipeline_result_default(self) -> None:
        """FilePipelineResult 默认值。"""
        fr = FilePipelineResult(file_path="/test.gds")
        assert fr.file_path == "/test.gds"
        assert fr.file_exists is True
        assert fr.steps == []
        assert fr.success_count == 0
        assert fr.fail_count == 0

    def test_pipeline_report_default(self) -> None:
        """PipelineReport 默认值。"""
        report = PipelineReport()
        assert report.input_files == []
        assert report.steps_requested == []
        assert report.file_results == []
        assert report.total_files == 0
        assert report.total_success_files == 0
        assert report.total_fail_files == 0

    def test_step_result_is_dataclass(self) -> None:
        """StepResult 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(StepResult)

    def test_file_pipeline_result_is_dataclass(self) -> None:
        """FilePipelineResult 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(FilePipelineResult)

    def test_pipeline_report_is_dataclass(self) -> None:
        """PipelineReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(PipelineReport)

    def test_pipeline_report_independent_lists(self) -> None:
        """PipelineReport list 字段独立。"""
        r1 = PipelineReport()
        r2 = PipelineReport()
        r1.input_files.append("/a.gds")
        r1.file_results.append(FilePipelineResult(file_path="/a.gds"))
        assert r2.input_files == []
        assert r2.file_results == []
