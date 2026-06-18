"""光子电路仿真模块（精确模型数据库与频率域仿真）。

集成方式（遵守 project_rules.md 规则 2/3）：
1. 直接集成 simphony + sax（规则 2）
2. SiPANN 安装失败 → 纯 numpy 100% 复刻（规则 3）
3. Touchstone .s2p/.snp 文件支持

来源:
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/
- SiPANN: https://sipann.readthedocs.io/
"""

from polaris.sim.smodels import (
    CircuitSimulator,
    ModelFunc,
    SDict,
    cascade_circuit,
    crossing_s,
    default_models,
    directional_coupler_s,
    grating_coupler_s,
    load_touchstone,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    save_touchstone,
    simphony_models,
    terminator_s,
    waveguide_s,
    y_branch_s,
)

__all__ = [
    "CircuitSimulator",
    "SDict",
    "ModelFunc",
    "cascade_circuit",
    "crossing_s",
    "default_models",
    "directional_coupler_s",
    "grating_coupler_s",
    "load_touchstone",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "phase_shifter_s",
    "ring_resonator_s",
    "save_touchstone",
    "simphony_models",
    "terminator_s",
    "waveguide_s",
    "y_branch_s",
]
