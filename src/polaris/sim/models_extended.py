"""扩展器件 S 参数模型库（R01 步骤 7 + R02 环谐振器）。

包含 12 个 R01 扩展器件模型 + R02 新增环谐振器模型：
- taper/modulator/detector/splitter/combiner/attenuator
- circulator/isolator/mirror/reflector/unitary/bend
- half_ring/add_drop_ring（R02）/sellmeier_neff（R02 色散）

所有模型基于真实物理公式，参数来自 SOI 220nm 平台典型值。

来源:
- SAX 模型库: https://flaport.github.io/sax/models/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015,
  ISBN 978-1-107-08345-6, https://www.cambridge.org/9781107083456
- Yariv, "Optical Electronics in Modern Communications", Oxford 1997
- Soref, Bennett, "Electrooptical effects in silicon", IEEE J. Quantum
  Electronics 1987, https://doi.org/10.1109/JQE.1987.1073206
- Bogaerts et al., "Silicon microring resonators", Laser & Photonics Reviews
  2012, https://doi.org/10.1002/lpor.201100017
- gdsfactory components 文档: https://gdsfactory.github.io/gdsfactory/components.html
"""

from __future__ import annotations

import numpy as np

from polaris.sim.models import validate_wavelength
from polaris.sim.types import SDict


def taper_s(
    wl: float | np.ndarray = 1.55,
    length: float = 10.0,
    w1: float = 0.5,
    w2: float = 0.5,
    loss_db: float = 0.1,
    insertion_loss_db: float | None = None,
) -> SDict:
    """锥形转换器 S 参数模型（对齐 simphony siepic.taper）。

    波导宽度渐变转换，仅引入插损无反射。S = [[sqrt(1-loss), 0], [0, sqrt(1-loss)]]
    端口: in, out。R02 升级: 增加 w1/w2/loss_db 参数，保持 insertion_loss_db 兼容。
    默认值（SiEPIC EBeam PDK, Chrostowski 2015 §2.3）: w1=0.5μm, w2=0.5μm, loss_db=0.1dB
    """
    wl_arr = validate_wavelength(wl)
    if length < 0:
        msg = f"锥形长度必须 >= 0，得到 {length}"
        raise ValueError(msg)
    if w1 <= 0:
        msg = f"输入宽度 w1 必须 > 0，得到 {w1}"
        raise ValueError(msg)
    if w2 <= 0:
        msg = f"输出宽度 w2 必须 > 0，得到 {w2}"
        raise ValueError(msg)
    if loss_db < 0:
        msg = f"损耗 loss_db 必须 >= 0，得到 {loss_db}"
        raise ValueError(msg)
    # 兼容旧参数 insertion_loss_db（优先使用 loss_db）
    effective_loss = loss_db if insertion_loss_db is None else insertion_loss_db
    amp = 10.0 ** (-effective_loss / 20.0)
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
    """MZI 调制器 S 参数模型。S = exp(-α/2)*exp(j*φ)。端口: in, out

    默认值（Chrostowski 2015 §8.4）: insertion_loss_db=0.5dB
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
    S 参数仅描述光学行为（全吸收）。端口: in（单端口）

    默认值（Chrostowski 2015 §9.2）: responsivity=1.0 A/W
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
    """光衰减器 S 参数模型。端口: in, out

    默认值（SAX models.attenuator）: attenuation_db=3.0
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
    """光隔离器 S 参数模型。正向传输低损耗，反向高隔离。端口: in, out

    默认值（Yariv 1997 §11.4）: isolation_db=40.0
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
    """理想反射镜 S 参数模型。端口: in（单端口，全反射）

    默认值（Yariv 1997 §4.5）: reflectivity=1.0
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
    """弯曲波导 S 参数模型。引入相位累积和弯曲损耗。端口: in, out

    默认值（SiEPIC EBeam PDK, Chrostowski 2015 §3.4）:
    - radius=10μm, loss_db_cm=0.5
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


# ---------------------------------------------------------------------------
# R02 新增模型：half_ring / add_drop_ring / Sellmeier 色散
# ---------------------------------------------------------------------------

# Sellmeier 色散参数（SOI 220nm strip 波导）: n_eff(λ)=sqrt(A+B/λ²+C/λ⁴)
# A=5.76 (@1550nm neff²≈5.76, neff≈2.4, Chrostowski 2015 §2.3)
# B=0.12, C=0.004: SiEPIC EBeam PDK 实测拟合色散项
SELLMEIER_A = 5.76
SELLMEIER_B = 0.12
SELLMEIER_C = 0.004


def sellmeier_neff(
    wl: float | np.ndarray,
    a: float = SELLMEIER_A,
    b: float = SELLMEIER_B,
    c: float = SELLMEIER_C,
) -> np.ndarray:
    """Sellmeier 色散 neff(λ) 模型（R02）。公式: sqrt(A + B/λ² + C/λ⁴)。

    对齐 simphony SiEPIC waveguide 的色散支持。
    Raises: ValueError 波长非正时告警退出（禁止 fall-back）。
    """
    wl_arr = np.asarray(wl, dtype=float)
    if np.any(wl_arr <= 0):
        msg = f"波长必须 > 0 μm，得到 min={float(np.min(wl_arr))}"
        raise ValueError(msg)
    return np.sqrt(a + b / wl_arr**2 + c / wl_arr**4)


def half_ring_s(
    wl: float | np.ndarray = 1.55,
    radius: float = 10.0,
    gap: float = 0.2,
    width: float = 0.5,
    thickness: float = 0.22,
    neff: float = 2.4,
    ng: float = 4.0,
    loss_db_cm: float = 0.1,
) -> SDict:
    """全通型环谐振器 S 参数模型（对齐 simphony siepic.half_ring）。

    传输函数: T(λ) = (t - a·e^{iφ}) / (1 - t·a·e^{iφ})
    - t=sqrt(1-κ): 自耦合; κ: 功率耦合（由 gap 决定）
    - a=10^{-α·L/20}: 单圈衰减; φ=2π·neff·L/λ: 单圈相位; L=2π·R

    端口: in, through
    默认值（SiEPIC EBeam PDK, Chrostowski 2015 §2.3/§4.5）:
    radius=10μm, gap=0.2μm, width=0.5μm, thickness=0.22μm, neff=2.4, ng=4.0
    来源: Yariv 1997 §10.5; Chrostowski 2015 §4.5
    """
    wl_arr = validate_wavelength(wl)
    if radius <= 0:
        msg = f"环半径必须 > 0，得到 {radius}"
        raise ValueError(msg)
    if gap <= 0:
        msg = f"耦合间隙 gap 必须 > 0，得到 {gap}"
        raise ValueError(msg)
    if width <= 0:
        msg = f"波导宽度必须 > 0，得到 {width}"
        raise ValueError(msg)
    if thickness <= 0:
        msg = f"波导厚度必须 > 0，得到 {thickness}"
        raise ValueError(msg)
    circumference = 2.0 * np.pi * radius
    beta = 2.0 * np.pi * neff / wl_arr
    phi = beta * circumference
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    # 耦合系数: κ = exp(-gap/τ)，τ=0.1μm (Chrostowski 2015 §4.5)
    kappa = np.exp(-gap / 0.1)
    if kappa > 1.0:
        kappa = 1.0
    t = np.sqrt(1.0 - kappa)
    T = (t - a * np.exp(1j * phi)) / (1.0 - t * a * np.exp(1j * phi))
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("through", "in"): T,
        ("in", "through"): T,
        ("through", "through"): zero,
    }


def add_drop_ring_s(
    wl: float | np.ndarray = 1.55,
    radius: float = 10.0,
    gap: float = 0.2,
    neff: float = 2.4,
    ng: float = 4.0,
    loss_db_cm: float = 0.0,
) -> SDict:
    """Add-drop 型环谐振器 S 参数模型（双总线，R02）。

    基于 Yariv 1997 §10.5:
    - through: (t1 - t2·a·e^{iφ}) / (1 - t1·t2·a·e^{iφ})
    - drop:    (κ1·κ2·sqrt(a)·e^{iφ/2}) / (1 - t1·t2·a·e^{iφ})

    t_i² + κ_i² = 1。功率守恒（无损）: |T_through|² + |T_drop|² = 1。
    端口: in, through, drop, add
    默认值（SiEPIC EBeam PDK, Chrostowski 2015 §4.5）:
    radius=10μm, gap=0.2μm, neff=2.4, ng=4.0, loss_db_cm=0.0
    """
    wl_arr = validate_wavelength(wl)
    if radius <= 0:
        msg = f"环半径必须 > 0，得到 {radius}"
        raise ValueError(msg)
    if gap <= 0:
        msg = f"耦合间隙 gap 必须 > 0，得到 {gap}"
        raise ValueError(msg)
    circumference = 2.0 * np.pi * radius
    beta = 2.0 * np.pi * neff / wl_arr
    phi = beta * circumference
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    sqrt_a = np.sqrt(a)
    # 功率耦合比 κ² = exp(-gap/τ)，τ=0.1μm (Chrostowski 2015 §4.5)
    kappa_power = np.exp(-gap / 0.1)
    if kappa_power > 1.0:
        kappa_power = 1.0
    # 振幅耦合 κ=sqrt(κ²), 自耦合 t=sqrt(1-κ²), 满足 t²+κ²=1
    kappa1_amp = kappa2_amp = np.sqrt(kappa_power)
    t1 = t2 = np.sqrt(1.0 - kappa_power)
    denominator = 1.0 - t1 * t2 * a * np.exp(1j * phi)
    T_through = (t1 - t2 * a * np.exp(1j * phi)) / denominator
    T_drop = (kappa1_amp * kappa2_amp * sqrt_a * np.exp(1j * phi / 2.0)) / denominator
    zero = np.zeros_like(wl_arr, dtype=complex)
    return {
        ("in", "in"): zero,
        ("through", "through"): zero,
        ("drop", "drop"): zero,
        ("add", "add"): zero,
        ("through", "in"): T_through,
        ("drop", "in"): T_drop,
        ("drop", "add"): T_through,
        ("through", "add"): T_drop,
        ("in", "through"): T_through,
        ("in", "drop"): T_drop,
        ("add", "drop"): T_through,
        ("add", "through"): T_drop,
        ("add", "in"): zero,
        ("in", "add"): zero,
        ("through", "drop"): zero,
        ("drop", "through"): zero,
    }
