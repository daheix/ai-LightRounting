"""R343 GDSII DRC width/space 检查工具测试。

覆盖:
- check_width: 窄矩形违规、宽矩形无违规、多违规
- check_space: 近矩形违规、远矩形无违规、多违规
- generate_drc_report: text/markdown/json 报告
- R03 错误处理（禁止 fall-back）
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region width_check: https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs: https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_width_space import (
    DRCReport,
    DRCViolation,
    check_width,
    check_space,
    generate_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_narrow_rect_gds(path: Path) -> Path:
    """创建窄矩形 GDSII（宽度 1μm < 2μm 阈值）。

    layer (1,0): Box(0,0)-(1000,5000) = 1μm×5μm
    dbu = 0.001μm
    width_check(2.0μm): 1 个违规，距离 1μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 5000))
    ly.write(str(path))
    return path


def _make_wide_rect_gds(path: Path) -> Path:
    """创建宽矩形 GDSII（宽度 5μm > 2μm 阈值，无违规）。

    layer (1,0): Box(0,0)-(5000,5000) = 5μm×5μm
    width_check(2.0μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 5000, 5000))
    ly.write(str(path))
    return path


def _make_close_rects_gds(path: Path) -> Path:
    """创建相近矩形 GDSII（间距 2μm < 3μm 阈值）。

    layer (1,0):
    - Box(0,0)-(1000,1000)
    - Box(3000,0)-(4000,1000)
    间距 = 2μm
    space_check(3.0μm): 1 个违规，距离 2μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(3000, 0, 4000, 1000))
    ly.write(str(path))
    return path


def _make_far_rects_gds(path: Path) -> Path:
    """创建远距离矩形 GDSII（间距 10μm > 3μm 阈值，无违规）。

    layer (1,0):
    - Box(0,0)-(1000,1000)
    - Box(11000,0)-(12000,1000)
    间距 = 10μm
    space_check(3.0μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(11000, 0, 12000, 1000))
    ly.write(str(path))
    return path


def _make_multi_narrow_gds(path: Path) -> Path:
    """创建多个窄矩形 GDSII（3 个 1μm 宽矩形，width_check 有 3 个违规）。

    layer (1,0):
    - Box(0,0)-(1000,5000)     1μm 宽
    - Box(5000,0)-(6000,5000)  1μm 宽
    - Box(10000,0)-(11000,5000) 1μm 宽
    width_check(2.0μm): 3 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 5000))
    top.shapes(li).insert(db.Box(5000, 0, 6000, 5000))
    top.shapes(li).insert(db.Box(10000, 0, 11000, 5000))
    ly.write(str(path))
    return path


def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含窄矩形）。

    - TOP cell
      - CHILD @ (0, 0)
    - CHILD cell
      - layer (1,0): Box(0,0)-(1000,5000) = 1μm×5μm
    width_check(2.0μm): 1 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(0, 0, 1000, 5000))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def narrow_rect_gds(tmp_path: Path) -> Path:
    """窄矩形 GDSII。"""
    return _make_narrow_rect_gds(tmp_path / "narrow.gds")


@pytest.fixture
def wide_rect_gds(tmp_path: Path) -> Path:
    """宽矩形 GDSII。"""
    return _make_wide_rect_gds(tmp_path / "wide.gds")


@pytest.fixture
def close_rects_gds(tmp_path: Path) -> Path:
    """相近矩形 GDSII。"""
    return _make_close_rects_gds(tmp_path / "close.gds")


@pytest.fixture
def far_rects_gds(tmp_path: Path) -> Path:
    """远距离矩形 GDSII。"""
    return _make_far_rects_gds(tmp_path / "far.gds")


@pytest.fixture
def multi_narrow_gds(tmp_path: Path) -> Path:
    """多个窄矩形 GDSII。"""
    return _make_multi_narrow_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckWidth: width 检查
# =============================================================================
class TestCheckWidth:
    """check_width 函数测试。"""

    def test_returns_report(self, narrow_rect_gds: Path) -> None:
        """返回 DRCReport。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert isinstance(report, DRCReport)

    def test_check_type(self, narrow_rect_gds: Path) -> None:
        """check_type 为 'width'。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.check_type == "width"

    def test_input_path(self, narrow_rect_gds: Path) -> None:
        """input_path 正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.input_path == str(narrow_rect_gds)

    def test_dbu(self, narrow_rect_gds: Path) -> None:
        """dbu 正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, narrow_rect_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.top_cell_name == "TOP"

    def test_layer_recorded(self, narrow_rect_gds: Path) -> None:
        """层信息记录正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.layer == (1, 0)

    def test_min_value_recorded(self, narrow_rect_gds: Path) -> None:
        """min_value_um 记录正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.min_value_um == pytest.approx(2.0)

    def test_narrow_violation(self, narrow_rect_gds: Path) -> None:
        """窄矩形 1μm 宽，阈值 2μm: 1 个违规。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.total_violations == 1

    def test_wide_no_violation(self, wide_rect_gds: Path) -> None:
        """宽矩形 5μm 宽，阈值 2μm: 0 个违规。"""
        report = check_width(wide_rect_gds, (1, 0), 2.0)
        assert report.total_violations == 0

    def test_violation_distance(self, narrow_rect_gds: Path) -> None:
        """违规距离 = 1μm（矩形宽度）。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.distance_um == pytest.approx(1.0, rel=1e-6)

    def test_violation_bbox(self, narrow_rect_gds: Path) -> None:
        """违规区域 bbox 正确。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        # 窄矩形 (0,0)-(1,5)μm
        assert xmin == pytest.approx(0.0, abs=1e-6)
        assert ymin == pytest.approx(0.0, abs=1e-6)
        assert xmax == pytest.approx(1.0, abs=1e-6)
        assert ymax == pytest.approx(5.0, abs=1e-6)

    def test_no_violation_no_bbox(self, wide_rect_gds: Path) -> None:
        """无违规时 bbox 为 None。"""
        report = check_width(wide_rect_gds, (1, 0), 2.0)
        assert report.total_violations == 0
        assert report.bbox is None

    def test_multi_narrow_violations(self, multi_narrow_gds: Path) -> None:
        """3 个窄矩形: 3 个违规。"""
        report = check_width(multi_narrow_gds, (1, 0), 2.0)
        assert report.total_violations == 3
        assert len(report.violations) == 3

    def test_max_violations_limit(self, multi_narrow_gds: Path) -> None:
        """max_violations 限制保留的违规数。"""
        report = check_width(multi_narrow_gds, (1, 0), 2.0, max_violations=2)
        assert report.total_violations == 3  # 实际违规数
        assert len(report.violations) == 2   # 保留 2 条


# =============================================================================
# TestCheckSpace: space 检查
# =============================================================================
class TestCheckSpace:
    """check_space 函数测试。"""

    def test_returns_report(self, close_rects_gds: Path) -> None:
        """返回 DRCReport。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert isinstance(report, DRCReport)

    def test_check_type(self, close_rects_gds: Path) -> None:
        """check_type 为 'space'。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert report.check_type == "space"

    def test_close_violation(self, close_rects_gds: Path) -> None:
        """近矩形间距 2μm，阈值 3μm: 1 个违规。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert report.total_violations == 1

    def test_far_no_violation(self, far_rects_gds: Path) -> None:
        """远矩形间距 10μm，阈值 3μm: 0 个违规。"""
        report = check_space(far_rects_gds, (1, 0), 3.0)
        assert report.total_violations == 0

    def test_violation_distance(self, close_rects_gds: Path) -> None:
        """违规距离 = 2μm（矩形间距）。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.distance_um == pytest.approx(2.0, rel=1e-6)

    def test_violation_bbox(self, close_rects_gds: Path) -> None:
        """违规区域 bbox 正确。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        # 两个矩形 (0,0)-(1,1) 和 (3,0)-(4,1)
        assert xmin == pytest.approx(1.0, abs=1e-6)
        assert xmax == pytest.approx(3.0, abs=1e-6)


# =============================================================================
# TestHierarchical: 层次化
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_width(self, hier_gds: Path) -> None:
        """层次化 GDSII width 检查（递归遍历子 cell）。"""
        report = check_width(hier_gds, (1, 0), 2.0)
        # CHILD 有 1μm 宽矩形，width_check(2.0) 有 1 个违规
        assert report.total_violations == 1


# =============================================================================
# TestGenerateDrcReport: 报告生成
# =============================================================================
class TestGenerateDrcReport:
    """generate_drc_report 函数测试。"""

    def test_text_report_width(self, narrow_rect_gds: Path) -> None:
        """text 报告（width）。"""
        s = generate_drc_report(
            narrow_rect_gds, (1, 0), "width", 2.0, output_format="text"
        )
        assert isinstance(s, str)
        assert "DRC WIDTH 检查报告" in s
        assert "违规总数" in s

    def test_text_report_space(self, close_rects_gds: Path) -> None:
        """text 报告（space）。"""
        s = generate_drc_report(
            close_rects_gds, (1, 0), "space", 3.0, output_format="text"
        )
        assert isinstance(s, str)
        assert "DRC SPACE 检查报告" in s

    def test_markdown_report(self, narrow_rect_gds: Path) -> None:
        """markdown 报告。"""
        s = generate_drc_report(
            narrow_rect_gds, (1, 0), "width", 2.0, output_format="markdown"
        )
        assert "# GDSII DRC WIDTH 检查报告" in s
        assert "## 检查结果" in s

    def test_json_report(self, narrow_rect_gds: Path) -> None:
        """json 报告。"""
        s = generate_drc_report(
            narrow_rect_gds, (1, 0), "width", 2.0, output_format="json"
        )
        data = json.loads(s)
        assert data["check_type"] == "width"
        assert data["total_violations"] == 1
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert "x1_um" in v
        assert "distance_um" in v

    def test_json_report_no_violation(self, wide_rect_gds: Path) -> None:
        """json 报告（无违规）。"""
        s = generate_drc_report(
            wide_rect_gds, (1, 0), "width", 2.0, output_format="json"
        )
        data = json.loads(s)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_contains_violation_details(
        self, narrow_rect_gds: Path
    ) -> None:
        """text 报告含违规详情。"""
        s = generate_drc_report(
            narrow_rect_gds, (1, 0), "width", 2.0, output_format="text"
        )
        assert "违规详情" in s
        assert "first:" in s
        assert "second:" in s

    def test_text_report_no_violation(
        self, wide_rect_gds: Path
    ) -> None:
        """text 报告（无违规）。"""
        s = generate_drc_report(
            wide_rect_gds, (1, 0), "width", 2.0, output_format="text"
        )
        assert "违规总数: 0" in s
        assert "违规详情" not in s


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_width(tmp_path / "nonexistent.gds", (1, 0), 2.0)

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            check_width(tmp_path, (1, 0), 2.0)

    def test_invalid_layer_tuple(self, narrow_rect_gds: Path) -> None:
        """layer 不是 2 元组 raise ValueError。"""
        with pytest.raises(ValueError, match="必须是"):
            check_width(narrow_rect_gds, (1,), 2.0)  # type: ignore

    def test_invalid_layer_out_of_range(self, narrow_rect_gds: Path) -> None:
        """layer 超出范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-999"):
            check_width(narrow_rect_gds, (1000, 0), 2.0)

    def test_invalid_datatype_out_of_range(self, narrow_rect_gds: Path) -> None:
        """datatype 超出范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-255"):
            check_width(narrow_rect_gds, (1, 256), 2.0)

    def test_min_value_zero(self, narrow_rect_gds: Path) -> None:
        """min_value_um = 0 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            check_width(narrow_rect_gds, (1, 0), 0.0)

    def test_min_value_negative(self, narrow_rect_gds: Path) -> None:
        """min_value_um 为负 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            check_width(narrow_rect_gds, (1, 0), -1.0)

    def test_invalid_max_violations(self, narrow_rect_gds: Path) -> None:
        """max_violations <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="max_violations"):
            check_width(narrow_rect_gds, (1, 0), 2.0, max_violations=0)

    def test_invalid_max_violations_negative(self, narrow_rect_gds: Path) -> None:
        """max_violations 为负 raise ValueError。"""
        with pytest.raises(ValueError, match="max_violations"):
            check_width(narrow_rect_gds, (1, 0), 2.0, max_violations=-1)

    def test_layer_not_found(self, narrow_rect_gds: Path) -> None:
        """层不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            check_width(narrow_rect_gds, (99, 99), 2.0)

    def test_top_cell_not_found(self, narrow_rect_gds: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            check_width(narrow_rect_gds, (1, 0), 2.0, top_cell_name="NONEXISTENT")

    def test_unsupported_check_type(self, narrow_rect_gds: Path) -> None:
        """不支持的 check_type raise ValueError。"""
        with pytest.raises(ValueError, match="check_type"):
            generate_drc_report(
                narrow_rect_gds, (1, 0), "overlap", 2.0
            )

    def test_unsupported_format(self, narrow_rect_gds: Path) -> None:
        """不支持的输出格式 raise ValueError。"""
        with pytest.raises(ValueError, match="output_format"):
            generate_drc_report(
                narrow_rect_gds, (1, 0), "width", 2.0, output_format="xml"
            )

    def test_space_file_not_found(self, tmp_path: Path) -> None:
        """space 检查文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_space(tmp_path / "nonexistent.gds", (1, 0), 3.0)

    def test_space_min_value_zero(self, close_rects_gds: Path) -> None:
        """space 检查 min_value=0 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            check_space(close_rects_gds, (1, 0), 0.0)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块有 docstring。"""
        from polaris.verification import gdsii_drc_width_space
        assert gdsii_drc_width_space.__doc__ is not None
        assert len(gdsii_drc_width_space.__doc__) > 100

    def test_module_docstring_has_api_facts(self) -> None:
        """docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        assert "db.Region" in doc
        assert "width_check" in doc
        assert "space_check" in doc
        assert "EdgePairs" in doc
        assert "edge_pairs.count()" in doc
        assert "edge_pair.first" in doc
        assert "edge_pair.distance()" in doc

    def test_module_docstring_has_references(self) -> None:
        """docstring 含 ≥5 个文献 URL。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        urls = [line for line in doc.split() if line.startswith("http")]
        assert len(urls) >= 5, f"只有 {len(urls)} 个 URL"

    def test_module_docstring_has_klayout_region_url(self) -> None:
        """docstring 含 KLayout Region class URL。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        assert "class_Region.html" in doc

    def test_module_docstring_has_klayout_edgepairs_url(self) -> None:
        """docstring 含 KLayout EdgePairs class URL。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        assert "class_EdgePairs.html" in doc

    def test_module_docstring_has_klayout_edgepair_url(self) -> None:
        """docstring 含 KLayout EdgePair class URL。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        assert "class_EdgePair.html" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_width_space
        doc = gdsii_drc_width_space.__doc__
        assert "R01" in doc
        assert "R02" in doc
        assert "R03" in doc
        assert "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_width_space as m
        width_src = m.check_width.__doc__ or ""
        assert "klayout.org" in width_src
        space_src = m.check_space.__doc__ or ""
        assert "klayout.org" in space_src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_width_full_workflow(self, narrow_rect_gds: Path) -> None:
        """width 检查完整工作流。"""
        report = check_width(narrow_rect_gds, (1, 0), 2.0)
        assert report.check_type == "width"
        assert report.total_violations == 1
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.distance_um == pytest.approx(1.0, rel=1e-6)
        assert report.bbox is not None

    def test_space_full_workflow(self, close_rects_gds: Path) -> None:
        """space 检查完整工作流。"""
        report = check_space(close_rects_gds, (1, 0), 3.0)
        assert report.check_type == "space"
        assert report.total_violations == 1
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.distance_um == pytest.approx(2.0, rel=1e-6)

    def test_width_then_report(self, narrow_rect_gds: Path) -> None:
        """width 检查 + 报告生成。"""
        s = generate_drc_report(
            narrow_rect_gds, (1, 0), "width", 2.0, output_format="text"
        )
        assert "违规总数: 1" in s
        assert "distance=1.000000 μm" in s or "distance=1.0000" in s

    def test_multi_violations_workflow(self, multi_narrow_gds: Path) -> None:
        """多违规完整工作流。"""
        report = check_width(multi_narrow_gds, (1, 0), 2.0)
        assert report.total_violations == 3
        # 所有违规距离都是 1μm
        for v in report.violations:
            assert v.distance_um == pytest.approx(1.0, rel=1e-6)


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_drc_violation_default(self) -> None:
        """DRCViolation 字段。"""
        v = DRCViolation(
            x1_um=0.0, y1_um=0.0,
            x2_um=0.0, y2_um=5.0,
            x3_um=1.0, y3_um=5.0,
            x4_um=1.0, y4_um=0.0,
            distance_um=1.0,
        )
        assert v.x1_um == 0.0
        assert v.distance_um == 1.0

    def test_drc_report_default(self) -> None:
        """DRCReport 默认值。"""
        r = DRCReport()
        assert r.input_path == ""
        assert r.check_type == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.min_value_um == 0.0
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None
        assert r.max_violations == 1000

    def test_drc_report_mutable_defaults(self) -> None:
        """DRCReport 可变默认值独立。"""
        r1 = DRCReport()
        r2 = DRCReport()
        r1.violations.append(DRCViolation(0, 0, 0, 0, 0, 0, 0, 0, 0.0))
        assert len(r2.violations) == 0

    def test_drc_violation_equality(self) -> None:
        """DRCViolation 相等性。"""
        v1 = DRCViolation(0, 0, 0, 5, 1, 5, 1, 0, 1.0)
        v2 = DRCViolation(0, 0, 0, 5, 1, 5, 1, 0, 1.0)
        v3 = DRCViolation(0, 0, 0, 5, 1, 5, 1, 0, 2.0)
        assert v1 == v2
        assert v1 != v3
