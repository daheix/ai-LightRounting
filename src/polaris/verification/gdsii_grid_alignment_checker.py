"""GDSII 网格对齐检查器（R325，Grid Alignment Checker）。

检查 GDSII 文件中所有多边形/Box 顶点是否对齐到指定网格（grid），
用于 DRC 网格合规验证。

## 核心概念

- **网格（Grid）**: 制造工艺要求的最小坐标单位（如 5nm grid）
- **On-grid 顶点**: 顶点坐标是 grid 的整数倍
- **Off-grid 顶点**: 顶点坐标不是 grid 的整数倍（DRC 违规）
- **检查范围**: 顶层 cell 递归所有子 cell 实例的 shapes

## 算法

1. 读取 GDSII 文件
2. grid_um → grid_dbu = round(grid_um / dbu)
3. 对每个层:
   - 用 Cell.begin_shapes_rec(li) 递归遍历所有 shapes
   - 对每个 shape:
     - 若是 polygon: 遍历所有顶点，检查 % grid_dbu
     - 若是 box: 检查 4 个角点 % grid_dbu
     - 用 it.trans() 变换顶点到世界坐标（含实例 placement）
4. 收集所有 off-grid 顶点，按层分组报告

## KLayout 0.30.9 API 关键事实（冒烟测试实测）

- Shape.is_polygon() / Shape.is_box() 判断类型
- Shape.polygon() 返回 Polygon 对象
- Polygon.num_points() 返回顶点数
- Polygon.point(i) 返回 Point（dbu 单位）
- Shape.bbox() 返回 Box（dbu 单位，含 left/bottom/right/top）
- Box 矩形存储为 Box（不是 4 点 Polygon）
- RecursiveShapeIterator.trans() 返回累积 ICplxTrans
- 世界坐标顶点 = it.trans() * point

## 学术依据

- KLayout DRC Reference（grid 检查）:
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
- KLayout Polygon class:
  https://www.klayout.org/doc-qt5/code/class_Polygon.html
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Shape class（is_polygon/is_box/polygon）:
  https://www.klayout.org/doc-qt4/code/class_Shape.html
- KLayout RecursiveShapeIterator:
  https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
- KLayout ICplxTrans:
  https://www.klayout.de/doc-qt5/code/class_ICplxTrans.html
- GDSII 坐标系统（dbu/网格）:
  https://en.wikipedia.org/wiki/GDS_File
- Calibre DRC GRID 检查:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK grid 规则:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "GridViolation",
    "GridCheckReport",
    "check_grid_alignment",
    "generate_grid_check_report",
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
            "klayout 未安装，无法执行 GDSII 网格对齐检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class GridViolation:
    """单个网格对齐违规（R325）。

    Attributes:
        layer_name: 层名。
        gds_layer: GDSII 层号。
        gds_datatype: GDSII datatype。
        x_um: 违规顶点 X 坐标（μm）。
        y_um: 违规顶点 Y 坐标（μm）。
        x_off_dbu: X 方向偏移量（dbu，= x_dbu % grid_dbu）。
        y_off_dbu: Y 方向偏移量（dbu）。
        cell_name: 违规 shape 所属 cell 名。
        shape_type: shape 类型（'polygon' / 'box'）。
    """

    layer_name: str
    gds_layer: int
    gds_datatype: int
    x_um: float
    y_um: float
    x_off_dbu: int
    y_off_dbu: int
    cell_name: str
    shape_type: str


@dataclass
class GridCheckReport:
    """GDSII 网格对齐检查报告（R325）。

    Attributes:
        file_path: GDSII 文件路径。
        dbu: 数据库单位（μm）。
        grid_um: 检查网格（μm）。
        grid_dbu: 检查网格（dbu）。
        top_cell_name: 顶层 cell 名。
        violations: 所有 GridViolation 列表。
        total_violations: 违规总数。
        layer_violation_counts: 按层名分组的违规计数。
        total_shapes_checked: 检查的 shape 总数。
    """

    file_path: str
    dbu: float = 0.0
    grid_um: float = 0.0
    grid_dbu: int = 1
    top_cell_name: str = ""
    violations: list[GridViolation] = field(default_factory=list)
    total_violations: int = 0
    layer_violation_counts: dict[str, int] = field(default_factory=dict)
    total_shapes_checked: int = 0


# =============================================================================
# 网格对齐检查
# =============================================================================
def check_grid_alignment(
    gds_path: str | Path,
    grid_um: float = 0.005,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_check: list[str] | None = None,
) -> GridCheckReport:
    """检查 GDSII 文件中所有顶点是否对齐到指定网格（R325）。

    递归遍历顶层 cell 及其所有子 cell 实例的 shapes，检查每个 polygon/box
    的顶点是否对齐到 grid_um 网格。

    Args:
        gds_path: GDSII 文件路径。
        grid_um: 检查网格（μm，必须 > 0，默认 0.005 = 5nm）。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        layers_to_check: 仅检查指定层名（None 检查所有层）。

    Returns:
        GridCheckReport 网格对齐检查报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / grid_um <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout DRC grid check:
      https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
    - KLayout Polygon API:
      https://www.klayout.org/doc-qt5/code/class_Polygon.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if grid_um <= 0:
        raise ValueError(
            f"grid_um 必须 > 0，得到 {grid_um}。"
            f"禁止 fall-back（R03）。"
        )

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    grid_dbu = int(round(grid_um / dbu))
    if grid_dbu < 1:
        raise ValueError(
            f"grid_um={grid_um} μm 小于 dbu={dbu} μm，"
            f"grid_dbu={grid_dbu} < 1，无法检查。"
            f"禁止 fall-back（R03）。"
        )

    if layer_map is None:
        layer_map = _get_default_layer_map()

    top_cell = _get_top_cell(ly, top_cell_name, gds_path)

    # 构造允许的层集合
    allowed_layer_keys: set[tuple[int, int]] | None = None
    if layers_to_check is not None:
        allowed_layer_keys = set()
        for (g, d), name in layer_map.items():
            if name in layers_to_check:
                allowed_layer_keys.add((g, d))

    violations: list[GridViolation] = []
    total_shapes = 0
    layer_violation_counts: dict[str, int] = {}

    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        layer_key = (gds_layer, gds_datatype)
        layer_name = layer_map.get(
            layer_key, f"LAYER_{gds_layer}_{gds_datatype}"
        )

        if allowed_layer_keys is not None and layer_key not in allowed_layer_keys:
            continue

        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            shape = it.shape()
            trans = it.trans()
            cell_name = str(it.cell().name)
            total_shapes += 1

            if shape.is_polygon():
                poly = shape.polygon()
                num_pts = int(poly.num_points())
                for i in range(num_pts):
                    pt = poly.point(i)
                    # 应用累积变换到世界坐标
                    world_pt = trans * pt
                    x_dbu = int(world_pt.x)
                    y_dbu = int(world_pt.y)
                    x_off = x_dbu % grid_dbu
                    y_off = y_dbu % grid_dbu
                    if x_off != 0 or y_off != 0:
                        v = GridViolation(
                            layer_name=layer_name,
                            gds_layer=gds_layer,
                            gds_datatype=gds_datatype,
                            x_um=float(x_dbu) * dbu,
                            y_um=float(y_dbu) * dbu,
                            x_off_dbu=x_off,
                            y_off_dbu=y_off,
                            cell_name=cell_name,
                            shape_type="polygon",
                        )
                        violations.append(v)
                        layer_violation_counts[layer_name] = (
                            layer_violation_counts.get(layer_name, 0) + 1
                        )
            elif shape.is_box():
                box = shape.bbox()
                # box 的 4 个角点
                corners = [
                    (int(box.left), int(box.bottom)),
                    (int(box.right), int(box.bottom)),
                    (int(box.right), int(box.top)),
                    (int(box.left), int(box.top)),
                ]
                for cx, cy in corners:
                    # 应用累积变换
                    world_pt = trans * db.Point(cx, cy)
                    wx = int(world_pt.x)
                    wy = int(world_pt.y)
                    x_off = wx % grid_dbu
                    y_off = wy % grid_dbu
                    if x_off != 0 or y_off != 0:
                        v = GridViolation(
                            layer_name=layer_name,
                            gds_layer=gds_layer,
                            gds_datatype=gds_datatype,
                            x_um=float(wx) * dbu,
                            y_um=float(wy) * dbu,
                            x_off_dbu=x_off,
                            y_off_dbu=y_off,
                            cell_name=cell_name,
                            shape_type="box",
                        )
                        violations.append(v)
                        layer_violation_counts[layer_name] = (
                            layer_violation_counts.get(layer_name, 0) + 1
                        )
            it.next()

    # 排序: gds_layer → gds_datatype → y_um → x_um
    violations.sort(
        key=lambda v: (
            v.gds_layer, v.gds_datatype, v.y_um, v.x_um,
        )
    )

    return GridCheckReport(
        file_path=str(gds_path),
        dbu=dbu,
        grid_um=grid_um,
        grid_dbu=grid_dbu,
        top_cell_name=str(top_cell.name),
        violations=violations,
        total_violations=len(violations),
        layer_violation_counts=layer_violation_counts,
        total_shapes_checked=total_shapes,
    )


def generate_grid_check_report(
    gds_path: str | Path,
    grid_um: float = 0.005,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_check: list[str] | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 网格对齐检查报告（R325）。

    Args:
        gds_path: GDSII 文件路径。
        grid_um: 检查网格（μm）。
        layer_map: 层映射。
        top_cell_name: 指定顶层 cell 名。
        layers_to_check: 仅检查指定层名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式 / 文件无效 / grid_um <= 0。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = check_grid_alignment(
        gds_path,
        grid_um=grid_um,
        layer_map=layer_map,
        top_cell_name=top_cell_name,
        layers_to_check=layers_to_check,
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


# =============================================================================
# 内部辅助函数
# =============================================================================
def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R325 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        return top_cell

    top_cells = [ly.cell(int(ci)) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
        )
    return top_cells[0]


def _render_text_report(report: GridCheckReport) -> str:
    """渲染纯文本报告（R325 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 网格对齐检查报告")
    lines.append("=" * 60)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"grid: {report.grid_um} μm ({report.grid_dbu} dbu)")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"检查 shape 总数: {report.total_shapes_checked}")
    lines.append(f"违规总数: {report.total_violations}")
    lines.append("")
    if report.layer_violation_counts:
        lines.append("-" * 60)
        lines.append("按层分组违规计数:")
        lines.append("-" * 60)
        for layer_name, count in sorted(report.layer_violation_counts.items()):
            lines.append(f"  {layer_name}: {count}")
        lines.append("")
    lines.append("-" * 60)
    lines.append("所有违规:")
    lines.append("-" * 60)
    lines.append(
        f"{'层名':<12} {'GDS':<8} {'X(μm)':>10} {'Y(μm)':>10} "
        f"{'Xoff':>6} {'Yoff':>6} {'cell':<12} {'type':<10}"
    )
    for v in report.violations:
        gds_str = f"{v.gds_layer}/{v.gds_datatype}"
        lines.append(
            f"{v.layer_name:<12} {gds_str:<8} {v.x_um:>10.4f} {v.y_um:>10.4f} "
            f"{v.x_off_dbu:>6} {v.y_off_dbu:>6} {v.cell_name:<12} {v.shape_type:<10}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: GridCheckReport) -> str:
    """渲染 Markdown 报告（R325 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 网格对齐检查报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**grid**: {report.grid_um} μm ({report.grid_dbu} dbu)")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**检查 shape 总数**: {report.total_shapes_checked}")
    lines.append(f"**违规总数**: {report.total_violations}")
    lines.append("")
    if report.layer_violation_counts:
        lines.append("## 按层分组违规计数")
        lines.append("")
        lines.append("| 层名 | 违规数 |")
        lines.append("|------|--------|")
        for layer_name, count in sorted(report.layer_violation_counts.items()):
            lines.append(f"| {layer_name} | {count} |")
        lines.append("")
    lines.append("## 所有违规")
    lines.append("")
    lines.append(
        "| 层名 | GDS 层/datatype | X(μm) | Y(μm) | Xoff(dbu) | "
        "Yoff(dbu) | cell | type |"
    )
    lines.append("|------|-----------------|-------|-------|-----------|"
                 "-----------|------|------|")
    for v in report.violations:
        gds_str = f"{v.gds_layer}/{v.gds_datatype}"
        lines.append(
            f"| {v.layer_name} | {gds_str} | {v.x_um:.4f} | {v.y_um:.4f} | "
            f"{v.x_off_dbu} | {v.y_off_dbu} | {v.cell_name} | {v.shape_type} |"
        )
    return "\n".join(lines)
