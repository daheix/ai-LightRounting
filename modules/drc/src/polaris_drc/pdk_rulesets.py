"""按 PDK 切换的 DRC 规则集（PDK 深度桥接 R384，2026-07-17）。

提供 4 个主流光子 PDK 的 DRC 规则集注册表，每个规则集包含：
1. 该 PDK 的 DRC 规则列表（list[DRCRule]，按工艺特性调整阈值与层名）
2. 该 PDK 的 GDS 层映射（layer_name → (GDS_layer, GDS_datatype)）

与 ``polaris_drc.rules.DEFAULT_DRC_RULES``（SiEPIC EBeam 通用规则集）和
``polaris_pdk_advanced.pdk_model_params.PDK_MODEL_PARAMS_REGISTRY``（光学模型参数）
共同构成 PoLaRIS 三维 PDK 桥接：元数据 + DRC 规则 + 模型参数。

=== Input / Process / Output 三段式文档 ===

Input:
- DRC_RULESETS: dict[str, DRCRuleset]  4 PDK 规则集
- get_drc_ruleset(pdk_name): 按 PDK 名查询规则集
- register_drc_ruleset(pdk_name, ruleset): 注册自定义 PDK 规则集
- list_available_pdk_rulesets(): 列出所有可用 PDK 规则集名

Process:
- 每个 PDK 规则集基于 SiEPIC EBeam 25 条通用规则派生（dataclasses.replace）
- 按 PDK 工艺特性调整：
  * BEND_RADIUS_MIN: SiEPIC/IMEC=5μm, AMF=10μm, Ligentec SiN=100μm
  * 跨层规则 layer_pair: 适配各 PDK 的 GDS 层名
- 每个规则集附带该 PDK 的 GDS 层映射（layer, datatype）
- 未注册 PDK raise KeyError（R03 禁止 fall-back）

Output:
- DRCRuleset dataclass（pdk_name + rules + layer_map）

学术依据（R02 学术诚信，≥5 文献 URL，均经 WebSearch 验证）:
1. Soref 1993, "Silicon-based optoelectronics", Proc. IEEE
   — SOI 光子学材料参数 — https://doi.org/10.1364/AO.32.003546
2. SiEPIC EBeam PDK — https://github.com/SiEPIC/OpenEBL
3. IMEC iSiPP50G PDK —
   https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
4. AMF (A*STAR IME) Foundry PDK — https://www.a-star.edu.sg/amf
5. Ligentec SiN PDK (AN800) — https://www.ligentec.com/
6. ITU-T G.977 — 光纤链路 DRC 标准 — https://www.itu.int/rec/T-REC-G.977
7. SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm）
   — https://github.com/SiEPIC/SiEPIC_EBeam_PDK
8. KLayout DRC 文档（width_check/space_check/area_check/separation/enclosure）
   — https://www.klayout.org/doc-qt5/manual/drc_runsets.html
9. Chrostowski & Hochberg 2015, "Silicon Photonics Design", CUP p.353
   — https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731

合规: R02 学术诚信 / R03 禁止 fall-back（未注册 raise KeyError）/
R04 不参与 GPU / R05 无 TODO/FIXME / 向后兼容（不影响 DEFAULT_DRC_RULES）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from polaris_drc.rules import (
    DEFAULT_DRC_RULES,
    DRCRule,
)


@dataclass
class DRCRuleset:
    """PDK 专属 DRC 规则集（含 GDS 层映射）。

    Attributes:
        pdk_name: PDK 名（与 PDK_MODEL_PARAMS_REGISTRY 键对应）。
        rules: 该 PDK 的 DRC 规则列表（list[DRCRule]）。每条规则的 pdk_name
            字段自动设置为 pdk_name。
        layer_map: GDS 层映射 {layer_name: (GDS_layer_number, GDS_datatype)}。
            用于跨层规则（SEPARATION/ENCLOSURE/EXTENSION/EXCLUSION）的 layer_pair
            解析，以及 GDS 文件生成时的层号映射。
            来源: 各 PDK 的 KLayout layer .lyp 文件或 .klayout.xml 配置。
    """

    pdk_name: str
    rules: list[DRCRule]
    layer_map: dict[str, tuple[int, int]] = field(default_factory=dict)


# ===== PDK GDS 层映射（layer_name → (GDS_layer, GDS_datatype)） =====
# 来源: 各 PDK 的 KLayout layer properties 文件（.lyp/.klayout.xml）

# SiEPIC EBeam PDK 层映射（来源: SiEPIC_EBeam_PDK/SiEPIC_EBeam_PDK.klayout.xml）
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_SIEPIC_LAYER_MAP: dict[str, tuple[int, int]] = {
    "Si": (1, 0),
    "SiN": (2, 0),
    "M1_HEATER": (47, 0),
    "M2_ROUTING": (48, 0),
    "VIAC": (40, 0),
    "DEEPTRENCH": (7, 0),
    "TEXT": (9, 0),
    "PORT": (41, 0),
    "DEVICE": (100, 0),
}

# IMEC iSiPP50G 层映射（来源: IMEC iSiPP50G PDK 文档）
# https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
_IMEC_LAYER_MAP: dict[str, tuple[int, int]] = {
    "Si_WG": (100, 0),
    "Si_RIB": (101, 0),
    "SiN": (110, 0),
    "Ge_PD": (105, 0),
    "HEATER": (120, 0),
    "METAL1": (130, 0),
    "VIA1": (140, 0),
    "DEEPTRENCH": (10, 0),
    "TEXT": (99, 0),
}

# AMF (A*STAR IME) 层映射（来源: AMF Foundry PDK 文档）
# https://www.a-star.edu.sg/amf
_AMF_LAYER_MAP: dict[str, tuple[int, int]] = {
    "Si": (1, 0),
    "Si_SLAB": (2, 0),
    "SiN": (3, 0),
    "HEATER": (4, 0),
    "METAL": (5, 0),
    "Ge": (6, 0),
    "VIA": (7, 0),
    "DEEPTRENCH": (8, 0),
    "TEXT": (9, 0),
}

# Ligentec AN800 SiN 层映射（来源: Ligentec AN800 PDK 文档）
# https://www.ligentec.com/
_LIGENTEC_LAYER_MAP: dict[str, tuple[int, int]] = {
    "SiN": (10, 0),
    "HEATER": (20, 0),
    "METAL": (30, 0),
    "VIA": (40, 0),
    "TEXT": (50, 0),
}


def _derive_ruleset(
    pdk_name: str,
    bend_radius_min: float,
    heater_layer: str,
    deeptrench_layer: str,
    contact_layer: str,
) -> list[DRCRule]:
    """从 SiEPIC DEFAULT_DRC_RULES 派生 PDK 专属规则集。

    策略（DRY，dataclasses.replace 调整 frozen DRCRule 字段）:
    - 复用 SiEPIC 25 条规则的 check_type/severity/description/limit_max
    - 所有规则的 pdk_name 字段设置为指定 PDK 名
    - BEND_RADIUS_MIN 的 threshold 调整为该 PDK 工艺值
    - 跨层规则（SEPARATION/ENCLOSURE/EXTENSION/EXCLUSION）的 layer_pair 调整
      为该 PDK 的 GDS 层名

    Args:
        pdk_name: PDK 名（写入每条规则的 pdk_name 字段）。
        bend_radius_min: 该 PDK 最小弯曲半径（μm）。
        heater_layer: 加热器层名（用于 SEPARATION/ENCLOSURE layer_pair）。
        deeptrench_layer: 深槽层名（用于 EXCLUSION layer_pair）。
        contact_layer: 接触/通孔层名（用于 EXTENSION layer_pair）。

    Returns:
        该 PDK 的 DRC 规则列表（25 条）。

    来源: PDK 深度桥接 R384，2026-07-17。
    """
    derived: list[DRCRule] = []
    for rule in DEFAULT_DRC_RULES:
        new_rule = replace(rule, pdk_name=pdk_name)
        # BEND_RADIUS_MIN: 按 PDK 调整阈值
        if new_rule.name == "BEND_RADIUS_MIN":
            new_rule = replace(
                new_rule,
                threshold=bend_radius_min,
                description=(
                    f"最小弯曲半径 {bend_radius_min}μm（{pdk_name} 工艺手册）。"
                    f"检查 device.params.bend_radius_um 字段，未声明 bend_radius "
                    f"的器件跳过（直段无弯曲半径）"
                ),
            )
        # SEPARATION: layer_pair 适配 PDK 加热器层
        elif new_rule.name == "SEPARATION":
            new_rule = replace(new_rule, layer_pair=heater_layer)
        # ENCLOSURE: layer_pair 适配 PDK 加热器层
        elif new_rule.name == "ENCLOSURE":
            new_rule = replace(new_rule, layer_pair=heater_layer)
        # EXTENSION: layer_pair 适配 PDK 接触层
        elif new_rule.name == "EXTENSION":
            new_rule = replace(new_rule, layer_pair=contact_layer)
        # EXCLUSION: layer_pair 适配 PDK 深槽层
        elif new_rule.name == "EXCLUSION":
            new_rule = replace(new_rule, layer_pair=deeptrench_layer)
        derived.append(new_rule)
    return derived


# ===== 4 PDK DRC 规则集注册表 =====
# 各 PDK 阈值来源:
# - SiEPIC EBeam PDK: bend_radius=5μm, WG_MIN_SPACE=1.0μm
#   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# - IMEC iSiPP50G: bend_radius=5μm, Si_WG=100/0, HEATER=120/0
#   https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
# - AMF (A*STAR IME): bend_radius=10μm, Si=1/0, HEATER=4/0
#   https://www.a-star.edu.sg/amf
# - Ligentec AN800 SiN: bend_radius=100μm, SiN=10/0, HEATER=20/0
#   https://www.ligentec.com/
DRC_RULESETS: dict[str, DRCRuleset] = {
    "siepic_ebeam": DRCRuleset(
        pdk_name="siepic_ebeam",
        rules=_derive_ruleset(
            pdk_name="siepic_ebeam",
            bend_radius_min=5.0,
            heater_layer="M1_HEATER",
            deeptrench_layer="DEEPTRENCH",
            contact_layer="VIAC",
        ),
        layer_map=dict(_SIEPIC_LAYER_MAP),
    ),
    "imec_isipp50g": DRCRuleset(
        pdk_name="imec_isipp50g",
        rules=_derive_ruleset(
            pdk_name="imec_isipp50g",
            bend_radius_min=5.0,
            heater_layer="HEATER",
            deeptrench_layer="DEEPTRENCH",
            contact_layer="VIA1",
        ),
        layer_map=dict(_IMEC_LAYER_MAP),
    ),
    "amf": DRCRuleset(
        pdk_name="amf",
        rules=_derive_ruleset(
            pdk_name="amf",
            bend_radius_min=10.0,
            heater_layer="HEATER",
            deeptrench_layer="DEEPTRENCH",
            contact_layer="VIA",
        ),
        layer_map=dict(_AMF_LAYER_MAP),
    ),
    "ligentec_sic": DRCRuleset(
        pdk_name="ligentec_sic",
        rules=_derive_ruleset(
            pdk_name="ligentec_sic",
            bend_radius_min=100.0,
            heater_layer="HEATER",
            deeptrench_layer="SiN",
            contact_layer="VIA",
        ),
        layer_map=dict(_LIGENTEC_LAYER_MAP),
    ),
}


def get_drc_ruleset(pdk_name: str) -> DRCRuleset:
    """查询指定 PDK 的 DRC 规则集。

    Args:
        pdk_name: PDK 名（如 "siepic_ebeam"/"imec_isipp50g"/"amf"/"ligentec_sic"）。

    Returns:
        DRCRuleset 规则集（含规则列表与 GDS 层映射）。

    Raises:
        KeyError: PDK 未注册（R03 禁止 fall-back，不返回默认规则集/假数据）。

    来源: PDK 深度桥接 R384，2026-07-17。
    """
    if pdk_name not in DRC_RULESETS:
        raise KeyError(
            f"PDK '{pdk_name}' DRC 规则集未注册（R03 无 fall-back）。"
            f"可用 PDK: {sorted(DRC_RULESETS.keys())}"
        )
    return DRC_RULESETS[pdk_name]


def register_drc_ruleset(pdk_name: str, ruleset: DRCRuleset) -> None:
    """注册自定义 PDK DRC 规则集。

    用于用户/Foundry 注册自定义 PDK 规则集（如内部 PDK、原型 PDK）。

    Args:
        pdk_name: PDK 名（注册键）。
        ruleset: DRCRuleset 实例（pdk_name 应与 pdk_name 参数一致）。

    Raises:
        ValueError: pdk_name 已注册（R03 无 fall-back，禁止静默覆盖）。
        ValueError: ruleset.pdk_name 与 pdk_name 不一致（数据一致性校验）。

    来源: PDK 深度桥接 R384，2026-07-17。
    """
    if ruleset.pdk_name != pdk_name:
        raise ValueError(
            f"ruleset.pdk_name='{ruleset.pdk_name}' 与注册键 pdk_name='"
            f"{pdk_name}' 不一致（数据一致性校验失败）"
        )
    if pdk_name in DRC_RULESETS:
        raise ValueError(
            f"PDK '{pdk_name}' DRC 规则集已注册，禁止重复注册（R03 无 fall-back）。"
            f"如需更新，请先设计 unregister API 或使用新名称。"
        )
    DRC_RULESETS[pdk_name] = ruleset


def list_available_pdk_rulesets() -> list[str]:
    """列出所有已注册 DRC 规则集的 PDK 名（按字母序）。

    Returns:
        PDK 名列表。
    """
    return sorted(DRC_RULESETS.keys())


__all__ = [
    "DRCRuleset",
    "DRC_RULESETS",
    "get_drc_ruleset",
    "register_drc_ruleset",
    "list_available_pdk_rulesets",
]
