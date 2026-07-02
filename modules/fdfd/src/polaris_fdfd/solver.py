"""频域有限差分（FDFD）求解器（polaris-fdfd 内核）。

求解 2D 频域 Helmholtz 方程::

    ∇²E(x,z) + k₀² n²(x,z) E(x,z) = -b(x,z)

其中 k₀ = 2π/λ，b 为源项（线源）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

构建稀疏矩阵 A = L_5pt + diag(k₀²n²)，求解线性系统::

    A · E = b

使用 scipy.sparse.linalg.spsolve（UMFPACK 直接求解器）。

## 数组布局

2D 网格 shape=(nx, nz)，C-order（row-major），flatten 后 index = i*nz + j
- x 方向（横向）: i，邻居偏移 ±nz
- z 方向（传播）: j，邻居偏移 ±1

## Input / Process / Output

- I: width_um / length_um / wavelength_um / n_core / n_clad / dx_um / pad_um
- P: 构建 2D 折射率 → 5 点拉普拉斯稀疏算子 → 高斯线源 → spsolve
- O: dict{field_2d, transmission_db, n_grid, ...}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Taflove & Hagness 2005 "Computational Electrodynamics"
- Shin & Fan 2014 Opt. Express https://opg.optica.org/oe/abstract.cfm?uri=oe-22-5-5230
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


def build_helmholtz_operator(
    n_profile: np.ndarray,
    dx: float, dz: float,
    k0: float,
) -> sparse.csr_matrix:
    """构建 2D Helmholtz 稀疏算子 A = L_5pt + diag(k₀²n²)。

    数组布局: shape=(nx, nz)，C-order，flatten 后 index = i*nz + j
    - x 方向邻居 (i±1, j): 偏移 ±nz，系数 1/dx²
    - z 方向邻居 (i, j±1): 偏移 ±1，系数 1/dz²

    Args:
        n_profile: 2D 折射率分布 (nx, nz)。
        dx, dz: 网格步长（μm）。
        k0: 真空波数（μm⁻¹）。

    Returns:
        scipy.sparse.csr_matrix (nx*nz, nx*nz): Helmholtz 算子。

    Raises:
        ValueError: 参数非法。
    """
    nx, nz = n_profile.shape
    if nx < 3 or nz < 3:
        raise ValueError(f"网格过小 {nx}×{nz}，须 >= 3×3")
    if dx <= 0 or dz <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dz={dz}")
    if k0 <= 0:
        raise ValueError(f"k0 须 > 0，得到 {k0}")

    n = nx * nz
    inv_dx2 = 1.0 / (dx * dx)
    inv_dz2 = 1.0 / (dz * dz)
    diag_main = -2.0 * (inv_dx2 + inv_dz2)

    main_diag = np.full(n, diag_main, dtype=np.float64)
    # z 方向偏移 ±1，每行末尾清零（防止 x 方向 wrap）
    off_z = np.full(n - 1, inv_dz2, dtype=np.float64)
    for i in range(nx - 1):
        off_z[(i + 1) * nz - 1] = 0.0
    # x 方向偏移 ±nz
    off_x = np.full(n - nz, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_z, main_diag, off_z, off_x],
        [-nz, -1, 0, 1, nz],
        format="csr",
        dtype=np.float64,
    )
    # 加折射率项: diag(k₀²n²)
    k0_sq = k0 * k0
    n_sq = n_profile.flatten() ** 2
    A = L + sparse.diags(k0_sq * n_sq, 0, format="csr")
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
    # ---- 参数校验（R03） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if length_um <= 0:
        raise ValueError(f"length_um 须 > 0，得到 {length_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})"
        )
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(f"dx_um ({dx_um}) 须 < width_um ({width_um})")
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    window_x_um = width_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    nz = int(round(length_um / dx_um))
    if nx < 5 or nz < 5:
        raise ValueError(
            f"网格过小 {nx}×{nz}，请减小 dx_um 或增大尺寸"
        )
    dx = window_x_um / nx
    dz = length_um / nz

    # 芯区索引（横向居中，z 方向全覆盖）
    core_x0 = int(round(pad_um / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    if core_x0 < 1 or core_x1 > nx - 1:
        raise ValueError(
            f"芯区索引越界: x=[{core_x0},{core_x1}) 网格 {nx}×{nz}"
        )

    # ---- 折射率分布 ----
    n_profile = np.full((nx, nz), n_clad, dtype=np.float64)
    n_profile[core_x0:core_x1, :] = n_core

    # ---- 物理参数 ----
    k0 = 2.0 * np.pi / wavelength_um

    # ---- 构建 Helmholtz 算子 ----
    A = build_helmholtz_operator(n_profile, dx, dz, k0)

    # ---- 构建源（高斯线源在 z=1 处，避开边界） ----
    source_z_idx = 1
    center_x_um = window_x_um / 2.0  # 波导中心
    waist_um = max(width_um, wavelength_um)
    b = build_line_source(
        nx, nz, dx, source_z_idx, center_x_um, waist_um,
    )

    # ---- 求解 A·E = b ----
    try:
        E_flat = spsolve(A.tocsc(), b)
    except Exception as e:
        raise RuntimeError(
            f"spsolve 求解失败: {e}（R03 禁止 fall-back）"
        ) from e

    # NaN 校验（R03）
    if np.any(np.isnan(E_flat)) or np.any(np.isinf(E_flat)):
        raise RuntimeError("FDFD 求解结果含 NaN/Inf（R03 禁止 fall-back）")

    # ---- 重塑为 2D 场 ----
    field_2d = E_flat.reshape(nx, nz)

    # ---- 提取传输率 ----
    # 输出端: z = nz - 2（避开边界）
    output_z_idx = nz - 2
    output_field = field_2d[core_x0:core_x1, output_z_idx]
    p_output = float(np.sum(np.abs(output_field) ** 2) * dx)
    # 源功率
    source_field = b.reshape(nx, nz)[:, source_z_idx]
    p_source = float(np.sum(np.abs(source_field) ** 2) * dx)
    if p_source <= 0:
        raise RuntimeError(
            f"源功率 {p_source} <= 0（R03 禁止 fall-back）"
        )
    transmission = p_output / p_source
    transmission_db = 10.0 * float(np.log10(max(transmission, 1e-30)))

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
            "output_z_idx": output_z_idx,
        },
        "physics": {
            "k0": float(k0),
            "n_core": float(n_core),
            "n_clad": float(n_clad),
        },
    }
