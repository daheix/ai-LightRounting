"""PDK Lite 器件模型资料库子包。

存放各工艺平台（SOI/SiN/InP/LNOI）的器件数据结构与器件库，
所有器件参数须附带 source 字段以溯源至公开文献。

顶层重导出四平台器件工厂汇总表（``SOI_DEVICES``/``SIN_DEVICES``/
``INP_DEVICES``/``LNOI_DEVICES``），便于上层代码统一访问：
``from polaris.pdk import SOI_DEVICES, LNOI_DEVICES``。

R09 路标：重导出 gdsfactory PDK 桥接模块（``gdsfactory_pdk_bridge``）的
公开符号，包括 PDK 注册表、LayerStack/CrossSection 转换、YAML 解析、
PolarisPDKRegistry、反向转换、版本兼容检测。

R11 路标：重导出版图参数化代码驱动模块（``pcell``）的公开符号，包括
``@polaris_cell`` 装饰器、``PCellMultiView`` 多视图 PCell、``TransformMatrix``
仿射变换引擎、``ai_generate_pcell`` AI 辅助生成。
"""

from polaris.pdk.catalog import DeviceCatalog, default_catalog
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.gpic import (
    GPIC_ALIAS_MAP,
    GPICBB,
    GPICPDK,
    build_gpic_pdk,
)
from polaris.pdk.gdsfactory_pdk_bridge import (
    GDSFACTORY_PDK_REGISTRY,
    PDKConflict,
    PDKInfo,
    PicYamlConnection,
    PicYamlInstance,
    PicYamlRoute,
    PicYamlSpec,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    VersionCompatibility,
    check_gdsfactory_version_compatibility,
    convert_crosssection,
    convert_layerstack,
    parse_pic_yaml,
    polaris_to_gdsfactory_component,
)
from polaris.pdk.inp import INP_DEVICES
from polaris.pdk.layer_map import (
    POLARIS_CATEGORY_LAYER_MAP,
    POLARIS_GDS_LAYER_MAP,
    GDSLayer,
    get_category_layer_tuple,
    get_layer_tuple,
)
from polaris.pdk.lnoi import LNOI_DEVICES
from polaris.pdk.optodesigner import (
    DesignIntent,
    DesignIntentEngine,
    FlexConnector,
    HierarchyDesign,
    PDAflowInterop,
    PyCell,
    PyCellFactory,
    TechnologyRule,
)
from polaris.pdk.pcell import (
    PCellCache,
    PCellMultiView,
    TransformMatrix,
    ai_generate_pcell,
    clear_pcell_cache,
    polaris_cell,
)
from polaris.pdk.vpi_pdk import (
    PDAflowExporter,
    VPIBuildingBlock,
    VPIPDKRegistry,
    VPIToolkitPDK,
    build_hhi_pdk,
    build_ligentec_pdk,
    build_lionix_pdk,
)
from polaris.pdk.port import Direction, Port
from polaris.pdk.sin import SIN_DEVICES
from polaris.pdk.soi import SOI_DEVICES
from polaris.pdk.source import Source

__all__ = [
    "BoundingBox",
    "Device",
    "DeviceCatalog",
    "Direction",
    "GDSFACTORY_PDK_REGISTRY",
    "GDSLayer",
    "GPIC_ALIAS_MAP",
    "GPICBB",
    "GPICPDK",
    "GPIC_DRC_RUNSET",
    "INP_DEVICES",
    "LNOI_DEVICES",
    "PCellCache",
    "PCellMultiView",
    "PDKConflict",
    "PDKInfo",
    "POLARIS_CATEGORY_LAYER_MAP",
    "POLARIS_GDS_LAYER_MAP",
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
    "Port",
    "SIN_DEVICES",
    "SOI_DEVICES",
    "Source",
    "TransformMatrix",
    "VersionCompatibility",
    "ai_generate_pcell",
    "check_gdsfactory_version_compatibility",
    "clear_pcell_cache",
    "convert_crosssection",
    "convert_layerstack",
    "default_catalog",
    "get_category_layer_tuple",
    "get_layer_tuple",
    "parse_pic_yaml",
    "polaris_cell",
    "polaris_to_gdsfactory_component",
    # R15 VPIphotonics PDK 对齐（VPIToolkitPDK + PDAflow + 3 foundry PDK）
    "PDAflowExporter",
    "VPIBuildingBlock",
    "VPIPDKRegistry",
    "VPIToolkitPDK",
    "build_hhi_pdk",
    "build_ligentec_pdk",
    "build_lionix_pdk",
    # R19 L-Edit GPIC iPDK 对齐（GPICPDK + 15 BB + SPICE + PDAflow）
    "build_gpic_pdk",
    # R20 Synopsys OptoDesigner 版图驱动设计对齐
    "DesignIntent",
    "DesignIntentEngine",
    "FlexConnector",
    "HierarchyDesign",
    "PDAflowInterop",
    "PyCell",
    "PyCellFactory",
    "TechnologyRule",
]


def __getattr__(name: str):
    """PEP 562 延迟访问 GPIC_DRC_RUNSET（避免循环导入）。

    GPIC_DRC_RUNSET 依赖 polaris.sim.klayout_drc.DRCRule，而 klayout_drc
    依赖 polaris.pdk.layer_map，形成循环。通过 __getattr__ 延迟到首次访问
    时才从 polaris.pdk.gpic 导入，此时所有模块均已完成初始化。
    """
    if name == "GPIC_DRC_RUNSET":
        from polaris.pdk.gpic import GPIC_DRC_RUNSET
        return GPIC_DRC_RUNSET
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
