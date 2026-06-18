"""InP 平台被动器件库。

覆盖 InP（Indium Phosphide）有源集成平台的被动器件真实参数模型：
有源波导与马赫-曾德调制器（MZM）。每个器件参数均来自公开文献并附带
``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。

来源文献：
- Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry
  https://doi.org/10.3390/app9081588
- Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO
  https://doi.org/10.1109/JSTQE.2018.2866565
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.inp.sources import (
    _INP_CONSTRAINTS,
    _SOURCE_SOARES,
    _SOURCE_ZHAO,
    _WG_WIDTH,
    _make_inout_ports,
)
from polaris.pdk.port import Direction, Port


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_inp_mzm_ports(length: float) -> list[Port]:
    """创建 InP MZM 的 4 个端口（in/out 光端口 + rf1/rf2 双臂电端口）。

    rf1 朝 NORTH（+y），rf2 朝 SOUTH（-y），均位于长度中点。

    Args:
        length: MZM 长度（μm），决定光端口与电端口 x 坐标。

    Returns:
        含 in、out、rf1、rf2 四端口的列表。
    """
    half_w = _WG_WIDTH / 2.0
    return [
        *_make_inout_ports(length),
        Port(
            name="rf1",
            x=length / 2.0,
            y=half_w,
            direction=Direction.NORTH,
            waveguide_type="electrical",
            width=50.0,
        ),
        Port(
            name="rf2",
            x=length / 2.0,
            y=-half_w,
            direction=Direction.SOUTH,
            waveguide_type="electrical",
            width=50.0,
        ),
    ]


# ===========================================================================
# 1. InP 有源波导 inp_waveguide
# ===========================================================================
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
        ports=_make_inout_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w),
        params={
            "width_um": _WG_WIDTH,
            "width_range_um": "1.5-2.5",
            "ssc_mode_field_um": "10x7",
            "length_um": length,
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 2. InP MZM 马赫-曾德调制器 inp_mzm
# ===========================================================================
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
        ports=_make_inp_mzm_ports(length),
        bbox=BoundingBox(xmin=0.0, ymin=-half_w - 50.0, xmax=length, ymax=half_w + 50.0),
        params={
            "length_mm": 1.0,
            "length_um": length,
            "modulation_type": "MZM",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_ZHAO,
        constraints=_INP_CONSTRAINTS,
    )
