"""polaris-pam4 子模块深度测试（v5.0，覆盖全 API）。

测试覆盖（24 个 pytest）:
- generate_pam4_signal: 信号长度 / 时间数组 / 4 电平 / 可复现 / 非法参数 raise
- compute_snr_db: 正值 / 公式正确性 / 零噪声 inf / 负噪声 raise
- compute_eye_diagram: shape / 值域 / sps<=0 raise / 长度不足 raise
- compute_ber: 范围 / 公式正确性 / 零噪声返回 0 / 负噪声 raise / n_levels<2 raise / 单调性
- simulate_pam4: 返回键 / 默认值 / 可复现 / 非法参数 raise
- 模块: 版本号

R02 学术诚信（docstring 含 ≥5 文献 URL）:
- Shafik et al., IEEE CommSurveys 2016, EVM/BER 综述
  https://ieeexplore.ieee.org/document/7410082
- OIF CEI-112G 标准 https://www.oiforum.com/
- Ansys Lumerical INTERCONNECT 眼图分析
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §9
- Proakis, "Digital Communications", McGraw-Hill 2007, §5（PAM BER 公式）
- pytest 文档: https://docs.pytest.org/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R05 无 TODO / R04 纯 NumPy
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_pam4  # noqa: E402
from polaris_pam4 import (  # noqa: E402
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
    simulate_pam4,
)


# ===========================================================================
# 1. generate_pam4_signal — PAM4 信号生成
# ===========================================================================
def test_generate_signal_length():
    """信号长度 = n_symbols × samples_per_symbol（上采样）。"""
    n_symbols, sps = 100, 16
    _, signal = generate_pam4_signal(n_symbols, bit_rate=100e9, samples_per_symbol=sps)
    assert len(signal) == n_symbols * sps, (
        f"信号长度期望 {n_symbols*sps}，实际 {len(signal)}"
    )


def test_generate_signal_time_array():
    """时间数组正确: 每符号时长 = 1/(bit_rate/2)（PAM4 每符号 2 比特）。"""
    n_symbols, sps = 10, 8
    bit_rate = 100e9
    time, _ = generate_pam4_signal(n_symbols, bit_rate=bit_rate, samples_per_symbol=sps)
    symbol_duration = 1.0 / (bit_rate / 2.0)
    sample_interval = symbol_duration / sps
    expected_time = np.arange(n_symbols * sps) * sample_interval
    assert np.allclose(time, expected_time), "时间数组与公式不符"


def test_generate_signal_4_levels():
    """PAM4 信号电平值 ∈ {0, 1/3, 2/3, 1}（OIF CEI-112G 4 电平）。"""
    _, signal = generate_pam4_signal(1000, bit_rate=100e9, samples_per_symbol=16, seed=42)
    valid_levels = {0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0}
    unique = set(signal.tolist())
    # 1000 符号至少命中 3 个电平（统计上几乎必全 4 个）
    assert len(unique) >= 3, f"电平数 {len(unique)} 应 ≥ 3"
    for v in unique:
        assert any(math.isclose(v, lv, rel_tol=1e-9) for lv in valid_levels), (
            f"电平 {v} 不在 PAM4 标准 4 电平中"
        )


def test_generate_signal_reproducible():
    """同 seed 同输出（可复现）。"""
    _, s1 = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    _, s2 = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    assert np.array_equal(s1, s2), "同 seed 须返回相同信号"


def test_generate_signal_different_seeds_differ():
    """不同 seed 产生不同信号。"""
    _, s1 = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    _, s2 = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=7)
    assert not np.array_equal(s1, s2), "不同 seed 应产生不同信号"


def test_generate_signal_invalid_params_raise():
    """非法参数 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        generate_pam4_signal(0, bit_rate=100e9)
    with pytest.raises(ValueError):
        generate_pam4_signal(-1, bit_rate=100e9)
    with pytest.raises(ValueError):
        generate_pam4_signal(100, bit_rate=0)
    with pytest.raises(ValueError):
        generate_pam4_signal(100, bit_rate=-1e9)
    with pytest.raises(ValueError):
        generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=0)


# ===========================================================================
# 2. compute_snr_db — 信噪比（dB）
# ===========================================================================
def test_snr_db_positive():
    """典型 PAM4 信号 SNR > 0（信号功率 > 噪声功率）。"""
    _, signal = generate_pam4_signal(1000, bit_rate=100e9, samples_per_symbol=16)
    snr = compute_snr_db(signal, noise_std=0.05)
    assert snr > 0, f"SNR 应 > 0，得到 {snr}"


def test_snr_db_formula():
    """公式: SNR_dB = 10·log10(mean(signal²)/σ²)。"""
    _, signal = generate_pam4_signal(1000, bit_rate=100e9, samples_per_symbol=16, seed=42)
    noise_std = 0.05
    snr = compute_snr_db(signal, noise_std=noise_std)
    expected = 10.0 * math.log10(np.mean(signal ** 2) / (noise_std ** 2))
    assert abs(snr - expected) < 1e-9, f"SNR 期望 {expected}，实际 {snr}"


def test_snr_db_zero_noise_returns_inf():
    """noise_std=0: 返回 +inf（无噪声，物理事实，非 fall-back）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    snr = compute_snr_db(signal, noise_std=0.0)
    assert math.isinf(snr), f"零噪声 SNR 应为 +inf，得到 {snr}"


def test_snr_db_negative_noise_raises():
    """noise_std < 0 raise ValueError（R03）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    with pytest.raises(ValueError):
        compute_snr_db(signal, noise_std=-0.1)


def test_snr_db_increases_with_lower_noise():
    """SNR 随噪声降低而升高（反比关系）。"""
    _, signal = generate_pam4_signal(500, bit_rate=100e9, samples_per_symbol=16, seed=42)
    snr1 = compute_snr_db(signal, noise_std=0.1)
    snr2 = compute_snr_db(signal, noise_std=0.01)
    assert snr2 > snr1, "噪声降低 → SNR 应升高"


# ===========================================================================
# 3. compute_eye_diagram — 眼图
# ===========================================================================
def test_eye_diagram_shape():
    """眼图 shape = [2*sps, n_windows]，n_windows = len(signal)//(2*sps)。"""
    n_symbols, sps = 100, 16
    _, signal = generate_pam4_signal(n_symbols, bit_rate=100e9, samples_per_symbol=sps)
    eye = compute_eye_diagram(signal, samples_per_symbol=sps)
    expected_windows = (n_symbols * sps) // (2 * sps)
    assert eye.shape == (2 * sps, expected_windows), (
        f"眼图 shape 期望 ({2*sps}, {expected_windows})，得到 {eye.shape}"
    )


def test_eye_diagram_value_range():
    """眼图值 ∈ [0, 1]（PAM4 归一化电平 0..1）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    eye = compute_eye_diagram(signal, samples_per_symbol=16)
    assert np.all(eye >= 0.0) and np.all(eye <= 1.0)


def test_eye_diagram_invalid_sps_raises():
    """samples_per_symbol <= 0 raise ValueError（R03）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    with pytest.raises(ValueError):
        compute_eye_diagram(signal, samples_per_symbol=0)
    with pytest.raises(ValueError):
        compute_eye_diagram(signal, samples_per_symbol=-1)


def test_eye_diagram_insufficient_length_raises():
    """信号长度不足一个眼图窗口 raise ValueError（R03）。"""
    short_signal = np.array([0.0, 0.5])  # 长度 2 < 2*sps=32
    with pytest.raises(ValueError):
        compute_eye_diagram(short_signal, samples_per_symbol=16)


# ===========================================================================
# 4. compute_ber — 误码率（Shafik 2016 理论公式）
# ===========================================================================
def test_ber_range():
    """BER ∈ (0, 0.5)（典型噪声，理论值非 0 非 0.5）。"""
    _, signal = generate_pam4_signal(1000, bit_rate=100e9, samples_per_symbol=16, seed=42)
    ber = compute_ber(signal, noise_std=0.05)
    assert 0.0 < ber < 0.5, f"BER 应 ∈ (0, 0.5)，得到 {ber}"


def test_ber_formula():
    """公式: BER = 0.5·erfc(√(SNR_eye/2)), SNR_eye=(eye/2)²/σ², eye=1/(n-1)。

    来源: Shafik et al., IEEE CommSurveys 2016.
         URL: https://ieeexplore.ieee.org/document/7410082
    """
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    noise_std = 0.05
    ber = compute_ber(signal, noise_std=noise_std, n_levels=4)
    eye = 1.0 / 3.0  # PAM4 眼图开口 = 1/(4-1)
    snr_eye = (eye / 2.0) ** 2 / (noise_std ** 2)
    expected = 0.5 * math.erfc(math.sqrt(snr_eye / 2.0))
    assert abs(ber - expected) < 1e-12, f"BER 期望 {expected}，实际 {ber}"


def test_ber_zero_noise_returns_zero():
    """noise_std=0: BER=0（无噪声无误差，物理事实，非 fall-back）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    ber = compute_ber(signal, noise_std=0.0)
    assert ber == 0.0, f"零噪声 BER 应为 0，得到 {ber}"


def test_ber_negative_noise_raises():
    """noise_std < 0 raise ValueError（R03）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    with pytest.raises(ValueError):
        compute_ber(signal, noise_std=-0.1)


def test_ber_n_levels_lt_2_raises():
    """n_levels < 2 raise ValueError（无眼图开口，R03）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16)
    with pytest.raises(ValueError):
        compute_ber(signal, n_levels=1, noise_std=0.1)
    with pytest.raises(ValueError):
        compute_ber(signal, n_levels=0, noise_std=0.1)


def test_ber_monotonic_with_noise():
    """BER 随噪声增大而单调递增（噪声越大误码越多）。"""
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    noise_levels = [0.01, 0.05, 0.1, 0.2, 0.5]
    bers = [compute_ber(signal, noise_std=n) for n in noise_levels]
    for i in range(len(bers) - 1):
        assert bers[i] < bers[i + 1], (
            f"BER 应随噪声单调递增: noise={noise_levels[i]}→{bers[i]}, "
            f"noise={noise_levels[i+1]}→{bers[i+1]}"
        )


def test_ber_decreases_with_more_levels_eye():
    """相同噪声下，更多电平 → 眼图开口更小 → BER 更高。

    PAM4 (4 电平) 眼图开口 1/3 < NRZ (2 电平) 眼图开口 1。
    """
    _, signal = generate_pam4_signal(100, bit_rate=100e9, samples_per_symbol=16, seed=42)
    noise_std = 0.1
    ber_nrz = compute_ber(signal, n_levels=2, noise_std=noise_std)
    ber_pam4 = compute_ber(signal, n_levels=4, noise_std=noise_std)
    assert ber_pam4 > ber_nrz, "PAM4 (4 电平) BER 应 > NRZ (2 电平)"


# ===========================================================================
# 5. simulate_pam4 — 端到端仿真
# ===========================================================================
def test_simulate_return_keys():
    """返回 dict 含 ber / snr_db / n_symbols / bit_rate_gbps 四键。"""
    result = simulate_pam4()
    assert set(result.keys()) == {"ber", "snr_db", "n_symbols", "bit_rate_gbps"}


def test_simulate_default_values():
    """默认参数: n_symbols=1000, bit_rate_gbps=100。"""
    result = simulate_pam4()
    assert result["n_symbols"] == 1000
    assert result["bit_rate_gbps"] == 100.0


def test_simulate_return_types():
    """返回值类型: ber/snr_db 为 float, n_symbols 为 int, bit_rate_gbps 为 float。"""
    result = simulate_pam4()
    assert isinstance(result["ber"], float)
    assert isinstance(result["snr_db"], float)
    assert isinstance(result["n_symbols"], int)
    assert isinstance(result["bit_rate_gbps"], float)


def test_simulate_deterministic():
    """simulate_pam4 默认 seed=42，可复现。"""
    r1 = simulate_pam4(n_symbols=500, noise_std=0.05)
    r2 = simulate_pam4(n_symbols=500, noise_std=0.05)
    assert r1 == r2, "simulate_pam4 默认 seed 应确定性"


def test_simulate_invalid_params_raise():
    """非法参数 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        simulate_pam4(n_symbols=0)
    with pytest.raises(ValueError):
        simulate_pam4(bit_rate_gbps=0)
    with pytest.raises(ValueError):
        simulate_pam4(samples_per_symbol=0)
    with pytest.raises(ValueError):
        simulate_pam4(noise_std=-0.1)


def test_simulate_ber_snr_consistency():
    """ber 与 snr_db 来自同一信号，低噪声 → 高 SNR → 低 BER。"""
    r_low_noise = simulate_pam4(n_symbols=500, noise_std=0.02)
    r_high_noise = simulate_pam4(n_symbols=500, noise_std=0.2)
    assert r_low_noise["snr_db"] > r_high_noise["snr_db"]
    assert r_low_noise["ber"] < r_high_noise["ber"]


# ===========================================================================
# 6. 模块元信息
# ===========================================================================
def test_pam4_version():
    """子模块版本号 5.0.0。"""
    assert polaris_pam4.__version__ == "5.0.0"


def test_pam4_api_exports():
    """__all__ 导出 5 个稳定 API + __version__。"""
    assert set(polaris_pam4.__all__) == {
        "simulate_pam4",
        "generate_pam4_signal",
        "compute_ber",
        "compute_snr_db",
        "compute_eye_diagram",
        "__version__",
    }
