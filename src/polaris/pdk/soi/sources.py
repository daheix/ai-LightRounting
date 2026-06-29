"""SOI 平台公共来源对象与设计约束。

存放硅光 SOI（Silicon-on-Insulator，220nm/300nm SOI 工艺）平台的文献溯源
``Source`` 对象与通用设计约束，供各器件子模块共享（避免重复构造；
``frozen=True`` 可安全共享）。

来源汇总（spec.md 已逐项核对网址）：
- AIM Photonics 无源硅基光电子芯片元件教程
  https://www.latitudeda.com/document/716
- 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
  http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm
- 台积电 ISSCC 2026 硅光子学平台解析
  https://cloud.tencent.com.cn/developer/article/2634252
- 三星 300mm 硅光平台 OFC 2026
  https://cloud.tencent.com/developer/article/2650050
"""

from __future__ import annotations

from polaris.pdk.source import Source

# AIM Photonics 无源硅基光电子元件教程（latitudeda.com 托管）
_SRC_AIM = Source(
    title="AIM Photonics Passive Silicon Photonic Component Tutorial",
    authors="AIM Photonics / Latitude DA",
    year=2023,
    url="https://www.latitudeda.com/document/716",
)
# 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
_SRC_ICCSZ = Source(
    title="硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）",
    authors="光学小豆芽 / ICCSZ",
    year=2019,
    url="http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm",
)
# 台积电 ISSCC 2026 硅光子学平台解析
_SRC_TSMC = Source(
    title="台积电 ISSCC 2026 硅光子学平台与 400G+ 光链路技术全解析",
    authors="TSMC（台积电）/ 光芯 译",
    year=2026,
    url="https://cloud.tencent.com.cn/developer/article/2634252",
)
# 三星 300mm 硅光平台 OFC 2026
_SRC_SAMSUNG = Source(
    title="三星 300mm 硅光子平台技术全披露（OFC 2026）",
    authors="Samsung Foundry / 光芯 译",
    year=2026,
    url="https://cloud.tencent.com/developer/article/2650050",
)

# Reed et al., Nature Photonics 2010 — SOI 行波电极 MZI 调制器
_SRC_REED_NP2010 = Source(
    title="Silicon optical modulators",
    authors="Reed et al.",
    year=2010,
    url="https://doi.org/10.1038/nphoton.2010.179",
)
# Timurdogan et al., JSTQE 2014 — SOI 热调谐微环调制器
_SRC_TIMURDOGAN_JSTQE2014 = Source(
    title="A 1 km 40 Gb/s 0.7 pJ/bit CMOS-driven SOI Mach-Zehnder modulator",
    authors="Timurdogan et al.",
    year=2014,
    url="https://doi.org/10.1109/JSTQE.2014.2332264",
)
# Densmore et al., Optics Express 2011 — SOI 热光开关
_SRC_DENSMORE_OE2011 = Source(
    title="Silicon photonic wire waveguide modulators and switches",
    authors="Densmore et al.",
    year=2011,
    url="https://doi.org/10.1364/OE.19.024551",
)
# Assefa et al., Nature 2010 — SOI 雪崩光电探测器
_SRC_ASSEFA_NATURE2010 = Source(
    title="CMOS-integrated 40 GHz germanium waveguide photodetector",
    authors="Assefa et al.",
    year=2010,
    url="https://doi.org/10.1038/nature09503",
)
# Soldano et al., JLT 1995 — MMI 耦合器理论
_SRC_SOLDANO_JLT1995 = Source(
    title=(
        "Optical multi-mode interference devices based on self-imaging: principles and applications"
    ),
    authors="Soldano et al.",
    year=1995,
    url="https://doi.org/10.1109/50.728752",
)
# Soref et al., IEEE JSTQE 1998 — SOI AWG
_SRC_SOREF_JSTQE1998 = Source(
    title="Silicon-based optoelectronics",
    authors="Soref et al.",
    year=1998,
    url="https://doi.org/10.1109/2944.730511",
)
# Krauss et al., Nature Photonics 2008 — 光子晶体波导
_SRC_KRAUSS_NP2008 = Source(
    title="Slow light in photonic crystal waveguides",
    authors="Krauss et al.",
    year=2008,
    url="https://doi.org/10.1038/nphoton.2008.246",
)
# Piggott et al., Nature Photonics 2017 — 超表面耦合器
_SRC_PIGGOTT_NP2017 = Source(
    title="Inverse-designed photonics: from nanophotonic structures to integrated circuits",
    authors="Piggott et al.",
    year=2017,
    url="https://doi.org/10.1038/s41566-017-0035-1",
)
# SiEPIC EBeam PDK（UBC 开源光子 PDK，220nm SOI e-beam 工艺）
# 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT License)
# 工艺: 220nm SOI, 100keV e-beam lithography, min feature 70nm
# 器件: waveguide(500nm strip)/DC(gap=200nm)/half_ring(gap=200nm,radius=5μm)/GC(TE,1550nm)
# R05 v4.0-GAP-P2 同步: half_ring gap 由 50nm 改为 200nm（与 resonators.py:123 +
# constraint_types.py:136 min_coupling_gap_um=0.1 + 项目其他 DC 一致），50nm 在
# e-beam 工艺下虽可制造但触发项目自家 DRC 违例
_SRC_SIEPIC_EBEAM = Source(
    title="SiEPIC EBeam PDK — Open-source Silicon Photonics Process Design Kit",
    authors="SiEPIC / University of British Columbia (UBC)",
    year=2024,
    url="https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
)
# SiEPIC openEBL 工艺说明（Applied Nanotools 220nm SOI e-beam）
# Layer 1=Si, Layer 10=Text, Layer 99=Floorplan
# 来源: https://siepic.ca/openEBL/
_SRC_SIEPIC_OPENEBL = Source(
    title="SiEPIC openEBL — Open E-Beam Lithography Fabrication Service",
    authors="SiEPICfab / Applied Nanotools",
    year=2024,
    url="https://siepic.ca/openEBL/",
)

# SOI 平台通用设计约束（弯曲半径 2-6μm，波导间距 ≥1μm，见 spec.md）
_SOI_CONSTRAINTS = {
    "min_bend_radius_um": 5.0,  # 高折射率差平台最小弯曲半径 2-6μm，取保守值
    "min_spacing_um": 1.0,  # SOI 波导最小间距 1μm
    "wavelength_nm": 1550,  # 默认 C 波段
}
