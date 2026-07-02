"""polaris-verify-advanced — PoLaRIS 高级验证子模块。

从 v4 旧包 ``polaris.sim`` + ``polaris.verify`` + ``polaris.verification`` 迁移
高级验证功能：图同构 LVS、层次化 DRC、方程驱动 DRC、KLayout 桥接、
Calibre xACT 寄生提取、Calibre LFD 光刻友好设计、曲线感知 DRC 规则集。

## IPO 三段式说明

### Input（输入）
- GDS 版图文件（``.gds``）或 Layout 对象（层 → 多边形列表）
- 参考网表（PhotonicsNetlist / ExtractedNetlist）
- DRC 规则集（DRCRule / CurvilinearDRCRule / EqDRCRule 列表）
- 物理层规格（LayerSpec，用于寄生提取）
- LFD 光刻规则（LithoRule 列表）

### Process（处理）
- 图同构 LVS 比对（VF2 算法，NetworkX GraphMatcher）
- 层次化 DRC（BVH 加速 + 自适应行分块，OpenDRC 论文）
- 方程驱动 DRC（eqDRC，对齐 Siemens Calibre eqDRC）
- KLayout DRC runset 桥接（width/space/notch/enclose/area/density/via）
- Calibre xACT 寄生 RC 提取（R=ρL/(wh), C=C_pp+C_fringe+C_coupling）
- Calibre LFD 光刻友好设计检查（PV-band 热点检测 + DVI 评分）
- 曲线感知 DRC（18 类规则 + 8 类扩展规则）
- DRC 规则集预设（SiEPIC EBeam SOI/SiN、Generic conservative）

### Output（输出）
- LVS 比对报告（PhotonicsLVSReport / StructuredErrorReport）
- DRC 违规列表（Violation / DRCViolation / EqDRCViolation / DRCViolation18）
- 寄生参数网络（ParasiticNet，含 SPICE 网表输出）
- 光刻友好度报告（LithoReport，含 0-100 评分）
- DRC 检查报告（DRCResult / 字典报告）

## 学术依据（≥5 文献 URL，R02 学术诚信）

1. He et al. 2023, "OpenDRC: A Linear Programming Based Hierarchical DRC Engine",
   DAC 2023, https://doi.org/10.1109/DAC56929.2023.10247734
2. Siemens Calibre eqDRC:
   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
3. Siemens Calibre xACT 寄生提取: https://eda.sw.siemens.com/en-US/calibre/
4. Wang et al., SPIE 6349, 63492Z (2006), Calibre LFD PV-band,
   doi:10.1117/12.685727, https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/
5. Banerjee ECE 225 UCSB, 寄生电容公式,
   https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
6. Shomalnasab et al. 2013, 侧壁耦合电容,
   https://www.sci-hub.ru/download/2024/3471/fbecce358e5bb9764190173c0142c377/shomalnasab2013.pdf
7. SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
8. Synopsys OptoDesigner DRC Module:
   https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
9. KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
10. Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯 NumPy/SciPy/NetworkX）/
      R05 无 TODO / R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

# --- 图同构 LVS ---
from .graph_lvs import (
    EquivalenceHints,
    GraphIsomorphismLVSComparer,
    NetlistEdge,
    NetlistNode,
    PhotonicsLVSReport,
    PhotonicsNetlist,
    run_graph_lvs,
    verify_port_orientation,
    verify_waveguide_length,
)

# --- LVS 进阶类型与连接性 ---
from .lvs_advanced_types import (
    ConnectivityReport,
    DeviceMatchResult,
    DirectionalCouplerParams,
    LocatedError,
    MMIParams,
    ParamMismatch,
    RingResonatorParams,
    StructuredErrorReport,
    ToleranceSpec,
    WaveguideParams,
)
from .lvs_advanced_matching import match_devices_with_tolerance
from .lvs_advanced_connectivity import extract_connectivity
from .lvs_advanced_error_report import generate_structured_error_report

# --- 内化依赖（类型 + 层映射）---
from ._types import (
    ExtractedNetlist,
    LVSMismatchType,
    Violation,
    ViolationType,
)
from ._layer_map import (
    GDSLayer,
    POLARIS_GDS_LAYER_MAP,
    get_layer_tuple,
)

# --- 方程驱动 DRC ---
from .eqdrc import (
    CurvilinearLVS,
    DRCReportGenerator,
    EqDRCRule,
    EqDRCViolation,
    EqDRCEngine,
    FoundryDRCCertifier,
    FoundryDRCRunset,
)

# --- KLayout DRC 桥接 ---
from .klayout_drc import (
    DRCCheckType,
    DRCResult,
    DRCRule,
    KLayoutDRCRunner,
    LayoutContext,
    SIEPIC_EBEAM_DRC_RUNSET,
    run_klayout_drc,
)

# --- 层次化 DRC ---
from .hierarchical_drc import (
    BVH,
    BVHNode,
    DRCViolation,
    HierarchicalDRC,
    RowPartition,
    run_hierarchical_drc,
)

# --- Calibre xACT 寄生提取 ---
from .calibre_interface import (
    EPSILON_0,
    EPS_R_SI,
    EPS_R_SIO2,
    EPS_R_SIN3,
    LayerSpec,
    Layout,
    ParasiticElement,
    ParasiticExtractor,
    ParasiticNet,
    RHO_AL,
    RHO_CU,
    RHO_TIN,
    RHO_W,
)

# --- Calibre LFD 光刻友好设计 ---
from .calibre_lfd import (
    LithoFriendlyChecker,
    LithoHotspot,
    LithoReport,
    LithoRule,
)

# --- 曲线感知 DRC ---
from ._drc_rules import (
    CurvilinearDRCRule,
    DRCRuleCategory,
    DRCViolation18,
)
from .drc_curvilinear_18rules import CurvilinearDRCEngine
from .drc_ruleset_presets import (
    GENERIC_CONSERVATIVE_RULESET,
    SIEPIC_EBEAM_SIN_RULESET,
    SIEPIC_EBEAM_SOI_RULESET,
    CustomRuleSetBuilder,
    get_preset_ruleset,
    list_preset_rulesets,
    validate_ruleset,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    # 图同构 LVS
    "EquivalenceHints",
    "GraphIsomorphismLVSComparer",
    "NetlistEdge",
    "NetlistNode",
    "PhotonicsLVSReport",
    "PhotonicsNetlist",
    "run_graph_lvs",
    "verify_port_orientation",
    "verify_waveguide_length",
    # LVS 进阶
    "ConnectivityReport",
    "DeviceMatchResult",
    "DirectionalCouplerParams",
    "LocatedError",
    "MMIParams",
    "ParamMismatch",
    "RingResonatorParams",
    "StructuredErrorReport",
    "ToleranceSpec",
    "WaveguideParams",
    "match_devices_with_tolerance",
    "extract_connectivity",
    "generate_structured_error_report",
    # 内化类型
    "ExtractedNetlist",
    "LVSMismatchType",
    "Violation",
    "ViolationType",
    "GDSLayer",
    "POLARIS_GDS_LAYER_MAP",
    "get_layer_tuple",
    # 方程驱动 DRC
    "CurvilinearLVS",
    "DRCReportGenerator",
    "EqDRCRule",
    "EqDRCViolation",
    "EqDRCEngine",
    "FoundryDRCCertifier",
    "FoundryDRCRunset",
    # KLayout DRC
    "DRCCheckType",
    "DRCResult",
    "DRCRule",
    "KLayoutDRCRunner",
    "LayoutContext",
    "SIEPIC_EBEAM_DRC_RUNSET",
    "run_klayout_drc",
    # 层次化 DRC
    "BVH",
    "BVHNode",
    "DRCViolation",
    "HierarchicalDRC",
    "RowPartition",
    "run_hierarchical_drc",
    # Calibre xACT
    "EPSILON_0",
    "EPS_R_SI",
    "EPS_R_SIO2",
    "EPS_R_SIN3",
    "LayerSpec",
    "Layout",
    "ParasiticElement",
    "ParasiticExtractor",
    "ParasiticNet",
    "RHO_AL",
    "RHO_CU",
    "RHO_TIN",
    "RHO_W",
    # Calibre LFD
    "LithoFriendlyChecker",
    "LithoHotspot",
    "LithoReport",
    "LithoRule",
    # 曲线感知 DRC
    "CurvilinearDRCRule",
    "DRCRuleCategory",
    "DRCViolation18",
    "CurvilinearDRCEngine",
    "GENERIC_CONSERVATIVE_RULESET",
    "SIEPIC_EBEAM_SIN_RULESET",
    "SIEPIC_EBEAM_SOI_RULESET",
    "CustomRuleSetBuilder",
    "get_preset_ruleset",
    "list_preset_rulesets",
    "validate_ruleset",
]
