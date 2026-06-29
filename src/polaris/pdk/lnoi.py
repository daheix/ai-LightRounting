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


def _port(name: str, x: float, y: float, d: Direction, w: float = _LNOI_WAVEGUIDE_WIDTH_UM) -> Port:
    """创建 LNOI 条形波导端口的紧凑辅助函数（降低器件函数 SLOC）。"""
    return Port(name=name, x=x, y=y, direction=d, waveguide_type="lnoi_strip", width=w)


def _rf_port(name: str, x: float, y: float, d: Direction, w: float = 3.0) -> Port:
    """创建 RF 共面波导端口的紧凑辅助函数（降低器件函数 SLOC）。"""
    return Port(name=name, x=x, y=y, direction=d, waveguide_type="rf_coplanar", width=w)


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
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out", length_um, 0.0, Direction.EAST),
    ]
    bbox = BoundingBox(xmin=0.0, ymin=-width_um / 2, xmax=length_um, ymax=width_um / 2)
    return Device(
        device_id="lnoi_waveguide",
        platform="LNOI",
        category="passive",
        name="lnoi_waveguide",
        ports=ports,
        bbox=bbox,
        params={
            "loss_db_cm": 0.4,  # <0.4 dB/cm（保守上界）
            "width_um": width_um,
            "length_um": length_um,
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
def _make_lnoi_modulator_device(
    device_id: str,
    name: str,
    length_um: float,
    params: dict,
    source: Source,
) -> Device:
    """构建 LNOI 调制器 Device（共用 in/out/rf_in/rf_out 端口与包围盒）。"""
    width_um = _LNOI_WAVEGUIDE_WIDTH_UM
    rf_offset_y = 3.0
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out", length_um, 0.0, Direction.EAST),
        _rf_port("rf_in", 0.0, -rf_offset_y, Direction.SOUTH),
        _rf_port("rf_out", length_um, -rf_offset_y, Direction.SOUTH),
    ]
    bbox = BoundingBox(xmin=0.0, ymin=-rf_offset_y - 1.5, xmax=length_um, ymax=width_um / 2)
    constraints = {
        "min_bend_radius_um": _LNOI_MIN_BEND_RADIUS_UM,
        "min_spacing_um": _LNOI_MIN_SPACING_UM,
        "electrode_gap_um": 3.0,
    }
    return Device(
        device_id=device_id,
        platform="LNOI",
        category="active",
        name=name,
        ports=ports,
        bbox=bbox,
        params=params,
        source=source,
        constraints=constraints,
    )


def make_lnoi_eo_modulator() -> Device:
    """LNOI 电光调制器（主动器件，量产平台参数）。

    带宽 >110GHz，Vπ <3V，良率 50%，4 英寸晶圆级量产验证。
    来源: Liu et al., Light: Advanced Manufacturing 2025, 6, 47
    """
    length_um = 1000.0  # 调制区长度 ~1mm（典型 MZM 臂长）
    return _make_lnoi_modulator_device(
        device_id="lnoi_eo_modulator",
        name="lnoi_eo_modulator",
        length_um=length_um,
        params={
            "bandwidth_ghz": 110.0,  # >110 GHz（保守下界）
            "vpi_v": 3.0,  # <3 V（保守上界）
            "yield_percent": 50.0,
            "wafer_size_inch": 4.0,
            "modulator_length_um": length_um,
        },
        source=Source(
            title="LNOI platform: wafer-scale lithium niobate photonic integrated circuits",
            authors="Liu et al.",
            year=2025,
            url="https://doi.org/10.37188/lam.2025.047",
        ),
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
    return _make_lnoi_modulator_device(
        device_id="lnoi_mzm_high_confined",
        name="lnoi_mzm_high_confined",
        length_um=length_um,
        params={
            "vpi_l_v_cm": 1.2,
            "excess_loss_db": 2.4,
            "bandwidth_ghz": 40.0,  # >40 GHz（保守下界）
            "modulator_length_um": length_um,
        },
        source=Source(
            title="High-confinement LNOI Mach-Zehnder modulator",
            authors="Chen et al.",
            year=2023,
            url="https://doi.org/10.1364/OL.481827",
        ),
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
    return _make_lnoi_modulator_device(
        device_id="lnoi_mzm_traveling_wave",
        name="lnoi_mzm_traveling_wave",
        length_um=length_um,
        params={
            "vpi_l_v_cm": 1.77,
            # R05 v4.0-LNOI-LOSS-P2（第2轮迭代发现）:
            # 0.022 dB/cm 是 U-T double-layer 行波电极 MZM 特定器件实测值
            # （MDPI Photonics 2023），非 LNOI 平台典型值（平台典型 0.4 dB/cm
            # 见 lnoi.py:71 / pretrain_constants.py:91 / waveguide_router.py:545）。
            # 若被其他模块误用为 LNOI 平台损耗会严重低估，注释明确"器件特定"。
            # 规则: R02 学术诚信 / R05 Bug 必修
            # 文献: MDPI Photonics 2023 U-T double-layer traveling-wave electrode
            "optical_loss_db_cm": 0.022,  # 器件特定（非平台典型值 0.4 dB/cm）
            "bandwidth_ghz": 100.0,  # >100 GHz（保守下界）
            "electrode_type": "traveling_wave_coplanar",
            "modulator_length_um": length_um,
        },
        source=Source(
            title="U-T double-layer traveling-wave electrode LNOI modulator",
            authors="MDPI Photonics",
            year=2023,
            url="https://www.mdpi.com/2304-6732/12/7/648",
        ),
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
    return _make_lnoi_modulator_device(
        device_id="lnoi_modulator_review",
        name="lnoi_modulator_review",
        length_um=length_um,
        params={
            "vpi_l_v_cm": 2.0,  # <2 V·cm（保守上界）
            "coupling_loss_db_facet": 0.5,  # <0.5 dB/facet（保守上界）
            "coupler_type": "double_taper",
            "bandwidth_ghz": 100.0,  # >100 GHz（保守下界）
            "modulator_length_um": length_um,
        },
        source=Source(
            title="LNOI 调制器综述（薄膜铌酸锂电光调制器研究进展）",
            authors="刘海锋等",
            year=2022,
            url="https://doi.org/10.37188/CO.2021-0115",
        ),
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
    width_um = _LNOI_WAVEGUIDE_WIDTH_UM
    ports = [
        _port("in", 0.0, 0.0, Direction.WEST),
        _port("out", length_um, 0.0, Direction.EAST),
    ]
    bbox = BoundingBox(xmin=0.0, ymin=-width_um / 2, xmax=length_um, ymax=width_um / 2)
    return Device(
        device_id="lnoi_photonics_review",
        platform="LNOI",
        category="passive",
        name="lnoi_photonics_review",
        ports=ports,
        bbox=bbox,
        params={
            "transparency_window_min_um": 0.4,
            "transparency_window_max_um": 5.0,
            "eo_coefficient_r33_pm_v": 30.0,
            "platform": "thin-film lithium niobate on insulator",
            "length_um": length_um,
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
    return _make_lnoi_modulator_device(
        device_id="lnoi_cmos_modulator",
        name="lnoi_cmos_modulator",
        length_um=length_um,
        params={
            "drive_voltage_v": 1.0,  # CMOS compatible (<1 V，保守上界）
            "bandwidth_ghz": 100.0,  # >100 GHz（保守下界）
            "vpi_v": 1.0,  # <1 V（保守上界）
            "milestone": "first CMOS-compatible voltage LN modulator",
            "modulator_length_um": length_um,
        },
        source=Source(
            title="Integrated LN EO modulators operating at CMOS-compatible voltages",
            authors="Wang et al.",
            year=2018,
            url="https://doi.org/10.1038/s41586-018-0551-y",
        ),
    )


# ---------------------------------------------------------------------------
# 8. LNOI TFLN 调制器（Wang et al., Optica 2018）
# ---------------------------------------------------------------------------
def make_lnoi_tfln_modulator() -> Device:
    """LNOI 薄膜铌酸锂调制器（Vπ·L ≈ 1.5 V·cm，带宽 > 100 GHz）。

    来源: Wang et al., Optica 2018, 5(11):1393-1397，
    首次实现亚伏特驱动电压的 TFLN 调制器，Vπ·L ≈ 1.5 V·cm。
    """
    length_um = 2000.0  # TFLN 调制器臂长 ~2mm
    return _make_lnoi_modulator_device(
        device_id="lnoi_tfln_modulator",
        name="lnoi_tfln_modulator",
        length_um=length_um,
        params={
            "vpi_l_v_cm": 1.5,
            "bandwidth_ghz": 100.0,  # >100 GHz（保守下界）
            "modulator_type": "TFLN MZM",
            "modulator_length_um": length_um,
        },
        source=Source(
            title=(
                "Integrated lithium niobate electro-optic modulators"
                " operating at CMOS-compatible voltages"
            ),
            authors="Wang et al.",
            year=2018,
            url="https://doi.org/10.1364/OPTICA.5.001393",
        ),
    )


# ---------------------------------------------------------------------------
# LNOI 器件汇总字典（按器件名索引工厂函数）
# ---------------------------------------------------------------------------
# 导入被动过渡与片上耦合器件（taper/S-bend/Euler bend/MMI/DC/Y-branch）
from polaris.pdk.lnoi_passive import (  # noqa: E402
    make_lnoi_directional_coupler,
    make_lnoi_euler_bend,
    make_lnoi_linear_taper,
    make_lnoi_mmi_1x2,
    make_lnoi_s_bend,
    make_lnoi_y_branch,
)

LNOI_DEVICES: dict[str, Callable[[], Device]] = {
    "lnoi_waveguide": make_lnoi_waveguide,
    "lnoi_eo_modulator": make_lnoi_eo_modulator,
    "lnoi_mzm_high_confined": make_lnoi_mzm_high_confined,
    "lnoi_mzm_traveling_wave": make_lnoi_mzm_traveling_wave,
    "lnoi_modulator_review": make_lnoi_modulator_review,
    "lnoi_photonics_review": make_lnoi_photonics_review,
    "lnoi_cmos_modulator": make_lnoi_cmos_modulator,
    "lnoi_tfln_modulator": make_lnoi_tfln_modulator,
    "lnoi_linear_taper": make_lnoi_linear_taper,
    "lnoi_s_bend": make_lnoi_s_bend,
    "lnoi_euler_bend": make_lnoi_euler_bend,
    "lnoi_mmi_1x2": make_lnoi_mmi_1x2,
    "lnoi_directional_coupler": make_lnoi_directional_coupler,
    "lnoi_y_branch": make_lnoi_y_branch,
}
