"""GDSII 层结构可视化工具（R318，ASCII art + 统计）。

提供 GDSII 文件层结构的可视化与统计：
1. 层统计: 各层多边形数/总面积/包围盒
2. 层结构 ASCII 可视化: 用字符矩阵展示各层分布
3. 层叠加可视化: 多层叠加的 ASCII art
4. 层摘要报告: text/markdown 格式

R318 实现:
- LayerStats: 单层统计数据类
- GDSIISummary: GDSII 文件层结构摘要
- compute_layer_stats(gds_path, layer_map) -> list[LayerStats]: 计算各层统计
- visualize_layers_ascii(gds_path, layer_map, width, height) -> str: ASCII 可视化
- generate_summary_report(gds_path, layer_map, format) -> str: 生成摘要报告

R03 合规:
- 文件不存在 raise FileNotFoundError
- 不支持的格式 raise ValueError
- klayout 未安装 raise ImportError

R02 学术诚信:
- KLayout API 用法附官方文档 URL
- ASCII 可视化算法参考字符矩阵渲染

来源:
- KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout Cell.begin_shapes_rec: https://www.klayout.org/doc-qt5/code/class_Cell.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ASCII art 渲染: https://en.wikipedia.org/wiki/ASCII_art
- CommonMark: https://spec.commonmark.org/
- Python pathlib: https://docs.python.org/3/library/pathlib.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "GDSIISummary",
    "LayerStats",
    "compute_layer_stats",
    "generate_summary_report",
    "visualize_layers_ascii",
]


@dataclass
class LayerStats:
    """单层统计数据（R318）。

    Attributes:
        layer_name: 层名（如 'WG'）。
        gds_layer: GDSII 层号。
        gds_datatype: GDSII datatype。
        polygon_count: 多边形数。
        total_area_um2: 总面积（μm²）。
        bbox_xmin: 包围盒 x 最小值（μm）。
        bbox_ymin: 包围盒 y 最小值（μm）。
        bbox_xmax: 包围盒 x 最大值（μm）。
        bbox_ymax: 包围盒 y 最大值（μm）。
    """

    layer_name: str
    gds_layer: int
    gds_datatype: int
    polygon_count: int = 0
    total_area_um2: float = 0.0
    bbox_xmin: float = 0.0
    bbox_ymin: float = 0.0
    bbox_xmax: float = 0.0
    bbox_ymax: float = 0.0


@dataclass
class GDSIISummary:
    """GDSII 文件层结构摘要（R318）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu: 数据库单位（米）。
        layer_stats: 各层统计列表。
        total_polygons: 总多边形数。
        total_area_um2: 总面积（μm²）。
        overall_bbox: 整体包围盒 (xmin, ymin, xmax, ymax)。
    """

    file_path: str
    top_cell_name: str = ""
    dbu: float = 0.0
    layer_stats: list[LayerStats] = field(default_factory=list)
    total_polygons: int = 0
    total_area_um2: float = 0.0
    overall_bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 层结构可视化。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 层统计计算
# =============================================================================
def compute_layer_stats(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> GDSIISummary:
    """计算 GDSII 文件各层统计（R318）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。

    Returns:
        GDSIISummary 摘要。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    - KLayout Region.area: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    path, layer_map = _validate_visualize_params(gds_path, layer_map)
    ly, dbu, top_cell = _read_visualize_layout(db, path, gds_path, top_cell_name)
    layer_stats, total_polygons, total_area, overall_bbox = _aggregate_layer_stats(
        db, ly, top_cell, dbu, layer_map
    )
    return GDSIISummary(
        file_path=str(gds_path),
        top_cell_name=top_cell.name,
        dbu=dbu,
        layer_stats=layer_stats,
        total_polygons=total_polygons,
        total_area_um2=total_area,
        overall_bbox=overall_bbox,
    )


def _aggregate_layer_stats(db, ly, top_cell, dbu, layer_map) -> tuple:
    """遍历所有层计算统计并汇总（R318 内部辅助）。

    Returns:
        (layer_stats, total_polygons, total_area, overall_bbox)。

    来源: KLayout Region.area https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    layer_stats: list[LayerStats] = []
    overall_xmin = float("inf")
    overall_ymin = float("inf")
    overall_xmax = float("-inf")
    overall_ymax = float("-inf")
    total_polygons = 0
    total_area = 0.0
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        layer_name = layer_map.get(
            (gds_layer, gds_datatype),
            f"LAYER_{gds_layer}_{gds_datatype}",
        )
        stats = _compute_single_layer_stats(
            db, top_cell, li, dbu, layer_name, gds_layer, gds_datatype
        )
        if stats is None:
            continue
        layer_stats.append(stats)
        total_polygons += stats.polygon_count
        total_area += stats.total_area_um2
        if stats.bbox_xmin < overall_xmin:
            overall_xmin = stats.bbox_xmin
        if stats.bbox_ymin < overall_ymin:
            overall_ymin = stats.bbox_ymin
        if stats.bbox_xmax > overall_xmax:
            overall_xmax = stats.bbox_xmax
        if stats.bbox_ymax > overall_ymax:
            overall_ymax = stats.bbox_ymax
    if overall_xmin == float("inf"):
        overall_bbox = (0.0, 0.0, 0.0, 0.0)
    else:
        overall_bbox = (overall_xmin, overall_ymin, overall_xmax, overall_ymax)
    return layer_stats, total_polygons, total_area, overall_bbox


def _compute_single_layer_stats(
    db, top_cell, li, dbu, layer_name, gds_layer, gds_datatype,
):
    """计算单层统计（R318 内部辅助）。

    Returns:
        LayerStats 或 None（空层）。
    """
    region = db.Region(top_cell.begin_shapes_rec(li))
    polygon_count = 0
    layer_xmin = float("inf")
    layer_ymin = float("inf")
    layer_xmax = float("-inf")
    layer_ymax = float("-inf")
    layer_area_dbu2 = 0
    for klayout_poly in region.each():
        polygon_count += 1
        simple = klayout_poly.to_simple_polygon()
        pts = list(simple.each_point())
        for p in pts:
            x_um = float(p.x) * dbu
            y_um = float(p.y) * dbu
            if x_um < layer_xmin:
                layer_xmin = x_um
            if y_um < layer_ymin:
                layer_ymin = y_um
            if x_um > layer_xmax:
                layer_xmax = x_um
            if y_um > layer_ymax:
                layer_ymax = y_um
        single_region = db.Region()
        single_region.insert(klayout_poly)
        layer_area_dbu2 += int(single_region.area())
    if polygon_count == 0:
        return None
    layer_area_um2 = layer_area_dbu2 * dbu * dbu
    return LayerStats(
        layer_name=layer_name, gds_layer=gds_layer, gds_datatype=gds_datatype,
        polygon_count=polygon_count, total_area_um2=layer_area_um2,
        bbox_xmin=layer_xmin, bbox_ymin=layer_ymin,
        bbox_xmax=layer_xmax, bbox_ymax=layer_ymax,
    )


# =============================================================================
# ASCII 可视化
# =============================================================================
def visualize_layers_ascii(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    width: int = 60,
    height: int = 20,
    layers_to_show: list[str] | None = None,
) -> str:
    """ASCII 可视化 GDSII 层结构（R318）。

    用字符矩阵展示各层多边形分布。每层用一个独特字符表示：
    - WG: '#'
    - METAL: 'M'
    - HEATER: 'H'
    - SiN: 'N'
    - SLAB150: '1'
    - SLAB90: '9'
    - 其他层: 用层名首字符

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。
        width: ASCII 画布宽度（字符数）。
        height: ASCII 画布高度（字符数）。
        layers_to_show: 要显示的层名列表（None 显示所有层）。

    Returns:
        ASCII art 字符串。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: width/height <= 0 / GDSII 无效。
        ImportError: klayout 未安装。

    来源:
    - ASCII art 渲染: https://en.wikipedia.org/wiki/ASCII_art
    """
    if width <= 0:
        raise ValueError(f"width 必须 > 0，得到 {width}")
    if height <= 0:
        raise ValueError(f"height 必须 > 0，得到 {height}")
    path, layer_map = _validate_visualize_params(gds_path, layer_map)
    db = _import_klayout_db()
    ly, dbu, top_cell = _read_visualize_layout(db, path, gds_path, top_cell_name)
    layer_polygons, all_x, all_y = _collect_viz_layer_polygons(
        db, ly, top_cell, dbu, layer_map, layers_to_show
    )
    if not layer_polygons or not all_x:
        return _render_empty_viz_canvas(width)
    return _render_viz_art(layer_polygons, all_x, all_y, width, height)


def _validate_visualize_params(gds_path, layer_map) -> tuple:
    """校验 visualize_layers_ascii 入参（R318 内部辅助，R03 禁止 fall-back）。

    Returns:
        (path, layer_map)。
    """
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = _get_default_layer_map()
    return path, layer_map


def _read_visualize_layout(db, path, gds_path, top_cell_name) -> tuple:
    """读取 GDSII 并定位顶层 cell（R318 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly, dbu, top_cell)。

    来源: KLayout Layout.read https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
    else:
        top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
        if not top_cells:
            raise ValueError(
                f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
            )
        top_cell = top_cells[0]
    return ly, dbu, top_cell


def _collect_viz_layer_polygons(
    db, ly, top_cell, dbu, layer_map, layers_to_show,
) -> tuple:
    """收集各层多边形顶点并确定整体包围盒（R318 内部辅助）。

    Returns:
        (layer_polygons, all_x, all_y)。
        layer_polygons: {layer_name: list[np.ndarray]}。
        all_x/all_y: 所有顶点的 x/y 坐标列表。

    来源: KLayout Region https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    layer_polygons: dict[str, list[np.ndarray]] = {}
    all_x: list[float] = []
    all_y: list[float] = []
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        layer_name = layer_map.get(
            (gds_layer, gds_datatype),
            f"LAYER_{gds_layer}_{gds_datatype}",
        )
        if layers_to_show is not None and layer_name not in layers_to_show:
            continue
        region = db.Region(top_cell.begin_shapes_rec(li))
        polys: list[np.ndarray] = []
        for klayout_poly in region.each():
            simple = klayout_poly.to_simple_polygon()
            pts = list(simple.each_point())
            coords = [(float(p.x) * dbu, float(p.y) * dbu) for p in pts]
            if len(coords) >= 3:
                poly = np.array(coords, dtype=float)
                polys.append(poly)
                all_x.extend(poly[:, 0].tolist())
                all_y.extend(poly[:, 1].tolist())
        if polys:
            layer_polygons[layer_name] = polys
    return layer_polygons, all_x, all_y


def _render_empty_viz_canvas(width: int) -> str:
    """渲染空画布（无多边形时，R318 内部辅助）。"""
    return " " * width + "\n" + ("无多边形可显示" + " " * max(0, width - 9)) + "\n"


def _render_viz_art(
    layer_polygons: dict[str, list[np.ndarray]],
    all_x: list[float],
    all_y: list[float],
    width: int,
    height: int,
) -> str:
    """渲染 ASCII art 画布并生成输出字符串（R318 内部辅助）。

    包括：包围盒计算、画布初始化、按层填充多边形、坐标轴标签和图例。

    来源: ASCII art 渲染 https://en.wikipedia.org/wiki/ASCII_art
    """
    layer_chars: dict[str, str] = {
        "WG": "#", "METAL": "M", "HEATER": "H", "SiN": "N",
        "SLAB150": "1", "SLAB90": "9", "TEXT": "T", "LABEL": "L",
        "DEVREC": "D", "PIN": "P", "PORT": "O", "FLOORPLAN": "F",
        "PORT_GEOM": "G",
    }
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = x_max - x_min if x_max > x_min else 1.0
    y_range = y_max - y_min if y_max > y_min else 1.0
    canvas: list[list[str]] = [[" "] * width for _ in range(height)]
    for layer_name, polys in layer_polygons.items():
        char = layer_chars.get(layer_name, layer_name[0] if layer_name else "?")
        for poly in polys:
            canvas_pts = _project_poly_to_canvas(poly, x_min, x_max, y_min, y_max,
                                                  x_range, y_range, width, height)
            _fill_polygon(canvas, canvas_pts, char)
    return _build_viz_output_lines(
        canvas, x_min, x_max, y_min, y_max, width, height, layer_polygons, layer_chars
    )


def _project_poly_to_canvas(
    poly, x_min, x_max, y_min, y_max, x_range, y_range, width, height,
) -> list:
    """将多边形顶点映射到画布坐标（R318 内部辅助）。

    y 轴翻转（ASCII 画布 y 向下，GDSII y 向上）。
    """
    canvas_pts: list[tuple[int, int]] = []
    for x, y in poly:
        col = int((x - x_min) / x_range * (width - 1))
        row = int((y_max - y) / y_range * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        canvas_pts.append((row, col))
    return canvas_pts


def _build_viz_output_lines(
    canvas, x_min, x_max, y_min, y_max, width, height,
    layer_polygons, layer_chars,
) -> str:
    """组装 ASCII art 输出字符串（坐标轴标签 + 画布 + 图例，R318 内部辅助）。"""
    lines: list[str] = []
    lines.append(f"x: [{x_min:.2f}, {x_max:.2f}] μm  y: [{y_min:.2f}, {y_max:.2f}] μm")
    lines.append(f"画布: {width}x{height} 字符")
    for row in canvas:
        lines.append("".join(row))
    legend_parts: list[str] = []
    for layer_name in layer_polygons:
        char = layer_chars.get(layer_name, layer_name[0] if layer_name else "?")
        legend_parts.append(f"{char}={layer_name}")
    if legend_parts:
        lines.append("图例: " + " ".join(legend_parts))
    return "\n".join(lines)


def _fill_polygon(
    canvas: list[list[str]],
    pts: list[tuple[int, int]],
    char: str,
) -> None:
    """填充多边形到画布（扫描线算法，R318 内部函数）。

    Args:
        canvas: 画布（height x width 字符矩阵）。
        pts: 多边形顶点 [(row, col), ...]。
        char: 填充字符。

    来源:
    - 扫描线填充算法: https://en.wikipedia.org/wiki/Scanline_fill
    """
    if len(pts) < 3:
        return
    height = len(canvas)
    width = len(canvas[0]) if height > 0 else 0
    if height == 0 or width == 0:
        return
    # 找到多边形的 row 范围
    rows = [p[0] for p in pts]
    min_row = max(0, min(rows))
    max_row = min(height - 1, max(rows))
    # 对每条扫描线，计算与多边形边的交点
    n = len(pts)
    for row in range(min_row, max_row + 1):
        intersections: list[int] = []
        for i in range(n):
            r1, c1 = pts[i]
            r2, c2 = pts[(i + 1) % n]
            # 检查边是否跨越当前扫描线
            if (r1 <= row < r2) or (r2 <= row < r1):
                # 线性插值计算交点 col
                if r2 != r1:
                    t = (row - r1) / (r2 - r1)
                    col = c1 + t * (c2 - c1)
                    intersections.append(int(round(col)))
        if not intersections:
            continue
        intersections.sort()
        # 填充交点对之间的像素
        for i in range(0, len(intersections) - 1, 2):
            c_start = max(0, intersections[i])
            c_end = min(width - 1, intersections[i + 1])
            for col in range(c_start, c_end + 1):
                canvas[row][col] = char


# =============================================================================
# 摘要报告生成
# =============================================================================
def generate_summary_report(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 层结构摘要报告（R318）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: 不支持的格式 / GDSII 无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    summary = compute_layer_stats(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name
    )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_summary(summary)
    if fmt == "markdown":
        return _render_markdown_summary(summary)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown。"
    )


def _render_text_summary(summary: GDSIISummary) -> str:
    """渲染纯文本摘要。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 层结构摘要")
    lines.append("=" * 60)
    lines.append(f"文件: {summary.file_path}")
    lines.append(f"顶层 cell: {summary.top_cell_name}")
    lines.append(f"dbu: {summary.dbu} m")
    lines.append(f"层总数: {len(summary.layer_stats)}")
    lines.append(f"多边形总数: {summary.total_polygons}")
    lines.append(f"总面积: {summary.total_area_um2:.4f} μm²")
    x_min, y_min, x_max, y_max = summary.overall_bbox
    lines.append(
        f"整体包围盒: [{x_min:.2f}, {y_min:.2f}] - "
        f"[{x_max:.2f}, {y_max:.2f}] μm"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("各层详情:")
    lines.append("-" * 60)
    for s in summary.layer_stats:
        lines.append(
            f"  {s.layer_name} (GDS {s.gds_layer}/{s.gds_datatype}):"
        )
        lines.append(f"    多边形数: {s.polygon_count}")
        lines.append(f"    面积: {s.total_area_um2:.4f} μm²")
        lines.append(
            f"    包围盒: [{s.bbox_xmin:.2f}, {s.bbox_ymin:.2f}] - "
            f"[{s.bbox_xmax:.2f}, {s.bbox_ymax:.2f}] μm"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_summary(summary: GDSIISummary) -> str:
    """渲染 Markdown 摘要。"""
    lines: list[str] = []
    lines.append("# GDSII 层结构摘要")
    lines.append("")
    lines.append(f"**文件**: `{summary.file_path}`")
    lines.append(f"**顶层 cell**: {summary.top_cell_name}")
    lines.append(f"**dbu**: {summary.dbu} m")
    lines.append(f"**层总数**: {len(summary.layer_stats)}")
    lines.append(f"**多边形总数**: {summary.total_polygons}")
    lines.append(f"**总面积**: {summary.total_area_um2:.4f} μm²")
    x_min, y_min, x_max, y_max = summary.overall_bbox
    lines.append(
        f"**整体包围盒**: [{x_min:.2f}, {y_min:.2f}] - "
        f"[{x_max:.2f}, {y_max:.2f}] μm"
    )
    lines.append("")
    lines.append("## 各层详情")
    lines.append("")
    lines.append("| 层名 | GDS 层/datatype | 多边形数 | 面积(μm²) | 包围盒 |")
    lines.append("|------|------------------|----------|-----------|--------|")
    for s in summary.layer_stats:
        bbox = (
            f"[{s.bbox_xmin:.1f},{s.bbox_ymin:.1f}]-"
            f"[{s.bbox_xmax:.1f},{s.bbox_ymax:.1f}]"
        )
        lines.append(
            f"| {s.layer_name} | {s.gds_layer}/{s.gds_datatype} | "
            f"{s.polygon_count} | {s.total_area_um2:.4f} | {bbox} |"
        )
    return "\n".join(lines)
