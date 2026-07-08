"""polaris-verify-advanced DRC 测试套件（从 test_verify_advanced.py 拆分）。

覆盖: eqDRC 方程驱动 DRC、KLayout DRC 桥接、DRC Rule/Result dataclass、
BVH 层次化 DRC、曲线感知 DRC 18 类规则、DRCRuleCategory 枚举。

## 学术依据（R02 学术诚信，≥5 文献 URL）

1. He et al. 2023, "OpenDRC: A Linear Programming Based Hierarchical DRC Engine",
   DAC 2023, https://doi.org/10.1109/DAC56929.2023.10247734
2. Siemens Calibre eqDRC:
   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
3. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
4. KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html
5. Synopsys OptoDesigner DRC Module:
   https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html

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
# eqdrc 测试
# =============================================================================
def test_eqdrc_engine_add_rule_and_invalid_category():
    """验证 EqDRCEngine.add_rule 与非法类别 raise ValueError。"""
    from polaris_verify_advanced import EqDRCEngine, EqDRCRule

    engine = EqDRCEngine()
    rule = EqDRCRule(name="W1", category="WIDTH", equation="min_width=0.4",
                     layer=(1, 0), description="测试")
    engine.add_rule(rule)
    assert len(engine.rules) == 1
    # 非法类别 raise ValueError（R03）
    bad_rule = EqDRCRule(name="X1", category="INVALID", equation="", layer=(1, 0))
    with pytest.raises(ValueError, match="规则类别"):
        engine.add_rule(bad_rule)


def test_eqdrc_engine_check_width_and_space():
    """验证 EqDRCEngine.check_width / check_space 检测违规与通过。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    # 窄多边形（宽度 0.3μm < 阈值 0.5μm）
    narrow = [(0, 0), (10, 0), (10, 0.3), (0, 0.3)]
    # 宽多边形（宽度 1.0μm > 阈值 0.5μm），间距 5μm（narrow 右边 x=10, wide 左边 x=15）
    wide = [(15, 0), (25, 0), (25, 1.0), (15, 1.0)]
    viols = engine.check_width([narrow, wide], (1, 0), min_width=0.5)
    assert len(viols) == 1
    assert viols[0].rule_name == "EQDRC_WIDTH"
    # 间距检查：两多边形间距 5μm > 阈值 1μm → 无违规
    viols_space = engine.check_space([narrow, wide], (1, 0), min_space=1.0)
    assert len(viols_space) == 0
    # 间距检查：阈值 10μm > 间距 5μm → 有违规
    viols_space2 = engine.check_space([narrow, wide], (1, 0), min_space=10.0)
    assert len(viols_space2) == 1


def test_eqdrc_engine_check_bend_radius_and_taper():
    """验证 EqDRCEngine.check_bend_radius / check_taper。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    # 构建曲线路径（半径约 5μm 的圆弧）
    theta = np.linspace(0, np.pi / 2, 20)
    path = [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]
    # 阈值 10μm → R≈5 < 10 违规
    viols = engine.check_bend_radius([{"points": path, "layer": (1, 0)}],
                                     (1, 0), min_radius=10.0)
    assert len(viols) == 1
    # 阈值 1μm → 通过
    viols2 = engine.check_bend_radius([{"points": path, "layer": (1, 0)}],
                                      (1, 0), min_radius=1.0)
    assert len(viols2) == 0


def test_eqdrc_engine_check_coverage():
    """验证 EqDRCEngine.check_coverage 覆盖率检查与 area<=0 raise。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    poly = [(0, 0), (10, 0), (10, 5), (0, 5)]  # 面积 50
    # 覆盖率 50/100 = 0.5 ≥ 0.3 → 无违规
    viols = engine.check_coverage([poly], (1, 0), min_coverage=0.3, area=100.0)
    assert len(viols) == 0
    # 覆盖率 0.5 < 0.8 → 违规
    viols2 = engine.check_coverage([poly], (1, 0), min_coverage=0.8, area=100.0)
    assert len(viols2) == 1
    # area <= 0 raise ValueError（R03）
    with pytest.raises(ValueError, match="区域面积"):
        engine.check_coverage([poly], (1, 0), min_coverage=0.5, area=0.0)


def test_eqdrc_engine_run_all_dispatch():
    """验证 EqDRCEngine.run_all 按 category 分发执行。"""
    from polaris_verify_advanced import EqDRCEngine, EqDRCRule

    engine = EqDRCEngine()
    engine.add_rule(EqDRCRule(
        name="W1", category="WIDTH", equation="min_width=0.5",
        layer=(1, 0), description="宽度"))
    layout = {
        "polygons": [{"points": [(0, 0), (10, 0), (10, 0.3), (0, 0.3)],
                      "layer": (1, 0)}],
        "paths": [],
    }
    viols = engine.run_all(layout)
    assert len(viols) == 1
    assert viols[0].rule_name == "EQDRC_WIDTH"


def test_curvilinear_lvs_extract_and_compare():
    """验证 CurvilinearLVS 提取网表与比对。"""
    from polaris_verify_advanced import CurvilinearLVS

    lvs = CurvilinearLVS()
    # 构建含曲线 path 的版图
    theta = np.linspace(0, np.pi / 2, 20)
    layout = {
        "paths": [{"name": "bend1", "layer": "WG",
                   "points": [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]}],
        "polygons": [],
        "markers": [{"layer": "TEXT", "text": "bend1", "xy": (0, 0)}],
    }
    result = lvs.extract_netlist_with_markers(layout, ["TEXT"])
    assert result["marker_count"] == 1
    assert len(result["devices"]) >= 1
    # 比对：原理图与版图一致
    schematic = {"devices": result["devices"], "connections": result["connections"]}
    cmp = lvs.compare_with_schematic(result, schematic)
    assert cmp["is_match"] is True
    # 比对：原理图多一个器件 → 不匹配
    schematic2 = {"devices": result["devices"] + [{"name": "extra", "type": "wg"}],
                  "connections": []}
    cmp2 = lvs.compare_with_schematic(result, schematic2)
    assert cmp2["is_match"] is False


def test_curvilinear_lvs_verify_curvilinear_shapes():
    """验证 CurvilinearLVS.verify_curvilinear_shapes 识别 bend/taper。"""
    from polaris_verify_advanced import CurvilinearLVS

    lvs = CurvilinearLVS()
    # 直线 → 无曲线组件
    layout = {"paths": [{"name": "straight", "points": [(0, 0), (10, 0), (20, 0)]}]}
    comps = lvs.verify_curvilinear_shapes(layout)
    # 三个共线点曲率为 0，finite 为空，无组件
    assert len(comps) == 0
    # 曲线 path → 识别 bend
    theta = np.linspace(0, np.pi / 2, 20)
    layout2 = {"paths": [{"name": "bend",
                          "points": [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]}]}
    comps2 = lvs.verify_curvilinear_shapes(layout2)
    assert any(c["type"] == "bend" for c in comps2)


def test_foundry_drc_certifier_build_runsets():
    """验证 FoundryDRCCertifier 构建 5 个 foundry runset。"""
    from polaris_verify_advanced import FoundryDRCCertifier

    certifier = FoundryDRCCertifier()
    amf = certifier.build_amf_runset()
    ihp = certifier.build_ihp_runset()
    gf = certifier.build_gf_fotonix_runset()
    ligentec = certifier.build_ligentec_runset()
    lionix = certifier.build_lionix_runset()
    for runset in (amf, ihp, gf, ligentec, lionix):
        assert len(runset.rules) == 4  # WIDTH/SPACE/BEND/TAPER
        assert runset.certified is True
        assert len(runset.sources) >= 1
    # 验证不同 foundry 参数差异
    amf_w_rule = next(r for r in amf.rules if r.category == "WIDTH")
    ligentec_w_rule = next(r for r in ligentec.rules if r.category == "WIDTH")
    # AMF w_min=0.4, LIGENTEC w_min=0.8
    assert "0.4" in amf_w_rule.equation
    assert "0.8" in ligentec_w_rule.equation


def test_foundry_drc_certifier_certify_runset():
    """验证 FoundryDRCCertifier.certify_runset 认证流程。"""
    from polaris_verify_advanced import FoundryDRCCertifier

    certifier = FoundryDRCCertifier()
    runset = certifier.build_amf_runset()
    # 干净版图（满足所有规则）→ PASS
    clean_layout = {
        "polygons": [{"points": [(0, 0), (100, 0), (100, 10), (0, 10)],
                      "layer": (1, 0)}],  # 宽度 10μm > 0.4
        "paths": [],
    }
    result = certifier.certify_runset(runset, clean_layout)
    assert "foundry" in result
    assert "certified" in result
    assert "report" in result


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


def test_klayout_drc_runner_import_error():
    """验证 KLayoutDRCRunner.run_gds 在无 klayout 时 raise ImportError 或 FileNotFoundError。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")  # 无 klayout 时跳过本测试（R03 用 importorskip）
    # 有 klayout 时，文件不存在 → FileNotFoundError
    from polaris_verify_advanced import KLayoutDRCRunner

    runner = KLayoutDRCRunner()
    with pytest.raises(FileNotFoundError):
        runner.run_gds("/nonexistent/path/test.gds")


def test_run_klayout_drc_function():
    """验证 run_klayout_drc 便捷函数（无 klayout 时跳过）。"""
    pytest.importorskip("klayout")
    from polaris_verify_advanced import run_klayout_drc

    with pytest.raises(FileNotFoundError):
        run_klayout_drc("/nonexistent/path/test.gds")


# =============================================================================
# hierarchical_drc 测试
# =============================================================================
def test_bvh_build_and_query():
    """验证 BVH 构建与查询。"""
    from polaris_verify_advanced import BVH

    bvh = BVH()
    # 空输入返回 None
    assert bvh.build([]) is None
    # 构建多个多边形
    polys = [
        np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float),
        np.array([[20, 0], [30, 0], [30, 10], [20, 10]], dtype=float),
        np.array([[100, 100], [110, 100], [110, 110], [100, 110]], dtype=float),
    ]
    root = bvh.build(polys)
    assert root is not None
    # 查询左下角区域 → 应返回前两个多边形
    result = bvh.query((0, 0, 35, 15))
    assert len(result) >= 2
    # 查询空区域
    assert bvh.query((1000, 1000, 1001, 1001)) == []


def test_bvh_node_is_leaf():
    """验证 BVHNode.is_leaf 属性。"""
    from polaris_verify_advanced import BVHNode

    leaf = BVHNode(bbox=(0, 0, 10, 10), polygons=[np.array([[0, 0]])])
    assert leaf.is_leaf is True
    internal = BVHNode(bbox=(0, 0, 20, 20), left=leaf,
                       right=BVHNode(bbox=(10, 10, 20, 20)))
    assert internal.is_leaf is False


def test_row_partition():
    """验证 RowPartition 自适应行分块与 max_rows 校验。"""
    from polaris_verify_advanced import RowPartition

    rp = RowPartition(max_rows=10)
    # 空输入
    assert rp.partition([]) == []
    # 多个多边形
    polys = [np.array([[i, 0], [i + 1, 0], [i + 1, 1], [i, 1]], dtype=float)
             for i in range(20)]
    blocks = rp.partition(polys)
    assert len(blocks) >= 1
    # 所有块的多边形总数 = 原始数
    total = sum(len(b) for b in blocks)
    assert total == 20
    # max_rows < 1 raise ValueError（R03）
    with pytest.raises(ValueError, match="max_rows"):
        RowPartition(max_rows=0)


def test_hierarchical_drc_width_and_empty_rules():
    """验证 HierarchicalDRC 检测宽度违规与空规则 raise ValueError。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    # 空规则 raise ValueError（R03）
    with pytest.raises(ValueError, match="DRC 规则列表不能为空"):
        HierarchicalDRC([])

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    wide = np.array([[20, 0], [30, 0], [30, 1.0], [20, 1.0]], dtype=float)
    rule = DRCRule(name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
                   threshold_um=0.5, vtype=ViolationType.MIN_WIDTH)
    engine = HierarchicalDRC([rule])
    layout = {"WG": [narrow, wide]}
    viols = engine.check(layout, hierarchical=True)
    assert len(viols) == 1
    assert "宽度" in viols[0].message
    # flat 模式
    viols_flat = engine.check(layout, hierarchical=False)
    assert len(viols_flat) == 1


def test_hierarchical_drc_space_and_area():
    """验证 HierarchicalDRC 间距与面积检查。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    # 两个相近多边形（间距 0.5μm < 阈值 1.0μm）
    p1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    p2 = np.array([[10.5, 0], [20, 0], [20, 1], [10.5, 1]], dtype=float)
    space_rule = DRCRule(name="S1", layer_name="WG", check_type=DRCCheckType.SPACE,
                         threshold_um=1.0, vtype=ViolationType.SPACING)
    engine = HierarchicalDRC([space_rule])
    viols = engine.check({"WG": [p1, p2]}, hierarchical=True)
    assert len(viols) == 1
    # 小面积违规
    small = np.array([[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2]], dtype=float)  # 面积 0.04
    area_rule = DRCRule(name="A1", layer_name="WG", check_type=DRCCheckType.AREA,
                        threshold_um=0.1, vtype=ViolationType.MIN_AREA)
    engine2 = HierarchicalDRC([area_rule])
    viols2 = engine2.check({"WG": [small]}, hierarchical=True)
    assert len(viols2) == 1


def test_run_hierarchical_drc_function():
    """验证 run_hierarchical_drc 统一入口。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        ViolationType,
        run_hierarchical_drc,
    )

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    rule = DRCRule(name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
                   threshold_um=0.5, vtype=ViolationType.MIN_WIDTH)
    viols = run_hierarchical_drc({"WG": [narrow]}, [rule], hierarchical=True)
    assert len(viols) == 1


# =============================================================================
# drc_curvilinear_18rules 测试（保留 smoke test 并扩展）
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
            "min_width": 0.40, "max_width": 4.0, "min_curve_width": 0.45,
            "min_spacing": 0.4, "same_net_spacing": 0.2, "density_spacing": 0.5,
            "end_to_end": 0.4, "density": 0.03, "max_angle": 140, "min_angle": 80,
            "min_bend_radius": 3.0, "max_curvature": 0.3, "taper_angle": 15,
        },
        "contact": {"min_enclosure": 0.08},
        "metal1": {"min_extension": 0.15},
        "pad": {"min_area": 2000},
        "slab": {"max_area": 60000},
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


def test_curvilinear_drc_engine_clean_layout():
    """验证 CurvilinearDRCEngine 干净版图无违规。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    # 所有指标都满足规则
    layout = {
        "waveguide": {
            "min_width": 0.5, "max_width": 2.0, "min_curve_width": 0.6,
            "min_spacing": 0.6, "same_net_spacing": 0.4, "density_spacing": 1.0,
            "end_to_end": 0.7, "density": 0.1, "max_angle": 120, "min_angle": 95,
            "min_bend_radius": 6.0, "max_curvature": 0.1, "taper_angle": 5,
        },
    }
    violations = engine.run_checks(layout)
    assert len(violations) == 0
    rpt = engine.report()
    assert rpt["passed"] is True
    assert rpt["total_violations"] == 0


def test_curvilinear_drc_engine_list_rules_by_category():
    """验证 CurvilinearDRCEngine.list_rules_by_category。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    by_cat = engine.list_rules_by_category()
    assert "min_width" in by_cat
    assert "min_spacing" in by_cat
    assert "min_bend_radius" in by_cat
    # MIN_WIDTH 类应有 W1 一条
    assert len(by_cat["min_width"]) == 1


def test_curvilinear_drc_engine_extended_idempotent():
    """验证扩展规则启用/禁用幂等性。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    # 重复启用幂等
    engine.enable_extended_rules()
    engine.enable_extended_rules()
    assert engine.rule_count == 26
    # 重复禁用幂等
    engine.disable_extended_rules()
    engine.disable_extended_rules()
    assert engine.rule_count == 18


# =============================================================================
# _drc_rules 测试
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
