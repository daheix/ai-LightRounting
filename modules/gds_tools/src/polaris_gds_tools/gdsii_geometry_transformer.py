"""GDSII 几何变换工具（R324，Geometry Transformer）。

对 GDSII 文件应用统一几何变换（平移/旋转/镜像/缩放），输出新的 GDSII 文件。
用于设计复用、对齐、坐标系转换。

## 核心概念

- **几何变换**: 仿射变换，含平移/旋转/镜像/缩放
- **应用范围**: 顶层 cell 的所有内容（含递归子 cell 实例的 placement）
- **变换顺序**（KLayout 约定，与 GDSII/OASIS 一致）:
  1. 镜像 x 轴（可选）
  2. 旋转
  3. 缩放
  4. 平移
- **原地 vs 输出**: 读取源文件 → 应用变换 → 写出新文件（不修改源文件）

## 算法

1. 读取 GDSII 文件
2. 构造 `db.DCplxTrans(mag, rot, mirr, x, y)` 变换对象
3. 对顶层 cell 调用 `Cell.transform(trans)`（KLayout 0.30.9 实测 OK）
   - 这会变换 cell 自己的 shapes
   - 同时调整子 cell 实例的 placement（递归传播）
4. 写出新的 GDSII 文件
5. 返回变换报告（含原 bbox 和新 bbox 对比）

## KLayout 0.30.9 API 关键事实（冒烟测试实测）

- `db.DCplxTrans(mag, rot, mirr, x, y)`: 复杂变换构造器
  - mag: 缩放因子（1.0 = 不缩放）
  - rot: 旋转角度（度，逆时针正方向）
  - mirr: 是否镜像 x 轴（bool）
  - x, y: 平移（μm）
- `Cell.transform(trans)`: 原地变换 cell 内容（含子 cell 实例 placement）
- 变换自动应用到所有层（polygons + texts + instances）
- 变换后写入 GDSII，再读取仍保持结果

## 学术依据

- KLayout Transformations（DCplxTrans / Cell.transform）:
  https://klayout.org/downloads/master/doc-qt5/about/transformations.html
- KLayout Transformations overview（DCplxTrans/CplxTrans）:
  https://klayout.org/klayout-pypi/overview/transformations/
- KLayout Geometry API（Cell.transform）:
  https://klayout.org/downloads/master/doc-qt5/programming/geometry_api.html
- KLayout DCplxTrans class:
  https://www.klayout.de/doc-qt5/code/class_DCplxTrans.html
- KLayout Cell class（transform 方法）:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- GDSII STRANS/ANGLE/MAG fields（变换标准）:
  https://en.wikipedia.org/wiki/GDS_File
- KLayout Nuts and Bolts 示例（ICplxTrans 应用）:
  https://klayout.org/klayout-pypi/examples/nuts_and_bolts/
- Foley & van Dam, "Computer Graphics: Principles and Practice"
  （仿射变换数学基础）: https://en.wikipedia.org/wiki/Affine_transformation

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris_gds_tools._common import get_default_layer_map as _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "TransformParams",
    "TransformReport",
    "transform_gdsii_geometry",
    "generate_transform_report",
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
            "klayout 未安装，无法执行 GDSII 几何变换。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class TransformParams:
    """几何变换参数（R324）。

    变换组合顺序（KLayout 约定）:
    1. 镜像 x 轴（若 mirror_x=True）
    2. 旋转 rotate_deg 度（逆时针）
    3. 缩放 scale 倍
    4. 平移 (translate_x_um, translate_y_um) μm

    Attributes:
        translate_x_um: X 平移（μm）。
        translate_y_um: Y 平移（μm）。
        rotate_deg: 旋转角度（度，逆时针正方向）。
        mirror_x: 是否镜像 x 轴（True=沿 x 轴翻转）。
        scale: 缩放因子（必须 > 0）。
    """

    translate_x_um: float = 0.0
    translate_y_um: float = 0.0
    rotate_deg: float = 0.0
    mirror_x: bool = False
    scale: float = 1.0


@dataclass
class TransformReport:
    """GDSII 几何变换报告（R324）。

    Attributes:
        input_path: 输入 GDSII 路径。
        output_path: 输出 GDSII 路径。
        top_cell_name: 顶层 cell 名。
        dbu: 数据库单位（μm）。
        params: 变换参数。
        original_bbox: 原 bbox (xmin, ymin, xmax, ymax) μm。
        transformed_bbox: 变换后 bbox (xmin, ymin, xmax, ymax) μm。
        transform_str: KLayout 变换字符串表示（如 "r90 *2 100,50"）。
    """

    input_path: str
    output_path: str
    top_cell_name: str = ""
    dbu: float = 0.0
    params: TransformParams = field(default_factory=TransformParams)
    original_bbox: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0,
    )
    transformed_bbox: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0,
    )
    transform_str: str = ""


# =============================================================================
# 几何变换
# =============================================================================
def transform_gdsii_geometry(
    input_path: str | Path,
    output_path: str | Path,
    params: TransformParams | None = None,
    top_cell_name: str | None = None,
) -> TransformReport:
    """对 GDSII 文件应用几何变换（R324）。

    读取输入 GDSII，对顶层 cell 应用统一变换（平移/旋转/镜像/缩放），
    写出新的 GDSII 文件。不修改输入文件。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        params: 变换参数（None 表示无变换，相当于拷贝）。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。

    Returns:
        TransformReport 变换报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / scale <= 0 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Cell.transform:
      https://www.klayout.org/doc-qt5/code/class_Cell.html
    - KLayout DCplxTrans:
      https://www.klayout.de/doc-qt5/code/class_DCplxTrans.html
    """
    db = _import_klayout_db()
    in_path = Path(input_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {input_path}")
    if params is None:
        params = TransformParams()
    if params.scale <= 0:
        raise ValueError(
            f"scale 必须 > 0，得到 {params.scale}。"
            f"禁止 fall-back（R03）。"
        )

    # 读取输入文件
    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取输入文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, input_path)

    # 计算原 bbox（含所有递归子 cell 实例的 bbox）
    # 注意: Cell.bbox() 只返回 cell 自身 shapes 的 bbox，不含子实例。
    # 必须用 begin_shapes_rec 遍历所有 shapes（含递归子实例）计算完整 bbox。
    # 来源: https://www.klayout.org/doc-qt4/code/class_Cell.html
    orig_bbox = _compute_full_bbox(top_cell, ly, dbu)

    # 构造 DCplxTrans 变换对象
    # db.DCplxTrans(mag, rot, mirr, x, y) - μm 单位
    # 来源: https://www.klayout.de/doc-qt5/code/class_DCplxTrans.html
    trans = db.DCplxTrans(
        params.scale,
        params.rotate_deg,
        params.mirror_x,
        params.translate_x_um,
        params.translate_y_um,
    )

    # 应用变换到顶层 cell（原地修改）
    # Cell.transform 递归传播到子 cell 实例的 placement
    # 同时变换 cell 自己的 shapes（polygons + texts）
    top_cell.transform(trans)

    # 计算变换后 bbox（含所有递归子 cell 实例）
    new_bbox = _compute_full_bbox(top_cell, ly, dbu)

    # 写出新的 GDSII 文件
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出输出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII 几何变换: %s → %s (transform=%s)",
        in_path, out_path, str(trans),
    )

    return TransformReport(
        input_path=str(input_path),
        output_path=str(output_path),
        top_cell_name=str(top_cell.name),
        dbu=dbu,
        params=params,
        original_bbox=orig_bbox,
        transformed_bbox=new_bbox,
        transform_str=str(trans),
    )


def generate_transform_report(
    input_path: str | Path,
    output_path: str | Path,
    params: TransformParams | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 几何变换报告（R324）。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        params: 变换参数。
        top_cell_name: 指定顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 不支持的格式 / 文件无效 / scale <= 0。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = transform_gdsii_geometry(
        input_path,
        output_path,
        params=params,
        top_cell_name=top_cell_name,
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
    """获取顶层 cell（R324 内部函数）。"""
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


def _compute_full_bbox(
    top_cell, ly, dbu: float
) -> tuple[float, float, float, float]:
    """计算 cell 的完整 bbox（含所有递归子 cell 实例）。

    遍历所有层的所有 shapes（用 begin_shapes_rec 递归迭代器），
    收集 bbox 的最小外接矩形。

    注意: Cell.bbox() 只返回 cell 自身 shapes 的 bbox，不含子实例。
    本函数用 RecursiveShapeIterator 遍历所有 shapes（含递归子实例）。

    关键: shape.bbox() 返回 cell-local 坐标（不含实例 placement 变换），
    必须用 it.trans() 获取累积变换并应用到 shape.bbox() 才能得到世界坐标。

    Args:
        top_cell: 顶层 Cell 对象。
        ly: Layout 对象。
        dbu: 数据库单位（μm）。

    Returns:
        (xmin_um, ymin_um, xmax_um, ymax_um) μm。
        若无任何 shape，返回 (0, 0, 0, 0)。

    来源:
    - KLayout Cell.begin_shapes_rec:
      https://www.klayout.org/doc-qt4/code/class_Cell.html
    - KLayout RecursiveShapeIterator（iter_trans / trans）:
      https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
    - KLayout ICplxTrans:
      https://www.klayout.de/doc-qt5/code/class_ICplxTrans.html
    """
    min_x = None
    min_y = None
    max_x = None
    max_y = None

    for li in ly.layer_indices():
        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            shape = it.shape()
            # shape.bbox() 返回 cell-local 坐标（dbu）
            # 来源: https://www.klayout.org/doc-qt4/code/class_Shape.html
            local_box = shape.bbox()
            if not local_box.empty():
                # it.trans() 返回当前累积的 ICplxTrans（dbu → dbu）
                # 应用变换得到世界坐标的 dbu bbox
                # 来源: https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
                world_box = it.trans() * local_box
                left = float(world_box.left) * dbu
                bottom = float(world_box.bottom) * dbu
                right = float(world_box.right) * dbu
                top = float(world_box.top) * dbu
                if min_x is None or left < min_x:
                    min_x = left
                if min_y is None or bottom < min_y:
                    min_y = bottom
                if max_x is None or right > max_x:
                    max_x = right
                if max_y is None or top > max_y:
                    max_y = top
            it.next()

    if min_x is None:
        return (0.0, 0.0, 0.0, 0.0)
    return (min_x, min_y, max_x, max_y)


def _render_text_report(report: TransformReport) -> str:
    """渲染纯文本报告（R324 内部函数）。"""
    p = report.params
    ox_min, oy_min, ox_max, oy_max = report.original_bbox
    nx_min, ny_min, nx_max, ny_max = report.transformed_bbox
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 几何变换报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"KLayout 变换: {report.transform_str}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("变换参数:")
    lines.append("-" * 60)
    lines.append(f"  平移 (x, y): ({p.translate_x_um}, {p.translate_y_um}) μm")
    lines.append(f"  旋转角度: {p.rotate_deg} 度")
    lines.append(f"  镜像 x 轴: {p.mirror_x}")
    lines.append(f"  缩放因子: {p.scale}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("包围盒对比 (μm):")
    lines.append("-" * 60)
    lines.append(
        f"  原始:   ({ox_min:.3f}, {oy_min:.3f}) - "
        f"({ox_max:.3f}, {oy_max:.3f})"
    )
    lines.append(
        f"  变换后: ({nx_min:.3f}, {ny_min:.3f}) - "
        f"({nx_max:.3f}, {ny_max:.3f})"
    )
    orig_w = ox_max - ox_min
    orig_h = oy_max - oy_min
    new_w = nx_max - nx_min
    new_h = ny_max - ny_min
    lines.append(f"  原始尺寸: {orig_w:.3f} × {orig_h:.3f} μm²")
    lines.append(f"  变换后尺寸: {new_w:.3f} × {new_h:.3f} μm²")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: TransformReport) -> str:
    """渲染 Markdown 报告（R324 内部函数）。"""
    p = report.params
    ox_min, oy_min, ox_max, oy_max = report.original_bbox
    nx_min, ny_min, nx_max, ny_max = report.transformed_bbox
    lines: list[str] = []
    lines.append("# GDSII 几何变换报告")
    lines.append("")
    lines.append(f"**输入文件**: `{report.input_path}`")
    lines.append(f"**输出文件**: `{report.output_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**KLayout 变换**: `{report.transform_str}`")
    lines.append("")
    lines.append("## 变换参数")
    lines.append("")
    lines.append("| 参数 | 值 |")
    lines.append("|------|------|")
    lines.append(
        f"| 平移 (x, y) μm | ({p.translate_x_um}, {p.translate_y_um}) |"
    )
    lines.append(f"| 旋转角度 (度) | {p.rotate_deg} |")
    lines.append(f"| 镜像 x 轴 | {p.mirror_x} |")
    lines.append(f"| 缩放因子 | {p.scale} |")
    lines.append("")
    lines.append("## 包围盒对比 (μm)")
    lines.append("")
    lines.append("| 项 | xmin | ymin | xmax | ymax |")
    lines.append("|----|------|------|------|------|")
    lines.append(
        f"| 原始 | {ox_min:.3f} | {oy_min:.3f} | "
        f"{ox_max:.3f} | {oy_max:.3f} |"
    )
    lines.append(
        f"| 变换后 | {nx_min:.3f} | {ny_min:.3f} | "
        f"{nx_max:.3f} | {ny_max:.3f} |"
    )
    lines.append("")
    orig_w = ox_max - ox_min
    orig_h = oy_max - oy_min
    new_w = nx_max - nx_min
    new_h = ny_max - ny_min
    lines.append(
        f"- 原始尺寸: **{orig_w:.3f} × {orig_h:.3f}** μm²"
    )
    lines.append(
        f"- 变换后尺寸: **{new_w:.3f} × {new_h:.3f}** μm²"
    )
    return "\n".join(lines)
