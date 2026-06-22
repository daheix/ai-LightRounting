"""CMOS photonics 工艺节点元数据（P1-3 深化，第28轮）。

定义 CMOS photonics 工艺节点元数据，使 PoLaRIS 支持主流 CMOS photonics
工艺节点（GF Fotonix/Tower PH18DA/IHP SG25H5/Intel/AMF），对齐
Cadence Innovus / Synopsys ICC2 的工艺节点支持能力。

## P1-3 差距修复目标

商业标杆（来源: docs/commercial_gap_analysis.md P1-3）：
- Cadence Innovus / Synopsys ICC2：支持 3nm/2nm 先进节点
- GF Fotonix 45CLO/90WG：45nm/90nm CMOS photonics
- Tower PH18DA by OpenLight：SiPh 平台
- IHP SG25H5：250nm BiCMOS photonics

PoLaRIS 现状（第27轮前）：
- 仅按材料平台分类（SOI/SiN/InP/LNOI），无 CMOS 节点标注
- foundry_platforms.py 有 process_node 字符串，但无结构化 CMOS 节点元数据

第28轮深化：
- 结构化 CMOS 节点元数据（node_name/foundry/cmos_node_um/...）
- CMOS 节点查询 API（按 foundry/按 CMOS 节点/按材料平台）
- process_node 字符串解析器（从 "45nm CMOS, 220nm SOI" 提取 CMOS 节点）

## 数据来源

所有参数均来自公开文献（foundry 官网、开源 PDK 仓库、学术论文），
不使用任何 NDA 信息。

来源:
- GF Fotonix: https://www.globalfoundries.com/technology-innovation/silicon-photonics
- Tower/OpenLight: https://www.openlightphotonics.com/
- IHP SG25H5: https://www.ihp-microelectronics.com/fileadmin/user_upload/flyers_photonics2023.pdf
- Intel 300mm CMOS photonics: https://www.intel.com/content/www/us/en/newsroom/news/intel-unveils-300mm-silicon-photonics-fab.html
- AMF: http://c-fol.net/m/news/view.php?id=20190303014237
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProcessNode:
    """CMOS photonics 工艺节点元数据（公开参数，非 NDA）。

    Attributes:
        name: 工艺节点唯一标识（如 ``"GF_Fotonix_45CLO"``）。
        foundry: foundry 厂商名（如 ``"GlobalFoundries"``）。
        cmos_node_nm: CMOS 工艺节点（nm，如 45/90/130/180/250）。
            纯光子平台（无 CMOS）为 0。
        photonic_layer_nm: 光子层厚度（nm，如 220nm SOI）。
        material_platform: 材料平台分类（SOI/SiN/InP/LNOI/ThickSOI/Hybrid）。
        wafer_size_mm: 晶圆直径（mm）。
        integration_type: 集成类型（monolithic/heterogeneous/hybrid）。
        sources: 公开来源 URL 列表。
        notes: 补充说明。
    """

    name: str
    foundry: str
    cmos_node_nm: int
    photonic_layer_nm: int
    material_platform: str
    wafer_size_mm: int
    integration_type: str
    sources: list[str] = field(default_factory=list)
    notes: str = ""


# =============================================================================
# CMOS photonics 工艺节点注册表
# 所有参数来自公开文献，非 NDA 信息
# =============================================================================

CMOS_PROCESS_NODES: dict[str, ProcessNode] = {
    "GF_Fotonix_45CLO": ProcessNode(
        name="GF_Fotonix_45CLO",
        foundry="GlobalFoundries",
        cmos_node_nm=45,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=300,
        integration_type="monolithic",
        sources=[
            "https://www.globalfoundries.com/technology-innovation/silicon-photonics",
            "https://europractice-ic.com/technologies/photonics/globalfoundries/",
        ],
        notes="GF Fotonix 45CLO，45nm CMOS + 220nm SOI，单片集成光电子",
    ),
    "GF_Fotonix_90WG": ProcessNode(
        name="GF_Fotonix_90WG",
        foundry="GlobalFoundries",
        cmos_node_nm=90,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=200,
        integration_type="monolithic",
        sources=[
            "https://www.globalfoundries.com/technology-innovation/silicon-photonics",
        ],
        notes="GF Fotonix 90WG，90nm CMOS + 220nm SOI，波形发生器集成",
    ),
    "Tower_PH18DA": ProcessNode(
        name="Tower_PH18DA",
        foundry="Tower Semiconductor",
        cmos_node_nm=180,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=200,
        integration_type="monolithic",
        sources=[
            "https://www.towersemi.com/technology/technology-portfolio/silicon-photonics",
            "https://www.openlightphotonics.com/",
        ],
        notes="Tower PH18DA by OpenLight，180nm CMOS + 220nm SOI，集成激光器",
    ),
    "IHP_SG25H5": ProcessNode(
        name="IHP_SG25H5",
        foundry="IHP Microelectronics",
        cmos_node_nm=250,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=200,
        integration_type="monolithic",
        sources=[
            "https://www.ihp-microelectronics.com/fileadmin/user_upload/flyers_photonics2023.pdf",
            "https://www.ihp-microelectronics.com/en/services/mpw-prototyping/sigetec-sibicmos-technologies.html",
        ],
        notes="IHP SG25H5，250nm BiCMOS + 220nm SOI，含 HBT 高速晶体管",
    ),
    "Intel_300mm_CMOS_Ph": ProcessNode(
        name="Intel_300mm_CMOS_Ph",
        foundry="Intel",
        cmos_node_nm=90,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=300,
        integration_type="monolithic",
        sources=[
            "https://www.intel.com/content/www/us/en/newsroom/news/intel-unveils-300mm-silicon-photonics-fab.html",
        ],
        notes="Intel 300mm CMOS photonics，90nm CMOS + 220nm SOI，大规模制造",
    ),
    "AMF_130nm_CMOS": ProcessNode(
        name="AMF_130nm_CMOS",
        foundry="Advanced Micro Foundry",
        cmos_node_nm=130,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=200,
        integration_type="monolithic",
        sources=[
            "http://c-fol.net/m/news/view.php?id=20190303014237",
        ],
        notes="AMF 0.13μm CMOS，130nm CMOS + 220nm SOI",
    ),
    "AIM_300mm_SOI": ProcessNode(
        name="AIM_300mm_SOI",
        foundry="AIM Photonics",
        cmos_node_nm=0,  # 纯光子平台，无 CMOS
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=300,
        integration_type="photonic_only",
        sources=[
            "https://www.aimphotonics.com/",
        ],
        notes="AIM Photonics，300mm 纯光子平台，无 CMOS 集成",
    ),
    "LioniX_TriPleX": ProcessNode(
        name="LioniX_TriPleX",
        foundry="LioniX International",
        cmos_node_nm=0,  # 纯光子平台
        photonic_layer_nm=800,  # SiN 波导
        material_platform="SiN",
        wafer_size_mm=100,
        integration_type="photonic_only",
        sources=[
            "https://www.lionix-international.com/wp-content/uploads/2022/08/Briefings-MPW-manual.pdf",
        ],
        notes="LioniX TriPleX，SiN 平台，无 CMOS 集成",
    ),
    "HyperLight_LNOI": ProcessNode(
        name="HyperLight_LNOI",
        foundry="HyperLight",
        cmos_node_nm=0,  # 纯光子平台
        photonic_layer_nm=600,  # LNOI 薄膜
        material_platform="LNOI",
        wafer_size_mm=100,
        integration_type="photonic_only",
        sources=[
            "https://www.hyperlightcorp.com/",
        ],
        notes="HyperLight LNOI，X-cut 铌酸锂，Pockels 调制 100GHz",
    ),
    "CompoundTek_90nm_SOI": ProcessNode(
        name="CompoundTek_90nm_SOI",
        foundry="CompoundTek",
        cmos_node_nm=90,
        photonic_layer_nm=220,
        material_platform="SOI",
        wafer_size_mm=200,
        integration_type="monolithic",
        sources=[
            "https://cloud.tencent.com/developer/article/2022690",
            "http://ydioe.pku.edu.cn/info/1162/1743.htm",
        ],
        notes="CompoundTek 90nm SOI，新加坡硅光子代工，Si+SiN 集成",
    ),
    "LIGENTEC_AN800_SiN": ProcessNode(
        name="LIGENTEC_AN800_SiN",
        foundry="LIGENTEC",
        cmos_node_nm=0,  # 纯光子平台
        photonic_layer_nm=800,  # SiN 波导层
        material_platform="SiN",
        wafer_size_mm=200,
        integration_type="photonic_only",
        sources=[
            "https://www.meetoptics.com/suppliers/ligentec",
            "https://zenodo.org/record/7937413/files/ome-13-2-458.pdf",
        ],
        notes="LIGENTEC AN800，全氮化物波导，Q>20M，400-4000nm 透明窗口",
    ),
    "VTT_ThickSOI": ProcessNode(
        name="VTT_ThickSOI",
        foundry="VTT Technical Research Centre",
        cmos_node_nm=0,  # 纯光子平台
        photonic_layer_nm=3000,  # 3μm 厚膜 SOI
        material_platform="ThickSOI",
        wafer_size_mm=150,
        integration_type="photonic_only",
        sources=[
            "https://cloud.tencent.com/developer/article/1678542",
            "https://www.omedasemi.com/news/641.html",
        ],
        notes="VTT 3μm 厚膜 SOI，Euler bend 1.3μm，偏振不敏感",
    ),
    "Tyndall_InP_SOI_Hybrid": ProcessNode(
        name="Tyndall_InP_SOI_Hybrid",
        foundry="Tyndall National Institute",
        cmos_node_nm=0,  # 纯光子平台（异质集成）
        photonic_layer_nm=220,  # SOI 层
        material_platform="Hybrid",
        wafer_size_mm=300,
        integration_type="heterogeneous",
        sources=[
            "https://pattern-project.eu/technology/material-platforms/inp-platform/",
            "https://pubs.aip.org/aip/apl/article-pdf/doi/10.1063/5.0223167/20123271/081104_1_5.0223167.pdf",
        ],
        notes="Tyndall InP+SOI 异质集成，InP DBR 激光器 μTP 工艺",
    ),
}


def get_process_node(name: str) -> ProcessNode:
    """查询 CMOS photonics 工艺节点元数据。

    Args:
        name: 工艺节点唯一标识（如 ``"GF_Fotonix_45CLO"``）。

    Returns:
        对应的 ``ProcessNode`` 实例。

    Raises:
        KeyError: 节点不在注册表中。
    """
    try:
        return CMOS_PROCESS_NODES[name]
    except KeyError:
        raise KeyError(
            f"工艺节点 '{name}' 不在注册表中，"
            f"可用: {list(CMOS_PROCESS_NODES.keys())}"
        ) from None


def list_process_nodes() -> list[str]:
    """列出所有已注册的 CMOS photonics 工艺节点名。

    Returns:
        工艺节点名列表（9 个公开工艺节点）。
    """
    return list(CMOS_PROCESS_NODES.keys())


def list_process_nodes_by_cmos_node(cmos_node_nm: int) -> list[str]:
    """按 CMOS 节点筛选工艺节点。

    Args:
        cmos_node_nm: CMOS 工艺节点（nm，如 45/90/130/180/250）。
            0 表示纯光子平台（无 CMOS）。

    Returns:
        匹配 CMOS 节点的工艺节点名列表。
    """
    return [
        name
        for name, node in CMOS_PROCESS_NODES.items()
        if node.cmos_node_nm == cmos_node_nm
    ]


def list_process_nodes_by_foundry(foundry: str) -> list[str]:
    """按 foundry 厂商筛选工艺节点。

    Args:
        foundry: foundry 厂商名（如 ``"GlobalFoundries"``）。

    Returns:
        匹配 foundry 的工艺节点名列表。
    """
    return [
        name
        for name, node in CMOS_PROCESS_NODES.items()
        if node.foundry == foundry
    ]


def list_process_nodes_by_material(material: str) -> list[str]:
    """按材料平台筛选工艺节点。

    Args:
        material: 材料平台分类（SOI/SiN/InP/LNOI/ThickSOI/Hybrid）。

    Returns:
        匹配材料平台的工艺节点名列表。
    """
    return [
        name
        for name, node in CMOS_PROCESS_NODES.items()
        if node.material_platform == material
    ]


def cmos_process_node_count() -> int:
    """返回已注册的 CMOS photonics 工艺节点总数。

    Returns:
        工艺节点数量（当前 9 个公开工艺节点）。
    """
    return len(CMOS_PROCESS_NODES)


def _parse_cmos_node(process_node: str) -> int:
    """从 process_node 字符串解析 CMOS 节点（nm）。

    支持格式：``"45nm CMOS"`` / ``"0.13μm CMOS"`` / ``"90nm,"`` / ``"BiCMOS"``。

    Args:
        process_node: process_node 字符串。

    Returns:
        CMOS 节点（nm），无 CMOS 为 0。
    """
    cmos_patterns = [
        r"(\d+(?:\.\d+)?)\s*nm\s*CMOS",
        r"(\d+(?:\.\d+)?)\s*μm\s*CMOS",
        r"(\d+(?:\.\d+)?)\s*um\s*CMOS",
        r"BiCMOS",  # IHP SG25H5 标记为 BiCMOS
        # "90nm, 220nm SOI" 格式：数字+nm+逗号 + 后续 SOI/SiN/LNOI
        r"^(\d+)\s*nm\s*,\s*\d+\s*nm\s*(?:SOI|SiN|LNOI|Si)",
    ]
    for pattern in cmos_patterns:
        m = re.search(pattern, process_node, re.IGNORECASE)
        if m:
            if pattern == "BiCMOS":
                # BiCMOS 默认 250nm（IHP SG25H5）
                return 250
            val = float(m.group(1))
            # μm → nm 转换
            if "μm" in pattern or "um" in pattern:
                val = val * 1000
            return int(val)
    return 0


def _parse_photonic_layer(process_node: str) -> int:
    """从 process_node 字符串解析光子层厚度（nm）。

    支持格式：``"220nm SOI"`` / ``"800nm SiN"`` / ``"600nm LNOI"``。

    Args:
        process_node: process_node 字符串。

    Returns:
        光子层厚度（nm），无光子层为 0。
    """
    photonic_match = re.search(
        r"(\d+)\s*nm\s*(?:SOI|SiN|LNOI|Si)", process_node, re.IGNORECASE
    )
    if photonic_match:
        return int(photonic_match.group(1))
    return 0


def _parse_wafer_size(process_node: str) -> int:
    """从 process_node 字符串解析晶圆直径（mm）。

    支持格式：``"(300mm)"`` / ``"(200mm)"`` / ``"(150mm)"`` / ``"(100mm)"``。

    Args:
        process_node: process_node 字符串。

    Returns:
        晶圆直径（mm），无信息为 0。
    """
    wafer_match = re.search(r"\((\d+)\s*mm\)", process_node, re.IGNORECASE)
    if wafer_match:
        return int(wafer_match.group(1))
    return 0


def parse_process_node_string(process_node: str) -> dict:
    """从 process_node 字符串解析 CMOS 节点信息。

    解析 foundry_platforms.py 中的 process_node 字符串，提取 CMOS 节点
    和光子层信息。支持格式：
    - ``"45nm CMOS, 220nm SOI (300mm)"`` → {cmos_node_nm: 45, photonic_layer_nm: 220, ...}
    - ``"0.13μm CMOS, 220nm SOI (200mm)"`` → {cmos_node_nm: 130, ...}
    - ``"220nm SOI + 220nm SiN (300mm)"`` → {cmos_node_nm: 0, ...}
    - ``"90nm, 220nm SOI (200mm)"`` → {cmos_node_nm: 90, ...}

    Args:
        process_node: process_node 字符串。

    Returns:
        解析结果字典，含:
        - ``cmos_node_nm``: CMOS 节点（nm），无 CMOS 为 0
        - ``photonic_layer_nm``: 光子层厚度（nm），无光子层为 0
        - ``wafer_size_mm``: 晶圆直径（mm），无信息为 0
        - ``has_cmos``: 是否含 CMOS
    """
    cmos_node_nm = _parse_cmos_node(process_node)
    photonic_layer_nm = _parse_photonic_layer(process_node)
    wafer_size_mm = _parse_wafer_size(process_node)
    return {
        "cmos_node_nm": cmos_node_nm,
        "photonic_layer_nm": photonic_layer_nm,
        "wafer_size_mm": wafer_size_mm,
        "has_cmos": cmos_node_nm > 0,
    }


def suggest_process_node_for_circuit(
    cmos_node_nm: int = 0,
    material: str = "SOI",
) -> str | None:
    """为电路推荐合适的工艺节点。

    根据 CMOS 节点和材料平台需求，推荐最匹配的工艺节点。

    Args:
        cmos_node_nm: 期望的 CMOS 节点（nm），0 表示无 CMOS 需求。
        material: 材料平台（SOI/SiN/InP/LNOI）。

    Returns:
        推荐的工艺节点名，无匹配则 None。
    """
    candidates = [
        name
        for name, node in CMOS_PROCESS_NODES.items()
        if node.material_platform == material
    ]
    if cmos_node_nm > 0:
        # 优先精确匹配 CMOS 节点
        exact = [
            name for name in candidates
            if CMOS_PROCESS_NODES[name].cmos_node_nm == cmos_node_nm
        ]
        if exact:
            return exact[0]
        # 其次选择 CMOS 节点 <= 需求的最大者（更先进工艺）
        smaller = [
            name for name in candidates
            if 0 < CMOS_PROCESS_NODES[name].cmos_node_nm <= cmos_node_nm
        ]
        if smaller:
            return min(
                smaller,
                key=lambda n: CMOS_PROCESS_NODES[n].cmos_node_nm,
            )
    # 无 CMOS 需求，选纯光子平台
    photonic_only = [
        name for name in candidates
        if CMOS_PROCESS_NODES[name].cmos_node_nm == 0
    ]
    if photonic_only:
        return photonic_only[0]
    return candidates[0] if candidates else None


# =============================================================================
# Foundry 平台 → 结构化 ProcessNode 关联（第75轮 P1-3 深化）
# 来源: foundry_platforms.py FOUNDRY_PLATFORMS 注册表
# =============================================================================

# Foundry 平台名 → CMOS_PROCESS_NODES 键的映射
# 用于将 FoundryPlatform.process_node（字符串）关联到结构化 ProcessNode
# 第89轮：全量映射 11/11 foundry 平台（新增 CompoundTek/LIGENTEC/VTT/Tyndall）
_FOUNDRY_TO_PROCESS_NODE: dict[str, str] = {
    "AIM": "AIM_300mm_SOI",
    "AMF": "AMF_130nm_CMOS",
    "CompoundTek": "CompoundTek_90nm_SOI",
    "IHP": "IHP_SG25H5",
    "GF_Fotonix": "GF_Fotonix_45CLO",
    "Tower_OpenLight": "Tower_PH18DA",
    "LIGENTEC": "LIGENTEC_AN800_SiN",
    "LioniX": "LioniX_TriPleX",
    "VTT": "VTT_ThickSOI",
    "Tyndall": "Tyndall_InP_SOI_Hybrid",
    "HyperLight": "HyperLight_LNOI",
}


def get_process_node_for_foundry(foundry_name: str) -> ProcessNode | None:
    """按 foundry 平台名查询结构化工艺节点（第75/89轮 P1-3 深化）。

    将 FoundryPlatform.process_node（字符串）关联到 CMOS_PROCESS_NODES
    注册表中的结构化 ProcessNode，提供 foundry 平台与 CMOS 节点的双向查询能力。

    来源: foundry_platforms.py FOUNDRY_PLATFORMS 注册表（11 个 foundry 平台）。
    第89轮全量映射 11/11 foundry 平台（新增 CompoundTek/LIGENTEC/VTT/Tyndall）。

    Args:
        foundry_name: foundry 平台名（如 ``"AMF"``、``"GF_Fotonix"``）。

    Returns:
        对应的结构化 ``ProcessNode``，无映射则 None。
    """
    key = _FOUNDRY_TO_PROCESS_NODE.get(foundry_name)
    if key is None:
        return None
    return CMOS_PROCESS_NODES.get(key)


def list_foundries_with_process_node() -> list[str]:
    """列出有结构化工艺节点映射的 foundry 平台名（第75/89轮 P1-3 深化）。

    Returns:
        有结构化 ProcessNode 映射的 foundry 平台名列表（当前 11 个，全量映射）。
    """
    return list(_FOUNDRY_TO_PROCESS_NODE.keys())


__all__ = [
    "ProcessNode",
    "CMOS_PROCESS_NODES",
    "get_process_node",
    "list_process_nodes",
    "list_process_nodes_by_cmos_node",
    "list_process_nodes_by_foundry",
    "list_process_nodes_by_material",
    "cmos_process_node_count",
    "parse_process_node_string",
    "suggest_process_node_for_circuit",
    "get_process_node_for_foundry",
    "list_foundries_with_process_node",
]
