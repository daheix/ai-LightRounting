"""Benchmark 历史趋势追踪（P1-5 深化，第29轮）。

对标 TILOS CodeBook 历史趋势追踪能力，提供多次评估记录持久化、
趋势分析、改进幅度计算、回归检测，支持 CI 长期质量追踪。

## TILOS CodeBook 历史趋势追踪对标

TILOS CodeBook（来源: https://github.com/TILOS-AI-CAD-Institute/CodeBook）
提供以下能力：
1. 多次评估记录持久化（每次运行记录 HPWL/利用率/达标状态）
2. 历史趋势分析（HPWL 改进幅度、达标率变化）
3. 回归检测（指标恶化时告警）
4. Markdown 趋势报告（可视化历史变化）

本模块实现 PoLaRIS 版本的历史趋势追踪，覆盖上述全部能力。

## 核心数据结构

### HistoryEntry（单次评估记录）
- run_id: 运行 ID（UUID 或时间戳）
- timestamp: 评估时间（ISO 8601）
- report: BenchmarkReport（含 HPWL/重叠/利用率/达标）
- commit_hash: Git commit hash（可选，用于追溯代码版本）
- notes: 备注（如 "v2.0.0 RL warm-start"）

### BenchmarkHistory（单 benchmark 历史记录）
- benchmark_name: benchmark 名称
- entries: 历史记录列表（按时间排序）

### TrendAnalysis（趋势分析结果）
- benchmark_name: benchmark 名称
- entry_count: 历史记录数
- first_hpwl_um: 首次 HPWL
- last_hpwl_um: 最近 HPWL
- best_hpwl_um: 历史最佳 HPWL
- worst_hpwl_um: 历史最差 HPWL
- improvement_vs_first: 相对首次改进幅度（%）
- improvement_vs_last: 相对上次改进幅度（%）
- trend_direction: 趋势方向（improving/regarding/stable）
- pass_rate_history: 达标率历史
- regression_detected: 是否检测到回归

来源:
- TILOS CodeBook: https://github.com/TILOS-AI-CAD-Institute/CodeBook
- Circuit Training 评估历史: https://github.com/google-research/circuit_training
- MLflow 实验追踪: https://mlflow.org/docs/latest/tracking.html
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from polaris.data.benchmark_report import BenchmarkReport


def _now_iso() -> str:
    """返回当前 UTC 时间 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class RecordMeta:
    """评估记录元数据（降低 add_record 参数个数，规则 4.1）。

    封装 run_id 和 timestamp 两个可选元数据字段。

    Attributes:
        run_id: 运行 ID（None 自动生成 UUID）。
        timestamp: 评估时间（None 用当前 UTC）。
    """

    run_id: str | None = None
    timestamp: str | None = None


@dataclass(frozen=True)
class HistoryEntry:
    """单次评估历史记录。

    Attributes:
        run_id: 运行 ID（UUID）。
        timestamp: 评估时间（ISO 8601）。
        report: BenchmarkReport。
        commit_hash: Git commit hash（可选）。
        notes: 备注（如版本号、算法变更说明）。
    """

    run_id: str
    timestamp: str
    report: BenchmarkReport
    commit_hash: str = ""
    notes: str = ""


@dataclass
class BenchmarkHistory:
    """单 benchmark 历史记录（多次评估）。

    Attributes:
        benchmark_name: benchmark 名称。
        entries: 历史记录列表（按时间排序，最早在前）。
    """

    benchmark_name: str
    entries: list[HistoryEntry] = field(default_factory=list)

    def add_entry(self, entry: HistoryEntry) -> None:
        """添加历史记录（按 timestamp 排序）。"""
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.timestamp)

    def latest(self) -> HistoryEntry | None:
        """返回最近一次评估记录。"""
        return self.entries[-1] if self.entries else None

    def first(self) -> HistoryEntry | None:
        """返回首次评估记录。"""
        return self.entries[0] if self.entries else None


@dataclass(frozen=True)
class TrendAnalysis:
    """趋势分析结果。

    Attributes:
        benchmark_name: benchmark 名称。
        entry_count: 历史记录数。
        first_hpwl_um: 首次 HPWL（μm）。
        last_hpwl_um: 最近 HPWL（μm）。
        best_hpwl_um: 历史最佳（最小）HPWL。
        worst_hpwl_um: 历史最差（最大）HPWL。
        improvement_vs_first: 相对首次改进幅度（%，正数=改进）。
        improvement_vs_last: 相对上次改进幅度（%，正数=改进）。
        trend_direction: 趋势方向（``improving``/``regarding``/``stable``）。
        pass_rate: 历史达标率（0-1）。
        regression_detected: 是否检测到回归（最近一次相对最佳恶化 > 阈值）。
    """

    benchmark_name: str
    entry_count: int
    first_hpwl_um: float
    last_hpwl_um: float
    best_hpwl_um: float
    worst_hpwl_um: float
    improvement_vs_first: float
    improvement_vs_last: float
    trend_direction: str
    pass_rate: float
    regression_detected: bool


class HistoryTracker:
    """历史趋势追踪器。

    管理多 benchmark 的历史评估记录，提供趋势分析与持久化。

    对标 TILOS CodeBook 实验追踪能力：
    - add_record(): 记录单次评估
    - get_history(): 查询 benchmark 历史
    - analyze_trend(): 分析趋势
    - save()/load(): JSON 持久化
    - generate_trend_report(): Markdown 趋势报告

    Args:
        regression_threshold: 回归检测阈值（默认 5%，即最近 HPWL 相对最佳恶化 > 5% 触发）。
    """

    def __init__(self, regression_threshold: float = 5.0) -> None:
        self._histories: dict[str, BenchmarkHistory] = {}
        self.regression_threshold = regression_threshold

    def add_record(
        self,
        report: BenchmarkReport,
        commit_hash: str = "",
        notes: str = "",
        meta: RecordMeta | None = None,
    ) -> HistoryEntry:
        """记录单次评估。

        Args:
            report: BenchmarkReport。
            commit_hash: Git commit hash（可选）。
            notes: 备注（如版本号）。
            meta: 元数据（run_id / timestamp，None 自动生成）。

        Returns:
            创建的 HistoryEntry。
        """
        m = meta or RecordMeta()
        entry = HistoryEntry(
            run_id=m.run_id or str(uuid.uuid4()),
            timestamp=m.timestamp or _now_iso(),
            report=report,
            commit_hash=commit_hash,
            notes=notes,
        )
        name = report.benchmark_name
        if name not in self._histories:
            self._histories[name] = BenchmarkHistory(benchmark_name=name)
        self._histories[name].add_entry(entry)
        return entry

    def get_history(self, benchmark_name: str) -> BenchmarkHistory:
        """查询 benchmark 历史。

        Args:
            benchmark_name: benchmark 名称。

        Returns:
            BenchmarkHistory（无记录时返回空历史）。
        """
        return self._histories.get(
            benchmark_name,
            BenchmarkHistory(benchmark_name=benchmark_name),
        )

    def list_benchmarks(self) -> list[str]:
        """列出全部有历史记录的 benchmark 名称。"""
        return sorted(self._histories.keys())

    def analyze_trend(self, benchmark_name: str) -> TrendAnalysis | None:
        """分析 benchmark 趋势。

        Args:
            benchmark_name: benchmark 名称。

        Returns:
            TrendAnalysis（无记录时返回 None）。
        """
        history = self.get_history(benchmark_name)
        if not history.entries:
            return None
        hpwls = [e.report.hpwl_um for e in history.entries]
        first_hpwl = hpwls[0]
        last_hpwl = hpwls[-1]
        best_hpwl = min(hpwls)
        worst_hpwl = max(hpwls)
        # 改进幅度（%）: 正数 = 改进（HPWL 减小）
        improvement_vs_first = _pct_improvement(first_hpwl, last_hpwl)
        improvement_vs_last = (
            _pct_improvement(hpwls[-2], last_hpwl) if len(hpwls) >= 2 else 0.0
        )
        # 趋势方向：最近 3 次评估的方向
        trend_direction = _detect_trend(hpwls)
        # 达标率
        passed = sum(1 for e in history.entries if e.report.passed)
        pass_rate = passed / len(history.entries)
        # 回归检测：最近 HPWL 相对最佳恶化 > 阈值
        regression = _detect_regression(best_hpwl, last_hpwl, self.regression_threshold)
        return TrendAnalysis(
            benchmark_name=benchmark_name,
            entry_count=len(history.entries),
            first_hpwl_um=first_hpwl,
            last_hpwl_um=last_hpwl,
            best_hpwl_um=best_hpwl,
            worst_hpwl_um=worst_hpwl,
            improvement_vs_first=improvement_vs_first,
            improvement_vs_last=improvement_vs_last,
            trend_direction=trend_direction,
            pass_rate=pass_rate,
            regression_detected=regression,
        )

    def analyze_all_trends(self) -> list[TrendAnalysis]:
        """分析全部 benchmark 趋势。"""
        return [
            t
            for name in self.list_benchmarks()
            if (t := self.analyze_trend(name)) is not None
        ]

    def save(self, path: str | Path) -> Path:
        """保存历史记录为 JSON 文件。

        Args:
            path: 输出文件路径。

        Returns:
            保存的文件路径。
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "regression_threshold": self.regression_threshold,
            "histories": {
                name: {
                    "benchmark_name": h.benchmark_name,
                    "entries": [asdict(e) for e in h.entries],
                }
                for name, h in self._histories.items()
            },
        }
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    def load(self, path: str | Path) -> None:
        """从 JSON 文件加载历史记录。

        Args:
            path: 输入文件路径。
        """
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        self.regression_threshold = data.get("regression_threshold", 5.0)
        self._histories.clear()
        for name, h_data in data.get("histories", {}).items():
            history = BenchmarkHistory(benchmark_name=name)
            for e_data in h_data.get("entries", []):
                report = BenchmarkReport(**e_data["report"])
                entry = HistoryEntry(
                    run_id=e_data["run_id"],
                    timestamp=e_data["timestamp"],
                    report=report,
                    commit_hash=e_data.get("commit_hash", ""),
                    notes=e_data.get("notes", ""),
                )
                history.add_entry(entry)
            self._histories[name] = history

    def generate_trend_report(self) -> str:
        """生成 Markdown 趋势报告（对标 TILOS CodeBook 趋势可视化）。

        Returns:
            Markdown 字符串。
        """
        trends = self.analyze_all_trends()
        lines = [
            "# PoLaRIS Benchmark 历史趋势报告",
            "",
            "## 1. 摘要",
            "",
            f"- **Benchmark 数**: {len(trends)}",
            f"- **生成时间**: {_now_iso()}",
            f"- **回归阈值**: {self.regression_threshold:.1f}%",
            "",
            "## 2. 趋势总览",
            "",
            "| Benchmark | 记录数 | 首次 HPWL | 最近 HPWL | 最佳 HPWL | "
            "改进(首次) | 改进(上次) | 趋势 | 达标率 | 回归 |",
            "|-----------|--------|-----------|-----------|-----------|"
            "------------|------------|------|--------|------|",
        ]
        for t in trends:
            trend_icon = _trend_icon(t.trend_direction)
            reg_icon = "⚠️" if t.regression_detected else "✅"
            lines.append(
                f"| {t.benchmark_name} | {t.entry_count} | "
                f"{t.first_hpwl_um:.2f} | {t.last_hpwl_um:.2f} | "
                f"{t.best_hpwl_um:.2f} | {t.improvement_vs_first:+.2f}% | "
                f"{t.improvement_vs_last:+.2f}% | {trend_icon} | "
                f"{t.pass_rate:.2%} | {reg_icon} |"
            )
        lines.extend([
            "",
            "## 3. 各 Benchmark 历史详情",
            "",
        ])
        for name in self.list_benchmarks():
            history = self.get_history(name)
            lines.extend([
                f"### {name}",
                "",
                "| Run ID | 时间 | 方法 | HPWL | 重叠 | 利用率 | 达标 | Commit | 备注 |",
                "|--------|------|------|------|------|--------|------|--------|------|",
            ])
            for e in history.entries:
                passed_str = "✅" if e.report.passed else "❌"
                commit_short = e.commit_hash[:8] if e.commit_hash else "—"
                lines.append(
                    f"| {e.run_id[:8]} | {e.timestamp} | "
                    f"{e.report.placement_method} | {e.report.hpwl_um:.2f} | "
                    f"{e.report.overlap_count} | {e.report.area_utilization:.4f} | "
                    f"{passed_str} | {commit_short} | {e.notes} |"
                )
            lines.append("")
        lines.extend([
            "## 4. 来源",
            "",
            "- TILOS CodeBook: https://github.com/TILOS-AI-CAD-Institute/CodeBook",
            "- Circuit Training 评估: https://github.com/google-research/circuit_training",
            "- MLflow 实验追踪: https://mlflow.org/docs/latest/tracking.html",
            "",
        ])
        return "\n".join(lines)


def _pct_improvement(old: float, new: float) -> float:
    """计算改进幅度（%）。

    HPWL 越小越好，正数 = 改进（new < old）。

    Args:
        old: 旧值。
        new: 新值。

    Returns:
        改进幅度（%），old=0 时返回 0。
    """
    if old == 0:
        return 0.0
    return (old - new) / old * 100.0


def _detect_trend(hpwls: list[float]) -> str:
    """检测趋势方向（基于最近 3 次评估）。

    Args:
        hpwls: HPWL 历史列表（按时间排序）。

    Returns:
        ``improving``/``regarding``/``stable``。
    """
    if len(hpwls) < 2:
        return "stable"
    # 取最近 min(3, n) 次评估
    recent = hpwls[-min(3, len(hpwls)):]
    if len(recent) < 2:
        return "stable"
    # 计算线性回归斜率（简单最小二乘）
    n = len(recent)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(recent) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, recent))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return "stable"
    slope = num / den
    # 斜率 < -阈值 = 改进（HPWL 下降），> 阈值 = 恶化
    threshold = 1e-6
    if slope < -threshold:
        return "improving"
    if slope > threshold:
        return "regarding"
    return "stable"


def _detect_regression(
    best_hpwl: float,
    last_hpwl: float,
    threshold: float,
) -> bool:
    """检测回归（最近 HPWL 相对最佳恶化 > 阈值）。

    Args:
        best_hpwl: 历史最佳 HPWL。
        last_hpwl: 最近 HPWL。
        threshold: 回归阈值（%）。

    Returns:
        是否检测到回归。
    """
    if best_hpwl == 0:
        return False
    deterioration = (last_hpwl - best_hpwl) / best_hpwl * 100.0
    return deterioration > threshold


def _trend_icon(direction: str) -> str:
    """趋势方向转图标。"""
    if direction == "improving":
        return "📈 改进"
    if direction == "regarding":
        return "📉 恶化"
    return "➡️ 稳定"


__all__ = [
    "HistoryEntry",
    "BenchmarkHistory",
    "TrendAnalysis",
    "HistoryTracker",
]
