"""PoLaRIS 多格式 I/O 包（polaris-gds-tools 子包）。

提供 OpenAccess 数据库与 ODB++/DXF/CIF/Gerber/LEF/DEF 六种格式的
统一读写能力。统一数据模型见 :mod:`polaris_gds_tools.formats.multi_format`。

v5.1 从 v4 旧包 ``polaris.io`` 迁移而来，包路径改为
``polaris_gds_tools.formats``，R13 不保留 v4 兼容。

## 来源（R02 学术诚信，≥5 个文献 URL）

- GDSII 格式标准: SEMI P39-0308E
  https://www.semi.org/en/standards/p39-0308e
- ODB++ 格式: Mentor/Siemens ODB++ Specification v8.1
  https://docs.sw.siemens.com/ru-RU/doc/783374671/1281097329/en/ODB_Format
- DXF 格式: Autodesk DXF Reference
  https://help.autodesk.com/view/OARX/2024/ENU/?guid=GUID-235B22E0-A567-4CF6-92D3-38A2306D73F3
- Gerber X2 格式: Ucamco Gerber Format Specification
  https://www.ucamco.com/en/gerber
- LEF/DEF 格式: Si2 LEF/DEF Open API
  https://si2.org/lefdef/
- OpenAccess: OpenAccess Database Schema
  https://openaccess.si2.org/
- CIF 格式: Caltech Intermediate Form Specification
  https://www.rulabinsky.com/cavd/text/chapb.html
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
