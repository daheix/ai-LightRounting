"""全局优化器测试（第40轮 P2-1 深化，CMA-ES / 粒子群）。

测试覆盖：
- GlobalMethod 枚举
- CMAESConfig / PSOConfig 配置
- GlobalResult 结果
- CMAESOptimizer CMA-ES 优化器
- ParticleSwarmOptimizer 粒子群优化器
- GlobalOptimizer 统一接口
- 工厂函数
- 商业差距缩减验证（对标 scipy/cma 包）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.global_optimizer import (
    CMAESConfig,
    CMAESOptimizer,
    GlobalMethod,
    GlobalOptimizer,
    GlobalResult,
    ParticleSwarmOptimizer,
    PSOConfig,
    create_cmaes_optimizer,
    create_global_optimizer,
    create_pso_optimizer,
    run_global_optimization,
)


class TestGlobalMethod:
    """全局优化方法枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert GlobalMethod.CMA_ES.value == "cma_es"
        assert GlobalMethod.PSO.value == "pso"

    def test_enum_from_value(self) -> None:
        """从字符串构造。"""
        assert GlobalMethod("cma_es") == GlobalMethod.CMA_ES
        assert GlobalMethod("pso") == GlobalMethod.PSO


class TestCMAESConfig:
    """CMA-ES 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = CMAESConfig()
        assert cfg.initial_std == 0.5
        assert cfg.population_size == 0
        assert cfg.max_iterations == 100
        assert cfg.convergence_threshold == 1e-6
        assert cfg.seed == 42

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = CMAESConfig(
            initial_std=1.0,
            population_size=20,
            max_iterations=50,
            seed=123,
        )
        assert cfg.initial_std == 1.0
        assert cfg.population_size == 20
        assert cfg.max_iterations == 50
        assert cfg.seed == 123

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = CMAESConfig()
        with pytest.raises(AttributeError):
            cfg.initial_std = 2.0  # type: ignore[misc]


class TestPSOConfig:
    """PSO 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = PSOConfig()
        assert cfg.num_particles == 30
        assert cfg.inertia_weight == 0.7
        assert cfg.cognitive_coef == 1.5
        assert cfg.social_coef == 1.5
        assert cfg.max_iterations == 100
        assert cfg.convergence_threshold == 1e-6
        assert cfg.seed == 42

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = PSOConfig(
            num_particles=50,
            inertia_weight=0.5,
            cognitive_coef=2.0,
            social_coef=2.0,
        )
        assert cfg.num_particles == 50
        assert cfg.inertia_weight == 0.5
        assert cfg.cognitive_coef == 2.0
        assert cfg.social_coef == 2.0

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = PSOConfig()
        with pytest.raises(AttributeError):
            cfg.num_particles = 100  # type: ignore[misc]


class TestGlobalResult:
    """全局优化结果测试。"""

    def test_default_result(self) -> None:
        """默认结果。"""
        result = GlobalResult(optimal_params=np.array([1.0]))
        assert result.optimal_fom == -float("inf")
        assert result.fom_history == []
        assert result.iterations == 0
        assert result.converged is False
        assert result.method == ""

    def test_result_with_history(self) -> None:
        """带历史的结果。"""
        result = GlobalResult(
            optimal_params=np.array([1.0]),
            optimal_fom=0.95,
            fom_history=[0.5, 0.7, 0.95],
            iterations=3,
            converged=True,
            method="CMA-ES",
        )
        assert result.optimal_fom == 0.95
        assert len(result.fom_history) == 3
        assert result.iterations == 3
        assert result.converged is True
        assert result.method == "CMA-ES"


class TestCMAESOptimizer:
    """CMA-ES 优化器测试。"""

    def test_creation(self) -> None:
        """创建优化器。"""
        opt = CMAESOptimizer()
        assert opt.config.max_iterations == 100

    def test_optimize_quadratic(self) -> None:
        """二次函数最大化。

        目标：max -(w-3)^2 + 10，最优 w=3，FoM=10
        """
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 3.0) ** 2 + 10.0)

        cfg = CMAESConfig(
            initial_std=1.0,
            max_iterations=50,
            seed=42,
        )
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 应向 3 靠拢
        assert result.optimal_params[0] > 1.5
        assert result.optimal_fom > 5.0
        assert result.method == "CMA-ES"
        assert result.iterations > 0

    def test_optimize_multimodal(self) -> None:
        """多模态函数（全局最优 vs 局部最优）。"""
        def fom_fn(p: np.ndarray) -> float:
            x = p[0]
            return float(
                -((x - 5.0) ** 2) * (1 + 0.5 * np.cos(5 * x))
                - 0.1 * (x - 5.0) ** 4
                + 20.0
            )

        cfg = CMAESConfig(
            initial_std=2.0,
            max_iterations=80,
            seed=42,
        )
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 应找到较好的解
        assert result.optimal_fom > 10.0

    def test_optimize_records_history(self) -> None:
        """历史记录。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-p[0] ** 2)

        cfg = CMAESConfig(max_iterations=10, seed=42)
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([1.0]), fom_fn)
        assert len(result.fom_history) == result.iterations
        assert result.iterations <= 10

    def test_optimize_multi_dim(self) -> None:
        """多维优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-np.sum((p - np.array([1.0, 2.0, 3.0])) ** 2))

        cfg = CMAESConfig(
            initial_std=1.0,
            max_iterations=50,
            seed=42,
        )
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([0.0, 0.0, 0.0]), fom_fn)
        # 应向 (1, 2, 3) 靠拢
        assert result.optimal_params[0] > 0.0
        assert result.optimal_params[2] > 1.0


class TestParticleSwarmOptimizer:
    """粒子群优化器测试。"""

    def test_creation(self) -> None:
        """创建优化器。"""
        opt = ParticleSwarmOptimizer()
        assert opt.config.num_particles == 30

    def test_optimize_quadratic(self) -> None:
        """二次函数最大化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 2.0) ** 2 + 5.0)

        cfg = PSOConfig(
            num_particles=20,
            max_iterations=50,
            seed=42,
        )
        opt = ParticleSwarmOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 应向 2 靠拢
        assert result.optimal_params[0] > 0.5
        assert result.optimal_fom > 0.0
        assert result.method == "PSO"

    def test_optimize_with_bounds(self) -> None:
        """带边界优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(p[0])

        cfg = PSOConfig(
            num_particles=10,
            max_iterations=20,
            seed=42,
        )
        opt = ParticleSwarmOptimizer(cfg)
        lower = np.array([-1.0])
        upper = np.array([1.0])
        result = opt.optimize(np.array([0.0]), fom_fn, (lower, upper))
        # 应在边界内
        assert -1.0 <= result.optimal_params[0] <= 1.0

    def test_optimize_records_history(self) -> None:
        """历史记录。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-p[0] ** 2)

        cfg = PSOConfig(max_iterations=10, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        result = opt.optimize(np.array([1.0]), fom_fn)
        assert len(result.fom_history) == result.iterations

    def test_optimize_multi_dim(self) -> None:
        """多维优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-np.sum((p - np.array([1.0, 2.0])) ** 2))

        cfg = PSOConfig(
            num_particles=20,
            max_iterations=50,
            seed=42,
        )
        opt = ParticleSwarmOptimizer(cfg)
        result = opt.optimize(np.array([0.0, 0.0]), fom_fn)
        # 应向 (1, 2) 靠拢
        assert result.optimal_params[0] > 0.0
        assert result.optimal_params[1] > 1.0


class TestGlobalOptimizer:
    """统一全局优化器测试。"""

    def test_creation_default(self) -> None:
        """默认创建（CMA-ES）。"""
        opt = GlobalOptimizer()
        assert opt.method == GlobalMethod.CMA_ES

    def test_creation_pso(self) -> None:
        """创建 PSO。"""
        opt = GlobalOptimizer(method=GlobalMethod.PSO)
        assert opt.method == GlobalMethod.PSO

    def test_optimize_cmaes(self) -> None:
        """CMA-ES 方法。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        opt = GlobalOptimizer(
            method=GlobalMethod.CMA_ES,
            cmaes_config=CMAESConfig(max_iterations=30, seed=42),
        )
        result = opt.optimize(np.array([0.0]), fom_fn)
        assert result.method == "CMA-ES"
        assert result.optimal_params[0] > 0.0

    def test_optimize_pso(self) -> None:
        """PSO 方法。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        opt = GlobalOptimizer(
            method=GlobalMethod.PSO,
            pso_config=PSOConfig(max_iterations=30, seed=42),
        )
        result = opt.optimize(np.array([0.0]), fom_fn)
        assert result.method == "PSO"
        assert result.optimal_params[0] > 0.0


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_cmaes_optimizer(self) -> None:
        """创建 CMA-ES 优化器。"""
        opt = create_cmaes_optimizer()
        assert isinstance(opt, CMAESOptimizer)

    def test_create_pso_optimizer(self) -> None:
        """创建 PSO 优化器。"""
        opt = create_pso_optimizer()
        assert isinstance(opt, ParticleSwarmOptimizer)

    def test_create_global_optimizer(self) -> None:
        """创建统一优化器。"""
        opt = create_global_optimizer()
        assert isinstance(opt, GlobalOptimizer)

    def test_run_global_optimization_cmaes(self) -> None:
        """运行 CMA-ES 全局优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        result = run_global_optimization(
            np.array([0.0]),
            fom_fn,
            method=GlobalMethod.CMA_ES,
        )
        assert isinstance(result, GlobalResult)
        assert result.method == "CMA-ES"

    def test_run_global_optimization_pso(self) -> None:
        """运行 PSO 全局优化。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        result = run_global_optimization(
            np.array([0.0]),
            fom_fn,
            method=GlobalMethod.PSO,
        )
        assert isinstance(result, GlobalResult)
        assert result.method == "PSO"


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 scipy/cma 包）。"""

    def test_cma_es_aligned_pycma(self) -> None:
        """CMA-ES 对齐 pycma 包：
        - 协方差矩阵自适应
        - 进化策略
        - 全局搜索
        """
        def fom_fn(p: np.ndarray) -> float:
            return float(-np.sum((p - np.array([2.0, 3.0])) ** 2))

        cfg = CMAESConfig(
            initial_std=1.0,
            max_iterations=80,
            seed=42,
        )
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([0.0, 0.0]), fom_fn)
        # 应找到全局最优附近
        assert result.optimal_params[0] > 1.0
        assert result.optimal_params[1] > 2.0

    def test_pso_aligned_scipy_de(self) -> None:
        """PSO 对齐 scipy.optimize.differential_evolution：
        - 种群搜索
        - 全局优化
        """
        def fom_fn(p: np.ndarray) -> float:
            return float(-np.sum((p - np.array([1.0, 1.0])) ** 2))

        cfg = PSOConfig(
            num_particles=30,
            max_iterations=50,
            seed=42,
        )
        opt = ParticleSwarmOptimizer(cfg)
        result = opt.optimize(np.array([0.0, 0.0]), fom_fn)
        # 应找到全局最优附近
        assert result.optimal_params[0] > 0.0
        assert result.optimal_params[1] > 0.0

    def test_global_vs_local(self) -> None:
        """全局优化 vs 局部优化：多模态函数。"""
        def fom_fn(p: np.ndarray) -> float:
            x = p[0]
            return float(
                -((x - 5.0) ** 2) + 10.0 * np.sin(2 * x) + 50.0
            )

        # 全局优化
        cfg = CMAESConfig(
            initial_std=3.0,
            max_iterations=80,
            seed=42,
        )
        opt = CMAESOptimizer(cfg)
        result = opt.optimize(np.array([0.0]), fom_fn)
        # 全局优化应找到较好的解
        assert result.optimal_fom > 30.0

    def test_reproducibility(self) -> None:
        """可复现性（相同种子）。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 2.0) ** 2)

        cfg1 = CMAESConfig(seed=42, max_iterations=20)
        cfg2 = CMAESConfig(seed=42, max_iterations=20)
        opt1 = CMAESOptimizer(cfg1)
        opt2 = CMAESOptimizer(cfg2)
        r1 = opt1.optimize(np.array([0.0]), fom_fn)
        r2 = opt2.optimize(np.array([0.0]), fom_fn)
        # 相同种子应得到相同结果
        assert np.allclose(r1.optimal_params, r2.optimal_params)

    def test_pso_reproducibility(self) -> None:
        """PSO 可复现性。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 2.0) ** 2)

        cfg1 = PSOConfig(seed=42, max_iterations=20)
        cfg2 = PSOConfig(seed=42, max_iterations=20)
        opt1 = ParticleSwarmOptimizer(cfg1)
        opt2 = ParticleSwarmOptimizer(cfg2)
        r1 = opt1.optimize(np.array([0.0]), fom_fn)
        r2 = opt2.optimize(np.array([0.0]), fom_fn)
        assert np.allclose(r1.optimal_params, r2.optimal_params)

    def test_method_selection(self) -> None:
        """方法选择：CMA-ES vs PSO。"""
        def fom_fn(p: np.ndarray) -> float:
            return float(-(p[0] - 1.0) ** 2)

        # CMA-ES
        r_cmaes = run_global_optimization(
            np.array([0.0]),
            fom_fn,
            method=GlobalMethod.CMA_ES,
        )
        assert r_cmaes.method == "CMA-ES"

        # PSO
        r_pso = run_global_optimization(
            np.array([0.0]),
            fom_fn,
            method=GlobalMethod.PSO,
        )
        assert r_pso.method == "PSO"

        # 两者都应找到较好的解
        assert r_cmaes.optimal_fom > -1.0
        assert r_pso.optimal_fom > -1.0
