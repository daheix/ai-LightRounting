"""PoLaRIS PAM4 信号仿真子模块（polaris-pam4）。

提供 PAM4 信号生成、BER/SNR 计算、眼图分析稳定 API。
本子模块由旧 polaris-sim 拆分而来（每种仿真独立成包），仅保留 PAM4 信号相关功能。

## Input / Process / Output 三段式（IPO）

- simulate_pam4:
  - I: n_symbols=1000 / bit_rate_gbps=100 / samples_per_symbol=16 / noise_std=0.05
  - P: PAM4 4 电平 (0, 1/3, 2/3, 1) + BER=0.5·erfc(√(SNR_eye/2))（Shafik 2016）
  - O: dict{ber, snr_db, n_symbols, bit_rate_gbps}
- generate_pam4_signal:
  - I: n_symbols / bit_rate / samples_per_symbol / seed
  - P: 4 电平等概率随机选取 + 上采样
  - O: (time, signal) ndarray
- compute_ber:
  - I: signal / n_levels=4 / noise_std
  - P: SNR_eye=(eye/2)²/σ², BER=0.5·erfc(√(SNR_eye/2))
  - O: float
- compute_snr_db:
  - I: signal / noise_std
  - P: SNR_dB = 10·log10(mean(signal²)/σ²)
  - O: float
- compute_eye_diagram:
  - I: signal / samples_per_symbol / n_levels
  - P: 按 2 符号周期折叠
  - O: ndarray [2*samples_per_symbol, n_windows]

## 稳定 API

- ``simulate_pam4(n_symbols=1000, bit_rate_gbps=100, samples_per_symbol=16, noise_std=0.05) -> dict``
- ``generate_pam4_signal(n_symbols, bit_rate, samples_per_symbol, seed=42) -> (time, signal)``
- ``compute_ber(signal, samples_per_symbol=16, n_levels=4, noise_std=0.05) -> float``
- ``compute_snr_db(signal, noise_std=0.05) -> float``
- ``compute_eye_diagram(signal, samples_per_symbol=16, n_levels=4) -> ndarray``

## 设计原则
- 纯 NumPy + math（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 非法参数 raise；噪声为 0 时 BER=0（无误差物理事实）
- 理论 BER 公式（解析、确定性、可复现），非蒙特卡洛误差计数

## 来源（R02 学术诚信，≥5 个文献 URL）
- Shafik et al., "On the Error Vector Magnitude as a Performance Metric
  and Comparative Analysis", IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7410082
- OIF CEI-112G 标准 https://www.oiforum.com/
- Ansys Lumerical INTERCONNECT 眼图分析
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §9
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Proakis, "Digital Communications", McGraw-Hill 2007, §5（PAM BER 公式）
  https://www.mhprofessional.com/digital-communications-5th-edition-9780072957167-usa
- Agrawal, "Fiber-Optic Communication Systems", Wiley 2012, §4（眼图与 BER）
  https://onlinelibrary.wiley.com/doi/book/10.1002/9781118080856
"""

from __future__ import annotations

from polaris_pam4.signal import (
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
    simulate_pam4,
)

__version__ = "5.0.0"

__all__ = [
    "simulate_pam4",
    "generate_pam4_signal",
    "compute_ber",
    "compute_snr_db",
    "compute_eye_diagram",
    "__version__",
]
