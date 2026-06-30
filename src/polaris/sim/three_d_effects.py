"""3D 效应修正（R299）。

补齐 2D 仿真与实际 3D 光子器件的核心差距:
1. **侧壁角修正 (Sidewall Angle)**: 梯形截面 → 等效矩形宽度
2. **侧壁粗糙度散射损耗 (Sidewall Roughness Scattering)**: Sanchis 2006 模型
3. **侧向模式耦合损耗**: 不同宽度波导间模式失配

## 核心理论

### 1. 侧壁角修正

实际波导侧壁非垂直（光刻/刻蚀工艺），呈梯形截面:
- 上宽 w_top = w - 2h·tan(θ)
- 下宽 w_bottom = w
- 等效矩形宽度 w_eq = (w_top + w_bottom) / 2 = w - h·tan(θ)

修正后 n_eff 用等效宽度代入 2D 求解器重算（一阶近似）。

### 2. 侧壁粗糙度散射损耗 (Sanchis 2006)

对洛伦兹自相关 R(u) = σ² exp(-|u|/L_c)，散射损耗:

    α [1/m] = (k_0² σ² / (2 n_eff)) · (∂n_eff/∂w)² · F(Δβ · L_c)

其中:
- k_0 = 2π/λ (真空波数)
- σ: RMS 粗糙度
- ∂n_eff/∂w: 模式对宽度灵敏度
- F(u) = L_c / (1 + u²) (洛伦兹 PSD)
- Δβ = k_0 · (∂n_eff/∂w) · σ (传播常数失配)

### 3. 模式耦合损耗

宽度不连续 (w_1 → w_2) 的模式重叠积分:

    L_coupling = -10·log₁₀(|∫ψ_1 · ψ_2* dx|²)

近似公式（高斯模式）:
    L_coupling [dB] ≈ -4.343 · ln(1 - ((w_1 - w_2)/(w_1 + w_2))²)

## 学术依据

- Sanchis et al. 2006, "Analysis of the surface roughness in SOI
  waveguides", Opt. Express 14(15):6979-6986,
  DOI: 10.1364/OE.14.006979 (粗糙度散射损耗公式)
- Payne & Lacey 1994, "A theoretical analysis of scattering loss from
  planar optical waveguides", Opt. Quantum Electron. 26(11):L9-L14,
  DOI: 10.1007/BF00708239 (经典粗糙度散射理论)
- Barwicz & Smith 2005, "Performance analysis of silicon micro-ring
  resonators", J. Lightw. Technol. 23(9):2749-2762,
  DOI: 10.1109/JLT.2005.855934 (SOI 波导损耗实测)
- Bogaerts et al. 2012, "Silicon microring resonators", Laser Photonics
  Rev. 6(1):47-73, DOI: 10.1002/lpor.201100017 (SOI 工艺损耗综述)
- Soref et al. 1991, "Numerical modeling of silicon-on-insulator
  channel waveguides", IEEE J. Quantum Electron. 27(8):1971-1974,
  DOI: 10.1109/3.83406 (侧壁角效应)
- 模式重叠积分: Yariv 1973, "Coupled-mode theory for guided-wave optics",
  IEEE J. Quantum Electron. 9(9):919-933, DOI: 10.1109/JQE.1973.1077767

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class SidewallAngleCorrection:
    """侧壁角修正结果（R299）。

    Attributes:
        angle_deg: 侧壁角 θ (度)。
        width_um: 设计宽度 w (μm)。
        height_um: 波导高度 h (μm)。
        w_top_um: 梯形上宽 (μm)。
        w_bottom_um: 梯形下宽 (μm)。
        w_eq_um: 等效矩形宽度 (μm)。
        neff_2d: 原 2D 有效折射率。
        neff_corrected: 修正后有效折射率。
        delta_neff: 修正量 Δn_eff。

    学术依据: Soref et al. 1991, DOI: 10.1109/3.83406
    """

    angle_deg: float = 0.0
    width_um: float = 0.0
    height_um: float = 0.0
    w_top_um: float = 0.0
    w_bottom_um: float = 0.0
    w_eq_um: float = 0.0
    neff_2d: float = 0.0
    neff_corrected: float = 0.0
    delta_neff: float = 0.0


@dataclass
class RoughnessScatteringLoss:
    """粗糙度散射损耗结果（R299）。

    Attributes:
        sigma_nm: RMS 粗糙度 σ (nm)。
        correlation_length_nm: 自相关长度 L_c (nm)。
        wavelength_nm: 真空波长 λ (nm)。
        neff: 有效折射率。
        dneff_dw_per_um: 模式对宽度灵敏度 ∂n_eff/∂w (1/μm)。
        loss_db_per_cm: 散射损耗 (dB/cm)。
        loss_db_per_m: 散射损耗 (dB/m)。
        delta_beta_per_m: 传播常数失配 Δβ (1/m)。
        psd_lorentzian_m: 洛伦兹 PSD F(0) 值 (m)。

    学术依据: Sanchis et al. 2006, DOI: 10.1364/OE.14.006979
    """

    sigma_nm: float = 0.0
    correlation_length_nm: float = 0.0
    wavelength_nm: float = 0.0
    neff: float = 0.0
    dneff_dw_per_um: float = 0.0
    loss_db_per_cm: float = 0.0
    loss_db_per_m: float = 0.0
    delta_beta_per_m: float = 0.0
    psd_lorentzian_m: float = 0.0


# ============================================================================
# 公开 API
# ============================================================================


def correct_neff_for_sidewall_angle(
    neff_2d: float,
    width_um: float,
    height_um: float,
    sidewall_angle_deg: float,
    dneff_dw_per_um: float,
) -> SidewallAngleCorrection:
    """修正 2D 有效折射率（侧壁角效应，R299）。

    梯形截面（侧壁角 θ）→ 等效矩形宽度::

        w_top    = w - 2·h·tan(θ)   (top)
        w_bottom = w                (bottom)
        w_eq     = (w_top + w_bottom) / 2 = w - h·tan(θ)

    一阶 Taylor 展开（基于模式对宽度灵敏度）::

        n_eff_3d ≈ n_eff_2d + (∂n_eff/∂w) · (w_eq - w)
                 = n_eff_2d - (∂n_eff/∂w) · h · tan(θ)

    Args:
        neff_2d: 2D 仿真器输出的有效折射率。
        width_um: 设计宽度 w (μm)。
        height_um: 波导高度 h (μm)。
        sidewall_angle_deg: 侧壁角 θ (度)。θ=0 垂直，θ>0 上窄下宽。
        dneff_dw_per_um: 模式对宽度灵敏度 ∂n_eff/∂w (1/μm)，
            可由 ``sensitivity_analysis`` 计算。

    Returns:
        SidewallAngleCorrection。

    Raises:
        ValueError: 参数无效。

    学术依据:
    - Soref et al. 1991, DOI: 10.1109/3.83406 (侧壁角效应)
    - Bogaerts et al. 2012, DOI: 10.1002/lpor.201100017 (SOI 工艺)
    """
    if width_um <= 0:
        raise ValueError(f"width_um 必须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 必须 > 0，得到 {height_um}")
    if abs(sidewall_angle_deg) >= 89:
        raise ValueError(
            f"sidewall_angle_deg 应在 (-89, 89)，得到 {sidewall_angle_deg}"
        )

    theta_rad = np.radians(sidewall_angle_deg)
    tan_theta = float(np.tan(theta_rad))

    w_top = width_um - 2.0 * height_um * tan_theta
    w_bottom = width_um
    w_eq = 0.5 * (w_top + w_bottom)

    # 检查 w_top 是否有效
    if w_top <= 0:
        raise ValueError(
            f"侧壁角导致 w_top = {w_top:.4f} μm ≤ 0，"
            f"角度 {sidewall_angle_deg}° 对 w={width_um}/h={height_um} 过大"
        )

    # 一阶 Taylor: n_eff_3d = n_eff_2d + (∂n_eff/∂w) · (w_eq - w)
    delta_w = w_eq - width_um
    delta_neff = dneff_dw_per_um * delta_w
    neff_corrected = neff_2d + delta_neff

    return SidewallAngleCorrection(
        angle_deg=sidewall_angle_deg,
        width_um=width_um,
        height_um=height_um,
        w_top_um=float(w_top),
        w_bottom_um=float(w_bottom),
        w_eq_um=float(w_eq),
        neff_2d=neff_2d,
        neff_corrected=float(neff_corrected),
        delta_neff=float(delta_neff),
    )


def sidewall_roughness_loss(
    sigma_nm: float,
    correlation_length_nm: float,
    wavelength_nm: float,
    neff: float,
    dneff_dw_per_um: float,
) -> RoughnessScatteringLoss:
    """侧壁粗糙度散射损耗（Sanchis 2006 模型，R299）。

    对洛伦兹自相关 ``R(u) = σ² exp(-|u|/L_c)``::

        α [1/m] = (k_0² σ² / (2 n_eff)) · (∂n_eff/∂w)² · F(Δβ · L_c)

    其中:
    - ``k_0 = 2π/λ`` (真空波数)
    - ``Δβ = k_0 · (∂n_eff/∂w) · σ`` (传播常数失配)
    - ``F(u) = L_c / (1 + u²)`` (洛伦兹 PSD)

    单位转换: 1/m → dB/cm 乘 4.343·0.01 = 0.04343。

    Args:
        sigma_nm: RMS 粗糙度 σ (nm)，典型 SOI 工艺 1-5 nm。
        correlation_length_nm: 自相关长度 L_c (nm)，典型 30-100 nm。
        wavelength_nm: 真空波长 λ (nm)，典型 1310/1550 nm。
        neff: 有效折射率。
        dneff_dw_per_um: 模式对宽度灵敏度 ∂n_eff/∂w (1/μm)。

    Returns:
        RoughnessScatteringLoss。

    Raises:
        ValueError: 参数无效。

    学术依据:
    - Sanchis et al. 2006, DOI: 10.1364/OE.14.006979 (公式来源)
    - Payne & Lacey 1994, DOI: 10.1007/BF00708239 (经典理论)
    - Barwicz & Smith 2005, DOI: 10.1109/JLT.2005.855934 (SOI 实测对照)
    """
    if sigma_nm <= 0:
        raise ValueError(f"sigma_nm 必须 > 0，得到 {sigma_nm}")
    if correlation_length_nm <= 0:
        raise ValueError(
            f"correlation_length_nm 必须 > 0，得到 {correlation_length_nm}"
        )
    if wavelength_nm <= 0:
        raise ValueError(f"wavelength_nm 必须 > 0，得到 {wavelength_nm}")
    if neff <= 0:
        raise ValueError(f"neff 必须 > 0，得到 {neff}")

    # 转 SI 单位
    sigma_m = sigma_nm * 1e-9
    L_c_m = correlation_length_nm * 1e-9
    lambda_m = wavelength_nm * 1e-9
    dneff_dw_per_m = dneff_dw_per_um * 1e6

    k0 = 2.0 * np.pi / lambda_m  # 1/m
    delta_beta = k0 * dneff_dw_per_m * sigma_m  # 1/m
    # 洛伦兹 PSD: F(u) = L_c / (1 + u²)
    u = delta_beta * L_c_m
    F = L_c_m / (1.0 + u * u)  # m

    # α [1/m]
    alpha_1m = (
        (k0 * k0 * sigma_m * sigma_m / (2.0 * neff))
        * (dneff_dw_per_m * dneff_dw_per_m)
        * F
    )

    # 1/m → dB/cm: × 4.343 (1/cm 转换) × 0.01 (m→cm)
    alpha_db_cm = float(alpha_1m * 4.343 * 0.01)
    alpha_db_m = float(alpha_1m * 4.343)

    return RoughnessScatteringLoss(
        sigma_nm=sigma_nm,
        correlation_length_nm=correlation_length_nm,
        wavelength_nm=wavelength_nm,
        neff=neff,
        dneff_dw_per_um=dneff_dw_per_um,
        loss_db_per_cm=alpha_db_cm,
        loss_db_per_m=alpha_db_m,
        delta_beta_per_m=float(delta_beta),
        psd_lorentzian_m=float(F),
    )


def mode_mismatch_loss_gaussian(
    w1_um: float,
    w2_um: float,
) -> float:
    """高斯模式宽度失配耦合损耗（R299）。

    对两个高斯模式（宽度参数 w_1, w_2），模式重叠积分::

        η = |∫ψ_1 · ψ_2 dx|² = 2·w_1·w_2 / (w_1² + w_2²)

    耦合损耗::

        L [dB] = -10·log₁₀(η) = -10·log₁₀(2·w_1·w_2 / (w_1² + w_2²))

    Args:
        w1_um: 模式 1 宽度参数 (μm)。
        w2_um: 模式 2 宽度参数 (μm)。

    Returns:
        耦合损耗 (dB)。0 dB 表示完美匹配。

    Raises:
        ValueError: 参数无效。

    学术依据:
    - Yariv 1973, DOI: 10.1109/JQE.1973.1077767 (耦合模理论)
    - 高斯模式重叠: Saleh & Teich 2019, "Fundamentals of Photonics",
      Wiley, 3rd ed., Ch.3
    """
    if w1_um <= 0:
        raise ValueError(f"w1_um 必须 > 0，得到 {w1_um}")
    if w2_um <= 0:
        raise ValueError(f"w2_um 必须 > 0，得到 {w2_um}")

    eta = 2.0 * w1_um * w2_um / (w1_um * w1_um + w2_um * w2_um)
    if eta <= 0 or eta > 1.0:
        raise RuntimeError(
            f"模式重叠 η = {eta} 不在 (0, 1]，物理不合理。禁止 fall-back。"
        )
    return float(-10.0 * np.log10(eta))


__all__ = [
    "RoughnessScatteringLoss",
    "SidewallAngleCorrection",
    "correct_neff_for_sidewall_angle",
    "mode_mismatch_loss_gaussian",
    "sidewall_roughness_loss",
]
