"""基础器件频域 S 参数模型（纯 NumPy 实现）。

本模块迁移自旧 ``polaris_sim/models.py``，聚焦频域解析 S 参数模型，
为 polaris-sparam 子模块提供波导 / MMI / 光栅耦合器的稳定 Python API。

## Input（输入）
- wavelength_um: 波长列表（μm），如 [1.50, 1.55, 1.60]
- device_params: 器件物理参数
  - 波导: neff=2.4（SiEPIC EBeam PDK strip 1550nm）、loss_db_cm=3.0
  - MMI 1x2: insertion_loss_db=0.4
  - MMI 2x2: insertion_loss_db=0.5
  - 光栅耦合器: peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9

## Process（处理）
- 波导: S = exp(-α·L/2 + j·2π·neff·L/λ)
  - α [1/μm] = loss_db_cm / 4.343 / 1e4（功率衰减系数）
  - 4.343 = 10·log10(e)，将 dB/cm 转 Np/cm；1e4 将 1/cm 转 1/μm
  - 振幅衰减 exp(-α·L/2)（场，对应功率 exp(-α·L)）
- MMI 1x2: S = sqrt(10^(-il/10)/2) · exp(j·π/2)
  - 10^(-il/10) 为插损后总功率，/2 为 3dB 分束，sqrt 取振幅
  - π/2 相位为 MMI 多模干涉固有相位（Soldano 1995）
- MMI 2x2: bar 实数 + cross 带 π/2 相位，振幅同 1x2
- 光栅耦合器: S = sqrt(10^(-il/10)) · exp(-((λ-peak)/bw)²)
  - 高斯型波长响应，bw 为高斯宽度参数（SiEPIC EBeam PDK GC 模型）

## Output（输出）
- dict: key 为端口对 str（``port_key``），value 为对应每个波长的复数 S 参数 list[complex]

## 设计原则
- 对外 API 返回 dict，key 为端口对 tuple 转 str（JSON 友好）
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 非法参数 raise ValueError
- 物理参数来自 SiEPIC EBeam PDK（neff=2.4, MMI split=0.48, GC il=1.9dB）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Simphony SiEPIC 模型库
  https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- SiPANN 解析模型
  https://sipann.readthedocs.io/en/latest/models.html
- SiEPIC EBeam PDK
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §2.3/§7.3
- Soldano & Pennings, "Optical multi-mode interference devices",
  J. Lightwave Technol. 13(4), 1995
  https://ieeexplore.ieee.org/document/374358
- Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, Ch. 13
- gdsfactory 组件库 https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "waveguide_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "port_key",
]


def port_key(out_port: str, in_port: str) -> str:
    """端口对 dict key（tuple 转 str，JSON 友好）。

    Args:
        out_port: 输出端口名（如 "out"）。
        in_port: 输入端口名（如 "in"）。

    Returns:
        端口对字符串 ``str((out_port, in_port))``，例如 ``"('out', 'in')"``。
    """
    return str((out_port, in_port))


def _to_array(wavelength_um: list | np.ndarray) -> np.ndarray:
    """波长列表转 numpy 数组并校验（R03: 非法即 raise）。"""
    arr = np.asarray(wavelength_um, dtype=float)
    if arr.ndim == 0:
        # 标量也包装为一维，保证返回值始终为 list
        arr = arr.reshape(1)
    if np.any(arr <= 0):
        raise ValueError(f"波长必须 > 0 μm，得到 min={float(np.min(arr))}")
    return arr


def waveguide_s(
    wavelength_um: list,
    length_um: float,
    neff: float = 2.4,
    loss_db_cm: float = 3.0,
) -> dict:
    """波导传播 S 参数模型（频域）。

    S = exp(-α·L/2 + j·2π·neff·L/λ)

    其中 α [1/μm] = loss_db_cm / 4.343 / 1e4 为功率衰减系数
    （4.343 = 10·log10(e) 将 dB/cm 转 Np/cm，1e4 将 1/cm 转 1/μm），
    振幅衰减为 exp(-α·L/2)（场衰减，对应功率 exp(-α·L)）。

    端口: in, out（互易双端口，无反射）。

    Args:
        wavelength_um: 波长列表（μm），如 [1.50, 1.55, 1.60]。
        length_um: 波导长度（μm）。
        neff: 有效折射率（默认 2.4，SiEPIC EBeam PDK strip 1550nm）。
        loss_db_cm: 传播损耗（dB/cm，默认 3.0）。

    Returns:
        dict，key 为端口对 str（``port_key``），value 为对应每个波长的
        复数 S 参数 list[complex]。

    Raises:
        ValueError: 波长非正 / 长度负 / neff 非正 / 损耗负（R03 禁止 fall-back）。
    """
    if length_um < 0:
        raise ValueError(f"波导长度必须 >= 0，得到 {length_um}")
    if neff <= 0:
        raise ValueError(f"neff 必须 > 0，得到 {neff}")
    if loss_db_cm < 0:
        raise ValueError(f"loss_db_cm 必须 >= 0，得到 {loss_db_cm}")

    wl = _to_array(wavelength_um)
    # 功率衰减系数 α [1/μm]：dB/cm → Np/μm
    alpha = loss_db_cm / 4.343 / 1e4
    # S = exp(-α·L/2 + j·2π·neff·L/λ)
    s = np.exp(-alpha * length_um / 2.0 + 1j * 2.0 * np.pi * neff * length_um / wl)
    zero = np.zeros_like(s, dtype=complex)
    return {
        port_key("out", "in"): s.tolist(),
        port_key("in", "out"): s.tolist(),
        port_key("in", "in"): zero.tolist(),
        port_key("out", "out"): zero.tolist(),
    }


def mmi_1x2_s(
    wavelength_um: list,
    insertion_loss_db: float = 0.4,
) -> dict:
    """MMI 1x2 S 参数模型（1 进 2 出 3dB 分束器）。

    S = sqrt(10^(-il/10)/2) · exp(j·π/2)

    10^(-il/10) 为插损后总功率传输，/2 为 3dB 等功分束，sqrt 取振幅，
    π/2 为 MMI 多模干涉固有相位（Soldano 1995）。

    端口: in, out1, out2。

    Args:
        wavelength_um: 波长列表（μm）。
        insertion_loss_db: 插入损耗（dB，默认 0.4，SiEPIC EBeam PDK mmi1x2 1550nm）。

    Returns:
        dict，key 为端口对 str，value 为 list[complex]。

    Raises:
        ValueError: 波长非正 / 插损负。
    """
    if insertion_loss_db < 0:
        raise ValueError(f"insertion_loss_db 必须 >= 0，得到 {insertion_loss_db}")
    wl = _to_array(wavelength_um)
    amp = np.sqrt(10.0 ** (-insertion_loss_db / 10.0) / 2.0)
    s = amp * np.exp(1j * np.pi / 2.0)  # π/2 相位
    s_arr = np.full_like(wl, s, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        port_key("out1", "in"): s_arr.tolist(),
        port_key("out2", "in"): s_arr.tolist(),
        port_key("in", "out1"): s_arr.tolist(),
        port_key("in", "out2"): s_arr.tolist(),
        port_key("in", "in"): zero.tolist(),
        port_key("out1", "out1"): zero.tolist(),
        port_key("out2", "out2"): zero.tolist(),
        port_key("out1", "out2"): zero.tolist(),
        port_key("out2", "out1"): zero.tolist(),
    }


def mmi_2x2_s(
    wavelength_um: list,
    insertion_loss_db: float = 0.5,
) -> dict:
    """MMI 2x2 S 参数模型（2 进 2 出分束/合束器，bar/cross 分量）。

    振幅 = sqrt(10^(-il/10)/2)（与 1x2 相同，3dB 等功分束）。
    - bar 分量（out1←in1, out2←in2）: 实数（0 相位）
    - cross 分量（out2←in1, out1←in2）: 乘 exp(j·π/2)（MMI 交叉端口固有 π/2 相位差）

    端口: in1, in2, out1, out2。

    Args:
        wavelength_um: 波长列表（μm）。
        insertion_loss_db: 插入损耗（dB，默认 0.5，SiEPIC EBeam PDK mmi2x2 1550nm）。

    Returns:
        dict，key 为端口对 str，value 为 list[complex]。

    Raises:
        ValueError: 波长非正 / 插损负。
    """
    if insertion_loss_db < 0:
        raise ValueError(f"insertion_loss_db 必须 >= 0，得到 {insertion_loss_db}")
    wl = _to_array(wavelength_um)
    amp = np.sqrt(10.0 ** (-insertion_loss_db / 10.0) / 2.0)
    bar = amp + 0.0j  # bar: 0 相位
    cross = amp * np.exp(1j * np.pi / 2.0)  # cross: π/2 相位
    bar_arr = np.full_like(wl, bar, dtype=complex)
    cross_arr = np.full_like(wl, cross, dtype=complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        # bar 分量
        port_key("out1", "in1"): bar_arr.tolist(),
        port_key("out2", "in2"): bar_arr.tolist(),
        port_key("in1", "out1"): bar_arr.tolist(),
        port_key("in2", "out2"): bar_arr.tolist(),
        # cross 分量
        port_key("out2", "in1"): cross_arr.tolist(),
        port_key("out1", "in2"): cross_arr.tolist(),
        port_key("in1", "out2"): cross_arr.tolist(),
        port_key("in2", "out1"): cross_arr.tolist(),
        # 对角反射项为零
        port_key("in1", "in1"): zero.tolist(),
        port_key("in2", "in2"): zero.tolist(),
        port_key("out1", "out1"): zero.tolist(),
        port_key("out2", "out2"): zero.tolist(),
    }


def grating_coupler_s(
    wavelength_um: list,
    peak_wl: float = 1.55,
    bandwidth_3db: float = 0.04,
    insertion_loss_db: float = 1.9,
) -> dict:
    """光栅耦合器 S 参数模型（高斯型波长响应）。

    S = sqrt(10^(-il/10)) · exp(-((λ-peak)/bw)²)

    sqrt(10^(-il/10)) 为插损振幅因子，exp(-((λ-peak)/bw)²) 为高斯波长响应
    （bw 为高斯宽度参数，SiEPIC EBeam PDK GC 模型典型 bw=0.04μm）。

    端口: fiber（光纤端）, waveguide（波导端），互易。

    Args:
        wavelength_um: 波长列表（μm）。
        peak_wl: 中心波长（μm，默认 1.55）。
        bandwidth_3db: 高斯宽度参数（μm，默认 0.04，SiEPIC EBeam PDK GC 3dB 带宽）。
        insertion_loss_db: 插入损耗（dB，默认 1.9，SiEPIC EBeam PDK GC 1550nm）。

    Returns:
        dict，key 为端口对 str，value 为 list[complex]。

    Raises:
        ValueError: 波长非正 / 带宽非正 / 插损负。
    """
    if bandwidth_3db <= 0:
        raise ValueError(f"bandwidth_3db 必须 > 0，得到 {bandwidth_3db}")
    if insertion_loss_db < 0:
        raise ValueError(f"insertion_loss_db 必须 >= 0，得到 {insertion_loss_db}")
    wl = _to_array(wavelength_um)
    amp = np.sqrt(10.0 ** (-insertion_loss_db / 10.0))
    gaussian = np.exp(-((wl - peak_wl) / bandwidth_3db) ** 2)
    s = (amp * gaussian).astype(complex)
    zero = np.zeros_like(wl, dtype=complex)
    return {
        port_key("waveguide", "fiber"): s.tolist(),
        port_key("fiber", "waveguide"): s.tolist(),
        port_key("fiber", "fiber"): zero.tolist(),
        port_key("waveguide", "waveguide"): zero.tolist(),
    }
