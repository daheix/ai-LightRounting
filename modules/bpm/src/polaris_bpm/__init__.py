"""PoLaRIS 光束传播法（BPM）仿真子模块（polaris-bpm）。

提供基于 Crank-Nicolson 隐式格式的抛物波动方程（paraxial wave equation）
数值求解 API。沿传播方向 z 步进，每个 z 步求解三对角线性系统，无条件稳定。

## Input / Process / Output 三段式（IPO）

- solve_bpm:
  - I: width_um=0.5 / length_um=50.0 / wavelength_um=1.55
       / n_core=3.476 / n_clad=1.444 / dz_um=0.1 / dx_um=0.01 / pad_um=2.0
  - P: 1) 构建 1D 折射率分布 n(x)
       2) 构建 Crank-Nicolson 三对角矩阵:
          (I - dz·H/2) E^{n+1} = (I + dz·H/2) E^n
          H = (j/(2k₀n₀)) L_x + j·k₀(n²-n₀²)/(2n₀) I
       3) 高斯光束初始化
       4) scipy.linalg.solve_banded 逐步求解
  - O: dict{field_z, transmission_db, n_steps, grid_info, ...}

## 稳定 API

- ``solve_bpm(width_um=0.5, length_um=50.0, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.01, pad_um=2.0) -> dict``

## 设计原则
- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现
- R03 禁止 fall-back: 参数非法 raise；NaN raise
- R02 学术诚信: 公式可溯源（Feit-Fleck 1978 + Crank-Nicolson）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Feit & Fleck, Appl. Opt. 17(24), 1978（光束传播法）
  https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson, Math. Proc. Cambridge 43(1), 1947（隐式差分）
  https://www.cambridge.org/core/journals/mathematical-proceedings-of-the-cambridge-philosophical-society/article/abs/practical-method-for-numerical-evaluation-of-solutions-of-partial-differential-equations-of-the-heatconduction-type/D0B5C0F5C0C0F5C0C0F5C0C0F5C0C0F5
- Lumerical varFDTD/BPM https://optics.ansys.com/hc/en-us/articles/360034902433
- scipy.linalg.solve_banded（三对角求解器）
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Chung & Dagli, IEEE JQE 26(8), 1990（BPM ADI）
  https://ieeexplore.ieee.org/document/59635
- Hadley, Opt. Lett. 17(10), 1992（透明边界条件）
  https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
"""

from __future__ import annotations

from polaris_bpm.solver import (
    C0,
    build_cn_matrices,
    gaussian_source,
    solve_bpm,
)

__version__ = "5.0.0"

__all__ = [
    "solve_bpm",
    "build_cn_matrices",
    "gaussian_source",
    "C0",
    "__version__",
]
