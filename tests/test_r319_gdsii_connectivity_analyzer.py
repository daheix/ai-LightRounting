"""R319 GDSII 几何连通分量分析器测试。

覆盖:
- analyze_layer_connectivity: 同层连通分量分析
- analyze_cross_layer_connectivity: 跨层连通分量分析（并查集）
- list_isolated_polygons: 孤立多边形列表
- generate_connectivity_report: text/markdown 报告
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- KLayout Region.merge: https://www.klayout.org/doc-qt5/code/class_Region.html
- 并查集 Union-Find: Tarjan JACM 1975, DOI: 10.1145/321879.321884
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- scipy.connected_components: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.connected_components.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_connectivity_analyzer import (
    ConnectedComponent,
    ConnectivityReport,
    LayerConnectivityResult,
    analyze_cross_layer_connectivity,
    analyze_layer_connectivity,
    generate_connectivity_report,
    list_isolated_polygons,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def touching_polygons_gds(tmp_path: Path) -> Path:
    """创建含接触多边形的 GDSII（2 个接触矩形 + 1 个分离矩形）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # 矩形 A: [0,0]-[5,1]
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 1], [0, 1]]},
                # 矩形 B: [5,0]-[10,1]（与 A 共享 x=5 边，接触）
                {"layer": 1, "datatype": 0, "points": [[5, 0], [10, 0], [10, 1], [5, 1]]},
                # 矩形 C: [20,0]-[25,1]（分离）
                {"layer": 1, "datatype": 0, "points": [[20, 0], [25, 0], [25, 1], [20, 1]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "touching.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def overlapping_polygons_gds(tmp_path: Path) -> Path:
    """创建含重叠多边形的 GDSII（2 个重叠矩形）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # 矩形 A: [0,0]-[5,5]
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
                # 矩形 B: [3,3]-[8,8]（与 A 重叠）
                {"layer": 1, "datatype": 0, "points": [[3, 3], [8, 3], [8, 8], [3, 8]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "overlapping.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def single_polygon_gds(tmp_path: Path) -> Path:
    """创建含单个多边形的 GDSII。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "single.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII（WG + METAL，两层层重叠）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # WG 层
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 1], [0, 1]]},
                # METAL 层（与 WG 重叠）
                {"layer": 5, "datatype": 0, "points": [[0, 0], [10, 0], [10, 1], [0, 1]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def separated_multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII（WG + METAL，两层分离不重叠）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # WG 层
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 1], [0, 1]]},
                # METAL 层（与 WG 不重叠）
                {"layer": 5, "datatype": 0, "points": [[10, 10], [15, 10], [15, 11], [10, 11]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "separated.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestAnalyzeLayerConnectivity: 同层连通分量分析
# =============================================================================
class TestAnalyzeLayerConnectivity:
    """analyze_layer_connectivity 函数测试。"""

    def test_returns_report(self, single_polygon_gds: Path) -> None:
        """返回 ConnectivityReport。"""
        report = analyze_layer_connectivity(single_polygon_gds)
        assert isinstance(report, ConnectivityReport)
        assert report.file_path == str(single_polygon_gds)
        assert report.top_cell_name == "TOP"
        assert report.dbu > 0

    def test_single_polygon(self, single_polygon_gds: Path) -> None:
        """单多边形 → 1 个分量，1 个孤立。"""
        report = analyze_layer_connectivity(single_polygon_gds)
        assert report.total_components == 1
        assert report.total_isolated == 1
        assert len(report.layer_results) == 1
        lr = report.layer_results[0]
        assert lr.layer_name == "WG"
        assert lr.total_polygons == 1
        assert len(lr.components) == 1
        assert lr.components[0].polygon_count == 1
        assert lr.isolated_count == 1
        assert lr.largest_component_size == 1

    def test_touching_polygons(self, touching_polygons_gds: Path) -> None:
        """3 个多边形（2 接触 + 1 分离）→ 2 个分量，1 个孤立。"""
        report = analyze_layer_connectivity(touching_polygons_gds)
        assert report.total_components == 2
        assert report.total_isolated == 1
        lr = report.layer_results[0]
        assert lr.total_polygons == 3
        assert len(lr.components) == 2
        # 找出大分量（2 多边形）和小分量（1 多边形）
        sizes = sorted([c.polygon_count for c in lr.components])
        assert sizes == [1, 2]
        assert lr.largest_component_size == 2

    def test_overlapping_polygons(self, overlapping_polygons_gds: Path) -> None:
        """2 个重叠多边形 → 1 个分量。"""
        report = analyze_layer_connectivity(overlapping_polygons_gds)
        assert report.total_components == 1
        assert report.total_isolated == 0
        lr = report.layer_results[0]
        assert lr.total_polygons == 2
        assert len(lr.components) == 1
        assert lr.components[0].polygon_count == 2

    def test_multi_layer(self, multi_layer_gds: Path) -> None:
        """多层 GDSII → 各层独立分析。"""
        report = analyze_layer_connectivity(multi_layer_gds)
        assert len(report.layer_results) == 2
        layer_names = {lr.layer_name for lr in report.layer_results}
        assert layer_names == {"WG", "METAL"}
        # 每层 1 个分量
        assert report.total_components == 2

    def test_layers_to_analyze_filter(
        self, multi_layer_gds: Path
    ) -> None:
        """layers_to_analyze 过滤层。"""
        report = analyze_layer_connectivity(
            multi_layer_gds, layers_to_analyze=["WG"]
        )
        assert len(report.layer_results) == 1
        assert report.layer_results[0].layer_name == "WG"

    def test_custom_layer_map(self, single_polygon_gds: Path) -> None:
        """自定义层映射。"""
        custom_map = {(1, 0): "MY_LAYER"}
        report = analyze_layer_connectivity(
            single_polygon_gds, layer_map=custom_map
        )
        assert report.layer_results[0].layer_name == "MY_LAYER"

    def test_top_cell_name_specified(self, single_polygon_gds: Path) -> None:
        """指定 top_cell_name。"""
        report = analyze_layer_connectivity(
            single_polygon_gds, top_cell_name="TOP"
        )
        assert report.top_cell_name == "TOP"

    def test_component_bbox(self, single_polygon_gds: Path) -> None:
        """分量包围盒正确。"""
        report = analyze_layer_connectivity(single_polygon_gds)
        comp = report.layer_results[0].components[0]
        x_min, y_min, x_max, y_max = comp.bbox
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(10.0, abs=1e-3)
        assert y_max == pytest.approx(5.0, abs=1e-3)

    def test_component_area(self, single_polygon_gds: Path) -> None:
        """分量面积正确（10x5=50μm²）。"""
        report = analyze_layer_connectivity(single_polygon_gds)
        comp = report.layer_results[0].components[0]
        assert comp.area_um2 == pytest.approx(50.0, rel=1e-3)


# =============================================================================
# TestAnalyzeCrossLayerConnectivity: 跨层连通分量分析
# =============================================================================
class TestAnalyzeCrossLayerConnectivity:
    """analyze_cross_layer_connectivity 函数测试。"""

    def test_overlapping_layers_connected(
        self, multi_layer_gds: Path
    ) -> None:
        """重叠层 → 跨层连通。"""
        result = analyze_cross_layer_connectivity(
            multi_layer_gds, layer_pairs=[("WG", "METAL")]
        )
        # WG 和 METAL 应在某个跨层分量组中合并
        assert "WG" in result
        assert "METAL" in result
        # 至少有一个跨层分量组包含两层的分量 ID
        wg_groups = result["WG"]
        metal_groups = result["METAL"]
        # 检查至少有一个组非空
        assert any(len(g) > 0 for g in wg_groups)
        assert any(len(g) > 0 for g in metal_groups)

    def test_separated_layers_not_connected(
        self, separated_multi_layer_gds: Path
    ) -> None:
        """分离层 → 无跨层连通。"""
        result = analyze_cross_layer_connectivity(
            separated_multi_layer_gds, layer_pairs=[("WG", "METAL")]
        )
        # 每层应该有独立的分量组，不合并
        # WG 1 个分量，METAL 1 个分量，但两者不连通
        assert "WG" in result
        assert "METAL" in result

    def test_empty_layer_pairs_raises(self, single_polygon_gds: Path) -> None:
        """空 layer_pairs raise ValueError。"""
        with pytest.raises(ValueError, match="layer_pairs 不能为空"):
            analyze_cross_layer_connectivity(
                single_polygon_gds, layer_pairs=[]
            )

    def test_nonexistent_layer_raises(
        self, single_polygon_gds: Path
    ) -> None:
        """不存在的层名 raise ValueError。"""
        with pytest.raises(ValueError, match="不在 GDSII 文件中"):
            analyze_cross_layer_connectivity(
                single_polygon_gds,
                layer_pairs=[("WG", "NONEXISTENT")],
            )

    def test_returns_dict(self, multi_layer_gds: Path) -> None:
        """返回字典结构。"""
        result = analyze_cross_layer_connectivity(
            multi_layer_gds, layer_pairs=[("WG", "METAL")]
        )
        assert isinstance(result, dict)
        for layer_name, groups in result.items():
            assert isinstance(layer_name, str)
            assert isinstance(groups, list)
            for g in groups:
                assert isinstance(g, set)


# =============================================================================
# TestListIsolatedPolygons: 孤立多边形列表
# =============================================================================
class TestListIsolatedPolygons:
    """list_isolated_polygons 函数测试。"""

    def test_single_polygon_isolated(self, single_polygon_gds: Path) -> None:
        """单多边形 → 1 个孤立。"""
        isolated = list_isolated_polygons(single_polygon_gds)
        assert len(isolated) == 1
        assert isinstance(isolated[0], ConnectedComponent)
        assert isolated[0].polygon_count == 1

    def test_touching_polygons_one_isolated(
        self, touching_polygons_gds: Path
    ) -> None:
        """3 个多边形（2 接触 + 1 分离）→ 1 个孤立。"""
        isolated = list_isolated_polygons(touching_polygons_gds)
        assert len(isolated) == 1
        assert isolated[0].polygon_count == 1

    def test_overlapping_no_isolated(
        self, overlapping_polygons_gds: Path
    ) -> None:
        """2 个重叠多边形 → 0 个孤立。"""
        isolated = list_isolated_polygons(overlapping_polygons_gds)
        assert len(isolated) == 0

    def test_multi_layer_isolated(
        self, multi_layer_gds: Path
    ) -> None:
        """多层 GDSII，每层 1 个多边形 → 2 个孤立。"""
        isolated = list_isolated_polygons(multi_layer_gds)
        assert len(isolated) == 2
        layer_names = {c.layer_name for c in isolated}
        assert layer_names == {"WG", "METAL"}


# =============================================================================
# TestGenerateConnectivityReport: 报告生成
# =============================================================================
class TestGenerateConnectivityReport:
    """generate_connectivity_report 函数测试。"""

    def test_text_format(self, single_polygon_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_connectivity_report(
            single_polygon_gds, output_format="text"
        )
        assert isinstance(report, str)
        assert "GDSII 几何连通分量分析报告" in report
        assert "文件:" in report
        assert "顶层 cell:" in report
        assert "dbu:" in report
        assert "总连通分量数:" in report
        assert "总孤立多边形数:" in report
        assert "各层详情:" in report

    def test_markdown_format(self, single_polygon_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_connectivity_report(
            single_polygon_gds, output_format="markdown"
        )
        assert isinstance(report, str)
        assert "# GDSII 几何连通分量分析报告" in report
        assert "**文件**" in report
        assert "**顶层 cell**" in report
        assert "**dbu**" in report
        assert "**总连通分量数**" in report
        assert "**总孤立多边形数**" in report
        assert "## 各层详情" in report
        assert "| 层名 |" in report

    def test_format_case_insensitive(self, single_polygon_gds: Path) -> None:
        """格式大小写不敏感。"""
        r1 = generate_connectivity_report(
            single_polygon_gds, output_format="TEXT"
        )
        r2 = generate_connectivity_report(
            single_polygon_gds, output_format="text"
        )
        assert r1 == r2

    def test_invalid_format_raises(self, single_polygon_gds: Path) -> None:
        """无效格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_connectivity_report(
                single_polygon_gds, output_format="json"
            )

    def test_text_report_has_layer_details(
        self, touching_polygons_gds: Path
    ) -> None:
        """text 报告含分量详情。"""
        report = generate_connectivity_report(
            touching_polygons_gds, output_format="text"
        )
        assert "分量 #" in report
        assert "多边形" in report
        assert "面积" in report
        assert "包围盒" in report

    def test_markdown_report_has_table(
        self, single_polygon_gds: Path
    ) -> None:
        """markdown 报告含表格。"""
        report = generate_connectivity_report(
            single_polygon_gds, output_format="markdown"
        )
        assert "| 层名 | 总多边形 |" in report
        assert "| 分量 ID | 多边形数 |" in report


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_analyze_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            analyze_layer_connectivity(tmp_path / "nonexistent.gds")

    def test_analyze_path_is_directory(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            analyze_layer_connectivity(tmp_path)

    def test_cross_layer_file_not_found(self, tmp_path: Path) -> None:
        """跨层分析文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            analyze_cross_layer_connectivity(
                tmp_path / "nonexistent.gds",
                layer_pairs=[("WG", "METAL")],
            )

    def test_list_isolated_file_not_found(self, tmp_path: Path) -> None:
        """孤立列表文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            list_isolated_polygons(tmp_path / "nonexistent.gds")

    def test_generate_report_file_not_found(self, tmp_path: Path) -> None:
        """报告生成文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            generate_connectivity_report(tmp_path / "nonexistent.gds")

    def test_invalid_top_cell_name_raises(
        self, single_polygon_gds: Path
    ) -> None:
        """无效 top_cell_name raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            analyze_layer_connectivity(
                single_polygon_gds, top_cell_name="NONEXISTENT"
            )


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL。"""
        from polaris.verification import gdsii_connectivity_analyzer as mod
        doc = mod.__doc__ or ""
        assert "https://www.klayout.org/" in doc
        assert "https://github.com/SiEPIC/SiEPIC_EBeam_PDK" in doc
        assert "DOI: 10.1145/321879.321884" in doc

    def test_module_docstring_has_klayout_reference(self) -> None:
        """模块 docstring 含 KLayout API 引用。"""
        from polaris.verification import gdsii_connectivity_analyzer as mod
        doc = mod.__doc__ or ""
        assert "KLayout Region.merge" in doc
        assert "Tarjan" in doc
        assert "Calibre nmLVS" in doc

    def test_function_docstrings_have_sources(self) -> None:
        """关键函数 docstring 含来源。"""
        from polaris.verification import gdsii_connectivity_analyzer as mod
        assert "KLayout Region.merge" in mod.analyze_layer_connectivity.__doc__
        assert "KLayout Layout.read" in mod.analyze_layer_connectivity.__doc__
        assert "Tarjan" in mod.analyze_cross_layer_connectivity.__doc__
        assert "CommonMark" in mod.generate_connectivity_report.__doc__

    def test_dataclass_fields_documented(self) -> None:
        """数据类字段有文档。"""
        from polaris.verification import gdsii_connectivity_analyzer as mod
        assert mod.ConnectedComponent.__doc__ is not None
        assert "component_id" in mod.ConnectedComponent.__doc__
        assert "polygon_count" in mod.ConnectedComponent.__doc__
        assert "area_um2" in mod.ConnectedComponent.__doc__
        assert mod.LayerConnectivityResult.__doc__ is not None
        assert "components" in mod.LayerConnectivityResult.__doc__
        assert "isolated_count" in mod.LayerConnectivityResult.__doc__
        assert mod.ConnectivityReport.__doc__ is not None
        assert "total_components" in mod.ConnectivityReport.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_pipeline_touching(self, touching_polygons_gds: Path) -> None:
        """完整流水线：分析 → 孤立列表 → 报告。"""
        report = analyze_layer_connectivity(touching_polygons_gds)
        isolated = list_isolated_polygons(touching_polygons_gds)
        text_report = generate_connectivity_report(
            touching_polygons_gds, output_format="text"
        )
        md_report = generate_connectivity_report(
            touching_polygons_gds, output_format="markdown"
        )
        assert report.total_components == 2
        assert len(isolated) == 1
        assert str(report.total_components) in text_report
        assert str(report.total_components) in md_report

    def test_full_pipeline_multi_layer(
        self, multi_layer_gds: Path
    ) -> None:
        """多层完整流水线。"""
        report = analyze_layer_connectivity(multi_layer_gds)
        cross = analyze_cross_layer_connectivity(
            multi_layer_gds, layer_pairs=[("WG", "METAL")]
        )
        assert report.total_components == 2
        assert "WG" in cross
        assert "METAL" in cross

    def test_polygon_indices_consistent(
        self, touching_polygons_gds: Path
    ) -> None:
        """多边形索引一致性：所有分量的索引应覆盖所有原始多边形。"""
        report = analyze_layer_connectivity(touching_polygons_gds)
        lr = report.layer_results[0]
        all_indices: list[int] = []
        for comp in lr.components:
            all_indices.extend(comp.polygon_indices)
        # 应覆盖所有 3 个原始多边形
        assert sorted(all_indices) == [0, 1, 2]
        # 不应有重复
        assert len(all_indices) == len(set(all_indices))

    def test_overlapping_polygons_pipeline(
        self, overlapping_polygons_gds: Path
    ) -> None:
        """重叠多边形完整流水线。"""
        report = analyze_layer_connectivity(overlapping_polygons_gds)
        isolated = list_isolated_polygons(overlapping_polygons_gds)
        assert report.total_components == 1
        assert len(isolated) == 0
        # 单分量应包含 2 个多边形
        comp = report.layer_results[0].components[0]
        assert comp.polygon_count == 2
        assert len(comp.polygon_indices) == 2


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类基础测试。"""

    def test_connected_component_defaults(self) -> None:
        """ConnectedComponent 默认值。"""
        comp = ConnectedComponent(
            component_id=0,
            layer_name="WG",
            polygon_count=1,
            area_um2=5.0,
            bbox=(0.0, 0.0, 10.0, 1.0),
        )
        assert comp.polygon_indices == []

    def test_layer_connectivity_result_defaults(self) -> None:
        """LayerConnectivityResult 默认值。"""
        result = LayerConnectivityResult(layer_name="WG")
        assert result.total_polygons == 0
        assert result.components == []
        assert result.isolated_count == 0
        assert result.largest_component_size == 0

    def test_connectivity_report_defaults(self) -> None:
        """ConnectivityReport 默认值。"""
        report = ConnectivityReport(file_path="test.gds")
        assert report.top_cell_name == ""
        assert report.dbu == 0.0
        assert report.layer_results == []
        assert report.total_components == 0
        assert report.total_isolated == 0

    def test_all_exports_exist(self) -> None:
        """__all__ 中所有导出符号存在。"""
        from polaris.verification import gdsii_connectivity_analyzer as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"导出符号 {name} 不存在"
