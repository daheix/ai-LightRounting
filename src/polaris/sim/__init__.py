"""光子电路仿真模块（精确模型数据库与频率域仿真）。

目录结构：
    polaris/sim/
        __init__.py        — 包入口，统一导出
        types.py           — S 参数类型定义（SDict, ModelFunc）
        models.py          — 基础器件 S 参数模型（规则3复刻 SiPANN）
        touchstone.py      — Touchstone .s2p/.snp 文件加载/保存
        cascade.py         — S 参数级联器（子网络增长算法，规则3复刻 SAX）
        simulator.py       — CircuitSimulator 电路级频率域仿真器
        device_models.py   — 51 器件到 S 参数模型映射

集成方式（遵守 project_rules.md 规则 2/3）：
1. 直接集成 simphony + sax（规则 2）
2. SiPANN 安装失败 → 纯 numpy 100% 复刻（规则 3）
3. Touchstone .s2p/.snp 文件支持

来源:
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/
- SiPANN: https://sipann.readthedocs.io/
- Touchstone: https://en.wikipedia.org/wiki/Touchstone_file
"""

from polaris.sim.cascade import cascade_circuit
from polaris.sim.models import (
    RingParams,
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.simulator import (
    CircuitSimulator,
    WavelengthRange,
    default_models,
    simphony_models,
)
from polaris.sim.touchstone import load_touchstone, save_touchstone
from polaris.sim.types import ModelFunc, SDict

__all__ = [
    # 类型
    "SDict",
    "ModelFunc",
    # 参数集合（规则 4：降低函数参数个数）
    "RingParams",
    "WavelengthRange",
    # 基础器件 S 参数模型
    "waveguide_s",
    "y_branch_s",
    "directional_coupler_s",
    "ring_resonator_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "crossing_s",
    "terminator_s",
    "phase_shifter_s",
    # Touchstone 文件
    "load_touchstone",
    "save_touchstone",
    # 级联器
    "cascade_circuit",
    # 仿真器
    "CircuitSimulator",
    "default_models",
    "simphony_models",
]
