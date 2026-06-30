"""R350 GDSII DRC strange_polygon 检查工具测试。

覆盖:
- check_strange_polygon: 自相交违规/通过、多违规
- generate_strange_polygon_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region strange_polygon_check: https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout Polygon class: https://www.klayout.de/doc-qt5/code/class_Polygon.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_strange_polygon import (
    StrangePolygonDRCReport,
    StrangePolygonDRCViolation,
    check_strange_polygon,
    generate_strange_polygon_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_self_intersecting_gds(path: Path) -> Path:
    """创建自相交 GDSII（strange_polygon 违规）。

    蝴蝶形自相交多边形:
    (0,0)-(2000,2000)-(2000,0)-(0,2000)
    即对角线交叉，形成自相交

    dbu = 0.001μm
    strange_polygon_check(): 1 个违规
    违规多边形 hull: (0,0)-(0,2000)-(1000,1000)（三角形）
    bbox: (0,0;1000,2000)
    area: 1000000 dbu² = 1.0 μm²
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(2000, 2000),
        db.Point(2000, 0), db.Point(0, 2000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_normal_rect_gds(path: Path) -> Path:
    """创建正常矩形 GDSII（无 strange_polygon 违规）。

    layer (1,0): Box(0,0)-(3000,3000) = 3×3μm
    strange_polygon_check(): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 3000, 3000))
    ly.write(str(path))
    return path


def _make_normal_polygon_gds(path: Path) -> Path:
    """创建正常多边形 GDSII（无 strange_polygon 违规）。

    五边形: (0,0)-(3000,0)-(3000,2000)-(1500,3000)-(0,2000)
    strange_polygon_check(): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(3000, 0), db.Point(3000, 2000),
        db.Point(1500, 3000), db.Point(0, 2000),
    ])
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_multi_strange_gds(path: Path) -> Path:
    """创建多自相交 GDSII（多个 strange_polygon 违规）。

    两个蝴蝶形自相交多边形:
    - (0,0)-(2000,2000)-(2000,0)-(0,2000)
    - (3000,0)-(5000,2000)-(5000,0)-(3000,2000)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    poly1 = db.Polygon([
        db.Point(0, 0), db.Point(2000, 2000),
        db.Point(2000, 0), db.Point(0, 2000),
    ])
    poly2 = db.Polygon([
        db.Point(3000, 0), db.Point(5000, 2000),
        db.Point(5000, 0), db.Point(3000, 2000),
    ])
    top.shapes(li).insert(poly1)
    top.shapes(li).insert(poly2)
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含自相交多边形）。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): 蝴蝶形自相交多边形
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    poly = db.Polygon([
        db.Point(0, 0), db.Point(2000, 2000),
        db.Point(2000, 0), db.Point(0, 2000),
    ])
    child.shapes(li).insert(poly)
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def self_intersect_gds(tmp_path: Path) -> Path:
    """自相交 GDSII（strange_polygon 违规）。"""
    return _make_self_intersecting_gds(tmp_path / "selfint.gds")


@pytest.fixture
def normal_rect_gds(tmp_path: Path) -> Path:
    """正常矩形 GDSII。"""
    return _make_normal_rect_gds(tmp_path / "rect.gds")


@pytest.fixture
def normal_polygon_gds(tmp_path: Path) -> Path:
    """正常多边形 GDSII。"""
    return _make_normal_polygon_gds(tmp_path / "poly.gds")


@pytest.fixture
def multi_strange_gds(tmp_path: Path) -> Path:
    """多自相交 GDSII。"""
    return _make_multi_strange_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckStrangePolygon: 基本 API
# =============================================================================
class TestCheckStrangePolygon:
    """check_strange_polygon 函数基本测试。"""

    def test_returns_report(self, self_intersect_gds: Path) -> None:
        """返回 StrangePolygonDRCReport。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert isinstance(report, StrangePolygonDRCReport)

    def test_input_path(self, self_intersect_gds: Path) -> None:
        """input_path 正确。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.input_path == str(self_intersect_gds)

    def test_layer(self, self_intersect_gds: Path) -> None:
        """layer 正确。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.layer == (1, 0)

    def test_dbu(self, self_intersect_gds: Path) -> None:
        """dbu 正确。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, self_intersect_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.top_cell_name == "TOP"

    def test_check_type(self, self_intersect_gds: Path) -> None:
        """check_type 为 'strange_polygon'。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.check_type == "strange_polygon"


# =============================================================================
# TestStrangePolygonViolation: 违规检测
# =============================================================================
class TestStrangePolygonViolation:
    """strange_polygon 违规检测测试。"""

    def test_self_intersect_violation(
        self, self_intersect_gds: Path,
    ) -> None:
        """自相交多边形 → 1 违规。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.total_violations >= 1
        assert len(report.violations) >= 1

    def test_normal_rect_pass(self, normal_rect_gds: Path) -> None:
        """正常矩形 → 0 违规。"""
        report = check_strange_polygon(normal_rect_gds, (1, 0))
        assert report.total_violations == 0
        assert report.violations == []

    def test_normal_polygon_pass(self, normal_polygon_gds: Path) -> None:
        """正常五边形 → 0 违规。"""
        report = check_strange_polygon(normal_polygon_gds, (1, 0))
        assert report.total_violations == 0

    def test_multi_strange_violations(
        self, multi_strange_gds: Path,
    ) -> None:
        """多自相交 → 多个违规。"""
        report = check_strange_polygon(multi_strange_gds, (1, 0))
        assert report.total_violations >= 2

    def test_violation_bbox(self, self_intersect_gds: Path) -> None:
        """违规包围盒存在。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.bbox is not None
        # 蝴蝶形 (0,0)-(2000,2000)-(2000,0)-(0,2000) 自相交
        # KLayout 分解后违规多边形 bbox: (0,0;1000,2000) dbu = (0,0)-(1.0,2.0) μm
        (xmin, ymin), (xmax, ymax) = report.bbox
        assert xmin == pytest.approx(0.0, abs=1e-6)
        assert ymin == pytest.approx(0.0, abs=1e-6)
        assert xmax == pytest.approx(1.0, abs=1e-3)
        assert ymax == pytest.approx(2.0, abs=1e-3)

    def test_violation_fields(self, self_intersect_gds: Path) -> None:
        """违规字段完整。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        v = report.violations[0]
        assert isinstance(v, StrangePolygonDRCViolation)
        # 蝴蝶形自相交 → 分解后三角形 hull: (0,0)-(0,2000)-(1000,1000)
        assert v.polygon_id == 0
        assert v.bbox_xmin_dbu == 0
        assert v.bbox_ymin_dbu == 0
        assert v.bbox_xmax_dbu == 1000
        assert v.bbox_ymax_dbu == 2000
        # area = 1000000 dbu²
        assert v.area_dbu2 == 1000000
        # area_um2 = 1000000 * 0.001 * 0.001 = 1.0 μm²
        assert v.area_um2 == pytest.approx(1.0, rel=1e-6)
        # hull 顶点
        assert v.num_hull_points == 3
        assert (0, 0) in v.hull_points_dbu
        assert (0, 2000) in v.hull_points_dbu
        assert (1000, 1000) in v.hull_points_dbu

    def test_max_violations_limit(
        self, multi_strange_gds: Path,
    ) -> None:
        """max_violations 限制返回数。"""
        report = check_strange_polygon(
            multi_strange_gds, (1, 0), max_violations=1,
        )
        assert len(report.violations) <= 1
        assert report.total_violations >= len(report.violations)


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_strange(self, hier_gds: Path) -> None:
        """层次化 GDSII strange_polygon 检查（递归遍历子 cell）。"""
        report = check_strange_polygon(hier_gds, (1, 0))
        # CHILD 含自相交多边形，应该有违规
        assert report.total_violations >= 1


# =============================================================================
# TestGenerateStrangePolygonDrcReport: 报告生成
# =============================================================================
class TestGenerateStrangePolygonDrcReport:
    """generate_strange_polygon_drc_report 函数测试。"""

    def test_text_report(self, self_intersect_gds: Path) -> None:
        """text 格式报告。"""
        result = generate_strange_polygon_drc_report(
            self_intersect_gds, (1, 0), output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII Strange Polygon DRC 检查报告" in result
        assert "违规总数" in result
        assert "strange_polygon" in result

    def test_markdown_report(self, self_intersect_gds: Path) -> None:
        """markdown 格式报告。"""
        result = generate_strange_polygon_drc_report(
            self_intersect_gds, (1, 0), output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII Strange Polygon DRC 检查报告" in result
        assert "| 违规总数 |" in result

    def test_json_report(self, self_intersect_gds: Path) -> None:
        """json 格式报告。"""
        result = generate_strange_polygon_drc_report(
            self_intersect_gds, (1, 0), output_format="json",
        )
        data = json.loads(result)
        assert data["check_type"] == "strange_polygon"
        assert data["total_violations"] >= 1
        assert len(data["violations"]) >= 1
        v = data["violations"][0]
        assert "polygon_id" in v
        assert "bbox_xmin_dbu" in v
        assert "area_um2" in v
        assert "hull_points_dbu" in v

    def test_json_no_violations(self, normal_rect_gds: Path) -> None:
        """无违规时 json 报告。"""
        result = generate_strange_polygon_drc_report(
            normal_rect_gds, (1, 0), output_format="json",
        )
        data = json.loads(result)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_no_violations(
        self, normal_rect_gds: Path,
    ) -> None:
        """无违规时 text 报告。"""
        result = generate_strange_polygon_drc_report(
            normal_rect_gds, (1, 0), output_format="text",
        )
        assert "违规总数: 0" in result

    def test_markdown_report_no_violations(
        self, normal_rect_gds: Path,
    ) -> None:
        """无违规时 markdown 报告。"""
        result = generate_strange_polygon_drc_report(
            normal_rect_gds, (1, 0), output_format="markdown",
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
            check_strange_polygon(tmp_path / "nonexistent.gds", (1, 0))

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            check_strange_polygon(d, (1, 0))

    def test_invalid_layer_tuple_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """layer 非 2 元组 raise。"""
        with pytest.raises(ValueError, match="二元组"):
            check_strange_polygon(self_intersect_gds, (1,))  # type: ignore

    def test_layer_out_of_range_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """layer 超范围 raise。"""
        with pytest.raises(ValueError, match="layer 必须 0-999"):
            check_strange_polygon(self_intersect_gds, (1000, 0))

    def test_datatype_out_of_range_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """datatype 超范围 raise。"""
        with pytest.raises(ValueError, match="datatype 必须 0-255"):
            check_strange_polygon(self_intersect_gds, (1, 256))

    def test_max_violations_zero_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """max_violations=0 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_strange_polygon(
                self_intersect_gds, (1, 0), max_violations=0,
            )

    def test_max_violations_negative_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """max_violations 负值 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_strange_polygon(
                self_intersect_gds, (1, 0), max_violations=-1,
            )

    def test_nonexistent_top_cell_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """不存在的 top_cell_name raise。"""
        with pytest.raises(ValueError, match="顶层 cell"):
            check_strange_polygon(
                self_intersect_gds, (1, 0), top_cell_name="NOEXIST",
            )

    def test_nonexistent_layer_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """不存在的层 raise。"""
        with pytest.raises(ValueError, match="不存在"):
            check_strange_polygon(self_intersect_gds, (99, 0))

    def test_invalid_output_format_raise(
        self, self_intersect_gds: Path,
    ) -> None:
        """无效 output_format raise。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_strange_polygon_drc_report(
                self_intersect_gds, (1, 0), output_format="xml",
            )

    def test_invalid_gds_file_raise(self, tmp_path: Path) -> None:
        """无效 GDS 文件 raise RuntimeError。"""
        bad = tmp_path / "bad.gds"
        bad.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="读取文件失败"):
            check_strange_polygon(bad, (1, 0))


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_strange_polygon
        assert gdsii_drc_strange_polygon.__doc__ is not None
        assert len(gdsii_drc_strange_polygon.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_strange_polygon
        doc = gdsii_drc_strange_polygon.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_strange_polygon
        doc = gdsii_drc_strange_polygon.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_strange_polygon_check_ref(self) -> None:
        """docstring 含 strange_polygon_check 引用。"""
        from polaris.verification import gdsii_drc_strange_polygon
        doc = gdsii_drc_strange_polygon.__doc__
        assert "strange_polygon_check" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_strange_polygon
        doc = gdsii_drc_strange_polygon.__doc__
        assert "R01" in doc and "R02" in doc
        assert "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_strange_polygon as m
        for fn in (
            m.check_strange_polygon, m.generate_strange_polygon_drc_report,
        ):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_violation(
        self, self_intersect_gds: Path,
    ) -> None:
        """自相交完整工作流（违规）。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.check_type == "strange_polygon"
        assert report.total_violations >= 1
        assert report.bbox is not None

    def test_full_workflow_pass(self, normal_rect_gds: Path) -> None:
        """正常矩形完整工作流（通过）。"""
        report = check_strange_polygon(normal_rect_gds, (1, 0))
        assert report.total_violations == 0
        assert report.violations == []
        assert report.bbox is None

    def test_run_then_generate_consistent(
        self, self_intersect_gds: Path,
    ) -> None:
        """check_strange_polygon 和 generate 结果一致。"""
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        json_str = generate_strange_polygon_drc_report(
            self_intersect_gds, (1, 0), output_format="json",
        )
        data = json.loads(json_str)
        assert data["total_violations"] == report.total_violations
        assert data["check_type"] == report.check_type

    def test_no_threshold_parameter(self, self_intersect_gds: Path) -> None:
        """strange_polygon_check 无阈值参数（与 width/space 不同）。"""
        # check_strange_polygon 签名: (gds_path, layer, top_cell_name, max_violations)
        # 没有 min_value_um 参数
        report = check_strange_polygon(self_intersect_gds, (1, 0))
        assert report.check_type == "strange_polygon"
        # 报告无 min_value_um 字段
        assert not hasattr(report, "min_value_um")


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_construction(self) -> None:
        """StrangePolygonDRCViolation 构造。"""
        v = StrangePolygonDRCViolation(
            polygon_id=0,
            bbox_xmin_dbu=0, bbox_ymin_dbu=0,
            bbox_xmax_dbu=1000, bbox_ymax_dbu=2000,
            area_dbu2=1000000,
            num_hull_points=3,
            hull_points_dbu=[(0, 0), (0, 2000), (1000, 1000)],
            area_um2=1.0,
        )
        assert v.polygon_id == 0
        assert v.bbox_xmin_dbu == 0
        assert v.bbox_xmax_dbu == 1000
        assert v.area_dbu2 == 1000000
        assert v.num_hull_points == 3
        assert v.area_um2 == pytest.approx(1.0)
        assert len(v.hull_points_dbu) == 3

    def test_report_defaults(self) -> None:
        """StrangePolygonDRCReport 默认值。"""
        r = StrangePolygonDRCReport()
        assert r.input_path == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.check_type == "strange_polygon"
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """StrangePolygonDRCReport 可变默认值独立。"""
        r1 = StrangePolygonDRCReport()
        r2 = StrangePolygonDRCReport()
        r1.violations.append(
            StrangePolygonDRCViolation(
                polygon_id=0,
                bbox_xmin_dbu=0, bbox_ymin_dbu=0,
                bbox_xmax_dbu=0, bbox_ymax_dbu=0,
                area_dbu2=0,
                num_hull_points=0,
                hull_points_dbu=[],
                area_um2=0.0,
            )
        )
        assert len(r2.violations) == 0
