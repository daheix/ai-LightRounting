"""Lumerical 对齐模块共享物理常数。

为 MODE Solutions / INTERCONNECT / CHARGE 三大子模块提供统一的物理常数，
避免常数重复定义导致的不一致。

## 学术依据

- CODATA 2018 推荐值: https://physics.nist.gov/cuu/Constants/
- SiEPIC EBeam PDK 标准值: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ansys Lumerical: https://www.ansys.com/products/optics

## 来源

- 真空光速 / 电子电荷 / 玻尔兹曼常数 / 真空介电常数：CODATA 2018
- 二氧化硅 / 硅相对介电常数：Sze & Ng, "Physics of Semiconductor Devices",
  3rd ed., 2007, Table 1.1
- 硅 / 二氧化硅折射率 @ 1.55μm：SiEPIC EBeam PDK 标准值
- 硅红外波段折射率（CHARGE 用）：Sze & Ng, §10.3
"""

from __future__ import annotations

# 物理常数（来源: CODATA 2018, https://physics.nist.gov/cuu/Constants/;
#           SiPANN/SiEPIC PDK 标准值, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
_C0 = 2.99792458e8  # 真空光速 (m/s)
_Q = 1.602176634e-19  # 电子电荷 (C)
_KB = 1.380649e-23  # 玻尔兹曼常数 (J/K)
_EPS0 = 8.8541878128e-12  # 真空介电常数 (F/m)
_EPS_SIO2 = 3.9  # 二氧化硅相对介电常数
_EPS_SI = 11.7  # 硅相对介电常数
_N_SILICON = 3.48  # 硅折射率 @ 1.55μm (SiEPIC EBeam PDK)
_N_SIO2 = 1.44  # 二氧化硅折射率 @ 1.55μm
_N_SI_INFRARED = 3.45  # 硅红外波段折射率（CHARGE 用）
