"""CPML 复坐标拉伸 PML（A09 §5，Roden & Gedney 2000 递归卷积）。

CPML（Convolution PML）通过递归卷积将频域复坐标拉伸因子
    s_x = κ_x + σ_x / (α_x + iω)
的卷积转化为时域递推，无需分裂场，与普通 leapfrog 兼容，是
Lumerical/Tidy3D/曼光/SimWorks 共同方案。物理等价于复坐标拉伸
（Shin & Fan 2012，与 A05-FDFD SC-PML 同源）。

ADE（辅助微分方程）实现，避免显式卷积求和（A09 §5.3）：
    E_z^{n+1} = C_a E_z^n + C_b (∇×H)_z + C_b · ψ_e,z^{n+1/2}
    ψ_e,z^{n+1/2} = b_x · ψ_e,z^{n-1/2} + a_x · ∂H_y^{n+1/2}/∂x

系数（A09 §5.3 / Taflove 2005 §7.8）：
    b_x = exp(-(σ_x/κ_x + α_x) · Δt / ε_0)
    a_x = σ_x / (Δx · (κ_x · α_x + σ_x)) · (b_x - 1)

σ_x 沿 PML 深度多项式渐变（Gedney 1996 推荐）：
    σ_max = (m+1) / (150·π·Δh·√ε_r)，m=3
    σ_x(d) = σ_max · (d / L_pml)^m（d 为距 PML 内边界的深度）

数值反射 ≤ −60 dB（10 层 PML），优于普通分裂场 PML（−30 dB，A09 §13.2）。

*创新*：与 A05-FDFD 共享 SC-PML 复坐标拉伸理论，但 A09 时域采用 ADE 递归卷积
实现，避免存储历史卷积和（O(N) 内存，O(N) 时间/步）。
- 底层逻辑：ψ 辅助变量与 leapfrog 同步更新，加到标准旋度差分结果上。
- 支持理论：Roden & Gedney 2000 证明 CPML 反射优于分裂场 PML；
  Shin & Fan 2012 证明复坐标拉伸是 PML 的最优数学形式。
- 案例：自由空间脉冲吸收、SOI 波导端口吸收、超表面周期边界吸收。

文献来源（≥5，规则 18 学术诚信）：
1. Roden JA, Gedney SD, "Convolution PML (CPML)," Microw. Opt. Technol.
   Lett. 27(5) 334-339 (2000) —
   https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
2. Shin & Fan 2012 J Comput Phys 231 3406-3431 —
   https://doi.org/10.1016/j.jcp.2011.12.037
3. Gedney 1996 IEEE Trans AP 44(12) 1630-1639 —
   https://doi.org/10.1109/8.546242
4. Taflove & Hagness 2005 Computational Electrodynamics §7 —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
5. Berenger 1994 J Comput Phys 114 185-200（PML 原始概念）—
   https://doi.org/10.1006/jcph.1994.1159
6. Lumerical FDTD PML 文档 —
   https://optics.ansys.com/hc/en-us/articles/360034915353
7. Tidy3D StablePML —
   https://docs.flexcompute.com/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化，仅主循环例外）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["CpmlConfig", "CpmlCoefficients", "CpmlBuffers", "build_cpml"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m


@dataclass(frozen=True)
class CpmlConfig:
    """CPML 参数规格（A09 §5.3，每侧 PML 相同）。

    Attributes:
        layers: PML 层数（每侧），默认 10（A09 §5.3 推荐）。
        order: σ 多项式渐变阶数 m，默认 3（Gedney 1996 推荐）。
        sigma_max: PML 最大电导率（S/m），None 则按 Gedney 公式自动计算。
        kappa_max: PML 最大 κ（相对磁导率修正），默认 1.0。
        alpha: CFS-PML α 参数（α>0 改善低频/长时稳定性，A09 §5.4），默认 0.08。
        r_target: 目标反射系数（用于 σ_max 备选估计），默认 1e-6（≤−60 dB）。
    """

    layers: int = 10
    order: int = 3
    sigma_max: float | None = None
    kappa_max: float = 1.0
    alpha: float = 0.08
    r_target: float = 1e-6

    def __post_init__(self) -> None:
        if self.layers < 2:
            raise ValueError(f"PML 层数过少 ({self.layers})，至少 2 层")
        if self.order < 1:
            raise ValueError(f"σ 渐变阶数 m 须 ≥1，实际 {self.order}")
        if self.kappa_max <= 0.0:
            raise ValueError(f"kappa_max 须 >0，实际 {self.kappa_max}")
        if self.alpha < 0.0:
            raise ValueError(f"alpha 须 ≥0，实际 {self.alpha}")
        if not (0.0 < self.r_target < 1.0):
            raise ValueError(f"r_target 须 ∈ (0,1)，实际 {self.r_target}")


@dataclass(frozen=True)
class CpmlCoefficients:
    """CPML 1D 系数数组（沿某一方向）。

    κ_x, σ_x, α_x 为复坐标拉伸参数；a_x, b_x 为递归卷积系数（A09 §5.3）。
    内部（非 PML）区域全部为 0（a_x=0 → ψ 不积累）。

    Attributes:
        sigma: σ (S/m) (n,)，PML 区非零，内部为 0。
        kappa: κ (n,)，PML 区渐变到 kappa_max，内部为 1.0。
        alpha: α (n,)，PML 区为 alpha 常数，内部为 0。
        a: 递归卷积系数 a_x (n,)，内部为 0。
        b: 递归卷积系数 b_x (n,)，内部为 1.0（ψ 不衰减）。
        layers: PML 层数。
    """

    sigma: np.ndarray
    kappa: np.ndarray
    alpha: np.ndarray
    a: np.ndarray
    b: np.ndarray
    layers: int


@dataclass
class CpmlBuffers:
    """CPML 辅助变量缓冲区（ψ_e, ψ_h，A09 §5.3 ADE 实现）。

    ψ_e_xz, ψ_e_yz 用于 E_z 更新（对应 ∂H_y/∂x、∂H_x/∂y 的修正）。
    ψ_h_yx, ψ_h_xy 用于 H_y, H_x 更新（对应 ∂E_z/∂x、∂E_z/∂y 的修正）。
    形状均为 (nx, ny)，内部区域始终为 0（因 a=0）。

    Attributes:
        psi_e_xz: ψ_e for E_z 的 x 方向修正 (nx, ny)。
        psi_e_yz: ψ_e for E_z 的 y 方向修正 (nx, ny)。
        psi_h_yx: ψ_h for H_y 的 x 方向修正 (nx, ny)。
        psi_h_xy: ψ_h for H_x 的 y 方向修正 (nx, ny)。
    """

    psi_e_xz: np.ndarray
    psi_e_yz: np.ndarray
    psi_h_yx: np.ndarray
    psi_h_xy: np.ndarray


def _sigma_max_gedney(pml: CpmlConfig, dx: float, eps_r_bg: float) -> float:
    """Gedney 1996 推荐 σ_max 公式（A09 §5.3）。

    σ_max = (m+1) / (150·π·Δh·√ε_r)

    Args:
        pml: CPML 参数。
        dx: 网格间距（米）。
        eps_r_bg: 背景相对介电常数（取内部区均值或 n_clad²）。

    Returns:
        σ_max（S/m）。
    """
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if eps_r_bg <= 0.0:
        raise ValueError(f"eps_r_bg 必须为正，实际 {eps_r_bg}")
    return float((pml.order + 1) / (150.0 * np.pi * dx * np.sqrt(eps_r_bg)))


def _build_axis_profile(
    n: int,
    dx: float,
    pml: CpmlConfig,
    eps_r_bg: float,
) -> CpmlCoefficients:
    """构造单轴 1D CPML 系数（σ, κ, α, a, b），含两侧 PML。

    内部（非 PML）区域：σ=0, κ=1, α=0 → a=0, b=1（ψ 不更新）。
    两侧 pml.layers 层：σ 多项式渐变、κ 渐变、α=alpha 常数。

    Args:
        n: 该方向网格点数。
        dx: 该方向网格间距（米）。
        pml: CPML 参数。
        eps_r_bg: 背景相对介电常数。

    Returns:
        CpmlCoefficients（长度 n 的 1D 系数数组）。

    Raises:
        ValueError: PML 层过多导致无内部区域（规则 14）。
    """
    if pml.layers * 2 >= n:
        raise ValueError(
            f"PML 层数 {pml.layers}·2 >= 网格点 {n}，无内部区域，请减少 PML 层数或增加网格分辨率"
        )
    sigma = np.zeros(n, dtype=np.float64)
    kappa = np.ones(n, dtype=np.float64)
    alpha = np.zeros(n, dtype=np.float64)
    sigma_max = pml.sigma_max if pml.sigma_max is not None else _sigma_max_gedney(pml, dx, eps_r_bg)
    layers = pml.layers
    l_pml = layers * dx
    # 左侧 PML：i=0 外边界（σ=σ_max），i=layers-1 内边界（σ≈0）
    idx_left = np.arange(layers)
    depth_left = (layers - idx_left) * dx  # 距外边界深度
    # 右侧 PML：i=n-layers 内边界（σ≈0），i=n-1 外边界（σ=σ_max）
    idx_right = n - layers + np.arange(layers)
    depth_right = (np.arange(layers) + 1) * dx
    for idx, depth in ((idx_left, depth_left), (idx_right, depth_right)):
        d_norm = depth / l_pml  # 归一化深度 ∈ (0, 1]
        d_norm = np.clip(d_norm, 0.0, 1.0)
        sigma[idx] = sigma_max * d_norm**pml.order
        kappa[idx] = 1.0 + (pml.kappa_max - 1.0) * d_norm**pml.order
        alpha[idx] = pml.alpha
    # 注：递归卷积系数 a/b 依赖 Δt，由 _fill_ab 在 build_cpml 中按 dt 计算
    # （A09 §5.3：b_x = exp(-(σ/κ+α)·Δt/ε_0)，a_x = σ/(Δx·(κ·α+σ))·(b_x-1)）
    return CpmlCoefficients(
        sigma=sigma,
        kappa=kappa,
        alpha=alpha,
        a=np.zeros(n),
        b=np.ones(n),
        layers=layers,
    )


def build_cpml(
    shape: tuple[int, int],
    dx: float,
    dy: float,
    dt: float,
    pml: CpmlConfig,
    eps_r_bg: float = 1.0,
) -> tuple[CpmlCoefficients, CpmlCoefficients, CpmlBuffers]:
    """构造 2D CPML 完整系数与辅助变量缓冲区。

    返回 x 方向与 y 方向各自的 CpmlCoefficients，以及全网格 ψ 缓冲区。
    系数 a/b 在此处根据 dt 一次性计算（A09 §5.3）。

    Args:
        shape: 网格形状 (Nx, Ny)。
        dx, dy: 网格间距（米）。
        dt: 时间步（秒）。
        pml: CPML 参数。
        eps_r_bg: 背景相对介电常数（σ_max 估计用），默认 1.0。

    Returns:
        (coeff_x, coeff_y, buffers) 三元组。

    Raises:
        ValueError: 形状/参数非法（规则 14）。
    """
    nx, ny = shape
    if nx < 2 * pml.layers + 1 or ny < 2 * pml.layers + 1:
        raise ValueError(f"网格 {shape} 过小，无法容纳 {pml.layers} 层 PML（每侧）")
    if dt <= 0.0:
        raise ValueError(f"dt 必须为正，实际 {dt}")
    # 1D 轴系数（σ, κ, α 渐变）
    cx = _build_axis_profile(nx, dx, pml, eps_r_bg)
    cy = _build_axis_profile(ny, dy, pml, eps_r_bg)
    # 计算 a/b 递归卷积系数（依赖 dt）
    cx_with_ab = _fill_ab(cx, dx, dt)
    cy_with_ab = _fill_ab(cy, dy, dt)
    # ψ 缓冲区（全网格，内部为 0）
    buffers = CpmlBuffers(
        psi_e_xz=np.zeros((nx, ny), dtype=np.float64),
        psi_e_yz=np.zeros((nx, ny), dtype=np.float64),
        psi_h_yx=np.zeros((nx, ny), dtype=np.float64),
        psi_h_xy=np.zeros((nx, ny), dtype=np.float64),
    )
    return cx_with_ab, cy_with_ab, buffers


def _fill_ab(coeff: CpmlCoefficients, dx: float, dt: float) -> CpmlCoefficients:
    """填充 a/b 递归卷积系数（A09 §5.3 公式）。

    b_x = exp(-(σ/κ + α) · Δt / ε_0)
    a_x = σ / (Δx · (κ·α + σ)) · (b_x - 1)
    """
    sigma = coeff.sigma
    kappa = coeff.kappa
    alpha = coeff.alpha
    b = np.exp(-(sigma / kappa + alpha) * dt / _EPS0)
    denom = dx * (kappa * alpha + sigma)
    # 内部区域 σ=0, α=0 → denom=0，a 应为 0
    a = np.zeros_like(sigma)
    nonzero = denom > 1e-300
    a[nonzero] = sigma[nonzero] / denom[nonzero] * (b[nonzero] - 1.0)
    return CpmlCoefficients(
        sigma=sigma,
        kappa=kappa,
        alpha=alpha,
        a=a,
        b=b,
        layers=coeff.layers,
    )


def update_h_psi(
    e_z: np.ndarray,
    buffers: CpmlBuffers,
    cx: CpmlCoefficients,
    cy: CpmlCoefficients,
) -> None:
    """更新 H 场 CPML 辅助变量 ψ_h（∂E_z/∂x、∂E_z/∂y，A09 §5.3）。

    ψ_h_yx^{n+1} = b_x · ψ_h_yx^n + a_x · (E_z[i+1] - E_z[i])
    ψ_h_xy^{n+1} = b_y · ψ_h_xy^n + a_y · (E_z[j+1] - E_z[j])

    注：差分未除以 dx/dy，因 a_x 已含 1/Δx 因子（A09 §5.3 公式）。

    Args:
        e_z: 当前电场 (Nx, Ny)。
        buffers: CPML 缓冲区（原地更新 psi_h_yx, psi_h_xy）。
        cx, cy: x/y 方向 CPML 系数。
    """
    # x 方向：∂E_z/∂x，覆盖 i ∈ [0, nx-2]
    ax = cx.a[:, None]  # (nx, 1) 广播到 ny
    bx = cx.b[:, None]
    de_dx = np.zeros_like(e_z)
    de_dx[:-1, :] = e_z[1:, :] - e_z[:-1, :]
    buffers.psi_h_yx *= bx
    buffers.psi_h_yx += ax * de_dx
    # y 方向：∂E_z/∂y，覆盖 j ∈ [0, ny-2]
    ay = cy.a[None, :]  # (1, ny)
    by = cy.b[None, :]
    de_dy = np.zeros_like(e_z)
    de_dy[:, :-1] = e_z[:, 1:] - e_z[:, :-1]
    buffers.psi_h_xy *= by
    buffers.psi_h_xy += ay * de_dy


def update_e_psi(
    h_x: np.ndarray,
    h_y: np.ndarray,
    buffers: CpmlBuffers,
    cx: CpmlCoefficients,
    cy: CpmlCoefficients,
) -> None:
    """更新 E 场 CPML 辅助变量 ψ_e（∂H_y/∂x、∂H_x/∂y，A09 §5.3）。

    ψ_e_xz^{n+1/2} = b_x · ψ_e_xz^{n-1/2} + a_x · (H_y[i] - H_y[i-1])
    ψ_e_yz^{n+1/2} = b_y · ψ_e_yz^{n-1/2} + a_y · (H_x[j] - H_x[j-1])

    Args:
        h_x, h_y: 当前磁场 (Nx, Ny)。
        buffers: CPML 缓冲区（原地更新 psi_e_xz, psi_e_yz）。
        cx, cy: x/y 方向 CPML 系数。
    """
    # x 方向：∂H_y/∂x，覆盖 i ∈ [1, nx-1]（中心差分）
    ax = cx.a[:, None]
    bx = cx.b[:, None]
    dhy_dx = np.zeros_like(h_y)
    dhy_dx[1:, :] = h_y[1:, :] - h_y[:-1, :]
    buffers.psi_e_xz *= bx
    buffers.psi_e_xz += ax * dhy_dx
    # y 方向：∂H_x/∂y，覆盖 j ∈ [1, ny-1]
    ay = cy.a[None, :]
    by = cy.b[None, :]
    dhx_dy = np.zeros_like(h_x)
    dhx_dy[:, 1:] = h_x[:, 1:] - h_x[:, :-1]
    buffers.psi_e_yz *= by
    buffers.psi_e_yz += ay * dhx_dy


def reflection_db(incident_peak: float, reflected_peak: float) -> float:
    """计算 CPML 反射系数（dB，A09 §13.2 验收）。

    R_dB = 20·log10(|E_reflected| / |E_incident|)

    Args:
        incident_peak: 入射场峰值振幅。
        reflected_peak: 反射场峰值振幅。

    Returns:
        反射系数（dB，负值）。
    """
    if incident_peak <= 0.0:
        raise ValueError(f"入射峰值必须为正，实际 {incident_peak}")
    if reflected_peak < 0.0:
        raise ValueError(f"反射峰值必须非负，实际 {reflected_peak}")
    if reflected_peak == 0.0:
        return -np.inf  # 完美吸收
    return float(20.0 * np.log10(reflected_peak / incident_peak))
