"""扩展器件 S 参数模型库（R01 步骤 7：扩展到 20+ 器件模型）。

包含 12 个新器件模型，对齐 sax 模型库：
- taper: 锥形转换器
- modulator: MZI 调制器
- detector: 光电探测器
- splitter: 理想 1x2 分束器
- combiner: 2x1 合波器
- attenuator: 光衰减器
- circulator: 三端口环行器
- isolator: 光隔离器
- mirror: 理想反射镜
- reflector: 部分反射器
- unitary: 酉矩阵器件
- bend: 弯曲波导

所有模型基于真实物理公式，参数来自 SOI 220nm 平台典型值。

来源:
- SAX 模型库: https://flaport.github.io/sax/models/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski, "Silicon Photonics Design", Cambridge 2015
- Yariv, "Optical Electronics in Modern Communications", Oxford 1997
"""

from __future__ import annotations

import numpy as np

from polaris.sim.models import validate_wavelength
from polaris.sim.types import SDict


def taper_s(
    wl: float | np.ndarray = 1.55,
    length: float = 10.0,
    insertion_loss_db: float = 0.1,
) -> SDict:
    """锥形转换器 S 参数模型。

    波导宽度渐变转换，理想情况下仅引入插损，无反射。

    端口: in, out

    默认值来源:
    - insertion_loss_db=0.1: SiEPIC EBeam PDK taper 1550nm 典型插损 0.1dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。

    来源: Simphony siepic.taper
    """
    wl_arr = validate_wavelength(wl)
    if length < 0:
        msg = f"锥形长度必须 >= 0，得到 {length}"
        raise ValueError(msg)
    amp = 10.0 ** (-insertion_loss_db / 20.0)
    amp_arr = np.full_like(wl_arr, amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): amp_arr,
        ("in", "out"): amp_arr,
        ("out", "out"): zero,
    }


def modulator_s(
    wl: float | np.ndarray = 1.55,
    phase_rad: float = 0.0,
    insertion_loss_db: float = 0.5,
) -> SDict:
    """MZI 调制器 S 参数模型。

    基于 MZI 原理，通过相位差实现强度调制：
    S = exp(-α/2) * exp(j*φ)

    端口: in, out

    默认值来源:
    - insertion_loss_db=0.5: SiEPIC EBeam PDK modulator 典型插损 0.5dB
      (Chrostowski 2015 §8.4)。

    来源: Chrostowski 2015 §8.4 MZI 调制器
    """
    wl_arr = validate_wavelength(wl)
    amp = 10.0 ** (-insertion_loss_db / 20.0)
    phase = amp * np.exp(1j * phase_rad)
    phase_arr = np.full_like(wl_arr, phase, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): phase_arr,
        ("in", "out"): phase_arr,
        ("out", "out"): zero,
    }


def detector_s(
    wl: float | np.ndarray = 1.55,
    responsivity: float = 1.0,
) -> SDict:
    """光电探测器 S 参数模型。

    探测器吸收所有入射光，无反射。responsivity 用于光电转换，
    S 参数仅描述光学行为（全吸收）。

    端口: in（单端口）

    默认值来源:
    - responsivity=1.0 A/W: SiEPIC EBeam PDK detector 1550nm 典型响应度
      (Chrostowski 2015 §9.2)。

    来源: Chrostowski 2015 §9.2 光电探测器
    """
    wl_arr = validate_wavelength(wl)
    if responsivity < 0:
        msg = f"响应度必须 >= 0，得到 {responsivity}"
        raise ValueError(msg)
    # 探测器吸收所有光，S11=0（无反射）
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {("in", "in"): zero}


def splitter_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.0,
) -> SDict:
    """理想 1x2 分束器 S 参数模型。

    理想 3dB 分束器，每个输出端口获得 50% 功率。

    端口: in, out1, out2

    来源: SAX splitter_ideal, Simphony siepic.y_branch
    """
    wl_arr = validate_wavelength(wl)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl_arr, amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
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


def combiner_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.0,
) -> SDict:
    """2x1 合波器 S 参数模型（splitter 的逆向）。

    端口: in1, in2, out

    来源: SAX combiner, Simphony siepic.y_branch（反向使用）
    """
    wl_arr = validate_wavelength(wl)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl_arr, amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out", "out"): zero,
        ("out", "in1"): amp_arr,
        ("out", "in2"): amp_arr,
        ("in1", "out"): amp_arr,
        ("in2", "out"): amp_arr,
        ("in1", "in2"): zero,
        ("in2", "in1"): zero,
    }


def attenuator_s(
    wl: float | np.ndarray = 1.55,
    attenuation_db: float = 3.0,
) -> SDict:
    """光衰减器 S 参数模型。

    端口: in, out

    默认值来源:
    - attenuation_db=3.0: SAX attenuator 默认值
      (https://flaport.github.io/sax/models/)。

    来源: SAX models.attenuator
    """
    wl_arr = validate_wavelength(wl)
    if attenuation_db < 0:
        msg = f"衰减量必须 >= 0，得到 {attenuation_db}"
        raise ValueError(msg)
    amp = 10.0 ** (-attenuation_db / 20.0)
    amp_arr = np.full_like(wl_arr, amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): amp_arr,
        ("in", "out"): amp_arr,
        ("out", "out"): zero,
    }


def circulator_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.5,
) -> SDict:
    """三端口光环行器 S 参数模型。

    光按 1→2→3→1 方向传输，反向隔离。

    端口: p1, p2, p3

    来源: SAX models.circulator, 标准微波网络理论
    """
    wl_arr = validate_wavelength(wl)
    amp = 10.0 ** (-insertion_loss_db / 20.0)
    amp_arr = np.full_like(wl_arr, amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("p1", "p1"): zero,
        ("p2", "p2"): zero,
        ("p3", "p3"): zero,
        # 1→2, 2→3, 3→1
        ("p2", "p1"): amp_arr,
        ("p3", "p2"): amp_arr,
        ("p1", "p3"): amp_arr,
        # 反向隔离
        ("p1", "p2"): zero,
        ("p2", "p3"): zero,
        ("p3", "p1"): zero,
    }


def isolator_s(
    wl: float | np.ndarray = 1.55,
    insertion_loss_db: float = 0.5,
    isolation_db: float = 40.0,
) -> SDict:
    """光隔离器 S 参数模型。

    正向传输低损耗，反向高隔离。

    端口: in, out

    默认值来源:
    - isolation_db=40.0: 典型光隔离器反向隔离度 40dB
      (Yariv 1997 §11.4)。

    来源: SAX models.isolator, Yariv 1997 §11.4
    """
    wl_arr = validate_wavelength(wl)
    fwd_amp = 10.0 ** (-insertion_loss_db / 20.0)
    rev_amp = 10.0 ** (-isolation_db / 20.0)
    fwd_arr = np.full_like(wl_arr, fwd_amp, dtype=complex)
    rev_arr = np.full_like(wl_arr, rev_amp, dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "out"): zero,
        ("out", "in"): fwd_arr,  # 正向
        ("in", "out"): rev_arr,  # 反向（隔离）
    }


def mirror_s(
    wl: float | np.ndarray = 1.55,
    reflectivity: float = 1.0,
) -> SDict:
    """理想反射镜 S 参数模型。

    端口: in（单端口，全反射）

    默认值来源:
    - reflectivity=1.0: 理想全反射镜
      (Yariv 1997 §4.5)。

    来源: SAX models.mirror, Yariv 1997 §4.5
    """
    wl_arr = validate_wavelength(wl)
    if not 0 <= reflectivity <= 1:
        msg = f"反射率必须在 [0, 1]，得到 {reflectivity}"
        raise ValueError(msg)
    r_arr = np.full_like(wl_arr, reflectivity, dtype=complex)
    return {("in", "in"): r_arr}


def reflector_s(
    wl: float | np.ndarray = 1.55,
    reflectivity: float = 0.5,
) -> SDict:
    """部分反射器 S 参数模型。

    端口: in, out（透射 = 1 - 反射）

    来源: SAX models.reflector
    """
    wl_arr = validate_wavelength(wl)
    if not 0 <= reflectivity <= 1:
        msg = f"反射率必须在 [0, 1]，得到 {reflectivity}"
        raise ValueError(msg)
    r = np.sqrt(reflectivity)
    t = np.sqrt(1.0 - reflectivity)
    r_arr = np.full_like(wl_arr, r, dtype=complex)
    t_arr = np.full_like(wl_arr, t, dtype=complex)
    return {
        ("in", "in"): r_arr,
        ("out", "out"): r_arr,
        ("out", "in"): t_arr,
        ("in", "out"): t_arr,
    }


def unitary_s(
    wl: float | np.ndarray = 1.55,
    theta: float = 0.0,
    phi: float = 0.0,
) -> SDict:
    """酉矩阵器件 S 参数模型（2x2 酉变换）。

    U = [[cos(θ), exp(jφ)·sin(θ)], [-exp(-jφ)·sin(θ), cos(θ)]]

    端口: in1, in2, out1, out2

    来源: SAX models.unitary, 量子光学酉变换
    """
    wl_arr = validate_wavelength(wl)
    c = np.cos(theta)
    s = np.sin(theta)
    phase = np.exp(1j * phi)
    c_arr = np.full_like(wl_arr, c, dtype=complex)
    s_arr = np.full_like(wl_arr, s * phase, dtype=complex)
    s_neg = np.full_like(wl_arr, -s * np.conj(phase), dtype=complex)
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        ("out1", "in1"): c_arr,
        ("out2", "in2"): c_arr,
        ("out2", "in1"): s_arr,
        ("out1", "in2"): s_neg,
        ("in1", "out1"): c_arr,
        ("in2", "out2"): c_arr,
        ("in1", "out2"): s_arr,
        ("in2", "out1"): s_neg,
    }


def bend_s(
    wl: float | np.ndarray = 1.55,
    radius: float = 10.0,
    angle_deg: float = 90.0,
    neff: float = 2.4,
    loss_db_cm: float = 0.5,
) -> SDict:
    """弯曲波导 S 参数模型。

    弯曲波导引入相位累积和弯曲损耗。

    端口: in, out

    默认值来源:
    - radius=10μm: SiEPIC EBeam PDK 最小弯曲半径 10μm
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - loss_db_cm=0.5: 弯曲波导损耗（含辐射损耗）典型值
      (Chrostowski 2015 §3.4)。

    来源: SAX models.bend, Chrostowski 2015 §3.4
    """
    wl_arr = validate_wavelength(wl)
    if radius <= 0:
        msg = f"弯曲半径必须 > 0，得到 {radius}"
        raise ValueError(msg)
    if angle_deg < 0:
        msg = f"弯曲角度必须 >= 0，得到 {angle_deg}"
        raise ValueError(msg)
    # 弯曲弧长
    angle_rad = np.radians(angle_deg)
    arc_length = radius * angle_rad
    # 相位累积
    beta = 2.0 * np.pi * neff / wl_arr
    phase = np.exp(1j * beta * arc_length)
    # 弯曲损耗
    if loss_db_cm > 0:
        alpha = 10.0 ** (-loss_db_cm * arc_length / 1e4 / 20.0)
        phase = phase * alpha
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("out", "in"): phase,
        ("in", "out"): phase,
        ("out", "out"): zero,
    }
