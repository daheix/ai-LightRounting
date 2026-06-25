"""RCWA 傅里叶因子化（A01 §3.1，Li 1996 normal/inverse rule）。

将周期介电常数 $\\varepsilon_r(x,y)$ 展开为双重傅里叶级数，并构造卷积
Toeplitz 矩阵。Li 1996 证明：在介电常数间断面，对 TE（电场平行光栅槽）
使用 normal rule（直接用 $\\varepsilon$ 的傅里叶系数），对 TM（磁场平行光栅槽）
使用 inverse rule（用 $1/\\varepsilon$ 的傅里叶系数），可消除 Gibbs 现象导致的
TM 偏振收敛缓慢，达到指数收敛。

数学定义（Li 1996 公式 5.2）：

    $\\varepsilon_r(x) = \\sum_m \\tilde{\\varepsilon}_m e^{i m K x}$
    $(\\varepsilon_r E)_m = \\sum_p \\tilde{\\varepsilon}_{m-p} E_p$  (normal, TE)
    $E_m = \\sum_p \\tilde{(1/\\varepsilon)}_{m-p} (\\varepsilon E)_p$  (inverse, TM)

2D 周期结构（$\\varepsilon_r(x,y)$）的傅里叶系数为 2D 数组 $\\tilde{\\varepsilon}_{mn}$，
卷积矩阵为嵌套 Toeplitz（Kronecker 结构）。

文献来源（≥5，规则 18 学术诚信）：
1. Li 1996 JOSA A 13, 1870 —
   https://doi.org/10.1364/JOSAA.13.001870
2. Lalanne & Morris 1996 JOSA A 13, 779 —
   https://doi.org/10.1364/JOSAA.13.000779
3. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
4. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
5. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/
6. Song 2025 Photonics 12(9), 943 (H-matrix) —
   https://www.mdpi.com/2304-6732/12/9/943

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

from enum import Enum

import numpy as np

__all__ = [
    "FourierRule",
    "fourier_coefficients_1d",
    "toeplitz_from_coefficients",
    "build_epsilon_toeplitz_1d",
    "build_epsilon_inv_toeplitz_1d",
    "fourier_coefficients_2d",
    "build_epsilon_toeplitz_2d",
    "select_rule",
]


class FourierRule(Enum):
    """Li 1996 傅里叶因子化规则（A01 §3.1）。

    - NORMAL: 直接用 ε 的傅里叶系数构造 Toeplitz（TE 偏振，E 场连续）。
    - INVERSE: 用 1/ε 的傅里叶系数构造 Toeplitz（TM 偏振，D=εE 连续）。
    """

    NORMAL = "normal"
    INVERSE = "inverse"


def select_rule(is_te: bool) -> FourierRule:
    """按偏振态自适应选择 Li 1996 因子化规则（S1-C4 验收点）。

    Args:
        is_te: True 表示 TE 偏振（E 平行光栅槽，电场切向连续）。

    Returns:
        - TE → NORMAL（用 ε 的傅里叶系数）
        - TM → INVERSE（用 1/ε 的傅里叶系数）
    """
    return FourierRule.NORMAL if is_te else FourierRule.INVERSE


def fourier_coefficients_1d(
    eps_r: np.ndarray, n_harmonics: int
) -> np.ndarray:
    """计算 1D 周期介电常数的傅里叶系数（A01 §3.1）。

    采样一个周期 $\\Lambda$，用 FFT 计算 $\\tilde{\\varepsilon}_m$，
    $m \\in \\{-N, ..., 0, ..., N\\}$（共 2N+1 个系数）。

    Args:
        eps_r: 一个周期内 ε_r 的采样值 (N_grid,)，N_grid ≥ 2·n_harmonics+1（Nyquist）。
        n_harmonics: 截断阶数 N（保留 |m| ≤ N 共 2N+1 个谐波）。

    Returns:
        傅里叶系数 $\\tilde{\\varepsilon}_m$，形状 (2N+1,)，按 [m=-N, ..., 0, ..., +N] 排列。

    Raises:
        ValueError: 采样点数不足或 n_harmonics < 1。
    """
    eps_r = np.asarray(eps_r, dtype=np.float64)
    if eps_r.ndim != 1:
        raise ValueError(f"eps_r 须为 1D 数组，实际 {eps_r.ndim}D")
    if n_harmonics < 1:
        raise ValueError(f"截断阶数 N 必须 ≥1，实际 {n_harmonics}")
    n_grid = eps_r.size
    n_need = 2 * n_harmonics + 1
    if n_grid < n_need:
        raise ValueError(
            f"采样点数 {n_grid} 不足，需 ≥{n_need}（2N+1，Nyquist 准则）"
        )
    # FFT 计算傅里叶系数：tilde_eps_m = (1/N_grid) * sum_n eps[n] * exp(-i·2π·m·n/N_grid)
    full_fft = np.fft.fft(eps_r) / n_grid
    # 取 [-N, ..., 0, ..., +N] 共 2N+1 个系数（fftshift 排列）
    # np.fft.fft 输出顺序：[0, 1, ..., N_grid/2, -N_grid/2+1, ..., -1]
    # 用 fftshift 将 0 阶移到中心，再取中间 2N+1 个
    shifted = np.fft.fftshift(full_fft)
    center = n_grid // 2
    start = center - n_harmonics
    end = center + n_harmonics + 1
    return shifted[start:end].astype(np.complex128)


def toeplitz_from_coefficients(coeffs: np.ndarray) -> np.ndarray:
    """由傅里叶系数构造 Toeplitz 卷积矩阵（A01 §3.1）。

    $T_{mp} = \\tilde{\\varepsilon}_{m-p}$，$m, p \\in \\{-N, ..., N\\}$。
    矩阵第 (i,j) 元素 = coeffs[N + i - j]（按 [m=-N..+N] 排列）。

    Args:
        coeffs: 傅里叶系数 (2N+1,)，按 [m=-N, ..., 0, ..., +N] 排列。

    Returns:
        (2N+1)×(2N+1) 复 Toeplitz 矩阵。
    """
    coeffs = np.asarray(coeffs, dtype=np.complex128)
    n = coeffs.size
    if n % 2 == 0:
        raise ValueError(f"傅里叶系数数须为奇数 2N+1，实际 {n}")
    n_half = n // 2
    # T[i, j] = coeffs[n_half + i - j]
    idx = n_half + np.arange(n)[:, None] - np.arange(n)[None, :]
    # 处理越界（|i-j|>N 时应为 0，但 |i-j| ≤ 2N = n-1 ≤ n_half*2，不会越界）
    # 当 i-j < -N 或 > N 时取 0（实际不会发生，因为 |i-j| ≤ n-1 = 2N）
    mask = (idx >= 0) & (idx < n)
    toeplitz = np.zeros((n, n), dtype=np.complex128)
    toeplitz[mask] = coeffs[idx[mask]]
    return toeplitz


def build_epsilon_toeplitz_1d(
    eps_r: np.ndarray, n_harmonics: int
) -> np.ndarray:
    """构造 ε 的 Toeplitz 卷积矩阵（Li 1996 NORMAL rule，TE 偏振）。

    Args:
        eps_r: 一个周期内 ε_r 采样 (N_grid,)。
        n_harmonics: 截断阶数 N。

    Returns:
        (2N+1)×(2N+1) 复 Toeplitz 矩阵。
    """
    coeffs = fourier_coefficients_1d(eps_r, n_harmonics)
    return toeplitz_from_coefficients(coeffs)


def build_epsilon_inv_toeplitz_1d(
    eps_r: np.ndarray, n_harmonics: int
) -> np.ndarray:
    """构造 1/ε 的 Toeplitz 卷积矩阵（Li 1996 INVERSE rule，TM 偏振）。

    在介电常数间断面，D = ε·E 连续（而非 E 连续），故对 TM 偏振应使用
    1/ε 的傅里叶系数构造卷积矩阵（Li 1996 §5，Lalanne & Morris 1996）。

    Args:
        eps_r: 一个周期内 ε_r 采样 (N_grid,)。
        n_harmonics: 截断阶数 N。

    Returns:
        (2N+1)×(2N+1) 复 Toeplitz 矩阵。
    """
    eps_inv = 1.0 / np.asarray(eps_r, dtype=np.float64)
    coeffs = fourier_coefficients_1d(eps_inv, n_harmonics)
    return toeplitz_from_coefficients(coeffs)


def fourier_coefficients_2d(
    eps_r: np.ndarray, n_harmonics_x: int, n_harmonics_y: int
) -> np.ndarray:
    """计算 2D 周期介电常数的双重傅里叶系数（A01 §3.1，2D 光栅）。

    $\\varepsilon_r(x,y) = \\sum_{m,n} \\tilde{\\varepsilon}_{mn} e^{i(m K_x x + n K_y y)}$

    Args:
        eps_r: 一个周期 (Λx, Λy) 内 ε_r 的采样 (N_grid_x, N_grid_y)。
        n_harmonics_x: x 方向截断阶数 Nx。
        n_harmonics_y: y 方向截断阶数 Ny。

    Returns:
        傅里叶系数 $\\tilde{\\varepsilon}_{mn}$，形状 (2Nx+1, 2Ny+1)，
        按 [m=-Nx..+Nx, n=-Ny..+Ny] 排列。

    Raises:
        ValueError: 采样网格不足。
    """
    eps_r = np.asarray(eps_r, dtype=np.float64)
    if eps_r.ndim != 2:
        raise ValueError(f"eps_r 须为 2D 数组，实际 {eps_r.ndim}D")
    nx_grid, ny_grid = eps_r.shape
    n_need_x = 2 * n_harmonics_x + 1
    n_need_y = 2 * n_harmonics_y + 1
    if nx_grid < n_need_x or ny_grid < n_need_y:
        raise ValueError(
            f"采样网格 ({nx_grid},{ny_grid}) 不足，需 ≥({n_need_x},{n_need_y})"
        )
    full_fft = np.fft.fft2(eps_r) / (nx_grid * ny_grid)
    shifted = np.fft.fftshift(full_fft)
    cx, cy = nx_grid // 2, ny_grid // 2
    sx = cx - n_harmonics_x
    ex = cx + n_harmonics_x + 1
    sy = cy - n_harmonics_y
    ey = cy + n_harmonics_y + 1
    return shifted[sx:ex, sy:ey].astype(np.complex128)


def build_epsilon_toeplitz_2d(
    eps_r: np.ndarray, n_harmonics_x: int, n_harmonics_y: int, inverse: bool = False
) -> np.ndarray:
    """构造 2D 嵌套 Toeplitz 卷积矩阵（A01 §3.1，2D 光栅矢量 RCWA）。

    2D 卷积 $\\sum_{p,q} \\tilde{\\varepsilon}_{m-p, n-q} E_{pq}$ 对应嵌套 Toeplitz
    块矩阵，维度 (2Nx+1)(2Ny+1) × (2Nx+1)(2Ny+1)。

    Args:
        eps_r: 一个周期内 ε_r 采样 (N_grid_x, N_grid_y)。
        n_harmonics_x, n_harmonics_y: x/y 方向截断阶数。
        inverse: True 使用 1/ε（TM），False 使用 ε（TE）。

    Returns:
        (M, M) 复 Toeplitz 块矩阵，M = (2Nx+1)(2Ny+1)。
    """
    src = 1.0 / eps_r if inverse else np.asarray(eps_r, dtype=np.float64)
    coeffs_2d = fourier_coefficients_2d(src, n_harmonics_x, n_harmonics_y)
    nx_total = 2 * n_harmonics_x + 1
    ny_total = 2 * n_harmonics_y + 1
    m_total = nx_total * ny_total
    # 嵌套 Toeplitz：T[(m,n),(p,q)] = coeffs_2d[m-p+Nx, n-q+Ny]
    # 展平索引 i = (m+Nx)*ny_total + (n+Ny)，j = (p+Nx)*ny_total + (q+Ny)
    # 卷积核仅当 |m-p|≤Nx 且 |n-q|≤Ny 时非零（截断范围）
    flat = np.arange(m_total)
    mi = flat[:, None] // ny_total
    ni = flat[:, None] % ny_total
    mj = flat[None, :] // ny_total
    nj = flat[None, :] % ny_total
    dm_phys = mi - mj  # 物理差 [-2Nx, 2Nx]
    dn_phys = ni - nj
    valid = (np.abs(dm_phys) <= n_harmonics_x) & (np.abs(dn_phys) <= n_harmonics_y)
    dm_idx = dm_phys + n_harmonics_x  # → coeffs_2d 行索引 [0, 2Nx]
    dn_idx = dn_phys + n_harmonics_y  # → coeffs_2d 列索引 [0, 2Ny]
    result = np.zeros((m_total, m_total), dtype=np.complex128)
    result[valid] = coeffs_2d[dm_idx[valid], dn_idx[valid]]
    return result
