"""PoLaRIS 频域有限差分（FDFD）仿真子模块（polaris-fdfd）。

提供频域 Helmholtz 方程稀疏矩阵求解 API。构建 2D 网格上的 5 点拉普拉斯算子
+ 折射率项，求解线性系统 A·E = b 得到稳态场分布，提取传输率。

## Input / Process / Output 三段式（IPO）

- solve_fdfd:
  - I: width_um=0.5 / length_um=10.0 / wavelength_um=1.55
       / n_core=3.476 / n_clad=1.444 / dx_um=0.05 / pad_um=1.5
  - P: 1) 构建 2D 折射率分布 n(x,z)（x 横向，z 传播方向）
       2) 构建 5 点拉普拉斯稀疏算子 A = ∇² + diag(k₀²n²)
       3) 高斯线源 b（z=0 处，横向高斯分布）
       4) scipy.sparse.linalg.spsolve 求解 A·E = b
       5) 输出端 z=L 提取传输率
  - O: dict{field_2d, transmission_db, n_grid, ...}

## 稳定 API

- ``solve_fdfd(width_um=0.5, length_um=10.0, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444, dx_um=0.05, pad_um=1.5) -> dict``

## 设计原则
- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现
- R03 禁止 fall-back: 参数非法 raise；求解失败 raise
- R02 学术诚信: 公式可溯源（Taflove 2005 + Shin 2014）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Taflove & Hagness, "Computational Electrodynamics: The FDTD Method",
  Artech 2005（FDFD 第 5 章）
- Shin & Fan, Opt. Express 2014（FDFD 2D 求解）
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230
- scipy.sparse.linalg.spsolve（稀疏直接求解器）
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Soref 1993 IEEE JQE（Si/SiO2 折射率）
  https://ieeexplore.ieee.org/document/1148303
"""

from __future__ import annotations

from polaris_fdfd.solver import (
    C0,
    build_helmholtz_operator,
    build_line_source,
    solve_fdfd,
)

__version__ = "5.0.0"

__all__ = [
    "solve_fdfd",
    "build_helmholtz_operator",
    "build_line_source",
    "C0",
    "__version__",
]
