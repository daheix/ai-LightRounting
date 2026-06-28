"""P0-4 Calibre xACT 寄生效应提取 + LFD 光刻友好设计 测试。

测试内容:
1. TestLayerSpec: 物理层规格参数校验（3 个）
2. TestLithoRule: 光刻规则参数校验（3 个）
3. TestParasiticExtractor: 寄生 RC 提取（8 个）
   - 电阻提取 R = ρ·L/(w·h)
   - 平行板电容 C_pp = ε₀·εᵣ·w·L/d
   - 边缘电容 C_fringe（混合引擎，短网络）
   - 侧壁耦合电容 C_coupling
   - SPICE 网表生成
   - 错误处理（空 layer_map / 空 Layout / 缺失 GDS / 非法阈值）
4. TestLithoFriendlyChecker: 光刻热点检测与评分（8 个）
   - WIDTH / SPACE / AREA 热点检测
   - 满分 / 含 ERROR / 含 WARNING 评分
   - 错误处理（空规则 / 空版图）
5. TestParasiticNet: 网表属性（2 个）

来源（规则 18 学术诚信）:
- Calibre xACT: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LFD: https://eda.sw.siemens.com/en-US/calibre/lfd/
- Banerjee ECE 225: https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
- Wang SPIE 63492Z: https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from polaris.verify.calibre_interface import (
    EPSILON_0,
    EPS_R_SIO2,
    RHO_CU,
    LayerSpec,
    Layout,
    LithoFriendlyChecker,
    LithoHotspot,
    LithoReport,
    LithoRule,
    ParasiticElement,
    ParasiticExtractor,
    ParasiticNet,
)


# ---------------------------------------------------------------------------
# 工具函数：构造矩形多边形
# ---------------------------------------------------------------------------
def _rect(x0: float, y0: float, w: float, h: float) -> np.ndarray:
    """构造轴对齐矩形多边形 (4, 2)。"""
    return np.array(
        [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]],
        dtype=float,
    )


def _cu_layer(
    gds_layer: tuple[int, int] = (11, 0),
    thickness_um: float = 0.5,
    dielectric_thickness_um: float = 1.0,
    eps_r_below: float = EPS_R_SIO2,
) -> LayerSpec:
    """构造标准 Cu 金属层（默认 0.5μm 厚、1μm 介质、SiO₂ 介电）。"""
    return LayerSpec(
        name="M1",
        gds_layer=gds_layer,
        thickness_um=thickness_um,
        resistivity_ohm_m=RHO_CU,
        eps_r_below=eps_r_below,
        dielectric_thickness_um=dielectric_thickness_um,
        is_conductor=True,
    )


# ---------------------------------------------------------------------------
# 1. TestLayerSpec — 物理层规格参数校验
# ---------------------------------------------------------------------------
class TestLayerSpec:
    """LayerSpec 数据类参数校验（规则 14.1 禁止 fall-back）。"""

    def test_valid_layer_spec(self):
        """合法参数：层规格正常创建。"""
        spec = _cu_layer()
        assert spec.name == "M1"
        assert spec.gds_layer == (11, 0)
        assert spec.thickness_um == pytest.approx(0.5)
        assert spec.resistivity_ohm_m == pytest.approx(RHO_CU)
        assert spec.is_conductor is True

    def test_negative_thickness_raises(self):
        """非法厚度：必须 raise ValueError（规则 14.1）。"""
        with pytest.raises(ValueError, match="厚度必须"):
            LayerSpec(
                name="BAD",
                gds_layer=(11, 0),
                thickness_um=-0.1,
                resistivity_ohm_m=RHO_CU,
                eps_r_below=EPS_R_SIO2,
                dielectric_thickness_um=1.0,
            )

    def test_negative_resistivity_for_conductor_raises(self):
        """导电层负电阻率：必须 raise ValueError。"""
        with pytest.raises(ValueError, match="电阻率必须"):
            LayerSpec(
                name="BAD",
                gds_layer=(11, 0),
                thickness_um=0.5,
                resistivity_ohm_m=-1.0,
                eps_r_below=EPS_R_SIO2,
                dielectric_thickness_um=1.0,
                is_conductor=True,
            )


# ---------------------------------------------------------------------------
# 2. TestLithoRule — 光刻规则参数校验
# ---------------------------------------------------------------------------
class TestLithoRule:
    """LithoRule 数据类参数校验。"""

    def test_valid_rule(self):
        """合法规则：正常创建。"""
        rule = LithoRule(
            name="WG_WIDTH", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="ERROR",
        )
        assert rule.name == "WG_WIDTH"
        assert rule.rule_type == "WIDTH"
        assert rule.severity == "ERROR"

    def test_invalid_rule_type_raises(self):
        """非法 rule_type：必须 raise ValueError。"""
        with pytest.raises(ValueError, match="rule_type"):
            LithoRule(
                name="BAD", rule_type="DENSITY",
                min_value=0.4, gds_layer=(1, 0),
            )

    def test_invalid_severity_raises(self):
        """非法 severity：必须 raise ValueError。"""
        with pytest.raises(ValueError, match="severity"):
            LithoRule(
                name="BAD", rule_type="WIDTH",
                min_value=0.4, gds_layer=(1, 0), severity="CRITICAL",
            )


# ---------------------------------------------------------------------------
# 3. TestParasiticExtractor — Calibre xACT 寄生 RC 提取
# ---------------------------------------------------------------------------
class TestParasiticExtractor:
    """ParasiticExtractor 寄生参数提取测试。"""

    def test_resistance_extraction(self):
        """电阻提取：R = ρ·L/(w·h)，与理论值误差 < 1%。

        理论: ρ=1.7e-8 Ω·m, L=10μm, w=1μm, h=0.5μm
              R = 1.7e-8×10e-6 / (1e-6×0.5e-6) = 0.34 Ω
        """
        spec = _cu_layer(thickness_um=0.5)
        # L=10μm, w=1μm 矩形
        poly = _rect(0.0, 0.0, 1.0, 10.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="test_r")
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        # 应至少 1 个电阻元件
        resistors = [e for e in net.elements if e.element_type == "RESISTOR"]
        assert len(resistors) == 1
        expected_r = RHO_CU * 10e-6 / (1e-6 * 0.5e-6)  # 0.34 Ω
        assert resistors[0].value == pytest.approx(expected_r, rel=0.01)
        assert net.total_resistance_ohm == pytest.approx(expected_r, rel=0.01)

    def test_parallel_plate_capacitance(self):
        """平行板电容: C_pp = ε₀·εᵣ·w·L/d（长网络无边缘电容）。

        使用长导线 L=100μm > 阈值 50μm，应只算 C_pp。
        理论: ε₀·3.9×1×100/1 × 1e-6 ≈ 3.453e-15 F
        """
        spec = _cu_layer(thickness_um=0.5, dielectric_thickness_um=1.0)
        poly = _rect(0.0, 0.0, 1.0, 100.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="test_cpp")
        extractor = ParasiticExtractor()  # 默认阈值 50μm
        net = extractor.extract_layout(layout, {"M1": spec})
        caps_to_gnd = [
            e for e in net.elements
            if e.element_type == "CAPACITOR" and e.node2 == "0"
        ]
        assert len(caps_to_gnd) == 1
        eps = EPSILON_0 * EPS_R_SIO2
        expected_c = eps * 1.0 * 100.0 / 1.0 * 1e-6  # ≈ 3.453e-15 F
        assert caps_to_gnd[0].value == pytest.approx(expected_c, rel=0.01)

    def test_fringe_capacitance_hybrid_engine(self):
        """*创新* 混合引擎：短网络 (L<阈值) 含边缘电容 C_fringe。

        短导线 L=10μm < 阈值 50μm，应同时含 C_pp 与 C_fringe。
        C_fringe = 2π·ε·L/arcosh(2d/H+1)
        """
        spec = _cu_layer(thickness_um=0.5, dielectric_thickness_um=1.0)
        poly = _rect(0.0, 0.0, 1.0, 10.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="test_fringe")
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        caps_to_gnd = [
            e for e in net.elements
            if e.element_type == "CAPACITOR" and e.node2 == "0"
        ]
        assert len(caps_to_gnd) == 1
        eps = EPSILON_0 * EPS_R_SIO2
        c_pp = eps * 1.0 * 10.0 / 1.0 * 1e-6
        arg = 2.0 * 1.0 / 0.5 + 1.0  # = 5.0
        c_fringe = 2.0 * math.pi * eps * 10.0 / math.acosh(arg) * 1e-6
        expected_total = c_pp + c_fringe
        # 必须严格大于纯 C_pp（验证混合引擎生效）
        assert caps_to_gnd[0].value > c_pp
        assert caps_to_gnd[0].value == pytest.approx(expected_total, rel=0.01)

    def test_long_network_no_fringe(self):
        """长网络 (L>阈值) 不含边缘电容，仅 C_pp（混合引擎验证）。"""
        spec = _cu_layer(thickness_um=0.5, dielectric_thickness_um=1.0)
        # L=60μm > 阈值 50μm
        poly = _rect(0.0, 0.0, 1.0, 60.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="test_long")
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        caps_to_gnd = [
            e for e in net.elements
            if e.element_type == "CAPACITOR" and e.node2 == "0"
        ]
        assert len(caps_to_gnd) == 1
        eps = EPSILON_0 * EPS_R_SIO2
        c_pp_only = eps * 1.0 * 60.0 / 1.0 * 1e-6
        # 长网络应等于纯 C_pp（无 fringe）
        assert caps_to_gnd[0].value == pytest.approx(c_pp_only, rel=0.01)

    def test_coupling_capacitance(self):
        """侧壁耦合电容: C_coupling = ε₀·εᵣ·h·L_overlap/s。

        两根平行导线，间距 0.5μm，重叠长度 10μm，h=0.5μm。
        理论: ε₀·3.9×0.5×10/0.5 × 1e-6 ≈ 3.453e-16 F
        """
        spec = _cu_layer(thickness_um=0.5, dielectric_thickness_um=1.0)
        # 两根 1μm 宽、10μm 长、间距 0.5μm 的平行导线
        poly1 = _rect(0.0, 0.0, 1.0, 10.0)
        poly2 = _rect(1.5, 0.0, 1.0, 10.0)  # 间距 = 0.5μm
        layout = Layout(
            polygons={spec.gds_layer: [poly1, poly2]}, name="test_coup"
        )
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        coupling_caps = [
            e for e in net.elements
            if e.element_type == "CAPACITOR" and "coup" in e.name
        ]
        assert len(coupling_caps) >= 1
        eps = EPSILON_0 * EPS_R_SIO2
        expected_c = eps * 0.5 * 10.0 / 0.5 * 1e-6  # ≈ 3.453e-16 F
        assert coupling_caps[0].value == pytest.approx(expected_c, rel=0.05)

    def test_spice_netlist_generation(self):
        """SPICE 子电路网表生成：对齐 Calibre xACT SPICE 输出格式。"""
        spec = _cu_layer()
        poly = _rect(0.0, 0.0, 1.0, 5.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="test_spice")
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        spice = net.to_spice()
        # 验证 SPICE 关键标记
        assert ".SUBCKT" in spice
        assert ".ENDS" in spice
        assert "parasitic_test_spice" in spice
        # 至少包含电阻和电容元件
        assert "R_" in spice
        assert "C_" in spice

    def test_extract_layout_empty_layer_map_raises(self):
        """空 layer_map：必须 raise ValueError（规则 14.1）。"""
        spec = _cu_layer()
        poly = _rect(0.0, 0.0, 1.0, 5.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="empty_map")
        extractor = ParasiticExtractor()
        with pytest.raises(ValueError, match="layer_map 不能为空"):
            extractor.extract_layout(layout, {})

    def test_extract_layout_empty_layout_raises(self):
        """空版图：必须 raise ValueError。"""
        spec = _cu_layer()
        layout = Layout(polygons={}, name="empty_layout")
        extractor = ParasiticExtractor()
        with pytest.raises(ValueError, match="版图多边形为空"):
            extractor.extract_layout(layout, {"M1": spec})

    def test_extract_missing_gds_raises(self):
        """缺失 GDS 文件：必须 raise FileNotFoundError。"""
        spec = _cu_layer()
        extractor = ParasiticExtractor()
        with pytest.raises(FileNotFoundError, match="GDS 文件不存在"):
            extractor.extract("/nonexistent/path.gds", {"M1": spec})

    def test_extract_empty_layer_map_raises(self):
        """extract() 入口空 layer_map：必须 raise ValueError。"""
        extractor = ParasiticExtractor()
        # GDS 路径存在与否不影响 layer_map 校验顺序
        with pytest.raises(ValueError, match="layer_map 不能为空"):
            extractor.extract("/tmp/dummy.gds", {})

    def test_invalid_hybrid_threshold_raises(self):
        """非法混合引擎阈值：必须 raise ValueError。"""
        with pytest.raises(ValueError, match="阈值必须"):
            ParasiticExtractor(hybrid_threshold_um=-10.0)

    def test_extraction_summary(self):
        """提取摘要：包含元素数、层数、混合阈值、来源 URL。"""
        spec = _cu_layer()
        poly = _rect(0.0, 0.0, 1.0, 5.0)
        layout = Layout(polygons={spec.gds_layer: [poly]}, name="summary")
        extractor = ParasiticExtractor()
        net = extractor.extract_layout(layout, {"M1": spec})
        summary = net.extraction_summary
        assert summary["element_count"] >= 1
        assert summary["layer_count"] == 1
        assert summary["hybrid_threshold_um"] == pytest.approx(50.0)
        # 至少 5 个学术来源 URL（规则 18）
        assert len(summary["sources"]) >= 5


# ---------------------------------------------------------------------------
# 4. TestLithoFriendlyChecker — Calibre LFD 光刻热点检测与评分
# ---------------------------------------------------------------------------
class TestLithoFriendlyChecker:
    """LithoFriendlyChecker 光刻热点检测测试。"""

    def test_width_hotspot_detection(self):
        """WIDTH 热点检测：宽度 < 阈值的多边形被标记。

        矩形 2μm×0.3μm，最小宽度 0.3μm，规则阈值 0.4μm → 应触发热点。
        """
        poly = _rect(0.0, 0.0, 2.0, 0.3)  # 宽度 0.3μm
        layout = Layout(polygons={(1, 0): [poly]}, name="width_hot")
        rule = LithoRule(
            name="WG_WIDTH", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="ERROR",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.hotspot_count >= 1
        assert report.error_count >= 1
        assert not report.passed

    def test_width_no_hotspot(self):
        """WIDTH 通过：宽度 ≥ 阈值不触发热点。"""
        poly = _rect(0.0, 0.0, 2.0, 1.0)  # 宽度 1.0μm
        layout = Layout(polygons={(1, 0): [poly]}, name="width_ok")
        rule = LithoRule(
            name="WG_WIDTH", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="ERROR",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.hotspot_count == 0
        assert report.passed

    def test_space_hotspot_detection(self):
        """SPACE 热点检测：间距 < 阈值被标记。

        两矩形间距 0.3μm，规则阈值 1.0μm → 应触发。
        """
        poly1 = _rect(0.0, 0.0, 1.0, 1.0)
        poly2 = _rect(1.3, 0.0, 1.0, 1.0)  # 间距 0.3μm
        layout = Layout(polygons={(1, 0): [poly1, poly2]}, name="space_hot")
        rule = LithoRule(
            name="WG_SPACE", rule_type="SPACE",
            min_value=1.0, gds_layer=(1, 0), severity="ERROR",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.hotspot_count >= 1
        assert report.error_count >= 1
        assert not report.passed

    def test_area_hotspot_detection(self):
        """AREA 热点检测：面积 < 阈值被标记。

        0.5μm×0.5μm 矩形面积 0.25μm²，规则阈值 0.5μm² → 应触发。
        """
        poly = _rect(0.0, 0.0, 0.5, 0.5)  # 面积 0.25μm²
        layout = Layout(polygons={(1, 0): [poly]}, name="area_hot")
        rule = LithoRule(
            name="WG_AREA", rule_type="AREA",
            min_value=0.5, gds_layer=(1, 0), severity="ERROR",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.hotspot_count >= 1
        assert report.error_count >= 1
        assert not report.passed

    def test_perfect_score_no_hotspots(self):
        """满分：所有规则通过 → score=100。"""
        poly = _rect(0.0, 0.0, 2.0, 2.0)  # 大方形，所有规则通过
        layout = Layout(polygons={(1, 0): [poly]}, name="perfect")
        rules = [
            LithoRule(
                name="WG_WIDTH", rule_type="WIDTH",
                min_value=0.5, gds_layer=(1, 0), severity="ERROR",
            ),
            LithoRule(
                name="WG_AREA", rule_type="AREA",
                min_value=1.0, gds_layer=(1, 0), severity="ERROR",
            ),
        ]
        checker = LithoFriendlyChecker()
        report = checker.check(layout, rules)
        assert report.hotspot_count == 0
        assert report.score == pytest.approx(100.0)
        assert report.passed

    def test_partial_score_with_errors(self):
        """含 ERROR 热点：score < 100，passed=False。"""
        poly = _rect(0.0, 0.0, 2.0, 0.3)  # 宽度 0.3μm < 0.4μm
        layout = Layout(polygons={(1, 0): [poly]}, name="err_score")
        rule = LithoRule(
            name="WG_WIDTH", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="ERROR",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.error_count >= 1
        assert report.score < 100.0
        assert not report.passed
        assert report.score >= 0.0

    def test_partial_score_with_warnings(self):
        """含 WARNING 热点：score < 100 但 passed=True（无 ERROR）。"""
        poly = _rect(0.0, 0.0, 2.0, 0.3)
        layout = Layout(polygons={(1, 0): [poly]}, name="warn_score")
        rule = LithoRule(
            name="WG_WIDTH_WARN", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="WARNING",
        )
        checker = LithoFriendlyChecker()
        report = checker.check(layout, [rule])
        assert report.warning_count >= 1
        assert report.error_count == 0
        assert report.passed  # 无 ERROR 即通过
        assert report.score < 100.0

    def test_empty_rules_raises(self):
        """空规则列表：必须 raise ValueError。"""
        poly = _rect(0.0, 0.0, 1.0, 1.0)
        layout = Layout(polygons={(1, 0): [poly]}, name="empty_rules")
        checker = LithoFriendlyChecker()
        with pytest.raises(ValueError, match="规则列表不能为空"):
            checker.check(layout, [])

    def test_empty_layout_raises(self):
        """空版图：必须 raise ValueError。"""
        layout = Layout(polygons={}, name="empty_layout")
        rule = LithoRule(
            name="WG_WIDTH", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0),
        )
        checker = LithoFriendlyChecker()
        with pytest.raises(ValueError, match="版图多边形为空"):
            checker.check(layout, [rule])

    def test_warning_weighted_half_of_error(self):
        """*创新* WARNING 权重 0.5 < ERROR 权重 1.0：相同热点数 WARNING 扣分更少。"""
        poly_err = _rect(0.0, 0.0, 2.0, 0.3)
        layout = Layout(polygons={(1, 0): [poly_err]}, name="cmp")
        rule_err = LithoRule(
            name="E", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="ERROR",
        )
        rule_warn = LithoRule(
            name="W", rule_type="WIDTH",
            min_value=0.4, gds_layer=(1, 0), severity="WARNING",
        )
        checker = LithoFriendlyChecker()
        report_err = checker.check(layout, [rule_err])
        report_warn = checker.check(layout, [rule_warn])
        # WARNING 扣分应小于 ERROR
        assert report_warn.score > report_err.score


# ---------------------------------------------------------------------------
# 5. TestParasiticNet — 网表属性
# ---------------------------------------------------------------------------
class TestParasiticNet:
    """ParasiticNet 数据类属性测试。"""

    def test_passed_property_no_error(self):
        """LithoReport.passed：无 ERROR 时返回 True。"""
        report = LithoReport(
            hotspots=[], total_checks=5,
            error_count=0, warning_count=2, score=80.0,
        )
        assert report.passed is True
        assert report.hotspot_count == 0

    def test_passed_property_with_error(self):
        """LithoReport.passed：有 ERROR 时返回 False。"""
        hotspot = LithoHotspot(
            rule_name="WG_WIDTH", rule_type="WIDTH",
            gds_layer=(1, 0), location=(1.0, 1.0),
            actual_value=0.3, expected_value=0.4,
            severity="ERROR", message="测试",
        )
        report = LithoReport(
            hotspots=[hotspot], total_checks=5,
            error_count=1, warning_count=0, score=80.0,
        )
        assert report.passed is False
        assert report.hotspot_count == 1

    def test_to_spice_empty_net(self):
        """ParasiticNet.to_spice：空网络生成基础 SPICE 框架。"""
        net = ParasiticNet(subckt_name="empty", nodes=["0", "in", "out"])
        spice = net.to_spice()
        assert ".SUBCKT empty 0 in out" in spice
        assert ".ENDS" in spice
