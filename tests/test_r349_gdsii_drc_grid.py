"""R349 GDSII DRC grid 检查工具测试。

覆盖:
- check_grid: 网格对齐/未对齐、多顶点、不同网格大小
- generate_grid_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region grid_check: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_grid import (
    GridDRCReport,
    GridDRCViolation,
    check_grid,
    generate_grid_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_misaligned_gds(path: Path) -> Path:
    """创建未对齐 GDSII（grid 违规）。

    两个矩形:
    - Box(0,0)-(1000,1000): 顶点在 100nm 网格上（对齐）
    - Box(2050,2050)-(3050,3050): 顶点偏移 50nm（未对齐 100nm 网格）

    dbu = 0.001μm
    grid_check(0.1, 0.1μm): 4 个违规（未对齐矩形的 4 个顶点）
    grid_check(0.05, 0.05μm): 0 个违规（2050 是 50 的倍数）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(2050, 2050, 3050, 3050))
    ly.write(str(path))
    return path


def _make_aligned_gds(path: Path) -> Path:
    """创建对齐 GDSII（无 grid 违规）。

    矩形顶点全部在 100nm 网格上:
    - Box(0,0)-(3000,3000) = 3×3μm

    grid_check(0.1, 0.1μm): 0 个违规
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 3000, 3000))
    ly.write(str(path))
    return path


def _make_single_aligned_gds(path: Path) -> Path:
    """创建单对齐多边形 GDSII（无违规）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    ly.write(str(path))
    return path


def _make_multi_misaligned_gds(path: Path) -> Path:
    """创建多未对齐 GDSII（多个 grid 违规）。

    4 个矩形，每个都偏移 50nm:
    - Box(50,50)-(1050,1050)
    - Box(2050,50)-(3050,1050)
    - Box(50,2050)-(1050,3050)
    - Box(2050,2050)-(3050,3050)

    grid_check(0.1, 0.1μm): 16 个违规（4 矩形 × 4 顶点）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(50, 50, 1050, 1050))
    top.shapes(li).insert(db.Box(2050, 50, 3050, 1050))
    top.shapes(li).insert(db.Box(50, 2050, 1050, 3050))
    top.shapes(li).insert(db.Box(2050, 2050, 3050, 3050))
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含未对齐矩形）。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): Box(2050,2050)-(3050,3050)（未对齐 100nm）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(2050, 2050, 3050, 3050))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def misaligned_gds(tmp_path: Path) -> Path:
    """未对齐 GDSII（grid 违规）。"""
    return _make_misaligned_gds(tmp_path / "misaligned.gds")


@pytest.fixture
def aligned_gds(tmp_path: Path) -> Path:
    """对齐 GDSII（无 grid 违规）。"""
    return _make_aligned_gds(tmp_path / "aligned.gds")


@pytest.fixture
def single_aligned_gds(tmp_path: Path) -> Path:
    """单对齐多边形 GDSII。"""
    return _make_single_aligned_gds(tmp_path / "single.gds")


@pytest.fixture
def multi_misaligned_gds(tmp_path: Path) -> Path:
    """多未对齐 GDSII。"""
    return _make_multi_misaligned_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckGrid: 基本 API
# =============================================================================
class TestCheckGrid:
    """check_grid 函数基本测试。"""

    def test_returns_report(self, misaligned_gds: Path) -> None:
        """返回 GridDRCReport。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert isinstance(report, GridDRCReport)

    def test_input_path(self, misaligned_gds: Path) -> None:
        """input_path 正确。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.input_path == str(misaligned_gds)

    def test_layer(self, misaligned_gds: Path) -> None:
        """layer 正确。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.layer == (1, 0)

    def test_dbu(self, misaligned_gds: Path) -> None:
        """dbu 正确。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, misaligned_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.top_cell_name == "TOP"

    def test_check_type(self, misaligned_gds: Path) -> None:
        """check_type 为 'grid'。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.check_type == "grid"

    def test_grid_values(self, misaligned_gds: Path) -> None:
        """grid_x_um/grid_y_um 正确。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.grid_x_um == pytest.approx(0.1)
        assert report.grid_y_um == pytest.approx(0.1)


# =============================================================================
# TestGridViolation: 违规检测
# =============================================================================
class TestGridViolation:
    """grid 违规检测测试。"""

    def test_misaligned_violation(self, misaligned_gds: Path) -> None:
        """未对齐多边形（2050,2050,3050,3050）检查 100nm → 4 违规。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.total_violations == 4
        assert len(report.violations) == 4

    def test_misaligned_pass(self, misaligned_gds: Path) -> None:
        """未对齐多边形检查 50nm → 0 违规（2050 是 50 倍数）。"""
        report = check_grid(misaligned_gds, (1, 0), 0.05, 0.05)
        assert report.total_violations == 0
        assert report.violations == []

    def test_aligned_pass(self, aligned_gds: Path) -> None:
        """对齐多边形检查 100nm → 0 违规。"""
        report = check_grid(aligned_gds, (1, 0), 0.1, 0.1)
        assert report.total_violations == 0

    def test_aligned_pass_50nm(self, aligned_gds: Path) -> None:
        """对齐多边形检查 50nm → 0 违规。"""
        report = check_grid(aligned_gds, (1, 0), 0.05, 0.05)
        assert report.total_violations == 0

    def test_multi_misaligned_violations(
        self, multi_misaligned_gds: Path,
    ) -> None:
        """多未对齐（4 矩形 × 4 顶点）检查 100nm → 16 违规。"""
        report = check_grid(multi_misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.total_violations == 16

    def test_violation_bbox(self, misaligned_gds: Path) -> None:
        """违规包围盒存在。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        # 未对齐矩形 x=2.05-3.05, y=2.05-3.05 (μm)
        assert xmin == pytest.approx(2.05, abs=0.01)
        assert xmax == pytest.approx(3.05, abs=0.01)

    def test_violation_fields(self, misaligned_gds: Path) -> None:
        """违规字段完整。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        v = report.violations[0]
        assert isinstance(v, GridDRCViolation)
        # 顶点坐标是 2.05 或 3.05 之一
        assert v.vertex_x_um in (pytest.approx(2.05), pytest.approx(3.05))
        assert v.vertex_y_um in (pytest.approx(2.05), pytest.approx(3.05))
        assert v.grid_x_um == pytest.approx(0.1)
        assert v.grid_y_um == pytest.approx(0.1)

    def test_max_violations_limit(
        self, multi_misaligned_gds: Path,
    ) -> None:
        """max_violations 限制返回数。"""
        report = check_grid(
            multi_misaligned_gds, (1, 0), 0.1, 0.1, max_violations=5,
        )
        assert len(report.violations) <= 5
        assert report.total_violations >= len(report.violations)


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_grid(self, hier_gds: Path) -> None:
        """层次化 GDSII grid 检查（递归遍历子 cell）。"""
        report = check_grid(hier_gds, (1, 0), 0.1, 0.1)
        # CHILD 含未对齐矩形（4 顶点），应该有 4 个违规
        assert report.total_violations == 4


# =============================================================================
# TestGenerateGridDrcReport: 报告生成
# =============================================================================
class TestGenerateGridDrcReport:
    """generate_grid_drc_report 函数测试。"""

    def test_text_report(self, misaligned_gds: Path) -> None:
        """text 格式报告。"""
        result = generate_grid_drc_report(
            misaligned_gds, (1, 0), 0.1, 0.1, output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII Grid DRC 检查报告" in result
        assert "违规总数" in result
        assert "grid" in result

    def test_markdown_report(self, misaligned_gds: Path) -> None:
        """markdown 格式报告。"""
        result = generate_grid_drc_report(
            misaligned_gds, (1, 0), 0.1, 0.1, output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII Grid DRC 检查报告" in result
        assert "| 违规总数 |" in result

    def test_json_report(self, misaligned_gds: Path) -> None:
        """json 格式报告。"""
        result = generate_grid_drc_report(
            misaligned_gds, (1, 0), 0.1, 0.1, output_format="json",
        )
        data = json.loads(result)
        assert data["check_type"] == "grid"
        assert data["total_violations"] == 4
        assert data["grid_x_um"] == pytest.approx(0.1)
        assert data["grid_y_um"] == pytest.approx(0.1)
        assert len(data["violations"]) == 4
        v = data["violations"][0]
        assert "vertex_x_um" in v
        assert "vertex_y_um" in v

    def test_json_no_violations(self, aligned_gds: Path) -> None:
        """无违规时 json 报告。"""
        result = generate_grid_drc_report(
            aligned_gds, (1, 0), 0.1, 0.1, output_format="json",
        )
        data = json.loads(result)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_no_violations(self, aligned_gds: Path) -> None:
        """无违规时 text 报告。"""
        result = generate_grid_drc_report(
            aligned_gds, (1, 0), 0.1, 0.1, output_format="text",
        )
        assert "违规总数: 0" in result

    def test_markdown_report_no_violations(self, aligned_gds: Path) -> None:
        """无违规时 markdown 报告。"""
        result = generate_grid_drc_report(
            aligned_gds, (1, 0), 0.1, 0.1, output_format="markdown",
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
            check_grid(tmp_path / "nonexistent.gds", (1, 0), 0.1, 0.1)

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            check_grid(d, (1, 0), 0.1, 0.1)

    def test_invalid_layer_tuple_raise(self, misaligned_gds: Path) -> None:
        """layer 非 2 元组 raise。"""
        with pytest.raises(ValueError, match="二元组"):
            check_grid(misaligned_gds, (1,), 0.1, 0.1)  # type: ignore

    def test_layer_out_of_range_raise(self, misaligned_gds: Path) -> None:
        """layer 超范围 raise。"""
        with pytest.raises(ValueError, match="layer 必须 0-999"):
            check_grid(misaligned_gds, (1000, 0), 0.1, 0.1)

    def test_datatype_out_of_range_raise(self, misaligned_gds: Path) -> None:
        """datatype 超范围 raise。"""
        with pytest.raises(ValueError, match="datatype 必须 0-255"):
            check_grid(misaligned_gds, (1, 256), 0.1, 0.1)

    def test_grid_x_zero_raise(self, misaligned_gds: Path) -> None:
        """grid_x_um=0 raise。"""
        with pytest.raises(ValueError, match="grid_x_um 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), 0.0, 0.1)

    def test_grid_x_negative_raise(self, misaligned_gds: Path) -> None:
        """grid_x_um 负值 raise。"""
        with pytest.raises(ValueError, match="grid_x_um 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), -0.1, 0.1)

    def test_grid_y_zero_raise(self, misaligned_gds: Path) -> None:
        """grid_y_um=0 raise。"""
        with pytest.raises(ValueError, match="grid_y_um 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), 0.1, 0.0)

    def test_grid_y_negative_raise(self, misaligned_gds: Path) -> None:
        """grid_y_um 负值 raise。"""
        with pytest.raises(ValueError, match="grid_y_um 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), 0.1, -0.1)

    def test_max_violations_zero_raise(self, misaligned_gds: Path) -> None:
        """max_violations=0 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), 0.1, 0.1, max_violations=0)

    def test_max_violations_negative_raise(
        self, misaligned_gds: Path,
    ) -> None:
        """max_violations 负值 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_grid(misaligned_gds, (1, 0), 0.1, 0.1, max_violations=-1)

    def test_nonexistent_top_cell_raise(
        self, misaligned_gds: Path,
    ) -> None:
        """不存在的 top_cell_name raise。"""
        with pytest.raises(ValueError, match="顶层 cell"):
            check_grid(
                misaligned_gds, (1, 0), 0.1, 0.1, top_cell_name="NOEXIST",
            )

    def test_nonexistent_layer_raise(self, misaligned_gds: Path) -> None:
        """不存在的层 raise。"""
        with pytest.raises(ValueError, match="不存在"):
            check_grid(misaligned_gds, (99, 0), 0.1, 0.1)

    def test_invalid_output_format_raise(
        self, misaligned_gds: Path,
    ) -> None:
        """无效 output_format raise。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_grid_drc_report(
                misaligned_gds, (1, 0), 0.1, 0.1, output_format="xml",
            )

    def test_invalid_gds_file_raise(self, tmp_path: Path) -> None:
        """无效 GDS 文件 raise RuntimeError。"""
        bad = tmp_path / "bad.gds"
        bad.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="读取文件失败"):
            check_grid(bad, (1, 0), 0.1, 0.1)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_grid
        assert gdsii_drc_grid.__doc__ is not None
        assert len(gdsii_drc_grid.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_grid
        doc = gdsii_drc_grid.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_grid
        doc = gdsii_drc_grid.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_grid_check_ref(self) -> None:
        """docstring 含 grid_check 引用。"""
        from polaris.verification import gdsii_drc_grid
        doc = gdsii_drc_grid.__doc__
        assert "grid_check" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_grid
        doc = gdsii_drc_grid.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_grid as m
        for fn in (m.check_grid, m.generate_grid_drc_report):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_violation(
        self, misaligned_gds: Path,
    ) -> None:
        """未对齐完整工作流（违规）。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        assert report.check_type == "grid"
        assert report.total_violations == 4
        assert len(report.violations) == 4
        assert report.bbox is not None

    def test_full_workflow_pass(self, aligned_gds: Path) -> None:
        """对齐完整工作流（通过）。"""
        report = check_grid(aligned_gds, (1, 0), 0.1, 0.1)
        assert report.total_violations == 0
        assert report.violations == []
        assert report.bbox is None

    def test_run_then_generate_consistent(
        self, misaligned_gds: Path,
    ) -> None:
        """check_grid 和 generate_grid_drc_report 结果一致。"""
        report = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        json_str = generate_grid_drc_report(
            misaligned_gds, (1, 0), 0.1, 0.1, output_format="json",
        )
        data = json.loads(json_str)
        assert data["total_violations"] == report.total_violations
        assert data["check_type"] == report.check_type
        assert data["grid_x_um"] == pytest.approx(report.grid_x_um)

    def test_grid_size_monotonicity(self, misaligned_gds: Path) -> None:
        """网格大小单调性: 网格越细，违规越少。"""
        r_strict = check_grid(misaligned_gds, (1, 0), 0.1, 0.1)
        r_loose = check_grid(misaligned_gds, (1, 0), 0.05, 0.05)
        assert r_strict.total_violations >= r_loose.total_violations


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_construction(self) -> None:
        """GridDRCViolation 构造。"""
        v = GridDRCViolation(2.05, 3.05, 0.1, 0.1)
        assert v.vertex_x_um == 2.05
        assert v.vertex_y_um == 3.05
        assert v.grid_x_um == 0.1
        assert v.grid_y_um == 0.1

    def test_report_defaults(self) -> None:
        """GridDRCReport 默认值。"""
        r = GridDRCReport()
        assert r.input_path == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.grid_x_um == 0.0
        assert r.grid_y_um == 0.0
        assert r.check_type == "grid"
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """GridDRCReport 可变默认值独立。"""
        r1 = GridDRCReport()
        r2 = GridDRCReport()
        r1.violations.append(GridDRCViolation(0.0, 0.0, 0.1, 0.1))
        assert len(r2.violations) == 0
