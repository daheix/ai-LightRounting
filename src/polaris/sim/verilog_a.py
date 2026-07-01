"""R35: Verilog-A 光电协同紧凑模型生成器 + SPICE 联合仿真接口。

实现 Ansys Lumerical CML Compiler 的核心能力：
- 从 S 参数字典生成 Verilog-A 紧凑模型文件
- 支持 5+ 器件（波导/MMI/环/调制器/探测器）
- Ngspice 联合仿真接口（时间步同步 + 数据交换）
- PAM4 收发机眼图 + BER 分析
- 光电协同可微分仿真（*创新*）

核心公式:
- 光功率 ↔ 电压转换: P_out = η·V_in², V_out = √(R·P_in)
- SPICE 时间步同步: Δt_sync = max(Δt_SPICE, Δt_optical)

来源:
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Verilog-A PAM4 transceiver
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- INTERCONNECT vs Verilog-A 模型对比
  https://optics.ansys.com/hc/en-us/articles/18698429782291
- Verilog-AMS LRM (Language Reference Manual)
  https://www.accellera.org/downloads/standards/v-ams
- Ngspice 用户手册
  https://ngspice.sourceforge.io/docs.html
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8/§9

拆分说明（facade 模式）:
本模块原为 1392 行，已按功能拆分为 5 个子模块（每个 ≤800 行），
保持外部 ``from polaris.sim.verilog_a import X`` 路径不变。
本文件仅作 re-export 入口，所有实现见子模块：
- `verilog_a_constants`: 常量与器件类型映射
- `verilog_a_models`: Verilog-A 模型生成器
- `verilog_a_spice`: SPICE 联合仿真接口（Ngspice）
- `verilog_a_pam4`: PAM4 眼图 + BER 分析
- `verilog_a_differentiable`: 光电协同可微分仿真（*创新*）

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：见上方创新点列表
  支持理论：2015, §8/§。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

"""

from __future__ import annotations

# Facade re-export：保持外部 ``from polaris.sim.verilog_a import X`` 路径不变。
# noqa: F401 由 facade 设计决定，以下导入均为对外公开 API。
from polaris.sim.verilog_a_constants import (  # noqa: F401
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
from polaris.sim.verilog_a_differentiable import (  # noqa: F401
    DifferentiableOptoElectricalModel,
    optimize_opto_electrical_link,
)
from polaris.sim.verilog_a_models import (  # noqa: F401
    VerilogAModel,
    generate_detector_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_modulator_verilog_a,
    generate_ring_verilog_a,
    generate_verilog_a,
    generate_waveguide_verilog_a,
    save_verilog_a,
)
from polaris.sim.verilog_a_pam4 import (  # noqa: F401
    PAM4Signal,
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
)
from polaris.sim.verilog_a_spice import (  # noqa: F401
    CoSimulationResult,
    SPICESimulationConfig,
    generate_spice_netlist,
    run_ngspice_cosimulation,
)

__all__ = [
    # 常量
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
    # Verilog-A 模型
    "VerilogAModel",
    "generate_detector_verilog_a",
    "generate_mmi_1x2_verilog_a",
    "generate_modulator_verilog_a",
    "generate_ring_verilog_a",
    "generate_verilog_a",
    "generate_waveguide_verilog_a",
    "save_verilog_a",
    # SPICE 联合仿真
    "CoSimulationResult",
    "SPICESimulationConfig",
    "generate_spice_netlist",
    "run_ngspice_cosimulation",
    # PAM4 眼图 + BER
    "PAM4Signal",
    "compute_ber",
    "compute_eye_diagram",
    "compute_snr_db",
    "generate_pam4_signal",
    # 光电协同可微分（*创新*）
    "DifferentiableOptoElectricalModel",
    "optimize_opto_electrical_link",
]
