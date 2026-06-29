"""SOI 平台环谐振器器件库。

覆盖硅光 SOI 平台的环谐振器器件真实参数模型：微环谐振器与双环滤波器。
每个器件参数均来自公开文献/工艺手册并附带 ``Source`` 溯源（含 URL），
禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.soi.sources import _SOI_CONSTRAINTS, _SRC_SAMSUNG, _SRC_SIEPIC_EBEAM


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_ring_resonator_ports(radius: float, gap: float, width: float) -> list[Port]:
    """创建微环谐振器的 4 个端口（add-drop 结构）。

    总线波导沿 x 轴，环圆心在 (radius, radius+gap+width)。
    """
    y_top = 2 * (radius + gap + width)
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
        Port(
            name="drop",
            x=2 * radius,
            y=y_top,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="add",
            x=0.0,
            y=y_top,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=width,
        ),
    ]


def _make_double_ring_ports(
    width: float, ring_spacing: float, radius: float, gap: float
) -> list[Port]:
    """创建双环滤波器的 4 个端口。

    Args:
        width: 波导宽度（μm）。
        ring_spacing: 两环间距（μm）。
        radius: 环半径（μm）。
        gap: 耦合间隙（μm）。
    """
    y_top = 2 * (radius + gap + width)
    return [
        Port(
            name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=width
        ),
        Port(
            name="through",
            x=ring_spacing,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="drop",
            x=ring_spacing,
            y=y_top,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=width,
        ),
        Port(
            name="add",
            x=0.0,
            y=y_top,
            direction=Direction.WEST,
            waveguide_type="strip",
            width=width,
        ),
    ]


# ===========================================================================
# 1. 微环谐振器 ring_resonator
# ===========================================================================
def make_ring_resonator() -> Device:
    """微环谐振器（add-drop ring resonator）。

    SiEPIC EBeam PDK half_ring 默认参数：radius=5μm, gap=200nm, width=500nm。

    R05 Bug 修复 v4.0-GAP-P1（第2轮迭代发现）:
    原 gap=50nm 与项目自家 DRC constraint_types.py:136 min_coupling_gap_um=0.1
    冲突，会触发自身 DRC 违例。50nm 虽在 SiEPIC e-beam 工艺下可制造，但项目
    其他 DC（couplers.py:174/192, double_ring_filter:144/164,
    gdsfactory_integration.py:144/158）均统一 200nm。修复为 200nm 与项目标准一致。
    规则: R02 学术诚信 / R05 Bug 必修 / R03 内部一致性
    文献:
    - SiEPIC EBeam PDK half_ring https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg 2015 §6.4 ring resonator
      https://www.cambridge.org/core/books/silicon-photonics-design/
    - 项目 DRC constraint_types.py:136 min_coupling_gap_um=0.1
    - 项目 couplers.py:174 gap_nm=200
    - AIM Photonics 教程 ring resonator
    半径 5-20μm，与总线波导耦合构成谐振滤波/调制单元。
    来源：SiEPIC EBeam PDK half_ring 模型 + AIM Photonics 教程。
    """
    radius = 5.0  # SiEPIC half_ring 默认半径 5μm
    gap = 0.2  # 项目 DRC 标准 200nm（与 couplers.py / gdsfactory_integration.py 一致）
    width = 0.5
    ports = _make_ring_resonator_ports(radius, gap, width)
    ring_top = 2 * (radius + gap + width) + width / 2
    return Device(
        device_id="soi_ring_resonator",
        platform="SOI",
        category="passive",
        name="ring_resonator",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-width / 2, xmax=2 * radius, ymax=ring_top),
        params={
            "radius_um": 5.0,  # SiEPIC 默认半径 5μm
            "gap_nm": 200,  # 项目 DRC 标准 200nm（R05 v4.0-GAP-P1 修复，原 50nm 触发自身 DRC）
            "q_factor": 10000,  # 品质因数
            "fsr_nm": 10.0,  # 自由光谱范围
            "loss_db_cm": 3.0,  # SiEPIC e-beam 波导损耗
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        source=_SRC_SIEPIC_EBEAM,
        constraints=_SOI_CONSTRAINTS,
    )


# ===========================================================================
# 2. 双环滤波器 double_ring_filter
# ===========================================================================
def make_double_ring_filter() -> Device:
    """双环滤波器（double ring filter, DRF）。

    drop 端口插损 <1.0dB，1-dB 带宽 105GHz，用于波长选择滤波。
    来源：三星 300mm 硅光平台 OFC 2026。
    """
    radius = 10.0  # 环半径
    gap = 0.2  # 耦合间隙
    width = 0.5
    ring_spacing = 2 * (radius + gap + width)  # 两环间距
    ports = _make_double_ring_ports(width, ring_spacing, radius, gap)
    return Device(
        device_id="soi_double_ring_filter",
        platform="SOI",
        category="passive",
        name="double_ring_filter",
        ports=ports,
        bbox=BoundingBox(
            xmin=0.0,
            ymin=-width / 2,
            xmax=ring_spacing,
            ymax=2 * (radius + gap + width) + width / 2,
        ),
        params={
            "drop_insertion_loss_db": 1.0,  # drop 插损 <1.0dB
            "bandwidth_1db_ghz": 105.0,  # 1-dB 带宽 105GHz
            "radius_um": 10.0,
            "gap_nm": 200,
            "wavelength_nm": 1310,  # O 波段
        },
        source=_SRC_SAMSUNG,
        constraints={
            "min_bend_radius_um": 2.0,
            "min_spacing_um": 1.0,
            "wavelength_nm": 1310,
        },
    )
