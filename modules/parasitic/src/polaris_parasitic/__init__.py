"""PoLaRIS 寄生提取与 Verilog-A 紧凑模型生成子模块（polaris-parasitic）。

从 v4 旧包 ``polaris.sim`` 迁移寄生参数提取（R/L/C/S/SPICE）与 Verilog-A 紧凑
模型生成（5+ 器件 + SPICE 联合仿真 + 光电协同可微分 *创新*）。R13: 不保留 v4
兼容路径，所有 imports 已切断对 ``polaris.sim.*`` 的依赖，纯 NumPy/SciPy CPU
实现（R04: 不参与 GPU）。

## 迁移来源

- 寄生提取 6 文件（R231-R235 + facade）:
  ``polaris.sim.parasitic_resistance`` / ``parasitic_capacitance`` /
  ``parasitic_inductance`` / ``parasitic_sparam`` / ``parasitic_spice`` /
  ``parasitic_advanced``
- Verilog-A 生成 4 文件（PAM4 部分已迁 polaris-pam4，此处迁移剩余）:
  ``polaris.sim.verilog_a_constants`` / ``verilog_a_models`` /
  ``verilog_a_spice`` / ``verilog_a_differentiable``
  （原任务描述中的 verilog_a_waveguide/mmi/modulator/ring/detector 5 个独立
  文件，在 v4 已整合于 verilog_a_models.py，见 操作记录.md 拆分记录）

## Input / Process / Output 三段式（IPO）

### 寄生参数提取（R231-R235）

- ParasiticResistor.extract:
  - I: sheet_resistance_ohm_sq=0.05 / length_um=100 / width_um=1 / temperature_c=25
  - P: R = RPSQ × L / W; R(T)=R0·(1+TC1·ΔT+TC2·ΔT²)（StarRC TC1/TC2 模型）
  - O: dict{resistance_ohm, n_squares, temp_factor}
- ParasiticCapacitor.extract_self:
  - I: eps_r=3.9 / metal_thickness_um=0.5 / dielectric_thickness_um=1.0 / L=100 / W=1
  - P: C_pp=ε·W·L/d + C_fringe=2π·ε·L/arcosh(2d/H+1)（Banerjee 圆柱模型）
  - O: dict{capacitance_ff, capacitance_area_ff, capacitance_fringe_ff}
- ParasiticInductor.extract_self:
  - I: metal_thickness_um=0.5 / length_um=100 / width_um=1
  - P: L_self=μ0·L/(2π)·[ln(2L/(W+H))+0.5+(W+H)/(6L)]（Rosa 1908）
  - O: dict{inductance_ph}
- ParasiticSParam.compute_s_params:
  - I: frequencies_ghz=[1,10] / R=1 / L=10 / C=1 / z0=50
  - P: π 型网络 ABCD → S（Pozar §4.4）；无源/互易验证
  - O: (N,2,2) complex ndarray
- SpiceNetlistWriter.to_string:
  - I: 节点 + R/L/C + TC1/TC2
  - P: 生成 .subckt 网表（StarRC DSPF 语法）
  - O: SPICE 网表字符串
- AdvancedParasiticExtractor.extract_all:
  - I: length_um / width_um / temperature_c
  - P: 一站式综合 R231-R235
  - O: dict{resistance, capacitance, inductance}

### Verilog-A 紧凑模型生成（5+ 器件）

- generate_waveguide_verilog_a:
  - I: length_um=100 / neff=2.4 / ng=4.0 / loss_db_cm=0.5 / wavelength_um=1.55
  - P: S21=exp(-α·L/2)·exp(j·2π·neff·L/λ)（Simphony waveguide）
  - O: VerilogAModel（含 .va 源代码）
- generate_mmi_1x2_verilog_a:
  - I: insertion_loss_db=0.4 / wavelength_um=1.55
  - P: 3dB 分束 + 插损（SiEPIC EBeam PDK）
  - O: VerilogAModel
- generate_ring_verilog_a:
  - I: radius_um=10 / neff=2.4 / coupling=0.01 / loss_db_cm=0.1
  - P: T=(t-a·e^{jφ})/(1-t·a·e^{jφ})（SiPANN ring, Yariv 1997）
  - O: VerilogAModel
- generate_modulator_verilog_a:
  - I: v_pi=2.0 / insertion_loss_db=0.5 / efficiency=0.1
  - P: P_out=η·V²·cos²(π·V/(2·V_π))（Chrostowski 2015 §8.4）
  - O: VerilogAModel
- generate_detector_verilog_a:
  - I: responsivity=1.0 / load_resistance=50 / wavelength_um=1.55
  - P: I_photo=R·P_in, V_out=I_photo·R_load（Chrostowski 2015 §9.2）
  - O: VerilogAModel
- generate_verilog_a: 统一入口（按 device_type 分发到上述生成器）

### SPICE 联合仿真（Ngspice）

- generate_spice_netlist:
  - I: models 列表 + SPICESimulationConfig + input_signal="pulse"
  - P: 生成 Ngspice 兼容网表（含 .include/.tran）
  - O: SPICE 网表字符串
- run_ngspice_cosimulation:
  - I: netlist 字符串 + config
  - P: 调用 ngspice -b -r rawfile → 解析真实仿真数据（禁止合成数据，R03）
  - O: CoSimulationResult{time_points, voltage, optical_power}
  - Raises: Ngspice 不可用时 FileNotFoundError（R03 无 fall-back）

### 光电协同可微分仿真（*创新*）

- DifferentiableOptoElectricalModel.forward:
  - I: voltage_in ndarray / modulator_length=100
  - P: P_opt=η·V²·exp(-α·L) → I_photo=R·P_opt → V_out=I_photo·R_load
  - O: dict{optical_power, detector_current, output_voltage}
- DifferentiableOptoElectricalModel.gradient:
  - I: voltage_in / modulator_length / eps=1e-6
  - P: 有限差分 ∂V_out/∂V_in, ∂V_out/∂L_mod（*创新*: 梯度跨光电边界）
  - O: dict{dV_out_dV_in, dV_out_dL_mod}
- optimize_opto_electrical_link:
  - I: target_output_voltage=0.5 / initial_voltage=1.0 / n_iterations=10
  - P: 梯度下降联合优化 V_in 与 L_mod（Lumerical 不支持此联合优化，*创新*）
  - O: dict{final_v_in, final_l_mod, final_v_out, history, converged}

## 设计原则

- 纯 NumPy/SciPy + math（R04: 不参与 GPU，禁止 CuPy/CUDA/ROCm）
- 禁止 fall-back（R03）: 非法参数 raise；Ngspice 不可用 raise（不合成数据）
- R05 Bug 必修: 0 个 TODO/FIXME/HACK 残留
- R13 不保留 v4 兼容: 切断所有 ``polaris.sim.*`` 依赖，SDict 本地定义
- 质量门禁: 函数≤80行 / 文件≤800行 / 圈复杂度≤15

## 来源（R02 学术诚信，≥5 个文献 URL）

- Synopsys StarRC Datasheet（RLCK 寄生提取，TC1/TC2）
  https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf
- Synopsys StarRC Resistance Extraction（RPSQ × L/W 片电阻公式）
  https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html
- Cadence Quantus QRC 3D 场求解
  https://en.eeworld.com.cn/mp/Cadence/a340059.jspx
- Ansys Lumerical CML Compiler（Verilog-A 紧凑模型）
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Verilog-AMS LRM (Language Reference Manual)
  https://www.accellera.org/downloads/standards/v-ams
- Ngspice 用户手册（SPICE 联合仿真 + rawfile 格式）
  https://ngspice.sourceforge.io/docs.html
- Pozar, "Microwave Engineering", 4th ed., §4（ABCD↔S 变换）
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §2.3/§8/§9
- Rosa, "Self and Mutual Inductances of Linear Conductors", NIST BS 1908
  https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf
- Wheeler, "Inductance Formulas for Single-Layer Coils", Proc. IRE 1928
  https://ieeexplore.ieee.org/document/1654891
- SiPANN ring_resonator
  https://sipann.readthedocs.io/en/latest/models.html
- Simphony waveguide 模型
  https://simphonyphotonics.readthedocs.io/
- SiEPIC EBeam PDK
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- JAX 自动微分框架（*创新* 可微分理论支持）
  https://jax.readthedocs.io/
- PyTorch autograd 设计参考
  https://pytorch.org/docs/stable/autograd.html
"""

from __future__ import annotations

from polaris_parasitic.advanced import (
    AdvancedParasiticExtractor,
    ParasiticCapacitor,
    ParasiticInductor,
    ParasiticResistor,
    ParasiticSParam,
    SpiceNetlistWriter,
)
from polaris_parasitic.constants import (
    DEFAULT_DETECTOR_RESPONSIVITY,
    DEFAULT_LOAD_RESISTANCE_OHM,
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_OPTICAL_TIMESTEP_S,
    DEFAULT_SPICE_TIMESTEP_S,
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
from polaris_parasitic.verilog_a_differentiable import (
    DifferentiableOptoElectricalModel,
    optimize_opto_electrical_link,
)
from polaris_parasitic.verilog_a_models import (
    SDict,
    VerilogAModel,
    generate_detector_verilog_a,
    generate_directional_coupler_verilog_a,
    generate_grating_coupler_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_mmi_2x2_verilog_a,
    generate_modulator_verilog_a,
    generate_phase_shifter_verilog_a,
    generate_ring_verilog_a,
    generate_verilog_a,
    generate_waveguide_verilog_a,
    generate_y_branch_verilog_a,
    save_verilog_a,
)
from polaris_parasitic.verilog_a_spice import (
    CoSimulationResult,
    SPICESimulationConfig,
    generate_spice_netlist,
    run_ngspice_cosimulation,
    run_photoelectric_cosim,
)

__version__ = "5.0.0"

__all__ = [
    # 版本
    "__version__",
    # 寄生提取（R231-R235 + facade）
    "AdvancedParasiticExtractor",
    "ParasiticCapacitor",
    "ParasiticInductor",
    "ParasiticResistor",
    "ParasiticSParam",
    "SpiceNetlistWriter",
    # Verilog-A 常量与器件类型
    "DEFAULT_DETECTOR_RESPONSIVITY",
    "DEFAULT_LOAD_RESISTANCE_OHM",
    "DEFAULT_MODULATOR_EFFICIENCY",
    "DEFAULT_OPTICAL_TIMESTEP_S",
    "DEFAULT_SPICE_TIMESTEP_S",
    "DEFAULT_WAVELENGTH_UM",
    "DEVICE_TYPE_DETECTOR",
    "DEVICE_TYPE_DIRECTIONAL_COUPLER",
    "DEVICE_TYPE_GRATING_COUPLER",
    "DEVICE_TYPE_MMI_1X2",
    "DEVICE_TYPE_MMI_2X2",
    "DEVICE_TYPE_MODULATOR",
    "DEVICE_TYPE_PHASE_SHIFTER",
    "DEVICE_TYPE_RING",
    "DEVICE_TYPE_WAVEGUIDE",
    "DEVICE_TYPE_Y_BRANCH",
    "SUPPORTED_DEVICE_TYPES",
    # Verilog-A 模型生成（10 器件，与 SUPPORTED_DEVICE_TYPES 一致）
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
    # SPICE 联合仿真（Ngspice + 自研 MNA SPICE 桥接）
    "CoSimulationResult",
    "SPICESimulationConfig",
    "generate_spice_netlist",
    "run_ngspice_cosimulation",
    "run_photoelectric_cosim",
    # 光电协同可微分（*创新*）
    "DifferentiableOptoElectricalModel",
    "optimize_opto_electrical_link",
]
