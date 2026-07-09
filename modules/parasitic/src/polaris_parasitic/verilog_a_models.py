"""Verilog-A 光电协同紧凑模型 — 模型生成器（5+ 器件）。

从 v4 ``polaris.sim.verilog_a_models`` 迁移至 polaris-parasitic 子模块
（R13: 不保留 v4 兼容路径）。从 S 参数字典生成 Verilog-A 紧凑模型文件，
支持波导/MMI/环/调制器/探测器 5+ 器件。

注：v4 原任务描述中的 ``verilog_a_waveguide.py`` / ``verilog_a_mmi.py`` /
``verilog_a_modulator.py`` / ``verilog_a_ring.py`` / ``verilog_a_detector.py``
5 个独立文件，在 v4 已整合于 ``verilog_a_models.py``（见 操作记录.md
"verilog_a.py 1392→131 行 facade" 拆分记录），本子模块保持该整合结构，
5 个 generate 函数（waveguide/mmi/ring/modulator/detector）均在本文件中。

核心公式:
- 波导传输: S21 = exp(-α·L/2) · exp(j·2π·neff·L/λ)
- 环谐振器全通传输: T = (t - a·e^{jφ}) / (1 - t·a·e^{jφ})
- MZM 调制: P_out = η · V_in² · cos²(π·V/(2·V_π))
- 探测器: I_photo = R · P_in, V_out = I_photo · R_load

来源（≥5 文献 URL）:
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Verilog-AMS LRM (Language Reference Manual)
  https://www.accellera.org/downloads/standards/v-ams
- INTERCONNECT vs Verilog-A 模型对比
  https://optics.ansys.com/hc/en-us/articles/18698429782291
- Simphony waveguide 模型
  https://simphonyphotonics.readthedocs.io/
- SiPANN ring_resonator
  https://sipann.readthedocs.io/en/latest/models.html
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §2.3/§8.4/§9.2

规则依据: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修 / R11 V8 极简 / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from polaris_parasitic.constants import (
    DEFAULT_DETECTOR_RESPONSIVITY,
    DEFAULT_LOAD_RESISTANCE_OHM,
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_WAVELENGTH_UM,
    DEVICE_TYPE_DETECTOR,
    DEVICE_TYPE_DIRECTIONAL_COUPLER,
    DEVICE_TYPE_GRATING_COUPLER,
    DEVICE_TYPE_MMI_1X2,
    DEVICE_TYPE_MMI_2X2,
    DEVICE_TYPE_MODULATOR,
    DEVICE_TYPE_PHASE_SHIFTER,
    DEVICE_TYPE_RING,
    DEVICE_TYPE_WAVEGUIDE,
    DEVICE_TYPE_Y_BRANCH,
    SUPPORTED_DEVICE_TYPES,
)

# S 参数字典类型（本地定义，切断对 polaris.sim.types 的依赖，R13 不保留 v4 兼容）。
# 原 v4 定义: SDict = dict[tuple[str, str], SArray]，其中 SArray = np.ndarray（无 JAX 时）。
SDict = dict[tuple[str, str], np.ndarray]


@dataclass
class VerilogAModel:
    """Verilog-A 紧凑模型（对应 Lumerical CML Component）。

    来源: Verilog-AMS LRM
      https://www.accellera.org/downloads/standards/v-ams

    Attributes:
        module_name: Verilog-A 模块名（如 "waveguide_soi"）。
        device_type: 器件类型（DEVICE_TYPE_*）。
        ports: 端口列表（光学端口 + 电气端口）。
        parameters: 参数字典 {name: value}。
        s_params: S 参数字典（参考波长处）。
        verilog_a_code: 生成的 Verilog-A 源代码。
    """

    module_name: str
    device_type: str
    ports: list[str]
    parameters: dict[str, float]
    s_params: SDict
    verilog_a_code: str = ""

    def __post_init__(self) -> None:
        """验证模型参数（规则 14.1: 无 fall-back）。

        Raises:
            ValueError: 器件类型不支持或参数非法。
        """
        if self.device_type not in SUPPORTED_DEVICE_TYPES:
            raise ValueError(
                f"不支持的器件类型 {self.device_type}，"
                f"支持: {sorted(SUPPORTED_DEVICE_TYPES)}"
            )
        if not self.module_name:
            raise ValueError("module_name 不能为空")
        if not self.ports:
            raise ValueError("ports 不能为空")


def _format_float(value: float) -> str:
    """格式化浮点数为 Verilog-A 兼容字符串。

    Args:
        value: 浮点数。

    Returns:
        Verilog-A 格式字符串（如 "1.55e-6"）。
    """
    if isinstance(value, complex):
        # 复数 S 参数: 转为幅度（相位在生成器中单独处理）
        magnitude = abs(value)
        return f"{magnitude:.6e}"
    return f"{float(value):.6e}"


def _s_to_magnitude_phase(s_value: complex) -> tuple[float, float]:
    """S 参数复数 → (幅度, 相位弧度)。

    Args:
        s_value: 复数 S 参数。

    Returns:
        (magnitude, phase_rad) 元组。
    """
    if isinstance(s_value, np.ndarray):
        # 取第一个元素（参考波长处）
        s_value = complex(s_value.flat[0])
    return float(abs(s_value)), float(np.angle(s_value))


def _compute_waveguide_s_params(
    length_um: float, neff: float, loss_db_cm: float, wavelength_um: float
) -> SDict:
    """计算波导 S 参数: S21 = exp(-α·L/2) · exp(j·2π·neff·L/λ)。

    来源: Simphony waveguide 模型 https://simphonyphotonics.readthedocs.io/;
    Chrostowski 2015 §2.3。
    """
    beta = 2.0 * math.pi * neff / wavelength_um
    phase = beta * length_um
    alpha = 10.0 ** (-loss_db_cm * length_um / 1e4 / 20.0)
    s21 = alpha * np.exp(1j * phase)
    return {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("out", "in"): np.array(s21, dtype=complex),
        ("in", "out"): np.array(s21, dtype=complex),
        ("out", "out"): np.array(0.0, dtype=complex),
    }


def _render_waveguide_verilog_a_code(
    module_name: str,
    length_um: float,
    neff: float,
    ng: float,
    loss_db_cm: float,
    wavelength_um: float,
) -> str:
    """渲染波导 Verilog-A 源代码。"""
    return f"""`include "disciplines.vams"
`include "constants.vams"

module {module_name} (in, out);
  electrical in, out;
  parameter real length = {length_um:.6e} from [0:inf);  // 波导长度 (m)
  parameter real neff = {neff:.6e} from (0:inf);          // 有效折射率
  parameter real ng = {ng:.6e} from (0:inf);              // 群折射率
  parameter real loss_db_cm = {loss_db_cm:.6e} from [0:inf);  // 损耗 (dB/cm)
  parameter real wavelength = {wavelength_um:.6e} from (0:inf);  // 波长 (m)

  real beta;
  real phase;
  real alpha_linear;
  real s21_mag;
  real s21_phase;

  analog begin
    // 传播常数 beta = 2*pi*neff/lambda
    beta = 2.0 * `M_PI * neff / wavelength;
    // 相位累积
    phase = beta * length;
    // 损耗转线性 (dB/cm -> 振幅衰减)
    // R390 修复: length 单位为 μm，μm→cm 应除以 1e4（原 *1e4 错误放大 1e8 倍）
    alpha_linear = pow(10.0, -loss_db_cm * length / 1e4 / 20.0);
    // S21 = alpha * exp(j*phase)
    s21_mag = alpha_linear;
    s21_phase = phase;
    // 光功率传输（小信号线性近似）
    V(out) <+ s21_mag * cos(s21_phase) * V(in);
  end
endmodule
"""


def generate_waveguide_verilog_a(
    module_name: str = "waveguide_soi",
    length_um: float = 100.0,
    neff: float = 2.4,
    ng: float = 4.0,
    loss_db_cm: float = 0.5,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成波导 Verilog-A 模型。

    波导传输: S21 = exp(-α·L/2) · exp(j·2π·neff·L/λ)

    来源:
    - Simphony waveguide 模型
      https://simphonyphotonics.readthedocs.io/
    - Chrostowski 2015 §2.3

    Args:
        module_name: Verilog-A 模块名。
        length_um: 波导长度（μm）。
        neff: 有效折射率。
        ng: 群折射率。
        loss_db_cm: 损耗（dB/cm）。
        wavelength_um: 参考波长（μm）。

    Returns:
        VerilogAModel 实例。
    """
    if length_um < 0:
        raise ValueError(f"波导长度须 >= 0，得到 {length_um}")
    if neff <= 0:
        raise ValueError(f"neff 须 > 0，得到 {neff}")
    s_params = _compute_waveguide_s_params(length_um, neff, loss_db_cm, wavelength_um)
    code = _render_waveguide_verilog_a_code(
        module_name, length_um, neff, ng, loss_db_cm, wavelength_um
    )
    return VerilogAModel(
        module_name=module_name,
        device_type=DEVICE_TYPE_WAVEGUIDE,
        ports=["in", "out"],
        parameters={
            "length_um": length_um,
            "neff": neff,
            "ng": ng,
            "loss_db_cm": loss_db_cm,
            "wavelength_um": wavelength_um,
        },
        s_params=s_params,
        verilog_a_code=code,
    )


def generate_mmi_1x2_verilog_a(
    module_name: str = "mmi_1x2_soI",
    insertion_loss_db: float = 0.4,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成 MMI 1x2 Verilog-A 模型。

    MMI 1x2: 3dB 分束器，每个输出 50% 功率。
    来源: gdsfactory mmi1x2, SiEPIC EBeam PDK
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        module_name: 模块名。
        insertion_loss_db: 插入损耗（dB）。
        wavelength_um: 参考波长。

    Returns:
        VerilogAModel 实例。
    """
    if insertion_loss_db < 0:
        raise ValueError(f"插损须 >= 0，得到 {insertion_loss_db}")
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    s_params: SDict = {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("out1", "in"): np.array(amp, dtype=complex),
        ("out2", "in"): np.array(amp, dtype=complex),
        ("in", "out1"): np.array(amp, dtype=complex),
        ("in", "out2"): np.array(amp, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, out1, out2);
  electrical in, out1, out2;
  parameter real insertion_loss_db = {insertion_loss_db:.6e} from [0:inf);
  real amp;

  analog begin
    // 3dB 分束 + 插损
    amp = pow(10.0, -(insertion_loss_db + 3.0) / 20.0);
    V(out1) <+ amp * V(in);
    V(out2) <+ amp * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name,
        device_type=DEVICE_TYPE_MMI_1X2,
        ports=["in", "out1", "out2"],
        parameters={"insertion_loss_db": insertion_loss_db, "wavelength_um": wavelength_um},
        s_params=s_params,
        verilog_a_code=code,
    )


def generate_ring_verilog_a(
    module_name: str = "ring_resonator_soi",
    radius_um: float = 10.0,
    neff: float = 2.4,
    coupling: float = 0.01,
    loss_db_cm: float = 0.1,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成环谐振器 Verilog-A 模型（全通型）。

    传输函数: T = (t - a·e^{jφ}) / (1 - t·a·e^{jφ})
    来源: SiPANN ring_resonator, Yariv 1997 §10.5
      https://sipann.readthedocs.io/en/latest/models.html

    Args:
        module_name: 模块名。
        radius_um: 环半径（μm）。
        neff: 有效折射率。
        coupling: 耦合系数。
        loss_db_cm: 损耗（dB/cm）。
        wavelength_um: 参考波长。

    Returns:
        VerilogAModel 实例。
    """
    if radius_um <= 0:
        raise ValueError(f"环半径须 > 0，得到 {radius_um}")
    if not 0 <= coupling <= 1:
        raise ValueError(f"coupling 须在 [0,1]，得到 {coupling}")
    circumference = 2.0 * math.pi * radius_um
    beta = 2.0 * math.pi * neff / wavelength_um
    phi = beta * circumference
    a = 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    t = math.sqrt(1.0 - coupling)
    T = (t - a * np.exp(1j * phi)) / (1.0 - t * a * np.exp(1j * phi))
    s_params: SDict = {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("through", "in"): np.array(T, dtype=complex),
        ("in", "through"): np.array(T, dtype=complex),
        ("through", "through"): np.array(0.0, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, through);
  electrical in, through;
  parameter real radius = {radius_um:.6e} from (0:inf);
  parameter real neff = {neff:.6e} from (0:inf);
  parameter real coupling = {coupling:.6e} from [0:1];
  parameter real loss_db_cm = {loss_db_cm:.6e} from [0:inf);
  parameter real wavelength = {wavelength_um:.6e} from (0:inf);

  real circumference, beta, phi, a, t, T_real, T_imag;

  analog begin
    circumference = 2.0 * `M_PI * radius;
    beta = 2.0 * `M_PI * neff / wavelength;
    phi = beta * circumference;
    // R390 修复: circumference 单位为 μm，μm→cm 应除以 1e4（原 *1e4 错误放大 1e8 倍）
    a = pow(10.0, -loss_db_cm * circumference / 1e4 / 20.0);
    t = sqrt(1.0 - coupling);
    // T = (t - a*exp(j*phi)) / (1 - t*a*exp(j*phi))
    T_real = (t - a*cos(phi)) / (1.0 - t*a*cos(phi));
    T_imag = (-a*sin(phi)) / (1.0 - t*a*cos(phi));
    V(through) <+ T_real * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name,
        device_type=DEVICE_TYPE_RING,
        ports=["in", "through"],
        parameters={
            "radius_um": radius_um,
            "neff": neff,
            "coupling": coupling,
            "loss_db_cm": loss_db_cm,
            "wavelength_um": wavelength_um,
        },
        s_params=s_params,
        verilog_a_code=code,
    )


def generate_modulator_verilog_a(
    module_name: str = "mzm_modulator_soi",
    v_pi: float = 2.0,
    insertion_loss_db: float = 0.5,
    efficiency: float = DEFAULT_MODULATOR_EFFICIENCY,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成 MZM 调制器 Verilog-A 模型（光电协同核心）。

    光功率-电压转换: P_out = η · V_in² · cos²(π·V/(2·V_π))
    来源: Chrostowski 2015 §8.4, Lumerical CML Compiler
      https://optics.ansys.com/hc/en-us/articles/49697869166611

    Args:
        module_name: 模块名。
        v_pi: 半波电压（V）。
        insertion_loss_db: 插损（dB）。
        efficiency: 调制器效率（W/V²）。
        wavelength_um: 参考波长。

    Returns:
        VerilogAModel 实例。
    """
    if v_pi <= 0:
        raise ValueError(f"V_pi 须 > 0，得到 {v_pi}")
    if efficiency < 0:
        raise ValueError(f"efficiency 须 >= 0，得到 {efficiency}")
    amp = 10.0 ** (-insertion_loss_db / 20.0)
    s_params: SDict = {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("out", "in"): np.array(amp, dtype=complex),
        ("in", "out"): np.array(amp, dtype=complex),
        ("out", "out"): np.array(0.0, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, out, rf_in);
  electrical in, out, rf_in;  // in/out 光学, rf_in 电学驱动
  parameter real v_pi = {v_pi:.6e} from (0:inf);     // 半波电压 (V)
  parameter real insertion_loss_db = {insertion_loss_db:.6e} from [0:inf);
  parameter real efficiency = {efficiency:.6e} from [0:inf);  // W/V^2
  real amp, modulation;

  analog begin
    amp = pow(10.0, -insertion_loss_db / 20.0);
    // MZM 传输: T = cos^2(pi*V/(2*V_pi))
    modulation = cos(`M_PI * V(rf_in) / (2.0 * v_pi));
    modulation = modulation * modulation;
    // 光功率输出 = efficiency * V_rf^2 * modulation
    V(out) <+ amp * sqrt(modulation) * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name,
        device_type=DEVICE_TYPE_MODULATOR,
        ports=["in", "out", "rf_in"],
        parameters={
            "v_pi": v_pi,
            "insertion_loss_db": insertion_loss_db,
            "efficiency": efficiency,
            "wavelength_um": wavelength_um,
        },
        s_params=s_params,
        verilog_a_code=code,
    )


def generate_detector_verilog_a(
    module_name: str = "photodetector_soi",
    responsivity: float = DEFAULT_DETECTOR_RESPONSIVITY,
    load_resistance: float = DEFAULT_LOAD_RESISTANCE_OHM,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成光电探测器 Verilog-A 模型（光电协同核心）。

    电压-光功率转换: V_out = √(R · P_in) = R · P_in · √(R_load)
    实际电路: I_photo = R · P_in, V_out = I_photo · R_load

    来源: Chrostowski 2015 §9.2, Lumerical CML Compiler
      https://optics.ansys.com/hc/en-us/articles/49697869166611

    Args:
        module_name: 模块名。
        responsivity: 响应度（A/W）。
        load_resistance: 负载电阻（Ω）。
        wavelength_um: 参考波长。

    Returns:
        VerilogAModel 实例。
    """
    if responsivity < 0:
        raise ValueError(f"响应度须 >= 0，得到 {responsivity}")
    if load_resistance <= 0:
        raise ValueError(f"负载电阻须 > 0，得到 {load_resistance}")
    s_params: SDict = {("in", "in"): np.array(0.0, dtype=complex)}
    code = f"""`include "disciplines.vams"
module {module_name} (in, rf_out);
  electrical in, rf_out;  // in 光学, rf_out 电学输出
  parameter real responsivity = {responsivity:.6e} from [0:inf);  // A/W
  parameter real load_resistance = {load_resistance:.6e} from (0:inf);  // Ohm
  real i_photo, v_out;

  analog begin
    // 光电流 I_photo = R * P_in (P_in 正比于 V(in)^2)
    i_photo = responsivity * V(in) * V(in);
    // 输出电压 V_out = I_photo * R_load
    v_out = i_photo * load_resistance;
    V(rf_out) <+ v_out;
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name,
        device_type=DEVICE_TYPE_DETECTOR,
        ports=["in", "rf_out"],
        parameters={
            "responsivity": responsivity,
            "load_resistance": load_resistance,
            "wavelength_um": wavelength_um,
        },
        s_params=s_params,
        verilog_a_code=code,
    )


def generate_mmi_2x2_verilog_a(
    module_name: str = "mmi_2x2_soi",
    insertion_loss_db: float = 0.4,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成 MMI 2x2 Verilog-A 模型（3dB 2x2 耦合器，cross 端 90° 相位超前）。

    来源: SiEPIC EBeam PDK ebeam_mmi_2x2; Chrostowski 2015 §3
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    if insertion_loss_db < 0:
        raise ValueError(f"插损须 >= 0，得到 {insertion_loss_db}")
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    cross = 1j * amp  # cross 端 90° 相位超前
    s_params: SDict = {
        ("in1", "in1"): np.array(0.0, dtype=complex),
        ("out1", "in1"): np.array(amp, dtype=complex),
        ("out2", "in1"): np.array(cross, dtype=complex),
        ("out1", "in2"): np.array(cross, dtype=complex),
        ("out2", "in2"): np.array(amp, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in1, in2, out1, out2);
  electrical in1, in2, out1, out2;
  parameter real insertion_loss_db = {insertion_loss_db:.6e} from [0:inf);
  real amp;
  analog begin
    amp = pow(10.0, -(insertion_loss_db + 3.0) / 20.0);
    V(out1) <+ amp * V(in1); V(out2) <+ amp * V(in1);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name, device_type=DEVICE_TYPE_MMI_2X2,
        ports=["in1", "in2", "out1", "out2"],
        parameters={"insertion_loss_db": insertion_loss_db, "wavelength_um": wavelength_um},
        s_params=s_params, verilog_a_code=code,
    )


def generate_grating_coupler_verilog_a(
    module_name: str = "grating_coupler_soi",
    coupling_efficiency: float = 0.6,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成光栅耦合器 Verilog-A 模型（光纤↔波导耦合，S21=√η）。

    来源: Chrostowski 2015 §6; Doerr 2011 IEEE PTL
      https://doi.org/10.1109/LPT.2011.2156100
    """
    if not 0.0 <= coupling_efficiency <= 1.0:
        raise ValueError(f"耦合效率须在 [0,1]，得到 {coupling_efficiency}")
    s21 = math.sqrt(coupling_efficiency)
    s_params: SDict = {
        ("fiber", "fiber"): np.array(0.0, dtype=complex),
        ("wg", "fiber"): np.array(s21, dtype=complex),
        ("fiber", "wg"): np.array(s21, dtype=complex),
        ("wg", "wg"): np.array(0.0, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (fiber, wg);
  electrical fiber, wg;
  parameter real coupling_efficiency = {coupling_efficiency:.6e} from [0:1];
  real s21;
  analog begin
    s21 = sqrt(coupling_efficiency); V(wg) <+ s21 * V(fiber);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name, device_type=DEVICE_TYPE_GRATING_COUPLER,
        ports=["fiber", "wg"],
        parameters={"coupling_efficiency": coupling_efficiency, "wavelength_um": wavelength_um},
        s_params=s_params, verilog_a_code=code,
    )


def generate_y_branch_verilog_a(
    module_name: str = "y_branch_soi",
    insertion_loss_db: float = 0.3,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成 Y 分支 Verilog-A 模型（1x2 功分器，对称 Y 形 50:50）。

    来源: SiEPIC EBeam PDK ebeam_y_1550; Chrostowski 2015 §3
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    if insertion_loss_db < 0:
        raise ValueError(f"插损须 >= 0，得到 {insertion_loss_db}")
    amp = 10.0 ** (-(insertion_loss_db + 3.0) / 20.0)
    s_params: SDict = {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("out1", "in"): np.array(amp, dtype=complex),
        ("out2", "in"): np.array(amp, dtype=complex),
        ("in", "out1"): np.array(amp, dtype=complex),
        ("in", "out2"): np.array(amp, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, out1, out2);
  electrical in, out1, out2;
  parameter real insertion_loss_db = {insertion_loss_db:.6e} from [0:inf);
  real amp;
  analog begin
    amp = pow(10.0, -(insertion_loss_db + 3.0) / 20.0);
    V(out1) <+ amp * V(in); V(out2) <+ amp * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name, device_type=DEVICE_TYPE_Y_BRANCH,
        ports=["in", "out1", "out2"],
        parameters={"insertion_loss_db": insertion_loss_db, "wavelength_um": wavelength_um},
        s_params=s_params, verilog_a_code=code,
    )


def generate_directional_coupler_verilog_a(
    module_name: str = "directional_coupler_soi",
    coupling_length_um: float = 10.0,
    kappa: float = 0.3,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成定向耦合器 Verilog-A 模型（through=cos(κL), cross=-j·sin(κL)）。

    来源: Yariv & Yeh, "Photonics", §10; Simphony directional_coupler
      https://simphonyphotonics.readthedocs.io/
    """
    if coupling_length_um < 0:
        raise ValueError(f"耦合长度须 >= 0，得到 {coupling_length_um}")
    if kappa < 0:
        raise ValueError(f"耦合系数须 >= 0，得到 {kappa}")
    kl = kappa * coupling_length_um
    s_through = math.cos(kl)
    s_cross = -1j * math.sin(kl)  # cross 端 -90° 相位（Yariv §10）
    s_params: SDict = {
        ("through", "in"): np.array(s_through, dtype=complex),
        ("cross", "in"): np.array(s_cross, dtype=complex),
        ("through", "coupled_in"): np.array(s_cross, dtype=complex),
        ("cross", "coupled_in"): np.array(s_through, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, through, coupled_in, cross);
  electrical in, through, coupled_in, cross;
  parameter real coupling_length = {coupling_length_um:.6e} from [0:inf);
  parameter real kappa = {kappa:.6e} from [0:inf);
  real kl;
  analog begin
    kl = kappa * coupling_length;
    V(through) <+ cos(kl) * V(in); V(cross) <+ -sin(kl) * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name, device_type=DEVICE_TYPE_DIRECTIONAL_COUPLER,
        ports=["in", "through", "coupled_in", "cross"],
        parameters={"coupling_length_um": coupling_length_um, "kappa": kappa, "wavelength_um": wavelength_um},
        s_params=s_params, verilog_a_code=code,
    )


def generate_phase_shifter_verilog_a(
    module_name: str = "phase_shifter_soi",
    delta_n_eff: float = 1e-3,
    length_um: float = 100.0,
    wavelength_um: float = DEFAULT_WAVELENGTH_UM,
) -> VerilogAModel:
    """生成移相器 Verilog-A 模型（φ=(2π/λ)·Δn_eff·L，S21=exp(jφ)）。

    来源: Chrostowski 2015 §8.2; Soref & Bennett 1987 等离子色散
      https://doi.org/10.1109/JQE.1987.1073206
    """
    if length_um < 0:
        raise ValueError(f"长度须 >= 0，得到 {length_um}")
    phi = 2.0 * math.pi * delta_n_eff * length_um / wavelength_um
    s21 = np.exp(1j * phi)
    s_params: SDict = {
        ("in", "in"): np.array(0.0, dtype=complex),
        ("out", "in"): np.array(s21, dtype=complex),
        ("in", "out"): np.array(s21, dtype=complex),
        ("out", "out"): np.array(0.0, dtype=complex),
    }
    code = f"""`include "disciplines.vams"
module {module_name} (in, out);
  electrical in, out;
  parameter real delta_n_eff = {delta_n_eff:.6e};
  parameter real length = {length_um:.6e} from [0:inf);
  parameter real wavelength = {wavelength_um:.6e} from (0:inf);
  analog begin
    V(out) <+ cos(2.0 * `M_PI * delta_n_eff * length / wavelength) * V(in);
  end
endmodule
"""
    return VerilogAModel(
        module_name=module_name, device_type=DEVICE_TYPE_PHASE_SHIFTER,
        ports=["in", "out"],
        parameters={"delta_n_eff": delta_n_eff, "length_um": length_um, "wavelength_um": wavelength_um},
        s_params=s_params, verilog_a_code=code,
    )


# 器件类型 → 生成器函数映射
_DEVICE_GENERATORS = {
    DEVICE_TYPE_WAVEGUIDE: generate_waveguide_verilog_a,
    DEVICE_TYPE_MMI_1X2: generate_mmi_1x2_verilog_a,
    DEVICE_TYPE_MMI_2X2: generate_mmi_2x2_verilog_a,
    DEVICE_TYPE_RING: generate_ring_verilog_a,
    DEVICE_TYPE_MODULATOR: generate_modulator_verilog_a,
    DEVICE_TYPE_DETECTOR: generate_detector_verilog_a,
    DEVICE_TYPE_GRATING_COUPLER: generate_grating_coupler_verilog_a,
    DEVICE_TYPE_Y_BRANCH: generate_y_branch_verilog_a,
    DEVICE_TYPE_DIRECTIONAL_COUPLER: generate_directional_coupler_verilog_a,
    DEVICE_TYPE_PHASE_SHIFTER: generate_phase_shifter_verilog_a,
}


def generate_verilog_a(
    device_type: str,
    module_name: str | None = None,
    **kwargs: Any,
) -> VerilogAModel:
    """根据器件类型生成 Verilog-A 模型（统一入口）。

    Args:
        device_type: 器件类型（DEVICE_TYPE_*）。
        module_name: 模块名（None 自动生成）。
        **kwargs: 器件参数。

    Returns:
        VerilogAModel 实例。

    Raises:
        ValueError: 器件类型不支持。
    """
    if device_type not in _DEVICE_GENERATORS:
        raise ValueError(
            f"不支持的器件类型 {device_type}，"
            f"支持: {sorted(_DEVICE_GENERATORS.keys())}"
        )
    if module_name is None:
        module_name = f"{device_type}_polaris"
    return _DEVICE_GENERATORS[device_type](module_name=module_name, **kwargs)


def save_verilog_a(model: VerilogAModel, output_path: str | Path) -> Path:
    """保存 Verilog-A 模型到文件。

    Args:
        model: VerilogAModel 实例。
        output_path: 输出文件路径（.va 扩展名）。

    Returns:
        保存的文件路径。
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.verilog_a_code, encoding="utf-8")
    return path


__all__ = [
    "SDict",
    "VerilogAModel",
    "generate_detector_verilog_a",
    "generate_directional_coupler_verilog_a",
    "generate_grating_coupler_verilog_a",
    "generate_mmi_1x2_verilog_a",
    "generate_mmi_2x2_verilog_a",
    "generate_modulator_verilog_a",
    "generate_phase_shifter_verilog_a",
    "generate_ring_verilog_a",
    "generate_verilog_a",
    "generate_waveguide_verilog_a",
    "generate_y_branch_verilog_a",
    "save_verilog_a",
]
