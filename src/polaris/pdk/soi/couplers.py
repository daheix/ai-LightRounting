"""SOI 平台耦合器与干涉仪器件库。

覆盖硅光 SOI 平台的片上耦合器/干涉仪器件真实参数模型：定向耦合器（DC）、
多模干涉耦合器（MMI 1x2 / 2x2）、马赫-曾德尔干涉仪（MZI）。每个器件参数均
来自公开文献/工艺手册并附带 ``Source`` 溯源（含 URL），禁止假数据
（见项目规则 1.1 与 spec.md 来源核对）。

本模块从 ``passive`` 拆分而来（规则 4.2 重构），通过 ``__init__.py`` 重导出，
保持 ``from polaris.pdk.soi import make_*`` 导入路径不变。

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.soi.sources import (
    _SOI_CONSTRAINTS,
    _SRC_AIM,
    _SRC_ICCSZ,
    _SRC_SOLDANO_JLT1995,
)


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_directional_coupler_ports(length: float, width: float, gap: float) -> list[Port]:
    """创建定向耦合器的 4 个端口（in1/in2 朝 WEST，out1/out2 朝 EAST）。"""
    return [
        Port(
            name="in1",
            x=0.0,
            y=gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="in2",
            x=0.0,
            y=-gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="out1",
            x=length,
            y=gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="out2",
            x=length,
            y=-gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
    ]


def _make_mmi_1x2_ports(length: float, out_gap: float) -> list[Port]:
    """创建 MMI 1x2 的 3 个端口（1 输入 2 输出）。"""
    return [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=0.5),
        Port(
            name="out1",
            x=length,
            y=out_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="out2",
            x=length,
            y=-out_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
    ]


def _make_mmi_2x2_ports(length: float, in_gap: float) -> list[Port]:
    """创建 MMI 2x2 的 4 个端口（2 输入 2 输出）。"""
    return [
        Port(
            name="in1",
            x=0.0,
            y=in_gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="in2",
            x=0.0,
            y=-in_gap / 2,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="out1",
            x=length,
            y=in_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
        Port(
            name="out2",
            x=length,
            y=-in_gap / 2,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        ),
    ]


def _make_mzi_ports(arm_gap: float, length: float) -> list[Port]:
    """创建 MZI 的 4 个端口（双臂干涉，in1/in2 朝 WEST，out1/out2 朝 EAST）。"""
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


# ===========================================================================
# 1. 定向耦合器 directional_coupler
# ===========================================================================
def make_directional_coupler() -> Device:
    """定向耦合器（directional coupler, DC）。

    间隙 100-300nm，耦合长度 5-20μm，实现 3dB 功率分束。
    来源：AIM Photonics 教程。
    """
    length = 10.0  # 耦合长度 5-20μm
    width = 0.5
    gap = 0.5  # 端口间距（波导间物理间距，μm）
    ports = _make_directional_coupler_ports(length, width, gap)
    return Device(
        device_id="soi_directional_coupler",
        platform="SOI",
        category="passive",
        name="directional_coupler",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-gap / 2 - width / 2, xmax=length, ymax=gap / 2 + width / 2
        ),
        params={
            "gap_nm": 200,  # 耦合间隙 100-300nm
            "coupling_length_um": 10.0,  # 耦合长度 5-20μm
            "width_nm": 500,
            "coupling_ratio": 0.5,  # 3dB 耦合
            "loss_db": 0.2,
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. MMI 1x2 mmi_1x2
# ===========================================================================
def make_mmi_1x2() -> Device:
    """MMI 1x2（多模干涉耦合器，1 输入 2 输出）。

    插损 <0.5dB，imbalance <5%。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 10.0  # MMI 区长度
    width = 3.0  # MMI 区宽度
    out_gap = 1.0  # 两输出端口间距
    ports = _make_mmi_1x2_ports(length, out_gap)
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
# 3. MMI 2x2 mmi_2x2
# ===========================================================================
def make_mmi_2x2() -> Device:
    """MMI 2x2（多模干涉耦合器，2 输入 2 输出）。

    插损 <0.5dB，imbalance <5%。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 12.0  # MMI 区长度
    width = 3.0
    in_gap = 1.0
    ports = _make_mmi_2x2_ports(length, in_gap)
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
# 4. MZI 马赫-曾德尔干涉仪 mzi
# ===========================================================================
def make_mzi() -> Device:
    """马赫-曾德尔干涉仪（MZI，双臂干涉）。

    双臂干涉，臂长差控相位，构成滤波/调制基本单元。
    来源：AIM Photonics 教程。
    """
    arm_length = 100.0  # 干涉臂长度
    arm_gap = 2.0  # 两臂间距
    length = arm_length + 20.0  # 含输入/输出 MMI 长度
    ports = _make_mzi_ports(arm_gap, length)
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
# 5. MMI 1x4 mmi_1x4
# ===========================================================================
def _make_mmi_1x4_ports(length: float, out_gap: float) -> list[Port]:
    """创建 MMI 1x4 的 5 个端口（1 输入 4 输出）。"""
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=0.5)
    ]
    offsets = [1.5 * out_gap, 0.5 * out_gap, -0.5 * out_gap, -1.5 * out_gap]
    for i, offset in enumerate(offsets):
        ports.append(
            Port(
                name=f"out{i + 1}",
                x=length,
                y=offset,
                direction=Direction.EAST,
                waveguide_type="strip",
                width=0.5,
            )
        )
    return ports


def make_mmi_1x4() -> Device:
    """MMI 1x4（多模干涉耦合器，1 输入 4 输出）。

    插损 < 0.5 dB，均匀性 < 0.5 dB，基于自成像原理实现 1x4 功率分束。
    来源: Soldano et al., JLT 1995。
    """
    length = 20.0  # MMI 区长度
    width = 6.0  # MMI 区宽度
    out_gap = 1.0  # 输出端口间距
    ports = _make_mmi_1x4_ports(length, out_gap)
    return Device(
        device_id="soi_mmi_1x4",
        platform="SOI",
        category="passive",
        name="mmi_1x4",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "insertion_loss_db": 0.4,  # 插损 < 0.5 dB
            "uniformity_db": 0.4,  # 均匀性 < 0.5 dB
            "mmi_length_um": 20.0,
            "mmi_width_um": 6.0,
            "num_outputs": 4,
            "wavelength_nm": 1550,
        },
        source=_SRC_SOLDANO_JLT1995,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 6. MMI 4x4 mmi_4x4
# ===========================================================================
def _make_mmi_4x4_ports(length: float, gap: float) -> list[Port]:
    """创建 MMI 4x4 的 8 个端口（4 输入 4 输出）。"""
    ports: list[Port] = []
    offsets = [1.5 * gap, 0.5 * gap, -0.5 * gap, -1.5 * gap]
    for i, offset in enumerate(offsets):
        ports.append(
            Port(
                name=f"in{i + 1}",
                x=0.0,
                y=offset,
                direction=Direction.WEST,
                waveguide_type="strip",
                width=0.5,
            )
        )
        ports.append(
            Port(
                name=f"out{i + 1}",
                x=length,
                y=offset,
                direction=Direction.EAST,
                waveguide_type="strip",
                width=0.5,
            )
        )
    return ports


def make_mmi_4x4() -> Device:
    """MMI 4x4（多模干涉耦合器，4 输入 4 输出）。

    插损 < 1.0 dB，基于自成像原理实现 4x4 功率分束/合束。
    来源: Soldano et al., JLT 1995。
    """
    length = 25.0  # MMI 区长度
    width = 6.0  # MMI 区宽度
    gap = 1.0  # 端口间距
    ports = _make_mmi_4x4_ports(length, gap)
    return Device(
        device_id="soi_mmi_4x4",
        platform="SOI",
        category="passive",
        name="mmi_4x4",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "insertion_loss_db": 0.8,  # 插损 < 1.0 dB
            "uniformity_db": 0.6,
            "mmi_length_um": 25.0,
            "mmi_width_um": 6.0,
            "num_inputs": 4,
            "num_outputs": 4,
            "wavelength_nm": 1550,
        },
        source=_SRC_SOLDANO_JLT1995,
        constraints=_SOI_CONSTRAINTS,
    )
