"""polaris-verify-advanced 子模块 smoke test。

验证核心迁移功能可正常导入和运行。不依赖 klayout（延迟导入），
仅依赖 numpy（pyproject.toml 已声明）。

学术依据: 见各模块 docstring（R02 学术诚信）。
合规: R03 禁止 fall-back / R05 无 TODO / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import numpy as np
import pytest


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
# Smoke Test 2: CurvilinearDRCEngine 18 类规则
# =============================================================================
def test_curvilinear_drc_engine_18_rules():
    """验证 CurvilinearDRCEngine 注册 18 类规则并能检测违规。

    来源: Synopsys OptoDesigner DRC Module
    https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    assert engine.rule_count == 18, f"应有 18 条规则，实际 {engine.rule_count}"

    # 验证曲线规则数量（W3/CV1/CV2/CV3/ANG3 共 5 条）
    curvilinear = [r for r in engine._rules if r.is_curvilinear]
    assert len(curvilinear) == 5, f"应有 5 条曲线规则，实际 {len(curvilinear)}"

    # 制造全违规版图数据
    layout = {
        "waveguide": {
            "min_width": 0.40,       # < 0.45 违规
            "max_width": 4.0,        # > 3.0 违规
            "min_curve_width": 0.45,  # < 0.50 违规
            "min_spacing": 0.4,      # < 0.5 违规
            "same_net_spacing": 0.2,  # < 0.3 违规
            "density_spacing": 0.5,  # < 0.8 违规
            "end_to_end": 0.4,       # < 0.6 违规
            "density": 0.03,         # < 0.05 违规
            "max_angle": 140,        # > 135 违规
            "min_angle": 80,         # < 90 违规
            "min_bend_radius": 3.0,  # < 5.0 违规
            "max_curvature": 0.3,    # > 0.2 违规
            "taper_angle": 15,       # > 10 违规
        },
        "contact": {"min_enclosure": 0.08},  # < 0.1 违规
        "metal1": {"min_extension": 0.15},   # < 0.2 违规
        "pad": {"min_area": 2000},           # < 2500 违规
        "slab": {"max_area": 60000},         # > 50000 违规
    }
    violations = engine.run_checks(layout)
    assert len(violations) == 18, f"应有 18 条违规，实际 {len(violations)}"

    rpt = engine.report()
    assert rpt["total_rules"] == 18
    assert rpt["errors"] > 0
    assert rpt["passed"] is False

    # 验证扩展规则启用
    engine.enable_extended_rules()
    assert engine.rule_count == 26
    assert engine.extended_rules_enabled is True
    engine.disable_extended_rules()
    assert engine.rule_count == 18
    assert engine.extended_rules_enabled is False


# =============================================================================
# Smoke Test 3: ParasiticExtractor 寄生提取（纯 NumPy，无 klayout）
# =============================================================================
def test_parasitic_extractor_layout():
    """验证 ParasiticExtractor.extract_layout 从 Layout 提取寄生参数。

    公式: R = ρ·L/(w·h), C_pp = ε₀·εᵣ·w·L/d
    来源: Banerjee ECE 225 UCSB
    https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
    """
    from polaris_verify_advanced import (
        EPSILON_0,
        EPS_R_SIO2,
        LayerSpec,
        Layout,
        ParasiticExtractor,
        RHO_CU,
    )

    # 构建简单版图：一条 10μm × 0.5μm 的铜导线
    poly = np.array([
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 0.5],
        [0.0, 0.5],
    ], dtype=float)
    layer_spec = LayerSpec(
        name="METAL1",
        gds_layer=(1, 0),
        thickness_um=0.2,
        resistivity_ohm_m=RHO_CU,
        eps_r_below=EPS_R_SIO2,
        dielectric_thickness_um=1.0,
        is_conductor=True,
    )
    layout = Layout(polygons={(1, 0): [poly]}, name="test_metal")

    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"METAL1": layer_spec})

    # 验证电阻 R = ρ·L/(w·h) = 1.7e-8 × 10 / (0.5 × 0.2) (单位转换后)
    assert net.total_resistance_ohm > 0, "电阻应 > 0"
    # 验证电容 C > 0
    assert net.total_capacitance_f > 0, "电容应 > 0"
    # 验证元件数（1 电阻 + 1 对地电容）
    assert len(net.elements) >= 2, f"应至少 2 个元件，实际 {len(net.elements)}"
    # 验证 SPICE 网表输出
    spice = net.to_spice()
    assert ".SUBCKT" in spice
    assert ".ENDS" in spice

    # 验证空 layer_map 抛 ValueError（R03 禁止 fall-back）
    with pytest.raises(ValueError, match="layer_map"):
        extractor.extract_layout(layout, {})


# =============================================================================
# Smoke Test 4: HierarchicalDRC 层次化 DRC（纯 NumPy）
# =============================================================================
def test_hierarchical_drc_width_violation():
    """验证 HierarchicalDRC 检测宽度违规。

    来源: OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    # 构建一个窄多边形（宽度 0.3μm < 阈值 0.5μm）
    narrow_poly = np.array([
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 0.3],
        [0.0, 0.3],
    ], dtype=float)
    # 构建一个宽多边形（宽度 1.0μm > 阈值 0.5μm）
    wide_poly = np.array([
        [20.0, 0.0],
        [30.0, 0.0],
        [30.0, 1.0],
        [20.0, 1.0],
    ], dtype=float)

    rule = DRCRule(
        name="TEST_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="测试宽度规则",
    )
    engine = HierarchicalDRC([rule])
    layout = {"WG": [narrow_poly, wide_poly]}
    violations = engine.check(layout, hierarchical=True)

    # 应检测到 1 条违规（窄多边形）
    assert len(violations) == 1, f"应有 1 条违规，实际 {len(violations)}"
    assert violations[0].rule_name == "TEST_WIDTH"
    assert "宽度" in violations[0].message


# =============================================================================
# Smoke Test 5: DRC 规则集预设
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


# =============================================================================
# Smoke Test 6: LithoFriendlyChecker 光刻友好设计检查
# =============================================================================
def test_litho_friendly_checker():
    """验证 LithoFriendlyChecker 检测光刻热点并计算评分。

    来源: Wang et al., SPIE 6349, 63492Z (2006), doi:10.1117/12.685727
    """
    from polaris_verify_advanced import (
        Layout,
        LithoFriendlyChecker,
        LithoRule,
    )

    # 构建窄多边形（宽度 0.3μm < 阈值 0.5μm → 违规）
    narrow_poly = np.array([
        [0.0, 0.0],
        [5.0, 0.0],
        [5.0, 0.3],
        [0.0, 0.3],
    ], dtype=float)
    layout = Layout(polygons={(1, 0): [narrow_poly]}, name="test_litho")

    rule = LithoRule(
        name="LITHO_WIDTH",
        rule_type="WIDTH",
        min_value=0.5,
        gds_layer=(1, 0),
        severity="ERROR",
    )
    checker = LithoFriendlyChecker()
    report = checker.check(layout, [rule])

    assert report.error_count == 1, f"应有 1 个 ERROR，实际 {report.error_count}"
    assert report.passed is False
    assert report.score < 100.0, "有违规时评分应 < 100"
    assert report.hotspot_count == 1

    # 验证空规则列表抛 ValueError（R03）
    with pytest.raises(ValueError, match="规则列表"):
        checker.check(layout, [])

    # 验证非法 rule_type 抛 ValueError（R03）
    with pytest.raises(ValueError, match="rule_type"):
        LithoRule(name="BAD", rule_type="INVALID", min_value=1.0, gds_layer=(1, 0))
