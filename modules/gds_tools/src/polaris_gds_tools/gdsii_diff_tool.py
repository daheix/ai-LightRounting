"""GDSII 文件对比工具（R321，GDSII Diff Tool）。

比较两个 GDSII 文件的几何差异，用于版本对比、设计变更检测。

## 核心概念

- **几何差异**: 两个 GDSII 文件中各层多边形集合的集合论差异
  - added: 在文件 B 但不在文件 A 中的几何（A → B 新增）
  - removed: 在文件 A 但不在文件 B 中的几何（A → B 删除）
  - common: 两个文件共有的几何（不变部分）
- **层差异**: 按层分别计算差异
- **面积差异**: added 和 removed 的面积统计

## 算法

1. 读取两个 GDSII 文件
2. 对每个 GDSII 层:
   - 用 KLayout Region 收集两个文件的多边形
   - 合并（merge）以消除重叠
   - 计算 A - B（removed）和 B - A（added）
   - 计算 A ∩ B（common）
3. 汇总各层差异

## 学术依据

- KLayout Region 运算（& | ^ -）:
  https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout Layout.read:
  https://www.klayout.org/doc-qt5/code/class_Layout.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- 集合论差集:
  https://en.wikipedia.org/wiki/Set_(mathematics)#Complements
- SiEPIC EBeam PDK 版本对比:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- git diff 算法（行级差异）:
  https://git-scm.com/docs/git-diff
- Myers 差异算法:
  https://en.wikipedia.org/wiki/Diff#Algorithm
- Fowler, "Refactoring"（版本对比模式）:
  https://refactoring.com/

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "DiffReport",
    "LayerDiff",
    "compare_gdsii_files",
    "generate_diff_report",
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
            "klayout 未安装，无法执行 GDSII 文件对比。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class LayerDiff:
    """单层差异（R321）。

    Attributes:
        layer_name: 层名。
        gds_layer: GDSII 层号。
        gds_datatype: GDSII datatype。
        added_area_um2: 新增几何面积（μm²）（B - A）。
        removed_area_um2: 删除几何面积（μm²）（A - B）。
        common_area_um2: 共有几何面积（μm²）（A ∩ B）。
        added_polygon_count: 新增多边形数。
        removed_polygon_count: 删除多边形数。
        common_polygon_count: 共有多边形数。
        is_identical: 该层是否完全一致（added=removed=0）。
    """

    layer_name: str
    gds_layer: int
    gds_datatype: int
    added_area_um2: float = 0.0
    removed_area_um2: float = 0.0
    common_area_um2: float = 0.0
    added_polygon_count: int = 0
    removed_polygon_count: int = 0
    common_polygon_count: int = 0
    is_identical: bool = True


@dataclass
class DiffReport:
    """GDSII 文件对比报告（R321）。

    Attributes:
        file_a: 文件 A 路径。
        file_b: 文件 B 路径。
        top_cell_a: 文件 A 顶层 cell 名。
        top_cell_b: 文件 B 顶层 cell 名。
        dbu_a: 文件 A 数据库单位（μm，KLayout Layout.dbu 返回 μm）。
        dbu_b: 文件 B 数据库单位（μm，KLayout Layout.dbu 返回 μm）。
        layer_diffs: 各层差异列表。
        total_added_area_um2: 总新增面积（μm²）。
        total_removed_area_um2: 总删除面积（μm²）。
        total_added_count: 总新增多边形数。
        total_removed_count: 总删除多边形数。
        is_identical: 两文件是否完全一致。
    """

    file_a: str
    file_b: str
    top_cell_a: str = ""
    top_cell_b: str = ""
    dbu_a: float = 0.0
    dbu_b: float = 0.0
    layer_diffs: list[LayerDiff] = field(default_factory=list)
    total_added_area_um2: float = 0.0
    total_removed_area_um2: float = 0.0
    total_added_count: int = 0
    total_removed_count: int = 0
    is_identical: bool = True


# =============================================================================
# 文件对比
# =============================================================================
def compare_gdsii_files(
    file_a: str | Path,
    file_b: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> DiffReport:
    """比较两个 GDSII 文件的几何差异（R321）。

    对每个 GDSII 层计算:
    - added: B - A（文件 B 新增的几何）
    - removed: A - B（文件 B 删除的几何）
    - common: A ∩ B（两文件共有的几何）

    Args:
        file_a: 文件 A 路径。
        file_b: 文件 B 路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。

    Returns:
        DiffReport 对比报告。

    Raises:
        FileNotFoundError: 任一文件不存在。
        ValueError: 文件无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region 运算: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    path_a = Path(file_a)
    path_b = Path(file_b)
    if not path_a.exists():
        raise FileNotFoundError(f"文件 A 不存在: {file_a}")
    if not path_b.exists():
        raise FileNotFoundError(f"文件 B 不存在: {file_b}")
    if not path_a.is_file():
        raise ValueError(f"文件 A 不是文件: {file_a}")
    if not path_b.is_file():
        raise ValueError(f"文件 B 不是文件: {file_b}")
    if layer_map is None:
        layer_map = _get_default_layer_map()
    ly_a, dbu_a, top_cell_a, ly_b, dbu_b, top_cell_b = _read_diff_layouts(
        db, path_a, path_b, file_a, file_b, top_cell_name
    )
    layers_a, layers_b, all_layer_keys = _collect_diff_layers(ly_a, ly_b)
    layer_diffs, total_added_area, total_removed_area, total_added_count, total_removed_count, is_identical = (
        _compute_all_layer_diffs(
            db, top_cell_a, top_cell_b, layers_a, layers_b, all_layer_keys,
            layer_map, dbu_a, dbu_b,
        )
    )
    return DiffReport(
        file_a=str(file_a), file_b=str(file_b),
        top_cell_a=top_cell_a.name, top_cell_b=top_cell_b.name,
        dbu_a=dbu_a, dbu_b=dbu_b, layer_diffs=layer_diffs,
        total_added_area_um2=total_added_area,
        total_removed_area_um2=total_removed_area,
        total_added_count=total_added_count,
        total_removed_count=total_removed_count, is_identical=is_identical,
    )


def _read_diff_layouts(db, path_a, path_b, file_a, file_b, top_cell_name) -> tuple:
    """读取两个 GDSII 文件并定位顶层 cell（R321 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly_a, dbu_a, top_cell_a, ly_b, dbu_b, top_cell_b)。

    Raises:
        RuntimeError: 读取失败。ValueError: top_cell_name 不存在。
    """
    ly_a = db.Layout()
    try:
        ly_a.read(str(path_a))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件 A 失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    ly_b = db.Layout()
    try:
        ly_b.read(str(path_b))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件 B 失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    dbu_a = float(ly_a.dbu)
    dbu_b = float(ly_b.dbu)
    top_cell_a = _get_top_cell(ly_a, top_cell_name, file_a)
    top_cell_b = _get_top_cell(ly_b, top_cell_name, file_b)
    return ly_a, dbu_a, top_cell_a, ly_b, dbu_b, top_cell_b


def _collect_diff_layers(ly_a, ly_b) -> tuple:
    """收集两个文件的所有层（R321 内部辅助）。

    Returns:
        (layers_a, layers_b, all_layer_keys)。
    """
    layers_a: dict[tuple[int, int], int] = {}
    for li in ly_a.layer_indices():
        info = ly_a.get_info(li)
        layers_a[(int(info.layer), int(info.datatype))] = li
    layers_b: dict[tuple[int, int], int] = {}
    for li in ly_b.layer_indices():
        info = ly_b.get_info(li)
        layers_b[(int(info.layer), int(info.datatype))] = li
    all_layer_keys = set(layers_a.keys()) | set(layers_b.keys())
    return layers_a, layers_b, all_layer_keys


def _compute_all_layer_diffs(
    db, top_cell_a, top_cell_b, layers_a, layers_b, all_layer_keys,
    layer_map, dbu_a, dbu_b,
) -> tuple:
    """逐层计算几何差异（R321 内部辅助）。

    Returns:
        (layer_diffs, total_added_area, total_removed_area,
         total_added_count, total_removed_count, is_identical)。

    来源: KLayout Region 运算 https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    layer_diffs: list[LayerDiff] = []
    total_added_area = total_removed_area = 0.0
    total_added_count = total_removed_count = 0
    is_identical = True
    dbu = dbu_a if dbu_a == dbu_b else dbu_a
    for gds_layer, gds_datatype in sorted(all_layer_keys):
        layer_name = layer_map.get(
            (gds_layer, gds_datatype), f"LAYER_{gds_layer}_{gds_datatype}",
        )
        region_a = db.Region()
        if (gds_layer, gds_datatype) in layers_a:
            region_a = db.Region(top_cell_a.begin_shapes_rec(layers_a[(gds_layer, gds_datatype)]))
        region_a.merge()
        region_b = db.Region()
        if (gds_layer, gds_datatype) in layers_b:
            region_b = db.Region(top_cell_b.begin_shapes_rec(layers_b[(gds_layer, gds_datatype)]))
        region_b.merge()
        added_region = region_b.dup()
        added_region -= region_a
        removed_region = region_a.dup()
        removed_region -= region_b
        common_region = region_a.dup()
        common_region &= region_b
        added_count = sum(1 for _ in added_region.each())
        removed_count = sum(1 for _ in removed_region.each())
        common_count = sum(1 for _ in common_region.each())
        added_area_um2 = int(added_region.area()) * dbu * dbu
        removed_area_um2 = int(removed_region.area()) * dbu * dbu
        common_area_um2 = int(common_region.area()) * dbu * dbu
        layer_identical = (added_count == 0 and removed_count == 0)
        if not layer_identical:
            is_identical = False
        layer_diffs.append(LayerDiff(
            layer_name=layer_name, gds_layer=gds_layer, gds_datatype=gds_datatype,
            added_area_um2=added_area_um2, removed_area_um2=removed_area_um2,
            common_area_um2=common_area_um2, added_polygon_count=added_count,
            removed_polygon_count=removed_count, common_polygon_count=common_count,
            is_identical=layer_identical,
        ))
        total_added_area += added_area_um2
        total_removed_area += removed_area_um2
        total_added_count += added_count
        total_removed_count += removed_count
    return (layer_diffs, total_added_area, total_removed_area,
            total_added_count, total_removed_count, is_identical)


# =============================================================================
# 报告生成
# =============================================================================
def generate_diff_report(
    file_a: str | Path,
    file_b: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 文件对比报告（R321）。

    Args:
        file_a: 文件 A 路径。
        file_b: 文件 B 路径。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 任一文件不存在。
        ValueError: 不支持的格式 / 文件无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = compare_gdsii_files(
        file_a, file_b, layer_map=layer_map, top_cell_name=top_cell_name,
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


def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R321 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        return top_cell

    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
        )
    return top_cells[0]


def _render_text_report(report: DiffReport) -> str:
    """渲染纯文本报告。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 文件对比报告")
    lines.append("=" * 60)
    lines.append(f"文件 A: {report.file_a}")
    lines.append(f"文件 B: {report.file_b}")
    lines.append(f"顶层 cell A: {report.top_cell_a}")
    lines.append(f"顶层 cell B: {report.top_cell_b}")
    lines.append(f"dbu A: {report.dbu_a} m")
    lines.append(f"dbu B: {report.dbu_b} m")
    status = "完全一致" if report.is_identical else "存在差异"
    lines.append(f"对比结果: {status}")
    lines.append(f"层数: {len(report.layer_diffs)}")
    lines.append(f"总新增面积: {report.total_added_area_um2:.4f} μm²")
    lines.append(f"总删除面积: {report.total_removed_area_um2:.4f} μm²")
    lines.append(f"总新增多边形: {report.total_added_count}")
    lines.append(f"总删除多边形: {report.total_removed_count}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("各层差异:")
    lines.append("-" * 60)
    for ld in report.layer_diffs:
        status = "一致" if ld.is_identical else "差异"
        lines.append(
            f"  {ld.layer_name} (GDS {ld.gds_layer}/{ld.gds_datatype}): {status}"
        )
        if not ld.is_identical:
            lines.append(f"    新增: {ld.added_polygon_count} 多边形, "
                         f"{ld.added_area_um2:.4f} μm²")
            lines.append(f"    删除: {ld.removed_polygon_count} 多边形, "
                         f"{ld.removed_area_um2:.4f} μm²")
        lines.append(f"    共有: {ld.common_polygon_count} 多边形, "
                     f"{ld.common_area_um2:.4f} μm²")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: DiffReport) -> str:
    """渲染 Markdown 报告。"""
    lines: list[str] = []
    lines.append("# GDSII 文件对比报告")
    lines.append("")
    lines.append(f"**文件 A**: `{report.file_a}`")
    lines.append(f"**文件 B**: `{report.file_b}`")
    lines.append(f"**顶层 cell A**: {report.top_cell_a}")
    lines.append(f"**顶层 cell B**: {report.top_cell_b}")
    lines.append(f"**dbu A**: {report.dbu_a} m")
    lines.append(f"**dbu B**: {report.dbu_b} m")
    status = "完全一致" if report.is_identical else "存在差异"
    lines.append(f"**对比结果**: {status}")
    lines.append(f"**层数**: {len(report.layer_diffs)}")
    lines.append(f"**总新增面积**: {report.total_added_area_um2:.4f} μm²")
    lines.append(f"**总删除面积**: {report.total_removed_area_um2:.4f} μm²")
    lines.append(f"**总新增多边形**: {report.total_added_count}")
    lines.append(f"**总删除多边形**: {report.total_removed_count}")
    lines.append("")
    lines.append("## 各层差异")
    lines.append("")
    lines.append(
        "| 层名 | GDS 层/datatype | 状态 | 新增数 | 新增面积(μm²) | "
        "删除数 | 删除面积(μm²) | 共有数 |"
    )
    lines.append(
        "|------|------------------|------|--------|---------------|"
        "--------|---------------|--------|"
    )
    for ld in report.layer_diffs:
        status = "一致" if ld.is_identical else "差异"
        lines.append(
            f"| {ld.layer_name} | {ld.gds_layer}/{ld.gds_datatype} | "
            f"{status} | {ld.added_polygon_count} | "
            f"{ld.added_area_um2:.4f} | {ld.removed_polygon_count} | "
            f"{ld.removed_area_um2:.4f} | {ld.common_polygon_count} |"
        )
    return "\n".join(lines)
