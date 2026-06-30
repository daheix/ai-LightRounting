"""R317 DRC 规则集预设库测试。

覆盖:
- SIEPIC_EBEAM_SOI_RULESET: SiEPIC EBeam 220nm SOI 标准规则集
- SIEPIC_EBEAM_SIN_RULESET: SiEPIC EBeam 300nm SiN 标准规则集
- GENERIC_CONSERVATIVE_RULESET: 通用保守规则集
- get_preset_ruleset: 按名获取预设规则集
- list_preset_rulesets: 列出所有预设规则集名
- validate_ruleset: 规则集校验
- CustomRuleSetBuilder: 自定义规则集构建器
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec AN800 SiN PDK: https://www.ligentec.com/
- gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import pytest

from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory
from polaris.verification.drc_ruleset_presets import (
    CustomRuleSetBuilder,
    GENERIC_CONSERVATIVE_RULESET,
    SIEPIC_EBEAM_SIN_RULESET,
    SIEPIC_EBEAM_SOI_RULESET,
    get_preset_ruleset,
    list_preset_rulesets,
    validate_ruleset,
)


# =============================================================================
# TestPresetRulesets: 预设规则集内容验证
# =============================================================================
class TestPresetRulesets:
    """预设规则集内容验证。"""

    def test_siepic_soi_ruleset_nonempty(self) -> None:
        """SiEPIC SOI 规则集非空。"""
        assert len(SIEPIC_EBEAM_SOI_RULESET) > 0

    def test_siepic_soi_ruleset_has_wg_min_width(self) -> None:
        """SiEPIC SOI 规则集含 WG 最小宽度。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SOI_RULESET
            if r.name == "SOI_WG_MIN_WIDTH"
        )
        assert rule.layer == "WG"
        assert rule.limit_value == 0.35
        assert rule.severity == "error"

    def test_siepic_soi_ruleset_has_wg_min_spacing(self) -> None:
        """SiEPIC SOI 规则集含 WG 最小间距。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SOI_RULESET
            if r.name == "SOI_WG_MIN_SPACING"
        )
        assert rule.limit_value == 0.6

    def test_siepic_soi_ruleset_has_bend_radius(self) -> None:
        """SiEPIC SOI 规则集含弯曲半径。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SOI_RULESET
            if r.name == "SOI_WG_MIN_BEND_RADIUS"
        )
        assert rule.is_curvilinear is True
        assert rule.limit_value == 5.0

    def test_siepic_sin_ruleset_nonempty(self) -> None:
        """SiEPIC SiN 规则集非空。"""
        assert len(SIEPIC_EBEAM_SIN_RULESET) > 0

    def test_siepic_sin_ruleset_has_sin_min_width(self) -> None:
        """SiEPIC SiN 规则集含 SiN 最小宽度。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SIN_RULESET
            if r.name == "SIN_WG_MIN_WIDTH"
        )
        assert rule.layer == "SiN"
        assert rule.limit_value == 0.8

    def test_generic_conservative_nonempty(self) -> None:
        """通用保守规则集非空。"""
        assert len(GENERIC_CONSERVATIVE_RULESET) > 0

    def test_generic_conservative_wg_min_width(self) -> None:
        """通用保守规则集 WG 最小宽度 0.5μm。"""
        rule = next(
            r for r in GENERIC_CONSERVATIVE_RULESET
            if r.name == "GENERIC_WG_MIN_WIDTH"
        )
        assert rule.limit_value == 0.5

    def test_all_rulesets_pass_validation(self) -> None:
        """所有预设规则集应通过校验。"""
        for name in list_preset_rulesets():
            rules = get_preset_ruleset(name)
            issues = validate_ruleset(rules)
            assert issues == [], (
                f"规则集 {name} 校验失败: {issues}"
            )


# =============================================================================
# TestGetPresetRuleset: 按名获取预设规则集
# =============================================================================
class TestGetPresetRuleset:
    """get_preset_ruleset 测试。"""

    def test_get_siepic_soi(self) -> None:
        """获取 SiEPIC SOI 规则集。"""
        rules = get_preset_ruleset("siepic_ebeam_soi")
        assert len(rules) == len(SIEPIC_EBEAM_SOI_RULESET)

    def test_get_siepic_sin(self) -> None:
        """获取 SiEPIC SiN 规则集。"""
        rules = get_preset_ruleset("siepic_ebeam_sin")
        assert len(rules) == len(SIEPIC_EBEAM_SIN_RULESET)

    def test_get_generic_conservative(self) -> None:
        """获取通用保守规则集。"""
        rules = get_preset_ruleset("generic_conservative")
        assert len(rules) == len(GENERIC_CONSERVATIVE_RULESET)

    def test_unknown_name_raises(self) -> None:
        """未知规则集名 raise ValueError。"""
        with pytest.raises(ValueError, match="未知规则集名"):
            get_preset_ruleset("nonexistent")

    def test_returns_copy(self) -> None:
        """返回副本，不污染预设。"""
        rules1 = get_preset_ruleset("siepic_ebeam_soi")
        rules2 = get_preset_ruleset("siepic_ebeam_soi")
        # 返回的是新列表（不同的列表对象）
        assert rules1 is not rules2
        # 列表中的规则对象是同一份（CurvilinearDRCRule 是共享的预设对象）
        # 但列表本身是副本，添加/删除规则不影响预设
        original_count = len(rules1)
        rules1.append(
            CurvilinearDRCRule(
                name="NEW", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=1.0,
            )
        )
        rules3 = get_preset_ruleset("siepic_ebeam_soi")
        assert len(rules3) == original_count  # 预设未被污染
        assert len(rules1) == original_count + 1


# =============================================================================
# TestListPresetRulesets: 列出预设规则集名
# =============================================================================
class TestListPresetRulesets:
    """list_preset_rulesets 测试。"""

    def test_returns_list(self) -> None:
        """返回列表。"""
        result = list_preset_rulesets()
        assert isinstance(result, list)

    def test_contains_all_presets(self) -> None:
        """包含所有预设规则集名。"""
        result = list_preset_rulesets()
        assert "siepic_ebeam_soi" in result
        assert "siepic_ebeam_sin" in result
        assert "generic_conservative" in result

    def test_sorted(self) -> None:
        """结果按字母排序。"""
        result = list_preset_rulesets()
        assert result == sorted(result)


# =============================================================================
# TestValidateRuleset: 规则集校验
# =============================================================================
class TestValidateRuleset:
    """validate_ruleset 测试。"""

    def test_valid_ruleset_no_issues(self) -> None:
        """有效规则集无问题。"""
        rules = get_preset_ruleset("siepic_ebeam_soi")
        issues = validate_ruleset(rules)
        assert issues == []

    def test_duplicate_name_issue(self) -> None:
        """规则名重复应报告。"""
        rules = [
            CurvilinearDRCRule(
                name="DUP", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.5,
            ),
            CurvilinearDRCRule(
                name="DUP", category=DRCRuleCategory.MIN_SPACING,
                layer="WG", limit_value=1.0,
            ),
        ]
        issues = validate_ruleset(rules)
        assert any("重复" in i for i in issues)

    def test_nonpositive_limit_value_issue(self) -> None:
        """limit_value <= 0 应报告。"""
        rules = [
            CurvilinearDRCRule(
                name="NEG", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=-1.0,
            ),
        ]
        issues = validate_ruleset(rules)
        assert any("<= 0" in i for i in issues)

    def test_zero_limit_value_issue(self) -> None:
        """limit_value == 0 应报告。"""
        rules = [
            CurvilinearDRCRule(
                name="ZERO", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.0,
            ),
        ]
        issues = validate_ruleset(rules)
        assert any("<= 0" in i for i in issues)

    def test_empty_layer_issue(self) -> None:
        """layer 为空应报告。"""
        rules = [
            CurvilinearDRCRule(
                name="EMPTY_LAYER", category=DRCRuleCategory.MIN_WIDTH,
                layer="", limit_value=0.5,
            ),
        ]
        issues = validate_ruleset(rules)
        assert any("layer" in i for i in issues)

    def test_empty_units_issue(self) -> None:
        """units 为空应报告。"""
        rules = [
            CurvilinearDRCRule(
                name="EMPTY_UNITS", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.5, units="",
            ),
        ]
        issues = validate_ruleset(rules)
        assert any("units" in i for i in issues)

    def test_non_rule_type_issue(self) -> None:
        """非 CurvilinearDRCRule 类型应报告。"""
        issues = validate_ruleset(["not_a_rule"])  # type: ignore[list-item]
        assert any("不是 CurvilinearDRCRule" in i for i in issues)

    def test_non_list_raises_type_error(self) -> None:
        """非列表 raise TypeError。"""
        with pytest.raises(TypeError):
            validate_ruleset("not_a_list")  # type: ignore[arg-type]

    def test_empty_list_no_issues(self) -> None:
        """空列表无问题。"""
        issues = validate_ruleset([])
        assert issues == []


# =============================================================================
# TestCustomRuleSetBuilder: 自定义规则集构建器
# =============================================================================
class TestCustomRuleSetBuilder:
    """CustomRuleSetBuilder 测试。"""

    def test_empty_builder(self) -> None:
        """空构建器。"""
        builder = CustomRuleSetBuilder()
        assert builder.rule_count() == 0

    def test_add_min_width(self) -> None:
        """添加最小宽度规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_width("W1", "WG", 0.5)
        assert builder.rule_count() == 1
        rules = builder.build()
        assert rules[0].category == DRCRuleCategory.MIN_WIDTH
        assert rules[0].limit_value == 0.5

    def test_add_min_spacing(self) -> None:
        """添加最小间距规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_spacing("S1", "WG", 1.0)
        rules = builder.build()
        assert rules[0].category == DRCRuleCategory.MIN_SPACING

    def test_add_min_area(self) -> None:
        """添加最小面积规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_area("A1", "WG", 0.25, units="μm²")
        rules = builder.build()
        assert rules[0].category == DRCRuleCategory.MIN_AREA

    def test_add_min_bend_radius(self) -> None:
        """添加最小弯曲半径规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_bend_radius("R1", "WG", 5.0)
        rules = builder.build()
        assert rules[0].is_curvilinear is True
        assert rules[0].category == DRCRuleCategory.MIN_BEND_RADIUS

    def test_add_max_angle(self) -> None:
        """添加最大拐角规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_max_angle("ANG1", "WG", 90.0)
        rules = builder.build()
        assert rules[0].category == DRCRuleCategory.MAX_ANGLE

    def test_add_rule_generic(self) -> None:
        """添加通用规则。"""
        builder = CustomRuleSetBuilder()
        builder.add_rule(
            "GEN1", DRCRuleCategory.MIN_ENCLOSURE, "METAL", 0.5
        )
        rules = builder.build()
        assert rules[0].category == DRCRuleCategory.MIN_ENCLOSURE

    def test_fluent_api(self) -> None:
        """流式 API 链式调用。"""
        rules = (
            CustomRuleSetBuilder()
            .add_min_width("W1", "WG", 0.5)
            .add_min_spacing("S1", "WG", 1.0)
            .add_min_bend_radius("R1", "WG", 5.0)
            .build()
        )
        assert len(rules) == 3

    def test_build_invalid_raises(self) -> None:
        """构建无效规则集 raise ValueError。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_width("W1", "WG", -1.0)  # 无效 limit_value
        with pytest.raises(ValueError, match="校验失败"):
            builder.build()

    def test_build_returns_copy(self) -> None:
        """build 返回副本。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_width("W1", "WG", 0.5)
        rules1 = builder.build()
        rules2 = builder.build()
        assert rules1 is not rules2


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理。"""

    def test_unknown_ruleset_raises(self) -> None:
        """未知规则集名 raise ValueError。"""
        with pytest.raises(ValueError):
            get_preset_ruleset("nonexistent")

    def test_validate_non_list_raises(self) -> None:
        """非列表 raise TypeError。"""
        with pytest.raises(TypeError):
            validate_ruleset(None)  # type: ignore[arg-type]

    def test_build_invalid_raises(self) -> None:
        """构建无效规则集 raise ValueError。"""
        builder = CustomRuleSetBuilder()
        builder.add_min_width("W1", "WG", -1.0)  # 无效 limit_value
        with pytest.raises(ValueError, match="校验失败"):
            builder.build()


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信验证。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 应含 5+ 文献 URL。"""
        from polaris.verification import drc_ruleset_presets as m
        doc = m.__doc__ or ""
        urls = [
            "SiEPIC" in doc,
            "Ligentec" in doc,
            "gdsfactory" in doc,
            "klayout" in doc,
            "Synopsys" in doc or "OptoDesigner" in doc,
            "github.com" in doc,
        ]
        url_count = sum(1 for u in urls if u)
        assert url_count >= 5, f"docstring 文献 URL 不足 5 个: {url_count}"

    def test_rules_have_description(self) -> None:
        """规则应含描述。"""
        for ruleset_name in list_preset_rulesets():
            rules = get_preset_ruleset(ruleset_name)
            for rule in rules:
                assert rule.description, (
                    f"规则集 {ruleset_name} 规则 {rule.name} 缺少描述"
                )

    def test_siepic_soi_rules_source_documented(self) -> None:
        """SiEPIC SOI 规则应溯源 SiEPIC PDK。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SOI_RULESET
            if r.name == "SOI_WG_MIN_WIDTH"
        )
        assert "SiEPIC" in rule.description

    def test_sin_rules_source_documented(self) -> None:
        """SiN 规则应溯源 Ligentec。"""
        rule = next(
            r for r in SIEPIC_EBEAM_SIN_RULESET
            if r.name == "SIN_WG_MIN_WIDTH"
        )
        assert "Ligentec" in rule.description or "SiN" in rule.description


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_preset_ruleset_with_drc_validator(self) -> None:
        """预设规则集与 DRC 验证器集成（仅用 KLayout 支持的规则类别）。"""
        from polaris.verification.gdsii_drc_validator import (
            drc_summary_from_gdsii,
        )
        from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
        import tempfile
        import os

        # 创建合规 GDS（仅含 WG 层）
        cells_spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 1, "datatype": 0,
                        "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                    },
                ],
                "is_top": True,
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = os.path.join(tmpdir, "test.gds")
            export_gdsii_from_cells(cells_spec, gds_path)
            # 从 generic_conservative 过滤出 KLayout 支持的规则类别
            # KLayout 桥接支持: MIN_WIDTH, MIN_SPACING, MIN_AREA
            all_rules = get_preset_ruleset("generic_conservative")
            supported_categories = {
                DRCRuleCategory.MIN_WIDTH,
                DRCRuleCategory.MIN_SPACING,
                DRCRuleCategory.MIN_AREA,
            }
            rules = [
                r for r in all_rules
                if r.category in supported_categories
            ]
            assert len(rules) > 0
            summary = drc_summary_from_gdsii(gds_path, rules)
            assert summary["passed"] is True

    def test_custom_builder_with_drc_validator(self) -> None:
        """自定义构建器与 DRC 验证器集成。"""
        from polaris.verification.gdsii_drc_validator import (
            drc_summary_from_gdsii,
        )
        from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
        import tempfile
        import os

        rules = (
            CustomRuleSetBuilder()
            .add_min_width("W1", "WG", 0.45)
            .add_min_spacing("S1", "WG", 0.5)
            .build()
        )
        cells_spec = [
            {
                "name": "TOP",
                "polygons": [
                    {
                        "layer": 1, "datatype": 0,
                        "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                    },
                ],
                "is_top": True,
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = os.path.join(tmpdir, "test.gds")
            export_gdsii_from_cells(cells_spec, gds_path)
            summary = drc_summary_from_gdsii(gds_path, rules)
            assert summary["passed"] is True

    def test_all_presets_valid(self) -> None:
        """所有预设规则集校验通过。"""
        for name in list_preset_rulesets():
            rules = get_preset_ruleset(name)
            issues = validate_ruleset(rules)
            assert issues == []

    def test_performance_large_ruleset(self) -> None:
        """性能: 大规则集校验 < 0.1s。"""
        import time
        builder = CustomRuleSetBuilder()
        for i in range(100):
            builder.add_min_width(f"W{i}", "WG", 0.5)
        rules = builder.build()
        start = time.perf_counter()
        validate_ruleset(rules)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1
