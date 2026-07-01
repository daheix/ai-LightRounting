"""GDSII 版图合并工具（R333，GDSII Layout Merger）。

将多个 GDSII 文件合并到单一顶层 cell 的版图，每个源文件的顶层 cell
作为子实例插入到合并 wrapper cell 中，可选平移偏移。

## 核心概念

- **版图合并（Layout Merge）**: 多个 GDSII 文件合并为一个文件
- **Wrapper Cell**: 创建一个新 cell 作为合并后唯一顶层 cell
- **实例化（Instantiation）**: 各源顶层 cell 作为子实例插入 wrapper
- **平移偏移**: 各源 cell 可在 wrapper 中按 (dx, dy) μm 偏移放置
- **应用场景**:
  - 多个 IP 块拼接为完整芯片版图
  - 多版图比对/差分基线生成
  - 测试夹具与 DUT 合并
  - 芯片级 assembly

## 算法

1. 创建目标 Layout，设置 dbu
2. 对每个输入 GDSII，用 `Layout.read()` 追加模式读入（同一 Layout）
3. 创建 wrapper cell（合并后顶层 cell）
4. 收集读取后所有非 wrapper 的顶层 cell（即各源文件的顶层 cell）
5. 对每个源顶层 cell，按对应偏移实例化到 wrapper:
   - `db.CellInstArray(cell_index, db.Trans(db.Point(dx_dbu, dy_dbu)))`
   - `wrapper.insert(cell_inst_array)`
6. 删除各源顶层 cell 的顶层属性（wrapper 成为唯一顶层）
7. `Layout.write()` 写出合并后文件
8. 验证：重新读入检查 wrapper 是唯一顶层 cell，统计实例数

## KLayout 0.30.9 API 关键事实（实测）

- `Layout.read(path)`: **追加模式**，多次调用将多个 GDSII 文件的 cell 合并到同一 Layout
  - 来源: https://www.klayout.de/doc-qt5/code/class_Layout.html#method15
- `Layout.create_cell(name)`: 创建新 cell，返回 Cell 对象
  - 来源: https://www.klayout.de/doc-qt5/code/class_Layout.html#method46
- `Layout.each_top_cell()`: 返回顶层 cell index 迭代器
  - 来源: https://www.klayout.de/doc-qt5/code/class_Layout.html#method101
- `Layout.each_cell_top_down()`: 拓扑顺序所有 cell index 迭代器
- `Cell.cell_index()`: 获取 cell 的 index
- `Cell.each_inst()`: **返回实例迭代器**（替代不存在的 num_insts）
  - 来源: https://www.klayout.de/doc-qt5/code/class_Cell.html
- `Cell.insert(cell_inst_array)`: 插入 cell 实例数组
- `db.CellInstArray(cell_index, trans)`: 创建 cell 实例数组
  - 来源: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- `db.Trans(point)`: 平移变换（r0 旋转 + 平移）
  - 来源: https://www.klayout.de/doc-qt5/code/class_Trans.html
- `db.Point(x, y)`: 整数点（dbu 单位）
- `Instance.cell`: 引用的 Cell 对象
- `Instance.cell_index`: 引用 cell 的 index
- `Instance.trans`: 实例变换
- `Layout.write(path)`: 写出 GDSII
- `Layout.dbu`: 数据库单位（μm）
- `Cell.bbox()`: cell 的 bbox（dbu 单位，含所有子实例）

## 学术依据

- KLayout Layout class:
  https://www.klayout.de/doc-qt5/code/class_Layout.html
- KLayout Cell class（each_inst / insert / bbox）:
  https://www.klayout.de/doc-qt5/code/class_Cell.html
- KLayout CellInstArray class:
  https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- KLayout Trans class（仿射变换）:
  https://www.klayout.de/doc-qt5/code/class_Trans.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 流格式标准:
  https://en.wikipedia.org/wiki/GDS_File
- KLayout 多文件合并教程:
  https://www.klayout.de/doc-qt5/programming/database_api.html
- KLayout Python 包文档:
  https://klayout.org/klayout-pypi/
- gdsfactory merge_cells 参考:
  https://gdsfactory.github.io/gdsfactory/api.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "MergedCellInfo",
    "MergeReport",
    "merge_gdsii",
    "generate_merge_report",
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
            "klayout 未安装，无法执行 GDSII 版图合并。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class MergedCellInfo:
    """单个源 cell 合并信息（R333）。

    Attributes:
        source_file: 源 GDSII 文件路径。
        source_top_cell: 源文件顶层 cell 名。
        offset_um: 实例在 wrapper 中的偏移 (dx, dy) μm。
        cell_index: 合并后 layout 中该源 cell 的 index。
        instance_count: 该源 cell 在 wrapper 中的实例化次数（默认 1）。
    """

    source_file: str
    source_top_cell: str = ""
    offset_um: tuple[float, float] = (0.0, 0.0)
    cell_index: int = -1
    instance_count: int = 1


@dataclass
class MergeReport:
    """GDSII 合并报告（R333）。

    Attributes:
        output_path: 合并后输出 GDSII 文件路径。
        top_cell_name: 合并后顶层 cell 名（wrapper cell）。
        dbu: 数据库单位（μm，KLayout Layout.dbu 返回 μm）。
        input_files: 输入 GDSII 文件路径列表。
        merged_cells: 各源 cell 的合并信息列表。
        total_instance_count: wrapper cell 中实例总数。
        all_cell_count: 合并后 layout 中所有 cell 总数。
        bounding_box_um: wrapper cell 的 bbox (xmin, ymin, xmax, ymax) μm。
            若 wrapper 为空，bbox 为 (0, 0, 0, 0)。
    """

    output_path: str = ""
    top_cell_name: str = ""
    dbu: float = 0.0
    input_files: list[str] = field(default_factory=list)
    merged_cells: list[MergedCellInfo] = field(default_factory=list)
    total_instance_count: int = 0
    all_cell_count: int = 0
    bounding_box_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


# =============================================================================
# 合并主入口
# =============================================================================
def merge_gdsii(
    input_paths: list[Path] | list[str],
    output_path: Path | str,
    offsets_um: list[tuple[float, float]] | None = None,
    top_cell_name: str = "MERGED",
) -> MergeReport:
    """合并多个 GDSII 文件到单一顶层 cell 版图（R333）。

    用 `Layout.read()` 追加模式读取多个 GDSII 文件，创建 wrapper cell
    作为新顶层，各源顶层 cell 作为实例按指定偏移插入 wrapper。

    Args:
        input_paths: 输入 GDSII 文件路径列表（至少 1 个）。
        output_path: 输出合并后 GDSII 文件路径。
        offsets_um: 各源文件顶层 cell 在 wrapper 中的偏移列表（μm）。
            None 表示全部 (0, 0)。长度必须与 input_paths 一致。
        top_cell_name: 合并后 wrapper cell 名（默认 "MERGED"）。
            不能为空字符串。

    Returns:
        MergeReport 合并报告。

    Raises:
        FileNotFoundError: 任一输入文件不存在。
        ValueError: input_paths 空 / offsets_um 长度不匹配 /
            top_cell_name 空 / 某源文件无顶层 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Layout.read（追加模式）:
      https://www.klayout.de/doc-qt5/code/class_Layout.html#method15
    - KLayout CellInstArray:
      https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
    """
    db = _import_klayout_db()
    offsets_um = _validate_merge_params(input_paths, top_cell_name, offsets_um)
    target = db.Layout()
    target.dbu = 0.001  # 1nm 标准单位
    input_files_str, source_top_cells = _read_all_gdsii_sources(
        db, target, input_paths
    )
    wrapper, merged_cells = _instantiate_sources_into_wrapper(
        db, target, source_top_cells, offsets_um, top_cell_name, input_files_str
    )
    out_path = _write_merged_gdsii(target, output_path)
    instance_count, all_cell_count, bbox_um = _compute_merge_stats(target, wrapper)
    dbu = float(target.dbu)
    top_name = str(wrapper.name)
    logger.info(
        "GDSII 合并: %d 个文件 → %s (top=%s, instances=%d, cells=%d)",
        len(input_paths), out_path, top_name, instance_count, all_cell_count,
    )
    return MergeReport(
        output_path=str(out_path), top_cell_name=top_name, dbu=dbu,
        input_files=input_files_str, merged_cells=merged_cells,
        total_instance_count=instance_count, all_cell_count=all_cell_count,
        bounding_box_um=bbox_um,
    )


def _validate_merge_params(input_paths, top_cell_name, offsets_um) -> list[tuple[float, float]]:
    """校验 merge_gdsii 入参并检查文件存在性（R333 内部辅助，R03 禁止 fall-back）。

    Returns:
        归一化后的 offsets_um 列表（None 时全为 (0,0)）。

    Raises:
        ValueError: input_paths 空 / top_cell_name 空 / offsets_um 长度不匹配。
        FileNotFoundError: 任一输入文件不存在。
    """
    if not input_paths:
        raise ValueError("input_paths 不能为空。禁止 fall-back（R03）。")
    if not top_cell_name:
        raise ValueError("top_cell_name 不能为空字符串。禁止 fall-back（R03）。")
    if offsets_um is not None:
        if len(offsets_um) != len(input_paths):
            raise ValueError(
                f"offsets_um 长度 ({len(offsets_um)}) 必须与 "
                f"input_paths 长度 ({len(input_paths)}) 一致。禁止 fall-back（R03）。"
            )
    else:
        offsets_um = [(0.0, 0.0)] * len(input_paths)
    for p in input_paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"GDSII 文件不存在: {p}")
        if not path.is_file():
            raise ValueError(f"路径不是文件: {p}")
    return offsets_um


def _read_all_gdsii_sources(db, target, input_paths) -> tuple[list[str], list[str]]:
    """追加模式读取所有 GDSII 源文件（R333 内部辅助）。

    Layout.read 是追加模式：多次调用合并多个文件的 cell 到同一 Layout。
    来源: https://www.klayout.de/doc-qt5/code/class_Layout.html#method15

    Returns:
        (input_files_str, source_top_cells)。

    Raises:
        RuntimeError: 读取失败。ValueError: 文件未新增顶层 cell。
    """
    input_files_str: list[str] = []
    source_top_cells: list[str] = []
    for p in input_paths:
        path = Path(p)
        before_top = {int(ci) for ci in target.each_top_cell()}
        try:
            target.read(str(path))
        except Exception as e:
            raise RuntimeError(
                f"klayout 读取文件失败: {path} - {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e
        after_top = {int(ci) for ci in target.each_top_cell()}
        new_tops = after_top - before_top
        if not new_tops:
            raise ValueError(
                f"文件 {path} 读取后未新增顶层 cell，"
                f"文件可能为空或损坏。禁止 fall-back（R03）。"
            )
        first_new_ci = sorted(new_tops)[0]
        source_top_cells.append(str(target.cell(first_new_ci).name))
        input_files_str.append(str(p))
    return input_files_str, source_top_cells


def _instantiate_sources_into_wrapper(
    db, target, source_top_cells, offsets_um, top_cell_name, input_files_str
) -> tuple:
    """创建 wrapper cell 并实例化各源顶层 cell（R333 内部辅助）。

    Returns:
        (wrapper, merged_cells)。

    Raises:
        RuntimeError: 源 cell 找不到。
    """
    wrapper = target.create_cell(top_cell_name)
    source_ci_list: list[int] = []
    for src_name in source_top_cells:
        src_cell = target.cell(src_name)
        if src_cell is None:
            raise RuntimeError(
                f"源 cell '{src_name}' 在合并 layout 中找不到。禁止 fall-back（R03）。"
            )
        source_ci_list.append(int(src_cell.cell_index()))
    merged_cells: list = []
    for idx, (src_ci, (dx_um, dy_um)) in enumerate(zip(source_ci_list, offsets_um)):
        dx_dbu = int(round(dx_um / target.dbu))
        dy_dbu = int(round(dy_um / target.dbu))
        trans = db.Trans(db.Point(dx_dbu, dy_dbu))
        inst_array = db.CellInstArray(src_ci, trans)
        wrapper.insert(inst_array)
        merged_cells.append(MergedCellInfo(
            source_file=input_files_str[idx],
            source_top_cell=source_top_cells[idx],
            offset_um=(dx_um, dy_um), cell_index=src_ci, instance_count=1,
        ))
    return wrapper, merged_cells


def _write_merged_gdsii(target, output_path) -> Path:
    """写出合并后 GDSII（R333 内部辅助）。

    Raises:
        RuntimeError: 写出失败。
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出失败: {out_path} - {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    return out_path


def _compute_merge_stats(target, wrapper) -> tuple[int, int, tuple[float, float, float, float]]:
    """统计合并后报告数据（R333 内部辅助）。

    Returns:
        (instance_count, all_cell_count, bbox_um)。
    """
    instance_count = sum(1 for _ in wrapper.each_inst())
    all_cell_count = sum(1 for _ in target.each_cell_top_down())
    bbox = wrapper.bbox()
    if bbox.empty():
        bbox_um = (0.0, 0.0, 0.0, 0.0)
    else:
        bbox_um = (
            float(bbox.left) * target.dbu, float(bbox.bottom) * target.dbu,
            float(bbox.right) * target.dbu, float(bbox.top) * target.dbu,
        )
    return instance_count, all_cell_count, bbox_um


# =============================================================================
# 报告生成
# =============================================================================
def generate_merge_report(
    input_paths: list[Path] | list[str],
    output_path: Path | str,
    offsets_um: list[tuple[float, float]] | None = None,
    top_cell_name: str = "MERGED",
    output_format: str = "text",
) -> str:
    """合并 GDSII 并生成报告字符串（R333）。

    Args:
        input_paths: 输入 GDSII 文件路径列表。
        output_path: 输出合并后 GDSII 文件路径。
        offsets_um: 各源文件偏移列表（μm）。
        top_cell_name: wrapper cell 名。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = merge_gdsii(
        input_paths,
        output_path,
        offsets_um=offsets_um,
        top_cell_name=top_cell_name,
    )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(report)
    if fmt == "markdown":
        return _render_markdown_report(report)
    if fmt == "json":
        return _render_json_report(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown / json。"
    )


# =============================================================================
# 内部辅助函数
# =============================================================================
def _render_text_report(report: MergeReport) -> str:
    """渲染纯文本报告（R333 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 版图合并报告")
    lines.append("=" * 60)
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"输入文件数: {len(report.input_files)}")
    lines.append(f"实例总数: {report.total_instance_count}")
    lines.append(f"layout cell 总数: {report.all_cell_count}")
    xmin, ymin, xmax, ymax = report.bounding_box_um
    lines.append(
        f"bbox: ({xmin:.3f}, {ymin:.3f}) - ({xmax:.3f}, {ymax:.3f}) μm"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("合并的源 cell 列表:")
    lines.append("-" * 60)
    lines.append(
        f"{'#':<3} {'源文件':<30} {'源 cell':<15} "
        f"{'偏移(μm)':<15} {'idx':<5}"
    )
    for i, mc in enumerate(report.merged_cells):
        src_short = mc.source_file
        if len(src_short) > 28:
            src_short = "..." + src_short[-25:]
        offset_str = f"({mc.offset_um[0]:.2f}, {mc.offset_um[1]:.2f})"
        lines.append(
            f"{i + 1:<3} {src_short:<30} {mc.source_top_cell:<15} "
            f"{offset_str:<15} {mc.cell_index:<5}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: MergeReport) -> str:
    """渲染 Markdown 报告（R333 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 版图合并报告")
    lines.append("")
    lines.append(f"**输出文件**: `{report.output_path}`")
    lines.append(f"**顶层 cell**: `{report.top_cell_name}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**输入文件数**: {len(report.input_files)}")
    lines.append(f"**实例总数**: {report.total_instance_count}")
    lines.append(f"**layout cell 总数**: {report.all_cell_count}")
    xmin, ymin, xmax, ymax = report.bounding_box_um
    lines.append(
        f"**bbox**: ({xmin:.3f}, {ymin:.3f}) - "
        f"({xmax:.3f}, {ymax:.3f}) μm"
    )
    lines.append("")
    lines.append("## 合并的源 cell 列表")
    lines.append("")
    lines.append(
        "| # | 源文件 | 源 cell | 偏移(μm) | cell index |"
    )
    lines.append("|---|--------|---------|----------|-----------|")
    for i, mc in enumerate(report.merged_cells):
        offset_str = f"({mc.offset_um[0]:.2f}, {mc.offset_um[1]:.2f})"
        lines.append(
            f"| {i + 1} | `{mc.source_file}` | `{mc.source_top_cell}` | "
            f"{offset_str} | {mc.cell_index} |"
        )
    return "\n".join(lines)


def _render_json_report(report: MergeReport) -> str:
    """渲染 JSON 报告（R333 内部函数）。"""
    data = {
        "output_path": report.output_path,
        "top_cell_name": report.top_cell_name,
        "dbu": report.dbu,
        "input_files": report.input_files,
        "merged_cells": [
            {
                "source_file": mc.source_file,
                "source_top_cell": mc.source_top_cell,
                "offset_um": list(mc.offset_um),
                "cell_index": mc.cell_index,
                "instance_count": mc.instance_count,
            }
            for mc in report.merged_cells
        ],
        "total_instance_count": report.total_instance_count,
        "all_cell_count": report.all_cell_count,
        "bounding_box_um": list(report.bounding_box_um),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
