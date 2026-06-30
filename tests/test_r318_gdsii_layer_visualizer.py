"""R318 GDSII 层结构可视化工具测试。

覆盖:
- compute_layer_stats: 各层多边形数/总面积/包围盒
- visualize_layers_ascii: ASCII art 可视化（扫描线填充）
- generate_summary_report: text/markdown 摘要报告
- _fill_polygon: 扫描线填充算法内部测试
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 扫描线填充算法: https://en.wikipedia.org/wiki/Scanline_fill
- ASCII art 渲染: https://en.wikipedia.org/wiki/ASCII_art
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_layer_visualizer import (
    GDSIISummary,
    LayerStats,
    _fill_polygon,
    compute_layer_stats,
    generate_summary_report,
    visualize_layers_ascii,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def single_layer_gds(tmp_path: Path) -> Path:
    """创建单层 GDSII 文件（WG 层，1 个矩形 10x0.5 μm）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "single_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII 文件（WG + METAL 两层）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,  # WG
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
                {
                    "layer": 5, "datatype": 0,  # METAL
                    "points": [[0, 1], [10, 1], [10, 2], [0, 2]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_polygon_gds(tmp_path: Path) -> Path:
    """创建多多边形 GDSII 文件（WG 层，2 个分离矩形）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [5, 0], [5, 1], [0, 1]],
                },
                {
                    "layer": 1, "datatype": 0,
                    "points": [[10, 0], [15, 0], [15, 1], [10, 1]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_polygon.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def custom_layer_gds(tmp_path: Path) -> Path:
    """创建自定义层 GDSII 文件（layer 100, datatype 0）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 100, "datatype": 0,
                    "points": [[0, 0], [5, 0], [5, 5], [0, 5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "custom_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestComputeLayerStats: compute_layer_stats 测试
# =============================================================================
class TestComputeLayerStats:
    """compute_layer_stats 函数测试。"""

    def test_single_layer_returns_summary(self, single_layer_gds: Path) -> None:
        """单层 GDSII 返回有效摘要。"""
        summary = compute_layer_stats(single_layer_gds)
        assert isinstance(summary, GDSIISummary)
        assert summary.file_path == str(single_layer_gds)
        assert summary.top_cell_name == "TOP"
        assert summary.dbu > 0
        assert len(summary.layer_stats) == 1

    def test_single_layer_stats_correctness(self, single_layer_gds: Path) -> None:
        """单层统计正确（多边形数=1，面积=5μm²）。"""
        summary = compute_layer_stats(single_layer_gds)
        stats = summary.layer_stats[0]
        assert stats.layer_name == "WG"
        assert stats.gds_layer == 1
        assert stats.gds_datatype == 0
        assert stats.polygon_count == 1
        # 矩形 10x0.5 = 5.0 μm²
        assert stats.total_area_um2 == pytest.approx(5.0, rel=1e-3)
        assert stats.bbox_xmin == pytest.approx(0.0, abs=1e-3)
        assert stats.bbox_ymin == pytest.approx(0.0, abs=1e-3)
        assert stats.bbox_xmax == pytest.approx(10.0, abs=1e-3)
        assert stats.bbox_ymax == pytest.approx(0.5, abs=1e-3)

    def test_multi_layer_stats(self, multi_layer_gds: Path) -> None:
        """多层统计（WG + METAL）。"""
        summary = compute_layer_stats(multi_layer_gds)
        assert len(summary.layer_stats) == 2
        layer_names = {s.layer_name for s in summary.layer_stats}
        assert layer_names == {"WG", "METAL"}
        # 总多边形数 = 2
        assert summary.total_polygons == 2

    def test_multi_polygon_count(self, multi_polygon_gds: Path) -> None:
        """多边形数正确（2 个分离矩形）。"""
        summary = compute_layer_stats(multi_polygon_gds)
        assert len(summary.layer_stats) == 1
        assert summary.layer_stats[0].polygon_count == 2
        assert summary.total_polygons == 2

    def test_custom_layer_map(self, custom_layer_gds: Path) -> None:
        """自定义层映射（layer 100 -> CUSTOM）。"""
        custom_map = {(100, 0): "CUSTOM"}
        summary = compute_layer_stats(custom_layer_gds, layer_map=custom_map)
        assert len(summary.layer_stats) == 1
        assert summary.layer_stats[0].layer_name == "CUSTOM"

    def test_unknown_layer_default_name(self, custom_layer_gds: Path) -> None:
        """未知层使用默认名 LAYER_{layer}_{datatype}。"""
        summary = compute_layer_stats(custom_layer_gds)
        assert len(summary.layer_stats) == 1
        assert summary.layer_stats[0].layer_name == "LAYER_100_0"

    def test_overall_bbox(self, multi_layer_gds: Path) -> None:
        """整体包围盒正确（含所有层）。"""
        summary = compute_layer_stats(multi_layer_gds)
        x_min, y_min, x_max, y_max = summary.overall_bbox
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(10.0, abs=1e-3)
        assert y_max == pytest.approx(2.0, abs=1e-3)

    def test_total_area_aggregation(self, multi_layer_gds: Path) -> None:
        """总面积聚合正确（WG 5μm² + METAL 10μm² = 15μm²）。"""
        summary = compute_layer_stats(multi_layer_gds)
        assert summary.total_area_um2 == pytest.approx(15.0, rel=1e-3)

    def test_top_cell_name_specified(self, single_layer_gds: Path) -> None:
        """指定 top_cell_name。"""
        summary = compute_layer_stats(single_layer_gds, top_cell_name="TOP")
        assert summary.top_cell_name == "TOP"

    def test_top_cell_name_invalid_raises(self, single_layer_gds: Path) -> None:
        """无效 top_cell_name raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            compute_layer_stats(single_layer_gds, top_cell_name="NONEXISTENT")


# =============================================================================
# TestVisualizeLayersAscii: visualize_layers_ascii 测试
# =============================================================================
class TestVisualizeLayersAscii:
    """visualize_layers_ascii 函数测试。"""

    def test_returns_string(self, single_layer_gds: Path) -> None:
        """返回字符串。"""
        result = visualize_layers_ascii(single_layer_gds, width=20, height=10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_axis_labels(self, single_layer_gds: Path) -> None:
        """含坐标轴标签。"""
        result = visualize_layers_ascii(single_layer_gds, width=20, height=10)
        assert "μm" in result
        assert "x:" in result
        assert "y:" in result

    def test_has_canvas_size_label(self, single_layer_gds: Path) -> None:
        """含画布尺寸标签。"""
        result = visualize_layers_ascii(single_layer_gds, width=30, height=15)
        assert "画布" in result
        assert "30x15" in result

    def test_has_legend(self, multi_layer_gds: Path) -> None:
        """含图例。"""
        result = visualize_layers_ascii(multi_layer_gds, width=20, height=10)
        assert "图例" in result
        assert "WG" in result
        assert "METAL" in result

    def test_wg_layer_uses_hash_char(self, single_layer_gds: Path) -> None:
        """WG 层用 # 字符填充。"""
        result = visualize_layers_ascii(single_layer_gds, width=30, height=10)
        assert "#" in result

    def test_metal_layer_uses_m_char(self, multi_layer_gds: Path) -> None:
        """METAL 层用 M 字符填充。"""
        result = visualize_layers_ascii(multi_layer_gds, width=30, height=10)
        assert "M" in result

    def test_custom_dimensions(self, single_layer_gds: Path) -> None:
        """自定义画布尺寸。"""
        result = visualize_layers_ascii(
            single_layer_gds, width=40, height=20
        )
        lines = result.split("\n")
        # 第 1 行: 坐标轴标签
        # 第 2 行: 画布尺寸
        # 第 3..22 行: 画布（20 行）
        # 第 23 行: 图例
        # 总行数 = 2 + 20 + 1 = 23
        assert len(lines) == 23

    def test_layers_to_show_filter(self, multi_layer_gds: Path) -> None:
        """layers_to_show 过滤层。"""
        result = visualize_layers_ascii(
            multi_layer_gds, width=30, height=10, layers_to_show=["WG"]
        )
        assert "WG" in result
        # 仅显示 WG 层，图例不应含 METAL
        assert "METAL" not in result

    def test_invalid_width_raises(self, single_layer_gds: Path) -> None:
        """无效 width raise ValueError。"""
        with pytest.raises(ValueError, match="width"):
            visualize_layers_ascii(single_layer_gds, width=0, height=10)

    def test_invalid_height_raises(self, single_layer_gds: Path) -> None:
        """无效 height raise ValueError。"""
        with pytest.raises(ValueError, match="height"):
            visualize_layers_ascii(single_layer_gds, width=20, height=-1)


# =============================================================================
# TestGenerateSummaryReport: generate_summary_report 测试
# =============================================================================
class TestGenerateSummaryReport:
    """generate_summary_report 函数测试。"""

    def test_text_format(self, single_layer_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_summary_report(single_layer_gds, output_format="text")
        assert isinstance(report, str)
        assert "GDSII 层结构摘要" in report
        assert "文件:" in report
        assert "顶层 cell:" in report
        assert "dbu:" in report
        assert "多边形总数:" in report
        assert "总面积:" in report
        assert "整体包围盒:" in report
        assert "各层详情:" in report

    def test_markdown_format(self, single_layer_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_summary_report(single_layer_gds, output_format="markdown")
        assert isinstance(report, str)
        assert "# GDSII 层结构摘要" in report
        assert "**文件**" in report
        assert "**顶层 cell**" in report
        assert "**dbu**" in report
        assert "**多边形总数**" in report
        assert "**总面积**" in report
        assert "**整体包围盒**" in report
        assert "## 各层详情" in report
        assert "| 层名 |" in report

    def test_format_case_insensitive(self, single_layer_gds: Path) -> None:
        """格式大小写不敏感。"""
        report_upper = generate_summary_report(
            single_layer_gds, output_format="TEXT"
        )
        report_lower = generate_summary_report(
            single_layer_gds, output_format="text"
        )
        assert report_upper == report_lower

    def test_invalid_format_raises(self, single_layer_gds: Path) -> None:
        """无效格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_summary_report(single_layer_gds, output_format="json")

    def test_text_report_has_layer_details(self, multi_layer_gds: Path) -> None:
        """text 报告含各层详情。"""
        report = generate_summary_report(multi_layer_gds, output_format="text")
        assert "WG" in report
        assert "METAL" in report
        assert "多边形数" in report
        assert "面积" in report
        assert "包围盒" in report

    def test_markdown_report_has_table_rows(self, multi_layer_gds: Path) -> None:
        """markdown 报告含表格行。"""
        report = generate_summary_report(multi_layer_gds, output_format="markdown")
        lines = report.split("\n")
        # 找到表格数据行（以 | 开头且非表头/分隔行）
        table_rows = [
            line for line in lines
            if line.startswith("| ")
            and "层名" not in line
            and "------" not in line
        ]
        assert len(table_rows) == 2  # WG + METAL

    def test_report_with_custom_layer_map(
        self, custom_layer_gds: Path
    ) -> None:
        """自定义层映射报告。"""
        custom_map = {(100, 0): "CUSTOM"}
        report = generate_summary_report(
            custom_layer_gds, layer_map=custom_map, output_format="text"
        )
        assert "CUSTOM" in report


# =============================================================================
# TestFillPolygon: _fill_polygon 内部函数测试
# =============================================================================
class TestFillPolygon:
    """_fill_polygon 扫描线填充算法测试。"""

    def test_fill_rectangle(self) -> None:
        """填充矩形（标准扫描线算法：[y_min, y_max) 半开区间）。"""
        canvas: list[list[str]] = [[" "] * 10 for _ in range(5)]
        # 矩形 (row 1, col 1) - (row 3, col 8)
        pts = [(1, 1), (1, 8), (3, 8), (3, 1)]
        _fill_polygon(canvas, pts, "#")
        # 标准扫描线算法：y_max 边界不填充（避免相邻多边形双重填充）
        # 来源: https://en.wikipedia.org/wiki/Scanline_fill
        # row 1, 2 被填充，row 3 (y_max) 不填充
        for row in range(1, 3):
            for col in range(1, 9):
                assert canvas[row][col] == "#"
        # row 0 和 row 4 不填充
        assert all(c == " " for c in canvas[0])
        assert all(c == " " for c in canvas[4])

    def test_fill_triangle(self) -> None:
        """填充三角形。"""
        canvas: list[list[str]] = [[" "] * 10 for _ in range(5)]
        # 三角形 (0,4) - (4,0) - (4,8)
        pts = [(0, 4), (4, 0), (4, 8)]
        _fill_polygon(canvas, pts, "T")
        # 三角形至少应有部分填充
        filled_count = sum(row.count("T") for row in canvas)
        assert filled_count > 0

    def test_fill_degenerate_no_op(self) -> None:
        """退化多边形（<3 顶点）不填充。"""
        canvas: list[list[str]] = [[" "] * 5 for _ in range(5)]
        _fill_polygon(canvas, [(1, 1), (2, 2)], "X")
        for row in canvas:
            for c in row:
                assert c == " "

    def test_fill_empty_canvas(self) -> None:
        """空画布不报错。"""
        canvas: list[list[str]] = []
        _fill_polygon(canvas, [(0, 0), (1, 1), (2, 0)], "X")
        # 不应 raise

    def test_fill_zero_width_canvas(self) -> None:
        """零宽画布不报错。"""
        canvas: list[list[str]] = [[]]
        _fill_polygon(canvas, [(0, 0), (1, 1), (2, 0)], "X")
        # 不应 raise

    def test_fill_out_of_bounds_clamped(self) -> None:
        """超出画布范围被裁剪。"""
        canvas: list[list[str]] = [[" "] * 5 for _ in range(5)]
        # 顶点超出 5x5 画布
        pts = [(-2, -2), (-2, 8), (8, 8), (8, -2)]
        _fill_polygon(canvas, pts, "#")
        # 不应 raise，部分填充在画布内
        filled_count = sum(row.count("#") for row in canvas)
        assert filled_count > 0


# =============================================================================
# TestR03ErrorHandling: R03 禁止 fall-back 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_compute_layer_stats_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            compute_layer_stats(tmp_path / "nonexistent.gds")

    def test_compute_layer_stats_path_is_directory(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            compute_layer_stats(tmp_path)

    def test_visualize_ascii_file_not_found(self, tmp_path: Path) -> None:
        """可视化文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            visualize_layers_ascii(tmp_path / "nonexistent.gds")

    def test_generate_report_file_not_found(self, tmp_path: Path) -> None:
        """报告生成文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            generate_summary_report(tmp_path / "nonexistent.gds")

    def test_invalid_top_cell_name_raises_value_error(
        self, single_layer_gds: Path
    ) -> None:
        """无效 top_cell_name raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            visualize_layers_ascii(
                single_layer_gds, top_cell_name="NONEXISTENT"
            )


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL。"""
        from polaris.verification import gdsii_layer_visualizer as mod
        doc = mod.__doc__ or ""
        assert "https://www.klayout.org/" in doc
        assert "https://github.com/SiEPIC/SiEPIC_EBeam_PDK" in doc
        assert "https://en.wikipedia.org/wiki/ASCII_art" in doc

    def test_module_docstring_has_klayout_reference(self) -> None:
        """模块 docstring 含 KLayout API 引用。"""
        from polaris.verification import gdsii_layer_visualizer as mod
        doc = mod.__doc__ or ""
        assert "KLayout Layout.read" in doc
        assert "KLayout Region" in doc
        assert "KLayout Cell.begin_shapes_rec" in doc

    def test_function_docstrings_have_sources(self) -> None:
        """关键函数 docstring 含来源。"""
        from polaris.verification import gdsii_layer_visualizer as mod
        # compute_layer_stats docstring
        assert "KLayout Layout.read" in mod.compute_layer_stats.__doc__
        assert "KLayout Region.area" in mod.compute_layer_stats.__doc__
        # visualize_layers_ascii docstring
        assert "ASCII art" in mod.visualize_layers_ascii.__doc__
        # _fill_polygon docstring
        assert "扫描线填充" in mod._fill_polygon.__doc__

    def test_dataclass_fields_documented(self) -> None:
        """数据类字段有文档。"""
        from polaris.verification import gdsii_layer_visualizer as mod
        assert mod.LayerStats.__doc__ is not None
        assert "layer_name" in mod.LayerStats.__doc__
        assert "polygon_count" in mod.LayerStats.__doc__
        assert "total_area_um2" in mod.LayerStats.__doc__
        assert mod.GDSIISummary.__doc__ is not None
        assert "file_path" in mod.GDSIISummary.__doc__
        assert "layer_stats" in mod.GDSIISummary.__doc__
        assert "overall_bbox" in mod.GDSIISummary.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_compute_then_visualize(self, multi_layer_gds: Path) -> None:
        """先 compute_layer_stats 再 visualize_layers_ascii。"""
        summary = compute_layer_stats(multi_layer_gds)
        assert summary.total_polygons == 2
        ascii_art = visualize_layers_ascii(
            multi_layer_gds, width=30, height=15
        )
        assert "WG" in ascii_art
        assert "METAL" in ascii_art

    def test_compute_then_report(self, multi_layer_gds: Path) -> None:
        """先 compute_layer_stats 再 generate_summary_report。"""
        summary = compute_layer_stats(multi_layer_gds)
        report = generate_summary_report(multi_layer_gds, output_format="markdown")
        # 报告应反映摘要信息
        assert str(summary.total_polygons) in report
        for s in summary.layer_stats:
            assert s.layer_name in report

    def test_full_pipeline_text_markdown(
        self, multi_polygon_gds: Path
    ) -> None:
        """完整流水线：统计 -> text/markdown 报告 -> ASCII。"""
        summary = compute_layer_stats(multi_polygon_gds)
        text_report = generate_summary_report(
            multi_polygon_gds, output_format="text"
        )
        md_report = generate_summary_report(
            multi_polygon_gds, output_format="markdown"
        )
        ascii_art = visualize_layers_ascii(
            multi_polygon_gds, width=40, height=20
        )
        # 所有产物应反映 2 个多边形
        assert summary.total_polygons == 2
        assert "2" in text_report
        assert "2" in md_report
        assert "#" in ascii_art  # WG 层用 #

    def test_custom_layer_full_pipeline(self, custom_layer_gds: Path) -> None:
        """自定义层完整流水线。"""
        custom_map = {(100, 0): "CUSTOM"}
        summary = compute_layer_stats(
            custom_layer_gds, layer_map=custom_map
        )
        report = generate_summary_report(
            custom_layer_gds, layer_map=custom_map, output_format="text"
        )
        assert summary.layer_stats[0].layer_name == "CUSTOM"
        assert "CUSTOM" in report


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类基础测试。"""

    def test_layer_stats_default_values(self) -> None:
        """LayerStats 默认值。"""
        stats = LayerStats(
            layer_name="WG", gds_layer=1, gds_datatype=0
        )
        assert stats.polygon_count == 0
        assert stats.total_area_um2 == 0.0
        assert stats.bbox_xmin == 0.0
        assert stats.bbox_ymin == 0.0
        assert stats.bbox_xmax == 0.0
        assert stats.bbox_ymax == 0.0

    def test_gdsii_summary_default_values(self) -> None:
        """GDSIISummary 默认值。"""
        summary = GDSIISummary(file_path="test.gds")
        assert summary.top_cell_name == ""
        assert summary.dbu == 0.0
        assert summary.layer_stats == []
        assert summary.total_polygons == 0
        assert summary.total_area_um2 == 0.0
        assert summary.overall_bbox == (0.0, 0.0, 0.0, 0.0)

    def test_layer_stats_immutable_fields(self) -> None:
        """LayerStats 可变字段可更新。"""
        stats = LayerStats(
            layer_name="WG", gds_layer=1, gds_datatype=0
        )
        stats.polygon_count = 5
        stats.total_area_um2 = 12.5
        assert stats.polygon_count == 5
        assert stats.total_area_um2 == 12.5

    def test_all_exports_exist(self) -> None:
        """__all__ 中所有导出符号存在。"""
        from polaris.verification import gdsii_layer_visualizer as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"导出符号 {name} 不存在"
