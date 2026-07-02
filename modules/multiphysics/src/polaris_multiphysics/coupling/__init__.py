"""多物理耦合模块（H01-H02，DDM/HEAT → OPTIC 耦合接口）。

本包实现光电子多物理仿真中"电-光"与"热-光"的耦合接口，将 DDM
（漂移-扩散）与 HEAT（热传导）求解器输出的载流子/温度场经相应物理
效应转化为折射率扰动场 Δn(x,y,z)，供下游光学求解器（FDE/FDTD/EME）
消费完成多物理闭环仿真。

## Input / Process / Output 三段式（IPO）

- apply_electro_optic_coupling (H01 等离子体色散，Soref-Bennett 1987):
  - I: ddm_result(electron_density/hole_density [cm^-3]) / wavelength=1.55μm / Γ
  - P: Δn = -α_e·ΔN_e - α_h·ΔN_h + Γ 加权 Δn_eff + 网格重采样
  - O: ElectroOpticCouplingResult(delta_n, delta_n_eff, coefficients, ...)
- apply_thermo_optic_coupling (H02 热光效应，Cocorullo 1999):
  - I: heat_result(temperature [K]) / material='silicon' / Γ / T_ref=300K
  - P: Δn = (dn/dT)·ΔT + Γ 加权 Δn_eff + 网格重采样
  - O: ThermoOpticCouplingResult(delta_n, delta_n_eff, dn_dt, material, ...)

## 物理参数（学术诚信，R02）

- 硅等离子体色散系数 @1.55μm: α_e=8.8e-22, α_h=8.5e-22 cm³
  （Soref & Bennett 1987 IEEE JQE 23(1):123-129）
- 硅热光系数 @1.55μm 室温: dn/dT = 1.86e-4 /K
  （Cocorullo 1999 IEEE JSTQE 5(3):519-521）
- SiO2 热光系数 @1.55μm 室温: dn/dT = 1.0e-5 /K
  （Komma 2012 Appl Phys Lett 101:041905）
- 默认参考温度 T_ref = 300 K

*创新* 接口契约设计：本包产出纯物理量（Δn 场、Δn_eff 标量、dn_dt 系数），
不内部重解光学模式，保持单一职责。下游光学求解器消费这些物理量完成闭环。
底层逻辑：解耦避免循环依赖，电-热-光三方可在各自求解器中独立验证与替换。

*创新* 网格重采样：当 DDM/HEAT 网格与光学网格不一致时，使用 scipy
RegularGridInterpolator 线性插值重采样 Δn 场到光学网格，禁止外推
（越界点 raise，避免物理不一致的边界假数据 fall-back，R03）。

文献来源（≥5，R02 学术诚信）：
1. Soref & Bennett 1987 IEEE J Quantum Electronics 23(1):123-129 —
   等离子体色散经典公式 — https://doi.org/10.1109/JQE.1987.1073206
2. Cocorullo, Iodice, Rendina 1999 IEEE JSTQE 5(3):519-521 —
   硅有效热光系数 — https://doi.org/10.1109/2944.788409
3. Nedeljkovic, Soref, Mashanovich 2011 Opt Express 19(10):9212 —
   硅等离子体色散精修 — https://doi.org/10.1364/OE.19.009212
4. Reed et al. 2010 Nature Photonics 4:518-526 —
   硅光调制器综述 — https://doi.org/10.1038/nphoton.2010.179
5. Komma, Schwarz, Hofmann et al. 2012 Appl Phys Lett 101:041905 —
   Si/SiO2 低温热光系数 — https://doi.org/10.1063/1.4738989
6. Frey, Gordon, Levi 2006 J Appl Phys 99:033107 —
   集成光子热光调制器综述 — https://doi.org/10.1063/1.2170418
7. Snyder & Love 1983 "Optical Waveguide Theory" Springer —
   模式微扰理论 §13 — https://link.springer.com/book/10.1007/978-94-009-6855-1
8. Della Corte et al. 2000 J Opt A 2(6):498-501 —
   硅温度依赖折射率 — https://doi.org/10.1088/1464-4258/2/6/308
9. Timurdogan, Poulton, Watts 2014 Opt Express 22(3):2845 —
   SOI 热光移相器实测 — https://doi.org/10.1364/OE.22.002845
10. Thomson et al. 2011 SPIE Silicon Photonics IV 7943:79430C —
    载流子注入/耗尽型调制器实测 — https://doi.org/10.1117/12.873024

规则依据：R02（学术诚信）/ R03（禁止 fall-back，失败 raise）/
R04（GPU 不参与，纯 numpy/scipy CPU）。
"""

from polaris_multiphysics.coupling.electro_optic import (
    PLASMA_DISPERSION_COEFFS,
    ElectroOpticCouplingResult,
    apply_electro_optic_coupling,
    compute_delta_n_from_carriers,
    compute_effective_index_change,
    get_plasma_dispersion_coefficients,
)
from polaris_multiphysics.coupling.thermo_optic import (
    DEFAULT_T_REF,
    THERMO_OPTIC_COEFFS,
    ThermoOpticCouplingResult,
    apply_thermo_optic_coupling,
    compute_delta_n_from_temperature,
    get_thermo_optic_coefficient,
)

__all__ = [
    # H01 电光耦合（Plasma Dispersion）
    "ElectroOpticCouplingResult",
    "PLASMA_DISPERSION_COEFFS",
    "apply_electro_optic_coupling",
    "compute_delta_n_from_carriers",
    "compute_effective_index_change",
    "get_plasma_dispersion_coefficients",
    # H02 热光耦合（Thermo-Optic）
    "ThermoOpticCouplingResult",
    "THERMO_OPTIC_COEFFS",
    "DEFAULT_T_REF",
    "apply_thermo_optic_coupling",
    "compute_delta_n_from_temperature",
    "get_thermo_optic_coefficient",
]
