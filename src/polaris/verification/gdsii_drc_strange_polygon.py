"""GDSII DRC strange_polygon 检查工具（R350，DRC Strange Polygon Checker）。

基于 KLayout Region 的 strange_polygon_check API，对 GDSII 指定层执行 DRC
奇异多边形检查，返回违规列表和详细报告。

## 核心概念

- **Strange Polygon 检查（奇异多边形检查）**: 检查多边形是否为奇异多边形
  - 违规: 多边形自相交、退化、孔洞异常、顶点重复等
  - 典型用途: 检测版图错误（自相交多边形可能导致制造失败、DRC 误报）
- **返回类型（R350 冒烟测试实测确认）**:
  - `region.strange_polygon_check()` 返回 **Region**（多边形集合），
    而非 EdgePairs
  - 每个违规是 Region 中的一个 `PolygonWithProperties`（继承自 Polygon）
  - 与 width_check/space_check/notch_check（返回 EdgePairs）不同：
    strange_polygon_check 返回的是"奇异多边形本身"（自相交多边形被分解
    后的子多边形），没有 first/second 边对和 distance 概念
- **Polygon 属性**:
  - `p.bbox()`: 多边形包围盒（Box）
  - `p.area()`: 多边形面积（dbu²）
  - `p.each_point_hull()`: 迭代 hull 顶点（Point）
  - `p.each_edge()`: 迭代边（Edge，有 p1/p2）

## KLayout 0.30.9 API 关键事实（R350 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.strange_polygon_check()`: 检查奇异多边形（**无参数**）
  - 返回 **Region**（多边形集合），不是 EdgePairs
  - 检测: 自相交、退化多边形等
- 实测: 蝴蝶形自相交多边形 (0,0)-(2000,2000)-(2000,0)-(0,2000)
  - strange_polygon_check(): 1 个违规
  - 违规多边形 hull: (0,0)-(0,2000)-(1000,1000)（三角形）
  - bbox: (0,0;1000,2000)
  - area: 1000000 dbu²
- 正常矩形/五边形: 0 个违规
- 多个自相交多边形: 每个自相交多边形一个违规
- `region.count()` / `each()` / `bbox()`: 违规数 / 迭代 / 包围盒

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 执行: region.strange_polygon_check() → 返回 Region
4. 迭代 Region.each()，对每个 PolygonWithProperties 提取:
   - polygon_id（序号）
   - bbox（包围盒）
   - area（面积）
   - hull_points（hull 顶点列表）
5. 生成报告

## 学术依据

- KLayout Region class (strange_polygon_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout Polygon class:
  https://www.klayout.de/doc-qt5/code/class_Polygon.html
- KLayout RegionIterator:
  https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout DRC Reference (strange_polygon):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Strange Polygon Check:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC DRC Rules:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "StrangePolygonDRCViolation",
    "StrangePolygonDRCReport",
    "check_strange_polygon",
    "generate_strange_polygon_drc_report",
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
            "klayout 未安装，无法执行 GDSII strange_polygon 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class StrangePolygonDRCViolation:
    """单个 strange_polygon 违规（R350）。

    表示一个奇异多边形违规。strange_polygon_check() 返回 Region，
    每个违规是 Region 中的一个 Polygon（自相交多边形被分解后的子多边形）。

    Attributes:
        polygon_id: 违规多边形序号（从 0 开始）。
        bbox_xmin_dbu: 多边形包围盒 xmin（dbu）。
        bbox_ymin_dbu: 多边形包围盒 ymin（dbu）。
        bbox_xmax_dbu: 多边形包围盒 xmax（dbu）。
        bbox_ymax_dbu: 多边形包围盒 ymax（dbu）。
        area_dbu2: 多边形面积（dbu²）。
        num_hull_points: hull 顶点数。
        hull_points_dbu: hull 顶点列表 [(x,y),...]（dbu）。
        area_um2: 多边形面积（μm²）。
    """

    polygon_id: int
    bbox_xmin_dbu: int
    bbox_ymin_dbu: int
    bbox_xmax_dbu: int
    bbox_ymax_dbu: int
    area_dbu2: int
    num_hull_points: int
    hull_points_dbu: list[tuple[int, int]]
    area_um2: float


@dataclass
class StrangePolygonDRCReport:
    """GDSII strange_polygon DRC 检查报告（R350）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        check_type: 检查类型（"strange_polygon"）。
        total_violations: 违规总数。
        violations: 违规列表。
        bbox: 所有违规的包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
    """

    input_path: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    check_type: str = "strange_polygon"
    total_violations: int = 0
    violations: list[StrangePolygonDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None


# =============================================================================
# strange_polygon 检查主入口
# =============================================================================
def check_strange_polygon(
    gds_path: str | Path,
    layer: tuple[int, int],
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> StrangePolygonDRCReport:
    """对 GDSII 指定层执行 strange_polygon（奇异多边形）检查（R350）。

    用 KLayout `region.strange_polygon_check()` 检查多边形是否为奇异多边形
    （自相交、退化等）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 保留的最大违规数（防止内存爆炸）。

    Returns:
        StrangePolygonDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / max_violations <= 0 /
            top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region strange_polygon_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if max_violations <= 0:
        raise ValueError(
            f"max_violations 必须 > 0，得到 {max_violations}。"
            f"禁止 fall-back（R03）。"
        )

    # 读取 GDSII
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

    # 提取 Region（递归遍历所有子 cell）
    r = db.Region(top_cell.begin_shapes_rec(li_src))

    # 执行 strange_polygon 检查（无参数）
    # 注意: 返回 Region（多边形集合），不是 EdgePairs
    strange_region = r.strange_polygon_check()

    total = int(strange_region.count())
    bbox_db = strange_region.bbox()

    violations: list[StrangePolygonDRCViolation] = []
    for i, poly in enumerate(strange_region.each()):
        if i >= max_violations:
            break
        # 提取多边形包围盒
        pbox = poly.bbox()
        # 提取多边形面积
        area_dbu2 = int(poly.area())
        # 提取 hull 顶点
        hull_pts: list[tuple[int, int]] = []
        for pt in poly.each_point_hull():
            hull_pts.append((int(pt.x), int(pt.y)))
        violations.append(StrangePolygonDRCViolation(
            polygon_id=i,
            bbox_xmin_dbu=int(pbox.left),
            bbox_ymin_dbu=int(pbox.bottom),
            bbox_xmax_dbu=int(pbox.right),
            bbox_ymax_dbu=int(pbox.top),
            area_dbu2=area_dbu2,
            num_hull_points=len(hull_pts),
            hull_points_dbu=hull_pts,
            area_um2=area_dbu2 * dbu * dbu,
        ))

    bbox_um: tuple[tuple[float, float], tuple[float, float]] | None = None
    if total > 0:
        bbox_um = (
            (float(bbox_db.left) * dbu, float(bbox_db.bottom) * dbu),
            (float(bbox_db.right) * dbu, float(bbox_db.top) * dbu),
        )

    logger.info(
        "GDSII strange_polygon 检查: %s layer=(%d,%d), "
        "violations=%d (返回 %d)",
        in_path, src_layer, src_dt,
        total, len(violations),
    )

    return StrangePolygonDRCReport(
        input_path=str(gds_path),
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=top_cell.name,
        check_type="strange_polygon",
        total_violations=total,
        violations=violations,
        bbox=bbox_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_strange_polygon_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """生成 strange_polygon DRC 检查报告字符串（R350）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 保留的最大违规数。
        output_format: 'text'/'markdown'/'json'。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    report = check_strange_polygon(
        gds_path, layer, top_cell_name, max_violations,
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
def _validate_layer(layer: tuple[int, int], name: str) -> tuple[int, int]:
    """验证层参数（R350 内部函数）。"""
    if not isinstance(layer, (tuple, list)) or len(layer) != 2:
        raise ValueError(
            f"{name} 必须是 (layer, datatype) 二元组，得到 {layer}。"
            f"禁止 fall-back（R03）。"
        )
    g, d = int(layer[0]), int(layer[1])
    if not (0 <= g <= 999):
        raise ValueError(
            f"{name}.layer 必须 0-999，得到 {g}。"
            f"禁止 fall-back（R03）。"
        )
    if not (0 <= d <= 255):
        raise ValueError(
            f"{name}.datatype 必须 0-255，得到 {d}。"
            f"禁止 fall-back（R03）。"
        )
    return (g, d)


def _get_top_cell(ly, top_cell_name: str | None, gds_path: str):
    """获取顶层 cell（R350 内部函数）。"""
    if top_cell_name is not None:
        cell = ly.cell(top_cell_name)
        if cell is None:
            raise ValueError(
                f"顶层 cell '{top_cell_name}' 不存在于 {gds_path}。"
                f"禁止 fall-back（R03）。"
            )
        return cell
    top_cells = ly.top_cells()
    if len(top_cells) == 0:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell。"
            f"禁止 fall-back（R03）。"
        )
    if len(top_cells) > 1:
        names = [c.name for c in top_cells]
        raise ValueError(
            f"GDSII 文件 {gds_path} 有多个顶层 cell: {names}，"
            f"请用 top_cell_name 指定。"
            f"禁止 fall-back（R03）。"
        )
    return top_cells[0]


def _find_or_raise_layer(ly, layer: int, datatype: int, gds_path: str, name: str):
    """查找层，不存在 raise（R350 内部函数）。"""
    li = ly.find_layer(layer, datatype)
    if li is None:
        raise ValueError(
            f"层 ({layer},{datatype}) 不存在于 {gds_path}（{name}）。"
            f"禁止 fall-back（R03）。"
        )
    return li


def _render_text_report(report: StrangePolygonDRCReport) -> str:
    """渲染纯文本报告（R350 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII Strange Polygon DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"层: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(f"违规总数: {report.total_violations}")
    if report.bbox is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox
        lines.append(
            f"违规包围盒: ({xmin:.4f},{ymin:.4f})-({xmax:.4f},{ymax:.4f}) μm"
        )
    lines.append("")
    lines.append("-" * 70)
    lines.append("违规详情（最多显示前 20 条）")
    lines.append("-" * 70)
    for i, v in enumerate(report.violations[:20]):
        lines.append(
            f"  [{i}] polygon_id={v.polygon_id} "
            f"area={v.area_um2:.6f} μm² ({v.area_dbu2} dbu²)\n"
            f"      bbox: ({v.bbox_xmin_dbu},{v.bbox_ymin_dbu})-"
            f"({v.bbox_xmax_dbu},{v.bbox_ymax_dbu}) dbu\n"
            f"      hull_points ({v.num_hull_points}): "
            f"{v.hull_points_dbu[:10]}"
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: StrangePolygonDRCReport) -> str:
    """渲染 Markdown 报告（R350 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII Strange Polygon DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **层**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 违规总数 | {report.total_violations} |")
    if report.bbox is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox
        lines.append(
            f"| 违规包围盒 (μm) | ({xmin:.4f},{ymin:.4f})-({xmax:.4f},{ymax:.4f}) |"
        )
    lines.append("")
    lines.append("## 违规详情（前 20 条）")
    lines.append("")
    lines.append("| # | area (μm²) | bbox (dbu) | hull_pts |")
    lines.append("|---|------------|------------|----------|")
    for i, v in enumerate(report.violations[:20]):
        lines.append(
            f"| {i} | {v.area_um2:.6f} | "
            f"({v.bbox_xmin_dbu},{v.bbox_ymin_dbu})-"
            f"({v.bbox_xmax_dbu},{v.bbox_ymax_dbu}) | "
            f"{v.num_hull_points} |"
        )
    return "\n".join(lines)


def _render_json_report(report: StrangePolygonDRCReport) -> str:
    """渲染 JSON 报告（R350 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "check_type": report.check_type,
        "total_violations": report.total_violations,
        "bbox": (
            [list(report.bbox[0]), list(report.bbox[1])]
            if report.bbox else None
        ),
        "violations": [
            {
                "polygon_id": v.polygon_id,
                "bbox_xmin_dbu": v.bbox_xmin_dbu,
                "bbox_ymin_dbu": v.bbox_ymin_dbu,
                "bbox_xmax_dbu": v.bbox_xmax_dbu,
                "bbox_ymax_dbu": v.bbox_ymax_dbu,
                "area_dbu2": v.area_dbu2,
                "num_hull_points": v.num_hull_points,
                "hull_points_dbu": v.hull_points_dbu,
                "area_um2": v.area_um2,
            }
            for v in report.violations
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
