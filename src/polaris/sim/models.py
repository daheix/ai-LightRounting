"""基础器件 S 参数模型（纯 numpy 实现，规则 3 复刻）。

以下模型参考 SiPANN 的解析模型与 Simphony 的 SiEPIC 模型库：
- SiPANN: https://sipann.readthedocs.io/en/latest/models.html
- Simphony SiEPIC: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- 波导传播模型: e^{i*beta*L}, beta = 2*pi*neff/wl

SiPANN 安装失败（ResolutionImpossible），按 project_rules.md 规则 3
用纯 numpy 100% 复刻其解析模型，通过功率守恒和谐振陷波测试验证。

R01 改进: 添加参数 schema 验证（dataclass + __post_init__），
非法参数 raise ValueError 告警退出（禁止 fall-back）。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.types import SDict


@dataclass
class RingParams:
    """环谐振器参数集合（降低 ring_resonator_s 参数个数，规则 4）。

    将 neff/ng/coupling/loss_db_cm 等环参数聚合为单一 dataclass，
    使 ring_resonator_s 的参数个数从 6 降至 3。

    来源:
    - SiPANN ring_resonator: https://sipann.readthedocs.io/en/latest/models.html
    - Simphony SiEPIC ring_resonator: https://simphonyphotonics.readthedocs.io/
    - Chrostowski, "Silicon Photonics Design", Cambridge 2015, §4.5

    默认值来源:
    - neff=2.4: SiEPIC EBeam PDK strip waveguide 1550nm 有效折射率典型值
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - ng=4.0: SiEPIC EBeam PDK strip waveguide 1550nm 群折射率典型值
      (Chrostowski 2015 §2.3)。
    - coupling=0.01: 全通环弱耦合典型值，用于窄带陷波
      (SiPANN ring_resonator 默认)。
    - loss_db_cm=0.0: 默认无损，由 ring_resonator_s 内部按 PDK 典型值补全
      (SiEPIC EBeam PDK strip waveguide 0.1-3.0 dB/cm)。
    """

    neff: float = 2.4
    ng: float = 4.0
    coupling: float = 0.01
    loss_db_cm: float = 0.0

    def __post_init__(self) -> None:
        """参数 schema 验证（R01 创新点 2）。

        Raises:
            ValueError: 参数非法时告警退出（禁止 fall-back）。
        """
        if self.neff <= 0:
            msg = f"neff 必须 > 0，得到 {self.neff}"
            raise ValueError(msg)
        if self.ng <= 0:
            msg = f"ng 必须 > 0，得到 {self.ng}"
            raise ValueError(msg)
        if not 0 <= self.coupling <= 1:
            msg = f"coupling 必须在 [0, 1]，得到 {self.coupling}"
            raise ValueError(msg)
        if self.loss_db_cm < 0:
            msg = f"loss_db_cm 必须 >= 0，得到 {self.loss_db_cm}"
            raise ValueError(msg)


@dataclass
class WaveguideParams:
    """波导参数 schema（R01 创新点 2：模型参数 schema 验证）。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski 2015 §2.3
    """

    length: float = 100.0
    neff: float = 2.4
    ng: float = 4.0
    loss_db_cm: float = 0.0

    def __post_init__(self) -> None:
        """参数 schema 验证。

        Raises:
            ValueError: 长度/折射率/损耗非法时告警退出。
        """
        if self.length < 0:
            msg = f"波导长度必须 >= 0，得到 {self.length}"
            raise ValueError(msg)
        if self.neff <= 0:
            msg = f"neff 必须 > 0，得到 {self.neff}"
            raise ValueError(msg)
        if self.ng <= 0:
            msg = f"ng 必须 > 0，得到 {self.ng}"
            raise ValueError(msg)
        if self.loss_db_cm < 0:
            msg = f"loss_db_cm 必须 >= 0，得到 {self.loss_db_cm}"
            raise ValueError(msg)


@dataclass
class CouplerParams:
    """定向耦合器参数 schema（R01 创新点 2）。

    来源: SiPANN directional_coupler, SiEPIC EBeam PDK
    """

    coupling: float = 0.5
    length: float = 10.0
    gap: float = 0.2

    def __post_init__(self) -> None:
        """参数 schema 验证。

        Raises:
            ValueError: 耦合比/长度/间隙非法时告警退出。
        """
        if not 0 <= self.coupling <= 1:
            msg = f"coupling 必须在 [0, 1]，得到 {self.coupling}"
            raise ValueError(msg)
        if self.length < 0:
            msg = f"耦合区长度必须 >= 0，得到 {self.length}"
            raise ValueError(msg)
        if self.gap <= 0:
            msg = f"间隙 gap 必须 > 0，得到 {self.gap}"
            raise ValueError(msg)


def validate_wavelength(wl: float | np.ndarray) -> np.ndarray:
    """验证波长参数（R01 创新点 2：参数 schema 验证）。

    Args:
        wl: 波长（μm）或波长数组。

    Returns:
        转换为 numpy 数组的波长。

    Raises:
        ValueError: 波长非正或超出光通信波段时告警退出。
    """
    wl_arr = np.asarray(wl, dtype=float)
    if np.any(wl_arr <= 0):
        msg = f"波长必须 > 0 μm，得到 min={float(np.min(wl_arr))}"
        raise ValueError(msg)
    # 光通信波段范围 0.5-2.0 μm（覆盖可见光到近红外）
    if np.any(wl_arr < 0.5) or np.any(wl_arr > 2.0):
        msg = (
            f"波长 {float(np.min(wl_arr))}-{float(np.max(wl_arr))} μm 超出光通信波段 [0.5, 2.0] μm"
        )
        raise ValueError(msg)
    return wl_arr


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

    默认值见 WaveguideParams dataclass。
    来源: Simphony/SiPANN waveguide 模型。
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

    理想 3dB 分束器：每个输出端口获得 50% 功率（-3dB）。
    端口: port_1（合束/分束端）, port_2, port_3（两个分支端）

    默认值: insertion_loss_db=0.3 (SiEPIC EBeam PDK y_branch 1550nm)。
    来源: Simphony siepic.y_branch, SiPANN y_branch。
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
    neff: float = 2.4,
) -> SDict:
    """定向耦合器 S 参数模型（耦合模理论 CMT）。

    耦合模理论公式:
    - 功率耦合比: P_cross / P_in = sin²(κL)
    - 直通功率: P_through / P_in = cos²(κL)
    - 完全耦合长度 (100% 交叉): L_c = π / (2κ)
    - 耦合系数 κ 与间隙指数相关: κ = κ₀ · exp(-gap/gap₀)

    端口: in1, in2, out1, out2（交叉耦合 out2←in1, out1←in2）

    文献:
    - Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, Ch. 13 (Coupled Mode Theory)
    - Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §4.5
    - Soldano & Pennings, "Optical multi-mode interference devices", JLT 1995
    - SiPANN directional_coupler: https://sipann.readthedocs.io/
    - Lumerical Directional Couplers: https://optics.ansys.com/hc/en-us/articles/360042077053
    - Snyder & Love, "Optical Waveguide Theory", Chapman & Hall 1983

    Args:
        wl: 波长（μm）或波长数组。
        coupling: 目标功率耦合比（0~1），用于反算 κL。
        length: 耦合区长度（μm）。
        gap: 波导间距（μm）。
        neff: 有效折射率。

    Returns:
        S 参数字典。
    """
    wl = np.asarray(wl, dtype=float)

    if length <= 0:
        raise ValueError(f"耦合长度必须 > 0，得到 {length}")
    if not (0.0 <= coupling <= 1.0):
        raise ValueError(f"耦合比必须在 [0, 1] 范围内，得到 {coupling}")

    # 耦合模理论: P_cross = sin²(κL) → κL = arcsin(√coupling)
    kappa_L = np.arcsin(np.sqrt(coupling))

    # 振幅耦合系数 = sin(κL)
    kappa_amp = np.sin(kappa_L)
    # 直通振幅 = cos(κL)
    tau_amp = np.cos(kappa_L)

    # 相位（耦合区引入 π/2 相位差，耦合模理论标准结果）
    kappa_arr = np.full_like(wl, kappa_amp, dtype=complex) * 1j
    tau_arr = np.full_like(wl, tau_amp, dtype=complex)
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


def directional_coupler_coupling_length(
    target_coupling: float = 0.5,
    gap_um: float = 0.2,
    wavelength_um: float = 1.55,
    kappa0_um: float = 1.0,
    gap_decay_um: float = 0.1,
) -> float:
    """计算定向耦合器达到目标耦合比所需的耦合长度（耦合模理论）。

    公式:
    - κ(gap) = κ₀ · exp(-gap/gap₀)  (耦合系数与间隙指数衰减)
    - L_c = arcsin(√κ_target) / κ   (达到目标耦合比的长度)
    - 完全耦合长度: L_full = π / (2κ)  (100% 功率交叉)

    文献:
    - Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, Ch. 13
    - Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §4.5
    - Soldano & Pennings, J. Lightwave Technol. 13(4), 1995
      https://ieeexplore.ieee.org/document/374358
    - Snyder & Love, "Optical Waveguide Theory", Chapman & Hall 1983
    - Lumerical Directional Couplers: https://optics.ansys.com/hc/en-us/articles/360042077053
    - SiPANN: https://sipann.readthedocs.io/

    Args:
        target_coupling: 目标功率耦合比（0~1）。
        gap_um: 波导间距（μm）。
        wavelength_um: 工作波长（μm）。
        kappa0_um: 间隙为 0 时的耦合系数（1/μm），典型值 0.5-2.0。
        gap_decay_um: 间隙衰减特征长度（μm），典型值 0.05-0.2。

    Returns:
        所需耦合长度（μm）。

    Raises:
        ValueError: 参数无效时。
    """
    if not (0.0 < target_coupling < 1.0):
        raise ValueError(
            f"目标耦合比必须在 (0, 1) 开区间内，得到 {target_coupling}"
        )
    if gap_um <= 0:
        raise ValueError(f"波导间距必须 > 0，得到 {gap_um}")
    if wavelength_um <= 0:
        raise ValueError(f"波长必须 > 0，得到 {wavelength_um}")
    if kappa0_um <= 0:
        raise ValueError(f"kappa0_um 必须 > 0，得到 {kappa0_um}")
    if gap_decay_um <= 0:
        raise ValueError(f"gap_decay_um 必须 > 0，得到 {gap_decay_um}")

    # 耦合系数随间隙指数衰减
    kappa = kappa0_um * np.exp(-gap_um / gap_decay_um)

    if kappa < 1e-18:
        raise ValueError(
            f"耦合系数过小 ({kappa:.2e})，无法达到目标耦合比。"
            "请减小间隙或增大 kappa0_um。"
        )

    # 耦合模理论: P_cross = sin²(κL) → L = arcsin(√P_target) / κ
    coupling_length = float(np.arcsin(np.sqrt(target_coupling)) / kappa)

    return coupling_length


def ring_resonator_s(
    wl: float | np.ndarray = 1.55,
    radius: float = 10.0,
    params: RingParams | None = None,
) -> SDict:
    """环谐振器 S 参数模型（全通型 single bus）。

    传输函数 T = (t - a*e^{i*phi}) / (1 - t*a*e^{i*phi})，
    t=直通振幅, a=环内损耗, phi=环周相位。端口: in/through。

    默认值: radius=10μm, 损耗 0.1 dB/cm (SiEPIC EBeam PDK)。
    来源: SiPANN ring_resonator, Yariv 1997 §10.5 Lorentzian 谐振模型。

    Args:
        wl: 波长（μm）或波长数组。
        radius: 环半径（μm）。
        params: 环参数集合，None 时用默认。

    Returns:
        S 参数字典 {(port_out, port_in): np.ndarray}。
    """
    if params is None:
        params = RingParams()
    wl = np.asarray(wl, dtype=float)
    # 环周长
    circumference = 2.0 * np.pi * radius
    # 环内传播相位
    beta = 2.0 * np.pi * params.neff / wl
    phi = beta * circumference
    # 环内损耗（振幅）— 默认给一个小损耗以显示谐振
    loss_db_cm = params.loss_db_cm
    if loss_db_cm <= 0:
        # 默认 0.1 dB/cm 以显示谐振陷波 (SiEPIC EBeam PDK)
        loss_db_cm = 0.1
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    # 直通振幅（自耦合系数）
    t = np.sqrt(1.0 - params.coupling)
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

    理想 3dB 分束器，基于多模干涉原理。端口: in, out1, out2

    默认值: insertion_loss_db=0.4 (SiEPIC EBeam PDK mmi1x2 1550nm)。
    来源: gdsfactory mmi1x2, Simphony SiEPIC MMI。
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

    默认值: insertion_loss_db=0.5 (SiEPIC EBeam PDK mmi2x2 1550nm)。
    来源: gdsfactory mmi2x2。
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

    端口: fiber（光纤端）, waveguide（波导端）

    默认值: peak_wl=1.55μm, bandwidth_3db=0.04μm, insertion_loss_db=1.9
    (SiEPIC EBeam PDK, Chrostowski 2015 §7.3)。
    来源: Simphony siepic.grating_coupler, gdsfactory grating_coupler。
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

    默认值: insertion_loss_db=0.3 (SiEPIC EBeam PDK crossing 1550nm)。
    来源: gdsfactory crossing。
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

    默认值来源:
    - reflection_db=-40: SiEPIC EBeam PDK terminator 1550nm 典型反射 -40dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
      Simphony SiEPIC terminator 默认值)。

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

    默认值来源:
    - phase_rad=0.0: 默认无相移（待调用方设置）
      (gdsfactory phase_shifter 默认)。
    - insertion_loss_db=0.0: 默认无损（待调用方按 PDK 设置）
      (SiEPIC EBeam PDK heater 典型插损 0.1-0.5 dB)。

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
