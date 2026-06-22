"""benchmark_history 模块测试（P1-5 深化，第29轮）。

对标 TILOS CodeBook 历史趋势追踪能力，测试历史记录持久化、
趋势分析、改进幅度计算、回归检测、Markdown 趋势报告。

来源:
- TILOS CodeBook: https://github.com/TILOS-AI-CAD-Institute/CodeBook
- MLflow 实验追踪: https://mlflow.org/docs/latest/tracking.html
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.data.benchmark_history import (
    BenchmarkHistory,
    HistoryEntry,
    HistoryTracker,
    RecordMeta,
    TrendAnalysis,
    _detect_regression,
    _detect_trend,
    _pct_improvement,
    _trend_icon,
)
from polaris.data.benchmark_report import BenchmarkReport


def _make_report(
    name: str = "test_bench",
    hpwl: float = 100.0,
    passed: bool = True,
    method: str = "grid",
) -> BenchmarkReport:
    """构造测试用 BenchmarkReport。"""
    return BenchmarkReport(
        benchmark_name=name,
        benchmark_source="CUSTOM",
        placement_method=method,
        hpwl_um=hpwl,
        overlap_count=0,
        area_utilization=0.4,
        module_count=5,
        connection_count=4,
        target_metric="hpwl",
        target_value=200.0,
        passed=passed,
        process_node="220nm SOI",
        timestamp="2026-06-21T00:00:00Z",
        extra={},
    )


class TestHistoryEntry:
    """HistoryEntry 数据类测试。"""

    def test_frozen_dataclass(self) -> None:
        """HistoryEntry 应为 frozen dataclass。"""
        entry = HistoryEntry(
            run_id="r1",
            timestamp="2026-06-21T00:00:00Z",
            report=_make_report(),
        )
        assert entry.run_id == "r1"
        assert entry.commit_hash == ""
        assert entry.notes == ""
        with pytest.raises(AttributeError):
            entry.run_id = "r2"  # type: ignore[misc]

    def test_with_commit_and_notes(self) -> None:
        """HistoryEntry 应支持 commit_hash 和 notes。"""
        entry = HistoryEntry(
            run_id="r1",
            timestamp="2026-06-21T00:00:00Z",
            report=_make_report(),
            commit_hash="abc12345",
            notes="v1.0.0 baseline",
        )
        assert entry.commit_hash == "abc12345"
        assert entry.notes == "v1.0.0 baseline"


class TestBenchmarkHistory:
    """BenchmarkHistory 数据类测试。"""

    def test_add_entry_sorted_by_timestamp(self) -> None:
        """add_entry 应按 timestamp 排序。"""
        history = BenchmarkHistory(benchmark_name="test")
        e1 = HistoryEntry(
            run_id="r1",
            timestamp="2026-06-21T10:00:00Z",
            report=_make_report(),
        )
        e2 = HistoryEntry(
            run_id="r2",
            timestamp="2026-06-21T09:00:00Z",
            report=_make_report(),
        )
        history.add_entry(e1)
        history.add_entry(e2)
        assert history.entries[0].run_id == "r2"
        assert history.entries[1].run_id == "r1"

    def test_latest_and_first(self) -> None:
        """latest/first 应返回正确记录。"""
        history = BenchmarkHistory(benchmark_name="test")
        assert history.latest() is None
        assert history.first() is None
        e1 = HistoryEntry(
            run_id="r1",
            timestamp="2026-06-21T09:00:00Z",
            report=_make_report(hpwl=100.0),
        )
        e2 = HistoryEntry(
            run_id="r2",
            timestamp="2026-06-21T10:00:00Z",
            report=_make_report(hpwl=80.0),
        )
        history.add_entry(e1)
        history.add_entry(e2)
        assert history.first() is e1
        assert history.latest() is e2


class TestPctImprovement:
    """_pct_improvement 函数测试。"""

    def test_improvement(self) -> None:
        """改进（new < old）应返回正数。"""
        assert _pct_improvement(100.0, 80.0) == pytest.approx(20.0)

    def test_regression(self) -> None:
        """恶化（new > old）应返回负数。"""
        assert _pct_improvement(80.0, 100.0) == pytest.approx(-25.0)

    def test_no_change(self) -> None:
        """无变化应返回 0。"""
        assert _pct_improvement(100.0, 100.0) == pytest.approx(0.0)

    def test_old_zero(self) -> None:
        """old=0 应返回 0（避免除零）。"""
        assert _pct_improvement(0.0, 100.0) == 0.0


class TestDetectTrend:
    """_detect_trend 函数测试。"""

    def test_improving(self) -> None:
        """HPWL 持续下降应判定为 improving。"""
        assert _detect_trend([100.0, 90.0, 80.0]) == "improving"

    def test_regarding(self) -> None:
        """HPWL 持续上升应判定为 regarding。"""
        assert _detect_trend([80.0, 90.0, 100.0]) == "regarding"

    def test_stable(self) -> None:
        """HPWL 基本不变应判定为 stable。"""
        assert _detect_trend([100.0, 100.0, 100.0]) == "stable"

    def test_single_entry(self) -> None:
        """单条记录应判定为 stable。"""
        assert _detect_trend([100.0]) == "stable"

    def test_empty(self) -> None:
        """空列表应判定为 stable。"""
        assert _detect_trend([]) == "stable"


class TestDetectRegression:
    """_detect_regression 函数测试。"""

    def test_no_regression(self) -> None:
        """最近 HPWL 接近最佳应无回归。"""
        assert not _detect_regression(100.0, 102.0, threshold=5.0)

    def test_regression_detected(self) -> None:
        """最近 HPWL 恶化 > 阈值应检测到回归。"""
        assert _detect_regression(100.0, 110.0, threshold=5.0)

    def test_best_zero(self) -> None:
        """best_hpwl=0 应返回 False（避免除零）。"""
        assert not _detect_regression(0.0, 100.0, threshold=5.0)


class TestTrendIcon:
    """_trend_icon 函数测试。"""

    def test_improving_icon(self) -> None:
        assert "改进" in _trend_icon("improving")

    def test_regarding_icon(self) -> None:
        assert "恶化" in _trend_icon("regarding")

    def test_stable_icon(self) -> None:
        assert "稳定" in _trend_icon("stable")


class TestHistoryTracker:
    """HistoryTracker 测试。"""

    def test_add_record_returns_entry(self) -> None:
        """add_record 应返回创建的 HistoryEntry。"""
        tracker = HistoryTracker()
        entry = tracker.add_record(_make_report(), notes="baseline")
        assert isinstance(entry, HistoryEntry)
        assert entry.notes == "baseline"
        assert len(entry.run_id) > 0

    def test_add_record_creates_history(self) -> None:
        """add_record 应自动创建 benchmark 历史。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_a"))
        assert "bench_a" in tracker.list_benchmarks()

    def test_get_history_empty(self) -> None:
        """无记录的 benchmark 应返回空历史。"""
        tracker = HistoryTracker()
        history = tracker.get_history("nonexistent")
        assert history.benchmark_name == "nonexistent"
        assert len(history.entries) == 0

    def test_get_history_with_records(self) -> None:
        """有记录的 benchmark 应返回完整历史。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_a", hpwl=100.0))
        tracker.add_record(_make_report(name="bench_a", hpwl=80.0))
        history = tracker.get_history("bench_a")
        assert len(history.entries) == 2

    def test_list_benchmarks_sorted(self) -> None:
        """list_benchmarks 应返回排序后的列表。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_c"))
        tracker.add_record(_make_report(name="bench_a"))
        tracker.add_record(_make_report(name="bench_b"))
        assert tracker.list_benchmarks() == ["bench_a", "bench_b", "bench_c"]

    def test_custom_run_id_and_timestamp(self) -> None:
        """add_record 应支持自定义 run_id 和 timestamp。"""
        tracker = HistoryTracker()
        entry = tracker.add_record(
            _make_report(),
            meta=RecordMeta(run_id="custom_id", timestamp="2026-01-01T00:00:00Z"),
        )
        assert entry.run_id == "custom_id"
        assert entry.timestamp == "2026-01-01T00:00:00Z"


class TestAnalyzeTrend:
    """analyze_trend 测试。"""

    def test_no_history(self) -> None:
        """无记录应返回 None。"""
        tracker = HistoryTracker()
        assert tracker.analyze_trend("nonexistent") is None

    def test_single_entry(self) -> None:
        """单条记录应返回有效趋势分析。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(hpwl=100.0))
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        assert trend.entry_count == 1
        assert trend.first_hpwl_um == 100.0
        assert trend.last_hpwl_um == 100.0
        assert trend.best_hpwl_um == 100.0
        assert trend.worst_hpwl_um == 100.0
        assert trend.improvement_vs_first == pytest.approx(0.0)
        assert trend.improvement_vs_last == pytest.approx(0.0)
        assert trend.trend_direction == "stable"

    def test_improving_trend(self) -> None:
        """HPWL 持续下降应判定为 improving。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(hpwl=100.0), meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=80.0), meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=60.0), meta=RecordMeta(timestamp="2026-06-03T00:00:00Z"))
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        assert trend.trend_direction == "improving"
        assert trend.improvement_vs_first == pytest.approx(40.0)
        assert trend.best_hpwl_um == 60.0
        assert trend.worst_hpwl_um == 100.0
        assert not trend.regression_detected

    def test_regarding_trend_with_regression(self) -> None:
        """HPWL 恶化应判定为 regarding 并检测到回归。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(hpwl=60.0), meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=80.0), meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=100.0), meta=RecordMeta(timestamp="2026-06-03T00:00:00Z"))
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        assert trend.trend_direction == "regarding"
        assert trend.improvement_vs_first == pytest.approx(-66.67, abs=0.01)
        assert trend.regression_detected

    def test_pass_rate(self) -> None:
        """pass_rate 应正确计算达标率。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(hpwl=100.0, passed=True))
        tracker.add_record(_make_report(hpwl=200.0, passed=False))
        tracker.add_record(_make_report(hpwl=90.0, passed=True))
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        assert trend.pass_rate == pytest.approx(2 / 3)

    def test_analyze_all_trends(self) -> None:
        """analyze_all_trends 应返回全部 benchmark 趋势。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_a"))
        tracker.add_record(_make_report(name="bench_b"))
        trends = tracker.analyze_all_trends()
        assert len(trends) == 2
        names = {t.benchmark_name for t in trends}
        assert names == {"bench_a", "bench_b"}


class TestPersistence:
    """save/load 持久化测试。"""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """save→load 应保持数据完整。"""
        tracker = HistoryTracker(regression_threshold=7.5)
        tracker.add_record(
            _make_report(name="bench_a", hpwl=100.0),
            commit_hash="abc12345",
            notes="baseline",
            meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"),
        )
        tracker.add_record(
            _make_report(name="bench_a", hpwl=80.0),
            commit_hash="def67890",
            notes="v2.0.0",
            meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"),
        )
        path = tmp_path / "history.json"
        tracker.save(path)
        assert path.exists()

        loaded = HistoryTracker()
        loaded.load(path)
        assert loaded.regression_threshold == pytest.approx(7.5)
        assert "bench_a" in loaded.list_benchmarks()
        history = loaded.get_history("bench_a")
        assert len(history.entries) == 2
        assert history.entries[0].report.hpwl_um == pytest.approx(100.0)
        assert history.entries[1].report.hpwl_um == pytest.approx(80.0)
        assert history.entries[0].commit_hash == "abc12345"
        assert history.entries[0].notes == "baseline"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """save 应自动创建父目录。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report())
        path = tmp_path / "subdir" / "nested" / "history.json"
        tracker.save(path)
        assert path.exists()

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """load 不存在的文件应无副作用。"""
        tracker = HistoryTracker()
        tracker.load(tmp_path / "nonexistent.json")
        assert tracker.list_benchmarks() == []

    def test_save_json_format(self, tmp_path: Path) -> None:
        """save 应输出合法 JSON。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report())
        path = tmp_path / "history.json"
        tracker.save(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "regression_threshold" in data
        assert "histories" in data


class TestTrendReport:
    """generate_trend_report 测试。"""

    def test_empty_report(self) -> None:
        """无记录时应生成有效报告。"""
        tracker = HistoryTracker()
        report = tracker.generate_trend_report()
        assert "PoLaRIS Benchmark 历史趋势报告" in report
        assert "Benchmark 数**: 0" in report

    def test_report_with_data(self) -> None:
        """有记录时应生成完整报告。"""
        tracker = HistoryTracker()
        tracker.add_record(
            _make_report(name="bench_a", hpwl=100.0),
            commit_hash="abc12345",
            notes="baseline",
            meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"),
        )
        tracker.add_record(
            _make_report(name="bench_a", hpwl=80.0),
            commit_hash="def67890",
            notes="v2.0.0",
            meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"),
        )
        report = tracker.generate_trend_report()
        assert "bench_a" in report
        assert "100.00" in report
        assert "80.00" in report
        assert "abc12345"[:8] in report
        assert "baseline" in report
        assert "TILOS CodeBook" in report

    def test_report_contains_trend_overview_table(self) -> None:
        """报告应包含趋势总览表。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report())
        report = tracker.generate_trend_report()
        assert "趋势总览" in report
        assert "| Benchmark |" in report

    def test_report_contains_history_detail(self) -> None:
        """报告应包含各 benchmark 历史详情。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_a"))
        report = tracker.generate_trend_report()
        assert "历史详情" in report
        assert "### bench_a" in report


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 TILOS CodeBook）。"""

    def test_trend_analysis_dataclass(self) -> None:
        """TrendAnalysis 应为 frozen dataclass。"""
        trend = TrendAnalysis(
            benchmark_name="test",
            entry_count=1,
            first_hpwl_um=100.0,
            last_hpwl_um=100.0,
            best_hpwl_um=100.0,
            worst_hpwl_um=100.0,
            improvement_vs_first=0.0,
            improvement_vs_last=0.0,
            trend_direction="stable",
            pass_rate=1.0,
            regression_detected=False,
        )
        assert trend.benchmark_name == "test"
        with pytest.raises(AttributeError):
            trend.benchmark_name = "other"  # type: ignore[misc]

    def test_full_workflow(self, tmp_path: Path) -> None:
        """完整工作流：记录→分析→持久化→加载→报告。"""
        tracker = HistoryTracker()
        # 模拟 3 轮评估（HPWL 持续改进）
        tracker.add_record(
            _make_report(name="tilos_ariane", hpwl=5000.0),
            commit_hash="c1",
            notes="v1.0.0 grid baseline",
            meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"),
        )
        tracker.add_record(
            _make_report(name="tilos_ariane", hpwl=4000.0, method="rl_ppo"),
            commit_hash="c2",
            notes="v1.1.0 RL PPO",
            meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"),
        )
        tracker.add_record(
            _make_report(name="tilos_ariane", hpwl=3500.0, method="rl_gnn"),
            commit_hash="c3",
            notes="v2.0.0 RL GNN warm-start",
            meta=RecordMeta(timestamp="2026-06-03T00:00:00Z"),
        )
        # 分析趋势
        trend = tracker.analyze_trend("tilos_ariane")
        assert trend is not None
        assert trend.trend_direction == "improving"
        assert trend.improvement_vs_first == pytest.approx(30.0)
        assert trend.best_hpwl_um == 3500.0
        assert not trend.regression_detected
        # 持久化
        path = tmp_path / "trend.json"
        tracker.save(path)
        # 加载并验证
        loaded = HistoryTracker()
        loaded.load(path)
        loaded_trend = loaded.analyze_trend("tilos_ariane")
        assert loaded_trend is not None
        assert loaded_trend.improvement_vs_first == pytest.approx(30.0)
        # 生成报告
        report = tracker.generate_trend_report()
        assert "tilos_ariane" in report
        assert "v2.0.0 RL GNN warm-start" in report

    def test_regression_detection_workflow(self) -> None:
        """回归检测工作流：先改进后恶化应触发回归告警。"""
        tracker = HistoryTracker(regression_threshold=5.0)
        tracker.add_record(_make_report(hpwl=100.0), meta=RecordMeta(timestamp="2026-06-01T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=80.0), meta=RecordMeta(timestamp="2026-06-02T00:00:00Z"))
        tracker.add_record(_make_report(hpwl=90.0), meta=RecordMeta(timestamp="2026-06-03T00:00:00Z"))
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        # 最近 90 vs 最佳 80，恶化 12.5% > 5% 阈值
        assert trend.regression_detected
        assert trend.best_hpwl_um == 80.0
        assert trend.last_hpwl_um == 90.0

    def test_multiple_benchmarks_independent(self) -> None:
        """多 benchmark 历史应独立维护。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(name="bench_a", hpwl=100.0))
        tracker.add_record(_make_report(name="bench_a", hpwl=80.0))
        tracker.add_record(_make_report(name="bench_b", hpwl=200.0))
        tracker.add_record(_make_report(name="bench_b", hpwl=150.0))
        trend_a = tracker.analyze_trend("bench_a")
        trend_b = tracker.analyze_trend("bench_b")
        assert trend_a is not None
        assert trend_b is not None
        assert trend_a.entry_count == 2
        assert trend_b.entry_count == 2
        assert trend_a.first_hpwl_um == 100.0
        assert trend_b.first_hpwl_um == 200.0

    def test_commit_hash_traceability(self) -> None:
        """commit_hash 应支持代码版本追溯。"""
        tracker = HistoryTracker()
        tracker.add_record(_make_report(), commit_hash="abc1234567890")
        history = tracker.get_history("test_bench")
        assert history.entries[0].commit_hash == "abc1234567890"

    def test_tiLOS_codebook_alignment(self) -> None:
        """对标 TILOS CodeBook 历史趋势追踪能力。"""
        tracker = HistoryTracker()
        # CodeBook 核心能力 1: 多次评估记录
        for i, hpwl in enumerate([100.0, 90.0, 80.0, 70.0]):
            tracker.add_record(
                _make_report(hpwl=hpwl),
                commit_hash=f"c{i}",
                notes=f"run {i}",
                meta=RecordMeta(timestamp=f"2026-06-0{i + 1}T00:00:00Z"),
            )
        # CodeBook 核心能力 2: 趋势分析
        trend = tracker.analyze_trend("test_bench")
        assert trend is not None
        assert trend.entry_count == 4
        assert trend.trend_direction == "improving"
        # CodeBook 核心能力 3: 回归检测
        assert hasattr(trend, "regression_detected")
        # CodeBook 核心能力 4: Markdown 趋势报告
        report = tracker.generate_trend_report()
        assert "趋势报告" in report
        # CodeBook 核心能力 5: 持久化
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        tracker.save(path)
        loaded = HistoryTracker()
        loaded.load(path)
        assert "test_bench" in loaded.list_benchmarks()
