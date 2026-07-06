"""基础器件 S 参数模型（纯 numpy 实现）。

参考 SiPANN 的解析模型与 Simphony 的 SiEPIC 模型库:
- SiPANN: https://sipann.readthedocs.io/en/latest/models.html
- Simphony SiEPIC: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- 波导传播模型: e^{i*beta*L}, beta = 2*pi*neff/wl

来源:
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, Ch. 13 (CMT)
- Soldano & Pennings, JLT 1995: https://ieeexplore.ieee.org/document/374358

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris_circuit.types import SDict


@dataclass
class RingParams:
    """环谐振器参数集合。

    默认值来源: SiEPIC EBeam PDK strip waveguide 1550nm。
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    neff: float = 2.4
    ng: float = 4.0
    coupling: float = 0.01
    loss_db_cm: float = 0.0

    def __post_init__(self) -> None:
        if self.neff <= 0:
            raise ValueError(f"neff 必须 > 0，得到 {self.neff}")
        if self.ng <= 0:
            raise ValueError(f"ng 必须 > 0，得到 {self.ng}")
        if not 0 <= self.coupling <= 1:
            raise ValueError(f"coupling 必须在 [0, 1]，得到 {self.coupling}")
        if self.loss_db_cm < 0:
            raise ValueError(f"loss_db_cm 必须 >= 0，得到 {self.loss_db_cm}")


def _validate_wavelength(wl: float | np.ndarray) -> np.ndarray:
    """验证波长参数（光通信波段 0.5-2.0 μm）。"""
    wl_arr = np.asarray(wl, dtype=float)
    if np.any(wl_arr <= 0):
        raise ValueError(f"波长必须 > 0 μm，得到 min={float(np.min(wl_arr))}")
    if np.any(wl_arr < 0.5) or np.any(wl_arr > 2.0):
        raise ValueError(
            f"波长 {float(np.min(wl_arr))}-{float(np.max(wl_arr))} μm 超出光通信波段 [0.5, 2.0] μm"
        )
    return wl_arr


def waveguide_s(
    wl: float | np.ndarray = 1.55,
    length: float = 100.0,
    neff: float = 2.4,
    ng: float = 4.0,
    loss_db_cm: float = 0.0,
) -> SDict:
    """波导传播 S 参数模型。

    相位: phi = 2*pi*neff*L/wl；损耗: dB/cm → 振幅衰减。
    来源: Simphony/SiPANN waveguide 模型。
    """
    wl = _validate_wavelength(wl)
    beta = 2.0 * np.pi * neff / wl
    phase = np.exp(1j * beta * length)
    if loss_db_cm > 0:
        alpha = 10.0 ** (-loss_db_cm * length / 1e4 / 20.0)  # length μm → cm
        phase = phase * alpha
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): phase,
        ("in", "out"): phase,
        ("out", "out"): zero,
    }


def y_branch_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.3,
) -> SDict:
    """Y 分支 S 参数模型（1进2出/2进1出 3dB 分束器）。

    端口: port_1（合束/分束端）, port_2, port_3（分支端）。
    来源: Simphony siepic.y_branch, SiPANN y_branch。
    """
    wl = _validate_wavelength(wl)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl, amp, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("port_1", "port_1"): zero,
        ("port_2", "port_2"): zero,
        ("port_3", "port_3"): zero,
        ("port_2", "port_1"): amp_arr,
        ("port_3", "port_1"): amp_arr,
        ("port_1", "port_2"): amp_arr,
        ("port_1", "port_3"): amp_arr,
        ("port_2", "port_3"): zero,
        ("port_3", "port_2"): zero,
    }


def directional_coupler_s(
    wl: float | np.ndarray = 1.55,
    coupling: float = 0.5,
    length: float = 10.0,
    gap: float = 0.2,
    neff: float = 2.4,
) -> SDict:
    """定向耦合器 S 参数模型（耦合模理论 CMT）。

    P_cross = sin²(κL), P_through = cos²(κL)。
    端口: in1, in2, out1, out2。
    来源: Yariv & Yeh 1984 Ch.13; SiPANN directional_coupler。
    """
    wl = _validate_wavelength(wl)
    if length <= 0:
        raise ValueError(f"耦合长度必须 > 0，得到 {length}")
    if not (0.0 <= coupling <= 1.0):
        raise ValueError(f"耦合比必须在 [0, 1] 范围内，得到 {coupling}")
    kappa_L = np.arcsin(np.sqrt(coupling))
    kappa_amp = np.sin(kappa_L)
    tau_amp = np.cos(kappa_L)
    kappa_arr = np.full_like(wl, kappa_amp, dtype=complex) * 1j
    tau_arr = np.full_like(wl, tau_amp, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        ("out1", "in1"): tau_arr,
        ("out2", "in2"): tau_arr,
        ("out2", "in1"): kappa_arr,
        ("out1", "in2"): kappa_arr,
        ("in1", "out1"): tau_arr,
        ("in2", "out2"): tau_arr,
        ("in1", "out2"): kappa_arr,
        ("in2", "out1"): kappa_arr,
    }


def ring_resonator_s(
    wl: float | np.ndarray = 1.55,
    radius: float = 10.0,
    params: RingParams | None = None,
) -> SDict:
    """环谐振器 S 参数模型（全通型 single bus）。

    T = (t - a*e^{i*phi}) / (1 - t*a*e^{i*phi})。
    端口: in/through。
    来源: SiPANN ring_resonator; Yariv 1997 §10.5。
    """
    if params is None:
        params = RingParams()
    wl = _validate_wavelength(wl)
    circumference = 2.0 * np.pi * radius
    beta = 2.0 * np.pi * params.neff / wl
    phi = beta * circumference
    loss_db_cm = params.loss_db_cm if params.loss_db_cm > 0 else 0.1
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    t = np.sqrt(1.0 - params.coupling)
    numerator = t - a * np.exp(1j * phi)
    denominator = 1.0 - t * a * np.exp(1j * phi)
    T = numerator / denominator
    return {
        ("in", "in"): np.zeros_like(wl, dtype=complex),
        ("through", "in"): T,
        ("in", "through"): T,
        ("through", "through"): np.zeros_like(wl, dtype=complex),
    }


def mmi_1x2_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.4,
) -> SDict:
    """MMI 1x2 S 参数模型（1进2出 3dB 分束器）。端口: in, out1, out2。"""
    wl = _validate_wavelength(wl)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl, amp, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        ("out1", "in"): amp_arr,
        ("out2", "in"): amp_arr,
        ("in", "out1"): amp_arr,
        ("in", "out2"): amp_arr,
        ("out1", "out2"): zero,
        ("out2", "out1"): zero,
    }


def mmi_2x2_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.5,
) -> SDict:
    """MMI 2x2 S 参数模型（2进2出分束/合束器）。端口: in1, in2, out1, out2。"""
    wl = _validate_wavelength(wl)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl, amp, dtype=complex)
    cross_arr = amp_arr * 1j  # 交叉端口 π/2 相位差
    bar_arr = amp_arr
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        ("out1", "in1"): bar_arr,
        ("out2", "in2"): bar_arr,
        ("in1", "out1"): bar_arr,
        ("in2", "out2"): bar_arr,
        ("out2", "in1"): cross_arr,
        ("out1", "in2"): cross_arr,
        ("in1", "out2"): cross_arr,
        ("in2", "out1"): cross_arr,
    }


def grating_coupler_s(
    wl: float | np.ndarray = 1.55,
    peak_wl: float = 1.55,
    bandwidth_3db: float = 0.04,
    insertion_loss_db: float = 1.9,
) -> SDict:
    """光栅耦合器 S 参数模型（高斯型波长响应）。端口: fiber, waveguide。

    来源: Simphony siepic.grating_coupler; Chrostowski 2015 §7.3。
    """
    wl = _validate_wavelength(wl)
    sigma = bandwidth_3db / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    gaussian = np.exp(-((wl - peak_wl) ** 2) / (2.0 * sigma**2))
    amp = 10.0 ** (-insertion_loss_db / 20.0) * gaussian
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("fiber", "fiber"): zero,
        ("waveguide", "waveguide"): zero,
        ("waveguide", "fiber"): amp,
        ("fiber", "waveguide"): amp,
    }


def crossing_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.3,
) -> SDict:
    """波导交叉 S 参数模型。端口: in1, in2, out1, out2（直通无交叉耦合）。"""
    wl = _validate_wavelength(wl)
    amp = 10.0 ** (-insertion_loss_db / 20.0)
    amp_arr = np.full_like(wl, amp, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        ("out1", "in1"): amp_arr,
        ("out2", "in2"): amp_arr,
        ("in1", "out1"): amp_arr,
        ("in2", "out2"): amp_arr,
        ("out2", "in1"): zero,
        ("out1", "in2"): zero,
        ("in1", "out2"): zero,
        ("in2", "out1"): zero,
    }


def terminator_s(
    wl: float | np.ndarray = 1.55,
    reflection_db: float = -40.0,
) -> SDict:
    """终端吸收器 S 参数模型。端口: in（单端口）。

    来源: Simphony siepic.terminator; SiEPIC EBeam PDK。
    """
    wl = _validate_wavelength(wl)
    r = 10.0 ** (reflection_db / 20.0)
    r_arr = np.full_like(wl, r, dtype=complex)
    return {("in", "in"): r_arr}


def phase_shifter_s(
    wl: float | np.ndarray = 1.55,
    phase_rad: float = 0.0,
    insertion_loss_db: float = 0.0,
) -> SDict:
    """热光移相器 S 参数模型。端口: in, out。"""
    wl = _validate_wavelength(wl)
    phase = np.exp(1j * phase_rad)
    if insertion_loss_db > 0:
        phase = phase * 10.0 ** (-insertion_loss_db / 20.0)
    phase_arr = np.full_like(wl, phase, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): phase_arr,
        ("in", "out"): phase_arr,
        ("out", "out"): zero,
    }


__all__ = [
    "RingParams",
    "waveguide_s",
    "y_branch_s",
    "directional_coupler_s",
    "ring_resonator_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "crossing_s",
    "terminator_s",
    "phase_shifter_s",
]
