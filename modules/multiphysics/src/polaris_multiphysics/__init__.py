"""PoLaRIS 多物理场仿真子模块（polaris-multiphysics）。

提供光电子多物理场仿真全栈 API：半导体漂移-扩散（DDM）、热传导（HEAT）、
2.5D VarFDTD、严格耦合波（RCWA）、有限元时域（FETD）、电-光/热-光耦合、
TCAD 2D 热仿真。由 v4 旧包 ``polaris.sim/{ddm,heat,varfdtd,rcwa,fetd,
multiphysics}`` 与 ``polaris.device`` 迁移整合而来（R13 不保留 v4 兼容）。

## Input / Process / Output 三段式（IPO）

- DDM 漂移扩散（DdmSolver，Scharfetter-Gummel 1969 + 阻尼牛顿法）:
  - I: DdmConfig(nx, dx, Na, Nd, va, vc) — PN 结网格 + 掺杂 + 偏置
  - P: Poisson + 电子/空穴连续性联立 + SG 离散 + SRH 复合 + Armijo 线搜索
  - O: DdmResult(potential, n, p, electron_density, hole_density, current_density)
- HEAT 稳态热传导（HeatSolver，5 点有限差分）:
  - I: HeatConfig(k_arr, q_arr, dx, dy) + 5 类边界 BcSpec
  - P: ∇·(k∇T)+Q=0 调和平均热导率 + scipy.sparse.linalg.spsolve
  - O: HeatResult(temperature, dx, dy)
- VarFDTD 2.5D（VarFdtdSolver，EIM + 2D Yee leapfrog + CPML + TFSF）:
  - I: VarFdtdConfig(wavelength, dx, dy, n_eff_arr, n_steps, pml_config, ...)
  - P: EIM 折叠 → 2D Yee leapfrog + CPML 吸收 + TFSF 注入 + DFT 监视
  - O: VarFdtdResult(e_z, h_x, h_y, s_params, dft_results, energy_history)
- RCWA 严格耦合波（solve_rcwa_1d/2d，Moharam 1995 ETM + Li 1996 FFF + Redheffer 星积）:
  - I: RcwaConfig1D/2D(wavelength, layers, n_harmonics, polarization)
  - P: 傅里叶因子化 + 本征模 + 界面/传播 S 矩阵 + Redheffer 星积级联
  - O: RcwaResult1D/2D(s_matrix, t_eff, r_eff, ...)
- FETD 有限元时域（FetdSolver，Newmark-β 无条件稳定）:
  - I: FetdConfig(mesh, materials, dt, sources) — 四面体/六面体网格
  - P: 质量/刚度/阻尼矩阵组装 + Newmark-β (β=0.25, γ=0.5) 时间积分
  - O: FetdResult(e_field, h_field, energy_history)
- 电-光/热-光耦合（apply_electro_optic_coupling / apply_thermo_optic_coupling）:
  - I: ddm_result/heat_result + optical_grid + wavelength/material/Γ
  - P: Soref-Bennett 等离子体色散 / Cocorullo 热光效应 + 网格重采样
  - O: ElectroOpticCouplingResult / ThermoOpticCouplingResult (delta_n, delta_n_eff)
- TCAD 2D 热仿真（ThermalSolver2D，5 点 FDM + Carslaw-Jaeger 线热源）:
  - I: layers([ThermalLayer]) + width_um + nx + substrate_temp_k
  - P: ∇·(k∇T)+Q=0 5 点 FDM + 调和平均 k_face + spsolve
  - O: T(nz,nx) [K] / max_temperature_k / thermal_crosstalk_matrix

## 设计原则

- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现（禁止 CuPy/CUDA/ROCm）
- R03 禁止 fall-back: 失败即 raise，无静默兜底/假数据
- R02 学术诚信: 所有物理常量/公式可溯源（CODATA 2018 + Soref-Bennett 1987 +
  Cocorullo 1999 + Scharfetter-Gummel 1969 + Moharam 1995 + Chang 1980 等）
- R13 不保留 v4 兼容: 仅保留最新代码，旧包依赖已全部重写为 polaris_multiphysics.*

## 来源（R02 学术诚信，≥5 个文献 URL）

- Scharfetter & Gummel 1969 IEEE TED 16(1):64-77 —
  https://doi.org/10.1109/T-ED.1969.16766
- Soref & Bennett 1987 IEEE JQE 23(1):123-129 —
  https://doi.org/10.1109/JQE.1987.1073206
- Cocorullo 1999 IEEE JSTQE 5(3):519-521 —
  https://doi.org/10.1109/2944.788409
- Moharam 1995 JOSA A 12:1077 (ETM) —
  https://doi.org/10.1364/JOSAA.12.001077
- Li 1996 JOSA A 13:1870 (FFF) —
  https://doi.org/10.1364/JOSAA.13.001870
- Chang 1980 IEEE TMTT 28(8):889 (EIM) —
  https://doi.org/10.1109/TMTT.1980.1130551
- Yee 1966 IEEE TAP 14(3):302-307 —
  https://doi.org/10.1109/TAP.1966.1138693
- Newmark 1959 ASCE J Eng Mech Div 85(3):67-94 —
  https://doi.org/10.1061/JMCEA3.0000097
- Redheffer 1959 J Math Mech —
  https://www.jstor.org/stable/24900576
- Carslaw & Jaeger 1959 "Conduction of Heat in Solids" §10.4 —
  https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
- Taflove & Hagness 2005 "Computational Electrodynamics" —
  https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
- Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
  https://link.springer.com/book/10.1007/978-3-7091-8752-4
- Jin 2014 "The Finite Element Method in Electromagnetics" 3rd ed. —
  https://onlinelibrary.wiley.com/doi/book/10.1002/9781118576637
- Roden & Gedney 2000 CPML —
  https://doi.org/10.1002/1099-1207(20000612)12:3%3C284::AID-MMPS5%3E3.0.CO;2-K
- NIST CODATA 2018 — https://physics.nist.gov/cuu/Constants/
"""

from __future__ import annotations

# DDM 漂移扩散
from polaris_multiphysics.ddm import (
    DdmConfig,
    DdmResult,
    DdmSolver,
    GummelSolver,
    solve_ddm,
    solve_ddm_gummel,
)
# HEAT 热传导
from polaris_multiphysics.heat import (
    HeatConfig,
    HeatResult,
    HeatSolver,
    TransientHeatSolver,
    solve_heat,
    solve_transient_heat,
)
# VarFDTD 2.5D
from polaris_multiphysics.varfdtd import (
    EffectiveIndexResult,
    VarFdtdConfig,
    VarFdtdResult,
    VarFdtdSolver,
    compute_effective_index,
    solve_varfdtd,
)
# RCWA 严格耦合波
from polaris_multiphysics.rcwa import (
    RcwaConfig1D,
    RcwaConfig2D,
    RcwaResult1D,
    RcwaResult2D,
    solve_rcwa_1d,
    solve_rcwa_2d,
)
# FETD 有限元时域
from polaris_multiphysics.fetd import (
    FetdConfig,
    FetdResult,
    FetdSolver,
    NewmarkIntegrator,
)
# 电-光/热-光耦合
from polaris_multiphysics.coupling import (
    DEFAULT_T_REF,
    PLASMA_DISPERSION_COEFFS,
    THERMO_OPTIC_COEFFS,
    ElectroOpticCouplingResult,
    ThermoOpticCouplingResult,
    apply_electro_optic_coupling,
    apply_thermo_optic_coupling,
    compute_delta_n_from_carriers,
    compute_delta_n_from_temperature,
)
# TCAD 2D 热仿真
from polaris_multiphysics.tcad_thermal import (
    ThermalLayer,
    ThermalSolver2D,
)

__version__ = "5.0.0"

__all__ = [
    "__version__",
    # DDM
    "DdmConfig",
    "DdmResult",
    "DdmSolver",
    "GummelSolver",
    "solve_ddm",
    "solve_ddm_gummel",
    # HEAT
    "HeatConfig",
    "HeatResult",
    "HeatSolver",
    "TransientHeatSolver",
    "solve_heat",
    "solve_transient_heat",
    # VarFDTD
    "EffectiveIndexResult",
    "VarFdtdConfig",
    "VarFdtdResult",
    "VarFdtdSolver",
    "compute_effective_index",
    "solve_varfdtd",
    # RCWA
    "RcwaConfig1D",
    "RcwaConfig2D",
    "RcwaResult1D",
    "RcwaResult2D",
    "solve_rcwa_1d",
    "solve_rcwa_2d",
    # FETD
    "FetdConfig",
    "FetdResult",
    "FetdSolver",
    "NewmarkIntegrator",
    # 耦合
    "ElectroOpticCouplingResult",
    "ThermoOpticCouplingResult",
    "PLASMA_DISPERSION_COEFFS",
    "THERMO_OPTIC_COEFFS",
    "DEFAULT_T_REF",
    "apply_electro_optic_coupling",
    "apply_thermo_optic_coupling",
    "compute_delta_n_from_carriers",
    "compute_delta_n_from_temperature",
    # TCAD 热仿真
    "ThermalLayer",
    "ThermalSolver2D",
]
