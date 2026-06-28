"""D04 伴随法/自动微分验收测试。

覆盖伴随优化与自动微分的核心能力：
- M1: 伴随梯度 vs 有限差分一致性
- M2: 参数化形状梯度
- M3: 拓扑优化密度更新

文献来源:
- Lalau-Keraly et al. 2013 "Adjoint shape optimization applied to electromagnetic design"
  https://doi.org/10.1364/OE.21.0021693
- Minkov et al. 2018 "Adjoint optimization of photonic devices with JAX autodiff"
  https://doi.org/10.1364/OE.26.030935
- Frostig et al. 2021 "Decomposing Reverse-Mode AD"
  https://arxiv.org/abs/2105.09469
- Osher & Sethian 1988 "Fronts propagating with curvature-dependent speed"
  https://doi.org/10.1016/0021-9991(88)90002-2
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
  https://doi.org/10.1016/j.cma.2010.07.013
"""

from __future__ import annotations

import numpy as np

from polaris.sim.adjoint_optimizer import (
    AdjointConfig,
    AdjointOptimizer,
    AnalyticalWaveguideCoupler,
    OptimizationBackend,
    OptimizationResult,
    ParameterizedGeometry,
    run_adjoint_optimization,
)
from polaris.sim.autodiff import (
    finite_difference_gradient,
)
from polaris.sim.topology_optimizer import (
    LevelSet,
    TopologyConfig,
    TopologyOptimizer,
    TopologyResult,
    run_topology_optimization,
)


def simple_quadratic(params: np.ndarray) -> float:
    """简单二次函数。"""
    return float(np.sum(params**2))


def sin_coupled(params: np.ndarray) -> float:
    """正弦耦合函数。"""
    return float(np.sin(params[0]) * np.cos(params[1]))


class TestOptimizationBackend:
    """OptimizationBackend 枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert OptimizationBackend.MEEP.value == "meep"
        assert OptimizationBackend.TIDY3D.value == "tidy3d"
        assert OptimizationBackend.ANALYTICAL.value == "analytical"

    def test_enum_from_string(self) -> None:
        """从字符串构造。"""
        assert OptimizationBackend("meep") == OptimizationBackend.MEEP
        assert OptimizationBackend("analytical") == OptimizationBackend.ANALYTICAL


class TestAdjointConfig:
    """AdjointConfig 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = AdjointConfig()
        assert cfg.max_iterations == 100
        assert cfg.learning_rate == 0.01
        assert cfg.convergence_threshold == 1e-6
        assert cfg.min_feature_size_um == 0.1
        assert cfg.symmetry == "none"
        assert cfg.backend == OptimizationBackend.ANALYTICAL
        assert cfg.optimizer == "adam"

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = AdjointConfig(
            max_iterations=50,
            learning_rate=0.05,
            convergence_threshold=1e-7,
            symmetry="x",
            optimizer="lbfgs",
        )
        assert cfg.max_iterations == 50
        assert cfg.learning_rate == 0.05
        assert cfg.symmetry == "x"
        assert cfg.optimizer == "lbfgs"


class TestParameterizedGeometry:
    """ParameterizedGeometry 参数化几何测试。"""

    def test_init_default_bounds(self) -> None:
        """初始化默认边界。"""
        params = np.array([0.5, 0.6, 0.7])
        geom = ParameterizedGeometry(params)
        assert len(geom.bounds) == 3
        assert geom.bounds[0] == (0.0, 1.0)

    def test_init_custom_bounds(self) -> None:
        """自定义边界。"""
        params = np.array([1.0, 2.0])
        bounds = [(0.0, 5.0), (-1.0, 1.0)]
        geom = ParameterizedGeometry(params, bounds=bounds)
        assert geom.bounds == bounds

    def test_get_params_copy(self) -> None:
        """get_params 返回副本。"""
        params = np.array([1.0, 2.0])
        geom = ParameterizedGeometry(params)
        p = geom.get_params()
        p[0] = 999.0
        assert geom.get_params()[0] == 1.0

    def test_set_params_bounds_clipping(self) -> None:
        """set_params 应用边界裁剪。"""
        params = np.array([0.5, 0.5])
        bounds = [(0.0, 1.0), (0.0, 1.0)]
        geom = ParameterizedGeometry(params, bounds=bounds)
        geom.set_params(np.array([-0.5, 1.5]))
        result = geom.get_params()
        assert result[0] == 0.0
        assert result[1] == 1.0

    def test_x_symmetry(self) -> None:
        """x 对称约束。"""
        params = np.array([1.0, 2.0, 3.0, 4.0])
        geom = ParameterizedGeometry(params, symmetry="x")
        geom.set_params(np.array([10.0, 20.0, 30.0, 40.0]))
        result = geom.get_params()
        assert result[0] == result[3]
        assert result[1] == result[2]

    def test_y_symmetry(self) -> None:
        """y 对称约束。"""
        params = np.array([1.0, 2.0, 3.0, 4.0])
        geom = ParameterizedGeometry(params, symmetry="y")
        geom.set_params(np.array([10.0, 20.0, 30.0, 40.0]))
        result = geom.get_params()
        assert result[0] == result[1]
        assert result[2] == result[3]

    def test_xy_symmetry(self) -> None:
        """xy 对称约束。"""
        params = np.array([1.0, 2.0, 3.0, 4.0])
        geom = ParameterizedGeometry(params, symmetry="xy")
        geom.set_params(np.array([10.0, 20.0, 30.0, 40.0]))
        result = geom.get_params()
        assert result[0] == result[1]
        assert result[0] == result[3]


class TestAdjointOptimizerM1GradientConsistency:
    """M1: 伴随梯度 vs 有限差分一致性测试。"""

    def test_analytical_coupler_gradient_fd_consistency(self) -> None:
        """解析波导耦合器梯度与有限差分一致。"""
        coupler = AnalyticalWaveguideCoupler()
        params = np.array([5.0, 0.5])

        grad_analytical = coupler.compute_gradient(params)
        grad_fd = finite_difference_gradient(
            lambda p: coupler.compute_figure_of_merit(p),
            params,
            eps=1e-6,
        )

        assert np.allclose(grad_analytical, grad_fd, rtol=1e-4, atol=1e-4)

    def test_analytical_coupler_fom_value(self) -> None:
        """FoM 值在 [0,1] 范围内。"""
        coupler = AnalyticalWaveguideCoupler()
        params = np.array([5.0, 0.5])
        fom = coupler.compute_figure_of_merit(params)
        assert 0.0 <= fom <= 1.0

    def test_finite_difference_quadratic(self) -> None:
        """有限差分梯度对二次函数的正确性。"""
        params = np.array([2.0, 3.0, -1.0])
        grad_fd = finite_difference_gradient(simple_quadratic, params, eps=1e-7)
        grad_analytical = 2.0 * params
        assert np.allclose(grad_fd, grad_analytical, rtol=1e-5, atol=1e-5)

    def test_finite_difference_1d(self) -> None:
        """1D 有限差分。"""
        def f(x):
            return float(x[0] ** 2)

        grad = finite_difference_gradient(f, np.array([3.0]), eps=1e-7)
        assert abs(grad[0] - 6.0) < 1e-5

    def test_finite_difference_5d(self) -> None:
        """5D 有限差分。"""
        def f(x):
            return float(np.sum(x**2))

        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        grad = finite_difference_gradient(f, x, eps=1e-7)
        expected = 2.0 * x
        assert np.allclose(grad, expected, rtol=1e-5)


class TestAdjointOptimizerM2ParameterizedShape:
    """M2: 参数化形状梯度测试。"""

    def test_adjoint_optimization_adam(self) -> None:
        """Adam 优化器的 adjoint 优化。"""
        coupler = AnalyticalWaveguideCoupler()
        initial = np.array([2.0, 0.3])
        bounds = [(0.0, 20.0), (0.0, 2.0)]
        geom = ParameterizedGeometry(initial, bounds=bounds)
        cfg = AdjointConfig(max_iterations=30, learning_rate=0.05, optimizer="adam")

        result = run_adjoint_optimization(geom, coupler, cfg)

        assert isinstance(result, OptimizationResult)
        assert result.iterations > 0
        assert len(result.fom_history) == result.iterations
        assert result.fom_history[-1] >= result.fom_history[0]

    def test_adjoint_optimization_gradient(self) -> None:
        """梯度上升优化。"""
        coupler = AnalyticalWaveguideCoupler()
        initial = np.array([2.0, 0.3])
        bounds = [(0.0, 20.0), (0.0, 2.0)]
        geom = ParameterizedGeometry(initial, bounds=bounds)
        cfg = AdjointConfig(max_iterations=50, learning_rate=0.01, optimizer="gradient")

        result = run_adjoint_optimization(geom, coupler, cfg)

        assert result.iterations > 0
        assert result.fom_history[-1] >= result.fom_history[0] - 1e-6

    def test_optimization_result_fields(self) -> None:
        """OptimizationResult 字段完整性。"""
        coupler = AnalyticalWaveguideCoupler()
        initial = np.array([2.0, 0.3])
        bounds = [(0.0, 20.0), (0.0, 2.0)]
        geom = ParameterizedGeometry(initial, bounds=bounds)
        cfg = AdjointConfig(max_iterations=10)

        result = run_adjoint_optimization(geom, coupler, cfg)

        assert hasattr(result, 'optimal_params')
        assert hasattr(result, 'optimal_fom')
        assert hasattr(result, 'fom_history')
        assert hasattr(result, 'param_history')
        assert hasattr(result, 'iterations')
        assert hasattr(result, 'converged')
        assert hasattr(result, 'backend_used')

    def test_param_history_length(self) -> None:
        """参数历史与 FoM 历史长度一致。"""
        coupler = AnalyticalWaveguideCoupler()
        initial = np.array([2.0, 0.3])
        bounds = [(0.0, 20.0), (0.0, 2.0)]
        geom = ParameterizedGeometry(initial, bounds=bounds)
        cfg = AdjointConfig(max_iterations=15)

        result = run_adjoint_optimization(geom, coupler, cfg)

        assert len(result.param_history) == result.iterations
        assert len(result.fom_history) == result.iterations


class TestTopologyOptimizerM3DensityUpdate:
    """M3: 拓扑优化密度更新测试。"""

    def test_level_set_init_circle(self) -> None:
        """LevelSet 圆形初始化。"""
        ls = LevelSet(grid_size=20, initial_shape="circle")
        assert ls.phi.shape == (20, 20)
        assert ls.get_material_fraction() > 0.1

    def test_level_set_init_rectangle(self) -> None:
        """矩形初始化。"""
        ls = LevelSet(grid_size=20, initial_shape="rectangle")
        assert ls.phi.shape == (20, 20)
        binary = ls.get_binary()
        assert binary.shape == (20, 20)
        assert np.all((binary == 0) | (binary == 1))

    def test_level_set_init_cross(self) -> None:
        """十字形初始化。"""
        ls = LevelSet(grid_size=20, initial_shape="cross")
        assert ls.get_material_fraction() > 0.0

    def test_level_set_binary(self) -> None:
        """二值化设计为 0/1。"""
        ls = LevelSet(grid_size=10)
        binary = ls.get_binary()
        assert np.all((binary == 0.0) | (binary == 1.0))

    def test_level_set_material_fraction(self) -> None:
        """材料占比在 [0,1]。"""
        ls = LevelSet(grid_size=20)
        frac = ls.get_material_fraction()
        assert 0.0 <= frac <= 1.0

    def test_level_set_evolve_changes_shape(self) -> None:
        """水平集演化改变形状。"""
        ls = LevelSet(grid_size=20, initial_shape="circle")
        phi_before = ls.phi.copy()
        velocity = np.ones((20, 20))
        ls.evolve(velocity, dt=0.01)
        assert not np.allclose(ls.phi, phi_before)

    def test_level_set_smooth(self) -> None:
        """水平集平滑。"""
        ls = LevelSet(grid_size=20)
        phi_before = ls.phi.copy()
        ls.smooth(sigma=1.0)
        assert ls.phi.shape == phi_before.shape

    def test_level_set_reinitialize(self) -> None:
        """重新初始化后符号不变。"""
        ls = LevelSet(grid_size=20, initial_shape="circle")
        original_sign = np.sign(ls.phi).copy()
        ls.phi *= 3.0
        ls.reinitialize()
        assert ls.phi.shape == (20, 20)
        assert np.all(np.sign(ls.phi) == original_sign)

    def test_topology_optimizer_basic(self) -> None:
        """拓扑优化基本运行。"""
        def fom_evaluator(binary):
            return float(np.mean(binary))

        def grad_evaluator(binary):
            return np.ones_like(binary)

        ls = LevelSet(grid_size=10, initial_shape="circle")
        cfg = TopologyConfig(max_iterations=5, learning_rate=0.01)
        opt = TopologyOptimizer(ls, fom_evaluator, grad_evaluator, cfg)

        result = opt.optimize()

        assert isinstance(result, TopologyResult)
        assert result.iterations > 0
        assert len(result.fom_history) == result.iterations
        assert result.level_set.shape == (10, 10)
        assert result.binary_design.shape == (10, 10)

    def test_topology_optimizer_convergence_flag(self) -> None:
        """收敛标志。"""
        def fom_evaluator(binary):
            return 0.5

        def grad_evaluator(binary):
            return np.zeros_like(binary)

        ls = LevelSet(grid_size=10)
        cfg = TopologyConfig(max_iterations=10, convergence_threshold=1e10)
        opt = TopologyOptimizer(ls, fom_evaluator, grad_evaluator, cfg)

        result = opt.optimize()
        assert result.converged is True

    def test_topology_config_default(self) -> None:
        """默认拓扑配置。"""
        cfg = TopologyConfig()
        assert cfg.grid_size == 50
        assert cfg.max_iterations == 50
        assert cfg.learning_rate == 0.1
        assert cfg.convergence_threshold == 1e-6

    def test_run_topology_optimization(self) -> None:
        """便捷函数。"""
        def fom_eval(b):
            return float(np.mean(b))

        def grad_eval(b):
            return np.ones_like(b)

        ls = LevelSet(grid_size=10)
        result = run_topology_optimization(
            ls, fom_eval, grad_eval,
            config=TopologyConfig(max_iterations=3),
        )
        assert isinstance(result, TopologyResult)

    def test_topology_result_binary_valid(self) -> None:
        """结果中二值化设计有效。"""
        def fom_eval(b):
            return float(np.sum(b))

        def grad_eval(b):
            return np.ones_like(b)

        ls = LevelSet(grid_size=10, initial_shape="circle")
        cfg = TopologyConfig(max_iterations=3)
        result = run_topology_optimization(ls, fom_eval, grad_eval, cfg)

        binary = result.binary_design
        assert np.all((binary == 0.0) | (binary == 1.0))


class TestAdjointOptimizerEdgeCases:
    """边界情况与异常测试。"""

    def test_convergence_stops_early(self) -> None:
        """收敛时提前停止。"""
        class FlatSimulator:
            def compute_figure_of_merit(self, params):
                return 0.5
            def compute_gradient(self, params):
                return np.zeros_like(params)

        geom = ParameterizedGeometry(np.array([0.5, 0.5]))
        cfg = AdjointConfig(max_iterations=100, convergence_threshold=1e10)
        opt = AdjointOptimizer(geom, FlatSimulator(), cfg)
        result = opt.optimize()

        assert result.iterations < 100
        assert result.converged is True

    def test_max_iterations_reached(self) -> None:
        """达到最大迭代次数。"""
        class AlwaysChangingSimulator:
            def __init__(self):
                self.counter = 0.0
            def compute_figure_of_merit(self, params):
                self.counter += 1.0
                return self.counter
            def compute_gradient(self, params):
                return np.ones_like(params)

        geom = ParameterizedGeometry(
            np.array([0.5, 0.5]),
            bounds=[(0.0, 10.0), (0.0, 10.0)],
        )
        cfg = AdjointConfig(max_iterations=10, convergence_threshold=0.0)
        opt = AdjointOptimizer(geom, AlwaysChangingSimulator(), cfg)
        result = opt.optimize()

        assert result.iterations == 10
        assert result.converged is False

    def test_run_adjoint_optimization_factory(self) -> None:
        """工厂函数。"""
        coupler = AnalyticalWaveguideCoupler()
        initial = np.array([2.0, 0.3])
        geom = ParameterizedGeometry(initial)
        result = run_adjoint_optimization(geom, coupler)
        assert isinstance(result, OptimizationResult)
