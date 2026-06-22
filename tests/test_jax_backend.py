"""JAX 后端测试（R05）。

测试 JIT 编译、双后端切换、波导链仿真。

来源:
- JAX 文档: https://docs.jax.dev/
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.jax_backend import (
    JAXConfig,
    benchmark_jit_vs_numpy,
    cascade_two_port_jax,
    enable_float64,
    get_jax_devices,
    is_jax_available,
    jit_compile,
    set_jax_backend,
    simulate_waveguide_chain_jax,
    waveguide_s_jax,
)


@pytest.fixture(autouse=True)
def _setup_float64():
    """每个测试前启用 float64。"""
    if is_jax_available():
        enable_float64()
    yield


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestJAXAvailability:
    """JAX 可用性测试。"""

    def test_jax_available(self):
        """测试 JAX 可用。"""
        assert is_jax_available()

    def test_get_jax_devices(self):
        """测试获取设备列表。"""
        devices = get_jax_devices()
        assert len(devices) > 0
        assert any("cpu" in d.lower() for d in devices)


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestWaveguideSJAX:
    """JAX 波导模型测试。"""

    def test_waveguide_s_jax_basic(self):
        """测试 JAX 波导模型基本功能。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        sdict = waveguide_s_jax(wl, length=10.0, neff=2.4)
        assert ("in", "in") in sdict
        assert ("out", "in") in sdict
        # S11 = 0（无反射）
        assert np.isclose(complex(sdict[("in", "in")][0]), 0.0)
        # |S21| = 1（无损）
        assert np.isclose(float(np.abs(sdict[("out", "in")][0])), 1.0)

    def test_waveguide_s_jax_multi_wavelength(self):
        """测试多波长波导模型。"""
        import jax.numpy as jnp

        wl = jnp.linspace(1.5, 1.6, 10)
        sdict = waveguide_s_jax(wl, length=10.0, neff=2.4)
        s21 = sdict[("out", "in")]
        assert s21.shape == (10,)
        # 所有波长 |S21| = 1
        assert np.allclose(np.abs(np.asarray(s21)), 1.0)


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestSimulateWaveguideChainJAX:
    """JAX 波导链仿真测试。"""

    def test_chain_basic(self):
        """测试波导链基本仿真。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        lengths = jnp.array([10.0, 20.0, 30.0])
        s21 = simulate_waveguide_chain_jax(wl, lengths, neff=2.4)
        # |S21| = 1（无损）
        assert np.isclose(float(np.abs(s21[0])), 1.0)

    def test_chain_vs_numpy(self):
        """测试 JAX 波导链与 numpy 一致性。"""
        import jax.numpy as jnp

        wl_np = np.array([1.55, 1.56, 1.57])
        lengths_np = np.array([10.0, 20.0, 30.0])

        # numpy 实现
        total_phase_np = np.zeros_like(wl_np, dtype=complex)
        for length in lengths_np:
            beta = 2 * np.pi * 2.4 / wl_np
            total_phase_np += beta * length
        s21_np = np.exp(1j * total_phase_np)

        # JAX 实现
        wl_jax = jnp.asarray(wl_np)
        lengths_jax = jnp.asarray(lengths_np)
        s21_jax = simulate_waveguide_chain_jax(wl_jax, lengths_jax, neff=2.4)

        # 对比（误差 < 1e-10）
        assert np.allclose(np.asarray(s21_jax), s21_np, atol=1e-10)


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestJITCompile:
    """JIT 编译测试。"""

    def test_jit_compile_basic(self):
        """测试 JIT 编译基本功能。"""
        import jax.numpy as jnp

        def func(x):
            return x ** 2 + 1

        jit_func = jit_compile(func)
        x = jnp.array([1.0, 2.0, 3.0])
        result = jit_func(x)
        assert np.allclose(np.asarray(result), [2.0, 5.0, 10.0])

    def test_jit_waveguide_chain(self):
        """测试 JIT 编译波导链仿真。"""
        import jax.numpy as jnp

        wl = jnp.array([1.55])
        lengths = jnp.array([10.0, 20.0])
        jit_simulate = jit_compile(simulate_waveguide_chain_jax)
        s21 = jit_simulate(wl, lengths, 2.4)
        assert np.isclose(float(np.abs(s21[0])), 1.0)


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestBenchmarkJIT:
    """JIT 性能基准测试。"""

    def test_benchmark_runs(self):
        """测试基准测试可运行。"""
        wl = np.linspace(1.5, 1.6, 100)
        result = benchmark_jit_vs_numpy(wl, n_wg=10)
        assert "numpy_time" in result
        assert "jit_time" in result
        assert "speedup" in result
        assert result["numpy_time"] > 0
        assert result["jit_time"] > 0


@pytest.mark.skipif(not is_jax_available(), reason="JAX 不可用")
class TestSetJAXBackend:
    """JAX 后端设置测试。"""

    def test_set_cpu_backend(self):
        """测试设置 CPU 后端。"""
        # 应该不 raise
        set_jax_backend("cpu")

    def test_set_gpu_backend_no_gpu_raises(self):
        """测试无 GPU 时设置 GPU 后端 raise。"""
        devices = get_jax_devices()
        has_gpu = any("gpu" in d.lower() for d in devices)
        if not has_gpu:
            with pytest.raises(RuntimeError, match="GPU 不可用"):
                set_jax_backend("gpu")

    def test_set_unknown_backend_raises(self):
        """测试未知平台 raise。"""
        with pytest.raises(ValueError, match="未知平台"):
            set_jax_backend("tpu")


class TestJAXConfig:
    """JAX 配置测试。"""

    def test_config_defaults(self):
        """测试默认配置。"""
        config = JAXConfig()
        assert config.enable_jit is True
        assert config.enable_gpu is False
        assert config.precision == "float64"
        assert config.platform == "cpu"


class TestR05JAXIntegration:
    """R05 JAX 集成测试。"""

    def test_no_fallback_in_jax_backend(self):
        """验证 jax_backend.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/jax_backend.py") as f:
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
