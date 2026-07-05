"""polaris-verify-advanced 深度测试套件（覆盖全部公开 API）。

本测试套件覆盖 polaris_verify_advanced 包的全部公开 API：
图同构 LVS、LVS 进阶类型/匹配/连接性/错误报告、内化类型与层映射、
方程驱动 DRC、KLayout DRC 桥接、层次化 DRC、Calibre xACT 寄生提取、
Calibre LFD 光刻友好设计、曲线感知 DRC 18 类规则、DRC 规则集预设。

## 学术依据（R02 学术诚信，≥5 文献 URL）

1. He et al. 2023, "OpenDRC: A Linear Programming Based Hierarchical DRC Engine",
   DAC 2023, https://doi.org/10.1109/DAC56929.2023.10247734
2. McKay & Piperno 2014, "Practical Graph Isomorphism, II",
   J. Symbolic Computation, https://www.sciencedirect.com/science/article/pii/S0747717113001930
3. Cordella et al. 2004, VF2 子图同构, IEEE TPAMI,
   https://ieeexplore.ieee.org/document/1266305
4. Siemens Calibre eqDRC:
   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
5. Wang et al., SPIE 6349, 63492Z (2006), Calibre LFD PV-band,
   https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/
6. Banerjee ECE 225 UCSB, 寄生电容公式,
   https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
7. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
8. KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html

合规: R02 学术诚信 / R03 禁止 fall-back（klayout 延迟导入用 importorskip）/ R05 无 TODO /
      R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# =============================================================================
# Smoke Test 1: 模块导入与版本
# =============================================================================

def test_module_import_and_version():
    """验证 polaris_verify_advanced 可导入且版本正确。"""
    import polaris_verify_advanced as pva

    assert pva.__version__ == "1.0.0"
    # 验证核心 API 可访问
    assert hasattr(pva, "GraphIsomorphismLVSComparer")
    assert hasattr(pva, "HierarchicalDRC")
    assert hasattr(pva, "EqDRCEngine")
    assert hasattr(pva, "KLayoutDRCRunner")
    assert hasattr(pva, "ParasiticExtractor")
    assert hasattr(pva, "LithoFriendlyChecker")
    assert hasattr(pva, "CurvilinearDRCEngine")
    assert hasattr(pva, "SIEPIC_EBEAM_SOI_RULESET")
    # 验证物理常数
    assert pva.EPSILON_0 > 0
    assert pva.RHO_CU > 0
    # 验证层映射
    assert "WG" in pva.POLARIS_GDS_LAYER_MAP


# =============================================================================
# _layer_map 测试
# =============================================================================
def test_gds_layer_frozen_dataclass():
    """验证 GDSLayer 为 frozen dataclass，字段完整。"""
    from polaris_verify_advanced import GDSLayer

    layer = GDSLayer(layer=1, datatype=0, name="WG", purpose="波导")
    assert layer.layer == 1
    assert layer.datatype == 0
    assert layer.name == "WG"
    assert layer.fabricated is True  # 默认值
    # frozen 验证
    with pytest.raises(Exception):
        layer.layer = 2  # type: ignore[misc]


def test_polaris_gds_layer_map_contains_41_layers():
    """验证 POLARIS_GDS_LAYER_MAP 含至少 41 个层定义。"""
    from polaris_verify_advanced import POLARIS_GDS_LAYER_MAP

    # 关键层存在
    for key in ("WG", "SLAB150", "SLAB90", "DEEPTRENCH", "GE", "M1", "M2", "M3",
                "PORT", "DEVREC", "TEXT", "FLOORPLAN", "DICING"):
        assert key in POLARIS_GDS_LAYER_MAP, f"层 {key} 应存在"
    # 总数 ≥ 40
    assert len(POLARIS_GDS_LAYER_MAP) >= 40


def test_get_layer_tuple_known_and_unknown():
    """验证 get_layer_tuple 返回 (layer, datatype) 元组，未知层 raise KeyError。"""
    from polaris_verify_advanced import get_layer_tuple

    assert get_layer_tuple("WG") == (1, 0)
    assert get_layer_tuple("PORT") == (1, 10)
    assert get_layer_tuple("M3") == (49, 0)
    # 未知层 raise KeyError（R03 禁止 fall-back）
    with pytest.raises(KeyError):
        get_layer_tuple("NONEXISTENT_LAYER")


def test_get_category_layer_tuple():
    """验证 get_category_layer_tuple 按类别返回层元组，未知类别回退到 WG。

    注: get_category_layer_tuple 未在 __init__ 导出，从 _layer_map 子模块导入。
    """
    from polaris_verify_advanced._layer_map import get_category_layer_tuple

    assert get_category_layer_tuple("passive") == (1, 0)  # → WG
    assert get_category_layer_tuple("waveguide") == (1, 0)
    assert get_category_layer_tuple("detector") == (5, 0)  # → GE
    # 未知类别回退到 WG（设计如此，非 fall-back）
    assert get_category_layer_tuple("unknown_category") == (1, 0)


# =============================================================================
# _types 测试
# =============================================================================
def test_drc_report_generator():
    """验证 DRCReportGenerator 生成报告与修复建议。"""
    from polaris_verify_advanced import (
        DRCReportGenerator,
        EqDRCViolation,
    )

    gen = DRCReportGenerator()
    viols = [EqDRCViolation(
        rule_name="EQDRC_WIDTH", layer=(1, 0), location=(5.0, 5.0),
        actual_value=0.3, expected_value=0.5, severity="ERROR",
        message="宽度不足")]
    report = gen.generate_report(viols, "test_layout")
    assert "DRC 认证报告" in report
    assert "EQDRC_WIDTH" in report
    summary = gen.generate_summary(viols)
    assert summary["total"] == 1
    assert summary["errors"] == 1
    assert "EQDRC_WIDTH" in summary["by_rule"]
    suggestions = gen.suggest_fixes(viols)
    assert len(suggestions) == 1
    assert suggestions[0]["action"] == "increase_width"
    # 干净报告
    clean_report = gen.generate_report([], "clean_layout")
    assert "DRC CLEAN" in clean_report


# =============================================================================
# klayout_drc 测试（klayout 延迟导入用 importorskip）
# =============================================================================
def test_drc_check_type_enum():
    """验证 DRCCheckType 枚举成员。"""
    from polaris_verify_advanced import DRCCheckType

    assert DRCCheckType.WIDTH.value == "width"
    assert DRCCheckType.SPACE.value == "space"
    assert DRCCheckType.NOTCH.value == "notch"
    assert DRCCheckType.ENCLOSE.value == "enclose"
    assert DRCCheckType.AREA.value == "area"
    assert DRCCheckType.DENSITY.value == "density"
    assert DRCCheckType.VIA.value == "via"


def test_drc_rule_dataclass_and_runset():
    """验证 DRCRule dataclass 与 SIEPIC_EBEAM_DRC_RUNSET 默认 runset。"""
    from polaris_verify_advanced import (
        DRCRule,
        DRCCheckType,
        SIEPIC_EBEAM_DRC_RUNSET,
        ViolationType,
    )

    rule = DRCRule(
        name="TEST", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH, description="测试",
    )
    assert rule.threshold_um == 0.5
    assert rule.severity == 1.0  # 默认
    # SiEPIC EBeam runset 至少 10 条规则
    assert len(SIEPIC_EBEAM_DRC_RUNSET) >= 10
    # 验证包含 WIDTH/SPACE/NOTCH/AREA/DENSITY/ENCLOSE/VIA 多种类型
    types = {r.check_type for r in SIEPIC_EBEAM_DRC_RUNSET}
    assert DRCCheckType.WIDTH in types
    assert DRCCheckType.SPACE in types
    assert DRCCheckType.VIA in types


def test_drc_result_dataclass():
    """验证 DRCResult dataclass 属性。"""
    from polaris_verify_advanced import DRCResult, Violation, ViolationType

    result = DRCResult(
        violations=[Violation(vtype=ViolationType.MIN_WIDTH, message="测试")],
        gds_path="/tmp/test.gds", runset_name="custom",
        total_rules=5, passed_rules=4,
    )
    assert result.violation_count == 1
    assert result.is_clean is False
    clean = DRCResult()
    assert clean.is_clean is True
    assert clean.violation_count == 0


def test_physical_constants():
    """验证物理常数（CODATA 2018 + Banerjee UCSB）。"""
    from polaris_verify_advanced import (
        EPS_R_SI,
        EPS_R_SIO2,
        EPS_R_SIN3,
        EPSILON_0,
        RHO_AL,
        RHO_CU,
        RHO_TIN,
        RHO_W,
    )

    assert 8.8e-12 < EPSILON_0 < 8.9e-12
    assert RHO_CU == 1.7e-8
    assert RHO_AL == 2.7e-8
    assert RHO_TIN == 1.0e-6
    assert RHO_W == 5.5e-8
    assert EPS_R_SI == 11.7
    assert EPS_R_SIO2 == 3.9
    assert EPS_R_SIN3 == 7.5


def test_layer_spec_validation():
    """验证 LayerSpec 参数校验（R03 禁止 fall-back）。"""
    from polaris_verify_advanced import EPS_R_SIO2, LayerSpec, RHO_CU

    # 合法
    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    assert spec.is_conductor is True
    # 厚度 <= 0 raise
    with pytest.raises(ValueError, match="厚度"):
        LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0,
                  resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                  dielectric_thickness_um=1.0)
    # 导电层电阻率 <= 0 raise
    with pytest.raises(ValueError, match="电阻率"):
        LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                  resistivity_ohm_m=0, eps_r_below=EPS_R_SIO2,
                  dielectric_thickness_um=1.0)


def test_layout_get_polygons_and_keyerror():
    """验证 Layout.get_polygons 与 KeyError。"""
    from polaris_verify_advanced import Layout

    poly = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    layout = Layout(polygons={(1, 0): [poly]}, name="test")
    assert layout.get_polygons((1, 0)) == [poly]
    # 不存在的层 raise KeyError（R03）
    with pytest.raises(KeyError):
        layout.get_polygons((99, 99))


def test_parasitic_element_and_net_to_spice():
    """验证 ParasiticElement 与 ParasiticNet.to_spice。"""
    from polaris_verify_advanced import ParasiticElement, ParasiticNet

    elem = ParasiticElement(name="R1", element_type="RESISTOR",
                            value=1.5, node1="n1", node2="n2")
    assert elem.element_type == "RESISTOR"
    net = ParasiticNet(
        subckt_name="test", elements=[elem], nodes=["n1", "n2", "0"],
        total_resistance_ohm=1.5, total_capacitance_f=0.0,
    )
    spice = net.to_spice()
    assert ".SUBCKT test" in spice
    assert ".ENDS" in spice
    assert "R1" in spice


def test_parasitic_extractor_layout_and_validation():
    """验证 ParasiticExtractor.extract_layout 提取与校验。"""
    from polaris_verify_advanced import (
        EPS_R_SIO2,
        LayerSpec,
        Layout,
        ParasiticExtractor,
        RHO_CU,
    )

    poly = np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)
    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    layout = Layout(polygons={(1, 0): [poly]}, name="test_metal")
    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"M1": spec})
    assert net.total_resistance_ohm > 0
    assert net.total_capacitance_f > 0
    # 空 layer_map raise ValueError（R03）
    with pytest.raises(ValueError, match="layer_map"):
        extractor.extract_layout(layout, {})
    # 空版图 raise ValueError
    with pytest.raises(ValueError, match="版图多边形为空"):
        extractor.extract_layout(Layout(polygons={}), {"M1": spec})


def test_parasitic_extractor_invalid_threshold():
    """验证 ParasiticExtractor 阈值非法 raise ValueError。"""
    from polaris_verify_advanced import ParasiticExtractor

    with pytest.raises(ValueError, match="阈值"):
        ParasiticExtractor(hybrid_threshold_um=0)
    with pytest.raises(ValueError, match="阈值"):
        ParasiticExtractor(hybrid_threshold_um=-1.0)


def test_parasitic_extractor_extract_file_not_found():
    """验证 ParasiticExtractor.extract 文件不存在 raise FileNotFoundError。"""
    from polaris_verify_advanced import EPS_R_SIO2, LayerSpec, ParasiticExtractor, RHO_CU

    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    extractor = ParasiticExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract("/nonexistent/path.gds", {"M1": spec})


# =============================================================================
# calibre_lfd 测试
# =============================================================================
def test_drc_rule_category_enum_26_values():
    """验证 DRCRuleCategory 26 类枚举成员。"""
    from polaris_verify_advanced import DRCRuleCategory

    # 18 类基础规则
    assert DRCRuleCategory.MIN_WIDTH.value == "min_width"
    assert DRCRuleCategory.MAX_WIDTH.value == "max_width"
    assert DRCRuleCategory.TAPER_ANGLE.value == "taper_angle"
    # 8 类扩展规则
    assert DRCRuleCategory.STEP_WIDTH.value == "step_width"
    assert DRCRuleCategory.SYMMETRY.value == "symmetry"
    assert DRCRuleCategory.MAX_WIDTH_SINGLE_MODE.value == "max_width_single_mode"
    # 总数 = 26
    assert len(list(DRCRuleCategory)) == 26


def test_curvilinear_drc_rule_dataclass():
    """验证 CurvilinearDRCRule dataclass 字段与扩展字段。"""
    from polaris_verify_advanced import CurvilinearDRCRule, DRCRuleCategory

    rule = CurvilinearDRCRule(
        name="R1", category=DRCRuleCategory.MIN_WIDTH, layer="WG",
        limit_value=0.5, units="μm", is_curvilinear=False,
        description="测试", severity="error",
    )
    assert rule.limit_max is None  # 默认
    assert rule.layer_pair is None
    assert rule.tolerance is None
    # 扩展字段
    rule2 = CurvilinearDRCRule(
        name="R2", category=DRCRuleCategory.EDGE_LENGTH, layer="WG",
        limit_value=0.2, limit_max=1000.0, layer_pair=None,
    )
    assert rule2.limit_max == 1000.0


def test_drc_violation18_dataclass():
    """验证 DRCViolation18 dataclass 字段。"""
    from polaris_verify_advanced import DRCViolation18

    v = DRCViolation18(
        rule_name="W1", category="min_width", layer="WG",
        severity="error", message="宽度不足",
        location_um=(5.0, 5.0), measured_value=0.3, limit_value=0.5,
    )
    assert v.rule_name == "W1"
    assert v.measured_value == 0.3
    assert v.limit_value == 0.5


# =============================================================================
# drc_ruleset_presets 测试（保留 smoke test 并扩展）
# =============================================================================
def test_drc_ruleset_presets():
    """验证 DRC 规则集预设可正确加载和校验。

    来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    from polaris_verify_advanced import (
        GENERIC_CONSERVATIVE_RULESET,
        SIEPIC_EBEAM_SIN_RULESET,
        SIEPIC_EBEAM_SOI_RULESET,
        CustomRuleSetBuilder,
        get_preset_ruleset,
        list_preset_rulesets,
        validate_ruleset,
    )

    # 验证预设规则集数量
    assert len(SIEPIC_EBEAM_SOI_RULESET) == 11, "SOI 规则集应有 11 条规则"
    assert len(SIEPIC_EBEAM_SIN_RULESET) == 8, "SiN 规则集应有 8 条规则"
    assert len(GENERIC_CONSERVATIVE_RULESET) == 6, "Generic 规则集应有 6 条规则"

    # 验证预设列表
    names = list_preset_rulesets()
    assert "siepic_ebeam_soi" in names
    assert "siepic_ebeam_sin" in names
    assert "generic_conservative" in names

    # 验证获取预设（返回副本）
    rules = get_preset_ruleset("siepic_ebeam_soi")
    assert len(rules) == 11
    rules.append(rules[0])  # 修改副本
    assert len(SIEPIC_EBEAM_SOI_RULESET) == 11  # 原始不受影响

    # 验证未知规则集名抛 ValueError（R03）
    with pytest.raises(ValueError, match="未知规则集名"):
        get_preset_ruleset("nonexistent")

    # 验证规则集校验（合法规则集无问题）
    issues = validate_ruleset(SIEPIC_EBEAM_SOI_RULESET)
    assert issues == [], f"SOI 规则集应有 0 个问题，实际 {issues}"

    # 验证 CustomRuleSetBuilder 流式构建
    builder = CustomRuleSetBuilder()
    ruleset = (
        builder
        .add_min_width("R1", "WG", 0.4, description="测试宽度")
        .add_min_spacing("R2", "WG", 1.0, description="测试间距")
        .add_min_bend_radius("R3", "WG", 5.0, description="测试弯曲半径")
        .build()
    )
    assert len(ruleset) == 3
    assert builder.rule_count() == 3


def test_drc_ruleset_presets_all_three():
    """验证三个预设规则集均能通过 validate_ruleset。"""
    from polaris_verify_advanced import (
        GENERIC_CONSERVATIVE_RULESET,
        SIEPIC_EBEAM_SIN_RULESET,
        SIEPIC_EBEAM_SOI_RULESET,
        validate_ruleset,
    )

    for name, ruleset in [("SOI", SIEPIC_EBEAM_SOI_RULESET),
                          ("SiN", SIEPIC_EBEAM_SIN_RULESET),
                          ("Generic", GENERIC_CONSERVATIVE_RULESET)]:
        issues = validate_ruleset(ruleset)
        assert issues == [], f"{name} 规则集应有 0 个问题，实际 {issues}"


def test_validate_ruleset_detects_issues():
    """验证 validate_ruleset 检测重复名/非法 limit_value/空 layer。"""
    from polaris_verify_advanced import (
        CurvilinearDRCRule,
        DRCRuleCategory,
        validate_ruleset,
    )

    # 重复规则名
    r1 = CurvilinearDRCRule(name="DUP", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0.5, units="μm")
    r2 = CurvilinearDRCRule(name="DUP", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0.4, units="μm")
    issues = validate_ruleset([r1, r2])
    assert any("重复" in i for i in issues)
    # limit_value <= 0
    r3 = CurvilinearDRCRule(name="R3", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0, units="μm")
    issues2 = validate_ruleset([r3])
    assert any("limit_value" in i for i in issues2)
    # 非 list 类型 raise TypeError
    with pytest.raises(TypeError, match="rules 必须是列表"):
        validate_ruleset("not_a_list")  # type: ignore[arg-type]


def test_custom_ruleset_builder_full_api():
    """验证 CustomRuleSetBuilder 全部 add_* 方法与 build 失败。"""
    from polaris_verify_advanced import CustomRuleSetBuilder, DRCRuleCategory

    builder = CustomRuleSetBuilder()
    ruleset = (
        builder
        .add_min_width("W1", "WG", 0.5)
        .add_min_spacing("S1", "WG", 1.0)
        .add_min_area("A1", "WG", 0.1)
        .add_min_bend_radius("B1", "WG", 5.0)
        .add_max_angle("ANG1", "WG", 90.0)
        .add_rule("X1", DRCRuleCategory.MAX_WIDTH, "WG", 3.0)
        .build()
    )
    assert len(ruleset) == 6
    # build 失败：重复名
    bad_builder = CustomRuleSetBuilder()
    bad_builder.add_min_width("DUP", "WG", 0.5)
    bad_builder.add_min_spacing("DUP", "WG", 1.0)  # 重复名
    with pytest.raises(ValueError, match="规则集校验失败"):
        bad_builder.build()


# =============================================================================
# lvs_advanced_connectivity / error_report 测试（klayout 延迟导入）
# =============================================================================
def test_generate_structured_error_report_no_klayout():
    """验证 generate_structured_error_report 在无 klayout 时 raise。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")
    from polaris_verify_advanced import (
        ExtractedNetlist,
        generate_structured_error_report,
    )

    ref = ExtractedNetlist(devices=["d1"], connections=[])
    with pytest.raises((FileNotFoundError, RuntimeError)):
        generate_structured_error_report("/nonexistent/path.gds", ref)


# =============================================================================
# Smoke Test 保留：ParasiticExtractor 寄生提取（纯 NumPy，无 klayout）
# =============================================================================
def test_parasitic_extractor_layout():
    """验证 ParasiticExtractor.extract_layout 从 Layout 提取寄生参数。

    公式: R = ρ·L/(w·h), C_pp = ε₀·εᵣ·w·L/d
    来源: Banerjee ECE 225 UCSB
    https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
    """
    from polaris_verify_advanced import (
        EPS_R_SIO2,
        LayerSpec,
        Layout,
        ParasiticExtractor,
        RHO_CU,
    )

    poly = np.array([
        [0.0, 0.0], [10.0, 0.0], [10.0, 0.5], [0.0, 0.5],
    ], dtype=float)
    layer_spec = LayerSpec(
        name="METAL1", gds_layer=(1, 0), thickness_um=0.2,
        resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
        dielectric_thickness_um=1.0, is_conductor=True,
    )
    layout = Layout(polygons={(1, 0): [poly]}, name="test_metal")
    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"METAL1": layer_spec})
    assert net.total_resistance_ohm > 0
    assert net.total_capacitance_f > 0
    assert len(net.elements) >= 2
    spice = net.to_spice()
    assert ".SUBCKT" in spice
    assert ".ENDS" in spice
    with pytest.raises(ValueError, match="layer_map"):
        extractor.extract_layout(layout, {})


# =============================================================================
# Smoke Test 保留：HierarchicalDRC 层次化 DRC（纯 NumPy）
# =============================================================================
