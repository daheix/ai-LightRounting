#!/usr/bin/env python3
"""批量测试报告生成器。

读取 out/batch_test/results.json，生成总体/分拓扑/分规模/分平台统计 + 失败分析。

用法:
    python scripts/generate_test_report.py
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = PROJECT_ROOT / "out" / "batch_test" / "results.json"
REPORT_FILE = PROJECT_ROOT / "out" / "batch_test" / "report.md"
STATS_FILE = PROJECT_ROOT / "out" / "batch_test" / "stats.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("report_gen")


def percentile(data: list[float], p: float) -> float:
    """计算百分位数。"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def main() -> int:
    """主入口。"""
    if not RESULTS_FILE.exists():
        logger.error("结果文件不存在: %s", RESULTS_FILE)
        return 1

    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    results = data.get("results", [])
    n_total = len(results)
    if n_total == 0:
        logger.error("无测试结果")
        return 1

    logger.info("加载 %d 个测试结果", n_total)

    # 总体统计
    n_success = sum(1 for r in results if r["success"])
    n_drc = sum(1 for r in results if r["drc_passed"])
    losses = [r["total_loss_db"] for r in results if r["success"] and r["total_loss_db"] > 0]
    times = [r["elapsed_sec"] for r in results if r["success"]]
    crossings = [r["n_crossings"] for r in results if r["success"]]

    overall = {
        "total": n_total,
        "success": n_success,
        "success_rate": n_success / n_total,
        "drc_passed": n_drc,
        "drc_rate": n_drc / n_total,
        "avg_loss_db": statistics.mean(losses) if losses else 0,
        "p50_loss_db": percentile(losses, 50),
        "p95_loss_db": percentile(losses, 95),
        "avg_elapsed_sec": statistics.mean(times) if times else 0,
        "p50_elapsed_sec": percentile(times, 50),
        "p95_elapsed_sec": percentile(times, 95),
        "avg_crossings": statistics.mean(crossings) if crossings else 0,
    }

    # 分拓扑统计
    by_topology: dict[str, list] = defaultdict(list)
    for r in results:
        by_topology[r["topology"]].append(r)

    topo_stats = {}
    for topo, items in sorted(by_topology.items()):
        t_success = sum(1 for r in items if r["success"])
        t_drc = sum(1 for r in items if r["drc_passed"])
        t_losses = [r["total_loss_db"] for r in items if r["success"] and r["total_loss_db"] > 0]
        t_times = [r["elapsed_sec"] for r in items if r["success"]]
        topo_stats[topo] = {
            "total": len(items),
            "success": t_success,
            "success_rate": t_success / len(items),
            "drc_passed": t_drc,
            "drc_rate": t_drc / len(items),
            "avg_loss_db": statistics.mean(t_losses) if t_losses else 0,
            "avg_elapsed_sec": statistics.mean(t_times) if t_times else 0,
        }

    # 分规模统计
    by_scale: dict[str, list] = defaultdict(list)
    for r in results:
        by_scale[r["scale"]].append(r)

    scale_stats = {}
    for scale in ["XS", "S", "M", "L", "XL"]:
        items = by_scale.get(scale, [])
        if not items:
            continue
        s_success = sum(1 for r in items if r["success"])
        s_drc = sum(1 for r in items if r["drc_passed"])
        s_losses = [r["total_loss_db"] for r in items if r["success"] and r["total_loss_db"] > 0]
        s_times = [r["elapsed_sec"] for r in items if r["success"]]
        scale_stats[scale] = {
            "total": len(items),
            "success": s_success,
            "success_rate": s_success / len(items),
            "drc_passed": s_drc,
            "drc_rate": s_drc / len(items),
            "avg_loss_db": statistics.mean(s_losses) if s_losses else 0,
            "avg_elapsed_sec": statistics.mean(s_times) if s_times else 0,
        }

    # 分平台统计
    by_platform: dict[str, list] = defaultdict(list)
    for r in results:
        by_platform[r["platform"]].append(r)

    platform_stats = {}
    for plat, items in sorted(by_platform.items()):
        p_success = sum(1 for r in items if r["success"])
        p_drc = sum(1 for r in items if r["drc_passed"])
        p_losses = [r["total_loss_db"] for r in items if r["success"] and r["total_loss_db"] > 0]
        p_times = [r["elapsed_sec"] for r in items if r["success"]]
        platform_stats[plat] = {
            "total": len(items),
            "success": p_success,
            "success_rate": p_success / len(items),
            "drc_passed": p_drc,
            "drc_rate": p_drc / len(items),
            "avg_loss_db": statistics.mean(p_losses) if p_losses else 0,
            "avg_elapsed_sec": statistics.mean(p_times) if p_times else 0,
        }

    # 失败分析
    failures = [r for r in results if not r["success"]]
    failure_categories = defaultdict(list)
    for f in failures:
        err = f.get("error", "")
        if "不在损耗表中" in err:
            cat = "器件类型未注册"
        elif "布线" in err or "route" in err.lower() or "unrouted" in err.lower():
            cat = "布线失败"
        elif "DRC" in err or "drc" in err.lower():
            cat = "DRC失败"
        elif "仿真" in err or "sim" in err.lower():
            cat = "仿真失败"
        elif "GDS" in err or "gds" in err.lower():
            cat = "GDS导出失败"
        elif "布局" in err or "placement" in err.lower():
            cat = "布局失败"
        else:
            cat = "其他"
        failure_categories[cat].append(f["name"])

    # 保存 stats.json
    stats = {
        "overall": overall,
        "by_topology": topo_stats,
        "by_scale": scale_stats,
        "by_platform": platform_stats,
        "failures": {
            "total": len(failures),
            "categories": {k: len(v) for k, v in failure_categories.items()},
        },
    }
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("统计: %s", STATS_FILE)

    # 生成 Markdown 报告
    lines = [
        "# PoLaRIS 1000 电路批量测试报告",
        "",
        f"> 测试时间: {data.get('updated', 'N/A')}",
        f"> 电路总数: {n_total}",
        "",
        "## 1. 总体统计",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 电路总数 | {n_total} |",
        f"| 成功数 | {n_success} ({overall['success_rate']:.1%}) |",
        f"| DRC 通过数 | {n_drc} ({overall['drc_rate']:.1%}) |",
        f"| 平均损耗 | {overall['avg_loss_db']:.2f} dB |",
        f"| P50 损耗 | {overall['p50_loss_db']:.2f} dB |",
        f"| P95 损耗 | {overall['p95_loss_db']:.2f} dB |",
        f"| 平均耗时 | {overall['avg_elapsed_sec']:.2f} s |",
        f"| P50 耗时 | {overall['p50_elapsed_sec']:.2f} s |",
        f"| P95 耗时 | {overall['p95_elapsed_sec']:.2f} s |",
        f"| 平均交叉数 | {overall['avg_crossings']:.1f} |",
        "",
        "## 2. 分拓扑统计",
        "",
        "| 拓扑 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 | 平均损耗 | 平均耗时 |",
        "|------|------|------|--------|---------|-------|----------|----------|",
    ]
    for topo, s in sorted(topo_stats.items()):
        lines.append(
            f"| {topo} | {s['total']} | {s['success']} | {s['success_rate']:.1%} | "
            f"{s['drc_passed']} | {s['drc_rate']:.1%} | {s['avg_loss_db']:.2f} | "
            f"{s['avg_elapsed_sec']:.2f} |"
        )

    lines += [
        "",
        "## 3. 分规模统计",
        "",
        "| 规模 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 | 平均损耗 | 平均耗时 |",
        "|------|------|------|--------|---------|-------|----------|----------|",
    ]
    for scale in ["XS", "S", "M", "L", "XL"]:
        s = scale_stats.get(scale)
        if s:
            lines.append(
                f"| {scale} | {s['total']} | {s['success']} | {s['success_rate']:.1%} | "
                f"{s['drc_passed']} | {s['drc_rate']:.1%} | {s['avg_loss_db']:.2f} | "
                f"{s['avg_elapsed_sec']:.2f} |"
            )

    lines += [
        "",
        "## 4. 分平台统计",
        "",
        "| 平台 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 | 平均损耗 | 平均耗时 |",
        "|------|------|------|--------|---------|-------|----------|----------|",
    ]
    for plat, s in sorted(platform_stats.items()):
        lines.append(
            f"| {plat} | {s['total']} | {s['success']} | {s['success_rate']:.1%} | "
            f"{s['drc_passed']} | {s['drc_rate']:.1%} | {s['avg_loss_db']:.2f} | "
            f"{s['avg_elapsed_sec']:.2f} |"
        )

    lines += [
        "",
        "## 5. 失败分析",
        "",
        f"失败总数: {len(failures)}",
        "",
    ]
    if failure_categories:
        lines.append("| 失败类型 | 数量 | 示例电路 |")
        lines.append("|----------|------|----------|")
        for cat, names in sorted(failure_categories.items(), key=lambda x: -len(x[1])):
            examples = ", ".join(names[:3])
            lines.append(f"| {cat} | {len(names)} | {examples} |")
    else:
        lines.append("无失败电路 ✓")

    # 目标达成
    lines += [
        "",
        "## 6. 目标达成",
        "",
        "| 目标 | 实际 | 状态 |",
        "|------|------|------|",
        f"| 成功率 ≥ 95% | {overall['success_rate']:.1%} | "
        f"{'✓' if overall['success_rate'] >= 0.95 else '✗'} |",
        f"| DRC 通过率 ≥ 90% | {overall['drc_rate']:.1%} | "
        f"{'✓' if overall['drc_rate'] >= 0.90 else '✗'} |",
        f"| 电路总数 ≥ 1000 | {n_total} | "
        f"{'✓' if n_total >= 1000 else '✗'} |",
        "",
    ]

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    logger.info("报告: %s", REPORT_FILE)

    # 打印摘要
    print(f"\n{'='*60}")
    print(f"总体: {n_total} 电路, 成功 {n_success} ({overall['success_rate']:.1%}), "
          f"DRC {n_drc} ({overall['drc_rate']:.1%})")
    print(f"平均损耗: {overall['avg_loss_db']:.2f} dB, "
          f"平均耗时: {overall['avg_elapsed_sec']:.2f} s")
    print(f"报告: {REPORT_FILE}")
    print(f"统计: {STATS_FILE}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
