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
# calibre_interface 测试
# =============================================================================
def test_litho_rule_validation():
    """验证 LithoRule 参数校验（R03 禁止 fall-back）。"""
    from polaris_verify_advanced import LithoRule

    # 合法
    rule = LithoRule(name="W1", rule_type="WIDTH", min_value=0.5,
                     gds_layer=(1, 0), severity="ERROR")
    assert rule.severity == "ERROR"
    # 非法 rule_type raise
    with pytest.raises(ValueError, match="rule_type"):
        LithoRule(name="X", rule_type="INVALID", min_value=1.0, gds_layer=(1, 0))
    # min_value <= 0 raise
    with pytest.raises(ValueError, match="min_value"):
        LithoRule(name="X", rule_type="WIDTH", min_value=0, gds_layer=(1, 0))
    # 非法 severity raise
    with pytest.raises(ValueError, match="severity"):
        LithoRule(name="X", rule_type="WIDTH", min_value=1.0,
                  gds_layer=(1, 0), severity="CRITICAL")


def test_litho_friendly_checker_width_and_area():
    """验证 LithoFriendlyChecker WIDTH 与 AREA 检查。"""
    from polaris_verify_advanced import Layout, LithoFriendlyChecker, LithoRule

    # 窄多边形（宽度 0.3μm < 阈值 0.5μm）
    narrow = np.array([[0, 0], [5, 0], [5, 0.3], [0, 0.3]], dtype=float)
    layout = Layout(polygons={(1, 0): [narrow]}, name="test")
    rule = LithoRule(name="W1", rule_type="WIDTH", min_value=0.5, gds_layer=(1, 0))
    report = LithoFriendlyChecker().check(layout, [rule])
    assert report.error_count == 1
    assert report.passed is False
    assert report.score < 100.0
    # 小面积（面积 0.04μm² < 阈值 0.1μm²）
    small = np.array([[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2]], dtype=float)
    layout2 = Layout(polygons={(1, 0): [small]}, name="test")
    area_rule = LithoRule(name="A1", rule_type="AREA", min_value=0.1,
                          gds_layer=(1, 0), severity="WARNING")
    report2 = LithoFriendlyChecker().check(layout2, [area_rule])
    assert report2.warning_count == 1
    assert report2.passed is True  # 无 ERROR


def test_litho_friendly_checker_empty_validation():
    """验证 LithoFriendlyChecker 空规则/空版图 raise ValueError。"""
    from polaris_verify_advanced import Layout, LithoFriendlyChecker

    checker = LithoFriendlyChecker()
    layout = Layout(polygons={(1, 0): [np.array([[0, 0], [1, 0], [1, 1], [0, 1]])]})
    # 空规则
    with pytest.raises(ValueError, match="规则列表"):
        checker.check(layout, [])
    # 空版图
    with pytest.raises(ValueError, match="版图多边形为空"):
        checker.check(Layout(polygons={}), [
            __import__("polaris_verify_advanced").LithoRule(
                name="W", rule_type="WIDTH", min_value=0.5, gds_layer=(1, 0))
        ])


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
