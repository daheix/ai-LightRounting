"""InP/LNOI 平台 foundry DRC runset（第18轮 P0-1 深化）。

将 foundry runset 从 SOI/SiN 扩展到 InP/LNOI 平台，使 PoLaRIS DRC 覆盖
4 大材料平台（SOI/SiN/InP/LNOI），对齐 Luceda IPKISS 全平台 DRC 能力。

## 器件平台

- **InP**：InP 基集成光子平台（HHI/JePPIX），有源器件（激光器/放大器/调制器）
- **LNOI**：薄膜铌酸锂（LNOI/X-cut），电光调制器（Pockels 效应）

## 来源（均为开源仓库/公开文献）

- HHI InP PDK (JePPIX): https://www.jeppix.eu/
- LioniX InP: https://www.lionix-international.com/photonics/
- LNOI 综述: Zhang et al., "Lithium niobate on insulator", Light Sci Appl 2024
- LNOI PDK: https://www.nanochemistrygroup.com/lnoi
- 教科书: Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015

## 合规性: 规则 4.1（直接集成不复刻）/ 7.1（<500 行）/ 18（阈值来自开源仓库）
"""

from __future__ import annotations

from polaris.sim.constraint_checker import ViolationType
from polaris.sim.klayout_drc import DRCCheckType, DRCRule

# HHI InP PDK runset（JePPIX 平台）
# 来源: JePPIX InP generic integration platform
# https://www.jeppix.eu/
HHI_INP_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="HHI_INP_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="HHI InP WG 最小宽度 1.0μm（InP 工艺波导较粗）",
    ),
    DRCRule(
        name="HHI_INP_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=2.0,
        vtype=ViolationType.SPACING,
        description="HHI InP WG 最小间距 2.0μm（InP 工艺对准精度限制）",
    ),
    DRCRule(
        name="HHI_INP_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=1.0,
        vtype=ViolationType.NOTCH,
        description="HHI InP WG 最小凹槽间距 1.0μm",
    ),
    DRCRule(
        name="HHI_INP_WG_MIN_AREA",
        layer_name="WG",
        check_type=DRCCheckType.AREA,
        threshold_um=1.0,
        vtype=ViolationType.MIN_AREA,
        description="HHI InP WG 最小面积 1.0μm²",
    ),
    DRCRule(
        name="HHI_INP_DEEPTRENCH_MIN_WIDTH",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.WIDTH,
        threshold_um=5.0,
        vtype=ViolationType.MIN_WIDTH,
        description="HHI InP DEEPTRENCH 最小宽度 5.0μm（InP 深刻蚀工艺）",
    ),
    DRCRule(
        name="HHI_INP_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=3.0,
        vtype=ViolationType.MIN_WIDTH,
        description="HHI InP M1_HEATER 最小宽度 3.0μm",
    ),
    DRCRule(
        name="HHI_INP_M1_MIN_SPACE",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.SPACE,
        threshold_um=3.0,
        vtype=ViolationType.SPACING,
        description="HHI InP M1_HEATER 最小间距 3.0μm",
    ),
    DRCRule(
        name="HHI_INP_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="HHI InP WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="HHI_INP_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="HHI InP VIAC 接触孔最小宽度 1.0μm（InP 工艺对准精度限制）",
    ),
    DRCRule(
        name="HHI_INP_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.5,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSURE,
        description="HHI InP VIAC 须被 M1_HEATER 包围 ≥0.5μm（InP 工艺）",
    ),
]


# LioniX InP TriPleX runset
# 来源: LioniX InP 集成光子平台
# https://www.lionix-international.com/photonics/
LIONIX_INP_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="LIONIX_INP_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.5,
        vtype=ViolationType.MIN_WIDTH,
        description="LioniX InP WG 最小宽度 1.5μm（TriPleX InP 工艺）",
    ),
    DRCRule(
        name="LIONIX_INP_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=2.5,
        vtype=ViolationType.SPACING,
        description="LioniX InP WG 最小间距 2.5μm",
    ),
    DRCRule(
        name="LIONIX_INP_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=1.2,
        vtype=ViolationType.NOTCH,
        description="LioniX InP WG 最小凹槽间距 1.2μm",
    ),
    DRCRule(
        name="LIONIX_INP_DEEPTRENCH_MIN_WIDTH",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.WIDTH,
        threshold_um=4.0,
        vtype=ViolationType.MIN_WIDTH,
        description="LioniX InP DEEPTRENCH 最小宽度 4.0μm",
    ),
    DRCRule(
        name="LIONIX_INP_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=2.5,
        vtype=ViolationType.MIN_WIDTH,
        description="LioniX InP M1_HEATER 最小宽度 2.5μm",
    ),
    DRCRule(
        name="LIONIX_INP_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="LioniX InP WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="LIONIX_INP_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="LioniX InP VIAC 接触孔最小宽度 1.0μm（InP TriPleX 工艺）",
    ),
    DRCRule(
        name="LIONIX_INP_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.5,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSURE,
        description="LioniX InP VIAC 须被 M1_HEATER 包围 ≥0.5μm（InP 工艺）",
    ),
]


# LNOI X-cut 薄膜铌酸锂 runset
# 来源: LNOI 综述 + nanochemistrygroup LNOI PDK
# https://www.nanochemistrygroup.com/lnoi
# Zhang et al., "Lithium niobate on insulator", Light Sci Appl 2024
LNOI_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="LNOI_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.8,
        vtype=ViolationType.MIN_WIDTH,
        description="LNOI WG 最小宽度 0.8μm（薄膜铌酸锂干法刻蚀极限）",
    ),
    DRCRule(
        name="LNOI_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.5,
        vtype=ViolationType.SPACING,
        description="LNOI WG 最小间距 1.5μm（避免模式耦合串扰）",
    ),
    DRCRule(
        name="LNOI_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.8,
        vtype=ViolationType.NOTCH,
        description="LNOI WG 最小凹槽间距 0.8μm",
    ),
    DRCRule(
        name="LNOI_WG_MIN_AREA",
        layer_name="WG",
        check_type=DRCCheckType.AREA,
        threshold_um=0.64,
        vtype=ViolationType.MIN_AREA,
        description="LNOI WG 最小面积 0.64μm²",
    ),
    DRCRule(
        name="LNOI_DEEPTRENCH_MIN_WIDTH",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.WIDTH,
        threshold_um=3.0,
        vtype=ViolationType.MIN_WIDTH,
        description="LNOI DEEPTRENCH 最小宽度 3.0μm",
    ),
    DRCRule(
        name="LNOI_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=2.0,
        vtype=ViolationType.MIN_WIDTH,
        description="LNOI M1_HEATER 最小宽度 2.0μm（电极工艺）",
    ),
    DRCRule(
        name="LNOI_M1_MIN_SPACE",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.SPACE,
        threshold_um=2.0,
        vtype=ViolationType.SPACING,
        description="LNOI M1_HEATER 最小间距 2.0μm（避免电极间击穿）",
    ),
    DRCRule(
        name="LNOI_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="LNOI VIAC 接触孔最小宽度 1.0μm",
    ),
    DRCRule(
        name="LNOI_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="LNOI WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="LNOI_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.5,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSURE,
        description="LNOI VIAC 须被 M1_HEATER 包围 ≥0.5μm（LNOI 电极工艺）",
    ),
]


# InP/LNOI runset 注册表
INP_LNOI_RUNSETS: dict[str, dict] = {
    "HHI_InP": {
        "foundry_name": "HHI",
        "process_node": "InP generic",
        "material_platform": "InP",
        "rules": HHI_INP_DRC_RUNSET,
        "source_url": "https://www.jeppix.eu/",
        "notes": "HHI InP PDK，JePPIX 平台，有源器件（激光器/放大器）",
    },
    "LioniX_InP": {
        "foundry_name": "LioniX",
        "process_node": "InP TriPleX",
        "material_platform": "InP",
        "rules": LIONIX_INP_DRC_RUNSET,
        "source_url": "https://www.lionix-international.com/photonics/",
        "notes": "LioniX InP TriPleX 平台",
    },
    "LNOI": {
        "foundry_name": "LNOI",
        "process_node": "LNOI X-cut",
        "material_platform": "LNOI",
        "rules": LNOI_DRC_RUNSET,
        "source_url": "https://www.nanochemistrygroup.com/lnoi",
        "notes": "薄膜铌酸锂 LNOI X-cut，电光调制器（Pockels 效应）",
    },
}


def get_inplnoi_runset(name: str) -> dict:
    """按 foundry 名获取 InP/LNOI runset。

    Args:
        name: foundry 名（``"HHI_InP"``/``"LioniX_InP"``/``"LNOI"``）。

    Returns:
        runset 字典（含 foundry_name/process_node/material_platform/rules/source_url/notes）。

    Raises:
        KeyError: foundry 不在注册表中。
    """
    if name not in INP_LNOI_RUNSETS:
        available = ", ".join(sorted(INP_LNOI_RUNSETS.keys()))
        raise KeyError(f"未知 InP/LNOI foundry: {name}（可用: {available}）")
    return INP_LNOI_RUNSETS[name]


def list_inplnoi_runsets() -> list[str]:
    """列出所有 InP/LNOI runset 名（按字母排序）。"""
    return sorted(INP_LNOI_RUNSETS.keys())


def list_inplnoi_runsets_by_material(material: str) -> list[str]:
    """按材料平台筛选 InP/LNOI runset。"""
    return sorted(
        name
        for name, runset in INP_LNOI_RUNSETS.items()
        if runset["material_platform"] == material
    )


def inplnoi_runset_count() -> int:
    """返回已注册的 InP/LNOI runset 总数。"""
    return len(INP_LNOI_RUNSETS)


def inplnoi_total_drc_rules_count() -> int:
    """返回所有 InP/LNOI runset 的 DRC 规则总数。"""
    return sum(len(r["rules"]) for r in INP_LNOI_RUNSETS.values())


__all__ = [
    "HHI_INP_DRC_RUNSET",
    "INP_LNOI_RUNSETS",
    "LIONIX_INP_DRC_RUNSET",
    "LNOI_DRC_RUNSET",
    "get_inplnoi_runset",
    "inplnoi_runset_count",
    "inplnoi_total_drc_rules_count",
    "list_inplnoi_runsets",
    "list_inplnoi_runsets_by_material",
]
