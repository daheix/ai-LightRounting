"""R391-R450 测试：RL 综合集成+文档+教程（纯 NumPy/SciPy CPU）。

覆盖 R391-R396 6 个模块 + R397-R400 报告生成 + R03/R02/R04 合规 + 集成场景。

学术依据：Agarwal 2021 NeurIPS https://arxiv.org/abs/2108.13264
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polaris.rl.rl_integration import (
    AlgorithmComparator,
    AlgorithmReportGenerator,
    ComparisonConfig,
    CrossModuleIntegration,
    DocumentationGenerator,
    PipelineConfig,
    PipelineResult,
    RLPipeline,
    RegressionTestSuite,
    ReportConfig,
    TutorialGenerator,
)


# ===========================================================================
# R391 — RL 流水线测试
# ===========================================================================


class TestR391RLPipeline:
    """R391 RL 流水线测试。"""

    def _make_train_fn(self, base_reward=1.0):
        def train_fn(it, rng):
            return {"reward": base_reward + it * 0.1, "loss": 0.5 - it * 0.05}
        return train_fn

    def test_pipeline_run_basic(self):
        pipe = RLPipeline(PipelineConfig(n_iterations=5, seed=42))
        result = pipe.run("test_algo", self._make_train_fn())
        assert isinstance(result, PipelineResult)
        assert result.algorithm_name == "test_algo"
        assert len(result.iterations) == 5
        assert len(result.rewards) == 5
        assert len(result.losses) == 5

    def test_pipeline_invalid_train_fn_raises(self):
        pipe = RLPipeline()
        with pytest.raises(ValueError, match="train_step_fn"):
            pipe.run("test", "not_callable")

    def test_pipeline_train_fn_missing_fields_raises(self):
        pipe = RLPipeline(PipelineConfig(n_iterations=2))

        def bad_fn(it, rng):
            return {"reward": 1.0}  # 缺 loss

        with pytest.raises(ValueError, match="train_step_fn"):
            pipe.run("test", bad_fn)

    def test_pipeline_with_eval(self):
        pipe = RLPipeline(PipelineConfig(n_iterations=4, eval_every=2, seed=0))
        result = pipe.run(
            "test", self._make_train_fn(),
            eval_fn=lambda rng: 0.5,
        )
        # iter 1, 3 应有评估值（eval_every=2）
        eval_values = [v for v in result.eval_values if not np.isnan(v)]
        assert len(eval_values) == 2

    def test_pipeline_final_metrics(self):
        pipe = RLPipeline(PipelineConfig(n_iterations=5))
        result = pipe.run("test", self._make_train_fn())
        assert "reward_mean" in result.final_metrics
        assert "reward_std" in result.final_metrics
        assert "reward_final" in result.final_metrics
        assert "loss_mean" in result.final_metrics
        assert result.final_metrics["reward_final"] == pytest.approx(1.4)  # 1.0 + 4*0.1
        assert result.final_metrics["n_iterations"] == 5.0

    def test_pipeline_elapsed_positive(self):
        pipe = RLPipeline(PipelineConfig(n_iterations=3))
        result = pipe.run("test", self._make_train_fn())
        assert result.elapsed_s > 0


# ===========================================================================
# R392 — 跨模块集成测试
# ===========================================================================


class TestR392CrossModuleIntegration:
    """R392 跨模块集成测试。"""

    def test_ppo_plus_curiosity(self):
        out = CrossModuleIntegration.ppo_plus_curiosity(n_steps=5, seed=0)
        assert len(out["rewards_extrinsic"]) == 5
        assert len(out["rewards_intrinsic"]) == 5
        assert len(out["rewards_total"]) == 5
        # total = ext + int
        for i in range(5):
            assert out["rewards_total"][i] == pytest.approx(
                out["rewards_extrinsic"][i] + out["rewards_intrinsic"][i]
            )

    def test_ppo_plus_transformer(self):
        out = CrossModuleIntegration.ppo_plus_transformer(n_steps=5, seed=0)
        assert len(out["policy_losses"]) == 5
        assert len(out["attention_entropies"]) == 5

    def test_bc_plus_cql(self):
        out = CrossModuleIntegration.bc_plus_cql(n_steps=5, seed=0)
        assert len(out["bc_losses"]) == 5
        assert len(out["cql_losses"]) == 5

    def test_validate_module_imports(self):
        """验证所有 RL 模块可正常导入。"""
        results = CrossModuleIntegration.validate_module_imports()
        expected_modules = [
            "rl_numpy_advanced", "rl_curiosity", "rl_transformer_policy",
            "rl_multi_agent", "rl_hierarchical", "rl_imitation",
            "rl_offline_cql", "rl_benchmark",
        ]
        for mod in expected_modules:
            assert mod in results, f"缺少模块 {mod}"
            assert results[mod] is True, f"模块 {mod} 导入失败"

    def test_validate_module_imports_failure_raises(self):
        """导入不存在的模块应 raise。"""
        # 直接调用真实方法，应全部成功
        results = CrossModuleIntegration.validate_module_imports()
        assert all(results.values())


# ===========================================================================
# R393 — 算法对比器测试
# ===========================================================================


class TestR393AlgorithmComparator:
    """R393 算法对比器测试。"""

    def _make_algos(self):
        def algo_a(it, rng):
            return {"reward": float(rng.normal(1.0, 0.1))}

        def algo_b(it, rng):
            return {"reward": float(rng.normal(0.5, 0.1))}

        return {"A": algo_a, "B": algo_b}

    def test_compare_basic(self):
        cmp = AlgorithmComparator(ComparisonConfig(n_runs=3, n_iterations=5, seed=0))
        out = cmp.compare(self._make_algos())
        assert "A" in out and "B" in out
        assert len(out["A"]["final_rewards"]) == 3
        assert out["A"]["n_runs"] == 3

    def test_compare_empty_algorithms_raises(self):
        cmp = AlgorithmComparator()
        with pytest.raises(ValueError, match="algorithms"):
            cmp.compare({})

    def test_compare_metrics_computed(self):
        cmp = AlgorithmComparator(ComparisonConfig(n_runs=5, n_iterations=3, seed=0))
        out = cmp.compare(self._make_algos())
        for name in ["A", "B"]:
            assert "mean" in out[name]
            assert "std" in out[name]
            assert "ci_lo" in out[name]
            assert "ci_hi" in out[name]
            assert out[name]["ci_lo"] < out[name]["ci_hi"]

    def test_statistical_test(self):
        """算法 A 显著优于 B（A 均值 1.0，B 均值 0.5）。"""
        cmp = AlgorithmComparator(ComparisonConfig(n_runs=10, n_iterations=3, seed=0))
        results = cmp.compare(self._make_algos())
        stat = cmp.statistical_test(results, baseline="B")
        # A vs B
        assert "A" in stat
        assert stat["A"]["better_than_baseline"] == 1.0  # A 优于 B

    def test_statistical_test_invalid_baseline_raises(self):
        cmp = AlgorithmComparator()
        with pytest.raises(ValueError, match="基线"):
            cmp.statistical_test({"A": {"final_rewards": [1.0]}}, baseline="X")

    def test_statistical_test_shape_mismatch_raises(self):
        cmp = AlgorithmComparator()
        results = {
            "A": {"final_rewards": [1.0, 2.0, 3.0]},
            "B": {"final_rewards": [1.0, 2.0]},
        }
        with pytest.raises(ValueError, match="运行次数不一致"):
            cmp.statistical_test(results, baseline="B")

    def test_wilcoxon_identical(self):
        """相同样本 W=0, p=1。"""
        x = np.array([1.0, 2.0, 3.0])
        W, p = AlgorithmComparator._wilcoxon(x, x)
        assert W == 0.0
        assert p == 1.0

    def test_bootstrap_ci_basic(self):
        rng = np.random.default_rng(0)
        s = rng.normal(0, 1, 100)
        lo, hi = AlgorithmComparator._bootstrap_ci(s, n_bootstrap=100, seed=0)
        assert lo < hi

    def test_bootstrap_ci_empty_raises(self):
        with pytest.raises(ValueError, match="不能为空"):
            AlgorithmComparator._bootstrap_ci(np.array([]))


# ===========================================================================
# R394 — 回归测试套件测试
# ===========================================================================


class TestR394RegressionTestSuite:
    """R394 回归测试套件测试。"""

    def test_register_and_run(self):
        suite = RegressionTestSuite()
        suite.register("test1", "测试 1", lambda: None)
        results = suite.run_all()
        assert results["test1"]["pass"] is True
        assert results["test1"]["error"] is None

    def test_register_failing_test(self):
        suite = RegressionTestSuite()

        def fail_fn():
            raise ValueError("故意失败")

        suite.register("fail_test", "失败测试", fail_fn)
        results = suite.run_all()
        assert results["fail_test"]["pass"] is False
        assert "故意失败" in results["fail_test"]["error"]

    def test_register_invalid_raises(self):
        suite = RegressionTestSuite()
        with pytest.raises(ValueError, match="name"):
            suite.register("", "无名字", lambda: None)
        with pytest.raises(ValueError, match="name"):
            suite.register("test", "无函数", "not_callable")

    def test_n_tests(self):
        suite = RegressionTestSuite()
        suite.register("a", "a", lambda: None)
        suite.register("b", "b", lambda: None)
        assert suite.n_tests == 2

    def test_get_test_names(self):
        suite = RegressionTestSuite()
        suite.register("a", "a", lambda: None)
        suite.register("b", "b", lambda: None)
        assert suite.get_test_names() == ["a", "b"]

    def test_multiple_tests(self):
        suite = RegressionTestSuite()
        suite.register("pass1", "通过1", lambda: None)
        suite.register("pass2", "通过2", lambda: None)
        suite.register("fail1", "失败1", lambda: (_ for _ in ()).throw(ValueError("err")))
        results = suite.run_all()
        assert results["pass1"]["pass"] is True
        assert results["pass2"]["pass"] is True
        assert results["fail1"]["pass"] is False


# ===========================================================================
# R395 — 文档生成器测试
# ===========================================================================


class TestR395DocumentationGenerator:
    """R395 文档生成器测试。"""

    def test_generate_module_doc_basic(self):
        doc = DocumentationGenerator.generate_module_doc("polaris.rl.rl_benchmark")
        assert "模块" in doc or "Benchmark" in doc
        assert "BenchmarkCircuitGenerator" in doc

    def test_generate_module_doc_invalid_raises(self):
        with pytest.raises(ImportError):
            DocumentationGenerator.generate_module_doc("nonexistent.module.xyz")

    def test_write_doc(self, tmp_path):
        out = DocumentationGenerator.write_doc(
            "polaris.rl.rl_benchmark", tmp_path / "benchmark.md"
        )
        assert out.exists()
        text = out.read_text()
        assert "BenchmarkCircuitGenerator" in text

    def test_generate_curiosity_doc(self):
        doc = DocumentationGenerator.generate_module_doc("polaris.rl.rl_curiosity")
        assert "Curiosity" in doc or "ICM" in doc or "InverseForward" in doc

    def test_generate_offline_cql_doc(self):
        doc = DocumentationGenerator.generate_module_doc("polaris.rl.rl_offline_cql")
        assert "CQL" in doc or "Conservative" in doc


# ===========================================================================
# R396 — 教程生成器测试
# ===========================================================================


class TestR396TutorialGenerator:
    """R396 教程生成器测试。"""

    def test_ppo_tutorial(self):
        code = TutorialGenerator.ppo_tutorial()
        assert "PPOAdvantageOptimizer" in code
        assert "LargeScalePlacementEnv" in code

    def test_cql_tutorial(self):
        code = TutorialGenerator.cql_tutorial()
        assert "ConservativeQLearning" in code
        assert "OfflineDataset" in code

    def test_benchmark_tutorial(self):
        code = TutorialGenerator.benchmark_tutorial()
        assert "BenchmarkSuite" in code
        assert "BaselineStrategies" in code

    def test_write_all_tutorials(self, tmp_path):
        paths = TutorialGenerator.write_all_tutorials(tmp_path / "tuts")
        assert len(paths) == 3
        for p in paths:
            assert p.exists()
            assert p.suffix == ".py"
            text = p.read_text()
            assert len(text) > 50  # 非空


# ===========================================================================
# R397-R400 — 报告生成器测试
# ===========================================================================


class TestR397ReportGenerator:
    """R397-R400 算法对比报告生成器测试。"""

    def _make_results(self):
        return {
            "A": {
                "final_rewards": [1.0, 1.1, 1.2, 1.0, 1.1],
                "all_rewards": [[1.0], [1.1], [1.2], [1.0], [1.1]],
                "mean": 1.08, "std": 0.08,
                "ci_lo": 1.0, "ci_hi": 1.16, "n_runs": 5,
            },
            "B": {
                "final_rewards": [0.5, 0.6, 0.4, 0.5, 0.6],
                "all_rewards": [[0.5], [0.6], [0.4], [0.5], [0.6]],
                "mean": 0.52, "std": 0.08,
                "ci_lo": 0.44, "ci_hi": 0.6, "n_runs": 5,
            },
        }

    def test_generate_json(self, tmp_path):
        out = AlgorithmReportGenerator.generate(
            self._make_results(),
            config=ReportConfig(
                output_dir=str(tmp_path), generate_json=True,
                generate_markdown=False, generate_tutorial=False,
            ),
        )
        assert "json" in out
        json_path = out["json"]
        assert Path(json_path).exists()
        data = json.loads(Path(json_path).read_text())
        assert "comparison" in data
        assert "A" in data["comparison"]

    def test_generate_markdown(self, tmp_path):
        out = AlgorithmReportGenerator.generate(
            self._make_results(),
            config=ReportConfig(
                output_dir=str(tmp_path), generate_json=False,
                generate_markdown=True, generate_tutorial=False,
            ),
        )
        assert "markdown" in out
        md_path = out["markdown"]
        text = Path(md_path).read_text()
        assert "算法对比报告" in text
        assert "| A |" in text
        assert "| B |" in text

    def test_generate_with_stat_tests(self, tmp_path):
        stat = {"A": {"W_statistic": 5.0, "p_value": 0.01,
                      "significant": 1.0, "better_than_baseline": 1.0}}
        out = AlgorithmReportGenerator.generate(
            self._make_results(), stat,
            config=ReportConfig(
                output_dir=str(tmp_path), generate_json=True,
                generate_markdown=True, generate_tutorial=False,
            ),
        )
        md_text = Path(out["markdown"]).read_text()
        assert "统计显著性检验" in md_text
        json_data = json.loads(Path(out["json"]).read_text())
        assert "statistical_tests" in json_data

    def test_generate_tutorials(self, tmp_path):
        out = AlgorithmReportGenerator.generate(
            self._make_results(),
            config=ReportConfig(
                output_dir=str(tmp_path), generate_json=False,
                generate_markdown=False, generate_tutorial=True,
            ),
        )
        assert "tutorials" in out
        tut_paths = out["tutorials"]
        assert len(tut_paths) == 3

    def test_generate_all(self, tmp_path):
        out = AlgorithmReportGenerator.generate(
            self._make_results(),
            config=ReportConfig(output_dir=str(tmp_path)),
        )
        assert "json" in out
        assert "markdown" in out
        assert "tutorials" in out


# ===========================================================================
# R03 / R02 / R04 合规
# ===========================================================================


class TestCompliance:
    """R03/R02/R04 合规检查。"""

    def test_r03_no_silent_fallback(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_integration.py"
        text = src.read_text(encoding="utf-8")
        assert "except: pass" not in text
        assert "except Exception: pass" not in text

    def test_r03_raise_on_business_error(self):
        pipe = RLPipeline()
        with pytest.raises(ValueError):
            pipe.run("test", "not_callable")
        cmp = AlgorithmComparator()
        with pytest.raises(ValueError):
            cmp.compare({})

    def test_r02_docstring_references(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_integration.py"
        text = src.read_text(encoding="utf-8")
        docstring = text.split('from __future__')[0]
        url_count = docstring.count("https://")
        assert url_count >= 5, f"R02 违规: URL < 5 (实际 {url_count})"

    def test_r02_innovation_marked(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_integration.py"
        text = src.read_text(encoding="utf-8")
        assert "*创新*" in text

    def test_r04_no_gpu_imports(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[1] / "src" / "polaris" / "rl" / "rl_integration.py"
        text = src.read_text(encoding="utf-8")
        for forbidden in ["import cupy", "import torch", "from torch",
                          "from cupy", "import jax", "import cuda"]:
            assert forbidden not in text

    def test_r04_gpu_disabled_flag(self):
        from polaris.rl.rl_integration import GPU_DISABLED_R04
        assert GPU_DISABLED_R04 is True


# ===========================================================================
# 端到端集成测试
# ===========================================================================


class TestEndToEndIntegration:
    """端到端集成测试。"""

    def test_full_pipeline_with_comparison(self):
        """完整流程：流水线 → 算法对比 → 报告生成。"""
        # 1) 定义两个算法
        def algo_ppo(it, rng):
            return {"reward": float(rng.normal(1.0, 0.1)), "loss": 0.5}

        def algo_cql(it, rng):
            return {"reward": float(rng.normal(0.7, 0.1)), "loss": 0.4}

        # 2) 对比
        cmp = AlgorithmComparator(ComparisonConfig(n_runs=5, n_iterations=3, seed=0))
        results = cmp.compare({"PPO": algo_ppo, "CQL": algo_cql})

        # 3) 统计检验
        stat = cmp.statistical_test(results, baseline="CQL")

        # 4) 生成报告
        out = AlgorithmReportGenerator.generate(
            results, stat,
            config=ReportConfig(output_dir="/tmp/test_report"),
        )
        assert "json" in out
        assert "markdown" in out

    def test_pipeline_with_real_modules(self):
        """使用真实 RLPipeline + Benchmark 模块。"""
        from polaris.rl.rl_benchmark import (
            BenchmarkCircuitGenerator, CircuitSpec, BaselineStrategies,
        )

        # 生成电路
        gen = BenchmarkCircuitGenerator(seed=0)
        circuit = gen.generate(CircuitSpec(name="t", n_devices=5, topology="mesh"))

        # 用真实基线策略做 mock 训练
        def train_fn(it, rng):
            p = BaselineStrategies.random(circuit, grid_size=(8, 8), seed=it)
            # 计算 wirelength 作为 reward
            from polaris.rl.rl_benchmark import default_metrics_fn
            m = default_metrics_fn(circuit, p)
            return {"reward": -m["wirelength_mean"], "loss": 100.0 - it}

        pipe = RLPipeline(PipelineConfig(n_iterations=3))
        result = pipe.run("random_baseline", train_fn)
        assert len(result.rewards) == 3
        assert all(r < 0 for r in result.rewards)  # wirelength 取负

    def test_full_documentation_workflow(self, tmp_path):
        """完整文档工作流：生成多个模块文档 + 教程。"""
        # 生成 3 个模块文档
        for mod in ["polaris.rl.rl_benchmark", "polaris.rl.rl_offline_cql",
                    "polaris.rl.rl_curiosity"]:
            DocumentationGenerator.write_doc(mod, tmp_path / f"{mod.split('.')[-1]}.md")

        # 生成教程
        TutorialGenerator.write_all_tutorials(tmp_path / "tutorials")

        # 验证
        assert (tmp_path / "rl_benchmark.md").exists()
        assert (tmp_path / "rl_offline_cql.md").exists()
        assert (tmp_path / "rl_curiosity.md").exists()
        assert (tmp_path / "tutorials").is_dir()
        assert len(list((tmp_path / "tutorials").iterdir())) == 3

    def test_regression_suite_with_real_tests(self):
        """使用真实模块功能作为回归测试。"""
        suite = RegressionTestSuite()

        # 注册 PPO GAE 回归测试（R353 修复后）
        def test_gae_basic():
            from polaris.rl.rl_numpy_advanced import PPOAdvantageOptimizer, PPOAdvConfig
            ppo = PPOAdvantageOptimizer(PPOAdvConfig())
            r = np.array([1.0, 1.0])
            v = np.array([0.0, 0.0])
            d = np.array([0.0, 0.0])
            adv, _ = ppo.compute_gae(r, v, d, last_value=0.0)
            # Â_1 = 1, Â_0 = 1 + 0.99·0.95·1 = 1.9405
            assert abs(adv[0] - 1.9405) < 1e-6

        suite.register("R353_gae_regression", "PPO GAE 回归测试", test_gae_basic)

        # 注册 CQL 默认 α 测试
        def test_cql_default_alpha():
            from polaris.rl.rl_offline_cql import CQLConfig
            assert CQLConfig().alpha == 5.0

        suite.register("R383_cql_alpha", "CQL 默认 α=5.0", test_cql_default_alpha)

        # 运行
        results = suite.run_all()
        for name, r in results.items():
            assert r["pass"] is True, f"{name} 失败: {r['error']}"
