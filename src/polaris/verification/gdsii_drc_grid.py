"""GDSII DRC grid 检查工具（R349，DRC Grid Checker）。

基于 KLayout Region 的 grid_check API，对 GDSII 指定层执行 DRC
网格检查，返回未对齐顶点列表和详细报告。

## 核心概念

- **Grid 检查（网格检查）**: 检查多边形顶点是否对齐到指定网格
  - 违规: 顶点坐标不在 (gx, gy) 网格上
  - 典型用途: 确保版图顶点对齐到制造网格（如 100nm 网格），
    避免 fracturing 错误和工艺偏差
- **退化 EdgePair**: grid_check 返回的 EdgePair 中 first/second 边
  均为退化点（p1 == p2），表示未对齐顶点位置
  - distance: 始终为 0（点到自身的距离）

## KLayout 0.30.9 API 关键事实（R349 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.grid_check(gx, gy)`: 检查顶点是否在 (gx, gy) 网格上
  - 返回 EdgePairs 集合
  - gx: x 方向网格大小（dbu，int）
  - gy: y 方向网格大小（dbu，int）
  - 注意: 需要两个参数，不能只传一个
- 实测: 未对齐多边形 Box(2050,2050,3050,3050) 在 100nm 网格上
  - grid_check(100, 100): 4 个违规（4 个顶点都不对齐）
  - grid_check(50, 50): 0 个违规（2050 是 50 的倍数）
- 对齐多边形 Box(0,0,1000,1000) 在 100nm 网格上: 0 个违规
- `edge_pairs.count()` / `each()` / `bbox()`: 违规数 / 迭代 / 包围盒
- `edge_pair.first` / `second`: 退化边（p1 == p2），表示顶点位置
- `edge_pair.distance()`: 始终为 0

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 grid_x_um/grid_y_um → dbu
4. 执行: region.grid_check(gx_dbu, gy_dbu)
5. 迭代 EdgePairs，提取每个违规的顶点位置（first.p1）
6. 生成报告

## 学术依据

- KLayout Region class (grid_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs class:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair class:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html
- KLayout DRC Reference (grid):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Grid Check:
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
    "GridDRCViolation",
    "GridDRCReport",
    "check_grid",
    "generate_grid_drc_report",
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
            "klayout 未安装，无法执行 GDSII grid 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class GridDRCViolation:
    """单个 grid 违规（R349）。

    表示一个未对齐到网格的顶点。

    Attributes:
        vertex_x_um: 未对齐顶点 X 坐标（μm）。
        vertex_y_um: 未对齐顶点 Y 坐标（μm）。
        grid_x_um: X 方向网格大小（μm）。
        grid_y_um: Y 方向网格大小（μm）。
    """

    vertex_x_um: float
    vertex_y_um: float
    grid_x_um: float
    grid_y_um: float


@dataclass
class GridDRCReport:
    """GDSII grid DRC 检查报告（R349）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        grid_x_um: X 方向网格大小（μm）。
        grid_y_um: Y 方向网格大小（μm）。
        check_type: 检查类型（"grid"）。
        total_violations: 违规总数。
        violations: 违规列表。
        bbox: 所有违规的包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
    """

    input_path: str = ""
    layer: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    grid_x_um: float = 0.0
    grid_y_um: float = 0.0
    check_type: str = "grid"
    total_violations: int = 0
    violations: list[GridDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None


# =============================================================================
# grid 检查主入口
# =============================================================================
def check_grid(
    gds_path: str | Path,
    layer: tuple[int, int],
    grid_x_um: float,
    grid_y_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> GridDRCReport:
    """对 GDSII 指定层执行 grid（网格对齐）检查（R349）。

    用 KLayout `region.grid_check(gx, gy)` 检查多边形顶点是否对齐到
    指定网格。未对齐顶点会产生违规。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        grid_x_um: X 方向网格大小（μm）。
        grid_y_um: Y 方向网格大小（μm）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 保留的最大违规数（防止内存爆炸）。

    Returns:
        GridDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / grid_x_um <= 0 /
            grid_y_um <= 0 / max_violations <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region grid_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")

    if grid_x_um <= 0:
        raise ValueError(
            f"grid_x_um 必须 > 0，得到 {grid_x_um}。"
            f"禁止 fall-back（R03）。"
        )
    if grid_y_um <= 0:
        raise ValueError(
            f"grid_y_um 必须 > 0，得到 {grid_y_um}。"
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

    # 执行 grid 检查
    gx_dbu = int(round(grid_x_um / dbu))
    gy_dbu = int(round(grid_y_um / dbu))
    edge_pairs = r.grid_check(gx_dbu, gy_dbu)

    total = int(edge_pairs.count())
    bbox_db = edge_pairs.bbox()

    violations: list[GridDRCViolation] = []
    for i, ep in enumerate(edge_pairs.each()):
        if i >= max_violations:
            break
        # grid_check 返回退化 EdgePair，first.p1 == first.p2 == 顶点位置
        p = ep.first.p1
        violations.append(GridDRCViolation(
            vertex_x_um=float(int(p.x)) * dbu,
            vertex_y_um=float(int(p.y)) * dbu,
            grid_x_um=grid_x_um,
            grid_y_um=grid_y_um,
        ))

    bbox_um: tuple[tuple[float, float], tuple[float, float]] | None = None
    if total > 0:
        bbox_um = (
            (float(bbox_db.left) * dbu, float(bbox_db.bottom) * dbu),
            (float(bbox_db.right) * dbu, float(bbox_db.top) * dbu),
        )

    logger.info(
        "GDSII grid 检查: %s layer=(%d,%d), grid=(%.4f,%.4f)μm, "
        "violations=%d (返回 %d)",
        in_path, src_layer, src_dt, grid_x_um, grid_y_um,
        total, len(violations),
    )

    return GridDRCReport(
        input_path=str(gds_path),
        layer=(src_layer, src_dt),
        dbu=dbu,
        top_cell_name=top_cell.name,
        grid_x_um=grid_x_um,
        grid_y_um=grid_y_um,
        check_type="grid",
        total_violations=total,
        violations=violations,
        bbox=bbox_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_grid_drc_report(
    gds_path: str | Path,
    layer: tuple[int, int],
    grid_x_um: float,
    grid_y_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """生成 grid DRC 检查报告字符串（R349）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer: 检查层 (layer, datatype)。
        grid_x_um: X 方向网格大小（μm）。
        grid_y_um: Y 方向网格大小（μm）。
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
    report = check_grid(
        gds_path, layer, grid_x_um, grid_y_um,
        top_cell_name, max_violations,
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
    """验证层参数（R349 内部函数）。"""
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
    """获取顶层 cell（R349 内部函数）。"""
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
    """查找层，不存在 raise（R349 内部函数）。"""
    li = ly.find_layer(layer, datatype)
    if li is None:
        raise ValueError(
            f"层 ({layer},{datatype}) 不存在于 {gds_path}（{name}）。"
            f"禁止 fall-back（R03）。"
        )
    return li


def _render_text_report(report: GridDRCReport) -> str:
    """渲染纯文本报告（R349 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII Grid DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"层: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查类型: {report.check_type}")
    lines.append(
        f"网格大小: X={report.grid_x_um:.4f} μm, Y={report.grid_y_um:.4f} μm"
    )
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
            f"  [{i}] 顶点: ({v.vertex_x_um:.4f},{v.vertex_y_um:.4f}) μm "
            f"(网格 {v.grid_x_um:.4f}x{v.grid_y_um:.4f})"
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: GridDRCReport) -> str:
    """渲染 Markdown 报告（R349 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII Grid DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **层**: ({report.layer[0]},{report.layer[1]})")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **检查类型**: {report.check_type}")
    lines.append(
        f"- **网格大小**: X={report.grid_x_um:.4f} μm, "
        f"Y={report.grid_y_um:.4f} μm"
    )
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
    lines.append("| # | 顶点 X (μm) | 顶点 Y (μm) |")
    lines.append("|---|-------------|-------------|")
    for i, v in enumerate(report.violations[:20]):
        lines.append(
            f"| {i} | {v.vertex_x_um:.4f} | {v.vertex_y_um:.4f} |"
        )
    return "\n".join(lines)


def _render_json_report(report: GridDRCReport) -> str:
    """渲染 JSON 报告（R349 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "layer": list(report.layer),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "check_type": report.check_type,
        "grid_x_um": report.grid_x_um,
        "grid_y_um": report.grid_y_um,
        "total_violations": report.total_violations,
        "bbox": (
            [list(report.bbox[0]), list(report.bbox[1])]
            if report.bbox else None
        ),
        "violations": [
            {
                "vertex_x_um": v.vertex_x_um,
                "vertex_y_um": v.vertex_y_um,
                "grid_x_um": v.grid_x_um,
                "grid_y_um": v.grid_y_um,
            }
            for v in report.violations
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
