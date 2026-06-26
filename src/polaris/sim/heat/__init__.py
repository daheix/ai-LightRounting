"""A07-HEAT 热传导求解器包（稳态傅里叶导热 + 5 类边界 + 双向耦合）。

本包实现光电子器件自热仿真所需的稳态热传导求解栈：
- solver.py: 稳态傅里叶导热 ∇·(k∇T)+Q=0 的 5 点有限差分 + 调和平均热导率
  + scipy.sparse.linalg.spsolve 直接求解；含功率守恒可解性检查。
- boundary.py: 5 类边界条件（Dirichlet/Neumann/Convective/Radiative/Periodic），
  ghost-cell 2 阶离散，向量化稀疏行替换注入。
- coupling.py: HEAT→FDE 热光耦合（Cocorullo dn/dT 模式重叠加权）
  + DDM→HEAT 焦耳热（Q=J²/σ）。

物理参数（Cocorullo 1999 / Incropera / CODATA 2018）：
- 硅热导率 k_Si = 148 W/(m·K)
- SiO2 热导率 k_SiO2 = 1.4 W/(m·K)
- 硅热光系数 dn/dT = 1.86e-4 /K（Cocorullo 1999）
- Stefan-Boltzmann σ_SB = 5.670374419e-8 W/(m²·K⁴)

验收（M1-M3，见 spec tasks.md Task 2.4）：
- M1 解析解对比：1D 平板固定温差，误差 ≤1e-10
- M2 功率守恒：绝热+热源无稳态解 → raise ValueError
- M3 5 类边界均可应用，不报错

文献来源（≥5，规则 18 学术诚信）：
1. Litz 2011 Optics Express — https://doi.org/10.1364/OE.19.012997
2. Cocorullo 1999 IEEE J Quantum Electron — https://doi.org/10.1109/3.791939
3. COMSOL Heat Transfer Module — https://www.comsol.com/heat-transfer-module
4. Incropera & DeWitt — https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
5. scipy.sparse.linalg.spsolve — https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
6. Taflove 2005 Computational Electrodynamics — https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
7. Schneider 1973 IEEE Trans MTT — https://doi.org/10.1109/TMTT.1973.1127965

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy/scipy CPU）
"""

from polaris.sim.heat.boundary import (
    SIGMA_SB,
    BcSpec,
    BoundaryType,
    apply_boundary_conditions,
    is_grounding_bc,
    radiative_h,
)
from polaris.sim.heat.coupling import (
    DDMResult,
    ThermoOpticCorrection,
    ddm_to_heat,
    heat_to_fde,
)
from polaris.sim.heat.solver import (
    ADIABATIC,
    DN_DT_SI,
    K_SILICON,
    K_SIO2,
    HeatConfig,
    HeatResult,
    HeatSolver,
    solve_heat,
)

__all__ = [
    "HeatConfig",
    "HeatResult",
    "HeatSolver",
    "solve_heat",
    "BoundaryType",
    "BcSpec",
    "apply_boundary_conditions",
    "is_grounding_bc",
    "radiative_h",
    "SIGMA_SB",
    "heat_to_fde",
    "ddm_to_heat",
    "DDMResult",
    "ThermoOpticCorrection",
    # 物理常数
    "ADIABATIC",
    "DN_DT_SI",
    "K_SILICON",
    "K_SIO2",
]
