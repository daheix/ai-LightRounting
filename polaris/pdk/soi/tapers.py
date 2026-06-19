"""SOI 平台锥形与弯曲过渡器件库。

覆盖硅光 SOI 平台的模斑转换器（taper）、S 弯曲波导（S-bend）与欧拉
弯曲波导（Euler bend）三类过渡器件。每个器件参数均来自公开文献/工艺手册
并附带 ``Source`` 溯源（含 URL），禁止假数据
（见项目规则 1.1 与 spec.md 来源核对）。

器件清单：
1. ``linear_taper`` — 线性模斑转换器（宽→窄波导过渡）
2. ``s_bend`` — S 弯曲波导（贝塞尔曲线，平移光轴）
3. ``euler_bend`` — 欧拉弯曲波导（曲率连续，低损耗无辐射模）

来源：
- Luy et al., Proc. SPIE 2005 — SOI taper 设计
  https://doi.org/10.1117/12.608298
- Sacher et al., Optics Express 2014 — SOI S-bend 与 Euler bend
  https://doi.org/10.1364/OE.22.009380
- Tang et al., Optics Express 2022 — Euler bend 低损耗设计
  https://doi.org/10.1364/OE.453449

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
)


# ===========================================================================
# 端口创建辅助函数（降低器件函数 SLOC）
# ===========================================================================
def _make_taper_ports(length: float, w_in: float, w_out: float) -> list[Port]:
    """创建线性 taper 的 in/out 端口（宽度不同）。"""
    return [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=w_in),
        Port(
            name="out",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=w_out,
        ),
    ]


def _make_s_bend_ports(length: float, offset: float, width: float) -> list[Port]:
    """创建 S-bend 的 in/out 端口（出射方向相同，y 偏移 offset）。"""
    return [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="out",
            x=length,
            y=offset,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
    ]


def _make_euler_bend_ports(radius: float, width: float) -> list[Port]:
    """创建 Euler bend 的 in/out 端口（90° 弧，in 朝 WEST，out 朝 NORTH）。"""
    return [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="out",
            x=radius,
            y=radius,
            direction=Direction.NORTH,
            waveguide_type="strip",
            width=width,
        ),
    ]


# ===========================================================================
# 1. 线性模斑转换器 linear_taper
# ===========================================================================
def make_linear_taper() -> Device:
    """线性模斑转换器（linear taper，宽→窄波导过渡）。

    输入宽 2μm（多模）→ 输出宽 0.5μm（单模），长度 10μm，
    插损 <0.1dB，用于波导宽度匹配与模斑转换。
    来源：Luy et al., Proc. SPIE 2005；AIM Photonics 教程。
    """
    length = 10.0
    w_in = 2.0  # 输入宽端口（多模/匹配用）
    w_out = 0.5  # 输出窄端口（单模条形波导）
    ports = _make_taper_ports(length, w_in, w_out)
    return Device(
        device_id="soi_linear_taper",
        platform="SOI",
        category="passive",
        name="linear_taper",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-w_in / 2, xmax=length, ymax=w_in / 2),
        params={
            "length_um": length,
            "width_in_um": w_in,
            "width_out_um": w_out,
            "insertion_loss_db": 0.1,  # 插损 <0.1dB
            "taper_type": "linear",
            "wavelength_nm": 1550,
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. S 弯曲波导 s_bend
# ===========================================================================
def make_s_bend() -> Device:
    """S 弯曲波导（S-bend，贝塞尔曲线平移光轴）。

    长度 20μm，y 偏移 5μm，插损 <0.05dB，用于端口对齐与避免交叉。
    来源：Sacher et al., Optics Express 2014。
    """
    length = 20.0
    offset = 5.0  # y 方向偏移
    width = 0.5
    ports = _make_s_bend_ports(length, offset, width)
    return Device(
        device_id="soi_s_bend",
        platform="SOI",
        category="passive",
        name="s_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=offset + width / 2),
        params={
            "length_um": length,
            "offset_um": offset,
            "insertion_loss_db": 0.05,  # 插损 <0.05dB
            "curve_type": "bezier",
            "width_nm": 500,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 3. 欧拉弯曲波导 euler_bend
# ===========================================================================
def make_euler_bend() -> Device:
    """欧拉弯曲波导（Euler bend，曲率连续过渡）。

    有效半径 5μm（与圆弧 bend 相同占位），插损 <0.02dB，
    曲率从 0 连续增加到 1/R 再回到 0，避免辐射模激发，损耗低于圆弧 bend。
    来源：Tang et al., Optics Express 2022。
    """
    radius = 5.0  # 有效半径（与圆弧 bend 占位一致）
    width = 0.5
    ports = _make_euler_bend_ports(radius, width)
    return Device(
        device_id="soi_euler_bend",
        platform="SOI",
        category="passive",
        name="euler_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=radius, ymax=radius),
        params={
            "effective_radius_um": radius,
            "angle_deg": 90,
            "insertion_loss_db": 0.02,  # 插损 <0.02dB（低于圆弧 bend 的 0.05dB）
            "curve_type": "euler",
            "width_nm": 500,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )
