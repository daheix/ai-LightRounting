"""R346 GDSII DRC notch 检查工具测试。

覆盖:
- check_notch: U 型凹槽违规/通过、矩形无凹槽、多凹槽
- generate_notch_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region notch_check: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_notch import (
    NotchDRCReport,
    NotchDRCViolation,
    check_notch,
    generate_notch_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_u_shape_narrow_gds(path: Path) -> Path:
    """创建 U 型窄凹槽 GDSII（notch 违规）。

    U 型多边形，凹槽宽度 0.5μm:
    (0,0)→(3000,0)→(3000,3000)→(2250,3000)→(2250,500)→
    (1750,500)→(1750,3000)→(0,3000)→(0,0)

    dbu = 0.001μm
    notch_check(1.0μm): 1 个违规（凹槽 0.5μm < 1.0μm）
    notch_check(0.4μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(3000, 0), db.Point(3000, 3000),
        db.Point(2250, 3000), db.Point(2250, 500), db.Point(1750, 500),
        db.Point(1750, 3000), db.Point(0, 3000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_u_shape_wide_gds(path: Path) -> Path:
    """创建 U 型宽凹槽 GDSII（无 notch 违规）。

    U 型多边形，凹槽宽度 2.0μm:
    (0,0)→(3000,0)→(3000,3000)→(2500,3000)→(2500,500)→
    (500,500)→(500,3000)→(0,3000)→(0,0)

    notch_check(1.0μm): 0 个违规（凹槽 2.0μm > 1.0μm）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(3000, 0), db.Point(3000, 3000),
        db.Point(2500, 3000), db.Point(2500, 500), db.Point(500, 500),
        db.Point(500, 3000), db.Point(0, 3000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_rect_no_notch_gds(path: Path) -> Path:
    """创建矩形 GDSII（无凹槽，无 notch 违规）。

    layer (1,0): Box(0,0)-(3000,3000) = 3μm×3μm
    notch_check(1.0μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 3000, 3000))
    ly.write(str(path))
    return path


def _make_multi_notch_gds(path: Path) -> Path:
    """创建多凹槽 GDSII（梳齿状，多个 notch 违规）。

    梳齿多边形（3 个齿，齿间距 0.5μm）:
    外轮廓形成 3 个凹槽，每个凹槽 0.5μm

    (0,0)→(5000,0)→(5000,3000)→(4500,3000)→(4500,500)→
    (4000,500)→(4000,3000)→(3500,3000)→(3500,500)→
    (3000,500)→(3000,3000)→(0,3000)→(0,0)

    凹槽1: x 3500-4000 (0.5μm)
    凹槽2: x 4000-4500 (0.5μm)
    凹槽3: x 4500-5000... 实际上这个多边形是梳齿状

    notch_check(1.0μm): 多个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(5000, 0), db.Point(5000, 3000),
        db.Point(4500, 3000), db.Point(4500, 500), db.Point(4000, 500),
        db.Point(4000, 3000), db.Point(3500, 3000), db.Point(3500, 500),
        db.Point(3000, 500), db.Point(3000, 3000), db.Point(0, 3000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含 U 型凹槽）。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): U 型窄凹槽（同 _make_u_shape_narrow_gds）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(3000, 0), db.Point(3000, 3000),
        db.Point(2250, 3000), db.Point(2250, 500), db.Point(1750, 500),
        db.Point(1750, 3000), db.Point(0, 3000),
    ])
    child.shapes(li).insert(poly)
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def narrow_notch_gds(tmp_path: Path) -> Path:
    """窄凹槽 U 型 GDSII（notch 违规）。"""
    return _make_u_shape_narrow_gds(tmp_path / "narrow.gds")


@pytest.fixture
def wide_notch_gds(tmp_path: Path) -> Path:
    """宽凹槽 U 型 GDSII（无 notch 违规）。"""
    return _make_u_shape_wide_gds(tmp_path / "wide.gds")


@pytest.fixture
def rect_gds(tmp_path: Path) -> Path:
    """矩形 GDSII（无凹槽）。"""
    return _make_rect_no_notch_gds(tmp_path / "rect.gds")


@pytest.fixture
def multi_notch_gds(tmp_path: Path) -> Path:
    """多凹槽 GDSII（梳齿状）。"""
    return _make_multi_notch_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckNotch: 基本 API
# =============================================================================
class TestCheckNotch:
    """check_notch 函数基本测试。"""

    def test_returns_report(self, narrow_notch_gds: Path) -> None:
        """返回 NotchDRCReport。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert isinstance(report, NotchDRCReport)

    def test_input_path(self, narrow_notch_gds: Path) -> None:
        """input_path 正确。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.input_path == str(narrow_notch_gds)

    def test_layer(self, narrow_notch_gds: Path) -> None:
        """layer 正确。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.layer == (1, 0)

    def test_dbu(self, narrow_notch_gds: Path) -> None:
        """dbu 正确。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, narrow_notch_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.top_cell_name == "TOP"

    def test_check_type(self, narrow_notch_gds: Path) -> None:
        """check_type 为 'notch'。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.check_type == "notch"

    def test_min_notch_um(self, narrow_notch_gds: Path) -> None:
        """min_notch_um 正确。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.min_notch_um == pytest.approx(1.0)


# =============================================================================
# TestNotchViolation: 违规检测
# =============================================================================
class TestNotchViolation:
    """notch 违规检测测试。"""

    def test_narrow_notch_violation(self, narrow_notch_gds: Path) -> None:
        """窄凹槽（0.5μm）检查 1.0μm → 违规。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.total_violations == 1
        assert report.violations[0].distance_um == pytest.approx(0.5, rel=1e-3)

    def test_narrow_notch_pass(self, narrow_notch_gds: Path) -> None:
        """窄凹槽（0.5μm）检查 0.4μm → 通过。"""
        report = check_notch(narrow_notch_gds, (1, 0), 0.4)
        assert report.total_violations == 0
        assert report.violations == []

    def test_wide_notch_pass(self, wide_notch_gds: Path) -> None:
        """宽凹槽（2.0μm）检查 1.0μm → 通过。"""
        report = check_notch(wide_notch_gds, (1, 0), 1.0)
        assert report.total_violations == 0

    def test_rect_no_notch(self, rect_gds: Path) -> None:
        """矩形无凹槽 → 无违规。"""
        report = check_notch(rect_gds, (1, 0), 1.0)
        assert report.total_violations == 0

    def test_multi_notch_violations(self, multi_notch_gds: Path) -> None:
        """多凹槽 → 多个违规。"""
        report = check_notch(multi_notch_gds, (1, 0), 1.0)
        assert report.total_violations >= 2  # 至少 2 个凹槽违规

    def test_violation_bbox(self, narrow_notch_gds: Path) -> None:
        """违规包围盒存在。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        # 凹槽在 x=1750-2250, y=500-3000 (dbu) = 1.75-2.25, 0.5-3.0 (μm)
        assert xmin == pytest.approx(1.75, abs=0.1)
        assert xmax == pytest.approx(2.25, abs=0.1)

    def test_violation_fields(self, narrow_notch_gds: Path) -> None:
        """违规字段完整。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        v = report.violations[0]
        assert isinstance(v, NotchDRCViolation)
        # first 边: (1750,500)-(1750,3000) 或 (2250,500)-(2250,3000)
        # second 边: 另一条
        assert v.distance_um == pytest.approx(0.5, rel=1e-3)

    def test_max_violations_limit(self, multi_notch_gds: Path) -> None:
        """max_violations 限制返回数。"""
        report = check_notch(multi_notch_gds, (1, 0), 1.0, max_violations=1)
        assert len(report.violations) <= 1
        # total_violations 仍是实际总数
        assert report.total_violations >= len(report.violations)


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_notch(self, hier_gds: Path) -> None:
        """层次化 GDSII notch 检查（递归遍历子 cell）。"""
        report = check_notch(hier_gds, (1, 0), 1.0)
        # CHILD 含 U 型窄凹槽，应该有 1 个违规
        assert report.total_violations == 1
        assert report.violations[0].distance_um == pytest.approx(0.5, rel=1e-3)


# =============================================================================
# TestGenerateNotchDrcReport: 报告生成
# =============================================================================
class TestGenerateNotchDrcReport:
    """generate_notch_drc_report 函数测试。"""

    def test_text_report(self, narrow_notch_gds: Path) -> None:
        """text 格式报告。"""
        result = generate_notch_drc_report(
            narrow_notch_gds, (1, 0), 1.0, output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII Notch DRC 检查报告" in result
        assert "违规总数" in result
        assert "notch" in result

    def test_markdown_report(self, narrow_notch_gds: Path) -> None:
        """markdown 格式报告。"""
        result = generate_notch_drc_report(
            narrow_notch_gds, (1, 0), 1.0, output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII Notch DRC 检查报告" in result
        assert "| 违规总数 |" in result

    def test_json_report(self, narrow_notch_gds: Path) -> None:
        """json 格式报告。"""
        result = generate_notch_drc_report(
            narrow_notch_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["check_type"] == "notch"
        assert data["total_violations"] == 1
        assert data["min_notch_um"] == pytest.approx(1.0)
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["distance_um"] == pytest.approx(0.5, rel=1e-3)

    def test_json_no_violations(self, rect_gds: Path) -> None:
        """无违规时 json 报告。"""
        result = generate_notch_drc_report(
            rect_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_no_violations(self, rect_gds: Path) -> None:
        """无违规时 text 报告。"""
        result = generate_notch_drc_report(
            rect_gds, (1, 0), 1.0, output_format="text",
        )
        assert "违规总数: 0" in result

    def test_markdown_report_no_violations(self, rect_gds: Path) -> None:
        """无违规时 markdown 报告。"""
        result = generate_notch_drc_report(
            rect_gds, (1, 0), 1.0, output_format="markdown",
        )
        assert "| 违规总数 | 0 |" in result


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试（禁止 fall-back）。"""

    def test_nonexistent_file_raise(self, tmp_path: Path) -> None:
        """不存在的文件 raise。"""
        with pytest.raises(FileNotFoundError):
            check_notch(tmp_path / "nonexistent.gds", (1, 0), 1.0)

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            check_notch(d, (1, 0), 1.0)

    def test_invalid_layer_tuple_raise(self, narrow_notch_gds: Path) -> None:
        """layer 非 2 元组 raise。"""
        with pytest.raises(ValueError, match="二元组"):
            check_notch(narrow_notch_gds, (1,), 1.0)  # type: ignore

    def test_layer_out_of_range_raise(self, narrow_notch_gds: Path) -> None:
        """layer 超范围 raise。"""
        with pytest.raises(ValueError, match="layer 必须 0-999"):
            check_notch(narrow_notch_gds, (1000, 0), 1.0)

    def test_datatype_out_of_range_raise(self, narrow_notch_gds: Path) -> None:
        """datatype 超范围 raise。"""
        with pytest.raises(ValueError, match="datatype 必须 0-255"):
            check_notch(narrow_notch_gds, (1, 256), 1.0)

    def test_min_notch_zero_raise(self, narrow_notch_gds: Path) -> None:
        """min_notch_um=0 raise。"""
        with pytest.raises(ValueError, match="min_notch_um 必须 > 0"):
            check_notch(narrow_notch_gds, (1, 0), 0.0)

    def test_min_notch_negative_raise(self, narrow_notch_gds: Path) -> None:
        """min_notch_um 负值 raise。"""
        with pytest.raises(ValueError, match="min_notch_um 必须 > 0"):
            check_notch(narrow_notch_gds, (1, 0), -1.0)

    def test_max_violations_zero_raise(self, narrow_notch_gds: Path) -> None:
        """max_violations=0 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_notch(narrow_notch_gds, (1, 0), 1.0, max_violations=0)

    def test_max_violations_negative_raise(self, narrow_notch_gds: Path) -> None:
        """max_violations 负值 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_notch(narrow_notch_gds, (1, 0), 1.0, max_violations=-1)

    def test_nonexistent_top_cell_raise(self, narrow_notch_gds: Path) -> None:
        """不存在的 top_cell_name raise。"""
        with pytest.raises(ValueError, match="顶层 cell"):
            check_notch(narrow_notch_gds, (1, 0), 1.0, top_cell_name="NOEXIST")

    def test_nonexistent_layer_raise(self, narrow_notch_gds: Path) -> None:
        """不存在的层 raise。"""
        with pytest.raises(ValueError, match="不存在"):
            check_notch(narrow_notch_gds, (99, 0), 1.0)

    def test_invalid_output_format_raise(self, narrow_notch_gds: Path) -> None:
        """无效 output_format raise。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_notch_drc_report(
                narrow_notch_gds, (1, 0), 1.0, output_format="xml",
            )

    def test_invalid_gds_file_raise(self, tmp_path: Path) -> None:
        """无效 GDS 文件 raise RuntimeError。"""
        bad = tmp_path / "bad.gds"
        bad.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="读取文件失败"):
            check_notch(bad, (1, 0), 1.0)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_notch
        assert gdsii_drc_notch.__doc__ is not None
        assert len(gdsii_drc_notch.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_notch
        doc = gdsii_drc_notch.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_notch
        doc = gdsii_drc_notch.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_notch_check_ref(self) -> None:
        """docstring 含 notch_check 引用。"""
        from polaris.verification import gdsii_drc_notch
        doc = gdsii_drc_notch.__doc__
        assert "notch_check" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_notch
        doc = gdsii_drc_notch.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_notch as m
        for fn in (m.check_notch, m.generate_notch_drc_report):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_narrow(self, narrow_notch_gds: Path) -> None:
        """窄凹槽完整工作流。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        assert report.check_type == "notch"
        assert report.total_violations == 1
        assert len(report.violations) == 1
        assert report.bbox is not None
        v = report.violations[0]
        assert v.distance_um == pytest.approx(0.5, rel=1e-3)

    def test_full_workflow_pass(self, wide_notch_gds: Path) -> None:
        """宽凹槽完整工作流（通过）。"""
        report = check_notch(wide_notch_gds, (1, 0), 1.0)
        assert report.total_violations == 0
        assert report.violations == []
        assert report.bbox is None

    def test_run_then_generate_consistent(
        self, narrow_notch_gds: Path,
    ) -> None:
        """check_notch 和 generate_notch_drc_report 结果一致。"""
        report = check_notch(narrow_notch_gds, (1, 0), 1.0)
        json_str = generate_notch_drc_report(
            narrow_notch_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(json_str)
        assert data["total_violations"] == report.total_violations
        assert data["check_type"] == report.check_type
        assert data["min_notch_um"] == pytest.approx(report.min_notch_um)

    def test_threshold_monotonicity(self, narrow_notch_gds: Path) -> None:
        """阈值单调性: 阈值越小，违规数越少。"""
        r_strict = check_notch(narrow_notch_gds, (1, 0), 1.0)
        r_loose = check_notch(narrow_notch_gds, (1, 0), 0.4)
        assert r_strict.total_violations >= r_loose.total_violations


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_construction(self) -> None:
        """NotchDRCViolation 构造。"""
        v = NotchDRCViolation(0, 0, 1, 0, 1, 0, 2, 0, 1.0)
        assert v.distance_um == 1.0
        assert v.x1_dbu == 0
        assert v.y1_dbu == 0

    def test_report_defaults(self) -> None:
        """NotchDRCReport 默认值。"""
        r = NotchDRCReport()
        assert r.input_path == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.min_notch_um == 0.0
        assert r.check_type == "notch"
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """NotchDRCReport 可变默认值独立。"""
        r1 = NotchDRCReport()
        r2 = NotchDRCReport()
        r1.violations.append(NotchDRCViolation(0, 0, 0, 0, 0, 0, 0, 0, 0.0))
        assert len(r2.violations) == 0
