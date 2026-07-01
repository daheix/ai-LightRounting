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
        self._extended_enabled: bool = False
        self._register_18_rules()
        self._rule_handlers: dict[Any, Any] = self._build_rule_handlers()
        self._simple_geo_handlers, self._pair_geo_handlers = self._build_geo_handlers()

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
        """启用 R141-R180 扩展规则（8 类: Step/Alignment/Edge/Perimeter/Symmetry/Array/Extension/MaxWidth）。

        调用后引擎将注册并检查这 8 个扩展规则。默认不启用以保持向后兼容
        （原 18 类基础规则保持 rule_count == 18 不变）。

        扩展规则清单（每条对应一个 ``_check_*_geo`` 几何算法）:
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
        - KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc.html
        """
        return [
            # 1. Step 规则: 波导宽度突变 ≤ 0.1μm（SiEPIC mismatched pin widths）
            CurvilinearDRCRule(
                "ST1_step_width", DRCRuleCategory.STEP_WIDTH,
                "waveguide", 0.1, "μm", False,
                "步进宽度突变（波导相邻段宽度差）",
                layer_pair=None,
            ),
            # 2. Alignment 规则: 层间对齐误差 ≤ 0.05μm（Calibre ALIGN）
            CurvilinearDRCRule(
                "AL1_layer_alignment", DRCRuleCategory.LAYER_ALIGNMENT,
                "metal1", 0.05, "μm", False,
                "层对齐度（metal1 与 contact 对齐误差）",
                layer_pair="contact",
            ),
            # 3. Extension 规则: 金属层延伸超出接触孔 ≥ 0.2μm
            CurvilinearDRCRule(
                "EX1_layer_extension", DRCRuleCategory.LAYER_EXTENSION,
                "metal1", 0.2, "μm", False,
                "层延伸（metal1 延伸超出 contact）",
                layer_pair="contact",
            ),
            # 4. Edge 规则: 最小边长 0.2μm，最大边长 1000μm
            CurvilinearDRCRule(
                "ED1_edge_length", DRCRuleCategory.EDGE_LENGTH,
                "waveguide", 0.2, "μm", False,
                "边缘长度（最小 0.2μm / 最大 1000μm）",
                limit_max=1000.0,
            ),
            # 5. Perimeter 规则: 最小周长 1.0μm，最大周长 10000μm
            CurvilinearDRCRule(
                "PM1_perimeter", DRCRuleCategory.PERIMETER,
                "waveguide", 1.0, "μm", False,
                "周长（最小 1.0μm / 最大 10000μm）",
                limit_max=10000.0,
            ),
            # 6. Symmetry 规则: 对称分数 ≥ 0.95（95% 顶点对称）
            CurvilinearDRCRule(
                "SY1_symmetry", DRCRuleCategory.SYMMETRY,
                "waveguide", 0.95, "", True,
                "对称性（反射对称度，分数 [0,1]）",
                tolerance=1e-6,
            ),
            # 7. Array 规则: 阵列 pitch 标准差 ≤ 0.01μm（10nm 阵列一致性）
            CurvilinearDRCRule(
                "AR1_array_pitch", DRCRuleCategory.ARRAY_PITCH,
                "waveguide", 0.01, "μm", False,
                "阵列间距（pitch 标准差，周期一致性）",
            ),
            # 8. MaxWidth 规则: 单模最大宽度 1.05μm（1550nm SOI 单模截止）
            CurvilinearDRCRule(
                "MW1_max_width_single_mode",
                DRCRuleCategory.MAX_WIDTH_SINGLE_MODE,
                "waveguide", 1.05, "μm", False,
                "最大宽度（防止过宽导致多模，1550nm SOI 单模截止）",
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
        """运行全部 18 类规则检查。

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
        """生成曲直 DRC 检查报告字典。

        Returns:
            含 total_rules/curvilinear_rules/total_violations/errors/
            warnings/violations_by_category/passed 的字典。
        """
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
