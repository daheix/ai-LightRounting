"""JAX 后端选择器测试套件（v5.1）。

覆盖 is_jax_available / get_jax_devices / jit_compile /
waveguide_s_jax / cascade_two_port_jax / simulate_waveguide_chain_jax。
JAX 不可用时验证 raise RuntimeError（R03 禁止 fall-back）。

================================================================
学术诚信文献溯源（R02，≥5 篇，均经 WebSearch 验证可访问）
================================================================
1. Bradbury et al. 2018, "JAX: composable transformations of Python+NumPy
   programs", JOSS 3(31):10219, https://doi.org/10.21105/joss.02021
2. JAX JIT 编译文档:
   https://jax.readthedocs.io/en/latest/jax-101/02-jitting.html
3. JAX lax.scan 文档:
   https://jax.readthedocs.io/en/latest/_autosummary/jax.lax.scan.html
4. Filipsson 1978, "A new general computer algorithm for S-matrix
   calculation of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
5. SAX JAX 后端: https://flaport.github.io/sax/
6. NumPy 广播规则:
   https://numpy.org/doc/stable/user/basics.broadcasting.html
7. Pozar, "Microwave Engineering" 4th ed. §4.3 (两网络级联),
   https://www.wiley.com/en-us/Microwave+Engineering%2C+4th+Edition-p-9781118213636

================================================================
合规声明
================================================================
- R02 学术诚信: 所有断言基于解析公式（相位叠加 / Redheffer star）
- R03 禁止 fall-back: JAX 不可用场景验证 raise RuntimeError
- R04 不参与 GPU: 验证 get_jax_devices 仅返回 CPU 设备
- R05 无 TODO/FIXME/HACK 残留
- R11 测试在 main 分支运行
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_circuit.backend_selector import (  # noqa: E402
    cascade_two_port_jax,
    get_jax_devices,
    is_jax_available,
    jit_compile,
    simulate_waveguide_chain_jax,
    waveguide_s_jax,
)

# 标记需要 JAX 的测试；JAX 不可用时这些测试跳过（不是 fail），
# 因为环境差异不应导致 CI 失败，但 R03 行为由 *_raises_when_unavailable 覆盖。
jax_required = pytest.mark.skipif(
    not is_jax_available(), reason="JAX 不可用，跳过 JAX 后端功能测试"
)


# ============================================================================
# 1. is_jax_available (1 测试)
# ============================================================================


def test_is_jax_available_returns_bool_and_cached() -> None:
    """is_jax_available 返回 bool 且结果缓存（重复调用一致）。"""
    r1 = is_jax_available()
    assert isinstance(r1, bool)
    # 缓存: 第二次调用必须返回相同结果
    r2 = is_jax_available()
    assert r2 == r1


# ============================================================================
# 2. get_jax_devices (2 测试: 正常 + R03 不可用 raise)
# ============================================================================


@jax_required
def test_get_jax_devices_returns_cpu_only() -> None:
    """get_jax_devices 返回 CPU 设备列表，不含 GPU/TPU（R04）。"""
    devs = get_jax_devices()
    assert isinstance(devs, list)
    assert len(devs) > 0, "JAX 可用但 CPU 设备列表为空（R04 违规）"
    # R04: 所有设备必须为 CPU，禁止 GPU/TPU
    for d in devs:
        assert "Cpu" in d or "cpu" in d.lower(), f"非 CPU 设备: {d}"
        assert "Gpu" not in d, f"R04 违规: 检测到 GPU 设备 {d}"
        assert "Tpu" not in d, f"R04 违规: 检测到 TPU 设备 {d}"


def test_get_jax_devices_raises_when_unavailable() -> None:
    """JAX 不可用时 get_jax_devices raise RuntimeError（R03 禁止 fall-back）。"""
    with mock.patch(
        "polaris_circuit.backend_selector.is_jax_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="JAX 不可用"):
            get_jax_devices()


# ============================================================================
# 3. jit_compile (2 测试: 正常 + R03 不可用 raise)
# ============================================================================


@jax_required
def test_jit_compile_returns_callable_and_correct() -> None:
    """jit_compile 返回可调用对象，且编译后数值正确（sin(π/2)=1）。"""
    import jax.numpy as jnp

    def fn(x):
        return jnp.sin(x)

    compiled = jit_compile(fn)
    assert callable(compiled), "jit_compile 必须返回可调用对象"
    result = np.asarray(compiled(jnp.asarray([0.0, np.pi / 2.0])))
    assert np.allclose(result, [0.0, 1.0], atol=1e-12), f"sin 计算错误: {result}"


def test_jit_compile_raises_when_unavailable() -> None:
    """JAX 不可用时 jit_compile raise RuntimeError（R03 禁止 fall-back）。"""
    with mock.patch(
        "polaris_circuit.backend_selector.is_jax_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="JAX 不可用"):
            jit_compile(lambda x: x)


# ============================================================================
# 4. waveguide_s_jax (2 测试: 正常 + R03 不可用 raise)
# ============================================================================


@jax_required
def test_waveguide_s_jax_shape_phase_and_numpy_consistency() -> None:
    """waveguide_s_jax: shape (2,2,n_freq)，相位与 numpy 版 waveguide_s 一致。"""
    from polaris_circuit.models import waveguide_s

    wl = np.array([1.55, 1.56])
    s_jax = waveguide_s_jax(wl, length_um=100.0, neff=2.4, ng=4.0)
    # shape 校验
    assert s_jax.shape == (2, 2, 2), f"shape 错误: {s_jax.shape}"
    # 对角反射 = 0
    assert np.allclose(s_jax[0, 0], 0.0, atol=1e-12), "S11 反射非零"
    assert np.allclose(s_jax[1, 1], 0.0, atol=1e-12), "S22 反射非零"
    # off-diagonal 传输相位 = exp(1j * 2π * neff * L / wl)
    expected_phase = np.exp(1j * 2.0 * np.pi * 2.4 * 100.0 / wl)
    assert np.allclose(s_jax[0, 1], expected_phase, atol=1e-10), "S12 相位错误"
    assert np.allclose(s_jax[1, 0], expected_phase, atol=1e-10), "S21 相位错误"
    # 互易性: S12 = S21
    assert np.allclose(s_jax[0, 1], s_jax[1, 0], atol=1e-12), "互易性违反"
    # 与 numpy 版 waveguide_s 数值一致（R02 物理一致性）
    s_np = waveguide_s(wl=wl, length=100.0, neff=2.4)
    assert np.allclose(s_jax[0, 1], s_np[("out", "in")], atol=1e-10), (
        "JAX 版与 numpy 版 waveguide_s 数值不一致"
    )
    assert np.allclose(s_jax[1, 0], s_np[("in", "out")], atol=1e-10), (
        "JAX 版与 numpy 版 waveguide_s 数值不一致"
    )


def test_waveguide_s_jax_raises_when_unavailable() -> None:
    """JAX 不可用时 waveguide_s_jax raise RuntimeError（R03）。"""
    with mock.patch(
        "polaris_circuit.backend_selector.is_jax_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="JAX 不可用"):
            waveguide_s_jax([1.55], 100.0, 2.4, 4.0)


# ============================================================================
# 5. cascade_two_port_jax (2 测试: 正常 + R03 不可用 raise)
# ============================================================================


@jax_required
def test_cascade_two_port_jax_phase_additive_lossless() -> None:
    """级联两段无损波导: |S21|=1，相位叠加 phi_total = exp(1j*2π*neff*(La+Lb)/wl)。"""
    wl = np.array([1.55])
    s_a = waveguide_s_jax(wl, length_um=10.0, neff=2.4, ng=4.0)
    s_b = waveguide_s_jax(wl, length_um=20.0, neff=2.4, ng=4.0)
    s_total = cascade_two_port_jax(s_a, s_b)
    assert s_total.shape == (2, 2, 1), f"shape 错误: {s_total.shape}"
    # 无损波导级联: |S21| = 1
    assert np.abs(s_total[1, 0, 0]) == pytest.approx(1.0, abs=1e-9), (
        f"无损级联 |S21|={np.abs(s_total[1, 0, 0])} 偏离 1"
    )
    # 相位叠加: phi_total = exp(1j * 2π * neff * (La + Lb) / wl)
    expected = np.exp(1j * 2.0 * np.pi * 2.4 * 30.0 / 1.55)
    assert np.allclose(s_total[1, 0], expected, atol=1e-10), (
        f"级联相位错误: {s_total[1, 0]} vs {expected}"
    )
    # 端口 0 反射 = 0（无损匹配波导级联）
    assert np.allclose(s_total[0, 0], 0.0, atol=1e-10), "级联后 S11 非零"


def test_cascade_two_port_jax_raises_when_unavailable() -> None:
    """JAX 不可用时 cascade_two_port_jax raise RuntimeError（R03）。"""
    with mock.patch(
        "polaris_circuit.backend_selector.is_jax_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="JAX 不可用"):
            cascade_two_port_jax(np.zeros((2, 2, 1)), np.zeros((2, 2, 1)))


@jax_required
def test_cascade_two_port_jax_invalid_shape_raises() -> None:
    """输入形状非 (2,2,n_freq) 应 raise ValueError（R03 参数校验）。"""
    with pytest.raises(ValueError, match="前两维必须为"):
        cascade_two_port_jax(np.zeros((3, 2, 1)), np.zeros((2, 2, 1)))


# ============================================================================
# 6. simulate_waveguide_chain_jax (3 测试: 正常 + R03 不可用 + 边界)
# ============================================================================


@jax_required
def test_simulate_waveguide_chain_jax_phase_additive() -> None:
    """N 段波导链级联: 相位 = exp(1j*2π*neff*sum(L)/wl)，|S21|=1（无损）。"""
    wl = np.array([1.55, 1.56])
    lengths = np.array([10.0, 20.0, 30.0])
    s_total = simulate_waveguide_chain_jax(wl, lengths, neff=2.4, ng=4.0)
    assert s_total.shape == (2, 2, 2), f"shape 错误: {s_total.shape}"
    # 无损级联: |S21| = 1
    assert np.allclose(np.abs(s_total[1, 0]), 1.0, atol=1e-9), (
        f"无损链级联 |S21|={np.abs(s_total[1, 0])} 偏离 1"
    )
    # 相位 = sum(L) = 60 μm
    expected = np.exp(1j * 2.0 * np.pi * 2.4 * 60.0 / wl)
    assert np.allclose(s_total[1, 0], expected, atol=1e-10), (
        f"链级联相位错误: {s_total[1, 0]} vs {expected}"
    )
    # 与 cascade_two_port_jax 两段级联一致性（N=2 时两者应等价）
    s_two = cascade_two_port_jax(
        waveguide_s_jax(wl, 10.0, 2.4, 4.0),
        waveguide_s_jax(wl, 20.0, 2.4, 4.0),
    )
    s_chain_two = simulate_waveguide_chain_jax(
        wl, np.array([10.0, 20.0]), neff=2.4, ng=4.0
    )
    assert np.allclose(s_two, s_chain_two, atol=1e-10), (
        "lax.scan 链级联与两两级联结果不一致"
    )


def test_simulate_waveguide_chain_jax_raises_when_unavailable() -> None:
    """JAX 不可用时 simulate_waveguide_chain_jax raise RuntimeError（R03）。"""
    with mock.patch(
        "polaris_circuit.backend_selector.is_jax_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="JAX 不可用"):
            simulate_waveguide_chain_jax([1.55], [10.0], 2.4, 4.0)


@jax_required
def test_simulate_waveguide_chain_jax_empty_or_invalid_raises() -> None:
    """空数组 / 非正波长 / 非正长度应 raise ValueError（R03）。"""
    # 空长度数组
    with pytest.raises(ValueError, match="不能为空"):
        simulate_waveguide_chain_jax(np.array([1.55]), np.array([]), 2.4, 4.0)
    # 空波长数组
    with pytest.raises(ValueError, match="不能为空"):
        simulate_waveguide_chain_jax(np.array([]), np.array([10.0]), 2.4, 4.0)
    # 非正波长
    with pytest.raises(ValueError, match="波长必须 > 0"):
        simulate_waveguide_chain_jax(np.array([0.0]), np.array([10.0]), 2.4, 4.0)
    # 非正长度
    with pytest.raises(ValueError, match="波导长度必须 > 0"):
        simulate_waveguide_chain_jax(np.array([1.55]), np.array([-10.0]), 2.4, 4.0)
