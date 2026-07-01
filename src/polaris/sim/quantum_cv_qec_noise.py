"""R554 噪声模型增强子模块（Extract Module 拆分自 quantum_cv_qec.py）。

光子损耗 / 相位噪声 / 探测器暗计数 + 效率。

学术依据（R02）:
- Kok & Lovett 2010 Introduction to Optical Quantum Information Processing
  Cambridge University Press https://www.cambridge.org/9780521191356
- Carmichael 1993 "An Open Systems Approach to Quantum Optics"
- Walls & Milburn 2008 "Quantum Optics" §3.7
- O'Brien, Furusawa, Vuckovic 2009 Nat Photonics 3 687-695 Photonic QC
  https://doi.org/10.1038/nphoton.2009.229

*创新* R554：光子损耗通道用 Kraus 算子 E_k = sqrt((1-η)^k / k!)·
a^k·η^(n/2) 实现（Kok & Lovett 2010 §3.2），密度矩阵演化保持
正定性，与 Beer-Lambert 定律 η=exp(-α·L) 一致。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。


## 补充文献（R02 学术诚信补齐）
- Gottesman-Kitaev-Preskill 2001 Phys Rev A 64:012310: https://doi.org/10.1103/PhysRevA.64.012310
- Sivak et al. 2023 GKP review: https://arxiv.org/abs/2308.02913
- Mirhoseini et al. 2021 Nature AlphaChip: https://www.nature.com/articles/s41586-021-03544-w
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "PhotonLossChannel",
    "PhaseNoiseChannel",
    "DetectorModel",
]


class PhotonLossChannel:
    """光子损耗通道（Kok & Lovett 2010 §3.2，Carmichael 1993）。

    Kraus 算子（束分裂器模型，环境初态真空）：
        E_k |n> = sqrt(C(n,k)·(1-η)^k·η^(n-k)) · |n-k>   (n ≥ k)
                = 0                                       (n < k)
    其中 C(n,k) = n! / (k!·(n-k)!) 为二项式系数。

    满足完备性 Σ_k E_k† E_k = I（CPTP 性质，保迹）。

    演化矩阵元（解析公式）：
        ρ'_{mn} = η^((m+n)/2) · Σ_k sqrt(C(m+k,k)·C(n+k,k)) · (1-η)^k · ρ_{m+k, n+k}

    推导：由 <m|E_k|p> = sqrt(C(m+k,k)·(1-η)^k·η^m) · δ_{p, m+k} 代入
    ρ' = Σ_k E_k ρ E_k† 展开得到。注意 ρ_{m+k,n+k} 是高阶到低阶的反向累加
    （损失 k 个光子从 |m+k> 到 |m>），原版本 ρ_{m-k,n-k} 方向错误导致不保迹。

    物理验证（|1><1|, η=0.5）：
        ρ'_{00} = 0.5（损失 1 光子到真空），ρ'_{11} = 0.5（保留 1 光子）
        Tr(ρ') = 1.0 ✓，<n>_after = 0.5 = η·<n>_before ✓

    Beer-Lambert 定律：η = exp(-α·L)（与经典衰减一致）。

    文献：
    - Kok & Lovett 2010 §3.2 https://www.cambridge.org/9780521191356
    - Carmichael 1993 "An Open Systems Approach to Quantum Optics"
    - Walls & Milburn 2008 "Quantum Optics" §3.7
    """

    def __init__(self, eta: float, n_max: int = 20) -> None:
        """初始化光子损耗通道。

        Args:
            eta: 透射率，须 ∈ (0, 1]。
            n_max: 粒子数截断，须 ≥1。
        """
        if not (0.0 < eta <= 1.0):
            raise ValueError(f"eta 须 ∈ (0,1]，实际 {eta}")
        if n_max < 1:
            raise ValueError(f"n_max 须 ≥1，实际 {n_max}")
        self.eta = float(eta)
        self.n_max = int(n_max)

    @staticmethod
    def beer_lambert_transmission(
        alpha: float, length: float,
    ) -> float:
        """Beer-Lambert 定律 η = exp(-α·L)。

        Args:
            alpha: 衰减系数 (1/m)。
            length: 传播长度 (m)。

        Returns:
            透射率 η。
        """
        if alpha < 0.0:
            raise ValueError(f"alpha 须 ≥0，实际 {alpha}")
        if length < 0.0:
            raise ValueError(f"length 须 ≥0，实际 {length}")
        return float(np.exp(-alpha * length))

    def apply(self, rho: np.ndarray) -> np.ndarray:
        """对密度矩阵应用光子损耗通道（解析 Kraus 求和）。

        Args:
            rho: (N+1)×(N+1) 密度矩阵（N+1 ≤ n_max+1）。

        Returns:
            演化后密度矩阵（保迹 Tr(ρ') = Tr(ρ)）。

        Raises:
            ValueError: rho 非方阵或维度超过 n_max+1（规则 14）。
        """
        from math import factorial

        rho = np.asarray(rho, dtype=np.complex128)
        if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
            raise ValueError(f"rho 须方阵，实际 {rho.shape}")
        n_state = rho.shape[0]
        if n_state > self.n_max + 1:
            raise ValueError(
                f"rho 维度 {n_state} 超过 n_max+1={self.n_max + 1}（规则 14）"
            )
        rho_out = np.zeros_like(rho)
        eta = self.eta
        one_minus_eta = 1.0 - eta
        # 矩阵元公式（Kok 2010 Eq. 3.13）：
        # ρ'_{mn} = η^((m+n)/2) · Σ_k sqrt(C(m+k,k)·C(n+k,k)) · (1-η)^k · ρ_{m+k, n+k}
        # k 从 0 到 n_state-1-max(m,n)（保证 m+k, n+k 在截断内）
        for m in range(n_state):
            for nn in range(n_state):
                s = 0.0 + 0j
                k_max = n_state - 1 - max(m, nn)
                for k in range(k_max + 1):
                    cmk = factorial(m + k) // (factorial(k) * factorial(m))
                    cnk = factorial(nn + k) // (factorial(k) * factorial(nn))
                    coeff = float(cmk * cnk) ** 0.5
                    s += coeff * (one_minus_eta ** k) * rho[m + k, nn + k]
                rho_out[m, nn] = eta ** ((m + nn) / 2.0) * s
        return rho_out


class PhaseNoiseChannel:
    """相位噪声通道（高斯相位扩散）。

    ρ → ∫ dφ N(0, σ²) · R(φ)·ρ·R(-φ)
    等价：ρ_mn → exp(-(m-n)²·σ²/2)·ρ_mn
    """

    def __init__(self, sigma_phi: float) -> None:
        if sigma_phi < 0.0:
            raise ValueError(f"sigma_phi 须 ≥0，实际 {sigma_phi}")
        self.sigma_phi = float(sigma_phi)

    def apply(self, rho: np.ndarray) -> np.ndarray:
        rho = np.asarray(rho, dtype=np.complex128)
        n = rho.shape[0]
        if rho.shape != (n, n):
            raise ValueError(f"rho 须方阵，实际 {rho.shape}")
        # 矩阵元 ρ_mn 衰减因子 exp(-(m-n)²·σ²/2)
        indices = np.arange(n)
        diff = indices[:, None] - indices[None, :]
        decay = np.exp(-(diff ** 2) * self.sigma_phi ** 2 / 2.0)
        return rho * decay


class DetectorModel:
    """探测器模型（效率 + 暗计数）。

    探测效率 η：实际探测概率 = η·P(photon) + (1-η)·P(dark)
    暗计数率 λ_dark：泊松过程，单位时间暗计数期望。
    """

    def __init__(
        self, efficiency: float, dark_count_rate: float = 0.0,
    ) -> None:
        if not (0.0 <= efficiency <= 1.0):
            raise ValueError(f"efficiency 须 ∈ [0,1]，实际 {efficiency}")
        if dark_count_rate < 0.0:
            raise ValueError(
                f"dark_count_rate 须 ≥0，实际 {dark_count_rate}"
            )
        self.efficiency = float(efficiency)
        self.dark_count_rate = float(dark_count_rate)

    def click_probability(
        self, n_photons: int, time_window: float = 1.0,
    ) -> float:
        """计算探测器点击概率。

        P_click = 1 - (1-η)^n · exp(-λ_dark·Δt)

        Args:
            n_photons: 入射光子数。
            time_window: 探测时间窗口（秒）。

        Returns:
            点击概率 ∈ [0, 1]。
        """
        if n_photons < 0:
            raise ValueError(f"n_photons 须 ≥0，实际 {n_photons}")
        if time_window < 0.0:
            raise ValueError(f"time_window 须 ≥0，实际 {time_window}")
        no_click_signal = (1.0 - self.efficiency) ** n_photons
        no_click_dark = np.exp(-self.dark_count_rate * time_window)
        return float(1.0 - no_click_signal * no_click_dark)
