"""GDSII DRC area 检查工具（R347，DRC Area Checker）。

基于 KLayout Region 的 polygon 迭代和 area() API，对 GDSII 指定层执行
DRC 最小面积检查，返回违规列表和详细报告。

## 核心概念

- **Area 检查（面积检查）**: 检查同层内每个多边形的面积是否 >= min_area
  - 违规: 单个多边形面积 < min_area
  - 典型用途: 检查通孔、焊盘、金属块的最小面积（工艺限制）
- **Region 合并**: KLayout Region 默认合并重叠/相邻的多边形
  - area 检查针对合并后的独立多边形区域
  - 与原始 shape 的面积可能不同（如果有重叠）
- **Polygon 迭代**: 用 region.each() 迭代每个独立多边形
  - polygon.area(): 返回面积（dbu²）
  - polygon.bbox(): 返回包围盒（db.Box）

## KLayout 0.30.9 API 关键事实（R347 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.count()`: 返回合并后的独立多边形数
- `region.area()`: 返回总面积（dbu²）
- `region.each()`: 迭代每个独立多边形（Polygon/SimplePolygon）
- `polygon.area()`: 返回单个多边形面积（dbu²，int）
- `polygon.bbox()`: 返回多边形包围盒（db.Box，dbu 单位）
- `bbox.width()` / `bbox.height()`: 宽/高（dbu，int）
- `bbox.left` / `bbox.bottom` / `bbox.right` / `bbox.top`: 边界（dbu，int）

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 min_area_um2 → dbu²（min_area_dbu2 = min_area_um2 / dbu²）
4. 迭代 region.each():
   - 计算 area_um2 = polygon.area() * dbu * dbu
   - 如果 area_um2 < min_area_um2，记录违规
5. 违规包含 bbox 和 area
6. 生成报告

## 学术依据

- KLayout Region class (area, each):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout Polygon class (area, bbox):
  https://www.klayout.de/doc-qt5/code/class_Polygon.html
- KLayout DRC Reference (area):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- KLayout Geometry API:
  https://www.klayout.de/doc-qt5/programming/geometry_api.html
- Calibre DRC Area Check:
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
    "AreaDRCViolation",
    "AreaDRCReport",
    "check_area",
    "generate_area_drc_report",
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
            "klayout 未安装，无法执行 GDSII area 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class AreaDRCViolation:
    """单个 area 违规（R347）。

    Attributes:
        bbox_xmin_um: 包围盒 xmin（μm）。
        bbox_ymin_um: 包围盒 ymin（μm）。
        bbox_xmax_um: 包围盒 xmax（μm）。
        bbox_ymax_um: 包围盒 ymax（μm）。
        area_um2: 多边形面积（μm²）。
        min_area_um2: 最小面积阈值（μm²）。
    """

    bbox_xmin_um: float
    bbox_ymin_um: float
    bbox_xmax_um: float
    bbox_ymax_um: float
    area_um2: float
    min_area_um2: float


@dataclass
class AreaDRCReport:
    """GDSII area DRC 检查报告（R347）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_area_um2: 最小面积阈值（μm²）。
        check_type: 检查类型（"area"）。
        total_polygons: 多边形总数。
        total_violations: 违规总数。
        total_area_um2: 所有多边形总面积（μm²）。
        violations: 违规列表。
        bbox: 所有违规的包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
    """

    input_path: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    min_area_um2: float = 0.0
    check_type: str = "area"
    total_polygons: int = 0
    total_violations: int = 0
    total_area_um2: float = 0.0
    violations: list[AreaDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None


# =============================================================================
# area 检查主入口
# =============================================================================
def check_area(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_area_um2: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> AreaDRCReport:
    """对 GDSII 指定层执行 area（最小面积）检查（R347）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_area_um2: 最小面积阈值（μm²）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 保留的最大违规数（防止内存爆炸）。

    Returns:
        AreaDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / min_area_um2 <= 0 /
            max_violations <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region area: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if min_area_um2 <= 0:
        raise ValueError(
            f"min_area_um2 必须 > 0，得到 {min_area_um2}。"
            f"禁止 fall-back（R03）。"
        )
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

    total_polygons = int(r.count())
    total_area_dbu2 = float(r.area())
    total_area_um2 = total_area_dbu2 * dbu * dbu

    violations: list[AreaDRCViolation] = []
    violation_count = 0

    # 迭代每个独立多边形
    for poly in r.each():
        poly_area_dbu2 = float(poly.area())
        poly_area_um2 = poly_area_dbu2 * dbu * dbu

        if poly_area_um2 < min_area_um2:
            violation_count += 1
            if len(violations) < max_violations:
                bbox_db = poly.bbox()
                violations.append(AreaDRCViolation(
                    bbox_xmin_um=float(bbox_db.left) * dbu,
                    bbox_ymin_um=float(bbox_db.bottom) * dbu,
                    bbox_xmax_um=float(bbox_db.right) * dbu,
                    bbox_ymax_um=float(bbox_db.top) * dbu,
                    area_um2=poly_area_um2,
                    min_area_um2=min_area_um2,
                ))

    # 计算所有违规的包围盒
    bbox_um: tuple[tuple[float, float], tuple[float, float]] | None = None
    if violation_count > 0 and violations:
        xmin = min(v.bbox_xmin_um for v in violations)
        ymin = min(v.bbox_ymin_um for v in violations)
        xmax = max(v.bbox_xmax_um for v in violations)
        ymax = max(v.bbox_ymax_um for v in violations)
        bbox_um = ((xmin, ymin), (xmax, ymax))

    logger.info(
        "GDSII area 检查: %s layer=(%d,%d), min_area=%.6fμm², "
        "polygons=%d, violations=%d (返回 %d), total_area=%.6fμm²",
        in_path, src_layer, src_dt, min_area_um2,
        total_polygons, violation_count, len(violations),
        total_area_um2,
    )

    return AreaDRCReport(
        input_path=str(gds_path),
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=top_cell.name,
        min_area_um2=min_area_um2,
        check_type="area",
        total_polygons=total_polygons,
        total_violations=violation_count,
        total_area_um2=total_area_um2,
        violations=violations,
        bbox=bbox_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_area_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_area_um2: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """生成 area DRC 检查报告字符串（R347）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_area_um2: 最小面积阈值（μm²）。
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
    report = check_area(
        gds_path, layer, min_area_um2, top_cell_name, max_violations,
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
    """验证层参数（R347 内部函数）。"""
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
    """获取顶层 cell（R347 内部函数）。"""
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
    """查找层，不存在 raise（R347 内部函数）。"""
    li = ly.find_layer(layer, datatype)
    if li is None:
        raise ValueError(
            f"层 ({layer},{datatype}) 不存在于 {gds_path}（{name}）。"
            f"禁止 fall-back（R03）。"
        )
    return li


def _render_text_report(report: AreaDRCReport) -> str:
    """渲染纯文本报告（R347 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII Area DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"层: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(f"最小面积: {report.min_area_um2:.6f} μm²")
    lines.append(f"多边形总数: {report.total_polygons}")
    lines.append(f"总面积: {report.total_area_um2:.6f} μm²")
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
            f"  [{i}] area={v.area_um2:.6f} μm² < min={v.min_area_um2:.6f} μm²\n"
            f"      bbox: ({v.bbox_xmin_um:.4f},{v.bbox_ymin_um:.4f})-"
            f"({v.bbox_xmax_um:.4f},{v.bbox_ymax_um:.4f}) μm"
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: AreaDRCReport) -> str:
    """渲染 Markdown 报告（R347 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII Area DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **层**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append(f"- **最小面积**: {report.min_area_um2:.6f} μm²")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 多边形总数 | {report.total_polygons} |")
    lines.append(f"| 总面积 (μm²) | {report.total_area_um2:.6f} |")
    lines.append(f"| 违规总数 | {report.total_violations} |")
    if report.bbox is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox
        lines.append(
            f"| 违规包围盒 (μm) | ({xmin:.4f},{ymin:.4f})-({xmax:.4f},{ymax:.4f}) |"
        )
    lines.append("")
    lines.append("## 违规详情（前 20 条）")
    lines.append("")
    lines.append("| # | area (μm²) | min (μm²) | bbox (μm) |")
    lines.append("|---|-----------|-----------|-----------|")
    for i, v in enumerate(report.violations[:20]):
        lines.append(
            f"| {i} | {v.area_um2:.6f} | {v.min_area_um2:.6f} | "
            f"({v.bbox_xmin_um:.4f},{v.bbox_ymin_um:.4f})-"
            f"({v.bbox_xmax_um:.4f},{v.bbox_ymax_um:.4f}) |"
        )
    return "\n".join(lines)


def _render_json_report(report: AreaDRCReport) -> str:
    """渲染 JSON 报告（R347 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "check_type": report.check_type,
        "min_area_um2": report.min_area_um2,
        "total_polygons": report.total_polygons,
        "total_violations": report.total_violations,
        "total_area_um2": report.total_area_um2,
        "bbox": (
            [list(report.bbox[0]), list(report.bbox[1])]
            if report.bbox else None
        ),
        "violations": [
            {
                "bbox_xmin_um": v.bbox_xmin_um,
                "bbox_ymin_um": v.bbox_ymin_um,
                "bbox_xmax_um": v.bbox_xmax_um,
                "bbox_ymax_um": v.bbox_ymax_um,
                "area_um2": v.area_um2,
                "min_area_um2": v.min_area_um2,
            }
            for v in report.violations
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
