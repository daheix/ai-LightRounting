"""R347 GDSII DRC area 检查工具测试。

覆盖:
- check_area: 小面积违规/通过、混合、多边形
- generate_area_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region area/each: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_area import (
    AreaDRCReport,
    AreaDRCViolation,
    check_area,
    generate_area_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_small_rect_gds(path: Path) -> Path:
    """创建小矩形 GDSII（area 违规）。

    layer (1,0): Box(0,0)-(500,500) = 0.5μm×0.5μm = 0.25μm²
    dbu = 0.001μm
    check_area(1.0μm²): 违规（0.25μm² < 1.0μm²）
    check_area(0.2μm²): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 500, 500))
    ly.write(str(path))
    return path


def _make_large_rect_gds(path: Path) -> Path:
    """创建大矩形 GDSII（无 area 违规）。

    layer (1,0): Box(0,0)-(3000,3000) = 3μm×3μm = 9μm²
    check_area(1.0μm²): 通过
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 3000, 3000))
    ly.write(str(path))
    return path


def _make_mixed_gds(path: Path) -> Path:
    """创建混合 GDSII（一小一大，1 个违规）。

    layer (1,0):
    - Box(0,0)-(500,500) = 0.25μm²（违规）
    - Box(1000,0)-(4000,3000) = 9μm²（通过）
    check_area(1.0μm²): 1 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 500, 500))
    top.shapes(li).insert(db.Box(1000, 0, 4000, 3000))
    ly.write(str(path))
    return path


def _make_multi_small_gds(path: Path) -> Path:
    """创建多个小矩形 GDSII（多个 area 违规）。

    layer (1,0): 3 个 0.5x0.5 矩形，每个 0.25μm²
    check_area(1.0μm²): 3 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 500, 500))
    top.shapes(li).insert(db.Box(1000, 0, 1500, 500))
    top.shapes(li).insert(db.Box(2000, 0, 2500, 500))
    ly.write(str(path))
    return path


def _make_polygon_gds(path: Path) -> Path:
    """创建多边形 GDSII（三角形）。

    layer (1,0): 三角形 (0,0)-(2000,0)-(1000,2000)
    面积 = 0.5 * 2000 * 2000 = 2000000 dbu² = 2.0μm²
    check_area(1.0μm²): 通过
    check_area(3.0μm²): 违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(2000, 0), db.Point(1000, 2000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含小矩形）。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): Box(0,0)-(500,500) = 0.25μm²
    check_area(1.0μm²): 1 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(0, 0, 500, 500))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def small_rect_gds(tmp_path: Path) -> Path:
    """小矩形 GDSII（area 违规）。"""
    return _make_small_rect_gds(tmp_path / "small.gds")


@pytest.fixture
def large_rect_gds(tmp_path: Path) -> Path:
    """大矩形 GDSII（无 area 违规）。"""
    return _make_large_rect_gds(tmp_path / "large.gds")


@pytest.fixture
def mixed_gds(tmp_path: Path) -> Path:
    """混合 GDSII（一小一大）。"""
    return _make_mixed_gds(tmp_path / "mixed.gds")


@pytest.fixture
def multi_small_gds(tmp_path: Path) -> Path:
    """多个小矩形 GDSII。"""
    return _make_multi_small_gds(tmp_path / "multi.gds")


@pytest.fixture
def polygon_gds(tmp_path: Path) -> Path:
    """多边形 GDSII（三角形）。"""
    return _make_polygon_gds(tmp_path / "poly.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckArea: 基本 API
# =============================================================================
class TestCheckArea:
    """check_area 函数基本测试。"""

    def test_returns_report(self, small_rect_gds: Path) -> None:
        """返回 AreaDRCReport。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert isinstance(report, AreaDRCReport)

    def test_input_path(self, small_rect_gds: Path) -> None:
        """input_path 正确。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.input_path == str(small_rect_gds)

    def test_layer(self, small_rect_gds: Path) -> None:
        """layer 正确。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.layer == (1, 0)

    def test_dbu(self, small_rect_gds: Path) -> None:
        """dbu 正确。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, small_rect_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.top_cell_name == "TOP"

    def test_check_type(self, small_rect_gds: Path) -> None:
        """check_type 为 'area'。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.check_type == "area"

    def test_min_area(self, small_rect_gds: Path) -> None:
        """min_area_um2 正确。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.min_area_um2 == pytest.approx(1.0)


# =============================================================================
# TestAreaViolation: 违规检测
# =============================================================================
class TestAreaViolation:
    """area 违规检测测试。"""

    def test_small_violation(self, small_rect_gds: Path) -> None:
        """小矩形（0.25μm²）检查 1.0μm² → 违规。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.total_violations == 1
        assert report.total_polygons == 1
        v = report.violations[0]
        assert v.area_um2 == pytest.approx(0.25, rel=1e-3)

    def test_small_pass(self, small_rect_gds: Path) -> None:
        """小矩形（0.25μm²）检查 0.2μm² → 通过。"""
        report = check_area(small_rect_gds, (1, 0), 0.2)
        assert report.total_violations == 0
        assert report.violations == []

    def test_large_pass(self, large_rect_gds: Path) -> None:
        """大矩形（9μm²）检查 1.0μm² → 通过。"""
        report = check_area(large_rect_gds, (1, 0), 1.0)
        assert report.total_violations == 0
        assert report.total_polygons == 1

    def test_mixed_violation(self, mixed_gds: Path) -> None:
        """混合（0.25μm² + 9μm²）检查 1.0μm² → 1 个违规。"""
        report = check_area(mixed_gds, (1, 0), 1.0)
        assert report.total_violations == 1
        assert report.total_polygons == 2
        v = report.violations[0]
        assert v.area_um2 == pytest.approx(0.25, rel=1e-3)

    def test_multi_small_violations(self, multi_small_gds: Path) -> None:
        """3 个小矩形（0.25μm² each）检查 1.0μm² → 3 个违规。"""
        report = check_area(multi_small_gds, (1, 0), 1.0)
        assert report.total_violations == 3
        assert report.total_polygons == 3

    def test_polygon_violation(self, polygon_gds: Path) -> None:
        """三角形（2.0μm²）检查 3.0μm² → 违规。"""
        report = check_area(polygon_gds, (1, 0), 3.0)
        assert report.total_violations == 1
        v = report.violations[0]
        assert v.area_um2 == pytest.approx(2.0, rel=1e-3)

    def test_polygon_pass(self, polygon_gds: Path) -> None:
        """三角形（2.0μm²）检查 1.0μm² → 通过。"""
        report = check_area(polygon_gds, (1, 0), 1.0)
        assert report.total_violations == 0

    def test_total_area(self, mixed_gds: Path) -> None:
        """总面积正确。"""
        report = check_area(mixed_gds, (1, 0), 1.0)
        # 0.25 + 9.0 = 9.25μm²
        assert report.total_area_um2 == pytest.approx(9.25, rel=1e-4)

    def test_violation_bbox(self, small_rect_gds: Path) -> None:
        """违规包围盒存在。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        assert xmin == pytest.approx(0.0, abs=1e-6)
        assert ymin == pytest.approx(0.0, abs=1e-6)
        assert xmax == pytest.approx(0.5, abs=1e-3)
        assert ymax == pytest.approx(0.5, abs=1e-3)

    def test_max_violations_limit(self, multi_small_gds: Path) -> None:
        """max_violations 限制返回数。"""
        report = check_area(multi_small_gds, (1, 0), 1.0, max_violations=2)
        assert len(report.violations) <= 2
        assert report.total_violations == 3  # total 仍是实际总数


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_area(self, hier_gds: Path) -> None:
        """层次化 GDSII area 检查（递归遍历子 cell）。"""
        report = check_area(hier_gds, (1, 0), 1.0)
        # CHILD 含 0.25μm² 矩形，应该有 1 个违规
        assert report.total_violations == 1
        assert report.total_polygons == 1
        v = report.violations[0]
        assert v.area_um2 == pytest.approx(0.25, rel=1e-3)


# =============================================================================
# TestGenerateAreaDrcReport: 报告生成
# =============================================================================
class TestGenerateAreaDrcReport:
    """generate_area_drc_report 函数测试。"""

    def test_text_report(self, small_rect_gds: Path) -> None:
        """text 格式报告。"""
        result = generate_area_drc_report(
            small_rect_gds, (1, 0), 1.0, output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII Area DRC 检查报告" in result
        assert "违规总数" in result
        assert "area" in result

    def test_markdown_report(self, small_rect_gds: Path) -> None:
        """markdown 格式报告。"""
        result = generate_area_drc_report(
            small_rect_gds, (1, 0), 1.0, output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII Area DRC 检查报告" in result
        assert "| 违规总数 |" in result

    def test_json_report(self, small_rect_gds: Path) -> None:
        """json 格式报告。"""
        result = generate_area_drc_report(
            small_rect_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["check_type"] == "area"
        assert data["total_violations"] == 1
        assert data["min_area_um2"] == pytest.approx(1.0)
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["area_um2"] == pytest.approx(0.25, rel=1e-3)

    def test_json_no_violations(self, large_rect_gds: Path) -> None:
        """无违规时 json 报告。"""
        result = generate_area_drc_report(
            large_rect_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_no_violations(self, large_rect_gds: Path) -> None:
        """无违规时 text 报告。"""
        result = generate_area_drc_report(
            large_rect_gds, (1, 0), 1.0, output_format="text",
        )
        assert "违规总数: 0" in result

    def test_json_total_area(self, mixed_gds: Path) -> None:
        """json 报告含总面积。"""
        result = generate_area_drc_report(
            mixed_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["total_area_um2"] == pytest.approx(9.25, rel=1e-4)
        assert data["total_polygons"] == 2


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试（禁止 fall-back）。"""

    def test_nonexistent_file_raise(self, tmp_path: Path) -> None:
        """不存在的文件 raise。"""
        with pytest.raises(FileNotFoundError):
            check_area(tmp_path / "nonexistent.gds", (1, 0), 1.0)

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            check_area(d, (1, 0), 1.0)

    def test_invalid_layer_tuple_raise(self, small_rect_gds: Path) -> None:
        """layer 非 2 元组 raise。"""
        with pytest.raises(ValueError, match="二元组"):
            check_area(small_rect_gds, (1,), 1.0)  # type: ignore

    def test_layer_out_of_range_raise(self, small_rect_gds: Path) -> None:
        """layer 超范围 raise。"""
        with pytest.raises(ValueError, match="layer 必须 0-999"):
            check_area(small_rect_gds, (1000, 0), 1.0)

    def test_datatype_out_of_range_raise(self, small_rect_gds: Path) -> None:
        """datatype 超范围 raise。"""
        with pytest.raises(ValueError, match="datatype 必须 0-255"):
            check_area(small_rect_gds, (1, 256), 1.0)

    def test_min_area_zero_raise(self, small_rect_gds: Path) -> None:
        """min_area_um2=0 raise。"""
        with pytest.raises(ValueError, match="min_area_um2 必须 > 0"):
            check_area(small_rect_gds, (1, 0), 0.0)

    def test_min_area_negative_raise(self, small_rect_gds: Path) -> None:
        """min_area_um2 负值 raise。"""
        with pytest.raises(ValueError, match="min_area_um2 必须 > 0"):
            check_area(small_rect_gds, (1, 0), -1.0)

    def test_max_violations_zero_raise(self, small_rect_gds: Path) -> None:
        """max_violations=0 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_area(small_rect_gds, (1, 0), 1.0, max_violations=0)

    def test_max_violations_negative_raise(self, small_rect_gds: Path) -> None:
        """max_violations 负值 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_area(small_rect_gds, (1, 0), 1.0, max_violations=-1)

    def test_nonexistent_top_cell_raise(self, small_rect_gds: Path) -> None:
        """不存在的 top_cell_name raise。"""
        with pytest.raises(ValueError, match="顶层 cell"):
            check_area(small_rect_gds, (1, 0), 1.0, top_cell_name="NOEXIST")

    def test_nonexistent_layer_raise(self, small_rect_gds: Path) -> None:
        """不存在的层 raise。"""
        with pytest.raises(ValueError, match="不存在"):
            check_area(small_rect_gds, (99, 0), 1.0)

    def test_invalid_output_format_raise(self, small_rect_gds: Path) -> None:
        """无效 output_format raise。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_area_drc_report(
                small_rect_gds, (1, 0), 1.0, output_format="xml",
            )

    def test_invalid_gds_file_raise(self, tmp_path: Path) -> None:
        """无效 GDS 文件 raise RuntimeError。"""
        bad = tmp_path / "bad.gds"
        bad.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="读取文件失败"):
            check_area(bad, (1, 0), 1.0)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_area
        assert gdsii_drc_area.__doc__ is not None
        assert len(gdsii_drc_area.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_area
        doc = gdsii_drc_area.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_area
        doc = gdsii_drc_area.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_area_ref(self) -> None:
        """docstring 含 area 引用。"""
        from polaris.verification import gdsii_drc_area
        doc = gdsii_drc_area.__doc__
        assert "area" in doc.lower()

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_area
        doc = gdsii_drc_area.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_area as m
        for fn in (m.check_area, m.generate_area_drc_report):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_small(self, small_rect_gds: Path) -> None:
        """小矩形完整工作流。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        assert report.check_type == "area"
        assert report.total_violations == 1
        assert len(report.violations) == 1
        assert report.bbox is not None
        v = report.violations[0]
        assert v.area_um2 == pytest.approx(0.25, rel=1e-3)
        assert v.min_area_um2 == pytest.approx(1.0)

    def test_full_workflow_pass(self, large_rect_gds: Path) -> None:
        """大矩形完整工作流（通过）。"""
        report = check_area(large_rect_gds, (1, 0), 1.0)
        assert report.total_violations == 0
        assert report.violations == []
        assert report.bbox is None
        assert report.total_area_um2 == pytest.approx(9.0, rel=1e-4)

    def test_run_then_generate_consistent(
        self, small_rect_gds: Path,
    ) -> None:
        """check_area 和 generate_area_drc_report 结果一致。"""
        report = check_area(small_rect_gds, (1, 0), 1.0)
        json_str = generate_area_drc_report(
            small_rect_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(json_str)
        assert data["total_violations"] == report.total_violations
        assert data["check_type"] == report.check_type
        assert data["min_area_um2"] == pytest.approx(report.min_area_um2)

    def test_threshold_monotonicity(self, mixed_gds: Path) -> None:
        """阈值单调性: 阈值越大，违规数越多。"""
        r_loose = check_area(mixed_gds, (1, 0), 0.1)   # 都通过
        r_strict = check_area(mixed_gds, (1, 0), 1.0)  # 1 个违规
        r_more = check_area(mixed_gds, (1, 0), 10.0)   # 2 个违规
        assert r_loose.total_violations <= r_strict.total_violations
        assert r_strict.total_violations <= r_more.total_violations


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_construction(self) -> None:
        """AreaDRCViolation 构造。"""
        v = AreaDRCViolation(0.0, 0.0, 1.0, 1.0, 0.5, 1.0)
        assert v.area_um2 == 0.5
        assert v.min_area_um2 == 1.0
        assert v.bbox_xmin_um == 0.0

    def test_report_defaults(self) -> None:
        """AreaDRCReport 默认值。"""
        r = AreaDRCReport()
        assert r.input_path == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.min_area_um2 == 0.0
        assert r.check_type == "area"
        assert r.total_polygons == 0
        assert r.total_violations == 0
        assert r.total_area_um2 == 0.0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """AreaDRCReport 可变默认值独立。"""
        r1 = AreaDRCReport()
        r2 = AreaDRCReport()
        r1.violations.append(AreaDRCViolation(0, 0, 0, 0, 0, 0))
        assert len(r2.violations) == 0
