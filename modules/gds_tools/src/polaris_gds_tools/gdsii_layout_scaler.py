"""GDSII 版图缩放工具（R337，GDSII Layout Scaler）。

按有理数比例对 GDSII 版图进行缩放，保留 cell 层次结构。

## 核心概念

- **版图缩放（Layout Scaling）**: 按比例缩放版图的所有几何元素（polygon、
  box、path、text）和 cell 实例位置。常用于:
  - 单位转换（如 μm → nm，scale_factor=1000）
  - 工艺节点迁移（如 130nm → 90nm，scale_factor=0.692）
  - 缩略图生成（scale_factor=0.1）
- **保留层次**: 使用 KLayout Layout.scale_and_snap 原地缩放整个 cell 树，
  保留 cell 实例层次结构，不破坏设计组织。
- **网格对齐**: 缩放后 snap 到 grid 网格，避免浮点精度导致的网格违例。

## KLayout 0.30.9 API 关键事实（R337 冒烟测试实测）

- `Layout.scale_and_snap(cell, grid, mult, div)`: 按 mult/div 比例缩放 cell，
  并 snap 到 grid 网格。cell 内所有 shapes 和子实例都被缩放。
  - `cell`: Cell 对象或 cell_index
  - `grid`: int，网格大小（dbu 单位，1=1 dbu 精度）
  - `mult`: int，分子
  - `div`: int，分母
- `Layout.write(path)`: 写出整个 layout
- `Layout.each_top_cell()`: 顶层 cell index 迭代器
- `Layout.cell(ci)`: 按 index 取 Cell
- `Cell.bbox()`: cell 的 bbox（dbu 单位，含子实例）

实测验证（R337 冒烟测试）:
- 源 bbox (0,0)-(100,50) μm
- scale_and_snap(top, 1, 1, 2) → bbox (0,0)-(50,25) μm  # 0.5x ✓
- scale_and_snap(top, 1, 2, 1) → bbox (0,0)-(200,100) μm # 2.0x ✓

## 算法

1. 用 `Layout.read` 读取 GDSII
2. 将 `scale_factor` (float) 转换为最简分数 `mult/div`（用 `Fraction`）
3. 对每个顶层 cell 调用 `scale_and_snap(cell, grid, mult, div)`
4. 用 `Layout.write` 写出

## scale_factor 转换规则

- 0.5 → Fraction(1, 2) → mult=1, div=2
- 2.0 → Fraction(2, 1) → mult=2, div=1
- 1.5 → Fraction(3, 2) → mult=3, div=2
- 0.1 → Fraction(1, 10) → mult=1, div=10
- 1.0 → Fraction(1, 1) → mult=1, div=1（无缩放）

`Fraction.limit_denominator(max_denominator)` 用于限制分母上限，避免
无限循环小数（如 0.333... → 1/3）产生过大分母。

## 学术依据

- KLayout Layout.scale_and_snap:
  https://klayout.org/doc-qt5/code/class_Layout.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- Python Fraction: https://docs.python.org/3/library/fractions.html
- Calibre Scaling: https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout Cell Statistics:
  https://www.klayout.org/doc-qt5/about/cell_views.html
- KLayout Trans class:
  https://www.klayout.org/doc-qt5/code/class_Trans.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "ScaleReport",
    "scale_gdsii",
    "generate_scale_report",
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
            "klayout 未安装，无法执行 GDSII 缩放。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class ScaleReport:
    """GDSII 版图缩放报告（R337）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        scale_factor: 用户指定的缩放比例（float）。
        mult: 实际使用的分子（int）。
        div: 实际使用的分母（int）。
        grid_dbu: 网格大小（dbu 单位）。
        dbu: 数据库单位（μm）。
        top_cell_names: 顶层 cell 名列表。
        original_bbox_um: 缩放前顶层 cell bbox (xmin, ymin, xmax, ymax) μm
            （单顶层 cell 时有效，多顶层为 (0,0,0,0)）。
        scaled_bbox_um: 缩放后顶层 cell bbox (xmin, ymin, xmax, ymax) μm
            （单顶层 cell 时有效，多顶层为 (0,0,0,0)）。
        actual_scale: 实际缩放比例（mult/div，float），
            用于检查 Fraction 转换是否损失精度。
    """

    input_path: str = ""
    output_path: str = ""
    scale_factor: float = 1.0
    mult: int = 1
    div: int = 1
    grid_dbu: int = 1
    dbu: float = 0.0
    top_cell_names: list[str] = field(default_factory=list)
    original_bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    scaled_bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    actual_scale: float = 1.0


# =============================================================================
# 辅助函数
# =============================================================================
def _scale_factor_to_fraction(
    scale_factor: float, max_denominator: int = 10000
) -> tuple[int, int]:
    """将浮点缩放比例转换为最简分数 (mult, div)。

    用 Fraction.limit_denominator 限制分母上限，避免无限循环小数产生过大
    分母。例如 0.333... → 1/3（max_denominator=10000 时）。

    Args:
        scale_factor: 缩放比例（float，>0）。
        max_denominator: 分母上限（默认 10000）。

    Returns:
        (mult, div) 元组，均为正整数，gcd(mult, div)=1。

    Raises:
        ValueError: scale_factor <= 0 或 max_denominator < 1。

    来源:
    - Python Fraction: https://docs.python.org/3/library/fractions.html
    """
    if scale_factor <= 0:
        raise ValueError(
            f"scale_factor 必须 > 0，得到 {scale_factor}。禁止 fall-back（R03）。"
        )
    if max_denominator < 1:
        raise ValueError(
            f"max_denominator 必须 >= 1，得到 {max_denominator}。"
        )
    frac = Fraction(scale_factor).limit_denominator(max_denominator)
    mult = int(frac.numerator)
    div = int(frac.denominator)
    if mult <= 0 or div <= 0:
        raise ValueError(
            f"Fraction 转换异常: scale_factor={scale_factor}, "
            f"mult={mult}, div={div}。禁止 fall-back（R03）。"
        )
    return mult, div


def _bbox_to_um(bbox, dbu: float) -> tuple[float, float, float, float]:
    """将 db.Box（dbu 单位）转换为 μm 元组。"""
    return (
        float(bbox.left) * dbu,
        float(bbox.bottom) * dbu,
        float(bbox.right) * dbu,
        float(bbox.top) * dbu,
    )


# =============================================================================
# 缩放主入口
# =============================================================================
def _validate_scale_inputs(
    input_path: str | Path,
    scale_factor: float,
    grid_dbu: int,
) -> Path:
    """校验 scale_gdsii 输入参数（Extract Method）。

    Args:
        input_path: 输入 GDSII 文件路径。
        scale_factor: 缩放比例。
        grid_dbu: 网格大小（dbu 单位）。

    Returns:
        输入文件 Path 对象。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / scale_factor <= 0 / grid_dbu < 1。
    """
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {input_path}")
    if scale_factor <= 0:
        raise ValueError(
            f"scale_factor 必须 > 0，得到 {scale_factor}。禁止 fall-back（R03）。"
        )
    if grid_dbu < 1:
        raise ValueError(
            f"grid_dbu 必须 >= 1，得到 {grid_dbu}。禁止 fall-back（R03）。"
        )
    return in_path


def _read_gdsii_layout(db, in_path: Path, input_path):
    """读取 GDSII 文件到 Layout 对象（Extract Method，含异常包装）。"""
    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    top_cell_indices = [int(ci) for ci in ly.each_top_cell()]
    if not top_cell_indices:
        raise ValueError(
            f"GDSII 文件 {input_path} 无任何 cell，文件可能为空或损坏"
        )
    return ly, top_cell_indices


def _select_cells_to_scale(
    ly, top_cell_indices: list[int], top_cell_name: str | None,
) -> tuple[list, list[str]]:
    """确定要缩放的 cell 列表与顶层 cell 名列表（Extract Method）。

    Args:
        ly: KLayout Layout 对象。
        top_cell_indices: 顶层 cell 索引列表。
        top_cell_name: 指定顶层 cell 名（None=全部顶层）。

    Returns:
        (cells_to_scale, top_cell_names_list)。

    Raises:
        ValueError: top_cell_name 不存在。
    """
    top_cell_names_list = sorted(
        ly.cell(ci).name for ci in top_cell_indices
    )
    if top_cell_name is not None:
        target_cell = ly.cell(top_cell_name)
        if target_cell is None:
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {top_cell_names_list}"
            )
        cells_to_scale = [target_cell]
    else:
        cells_to_scale = [ly.cell(ci) for ci in top_cell_indices]
    return cells_to_scale, top_cell_names_list


def _write_gdsii_layout(ly, out_path: Path):
    """写出 GDSII 文件（Extract Method，含异常包装）。"""
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e


def scale_gdsii(
    input_path: str | Path,
    output_path: str | Path,
    scale_factor: float,
    grid_dbu: int = 1,
    max_denominator: int = 10000,
    top_cell_name: str | None = None,
) -> ScaleReport:
    """对 GDSII 文件按比例缩放（R337）。

    用 KLayout `Layout.scale_and_snap(cell, grid, mult, div)` 按有理数比例
    缩放版图。保留 cell 层次结构，缩放后 snap 到 grid 网格。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        scale_factor: 缩放比例（>0，如 0.5=缩小一半，2.0=放大一倍）。
        grid_dbu: 网格大小（dbu 单位，默认 1=1 dbu 精度）。
        max_denominator: Fraction 转换的分母上限（默认 10000）。
        top_cell_name: 指定顶层 cell 名（None 缩放所有顶层 cell）。
            指定后只缩放该 cell，其他顶层 cell 保持不变。

    Returns:
        ScaleReport 缩放报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / scale_factor <= 0 / grid_dbu < 1 /
            top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Layout.scale_and_snap:
      https://klayout.org/doc-qt5/code/class_Layout.html
    - Python Fraction:
      https://docs.python.org/3/library/fractions.html
    - Fowler, "Refactoring" 2nd ed., 2018, Extract Method
      https://martinfowler.com/books/refactoring.html
    """
    db = _import_klayout_db()
    in_path = _validate_scale_inputs(input_path, scale_factor, grid_dbu)
    out_path = Path(output_path)

    # 转换 scale_factor → (mult, div)
    mult, div = _scale_factor_to_fraction(scale_factor, max_denominator)
    actual_scale = mult / div

    # 读取 GDSII
    ly, top_cell_indices = _read_gdsii_layout(db, in_path, input_path)
    dbu = float(ly.dbu)

    # 确定要缩放的 cell
    cells_to_scale, top_cell_names_list = _select_cells_to_scale(
        ly, top_cell_indices, top_cell_name
    )

    # 记录缩放前 bbox（仅单顶层 cell 时有意义）
    original_bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    if len(cells_to_scale) == 1:
        original_bbox_um = _bbox_to_um(cells_to_scale[0].bbox(), dbu)

    # 执行缩放
    for cell in cells_to_scale:
        ly.scale_and_snap(cell, grid_dbu, mult, div)

    # 记录缩放后 bbox
    scaled_bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    if len(cells_to_scale) == 1:
        scaled_bbox_um = _bbox_to_um(cells_to_scale[0].bbox(), dbu)

    # 写出
    _write_gdsii_layout(ly, out_path)

    logger.info(
        "GDSII 缩放: %s → %s (scale=%s, mult=%d, div=%d, grid=%d dbu, "
        "cells=%d)",
        in_path, out_path, scale_factor, mult, div, grid_dbu,
        len(cells_to_scale),
    )

    return ScaleReport(
        input_path=str(input_path),
        output_path=str(output_path),
        scale_factor=scale_factor,
        mult=mult,
        div=div,
        grid_dbu=grid_dbu,
        dbu=dbu,
        top_cell_names=top_cell_names_list,
        original_bbox_um=original_bbox_um,
        scaled_bbox_um=scaled_bbox_um,
        actual_scale=actual_scale,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_scale_report(
    input_path: str | Path,
    output_path: str | Path,
    scale_factor: float,
    grid_dbu: int = 1,
    max_denominator: int = 10000,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """缩放 GDSII 并生成报告字符串（R337）。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        scale_factor: 缩放比例（>0）。
        grid_dbu: 网格大小（dbu 单位，默认 1）。
        max_denominator: Fraction 分母上限（默认 10000）。
        top_cell_name: 指定顶层 cell 名（None 缩放所有顶层 cell）。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = scale_gdsii(
        input_path,
        output_path,
        scale_factor,
        grid_dbu=grid_dbu,
        max_denominator=max_denominator,
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
# 内部渲染函数
# =============================================================================
def _render_text_report(report: ScaleReport) -> str:
    """渲染纯文本报告（R337 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 版图缩放报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("缩放参数")
    lines.append("-" * 60)
    lines.append(f"指定缩放比例: {report.scale_factor}")
    lines.append(f"实际缩放比例: {report.actual_scale}")
    lines.append(f"分子 mult: {report.mult}")
    lines.append(f"分母 div: {report.div}")
    lines.append(f"网格 grid: {report.grid_dbu} dbu")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append("")
    lines.append("-" * 60)
    lines.append("Cell 信息")
    lines.append("-" * 60)
    lines.append(f"顶层 cell: {report.top_cell_names}")
    if report.original_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.original_bbox_um
        lines.append(
            f"缩放前 bbox: ({l:.4f}, {b:.4f}) - ({r:.4f}, {t:.4f}) μm"
        )
    if report.scaled_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.scaled_bbox_um
        lines.append(
            f"缩放后 bbox: ({l:.4f}, {b:.4f}) - ({r:.4f}, {t:.4f}) μm"
        )
    return "\n".join(lines)


def _render_markdown_report(report: ScaleReport) -> str:
    """渲染 Markdown 报告（R337 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 版图缩放报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append("")
    lines.append("## 缩放参数")
    lines.append("")
    lines.append("| 参数 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 指定缩放比例 | {report.scale_factor} |")
    lines.append(f"| 实际缩放比例 | {report.actual_scale} |")
    lines.append(f"| 分子 mult | {report.mult} |")
    lines.append(f"| 分母 div | {report.div} |")
    lines.append(f"| 网格 grid | {report.grid_dbu} dbu |")
    lines.append(f"| dbu | {report.dbu} μm |")
    lines.append("")
    lines.append("## Cell 信息")
    lines.append("")
    lines.append(f"- **顶层 cell**: {report.top_cell_names}")
    if report.original_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.original_bbox_um
        lines.append(
            f"- **缩放前 bbox**: ({l:.4f}, {b:.4f}) - ({r:.4f}, {t:.4f}) μm"
        )
    if report.scaled_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.scaled_bbox_um
        lines.append(
            f"- **缩放后 bbox**: ({l:.4f}, {b:.4f}) - ({r:.4f}, {t:.4f}) μm"
        )
    return "\n".join(lines)


def _render_json_report(report: ScaleReport) -> str:
    """渲染 JSON 报告（R337 内部函数）。"""
    import json
    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "scale_factor": report.scale_factor,
        "actual_scale": report.actual_scale,
        "mult": report.mult,
        "div": report.div,
        "grid_dbu": report.grid_dbu,
        "dbu": report.dbu,
        "top_cell_names": report.top_cell_names,
        "original_bbox_um": list(report.original_bbox_um),
        "scaled_bbox_um": list(report.scaled_bbox_um),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
