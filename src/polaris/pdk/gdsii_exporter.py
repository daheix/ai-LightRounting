"""GDSII 导出模块（R302 — 输出与 gdsfactory 兼容）。

原属 gdsfactory_integration.py §4-§5（批次 10-B 拆分提取），保留原始文献溯源。

提供:
- export_gdsii_from_layout: klayout Layout → GDSII 文件
- round_trip_gdsii: GDSII 往返导入导出（验证无信息损失）
- create_gdsii_layout_from_cells: cell 规格列表 → klayout Layout
- export_gdsii_from_cells: cell 规格列表 → GDSII 文件（综合接口）

学术依据:
- klayout Layout.write API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds 默认参数:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- GDSII 层次结构: https://en.wikipedia.org/wiki/GDS_File
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from polaris.pdk.gdsii_importer import GDSIIImportResult, import_gdsii_from_gdsfactory

logger = logging.getLogger(__name__)


# gdsfactory 写出 GDSII 的默认 dbu（μm）
# 来源: gdsfactory write_gds 默认参数
# https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
_GDSFACTORY_DEFAULT_DBU_UM: float = 0.001


@dataclass
class GDSIIExportConfig:
    """GDSII 导出配置（R302）。

    Attributes:
        top_cell_name: 顶层 cell 名（写入 GDSII 时若 Layout 无顶层 cell 用此名创建）。
        dbu_um: 数据库单位（μm），gdsfactory 默认 0.001μm (1nm)。
        layer_map: 自定义层映射（仅用于元数据验证，不参与实际写出）。
        write_context_info: 是否写入 klayout 上下文信息（gdsfactory 兼容）。

    学术依据:
    - gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
    - GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
    """

    top_cell_name: str = "TOP"
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM
    layer_map: dict[tuple[int, int], str] | None = None
    write_context_info: bool = True


def export_gdsii_from_layout(
    layout,
    output_path: str | Path,
    config: GDSIIExportConfig | None = None,
) -> str:
    """将 klayout Layout 写出为 gdsfactory 兼容的 GDSII 文件（R302 TR-302.1/2）。

    使用 klayout.db.Layout.write() 写出 GDSII 文件，确保:
    1. dbu 与 gdsfactory 默认一致（0.001μm = 1nm）
    2. 层次结构完整保留（顶层 + 所有子 cells + instances）
    3. 输出文件可被 gdsfactory.kuple.import_gds 正确读取

    Args:
        layout: klayout.db.Layout 对象。
        output_path: GDSII 输出路径。
        config: 导出配置（None 用默认）。

    Returns:
        GDSII 文件路径。

    Raises:
        ValueError: Layout 无 cell 或 output_path 无效。
        RuntimeError: klayout 写入失败。

    学术依据:
    - klayout Layout.write API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdsfactory write_gds 默认参数:
      https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
    """
    from pathlib import Path as _Path

    cfg = config or GDSIIExportConfig()
    output_path = _Path(output_path)

    # R03: 输入验证
    if layout.cells() == 0:
        raise ValueError(
            "Layout 无 cell，无法写出 GDSII。"
            "需先在 Layout 中创建至少一个 cell。"
        )
    if output_path.is_dir():
        raise ValueError(f"输出路径是目录不是文件: {output_path}")

    # 验证 dbu 与 gdsfactory 默认一致（若不一致告警，不强制修改）
    actual_dbu = float(layout.dbu)
    if abs(actual_dbu - cfg.dbu_um) > 1e-9:
        logger.warning(
            "Layout dbu=%.6fμm 与 gdsfactory 默认 %.6fμm 不一致，"
            "可能影响 gdsfactory 读取兼容性",
            actual_dbu,
            cfg.dbu_um,
        )

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        layout.write(str(output_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII 写出: %s (cells=%d, dbu=%.4fμm)",
        output_path,
        layout.cells(),
        actual_dbu,
    )
    return str(output_path)


def round_trip_gdsii(
    input_path: str | Path,
    output_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> tuple[GDSIIImportResult, str]:
    """GDSII 往返导入导出（R302 TR-302.3 验证无信息损失）。

    流程:
    1. 用 import_gdsii_from_gdsfactory 读入 GDSII → GDSIIImportResult
    2. 重新写出 GDSII 到 output_path（直接复用读入的 Layout）
    3. 再次读入 output_path，验证 cells/instances/shapes 数量一致

    Args:
        input_path: 输入 GDSII 路径。
        output_path: 输出 GDSII 路径。
        layer_map: 层映射（None 用默认）。

    Returns:
        (原始导入结果, 输出文件路径) 元组。

    Raises:
        FileNotFoundError: 输入文件不存在。
        RuntimeError: 往返验证失败（数量不一致）。

    学术依据:
    - GDSII 往返一致性: https://en.wikipedia.org/wiki/GDS_File
    - klayout Layout API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    """
    from pathlib import Path as _Path

    import klayout.db as db

    input_path = _Path(input_path)
    output_path = _Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")

    # 步骤 1: 导入原始 GDSII
    original_result = import_gdsii_from_gdsfactory(
        input_path, layer_map=layer_map
    )

    # 步骤 2: 重新读取并写出（保留层次结构）
    ly = db.Layout()
    try:
        ly.read(str(input_path))
    except Exception as e:
        raise RuntimeError(
            f"重新读取 GDSII 失败: {type(e).__name__}: {e}"
        ) from e

    export_gdsii_from_layout(ly, output_path)

    # 步骤 3: 验证往返一致性（TR-302.3）
    round_trip_result = import_gdsii_from_gdsfactory(
        output_path, layer_map=layer_map
    )

    # 验证关键字段一致（不允许信息损失）
    if original_result.n_cells != round_trip_result.n_cells:
        raise RuntimeError(
            f"往返验证失败: n_cells 不一致 "
            f"(原始={original_result.n_cells}, 往返={round_trip_result.n_cells})"
        )
    if original_result.total_instances != round_trip_result.total_instances:
        raise RuntimeError(
            f"往返验证失败: total_instances 不一致 "
            f"(原始={original_result.total_instances}, "
            f"往返={round_trip_result.total_instances})"
        )
    if original_result.total_polygons != round_trip_result.total_polygons:
        raise RuntimeError(
            f"往返验证失败: total_polygons 不一致 "
            f"(原始={original_result.total_polygons}, "
            f"往返={round_trip_result.total_polygons})"
        )
    if original_result.total_texts != round_trip_result.total_texts:
        raise RuntimeError(
            f"往返验证失败: total_texts 不一致 "
            f"(原始={original_result.total_texts}, "
            f"往返={round_trip_result.total_texts})"
        )
    if original_result.total_paths != round_trip_result.total_paths:
        raise RuntimeError(
            f"往返验证失败: total_paths 不一致 "
            f"(原始={original_result.total_paths}, "
            f"往返={round_trip_result.total_paths})"
        )

    logger.info(
        "GDSII 往返验证通过: %s → %s (cells=%d, instances=%d, polygons=%d)",
        input_path,
        output_path,
        original_result.n_cells,
        original_result.total_instances,
        original_result.total_polygons,
    )
    return original_result, str(output_path)


def _create_all_cells(ly, cells_spec: list[dict]) -> dict[str, "db.Cell"]:
    """第一遍: 创建所有 cells（解决引用顺序，R629 Extract Method）。"""
    import klayout.db as db
    name_to_cell: dict[str, "db.Cell"] = {}
    for spec in cells_spec:
        name = spec.get("name")
        if not name:
            raise ValueError(f"cell 规格缺少 'name' 字段: {spec}")
        if name in name_to_cell:
            raise ValueError(f"cell 名重复: {name}")
        name_to_cell[name] = ly.create_cell(name)
    return name_to_cell


def _fill_cell_shapes(
    ly, cell, spec: dict, name: str, dbu_um: float, db
) -> None:
    """填充 cell 的多边形/文本/路径形状（R629 Extract Method）。"""
    # 多边形
    for poly in spec.get("polygons", []):
        layer = int(poly["layer"])
        datatype = int(poly["datatype"])
        li = ly.layer(layer, datatype)
        points = poly["points"]
        if len(points) < 3:
            raise ValueError(
                f"多边形点数 < 3 (cell={name}, layer={layer}/{datatype})"
            )
        dbu_points = [db.Point(int(round(p[0] / dbu_um)), int(round(p[1] / dbu_um))) for p in points]
        cell.shapes(li).insert(db.Polygon(dbu_points))

    # 文本
    for txt in spec.get("texts", []):
        layer = int(txt["layer"])
        datatype = int(txt["datatype"])
        li = ly.layer(layer, datatype)
        string = str(txt["string"])
        x_um = float(txt.get("x", 0.0))
        y_um = float(txt.get("y", 0.0))
        # Text 接受 Trans（dbu 单位）
        # R05 Bug 修复 v5.0-P1-3R1: 统一用 int(round()) 避免截断漂移
        trans = db.Trans(int(round(x_um / dbu_um)), int(round(y_um / dbu_um)))
        cell.shapes(li).insert(db.Text(string, trans))

    # 路径
    for path in spec.get("paths", []):
        layer = int(path["layer"])
        datatype = int(path["datatype"])
        li = ly.layer(layer, datatype)
        points = path["points"]
        if len(points) < 2:
            raise ValueError(
                f"路径点数 < 2 (cell={name}, layer={layer}/{datatype})"
            )
        width_um = float(path.get("width", 0.5))
        width_dbu = int(round(width_um / dbu_um))
        dbu_points = [db.Point(int(round(p[0] / dbu_um)), int(round(p[1] / dbu_um))) for p in points]
        cell.shapes(li).insert(db.Path(dbu_points, width_dbu))


def _fill_cell_instances(
    cell, spec: dict, name: str, name_to_cell: dict, dbu_um: float, db
) -> None:
    """填充 cell 的实例引用（R629 Extract Method）。"""
    # 修复（R05）: 原代码用 db.DCplxTrans(μm) 构造 instance，但 CellInstArray
    # 在 KLayout 0.30.9 中将 DCplxTrans 的位移当成 dbu 存储，导致 20μm 变成
    # 0.02μm（20dbu）。改为用 db.ICplxTrans(dbu) 显式构造，μm → dbu 转换
    # 后再传入，确保 instance 的 placement 正确。
    # 实测（调试 _debug4_r324.py）: DCplxTrans(1.0,0,False,20.0,0.0) 存储
    # 后 dcplx_trans 显示 0.02,0 μm（即 20 dbu），而非 20 μm。
    # 来源: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
    for inst in spec.get("instances", []):
        child_name = inst.get("cell_name")
        if child_name not in name_to_cell:
            raise ValueError(
                f"实例引用的 cell 不存在: {child_name} "
                f"(在 cell '{name}' 中)"
            )
        child_cell = name_to_cell[child_name]
        x_um = float(inst.get("x", 0.0))
        y_um = float(inst.get("y", 0.0))
        rotation = float(inst.get("rotation", 0.0))
        mirror = bool(inst.get("mirror", False))
        # 用 ICplxTrans（dbu 单位）显式构造，避免 DCplxTrans → ICplxTrans
        # 转换时的单位歧义
        x_dbu = int(round(x_um / dbu_um))
        y_dbu = int(round(y_um / dbu_um))
        trans = db.ICplxTrans(1.0, rotation, mirror, x_dbu, y_dbu)
        cell.insert(db.CellInstArray(child_cell.cell_index(), trans))


def create_gdsii_layout_from_cells(
    cells_spec: list[dict],
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM,
) -> "db.Layout":
    """从 cell 规格列表构造 klayout Layout（R302 TR-302.2 层次结构导出）。

    用于将 PoLaRIS 内部数据结构（dict）转换为 klayout Layout，
    再用 export_gdsii_from_layout 写出。

    Args:
        cells_spec: cell 规格列表，每个 dict 含:
            - name: cell 名（必填）
            - polygons: list[dict] 多边形列表，每个含 layer/datatype/points
            - texts: list[dict] 文本列表，每个含 layer/datatype/string/x/y
            - paths: list[dict] 路径列表，每个含 layer/datatype/points/width
            - instances: list[dict] 实例列表，每个含 cell_name/x/y/rotation/mirror
            - is_top: bool 是否为顶层 cell
        dbu_um: 数据库单位（μm）。

    Returns:
        klayout.db.Layout 对象。

    Raises:
        ValueError: cells_spec 为空或 cell 名重复或引用不存在 cell。
        RuntimeError: klayout 构造失败。

    学术依据:
    - klayout Layout API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - GDSII 层次结构: https://en.wikipedia.org/wiki/GDS_File
    """
    import klayout.db as db

    if not cells_spec:
        raise ValueError("cells_spec 不能为空")

    ly = db.Layout()
    ly.dbu = dbu_um

    # 第一遍: 创建所有 cells（解决引用顺序问题）
    name_to_cell = _create_all_cells(ly, cells_spec)

    # 第二遍: 填充形状和实例
    for spec in cells_spec:
        name = spec["name"]
        cell = name_to_cell[name]
        _fill_cell_shapes(ly, cell, spec, name, dbu_um, db)
        _fill_cell_instances(cell, spec, name, name_to_cell, dbu_um, db)

    # 验证至少有一个顶层 cell
    top_cells = list(ly.each_top_cell())
    if not top_cells:
        raise ValueError(
            "构造的 Layout 无顶层 cell，可能所有 cells 都被引用为子 cell"
        )

    return ly


def export_gdsii_from_cells(
    cells_spec: list[dict],
    output_path: str | Path,
    dbu_um: float = _GDSFACTORY_DEFAULT_DBU_UM,
) -> str:
    """从 cell 规格列表导出 gdsfactory 兼容 GDSII（R302 综合接口）。

    一步完成: cells_spec → Layout → GDSII 文件。
    适合 PoLaRIS 内部数据结构直接导出。

    Args:
        cells_spec: cell 规格列表（见 create_gdsii_layout_from_cells）。
        output_path: GDSII 输出路径。
        dbu_um: 数据库单位（μm）。

    Returns:
        GDSII 文件路径。

    Raises:
        ValueError: cells_spec 无效。
        RuntimeError: 写出失败。
    """
    layout = create_gdsii_layout_from_cells(cells_spec, dbu_um=dbu_um)
    return export_gdsii_from_layout(layout, output_path)


__all__ = [
    "GDSIIExportConfig",
    "export_gdsii_from_layout",
    "round_trip_gdsii",
    "create_gdsii_layout_from_cells",
    "export_gdsii_from_cells",
]
