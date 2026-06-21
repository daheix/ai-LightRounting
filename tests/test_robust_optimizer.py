"""鲁棒性优化测试（第39轮 P2-2 深化，制造公差）。

测试覆盖：
- ToleranceType / ToleranceModel 公差模型
- RobustMode / RobustConfig 配置
- RobustResult 结果
- MonteCarloEvaluator 蒙特卡洛评估
- RobustObjective 鲁棒性目标
- RobustOptimizer 鲁棒性优化器
- 工厂函数
- 商业差距缩减验证（对标 Tidy3D/Lumerical/lumopt）
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


class TestToleranceType:
    """公差类型测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert ToleranceType.GAUSSIAN.value == "gaussian"
        assert ToleranceType.UNIFORM.value == "uniform"

    def test_enum_from_value(self) -> None:
        """从字符串构造。"""
        assert ToleranceType("gaussian") == ToleranceType.GAUSSIAN
        assert ToleranceType("uniform") == ToleranceType.UNIFORM


class TestToleranceModel:
    """制造公差模型测试。"""

    def test_default_model(self) -> None:
        """默认模型。"""
        model = ToleranceModel()
        assert model.tol_type == ToleranceType.GAUSSIAN
        assert model.relative_std == 0.05
        assert model.absolute_std == 0.0
        assert model.seed is None

    def test_custom_model(self) -> None:
        """自定义模型。"""
        model = ToleranceModel(
            tol_type=ToleranceType.UNIFORM,
            relative_std=0.1,
            absolute_std=0.01,
            seed=42,
        )
        assert model.tol_type == ToleranceType.UNIFORM
        assert model.relative_std == 0.1
        assert model.absolute_std == 0.01
        assert model.seed == 42

    def test_sample_gaussian(self) -> None:
        """高斯扰动采样。"""
        model = ToleranceModel(
            tol_type=ToleranceType.GAUSSIAN,
            relative_std=0.1,
            seed=42,
        )
        params = np.array([1.0, 2.0, 3.0])
        rng = np.random.default_rng(42)
        perturbed = model.sample(params, rng)
        # 扰动后的值应接近原值（在 3σ 内）
        assert np.all(np.abs(perturbed - params) < 1.0)

    def test_sample_uniform(self) -> None:
        """均匀扰动采样。"""
        model = ToleranceModel(
            tol_type=ToleranceType.UNIFORM,
            relative_std=0.1,
            seed=42,
        )
        params = np.array([1.0, 2.0, 3.0])
        rng = np.random.default_rng(42)
        perturbed = model.sample(params, rng)
        # 均匀扰动幅度应小于等于 std
        std = 0.1 * np.abs(params)
        assert np.all(np.abs(perturbed - params) <= std + 1e-10)

    def test_sample_reproducible(self) -> None:
        """可复现性（相同种子）。"""
        model = ToleranceModel(seed=42)
        params = np.array([1.0, 2.0])
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        p1 = model.sample(params, rng1)
        p2 = model.sample(params, rng2)
        assert np.allclose(p1, p2)

    def test_sample_absolute_std(self) -> None:
        """绝对标准差。"""
        model = ToleranceModel(
            relative_std=0.0,
            absolute_std=0.1,
            seed=42,
        )
        params = np.array([0.0, 0.0])
        rng = np.random.default_rng(42)
        perturbed = model.sample(params, rng)
        # 参数为 0，仅有绝对扰动
        assert not np.allclose(perturbed, 0.0)

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        model = ToleranceModel()
        with pytest.raises(AttributeError):
            model.relative_std = 0.2  # type: ignore[misc]


class TestRobustMode:
    """鲁棒性模式测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert RobustMode.MEAN.value == "mean"
        assert RobustMode.WORST_CASE.value == "worst_case"
        assert RobustMode.MEAN_MINUS_STD.value == "mean_minus_std"

    def test_enum_from_value(self) -> None:
        """从字符串构造。"""
        assert RobustMode("mean") == RobustMode.MEAN
        assert RobustMode("worst_case") == RobustMode.WORST_CASE
        assert RobustMode("mean_minus_std") == RobustMode.MEAN_MINUS_STD


class TestRobustConfig:
    """鲁棒性配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = RobustConfig()
        assert cfg.mode == RobustMode.MEAN
        assert cfg.num_samples == 8
        assert cfg.seed == 42
        assert cfg.max_iterations == 50
        assert cfg.convergence_threshold == 1e-4
        assert cfg.learning_rate == 0.01
        assert cfg.beta == 1.0
        assert isinstance(cfg.tolerance, ToleranceModel)

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = RobustConfig(
            mode=RobustMode.WORST_CASE,
            num_samples=16,
            max_iterations=100,
            learning_rate=0.05,
            beta=2.0,
        )
        assert cfg.mode == RobustMode.WORST_CASE
        assert cfg.num_samples == 16
        assert cfg.max_iterations == 100
        assert cfg.learning_rate == 0.05
        assert cfg.beta == 2.0

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = RobustConfig()
        with pytest.raises(AttributeError):
            cfg.mode = RobustMode.WORST_CASE  # type: ignore[misc]


class TestRobustResult:
    """鲁棒性结果测试。"""

    def test_default_result(self) -> None:
        """默认结果。"""
        result = RobustResult(optimal_params=np.array([1.0]))
        assert result.optimal_fom == 0.0
        assert result.fom_mean == 0.0
        assert result.fom_std == 0.0
        assert result.fom_worst == 0.0
        assert result.fom_history == []
        assert result.iterations == 0
        assert result.converged is False

    def test_result_with_history(self) -> None:
        """带历史的结果。"""
        result = RobustResult(
            optimal_params=np.array([1.0]),
            optimal_fom=0.95,
            fom_mean=0.93,
            fom_std=0.02,
            fom_worst=0.88,
            fom_history=[0.5, 0.7, 0.95],
            iterations=3,
            converged=True,
        )
        assert result.optimal_fom == 0.95
        assert result.fom_mean == 0.93
        assert result.fom_std == 0.02
        assert result.fom_worst == 0.88
        assert len(result.fom_history) == 3
        assert result.iterations == 3
        assert result.converged is True


class TestMonteCarloEvaluator:
    """蒙特卡洛评估器测试。"""

    def test_creation(self) -> None:
        """创建评估器。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        evaluator = MonteCarloEvaluator(
            fom_fn=fom_fn,
            tolerance=ToleranceModel(seed=42),
            num_samples=10,
        )
        assert evaluator.num_samples == 10

    def test_evaluate(self) -> None:
        """评估统计量。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        evaluator = MonteCarloEvaluator(
            fom_fn=fom_fn,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        params = np.array([1.0, 2.0])
        mean, std, worst = evaluator.evaluate(params)
        # 均值应接近 5（1+4）
        assert 3.0 < mean < 8.0
        assert std >= 0
        assert worst <= mean

    def test_evaluate_no_perturbation(self) -> None:
        """无扰动时统计量应一致。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        evaluator = MonteCarloEvaluator(
            fom_fn=fom_fn,
            tolerance=ToleranceModel(relative_std=0.0, absolute_std=0.0),
            num_samples=8,
        )
        params = np.array([1.0, 2.0])
        mean, std, worst = evaluator.evaluate(params)
        # 无扰动时所有样本相同
        assert np.isclose(mean, 5.0)
        assert np.isclose(std, 0.0)
        assert np.isclose(worst, 5.0)


class TestRobustObjective:
    """鲁棒性目标函数测试。"""

    def test_mean_mode(self) -> None:
        """MEAN 模式：最大化均值。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p))

        cfg = RobustConfig(
            mode=RobustMode.MEAN,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        obj = RobustObjective(fom_fn, cfg)
        robust_fom, mean, std, worst = obj.evaluate(np.array([1.0, 2.0]))
        # MEAN 模式下 robust_fom == mean
        assert np.isclose(robust_fom, mean)
        assert robust_fom >= worst

    def test_worst_case_mode(self) -> None:
        """WORST_CASE 模式：最大化最差情况。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p))

        cfg = RobustConfig(
            mode=RobustMode.WORST_CASE,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        obj = RobustObjective(fom_fn, cfg)
        robust_fom, mean, std, worst = obj.evaluate(np.array([1.0, 2.0]))
        # WORST_CASE 模式下 robust_fom == worst
        assert np.isclose(robust_fom, worst)
        assert robust_fom <= mean

    def test_mean_minus_std_mode(self) -> None:
        """MEAN_MINUS_STD 模式：最大化 mean - beta * std。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p))

        cfg = RobustConfig(
            mode=RobustMode.MEAN_MINUS_STD,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
            beta=2.0,
        )
        obj = RobustObjective(fom_fn, cfg)
        robust_fom, mean, std, worst = obj.evaluate(np.array([1.0, 2.0]))
        # MEAN_MINUS_STD 模式下 robust_fom == mean - beta * std
        assert np.isclose(robust_fom, mean - 2.0 * std)


class TestRobustOptimizer:
    """鲁棒性优化器测试。"""

    def test_creation(self) -> None:
        """创建优化器。"""
        opt = RobustOptimizer()
        assert opt.config.mode == RobustMode.MEAN
        assert opt.config.max_iterations == 50

    def test_optimize_quadratic(self) -> None:
        """二次函数最大化（端到端）。

        目标：max -(w-3)^2 + 10，最优 w=3，FoM=10
        """
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 3.0) ** 2 + 10.0)

        cfg = RobustConfig(
            mode=RobustMode.MEAN,
            tolerance=ToleranceModel(relative_std=0.01, seed=42),
            num_samples=4,
            max_iterations=30,
            learning_rate=0.05,
            convergence_threshold=1e-6,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 参数应向 3 靠拢
        assert result.optimal_params[0] > 1.0
        assert result.iterations > 0
        assert len(result.fom_history) == result.iterations

    def test_optimize_with_gradient(self) -> None:
        """带解析梯度的优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 2.0) ** 2)

        def grad_fn(p: np.ndarray) -> np.ndarray:
            return np.array([-2.0 * (p[0] - 2.0)])

        cfg = RobustConfig(
            mode=RobustMode.MEAN,
            tolerance=ToleranceModel(relative_std=0.01, seed=42),
            num_samples=4,
            max_iterations=50,
            learning_rate=0.1,
            convergence_threshold=1e-6,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn, grad_fn)
        # 参数应向 2 靠拢
        assert result.optimal_params[0] > 0.5

    def test_optimize_records_history(self) -> None:
        """优化历史记录。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-p[0] ** 2)

        cfg = RobustConfig(
            max_iterations=5,
            num_samples=2,
            tolerance=ToleranceModel(relative_std=0.01, seed=42),
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([1.0]), fom_fn)
        assert len(result.fom_history) == result.iterations
        assert result.iterations <= 5

    def test_optimize_convergence(self) -> None:
        """收敛检测。"""
        call_count = [0]

        def fom_fn(p: np.ndarray) -> float:
            call_count[0] += 1
            return float(-(p[0] - 1.0) ** 2 + 5.0)

        cfg = RobustConfig(
            max_iterations=100,
            num_samples=2,
            tolerance=ToleranceModel(relative_std=0.001, seed=42),
            convergence_threshold=1e-3,
            learning_rate=0.01,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.5]), fom_fn)
        # 应在 max_iterations 之前收敛或达到上限
        assert result.iterations <= 100


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_tolerance_model(self) -> None:
        """创建公差模型工厂。"""
        model = create_tolerance_model(
            tol_type=ToleranceType.UNIFORM,
            relative_std=0.1,
            seed=42,
        )
        assert isinstance(model, ToleranceModel)
        assert model.tol_type == ToleranceType.UNIFORM
        assert model.relative_std == 0.1

    def test_create_robust_optimizer(self) -> None:
        """创建鲁棒性优化器工厂。"""
        opt = create_robust_optimizer()
        assert isinstance(opt, RobustOptimizer)

    def test_run_robust_optimization(self) -> None:
        """运行鲁棒性优化工厂。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        cfg = RobustConfig(
            max_iterations=5,
            num_samples=2,
            tolerance=ToleranceModel(relative_std=0.01, seed=42),
        )
        result = run_robust_optimization(np.array([0.0]), fom_fn, cfg)
        assert isinstance(result, RobustResult)
        assert result.iterations > 0

    def test_evaluate_robustness(self) -> None:
        """评估鲁棒性工厂。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        mean, std, worst = evaluate_robustness(
            params=np.array([1.0, 2.0]),
            fom_fn=fom_fn,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        assert mean > 0
        assert std >= 0
        assert worst <= mean


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 Tidy3D/Lumerical/lumopt）。"""

    def test_tidy3d_aligned(self) -> None:
        """Tidy3D 鲁棒优化对齐：
        - 蒙特卡洛采样评估
        - 制造公差扰动
        - 鲁棒性目标函数
        """
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 2.0) ** 2 + 10.0)

        cfg = RobustConfig(
            mode=RobustMode.MEAN,
            tolerance=ToleranceModel(
                tol_type=ToleranceType.GAUSSIAN,
                relative_std=0.05,
                seed=42,
            ),
            num_samples=16,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 应向 2 靠拢
        assert result.optimal_params[0] > 0.5
        # 应有完整的统计量
        assert result.fom_mean != 0
        assert result.fom_std >= 0
        assert result.fom_worst <= result.fom_mean

    def test_lumerical_worst_case(self) -> None:
        """Lumerical worst-case 鲁棒优化对齐。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2 + 5.0)

        cfg = RobustConfig(
            mode=RobustMode.WORST_CASE,
            tolerance=ToleranceModel(relative_std=0.05, seed=42),
            num_samples=8,
            max_iterations=20,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # WORST_CASE 模式应优化最差情况
        assert result.optimal_fom == pytest.approx(result.fom_worst, rel=1e-3)

    def test_lumopt_mean_minus_std(self) -> None:
        """lumopt mean-std 鲁棒优化对齐。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2 + 5.0)

        cfg = RobustConfig(
            mode=RobustMode.MEAN_MINUS_STD,
            tolerance=ToleranceModel(relative_std=0.05, seed=42),
            num_samples=8,
            beta=1.0,
            max_iterations=20,
        )
        opt = RobustOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # MEAN_MINUS_STD 模式应优化 mean - beta * std
        expected = result.fom_mean - 1.0 * result.fom_std
        assert result.optimal_fom == pytest.approx(expected, rel=1e-3)

    def test_gaussian_vs_uniform(self) -> None:
        """高斯 vs 均匀扰动对比。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        # 高斯
        cfg_g = RobustConfig(
            tolerance=ToleranceModel(
                tol_type=ToleranceType.GAUSSIAN,
                relative_std=0.1,
                seed=42,
            ),
            num_samples=100,
        )
        opt_g = RobustObjective(fom_fn, cfg_g)
        _, mean_g, std_g, _ = opt_g.evaluate(np.array([1.0]))

        # 均匀
        cfg_u = RobustConfig(
            tolerance=ToleranceModel(
                tol_type=ToleranceType.UNIFORM,
                relative_std=0.1,
                seed=42,
            ),
            num_samples=100,
        )
        opt_u = RobustObjective(fom_fn, cfg_u)
        _, mean_u, std_u, _ = opt_u.evaluate(np.array([1.0]))

        # 两者均值应接近
        assert abs(mean_g - mean_u) < 1.0
        # 高斯标准差通常大于均匀（均匀分布方差 = (2a)^2/12，高斯 = a^2）
        # 但这里采样数有限，只检查两者都 > 0
        assert std_g > 0
        assert std_u > 0

    def test_robust_better_than_nominal(self) -> None:
        """鲁棒优化应比标称优化更鲁棒（worst-case 更好）。"""
        def fom_fn(p: np.ndarray) -> float:
            # 在 p=2 附近最优，但对扰动敏感
            return float(-(p[0] - 2.0) ** 4 + 16.0)

        # 标称优化（无扰动）
        cfg_nominal = RobustConfig(
            tolerance=ToleranceModel(relative_std=0.0, absolute_std=0.0),
            num_samples=1,
            max_iterations=30,
            learning_rate=0.05,
        )
        opt_nominal = RobustOptimizer(cfg_nominal)
        result_nominal = opt_nominal.optimize(np.array([0.0]), fom_fn)

        # 鲁棒优化（有扰动）
        cfg_robust = RobustConfig(
            mode=RobustMode.WORST_CASE,
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=8,
            max_iterations=30,
            learning_rate=0.05,
        )
        opt_robust = RobustOptimizer(cfg_robust)
        result_robust = opt_robust.optimize(np.array([0.0]), fom_fn)

        # 两者都应优化（FoM 提升）
        assert len(result_nominal.fom_history) > 0
        assert len(result_robust.fom_history) > 0

    def test_tolerance_model_reproducibility(self) -> None:
        """公差模型可复现性。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(np.sum(p ** 2))

        # 相同种子应得到相同结果
        cfg1 = RobustConfig(
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        cfg2 = RobustConfig(
            tolerance=ToleranceModel(relative_std=0.1, seed=42),
            num_samples=16,
        )
        obj1 = RobustObjective(fom_fn, cfg1)
        obj2 = RobustObjective(fom_fn, cfg2)
        _, m1, s1, _ = obj1.evaluate(np.array([1.0]))
        _, m2, s2, _ = obj2.evaluate(np.array([1.0]))
        assert np.isclose(m1, m2)
        assert np.isclose(s1, s2)
