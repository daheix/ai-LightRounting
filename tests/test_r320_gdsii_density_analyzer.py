"""R320 GDSII 层密度分析器测试。

覆盖:
- compute_layer_density: 全局密度计算
- compute_density_map: 密度网格图
- check_density_rules: 密度规则检查（min/max）
- generate_density_report: text/markdown 报告
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- KLayout Region.area: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout DRC density: https://www.klayout.org/doc-qt5/manual/drc.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_density_analyzer import (
    DensityMap,
    DensityReport,
    DensityViolation,
    LayerDensity,
    check_density_rules,
    compute_density_map,
    compute_layer_density,
    generate_density_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def full_density_gds(tmp_path: Path) -> Path:
    """创建密度 1.0 的 GDSII（单矩形填满包围盒）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # 10x5 矩形 = 50 μm²，包围盒也是 50 μm²，密度 1.0
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "full.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def half_density_gds(tmp_path: Path) -> Path:
    """创建密度 0.5 的 GDSII（矩形占包围盒一半）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # 10x5 矩形 = 50 μm²
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        },
        # 同层增加一个不影响 bbox 的"空区域"——通过第二个分离多边形扩大 bbox
        # 不好实现，改用另一 fixture
    ]
    out = tmp_path / "half.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def sparse_density_gds(tmp_path: Path) -> Path:
    """创建稀疏密度 GDSII（小矩形在大包围盒中）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # 2x2 矩形 = 4 μm²，但包围盒扩大到 20x10=200 μm²
                # 用两个分离多边形形成大包围盒
                {"layer": 1, "datatype": 0, "points": [[0, 0], [2, 0], [2, 2], [0, 2]]},
                {"layer": 1, "datatype": 0, "points": [[18, 8], [20, 8], [20, 10], [18, 10]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "sparse.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII（WG + METAL）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
                {"layer": 5, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def custom_layer_gds(tmp_path: Path) -> Path:
    """创建自定义层 GDSII（layer 100）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 100, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "custom.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestComputeLayerDensity: 全局密度计算
# =============================================================================
class TestComputeLayerDensity:
    """compute_layer_density 函数测试。"""

    def test_returns_report(self, full_density_gds: Path) -> None:
        """返回 DensityReport。"""
        report = compute_layer_density(full_density_gds)
        assert isinstance(report, DensityReport)
        assert report.file_path == str(full_density_gds)
        assert report.top_cell_name == "TOP"
        assert report.dbu > 0

    def test_full_density(self, full_density_gds: Path) -> None:
        """密度 1.0（多边形填满包围盒）。"""
        report = compute_layer_density(full_density_gds)
        assert len(report.layer_densities) == 1
        ld = report.layer_densities[0]
        assert ld.layer_name == "WG"
        assert ld.polygon_area_um2 == pytest.approx(50.0, rel=1e-3)
        assert ld.bbox_area_um2 == pytest.approx(50.0, rel=1e-3)
        assert ld.density == pytest.approx(1.0, rel=1e-3)

    def test_sparse_density(self, sparse_density_gds: Path) -> None:
        """稀疏密度（小矩形在大包围盒中）。"""
        report = compute_layer_density(sparse_density_gds)
        assert len(report.layer_densities) == 1
        ld = report.layer_densities[0]
        # 两个 2x2=4μm² 矩形 = 8μm²，bbox 20x10=200μm²，密度 0.04
        assert ld.polygon_area_um2 == pytest.approx(8.0, rel=1e-3)
        assert ld.bbox_area_um2 == pytest.approx(200.0, rel=1e-3)
        assert ld.density == pytest.approx(0.04, abs=1e-3)

    def test_multi_layer(self, multi_layer_gds: Path) -> None:
        """多层密度。"""
        report = compute_layer_density(multi_layer_gds)
        assert len(report.layer_densities) == 2
        layer_names = {ld.layer_name for ld in report.layer_densities}
        assert layer_names == {"WG", "METAL"}
        # 每层密度都是 1.0
        for ld in report.layer_densities:
            assert ld.density == pytest.approx(1.0, rel=1e-3)

    def test_layers_to_analyze_filter(self, multi_layer_gds: Path) -> None:
        """layers_to_analyze 过滤层。"""
        report = compute_layer_density(
            multi_layer_gds, layers_to_analyze=["WG"]
        )
        assert len(report.layer_densities) == 1
        assert report.layer_densities[0].layer_name == "WG"

    def test_custom_layer_map(self, custom_layer_gds: Path) -> None:
        """自定义层映射。"""
        custom_map = {(100, 0): "CUSTOM"}
        report = compute_layer_density(custom_layer_gds, layer_map=custom_map)
        assert len(report.layer_densities) == 1
        assert report.layer_densities[0].layer_name == "CUSTOM"

    def test_overall_bbox(self, multi_layer_gds: Path) -> None:
        """整体包围盒正确。"""
        report = compute_layer_density(multi_layer_gds)
        x_min, y_min, x_max, y_max = report.overall_bbox
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(10.0, abs=1e-3)
        assert y_max == pytest.approx(5.0, abs=1e-3)

    def test_layer_density_bbox(self, full_density_gds: Path) -> None:
        """层密度包围盒正确。"""
        report = compute_layer_density(full_density_gds)
        ld = report.layer_densities[0]
        x_min, y_min, x_max, y_max = ld.bbox
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(10.0, abs=1e-3)
        assert y_max == pytest.approx(5.0, abs=1e-3)

    def test_top_cell_name_specified(self, full_density_gds: Path) -> None:
        """指定 top_cell_name。"""
        report = compute_layer_density(full_density_gds, top_cell_name="TOP")
        assert report.top_cell_name == "TOP"


# =============================================================================
# TestComputeDensityMap: 密度网格图
# =============================================================================
class TestComputeDensityMap:
    """compute_density_map 函数测试。"""

    def test_returns_density_map(self, full_density_gds: Path) -> None:
        """返回 DensityMap。"""
        dmap = compute_density_map(full_density_gds, "WG", cell_size_um=5.0)
        assert isinstance(dmap, DensityMap)
        assert dmap.layer_name == "WG"
        assert dmap.cell_size_um == 5.0

    def test_grid_shape(self, full_density_gds: Path) -> None:
        """网格形状正确（10x5μm，cell_size=5μm → 2x1 网格）。"""
        dmap = compute_density_map(full_density_gds, "WG", cell_size_um=5.0)
        assert dmap.rows == 1
        assert dmap.cols == 2
        assert dmap.grid.shape == (1, 2)

    def test_grid_values_full_density(self, full_density_gds: Path) -> None:
        """网格密度值正确（全填充 → 1.0）。"""
        dmap = compute_density_map(full_density_gds, "WG", cell_size_um=5.0)
        for r in range(dmap.rows):
            for c in range(dmap.cols):
                assert dmap.grid[r, c] == pytest.approx(1.0, abs=1e-3)

    def test_grid_values_sparse(self, sparse_density_gds: Path) -> None:
        """稀疏网格密度值正确。"""
        # 20x10μm，cell_size=5μm → 4x2 网格
        # 多边形在 [0,0]-[2,2] 和 [18,8]-[20,10]
        # 第一个多边形在 (0,0) 网格，面积 4/25=0.16
        # 第二个多边形在 (3,1) 网格，面积 4/25=0.16
        dmap = compute_density_map(
            sparse_density_gds, "WG", cell_size_um=5.0
        )
        assert dmap.rows == 2
        assert dmap.cols == 4
        # (0,0) 网格密度 0.16
        assert dmap.grid[0, 0] == pytest.approx(0.16, abs=0.01)
        # (1,3) 网格密度 0.16
        assert dmap.grid[1, 3] == pytest.approx(0.16, abs=0.01)
        # 其他网格密度 0
        assert dmap.grid[0, 1] == pytest.approx(0.0, abs=1e-3)
        assert dmap.grid[1, 0] == pytest.approx(0.0, abs=1e-3)

    def test_cell_size_too_small_raises(
        self, full_density_gds: Path
    ) -> None:
        """cell_size_um <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="cell_size_um"):
            compute_density_map(full_density_gds, "WG", cell_size_um=0.0)

    def test_nonexistent_layer_raises(
        self, full_density_gds: Path
    ) -> None:
        """不存在的层 raise ValueError。"""
        with pytest.raises(ValueError, match="不在 GDSII 文件中"):
            compute_density_map(full_density_gds, "NONEXISTENT")

    def test_bbox(self, full_density_gds: Path) -> None:
        """密度图包围盒正确。"""
        dmap = compute_density_map(full_density_gds, "WG", cell_size_um=5.0)
        x_min, y_min, x_max, y_max = dmap.bbox
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(10.0, abs=1e-3)
        assert y_max == pytest.approx(5.0, abs=1e-3)


# =============================================================================
# TestCheckDensityRules: 密度规则检查
# =============================================================================
class TestCheckDensityRules:
    """check_density_rules 函数测试。"""

    def test_min_density_pass(self, full_density_gds: Path) -> None:
        """min_density 规则通过（密度 1.0 >= 0.3）。"""
        violations = check_density_rules(
            full_density_gds, [("WG", "min_density", 0.3)]
        )
        assert len(violations) == 0

    def test_min_density_fail(self, sparse_density_gds: Path) -> None:
        """min_density 规则失败（密度 0.04 < 0.3）。"""
        violations = check_density_rules(
            sparse_density_gds, [("WG", "min_density", 0.3)]
        )
        assert len(violations) == 1
        v = violations[0]
        assert v.layer_name == "WG"
        assert v.rule_type == "min_density"
        assert v.measured_density < v.limit_density

    def test_max_density_pass(self, sparse_density_gds: Path) -> None:
        """max_density 规则通过（密度 0.04 <= 0.5）。"""
        violations = check_density_rules(
            sparse_density_gds, [("WG", "max_density", 0.5)]
        )
        assert len(violations) == 0

    def test_max_density_fail(self, full_density_gds: Path) -> None:
        """max_density 规则失败（密度 1.0 > 0.5）。"""
        violations = check_density_rules(
            full_density_gds, [("WG", "max_density", 0.5)]
        )
        assert len(violations) == 1
        v = violations[0]
        assert v.layer_name == "WG"
        assert v.rule_type == "max_density"
        assert v.measured_density > v.limit_density

    def test_multiple_rules(self, full_density_gds: Path) -> None:
        """多条规则同时检查。"""
        violations = check_density_rules(
            full_density_gds,
            [
                ("WG", "min_density", 0.3),  # pass
                ("WG", "max_density", 0.5),  # fail
            ],
        )
        assert len(violations) == 1
        assert violations[0].rule_type == "max_density"

    def test_empty_rules_raises(self, full_density_gds: Path) -> None:
        """空规则 raise ValueError。"""
        with pytest.raises(ValueError, match="rules 不能为空"):
            check_density_rules(full_density_gds, [])

    def test_invalid_rule_type_raises(
        self, full_density_gds: Path
    ) -> None:
        """无效 rule_type raise ValueError。"""
        with pytest.raises(ValueError, match="无效 rule_type"):
            check_density_rules(
                full_density_gds, [("WG", "invalid_type", 0.5)]
            )

    def test_invalid_limit_raises(self, full_density_gds: Path) -> None:
        """limit_density 超出 [0,1] raise ValueError。"""
        with pytest.raises(ValueError, match="limit_density"):
            check_density_rules(
                full_density_gds, [("WG", "min_density", 1.5)]
            )

    def test_nonexistent_layer_raises(
        self, full_density_gds: Path
    ) -> None:
        """不存在的层 raise ValueError。"""
        with pytest.raises(ValueError, match="不在 GDSII 文件中"):
            check_density_rules(
                full_density_gds, [("NONEXISTENT", "min_density", 0.3)]
            )

    def test_violation_message(self, full_density_gds: Path) -> None:
        """违规消息含层名和密度。"""
        violations = check_density_rules(
            full_density_gds, [("WG", "max_density", 0.5)]
        )
        assert len(violations) == 1
        msg = violations[0].message
        assert "WG" in msg
        assert "最大密度" in msg


# =============================================================================
# TestGenerateDensityReport: 报告生成
# =============================================================================
class TestGenerateDensityReport:
    """generate_density_report 函数测试。"""

    def test_text_format(self, full_density_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_density_report(
            full_density_gds, output_format="text"
        )
        assert isinstance(report, str)
        assert "GDSII 层密度分析报告" in report
        assert "文件:" in report
        assert "顶层 cell:" in report
        assert "dbu:" in report
        assert "整体包围盒:" in report
        assert "各层密度:" in report
        assert "多边形面积:" in report
        assert "包围盒面积:" in report
        assert "密度:" in report

    def test_markdown_format(self, full_density_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_density_report(
            full_density_gds, output_format="markdown"
        )
        assert isinstance(report, str)
        assert "# GDSII 层密度分析报告" in report
        assert "**文件**" in report
        assert "**顶层 cell**" in report
        assert "**dbu**" in report
        assert "**整体包围盒**" in report
        assert "## 各层密度" in report
        assert "| 层名 |" in report

    def test_format_case_insensitive(
        self, full_density_gds: Path
    ) -> None:
        """格式大小写不敏感。"""
        r1 = generate_density_report(
            full_density_gds, output_format="TEXT"
        )
        r2 = generate_density_report(
            full_density_gds, output_format="text"
        )
        assert r1 == r2

    def test_invalid_format_raises(self, full_density_gds: Path) -> None:
        """无效格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_density_report(
                full_density_gds, output_format="json"
            )

    def test_multi_layer_report(self, multi_layer_gds: Path) -> None:
        """多层报告。"""
        report = generate_density_report(
            multi_layer_gds, output_format="text"
        )
        assert "WG" in report
        assert "METAL" in report


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_compute_density_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            compute_layer_density(tmp_path / "nonexistent.gds")

    def test_compute_density_path_is_directory(
        self, tmp_path: Path
    ) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            compute_layer_density(tmp_path)

    def test_density_map_file_not_found(self, tmp_path: Path) -> None:
        """密度图文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            compute_density_map(tmp_path / "nonexistent.gds", "WG")

    def test_check_rules_file_not_found(self, tmp_path: Path) -> None:
        """规则检查文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_density_rules(
                tmp_path / "nonexistent.gds",
                [("WG", "min_density", 0.3)],
            )

    def test_generate_report_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """报告生成文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            generate_density_report(tmp_path / "nonexistent.gds")

    def test_invalid_top_cell_name_raises(
        self, full_density_gds: Path
    ) -> None:
        """无效 top_cell_name raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            compute_layer_density(
                full_density_gds, top_cell_name="NONEXISTENT"
            )


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_source_urls(self) -> None:
        """模块 docstring 含来源 URL。"""
        from polaris.verification import gdsii_density_analyzer as mod
        doc = mod.__doc__ or ""
        assert "https://www.klayout.org/" in doc
        assert "https://github.com/SiEPIC/SiEPIC_EBeam_PDK" in doc
        assert "https://www.synopsys.com/photonic-solutions" in doc

    def test_module_docstring_has_klayout_reference(self) -> None:
        """模块 docstring 含 KLayout API 引用。"""
        from polaris.verification import gdsii_density_analyzer as mod
        doc = mod.__doc__ or ""
        assert "KLayout Region.area" in doc
        assert "KLayout DRC density" in doc
        assert "Calibre nmDRC" in doc

    def test_function_docstrings_have_sources(self) -> None:
        """关键函数 docstring 含来源。"""
        from polaris.verification import gdsii_density_analyzer as mod
        assert "KLayout Region.area" in mod.compute_layer_density.__doc__
        assert "KLayout Layout.read" in mod.compute_layer_density.__doc__
        assert "KLayout Region & Box" in mod.compute_density_map.__doc__
        assert "KLayout DRC density" in mod.check_density_rules.__doc__
        assert "CommonMark" in mod.generate_density_report.__doc__

    def test_dataclass_fields_documented(self) -> None:
        """数据类字段有文档。"""
        from polaris.verification import gdsii_density_analyzer as mod
        assert mod.LayerDensity.__doc__ is not None
        assert "density" in mod.LayerDensity.__doc__
        assert "polygon_area_um2" in mod.LayerDensity.__doc__
        assert mod.DensityMap.__doc__ is not None
        assert "grid" in mod.DensityMap.__doc__
        assert "cell_size_um" in mod.DensityMap.__doc__
        assert mod.DensityViolation.__doc__ is not None
        assert "rule_type" in mod.DensityViolation.__doc__
        assert mod.DensityReport.__doc__ is not None
        assert "layer_densities" in mod.DensityReport.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_pipeline_full_density(
        self, full_density_gds: Path
    ) -> None:
        """完整流水线：全局密度 → 密度图 → 规则检查 → 报告。"""
        report = compute_layer_density(full_density_gds)
        dmap = compute_density_map(full_density_gds, "WG", cell_size_um=5.0)
        violations = check_density_rules(
            full_density_gds, [("WG", "min_density", 0.3)]
        )
        text_report = generate_density_report(
            full_density_gds, output_format="text"
        )
        md_report = generate_density_report(
            full_density_gds, output_format="markdown"
        )
        assert report.layer_densities[0].density == pytest.approx(1.0)
        assert dmap.grid.shape == (1, 2)
        assert len(violations) == 0
        assert "1.0000" in text_report or "1.0000" in md_report

    def test_full_pipeline_sparse_density(
        self, sparse_density_gds: Path
    ) -> None:
        """稀疏密度完整流水线。"""
        report = compute_layer_density(sparse_density_gds)
        violations = check_density_rules(
            sparse_density_gds,
            [("WG", "min_density", 0.1), ("WG", "max_density", 0.5)],
        )
        # 密度 0.04 < 0.1 → min_density 违规
        # 密度 0.04 <= 0.5 → max_density 通过
        assert report.layer_densities[0].density < 0.1
        assert len(violations) == 1
        assert violations[0].rule_type == "min_density"

    def test_multi_layer_pipeline(self, multi_layer_gds: Path) -> None:
        """多层完整流水线。"""
        report = compute_layer_density(multi_layer_gds)
        wg_dmap = compute_density_map(multi_layer_gds, "WG", cell_size_um=5.0)
        metal_dmap = compute_density_map(
            multi_layer_gds, "METAL", cell_size_um=5.0
        )
        assert len(report.layer_densities) == 2
        assert wg_dmap.grid.shape == (1, 2)
        assert metal_dmap.grid.shape == (1, 2)


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类基础测试。"""

    def test_layer_density_fields(self) -> None:
        """LayerDensity 字段。"""
        ld = LayerDensity(
            layer_name="WG",
            gds_layer=1,
            gds_datatype=0,
            polygon_area_um2=50.0,
            bbox_area_um2=100.0,
            density=0.5,
            bbox=(0.0, 0.0, 10.0, 10.0),
        )
        assert ld.density == 0.5
        assert ld.bbox == (0.0, 0.0, 10.0, 10.0)

    def test_density_map_defaults(self) -> None:
        """DensityMap 默认值。"""
        dmap = DensityMap(
            layer_name="WG",
            rows=0,
            cols=0,
            cell_size_um=5.0,
            grid=np.zeros((0, 0)),
            bbox=(0.0, 0.0, 0.0, 0.0),
        )
        assert dmap.rows == 0
        assert dmap.grid.shape == (0, 0)

    def test_density_report_defaults(self) -> None:
        """DensityReport 默认值。"""
        report = DensityReport(file_path="test.gds")
        assert report.top_cell_name == ""
        assert report.dbu == 0.0
        assert report.layer_densities == []
        assert report.violations == []
        assert report.overall_bbox == (0.0, 0.0, 0.0, 0.0)

    def test_all_exports_exist(self) -> None:
        """__all__ 中所有导出符号存在。"""
        from polaris.verification import gdsii_density_analyzer as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"导出符号 {name} 不存在"
