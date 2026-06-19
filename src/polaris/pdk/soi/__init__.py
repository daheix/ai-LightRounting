"""硅光 SOI 平台器件库（Task 3）。

覆盖硅光 SOI（Silicon-on-Insulator，220nm/300nm SOI 工艺）平台的被动与主动
器件真实参数模型。每个器件参数均来自公开文献/工艺手册并附带 ``Source`` 溯源
（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

本包按器件类别拆分为子模块，通过 ``__init__.py`` 重导出所有 ``make_*``
工厂函数与 ``SOI_DEVICES`` 汇总表，保持 ``from polaris.pdk.soi import make_*``
导入路径不变。

子模块：
- ``sources`` — 公共来源对象与设计约束
- ``passive`` — 波导、弯曲、Y 分支、crossing、光栅/端面耦合器
- ``couplers`` — 定向耦合器（DC）、MMI、MZI 等片上耦合器/干涉仪
- ``resonators`` — 微环谐振器、双环滤波器
- ``active`` — 热光移相器、MZM/MRM 调制器、Ge 探测器

来源汇总（spec.md 已逐项核对网址）：
- AIM Photonics 无源硅基光电子芯片元件教程
  https://www.latitudeda.com/document/716
- 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
  http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm
- 台积电 ISSCC 2026 硅光子学平台解析
  https://cloud.tencent.com.cn/developer/article/2634252
- 三星 300mm 硅光平台 OFC 2026
  https://cloud.tencent.com/developer/article/2650050

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。
"""

from __future__ import annotations

from collections.abc import Callable

from polaris.pdk.device import Device
from polaris.pdk.soi.active import (
    make_avalanche_photodetector,
    make_ge_photodetector,
    make_mrm_modulator,
    make_mzm_modulator,
    make_thermo_optic_phase_shifter,
    make_thermo_optic_switch,
    make_thermo_tuned_ring_modulator,
    make_traveling_wave_mzm,
)
from polaris.pdk.soi.couplers import (
    make_directional_coupler,
    make_mmi_1x2,
    make_mmi_1x4,
    make_mmi_2x2,
    make_mmi_4x4,
    make_mzi,
)
from polaris.pdk.soi.passive import (
    make_awg,
    make_bend,
    make_crossing,
    make_edge_coupler,
    make_grating_coupler_1d,
    make_grating_coupler_2d,
    make_metasurface_coupler,
    make_photonic_crystal_waveguide,
    make_rib_waveguide,
    make_strip_waveguide,
    make_y_branch,
)
from polaris.pdk.soi.resonators import make_double_ring_filter, make_ring_resonator
from polaris.pdk.soi.tapers import make_euler_bend, make_linear_taper, make_s_bend

# ===========================================================================
# SOI 平台器件工厂汇总表
# ===========================================================================
SOI_DEVICES: dict[str, Callable[[], Device]] = {
    "strip_waveguide": make_strip_waveguide,
    "rib_waveguide": make_rib_waveguide,
    "bend": make_bend,
    "directional_coupler": make_directional_coupler,
    "mmi_1x2": make_mmi_1x2,
    "mmi_2x2": make_mmi_2x2,
    "mzi": make_mzi,
    "ring_resonator": make_ring_resonator,
    "grating_coupler_1d": make_grating_coupler_1d,
    "grating_coupler_2d": make_grating_coupler_2d,
    "edge_coupler": make_edge_coupler,
    "y_branch": make_y_branch,
    "crossing": make_crossing,
    "thermo_optic_phase_shifter": make_thermo_optic_phase_shifter,
    "mzm_modulator": make_mzm_modulator,
    "mrm_modulator": make_mrm_modulator,
    "ge_photodetector": make_ge_photodetector,
    "double_ring_filter": make_double_ring_filter,
    "traveling_wave_mzm": make_traveling_wave_mzm,
    "thermo_tuned_ring_modulator": make_thermo_tuned_ring_modulator,
    "thermo_optic_switch": make_thermo_optic_switch,
    "avalanche_photodetector": make_avalanche_photodetector,
    "mmi_1x4": make_mmi_1x4,
    "mmi_4x4": make_mmi_4x4,
    "awg": make_awg,
    "photonic_crystal_waveguide": make_photonic_crystal_waveguide,
    "metasurface_coupler": make_metasurface_coupler,
    "linear_taper": make_linear_taper,
    "s_bend": make_s_bend,
    "euler_bend": make_euler_bend,
}

__all__ = [
    "SOI_DEVICES",
    "make_avalanche_photodetector",
    "make_awg",
    "make_bend",
    "make_crossing",
    "make_directional_coupler",
    "make_double_ring_filter",
    "make_edge_coupler",
    "make_euler_bend",
    "make_ge_photodetector",
    "make_grating_coupler_1d",
    "make_grating_coupler_2d",
    "make_linear_taper",
    "make_metasurface_coupler",
    "make_mmi_1x2",
    "make_mmi_1x4",
    "make_mmi_2x2",
    "make_mmi_4x4",
    "make_mrm_modulator",
    "make_mzi",
    "make_mzm_modulator",
    "make_photonic_crystal_waveguide",
    "make_rib_waveguide",
    "make_ring_resonator",
    "make_s_bend",
    "make_strip_waveguide",
    "make_thermo_optic_phase_shifter",
    "make_thermo_optic_switch",
    "make_thermo_tuned_ring_modulator",
    "make_traveling_wave_mzm",
    "make_y_branch",
]
