"""频域有限差分（FDFD）求解器（polaris-fdfd 内核）。

求解 2D 频域 Helmholtz 方程::

    ∇²E(x,z) + k₀² n²(x,z) E(x,z) = -b(x,z)

其中 k₀ = 2π/λ，b 为源项（线源）。

## 离散化（5 点拉普拉斯 + PML 复坐标拉伸）

构建稀疏矩阵 A = L_5pt(s) + diag(k₀²n²)，求解线性系统::

    A · E = b

使用 scipy.sparse.linalg.spsolve（UMFPACK 直接求解器）。

PML（完美匹配层）用 Berenger 1994 复坐标拉伸 s = 1 + iσ/(ωε)，
在边界渐变吸收，消除 Dirichlet 边界反射导致的驻波（旧实现场纯实数、
Poynting 流为 0、transmission 计算失真）。

## 数组布局

2D 网格 shape=(nx, nz)，C-order（row-major），flatten 后 index = i*nz + j
- x 方向（横向）: i，邻居偏移 ±nz
- z 方向（传播）: j，邻居偏移 ±1

## 传输率（Poynting 流）

T = P_out / P_in，P = ∫ S_z dx，S_z = (1/(2ωμ)) Im[E* ∂E/∂z]
（Taflove 2005 §5，复数场 Poynting 矢量 z 分量积分）。
输入监视器在源后（z=pml_n+2），输出监视器在 z=L（z=nz-1-pml_n）。

## Input / Process / Output

- I: width_um / length_um / wavelength_um / n_core / n_clad / dx_um / pad_um
- P: 构建 2D 折射率 → PML 拉伸 → 5 点拉普拉斯稀疏算子 → 高斯线源 → spsolve → Poynting 流
- O: dict{field_2d, transmission_db, n_grid, ...}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Taflove & Hagness 2005 "Computational Electrodynamics" §5.8 PML
- Shin & Fan 2014 Opt. Express https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230
- Shin & Fan 2012 J. Comput. Phys. (SC-PML) https://doi.org/10.1016/j.jcp.2012.01.015
- Berenger 1994 J. Comput. Phys. (PML 原创) https://doi.org/10.1006/jcph.1994.1159
- Gedney 1996 IEEE T-AP (uniaxial PML) https://ieeexplore.ieee.org/document/549506
- scipy.sparse.linalg.spsolve https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

__all__ = [
    "solve_fdfd",
    "build_helmholtz_operator",
    "build_line_source",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def _pml_stretch(
    n: int, pml_n: int, sigma_max: float, p: int = 3,
) -> np.ndarray:
    """PML 复坐标拉伸系数 s(i) = 1 + i·σ_max·((pml_n-d)/pml_n)^p。

    在网格两端渐变吸收（Berenger 1994 复坐标拉伸 PML），
    中心区域 s=1 不影响。d=min(i, n-1-i) 为到最近边界的距离。

    Args:
        n: 网格点数。
        pml_n: 每侧 PML 层数。
        sigma_max: 最大 σ/(ωε)（无量纲，来自 Taflove 公式）。
        p: 渐变幂次（默认 3，Taflove 2005 §5.8 推荐）。

    Returns:
        ndarray (n,) complex128: 复坐标拉伸系数。

    来源:
        Berenger 1994 J. Comput. Phys.
        https://doi.org/10.1006/jcph.1994.1159
    """
    s = np.ones(n, dtype=np.complex128)
    if pml_n <= 0 or sigma_max <= 0:
        return s
    for i in range(n):
        d = min(i, n - 1 - i)
        if d < pml_n:
            s[i] = 1.0 + 1j * sigma_max * ((pml_n - d) / pml_n) ** p
    return s


def _taflove_sigma_max(
    pml_n: int, dx: float,
    wavelength_um: float, n_ref: float,
    R: float = 1e-6, p: int = 3,
) -> float:
    """Taflove 2005 §5.8 PML σ_max 公式（无量纲 σ_max/(ωε)）。

        σ_max/(ωε) = -(p+1)·ln(R)·λ / (2π·D·n_ref)

    其中 D = pml_n·dx 为 PML 厚度，R 为目标反射率，p 为渐变幂次。

    Args:
        pml_n: PML 层数。
        dx: 步长（μm）。
        wavelength_um: 波长（μm）。
        n_ref: 参考折射率（取 n_clad）。
        R: 目标反射率（默认 1e-6）。
        p: 渐变幂次（默认 3）。

    Returns:
        float: σ_max/(ωε)（无量纲）。

    Raises:
        ValueError: 参数非法。

    来源:
        Taflove & Hagness 2005 "Computational Electrodynamics" §5.8
    """
    if pml_n <= 0 or dx <= 0 or wavelength_um <= 0 or n_ref <= 0:
        raise ValueError(
            f"PML 参数非法: pml_n={pml_n} dx={dx} "
            f"λ={wavelength_um} n_ref={n_ref}"
        )
    if not 0 < R < 1:
        raise ValueError(f"R 须在 (0,1)，得到 {R}")
    D = pml_n * dx
    return -(p + 1) * float(np.log(R)) * wavelength_um / (
        2.0 * np.pi * D * n_ref
    )


def _poynting_z(F: np.ndarray, j: int, dz: float) -> float:
    """计算 z 方向 Poynting 流积分（常数因子 1/(2ωμ) 在比值中约掉）。

        S_z(x) = Im[E*(x,j) · ∂E/∂z (x,j)]
        P = ∫ S_z dx ≈ Σ S_z(x_i) · dx

    ∂E/∂z 用中心差分 (E[j+1]-E[j-1])/(2·dz)。返回未乘 dx 的 Σ S_z
    （调用方乘 dx 得积分；常数因子在传输率比值中约掉）。

    Args:
        F: 2D 场分布 (nx, nz) 复数。
        j: z 索引（须在 [1, nz-2]）。
        dz: z 步长。

    Returns:
        float: Σ Im[E* ∂E/∂z]（正=正 z 传播）。

    Raises:
        ValueError: j 越界。

    来源:
        Taflove & Hagness 2005 §5（复 Poynting 矢量）
    """
    nx, nz = F.shape
    if j < 1 or j > nz - 2:
        raise ValueError(f"j 须在 [1, {nz-2}]，得到 {j}")
    if dz <= 0:
        raise ValueError(f"dz 须 > 0，得到 {dz}")
    dEdz = (F[:, j + 1] - F[:, j - 1]) / (2.0 * dz)
    sz = np.imag(np.conj(F[:, j]) * dEdz)
    return float(np.sum(sz))


def _validate_helmholtz_params(
    n_profile: np.ndarray,
    dx: float,
    dz: float,
    k0: float,
    pml_n: int,
) -> tuple[int, int]:
    """校验 build_helmholtz_operator 输入参数（R03 禁止 fall-back）。"""
    if n_profile.ndim != 2:
        raise ValueError(f"n_profile 须为 2D，得到 {n_profile.ndim}D")
    nx, nz = n_profile.shape
    if nx < 3 or nz < 3:
        raise ValueError(f"网格过小 {nx}×{nz}，须 >= 3×3")
    if dx <= 0 or dz <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dz={dz}")
    if k0 <= 0:
        raise ValueError(f"k0 须 > 0，得到 {k0}")
    if pml_n < 0:
        raise ValueError(f"pml_n 须 >= 0，得到 {pml_n}")
    return nx, nz


def build_helmholtz_operator(
    n_profile: np.ndarray,
    dx: float, dz: float,
    k0: float,
    pml_n: int = 0,
    sigma_max: float = 0.0,
) -> sparse.csr_matrix:
    """构建 2D Helmholtz 稀疏算子 A = L_5pt(s) + diag(k₀²n²)。

    数组布局: shape=(nx, nz)，C-order，flatten 后 index = i*nz + j。
    当 pml_n > 0 时启用 PML 复坐标拉伸（Berenger 1994 / Shin & Fan 2012），
    pml_n=0 时退化为 Dirichlet 边界实数矩阵（向后兼容）。

    Args:
        n_profile: 2D 折射率分布 (nx, nz)。
        dx, dz: 网格步长（μm）。
        k0: 真空波数（μm⁻¹）。
        pml_n: 每侧 PML 层数（0=禁用 PML）。
        sigma_max: PML 最大 σ/(ωε)（pml_n=0 时忽略）。

    Returns:
        scipy.sparse.csr_matrix (nx*nz, nx*nz)。

    Raises:
        ValueError: 参数非法。

    来源: Shin & Fan 2012 J. Comput. Phys. (SC-PML)
        https://doi.org/10.1016/j.jcp.2012.01.015
    """
    nx, nz = _validate_helmholtz_params(n_profile, dx, dz, k0, pml_n)
    n = nx * nz
    use_pml = pml_n > 0
    dtype = np.complex128 if use_pml else np.float64

    if use_pml:
        sx = _pml_stretch(nx, pml_n, sigma_max)
        sz = _pml_stretch(nz, pml_n, sigma_max)
        # 每个网格点 (i,j) 的拉伸系数: cx[i], cz[j]
        coeff_x = 1.0 / (sx * sx * dx * dx)        # (nx,)
        coeff_z = 1.0 / (sz * sz * dz * dz)        # (nz,)
        # 展平到 n 个网格点: index = i*nz + j
        cx_flat = np.repeat(coeff_x, nz)           # (n,)
        cz_flat = np.tile(coeff_z, nx)             # (n,)
        main_diag = -2.0 * (cx_flat + cz_flat)
        off_x = np.repeat(coeff_x[:-1], nz)        # (n-nz,)
        off_z = np.tile(coeff_z, nx)[:n - 1]       # (n-1,)
    else:
        inv_dx2 = 1.0 / (dx * dx)
        inv_dz2 = 1.0 / (dz * dz)
        main_diag = np.full(n, -2.0 * (inv_dx2 + inv_dz2), dtype=dtype)
        off_x = np.full(n - nz, inv_dx2, dtype=dtype)
        off_z = np.full(n - 1, inv_dz2, dtype=dtype)

    # z 方向偏移 ±1，每行末尾清零（防止 x 方向 wrap）
    for i in range(nx - 1):
        off_z[(i + 1) * nz - 1] = 0.0

    L = sparse.diags(
        [off_x, off_z, main_diag, off_z, off_x],
        [-nz, -1, 0, 1, nz],
        format="csr",
        dtype=dtype,
    )
    # 加折射率项: diag(k₀²n²)
    k0_sq = k0 * k0
    n_sq = n_profile.flatten() ** 2
    A = L + sparse.diags(k0_sq * n_sq, 0, format="csr", dtype=dtype)
    return A


def build_line_source(
    nx: int, nz: int,
    dx: float,
    source_z_idx: int,
    center_x_um: float,
    waist_um: float,
) -> np.ndarray:
    """构建高斯线源（z=source_z_idx 处的横向高斯分布）。

    b[i, source_z_idx] = exp(-(x_i - center)² / waist²)，其余位置为 0。

    Args:
        nx, nz: 网格点数。
        dx: 横向步长（μm）。
        source_z_idx: 源在 z 方向的索引。
        center_x_um: 源横向中心位置（μm，相对窗口起点）。
        waist_um: 高斯腰斑（μm）。

    Returns:
        ndarray (nx*nz,): 展平的源向量。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or nz < 3:
        raise ValueError(f"网格过小 {nx}×{nz}")
    if dx <= 0:
        raise ValueError(f"dx 须 > 0，得到 {dx}")
    if not 0 <= source_z_idx < nz:
        raise ValueError(
            f"source_z_idx 须在 [0, {nz})，得到 {source_z_idx}"
        )
    if waist_um <= 0:
        raise ValueError(f"waist_um 须 > 0，得到 {waist_um}")

    x = np.arange(nx) * dx
    gaussian = np.exp(-((x - center_x_um) ** 2) / (waist_um ** 2))
    # 归一化: max|b| = 1
    g_max = float(np.max(np.abs(gaussian)))
    if g_max > 0:
        gaussian = gaussian / g_max

    b = np.zeros(nx * nz, dtype=np.complex128)
    for i in range(nx):
        b[i * nz + source_z_idx] = gaussian[i]
    return b


def _validate_fdfd_params(
    width_um: float,
    length_um: float,
    wavelength_um: float,
    n_core: float,
    n_clad: float,
    dx_um: float,
    pad_um: float,
) -> None:
    """校验 solve_fdfd 输入参数（R03 禁止 fall-back）。"""
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if length_um <= 0:
        raise ValueError(f"length_um 须 > 0，得到 {length_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(f"n_core ({n_core}) 须 > n_clad ({n_clad})")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(f"dx_um ({dx_um}) 须 < width_um ({width_um})")
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")


def _build_fdfd_grid_and_source(
    width_um: float,
    length_um: float,
    dx_um: float,
    pad_um: float,
    n_core: float,
    n_clad: float,
    wavelength_um: float,
) -> tuple:
    """构建 FDFD 网格、折射率分布、Helmholtz 算子与高斯线源。

    R05 修复: 网格点数 = 间隔数 + 1（N = int(W/dx) + 1），
    保证 (N-1)*dx 精确等于窗口物理尺寸。
    """
    window_x_um = width_um + 2.0 * pad_um
    nx = int(window_x_um / dx_um) + 1
    nz = int(length_um / dx_um) + 1
    if nx < 5 or nz < 5:
        raise ValueError(f"网格过小 {nx}×{nz}，请减小 dx_um 或增大尺寸")
    dx = float(dx_um)
    dz = float(dx_um)
    core_x0 = int(round(pad_um / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    if core_x0 < 1 or core_x1 > nx - 1:
        raise ValueError(
            f"芯区索引越界: x=[{core_x0},{core_x1}) 网格 {nx}×{nz}"
        )
    n_profile = np.full((nx, nz), n_clad, dtype=np.float64)
    n_profile[core_x0:core_x1, :] = n_core
    k0 = 2.0 * np.pi / wavelength_um
    # PML 参数（Taflove 2005 §5.8）: 4~10 层，σ_max 用 Taflove 公式 R=1e-6
    pml_n = max(4, min(10, (min(nx, nz) - 1) // 4))
    sigma_max = _taflove_sigma_max(pml_n, dx, wavelength_um, n_clad)
    A = build_helmholtz_operator(
        n_profile, dx, dz, k0, pml_n=pml_n, sigma_max=sigma_max,
    )
    source_z_idx = pml_n
    center_x_um = window_x_um / 2.0
    waist_um = max(width_um, wavelength_um)
    b = build_line_source(nx, nz, dx, source_z_idx, center_x_um, waist_um)
    return (nx, nz, dx, dz, core_x0, core_x1, window_x_um,
            k0, pml_n, sigma_max, A, b, source_z_idx)


def _solve_fdfd_extract_transmission(
    A: sparse.csr_matrix,
    b: np.ndarray,
    nx: int,
    nz: int,
    dz: float,
    dx: float,
    pml_n: int,
    source_z_idx: int,
) -> tuple:
    """求解 A·E = b 并提取场分布与传输率（Poynting 流）。

    T = P_out/P_in, P = ∫ S_z dx, S_z = (1/(2ωμ)) Im[E* ∂E/∂z]。
    常数因子在比值中约掉，故只算 Σ Im[E* ∂E/∂z]·dx。
    """
    try:
        E_flat = spsolve(A.tocsc(), b)
    except Exception as e:
        raise RuntimeError(
            f"spsolve 求解失败: {e}（R03 禁止 fall-back）"
        ) from e
    if np.any(np.isnan(E_flat)) or np.any(np.isinf(E_flat)):
        raise RuntimeError("FDFD 求解结果含 NaN/Inf（R03 禁止 fall-back）")
    field_2d = E_flat.reshape(nx, nz)
    input_z_idx = source_z_idx + 2
    output_z_idx = nz - 1 - pml_n
    if output_z_idx <= input_z_idx:
        raise RuntimeError(
            f"监视器位置异常 input={input_z_idx} >= output={output_z_idx}"
            f"（网格或 PML 过大，R03）"
        )
    p_source = _poynting_z(field_2d, input_z_idx, dz) * dx
    p_output = _poynting_z(field_2d, output_z_idx, dz) * dx
    if p_source <= 0:
        raise RuntimeError(
            f"输入 Poynting 流 {p_source} <= 0（R03 禁止 fall-back）"
        )
    transmission = p_output / p_source
    if transmission < 0:
        raise RuntimeError(f"transmission={transmission} < 0，物理异常（R03）")
    transmission_db = 10.0 * float(np.log10(max(transmission, 1e-30)))
    return (field_2d, transmission, transmission_db, p_output, p_source,
            input_z_idx, output_z_idx)


def solve_fdfd(
    width_um: float = 0.5,
    length_um: float = 10.0,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    dx_um: float = 0.05,
    pad_um: float = 1.5,
) -> dict:
    """2D 频域有限差分求解器。

    在 2D x-z 平面（x 横向，z 传播方向）求解 Helmholtz 方程，
    使用高斯线源激发，scipy.sparse.linalg.spsolve 求解稳态场。

    Args:
        width_um: 波导芯宽度（μm，横向）。
        length_um: 传播长度（μm，z 方向）。
        wavelength_um: 波长（μm）。
        n_core: 芯区折射率（Si 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 1.444，Soref 1993）。
        dx_um: 横向步长（μm）。
        pad_um: 包层 padding（μm，每侧）。

    Returns:
        dict: {field_2d, transmission_db, n_grid, ...}
            - field_2d: 稳态场分布 (nx, nz)（复数）
            - transmission_db: 输出端传输率（dB）
            - n_grid: 总网格点数

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 求解失败或结果含 NaN（R03）。

    来源:
        - Taflove & Hagness 2005（FDFD 第 5 章）
        - Shin & Fan 2014 Opt. Express
        - scipy.sparse.linalg.spsolve
    """
    _validate_fdfd_params(
        width_um, length_um, wavelength_um, n_core, n_clad, dx_um, pad_um
    )
    (nx, nz, dx, dz, core_x0, core_x1, window_x_um, k0, pml_n, sigma_max,
     A, b, source_z_idx) = _build_fdfd_grid_and_source(
        width_um, length_um, dx_um, pad_um, n_core, n_clad, wavelength_um
    )
    (field_2d, transmission, transmission_db, p_output, p_source,
     input_z_idx, output_z_idx) = _solve_fdfd_extract_transmission(
        A, b, nx, nz, dz, dx, pml_n, source_z_idx
    )
    return {
        "field_2d": field_2d.tolist(),
        "transmission": float(transmission),
        "transmission_db": transmission_db,
        "p_output": p_output,
        "p_source": p_source,
        "n_grid": int(nx * nz),
        "wavelength_um": float(wavelength_um),
        "grid_info": {
            "nx": nx,
            "nz": nz,
            "dx_um": float(dx),
            "dz_um": float(dz),
            "window_x_um": float(window_x_um),
            "length_um": float(length_um),
            "core_x": [core_x0, core_x1],
            "source_z_idx": source_z_idx,
            "input_z_idx": input_z_idx,
            "output_z_idx": output_z_idx,
            "pml_n": pml_n,
            "sigma_max": float(sigma_max),
        },
        "physics": {
            "k0": float(k0),
            "n_core": float(n_core),
            "n_clad": float(n_clad),
        },
    }
