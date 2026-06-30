"""GDSII DRC 批量检查工具（R345，Batch DRC Checker）。

集成 R343（width/space 同层检查）和 R344（enclosing/enclosed/overlap/
separation 层间检查），支持一次运行多个 DRC 规则，生成汇总报告。

## 核心概念

- **DRC 规则（DRCRule）**: 一条 DRC 检查规则
  - name: 规则名（用户自定义）
  - check_type: 检查类型（width/space/enclosing/enclosed/overlap/separation）
  - layer_a / layer_b: 检查层（同层检查 layer_b 为空）
  - min_value_um: 最小阈值
- **批量检查**: 一次运行多个规则，收集所有违规
- **汇总报告**: 每条规则的通过/失败状态 + 总违规数

## 检查类型分类

- **同层检查**（layer_b 为空元组）:
  - width: 同层内最小宽度
  - space: 同层内最小间距
- **层间检查**（layer_b 不为空）:
  - enclosing: layer_a 包围 layer_b
  - enclosed: layer_a 被 layer_b 包围
  - overlap: layer_a 与 layer_b 重叠
  - separation: layer_a 与 layer_b 间距

## 算法

1. 读取 GDSII 一次（避免重复 I/O）
2. 对每条规则:
   - 同层检查: 调用 R343 的 check_width / check_space
   - 层间检查: 调用 R344 的 check_enclosing / check_enclosed / check_overlap / check_separation
3. 收集所有规则的检查结果
4. 生成汇总报告

## 学术依据

- KLayout Region class:
  https://www.klayout.de/doc-qt5/code/class_Region.html
- KLayout DRC Reference:
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- Calibre DRC Batch:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC DRC Rules:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- KLayout EdgePairs:
  https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
- KLayout EdgePair:
  https://www.klayout.org/doc-qt5/code/class_EdgePair.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polaris.verification.gdsii_drc_width_space import (
    DRCReport,
    check_width,
    check_space,
)
from polaris.verification.gdsii_drc_interlayer import (
    InterLayerDRCReport,
    check_enclosing,
    check_enclosed,
    check_overlap,
    check_separation,
)

logger = logging.getLogger(__name__)

__all__ = [
    "DRCRule",
    "DRCRuleResult",
    "BatchDRCReport",
    "run_batch_drc",
    "generate_batch_drc_report",
]

# 同层检查类型
SINGLE_LAYER_CHECKS = ("width", "space")
# 层间检查类型
INTER_LAYER_CHECKS = ("enclosing", "enclosed", "overlap", "separation")
# 所有有效检查类型
VALID_CHECK_TYPES = SINGLE_LAYER_CHECKS + INTER_LAYER_CHECKS


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class DRCRule:
    """单个 DRC 规则（R345）。

    Attributes:
        name: 规则名（用户自定义，用于标识）。
        check_type: 检查类型 'width'/'space'/'enclosing'/'enclosed'/'overlap'/'separation'。
        layer_a: 第一层 (layer, datatype)。
        layer_b: 第二层 (layer, datatype)，同层检查为空元组 ()。
        min_value_um: 最小阈值（μm）。
    """

    name: str
    check_type: str
    layer_a: tuple[int, int]
    layer_b: tuple[int, int] = ()
    min_value_um: float = 0.0


@dataclass
class DRCRuleResult:
    """单个规则的检查结果（R345）。

    Attributes:
        rule: 原始规则。
        passed: 是否通过（违规数 == 0）。
        total_violations: 违规数。
        check_type: 检查类型。
        layer_a: 第一层。
        layer_b: 第二层。
        min_value_um: 最小阈值。
        error: 错误信息（如规则执行失败），None 表示无错误。
    """

    rule: DRCRule
    passed: bool
    total_violations: int
    check_type: str
    layer_a: tuple[int, int]
    layer_b: tuple[int, int]
    min_value_um: float
    error: str | None = None


@dataclass
class BatchDRCReport:
    """批量 DRC 检查报告（R345）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        total_rules: 总规则数。
        passed_rules: 通过规则数。
        failed_rules: 失败规则数（有违规）。
        error_rules: 错误规则数（执行失败）。
        total_violations: 所有规则违规总数。
        results: 每条规则的结果列表。
    """

    input_path: str = ""
    dbu: float = 0.0
    top_cell_name: str = ""
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    error_rules: int = 0
    total_violations: int = 0
    results: list[DRCRuleResult] = field(default_factory=list)


# =============================================================================
# 批量检查主入口
# =============================================================================
def run_batch_drc(
    gds_path: str | Path,
    rules: list[DRCRule],
    top_cell_name: str | None = None,
    max_violations: int = 1000,
) -> BatchDRCReport:
    """批量运行 DRC 规则（R345）。

    对每条规则调用对应的 R343/R344 检查函数，收集所有结果。

    Args:
        gds_path: 输入 GDSII 文件路径。
        rules: DRC 规则列表。
        top_cell_name: 指定顶层 cell 名（None 用第一个 top cell）。
        max_violations: 每条规则保留的最大违规数。

    Returns:
        BatchDRCReport 批量检查报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: rules 为空 / 规则无效。
        ImportError: klayout 未安装。

    来源:
    - KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt5/about/drc_ref_layer.html
    """
    in_path = Path(gds_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {gds_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {gds_path}")
    if not rules:
        raise ValueError(
            "rules 不能为空。禁止 fall-back（R03）。"
        )

    # 验证所有规则
    for i, rule in enumerate(rules):
        _validate_rule(rule, i)

    results: list[DRCRuleResult] = []
    total_violations = 0
    passed_rules = 0
    failed_rules = 0
    error_rules = 0
    dbu = 0.0
    top_cell_name_resolved = ""

    for rule in rules:
        try:
            if rule.check_type in SINGLE_LAYER_CHECKS:
                # 同层检查
                if rule.check_type == "width":
                    report = check_width(
                        gds_path, rule.layer_a, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                else:  # space
                    report = check_space(
                        gds_path, rule.layer_a, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                violations = report.total_violations
                layer_b_resolved: tuple[int, int] = ()
            else:
                # 层间检查
                if not rule.layer_b:
                    raise ValueError(
                        f"规则 '{rule.name}' ({rule.check_type}) 需要层间检查，"
                        f"但 layer_b 为空。"
                        f"禁止 fall-back（R03）。"
                    )
                if rule.check_type == "enclosing":
                    report = check_enclosing(
                        gds_path, rule.layer_a, rule.layer_b, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                elif rule.check_type == "enclosed":
                    report = check_enclosed(
                        gds_path, rule.layer_a, rule.layer_b, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                elif rule.check_type == "overlap":
                    report = check_overlap(
                        gds_path, rule.layer_a, rule.layer_b, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                else:  # separation
                    report = check_separation(
                        gds_path, rule.layer_a, rule.layer_b, rule.min_value_um,
                        top_cell_name, max_violations,
                    )
                violations = report.total_violations
                layer_b_resolved = rule.layer_b

            # 记录 dbu 和 top_cell_name（从第一个成功的报告获取）
            if dbu == 0.0:
                dbu = report.dbu
                top_cell_name_resolved = report.top_cell_name

            passed = (violations == 0)
            if passed:
                passed_rules += 1
            else:
                failed_rules += 1

            total_violations += violations

            results.append(DRCRuleResult(
                rule=rule,
                passed=passed,
                total_violations=violations,
                check_type=rule.check_type,
                layer_a=rule.layer_a,
                layer_b=layer_b_resolved,
                min_value_um=rule.min_value_um,
                error=None,
            ))
        except Exception as e:
            error_rules += 1
            results.append(DRCRuleResult(
                rule=rule,
                passed=False,
                total_violations=0,
                check_type=rule.check_type,
                layer_a=rule.layer_a,
                layer_b=rule.layer_b,
                min_value_um=rule.min_value_um,
                error=f"{type(e).__name__}: {e}",
            ))
            logger.warning(
                "规则 '%s' 执行失败: %s: %s",
                rule.name, type(e).__name__, e,
            )

    logger.info(
        "批量 DRC 检查: %s, rules=%d, passed=%d, failed=%d, errors=%d, "
        "total_violations=%d",
        in_path, len(rules), passed_rules, failed_rules, error_rules,
        total_violations,
    )

    return BatchDRCReport(
        input_path=str(gds_path),
        dbu=dbu,
        top_cell_name=top_cell_name_resolved,
        total_rules=len(rules),
        passed_rules=passed_rules,
        failed_rules=failed_rules,
        error_rules=error_rules,
        total_violations=total_violations,
        results=results,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_batch_drc_report(
    gds_path: str | Path,
    rules: list[DRCRule],
    top_cell_name: str | None = None,
    max_violations: int = 1000,
    output_format: str = "text",
) -> str:
    """批量运行 DRC 规则并生成报告字符串（R345）。

    Args:
        gds_path: 输入 GDSII 文件路径。
        rules: DRC 规则列表。
        top_cell_name: 指定顶层 cell 名。
        max_violations: 每条规则保留的最大违规数。
        output_format: 'text'/'markdown'/'json'。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。
    """
    report = run_batch_drc(
        gds_path, rules, top_cell_name, max_violations,
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
def _validate_rule(rule: DRCRule, index: int) -> None:
    """验证 DRC 规则（R345 内部函数）。

    Args:
        rule: 要验证的规则。
        index: 规则索引（用于错误消息）。

    Raises:
        ValueError: 规则无效。
    """
    if not isinstance(rule, DRCRule):
        raise ValueError(
            f"rules[{index}] 不是 DRCRule 实例: {type(rule).__name__}。"
            f"禁止 fall-back（R03）。"
        )
    if not rule.name or not isinstance(rule.name, str):
        raise ValueError(
            f"rules[{index}].name 必须是非空字符串。"
            f"禁止 fall-back（R03）。"
        )
    ct = rule.check_type.lower()
    if ct not in VALID_CHECK_TYPES:
        raise ValueError(
            f"rules[{index}] '{rule.name}' check_type 无效: {rule.check_type}。"
            f"支持: {VALID_CHECK_TYPES}。"
            f"禁止 fall-back（R03）。"
        )
    # 规范化 check_type
    rule.check_type = ct

    if not isinstance(rule.layer_a, (tuple, list)) or len(rule.layer_a) != 2:
        raise ValueError(
            f"rules[{index}] '{rule.name}' layer_a 必须是 (layer, datatype)。"
            f"禁止 fall-back（R03）。"
        )
    la_g, la_d = int(rule.layer_a[0]), int(rule.layer_a[1])
    if not (0 <= la_g <= 999):
        raise ValueError(
            f"rules[{index}] '{rule.name}' layer_a.layer 必须 0-999。"
            f"禁止 fall-back（R03）。"
        )
    if not (0 <= la_d <= 255):
        raise ValueError(
            f"rules[{index}] '{rule.name}' layer_a.datatype 必须 0-255。"
            f"禁止 fall-back（R03）。"
        )
    rule.layer_a = (la_g, la_d)

    # layer_b 验证（同层检查允许空元组）
    if rule.layer_b:
        if not isinstance(rule.layer_b, (tuple, list)) or len(rule.layer_b) != 2:
            raise ValueError(
                f"rules[{index}] '{rule.name}' layer_b 必须是 (layer, datatype)。"
                f"禁止 fall-back（R03）。"
            )
        lb_g, lb_d = int(rule.layer_b[0]), int(rule.layer_b[1])
        if not (0 <= lb_g <= 999):
            raise ValueError(
                f"rules[{index}] '{rule.name}' layer_b.layer 必须 0-999。"
                f"禁止 fall-back（R03）。"
            )
        if not (0 <= lb_d <= 255):
            raise ValueError(
                f"rules[{index}] '{rule.name}' layer_b.datatype 必须 0-255。"
                f"禁止 fall-back（R03）。"
            )
        rule.layer_b = (lb_g, lb_d)

    # 同层检查不允许 layer_b
    if ct in SINGLE_LAYER_CHECKS and rule.layer_b:
        raise ValueError(
            f"rules[{index}] '{rule.name}' {ct} 是同层检查，"
            f"layer_b 必须为空。"
            f"禁止 fall-back（R03）。"
        )

    # 层间检查必须 layer_b
    if ct in INTER_LAYER_CHECKS and not rule.layer_b:
        raise ValueError(
            f"rules[{index}] '{rule.name}' {ct} 是层间检查，"
            f"layer_b 不能为空。"
            f"禁止 fall-back（R03）。"
        )

    # 层间检查 layer_a != layer_b
    if ct in INTER_LAYER_CHECKS and rule.layer_a == rule.layer_b:
        raise ValueError(
            f"rules[{index}] '{rule.name}' {ct} layer_a 和 layer_b 不能相同。"
            f"禁止 fall-back（R03）。"
        )

    if rule.min_value_um <= 0:
        raise ValueError(
            f"rules[{index}] '{rule.name}' min_value_um 必须 > 0。"
            f"禁止 fall-back（R03）。"
        )


def _render_text_report(report: BatchDRCReport) -> str:
    """渲染纯文本报告（R345 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII 批量 DRC 检查报告")
    lines.append("=" * 70)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("汇总")
    lines.append("-" * 70)
    lines.append(f"  总规则数: {report.total_rules}")
    lines.append(f"  通过规则: {report.passed_rules}")
    lines.append(f"  失败规则: {report.failed_rules}（有违规）")
    lines.append(f"  错误规则: {report.error_rules}（执行失败）")
    lines.append(f"  总违规数: {report.total_violations}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("规则详情")
    lines.append("-" * 70)
    for i, r in enumerate(report.results):
        status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
        layer_b_str = (
            f" → ({r.layer_b[0]},{r.layer_b[1]})"
            if r.layer_b else ""
        )
        lines.append(
            f"  [{i}] {status} {r.rule.name} ({r.check_type}) "
            f"({r.layer_a[0]},{r.layer_a[1]}){layer_b_str} "
            f"min={r.min_value_um:.4f}μm → violations={r.total_violations}"
        )
        if r.error:
            lines.append(f"        error: {r.error}")
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: BatchDRCReport) -> str:
    """渲染 Markdown 报告（R345 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 批量 DRC 检查报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_name}")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 总规则数 | {report.total_rules} |")
    lines.append(f"| 通过规则 | {report.passed_rules} |")
    lines.append(f"| 失败规则 | {report.failed_rules} |")
    lines.append(f"| 错误规则 | {report.error_rules} |")
    lines.append(f"| 总违规数 | {report.total_violations} |")
    lines.append("")
    lines.append("## 规则详情")
    lines.append("")
    lines.append("| # | 状态 | 规则名 | 类型 | layer_a | layer_b | 阈值 (μm) | 违规数 |")
    lines.append("|---|------|--------|------|---------|---------|-----------|--------|")
    for i, r in enumerate(report.results):
        status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
        layer_b_str = f"({r.layer_b[0]},{r.layer_b[1]})" if r.layer_b else "-"
        lines.append(
            f"| {i} | {status} | {r.rule.name} | {r.check_type} | "
            f"({r.layer_a[0]},{r.layer_a[1]}) | {layer_b_str} | "
            f"{r.min_value_um:.4f} | {r.total_violations} |"
        )
    return "\n".join(lines)


def _render_json_report(report: BatchDRCReport) -> str:
    """渲染 JSON 报告（R345 内部函数）。"""
    import json

    data = {
        "input_path": report.input_path,
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "total_rules": report.total_rules,
        "passed_rules": report.passed_rules,
        "failed_rules": report.failed_rules,
        "error_rules": report.error_rules,
        "total_violations": report.total_violations,
        "results": [
            {
                "name": r.rule.name,
                "check_type": r.check_type,
                "layer_a": list(r.layer_a),
                "layer_b": list(r.layer_b) if r.layer_b else [],
                "min_value_um": r.min_value_um,
                "passed": r.passed,
                "total_violations": r.total_violations,
                "error": r.error,
            }
            for r in report.results
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
