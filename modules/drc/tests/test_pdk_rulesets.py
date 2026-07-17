"""PDK DRC 规则集测试（PDK 深度桥接 R384，2026-07-17）。

覆盖 ``polaris_drc.pdk_rulesets`` 模块的全部公开 API:
- DRCRuleset dataclass（pdk_name + rules + layer_map）
- DRC_RULESETS 4 PDK 规则集注册表
- get_drc_ruleset() 查询 / R03 KeyError 行为
- register_drc_ruleset() 自定义注册 / R03 重复注册 ValueError
- list_available_pdk_rulesets() 列表

R03 合规验证: 未注册 PDK raise KeyError，重复注册 raise ValueError，
禁止 fall-back。

学术依据（R02 学术诚信，≥5 文献 URL）:
- Soref 1993 SOI: https://doi.org/10.1364/AO.32.003546
- SiEPIC EBeam PDK: https://github.com/SiEPIC/OpenEBL
- IMEC iSiPP50G: https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
- AMF Foundry: https://www.a-star.edu.sg/amf
- Ligentec SiN: https://www.ligentec.com/
- ITU-T G.977: https://www.itu.int/rec/T-REC-G.977
- SiEPIC_EBeam_PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc_runsets.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 无 TODO。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_drc.pdk_rulesets import (  # noqa: E402
    DRC_RULESETS,
    DRCRuleset,
    get_drc_ruleset,
    list_available_pdk_rulesets,
    register_drc_ruleset,
)
from polaris_drc.rules import DEFAULT_DRC_RULES, CheckType, DRCRule  # noqa: E402


# =============================================================================
# 1. 查询: get_drc_ruleset 4 PDK 规则集
# =============================================================================


@pytest.mark.parametrize("pdk_name", [
    "siepic_ebeam",
    "imec_isipp50g",
    "amf",
    "ligentec_sic",
])
def test_get_drc_ruleset_returns_valid_ruleset(pdk_name):
    """get_drc_ruleset 应返回有效 DRCRuleset（4 PDK 参数化测试）。

    来源: 各 PDK 文档（见模块 docstring）。
    """
    ruleset = get_drc_ruleset(pdk_name)
    assert isinstance(ruleset, DRCRuleset)
    assert ruleset.pdk_name == pdk_name
    # 规则数量应与 SiEPIC DEFAULT_DRC_RULES 相同（25 条派生规则）
    assert len(ruleset.rules) == len(DEFAULT_DRC_RULES)
    # 每条规则的 pdk_name 字段应设置为该 PDK 名
    for rule in ruleset.rules:
        assert rule.pdk_name == pdk_name
    # layer_map 非空
    assert len(ruleset.layer_map) > 0


# =============================================================================
# 2. 查询: BEND_RADIUS_MIN 按 PDK 工艺特性调整
# =============================================================================


def test_bend_radius_min_per_pdk():
    """BEND_RADIUS_MIN 阈值应按 PDK 工艺特性调整（R02 文献溯源）。

    - SiEPIC EBeam: 5.0μm（SiEPIC_EBeam_PDK）
    - IMEC iSiPP50G: 5.0μm（IMEC 文档）
    - AMF: 10.0μm（AMF Foundry PDK）
    - Ligentec SiN: 100.0μm（Ligentec AN800，SiN 弯曲损耗大）
    """
    expected_bend = {
        "siepic_ebeam": 5.0,
        "imec_isipp50g": 5.0,
        "amf": 10.0,
        "ligentec_sic": 100.0,
    }
    for pdk_name, expected_radius in expected_bend.items():
        ruleset = get_drc_ruleset(pdk_name)
        bend_rules = [r for r in ruleset.rules if r.name == "BEND_RADIUS_MIN"]
        assert len(bend_rules) == 1, f"{pdk_name} 应有且仅有 1 条 BEND_RADIUS_MIN"
        assert bend_rules[0].threshold == pytest.approx(
            expected_radius, abs=1e-6
        ), f"{pdk_name} BEND_RADIUS_MIN 应为 {expected_radius}μm"
        assert bend_rules[0].check_type == CheckType.BEND_RADIUS_MIN


# =============================================================================
# 3. 查询: layer_map 各 PDK GDS 层映射正确
# =============================================================================


def test_layer_map_per_pdk():
    """各 PDK layer_map 应包含关键 GDS 层（R02 文献溯源）。

    来源: 各 PDK 的 KLayout layer .lyp/.klayout.xml 文件。
    """
    # SiEPIC EBeam PDK: Si=(1,0), M1_HEATER=(47,0), VIAC=(40,0), DEEPTRENCH=(7,0)
    siepic = get_drc_ruleset("siepic_ebeam")
    assert siepic.layer_map["Si"] == (1, 0)
    assert siepic.layer_map["M1_HEATER"] == (47, 0)
    assert siepic.layer_map["VIAC"] == (40, 0)
    assert siepic.layer_map["DEEPTRENCH"] == (7, 0)

    # IMEC iSiPP50G: Si_WG=(100,0), HEATER=(120,0), VIA1=(140,0)
    imec = get_drc_ruleset("imec_isipp50g")
    assert imec.layer_map["Si_WG"] == (100, 0)
    assert imec.layer_map["HEATER"] == (120, 0)
    assert imec.layer_map["VIA1"] == (140, 0)

    # AMF: Si=(1,0), HEATER=(4,0), VIA=(7,0)
    amf = get_drc_ruleset("amf")
    assert amf.layer_map["Si"] == (1, 0)
    assert amf.layer_map["HEATER"] == (4, 0)
    assert amf.layer_map["VIA"] == (7, 0)

    # Ligentec SiN: SiN=(10,0), HEATER=(20,0), VIA=(40,0)
    ligentec = get_drc_ruleset("ligentec_sic")
    assert ligentec.layer_map["SiN"] == (10, 0)
    assert ligentec.layer_map["HEATER"] == (20, 0)
    assert ligentec.layer_map["VIA"] == (40, 0)


def test_layer_map_layer_pair_consistency():
    """跨层规则的 layer_pair 应在 layer_map 中有对应条目（数据一致性）。

    SEPARATION/ENCLOSURE/EXTENSION/EXCLUSION 的 layer_pair 字段必须在该 PDK
    的 layer_map 中能查到，否则跨层 DRC 检查无法解析层号。
    """
    cross_layer_rule_names = {"SEPARATION", "ENCLOSURE", "EXTENSION", "EXCLUSION"}
    for pdk_name in list_available_pdk_rulesets():
        ruleset = get_drc_ruleset(pdk_name)
        for rule in ruleset.rules:
            if rule.name in cross_layer_rule_names:
                assert rule.layer_pair is not None, (
                    f"{pdk_name} 的 {rule.name} 规则 layer_pair 不应为 None"
                )
                assert rule.layer_pair in ruleset.layer_map, (
                    f"{pdk_name} 的 {rule.name} 规则 layer_pair='"
                    f"{rule.layer_pair}' 未在 layer_map 中找到"
                )


# =============================================================================
# 4. 注册: register_drc_ruleset 自定义 PDK
# =============================================================================


def test_register_drc_ruleset_custom_pdk():
    """register_drc_ruleset 应成功注册自定义 PDK 规则集。"""
    custom_pdk_name = "test_custom_pdk_xyz_unique"
    custom_rules = [
        DRCRule(
            name="CUSTOM_MIN_WIDTH",
            check_type=CheckType.MIN_WIDTH,
            threshold=0.3,
            severity=1.0,
            description="自定义最小宽度 0.3μm",
            pdk_name=custom_pdk_name,
        ),
    ]
    custom_layer_map = {"WG": (1, 0), "HEATER": (10, 0)}
    custom_ruleset = DRCRuleset(
        pdk_name=custom_pdk_name,
        rules=custom_rules,
        layer_map=custom_layer_map,
    )
    try:
        # 注册前确认未注册
        assert custom_pdk_name not in list_available_pdk_rulesets()
        # 注册
        register_drc_ruleset(custom_pdk_name, custom_ruleset)
        # 注册后确认可用
        assert custom_pdk_name in list_available_pdk_rulesets()
        # 查询应返回同一实例
        retrieved = get_drc_ruleset(custom_pdk_name)
        assert retrieved is custom_ruleset
        assert retrieved.pdk_name == custom_pdk_name
        assert len(retrieved.rules) == 1
        assert retrieved.rules[0].name == "CUSTOM_MIN_WIDTH"
        assert retrieved.layer_map == custom_layer_map
    finally:
        # 清理全局注册表，避免污染其他测试
        del DRC_RULESETS[custom_pdk_name]


# =============================================================================
# 5. 错误处理: R03 KeyError / ValueError
# =============================================================================


def test_get_drc_ruleset_unregistered_raises_keyerror():
    """R03 合规: 未注册 PDK 必须 raise KeyError，禁止 fall-back。"""
    with pytest.raises(KeyError, match="未注册"):
        get_drc_ruleset("nonexistent_pdk_xyz")


def test_register_drc_ruleset_duplicate_raises_valueerror():
    """R03 合规: 重复注册 PDK 必须 raise ValueError，禁止静默覆盖。"""
    duplicate_pdk_name = "siepic_ebeam"  # 已注册的 PDK
    duplicate_ruleset = DRCRuleset(
        pdk_name="siepic_ebeam",
        rules=[],
        layer_map={},
    )
    with pytest.raises(ValueError, match="已注册"):
        register_drc_ruleset(duplicate_pdk_name, duplicate_ruleset)


def test_register_drc_ruleset_name_mismatch_raises_valueerror():
    """数据一致性: ruleset.pdk_name 与注册键不一致时 raise ValueError。"""
    mismatch_pdk_name = "test_mismatch_unique_xyz"
    mismatch_ruleset = DRCRuleset(
        pdk_name="different_name",  # 与注册键不一致
        rules=[],
        layer_map={},
    )
    try:
        with pytest.raises(ValueError, match="不一致"):
            register_drc_ruleset(mismatch_pdk_name, mismatch_ruleset)
        # 注册失败，确认未污染注册表
        assert mismatch_pdk_name not in list_available_pdk_rulesets()
    finally:
        # 双保险清理
        if mismatch_pdk_name in DRC_RULESETS:
            del DRC_RULESETS[mismatch_pdk_name]


# =============================================================================
# 6. 列表: list_available_pdk_rulesets
# =============================================================================


def test_list_available_pdk_rulesets():
    """list_available_pdk_rulesets 应返回 4 个内置 PDK，按字母序排列。"""
    listed = list_available_pdk_rulesets()
    expected = {"siepic_ebeam", "imec_isipp50g", "amf", "ligentec_sic"}
    assert set(listed) == expected
    assert len(listed) == 4
    # 应按字母序排列
    assert listed == sorted(expected)


# =============================================================================
# 7. 规则集派生正确性: 与 DEFAULT_DRC_RULES 一致性
# =============================================================================


def test_siepic_ruleset_matches_default_except_pdk_name():
    """SiEPIC 规则集应与 DEFAULT_DRC_RULES 一致（除 pdk_name 与 EXTENSION layer_pair 外）。

    验证 _derive_ruleset 的派生逻辑:
    - SiEPIC bend_radius_min=5.0 与 DEFAULT_DRC_RULES 的 BEND_RADIUS_MIN=5.0 相同
    - SiEPIC SEPARATION/ENCLOSURE/EXCLUSION 的 layer_pair 与 DEFAULT 相同
      （M1_HEATER/DEEPTRENCH）
    - SiEPIC EXTENSION 的 layer_pair 从 DEFAULT 的 "CONTACT" 调整为 "VIAC"
      （SiEPIC 接触层实际名为 VIAC，按 PDK 调整是 _derive_ruleset 的设计意图）
    - 唯一差异: SiEPIC 规则集的 pdk_name="siepic_ebeam"，DEFAULT 为 None
    """
    siepic = get_drc_ruleset("siepic_ebeam")
    assert len(siepic.rules) == len(DEFAULT_DRC_RULES)
    for derived_rule, default_rule in zip(siepic.rules, DEFAULT_DRC_RULES):
        # 名称、检查类型、阈值、严重程度应一致
        assert derived_rule.name == default_rule.name
        assert derived_rule.check_type == default_rule.check_type
        assert derived_rule.threshold == default_rule.threshold
        assert derived_rule.severity == default_rule.severity
        assert derived_rule.limit_max == default_rule.limit_max
        # layer_pair: EXTENSION 按 PDK 调整（CONTACT→VIAC），其余应一致
        if derived_rule.name == "EXTENSION":
            # SiEPIC 接触层名为 VIAC，DEFAULT 为 CONTACT（按 PDK 调整）
            assert derived_rule.layer_pair == "VIAC"
            assert default_rule.layer_pair == "CONTACT"
        else:
            assert derived_rule.layer_pair == default_rule.layer_pair
        # pdk_name 字段: SiEPIC 规则集设置为 "siepic_ebeam"，DEFAULT 为 None
        assert derived_rule.pdk_name == "siepic_ebeam"
        assert default_rule.pdk_name is None
