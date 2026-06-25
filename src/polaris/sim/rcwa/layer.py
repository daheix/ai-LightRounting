"""RCWA 单层本征模与 S 矩阵构造（A01 §5 步骤 2-3，ETM 增强透射矩阵法）。

每层内沿 z 均匀、横向周期分布 ε_r(x)。通过傅里叶展开 + 本征值问题求得层内
本征模 W、纵向波数 k_z、配套场矩阵 V，再构造层界面 S 矩阵。

本征值问题（1D，TE/TM 分离）：
    - TE（E_y，normal rule）: Q = k₀²·Eps - Kx²,  V = W·diag(k_z)
    - TM（H_y，inverse rule）: Q = k₀²·Eps - Eps·Kx·Eps_inv·Kx,
      V = Eps_inv·W·diag(k_z)（保证 E_x 连续性，Li 1996）

齐次层（入射/衬底半空间）：W=I，V=diag(k_z)（TE）或 diag(k_z/n²)（TM）。

S 矩阵约定（与 ``polaris.sim.cascade.smatrix.BlockSMatrix`` 一致）::

    [b_left ]   [S11  S12] [a_left ]
    [b_right] = [S21  S22] [a_right]

文献来源（≥5，规则 18）：
1. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
2. Li 1996 JOSA A 13, 1870 —
   https://doi.org/10.1364/JOSAA.13.001870
3. Lalanne & Morris 1996 JOSA A 13, 779 —
   https://doi.org/10.1364/JOSAA.13.000779
4. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
5. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import eig

from polaris.sim.cascade.smatrix import BlockSMatrix
from polaris.sim.rcwa.fourier import (
    build_epsilon_inv_toeplitz_1d,
    build_epsilon_toeplitz_1d,
)

__all__ = [
    "Polarization",
    "LayerModes",
    "solve_layer_eigenmodes_1d",
    "build_homogeneous_modes_1d",
    "build_interface_smatrix",
    "build_propagation_smatrix",
]


class Polarization:
    """偏振态常量（A01 §2）。"""

    TE = "te"  # E 平行光栅槽（s 偏振）
    TM = "tm"  # H 平行光栅槽（p 偏振）


@dataclass
class LayerModes:
    """单层本征模解（A01 §5 步骤 2）。

    Attributes:
        w: 本征模矩阵 (M, M)，列为层内本征场分布。
        v: 配套场矩阵 (M, M)，TE 为 H_x∝dE_y/dz，TM 为 E_x∝(1/ε)dH_y/dz。
        k_z: 纵向波数 (M,)，复数，约定 Im(k_z)≥0（传播实、消逝正虚）。
        n_total: 总模式数 M = 2N+1。
    """

    w: np.ndarray
    v: np.ndarray
    k_z: np.ndarray

    def __post_init__(self) -> None:
        m = self.w.shape[0]
        if self.w.shape != (m, m) or self.v.shape != (m, m):
            raise ValueError(f"W/V 形状不一致: W={self.w.shape}, V={self.v.shape}")
        if self.k_z.shape != (m,):
            raise ValueError(f"k_z 形状 {self.k_z.shape} 与 W ({m},{m}) 不匹配")

    @property
    def n_total(self) -> int:
        return self.w.shape[0]


def _normalize_kz(k_z: np.ndarray) -> np.ndarray:
    """分支切割：保证 Im(k_z) ≥ 0（物理因果性，A01 §4）。

    传播波 Im(k_z)=0，消逝波 Im(k_z)>0（指数衰减）。scipy.linalg.eig 的
    平方根分支需手动归一化。
    """
    k_z = np.asarray(k_z, dtype=np.complex128)
    root = np.sqrt(k_z)
    # 若 Im(sqrt)<0，取相反数（保证 Im≥0）
    flip = np.imag(root) < 0
    root[flip] = -root[flip]
    # 纯实数但原值为负的（非物理传播波）也翻转
    zero_imag = np.imag(root) == 0
    root[zero_imag & (np.real(root) < 0)] *= -1
    return root


def solve_layer_eigenmodes_1d(
    eps_r_period: np.ndarray,
    n_harmonics: int,
    k0: float,
    kx: np.ndarray,
    polarization: str,
) -> LayerModes:
    """求解 1D 光栅层本征模（A01 §5 步骤 2）。

    Args:
        eps_r_period: 一个周期 Λ 内 ε_r 采样 (N_grid,)。
        n_harmonics: 截断阶数 N（保留 |m|≤N 共 2N+1 模式）。
        k0: 真空波数 2π/λ。
        kx: 横向 Bloch 波矢 (2N+1,)，kx_m = kx0 + m·K。
        polarization: "te" 或 "tm"。

    Returns:
        LayerModes（W, V, k_z）。

    Raises:
        ValueError: 偏振态非法或参数不匹配。
    """
    polarization = polarization.lower()
    if polarization not in (Polarization.TE, Polarization.TM):
        raise ValueError(f"偏振态必须为 'te' 或 'tm'，实际 '{polarization}'")
    kx = np.asarray(kx, dtype=np.complex128)
    n_total = 2 * n_harmonics + 1
    if kx.shape != (n_total,):
        raise ValueError(f"kx 形状 {kx.shape} 与 (2N+1={n_total},) 不匹配")

    kx_diag = np.diag(kx)
    eps_toep = build_epsilon_toeplitz_1d(eps_r_period, n_harmonics)

    if polarization == Polarization.TE:
        # TE: Q = k₀²·Eps - Kx²，特征值 = k_z²，V = W·diag(k_z)（H_x∝dE_y/dz）
        q_mat = (k0**2) * eps_toep - kx_diag @ kx_diag
        w, k_z_sq = _eig_sorted(q_mat)
        k_z = _normalize_kz(k_z_sq)
        v = w @ np.diag(k_z)
    else:
        # TM: Q = k₀²·Eps - Eps·Kx·Eps_inv·Kx（Li 1996 inverse rule）
        # 特征值 = k_z²，V = Eps_inv·W·diag(k_z)（保证 E_x 连续）
        eps_inv_toep = build_epsilon_inv_toeplitz_1d(eps_r_period, n_harmonics)
        q_mat = (k0**2) * eps_toep - eps_toep @ kx_diag @ eps_inv_toep @ kx_diag
        w, k_z_sq = _eig_sorted(q_mat)
        k_z = _normalize_kz(k_z_sq)
        v = eps_inv_toep @ w @ np.diag(k_z)
    return LayerModes(w=w, v=v, k_z=k_z)


def build_homogeneous_modes_1d(
    n_refr: float,
    kx: np.ndarray,
    k0: float,
    polarization: str,
) -> LayerModes:
    """构造齐次半空间（入射/衬底）本征模（A01 §5 步骤 2，无光栅层）。

    齐次介质 ε=n² 常数，Fourier 模为平面波：W=I，V=diag(k_z)（TE）
    或 diag(k_z/n²)（TM）。

    Args:
        n_refr: 介质折射率 n（实数，无损耗）。
        kx: 横向 Bloch 波矢 (M,)。
        k0: 真空波数。
        polarization: "te" 或 "tm"。

    Returns:
        LayerModes（W=I, V=diag(k_z) 或 diag(k_z/n²), k_z）。
    """
    polarization = polarization.lower()
    kx = np.asarray(kx, dtype=np.complex128)
    k_z_sq = (k0 * n_refr) ** 2 - kx**2
    k_z = _normalize_kz(k_z_sq)
    m = kx.size
    w = np.eye(m, dtype=np.complex128)
    if polarization == Polarization.TE:
        v = np.diag(k_z)
    else:
        # TM: E_x ∝ (1/ε)·dH_y/dz = (1/n²)·k_z·H_y → V = diag(k_z/n²)
        v = np.diag(k_z / (n_refr**2))
    return LayerModes(w=w, v=v, k_z=k_z)


def _eig_sorted(q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """本征值分解并按虚部升序、实部降序排序（传播波在前）。

    Args:
        q: 本征值矩阵 (M, M)。

    Returns:
        (w, eigvals): 本征向量矩阵 (M, M) 与本征值 (M,)。
    """
    eigvals, eigvecs = eig(q)
    # 排序：传播波（Im≈0）在前，按 Re(k_z²) 降序；消逝波在后
    order = np.lexsort((np.imag(eigvals), -np.real(eigvals)))
    return eigvecs[:, order], eigvals[order]


def build_interface_smatrix(left: LayerModes, right: LayerModes) -> BlockSMatrix:
    """构造层界面 S 矩阵（A01 §5 步骤 3，ETM 单界面）。

    输入：(a_left, b_right) = (左入射前向波, 右入射后向波)
    输出：(b_left, a_right) = (左出射后向波, 右出射前向波)

    由切向场连续性（E_t、H_t）::

        W_L(a+b) = W_R(c+d),  V_L(a-b) = V_R(c-d)

    其中 a/b 为左层前向/后向，c/d 为右层前向/后向。解出::

        inv_AB = inv(A+B),  A = inv(W_L)·W_R,  B = inv(V_L)·V_R
        S11 = (A-B)·inv_AB
        S12 = 0.5·[(A+B) - (A-B)·inv_AB·(A-B)]
        S21 = 2·inv_AB
        S22 = -inv_AB·(A-B)

    Args:
        left: 左层本征模。
        right: 右层本征模。

    Returns:
        界面 S 矩阵（2M×2M 分块）。

    Raises:
        RuntimeError: (A+B) 奇异（界面物理不合理，规则 14）。
    """
    if left.n_total != right.n_total:
        raise ValueError(f"层界面模式数不匹配: left={left.n_total}, right={right.n_total}")
    # A = inv(W_L)·W_R, B = inv(V_L)·V_R（用 solve 替代 inv）
    a_mat = np.linalg.solve(left.w, right.w)
    b_mat = np.linalg.solve(left.v, right.v)
    ab_sum = a_mat + b_mat
    ab_diff = a_mat - b_mat
    # 检查 (A+B) 可逆性
    rank = np.linalg.matrix_rank(ab_sum)
    if rank < ab_sum.shape[0]:
        raise RuntimeError(
            f"界面 S 矩阵 (A+B) 奇异，rank={rank}/{ab_sum.shape[0]}。"
            "检查层界面物理合理性（介电常数对比度过大或模式简并）。"
        )
    inv_ab = np.linalg.inv(ab_sum)
    s11 = ab_diff @ inv_ab
    s22 = -inv_ab @ ab_diff
    s21 = 2.0 * inv_ab
    s12 = 0.5 * (ab_sum - ab_diff @ inv_ab @ ab_diff)
    return BlockSMatrix(s11, s12, s21, s22)


def build_propagation_smatrix(layer: LayerModes, thickness: float) -> BlockSMatrix:
    """构造层内传播 S 矩阵（A01 §5 步骤 3，ETM 均匀段）。

    齐次段无反射，仅相位累积：S = [[0, X], [X, 0]]，
    X = diag(exp(i·k_z·d))。对消逝波（Im(k_z)>0），|X|=exp(-Im(k_z)·d)<1，
    天然衰减无溢出（C03 §7.2 数值稳定性）。

    Args:
        layer: 层本征模（提供 k_z）。
        thickness: 层厚 d（米）。

    Returns:
        传播 S 矩阵（2M×2M 分块，R=0, T=X）。
    """
    if thickness < 0:
        raise ValueError(f"层厚必须非负，实际 {thickness}")
    x_phase = np.diag(np.exp(1j * layer.k_z * thickness))
    zeros = np.zeros_like(x_phase)
    # S11=0, S12=X (右→左透射), S21=X (左→右透射), S22=0
    return BlockSMatrix(zeros, x_phase, x_phase, zeros)
