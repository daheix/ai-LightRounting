"""2D RCWA 求解器（A01 §5，2D 周期光栅矢量实现）。

2D RCWA（crossed grating / conical mounting）将介电常数做二维傅里叶展开，
构造 2M×2M 本征值问题（M=(2Nx+1)(2Ny+1) 为总模式数），求解 [E_x, E_y]
两横向分量的耦合本征模。V 矩阵对应 H_t（切向磁场），用于层界面匹配。

本征值问题（Liu & Fan 2012，S4 公式，各向同性介质）::

    Q² = k₀²·blockdiag(Eps, Eps)
         - [[Kx·Eps_inv·Kx,  Kx·Eps_inv·Ky],
            [Ky·Eps_inv·Kx,  Ky·Eps_inv·Ky]]

    Q²·[S_x; S_y] = k_z²·[S_x; S_y]

Li 1996 因子化：TE 分量用 normal rule（Eps），TM/导数项用 inverse rule
（Eps_inv），在 2D 矢量形式下统一为 Eps（k₀² 项）+ Eps_inv（旋度项）。

文献来源（≥5，规则 18）：
1. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
2. Li 1996 JOSA A 13, 1870 —
   https://doi.org/10.1364/JOSAA.13.001870
3. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
4. Pham 2022 Nanomaterials 12(22), 3951 —
   https://doi.org/10.3390/nano12223951
5. Song 2025 Photonics 12(9), 943 (H-matrix) —
   https://www.mdpi.com/2304-6732/12/9/943
6. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import eig

from polaris_multiphysics.rcwa.smatrix import BlockSMatrix, cascade_redheffer
from polaris_multiphysics.rcwa.fourier import (
    build_epsilon_inv_toeplitz_2d,
    build_epsilon_toeplitz_2d,
)
from polaris_multiphysics.rcwa.layer import LayerModes, _normalize_kz

__all__ = [
    "GratingLayer2D",
    "RcwaConfig2D",
    "RcwaResult2D",
    "solve_rcwa_2d",
]


@dataclass
class GratingLayer2D:
    """2D 光栅单层定义。

    Attributes:
        thickness: 层厚 d（米）。
        eps_r_period: 一个周期 (Λx, Λy) 内 ε_r 采样 (N_grid_x, N_grid_y)。
    """

    thickness: float
    eps_r_period: np.ndarray

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError(f"层厚必须为正，实际 {self.thickness}")
        eps = np.asarray(self.eps_r_period, dtype=np.float64)
        if eps.ndim != 2 or min(eps.shape) < 3:
            raise ValueError(f"eps_r_period 须为 2D 数组且每维≥3，实际 {eps.shape}")
        if np.any(eps <= 0):
            raise ValueError("介电常数 ε_r 必须严格为正")
        self.eps_r_period = eps


@dataclass
class RcwaConfig2D:
    """2D RCWA 求解配置。

    Attributes:
        wavelength: 自由空间波长 λ（米）。
        period_x, period_y: x/y 方向周期 Λx, Λy（米）。
        n_harmonics_x, n_harmonics_y: x/y 截断阶数 Nx, Ny。
        theta, phi: 入射角（弧度）。theta 相对 z 轴，phi 相对 x 轴（方位角）。
        n_inc, n_sub: 入射/衬底折射率。
    """

    wavelength: float
    period_x: float
    period_y: float
    n_harmonics_x: int = 3
    n_harmonics_y: int = 3
    theta: float = 0.0
    phi: float = 0.0
    n_inc: float = 1.0
    n_sub: float = 1.0

    def __post_init__(self) -> None:
        for name, val in [
            ("wavelength", self.wavelength),
            ("period_x", self.period_x),
            ("period_y", self.period_y),
        ]:
            if val <= 0:
                raise ValueError(f"{name} 必须为正，实际 {val}")
        if self.n_harmonics_x < 1 or self.n_harmonics_y < 1:
            raise ValueError("截断阶数 Nx, Ny 必须 ≥1")
        if self.n_inc <= 0 or self.n_sub <= 0:
            raise ValueError("折射率必须为正")


@dataclass
class RcwaResult2D:
    """2D RCWA 求解结果。

    Attributes:
        reflection_eff: 反射衍射效率 (M,)，M=(2Nx+1)(2Ny+1)。
        transmission_eff: 透射衍射效率 (M,)。
        energy_sum: Σ(R+T)，应 ≈1.0。
        m_total: 总模式数 M。
        iterations: Redheffer 级联层数。
    """

    reflection_eff: np.ndarray
    transmission_eff: np.ndarray
    energy_sum: float
    m_total: int
    iterations: int


def _build_2d_wavevectors(
    config: RcwaConfig2D,
) -> tuple[np.ndarray, np.ndarray, float]:
    """构造 2D 衍射级 Bloch 波矢 kx, ky（A01 §5 步骤 0）。

    Returns:
        (kx, ky, k0): kx, ky 为 (M,) 数组，k0 真空波数。
    """
    k0 = 2.0 * np.pi / config.wavelength
    kx0 = config.n_inc * k0 * np.sin(config.theta) * np.cos(config.phi)
    ky0 = config.n_inc * k0 * np.sin(config.theta) * np.sin(config.phi)
    kx_grating = 2.0 * np.pi / config.period_x
    ky_grating = 2.0 * np.pi / config.period_y
    mx_idx = np.arange(-config.n_harmonics_x, config.n_harmonics_x + 1)
    my_idx = np.arange(-config.n_harmonics_y, config.n_harmonics_y + 1)
    # 2D 网格 → 展平（m 优先，n 次之，与 fourier.py 约定一致）
    mx_grid, my_grid = np.meshgrid(mx_idx, my_idx, indexing="ij")
    mx_flat = mx_grid.ravel()
    my_flat = my_grid.ravel()
    kx = kx0 + mx_flat * kx_grating
    ky = ky0 + my_flat * ky_grating
    return kx, ky, k0


def solve_layer_eigenmodes_2d(
    eps_r_period: np.ndarray,
    n_harmonics_x: int,
    n_harmonics_y: int,
    k0: float,
    kx: np.ndarray,
    ky: np.ndarray,
) -> LayerModes:
    """求解 2D 光栅层矢量本征模（2M×2M 本征值问题）。

    Args:
        eps_r_period: 一个周期 ε_r 采样 (N_grid_x, N_grid_y)。
        n_harmonics_x, n_harmonics_y: 截断阶数。
        k0: 真空波数。
        kx, ky: 横向 Bloch 波矢 (M,)。

    Returns:
        LayerModes（W, V, k_z），W/V 为 (2M, 2M)。
    """
    eps_toep = build_epsilon_toeplitz_2d(eps_r_period, n_harmonics_x, n_harmonics_y)
    eps_inv_toep = build_epsilon_inv_toeplitz_2d(
        eps_r_period, n_harmonics_x, n_harmonics_y, inverse=True
    )
    m_total = eps_toep.shape[0]
    kx_diag = np.diag(kx)
    ky_diag = np.diag(ky)
    # Q² = k₀²·blockdiag(Eps, Eps) - G,  G = [[Kx·Eps_inv·Kx, Kx·Eps_inv·Ky],
    #                                          [Ky·Eps_inv·Kx, Ky·Eps_inv·Ky]]
    kx_ei_kx = kx_diag @ eps_inv_toep @ kx_diag
    kx_ei_ky = kx_diag @ eps_inv_toep @ ky_diag
    ky_ei_kx = ky_diag @ eps_inv_toep @ kx_diag
    ky_ei_ky = ky_diag @ eps_inv_toep @ ky_diag
    g_mat = np.block([[kx_ei_kx, kx_ei_ky], [ky_ei_kx, ky_ei_ky]])
    eps_block = np.block(
        [
            [eps_toep, np.zeros((m_total, m_total), dtype=np.complex128)],
            [np.zeros((m_total, m_total), dtype=np.complex128), eps_toep],
        ]
    )
    q2 = (k0**2) * eps_block - g_mat
    eigvals, eigvecs = eig(q2)
    k_z = _normalize_kz(eigvals)
    # V = Q²·W·diag(1/k_z) = W·diag(k_z)（H_t 场，Q²W = W·diag(k_z²)）
    v = eigvecs @ np.diag(k_z)
    return LayerModes(w=eigvecs, v=v, k_z=k_z)


def build_homogeneous_modes_2d(
    n_refr: float, kx: np.ndarray, ky: np.ndarray, k0: float
) -> LayerModes:
    """构造 2D 齐次半空间本征模（入射/衬底）。

    齐次介质：W=I (2M×2M)，V=diag(k_z)（块对角，两横向分量相同 k_z）。
    """
    m_total = kx.size
    k_z_sq = (k0 * n_refr) ** 2 - kx**2 - ky**2
    k_z = _normalize_kz(k_z_sq)
    # 2M 维：[E_x 模式; E_y 模式]，各自 k_z 相同
    w = np.eye(2 * m_total, dtype=np.complex128)
    v = np.diag(np.concatenate([k_z, k_z]))
    return LayerModes(w=w, v=v, k_z=np.concatenate([k_z, k_z]))


def solve_rcwa_2d(layers: list[GratingLayer2D], config: RcwaConfig2D) -> RcwaResult2D:
    """求解 2D 周期光栅矢量 RCWA（A01 §5 完整流程）。

    Args:
        layers: 光栅层列表。
        config: 求解配置。

    Returns:
        RcwaResult2D（含衍射效率 + 能量守恒校验）。
    """
    if not layers:
        raise ValueError("光栅层列表不能为空（规则 14：禁止 fall-back）")
    kx, ky, k0 = _build_2d_wavevectors(config)
    m_total = kx.size

    # 本征模序列：入射 + 光栅层 + 衬底
    modes_list: list[LayerModes] = [build_homogeneous_modes_2d(config.n_inc, kx, ky, k0)]
    for layer in layers:
        modes_list.append(
            solve_layer_eigenmodes_2d(
                layer.eps_r_period,
                config.n_harmonics_x,
                config.n_harmonics_y,
                k0,
                kx,
                ky,
            )
        )
    modes_list.append(build_homogeneous_modes_2d(config.n_sub, kx, ky, k0))

    # S 矩阵序列（界面 + 传播）
    s_list: list[BlockSMatrix] = []
    for i in range(len(modes_list) - 1):
        s_list.append(_build_interface_2d(modes_list[i], modes_list[i + 1]))
        if i < len(modes_list) - 2:
            s_list.append(_build_propagation_2d(modes_list[i + 1], layers[i].thickness))
    s_global = cascade_redheffer(s_list)

    # 提取 0 阶入射 → 各阶反射/透射
    a_inc = np.zeros(2 * m_total, dtype=np.complex128)
    a_inc[m_total // 2] = 1.0  # 0 阶 E_x 分量
    r_amp = s_global.s11 @ a_inc
    t_amp = s_global.s21 @ a_inc

    kz_inc = modes_list[0].k_z[:m_total]
    kz_sub = modes_list[-1].k_z[:m_total]
    kz0 = kz_inc[m_total // 2]
    ref_ratio = _safe_real_ratio(kz_inc, kz0)
    trn_ratio = _safe_real_ratio(kz_sub, kz0)
    # 取前 M 维（E_x 分量）的反射/透射效率
    reflection_eff = np.abs(r_amp[:m_total]) ** 2 * ref_ratio
    transmission_eff = np.abs(t_amp[:m_total]) ** 2 * trn_ratio
    energy_sum = float(np.sum(reflection_eff) + np.sum(transmission_eff))
    return RcwaResult2D(
        reflection_eff=reflection_eff,
        transmission_eff=transmission_eff,
        energy_sum=energy_sum,
        m_total=m_total,
        iterations=len(s_list),
    )


def _build_interface_2d(left: LayerModes, right: LayerModes) -> BlockSMatrix:
    """2D 层界面 S 矩阵（与 layer.build_interface_smatrix 相同公式，2M 维）。"""
    a_mat = np.linalg.solve(left.w, right.w)
    b_mat = np.linalg.solve(left.v, right.v)
    ab_sum = a_mat + b_mat
    ab_diff = a_mat - b_mat
    rank = np.linalg.matrix_rank(ab_sum)
    if rank < ab_sum.shape[0]:
        raise RuntimeError(f"2D 界面 S 矩阵 (A+B) 奇异，rank={rank}/{ab_sum.shape[0]}")
    inv_ab = np.linalg.inv(ab_sum)
    s11 = ab_diff @ inv_ab
    s22 = -inv_ab @ ab_diff
    s21 = 2.0 * inv_ab
    s12 = 0.5 * (ab_sum - ab_diff @ inv_ab @ ab_diff)
    return BlockSMatrix(s11, s12, s21, s22)


def _build_propagation_2d(layer: LayerModes, thickness: float) -> BlockSMatrix:
    """2D 层内传播 S 矩阵（与 layer.build_propagation_smatrix 相同公式，2M 维）。"""
    if thickness < 0:
        raise ValueError(f"层厚必须非负，实际 {thickness}")
    x_phase = np.diag(np.exp(1j * layer.k_z * thickness))
    zeros = np.zeros_like(x_phase)
    return BlockSMatrix(zeros, x_phase, x_phase, zeros)


def _safe_real_ratio(numerator: np.ndarray, denominator: complex) -> np.ndarray:
    """安全计算 Re(num/den)，消逝波贡献置 0。

    R5-P1-7 修复: 负衍射效率表示能量守恒违反，禁止静默截断为 0（R03）。
    文献: Moharam 1995 JOSA A 12(5) 1077-1086 §6 能量守恒
      https://doi.org/10.1364/JOSAA.12.001077
    """
    num = np.asarray(numerator, dtype=np.complex128)
    propagating = np.abs(np.imag(num)) < 1e-10
    ratio = np.zeros_like(num, dtype=np.float64)
    safe_den = np.real(denominator) if np.abs(np.real(denominator)) > 1e-30 else 1e-30
    ratio[propagating] = np.real(num[propagating]) / safe_den
    if np.any(ratio[propagating] < -1e-10):
        raise RuntimeError(
            f"RCWA 2D 衍射效率出现负值 {ratio[propagating].min():.6e}，"
            "提示数值发散或傅里叶阶数不足（Moharam 1995 JOSA A §6 能量守恒违反）。"
            "请增加傅里叶阶数 n_harmonics 或检查介质层参数。"
            "R03 禁止 fall-back: 禁止静默截断负效率为 0。"
        )
    return ratio
