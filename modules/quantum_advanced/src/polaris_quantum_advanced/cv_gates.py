"""R551 连续变量（CV）量子计算子模块（纯 NumPy/SciPy CPU，R04 兼容）。

高斯态协方差矩阵表示 + 位移/压缩/旋转/分束器门 + 零差检测。

学术依据（R02，≥5 个文献 URL）:
1. Braunstein & van Loock 2005 Rev. Mod. Phys. 77 513-577,
   "Quantum information with continuous variables"
   https://doi.org/10.1103/RevModPhys.77.513
2. Weedbrook et al. 2012 Rev. Mod. Phys. 84 621-669,
   "Gaussian quantum information"
   https://doi.org/10.1103/RevModPhys.84.621
3. Menicucci, Flammia, Pfister 2008 PRL 101 220501,
   "One-way QC with CV cluster states"
   https://doi.org/10.1103/PhysRevLett.101.220501
4. Gottesman, Kitaev, Preskill 2001 Phys. Rev. A 64 012310,
   "Encoding a qubit in an oscillator"
   https://doi.org/10.1103/PhysRevA.64.012310
5. Sivak et al. 2023, "Advances in Bosonic QEC with GKP Codes"
   https://arxiv.org/abs/2308.02913
6. Adesso, Illuminati 2007 J. Phys. A 40 7821, "Entanglement in CV systems"
   https://doi.org/10.1088/1751-8113/40/26/S01

*创新* R551: 用协方差矩阵 V + 平均向量 d 双量表示 CV 高斯态
（Weedbrook 2012 §II），所有高斯门用辛变换 S + 位移 α 实现，
避免显式 Hilbert 空间存储（指数降复杂度）。

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- R551-CV-State 底层逻辑: CV 高斯态用 (V, d) 双量表示，V 为 2N×2N
  协方差矩阵，d 为 2N 平均向量。所有高斯门（位移/压缩/旋转/分束器）
  用辛变换 S 和位移 α 实现: V→S·V·S^T, d→S·d+α。避免显式 Hilbert
  空间存储（N 模式从 2^N 维降到 2N 维）。
  支持理论: Weedbrook 2012 Rev. Mod. Phys. 84 621 §II；
  Braunstein-van Loock 2005 Rev. Mod. Phys. 77 513 §III。
  案例: 单模压缩真空态 V=diag(e^{-2r}/2, e^{2r}/2)，r=1 时 V≠I/2。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class GaussianState:
    """CV 高斯态（N 模式），用协方差矩阵 V + 平均向量 d 表示。

    协方差矩阵 V (2N, 2N)：V_ij = 1/2·<{R_i, R_j}>，R = (x_1,...,x_N,
    p_1,...,p_N)^T，{A,B}=AB+BA。真空态 V = I/2，平均 d = 0。

    满足不确定性关系 V + i·Ω/2 ≥ 0，其中 Ω = [[0, I], [-I, 0]]（辛形式）。

    Attributes:
        covariance: 协方差矩阵 (2N, 2N)。
        mean: 平均向量 (2N,)。
        n_modes: 模式数 N。
    """

    covariance: NDArray[np.float64]
    mean: NDArray[np.float64]
    n_modes: int

    def __post_init__(self) -> None:
        cov = np.asarray(self.covariance, dtype=np.float64)
        mean = np.asarray(self.mean, dtype=np.float64)
        n = cov.shape[0] // 2
        if cov.shape != (2 * n, 2 * n):
            raise ValueError(
                f"协方差矩阵须 (2N, 2N)，实际 {cov.shape}"
            )
        if mean.shape != (2 * n,):
            raise ValueError(
                f"平均向量须 (2N,)，实际 {mean.shape}"
            )
        omega = self._symplectic_form(n)
        test = cov + 1j * omega / 2.0
        eigvals = np.linalg.eigvalsh((test + test.T.conj()) / 2)
        if np.min(eigvals.real) < -1e-9:
            raise ValueError(
                f"违反不确定性关系 V+iΩ/2 ≥ 0（min eigval "
                f"{np.min(eigvals.real):.3e}）"
            )
        self.covariance = cov
        self.mean = mean
        self.n_modes = n

    @staticmethod
    def _symplectic_form(n: int) -> NDArray[np.float64]:
        """辛形式 Ω = [[0, I], [-I, 0]]。"""
        return np.block([
            [np.zeros((n, n)), np.eye(n)],
            [-np.eye(n), np.zeros((n, n))],
        ])

    @classmethod
    def vacuum(cls, n_modes: int) -> "GaussianState":
        """构造 N 模式真空态 V=I/2, d=0。"""
        if n_modes < 1:
            raise ValueError(f"n_modes 须 ≥1，实际 {n_modes}")
        return cls(
            covariance=0.5 * np.eye(2 * n_modes),
            mean=np.zeros(2 * n_modes),
            n_modes=n_modes,
        )

    @classmethod
    def squeezed_vacuum(
        cls, r: float, theta: float = 0.0
    ) -> "GaussianState":
        """单模压缩真空态 V=diag(exp(-2r)/2, exp(2r)/2)。"""
        c = np.cos(theta)
        s = np.sin(theta)
        v = 0.5 * np.array([
            [np.exp(-2 * r) * c ** 2 + np.exp(2 * r) * s ** 2,
             (np.exp(-2 * r) - np.exp(2 * r)) * c * s],
            [(np.exp(-2 * r) - np.exp(2 * r)) * c * s,
             np.exp(-2 * r) * s ** 2 + np.exp(2 * r) * c ** 2],
        ])
        return cls(covariance=v, mean=np.zeros(2), n_modes=1)


class DisplacementGate:
    """位移算符 D(α) = exp(α·a† - α*·a)（Braunstein 2005 §III）。

    对高斯态：d → d + sqrt(2)·(Re α, Im α)，V 不变。
    """

    def __init__(self, alpha_real: float, alpha_imag: float) -> None:
        self.alpha = complex(alpha_real, alpha_imag)

    def apply(self, state: GaussianState) -> GaussianState:
        d = state.mean.copy()
        d[0] += np.sqrt(2.0) * self.alpha.real
        d[state.n_modes] += np.sqrt(2.0) * self.alpha.imag
        return GaussianState(
            covariance=state.covariance.copy(),
            mean=d,
            n_modes=state.n_modes,
        )


class SqueezingGate:
    """单模压缩算符 S(r, θ)。

    对高斯态：V → S·V·S^T，d → S·d
    S = R(θ)·diag(e^{-r}, e^r)·R(-θ)（Weedbrook 2012 §IV.A）
    """

    def __init__(self, r: float, theta: float = 0.0) -> None:
        if r < 0.0:
            raise ValueError(f"压缩参数 r 须 ≥0，实际 {r}")
        self.r = float(r)
        self.theta = float(theta)

    def _symplectic(self) -> NDArray[np.float64]:
        """2×2 辛变换矩阵 S = R(θ)·diag(e^{-r}, e^r)·R(-θ)。"""
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        R = np.array([[c, -s], [s, c]])
        D = np.diag([np.exp(-self.r), np.exp(self.r)])
        return R @ D @ R.T

    def apply(self, state: GaussianState, mode: int = 0) -> GaussianState:
        if not (0 <= mode < state.n_modes):
            raise ValueError(
                f"mode 须 ∈ [0, {state.n_modes})，实际 {mode}"
            )
        S = self._symplectic()
        V = state.covariance.copy()
        d = state.mean.copy()
        n = state.n_modes
        idx = [mode, n + mode]
        sub = V[np.ix_(idx, idx)]
        V[np.ix_(idx, idx)] = S @ sub @ S.T
        d_sub = d[idx]
        d[idx] = S @ d_sub
        return GaussianState(covariance=V, mean=d, n_modes=n)


class RotationGate:
    """相空间旋转 R(φ) = exp(-i φ a†a)。

    单模：V → R(φ)·V·R(-φ)，d → R(φ)·d
    R(φ) = [[cos φ, -sin φ], [sin φ, cos φ]]
    """

    def __init__(self, phi: float) -> None:
        self.phi = float(phi)

    def apply(self, state: GaussianState, mode: int = 0) -> GaussianState:
        if not (0 <= mode < state.n_modes):
            raise ValueError(
                f"mode 须 ∈ [0, {state.n_modes})，实际 {mode}"
            )
        c = np.cos(self.phi)
        s = np.sin(self.phi)
        R = np.array([[c, -s], [s, c]])
        V = state.covariance.copy()
        d = state.mean.copy()
        n = state.n_modes
        idx = [mode, n + mode]
        sub = V[np.ix_(idx, idx)]
        V[np.ix_(idx, idx)] = R @ sub @ R.T
        d_sub = d[idx]
        d[idx] = R @ d_sub
        return GaussianState(covariance=V, mean=d, n_modes=n)


class BeamSplitterGate:
    """50:50 分束器 B(θ, φ)（两模辛变换）。

    B(θ, φ) = exp(θ·(e^{-iφ}·a_1·a_2† - e^{iφ}·a_1†·a_2))
    50:50: θ=π/4，辛变换 4×4 矩阵（Weedbrook 2012 §IV.C）。
    """

    def __init__(self, theta: float = np.pi / 4, phi: float = 0.0) -> None:
        self.theta = float(theta)
        self.phi = float(phi)

    def apply(
        self, state: GaussianState, mode1: int, mode2: int,
    ) -> GaussianState:
        n = state.n_modes
        if not (0 <= mode1 < n and 0 <= mode2 < n and mode1 != mode2):
            raise ValueError(
                f"mode1/mode2 须不同且 ∈ [0, {n})，得到 {mode1}, {mode2}"
            )
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        R_phi = np.array([
            [np.cos(self.phi), -np.sin(self.phi)],
            [np.sin(self.phi), np.cos(self.phi)],
        ])
        I2 = np.eye(2)
        S = np.block([
            [c * I2, s * R_phi],
            [-s * R_phi.T, c * I2],
        ])
        idx = [mode1, mode2, n + mode1, n + mode2]
        V = state.covariance.copy()
        d = state.mean.copy()
        sub = V[np.ix_(idx, idx)]
        V[np.ix_(idx, idx)] = S @ sub @ S.T
        d_sub = d[idx]
        d[idx] = S @ d_sub
        return GaussianState(covariance=V, mean=d, n_modes=n)


class HomodyneDetection:
    """零差检测（测 x_quadrature 或 p_quadrature，Braunstein 2005 §V）。

    对单模高斯态：测 x = R_0，结果服从正态分布 N(d[0], V[0,0])。
    """

    def __init__(self, quadrature: str = "x") -> None:
        if quadrature not in ("x", "p"):
            raise ValueError(f"quadrature 须 'x'/'p'，实际 {quadrature}")
        self.quadrature = quadrature

    def measure(
        self,
        state: GaussianState,
        mode: int = 0,
        rng: np.random.Generator | None = None,
    ) -> float:
        """执行零差检测，返回测量值。"""
        if not (0 <= mode < state.n_modes):
            raise ValueError(f"mode 须 ∈ [0, {state.n_modes})，实际 {mode}")
        n = state.n_modes
        idx = mode if self.quadrature == "x" else n + mode
        mean = float(state.mean[idx])
        var = float(state.covariance[idx, idx])
        if var < 0.0:
            raise ValueError(f"方差须 ≥0，实际 {var}")
        rng = rng or np.random.default_rng()
        return float(rng.normal(mean, np.sqrt(var)))

    def expected_variance(
        self, state: GaussianState, mode: int = 0
    ) -> float:
        """理论方差 V[idx, idx]。"""
        n = state.n_modes
        idx = mode if self.quadrature == "x" else n + mode
        return float(state.covariance[idx, idx])


__all__ = [
    "GaussianState",
    "DisplacementGate",
    "SqueezingGate",
    "RotationGate",
    "BeamSplitterGate",
    "HomodyneDetection",
]
