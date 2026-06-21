"""pyCopySiPANN — SiPANN 纯 Python 100% 复刻（规则 3/21）。

复刻 SiPANN 的硅光器件 S 参数模型，包括波导/Y 分支/定向耦合器/
环谐振器/MMI/光栅耦合器/交叉/终端/相移器。

原工具: SiPANN https://sipann.readthedocs.io/ (MIT)
复刻位置: src/polaris/sim/models.py
复刻模型: 10 个 S 参数模型

版本历史: 见 VERSION.md
- v1.0.0 (2026-06-21): 100% 复刻完成（原工具因 Python 3.14 无 wheel，用文档示例验证）

来源:
- SiPANN: https://github.com/contagon/SiPANN
- Hammond et al., "Accelerating silicon photonic parameter extraction
  using artificial neural networks", OSA Continuum 2, 1964-1973 (2019)
"""

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

__version__ = "1.0.0"

__all__ = [
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
    "RingParams",
    "__version__",
]
