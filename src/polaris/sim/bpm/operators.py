"""三对角差分算子构造（A03 §4.1，稀疏 scipy.sparse.diags）。

构造 BPM 抛物型方程（A03 §3.2 公式 F1）

    a·∂ψ/∂z = ∇⊥²ψ + b·ψ，a = 2i·k₀·n_ref，b = k₀²·(n² - n_ref²)

中的横向差分算子 A = ∇⊥² + diag(b)，即

    A[i, i]   = -2/Δx² + b_i           （主对角，含折射率项）
    A[i, i-1] = 1/Δx²                    （下次对角）
    A[i, i+1] = 1/Δx²                    （上次对角）

TM 半矢量形式（A03 §3.3 公式 F6）保留 n²·∂(n⁻²·∂/∂x)/∂x 界面项，
采用调和平均 n²_eff = 2·n_i²·n_{i+1}²/(n_i² + n_{i+1}²) 保证通量连续，
与 Optiwave OptiBPM、Photon Design OmniSim 半矢量实现一致。

banded 表示（scipy.linalg.solve_banded 输入，Thomas 算法 O(N)）::

    ab[0, 1:]   = 上次对角 a[i, i+1]   （长度 N-1，首元素未用）
    ab[1, :]    = 主对角 a[i, i]       （长度 N）
    ab[2, :-1]  = 下次对角 a[i, i-1]   （长度 N-1，末元素未用）

稀疏矩阵用 scipy.sparse.diags 一次性构造（向量化，无 Python 元素循环，
python代码开发规则.md §4），z 步进中复用（折射率不变段，A03 §8.3 性能策略）。

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy+scipy.sparse）
/python代码开发规则.md §4（向量化，scipy.sparse.diags 一次性构造）
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

__all__ = [
    "build_tridiag_operator",
    "build_tridiag_operator_te",
    "build_tridiag_operator_tm",
    "sparse_to_banded",
    "build_lhs_banded",
    "apply_rhs_operator",
    "Polarization",
]


class Polarization:
    """偏振模式枚举（A03 §3.3 半矢量 TE/TM 分离）。

    - TE: E_y 主分量，标量拉普拉斯 ∂²/∂x²（A03 §3.3 TE 形式）
    - TM: H_y 主分量，含 n²·∂(n⁻²·∂/∂x)/∂x 界面修正（A03 §3.3 TM 形式，公式 F6）
    - SCALAR: 标量 BPM（弱导近似，与 TE 形式相同）
    """

    TE = "te"
    TM = "tm"
    SCALAR = "scalar"


def build_tridiag_operator(
    n_arr: np.ndarray,
    dx: float,
    k0: float,
    n_ref: float,
    polarization: str = Polarization.TE,
) -> sp.csr_matrix:
    """构造 1D 三对角差分算子 A（A03 §4.1，按极化分发 TE/TM）。

    Args:
        n_arr: 折射率分布 (Nx,)，1D 实数或复数（含损耗）。
        dx: x 方向网格间距（米），必须 > 0。
        k0: 真空波数 2π/λ（1/m）。
        n_ref: 参考折射率，必须 > 0。
        polarization: 偏振模式 'te'/'tm'/'scalar'。

    Returns:
        scipy.sparse.csr_matrix (Nx, Nx)，复数。

    Raises:
        ValueError: 输入非法（规则 14：禁止 fall-back）。
    """
    if polarization in (Polarization.TE, Polarization.SCALAR):
        return build_tridiag_operator_te(n_arr, dx, k0, n_ref)
    if polarization == Polarization.TM:
        return build_tridiag_operator_tm(n_arr, dx, k0, n_ref)
    raise ValueError(f"polarization 须为 'te'/'tm'/'scalar'，实际 {polarization!r}（规则 14）")


def build_tridiag_operator_te(
    n_arr: np.ndarray,
    dx: float,
    k0: float,
    n_ref: float,
) -> sp.csr_matrix:
    """构造 1D TE/标量三对角算子 A（A03 §4.1，标准二阶中心差分）。

    A[i, i]   = -2/Δx² + k₀²·(n_i² - n_ref²)
    A[i, i±1] = 1/Δx²

    向量化构造（scipy.sparse.diags 一次性构造，无 Python 元素循环）。

    Args:
        n_arr: 折射率分布 (Nx,)。
        dx: x 方向网格间距（米）。
        k0: 真空波数（1/m）。
        n_ref: 参考折射率。

    Returns:
        scipy.sparse.csr_matrix (Nx, Nx) 复数。

    Raises:
        ValueError: 输入非法。
    """
    if n_arr.ndim != 1:
        raise ValueError(f"n_arr 必须为 1D，实际 {n_arr.ndim}D（规则 14）")
    if n_arr.size < 3:
        raise ValueError(f"n_arr 长度须 ≥3（含边界节点），实际 {n_arr.size}")
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if k0 <= 0.0:
        raise ValueError(f"k0 必须为正，实际 {k0}")
    if n_ref <= 0.0:
        raise ValueError(f"n_ref 必须为正，实际 {n_ref}")

    # 折射率项 b_i = k₀²·(n_i² - n_ref²)（向量化，无 Python 循环）
    n_arr_c = np.asarray(n_arr, dtype=np.complex128)
    b_diag = k0 * k0 * (n_arr_c * n_arr_c - n_ref * n_ref)
    inv_dx2 = 1.0 / (dx * dx)
    # 主对角：-2/Δx² + b_i（向量化）
    main = -2.0 * inv_dx2 + b_diag
    # 上/下次对角：1/Δx²（常数填充）
    off = np.full(n_arr.size - 1, inv_dx2, dtype=np.complex128)
    # scipy.sparse.diags 一次性构造（向量化，A03 §8.3 性能策略：z 步进复用）
    return sp.diags(
        [off, main, off],
        offsets=[-1, 0, 1],
        shape=(n_arr.size, n_arr.size),
        dtype=np.complex128,
        format="csr",
    )


def build_tridiag_operator_tm(
    n_arr: np.ndarray,
    dx: float,
    k0: float,
    n_ref: float,
) -> sp.csr_matrix:
    """构造 1D TM 半矢量三对角算子 A（A03 §3.3 公式 F6，含界面调和平均）。

    TM 形式保留 n²·∂(n⁻²·∂/∂x)/∂x 界面项，离散为::

        A[i, i-1] = n_i² / (n²_harm[i-1] · Δx²)
        A[i, i+1] = n_i² / (n²_harm[i]   · Δx²)
        A[i, i]   = -n_i²·(1/n²_harm[i-1] + 1/n²_harm[i]) / Δx² + b_i

    其中 n²_harm[i] = 2·n_i²·n_{i+1}²/(n_i² + n_{i+1}²) 为界面 i+1/2 处
    折射率平方的调和平均（保证通量连续，A03 §3.3）。

    Args:
        n_arr: 折射率分布 (Nx,)。
        dx: x 方向网格间距（米）。
        k0: 真空波数（1/m）。
        n_ref: 参考折射率。

    Returns:
        scipy.sparse.csr_matrix (Nx, Nx) 复数。

    Raises:
        ValueError: 输入非法。
    """
    if n_arr.ndim != 1:
        raise ValueError(f"n_arr 必须为 1D，实际 {n_arr.ndim}D（规则 14）")
    if n_arr.size < 3:
        raise ValueError(f"n_arr 长度须 ≥3，实际 {n_arr.size}")
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if k0 <= 0.0:
        raise ValueError(f"k0 必须为正，实际 {k0}")
    if n_ref <= 0.0:
        raise ValueError(f"n_ref 必须为正，实际 {n_ref}")

    n_arr_c = np.asarray(n_arr, dtype=np.complex128)
    n_sq = n_arr_c * n_arr_c  # n_i²（向量化）
    # 界面 i+1/2 调和平均 n²_harm[i] = 2·n_i²·n_{i+1}²/(n_i² + n_{i+1}²)，长度 N-1
    # 向量化（无 Python 循环，python代码开发规则.md §4）
    n_sq_next = n_sq[1:]
    n_sq_harm = 2.0 * n_sq[:-1] * n_sq_next / (n_sq[:-1] + n_sq_next)
    # 节点 i 的 "左侧界面" 为 n_sq_harm[i-1]，"右侧界面" 为 n_sq_harm[i]
    # 边界节点（i=0, i=N-1）仅有一个界面，另一个用同值填充避免除零（边界处理由 TBC/Dirichlet 覆盖）
    n_sq_harm_left = np.empty_like(n_sq)
    n_sq_harm_left[0] = n_sq_harm[0]
    n_sq_harm_left[1:] = n_sq_harm  # 节点 i 的左界面 = n_sq_harm[i-1]
    n_sq_harm_right = np.empty_like(n_sq)
    n_sq_harm_right[:-1] = n_sq_harm  # 节点 i 的右界面 = n_sq_harm[i]
    n_sq_harm_right[-1] = n_sq_harm[-1]

    inv_dx2 = 1.0 / (dx * dx)
    b_diag = k0 * k0 * (n_sq - n_ref * n_ref)
    # 主对角：-n_i²·(1/n²_harm_left + 1/n²_harm_right) / Δx² + b_i（向量化）
    main = -n_sq * (1.0 / n_sq_harm_left + 1.0 / n_sq_harm_right) * inv_dx2 + b_diag
    # 下次对角 A[i, i-1] = n_i²/n²_harm_left[i]/Δx²（i=1..N-1）
    lower = n_sq[1:] / n_sq_harm_left[1:] * inv_dx2
    # 上次对角 A[i, i+1] = n_i²/n²_harm_right[i]/Δx²（i=0..N-2）
    upper = n_sq[:-1] / n_sq_harm_right[:-1] * inv_dx2
    return sp.diags(
        [lower, main, upper],
        offsets=[-1, 0, 1],
        shape=(n_arr.size, n_arr.size),
        dtype=np.complex128,
        format="csr",
    )


def sparse_to_banded(a_sparse: sp.csr_matrix, ku: int = 1, kl: int = 1) -> np.ndarray:
    """稀疏三对角矩阵转 scipy.linalg.solve_banded 输入格式。

    banded 表示（A03 §4.2 Thomas 算法 O(N)，scipy 文档约定）::

        ab[0, 1:]   = 上次对角（长度 N-1，首元素 0 占位）
        ab[1, :]    = 主对角（长度 N）
        ab[2, :-1]  = 下次对角（长度 N-1，末元素 0 占位）

    Args:
        a_sparse: 稀疏三对角矩阵 (N, N)。
        ku: 上对角数（默认 1）。
        kl: 下对角数（默认 1）。

    Returns:
        ab: ndarray (ku+kl+1, N)，复数。

    Raises:
        ValueError: 矩阵非方阵或维度非法。
    """
    n = a_sparse.shape[0]
    if a_sparse.shape[0] != a_sparse.shape[1]:
        raise ValueError(f"稀疏矩阵须为方阵，实际 shape={a_sparse.shape}（规则 14）")
    if n < 2:
        raise ValueError(f"矩阵维度须 ≥2，实际 {n}")
    ab = np.zeros((ku + kl + 1, n), dtype=np.complex128)
    a_dense_diag = a_sparse.diagonal(0)
    ab[ku, :] = a_dense_diag
    if ku >= 1 and n >= 2:
        ab[ku - 1, 1:] = a_sparse.diagonal(1)
    if kl >= 1 and n >= 2:
        ab[ku + 1, :-1] = a_sparse.diagonal(-1)
    return ab


def build_lhs_banded(a_banded: np.ndarray, alpha_lhs: complex) -> np.ndarray:
    """构造 Crank-Nicolson 左侧矩阵 M_lhs = I - α·A 的 banded 表示（A03 §4.2 公式 F2）。

    其中 α = θ·Δz/a（复数），A 为三对角差分算子。

    M_lhs 的对角元 = 1 - α·A_diag，次对角元 = -α·A_offdiag。

    Args:
        a_banded: 算子 A 的 banded 表示 (3, N)（由 sparse_to_banded 构造）。
        alpha_lhs: 复系数 θ·Δz/a。

    Returns:
        lhs_banded: ndarray (3, N)，M_lhs 的 banded 表示（Dirichlet 基底，
            TBC 时由 boundary.apply_tbc_lhs_banded_inplace 修改边界行）。

    Raises:
        ValueError: a_banded 形状非法。
    """
    if a_banded.ndim != 2 or a_banded.shape[0] != 3:
        raise ValueError(f"a_banded 须为 (3, N) 三对角 banded，实际 shape={a_banded.shape}")
    lhs = np.empty_like(a_banded)
    # 主对角：1 - α·A_main（向量化，无 Python 循环）
    lhs[1, :] = 1.0 - alpha_lhs * a_banded[1, :]
    # 上次对角：-α·A_upper
    lhs[0, :] = -alpha_lhs * a_banded[0, :]
    # 下次对角：-α·A_lower
    lhs[2, :] = -alpha_lhs * a_banded[2, :]
    return lhs


def apply_rhs_operator(
    a_sparse: sp.csr_matrix,
    psi: np.ndarray,
    alpha_rhs: complex,
) -> np.ndarray:
    """计算 Crank-Nicolson 右端 rhs = [I + (1-θ)·Δz/a·A]·ψ（A03 §4.2 公式 F2）。

    稀疏矩阵-向量积（scipy.sparse 高效 CSR 实现，无 Python 循环）。

    Args:
        a_sparse: 三对角算子 A 的稀疏矩阵（CSR）。
        psi: 当前场向量 ψ^n，形状 (N,) 或 (Ny, Nx)。
        alpha_rhs: 复系数 (1-θ)·Δz/a。

    Returns:
        rhs: 与 psi 同形的复数数组。

    Raises:
        ValueError: 形状不匹配。
    """
    psi_c = np.asarray(psi, dtype=np.complex128)
    if psi_c.shape != (a_sparse.shape[0],):
        raise ValueError(
            f"psi 形状 {psi_c.shape} 与算子维度 ({a_sparse.shape[0]},) 不匹配（规则 14）"
        )
    # rhs = ψ + α·(A @ ψ)（稀疏 matvec + 向量加，向量化）
    return psi_c + alpha_rhs * (a_sparse @ psi_c)
