"""R35: Verilog-A 光电协同紧凑模型 — PAM4 眼图 + BER 分析。

本模块从 `verilog_a.py` 拆分而来（facade 模式，保持外部 import 路径不变），
实现 PAM4（4 电平脉冲幅度调制）信号生成、眼图计算、误码率（BER）与
信噪比（SNR）分析。

核心公式:
- PAM4 电平: (0, 1/3, 2/3, 1)，每符号 2 比特
- BER 近似: BER ≈ 0.5 · erfc(√(SNR/2))
- SNR: SNR = (eye_opening / 2)² / σ_noise²
- SNR_dB = 10 · log10(P_signal / P_noise)

来源:
- OIF CEI-112G 标准
  https://www.oiforum.com/
- Lumerical INTERCONNECT 眼图分析
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Verilog-A PAM4 transceiver
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §9
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class PAM4Signal:
    """PAM4 调制信号（4 电平脉冲幅度调制）。

    来源: OIF CEI-112G 标准
      https://www.oiforum.com/

    Attributes:
        levels: 4 个电平值（V）。
        bit_rate: 比特率（bps）。
        samples_per_symbol: 每符号采样点数。
    """

    levels: tuple[float, float, float, float] = (0.0, 0.33, 0.67, 1.0)
    bit_rate: float = 100e9  # 100 Gbps
    samples_per_symbol: int = 16

    def __post_init__(self) -> None:
        """验证 PAM4 参数。

        Raises:
            ValueError: 电平数或比特率非法。
        """
        if len(self.levels) != 4:
            raise ValueError(f"PAM4 须 4 个电平，得到 {len(self.levels)}")
        if self.bit_rate <= 0:
            raise ValueError(f"比特率须 > 0，得到 {self.bit_rate}")
        if self.samples_per_symbol <= 0:
            raise ValueError(
                f"每符号采样点数须 > 0，得到 {self.samples_per_symbol}"
            )


def generate_pam4_signal(
    n_symbols: int = 1000,
    bit_rate: float = 100e9,
    samples_per_symbol: int = 16,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """生成 PAM4 调制信号。

    PAM4: 每符号 2 比特，4 电平 (0, 1/3, 2/3, 1)。

    来源: OIF CEI-112G 标准
      https://www.oiforum.com/

    Args:
        n_symbols: 符号数。
        bit_rate: 比特率（bps）。
        samples_per_symbol: 每符号采样点数。
        seed: 随机种子。

    Returns:
        (time, signal) 元组。
    """
    if n_symbols <= 0:
        raise ValueError(f"符号数须 > 0，得到 {n_symbols}")
    rng = np.random.default_rng(seed)
    # 4 电平 (0, 1/3, 2/3, 1)
    levels = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])
    symbols = rng.choice(levels, size=n_symbols)
    # 上采样
    signal = np.repeat(symbols, samples_per_symbol)
    # 时间轴
    symbol_duration = 1.0 / (bit_rate / 2.0)  # 每符号 2 比特
    sample_interval = symbol_duration / samples_per_symbol
    time = np.arange(len(signal)) * sample_interval
    return time, signal


def compute_eye_diagram(
    signal: np.ndarray,
    samples_per_symbol: int = 16,
    n_levels: int = 4,
) -> np.ndarray:
    """计算眼图（PAM4: 3 个眼）。

    将信号按 2 个符号周期折叠，生成眼图矩阵。

    来源: Lumerical INTERCONNECT 眼图分析
      https://optics.ansys.com/hc/en-us/articles/49697869166611

    Args:
        signal: 信号数组。
        samples_per_symbol: 每符号采样点数。
        n_levels: 调制电平数（PAM4=4）。

    Returns:
        眼图矩阵 [2*samples_per_symbol, n_windows]。
    """
    if samples_per_symbol <= 0:
        raise ValueError(f"每符号采样点数须 > 0，得到 {samples_per_symbol}")
    window_size = 2 * samples_per_symbol
    n_windows = len(signal) // window_size
    if n_windows == 0:
        raise ValueError(
            f"信号长度 {len(signal)} 不足一个眼图窗口 ({window_size})"
        )
    # 截断到整数窗口
    truncated = signal[: n_windows * window_size]
    eye = truncated.reshape(n_windows, window_size).T
    return eye


def compute_ber(
    signal: np.ndarray,
    samples_per_symbol: int = 16,
    n_levels: int = 4,
    noise_std: float = 0.05,
) -> float:
    """计算误码率（BER）。

    PAM4 BER: 基于眼图开口和噪声标准差。
    BER ≈ 0.5 * erfc(√(SNR/2))

    来源: OIF CEI-112G BER 分析
      https://www.oiforum.com/

    Args:
        signal: 信号数组。
        samples_per_symbol: 每符号采样点数。
        n_levels: 电平数。
        noise_std: 噪声标准差（V）。

    Returns:
        误码率（0-1）。
    """
    if noise_std < 0:
        raise ValueError(f"噪声标准差须 >= 0，得到 {noise_std}")
    if n_levels < 2:
        raise ValueError(f"电平数须 >= 2，得到 {n_levels}")
    # PAM4 电平
    levels = np.linspace(0, 1, n_levels)
    # 眼图开口（相邻电平间距）
    eye_opening = (levels[1] - levels[0]) if n_levels > 1 else 1.0
    # SNR = (eye_opening / 2)^2 / noise_std^2
    if noise_std == 0:
        return 0.0
    snr = (eye_opening / 2.0) ** 2 / (noise_std ** 2)
    # BER ≈ 0.5 * erfc(√(SNR/2))
    from math import erf, sqrt
    ber = 0.5 * (1.0 - erf(sqrt(snr / 2.0)))
    return float(ber)


def compute_snr_db(
    signal: np.ndarray,
    noise_std: float = 0.05,
) -> float:
    """计算信噪比（dB）。

    SNR_dB = 10 * log10(P_signal / P_noise)

    Args:
        signal: 信号数组。
        noise_std: 噪声标准差。

    Returns:
        SNR (dB)。
    """
    if noise_std <= 0:
        return float("inf")
    signal_power = float(np.mean(signal ** 2))
    noise_power = noise_std ** 2
    if noise_power <= 0:
        return float("inf")
    return 10.0 * math.log10(signal_power / noise_power)


__all__ = [
    "PAM4Signal",
    "compute_ber",
    "compute_eye_diagram",
    "compute_snr_db",
    "generate_pam4_signal",
]
