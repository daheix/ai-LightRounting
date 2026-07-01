"""GDSII 层密度分析器（R320，Layer Density Analyzer）。

计算 GDSII 文件中各层的多边形密度，用于 DRC 密度规则检查。

## 核心概念

- **层密度**: 指定区域内某层多边形总面积 / 区域总面积
- **全局密度**: 整个 chip 区域内的密度
- **窗口密度**: 滑动窗口内的密度（用于检测局部密度过低/过高区域）
- **密度规则**: min_density（最小密度，确保工艺均匀性）/ max_density（最大密度）

## 算法

1. **全局密度**: KLayout Region.area() / 整体包围盒面积
2. **窗口密度图**: 将整体区域划分为 N x M 网格，每个网格计算密度
3. **滑动窗口密度**: 用固定大小窗口滑动，计算每个窗口内密度
   - 窗口步长通常为窗口大小的 1/2（50% overlap）
   - 用于检测局部密度违规

## 学术依据

- KLayout Region.area: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout DRC density check:
  https://www.klayout.org/doc-qt5/manual/drc.html
- Synopsys OptoDesigner density rule:
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- Siemens Calibre nmDRC density check:
  https://www.siemens.com/en-us/products/ic/ic-custom/verification/calibre-nmdrc/
- SiEPIC EBeam PDK 密度规范:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- OpenROAD DRC density:
  https://openroad.readthedocs.io/en/latest/main/src/drt/README.html
- 光子学 CMP 化学机械抛光密度规则:
  https://en.wikipedia.org/wiki/Chemical-mechanical_polishing

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "DensityMap",
    "DensityReport",
    "DensityViolation",
    "LayerDensity",
    "check_density_rules",
    "compute_density_map",
    "compute_layer_density",
    "generate_density_report",
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
            "klayout 未安装，无法执行 GDSII 层密度分析。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class LayerDensity:
    """单层全局密度（R320）。

    Attributes:
        layer_name: 层名。
        gds_layer: GDSII 层号。
        gds_datatype: GDSII datatype。
        polygon_area_um2: 该层多边形总面积（μm²）。
        bbox_area_um2: 该层包围盒面积（μm²）。
        density: 全局密度（0.0-1.0），= polygon_area / bbox_area。
        bbox: 该层包围盒 (xmin, ymin, xmax, ymax)（μm）。
    """

    layer_name: str
    gds_layer: int
    gds_datatype: int
    polygon_area_um2: float
    bbox_area_um2: float
    density: float
    bbox: tuple[float, float, float, float]


@dataclass
class DensityMap:
    """密度网格图（R320）。

    将整体区域划分为 rows x cols 网格，每个网格计算密度。

    Attributes:
        layer_name: 层名。
        rows: 网格行数。
        cols: 网格列数。
        cell_size_um: 每个网格单元边长（μm）。
        grid: 密度矩阵 (rows, cols)，值 0.0-1.0。
        bbox: 整体包围盒 (xmin, ymin, xmax, ymax)（μm）。
    """

    layer_name: str
    rows: int
    cols: int
    cell_size_um: float
    grid: np.ndarray  # shape (rows, cols), dtype float
    bbox: tuple[float, float, float, float]


@dataclass
class DensityViolation:
    """密度规则违规（R320）。

    Attributes:
        layer_name: 层名。
        rule_type: 规则类型（'min_density' / 'max_density'）。
        region: 违规区域 (xmin, ymin, xmax, ymax)（μm）。
        measured_density: 实测密度（0.0-1.0）。
        limit_density: 规则限制密度（0.0-1.0）。
        message: 违规描述。
    """

    layer_name: str
    rule_type: str  # 'min_density' / 'max_density'
    region: tuple[float, float, float, float]
    measured_density: float
    limit_density: float
    message: str


@dataclass
class DensityReport:
    """GDSII 层密度分析报告（R320）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu: 数据库单位（米）。
        layer_densities: 各层全局密度列表。
        violations: 密度规则违规列表。
        overall_bbox: 整体包围盒 (xmin, ymin, xmax, ymax)（μm）。
    """

    file_path: str
    top_cell_name: str = ""
    dbu: float = 0.0
    layer_densities: list[LayerDensity] = field(default_factory=list)
    violations: list[DensityViolation] = field(default_factory=list)
    overall_bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


# =============================================================================
# 全局密度计算
# =============================================================================
def compute_layer_density(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_analyze: list[str] | None = None,
) -> DensityReport:
    """计算 GDSII 文件各层的全局密度（R320）。

    对每个 GDSII 层，计算:
    - 多边形总面积（KLayout Region.area()）
    - 该层包围盒面积
    - 密度 = 多边形面积 / 包围盒面积

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。
        layers_to_analyze: 要分析的层名列表（None 分析所有层）。

    Returns:
        DensityReport 报告。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region.area: https://www.klayout.org/doc-qt5/code/class_Region.html
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = _get_default_layer_map()

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)

    layer_densities: list[LayerDensity] = []
    overall_xmin = float("inf")
    overall_ymin = float("inf")
    overall_xmax = float("-inf")
    overall_ymax = float("-inf")

    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        layer_name = layer_map.get(
            (gds_layer, gds_datatype),
            f"LAYER_{gds_layer}_{gds_datatype}",
        )
        if layers_to_analyze is not None and layer_name not in layers_to_analyze:
            continue

        # 用 Region 收集多边形
        region = db.Region(top_cell.begin_shapes_rec(li))
        area_dbu2 = int(region.area())
        if area_dbu2 == 0:
            continue  # 空层跳过

        area_um2 = area_dbu2 * dbu * dbu

        # 计算包围盒
        bbox_dbu = region.bbox()
        bbox = (
            float(bbox_dbu.left) * dbu,
            float(bbox_dbu.bottom) * dbu,
            float(bbox_dbu.right) * dbu,
            float(bbox_dbu.top) * dbu,
        )
        bbox_w = bbox[2] - bbox[0]
        bbox_h = bbox[3] - bbox[1]
        bbox_area_um2 = bbox_w * bbox_h

        # 密度 = 多边形面积 / 包围盒面积
        # 注意：当包围盒面积为 0（退化情况）时密度为 0
        if bbox_area_um2 > 0:
            density = area_um2 / bbox_area_um2
        else:
            density = 0.0

        layer_densities.append(
            LayerDensity(
                layer_name=layer_name,
                gds_layer=gds_layer,
                gds_datatype=gds_datatype,
                polygon_area_um2=area_um2,
                bbox_area_um2=bbox_area_um2,
                density=density,
                bbox=bbox,
            )
        )

        if bbox[0] < overall_xmin:
            overall_xmin = bbox[0]
        if bbox[1] < overall_ymin:
            overall_ymin = bbox[1]
        if bbox[2] > overall_xmax:
            overall_xmax = bbox[2]
        if bbox[3] > overall_ymax:
            overall_ymax = bbox[3]

    if overall_xmin == float("inf"):
        overall_bbox = (0.0, 0.0, 0.0, 0.0)
    else:
        overall_bbox = (overall_xmin, overall_ymin, overall_xmax, overall_ymax)

    return DensityReport(
        file_path=str(gds_path),
        top_cell_name=top_cell.name,
        dbu=dbu,
        layer_densities=layer_densities,
        violations=[],
        overall_bbox=overall_bbox,
    )


# =============================================================================
# 密度网格图
# =============================================================================
def _find_target_layer(ly, layer_name: str, layer_map: dict) -> object:
    """在 GDSII 中查找指定名称的层索引（R629 Extract Method）。

    Raises:
        ValueError: 层不存在。
    """
    for li in ly.layer_indices():
        info = ly.get_info(li)
        ln = layer_map.get(
            (int(info.layer), int(info.datatype)),
            f"LAYER_{int(info.layer)}_{int(info.datatype)}",
        )
        if ln == layer_name:
            return li
    # 收集可用层名
    available = set()
    for li in ly.layer_indices():
        info = ly.get_info(li)
        ln = layer_map.get(
            (int(info.layer), int(info.datatype)),
            f"LAYER_{int(info.layer)}_{int(info.datatype)}",
        )
        available.add(ln)
    raise ValueError(
        f"层 '{layer_name}' 不在 GDSII 文件中。"
        f"可用层: {available}"
    )


def _compute_density_grid(
    region, db, x_min: float, y_min: float, cell_size_um: float,
    dbu: float, rows: int, cols: int,
) -> np.ndarray:
    """计算每个网格单元的密度（R629 Extract Method）。"""
    grid = np.zeros((rows, cols), dtype=float)
    for r in range(rows):
        for c in range(cols):
            cell_x_min = x_min + c * cell_size_um
            cell_y_min = y_min + r * cell_size_um
            cell_x_max = cell_x_min + cell_size_um
            cell_y_max = cell_y_min + cell_size_um

            # 构造网格单元的 Box（dbu 单位）
            cell_box = db.Box(
                int(cell_x_min / dbu),
                int(cell_y_min / dbu),
                int(cell_x_max / dbu),
                int(cell_y_max / dbu),
            )
            cell_region = db.Region(cell_box)

            # 与该层多边形求交集
            intersection = region.dup()
            intersection &= cell_region
            cell_polygon_area_dbu2 = int(intersection.area())
            cell_polygon_area_um2 = cell_polygon_area_dbu2 * dbu * dbu
            cell_area_um2 = cell_size_um * cell_size_um

            if cell_area_um2 > 0:
                grid[r, c] = cell_polygon_area_um2 / cell_area_um2
            else:
                grid[r, c] = 0.0
    return grid


def compute_density_map(
    gds_path: str | Path,
    layer_name: str,
    cell_size_um: float = 10.0,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> DensityMap:
    """计算指定层的密度网格图（R320）。

    将整体区域划分为 rows x cols 网格，每个网格计算密度。
    网格大小由 cell_size_um 决定。

    Args:
        gds_path: GDSII 文件路径。
        layer_name: 要分析的层名。
        cell_size_um: 每个网格单元边长（μm）。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。

    Returns:
        DensityMap 密度网格图。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: cell_size_um <= 0 / 层不存在 / GDSII 无效。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region & Box 运算: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    if cell_size_um <= 0:
        raise ValueError(f"cell_size_um 必须 > 0，得到 {cell_size_um}")

    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = _get_default_layer_map()

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)

    target_li = _find_target_layer(ly, layer_name, layer_map)

    # 收集该层所有多边形
    region = db.Region(top_cell.begin_shapes_rec(target_li))

    # 计算整体包围盒
    bbox_dbu = region.bbox()
    if bbox_dbu.empty():
        # 空层返回空网格
        return DensityMap(
            layer_name=layer_name,
            rows=0,
            cols=0,
            cell_size_um=cell_size_um,
            grid=np.zeros((0, 0)),
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    x_min = float(bbox_dbu.left) * dbu
    y_min = float(bbox_dbu.bottom) * dbu
    x_max = float(bbox_dbu.right) * dbu
    y_max = float(bbox_dbu.top) * dbu
    bbox = (x_min, y_min, x_max, y_max)

    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        raise ValueError(
            f"层 '{layer_name}' 包围盒退化: {bbox}。"
            f"无法计算密度网格。"
        )

    cols = max(1, int(np.ceil(width / cell_size_um)))
    rows = max(1, int(np.ceil(height / cell_size_um)))

    grid = _compute_density_grid(
        region, db, x_min, y_min, cell_size_um, dbu, rows, cols
    )

    return DensityMap(
        layer_name=layer_name,
        rows=rows,
        cols=cols,
        cell_size_um=cell_size_um,
        grid=grid,
        bbox=bbox,
    )


# =============================================================================
# 密度规则检查
# =============================================================================
def check_density_rules(
    gds_path: str | Path,
    rules: list[tuple[str, str, float]],
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> list[DensityViolation]:
    """检查 GDSII 文件各层密度规则（R320）。

    Args:
        gds_path: GDSII 文件路径。
        rules: 密度规则列表，每条为 (layer_name, rule_type, limit_density)。
            rule_type: 'min_density' 或 'max_density'。
            limit_density: 限制密度（0.0-1.0）。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。

    Returns:
        密度违规列表。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: 规则格式无效 / limit_density 不在 [0,1] / 层不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout DRC density check: https://www.klayout.org/doc-qt5/manual/drc.html
    - Synopsys OptoDesigner density rule: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """
    if not rules:
        raise ValueError("rules 不能为空")

    # 校验规则格式
    for layer_name, rule_type, limit in rules:
        if rule_type not in ("min_density", "max_density"):
            raise ValueError(
                f"无效 rule_type: {rule_type}。"
                f"支持: 'min_density' / 'max_density'"
            )
        if not 0.0 <= limit <= 1.0:
            raise ValueError(
                f"limit_density 必须在 [0.0, 1.0]，得到 {limit}"
            )

    # 计算各层密度
    layers_to_check = list({r[0] for r in rules})
    report = compute_layer_density(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name,
        layers_to_analyze=layers_to_check,
    )

    # 检查每条规则
    available_layers = {ld.layer_name for ld in report.layer_densities}
    violations: list[DensityViolation] = []
    for layer_name, rule_type, limit in rules:
        if layer_name not in available_layers:
            raise ValueError(
                f"规则引用的层 '{layer_name}' 不在 GDSII 文件中。"
                f"可用层: {available_layers}"
            )

        ld = next(
            d for d in report.layer_densities if d.layer_name == layer_name
        )

        if rule_type == "min_density" and ld.density < limit:
            violations.append(
                DensityViolation(
                    layer_name=layer_name,
                    rule_type=rule_type,
                    region=ld.bbox,
                    measured_density=ld.density,
                    limit_density=limit,
                    message=(
                        f"层 {layer_name} 全局密度 {ld.density:.4f} "
                        f"< 最小密度 {limit:.4f}，"
                        f"工艺均匀性不足（CMP 抛光风险）"
                    ),
                )
            )
        elif rule_type == "max_density" and ld.density > limit:
            violations.append(
                DensityViolation(
                    layer_name=layer_name,
                    rule_type=rule_type,
                    region=ld.bbox,
                    measured_density=ld.density,
                    limit_density=limit,
                    message=(
                        f"层 {layer_name} 全局密度 {ld.density:.4f} "
                        f"> 最大密度 {limit:.4f}，"
                        f"过密可能导致工艺问题"
                    ),
                )
            )

    return violations


# =============================================================================
# 报告生成
# =============================================================================
def generate_density_report(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 层密度分析报告（R320）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: 不支持的格式 / GDSII 无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = compute_layer_density(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name,
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


def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R320 内部函数）。"""
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        return top_cell

    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
        )
    return top_cells[0]


def _render_text_report(report: DensityReport) -> str:
    """渲染纯文本报告。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 层密度分析报告")
    lines.append("=" * 60)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"dbu: {report.dbu} m")
    x_min, y_min, x_max, y_max = report.overall_bbox
    lines.append(
        f"整体包围盒: [{x_min:.2f}, {y_min:.2f}] - "
        f"[{x_max:.2f}, {y_max:.2f}] μm"
    )
    lines.append(f"层数: {len(report.layer_densities)}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("各层密度:")
    lines.append("-" * 60)
    for ld in report.layer_densities:
        bx_min, by_min, bx_max, by_max = ld.bbox
        lines.append(
            f"  {ld.layer_name} (GDS {ld.gds_layer}/{ld.gds_datatype}):"
        )
        lines.append(f"    多边形面积: {ld.polygon_area_um2:.4f} μm²")
        lines.append(f"    包围盒面积: {ld.bbox_area_um2:.4f} μm²")
        lines.append(f"    密度: {ld.density:.4f} ({ld.density * 100:.2f}%)")
        lines.append(
            f"    包围盒: [{bx_min:.2f}, {by_min:.2f}]-"
            f"[{bx_max:.2f}, {by_max:.2f}] μm"
        )
    if report.violations:
        lines.append("-" * 60)
        lines.append(f"密度违规: {len(report.violations)} 条")
        lines.append("-" * 60)
        for v in report.violations:
            lines.append(f"  {v.message}")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: DensityReport) -> str:
    """渲染 Markdown 报告。"""
    lines: list[str] = []
    lines.append("# GDSII 层密度分析报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**dbu**: {report.dbu} m")
    x_min, y_min, x_max, y_max = report.overall_bbox
    lines.append(
        f"**整体包围盒**: [{x_min:.2f}, {y_min:.2f}] - "
        f"[{x_max:.2f}, {y_max:.2f}] μm"
    )
    lines.append(f"**层数**: {len(report.layer_densities)}")
    lines.append("")
    lines.append("## 各层密度")
    lines.append("")
    lines.append(
        "| 层名 | GDS 层/datatype | 多边形面积(μm²) | 包围盒面积(μm²) | 密度 |"
    )
    lines.append(
        "|------|------------------|------------------|------------------|------|"
    )
    for ld in report.layer_densities:
        lines.append(
            f"| {ld.layer_name} | {ld.gds_layer}/{ld.gds_datatype} | "
            f"{ld.polygon_area_um2:.4f} | {ld.bbox_area_um2:.4f} | "
            f"{ld.density:.4f} ({ld.density * 100:.2f}%) |"
        )
    if report.violations:
        lines.append("")
        lines.append(f"## 密度违规（{len(report.violations)} 条）")
        lines.append("")
        for v in report.violations:
            lines.append(f"- **{v.layer_name}** {v.rule_type}: {v.message}")
    return "\n".join(lines)
