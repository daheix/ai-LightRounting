"""曲线感知 DRC 18 类规则引擎（polaris-verify-advanced 子模块迁移版）。

对齐 Synopsys OptoDesigner DRC 模块（18 类曲线感知规则）+ Siemens Calibre nmDRC。

迁移说明: 原 v4 ``drc_curvilinear_18rules.py`` 依赖 ``_drc_geometry.py`` (1027 行)
与 ``_drc_checks.py`` (1080 行) 的几何检查 Mixin（``run_geometric_checks`` 入口）。
这两个文件均超过 R13 文件 ≤800 行限制，本次迁移仅保留核心
``CurvilinearDRCEngine.run_checks``（预计算值检查，18 类规则 dispatch），
几何检查 Mixin 不在本次迁移范围（需单独拆分迁移）。

学术依据:
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- KLayout DRC Reference (曲线感知规则)
  URL: https://www.klayout.de/doc-qt5/manual/drc.html
- Siemens Calibre nmDRC
  URL: https://www.siemens.com/en-us/products/ic/ic-custom/verification/calibre-nmdrc/
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024,
  http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
- imec Curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

from typing import Any

from ._drc_rules import (
    CurvilinearDRCRule,
    DRCRuleCategory,
    DRCViolation18,
)

__all__ = [
    "CurvilinearDRCRule",
    "DRCRuleCategory",
    "DRCViolation18",
    "CurvilinearDRCEngine",
]


class CurvilinearDRCEngine:
    """曲线感知 DRC 引擎（18 类规则，预计算值检查）。

    对齐: Synopsys OptoDesigner DRC Module + KLayout 曲线 DRC + Calibre nmDRC。
    支持: 直线/曲线版图规则注册、预计算值检查（``run_checks``）、报告生成。

    迁移说明: 原 v4 引擎继承 ``_DRCGeometricChecksMixin``（几何检查方法）。
    本次迁移仅保留预计算值检查入口 ``run_checks``，几何检查
    ``run_geometric_checks`` 需 ``_drc_geometry`` + ``_drc_checks`` 模块
    （均超 800 行限制，未迁移）。

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
        self._extended_enabled: bool = False
        self._register_18_rules()
        self._rule_handlers: dict[Any, Any] = self._build_rule_handlers()

    def _build_rule_handlers(self) -> dict[Any, Any]:
        """构建规则类别 → 检查函数的 dispatch table（降低 _check_rule 圈复杂度）。"""
        return {
            DRCRuleCategory.MIN_WIDTH: self._chk_min_width,
            DRCRuleCategory.MAX_WIDTH: self._chk_max_width,
            DRCRuleCategory.MIN_WIDTH_CURVE: self._chk_min_curve_width,
            DRCRuleCategory.MIN_SPACING: self._chk_min_spacing,
            DRCRuleCategory.MIN_SPACING_SAME_NET: self._chk_same_net_spacing,
            DRCRuleCategory.MIN_SPACING_DENSITY: self._chk_density_spacing,
            DRCRuleCategory.MIN_END_TO_END: self._chk_end_to_end,
            DRCRuleCategory.MIN_ENCLOSURE: self._chk_min_enclosure,
            DRCRuleCategory.MIN_EXTENSION: self._chk_min_extension,
            DRCRuleCategory.MIN_AREA: self._chk_min_area,
            DRCRuleCategory.MAX_AREA: self._chk_max_area,
            DRCRuleCategory.MIN_DENSITY: self._chk_min_density,
            DRCRuleCategory.MAX_ANGLE: self._chk_max_angle,
            DRCRuleCategory.MIN_ANGLE: self._chk_min_angle,
            DRCRuleCategory.ACUTE_ANGLE: self._chk_acute_angle,
            DRCRuleCategory.MIN_BEND_RADIUS: self._chk_min_bend_radius,
            DRCRuleCategory.MAX_CURVATURE: self._chk_max_curvature,
            DRCRuleCategory.TAPER_ANGLE: self._chk_taper_angle,
        }

    @property
    def rule_count(self) -> int:
        """返回已注册的 DRC 规则总数。"""
        return len(self._rules)

    @property
    def violation_count(self) -> int:
        """返回违规实例总数。"""
        return len(self._violations)

    @property
    def error_count(self) -> int:
        """返回 ERROR 级别违规数量。"""
        return sum(1 for v in self._violations if v.severity == "error")

    @property
    def extended_rules_enabled(self) -> bool:
        """是否启用了 R141-R180 扩展规则（8 类）。"""
        return self._extended_enabled

    def enable_extended_rules(self) -> None:
        """启用 R141-R180 扩展规则（8 类）。

        扩展规则清单:
        - ST1_step_width: 步进宽度突变（波导相邻段宽度差）
        - AL1_layer_alignment: 层对齐度（两层图形边缘错位）
        - EX1_layer_extension: 层延伸（一层超出另一层的最小延伸量）
        - ED1_edge_length: 边缘长度（最小/最大边长）
        - PM1_perimeter: 周长（最小/最大周长）
        - SY1_symmetry: 对称性（图形对称度）
        - AR1_array_pitch: 阵列间距（周期性阵列 pitch 一致性）
        - MW1_max_width_single_mode: 最大宽度（防止过宽导致多模）

        学术依据:
        - Synopsys OptoDesigner DRC Module:
          https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
        - KLayout DRC Reference: https://www.klayout.org/doc-qt5/manual/drc.html
        - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
        - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Eades 1986 "Optimal Algorithms for Symmetry Detection":
          https://deepblue.lib.umich.edu/bitstream/handle/2027.42/8337/bad6491.0001.001.pdf
        - Toussaint 1983 "Rotating Calipers":
          https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
        """
        if self._extended_enabled:
            return  # 已启用，幂等
        extended = self._build_extended_rules()
        self._rules.extend(extended)
        self._extended_enabled = True

    def disable_extended_rules(self) -> None:
        """禁用 R141-R180 扩展规则（移除 8 条扩展规则，恢复 18 类基础规则集）。"""
        if not self._extended_enabled:
            return
        extended_categories = {
            DRCRuleCategory.STEP_WIDTH,
            DRCRuleCategory.LAYER_ALIGNMENT,
            DRCRuleCategory.LAYER_EXTENSION,
            DRCRuleCategory.EDGE_LENGTH,
            DRCRuleCategory.PERIMETER,
            DRCRuleCategory.SYMMETRY,
            DRCRuleCategory.ARRAY_PITCH,
            DRCRuleCategory.MAX_WIDTH_SINGLE_MODE,
        }
        self._rules = [r for r in self._rules if r.category not in extended_categories]
        self._extended_enabled = False

    @staticmethod
    def _build_extended_rules() -> list[CurvilinearDRCRule]:
        """构建 R141-R180 扩展规则集（8 条）。

        每条规则的阈值来自 SiEPIC EBeam PDK / Chrostowski & Hochberg 2015 /
        Synopsys OptoDesigner DRC Module，禁止编造（R02 学术诚信）。

        文献:
        - SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
        - Synopsys OptoDesigner DRC Module:
          https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
        - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
        - KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html
        """
        return [
            CurvilinearDRCRule(
                "ST1_step_width", DRCRuleCategory.STEP_WIDTH,
                "waveguide", 0.1, "μm", False,
                "步进宽度突变（波导相邻段宽度差）",
                layer_pair=None,
            ),
            CurvilinearDRCRule(
                "AL1_layer_alignment", DRCRuleCategory.LAYER_ALIGNMENT,
                "metal1", 0.05, "μm", False,
                "层对齐度（metal1 与 contact 对齐误差）",
                layer_pair="contact",
            ),
            CurvilinearDRCRule(
                "EX1_layer_extension", DRCRuleCategory.LAYER_EXTENSION,
                "metal1", 0.2, "μm", False,
                "层延伸（metal1 延伸超出 contact）",
                layer_pair="contact",
            ),
            CurvilinearDRCRule(
                "ED1_edge_length", DRCRuleCategory.EDGE_LENGTH,
                "waveguide", 0.2, "μm", False,
                "边缘长度（最小 0.2μm / 最大 1000μm）",
                limit_max=1000.0,
            ),
            CurvilinearDRCRule(
                "PM1_perimeter", DRCRuleCategory.PERIMETER,
                "waveguide", 1.0, "μm", False,
                "周长（最小 1.0μm / 最大 10000μm）",
                limit_max=10000.0,
            ),
            CurvilinearDRCRule(
                "SY1_symmetry", DRCRuleCategory.SYMMETRY,
                "waveguide", 0.95, "", True,
                "对称性（反射对称度，分数 [0,1]）",
                tolerance=1e-6,
            ),
            CurvilinearDRCRule(
                "AR1_array_pitch", DRCRuleCategory.ARRAY_PITCH,
                "waveguide", 0.01, "μm", False,
                "阵列间距（pitch 标准差，周期一致性）",
            ),
            CurvilinearDRCRule(
                "MW1_max_width_single_mode",
                DRCRuleCategory.MAX_WIDTH_SINGLE_MODE,
                "waveguide", 1.0, "μm", False,
                "最大宽度（单模截止，SOI 220nm@1550nm 工程经验值; "
                "Soref 1991 IEEE JQE 数值仿真; Grillot 2006 JLT 方形<320nm 单模; "
                "SiEPIC EBeam PDK strip 500nm 标准; "
                "R05 修正: 原 1.05μm 无文献支撑，V 参数块材料推导 W_max≈0.375μm "
                "过保守不适用于矩形波导，1.0μm 来自 Soref/SiEPIC 全矢量仿真经验）",
            ),
        ]

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
        """运行全部 18 类规则检查（预计算值模式）。

        Args:
            layout_data: {layer: {"features": [...], "min_width": x, ...}}
        """
        self._violations = []
        for rule in self._rules:
            self._check_rule(rule, layout_data)
        return self._violations

    def _check_rule(self, rule: CurvilinearDRCRule, layout: dict[str, Any]) -> None:
        """按规则类别分发到具体检查子方法（dispatch table 模式）。"""
        layer_data = layout.get(rule.layer, {})
        if not layer_data:
            return
        handler = self._rule_handlers.get(rule.category)
        if handler is None:
            return
        handler(rule, layer_data)

    def _chk_min_width(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_width", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"最小宽度 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_max_width(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("max_width", 0)
        if v > rule.limit_value:
            self._add_violation(rule, f"最大宽度 {v:.3f} > {rule.limit_value}", v, rule.limit_value)

    def _chk_min_curve_width(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_curve_width", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"曲线最小宽度 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_min_spacing(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_spacing", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"最小间距 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_same_net_spacing(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("same_net_spacing", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"同网络间距 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_density_spacing(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("density_spacing", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"高密度区间距 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_end_to_end(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("end_to_end", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"端到端间距 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_min_enclosure(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_enclosure", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"包围 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_min_extension(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_extension", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"延伸 {v:.3f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_min_area(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_area", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"最小面积 {v:.0f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_max_area(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("max_area", 0)
        if v > rule.limit_value:
            self._add_violation(rule, f"最大面积 {v:.0f} > {rule.limit_value}", v, rule.limit_value)

    def _chk_min_density(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("density", 0.0)
        if v < rule.limit_value:
            self._add_violation(rule, f"密度 {v:.1%} < {rule.limit_value:.1%}", v, rule.limit_value)

    def _chk_max_angle(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("max_angle", 0)
        if v > rule.limit_value:
            self._add_violation(rule, f"最大拐角 {v:.0f}° > {rule.limit_value}°", v, rule.limit_value)

    def _chk_min_angle(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_angle", 180)
        if v < rule.limit_value:
            self._add_violation(rule, f"最小拐角 {v:.0f}° < {rule.limit_value}°", v, rule.limit_value)

    def _chk_acute_angle(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_angle", 180)
        if v < rule.limit_value:
            self._add_violation(rule, f"锐角 {v:.0f}° < {rule.limit_value}°", v, rule.limit_value)

    def _chk_min_bend_radius(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("min_bend_radius", float("inf"))
        if v < rule.limit_value:
            self._add_violation(rule, f"弯曲半径 {v:.2f} < {rule.limit_value}", v, rule.limit_value)

    def _chk_max_curvature(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("max_curvature", 0.0)
        if v > rule.limit_value:
            self._add_violation(rule, f"曲率 {v:.3f} > {rule.limit_value}", v, rule.limit_value)

    def _chk_taper_angle(self, rule: CurvilinearDRCRule, d: dict[str, Any]) -> None:
        v = d.get("taper_angle", 0)
        if v > rule.limit_value:
            self._add_violation(rule, f"锥形角度 {v:.1f}° > {rule.limit_value}°", v, rule.limit_value)

    def _add_violation(self, rule: CurvilinearDRCRule, msg: str,
                       measured: float, limit: float) -> None:
        self._violations.append(DRCViolation18(
            rule_name=rule.name, category=rule.category.value,
            layer=rule.layer, severity=rule.severity,
            message=msg, measured_value=measured, limit_value=limit,
        ))

    def report(self) -> dict[str, Any]:
        """生成曲直 DRC 检查报告字典。"""
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
