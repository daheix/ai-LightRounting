"""R555 实验数据拟合接口子模块（Extract Module 拆分自 quantum_cv_qec.py）。

S 参数拟合 / 损耗提取 / 耦合效率提取。

学术依据（R02）:
- Nelder-Mead simplex method: Nelder & Mead 1965 Comput J 7 308-313
  https://doi.org/10.1093/comjnl/7.4.308
- scipy.optimize.minimize
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
- Beer-Lambert 定律：η = exp(-α·L)（与经典衰减一致）
  https://doi.org/10.1016/B978-0-12-397024-5.00007-X
- Gottesman, Kitaev, Preskill 2001, "Encoding a qubit in an oscillator",
  Phys. Rev. A 64:012310, https://doi.org/10.1103/PhysRevA.64.012310
- Sivak et al. 2023, "Advances in Bosonic Quantum Error Correction with
  GKP Codes", https://arxiv.org/abs/2308.02913
- Conrad, Eisert, Flammia 2024, "Chasing shadows with GKP codes",
  https://arxiv.org/abs/2411.00235
- numpy.polyfit 文档: https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html

*创新* R555：S 参数拟合用 Nelder-Mead 简单x + 损耗物理约束
|S_ij|² ≤ 1，避免非物理解。

*创新* 底层逻辑：Nelder-Mead 无需梯度，适合噪声 S 参数拟合；
物理约束 |S|² ≤ 1 来自能量守恒（无源互易网络酉性），
支持理论为散射矩阵的酉性条件 S†S = I（Kurokawa 1965），
案例：从测量 S21 提取波导损耗 α 与耦合效率 κ。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

__all__ = [
    "FitResult",
    "SParamFitter",
    "LossExtractor",
    "CouplingEfficiencyExtractor",
]


@dataclass
class FitResult:
    """拟合结果。

    Attributes:
        params: 拟合参数。
        residuals: 残差。
        r_squared: 拟合优度 R²。
        success: 是否成功。
    """

    params: np.ndarray
    residuals: np.ndarray
    r_squared: float
    success: bool


class SParamFitter:
    """S 参数拟合器（Nelder-Mead + 物理约束）。

    拟合模型：S_ij(ω) = A·exp(iφ)·exp(-α·L)·exp(i·β·L)
    其中 α = α_0·(ω/ω_0)^p（损耗色散），β = n_eff·ω/c。

    物理约束：|S_ij|² ≤ 1（无源器件）。
    """

    @staticmethod
    def fit(
        freqs: np.ndarray,
        s_meas: np.ndarray,
        initial_params: np.ndarray | None = None,
    ) -> FitResult:
        """拟合 S 参数。

        Args:
            freqs: 频率 (Hz) 数组。
            s_meas: 测量 S 参数（复数）数组。
            initial_params: 初始参数 [A, φ, α_0, n_eff, p]。

        Returns:
            FitResult。
        """
        freqs = np.asarray(freqs, dtype=np.float64)
        s_meas = np.asarray(s_meas, dtype=np.complex128)
        if freqs.shape != s_meas.shape:
            raise ValueError(
                f"freqs {freqs.shape} 与 s_meas {s_meas.shape} 形状不匹配"
            )
        if initial_params is None:
            # 默认初值：A=0.9, φ=0, α_0=0, n_eff=2.0, p=1
            initial_params = np.array([0.9, 0.0, 0.0, 2.0, 1.0])
        initial_params = np.asarray(initial_params, dtype=np.float64)
        c0 = 2.99792458e8

        def model(params: np.ndarray, f: np.ndarray) -> np.ndarray:
            A, phi, alpha_0, n_eff, p = params
            omega = 2.0 * np.pi * f
            omega_ref = omega[0] if omega.size > 0 else 1.0
            # 物理约束：|A| ≤ 1
            A_clip = np.clip(A, 0.0, 1.0)
            alpha = alpha_0 * (omega / omega_ref) ** p
            beta = n_eff * omega / c0
            L = 1e-3  # 假设 1mm 长度
            return A_clip * np.exp(1j * phi) * np.exp(-alpha * L) * np.exp(1j * beta * L)

        def cost(params: np.ndarray) -> float:
            s_pred = model(params, freqs)
            residual = s_pred - s_meas
            return float(np.sum(np.abs(residual) ** 2))

        result = minimize(
            cost, initial_params, method="Nelder-Mead",
            options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-12},
        )
        s_pred = model(result.x, freqs)
        residuals = s_pred - s_meas
        # R² 拟合优度
        ss_res = float(np.sum(np.abs(residuals) ** 2))
        ss_tot = float(np.sum(np.abs(s_meas - np.mean(s_meas)) ** 2))
        if ss_tot < 1e-30:
            r_squared = 0.0
        else:
            r_squared = 1.0 - ss_res / ss_tot
        return FitResult(
            params=result.x,
            residuals=residuals,
            r_squared=float(r_squared),
            success=result.success,
        )


class LossExtractor:
    """光子损耗提取器。

    从测量 S 参数提取插入损耗：
        IL(dB) = -10·log10(|S_21|²)
    """

    @staticmethod
    def extract_insertion_loss(s21: np.ndarray) -> np.ndarray:
        """从 S21 提取插入损耗（dB）。

        Args:
            s21: 复数 S21 数组。

        Returns:
            插入损耗数组（dB，非负）。
        """
        s21 = np.asarray(s21, dtype=np.complex128)
        power = np.abs(s21) ** 2
        # 避免 log(0)
        if np.any(power <= 0.0):
            raise ValueError(
                "S21 功率为 0（可能完全损耗），无法计算 log（规则 14）"
            )
        return -10.0 * np.log10(power)

    @staticmethod
    def extract_loss_per_length(
        s21: np.ndarray, length: float,
    ) -> np.ndarray:
        """提取单位长度损耗（dB/cm 或 dB/m）。

        Args:
            s21: 复数 S21 数组。
            length: 器件长度（米）。

        Returns:
            单位长度损耗数组。
        """
        if length <= 0.0:
            raise ValueError(f"length 须 >0，实际 {length}")
        il = LossExtractor.extract_insertion_loss(s21)
        return il / length


class CouplingEfficiencyExtractor:
    """耦合效率提取器。

    从测量的 S 参数和理论 S 参数提取耦合效率：
        η_coupling = |S_measured|² / |S_ideal|²
    """

    @staticmethod
    def extract(
        s_measured: np.ndarray, s_ideal: np.ndarray,
    ) -> np.ndarray:
        """提取耦合效率。

        Args:
            s_measured: 测量 S 参数。
            s_ideal: 理想 S 参数（无损耗）。

        Returns:
            耦合效率数组 ∈ [0, 1]。
        """
        s_measured = np.asarray(s_measured, dtype=np.complex128)
        s_ideal = np.asarray(s_ideal, dtype=np.complex128)
        if s_measured.shape != s_ideal.shape:
            raise ValueError("形状不匹配")
        p_meas = np.abs(s_measured) ** 2
        p_ideal = np.abs(s_ideal) ** 2
        if np.any(p_ideal <= 0.0):
            raise ValueError(
                "理想 S 功率为 0，无法计算耦合效率（规则 14）"
            )
        eta = p_meas / p_ideal
        # 物理约束：η ≤ 1（无源器件不可能增益）
        return np.clip(eta, 0.0, 1.0)
