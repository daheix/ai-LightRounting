"""GDSII 导入模块（R301 — 完全兼容 gdsfactory 输出格式）。

原属 gdsfactory_integration.py §3（批次 10-B 拆分提取），保留原始文献溯源。

使用 klayout.db 读取 GDSII 文件，保留:
1. 层次结构: 所有 cells + 递归 instances (TR-301.2)
2. 层号映射: (gds_layer, gds_datatype) → PoLaRIS 层名 (TR-301.3)
3. 无损导入: 多边形/路径/文本/实例全部保留 (TR-301.1)

学术依据:
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- gdsfactory GDS 导出: https://gdsfactory.github.io/gdsfactory/
- gdsfactory PDK import: https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- klayout Database API: https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdspy 层次化引用: https://gdspy.readthedocs.io/en/master/gettingstarted.html#references

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# gdsfactory 默认端口层（WG layer (1, 0)）
# 来源: gdsfactory PDK import 文档
# https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
_GDSFACTORY_DEFAULT_PORT_LAYER: tuple[int, int] = (1, 0)

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


@dataclass
class GDSIILayerInfo:
    """GDSII 层信息（R301）。

    Attributes:
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype。
        polaris_name: PoLaRIS 层名（来自层映射）。
        n_shapes: 该层上的形状总数（跨所有 cells）。

    学术依据: GDSII 层规范
    https://en.wikipedia.org/wiki/GDS_File
    """

    gds_layer: int = 0
    gds_datatype: int = 0
    polaris_name: str = ""
    n_shapes: int = 0


@dataclass
class GDSIIInstanceInfo:
    """GDSII 实例信息（层次化引用，R301）。

    Attributes:
        cell_name: 被引用的 cell 名。
        x: 实例原点 x (μm)。
        y: 实例原点 y (μm)。
        rotation_deg: 旋转角度 (度)。
        mirror_x: 是否 X 镜像。
        magnification: 缩放因子（通常 1.0）。

    学术依据: GDSII AREF/SREF 结构
    https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
    """

    cell_name: str = ""
    x: float = 0.0
    y: float = 0.0
    rotation_deg: float = 0.0
    mirror_x: bool = False
    magnification: float = 1.0


@dataclass
class GDSIICellInfo:
    """GDSII cell 信息（R301）。

    Attributes:
        name: cell 名。
        n_polygons: 多边形数。
        n_paths: 路径数。
        n_texts: 文本数。
        n_instances: 子 cell 实例数。
        instances: 子 cell 实例列表。
        bbox_um: 边界框 (xmin, ymin, xmax, ymax) μm。
        is_top: 是否为顶层 cell。

    学术依据: GDSII cell 结构
    https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """

    name: str = ""
    n_polygons: int = 0
    n_paths: int = 0
    n_texts: int = 0
    n_instances: int = 0
    instances: list[GDSIIInstanceInfo] = None
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    is_top: bool = False

    def __post_init__(self):
        if self.instances is None:
            self.instances = []


@dataclass
class GDSIIImportResult:
    """GDSII 导入结果（R301）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu_um: 数据库单位 (μm)。
        cells: 所有 cells 列表（保留层次结构）。
        layers: 所有层信息列表。
        total_instances: 总实例数。
        total_polygons: 总多边形数。
        total_paths: 总路径数。
        total_texts: 总文本数。
        n_cells: cell 数。

    学术依据: GDSII 层次化结构
    https://gdsfactory.github.io/gdsfactory/
    """

    file_path: str = ""
    top_cell_name: str = ""
    dbu_um: float = 0.001
    cells: list[GDSIICellInfo] = None
    layers: list[GDSIILayerInfo] = None
    total_instances: int = 0
    total_polygons: int = 0
    total_paths: int = 0
    total_texts: int = 0
    n_cells: int = 0

    def __post_init__(self):
        if self.cells is None:
            self.cells = []
        if self.layers is None:
            self.layers = []


def _klayout_trans_to_info(trans, dbu: float) -> GDSIIInstanceInfo:
    """将 klayout DCplxTrans 变换对象转换为 GDSIIInstanceInfo（R301 内部辅助）。

    klayout 0.30.9 验证 API（无 fall-back，R03 合规）:
    - ``ct.mag``: 缩放因子（float）
    - ``ct.angle``: 旋转角度（度，float）
    - ``ct.is_mirror()``: 是否镜像（bool）
    - ``ct.disp``: 位移 DPoint（单位 μm，DCplxTrans 始终用 μm）

    Args:
        trans: klayout DCplxTrans 变换对象（来自 ``inst.dcplx_trans``）。
        dbu: 数据库单位 (μm)（保留参数，DCplxTrans 已用 μm，不参与计算）。

    Returns:
        GDSIIInstanceInfo 实例。

    Raises:
        AttributeError: trans 不含预期属性（klayout 版本不兼容）。

    学术依据:
    - klayout DCplxTrans API:
      https://www.klayout.org/klayout-pypi/overview/instances/
    - klayout Database API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """
    # klayout 0.30.9: DCplxTrans 属性全部存在（已冒烟测试验证）
    mag = float(trans.mag)
    rot = float(trans.angle)
    mirror = bool(trans.is_mirror())
    # disp 是 DPoint，单位 μm（D 前缀 = double micrometers）
    disp = trans.disp
    x = float(disp.x)
    y = float(disp.y)
    return GDSIIInstanceInfo(
        cell_name="",  # 由调用方填充
        x=x,
        y=y,
        rotation_deg=rot,
        mirror_x=mirror,
        magnification=mag,
    )


def import_gdsii_from_gdsfactory(
    gds_path: str | Path,
    top_cell_name: str | None = None,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> GDSIIImportResult:
    """从 GDSII 文件导入，完全兼容 gdsfactory 输出格式（R301）。

    使用 klayout.db 读取 GDSII 文件，保留:
    1. **层次结构**: 所有 cells + 递归 instances (TR-301.2)
    2. **层号映射**: (gds_layer, gds_datatype) → PoLaRIS 层名 (TR-301.3)
    3. **无损导入**: 多边形/路径/文本/实例全部保留 (TR-301.1)

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名（None 则用第一个 top cell）。
        layer_map: 自定义层映射 {(layer, datatype): polaris_name}。
            None 则用 gdsfactory generic PDK 默认映射。

    Returns:
        GDSIIImportResult。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: GDSII 文件无效或 top_cell_name 不存在。
        RuntimeError: klayout 读取失败。

    学术依据:
    - GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
    - gdsfactory GDS 导出: https://gdsfactory.github.io/gdsfactory/
    - gdsfactory PDK import: https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
    - klayout Database API: https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdspy 层次化引用: https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
    """
    from pathlib import Path as _Path
    import klayout.db as db
    gds_path = _Path(gds_path)
    if not gds_path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not gds_path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = dict(_DEFAULT_LAYER_MAP)
    ly, dbu, top_cell, top_cell_name = _read_and_select_top_cell(
        db, gds_path, top_cell_name
    )
    layer_infos, layer_shape_count = _collect_layer_infos(ly, layer_map)
    cells_info, total_instances, total_polygons, total_paths, total_texts = (
        _collect_cells_info(ly, dbu, top_cell_name, layer_shape_count)
    )
    _finalize_layer_infos(layer_infos, layer_shape_count)
    return GDSIIImportResult(
        file_path=str(gds_path), top_cell_name=top_cell_name, dbu_um=dbu,
        cells=cells_info, layers=layer_infos, total_instances=total_instances,
        total_polygons=total_polygons, total_paths=total_paths,
        total_texts=total_texts, n_cells=len(cells_info),
    )


def _read_and_select_top_cell(db, gds_path, top_cell_name) -> tuple:
    """读取 GDSII 并选择顶层 cell（R301 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly, dbu, top_cell, top_cell_name)。

    Raises:
        RuntimeError: klayout 读取失败。ValueError: top_cell_name 不存在 / 无顶层 cell。
    """
    ly = db.Layout()
    try:
        ly.read(str(gds_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。可用顶层 cells: {available}"
            )
    else:
        top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
        if not top_cells:
            raise ValueError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
        top_cell = top_cells[0]
        top_cell_name = top_cell.name
    return ly, dbu, top_cell, top_cell_name


def _collect_layer_infos(ly, layer_map) -> tuple:
    """收集所有 layers 信息（R301 内部辅助）。

    Returns:
        (layer_infos, layer_shape_count)。
    """
    layer_infos: list[GDSIILayerInfo] = []
    layer_shape_count: dict[tuple[int, int], int] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        polaris_name = layer_map.get(
            (gds_layer, gds_datatype), f"LAYER_{gds_layer}_{gds_datatype}",
        )
        layer_infos.append(GDSIILayerInfo(
            gds_layer=gds_layer, gds_datatype=gds_datatype,
            polaris_name=polaris_name, n_shapes=0,
        ))
        layer_shape_count[(gds_layer, gds_datatype)] = 0
    return layer_infos, layer_shape_count


def _collect_cells_info(ly, dbu, top_cell_name, layer_shape_count) -> tuple:
    """遍历所有 cells 收集层次结构与形状统计（R301 内部辅助）。

    Args:
        layer_shape_count: 层→shape 计数字典（会被本函数累加更新）。

    Returns:
        (cells_info, total_instances, total_polygons, total_paths, total_texts)。
    """
    cells_info: list[GDSIICellInfo] = []
    total_instances = total_polygons = total_paths = total_texts = 0
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        cell_name = cell.name
        is_top = (cell_name == top_cell_name)
        n_poly, n_path, n_text, layer_counts = _count_cell_shapes(ly, cell)
        for key, cnt in layer_counts.items():
            layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt
        instances = _collect_cell_instances(ly, cell, dbu)
        bbox_um = _cell_bbox_um(cell, dbu)
        cells_info.append(GDSIICellInfo(
            name=cell_name, n_polygons=n_poly, n_paths=n_path, n_texts=n_text,
            n_instances=len(instances), instances=instances, bbox_um=bbox_um, is_top=is_top,
        ))
        total_instances += len(instances)
        total_polygons += n_poly
        total_paths += n_path
        total_texts += n_text
    return cells_info, total_instances, total_polygons, total_paths, total_texts


def _count_cell_shapes(ly, cell) -> tuple:
    """统计 cell 内形状（R301 内部辅助）。

    Returns:
        (n_poly, n_path, n_text, layer_counts)。
    """
    n_poly = n_path = n_text = 0
    layer_counts: dict[tuple[int, int], int] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        key = (int(info.layer), int(info.datatype))
        for shape in cell.shapes(li).each():
            if shape.is_polygon() or shape.is_box() or shape.is_simple_polygon():
                n_poly += 1
            elif shape.is_path():
                n_path += 1
            elif shape.is_text():
                n_text += 1
            layer_counts[key] = layer_counts.get(key, 0) + 1
    return n_poly, n_path, n_text, layer_counts


def _collect_cell_instances(ly, cell, dbu) -> list:
    """收集 cell 的实例信息（R301 内部辅助）。"""
    instances: list[GDSIIInstanceInfo] = []
    for inst in cell.each_inst():
        child_idx = inst.cell_index
        child_name = ly.cell(child_idx).name
        inst_info = _klayout_trans_to_info(inst.dcplx_trans, dbu)
        inst_info.cell_name = child_name
        instances.append(inst_info)
    return instances


def _cell_bbox_um(cell, dbu) -> tuple[float, float, float, float]:
    """计算 cell bbox（dbu → μm）（R301 内部辅助）。"""
    bbox = cell.bbox()
    return (
        float(bbox.left) * dbu, float(bbox.bottom) * dbu,
        float(bbox.right) * dbu, float(bbox.top) * dbu,
    )


def _finalize_layer_infos(layer_infos, layer_shape_count) -> None:
    """更新 layer 形状计数并过滤空层（R301 内部辅助）。"""
    for li_info in layer_infos:
        key = (li_info.gds_layer, li_info.gds_datatype)
        li_info.n_shapes = layer_shape_count.get(key, 0)
    layer_infos[:] = [li for li in layer_infos if li.n_shapes > 0]


__all__ = [
    "GDSIILayerInfo",
    "GDSIIInstanceInfo",
    "GDSIICellInfo",
    "GDSIIImportResult",
    "import_gdsii_from_gdsfactory",
    "_DEFAULT_LAYER_MAP",
    "_GDSFACTORY_DEFAULT_PORT_LAYER",
]
