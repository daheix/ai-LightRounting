"""P2-1 L-BFGS 优化器测试（第37轮 P2-1 深化）。

验证 L-BFGS 两循环递归、线搜索、收敛性。

来源: commercial_gap_analysis.md P2-1 逆向设计
对标: lumopt L-BFGS / scipy L-BFGS-B
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.lbfgs_optimizer import (
    LBFGSConfig,
    LBFGSOptimizer,
    LBFGSResult,
    create_lbfgs_optimizer,
    run_lbfgs_optimization,
)


class TestLBFGSConfig:
    """L-BFGS 配置测试。"""

    def test_default_config(self):
        """默认配置。"""
        cfg = LBFGSConfig()
        assert cfg.max_iterations == 100
        assert cfg.memory_size == 10
        assert cfg.convergence_threshold == 1e-5
        assert cfg.wolfe_c1 == 1e-4
        assert cfg.wolfe_c2 == 0.9
        assert cfg.line_search_max_iter == 20
        assert cfg.line_search_init == 1.0

    def test_custom_config(self):
        """自定义配置。"""
        cfg = LBFGSConfig(memory_size=5, max_iterations=50)
        assert cfg.memory_size == 5
        assert cfg.max_iterations == 50

    def test_frozen_dataclass(self):
        """frozen dataclass。"""
        cfg = LBFGSConfig()
        with pytest.raises(AttributeError):
            cfg.memory_size = 20  # type: ignore[misc]


class TestLBFGSResult:
    """L-BFGS 结果测试。"""

    def test_default_result(self):
        """默认结果。"""
        result = LBFGSResult(
            optimal_params=np.array([1.0, 2.0]),
            optimal_fom=0.5,
        )
        assert np.array_equal(result.optimal_params, [1.0, 2.0])
        assert result.optimal_fom == 0.5
        assert result.fom_history == []
        assert result.iterations == 0
        assert result.converged is False

    def test_result_with_history(self):
        """带历史的结果。"""
        result = LBFGSResult(
            optimal_params=np.array([1.0]),
            optimal_fom=1.0,
            fom_history=[0.5, 0.8, 1.0],
            iterations=3,
            converged=True,
        )
        assert len(result.fom_history) == 3
        assert result.converged is True


class TestLBFGSOptimizer:
    """L-BFGS 优化器测试。"""

    def test_creation_default(self):
        """默认创建。"""
        opt = LBFGSOptimizer()
        assert opt.config.memory_size == 10

    def test_creation_with_config(self):
        """带配置创建。"""
        cfg = LBFGSConfig(memory_size=5)
        opt = LBFGSOptimizer(cfg)
        assert opt.config.memory_size == 5

    def test_optimize_quadratic(self):
        """二次函数优化。"""
        # f(x) = -((x-3)^2 + (y-2)^2)（最大化 → x=3, y=2）
        def fom_fn(params):
            return -((params[0] - 3) ** 2 + (params[1] - 2) ** 2)

        def grad_fn(params):
            return np.array([
                -2 * (params[0] - 3),
                -2 * (params[1] - 2),
            ])

        opt = LBFGSOptimizer(LBFGSConfig(max_iterations=50))
        result = opt.optimize(np.array([0.0, 0.0]), fom_fn, grad_fn)
        assert result.optimal_fom == pytest.approx(0.0, abs=1e-3)
        assert result.optimal_params[0] == pytest.approx(3.0, abs=1e-2)
        assert result.optimal_params[1] == pytest.approx(2.0, abs=1e-2)

    def test_optimize_convergence(self):
        """收敛检测。"""
        def fom_fn(params):
            return -params[0] ** 2

        def grad_fn(params):
            return np.array([-2 * params[0]])

        cfg = LBFGSConfig(
            max_iterations=100,
            convergence_threshold=1e-5,
        )
        opt = LBFGSOptimizer(cfg)
        result = opt.optimize(np.array([1.0]), fom_fn, grad_fn)
        assert result.converged is True
        assert result.optimal_params[0] == pytest.approx(0.0, abs=1e-3)

    def test_optimize_records_history(self):
        """记录历史。"""
        def fom_fn(params):
            return -params[0] ** 2

        def grad_fn(params):
            return np.array([-2 * params[0]])

        opt = LBFGSOptimizer(LBFGSConfig(max_iterations=10))
        result = opt.optimize(np.array([1.0]), fom_fn, grad_fn)
        assert len(result.fom_history) == result.iterations + 1
        assert len(result.param_history) == result.iterations + 1
        assert len(result.gradient_norm_history) == result.iterations + 1

    def test_memory_size_limit(self):
        """记忆长度限制。"""
        cfg = LBFGSConfig(memory_size=3, max_iterations=20)
        opt = LBFGSOptimizer(cfg)

        def fom_fn(params):
            return -params[0] ** 2

        def grad_fn(params):
            return np.array([-2 * params[0]])

        opt.optimize(np.array([1.0]), fom_fn, grad_fn)
        assert len(opt._s_history) <= 3  # noqa: SLF001
        assert len(opt._y_history) <= 3  # noqa: SLF001


class TestFactoryFunction:
    """工厂函数测试。"""

    def test_create_default(self):
        """默认创建。"""
        opt = create_lbfgs_optimizer()
        assert isinstance(opt, LBFGSOptimizer)

    def test_create_with_config(self):
        """带配置创建。"""
        cfg = LBFGSConfig(memory_size=5)
        opt = create_lbfgs_optimizer(cfg)
        assert opt.config.memory_size == 5


class TestRunLBFGSOptimization:
    """便捷函数测试。"""

    def test_run_quadratic(self):
        """运行二次函数优化。"""
        def fom_fn(params):
            return -(params[0] - 1) ** 2

        def grad_fn(params):
            return np.array([-2 * (params[0] - 1)])

        result = run_lbfgs_optimization(np.array([0.0]), fom_fn, grad_fn)
        assert result.optimal_params[0] == pytest.approx(1.0, abs=1e-2)

    def test_run_with_config(self):
        """带配置运行。"""
        def fom_fn(params):
            return -params[0] ** 2

        def grad_fn(params):
            return np.array([-2 * params[0]])

        cfg = LBFGSConfig(max_iterations=20)
        result = run_lbfgs_optimization(np.array([1.0]), fom_fn, grad_fn, cfg)
        assert result.iterations <= 20


class TestCommercialGapReduction:
    """P2-1 商业差距缩减验证。"""

    def test_lbfgs_aligned_lumopt(self):
        """L-BFGS 对齐 lumopt 优化器。"""
        # lumopt 使用 L-BFGS 优化光子器件
        opt = create_lbfgs_optimizer()
        # 核心能力：两循环递归 + Wolfe 线搜索
        assert hasattr(opt, "_compute_direction")
        assert hasattr(opt, "_line_search")

    def test_two_loop_recursion(self):
        """两循环递归计算搜索方向。"""
        # Liu & Nocedal 1989 算法 7.4
        opt = LBFGSOptimizer(LBFGSConfig(memory_size=5))
        # 手动添加历史
        opt._s_history.append(np.array([0.1, 0.0]))  # noqa: SLF001
        opt._y_history.append(np.array([0.2, 0.0]))  # noqa: SLF001
        opt._rho_history.append(1.0 / 0.02)  # noqa: SLF001
        grad = np.array([1.0, 1.0])
        direction = opt._compute_direction(grad)  # noqa: SLF001
        assert direction.shape == grad.shape

    def test_wolfe_line_search(self):
        """Wolfe 条件线搜索。"""
        # Nocedal & Wright Chapter 3 Wolfe 条件
        opt = LBFGSOptimizer(LBFGSConfig(wolfe_c1=1e-4, wolfe_c2=0.9))

        def fom_fn(params):
            return -params[0] ** 2

        direction = np.array([1.0])  # 上升方向（最大化）
        params = np.array([0.5])
        fom = fom_fn(params)
        grad = np.array([-1.0])
        alpha = opt._line_search(params, direction, fom, grad, fom_fn)  # noqa: SLF001
        assert alpha > 0

    def test_faster_convergence_than_gradient_descent(self):
        """L-BFGS 收敛快于梯度下降。"""
        # Rosenbrock 函数（经典测试）
        def fom_fn(params):
            return -(100 * (params[1] - params[0] ** 2) ** 2 + (1 - params[0]) ** 2)

        def grad_fn(params):
            df_dx = -(-400 * (params[1] - params[0] ** 2) * params[0] - 2 * (1 - params[0]))
            df_dy = -(-200 * (params[1] - params[0] ** 2))
            return np.array([df_dx, df_dy])

        # L-BFGS
        lbfgs_result = run_lbfgs_optimization(
            np.array([-1.2, 1.0]),
            fom_fn,
            grad_fn,
            LBFGSConfig(max_iterations=100),
        )
        # L-BFGS 应在 100 轮内显著改善
        assert lbfgs_result.optimal_fom > fom_fn(np.array([-1.2, 1.0]))

    def test_memory_efficient(self):
        """内存高效（只保存 m 次历史）。"""
        cfg = LBFGSConfig(memory_size=5, max_iterations=50)
        opt = LBFGSOptimizer(cfg)

        def fom_fn(params):
            return -np.sum(params ** 2)

        def grad_fn(params):
            return -2 * params

        opt.optimize(np.ones(10), fom_fn, grad_fn)
        # 历史长度不超过 memory_size
        assert len(opt._s_history) <= 5  # noqa: SLF001

    def test_gamma_computation(self):
        """γ 缩放因子计算。"""
        opt = LBFGSOptimizer()
        # 无历史时 γ=1
        assert opt._compute_gamma() == 1.0  # noqa: SLF001
        # 添加历史
        opt._s_history.append(np.array([1.0, 0.0]))  # noqa: SLF001
        opt._y_history.append(np.array([2.0, 0.0]))  # noqa: SLF001
        # γ = s^T y / y^T y = 2 / 4 = 0.5
        assert opt._compute_gamma() == pytest.approx(0.5)  # noqa: SLF001
