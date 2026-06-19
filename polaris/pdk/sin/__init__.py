"""氮化硅 SiN 平台器件库（Task 4）。

提供 SiN 平台被动器件的 ``Device`` 工厂函数，每个器件的电光参数均来自
公开文献/工艺手册并附 ``Source`` 溯源对象（含 URL），禁止假数据。

本包按器件类别拆分为子模块，通过 ``__init__.py`` 重导出所有 ``make_*``
工厂函数与 ``SIN_DEVICES`` 汇总表，保持 ``from polaris.pdk.sin import make_*``
导入路径不变。

子模块：
- ``sources`` — 公共来源对象与设计约束
- ``passive`` — 条形/双条带/Damascene/ULL 波导、光栅耦合器、材料参数
- ``resonators`` — 双条带环、高 Q 微环谐振器

参数来源（已逐项核对网址可达性与数值区间）：
- IMEC Silicon Nitride Photonics —
  https://www.imec-int.com/en/what-we-offer/development/silicon-nitride
- LioniX TriPleX SiN 波导技术 —
  https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
- Li et al., Appl. Sci. 2023, 13, 3660（Damascene SiN 8 寸） —
  https://doi.org/10.3390/app13063660
- PatSnap Eureka: SiN 波导损耗综述（UCSB/EPFL/Twente/Cornell） —
  https://www.patsnap.com/resources/blog/rd-blog/si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/
- 中国物理学会期刊网：Si3N4 波导材料 —
  https://c.m.163.com/news/a/E9107H030516DOTJ.html
- 台积电 ISSCC 2026 硅光平台 —
  https://cloud.tencent.com.cn/developer/article/2634252
- 三星 300mm 硅光平台 OFC 2026 —
  https://cloud.tencent.com/developer/article/2650050

设计约束（SiN 平台，参考 spec.md）：
- 最小波导间距 2μm（低折射率差平台需更大间距抑制串扰）
- 最小弯曲半径 50-100μm（SiN 弯曲损耗敏感，半径远大于 SOI 的 2-6μm）
"""

from __future__ import annotations

from collections.abc import Callable

from polaris.pdk.device import Device
from polaris.pdk.sin.passive import (
    make_sin_grating_coupler_1d,
    make_sin_material,
    make_sin_thermo_optic,
    make_sin_waveguide_damascene,
    make_sin_waveguide_epfl,
    make_sin_waveguide_lpcvd,
    make_sin_waveguide_pecvd,
    make_sin_waveguide_trench,
    make_sin_waveguide_tsmc,
    make_sin_waveguide_ull,
    make_sin_waveguide_visible,
    make_triplex_double_stripe,
)
from polaris.pdk.sin.resonators import make_sin_ring_double_stripe, make_sin_ring_high_q
from polaris.pdk.sin.tapers import (
    make_sin_directional_coupler,
    make_sin_euler_bend,
    make_sin_linear_taper,
    make_sin_mmi_1x2,
    make_sin_mzi,
    make_sin_s_bend,
)

# ===========================================================================
# SiN 平台器件工厂汇总表
# ===========================================================================
SIN_DEVICES: dict[str, Callable[[], Device]] = {
    "sin_waveguide_lpcvd": make_sin_waveguide_lpcvd,
    "sin_waveguide_pecvd": make_sin_waveguide_pecvd,
    "triplex_double_stripe": make_triplex_double_stripe,
    "sin_waveguide_damascene": make_sin_waveguide_damascene,
    "sin_waveguide_ull": make_sin_waveguide_ull,
    "sin_waveguide_epfl": make_sin_waveguide_epfl,
    "sin_waveguide_trench": make_sin_waveguide_trench,
    "sin_ring_double_stripe": make_sin_ring_double_stripe,
    "sin_waveguide_visible": make_sin_waveguide_visible,
    "sin_ring_high_q": make_sin_ring_high_q,
    "sin_grating_coupler_1d": make_sin_grating_coupler_1d,
    "sin_material": make_sin_material,
    "sin_thermo_optic": make_sin_thermo_optic,
    "sin_waveguide_tsmc": make_sin_waveguide_tsmc,
    "sin_linear_taper": make_sin_linear_taper,
    "sin_s_bend": make_sin_s_bend,
    "sin_euler_bend": make_sin_euler_bend,
    "sin_mmi_1x2": make_sin_mmi_1x2,
    "sin_directional_coupler": make_sin_directional_coupler,
    "sin_mzi": make_sin_mzi,
}

__all__ = [
    "SIN_DEVICES",
    "make_sin_directional_coupler",
    "make_sin_euler_bend",
    "make_sin_grating_coupler_1d",
    "make_sin_linear_taper",
    "make_sin_material",
    "make_sin_mmi_1x2",
    "make_sin_mzi",
    "make_sin_ring_double_stripe",
    "make_sin_ring_high_q",
    "make_sin_s_bend",
    "make_sin_thermo_optic",
    "make_sin_waveguide_damascene",
    "make_sin_waveguide_epfl",
    "make_sin_waveguide_lpcvd",
    "make_sin_waveguide_pecvd",
    "make_sin_waveguide_trench",
    "make_sin_waveguide_tsmc",
    "make_sin_waveguide_ull",
    "make_sin_waveguide_visible",
    "make_triplex_double_stripe",
]
