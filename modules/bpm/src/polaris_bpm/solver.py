"""Crank-Nicolson BPM 求解器（polaris-bpm 内核）。

求解抛物波动方程（paraxial wave equation，1D 横向）::

    ∂E/∂z = (j/(2k₀n₀)) ∂²E/∂x² + j·k₀(n²(x) - n₀²)/(2n₀) E

其中 n₀ 为参考折射率（通常取包层 n_clad），k₀ = 2π/λ。

## Crank-Nicolson 隐式格式

将方程写为 ∂E/∂z = H·E，其中::

    H = (j/(2k₀n₀)) L_x + j·k₀(n²-n₀²)/(2n₀) I

Crank-Nicolson 时间步进::

    (I - dz·H/2) E^{n+1} = (I + dz·H/2) E^n

LHS 和 RHS 均为三对角矩阵，可用 scipy.linalg.solve_banded 高效求解 O(N)。

## 稳定性

Crank-Nicolson 格式无条件稳定（Crank & Nicolson 1947），任意 dz 都不发散。
但精度要求 dz << λ（典型 dz = 0.1μm）。

## ADI 扩展（2D 横向）

2D 横向时用 ADI（Alternating Direction Implicit）分裂（Chung & Dagli 1990）:
- x-half-step: (I - dz·Hx/2) E* = (I + dz·Hy/2) E^n
- y-half-step: (I - dz·Hy/2) E^{n+1} = (I + dz·Hx/2) E*
本模块当前实现 1D 横向，ADI 为 2D 扩展接口。

## Input / Process / Output

- I: width_um / length_um / wavelength_um / n_core / n_clad / dz_um / dx_um / pad_um
- P: 构建 1D 折射率 → CN 三对角矩阵 → 高斯源 → 逐步求解
- O: dict{field_z, transmission_db, n_steps, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Feit & Fleck 1978 Appl. Opt. https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947 Math. Proc. Cambridge
- Lumerical varFDTD https://optics.ansys.com/hc/en-us/articles/360034902433
- scipy.linalg.solve_banded https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
- Chung & Dagli 1990 IEEE JQE https://ieeexplore.ieee.org/document/59635
- Hadley 1992 Opt. Lett. https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import solve_banded

__all__ = [
    "solve_bpm",
    "build_cn_matrices",
    "gaussian_source",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def gaussian_source(
    nx: int, dx: float, center_um: float, waist_um: float,
) -> np.ndarray:
    """构建高斯光束源（BPM 初始场）。

    E(x) = exp(-(x - x₀)² / w²)

    Args:
        nx: 网格点数。
        dx: 网格步长（μm）。
        center_um: 光束中心位置（μm，相对窗口起点）。
        waist_um: 光束腰斑半径（μm）。

    Returns:
        ndarray (nx,): 复数高斯场（功率归一化 ∫|E|²dx = 1）。

    Raises:
        ValueError: 参数非法（R03）。
    """
    if nx < 3:
        raise ValueError(f"nx 须 >= 3，得到 {nx}")
    if dx <= 0:
        raise ValueError(f"dx 须 > 0，得到 {dx}")
    if waist_um <= 0:
        raise ValueError(f"waist_um 须 > 0，得到 {waist_um}")
    if center_um < 0 or center_um > nx * dx:
        raise ValueError(
            f"center_um 须在 [0, {nx*dx}]，得到 {center_um}"
        )
    x = np.arange(nx) * dx
    field = np.exp(-((x - center_um) ** 2) / (waist_um ** 2))
    # 功率归一化: ∫|E|²dx = 1
    norm = float(np.sqrt(np.sum(np.abs(field) ** 2) * dx))
    if norm > 0:
        field = field / norm
    return field.astype(np.complex128)


def build_cn_matrices(
    n_profile: np.ndarray,
    dx: float,
    dz: float,
    k0: float,
    n0: float,
) -> tuple[np.ndarray, np.ndarray]:
    """构建 Crank-Nicolson 三对角矩阵（banded 形式）。

    LHS: A = I - dz·H/2
    RHS: B = I + dz·H/2
    其中 H = (j/(2k₀n₀)) L_x + j·k₀(n²-n₀²)/(2n₀) I

    Args:
        n_profile: 1D 折射率分布 (nx,)。
        dx: 横向步长（μm）。
        dz: 纵向步长（μm）。
        k0: 真空波数（μm⁻¹）。
        n0: 参考折射率。

    Returns:
        tuple: (A_banded, B_diag)
            A_banded: (3, nx) banded 矩阵（用于 solve_banded）
            B_diag: (nx,) 对角矩阵的对角元素（RHS 仅需点乘）

    Raises:
        ValueError: 参数非法。
    """
    nx = len(n_profile)
    if nx < 3:
        raise ValueError(f"n_profile 长度须 >= 3，得到 {nx}")
    if dx <= 0:
        raise ValueError(f"dx 须 > 0，得到 {dx}")
    if dz <= 0:
        raise ValueError(f"dz 须 > 0，得到 {dz}")
    if k0 <= 0:
        raise ValueError(f"k0 须 > 0，得到 {k0}")
    if n0 <= 0:
        raise ValueError(f"n0 须 > 0，得到 {n0}")

    inv_dx2 = 1.0 / (dx * dx)
    # H 的二阶导系数: j/(2k₀n₀) · 1/dx²
    coef_lap = 1j / (2.0 * k0 * n0) * inv_dx2
    # H 的折射率项: j·k₀(n²-n₀²)/(2n₀)
    coef_n = 1j * k0 * (n_profile ** 2 - n0 ** 2) / (2.0 * n0)

    # Crank-Nicolson: A = I - dz/2 · H, B = I + dz/2 · H
    # H 的三对角: 主对角 = -2·coef_lap + coef_n, 上下副对角 = coef_lap
    h_main = -2.0 * coef_lap + coef_n
    h_off = coef_lap  # ±1 偏移

    # A = I - dz/2 · H
    a_main = 1.0 - 0.5 * dz * h_main
    a_off = -0.5 * dz * h_off

    # B = I + dz/2 · H（仅对角，因为 RHS 是矩阵-向量乘，banded 也可）
    b_main = 1.0 + 0.5 * dz * h_main
    b_off = 0.5 * dz * h_off

    # solve_banded 的 ab 格式: ab[u+i-j, j] = a[i,j]
    # 三对角: ab[0] = 上副对角（最后一个元素无用），ab[1] = 主对角，ab[2] = 下副对角
    A_banded = np.zeros((3, nx), dtype=np.complex128)
    A_banded[0, 1:] = a_off       # 上副对角（ab[0,1:nx] = a[i, i+1]）
    A_banded[1, :] = a_main       # 主对角
    A_banded[2, :-1] = a_off      # 下副对角（ab[2,0:nx-1] = a[i+1, i]）

    # 边界条件: Dirichlet E=0（首末行只保留对角）
    A_banded[0, 1] = 0.0  # (0,1) 处的耦合
    A_banded[2, -2] = 0.0  # (nx-1, nx-2) 处的耦合
    A_banded[1, 0] = 1.0   # 首行: E[0] = 0
    A_banded[1, -1] = 1.0  # 末行: E[nx-1] = 0

    # B 也用 banded 形式（便于矩阵-向量乘）
    B_banded = np.zeros((3, nx), dtype=np.complex128)
    B_banded[0, 1:] = b_off
    B_banded[1, :] = b_main
    B_banded[2, :-1] = b_off
    B_banded[0, 1] = 0.0
    B_banded[2, -2] = 0.0
    B_banded[1, 0] = 0.0
    B_banded[1, -1] = 0.0

    return A_banded, B_banded


def solve_bpm(
    width_um: float = 0.5,
    length_um: float = 50.0,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    dz_um: float = 0.1,
    dx_um: float = 0.01,
    pad_um: float = 2.0,
) -> dict:
    """1D Crank-Nicolson BPM 求解器。

    在硅条形波导（n_core 芯 / n_clad 包层）中传播高斯光束，
    使用 Crank-Nicolson 隐式格式逐步求解抛物波动方程。

    Args:
        width_um: 波导芯宽度（μm）。
        length_um: 传播长度（μm）。
        wavelength_um: 波长（μm）。
        n_core: 芯区折射率（Si 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 1.444，Soref 1993）。
        dz_um: 纵向步长（μm）。
        dx_um: 横向步长（μm）。
        pad_um: 包层 padding（μm，每侧）。

    Returns:
        dict: {field_z, transmission_db, n_steps, grid_info, ...}
            - field_z: 末态场分布 (nx,)（复数）
            - transmission_db: 传输率（dB，末态功率/初态功率）
            - n_steps: 实际步数
            - grid_info: {nx, dx_um, dz_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 求解失败或结果含 NaN（R03）。

    来源:
        - Feit & Fleck 1978（BPM）
        - Crank & Nicolson 1947（隐式格式）
        - Chung & Dagli 1990（ADI 扩展）
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
    if dz_um <= 0:
        raise ValueError(f"dz_um 须 > 0，得到 {dz_um}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(f"dx_um ({dx_um}) 须 < width_um ({width_um})")
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    window_um = width_um + 2.0 * pad_um
    nx = int(round(window_um / dx_um))
    if nx < 5:
        raise ValueError(f"网格过小 nx={nx}，请减小 dx_um 或增大 pad_um")
    dx = window_um / nx
    nz = int(round(length_um / dz_um))
    if nz < 1:
        raise ValueError(f"步数过少 nz={nz}，请增大 length_um 或减小 dz_um")
    dz = length_um / nz

    # 芯区索引（居中）
    core_x0 = int(round((window_um - width_um) / 2.0 / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    if core_x0 < 1 or core_x1 > nx - 1:
        raise ValueError(
            f"芯区索引越界: x=[{core_x0},{core_x1}) 网格 {nx}"
        )

    # ---- 折射率分布 ----
    n_profile = np.full(nx, n_clad, dtype=np.float64)
    n_profile[core_x0:core_x1] = n_core

    # ---- 物理参数 ----
    k0 = 2.0 * np.pi / wavelength_um  # 真空波数（μm⁻¹）
    n0 = n_clad  # 参考折射率（取包层）

    # ---- 构建 Crank-Nicolson 矩阵 ----
    A_banded, B_banded = build_cn_matrices(n_profile, dx, dz, k0, n0)

    # ---- 初始场: 高斯光束（中心对准波导） ----
    center_um = window_um / 2.0
    # 腰斑 ≈ 波导宽度（耦合到基模）
    waist_um = max(width_um, wavelength_um)
    field = gaussian_source(nx, dx, center_um, waist_um)
    # 强制边界为 0（Dirichlet）
    field[0] = 0.0
    field[-1] = 0.0

    # 初始功率
    p_initial = float(np.sum(np.abs(field) ** 2) * dx)

    # ---- 逐步求解 ----
    for _ in range(nz):
        # RHS: b = B · E^n
        # B 是 banded 三对角，用矩阵-向量乘
        rhs = np.zeros(nx, dtype=np.complex128)
        rhs[:] = B_banded[1, :] * field
        rhs[1:] += B_banded[0, 1:] * field[:-1]  # 上副对角
        rhs[:-1] += B_banded[2, :-1] * field[1:]  # 下副对角
        # 强制边界
        rhs[0] = 0.0
        rhs[-1] = 0.0
        # 求解 A · E^{n+1} = rhs
        field = solve_banded((1, 1), A_banded, rhs)
        # NaN 校验
        if np.any(np.isnan(field)):
            raise RuntimeError(
                "BPM 求解出现 NaN（R03 禁止 fall-back）"
            )

    # ---- 输出 ----
    p_final = float(np.sum(np.abs(field) ** 2) * dx)
    if p_initial <= 0:
        raise RuntimeError(
            f"初始功率 {p_initial} <= 0（R03 禁止 fall-back）"
        )
    transmission = p_final / p_initial
    transmission_db = 10.0 * float(np.log10(max(transmission, 1e-30)))

    return {
        "field_z": field.tolist(),
        "transmission": float(transmission),
        "transmission_db": transmission_db,
        "p_initial": p_initial,
        "p_final": p_final,
        "n_steps": int(nz),
        "wavelength_um": float(wavelength_um),
        "grid_info": {
            "nx": nx,
            "nz": nz,
            "dx_um": float(dx),
            "dz_um": float(dz),
            "window_um": float(window_um),
            "core_x": [core_x0, core_x1],
        },
        "physics": {
            "k0": float(k0),
            "n0": float(n0),
            "n_core": float(n_core),
            "n_clad": float(n_clad),
        },
    }
