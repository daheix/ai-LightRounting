"""R348 GDSII DRC isolated 检查工具测试。

覆盖:
- check_isolated: 孤立违规/通过、单多边形、多违规
- generate_isolated_drc_report: text/markdown/json
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region isolated_check: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_drc_isolated import (
    IsolatedDRCReport,
    IsolatedDRCViolation,
    check_isolated,
    generate_isolated_drc_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_close_isolated_gds(path: Path) -> Path:
    """创建近距离孤立 GDSII（isolated 违规）。

    两个矩形间距 2μm:
    - layer (1,0): Box(0,0)-(1000,1000) = 1×1μm
    - layer (1,0): Box(3000,0)-(4000,1000) = 1×1μm
    间距 = 2μm

    dbu = 0.001μm
    isolated_check(2.5μm): 1 个违规（间距 2μm < 2.5μm）
    isolated_check(1.5μm): 0 个违规（间距 2μm > 1.5μm）
    isolated_check(2.0μm): 0 个违规（边界，间距 == 阈值不违规）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(3000, 0, 4000, 1000))
    ly.write(str(path))
    return path


def _make_far_isolated_gds(path: Path) -> Path:
    """创建远距离孤立 GDSII（无 isolated 违规）。

    两个矩形间距 5μm:
    - layer (1,0): Box(0,0)-(1000,1000) = 1×1μm
    - layer (1,0): Box(6000,0)-(7000,1000) = 1×1μm
    间距 = 5μm

    isolated_check(2.5μm): 0 个违规（间距 5μm > 2.5μm）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(6000, 0, 7000, 1000))
    ly.write(str(path))
    return path


def _make_single_poly_gds(path: Path) -> Path:
    """创建单多边形 GDSII（无对比对象，0 违规）。

    layer (1,0): Box(0,0)-(3000,3000) = 3×3μm
    isolated_check(1.0μm): 0 个违规（无其他多边形比较）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 3000, 3000))
    ly.write(str(path))
    return path


def _make_multi_isolated_gds(path: Path) -> Path:
    """创建多对近距离孤立 GDSII（多个 isolated 违规）。

    4 个矩形排成一行，相邻间距均为 1μm:
    - Box(0,0)-(1000,1000): x=0-1μm
    - Box(2000,0)-(3000,1000): x=2-3μm (与上一个间距1μm)
    - Box(4000,0)-(5000,1000): x=4-5μm (与上一个间距1μm)
    - Box(6000,0)-(7000,1000): x=6-7μm (与上一个间距1μm)

    共 3 对相邻，每对间距 1μm
    isolated_check(2.0μm): 至少 3 个违规（每对相邻都违规）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li).insert(db.Box(2000, 0, 3000, 1000))
    top.shapes(li).insert(db.Box(4000, 0, 5000, 1000))
    top.shapes(li).insert(db.Box(6000, 0, 7000, 1000))
    ly.write(str(path))
    return path


def _make_hier_gds(path: Path) -> Path:
    """创建层次化 GDSII（CHILD 含两个近距离矩形）。

    TOP cell
      - CHILD @ (0, 0)
    CHILD cell
      - layer (1,0): 两个矩形间距 2μm（同 _make_close_isolated_gds）
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    child.shapes(li).insert(db.Box(3000, 0, 4000, 1000))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


@pytest.fixture
def close_isolated_gds(tmp_path: Path) -> Path:
    """近距离孤立 GDSII（isolated 违规）。"""
    return _make_close_isolated_gds(tmp_path / "close.gds")


@pytest.fixture
def far_isolated_gds(tmp_path: Path) -> Path:
    """远距离孤立 GDSII（无 isolated 违规）。"""
    return _make_far_isolated_gds(tmp_path / "far.gds")


@pytest.fixture
def single_gds(tmp_path: Path) -> Path:
    """单多边形 GDSII（无对比）。"""
    return _make_single_poly_gds(tmp_path / "single.gds")


@pytest.fixture
def multi_isolated_gds(tmp_path: Path) -> Path:
    """多对近距离孤立 GDSII。"""
    return _make_multi_isolated_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hier_gds(tmp_path / "hier.gds")


# =============================================================================
# TestCheckIsolated: 基本 API
# =============================================================================
class TestCheckIsolated:
    """check_isolated 函数基本测试。"""

    def test_returns_report(self, close_isolated_gds: Path) -> None:
        """返回 IsolatedDRCReport。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert isinstance(report, IsolatedDRCReport)

    def test_input_path(self, close_isolated_gds: Path) -> None:
        """input_path 正确。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.input_path == str(close_isolated_gds)

    def test_layer(self, close_isolated_gds: Path) -> None:
        """layer 正确。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.layer == (1, 0)

    def test_dbu(self, close_isolated_gds: Path) -> None:
        """dbu 正确。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, close_isolated_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.top_cell_name == "TOP"

    def test_check_type(self, close_isolated_gds: Path) -> None:
        """check_type 为 'isolated'。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.check_type == "isolated"

    def test_min_isolated_um(self, close_isolated_gds: Path) -> None:
        """min_isolated_um 正确。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.min_isolated_um == pytest.approx(2.5)


# =============================================================================
# TestIsolatedViolation: 违规检测
# =============================================================================
class TestIsolatedViolation:
    """isolated 违规检测测试。"""

    def test_close_isolated_violation(self, close_isolated_gds: Path) -> None:
        """近距离（2μm）检查 2.5μm → 违规。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.total_violations == 1
        assert report.violations[0].distance_um == pytest.approx(
            2.0, rel=1e-3,
        )

    def test_close_isolated_pass(self, close_isolated_gds: Path) -> None:
        """近距离（2μm）检查 1.5μm → 通过。"""
        report = check_isolated(close_isolated_gds, (1, 0), 1.5)
        assert report.total_violations == 0
        assert report.violations == []

    def test_boundary_no_violation(self, close_isolated_gds: Path) -> None:
        """边界: 间距 == 阈值 → 不违规（KLayout 边界行为）。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.0)
        assert report.total_violations == 0

    def test_far_isolated_pass(self, far_isolated_gds: Path) -> None:
        """远距离（5μm）检查 2.5μm → 通过。"""
        report = check_isolated(far_isolated_gds, (1, 0), 2.5)
        assert report.total_violations == 0

    def test_single_poly_no_violation(self, single_gds: Path) -> None:
        """单多边形 → 无违规（无其他多边形比较）。"""
        report = check_isolated(single_gds, (1, 0), 1.0)
        assert report.total_violations == 0

    def test_multi_isolated_violations(
        self, multi_isolated_gds: Path,
    ) -> None:
        """多对近距离（1μm）检查 2.0μm → 多个违规。"""
        report = check_isolated(multi_isolated_gds, (1, 0), 2.0)
        assert report.total_violations >= 3  # 至少 3 对相邻

    def test_violation_bbox(self, close_isolated_gds: Path) -> None:
        """违规包围盒存在。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.bbox is not None
        (xmin, ymin), (xmax, ymax) = report.bbox
        # 两个矩形 x=0-1, 3-4；违规区域在 x=1-3, y=0-1 (μm)
        assert xmin == pytest.approx(1.0, abs=0.01)
        assert xmax == pytest.approx(3.0, abs=0.01)

    def test_violation_fields(self, close_isolated_gds: Path) -> None:
        """违规字段完整。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        v = report.violations[0]
        assert isinstance(v, IsolatedDRCViolation)
        assert v.distance_um == pytest.approx(2.0, rel=1e-3)


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_isolated(self, hier_gds: Path) -> None:
        """层次化 GDSII isolated 检查（递归遍历子 cell）。"""
        report = check_isolated(hier_gds, (1, 0), 2.5)
        # CHILD 含两个间距 2μm 的矩形，应该有 1 个违规
        assert report.total_violations == 1
        assert report.violations[0].distance_um == pytest.approx(
            2.0, rel=1e-3,
        )


# =============================================================================
# TestGenerateIsolatedDrcReport: 报告生成
# =============================================================================
class TestGenerateIsolatedDrcReport:
    """generate_isolated_drc_report 函数测试。"""

    def test_text_report(self, close_isolated_gds: Path) -> None:
        """text 格式报告。"""
        result = generate_isolated_drc_report(
            close_isolated_gds, (1, 0), 2.5, output_format="text",
        )
        assert isinstance(result, str)
        assert "GDSII Isolated DRC 检查报告" in result
        assert "违规总数" in result
        assert "isolated" in result

    def test_markdown_report(self, close_isolated_gds: Path) -> None:
        """markdown 格式报告。"""
        result = generate_isolated_drc_report(
            close_isolated_gds, (1, 0), 2.5, output_format="markdown",
        )
        assert isinstance(result, str)
        assert "# GDSII Isolated DRC 检查报告" in result
        assert "| 违规总数 |" in result

    def test_json_report(self, close_isolated_gds: Path) -> None:
        """json 格式报告。"""
        result = generate_isolated_drc_report(
            close_isolated_gds, (1, 0), 2.5, output_format="json",
        )
        data = json.loads(result)
        assert data["check_type"] == "isolated"
        assert data["total_violations"] == 1
        assert data["min_isolated_um"] == pytest.approx(2.5)
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["distance_um"] == pytest.approx(2.0, rel=1e-3)

    def test_json_no_violations(self, single_gds: Path) -> None:
        """无违规时 json 报告。"""
        result = generate_isolated_drc_report(
            single_gds, (1, 0), 1.0, output_format="json",
        )
        data = json.loads(result)
        assert data["total_violations"] == 0
        assert data["violations"] == []
        assert data["bbox"] is None

    def test_text_report_no_violations(self, single_gds: Path) -> None:
        """无违规时 text 报告。"""
        result = generate_isolated_drc_report(
            single_gds, (1, 0), 1.0, output_format="text",
        )
        assert "违规总数: 0" in result

    def test_markdown_report_no_violations(self, single_gds: Path) -> None:
        """无违规时 markdown 报告。"""
        result = generate_isolated_drc_report(
            single_gds, (1, 0), 1.0, output_format="markdown",
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
            check_isolated(tmp_path / "nonexistent.gds", (1, 0), 1.0)

    def test_not_a_file_raise(self, tmp_path: Path) -> None:
        """非文件路径 raise。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ValueError, match="不是文件"):
            check_isolated(d, (1, 0), 1.0)

    def test_invalid_layer_tuple_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """layer 非 2 元组 raise。"""
        with pytest.raises(ValueError, match="二元组"):
            check_isolated(close_isolated_gds, (1,), 1.0)  # type: ignore

    def test_layer_out_of_range_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """layer 超范围 raise。"""
        with pytest.raises(ValueError, match="layer 必须 0-999"):
            check_isolated(close_isolated_gds, (1000, 0), 1.0)

    def test_datatype_out_of_range_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """datatype 超范围 raise。"""
        with pytest.raises(ValueError, match="datatype 必须 0-255"):
            check_isolated(close_isolated_gds, (1, 256), 1.0)

    def test_min_isolated_zero_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """min_isolated_um=0 raise。"""
        with pytest.raises(ValueError, match="min_isolated_um 必须 > 0"):
            check_isolated(close_isolated_gds, (1, 0), 0.0)

    def test_min_isolated_negative_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """min_isolated_um 负值 raise。"""
        with pytest.raises(ValueError, match="min_isolated_um 必须 > 0"):
            check_isolated(close_isolated_gds, (1, 0), -1.0)

    def test_max_violations_zero_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """max_violations=0 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_isolated(close_isolated_gds, (1, 0), 1.0, max_violations=0)

    def test_max_violations_negative_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """max_violations 负值 raise。"""
        with pytest.raises(ValueError, match="max_violations 必须 > 0"):
            check_isolated(close_isolated_gds, (1, 0), 1.0, max_violations=-1)

    def test_nonexistent_top_cell_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """不存在的 top_cell_name raise。"""
        with pytest.raises(ValueError, match="顶层 cell"):
            check_isolated(
                close_isolated_gds, (1, 0), 1.0, top_cell_name="NOEXIST",
            )

    def test_nonexistent_layer_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """不存在的层 raise。"""
        with pytest.raises(ValueError, match="不存在"):
            check_isolated(close_isolated_gds, (99, 0), 1.0)

    def test_invalid_output_format_raise(
        self, close_isolated_gds: Path,
    ) -> None:
        """无效 output_format raise。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_isolated_drc_report(
                close_isolated_gds, (1, 0), 1.0, output_format="xml",
            )

    def test_invalid_gds_file_raise(self, tmp_path: Path) -> None:
        """无效 GDS 文件 raise RuntimeError。"""
        bad = tmp_path / "bad.gds"
        bad.write_text("not a gds file")
        with pytest.raises(RuntimeError, match="读取文件失败"):
            check_isolated(bad, (1, 0), 1.0)

    def test_max_violations_limit(
        self, multi_isolated_gds: Path,
    ) -> None:
        """max_violations 限制返回数。"""
        report = check_isolated(
            multi_isolated_gds, (1, 0), 2.0, max_violations=1,
        )
        assert len(report.violations) <= 1
        # total_violations 仍是实际总数
        assert report.total_violations >= len(report.violations)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块 docstring 存在。"""
        from polaris.verification import gdsii_drc_isolated
        assert gdsii_drc_isolated.__doc__ is not None
        assert len(gdsii_drc_isolated.__doc__) > 100

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL（≥5）。"""
        from polaris.verification import gdsii_drc_isolated
        doc = gdsii_drc_isolated.__doc__
        url_count = doc.count("http")
        assert url_count >= 5

    def test_module_docstring_has_klayout_ref(self) -> None:
        """docstring 含 klayout 引用。"""
        from polaris.verification import gdsii_drc_isolated
        doc = gdsii_drc_isolated.__doc__
        assert "klayout" in doc.lower()

    def test_module_docstring_has_isolated_check_ref(self) -> None:
        """docstring 含 isolated_check 引用。"""
        from polaris.verification import gdsii_drc_isolated
        doc = gdsii_drc_isolated.__doc__
        assert "isolated_check" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_drc_isolated
        doc = gdsii_drc_isolated.__doc__
        assert "R01" in doc and "R02" in doc and "R03" in doc and "R11" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_drc_isolated as m
        for fn in (m.check_isolated, m.generate_isolated_drc_report):
            src = fn.__doc__ or ""
            assert "klayout.de" in src or "klayout.org" in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_violation(
        self, close_isolated_gds: Path,
    ) -> None:
        """近距离完整工作流（违规）。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        assert report.check_type == "isolated"
        assert report.total_violations == 1
        assert len(report.violations) == 1
        assert report.bbox is not None
        v = report.violations[0]
        assert v.distance_um == pytest.approx(2.0, rel=1e-3)

    def test_full_workflow_pass(self, far_isolated_gds: Path) -> None:
        """远距离完整工作流（通过）。"""
        report = check_isolated(far_isolated_gds, (1, 0), 2.5)
        assert report.total_violations == 0
        assert report.violations == []
        assert report.bbox is None

    def test_run_then_generate_consistent(
        self, close_isolated_gds: Path,
    ) -> None:
        """check_isolated 和 generate_isolated_drc_report 结果一致。"""
        report = check_isolated(close_isolated_gds, (1, 0), 2.5)
        json_str = generate_isolated_drc_report(
            close_isolated_gds, (1, 0), 2.5, output_format="json",
        )
        data = json.loads(json_str)
        assert data["total_violations"] == report.total_violations
        assert data["check_type"] == report.check_type
        assert data["min_isolated_um"] == pytest.approx(
            report.min_isolated_um,
        )

    def test_threshold_monotonicity(
        self, close_isolated_gds: Path,
    ) -> None:
        """阈值单调性: 阈值越大，违规数越多。"""
        r_strict = check_isolated(close_isolated_gds, (1, 0), 2.5)
        r_loose = check_isolated(close_isolated_gds, (1, 0), 1.5)
        assert r_strict.total_violations >= r_loose.total_violations


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_violation_construction(self) -> None:
        """IsolatedDRCViolation 构造。"""
        v = IsolatedDRCViolation(0, 0, 1, 0, 1, 0, 2, 0, 1.0)
        assert v.distance_um == 1.0
        assert v.x1_dbu == 0
        assert v.y1_dbu == 0

    def test_report_defaults(self) -> None:
        """IsolatedDRCReport 默认值。"""
        r = IsolatedDRCReport()
        assert r.input_path == ""
        assert r.layer == (0, 0)
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.min_isolated_um == 0.0
        assert r.check_type == "isolated"
        assert r.total_violations == 0
        assert r.violations == []
        assert r.bbox is None

    def test_report_mutable_defaults(self) -> None:
        """IsolatedDRCReport 可变默认值独立。"""
        r1 = IsolatedDRCReport()
        r2 = IsolatedDRCReport()
        r1.violations.append(IsolatedDRCViolation(0, 0, 0, 0, 0, 0, 0, 0, 0.0))
        assert len(r2.violations) == 0
