"""A06-VarFDTD 有效折射率法求解器包（A06 §1）。

VarFDTD（2.5D Variational FDTD）通过有效折射率法（EIM）将 3D 波导结构折叠为
2D 等效折射率分布，再在该 2D 平面上执行标准 FDTD leapfrog，以 2D FDTD 的
计算成本近似获得 3D FDTD 的精度。是 Lumerical MODE / Ansys Optics varFDTD
求解器的核心算法，特别适合 SOI 平面波导器件（环谐振器、Y 分支、光栅天线）。

== 模块组成 ==
- effective_index : EIM 折叠（色散方程 brentq 精确求解 + Marcatili 近似）
- yee_2d          : 2D Yee leapfrog（复用 A09-FDTD YeeGridFdtd）
- solver          : 主求解器，编排 effective_index + yee_2d + cpml + tfsf + 源/监视器

== 公开 API ==
- compute_effective_index  : EIM 折叠，n_y → n_eff
- EffectiveIndexResult     : EIM 折叠结果数据类
- VarFdtdConfig / VarFdtdResult : 仿真配置与结果
- VarFdtdSolver            : 2.5D 求解器（编排 CPML/TFSF/源/监视器）
- solve_varfdtd             : 便捷入口（一键运行）

== 与 A09-FDTD / A04-FDE 的依赖关系（规则 9 单文件版本，复用现有高质量实现）==
- 复用 A09-FDTD 的 YeeGridFdtd（ca/cb/da/db 与 Courant 校验）
- 复用 A09-FDTD 的 CPML（build_cpml/update_*_psi）
- 复用 A09-FDTD 的 TFSF（Incident1D/apply_tfsf_*_correction）
- 复用 A09-FDTD 的源（GaussianPulse/DipoleSource/inject_dipole）
- 复用 A09-FDTD 的监视器（DftMonitor/SParamExtractor）
- A04-FDE 的 Mode 数据类供 effective_index 可选调用（spec 允许简化为解析 EIM）

== 检索记录（R01 方案检索）==
- 关键词："varFDTD effective index method Lumerical"
- 关键词："effective index method waveguide 2D FDTD reduction"
- 关键词："Chang 1980 effective dielectric constant method"
- 关键词："Lumerical varFDTD 2.5D time domain simulation"
- 采用方案：EIM 色散方程 brentq 精确求根 + 复用 A09-FDTD 底座
- 来源：Ansys Optics varFDTD、Lumerical、Chang 1980、Marcatili 1969、Yee 1966

文献来源（≥5，规则 18 学术诚信）：
1. Chang 1980 IEEE Trans MTT 28(8) 889 —
   https://doi.org/10.1109/TMTT.1980.1130551
2. Lumerical varFDTD — https://www.lumerical.com/products/varfdtd/
3. Marcatili 1969 Bell Syst Tech J 48(7) 2071 —
   https://doi.org/10.1002/j.1538-7305.1969.tb01161.x
4. Kumar et al. 1985 IEEE JQE 21(1) —
   https://doi.org/10.1109/JQE.1985.1072717
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. Taflove 2005 Computational Electrodynamics —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
7. Soref 1991 IEEE JQE 27(8) 1971 —
   https://doi.org/10.1109/3.84143

规则依据：规则 9（单文件版本，复用 A09/A04 不重写）/规则 14（无 fall-back）/
规则 18（学术诚信）/规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from polaris_multiphysics.varfdtd.effective_index import (
    EffectiveIndexResult,
    compute_effective_index,
    marcatili_neff,
)
from polaris_multiphysics.varfdtd.solver import (
    VarFdtdConfig,
    VarFdtdResult,
    VarFdtdSolver,
    solve_varfdtd,
)
from polaris_multiphysics.varfdtd.yee_2d import (
    Yee2DFields,
    build_2d_grid,
    build_eps_from_neff,
    step_leapfrog,
)

__all__ = [
    # effective_index
    "EffectiveIndexResult",
    "compute_effective_index",
    "marcatili_neff",
    # yee_2d
    "Yee2DFields",
    "build_2d_grid",
    "build_eps_from_neff",
    "step_leapfrog",
    # solver
    "VarFdtdConfig",
    "VarFdtdResult",
    "VarFdtdSolver",
    "solve_varfdtd",
]
