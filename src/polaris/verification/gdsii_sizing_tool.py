"""GDSII 层 Sizing 工具（R341，Layer Sizing）。

提供 GDSII 层的 sizing（膨胀/收缩）操作，用于 DRC 规则检查、
掩膜偏置、过孔扩大、线宽补偿等场景。

## 核心概念

- **Sizing（尺寸调整/偏置）**: 将多边形边缘偏移指定距离
  - 正值: 膨胀（向外偏移，图形变大）
  - 负值: 收缩（向内偏移，图形变小）
  - 各向同性: X/Y 方向偏移相同
  - 各向异性: X/Y 方向偏移不同
- **每边偏移**: sizing 参数 d 表示每边的偏移量
  - 矩形 W×H 各向同性 +d → (W+2d)×(H+2d)
  - 矩形 W×H 各向同性 -d → (W-2d)×(H-2d)
- **典型用途**:
  - DRC: width/spacing/enclosing 检查的基础
  - 掩膜偏置: 工艺补偿（OPC 预处理）
  - 过孔扩大: 增大接触面积
  - 线宽补偿: 蚀刻效应补偿

## KLayout 0.30.9 API 关键事实（R341 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.sized(d)`: 各向同性 sizing（dbu 单位，每边偏移 d）
  - 正值膨胀，负值收缩
  - 收缩超过半宽会消失（area=0, count=0）
- `region.sized(dx, dy, mode)`: 各向异性 sizing
  - dx, dy: X/Y 方向每边偏移（dbu）
  - mode=2: 各向异性必须的截止模式
- `region.area()`: 返回面积（dbu²）
- `region.count()`: 返回 polygon 数
- `region.bbox()`: 返回 Box（dbu 单位）
- `top_cell.shapes(li).insert(region)`: 插入 Region 到 layout

## 算法

1. 读取 GDSII
2. 提取 layer 的 Region（递归遍历子 cell）
3. 转换 size_um → dbu（size_dbu = size_um / dbu）
4. 执行 sizing:
   - 各向同性: region.sized(d_dbu)
   - 各向异性: region.sized(dx_dbu, dy_dbu, 2)
5. 将结果插入 layer_result
6. 写出 GDSII

## 学术依据

- KLayout Region overview (Sizing):
  https://klayout.org/klayout-pypi/overview/geometry/regions/
- KLayout Region class (sized method):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout DRC Reference (sized):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html#h2-905
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- KLayout Geometry API:
  https://www.klayout.de/doc-qt5/programming/geometry_api.html
- Calibre DRC Sizing operations:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- Optical Proximity Correction (OPC):
  https://en.wikipedia.org/wiki/Optical_proximity_correction
- Polygon offsetting algorithms:
  https://en.wikipedia.org/wiki/Minkowski_addition

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "SizingReport",
    "size_layer",
    "generate_sizing_report",
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
            "klayout 未安装，无法执行 GDSII sizing。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class SizingReport:
    """GDSII 层 sizing 报告（R341）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        layer: 操作层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        size_x_um: X 方向每边偏移（μm）。
        size_y_um: Y 方向每边偏移（μm）。
        is_isotropic: 是否各向同性（size_x_um == size_y_um）。
        area_before_um2: 操作前面积（μm²）。
        area_after_um2: 操作后面积（μm²）。
        count_before: 操作前 polygon 数。
        count_after: 操作后 polygon 数。
        bbox_before: 操作前 bbox [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
        bbox_after: 操作后 bbox（μm），空为 None。
        top_cell_name: 顶层 cell 名。
    """

    input_path: str = ""
    output_path: str = ""
    layer: tuple[int, int] = (0, 0)
    layer_result: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    size_x_um: float = 0.0
    size_y_um: float = 0.0
    is_isotropic: bool = True
    area_before_um2: float = 0.0
    area_after_um2: float = 0.0
    count_before: int = 0
    count_after: int = 0
    bbox_before: tuple[tuple[float, float], tuple[float, float]] | None = None
    bbox_after: tuple[tuple[float, float], tuple[float, float]] | None = None
    top_cell_name: str = ""


# =============================================================================
# Sizing 主入口
# =============================================================================
def size_layer(
    gds_path: str | Path,
    output_path: str | Path,
    layer: tuple[int, int],
    layer_result: tuple[int, int],
    size_x_um: float,
    size_y_um: float | None = None,
    top_cell_name: str | None = None,
) -> SizingReport:
    """对 GDSII 层执行 sizing（膨胀/收缩）（R341）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        layer: 操作层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        size_x_um: X 方向每边偏移（μm，正值膨胀，负值收缩）。
        size_y_um: Y 方向每边偏移（None = 各向同性 = size_x_um）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。

    Returns:
        SizingReport sizing 报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / 层参数无效 / layer == layer_result /
            size_x_um 或 size_y_um 为 0（无意义）/ top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Region sized: https://klayout.org/klayout-pypi/overview/geometry/regions/
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    src_layer, src_dt = _validate_layer(layer, "layer")
    tgt_layer, tgt_dt = _validate_layer(layer_result, "layer_result")
    if (src_layer, src_dt) == (tgt_layer, tgt_dt):
        raise ValueError(
            f"layer 和 layer_result 不能相同: {(src_layer, src_dt)}。"
            f"禁止 fall-back（R03）。"
        )

    # size_x_um 不能为 0（无意义）
    if size_x_um == 0:
        raise ValueError(
            f"size_x_um 不能为 0（无 sizing 效果）。"
            f"禁止 fall-back（R03）。"
        )
    # 处理 size_y_um
    if size_y_um is None:
        size_y_um = size_x_um
    else:
        if size_y_um == 0:
            raise ValueError(
                f"size_y_um 不能为 0（无 sizing 效果）。"
                f"禁止 fall-back（R03）。"
            )

    is_isotropic = (size_x_um == size_y_um)

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
    li_tgt = ly.layer(tgt_layer, tgt_dt)

    # 提取 Region（递归遍历所有子 cell）
    r = db.Region(top_cell.begin_shapes_rec(li_src))

    # 操作前统计
    area_before_um2 = float(r.area()) * dbu * dbu
    count_before = int(r.count())
    bbox_before: tuple[tuple[float, float], tuple[float, float]] | None = None
    if count_before > 0:
        bbox = r.bbox()
        bbox_before = (
            (float(bbox.left) * dbu, float(bbox.bottom) * dbu),
            (float(bbox.right) * dbu, float(bbox.top) * dbu),
        )

    # 执行 sizing
    # dbu 是 μm/dbu，size_um / dbu = size_dbu
    dx_dbu = int(round(size_x_um / dbu))
    dy_dbu = int(round(size_y_um / dbu))

    if is_isotropic:
        # 各向同性: region.sized(d)
        r_result = r.sized(dx_dbu)
    else:
        # 各向异性: region.sized(dx, dy, mode=2)
        # mode=2 是各向异性 sizing 必须的截止模式
        # 来源: https://klayout.org/klayout-pypi/overview/geometry/regions/
        r_result = r.sized(dx_dbu, dy_dbu, 2)

    # 操作后统计
    area_after_um2 = float(r_result.area()) * dbu * dbu
    count_after = int(r_result.count())
    bbox_after: tuple[tuple[float, float], tuple[float, float]] | None = None
    if count_after > 0:
        bbox = r_result.bbox()
        bbox_after = (
            (float(bbox.left) * dbu, float(bbox.bottom) * dbu),
            (float(bbox.right) * dbu, float(bbox.top) * dbu),
        )

    # 将结果插入 layer_result
    top_cell.shapes(li_tgt).insert(r_result)

    # 写出
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII sizing: %s → %s (%d,%d)→(%d,%d), "
        "dx=%.4fμm, dy=%.4fμm, isotropic=%s, "
        "area_before=%.4fμm², area_after=%.4fμm², "
        "count_before=%d, count_after=%d",
        in_path, out_path,
        src_layer, src_dt, tgt_layer, tgt_dt,
        size_x_um, size_y_um, is_isotropic,
        area_before_um2, area_after_um2,
        count_before, count_after,
    )

    return SizingReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        layer=(src_layer, src_dt),
        layer_result=(tgt_layer, tgt_dt),
        dbu=dbu,
        size_x_um=size_x_um,
        size_y_um=size_y_um,
        is_isotropic=is_isotropic,
        area_before_um2=area_before_um2,
        area_after_um2=area_after_um2,
        count_before=count_before,
        count_after=count_after,
        bbox_before=bbox_before,
        bbox_after=bbox_after,
        top_cell_name=str(top_cell.name),
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_sizing_report(
    gds_path: str | Path,
    output_path: str | Path,
    layer: tuple[int, int],
    layer_result: tuple[int, int],
    size_x_um: float,
    size_y_um: float | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """执行 GDSII sizing 并生成报告字符串（R341）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        layer: 操作层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        size_x_um: X 方向每边偏移（μm）。
        size_y_um: Y 方向每边偏移（None = 各向同性）。
        top_cell_name: 指定顶层 cell 名。
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
    report = size_layer(
        gds_path, output_path, layer, layer_result,
        size_x_um, size_y_um,
        top_cell_name=top_cell_name,
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
    """验证层参数（R341 内部函数）。"""
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
    """获取顶层 cell（R341 内部函数）。"""
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
    """查找层，不存在则 raise（R341 内部函数）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return int(li)
    raise ValueError(
        f"{context} ({layer}, {datatype}) 在文件 {gds_path} 中不存在。"
        f"禁止 fall-back（R03）。"
    )


def _render_text_report(report: SizingReport) -> str:
    """渲染纯文本报告（R341 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 层 Sizing 报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(
        f"layer: ({report.layer[0]},{report.layer[1]})  "
        f"layer_result: ({report.layer_result[0]},{report.layer_result[1]})"
    )
    mode = "各向同性" if report.is_isotropic else "各向异性"
    lines.append(f"模式: {mode}")
    lines.append(
        f"size_x: {report.size_x_um:.6f} μm  "
        f"size_y: {report.size_y_um:.6f} μm"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("操作前统计")
    lines.append("-" * 60)
    lines.append(
        f"  area: {report.area_before_um2:.6f} μm², count: {report.count_before}"
    )
    if report.bbox_before is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox_before
        lines.append(
            f"  bbox: ({xmin:.6f}, {ymin:.6f}) - ({xmax:.6f}, {ymax:.6f}) μm"
        )
    else:
        lines.append("  bbox: (空)")
    lines.append("")
    lines.append("-" * 60)
    lines.append("操作后统计")
    lines.append("-" * 60)
    lines.append(
        f"  area: {report.area_after_um2:.6f} μm², count: {report.count_after}"
    )
    if report.bbox_after is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox_after
        lines.append(
            f"  bbox: ({xmin:.6f}, {ymin:.6f}) - ({xmax:.6f}, {ymax:.6f}) μm"
        )
    else:
        lines.append("  bbox: (空结果，可能收缩消失)")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: SizingReport) -> str:
    """渲染 Markdown 报告（R341 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 层 Sizing 报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(
        f"- **layer**: ({report.layer[0]},{report.layer[1]})"
    )
    lines.append(
        f"- **layer_result**: ({report.layer_result[0]},{report.layer_result[1]})"
    )
    mode = "各向同性" if report.is_isotropic else "各向异性"
    lines.append(f"- **模式**: {mode}")
    lines.append(f"- **size_x**: {report.size_x_um:.6f} μm")
    lines.append(f"- **size_y**: {report.size_y_um:.6f} μm")
    lines.append("")
    lines.append("## 统计对比")
    lines.append("")
    lines.append("| 指标 | 操作前 | 操作后 |")
    lines.append("|------|--------|--------|")
    lines.append(
        f"| 面积 (μm²) | {report.area_before_um2:.6f} | "
        f"{report.area_after_um2:.6f} |"
    )
    lines.append(
        f"| polygon 数 | {report.count_before} | {report.count_after} |"
    )

    def _bbox_str(bbox):
        if bbox is None:
            return "(空)"
        (xmin, ymin), (xmax, ymax) = bbox
        return f"({xmin:.6f}, {ymin:.6f}) - ({xmax:.6f}, {ymax:.6f})"

    lines.append(
        f"| bbox (μm) | {_bbox_str(report.bbox_before)} | "
        f"{_bbox_str(report.bbox_after)} |"
    )
    return "\n".join(lines)


def _render_json_report(report: SizingReport) -> str:
    """渲染 JSON 报告（R341 内部函数）。"""
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
        "output_path": report.output_path,
        "layer": list(report.layer),
        "layer_result": list(report.layer_result),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "size_x_um": report.size_x_um,
        "size_y_um": report.size_y_um,
        "is_isotropic": report.is_isotropic,
        "area_before_um2": report.area_before_um2,
        "area_after_um2": report.area_after_um2,
        "count_before": report.count_before,
        "count_after": report.count_after,
        "bbox_before": _bbox_dict(report.bbox_before),
        "bbox_after": _bbox_dict(report.bbox_after),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
