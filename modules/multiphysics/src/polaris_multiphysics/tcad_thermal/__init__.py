"""TCAD 热仿真子包（2D 稳态/瞬态热传导 + 热串扰 + TCAD-Aware 器件模型）。

由 v4 ``polaris.device`` 迁移而来，含 7 个子模块：
- solver.ThermalSolver2D     : 2D 稳态热传导有限差分（5 点中心差分 + 调和平均热导率）
- transient.CrankNicolson2D  : 2D 瞬态热传导 Crank-Nicolson 隐式时间步进
- tcad_model.TCADAwareModel  : TCAD-Aware 器件模型（掺杂/等离子体色散）
- packaging.PackageDesigner  : 封装热设计
- testchip.TestChipDesigner  : 测试芯片设计
- m3.M3Deliverable           : M3 里程碑交付物
- package                    : 聚合 re-export

## Input / Process / Output 三段式（IPO）

- ThermalSolver2D.solve_steady_state:
  - I: layers([ThermalLayer]) / width_um / nx / substrate_temp_k
  - P: ∇·(k∇T)+Q=0 5 点 FDM + 调和平均 k_face + spsolve 直接解
  - O: T(nz,nx) [K] / max_temperature_k() / avg_temp_at_layer()
- ThermalSolver2D.thermal_crosstalk_matrix:
  - I: heater_positions_um / device_positions_um / heater_power_mw
  - P: Carslaw-Jaeger §10.4 2D 线热源 Green's 函数 ΔT=(P'/2πk)·ln(2h/r)
  - O: 串扰矩阵 (n_heaters × n_devices) [K]

## 物理参数（学术诚信，R02）

- 硅热导率 k_Si = 148 W/(m·K)（Cocorullo 1999 / Incropera）
- 硅密度 ρ_Si = 2330 kg/m³，定压热容 Cp_Si = 700 J/(kg·K)（Incropera 表 A.1）
- SiO2 热导率 k_SiO2 = 1.4 W/(m·K)
- Stefan-Boltzmann σ_SB = 5.670374419e-8 W/(m²·K⁴)（CODATA 2018）

*创新* 严格镜像源法：r_ref = 2h（热源到镜像源距离），替代无溯源魔法数，
基于 Carslaw & Jaeger §10.4 (iv) 镜像源 Green's 函数解析解。

文献来源（≥5，R02 学术诚信）：
1. Carslaw & Jaeger 1959 "Conduction of Heat in Solids" 2nd ed. Oxford §10.4 —
   https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
2. Cocorullo 1999 Electron. Lett. 35(6):453-455 —
   https://doi.org/10.1049/el:19990151
3. Incropera & DeWitt "Fundamentals of Heat and Mass Transfer" §4.4 —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
4. Taflove & Hagness 2005 Computational Electrodynamics §4 —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
5. Scharfetter & Gummel 1969 IEEE TED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16767
6. Selberherr 1984 Analysis and Simulation of Semiconductor Devices —
   https://link.springer.com/book/10.1007/978-3-7091-8752-4
7. Crank & Nicolson 1947 Proc. Camb. Phil. Soc. 43(1):50-67 —
   https://doi.org/10.1017/S0305004100023197
8. Pant et al. 2021 Optics Express 29(23):36461-36468 —
   https://doi.org/10.1364/OE.426748
9. Coenen et al. 2024 Photonics 11(7):603 —
   https://doi.org/10.3390/photonics11070603
10. Lumerical HEAT — https://optics.ansys.com/hc/en-us/articles/47617107334291

规则依据：R02（学术诚信）/ R03（禁止 fall-back）/ R04（纯 numpy/scipy CPU）。
"""

from polaris_multiphysics.tcad_thermal.solver import ThermalLayer, ThermalSolver2D
from polaris_multiphysics.tcad_thermal.transient import (
    CrankNicolson2D,
    ThermalLayer2D,
)
from polaris_multiphysics.tcad_thermal.tcad_model import (
    DopingType,
    TCADAwareModel,
    TCADDeviceSpec,
)
from polaris_multiphysics.tcad_thermal.packaging import (
    PackageDesigner,
    PackageSpec,
    PackageType,
)
from polaris_multiphysics.tcad_thermal.testchip import (
    TestChipDesigner,
    TestStructure,
    TestType,
)
from polaris_multiphysics.tcad_thermal.m3 import M3Deliverable

__all__ = [
    # 热仿真引擎
    "ThermalLayer",
    "ThermalSolver2D",
    "ThermalLayer2D",
    "CrankNicolson2D",
    # TCAD-Aware 器件模型
    "DopingType",
    "TCADDeviceSpec",
    "TCADAwareModel",
    # 封装设计
    "PackageType",
    "PackageSpec",
    "PackageDesigner",
    # 测试芯片设计
    "TestType",
    "TestStructure",
    "TestChipDesigner",
    # M3 交付
    "M3Deliverable",
]
