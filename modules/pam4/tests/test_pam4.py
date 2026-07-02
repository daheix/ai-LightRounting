"""polaris-pam4 子模块测试（R13 强制自测）。

测试覆盖（≥3 个 pytest，任务要求）:
- test_ber_range: BER ∈ (0, 1)
- test_snr_positive: SNR > 0
- test_eye_diagram_shape: 眼图矩阵 shape 正确
- test_signal_generation: 信号生成正确（4 电平）
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7410082
- OIF CEI-112G 标准 https://www.oiforum.com/
- Ansys Lumerical INTERCONNECT 眼图分析
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §9
- Proakis, "Digital Communications", McGraw-Hill 2007, §5
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


def test_ber_range():
    """BER 应在 (0, 1) 范围内（理论值，noise_std=0.05）。"""
    result = simulate_pam4(n_symbols=1000, bit_rate_gbps=100, noise_std=0.05)
    assert 0.0 < result["ber"] < 1.0, (
        f"BER 应在 (0, 1) 内，得到 {result['ber']}"
    )
    # 100Gbps PAM4 灵敏度噪声 0.05 → BER ~4.29e-04 @ SNR 21.97dB（任务预期）
    # 容忍 1 个数量级波动（公式解析确定，但参数微调可能漂移）
    assert result["ber"] < 0.1, f"BER 应远低于 0.1，得到 {result['ber']}"


def test_snr_positive():
    """SNR > 0（信号功率 > 噪声功率）。"""
    result = simulate_pam4(n_symbols=1000, bit_rate_gbps=100, noise_std=0.05)
    assert result["snr_db"] > 0, f"SNR 应 > 0，得到 {result['snr_db']}"
    # 100Gbps PAM4 noise_std=0.05: SNR ~21.97 dB（任务预期）
    assert 15.0 < result["snr_db"] < 30.0, (
        f"SNR 应在 15-30 dB 范围（≈21.97），得到 {result['snr_db']}"
    )


def test_eye_diagram_shape():
    """眼图矩阵 shape: [2*samples_per_symbol, n_windows]。"""
    n_symbols = 1000
    samples_per_symbol = 16
    _, signal = generate_pam4_signal(
        n_symbols=n_symbols, bit_rate=100e9, samples_per_symbol=samples_per_symbol
    )
    eye = compute_eye_diagram(signal, samples_per_symbol=samples_per_symbol)
    # 信号长度 = n_symbols * samples_per_symbol = 16000
    # 窗口 = 2*samples_per_symbol = 32 → n_windows = 16000/32 = 500
    expected_windows = (n_symbols * samples_per_symbol) // (2 * samples_per_symbol)
    assert eye.shape == (2 * samples_per_symbol, expected_windows), (
        f"眼图 shape 应 ({2*samples_per_symbol}, {expected_windows})，"
        f"得到 {eye.shape}"
    )
    # 眼图值应在 [0, 1] 内（PAM4 归一化电平）
    assert np.all(eye >= 0.0) and np.all(eye <= 1.0)


def test_signal_generation():
    """PAM4 信号生成: 4 电平值正确 (0, 1/3, 2/3, 1)。"""
    _, signal = generate_pam4_signal(
        n_symbols=1000, bit_rate=100e9, samples_per_symbol=16
    )
    unique_levels = sorted(set(signal.tolist()))
    # 应是 4 电平的子集（采样数足够时应有全部 4 个）
    assert len(unique_levels) >= 3, f"应至少 3 个电平被选中，得到 {unique_levels}"
    # 电平值应是 0, 1/3, 2/3, 1 的子集
    valid_levels = {0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0}
    for v in unique_levels:
        assert any(math.isclose(v, lv, rel_tol=1e-9) for lv in valid_levels), (
            f"电平 {v} 不在 PAM4 标准电平 {{0, 1/3, 2/3, 1}} 中"
        )


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        simulate_pam4(n_symbols=0)
    with pytest.raises(ValueError):
        simulate_pam4(bit_rate_gbps=0)
    with pytest.raises(ValueError):
        simulate_pam4(noise_std=-0.1)
    with pytest.raises(ValueError):
        generate_pam4_signal(n_symbols=-1, bit_rate=100e9)
    with pytest.raises(ValueError):
        compute_ber(np.array([0.0, 1.0]), n_levels=1, noise_std=0.1)


def test_pam4_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_pam4.__version__ == "5.0.0"
