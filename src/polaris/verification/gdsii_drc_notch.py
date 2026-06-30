"""GDSII DRC notch 检查工具（R346，DRC Notch Checker）。

基于 KLayout Region 的 notch_check API，对 GDSII 指定层执行 DRC 凹角
检查，返回违规列表和详细报告。

## 核心概念

- **Notch（凹角）**: 多边形边界上的凹入部分，形成 U 型或 V 型槽
  - 同一多边形凹槽两侧边距离过近会产生 notch 违规
  - 典型场景: U 型波导耦合器、MMI 锥形过渡区的凹槽
- **Notch 检查**: 检查同一 Region 内凹角处的最小间距
  - 与 space_check 区别: space_check 检查不同多边形之间，notch_check
    专门检查同一多边形（或合并后 Region）凹角处的间距
  - 违规: 凹槽两侧边距离 < min_notch
- **EdgePair（违规对）**: KLayout DRC 检查返回的违规结果
  - first: 凹槽一侧边
  - second: 凹槽另一侧边
  - distance: 两条边之间的距离（违规凹槽宽度）

## KLayout 0.30.9 API 关键事实（R346）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.notch_check(d)`: 检查同一 Region 内凹角间距 < d dbu 的违规
  - 返回 EdgePairs 集合
  - d: 最小凹角间距阈值（dbu，int）
  - 语义: 仅检查同一多边形凹角，不检查不同多边形之间（那是 space_check）
- `edge_pairs.count()` / `each()` / `bbox()`: 违规数 / 迭代 / 包围盒
- `edge_pair.first` / `second` / `distance()`: 违规边对 / 距离

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 min_value_um → dbu（min_value_dbu = min_value_um / dbu）
4. 执行: region.notch_check(min_value_dbu)
5. 迭代 EdgePairs，提取每个违规的:
   - first 边端点 (x1,y1)-(x2,y2)
   - second 边端点 (x3,y3)-(x4,y4)
   - distance（违规凹槽宽度）
6. 生成报告

## 学术依据

- KLayout Region class (notch_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs class:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair class:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html
- KLayout DRC Reference (notch):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Notch Check:
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
    "NotchDRCViolation",
    "NotchDRCReport",
    "check_notch",
    "generate_notch_drc_report",
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
            "klayout 未安装，无法执行 GDSII notch 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class NotchDRCViolation:
    """单个 notch 违规（R346）。

    Attributes:
        x1_dbu: first 边端点 1 x（dbu）。
        y1_dbu: first 边端点 1 y（dbu）。
        x2_dbu: first 边端点 2 x（dbu）。
        y2_dbu: first 边端点 2 y（dbu）。
        x3_dbu: second 边端点 1 x（dbu）。
        y3_dbu: second 边端点 1 y（dbu）。
        x4_dbu: second 边端点 2 x（dbu）。
        y4_dbu: second 边端点 2 y（dbu）。
        distance_um: 违规凹槽宽度（μm）。
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
class NotchDRCReport:
    """GDSII notch DRC 检查报告（R346）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_notch_um: 最小凹角间距阈值（μm）。
        check_type: 检查类型（"notch"）。
        total_violations: 违规总数。
        violations: 违规列表。
        bbox: 所有违规的包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
    """

    input_path: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    min_notch_um: float = 0.0
    check_type: str = "notch"
    total_violations: int = 0
    violations: list[NotchDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None


# =============================================================================
# notch 检查主入口
# =============================================================================
def check_notch(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_notch_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> NotchDRCReport:
    """对 GDSII 指定层执行 notch（凹角）检查（R346）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_notch_um: 最小凹角间距阈值（μm）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 保留的最大违规数（防止内存爆炸）。

    Returns:
        NotchDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / min_notch_um <= 0 /
            max_violations <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region notch_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if min_notch_um <= 0:
        raise ValueError(
            f"min_notch_um 必须 > 0，得到 {min_notch_um}。"
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

    # 执行 notch 检查
    min_notch_dbu = int(round(min_notch_um / dbu))
    edge_pairs = r.notch_check(min_notch_dbu)

    total = int(edge_pairs.count())
    bbox_db = edge_pairs.bbox()

    violations: list[NotchDRCViolation] = []
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
        violations.append(NotchDRCViolation(
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
        "GDSII notch 检查: %s layer=(%d,%d), min_notch=%.4fμm, "
        "violations=%d (返回 %d)",
        in_path, src_layer, src_dt, min_notch_um,
        total, len(violations),
    )

    return NotchDRCReport(
        input_path=str(gds_path),
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=top_cell.name,
        min_notch_um=min_notch_um,
        check_type="notch",
        total_violations=total,
        violations=violations,
        bbox=bbox_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_notch_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    min_notch_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """生成 notch DRC 检查报告字符串（R346）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        min_notch_um: 最小凹角间距阈值（μm）。
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
    report = check_notch(
        gds_path, layer, min_notch_um, top_cell_name, max_violations,
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
    """验证层参数（R346 内部函数）。"""
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
    """获取顶层 cell（R346 内部函数）。"""
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
    """查找层，不存在 raise（R346 内部函数）。"""
    li = ly.find_layer(layer, datatype)
    if li is None:
        raise ValueError(
            f"层 ({layer},{datatype}) 不存在于 {gds_path}（{name}）。"
            f"禁止 fall-back（R03）。"
        )
    return li


def _render_text_report(report: NotchDRCReport) -> str:
    """渲染纯文本报告（R346 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII Notch DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"层: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(f"最小凹角间距: {report.min_notch_um:.4f} μm")
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


def _render_markdown_report(report: NotchDRCReport) -> str:
    """渲染 Markdown 报告（R346 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII Notch DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **层**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append(f"- **最小凹角间距**: {report.min_notch_um:.4f} μm")
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


def _render_json_report(report: NotchDRCReport) -> str:
    """渲染 JSON 报告（R346 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "check_type": report.check_type,
        "min_notch_um": report.min_notch_um,
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
