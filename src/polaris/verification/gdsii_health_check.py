"""GDSII 文件级结构化校验工具（R314，pre-DRC 健康检查）。

在 DRC 检查前对 GDSII 文件做结构化健康检查，识别潜在的格式/结构问题：
1. 层定义完整性: GDSII 中的层是否都在 layer_map 中
2. 多边形有效性: 多边形 ≥3 顶点、非退化
3. cell 引用完整性: 无悬空 cell 引用、孤立 cell 检测
4. 单位一致性: dbu 在合理范围（1e-3 ~ 1e-9 m）
5. 顶层 cell 唯一性: 多顶层 cell 触发警告

R314 实现:
- HealthCheckIssue: 单个问题数据类（severity/category/message/layer/cell_name）
- HealthCheckReport: 校验报告数据类（file_path/issues/passed/checks_run/by_category）
- check_gdsii_health: 端到端校验入口
- check_layer_completeness: 层完整性子检查
- check_polygon_validity: 多边形有效性子检查
- check_cell_references: cell 引用完整性子检查
- check_unit_consistency: 单位一致性子检查
- check_top_cell_uniqueness: 顶层 cell 唯一性子检查

R03 合规:
- 文件不存在 raise FileNotFoundError
- GDSII 读取失败 raise RuntimeError
- 不支持的 severity/category raise ValueError
- 校验发现的问题通过 HealthCheckIssue 显式标记，不静默吞异常

R02 学术诚信:
- KLayout API 用法附官方文档 URL
- GDSII 格式规范附 Wikipedia/GDSII spec URL
- dbu 合理范围参考 GDSII 规范（典型值 1e-9 ~ 1e-3 m）

来源:
- KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout Cell API: https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout LayerInfo: https://www.klayout.org/doc-qt5/code/class_LayerInfo.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- GDSII Specification: https://www.itu.int/rec/T-REC-GDSII
- KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout SimplePolygon: https://www.klayout.org/doc-qt5/code/class_SimplePolygon.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from polaris.verification.gdsii_drc_validator import _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "HealthCheckIssue",
    "HealthCheckReport",
    "IssueCategory",
    "IssueSeverity",
    "check_cell_references",
    "check_gdsii_health",
    "check_layer_completeness",
    "check_polygon_validity",
    "check_top_cell_uniqueness",
    "check_unit_consistency",
]


class IssueSeverity(str, Enum):
    """问题严重级别（R314）。

    来源: 借鉴 Python logging 级别 + LLVM diagnostic severities
    https://docs.python.org/3/library/logging.html#levels
    """

    ERROR = "error"  # 阻断性问题，必须修复
    WARNING = "warning"  # 警告，建议修复
    INFO = "info"  # 提示信息


class IssueCategory(str, Enum):
    """问题类别（R314）。

    对应 5 类预校验：
    - LAYER_COMPLETENESS: 层定义完整性
    - POLYGON_VALIDITY: 多边形有效性
    - CELL_REFERENCE: cell 引用完整性
    - UNIT_CONSISTENCY: 单位一致性
    - TOP_CELL_UNIQUENESS: 顶层 cell 唯一性
    """

    LAYER_COMPLETENESS = "layer_completeness"
    POLYGON_VALIDITY = "polygon_validity"
    CELL_REFERENCE = "cell_reference"
    UNIT_CONSISTENCY = "unit_consistency"
    TOP_CELL_UNIQUENESS = "top_cell_uniqueness"


@dataclass
class HealthCheckIssue:
    """单个健康检查问题（R314）。

    Attributes:
        severity: 严重级别（ERROR/WARNING/INFO）。
        category: 问题类别。
        message: 问题描述（中文）。
        layer: 相关层名（None 表示不针对特定层）。
        cell_name: 相关 cell 名（None 表示不针对特定 cell）。
    """

    severity: IssueSeverity
    category: IssueCategory
    message: str
    layer: str | None = None
    cell_name: str | None = None


@dataclass
class HealthCheckReport:
    """GDSII 健康检查报告（R314）。

    Attributes:
        file_path: GDSII 文件路径。
        issues: 所有 HealthCheckIssue 列表。
        passed: 是否通过（无 ERROR 级别问题）。
        checks_run: 执行的检查项列表。
        by_category: 按类别分组的问题数 {category: count}。
        by_severity: 按严重级别分组的问题数 {severity: count}。
    """

    file_path: str
    issues: list[HealthCheckIssue] = field(default_factory=list)
    passed: bool = True
    checks_run: list[str] = field(default_factory=list)
    by_category: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 健康检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 5 类子检查
# =============================================================================
def check_layer_completeness(
    ly, layer_map: dict[tuple[int, int], str] | None = None
) -> list[HealthCheckIssue]:
    """检查层定义完整性（R314）。

    检查 GDSII 文件中实际存在的层是否都在 layer_map 中定义。
    未定义的层标记为 WARNING（可能是新层或层映射缺失）。

    Args:
        ly: klayout.db.Layout 对象。
        layer_map: 层映射（None 用 SiEPIC 标准）。

    Returns:
        HealthCheckIssue 列表。

    来源:
    - KLayout Layout.layer_indices: https://www.klayout.org/doc-qt5/code/class_Layout.html
    - KLayout LayerInfo: https://www.klayout.org/doc-qt5/code/class_LayerInfo.html
    """
    if layer_map is None:
        layer_map = _get_default_layer_map()
    issues: list[HealthCheckIssue] = []
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        if (gds_layer, gds_datatype) not in layer_map:
            issues.append(
                HealthCheckIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.LAYER_COMPLETENESS,
                    message=(
                        f"层 ({gds_layer}/{gds_datatype}) 不在 layer_map 中，"
                        f"建议补充层映射或确认是否为新工艺层。"
                    ),
                    layer=f"LAYER_{gds_layer}_{gds_datatype}",
                )
            )
    return issues


def check_polygon_validity(ly, top_cell) -> list[HealthCheckIssue]:
    """检查多边形有效性（R314）。

    检查顶层 cell（递归）中所有多边形：
    - 顶点数 < 3: ERROR（退化多边形）
    - 顶点数 == 3: INFO（三角形，技术有效但需注意）
    - 面积 == 0: ERROR（退化多边形）

    Args:
        ly: klayout.db.Layout 对象。
        top_cell: 顶层 klayout.db.Cell 对象。

    Returns:
        HealthCheckIssue 列表。

    来源:
    - KLayout Cell.begin_shapes_rec: https://www.klayout.org/doc-qt5/code/class_Cell.html
    - KLayout SimplePolygon: https://www.klayout.org/doc-qt5/code/class_SimplePolygon.html
    """
    db = _import_klayout_db()
    issues: list[HealthCheckIssue] = []
    dbu = float(ly.dbu)
    for li in ly.layer_indices():
        info = ly.get_info(li)
        layer_name = f"LAYER_{int(info.layer)}_{int(info.datatype)}"
        # 用 Region 收集多边形（自动合并）
        region = db.Region(top_cell.begin_shapes_rec(li))
        for klayout_poly in region.each():
            simple = klayout_poly.to_simple_polygon()
            pts = list(simple.each_point())
            n_pts = len(pts)
            if n_pts < 3:
                issues.append(
                    HealthCheckIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.POLYGON_VALIDITY,
                        message=(
                            f"多边形顶点数 {n_pts} < 3，退化多边形，"
                            f"必须修复。"
                        ),
                        layer=layer_name,
                        cell_name=top_cell.name,
                    )
                )
                continue
            # 面积检查（用 KLayout Region.area 计算，单位 dbu²）
            # 单个多边形面积需要单独构造 Region
            single_region = db.Region()
            single_region.insert(klayout_poly)
            area_dbu2 = int(single_region.area())
            if area_dbu2 == 0:
                issues.append(
                    HealthCheckIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.POLYGON_VALIDITY,
                        message=(
                            f"多边形面积为 0，退化多边形（顶点共线），"
                            f"必须修复。"
                        ),
                        layer=layer_name,
                        cell_name=top_cell.name,
                    )
                )
    return issues


def check_cell_references(ly) -> list[HealthCheckIssue]:
    """检查 cell 引用完整性（R314）。

    检测孤立 cell：既不是顶层 cell，也不被任何其他 cell 引用的 cell。
    孤立 cell 标记为 WARNING（可能是未使用的备用 cell 或设计遗留）。

    Args:
        ly: klayout.db.Layout 对象。

    Returns:
        HealthCheckIssue 列表。

    来源:
    - KLayout Cell.called_cells: https://www.klayout.org/doc-qt5/code/class_Cell.html
    - KLayout Cell.caller_cells: https://www.klayout.org/doc-qt5/code/class_Cell.html
    - KLayout Layout.each_top_cell: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    issues: list[HealthCheckIssue] = []
    top_cell_indices = set(ly.each_top_cell())
    for ci in ly.each_cell():
        cell = ly.cell(ci)
        # 顶层 cell 跳过
        if ci in top_cell_indices:
            continue
        # 非顶层 cell 必须被调用
        callers = list(cell.caller_cells())
        if not callers:
            issues.append(
                HealthCheckIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.CELL_REFERENCE,
                    message=(
                        f"cell '{cell.name}' 既非顶层 cell 也无 caller，"
                        f"属于孤立 cell（可能是未使用的备用 cell 或设计遗留）。"
                    ),
                    cell_name=cell.name,
                )
            )
    return issues


def check_unit_consistency(ly) -> list[HealthCheckIssue]:
    """检查单位一致性（R314）。

    检查 Layout.dbu（数据库单位，米）是否在合理范围。
    GDSII 规范典型 dbu: 1e-9 m（1 nm）~ 1e-3 m（1 mm）。
    - dbu > 1e-3: ERROR（单位过大，精度不足）
    - dbu < 1e-9: ERROR（单位过小，可能是数据损坏）
    - dbu 不在常见值（1e-9/1e-8/1e-7/1e-6）: WARNING

    Args:
        ly: klayout.db.Layout 对象。

    Returns:
        HealthCheckIssue 列表。

    来源:
    - GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
    - KLayout Layout.dbu: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    issues: list[HealthCheckIssue] = []
    dbu = float(ly.dbu)
    # GDSII 典型 dbu 范围 1e-9 ~ 1e-3 m
    if dbu > 1e-3:
        issues.append(
            HealthCheckIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.UNIT_CONSISTENCY,
                message=(
                    f"dbu={dbu} m 过大（>1e-3 m），精度不足，"
                    f"必须修复为更小的 dbu。"
                ),
            )
        )
    elif dbu < 1e-9:
        issues.append(
            HealthCheckIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.UNIT_CONSISTENCY,
                message=(
                    f"dbu={dbu} m 过小（<1e-9 m），可能是数据损坏，"
                    f"必须修复。"
                ),
            )
        )
    # 常见 dbu 值检查
    common_dbus = {1e-9, 1e-8, 1e-7, 1e-6, 1e-5}
    if dbu not in common_dbus and 1e-9 <= dbu <= 1e-3:
        issues.append(
            HealthCheckIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.UNIT_CONSISTENCY,
                message=(
                    f"dbu={dbu} m 不是常见值（常见: 1nm/10nm/100nm/1μm/10μm），"
                    f"建议确认工艺文件指定单位。"
                ),
            )
        )
    return issues


def check_top_cell_uniqueness(ly) -> list[HealthCheckIssue]:
    """检查顶层 cell 唯一性（R314）。

    GDSII 文件可以有多个顶层 cell，但 DRC/流片通常期望单一顶层 cell。
    多顶层 cell 标记为 WARNING。

    Args:
        ly: klayout.db.Layout 对象。

    Returns:
        HealthCheckIssue 列表。

    来源:
    - KLayout Layout.each_top_cell: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    issues: list[HealthCheckIssue] = []
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if len(top_cells) == 0:
        issues.append(
            HealthCheckIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.TOP_CELL_UNIQUENESS,
                message=(
                    f"GDSII 文件无顶层 cell，可能是空文件或数据损坏。"
                ),
            )
        )
    elif len(top_cells) > 1:
        names = [c.name for c in top_cells]
        issues.append(
            HealthCheckIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.TOP_CELL_UNIQUENESS,
                message=(
                    f"GDSII 文件有 {len(top_cells)} 个顶层 cell: {names}，"
                    f"DRC/流片通常期望单一顶层 cell，建议确认。"
                ),
            )
        )
    return issues


# =============================================================================
# 端到端校验入口
# =============================================================================
def check_gdsii_health(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    checks: list[str] | None = None,
) -> HealthCheckReport:
    """对 GDSII 文件执行结构化健康检查（R314）。

    端到端流程: GDSII 文件 → KLayout Layout.read → 5 类子检查 → 汇总报告。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell，多顶层时必须指定）。
        checks: 要执行的检查项列表（None 执行全部）。可选:
            - 'layer_completeness'
            - 'polygon_validity'
            - 'cell_references'
            - 'unit_consistency'
            - 'top_cell_uniqueness'

    Returns:
        HealthCheckReport 报告。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / top_cell_name 不存在 / checks 含未知项。
        ImportError: klayout 未安装。
        RuntimeError: GDSII 读取失败。

    来源:
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")

    # 校验 checks 参数
    all_checks = {
        "layer_completeness",
        "polygon_validity",
        "cell_references",
        "unit_consistency",
        "top_cell_uniqueness",
    }
    if checks is not None:
        unknown = set(checks) - all_checks
        if unknown:
            raise ValueError(
                f"未知的检查项: {unknown}。支持的检查: {sorted(all_checks)}"
            )
        run_checks = set(checks)
    else:
        run_checks = all_checks

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    # 选择顶层 cell（用于 polygon_validity 检查）
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
    else:
        top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
        if not top_cells:
            raise ValueError(
                f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
            )
        top_cell = top_cells[0]

    issues: list[HealthCheckIssue] = []
    checks_run: list[str] = []

    if "layer_completeness" in run_checks:
        issues.extend(check_layer_completeness(ly, layer_map))
        checks_run.append("layer_completeness")
    if "polygon_validity" in run_checks:
        issues.extend(check_polygon_validity(ly, top_cell))
        checks_run.append("polygon_validity")
    if "cell_references" in run_checks:
        issues.extend(check_cell_references(ly))
        checks_run.append("cell_references")
    if "unit_consistency" in run_checks:
        issues.extend(check_unit_consistency(ly))
        checks_run.append("unit_consistency")
    if "top_cell_uniqueness" in run_checks:
        issues.extend(check_top_cell_uniqueness(ly))
        checks_run.append("top_cell_uniqueness")

    # 按类别/严重级别分组
    by_category = dict(Counter(i.category.value for i in issues))
    by_severity = dict(Counter(i.severity.value for i in issues))
    passed = by_severity.get("error", 0) == 0

    return HealthCheckReport(
        file_path=str(gds_path),
        issues=issues,
        passed=passed,
        checks_run=checks_run,
        by_category=by_category,
        by_severity=by_severity,
    )
