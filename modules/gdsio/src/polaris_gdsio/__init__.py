"""PoLaRIS GDSII 导入导出子模块（polaris-gdsio）。

v5.1 从 polaris-pdk 拆分而来，单一职责：GDSII 文件 I/O。
polaris-pdk 只保留器件库查询，本模块只做 GDSII 读写，二者解耦。

设计原则:
- 对外 API 返回 JSON-serializable dict，不返回 klayout 内部对象
- 禁止 fall-back（R03）：klayout 读写失败 / circuit 无效必须 raise
- 纯 klayout(CPU) 实现（R04: 不参与 GPU）

=== Input / Process / Output 三段式文档 ===

Input:
- export_gds(circuit, output_path)
    * circuit: dict（polaris-core 风格），含
        - name: str                 顶层 cell 名
        - devices: list[dict]       每个器件含 name/device_type/width_um/height_um
        - connections: list         （可空，导出时不强制使用）
        - canvas_w / canvas_h: float（可选，导出时不强制使用）
    * output_path: str              GDSII 输出文件路径
- import_gds(gds_path)
    * gds_path: str                 GDSII 文件路径

Process:
- klayout.db 创建 Layout（dbu=0.001μm=1nm，与 gdsfactory 默认一致）
- export: 顶层 cell + 每器件子 cell（box 在 WG 层 (1,0)）+ 实例放置 + 写 GDSII + 读回验证
- import: 读取 GDSII + 层号映射 (gds_layer, gds_datatype) → polaris_name + 顶层 bbox
- 层映射: (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
          / (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT

Output:
- export_gds -> {path, file_size_bytes, n_structures, n_layers, loadable: bool}
- import_gds -> {n_structures, n_layers,
                 layers: list[{gds_layer, gds_datatype, polaris_name, n_shapes}],
                 bbox_um: {xmin, ymin, xmax, ymax}}

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- klayout Layout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds 默认参数（dbu=0.001μm=1nm）:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from polaris_gdsio.exporter import export_gds
from polaris_gdsio.importer import import_gds

__version__ = "5.1.0"

__all__ = ["export_gds", "import_gds", "__version__"]
