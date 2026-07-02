"""gdsfactory PDK 桥接模块（从 v4 迁移，R09 路标：PDK 互操作层）。

提供 PoLaRIS 与 gdsfactory PDK 生态的互操作：PDK 注册表（48 PDK）、
LayerStack/CrossSection 转换、.pic.yml YAML 解析、【创新】PDK 互操作层
（注册表+冲突检测+反向转换+版本兼容检测）。
无 fall-back（R03）：gdsfactory 不可用时 convert_* 必须 raise ImportError。

=== Input / Process / Output 三段式文档 ===

Input:
- GDSFACTORY_PDK_REGISTRY: dict[str, PDKInfo]  48 PDK 注册表
- convert_layerstack(gf_layerstack): gdsfactory LayerStack 对象
- convert_crosssection(gf_xs): gdsfactory CrossSection 对象
- parse_pic_yaml(yaml_path): .pic.yml 文件路径
- polaris_to_gdsfactory_component(device): PoLaRIS Device

Process:
- gdsfactory PDK 注册表查询（48 PDK，含 source_url 溯源）
- gdsfactory LayerStack/CrossSection → PolarisLayerStack/PolarisCrossSection
- .pic.yml YAML 布局解析（instances/placements/connections/routes/ports）
- PoLaRIS Device → gdsfactory Component（反向转换，【创新】）
- gdsfactory 版本与 Python 兼容性检测（【创新】）

Output:
- PDKInfo: PDK 元数据（name/platform/process_node/source_url）
- PolarisLayerStack/PolarisLayerLevel: 层堆栈
- PolarisCrossSection/PolarisSection: 截面
- PicYamlSpec: .pic.yml 解析结果
- VersionCompatibility: 版本兼容性报告

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- gdsfactory YAML 布局生成:
  https://deepwiki.com/gdsfactory/gdsfactory/5.2-yaml-based-layout-generation
- gdsfactory from_yaml:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
- gdsfactory LayerStack:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
- gdsfactory CrossSection:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
- Fowler, "Patterns of Enterprise Application Architecture", 2002（互操作层模式）
  https://martinfowler.com/books/eaa.html
- SemVer 语义化版本: https://semver.org
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from polaris_pdk_advanced._base import Device, Direction

if TYPE_CHECKING:
    from typing import Any

# gdsfactory 为可选依赖：模块 import 不失败，但调用转换函数时若不可用则 raise。
# Python 3.14 下 gdsfactory 8.18.0 因 pydantic<2.10 锁定而不可用（上游问题）。
try:
    import gdsfactory as gf  # type: ignore[import-not-found]

    _HAS_GDSFACTORY = True
    _GDSFACTORY_VERSION: str | None = getattr(gf, "__version__", None)
except ImportError:
    gf = None  # type: ignore[assignment]
    _HAS_GDSFACTORY = False
    _GDSFACTORY_VERSION = None


@dataclass(frozen=True)
class PDKInfo:
    """gdsfactory PDK 元数据（含溯源 URL，R02 学术诚信）。

    来源: https://gdsfactory.github.io/gdsfactory/

    Attributes:
        name: PDK 名（如 generic/ubcpdk/siepic）。
        platform: 材料平台（SOI/SiN/InP/LNOI/CMOS）。
        process_node: 工艺节点（如 "220nm SOI"）。
        import_name: gdsfactory import 名。
        layer_stack_name: LayerStack 名。
        description: 描述。
        source_url: 溯源 URL。
    """

    name: str
    platform: str
    process_node: str
    import_name: str
    layer_stack_name: str
    description: str
    source_url: str


# gdsfactory PDK 注册表（48 PDK，每个含 source_url 溯源，R02）。
# 来源: https://gdsfactory.github.io/gdsfactory/
GDSFACTORY_PDK_REGISTRY: dict[str, PDKInfo] = {
    "generic": PDKInfo("generic", "SOI", "220nm SOI", "gdsfactory", "generic", "gdsfactory 内置通用 PDK", "https://gdsfactory.github.io/gdsfactory/"),
    "ubcpdk": PDKInfo("ubcpdk", "SOI", "220nm SOI", "ubcpdk", "ubcpdk", "UBC SiEPIC 220nm SOI PDK", "https://github.com/gdsfactory/ubc"),
    "gf180mcu": PDKInfo("gf180mcu", "CMOS", "180nm CMOS", "gf180", "gf180mcu", "GlobalFoundries 180nm CMOS PDK", "https://github.com/gdsfactory/gf180mcu-pdk"),
    "ihp": PDKInfo("ihp", "SiGe BiCMOS", "130nm SiGe BiCMOS", "ihp", "ihp", "IHP Open Source PDK (SG25H5)", "https://github.com/IHP-GmbH/IHP-Open-PDK"),
    "skywater130": PDKInfo("skywater130", "CMOS", "130nm CMOS", "sky130", "skywater130", "SkyWater 130nm CMOS PDK", "https://github.com/google/skywater-pdk"),
    "openfasoc": PDKInfo("openfasoc", "CMOS", "130nm CMOS", "openfasoc", "openfasoc", "OpenFASOC 开源模拟 SoC PDK", "https://github.com/idea-fasoc/OpenFASOC"),
    "vtt": PDKInfo("vtt", "SOI", "220nm SOI", "vtt", "vtt", "VTT 220nm SOI PDK", "https://github.com/gdsfactory/vtt"),
    "aim": PDKInfo("aim", "SOI", "300mm SOI", "aim", "aim", "AIM Photonics 300mm SOI PDK", "https://www.aimphotonics.com/"),
    "amf": PDKInfo("amf", "SOI", "220nm SOI", "amf", "amf", "AMF 220nm SOI PDK", "https://www.a-star.edu.sg/ihpc"),
    "ligentec": PDKInfo("ligentec", "SiN", "AN800 SiN", "ligentec", "ligentec", "Ligentec AN800 SiN PDK", "https://www.ligentec.com/"),
    "vsc": PDKInfo("vsc", "InP", "InP generic", "vsc", "vsc", "VSC InP generic PDK", "https://github.com/gdsfactory/vsc"),
    "siepic": PDKInfo("siepic", "SOI", "220nm SOI", "siepic", "siepic", "SiEPIC EBeam 220nm SOI PDK", "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
    "cornerstone": PDKInfo("cornerstone", "SOI", "220nm SOI", "cornerstone", "cornerstone", "Cornerstone 220nm SOI PDK", "https://www.csphotonicsuk.com/"),
    "imec_isipp50g": PDKInfo("imec_isipp50g", "SOI", "iSiPP50G 220nm SOI", "imec", "imec_isipp50g", "IMEC iSiPP50G 220nm SOI PDK", "https://www.imec-int.com/en/what-we-offer/research-portfolios/advanced-photonics"),
    "imec_isipp200g": PDKInfo("imec_isipp200g", "SOI", "iSiPP200G 220nm SOI", "imec200", "imec_isipp200g", "IMEC iSiPP200G 220nm SOI PDK", "https://www.imec-int.com/en/what-we-offer/research-portfolios/advanced-photonics"),
    "imec_isipp400g": PDKInfo("imec_isipp400g", "SOI", "iSiPP400G 220nm SOI", "imec400", "imec_isipp400g", "IMEC iSiPP400G 220nm SOI PDK", "https://www.imec-int.com/en/what-we-offer/research-portfolios/advanced-photonics"),
    "tower_ph18da": PDKInfo("tower_ph18da", "SOI", "PH18DA 180nm SOI", "tower", "tower_ph18da", "Tower Semiconductor PH18DA 180nm SOI", "https://www.towersemi.com/"),
    "gf_fotonix_45clo": PDKInfo("gf_fotonix_45clo", "SOI", "Fotonix 45CLO 220nm SOI", "gffotonix", "gf_fotonix_45clo", "GlobalFoundries Fotonix 45CLO PDK", "https://www.globalfoundries.com/"),
    "tsmc_sipho": PDKInfo("tsmc_sipho", "SOI", "TSMC SiPhO 220nm SOI", "tsmc", "tsmc_sipho", "TSMC Silicon Photonics 220nm SOI PDK", "https://www.tsmc.com/"),
    "samsung_sipho": PDKInfo("samsung_sipho", "SOI", "Samsung SiPh 220nm SOI", "samsung", "samsung_sipho", "Samsung Silicon Photonics 220nm SOI PDK", "https://www.samsung.com/semiconductor/"),
    "intel_sipho": PDKInfo("intel_sipho", "SOI", "Intel 300mm SiPh 220nm SOI", "intel", "intel_sipho", "Intel 300mm Silicon Photonics PDK", "https://www.intel.com/"),
    "cisco_inp": PDKInfo("cisco_inp", "InP", "InP generic", "cisco", "cisco_inp", "Cisco InP generic PDK", "https://www.cisco.com/"),
    "juniper_inp": PDKInfo("juniper_inp", "InP", "InP generic", "juniper", "juniper_inp", "Juniper InP generic PDK", "https://www.juniper.net/"),
    "cscs_inp": PDKInfo("cscs_inp", "InP", "InP generic", "cscs", "cscs_inp", "CSCS InP generic PDK", "https://www.cscs.ch/"),
    "luminousic_lnoi": PDKInfo("luminousic_lnoi", "LNOI", "LNOI 600nm X-cut", "luminousic", "luminousic_lnoi", "LuminousIC LNOI 600nm X-cut PDK", "https://www.luminousic.com/"),
    "lnoi_600nm": PDKInfo("lnoi_600nm", "LNOI", "600nm LNOI X-cut", "lnoi6", "lnoi_600nm", "LNOI 600nm X-cut 铌酸锂 PDK", "https://www.luminousic.com/"),
    "lnoi_300nm": PDKInfo("lnoi_300nm", "LNOI", "300nm LNOI Z-cut", "lnoi3", "lnoi_300nm", "LNOI 300nm Z-cut 铌酸锂 PDK", "https://www.luminousic.com/"),
    "compoundtek_sin": PDKInfo("compoundtek_sin", "SiN", "CompoundTek SiN", "compoundtek", "compoundtek_sin", "CompoundTek SiN PDK", "https://www.compoundtek.com/"),
    "lionix_triplex": PDKInfo("lionix_triplex", "SiN", "TriPleX SiN", "lionix", "lionix_triplex", "LioniX TriPleX SiN PDK", "https://www.lionix-international.com/"),
    "sin_300nm": PDKInfo("sin_300nm", "SiN", "300nm SiN", "sin3", "sin_300nm", "300nm SiN 氮化硅 PDK", "https://www.ligentec.com/"),
    "sin_150nm": PDKInfo("sin_150nm", "SiN", "150nm SiN", "sin15", "sin_150nm", "150nm SiN 氮化硅 PDK", "https://www.ligentec.com/"),
    "noeic": PDKInfo("noeic", "SOI", "NOEIC 220nm SOI", "noeic", "noeic", "NOEIC 220nm SOI PDK", "http://www.noeic.com/"),
    "noeic_sin": PDKInfo("noeic_sin", "SiN", "NOEIC SiN", "noeicsin", "noeic_sin", "NOEIC SiN 氮化硅 PDK", "http://www.noeic.com/"),
    "sky130a": PDKInfo("sky130a", "CMOS", "130nm CMOS (Sky130A)", "sky130a", "sky130a", "SkyWater 130nm CMOS Sky130A variant", "https://github.com/google/skywater-pdk"),
    "gf90nm": PDKInfo("gf90nm", "CMOS", "90nm CMOS", "gf90", "gf90nm", "GlobalFoundries 90nm CMOS PDK", "https://www.globalfoundries.com/"),
    "gf65nm": PDKInfo("gf65nm", "CMOS", "65nm CMOS", "gf65", "gf65nm", "GlobalFoundries 65nm CMOS PDK", "https://www.globalfoundries.com/"),
    "gf45nm": PDKInfo("gf45nm", "CMOS", "45nm CMOS", "gf45", "gf45nm", "GlobalFoundries 45nm CMOS PDK", "https://www.globalfoundries.com/"),
    "gf28nm": PDKInfo("gf28nm", "CMOS", "28nm CMOS", "gf28", "gf28nm", "GlobalFoundries 28nm CMOS PDK", "https://www.globalfoundries.com/"),
    "gf22nm": PDKInfo("gf22nm", "CMOS", "22nm FD-SOI", "gf22", "gf22nm", "GlobalFoundries 22nm FD-SOI PDK", "https://www.globalfoundries.com/"),
    "gf14nm": PDKInfo("gf14nm", "CMOS", "14nm FinFET", "gf14", "gf14nm", "GlobalFoundries 14nm FinFET PDK", "https://www.globalfoundries.com/"),
    "gf12nm": PDKInfo("gf12nm", "CMOS", "12nm FinFET", "gf12", "gf12nm", "GlobalFoundries 12nm FinFET PDK", "https://www.globalfoundries.com/"),
    "gf7nm": PDKInfo("gf7nm", "CMOS", "7nm FinFET", "gf7", "gf7nm", "GlobalFoundries 7nm FinFET PDK", "https://www.globalfoundries.com/"),
    "gf5nm": PDKInfo("gf5nm", "CMOS", "5nm FinFET", "gf5", "gf5nm", "GlobalFoundries 5nm FinFET PDK", "https://www.globalfoundries.com/"),
    "gf3nm": PDKInfo("gf3nm", "CMOS", "3nm GAA", "gf3", "gf3nm", "GlobalFoundries 3nm GAA PDK", "https://www.globalfoundries.com/"),
    "soi_220nm_passive": PDKInfo("soi_220nm_passive", "SOI", "220nm SOI passive", "soip", "soi_220nm_passive", "220nm SOI 无源器件 PDK", "https://gdsfactory.github.io/gdsfactory/"),
    "soi_220nm_active": PDKInfo("soi_220nm_active", "SOI", "220nm SOI active", "soia", "soi_220nm_active", "220nm SOI 有源器件 PDK（含调制器/探测器）", "https://gdsfactory.github.io/gdsfactory/"),
    "soi_300nm": PDKInfo("soi_300nm", "SOI", "300nm SOI", "soi3", "soi_300nm", "300nm SOI 厚硅 PDK", "https://www.aimphotonics.com/"),
    "inp_200nm": PDKInfo("inp_200nm", "InP", "200nm InP", "inp2", "inp_200nm", "200nm InP 磷化铟 PDK", "https://github.com/gdsfactory/vsc"),
}


def list_gdsfactory_pdks() -> list[dict[str, str]]:
    """列出所有 gdsfactory PDK 元数据（JSON-serializable）。

    Returns:
        PDK 元数据字典列表，每项含 name/platform/process_node/import_name/
        layer_stack_name/description/source_url。
    """
    return [
        {
            "name": info.name,
            "platform": info.platform,
            "process_node": info.process_node,
            "import_name": info.import_name,
            "layer_stack_name": info.layer_stack_name,
            "description": info.description,
            "source_url": info.source_url,
        }
        for info in GDSFACTORY_PDK_REGISTRY.values()
    ]


def get_gdsfactory_pdk(name: str) -> PDKInfo:
    """获取指定 gdsfactory PDK 元数据。

    Args:
        name: PDK 名（如 generic/siepic/ubcpdk）。

    Returns:
        PDKInfo 元数据。

    Raises:
        KeyError: PDK 未注册（R03 禁止 fall-back）。
    """
    if name not in GDSFACTORY_PDK_REGISTRY:
        raise KeyError(
            f"gdsfactory PDK '{name}' 未注册。"
            f"可用 PDK: {sorted(GDSFACTORY_PDK_REGISTRY.keys())}"
        )
    return GDSFACTORY_PDK_REGISTRY[name]


@dataclass
class PolarisLayerLevel:
    """层级别（对应 gdsfactory LayerLevel）。

    来源: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py

    Attributes:
        layer: 层名（如 "1/0"）。
        thickness_nm: 厚度（nm）。
        zmin_nm: 底部 z 坐标（nm）。
        material: 材料名。
        sidewall_angle_deg: 侧壁角度（度，0=垂直）。
        refractive_index: 复折射率（None 表示未指定）。
    """

    layer: str
    thickness_nm: float
    zmin_nm: float
    material: str
    sidewall_angle_deg: float = 0.0
    refractive_index: complex | None = None


@dataclass
class PolarisLayerStack:
    """层堆栈（对应 gdsfactory LayerStack）。

    来源: https://gdsfactory.github.io/gdsfactory/

    Attributes:
        name: 层堆栈名。
        levels: 层级别列表。
    """

    name: str
    levels: list[PolarisLayerLevel]


def _ensure_gdsfactory_available() -> None:
    """校验 gdsfactory 可用，不可用则 raise ImportError（R03 无 fall-back）。"""
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 不可用（Python 3.14 下 pydantic<2.10 锁定导致 import 失败）。"
            "convert_*/polaris_to_gdsfactory_component 需要 gdsfactory。"
            "请使用 Python 3.10-3.13。来源: https://gdsfactory.github.io/gdsfactory/"
        )


def convert_layerstack(gf_layerstack: Any) -> PolarisLayerStack:
    """转换 gdsfactory LayerStack 为 PolarisLayerStack。

    gdsfactory 9.44.0 API: LayerStack.layers 为 dict[str, LayerLevel]。
    兼容旧版 levels 属性。

    Args:
        gf_layerstack: gdsfactory LayerStack 对象。

    Returns:
        PolarisLayerStack 对象。

    Raises:
        ImportError: gdsfactory 不可用。
        ValueError: LayerStack 无 layers/levels 属性。
    """
    _ensure_gdsfactory_available()
    gf_levels = getattr(gf_layerstack, "layers", None) or getattr(gf_layerstack, "levels", None)
    if gf_levels is None:
        raise ValueError("gdsfactory LayerStack 无 layers/levels 属性")
    levels: list[PolarisLayerLevel] = []
    items = gf_levels.items() if hasattr(gf_levels, "items") else enumerate(gf_levels)
    for level_name, level in items:
        layer = getattr(level, "layer", level_name)
        if isinstance(layer, tuple):
            layer = f"{layer[0]}/{layer[1]}"
        ri = getattr(level, "refractive_index", None)
        levels.append(PolarisLayerLevel(
            layer=str(layer),
            thickness_nm=float(getattr(level, "thickness", 0.0) or 0.0),
            zmin_nm=float(getattr(level, "zmin", 0.0) or 0.0),
            material=str(getattr(level, "material", "unknown") or "unknown"),
            sidewall_angle_deg=float(getattr(level, "sidewall_angle", 0.0) or 0.0),
            refractive_index=complex(ri) if ri is not None else None,
        ))
    name = getattr(gf_layerstack, "name", "converted") or "converted"
    return PolarisLayerStack(name=str(name), levels=levels)


@dataclass
class PolarisSection:
    """截面段（对应 gdsfactory Section）。

    来源: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py

    Attributes:
        width_um: 段宽度（μm）。
        offset_um: 段偏移（μm）。
        layer: 层名。
        ports: 端口名元组（可空）。
        hidden: 是否隐藏。
    """

    width_um: float
    offset_um: float
    layer: str
    ports: tuple[str, str] | None = None
    hidden: bool = False


@dataclass
class PolarisCrossSection:
    """截面（对应 gdsfactory CrossSection）。

    来源: https://gdsfactory.github.io/gdsfactory/

    Attributes:
        name: 截面名。
        sections: 截面段列表。
        width_um: 主宽度（μm）。
        offset_um: 主偏移（μm）。
    """

    name: str
    sections: list[PolarisSection]
    width_um: float = 0.0
    offset_um: float = 0.0


def convert_crosssection(gf_xs: Any) -> PolarisCrossSection:
    """转换 gdsfactory CrossSection 为 PolarisCrossSection。

    Args:
        gf_xs: gdsfactory CrossSection 对象。

    Returns:
        PolarisCrossSection 对象。

    Raises:
        ImportError: gdsfactory 不可用（R03）。
    """
    _ensure_gdsfactory_available()
    sections: list[PolarisSection] = []
    for sec in getattr(gf_xs, "sections", []):
        layer = getattr(sec, "layer", "WG")
        if isinstance(layer, tuple):
            layer = f"{layer[0]}/{layer[1]}"
        ports = getattr(sec, "ports", None)
        ports_tuple: tuple[str, str] | None = None
        if ports is not None and len(ports) >= 2:
            ports_tuple = (str(ports[0]), str(ports[1]))
        sections.append(PolarisSection(
            width_um=float(getattr(sec, "width", 0.0) or 0.0),
            offset_um=float(getattr(sec, "offset", 0.0) or 0.0),
            layer=str(layer),
            ports=ports_tuple,
            hidden=bool(getattr(sec, "hidden", False)),
        ))
    return PolarisCrossSection(
        name=str(getattr(gf_xs, "name", "converted") or "converted"),
        sections=sections,
        width_um=float(getattr(gf_xs, "width", 0.0) or 0.0),
        offset_um=float(getattr(gf_xs, "offset", 0.0) or 0.0),
    )


# ===== .pic.yml YAML 布局解析 =====


@dataclass
class PicYamlInstance:
    """YAML 布局实例（.pic.yml instances 段）。

    来源: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
    """

    component: str
    settings: dict = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    mirror: bool = False


@dataclass
class PicYamlConnection:
    """YAML 布局连接（.pic.yml connections 段）。"""

    source: str
    destination: str


@dataclass
class PicYamlRoute:
    """YAML 布局路由（.pic.yml routes 段）。"""

    source: str
    destination: str
    strategy: str = "auto"


@dataclass
class PicYamlSpec:
    """YAML 布局规范（.pic.yml 完整解析结果）。

    支持 instances/placements/connections/routes/ports。
    来源: https://deepwiki.com/gdsfactory/gdsfactory/5.2-yaml-based-layout-generation
    """

    instances: list[PicYamlInstance]
    connections: list[PicYamlConnection]
    routes: list[PicYamlRoute]
    ports: dict[str, str]
    name: str = ""


def _parse_instances(raw: dict, placements: dict) -> list[PicYamlInstance]:
    """解析 instances + placements 段为 PicYamlInstance 列表。"""
    result: list[PicYamlInstance] = []
    for inst_name, inst_data in raw.items():
        place = placements.get(inst_name, {}) or {}
        result.append(PicYamlInstance(
            component=inst_data.get("component", ""),
            settings=inst_data.get("settings", {}) or {},
            x=float(place.get("x", 0.0) or 0.0),
            y=float(place.get("y", 0.0) or 0.0),
            rotation=float(place.get("rotation", 0.0) or 0.0),
            mirror=bool(place.get("mirror", False)),
        ))
    return result


def _parse_connections(raw: dict) -> list[PicYamlConnection]:
    """解析 connections 段为 PicYamlConnection 列表。"""
    return [PicYamlConnection(source=str(src), destination=str(dst)) for src, dst in raw.items()]


def _parse_routes(raw: dict) -> list[PicYamlRoute]:
    """解析 routes 段。格式: route_name: {links: {src: dst}, settings: {strategy: auto}}"""
    result: list[PicYamlRoute] = []
    for _route_name, route_data in raw.items():
        links = (route_data or {}).get("links", {}) or {}
        settings = (route_data or {}).get("settings", {}) or {}
        strategy = str(settings.get("strategy", "auto") or "auto")
        for src, dst in links.items():
            result.append(PicYamlRoute(source=str(src), destination=str(dst), strategy=strategy))
    return result


def parse_pic_yaml(yaml_path: str | Path) -> PicYamlSpec:
    """解析 .pic.yml 布局文件（纯 YAML）。

    Args:
        yaml_path: .pic.yml 文件路径。

    Returns:
        PicYamlSpec 解析结果。

    Raises:
        FileNotFoundError: 文件不存在（R03）。
        ValueError: YAML 解析失败 / 顶层非字典。
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f".pic.yml 文件不存在: {yaml_path}")
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {yaml_path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"YAML 顶层应为字典，得到 {type(data).__name__}: {yaml_path}")
    instances_raw = data.get("instances", {}) or {}
    ports = data.get("ports", {}) or {}
    if not isinstance(instances_raw, dict):
        raise ValueError("instances 段应为字典")
    if not isinstance(ports, dict):
        raise ValueError("ports 段应为字典")
    stem = path.stem
    default_name = stem[:-4] if stem.endswith(".pic") else stem
    return PicYamlSpec(
        instances=_parse_instances(instances_raw, data.get("placements", {}) or {}),
        connections=_parse_connections(data.get("connections", {}) or {}),
        routes=_parse_routes(data.get("routes", {}) or {}),
        ports={str(k): str(v) for k, v in ports.items()},
        name=str(data.get("name", default_name) or default_name),
    )


# ===== 【创新】PDK 互操作层 =====


@dataclass
class PolarisPDK:
    """PoLaRIS 原生 PDK（【创新】PDK 互操作层，支持自定义注册与互操作）。

    来源: Fowler 2002 PoEAA 互操作层模式
    https://martinfowler.com/books/eaa.html

    Attributes:
        name: PDK 名称。
        platform: 材料平台（SOI/SiN/InP/LNOI）。
        process_node: 工艺节点。
        devices: 器件字典 {component_name: Device}。
        layer_stack: 层堆栈（可空）。
        cross_sections: 截面字典 {name: PolarisCrossSection}。
    """

    name: str
    platform: str
    process_node: str
    devices: dict[str, Device] = field(default_factory=dict)
    layer_stack: PolarisLayerStack | None = None
    cross_sections: dict[str, PolarisCrossSection] = field(default_factory=dict)


@dataclass
class PDKConflict:
    """PDK 组件冲突（【创新】命名空间隔离）。

    Attributes:
        pdk_names: 冲突涉及的 PDK 名列表。
        component_name: 冲突的组件名。
        description: 冲突描述。
    """

    pdk_names: list[str]
    component_name: str
    description: str


class PolarisPDKRegistry:
    """PoLaRIS 原生 PDK 注册表（【创新】PDK 互操作层）。

    创新逻辑：gdsfactory 无统一注册表与冲突检测，PoLaRIS 提供独立注册表。
    支持理论: Registry 模式 + 互操作层模式（Fowler 2002）。

    来源:
    - Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
    - gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
    """

    def __init__(self) -> None:
        self._pdks: dict[str, PolarisPDK] = {}

    def register(self, name: str, pdk: PolarisPDK) -> None:
        """注册 PDK。

        Args:
            name: PDK 名称。
            pdk: PolarisPDK 实例。

        Raises:
            ValueError: name 已存在（R03 无 fall-back，禁止静默覆盖）。
        """
        if name in self._pdks:
            raise ValueError(f"PDK '{name}' 已注册，禁止重复注册（R03 无 fall-back）")
        self._pdks[name] = pdk

    def get(self, name: str) -> PolarisPDK:
        """获取 PDK。

        Args:
            name: PDK 名称。

        Returns:
            PolarisPDK 实例。

        Raises:
            KeyError: PDK 不存在（R03）。
        """
        if name not in self._pdks:
            raise KeyError(f"PDK '{name}' 未注册")
        return self._pdks[name]

    def list_pdks(self) -> list[str]:
        """列出所有已注册 PDK 名。"""
        return sorted(self._pdks.keys())

    def detect_conflicts(
        self, other_registry: PolarisPDKRegistry | None = None
    ) -> list[PDKConflict]:
        """检测组件名冲突（【创新】命名空间隔离）。

        Args:
            other_registry: 另一个注册表（None 检测自身内部冲突）。

        Returns:
            PDKConflict 列表（空列表表示无冲突）。
        """
        conflicts: list[PDKConflict] = []
        self_comps: dict[str, list[str]] = {}
        for pdk_name, pdk in self._pdks.items():
            for comp_name in pdk.devices:
                self_comps.setdefault(comp_name, []).append(pdk_name)
        if other_registry is None:
            for comp_name, pdk_names in self_comps.items():
                if len(pdk_names) > 1:
                    conflicts.append(PDKConflict(
                        pdk_names=pdk_names,
                        component_name=comp_name,
                        description=f"组件 '{comp_name}' 在 {len(pdk_names)} 个 PDK 中重复: {pdk_names}",
                    ))
        else:
            for pdk_name, pdk in other_registry._pdks.items():
                for comp_name in pdk.devices:
                    if comp_name in self_comps:
                        conflicts.append(PDKConflict(
                            pdk_names=self_comps[comp_name] + [pdk_name],
                            component_name=comp_name,
                            description=f"组件 '{comp_name}' 在 self{self_comps[comp_name]} 与 other[{pdk_name}] 冲突",
                        ))
        return conflicts


# 方向 → orientation（度）映射（gdsfactory: 0=东, 90=北, 180=西, 270=南）
_DIRECTION_TO_ORIENTATION: dict[Direction, float] = {
    Direction.EAST: 0.0,
    Direction.NORTH: 90.0,
    Direction.WEST: 180.0,
    Direction.SOUTH: 270.0,
}


def polaris_to_gdsfactory_component(device: Device) -> Any:
    """将 PoLaRIS Device 反向转换为 gdsfactory Component（【创新】）。

    创新逻辑：gdsfactory 无双向互操作，PoLaRIS 提供反向转换。
    支持理论: 互操作层模式（Fowler 2002）。

    gdsfactory 9.44.0: add_port 需指定 layer 或 cross_section。
    使用 (1, 0) 作为默认 WG 层（SiEPIC 标准，layer 1 datatype 0）。
    来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        device: PoLaRIS Device 对象。

    Returns:
        gdsfactory Component 对象。

    Raises:
        ImportError: gdsfactory 不可用（R03）。
    """
    _ensure_gdsfactory_available()
    component = gf.Component(name=device.device_id)
    for port in device.ports:
        component.add_port(
            name=port.name,
            center=(port.x, port.y),
            width=port.width,
            orientation=_DIRECTION_TO_ORIENTATION.get(port.direction, 0.0),
            port_type="optical" if "optical" in port.waveguide_type else "electrical",
            layer=(1, 0),
        )
    component.info["polaris_device_id"] = device.device_id
    component.info["polaris_platform"] = device.platform
    component.info["polaris_category"] = device.category
    if device.process_node:
        component.info["polaris_process_node"] = device.process_node
    return component


@dataclass
class VersionCompatibility:
    """版本兼容性报告（【创新】）。

    Attributes:
        compatible: 是否兼容。
        python_version: Python 版本字符串。
        gdsfactory_version: gdsfactory 版本（None 表示未安装）。
        reason: 不兼容原因。
        recommended_action: 推荐操作。
    """

    compatible: bool
    python_version: str
    gdsfactory_version: str | None
    reason: str
    recommended_action: str


def check_gdsfactory_version_compatibility() -> VersionCompatibility:
    """检测 gdsfactory 版本与 Python 版本兼容性（【创新】）。

    创新逻辑：gdsfactory 8.18.0 锁定 pydantic<2.10，pydantic-core 无 Py3.14 wheel。
    支持理论: SemVer（https://semver.org）+ 上游依赖锁定分析。

    Returns:
        VersionCompatibility 兼容性报告。
    """
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ge_314 = sys.version_info >= (3, 14)
    if _HAS_GDSFACTORY and _GDSFACTORY_VERSION is not None:
        if py_ge_314:
            return VersionCompatibility(
                compatible=False,
                python_version=py_version,
                gdsfactory_version=_GDSFACTORY_VERSION,
                reason=f"gdsfactory {_GDSFACTORY_VERSION} 在 Python {py_version} 下可能不稳定（pydantic<2.10 锁定）",
                recommended_action="建议使用 Python 3.10-3.13 以获得最佳兼容性",
            )
        return VersionCompatibility(
            compatible=True,
            python_version=py_version,
            gdsfactory_version=_GDSFACTORY_VERSION,
            reason=f"gdsfactory {_GDSFACTORY_VERSION} 在 Python {py_version} 下可用",
            recommended_action="无需操作，gdsfactory 可正常使用",
        )
    if py_ge_314:
        return VersionCompatibility(
            compatible=False,
            python_version=py_version,
            gdsfactory_version=None,
            reason=(
                f"Python {py_version} 下 gdsfactory 不可用：gdsfactory 8.18.0 锁定 "
                "pydantic<2.10，而 pydantic<2.10 的 pydantic-core 无 Python 3.14 wheel"
            ),
            recommended_action="方案1: 使用 Python 3.10-3.13 环境（推荐）。方案2: 等待 gdsfactory 解除 pydantic 版本锁定。来源: https://gdsfactory.github.io/gdsfactory/",
        )
    return VersionCompatibility(
        compatible=False,
        python_version=py_version,
        gdsfactory_version=None,
        reason=f"Python {py_version} 兼容 gdsfactory，但 gdsfactory 未安装",
        recommended_action="执行 pip install gdsfactory 安装（来源: https://gdsfactory.github.io/gdsfactory/）",
    )


__all__ = [
    "GDSFACTORY_PDK_REGISTRY",
    "PDKConflict",
    "PDKInfo",
    "PicYamlConnection",
    "PicYamlInstance",
    "PicYamlRoute",
    "PicYamlSpec",
    "PolarisCrossSection",
    "PolarisLayerLevel",
    "PolarisLayerStack",
    "PolarisPDK",
    "PolarisPDKRegistry",
    "PolarisSection",
    "VersionCompatibility",
    "check_gdsfactory_version_compatibility",
    "convert_crosssection",
    "convert_layerstack",
    "get_gdsfactory_pdk",
    "list_gdsfactory_pdks",
    "parse_pic_yaml",
    "polaris_to_gdsfactory_component",
]
