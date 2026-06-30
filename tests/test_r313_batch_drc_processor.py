"""R313 GDSII 批量 DRC 处理与报告聚合工具测试。

覆盖:
- run_batch_drc: 批量 DRC 执行
- aggregate_violations_by_rule: 跨文件按规则聚合
- aggregate_violations_by_layer: 跨文件按层聚合
- generate_batch_drc_report: 三种格式报告生成（text/markdown/json）
- save_batch_drc_report: 报告保存
- R03 错误处理（空列表/文件不存在/不支持格式）
- R02 学术诚信（docstring 文献引用）
- 集成测试（端到端批处理 + 报告）

来源:
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- Fowler 2002: https://martinfowler.com/books/eaa.html
- CommonMark: https://spec.commonmark.org/
- JSON RFC 8259: https://datatracker.ietf.org/doc/html/rfc8259
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory
from polaris.verification.batch_drc_processor import (
    BatchDRCReport,
    BatchDRCResult,
    aggregate_violations_by_layer,
    aggregate_violations_by_rule,
    generate_batch_drc_report,
    run_batch_drc,
    save_batch_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def compliant_gds(tmp_path: Path) -> Path:
    """合规 GDSII 文件（宽 0.5μm，间距 1.0μm）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
                {
                    "layer": 1, "datatype": 0,
                    "points": [[11, 0], [21, 0], [21, 0.5], [11, 0.5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "compliant.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def violating_gds(tmp_path: Path) -> Path:
    """违规 GDSII 文件（宽 0.3μm，间距 0.2μm）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.3], [0, 0.3]],
                },
                {
                    "layer": 1, "datatype": 0,
                    "points": [[10.2, 0], [20.2, 0], [20.2, 0.3], [10.2, 0.3]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "violating.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """多层 GDSII 文件（WG + METAL）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
                {
                    "layer": 5, "datatype": 0,
                    "points": [[0, 1], [10, 1], [10, 2], [0, 2]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def standard_rules() -> list[CurvilinearDRCRule]:
    """标准 DRC 规则集（宽度 + 间距）。"""
    return [
        CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        ),
        CurvilinearDRCRule(
            name="S1", category=DRCRuleCategory.MIN_SPACING,
            layer="WG", limit_value=0.5,
        ),
    ]


# =============================================================================
# TestRunBatchDrc: 批量 DRC 执行
# =============================================================================
class TestRunBatchDrc:
    """run_batch_drc 测试。"""

    def test_batch_single_compliant(
        self, compliant_gds: Path, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """批量处理单个合规文件。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        assert isinstance(result, BatchDRCResult)
        assert result.total_files == 1
        assert result.passed_files == 1
        assert result.failed_files == 0
        assert result.total_violations == 0
        assert len(result.reports) == 1
        assert result.reports[0].passed is True
        assert result.reports[0].error is None

    def test_batch_single_violating(
        self, violating_gds: Path, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """批量处理单个违规文件。"""
        result = run_batch_drc([violating_gds], standard_rules)
        assert result.total_files == 1
        assert result.failed_files == 1
        assert result.passed_files == 0
        assert result.total_violations > 0
        assert result.reports[0].passed is False

    def test_batch_mixed_files(
        self,
        compliant_gds: Path,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """批量处理合规 + 违规混合文件。"""
        result = run_batch_drc([compliant_gds, violating_gds], standard_rules)
        assert result.total_files == 2
        assert result.passed_files == 1
        assert result.failed_files == 1
        assert len(result.reports) == 2
        # 顺序保持
        assert result.reports[0].file_path == str(compliant_gds)
        assert result.reports[1].file_path == str(violating_gds)
        assert result.reports[0].passed is True
        assert result.reports[1].passed is False

    def test_batch_multi_layer(
        self,
        multi_layer_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """批量处理多层 GDS 文件（WG + METAL 均合规）。"""
        rules = standard_rules + [
            CurvilinearDRCRule(
                name="W2", category=DRCRuleCategory.MIN_WIDTH,
                layer="METAL", limit_value=0.5,
            ),
        ]
        result = run_batch_drc([multi_layer_gds], rules)
        assert result.total_files == 1
        assert result.passed_files == 1
        assert result.reports[0].summary is not None
        # 多层提取应包含 WG 和 METAL
        layers = result.reports[0].summary["layers_extracted"]
        assert "WG" in layers
        assert "METAL" in layers

    def test_batch_preserves_order(
        self,
        compliant_gds: Path,
        violating_gds: Path,
        multi_layer_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """批量处理保持输入顺序。"""
        paths = [violating_gds, compliant_gds, multi_layer_gds]
        result = run_batch_drc(paths, standard_rules)
        assert result.reports[0].file_path == str(violating_gds)
        assert result.reports[1].file_path == str(compliant_gds)
        assert result.reports[2].file_path == str(multi_layer_gds)

    def test_batch_processing_time_positive(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """处理时间应为正数。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        assert result.total_time_s > 0
        assert result.reports[0].processing_time_s > 0
        # 总时间应 ≥ 单文件时间
        assert result.total_time_s >= result.reports[0].processing_time_s

    def test_batch_with_top_cell_names(
        self, compliant_gds: Path, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """通过 top_cell_names 指定顶层 cell。"""
        top_names = {str(compliant_gds): "TOP"}
        result = run_batch_drc(
            [compliant_gds], standard_rules, top_cell_names=top_names
        )
        assert result.total_files == 1
        assert result.passed_files == 1

    def test_batch_with_top_cell_names_by_basename(
        self, compliant_gds: Path, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """通过文件 basename 指定顶层 cell。"""
        top_names = {"compliant.gds": "TOP"}
        result = run_batch_drc(
            [compliant_gds], standard_rules, top_cell_names=top_names
        )
        assert result.passed_files == 1

    def test_batch_aggregate_violations(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """违规文件的违规计数应累计到 total_violations。"""
        result = run_batch_drc([violating_gds], standard_rules)
        # violating_gds 同时违反 W1（宽度 0.3 < 0.45）和 S1（间距 0.2 < 0.5）
        assert result.total_violations >= 2
        assert result.total_errors >= 2


# =============================================================================
# TestAggregateViolations: 跨文件聚合
# =============================================================================
class TestAggregateViolations:
    """aggregate_violations_by_rule / by_layer 测试。"""

    def test_aggregate_by_rule_single_file(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """单文件按规则聚合。"""
        result = run_batch_drc([violating_gds], standard_rules)
        by_rule = aggregate_violations_by_rule(result)
        assert isinstance(by_rule, dict)
        # W1 和 S1 规则都应有违规
        assert "W1" in by_rule
        assert "S1" in by_rule
        assert by_rule["W1"] > 0
        assert by_rule["S1"] > 0

    def test_aggregate_by_rule_multi_file(
        self,
        compliant_gds: Path,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """多文件按规则聚合（违规累加）。"""
        result = run_batch_drc(
            [violating_gds, violating_gds], standard_rules
        )
        by_rule = aggregate_violations_by_rule(result)
        # 两个违规文件，违规数应翻倍
        single_result = run_batch_drc([violating_gds], standard_rules)
        single_by_rule = aggregate_violations_by_rule(single_result)
        for rule_id in by_rule:
            assert by_rule[rule_id] == 2 * single_by_rule[rule_id]

    def test_aggregate_by_rule_no_violations(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """合规文件聚合应为空字典或全零。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        by_rule = aggregate_violations_by_rule(result)
        # 合规文件无违规，by_rule 应为空
        for count in by_rule.values():
            assert count == 0

    def test_aggregate_by_layer_single_file(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """单文件按层聚合。"""
        result = run_batch_drc([violating_gds], standard_rules)
        by_layer = aggregate_violations_by_layer(result)
        assert isinstance(by_layer, dict)
        # 违规都在 WG 层
        assert "WG" in by_layer
        assert by_layer["WG"] > 0

    def test_aggregate_by_layer_multi_file(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """多文件按层聚合。"""
        result = run_batch_drc(
            [violating_gds, violating_gds], standard_rules
        )
        by_layer = aggregate_violations_by_layer(result)
        single_result = run_batch_drc([violating_gds], standard_rules)
        single_by_layer = aggregate_violations_by_layer(single_result)
        assert by_layer["WG"] == 2 * single_by_layer["WG"]


# =============================================================================
# TestGenerateBatchDrcReport: 报告生成
# =============================================================================
class TestGenerateBatchDrcReport:
    """generate_batch_drc_report 测试。"""

    def test_text_report_basic(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """text 格式报告基本内容。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        report = generate_batch_drc_report(result, "text")
        assert isinstance(report, str)
        assert "PoLaRIS 批量 GDSII DRC 报告" in report
        assert "文件总数: 1" in report
        assert "通过文件: 1" in report
        assert str(compliant_gds) in report

    def test_markdown_report_basic(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """markdown 格式报告基本内容。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        report = generate_batch_drc_report(result, "markdown")
        assert isinstance(report, str)
        assert "# PoLaRIS 批量 GDSII DRC 报告" in report
        assert "| 文件总数 |" in report
        assert str(compliant_gds) in report

    def test_json_report_basic(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """json 格式报告基本内容。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        report = generate_batch_drc_report(result, "json")
        assert isinstance(report, str)
        # 必须是合法 JSON
        payload = json.loads(report)
        assert "overview" in payload
        assert "reports" in payload
        assert "aggregations" in payload
        assert payload["overview"]["total_files"] == 1
        assert payload["overview"]["passed_files"] == 1

    def test_text_report_with_violations(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """text 报告含违规信息。"""
        result = run_batch_drc([violating_gds], standard_rules)
        report = generate_batch_drc_report(result, "text")
        assert "FAIL" in report
        assert "违规总数" in report

    def test_markdown_report_with_aggregations(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """markdown 报告含聚合部分。"""
        result = run_batch_drc([violating_gds], standard_rules)
        report = generate_batch_drc_report(result, "markdown")
        assert "跨文件按规则聚合" in report
        assert "跨文件按层聚合" in report
        assert "| W1 |" in report
        assert "| WG |" in report

    def test_json_report_aggregations(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """json 报告 aggregations 字段。"""
        result = run_batch_drc([violating_gds], standard_rules)
        report = generate_batch_drc_report(result, "json")
        payload = json.loads(report)
        assert "by_rule" in payload["aggregations"]
        assert "by_layer" in payload["aggregations"]
        assert "W1" in payload["aggregations"]["by_rule"]
        assert "WG" in payload["aggregations"]["by_layer"]

    def test_report_format_case_insensitive(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """格式参数大小写不敏感。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        r1 = generate_batch_drc_report(result, "TEXT")
        r2 = generate_batch_drc_report(result, "Text")
        r3 = generate_batch_drc_report(result, "text")
        assert r1 == r2 == r3

    def test_report_unsupported_format_raises(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """不支持的格式应 raise ValueError。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        with pytest.raises(ValueError, match="不支持"):
            generate_batch_drc_report(result, "xml")

    def test_report_with_error_files(
        self,
        compliant_gds: Path,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """报告含 ERROR 状态文件（混合通过/失败）。"""
        result = run_batch_drc(
            [compliant_gds, violating_gds], standard_rules
        )
        report = generate_batch_drc_report(result, "text")
        assert "PASS" in report
        assert "FAIL" in report


# =============================================================================
# TestSaveBatchDrcReport: 报告保存
# =============================================================================
class TestSaveBatchDrcReport:
    """save_batch_drc_report 测试。"""

    def test_save_text_report(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """保存 text 报告。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        out = tmp_path / "report.txt"
        saved = save_batch_drc_report(result, out, "text")
        assert saved == str(out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "PoLaRIS 批量 GDSII DRC 报告" in content

    def test_save_markdown_report(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """保存 markdown 报告。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        out = tmp_path / "report.md"
        save_batch_drc_report(result, out, "markdown")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "# PoLaRIS 批量 GDSII DRC 报告" in content

    def test_save_json_report(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """保存 json 报告。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        out = tmp_path / "report.json"
        save_batch_drc_report(result, out, "json")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        payload = json.loads(content)
        assert payload["overview"]["total_files"] == 1

    def test_save_parent_dir_not_exists_raises(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """父目录不存在应 raise ValueError。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        out = tmp_path / "nonexistent_dir" / "report.txt"
        with pytest.raises(ValueError, match="父目录不存在"):
            save_batch_drc_report(result, out, "text")

    def test_save_returns_path_string(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """返回路径字符串。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        out = tmp_path / "report.txt"
        saved = save_batch_drc_report(result, out, "text")
        assert isinstance(saved, str)
        assert saved == str(out)


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理。"""

    def test_empty_paths_raises_value_error(
        self, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """空路径列表应 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            run_batch_drc([], standard_rules)

    def test_nonexistent_file_raises(
        self, standard_rules: list[CurvilinearDRCRule], tmp_path: Path
    ) -> None:
        """文件不存在应 raise FileNotFoundError（不跳过）。"""
        with pytest.raises(FileNotFoundError, match="不存在"):
            run_batch_drc([tmp_path / "no.gds"], standard_rules)

    def test_directory_path_raises(
        self,
        standard_rules: list[CurvilinearDRCRule],
        compliant_gds: Path,
        tmp_path: Path,
    ) -> None:
        """目录路径应 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            run_batch_drc([tmp_path], standard_rules)

    def test_non_list_paths_raises_type_error(
        self, standard_rules: list[CurvilinearDRCRule]
    ) -> None:
        """非列表/元组路径应 raise TypeError。"""
        with pytest.raises(TypeError):
            run_batch_drc("not_a_list", standard_rules)  # type: ignore[arg-type]

    def test_invalid_format_raises(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """不支持的格式应 raise ValueError。"""
        result = run_batch_drc([compliant_gds], standard_rules)
        with pytest.raises(ValueError, match="不支持"):
            generate_batch_drc_report(result, "yaml")

    def test_invalid_result_type_raises_aggregate(self) -> None:
        """aggregate 函数接错类型 raise TypeError。"""
        with pytest.raises(TypeError):
            aggregate_violations_by_rule("not_a_result")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            aggregate_violations_by_layer("not_a_result")  # type: ignore[arg-type]

    def test_invalid_result_type_raises_generate(self) -> None:
        """generate_batch_drc_report 接错类型 raise TypeError。"""
        with pytest.raises(TypeError):
            generate_batch_drc_report("not_a_result", "text")  # type: ignore[arg-type]


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信验证。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 应含 5+ 文献 URL。"""
        from polaris.verification import batch_drc_processor as m
        doc = m.__doc__ or ""
        urls = [
            "klayout.de/doc",
            "SiEPIC",
            "martinfowler.com",
            "commonmark.org",
            "rfc-editor.org" in doc or "datatracker.ietf.org" in doc,
            "python.org",
        ]
        url_count = sum(1 for u in urls if u is True or (isinstance(u, str) and u in doc))
        assert url_count >= 5, f"docstring 文献 URL 不足 5 个: {url_count}"

    def test_functions_have_source_annotations(self) -> None:
        """核心函数应含来源说明。"""
        from polaris.verification import batch_drc_processor as m
        for func_name in [
            "run_batch_drc",
            "aggregate_violations_by_rule",
            "aggregate_violations_by_layer",
            "generate_batch_drc_report",
            "save_batch_drc_report",
        ]:
            func = getattr(m, func_name)
            doc = func.__doc__ or ""
            assert "来源" in doc or "Fowler" in doc or "Python" in doc, (
                f"{func_name} 缺少来源标注"
            )

    def test_batch_design_pattern_documented(self) -> None:
        """批处理设计模式应记录 Fowler 2002 文献。"""
        from polaris.verification import batch_drc_processor as m
        doc = m.__doc__ or ""
        # 模块 docstring 应引用 Fowler 2002
        assert "Fowler" in doc
        assert "2002" in doc

    def test_siepic_layer_map_inherited(self) -> None:
        """R313 通过 R312 继承 SiEPIC 标准层映射。"""
        # R313 不重新定义层映射，而是复用 R312 drc_summary_from_gdsii 的默认映射
        from polaris.verification.batch_drc_processor import run_batch_drc
        # 通过检查 run_batch_drc 调用 drc_summary_from_gdsii（layer_map=None 时用 SiEPIC）
        import inspect

        src = inspect.getsource(run_batch_drc)
        assert "drc_summary_from_gdsii" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_batch_workflow(
        self,
        compliant_gds: Path,
        violating_gds: Path,
        multi_layer_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
        tmp_path: Path,
    ) -> None:
        """端到端: 批处理 → 聚合 → 报告生成 → 保存。"""
        paths = [compliant_gds, violating_gds, multi_layer_gds]
        # 1. 批处理
        result = run_batch_drc(paths, standard_rules)
        assert result.total_files == 3
        # 2. 聚合
        by_rule = aggregate_violations_by_rule(result)
        by_layer = aggregate_violations_by_layer(result)
        assert isinstance(by_rule, dict)
        assert isinstance(by_layer, dict)
        # 3. 报告生成（三种格式）
        for fmt in ["text", "markdown", "json"]:
            report = generate_batch_drc_report(result, fmt)
            assert isinstance(report, str)
            assert len(report) > 0
        # 4. 保存
        for fmt, ext in [("text", "txt"), ("markdown", "md"), ("json", "json")]:
            out = tmp_path / f"batch_report.{ext}"
            save_batch_drc_report(result, out, fmt)
            assert out.exists()
            assert out.stat().st_size > 0

    def test_batch_drc_consistency_with_single(
        self,
        violating_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """批处理结果与单文件 DRC 一致性验证。"""
        from polaris.verification.gdsii_drc_validator import drc_summary_from_gdsii

        # 单文件
        single = drc_summary_from_gdsii(violating_gds, standard_rules)
        # 批处理
        batch = run_batch_drc([violating_gds], standard_rules)
        assert batch.reports[0].summary is not None
        assert (
            batch.reports[0].summary["total_violations"]
            == single["total_violations"]
        )
        assert batch.reports[0].summary["errors"] == single["errors"]

    def test_performance_batch_large(
        self,
        compliant_gds: Path,
        standard_rules: list[CurvilinearDRCRule],
    ) -> None:
        """性能: 批量 10 个合规文件应在 10s 内完成。"""
        paths = [compliant_gds] * 10
        result = run_batch_drc(paths, standard_rules)
        assert result.total_files == 10
        assert result.passed_files == 10
        # 性能阈值: 10 文件 < 10s
        assert result.total_time_s < 10.0


# =============================================================================
# TestBatchDRCReportDataclass: 数据类测试
# =============================================================================
class TestBatchDRCReportDataclass:
    """BatchDRCReport / BatchDRCResult 数据类测试。"""

    def test_batch_drc_report_defaults(self) -> None:
        """BatchDRCReport 默认值。"""
        r = BatchDRCReport(file_path="/tmp/test.gds")
        assert r.file_path == "/tmp/test.gds"
        assert r.summary is None
        assert r.processing_time_s == 0.0
        assert r.error is None
        assert r.passed is False

    def test_batch_drc_result_defaults(self) -> None:
        """BatchDRCResult 默认值。"""
        r = BatchDRCResult()
        assert r.reports == []
        assert r.total_files == 0
        assert r.passed_files == 0
        assert r.failed_files == 0
        assert r.total_violations == 0
        assert r.total_errors == 0
        assert r.total_warnings == 0
        assert r.total_time_s == 0.0

    def test_batch_drc_report_with_summary(self) -> None:
        """BatchDRCReport 含 summary。"""
        r = BatchDRCReport(
            file_path="/tmp/test.gds",
            summary={"total_violations": 5, "passed": False},
            processing_time_s=0.5,
            passed=False,
        )
        assert r.summary["total_violations"] == 5
        assert r.processing_time_s == 0.5

    def test_batch_drc_report_with_error(self) -> None:
        """BatchDRCReport 含错误。"""
        r = BatchDRCReport(
            file_path="/tmp/test.gds",
            error="FileNotFoundError: 文件不存在",
            passed=False,
        )
        assert r.error is not None
        assert "FileNotFoundError" in r.error
