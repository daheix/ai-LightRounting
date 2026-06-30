"""GDSII DRC width/space 检查工具（R343，DRC Width/Space Checker）。

基于 KLayout Region 的 width_check / space_check API，对 GDSII 指定层执行
DRC 宽度/间距检查，返回违规列表和详细报告。

## 核心概念

- **Width 检查（宽度检查）**: 检查同层内多边形的最小宽度是否满足阈值
  - 违规: 两条相对的边距离 < min_width
  - 典型用途: 检查线宽是否过窄（可能导致工艺失败）
- **Space 检查（间距检查）**: 检查同层内多边形之间的最小间距是否满足阈值
  - 违规: 两个不同多边形的边距离 < min_space
  - 典型用途: 检查间距是否过小（可能导致短路）
- **EdgePair（违规对）**: KLayout DRC 检查返回的违规结果
  - first: 第一条违规边
  - second: 第二条违规边
  - distance: 两条边之间的距离（违规宽度/间距）

## KLayout 0.30.9 API 关键事实（R343 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.width_check(d)`: 检查同层内宽度 < d dbu 的违规
  - 返回 EdgePairs 集合
  - d: 最小宽度阈值（dbu，int）
- `region.space_check(d)`: 检查同层内间距 < d dbu 的违规
  - 返回 EdgePairs 集合
  - d: 最小间距阈值（dbu，int）
- `edge_pairs.count()`: 返回违规数（int）
- `edge_pairs.each()`: 迭代 EdgePair
- `edge_pairs.bbox()`: 返回所有违规的包围盒（db.Box）
- `edge_pair.first`: 第一条违规边（Edge）
- `edge_pair.second`: 第二条违规边（Edge）
- `edge_pair.distance()`: 两条边之间的距离（int，dbu 单位）
- `edge.length()`: 边长度（int，dbu）
- `edge.p1` / `edge.p2`: 边端点（Point，dbu）
- Region DRC 方法: width_check / space_check / enclosed_check /
  enclosing_check / inside_check / isolated_check / notch_check /
  overlap_check / separation_check / grid_check / strange_polygon_check

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 min_value_um → dbu（min_value_dbu = min_value_um / dbu）
4. 执行检查:
   - width: region.width_check(min_value_dbu)
   - space: region.space_check(min_value_dbu)
5. 迭代 EdgePairs，提取每个违规的:
   - first 边端点 (x1,y1)-(x2,y2)
   - second 边端点 (x3,y3)-(x4,y4)
   - distance（违规距离）
6. 生成报告

## 学术依据

- KLayout Region class (width_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs class:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair class:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html
- KLayout DRC Reference (width, space):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- KLayout Geometry API:
  https://www.klayout.de/doc-qt5/programming/geometry_api.html
- Calibre DRC Width/Space:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC DRC Rules:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "DRCViolation",
    "DRCReport",
    "check_width",
    "check_space",
    "generate_drc_report",
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
            "klayout 未安装，无法执行 GDSII DRC 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class DRCViolation:
    """单个 DRC 违规记录（R343）。

    一个违规由两条边组成（first 和 second），表示宽度或间距违规。

    Attributes:
        x1_um: first 边起点 X（μm）。
        y1_um: first 边起点 Y（μm）。
        x2_um: first 边终点 X（μm）。
        y2_um: first 边终点 Y（μm）。
        x3_um: second 边起点 X（μm）。
        y3_um: second 边起点 Y（μm）。
        x4_um: second 边终点 X（μm）。
        y4_um: second 边终点 Y（μm）。
        distance_um: 两条边之间的距离（μm，即违规宽度/间距）。
    """

    x1_um: float
    y1_um: float
    x2_um: float
    y2_um: float
    x3_um: float
    y3_um: float
    x4_um: float
    y4_um: float
    distance_um: float


@dataclass
class DRCReport:
    """GDSII DRC 检查报告（R343）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        check_type: 检查类型 'width' / 'space'。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_value_um: 最小阈值（μm，宽度或间距）。
        total_violations: 违规总数。
        violations: 违规列表（最多 max_violations 条）。
        bbox: 违规区域包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
        max_violations: 报告中保留的最大违规数。
    """

    input_path: str = ""
    check_type: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    min_value_um: float = 0.0
    total_violations: int = 0
    violations: list[DRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None
    max_violations: int = 1000


# =============================================================================
# Width 检查主入口
# =============================================================================
def check_width(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_width_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> DRCReport:
    """对 GDSII 层执行 DRC width 检查（R343）。

    用 KLayout `region.width_check(d)` 检查同层内多边形的最小宽度。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_width_um: 最小宽度阈值（μm），宽度 < 此值的为违规。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 报告中保留的最大违规数（默认 1000）。

    Returns:
        DRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / min_width_um <= 0 /
            top_cell_name 不存在 / 层不存在 / max_violations <= 0。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region width_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    - KLayout DRC Reference width: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    return _run_check(
        gds_path=gds_path,
        layer=layer,
        min_value_um=min_width_um,
        check_type="width",
        top_cell_name=top_cell_name,
        max_violations=max_violations,
    )


# =============================================================================
# Space 检查主入口
# =============================================================================
def check_space(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_space_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> DRCReport:
    """对 GDSII 层执行 DRC space 检查（R343）。

    用 KLayout `region.space_check(d)` 检查同层内多边形之间的最小间距。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_space_um: 最小间距阈值（μm），间距 < 此值的为违规。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 报告中保留的最大违规数（默认 1000）。

    Returns:
        DRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / min_space_um <= 0 /
            top_cell_name 不存在 / 层不存在 / max_violations <= 0。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region space_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    - KLayout DRC Reference space: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    return _run_check(
        gds_path=gds_path,
        layer=layer,
        min_value_um=min_space_um,
        check_type="space",
        top_cell_name=top_cell_name,
        max_violations=max_violations,
    )


# =============================================================================
# 内部检查实现
# =============================================================================
def _run_check(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_value_um: float,
    check_type: str,
    top_cell_name: str | None,
    max_violations: int,
) -> DRCReport:
    """执行 DRC 检查的内部实现（R343 内部函数）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_value_um: 最小阈值（μm）。
        check_type: 'width' / 'space'。
        top_cell_name: 顶层 cell 名。
        max_violations: 最大违规数。

    Returns:
        DRCReport 检查报告。
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if min_value_um <= 0:
        raise ValueError(
            f"min_value_um 必须 > 0，得到: {min_value_um}。"
            f"禁止 fall-back（R03）。"
        )

    if not isinstance(max_violations, int) or max_violations <= 0:
        raise ValueError(
            f"max_violations 必须是正整数，得到: {max_violations}。"
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

    # 获取/验证层
    li_src = _find_or_raise_layer(ly, src_layer, src_dt, gds_path, "layer")

    # 提取 Region（递归遍历子 cell）
    r = db.Region(top_cell.begin_shapes_rec(li_src))

    # 转换 min_value_um → dbu
    min_value_dbu = int(round(min_value_um / dbu))

    # 执行检查
    if check_type == "width":
        edge_pairs = r.width_check(min_value_dbu)
    else:  # space
        edge_pairs = r.space_check(min_value_dbu)

    total_violations = int(edge_pairs.count())

    # 提取违规详情（最多 max_violations 条）
    violations: list[DRCViolation] = []
    for ep in edge_pairs.each():
        if len(violations) >= max_violations:
            break
        first = ep.first
        second = ep.second
        distance_dbu = int(ep.distance())
        violations.append(DRCViolation(
            x1_um=float(int(first.p1.x)) * dbu,
            y1_um=float(int(first.p1.y)) * dbu,
            x2_um=float(int(first.p2.x)) * dbu,
            y2_um=float(int(first.p2.y)) * dbu,
            x3_um=float(int(second.p1.x)) * dbu,
            y3_um=float(int(second.p1.y)) * dbu,
            x4_um=float(int(second.p2.x)) * dbu,
            y4_um=float(int(second.p2.y)) * dbu,
            distance_um=float(distance_dbu) * dbu,
        ))

    # 违规区域包围盒
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None
    if total_violations > 0:
        ep_bbox = edge_pairs.bbox()
        bbox = (
            (float(int(ep_bbox.left)) * dbu, float(int(ep_bbox.bottom)) * dbu),
            (float(int(ep_bbox.right)) * dbu, float(int(ep_bbox.top)) * dbu),
        )

    logger.info(
        "GDSII DRC %s 检查: %s (%d,%d), min=%.4fμm, violations=%d",
        check_type, in_path, src_layer, src_dt,
        min_value_um, total_violations,
    )

    return DRCReport(
        input_path=str(gds_path),
        check_type=check_type,
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=str(top_cell.name),
        min_value_um=min_value_um,
        total_violations=total_violations,
        violations=violations,
        bbox=bbox,
        max_violations=max_violations,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    check_type: str,
    min_value_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """执行 GDSII DRC 检查并生成报告字符串（R343）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        check_type: 检查类型 'width' / 'space'。
        min_value_um: 最小阈值（μm）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / check_type 无效 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    ct = check_type.lower()
    if ct == "width":
        report = check_width(
            gds_path, layer, min_value_um, top_cell_name, max_violations
        )
    elif ct == "space":
        report = check_space(
            gds_path, layer, min_value_um, top_cell_name, max_violations
        )
    else:
        raise ValueError(
            f"不支持的 check_type: {check_type}。"
            f"支持: width / space。"
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
    """验证层参数（R343 内部函数）。"""
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
    """获取顶层 cell（R343 内部函数）。"""
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
    """查找层，不存在则 raise（R343 内部函数）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return int(li)
    raise ValueError(
        f"{context} ({layer}, {datatype}) 在文件 {gds_path} 中不存在。"
        f"禁止 fall-back（R03）。"
    )


def _render_text_report(report: DRCReport) -> str:
    """渲染纯文本报告（R343 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"GDSII DRC {report.check_type.upper()} 检查报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"layer: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(
        f"最小阈值: {report.min_value_um:.6f} μm"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("检查结果")
    lines.append("-" * 60)
    lines.append(f"  违规总数: {report.total_violations}")
    if report.bbox is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox
        lines.append(
            f"  违规区域 bbox: ({xmin:.6f}, {ymin:.6f}) - "
            f"({xmax:.6f}, {ymax:.6f}) μm"
        )
    else:
        lines.append("  违规区域 bbox: (无违规)")
    lines.append(f"  报告保留违规: {len(report.violations)}")
    if report.total_violations > report.max_violations:
        lines.append(
            f"  (实际违规 {report.total_violations} > 上限 "
            f"{report.max_violations}，仅保留前 {report.max_violations} 条)"
        )
    if report.violations:
        lines.append("")
        lines.append(f"  违规详情（前 {min(10, len(report.violations))} 条）:")
        for i, v in enumerate(report.violations[:10]):
            lines.append(
                f"    [{i}] distance={v.distance_um:.6f} μm"
            )
            lines.append(
                f"        first:  ({v.x1_um:.4f},{v.y1_um:.4f}) → "
                f"({v.x2_um:.4f},{v.y2_um:.4f})"
            )
            lines.append(
                f"        second: ({v.x3_um:.4f},{v.y3_um:.4f}) → "
                f"({v.x4_um:.4f},{v.y4_um:.4f})"
            )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: DRCReport) -> str:
    """渲染 Markdown 报告（R343 内部函数）。"""
    lines: list[str] = []
    lines.append(f"# GDSII DRC {report.check_type.upper()} 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **layer**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append(f"- **最小阈值**: {report.min_value_um:.6f} μm")
    lines.append("")
    lines.append("## 检查结果")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 违规总数 | {report.total_violations} |")
    lines.append(f"| 报告保留违规 | {len(report.violations)} |")
    if report.bbox is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox
        lines.append(
            f"| 违规区域 bbox (μm) | "
            f"({xmin:.6f}, {ymin:.6f}) - ({xmax:.6f}, {ymax:.6f}) |"
        )
    else:
        lines.append("| 违规区域 bbox | (无违规) |")
    if report.violations:
        lines.append("")
        lines.append(f"## 违规详情（前 {min(20, len(report.violations))} 条）")
        lines.append("")
        lines.append(
            "| # | 距离 (μm) | first 边 | second 边 |"
        )
        lines.append("|---|----------|----------|-----------|")
        for i, v in enumerate(report.violations[:20]):
            lines.append(
                f"| {i} | {v.distance_um:.4f} | "
                f"({v.x1_um:.3f},{v.y1_um:.3f})→({v.x2_um:.3f},{v.y2_um:.3f}) | "
                f"({v.x3_um:.3f},{v.y3_um:.3f})→({v.x4_um:.3f},{v.y4_um:.3f}) |"
            )
    return "\n".join(lines)


def _render_json_report(report: DRCReport) -> str:
    """渲染 JSON 报告（R343 内部函数）。"""
    import json

    def _bbox_dict(bbox):
        if bbox is None:
            return None
        (xmin, ymin), (xmax, ymax) = bbox
        return {
            "xmin_um": xmin, "ymin_um": ymin,
            "xmax_um": xmax, "ymax_um": ymax,
        }

    data = {
        "input_path": report.input_path,
        "check_type": report.check_type,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "min_value_um": report.min_value_um,
        "total_violations": report.total_violations,
        "max_violations": report.max_violations,
        "bbox": _bbox_dict(report.bbox),
        "violations": [
            {
                "x1_um": v.x1_um, "y1_um": v.y1_um,
                "x2_um": v.x2_um, "y2_um": v.y2_um,
                "x3_um": v.x3_um, "y3_um": v.y3_um,
                "x4_um": v.x4_um, "y4_um": v.y4_um,
                "distance_um": v.distance_um,
            }
            for v in report.violations
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
