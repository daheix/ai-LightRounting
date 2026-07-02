"""PoLaRIS 光子仿真子模块（polaris-sim）。

提供稳定 Python API，聚焦频域 S 参数模型 + MZI 扫描 + Clements 酉矩阵 + PAM4 眼图。
不重复 polaris-inverse 的 FDTD 全波仿真（仅用解析模型）。

## 稳定 API

- ``waveguide_s(wavelength_um, length_um, neff=2.4, loss_db_cm=3.0) -> dict``
- ``mmi_1x2_s(wavelength_um, insertion_loss_db=0.4) -> dict``
- ``mmi_2x2_s(wavelength_um, insertion_loss_db=0.5) -> dict``
- ``grating_coupler_s(wavelength_um, peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9) -> dict``
- ``simulate_mzi_sparam(wavelength_nm=None) -> dict``
- ``compute_clements_unitary(n_modes=4) -> dict``
- ``simulate_pam4(n_symbols=1000, bit_rate_gbps=100, samples_per_symbol=16, noise_std=0.05) -> dict``

## 设计原则

- 对外 API 返回 dict（与 polaris-core/route/quantum 等子模块一致）
- 纯 NumPy 实现（R04: 不参与 GPU；R03: 禁止 fall-back，失败即 raise）
- 不修改 src/polaris/ 原代码；本子模块独立迁移解析仿真内核
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
- Shafik et al., IEEE CommSurveys 2016（PAM4 BER/SNR）
  https://ieeexplore.ieee.org/document/7410082
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
"""

from __future__ import annotations

from polaris_sim.clements import compute_clements_unitary
from polaris_sim.models import (
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    port_key,
    waveguide_s,
)
from polaris_sim.mzi import simulate_mzi_sparam
from polaris_sim.pam4 import (
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
    simulate_pam4,
)

__version__ = "5.0.0"

__all__ = [
    "waveguide_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "simulate_mzi_sparam",
    "compute_clements_unitary",
    "simulate_pam4",
    "generate_pam4_signal",
    "compute_ber",
    "compute_snr_db",
    "compute_eye_diagram",
    "port_key",
    "__version__",
]
