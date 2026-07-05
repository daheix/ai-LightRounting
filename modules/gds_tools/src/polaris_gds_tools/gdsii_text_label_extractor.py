"""GDSII 文本标签提取器（R323，Text Label Extractor）。

提取 GDSII 文件中所有 text 标签，用于命名/标注验证、器件识别、引脚定位。

## 核心概念

- **Text 标签**: GDSII TEXT 元素，附带字符串和位置
- **典型用途**:
  - SiEPIC PDK TEXT 层 (10,0): 器件名标注
  - SiEPIC PDK LABEL 层 (11,0): 引脚名标注
  - 用户自定义层: 任意命名/注释
- **递归提取**: 从顶层 cell 递归遍历所有子 cell 实例中的 text

## 算法

1. 读取 GDSII 文件
2. 对每个层:
   - 用 KLayout `Cell.begin_shapes_rec(layer_index)` 递归遍历所有 shapes
   - 对每个 shape，用 `Shape.is_text()` 判断是否为 text
   - 提取 `Shape.text_string`（文本内容）和 `Shape.text_pos`（位置，dbu 单位）
   - 用 `RecursiveShapeIterator.cell()` 获取 shape 所在的 cell 名
3. 按 layer_map 映射层名，按层/cell 分组统计

## KLayout 0.30.9 API 关键事实

- `Cell.begin_shapes_rec(layer_index)` 返回 `RecursiveShapeIterator`
- `RecursiveShapeIterator.at_end()` / `.next()` / `.shape()` / `.cell()`
- `Shape.is_text()` 判断是否为 text shape
- `Shape.text_string` 返回文本字符串（属性）
- `Shape.text_pos` 返回 `Vector`（dbu 单位，属性）
- `Vector.x` / `Vector.y` 为 dbu 整数坐标
- `Layout.layer_indices()` 返回所有层索引迭代器
- `Layout.get_info(layer_index)` 返回 `LayerInfo`，含 `.layer` / `.datatype`

## 学术依据

- KLayout Text class: https://www.klayout.de/doc-qt5/code/class_Text.html
- KLayout Shape class（is_text / text_string / text_pos）:
  https://www.klayout.org/doc-qt4/code/class_Shape.html
- KLayout Shapes overview（text 提取模式）:
  https://klayout.org/klayout-pypi/overview/shapes/
- KLayout Texts overview（位置/对齐属性）:
  https://klayout.org/klayout-pypi/overview/geometry/texts/
- KLayout DRC labels（DRC 文本层提取）:
  https://klayout.org/downloads/master/doc-qt4/about/drc_ref_source.html
- GDSII TEXT record（流格式标准）:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK Text/Label 层标准:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout RecursiveShapeIterator:
  https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from polaris_gds_tools._common import get_default_layer_map as _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "TextLabel",
    "TextLabelReport",
    "extract_text_labels",
    "generate_text_label_report",
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
            "klayout 未安装，无法执行 GDSII 文本标签提取。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class TextLabel:
    """单个文本标签（R323）。

    Attributes:
        text: 文本内容。
        layer_name: 层名（来自 layer_map 映射）。
        gds_layer: GDSII 层号。
        gds_datatype: GDSII datatype。
        x_um: X 坐标（μm）。
        y_um: Y 坐标（μm）。
        cell_name: 该 text 所属的 cell 名（递归遍历时的当前 cell）。
    """

    text: str
    layer_name: str
    gds_layer: int
    gds_datatype: int
    x_um: float
    y_um: float
    cell_name: str


@dataclass
class TextLabelReport:
    """GDSII 文本标签提取报告（R323）。

    Attributes:
        file_path: GDSII 文件路径。
        dbu: 数据库单位（μm，KLayout Layout.dbu 返回 μm）。
        top_cell_name: 顶层 cell 名。
        labels: 所有 TextLabel 列表（按层号→datatype→y→x 排序）。
        total_count: 文本标签总数。
        layer_counts: 按层名分组的计数 {layer_name: count}。
        cell_counts: 按 cell 名分组的计数 {cell_name: count}。
    """

    file_path: str
    dbu: float = 0.0
    top_cell_name: str = ""
    labels: list[TextLabel] = field(default_factory=list)
    total_count: int = 0
    layer_counts: dict[str, int] = field(default_factory=dict)
    cell_counts: dict[str, int] = field(default_factory=dict)


# =============================================================================
# 文本提取
# =============================================================================
def _text_labels_load_layout(
    db, gds_path: str | Path, layer_map, top_cell_name: str | None,
):
    """加载 GDSII layout 并校验（R03 禁止 fall-back）。

    Args:
        db: klayout.db 模块。
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。

    Returns:
        (ly, dbu, top_cell, layer_map)。
    """
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    if layer_map is None:
        layer_map = _get_default_layer_map()
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)
    return ly, dbu, top_cell, layer_map


def _text_labels_collect_one_layer(
    top_cell, li: int, layer_map: dict, dbu: float,
    allowed_layer_keys: set | None,
) -> list:
    """递归遍历单层收集 TEXT 元素。

    Args:
        top_cell: klayout.db.Cell。
        li: layer index。
        layer_map: 层映射。
        dbu: 数据库单位（μm）。
        allowed_layer_keys: 允许的 (layer, datatype) 集合（None 提取所有）。

    Returns:
        list[TextLabel] 该层文本标签列表（可能为空）。

    来源:
        KLayout RecursiveShapeIterator:
        https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
    """
    info = top_cell.layout().get_info(li)
    gds_layer = int(info.layer)
    gds_datatype = int(info.datatype)
    layer_key = (gds_layer, gds_datatype)
    layer_name = layer_map.get(
        layer_key, f"LAYER_{gds_layer}_{gds_datatype}"
    )
    if allowed_layer_keys is not None and layer_key not in allowed_layer_keys:
        return []
    labels: list = []
    it = top_cell.begin_shapes_rec(li)
    while not it.at_end():
        shape = it.shape()
        if shape.is_text():
            text_str = str(shape.text_string)
            pos = shape.text_pos
            cell_obj = it.cell()
            labels.append({
                "text": text_str,
                "layer_name": layer_name,
                "gds_layer": gds_layer,
                "gds_datatype": gds_datatype,
                "x_um": float(pos.x) * dbu,
                "y_um": float(pos.y) * dbu,
                "cell_name": str(cell_obj.name),
            })
        it.next()
    return labels


def extract_text_labels(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_extract: list[str] | None = None,
) -> TextLabelReport:
    """提取 GDSII 文件中所有文本标签（R323）。

    递归遍历顶层 cell 及其所有子 cell 实例，提取所有 TEXT 元素。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        layers_to_extract: 仅提取指定层名的 text（None 提取所有层）。

    Returns:
        TextLabelReport 文本标签报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Shape API: https://www.klayout.org/doc-qt4/code/class_Shape.html
    """
    db = _import_klayout_db()
    ly, dbu, top_cell, layer_map = _text_labels_load_layout(
        db, gds_path, layer_map, top_cell_name,
    )
    # 若指定 layers_to_extract，构造允许的 (layer, datatype) 集合
    allowed_layer_keys: set[tuple[int, int]] | None = None
    if layers_to_extract is not None:
        allowed_layer_keys = set()
        for (g, d), name in layer_map.items():
            if name in layers_to_extract:
                allowed_layer_keys.add((g, d))
    # 遍历所有层收集 TEXT 元素
    raw_labels: list[dict] = []
    for li in ly.layer_indices():
        raw_labels.extend(_text_labels_collect_one_layer(
            top_cell, li, layer_map, dbu, allowed_layer_keys,
        ))
    labels: list[TextLabel] = [
        TextLabel(
            text=rl["text"], layer_name=rl["layer_name"],
            gds_layer=rl["gds_layer"], gds_datatype=rl["gds_datatype"],
            x_um=rl["x_um"], y_um=rl["y_um"], cell_name=rl["cell_name"],
        )
        for rl in raw_labels
    ]
    # 排序: gds_layer → gds_datatype → y_um → x_um
    labels.sort(
        key=lambda lbl: (
            lbl.gds_layer, lbl.gds_datatype, lbl.y_um, lbl.x_um,
        )
    )
    layer_counts = dict(Counter(lbl.layer_name for lbl in labels))
    cell_counts = dict(Counter(lbl.cell_name for lbl in labels))
    return TextLabelReport(
        file_path=str(gds_path),
        dbu=dbu,
        top_cell_name=str(top_cell.name),
        labels=labels,
        total_count=len(labels),
        layer_counts=layer_counts,
        cell_counts=cell_counts,
    )


def generate_text_label_report(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_extract: list[str] | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 文本标签提取报告（R323）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射。
        top_cell_name: 指定顶层 cell 名。
        layers_to_extract: 仅提取指定层名（None 提取所有层）。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式 / 文件无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = extract_text_labels(
        gds_path,
        layer_map=layer_map,
        top_cell_name=top_cell_name,
        layers_to_extract=layers_to_extract,
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
    """获取顶层 cell（R323 内部函数）。"""
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


def _render_text_report(report: TextLabelReport) -> str:
    """渲染纯文本报告（R323 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 文本标签提取报告")
    lines.append("=" * 60)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"文本标签总数: {report.total_count}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("按层分组统计:")
    lines.append("-" * 60)
    for layer_name, count in sorted(report.layer_counts.items()):
        lines.append(f"  {layer_name}: {count}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("按 cell 分组统计:")
    lines.append("-" * 60)
    for cell_name, count in sorted(report.cell_counts.items()):
        lines.append(f"  {cell_name}: {count}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("所有文本标签:")
    lines.append("-" * 60)
    lines.append(
        f"{'文本':<25} {'层名':<12} {'GDS':<8} {'X(μm)':>8} "
        f"{'Y(μm)':>8} {'cell':<15}"
    )
    for lbl in report.labels:
        text_display = lbl.text[:23] if len(lbl.text) > 23 else lbl.text
        gds_str = f"{lbl.gds_layer}/{lbl.gds_datatype}"
        lines.append(
            f"{text_display:<25} {lbl.layer_name:<12} {gds_str:<8} "
            f"{lbl.x_um:>8.3f} {lbl.y_um:>8.3f} {lbl.cell_name:<15}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: TextLabelReport) -> str:
    """渲染 Markdown 报告（R323 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 文本标签提取报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**文本标签总数**: {report.total_count}")
    lines.append("")
    lines.append("## 按层分组统计")
    lines.append("")
    lines.append("| 层名 | 数量 |")
    lines.append("|------|------|")
    for layer_name, count in sorted(report.layer_counts.items()):
        lines.append(f"| {layer_name} | {count} |")
    lines.append("")
    lines.append("## 按 cell 分组统计")
    lines.append("")
    lines.append("| cell 名 | 数量 |")
    lines.append("|---------|------|")
    for cell_name, count in sorted(report.cell_counts.items()):
        lines.append(f"| {cell_name} | {count} |")
    lines.append("")
    lines.append("## 所有文本标签")
    lines.append("")
    lines.append(
        "| 文本 | 层名 | GDS 层/datatype | X(μm) | Y(μm) | cell |"
    )
    lines.append("|------|------|-----------------|-------|-------|------|")
    for lbl in report.labels:
        gds_str = f"{lbl.gds_layer}/{lbl.gds_datatype}"
        lines.append(
            f"| {lbl.text} | {lbl.layer_name} | {gds_str} | "
            f"{lbl.x_um:.3f} | {lbl.y_um:.3f} | {lbl.cell_name} |"
        )
    return "\n".join(lines)
