"""GDSII DRC isolated 检查工具（R348，DRC Isolated Checker）。

基于 KLayout Region 的 isolated_check API，对 GDSII 指定层执行 DRC
孤立检查，返回违规列表和详细报告。

## 核心概念

- **Isolated 检查（孤立/隔离检查）**: 检查同层内多边形之间是否被充分隔离
  - 违规: 两个多边形之间间距 < min_isolated
  - 与 space_check 区别: isolated_check 语义上检查"隔离性"，确保多边形
    之间有足够的隔离距离（如防止串扰、工艺隔离要求）
  - 典型用途: 高压器件隔离、模拟/数字区域隔离、敏感电路保护
- **EdgePair（违规对）**: KLayout DRC 检查返回的违规结果
  - first: 第一个多边形的边
  - second: 第二个多边形的边
  - distance: 两条边之间的距离（违规间距）

## KLayout 0.30.9 API 关键事实（R348 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.isolated_check(d)`: 检查同层内多边形间距 < d dbu 的违规
  - 返回 EdgePairs 集合
  - d: 最小隔离间距阈值（dbu，int）
- 实测: 两个间距 2μm 的矩形
  - isolated_check(2.5μm): 1 个违规（间距 2μm < 2.5μm）
  - isolated_check(1.5μm): 0 个违规（间距 2μm > 1.5μm）
  - isolated_check(2.0μm): 0 个违规（间距 == 阈值，边界不违规）
- 单个多边形: 0 个违规（无其他多边形比较）
- `edge_pairs.count()` / `each()` / `bbox()`: 违规数 / 迭代 / 包围盒
- `edge_pair.first` / `second` / `distance()`: 违规边对 / 距离

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 min_value_um → dbu
4. 执行: region.isolated_check(min_value_dbu)
5. 迭代 EdgePairs，提取每个违规的 first/second 边和 distance
6. 生成报告

## 学术依据

- KLayout Region class (isolated_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs class:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair class:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html
- KLayout DRC Reference (isolated):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Isolated Check:
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
    "IsolatedDRCViolation",
    "IsolatedDRCReport",
    "check_isolated",
    "generate_isolated_drc_report",
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
            "klayout 未安装，无法执行 GDSII isolated 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class IsolatedDRCViolation:
    """单个 isolated 违规（R348）。

    Attributes:
        x1_dbu: first 边端点 1 x（dbu）。
        y1_dbu: first 边端点 1 y（dbu）。
        x2_dbu: first 边端点 2 x（dbu）。
        y2_dbu: first 边端点 2 y（dbu）。
        x3_dbu: second 边端点 1 x（dbu）。
        y3_dbu: second 边端点 1 y（dbu）。
        x4_dbu: second 边端点 2 x（dbu）。
        y4_dbu: second 边端点 2 y（dbu）。
        distance_um: 违规间距（μm）。
    """

    x1_dbu: int
    y1_dbu: int
    x2_dbu: int
    y2_dbu: int
    x3_dbu: int
    y3_dbu: int
    x4_dbu: int
    y4_dbu: int
    distance_um: float


@dataclass
class IsolatedDRCReport:
    """GDSII isolated DRC 检查报告（R348）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_isolated_um: 最小隔离间距阈值（μm）。
        check_type: 检查类型（"isolated"）。
        total_violations: 违规总数。
        violations: 违规列表。
        bbox: 所有违规的包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
    """

    input_path: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    min_isolated_um: float = 0.0
    check_type: str = "isolated"
    total_violations: int = 0
    violations: list[IsolatedDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None


# =============================================================================
# isolated 检查主入口
# =============================================================================
def check_isolated(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_isolated_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> IsolatedDRCReport:
    """对 GDSII 指定层执行 isolated（孤立/隔离）检查（R348）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_isolated_um: 最小隔离间距阈值（μm）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 保留的最大违规数（防止内存爆炸）。

    Returns:
        IsolatedDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / min_isolated_um <= 0 /
            max_violations <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region isolated_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if min_isolated_um <= 0:
        raise ValueError(
            f"min_isolated_um 必须 > 0，得到 {min_isolated_um}。"
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

    # 提取 Region
    r = db.Region(top_cell.begin_shapes_rec(li_src))

    # 执行 isolated 检查
    min_isolated_dbu = int(round(min_isolated_um / dbu))
    edge_pairs = r.isolated_check(min_isolated_dbu)

    total = int(edge_pairs.count())
    bbox_db = edge_pairs.bbox()

    violations: list[IsolatedDRCViolation] = []
    for i, ep in enumerate(edge_pairs.each()):
        if i >= max_violations:
            break
        e1 = ep.first
        e2 = ep.second
        p1 = e1.p1
        p2 = e1.p2
        p3 = e2.p1
        p4 = e2.p2
        dist_dbu = int(ep.distance())
        violations.append(IsolatedDRCViolation(
            x1_dbu=int(p1.x), y1_dbu=int(p1.y),
            x2_dbu=int(p2.x), y2_dbu=int(p2.y),
            x3_dbu=int(p3.x), y3_dbu=int(p3.y),
            x4_dbu=int(p4.x), y4_dbu=int(p4.y),
            distance_um=dist_dbu * dbu,
        ))

    bbox_um: tuple[tuple[float, float], tuple[float, float]] | None = None
    if total > 0:
        bbox_um = (
            (float(bbox_db.left) * dbu, float(bbox_db.bottom) * dbu),
            (float(bbox_db.right) * dbu, float(bbox_db.top) * dbu),
        )

    logger.info(
        "GDSII isolated 检查: %s layer=(%d,%d), min_isolated=%.4fμm, "
        "violations=%d (返回 %d)",
        in_path, src_layer, src_dt, min_isolated_um,
        total, len(violations),
    )

    return IsolatedDRCReport(
        input_path=str(gds_path),
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=top_cell.name,
        min_isolated_um=min_isolated_um,
        check_type="isolated",
        total_violations=total,
        violations=violations,
        bbox=bbox_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_isolated_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_isolated_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """生成 isolated DRC 检查报告字符串（R348）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_isolated_um: 最小隔离间距阈值（μm）。
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
    report = check_isolated(
        gds_path, layer, min_isolated_um, top_cell_name, max_violations,
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
    """验证层参数（R348 内部函数）。"""
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
    """获取顶层 cell（R348 内部函数）。"""
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
    """查找层，不存在 raise（R348 内部函数）。"""
    li = ly.find_layer(layer, datatype)
    if li is None:
        raise ValueError(
            f"层 ({layer},{datatype}) 不存在于 {gds_path}（{name}）。"
            f"禁止 fall-back（R03）。"
        )
    return li


def _render_text_report(report: IsolatedDRCReport) -> str:
    """渲染纯文本报告（R348 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII Isolated DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"层: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(f"最小隔离间距: {report.min_isolated_um:.4f} μm")
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
            f"  [{i}] distance={v.distance_um:.4f} μm\n"
            f"      first:  ({v.x1_dbu},{v.y1_dbu})-({v.x2_dbu},{v.y2_dbu}) dbu\n"
            f"      second: ({v.x3_dbu},{v.y3_dbu})-({v.x4_dbu},{v.y4_dbu}) dbu"
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: IsolatedDRCReport) -> str:
    """渲染 Markdown 报告（R348 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII Isolated DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **层**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append(f"- **最小隔离间距**: {report.min_isolated_um:.4f} μm")
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
    lines.append("| # | distance (μm) | first 边 (dbu) | second 边 (dbu) |")
    lines.append("|---|---------------|-----------------|------------------|")
    for i, v in enumerate(report.violations[:20]):
        lines.append(
            f"| {i} | {v.distance_um:.4f} | "
            f"({v.x1_dbu},{v.y1_dbu})-({v.x2_dbu},{v.y2_dbu}) | "
            f"({v.x3_dbu},{v.y3_dbu})-({v.x4_dbu},{v.y4_dbu}) |"
        )
    return "\n".join(lines)


def _render_json_report(report: IsolatedDRCReport) -> str:
    """渲染 JSON 报告（R348 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "check_type": report.check_type,
        "min_isolated_um": report.min_isolated_um,
        "total_violations": report.total_violations,
        "bbox": (
            [list(report.bbox[0]), list(report.bbox[1])]
            if report.bbox else None
        ),
        "violations": [
            {
                "x1_dbu": v.x1_dbu, "y1_dbu": v.y1_dbu,
                "x2_dbu": v.x2_dbu, "y2_dbu": v.y2_dbu,
                "x3_dbu": v.x3_dbu, "y3_dbu": v.y3_dbu,
                "x4_dbu": v.x4_dbu, "y4_dbu": v.y4_dbu,
                "distance_um": v.distance_um,
            }
            for v in report.violations
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
