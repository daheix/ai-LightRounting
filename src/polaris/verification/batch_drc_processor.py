"""GDSII 批量 DRC 处理与报告聚合工具（R313）。

基于 R312 单文件 DRC 能力，扩展到多 GDSII 文件批量处理 + 多维度报告聚合。
适用于流片前对一批 GDSII 文件统一 DRC 检查并生成汇总报告。

R313 实现:
1. run_batch_drc(gds_paths, rules, config, layer_map) -> BatchDRCResult
   批量执行 DRC，逐文件调用 R312 run_drc_on_gdsii
2. aggregate_violations_by_rule(result) -> dict[str, int]
   跨文件按规则聚合违规数
3. aggregate_violations_by_layer(result) -> dict[str, int]
   跨文件按层聚合违规数
4. generate_batch_drc_report(result, output_format) -> str
   生成 text/markdown/json 三种格式报告
5. save_batch_drc_report(result, output_path, output_format) -> str
   保存报告到文件

设计模式（来源: Fowler, "Patterns of Enterprise Application Architecture", 2002）:
- Batch Pattern: 批量处理多个输入，逐个执行同质操作
- Aggregate Pattern: 跨多个结果集汇总统计
- Reporter Pattern: 将结构化数据渲染为多种输出格式

R03 合规:
- 空 gds_paths 列表 raise ValueError
- 文件不存在 raise FileNotFoundError（不跳过，禁止 fall-back）
- 不支持的 output_format raise ValueError
- 单文件 DRC 失败：将异常信息记录到 BatchDRCReport.error，继续处理其他文件
  （批处理语义：单文件失败不阻塞整批，但必须显式标记失败状态供业务判断）

R02 学术诚信:
- 批处理设计模式引用 Fowler 2002
- DRC 引擎引用 KLayout 官方文档
- 报告格式引用 Markdown CommonMark 与 JSON RFC 8259

来源:
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Fowler, "Patterns of Enterprise Application Architecture", 2002:
  https://martinfowler.com/books/eaa.html
- CommonMark Specification: https://spec.commonmark.org/
- JSON RFC 8259: https://datatracker.ietf.org/doc/html/rfc8259
- Python pathlib: https://docs.python.org/3/library/pathlib.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from polaris.verification._drc_rules import CurvilinearDRCRule
from polaris.verification.gdsii_drc_validator import drc_summary_from_gdsii
from polaris.verification.klayout_drc_bridge import KLayoutDRCConfig

logger = logging.getLogger(__name__)

__all__ = [
    "BatchDRCReport",
    "BatchDRCResult",
    "aggregate_violations_by_layer",
    "aggregate_violations_by_rule",
    "generate_batch_drc_report",
    "run_batch_drc",
    "save_batch_drc_report",
]


@dataclass
class BatchDRCReport:
    """单个 GDSII 文件的批量 DRC 报告（R313）。

    Attributes:
        file_path: GDSII 文件路径。
        summary: drc_summary_from_gdsii 返回的字典；失败时为 None。
        processing_time_s: 该文件 DRC 处理耗时（秒）。
        error: 失败时的异常信息字符串；成功时为 None。
        passed: 是否通过（summary.passed 且 error is None）。
    """

    file_path: str
    summary: dict[str, Any] | None = None
    processing_time_s: float = 0.0
    error: str | None = None
    passed: bool = False


@dataclass
class BatchDRCResult:
    """批量 DRC 处理结果（R313）。

    Attributes:
        reports: 各文件的 BatchDRCReport 列表（保持输入顺序）。
        total_files: 文件总数。
        passed_files: 通过文件数（error is None 且 summary.passed）。
        failed_files: 失败文件数（含 DRC 违规 error 或 DRC 失败 summary.passed=False）。
        total_violations: 所有文件违规总数。
        total_errors: 所有文件错误级违规总数。
        total_warnings: 所有文件警告级违规总数。
        total_time_s: 批处理总耗时（秒，含所有文件串行处理时间）。
    """

    reports: list[BatchDRCReport] = field(default_factory=list)
    total_files: int = 0
    passed_files: int = 0
    failed_files: int = 0
    total_violations: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_time_s: float = 0.0


def run_batch_drc(
    gds_paths: list[str | Path],
    rules: list[CurvilinearDRCRule],
    config: KLayoutDRCConfig | None = None,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_names: dict[str, str] | None = None,
) -> BatchDRCResult:
    """对多个 GDSII 文件批量执行 DRC 检查（R313）。

    串行处理每个文件：调用 R312 drc_summary_from_gdsii 生成单文件汇总，
    单文件失败时记录 error 但继续处理后续文件（批处理语义）。

    Args:
        gds_paths: GDSII 文件路径列表（保持顺序）。
        rules: DRC 规则列表。
        config: KLayout DRC 配置（None 用默认）。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_names: {file_path: top_cell_name} 映射，指定各文件的顶层 cell；
            未指定的文件用 None（自动取第一个 top cell）。

    Returns:
        BatchDRCResult 批量处理结果。

    Raises:
        ValueError: gds_paths 为空列表。
        FileNotFoundError: 任一文件不存在（批处理前预检，禁止 fall-back 跳过）。
        TypeError: gds_paths 不是列表/可迭代对象。

    来源:
    - 批处理模式: Fowler 2002 https://martinfowler.com/books/eaa.html
    - KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html
    """
    if not isinstance(gds_paths, (list, tuple)):
        raise TypeError(
            f"gds_paths 必须是列表或元组，得到 {type(gds_paths).__name__}"
        )
    if len(gds_paths) == 0:
        raise ValueError(
            "gds_paths 不能为空列表。批量 DRC 至少需要一个 GDSII 文件。"
        )

    # 预检：所有文件必须存在（R03: 禁止 fall-back 跳过缺失文件）
    path_objs = [Path(p) for p in gds_paths]
    for p in path_objs:
        if not p.exists():
            raise FileNotFoundError(
                f"GDSII 文件不存在: {p}。批量 DRC 禁止跳过缺失文件（R03）。"
            )
        if not p.is_file():
            raise ValueError(
                f"路径不是文件: {p}（可能是目录）。批量 DRC 仅支持 GDSII 文件。"
            )

    top_cell_map = top_cell_names or {}
    reports: list[BatchDRCReport] = []
    total_violations = 0
    total_errors = 0
    total_warnings = 0
    passed_files = 0
    failed_files = 0
    batch_start = time.perf_counter()

    for p in path_objs:
        file_start = time.perf_counter()
        # 取该文件对应的 top_cell_name（键支持 str 或 Path 形式）
        top_cell = top_cell_map.get(str(p)) or top_cell_map.get(p.name)
        report = BatchDRCReport(file_path=str(p))
        try:
            summary = drc_summary_from_gdsii(
                p,
                rules,
                config=config,
                layer_map=layer_map,
                top_cell_name=top_cell,
            )
            report.summary = summary
            report.passed = bool(summary.get("passed", False))
            total_violations += int(summary.get("total_violations", 0))
            total_errors += int(summary.get("errors", 0))
            total_warnings += int(summary.get("warnings", 0))
            if report.passed:
                passed_files += 1
            else:
                failed_files += 1
        except (FileNotFoundError, ValueError, RuntimeError, ImportError, KeyError) as e:
            # 批处理语义：单文件失败不阻塞整批，但显式标记 error 供业务判断
            # R03 合规：不静默吞异常，error 字段保留完整异常信息
            report.error = f"{type(e).__name__}: {e}"
            report.passed = False
            failed_files += 1
            logger.warning("批量 DRC 文件 %s 失败: %s", p, report.error)
        report.processing_time_s = time.perf_counter() - file_start
        reports.append(report)

    total_time = time.perf_counter() - batch_start
    return BatchDRCResult(
        reports=reports,
        total_files=len(path_objs),
        passed_files=passed_files,
        failed_files=failed_files,
        total_violations=total_violations,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_time_s=total_time,
    )


def aggregate_violations_by_rule(result: BatchDRCResult) -> dict[str, int]:
    """跨文件按规则聚合违规数（R313）。

    Args:
        result: 批量 DRC 结果。

    Returns:
        {rule_id: total_violation_count} 字典。

    Raises:
        TypeError: result 不是 BatchDRCResult。

    来源:
    - 聚合模式: Fowler 2002 https://martinfowler.com/books/eaa.html
    """
    if not isinstance(result, BatchDRCResult):
        raise TypeError(
            f"result 必须是 BatchDRCResult，得到 {type(result).__name__}"
        )
    agg: dict[str, int] = {}
    for report in result.reports:
        if report.summary is None:
            continue
        by_rule = report.summary.get("violations_by_rule", {})
        for rule_id, count in by_rule.items():
            agg[rule_id] = agg.get(rule_id, 0) + int(count)
    return agg


def aggregate_violations_by_layer(result: BatchDRCResult) -> dict[str, int]:
    """跨文件按层聚合违规数（R313）。

    Args:
        result: 批量 DRC 结果。

    Returns:
        {layer_name: total_violation_count} 字典。

    Raises:
        TypeError: result 不是 BatchDRCResult。

    来源:
    - 聚合模式: Fowler 2002 https://martinfowler.com/books/eaa.html
    """
    if not isinstance(result, BatchDRCResult):
        raise TypeError(
            f"result 必须是 BatchDRCResult，得到 {type(result).__name__}"
        )
    agg: dict[str, int] = {}
    for report in result.reports:
        if report.summary is None:
            continue
        by_layer = report.summary.get("violations_by_layer", {})
        for layer, count in by_layer.items():
            agg[layer] = agg.get(layer, 0) + int(count)
    return agg


def generate_batch_drc_report(
    result: BatchDRCResult,
    output_format: str = "text",
) -> str:
    """生成批量 DRC 报告字符串（R313）。

    Args:
        result: 批量 DRC 结果。
        output_format: 输出格式，'text' / 'markdown' / 'json'。

    Returns:
        报告字符串。

    Raises:
        TypeError: result 不是 BatchDRCResult。
        ValueError: output_format 不支持。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON RFC 8259: https://datatracker.ietf.org/doc/html/rfc8259
    """
    if not isinstance(result, BatchDRCResult):
        raise TypeError(
            f"result 必须是 BatchDRCResult，得到 {type(result).__name__}"
        )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(result)
    if fmt == "markdown":
        return _render_markdown_report(result)
    if fmt == "json":
        return _render_json_report(result)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持的格式: text / markdown / json。"
    )


def save_batch_drc_report(
    result: BatchDRCResult,
    output_path: str | Path,
    output_format: str = "text",
) -> str:
    """保存批量 DRC 报告到文件（R313）。

    Args:
        result: 批量 DRC 结果。
        output_path: 输出文件路径。
        output_format: 输出格式（text/markdown/json）。

    Returns:
        输出文件路径字符串。

    Raises:
        TypeError: result 不是 BatchDRCResult。
        ValueError: output_format 不支持 / 输出路径父目录不存在。
        OSError: 文件写入失败。

    来源:
    - Python pathlib: https://docs.python.org/3/library/pathlib.html
    """
    content = generate_batch_drc_report(result, output_format=output_format)
    out = Path(output_path)
    parent = out.parent
    if not parent.exists():
        raise ValueError(
            f"输出路径父目录不存在: {parent}。请先创建目录。"
        )
    if not parent.is_dir():
        raise ValueError(
            f"输出路径父路径不是目录: {parent}。"
        )
    out.write_text(content, encoding="utf-8")
    logger.info("批量 DRC 报告已保存: %s（格式: %s）", out, output_format)
    return str(out)


# =============================================================================
# 内部渲染函数
# =============================================================================
def _render_text_report(result: BatchDRCResult) -> str:
    """渲染纯文本报告。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("PoLaRIS 批量 GDSII DRC 报告")
    lines.append("=" * 70)
    lines.append(f"文件总数: {result.total_files}")
    lines.append(f"通过文件: {result.passed_files}")
    lines.append(f"失败文件: {result.failed_files}")
    lines.append(f"违规总数: {result.total_violations}")
    lines.append(f"错误级违规: {result.total_errors}")
    lines.append(f"警告级违规: {result.total_warnings}")
    lines.append(f"总耗时: {result.total_time_s:.3f}s")
    lines.append("")
    lines.append("-" * 70)
    lines.append("各文件详情:")
    lines.append("-" * 70)
    for r in result.reports:
        status = "PASS" if r.passed else "FAIL"
        if r.error:
            status = "ERROR"
        lines.append(f"[{status}] {r.file_path} ({r.processing_time_s:.3f}s)")
        if r.error:
            lines.append(f"  错误: {r.error}")
        elif r.summary:
            lines.append(
                f"  违规: {r.summary.get('total_violations', 0)} "
                f"(错误 {r.summary.get('errors', 0)} / "
                f"警告 {r.summary.get('warnings', 0)})"
            )
    lines.append("")
    # 按规则聚合
    by_rule = aggregate_violations_by_rule(result)
    if by_rule:
        lines.append("-" * 70)
        lines.append("跨文件按规则聚合:")
        lines.append("-" * 70)
        for rule_id, count in sorted(by_rule.items()):
            lines.append(f"  {rule_id}: {count}")
    # 按层聚合
    by_layer = aggregate_violations_by_layer(result)
    if by_layer:
        lines.append("")
        lines.append("-" * 70)
        lines.append("跨文件按层聚合:")
        lines.append("-" * 70)
        for layer, count in sorted(by_layer.items()):
            lines.append(f"  {layer}: {count}")
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(result: BatchDRCResult) -> str:
    """渲染 Markdown 报告（CommonMark 规范）。"""
    lines: list[str] = []
    lines.append("# PoLaRIS 批量 GDSII DRC 报告")
    lines.append("")
    lines.append("## 概览")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 文件总数 | {result.total_files} |")
    lines.append(f"| 通过文件 | {result.passed_files} |")
    lines.append(f"| 失败文件 | {result.failed_files} |")
    lines.append(f"| 违规总数 | {result.total_violations} |")
    lines.append(f"| 错误级违规 | {result.total_errors} |")
    lines.append(f"| 警告级违规 | {result.total_warnings} |")
    lines.append(f"| 总耗时 | {result.total_time_s:.3f}s |")
    lines.append("")
    lines.append("## 各文件详情")
    lines.append("")
    lines.append("| 状态 | 文件 | 耗时(s) | 违规 | 错误 | 警告 | 备注 |")
    lines.append("|------|------|---------|------|------|------|------|")
    for r in result.reports:
        if r.error:
            status = "ERROR"
            violations = "-"
            errors = "-"
            warnings = "-"
            note = r.error
        else:
            status = "PASS" if r.passed else "FAIL"
            violations = r.summary.get("total_violations", 0) if r.summary else 0
            errors = r.summary.get("errors", 0) if r.summary else 0
            warnings = r.summary.get("warnings", 0) if r.summary else 0
            note = ""
        lines.append(
            f"| {status} | {r.file_path} | {r.processing_time_s:.3f} | "
            f"{violations} | {errors} | {warnings} | {note} |"
        )
    lines.append("")
    by_rule = aggregate_violations_by_rule(result)
    if by_rule:
        lines.append("## 跨文件按规则聚合")
        lines.append("")
        lines.append("| 规则 ID | 违规总数 |")
        lines.append("|---------|----------|")
        for rule_id, count in sorted(by_rule.items()):
            lines.append(f"| {rule_id} | {count} |")
        lines.append("")
    by_layer = aggregate_violations_by_layer(result)
    if by_layer:
        lines.append("## 跨文件按层聚合")
        lines.append("")
        lines.append("| 层名 | 违规总数 |")
        lines.append("|------|----------|")
        for layer, count in sorted(by_layer.items()):
            lines.append(f"| {layer} | {count} |")
        lines.append("")
    return "\n".join(lines)


def _render_json_report(result: BatchDRCResult) -> str:
    """渲染 JSON 报告（RFC 8259）。"""
    payload = {
        "overview": {
            "total_files": result.total_files,
            "passed_files": result.passed_files,
            "failed_files": result.failed_files,
            "total_violations": result.total_violations,
            "total_errors": result.total_errors,
            "total_warnings": result.total_warnings,
            "total_time_s": result.total_time_s,
        },
        "reports": [asdict(r) for r in result.reports],
        "aggregations": {
            "by_rule": aggregate_violations_by_rule(result),
            "by_layer": aggregate_violations_by_layer(result),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
