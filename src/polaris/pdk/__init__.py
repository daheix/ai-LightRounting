"""PDK Lite 器件模型资料库子包。

存放各工艺平台（SOI/SiN/InP/LNOI）的器件数据结构与器件库，
所有器件参数须附带 source 字段以溯源至公开文献。

顶层重导出四平台器件工厂汇总表（``SOI_DEVICES``/``SIN_DEVICES``/
``INP_DEVICES``/``LNOI_DEVICES``），便于上层代码统一访问：
``from polaris.pdk import SOI_DEVICES, LNOI_DEVICES``。
"""

from polaris.pdk.catalog import DeviceCatalog, default_catalog
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.inp import INP_DEVICES
from polaris.pdk.layer_map import (
    POLARIS_CATEGORY_LAYER_MAP,
    POLARIS_GDS_LAYER_MAP,
    GDSLayer,
    get_category_layer_tuple,
    get_layer_tuple,
)
from polaris.pdk.lnoi import LNOI_DEVICES
from polaris.pdk.port import Direction, Port
from polaris.pdk.sin import SIN_DEVICES
from polaris.pdk.soi import SOI_DEVICES
from polaris.pdk.source import Source

__all__ = [
    "BoundingBox",
    "Device",
    "DeviceCatalog",
    "Direction",
    "GDSLayer",
    "INP_DEVICES",
    "LNOI_DEVICES",
    "POLARIS_CATEGORY_LAYER_MAP",
    "POLARIS_GDS_LAYER_MAP",
    "Port",
    "SIN_DEVICES",
    "SOI_DEVICES",
    "Source",
    "default_catalog",
    "get_category_layer_tuple",
    "get_layer_tuple",
]
