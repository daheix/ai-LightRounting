"""PoLaRIS 多格式 I/O 包（polaris-gds-tools 子包）。

提供 OpenAccess 数据库与 ODB++/DXF/CIF/Gerber/LEF/DEF 六种格式的
统一读写能力。统一数据模型见 :mod:`polaris_gds_tools.formats.multi_format`。

v5.1 从 v4 旧包 ``polaris.io`` 迁移而来，包路径改为
``polaris_gds_tools.formats``，R13 不保留 v4 兼容。
"""

from polaris_gds_tools.formats.multi_format import (
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    MultiFormatIO,
    Point,
    Shape,
    SUPPORTED_FORMATS,
    layouts_equal,
)
from polaris_gds_tools.formats.openaccess import (
    OPENACCESS_LAYER_MAP,
    OpenAccessDB,
)

__all__ = [
    "Cell",
    "FormatLayout",
    "Instance",
    "LayerInfo",
    "MultiFormatIO",
    "OpenAccessDB",
    "OPENACCESS_LAYER_MAP",
    "Point",
    "SUPPORTED_FORMATS",
    "Shape",
    "layouts_equal",
]
