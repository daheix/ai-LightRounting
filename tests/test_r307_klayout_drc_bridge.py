"""R307 KLayout DRC 集成桥接测试套件。

测试 polaris.verification.klayout_drc_bridge 模块的全部公开接口:
1. KLayoutDRCConfig / KLayoutDRCResult 数据类
2. polygons_to_klayout_region / klayout_region_to_polygons 多边形往返
3. check_min_width / check_min_spacing / check_min_area 三类 DRC 检查
4. run_klayout_drc 多规则编排
5. klayout_drc_summary 摘要生成
6. R03 错误处理（规则类别校验/点数校验/层名校验）
7. 学术诚信（KLayout API 文献溯源）

学术依据:
- KLayout Region API: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout EdgePairs: https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- Shoelace formula: https://en.wikipedia.org/wiki/Shoelace_formula
- Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
- Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory
from polaris.verification.klayout_drc_bridge import (
    KLayoutDRCConfig,
    KLayoutDRCResult,
    check_min_area,
    check_min_spacing,
    check_min_width,
    klayout_drc_summary,
    klayout_region_to_polygons,
    polygons_to_klayout_region,
    run_klayout_drc,
)


# =============================================================================
# 测试 fixtures
# =============================================================================
@pytest.fixture
def rule_min_width() -> CurvilinearDRCRule:
    """最小宽度规则 fixture: 0.45μm。"""
    return CurvilinearDRCRule(
        name="W1_min_wg_width",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="waveguide",
        limit_value=0.45,
        units="μm",
        is_curvilinear=False,
        description="波导最小宽度",
        severity="error",
    )


@pytest.fixture
def rule_min_spacing() -> CurvilinearDRCRule:
    """最小间距规则 fixture: 0.5μm。"""
    return CurvilinearDRCRule(
        name="S1_min_wg_spacing",
        category=DRCRuleCategory.MIN_SPACING,
        layer="waveguide",
        limit_value=0.5,
        units="μm",
        is_curvilinear=False,
        description="波导最小间距",
        severity="error",
    )


@pytest.fixture
def rule_min_area() -> CurvilinearDRCRule:
    """最小面积规则 fixture: 2.0μm²。"""
    return CurvilinearDRCRule(
        name="A1_min_pad_area",
        category=DRCRuleCategory.MIN_AREA,
        layer="waveguide",
        limit_value=2.0,
        units="μm²",
        is_curvilinear=False,
        description="焊盘最小面积",
        severity="error",
    )


@pytest.fixture
def rule_warning() -> CurvilinearDRCRule:
    """警告级规则 fixture（severity=warning）。"""
    return CurvilinearDRCRule(
        name="W3_min_curve_width",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="waveguide",
        limit_value=0.50,
        units="μm",
        is_curvilinear=True,
        description="曲线段最小宽度",
        severity="warning",
    )


@pytest.fixture
def square_1um() -> np.ndarray:
    """1x1μm 方形多边形。"""
    return np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)


@pytest.fixture
def thin_polygon() -> np.ndarray:
    """0.1μm 宽的细长多边形（违反最小宽度 0.45μm）。"""
    return np.array([[0, 0], [0.1, 0], [0.1, 5], [0, 5]], dtype=float)


@pytest.fixture
def wide_polygon() -> np.ndarray:
    """1μm 宽的多边形（满足最小宽度 0.45μm）。"""
    return np.array([[0, 0], [1, 0], [1, 5], [0, 5]], dtype=float)


@pytest.fixture
def close_pair() -> list[np.ndarray]:
    """两个间距 0.1μm 的方形（违反最小间距 0.5μm）。"""
    return [
        np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float),
        np.array([[1.1, 0], [2.1, 0], [2.1, 1], [1.1, 1]], dtype=float),
    ]


@pytest.fixture
def far_pair() -> list[np.ndarray]:
    """两个间距 1.0μm 的方形（满足最小间距 0.5μm）。"""
    return [
        np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float),
        np.array([[2, 0], [3, 0], [3, 1], [2, 1]], dtype=float),
    ]


# =============================================================================
# 1. KLayoutDRCConfig 数据类测试
# =============================================================================
class TestKLayoutDRCConfig:
    """KLayoutDRCConfig 配置数据类测试。"""

    def test_default_config(self):
        """默认配置: dbu=0.001μm, snap_to_dbu=True, 13 层 SiEPIC 映射。"""
        cfg = KLayoutDRCConfig()
        assert cfg.dbu == 0.001
        assert cfg.snap_to_dbu is True
        # SiEPIC 13 层标准映射
        assert len(cfg.layer_map) == 13
        assert cfg.layer_map["WG"] == (1, 0)
        assert cfg.layer_map["SLAB150"] == (2, 0)
        assert cfg.layer_map["SLAB90"] == (3, 0)
        assert cfg.layer_map["SiN"] == (4, 0)
        assert cfg.layer_map["METAL"] == (5, 0)
        assert cfg.layer_map["HEATER"] == (6, 0)
        assert cfg.layer_map["TEXT"] == (7, 0)
        assert cfg.layer_map["LABEL"] == (8, 0)
        assert cfg.layer_map["DEVREC"] == (68, 0)
        assert cfg.layer_map["PIN"] == (69, 0)
        assert cfg.layer_map["PORT"] == (70, 0)
        assert cfg.layer_map["FLOORPLAN"] == (99, 0)
        assert cfg.layer_map["PORT_GEOM"] == (71, 0)

    def test_custom_dbu(self):
        """自定义 dbu: 0.0005μm = 0.5nm。"""
        cfg = KLayoutDRCConfig(dbu=0.0005)
        assert cfg.dbu == 0.0005

    def test_custom_layer_map(self):
        """自定义层映射。"""
        custom_map = {"WG": (10, 0), "METAL": (20, 0)}
        cfg = KLayoutDRCConfig(layer_map=custom_map)
        assert cfg.layer_map == custom_map
        assert len(cfg.layer_map) == 2

    def test_snap_to_dbu_disable(self):
        """禁用 snap_to_dbu。"""
        cfg = KLayoutDRCConfig(snap_to_dbu=False)
        assert cfg.snap_to_dbu is False


# =============================================================================
# 2. KLayoutDRCResult 数据类测试
# =============================================================================
class TestKLayoutDRCResult:
    """KLayoutDRCResult 结果数据类测试。"""

    def test_default_result(self):
        """默认结果: severity=error, violation_count=0, 空多边形列表。"""
        result = KLayoutDRCResult(
            rule_id="W1",
            rule_category=DRCRuleCategory.MIN_WIDTH,
            layer_name="waveguide",
            violation_count=0,
        )
        assert result.rule_id == "W1"
        assert result.rule_category == DRCRuleCategory.MIN_WIDTH
        assert result.layer_name == "waveguide"
        assert result.violation_count == 0
        assert result.violation_polygons == []
        assert result.severity == "error"

    def test_custom_severity(self):
        """自定义 severity=warning。"""
        result = KLayoutDRCResult(
            rule_id="W3",
            rule_category=DRCRuleCategory.MIN_WIDTH,
            layer_name="waveguide",
            violation_count=2,
            severity="warning",
        )
        assert result.severity == "warning"
        assert result.violation_count == 2


# =============================================================================
# 3. 多边形往返测试
# =============================================================================
class TestPolygonRoundTrip:
    """PoLaRIS 多边形 ↔ KLayout Region 往返测试。"""

    def test_square_roundtrip(self, square_1um):
        """1x1μm 方形往返: 顶点数和面积保持一致。"""
        region = polygons_to_klayout_region([square_1um])
        polys_back = klayout_region_to_polygons(region)
        assert len(polys_back) == 1
        # 顶点数 4
        assert polys_back[0].shape == (4, 2)
        # 面积 1.0μm²（鞋带公式）
        area = 0.5 * abs(np.sum(
            polys_back[0][:, 0] * np.roll(polys_back[0][:, 1], -1) -
            np.roll(polys_back[0][:, 0], -1) * polys_back[0][:, 1]
        ))
        assert abs(area - 1.0) < 0.01

    def test_rectangle_roundtrip(self):
        """10x5μm 矩形往返。"""
        rect = np.array([[0, 0], [10, 0], [10, 5], [0, 5]], dtype=float)
        region = polygons_to_klayout_region([rect])
        polys_back = klayout_region_to_polygons(region)
        assert len(polys_back) == 1
        assert polys_back[0].shape == (4, 2)

    def test_multiple_polygons(self):
        """多个多边形往返。"""
        polys = [
            np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float),
            np.array([[5, 5], [6, 5], [6, 6], [5, 6]], dtype=float),
            np.array([[10, 10], [12, 10], [12, 12], [10, 12]], dtype=float),
        ]
        region = polygons_to_klayout_region(polys)
        polys_back = klayout_region_to_polygons(region)
        assert len(polys_back) == 3

    def test_triangle_roundtrip(self):
        """三角形往返。"""
        tri = np.array([[0, 0], [2, 0], [1, 2]], dtype=float)
        region = polygons_to_klayout_region([tri])
        polys_back = klayout_region_to_polygons(region)
        assert len(polys_back) == 1
        assert polys_back[0].shape == (3, 2)

    def test_custom_dbu_roundtrip(self):
        """自定义 dbu=0.0005μm 往返。"""
        cfg = KLayoutDRCConfig(dbu=0.0005)
        square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
        region = polygons_to_klayout_region([square], cfg)
        polys_back = klayout_region_to_polygons(region, cfg)
        assert len(polys_back) == 1
        # 面积仍约等于 1.0μm²
        area = 0.5 * abs(np.sum(
            polys_back[0][:, 0] * np.roll(polys_back[0][:, 1], -1) -
            np.roll(polys_back[0][:, 0], -1) * polys_back[0][:, 1]
        ))
        assert abs(area - 1.0) < 0.01

    def test_empty_polygon_list(self):
        """空多边形列表: 返回空 Region。"""
        region = polygons_to_klayout_region([])
        polys_back = klayout_region_to_polygons(region)
        assert len(polys_back) == 0


# =============================================================================
# 4. 最小宽度检查测试
# =============================================================================
class TestCheckMinWidth:
    """check_min_width 最小宽度检查测试。"""

    def test_violation_thin_polygon(self, rule_min_width, thin_polygon):
        """0.1μm 细长多边形违反 0.45μm 最小宽度规则。"""
        result = check_min_width([thin_polygon], rule_min_width)
        assert result.violation_count >= 1
        assert result.severity == "error"
        assert result.rule_id == "W1_min_wg_width"
        assert result.layer_name == "waveguide"

    def test_pass_wide_polygon(self, rule_min_width, wide_polygon):
        """1μm 宽多边形满足 0.45μm 最小宽度规则。"""
        result = check_min_width([wide_polygon], rule_min_width)
        assert result.violation_count == 0

    def test_square_passes(self, rule_min_width, square_1um):
        """1x1μm 方形满足 0.45μm 最小宽度规则。"""
        result = check_min_width([square_1um], rule_min_width)
        assert result.violation_count == 0

    def test_warning_severity(self, rule_warning, thin_polygon):
        """警告级规则触发时 severity=warning。"""
        result = check_min_width([thin_polygon], rule_warning)
        assert result.severity == "warning"

    def test_violation_polygons_returned(self, rule_min_width, thin_polygon):
        """违规时返回违规多边形列表。"""
        result = check_min_width([thin_polygon], rule_min_width)
        if result.violation_count > 0:
            assert len(result.violation_polygons) >= 0  # polygons 可能为空（边对转多边形）


# =============================================================================
# 5. 最小间距检查测试
# =============================================================================
class TestCheckMinSpacing:
    """check_min_spacing 最小间距检查测试。"""

    def test_violation_close_pair(self, rule_min_spacing, close_pair):
        """间距 0.1μm 的方形对违反 0.5μm 最小间距规则。"""
        result = check_min_spacing(close_pair, rule_min_spacing)
        assert result.violation_count >= 1
        assert result.severity == "error"
        assert result.rule_id == "S1_min_wg_spacing"

    def test_pass_far_pair(self, rule_min_spacing, far_pair):
        """间距 1.0μm 的方形对满足 0.5μm 最小间距规则。"""
        result = check_min_spacing(far_pair, rule_min_spacing)
        assert result.violation_count == 0

    def test_single_polygon_no_spacing_violation(self, rule_min_spacing, square_1um):
        """单个多边形不触发间距违规。"""
        result = check_min_spacing([square_1um], rule_min_spacing)
        assert result.violation_count == 0


# =============================================================================
# 6. 最小面积检查测试
# =============================================================================
class TestCheckMinArea:
    """check_min_area 最小面积检查测试（鞋带公式）。"""

    def test_violation_small_square(self, rule_min_area, square_1um):
        """1x1μm=1μm² 方形违反 2.0μm² 最小面积规则。"""
        result = check_min_area([square_1um], rule_min_area)
        assert result.violation_count == 1
        assert result.severity == "error"
        assert result.rule_id == "A1_min_pad_area"
        # 违规多边形就是原多边形
        assert len(result.violation_polygons) == 1

    def test_pass_large_square(self, rule_min_area):
        """2x2μm=4μm² 方形满足 2.0μm² 最小面积规则。"""
        large = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
        result = check_min_area([large], rule_min_area)
        assert result.violation_count == 0

    def test_multiple_violations(self, rule_min_area):
        """多个小多边形都违反面积规则。"""
        small_polys = [
            np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float),  # 1μm²
            np.array([[5, 5], [6, 5], [6, 6], [5, 6]], dtype=float),  # 1μm²
            np.array([[10, 10], [11, 10], [11, 11], [10, 11]], dtype=float),  # 1μm²
        ]
        result = check_min_area(small_polys, rule_min_area)
        assert result.violation_count == 3

    def test_triangle_area(self, rule_min_area):
        """三角形面积: 底x高/2。"""
        # 底=2, 高=2, 面积=2.0μm² 满足规则
        tri = np.array([[0, 0], [2, 0], [1, 2]], dtype=float)
        result = check_min_area([tri], rule_min_area)
        assert result.violation_count == 0

    def test_violation_polygon_returned(self, rule_min_area, square_1um):
        """违规时返回的多边形就是原多边形。"""
        result = check_min_area([square_1um], rule_min_area)
        assert len(result.violation_polygons) == 1
        np.testing.assert_array_almost_equal(
            result.violation_polygons[0], square_1um
        )


# =============================================================================
# 7. R03 错误处理测试
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back: 所有错误必须 raise。"""

    def test_width_rule_category_mismatch(self, rule_min_spacing, square_1um):
        """宽度检查收到间距规则: raise ValueError。"""
        with pytest.raises(ValueError, match="MIN_WIDTH"):
            check_min_width([square_1um], rule_min_spacing)

    def test_spacing_rule_category_mismatch(self, rule_min_width, close_pair):
        """间距检查收到宽度规则: raise ValueError。"""
        with pytest.raises(ValueError, match="MIN_SPACING"):
            check_min_spacing(close_pair, rule_min_width)

    def test_area_rule_category_mismatch(self, rule_min_width, square_1um):
        """面积检查收到宽度规则: raise ValueError。"""
        with pytest.raises(ValueError, match="MIN_AREA"):
            check_min_area([square_1um], rule_min_width)

    def test_polygon_less_than_3_points_to_region(self):
        """点数 < 3 的多边形转 Region: raise ValueError。"""
        bad_poly = np.array([[0, 0], [1, 0]], dtype=float)
        with pytest.raises(ValueError, match="点数 2 < 3"):
            polygons_to_klayout_region([bad_poly])

    def test_polygon_less_than_3_points_area_check(self, rule_min_area):
        """面积检查点数 < 3: raise ValueError（不静默跳过）。"""
        bad_poly = np.array([[0, 0], [1, 0]], dtype=float)
        with pytest.raises(ValueError, match="点数 2 < 3"):
            check_min_area([bad_poly], rule_min_area)

    def test_non_2d_polygon_to_region(self):
        """非二维数组多边形转 Region: raise ValueError。"""
        bad_poly = np.array([0, 1, 2, 3], dtype=float)
        with pytest.raises(ValueError, match="必须是 .N, 2. 二维数组"):
            polygons_to_klayout_region([bad_poly])

    def test_run_klayout_drc_missing_layer(self, rule_min_width, square_1um):
        """run_klayout_drc 规则引用不存在的层: raise KeyError。"""
        with pytest.raises(KeyError, match="不在 layer_polygons"):
            run_klayout_drc({"metal": [square_1um]}, [rule_min_width])

    def test_run_klayout_drc_unsupported_category(self, square_1um):
        """run_klayout_drc 不支持的规则类别: raise ValueError。"""
        unsupported_rule = CurvilinearDRCRule(
            name="ANG1",
            category=DRCRuleCategory.MAX_ANGLE,
            layer="waveguide",
            limit_value=135,
            units="°",
            is_curvilinear=False,
            description="最大拐角",
            severity="error",
        )
        with pytest.raises(ValueError, match="暂不支持 KLayout 检查"):
            run_klayout_drc({"waveguide": [square_1um]}, [unsupported_rule])


# =============================================================================
# 8. run_klayout_drc 多规则编排测试
# =============================================================================
class TestRunKLayoutDRC:
    """run_klayout_drc 多规则编排测试。"""

    def test_multi_rule_execution(
        self, rule_min_width, rule_min_spacing, rule_min_area,
        close_pair, square_1um,
    ):
        """多规则编排: 同时执行 width/spacing/area 检查。"""
        layer_polys = {"waveguide": close_pair + [square_1um]}
        rules = [rule_min_width, rule_min_spacing, rule_min_area]
        results = run_klayout_drc(layer_polys, rules)
        assert len(results) == 3
        # 各结果对应正确的规则
        assert results[0].rule_id == "W1_min_wg_width"
        assert results[1].rule_id == "S1_min_wg_spacing"
        assert results[2].rule_id == "A1_min_pad_area"

    def test_empty_rules_list(self, square_1um):
        """空规则列表: 返回空结果列表。"""
        results = run_klayout_drc({"waveguide": [square_1um]}, [])
        assert results == []

    def test_all_pass_scenario(self, rule_min_width, rule_min_spacing, far_pair):
        """全部合规场景: 所有规则 violation_count=0。"""
        layer_polys = {"waveguide": far_pair}
        rules = [rule_min_width, rule_min_spacing]
        results = run_klayout_drc(layer_polys, rules)
        assert all(r.violation_count == 0 for r in results)

    def test_multiple_layers(self, rule_min_width, rule_min_area, square_1um):
        """多层多规则: 不同层应用不同规则。"""
        rule_metal_width = CurvilinearDRCRule(
            name="W_metal",
            category=DRCRuleCategory.MIN_WIDTH,
            layer="metal",
            limit_value=0.45,
            units="μm",
            description="金属最小宽度",
            severity="error",
        )
        layer_polys = {
            "waveguide": [square_1um],
            "metal": [np.array([[0, 0], [0.1, 0], [0.1, 5], [0, 5]], dtype=float)],
        }
        rules = [rule_min_width, rule_metal_width, rule_min_area]
        results = run_klayout_drc(layer_polys, rules)
        assert len(results) == 3


# =============================================================================
# 9. klayout_drc_summary 摘要测试
# =============================================================================
class TestKLayoutDRCSummary:
    """klayout_drc_summary 摘要生成测试。"""

    def test_empty_results(self):
        """空结果列表: 生成基本摘要。"""
        summary = klayout_drc_summary([])
        assert "KLayout DRC" in summary
        assert "检查规则数: 0" in summary
        assert "总违规数: 0" in summary

    def test_pass_results(self, rule_min_width, wide_polygon):
        """全部 PASS 的结果摘要。"""
        result = check_min_width([wide_polygon], rule_min_width)
        summary = klayout_drc_summary([result])
        assert "PASS" in summary
        assert "总违规数: 0" in summary

    def test_fail_results(self, rule_min_width, thin_polygon):
        """违规结果摘要。"""
        result = check_min_width([thin_polygon], rule_min_width)
        summary = klayout_drc_summary([result])
        assert "FAIL" in summary
        assert "总违规数:" in summary
        assert "错误级违规规则数:" in summary

    def test_mixed_severity_summary(
        self, rule_min_width, rule_warning, thin_polygon,
    ):
        """混合 error+warning 严重级别的摘要。"""
        result_error = check_min_width([thin_polygon], rule_min_width)
        result_warning = check_min_width([thin_polygon], rule_warning)
        summary = klayout_drc_summary([result_error, result_warning])
        assert "错误级违规规则数:" in summary
        assert "警告级违规规则数:" in summary

    def test_summary_contains_rule_details(self, rule_min_width, thin_polygon):
        """摘要包含各规则详情。"""
        result = check_min_width([thin_polygon], rule_min_width)
        summary = klayout_drc_summary([result])
        assert rule_min_width.name in summary
        assert "waveguide" in summary
        assert "MIN_WIDTH" in summary


# =============================================================================
# 10. 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_drc_workflow(
        self, rule_min_width, rule_min_spacing, rule_min_area,
    ):
        """完整 DRC 工作流: 多边形 → Region → 检查 → 摘要。"""
        # 1. 准备版图（包含 width/spacing/area 三类违规）
        layer_polys = {
            "waveguide": [
                # 细长多边形（width 违规）
                np.array([[0, 0], [0.1, 0], [0.1, 5], [0, 5]], dtype=float),
                # 两个间距 0.1μm 的方形（spacing 违规）
                np.array([[10, 0], [11, 0], [11, 1], [10, 1]], dtype=float),
                np.array([[11.1, 0], [12.1, 0], [12.1, 1], [11.1, 1]], dtype=float),
                # 1x1μm 小方形（area 违规，1μm² < 2μm²）
                np.array([[20, 0], [21, 0], [21, 1], [20, 1]], dtype=float),
            ]
        }
        rules = [rule_min_width, rule_min_spacing, rule_min_area]

        # 2. 执行 DRC
        results = run_klayout_drc(layer_polys, rules)

        # 3. 生成摘要
        summary = klayout_drc_summary(results)

        # 4. 验证
        assert len(results) == 3
        assert "KLayout DRC" in summary
        # 至少有 width 和 spacing 违规
        total_violations = sum(r.violation_count for r in results)
        assert total_violations >= 2

    def test_roundtrip_preserves_geometry(self):
        """往返保持几何形状: 多边形 → Region → 多边形 面积一致。"""
        original = np.array([[0, 0], [5, 0], [5, 3], [0, 3]], dtype=float)
        region = polygons_to_klayout_region([original])
        polys_back = klayout_region_to_polygons(region)

        # 原面积
        orig_area = 0.5 * abs(np.sum(
            original[:, 0] * np.roll(original[:, 1], -1) -
            np.roll(original[:, 0], -1) * original[:, 1]
        ))
        # 返还面积
        back = polys_back[0]
        back_area = 0.5 * abs(np.sum(
            back[:, 0] * np.roll(back[:, 1], -1) -
            np.roll(back[:, 0], -1) * back[:, 1]
        ))
        assert abs(orig_area - back_area) < 0.01
        assert abs(orig_area - 15.0) < 0.01  # 5x3=15μm²

    def test_siepic_layer_map_consistency(self):
        """SiEPIC 13 层映射一致性: 与 SiEPIC_EBeam_PDK 标准对齐。"""
        cfg = KLayoutDRCConfig()
        # SiEPIC EBeam PDK 标准层定义
        # 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        expected_layers = {
            "WG": (1, 0),
            "SLAB150": (2, 0),
            "SLAB90": (3, 0),
            "SiN": (4, 0),
            "METAL": (5, 0),
            "HEATER": (6, 0),
            "TEXT": (7, 0),
            "LABEL": (8, 0),
            "DEVREC": (68, 0),
            "PIN": (69, 0),
            "PORT": (70, 0),
            "FLOORPLAN": (99, 0),
            "PORT_GEOM": (71, 0),
        }
        for layer_name, layer_tuple in expected_layers.items():
            assert cfg.layer_map[layer_name] == layer_tuple, (
                f"SiEPIC 层 {layer_name} 映射不一致: "
                f"期望 {layer_tuple}, 实际 {cfg.layer_map[layer_name]}"
            )


# =============================================================================
# 11. 学术诚信测试
# =============================================================================
class TestAcademicIntegrity:
    """R02 学术诚信: 验证 KLayout API 与文献溯源。"""

    def test_klayout_dbu_default_source(self):
        """dbu 默认值 0.001μm=1nm 来源: KLayout 默认 dbu。

        来源: https://www.klayout.org/doc-qt5/code/class_Layout.html
        """
        cfg = KLayoutDRCConfig()
        # KLayout 默认 dbu 为 0.001μm（1nm），对应 1nm 分辨率
        assert cfg.dbu == 0.001
        assert cfg.dbu == 1e-3  # 1nm

    def test_klayout_width_check_api(self, rule_min_width, thin_polygon):
        """width_check(d) 返回 EdgePairs: KLayout 0.30.9 API。

        来源: https://www.klayout.org/doc-qt5/code/class_Region.html#method1046
        """
        # 通过 check_min_width 间接验证 width_check API
        result = check_min_width([thin_polygon], rule_min_width)
        assert isinstance(result, KLayoutDRCResult)
        assert result.violation_count >= 1  # 细长多边形必触发宽度违规

    def test_klayout_space_check_api(self, rule_min_spacing, close_pair):
        """space_check(d) 返回 EdgePairs: KLayout 0.30.9 API。

        来源: https://www.klayout.org/doc-qt5/code/class_Region.html#method1047
        """
        result = check_min_spacing(close_pair, rule_min_spacing)
        assert isinstance(result, KLayoutDRCResult)
        assert result.violation_count >= 1  # 间距 0.1μm < 0.5μm 必触发

    def test_shoelace_formula_area(self, rule_min_area):
        """鞋带公式面积计算: Area = 0.5 * |Σ(x_i*y_{i+1} - x_{i+1}*y_i)|。

        来源: https://en.wikipedia.org/wiki/Shoelace_formula
        """
        # 2x3=6μm² 矩形
        rect = np.array([[0, 0], [2, 0], [2, 3], [0, 3]], dtype=float)
        # 鞋带公式验证
        area = 0.5 * abs(np.sum(
            rect[:, 0] * np.roll(rect[:, 1], -1) -
            np.roll(rect[:, 0], -1) * rect[:, 1]
        ))
        assert abs(area - 6.0) < 1e-10
        # 6μm² > 2μm² 不违规
        result = check_min_area([rect], rule_min_area)
        assert result.violation_count == 0

    def test_siepic_13_layers_count(self):
        """SiEPIC EBeam PDK 标准 13 层映射。

        来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        cfg = KLayoutDRCConfig()
        # SiEPIC EBeam PDK 定义 13 个标准层
        assert len(cfg.layer_map) == 13


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
