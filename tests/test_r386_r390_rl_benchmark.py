"""R386-R390 测试：RL Benchmark 套件（纯 NumPy/SciPy CPU）。

覆盖 R386-R390 5 个模块 + R03/R02/R04 合规 + 集成场景。

学术依据：While 2012 EMO WFG https://ieeexplore.ieee.org/document/6263723
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from polaris.rl.rl_benchmark import (
    BenchmarkCircuitGenerator,
    BenchmarkMetrics,
    BenchmarkReporter,
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkSuiteConfig,
    BaselineStrategies,
    CircuitSpec,
    MetricSummary,
    default_metrics_fn,
)


# ===========================================================================
# R386 — 电路生成器测试
# ===========================================================================


class TestR386CircuitGenerator:
    """R386 标准电路生成器测试。"""

    def test_generate_mesh(self):
        gen = BenchmarkCircuitGenerator(seed=0)
        c = gen.generate(CircuitSpec(name="t", n_devices=5, topology="mesh"))
        assert c["name"] == "t"
        assert len(c["devices"]) == 5
        # mesh: C(5,2) = 10 条 net
        assert len(c["nets"]) == 10

    def test_generate_linear(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="t", n_devices=5, topology="linear"))
        assert len(c["nets"]) == 4  # N-1 条

    def test_generate_tree(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="t", n_devices=7, topology="tree"))
        assert len(c["nets"]) == 6  # N-1 条

    def test_generate_random(self):
        gen = BenchmarkCircuitGenerator(seed=0)
        c = gen.generate(CircuitSpec(name="t", n_devices=10, topology="random", seed=0))
        # 随机图：net 数量随机但 >= 0
        assert len(c["nets"]) >= 0

    def test_generate_crossbar(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="t", n_devices=9, topology="crossbar"))
        assert len(c["nets"]) >= 1

    def test_invalid_topology_raises(self):
        gen = BenchmarkCircuitGenerator()
        with pytest.raises(ValueError, match="不在"):
            gen.generate(CircuitSpec(name="t", n_devices=5, topology="invalid"))

    def test_invalid_n_devices_raises(self):
        gen = BenchmarkCircuitGenerator()
        with pytest.raises(ValueError, match="n_devices"):
            gen.generate(CircuitSpec(name="t", n_devices=0, topology="mesh"))

    def test_generate_suite(self):
        gen = BenchmarkCircuitGenerator()
        circuits = gen.generate_suite(scales=(5, 10), topologies=("mesh", "linear"))
        # 2 scales × 2 topologies = 4 circuits
        assert len(circuits) == 4

    def test_devices_have_required_fields(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="t", n_devices=3, topology="mesh"))
        for dev in c["devices"]:
            assert "id" in dev
            assert "type" in dev
            assert "width" in dev
            assert "height" in dev
            assert "ports" in dev

    def test_nets_have_required_fields(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="t", n_devices=3, topology="mesh"))
        for net in c["nets"]:
            assert "id" in net
            assert "src" in net
            assert "dst" in net


# ===========================================================================
# R387 — 评估指标测试
# ===========================================================================


class TestR387Metrics:
    """R387 评估指标测试。"""

    def test_reward_summary_basic(self):
        r = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        s = BenchmarkMetrics.reward_summary(r)
        assert s.mean == pytest.approx(3.0)
        assert s.min_val == pytest.approx(1.0)
        assert s.max_val == pytest.approx(5.0)
        assert s.n_samples == 5

    def test_reward_summary_empty_raises(self):
        with pytest.raises(ValueError, match="不能为空"):
            BenchmarkMetrics.reward_summary(np.array([]))

    def test_convergence_iteration_basic(self):
        r = np.array([0.1, 0.5, 0.8, 0.9, 0.95, 1.0])
        idx = BenchmarkMetrics.convergence_iteration(r, threshold=0.9)
        # 0.9 × 1.0 = 0.9，首个 >= 0.9 是索引 3 (值 0.9)
        assert idx == 3

    def test_convergence_iteration_never(self):
        r = np.array([0.1, 0.2, 0.3])  # final=0.3, target=0.27
        idx = BenchmarkMetrics.convergence_iteration(r, threshold=0.9)
        # 0.27 < 0.1? No, 0.27 > 0.1, 0.2, 0.3 ok at index 2
        # Actually 0.9*0.3=0.27, first >= 0.27 is index 2 (0.3)
        assert idx == 2

    def test_convergence_invalid_threshold_raises(self):
        r = np.array([1.0])
        with pytest.raises(ValueError):
            BenchmarkMetrics.convergence_iteration(r, threshold=1.5)
        with pytest.raises(ValueError):
            BenchmarkMetrics.convergence_iteration(r, threshold=0.0)

    def test_coverage(self):
        states = np.array([[1, 0], [0, 1], [1, 0]])  # 2 unique
        cov = BenchmarkMetrics.coverage(states, total_states=10)
        assert cov == pytest.approx(0.2)

    def test_coverage_invalid_total_raises(self):
        with pytest.raises(ValueError):
            BenchmarkMetrics.coverage(np.zeros((1, 2)), total_states=0)

    def test_pareto_front_minimize(self):
        # 最小化：[(1,5),(2,2),(3,3)] 前沿 = {0, 1}
        obj = np.array([[1.0, 5.0], [2.0, 2.0], [3.0, 3.0]])
        front = BenchmarkMetrics.pareto_front_indices(obj, minimize=True)
        assert set(front.tolist()) == {0, 1}

    def test_pareto_front_maximize(self):
        # 最大化：[(1,5),(2,2),(3,3)] 前沿 = {0, 2}
        obj = np.array([[1.0, 5.0], [2.0, 2.0], [3.0, 3.0]])
        front = BenchmarkMetrics.pareto_front_indices(obj, minimize=False)
        assert set(front.tolist()) == {0, 2}

    def test_pareto_front_empty_raises(self):
        with pytest.raises(ValueError):
            BenchmarkMetrics.pareto_front_indices(np.zeros((0, 2)))

    def test_hypervolume_2d_minimize_basic(self):
        """2D hypervolume 最小化：单点 (1, 1), ref (2, 2) → 面积 = 1。"""
        front = np.array([[1.0, 1.0]])
        ref = np.array([2.0, 2.0])
        hv = BenchmarkMetrics.hypervolume_2d(front, ref, minimize=True)
        assert hv == pytest.approx(1.0)

    def test_hypervolume_2d_minimize_two_points(self):
        """2D hypervolume：两点 (1, 1.5) 和 (1.5, 1)，ref (2, 2)。

        排序后：[(1, 1.5), (1.5, 1)]
        i=0: prev_x=1, 不累加
        i=1: hv += (1.5-1) × (2-1.5) = 0.5×0.5 = 0.25
        最后: hv += (2-1.5) × (2-1) = 0.5×1 = 0.5
        总 hv = 0.75
        """
        front = np.array([[1.0, 1.5], [1.5, 1.0]])
        ref = np.array([2.0, 2.0])
        hv = BenchmarkMetrics.hypervolume_2d(front, ref, minimize=True)
        assert hv == pytest.approx(0.75, rel=1e-6)

    def test_hypervolume_2d_invalid_dim_raises(self):
        front = np.array([[1.0, 1.0, 1.0]])
        ref = np.array([2.0, 2.0])
        with pytest.raises(ValueError, match="仅支持 2D"):
            BenchmarkMetrics.hypervolume_2d(front, ref)

    def test_hypervolume_2d_invalid_ref_raises(self):
        """最小化模式下 reference 须 >= 前沿点。"""
        front = np.array([[3.0, 3.0]])
        ref = np.array([2.0, 2.0])
        with pytest.raises(ValueError, match="reference 须"):
            BenchmarkMetrics.hypervolume_2d(front, ref, minimize=True)

    def test_hypervolume_2d_maximize(self):
        """最大化：单点 (3, 3), ref (2, 2) → 面积 = 1。"""
        front = np.array([[3.0, 3.0]])
        ref = np.array([2.0, 2.0])
        hv = BenchmarkMetrics.hypervolume_2d(front, ref, minimize=False)
        assert hv == pytest.approx(1.0)

    def test_hypervolume_2d_empty_front(self):
        front = np.zeros((0, 2))
        ref = np.array([2.0, 2.0])
        hv = BenchmarkMetrics.hypervolume_2d(front, ref)
        assert hv == 0.0


# ===========================================================================
# R388 — 基线策略测试
# ===========================================================================


class TestR388BaselineStrategies:
    """R388 基线策略测试。"""

    def _make_circuit(self, n=5) -> dict:
        gen = BenchmarkCircuitGenerator(seed=0)
        return gen.generate(CircuitSpec(name="t", n_devices=n, topology="mesh"))

    def test_random_placement(self):
        c = self._make_circuit(5)
        p = BaselineStrategies.random(c, grid_size=(4, 4), seed=0)
        assert len(p) == 5
        for dev_id, pos in p.items():
            assert "x" in pos and "y" in pos and "rotation" in pos

    def test_random_no_overlap(self):
        """random 应无重叠（无放回采样）。"""
        c = self._make_circuit(5)
        p = BaselineStrategies.random(c, grid_size=(8, 8), seed=42)
        cells = [(pos["x"], pos["y"]) for pos in p.values()]
        assert len(cells) == len(set(cells))

    def test_random_too_many_devices_raises(self):
        c = self._make_circuit(20)
        with pytest.raises(ValueError, match="超过网格容量"):
            BaselineStrategies.random(c, grid_size=(2, 2))

    def test_random_invalid_circuit_raises(self):
        with pytest.raises(ValueError, match="devices"):
            BaselineStrategies.random({"nets": []}, grid_size=(4, 4))

    def test_greedy_placement(self):
        c = self._make_circuit(5)
        p = BaselineStrategies.greedy(c, grid_size=(8, 8))
        assert len(p) == 5
        # 高连接度器件应在中心附近
        # mesh 拓扑所有器件等连接度
        for pos in p.values():
            assert pos["x"] >= 0
            assert pos["y"] >= 0

    def test_greedy_invalid_circuit_raises(self):
        with pytest.raises(ValueError, match="devices"):
            BaselineStrategies.greedy({"nets": []}, grid_size=(4, 4))
        with pytest.raises(ValueError, match="devices"):
            BaselineStrategies.greedy({"devices": []}, grid_size=(4, 4))

    def test_heuristic_placement(self):
        c = self._make_circuit(5)
        p = BaselineStrategies.heuristic(c, grid_size=(8, 8))
        assert len(p) == 5
        # 蛇形：第一个器件应在 (0, 0)
        first_id = c["devices"][0]["id"]
        assert p[first_id]["x"] == 0
        assert p[first_id]["y"] == 0

    def test_heuristic_invalid_circuit_raises(self):
        with pytest.raises(ValueError, match="devices"):
            BaselineStrategies.heuristic({"nets": []}, grid_size=(4, 4))

    def test_heuristic_too_many_raises(self):
        c = self._make_circuit(20)
        with pytest.raises(ValueError, match="超过网格容量"):
            BaselineStrategies.heuristic(c, grid_size=(2, 2))

    def test_all_strategies_dict(self):
        s = BaselineStrategies.all_strategies()
        assert "random" in s
        assert "greedy" in s
        assert "heuristic" in s
        assert callable(s["random"])

    def test_heuristic_snake_pattern(self):
        """蛇形第 2 行应从右到左。"""
        c = self._make_circuit(10)
        p = BaselineStrategies.heuristic(c, grid_size=(5, 5), cell_size=1.0)
        # 第 2 个器件（i=1，第 0 行）应在 (1, 0)
        d1 = c["devices"][1]["id"]
        assert p[d1]["x"] == 1.0
        # 第 6 个器件（i=5，第 1 行，奇数行右→左）应在 (4, 1)
        d5 = c["devices"][5]["id"]
        assert p[d5]["x"] == 4.0  # gw-1-0 = 5-1-0 = 4


# ===========================================================================
# R389 — 基准测试套件测试
# ===========================================================================


class TestR389BenchmarkSuite:
    """R389 基准测试套件测试。"""

    def test_default_metrics_fn(self):
        gen = BenchmarkCircuitGenerator(seed=0)
        c = gen.generate(CircuitSpec(name="t", n_devices=3, topology="linear"))
        p = BaselineStrategies.heuristic(c, grid_size=(4, 4), cell_size=100.0)
        m = default_metrics_fn(c, p)
        assert "n_placed" in m
        assert "wirelength_mean" in m
        assert "overlaps" in m
        assert m["n_placed"] == 3.0

    def test_default_metrics_fn_empty_raises(self):
        with pytest.raises(ValueError):
            default_metrics_fn({}, {})

    def test_suite_run(self):
        gen = BenchmarkCircuitGenerator()
        circuits = [
            gen.generate(CircuitSpec(name=f"c{i}", n_devices=5, topology="mesh"))
            for i in range(2)
        ]
        strategies = BaselineStrategies.all_strategies()
        suite = BenchmarkSuite(BenchmarkSuiteConfig(grid_size=(8, 8)))
        results = suite.run(circuits, strategies)
        # 2 circuits × 3 strategies = 6 results
        assert len(results) == 6
        for r in results:
            assert isinstance(r, BenchmarkResult)
            assert r.circuit_name in {"c0", "c1"}
            assert r.strategy_name in {"random", "greedy", "heuristic"}
            assert r.elapsed_s > 0
            assert "n_placed" in r.metrics

    def test_suite_run_empty_circuits_raises(self):
        suite = BenchmarkSuite()
        with pytest.raises(ValueError, match="circuits"):
            suite.run([], BaselineStrategies.all_strategies())

    def test_suite_run_empty_strategies_raises(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="c", n_devices=3, topology="mesh"))
        suite = BenchmarkSuite()
        with pytest.raises(ValueError, match="strategies"):
            suite.run([c], {})

    def test_suite_with_custom_metrics_fn(self):
        gen = BenchmarkCircuitGenerator()
        c = gen.generate(CircuitSpec(name="c", n_devices=3, topology="mesh"))

        def custom(circ, place):
            return {"custom_metric": 42.0}

        suite = BenchmarkSuite(BenchmarkSuiteConfig(metrics_fn=custom))
        results = suite.run([c], {"heuristic": BaselineStrategies.heuristic})
        assert results[0].metrics["custom_metric"] == 42.0


# ===========================================================================
# R390 — 报告生成器测试
# ===========================================================================


class TestR390Reporter:
    """R390 报告生成器测试。"""

    def _make_results(self) -> list[BenchmarkResult]:
        return [
            BenchmarkResult(
                circuit_name="c0", strategy_name="random",
                placement={},
                metrics={"wirelength_mean": 100.0, "overlaps": 2.0},
                elapsed_s=0.001,
            ),
            BenchmarkResult(
                circuit_name="c0", strategy_name="heuristic",
                placement={},
                metrics={"wirelength_mean": 50.0, "overlaps": 0.0},
                elapsed_s=0.002,
            ),
        ]

    def test_to_json(self):
        r = self._make_results()
        text = BenchmarkReporter.to_json(r)
        data = json.loads(text)
        assert len(data) == 2
        assert data[0]["circuit"] == "c0"
        assert data[0]["strategy"] == "random"

    def test_to_json_to_file(self, tmp_path):
        r = self._make_results()
        p = tmp_path / "r.json"
        BenchmarkReporter.to_json(r, p)
        assert p.exists()
        data = json.loads(p.read_text())
        assert len(data) == 2

    def test_to_markdown(self):
        r = self._make_results()
        md = BenchmarkReporter.to_markdown(r)
        assert "| Circuit | Strategy |" in md
        assert "c0" in md
        assert "random" in md
        assert "heuristic" in md

    def test_to_markdown_empty_raises(self):
        with pytest.raises(ValueError):
            BenchmarkReporter.to_markdown([])

    def test_aggregate_by_strategy(self):
        r = self._make_results()
        agg = BenchmarkReporter.aggregate_by_strategy(r)
        assert "random" in agg
        assert "heuristic" in agg
        assert isinstance(agg["random"]["wirelength_mean"], MetricSummary)
        assert agg["random"]["wirelength_mean"].mean == pytest.approx(100.0)

    def test_aggregate_empty_raises(self):
        with pytest.raises(ValueError):
            BenchmarkReporter.aggregate_by_strategy([])

    def test_wilcoxon_basic(self):
        """Wilcoxon 符号秩检验基本用例。"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.5, 2.5, 3.5, 4.5, 5.5])
        W, p = BenchmarkReporter.wilcoxon_signed_rank(x, y)
        # 全部 y > x，sign 全负
        assert W < 0
        assert 0.0 <= p <= 1.0

    def test_wilcoxon_identical(self):
        """x == y 时 W = 0, p = 1。"""
        x = np.array([1.0, 2.0, 3.0])
        W, p = BenchmarkReporter.wilcoxon_signed_rank(x, x)
        assert W == 0.0
        assert p == 1.0

    def test_wilcoxon_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="形状"):
            BenchmarkReporter.wilcoxon_signed_rank(np.array([1, 2]), np.array([1]))

    def test_bootstrap_ci(self):
        rng = np.random.default_rng(0)
        samples = rng.normal(0, 1, size=100)
        lo, hi = BenchmarkReporter.bootstrap_ci(samples, n_bootstrap=100, seed=0)
        assert lo < hi
        # 95% CI 应包含样本均值
        assert lo < samples.mean() < hi

    def test_bootstrap_ci_empty_raises(self):
        with pytest.raises(ValueError, match="不能为空"):
            BenchmarkReporter.bootstrap_ci(np.array([]))

    def test_bootstrap_ci_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            BenchmarkReporter.bootstrap_ci(np.array([1.0]), confidence=1.5)


# ===========================================================================
# R03 / R02 / R04 合规
# ===========================================================================


class TestCompliance:
    """R03/R02/R04 合规检查。"""

    def test_r03_no_silent_fallback(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_benchmark.py"
        text = src.read_text(encoding="utf-8")
        assert "except: pass" not in text
        assert "except Exception: pass" not in text

    def test_r03_raise_on_business_error(self):
        gen = BenchmarkCircuitGenerator()
        with pytest.raises(ValueError):
            gen.generate(CircuitSpec(name="t", n_devices=0, topology="mesh"))
        with pytest.raises(ValueError):
            BenchmarkMetrics.reward_summary(np.array([]))

    def test_r02_docstring_references(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_benchmark.py"
        text = src.read_text(encoding="utf-8")
        docstring = text.split('from __future__')[0]
        url_count = docstring.count("https://")
        assert url_count >= 5, f"R02 违规: URL < 5 (实际 {url_count})"

    def test_r02_innovation_marked(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_benchmark.py"
        text = src.read_text(encoding="utf-8")
        assert "*创新*" in text

    def test_r04_no_gpu_imports(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_benchmark.py"
        text = src.read_text(encoding="utf-8")
        for forbidden in ["import cupy", "import torch", "from torch",
                          "from cupy", "import jax", "import cuda"]:
            assert forbidden not in text

    def test_r04_gpu_disabled_flag(self):
        from polaris.rl.rl_benchmark import GPU_DISABLED_R04
        assert GPU_DISABLED_R04 is True


# ===========================================================================
# 集成测试
# ===========================================================================


class TestIntegration:
    """端到端集成测试。"""

    def test_end_to_end_benchmark_pipeline(self):
        """端到端：生成电路 → 运行 3 策略 → 计算指标 → 生成报告。"""
        # 1) 生成电路
        gen = BenchmarkCircuitGenerator(seed=42)
        circuits = gen.generate_suite(scales=(5,), topologies=("mesh", "linear"))
        assert len(circuits) == 2

        # 2) 运行 benchmark
        strategies = BaselineStrategies.all_strategies()
        suite = BenchmarkSuite(BenchmarkSuiteConfig(grid_size=(8, 8)))
        results = suite.run(circuits, strategies)
        # 2 circuits × 3 strategies = 6
        assert len(results) == 6

        # 3) 生成 JSON 报告
        json_text = BenchmarkReporter.to_json(results)
        data = json.loads(json_text)
        assert len(data) == 6

        # 4) 生成 Markdown 报告
        md = BenchmarkReporter.to_markdown(results)
        assert "mesh" in md or "linear" in md

        # 5) 聚合
        agg = BenchmarkReporter.aggregate_by_strategy(results)
        for sname in ["random", "greedy", "heuristic"]:
            assert sname in agg
            assert "wirelength_mean" in agg[sname]

    def test_wilcoxon_compare_strategies(self):
        """用 Wilcoxon 检验两个策略是否显著不同。"""
        rng = np.random.default_rng(0)
        # 模拟两个策略在 10 个电路上的 wirelength
        x_random = rng.normal(100, 10, 10)
        x_heuristic = x_random * 0.6  # heuristic 更短
        W, p = BenchmarkReporter.wilcoxon_signed_rank(x_random, x_heuristic)
        # heuristic 显著优于 random
        assert p < 0.05

    def test_hypervolume_pareto_workflow(self):
        """Pareto 前沿 + hypervolume 完整工作流。"""
        # 模拟 5 个解的 2 目标 (wirelength, overlaps)，最小化
        rng = np.random.default_rng(0)
        objs = rng.uniform([50, 0], [200, 5], size=(5, 2))
        # 计算前沿
        front_idx = BenchmarkMetrics.pareto_front_indices(objs, minimize=True)
        front = objs[front_idx]
        # 计算 hypervolume（参考点取 max × 1.2）
        ref = objs.max(axis=0) * 1.2
        hv = BenchmarkMetrics.hypervolume_2d(front, ref, minimize=True)
        assert hv > 0
        # 前沿应至少 1 个点
        assert front.shape[0] >= 1
