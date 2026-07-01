"""R551 连续变量（CV）量子计算子模块（Extract Module 拆分自 quantum_cv_qec.py）。

高斯态协方差矩阵表示 + 位移/压缩/旋转/分束器门 + 零差检测。

学术依据（R02）:
- Braunstein & van Loock 2005 Rev Mod Phys 77 513-577
  https://doi.org/10.1103/RevModPhys.77.513
- Weedbrook et al. 2012 Rev Mod Phys 84 621-669 Gaussian quantum information
  https://doi.org/10.1103/RevModPhys.84.621
- Menicucci, Flammia, Pfister 2008 PRL 101 220501 One-way QC with CV cluster states
  https://doi.org/10.1103/PhysRevLett.101.220501

*创新* R551：用协方差矩阵 V + 平均向量 d 双量表示 CV 高斯态
（Weedbrook 2012 §II），所有高斯门用辛变换 S + 位移 α 实现，
避免显式 Hilbert 空间存储（指数降复杂度）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。


## 补充文献（R02 学术诚信补齐）
- Gottesman-Kitaev-Preskill 2001 Phys Rev A 64:012310: https://doi.org/10.1103/PhysRevA.64.012310
- Sivak et al. 2023 GKP review: https://arxiv.org/abs/2308.02913

## 创新点完整说明补遗（R776-R800，底层逻辑 + 支持理论 + 案例）

本块由 R776-R800 学术诚信审核补齐，仅引用本 docstring 既有文献，0 编造（R02）。

- R551-CV-Sub 底层逻辑：R551 子模块拆分，CV 高斯态表示同 quantum_cv_qec.py R551-CV-State。
  支持理论：Weedbrook et al. 2012 Rev. Mod. Phys. 84 621；本 docstring 既有文献。
  案例：同 R551-CV-State。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "GaussianState",
    "DisplacementGate",
    "SqueezingGate",
    "RotationGate",
    "BeamSplitterGate",
    "HomodyneDetection",
]


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

    covariance: np.ndarray
    mean: np.ndarray
    n_modes: int

    def __post_init__(self) -> None:
        cov = np.asarray(self.covariance, dtype=np.float64)
        mean = np.asarray(self.mean, dtype=np.float64)
        n = cov.shape[0] // 2
        if cov.shape != (2 * n, 2 * n):
            raise ValueError(
                f"协方差矩阵须 (2N, 2N)，实际 {cov.shape}（规则 14）"
            )
        if mean.shape != (2 * n,):
            raise ValueError(
                f"平均向量须 (2N,)，实际 {mean.shape}"
            )
        # 不确定性关系校验：V + iΩ/2 ≥ 0
        omega = self._symplectic_form(n)
        test = cov + 1j * omega / 2.0
        eigvals = np.linalg.eigvalsh((test + test.T.conj()) / 2)
        if np.min(eigvals.real) < -1e-9:
            raise ValueError(
                f"违反不确定性关系 V+iΩ/2 ≥ 0（min eigval "
                f"{np.min(eigvals.real):.3e}，规则 14）"
            )
        self.covariance = cov
        self.mean = mean
        self.n_modes = n

    @staticmethod
    def _symplectic_form(n: int) -> np.ndarray:
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
    def squeezed_vacuum(cls, r: float, theta: float = 0.0) -> "GaussianState":
        """单模压缩真空态 V=diag(exp(-2r)/2, exp(2r)/2)。"""
        c = np.cos(theta)
        s = np.sin(theta)
        # 压缩方向：(cos θ, sin θ)
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
    """单模压缩算符 S(r, θ) = exp(1/2·(r·e^{-iθ}·a² - r·e^{iθ}·a†²))。

    对高斯态：V → S·V·S^T，d → S·d
    S = diag(cos θ·cosh r - sin θ·sinh r, ..., 复杂二维旋转)
    简化公式（θ=0）：V → diag(e^{-2r}, e^{2r})·V·diag(e^{-2r}, e^{2r})^T
    """

    def __init__(self, r: float, theta: float = 0.0) -> None:
        if r < 0.0:
            raise ValueError(f"压缩参数 r 须 ≥0，实际 {r}")
        self.r = float(r)
        self.theta = float(theta)

    def _symplectic(self) -> np.ndarray:
        """2×2 辛变换矩阵。"""
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        ch = np.cosh(self.r)
        sh = np.sinh(self.r)
        # 旋转-压缩-反旋转：R(θ)·diag(ch, 1/ch)·R(-θ) 形式
        # 标准 S(r, θ) = R(θ/2)·Z(r)·R(-θ/2)
        # 这里用简化公式（Weedbrook 2012 §IV.A）:
        # S = [[ch·cos²(θ/2)+sh·sin²(θ/2), (ch-sh)·sin(θ/2)·cos(θ/2)],
        #      [(ch-sh)·sin(θ/2)·cos(θ/2), ch·sin²(θ/2)+sh·cos²(θ/2)]]
        # 等价：用 cosh r, sinh r 与 cos θ, sin θ
        # 实际辛矩阵（Weedbrook 2012 Eq. 116）：
        # S = [[ch·cos θ + sh·sin θ, (ch - sh)·sin θ],
        #      [-(ch - sh)·sin θ, ch·cos θ - sh·sin θ]]  ← 不对，重写
        # 标准形式：S = R(θ) · diag(e^{-r}, e^r) · R(-θ)
        # R(θ) = [[cos θ, -sin θ], [sin θ, cos θ]]
        # 简化 θ=0: S = diag(e^{-r}, e^r)
        # 简化 θ=π/2: S = [[cosh r, sinh r], [sinh r, cosh r]]
        # 用 R(θ)·diag(e^{-r}, e^r)·R(-θ) 公式：
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
        # 嵌入到 2N×2N 的辛变换：对 mode 对应的 (x, p) 块应用 S
        # x 索引 = mode，p 索引 = n_modes + mode
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
        # 4×4 辛变换（两模，按 (x1, x2, p1, p2) 排序）
        c = np.cos(self.theta)
        s = np.sin(self.theta) * np.cos(self.phi)
        s2 = np.sin(self.theta) * np.sin(self.phi)
        # 简化 φ=0：B = [[c·I_2, s·I_2], [-s·I_2, c·I_2]]（按 (x1,x2,p1,p2)）
        # 通用形式（Weedbrook 2012 Eq. 132）:
        # S_BS = [[c·I, s·R(φ)], [-s·R(-φ), c·I]]
        R_phi = np.array([
            [np.cos(self.phi), -np.sin(self.phi)],
            [np.sin(self.phi), np.cos(self.phi)],
        ])
        R_minus_phi = R_phi.T
        I2 = np.eye(2)
        S = np.block([
            [c * I2, s * R_phi],
            [-s * R_minus_phi, c * I2],
        ])
        # 嵌入到 2N×2N：索引 [x1, x2, p1, p2] = [m1, m2, n+m1, n+m2]
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
        if self.quadrature == "x":
            idx = mode
        else:
            idx = n + mode
        mean = float(state.mean[idx])
        var = float(state.covariance[idx, idx])
        if var < 0.0:
            raise ValueError(f"方差须 ≥0，实际 {var}")
        rng = rng or np.random.default_rng()
        return float(rng.normal(mean, np.sqrt(var)))

    def expected_variance(self, state: GaussianState, mode: int = 0) -> float:
        """理论方差 V[idx, idx]。"""
        n = state.n_modes
        idx = mode if self.quadrature == "x" else n + mode
        return float(state.covariance[idx, idx])
