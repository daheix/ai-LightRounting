"""DRC 规则集预设库（polaris-verify-advanced 子模块迁移版）。

提供预定义的 DRC 规则集，对标 SiEPIC EBeam PDK 标准 DRC 规则：
1. SiEPIC EBeam 220nm SOI 标准规则集（11 条规则）
2. SiEPIC EBeam 300nm SiN 规则集（8 条规则）
3. Generic conservative 规则集（保守设计，6 条规则）
4. 自定义规则集构建器（CustomRuleSetBuilder）

规则参数溯源（R02 学术诚信）:
- SiEPIC EBeam 220nm SOI:
  - WG 最小宽度 0.35μm / 最小间距 0.6μm（SiEPIC EBeam PDK 标准）
  - 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC EBeam 300nm SiN:
  - SiN 最小宽度 0.8μm / 最小间距 0.8μm（Ligentec AN800 SiN PDK 参考）
  - 来源: https://www.ligentec.com/
- Generic conservative:
  - WG 最小宽度 0.5μm / 最小间距 1.0μm（保守工艺余量）

R03 合规:
- 未知规则集名 raise ValueError（不静默返回空列表）
- 规则集校验发现问题返回问题列表（不静默跳过）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC EBeam DRC: https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/master/klayout
- Ligentec AN800 SiN PDK: https://www.ligentec.com/
- gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- Synopsys OptoDesigner DRC: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from typing import Any

from ._drc_rules import CurvilinearDRCRule, DRCRuleCategory

logger = logging.getLogger(__name__)

__all__ = [
    "CustomRuleSetBuilder",
    "GENERIC_CONSERVATIVE_RULESET",
    "SIEPIC_EBEAM_SIN_RULESET",
    "SIEPIC_EBEAM_SOI_RULESET",
    "get_preset_ruleset",
    "list_preset_rulesets",
    "validate_ruleset",
]


# SiEPIC EBeam 220nm SOI 标准 DRC 规则集
# 来源: SiEPIC EBeam PDK 标准 DRC 规则
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
SIEPIC_EBEAM_SOI_RULESET: list[CurvilinearDRCRule] = [
    CurvilinearDRCRule(
        name="SOI_WG_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="WG",
        limit_value=0.35,
        units="μm",
        description="SiEPIC EBeam 220nm SOI 波导最小宽度 0.35μm（SiEPIC EBeam PDK 标准）",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_WG_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="WG",
        limit_value=0.6,
        units="μm",
        description="SiEPIC EBeam 220nm SOI 波导最小间距 0.6μm（SiEPIC EBeam PDK 标准）",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_WG_MIN_AREA",
        category=DRCRuleCategory.MIN_AREA,
        layer="WG",
        limit_value=0.1,
        units="μm²",
        description="SOI 波导最小面积 0.1μm²",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_SLAB150_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="SLAB150",
        limit_value=0.5,
        units="μm",
        description="SOI SLAB150 最小宽度 0.5μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_SLAB90_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="SLAB90",
        limit_value=0.5,
        units="μm",
        description="SOI SLAB90 最小宽度 0.5μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_METAL_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="METAL",
        limit_value=2.0,
        units="μm",
        description="METAL 最小宽度 2.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_METAL_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="METAL",
        limit_value=2.0,
        units="μm",
        description="METAL 最小间距 2.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_HEATER_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="HEATER",
        limit_value=1.0,
        units="μm",
        description="HEATER 最小宽度 1.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_HEATER_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="HEATER",
        limit_value=2.0,
        units="μm",
        description="HEATER 最小间距 2.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SOI_WG_MIN_BEND_RADIUS",
        category=DRCRuleCategory.MIN_BEND_RADIUS,
        layer="WG",
        limit_value=5.0,
        units="μm",
        is_curvilinear=True,
        description="SOI 波导最小弯曲半径 5.0μm（SiEPIC EBeam PDK 标准）",
        severity="warning",
    ),
    CurvilinearDRCRule(
        name="SOI_WG_MAX_ANGLE",
        category=DRCRuleCategory.MAX_ANGLE,
        layer="WG",
        limit_value=90.0,
        units="°",
        description="SOI 波导最大拐角 90°（禁止锐角）",
        severity="warning",
    ),
]


# SiEPIC EBeam 300nm SiN 标准 DRC 规则集
# 来源: Ligentec AN800 SiN PDK 参考 + SiEPIC EBeam 扩展
# https://www.ligentec.com/
SIEPIC_EBEAM_SIN_RULESET: list[CurvilinearDRCRule] = [
    CurvilinearDRCRule(
        name="SIN_WG_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="SiN",
        limit_value=0.8,
        units="μm",
        description="SiN 波导最小宽度 0.8μm（Ligentec AN800 SiN PDK 参考）",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SIN_WG_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="SiN",
        limit_value=0.8,
        units="μm",
        description="SiN 波导最小间距 0.8μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SIN_WG_MIN_AREA",
        category=DRCRuleCategory.MIN_AREA,
        layer="SiN",
        limit_value=0.5,
        units="μm²",
        description="SiN 波导最小面积 0.5μm²",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SIN_WG_MIN_BEND_RADIUS",
        category=DRCRuleCategory.MIN_BEND_RADIUS,
        layer="SiN",
        limit_value=50.0,
        units="μm",
        is_curvilinear=True,
        description="SiN 波导最小弯曲半径 50.0μm（SiN 弯曲损耗较大）",
        severity="warning",
    ),
    CurvilinearDRCRule(
        name="SIN_METAL_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="METAL",
        limit_value=2.0,
        units="μm",
        description="METAL 最小宽度 2.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SIN_METAL_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="METAL",
        limit_value=2.0,
        units="μm",
        description="METAL 最小间距 2.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="SIN_WG_MAX_ANGLE",
        category=DRCRuleCategory.MAX_ANGLE,
        layer="SiN",
        limit_value=90.0,
        units="°",
        description="SiN 波导最大拐角 90°（禁止锐角）",
        severity="warning",
    ),
    CurvilinearDRCRule(
        name="SIN_WG_MIN_END_TO_END",
        category=DRCRuleCategory.MIN_END_TO_END,
        layer="SiN",
        limit_value=1.0,
        units="μm",
        description="SiN 波导线端最小间距 1.0μm",
        severity="error",
    ),
]


# Generic 保守规则集（工艺余量大，适用于早期设计）
# 来源: 通用光子学设计保守规则 + gdsfactory generic PDK 参考
# https://gdsfactory.github.io/gdsfactory/
GENERIC_CONSERVATIVE_RULESET: list[CurvilinearDRCRule] = [
    CurvilinearDRCRule(
        name="GENERIC_WG_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="WG",
        limit_value=0.5,
        units="μm",
        description="通用保守 WG 最小宽度 0.5μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="GENERIC_WG_MIN_SPACING",
        category=DRCRuleCategory.MIN_SPACING,
        layer="WG",
        limit_value=1.0,
        units="μm",
        description="通用保守 WG 最小间距 1.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="GENERIC_WG_MIN_AREA",
        category=DRCRuleCategory.MIN_AREA,
        layer="WG",
        limit_value=0.25,
        units="μm²",
        description="通用保守 WG 最小面积 0.25μm²",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="GENERIC_WG_MIN_BEND_RADIUS",
        category=DRCRuleCategory.MIN_BEND_RADIUS,
        layer="WG",
        limit_value=10.0,
        units="μm",
        is_curvilinear=True,
        description="通用保守 WG 最小弯曲半径 10.0μm",
        severity="warning",
    ),
    CurvilinearDRCRule(
        name="GENERIC_METAL_MIN_WIDTH",
        category=DRCRuleCategory.MIN_WIDTH,
        layer="METAL",
        limit_value=3.0,
        units="μm",
        description="通用保守 METAL 最小宽度 3.0μm",
        severity="error",
    ),
    CurvilinearDRCRule(
        name="GENERIC_WG_MAX_ANGLE",
        category=DRCRuleCategory.MAX_ANGLE,
        layer="WG",
        limit_value=90.0,
        units="°",
        description="通用保守 WG 最大拐角 90°",
        severity="warning",
    ),
]


# 预设规则集注册表
_PRESET_REGISTRY: dict[str, list[CurvilinearDRCRule]] = {
    "siepic_ebeam_soi": SIEPIC_EBEAM_SOI_RULESET,
    "siepic_ebeam_sin": SIEPIC_EBEAM_SIN_RULESET,
    "generic_conservative": GENERIC_CONSERVATIVE_RULESET,
}


def list_preset_rulesets() -> list[str]:
    """列出所有预设规则集名。

    Returns:
        规则集名列表（按字母排序）。
    """
    return sorted(_PRESET_REGISTRY.keys())


def get_preset_ruleset(name: str) -> list[CurvilinearDRCRule]:
    """按名获取预设规则集。

    Args:
        name: 规则集名（'siepic_ebeam_soi' / 'siepic_ebeam_sin' /
            'generic_conservative'）。

    Returns:
        CurvilinearDRCRule 列表（副本，避免外部修改污染预设）。

    Raises:
        ValueError: 未知规则集名。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    if name not in _PRESET_REGISTRY:
        raise ValueError(
            f"未知规则集名: {name!r}。"
            f"可用规则集: {sorted(_PRESET_REGISTRY.keys())}"
        )
    return [rule for rule in _PRESET_REGISTRY[name]]


def validate_ruleset(rules: list[CurvilinearDRCRule]) -> list[str]:
    """校验规则集完整性。

    检查项: 规则名唯一、limit_value > 0、layer 非空、units 非空。

    Args:
        rules: CurvilinearDRCRule 列表。

    Returns:
        问题列表（空列表表示无问题）。

    Raises:
        TypeError: rules 不是列表。
    """
    if not isinstance(rules, (list, tuple)):
        raise TypeError(
            f"rules 必须是列表或元组，得到 {type(rules).__name__}"
        )
    issues: list[str] = []
    seen_names: set[str] = set()
    for i, rule in enumerate(rules):
        if not isinstance(rule, CurvilinearDRCRule):
            issues.append(
                f"规则 #{i} 不是 CurvilinearDRCRule 类型: "
                f"{type(rule).__name__}"
            )
            continue
        if rule.name in seen_names:
            issues.append(f"规则名重复: {rule.name!r}")
        seen_names.add(rule.name)
        if rule.limit_value <= 0:
            issues.append(
                f"规则 {rule.name!r} limit_value={rule.limit_value} <= 0"
            )
        if not rule.layer or not isinstance(rule.layer, str):
            issues.append(f"规则 {rule.name!r} layer 为空或非字符串")
        if not rule.units or not isinstance(rule.units, str):
            issues.append(f"规则 {rule.name!r} units 为空或非字符串")
    return issues


class CustomRuleSetBuilder:
    """自定义规则集构建器（Builder Pattern）。

    提供流式 API 构建自定义 DRC 规则集。

    来源:
    - Builder Pattern: GoF Design Patterns
      https://en.wikipedia.org/wiki/Builder_pattern
    - CurvilinearDRCRule: polaris_verify_advanced._drc_rules
    """

    def __init__(self) -> None:
        self._rules: list[CurvilinearDRCRule] = []

    def add_min_width(
        self, name: str, layer: str, limit_value: float,
        units: str = "μm", severity: str = "error", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加最小宽度规则。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=DRCRuleCategory.MIN_WIDTH, layer=layer,
            limit_value=limit_value, units=units,
            description=description, severity=severity,
        ))
        return self

    def add_min_spacing(
        self, name: str, layer: str, limit_value: float,
        units: str = "μm", severity: str = "error", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加最小间距规则。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=DRCRuleCategory.MIN_SPACING, layer=layer,
            limit_value=limit_value, units=units,
            description=description, severity=severity,
        ))
        return self

    def add_min_area(
        self, name: str, layer: str, limit_value: float,
        units: str = "μm²", severity: str = "error", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加最小面积规则。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=DRCRuleCategory.MIN_AREA, layer=layer,
            limit_value=limit_value, units=units,
            description=description, severity=severity,
        ))
        return self

    def add_min_bend_radius(
        self, name: str, layer: str, limit_value: float,
        units: str = "μm", severity: str = "warning", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加最小弯曲半径规则（曲线感知）。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=DRCRuleCategory.MIN_BEND_RADIUS, layer=layer,
            limit_value=limit_value, units=units, is_curvilinear=True,
            description=description, severity=severity,
        ))
        return self

    def add_max_angle(
        self, name: str, layer: str, limit_value: float,
        units: str = "°", severity: str = "warning", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加最大拐角规则。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=DRCRuleCategory.MAX_ANGLE, layer=layer,
            limit_value=limit_value, units=units,
            description=description, severity=severity,
        ))
        return self

    def add_rule(
        self, name: str, category: DRCRuleCategory, layer: str,
        limit_value: float, units: str = "μm", is_curvilinear: bool = False,
        severity: str = "error", description: str = "",
    ) -> "CustomRuleSetBuilder":
        """添加通用规则（任意类别）。"""
        self._rules.append(CurvilinearDRCRule(
            name=name, category=category, layer=layer,
            limit_value=limit_value, units=units, is_curvilinear=is_curvilinear,
            description=description, severity=severity,
        ))
        return self

    def build(self) -> list[CurvilinearDRCRule]:
        """构建规则集列表。

        Raises:
            ValueError: 规则集校验失败（通过 validate_ruleset 检测）。
        """
        issues = validate_ruleset(self._rules)
        if issues:
            raise ValueError(
                f"规则集校验失败，发现 {len(issues)} 个问题: {issues}"
            )
        return list(self._rules)

    def rule_count(self) -> int:
        """返回当前规则数。"""
        return len(self._rules)
