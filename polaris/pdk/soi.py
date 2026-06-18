"""硅光 SOI 平台器件库（Task 3）。

覆盖硅光 SOI（Silicon-on-Insulator，220nm/300nm SOI 工艺）平台的被动与主动
器件真实参数模型。每个器件参数均来自公开文献/工艺手册并附带 ``Source`` 溯源
（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

本模块保留波导与耦合器工厂函数；MMI/MZI/微环/Y 分支/crossing/热光移相器
拆分至 ``soi_passive.py``，MZM/MRM/Ge PD/双环滤波器拆分至 ``soi_active.py``。
``SOI_DEVICES`` 汇总表在此重导出全部 18 个器件工厂函数。

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

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.soi_active import (
    make_double_ring_filter,
    make_ge_photodetector,
    make_mrm_modulator,
    make_mzm_modulator,
)
from polaris.pdk.soi_passive import (
    make_crossing,
    make_mmi_1x2,
    make_mmi_2x2,
    make_mzi,
    make_ring_resonator,
    make_thermo_optic_phase_shifter,
    make_y_branch,
)
from polaris.pdk.source import Source

# ---------------------------------------------------------------------------
# 公共来源对象（避免重复构造；frozen=True 可安全共享）
# ---------------------------------------------------------------------------
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


# ===========================================================================
# 1. 条形波导 strip_waveguide
# ===========================================================================
def make_strip_waveguide() -> Device:
    """条形波导（strip waveguide，全刻蚀）。

    厚 220nm，宽 450-500nm（单模 TE0），传播损耗 1-3 dB/cm。
    来源：AIM Photonics 教程 + 硅光工艺平台比较（iccsz.com）。
    """
    length = 10.0  # 默认 10μm 直波导
    width = 0.5  # 500nm 单模
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="out", x=length, y=0.0, direction=Direction.EAST,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_strip_waveguide",
        platform="SOI",
        category="passive",
        name="strip_waveguide",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "thickness_nm": 220,  # SOI 顶层硅厚 220nm
            "width_nm": 500,  # 单模条形波导宽 450-500nm
            "loss_db_cm": 2.0,  # 传播损耗 1-3 dB/cm
            "wavelength_nm": 1550,
            "mode": "TE0",
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. 肋形波导 rib_waveguide
# ===========================================================================
def make_rib_waveguide() -> Device:
    """肋形波导（rib waveguide，浅刻蚀）。

    SOI 厚 220nm，slab 高 90nm，浅刻蚀，损耗更低，适用于长距离布线。
    来源：硅光工艺平台比较（iccsz.com）；三星 Si rib 损耗 0.7 dB/cm。
    """
    length = 10.0
    width = 0.5
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="rib", width=width),
        Port(name="out", x=length, y=0.0, direction=Direction.EAST,
             waveguide_type="rib", width=width),
    ]
    return Device(
        device_id="soi_rib_waveguide",
        platform="SOI",
        category="passive",
        name="rib_waveguide",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "thickness_nm": 220,  # SOI 顶层硅厚 220nm
            "slab_height_nm": 90,  # slab 残留高度 90nm（浅刻蚀）
            "width_nm": 500,
            "loss_db_cm": 0.7,  # 三星 Si rib 损耗 0.7 dB/cm
            "wavelength_nm": 1550,
            "mode": "TE0",
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 3. 弯曲波导 bend
# ===========================================================================
def make_bend() -> Device:
    """弯曲波导（90° 圆弧 bend）。

    最小弯曲半径 2-6μm（高折射率差 SOI 平台），损耗 0.01-0.1 dB/90°。
    来源：台积电 ISSCC 2026 硅光子学平台解析。
    """
    radius = 5.0  # 默认半径 5μm（区间 2-6μm）
    width = 0.5
    # 90° 弯曲：圆心 (R, 0)，弧从 (0,0) 切向 +x 到 (R,R) 切向 +y
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="out", x=radius, y=radius, direction=Direction.NORTH,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_bend",
        platform="SOI",
        category="passive",
        name="bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=radius, ymax=radius),
        params={
            "radius_um": radius,  # 弯曲半径 2-6μm
            "angle_deg": 90,  # 90° 弧
            "loss_db_90": 0.05,  # 损耗 0.01-0.1 dB/90°
            "width_nm": 500,
            "wavelength_nm": 1550,
        },
        source=_SRC_TSMC,
        constraints={
            "min_bend_radius_um": 2.0,  # 高折射率差平台最小弯曲半径
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 4. 定向耦合器 directional_coupler
# ===========================================================================
def make_directional_coupler() -> Device:
    """定向耦合器（directional coupler, DC）。

    间隙 100-300nm，耦合长度 5-20μm，实现 3dB 功率分束。
    来源：AIM Photonics 教程。
    """
    length = 10.0  # 耦合长度 5-20μm
    width = 0.5
    gap = 0.5  # 端口间距（波导间物理间距，μm）
    ports = [
        Port(name="in1", x=0.0, y=gap / 2, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="in2", x=0.0, y=-gap / 2, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="out1", x=length, y=gap / 2, direction=Direction.EAST,
             waveguide_type="strip", width=width),
        Port(name="out2", x=length, y=-gap / 2, direction=Direction.EAST,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_directional_coupler",
        platform="SOI",
        category="passive",
        name="directional_coupler",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-gap / 2 - width / 2,
                         xmax=length, ymax=gap / 2 + width / 2),
        params={
            "gap_nm": 200,  # 耦合间隙 100-300nm
            "coupling_length_um": 10.0,  # 耦合长度 5-20μm
            "width_nm": 500,
            "coupling_ratio": 0.5,  # 3dB 耦合
            "loss_db": 0.2,
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 9. 光栅耦合器 1D Si grating_coupler_1d
# ===========================================================================
def make_grating_coupler_1d() -> Device:
    """一维硅光栅耦合器（1D Si grating coupler）。

    峰值耦合损耗 1.9dB，1-dB 带宽 27nm，O 波段 TE 偏振。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    width = 12.0  # 光栅区宽度
    length = 20.0  # 光栅区长度
    ports = [
        # 波导端口（水平出射）
        Port(name="wg", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id="soi_grating_coupler_1d",
        platform="SOI",
        category="passive",
        name="grating_coupler_1d",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "peak_coupling_loss_db": 1.9,  # 峰值耦合损耗 1.9dB
            "bandwidth_1db_nm": 27,  # 1-dB 带宽 27nm
            "wavelength_nm": 1310,  # O 波段
            "polarization": "TE",
            "grating_type": "1D Si",
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )


# ===========================================================================
# 10. 光栅耦合器 2D Si grating_coupler_2d
# ===========================================================================
def make_grating_coupler_2d() -> Device:
    """二维硅光栅耦合器（2D Si grating coupler）。

    耦合损耗 2.4dB，1-dB 带宽 17nm，TE/TM 双模兼容。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    size = 15.0  # 2D 光栅方形边长
    ports = [
        Port(name="wg", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id="soi_grating_coupler_2d",
        platform="SOI",
        category="passive",
        name="grating_coupler_2d",
        ports=ports,
        bbox=BoundingBox(xmin=-size / 2, ymin=-size / 2,
                         xmax=size / 2, ymax=size / 2),
        params={
            "coupling_loss_db": 2.4,  # 耦合损耗 2.4dB
            "bandwidth_1db_nm": 17,  # 1-dB 带宽 17nm
            "wavelength_nm": 1310,  # O 波段
            "polarization": "TE/TM",  # TE/TM 双模兼容
            "grating_type": "2D Si",
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )


# ===========================================================================
# 11. 端面耦合器 edge_coupler
# ===========================================================================
def make_edge_coupler() -> Device:
    """端面耦合器（edge coupler，模斑转换器 SSC）。

    耦合损耗 ~2dB（传统），优化后 0.2-1dB，宽带光纤-芯片耦合。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 200.0  # 锥形长度
    width = 0.5
    ports = [
        # 芯片端面侧（光纤耦合，宽端口）
        Port(name="fiber", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=3.0),
        # 波导侧（窄端口）
        Port(name="wg", x=length, y=0.0, direction=Direction.EAST,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_edge_coupler",
        platform="SOI",
        category="passive",
        name="edge_coupler",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-1.5, xmax=length, ymax=1.5),
        params={
            "coupling_loss_db": 2.0,  # 传统耦合损耗 ~2dB
            "optimized_loss_db": 0.5,  # 优化后 0.2-1dB
            "bandwidth_nm": 200,  # 宽带
            "taper_length_um": 200.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


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
}
