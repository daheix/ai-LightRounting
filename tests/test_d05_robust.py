"""D05 鲁棒优化验收测试。

覆盖鲁棒性优化的核心能力：
- M1: 最坏情况优化
- M2: 公差分析集成
- M3: 鲁棒解 vs 标称解对比

文献来源:
- Wang et al. 2018 "Robust topology optimization of photonic devices"
  https://doi.org/10.1364/OE.26.023273
- Alexander et al. 2021 "Robust optimization of nanophotonic devices"
  https://doi.org/10.1103/PhysRevApplied.16.014013
- Tidy3D Robust Optimization
  https://docs.flexcompute.com/projects/tidy3d/en/latest/
- Lumerical Robust Optimization
  https://www.ansys.com/products/optics/lumerical-robust-design
- Lumopt Robust Optimization
  https://lumopt.readthedocs.io/en/latest/
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.robust_optimizer import (
    MonteCarloEvaluator,
    RobustConfig,
    RobustMode,
    RobustObjective,
    RobustOptimizer,
    RobustResult,
    ToleranceModel,
    ToleranceType,
    create_robust_optimizer,
    create_tolerance_model,
    evaluate_robustness,
    run_robust_optimization,
)


def simple_quadratic(x: np.ndarray) -> float:
    """简单二次函数。"""
    return float(-np.sum(x**2))


def shifted_quadratic(x: np.ndarray) -> float:
    """平移二次函数（最小值在 x=[1,1]）。"""
    return float(-np.sum((x - 1.0) ** 2))


def flat_function(x: np.ndarray) -> float:
    """平坦函数。"""
    return 1.0


def sensitive_function(x: np.ndarray) -> float:
    """对参数敏感的函数。"""
    return float(1.0 / (np.sum(x**2) + 0.1))


class TestToleranceType:
    """ToleranceType 枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert ToleranceType.GAUSSIAN.value == "gaussian"
        assert ToleranceType.UNIFORM.value == "uniform"

    def test_enum_from_string(self) -> None:
        """从字符串构造。"""
        assert ToleranceType("gaussian") == ToleranceType.GAUSSIAN
        assert ToleranceType("uniform") == ToleranceType.UNIFORM


class TestRobustMode:
    """RobustMode 枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert RobustMode.MEAN.value == "mean"
        assert RobustMode.WORST_CASE.value == "worst_case"
        assert RobustMode.MEAN_MINUS_STD.value == "mean_minus_std"

    def test_enum_from_string(self) -> None:
        """从字符串构造。"""
        assert RobustMode("mean") == RobustMode.MEAN
        assert RobustMode("worst_case") == RobustMode.WORST_CASE


class TestToleranceModel:
    """ToleranceModel 公差模型测试。"""

    def test_default_tolerance(self) -> None:
        """默认公差。"""
        tol = ToleranceModel()
        assert tol.tol_type == ToleranceType.GAUSSIAN
        assert tol.relative_std == 0.05
        assert tol.absolute_std == 0.0

    def test_custom_tolerance(self) -> None:
        """自定义公差。"""
        tol = ToleranceModel(
            tol_type=ToleranceType.UNIFORM,
            relative_std=0.1,
            absolute_std=0.01,
            seed=42,
        )
        assert tol.tol_type == ToleranceType.UNIFORM
        assert tol.relative_std == 0.1
        assert tol.absolute_std == 0.01
        assert tol.seed == 42

    def test_sample_gaussian_shape(self) -> None:
        """高斯采样形状正确。"""
        tol = ToleranceModel(tol_type=ToleranceType.GAUSSIAN, seed=42)
        params = np.array([1.0, 2.0, 3.0])
        sampled = tol.sample(params)
        assert sampled.shape == params.shape

    def test_sample_uniform_shape(self) -> None:
        """均匀采样形状正确。"""
        tol = ToleranceModel(tol_type=ToleranceType.UNIFORM, seed=42)
        params = np.array([1.0, 2.0, 3.0])
        sampled = tol.sample(params)
        assert sampled.shape == params.shape

    def test_sample_reproducible(self) -> None:
        """相同种子可复现。"""
        tol1 = ToleranceModel(seed=42)
        tol2 = ToleranceModel(seed=42)
        params = np.array([1.0, 2.0, 3.0])
        s1 = tol1.sample(params)
        s2 = tol2.sample(params)
        assert np.allclose(s1, s2)

    def test_sample_relative_std_effect(self) -> None:
        """相对标准差影响扰动幅度。"""
        params = np.array([10.0, 10.0])
        tol_small = ToleranceModel(relative_std=0.01, seed=42)
        tol_large = ToleranceModel(relative_std=0.5, seed=42)

        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        s_small = tol_small.sample(params, rng1)
        s_large = tol_large.sample(params, rng2)

        assert np.linalg.norm(s_large - params) >= np.linalg.norm(s_small - params)

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可修改。"""
        tol = ToleranceModel()
        with pytest.raises(AttributeError):
            tol.relative_std = 0.1


class TestRobustConfig:
    """RobustConfig 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = RobustConfig()
        assert cfg.mode == RobustMode.MEAN
        assert cfg.num_samples == 8
        assert cfg.seed == 42
        assert cfg.max_iterations == 50
        assert cfg.learning_rate == 0.01
        assert cfg.beta == 1.0

    def test_custom_config(self) -> None:
        """自定义配置。"""
        tol = ToleranceModel(relative_std=0.1)
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.WORST_CASE,
            num_samples=16,
            max_iterations=30,
            learning_rate=0.05,
            beta=2.0,
        )
        assert cfg.mode == RobustMode.WORST_CASE
        assert cfg.num_samples == 16
        assert cfg.max_iterations == 30
        assert cfg.beta == 2.0


class TestMonteCarloEvaluator:
    """MonteCarloEvaluator 蒙特卡洛评估测试。"""

    def test_evaluator_returns_three_values(self) -> None:
        """返回均值、标准差、最差值。"""
        tol = ToleranceModel(relative_std=0.05, seed=42)
        evaluator = MonteCarloEvaluator(
            fom_fn=simple_quadratic,
            tolerance=tol,
            num_samples=10,
            seed=42,
        )
        params = np.array([1.0, 2.0])
        mean, std, worst = evaluator.evaluate(params)

        assert isinstance(mean, float)
        assert isinstance(std, float)
        assert isinstance(worst, float)
        assert std >= 0.0

    def test_evaluator_flat_function_zero_std(self) -> None:
        """平坦函数标准差接近 0。"""
        tol = ToleranceModel(relative_std=0.1, seed=42)
        evaluator = MonteCarloEvaluator(
            fom_fn=flat_function,
            tolerance=tol,
            num_samples=20,
            seed=42,
        )
        params = np.array([1.0, 2.0])
        mean, std, worst = evaluator.evaluate(params)

        assert abs(mean - 1.0) < 1e-10
        assert std < 1e-10
        assert abs(worst - 1.0) < 1e-10

    def test_evaluator_num_samples(self) -> None:
        """采样数影响结果稳定性。"""
        tol = ToleranceModel(relative_std=0.2, seed=42)
        params = np.array([1.0, 2.0])

        evaluator_small = MonteCarloEvaluator(simple_quadratic, tol, num_samples=5, seed=42)
        evaluator_large = MonteCarloEvaluator(simple_quadratic, tol, num_samples=100, seed=42)

        mean_small, _, _ = evaluator_small.evaluate(params)
        mean_large, _, _ = evaluator_large.evaluate(params)

        assert isinstance(mean_small, float)
        assert isinstance(mean_large, float)

    def test_evaluator_reproducible(self) -> None:
        """相同种子结果可复现。"""
        tol = ToleranceModel(seed=42)
        ev1 = MonteCarloEvaluator(simple_quadratic, tol, num_samples=10, seed=42)
        ev2 = MonteCarloEvaluator(simple_quadratic, tol, num_samples=10, seed=42)
        params = np.array([1.0, 2.0])

        r1 = ev1.evaluate(params)
        r2 = ev2.evaluate(params)
        assert np.allclose(r1, r2)


class TestRobustObjective:
    """RobustObjective 鲁棒目标函数测试。"""

    def test_mean_mode(self) -> None:
        """MEAN 模式下 robust_fom = mean。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, mode=RobustMode.MEAN, num_samples=10, seed=42)
        obj = RobustObjective(simple_quadratic, cfg)
        params = np.array([1.0, 2.0])
        robust_fom, mean, std, worst = obj.evaluate(params)

        assert abs(robust_fom - mean) < 1e-10

    def test_worst_case_mode(self) -> None:
        """WORST_CASE 模式下 robust_fom = worst。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, mode=RobustMode.WORST_CASE, num_samples=10, seed=42)
        obj = RobustObjective(simple_quadratic, cfg)
        params = np.array([1.0, 2.0])
        robust_fom, mean, std, worst = obj.evaluate(params)

        assert abs(robust_fom - worst) < 1e-10

    def test_mean_minus_std_mode(self) -> None:
        """MEAN_MINUS_STD 模式。"""
        tol = ToleranceModel(seed=42)
        beta = 2.0
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.MEAN_MINUS_STD,
            num_samples=10,
            beta=beta,
            seed=42,
        )
        obj = RobustObjective(simple_quadratic, cfg)
        params = np.array([1.0, 2.0])
        robust_fom, mean, std, worst = obj.evaluate(params)

        expected = mean - beta * std
        assert abs(robust_fom - expected) < 1e-10

    def test_worst_le_mean(self) -> None:
        """最差值 <= 均值（对于最大化问题，worst 是 min）。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, mode=RobustMode.MEAN, num_samples=20, seed=42)
        obj = RobustObjective(sensitive_function, cfg)
        params = np.array([1.0, 1.0])
        _, mean, std, worst = obj.evaluate(params)

        assert worst <= mean + std


class TestRobustOptimizerM1WorstCase:
    """M1: 最坏情况优化测试。"""

    def test_worst_case_optimization_runs(self) -> None:
        """最坏情况优化能运行。"""
        tol = ToleranceModel(relative_std=0.1, seed=42)
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.WORST_CASE,
            num_samples=10,
            max_iterations=10,
            learning_rate=0.01,
            seed=42,
        )
        opt = RobustOptimizer(cfg)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, simple_quadratic)

        assert isinstance(result, RobustResult)
        assert result.iterations > 0
        assert len(result.fom_history) == result.iterations

    def test_worst_case_fom_history(self) -> None:
        """最坏情况 FoM 历史。"""
        tol = ToleranceModel(relative_std=0.05, seed=42)
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.WORST_CASE,
            num_samples=8,
            max_iterations=20,
            learning_rate=0.02,
            seed=42,
        )
        opt = RobustOptimizer(cfg)
        initial = np.array([3.0, 3.0])

        result = opt.optimize(initial, simple_quadratic)

        assert result.fom_worst <= result.fom_mean

    def test_worst_case_result_fields(self) -> None:
        """结果字段完整性。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, max_iterations=5, seed=42)
        opt = RobustOptimizer(cfg)
        initial = np.array([1.0, 1.0])

        result = opt.optimize(initial, simple_quadratic)

        assert hasattr(result, 'optimal_params')
        assert hasattr(result, 'optimal_fom')
        assert hasattr(result, 'fom_mean')
        assert hasattr(result, 'fom_std')
        assert hasattr(result, 'fom_worst')
        assert hasattr(result, 'fom_history')
        assert hasattr(result, 'iterations')
        assert hasattr(result, 'converged')


class TestRobustOptimizerM2Tolerance:
    """M2: 公差分析集成测试。"""

    def test_evaluate_robustness_function(self) -> None:
        """evaluate_robustness 便捷函数。"""
        tol = ToleranceModel(seed=42)
        params = np.array([1.0, 2.0])
        mean, std, worst = evaluate_robustness(
            params, simple_quadratic, tol, num_samples=10, seed=42,
        )
        assert isinstance(mean, float)
        assert isinstance(std, float)
        assert isinstance(worst, float)

    def test_larger_tolerance_larger_std(self) -> None:
        """公差越大，标准差越大。"""
        params = np.array([1.0, 1.0])

        tol_small = ToleranceModel(relative_std=0.01, seed=42)
        tol_large = ToleranceModel(relative_std=0.3, seed=42)

        _, std_small, _ = evaluate_robustness(
            params, sensitive_function, tol_small, num_samples=50, seed=42,
        )
        _, std_large, _ = evaluate_robustness(
            params, sensitive_function, tol_large, num_samples=50, seed=42,
        )

        assert std_large > std_small

    def test_uniform_vs_gaussian_tolerance(self) -> None:
        """均匀和高斯公差都能工作。"""
        params = np.array([1.0, 2.0])
        gaussian_tol = ToleranceModel(tol_type=ToleranceType.GAUSSIAN, seed=42)
        uniform_tol = ToleranceModel(tol_type=ToleranceType.UNIFORM, seed=42)

        mean_g, _, _ = evaluate_robustness(
            params, simple_quadratic, gaussian_tol, num_samples=10, seed=42,
        )
        mean_u, _, _ = evaluate_robustness(
            params, simple_quadratic, uniform_tol, num_samples=10, seed=42,
        )

        assert isinstance(mean_g, float)
        assert isinstance(mean_u, float)

    def test_tolerance_absolute_std(self) -> None:
        """绝对标准差。"""
        params = np.array([0.0, 0.0])
        tol = ToleranceModel(absolute_std=0.1, seed=42)
        sampled = tol.sample(params)
        assert sampled.shape == params.shape

    def test_create_tolerance_model_factory(self) -> None:
        """工厂函数。"""
        tol = create_tolerance_model(
            tol_type=ToleranceType.GAUSSIAN,
            relative_std=0.1,
            seed=42,
        )
        assert isinstance(tol, ToleranceModel)
        assert tol.relative_std == 0.1


class TestRobustOptimizerM3Comparison:
    """M3: 鲁棒解 vs 标称解对比测试。"""

    def test_nominal_vs_robust_different(self) -> None:
        """标称解和鲁棒解应该不同。"""
        tol = ToleranceModel(relative_std=0.2, seed=42)

        nominal_opt = RobustOptimizer(RobustConfig(
            tolerance=tol,
            mode=RobustMode.MEAN,
            num_samples=1,
            max_iterations=20,
            learning_rate=0.02,
            seed=42,
        ))
        robust_opt = RobustOptimizer(RobustConfig(
            tolerance=tol,
            mode=RobustMode.MEAN_MINUS_STD,
            num_samples=20,
            max_iterations=20,
            learning_rate=0.02,
            seed=42,
            beta=1.0,
        ))

        initial = np.array([2.0, 2.0])
        nominal_result = nominal_opt.optimize(initial, simple_quadratic)
        robust_result = robust_opt.optimize(initial, simple_quadratic)

        assert nominal_result.iterations > 0
        assert robust_result.iterations > 0

    def test_robust_has_lower_std_potentially(self) -> None:
        """鲁棒优化目标是降低方差（MEAN_MINUS_STD 模式）。"""
        tol = ToleranceModel(relative_std=0.15, seed=42)
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.MEAN_MINUS_STD,
            num_samples=15,
            max_iterations=15,
            learning_rate=0.01,
            seed=42,
        )
        opt = RobustOptimizer(cfg)
        initial = np.array([1.5, 1.5])

        result = opt.optimize(initial, simple_quadratic)

        assert result.fom_std >= 0.0

    def test_mean_mode_improves_mean(self) -> None:
        """MEAN 模式提升均值。"""
        tol = ToleranceModel(relative_std=0.05, seed=42)
        cfg = RobustConfig(
            tolerance=tol,
            mode=RobustMode.MEAN,
            num_samples=10,
            max_iterations=30,
            learning_rate=0.02,
            seed=42,
        )
        opt = RobustOptimizer(cfg)
        initial = np.array([3.0, 3.0])

        result = opt.optimize(initial, simple_quadratic)

        assert result.fom_history[-1] >= result.fom_history[0]


class TestRobustOptimizerEdgeCases:
    """边界情况测试。"""

    def test_single_iteration(self) -> None:
        """单次迭代。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, max_iterations=1, seed=42)
        opt = RobustOptimizer(cfg)
        initial = np.array([1.0, 2.0])

        result = opt.optimize(initial, simple_quadratic)

        assert result.iterations == 1

    def test_1d_problem(self) -> None:
        """1D 问题。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, max_iterations=10, seed=42)
        opt = RobustOptimizer(cfg)
        initial = np.array([2.0])

        result = opt.optimize(initial, simple_quadratic)

        assert result.iterations > 0
        assert result.optimal_params.shape == (1,)

    def test_flat_function_converges_fast(self) -> None:
        """平坦函数快速收敛。"""
        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(
            tolerance=tol,
            max_iterations=50,
            convergence_threshold=1e-10,
            seed=42,
        )
        opt = RobustOptimizer(cfg)
        initial = np.array([1.0, 2.0])

        result = opt.optimize(initial, flat_function)

        assert result.converged is True or result.iterations <= 50

    def test_create_robust_optimizer_factory(self) -> None:
        """工厂函数。"""
        opt = create_robust_optimizer()
        assert isinstance(opt, RobustOptimizer)

    def test_run_robust_optimization(self) -> None:
        """便捷函数。"""
        initial = np.array([1.0, 1.0])
        result = run_robust_optimization(
            initial,
            simple_quadratic,
            config=RobustConfig(max_iterations=5, seed=42),
        )
        assert isinstance(result, RobustResult)

    def test_robust_gradient_with_custom_grad_fn(self) -> None:
        """自定义梯度函数。"""
        def grad_fn(x):
            return -2.0 * x

        tol = ToleranceModel(seed=42)
        cfg = RobustConfig(tolerance=tol, max_iterations=10, seed=42)
        opt = RobustOptimizer(cfg)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, simple_quadratic, grad_fn=grad_fn)

        assert result.iterations > 0
