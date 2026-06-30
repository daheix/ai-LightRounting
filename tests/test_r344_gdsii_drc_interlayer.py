"""R344 GDSII DRC 层间检查工具测试。

覆盖:
- check_enclosing / check_enclosed / check_overlap / check_separation
- generate_interlayer_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region enclosing_check: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_interlayer import (
    InterLayerDRCReport,
    InterLayerDRCViolation,
    check_enclosing,
    check_enclosed,
    check_overlap,
    check_separation,
    generate_interlayer_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_enclosing_gds(path: Path) -> Path:
    """创建包围 GDSII（layer_a 5x5 包围 layer_b 3x3，每边大 1μm）。

    layer (1,0): Box(0,0)-(5000,5000) = 5x5μm
    layer (2,0): Box(1000,1000)-(4000,4000) = 3x3μm
    enclosing_check(2.0μm): 4 个违规（每边大 1μm < 2μm）
    enclosing_check(1.0μm): 0 个违规
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
    """创建间距 GDSII（layer_a 和 layer_c 间距 2μm）。

    layer (1,0): Box(0,0)-(1000,1000)
    layer (3,0): Box(3000,0)-(4000,1000)
    间距 = 2μm
    separation_check(3.0μm): 1 个违规
    separation_check(2.0μm): 0 个违规
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


def _make_overlap_gds(path: Path) -> Path:
    """创建重叠 GDSII（layer_a 和 layer_d 重叠 1x1μm）。

    layer (1,0): Box(0,0)-(2000,2000) = 2x2μm
    layer (4,0): Box(1000,1000)-(3000,3000) = 2x2μm
    重叠区域 = (1000,1000)-(2000,2000) = 1x1μm
    overlap_check(2.0μm): 2 个违规
    overlap_check(1.0μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    la = ly.layer(1, 0)
    ld = ly.layer(4, 0)
    top = ly.create_cell("TOP")
    top.shapes(la).insert(db.Box(0, 0, 2000, 2000))
    top.shapes(ld).insert(db.Box(1000, 1000, 3000, 3000))
    ly.write(str(path))
    return path


@pytest.fixture
def enclosing_gds(tmp_path: Path) -> Path:
    """包围 GDSII。"""
    return _make_enclosing_gds(tmp_path / "enc.gds")


@pytest.fixture
def separation_gds(tmp_path: Path) -> Path:
    """间距 GDSII。"""
    return _make_separation_gds(tmp_path / "sep.gds")


@pytest.fixture
def overlap_gds(tmp_path: Path) -> Path:
    """重叠 GDSII。"""
    return _make_overlap_gds(tmp_path / "ovl.gds")


# =============================================================================
# TestCheckEnclosing: enclosing 检查
# =============================================================================
class TestCheckEnclosing:
    """check_enclosing 函数测试。"""

    def test_returns_report(self, enclosing_gds: Path) -> None:
        """返回 InterLayerDRCReport。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert isinstance(r, InterLayerDRCReport)

    def test_check_type(self, enclosing_gds: Path) -> None:
        """check_type 为 'enclosing'。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.check_type == "enclosing"

    def test_layers_recorded(self, enclosing_gds: Path) -> None:
        """层信息记录正确。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.layer_a == (1, 0)
        assert r.layer_b == (2, 0)

    def test_violation_count(self, enclosing_gds: Path) -> None:
        """5x5 包围 3x3，阈值 2μm: 4 个违规。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.total_violations == 4

    def test_no_violation(self, enclosing_gds: Path) -> None:
        """5x5 包围 3x3，阈值 1μm: 0 个违规。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 1.0)
        assert r.total_violations == 0

    def test_violation_bbox(self, enclosing_gds: Path) -> None:
        """违规区域 bbox 不为 None。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.bbox is not None

    def test_no_violation_no_bbox(self, enclosing_gds: Path) -> None:
        """无违规时 bbox 为 None。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 1.0)
        assert r.bbox is None

    def test_min_value_recorded(self, enclosing_gds: Path) -> None:
        """min_value_um 记录正确。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.min_value_um == pytest.approx(2.0)


# =============================================================================
# TestCheckEnclosed: enclosed 检查
# =============================================================================
class TestCheckEnclosed:
    """check_enclosed 函数测试。"""

    def test_check_type(self, enclosing_gds: Path) -> None:
        """check_type 为 'enclosed'。"""
        r = check_enclosed(enclosing_gds, (2, 0), (1, 0), 2.0)
        assert r.check_type == "enclosed"

    def test_violation_count(self, enclosing_gds: Path) -> None:
        """3x3 被 5x5 包围，阈值 2μm: 4 个违规。"""
        r = check_enclosed(enclosing_gds, (2, 0), (1, 0), 2.0)
        assert r.total_violations == 4

    def test_no_violation(self, enclosing_gds: Path) -> None:
        """3x3 被 5x5 包围，阈值 1μm: 0 个违规。"""
        r = check_enclosed(enclosing_gds, (2, 0), (1, 0), 1.0)
        assert r.total_violations == 0


# =============================================================================
# TestCheckSeparation: separation 检查
# =============================================================================
class TestCheckSeparation:
    """check_separation 函数测试。"""

    def test_check_type(self, separation_gds: Path) -> None:
        """check_type 为 'separation'。"""
        r = check_separation(separation_gds, (1, 0), (3, 0), 3.0)
        assert r.check_type == "separation"

    def test_violation_count(self, separation_gds: Path) -> None:
        """间距 2μm，阈值 3μm: 1 个违规。"""
        r = check_separation(separation_gds, (1, 0), (3, 0), 3.0)
        assert r.total_violations == 1

    def test_no_violation(self, separation_gds: Path) -> None:
        """间距 2μm，阈值 2μm: 0 个违规。"""
        r = check_separation(separation_gds, (1, 0), (3, 0), 2.0)
        assert r.total_violations == 0

    def test_violation_distance(self, separation_gds: Path) -> None:
        """违规距离 = 2μm（实际间距）。"""
        r = check_separation(separation_gds, (1, 0), (3, 0), 3.0)
        assert len(r.violations) == 1
        v = r.violations[0]
        assert v.distance_um == pytest.approx(2.0, rel=1e-6)


# =============================================================================
# TestCheckOverlap: overlap 检查
# =============================================================================
class TestCheckOverlap:
    """check_overlap 函数测试。"""

    def test_check_type(self, overlap_gds: Path) -> None:
        """check_type 为 'overlap'。"""
        r = check_overlap(overlap_gds, (1, 0), (4, 0), 2.0)
        assert r.check_type == "overlap"

    def test_violation_count(self, overlap_gds: Path) -> None:
        """重叠 1μm，阈值 2μm: 2 个违规。"""
        r = check_overlap(overlap_gds, (1, 0), (4, 0), 2.0)
        assert r.total_violations == 2

    def test_no_violation(self, overlap_gds: Path) -> None:
        """重叠 1μm，阈值 1μm: 0 个违规。"""
        r = check_overlap(overlap_gds, (1, 0), (4, 0), 1.0)
        assert r.total_violations == 0


# =============================================================================
# TestGenerateReport: 报告生成
# =============================================================================
class TestGenerateReport:
    """generate_interlayer_drc_report 函数测试。"""

    def test_text_enclosing(self, enclosing_gds: Path) -> None:
        """text 报告（enclosing）。"""
        s = generate_interlayer_drc_report(
            enclosing_gds, (1, 0), (2, 0), "enclosing", 2.0,
            output_format="text",
        )
        assert "ENCLOSING" in s
        assert "违规总数" in s

    def test_text_separation(self, separation_gds: Path) -> None:
        """text 报告（separation）。"""
        s = generate_interlayer_drc_report(
            separation_gds, (1, 0), (3, 0), "separation", 3.0,
            output_format="text",
        )
        assert "SEPARATION" in s

    def test_markdown(self, enclosing_gds: Path) -> None:
        """markdown 报告。"""
        s = generate_interlayer_drc_report(
            enclosing_gds, (1, 0), (2, 0), "enclosing", 2.0,
            output_format="markdown",
        )
        assert "# GDSII 层间 DRC ENCLOSING 检查报告" in s

    def test_json(self, enclosing_gds: Path) -> None:
        """json 报告。"""
        s = generate_interlayer_drc_report(
            enclosing_gds, (1, 0), (2, 0), "enclosing", 2.0,
            output_format="json",
        )
        data = json.loads(s)
        assert data["check_type"] == "enclosing"
        assert data["total_violations"] == 4
        assert data["layer_a"] == [1, 0]
        assert data["layer_b"] == [2, 0]

    def test_json_no_violation(self, enclosing_gds: Path) -> None:
        """json 报告（无违规）。"""
        s = generate_interlayer_drc_report(
            enclosing_gds, (1, 0), (2, 0), "enclosing", 1.0,
            output_format="json",
        )
        data = json.loads(s)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_enclosing(tmp_path / "nonexistent.gds", (1, 0), (2, 0), 2.0)

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            check_enclosing(tmp_path, (1, 0), (2, 0), 2.0)

    def test_same_layers(self, enclosing_gds: Path) -> None:
        """layer_a == layer_b raise ValueError。"""
        with pytest.raises(ValueError, match="不能相同"):
            check_enclosing(enclosing_gds, (1, 0), (1, 0), 2.0)

    def test_invalid_layer(self, enclosing_gds: Path) -> None:
        """layer 超范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-999"):
            check_enclosing(enclosing_gds, (1000, 0), (2, 0), 2.0)

    def test_invalid_datatype(self, enclosing_gds: Path) -> None:
        """datatype 超范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-255"):
            check_enclosing(enclosing_gds, (1, 256), (2, 0), 2.0)

    def test_min_value_zero(self, enclosing_gds: Path) -> None:
        """min_value=0 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            check_enclosing(enclosing_gds, (1, 0), (2, 0), 0.0)

    def test_min_value_negative(self, enclosing_gds: Path) -> None:
        """min_value 负 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            check_enclosing(enclosing_gds, (1, 0), (2, 0), -1.0)

    def test_invalid_max_violations(self, enclosing_gds: Path) -> None:
        """max_violations <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="max_violations"):
            check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0, max_violations=0)

    def test_layer_a_not_found(self, enclosing_gds: Path) -> None:
        """layer_a 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="layer_a"):
            check_enclosing(enclosing_gds, (99, 99), (2, 0), 2.0)

    def test_layer_b_not_found(self, enclosing_gds: Path) -> None:
        """layer_b 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="layer_b"):
            check_enclosing(enclosing_gds, (1, 0), (99, 99), 2.0)

    def test_top_cell_not_found(self, enclosing_gds: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0, top_cell_name="X")

    def test_unsupported_check_type(self, enclosing_gds: Path) -> None:
        """不支持的 check_type raise ValueError。"""
        with pytest.raises(ValueError, match="check_type"):
            generate_interlayer_drc_report(
                enclosing_gds, (1, 0), (2, 0), "invalid", 2.0
            )

    def test_unsupported_format(self, enclosing_gds: Path) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="output_format"):
            generate_interlayer_drc_report(
                enclosing_gds, (1, 0), (2, 0), "enclosing", 2.0,
                output_format="xml",
            )


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块有 docstring。"""
        from polaris.verification import gdsii_drc_interlayer
        assert gdsii_drc_interlayer.__doc__ is not None
        assert len(gdsii_drc_interlayer.__doc__) > 100

    def test_module_docstring_has_api_facts(self) -> None:
        """docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_drc_interlayer
        doc = gdsii_drc_interlayer.__doc__
        assert "enclosing_check" in doc
        assert "enclosed_check" in doc
        assert "overlap_check" in doc
        assert "separation_check" in doc
        assert "EdgePairs" in doc

    def test_module_docstring_has_references(self) -> None:
        """docstring 含 ≥5 个文献 URL。"""
        from polaris.verification import gdsii_drc_interlayer
        doc = gdsii_drc_interlayer.__doc__
        urls = [w for w in doc.split() if w.startswith("http")]
        assert len(urls) >= 5

    def test_module_docstring_has_region_url(self) -> None:
        """docstring 含 KLayout Region class URL。"""
        from polaris.verification import gdsii_drc_interlayer
        assert "class_Region.html" in gdsii_drc_interlayer.__doc__

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_interlayer
        doc = gdsii_drc_interlayer.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_interlayer as m
        for fn in (m.check_enclosing, m.check_enclosed, m.check_overlap, m.check_separation):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_enclosing_workflow(self, enclosing_gds: Path) -> None:
        """enclosing 完整工作流。"""
        r = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        assert r.check_type == "enclosing"
        assert r.total_violations == 4
        assert len(r.violations) == 4
        assert r.bbox is not None

    def test_separation_workflow(self, separation_gds: Path) -> None:
        """separation 完整工作流。"""
        r = check_separation(separation_gds, (1, 0), (3, 0), 3.0)
        assert r.check_type == "separation"
        assert r.total_violations == 1
        v = r.violations[0]
        assert v.distance_um == pytest.approx(2.0, rel=1e-6)

    def test_all_four_checks(self, enclosing_gds: Path) -> None:
        """四种检查都能运行。"""
        r1 = check_enclosing(enclosing_gds, (1, 0), (2, 0), 2.0)
        r2 = check_enclosed(enclosing_gds, (2, 0), (1, 0), 2.0)
        assert r1.check_type == "enclosing"
        assert r2.check_type == "enclosed"
        assert r1.total_violations > 0
        assert r2.total_violations > 0


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_default(self) -> None:
        """InterLayerDRCViolation 字段。"""
        v = InterLayerDRCViolation(
            0, 0, 1, 0, 1, 0, 2, 0, 1.0
        )
        assert v.distance_um == 1.0

    def test_report_default(self) -> None:
        """InterLayerDRCReport 默认值。"""
        r = InterLayerDRCReport()
        assert r.input_path == ""
        assert r.check_type == ""
        assert r.layer_a == (0, 0)
        assert r.layer_b == (0, 0)
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """InterLayerDRCReport 可变默认值独立。"""
        r1 = InterLayerDRCReport()
        r2 = InterLayerDRCReport()
        r1.violations.append(InterLayerDRCViolation(0, 0, 0, 0, 0, 0, 0, 0, 0.0))
        assert len(r2.violations) == 0
