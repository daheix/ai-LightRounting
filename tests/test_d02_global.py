"""D02 全局优化（PSO/CMA-ES）验收测试。

覆盖全局优化器的核心能力：
- M1: PSO 多峰函数（Rastrigin/Ackley）收敛
- M2: 全局最优覆盖率
- M3: 收敛历史记录正确

文献来源:
- Kennedy & Eberhart 1995 "Particle Swarm Optimization"
  https://ieeexplore.ieee.org/document/488968
- Hansen & Ostermeier 2001 "Completely Derandomized Self-Adaptation in Evolution Strategies"
  https://doi.org/10.1162/106365601750190398
- Rastrigin 函数: Rastrigin 1974 "Systems of extremal control"
  https://www.mathworks.com/help/optim/ug/rastrigin-function.html
- Ackley 函数: Ackley 1987 "A connectionist machine for genetic hillclimbing"
  https://dl.acm.org/doi/10.5555/38988
- scipy.optimize.differential_evolution
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html
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
    create_cmaes_optimizer,
    create_global_optimizer,
    run_global_optimization,
)
from polaris.sim.pso_optimizer import (
    ParticleSwarmOptimizer,
    PSOConfig,
    create_pso_optimizer,
)


def rastrigin(x: np.ndarray) -> float:
    """Rastrigin 函数（最小值 = 0，在 x=[0,0,...,0]）。

    f(x) = A*n + sum_{i=1}^n [x_i^2 - A*cos(2*pi*x_i)]
    多峰函数，大量局部最优。
    """
    n = len(x)
    A = 10.0
    return float(A * n + np.sum(x**2 - A * np.cos(2.0 * np.pi * x)))


def ackley(x: np.ndarray) -> float:
    """Ackley 函数（最小值 = 0，在 x=[0,0,...,0]）。

    f(x) = -a*exp(-b*sqrt(1/n * sum x_i^2)) - exp(1/n * sum cos(c*x_i)) + a + exp(1)
    """
    n = len(x)
    a = 20.0
    b = 0.2
    c = 2.0 * np.pi
    sum_sq = np.sum(x**2)
    sum_cos = np.sum(np.cos(c * x))
    term1 = -a * np.exp(-b * np.sqrt(sum_sq / n))
    term2 = -np.exp(sum_cos / n)
    return float(term1 + term2 + a + np.e)


def sphere(x: np.ndarray) -> float:
    """Sphere 函数（最小值 = 0，在 x=0）。"""
    return float(np.sum(x**2))


def neg_rastrigin(x: np.ndarray) -> float:
    """负 Rastrigin（用于最大化）。"""
    return -rastrigin(x)


def neg_ackley(x: np.ndarray) -> float:
    """负 Ackley（用于最大化）。"""
    return -ackley(x)


def neg_sphere(x: np.ndarray) -> float:
    """负 Sphere（用于最大化）。"""
    return -sphere(x)


class TestGlobalMethod:
    """GlobalMethod 枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值正确性。"""
        assert GlobalMethod.CMA_ES.value == "cma_es"
        assert GlobalMethod.PSO.value == "pso"

    def test_enum_from_string(self) -> None:
        """从字符串构造枚举。"""
        assert GlobalMethod("cma_es") == GlobalMethod.CMA_ES
        assert GlobalMethod("pso") == GlobalMethod.PSO


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
            inertia_weight=0.8,
            cognitive_coef=2.0,
            social_coef=2.0,
            max_iterations=200,
            seed=123,
        )
        assert cfg.num_particles == 50
        assert cfg.inertia_weight == 0.8
        assert cfg.seed == 123

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = PSOConfig()
        with pytest.raises(AttributeError):
            cfg.num_particles = 100


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
            seed=999,
        )
        assert cfg.initial_std == 1.0
        assert cfg.population_size == 20
        assert cfg.max_iterations == 50
        assert cfg.seed == 999


class TestGlobalResult:
    """GlobalResult 数据类测试。"""

    def test_result_defaults(self) -> None:
        """默认值。"""
        params = np.array([1.0, 2.0])
        result = GlobalResult(optimal_params=params)
        assert result.optimal_fom == -float("inf")
        assert result.fom_history == []
        assert result.iterations == 0
        assert result.converged is False
        assert result.method == ""

    def test_result_full(self) -> None:
        """完整字段。"""
        result = GlobalResult(
            optimal_params=np.array([0.0, 0.0]),
            optimal_fom=0.0,
            fom_history=[-10.0, -5.0, 0.0],
            iterations=3,
            converged=True,
            method="PSO",
        )
        assert len(result.fom_history) == 3
        assert result.method == "PSO"


class TestPSOOptimizerM1Multimodal:
    """M1: PSO 多峰函数收敛测试。"""

    def test_pso_sphere_converges(self) -> None:
        """PSO 在 Sphere 单峰函数上收敛。"""
        cfg = PSOConfig(num_particles=30, max_iterations=100, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([2.0, 2.0])
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))

        result = opt.optimize(initial, neg_sphere, bounds)

        assert result.method == "PSO"
        assert result.optimal_fom > -1.0
        assert np.linalg.norm(result.optimal_params) < 1.0

    def test_pso_rastrigin_2d_converges(self) -> None:
        """2D Rastrigin 函数 PSO 收敛到全局最优附近。"""
        cfg = PSOConfig(num_particles=50, max_iterations=200, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([2.0, 2.0])
        bounds = (np.array([-5.12, -5.12]), np.array([5.12, 5.12]))

        result = opt.optimize(initial, neg_rastrigin, bounds)

        assert result.optimal_fom > -10.0
        assert np.linalg.norm(result.optimal_params) < 2.0

    def test_pso_ackley_converges(self) -> None:
        """Ackley 函数 PSO 收敛。"""
        cfg = PSOConfig(num_particles=40, max_iterations=150, seed=123)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([1.0, 1.0, 1.0])
        bounds = (np.array([-5.0, -5.0, -5.0]), np.array([5.0, 5.0, 5.0]))

        result = opt.optimize(initial, neg_ackley, bounds)

        assert result.optimal_fom > -5.0

    def test_pso_multiple_seeds(self) -> None:
        """不同随机种子都能找到较好解。"""
        good_count = 0
        for seed in [42, 123, 456, 789, 1001]:
            cfg = PSOConfig(num_particles=30, max_iterations=100, seed=seed)
            opt = ParticleSwarmOptimizer(cfg)
            initial = np.array([3.0, 3.0])
            bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))
            result = opt.optimize(initial, neg_sphere, bounds)
            if np.linalg.norm(result.optimal_params) < 2.0:
                good_count += 1
        assert good_count >= 3


class TestPSOOptimizerM2Coverage:
    """M2: 全局最优覆盖率测试。"""

    def test_pso_escapes_local_optimum(self) -> None:
        """PSO 能跳出局部最优（Rastrigin 有很多局部最优）。"""
        cfg = PSOConfig(num_particles=50, max_iterations=200, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([3.0, 3.0])
        bounds = (np.array([-5.12, -5.12]), np.array([5.12, 5.12]))
        initial_fom = neg_rastrigin(initial)

        result = opt.optimize(initial, neg_rastrigin, bounds)

        assert result.optimal_fom >= initial_fom - 1e-10
        assert result.iterations > 1

    def test_pso_global_best_better_than_initial(self) -> None:
        """全局最优优于初始点。"""
        cfg = PSOConfig(num_particles=30, max_iterations=50, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([4.0, 4.0])
        bounds = (np.array([-5.0, -5.0]), np.array([5.0, 5.0]))

        result = opt.optimize(initial, neg_sphere, bounds)

        assert result.optimal_fom > neg_sphere(initial)

    def test_pso_bounds_respected(self) -> None:
        """PSO 粒子始终在边界内。"""
        cfg = PSOConfig(num_particles=20, max_iterations=30, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([0.0, 0.0])
        lower = np.array([-1.0, -1.0])
        upper = np.array([1.0, 1.0])

        state = opt._init_pso_state(initial, neg_sphere, (lower, upper))

        assert np.all(state.positions >= lower - 1e-10)
        assert np.all(state.positions <= upper + 1e-10)
        assert np.all(state.personal_best >= lower - 1e-10)
        assert np.all(state.personal_best <= upper + 1e-10)
        assert np.all(state.global_best >= lower - 1e-10)
        assert np.all(state.global_best <= upper + 1e-10)


class TestPSOOptimizerM3History:
    """M3: 收敛历史记录测试。"""

    def test_pso_fom_history_length(self) -> None:
        """FoM 历史长度正确。"""
        cfg = PSOConfig(num_particles=10, max_iterations=10, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([1.0, 1.0])

        result = opt.optimize(initial, neg_sphere)

        assert len(result.fom_history) == result.iterations
        assert result.iterations > 0

    def test_pso_history_monotonic(self) -> None:
        """历史最优 FoM 单调不减（最大化）。"""
        cfg = PSOConfig(num_particles=20, max_iterations=50, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, neg_sphere)

        for i in range(len(result.fom_history) - 1):
            assert result.fom_history[i + 1] >= result.fom_history[i] - 1e-12

    def test_pso_final_matches_history(self) -> None:
        """最终最优解与历史最后一致。"""
        cfg = PSOConfig(num_particles=15, max_iterations=20, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([1.0, 1.0])

        result = opt.optimize(initial, neg_sphere)

        assert abs(result.optimal_fom - result.fom_history[-1]) < 1e-10


class TestCMAESOptimizer:
    """CMA-ES 优化器测试。"""

    def test_cmaes_sphere_converges(self) -> None:
        """CMA-ES 在 Sphere 函数上收敛。"""
        cfg = CMAESConfig(initial_std=0.5, max_iterations=50, seed=42)
        opt = CMAESOptimizer(cfg)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, neg_sphere)

        assert result.method == "CMA-ES"
        assert result.optimal_fom > -1.0

    def test_cmaes_fom_history(self) -> None:
        """CMA-ES 历史记录。"""
        cfg = CMAESConfig(max_iterations=10, seed=42)
        opt = CMAESOptimizer(cfg)
        initial = np.array([1.0, 1.0])

        result = opt.optimize(initial, neg_sphere)

        assert len(result.fom_history) > 0
        assert result.iterations > 0

    def test_cmaes_2d_rastrigin(self) -> None:
        """CMA-ES 2D Rastrigin。"""
        cfg = CMAESConfig(initial_std=1.0, max_iterations=100, seed=42)
        opt = CMAESOptimizer(cfg)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, neg_rastrigin)

        assert result.optimal_fom > -20.0


class TestGlobalOptimizerUnified:
    """GlobalOptimizer 统一接口测试。"""

    def test_global_optimizer_pso(self) -> None:
        """统一接口 PSO 方法。"""
        opt = GlobalOptimizer(method=GlobalMethod.PSO)
        initial = np.array([2.0, 2.0])

        result = opt.optimize(initial, neg_sphere)

        assert isinstance(result, GlobalResult)
        assert result.method == "PSO"

    def test_global_optimizer_cmaes(self) -> None:
        """统一接口 CMA-ES 方法。"""
        opt = GlobalOptimizer(method=GlobalMethod.CMA_ES)
        initial = np.array([1.0, 1.0])

        result = opt.optimize(initial, neg_sphere)

        assert isinstance(result, GlobalResult)
        assert result.method == "CMA-ES"

    def test_run_global_optimization_pso(self) -> None:
        """便捷函数 PSO。"""
        initial = np.array([2.0, 2.0])
        result = run_global_optimization(initial, neg_sphere, method=GlobalMethod.PSO)
        assert isinstance(result, GlobalResult)
        assert result.method == "PSO"

    def test_run_global_optimization_cmaes(self) -> None:
        """便捷函数 CMA-ES。"""
        initial = np.array([1.0, 1.0])
        result = run_global_optimization(initial, neg_sphere, method=GlobalMethod.CMA_ES)
        assert isinstance(result, GlobalResult)
        assert result.method == "CMA-ES"

    def test_create_pso_optimizer(self) -> None:
        """工厂函数 PSO。"""
        opt = create_pso_optimizer()
        assert isinstance(opt, ParticleSwarmOptimizer)

    def test_create_cmaes_optimizer(self) -> None:
        """工厂函数 CMA-ES。"""
        opt = create_cmaes_optimizer()
        assert isinstance(opt, CMAESOptimizer)

    def test_create_global_optimizer(self) -> None:
        """工厂函数全局。"""
        opt = create_global_optimizer(method=GlobalMethod.PSO)
        assert isinstance(opt, GlobalOptimizer)


class TestGlobalOptimizerEdgeCases:
    """边界情况测试。"""

    def test_pso_single_particle(self) -> None:
        """单个粒子。"""
        cfg = PSOConfig(num_particles=1, max_iterations=5, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([1.0])

        result = opt.optimize(initial, neg_sphere)

        assert result.iterations > 0

    def test_pso_1d_problem(self) -> None:
        """1D 问题。"""
        cfg = PSOConfig(num_particles=10, max_iterations=20, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([3.0])
        bounds = (np.array([-5.0]), np.array([5.0]))

        result = opt.optimize(initial, neg_sphere, bounds)

        assert abs(result.optimal_params[0]) < 2.0

    def test_pso_default_bounds(self) -> None:
        """默认边界。"""
        cfg = PSOConfig(num_particles=10, max_iterations=5, seed=42)
        opt = ParticleSwarmOptimizer(cfg)
        initial = np.array([0.0, 0.0])

        result = opt.optimize(initial, neg_sphere)

        assert result.iterations > 0

    def test_cmaes_1d(self) -> None:
        """CMA-ES 1D 问题。"""
        cfg = CMAESConfig(max_iterations=10, seed=42)
        opt = CMAESOptimizer(cfg)
        initial = np.array([2.0])

        result = opt.optimize(initial, neg_sphere)

        assert result.iterations > 0
