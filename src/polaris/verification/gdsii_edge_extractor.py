"""GDSII 边缘提取工具（R342，Edge Extractor）。

从 GDSII 指定层提取多边形边缘（Edges），支持按长度/方向过滤，
用于 DRC width/space 检查基础、掩膜检查、布局分析等场景。

## 核心概念

- **边缘（Edge）**: 多边形边界上的一条线段，由两个端点 (x1,y1)→(x2,y2) 定义
- **边缘提取**: 把多边形的边界分解为边的集合
- **典型用途**:
  - DRC 基础: width/space/enclosing 检查都基于边
  - 布局分析: 统计边的长度分布、方向分布
  - 掩膜检查: 提取关键边（如最短边、对角边）
  - 调试: 查看多边形边界是否正确

## 边的方向分类

- **水平 (H)**: y1 == y2（边平行于 X 轴）
- **垂直 (V)**: x1 == x2（边平行于 Y 轴）
- **对角 (D)**: 其他（非正交边，常见于斜切、圆形近似）

## KLayout 0.30.9 API 关键事实（R342 冒烟测试实测）

- `db.Edges(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Edges
- `db.Region(...).edges()`: 从 Region 提取 Edges（与 db.Edges 等价）
- `edges.count()`: 返回边数（int，dbu 单位无关）
- `edges.length()`: 返回所有边总长度（int，dbu 单位）
- `edges.each()`: 返回 Edge 迭代器
- `edge.p1` / `edge.p2`: 边的两个端点（Point，dbu 单位）
- `edge.length()`: 单条边长度（int，dbu 单位）
- `edges.with_length(min, max, inverse)`: 范围过滤（3 参数，inverse=False 保留范围内）
- `edges.with_length(length, inverse)`: 单值过滤（2 参数，inverse=False 保留等于 length）
- **注意**: with_length 传 2 个 int 会被当作 (length, inverse)，不是 (min, max)

## 算法

1. 读取 GDSII
2. 用 db.Edges(top_cell.begin_shapes_rec(li)) 提取该层所有边（递归遍历子 cell）
3. 迭代 edges.each()，对每条边:
   - 计算 length_um = edge.length() * dbu
   - 计算 orientation: H / V / D
4. 按过滤参数（min_length_um, max_length_um, orientation_filter）过滤
5. 统计: 总边数、总长度、min/max/avg、方向分布、长度直方图
6. 可选: 将过滤后的边作为细矩形（width=1dbu）插入 layer_result，写出 GDSII

## 学术依据

- KLayout Edges class:
  https://www.klayout.org/doc-qt5/code/class_Edges.html
- KLayout Edge class:
  https://www.klayout.org/doc-qt5/code/class_Edge.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- KLayout Geometry API:
  https://www.klayout.de/doc-qt5/programming/geometry_api.html
- KLayout DRC Reference (edges):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html#h2-905
- KLayout Region.edges():
  https://www.klayout.org/klayout-pypi/overview/geometry/regions/
- Calibre DRC Edge-based operations:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- GDSII 边界表示:
  https://en.wikipedia.org/wiki/GDS_File

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "EdgeInfo",
    "EdgeExtractionReport",
    "extract_edges",
    "generate_edge_report",
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
            "klayout 未安装，无法执行 GDSII 边缘提取。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class EdgeInfo:
    """单条边信息（R342）。

    Attributes:
        x1_um: 起点 X 坐标（μm）。
        y1_um: 起点 Y 坐标（μm）。
        x2_um: 终点 X 坐标（μm）。
        y2_um: 终点 Y 坐标（μm）。
        length_um: 边长度（μm）。
        orientation: 方向分类 'H'（水平）/ 'V'（垂直）/ 'D'（对角）。
    """

    x1_um: float
    y1_um: float
    x2_um: float
    y2_um: float
    length_um: float
    orientation: str


@dataclass
class EdgeExtractionReport:
    """GDSII 边缘提取报告（R342）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径（空字符串表示未写出）。
        layer: 提取层 (layer, datatype)。
        layer_result: 输出层 (layer, datatype)，空元组表示未输出到层。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_length_um: 长度下限（μm），0 表示无下限。
        max_length_um: 长度上限（μm），0 表示无上限。
        orientation_filter: 方向过滤 ''（无）/ 'H' / 'V' / 'D'。
        total_edges_before: 过滤前总边数。
        total_edges_after: 过滤后总边数。
        total_length_um: 过滤后边总长度（μm）。
        min_edge_length_um: 过滤后最短边长（μm），无边为 0.0。
        max_edge_length_um: 过滤后最长边长（μm），无边为 0.0。
        avg_edge_length_um: 过滤后平均边长（μm），无边为 0.0。
        horizontal_count: 过滤后水平边数。
        vertical_count: 过滤后垂直边数。
        diagonal_count: 过滤后对角边数。
        length_histogram: 长度直方图 {区间名: 边数}。
        sample_edges: 边样本列表（最多 100 条，用于检查）。
    """

    input_path: str = ""
    output_path: str = ""
    layer: tuple[int, int] = (0, 0)
    layer_result: tuple[int, int] = ()
    dbu: float = 0.0
    top_cell_name: str = ""
    min_length_um: float = 0.0
    max_length_um: float = 0.0
    orientation_filter: str = ""
    total_edges_before: int = 0
    total_edges_after: int = 0
    total_length_um: float = 0.0
    min_edge_length_um: float = 0.0
    max_edge_length_um: float = 0.0
    avg_edge_length_um: float = 0.0
    horizontal_count: int = 0
    vertical_count: int = 0
    diagonal_count: int = 0
    length_histogram: dict[str, int] = field(default_factory=dict)
    sample_edges: list[EdgeInfo] = field(default_factory=list)


# =============================================================================
# 边缘提取主入口
# =============================================================================
def extract_edges(
    gds_path: str | Path,
    layer: tuple[int, int],
    output_path: str | Path | None = None,
    layer_result: tuple[int, int] | None = None,
    min_length_um: float = 0.0,
    max_length_um: float = 0.0,
    orientation_filter: str = "",
    top_cell_name: str | None = None,
    max_samples: int = 100,
) -> EdgeExtractionReport:
    """从 GDSII 指定层提取边缘（R342，Extract Method 拆分）。

    用 KLayout `db.Edges(top_cell.begin_shapes_rec(li))` 递归提取该层所有边，
    按长度和方向过滤，生成统计报告，可选输出到新层。本函数为编排入口，
    具体逻辑拆分到 `_validate_extract_edges_params`/`_read_gdsii_layout`/
    `_filter_edges_by_criteria`/`_compute_edge_statistics`/`_write_edges_to_layer`。

    Args:
        gds_path: 输入 GDSII 文件路径。layer: 提取层 (layer, datatype)。
        output_path: 输出 GDSII 文件路径（None 表示不写出，仅生成报告）。
        layer_result: 输出层 (layer, datatype)（None 表示不输出到层）。
            当 output_path 不为 None 时，layer_result 必须提供。
        min_length_um: 长度下限（μm），0 表示无下限。max_length_um: 长度上限（μm），0 表示无上限。
        orientation_filter: 方向过滤 ''（无）/ 'H' / 'V' / 'D'。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_samples: 报告中保留的边样本数（最多 N 条，默认 100）。

    Returns:
        EdgeExtractionReport 边缘提取报告。

    Raises:
        FileNotFoundError: 输入文件不存在。ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。
        ValueError: 文件无效 / 层参数无效 / orientation_filter 无效 /
            output_path 提供但 layer_result 未提供 / top_cell_name 不存在 / 层不存在 / max_samples <= 0。

    来源:
    - KLayout Edges class: https://www.klayout.org/doc-qt5/code/class_Edges.html
    - KLayout Edge class: https://www.klayout.org/doc-qt5/code/class_Edge.html
    - Martin Fowler《Refactoring》Extract Method 模式
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)
    src_layer, src_dt, out_path_str, tgt_layer, orient_norm = (
        _validate_extract_edges_params(
            gds_path, in_path, layer, output_path, layer_result,
            min_length_um, max_length_um, orientation_filter, max_samples,
        )
    )
    ly, dbu, top_cell, li_src = _read_gdsii_layout(
        db, in_path, gds_path, top_cell_name, src_layer, src_dt
    )
    edges = db.Edges(top_cell.begin_shapes_rec(li_src))
    total_edges_before = int(edges.count())
    edge_infos = _filter_edges_by_criteria(
        edges, dbu, min_length_um, max_length_um, orient_norm
    )
    stats = _compute_edge_statistics(edge_infos, max_samples)
    if output_path is not None and layer_result is not None:
        _write_edges_to_layer(ly, top_cell, tgt_layer, edge_infos, dbu, output_path)
    logger.info(
        "GDSII 边缘提取: %s (%d,%d), edges_before=%d, edges_after=%d, "
        "total_len=%.6fμm, H=%d, V=%d, D=%d",
        in_path, src_layer, src_dt, total_edges_before, stats["total_after"],
        stats["total_len"], stats["h"], stats["v"], stats["d"],
    )
    return EdgeExtractionReport(
        input_path=str(gds_path), output_path=out_path_str,
        layer=(src_layer, src_dt), layer_result=tgt_layer, dbu=dbu,
        top_cell_name=str(top_cell.name),
        min_length_um=min_length_um, max_length_um=max_length_um,
        orientation_filter=orient_norm, total_edges_before=total_edges_before,
        total_edges_after=stats["total_after"], total_length_um=stats["total_len"],
        min_edge_length_um=stats["min_len"], max_edge_length_um=stats["max_len"],
        avg_edge_length_um=stats["avg_len"], horizontal_count=stats["h"],
        vertical_count=stats["v"], diagonal_count=stats["d"],
        length_histogram=stats["histogram"], sample_edges=stats["sample"],
    )


def _validate_extract_edges_params(
    gds_path, in_path, layer, output_path, layer_result,
    min_length_um, max_length_um, orientation_filter, max_samples,
) -> tuple[int, int, str, tuple[int, int], str]:
    """校验 extract_edges 入参（R342 内部辅助，R03 禁止 fall-back）。

    Returns:
        (src_layer, src_dt, out_path_str, tgt_layer, orientation_filter_norm)。

    Raises:
        FileNotFoundError / ValueError: 见 extract_edges 文档。
    """
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    src_layer, src_dt = _validate_layer(layer, "layer")
    out_path_str = ""
    tgt_layer: tuple[int, int] = ()
    if output_path is not None:
        if layer_result is None:
            raise ValueError(
                "output_path 提供时 layer_result 必须提供。"
                f"禁止 fall-back（R03）。"
            )
        tgt_layer = _validate_layer(layer_result, "layer_result")
        if (src_layer, src_dt) == tgt_layer:
            raise ValueError(
                f"layer 和 layer_result 不能相同: {(src_layer, src_dt)}。"
                f"禁止 fall-back（R03）。"
            )
        out_path_str = str(output_path)
    if min_length_um < 0:
        raise ValueError(
            f"min_length_um 不能为负: {min_length_um}。禁止 fall-back（R03）。"
        )
    if max_length_um < 0:
        raise ValueError(
            f"max_length_um 不能为负: {max_length_um}。禁止 fall-back（R03）。"
        )
    if max_length_um > 0 and min_length_um > max_length_um:
        raise ValueError(
            f"min_length_um ({min_length_um}) 不能大于 max_length_um ({max_length_um})。"
            f"禁止 fall-back（R03）。"
        )
    orient_norm = orientation_filter.upper() if orientation_filter else ""
    if orient_norm not in ("", "H", "V", "D"):
        raise ValueError(
            f"orientation_filter 必须是 ''/'H'/'V'/'D'，得到: {orientation_filter!r}。"
            f"禁止 fall-back（R03）。"
        )
    if not isinstance(max_samples, int) or max_samples <= 0:
        raise ValueError(
            f"max_samples 必须是正整数，得到: {max_samples}。禁止 fall-back（R03）。"
        )
    return src_layer, src_dt, out_path_str, tgt_layer, orient_norm


def _read_gdsii_layout(db, in_path, gds_path, top_cell_name, src_layer, src_dt):
    """读取 GDSII 并定位 top_cell 与源层（R342 内部辅助）。

    Returns:
        (ly, dbu, top_cell, li_src)。

    Raises:
        RuntimeError: klayout 读取失败。
        ValueError: top_cell_name 不存在 / 层不存在。
    """
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
    li_src = _find_or_raise_layer(ly, src_layer, src_dt, gds_path, "layer")
    return ly, dbu, top_cell, li_src


def _filter_edges_by_criteria(
    edges, dbu: float, min_length_um: float, max_length_um: float, orient_norm: str
) -> list[EdgeInfo]:
    """迭代边并按长度/方向过滤（R342 内部辅助）。

    Returns:
        过滤后的 EdgeInfo 列表。
    """
    edge_infos: list[EdgeInfo] = []
    for edge in edges.each():
        p1, p2 = edge.p1, edge.p2
        x1_dbu, y1_dbu = int(p1.x), int(p1.y)
        x2_dbu, y2_dbu = int(p2.x), int(p2.y)
        length_um = int(edge.length()) * dbu
        orientation = _classify_orientation(x1_dbu, y1_dbu, x2_dbu, y2_dbu)
        if min_length_um > 0 and length_um < min_length_um:
            continue
        if max_length_um > 0 and length_um > max_length_um:
            continue
        if orient_norm and orientation != orient_norm:
            continue
        edge_infos.append(EdgeInfo(
            x1_um=x1_dbu * dbu, y1_um=y1_dbu * dbu,
            x2_um=x2_dbu * dbu, y2_um=y2_dbu * dbu,
            length_um=length_um, orientation=orientation,
        ))
    return edge_infos


def _compute_edge_statistics(
    edge_infos: list[EdgeInfo], max_samples: int
) -> dict:
    """计算边统计量（R342 内部辅助）。

    Returns:
        含 total_after/total_len/min_len/max_len/avg_len/h/v/d/histogram/sample 的 dict。
    """
    total_after = len(edge_infos)
    if total_after > 0:
        lengths = [e.length_um for e in edge_infos]
        total_len = sum(lengths)
        min_len = min(lengths)
        max_len = max(lengths)
        avg_len = total_len / total_after
        h = sum(1 for e in edge_infos if e.orientation == "H")
        v = sum(1 for e in edge_infos if e.orientation == "V")
        d = sum(1 for e in edge_infos if e.orientation == "D")
    else:
        total_len = min_len = max_len = avg_len = 0.0
        h = v = d = 0
    return {
        "total_after": total_after,
        "total_len": total_len,
        "min_len": min_len,
        "max_len": max_len,
        "avg_len": avg_len,
        "h": h, "v": v, "d": d,
        "histogram": _build_length_histogram(edge_infos),
        "sample": edge_infos[:max_samples],
    }


def _write_edges_to_layer(ly, top_cell, tgt_layer, edge_infos, dbu, output_path) -> None:
    """将过滤后的边作为细矩形写入新层并写出 GDSII（R342 内部辅助）。

    GDSII 不支持 Edge，需转换为 polygon（细矩形 width=1 dbu）。

    Raises:
        RuntimeError: klayout 写出失败。
    """
    li_tgt = ly.layer(tgt_layer[0], tgt_layer[1])
    for e in edge_infos:
        x1_dbu = int(round(e.x1_um / dbu))
        y1_dbu = int(round(e.y1_um / dbu))
        x2_dbu = int(round(e.x2_um / dbu))
        y2_dbu = int(round(e.y2_um / dbu))
        box = _edge_to_box(x1_dbu, y1_dbu, x2_dbu, y2_dbu, width_dbu=1)
        top_cell.shapes(li_tgt).insert(box)
    try:
        ly.write(str(Path(output_path)))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e


# =============================================================================
# 报告生成
# =============================================================================
def generate_edge_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    output_path: str | Path | None = None,
    layer_result: tuple[int, int] | None = None,
    min_length_um: float = 0.0,
    max_length_um: float = 0.0,
    orientation_filter: str = "",
    top_cell_name: str | None = None,
    max_samples: int = 100,
    output_format: str = "text",
) -> str:
    """提取 GDSII 边缘并生成报告字符串（R342）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 提取层 (layer, datatype)。
        output_path: 输出 GDSII 文件路径（None 表示不写出）。
        layer_result: 输出层 (layer, datatype)（None 表示不输出到层）。
        min_length_um: 长度下限（μm），0 表示无下限。
        max_length_um: 长度上限（μm），0 表示无上限。
        orientation_filter: 方向过滤 ''（无）/ 'H' / 'V' / 'D'。
        top_cell_name: 指定顶层 cell 名。
        max_samples: 报告中保留的边样本数。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = extract_edges(
        gds_path, layer, output_path, layer_result,
        min_length_um, max_length_um, orientation_filter,
        top_cell_name, max_samples,
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
def _validate_layer(layer: tuple[int, int], context: str) -> tuple[int, int]:
    """验证层参数（R342 内部函数）。"""
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
    return g, d


def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R342 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = sorted(ly.cell(int(ci)).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}。"
                f"禁止 fall-back（R03）。"
            )
        return top_cell

    top_cells = [ly.cell(int(ci)) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空。"
            f"禁止 fall-back（R03）。"
        )
    return top_cells[0]


def _find_or_raise_layer(
    ly, layer: int, datatype: int, gds_path, context: str
) -> int:
    """查找层，不存在则 raise（R342 内部函数）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return int(li)
    raise ValueError(
        f"{context} ({layer}, {datatype}) 在文件 {gds_path} 中不存在。"
        f"禁止 fall-back（R03）。"
    )


def _classify_orientation(x1: int, y1: int, x2: int, y2: int) -> str:
    """分类边的方向（R342 内部函数）。

    Args:
        x1, y1, x2, y2: 边的两个端点（dbu）。

    Returns:
        'H'（水平，y1==y2）/ 'V'（垂直，x1==x2）/ 'D'（对角）。
    """
    if y1 == y2:
        return "H"
    if x1 == x2:
        return "V"
    return "D"


def _build_length_histogram(edge_infos: list[EdgeInfo]) -> dict[str, int]:
    """构建长度直方图（R342 内部函数）。

    区间:
    - "0-0.1μm": [0, 0.1)
    - "0.1-1μm": [0.1, 1)
    - "1-10μm": [1, 10)
    - "10-100μm": [10, 100)
    - "100μm+": [100, ∞)
    """
    bins = {
        "0-0.1μm": 0,
        "0.1-1μm": 0,
        "1-10μm": 0,
        "10-100μm": 0,
        "100μm+": 0,
    }
    for e in edge_infos:
        length = e.length_um
        if length < 0.1:
            bins["0-0.1μm"] += 1
        elif length < 1.0:
            bins["0.1-1μm"] += 1
        elif length < 10.0:
            bins["1-10μm"] += 1
        elif length < 100.0:
            bins["10-100μm"] += 1
        else:
            bins["100μm+"] += 1
    return bins


def _edge_to_box(
    x1: int, y1: int, x2: int, y2: int, width_dbu: int = 1
):
    """把边转换为细矩形 Box（R342 内部函数）。

    GDSII 不支持 Edge，需要把边转换为 polygon 才能写出。
    本函数把边转换为 width_dbu 宽的矩形（包围边的最小轴对齐矩形）。

    对于水平/垂直边，矩形是明确的。
    对于对角边，矩形是边的轴对齐包围盒（不是真正的斜线）。
    这是简化的可视化方案，足够用于调试。

    Args:
        x1, y1, x2, y2: 边端点（dbu）。
        width_dbu: 矩形宽度（dbu），默认 1。

    Returns:
        db.Box 对象。
    """
    db = _import_klayout_db()
    xmin = min(x1, x2)
    xmax = max(x1, x2)
    ymin = min(y1, y2)
    ymax = max(y1, y2)
    # 确保至少 width_dbu 宽
    if xmax == xmin:
        xmax += width_dbu
    if ymax == ymin:
        ymax += width_dbu
    return db.Box(xmin, ymin, xmax, ymax)


def _render_text_report(report: EdgeExtractionReport) -> str:
    """渲染纯文本报告（R342 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 边缘提取报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    if report.output_path:
        lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(
        f"layer: ({report.layer[0]},{report.layer[1]})"
    )
    if report.layer_result:
        lines.append(
            f"layer_result: ({report.layer_result[0]},{report.layer_result[1]})"
        )
    lines.append("")
    lines.append("-" * 60)
    lines.append("过滤参数")
    lines.append("-" * 60)
    min_str = f"{report.min_length_um:.6f} μm" if report.min_length_um > 0 else "无"
    max_str = f"{report.max_length_um:.6f} μm" if report.max_length_um > 0 else "无"
    orient_str = report.orientation_filter or "无"
    lines.append(f"  min_length: {min_str}")
    lines.append(f"  max_length: {max_str}")
    lines.append(f"  orientation: {orient_str}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("统计")
    lines.append("-" * 60)
    lines.append(
        f"  过滤前边数: {report.total_edges_before}"
    )
    lines.append(
        f"  过滤后边数: {report.total_edges_after}"
    )
    lines.append(
        f"  总长度: {report.total_length_um:.6f} μm"
    )
    if report.total_edges_after > 0:
        lines.append(
            f"  最短边: {report.min_edge_length_um:.6f} μm"
        )
        lines.append(
            f"  最长边: {report.max_edge_length_um:.6f} μm"
        )
        lines.append(
            f"  平均边长: {report.avg_edge_length_um:.6f} μm"
        )
    lines.append("")
    lines.append("  方向分布:")
    lines.append(f"    水平 (H): {report.horizontal_count}")
    lines.append(f"    垂直 (V): {report.vertical_count}")
    lines.append(f"    对角 (D): {report.diagonal_count}")
    lines.append("")
    lines.append("  长度直方图:")
    for bin_name, count in report.length_histogram.items():
        lines.append(f"    {bin_name}: {count}")
    if report.sample_edges:
        lines.append("")
        lines.append(f"  样本边（前 {len(report.sample_edges)} 条）:")
        for i, e in enumerate(report.sample_edges[:10]):
            lines.append(
                f"    [{i}] ({e.x1_um:.4f},{e.y1_um:.4f}) → "
                f"({e.x2_um:.4f},{e.y2_um:.4f}) "
                f"len={e.length_um:.4f}μm {e.orientation}"
            )
        if len(report.sample_edges) > 10:
            lines.append(f"    ... 共 {len(report.sample_edges)} 条")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: EdgeExtractionReport) -> str:
    """渲染 Markdown 报告（R342 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 边缘提取报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    if report.output_path:
        lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **layer**: ({report.layer[0]},{report.layer[1]})")
    if report.layer_result:
        lines.append(
            f"- **layer_result**: ({report.layer_result[0]},{report.layer_result[1]})"
        )
    lines.append("")
    lines.append("## 过滤参数")
    lines.append("")
    min_str = f"{report.min_length_um:.6f} μm" if report.min_length_um > 0 else "无"
    max_str = f"{report.max_length_um:.6f} μm" if report.max_length_um > 0 else "无"
    orient_str = report.orientation_filter or "无"
    lines.append(f"- **min_length**: {min_str}")
    lines.append(f"- **max_length**: {max_str}")
    lines.append(f"- **orientation**: {orient_str}")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 过滤前边数 | {report.total_edges_before} |")
    lines.append(f"| 过滤后边数 | {report.total_edges_after} |")
    lines.append(f"| 总长度 (μm) | {report.total_length_um:.6f} |")
    if report.total_edges_after > 0:
        lines.append(f"| 最短边 (μm) | {report.min_edge_length_um:.6f} |")
        lines.append(f"| 最长边 (μm) | {report.max_edge_length_um:.6f} |")
        lines.append(f"| 平均边长 (μm) | {report.avg_edge_length_um:.6f} |")
    lines.append(f"| 水平边 (H) | {report.horizontal_count} |")
    lines.append(f"| 垂直边 (V) | {report.vertical_count} |")
    lines.append(f"| 对角边 (D) | {report.diagonal_count} |")
    lines.append("")
    lines.append("## 长度直方图")
    lines.append("")
    lines.append("| 区间 | 边数 |")
    lines.append("|------|------|")
    for bin_name, count in report.length_histogram.items():
        lines.append(f"| {bin_name} | {count} |")
    if report.sample_edges:
        lines.append("")
        lines.append(f"## 样本边（前 {len(report.sample_edges)} 条）")
        lines.append("")
        lines.append("| # | x1 (μm) | y1 (μm) | x2 (μm) | y2 (μm) | 长度 (μm) | 方向 |")
        lines.append("|---|---------|---------|---------|---------|-----------|------|")
        for i, e in enumerate(report.sample_edges[:20]):
            lines.append(
                f"| {i} | {e.x1_um:.4f} | {e.y1_um:.4f} | "
                f"{e.x2_um:.4f} | {e.y2_um:.4f} | "
                f"{e.length_um:.4f} | {e.orientation} |"
            )
        if len(report.sample_edges) > 20:
            lines.append(f"\n*共 {len(report.sample_edges)} 条样本*")
    return "\n".join(lines)


def _render_json_report(report: EdgeExtractionReport) -> str:
    """渲染 JSON 报告（R342 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "layer": list(report.layer),
        "layer_result": list(report.layer_result) if report.layer_result else [],
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "min_length_um": report.min_length_um,
        "max_length_um": report.max_length_um,
        "orientation_filter": report.orientation_filter,
        "total_edges_before": report.total_edges_before,
        "total_edges_after": report.total_edges_after,
        "total_length_um": report.total_length_um,
        "min_edge_length_um": report.min_edge_length_um,
        "max_edge_length_um": report.max_edge_length_um,
        "avg_edge_length_um": report.avg_edge_length_um,
        "horizontal_count": report.horizontal_count,
        "vertical_count": report.vertical_count,
        "diagonal_count": report.diagonal_count,
        "length_histogram": report.length_histogram,
        "sample_edges": [
            {
                "x1_um": e.x1_um,
                "y1_um": e.y1_um,
                "x2_um": e.x2_um,
                "y2_um": e.y2_um,
                "length_um": e.length_um,
                "orientation": e.orientation,
            }
            for e in report.sample_edges
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
