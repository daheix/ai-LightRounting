"""薄膜铌酸锂 LNOI 平台器件库（Task 6）。

本模块提供 LNOI（Lithium Niobate on Insulator，薄膜铌酸锂）平台所有器件的
``Device`` 工厂函数。每个器件的电光参数均来自公开文献（已在 spec.md 核实），
并附带 ``Source`` 对象（含标题、作者、年份、URL），禁止假数据。

LNOI 平台特点（来源: Zhu et al., Adv. Opt. Photonics 2021）：
- LN 透明窗口宽（0.4-5μm），覆盖可见到中红外
- 高电光系数（r33 ~30 pm/V），优于硅基等离子色散效应
- 高约束波导损耗低（<0.4 dB/cm），支持高速（>100GHz）低 Vπ 调制
- 弯曲半径典型 50-100μm（介于 SOI 高约束与 SiN 低约束之间）

来源汇总（见 spec.md 第 244-250 行）：
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47 — https://doi.org/10.37188/lam.2025.047
- Chen et al., Optics Letters 2023, 48(7):1602-1605 — https://doi.org/10.1364/OL.481827
- MDPI Photonics 2023, 12(7):648 — https://www.mdpi.com/2304-6732/12/7/648
- 刘海锋等，中国光学 2022, 15(1):1-13 — https://doi.org/10.37188/CO.2021-0115
- Zhu et al., Adv. Opt. Photonics 2021, 13:242-352 — https://doi.org/10.1364/AOP.411024
- Wang et al., Nature 2018, 562:101-104 — https://doi.org/10.1038/s41586-018-0551-y
"""

from __future__ import annotations

from collections.abc import Callable

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source

# LNOI 平台通用约束（来源: spec.md，LNOI 弯曲半径 50-100μm）
# 高约束 TFLN 波导可实现 ~50μm 弯曲，低约束结构需 ~100μm
_LNOI_MIN_BEND_RADIUS_UM = 80.0  # 取 50-100μm 区间代表值
_LNOI_MIN_SPACING_UM = 2.5  # LNOI 波导间距典型 2-3μm
_LNOI_WAVEGUIDE_WIDTH_UM = 1.5  # TFLN 条形波导典型宽度 1-2μm
_LNOI_RF_OFFSET_Y = 3.0  # RF 电极相对波导的 y 偏移（μm），电极间距 ~3μm


def _lnoi_mzm_optical_ports(length_um: float) -> list[Port]:
    """构建 LNOI MZM 光学端口（in/out，y=0，lnoi_strip 波导）。

    Args:
        length_um: 调制区长度（μm），决定 out 端口 x 坐标。

    Returns:
        含 in/out 两光学端口的列表。
    """
    width_um = _LNOI_WAVEGUIDE_WIDTH_UM
    return [
        Port(
            name="in",
            x=0.0,
            y=0.0,
            direction=Direction.WEST,
            waveguide_type="lnoi_strip",
            width=width_um,
        ),
        Port(
            name="out",
            x=length_um,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type="lnoi_strip",
            width=width_um,
        ),
    ]


def _lnoi_mzm_rf_ports(length_um: float) -> list[Port]:
    """构建 LNOI MZM RF 端口（rf_in/rf_out，SOUTH，rf_coplanar）。

    Args:
        length_um: 调制区长度（μm），决定 rf_out 端口 x 坐标。

    Returns:
        含 rf_in/rf_out 两 RF 共面端口的列表。
    """
    return [
        Port(
            name="rf_in",
            x=0.0,
            y=-_LNOI_RF_OFFSET_Y,
            direction=Direction.SOUTH,
            waveguide_type="rf_coplanar",
            width=3.0,
        ),
        Port(
            name="rf_out",
            x=length_um,
            y=-_LNOI_RF_OFFSET_Y,
            direction=Direction.SOUTH,
            waveguide_type="rf_coplanar",
            width=3.0,
        ),
    ]


def _lnoi_mzm_ports(length_um: float) -> list[Port]:
    """构建 LNOI MZM 调制器标准端口（in/out/rf_in/rf_out）。

    Args:
        length_um: 调制区长度（μm），决定 out/rf_out 端口 x 坐标。

    Returns:
        含 in/out（光）与 rf_in/rf_out（RF 共面）四端口的列表。
    """
    return _lnoi_mzm_optical_ports(length_um) + _lnoi_mzm_rf_ports(length_um)


def _lnoi_mzm_bbox(length_um: float) -> BoundingBox:
    """构建 LNOI MZM 调制器包围盒。"""
    width_um = _LNOI_WAVEGUIDE_WIDTH_UM
    return BoundingBox(xmin=0.0, ymin=-_LNOI_RF_OFFSET_Y - 1.5, xmax=length_um, ymax=width_um / 2)


def _lnoi_mzm_constraints() -> dict[str, float]:
    """构建 LNOI MZM 调制器工艺约束（弯曲半径/间距/电极间距）。"""
    return {
        "min_bend_radius_um": _LNOI_MIN_BEND_RADIUS_UM,
        "min_spacing_um": _LNOI_MIN_SPACING_UM,
        "electrode_gap_um": 3.0,
    }


# ---------------------------------------------------------------------------
# 1. LNOI 波导
# ---------------------------------------------------------------------------
def make_lnoi_waveguide() -> Device:
    """LNOI 薄膜铌酸锂条形波导（被动器件）。

    量产 LNOI 平台波导损耗 <0.4 dB/cm，4 英寸晶圆级验证。
    来源: Liu et al., Light: Advanced Manufacturing 2025, 6, 47
    """
    length_um = 10.0  # 单位波导段长度（μm）
    width_um = _LNOI_WAVEGUIDE_WIDTH_UM
    return Device(
        device_id="lnoi_waveguide",
        platform="LNOI",
        category="passive",
        name="lnoi_waveguide",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "loss_db_cm": "<0.4 dB/cm",
            "width_um": f"{width_um} μm",
            "length_um": f"{length_um} μm",
            "waveguide_type": "lnoi_strip",
        },
        source=Source(
            title="LNOI platform: wafer-scale lithium niobate photonic integrated circuits",
            authors="Liu et al.",
            year=2025,
            url="https://doi.org/10.37188/lam.2025.047",
        ),
        constraints={
            "min_bend_radius_um": _LNOI_MIN_BEND_RADIUS_UM,
            "min_spacing_um": _LNOI_MIN_SPACING_UM,
        },
    )


# ---------------------------------------------------------------------------
# 2. LNOI 电光调制器（量产平台）
# ---------------------------------------------------------------------------
def make_lnoi_eo_modulator() -> Device:
    """LNOI 电光调制器（主动器件，量产平台参数）。

    带宽 >110GHz，Vπ <3V，良率 50%，4 英寸晶圆级量产验证。
    来源: Liu et al., Light: Advanced Manufacturing 2025, 6, 47
    """
    length_um = 1000.0  # 调制区长度 ~1mm（典型 MZM 臂长）
    return Device(
        device_id="lnoi_eo_modulator",
        platform="LNOI",
        category="active",
        name="lnoi_eo_modulator",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "bandwidth_ghz": ">110 GHz",
            "vpi_v": "<3 V",
            "yield": "50%",
            "wafer_size": "4 inch",
            "modulator_length_um": f"{length_um} μm",
        },
        source=Source(
            title="LNOI platform: wafer-scale lithium niobate photonic integrated circuits",
            authors="Liu et al.",
            year=2025,
            url="https://doi.org/10.37188/lam.2025.047",
        ),
        constraints=_lnoi_mzm_constraints(),
    )


# ---------------------------------------------------------------------------
# 3. LNOI MZM 高约束
# ---------------------------------------------------------------------------
def make_lnoi_mzm_high_confined() -> Device:
    """LNOI 高约束 Mach-Zehnder 调制器（主动器件）。

    VπL 1.2 V·cm，过剩损耗 ~2.4dB，带宽 >40GHz。
    来源: Chen et al., Optics Letters 2023, 48(7):1602-1605
    """
    length_um = 2000.0  # 高约束 MZM 调制臂长 ~2mm
    return Device(
        device_id="lnoi_mzm_high_confined",
        platform="LNOI",
        category="active",
        name="lnoi_mzm_high_confined",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "vpi_l_v_cm": "1.2 V·cm",
            "excess_loss_db": "~2.4 dB",
            "bandwidth_ghz": ">40 GHz",
            "modulator_length_um": f"{length_um} μm",
        },
        source=Source(
            title="High-confinement LNOI Mach-Zehnder modulator",
            authors="Chen et al.",
            year=2023,
            url="https://doi.org/10.1364/OL.481827",
        ),
        constraints=_lnoi_mzm_constraints(),
    )


# ---------------------------------------------------------------------------
# 4. LNOI 行波电极调制器
# ---------------------------------------------------------------------------
def make_lnoi_mzm_traveling_wave() -> Device:
    """LNOI 行波电极 Mach-Zehnder 调制器（主动器件）。

    VπL 1.77 V·cm，光损耗 0.022 dB/cm，带宽 >100GHz。
    来源: MDPI Photonics 2023, 12(7):648
    """
    length_um = 3000.0  # 行波电极 MZM 臂长 ~3mm
    return Device(
        device_id="lnoi_mzm_traveling_wave",
        platform="LNOI",
        category="active",
        name="lnoi_mzm_traveling_wave",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "vpi_l_v_cm": "1.77 V·cm",
            "optical_loss_db_cm": "0.022 dB/cm",
            "bandwidth_ghz": ">100 GHz",
            "electrode_type": "traveling_wave_coplanar",
            "modulator_length_um": f"{length_um} μm",
        },
        source=Source(
            title="U-T double-layer traveling-wave electrode LNOI modulator",
            authors="MDPI Photonics",
            year=2023,
            url="https://www.mdpi.com/2304-6732/12/7/648",
        ),
        constraints=_lnoi_mzm_constraints(),
    )


# ---------------------------------------------------------------------------
# 5. LNOI 调制器综述参数
# ---------------------------------------------------------------------------
def make_lnoi_modulator_review() -> Device:
    """LNOI 调制器综述参数器件（主动器件，综合文献指标）。

    VπL<2 V·cm，双锥形耦合 <0.5dB/facet，带宽 >100GHz。
    来源: 刘海锋等，中国光学 2022, 15(1):1-13
    """
    length_um = 1500.0  # 综述典型 MZM 臂长 ~1.5mm
    return Device(
        device_id="lnoi_modulator_review",
        platform="LNOI",
        category="active",
        name="lnoi_modulator_review",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "vpi_l_v_cm": "<2 V·cm",
            "coupling_loss_db_facet": "<0.5 dB/facet",
            "coupler_type": "double_taper",
            "bandwidth_ghz": ">100 GHz",
            "modulator_length_um": f"{length_um} μm",
        },
        source=Source(
            title="LNOI 调制器综述（薄膜铌酸锂电光调制器研究进展）",
            authors="刘海锋等",
            year=2022,
            url="https://doi.org/10.37188/CO.2021-0115",
        ),
        constraints=_lnoi_mzm_constraints(),
    )


# ---------------------------------------------------------------------------
# 6. LNOI 集成光子学综述（材料/平台参考器件）
# ---------------------------------------------------------------------------
def make_lnoi_photonics_review() -> Device:
    """LNOI 集成光子学综述参考器件（被动，材料平台指标）。

    LN 透明窗口 0.4-5μm，高电光系数（r33 ~30 pm/V）。
    来源: Zhu et al., Adv. Opt. Photonics 2021, 13:242-352
    """
    length_um = 10.0  # 参考波导段
    return Device(
        device_id="lnoi_photonics_review",
        platform="LNOI",
        category="passive",
        name="lnoi_photonics_review",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "transparency_window_um": "0.4-5 μm",
            "eo_coefficient_r33": "~30 pm/V",
            "platform": "thin-film lithium niobate on insulator",
            "length_um": f"{length_um} μm",
        },
        source=Source(
            title="Thin-film lithium niobate integrated photonics (TFLN review)",
            authors="Zhu et al.",
            year=2021,
            url="https://doi.org/10.1364/AOP.411024",
        ),
        constraints={
            "min_bend_radius_um": _LNOI_MIN_BEND_RADIUS_UM,
            "min_spacing_um": _LNOI_MIN_SPACING_UM,
        },
    )


# ---------------------------------------------------------------------------
# 7. LNOI CMOS 兼容调制器
# ---------------------------------------------------------------------------
def make_lnoi_cmos_modulator() -> Device:
    """LNOI CMOS 兼容电压调制器（主动器件，里程碑工作）。

    Nature 2018 首篇 CMOS 兼容电压（<1V）LN 调制器，开创 LNOI 高速调制方向。
    来源: Wang et al., Nature 2018, 562:101-104
    """
    length_um = 2000.0  # CMOS 兼容 MZM 臂长 ~2mm
    return Device(
        device_id="lnoi_cmos_modulator",
        platform="LNOI",
        category="active",
        name="lnoi_cmos_modulator",
        ports=_lnoi_mzm_ports(length_um),
        bbox=_lnoi_mzm_bbox(length_um),
        params={
            "drive_voltage_v": "CMOS compatible (<1 V)",
            "bandwidth_ghz": ">100 GHz",
            "vpi_v": "<1 V",
            "milestone": "first CMOS-compatible voltage LN modulator",
            "modulator_length_um": f"{length_um} μm",
        },
        source=Source(
            title="Integrated LN EO modulators operating at CMOS-compatible voltages",
            authors="Wang et al.",
            year=2018,
            url="https://doi.org/10.1038/s41586-018-0551-y",
        ),
        constraints=_lnoi_mzm_constraints(),
    )


# ---------------------------------------------------------------------------
# LNOI 器件汇总字典（按器件名索引工厂函数）
# ---------------------------------------------------------------------------
LNOI_DEVICES: dict[str, Callable[[], Device]] = {
    "lnoi_waveguide": make_lnoi_waveguide,
    "lnoi_eo_modulator": make_lnoi_eo_modulator,
    "lnoi_mzm_high_confined": make_lnoi_mzm_high_confined,
    "lnoi_mzm_traveling_wave": make_lnoi_mzm_traveling_wave,
    "lnoi_modulator_review": make_lnoi_modulator_review,
    "lnoi_photonics_review": make_lnoi_photonics_review,
    "lnoi_cmos_modulator": make_lnoi_cmos_modulator,
}
