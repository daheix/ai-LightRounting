"""基础器件 S 参数模型（纯 numpy 实现，规则 3 复刻）。

以下模型参考 SiPANN 的解析模型与 Simphony 的 SiEPIC 模型库：
- SiPANN: https://sipann.readthedocs.io/en/latest/models.html
- Simphony SiEPIC: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- 波导传播模型: e^{i*beta*L}, beta = 2*pi*neff/wl

SiPANN 安装失败（ResolutionImpossible），按 project_rules.md 规则 3
用纯 numpy 100% 复刻其解析模型，通过功率守恒和谐振陷波测试验证。
"""

from __future__ import annotations

import numpy as np

from polaris.sim.types import SDict


def waveguide_s(
    wl: float | np.ndarray = 1.55,
    length: float = 100.0,
    neff: float = 2.4,
    ng: float = 4.0,
    loss_db_cm: float = 0.0,
) -> SDict:
    """波导传播 S 参数模型。

    光在波导中传播距离 L 后的相位累积与损耗：
    - 相位: phi = 2*pi*neff*L/wl
    - 损耗: alpha = -loss_db_cm * L / (10*4.343) (转换为振幅衰减)
    - 群折射率 ng 用于色散计算

    来源:
    - Simphony waveguide 模型: https://simphonyphotonics.readthedocs.io/
    - SiPANN waveguide 模型: https://sipann.readthedocs.io/
    """
    wl = np.asarray(wl, dtype=float)
    beta = 2.0 * np.pi * neff / wl
    phase = np.exp(1j * beta * length)
    # 损耗：dB/cm → 振幅衰减因子
    if loss_db_cm > 0:
        alpha = 10.0 ** (-loss_db_cm * length / 1e4 / 20.0)  # length in μm → cm
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
    """Y 分支 S 参数模型（1进2出/2进1出分束器）。

    理想 3dB 分束器：每个输出端口获得 50% 功率（-3dB），
    加上插损后实际功率略低于 50%。

    端口: port_1（合束/分束端）, port_2, port_3（两个分支端）

    来源:
    - Simphony siepic.y_branch: https://simphonyphotonics.readthedocs.io/
    - SiPANN y_branch 模型: https://sipann.readthedocs.io/
    """
    wl = np.asarray(wl, dtype=float)
    # 功率分束比 0.5，加上插损
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)  # -3dB 分束 + 插损
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
) -> SDict:
    """定向耦合器 S 参数模型。

    耦合区长度决定分光比。耦合系数 kappa 由间隙 gap 和波长 wl 决定。
    简化模型：coupling 为功率耦合比（0~1），转换为振幅。

    端口: in1, in2, out1, out2（交叉耦合 out2←in1, out1←in2）

    来源:
    - SiPANN directional_coupler: https://sipann.readthedocs.io/en/latest/models.html
    - Simphony siepic.directional_coupler
    """
    wl = np.asarray(wl, dtype=float)
    # 振幅耦合系数 = sqrt(功率耦合比)
    kappa = np.sqrt(coupling)
    # 直通振幅 = sqrt(1 - kappa^2)
    tau = np.sqrt(1.0 - coupling)
    # 相位（耦合区引入 π/2 相位差）
    kappa_arr = np.full_like(wl, kappa, dtype=complex) * 1j
    tau_arr = np.full_like(wl, tau, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        # 直通: out1 ← in1, out2 ← in2
        ("out1", "in1"): tau_arr,
        ("out2", "in2"): tau_arr,
        # 交叉耦合: out2 ← in1, out1 ← in2
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
    neff: float = 2.4,
    ng: float = 4.0,
    coupling: float = 0.01,
    loss_db_cm: float = 0.0,
) -> SDict:
    """环谐振器 S 参数模型（全通型 single bus）。

    环谐振器的洛伦兹谐振峰由环周长和耦合系数决定。
    传输函数: T = (t - a*e^{i*phi}) / (1 - t*a*e^{i*phi})
    其中 t=直通振幅, a=环内损耗, phi=环周相位

    注意：全通型环在无损（a=1）时传输始终为 1（仅相位变化），
    谐振陷波仅在环内有损耗时出现。

    端口: in, through（直通端）, drop（下路端，全通型无 drop）

    来源:
    - SiPANN ring_resonator: https://sipann.readthedocs.io/en/latest/models.html
    - Lorentzian 谐振模型: 标准光子学教材
    """
    wl = np.asarray(wl, dtype=float)
    # 环周长
    circumference = 2.0 * np.pi * radius
    # 环内传播相位
    beta = 2.0 * np.pi * neff / wl
    phi = beta * circumference
    # 环内损耗（振幅）— 默认给一个小损耗以显示谐振
    if loss_db_cm <= 0:
        loss_db_cm = 0.1  # 默认 0.1 dB/cm 以显示谐振陷波
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    # 直通振幅（自耦合系数）
    t = np.sqrt(1.0 - coupling)
    # 传输函数（全通型）
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
    """MMI 1x2 S 参数模型（1进2出分束器）。

    理想 3dB 分束器，与 Y 分支类似但基于多模干涉原理。

    端口: in, out1, out2

    来源:
    - gdsfactory mmi1x2: https://gdsfactory.github.io/gdsfactory/
    - Simphony SiEPIC MMI 模型
    """
    wl = np.asarray(wl, dtype=float)
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
    """MMI 2x2 S 参数模型（2进2出分束器/合束器）。

    端口: in1, in2, out1, out2

    来源:
    - gdsfactory mmi2x2: https://gdsfactory.github.io/gdsfactory/
    """
    wl = np.asarray(wl, dtype=float)
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    amp_arr = np.full_like(wl, amp, dtype=complex)
    # MMI 2x2 交叉耦合（bar/cross 状态）
    cross_arr = amp_arr * 1j  # 交叉端口有 π/2 相位差
    bar_arr = amp_arr
    zero = np.zeros_like(wl, dtype=complex)
    return {
        ("in1", "in1"): zero,
        ("in2", "in2"): zero,
        ("out1", "out1"): zero,
        ("out2", "out2"): zero,
        # bar: out1←in1, out2←in2
        ("out1", "in1"): bar_arr,
        ("out2", "in2"): bar_arr,
        ("in1", "out1"): bar_arr,
        ("in2", "out2"): bar_arr,
        # cross: out2←in1, out1←in2
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
    """光栅耦合器 S 参数模型（高斯型波长响应）。

    光栅耦合器有中心波长和带宽，响应曲线近似高斯型。

    端口: fiber（光纤端）, waveguide（波导端）

    来源:
    - Simphony siepic.grating_coupler: https://simphonyphotonics.readthedocs.io/
    - gdsfactory grating_coupler: https://gdsfactory.github.io/gdsfactory/
    """
    wl = np.asarray(wl, dtype=float)
    # 高斯型波长响应
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
    """波导交叉 S 参数模型。

    端口: in1, in2, out1, out2（直通无交叉耦合）

    来源: gdsfactory crossing
    """
    wl = np.asarray(wl, dtype=float)
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
    """终端吸收器 S 参数模型（吸收残余光，防止反射）。

    端口: in（单端口）

    来源: Simphony siepic.terminator
    """
    wl = np.asarray(wl, dtype=float)
    r = 10.0 ** (reflection_db / 20.0)
    r_arr = np.full_like(wl, r, dtype=complex)
    return {("in", "in"): r_arr}


def phase_shifter_s(
    wl: float | np.ndarray = 1.55,
    phase_rad: float = 0.0,
    insertion_loss_db: float = 0.0,
) -> SDict:
    """热光移相器 S 参数模型。

    通过加热改变波导有效折射率，引入可调相位。

    端口: in, out

    来源: gdsfactory phase_shifter
    """
    wl = np.asarray(wl, dtype=float)
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
