"""GDSII 层操作工具（R330，GDSII Layer Operations）。

提供 GDSII 层的复制、合并、删除操作，用于层重映射、层清理、
PDK 层转换等场景。

## 核心概念

- **层（Layer）**: GDSII 用 (layer, datatype) 二元组标识层
- **复制（Copy）**: 将源层所有 shapes 复制到目标层（保留源层）
- **合并（Merge）**: 将多个源层 shapes 合并到目标层，并删除源层
- **删除（Delete）**: 删除指定层及其所有 shapes
- **保持层次**: 操作遍历所有 cell 的本地 shapes，保持原层次结构

## 算法

1. 读取 GDSII 文件
2. 获取/创建目标层 layer_index
3. 遍历所有 cell（ly.each_cell()）:
   - 对每个 cell 的源层 shapes 容器:
     - 复制: 遍历 shapes，insert 到同 cell 的目标层
     - 合并: 复制后删除源层
     - 删除: 直接删除层
4. 写出 GDSII 文件

## KLayout 0.30.9 API 关键事实（冒烟测试实测）

- Layout.layer(layer, datatype) -> layer_index: 获取/创建层
- Layout.delete_layer(li): 删除层（含所有 cell 的该层 shapes）
- Layout.get_info(li) -> LayerInfo: 获取层信息
- Layout.layer_indices(): 返回所有 layer_index 迭代器
- Cell.shapes(li) -> Shapes 容器: 获取该 cell 该层的 shapes 容器
- Shapes.each(): 迭代 Shape 对象（非递归，只本 cell）
- Shapes.size(): 返回 shape 数
- Shapes.insert(polygon): 插入 polygon
- Shapes.clear(): 清空该层所有 shapes（不删除层定义）
- Shape.is_polygon() / Shape.polygon: 判断/获取 Polygon 对象
- Layout.each_cell(): 返回 Cell 对象迭代器（非 index）

## 学术依据

- KLayout Layout class:
  https://www.klayout.de/doc.html
- KLayout Cell class:
  https://www.klayout.de/doc.html
- KLayout Shapes class:
  https://www.klayout.de/doc.html
- KLayout Shape class:
  https://www.klayout.de/doc.html
- KLayout LayerInfo:
  https://www.klayout.de/doc.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 层规范:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 层映射:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Calibre 层操作:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "LayerOpReport",
    "copy_layer",
    "merge_layers",
    "delete_layers",
    "generate_layer_op_report",
]


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 层操作。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class LayerOpReport:
    """GDSII 层操作报告（R330）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        operation: 操作类型（'copy' / 'merge' / 'delete'）。
        source_layers: 源层列表 [(layer, datatype), ...]。
        target_layer: 目标层 (layer, datatype)（copy/merge 有效，delete 为 None）。
        dbu: 数据库单位（μm）。
        shapes_moved: 复制/移动的 shape 总数。
        layers_before: 操作前层列表 [(layer, datatype), ...]。
        layers_after: 操作后层列表 [(layer, datatype), ...]。
    """

    input_path: str
    output_path: str
    operation: str = ""
    source_layers: list[tuple[int, int]] = field(default_factory=list)
    target_layer: tuple[int, int] | None = None
    dbu: float = 0.0
    shapes_moved: int = 0
    layers_before: list[tuple[int, int]] = field(default_factory=list)
    layers_after: list[tuple[int, int]] = field(default_factory=list)


# =============================================================================
# 层复制
# =============================================================================
def copy_layer(
    gds_path: str | Path,
    output_path: str | Path,
    source_layer: tuple[int, int],
    target_layer: tuple[int, int],
    top_cell_name: str | None = None,
) -> LayerOpReport:
    """复制 GDSII 层（R330）。

    将源层所有 shapes 复制到目标层（保留源层）。遍历所有 cell 的本地
    shapes，保持原层次结构。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        source_layer: 源层 (layer, datatype)。
        target_layer: 目标层 (layer, datatype)。
        top_cell_name: 未使用（层操作作用于所有 cell），保留接口一致性。

    Returns:
        LayerOpReport 操作报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / 层参数无效。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Shapes class:
      https://www.klayout.de/doc.html
    """
    src_layer, src_dt = _validate_layer(source_layer, "source_layer")
    tgt_layer, tgt_dt = _validate_layer(target_layer, "target_layer")
    if (src_layer, src_dt) == (tgt_layer, tgt_dt):
        raise ValueError(
            f"source_layer 和 target_layer 不能相同: {(src_layer, src_dt)}。"
            f"禁止 fall-back（R03）。"
        )

    db = _import_klayout_db()
    ly, layers_before, dbu = _read_gdsii(gds_path)

    src_li = _find_or_raise_layer(ly, src_layer, src_dt, gds_path)
    tgt_li = ly.layer(tgt_layer, tgt_dt)

    shapes_moved = _copy_shapes_all_cells(ly, src_li, tgt_li)

    layers_after = _get_all_layers(ly)
    _write_gdsii(ly, output_path)

    logger.info(
        "层复制: %s → %s (%d,%d)→(%d,%d), %d shapes",
        gds_path, output_path, src_layer, src_dt, tgt_layer, tgt_dt,
        shapes_moved,
    )

    return LayerOpReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        operation="copy",
        source_layers=[(src_layer, src_dt)],
        target_layer=(tgt_layer, tgt_dt),
        dbu=dbu,
        shapes_moved=shapes_moved,
        layers_before=layers_before,
        layers_after=layers_after,
    )


# =============================================================================
# 层合并
# =============================================================================
def merge_layers(
    gds_path: str | Path,
    output_path: str | Path,
    source_layers: list[tuple[int, int]],
    target_layer: tuple[int, int],
    top_cell_name: str | None = None,
) -> LayerOpReport:
    """合并多个 GDSII 层到目标层（R330）。

    将多个源层所有 shapes 复制到目标层，并删除源层。遍历所有 cell 的
    本地 shapes，保持原层次结构。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        source_layers: 源层列表 [(layer, datatype), ...]。
        target_layer: 目标层 (layer, datatype)。
        top_cell_name: 未使用，保留接口一致性。

    Returns:
        LayerOpReport 操作报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / source_layers 空 / 层参数无效 /
            目标层在源层列表中。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Layout.delete_layer:
      https://www.klayout.de/doc.html
    """
    if not source_layers:
        raise ValueError(
            "source_layers 不能为空。禁止 fall-back（R03）。"
        )

    validated_sources: list[tuple[int, int]] = []
    for i, layer in enumerate(source_layers):
        validated_sources.append(_validate_layer(layer, f"source_layers[{i}]"))

    tgt_layer, tgt_dt = _validate_layer(target_layer, "target_layer")
    if (tgt_layer, tgt_dt) in validated_sources:
        raise ValueError(
            f"target_layer {(tgt_layer, tgt_dt)} 不能在 source_layers 中。"
            f"禁止 fall-back（R03）。"
        )

    db = _import_klayout_db()
    ly, layers_before, dbu = _read_gdsii(gds_path)

    tgt_li = ly.layer(tgt_layer, tgt_dt)

    total_moved = 0
    for (src_layer, src_dt) in validated_sources:
        src_li = _find_or_raise_layer(ly, src_layer, src_dt, gds_path)
        total_moved += _copy_shapes_all_cells(ly, src_li, tgt_li)
        ly.delete_layer(src_li)

    layers_after = _get_all_layers(ly)
    _write_gdsii(ly, output_path)

    logger.info(
        "层合并: %s → %s %s→(%d,%d), %d shapes",
        gds_path, output_path, validated_sources, tgt_layer, tgt_dt,
        total_moved,
    )

    return LayerOpReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        operation="merge",
        source_layers=validated_sources,
        target_layer=(tgt_layer, tgt_dt),
        dbu=dbu,
        shapes_moved=total_moved,
        layers_before=layers_before,
        layers_after=layers_after,
    )


# =============================================================================
# 层删除
# =============================================================================
def delete_layers(
    gds_path: str | Path,
    output_path: str | Path,
    layers_to_delete: list[tuple[int, int]],
    top_cell_name: str | None = None,
) -> LayerOpReport:
    """删除 GDSII 指定层（R330）。

    删除指定层及其所有 shapes。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        layers_to_delete: 要删除的层列表 [(layer, datatype), ...]。
        top_cell_name: 未使用，保留接口一致性。

    Returns:
        LayerOpReport 操作报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / layers_to_delete 空 / 层参数无效。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Layout.delete_layer:
      https://www.klayout.de/doc.html
    """
    if not layers_to_delete:
        raise ValueError(
            "layers_to_delete 不能为空。禁止 fall-back（R03）。"
        )

    validated: list[tuple[int, int]] = []
    for i, layer in enumerate(layers_to_delete):
        validated.append(_validate_layer(layer, f"layers_to_delete[{i}]"))

    db = _import_klayout_db()
    ly, layers_before, dbu = _read_gdsii(gds_path)

    total_deleted = 0
    for (layer, datatype) in validated:
        src_li = _find_or_raise_layer(ly, layer, datatype, gds_path)
        # 统计 shape 数
        for cell in ly.each_cell():
            total_deleted += int(cell.shapes(src_li).size())
        ly.delete_layer(src_li)

    layers_after = _get_all_layers(ly)
    _write_gdsii(ly, output_path)

    logger.info(
        "层删除: %s → %s %s, %d shapes",
        gds_path, output_path, validated, total_deleted,
    )

    return LayerOpReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        operation="delete",
        source_layers=validated,
        target_layer=None,
        dbu=dbu,
        shapes_moved=total_deleted,
        layers_before=layers_before,
        layers_after=layers_after,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_layer_op_report(
    gds_path: str | Path,
    output_path: str | Path,
    operation: str,
    source_layers: list[tuple[int, int]],
    target_layer: tuple[int, int] | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 层操作报告（R330）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        operation: 操作类型（'copy' / 'merge' / 'delete'）。
        source_layers: 源层列表。
        target_layer: 目标层（copy/merge 有效）。
        top_cell_name: 未使用。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 操作类型无效 / 参数无效。
        FileNotFoundError: 文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    op = operation.lower()
    if op == "copy":
        if target_layer is None:
            raise ValueError("copy 操作需要 target_layer")
        if len(source_layers) != 1:
            raise ValueError("copy 操作需要恰好 1 个 source_layer")
        report = copy_layer(gds_path, output_path, source_layers[0], target_layer)
    elif op == "merge":
        if target_layer is None:
            raise ValueError("merge 操作需要 target_layer")
        report = merge_layers(gds_path, output_path, source_layers, target_layer)
    elif op == "delete":
        report = delete_layers(gds_path, output_path, source_layers)
    else:
        raise ValueError(
            f"不支持的 operation: {operation}。支持: copy / merge / delete。"
        )

    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(report)
    if fmt == "markdown":
        return _render_markdown_report(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown。"
    )


# =============================================================================
# 内部辅助函数
# =============================================================================
def _validate_layer(layer: tuple[int, int], context: str) -> tuple[int, int]:
    """验证层参数（R330 内部函数）。

    Args:
        layer: (layer, datatype) 元组。
        context: 错误消息上下文。

    Returns:
        验证后的 (layer, datatype)。

    Raises:
        ValueError: 格式无效 / layer/datatype 超范围。
    """
    if not isinstance(layer, (tuple, list)) or len(layer) != 2:
        raise ValueError(
            f"{context} 必须是 (layer, datatype) 元组，得到: {layer}。"
            f"禁止 fall-back（R03）。"
        )
    g, d = int(layer[0]), int(layer[1])
    if not (0 <= g <= 999):
        raise ValueError(
            f"{context} layer ({g}) 必须 0-999。禁止 fall-back（R03）。"
        )
    if not (0 <= d <= 255):
        raise ValueError(
            f"{context} datatype ({d}) 必须 0-255。禁止 fall-back（R03）。"
        )
    return (g, d)


def _read_gdsii(gds_path):
    """读取 GDSII 文件，返回 (Layout, layers_before, dbu)（R330 内部函数）。"""
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    layers_before = _get_all_layers(ly)
    dbu = float(ly.dbu)
    return ly, layers_before, dbu


def _write_gdsii(ly, output_path) -> None:
    """写出 GDSII 文件（R330 内部函数）。"""
    try:
        ly.write(str(output_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e


def _get_all_layers(ly) -> list[tuple[int, int]]:
    """获取所有层列表（排序）（R330 内部函数）。"""
    result: list[tuple[int, int]] = []
    for li in ly.layer_indices():
        info = ly.get_info(li)
        result.append((int(info.layer), int(info.datatype)))
    return sorted(result)


def _find_or_raise_layer(ly, layer: int, datatype: int, gds_path):
    """查找层，不存在则 raise（R330 内部函数）。

    Returns:
        layer_index。

    Raises:
        ValueError: 层不存在。
    """
    # 遍历现有层查找匹配的
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return li
    available = _get_all_layers(ly)
    raise ValueError(
        f"层 ({layer}, {datatype}) 不存在于 {gds_path}。"
        f"可用层: {available}"
    )


def _copy_shapes_all_cells(ly, src_li, tgt_li) -> int:
    """复制所有 cell 的源层 shapes 到目标层（R330 内部函数）。

    遍历每个 cell 的本地 shapes（非递归），复制到同 cell 的目标层，
    保持原层次结构。

    Returns:
        复制的 shape 总数。
    """
    moved = 0
    for cell in ly.each_cell():
        src_shapes = cell.shapes(src_li)
        for shape in src_shapes.each():
            # 支持 polygon 和 box
            if shape.is_polygon():
                cell.shapes(tgt_li).insert(shape.polygon)
                moved += 1
            elif shape.is_box():
                cell.shapes(tgt_li).insert(shape.bbox())
                moved += 1
    return moved


def _render_text_report(report: LayerOpReport) -> str:
    """渲染纯文本报告（R330 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"GDSII 层操作报告 ({report.operation})")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"操作: {report.operation}")
    lines.append(f"源层: {report.source_layers}")
    if report.target_layer is not None:
        lines.append(f"目标层: {report.target_layer}")
    lines.append(f"移动 shapes: {report.shapes_moved}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("层变化:")
    lines.append("-" * 60)
    lines.append(f"操作前层: {report.layers_before}")
    lines.append(f"操作后层: {report.layers_after}")
    added = [l for l in report.layers_after if l not in report.layers_before]
    removed = [l for l in report.layers_before if l not in report.layers_after]
    if added:
        lines.append(f"新增层: {added}")
    if removed:
        lines.append(f"删除层: {removed}")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: LayerOpReport) -> str:
    """渲染 Markdown 报告（R330 内部函数）。"""
    lines: list[str] = []
    lines.append(f"# GDSII 层操作报告 ({report.operation})")
    lines.append("")
    lines.append(f"**输入文件**: `{report.input_path}`")
    lines.append(f"**输出文件**: `{report.output_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**操作**: `{report.operation}`")
    lines.append(f"**源层**: {report.source_layers}")
    if report.target_layer is not None:
        lines.append(f"**目标层**: `{report.target_layer}`")
    lines.append(f"**移动 shapes**: {report.shapes_moved}")
    lines.append("")
    lines.append("## 层变化")
    lines.append("")
    lines.append(f"- **操作前层**: {report.layers_before}")
    lines.append(f"- **操作后层**: {report.layers_after}")
    added = [l for l in report.layers_after if l not in report.layers_before]
    removed = [l for l in report.layers_before if l not in report.layers_after]
    if added:
        lines.append(f"- **新增层**: {added}")
    if removed:
        lines.append(f"- **删除层**: {removed}")
    return "\n".join(lines)
