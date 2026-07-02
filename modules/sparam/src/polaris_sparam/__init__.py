"""PoLaRIS 频域 S 参数子模块（polaris-sparam）。

提供稳定 Python API，聚焦频域 S 参数模型 + MZI 扫描 + Clements 酉矩阵。
本子模块由旧 polaris-sim 拆分而来（每种仿真独立成包），仅保留 S 参数相关功能。

## Input / Process / Output 三段式（IPO）

- waveguide_s:
  - I: wavelength_um / length_um / neff=2.4 / loss_db_cm=3.0
  - P: S = exp(-α·L/2 + j·2π·neff·L/λ)
  - O: dict[port_pair -> list[complex]]
- mmi_1x2_s / mmi_2x2_s:
  - I: wavelength_um / insertion_loss_db
  - P: sqrt(10^(-il/10)/2) · exp(j·π/2)
  - O: dict[port_pair -> list[complex]]
- grating_coupler_s:
  - I: wavelength_um / peak_wl / bandwidth_3db / insertion_loss_db
  - P: sqrt(10^(-il/10)) · exp(-((λ-peak)/bw)²)
  - O: dict[port_pair -> list[complex]]
- simulate_mzi_sparam:
  - I: wavelength_nm（None 默认 1500-1600nm 101 点）
  - P: T_bar = R²+T²+2RT·cos(2π·neff·ΔL/λ)（Saleh & Teich 2019 §4.4）
  - O: dict{resonant_wavelength_nm, extinction_ratio_db, ...}
- compute_clements_unitary:
  - I: n_modes=4
  - P: Clements 网格交替层左乘分束器（Optica 2016）
  - O: dict{unitary, unitarity_error, is_unitary}

## 稳定 API

- ``waveguide_s(wavelength_um, length_um, neff=2.4, loss_db_cm=3.0) -> dict``
- ``mmi_1x2_s(wavelength_um, insertion_loss_db=0.4) -> dict``
- ``mmi_2x2_s(wavelength_um, insertion_loss_db=0.5) -> dict``
- ``grating_coupler_s(wavelength_um, peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9) -> dict``
- ``simulate_mzi_sparam(wavelength_nm=None) -> dict``
- ``compute_clements_unitary(n_modes=4) -> dict``
- ``port_key(out_port, in_port) -> str``

## 设计原则
- 对外 API 返回 dict（与 polaris-core/route/quantum 等子模块一致）
- 纯 NumPy 实现（R04: 不参与 GPU；R03: 禁止 fall-back，失败即 raise）
- 物理参数来自 SiEPIC EBeam PDK（neff=2.4, MMI split=0.48, GC il=1.9dB）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Simphony SiEPIC 模型库
  https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- SiPANN 解析模型 https://sipann.readthedocs.io/en/latest/models.html
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Saleh & Teich, "Fundamentals of Photonics", Wiley 2019, §4.4（MZI）
- Soldano & Pennings, J. Lightwave Technol. 13(4), 1995（MMI）
  https://ieeexplore.ieee.org/document/374358
- Clements et al., Optica 3(12), 1460 (2016)（Clements 分解）
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
"""

from __future__ import annotations

from polaris_sparam.clements import compute_clements_unitary
from polaris_sparam.models import (
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    port_key,
    waveguide_s,
)
from polaris_sparam.mzi import simulate_mzi_sparam

__version__ = "5.0.0"

__all__ = [
    "waveguide_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "simulate_mzi_sparam",
    "compute_clements_unitary",
    "port_key",
    "__version__",
]
