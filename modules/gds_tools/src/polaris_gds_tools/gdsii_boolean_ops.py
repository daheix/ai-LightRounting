"""GDSII 布尔运算工具（R340，Boolean Operations）。

提供 GDSII 层间布尔运算（AND/OR/NOT/XOR），用于 DRC 规则检查、
LVS 网络提取、版图对比、掩膜合成等场景。

## 核心概念

- **布尔运算**: 两个图层的几何运算
  - AND（&）: 交集，两图层重叠部分
  - OR（|）: 并集，两图层合并
  - NOT（-）: 差集，A 减去 B 的部分
  - XOR（^）: 对称差，只在其中一个图层中的部分
- **db.Region**: KLayout 的多边形集合，支持布尔运算
- **典型用途**:
  - DRC: 检查间距/宽度/包围规则
  - LVS: 提取网络连接关系
  - 版图对比: XOR 两个版本找差异
  - 掩膜合成: OR 合并多个层

## KLayout 0.30.9 API 关键事实（R340 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 提取 Region
  - 递归遍历所有子 cell 的 shapes
- `r1 & r2`: AND 交集
- `(r1 + r2).merged()`: OR 并集（+ 合并，merged 去重叠）
- `r1 - r2`: NOT 差集
- `r1 ^ r2`: XOR 对称差
- `region.area()`: 返回面积（dbu²，int）
- `region.count()`: 返回 polygon 数（int）
- `region.bbox()`: 返回 Box（dbu 单位）
- `top_cell.shapes(layer_index).insert(region)`: 插入 Region 到 layout

## 算法

1. 读取 GDSII
2. 获取 layer_a 和 layer_b 的 Region
3. 执行布尔运算:
   - and: r_a & r_b
   - or: (r_a + r_b).merged()
   - not: r_a - r_b
   - xor: r_a ^ r_b
4. 将结果插入 layer_result
5. 写出 GDSII

## 学术依据

- KLayout Region overview:
  https://klayout.org/klayout-pypi/overview/geometry/regions/
- KLayout Region class:
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout DRC Reference (Boolean operations):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- gdsfactory boolean_klayout:
  https://gdsfactory.github.io/gdsfactory7/_modules/gdsfactory/geometry/boolean_klayout.html
- phidl kl_boolean:
  https://phidl.readthedocs.io/en/dev/API.html
- Boolean operations on polygons:
  https://en.wikipedia.org/wiki/Boolean_operations_on_polygons
- Calibre DRC Boolean operations:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- KLayout Geometry API:
  https://www.klayout.de/doc-qt5/programming/geometry_api.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "BooleanReport",
    "boolean_operation",
    "generate_boolean_report",
    "VALID_OPERATIONS",
]

VALID_OPERATIONS = ("and", "or", "not", "xor")


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 布尔运算。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class BooleanReport:
    """GDSII 布尔运算报告（R340）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        operation: 布尔运算类型（'and' / 'or' / 'not' / 'xor'）。
        layer_a: 操作数 A 层 (layer, datatype)。
        layer_b: 操作数 B 层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        area_a_um2: 操作数 A 面积（μm²）。
        area_b_um2: 操作数 B 面积（μm²）。
        area_result_um2: 结果面积（μm²）。
        count_a: 操作数 A polygon 数。
        count_b: 操作数 B polygon 数。
        count_result: 结果 polygon 数。
        bbox_result: 结果 bbox [(xmin, ymin), (xmax, ymax)]（μm），空结果为 None。
        top_cell_name: 顶层 cell 名。
    """

    input_path: str = ""
    output_path: str = ""
    operation: str = ""
    layer_a: tuple[int, int] = (0, 0)
    layer_b: tuple[int, int] = (0, 0)
    layer_result: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    area_a_um2: float = 0.0
    area_b_um2: float = 0.0
    area_result_um2: float = 0.0
    count_a: int = 0
    count_b: int = 0
    count_result: int = 0
    bbox_result: tuple[tuple[float, float], tuple[float, float]] | None = None
    top_cell_name: str = ""


# =============================================================================
# 布尔运算主入口
# =============================================================================
def boolean_operation(
    gds_path: str | Path,
    output_path: str | Path,
    operation: str,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    layer_result: tuple[int, int],
    top_cell_name: str | None = None,
) -> BooleanReport:
    """执行 GDSII 层间布尔运算（R340）。

    对同一 GDSII 文件的 layer_a 和 layer_b 执行布尔运算，
    将结果写入 layer_result。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        operation: 布尔运算类型（'and' / 'or' / 'not' / 'xor'）。
        layer_a: 操作数 A 层 (layer, datatype)。
        layer_b: 操作数 B 层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。

    Returns:
        BooleanReport 布尔运算报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / operation 不支持 / 层参数无效 /
            layer_a == layer_b（and/or/xor 自身无意义，not 会清零）/
            top_cell_name 不存在 / 无顶层 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Region: https://klayout.org/klayout-pypi/overview/geometry/regions/
    - KLayout DRC Boolean: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    db = _import_klayout_db()
    in_path, out_path, op, layers = _validate_boolean_params(
        gds_path, output_path, operation, layer_a, layer_b, layer_result
    )
    la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt = layers
    ly, dbu, top_cell, li_a, li_b, li_r = _setup_boolean_layout(
        db, in_path, gds_path, top_cell_name,
        la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt,
    )
    r_result, op_stats, bbox_result = _compute_boolean_result(
        db, top_cell, op, li_a, li_b, dbu
    )
    area_a_um2, area_b_um2, count_a, count_b, area_result_um2, count_result = op_stats
    top_cell.shapes(li_r).insert(r_result)
    _write_boolean_gdsii(ly, out_path, output_path)
    logger.info(
        "GDSII 布尔运算 %s: %s → %s (%d,%d)&(%d,%d)→(%d,%d), "
        "area_a=%.4f μm², area_b=%.4f μm², area_result=%.4f μm², "
        "count_result=%d",
        op, in_path, out_path,
        la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt,
        area_a_um2, area_b_um2, area_result_um2, count_result,
    )
    return BooleanReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        operation=op,
        layer_a=(la_layer, la_dt),
        layer_b=(lb_layer, lb_dt),
        layer_result=(lr_layer, lr_dt),
        dbu=dbu,
        area_a_um2=area_a_um2,
        area_b_um2=area_b_um2,
        area_result_um2=area_result_um2,
        count_a=count_a,
        count_b=count_b,
        count_result=count_result,
        bbox_result=bbox_result,
        top_cell_name=str(top_cell.name),
    )


def _validate_boolean_params(
    gds_path, output_path, operation, layer_a, layer_b, layer_result,
) -> tuple:
    """校验 boolean_operation 入参（R340 内部辅助，R03 禁止 fall-back）。

    Returns:
        (in_path, out_path, op, (la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt))。
    """
    in_path = Path(gds_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    op = operation.lower()
    if op not in VALID_OPERATIONS:
        raise ValueError(
            f"不支持的 operation: {operation}。"
            f"支持: {VALID_OPERATIONS}。禁止 fall-back（R03）。"
        )
    la_layer, la_dt = _validate_layer(layer_a, "layer_a")
    lb_layer, lb_dt = _validate_layer(layer_b, "layer_b")
    lr_layer, lr_dt = _validate_layer(layer_result, "layer_result")
    # and/or/xor 自身无意义，not 会清零
    if (la_layer, la_dt) == (lb_layer, lb_dt):
        raise ValueError(
            f"layer_a 和 layer_b 不能相同: {(la_layer, la_dt)}。"
            f"禁止 fall-back（R03）。"
        )
    # 结果层不能等于操作数层（避免覆盖）
    if (lr_layer, lr_dt) == (la_layer, la_dt):
        raise ValueError(
            f"layer_result 不能等于 layer_a: {(lr_layer, lr_dt)}。"
            f"禁止 fall-back（R03）。"
        )
    if (lr_layer, lr_dt) == (lb_layer, lb_dt):
        raise ValueError(
            f"layer_result 不能等于 layer_b: {(lr_layer, lr_dt)}。"
            f"禁止 fall-back（R03）。"
        )
    return in_path, out_path, op, (la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt)


def _setup_boolean_layout(
    db, in_path, gds_path, top_cell_name,
    la_layer, la_dt, lb_layer, lb_dt, lr_layer, lr_dt,
) -> tuple:
    """读取 GDSII + 定位顶层 cell + 查找/创建层（R340 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly, dbu, top_cell, li_a, li_b, li_r)。

    来源: KLayout Region https://klayout.org/klayout-pypi/overview/geometry/regions/
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
    li_a = _find_or_raise_layer(ly, la_layer, la_dt, gds_path, "layer_a")
    li_b = _find_or_raise_layer(ly, lb_layer, lb_dt, gds_path, "layer_b")
    li_r = ly.layer(lr_layer, lr_dt)
    return ly, dbu, top_cell, li_a, li_b, li_r


def _compute_boolean_result(db, top_cell, op, li_a, li_b, dbu) -> tuple:
    """提取 Region、执行布尔运算、计算统计（R340 内部辅助）。

    Returns:
        (r_result, (area_a_um2, area_b_um2, count_a, count_b,
                    area_result_um2, count_result), bbox_result)。

    来源: KLayout DRC Boolean
        https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    # db.Region(top_cell.begin_shapes_rec(layer_index)) 递归遍历所有子 cell
    r_a = db.Region(top_cell.begin_shapes_rec(li_a))
    r_b = db.Region(top_cell.begin_shapes_rec(li_b))
    area_a_um2 = float(r_a.area()) * dbu * dbu
    area_b_um2 = float(r_b.area()) * dbu * dbu
    count_a = int(r_a.count())
    count_b = int(r_b.count())
    r_result = _apply_boolean_operator(db, op, r_a, r_b)
    area_result_um2 = float(r_result.area()) * dbu * dbu
    count_result = int(r_result.count())
    bbox_result = _compute_result_bbox(r_result, dbu, count_result)
    op_stats = (area_a_um2, area_b_um2, count_a, count_b,
                area_result_um2, count_result)
    return r_result, op_stats, bbox_result


def _apply_boolean_operator(db, op: str, r_a, r_b):
    """根据 op 执行对应布尔运算（R340 内部辅助）。

    来源: Boolean operations on polygons
        https://en.wikipedia.org/wiki/Boolean_operations_on_polygons
    """
    if op == "and":
        return r_a & r_b
    if op == "or":
        # OR: + 合并，merged 去重叠
        return (r_a + r_b).merged()
    if op == "not":
        return r_a - r_b
    # xor
    return r_a ^ r_b


def _compute_result_bbox(r_result, dbu: float, count_result: int):
    """计算结果 Region 的 bbox（R340 内部辅助）。"""
    if count_result <= 0:
        return None  # 合法：空输入空输出，无结果多边形则无 bbox
    bbox = r_result.bbox()
    return (
        (float(bbox.left) * dbu, float(bbox.bottom) * dbu),
        (float(bbox.right) * dbu, float(bbox.top) * dbu),
    )


def _write_boolean_gdsii(ly, out_path, output_path) -> None:
    """写出布尔运算结果 GDSII（R340 内部辅助，R03 禁止 fall-back）。"""
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e


# =============================================================================
# 报告生成
# =============================================================================
def generate_boolean_report(
    gds_path: str | Path,
    output_path: str | Path,
    operation: str,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    layer_result: tuple[int, int],
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """执行 GDSII 布尔运算并生成报告字符串（R340）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        operation: 布尔运算类型（'and' / 'or' / 'not' / 'xor'）。
        layer_a: 操作数 A 层 (layer, datatype)。
        layer_b: 操作数 B 层 (layer, datatype)。
        layer_result: 结果层 (layer, datatype)。
        top_cell_name: 指定顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / operation 无效 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = boolean_operation(
        gds_path, output_path, operation,
        layer_a, layer_b, layer_result,
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
    """验证层参数（R340 内部函数）。

    Args:
        layer: (layer, datatype) 元组。
        context: 错误消息上下文。

    Returns:
        验证后的 (layer, datatype)。

    Raises:
        ValueError: 格式无效 / layer/datatype 超范围。
    """
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
    """获取顶层 cell（R340 内部函数）。"""
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
    """查找层，不存在则 raise（R340 内部函数）。"""
    # 遍历所有 layer_index 找匹配的 (layer, datatype)
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return int(li)
    raise ValueError(
        f"{context} ({layer}, {datatype}) 在文件 {gds_path} 中不存在。"
        f"禁止 fall-back（R03）。"
    )


def _render_text_report(report: BooleanReport) -> str:
    """渲染纯文本报告（R340 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 布尔运算报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"操作: {report.operation.upper()}")
    lines.append(
        f"layer_a: ({report.layer_a[0]},{report.layer_a[1]})  "
        f"layer_b: ({report.layer_b[0]},{report.layer_b[1]})  "
        f"layer_result: ({report.layer_result[0]},{report.layer_result[1]})"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("操作数统计")
    lines.append("-" * 60)
    lines.append(
        f"  A ({report.layer_a[0]},{report.layer_a[1]}): "
        f"area={report.area_a_um2:.6f} μm², count={report.count_a}"
    )
    lines.append(
        f"  B ({report.layer_b[0]},{report.layer_b[1]}): "
        f"area={report.area_b_um2:.6f} μm², count={report.count_b}"
    )
    lines.append("")
    lines.append("-" * 60)
    lines.append("结果统计")
    lines.append("-" * 60)
    lines.append(
        f"  结果 ({report.layer_result[0]},{report.layer_result[1]}): "
        f"area={report.area_result_um2:.6f} μm², count={report.count_result}"
    )
    if report.bbox_result is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox_result
        lines.append(
            f"  bbox: ({xmin:.6f}, {ymin:.6f}) - ({xmax:.6f}, {ymax:.6f}) μm"
        )
    else:
        lines.append("  bbox: (空结果)")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: BooleanReport) -> str:
    """渲染 Markdown 报告（R340 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 布尔运算报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **操作**: `{report.operation.upper()}`")
    lines.append(
        f"- **layer_a**: ({report.layer_a[0]},{report.layer_a[1]})"
    )
    lines.append(
        f"- **layer_b**: ({report.layer_b[0]},{report.layer_b[1]})"
    )
    lines.append(
        f"- **layer_result**: ({report.layer_result[0]},{report.layer_result[1]})"
    )
    lines.append("")
    lines.append("## 操作数统计")
    lines.append("")
    lines.append("| 操作数 | 层 | 面积 (μm²) | polygon 数 |")
    lines.append("|--------|----|------------|------------|")
    lines.append(
        f"| A | ({report.layer_a[0]},{report.layer_a[1]}) | "
        f"{report.area_a_um2:.6f} | {report.count_a} |"
    )
    lines.append(
        f"| B | ({report.layer_b[0]},{report.layer_b[1]}) | "
        f"{report.area_b_um2:.6f} | {report.count_b} |"
    )
    lines.append("")
    lines.append("## 结果统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(
        f"| 结果层 | ({report.layer_result[0]},{report.layer_result[1]}) |"
    )
    lines.append(f"| 结果面积 (μm²) | {report.area_result_um2:.6f} |")
    lines.append(f"| 结果 polygon 数 | {report.count_result} |")
    if report.bbox_result is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox_result
        lines.append(
            f"| 结果 bbox (μm) | ({xmin:.6f}, {ymin:.6f}) - "
            f"({xmax:.6f}, {ymax:.6f}) |"
        )
    else:
        lines.append("| 结果 bbox | (空结果) |")
    return "\n".join(lines)


def _render_json_report(report: BooleanReport) -> str:
    """渲染 JSON 报告（R340 内部函数）。"""
    import json
    bbox_data = None
    if report.bbox_result is not None:
        (xmin, ymin), (xmax, ymax) = report.bbox_result
        bbox_data = {
            "xmin_um": xmin, "ymin_um": ymin,
            "xmax_um": xmax, "ymax_um": ymax,
        }
    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "operation": report.operation,
        "layer_a": list(report.layer_a),
        "layer_b": list(report.layer_b),
        "layer_result": list(report.layer_result),
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "area_a_um2": report.area_a_um2,
        "area_b_um2": report.area_b_um2,
        "area_result_um2": report.area_result_um2,
        "count_a": report.count_a,
        "count_b": report.count_b,
        "count_result": report.count_result,
        "bbox_result": bbox_data,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
