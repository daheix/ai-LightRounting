"""GDSII DRC 层间检查工具（R344，Inter-Layer DRC Checker）。

基于 KLayout Region 的 enclosing_check / enclosed_check / overlap_check /
separation_check API，对 GDSII 两个层执行层间 DRC 检查。

## 核心概念

- **Enclosing 检查（包围检查）**: 检查 layer_a 是否充分包围 layer_b
  - 违规: layer_a 比 layer_b 小（每边差距 < min_enclosing）
  - 典型用途: 检查金属层是否充分覆盖接触孔
- **Enclosed 检查（被包围检查）**: 检查 layer_a 是否被 layer_b 充分包围
  - 违规: layer_b 比 layer_a 小（每边差距 < min_enclosed）
  - 典型用途: 检查植入区是否充分覆盖栅极
- **Overlap 检查（重叠检查）**: 检查 layer_a 与 layer_b 的重叠
  - 违规: 重叠区域 < min_overlap
  - 典型用途: 检查两层是否充分重叠（如通孔上下层）
- **Separation 检查（间距检查）**: 检查 layer_a 与 layer_b 的间距
  - 违规: 间距 < min_separation
  - 典型用途: 检查不同层之间的最小间距

## KLayout 0.30.9 API 关键事实（R344 冒烟测试实测）

- `db.Region(top_cell.begin_shapes_rec(layer_index))`: 从 layout 递归提取 Region
- `region.enclosing_check(other, d)`: 检查 self 是否比 other 大至少 d dbu（每边）
  - 返回 EdgePairs 集合
  - d: 最小包围阈值（dbu，int）
- `region.enclosed_check(other, d)`: 检查 self 是否被 other 充分包围
  - 返回 EdgePairs 集合
- `region.overlap_check(other, d)`: 检查 self 与 other 重叠 >= d dbu
  - 返回 EdgePairs 集合
- `region.separation_check(other, d)`: 检查 self 与 other 间距 >= d dbu
  - 返回 EdgePairs 集合
- `edge_pairs.count()`: 返回违规数
- `edge_pairs.each()`: 迭代 EdgePair
- `edge_pairs.bbox()`: 返回所有违规的包围盒
- `edge_pair.first` / `edge_pair.second`: 违规边对
- `edge_pair.distance()`: 违规距离（dbu）

## 算法

1. 读取 GDSII
2. 提取 layer_a 和 layer_b 的 Region（递归遍历子 cell）
3. 转换 min_value_um → dbu
4. 执行层间检查:
   - enclosing: r_a.enclosing_check(r_b, d)
   - enclosed: r_a.enclosed_check(r_b, d)
   - overlap: r_a.overlap_check(r_b, d)
   - separation: r_a.separation_check(r_b, d)
5. 迭代 EdgePairs，提取违规详情
6. 生成报告

## 学术依据

- KLayout Region class (enclosing_check):
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout EdgePairs class:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair class:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html
- KLayout DRC Reference (enclosing, enclosed, overlap, separation):
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Inter-Layer Checks:
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
    "InterLayerDRCViolation",
    "InterLayerDRCReport",
    "check_enclosing",
    "check_enclosed",
    "check_overlap",
    "check_separation",
    "generate_interlayer_drc_report",
]

VALID_CHECK_TYPES = ("enclosing", "enclosed", "overlap", "separation")


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 层间 DRC 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class InterLayerDRCViolation:
    """单个层间 DRC 违规记录（R344）。

    一个违规由两条边组成（first 和 second），分别来自 layer_a 和 layer_b。

    Attributes:
        x1_um: first 边起点 X（μm）。
        y1_um: first 边起点 Y（μm）。
        x2_um: first 边终点 X（μm）。
        y2_um: first 边终点 Y（μm）。
        x3_um: second 边起点 X（μm）。
        y3_um: second 边起点 Y（μm）。
        x4_um: second 边终点 X（μm）。
        y4_um: second 边终点 Y（μm）。
        distance_um: 两条边之间的距离（μm，即违规阈值差距）。
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
class InterLayerDRCReport:
    """GDSII 层间 DRC 检查报告（R344）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        check_type: 检查类型 'enclosing'/'enclosed'/'overlap'/'separation'。
        layer_a: 第一层 (layer, datatype)。
        layer_b: 第二层 (layer, datatype)。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        min_value_um: 最小阈值（μm）。
        total_violations: 违规总数。
        violations: 违规列表（最多 max_violations 条）。
        bbox: 违规区域包围盒 [(xmin,ymin),(xmax,ymax)]（μm），空为 None。
        max_violations: 报告中保留的最大违规数。
    """

    input_path: str = ""
    check_type: str = ""
    layer_a: tuple[int, int] = (0, 0)
    layer_b: tuple[int, int] = (0, 0)
    dbu: float = 0.0
    top_cell_name: str = ""
    min_value_um: float = 0.0
    total_violations: int = 0
    violations: list[InterLayerDRCViolation] = field(default_factory=list)
    bbox: tuple[tuple[float, float], tuple[float, float]] | None = None
    max_violations: int = 1000


# =============================================================================
# 四个公开检查函数
# =============================================================================
def check_enclosing(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    min_enclosing_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> InterLayerDRCReport:
    """检查 layer_a 是否充分包围 layer_b（R344）。

    用 KLayout `r_a.enclosing_check(r_b, d)` 检查 layer_a 是否比 layer_b
    大至少 min_enclosing_um（每边）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer_a: 包围层 (layer, datatype)。
        layer_b: 被包围层 (layer, datatype)。
        min_enclosing_um: 最小包围阈值（μm，每边）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。

    Returns:
        InterLayerDRCReport 检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 参数无效 / 层相同 / 层不存在。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Region enclosing_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    return _run_interlayer_check(
        gds_path, layer_a, layer_b, min_enclosing_um,
        "enclosing", top_cell_name, max_violations,
    )


def check_enclosed(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    min_enclosed_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> InterLayerDRCReport:
    """检查 layer_a 是否被 layer_b 充分包围（R344）。

    用 KLayout `r_a.enclosed_check(r_b, d)` 检查 layer_a 是否被 layer_b
    充分包围（layer_b 比 layer_a 大至少 min_enclosed_um 每边）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer_a: 被包围层 (layer, datatype)。
        layer_b: 包围层 (layer, datatype)。
        min_enclosed_um: 最小被包围阈值（μm，每边）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。

    Returns:
        InterLayerDRCReport 检查报告。

    来源:
    - KLayout Region enclosed_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    return _run_interlayer_check(
        gds_path, layer_a, layer_b, min_enclosed_um,
        "enclosed", top_cell_name, max_violations,
    )


def check_overlap(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    min_overlap_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> InterLayerDRCReport:
    """检查 layer_a 与 layer_b 的重叠（R344）。

    用 KLayout `r_a.overlap_check(r_b, d)` 检查 layer_a 与 layer_b 的重叠
    是否 >= min_overlap_um。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer_a: 第一层 (layer, datatype)。
        layer_b: 第二层 (layer, datatype)。
        min_overlap_um: 最小重叠阈值（μm）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。

    Returns:
        InterLayerDRCReport 检查报告。

    来源:
    - KLayout Region overlap_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    return _run_interlayer_check(
        gds_path, layer_a, layer_b, min_overlap_um,
        "overlap", top_cell_name, max_violations,
    )


def check_separation(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    min_separation_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> InterLayerDRCReport:
    """检查 layer_a 与 layer_b 的间距（R344）。

    用 KLayout `r_a.separation_check(r_b, d)` 检查 layer_a 与 layer_b 的间距
    是否 >= min_separation_um。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer_a: 第一层 (layer, datatype)。
        layer_b: 第二层 (layer, datatype)。
        min_separation_um: 最小间距阈值（μm）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。

    Returns:
        InterLayerDRCReport 检查报告。

    来源:
    - KLayout Region separation_check: https://www.klayout.de/doc-qt5/code/class_Region.html
    """
    return _run_interlayer_check(
        gds_path, layer_a, layer_b, min_separation_um,
        "separation", top_cell_name, max_violations,
    )


# =============================================================================
# 内部检查实现
# =============================================================================
def _run_interlayer_check(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    min_value_um: float,
    check_type: str,
    top_cell_name: str | None,
    max_violations: int,
) -> InterLayerDRCReport:
    """执行层间 DRC 检查的内部实现（R344 内部函数）。"""
    db = _import_klayout_db()
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")

    a_layer, a_dt = _validate_layer(layer_a, "layer_a")
    b_layer, b_dt = _validate_layer(layer_b, "layer_b")
    if (a_layer, a_dt) == (b_layer, b_dt):
        raise ValueError(
            f"layer_a 和 layer_b 不能相同: {(a_layer, a_dt)}。"
            f"层间检查需要两个不同的层。"
            f"禁止 fall-back（R03）。"
        )

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
    li_a = _find_or_raise_layer(ly, a_layer, a_dt, gds_path, "layer_a")
    li_b = _find_or_raise_layer(ly, b_layer, b_dt, gds_path, "layer_b")

    # 提取 Region（递归遍历子 cell）
    r_a = db.Region(top_cell.begin_shapes_rec(li_a))
    r_b = db.Region(top_cell.begin_shapes_rec(li_b))

    # 转换 min_value_um → dbu
    min_value_dbu = int(round(min_value_um / dbu))

    # 执行检查
    if check_type == "enclosing":
        edge_pairs = r_a.enclosing_check(r_b, min_value_dbu)
    elif check_type == "enclosed":
        edge_pairs = r_a.enclosed_check(r_b, min_value_dbu)
    elif check_type == "overlap":
        edge_pairs = r_a.overlap_check(r_b, min_value_dbu)
    else:  # separation
        edge_pairs = r_a.separation_check(r_b, min_value_dbu)

    total_violations = int(edge_pairs.count())

    # 提取违规详情
    violations: list[InterLayerDRCViolation] = []
    for ep in edge_pairs.each():
        if len(violations) >= max_violations:
            break
        first = ep.first
        second = ep.second
        distance_dbu = int(ep.distance())
        violations.append(InterLayerDRCViolation(
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
        "GDSII 层间 DRC %s 检查: %s (%d,%d)→(%d,%d), min=%.4fμm, violations=%d",
        check_type, in_path, a_layer, a_dt, b_layer, b_dt,
        min_value_um, total_violations,
    )

    return InterLayerDRCReport(
        input_path=str(gds_path),
        check_type=check_type,
        layer_a=(a_layer, a_dt),
        layer_b=(b_layer, b_dt),
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
def generate_interlayer_drc_report(
    gds_path: str | Path,
    layer_a: tuple[int, int],
    layer_b: tuple[int, int],
    check_type: str,
    min_value_um: float,
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """执行层间 DRC 检查并生成报告字符串（R344）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        layer_a: 第一层 (layer, datatype)。
        layer_b: 第二层 (layer, datatype)。
        check_type: 'enclosing'/'enclosed'/'overlap'/'separation'。
        min_value_um: 最小阈值（μm）。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 报告中保留的最大违规数。
        output_format: 'text'/'markdown'/'json'。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / check_type 无效 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。
    """
    ct = check_type.lower()
    if ct == "enclosing":
        report = check_enclosing(
            gds_path, layer_a, layer_b, min_value_um,
            top_cell_name, max_violations,
        )
    elif ct == "enclosed":
        report = check_enclosed(
            gds_path, layer_a, layer_b, min_value_um,
            top_cell_name, max_violations,
        )
    elif ct == "overlap":
        report = check_overlap(
            gds_path, layer_a, layer_b, min_value_um,
            top_cell_name, max_violations,
        )
    elif ct == "separation":
        report = check_separation(
            gds_path, layer_a, layer_b, min_value_um,
            top_cell_name, max_violations,
        )
    else:
        raise ValueError(
            f"不支持的 check_type: {check_type}。"
            f"支持: {VALID_CHECK_TYPES}。"
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
    """验证层参数（R344 内部函数）。"""
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
    """获取顶层 cell（R344 内部函数）。"""
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
    """查找层，不存在则 raise（R344 内部函数）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return int(li)
    raise ValueError(
        f"{context} ({layer}, {datatype}) 在文件 {gds_path} 中不存在。"
        f"禁止 fall-back（R03）。"
    )


def _render_text_report(report: InterLayerDRCReport) -> str:
    """渲染纯文本报告（R344 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"GDSII 层间 DRC {report.check_type.upper()} 检查报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(
        f"layer_a: ({report.layer_a[0]},{report.layer_a[1]})  "
        f"layer_b: ({report.layer_b[0]},{report.layer_b[1]})"
    )
    lines.append(f"检查类型: {report.check_type}")
    lines.append(f"最小阈值: {report.min_value_um:.6f} μm")
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
    if report.violations:
        lines.append("")
        lines.append(f"  违规详情（前 {min(10, len(report.violations))} 条）:")
        for i, v in enumerate(report.violations[:10]):
            lines.append(f"    [{i}] distance={v.distance_um:.6f} μm")
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


def _render_markdown_report(report: InterLayerDRCReport) -> str:
    """渲染 Markdown 报告（R344 内部函数）。"""
    lines: list[str] = []
    lines.append(f"# GDSII 层间 DRC {report.check_type.upper()} 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(
        f"- **layer_a**: ({report.layer_a[0]},{report.layer_a[1]})"
    )
    lines.append(
        f"- **layer_b**: ({report.layer_b[0]},{report.layer_b[1]})"
    )
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
        lines.append("| # | 距离 (μm) | first 边 | second 边 |")
        lines.append("|---|----------|----------|-----------|")
        for i, v in enumerate(report.violations[:20]):
            lines.append(
                f"| {i} | {v.distance_um:.4f} | "
                f"({v.x1_um:.3f},{v.y1_um:.3f})→({v.x2_um:.3f},{v.y2_um:.3f}) | "
                f"({v.x3_um:.3f},{v.y3_um:.3f})→({v.x4_um:.3f},{v.y4_um:.3f}) |"
            )
    return "\n".join(lines)


def _render_json_report(report: InterLayerDRCReport) -> str:
    """渲染 JSON 报告（R344 内部函数）。"""
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
        "layer_a": list(report.layer_a),
        "layer_b": list(report.layer_b),
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
