"""FETD 有限元时域电磁场求解器（P0-6）。

基于有限元方法（FEM）+ Newmark-β 无条件稳定时间积分的时域电磁场仿真，
适用于等离激元/超材料等具有复杂几何与色散边界的场景。

模块组成：
- solver.FetdSolver          — FETD 主求解器（Newmark-β 时间积分）
- solver.assemble_mass       — 质量矩阵 M 组装
- solver.assemble_stiffness  — 刚度矩阵 K 组装
- solver.assemble_damping    — 阻尼矩阵 C 组装（介质损耗）
- solver.NewmarkIntegrator   — Newmark-β 时间积分器（β=0.25, γ=0.5）
- solver.TetrahedronMesh     — 四面体网格
- solver.HexahedronMesh      — 六面体网格

文献来源（≥5，规则 18 学术诚信）：
1. Jin, "The Finite Element Method in Electromagnetics" 3rd ed., Wiley 2014 —
   https://onlinelibrary.wiley.com/doi/book/10.1002/9781118576637
2. Newmark 1959 "A Method of Computation for Structural Dynamics"
   ASCE J. Eng. Mech. Div. 85(3) 67-94 —
   https://doi.org/10.1061/JMCEA3.0000097
3. Lou & Jin 2006 "A Novel Dual-Field Time-Domain Finite-Element
   Domain-Decomposition Method for Computational Electromagnetics"
   IEEE Trans AP 54(10) 2900-2910 —
   https://doi.org/10.1109/TAP.2006.882184
4. Jiao & Jin 2003 "Time-Domain Finite-Element Modeling of Dispersive Media"
   IEEE Microwave Wireless Compon. Lett. 13(9) 376-378 —
   https://doi.org/10.1109/LMWC.2003.817170
5. Edelvik & Wiren 2007 "A Stable FEM-FDTD Hybrid Solver for Maxwell's Equations
   in 3D" IEEE Trans AP 55(8) 2238-2245 —
   https://doi.org/10.1109/TAP.2007.902014
6. Hughes 2000 "The Finite Element Method" Dover —
   https://store.doverpublications.com/0486411818.html
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（GPU 不参与，纯 NumPy/SciPy CPU）/§4（向量化，时间步循环例外）
"""

from __future__ import annotations

from polaris_multiphysics.fetd.solver import (
    FetdConfig,
    FetdMaterial,
    FetdResult,
    FetdSolver,
    HexahedronMesh,
    NewmarkIntegrator,
    TetrahedronMesh,
    assemble_damping,
    assemble_mass,
    assemble_stiffness,
    enforce_dirichlet,
    newmark_beta_coefficients,
)

__all__ = [
    "FetdConfig",
    "FetdMaterial",
    "FetdResult",
    "FetdSolver",
    "HexahedronMesh",
    "NewmarkIntegrator",
    "TetrahedronMesh",
    "assemble_damping",
    "assemble_mass",
    "assemble_stiffness",
    "enforce_dirichlet",
    "newmark_beta_coefficients",
]
