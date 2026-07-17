"""GDSII 层密度分析报告渲染器（R320，从 gdsii_density_analyzer 拆分）。

本模块负责将 ``DensityReport`` 渲染为纯文本或 Markdown 字符串，
从 ``gdsii_density_analyzer.py`` 拆分以满足 R11 质量门禁（单文件 ≤800 行）。

## 渲染格式

- **text**: 等宽对齐的纯文本报告（适合终端输出与日志）
- **markdown**: CommonMark 兼容的 Markdown 表格报告（适合文档与 PR 评论）

## 学术依据

- CommonMark 规范: https://spec.commonmark.org/
- GitHub Flavored Markdown: https://github.github.com/gfm/
- KLayout Database API（密度分析数据源 ``DensityReport`` 的上游）:
  https://www.klayout.de/doc.html
- gdsfactory GDSII 生态（层密度/dummy fill 设计流程参考）:
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK（晶圆厂密度规则参考）:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polaris_gds_tools.gdsii_density_analyzer import DensityReport


def render_text_report(report: "DensityReport") -> str:
    """渲染纯文本报告。

    Args:
        report: ``DensityReport`` 实例。

    Returns:
        多行纯文本字符串。
    """
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


def render_markdown_report(report: "DensityReport") -> str:
    """渲染 Markdown 报告（CommonMark 兼容）。

    Args:
        report: ``DensityReport`` 实例。

    Returns:
        Markdown 字符串。
    """
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
