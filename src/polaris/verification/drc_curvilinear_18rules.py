"""M4-R22/R24: 曲线感知 DRC 18 类规则扩展 + M4 交付清单。

对齐 Synopsys OptoDesigner DRC 模块（18 类曲线感知规则）+ Siemens Calibre nmDRC。

R181-R200 拆分: 几何工具函数迁移到 ``_drc_geometry.py``，规则定义（枚举与
dataclass）迁移到 ``_drc_rules.py``。本文件仅保留 ``CurvilinearDRCEngine``
引擎与 ``M4Deliverable`` 交付清单，并通过 ``__all__`` re-export 保持向后兼容。

学术依据:
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则，对齐本模块 18 类枚举）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- KLayout DRC Reference (曲线感知规则)
  URL: https://www.klayout.de/doc-qt5/manual/drc.html
- Siemens Calibre nmDRC
  URL: https://www.siemens.com/en-us/products/ic/ic-custom/verification/calibre-nmdrc/
- OpenROAD DRC Engine
  URL: https://openroad.readthedocs.io/en/latest/main/src/drt/README.html
- OpenTitan M4 RTL Freeze Milestone 定义（里程碑退出准则：D3/V2(S) + CDC/RDC + 时序优化）
  URL: https://opentitan.org/book/doc/project_governance/project_milestone_definitions.html
- ONAP M4 Code Freeze Milestone Checklist Template（交付清单模板：CSIT/Jenkins/Daily Build 验证）
  URL: https://wiki.onap.org/display/DW/M4+Deliverable+for+Code+Freeze+Milestone+Checklist+Template
- Luceda IPKISS DRC tape-out 验证（曲线 DRC 实践：重叠层/锐角检测）
  URL: https://academy.lucedaphotonics.com/training/topical_training/tape_out_prep_verification/drc/drc
- Cao et al. 2015, Silicon Photonics Design Rule Checking (curvilinear 验证方法学)
  URL: https://www.semiconductorpackagingnews.com/uploads/1/Advancing_silicon_photonics_verification_innovation__4_.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

from typing import Any

# R181-R200 拆分: 几何工具迁移到 _drc_geometry，规则定义迁移到 _drc_rules。
# 本文件仅保留 CurvilinearDRCEngine 引擎与 M4Deliverable 交付清单。
# re-export 保持向后兼容（tests 直接从本模块导入私有几何函数与规则类）。
from ._drc_geometry import (  # noqa: F401
    _edge_to_edge_distance,
    _layer_density,
    _point_in_polygon,
    _point_segment_distance,
    _polygon_angles,
    _polygon_area,
    _polygon_bbox,
    _polygon_curvature,
    _polygon_end_edges,
    _polygon_extension,
    _polygon_min_enclosure,
    _polygon_min_width,
    _polygon_pair_min_distance,
    _polygon_taper_angle,
    _segment_segment_distance,
    _segments_intersect,
)
from ._drc_rules import (  # noqa: F401
    CurvilinearDRCRule,
    DRCRuleCategory,
    DRCViolation18,
)
# R181-R200 拆分: 18 类 _check_*_geo 几何检查方法迁移到 _drc_checks Mixin。
from ._drc_checks import _DRCGeometricChecksMixin  # noqa: F401
# R181-R200 拆分: M4Deliverable 与验证辅助函数迁移到 _drc_m4_deliverable。
# 延迟导入在 _drc_m4_deliverable 内部处理（避免循环依赖）。
from ._drc_m4_deliverable import (  # noqa: F401
    M4Deliverable,
    _load_foundry_platforms_module,
    _src_file_exists,
    _test_file_exists,
    _verify_curvilinear_rules_count,
    _verify_drc_18_rules,
    _verify_drc_rules_total_ge_200,
    _verify_foundry_platform_count,
)

__all__ = [
    "CurvilinearDRCRule",
    "DRCRuleCategory",
    "DRCViolation18",
    "_edge_to_edge_distance",
    "_polygon_end_edges",
    "_polygon_extension",
    "CurvilinearDRCEngine",
    "M4Deliverable",
]


class CurvilinearDRCEngine(_DRCGeometricChecksMixin):
    """曲线感知 DRC 引擎（18 类规则）。

    对齐: Synopsys OptoDesigner DRC Module + KLayout 曲线 DRC + Calibre nmDRC。
    支持: 直线/曲线版图，弯曲半径检查，曲率连续性，锥形角度。
    几何实现: 基于计算几何算法（旋转卡尺、三点圆拟合、鞋带公式等）
    实现真实的多边形几何 DRC 检查。

    R181-R200 拆分: 18 类 ``_check_*_geo`` 几何检查方法 + ``run_geometric_checks``
    公共入口迁移到 ``_DRCGeometricChecksMixin``（``_drc_checks.py``）。
    本类保留: 规则注册、预计算值检查（``run_checks``）、报告生成。

    学术依据（≥5 文献 URL）:
    - KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024, http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    - imec Curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
    """

    def __init__(self) -> None:
        self._rules: list[CurvilinearDRCRule] = []
        self._violations: list[DRCViolation18] = []
        self._register_18_rules()

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self._violations if v.severity == "error")

    def _register_18_rules(self) -> None:
        """注册 18 类标准 DRC 规则。"""
        rules = [
            # 宽度类 (3)
            CurvilinearDRCRule("W1_min_wg_width", DRCRuleCategory.MIN_WIDTH,
                               "waveguide", 0.45, "μm", False, "波导最小宽度"),
            CurvilinearDRCRule("W2_max_wg_width", DRCRuleCategory.MAX_WIDTH,
                               "waveguide", 3.0, "μm", False, "波导最大宽度"),
            CurvilinearDRCRule("W3_min_curve_width", DRCRuleCategory.MIN_WIDTH_CURVE,
                               "waveguide", 0.50, "μm", True, "曲线段最小宽度（加宽补偿）"),
            # 间距类 (4)
            CurvilinearDRCRule("S1_min_wg_spacing", DRCRuleCategory.MIN_SPACING,
                               "waveguide", 0.5, "μm", False, "波导最小间距"),
            CurvilinearDRCRule("S2_same_net_spacing", DRCRuleCategory.MIN_SPACING_SAME_NET,
                               "waveguide", 0.3, "μm", False, "同网络间距"),
            CurvilinearDRCRule("S3_density_spacing", DRCRuleCategory.MIN_SPACING_DENSITY,
                               "waveguide", 0.8, "μm", False, "高密度区间距"),
            CurvilinearDRCRule("S4_end_to_end", DRCRuleCategory.MIN_END_TO_END,
                               "waveguide", 0.6, "μm", False, "端到端间距"),
            # 包围类 (2)
            CurvilinearDRCRule("E1_contact_enc", DRCRuleCategory.MIN_ENCLOSURE,
                               "contact", 0.1, "μm", False, "接触孔包围"),
            CurvilinearDRCRule("E2_metal_ext", DRCRuleCategory.MIN_EXTENSION,
                               "metal1", 0.2, "μm", False, "金属延伸"),
            # 面积类 (3)
            CurvilinearDRCRule("A1_min_pad_area", DRCRuleCategory.MIN_AREA,
                               "pad", 2500, "μm²", False, "焊盘最小面积"),
            CurvilinearDRCRule("A2_max_slab_area", DRCRuleCategory.MAX_AREA,
                               "slab", 50000, "μm²", False, "SLAB 最大面积"),
            CurvilinearDRCRule("A3_min_density", DRCRuleCategory.MIN_DENSITY,
                               "waveguide", 0.05, "", False, "波导最小密度"),
            # 角度类 (3)
            CurvilinearDRCRule("ANG1_max_corner", DRCRuleCategory.MAX_ANGLE,
                               "waveguide", 135, "°", False, "最大拐角"),
            CurvilinearDRCRule("ANG2_min_corner", DRCRuleCategory.MIN_ANGLE,
                               "waveguide", 90, "°", False, "最小拐角"),
            CurvilinearDRCRule("ANG3_acute", DRCRuleCategory.ACUTE_ANGLE,
                               "waveguide", 89, "°", True, "锐角禁止"),
            # 曲线类 (3)
            CurvilinearDRCRule("CV1_min_bend_r", DRCRuleCategory.MIN_BEND_RADIUS,
                               "waveguide", 5.0, "μm", True, "最小弯曲半径"),
            CurvilinearDRCRule("CV2_max_curvature", DRCRuleCategory.MAX_CURVATURE,
                               "waveguide", 0.2, "1/μm", True, "最大曲率"),
            CurvilinearDRCRule("CV3_taper_angle", DRCRuleCategory.TAPER_ANGLE,
                               "waveguide", 10, "°", True, "锥形最大角度"),
        ]
        self._rules = rules

    def run_checks(self, layout_data: dict[str, Any]) -> list[DRCViolation18]:
        """运行全部 18 类规则检查。

        Args:
            layout_data: {layer: {"features": [...], "min_width": x, ...}}
        """
        self._violations = []
        for rule in self._rules:
            self._check_rule(rule, layout_data)
        return self._violations

    def _check_rule(self, rule: CurvilinearDRCRule, layout: dict[str, Any]) -> None:
        layer_data = layout.get(rule.layer, {})
        if not layer_data:
            return

        cat = rule.category
        val = rule.limit_value

        if cat == DRCRuleCategory.MIN_WIDTH:
            w = layer_data.get("min_width", float("inf"))
            if w < val:
                self._add_violation(rule, f"最小宽度 {w:.3f} < {val}", w, val)
        elif cat == DRCRuleCategory.MAX_WIDTH:
            w = layer_data.get("max_width", 0)
            if w > val:
                self._add_violation(rule, f"最大宽度 {w:.3f} > {val}", w, val)
        elif cat == DRCRuleCategory.MIN_WIDTH_CURVE:
            cw = layer_data.get("min_curve_width", float("inf"))
            if cw < val:
                self._add_violation(rule, f"曲线最小宽度 {cw:.3f} < {val}", cw, val)
        elif cat == DRCRuleCategory.MIN_SPACING:
            s = layer_data.get("min_spacing", float("inf"))
            if s < val:
                self._add_violation(rule, f"最小间距 {s:.3f} < {val}", s, val)
        elif cat == DRCRuleCategory.MIN_SPACING_SAME_NET:
            s = layer_data.get("same_net_spacing", float("inf"))
            if s < val:
                self._add_violation(rule, f"同网络间距 {s:.3f} < {val}", s, val)
        elif cat == DRCRuleCategory.MIN_SPACING_DENSITY:
            s = layer_data.get("density_spacing", float("inf"))
            if s < val:
                self._add_violation(rule, f"高密度区间距 {s:.3f} < {val}", s, val)
        elif cat == DRCRuleCategory.MIN_END_TO_END:
            s = layer_data.get("end_to_end", float("inf"))
            if s < val:
                self._add_violation(rule, f"端到端间距 {s:.3f} < {val}", s, val)
        elif cat == DRCRuleCategory.MIN_ENCLOSURE:
            e = layer_data.get("min_enclosure", float("inf"))
            if e < val:
                self._add_violation(rule, f"包围 {e:.3f} < {val}", e, val)
        elif cat == DRCRuleCategory.MIN_EXTENSION:
            e = layer_data.get("min_extension", float("inf"))
            if e < val:
                self._add_violation(rule, f"延伸 {e:.3f} < {val}", e, val)
        elif cat == DRCRuleCategory.MIN_AREA:
            a = layer_data.get("min_area", float("inf"))
            if a < val:
                self._add_violation(rule, f"最小面积 {a:.0f} < {val}", a, val)
        elif cat == DRCRuleCategory.MAX_AREA:
            a = layer_data.get("max_area", 0)
            if a > val:
                self._add_violation(rule, f"最大面积 {a:.0f} > {val}", a, val)
        elif cat == DRCRuleCategory.MIN_DENSITY:
            d = layer_data.get("density", 0.0)
            if d < val:
                self._add_violation(rule, f"密度 {d:.1%} < {val:.1%}", d, val)
        elif cat == DRCRuleCategory.MAX_ANGLE:
            ang = layer_data.get("max_angle", 0)
            if ang > val:
                self._add_violation(rule, f"最大拐角 {ang:.0f}° > {val}°", ang, val)
        elif cat == DRCRuleCategory.MIN_ANGLE:
            ang = layer_data.get("min_angle", 180)
            if ang < val:
                self._add_violation(rule, f"最小拐角 {ang:.0f}° < {val}°", ang, val)
        elif cat == DRCRuleCategory.ACUTE_ANGLE:
            ang = layer_data.get("min_angle", 180)
            if ang < val:
                self._add_violation(rule, f"锐角 {ang:.0f}° < {val}°", ang, val)
        elif cat == DRCRuleCategory.MIN_BEND_RADIUS:
            r = layer_data.get("min_bend_radius", float("inf"))
            if r < val:
                self._add_violation(rule, f"弯曲半径 {r:.2f} < {val}", r, val)
        elif cat == DRCRuleCategory.MAX_CURVATURE:
            k = layer_data.get("max_curvature", 0.0)
            if k > val:
                self._add_violation(rule, f"曲率 {k:.3f} > {val}", k, val)
        elif cat == DRCRuleCategory.TAPER_ANGLE:
            ta = layer_data.get("taper_angle", 0)
            if ta > val:
                self._add_violation(rule, f"锥形角度 {ta:.1f}° > {val}°", ta, val)

    def _add_violation(self, rule: CurvilinearDRCRule, msg: str,
                       measured: float, limit: float) -> None:
        self._violations.append(DRCViolation18(
            rule_name=rule.name, category=rule.category.value,
            layer=rule.layer, severity=rule.severity,
            message=msg, measured_value=measured, limit_value=limit,
        ))

    def report(self) -> dict[str, Any]:
        by_cat: dict[str, int] = {}
        for v in self._violations:
            by_cat[v.category] = by_cat.get(v.category, 0) + 1
        return {
            "total_rules": self.rule_count,
            "curvilinear_rules": sum(1 for r in self._rules if r.is_curvilinear),
            "total_violations": self.violation_count,
            "errors": self.error_count,
            "warnings": self.violation_count - self.error_count,
            "violations_by_category": by_cat,
            "passed": self.error_count == 0,
        }

    def list_rules_by_category(self) -> dict[str, list[str]]:
        """按类别列出所有规则。"""
        result: dict[str, list[str]] = {}
        for rule in self._rules:
            cat = rule.category.value
            result.setdefault(cat, []).append(rule.name)
        return result


# =============================================================================
# 单元测试
# =============================================================================
# 注: M4Deliverable 与验证辅助函数已迁移到 _drc_m4_deliverable.py（R181-R200 拆分）。


def _test() -> None:
    """冒烟测试。"""
    engine = CurvilinearDRCEngine()

    # 验证 18 类规则
    assert engine.rule_count == 18, f"应有 18 条规则，实际 {engine.rule_count}"
    curvilinear = [r for r in engine._rules if r.is_curvilinear]
    assert len(curvilinear) == 5, f"应有 5 条曲线规则，实际 {len(curvilinear)}"  # noqa

    by_cat = engine.list_rules_by_category()
    assert len(by_cat) == 18

    # 运行检查（制造违规）
    layout = {
        "waveguide": {
            "min_width": 0.40,  # < 0.45 违规
            "max_width": 4.0,   # > 3.0 违规
            "min_curve_width": 0.45,  # < 0.50 违规
            "min_spacing": 0.4,  # < 0.5 违规
            "same_net_spacing": 0.2,  # < 0.3 违规
            "density_spacing": 0.5,  # < 0.8 违规
            "end_to_end": 0.4,  # < 0.6 违规
            "density": 0.03,  # < 0.05 违规
            "max_angle": 140,  # > 135 违规
            "min_angle": 80,   # < 90 违规
            "min_bend_radius": 3.0,  # < 5.0 违规
            "max_curvature": 0.3,  # > 0.2 违规
            "taper_angle": 15,  # > 10 违规
        },
        "contact": {"min_enclosure": 0.08},  # < 0.1 违规
        "metal1": {"min_extension": 0.15},  # < 0.2 违规
        "pad": {"min_area": 2000},  # < 2500 违规
        "slab": {"max_area": 60000},  # > 50000 违规
    }
    violations = engine.run_checks(layout)
    assert len(violations) == 18, f"应有 18 条违规，实际 {len(violations)}"

    rpt = engine.report()
    assert rpt["total_rules"] == 18
    assert rpt["curvilinear_rules"] == 5
    assert rpt["errors"] > 0
    print(f"DRC 18类: {rpt['total_rules']} 条规则 ({rpt['curvilinear_rules']} 曲线), "
          f"{rpt['total_violations']} 违规 ({rpt['errors']} 错误)")
    print(f"  违规分类: {rpt['violations_by_category']}")

    # M4 交付检查
    m4 = M4Deliverable()
    m4_rpt = m4.report()
    assert m4_rpt["total_items"] >= 20
    assert m4_rpt["completion_rate"] >= 0.9
    print(f"M4交付: {m4_rpt['passed_items']}/{m4_rpt['total_items']} 通过, "
          f"完成率={m4_rpt['completion_rate']:.1%}, "
          f"目标={m4_rpt['target_score']}")

    print("\n所有测试通过 ✅")


if __name__ == "__main__":
    _test()
