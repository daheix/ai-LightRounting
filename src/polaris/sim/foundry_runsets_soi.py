"""SOI 平台 foundry DRC runset（第86轮从 foundry_runsets.py 拆分）。

将 SOI 平台的 foundry runset（AMF/IHP/GF_Fotonix/CompoundTek）独立维护，
与 foundry_runsets_inplnoi.py（InP/LNOI 平台）形成对称的按平台拆分结构。

## 器件平台

- **SOI**：绝缘体上硅，主流硅光子平台（AMF/IHP/GF_Fotonix/CompoundTek）

## 来源（均为开源仓库/公开 PDK）

- AMF PDK (Luceda IPKISS): https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
- IHP SG25H5 (Open Source PDK): https://github.com/IHP-GmbH/IHP-Open-PDK
- GF Fotonix 45CLO: https://www.globalfoundries.com/en/press-release/globalfoundries-introduces-monolithic-photonics-platform
- CompoundTek (Luceda IPKISS): https://www.lucedaphotonics.com/zh_CN/luceda-design-kits

## 合规性: 规则 4.1（直接集成不复刻）/ 7.1（<500 行）/ 18（阈值来自开源仓库）
"""

from __future__ import annotations

from polaris.sim.constraint_checker import ViolationType
from polaris.sim.klayout_drc import DRCCheckType, DRCRule

# AMF (Advanced Micro Foundry) 180nm SOI runset - 来源: Luceda IPKISS AMF PDK
# https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
AMF_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="AMF_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF WG 最小宽度 0.4μm（180nm SOI 工艺极限）",
    ),
    DRCRule(
        name="AMF_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.5,
        vtype=ViolationType.SPACING,
        description="AMF WG 最小间距 1.5μm（避免波导耦合串扰）",
    ),
    DRCRule(
        name="AMF_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.7,
        vtype=ViolationType.NOTCH,
        description="AMF WG 最小凹槽间距 0.7μm",
    ),
    DRCRule(
        name="AMF_WG_MIN_AREA",
        layer_name="WG",
        check_type=DRCCheckType.AREA,
        threshold_um=0.16,
        vtype=ViolationType.MIN_AREA,
        description="AMF WG 最小面积 0.16μm²",
    ),
    DRCRule(
        name="AMF_SLAB150_MIN_WIDTH",
        layer_name="SLAB150",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF SLAB150 最小宽度 0.5μm",
    ),
    DRCRule(
        name="AMF_GE_MIN_WIDTH",
        layer_name="GE",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF GE 最小宽度 1.0μm（锗外延工艺极限）",
    ),
    DRCRule(
        name="AMF_GE_MIN_SPACE",
        layer_name="GE",
        check_type=DRCCheckType.SPACE,
        threshold_um=0.5,
        vtype=ViolationType.SPACING,
        description="AMF GE 最小间距 0.5μm",
    ),
    DRCRule(
        name="AMF_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=2.0,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF M1_HEATER 最小宽度 2.0μm",
    ),
    DRCRule(
        name="AMF_M1_MIN_SPACE",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.SPACE,
        threshold_um=2.0,
        vtype=ViolationType.SPACING,
        description="AMF M1_HEATER 最小间距 2.0μm",
    ),
    DRCRule(
        name="AMF_DEEPTRENCH_MIN_WIDTH",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.WIDTH,
        threshold_um=3.0,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF DEEPTRENCH 最小宽度 3.0μm",
    ),
    DRCRule(
        name="AMF_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="AMF WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="AMF_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.8,
        vtype=ViolationType.MIN_WIDTH,
        description="AMF VIAC 接触孔最小宽度 0.8μm（180nm SOI 工艺）",
    ),
    DRCRule(
        name="AMF_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.4,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSEMENT,
        description="AMF VIAC 须被 M1_HEATER 包围 ≥0.4μm（180nm SOI 工艺）",
    ),
]


# IHP SG25H5 250nm BiCMOS SOI runset - 来源: IHP Open Source PDK
# https://github.com/IHP-GmbH/IHP-Open-PDK
IHP_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="IHP_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP WG 最小宽度 0.4μm（SG25H5 220nm SOI）",
    ),
    DRCRule(
        name="IHP_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.0,
        vtype=ViolationType.SPACING,
        description="IHP WG 最小间距 1.0μm",
    ),
    DRCRule(
        name="IHP_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.6,
        vtype=ViolationType.NOTCH,
        description="IHP WG 最小凹槽间距 0.6μm",
    ),
    DRCRule(
        name="IHP_SLAB90_MIN_WIDTH",
        layer_name="SLAB90",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP SLAB90 最小宽度 0.5μm（90nm slab 调制器）",
    ),
    DRCRule(
        name="IHP_GE_MIN_WIDTH",
        layer_name="GE",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP GE 最小宽度 1.0μm",
    ),
    DRCRule(
        name="IHP_N_MIN_WIDTH",
        layer_name="N",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP N 掺杂最小宽度 0.5μm",
    ),
    DRCRule(
        name="IHP_P_MIN_WIDTH",
        layer_name="P",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP P 掺杂最小宽度 0.5μm",
    ),
    DRCRule(
        name="IHP_NP_MIN_SPACE",
        layer_name="NP",
        check_type=DRCCheckType.SPACE,
        threshold_um=0.5,
        vtype=ViolationType.SPACING,
        description="IHP N+ 掺杂最小间距 0.5μm",
    ),
    DRCRule(
        name="IHP_PP_MIN_SPACE",
        layer_name="PP",
        check_type=DRCCheckType.SPACE,
        threshold_um=0.5,
        vtype=ViolationType.SPACING,
        description="IHP P+ 掺杂最小间距 0.5μm",
    ),
    DRCRule(
        name="IHP_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.5,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP M1_HEATER 最小宽度 1.5μm",
    ),
    DRCRule(
        name="IHP_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.8,
        vtype=ViolationType.MIN_WIDTH,
        description="IHP VIAC 接触孔最小宽度 0.8μm",
    ),
    DRCRule(
        name="IHP_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="IHP WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="IHP_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.3,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSEMENT,
        description="IHP VIAC 须被 M1_HEATER 包围 ≥0.3μm（250nm BiCMOS 工艺）",
    ),
]


# GF Fotonix 45CLO 45nm CMOS photonics runset - 来源: GF Fotonix 官方 + Luceda IPKISS GF PDK
# https://www.globalfoundries.com/en/press-release/globalfoundries-introduces-monolithic-photonics-platform
GF_FOTONIX_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="GF_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.3,
        vtype=ViolationType.MIN_WIDTH,
        description="GF WG 最小宽度 0.3μm（45CLO 45nm CMOS 工艺）",
    ),
    DRCRule(
        name="GF_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=0.8,
        vtype=ViolationType.SPACING,
        description="GF WG 最小间距 0.8μm（45nm 工艺紧凑布线）",
    ),
    DRCRule(
        name="GF_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.4,
        vtype=ViolationType.NOTCH,
        description="GF WG 最小凹槽间距 0.4μm",
    ),
    DRCRule(
        name="GF_WG_MIN_AREA",
        layer_name="WG",
        check_type=DRCCheckType.AREA,
        threshold_um=0.09,
        vtype=ViolationType.MIN_AREA,
        description="GF WG 最小面积 0.09μm²",
    ),
    DRCRule(
        name="GF_SLAB90_MIN_WIDTH",
        layer_name="SLAB90",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="GF SLAB90 最小宽度 0.4μm（45nm 调制器）",
    ),
    DRCRule(
        name="GF_GE_MIN_WIDTH",
        layer_name="GE",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.8,
        vtype=ViolationType.MIN_WIDTH,
        description="GF GE 最小宽度 0.8μm",
    ),
    DRCRule(
        name="GF_N_MIN_WIDTH",
        layer_name="N",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="GF N 掺杂最小宽度 0.4μm（45nm CMOS）",
    ),
    DRCRule(
        name="GF_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="GF M1_HEATER 最小宽度 1.0μm",
    ),
    DRCRule(
        name="GF_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="GF VIAC 接触孔最小宽度 0.5μm（45nm 工艺）",
    ),
    DRCRule(
        name="GF_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="GF WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="GF_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.2,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSEMENT,
        description="GF VIAC 须被 M1_HEATER 包围 ≥0.2μm（45nm CMOS 工艺）",
    ),
]


# CompoundTek 130nm SOI runset - 来源: CompoundTek 官方 + Luceda IPKISS CompoundTek PDK
# https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
COMPOUNDTEK_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="CT_WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="CompoundTek WG 最小宽度 0.4μm（130nm SOI）",
    ),
    DRCRule(
        name="CT_WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.2,
        vtype=ViolationType.SPACING,
        description="CompoundTek WG 最小间距 1.2μm",
    ),
    DRCRule(
        name="CT_WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.6,
        vtype=ViolationType.NOTCH,
        description="CompoundTek WG 最小凹槽间距 0.6μm",
    ),
    DRCRule(
        name="CT_SLAB150_MIN_WIDTH",
        layer_name="SLAB150",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="CompoundTek SLAB150 最小宽度 0.5μm",
    ),
    DRCRule(
        name="CT_GE_MIN_WIDTH",
        layer_name="GE",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="CompoundTek GE 最小宽度 1.0μm",
    ),
    DRCRule(
        name="CT_M1_MIN_WIDTH",
        layer_name="M1_HEATER",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.8,
        vtype=ViolationType.MIN_WIDTH,
        description="CompoundTek M1_HEATER 最小宽度 1.8μm",
    ),
    DRCRule(
        name="CT_WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,
        max_density=70.0,
        vtype=ViolationType.LAYER_DENSITY,
        description="CompoundTek WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="CT_VIAC_MIN_WIDTH",
        layer_name="VIAC",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.8,
        vtype=ViolationType.MIN_WIDTH,
        description="CompoundTek VIAC 接触孔最小宽度 0.8μm（130nm SOI 工艺）",
    ),
    DRCRule(
        name="CT_VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.4,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSEMENT,
        description="CompoundTek VIAC 须被 M1_HEATER 包围 ≥0.4μm（130nm SOI 工艺）",
    ),
]


__all__ = [
    "AMF_DRC_RUNSET",
    "COMPOUNDTEK_DRC_RUNSET",
    "GF_FOTONIX_DRC_RUNSET",
    "IHP_DRC_RUNSET",
]
