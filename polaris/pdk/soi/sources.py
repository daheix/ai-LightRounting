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

# SOI 平台通用设计约束（弯曲半径 2-6μm，波导间距 ≥1μm，见 spec.md）
_SOI_CONSTRAINTS = {
    "min_bend_radius_um": 5.0,  # 高折射率差平台最小弯曲半径 2-6μm，取保守值
    "min_spacing_um": 1.0,  # SOI 波导最小间距 1μm
    "wavelength_nm": 1550,  # 默认 C 波段
}
