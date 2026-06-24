"""公开 Benchmark 评估报告生成器（P1-5 深化，第26轮）。

对标 TILOS MacroPlacement 评估流程，提供标准化评估报告生成，
输出 Markdown/JSON 格式报告，含 HPWL/重叠/利用率/达标判定/对比基准。

## TILOS MacroPlacement 评估流程对标

TILOS 评估流程（来源: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement）：
1. 加载 benchmark（Ariane/MemPool/NVDLA + NanGate45/ASAP7/SKY130HD）
2. 运行布局算法（DREAMPlace/RePlAce/Circuit Training/Custom）
3. 评估指标（HPWL/重叠/利用率/拥塞/DRV）
4. 生成评估报告（Markdown + JSON）
5. 对比基准（多算法横向对比 + 历史纵向对比）

本模块实现 PoLaRIS 版本的评估报告生成器，覆盖步骤 3-5，
支持 TILOS/Apollo/LiDAR 三大 benchmark 全覆盖评估。

## 报告格式

### Markdown 报告（对标 TILOS CodeBook 评估输出）
```markdown
# PoLaRIS Benchmark 评估报告

## 1. 摘要
- Benchmark: tilos_ariane
- 布局方法: grid
- HPWL: 12345.67 μm
- 重叠: 0
- 利用率: 0.45
- 达标: ✅

## 2. 详细指标
...
```

### JSON 报告（机器可读，用于 CI 回归）
```json
{
  "benchmark_name": "tilos_ariane",
  "placement_method": "grid",
  "hpwl_um": 12345.67,
  "overlap_count": 0,
  ...
}
```

来源:
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Circuit Training 评估: https://github.com/google-research/circuit_training
- ISPD 2025 评估标准: https://dl.acm.org/doi/10.1145/3698364.3705355
"""

from __future__ import annotations

import json
<<<<<<< HEAD
import time
=======
>>>>>>> trae/solo-agent-pkVjID
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from polaris.data.benchmark_evaluator import (
    BenchmarkResult,
    evaluate_benchmark,
    grid_placement,
)
from polaris.data.specs import CircuitSpec


@dataclass(frozen=True)
class BenchmarkReport:
    """单 benchmark 评估报告（对标 TILOS 评估输出）。

    Attributes:
        benchmark_name: benchmark 名称（如 ``tilos_ariane``）。
        benchmark_source: benchmark 来源（TILOS/APOLLO/LIDAR/CUSTOM）。
        placement_method: 布局方法名（``grid``/``rl_ppo``/``rl_gnn``/...）。
        hpwl_um: 半周长线长（μm）。
        overlap_count: 重叠对数。
        area_utilization: 面积利用率（0-1）。
        module_count: 模块数。
        connection_count: 连接数。
        target_metric: 目标指标名。
        target_value: 目标值。
        passed: 是否达标。
        process_node: 工艺节点。
        timestamp: 评估时间（ISO 8601）。
<<<<<<< HEAD
        runtime_s: 布局运行时间（秒，第81轮新增，对标 TILOS 评估运行时间统计）。
=======
>>>>>>> trae/solo-agent-pkVjID
        extra: 额外信息（如 curvy_challenge_count 等）。
    """

    benchmark_name: str
    benchmark_source: str
    placement_method: str
    hpwl_um: float
    overlap_count: int
    area_utilization: float
    module_count: int
    connection_count: int
    target_metric: str
    target_value: float
    passed: bool
    process_node: str
    timestamp: str = ""
<<<<<<< HEAD
    runtime_s: float = 0.0
=======
>>>>>>> trae/solo-agent-pkVjID
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ComparisonReport:
    """多 benchmark 对比报告（对标 TILOS 多算法横向对比）。

    Attributes:
        reports: 各 benchmark 的评估报告列表。
        total_benchmarks: benchmark 总数。
        passed_count: 达标数。
        pass_rate: 达标率（0-1）。
        avg_hpwl_um: 平均 HPWL（μm）。
        avg_utilization: 平均利用率。
        total_modules: 总模块数。
        total_connections: 总连接数。
<<<<<<< HEAD
        total_overlaps: 总重叠对数（第79轮新增）。
        total_runtime_s: 总运行时间（秒，第81轮新增）。
        avg_runtime_s: 平均运行时间（秒，第81轮新增）。
=======
>>>>>>> trae/solo-agent-pkVjID
        timestamp: 评估时间（ISO 8601）。
    """

    reports: list[BenchmarkReport] = field(default_factory=list)
    total_benchmarks: int = 0
    passed_count: int = 0
    pass_rate: float = 0.0
    avg_hpwl_um: float = 0.0
    avg_utilization: float = 0.0
    total_modules: int = 0
    total_connections: int = 0
<<<<<<< HEAD
    total_overlaps: int = 0
    total_runtime_s: float = 0.0
    avg_runtime_s: float = 0.0
=======
>>>>>>> trae/solo-agent-pkVjID
    timestamp: str = ""


def _now_iso() -> str:
    """返回当前 UTC 时间 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_report(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
    placement_method: str = "grid",
<<<<<<< HEAD
    runtime_s: float = 0.0,
=======
>>>>>>> trae/solo-agent-pkVjID
) -> BenchmarkReport:
    """生成单 benchmark 评估报告。

    对标 TILOS MacroPlacement 评估流程：计算 HPWL/重叠/利用率/达标判定，
    封装为 BenchmarkReport。

    Args:
        circuit: 电路规格（含 target_metric/target_value）。
        placements: 布局字典 {module_name: (cx, cy)}。
        placement_method: 布局方法名（默认 ``grid``）。
<<<<<<< HEAD
        runtime_s: 布局运行时间（秒，默认 0.0）。
=======
>>>>>>> trae/solo-agent-pkVjID

    Returns:
        BenchmarkReport，含全部指标与达标判定。

    来源:
        TILOS 评估流程: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
    """
    result: BenchmarkResult = evaluate_benchmark(circuit, placements)
    return BenchmarkReport(
        benchmark_name=result.benchmark_name,
        benchmark_source=result.extra.get("benchmark_source", "CUSTOM"),
        placement_method=placement_method,
        hpwl_um=result.hpwl_um,
        overlap_count=result.overlap_count,
        area_utilization=result.area_utilization,
        module_count=result.module_count,
        connection_count=result.connection_count,
        target_metric=result.target_metric,
        target_value=result.target_value,
        passed=result.passed,
        process_node=result.extra.get("process_node", ""),
        timestamp=_now_iso(),
<<<<<<< HEAD
        runtime_s=runtime_s,
=======
>>>>>>> trae/solo-agent-pkVjID
        extra=dict(result.extra),
    )


def generate_grid_report(circuit: CircuitSpec) -> BenchmarkReport:
    """生成网格基准布局评估报告（TILOS 基准对照）。

    使用 ``grid_placement`` 生成基准布局，评估并生成报告。
    用于与 RL 布局算法对比，量化 RL 相对基准的改进幅度。

    Args:
        circuit: 电路规格。

    Returns:
        BenchmarkReport，placement_method=``grid``。
    """
    placements = grid_placement(circuit)
    return generate_report(circuit, placements, placement_method="grid")


def generate_comparison_report(
    reports: list[BenchmarkReport],
) -> ComparisonReport:
    """生成多 benchmark 对比报告。

    对标 TILOS 多算法横向对比：汇总各 benchmark 的评估结果，
    计算达标率、平均 HPWL、平均利用率等统计指标。

    Args:
        reports: 各 benchmark 的评估报告列表。

    Returns:
        ComparisonReport，含统计汇总。
    """
    if not reports:
        return ComparisonReport(timestamp=_now_iso())
    passed = sum(1 for r in reports if r.passed)
    avg_hpwl = sum(r.hpwl_um for r in reports) / len(reports)
    avg_util = sum(r.area_utilization for r in reports) / len(reports)
    total_mod = sum(r.module_count for r in reports)
    total_conn = sum(r.connection_count for r in reports)
<<<<<<< HEAD
    total_ovlp = sum(r.overlap_count for r in reports)
    total_rt = sum(r.runtime_s for r in reports)
    avg_rt = total_rt / len(reports)
=======
>>>>>>> trae/solo-agent-pkVjID
    return ComparisonReport(
        reports=list(reports),
        total_benchmarks=len(reports),
        passed_count=passed,
        pass_rate=passed / len(reports),
        avg_hpwl_um=avg_hpwl,
        avg_utilization=avg_util,
        total_modules=total_mod,
        total_connections=total_conn,
<<<<<<< HEAD
        total_overlaps=total_ovlp,
        total_runtime_s=total_rt,
        avg_runtime_s=avg_rt,
=======
>>>>>>> trae/solo-agent-pkVjID
        timestamp=_now_iso(),
    )


def run_all_benchmarks(
    placement_method: str = "grid",
) -> ComparisonReport:
    """一键运行所有公开 benchmark 评估（TILOS/Apollo/LiDAR）。

    对标 TILOS MacroPlacement 全 benchmark 回归测试：
    加载全部公开 benchmark，使用指定布局方法评估，生成对比报告。

<<<<<<< HEAD
    第76轮 P1-5 扩展：支持 grid/analytical/hierarchical 三种布局方法，
    量化对比不同布局算法的 HPWL/重叠/利用率。

    第81轮 P1-5 扩展：添加 ``time.perf_counter()`` 计时，记录每个 benchmark
    的布局运行时间，用于对标 TILOS 评估运行时间统计与商业产品可扩展性对比。

    Args:
        placement_method: 布局方法名（``grid``/``analytical``/``hierarchical``，
            默认 ``grid``）。
=======
    Args:
        placement_method: 布局方法名（默认 ``grid``）。
>>>>>>> trae/solo-agent-pkVjID

    Returns:
        ComparisonReport，含全部 benchmark 评估结果。

    来源:
        TILOS 全 benchmark: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
        Apollo: https://github.com/ASU-LOPE-Group/Apollo
        LiDAR: https://github.com/ScopeX-ASU/LiDAR
<<<<<<< HEAD
        DREAMPlace: https://arxiv.org/abs/2004.10746
    """
    from polaris.data.benchmark_evaluator import placement_by_method
=======
    """
>>>>>>> trae/solo-agent-pkVjID
    from polaris.data.data_loader import (
        load_apollo_onoc,
        load_apollo_ptc,
        load_lidar_benchmark,
        load_tilos_ariane,
    )

    circuits = [
        load_tilos_ariane(),
        load_apollo_ptc(),
        load_apollo_onoc(),
        load_lidar_benchmark(),
    ]
    reports: list[BenchmarkReport] = []
    for circuit in circuits:
<<<<<<< HEAD
        t_start = time.perf_counter()
        placements = placement_by_method(circuit, placement_method)
        runtime_s = time.perf_counter() - t_start
        report = generate_report(
            circuit,
            placements,
            placement_method,
            runtime_s=runtime_s,
        )
=======
        placements = grid_placement(circuit)
        report = generate_report(circuit, placements, placement_method)
>>>>>>> trae/solo-agent-pkVjID
        reports.append(report)
    return generate_comparison_report(reports)


def _format_report_metrics(report: BenchmarkReport) -> list[str]:
    """格式化报告核心指标表格。

    Args:
        report: BenchmarkReport。

    Returns:
        Markdown 表格行列表。
    """
<<<<<<< HEAD
    max_cong = report.extra.get("max_congestion", 0.0)
    avg_cong = report.extra.get("avg_congestion", 0.0)
    ovf_count = report.extra.get("overflow_count", 0)
    total_ovf = report.extra.get("total_overflow", 0.0)
=======
>>>>>>> trae/solo-agent-pkVjID
    return [
        "## 2. 核心指标",
        "",
        "| 指标 | 数值 | 目标 |",
        "|------|------|------|",
        f"| HPWL (μm) | {report.hpwl_um:.2f} | {report.target_value:.2f} |",
        f"| 重叠对数 | {report.overlap_count} | 0 |",
        f"| 面积利用率 | {report.area_utilization:.4f} | — |",
<<<<<<< HEAD
        f"| 最大拥塞比 | {max_cong:.4f} | ≤1.0 |",
        f"| 平均拥塞比 | {avg_cong:.4f} | — |",
        f"| 拥塞溢出网格数 | {ovf_count} | 0 |",
        f"| 总溢出量 | {total_ovf:.4f} | 0 |",
        f"| 模块数 | {report.module_count} | — |",
        f"| 连接数 | {report.connection_count} | — |",
        f"| 运行时间 (s) | {report.runtime_s:.4f} | — |",
=======
        f"| 模块数 | {report.module_count} | — |",
        f"| 连接数 | {report.connection_count} | — |",
>>>>>>> trae/solo-agent-pkVjID
        f"| 目标指标 | {report.target_metric} | — |",
        "",
    ]


def format_report_markdown(report: BenchmarkReport) -> str:
    """格式化单 benchmark 报告为 Markdown（对标 TILOS CodeBook 输出）。

    Args:
        report: BenchmarkReport。

    Returns:
        Markdown 字符串。
    """
    passed_str = "✅ 达标" if report.passed else "❌ 未达标"
    lines = [
        f"# PoLaRIS Benchmark 评估报告: {report.benchmark_name}",
        "",
        "## 1. 摘要",
        "",
        f"- **Benchmark**: {report.benchmark_name}",
        f"- **来源**: {report.benchmark_source}",
        f"- **工艺节点**: {report.process_node}",
        f"- **布局方法**: {report.placement_method}",
        f"- **评估时间**: {report.timestamp}",
        f"- **达标判定**: {passed_str}",
        "",
    ]
    lines.extend(_format_report_metrics(report))
    if report.extra:
        lines.extend(["## 3. 额外信息", ""])
        for key, value in report.extra.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    lines.extend([
        "## 来源",
        "",
        "- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement",
        "- Circuit Training: https://github.com/google-research/circuit_training",
        "- Apollo: https://github.com/ASU-LOPE-Group/Apollo",
        "- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355",
        "",
    ])
    return "\n".join(lines)


def _format_comparison_rows(reports: list[BenchmarkReport]) -> list[str]:
    """格式化对比报告各 Benchmark 行。

    Args:
        reports: BenchmarkReport 列表。

    Returns:
        Markdown 表格行列表。
    """
    lines = []
    for r in reports:
        passed_str = "✅" if r.passed else "❌"
<<<<<<< HEAD
        max_cong = r.extra.get("max_congestion", 0.0)
        ovf_count = r.extra.get("overflow_count", 0)
        lines.append(
            f"| {r.benchmark_name} | {r.benchmark_source} | {r.process_node} | "
            f"{r.placement_method} | {r.hpwl_um:.2f} | {r.overlap_count} | "
            f"{r.area_utilization:.4f} | {max_cong:.4f} | {ovf_count} | "
            f"{r.module_count} | {r.connection_count} | "
            f"{r.runtime_s:.4f} | {passed_str} |"
=======
        lines.append(
            f"| {r.benchmark_name} | {r.benchmark_source} | {r.process_node} | "
            f"{r.placement_method} | {r.hpwl_um:.2f} | {r.overlap_count} | "
            f"{r.area_utilization:.4f} | {r.module_count} | {r.connection_count} | {passed_str} |"
>>>>>>> trae/solo-agent-pkVjID
        )
    return lines


def format_comparison_markdown(comp: ComparisonReport) -> str:
    """格式化对比报告为 Markdown（对标 TILOS 多算法横向对比）。

    Args:
        comp: ComparisonReport。

    Returns:
        Markdown 字符串。
    """
    lines = [
        "# PoLaRIS Benchmark 对比评估报告",
        "",
        "## 1. 摘要",
        "",
        f"- **Benchmark 总数**: {comp.total_benchmarks}",
        f"- **达标数**: {comp.passed_count}",
        f"- **达标率**: {comp.pass_rate:.2%}",
        f"- **平均 HPWL**: {comp.avg_hpwl_um:.2f} μm",
        f"- **平均利用率**: {comp.avg_utilization:.4f}",
        f"- **总模块数**: {comp.total_modules}",
        f"- **总连接数**: {comp.total_connections}",
<<<<<<< HEAD
        f"- **总重叠对数**: {comp.total_overlaps}",
        f"- **总运行时间**: {comp.total_runtime_s:.4f} s",
        f"- **平均运行时间**: {comp.avg_runtime_s:.4f} s",
=======
>>>>>>> trae/solo-agent-pkVjID
        f"- **评估时间**: {comp.timestamp}",
        "",
        "## 2. 各 Benchmark 详细结果",
        "",
<<<<<<< HEAD
        "| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 最大拥塞 | 溢出网格 | 模块 | 连接 | 运行时间 (s) | 达标 |",
        "|-----------|------|------|------|-----------|------|--------|----------|----------|------|------|--------------|------|",
=======
        "| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 模块 | 连接 | 达标 |",
        "|-----------|------|------|------|-----------|------|--------|------|------|------|",
>>>>>>> trae/solo-agent-pkVjID
    ]
    lines.extend(_format_comparison_rows(comp.reports))
    lines.extend([
        "",
        "## 3. 来源",
        "",
        "- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement",
        "- Apollo: https://github.com/ASU-LOPE-Group/Apollo",
        "- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355",
<<<<<<< HEAD
        "- Congestion: Nesterenko & Hsu TCAD 2002, BoxRouter ISPD 2006",
=======
>>>>>>> trae/solo-agent-pkVjID
        "",
    ])
    return "\n".join(lines)


def save_report_markdown(
    report: BenchmarkReport | ComparisonReport,
    path: str | Path,
) -> Path:
    """保存报告为 Markdown 文件。

    Args:
        report: BenchmarkReport 或 ComparisonReport。
        path: 输出文件路径。

    Returns:
        保存的文件路径（Path）。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(report, BenchmarkReport):
        content = format_report_markdown(report)
    else:
        content = format_comparison_markdown(report)
    p.write_text(content, encoding="utf-8")
    return p


def save_report_json(
    report: BenchmarkReport | ComparisonReport,
    path: str | Path,
) -> Path:
    """保存报告为 JSON 文件（机器可读，CI 回归用）。

    Args:
        report: BenchmarkReport 或 ComparisonReport。
        path: 输出文件路径。

    Returns:
        保存的文件路径（Path）。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(report)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


__all__ = [
    "BenchmarkReport",
    "ComparisonReport",
    "generate_report",
    "generate_grid_report",
    "generate_comparison_report",
    "run_all_benchmarks",
    "format_report_markdown",
    "format_comparison_markdown",
    "save_report_markdown",
    "save_report_json",
]
