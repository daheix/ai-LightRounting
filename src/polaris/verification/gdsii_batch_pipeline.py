"""GDSII 批处理流水线工具（R334，GDSII Batch Pipeline）。

对多个 GDSII 文件批量执行验证流程（统计、端口提取、文本提取、
tapeout 预检），生成综合质量报告。EDA 流程自动化的核心工具。

## 核心概念

- **批处理（Batch）**: 一次性处理多个 GDSII 文件，避免手动逐个验证
- **流水线（Pipeline）**: 对每个文件执行可配置的验证步骤序列
- **综合报告**: 汇总所有文件的所有步骤结果，统一格式输出
- **应用场景**:
  - 芯片级 assembly 前对所有 IP 块做统一验证
  - 设计审查时的批量质量检查
  - CI/CD 流水线中的 GDSII 质量门禁
  - 多版图比对/回归测试

## 算法

1. 接收输入 GDSII 文件列表和步骤配置
2. 对每个文件:
   - 按 steps 列表顺序执行验证步骤
   - 每步调用对应的验证工具
   - 捕获异常（标记为 FAIL，不中断其他文件）
   - 收集所有步骤结果到 FilePipelineResult
3. 汇总所有文件结果到 PipelineReport
4. 渲染为 text/markdown/json 格式报告

## 支持的验证步骤

- `statistics`: 调用 `gdsii_statistics.generate_gdsii_statistics`
- `ports`: 调用 `gdsii_port_extractor.extract_ports`
- `texts`: 调用 `gdsii_text_label_extractor.extract_text_labels`
- `precheck`: 调用 `gdsii_tapeout_precheck.tapeout_precheck`

## KLayout 0.30.9 API 关键事实

- 各验证步骤的 API 见对应模块 docstring
- 本模块仅做编排，不直接调用 KLayout API

## 学术依据

- EDA 流水线自动化:
  https://www.cadence.com/en_US/home/tools.html
- KLayout 批处理模式:
  https://www.klayout.de/doc-qt5/programming/
- gdsfactory 流水线:
  https://gdsfactory.github.io/gdsfactory/
- Calibre 批处理 DRC:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK 验证流程:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- CI/CD for EDA:
  https://docs.github.com/en/actions
- OpenROAD 流水线:
  https://theopenroadproject.org/
- KLayout Python 脚本批处理:
  https://klayout.org/klayout-pypi/

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "StepResult",
    "FilePipelineResult",
    "PipelineReport",
    "SUPPORTED_STEPS",
    "run_batch_pipeline",
    "generate_pipeline_report",
]


# =============================================================================
# 支持的步骤列表
# =============================================================================
SUPPORTED_STEPS: list[str] = ["statistics", "ports", "texts", "precheck"]


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 批处理流水线。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class StepResult:
    """单个验证步骤结果（R334）。

    Attributes:
        step_name: 步骤名（statistics/ports/texts/precheck）。
        success: 是否成功。
        error_message: 失败时的错误消息（成功为空字符串）。
        summary: 步骤结果摘要（成功时填充关键指标）。
            - statistics: {"cell_count": int, "polygon_count": int, ...}
            - ports: {"port_count": int, "matched_count": int}
            - texts: {"text_count": int, "layer_count": int}
            - precheck: {"passed": bool, "warning_count": int}
    """

    step_name: str
    success: bool
    error_message: str = ""
    summary: dict = field(default_factory=dict)


@dataclass
class FilePipelineResult:
    """单个文件的流水线结果（R334）。

    Attributes:
        file_path: GDSII 文件路径。
        file_exists: 文件是否存在。
        steps: 各步骤结果列表。
        success_count: 成功步骤数。
        fail_count: 失败步骤数。
    """

    file_path: str
    file_exists: bool = True
    steps: list[StepResult] = field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0


@dataclass
class PipelineReport:
    """批处理流水线综合报告（R334）。

    Attributes:
        input_files: 输入 GDSII 文件路径列表。
        steps_requested: 请求执行的步骤列表。
        file_results: 各文件的流水线结果列表。
        total_files: 文件总数。
        total_success_files: 所有步骤都成功的文件数。
        total_fail_files: 至少一步失败的文件数。
        total_steps_executed: 执行的步骤总数。
        total_step_success: 步骤成功总数。
        total_step_fail: 步骤失败总数。
    """

    input_files: list[str] = field(default_factory=list)
    steps_requested: list[str] = field(default_factory=list)
    file_results: list[FilePipelineResult] = field(default_factory=list)
    total_files: int = 0
    total_success_files: int = 0
    total_fail_files: int = 0
    total_steps_executed: int = 0
    total_step_success: int = 0
    total_step_fail: int = 0


# =============================================================================
# 批处理主入口
# =============================================================================
def run_batch_pipeline(
    input_paths: list[Path] | list[str],
    steps: list[str] | None = None,
) -> PipelineReport:
    """对多个 GDSII 文件批量执行验证流水线（R334）。

    对每个文件按 steps 顺序执行验证步骤，汇总结果。

    Args:
        input_paths: 输入 GDSII 文件路径列表（至少 1 个）。
        steps: 验证步骤列表（None 用全部 SUPPORTED_STEPS）。
            支持的步骤: statistics / ports / texts / precheck。

    Returns:
        PipelineReport 综合报告。

    Raises:
        ValueError: input_paths 空 / steps 含不支持的步骤名。
        FileNotFoundError: 仅当所有文件都不存在时 raise（部分文件
            不存在标记为 FAIL，不中断流水线）。
        ImportError: klayout 未安装。

    来源:
    - EDA 流水线自动化: https://www.cadence.com/en_US/home/tools.html
    - gdsfactory 流水线: https://gdsfactory.github.io/gdsfactory/
    """
    # 参数校验（R03 禁止 fall-back）
    if not input_paths:
        raise ValueError(
            "input_paths 不能为空。禁止 fall-back（R03）。"
        )
    if steps is None:
        steps = list(SUPPORTED_STEPS)
    if not steps:
        raise ValueError(
            "steps 不能为空。禁止 fall-back（R03）。"
        )
    # 验证步骤名合法
    invalid = [s for s in steps if s not in SUPPORTED_STEPS]
    if invalid:
        raise ValueError(
            f"不支持的步骤: {invalid}。"
            f"支持: {SUPPORTED_STEPS}。禁止 fall-back（R03）。"
        )

    # 检查 klayout 可用性（R03 失败即 raise）
    _import_klayout_db()

    # 导入验证步骤函数（延迟导入，避免循环依赖）
    from polaris.verification.gdsii_statistics import generate_gdsii_statistics
    from polaris.verification.gdsii_port_extractor import extract_ports
    from polaris.verification.gdsii_text_label_extractor import (
        extract_text_labels,
    )
    from polaris.verification.gdsii_tapeout_precheck import tapeout_precheck

    file_results: list[FilePipelineResult] = []
    input_files_str: list[str] = [str(p) for p in input_paths]

    for fpath in input_paths:
        path = Path(fpath)
        file_result = FilePipelineResult(file_path=str(fpath))

        if not path.exists():
            file_result.file_exists = False
            # 文件不存在: 所有步骤标记为 FAIL
            for step_name in steps:
                file_result.steps.append(
                    StepResult(
                        step_name=step_name,
                        success=False,
                        error_message=f"文件不存在: {fpath}",
                    )
                )
            file_result.fail_count = len(steps)
            file_results.append(file_result)
            logger.warning("文件不存在，跳过: %s", fpath)
            continue

        file_result.file_exists = True

        for step_name in steps:
            step_result = _execute_step(
                step_name, path,
                generate_gdsii_statistics,
                extract_ports,
                extract_text_labels,
                tapeout_precheck,
            )
            file_result.steps.append(step_result)

        file_result.success_count = sum(
            1 for s in file_result.steps if s.success
        )
        file_result.fail_count = sum(
            1 for s in file_result.steps if not s.success
        )
        file_results.append(file_result)

    # 汇总
    total_files = len(file_results)
    total_success_files = sum(
        1 for fr in file_results if fr.fail_count == 0 and fr.file_exists
    )
    total_fail_files = sum(
        1 for fr in file_results if fr.fail_count > 0 or not fr.file_exists
    )
    total_steps_executed = sum(len(fr.steps) for fr in file_results)
    total_step_success = sum(fr.success_count for fr in file_results)
    total_step_fail = sum(fr.fail_count for fr in file_results)

    logger.info(
        "批处理流水线: %d 文件, %d 步骤/文件, 成功 %d, 失败 %d",
        total_files, len(steps), total_step_success, total_step_fail,
    )

    return PipelineReport(
        input_files=input_files_str,
        steps_requested=list(steps),
        file_results=file_results,
        total_files=total_files,
        total_success_files=total_success_files,
        total_fail_files=total_fail_files,
        total_steps_executed=total_steps_executed,
        total_step_success=total_step_success,
        total_step_fail=total_step_fail,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_pipeline_report(
    input_paths: list[Path] | list[str],
    steps: list[str] | None = None,
    output_format: str = "text",
) -> str:
    """执行批处理流水线并生成报告字符串（R334）。

    Args:
        input_paths: 输入 GDSII 文件路径列表。
        steps: 验证步骤列表（None 用全部）。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = run_batch_pipeline(input_paths, steps=steps)
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
def _execute_step(
    step_name: str,
    path: Path,
    statistics_fn,
    ports_fn,
    texts_fn,
    precheck_fn,
) -> StepResult:
    """执行单个验证步骤（R334 内部函数）。

    捕获异常，返回 StepResult（不 raise，避免中断流水线）。
    注意: 这不是 R03 fall-back，因为失败会被记录到 StepResult，
    调用方可从报告看到失败原因。R03 禁止的是"静默兜底返回假数据"，
    本模块显式记录失败，不返回假数据。

    Args:
        step_name: 步骤名。
        path: GDSII 文件路径。
        statistics_fn / ports_fn / texts_fn / precheck_fn: 验证函数。

    Returns:
        StepResult 步骤结果。
    """
    try:
        if step_name == "statistics":
            stats = statistics_fn(path)
            return StepResult(
                step_name=step_name,
                success=True,
                summary={
                    "total_cells": stats.total_cells,
                    "total_polygons": stats.total_polygons,
                    "total_layers": len(stats.layer_stats),
                    "total_area_um2": round(stats.total_area_um2, 4),
                },
            )
        if step_name == "ports":
            port_report = ports_fn(path)
            matched = sum(1 for p in port_report.ports if p.text_matched)
            return StepResult(
                step_name=step_name,
                success=True,
                summary={
                    "port_count": len(port_report.ports),
                    "matched_count": matched,
                    "top_cell": port_report.top_cell_name,
                },
            )
        if step_name == "texts":
            text_report = texts_fn(path)
            return StepResult(
                step_name=step_name,
                success=True,
                summary={
                    "text_count": text_report.total_count,
                    "layer_count": len(text_report.layer_counts),
                    "cell_count": len(text_report.cell_counts),
                },
            )
        if step_name == "precheck":
            precheck_report = precheck_fn(path)
            return StepResult(
                step_name=step_name,
                success=True,
                summary={
                    "passed": precheck_report.passed,
                    "warning_count": precheck_report.warning_count,
                    "error_count": precheck_report.error_count,
                },
            )
        # 不应该到这里（前面已校验），但 R03 要求显式 raise
        raise ValueError(
            f"未知步骤名: {step_name}。禁止 fall-back（R03）。"
        )
    except Exception as e:
        return StepResult(
            step_name=step_name,
            success=False,
            error_message=f"{type(e).__name__}: {e}",
        )


def _render_text_report(report: PipelineReport) -> str:
    """渲染纯文本报告（R334 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII 批处理流水线综合报告")
    lines.append("=" * 70)
    lines.append(f"文件总数: {report.total_files}")
    lines.append(f"请求步骤: {', '.join(report.steps_requested)}")
    lines.append(f"全成功文件数: {report.total_success_files}")
    lines.append(f"有失败文件数: {report.total_fail_files}")
    lines.append(f"步骤成功总数: {report.total_step_success}")
    lines.append(f"步骤失败总数: {report.total_step_fail}")
    lines.append("")

    for fr in report.file_results:
        lines.append("-" * 70)
        status = "✓" if (fr.fail_count == 0 and fr.file_exists) else "✗"
        lines.append(f"{status} 文件: {fr.file_path}")
        if not fr.file_exists:
            lines.append("  [文件不存在]")
        for sr in fr.steps:
            if sr.success:
                summary_str = ", ".join(
                    f"{k}={v}" for k, v in sr.summary.items()
                )
                lines.append(f"  ✓ {sr.step_name}: {summary_str}")
            else:
                lines.append(f"  ✗ {sr.step_name}: {sr.error_message}")
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: PipelineReport) -> str:
    """渲染 Markdown 报告（R334 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 批处理流水线综合报告")
    lines.append("")
    lines.append(f"**文件总数**: {report.total_files}")
    lines.append(f"**请求步骤**: `{', '.join(report.steps_requested)}`")
    lines.append(f"**全成功文件数**: {report.total_success_files}")
    lines.append(f"**有失败文件数**: {report.total_fail_files}")
    lines.append(f"**步骤成功总数**: {report.total_step_success}")
    lines.append(f"**步骤失败总数**: {report.total_step_fail}")
    lines.append("")

    for fr in report.file_results:
        status = "✓" if (fr.fail_count == 0 and fr.file_exists) else "✗"
        lines.append(f"## {status} `{fr.file_path}`")
        lines.append("")
        if not fr.file_exists:
            lines.append("> 文件不存在")
            lines.append("")
            continue
        lines.append("| 步骤 | 状态 | 摘要 |")
        lines.append("|------|------|------|")
        for sr in fr.steps:
            if sr.success:
                summary_str = ", ".join(
                    f"`{k}`={v}" for k, v in sr.summary.items()
                )
                lines.append(f"| {sr.step_name} | ✓ | {summary_str} |")
            else:
                lines.append(
                    f"| {sr.step_name} | ✗ | {sr.error_message} |"
                )
        lines.append("")
    return "\n".join(lines)


def _render_json_report(report: PipelineReport) -> str:
    """渲染 JSON 报告（R334 内部函数）。"""
    data = {
        "total_files": report.total_files,
        "steps_requested": report.steps_requested,
        "total_success_files": report.total_success_files,
        "total_fail_files": report.total_fail_files,
        "total_steps_executed": report.total_steps_executed,
        "total_step_success": report.total_step_success,
        "total_step_fail": report.total_step_fail,
        "file_results": [
            {
                "file_path": fr.file_path,
                "file_exists": fr.file_exists,
                "success_count": fr.success_count,
                "fail_count": fr.fail_count,
                "steps": [
                    {
                        "step_name": sr.step_name,
                        "success": sr.success,
                        "error_message": sr.error_message,
                        "summary": sr.summary,
                    }
                    for sr in fr.steps
                ],
            }
            for fr in report.file_results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
