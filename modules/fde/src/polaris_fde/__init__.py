"""PoLaRIS 频域本征模（FDE）仿真子模块（polaris-fde）。

提供 2D 有限差分本征模求解器 API，计算任意折射率截面波导的导模
（有效折射率 neff + 模场分布 field_2d）。本子模块由旧 polaris-sim 拆分而来
（每种仿真独立成包）。

## Input / Process / Output 三段式（IPO）

- solve_modes:
  - I: width_um=0.5 / height_um=0.22 / wavelength_um=1.55
       / n_core=3.476（Si）/ n_clad=1.444（SiO2）/ n_modes=4
  - P: 2D 有限差分离散化标量 Helmholtz 方程 ∇²E + k₀²n²(x,y)E = β²E，
       scipy.sparse.linalg.eigsh 求前 n_modes 个最大代数特征值（导模 β²）
       n_eff = β / k₀ = sqrt(eigenvalue) / k₀
  - O: dict{modes: list[{neff, field_2d}], n_modes, wavelength_um, ...}

## 稳定 API

- ``solve_modes(width_um=0.5, height_um=0.22, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444, n_modes=4) -> dict``

## 设计原则
- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现
- R03 禁止 fall-back: 参数非法 raise；特征值 NaN raise
- R02 学术诚信: 物理参数与公式可溯源（Smit 1996 + Silvester 1996 + Soref 1993）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam, IEEE/OSA JLT 14(7), 1996（基于模式的本征模展开）
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari, "Finite Elements for Electrical Engineers",
  Cambridge 1996（FEM/FD 本征模求解）
- Soref 1993 IEEE JQE（Si/SiO2 折射率 3.476/1.444）
  https://ieeexplore.ieee.org/document/1148303
- Bogaerts et al., "Silicon microring resonators", Laser Photonics Rev 2012
  https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
- scipy.sparse.linalg.eigsh 文档（ARPACK Lanczos）
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE 求解器
  https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018（光速 c=299792458 m/s）
  https://physics.nist.gov/cuu/Constants/
"""

from __future__ import annotations

from polaris_fde.solver import (
    C0,
    CONFINEMENT_THRESHOLD,
    V_CUTOFF_SINGLE_MODE,
    build_index_profile,
    build_laplacian_operator,
    compute_v_parameter,
    confinement_factor,
    solve_modes,
)

__version__ = "5.0.0"

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "compute_v_parameter",
    "confinement_factor",
    "C0",
    "CONFINEMENT_THRESHOLD",
    "V_CUTOFF_SINGLE_MODE",
    "__version__",
]
