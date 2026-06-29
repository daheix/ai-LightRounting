"""SOI 平台主动器件库。

覆盖硅光 SOI 平台的主动器件真实参数模型：热光移相器、MZM 调制器、
MRM 调制器与 Ge 光电探测器。每个器件参数均来自公开文献/工艺手册并附带
``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.soi.sources import (
    _SRC_ASSEFA_NATURE2010,
    _SRC_DENSMORE_OE2011,
    _SRC_ICCSZ,
    _SRC_REED_NP2010,
    _SRC_SAMSUNG,
    _SRC_TIMURDOGAN_JSTQE2014,
)


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

    Pπ ~20mW，基于 Si 热光系数（1.86×10⁻⁴ /K）实现相位调谐。

    R05 Bug 修复 v4.0-DNDT-P0（第2轮迭代发现）:
    原 dn/dT=1.8e-4 /K 来源 iccsz.com/ISSCC 2026 不可溯源二手，违反 R02。
    修复为 1.86e-4 /K（Cocorullo 1999 IEEE JSTQE 5(3):519-521, DOI:10.1109/2944.788409），
    与 sim/heat/solver.py、sim/multiphysics/thermo_optic.py、device/tcad_thermal_package.py
    等 5 处保持一致。差异约 3.3%，影响 Pπ 功耗/热光开关时间/热串扰计算。
    规则: R02 学术诚信 / R05 Bug 必修
    文献:
    - Cocorullo 1999 IEEE JSTQE 5(3):519-521
      https://doi.org/10.1109/2944.788409
    - Cocorullo 1999 Electron. Lett. 35(5):453-455
      https://doi.org/10.1049/el:19990151
    - Komma 2012 Appl. Phys. Lett. 101:041905 复核
      https://doi.org/10.1063/1.4738989
    - Della Corte 2000 IEEE
    - Frey/Gordon/Levi 2006 J. Appl. Phys. 99:033107 综述
      https://doi.org/10.1063/1.2170418
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
            "thermo_optic_coeff_per_k": 1.86e-4,  # Si 热光系数 1.86×10⁻⁴ /K (Cocorullo 1999)
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


# ===========================================================================
# 5. 行波电极 MZI 调制器 traveling_wave_mzm
# ===========================================================================
def make_traveling_wave_mzm() -> Device:
    """行波电极马赫-曾德尔调制器（traveling-wave MZM）。

    Vπ·L ≈ 2.0 V·cm，带宽 > 40 GHz，采用行波电极实现高速调制。
    来源: Reed et al., "Silicon optical modulators", Nature Photonics 2010。
    """
    arm_length = 2000.0  # 行波电极调制臂长度 2mm
    arm_gap = 2.0
    length = arm_length + 40.0  # 含输入/输出 MMI
    ports = _make_mzm_ports(arm_gap, length)
    return Device(
        device_id="soi_traveling_wave_mzm",
        platform="SOI",
        category="active",
        name="traveling_wave_mzm",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-arm_gap / 2 - 0.25, xmax=length, ymax=arm_gap / 2 + 0.25),
        params={
            "vpi_l_v_cm": 2.0,  # Vπ·L ≈ 2.0 V·cm
            "bandwidth_3db_ghz": 40.0,  # 带宽 > 40 GHz
            "electrode_type": "traveling_wave",
            "arm_length_um": 2000.0,
            "modulation_mechanism": "PN junction carrier dispersion",
            "wavelength_nm": 1550,
        },
        source=_SRC_REED_NP2010,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 6. 热调谐微环调制器 thermo_tuned_ring_modulator
# ===========================================================================
def make_thermo_tuned_ring_modulator() -> Device:
    """热调谐微环调制器（thermally tuned ring modulator）。

    FSR ≈ 10 nm，热调谐效率 ≈ 0.8 mW/nm，通过微加热器实现波长调谐。
    来源: Timurdogan et al., JSTQE 2014。
    """
    radius = 8.0  # 微环半径
    gap = 0.2  # 环-总线耦合间隙
    width = 0.5
    ports = _make_mrm_ports(radius, width)
    return Device(
        device_id="soi_thermo_tuned_ring_modulator",
        platform="SOI",
        category="active",
        name="thermo_tuned_ring_modulator",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-width / 2, xmax=2 * radius, ymax=radius + gap + width + width / 2
        ),
        params={
            "fsr_nm": 10.0,  # 自由光谱范围 ≈ 10 nm
            "thermal_tuning_efficiency_mw_nm": 0.8,  # 热调谐效率 ≈ 0.8 mW/nm
            "radius_um": 8.0,
            "tuning_mechanism": "thermal",
            "wavelength_nm": 1550,
        },
        source=_SRC_TIMURDOGAN_JSTQE2014,
        constraints={
            "min_bend_radius_um": 2.0,
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 7. 热光开关 thermo_optic_switch
# ===========================================================================
def make_thermo_optic_switch() -> Device:
    """热光开关（thermo-optic switch, TOS）。

    功耗 ≈ 30 mW，开关时间 ≈ 10 μs，基于 MZI 结构与热光效应实现光路切换。
    来源: Densmore et al., Optics Express 2011。
    """
    arm_length = 200.0  # MZI 干涉臂长度
    arm_gap = 2.0
    length = arm_length + 20.0  # 含输入/输出 MMI
    ports = _make_mzm_ports(arm_gap, length)
    return Device(
        device_id="soi_thermo_optic_switch",
        platform="SOI",
        category="active",
        name="thermo_optic_switch",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-arm_gap / 2 - 0.25, xmax=length, ymax=arm_gap / 2 + 0.25),
        params={
            "power_mw": 30.0,  # 功耗 ≈ 30 mW
            "switching_time_us": 10.0,  # 开关时间 ≈ 10 μs
            "switching_mechanism": "thermo_optic",
            "arm_length_um": 200.0,
            "extinction_ratio_db": 20.0,  # 消光比
            "wavelength_nm": 1550,
        },
        source=_SRC_DENSMORE_OE2011,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 8. 雪崩光电探测器 avalanche_photodetector
# ===========================================================================
def make_avalanche_photodetector() -> Device:
    """雪崩光电探测器（avalanche photodetector, APD）。

    增益 > 10，带宽 > 10 GHz，基于 Ge/Si 雪崩倍增效应实现高灵敏度探测。
    来源: Assefa et al., Nature 2010。
    """
    length = 30.0  # 探测区长度
    width = 0.5
    ports = [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
    ]
    return Device(
        device_id="soi_avalanche_photodetector",
        platform="SOI",
        category="detector",
        name="avalanche_photodetector",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "gain": 10.0,  # 增益 > 10
            "bandwidth_3db_ghz": 10.0,  # 带宽 > 10 GHz
            "detector_type": "Ge/Si APD",
            "detector_length_um": 30.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ASSEFA_NATURE2010,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )
