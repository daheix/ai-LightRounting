"""公开 Foundry 平台元数据（第13轮 P0-3 PDK 覆盖扩展）。

定义 11 个公开光电子 foundry 平台的技术参数元数据，使 PoLaRIS 的
PDK 覆盖从 4 平台扩展到 15 平台（4 内置 + 11 foundry），对齐
Luceda IPKISS 15+ PDK 的商业覆盖能力。

## 数据来源

所有参数均来自公开文献（foundry 官网、开源 PDK 仓库、学术论文），
不使用任何 NDA 信息。每个平台的来源 URL 在 ``FoundryPlatform.sources``
字段中标注。

## 合规性

- project_rules.md 规则 18: 所有 layer 编号/DRC 阈值来自开源仓库实际源码
- project_rules.md 规则 11.2: 标注 foundry 参数来源
- 差距分析 P0-3: docs/commercial_gap_analysis.md

来源:
- AIM Photonics: https://www.aimphotonics.com/
- AMF: http://c-fol.net/m/news/view.php?id=20190303014237
- CompoundTek: https://cloud.tencent.com/developer/article/2022690
- IHP SG25H5: https://www.ihp-microelectronics.com/fileadmin/user_upload/flyers_photonics2023.pdf
- GF Fotonix: https://europractice-ic.com/technologies/photonics/globalfoundries/
- Tower/OpenLight: http://www.c-fol.net/m/news/view.php?id=20250327095459
- LIGENTEC: https://www.meetoptics.com/suppliers/ligentec
- LioniX TriPleX: https://www.lionix-international.com/wp-content/uploads/2022/08/Briefings-MPW-manual.pdf
- VTT: https://cloud.tencent.com/developer/article/1678542
- Tyndall: https://pattern-project.eu/technology/material-platforms/inp-platform/
- HyperLight LNOI: https://www.hyperlightcorp.com/
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FoundryPlatform:
    """Foundry 平台元数据（公开参数，非 NDA）。

    Attributes:
        name: 平台唯一标识（如 ``"AIM"``、``"AMF"``）。
        foundry: foundry 厂商名（如 ``"AIM Photonics"``）。
        process_node: 工艺节点描述（如 ``"220nm SOI + SiN (300mm)"``）。
        material_platform: 材料平台分类（SOI/SiN/InP/LNOI/ThickSOI/Hybrid）。
        waveguide_width_um: 典型波导宽度（μm）。
        min_bend_radius_um: 最小弯曲半径（μm），公开文献典型值。
        waveguide_loss_db_cm: 波导损耗（dB/cm），公开文献典型值。
        wafer_size_mm: 晶圆直径（mm）。
        sources: 公开来源 URL 列表。
        notes: 补充说明（特色能力等）。
    """

    name: str
    foundry: str
    process_node: str
    material_platform: str
    waveguide_width_um: float
    min_bend_radius_um: float
    waveguide_loss_db_cm: float
    wafer_size_mm: int
    sources: list[str] = field(default_factory=list)
    notes: str = ""


# =============================================================================
# 11 个公开 Foundry 平台元数据
# 所有参数来自公开文献，非 NDA 信息
# =============================================================================

FOUNDRY_PLATFORMS: dict[str, FoundryPlatform] = {
    # --- 硅光 SOI 平台 ---
    "AIM": FoundryPlatform(
        name="AIM",
        foundry="AIM Photonics",
        process_node="220nm SOI + 220nm SiN (300mm)",
        material_platform="SOI",
        waveguide_width_um=0.45,
        min_bend_radius_um=5.0,
        waveguide_loss_db_cm=0.25,
        wafer_size_mm=300,
        sources=[
            "https://www.aimphotonics.com/aim-photonics-announces-bestinclass-300mm-silicon-photonics-multiproject-wafer-mpw-performance",
            "https://www.researchgate.net/publication/368684146_Design_Enablement_Methodology_for_Silicon_Photonics-Based_Photonic_Integrated_Design",
        ],
        notes="美国 AIM，300mm 晶圆，双层波导 SOI+SiN",
    ),
    "AMF": FoundryPlatform(
        name="AMF",
        foundry="Advanced Micro Foundry",
        process_node="0.13μm CMOS, 220nm SOI (200mm)",
        material_platform="SOI",
        waveguide_width_um=0.45,
        min_bend_radius_um=10.0,
        waveguide_loss_db_cm=2.0,
        wafer_size_mm=200,
        sources=[
            "http://c-fol.net/m/news/view.php?id=20190303014237",
            "http://www.iccsz.com/site/cn/News/2018/11/11/20181111074445123021.htm",
        ],
        notes="新加坡 AMF，0.13μm CMOS 工艺，56G MZI 调制器",
    ),
    "CompoundTek": FoundryPlatform(
        name="CompoundTek",
        foundry="CompoundTek",
        process_node="90nm, 220nm SOI (200mm)",
        material_platform="SOI",
        waveguide_width_um=0.45,
        min_bend_radius_um=10.0,
        waveguide_loss_db_cm=0.43,
        wafer_size_mm=200,
        sources=[
            "https://cloud.tencent.com/developer/article/2022690",
            "http://ydioe.pku.edu.cn/info/1162/1743.htm",
        ],
        notes="新加坡 CompoundTek，90nm 线宽，Si+SiN 集成",
    ),
    "IHP": FoundryPlatform(
        name="IHP",
        foundry="IHP Microelectronics",
        process_node="0.25μm BiCMOS + 220nm SOI (200mm)",
        material_platform="SOI",
        waveguide_width_um=0.45,
        min_bend_radius_um=5.0,
        waveguide_loss_db_cm=3.0,
        wafer_size_mm=200,
        sources=[
            "https://www.ihp-microelectronics.com/fileadmin/user_upload/flyers_photonics2023.pdf",
            "https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service/sigec-bicmos-technologies",
        ],
        notes="德国 IHP SG25H5，BiCMOS+光子集成，HBT fT=220GHz",
    ),
    "GF_Fotonix": FoundryPlatform(
        name="GF_Fotonix",
        foundry="GlobalFoundries",
        process_node="45nm CMOS, 160nm Si (300mm)",
        material_platform="SOI",
        waveguide_width_um=0.5,
        min_bend_radius_um=1.5,
        waveguide_loss_db_cm=1.0,
        wafer_size_mm=300,
        sources=[
            "https://europractice-ic.com/technologies/photonics/globalfoundries/",
            "https://cloud.tencent.com/developer/article/1868223",
        ],
        notes="GF Fotonix 45SPCLO，单片集成 45nm RFCMOS+光子",
    ),
    "Tower_OpenLight": FoundryPlatform(
        name="Tower_OpenLight",
        foundry="Tower Semiconductor / OpenLight",
        process_node="PH18DA, 220nm SOI (200mm)",
        material_platform="Hybrid",
        waveguide_width_um=0.45,
        min_bend_radius_um=5.0,
        waveguide_loss_db_cm=1.0,
        wafer_size_mm=200,
        sources=[
            "http://www.c-fol.net/m/news/view.php?id=20250327095459",
            "https://cloud.tencent.cn/developer/article/2512304",
        ],
        notes="Tower/OpenLight，InP 异质集成，448Gbps 单通道",
    ),
    # --- SiN 平台 ---
    "LIGENTEC": FoundryPlatform(
        name="LIGENTEC",
        foundry="LIGENTEC",
        process_node="AN800, 800nm SiN (200mm)",
        material_platform="SiN",
        waveguide_width_um=0.8,
        min_bend_radius_um=100.0,
        waveguide_loss_db_cm=0.1,
        wafer_size_mm=200,
        sources=[
            "https://www.meetoptics.com/suppliers/ligentec",
            "https://zenodo.org/record/7937413/files/ome-13-2-458.pdf",
        ],
        notes="瑞士 LIGENTEC，全氮化物波导，Q>20M，400-4000nm 透明窗口",
    ),
    "LioniX": FoundryPlatform(
        name="LioniX",
        foundry="LioniX International",
        process_node="TriPleX SiN LPCVD (100mm)",
        material_platform="SiN",
        waveguide_width_um=1.4,
        min_bend_radius_um=125.0,
        waveguide_loss_db_cm=0.5,
        wafer_size_mm=100,
        sources=[
            "https://www.lionix-international.com/wp-content/uploads/2022/08/Briefings-MPW-manual.pdf",
            "https://europractice-ic.com/technologies/photonics/lionix-techs/",
        ],
        notes="荷兰 LioniX TriPleX，Si3N4/SiO2 多层，MFD 1.4-3.6μm",
    ),
    # --- 厚膜 SOI 平台 ---
    "VTT": FoundryPlatform(
        name="VTT",
        foundry="VTT Technical Research Centre",
        process_node="3μm Thick SOI (150mm)",
        material_platform="ThickSOI",
        waveguide_width_um=3.0,
        min_bend_radius_um=1.3,
        waveguide_loss_db_cm=0.1,
        wafer_size_mm=150,
        sources=[
            "https://cloud.tencent.com/developer/article/1678542",
            "https://www.omedasemi.com/news/641.html",
        ],
        notes="芬兰 VTT，3μm 厚膜 SOI，Euler bend 1.3μm，偏振不敏感",
    ),
    # --- InP 异质集成平台 ---
    "Tyndall": FoundryPlatform(
        name="Tyndall",
        foundry="Tyndall National Institute",
        process_node="InP + SOI Heterogeneous (300mm)",
        material_platform="Hybrid",
        waveguide_width_um=0.5,
        min_bend_radius_um=500.0,
        waveguide_loss_db_cm=2.0,
        wafer_size_mm=300,
        sources=[
            "https://pattern-project.eu/technology/material-platforms/inp-platform/",
            "https://pubs.aip.org/aip/apl/article-pdf/doi/10.1063/5.0223167/20123271/081104_1_5.0223167.pdf",
        ],
        notes="爱尔兰 Tyndall，InP DBR 激光器异质集成，μTP 工艺",
    ),
    # --- LNOI 薄膜铌酸锂平台 ---
    "HyperLight": FoundryPlatform(
        name="HyperLight",
        foundry="HyperLight Corporation",
        process_node="600nm LNOI X-cut (100mm)",
        material_platform="LNOI",
        waveguide_width_um=0.8,
        min_bend_radius_um=80.0,
        waveguide_loss_db_cm=0.5,
        wafer_size_mm=100,
        sources=[
            "https://www.hyperlightcorp.com/",
            "https://doi.org/10.1038/s41377-024-01389-6",
        ],
        notes="美国 HyperLight，X-cut LNOI，Pockels 调制 100GHz，CMOS 兼容",
    ),
}


def get_foundry_platform(name: str) -> FoundryPlatform:
    """查询 foundry 平台元数据。

    Args:
        name: 平台唯一标识（如 ``"AIM"``、``"AMF"``）。

    Returns:
        对应的 ``FoundryPlatform`` 实例。

    Raises:
        KeyError: 平台不在注册表中。
    """
    try:
        return FOUNDRY_PLATFORMS[name]
    except KeyError:
        raise KeyError(
            f"Foundry 平台 '{name}' 不在注册表中，"
            f"可用: {list(FOUNDRY_PLATFORMS.keys())}"
        ) from None


def list_foundry_platforms() -> list[str]:
    """列出所有已注册的 foundry 平台名。

    Returns:
        平台名列表（11 个公开 foundry 平台）。
    """
    return list(FOUNDRY_PLATFORMS.keys())


def list_foundry_platforms_by_material(material: str) -> list[str]:
    """按材料平台筛选 foundry。

    Args:
        material: 材料平台分类（SOI/SiN/InP/LNOI/ThickSOI/Hybrid）。

    Returns:
        匹配材料平台的 foundry 名列表。
    """
    return [
        name
        for name, fp in FOUNDRY_PLATFORMS.items()
        if fp.material_platform == material
    ]


def foundry_platform_count() -> int:
    """返回已注册的 foundry 平台总数。

    Returns:
        平台数量（当前 11 个公开 foundry 平台）。
    """
    return len(FOUNDRY_PLATFORMS)


__all__ = [
    "FOUNDRY_PLATFORMS",
    "FoundryPlatform",
    "foundry_platform_count",
    "get_foundry_platform",
    "list_foundry_platforms",
    "list_foundry_platforms_by_material",
]
