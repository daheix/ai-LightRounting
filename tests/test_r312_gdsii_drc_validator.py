"""R312 GDSII 文件直接 DRC 验证工具测试。

覆盖:
- extract_polygons_from_gdsii: 从 GDSII 提取多边形
- run_drc_on_gdsii: 端到端 DRC 检查
- drc_summary_from_gdsii: 汇总报告
- R03 错误处理
- R02 学术诚信

来源:
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory
from polaris.verification.gdsii_drc_validator import (
    drc_summary_from_gdsii,
    extract_polygons_from_gdsii,
    run_drc_on_gdsii,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def compliant_gds(tmp_path: Path) -> Path:
    """创建合规 GDSII 文件（宽 0.5μm，间距 1.0μm）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
                {
                    "layer": 1, "datatype": 0,
                    "points": [[11, 0], [21, 0], [21, 0.5], [11, 0.5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "compliant.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def violating_gds(tmp_path: Path) -> Path:
    """创建违规 GDSII 文件（宽 0.3μm，间距 0.2μm）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.3], [0, 0.3]],  # 宽度 0.3 < 0.45
                },
                {
                    "layer": 1, "datatype": 0,
                    "points": [[10.2, 0], [20.2, 0], [20.2, 0.3], [10.2, 0.3]],  # 间距 0.2 < 0.5
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "violating.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_gds(tmp_path: Path) -> Path:
    """创建多层 GDSII 文件（WG 层 + METAL 层）。"""
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


# =============================================================================
# TestExtractPolygonsFromGdsii: 多边形提取
# =============================================================================
class TestExtractPolygonsFromGdsii:
    """extract_polygons_from_gdsii 测试。"""

    def test_extract_single_layer(self, compliant_gds: Path) -> None:
        """提取单层多边形。"""
        result = extract_polygons_from_gdsii(compliant_gds)
        assert "WG" in result
        assert len(result["WG"]) >= 1
        # 验证多边形格式
        for poly in result["WG"]:
            assert isinstance(poly, np.ndarray)
            assert poly.shape[1] == 2
            assert poly.shape[0] >= 3

    def test_extract_multi_layer(self, multi_layer_gds: Path) -> None:
        """提取多层多边形。"""
        result = extract_polygons_from_gdsii(multi_layer_gds)
        assert "WG" in result
        assert "METAL" in result
        assert len(result["WG"]) >= 1
        assert len(result["METAL"]) >= 1

    def test_extract_custom_layer_map(self, compliant_gds: Path) -> None:
        """自定义层映射。"""
        custom_map = {(1, 0): "MY_WG"}
        result = extract_polygons_from_gdsii(compliant_gds, layer_map=custom_map)
        assert "MY_WG" in result

    def test_extract_polygon_coordinates(self, compliant_gds: Path) -> None:
        """验证提取的多边形坐标在合理范围。"""
        result = extract_polygons_from_gdsii(compliant_gds)
        for poly in result["WG"]:
            # 坐标应为 μm 单位，原 GDSII 范围 0-21μm
            assert poly.min() >= -0.1  # 允许微小浮点误差
            assert poly.max() <= 22.0

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_polygons_from_gdsii(tmp_path / "nonexistent.gds")

    def test_invalid_top_cell_raises(self, compliant_gds: Path) -> None:
        with pytest.raises(ValueError, match="不存在"):
            extract_polygons_from_gdsii(compliant_gds, top_cell_name="NONEXISTENT")


# =============================================================================
# TestRunDrcOnGdsii: DRC 检查
# =============================================================================
class TestRunDrcOnGdsii:
    """run_drc_on_gdsii 测试。"""

    def test_compliant_gds_no_violations(self, compliant_gds: Path) -> None:
        """合规 GDS 应无违规。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="S1", category=DRCRuleCategory.MIN_SPACING,
                layer="WG", limit_value=0.5,
            ),
        ]
        results = run_drc_on_gdsii(compliant_gds, rules)
        assert len(results) == 2
        for r in results:
            assert r.violation_count == 0

    def test_violating_gds_has_violations(self, violating_gds: Path) -> None:
        """违规 GDS 应有违规。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
        ]
        results = run_drc_on_gdsii(violating_gds, rules)
        assert len(results) == 1
        assert results[0].violation_count > 0

    def test_violating_gds_spacing_check(self, violating_gds: Path) -> None:
        """违规 GDS 的间距检查应有违规。"""
        rules = [
            CurvilinearDRCRule(
                name="S1", category=DRCRuleCategory.MIN_SPACING,
                layer="WG", limit_value=0.5,
            ),
        ]
        results = run_drc_on_gdsii(violating_gds, rules)
        assert len(results) == 1
        assert results[0].violation_count > 0

    def test_multi_layer_drc(self, multi_layer_gds: Path) -> None:
        """多层 GDS 的 DRC 检查。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="W2", category=DRCRuleCategory.MIN_WIDTH,
                layer="METAL", limit_value=0.5,
            ),
        ]
        results = run_drc_on_gdsii(multi_layer_gds, rules)
        assert len(results) == 2
        # 两个层都应无违规
        for r in results:
            assert r.violation_count == 0

    def test_drc_undefined_layer_raises(self, compliant_gds: Path) -> None:
        """规则引用未定义的层应 raise KeyError（R03）。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="NONEXISTENT_LAYER", limit_value=0.45,
            ),
        ]
        with pytest.raises(KeyError, match="NONEXISTENT_LAYER"):
            run_drc_on_gdsii(compliant_gds, rules)

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_drc_on_gdsii(tmp_path / "nonexistent.gds", [])


# =============================================================================
# TestDrcSummaryFromGdsii: 汇总报告
# =============================================================================
class TestDrcSummaryFromGdsii:
    """drc_summary_from_gdsii 测试。"""

    def test_compliant_summary(self, compliant_gds: Path) -> None:
        """合规 GDS 汇总报告。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
        ]
        summary = drc_summary_from_gdsii(compliant_gds, rules)
        assert summary["file_path"] == str(compliant_gds)
        assert summary["total_rules"] == 1
        assert summary["total_violations"] == 0
        assert summary["errors"] == 0
        assert summary["passed"] is True
        assert "WG" in summary["layers_extracted"]
        assert summary["polygon_count_by_layer"]["WG"] >= 1

    def test_violating_summary(self, violating_gds: Path) -> None:
        """违规 GDS 汇总报告。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
        ]
        summary = drc_summary_from_gdsii(violating_gds, rules)
        assert summary["total_violations"] > 0
        assert summary["errors"] > 0
        assert summary["passed"] is False
        assert summary["violations_by_rule"]["W1"] > 0
        assert summary["violations_by_layer"]["WG"] > 0

    def test_multi_layer_summary(self, multi_layer_gds: Path) -> None:
        """多层 GDS 汇总报告。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="W2", category=DRCRuleCategory.MIN_WIDTH,
                layer="METAL", limit_value=0.5,
            ),
        ]
        summary = drc_summary_from_gdsii(multi_layer_gds, rules)
        assert summary["total_rules"] == 2
        assert "WG" in summary["layers_extracted"]
        assert "METAL" in summary["layers_extracted"]
        assert summary["passed"] is True

    def test_summary_contains_polygon_count(self, compliant_gds: Path) -> None:
        """汇总报告应包含各层多边形数。"""
        rules = []
        summary = drc_summary_from_gdsii(compliant_gds, rules)
        assert isinstance(summary["polygon_count_by_layer"], dict)
        assert summary["polygon_count_by_layer"]["WG"] >= 1


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_extract_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_polygons_from_gdsii(tmp_path / "missing.gds")

    def test_extract_path_is_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="不是文件"):
            extract_polygons_from_gdsii(tmp_path)

    def test_drc_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_drc_on_gdsii(tmp_path / "missing.gds", [])

    def test_summary_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            drc_summary_from_gdsii(tmp_path / "missing.gds", [])


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 包含 ≥5 个 URL。"""
        from polaris.verification import gdsii_drc_validator
        doc = gdsii_drc_validator.__doc__ or ""
        urls = [line for line in doc.split() if line.startswith("http")]
        assert len(urls) >= 5

    def test_default_layer_map_documented(self) -> None:
        """默认层映射来源标注。"""
        from polaris.verification.gdsii_drc_validator import _get_default_layer_map
        # 检查函数注释中是否提到 SiEPIC
        # _get_default_layer_map 是私有函数，检查模块 docstring 即可
        from polaris.verification import gdsii_drc_validator
        doc = gdsii_drc_validator.__doc__ or ""
        assert "SiEPIC" in doc

    def test_siepic_standard_layers_present(self) -> None:
        """默认层映射应包含 SiEPIC 13 层。"""
        from polaris.verification.gdsii_drc_validator import _get_default_layer_map
        layer_map = _get_default_layer_map()
        # SiEPIC 标准 13 层
        assert len(layer_map) == 13
        assert layer_map[(1, 0)] == "WG"
        assert layer_map[(5, 0)] == "METAL"


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_drc_workflow_compliant(self, compliant_gds: Path) -> None:
        """合规 GDS 完整 DRC 工作流。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="S1", category=DRCRuleCategory.MIN_SPACING,
                layer="WG", limit_value=0.5,
            ),
            CurvilinearDRCRule(
                name="A1", category=DRCRuleCategory.MIN_AREA,
                layer="WG", limit_value=0.1,
            ),
        ]
        # Step 1: 提取多边形
        polygons = extract_polygons_from_gdsii(compliant_gds)
        assert "WG" in polygons
        # Step 2: DRC 检查
        results = run_drc_on_gdsii(compliant_gds, rules)
        assert len(results) == 3
        # Step 3: 汇总报告
        summary = drc_summary_from_gdsii(compliant_gds, rules)
        assert summary["passed"] is True
        assert summary["total_violations"] == 0

    def test_full_drc_workflow_violating(self, violating_gds: Path) -> None:
        """违规 GDS 完整 DRC 工作流。"""
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="S1", category=DRCRuleCategory.MIN_SPACING,
                layer="WG", limit_value=0.5,
            ),
        ]
        summary = drc_summary_from_gdsii(violating_gds, rules)
        assert summary["passed"] is False
        assert summary["total_violations"] > 0
        # 至少 W1 或 S1 触发
        assert summary["violations_by_rule"]["W1"] > 0 or summary["violations_by_rule"]["S1"] > 0

    def test_performance_large_gds(self, tmp_path: Path) -> None:
        """大 GDSII 文件 DRC 性能测试。"""
        import time
        # 创建 50 个多边形的大 GDS
        polygons = []
        for i in range(50):
            polygons.append({
                "layer": 1, "datatype": 0,
                "points": [[i * 2, 0], [i * 2 + 1, 0], [i * 2 + 1, 0.5], [i * 2, 0.5]],
            })
        cells_spec = [{"name": "TOP", "polygons": polygons, "is_top": True}]
        gds_path = tmp_path / "large.gds"
        export_gdsii_from_cells(cells_spec, gds_path)
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
        ]
        t0 = time.time()
        summary = drc_summary_from_gdsii(gds_path, rules)
        elapsed = time.time() - t0
        assert elapsed < 2.0, f"大 GDS DRC 耗时 {elapsed:.3f}s"
        assert summary["passed"] is True
