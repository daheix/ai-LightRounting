"""GDSII 扁平化工具（R326，GDSII Flattener）。

将层次化 GDSII（含子 cell 实例）扁平化为单顶层 cell（无子实例），
用于 DRC 前处理、流片导出、与不支持层次的工具兼容。

## 核心概念

- **层次化 GDSII**: 顶层 cell 通过实例（CellInstArray）引用子 cell
- **扁平化（Flatten）**: 将子 cell 的 shapes 传播到顶层 cell，移除实例引用
- **levels**: 扁平化的层次数（-1=全部，0=无，1=一层等）
- **prune**: True 删除扁平化后不再被引用的孤儿 cell

## 算法

1. 读取 GDSII 文件
2. 统计扁平化前指标（cell 数、实例数、shape 数）
3. 对指定 top cell 调用 Cell.flatten(levels, prune)
4. 若 prune=True 但孤儿 cell 仍存在，手动删除非 top 的孤儿 cell
5. 写出 GDSII 文件
6. 统计扁平化后指标

## KLayout 0.30.9 API 关键事实（冒烟测试实测）

- Cell.flatten(levels, prune): 扁平化 cell 的子实例
  - levels: 层次数（-1=全部，0=无，1=一层）
  - prune: True 删除孤儿 cell（实测确实删除，但 cells() 缓存不更新）
- Layout.cells(): 返回总 cell 数（方法）—— **不可靠，返回缓存值**
  扁平化/删除 cell 后不会立即更新，实测仍返回扁平化前的值。
  必须用 `len(list(ly.each_cell()))` 获取实际 cell 数。
  来源: 冒烟测试 R326，对比 ly.cells()=2 vs len(list(ly.each_cell()))=1
- len(list(ly.each_cell())): 实际 cell 数（可靠，每次重新迭代）
- Cell.child_instances(): 返回直接子实例数（方法，返回 int）
- Layout.each_top_cell(): 返回顶层 cell 索引迭代器
- Layout.delete_cell(cell_index): 删除指定 cell
- Cell.begin_shapes_rec(li): 递归 shapes 迭代器

## 学术依据

- KLayout Cell.flatten:
  https://klayout.org/downloads/master/doc-qt5/code/class_Cell.html
- KLayout Layout.flatten:
  https://klayout.org/downloads/master/doc-qt5/code/class_Layout.html
- KLayout Flatten Cells 手册:
  https://klayout.org/downloads/master/doc-qt5/manual/flatten.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
- KLayout Instance.flatten:
  https://klayout.org/downloads/master/doc-qt5/code/class_Instance.html
- KLayout Cell class:
  https://klayout.org/downloads/master/doc-qt5/code/class_Cell.html
- GDSII 层次结构:
  https://en.wikipedia.org/wiki/GDS_File
- Calibre DRC 前处理扁平化:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK 流片导出:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "FlattenReport",
    "flatten_gdsii",
    "generate_flatten_report",
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
            "klayout 未安装，无法执行 GDSII 扁平化。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class FlattenReport:
    """GDSII 扁平化报告（R326）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        dbu: 数据库单位（μm）。
        top_cell_name: 扁平化的顶层 cell 名。
        levels: 扁平化层次数（-1=全部）。
        prune: 是否删除孤儿 cell。
        cells_before: 扁平化前总 cell 数。
        cells_after: 扁平化后总 cell 数。
        instances_before: 扁平化前 top cell 直接子实例数。
        instances_after: 扁平化后 top cell 直接子实例数。
        shapes_before: 扁平化前 top cell 递归 shape 数。
        shapes_after: 扁平化后 top cell 递归 shape 数。
    """

    input_path: str
    output_path: str
    dbu: float = 0.0
    top_cell_name: str = ""
    levels: int = -1
    prune: bool = True
    cells_before: int = 0
    cells_after: int = 0
    instances_before: int = 0
    instances_after: int = 0
    shapes_before: int = 0
    shapes_after: int = 0


# =============================================================================
# 扁平化
# =============================================================================
def flatten_gdsii(
    gds_path: str | Path,
    output_path: str | Path,
    levels: int = -1,
    prune: bool = True,
    top_cell_name: str | None = None,
) -> FlattenReport:
    """扁平化 GDSII 文件的层次结构（R326）。

    将指定顶层 cell 的子 cell 实例扁平化到顶层 cell 中，移除实例引用。
    可选删除扁平化后不再被引用的孤儿 cell。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        levels: 扁平化层次数（-1=全部，0=无，1=一层等）。
        prune: True 删除孤儿 cell。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。

    Returns:
        FlattenReport 扁平化报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 输入无效 / levels < -1 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Cell.flatten:
      https://klayout.org/downloads/master/doc-qt5/code/class_Cell.html
    - KLayout Flatten 手册:
      https://klayout.org/downloads/master/doc-qt5/manual/flatten.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    if levels < -1:
        raise ValueError(
            f"levels 必须 >= -1，得到 {levels}。"
            f"禁止 fall-back（R03）。"
        )

    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)

    # 扁平化前统计
    # 注: ly.cells() 返回缓存值不可靠，用 len(list(ly.each_cell())) 获取实际值
    # 来源: R326 冒烟测试，ly.cells()=2 vs len(list(ly.each_cell()))=1
    cells_before = len(list(ly.each_cell()))
    instances_before = int(top_cell.child_instances())
    shapes_before = _count_shapes_rec(top_cell, ly)

    # 扁平化
    # KLayout 0.30.9: Cell.flatten(levels, prune)
    # 来源: https://klayout.org/downloads/master/doc-qt5/code/class_Cell.html
    top_cell.flatten(levels, prune)

    # prune=True 时手动删除孤儿 cell（KLayout prune 实测可能不删除）
    if prune:
        _delete_orphan_cells(ly)

    # 扁平化后统计
    # 注: ly.cells() 返回缓存值不可靠，用 len(list(ly.each_cell())) 获取实际值
    cells_after = len(list(ly.each_cell()))
    instances_after = int(top_cell.child_instances())
    shapes_after = _count_shapes_rec(top_cell, ly)

    # 写出
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII 扁平化: %s → %s (cells %d→%d, instances %d→%d, shapes %d→%d)",
        in_path, out_path,
        cells_before, cells_after,
        instances_before, instances_after,
        shapes_before, shapes_after,
    )

    return FlattenReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        dbu=dbu,
        top_cell_name=str(top_cell.name),
        levels=levels,
        prune=prune,
        cells_before=cells_before,
        cells_after=cells_after,
        instances_before=instances_before,
        instances_after=instances_after,
        shapes_before=shapes_before,
        shapes_after=shapes_after,
    )


def generate_flatten_report(
    gds_path: str | Path,
    output_path: str | Path,
    levels: int = -1,
    prune: bool = True,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 扁平化报告（R326）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        levels: 扁平化层次数。
        prune: 是否删除孤儿 cell。
        top_cell_name: 指定顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式 / levels < -1 / top_cell 不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = flatten_gdsii(
        gds_path,
        output_path,
        levels=levels,
        prune=prune,
        top_cell_name=top_cell_name,
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
def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R326 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        return top_cell

    top_cells = [ly.cell(int(ci)) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
        )
    return top_cells[0]


def _count_shapes_rec(top_cell, ly) -> int:
    """递归统计 top cell 的 shape 总数（R326 内部函数）。

    用 RecursiveShapeIterator 遍历所有层的所有 shapes（含子实例）。

    来源:
    - KLayout RecursiveShapeIterator:
      https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
    """
    count = 0
    for li in ly.layer_indices():
        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            count += 1
            it.next()
    return count


def _delete_orphan_cells(ly) -> None:
    """删除孤儿 cell（不再被任何 cell 实例化的非 top cell，R326 内部函数）。

    KLayout 的 Cell.flatten(prune=True) 实测可能不删除孤儿 cell，
    此函数手动清理。

    来源:
    - KLayout Cell 删除:
      https://klayout.org/downloads/master/doc-qt5/code/class_Layout.html
    """
    top_cell_indices = set(int(ci) for ci in ly.each_top_cell())
    # ly.each_cell() 返回 Cell 对象迭代器（非 index）
    all_cells = [cell for cell in ly.each_cell()]
    all_cell_indices = [int(cell.cell_index()) for cell in all_cells]
    # 收集所有被实例化的 cell index
    instantiated = set()
    for cell in all_cells:
        for inst in cell.each_inst():
            instantiated.add(int(inst.cell_index))
    # 删除非 top 且未被实例化的 cell
    for ci_int in all_cell_indices:
        if ci_int in top_cell_indices:
            continue
        if ci_int not in instantiated:
            ly.delete_cell(ci_int)


def _render_text_report(report: FlattenReport) -> str:
    """渲染纯文本报告（R326 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 扁平化报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"扁平化层次: {report.levels}（-1=全部）")
    lines.append(f"删除孤儿 cell: {report.prune}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("扁平化统计:")
    lines.append("-" * 60)
    lines.append(f"{'指标':<20} {'扁平前':>12} {'扁平后':>12} {'变化':>12}")
    lines.append(f"{'cell 数':<20} {report.cells_before:>12} "
                 f"{report.cells_after:>12} "
                 f"{report.cells_after - report.cells_before:>+12}")
    lines.append(f"{'实例数':<20} {report.instances_before:>12} "
                 f"{report.instances_after:>12} "
                 f"{report.instances_after - report.instances_before:>+12}")
    lines.append(f"{'shape 数':<20} {report.shapes_before:>12} "
                 f"{report.shapes_after:>12} "
                 f"{report.shapes_after - report.shapes_before:>+12}")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: FlattenReport) -> str:
    """渲染 Markdown 报告（R326 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 扁平化报告")
    lines.append("")
    lines.append(f"**输入文件**: `{report.input_path}`")
    lines.append(f"**输出文件**: `{report.output_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**扁平化层次**: {report.levels}（-1=全部）")
    lines.append(f"**删除孤儿 cell**: {report.prune}")
    lines.append("")
    lines.append("## 扁平化统计")
    lines.append("")
    lines.append("| 指标 | 扁平前 | 扁平后 | 变化 |")
    lines.append("|------|--------|--------|------|")
    lines.append(f"| cell 数 | {report.cells_before} | "
                 f"{report.cells_after} | "
                 f"{report.cells_after - report.cells_before:+d} |")
    lines.append(f"| 实例数 | {report.instances_before} | "
                 f"{report.instances_after} | "
                 f"{report.instances_after - report.instances_before:+d} |")
    lines.append(f"| shape 数 | {report.shapes_before} | "
                 f"{report.shapes_after} | "
                 f"{report.shapes_after - report.shapes_before:+d} |")
    return "\n".join(lines)
