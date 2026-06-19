"""InP 平台公共来源对象、设计约束与端口辅助函数。

存放 InP（Indium Phosphide）有源集成平台的文献溯源 ``Source`` 对象、
通用设计约束与共享端口创建辅助函数，供各器件子模块共享（避免重复构造；
``Source`` 为 frozen 可安全共享）。

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
"""

from __future__ import annotations

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

# Koren et al., IEEE PTL 2005 — InP SOA
_SOURCE_KOREN_PTL2005 = Source(
    title="InP-based SOA with 20 dB gain and 10 dBm saturation power",
    authors="Koren et al.",
    year=2005,
    url="https://doi.org/10.1109/LPT.2005.857997",
)

# Mason et al., IEEE PTL 2002 — InP EAM
_SOURCE_MASON_PTL2002 = Source(
    title="40 Gb/s photoreceiver with InP EAM integrated on SOI",
    authors="Mason et al.",
    year=2002,
    url="https://doi.org/10.1109/LPT.2002.806825",
)

# ---------------------------------------------------------------------------
# InP 平台通用设计常量与约束
# ---------------------------------------------------------------------------

# InP 平台波导类型常量（有源波导，用于端口宽度匹配）
_WG_TYPE = "inp_active"

# InP 有源波导典型宽度（μm），取 1.5-2.5 范围的代表值
_WG_WIDTH = 2.0

# InP 平台最小弯曲半径（μm），低折射率差平台需较大弯曲半径
_MIN_BEND_RADIUS = 250.0

# InP 平台最小器件间距（μm）
_MIN_SPACING = 2.0

# InP 平台通用设计约束（所有器件共享，弯曲半径与间距）
_INP_CONSTRAINTS: dict[str, float] = {
    "min_spacing_um": _MIN_SPACING,
    "min_bend_radius_um": _MIN_BEND_RADIUS,
}

# 电端口宽度（μm），InP 平台标准 RF/DC 电端口
_ELECTRICAL_WIDTH = 50.0


# ---------------------------------------------------------------------------
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ---------------------------------------------------------------------------
def _make_inout_ports(length: float) -> list[Port]:
    """创建 InP 有源波导标准 in/out 光端口。

    Args:
        length: 器件长度（μm），决定 out 端口 x 坐标。

    Returns:
        含 in（WEST）与 out（EAST）两端口的标准列表。
    """
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type=_WG_TYPE,
            width=_WG_WIDTH,
        ),
        Port(
            name="out",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type=_WG_TYPE,
            width=_WG_WIDTH,
        ),
    ]


def _make_electrical_port(x: float, name: str = "electrical") -> Port:
    """创建 InP 标准电端口（NORTH 朝向，electrical 类型）。

    Args:
        x: 电端口 x 坐标（μm）。
        name: 端口名（默认 "electrical"）。

    Returns:
        位于波导上沿（y=half_w）朝 NORTH 的电端口。
    """
    return Port(
        name=name,
        x=x,
        y=_WG_WIDTH / 2.0,
        direction=Direction.NORTH,
        waveguide_type="electrical",
        width=_ELECTRICAL_WIDTH,
    )
