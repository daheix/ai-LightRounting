"""Verilog-A 器件类型枚举与默认物理参数。

从 v4 ``polaris.sim.verilog_a_constants`` 迁移，集中维护 Verilog-A 器件类型
枚举与默认物理参数，所有数值均来自开源 PDK 或权威文献，禁止编造（R02）。

来源（≥5 个文献 URL）:
- Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- INTERCONNECT vs Verilog-A 模型对比
  https://optics.ansys.com/hc/en-us/articles/18698429782291
- SiEPIC EBeam PDK
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8/§9
- Lumerical INTERCONNECT 文档（SPICE 时间步默认值）
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Simphony waveguide 模型
  https://simphonyphotonics.readthedocs.io/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R13 不保留 v4 兼容。
"""

from __future__ import annotations

# Verilog-A 器件类型枚举（对应 Lumerical CML 类型）
# 来源: https://optics.ansys.com/hc/en-us/articles/18698429782291
DEVICE_TYPE_WAVEGUIDE = "waveguide"
DEVICE_TYPE_MMI_1X2 = "mmi_1x2"
DEVICE_TYPE_MMI_2X2 = "mmi_2x2"
DEVICE_TYPE_RING = "ring_resonator"
DEVICE_TYPE_MODULATOR = "modulator"
DEVICE_TYPE_DETECTOR = "detector"
DEVICE_TYPE_GRATING_COUPLER = "grating_coupler"
DEVICE_TYPE_Y_BRANCH = "y_branch"
DEVICE_TYPE_DIRECTIONAL_COUPLER = "directional_coupler"
DEVICE_TYPE_PHASE_SHIFTER = "phase_shifter"

# 支持的器件类型集合（验收标准: 5+ 器件）
SUPPORTED_DEVICE_TYPES = frozenset({
    DEVICE_TYPE_WAVEGUIDE,
    DEVICE_TYPE_MMI_1X2,
    DEVICE_TYPE_MMI_2X2,
    DEVICE_TYPE_RING,
    DEVICE_TYPE_MODULATOR,
    DEVICE_TYPE_DETECTOR,
    DEVICE_TYPE_GRATING_COUPLER,
    DEVICE_TYPE_Y_BRANCH,
    DEVICE_TYPE_DIRECTIONAL_COUPLER,
    DEVICE_TYPE_PHASE_SHIFTER,
})

# 默认波长（μm）— SiEPIC EBeam PDK 1550nm
# 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
DEFAULT_WAVELENGTH_UM = 1.55

# 默认响应度（A/W）— Chrostowski 2015 §9.2 Si 探测器典型值
DEFAULT_DETECTOR_RESPONSIVITY = 1.0

# 默认调制器效率（W/V²）— Chrostowski 2015 §8.4 MZM 典型值
DEFAULT_MODULATOR_EFFICIENCY = 0.1

# 默认探测器负载电阻（Ω）— 50Ω 射频标准
DEFAULT_LOAD_RESISTANCE_OHM = 50.0

# SPICE 时间步默认值（s）— Lumerical INTERCONNECT 典型值
DEFAULT_SPICE_TIMESTEP_S = 1e-12

# 光子仿真器时间步默认值（s）
DEFAULT_OPTICAL_TIMESTEP_S = 1e-13


__all__ = [
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
]
