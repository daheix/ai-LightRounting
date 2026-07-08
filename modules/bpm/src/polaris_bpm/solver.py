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

## 传输率 BUG 修复（split-step BPM，2026-07）

CN 格式对反厄米 H（实折射率）严格功率守恒：A†A = B†B = I-(dz/2)²H²，
内点子矩阵在 Dirichlet 截断后仍反厄米，能量不"漏出"系统而被反射回波导，
导致 transmission ≡ 1.0（dB≈0）。这是 BPM 数值方法在无损耗设置的理论预测，
并非提取逻辑 BUG。

引入 split-step 物理损耗（RP Photonics 标准方案）:
1. **Soref 材料吸收**（芯区均匀功率衰减 α_p，Soref 1993 SOI 3 dB/cm）
2. **CAP 吸收边界层**（pad 外侧平方渐变衰减，吸收辐射模避免 Dirichlet 反射）

每步: E^{n+1} = exp(-α·dz/2) · CN(E^n) · exp(-α·dz/2)  (symmetric split, O(dz³))

## ADI 扩展（2D 横向）

2D 横向时用 ADI（Alternating Direction Implicit）分裂（Chung & Dagli 1990）:
- x-half-step: (I - dz·Hx/2) E* = (I + dz·Hy/2) E^n
- y-half-step: (I - dz·Hy/2) E^{n+1} = (I + dz·Hx/2) E*
本模块当前实现 1D 横向，ADI 为 2D 扩展接口。

## Input / Process / Output

- I: width_um / length_um / wavelength_um / n_core / n_clad / dz_um / dx_um / pad_um
- P: 构建 1D 折射率 → CN 三对角矩阵 → 高斯源 → split-step 逐步求解
- O: dict{field_z, transmission_db, n_steps, grid_info, alpha_profile}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Feit & Fleck 1978 Appl. Opt. https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947 Math. Proc. Cambridge
- Lumerical varFDTD https://optics.ansys.com/hc/en-us/articles/360034902433
- scipy.linalg.solve_banded https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
- Chung & Dagli 1990 IEEE JQE https://ieeexplore.ieee.org/document/59635
- Hadley 1992 Opt. Lett. (TBC/CAP 边界) https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
- Soref R.A. 1993 Proc. IEEE 81(12) "Silicon-based optoelectronics"
  https://ieeexplore.ieee.org/document/249720
- Rickman & Reed 1994 Electron. Lett. 30(10) (SOI 0.5 dB/cm 实测)
  https://digital-library.theiet.org/doi/abs/10.1049/el:19931356
- Grillot 2006 JLT 24(2) (SOI 条形波导损耗 1-10 dB/cm)
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-24-2-891
- RP Photonics BPM 边界处理
  https://www.rp-photonics.com/numerical_beam_propagation.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import solve_banded

__all__ = [
    "solve_bpm",
    "build_cn_matrices",
    "gaussian_source",
    "build_loss_profile",
    "C0",
    "LOSS_DB_PER_CM_SI",
    "CAP_STRENGTH",
    "CAP_FRACTION",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0

# Soref 1993 SOI 波导传播损耗 (dB/cm) — SOI 条形波导保守典型上界
# 来源 (R02):
# - Soref R.A. 1993 Proc. IEEE 81(12) "Silicon-based optoelectronics"
#   https://ieeexplore.ieee.org/document/249720
# - Rickman & Reed 1994 Electron. Lett. 30(10) (SOI 脊形 0.5 dB/cm 实测)
#   https://digital-library.theiet.org/doi/abs/10.1049/el:19931356
# - Grillot 2006 JLT 24(2) (SOI 条形波导损耗 1-10 dB/cm，依赖侧壁粗糙度)
#   https://opg.optica.org/jlt/abstract.cfm?uri=jlt-24-2-891
LOSS_DB_PER_CM_SI: float = 3.0

# 吸收边界层 (Complex Absorbing Potential) 参数
# 在 pad 外侧 CAP_FRACTION 区域加平方渐变振幅衰减系数，吸收辐射模
# 避免 Dirichlet 边界把辐射模反射回波导导致 transmission≡1（CN 严格守恒）
# 来源 (R02):
# - Hadley 1992 Opt. Lett. 17(10) 726 (TBC 透明边界条件)
#   https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
# - RP Photonics BPM 边界处理
#   https://www.rp-photonics.com/numerical_beam_propagation.html
CAP_STRENGTH: float = 0.5  # 边界处最大功率衰减系数 α (μm⁻¹)
CAP_FRACTION: float = 0.3  # pad 外侧比例作为 CAP


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


def _validate_loss_profile_params(
    nx: int, core_x0: int, core_x1: int, pad_pts: int,
    loss_db_per_cm: float, cap_strength: float, cap_fraction: float,
) -> None:
    """校验 build_loss_profile 入参（R03 禁止 fall-back）。"""
    if nx < 3:
        raise ValueError(f"nx 须 >= 3，得到 {nx}")
    if not (0 <= core_x0 <= core_x1 <= nx):
        raise ValueError(f"芯区索引非法: [{core_x0},{core_x1}) 网格 {nx}")
    if pad_pts < 0:
        raise ValueError(f"pad_pts 须 >= 0，得到 {pad_pts}")
    if loss_db_per_cm < 0:
        raise ValueError(f"loss_db_per_cm 须 >= 0，得到 {loss_db_per_cm}")
    if cap_strength < 0:
        raise ValueError(f"cap_strength 须 >= 0，得到 {cap_strength}")
    if not (0.0 <= cap_fraction <= 1.0):
        raise ValueError(f"cap_fraction 须 ∈ [0,1]，得到 {cap_fraction}")


def _apply_cap_boundary(
    alpha: np.ndarray, nx: int, pad_pts: int,
    cap_strength: float, cap_fraction: float,
) -> None:
    """CAP 吸收边界层: pad 外侧 cap_fraction 加平方渐变 α_cap(t)=cap·t²。

    t ∈ [0,1]: 内侧 0 → 边界 1（除以 cap_pts-1 保证边界恰为 1）。
    来源: Hadley 1992 Opt. Lett. TBC/CAP 边界。
    """
    if cap_strength > 0 and cap_fraction > 0:
        cap_pts = int(round(pad_pts * cap_fraction))
        if cap_pts >= 2:
            t = np.arange(cap_pts, dtype=np.float64) / (cap_pts - 1)
            ramp = cap_strength * (t ** 2)
            # 左侧: 内侧 t=0 → 边界 t=1
            alpha[:cap_pts] = np.maximum(alpha[:cap_pts], ramp[::-1])
            # 右侧: 内侧 t=0 → 边界 t=1
            alpha[nx - cap_pts:] = np.maximum(alpha[nx - cap_pts:], ramp)


def build_loss_profile(
    nx: int,
    core_x0: int,
    core_x1: int,
    pad_pts: int,
    loss_db_per_cm: float = LOSS_DB_PER_CM_SI,
    cap_strength: float = CAP_STRENGTH,
    cap_fraction: float = CAP_FRACTION,
) -> np.ndarray:
    """构建功率衰减系数分布 α(x) (μm⁻¹)。

    用于 split-step BPM 的振幅衰减步: |E| *= exp(-α·dz/2)。
    功率衰减: P(z) = P(0)·exp(-α·z)。

    分布构成:
    - 芯区 [core_x0, core_x1): Soref 1993 SOI 材料吸收损耗（均匀 α_core）
    - pad 外侧 cap_fraction 比例: 平方渐变 α_cap(t) = cap_strength·t²
      （t=0 内侧 → t=1 边界），吸收辐射模避免 Dirichlet 反射

    Args:
        nx: 网格点数。
        core_x0, core_x1: 芯区索引 [core_x0, core_x1)。
        pad_pts: 单侧 pad 点数。
        loss_db_per_cm: Soref 传播损耗 (dB/cm)，默认 3.0。
        cap_strength: CAP 边界处最大功率衰减系数 (μm⁻¹)，默认 0.5。
        cap_fraction: pad 外侧作为 CAP 的比例，默认 0.3。

    Returns:
        ndarray (nx,): 功率衰减系数 α(x) (μm⁻¹)，非负。

    Raises:
        ValueError: 参数非法（R03）。

    来源 (R02):
        - Soref 1993 Proc. IEEE — SOI 波导损耗
          https://ieeexplore.ieee.org/document/249720
        - Rickman & Reed 1994 ELL — SOI 0.5 dB/cm 实测
          https://digital-library.theiet.org/doi/abs/10.1049/el:19931356
        - Grillot 2006 JLT — SOI 条形波导损耗
          https://opg.optica.org/jlt/abstract.cfm?uri=jlt-24-2-891
        - Hadley 1992 Opt. Lett. — TBC/CAP 边界
          https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
        - RP Photonics BPM 边界处理
          https://www.rp-photonics.com/numerical_beam_propagation.html
    """
    _validate_loss_profile_params(
        nx, core_x0, core_x1, pad_pts, loss_db_per_cm, cap_strength,
        cap_fraction,
    )
    alpha = np.zeros(nx, dtype=np.float64)
    if loss_db_per_cm > 0:
        alpha_core = loss_db_per_cm * np.log(10.0) / 10.0 / 1e4
        alpha[core_x0:core_x1] = alpha_core
    _apply_cap_boundary(alpha, nx, pad_pts, cap_strength, cap_fraction)
    return alpha


def _validate_cn_params(
    nx: int, dx: float, dz: float, k0: float, n0: float,
) -> None:
    """校验 build_cn_matrices 入参（R03 禁止 fall-back）。"""
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


def _build_cn_h_diag(
    n_profile: np.ndarray, dx: float, k0: float, n0: float,
) -> tuple:
    """构造 H 的主/副对角元素（H = (j/(2k₀n₀)) L_x + j·k₀(n²-n₀²)/(2n₀) I）。"""
    inv_dx2 = 1.0 / (dx * dx)
    # H 的二阶导系数: j/(2k₀n₀) · 1/dx²
    coef_lap = 1j / (2.0 * k0 * n0) * inv_dx2
    # H 的折射率项: j·k₀(n²-n₀²)/(2n₀)
    coef_n = 1j * k0 * (n_profile ** 2 - n0 ** 2) / (2.0 * n0)
    # H 的三对角: 主对角 = -2·coef_lap + coef_n, 上下副对角 = coef_lap
    h_main = -2.0 * coef_lap + coef_n
    h_off = coef_lap  # ±1 偏移
    return h_main, h_off


def _assemble_cn_banded(
    h_main: np.ndarray, h_off: np.ndarray, dz: float, nx: int,
) -> tuple:
    """组装 CN 三对角 banded 矩阵 A=I-dz/2·H, B=I+dz/2·H（含 Dirichlet 边界）。"""
    # A = I - dz/2 · H
    a_main = 1.0 - 0.5 * dz * h_main
    a_off = -0.5 * dz * h_off
    # B = I + dz/2 · H
    b_main = 1.0 + 0.5 * dz * h_main
    b_off = 0.5 * dz * h_off
    # solve_banded 的 ab 格式: ab[u+i-j, j] = a[i,j]
    # 三对角: ab[0] = 上副对角，ab[1] = 主对角，ab[2] = 下副对角
    A_banded = np.zeros((3, nx), dtype=np.complex128)
    A_banded[0, 1:] = a_off       # 上副对角
    A_banded[1, :] = a_main       # 主对角
    A_banded[2, :-1] = a_off      # 下副对角
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
    _validate_cn_params(nx, dx, dz, k0, n0)
    h_main, h_off = _build_cn_h_diag(n_profile, dx, k0, n0)
    return _assemble_cn_banded(h_main, h_off, dz, nx)


def _validate_bpm_grid(
    width_um: float, length_um: float, wavelength_um: float,
    n_core: float, n_clad: float, dz_um: float, dx_um: float, pad_um: float,
) -> tuple:
    """校验 solve_bpm 入参 + 构建网格/芯区索引（R03 禁止 fall-back）。"""
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
    window_um = width_um + 2.0 * pad_um
    nx = int(round(window_um / dx_um))
    if nx < 5:
        raise ValueError(f"网格过小 nx={nx}，请减小 dx_um 或增大 pad_um")
    dx = window_um / nx
    nz = int(round(length_um / dz_um))
    if nz < 1:
        raise ValueError(f"步数过少 nz={nz}，请增大 length_um 或减小 dz_um")
    dz = length_um / nz
    core_x0 = int(round((window_um - width_um) / 2.0 / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    if core_x0 < 1 or core_x1 > nx - 1:
        raise ValueError(f"芯区索引越界: x=[{core_x0},{core_x1}) 网格 {nx}")
    return window_um, nx, dx, nz, dz, core_x0, core_x1


def _setup_bpm_field(
    width_um: float, wavelength_um: float, n_core: float, n_clad: float,
    window_um: float, nx: int, dx: float, dz: float,
    core_x0: int, core_x1: int,
) -> tuple:
    """构建折射率/CN 矩阵/损耗/初始高斯场，返回 BPM 求解上下文。"""
    n_profile = np.full(nx, n_clad, dtype=np.float64)
    n_profile[core_x0:core_x1] = n_core
    k0 = 2.0 * np.pi / wavelength_um  # 真空波数（μm⁻¹）
    n0 = n_clad  # 参考折射率（取包层）
    A_banded, B_banded = build_cn_matrices(n_profile, dx, dz, k0, n0)
    # 损耗分布 α(x): Soref 芯区吸收 + CAP 边界吸收
    pad_pts = core_x0  # 单侧 pad 点数（芯区居中）
    alpha_profile = build_loss_profile(
        nx, core_x0, core_x1, pad_pts,
        loss_db_per_cm=LOSS_DB_PER_CM_SI,
        cap_strength=CAP_STRENGTH, cap_fraction=CAP_FRACTION,
    )
    attn_half = np.exp(-0.5 * alpha_profile * dz)
    # 初始场: 高斯光束（中心对准波导，腰斑≈波导宽度，耦合到基模）
    center_um = window_um / 2.0
    waist_um = width_um
    field = gaussian_source(nx, dx, center_um, waist_um)
    field[0] = 0.0  # Dirichlet 边界
    field[-1] = 0.0
    p_initial = float(np.sum(np.abs(field) ** 2) * dx)
    return (A_banded, B_banded, alpha_profile, attn_half, field,
            p_initial, k0, n0)


def _run_bpm_split_step(
    field: np.ndarray, attn_half: np.ndarray,
    A_banded: np.ndarray, B_banded: np.ndarray, nz: int,
) -> np.ndarray:
    """symmetric split-step Crank-Nicolson 主循环。

    每步: E^{n+1} = attn_half · A⁻¹·B · attn_half · E^n  (O(dz³))
    CN 步: 实折射率反厄米 H，严格功率守恒（仅相位演化）。
    衰减步: α(x) 来自 Soref 芯区损耗 + CAP pad 外侧渐变。
    """
    for _ in range(nz):
        # 半步衰减（前）
        field = field * attn_half
        # CN 全步（相位演化，实折射率守恒功率）
        rhs = np.zeros_like(field)
        rhs[:] = B_banded[1, :] * field
        rhs[1:] += B_banded[0, 1:] * field[:-1]  # 上副对角
        rhs[:-1] += B_banded[2, :-1] * field[1:]  # 下副对角
        rhs[0] = 0.0  # Dirichlet 边界
        rhs[-1] = 0.0
        # 求解 A · E^{n+1} = rhs
        field = solve_banded((1, 1), A_banded, rhs)
        # 半步衰减（后）
        field = field * attn_half
        field[0] = 0.0
        field[-1] = 0.0
        # NaN 校验（R03 禁止 fall-back）
        if np.any(np.isnan(field)) or np.any(np.isinf(field)):
            raise RuntimeError("BPM 求解出现 NaN/Inf（R03 禁止 fall-back）")
    return field


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
    """1D Crank-Nicolson split-step BPM 求解器。

    在硅条形波导中传播高斯光束，CN 隐式格式求解抛物波动方程（相位演化），
    symmetric split-step 显式衰减步引入物理损耗（Soref 材料吸收 + CAP 边界）。
    每步: E^{n+1} = exp(-α·dz/2) · A⁻¹·B · exp(-α·dz/2) · E^n。
    CN 步实折射率反厄米 H 严格功率守恒（仅相位演化）；
    衰减步 α(x) 来自 Soref 芯区损耗 + CAP pad 外侧渐变。

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
        dict: {field_z, transmission_db, n_steps, grid_info, physics, loss}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 求解失败或结果含 NaN（R03）。

    来源: Feit & Fleck 1978（BPM）/ Crank & Nicolson 1947（隐式格式）/
        Chung & Dagli 1990（ADI）/ Soref 1993 Proc. IEEE（SOI 损耗）/
        Hadley 1992 Opt. Lett.（CAP/TBC 边界）
    """
    (window_um, nx, dx, nz, dz, core_x0, core_x1) = _validate_bpm_grid(
        width_um, length_um, wavelength_um, n_core, n_clad,
        dz_um, dx_um, pad_um,
    )
    (A_banded, B_banded, alpha_profile, attn_half, field,
     p_initial, k0, n0) = _setup_bpm_field(
        width_um, wavelength_um, n_core, n_clad, window_um, nx, dx, dz,
        core_x0, core_x1,
    )
    field = _run_bpm_split_step(field, attn_half, A_banded, B_banded, nz)
    p_final = float(np.sum(np.abs(field) ** 2) * dx)
    if p_initial <= 0:
        raise RuntimeError(f"初始功率 {p_initial} <= 0（R03 禁止 fall-back）")
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
            "nx": nx, "nz": nz, "dx_um": float(dx), "dz_um": float(dz),
            "window_um": float(window_um), "core_x": [core_x0, core_x1],
        },
        "physics": {
            "k0": float(k0), "n0": float(n0),
            "n_core": float(n_core), "n_clad": float(n_clad),
        },
        "loss": {
            "loss_db_per_cm": float(LOSS_DB_PER_CM_SI),
            "cap_strength": float(CAP_STRENGTH),
            "cap_fraction": float(CAP_FRACTION),
            "alpha_profile": alpha_profile.tolist(),
        },
    }


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
    """1D Crank-Nicolson split-step BPM 求解器。

    在硅条形波导中传播高斯光束，CN 隐式格式求解抛物波动方程，
    symmetric split-step 显式衰减步引入物理损耗。

    每步: E^{n+1} = exp(-α·dz/2) · A⁻¹·B · exp(-α·dz/2) · E^n

    Args:
        width_um: 波导芯宽度（μm）。
        length_um: 传播长度（μm）。
        wavelength_um: 波长（μm）。
        n_core: 芯区折射率（Si 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 1.444）。
        dz_um: 纵向步长（μm）。
        dx_um: 横向步长（μm）。
        pad_um: 包层 padding（μm，每侧）。

    Returns:
        dict: {field_z, transmission_db, n_steps, grid_info, physics, loss}

    Raises:
        ValueError: 参数非法（R03）。
        RuntimeError: 求解失败或 NaN（R03）。

    来源: Feit & Fleck 1978; Crank & Nicolson 1947; Soref 1993; Hadley 1992
    """
    (field, A_banded, B_banded, attn_half, nx, nz, dz, dx,
     window_um, core_x0, core_x1, k0, n0, alpha_profile, p_initial) = (
        _solve_bpm_setup(
            width_um, length_um, wavelength_um, n_core, n_clad,
            dx_um, dz_um, pad_um
        )
    )
    field = _solve_bpm_propagate(field, A_banded, B_banded, attn_half, nx, nz)
    return _solve_bpm_build_result(
        field, p_initial, nx, nz, dz, dx, window_um, core_x0, core_x1,
        k0, n0, n_core, n_clad, wavelength_um, alpha_profile
    )
