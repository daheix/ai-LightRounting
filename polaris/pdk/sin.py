"""氮化硅 SiN 平台器件库（Task 4）。

提供 SiN 平台被动器件的 ``Device`` 工厂函数，每个器件的电光参数均来自
公开文献/工艺手册并附 ``Source`` 溯源对象（含 URL），禁止假数据。

参数来源（已逐项核对网址可达性与数值区间）：
- IMEC Silicon Nitride Photonics —
  https://www.imec-int.com/en/what-we-offer/development/silicon-nitride
- LioniX TriPleX SiN 波导技术 —
  https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
- Li et al., Appl. Sci. 2023, 13, 3660（Damascene SiN 8 寸） —
  https://doi.org/10.3390/app13063660
- PatSnap Eureka: SiN 波导损耗综述（UCSB/EPFL/Twente/Cornell） —
  https://www.patsnap.com/resources/blog/rd-blog/si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/
- 中国物理学会期刊网：Si3N4 波导材料 —
  https://c.m.163.com/news/a/E9107H030516DOTJ.html
- 台积电 ISSCC 2026 硅光平台 —
  https://cloud.tencent.com.cn/developer/article/2634252
- 三星 300mm 硅光平台 OFC 2026 —
  https://cloud.tencent.com/developer/article/2650050

设计约束（SiN 平台，参考 spec.md）：
- 最小波导间距 2μm（低折射率差平台需更大间距抑制串扰）
- 最小弯曲半径 50-100μm（SiN 弯曲损耗敏感，半径远大于 SOI 的 2-6μm）
"""

from __future__ import annotations

from collections.abc import Callable

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source

# SiN 平台通用设计约束（最小间距 2μm，最小弯曲半径 50μm）
_SIN_CONSTRAINTS: dict = {
    "min_spacing_um": 2.0,
    "min_bend_radius_um": 50.0,
}


def _straight_waveguide_ports(length: float, width: float, waveguide_type: str) -> list[Port]:
    """构造直波导两端端口（in 朝 WEST，out 朝 EAST）。

    Args:
        length: 波导长度（μm）。
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
            name="out",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type=waveguide_type,
            width=width,
        ),
    ]


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


# ---------------------------------------------------------------------------
# 1. SiN 条形波导 LPCVD（IMEC）
# ---------------------------------------------------------------------------
def make_sin_waveguide_lpcvd() -> Device:
    """IMEC LPCVD SiN 条形波导。

    损耗 <0.1 dB/cm，最低 2 dB/m（即 0.2 dB/cm），波长覆盖 405-2500nm。
    来源: IMEC Silicon Nitride Photonics。
    """
    length = 100.0
    width = 1.0
    src = Source(
        title="Silicon nitride-based photonics",
        authors="IMEC",
        year=2024,
        url="https://www.imec-int.com/en/what-we-offer/development/silicon-nitride",
    )
    return Device(
        device_id="sin_waveguide_lpcvd",
        platform="SiN",
        category="passive",
        name="sin_waveguide_strip",
        ports=_straight_waveguide_ports(length, width, "sin_strip_lpcvd"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 0.1,  # 典型值 <0.1 dB/cm
            "loss_min_db_m": 2.0,  # 最低 2 dB/m（0.2 dB/cm）
            "wavelength_range_nm": "405-2500",
            "deposition": "LPCVD",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 2. SiN 条形波导 PECVD（IMEC）
# ---------------------------------------------------------------------------
def make_sin_waveguide_pecvd() -> Device:
    """IMEC PECVD SiN 条形波导。

    损耗 <2 dB/cm，低温工艺，适用于 CMOS imager 与平面光学后道集成。
    来源: IMEC Silicon Nitride Photonics。
    """
    length = 100.0
    width = 1.0
    src = Source(
        title="Silicon nitride-based photonics",
        authors="IMEC",
        year=2024,
        url="https://www.imec-int.com/en/what-we-offer/development/silicon-nitride",
    )
    return Device(
        device_id="sin_waveguide_pecvd",
        platform="SiN",
        category="passive",
        name="sin_waveguide_strip",
        ports=_straight_waveguide_ports(length, width, "sin_strip_pecvd"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 2.0,  # <2 dB/cm
            "wavelength_range_nm": "405-2500",
            "deposition": "PECVD",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 3. TriPleX 双条带波导（LioniX）
# ---------------------------------------------------------------------------
def make_triplex_double_stripe() -> Device:
    """LioniX TriPleX 双条带（double-stripe）SiN 波导。

    损耗 <0.1 dB/cm，最低 0.1 dB/m，波长 405-2350nm，光纤耦合 <0.5dB/facet。
    来源: LioniX TriPleX Waveguide Technology。
    """
    length = 100.0
    width = 1.2
    src = Source(
        title="TriPleX Waveguide Technology",
        authors="LioniX International",
        year=2024,
        url="https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/",
    )
    return Device(
        device_id="triplex_double_stripe",
        platform="SiN",
        category="passive",
        name="sin_waveguide_double_stripe",
        ports=_straight_waveguide_ports(length, width, "triplex_double_stripe"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 0.1,  # <0.1 dB/cm
            "loss_min_db_m": 0.1,  # 最低 0.1 dB/m
            "wavelength_range_nm": "405-2350",
            "fiber_coupling_loss_db": 0.5,  # <0.5 dB/facet
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 4. SiN Damascene 波导 8 寸（Li et al., Appl. Sci. 2023）
# ---------------------------------------------------------------------------
def make_sin_waveguide_damascene() -> Device:
    """Damascene 工艺 LPCVD SiN 波导（8 寸晶圆）。

    400nm 厚，损耗 0.157 dB/cm @1550nm，0.06 dB/cm @1580nm。
    来源: Li et al., Appl. Sci. 2023, 13, 3660。
    """
    length = 100.0
    width = 1.5
    src = Source(
        title="Process Development of Low-Loss LPCVD Silicon Nitride Waveguides on 8-Inch Wafer",
        authors="Li, Z.; Fan, Z.; Zhou, J.; Cong, Q.; Zeng, X.; Zhang, Y.; Jia, L.",
        year=2023,
        url="https://doi.org/10.3390/app13063660",
    )
    return Device(
        device_id="sin_waveguide_damascene",
        platform="SiN",
        category="passive",
        name="sin_waveguide_damascene",
        ports=_straight_waveguide_ports(length, width, "sin_damascene"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm_1550nm": 0.157,  # 0.157 dB/cm @1550nm
            "loss_db_cm_1580nm": 0.06,  # 0.06 dB/cm @1580nm
            "core_thickness_nm": 400,  # 400nm 厚
            "wafer_size_inch": 8,
            "deposition": "LPCVD",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 5. SiN 超低损耗波导 UCSB（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_waveguide_ull() -> Device:
    """UCSB 超低损耗（ULL）SiN 波导。

    损耗 1.2 dB/m @1590nm。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
    return Device(
        device_id="sin_waveguide_ull",
        platform="SiN",
        category="passive",
        name="sin_waveguide_ull",
        ports=_straight_waveguide_ports(length, width, "sin_ull"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_m": 1.2,  # 1.2 dB/m @1590nm
            "wavelength_nm": 1590,
            "institution": "UCSB",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 6. SiN 超低损耗波导 EPFL（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_waveguide_epfl() -> Device:
    """EPFL Damascene reflow 工艺超低损耗 SiN 波导（晶圆级）。

    损耗 <1 dB/m，微环谐振器 Q>10⁷（晶圆级）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
    return Device(
        device_id="sin_waveguide_epfl",
        platform="SiN",
        category="passive",
        name="sin_waveguide_epfl",
        ports=_straight_waveguide_ports(length, width, "sin_epfl"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_m": 1.0,  # <1 dB/m
            "ring_q_factor": 1.0e7,  # Q>10⁷（晶圆级）
            "process": "Damascene reflow + CMP",
            "institution": "EPFL",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 7. SiN 沟槽填充波导 Twente（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_waveguide_trench() -> Device:
    """Twente 沟槽填充（trench-fill）SiN 波导。

    损耗 0.4 dB/cm @1550nm，厚核 900nm（消除厚膜开裂）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
    return Device(
        device_id="sin_waveguide_trench",
        platform="SiN",
        category="passive",
        name="sin_waveguide_trench",
        ports=_straight_waveguide_ports(length, width, "sin_trench"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 0.4,  # 0.4 dB/cm @1550nm
            "wavelength_nm": 1550,
            "core_thickness_nm": 900,  # 厚核 900nm
            "process": "trench-fill",
            "institution": "Twente",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 8. SiN 双条带环 Twente（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_ring_double_stripe() -> Device:
    """Twente 双条带（double-stripe）SiN 环谐振器。

    损耗 0.095 dB/cm。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    radius = 50.0
    width = 1.2
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
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
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 9. SiN 可见光波导 Myongji（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_waveguide_visible() -> Device:
    """Myongji SiN 可见光波导。

    损耗 0.1 dB/cm（可见光波段）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 0.8
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
    return Device(
        device_id="sin_waveguide_visible",
        platform="SiN",
        category="passive",
        name="sin_waveguide_visible",
        ports=_straight_waveguide_ports(length, width, "sin_visible"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 0.1,  # 0.1 dB/cm
            "band": "visible",
            "institution": "Myongji",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 10. SiN 微环高 Q Cornell（PatSnap Eureka）
# ---------------------------------------------------------------------------
def make_sin_ring_high_q() -> Device:
    """Cornell 高 Q SiN 微环谐振器。

    Q 37M（2.5μm 宽）/ 67M（10μm 宽），高约束 SiN 平台最高 Q 值之一。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    radius = 100.0
    width = 2.5  # 2.5μm 宽对应 Q=37M
    src = Source(
        title="Reducing Waveguide Propagation Loss in SiN Photonic Integrated "
        "Circuits for Optical Gyroscopes",
        authors="PatSnap Eureka",
        year=2026,
        url="https://www.patsnap.com/resources/blog/rd-blog/"
        "si%E2%82%83n%E2%82%84-waveguide-loss-reduction-patsnap-eureka/",
    )
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
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 11. SiN 光栅耦合器 1D（三星 300mm 硅光平台）
# ---------------------------------------------------------------------------
def make_sin_grating_coupler_1d() -> Device:
    """三星 300mm 平台 SiN 一维光栅耦合器。

    峰值耦合损耗 2.1dB，1-dB 带宽 57nm。
    来源: 三星 300mm 硅光平台 OFC 2026。
    """
    src = Source(
        title="Samsung 300mm Silicon Photonics Platform (OFC 2026)",
        authors="Samsung",
        year=2026,
        url="https://cloud.tencent.com/developer/article/2650050",
    )
    # 光栅耦合器：光纤端口朝上（NORTH），波导输出朝东（EAST）
    ports = [
        Port(
            name="fiber",
            x=10.0,
            y=10.0,
            direction=Direction.NORTH,
            waveguide_type="fiber",
            width=10.0,
        ),
        Port(
            name="out",
            x=20.0,
            y=10.0,
            direction=Direction.EAST,
            waveguide_type="sin_strip",
            width=1.0,
        ),
    ]
    return Device(
        device_id="sin_grating_coupler_1d",
        platform="SiN",
        category="passive",
        name="sin_grating_coupler_1d",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=20.0, ymax=20.0),
        params={
            "coupling_loss_db": 2.1,  # 峰值耦合损耗 2.1dB
            "bandwidth_1db_nm": 57,  # 1-dB 带宽 57nm
            "type": "1D",
            "foundry": "Samsung",
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 12. SiN 材料参数（中国物理学会期刊网）
# ---------------------------------------------------------------------------
def make_sin_material() -> Device:
    """SiN（Si3N4）材料本征参数。

    带隙 Eg~5.1eV，折射率 n~2 @1550nm，损耗 0.045±0.04 dB/m，
    热膨胀系数 2.35×10⁻⁶/°C。
    来源: 中国物理学会期刊网 Si3N4 波导材料。
    """
    src = Source(
        title="Si3N4 波导材料参数",
        authors="中国物理学会期刊网",
        year=2024,
        url="https://c.m.163.com/news/a/E9107H030516DOTJ.html",
    )
    return Device(
        device_id="sin_material",
        platform="SiN",
        category="material",
        name="sin_material",
        ports=[],  # 材料本征参数无端口
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0),
        params={
            "bandgap_ev": 5.1,  # Eg~5.1eV
            "refractive_index_1550nm": 2.0,  # n~2 @1550nm
            "loss_db_m": 0.045,  # 0.045±0.04 dB/m
            "loss_db_m_uncertainty": 0.04,
            "thermal_expansion_per_k": 2.35e-6,  # 2.35×10⁻⁶/°C
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 13. SiN 热光系数（台积电 ISSCC 2026）
# ---------------------------------------------------------------------------
def make_sin_thermo_optic() -> Device:
    """SiN 热光系数。

    热光系数 0.2×10⁻⁴ /K（比 Si 低一个数量级），温度敏感度低。
    来源: 台积电 ISSCC 2026 硅光平台。
    """
    src = Source(
        title="TSMC ISSCC 2026 Silicon Photonics Platform",
        authors="TSMC",
        year=2026,
        url="https://cloud.tencent.com.cn/developer/article/2634252",
    )
    return Device(
        device_id="sin_thermo_optic",
        platform="SiN",
        category="material",
        name="sin_thermo_optic_coefficient",
        ports=[],  # 材料参数无端口
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0),
        params={
            "thermo_optic_coefficient_per_k": 2.0e-5,  # 0.2×10⁻⁴ /K
            "si_thermo_optic_coefficient_per_k": 1.8e-4,  # Si 1.8×10⁻⁴ /K（对比）
            "comparison": "比 Si 低一个数量级",
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# 14. SiN 波导损耗 台积电（台积电 ISSCC 2026）
# ---------------------------------------------------------------------------
def make_sin_waveguide_tsmc() -> Device:
    """台积电 ISSCC 2026 平台 SiN 波导。

    损耗 <0.23 dB/cm。
    来源: 台积电 ISSCC 2026 硅光平台。
    """
    length = 100.0
    width = 1.0
    src = Source(
        title="TSMC ISSCC 2026 Silicon Photonics Platform",
        authors="TSMC",
        year=2026,
        url="https://cloud.tencent.com.cn/developer/article/2634252",
    )
    return Device(
        device_id="sin_waveguide_tsmc",
        platform="SiN",
        category="passive",
        name="sin_waveguide_tsmc",
        ports=_straight_waveguide_ports(length, width, "sin_tsmc"),
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "loss_db_cm": 0.23,  # <0.23 dB/cm
            "foundry": "TSMC",
            "core_width_um": width,
            "length_um": length,
        },
        source=src,
        constraints=_SIN_CONSTRAINTS,
    )


# ---------------------------------------------------------------------------
# SiN 平台器件汇总注册表
# ---------------------------------------------------------------------------
SIN_DEVICES: dict[str, Callable[[], Device]] = {
    "sin_waveguide_lpcvd": make_sin_waveguide_lpcvd,
    "sin_waveguide_pecvd": make_sin_waveguide_pecvd,
    "triplex_double_stripe": make_triplex_double_stripe,
    "sin_waveguide_damascene": make_sin_waveguide_damascene,
    "sin_waveguide_ull": make_sin_waveguide_ull,
    "sin_waveguide_epfl": make_sin_waveguide_epfl,
    "sin_waveguide_trench": make_sin_waveguide_trench,
    "sin_ring_double_stripe": make_sin_ring_double_stripe,
    "sin_waveguide_visible": make_sin_waveguide_visible,
    "sin_ring_high_q": make_sin_ring_high_q,
    "sin_grating_coupler_1d": make_sin_grating_coupler_1d,
    "sin_material": make_sin_material,
    "sin_thermo_optic": make_sin_thermo_optic,
    "sin_waveguide_tsmc": make_sin_waveguide_tsmc,
}
