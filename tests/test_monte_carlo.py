"""蒙特卡洛分析测试（R05）。

测试 vmap 并行蒙特卡洛仿真、敏感度分析、良率分析。

来源:
- JAX vmap 文档: https://docs.jax.dev/en/latest/_autosummary/jax.vmap.html
- 蒙特卡洛方法: Metropolis & Ulam 1949
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.jax_backend import is_jax_available
from polaris.sim.monte_carlo import (
    MonteCarloResult,
    monte_carlo_simulate,
    sensitivity_analysis,
    waveguide_transmission_mc,
    yield_analysis,
)


@pytest.fixture(autouse=True)
def _setup_float64():
    """每个测试前启用 float64。"""
    if is_jax_available():
        from polaris.sim.jax_backend import enable_float64

        enable_float64()
    yield


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestMonteCarloSimulate:
    """蒙特卡洛仿真测试。"""

    def test_monte_carlo_basic(self):
        """测试蒙特卡洛仿真基本功能。"""
        import jax.numpy as jnp

        def func(params):
            """简单函数: sum(params^2)。"""
            return jnp.sum(params ** 2)

        base_params = np.array([1.0, 2.0, 3.0])
        result = monte_carlo_simulate(func, base_params, n_samples=100, sigma=0.01, seed=42)

        assert isinstance(result, MonteCarloResult)
        assert result.samples.shape == (100,)  # 标量输出

    def test_monte_carlo_statistics(self):
        """测试蒙特卡洛统计量正确性。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        base_params = np.array([10.0, 20.0])
        result = monte_carlo_simulate(func, base_params, n_samples=1000, sigma=0.01, seed=42)

        # 均值应接近 30.0（10+20），允许 5% 波动
        assert abs(float(result.mean) - 30.0) < 1.5
        # 标准差应为正
        assert float(result.std) > 0
        # min <= mean <= max
        assert float(result.min) <= float(result.mean) <= float(result.max)
        # 百分位
        assert float(result.percentile_05) <= float(result.percentile_95)

    def test_monte_carlo_reproducible(self):
        """测试相同 seed 结果一致。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params ** 2)

        base_params = np.array([1.0, 2.0])
        result1 = monte_carlo_simulate(func, base_params, n_samples=50, sigma=0.01, seed=42)
        result2 = monte_carlo_simulate(func, base_params, n_samples=50, sigma=0.01, seed=42)

        assert np.allclose(result1.samples, result2.samples)
        assert np.isclose(float(result1.mean), float(result2.mean))

    def test_monte_carlo_n_samples(self):
        """测试不同采样数。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        base_params = np.array([1.0])
        for n in [10, 50, 100]:
            result = monte_carlo_simulate(func, base_params, n_samples=n, sigma=0.01, seed=42)
            assert result.samples.shape == (n,)

    def test_monte_carlo_result_fields(self):
        """测试 MonteCarloResult 所有字段存在。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        base_params = np.array([1.0])
        result = monte_carlo_simulate(func, base_params, n_samples=10, sigma=0.01, seed=42)

        # 所有字段必须存在且为 numpy 数组
        assert hasattr(result, "samples")
        assert hasattr(result, "mean")
        assert hasattr(result, "std")
        assert hasattr(result, "min")
        assert hasattr(result, "max")
        assert hasattr(result, "percentile_95")
        assert hasattr(result, "percentile_05")
        assert isinstance(result.samples, np.ndarray)


class TestSensitivityAnalysis:
    """敏感度分析测试。"""

    def test_sensitivity_basic(self):
        """测试基本敏感度计算。"""
        def func(params):
            """f(x, y) = x + 2y，df/dx = 1，df/dy = 2。"""
            return float(params[0] + 2 * params[1])

        base_params = np.array([1.0, 2.0])
        sens = sensitivity_analysis(func, base_params, delta=0.01)

        assert len(sens) == 2
        # 归一化敏感度: S_i = (df/dp_i) * (p_i / f)
        # f = 1 + 4 = 5
        # S_x = 1 * (1/5) = 0.2
        # S_y = 2 * (2/5) = 0.8
        assert abs(sens["param_0"] - 0.2) < 0.01
        assert abs(sens["param_1"] - 0.8) < 0.01

    def test_sensitivity_param_names(self):
        """测试参数名映射。"""
        def func(params):
            return float(params[0] ** 2)

        base_params = np.array([2.0])
        sens = sensitivity_analysis(
            func, base_params, param_names=["length"], delta=0.01
        )

        assert "length" in sens
        # f = 4, df/dx = 2x = 4, S = 4 * (2/4) = 2
        assert abs(sens["length"] - 2.0) < 0.05


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestYieldAnalysis:
    """良率分析测试。"""

    def test_yield_basic(self):
        """测试基本良率计算。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        def spec_func(output):
            """规格: 输出在 [0.9, 1.1] 范围内。"""
            return float(0.9 < output < 1.1)

        base_params = np.array([1.0])
        result = yield_analysis(
            func, base_params, spec_func, n_samples=100, sigma=0.01, seed=42
        )

        assert "yield" in result
        assert "n_pass" in result
        assert "n_total" in result
        assert result["n_total"] == 100
        assert 0.0 <= result["yield"] <= 1.0
        assert result["n_pass"] <= result["n_total"]

    def test_yield_all_pass(self):
        """测试全部通过场景（sigma 极小）。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        def spec_func(output):
            return float(0.5 < output < 1.5)

        base_params = np.array([1.0])
        result = yield_analysis(
            func, base_params, spec_func, n_samples=50, sigma=0.001, seed=42
        )

        # sigma 极小，所有样本都应通过
        assert result["yield"] == 1.0
        assert result["n_pass"] == 50

    def test_yield_all_fail(self):
        """测试全部失败场景（规格严格）。"""
        import jax.numpy as jnp

        def func(params):
            return jnp.sum(params)

        def spec_func(output):
            """不可能满足的规格。"""
            return float(output > 1000.0)

        base_params = np.array([1.0])
        result = yield_analysis(
            func, base_params, spec_func, n_samples=50, sigma=0.01, seed=42
        )

        assert result["yield"] == 0.0
        assert result["n_pass"] == 0


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestWaveguideTransmissionMC:
    """波导传输蒙特卡洛测试。"""

    def test_waveguide_mc_basic(self):
        """测试波导传输蒙特卡洛基本功能。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        params = jnp.array([10.0, 2.4])  # [length, neff]
        power = waveguide_transmission_mc(params, wl)

        # 无损波导，功率 = 1
        assert np.isclose(float(power), 1.0, atol=1e-6)

    def test_waveguide_mc_with_monte_carlo(self):
        """测试波导传输蒙特卡洛仿真。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        base_params = np.array([10.0, 2.4])

        def func(params):
            return waveguide_transmission_mc(params, wl)

        result = monte_carlo_simulate(func, base_params, n_samples=50, sigma=0.01, seed=42)

        # 无损波导，所有样本功率应接近 1.0
        assert abs(float(result.mean) - 1.0) < 0.01
        assert float(result.std) < 0.01


class TestR05MonteCarloIntegration:
    """R05 蒙特卡洛集成测试。"""

    def test_no_fallback_in_monte_carlo(self):
        """验证 monte_carlo.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/monte_carlo.py") as f:
            source = f.read()
        tree = ast.parse(source)

        fallback_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for child in ast.walk(node):
                    if isinstance(child, ast.Pass):
                        fallback_count += 1

        assert fallback_count == 0, (
            f"发现 {fallback_count} 个 except:pass fall-back，违反规则 14.1"
        )

    def test_monte_carlo_result_is_dataclass(self):
        """验证 MonteCarloResult 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(MonteCarloResult)
