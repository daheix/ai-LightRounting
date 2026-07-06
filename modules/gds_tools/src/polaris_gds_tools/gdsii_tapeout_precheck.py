"""GDSII 流片前预检查工具（R329，Tape-out Pre-check）。

整合 R314（健康检查）、R322（层次分析）、R325（网格对齐）为一站式流片前
综合检查工具，提供 pass/fail 汇总与详细报告。

## 核心概念

- **流片前预检查（Tape-out Pre-check）**: 流片前对 GDSII 做综合检查，确保版图
  满足制造要求。工业 EDA 工具（Calibre、KLayout、SiEPIC）均提供类似功能。
- **检查项**: 网格对齐（grid）、结构健康（health）、层次完整性（hierarchy）
- **Pass 判定**: 所有启用的检查项均通过

## 算法

1. 验证输入文件与检查项
2. 按检查项调用对应工具:
   - 'grid': R325 check_grid_alignment
   - 'health': R314 check_gdsii_health
   - 'hierarchy': R322 analyze_cell_hierarchy
3. 汇总各检查结果，判定总体 pass/fail
4. 生成 text/markdown 报告

## Pass 判定规则

- grid: total_violations == 0
- health: passed == True（无 ERROR 级别 issue）
- hierarchy: not has_circular_reference

## 学术依据

- KLayout DRC Reference:
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
- Calibre DRC 流片前检查:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK 流片流程:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- KLayout Layout.read:
  https://www.klayout.de/doc.html
- KLayout Cell class:
  https://www.klayout.de/doc.html
- OpenROAD Sign-off:
  https://openroad.readthedocs.io/en/latest/main/src/src.html
- CommonMark 规范:
  https://spec.commonmark.org/

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris_gds_tools.gdsii_cell_hierarchy_analyzer import (
    HierarchyReport,
    analyze_cell_hierarchy,
)
from polaris_gds_tools.gdsii_grid_alignment_checker import (
    GridCheckReport,
    check_grid_alignment,
)
from polaris_gds_tools.gdsii_health_check import (
    HealthCheckReport,
    check_gdsii_health,
)

logger = logging.getLogger(__name__)

__all__ = [
    "TapeoutReport",
    "tapeout_precheck",
    "generate_tapeout_report",
]


# 所有支持的检查项
ALL_CHECKS: dict[str, str] = {
    "grid": "网格对齐检查（R325）",
    "health": "结构健康检查（R314）",
    "hierarchy": "层次完整性检查（R322）",
}


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class TapeoutReport:
    """GDSII 流片前预检查报告（R329）。

    Attributes:
        file_path: GDSII 文件路径。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        checks_run: 执行的检查项列表。
        grid_report: 网格对齐检查报告（None=未执行）。
        health_report: 健康检查报告（None=未执行）。
        hierarchy_report: 层次分析报告（None=未执行）。
        passed: 总体是否通过（所有启用的检查均通过）。
        grid_passed: 网格检查是否通过（None=未执行）。
        health_passed: 健康检查是否通过（None=未执行）。
        hierarchy_passed: 层次检查是否通过（None=未执行）。
        error_count: 错误总数（grid violations + health ERROR + 循环引用）。
        warning_count: 警告总数（health WARNING）。
    """

    file_path: str
    dbu: float = 0.0
    top_cell_name: str = ""
    checks_run: list[str] = field(default_factory=list)
    grid_report: GridCheckReport | None = None
    health_report: HealthCheckReport | None = None
    hierarchy_report: HierarchyReport | None = None
    passed: bool = True
    grid_passed: bool | None = None
    health_passed: bool | None = None
    hierarchy_passed: bool | None = None
    error_count: int = 0
    warning_count: int = 0


# =============================================================================
# 流片前预检查
# =============================================================================
def tapeout_precheck(
    gds_path: str | Path,
    grid_um: float = 0.005,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    checks: list[str] | None = None,
) -> TapeoutReport:
    """对 GDSII 文件执行流片前综合预检查（R329）。

    整合 R314（健康检查）、R322（层次分析）、R325（网格对齐）为一站式检查。

    Args:
        gds_path: GDSII 文件路径。
        grid_um: 网格检查的网格（μm，默认 0.005=5nm）。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。
        checks: 要执行的检查项列表（None 执行全部）。可选:
            - 'grid': 网格对齐检查
            - 'health': 结构健康检查
            - 'hierarchy': 层次完整性检查

    Returns:
        TapeoutReport 综合报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / checks 含未知项 / grid_um <= 0。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout DRC Reference:
      https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
    - Calibre DRC:
      https://www.mentor.com/products/ic_nanometer_design/calibre-drc
    """
    path, run_checks = _validate_tapeout_params(gds_path, grid_um, checks)
    grid_report, health_report, hierarchy_report = _run_tapeout_checks(
        gds_path, grid_um, layer_map, top_cell_name, run_checks,
    )
    grid_passed, health_passed, hierarchy_passed, error_count, warning_count = (
        _compute_tapeout_results(grid_report, health_report, hierarchy_report)
    )
    # 总体 pass: 所有执行的检查均通过
    partial_results = [
        r for r in [grid_passed, health_passed, hierarchy_passed]
        if r is not None
    ]
    passed = all(partial_results) if partial_results else True
    dbu, top_name = _resolve_tapeout_dbu_topname(
        grid_report, hierarchy_report,
    )
    logger.info(
        "流片前预检查: %s (checks=%s, passed=%s, errors=%d, warnings=%d)",
        path, run_checks, passed, error_count, warning_count,
    )
    return TapeoutReport(
        file_path=str(gds_path),
        dbu=dbu,
        top_cell_name=top_name,
        checks_run=run_checks,
        grid_report=grid_report,
        health_report=health_report,
        hierarchy_report=hierarchy_report,
        passed=passed,
        grid_passed=grid_passed,
        health_passed=health_passed,
        hierarchy_passed=hierarchy_passed,
        error_count=error_count,
        warning_count=warning_count,
    )


def _validate_tapeout_params(gds_path, grid_um, checks) -> tuple:
    """校验 tapeout_precheck 入参（R329 内部辅助，R03 禁止 fall-back）。

    Returns:
        (path, run_checks)。
    """
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if grid_um <= 0:
        raise ValueError(
            f"grid_um 必须 > 0，得到 {grid_um}。禁止 fall-back（R03）。"
        )
    # 校验 checks 参数
    if checks is not None:
        if not checks:
            raise ValueError(
                "checks 不能为空列表。禁止 fall-back（R03）。"
                f"支持: {sorted(ALL_CHECKS.keys())}"
            )
        unknown = set(checks) - set(ALL_CHECKS.keys())
        if unknown:
            raise ValueError(
                f"未知的检查项: {sorted(unknown)}。"
                f"支持的检查: {sorted(ALL_CHECKS.keys())}"
            )
        run_checks = list(checks)
    else:
        run_checks = list(ALL_CHECKS.keys())
    return path, run_checks


def _run_tapeout_checks(
    gds_path, grid_um, layer_map, top_cell_name, run_checks,
) -> tuple:
    """执行各检查项（每项独立，一项失败不影响其他项，R329 内部辅助）。

    Returns:
        (grid_report, health_report, hierarchy_report)，未执行的为 None。

    来源:
    - R325 check_grid_alignment: 网格对齐
    - R314 check_gdsii_health: 结构健康
    - R322 analyze_cell_hierarchy: 层次完整性
    """
    grid_report: GridCheckReport | None = None
    health_report: HealthCheckReport | None = None
    hierarchy_report: HierarchyReport | None = None
    if "grid" in run_checks:
        grid_report = check_grid_alignment(
            gds_path,
            grid_um=grid_um,
            layer_map=layer_map,
            top_cell_name=top_cell_name,
        )
    if "health" in run_checks:
        health_report = check_gdsii_health(
            gds_path,
            layer_map=layer_map,
            top_cell_name=top_cell_name,
        )
    if "hierarchy" in run_checks:
        hierarchy_report = analyze_cell_hierarchy(
            gds_path,
            top_cell_name=top_cell_name,
        )
    return grid_report, health_report, hierarchy_report


def _compute_tapeout_results(
    grid_report, health_report, hierarchy_report,
) -> tuple:
    """判定各项 pass/fail 并统计 error/warning（R329 内部辅助）。

    Returns:
        (grid_passed, health_passed, hierarchy_passed,
         error_count, warning_count)。

    Pass 判定规则:
    - grid: total_violations == 0
    - health: passed == True（无 ERROR 级别 issue）
    - hierarchy: not has_circular_reference
    """
    grid_passed: bool | None = None
    if grid_report is not None:
        grid_passed = grid_report.total_violations == 0
    health_passed: bool | None = None
    if health_report is not None:
        health_passed = health_report.passed
    hierarchy_passed: bool | None = None
    if hierarchy_report is not None:
        hierarchy_passed = not hierarchy_report.has_circular_reference
    # 统计错误/警告
    error_count = 0
    warning_count = 0
    if grid_report is not None:
        error_count += grid_report.total_violations
    if health_report is not None:
        # by_severity 的 key 是 str(Severity enum)，含 'ERROR'/'WARNING'/'INFO'
        for sev, cnt in health_report.by_severity.items():
            sev_str = str(sev).upper()
            if "ERROR" in sev_str:
                error_count += cnt
            elif "WARN" in sev_str:
                warning_count += cnt
    if hierarchy_report is not None and hierarchy_report.has_circular_reference:
        error_count += len(hierarchy_report.circular_chains)
    return (grid_passed, health_passed, hierarchy_passed,
            error_count, warning_count)


def _resolve_tapeout_dbu_topname(grid_report, hierarchy_report) -> tuple:
    """从可用报告获取 dbu 和 top_cell_name（R329 内部辅助）。

    Returns:
        (dbu, top_name)。
    """
    dbu = 0.0
    top_name = ""
    if grid_report is not None:
        dbu = grid_report.dbu
        top_name = grid_report.top_cell_name
    elif hierarchy_report is not None:
        dbu = hierarchy_report.dbu
        top_name = (
            hierarchy_report.top_cell_names[0]
            if hierarchy_report.top_cell_names else ""
        )
    return dbu, top_name


# =============================================================================
# 报告生成
# =============================================================================
def generate_tapeout_report(
    gds_path: str | Path,
    grid_um: float = 0.005,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    checks: list[str] | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 流片前预检查报告（R329）。

    Args:
        gds_path: GDSII 文件路径。
        grid_um: 网格检查的网格（μm）。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。
        checks: 要执行的检查项列表。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式 / checks 含未知项 / grid_um <= 0。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = tapeout_precheck(
        gds_path,
        grid_um=grid_um,
        layer_map=layer_map,
        top_cell_name=top_cell_name,
        checks=checks,
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
# 内部渲染函数
# =============================================================================
def _render_text_report(report: TapeoutReport) -> str:
    """渲染纯文本报告（R329 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 流片前预检查报告")
    lines.append("=" * 60)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"执行检查: {', '.join(report.checks_run)}")
    status = "通过" if report.passed else "失败"
    lines.append(f"总体状态: {status}")
    lines.append(f"错误数: {report.error_count}")
    lines.append(f"警告数: {report.warning_count}")
    lines.append("")

    if report.grid_report is not None:
        lines.append("-" * 60)
        lines.append("[网格对齐检查 R325]")
        lines.append("-" * 60)
        g = report.grid_report
        g_status = "通过" if report.grid_passed else "失败"
        lines.append(f"  状态: {g_status}")
        lines.append(f"  网格: {g.grid_um} μm ({g.grid_dbu} dbu)")
        lines.append(f"  检查 shapes: {g.total_shapes_checked}")
        lines.append(f"  违规数: {g.total_violations}")
        if g.layer_violation_counts:
            lines.append(f"  按层违规: {g.layer_violation_counts}")
        lines.append("")

    if report.health_report is not None:
        lines.append("-" * 60)
        lines.append("[结构健康检查 R314]")
        lines.append("-" * 60)
        h = report.health_report
        h_status = "通过" if report.health_passed else "失败"
        lines.append(f"  状态: {h_status}")
        lines.append(f"  执行检查: {', '.join(h.checks_run)}")
        lines.append(f"  问题总数: {len(h.issues)}")
        if h.by_severity:
            lines.append(f"  按严重级别: {dict(h.by_severity)}")
        if h.by_category:
            lines.append(f"  按类别: {dict(h.by_category)}")
        lines.append("")

    if report.hierarchy_report is not None:
        lines.append("-" * 60)
        lines.append("[层次完整性检查 R322]")
        lines.append("-" * 60)
        hier = report.hierarchy_report
        hier_status = "通过" if report.hierarchy_passed else "失败"
        lines.append(f"  状态: {hier_status}")
        lines.append(f"  cell 总数: {hier.total_cell_count}")
        lines.append(f"  最大层级深度: {hier.max_hierarchy_depth}")
        lines.append(f"  顶层 cells: {hier.top_cell_names}")
        circ = "有" if hier.has_circular_reference else "无"
        lines.append(f"  循环引用: {circ}")
        if hier.has_circular_reference:
            lines.append(f"  循环链: {hier.circular_chains}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: TapeoutReport) -> str:
    """渲染 Markdown 报告（R329 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 流片前预检查报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**顶层 cell**: `{report.top_cell_name}`")
    lines.append(f"**执行检查**: {', '.join(report.checks_run)}")
    status = "通过" if report.passed else "失败"
    lines.append(f"**总体状态**: {status}")
    lines.append(f"**错误数**: {report.error_count}")
    lines.append(f"**警告数**: {report.warning_count}")
    lines.append("")

    if report.grid_report is not None:
        lines.append("## 网格对齐检查（R325）")
        lines.append("")
        g = report.grid_report
        g_status = "通过" if report.grid_passed else "失败"
        lines.append(f"- **状态**: {g_status}")
        lines.append(f"- **网格**: {g.grid_um} μm ({g.grid_dbu} dbu)")
        lines.append(f"- **检查 shapes**: {g.total_shapes_checked}")
        lines.append(f"- **违规数**: {g.total_violations}")
        if g.layer_violation_counts:
            lines.append(f"- **按层违规**: {g.layer_violation_counts}")
        lines.append("")

    if report.health_report is not None:
        lines.append("## 结构健康检查（R314）")
        lines.append("")
        h = report.health_report
        h_status = "通过" if report.health_passed else "失败"
        lines.append(f"- **状态**: {h_status}")
        lines.append(f"- **执行检查**: {', '.join(h.checks_run)}")
        lines.append(f"- **问题总数**: {len(h.issues)}")
        if h.by_severity:
            lines.append(f"- **按严重级别**: {dict(h.by_severity)}")
        if h.by_category:
            lines.append(f"- **按类别**: {dict(h.by_category)}")
        lines.append("")

    if report.hierarchy_report is not None:
        lines.append("## 层次完整性检查（R322）")
        lines.append("")
        hier = report.hierarchy_report
        hier_status = "通过" if report.hierarchy_passed else "失败"
        lines.append(f"- **状态**: {hier_status}")
        lines.append(f"- **cell 总数**: {hier.total_cell_count}")
        lines.append(f"- **最大层级深度**: {hier.max_hierarchy_depth}")
        lines.append(f"- **顶层 cells**: {hier.top_cell_names}")
        circ = "有" if hier.has_circular_reference else "无"
        lines.append(f"- **循环引用**: {circ}")
        if hier.has_circular_reference:
            lines.append(f"- **循环链**: {hier.circular_chains}")
        lines.append("")

    lines.append("---")
    return "\n".join(lines)
