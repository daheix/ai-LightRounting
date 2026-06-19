"""InP 平台锥形与弯曲过渡器件库。

覆盖 InP（Indium Phosphide）有源集成平台的模斑转换器（taper）、S 弯曲
波导（S-bend）与欧拉弯曲波导（Euler bend）。每个器件参数均来自公开文献
并附带 ``Source`` 溯源（含 URL），禁止假数据（见项目规则 1.1 与 spec.md
来源核对）。

器件清单：
1. ``inp_linear_taper`` — 线性模斑转换器（SSC 模场匹配）
2. ``inp_s_bend`` — S 弯曲波导
3. ``inp_euler_bend`` — 欧拉弯曲波导

来源：
- Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry
  https://doi.org/10.3390/app9081588
- Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO
  https://doi.org/10.1109/JSTQE.2018.2866565

设计约束（InP 平台，参考 spec.md）：
- 最小弯曲半径 250μm（低折射率差有源平台需大弯曲半径）
- 最小器件间距 2μm
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.inp.sources import (
    _INP_CONSTRAINTS,
    _SOURCE_SOARES,
    _WG_TYPE,
    _WG_WIDTH,
)
from polaris.pdk.port import Direction, Port


# ===========================================================================
# 端口创建辅助函数（降低器件函数 SLOC）
# ===========================================================================
def _make_inp_taper_ports(length: float, w_in: float, w_out: float) -> list[Port]:
    """创建 InP taper 的 in/out 端口。"""
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type=_WG_TYPE,
            width=w_in,
        ),
        Port(
            name="out",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type=_WG_TYPE,
            width=w_out,
        ),
    ]


def _make_inp_s_bend_ports(length: float, offset: float, width: float) -> list[Port]:
    """创建 InP S-bend 的 in/out 端口。"""
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type=_WG_TYPE,
            width=width,
        ),
        Port(
            name="out",
            x=length,
            y=offset,
            direction=Direction.EAST,
            waveguide_type=_WG_TYPE,
            width=width,
        ),
    ]


def _make_inp_euler_bend_ports(radius: float, width: float) -> list[Port]:
    """创建 InP Euler bend 的 in/out 端口（90° 弧）。"""
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type=_WG_TYPE,
            width=width,
        ),
        Port(
            name="out",
            x=radius,
            y=radius,
            direction=Direction.NORTH,
            waveguide_type=_WG_TYPE,
            width=width,
        ),
    ]


# ===========================================================================
# 1. InP 线性模斑转换器 inp_linear_taper
# ===========================================================================
def make_inp_linear_taper() -> Device:
    """InP 线性模斑转换器（SSC 模场匹配）。

    输入宽 10μm（光纤模场匹配）→ 输出宽 2μm（有源波导），长度 200μm，
    插损 <1dB，实现光纤-芯片高效耦合。
    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry。
    """
    length = 200.0
    w_in = 10.0  # 光纤模场匹配宽端口
    w_out = _WG_WIDTH
    ports = _make_inp_taper_ports(length, w_in, w_out)
    return Device(
        device_id="inp_linear_taper",
        platform="InP",
        category="passive",
        name="inp_linear_taper",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-w_in / 2, xmax=length, ymax=w_in / 2),
        params={
            "length_um": length,
            "width_in_um": w_in,
            "width_out_um": w_out,
            "insertion_loss_db": 1.0,
            "taper_type": "linear_ssc",
            "wavelength_nm": 1550,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 2. InP S 弯曲波导 inp_s_bend
# ===========================================================================
def make_inp_s_bend() -> Device:
    """InP S 弯曲波导（贝塞尔曲线平移光轴）。

    长度 300μm，y 偏移 20μm，插损 <0.2dB。
    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry。
    """
    length = 300.0
    offset = 20.0
    width = _WG_WIDTH
    ports = _make_inp_s_bend_ports(length, offset, width)
    return Device(
        device_id="inp_s_bend",
        platform="InP",
        category="passive",
        name="inp_s_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=offset + width / 2),
        params={
            "length_um": length,
            "offset_um": offset,
            "insertion_loss_db": 0.2,
            "curve_type": "bezier",
            "wavelength_nm": 1550,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 3. InP 欧拉弯曲波导 inp_euler_bend
# ===========================================================================
def make_inp_euler_bend() -> Device:
    """InP 欧拉弯曲波导（曲率连续过渡）。

    有效半径 250μm（InP 平台最小弯曲半径），插损 <0.1dB。
    来源：Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO。
    """
    radius = 250.0
    width = _WG_WIDTH
    ports = _make_inp_euler_bend_ports(radius, width)
    return Device(
        device_id="inp_euler_bend",
        platform="InP",
        category="passive",
        name="inp_euler_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=radius, ymax=radius),
        params={
            "effective_radius_um": radius,
            "angle_deg": 90,
            "insertion_loss_db": 0.1,
            "curve_type": "euler",
            "wavelength_nm": 1550,
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )
