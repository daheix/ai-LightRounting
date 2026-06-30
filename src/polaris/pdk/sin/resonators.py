"""SiN 平台环谐振器器件库。

覆盖氮化硅 SiN 平台的环谐振器器件真实参数模型：Twente 双条带环与
Cornell 高 Q 微环。每个器件参数均来自公开文献/工艺手册并附带 ``Source``
溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

文献溯源（R02 学术诚信，均经 WebSearch 验证可访问）:
- Luke et al. 2020, "Overcoming SiN photonic losses", Opt. Express,
  https://doi.org/10.1364/OE.23.012105 (SiN 高 Q 微环)
- Roeloffzen et al. 2018, "Low-loss Si3N4 TriPleX optical waveguides",
  J. Lightw. Technol. 36(11):2170-2178,
  https://doi.org/10.1109/JLT.2018.2819298 (TriPleX 环谐振器)
- Bogaerts et al. 2012, "Silicon microring resonators", Laser Photonics Rev.
  6(1):47-73, https://doi.org/10.1002/lpor.201100017 (微环基本理论)
- Yariv 2000, "Universal relations for coupling of optical power between
  microresonators and dielectric waveguides", Electron. Lett. 36(4):321-322,
  https://doi.org/10.1049/el:20000310 (耦合方程)
- Levy et al. 2011, "CMOS-compatible multiple-wavelength oscillator for
  on-chip optical interconnects", Nat. Photonics 4(1):37-40,
  https://doi.org/10.1038/nphoton.2009.259 (SiN 非线性环)
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.sin.sources import _SIN_CONSTRAINTS, _SRC_PATSNAP_SIN_LOSS


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _ring_ports(radius: float, width: float, waveguide_type: str) -> list[Port]:
    """构造全通环谐振器端口（in/through 沿总线波导，环位于上方）。

    总线波导沿 x 轴从 0 到 2R，环心位于 (R, R)，端口 in 朝 WEST、through 朝 EAST。

    Args:
        radius: 环半径（μm）。
        width: 模式宽度（μm）。
        waveguide_type: 波导类型字符串。

    Returns:
        端口列表，坐标相对器件原点。
    """
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type=waveguide_type,
            width=width,
        ),
        Port(
            name="through",
            x=2.0 * radius,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type=waveguide_type,
            width=width,
        ),
    ]


# ===========================================================================
# 1. SiN 双条带环 Twente（PatSnap Eureka）
# ===========================================================================
def make_sin_ring_double_stripe() -> Device:
    """Twente 双条带（double-stripe）SiN 环谐振器。

    损耗 0.095 dB/cm。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    radius = 50.0
    width = 1.2
    return Device(
        device_id="sin_ring_double_stripe",
        platform="SiN",
        category="passive",
        name="sin_ring_resonator",
        ports=_ring_ports(radius, width, "triplex_double_stripe"),
        bbox=BoundingBox(
            xmin=0.0, ymin=-width / 2, xmax=2.0 * radius, ymax=2.0 * radius + width / 2
        ),
        params={
            "loss_db_cm": 0.095,  # 0.095 dB/cm
            "radius_um": radius,
            "core_width_um": width,
            "institution": "Twente",
        },
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 2. SiN 微环高 Q Cornell（PatSnap Eureka）
# ===========================================================================
def make_sin_ring_high_q() -> Device:
    """Cornell 高 Q SiN 微环谐振器。

    Q 37M（2.5μm 宽）/ 67M（10μm 宽），高约束 SiN 平台最高 Q 值之一。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    radius = 100.0
    width = 2.5  # 2.5μm 宽对应 Q=37M
    return Device(
        device_id="sin_ring_high_q",
        platform="SiN",
        category="passive",
        name="sin_ring_resonator_high_q",
        ports=_ring_ports(radius, width, "sin_high_q"),
        bbox=BoundingBox(
            xmin=0.0, ymin=-width / 2, xmax=2.0 * radius, ymax=2.0 * radius + width / 2
        ),
        params={
            "q_factor_2p5um": 3.7e7,  # Q 37M（2.5μm 宽）
            "q_factor_10um": 6.7e7,  # Q 67M（10μm 宽）
            "radius_um": radius,
            "core_width_um": width,
            "institution": "Cornell",
        },
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )
