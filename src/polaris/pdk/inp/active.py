"""InP 平台主动器件库。

覆盖 InP（Indium Phosphide）有源集成平台的主动器件真实参数模型：
EAM 电吸收调制器、InP 光电探测器、SOA 半导体光放大器与超高功率 SOA。
每个器件参数均来自公开文献并附带 ``Source`` 溯源（含 URL），禁止假数据
（见项目规则 1.1 与 spec.md 来源核对）。

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。

来源文献：
- Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry
  https://doi.org/10.3390/app9081588
- AP Technologies — SemiNex 高功率 InP 器件
  https://www.aptechnologies.co.uk/news
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.inp.sources import (
    _INP_CONSTRAINTS,
    _SOURCE_AP_TECH,
    _SOURCE_KOREN_PTL2005,
    _SOURCE_MASON_PTL2002,
    _SOURCE_SOARES,
    _WG_WIDTH,
    _make_electrical_port,
    _make_inout_ports,
)
from polaris.pdk.port import Direction, Port


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_eam_modulator_ports(length: float) -> list[Port]:
    """创建 EAM 调制器的 3 个端口（in/out 光端口 + rf 电端口）。

    Args:
        length: EAM 长度（μm），决定 out 端口 x 坐标与 rf 中点。

    Returns:
        含 in、out、rf 三端口的列表。
    """
    return [
        *_make_inout_ports(length),
        _make_electrical_port(length / 2.0, name="rf"),
    ]


def _make_inp_photodetector_ports(length: float) -> list[Port]:
    """创建 InP 光电探测器的 2 个端口（in 光端口 + electrical 电端口）。

    Args:
        length: 探测器长度（μm），决定 electrical 端口 x 坐标。

    Returns:
        含 in、electrical 两端口的列表。
    """
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type="inp_active",
            width=_WG_WIDTH,
        ),
        _make_electrical_port(length / 2.0),
    ]


def _make_soa_ports(length: float) -> list[Port]:
    """创建 SOA 的 3 个端口（in/out 光端口 + electrical 电端口）。

    SOA 与超高功率 SOA 端口结构相同，共享此辅助函数。

    Args:
        length: SOA 长度（μm），决定 out 端口 x 坐标与 electrical 中点。

    Returns:
        含 in、out、electrical 三端口的列表。
    """
    return [
        *_make_inout_ports(length),
        _make_electrical_port(length / 2.0),
    ]


# ===========================================================================
# 1. EAM 电吸收调制器 eam_modulator
# ===========================================================================
def make_eam_modulator() -> Device:
    """EAM 电吸收调制器（带宽 ~45GHz）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了集成 EAM 的 20 Gb/s 双偏振 EML，EAM 带宽约 45GHz。

    Returns:
        EAM 调制器 Device 实例（in→out 光端口 + rf 电端口）。
    """
    length = 150.0  # EAM 长度（μm），典型 100-250μm
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="eam_modulator",
        platform="InP",
        category="active",
        name="eam_modulator",
        ports=_make_eam_modulator_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "bandwidth_ghz": 45.0,
            "bandwidth_note": "~45 GHz",
            "length_um": length,
            "modulation_type": "EAM",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 2. InP 光电探测器 inp_photodetector
# ===========================================================================
def make_inp_photodetector() -> Device:
    """InP 光电探测器（内部响应率 >0.8 A/W）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了由雪崩光电二极管组成的平衡探测器，内部响应率 >0.8 A/W。

    Returns:
        InP 光电探测器 Device 实例（in 光端口 + electrical 电端口）。
    """
    length = 40.0  # 探测器长度（μm），典型值
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="inp_photodetector",
        platform="InP",
        category="detector",
        name="inp_photodetector",
        ports=_make_inp_photodetector_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "responsivity_a_w": 0.8,
            "responsivity_note": ">0.8 A/W (internal)",
            "bandwidth_ghz": 28.0,
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 3. SOA 半导体光放大器 soa
# ===========================================================================
def make_soa() -> Device:
    """SOA 半导体光放大器（增益 ~4dB/100μm）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了 SOA 作为增益模块，增益约 4dB/100μm。

    Returns:
        SOA 放大器 Device 实例（in→out 光端口 + electrical 电端口）。
    """
    length = 500.0  # SOA 长度（μm），典型值
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="soa",
        platform="InP",
        category="active",
        name="soa",
        ports=_make_soa_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "gain_db_per_100um": 4.0,
            "gain_note": "~4 dB/100μm",
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 4. 超高功率 SOA soa_high_power
# ===========================================================================
def make_soa_high_power() -> Device:
    """超高功率 SOA（>1W 输出，PCE ~25%@25°C）。

    来源：AP Technologies — SemiNex 超高功率 SOA，
    输出功率 >1W，功率转换效率（PCE）约 25%@25°C。

    Returns:
        超高功率 SOA Device 实例（in→out 光端口 + electrical 电端口）。
    """
    length = 2000.0  # 超高功率 SOA 长度（μm），大功率器件需要更长增益区
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="soa_high_power",
        platform="InP",
        category="active",
        name="soa_high_power",
        ports=_make_soa_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "output_power_w": 1.0,
            "output_power_note": ">1 W",
            "pce_percent": 25.0,
            "pce_note": "~25% @25°C",
            "operating_temp_c": 25,
            "manufacturer": "SemiNex",
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_AP_TECH,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 5. InP SOA（半导体光放大器，文献参数） inp_soa_koren
# ===========================================================================
def make_inp_soa_koren() -> Device:
    """InP SOA 半导体光放大器（增益 ≈ 20 dB，饱和功率 ≈ 10 dBm）。

    来源: Koren et al., IEEE PTL 2005，
    论文描述了 InP 基 SOA，增益约 20 dB，饱和输出功率约 10 dBm。
    """
    length = 500.0  # SOA 长度（μm），典型值
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="inp_soa_koren",
        platform="InP",
        category="active",
        name="inp_soa_koren",
        ports=_make_soa_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "gain_db": 20.0,  # 增益 ≈ 20 dB
            "saturation_power_dbm": 10.0,  # 饱和功率 ≈ 10 dBm
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_KOREN_PTL2005,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 6. InP EAM（电吸收调制器，文献参数） inp_eam_mason
# ===========================================================================
def make_inp_eam_mason() -> Device:
    """InP EAM 电吸收调制器（带宽 > 50 GHz，消光比 > 10 dB）。

    来源: Mason et al., IEEE PTL 2002，
    论文描述了集成 InP EAM 的高速光接收机，EAM 带宽 > 50 GHz。
    """
    length = 150.0  # EAM 长度（μm），典型 100-250μm
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="inp_eam_mason",
        platform="InP",
        category="active",
        name="inp_eam_mason",
        ports=_make_eam_modulator_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "bandwidth_ghz": 50.0,  # 带宽 > 50 GHz
            "extinction_ratio_db": 10.0,  # 消光比 > 10 dB
            "length_um": length,
            "modulation_type": "EAM",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_MASON_PTL2002,
        constraints=_INP_CONSTRAINTS,
    )
