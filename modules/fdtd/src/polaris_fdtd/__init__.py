"""PoLaRIS 时域有限差分（FDTD）仿真子模块（polaris-fdtd）。

提供 3D FDTD 全波仿真 API（Yee 1966 + Gedney 1996 PML + JAX 可微内核）。
本子模块由旧 polaris-sim 拆分而来（每种仿真独立成包），FDTD 内核迁移自 polaris-inverse。

## Input / Process / Output 三段式（IPO）

- simulate_waveguide_fdtd:
  - I: dx_um=0.05 / n_steps=2000 / wavelength_um=1.55
  - P: Yee 1966 时间步进 + Gedney 1996 PML + 双监视器比值法
  - O: dict{transmission_db, T_fdtd, fdtd_duration_s, n_steps, dx_um, pml_enabled}
- simulate_mmi_fdtd:
  - I: dx_um=0.05 / n_steps=2000 / wavelength_um=1.55
  - P: MMI 多模干涉 + 双输出功率提取 + 分束比
  - O: dict{split_ratio, T_fdtd, transmission_db, fdtd_duration_s, ...}
- YeeGrid3D / GedneyPML / DifferentiableFDTD: 底层内核（迁移自 polaris-inverse）

## 稳定 API

- ``simulate_waveguide_fdtd(dx_um=0.05, n_steps=2000) -> dict``
- ``simulate_mmi_fdtd(dx_um=0.05, n_steps=2000) -> dict``
- ``YeeGrid3D(nx, ny, nz, dx, dy, dz, epsilon_r=None, mu_r=None)``
- ``GedneyPML(grid, n_layers=8, sigma_ratio=1.0, m=3, eps_r_bg=None)``
- ``DifferentiableFDTD(grid, pml=None, dt=None, eps_r_bg=None)``

## 设计原则
- R04 不参与 GPU: 强制 JAX CPU 后端（JAX_PLATFORMS=cpu）
- R03 禁止 fall-back: JAX 不可用即 raise；仿真 NaN 即 raise
- R02 学术诚信: 所有物理常量/公式可溯源（NIST CODATA 2018 + Soref 1993）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249
- Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Mahau 2024 arXiv:2412.12360（JAX 可微 FDTD）https://arxiv.org/abs/2412.12360
- Hughes 2018 ACS Photonics（autograd=adjoint）https://arxiv.org/abs/1811.01255
- Lumerical FDTD 求解器 https://optics.ansys.com/hc/en-us/articles/360034914833
"""

from __future__ import annotations

from polaris_fdtd.solver import (
    CFL_SAFETY,
    C0,
    DifferentiableFDTD,
    EPS0,
    GedneyPML,
    MU0,
    SOI_EPS_R_SI,
    SOI_EPS_R_SIO2,
    SOI_N_SI,
    SOI_N_SIO2,
    YeeGrid3D,
)
from polaris_fdtd.mmi import simulate_mmi_fdtd
from polaris_fdtd.waveguide import simulate_waveguide_fdtd

__version__ = "5.0.0"

__all__ = [
    "simulate_waveguide_fdtd",
    "simulate_mmi_fdtd",
    "YeeGrid3D",
    "GedneyPML",
    "DifferentiableFDTD",
    "C0",
    "EPS0",
    "MU0",
    "SOI_N_SI",
    "SOI_N_SIO2",
    "SOI_EPS_R_SI",
    "SOI_EPS_R_SIO2",
    "CFL_SAFETY",
    "__version__",
]
