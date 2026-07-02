"""GDSII 统计报告工具（R331，GDSII Statistics Report）。

对 GDSII 文件做一站式统计汇总，提供版图整体概览:
1. 文件信息: 路径、文件大小、dbu
2. cell 统计: cell 总数、顶层 cell、最大层级深度
3. 层统计: 每层 shape 数、总面积（μm²）
4. 几何统计: 总 polygon 数、总面积、总顶点数
5. 顶层 cell bbox

用于版图质量评估、设计规模度量、与商业工具（KLayout Cell Statistics /
Calibre REPORT）对齐。

## KLayout 0.30.9 API 关键事实（实测）

- Layout.read(path): 读取 GDSII
- Layout.dbu: 数据库单位（μm，float）
- Layout.each_top_cell(): 返回 int cell_index 迭代器
- Layout.each_cell(): 返回 Cell 对象迭代器
- Layout.cell(ci): 按 index 取 Cell
- Layout.layer_indices(): 返回所有 layer_index 迭代器
- Layout.get_info(li): 返回 LayerInfo（.layer / .datatype 属性）
- Cell.cell_index(): 返回 int
- Cell.name: cell 名
- Cell.bbox(): 返回 db.Box（dbu 单位）
- Cell.shapes(li) -> Shapes: 该层 shapes 容器
- Shapes.size(): shape 数
- Shapes.each(): 迭代 Shape 对象
- Shape.is_polygon() / Shape.polygon: 判断/获取 Polygon 对象
- Shape.is_box() / Shape.bbox(): 判断/获取 Box
- Polygon.num_points(): 返回顶点数（含 holes）
- Polygon.area(): 面积（dbu²）
- Box.area(): 面积（dbu²）

## 学术依据

- KLayout Layout class:
  https://klayout.org/doc-qt5/code/class_Layout.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Shapes class:
  https://klayout.org/doc-qt5/code/class_Shapes.html
- KLayout SimplePolygon:
  https://www.klayout.org/doc-qt5/code/class_SimplePolygon.html
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Calibre Statistics:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- KLayout Cell Statistics（内置）:
  https://www.klayout.org/doc-qt5/about/cell_views.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "LayerStat",
    "StatisticsReport",
    "generate_gdsii_statistics",
    "generate_statistics_report",
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
            "klayout 未安装，无法执行 GDSII 统计。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class LayerStat:
    """单层统计信息（R331）。

    Attributes:
        layer: GDSII 层号。
        datatype: GDSII datatype。
        shape_count: 该层 shape 总数（所有 cell 累加）。
        area_um2: 该层 polygon+box 总面积（μm²）。
        vertex_count: 该层 polygon 顶点总数（box 计 4 顶点）。
    """

    layer: int
    datatype: int
    shape_count: int = 0
    area_um2: float = 0.0
    vertex_count: int = 0


@dataclass
class StatisticsReport:
    """GDSII 统计报告（R331）。

    Attributes:
        file_path: GDSII 文件路径。
        file_size_bytes: 文件大小（字节）。
        dbu: 数据库单位（μm）。
        total_cells: cell 总数。
        top_cell_names: 顶层 cell 名列表（排序）。
        max_hierarchy_depth: 最大层级深度（顶层=0）。
        layer_stats: 各层统计 LayerStat 列表（按 layer/datatype 排序）。
        total_polygons: 总 polygon 数（所有层所有 cell）。
        total_boxes: 总 box 数。
        total_area_um2: 总面积（μm²，所有层所有 cell）。
        total_vertex_count: 总顶点数。
        top_cell_bbox_um: 顶层 cell bbox (xmin, ymin, xmax, ymax) μm
            （单顶层 cell 时有效，多顶层为 (0,0,0,0)）。
    """

    file_path: str = ""
    file_size_bytes: int = 0
    dbu: float = 0.0
    total_cells: int = 0
    top_cell_names: list[str] = field(default_factory=list)
    max_hierarchy_depth: int = 0
    layer_stats: list[LayerStat] = field(default_factory=list)
    total_polygons: int = 0
    total_boxes: int = 0
    total_area_um2: float = 0.0
    total_vertex_count: int = 0
    top_cell_bbox_um: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0
    )


# =============================================================================
# 统计主入口
# =============================================================================
def generate_gdsii_statistics(
    gds_path: str | Path,
    top_cell_name: str | None = None,
) -> StatisticsReport:
    """生成 GDSII 文件统计报告（R331）。

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 指定顶层 cell 名（None 自动检测）。
            指定后 top_cell_bbox_um 为该 cell 的 bbox；
            否则单顶层 cell 时取该 cell bbox，多顶层为 (0,0,0,0)。

    Returns:
        StatisticsReport 统计报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / top_cell_name 不存在 / 无 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Layout.read:
      https://klayout.org/doc-qt5/code/class_Layout.html
    - KLayout Cell.bbox:
      https://www.klayout.org/doc-qt5/code/class_Cell.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    file_size = int(path.stat().st_size)
    ly, dbu, all_cell_indices, top_cell_indices, top_cell_names_list, specified_top_index = (
        _read_and_validate_stats(db, path, gds_path, top_cell_name)
    )
    max_depth = _compute_stats_hierarchy_depth(ly, all_cell_indices, top_cell_indices)
    layer_stats, total_polygons, total_boxes, total_area_um2, total_vertex_count = (
        _collect_layer_stats(ly, all_cell_indices, dbu)
    )
    top_cell_bbox_um = _compute_top_cell_bbox(
        ly, dbu, specified_top_index, top_cell_indices
    )
    logger.info(
        "GDSII 统计: %s (%d bytes, %d cells, %d layers, %d polygons)",
        path, file_size, len(all_cell_indices), len(layer_stats), total_polygons,
    )
    return StatisticsReport(
        file_path=str(gds_path), file_size_bytes=file_size, dbu=dbu,
        total_cells=len(all_cell_indices), top_cell_names=top_cell_names_list,
        max_hierarchy_depth=max_depth, layer_stats=layer_stats,
        total_polygons=total_polygons, total_boxes=total_boxes,
        total_area_um2=total_area_um2, total_vertex_count=total_vertex_count,
        top_cell_bbox_um=top_cell_bbox_um,
    )


def _read_and_validate_stats(db, path, gds_path, top_cell_name) -> tuple:
    """读取 GDSII 并收集 cell 索引（R331 内部辅助）。

    Returns:
        (ly, dbu, all_cell_indices, top_cell_indices, top_cell_names_list, specified_top_index)。

    Raises:
        RuntimeError: 读取失败。ValueError: 无 cell / top_cell_name 不存在。
    """
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    all_cell_indices: list[int] = [int(ci) for ci in ly.each_cell_top_down()]
    if not all_cell_indices:
        raise ValueError(f"GDSII 文件 {gds_path} 无任何 cell，文件可能为空或损坏")
    top_cell_indices: set[int] = set(int(ci) for ci in ly.each_top_cell())
    top_cell_names_list = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
    specified_top_index: int | None = None
    if top_cell_name is not None:
        top_cell_obj = ly.cell(top_cell_name)
        if top_cell_obj is None:
            available = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。可用顶层 cells: {available}"
            )
        specified_top_index = int(top_cell_obj.cell_index())
    return ly, dbu, all_cell_indices, top_cell_indices, top_cell_names_list, specified_top_index


def _compute_stats_hierarchy_depth(ly, all_cell_indices, top_cell_indices) -> int:
    """计算层级深度（R331 内部辅助，复用 R322 拓扑深度算法）。

    Returns:
        max_depth。
    """
    parent_cells_of: dict[int, set[int]] = {ci: set() for ci in all_cell_indices}
    for ci in all_cell_indices:
        cell = ly.cell(ci)
        for child_ci in cell.each_child_cell():
            parent_cells_of[int(child_ci)].add(ci)
    depth_of: dict[int, int] = {ci: 0 for ci in all_cell_indices}
    for ci in all_cell_indices:
        if ci not in top_cell_indices:
            parent_depths = [depth_of[p] for p in parent_cells_of[ci] if p in depth_of]
            depth_of[ci] = (max(parent_depths) + 1) if parent_depths else 0
    return max(depth_of.values()) if depth_of else 0


def _collect_layer_stats(ly, all_cell_indices, dbu) -> tuple:
    """遍历所有 cell 的所有层收集统计（R331 内部辅助）。

    Returns:
        (layer_stats, total_polygons, total_boxes, total_area_um2, total_vertex_count)。
    """
    layer_stat_map: dict[tuple[int, int], LayerStat] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        key = (int(info.layer), int(info.datatype))
        layer_stat_map[key] = LayerStat(layer=key[0], datatype=key[1])
    total_polygons = total_boxes = total_vertex_count = 0
    total_area_um2 = 0.0
    for ci in all_cell_indices:
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            stat = layer_stat_map[key]
            for shape in cell.shapes(li).each():
                stat.shape_count += 1
                if shape.is_polygon():
                    total_polygons += 1
                    poly = shape.polygon
                    area_um2 = float(poly.area()) * dbu * dbu
                    stat.area_um2 += area_um2
                    total_area_um2 += area_um2
                    n_pts = int(poly.num_points())
                    stat.vertex_count += n_pts
                    total_vertex_count += n_pts
                elif shape.is_box():
                    total_boxes += 1
                    stat.vertex_count += 4
                    area_um2 = float(shape.bbox().area()) * dbu * dbu
                    stat.area_um2 += area_um2
                    total_area_um2 += area_um2
                    total_vertex_count += 4
    layer_stats = sorted(layer_stat_map.values(), key=lambda s: (s.layer, s.datatype))
    return layer_stats, total_polygons, total_boxes, total_area_um2, total_vertex_count


def _compute_top_cell_bbox(ly, dbu, specified_top_index, top_cell_indices) -> tuple[float, float, float, float]:
    """计算顶层 cell 的 bbox（R331 内部辅助）。

    指定 top_cell_name 时取该 cell bbox；单顶层时取其 bbox；多顶层为 (0,0,0,0)。
    """
    if specified_top_index is not None:
        bbox = ly.cell(specified_top_index).bbox()
    elif len(top_cell_indices) == 1:
        bbox = ly.cell(next(iter(top_cell_indices))).bbox()
    else:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        float(bbox.left) * dbu, float(bbox.bottom) * dbu,
        float(bbox.right) * dbu, float(bbox.top) * dbu,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_statistics_report(
    gds_path: str | Path,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 统计报告字符串（R331）。

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 指定顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式。
        FileNotFoundError: 文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = generate_gdsii_statistics(gds_path, top_cell_name=top_cell_name)
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
def _render_text_report(report: StatisticsReport) -> str:
    """渲染纯文本报告（R331 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 统计报告")
    lines.append("=" * 60)
    lines.append(f"文件路径: {report.file_path}")
    lines.append(f"文件大小: {report.file_size_bytes} bytes")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append("")
    lines.append("-" * 60)
    lines.append("Cell 统计")
    lines.append("-" * 60)
    lines.append(f"cell 总数: {report.total_cells}")
    lines.append(f"顶层 cell: {report.top_cell_names}")
    lines.append(f"最大层级深度: {report.max_hierarchy_depth}")
    if report.top_cell_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.top_cell_bbox_um
        lines.append(
            f"顶层 cell bbox: ({l:.4f}, {b:.4f}) - ({r:.4f}, {t:.4f}) μm"
        )
    lines.append("")
    lines.append("-" * 60)
    lines.append("几何统计")
    lines.append("-" * 60)
    lines.append(f"总 polygon 数: {report.total_polygons}")
    lines.append(f"总 box 数: {report.total_boxes}")
    lines.append(f"总面积: {report.total_area_um2:.6f} μm²")
    lines.append(f"总顶点数: {report.total_vertex_count}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("层统计")
    lines.append("-" * 60)
    lines.append(
        f"{'层':>12} {'datatype':>10} {'shapes':>8} "
        f"{'面积(μm²)':>14} {'顶点':>8}"
    )
    for stat in report.layer_stats:
        lines.append(
            f"({stat.layer:>3},{stat.datatype:>3}) "
            f"{stat.shape_count:>8} {stat.area_um2:>14.6f} "
            f"{stat.vertex_count:>8}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: StatisticsReport) -> str:
    """渲染 Markdown 报告（R331 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 统计报告")
    lines.append("")
    lines.append("## 文件信息")
    lines.append("")
    lines.append(f"- **路径**: `{report.file_path}`")
    lines.append(f"- **大小**: {report.file_size_bytes} bytes")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append("")
    lines.append("## Cell 统计")
    lines.append("")
    lines.append(f"- **cell 总数**: {report.total_cells}")
    lines.append(f"- **顶层 cell**: {report.top_cell_names}")
    lines.append(f"- **最大层级深度**: {report.max_hierarchy_depth}")
    if report.top_cell_bbox_um != (0.0, 0.0, 0.0, 0.0):
        l, b, r, t = report.top_cell_bbox_um
        lines.append(
            f"- **顶层 cell bbox**: ({l:.4f}, {b:.4f}) - "
            f"({r:.4f}, {t:.4f}) μm"
        )
    lines.append("")
    lines.append("## 几何统计")
    lines.append("")
    lines.append(f"- **总 polygon 数**: {report.total_polygons}")
    lines.append(f"- **总 box 数**: {report.total_boxes}")
    lines.append(f"- **总面积**: {report.total_area_um2:.6f} μm²")
    lines.append(f"- **总顶点数**: {report.total_vertex_count}")
    lines.append("")
    lines.append("## 层统计")
    lines.append("")
    lines.append(
        "| 层 (layer,datatype) | shapes | 面积 (μm²) | 顶点 |"
    )
    lines.append("| --- | ---: | ---: | ---: |")
    for stat in report.layer_stats:
        lines.append(
            f"| ({stat.layer},{stat.datatype}) | {stat.shape_count} | "
            f"{stat.area_um2:.6f} | {stat.vertex_count} |"
        )
    return "\n".join(lines)


def _render_json_report(report: StatisticsReport) -> str:
    """渲染 JSON 报告（R331 内部函数）。"""
    data = {
        "file_path": report.file_path,
        "file_size_bytes": report.file_size_bytes,
        "dbu": report.dbu,
        "total_cells": report.total_cells,
        "top_cell_names": report.top_cell_names,
        "max_hierarchy_depth": report.max_hierarchy_depth,
        "total_polygons": report.total_polygons,
        "total_boxes": report.total_boxes,
        "total_area_um2": report.total_area_um2,
        "total_vertex_count": report.total_vertex_count,
        "top_cell_bbox_um": list(report.top_cell_bbox_um),
        "layer_stats": [
            {
                "layer": s.layer,
                "datatype": s.datatype,
                "shape_count": s.shape_count,
                "area_um2": s.area_um2,
                "vertex_count": s.vertex_count,
            }
            for s in report.layer_stats
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
