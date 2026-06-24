"""SiN 平台公共来源对象与设计约束。

存放氮化硅 SiN 平台的文献溯源 ``Source`` 对象与通用设计约束，供各器件
子模块共享（避免重复构造；``Source`` 采用 ``frozen=True`` 可安全共享）。

来源汇总（spec.md 已逐项核对网址）：
- IMEC Silicon Nitride Photonics
  https://www.imec-int.com/en/what-we-offer/development/silicon-nitride
- LioniX TriPleX SiN 波导技术
  https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
- Li et al., Appl. Sci. 2023, 13, 3660（Damascene SiN 8 寸）
  https://doi.org/10.3390/app13063660
- PatSnap Eureka: SiN 波导损耗综述（UCSB/EPFL/Twente/Cornell）
  https://www.patsnap.com/resources/blog/rd-blog/si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/
- 中国物理学会期刊网：Si3N4 波导材料
  https://c.m.163.com/news/a/E9107H030516DOTJ.html
- 台积电 ISSCC 2026 硅光平台
  https://cloud.tencent.com.cn/developer/article/2634252
- 三星 300mm 硅光平台 OFC 2026
  https://cloud.tencent.com.cn/developer/article/2650050
- SiN 热光系数文献典型值综述（eefocus / ResearchGate）
  https://m.eefocus.com/article/2023416.html
"""

from __future__ import annotations

from polaris.pdk.source import Source

# IMEC LPCVD/PECVD SiN 条形波导（损耗 <0.1 dB/cm，波长 405-2500nm）
_SRC_IMEC_SIN = Source(
    title="Silicon nitride-based photonics",
    authors="IMEC",
    year=2024,
    url="https://www.imec-int.com/en/what-we-offer/development/silicon-nitride",
)
# LioniX TriPleX 双条带 SiN 波导（损耗 <0.1 dB/cm，最低 0.1 dB/m）
_SRC_LIONIX_TRIPLEX = Source(
    title="TriPleX Waveguide Technology",
    authors="LioniX International",
    year=2024,
    url="https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/",
)
# Li et al., Appl. Sci. 2023, 13, 3660（Damascene LPCVD SiN 8 寸晶圆）
_SRC_LI_DAMASCENE = Source(
    title="Process Development of Low-Loss LPCVD Silicon Nitride Waveguides on 8-Inch Wafer",
    authors="Li, Z.; Fan, Z.; Zhou, J.; Cong, Q.; Zeng, X.; Zhang, Y.; Jia, L.",
    year=2023,
    url="https://doi.org/10.3390/app13063660",
)
# PatSnap Eureka: SiN 波导损耗综述（UCSB/EPFL/Twente/Cornell/Myongji）
_SRC_PATSNAP_SIN_LOSS = Source(
    title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
    "Circuits for Optical Gyroscopes",
    authors="PatSnap Eureka",
    year=2026,
    url="https://www.patsnap.com/resources/blog/rd-blog/"
    "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
)
# 三星 300mm 硅光平台 OFC 2026
_SRC_SAMSUNG_OFC2026 = Source(
    title="Samsung 300mm Silicon Photonics Platform (OFC 2026)",
    authors="Samsung",
    year=2026,
    url="https://cloud.tencent.com/developer/article/2650050",
)
# 中国物理学会期刊网：Si3N4 波导材料参数
_SRC_SIN_MATERIAL_CN = Source(
    title="Si3N4 波导材料参数",
    authors="中国物理学会期刊网",
    year=2024,
    url="https://c.m.163.com/news/a/E9107H030516DOTJ.html",
)
# 台积电 ISSCC 2026 硅光平台
_SRC_TSMC_ISSCC2026 = Source(
    title="TSMC ISSCC 2026 Silicon Photonics Platform",
    authors="TSMC",
    year=2026,
    url="https://cloud.tencent.com.cn/developer/article/2634252",
)
# SiN 热光系数文献典型值（eefocus 综述 / ResearchGate）
# 文献典型值 2.4-2.5×10⁻⁵ /K；台积电 ISSCC 2026 报告 2.0×10⁻⁵ /K 为下界
_SRC_EEFOCUS_SIN_TOC = Source(
    title="SiN 热光系数典型值综述",
    authors="eefocus / ResearchGate",
    year=2023,
    url="https://m.eefocus.com/article/2023416.html",
    note="文献典型值 2.4-2.5×10⁻⁵ /K；台积电 ISSCC 2026 报告 2.0×10⁻⁵ /K 为下界",
)

# SiN 平台通用设计约束（最小间距 2μm，最小弯曲半径 100μm）
# 低折射率差平台需更大间距抑制串扰，弯曲半径远大于 SOI 的 2-6μm
# LIGENTEC AN800 SiN 平台最小弯曲半径 100μm
# 来源: https://www.meetoptics.com/suppliers/ligentec
_SIN_CONSTRAINTS: dict = {
    "min_spacing_um": 2.0,
    "min_bend_radius_um": 100.0,
}
