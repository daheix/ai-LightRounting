"""PoLaRIS 本征模展开（EME）仿真子模块（polaris-eme）。

提供基于本征模展开的传播仿真 API。将结构沿传播方向（z）切片为多个均匀段，
每段求解本地本征模，界面用模式匹配（重叠积分）计算透射/反射，
段内用相位 exp(j·β·L) 传播，最终级联所有段的 S 矩阵得到总传输率。

## Input / Process / Output 三段式（IPO）

- solve_eme:
  - I: sections（list[{width_um, length_um, n_core, n_clad}]）
       / wavelength_um=1.55 / n_modes_per_section=2
  - P: 1) 每段 1D FD 本征模求解（slab 波导）
       2) 段内相位传播 P_i = diag(exp(j·β_i·L_i))
       3) 界面模式匹配: t = ∫ E_a · E_b* dx（功率归一化）
       4) Redheffer 星积级联所有段 S 矩阵
  - O: dict{transmission, transmission_db, reflection, s_matrix, sections_info}

## 稳定 API

- ``solve_eme(sections, wavelength_um=1.55, n_modes_per_section=2) -> dict``

## 设计原则
- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现
- R03 禁止 fall-back: 参数非法 raise；模式求解失败 raise
- R02 学术诚信: 公式可溯源（Smit 1996 + Lumerical EME 文档）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam, IEEE/OSA JLT 14(7), 1996（EME 理论基础）
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Lumerical EME 求解器
  https://optics.ansys.com/hc/en-us/articles/360034902433
- P. Bienstman, "Rigorous and efficient modelling of wavelength scale
  photonic components", Ghent 2001（EME S 矩阵级联）
  https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf
- Sztefanka & Kapon, J. Lightwave Technol. 1993（模式匹配）
  https://ieeexplore.ieee.org/document/247559
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
"""

from __future__ import annotations

from polaris_eme.eme_2d import mode_overlap_2d, solve_eme_2d
from polaris_eme.solver import (
    compute_overlap_1d,
    propagate_phase,
    redheffer_star,
    solve_eme,
    solve_slab_modes,
)

__version__ = "5.0.0"

__all__ = [
    "solve_eme",
    "solve_eme_2d",
    "solve_slab_modes",
    "compute_overlap_1d",
    "mode_overlap_2d",
    "propagate_phase",
    "redheffer_star",
    "__version__",
]
