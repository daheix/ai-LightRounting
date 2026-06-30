"""R340 GDSII 布尔运算工具测试。

覆盖:
- boolean_operation: AND/OR/NOT/XOR 四种运算、面积/count/bbox 统计
- generate_boolean_report: text/markdown/json 报告
- R03 错误处理（禁止 fall-back）
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region: https://klayout.org/klayout-pypi/overview/geometry/regions/
- KLayout DRC Boolean: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- gdsfactory boolean_klayout: https://gdsfactory.github.io/gdsfactory7/_modules/gdsfactory/geometry/boolean_klayout.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_boolean_ops import (
    BooleanReport,
    boolean_operation,
    generate_boolean_report,
    VALID_OPERATIONS,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_two_layer_gds(path: Path) -> Path:
    """创建两层层 GDSII（用于布尔运算）。

    结构（dbu=0.001μm，即 1nm）:
    - layer (1,0): Box(0,0)-(3000,4000)  → 3μm×4μm = 12μm²
    - layer (2,0): Box(1000,1000)-(6000,2000)  → 5μm×1μm = 5μm²
    - 重叠区: (1000,1000)-(3000,2000) = 2μm×1μm = 2μm²
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li1 = ly.layer(1, 0)
    li2 = ly.layer(2, 0)

    top = ly.create_cell("TOP")
    top.shapes(li1).insert(db.Box(0, 0, 3000, 4000))
    top.shapes(li2).insert(db.Box(1000, 1000, 6000, 2000))

    ly.write(str(path))
    return path


def _make_disjoint_layer_gds(path: Path) -> Path:
    """创建不相交的两层 GDSII。

    结构:
    - layer (1,0): Box(0,0)-(1000,1000)  → 1μm²
    - layer (2,0): Box(5000,5000)-(6000,6000)  → 1μm²
    - 无重叠
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li1 = ly.layer(1, 0)
    li2 = ly.layer(2, 0)

    top = ly.create_cell("TOP")
    top.shapes(li1).insert(db.Box(0, 0, 1000, 1000))
    top.shapes(li2).insert(db.Box(5000, 5000, 6000, 6000))

    ly.write(str(path))
    return path


def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII（子 cell 含 shapes）。

    结构:
    - TOP cell
      - CHILD @ (0, 0)
    - CHILD cell
      - layer (1,0): Box(0,0)-(2000,2000)
    - TOP cell 直接 layer (2,0): Box(500,500)-(3000,3000)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li1 = ly.layer(1, 0)
    li2 = ly.layer(2, 0)

    child = ly.create_cell("CHILD")
    child.shapes(li1).insert(db.Box(0, 0, 2000, 2000))

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    top.shapes(li2).insert(db.Box(500, 500, 3000, 3000))

    ly.write(str(path))
    return path


@pytest.fixture
def two_layer_gds(tmp_path: Path) -> Path:
    """两层层 GDSII（有重叠）。"""
    return _make_two_layer_gds(tmp_path / "two_layer.gds")


@pytest.fixture
def disjoint_gds(tmp_path: Path) -> Path:
    """不相交两层 GDSII。"""
    return _make_disjoint_layer_gds(tmp_path / "disjoint.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


# =============================================================================
# TestBooleanOperation: 基本布尔运算
# =============================================================================
class TestBooleanOperation:
    """boolean_operation 函数测试。"""

    def test_returns_report(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """返回 BooleanReport。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(
            two_layer_gds, out, "and",
            (1, 0), (2, 0), (3, 0)
        )
        assert isinstance(report, BooleanReport)

    def test_input_path(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """input_path 正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.input_path == str(two_layer_gds)

    def test_output_path(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """output_path 正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.output_path == str(out)

    def test_dbu(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """dbu 正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """top_cell_name 正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.top_cell_name == "TOP"

    def test_operation_lowercased(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """operation 被小写化。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "AND", (1, 0), (2, 0), (3, 0))
        assert report.operation == "and"

    def test_layers_recorded(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """层信息记录正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.layer_a == (1, 0)
        assert report.layer_b == (2, 0)
        assert report.layer_result == (3, 0)

    def test_output_file_exists(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """输出文件被创建。"""
        out = tmp_path / "out.gds"
        boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert out.exists()


# =============================================================================
# TestAndOperation: AND 交集
# =============================================================================
class TestAndOperation:
    """AND 布尔运算测试。"""

    def test_and_area(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """AND 面积 = 重叠区面积 = 2μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        # 重叠区 (1000,1000)-(3000,2000) = 2μm×1μm = 2μm²
        assert report.area_result_um2 == pytest.approx(2.0, rel=1e-6)

    def test_and_area_a(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """A 面积 = 12μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.area_a_um2 == pytest.approx(12.0, rel=1e-6)

    def test_and_area_b(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """B 面积 = 5μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.area_b_um2 == pytest.approx(5.0, rel=1e-6)

    def test_and_count(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """AND 结果 1 个 polygon。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.count_result == 1

    def test_and_bbox(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """AND bbox 正确。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.bbox_result is not None
        (xmin, ymin), (xmax, ymax) = report.bbox_result
        assert xmin == pytest.approx(1.0, rel=1e-6)
        assert ymin == pytest.approx(1.0, rel=1e-6)
        assert xmax == pytest.approx(3.0, rel=1e-6)
        assert ymax == pytest.approx(2.0, rel=1e-6)

    def test_and_disjoint_empty(self, disjoint_gds: Path, tmp_path: Path) -> None:
        """不相交时 AND 结果为空。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(disjoint_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.area_result_um2 == pytest.approx(0.0)
        assert report.count_result == 0
        assert report.bbox_result is None


# =============================================================================
# TestOrOperation: OR 并集
# =============================================================================
class TestOrOperation:
    """OR 布尔运算测试。"""

    def test_or_area(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """OR 面积 = A+B-重叠 = 12+5-2 = 15μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "or", (1, 0), (2, 0), (3, 0))
        assert report.area_result_um2 == pytest.approx(15.0, rel=1e-6)

    def test_or_count_merged(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """OR 结果合并后 1 个 polygon（merged 去重叠）。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "or", (1, 0), (2, 0), (3, 0))
        assert report.count_result == 1

    def test_or_disjoint_count(self, disjoint_gds: Path, tmp_path: Path) -> None:
        """不相交时 OR 结果 2 个 polygon。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(disjoint_gds, out, "or", (1, 0), (2, 0), (3, 0))
        assert report.count_result == 2
        assert report.area_result_um2 == pytest.approx(2.0, rel=1e-6)


# =============================================================================
# TestNotOperation: NOT 差集
# =============================================================================
class TestNotOperation:
    """NOT 布尔运算测试（A - B）。"""

    def test_not_area(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """NOT 面积 = A - 重叠 = 12-2 = 10μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "not", (1, 0), (2, 0), (3, 0))
        assert report.area_result_um2 == pytest.approx(10.0, rel=1e-6)

    def test_not_count(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """NOT 结果可能是 1 或多个 polygon（取决于几何）。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "not", (1, 0), (2, 0), (3, 0))
        assert report.count_result >= 1

    def test_not_disjoint_full(self, disjoint_gds: Path, tmp_path: Path) -> None:
        """不相交时 NOT = A 完整。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(disjoint_gds, out, "not", (1, 0), (2, 0), (3, 0))
        assert report.area_result_um2 == pytest.approx(1.0, rel=1e-6)


# =============================================================================
# TestXorOperation: XOR 对称差
# =============================================================================
class TestXorOperation:
    """XOR 布尔运算测试。"""

    def test_xor_area(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """XOR 面积 = A+B-2*重叠 = 12+5-4 = 13μm²。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "xor", (1, 0), (2, 0), (3, 0))
        assert report.area_result_um2 == pytest.approx(13.0, rel=1e-6)

    def test_xor_count(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """XOR 结果 ≥1 个 polygon。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(two_layer_gds, out, "xor", (1, 0), (2, 0), (3, 0))
        assert report.count_result >= 1

    def test_xor_disjoint_count(self, disjoint_gds: Path, tmp_path: Path) -> None:
        """不相交时 XOR = A+B（2 个 polygon）。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(disjoint_gds, out, "xor", (1, 0), (2, 0), (3, 0))
        assert report.count_result == 2
        assert report.area_result_um2 == pytest.approx(2.0, rel=1e-6)


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 布尔运算测试。"""

    def test_hierarchical_and(self, hier_gds: Path, tmp_path: Path) -> None:
        """层次化 GDSII AND 运算（递归遍历子 cell）。"""
        out = tmp_path / "out.gds"
        # CHILD 的 layer(1,0): Box(0,0)-(2000,2000) = 4μm²
        # TOP 的 layer(2,0): Box(500,500)-(3000,3000) = 6.25μm²
        # 重叠: (500,500)-(2000,2000) = 1.5μm×1.5μm = 2.25μm²
        report = boolean_operation(hier_gds, out, "and", (1, 0), (2, 0), (3, 0))
        assert report.area_a_um2 == pytest.approx(4.0, rel=1e-6)
        assert report.area_b_um2 == pytest.approx(6.25, rel=1e-6)
        assert report.area_result_um2 == pytest.approx(2.25, rel=1e-6)

    def test_hierarchical_or(self, hier_gds: Path, tmp_path: Path) -> None:
        """层次化 GDSII OR 运算。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(hier_gds, out, "or", (1, 0), (2, 0), (3, 0))
        # OR = A + B - 重叠 = 4 + 6.25 - 2.25 = 8.0
        assert report.area_result_um2 == pytest.approx(8.0, rel=1e-6)


# =============================================================================
# TestGenerateBooleanReport: 报告生成
# =============================================================================
class TestGenerateBooleanReport:
    """generate_boolean_report 函数测试。"""

    def test_text_report(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_boolean_report(
            two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0),
            output_format="text"
        )
        assert isinstance(result, str)
        assert "GDSII 布尔运算报告" in result
        assert "AND" in result
        assert "操作数统计" in result

    def test_markdown_report(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_boolean_report(
            two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0),
            output_format="markdown"
        )
        assert isinstance(result, str)
        assert "# GDSII 布尔运算报告" in result
        assert "| A |" in result

    def test_json_report(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """json 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_boolean_report(
            two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0),
            output_format="json"
        )
        data = json.loads(result)
        assert data["operation"] == "and"
        assert data["area_a_um2"] == pytest.approx(12.0, rel=1e-6)
        assert data["area_result_um2"] == pytest.approx(2.0, rel=1e-6)
        assert data["layer_a"] == [1, 0]
        assert data["layer_result"] == [3, 0]

    def test_json_report_with_bbox(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """json 报告含 bbox。"""
        out = tmp_path / "out.gds"
        result = generate_boolean_report(
            two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0),
            output_format="json"
        )
        data = json.loads(result)
        assert data["bbox_result"] is not None
        assert data["bbox_result"]["xmin_um"] == pytest.approx(1.0, rel=1e-6)

    def test_json_report_empty_bbox(self, disjoint_gds: Path, tmp_path: Path) -> None:
        """不相交时 json 报告 bbox 为 None。"""
        out = tmp_path / "out.gds"
        result = generate_boolean_report(
            disjoint_gds, out, "and", (1, 0), (2, 0), (3, 0),
            output_format="json"
        )
        data = json.loads(result)
        assert data["bbox_result"] is None
        assert data["count_result"] == 0

    def test_unsupported_format_raises(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """不支持的格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_boolean_report(
                two_layer_gds, out, "and", (1, 0), (2, 0), (3, 0),
                output_format="xml"
            )


# =============================================================================
# TestR03ErrorHandling: 错误处理（禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="不存在"):
            boolean_operation(
                tmp_path / "nonexistent.gds", out, "and",
                (1, 0), (2, 0), (3, 0)
            )

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径不是文件 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不是文件"):
            boolean_operation(
                tmp_path, out, "and",
                (1, 0), (2, 0), (3, 0)
            )

    def test_unsupported_operation(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """不支持的 operation raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 operation"):
            boolean_operation(
                two_layer_gds, out, "nand",
                (1, 0), (2, 0), (3, 0)
            )

    def test_same_layer_a_b(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer_a == layer_b raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_a 和 layer_b 不能相同"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1, 0), (1, 0), (3, 0)
            )

    def test_result_layer_equals_a(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer_result == layer_a raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_result 不能等于 layer_a"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1, 0), (2, 0), (1, 0)
            )

    def test_result_layer_equals_b(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer_result == layer_b raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_result 不能等于 layer_b"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1, 0), (2, 0), (2, 0)
            )

    def test_layer_a_not_exist(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer_a 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_a"):
            boolean_operation(
                two_layer_gds, out, "and",
                (99, 0), (2, 0), (3, 0)
            )

    def test_layer_b_not_exist(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer_b 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_b"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1, 0), (99, 0), (3, 0)
            )

    def test_invalid_layer_format(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """层格式无效 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_a 必须是"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1,), (2, 0), (3, 0)  # type: ignore
            )

    def test_layer_out_of_range(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """layer 超范围 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1000, 0), (2, 0), (3, 0)
            )

    def test_top_cell_name_not_exist(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="top_cell_name"):
            boolean_operation(
                two_layer_gds, out, "and",
                (1, 0), (2, 0), (3, 0),
                top_cell_name="NONEXISTENT"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_urls(self) -> None:
        """模块 docstring 含 5+ URL。"""
        from polaris.verification import gdsii_boolean_ops
        doc = gdsii_boolean_ops.__doc__ or ""
        url_count = doc.count("https://")
        assert url_count >= 5, f"模块 docstring 只有 {url_count} 个 URL，要求 ≥5"

    def test_module_docstring_has_klayout_url(self) -> None:
        """模块 docstring 含 KLayout URL。"""
        from polaris.verification import gdsii_boolean_ops
        doc = gdsii_boolean_ops.__doc__ or ""
        assert "klayout.org" in doc

    def test_module_docstring_has_api_facts(self) -> None:
        """模块 docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_boolean_ops
        doc = gdsii_boolean_ops.__doc__ or ""
        assert "db.Region" in doc
        assert "begin_shapes_rec" in doc
        assert "merged" in doc

    def test_module_docstring_has_gdsfactory_ref(self) -> None:
        """模块 docstring 含 gdsfactory 参考。"""
        from polaris.verification import gdsii_boolean_ops
        doc = gdsii_boolean_ops.__doc__ or ""
        assert "gdsfactory" in doc

    def test_boolean_operation_docstring_has_source(self) -> None:
        """boolean_operation docstring 含来源 URL。"""
        assert "klayout.org" in boolean_operation.__doc__

    def test_no_fall_back_in_source(self) -> None:
        """源代码无 fall-back 模式。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_boolean_ops.py"
        src = src_path.read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_raise_in_error_paths(self) -> None:
        """错误路径用 raise。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_boolean_ops.py"
        src = src_path.read_text(encoding="utf-8")
        assert "raise FileNotFoundError" in src
        assert "raise ValueError" in src
        assert "raise RuntimeError" in src

    def test_module_docstring_has_compliance(self) -> None:
        """模块 docstring 含合规声明。"""
        from polaris.verification import gdsii_boolean_ops
        doc = gdsii_boolean_ops.__doc__ or ""
        assert "R01" in doc
        assert "R03" in doc

    def test_valid_operations_constant(self) -> None:
        """VALID_OPERATIONS 常量正确。"""
        assert VALID_OPERATIONS == ("and", "or", "not", "xor")


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_workflow_and_persisted(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """完整流程: AND 运算 → 重新读取 → 验证结果层。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(
            two_layer_gds, out, "and",
            (1, 0), (2, 0), (3, 0)
        )
        assert report.area_result_um2 == pytest.approx(2.0, rel=1e-6)

        # 重新读取验证结果层
        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        li_r = ly.layer(3, 0)
        r_result = db.Region(top.begin_shapes_rec(li_r))
        assert float(r_result.area()) * 0.001 * 0.001 == pytest.approx(2.0, rel=1e-6)

    def test_full_workflow_xor_persisted(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """完整流程: XOR 运算 → 重新读取 → 验证。"""
        out = tmp_path / "out.gds"
        report = boolean_operation(
            two_layer_gds, out, "xor",
            (1, 0), (2, 0), (3, 0)
        )
        assert report.area_result_um2 == pytest.approx(13.0, rel=1e-6)

        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        li_r = ly.layer(3, 0)
        r_result = db.Region(top.begin_shapes_rec(li_r))
        assert float(r_result.area()) * 1e-6 == pytest.approx(13.0, rel=1e-6)

    def test_all_operations(self, two_layer_gds: Path, tmp_path: Path) -> None:
        """测试所有 4 种运算。"""
        for op in VALID_OPERATIONS:
            out = tmp_path / f"out_{op}.gds"
            report = boolean_operation(
                two_layer_gds, out, op,
                (1, 0), (2, 0), (3, 0)
            )
            assert report.operation == op
            assert report.count_result >= 0
            assert out.exists()


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_boolean_report_defaults(self) -> None:
        """BooleanReport 默认值。"""
        report = BooleanReport()
        assert report.input_path == ""
        assert report.output_path == ""
        assert report.operation == ""
        assert report.layer_a == (0, 0)
        assert report.dbu == 0.0
        assert report.area_a_um2 == 0.0
        assert report.count_a == 0
        assert report.bbox_result is None
        assert report.top_cell_name == ""

    def test_boolean_report_with_values(self) -> None:
        """BooleanReport 赋值。"""
        report = BooleanReport(
            input_path="/in.gds",
            output_path="/out.gds",
            operation="and",
            layer_a=(1, 0),
            layer_b=(2, 0),
            layer_result=(3, 0),
            dbu=0.001,
            area_a_um2=12.0,
            area_b_um2=5.0,
            area_result_um2=2.0,
            count_a=1,
            count_b=1,
            count_result=1,
            bbox_result=((1.0, 1.0), (3.0, 2.0)),
            top_cell_name="TOP",
        )
        assert report.input_path == "/in.gds"
        assert report.operation == "and"
        assert report.area_result_um2 == 2.0
        assert report.bbox_result == ((1.0, 1.0), (3.0, 2.0))

    def test_boolean_report_is_dataclass(self) -> None:
        """BooleanReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(BooleanReport)
