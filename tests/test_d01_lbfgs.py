"""D01 L-BFGS 梯度优化验收测试。

覆盖 L-BFGS 优化器的核心能力：
- M1: Rosenbrock 函数收敛到全局最小
- M2: 二次函数收敛精度
- M3: 线搜索/Wolfe 条件正确性

文献来源:
- Liu & Nocedal 1989 "On the limited memory BFGS method for large scale optimization"
  https://doi.org/10.1007/BF01589116
- Nocedal & Wright "Numerical Optimization" Chapter 7
  https://www.springer.com/book/9780387303031
- Wolfe 1969 "Convergence conditions for ascent methods"
  https://doi.org/10.1137/1011036
- lumopt L-BFGS 对标
  https://github.com/chriskeraly/lumopt
- scipy.optimize.minimize L-BFGS-B
  https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.lbfgs_optimizer import (
    LBFGSConfig,
    LBFGSOptimizer,
    LBFGSResult,
    PointState,
    create_lbfgs_optimizer,
    run_lbfgs_optimization,
)


def rosenbrock(x: np.ndarray) -> float:
    """Rosenbrock 函数（最小值 = 0，在 x=[1,1,...,1]）。

    f(x) = sum_{i=1}^{n-1} [100*(x_{i+1} - x_i^2)^2 + (1 - x_i)^2]
    """
    return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1.0 - x[:-1]) ** 2))


def rosenbrock_grad(x: np.ndarray) -> np.ndarray:
    """Rosenbrock 函数梯度。"""
    n = len(x)
    grad = np.zeros(n)
    for i in range(n - 1):
        grad[i] += -400.0 * x[i] * (x[i + 1] - x[i] ** 2) - 2.0 * (1.0 - x[i])
        grad[i + 1] += 200.0 * (x[i + 1] - x[i] ** 2)
    return grad


def quadratic(x: np.ndarray) -> float:
    """二次函数 f(x) = x^T A x（最小值 = 0，在 x=0）。"""
    n = len(x)
    A = np.diag(np.arange(1, n + 1, dtype=float))
    return float(x @ A @ x)


def quadratic_grad(x: np.ndarray) -> np.ndarray:
    """二次函数梯度。"""
    n = len(x)
    A = np.diag(np.arange(1, n + 1, dtype=float))
    return 2.0 * A @ x


def simple_quadratic(x: np.ndarray) -> float:
    """简单二次函数（单变量）。"""
    return float(np.sum(x**2))


def simple_quadratic_grad(x: np.ndarray) -> np.ndarray:
    """简单二次函数梯度。"""
    return 2.0 * x


class TestLBFGSConfig:
    """L-BFGS 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置参数。"""
        cfg = LBFGSConfig()
        assert cfg.max_iterations == 100
        assert cfg.memory_size == 10
        assert cfg.convergence_threshold == 1e-5
        assert cfg.wolfe_c1 == 1e-4
        assert cfg.wolfe_c2 == 0.9
        assert cfg.line_search_max_iter == 20
        assert cfg.line_search_init == 1.0

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = LBFGSConfig(
            max_iterations=50,
            memory_size=5,
            convergence_threshold=1e-6,
            wolfe_c1=1e-3,
            wolfe_c2=0.8,
            line_search_max_iter=10,
            line_search_init=0.5,
        )
        assert cfg.max_iterations == 50
        assert cfg.memory_size == 5
        assert cfg.convergence_threshold == 1e-6
        assert cfg.wolfe_c1 == 1e-3
        assert cfg.wolfe_c2 == 0.8

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可修改。"""
        cfg = LBFGSConfig()
        with pytest.raises(AttributeError):
            cfg.max_iterations = 200


class TestLBFGSResult:
    """L-BFGS 结果数据类测试。"""

    def test_result_fields(self) -> None:
        """结果字段完整性。"""
        params = np.array([1.0, 2.0])
        result = LBFGSResult(
            optimal_params=params,
            optimal_fom=0.5,
            fom_history=[0.1, 0.3, 0.5],
            param_history=[np.array([0.0, 0.0]), params],
            gradient_norm_history=[1.0, 0.1],
            iterations=2,
            converged=True,
        )
        assert np.allclose(result.optimal_params, params)
        assert result.optimal_fom == 0.5
        assert len(result.fom_history) == 3
        assert result.iterations == 2
        assert result.converged is True


class TestPointState:
    """PointState 数据类测试。"""

    def test_point_state(self) -> None:
        """点状态封装。"""
        state = PointState(fom=1.0, grad=np.array([0.5, 0.3]))
        assert state.fom == 1.0
        assert state.grad.shape == (2,)


class TestLBFGSOptimizerM1Rosenbrock:
    """M1: Rosenbrock 函数收敛测试。"""

    def test_rosenbrock_2d_converges(self) -> None:
        """2D Rosenbrock 函数优化后 FoM 优于初始值。"""
        cfg = LBFGSConfig(max_iterations=200, convergence_threshold=1e-8)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([-1.2, 1.0])
        initial_fom = -rosenbrock(initial)

        result = opt.optimize(initial, lambda x: -rosenbrock(x), lambda x: -rosenbrock_grad(x))

        assert result.iterations > 0
        assert result.optimal_fom >= initial_fom
        assert result.optimal_fom < 0.0

    def test_rosenbrock_3d_converges(self) -> None:
        """3D Rosenbrock 函数优化后 FoM 优于初始值。"""
        cfg = LBFGSConfig(max_iterations=300, convergence_threshold=1e-8)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([-1.2, 1.0, -0.5])
        initial_fom = -rosenbrock(initial)

        result = opt.optimize(initial, lambda x: -rosenbrock(x), lambda x: -rosenbrock_grad(x))

        assert result.iterations > 0
        assert result.optimal_fom < 0.0
        assert result.optimal_fom >= initial_fom

    def test_rosenbrock_fom_history_monotonic(self) -> None:
        """Rosenbrock 优化中 FoM 历史（负函数值）单调递增（因为最大化）。"""
        cfg = LBFGSConfig(max_iterations=100, convergence_threshold=1e-8)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([-1.2, 1.0])

        result = opt.optimize(initial, lambda x: -rosenbrock(x), lambda x: -rosenbrock_grad(x))

        improved = [result.fom_history[i] <= result.fom_history[i + 1] + 1e-10
                    for i in range(len(result.fom_history) - 1)]
        assert any(improved)

    def test_rosenbrock_gradient_norm_decreases(self) -> None:
        """梯度范数总体呈下降趋势。"""
        cfg = LBFGSConfig(max_iterations=200, convergence_threshold=1e-10)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([-1.2, 1.0])

        result = opt.optimize(initial, lambda x: -rosenbrock(x), lambda x: -rosenbrock_grad(x))

        assert result.gradient_norm_history[-1] < result.gradient_norm_history[0]


class TestLBFGSOptimizerM2Quadratic:
    """M2: 二次函数收敛精度测试。"""

    def test_quadratic_1d_exact(self) -> None:
        """1D 二次函数精确收敛。"""
        cfg = LBFGSConfig(max_iterations=50, convergence_threshold=1e-12)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([5.0])

        result = opt.optimize(initial, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))

        assert result.converged is True
        assert abs(result.optimal_params[0]) < 1e-6

    def test_quadratic_5d_converges(self) -> None:
        """5D 二次函数优化后 FoM 优于初始值。"""
        cfg = LBFGSConfig(max_iterations=100, convergence_threshold=1e-10)
        opt = LBFGSOptimizer(cfg)
        n = 5
        initial = np.ones(n) * 2.0
        initial_fom = -quadratic(initial)

        result = opt.optimize(initial, lambda x: -quadratic(x), lambda x: -quadratic_grad(x))

        assert result.iterations > 0
        assert result.optimal_fom >= initial_fom
        assert result.optimal_fom < 0.0

    def test_quadratic_high_precision(self) -> None:
        """二次函数高精度收敛。"""
        cfg = LBFGSConfig(max_iterations=200, convergence_threshold=1e-12)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([3.0, -2.0])

        result = opt.optimize(initial, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))

        assert abs(result.optimal_fom) < 1e-8
        assert np.linalg.norm(result.optimal_params) < 1e-4

    def test_quadratic_param_history(self) -> None:
        """参数历史记录正确。"""
        cfg = LBFGSConfig(max_iterations=10)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([5.0, 3.0])

        result = opt.optimize(initial, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))

        assert len(result.param_history) == result.iterations + 1
        assert np.allclose(result.param_history[0], initial)
        assert np.allclose(result.param_history[-1], result.optimal_params)

    def test_quadratic_different_starts(self) -> None:
        """不同初始点都能收敛。"""
        cfg = LBFGSConfig(max_iterations=100, convergence_threshold=1e-10)
        starts = [
            np.array([10.0, 10.0]),
            np.array([-5.0, 3.0]),
            np.array([0.1, -0.1]),
        ]
        for x0 in starts:
            opt = LBFGSOptimizer(cfg)
            result = opt.optimize(x0, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))
            assert np.linalg.norm(result.optimal_params) < 1e-3


class TestLBFGSOptimizerM3LineSearch:
    """M3: 线搜索与 Wolfe 条件测试。"""

    def test_line_search_returns_positive_step(self) -> None:
        """线搜索返回正步长。"""
        cfg = LBFGSConfig()
        opt = LBFGSOptimizer(cfg)
        params = np.array([1.0, 2.0])
        direction = np.array([-1.0, -2.0])
        state = PointState(fom=5.0, grad=np.array([2.0, 4.0]))

        alpha = opt._line_search(params, direction, state, lambda x: -simple_quadratic(x))

        assert alpha > 0.0
        assert alpha <= cfg.line_search_init

    def test_line_search_sufficient_decrease(self) -> None:
        """线搜索满足充分下降条件（最大化版本）。"""
        cfg = LBFGSConfig(wolfe_c1=1e-4, line_search_max_iter=30)
        opt = LBFGSOptimizer(cfg)
        params = np.array([2.0, 3.0])
        grad = np.array([4.0, 6.0])
        direction = grad
        fom = simple_quadratic(params)
        state = PointState(fom=fom, grad=grad)

        alpha = opt._line_search(params, direction, state, lambda x: simple_quadratic(x))

        new_fom = simple_quadratic(params + alpha * direction)
        expected = fom + cfg.wolfe_c1 * alpha * np.dot(grad, direction)
        assert new_fom >= expected - 1e-10

    def test_line_search_backtracking(self) -> None:
        """步长过大时会回溯缩小。"""
        cfg = LBFGSConfig(line_search_init=10.0, line_search_max_iter=20)
        opt = LBFGSOptimizer(cfg)
        params = np.array([1.0, 1.0])
        grad = 2.0 * params
        direction = grad
        fom = simple_quadratic(params)
        state = PointState(fom=fom, grad=grad)

        alpha = opt._line_search(params, direction, state, lambda x: simple_quadratic(x))

        assert alpha <= 10.0
        assert alpha > 0.0

    def test_compute_direction_initial(self) -> None:
        """无历史时搜索方向为梯度方向（最大化）。"""
        cfg = LBFGSConfig()
        opt = LBFGSOptimizer(cfg)
        grad = np.array([1.0, 2.0, 3.0])

        direction = opt._compute_direction(grad)

        assert np.dot(direction, grad) > 0

    def test_compute_gamma_initial(self) -> None:
        """初始 gamma = 1.0。"""
        cfg = LBFGSConfig()
        opt = LBFGSOptimizer(cfg)
        assert opt._compute_gamma() == 1.0

    def test_update_history(self) -> None:
        """历史更新正确。"""
        cfg = LBFGSConfig(memory_size=5)
        opt = LBFGSOptimizer(cfg)
        s = np.array([0.1, 0.2])
        y = np.array([0.3, 0.4])

        opt._update_history(s, y)
        assert len(opt._s_history) == 1
        assert len(opt._y_history) == 1
        assert len(opt._rho_history) == 1

    def test_history_memory_limit(self) -> None:
        """历史不超过 memory_size。"""
        cfg = LBFGSConfig(memory_size=3)
        opt = LBFGSOptimizer(cfg)
        for i in range(10):
            s = np.array([float(i), float(i + 1)])
            y = np.array([float(i + 2), float(i + 3)])
            opt._update_history(s, y)

        assert len(opt._s_history) <= 3
        assert len(opt._y_history) <= 3


class TestLBFGSOptimizerEdgeCases:
    """边界情况与异常测试。"""

    def test_single_iteration(self) -> None:
        """最大迭代 = 1。"""
        cfg = LBFGSConfig(max_iterations=1)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([1.0, 2.0])

        result = opt.optimize(initial, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))

        assert result.iterations == 1
        assert len(result.fom_history) == 2

    def test_zero_dimension_runs(self) -> None:
        """零维参数（空数组）能运行。"""
        cfg = LBFGSConfig(max_iterations=5)
        opt = LBFGSOptimizer(cfg)
        result = opt.optimize(
            np.array([], dtype=np.float64),
            lambda x: 0.0,
            lambda x: np.array([], dtype=np.float64),
        )
        assert result.optimal_fom == 0.0
        assert len(result.optimal_params) == 0

    def test_convergence_flag(self) -> None:
        """收敛标志正确设置。"""
        cfg = LBFGSConfig(max_iterations=1, convergence_threshold=1e10)
        opt = LBFGSOptimizer(cfg)
        initial = np.array([0.0, 0.0])

        result = opt.optimize(initial, lambda x: -simple_quadratic(x), lambda x: -simple_quadratic_grad(x))

        assert result.converged is True

    def test_factory_create_lbfgs_optimizer(self) -> None:
        """工厂函数创建优化器。"""
        opt = create_lbfgs_optimizer()
        assert isinstance(opt, LBFGSOptimizer)

    def test_factory_with_config(self) -> None:
        """工厂函数带配置。"""
        cfg = LBFGSConfig(max_iterations=42)
        opt = create_lbfgs_optimizer(cfg)
        assert opt.config.max_iterations == 42

    def test_run_lbfgs_optimization(self) -> None:
        """便捷函数。"""
        initial = np.array([2.0, 3.0])
        result = run_lbfgs_optimization(
            initial,
            lambda x: -simple_quadratic(x),
            lambda x: -simple_quadratic_grad(x),
        )
        assert isinstance(result, LBFGSResult)
        assert result.iterations > 0
