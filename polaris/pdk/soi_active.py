"""硅光 SOI 平台主动器件库（自 soi.py 拆分）。

覆盖硅光 SOI 平台的 MZM/MRM 调制器、Ge 光电探测器、双环滤波器等主动器件
真实参数模型。每个器件参数均来自公开文献/工艺手册并附带 ``Source`` 溯源
（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

来源汇总（spec.md 已逐项核对网址）：
- 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
  http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm
- 三星 300mm 硅光平台 OFC 2026
  https://cloud.tencent.com/developer/article/2650050

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source

# ---------------------------------------------------------------------------
# 公共来源对象（避免重复构造；frozen=True 可安全共享）
# ---------------------------------------------------------------------------
# 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
_SRC_ICCSZ = Source(
    title="硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）",
    authors="光学小豆芽 / ICCSZ",
    year=2019,
    url="http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm",
)
# 三星 300mm 硅光平台 OFC 2026
_SRC_SAMSUNG = Source(
    title="三星 300mm 硅光子平台技术全披露（OFC 2026）",
    authors="Samsung Foundry / 光芯 译",
    year=2026,
    url="https://cloud.tencent.com/developer/article/2650050",
)


# ===========================================================================
# MZ 调制器 mzm_modulator
# ===========================================================================
def make_mzm_modulator() -> Device:
    """马赫-曾德尔调制器（MZM，基于 PN 结载流子色散）。

    带宽 ~20GHz，插损 ~5dB，VπL ~2V·cm。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    arm_length = 1000.0  # 调制臂长度 1mm
    arm_gap = 2.0
    length = arm_length + 40.0  # 含输入/输出 MMI
    ports = [
        Port(name="in1", x=0.0, y=arm_gap / 2, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
        Port(name="in2", x=0.0, y=-arm_gap / 2, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
        Port(name="out1", x=length, y=arm_gap / 2, direction=Direction.EAST,
             waveguide_type="strip", width=0.5),
        Port(name="out2", x=length, y=-arm_gap / 2, direction=Direction.EAST,
             waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id="soi_mzm_modulator",
        platform="SOI",
        category="active",
        name="mzm_modulator",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-arm_gap / 2 - 0.25,
                         xmax=length, ymax=arm_gap / 2 + 0.25),
        params={
            "bandwidth_3db_ghz": 20.0,  # 带宽 ~20GHz
            "insertion_loss_db": 5.0,  # 插损 ~5dB
            "vpi_l_v_cm": 2.0,  # VπL ~2V·cm
            "arm_length_um": 1000.0,  # 调制臂长度 1mm
            "modulation_mechanism": "PN junction carrier dispersion",
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 微环调制器 mrm_modulator
# ===========================================================================
def make_mrm_modulator() -> Device:
    """微环调制器（MRM，基于 PN 结载流子色散）。

    垂直 PN 结调制效率 52 pm/V，横向 PN 结 3-dB/6-dB 带宽 74GHz/58GHz。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    radius = 5.0  # 微环半径
    gap = 0.2  # 环-总线耦合间隙
    width = 0.5
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="through", x=2 * radius, y=0.0, direction=Direction.EAST,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_mrm_modulator",
        platform="SOI",
        category="active",
        name="mrm_modulator",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2,
                         xmax=2 * radius, ymax=radius + gap + width + width / 2),
        params={
            "efficiency_pm_v": 52.0,  # 垂直 PN 结效率 52 pm/V
            "bandwidth_3db_ghz": 74.0,  # 横向 PN 结 3-dB 带宽 74GHz
            "bandwidth_6db_ghz": 58.0,  # 6-dB 带宽 58GHz
            "pn_junction": "vertical",  # 垂直 PN 结
            "radius_um": 5.0,
            "wavelength_nm": 1310,  # O 波段
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_bend_radius_um": 2.0,
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )


# ===========================================================================
# Ge 光电探测器 ge_photodetector
# ===========================================================================
def make_ge_photodetector() -> Device:
    """锗光电探测器（Ge photodetector, PD）。

    带宽 ~30GHz，响应率 ~0.7A/W，暗电流 <100nA。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 30.0  # 探测区长度
    width = 0.5
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=width),
    ]
    return Device(
        device_id="soi_ge_photodetector",
        platform="SOI",
        category="detector",
        name="ge_photodetector",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "bandwidth_3db_ghz": 30.0,  # 带宽 ~30GHz
            "responsivity_a_w": 0.7,  # 响应率 ~0.7A/W
            "dark_current_na": 100.0,  # 暗电流 <100nA
            "detector_length_um": 30.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 双环滤波器 double_ring_filter
# ===========================================================================
def make_double_ring_filter() -> Device:
    """双环滤波器（double ring filter, DRF）。

    drop 端口插损 <1.0dB，1-dB 带宽 105GHz，用于波长选择滤波。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    radius = 10.0  # 环半径
    gap = 0.2  # 耦合间隙
    width = 0.5
    ring_spacing = 2 * (radius + gap + width)  # 两环间距
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=width),
        Port(name="through", x=ring_spacing, y=0.0, direction=Direction.EAST,
             waveguide_type="strip", width=width),
        Port(name="drop", x=ring_spacing, y=2 * (radius + gap + width),
             direction=Direction.EAST, waveguide_type="strip", width=width),
        Port(name="add", x=0.0, y=2 * (radius + gap + width),
             direction=Direction.WEST, waveguide_type="strip", width=width),
    ]
    params = {
        "drop_insertion_loss_db": 1.0, "bandwidth_1db_ghz": 105.0,
        "radius_um": 10.0, "gap_nm": 200, "wavelength_nm": 1310,
    }
    return Device(
        device_id="soi_double_ring_filter",
        platform="SOI",
        category="passive",
        name="double_ring_filter",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2,
                         xmax=ring_spacing, ymax=2 * (radius + gap + width) + width / 2),
        params=params,
        source=_SRC_SAMSUNG,
        constraints={
            "min_bend_radius_um": 2.0,
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )
