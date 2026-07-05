"""GDSII 区域裁剪工具（R327，GDSII Clip/Crop Tool）。

从大版图中裁剪指定矩形区域内的图形，生成新的 GDSII 文件。
用于版图分区检查、局部 DRC、区域提取等场景。

## 核心概念

- **裁剪框（Clip Box）**: 矩形区域 (left, bottom, right, top)，微米单位
- **层次化裁剪**: KLayout Layout.clip() 保留原层次结构（效率高）
- **几何裁剪**: 跨越裁剪框边界的图形在边界处被切断，只保留框内部分
- **多区域裁剪**: Layout.multi_clip() 一次裁剪多个框，生成多个 cell

## 算法

1. 读取 GDSII 文件
2. 将裁剪框 μm → dbu（整数单位，KLayout clip 要求）
3. 验证裁剪框有效性（left < right, bottom < top）
4. 调用 Layout.clip(top_cell_index, box) 层次化裁剪
5. 删除原 top cell，将裁剪后的新 cell 重命名为友好名
6. 写出 GDSII 文件
7. 统计裁剪前后 shapes 数

## KLayout 0.30.9 API 关键事实（冒烟测试实测）

- Layout.clip(cell_index, box) -> new_cell_index: 层次化裁剪
  - box 必须是 db.Box（整数 dbu 单位）
  - 返回新 cell index，新 cell 名为 "原名$N"
  - 保留层次结构，跨边界图形被几何切断
  - 来源: https://klayout.org/klayout-pypi/examples/clip/
- Layout.multi_clip(cell_index, [box1, box2, ...]) -> [ci1, ci2, ...]
  - 一次裁剪多个框，返回 cell index 列表
- Cell.cell_index(): 返回 cell index（方法）
- Cell.bbox(): 返回 cell 的 bbox（dbu 单位）
- Cell.write(path): 写出单个 cell 为 GDSII
- Layout.delete_cell(cell_index): 删除 cell
- Cell.name = "NEW": 重命名 cell

## 学术依据

- KLayout Layout.clip:
  https://klayout.org/doc-qt5/code/class_Layout.html#method33
- KLayout Layout.multi_clip:
  https://klayout.org/doc-qt5/code/class_Layout.html#method98
- KLayout clip 示例:
  https://klayout.org/klayout-pypi/examples/clip/
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- Calibre clip 模式:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK 区域提取:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "ClipReport",
    "clip_gdsii",
    "multi_clip_gdsii",
    "generate_clip_report",
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
            "klayout 未安装，无法执行 GDSII 区域裁剪。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class ClipReport:
    """GDSII 区域裁剪报告（R327）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        dbu: 数据库单位（μm）。
        top_cell_name: 裁剪的源顶层 cell 名。
        clip_box_um: 裁剪框 (left, bottom, right, top) μm。
        clipped_cell_name: 裁剪后新 cell 名。
        shapes_before: 裁剪前 top cell 递归 shape 数。
        shapes_after: 裁剪后新 cell 递归 shape 数。
        bbox_before_um: 裁剪前 top cell bbox (l,b,r,t) μm。
        bbox_after_um: 裁剪后新 cell bbox (l,b,r,t) μm。
    """

    input_path: str
    output_path: str
    dbu: float = 0.0
    top_cell_name: str = ""
    clip_box_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    clipped_cell_name: str = ""
    shapes_before: int = 0
    shapes_after: int = 0
    bbox_before_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    bbox_after_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


def _bbox_to_um(bbox, dbu: float) -> tuple[float, float, float, float]:
    """将 KLayout dbu bbox 转换为 μm 元组 (left, bottom, right, top)。"""
    return (
        float(bbox.left) * dbu,
        float(bbox.bottom) * dbu,
        float(bbox.right) * dbu,
        float(bbox.top) * dbu,
    )


def _build_box_dbu(db, left: float, bottom: float, right: float, top: float, dbu: float):
    """构造 dbu 整数单位的 KLayout Box。"""
    return db.Box(
        int(round(left / dbu)),
        int(round(bottom / dbu)),
        int(round(right / dbu)),
        int(round(top / dbu)),
    )


def _read_gdsii_layout(db, gds_path):
    """读取 GDSII 文件为 KLayout Layout（失败 raise RuntimeError，R03）。"""
    ly = db.Layout()
    try:
        ly.read(str(gds_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    return ly


def _do_clip_operation(
    ly, top_cell, box_dbu, dbu, out_path,
    original_name, clipped_cell_name, clip_box_um,
    shapes_before, bbox_before_um, gds_path, output_path,
) -> ClipReport:
    """执行单区域裁剪 + 重命名 + 统计 + 写出，返回 ClipReport。"""
    new_ci = ly.clip(top_cell.cell_index(), box_dbu)
    if new_ci < 0:
        raise RuntimeError(
            f"KLayout clip 返回无效 cell index: {new_ci}。禁止 fall-back（R03）。"
        )
    new_cell = ly.cell(new_ci)
    final_name = clipped_cell_name if clipped_cell_name is not None else original_name
    new_cell.name = final_name
    shapes_after = _count_shapes_rec(new_cell, ly)
    bbox_after_um = _bbox_to_um(new_cell.bbox(), dbu)
    try:
        new_cell.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    logger.info(
        "GDSII 裁剪: clip %s, shapes %d→%d",
        clip_box_um, shapes_before, shapes_after,
    )
    return ClipReport(
        input_path=str(gds_path),
        output_path=str(output_path),
        dbu=dbu,
        top_cell_name=original_name,
        clip_box_um=clip_box_um,
        clipped_cell_name=final_name,
        shapes_before=shapes_before,
        shapes_after=shapes_after,
        bbox_before_um=bbox_before_um,
        bbox_after_um=bbox_after_um,
    )


def _do_multi_clip_one_region(
    ly, ci, box_um, dbu, out_dir, prefix, idx,
    original_name, shapes_before, bbox_before_um, gds_path,
) -> ClipReport:
    """处理多区域裁剪的单个区域: 重命名 + 统计 + 写出 + 构建 ClipReport。"""
    new_cell = ly.cell(ci)
    final_name = f"{prefix}_clip{idx}"
    new_cell.name = final_name
    shapes_after = _count_shapes_rec(new_cell, ly)
    bbox_after_um = _bbox_to_um(new_cell.bbox(), dbu)
    out_file = out_dir / f"{final_name}.gds"
    try:
        new_cell.write(str(out_file))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件 {out_file} 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    return ClipReport(
        input_path=str(gds_path),
        output_path=str(out_file),
        dbu=dbu,
        top_cell_name=original_name,
        clip_box_um=box_um,
        clipped_cell_name=final_name,
        shapes_before=shapes_before,
        shapes_after=shapes_after,
        bbox_before_um=bbox_before_um,
        bbox_after_um=bbox_after_um,
    )


# =============================================================================
# 单区域裁剪
# =============================================================================
def clip_gdsii(
    gds_path: str | Path,
    output_path: str | Path,
    clip_box_um: tuple[float, float, float, float],
    top_cell_name: str | None = None,
    clipped_cell_name: str | None = None,
) -> ClipReport:
    """裁剪 GDSII 文件的指定矩形区域（R327）。

    使用 KLayout Layout.clip() 层次化裁剪，保留原层次结构，
    跨越裁剪框边界的图形在边界处被几何切断。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        clip_box_um: 裁剪框 (left, bottom, right, top) μm。
        top_cell_name: 源顶层 cell 名（None 用第一个 top cell）。
        clipped_cell_name: 裁剪后新 cell 名（None 用原 top cell 名）。

    Returns:
        ClipReport 裁剪报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 输入无效 / clip_box 无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Layout.clip: https://klayout.org/doc-qt5/code/class_Layout.html#method33
    - KLayout clip 示例: https://klayout.org/klayout-pypi/examples/clip/
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    left, bottom, right, top = _validate_clip_box(clip_box_um)
    ly = _read_gdsii_layout(db, in_path)
    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)
    original_name = str(top_cell.name)
    shapes_before = _count_shapes_rec(top_cell, ly)
    bbox_before_um = _bbox_to_um(top_cell.bbox(), dbu)
    box_dbu = _build_box_dbu(db, left, bottom, right, top, dbu)
    return _do_clip_operation(
        ly, top_cell, box_dbu, dbu, out_path,
        original_name, clipped_cell_name, (left, bottom, right, top),
        shapes_before, bbox_before_um, gds_path, output_path,
    )


# =============================================================================
# 多区域裁剪
# =============================================================================
def multi_clip_gdsii(
    gds_path: str | Path,
    output_dir: str | Path,
    clip_boxes_um: list[tuple[float, float, float, float]],
    top_cell_name: str | None = None,
    name_prefix: str | None = None,
) -> list[ClipReport]:
    """多区域裁剪 GDSII 文件（R327）。

    使用 KLayout Layout.multi_clip() 一次裁剪多个矩形区域，
    每个区域生成一个独立的 GDSII 文件。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_dir: 输出目录（自动创建）。
        clip_boxes_um: 裁剪框列表 [(l,b,r,t) μm, ...]。
        top_cell_name: 源顶层 cell 名。
        name_prefix: 输出文件名前缀（None 用原 top cell 名）。

    Returns:
        各区域的 ClipReport 列表。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 输入无效 / clip_boxes 为空 / 任一 clip_box 无效。
        ImportError: klayout 未安装。
        RuntimeError: 读取/写出失败。

    来源:
    - KLayout Layout.multi_clip:
      https://klayout.org/doc-qt5/code/class_Layout.html#method98
    """
    db = _import_klayout_db()
    in_path = Path(gds_path)
    out_dir = Path(output_dir)
    if not in_path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    if not clip_boxes_um:
        raise ValueError(
            "clip_boxes_um 不能为空。禁止 fall-back（R03）。"
        )

    # 验证所有裁剪框
    validated_boxes: list[tuple[float, float, float, float]] = []
    for i, box in enumerate(clip_boxes_um):
        validated_boxes.append(_validate_clip_box(box, context=f"clip_boxes[{i}]"))

    out_dir.mkdir(parents=True, exist_ok=True)

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
    original_name = str(top_cell.name)
    prefix = name_prefix if name_prefix is not None else original_name

    # 裁剪前统计（共享）
    shapes_before = _count_shapes_rec(top_cell, ly)
    bbox_before = top_cell.bbox()
    bbox_before_um = (
        float(bbox_before.left) * dbu,
        float(bbox_before.bottom) * dbu,
        float(bbox_before.right) * dbu,
        float(bbox_before.top) * dbu,
    )

    # 构造 dbu 裁剪框列表
    box_dbu_list = []
    for (left, bottom, right, top) in validated_boxes:
        box_dbu_list.append(
            db.Box(
                int(round(left / dbu)),
                int(round(bottom / dbu)),
                int(round(right / dbu)),
                int(round(top / dbu)),
            )
        )

    # 多区域裁剪
    # KLayout 0.30.9: Layout.multi_clip(cell_index, [box1, box2, ...]) -> [ci1, ci2, ...]
    # 来源: https://klayout.org/doc-qt5/code/class_Layout.html#method98
    new_cis = ly.multi_clip(top_cell.cell_index(), box_dbu_list)
    new_cis = [int(ci) for ci in new_cis]
    if len(new_cis) != len(validated_boxes):
        raise RuntimeError(
            f"multi_clip 返回 {len(new_cis)} 个 cell，"
            f"预期 {len(validated_boxes)}。禁止 fall-back（R03）。"
        )

    # 注: 不删除原 top cell，因为用 Cell.write 只写出裁剪 cell 层次，
    # 原 layout 中的其他 cell 不会被写入输出文件。

    # 为每个裁剪结果生成独立文件
    reports: list[ClipReport] = []
    for idx, (ci, box_um) in enumerate(zip(new_cis, validated_boxes)):
        new_cell = ly.cell(ci)
        final_name = f"{prefix}_clip{idx}"
        new_cell.name = final_name
        left, bottom, right, top = box_um

        shapes_after = _count_shapes_rec(new_cell, ly)
        bbox_after = new_cell.bbox()
        bbox_after_um = (
            float(bbox_after.left) * dbu,
            float(bbox_after.bottom) * dbu,
            float(bbox_after.right) * dbu,
            float(bbox_after.top) * dbu,
        )

        out_file = out_dir / f"{final_name}.gds"
        # 单独写出此 cell
        # 注: Cell.write 只写该 cell 及其子 cell 的层次
        try:
            new_cell.write(str(out_file))
        except Exception as e:
            raise RuntimeError(
                f"klayout 写出文件 {out_file} 失败: {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e

        reports.append(
            ClipReport(
                input_path=str(gds_path),
                output_path=str(out_file),
                dbu=dbu,
                top_cell_name=original_name,
                clip_box_um=(left, bottom, right, top),
                clipped_cell_name=final_name,
                shapes_before=shapes_before,
                shapes_after=shapes_after,
                bbox_before_um=bbox_before_um,
                bbox_after_um=bbox_after_um,
            )
        )

    logger.info(
        "GDSII 多区域裁剪: %s → %s (%d 个区域)",
        in_path, out_dir, len(reports),
    )

    return reports


# =============================================================================
# 报告生成
# =============================================================================
def generate_clip_report(
    gds_path: str | Path,
    output_path: str | Path,
    clip_box_um: tuple[float, float, float, float],
    top_cell_name: str | None = None,
    clipped_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 区域裁剪报告（R327）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        clip_box_um: 裁剪框 (left, bottom, right, top) μm。
        top_cell_name: 源顶层 cell 名。
        clipped_cell_name: 裁剪后新 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式 / clip_box 无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = clip_gdsii(
        gds_path,
        output_path,
        clip_box_um,
        top_cell_name=top_cell_name,
        clipped_cell_name=clipped_cell_name,
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
def _validate_clip_box(
    clip_box_um: tuple[float, float, float, float],
    context: str = "clip_box_um",
) -> tuple[float, float, float, float]:
    """验证裁剪框有效性（R327 内部函数）。

    Args:
        clip_box_um: 裁剪框 (left, bottom, right, top) μm。
        context: 错误消息上下文。

    Returns:
        验证后的裁剪框。

    Raises:
        ValueError: 长度不为 4 / left >= right / bottom >= top。
    """
    if not isinstance(clip_box_um, (tuple, list)) or len(clip_box_um) != 4:
        raise ValueError(
            f"{context} 必须是长度 4 的 (left, bottom, right, top) 元组，"
            f"得到: {clip_box_um}。禁止 fall-back（R03）。"
        )
    left, bottom, right, top = (float(v) for v in clip_box_um)
    if left >= right:
        raise ValueError(
            f"{context} left ({left}) 必须 < right ({right})。"
            f"禁止 fall-back（R03）。"
        )
    if bottom >= top:
        raise ValueError(
            f"{context} bottom ({bottom}) 必须 < top ({top})。"
            f"禁止 fall-back（R03）。"
        )
    return (left, bottom, right, top)


def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R327 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = sorted(ly.cell(int(ci)).name for ci in ly.each_top_cell())
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


def _count_shapes_rec(top_cell, ly) -> int:
    """递归统计 top cell 的 shape 总数（R327 内部函数）。

    来源:
    - KLayout RecursiveShapeIterator:
      https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
    """
    count = 0
    for li in ly.layer_indices():
        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            count += 1
            it.next()
    return count


def _render_text_report(report: ClipReport) -> str:
    """渲染纯文本报告（R327 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 区域裁剪报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"源顶层 cell: {report.top_cell_name}")
    lines.append(f"裁剪后 cell: {report.clipped_cell_name}")
    l, b, r, t = report.clip_box_um
    lines.append(f"裁剪框 (μm): left={l}, bottom={b}, right={r}, top={t}")
    lines.append(f"裁剪框尺寸 (μm): {r - l} × {t - b}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("裁剪统计:")
    lines.append("-" * 60)
    lines.append(f"{'指标':<20} {'裁剪前':>20} {'裁剪后':>20}")
    bl, bb, br, bt = report.bbox_before_um
    al, ab, ar, at = report.bbox_after_um
    lines.append(
        f"{'bbox (μm)':<20} "
        f"{'(' + str(round(bl, 3)) + ',' + str(round(bb, 3)) + ',' + str(round(br, 3)) + ',' + str(round(bt, 3)) + ')':>20} "
        f"{'(' + str(round(al, 3)) + ',' + str(round(ab, 3)) + ',' + str(round(ar, 3)) + ',' + str(round(at, 3)) + ')':>20}"
    )
    lines.append(f"{'shape 数':<20} {report.shapes_before:>20} "
                 f"{report.shapes_after:>20}")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: ClipReport) -> str:
    """渲染 Markdown 报告（R327 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 区域裁剪报告")
    lines.append("")
    lines.append(f"**输入文件**: `{report.input_path}`")
    lines.append(f"**输出文件**: `{report.output_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**源顶层 cell**: `{report.top_cell_name}`")
    lines.append(f"**裁剪后 cell**: `{report.clipped_cell_name}`")
    l, b, r, t = report.clip_box_um
    lines.append(
        f"**裁剪框 (μm)**: left={l}, bottom={b}, right={r}, top={t}"
    )
    lines.append(f"**裁剪框尺寸 (μm)**: {r - l} × {t - b}")
    lines.append("")
    lines.append("## 裁剪统计")
    lines.append("")
    lines.append("| 指标 | 裁剪前 | 裁剪后 |")
    lines.append("|------|--------|--------|")
    bl, bb, br, bt = report.bbox_before_um
    al, ab, ar, at = report.bbox_after_um
    lines.append(
        f"| bbox (μm) | "
        f"({round(bl, 3)},{round(bb, 3)},{round(br, 3)},{round(bt, 3)}) | "
        f"({round(al, 3)},{round(ab, 3)},{round(ar, 3)},{round(at, 3)}) |"
    )
    lines.append(
        f"| shape 数 | {report.shapes_before} | {report.shapes_after} |"
    )
    return "\n".join(lines)
