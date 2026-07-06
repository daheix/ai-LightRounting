"""马赫-曾德尔干涉仪（MZI）S 参数频域扫描。

本模块迁移自旧 ``polaris_sim/mzi.py``，提供 ``simulate_mzi_sparam``
稳定 API，对 MZI Bar 端传输率进行波长扫描，提取谐振波长与消光比。

## Input（输入）
- wavelength_nm: 扫描波长列表（nm）。None 时默认 1500-1600nm 101 点
  （SiEPIC EBeam PDK 典型 C 波段扫描范围）

## Process（处理）
MZI 由两个 2x2 分束器（MMI/DC）与两臂波导组成，Bar 端传输率
（Saleh & Teich 2019 §4.4）::

    T_bar(λ) = R² + T² + 2·R·T·cos(Δφ(λ))

其中:
- R, T 为 MMI 功率分束比（cross / bar），R + T = 1（无损理想化）
- Δφ = 2π·neff·ΔL/λ 为两臂相位差，ΔL 为臂长差
- 极值: T_max = (R+T)² = 1（Δφ=2kπ, 相长）, T_min = (R-T)²（Δφ=(2k+1)π, 相消）
- 谐振陷波波长（Bar 端极小）: 2π·neff·ΔL/λ = (2m+1)π → λ = 2·neff·ΔL/(2m+1)

## Output（输出）
dict::

    {
        "resonant_wavelength_nm": float,        # Bar 端陷波波长（nm）
        "extinction_ratio_db": float,           # 理论消光比（来自 MMI 分束比）
        "extinction_ratio_physical_db": float,  # 实际消光比（扫描 max/min）
        "n_points": int,                        # 扫描点数
        "T_max": float,                         # 扫描最大传输率
        "T_min": float,                         # 扫描最小传输率
    }

## 消光比
- 理论消光比（来自 MMI 分束比）::
      ER_db = 10·log10((R+T)² / (R-T)²) = 10·log10(1 / (R-T)²)
  R=0.48, T=0.52 → ER ≈ 27.96 dB ≈ 30 dB
- 实际消光比（扫描范围内 max/min，受有限采样与窗口影响）::
      ER_physical_db = 10·log10(max(T_bar) / min(T_bar))

## 设计参数（SiEPIC EBeam PDK）
- neff = 2.4（strip waveguide 1550nm 有效折射率）
- R = 0.48, T = 0.52（MMI 2x2 功率分束比，SiEPIC EBeam PDK 典型非理想分束）
- ΔL 选取使 Bar 端陷波落在 1549nm（m=9, ΔL = 19·1.549/(2·2.4) ≈ 6.1315μm，
  FSR ≈ 97.8nm，1500-1600nm 扫描内单陷波）

## 设计原则
- 纯 NumPy（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 非法参数 raise；T_min=0 时 ER 物理 raise
- 谐振波长由实际扫描 argmin 决定（不硬编码）

## 来源（R02 学术诚信，≥5 个文献 URL）
1. Saleh & Teich, "Fundamentals of Photonics", Wiley 2019, §4.4（MZI 传输率公式）
   https://www.wiley.com/en-us/Fundamentals+of+Photonics%2C+3rd+Edition-p-9781119303930
2. SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
3. Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §4.4
   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
4. Simphony MZI 教程
   https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
5. Soldano & Pennings, J. Lightwave Technol. 13(4), 1995（MMI 原理）
   https://ieeexplore.ieee.org/document/374358
6. Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, §4.2（干涉仪）
   https://www.wiley.com/en-us/Optical+Waves+in+Crystals%3A+Propagation+and+Control+of+Laser+Radiation-p-9780471430810
7. Pflügger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85
   https://arxiv.org/abs/2009.05146
"""

from __future__ import annotations

import numpy as np

__all__ = ["simulate_mzi_sparam"]


# SiEPIC EBeam PDK 物理参数
_NEFF = 2.4          # strip waveguide 1550nm 有效折射率
_MMI_SPLIT_R = 0.48  # MMI 2x2 cross 功率分束比（SiEPIC EBeam PDK 典型非理想分束）
_MMI_SPLIT_T = 0.52  # MMI 2x2 bar  功率分束比（R + T = 1.0）
# 臂长差 ΔL: 取 m=9 (2m+1=19) 使 Bar 端陷波落在 1549nm
# Δφ(1.549) = 2π·neff·ΔL/1.549 = 19π → cos=-1 → T_bar=(R-T)²（极小）
_M_ORDER = 9
_LAMBDA_RES_UM = 1.549  # 目标谐振波长（SiEPIC EBeam PDK 典型 MZI 工作点）
_DELTA_L_UM = (2 * _M_ORDER + 1) * _LAMBDA_RES_UM / (2.0 * _NEFF)


def simulate_mzi_sparam(wavelength_nm: list | None = None) -> dict:
    """MZI Bar 端 S 参数波长扫描。

    计算 T_bar(λ) = R² + T² + 2·R·T·cos(2π·neff·ΔL/λ)（Saleh & Teich 2019 §4.4），
    提取谐振陷波波长、理论/实际消光比。

    Args:
        wavelength_nm: 扫描波长列表（nm）。None 时默认 1500-1600nm 101 点
            （SiEPIC EBeam PDK 典型 C 波段扫描范围）。

    Returns:
        dict::

            {
                "resonant_wavelength_nm": float,        # Bar 端陷波波长（nm）
                "extinction_ratio_db": float,           # 理论消光比（来自 MMI 分束比）
                "extinction_ratio_physical_db": float,  # 实际消光比（扫描 max/min）
                "n_points": int,                        # 扫描点数
                "T_max": float,                         # 扫描最大传输率
                "T_min": float,                         # 扫描最小传输率
            }

    Raises:
        ValueError: 扫描点数 < 2 / 波长非正（R03 禁止 fall-back）。
        RuntimeError: T_min <= 0 导致消光比无法计算（物理上不应发生）。
    """
    if wavelength_nm is None:
        wl_nm = np.linspace(1500.0, 1600.0, 101)
    else:
        wl_nm = np.asarray(wavelength_nm, dtype=float)
        if wl_nm.ndim == 0:
            wl_nm = wl_nm.reshape(1)
    if wl_nm.size < 2:
        raise ValueError(f"扫描点数必须 >= 2，得到 {wl_nm.size}")
    if np.any(wl_nm <= 0):
        raise ValueError(f"波长必须 > 0 nm，得到 min={float(np.min(wl_nm))}")

    wl_um = wl_nm / 1000.0
    # 两臂相位差 Δφ = 2π·neff·ΔL/λ
    delta_phi = 2.0 * np.pi * _NEFF * _DELTA_L_UM / wl_um
    # Bar 端传输率（Saleh & Teich 2019 §4.4）
    R, T = _MMI_SPLIT_R, _MMI_SPLIT_T
    t_bar = R ** 2 + T ** 2 + 2.0 * R * T * np.cos(delta_phi)

    # 谐振陷波（最小传输率）
    idx_min = int(np.argmin(t_bar))
    resonant_wavelength_nm = float(wl_nm[idx_min])
    t_min = float(t_bar[idx_min])
    t_max = float(np.max(t_bar))

    if t_min <= 0:
        raise RuntimeError(
            f"T_min={t_min} <= 0，消光比无法计算（R03 禁止 fall-back）"
        )

    # 理论消光比（来自 MMI 分束比，假设无损 MMI 且完整条纹）
    extinction_ratio_db = 10.0 * np.log10((R + T) ** 2 / (R - T) ** 2)
    # 实际消光比（扫描范围内 max/min，反映有限采样）
    extinction_ratio_physical_db = 10.0 * np.log10(t_max / t_min)

    return {
        "resonant_wavelength_nm": resonant_wavelength_nm,
        "extinction_ratio_db": float(extinction_ratio_db),
        "extinction_ratio_physical_db": float(extinction_ratio_physical_db),
        "n_points": int(wl_nm.size),
        "T_max": t_max,
        "T_min": t_min,
    }
