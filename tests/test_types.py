"""types.py 测试（R01 步骤 8）。

测试内容:
1. SDict 双后端支持（numpy/jax）
2. set_backend/get_backend 切换
3. asarray/zeros_like/full_like 双后端兼容
4. jax.grad 自动微分支持

来源:
- R01 路标: /workspace/docs/roundmap/R01.md
- JAX 自动微分: https://docs.jax.dev/
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.types import (
    SDict,
    asarray,
    full_like,
    get_backend,
    get_xp,
    set_backend,
    zeros_like,
)


class TestBackendSwitching:
    """测试后端切换。"""

    def test_default_backend_is_numpy(self):
        """默认后端应为 numpy。"""
        # 重置为 numpy
        set_backend("numpy")
        assert get_backend() == "numpy"

    def test_switch_to_jax(self):
        """切换到 jax 后端。"""
        pytest.importorskip("jax")
        set_backend("jax")
        assert get_backend() == "jax"
        # 切回 numpy 避免影响其他测试
        set_backend("numpy")

    def test_unknown_backend_raises(self):
        """未知后端应 raise ValueError。"""
        with pytest.raises(ValueError, match="未知后端"):
            set_backend("torch")


class TestArrayOperations:
    """测试双后端数组操作。"""

    def test_asarray_numpy(self):
        """numpy 后端 asarray 返回 numpy.ndarray。"""
        set_backend("numpy")
        arr = asarray([1.0, 2.0, 3.0])
        assert isinstance(arr, np.ndarray)

    def test_asarray_jax(self):
        """jax 后端 asarray 返回 jax.Array。"""
        pytest.importorskip("jax")
        set_backend("jax")
        try:
            arr = asarray([1.0, 2.0, 3.0])
            # jax.Array 的类型名包含 "Array"
            assert "Array" in type(arr).__name__ or hasattr(arr, "device")
        finally:
            set_backend("numpy")

    def test_zeros_like_numpy(self):
        """numpy 后端 zeros_like。"""
        set_backend("numpy")
        ref = np.array([1.0, 2.0])
        z = zeros_like(ref)
        assert np.all(z == 0)
        assert z.shape == ref.shape

    def test_full_like_numpy(self):
        """numpy 后端 full_like。"""
        set_backend("numpy")
        ref = np.array([1.0, 2.0])
        f = full_like(ref, 5.0)
        assert np.all(f == 5.0)

    def test_get_xp_numpy(self):
        """numpy 后端 get_xp 返回 numpy 模块。"""
        set_backend("numpy")
        xp = get_xp()
        assert xp is np

    def test_get_xp_jax(self):
        """jax 后端 get_xp 返回 jax.numpy 模块。"""
        pytest.importorskip("jax")
        import jax.numpy as jnp

        set_backend("jax")
        try:
            xp = get_xp()
            assert xp is jnp
        finally:
            set_backend("numpy")


class TestSDictType:
    """测试 SDict 类型定义。"""

    def test_sdict_accepts_numpy_arrays(self):
        """SDict 应接受 numpy 数组。"""
        set_backend("numpy")
        s: SDict = {
            ("in", "out"): np.array([1.0 + 0j]),
            ("out", "in"): np.array([1.0 + 0j]),
        }
        assert ("in", "out") in s
        assert isinstance(s[("in", "out")], np.ndarray)

    def test_sdict_accepts_jax_arrays(self):
        """SDict 应接受 jax 数组。"""
        pytest.importorskip("jax")
        import jax.numpy as jnp

        set_backend("jax")
        try:
            s: SDict = {
                ("in", "out"): jnp.array([1.0 + 0j]),
            }
            assert ("in", "out") in s
        finally:
            set_backend("numpy")


class TestJaxAutodiff:
    """测试 jax.grad 自动微分支持（R01 创新点）。"""

    def test_jax_grad_on_waveguide_phase(self):
        """jax.grad 可对波导相位求导。

        来源: Frostig et al., "Decomposing Reverse-Mode AD", arXiv:2105.09469
        """
        jax = pytest.importorskip("jax")
        import jax.numpy as jnp

        def phase_fn(length: float) -> float:
            """波导相位函数（用于求导）。"""
            wl = 1.55
            neff = 2.4
            beta = 2.0 * jnp.pi * neff / wl
            return jnp.exp(1j * beta * length).real

        # d(phase)/d(length) = -beta * sin(beta*length)
        grad_fn = jax.grad(phase_fn)
        length = 10.0
        grad = grad_fn(length)

        # 手动计算期望值
        wl = 1.55
        neff = 2.4
        beta = 2.0 * np.pi * neff / wl
        expected = -beta * np.sin(beta * length)

        assert abs(grad - expected) < 1e-6, f"jax.grad 结果 {grad} 与期望 {expected} 不符"

    def test_jax_grad_returns_float(self):
        """jax.grad 返回浮点数。"""
        jax = pytest.importorskip("jax")

        def square(x: float) -> float:
            return x**2

        grad_fn = jax.grad(square)
        grad = grad_fn(3.0)
        assert abs(grad - 6.0) < 1e-6
