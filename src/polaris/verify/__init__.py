"""PoLaRIS 验证模块 —— 寄生效应提取 + 光刻友好设计。

对齐 Siemens Calibre xACT（寄生 RC 提取）与 Calibre LFD（光刻友好设计），
提供版图级寄生参数提取与光刻热点检测能力。

子模块:
    calibre_interface.py — Calibre xACT 寄生提取 + LFD 光刻友好设计接口

来源:
- Calibre xACT: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LFD: https://eda.sw.siemens.com/en-US/calibre/lfd/

参考文献：
[1] He Z, Yu B. OpenDRC: An open-source design rule checking engine with hierarchical GPU acceleration[C]//Design Automation Conference (DAC). 2023. https://www.cse.cuhk.edu.hk/~byu/papers/C172-DAC2023-OpenDRC.pdf
[2] Siemens EDA. Calibre nmLVS: Layout vs. Schematic verification[EB/OL]. 2024. https://www.siemens.com/en-us/products/ic/calibre-design/circuit-verification/nmlvs/
[3] KLayout. KLayout DRC basics[EB/OL]. 2024. https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
[4] KLayout. KLayout LVS compare[EB/OL]. 2024. https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
[5] NetworkX. NetworkX isomorphism VF2 algorithm[EB/OL]. 2024. https://networkx.org/documentation/networkx-3.3/_modules/networkx/algorithms/isomorphism/isomorphvf2.html
[6] Siemens EDA. Calibre xACT 3D: Accurate parasitic extraction[EB/OL]. 2024. https://eda.sw.siemens.com/en-US/calibre/
"""

from polaris.verify.calibre_interface import (
    Layout,
    LayerSpec,
    LithoFriendlyChecker,
    LithoHotspot,
    LithoReport,
    LithoRule,
    ParasiticElement,
    ParasiticExtractor,
    ParasiticNet,
)

__all__ = [
    "Layout",
    "LayerSpec",
    "LithoFriendlyChecker",
    "LithoHotspot",
    "LithoReport",
    "LithoRule",
    "ParasiticElement",
    "ParasiticExtractor",
    "ParasiticNet",
]
