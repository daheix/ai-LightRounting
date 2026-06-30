"""SC-PML（Stretched Coordinate Perfectly Matched Layer）复坐标拉伸。

按 A04-FDE 算法文档 §5 实现 Shin & Fan 2012 证明频域反射最低的 SC-PML。
PML 区域波指数衰减无反射，用于吸收 FDE/FDFD 辐射模（泄露模）。

理论（Shin & Fan 2012）：
- 笛卡尔坐标拉伸 x → x̃ = ∫₀ˣ s_x(x') dx'
- 拉伸因子 s_x = κ_x + σ_x / (iωε₀)
- 非吸收区域 s_x = 1，PML 区域 s_x 复数（σ_x > 0 吸收）
- 介质张量修正：ε̃ = ε / s_x，μ̃ = μ / s_x

σ_x 沿 PML 深度渐变（多项式渐变，标准做法）：
    σ_x(d) = σ_max · (d / L_pml)^m，m=3（Taflove 推荐）

σ_max 经验公式（Taflove 2005，反射 ≤ -60 dB）：
    σ_max = -(m+1) · ln(R) / (2 · η · L_pml)
    η = 377 Ω（自由空间波阻抗），R = 1e-6（目标反射系数）

文献来源：
- Shin W, Fan S, "Choice of the perfectly matched layer boundary condition
  for frequency-domain Maxwell's equations solvers," J. Comput. Phys. 231,
  3406-3431 (2012). https://doi.org/10.1016/j.jcp.2011.12.037
- Taflove & Hagness, "Computational Electrodynamics," 3rd ed. (2005), §5.
- Roden JA, Gedney SD, "Convolution PML (CPML)," IEEE MWCL (2000).

规则依据：project_rules.md 规则 26（纯 CPU）；规则 14（失败 raise，无 fall-back）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["ScPml", "build_pml_stretch"]

# 物理常数（SI）
_C0 = 2.99792458e8  # 真空光速 m/s (NIST CODATA 2018)
_ETA0 = 376.730313668  # 自由空间波阻抗 Ω
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m


@dataclass(frozen=True)
class ScPml:
    """SC-PML 参数规格。

    Attributes:
        layers: PML 层数（每侧）。
        sigma_max: PML 最大电导率（S/m），若 None 则按反射目标自动计算。
        kappa_max: PML 最大 κ（相对磁导率修正），默认 1.0（不修正）。
        order: σ 多项式渐变阶数 m，默认 3（Taflove 推荐）。
        r_target: PML 目标反射系数，默认 1e-6（≤ -60 dB）。
    """

    layers: int = 10
    sigma_max: float | None = None
    kappa_max: float = 1.0
    order: int = 3
    r_target: float = 1e-6

    def __post_init__(self) -> None:
        if self.layers < 2:
            raise ValueError(f"PML 层数过少 ({self.layers})，至少 2 层")
        if self.order < 1:
            raise ValueError(f"PML 渐变阶数必须 ≥1，实际 {self.order}")
        if not (0.0 < self.r_target < 1.0):
            raise ValueError(f"目标反射系数须在 (0,1)，实际 {self.r_target}")


def _sigma_max_auto(
    pml: ScPml, wavelength: float, dx: float
) -> float:
    """按 Taflove 2005 经验公式计算 σ_max。

    σ_max = -(m+1) · ln(R) / (2 · η₀ · L_pml)
    L_pml = layers · dx

    Args:
        pml: PML 参数。
        wavelength: 自由空间波长（米）。
        dx: 网格间距（米）。

    Returns:
        σ_max（S/m）。
    """
    l_pml = pml.layers * dx
    if l_pml <= 0.0:
        raise ValueError("PML 厚度必须为正")
    return -(pml.order + 1) * np.log(pml.r_target) / (2.0 * _ETA0 * l_pml)


def build_pml_stretch(
    n: int,
    dx: float,
    wavelength: float,
    pml: ScPml | None = None,
    axis: str = "x",
) -> np.ndarray:
    """构造 1D PML 复坐标拉伸因子数组。

    返回长度 n 的复数数组 s_x（或 s_y），非 PML 区域为 1.0，
    两侧 pml.layers 层区域为复数 (κ + σ/(iωε₀))。

    Args:
        n: 该方向网格点数。
        dx: 该方向网格间距（米）。
        wavelength: 自由空间波长（米）。
        pml: PML 参数，None 则用默认 ScPml()。
        axis: 方向标识，仅用于错误信息。

    Returns:
        拉伸因子数组 (n,) complex128。

    Raises:
        ValueError: PML 层数超过网格点数一半。
    """
    if pml is None:
        pml = ScPml()
    if pml.layers * 2 >= n:
        raise ValueError(
            f"{axis} 方向 PML 层数 {pml.layers}*2 >= 网格点数 {n}，"
            "请减少 PML 层数或增加网格分辨率"
        )
    # R05 Bug 修复 v5.0-P2-2R1: 光速使用 NIST CODATA 2018 精确值，
    # 与项目其他模块（fdtd/yee_grid.py:65, lumerical_fdtd.py:59）保持一致。
    # 原代码用 3e8 近似值引入 0.07% 误差，影响 PML 拉伸因子 s 的电导率匹配。
    omega = 2.0 * np.pi * _C0 / wavelength  # 角频率 ω = 2πc/λ
    sigma_max = pml.sigma_max if pml.sigma_max is not None else _sigma_max_auto(
        pml, wavelength, dx
    )
    # 拉伸因子 s = κ + σ/(iωε₀) = κ - i·σ/(ωε₀)
    s = np.ones(n, dtype=np.complex128)
    for side in ("left", "right"):
        if side == "left":
            idx = np.arange(pml.layers)  # 0..L-1
            # 距 PML 内边界（最外层 d=L_pml，最内层 d≈0）
            depth = (pml.layers - idx) * dx
        else:
            idx = n - 1 - np.arange(pml.layers)
            depth = (idx - (n - 1 - pml.layers) + 1) * dx
        # σ 多项式渐变 σ(d) = σ_max · (d/L_pml)^m
        d_norm = depth / (pml.layers * dx)
        sigma = sigma_max * d_norm**pml.order
        # κ 渐变（默认 1.0，可扩展）
        kappa = 1.0 + (pml.kappa_max - 1.0) * d_norm**pml.order
        s[idx] = kappa - 1j * sigma / (omega * _EPS0)
    return s
