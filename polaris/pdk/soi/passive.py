"""SOI 平台被动器件库（波导/弯曲/Y 分支/交叉/光纤耦合器）。

覆盖硅光 SOI 平台的被动器件真实参数模型：条形/肋形波导、弯曲、Y 分支、
波导交叉、光栅耦合器与端面耦合器。片上耦合器/干涉仪（DC、MMI、MZI）已拆分
至 ``couplers`` 模块（规则 4.2 重构）。每个器件参数均来自公开文献/工艺手册
并附带 ``Source`` 溯源（含 URL），禁止假数据
（见项目规则 1.1 与 spec.md 来源核对）。

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
    _SRC_SAMSUNG,
    _SRC_TSMC,
)


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_bend_ports(radius: float, width: float) -> list[Port]:
    """创建弯曲波导的 2 个端口（90° 弧，in 朝 WEST，out 朝 NORTH）。

    圆心 (R, 0)，弧从 (0,0) 切向 +x 到 (R,R) 切向 +y。
    """
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


def _make_y_branch_ports(length: float, out_gap: float) -> list[Port]:
    """创建 Y 分支的 3 个端口（1 输入 2 输出）。"""
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


def _make_crossing_ports(size: float, width: float) -> list[Port]:
    """创建波导交叉的 4 个端口（水平 in1/out1，垂直 in2/out2）。"""
    return [
        Port(
            name="in1", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="out1",
            x=size,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="in2",
            x=size / 2,
            y=0.0,
            direction=Direction.SOUTH,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="out2",
            x=size / 2,
            y=size,
            direction=Direction.NORTH,
            waveguide_type="strip",
            width=width,
        ),
    ]


# ===========================================================================
# 1. 条形波导 strip_waveguide
# ===========================================================================
def make_strip_waveguide() -> Device:
    """条形波导（strip waveguide，全刻蚀）。

    厚 220nm，宽 450-500nm（单模 TE0），传播损耗 1-3 dB/cm。
    来源：AIM Photonics 教程 + 硅光工艺平台比较（iccsz.com）。
    """
    length = 10.0  # 默认 10μm 直波导
    width = 0.5  # 500nm 单模
    ports = [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="out",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
    ]
    return Device(
        device_id="soi_strip_waveguide",
        platform="SOI",
        category="passive",
        name="strip_waveguide",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "thickness_nm": 220,  # SOI 顶层硅厚 220nm
            "width_nm": 500,  # 单模条形波导宽 450-500nm
            "loss_db_cm": 2.0,  # 传播损耗 1-3 dB/cm
            "wavelength_nm": 1550,
            "mode": "TE0",
        },
        source=_SRC_AIM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. 肋形波导 rib_waveguide
# ===========================================================================
def make_rib_waveguide() -> Device:
    """肋形波导（rib waveguide，浅刻蚀）。

    SOI 厚 220nm，slab 高 90nm，浅刻蚀，损耗更低，适用于长距离布线。
    来源：硅光工艺平台比较（iccsz.com）；三星 Si rib 损耗 0.7 dB/cm。
    """
    length = 10.0
    width = 0.5
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="rib", width=width),
        Port(
            name="out", x=length, y=0.0, direction=Direction.EAST, waveguide_type="rib", width=width
        ),
    ]
    return Device(
        device_id="soi_rib_waveguide",
        platform="SOI",
        category="passive",
        name="rib_waveguide",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "thickness_nm": 220,  # SOI 顶层硅厚 220nm
            "slab_height_nm": 90,  # slab 残留高度 90nm（浅刻蚀）
            "width_nm": 500,
            "loss_db_cm": 0.7,  # 三星 Si rib 损耗 0.7 dB/cm
            "wavelength_nm": 1550,
            "mode": "TE0",
        },
        source=_SRC_ICCSZ,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 3. 弯曲波导 bend
# ===========================================================================
def make_bend() -> Device:
    """弯曲波导（90° 圆弧 bend）。

    最小弯曲半径 2-6μm（高折射率差 SOI 平台），损耗 0.01-0.1 dB/90°。
    来源：台积电 ISSCC 2026 硅光子学平台解析。
    """
    radius = 5.0  # 默认半径 5μm（区间 2-6μm）
    width = 0.5
    ports = _make_bend_ports(radius, width)
    return Device(
        device_id="soi_bend",
        platform="SOI",
        category="passive",
        name="bend",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=radius, ymax=radius),
        params={
            "radius_um": radius,  # 弯曲半径 2-6μm
            "angle_deg": 90,  # 90° 弧
            "loss_db_90": 0.05,  # 损耗 0.01-0.1 dB/90°
            "width_nm": 500,
            "wavelength_nm": 1550,
        },
        source=_SRC_TSMC,
        constraints={
            "min_bend_radius_um": 2.0,  # 高折射率差平台最小弯曲半径
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 4. 光栅耦合器 1D Si grating_coupler_1d
# ===========================================================================
def make_grating_coupler_1d() -> Device:
    """一维硅光栅耦合器（1D Si grating coupler）。

    峰值耦合损耗 1.9dB，1-dB 带宽 27nm，O 波段 TE 偏振。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    width = 12.0  # 光栅区宽度
    length = 20.0  # 光栅区长度
    ports = [
        # 波导端口（水平出射）
        Port(name="wg", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id="soi_grating_coupler_1d",
        platform="SOI",
        category="passive",
        name="grating_coupler_1d",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=length, ymax=width / 2),
        params={
            "peak_coupling_loss_db": 1.9,  # 峰值耦合损耗 1.9dB
            "bandwidth_1db_nm": 27,  # 1-dB 带宽 27nm
            "wavelength_nm": 1310,  # O 波段
            "polarization": "TE",
            "grating_type": "1D Si",
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )


# ===========================================================================
# 5. 光栅耦合器 2D Si grating_coupler_2d
# ===========================================================================
def make_grating_coupler_2d() -> Device:
    """二维硅光栅耦合器（2D Si grating coupler）。

    耦合损耗 2.4dB，1-dB 带宽 17nm，TE/TM 双模兼容。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    size = 15.0  # 2D 光栅方形边长
    ports = [
        Port(name="wg", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id="soi_grating_coupler_2d",
        platform="SOI",
        category="passive",
        name="grating_coupler_2d",
        ports=ports,
        bbox=BoundingBox(xmin=-size / 2, ymin=-size / 2, xmax=size / 2, ymax=size / 2),
        params={
            "coupling_loss_db": 2.4,  # 耦合损耗 2.4dB
            "bandwidth_1db_nm": 17,  # 1-dB 带宽 17nm
            "wavelength_nm": 1310,  # O 波段
            "polarization": "TE/TM",  # TE/TM 双模兼容
            "grating_type": "2D Si",
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )


# ===========================================================================
# 6. 端面耦合器 edge_coupler
# ===========================================================================
def make_edge_coupler() -> Device:
    """端面耦合器（edge coupler，模斑转换器 SSC）。

    耦合损耗 ~2dB（传统），优化后 0.2-1dB，宽带光纤-芯片耦合。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    length = 200.0  # 锥形长度
    width = 0.5
    ports = [
        # 芯片端面侧（光纤耦合，宽端口）
        Port(
            name="fiber", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=3.0
        ),
        # 波导侧（窄端口）
        Port(
            name="wg",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
    ]
    return Device(
        device_id="soi_edge_coupler",
        platform="SOI",
        category="passive",
        name="edge_coupler",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-1.5, xmax=length, ymax=1.5),
        params={
            "coupling_loss_db": 2.0,  # 传统耦合损耗 ~2dB
            "optimized_loss_db": 0.5,  # 优化后 0.2-1dB
            "bandwidth_nm": 200,  # 宽带
            "taper_length_um": 200.0,
            "wavelength_nm": 1550,
        },
        source=_SRC_ICCSZ,
        constraints={
            "min_spacing_um": 1.0,
            "wavelength_nm": 1550,
        },
    )


# ===========================================================================
# 7. Y 分支 y_branch
# ===========================================================================
def make_y_branch() -> Device:
    """Y 分支（Y-branch，1x2 功分器）。

    插损 <0.3dB，宽带无源分束。
    来源：AIM Photonics 教程。
    """
    length = 20.0
    out_gap = 1.0
    ports = _make_y_branch_ports(length, out_gap)
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
# 8. 波导交叉 crossing
# ===========================================================================
def make_crossing() -> Device:
    """波导交叉（waveguide crossing）。

    插损 ~0.3dB，串扰 ~-30dB，实现正交波导低损耗低串扰交叉。
    来源：硅光工艺平台比较（iccsz.com）。
    """
    size = 5.0  # 交叉区尺寸
    width = 0.5
    ports = _make_crossing_ports(size, width)
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
