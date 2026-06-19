"""InP 平台器件库（Task 5）。

覆盖 InP（Indium Phosphide）有源集成平台的主要器件，所有参数来自公开文献
真实数据，每个器件附带 ``Source`` 对象以溯源（见项目规则 1.1，禁止假数据）。

本包按器件类别拆分为子模块，通过 ``__init__.py`` 重导出所有 ``make_*``
工厂函数与 ``INP_DEVICES`` 汇总表，保持 ``from polaris.pdk.inp import make_*``
与 ``from polaris.pdk.inp import INP_DEVICES`` 导入路径不变。

子模块：
- ``sources`` — 公共来源对象、设计约束与共享端口辅助函数
- ``passive`` — InP 有源波导、MZM 调制器
- ``active`` — EAM 调制器、光电探测器、SOA 放大器
- ``lasers`` — DFB、DBR、SGDBR、O-band、Coherent、IMOS 激光器

来源文献：
- Soares et al., "InP-Based Foundry PICs for Optical Interconnects",
  Appl. Sci. 2019, 9(8), 1588 — https://doi.org/10.3390/app9081588
  （Fraunhofer HHI InP Foundry：有源波导、EAM、PD、SOA、DFB/DBR 激光器）
- Zhao et al., "Indium Phosphide Photonic Integrated Circuits for Free Space
  Optical Links", IEEE JSTQE 2018, 24(6), 6101806 —
  https://doi.org/10.1109/JSTQE.2018.2866565
  （UCSB SGDBR 激光器、InP MZM）
- AP Technologies, 高功率 InP 器件（SemiNex DFB/SOA）—
  https://www.aptechnologies.co.uk/news
- Coherent, 400mW InP BH DFB 激光器 —
  http://ep.cntronics.com/guide/4364/14539
- Zozulia et al., "IMOS DFB on InP Membrane", Photonics Benelux 2023 —
  https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf

器件清单（12 个）：
1. inp_waveguide — InP 有源波导（宽 1.5-2.5μm，SSC 模场 10×7μm）
2. eam_modulator — EAM 电吸收调制器（带宽 ~45GHz）
3. inp_photodetector — InP 光电探测器（内部响应率 >0.8 A/W）
4. soa — SOA 半导体光放大器（增益 ~4dB/100μm）
5. dfb_laser — DFB 激光器（输出功率 >3mW）
6. dbr_laser — DBR 激光器（输出功率 >3mW）
7. sgdbr_laser — SGDBR 激光器（调谐 1521-1565nm，SMSR >45dB）
8. inp_mzm — InP MZM（1mm 长，集成于 PIC）
9. dfb_laser_oband — O-band DFB 激光器 SemiNex（200-250mW CW @25°C）
10. soa_high_power — 超高功率 SOA（>1W 输出，PCE ~25%@25°C）
11. dfb_laser_coherent — InP BH DFB 激光器 Coherent（1311nm，400mW@55°C）
12. imos_dfb_laser — IMOS DFB 激光器（250μm 长，600μW 光纤功率，25Gbit/s）
"""

from __future__ import annotations

from collections.abc import Callable

from polaris.pdk.device import Device
from polaris.pdk.inp.active import (
    make_eam_modulator,
    make_inp_eam_mason,
    make_inp_photodetector,
    make_inp_soa_koren,
    make_soa,
    make_soa_high_power,
)
from polaris.pdk.inp.lasers import (
    make_dbr_laser,
    make_dfb_laser,
    make_dfb_laser_coherent,
    make_dfb_laser_oband,
    make_imos_dfb_laser,
    make_sgdbr_laser,
)
from polaris.pdk.inp.passive import make_inp_mzm, make_inp_waveguide
from polaris.pdk.inp.tapers import make_inp_euler_bend, make_inp_linear_taper, make_inp_s_bend

# ===========================================================================
# InP 平台器件工厂汇总表
# ===========================================================================
INP_DEVICES: dict[str, Callable[[], Device]] = {
    "inp_waveguide": make_inp_waveguide,
    "eam_modulator": make_eam_modulator,
    "inp_photodetector": make_inp_photodetector,
    "soa": make_soa,
    "dfb_laser": make_dfb_laser,
    "dbr_laser": make_dbr_laser,
    "sgdbr_laser": make_sgdbr_laser,
    "inp_mzm": make_inp_mzm,
    "dfb_laser_oband": make_dfb_laser_oband,
    "soa_high_power": make_soa_high_power,
    "dfb_laser_coherent": make_dfb_laser_coherent,
    "imos_dfb_laser": make_imos_dfb_laser,
    "inp_soa_koren": make_inp_soa_koren,
    "inp_eam_mason": make_inp_eam_mason,
    "inp_linear_taper": make_inp_linear_taper,
    "inp_s_bend": make_inp_s_bend,
    "inp_euler_bend": make_inp_euler_bend,
}

__all__ = [
    "INP_DEVICES",
    "make_dbr_laser",
    "make_dfb_laser",
    "make_dfb_laser_coherent",
    "make_dfb_laser_oband",
    "make_eam_modulator",
    "make_imos_dfb_laser",
    "make_inp_eam_mason",
    "make_inp_euler_bend",
    "make_inp_linear_taper",
    "make_inp_mzm",
    "make_inp_photodetector",
    "make_inp_s_bend",
    "make_inp_soa_koren",
    "make_inp_waveguide",
    "make_sgdbr_laser",
    "make_soa",
    "make_soa_high_power",
]
