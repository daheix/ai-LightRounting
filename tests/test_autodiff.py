"""自动微分测试（R05）。

测试梯度计算、VJP/JVP、有限差分验证、波导优化。

来源:
- Frostig et al., "Decomposing Reverse-Mode AD", LAFI 2021
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.autodiff import (
    compute_gradient,
    compute_jvp,
    compute_vjp,
    finite_difference_gradient,
    optimize_waveguide_lengths,
    verify_gradient,
    waveguide_transmission_loss,
)
from polaris.sim.jax_backend import is_jax_available


@pytest.fixture(autouse=True)
def _setup_float64():
    """每个测试前启用 float64。"""
    if is_jax_available():
        from polaris.sim.jax_backend import enable_float64

        enable_float64()
    yield


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestComputeGradient:
    """梯度计算测试。"""

    def test_gradient_simple(self):
        """测试简单函数梯度。"""
        import jax.numpy as jnp

        def func(x):
            return jnp.sum(x ** 2)

        x = jnp.array([1.0, 2.0, 3.0])
        grad = compute_gradient(func, x)
        # df/dx = 2x
        assert np.allclose(np.asarray(grad), [2.0, 4.0, 6.0])

    def test_gradient_polynomial(self):
        """测试多项式梯度。"""
        import jax.numpy as jnp

        def func(x):
            return jnp.sum(x ** 3 + 2 * x)

        x = jnp.array([1.0, 2.0])
        grad = compute_gradient(func, x)
        # df/dx = 3x² + 2
        assert np.allclose(np.asarray(grad), [5.0, 14.0])


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestVJP:
    """VJP 测试。"""

    def test_vjp_simple(self):
        """测试简单 VJP。"""
        import jax.numpy as jnp

        def func(x):
            return x ** 2

        x = jnp.array([1.0, 2.0, 3.0])
        cotangent = jnp.array([1.0, 1.0, 1.0])
        vjp = compute_vjp(func, x, cotangent)
        # VJP = J^T · cotangent = 2x · 1 = 2x
        assert np.allclose(np.asarray(vjp), [2.0, 4.0, 6.0])


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestJVP:
    """JVP 测试。"""

    def test_jvp_simple(self):
        """测试简单 JVP。"""
        import jax.numpy as jnp

        def func(x):
            return x ** 2

        x = jnp.array([1.0, 2.0, 3.0])
        tangent = jnp.array([1.0, 1.0, 1.0])
        output, jvp = compute_jvp(func, x, tangent)
        # output = x²
        assert np.allclose(np.asarray(output), [1.0, 4.0, 9.0])
        # JVP = J · tangent = 2x · 1 = 2x
        assert np.allclose(np.asarray(jvp), [2.0, 4.0, 6.0])


class TestFiniteDifference:
    """有限差分测试。"""

    def test_finite_difference_polynomial(self):
        """测试多项式有限差分。"""
        def func(x):
            return np.sum(x ** 2)

        x = np.array([1.0, 2.0, 3.0])
        grad = finite_difference_gradient(func, x)
        # df/dx = 2x
        assert np.allclose(grad, [2.0, 4.0, 6.0], atol=1e-4)

    def test_finite_difference_trig(self):
        """测试三角函数有限差分。"""
        def func(x):
            return np.sum(np.sin(x))

        x = np.array([0.5, 1.0, 1.5])
        grad = finite_difference_gradient(func, x)
        # df/dx = cos(x)
        expected = np.cos(x)
        assert np.allclose(grad, expected, atol=1e-4)


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestVerifyGradient:
    """梯度验证测试。"""

    def test_verify_gradient_polynomial(self):
        """验证多项式梯度一致性。"""
        import jax.numpy as jnp

        def func(x):
            return jnp.sum(x ** 2)

        x = jnp.array([1.0, 2.0, 3.0])
        is_consistent, max_error = verify_gradient(func, x, atol=1e-3)
        assert is_consistent, f"梯度不一致，max_error = {max_error}"
        assert max_error < 1e-3


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestWaveguideTransmissionLoss:
    """波导传输损耗函数测试。"""

    def test_transmission_loss_basic(self):
        """测试波导传输损耗基本功能。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        params = jnp.array([10.0, 2.4])  # [length, neff]
        power = waveguide_transmission_loss(params, wl)
        # 无损波导，功率 = 1
        assert np.isclose(float(power), 1.0, atol=1e-6)

    def test_transmission_loss_gradient(self):
        """测试波导传输损耗梯度。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        params = jnp.array([10.0, 2.4])
        is_consistent, max_error = verify_gradient(
            lambda p: waveguide_transmission_loss(p, wl),
            params,
            atol=1e-3,
        )
        assert is_consistent, f"梯度不一致，max_error = {max_error}"


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestOptimizeWaveguideLengths:
    """波导长度优化测试。"""

    def test_optimize_runs(self):
        """测试优化可运行。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        initial_lengths = jnp.array([10.0])
        neff = 2.4
        target = 1.0  # 目标功率 = 1（无损）

        optimized, loss_history = optimize_waveguide_lengths(
            target, initial_lengths, neff, wl,
            learning_rate=0.01, n_steps=10,
        )
        assert len(loss_history) == 10
        # 损失应有限
        assert all(np.isfinite(loss_history))


class TestR05AutodiffIntegration:
    """R05 自动微分集成测试。"""

    def test_no_fallback_in_autodiff(self):
        """验证 autodiff.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/autodiff.py") as f:
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
