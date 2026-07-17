"""GDSII 边缘提取报告渲染器（R342，从 gdsii_edge_extractor 拆分）。

本模块负责将 ``EdgeExtractionReport`` 渲染为纯文本 / Markdown / JSON 字符串，
从 ``gdsii_edge_extractor.py`` 拆分以满足 R11 质量门禁（单文件 ≤800 行）。

## 渲染格式

- **text**: 等宽对齐的纯文本报告（适合终端输出与日志）
- **markdown**: CommonMark 兼容的 Markdown 表格报告（适合文档与 PR 评论）
- **json**: 结构化 JSON（适合程序消费与 API 返回）

## 学术依据

- CommonMark 规范: https://spec.commonmark.org/
- GitHub Flavored Markdown: https://github.github.com/gfm/
- JSON 标准 (ECMA-404): https://www.json.org/
- KLayout Database API（边缘提取数据源 ``EdgeExtractionReport`` 的上游）:
  https://www.klayout.de/doc.html
- gdsfactory GDSII 生态（边缘/轮廓提取流程参考）:
  https://gdsfactory.github.io/gdsfactory/

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polaris_gds_tools.gdsii_edge_extractor import EdgeExtractionReport


def render_text_report(report: "EdgeExtractionReport") -> str:
    """渲染纯文本报告。

    Args:
        report: ``EdgeExtractionReport`` 实例。

    Returns:
        多行纯文本字符串。
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 边缘提取报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    if report.output_path:
        lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(
        f"layer: ({report.layer[0]},{report.layer[1]})"
    )
    if report.layer_result:
        lines.append(
            f"layer_result: ({report.layer_result[0]},{report.layer_result[1]})"
        )
    lines.append("")
    lines.append("-" * 60)
    lines.append("过滤参数")
    lines.append("-" * 60)
    min_str = f"{report.min_length_um:.6f} μm" if report.min_length_um > 0 else "无"
    max_str = f"{report.max_length_um:.6f} μm" if report.max_length_um > 0 else "无"
    orient_str = report.orientation_filter or "无"
    lines.append(f"  min_length: {min_str}")
    lines.append(f"  max_length: {max_str}")
    lines.append(f"  orientation: {orient_str}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("统计")
    lines.append("-" * 60)
    lines.append(
        f"  过滤前边数: {report.total_edges_before}"
    )
    lines.append(
        f"  过滤后边数: {report.total_edges_after}"
    )
    lines.append(
        f"  总长度: {report.total_length_um:.6f} μm"
    )
    if report.total_edges_after > 0:
        lines.append(
            f"  最短边: {report.min_edge_length_um:.6f} μm"
        )
        lines.append(
            f"  最长边: {report.max_edge_length_um:.6f} μm"
        )
        lines.append(
            f"  平均边长: {report.avg_edge_length_um:.6f} μm"
        )
    lines.append("")
    lines.append("  方向分布:")
    lines.append(f"    水平 (H): {report.horizontal_count}")
    lines.append(f"    垂直 (V): {report.vertical_count}")
    lines.append(f"    对角 (D): {report.diagonal_count}")
    lines.append("")
    lines.append("  长度直方图:")
    for bin_name, count in report.length_histogram.items():
        lines.append(f"    {bin_name}: {count}")
    if report.sample_edges:
        lines.append("")
        lines.append(f"  样本边（前 {len(report.sample_edges)} 条）:")
        for i, e in enumerate(report.sample_edges[:10]):
            lines.append(
                f"    [{i}] ({e.x1_um:.4f},{e.y1_um:.4f}) → "
                f"({e.x2_um:.4f},{e.y2_um:.4f}) "
                f"len={e.length_um:.4f}μm {e.orientation}"
            )
        if len(report.sample_edges) > 10:
            lines.append(f"    ... 共 {len(report.sample_edges)} 条")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_markdown_report(report: "EdgeExtractionReport") -> str:
    """渲染 Markdown 报告（CommonMark 兼容）。

    Args:
        report: ``EdgeExtractionReport`` 实例。

    Returns:
        Markdown 字符串。
    """
    lines: list[str] = []
    lines.append("# GDSII 边缘提取报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    if report.output_path:
        lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append(f"- **layer**: ({report.layer[0]},{report.layer[1]})")
    if report.layer_result:
        lines.append(
            f"- **layer_result**: ({report.layer_result[0]},{report.layer_result[1]})"
        )
    lines.append("")
    lines.append("## 过滤参数")
    lines.append("")
    min_str = f"{report.min_length_um:.6f} μm" if report.min_length_um > 0 else "无"
    max_str = f"{report.max_length_um:.6f} μm" if report.max_length_um > 0 else "无"
    orient_str = report.orientation_filter or "无"
    lines.append(f"- **min_length**: {min_str}")
    lines.append(f"- **max_length**: {max_str}")
    lines.append(f"- **orientation**: {orient_str}")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 过滤前边数 | {report.total_edges_before} |")
    lines.append(f"| 过滤后边数 | {report.total_edges_after} |")
    lines.append(f"| 总长度 (μm) | {report.total_length_um:.6f} |")
    if report.total_edges_after > 0:
        lines.append(f"| 最短边 (μm) | {report.min_edge_length_um:.6f} |")
        lines.append(f"| 最长边 (μm) | {report.max_edge_length_um:.6f} |")
        lines.append(f"| 平均边长 (μm) | {report.avg_edge_length_um:.6f} |")
    lines.append(f"| 水平边 (H) | {report.horizontal_count} |")
    lines.append(f"| 垂直边 (V) | {report.vertical_count} |")
    lines.append(f"| 对角边 (D) | {report.diagonal_count} |")
    lines.append("")
    lines.append("## 长度直方图")
    lines.append("")
    lines.append("| 区间 | 边数 |")
    lines.append("|------|------|")
    for bin_name, count in report.length_histogram.items():
        lines.append(f"| {bin_name} | {count} |")
    if report.sample_edges:
        lines.append("")
        lines.append(f"## 样本边（前 {len(report.sample_edges)} 条）")
        lines.append("")
        lines.append("| # | x1 (μm) | y1 (μm) | x2 (μm) | y2 (μm) | 长度 (μm) | 方向 |")
        lines.append("|---|---------|---------|---------|---------|-----------|------|")
        for i, e in enumerate(report.sample_edges[:20]):
            lines.append(
                f"| {i} | {e.x1_um:.4f} | {e.y1_um:.4f} | "
                f"{e.x2_um:.4f} | {e.y2_um:.4f} | "
                f"{e.length_um:.4f} | {e.orientation} |"
            )
        if len(report.sample_edges) > 20:
            lines.append(f"\n*共 {len(report.sample_edges)} 条样本*")
    return "\n".join(lines)


def render_json_report(report: "EdgeExtractionReport") -> str:
    """渲染 JSON 报告（ECMA-404 兼容）。

    Args:
        report: ``EdgeExtractionReport`` 实例。

    Returns:
        缩进 JSON 字符串。
    """
    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "layer": list(report.layer),
        "layer_result": list(report.layer_result) if report.layer_result else [],
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "min_length_um": report.min_length_um,
        "max_length_um": report.max_length_um,
        "orientation_filter": report.orientation_filter,
        "total_edges_before": report.total_edges_before,
        "total_edges_after": report.total_edges_after,
        "total_length_um": report.total_length_um,
        "min_edge_length_um": report.min_edge_length_um,
        "max_edge_length_um": report.max_edge_length_um,
        "avg_edge_length_um": report.avg_edge_length_um,
        "horizontal_count": report.horizontal_count,
        "vertical_count": report.vertical_count,
        "diagonal_count": report.diagonal_count,
        "length_histogram": report.length_histogram,
        "sample_edges": [
            {
                "x1_um": e.x1_um,
                "y1_um": e.y1_um,
                "x2_um": e.x2_um,
                "y2_um": e.y2_um,
                "length_um": e.length_um,
                "orientation": e.orientation,
            }
            for e in report.sample_edges
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
