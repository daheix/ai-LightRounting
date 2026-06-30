"""R341 GDSII 层 Sizing 工具测试。

覆盖:
- size_layer: 各向同性/各向异性 sizing、膨胀/收缩、收缩消失
- generate_sizing_report: text/markdown/json 报告
- R03 错误处理（禁止 fall-back）
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Region sized: https://klayout.org/klayout-pypi/overview/geometry/regions/
- KLayout Region class: https://www.klayout.de/doc-qt5/code/class_Region.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_sizing_tool import (
    SizingReport,
    size_layer,
    generate_sizing_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_single_rect_gds(path: Path) -> Path:
    """创建单矩形 GDSII。

    layer (1,0): Box(1000,1000)-(3000,4000) = 2μm×3μm = 6μm²
    dbu = 0.001μm (1nm)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(1000, 1000, 3000, 4000))
    ly.write(str(path))
    return path


def _make_multi_poly_gds(path: Path) -> Path:
    """创建多边形 GDSII（2 个不相交矩形）。

    layer (1,0):
    - Box(0,0)-(2000,2000) = 2μm×2μm
    - Box(5000,5000)-(7000,7000) = 2μm×2μm
    总 area = 8μm², count = 2
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 2000, 2000))
    top.shapes(li).insert(db.Box(5000, 5000, 7000, 7000))
    ly.write(str(path))
    return path


def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII。

    - TOP cell
      - CHILD @ (0, 0)
    - CHILD cell
      - layer (1,0): Box(0,0)-(2000,2000) = 2μm×2μm
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
def single_rect_gds(tmp_path: Path) -> Path:
    """单矩形 GDSII。"""
    return _make_single_rect_gds(tmp_path / "rect.gds")


@pytest.fixture
def multi_poly_gds(tmp_path: Path) -> Path:
    """多边形 GDSII。"""
    return _make_multi_poly_gds(tmp_path / "multi.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


# =============================================================================
# TestSizeLayer: 基本 sizing
# =============================================================================
class TestSizeLayer:
    """size_layer 函数测试。"""

    def test_returns_report(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """返回 SizingReport。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert isinstance(report, SizingReport)

    def test_input_path(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """input_path 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.input_path == str(single_rect_gds)

    def test_output_path(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """output_path 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.output_path == str(out)

    def test_dbu(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """dbu 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """top_cell_name 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.top_cell_name == "TOP"

    def test_layers_recorded(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """层信息记录正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.layer == (1, 0)
        assert report.layer_result == (2, 0)

    def test_size_recorded(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """size 信息记录正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.size_x_um == pytest.approx(0.5)
        assert report.size_y_um == pytest.approx(0.5)
        assert report.is_isotropic is True

    def test_output_file_exists(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """输出文件被创建。"""
        out = tmp_path / "out.gds"
        size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert out.exists()


# =============================================================================
# TestIsotropicSizing: 各向同性 sizing
# =============================================================================
class TestIsotropicSizing:
    """各向同性 sizing 测试。"""

    def test_grow_area(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """膨胀 +0.5μm: 6μm² → 12μm²。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        # 原始 2μm×3μm=6μm², +0.5μm 每边 → 3μm×4μm=12μm²
        assert report.area_before_um2 == pytest.approx(6.0, rel=1e-6)
        assert report.area_after_um2 == pytest.approx(12.0, rel=1e-6)

    def test_shrink_area(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """收缩 -0.5μm: 6μm² → 2μm²。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), -0.5)
        # 原始 2μm×3μm=6μm², -0.5μm 每边 → 1μm×2μm=2μm²
        assert report.area_before_um2 == pytest.approx(6.0, rel=1e-6)
        assert report.area_after_um2 == pytest.approx(2.0, rel=1e-6)

    def test_grow_bbox(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """膨胀 bbox 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        # 原 bbox (1,1)-(3,4), +0.5 → (0.5,0.5)-(3.5,4.5)
        assert report.bbox_before is not None
        (xmin, ymin), (xmax, ymax) = report.bbox_before
        assert xmin == pytest.approx(1.0, rel=1e-6)
        assert ymin == pytest.approx(1.0, rel=1e-6)
        assert xmax == pytest.approx(3.0, rel=1e-6)
        assert ymax == pytest.approx(4.0, rel=1e-6)

        assert report.bbox_after is not None
        (xmin, ymin), (xmax, ymax) = report.bbox_after
        assert xmin == pytest.approx(0.5, rel=1e-6)
        assert ymin == pytest.approx(0.5, rel=1e-6)
        assert xmax == pytest.approx(3.5, rel=1e-6)
        assert ymax == pytest.approx(4.5, rel=1e-6)

    def test_count_preserved(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """单矩形 sizing 后 count 仍为 1。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.count_before == 1
        assert report.count_after == 1

    def test_default_y_is_isotropic(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """size_y_um=None 时各向同性。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.is_isotropic is True
        assert report.size_y_um == report.size_x_um

    def test_multi_poly_grow(self, multi_poly_gds: Path, tmp_path: Path) -> None:
        """多 polygon 膨胀（不相交保持 2 个）。"""
        out = tmp_path / "out.gds"
        report = size_layer(multi_poly_gds, out, (1, 0), (2, 0), 0.1)
        # 不相交，+0.1μm 不会合并
        assert report.count_before == 2
        assert report.count_after == 2


# =============================================================================
# TestAnisotropicSizing: 各向异性 sizing
# =============================================================================
class TestAnisotropicSizing:
    """各向异性 sizing 测试。"""

    def test_anisotropic_area(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """各向异性 +1μm X, +2μm Y: 6μm² → 28μm²。"""
        out = tmp_path / "out.gds"
        report = size_layer(
            single_rect_gds, out, (1, 0), (2, 0),
            size_x_um=1.0, size_y_um=2.0
        )
        # 原 2μm×3μm, +1μm X 每边 → 4μm, +2μm Y 每边 → 7μm → 28μm²
        assert report.area_after_um2 == pytest.approx(28.0, rel=1e-6)
        assert report.is_isotropic is False

    def test_anisotropic_bbox(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """各向异性 bbox 正确。"""
        out = tmp_path / "out.gds"
        report = size_layer(
            single_rect_gds, out, (1, 0), (2, 0),
            size_x_um=1.0, size_y_um=2.0
        )
        # 原 (1,1)-(3,4), +1μm X → (0,1)-(4,4), +2μm Y → (0,-1)-(4,6)
        assert report.bbox_after is not None
        (xmin, ymin), (xmax, ymax) = report.bbox_after
        assert xmin == pytest.approx(0.0, rel=1e-6)
        assert ymin == pytest.approx(-1.0, rel=1e-6)
        assert xmax == pytest.approx(4.0, rel=1e-6)
        assert ymax == pytest.approx(6.0, rel=1e-6)

    def test_anisotropic_shrink(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """各向异性收缩 -0.5μm X, -1μm Y。"""
        out = tmp_path / "out.gds"
        report = size_layer(
            single_rect_gds, out, (1, 0), (2, 0),
            size_x_um=-0.5, size_y_um=-1.0
        )
        # 原 2μm×3μm, -0.5μm X → 1μm, -1μm Y → 1μm → 1μm²
        assert report.area_after_um2 == pytest.approx(1.0, rel=1e-6)


# =============================================================================
# TestShrinkToEmpty: 收缩消失
# =============================================================================
class TestShrinkToEmpty:
    """收缩超过半宽导致消失。"""

    def test_shrink_to_empty_area(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """收缩 -2μm（超过半宽 1μm）→ 消失。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), -2.0)
        assert report.area_after_um2 == pytest.approx(0.0)
        assert report.count_after == 0
        assert report.bbox_after is None

    def test_shrink_to_empty_count(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """收缩消失 count=0。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), -1.5)
        assert report.count_after == 0


# =============================================================================
# TestHierarchical: 层次化测试
# =============================================================================
class TestHierarchical:
    """层次化 GDSII sizing 测试。"""

    def test_hierarchical_grow(self, hier_gds: Path, tmp_path: Path) -> None:
        """层次化 GDSII sizing（递归遍历子 cell）。"""
        out = tmp_path / "out.gds"
        # CHILD 的 layer(1,0): Box(0,0)-(2000,2000) = 4μm²
        # +0.5μm → 3μm×3μm = 9μm²
        report = size_layer(hier_gds, out, (1, 0), (2, 0), 0.5)
        assert report.area_before_um2 == pytest.approx(4.0, rel=1e-6)
        assert report.area_after_um2 == pytest.approx(9.0, rel=1e-6)


# =============================================================================
# TestGenerateSizingReport: 报告生成
# =============================================================================
class TestGenerateSizingReport:
    """generate_sizing_report 函数测试。"""

    def test_text_report(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_sizing_report(
            single_rect_gds, out, (1, 0), (2, 0), 0.5,
            output_format="text"
        )
        assert isinstance(result, str)
        assert "GDSII 层 Sizing 报告" in result
        assert "各向同性" in result
        assert "操作前统计" in result

    def test_markdown_report(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_sizing_report(
            single_rect_gds, out, (1, 0), (2, 0), 0.5,
            output_format="markdown"
        )
        assert isinstance(result, str)
        assert "# GDSII 层 Sizing 报告" in result
        assert "| 面积 (μm²) |" in result

    def test_json_report(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """json 格式报告。"""
        out = tmp_path / "out.gds"
        result = generate_sizing_report(
            single_rect_gds, out, (1, 0), (2, 0), 0.5,
            output_format="json"
        )
        data = json.loads(result)
        assert data["size_x_um"] == pytest.approx(0.5)
        assert data["is_isotropic"] is True
        assert data["area_before_um2"] == pytest.approx(6.0, rel=1e-6)
        assert data["area_after_um2"] == pytest.approx(12.0, rel=1e-6)

    def test_json_anisotropic(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """json 各向异性报告。"""
        out = tmp_path / "out.gds"
        result = generate_sizing_report(
            single_rect_gds, out, (1, 0), (2, 0),
            size_x_um=1.0, size_y_um=2.0,
            output_format="json"
        )
        data = json.loads(result)
        assert data["is_isotropic"] is False
        assert data["size_x_um"] == pytest.approx(1.0)
        assert data["size_y_um"] == pytest.approx(2.0)

    def test_json_empty_bbox(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """收缩消失时 json bbox_after 为 None。"""
        out = tmp_path / "out.gds"
        result = generate_sizing_report(
            single_rect_gds, out, (1, 0), (2, 0), -2.0,
            output_format="json"
        )
        data = json.loads(result)
        assert data["bbox_after"] is None
        assert data["count_after"] == 0

    def test_unsupported_format_raises(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """不支持的格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_sizing_report(
                single_rect_gds, out, (1, 0), (2, 0), 0.5,
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
            size_layer(tmp_path / "nonexistent.gds", out, (1, 0), (2, 0), 0.5)

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径不是文件 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不是文件"):
            size_layer(tmp_path, out, (1, 0), (2, 0), 0.5)

    def test_same_layer(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """layer == layer_result raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer 和 layer_result 不能相同"):
            size_layer(single_rect_gds, out, (1, 0), (1, 0), 0.5)

    def test_zero_size_x(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """size_x_um=0 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="size_x_um 不能为 0"):
            size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.0)

    def test_zero_size_y(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """size_y_um=0 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="size_y_um 不能为 0"):
            size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5, size_y_um=0.0)

    def test_layer_not_exist(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """layer 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer"):
            size_layer(single_rect_gds, out, (99, 0), (2, 0), 0.5)

    def test_invalid_layer_format(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """层格式无效 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer 必须是"):
            size_layer(single_rect_gds, out, (1,), (2, 0), 0.5)  # type: ignore

    def test_layer_out_of_range(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """layer 超范围 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer"):
            size_layer(single_rect_gds, out, (1000, 0), (2, 0), 0.5)

    def test_top_cell_name_not_exist(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="top_cell_name"):
            size_layer(
                single_rect_gds, out, (1, 0), (2, 0), 0.5,
                top_cell_name="NONEXISTENT"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_urls(self) -> None:
        """模块 docstring 含 5+ URL。"""
        from polaris.verification import gdsii_sizing_tool
        doc = gdsii_sizing_tool.__doc__ or ""
        url_count = doc.count("https://")
        assert url_count >= 5, f"模块 docstring 只有 {url_count} 个 URL，要求 ≥5"

    def test_module_docstring_has_klayout_url(self) -> None:
        """模块 docstring 含 KLayout URL。"""
        from polaris.verification import gdsii_sizing_tool
        doc = gdsii_sizing_tool.__doc__ or ""
        assert "klayout.org" in doc

    def test_module_docstring_has_api_facts(self) -> None:
        """模块 docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_sizing_tool
        doc = gdsii_sizing_tool.__doc__ or ""
        assert "sized" in doc
        assert "db.Region" in doc

    def test_module_docstring_has_opc_ref(self) -> None:
        """模块 docstring 含 OPC 参考（sizing 商业应用）。"""
        from polaris.verification import gdsii_sizing_tool
        doc = gdsii_sizing_tool.__doc__ or ""
        assert "OPC" in doc or "Proximity" in doc

    def test_size_layer_docstring_has_source(self) -> None:
        """size_layer docstring 含来源 URL。"""
        assert "klayout.org" in size_layer.__doc__

    def test_no_fall_back_in_source(self) -> None:
        """源代码无 fall-back 模式。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_sizing_tool.py"
        src = src_path.read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_raise_in_error_paths(self) -> None:
        """错误路径用 raise。"""
        src_path = Path(__file__).parent.parent / "src" / "polaris" / "verification" / "gdsii_sizing_tool.py"
        src = src_path.read_text(encoding="utf-8")
        assert "raise FileNotFoundError" in src
        assert "raise ValueError" in src
        assert "raise RuntimeError" in src

    def test_module_docstring_has_compliance(self) -> None:
        """模块 docstring 含合规声明。"""
        from polaris.verification import gdsii_sizing_tool
        doc = gdsii_sizing_tool.__doc__ or ""
        assert "R01" in doc
        assert "R03" in doc


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_workflow_grow_persisted(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """完整流程: 膨胀 → 重新读取 → 验证结果层。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), 0.5)
        assert report.area_after_um2 == pytest.approx(12.0, rel=1e-6)

        # 重新读取验证结果层
        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        li_r = ly.layer(2, 0)
        r_result = db.Region(top.begin_shapes_rec(li_r))
        assert float(r_result.area()) * 1e-6 == pytest.approx(12.0, rel=1e-6)

    def test_full_workflow_shrink_persisted(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """完整流程: 收缩 → 重新读取 → 验证。"""
        out = tmp_path / "out.gds"
        report = size_layer(single_rect_gds, out, (1, 0), (2, 0), -0.5)
        assert report.area_after_um2 == pytest.approx(2.0, rel=1e-6)

        ly = db.Layout()
        ly.read(str(out))
        top = ly.cell("TOP")
        li_r = ly.layer(2, 0)
        r_result = db.Region(top.begin_shapes_rec(li_r))
        assert float(r_result.area()) * 1e-6 == pytest.approx(2.0, rel=1e-6)

    def test_grow_and_shrink_inverse(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """先膨胀再收缩（不同层），面积近似恢复。"""
        # 第一次: +0.5μm 到 layer 2
        out1 = tmp_path / "out1.gds"
        size_layer(single_rect_gds, out1, (1, 0), (2, 0), 0.5)

        # 第二次: -0.5μm 从 layer 2 到 layer 3
        out2 = tmp_path / "out2.gds"
        report = size_layer(out1, out2, (2, 0), (3, 0), -0.5)
        # 理论上应该恢复到 6μm²（实际可能有数值误差）
        assert report.area_after_um2 == pytest.approx(6.0, rel=1e-3)


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_sizing_report_defaults(self) -> None:
        """SizingReport 默认值。"""
        report = SizingReport()
        assert report.input_path == ""
        assert report.output_path == ""
        assert report.layer == (0, 0)
        assert report.dbu == 0.0
        assert report.size_x_um == 0.0
        assert report.is_isotropic is True
        assert report.area_before_um2 == 0.0
        assert report.count_before == 0
        assert report.bbox_before is None
        assert report.bbox_after is None
        assert report.top_cell_name == ""

    def test_sizing_report_with_values(self) -> None:
        """SizingReport 赋值。"""
        report = SizingReport(
            input_path="/in.gds",
            output_path="/out.gds",
            layer=(1, 0),
            layer_result=(2, 0),
            dbu=0.001,
            size_x_um=0.5,
            size_y_um=0.5,
            is_isotropic=True,
            area_before_um2=6.0,
            area_after_um2=12.0,
            count_before=1,
            count_after=1,
            bbox_before=((1.0, 1.0), (3.0, 4.0)),
            bbox_after=((0.5, 0.5), (3.5, 4.5)),
            top_cell_name="TOP",
        )
        assert report.input_path == "/in.gds"
        assert report.area_after_um2 == 12.0
        assert report.bbox_after == ((0.5, 0.5), (3.5, 4.5))

    def test_sizing_report_is_dataclass(self) -> None:
        """SizingReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(SizingReport)
