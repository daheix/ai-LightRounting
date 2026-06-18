"""硅光 SOI 平台被动器件库（自 soi.py 拆分）。

覆盖硅光 SOI 平台的 MMI、MZI、微环谐振器、Y 分支、波导交叉、热光移相器
等被动/干涉器件真实参数模型。每个器件参数均来自公开文献/工艺手册并附带
``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

来源汇总（spec.md 已逐项核对网址）：
- AIM Photonics 无源硅基光电子芯片元件教程
  https://www.latitudeda.com/document/716
- 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
  http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm

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
# AIM Photonics 无源硅基光电子元件教程（latitudeda.com 托管）
_SRC_AIM = Source(
    title="AIM Photonics Passive Silicon Photonic Component Tutorial",
    authors="AIM Photonics / Latitude DA",
    year=2023,
    url="https://www.latitudeda.com/document/716",
)
# 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）
_SRC_ICCSZ = Source(
    title="硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数）",
    authors="光学小豆芽 / ICCSZ",
    year=2019,
    url="http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm",
)

# SOI 平台通用设计约束（弯曲半径 2-6μm，波导间距 ≥1μm，见 spec.md）
_SOI_CONSTRAINTS = {
    "min_bend_radius_um": 5.0,
    "min_spacing_um": 1.0,
    "wavelength_nm": 1550,
}


def _port(name: str, x: float, y: float, d: Direction, w: float = 0.5) -> Port:
    """创建端口的紧凑辅助函数（降低器件函数 SLOC）。"""
    return Port(name=name, x=x, y=y, direction=d, waveguide_type="strip", width=w)


# ===========================================================================
# MMI 1x2 mmi_1x2
# ===========================================================================
def make_mmi_1x2() -> Device:
    """MMI 1x2（多模干涉耦合器，1 输入 2 输出）。

    插损 <0.5dB，imbalance <5%。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 10.0  # MMI 区长度
    width = 3.0  # MMI 区宽度
    out_gap = 1.0  # 两输出端口间距
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out1", length, out_gap / 2, Direction.EAST),
        _port("out2", length, -out_gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="soi_mmi_1x2",
        platform="SOI",
        category="passive",
        name="mmi_1x2",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "insertion_loss_db": 0.4,  # 插损 <0.5dB
            "imbalance_db": 0.2,  # imbalance <5%（~0.2dB）
            "mmi_length_um": 10.0,
            "mmi_width_um": 3.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# MMI 2x2 mmi_2x2
# ===========================================================================
def make_mmi_2x2() -> Device:
    """MMI 2x2（多模干涉耦合器，2 输入 2 输出）。

    插损 <0.5dB，imbalance <5%。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 12.0  # MMI 区长度
    width = 3.0
    in_gap = 1.0
    ports = [
        _port("in1", 0.0, in_gap / 2, Direction.WEST),
        _port("in2", 0.0, -in_gap / 2, Direction.WEST),
        _port("out1", length, in_gap / 2, Direction.EAST),
        _port("out2", length, -in_gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="soi_mmi_2x2",
        platform="SOI",
        category="passive",
        name="mmi_2x2",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "insertion_loss_db": 0.4,  # 插损 <0.5dB
            "imbalance_db": 0.2,  # imbalance <5%
            "mmi_length_um": 12.0,
            "mmi_width_um": 3.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# MZI 马赫-曾德尔干涉仪 mzi
# ===========================================================================
def make_mzi() -> Device:
    """马赫-曾德尔干涉仪（MZI，双臂干涉）。

    双臂干涉，臂长差控相位，构成滤波/调制基本单元。
    来源：AIM Photonics 教程。
    """
    arm_length = 100.0  # 干涉臂长度
    arm_gap = 2.0  # 两臂间距
    length = arm_length + 20.0  # 含输入/输出 MMI 长度
    ports = [
        _port("in1", 0.0, arm_gap / 2, Direction.WEST),
        _port("in2", 0.0, -arm_gap / 2, Direction.WEST),
        _port("out1", length, arm_gap / 2, Direction.EAST),
        _port("out2", length, -arm_gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="soi_mzi",
        platform="SOI",
        category="passive",
        name="mzi",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-arm_gap / 2 - 0.25, xmax=length, ymax=arm_gap / 2 + 0.25),
        params={
            "arm_length_um": 100.0,  # 干涉臂长度
            "arm_length_diff_um": 0.0,  # 臂长差（控相位）
            "arm_gap_um": 2.0,
            "insertion_loss_db": 1.0,
            "fsr_nm": 10.0,  # 自由光谱范围
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 微环谐振器 ring_resonator
# ===========================================================================
def make_ring_resonator() -> Device:
    """微环谐振器（add-drop ring resonator）。

    半径 5-20μm，与总线波导耦合构成谐振滤波/调制单元。
    来源：AIM Photonics 教程。
    """
    radius = 10.0  # 半径 5-20μm
    gap = 0.2  # 环-总线耦合间隙 200nm
    width = 0.5
    # 总线波导沿 x 轴，环圆心在 (radius, radius+gap+width)
    bus_y = 0.0
    ring_top = 2 * (radius + gap + width)
    ports = [
        _port("in", 0.0, bus_y, Direction.WEST, width),
        _port("through", 2 * radius, bus_y, Direction.EAST, width),
        _port("drop", 2 * radius, ring_top, Direction.EAST, width),
        _port("add", 0.0, ring_top, Direction.WEST, width),
    ]
    return Device(
        device_id="soi_ring_resonator",
        platform="SOI",
        category="passive",
        name="ring_resonator",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=2 * radius, ymax=ring_top + width / 2),
        params={
            "radius_um": 10.0,  # 半径 5-20μm
            "gap_nm": 200,  # 耦合间隙
            "q_factor": 10000,  # 品质因数
            "fsr_nm": 10.0,  # 自由光谱范围
            "loss_db_cm": 2.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# Y 分支 y_branch
# ===========================================================================
def make_y_branch() -> Device:
    """Y 分支（Y-branch，1x2 功分器）。

    插损 <0.3dB，宽带无源分束。
    来源：AIM Photonics 教程。
    """
    length = 20.0
    out_gap = 1.0
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out1", length, out_gap / 2, Direction.EAST),
        _port("out2", length, -out_gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="soi_y_branch",
        platform="SOI",
        category="passive",
        name="y_branch",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-out_gap / 2 - 0.25, xmax=length, ymax=out_gap / 2 + 0.25),
        params={
            "insertion_loss_db": 0.3,  # 插损 <0.3dB
            "imbalance_db": 0.1,
            "bandwidth_nm": 100,  # 宽带
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 波导交叉 crossing
# ===========================================================================
def make_crossing() -> Device:
    """波导交叉（waveguide crossing）。

    插损 ~0.3dB，串扰 ~-30dB，实现正交波导低损耗低串扰交叉。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    size = 5.0  # 交叉区尺寸
    width = 0.5
    ports = [
        _port("in1", 0.0, 0.0, Direction.WEST, width),
        _port("out1", size, 0.0, Direction.EAST, width),
        _port("in2", size / 2, 0.0, Direction.SOUTH, width),
        _port("out2", size / 2, size, Direction.NORTH, width),
    ]
    return Device(
        device_id="soi_crossing",
        platform="SOI",
        category="passive",
        name="crossing",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=size, ymax=size),
        params={
            "insertion_loss_db": 0.3,  # 插损 ~0.3dB
            "crosstalk_db": -30.0,  # 串扰 ~-30dB
            "crossing_size_um": 5.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 热光移相器 thermo_optic_phase_shifter
# ===========================================================================
def make_thermo_optic_phase_shifter() -> Device:
    """热光移相器（thermo-optic phase shifter, TOPS）。

    Pπ ~20mW，基于 Si 热光系数（1.8×10⁻⁴ /K）实现相位调谐。
    来源：硅光工艺平台比较（iccsz.com）；热光系数来源台积电 ISSCC 2026。
    """
    length = 100.0  # 加热器长度
    width = 0.5
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST, width),
        _port("out", length, 0.0, Direction.EAST, width),
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
