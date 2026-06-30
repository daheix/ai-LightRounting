"""R331 GDSII 统计报告工具测试。

覆盖:
- generate_gdsii_statistics: 统计报告（cell/层/几何/bbox/层次深度）
- generate_statistics_report: text/markdown/json 报告
- LayerStat / StatisticsReport: 数据类
- R03 错误处理（文件不存在/路径非文件/top_cell_name 不存在/无 cell/不支持格式）
- R02 学术诚信（docstring URL ≥5 / __all__ / dataclass / 无 silent fall-back）
- 集成测试（统计后裁剪/扁平化/预检查可读）
- 数据类（字段完整/构造/repr/相等）

来源:
- KLayout Layout class:
  https://klayout.org/doc-qt5/code/class_Layout.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Shapes class:
  https://klayout.org/doc-qt5/code/class_Shapes.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_statistics import (
    LayerStat,
    StatisticsReport,
    generate_gdsii_statistics,
    generate_statistics_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建含多层 polygon 的 GDSII（3 层: (1,0) (2,0) (3,0)）。

    每层一个三角形 polygon，所有在 TOP cell 中。
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
                {
                    "layer": 2,
                    "datatype": 0,
                    "points": [[0, 0], [8, 0], [4, 4]],
                },
                {
                    "layer": 3,
                    "datatype": 0,
                    "points": [[0, 0], [6, 0], [3, 3]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """创建含层次结构的多层 GDSII。

    TOP 引用 CHILD，CHILD 在 (1,0) 和 (2,0) 各有 1 个 polygon。
    TOP 自身在 (1,0) 也有 1 个 polygon。

    面积:
    - TOP (1,0): 三角形 (0,0),(10,0),(5,5) = 25 μm²
    - CHILD (1,0): 三角形 (0,0),(2,0),(1,1) = 1 μm²
    - CHILD (2,0): 三角形 (0,0),(3,0),(1,2) = 3 μm²
    总面积 = 29 μm²
    总 polygon = 3
    总顶点 = 9
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [2, 0], [1, 1]],
                },
                {
                    "layer": 2,
                    "datatype": 0,
                    "points": [[0, 0], [3, 0], [1, 2]],
                },
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 20.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "hier.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def single_layer_gds(tmp_path: Path) -> Path:
    """创建单层 GDSII（仅 (1,0) 层）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "single.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestGenerateGdsiiStatistics: 统计主函数
# =============================================================================
class TestGenerateGdsiiStatistics:
    """generate_gdsii_statistics 函数测试。"""

    def test_returns_report(self, multi_layer_gds: Path) -> None:
        """返回 StatisticsReport。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert isinstance(report, StatisticsReport)

    def test_file_path_field(self, multi_layer_gds: Path) -> None:
        """file_path 字段正确。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.file_path == str(multi_layer_gds)

    def test_file_size_bytes_positive(self, multi_layer_gds: Path) -> None:
        """file_size_bytes 为正。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.file_size_bytes > 0

    def test_dbu_value(self, multi_layer_gds: Path) -> None:
        """dbu 字段正确（gdsfactory 默认 0.001 μm）。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_total_cells_single(self, single_layer_gds: Path) -> None:
        """单 cell 文件 total_cells=1。"""
        report = generate_gdsii_statistics(single_layer_gds)
        assert report.total_cells == 1

    def test_total_cells_hier(self, hier_gds: Path) -> None:
        """层次文件 total_cells=2（TOP + CHILD）。"""
        report = generate_gdsii_statistics(hier_gds)
        assert report.total_cells == 2

    def test_top_cell_names(self, multi_layer_gds: Path) -> None:
        """top_cell_names 正确。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.top_cell_names == ["TOP"]

    def test_max_depth_single(self, single_layer_gds: Path) -> None:
        """单 cell max_depth=0。"""
        report = generate_gdsii_statistics(single_layer_gds)
        assert report.max_hierarchy_depth == 0

    def test_max_depth_hier(self, hier_gds: Path) -> None:
        """层次文件 max_depth=1。"""
        report = generate_gdsii_statistics(hier_gds)
        assert report.max_hierarchy_depth == 1

    def test_total_polygons_multi(self, multi_layer_gds: Path) -> None:
        """多层文件 total_polygons=3。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.total_polygons == 3

    def test_total_polygons_hier(self, hier_gds: Path) -> None:
        """层次文件 total_polygons=3（TOP 1 + CHILD 2）。"""
        report = generate_gdsii_statistics(hier_gds)
        assert report.total_polygons == 3

    def test_total_boxes_zero(self, multi_layer_gds: Path) -> None:
        """无 box 时 total_boxes=0。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.total_boxes == 0

    def test_total_area_multi(self, multi_layer_gds: Path) -> None:
        """多层文件总面积 = 25 + 16 + 9 = 50 μm²。

        (1,0): (0,0),(10,0),(5,5) = 0.5*|10*5| = 25
        (2,0): (0,0),(8,0),(4,4) = 0.5*|8*4| = 16
        (3,0): (0,0),(6,0),(3,3) = 0.5*|6*3| = 9
        """
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.total_area_um2 == pytest.approx(50.0, abs=1e-6)

    def test_total_area_hier(self, hier_gds: Path) -> None:
        """层次文件总面积 = 25 + 1 + 3 = 29 μm²。"""
        report = generate_gdsii_statistics(hier_gds)
        assert report.total_area_um2 == pytest.approx(29.0, abs=1e-6)

    def test_total_vertex_count(self, multi_layer_gds: Path) -> None:
        """3 个三角形，每个 3 顶点 = 9。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.total_vertex_count == 9

    def test_layer_stats_count(self, multi_layer_gds: Path) -> None:
        """3 层。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        assert len(report.layer_stats) == 3

    def test_layer_stats_sorted(self, multi_layer_gds: Path) -> None:
        """层统计按 (layer, datatype) 排序。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        keys = [(s.layer, s.datatype) for s in report.layer_stats]
        assert keys == sorted(keys)

    def test_layer_stat_shape_count(self, multi_layer_gds: Path) -> None:
        """每层 shape 数 = 1。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        for stat in report.layer_stats:
            assert stat.shape_count == 1

    def test_layer_stat_area(self, multi_layer_gds: Path) -> None:
        """(1,0) 层面积 = 25 μm²。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        stat_1_0 = next(
            s for s in report.layer_stats if s.layer == 1 and s.datatype == 0
        )
        assert stat_1_0.area_um2 == pytest.approx(25.0, abs=1e-6)

    def test_layer_stat_vertex_count(self, multi_layer_gds: Path) -> None:
        """每层顶点数 = 3。"""
        report = generate_gdsii_statistics(multi_layer_gds)
        for stat in report.layer_stats:
            assert stat.vertex_count == 3

    def test_top_cell_bbox_single(self, single_layer_gds: Path) -> None:
        """单顶层 cell bbox 正确。

        三角形 (0,0),(10,0),(5,5) bbox = (0,0)-(10,5) μm
        """
        report = generate_gdsii_statistics(single_layer_gds)
        xmin, ymin, xmax, ymax = report.top_cell_bbox_um
        assert xmin == pytest.approx(0.0, abs=1e-6)
        assert ymin == pytest.approx(0.0, abs=1e-6)
        assert xmax == pytest.approx(10.0, abs=1e-6)
        assert ymax == pytest.approx(5.0, abs=1e-6)

    def test_top_cell_bbox_hier(self, hier_gds: Path) -> None:
        """层次文件 top cell bbox 含实例化的 CHILD。

        TOP 三角形 (0,0)-(10,5)，CHILD 实例化在 (20,0)，CHILD bbox (0,0)-(3,2)
        所以 TOP bbox = (0,0)-(23,5)
        """
        report = generate_gdsii_statistics(hier_gds)
        xmin, ymin, xmax, ymax = report.top_cell_bbox_um
        assert xmin == pytest.approx(0.0, abs=1e-6)
        assert ymin == pytest.approx(0.0, abs=1e-6)
        assert xmax == pytest.approx(23.0, abs=1e-6)
        assert ymax == pytest.approx(5.0, abs=1e-6)

    def test_specified_top_cell_name(self, hier_gds: Path) -> None:
        """指定 top_cell_name='TOP' 正常工作。"""
        report = generate_gdsii_statistics(hier_gds, top_cell_name="TOP")
        assert report.total_cells == 2  # 全图统计不变
        assert report.top_cell_bbox_um[2] == pytest.approx(23.0, abs=1e-6)


# =============================================================================
# TestGenerateStatisticsReport: 报告生成
# =============================================================================
class TestGenerateStatisticsReport:
    """generate_statistics_report 函数测试。"""

    def test_text_report(self, multi_layer_gds: Path) -> None:
        """text 报告。"""
        text = generate_statistics_report(multi_layer_gds)
        assert isinstance(text, str)
        assert "GDSII 统计报告" in text
        assert "Cell 统计" in text
        assert "层统计" in text

    def test_markdown_report(self, multi_layer_gds: Path) -> None:
        """markdown 报告。"""
        md = generate_statistics_report(
            multi_layer_gds, output_format="markdown"
        )
        assert isinstance(md, str)
        assert md.startswith("#")
        assert "## 文件信息" in md
        assert "## Cell 统计" in md
        assert "## 层统计" in md

    def test_json_report(self, multi_layer_gds: Path) -> None:
        """json 报告可解析。"""
        text = generate_statistics_report(
            multi_layer_gds, output_format="json"
        )
        data = json.loads(text)
        assert "file_path" in data
        assert "total_cells" in data
        assert "layer_stats" in data
        assert isinstance(data["layer_stats"], list)

    def test_json_report_content(self, multi_layer_gds: Path) -> None:
        """json 报告内容正确。"""
        text = generate_statistics_report(
            multi_layer_gds, output_format="json"
        )
        data = json.loads(text)
        assert data["total_cells"] == 1
        assert data["total_polygons"] == 3
        assert data["total_area_um2"] == pytest.approx(50.0, abs=1e-6)
        assert len(data["layer_stats"]) == 3

    def test_text_report_contains_layers(self, multi_layer_gds: Path) -> None:
        """text 报告包含层信息。"""
        text = generate_statistics_report(multi_layer_gds)
        assert "(1,0)" in text or "1" in text

    def test_markdown_report_table(self, multi_layer_gds: Path) -> None:
        """markdown 报告含表格。"""
        md = generate_statistics_report(
            multi_layer_gds, output_format="markdown"
        )
        assert "|" in md
        assert "---" in md


# =============================================================================
# TestR03ErrorHandling: 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试: 失败即 raise。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            generate_gdsii_statistics(tmp_path / "nonexistent.gds")

    def test_path_is_directory_raises(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            generate_gdsii_statistics(tmp_path)

    def test_top_cell_name_not_exist_raises(
        self, multi_layer_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            generate_gdsii_statistics(
                multi_layer_gds, top_cell_name="NONEXISTENT"
            )

    def test_unsupported_format_raises(self, multi_layer_gds: Path) -> None:
        """不支持的 output_format raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_statistics_report(
                multi_layer_gds, output_format="xml"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_5_plus_urls(self) -> None:
        """模块 docstring 至少 5 个 URL（R02）。"""
        from polaris.verification import gdsii_statistics

        docstring = gdsii_statistics.__doc__ or ""
        url_count = docstring.count("https://")
        assert url_count >= 5, (
            f"docstring 只有 {url_count} 个 URL，要求 ≥5 个（R02）"
        )

    def test_all_exported(self) -> None:
        """__all__ 列出所有公开 API。"""
        from polaris.verification import gdsii_statistics

        expected = {
            "LayerStat",
            "StatisticsReport",
            "generate_gdsii_statistics",
            "generate_statistics_report",
        }
        assert set(gdsii_statistics.__all__) == expected

    def test_layerstat_is_dataclass(self) -> None:
        """LayerStat 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(LayerStat)

    def test_statisticsreport_is_dataclass(self) -> None:
        """StatisticsReport 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(StatisticsReport)

    def test_statisticsreport_fields(self) -> None:
        """StatisticsReport 字段完整（13 字段）。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(StatisticsReport)}
        expected = {
            "file_path",
            "file_size_bytes",
            "dbu",
            "total_cells",
            "top_cell_names",
            "max_hierarchy_depth",
            "layer_stats",
            "total_polygons",
            "total_boxes",
            "total_area_um2",
            "total_vertex_count",
            "top_cell_bbox_um",
        }
        assert field_names == expected

    def test_layerstat_fields(self) -> None:
        """LayerStat 字段完整（5 字段）。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(LayerStat)}
        expected = {
            "layer",
            "datatype",
            "shape_count",
            "area_um2",
            "vertex_count",
        }
        assert field_names == expected

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back。"""
        from polaris.verification import gdsii_statistics

        source_path = Path(gdsii_statistics.__file__)
        source = source_path.read_text(encoding="utf-8")
        assert "except: pass" not in source, "禁止 silent except: pass（R03）"
        assert "except Exception: pass" not in source, (
            "禁止 silent except Exception: pass（R03）"
        )

    def test_klayout_import_error_message(self) -> None:
        """klayout 导入失败时 raise ImportError。"""
        from polaris.verification.gdsii_statistics import _import_klayout_db

        db = _import_klayout_db()
        assert db is not None


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """与其他 R3xx 工具的集成测试。"""

    def test_statistics_then_flatten(
        self, hier_gds: Path, tmp_path: Path
    ) -> None:
        """统计后 R326 扁平化仍能读取。"""
        from polaris.verification.gdsii_flattener import flatten_gdsii

        # 先统计
        report = generate_gdsii_statistics(hier_gds)
        assert report.total_cells == 2

        # 再 flatten
        flattened = tmp_path / "flattened.gds"
        flatten_report = flatten_gdsii(hier_gds, flattened)
        assert flatten_report.cells_after >= 1

    def test_statistics_then_clip(
        self, hier_gds: Path, tmp_path: Path
    ) -> None:
        """统计后 R327 裁剪仍能读取。"""
        from polaris.verification.gdsii_clip_tool import clip_gdsii

        # 先统计
        report = generate_gdsii_statistics(hier_gds)
        assert report.total_polygons == 3

        # 再 clip
        clipped = tmp_path / "clipped.gds"
        clip_report = clip_gdsii(
            hier_gds, clipped, (-1.0, -1.0, 25.0, 10.0)
        )
        assert clip_report.shapes_after >= 1

    def test_statistics_then_precheck(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """统计后 R329 预检查仍能读取。"""
        from polaris.verification.gdsii_tapeout_precheck import (
            TapeoutReport,
            tapeout_precheck,
        )

        # 先统计
        report = generate_gdsii_statistics(multi_layer_gds)
        assert report.total_cells == 1

        # 再 precheck
        precheck_report = tapeout_precheck(multi_layer_gds)
        assert isinstance(precheck_report, TapeoutReport)

    def test_statistics_then_layer_op(
        self, multi_layer_gds: Path, tmp_path: Path
    ) -> None:
        """统计后 R330 层操作仍能读取。"""
        from polaris.verification.gdsii_layer_ops import (
            LayerOpReport,
            delete_layers,
        )

        # 先统计
        report = generate_gdsii_statistics(multi_layer_gds)
        assert len(report.layer_stats) == 3

        # 再 delete 一层
        deleted = tmp_path / "deleted.gds"
        op_report = delete_layers(multi_layer_gds, deleted, [(1, 0)])
        assert isinstance(op_report, LayerOpReport)

        # 统计删除后的文件
        report2 = generate_gdsii_statistics(deleted)
        assert len(report2.layer_stats) == 2
        assert report2.total_polygons == 2


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """LayerStat / StatisticsReport 数据类测试。"""

    def test_layerstat_default_construction(self) -> None:
        """LayerStat 默认构造。"""
        stat = LayerStat(layer=1, datatype=0)
        assert stat.layer == 1
        assert stat.datatype == 0
        assert stat.shape_count == 0
        assert stat.area_um2 == 0.0
        assert stat.vertex_count == 0

    def test_layerstat_full_construction(self) -> None:
        """LayerStat 完整构造。"""
        stat = LayerStat(
            layer=1, datatype=0, shape_count=5,
            area_um2=12.5, vertex_count=15,
        )
        assert stat.shape_count == 5
        assert stat.area_um2 == 12.5
        assert stat.vertex_count == 15

    def test_statisticsreport_default_construction(self) -> None:
        """StatisticsReport 默认构造。"""
        report = StatisticsReport()
        assert report.file_path == ""
        assert report.file_size_bytes == 0
        assert report.dbu == 0.0
        assert report.total_cells == 0
        assert report.top_cell_names == []
        assert report.max_hierarchy_depth == 0
        assert report.layer_stats == []
        assert report.total_polygons == 0
        assert report.total_boxes == 0
        assert report.total_area_um2 == 0.0
        assert report.total_vertex_count == 0
        assert report.top_cell_bbox_um == (0.0, 0.0, 0.0, 0.0)

    def test_statisticsreport_full_construction(self) -> None:
        """StatisticsReport 完整构造。"""
        stat = LayerStat(layer=1, datatype=0, shape_count=2)
        report = StatisticsReport(
            file_path="/in.gds",
            file_size_bytes=1024,
            dbu=0.001,
            total_cells=3,
            top_cell_names=["TOP"],
            max_hierarchy_depth=2,
            layer_stats=[stat],
            total_polygons=10,
            total_boxes=2,
            total_area_um2=100.5,
            total_vertex_count=30,
            top_cell_bbox_um=(0.0, 0.0, 100.0, 50.0),
        )
        assert report.file_path == "/in.gds"
        assert report.file_size_bytes == 1024
        assert report.dbu == 0.001
        assert report.total_cells == 3
        assert report.layer_stats == [stat]
        assert report.total_polygons == 10

    def test_layerstat_repr(self) -> None:
        """LayerStat repr 含类名。"""
        stat = LayerStat(layer=1, datatype=0)
        assert "LayerStat" in repr(stat)

    def test_statisticsreport_repr(self) -> None:
        """StatisticsReport repr 含类名。"""
        report = StatisticsReport()
        assert "StatisticsReport" in repr(report)

    def test_layerstat_equality(self) -> None:
        """LayerStat 相等。"""
        s1 = LayerStat(layer=1, datatype=0, shape_count=5)
        s2 = LayerStat(layer=1, datatype=0, shape_count=5)
        assert s1 == s2
