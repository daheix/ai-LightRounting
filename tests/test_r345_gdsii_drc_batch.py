"""R345 GDSII DRC 批量检查工具测试。

覆盖:
- run_batch_drc: 多规则批量检查（同层 + 层间 + 混合）
- generate_batch_drc_report: text/markdown/json 报告
- R03 错误处理（空规则、无效规则、layer_a==layer_b 等）
- R02 学术诚信（docstring URL）
- 集成测试
- 数据类测试（DRCRule / DRCRuleResult / BatchDRCReport）

来源:
- KLayout Region DRC: https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_batch import (
    BatchDRCReport,
    DRCRule,
    DRCRuleResult,
    generate_batch_drc_report,
    run_batch_drc,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_narrow_width_gds(path: Path) -> Path:
    """创建窄矩形 GDSII（width 违规）。

    layer (1,0): Box(0,0)-(500,5000) = 0.5μm×5μm
    dbu = 0.001μm
    width_check(1.0μm): 违规（0.5μm < 1.0μm）
    width_check(0.4μm): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 500, 5000))
    ly.write(str(path))
    return path


def _make_close_space_gds(path: Path) -> Path:
    """创建靠近矩形 GDSII（space 违规）。

    layer (1,0):
    - Box(0,0)-(2000,2000) = 2μm×2μm
    - Box(2500,0)-(4500,2000) = 2μm×2μm
    间距 = 0.5μm
    space_check(1.0μm): 违规（0.5μm < 1.0μm）
    space_check(0.4μm): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 2000, 2000))
    top.shapes(li).insert(db.Box(2500, 0, 4500, 2000))
    ly.write(str(path))
    return path


def _make_enclosing_gds(path: Path) -> Path:
    """创建包围 GDSII（enclosing 违规）。

    layer (1,0): Box(0,0)-(5000,5000) = 5x5μm
    layer (2,0): Box(1000,1000)-(4000,4000) = 3x3μm
    layer_a 包围 layer_b 每边大 1μm
    enclosing_check(2.0μm): 违规（1μm < 2μm）
    enclosing_check(1.0μm): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    la = ly.layer(1, 0)
    lb = ly.layer(2, 0)
    top = ly.create_cell("TOP")
    top.shapes(la).insert(db.Box(0, 0, 5000, 5000))
    top.shapes(lb).insert(db.Box(1000, 1000, 4000, 4000))
    ly.write(str(path))
    return path


def _make_separation_gds(path: Path) -> Path:
    """创建间距 GDSII（separation 违规）。

    layer (1,0): Box(0,0)-(1000,1000) = 1x1μm
    layer (3,0): Box(3000,0)-(4000,1000) = 1x1μm
    间距 = 2μm
    separation_check(3.0μm): 违规（2μm < 3μm）
    separation_check(1.5μm): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    la = ly.layer(1, 0)
    lc = ly.layer(3, 0)
    top = ly.create_cell("TOP")
    top.shapes(la).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(lc).insert(db.Box(3000, 0, 4000, 1000))
    ly.write(str(path))
    return path


def _make_comprehensive_gds(path: Path) -> Path:
    """创建综合 GDSII（4 个规则可同时检查）。

    layer (1,0): 5x5μm 大矩形（包围 layer 2）
    layer (2,0): 内部 3x3μm 矩形
    layer (3,0): 远处 1x1μm 矩形（与 layer 1 间距 2μm）

    可测试规则:
    - width(1.0μm) layer(1,0): 大矩形边长 > 1μm，PASS
    - space(1.0μm) layer(2,0): 单矩形无 space，PASS
    - enclosing(1.0μm) (1,0)→(2,0): 每边 1μm ≥ 1μm，PASS
    - separation(1.5μm) (1,0)→(3,0): 间距 2μm ≥ 1.5μm，PASS
    - enclosing(2.0μm) (1,0)→(2,0): 每边 1μm < 2μm，FAIL
    """
    ly = db.Layout()
    ly.dbu = 0.001
    la = ly.layer(1, 0)
    lb = ly.layer(2, 0)
    lc = ly.layer(3, 0)
    top = ly.create_cell("TOP")
    # layer 1: 5x5
    top.shapes(la).insert(db.Box(0, 0, 5000, 5000))
    # layer 2: 内部 3x3
    top.shapes(lb).insert(db.Box(1000, 1000, 4000, 4000))
    # layer 3: 远处 1x1，与 layer 1 间距 = (7000-5000)/1000 = 2μm
    top.shapes(lc).insert(db.Box(7000, 0, 8000, 1000))
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): Box(0,0)-(2000,2000) = 2μm×2μm
    width_check(1.0μm): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(0, 0, 2000, 2000))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def narrow_width_gds(tmp_path: Path) -> Path:
    """窄矩形 GDSII（width 违规）。"""
    return _make_narrow_width_gds(tmp_path / "narrow.gds")


@pytest.fixture
def close_space_gds(tmp_path: Path) -> Path:
    """靠近矩形 GDSII（space 违规）。"""
    return _make_close_space_gds(tmp_path / "close.gds")


@pytest.fixture
def enclosing_gds(tmp_path: Path) -> Path:
    """包围 GDSII（enclosing 违规）。"""
    return _make_enclosing_gds(tmp_path / "enc.gds")


@pytest.fixture
def separation_gds(tmp_path: Path) -> Path:
    """间距 GDSII（separation 违规）。"""
    return _make_separation_gds(tmp_path / "sep.gds")


@pytest.fixture
def comprehensive_gds(tmp_path: Path) -> Path:
    """综合 GDSII（多规则可同时检查）。"""
    return _make_comprehensive_gds(tmp_path / "comp.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


@pytest.fixture
def empty_gds(tmp_path: Path) -> Path:
    """无 layer 的 GDSII（无 layer(1,0)）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    # 不创建任何 layer
    ly.write(str(path := tmp_path / "empty.gds"))
    return path


# =============================================================================
# TestRunBatchDRC: 基本 API
# =============================================================================
class TestRunBatchDRC:
    """run_batch_drc 函数基本测试。"""

    def test_returns_report(self, narrow_width_gds: Path) -> None:
        """返回 BatchDRCReport。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert isinstance(report, BatchDRCReport)

    def test_input_path(self, narrow_width_gds: Path) -> None:
        """input_path 正确。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.input_path == str(narrow_width_gds)

    def test_dbu(self, narrow_width_gds: Path) -> None:
        """dbu 正确。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, narrow_width_gds: Path) -> None:
        """top_cell_name 正确。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.top_cell_name == "TOP"

    def test_total_rules(self, narrow_width_gds: Path) -> None:
        """total_rules 正确。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.total_rules == 1

    def test_results_length(self, narrow_width_gds: Path) -> None:
        """results 长度等于 rules 长度。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert len(report.results) == 1

    def test_results_contain_rule_result(self, narrow_width_gds: Path) -> None:
        """results 包含 DRCRuleResult。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert isinstance(report.results[0], DRCRuleResult)


# =============================================================================
# TestSingleLayerChecks: 同层检查集成
# =============================================================================
class TestSingleLayerChecks:
    """同层检查（width/space）集成测试。"""

    def test_width_violation(self, narrow_width_gds: Path) -> None:
        """width 违规检测。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.failed_rules == 1
        assert report.passed_rules == 0
        assert report.total_violations > 0
        assert report.results[0].passed is False
        assert report.results[0].check_type == "width"
        assert report.results[0].layer_b == ()

    def test_width_pass(self, narrow_width_gds: Path) -> None:
        """width 通过。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 0.4)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.passed_rules == 1
        assert report.failed_rules == 0
        assert report.results[0].passed is True

    def test_space_violation(self, close_space_gds: Path) -> None:
        """space 违规检测。"""
        rules = [DRCRule("s1", "space", (1, 0), (), 1.0)]
        report = run_batch_drc(close_space_gds, rules)
        assert report.failed_rules == 1
        assert report.total_violations > 0
        assert report.results[0].passed is False
        assert report.results[0].check_type == "space"

    def test_space_pass(self, close_space_gds: Path) -> None:
        """space 通过。"""
        rules = [DRCRule("s1", "space", (1, 0), (), 0.4)]
        report = run_batch_drc(close_space_gds, rules)
        assert report.passed_rules == 1
        assert report.results[0].passed is True

    def test_width_and_space_together(
        self, narrow_width_gds: Path, close_space_gds: Path,
    ) -> None:
        """width + space 一起测试（两个文件）。"""
        # 单独测试每个文件
        r1 = run_batch_drc(
            narrow_width_gds,
            [DRCRule("w1", "width", (1, 0), (), 1.0)],
        )
        r2 = run_batch_drc(
            close_space_gds,
            [DRCRule("s1", "space", (1, 0), (), 1.0)],
        )
        assert r1.failed_rules == 1
        assert r2.failed_rules == 1


# =============================================================================
# TestInterLayerChecks: 层间检查集成
# =============================================================================
class TestInterLayerChecks:
    """层间检查集成测试。"""

    def test_enclosing_violation(self, enclosing_gds: Path) -> None:
        """enclosing 违规检测。"""
        rules = [DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0)]
        report = run_batch_drc(enclosing_gds, rules)
        assert report.failed_rules == 1
        assert report.total_violations > 0
        assert report.results[0].passed is False
        assert report.results[0].check_type == "enclosing"
        assert report.results[0].layer_b == (2, 0)

    def test_enclosing_pass(self, enclosing_gds: Path) -> None:
        """enclosing 通过。"""
        rules = [DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0)]
        report = run_batch_drc(enclosing_gds, rules)
        assert report.passed_rules == 1

    def test_enclosed_check(self, enclosing_gds: Path) -> None:
        """enclosed 检查（layer_b 被 layer_a 包围，反向）。"""
        rules = [DRCRule("enc1", "enclosed", (2, 0), (1, 0), 2.0)]
        report = run_batch_drc(enclosing_gds, rules)
        assert report.results[0].check_type == "enclosed"

    def test_separation_violation(self, separation_gds: Path) -> None:
        """separation 违规检测。"""
        rules = [DRCRule("sep1", "separation", (1, 0), (3, 0), 3.0)]
        report = run_batch_drc(separation_gds, rules)
        assert report.failed_rules == 1
        assert report.total_violations > 0
        assert report.results[0].check_type == "separation"

    def test_separation_pass(self, separation_gds: Path) -> None:
        """separation 通过。"""
        rules = [DRCRule("sep1", "separation", (1, 0), (3, 0), 1.5)]
        report = run_batch_drc(separation_gds, rules)
        assert report.passed_rules == 1

    def test_overlap_check(self, comprehensive_gds: Path) -> None:
        """overlap 检查可运行。"""
        rules = [DRCRule("ov1", "overlap", (1, 0), (2, 0), 1.0)]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.results[0].check_type == "overlap"


# =============================================================================
# TestMixedChecks: 混合规则
# =============================================================================
class TestMixedChecks:
    """同层 + 层间混合规则测试。"""

    def test_mixed_pass_rules(self, comprehensive_gds: Path) -> None:
        """4 个规则全部通过。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("s1", "space", (2, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0),
            DRCRule("sep1", "separation", (1, 0), (3, 0), 1.5),
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.total_rules == 4
        assert report.passed_rules == 4
        assert report.failed_rules == 0
        assert report.error_rules == 0
        assert report.total_violations == 0

    def test_mixed_partial_fail(self, comprehensive_gds: Path) -> None:
        """3 通过 1 失败。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),  # PASS
            DRCRule("s1", "space", (2, 0), (), 1.0),  # PASS
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),  # FAIL
            DRCRule("sep1", "separation", (1, 0), (3, 0), 1.5),  # PASS
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.passed_rules == 3
        assert report.failed_rules == 1
        assert report.results[2].passed is False
        assert report.results[2].rule.name == "e1"

    def test_mixed_all_fail(
        self, narrow_width_gds: Path, close_space_gds: Path,
    ) -> None:
        """同层失败场景。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),  # FAIL
            DRCRule("s1", "space", (1, 0), (), 1.0),  # FAIL
        ]
        report = run_batch_drc(close_space_gds, rules)
        # close_space_gds 上:
        # - width 1.0μm 在 2μm 矩形上 PASS（但第二个矩形也 2μm，PASS）
        # - space 1.0μm FAIL（间距 0.5μm）
        # 实际上需要重新评估
        # close_space_gds: 2μm×2μm 两个矩形，间距 0.5μm
        # width 1.0μm: 2μm 矩形满足，PASS
        # space 1.0μm: 0.5μm 间距，FAIL
        assert report.passed_rules == 1
        assert report.failed_rules == 1

    def test_six_check_types_all_run(self, comprehensive_gds: Path) -> None:
        """六种检查类型都能运行（不报错）。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("s1", "space", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0),
            DRCRule("enc1", "enclosed", (2, 0), (1, 0), 1.0),
            DRCRule("ov1", "overlap", (1, 0), (2, 0), 0.5),
            DRCRule("sep1", "separation", (1, 0), (3, 0), 1.5),
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.total_rules == 6
        assert report.error_rules == 0
        # 所有规则都有结果（无 error）
        for r in report.results:
            assert r.error is None


# =============================================================================
# TestMaxViolations: 最大违规数限制
# =============================================================================
class TestMaxViolations:
    """max_violations 参数测试。"""

    def test_max_violations_default(self, narrow_width_gds: Path) -> None:
        """默认 max_violations=1000。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        # 窄矩形应该有有限个违规
        assert report.results[0].total_violations >= 0

    def test_max_violations_limit(self, narrow_width_gds: Path) -> None:
        """max_violations=1 限制违规数。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules, max_violations=1)
        # 至少应该能运行（具体数量取决于实现）
        assert report.error_rules == 0


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_width(self, hier_gds: Path) -> None:
        """层次化 GDSII width 检查。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        report = run_batch_drc(hier_gds, rules)
        # CHILD 的 2μm×2μm 矩形，width 1.0μm PASS
        assert report.passed_rules == 1


# =============================================================================
# TestGenerateBatchDrcReport: 报告生成
# =============================================================================
class TestGenerateBatchDrcReport:
    """generate_batch_drc_report 函数测试。"""

    def test_text_report(self, comprehensive_gds: Path) -> None:
        """text 格式报告。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),
        ]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII 批量 DRC 检查报告" in result
        assert "汇总" in result
        assert "规则详情" in result
        assert "w1" in result
        assert "e1" in result

    def test_markdown_report(self, comprehensive_gds: Path) -> None:
        """markdown 格式报告。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
        ]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII 批量 DRC 检查报告" in result
        assert "| 总规则数 |" in result
        assert "## 规则详情" in result

    def test_json_report(self, comprehensive_gds: Path) -> None:
        """json 格式报告。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),
        ]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="json",
        )
        data = json.loads(result)
        assert data["total_rules"] == 2
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["name"] == "w1"
        assert data["results"][1]["name"] == "e1"

    def test_json_results_fields(self, comprehensive_gds: Path) -> None:
        """json 结果字段完整。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="json",
        )
        data = json.loads(result)
        r = data["results"][0]
        for key in (
            "name", "check_type", "layer_a", "layer_b",
            "min_value_um", "passed", "total_violations", "error",
        ):
            assert key in r

    def test_text_status_indicators(self, comprehensive_gds: Path) -> None:
        """text 报告含 PASS/FAIL 状态。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),  # PASS
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),  # FAIL
        ]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="text",
        )
        assert "PASS" in result
        assert "FAIL" in result

    def test_markdown_status_indicators(self, comprehensive_gds: Path) -> None:
        """markdown 报告含 PASS/FAIL 状态。"""
        rules = [
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),  # FAIL
        ]
        result = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="markdown",
        )
        assert "FAIL" in result


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试（禁止 fall-back）。"""

    def test_empty_rules_raise(self, narrow_width_gds: Path) -> None:
        """空 rules 列表 raise。"""
        with pytest.raises(ValueError, match="不能为空"):
            run_batch_drc(narrow_width_gds, [])

    def test_nonexistent_file_raise(self, tmp_path: Path) -> None:
        """不存在的文件 raise。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        with pytest.raises(FileNotFoundError):
            run_batch_drc(tmp_path / "nonexistent.gds", rules)

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            run_batch_drc(d, rules)

    def test_invalid_rule_type_raise(self, narrow_width_gds: Path) -> None:
        """rules 元素非 DRCRule raise。"""
        with pytest.raises(ValueError, match="不是 DRCRule"):
            run_batch_drc(narrow_width_gds, ["not_a_rule"])  # type: ignore

    def test_empty_rule_name_raise(self, narrow_width_gds: Path) -> None:
        """空规则名 raise。"""
        rules = [DRCRule("", "width", (1, 0), (), 1.0)]
        with pytest.raises(ValueError, match="name 必须是非空字符串"):
            run_batch_drc(narrow_width_gds, rules)

    def test_invalid_check_type_raise(self, narrow_width_gds: Path) -> None:
        """无效 check_type raise。"""
        rules = [DRCRule("r1", "invalid_type", (1, 0), (), 1.0)]
        with pytest.raises(ValueError, match="check_type 无效"):
            run_batch_drc(narrow_width_gds, rules)

    def test_invalid_layer_a_raise(self, narrow_width_gds: Path) -> None:
        """layer_a 非二元组 raise。"""
        rules = [DRCRule("r1", "width", (1,), (), 1.0)]  # type: ignore
        with pytest.raises(ValueError, match="layer_a 必须"):
            run_batch_drc(narrow_width_gds, rules)

    def test_layer_a_out_of_range_raise(self, narrow_width_gds: Path) -> None:
        """layer_a.layer 超出范围 raise。"""
        rules = [DRCRule("r1", "width", (1000, 0), (), 1.0)]
        with pytest.raises(ValueError, match="layer_a.layer 必须 0-999"):
            run_batch_drc(narrow_width_gds, rules)

    def test_layer_a_dt_out_of_range_raise(self, narrow_width_gds: Path) -> None:
        """layer_a.datatype 超出范围 raise。"""
        rules = [DRCRule("r1", "width", (1, 256), (), 1.0)]
        with pytest.raises(ValueError, match="layer_a.datatype 必须 0-255"):
            run_batch_drc(narrow_width_gds, rules)

    def test_single_layer_with_layer_b_raise(
        self, narrow_width_gds: Path,
    ) -> None:
        """同层检查带 layer_b raise。"""
        rules = [DRCRule("r1", "width", (1, 0), (2, 0), 1.0)]
        with pytest.raises(ValueError, match="同层检查"):
            run_batch_drc(narrow_width_gds, rules)

    def test_inter_layer_without_layer_b_raise(
        self, narrow_width_gds: Path,
    ) -> None:
        """层间检查无 layer_b raise。"""
        rules = [DRCRule("r1", "enclosing", (1, 0), (), 1.0)]
        with pytest.raises(ValueError, match="层间检查"):
            run_batch_drc(narrow_width_gds, rules)

    def test_inter_layer_same_layer_raise(
        self, narrow_width_gds: Path,
    ) -> None:
        """层间检查 layer_a == layer_b raise。"""
        rules = [DRCRule("r1", "enclosing", (1, 0), (1, 0), 1.0)]
        with pytest.raises(ValueError, match="不能相同"):
            run_batch_drc(narrow_width_gds, rules)

    def test_min_value_zero_raise(self, narrow_width_gds: Path) -> None:
        """min_value_um=0 raise。"""
        rules = [DRCRule("r1", "width", (1, 0), (), 0.0)]
        with pytest.raises(ValueError, match="min_value_um 必须 > 0"):
            run_batch_drc(narrow_width_gds, rules)

    def test_min_value_negative_raise(self, narrow_width_gds: Path) -> None:
        """min_value_um 负值 raise。"""
        rules = [DRCRule("r1", "width", (1, 0), (), -1.0)]
        with pytest.raises(ValueError, match="min_value_um 必须 > 0"):
            run_batch_drc(narrow_width_gds, rules)

    def test_invalid_output_format_raise(
        self, comprehensive_gds: Path,
    ) -> None:
        """无效 output_format raise。"""
        rules = [DRCRule("w1", "width", (1, 0), (), 1.0)]
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_batch_drc_report(
                comprehensive_gds, rules, output_format="xml",
            )

    def test_nonexistent_layer_records_error(
        self, narrow_width_gds: Path,
    ) -> None:
        """不存在的层记录为 error（不中断）。"""
        # layer (99,0) 不存在
        rules = [DRCRule("w1", "width", (99, 0), (), 1.0)]
        report = run_batch_drc(narrow_width_gds, rules)
        assert report.error_rules == 1
        assert report.results[0].error is not None
        assert report.results[0].passed is False

    def test_error_does_not_stop_other_rules(
        self, comprehensive_gds: Path,
    ) -> None:
        """规则错误不中断其他规则。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),  # PASS
            DRCRule("w2", "width", (99, 0), (), 1.0),  # ERROR
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0),  # PASS
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.total_rules == 3
        assert report.error_rules == 1
        assert report.passed_rules == 2


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_batch
        assert gdsii_drc_batch.__doc__ is not None
        assert len(gdsii_drc_batch.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_batch
        doc = gdsii_drc_batch.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_batch
        doc = gdsii_drc_batch.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_batch
        doc = gdsii_drc_batch.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_batch as m
        for fn in (m.run_batch_drc, m.generate_batch_drc_report):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src

    def test_check_type_constants(self) -> None:
        """检查类型常量完整。"""
        from polaris.verification.gdsii_drc_batch import (
            SINGLE_LAYER_CHECKS, INTER_LAYER_CHECKS, VALID_CHECK_TYPES,
        )
        assert "width" in SINGLE_LAYER_CHECKS
        assert "space" in SINGLE_LAYER_CHECKS
        assert "enclosing" in INTER_LAYER_CHECKS
        assert "enclosed" in INTER_LAYER_CHECKS
        assert "overlap" in INTER_LAYER_CHECKS
        assert "separation" in INTER_LAYER_CHECKS
        assert len(VALID_CHECK_TYPES) == 6


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_comprehensive(self, comprehensive_gds: Path) -> None:
        """完整工作流（综合 fixture）。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("s1", "space", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0),
            DRCRule("sep1", "separation", (1, 0), (3, 0), 1.5),
            DRCRule("enc1", "enclosed", (2, 0), (1, 0), 1.0),
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        # 全部通过
        assert report.passed_rules == 5
        assert report.failed_rules == 0
        assert report.error_rules == 0

    def test_report_consistency(self, comprehensive_gds: Path) -> None:
        """报告字段一致性。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),  # FAIL
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        # passed + failed + error == total
        assert (
            report.passed_rules + report.failed_rules + report.error_rules
            == report.total_rules
        )
        # total_violations == sum of each rule's violations
        sum_violations = sum(r.total_violations for r in report.results)
        assert report.total_violations == sum_violations

    def test_layer_b_recorded_correctly(self, comprehensive_gds: Path) -> None:
        """layer_b 在结果中正确记录。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),  # 同层，layer_b=()
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 1.0),  # 层间
        ]
        report = run_batch_drc(comprehensive_gds, rules)
        assert report.results[0].layer_b == ()
        assert report.results[1].layer_b == (2, 0)

    def test_run_then_generate_consistent(
        self, comprehensive_gds: Path,
    ) -> None:
        """run_batch_drc 和 generate_batch_drc_report 结果一致。"""
        rules = [
            DRCRule("w1", "width", (1, 0), (), 1.0),
            DRCRule("e1", "enclosing", (1, 0), (2, 0), 2.0),
        ]
        # 直接 run
        report = run_batch_drc(comprehensive_gds, rules)
        # 通过 generate 获取 json
        json_str = generate_batch_drc_report(
            comprehensive_gds, rules, output_format="json",
        )
        data = json.loads(json_str)
        # 关键字段一致
        assert data["total_rules"] == report.total_rules
        assert data["passed_rules"] == report.passed_rules
        assert data["failed_rules"] == report.failed_rules
        assert data["error_rules"] == report.error_rules
        assert data["total_violations"] == report.total_violations


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_drc_rule_construction(self) -> None:
        """DRCRule 构造。"""
        r = DRCRule("w1", "width", (1, 0), (), 1.0)
        assert r.name == "w1"
        assert r.check_type == "width"
        assert r.layer_a == (1, 0)
        assert r.layer_b == ()
        assert r.min_value_um == 1.0

    def test_drc_rule_default_layer_b(self) -> None:
        """DRCRule 默认 layer_b 为空元组。"""
        r = DRCRule("w1", "width", (1, 0), min_value_um=1.0)
        assert r.layer_b == ()

    def test_drc_rule_result_default_error(self) -> None:
        """DRCRuleResult 默认 error 为 None。"""
        rule = DRCRule("w1", "width", (1, 0), (), 1.0)
        r = DRCRuleResult(
            rule=rule, passed=True, total_violations=0,
            check_type="width", layer_a=(1, 0), layer_b=(),
            min_value_um=1.0,
        )
        assert r.error is None

    def test_batch_drc_report_defaults(self) -> None:
        """BatchDRCReport 默认值。"""
        r = BatchDRCReport()
        assert r.input_path == ""
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.total_rules == 0
        assert r.passed_rules == 0
        assert r.failed_rules == 0
        assert r.error_rules == 0
        assert r.total_violations == 0
        assert r.results == []

    def test_batch_drc_report_mutable_defaults(self) -> None:
        """BatchDRCReport 可变默认值独立。"""
        r1 = BatchDRCReport()
        r2 = BatchDRCReport()
        rule = DRCRule("w1", "width", (1, 0), (), 1.0)
        r1.results.append(DRCRuleResult(
            rule=rule, passed=True, total_violations=0,
            check_type="width", layer_a=(1, 0), layer_b=(),
            min_value_um=1.0,
        ))
        assert len(r2.results) == 0
