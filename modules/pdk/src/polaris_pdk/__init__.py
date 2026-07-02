"""PoLaRIS PDK 器件库管理 + GDSII 导入导出（polaris-pdk 子模块）。

提供稳定的 Python API（返回 dict/list，不返回内部对象），其他子模块
（place/route/sim/verify/export/pipe）依赖本模块获取 PDK 器件规格与
GDSII 文件读写能力。

设计原则:
- 对外 API 返回 JSON-serializable dict/list，不返回 dataclass 或 klayout 对象
- 禁止 fall-back（R03）：器件未找到 / GDSII 读写失败 raise RuntimeError
- 所有器件参数标注来源（SiEPIC EBeam PDK / Ligentec / Pattern Project / HyperLight）
- 纯 NumPy/klayout(CPU) 实现（R04: 不参与 GPU）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec ANR PDK: https://www.ligentec.com/
- Pattern Project / JEPPIX InP: https://www.jeppix.eu/
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
"""

from __future__ import annotations

from polaris_pdk.catalog import get_device, list_devices, list_platforms
from polaris_pdk.gdsii import export_gds, import_gds

__version__ = "5.0.0"

__all__ = [
    "list_platforms",
    "get_device",
    "list_devices",
    "export_gds",
    "import_gds",
    "__version__",
]
