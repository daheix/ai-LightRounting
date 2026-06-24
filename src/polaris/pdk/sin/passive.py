"""SiN 平台被动器件库。

覆盖氮化硅 SiN 平台的被动器件真实参数模型：条形/双条带/Damascene/ULL
波导、光栅耦合器与材料本征参数。每个器件参数均来自公开文献/工艺手册并
附带 ``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md
来源核对）。

设计约束（SiN 平台，参考 spec.md）：
- 最小波导间距 2μm（低折射率差平台需更大间距抑制串扰）
- 最小弯曲半径 50-100μm（SiN 弯曲损耗敏感，半径远大于 SOI 的 2-6μm）
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.sin.sources import (
    _SIN_CONSTRAINTS,
    _SRC_EEFOCUS_SIN_TOC,
    _SRC_IMEC_SIN,
    _SRC_LI_DAMASCENE,
    _SRC_LIONIX_TRIPLEX,
    _SRC_PATSNAP_SIN_LOSS,
    _SRC_SAMSUNG_OFC2026,
    _SRC_SIN_MATERIAL_CN,
    _SRC_TSMC_ISSCC2026,
)


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
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


def _make_sin_grating_coupler_ports() -> list[Port]:
    """构建 SiN 一维光栅耦合器端口（fiber/out）。

    光栅耦合器：光纤端口朝上（NORTH），波导输出朝东（EAST）。

    Returns:
        含 fiber 与 out 两端口的列表。
    """
    return [
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


# ===========================================================================
# 1. SiN 条形波导 LPCVD（IMEC）
# ===========================================================================
def make_sin_waveguide_lpcvd() -> Device:
    """IMEC LPCVD SiN 条形波导。

    损耗 <0.1 dB/cm，最低 2 dB/m（即 0.2 dB/cm），波长覆盖 405-2500nm。
    来源: IMEC Silicon Nitride Photonics。
    """
    length = 100.0
    width = 1.0
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
        source=_SRC_IMEC_SIN,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 2. SiN 条形波导 PECVD（IMEC）
# ===========================================================================
def make_sin_waveguide_pecvd() -> Device:
    """IMEC PECVD SiN 条形波导。

    损耗 <2 dB/cm，低温工艺，适用于 CMOS imager 与平面光学后道集成。
    来源: IMEC Silicon Nitride Photonics。
    """
    length = 100.0
    width = 1.0
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
        source=_SRC_IMEC_SIN,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 3. TriPleX 双条带波导（LioniX）
# ===========================================================================
def make_triplex_double_stripe() -> Device:
    """LioniX TriPleX 双条带（double-stripe）SiN 波导。

    损耗 <0.1 dB/cm，最低 0.1 dB/m，波长 405-2350nm，光纤耦合 <0.5dB/facet。
    来源: LioniX TriPleX Waveguide Technology。
    """
    length = 100.0
    width = 1.2
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
        source=_SRC_LIONIX_TRIPLEX,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 4. SiN Damascene 波导 8 寸（Li et al., Appl. Sci. 2023）
# ===========================================================================
def make_sin_waveguide_damascene() -> Device:
    """Damascene 工艺 LPCVD SiN 波导（8 寸晶圆）。

    400nm 厚，损耗 0.157 dB/cm @1550nm，0.06 dB/cm @1580nm。
    来源: Li et al., Appl. Sci. 2023, 13, 3660。
    """
    length = 100.0
    width = 1.5
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
        source=_SRC_LI_DAMASCENE,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 5. SiN 超低损耗波导 UCSB（PatSnap Eureka）
# ===========================================================================
def make_sin_waveguide_ull() -> Device:
    """UCSB 超低损耗（ULL）SiN 波导。

    损耗 1.2 dB/m @1590nm。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
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
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 6. SiN 超低损耗波导 EPFL（PatSnap Eureka）
# ===========================================================================
def make_sin_waveguide_epfl() -> Device:
    """EPFL Damascene reflow 工艺超低损耗 SiN 波导（晶圆级）。

    损耗 <1 dB/m，微环谐振器 Q>10⁷（晶圆级）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
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
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 7. SiN 沟槽填充波导 Twente（PatSnap Eureka）
# ===========================================================================
def make_sin_waveguide_trench() -> Device:
    """Twente 沟槽填充（trench-fill）SiN 波导。

    损耗 0.4 dB/cm @1550nm，厚核 900nm（消除厚膜开裂）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 2.0
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
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 8. SiN 可见光波导 Myongji（PatSnap Eureka）
# ===========================================================================
def make_sin_waveguide_visible() -> Device:
    """Myongji SiN 可见光波导。

    损耗 0.1 dB/cm（可见光波段）。
    来源: PatSnap Eureka SiN 波导损耗综述。
    """
    length = 100.0
    width = 0.8
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
        source=_SRC_PATSNAP_SIN_LOSS,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 9. SiN 光栅耦合器 1D（三星 300mm 硅光平台）
# ===========================================================================
def make_sin_grating_coupler_1d() -> Device:
    """三星 300mm 平台 SiN 一维光栅耦合器。

    峰值耦合损耗 2.1dB，1-dB 带宽 57nm。
    来源: 三星 300mm 硅光平台 OFC 2026。
    """
    return Device(
        device_id="sin_grating_coupler_1d",
        platform="SiN",
        category="passive",
        name="sin_grating_coupler_1d",
        ports=_make_sin_grating_coupler_ports(),
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=20.0, ymax=20.0),
        params={
            "coupling_loss_db": 2.1,  # 峰值耦合损耗 2.1dB
            "bandwidth_1db_nm": 57,  # 1-dB 带宽 57nm
            "type": "1D",
            "foundry": "Samsung",
        },
        source=_SRC_SAMSUNG_OFC2026,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 10. SiN 材料参数（中国物理学会期刊网）
# ===========================================================================
def make_sin_material() -> Device:
    """SiN（Si3N4）材料本征参数。

    带隙 Eg~5.1eV，折射率 n~2 @1550nm，损耗 0.045±0.04 dB/m，
    热膨胀系数 2.35×10⁻⁶/°C。
    来源: 中国物理学会期刊网 Si3N4 波导材料。
    """
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
        source=_SRC_SIN_MATERIAL_CN,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 11. SiN 热光系数（文献典型值 2.4-2.5×10⁻⁵ /K，台积电 ISSCC 2026 为下界）
# ===========================================================================
def make_sin_thermo_optic() -> Device:
    """SiN 热光系数。

    热光系数 2.4×10⁻⁵ /K（0.24×10⁻⁴ /K，比 Si 低一个数量级），温度敏感度低。
    来源: 文献典型值 2.4-2.5×10⁻⁵ /K（eefocus, ResearchGate），
          台积电 ISSCC 2026 报告 2.0×10⁻⁵ /K 为下界。
    """
    return Device(
        device_id="sin_thermo_optic",
        platform="SiN",
        category="material",
        name="sin_thermo_optic_coefficient",
        ports=[],  # 材料参数无端口
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0),
        params={
            "thermo_optic_coefficient_per_k": 2.4e-5,  # 2.4×10⁻⁵ /K（文献典型值）
            "si_thermo_optic_coefficient_per_k": 1.8e-4,  # Si 1.8×10⁻⁴ /K（对比）
            "comparison": "比 Si 低一个数量级",
        },
        source=_SRC_EEFOCUS_SIN_TOC,
        constraints=_SIN_CONSTRAINTS,
    )


# ===========================================================================
# 12. SiN 波导损耗 台积电（台积电 ISSCC 2026）
# ===========================================================================
def make_sin_waveguide_tsmc() -> Device:
    """台积电 ISSCC 2026 平台 SiN 波导。

    损耗 <0.23 dB/cm。
    来源: 台积电 ISSCC 2026 硅光平台。
    """
    length = 100.0
    width = 1.0
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
        source=_SRC_TSMC_ISSCC2026,
        constraints=_SIN_CONSTRAINTS,
    )
