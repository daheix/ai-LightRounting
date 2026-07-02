"""PoLaRIS GDSII 工程化工具与多格式 IO 子模块（polaris-gds-tools）。

v5.1 从 v4 旧包 ``polaris.verification``（43 文件）+ ``polaris.io``（8 文件）
+ ``polaris.eval.layout_render`` 迁移而来。本子模块聚焦 GDSII 工程化工具链
与多格式版图互操作，与 ``polaris-gdsio``（基础 GDSII 读写）解耦：
- ``polaris-gdsio``：单一职责 GDSII import/export（circuit dict → GDS）
- ``polaris-gds-tools``：GDSII 工程化（统计/DRC/裁剪/合并/...）+ 多格式 IO
  （CIF/DXF/Gerber/ODB++/LEF-DEF/OpenAccess）+ 版图渲染

迁移范围（R13 不保留 v4 兼容，包路径 polaris.verification/io → polaris_gds_tools）：
- 22 个 GDSII 工程化工具（statistics/health_check/flattener/clip/layer_ops/
  merger/scaler/cell_hierarchy/cell_renamer/boolean_ops/geometry_transformer/
  sizing/diff/density/grid_alignment/edge/port/text_label/connectivity/
  tapeout_precheck/batch_pipeline/drc_area）
- 6 种格式 IO + 统一数据模型 FormatLayout（Cell/Shape/Instance/LayerInfo）
- 版图渲染 export_oasis / render_layout / RenderOptions（适配 FormatLayout，
  删除 v4 引擎 Placement/WaveguidePath 依赖）

=== Input / Process / Output 三段式文档 ===

Input:
- GDSII 工具：接受 GDSII 文件路径（str|Path），klayout.db 延迟导入读取
- 多格式 IO：MultiFormatIO.read(path, fmt) / write(layout, path, fmt)
    * fmt: cif/gerber/dxf/odb++/lef_def/openaccess
    * layout: FormatLayout（统一数据模型）
- 渲染：render_layout(layout, congestion, options) / export_oasis(layout, path)

Process:
- GDSII 工具：klayout.db 读取 GDSII → 几何分析/变换/布尔运算 → 报告或写出
- 多格式 IO：格式调度表懒加载子模块（_cif/_dxf/_gerber/_odbpp/_lef_def/
  openaccess），read→write→read 往返一致（浮点容差 1e-6）
- 渲染：FormatLayout.Shape → matplotlib 几何 / klayout 几何 → 原子写入
- 层映射：SiEPIC EBeam PDK 13 层标准（_common.get_default_layer_map）
- 原子写入：mkstemp + fsync + os.replace（POSIX rename 原子性）

Output:
- GDSII 工具：dataclass 报告（StatisticsReport/DiffReport/...）或写出文件
- 多格式 IO：FormatLayout（read）/ 文件（write）
- 渲染：LayoutRender(fig, ax) / OASIS 文件路径

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- KLayout Database API: https://www.klayout.org/doc-qt5/code/
- SiEPIC EBeam PDK 层映射: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic_pdk: https://gdsfactory.github.io/gdsfactory/
- ODB++ Format Specification: http://www.odb-sa.com/
- Si2 OpenAccess 22.60 API: https://si2.org/openaccess/
- UCAMCO Gerber Format Spec Rev 2024.06:
  https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
- Autodesk DXF Reference: https://images.autodesk.com/adskfiles/acad_dxf.pdf
- OpenROAD LEF/DEF Reference: https://github.com/The-OpenROAD-Project/OpenDB
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980
  (CIF 格式与版图分层理论)
- OASIS 格式规范 (SEMIM P39):
  https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
- POSIX rename(2) 原子性:
  https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯 NumPy/klayout CPU）
/ R05 Bug 必修 / R13 不保留 v4 兼容。函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

# --- 共享基础设施 ---
from polaris_gds_tools._common import (
    atomic_write_klayout,
    atomic_write_text,
    get_default_layer_map,
    get_klayout_db,
)

# --- 多格式 IO + 统一数据模型 ---
from polaris_gds_tools.formats import (
    OPENACCESS_LAYER_MAP,
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    MultiFormatIO,
    OpenAccessDB,
    Point,
    SUPPORTED_FORMATS,
    Shape,
    layouts_equal,
)

# --- 版图渲染 ---
from polaris_gds_tools.layout_render import (
    LayoutRender,
    RenderOptions,
    export_oasis,
    render_layout,
)

# --- GDSII 工程化工具（主入口函数）---
from polaris_gds_tools.gdsii_statistics import (
    StatisticsReport,
    generate_gdsii_statistics,
    generate_statistics_report,
)
from polaris_gds_tools.gdsii_health_check import check_gdsii_health
from polaris_gds_tools.gdsii_flattener import flatten_gdsii, generate_flatten_report
from polaris_gds_tools.gdsii_clip_tool import clip_gdsii, multi_clip_gdsii
from polaris_gds_tools.gdsii_layer_ops import copy_layer, delete_layers, merge_layers
from polaris_gds_tools.gdsii_layout_merger import merge_gdsii
from polaris_gds_tools.gdsii_layout_scaler import scale_gdsii
from polaris_gds_tools.gdsii_cell_hierarchy_analyzer import (
    analyze_cell_hierarchy,
    detect_circular_references,
)
from polaris_gds_tools.gdsii_cell_renamer import rename_cells
from polaris_gds_tools.gdsii_boolean_ops import boolean_operation
from polaris_gds_tools.gdsii_geometry_transformer import transform_gdsii_geometry
from polaris_gds_tools.gdsii_sizing_tool import size_layer
from polaris_gds_tools.gdsii_diff_tool import compare_gdsii_files, generate_diff_report
from polaris_gds_tools.gdsii_density_analyzer import (
    check_density_rules,
    compute_density_map,
    compute_layer_density,
)
from polaris_gds_tools.gdsii_grid_alignment_checker import check_grid_alignment
from polaris_gds_tools.gdsii_edge_extractor import extract_edges
from polaris_gds_tools.gdsii_port_extractor import extract_ports
from polaris_gds_tools.gdsii_text_label_extractor import extract_text_labels
from polaris_gds_tools.gdsii_connectivity_analyzer import (
    analyze_cross_layer_connectivity,
    analyze_layer_connectivity,
    list_isolated_polygons,
)
from polaris_gds_tools.gdsii_tapeout_precheck import tapeout_precheck
from polaris_gds_tools.gdsii_batch_pipeline import run_batch_pipeline
from polaris_gds_tools.gdsii_drc_area import check_area

__version__ = "5.1.0"

__all__ = [
    "__version__",
    # 共享基础设施
    "get_klayout_db",
    "get_default_layer_map",
    "atomic_write_klayout",
    "atomic_write_text",
    # 多格式 IO + 数据模型
    "Cell",
    "Shape",
    "Instance",
    "LayerInfo",
    "Point",
    "FormatLayout",
    "MultiFormatIO",
    "OpenAccessDB",
    "OPENACCESS_LAYER_MAP",
    "SUPPORTED_FORMATS",
    "layouts_equal",
    # 版图渲染
    "LayoutRender",
    "RenderOptions",
    "render_layout",
    "export_oasis",
    # GDSII 工程化工具
    "StatisticsReport",
    "generate_gdsii_statistics",
    "generate_statistics_report",
    "check_gdsii_health",
    "flatten_gdsii",
    "generate_flatten_report",
    "clip_gdsii",
    "multi_clip_gdsii",
    "copy_layer",
    "delete_layers",
    "merge_layers",
    "merge_gdsii",
    "scale_gdsii",
    "analyze_cell_hierarchy",
    "detect_circular_references",
    "rename_cells",
    "boolean_operation",
    "transform_gdsii_geometry",
    "size_layer",
    "compare_gdsii_files",
    "generate_diff_report",
    "check_density_rules",
    "compute_density_map",
    "compute_layer_density",
    "check_grid_alignment",
    "extract_edges",
    "extract_ports",
    "extract_text_labels",
    "analyze_cross_layer_connectivity",
    "analyze_layer_connectivity",
    "list_isolated_polygons",
    "tapeout_precheck",
    "run_batch_pipeline",
    "check_area",
]
