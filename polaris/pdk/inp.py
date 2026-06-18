"""InP 平台器件库（Task 5）。

覆盖 InP（Indium Phosphide）有源集成平台的主要器件，所有参数来自公开文献
真实数据，每个器件附带 ``Source`` 对象以溯源（见项目规则 1.1，禁止假数据）。

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

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source

# ---------------------------------------------------------------------------
# 可复用的文献来源对象（frozen，可安全共享）
# ---------------------------------------------------------------------------

# Soares et al., Fraunhofer HHI InP Foundry（有源波导/EAM/PD/SOA/DFB/DBR）
_SOURCE_SOARES = Source(
    title="InP-Based Foundry PICs for Optical Interconnects",
    authors="Soares et al. (Fraunhofer HHI)",
    year=2019,
    url="https://doi.org/10.3390/app9081588",
)

# Zhao et al., UCSB InP PIC for FSO（SGDBR 激光器、InP MZM）
_SOURCE_ZHAO = Source(
    title="Indium Phosphide Photonic Integrated Circuits for Free Space Optical Links",
    authors="Zhao et al. (UCSB)",
    year=2018,
    url="https://doi.org/10.1109/JSTQE.2018.2866565",
)

# AP Technologies，SemiNex 高功率 InP 器件（O-band DFB / 超高功率 SOA）
_SOURCE_AP_TECH = Source(
    title="High Power InP Devices (SemiNex DFB/SOA)",
    authors="AP Technologies",
    year=2023,
    url="https://www.aptechnologies.co.uk/news",
    note="产品新闻页，年份为估算",
)

# Coherent，400mW InP BH DFB 激光器（1311nm）
_SOURCE_COHERENT = Source(
    title="Coherent 400mW InP BH DFB Laser (1311nm)",
    authors="Coherent",
    year=2023,
    url="http://ep.cntronics.com/guide/4364/14539",
    note="产品报道，年份为估算",
)

# Zozulia et al., TU Eindhoven，IMOS DFB on InP membrane
_SOURCE_ZOZULIA = Source(
    title="IMOS DFB Laser on InP Membrane",
    authors="Zozulia et al. (TU Eindhoven)",
    year=2023,
    url="https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf",
)

# InP 平台波导类型常量（有源波导，用于端口宽度匹配）
_WG_TYPE = "inp_active"

# InP 有源波导典型宽度（μm），取 1.5-2.5 范围的代表值
_WG_WIDTH = 2.0

# InP 平台最小弯曲半径（μm），低折射率差平台需较大弯曲半径
_MIN_BEND_RADIUS = 250.0

# InP 平台最小器件间距（μm）
_MIN_SPACING = 2.0


# ---------------------------------------------------------------------------
# 器件工厂函数
# ---------------------------------------------------------------------------

def make_inp_waveguide() -> Device:
    """InP 有源波导（宽 1.5-2.5μm，SSC 模场 10×7μm）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文图 1 描述了通用 foundry 工艺的外延层结构与各波导截面，
    SSC（spot-size converter）实现 10μm × 7μm 的大模场以降低光纤耦合损耗。

    Returns:
        InP 有源波导 Device 实例（in→out 双端口）。
    """
    length = 100.0  # 波导长度（μm），代表值
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="inp_waveguide",
        platform="InP",
        category="passive",
        name="inp_waveguide",
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="out", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w),
        params={
            "width_um": _WG_WIDTH,
            "width_range_um": "1.5-2.5",
            "ssc_mode_field_um": "10x7",
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


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
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="out", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="rf", x=length / 2.0, y=half_w, direction=Direction.NORTH,
                 waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "bandwidth_ghz": 45.0,
            "bandwidth_note": "~45 GHz",
            "length_um": length,
            "modulation_type": "EAM",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


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
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "responsivity_a_w": 0.8,
            "responsivity_note": ">0.8 A/W (internal)",
            "bandwidth_ghz": 28.0,
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


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
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="out", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "gain_db_per_100um": 4.0,
            "gain_note": "~4 dB/100μm",
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_dfb_laser() -> Device:
    """DFB 激光器（输出功率 >3mW）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了 DFB 激光器作为集成光源，输出功率 >3mW。

    Returns:
        DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 400.0  # DFB 激光器长度（μm），典型值
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="dfb_laser",
        platform="InP",
        category="source",
        name="dfb_laser",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "output_power_mw": 3.0,
            "output_power_note": ">3 mW",
            "length_um": length,
            "wavelength_nm": 1550.0,
            "laser_type": "DFB",
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_dbr_laser() -> Device:
    """DBR 激光器（输出功率 >3mW）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了 DBR 激光器作为可调谐集成光源，输出功率 >3mW。

    Returns:
        DBR 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 600.0  # DBR 激光器长度（μm），含 Bragg 光栅段，比 DFB 更长
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="dbr_laser",
        platform="InP",
        category="source",
        name="dbr_laser",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "output_power_mw": 3.0,
            "output_power_note": ">3 mW",
            "length_um": length,
            "wavelength_nm": 1550.0,
            "laser_type": "DBR",
        },
        source=_SOURCE_SOARES,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_sgdbr_laser() -> Device:
    """SGDBR 激光器（调谐 1521-1565nm，SMSR >45dB）。

    来源：Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO，
    论文描述了五段 SGDBR 激光器，调谐范围 1521-1565nm（覆盖整个 C 波段），
    边模抑制比 >45dB。

    Returns:
        SGDBR 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 1000.0  # SGDBR 五段激光器长度（μm），含多个光栅段
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="sgdbr_laser",
        platform="InP",
        category="source",
        name="sgdbr_laser",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "tuning_range_nm": "1521-1565",
            "smsr_db": 45.0,
            "smsr_note": ">45 dB",
            "length_um": length,
            "laser_type": "SGDBR",
            "sections": 5,
        },
        source=_SOURCE_ZHAO,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_inp_mzm() -> Device:
    """InP MZM 马赫-曾德调制器（1mm 长，集成于 PIC）。

    来源：Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO，
    论文图 1 描述了集成于 InP PIC 的 1mm 长 MZM，用于相位/强度调制。

    Returns:
        InP MZM Device 实例（in→out 光端口 + rf1/rf2 双臂电端口）。
    """
    length = 1000.0  # MZM 长度（μm），论文明确为 1mm
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="inp_mzm",
        platform="InP",
        category="active",
        name="inp_mzm",
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="out", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="rf1", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
            Port(name="rf2", x=length / 2.0, y=-half_w,
                 direction=Direction.SOUTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w - 50.0, xmax=length,
                         ymax=half_w + 50.0),
        params={
            "length_mm": 1.0,
            "length_um": length,
            "modulation_type": "MZM",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_ZHAO,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_dfb_laser_oband() -> Device:
    """O-band DFB 激光器 SemiNex（200-250mW CW @25°C）。

    来源：AP Technologies — SemiNex 高功率 O-band DFB 激光器，
    连续输出功率 200-250mW @25°C。

    Returns:
        O-band DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 1500.0  # 高功率 DFB 激光器长度（μm），高功率器件通常更长
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="dfb_laser_oband",
        platform="InP",
        category="source",
        name="dfb_laser_oband",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "output_power_mw": "200-250",
            "output_power_note": "200-250 mW CW @25°C",
            "wavelength_band": "O-band",
            "wavelength_nm": 1310.0,
            "operating_temp_c": 25,
            "manufacturer": "SemiNex",
            "length_um": length,
        },
        source=_SOURCE_AP_TECH,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


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
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="out", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
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
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_dfb_laser_coherent() -> Device:
    """InP BH DFB 激光器 Coherent（1311nm，400mW@55°C，线宽 <200kHz）。

    来源：Coherent 产品报道 — InP BH（Buried Heterostructure）DFB 激光器，
    波长 1311nm，输出功率 400mW@55°C，线宽 <200kHz，
    RIN（相对强度噪声）<-145 dB/Hz。

    Returns:
        Coherent BH DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 750.0  # BH DFB 激光器长度（μm），典型值
    half_w = _WG_WIDTH / 2.0
    params = {
        "wavelength_nm": 1311.0, "output_power_mw": 400.0,
        "output_power_note": "400 mW @55°C", "operating_temp_c": 55,
        "linewidth_khz": 200.0, "linewidth_note": "<200 kHz",
        "rin_db_hz": -145.0, "rin_note": "<-145 dB/Hz",
        "manufacturer": "Coherent",
        "structure": "BH (Buried Heterostructure)",
        "length_um": length,
    }
    return Device(
        device_id="dfb_laser_coherent",
        platform="InP",
        category="source",
        name="dfb_laser_coherent",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params=params,
        source=_SOURCE_COHERENT,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


def make_imos_dfb_laser() -> Device:
    """IMOS DFB 激光器（250μm 长，600μW 光纤功率，带宽 15GHz，25Gbit/s）。

    来源：Zozulia et al., Photonics Benelux 2023 — TU Eindhoven，
    IMOS（InP Membrane on Silicon）平台上的 DFB 激光器，
    腔长 250μm，光纤耦合功率 600μW，调制带宽 15GHz，支持 25Gbit/s 传输。

    Returns:
        IMOS DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 250.0  # IMOS DFB 激光器长度（μm），论文明确为 250μm
    half_w = _WG_WIDTH / 2.0
    return Device(
        device_id="imos_dfb_laser",
        platform="InP",
        category="source",
        name="imos_dfb_laser",
        ports=[
            Port(name="output", x=length, y=0.0, direction=Direction.EAST,
                 waveguide_type=_WG_TYPE, width=_WG_WIDTH),
            Port(name="electrical", x=length / 2.0, y=half_w,
                 direction=Direction.NORTH, waveguide_type="electrical", width=50.0),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0),
        params={
            "length_um": length,
            "fiber_power_uw": 600.0,
            "fiber_power_note": "600 μW fiber-coupled",
            "bandwidth_ghz": 15.0,
            "data_rate_gbps": 25.0,
            "platform": "IMOS (InP Membrane on Silicon)",
            "manufacturer": "TU Eindhoven",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_ZOZULIA,
        constraints={
            "min_spacing_um": _MIN_SPACING,
            "min_bend_radius_um": _MIN_BEND_RADIUS,
        },
    )


# ---------------------------------------------------------------------------
# InP 器件汇总字典（器件名 → 工厂函数）
# ---------------------------------------------------------------------------

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
}
