"""SOI 平台主动器件库。

覆盖硅光 SOI 平台的主动器件真实参数模型：热光移相器、MZM 调制器、
MRM 调制器与 Ge 光电探测器。每个器件参数均来自公开文献/工艺手册并附带
``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.soi.sources import _SRC_ICCSZ, _SRC_SAMSUNG


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_mzm_ports(arm_gap: float, length: float) -> list[Port]:
    """创建 MZM 调制器的 4 个端口（双臂，in1/in2 朝 WEST，out1/out2 朝 EAST）。"""
    return [
        Port(
            name="in1",
            x=0.0,
            y=arm_gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="in2",
            x=0.0,
            y=-arm_gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="out1",
            x=length,
            y=arm_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="out2",
            x=length,
            y=-arm_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
    ]


def _make_mrm_ports(radius: float, width: float) -> list[Port]:
    """创建 MRM 调制器的 2 个端口（全通结构，in 朝 WEST，through 朝 EAST）。"""
    return [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="through",
            x=2 * radius,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
    ]


# ===========================================================================
# 1. 热光移相器 thermo_optic_phase_shifter
# ===========================================================================
def make_thermo_optic_phase_shifter() -> Device:
    """热光移相器（thermo-optic phase shifter, TOPS）。

    Pπ ~20mW，基于 Si 热光系数（1.8×10⁻⁴ /K）实现相位调谐。
    来源：硅光工艺平台比较（iccsz.com）；热光系数来源台积电 ISSCC 2026。
    """
    length = 100.0  # 加热器长度
    width = 0.5
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="rib", width=width),
        Port(
            name="out", x=length, y=0.0, direction=Direction.EAST, waveguide_type="rib", width=width
        ),
    ]
    return Device(
        device_id="soi_thermo_optic_phase_shifter",
        platform="SOI",
        category="active",
        name="thermo_optic_phase_shifter",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "ppi_mw": 20.0,  # Pπ ~20mW（π 相移功耗）
            "insertion_loss_db": 0.1,
            "heater_length_um": 100.0,
            "thermo_optic_coeff_per_k": 1.8e-4,  # Si 热光系数 1.8×10⁻⁴ /K
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 2. MZ 调制器 mzm_modulator
# ===========================================================================
def make_mzm_modulator() -> Device:
    """马赫-曾德尔调制器（MZM，基于 PN 结载流子色散）。

    带宽 ~20GHz，插损 ~5dB，VπL ~2V·cm。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    arm_length = 1000.0  # 调制臂长度 1mm
    arm_gap = 2.0
    length = arm_length + 40.0  # 含输入/输出 MMI
    ports = _make_mzm_ports(arm_gap, length)
    return Device(
        device_id="soi_mzm_modulator",
        platform="SOI",
        category="active",
        name="mzm_modulator",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-arm_gap / 2 - 0.25, xmax=length, ymax=arm_gap / 2 + 0.25),
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
# 3. 微环调制器 mrm_modulator
# ===========================================================================
def make_mrm_modulator() -> Device:
    """微环调制器（MRM，基于 PN 结载流子色散）。

    垂直 PN 结调制效率 52 pm/V，横向 PN 结 3-dB/6-dB 带宽 74GHz/58GHz。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    radius = 5.0  # 微环半径
    gap = 0.2  # 环-总线耦合间隙
    width = 0.5
    ports = _make_mrm_ports(radius, width)
    return Device(
        device_id="soi_mrm_modulator",
        platform="SOI",
        category="active",
        name="mrm_modulator",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-width / 2, xmax=2 * radius, ymax=radius + gap + width + width / 2
        ),
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
# 4. Ge 光电探测器 ge_photodetector
# ===========================================================================
def make_ge_photodetector() -> Device:
    """锗光电探测器（Ge photodetector, PD）。

    带宽 ~30GHz，响应率 ~0.7A/W，暗电流 <100nA。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 30.0  # 探测区长度
    width = 0.5
    ports = [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
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
