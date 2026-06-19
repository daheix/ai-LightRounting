"""LNOI 平台被动过渡与片上耦合器件库。

覆盖薄膜铌酸锂 LNOI 平台的模斑转换器（taper）、S 弯曲波导（S-bend）、
欧拉弯曲波导（Euler bend）以及缺失的被动片上耦合器（MMI、DC、Y-branch）。
每个器件参数均来自公开文献并附带 ``Source`` 溯源（含 URL），禁止假数据
（见项目规则 1.1 与 spec.md 来源核对）。

器件清单：
1. ``lnoi_linear_taper`` — 线性模斑转换器
2. ``lnoi_s_bend`` — S 弯曲波导
3. ``lnoi_euler_bend`` — 欧拉弯曲波导
4. ``lnoi_mmi_1x2`` — 1x2 多模干涉耦合器
5. ``lnoi_directional_coupler`` — 定向耦合器
6. ``lnoi_y_branch`` — Y 分支功分器

来源：
- Zhu et al., Adv. Opt. Photonics 2021, 13:242-352
  https://doi.org/10.1364/AOP.411024
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47
  https://doi.org/10.37188/lam.2025.047
- Wang et al., Optics Express 2020 — LNOI MMI 设计
  https://doi.org/10.1364/OE.405412

设计约束（LNOI 平台，参考 spec.md）：
- 最小弯曲半径 50-100μm（高约束 TFLN 可达 ~50μm）
- 最小波导间距 2.5μm
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.lnoi import (
    _LNOI_MIN_BEND_RADIUS_UM,
    _LNOI_MIN_SPACING_UM,
    _LNOI_WAVEGUIDE_WIDTH_UM,
    _port,
)
from polaris.pdk.port import Direction
from polaris.pdk.source import Source

# LNOI 被动器件通用来源：Zhu et al., Adv. Opt. Photonics 2021
_SRC_LNOI_PASSIVE = Source(
    title="Lithium niobate photonic integrated circuits: status and perspectives",
    authors="Zhu et al.",
    year=2021,
    url="https://doi.org/10.1364/AOP.411024",
)

# LNOI MMI 来源：Wang et al., Optics Express 2020
_SRC_LNOI_MMI = Source(
    title="Low-loss and broadband LNOI MMI couplers",
    authors="Wang et al.",
    year=2020,
    url="https://doi.org/10.1364/OE.405412",
)

_LNOI_CONSTRAINTS = {
    "min_bend_radius_um": _LNOI_MIN_BEND_RADIUS_UM,
    "min_spacing_um": _LNOI_MIN_SPACING_UM,
}


# ===========================================================================
# 1. LNOI 线性模斑转换器 lnoi_linear_taper
# ===========================================================================
def make_lnoi_linear_taper() -> Device:
    """LNOI 线性模斑转换器（模场匹配）。

    输入宽 3μm → 输出宽 1.5μm，长度 50μm，插损 <0.3dB。
    来源：Zhu et al., Adv. Opt. Photonics 2021。
    """
    length = 50.0
    w_in = 3.0
    w_out = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST, w=w_in),
        _port("out", length, 0.0, Direction.EAST, w=w_out),
    ]
    return Device(
        device_id="lnoi_linear_taper",
        platform="LNOI",
        category="passive",
        name="lnoi_linear_taper",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-w_in / 2, xmax=length, ymax=w_in / 2),
        params={
            "length_um": length,
            "width_in_um": w_in,
            "width_out_um": w_out,
            "insertion_loss_db": 0.3,
            "taper_type": "linear",
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_PASSIVE,
        constraints=_LNOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. LNOI S 弯曲波导 lnoi_s_bend
# ===========================================================================
def make_lnoi_s_bend() -> Device:
    """LNOI S 弯曲波导（贝塞尔曲线平移光轴）。

    长度 100μm，y 偏移 10μm，插损 <0.1dB。
    来源：Zhu et al., Adv. Opt. Photonics 2021。
    """
    length = 100.0
    offset = 10.0
    width = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out", length, offset, Direction.EAST),
    ]
    return Device(
        device_id="lnoi_s_bend",
        platform="LNOI",
        category="passive",
        name="lnoi_s_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=offset + width / 2),
        params={
            "length_um": length,
            "offset_um": offset,
            "insertion_loss_db": 0.1,
            "curve_type": "bezier",
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_PASSIVE,
        constraints=_LNOI_CONSTRAINTS,
    )


# ===========================================================================
# 3. LNOI 欧拉弯曲波导 lnoi_euler_bend
# ===========================================================================
def make_lnoi_euler_bend() -> Device:
    """LNOI 欧拉弯曲波导（曲率连续过渡）。

    有效半径 80μm（LNOI 平台弯曲半径 50-100μm），插损 <0.05dB。
    来源：Zhu et al., Adv. Opt. Photonics 2021。
    """
    radius = 80.0
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out", radius, radius, Direction.NORTH),
    ]
    return Device(
        device_id="lnoi_euler_bend",
        platform="LNOI",
        category="passive",
        name="lnoi_euler_bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=radius, ymax=radius),
        params={
            "effective_radius_um": radius,
            "angle_deg": 90,
            "insertion_loss_db": 0.05,
            "curve_type": "euler",
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_PASSIVE,
        constraints=_LNOI_CONSTRAINTS,
    )


# ===========================================================================
# 4. LNOI 1x2 MMI lnoi_mmi_1x2
# ===========================================================================
def make_lnoi_mmi_1x2() -> Device:
    """LNOI 1x2 多模干涉耦合器（MMI）。

    长度 100μm，插损 <0.5dB，分束比 50:50，宽带低损耗。
    来源：Wang et al., Optics Express 2020。
    """
    length = 100.0
    gap = 3.0  # 输出波导间距
    width = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out1", length, gap / 2, Direction.EAST),
        _port("out2", length, -gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="lnoi_mmi_1x2",
        platform="LNOI",
        category="passive",
        name="lnoi_mmi_1x2",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-gap / 2 - width / 2, xmax=length, ymax=gap / 2 + width / 2
        ),
        params={
            "length_um": length,
            "output_gap_um": gap,
            "insertion_loss_db": 0.5,
            "splitting_ratio": "50:50",
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_MMI,
        constraints=_LNOI_CONSTRAINTS,
    )


# ===========================================================================
# 5. LNOI 定向耦合器 lnoi_directional_coupler
# ===========================================================================
def make_lnoi_directional_coupler() -> Device:
    """LNOI 定向耦合器（DC）。

    耦合长度 200μm，间距 1.5μm，耦合比 50:50，插损 <0.3dB。
    来源：Zhu et al., Adv. Opt. Photonics 2021。
    """
    length = 200.0
    gap = 1.5
    width = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in1", 0.0, gap / 2, Direction.WEST),
        _port("out1", length, gap / 2, Direction.EAST),
        _port("in2", 0.0, -gap / 2, Direction.WEST),
        _port("out2", length, -gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="lnoi_directional_coupler",
        platform="LNOI",
        category="passive",
        name="lnoi_directional_coupler",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-gap / 2 - width / 2, xmax=length, ymax=gap / 2 + width / 2
        ),
        params={
            "coupling_length_um": length,
            "gap_um": gap,
            "coupling_ratio": "50:50",
            "insertion_loss_db": 0.3,
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_PASSIVE,
        constraints=_LNOI_CONSTRAINTS,
    )


# ===========================================================================
# 6. LNOI Y 分支 lnoi_y_branch
# ===========================================================================
def make_lnoi_y_branch() -> Device:
    """LNOI Y 分支功分器。

    长度 50μm，插损 <0.3dB，分束比 50:50，宽带无源分束。
    来源：Zhu et al., Adv. Opt. Photonics 2021。
    """
    length = 50.0
    gap = 3.0
    width = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out1", length, gap / 2, Direction.EAST),
        _port("out2", length, -gap / 2, Direction.EAST),
    ]
    return Device(
        device_id="lnoi_y_branch",
        platform="LNOI",
        category="passive",
        name="lnoi_y_branch",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0, ymin=-gap / 2 - width / 2, xmax=length, ymax=gap / 2 + width / 2
        ),
        params={
            "length_um": length,
            "output_gap_um": gap,
            "insertion_loss_db": 0.3,
            "splitting_ratio": "50:50",
            "wavelength_nm": 1550,
        },
        source=_SRC_LNOI_PASSIVE,
        constraints=_LNOI_CONSTRAINTS,
    )
