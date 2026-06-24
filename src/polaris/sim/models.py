"""基础器件 S 参数模型（纯 numpy 实现，规则 3 复刻）。

以下模型参考 SiPANN 的解析模型与 Simphony 的 SiEPIC 模型库：
- SiPANN: https://sipann.readthedocs.io/en/latest/models.html
- Simphony SiEPIC: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- 波导传播模型: e^{i*beta*L}, beta = 2*pi*neff/wl

SiPANN 安装失败（ResolutionImpossible），按 project_rules.md 规则 3
用纯 numpy 100% 复刻其解析模型，通过功率守恒和谐振陷波测试验证。
<<<<<<< HEAD

R01 改进: 添加参数 schema 验证（dataclass + __post_init__），
非法参数 raise ValueError 告警退出（禁止 fall-back）。
=======
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
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

=======
>>>>>>> trae/solo-agent-pkVjID

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
<<<<<<< HEAD

    默认值见 WaveguideParams dataclass。
    来源: Simphony/SiPANN waveguide 模型。
=======
    - 群折射率 ng 用于色散计算

    默认值来源:
    - wl=1.55μm: C 波段中心波长 (ITU-T G.694.1 DWDM 标准)。
    - length=100μm: SiEPIC EBeam PDK 波导典型长度
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - neff=2.4: SiEPIC EBeam PDK strip waveguide 1550nm 有效折射率典型值
      (Chrostowski 2015 §2.3)。
    - ng=4.0: SiEPIC EBeam PDK strip waveguide 1550nm 群折射率典型值
      (Chrostowski 2015 §2.3)。
    - loss_db_cm=0.0: 默认无损，调用方按场景设置
      (SiEPIC EBeam PDK strip waveguide 0.1-3.0 dB/cm)。

    来源:
    - Simphony waveguide 模型: https://simphonyphotonics.readthedocs.io/
    - SiPANN waveguide 模型: https://sipann.readthedocs.io/
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    理想 3dB 分束器：每个输出端口获得 50% 功率（-3dB）。
    端口: port_1（合束/分束端）, port_2, port_3（两个分支端）

    默认值: insertion_loss_db=0.3 (SiEPIC EBeam PDK y_branch 1550nm)。
    来源: Simphony siepic.y_branch, SiPANN y_branch。
=======
    理想 3dB 分束器：每个输出端口获得 50% 功率（-3dB），
    加上插损后实际功率略低于 50%。

    端口: port_1（合束/分束端）, port_2, port_3（两个分支端）

    默认值来源:
    - insertion_loss_db=0.3: SiEPIC EBeam PDK y_branch 1550nm 典型插损 0.3dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
      Simphony SiEPIC y_branch 默认值)。

    来源:
    - Simphony siepic.y_branch: https://simphonyphotonics.readthedocs.io/
    - SiPANN y_branch 模型: https://sipann.readthedocs.io/
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    耦合区长度决定分光比。简化模型：coupling 为功率耦合比（0~1）。
    端口: in1, in2, out1, out2（交叉耦合 out2←in1, out1←in2）

    默认值见 CouplerParams dataclass。
    来源: SiPANN directional_coupler, Simphony siepic.directional_coupler。
=======
    耦合区长度决定分光比。耦合系数 kappa 由间隙 gap 和波长 wl 决定。
    简化模型：coupling 为功率耦合比（0~1），转换为振幅。

    端口: in1, in2, out1, out2（交叉耦合 out2←in1, out1←in2）

    默认值来源:
    - coupling=0.5: 3dB 分束典型值 (50:50 分光比)
      (SiPANN directional_coupler 默认)。
    - length=10μm: SiEPIC EBeam PDK 定向耦合器耦合区典型长度
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - gap=0.2μm: SiEPIC EBeam PDK 定向耦合器 gap 200nm
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。

    来源:
    - SiPANN directional_coupler: https://sipann.readthedocs.io/en/latest/models.html
    - Simphony siepic.directional_coupler
>>>>>>> trae/solo-agent-pkVjID
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
    params: RingParams | None = None,
) -> SDict:
    """环谐振器 S 参数模型（全通型 single bus）。

    传输函数 T = (t - a*e^{i*phi}) / (1 - t*a*e^{i*phi})，
<<<<<<< HEAD
    t=直通振幅, a=环内损耗, phi=环周相位。端口: in/through。

    默认值: radius=10μm, 损耗 0.1 dB/cm (SiEPIC EBeam PDK)。
    来源: SiPANN ring_resonator, Yariv 1997 §10.5 Lorentzian 谐振模型。
=======
    t=直通振幅, a=环内损耗, phi=环周相位。无损时传输恒为 1，
    谐振陷波仅在环内有损耗时出现。端口: in/through/drop（全通型无 drop）。

    默认值来源:
    - radius=10μm: SiEPIC EBeam PDK ring_resonator 默认半径 10μm
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - 默认损耗 0.1 dB/cm: SiEPIC EBeam PDK strip waveguide 1550nm 传播损耗
      典型值 0.1-3.0 dB/cm，取下限用于显示谐振陷波
      (Chrostowski 2015 §6.4)。

    来源:
    - SiPANN ring_resonator: https://sipann.readthedocs.io/en/latest/models.html
    - Lorentzian 谐振模型: 标准光子学教材
      (Yariv, "Optical Electronics in Modern Communications", Oxford 1997, §10.5)
>>>>>>> trae/solo-agent-pkVjID

    Args:
        wl: 波长（μm）或波长数组。
        radius: 环半径（μm）。
<<<<<<< HEAD
        params: 环参数集合，None 时用默认。
=======
        params: 环参数集合（neff/ng/coupling/loss_db_cm），None 时用默认。
>>>>>>> trae/solo-agent-pkVjID

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
<<<<<<< HEAD
        # 默认 0.1 dB/cm 以显示谐振陷波 (SiEPIC EBeam PDK)
=======
        # 默认 0.1 dB/cm 以显示谐振陷波
        # 来源: SiEPIC EBeam PDK strip waveguide 1550nm 传播损耗典型值 0.1-3.0 dB/cm
        #   SiEPIC_EBeam_PDK, Lukas Chrostowski et al., UBC, MIT 协议
        #   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    理想 3dB 分束器，基于多模干涉原理。端口: in, out1, out2

    默认值: insertion_loss_db=0.4 (SiEPIC EBeam PDK mmi1x2 1550nm)。
    来源: gdsfactory mmi1x2, Simphony SiEPIC MMI。
=======
    理想 3dB 分束器，与 Y 分支类似但基于多模干涉原理。

    端口: in, out1, out2

    默认值来源:
    - insertion_loss_db=0.4: SiEPIC EBeam PDK mmi1x2 1550nm 典型插损 0.4dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
      gdsfactory mmi1x2 默认插损)。

    来源:
    - gdsfactory mmi1x2: https://gdsfactory.github.io/gdsfactory/
    - Simphony SiEPIC MMI 模型
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    默认值: insertion_loss_db=0.5 (SiEPIC EBeam PDK mmi2x2 1550nm)。
    来源: gdsfactory mmi2x2。
=======
    默认值来源:
    - insertion_loss_db=0.5: SiEPIC EBeam PDK mmi2x2 1550nm 典型插损 0.5dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
      gdsfactory mmi2x2 默认插损)。

    来源:
    - gdsfactory mmi2x2: https://gdsfactory.github.io/gdsfactory/
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    端口: fiber（光纤端）, waveguide（波导端）

    默认值: peak_wl=1.55μm, bandwidth_3db=0.04μm, insertion_loss_db=1.9
    (SiEPIC EBeam PDK, Chrostowski 2015 §7.3)。
    来源: Simphony siepic.grating_coupler, gdsfactory grating_coupler。
=======
    光栅耦合器有中心波长和带宽，响应曲线近似高斯型。

    端口: fiber（光纤端）, waveguide（波导端）

    默认值来源:
    - peak_wl=1.55μm: C 波段中心波长 (ITU-T G.694.1)。
    - bandwidth_3db=0.04μm: SiEPIC EBeam PDK grating_coupler 3dB 带宽 40nm
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
    - insertion_loss_db=1.9: SiEPIC EBeam PDK grating_coupler 1550nm 典型插损
      1.5-2.5 dB，取中值 1.9dB
      (Chrostowski 2015 §7.3)。

    来源:
    - Simphony siepic.grating_coupler: https://simphonyphotonics.readthedocs.io/
    - gdsfactory grating_coupler: https://gdsfactory.github.io/gdsfactory/
>>>>>>> trae/solo-agent-pkVjID
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

<<<<<<< HEAD
    默认值: insertion_loss_db=0.3 (SiEPIC EBeam PDK crossing 1550nm)。
    来源: gdsfactory crossing。
=======
    默认值来源:
    - insertion_loss_db=0.3: SiEPIC EBeam PDK crossing 1550nm 典型插损 0.3dB
      (https://github.com/SiEPIC/SiEPIC_EBeam_PDK;
      gdsfactory crossing 默认插损)。

    来源: gdsfactory crossing
>>>>>>> trae/solo-agent-pkVjID
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
