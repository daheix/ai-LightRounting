"""InP 平台激光器器件库（从 inp.py 拆分）。

覆盖 InP（Indium Phosphide）有源集成平台的激光器真实参数模型：
DFB、DBR、SGDBR 激光器、O-band 高功率 DFB、Coherent BH DFB 与
IMOS DFB 激光器。每个器件参数均来自公开文献并附带 ``Source`` 溯源
（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

来源文献：
- Soares et al., "InP-Based Foundry PICs for Optical Interconnects",
  Appl. Sci. 2019, 9(8), 1588 — https://doi.org/10.3390/app9081588
  （Fraunhofer HHI InP Foundry：DFB/DBR 激光器）
- Zhao et al., "Indium Phosphide Photonic Integrated Circuits for Free Space
  Optical Links", IEEE JSTQE 2018, 24(6), 6101806 —
  https://doi.org/10.1109/JSTQE.2018.2866565
  （UCSB SGDBR 激光器）
- AP Technologies, 高功率 InP 器件（SemiNex DFB/SOA）—
  https://www.aptechnologies.co.uk/news
- Coherent, 400mW InP BH DFB 激光器 —
  http://ep.cntronics.com/guide/4364/14539
- Zozulia et al., "IMOS DFB on InP Membrane", Photonics Benelux 2023 —
  https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf
"""

from __future__ import annotations

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
# 激光器器件工厂函数
# ---------------------------------------------------------------------------

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
        "manufacturer": "Coherent", "structure": "BH (Buried Heterostructure)",
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
