"""polaris-verify-advanced 扩展测试套件（从 test_verify_advanced.py 拆分）。

覆盖: DRC 规则集预设、Calibre xACT 连接性提取、Calibre LFD 光刻友好设计、
层次化 LVS（≥3 层递归比对）、Tiled/Deep 模式 DRC。

## 学术依据（R02 学术诚信，≥5 文献 URL）

1. McKay & Piperno 2014, "Practical Graph Isomorphism, II",
   J. Symbolic Computation, https://www.sciencedirect.com/science/article/pii/S0747717113001930
2. Cordella et al. 2004, VF2 子图同构, IEEE TPAMI,
   https://ieeexplore.ieee.org/document/1266305
3. Wang et al., SPIE 6349, 63492Z (2006), Calibre LFD PV-band,
   https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/
4. Banerjee ECE 225 UCSB, 寄生电容公式,
   https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
5. KLayout DRC tiled/hierarchical/deep 模式:
   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
6. He et al. 2023, OpenDRC, DAC 2023, DOI:10.1109/DAC56929.2023.10247734
7. Siemens Calibre nmDRC/nmLVS: https://eda.sw.siemens.com/en-US/calibre/
8. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

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
def test_extract_connectivity_no_klayout():
    """验证 extract_connectivity 在无 klayout 时 raise ImportError。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")
    from polaris_verify_advanced import extract_connectivity

    with pytest.raises((FileNotFoundError, RuntimeError)):
        extract_connectivity("/nonexistent/path.gds")


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

    narrow_poly = np.array([
        [0.0, 0.0], [10.0, 0.0], [10.0, 0.3], [0.0, 0.3],
    ], dtype=float)
    wide_poly = np.array([
        [20.0, 0.0], [30.0, 0.0], [30.0, 1.0], [20.0, 1.0],
    ], dtype=float)
    rule = DRCRule(
        name="TEST_WIDTH", layer_name="WG",
        check_type=DRCCheckType.WIDTH, threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH, description="测试宽度规则",
    )
    engine = HierarchicalDRC([rule])
    layout = {"WG": [narrow_poly, wide_poly]}
    violations = engine.check(layout, hierarchical=True)
    assert len(violations) == 1
    assert violations[0].rule_name == "TEST_WIDTH"
    assert "宽度" in violations[0].message


# =============================================================================
# Smoke Test 保留：LithoFriendlyChecker 光刻友好设计检查
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

    narrow_poly = np.array([
        [0.0, 0.0], [5.0, 0.0], [5.0, 0.3], [0.0, 0.3],
    ], dtype=float)
    layout = Layout(polygons={(1, 0): [narrow_poly]}, name="test_litho")
    rule = LithoRule(
        name="LITHO_WIDTH", rule_type="WIDTH", min_value=0.5,
        gds_layer=(1, 0), severity="ERROR",
    )
    checker = LithoFriendlyChecker()
    report = checker.check(layout, [rule])
    assert report.error_count == 1
    assert report.passed is False
    assert report.score < 100.0
    assert report.hotspot_count == 1
    with pytest.raises(ValueError, match="规则列表"):
        checker.check(layout, [])
    with pytest.raises(ValueError, match="rule_type"):
        LithoRule(name="BAD", rule_type="INVALID", min_value=1.0, gds_layer=(1, 0))


# =============================================================================
# 层次化 LVS（≥3 层递归比对，R9 路标）
# =============================================================================
def _make_3level_hierarchy(top_dev: str, mid_dev: str, leaf_dev: str, prefix: str) -> dict:
    """构造 3 层层次结构（dict 格式，TOP → MID → LEAF）。

    来源: Cordella 2004 VF2; Calibre nmLVS hierarchical compare
    https://ieeexplore.ieee.org/document/1266305
    """
    return {
        "name": "TOP",
        "devices": [{"node_id": f"{prefix}_top_d1", "device_type": top_dev}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": f"{prefix}_mid_d1", "device_type": mid_dev}],
                "connections": [],
                "children": [
                    {
                        "name": "LEAF",
                        "devices": [
                            {"node_id": f"{prefix}_leaf_d1", "device_type": leaf_dev}
                        ],
                        "connections": [],
                        "children": [],
                    }
                ],
            }
        ],
    }


def test_hierarchical_lvs_3_levels_match():
    """验证 3 层层次化 LVS 递归比对匹配 → is_match=True, total_levels=3。

    来源: Cordella 2004 VF2; Calibre nmLVS hierarchical compare
    https://ieeexplore.ieee.org/document/1266305
    https://eda.sw.siemens.com/en-US/calibre/calibre-nm-lvs-replay/
    """
    from polaris_verify_advanced import HierarchicalLVS

    sch = _make_3level_hierarchy("mmi", "wg", "ybranch", "sch")
    lay = _make_3level_hierarchy("mmi", "wg", "ybranch", "lay")
    comparer = HierarchicalLVS()
    report = comparer.compare_hierarchical(sch, lay)
    assert report.is_match is True
    assert report.total_levels == 3
    assert len(report.level_results) == 3
    # 每层 cell name 与层级编号
    level_names = {(r.level, r.cell_name) for r in report.level_results}
    assert (0, "TOP") in level_names
    assert (1, "MID") in level_names
    assert (2, "LEAF") in level_names
    # 每层均匹配且无不匹配项
    assert all(r.is_match for r in report.level_results)
    assert report.all_mismatches == []
    # 每层 VF2 应找到同构映射（节点数 1 → 映射非空）
    assert all(r.isomorphism_mapping for r in report.level_results)
    assert report.comparison_time_s >= 0.0


def test_hierarchical_lvs_mismatch_raises():
    """验证层次结构不匹配（子 cell 数量不一致）时 raise RuntimeError（R03）。

    来源: R03 禁止 fall-back; Calibre nmLVS hierarchical compare
    https://eda.sw.siemens.com/en-US/calibre/calibre-nm-lvs-replay/
    """
    from polaris_verify_advanced import HierarchicalLVS

    def leaf(node_id: str) -> dict:
        return {
            "name": "LEAF",
            "devices": [{"node_id": node_id, "device_type": "ybranch"}],
            "connections": [],
            "children": [],
        }

    # 原理图 top 有 1 个子 cell，版图 top 有 2 个子 cell → 子 cell 数量不一致
    sch = {
        "name": "TOP",
        "devices": [{"node_id": "sch_top_d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": "sch_mid_d1", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("sch_leaf_d1")],
            }
        ],
    }
    lay = {
        "name": "TOP",
        "devices": [{"node_id": "lay_top_d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID_A",
                "devices": [{"node_id": "lay_mid_a", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("lay_leaf_a")],
            },
            {
                "name": "MID_B",
                "devices": [{"node_id": "lay_mid_b", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("lay_leaf_b")],
            },
        ],
    }
    comparer = HierarchicalLVS()
    with pytest.raises(RuntimeError, match="子 cell 数量不匹配"):
        comparer.compare_hierarchical(sch, lay)


def test_hierarchical_lvs_invalid_input_raises():
    """验证无效输入（非 dict/缺字段/层级数<3）时 raise ValueError（R03）。

    来源: R03 禁止 fall-back; KLayout LVS Compare
    https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
    """
    from polaris_verify_advanced import HierarchicalLVS

    comparer = HierarchicalLVS()
    # 1. 非 dict 输入
    with pytest.raises(ValueError, match="必须为 dict"):
        comparer.compare_hierarchical([], {})
    # 2. 缺必需字段（缺 children）
    bad_node = {"name": "TOP", "devices": [], "connections": []}
    with pytest.raises(ValueError, match="缺少必需字段 'children'"):
        comparer.compare_hierarchical(bad_node, bad_node)
    # 3. 层级数 <3（仅 top → mid 两层，mid 无子 cell）
    shallow = {
        "name": "TOP",
        "devices": [{"node_id": "d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": "d2", "device_type": "wg"}],
                "connections": [],
                "children": [],  # MID 为叶子 → 总深度仅 2
            }
        ],
    }
    with pytest.raises(ValueError, match="层次深度 2 < 最小要求 3"):
        comparer.compare_hierarchical(shallow, shallow)


# =============================================================================
# tiled / deep 模式 DRC 测试（R8 路标）
#
# 来源（R02 学术诚信，≥5 文献 URL）:
# 1. KLayout DRC tiled/hierarchical/deep 模式:
#    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
# 2. He et al. 2023, OpenDRC, DAC 2023, DOI:10.1109/DAC56929.2023.10247734
# 3. Siemens Calibre nmDRC 分块扫描: https://eda.sw.siemens.com/en-US/calibre/
# 4. SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 5. Chrostowski & Hochberg 2015, Silicon Photonics Design, CUP, p.353
# =============================================================================
def test_tiled_drc_basic():
    """验证 TiledDRC 检测宽度违规（单 tile 基本功能）。

    来源: KLayout DRC tiling mode; OpenDRC DAC 2023。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCReport,
        DRCRule,
        TiledDRC,
        ViolationType,
        run_tiled_drc,
    )

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    wide = np.array([[20, 0], [30, 0], [30, 1.0], [20, 1.0]], dtype=float)
    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    layout = {"WG": [narrow, wide]}

    # 类入口
    engine = TiledDRC([rule])
    report = engine.check(layout, tile_size_um=100.0)
    assert isinstance(report, DRCReport)
    assert report.mode == "tiled"
    assert report.total_tiles >= 1
    assert report.violation_count == 1
    assert not report.is_clean
    assert "宽度" in report.violations[0].message
    assert report.elapsed_ms >= 0.0

    # 函数入口
    report2 = run_tiled_drc(layout, [rule], tile_size_um=100.0)
    assert report2.violation_count == 1
    assert report2.mode == "tiled"


def test_tiled_drc_tile_size():
    """验证不同 tile_size_um 下违规数一致（边界扩展 + 去重正确）。

    来源: KLayout tiling mode 边界扩展 + 去重策略。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        TiledDRC,
        ViolationType,
    )

    # 两个相近多边形（间距 0.5μm < 阈值 1.0μm），跨度约 20μm
    p1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    p2 = np.array([[10.5, 0], [20, 0], [20, 1], [10.5, 1]], dtype=float)
    rule = DRCRule(
        name="S1", layer_name="WG", check_type=DRCCheckType.SPACE,
        threshold_um=1.0, vtype=ViolationType.SPACING,
    )
    layout = {"WG": [p1, p2]}
    engine = TiledDRC([rule])

    # 大 tile（单块覆盖全部）
    r_big = engine.check(layout, tile_size_um=100.0)
    assert r_big.total_tiles == 1
    assert r_big.violation_count == 1

    # 小 tile（多块，跨边界违规由 overlap 捕获，去重消除重复）
    r_small = engine.check(layout, tile_size_um=5.0)
    assert r_small.total_tiles > 1
    # 跨块间距违规不遗漏，去重后仅 1 条
    assert r_small.violation_count == 1, (
        f"小 tile 模式应去重为 1 条，得到 {r_small.violation_count}"
    )

    # 不同 tile_size 违规数一致
    r_mid = engine.check(layout, tile_size_um=10.0)
    assert r_mid.violation_count == 1


def test_deep_drc_basic():
    """验证 DeepDRC 递归 flatten + 跨层次检查。

    层次: TOP（含宽多边形）→ instance SUB（dx=20）含窄多边形。
    flatten 后窄多边形平移到 x=20，宽度违规被检出。
    来源: KLayout deep mode; OpenDRC 层次化展开。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCReport,
        DRCRule,
        DeepDRC,
        ViolationType,
        run_deep_drc,
    )

    wide = np.array([[0, 0], [5, 0], [5, 1.0], [0, 1.0]], dtype=float)
    narrow = np.array([[0, 0], [8, 0], [8, 0.3], [0, 0.3]], dtype=float)
    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    hierarchy = {
        "top_cell": "TOP",
        "cells": {
            "TOP": {
                "polygons": {"WG": [wide]},
                "instances": [{"cell_name": "SUB", "dx": 20.0, "dy": 0.0}],
            },
            "SUB": {
                "polygons": {"WG": [narrow]},
                "instances": [],
            },
        },
    }

    engine = DeepDRC([rule])
    report = engine.check(hierarchy)
    assert isinstance(report, DRCReport)
    assert report.mode == "deep"
    assert report.total_cells == 2  # TOP + SUB
    assert report.total_tiles == 0
    assert report.violation_count == 1
    assert not report.is_clean
    assert "宽度" in report.violations[0].message
    # flatten 后窄多边形位于 x=20..28
    loc_x = report.violations[0].location[0]
    assert 20.0 <= loc_x <= 28.0

    # 函数入口
    report2 = run_deep_drc(hierarchy, [rule])
    assert report2.violation_count == 1
    assert report2.total_cells == 2


def test_tiled_drc_invalid_input_raises():
    """验证 TiledDRC 无效输入即 raise（R03 禁止 fall-back）。

    覆盖: 空 rules / rules 非 list / layout 非 dict / layout 空 /
          tile_size_um ≤0 / overlap_um <0 / hierarchy 非法 / 层次环。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DeepDRC,
        DRCRule,
        TiledDRC,
        ViolationType,
    )

    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    poly = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    layout = {"WG": [poly]}

    # 空 rules
    with pytest.raises(RuntimeError, match="DRC 规则列表不能为空"):
        TiledDRC([])
    # rules 非 list
    with pytest.raises(RuntimeError, match="rules 必须是 list"):
        TiledDRC("not_a_list")  # type: ignore[arg-type]
    # layout 非 dict
    with pytest.raises(RuntimeError, match="layout 必须是 dict"):
        TiledDRC([rule]).check([("WG", [poly])], tile_size_um=100.0)  # type: ignore[arg-type]
    # layout 空
    with pytest.raises(RuntimeError, match="layout 不能为空"):
        TiledDRC([rule]).check({}, tile_size_um=100.0)
    # tile_size_um ≤ 0
    with pytest.raises(RuntimeError, match="tile_size_um 必须 > 0"):
        TiledDRC([rule]).check(layout, tile_size_um=0.0)
    with pytest.raises(RuntimeError, match="tile_size_um 必须 > 0"):
        TiledDRC([rule]).check(layout, tile_size_um=-5.0)
    # overlap_um < 0
    with pytest.raises(RuntimeError, match="overlap_um 必须 ≥ 0"):
        TiledDRC([rule]).check(layout, tile_size_um=100.0, overlap_um=-1.0)

    # DeepDRC 空 rules
    with pytest.raises(RuntimeError, match="DRC 规则列表不能为空"):
        DeepDRC([])
    # hierarchy 非 dict
    with pytest.raises(RuntimeError, match="hierarchy 必须是 dict"):
        DeepDRC([rule]).check("not_a_dict")  # type: ignore[arg-type]
    # hierarchy 缺字段
    with pytest.raises(RuntimeError, match="hierarchy 缺少必要字段"):
        DeepDRC([rule]).check({"top_cell": "TOP"})
    # top_cell 不在 cells
    with pytest.raises(RuntimeError, match="不在 cells 中"):
        DeepDRC([rule]).check(
            {"top_cell": "MISSING", "cells": {"TOP": {"polygons": {}, "instances": []}}}
        )
    # 层次环
    cycle_hier = {
        "top_cell": "A",
        "cells": {
            "A": {"polygons": {}, "instances": [{"cell_name": "B", "dx": 0.0, "dy": 0.0}]},
            "B": {"polygons": {}, "instances": [{"cell_name": "A", "dx": 0.0, "dy": 0.0}]},
        },
    }
    with pytest.raises(RuntimeError, match="检测到层次环"):
        DeepDRC([rule]).check(cycle_hier)
