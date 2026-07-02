"""polaris-lumerical: PoLaRIS 商业软件集成子模块。

从 v4 旧包 sim/ 迁移 Lumerical/Tidy3D/MEEP 多后端 + 光电协同 + CML Compiler，
提取核心 API 定义与调用逻辑，删除跨模块依赖（R13 不保留 v4 兼容）。

IPO: Input(几何/物理/仿真配置/S参数) → Process(FDTD/MODE/CHARGE/INTERCONNECT/
Tidy3D/MEEP/光电协同/CML编译) → Output(n_eff/depletion_width/BER/s_params/
passivity_ok)。

学术依据（R02 ≥5 文献 URL，完整列表见各子模块 docstring）:
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Soref & Bennett 1987 IEEE JQE https://doi.org/10.1109/JQE.1987.1073206
- Marcatili 1969 Bell Syst Tech J https://doi.org/10.1002/j.1538-7305.1969.tb01163.x
- Sze & Ng 2007 Physics of Semiconductor Devices §3.4-3.5
- Agrawal 2010 Fiber-Optic Communication Systems §4.5-4.7
- ITU-T O.150 PRBS https://www.itu.int/rec/T-REC-O.150
- Mur 1981 IEEE EMC https://doi.org/10.1109/TEMC.1981.303970
- Chrostowski 2015 Silicon Photonics Design Cambridge
- Ansys Lumerical https://optics.ansys.com/hc/en-us
- Tidy3D https://docs.flexcompute.com/projects/tidy3d/en/latest/
- MEEP https://meep.readthedocs.io/en/latest/

设计原则: R02 学术诚信 / R03 禁止 fall-back(商业软件未安装即 raise) /
R04 纯 NumPy CPU(GPUFDTDEngine 历史命名，实际 CPU) / R05 无 TODO /
R13 不保留 v4 兼容 / 函数≤80行 / 文件≤800行。

模块结构（R05 文件≤800行，按职责拆分）:
- _lumerical.py: Lumerical FDTD3D/MODE/CHARGE/INTERCONNECT + Integration
- _backends.py: Tidy3D/GPUFDTD/MEEP/FDTD Simulator + SOI 解析模型
- _cosim.py: Photoelectric CoSim (MZM + PD + Laser)
- _cml.py: CML Compiler (S 参数 + 无源性/互易性诊断)
"""

from __future__ import annotations

# 物理常数（CODATA 2018 / SiEPIC EBeam PDK，re-export 保持向后兼容）
from ._lumerical import (
    _C0, _Q, _KB, _EPS0, _EPS_SI, _N_SILICON, _N_SIO2,
    _SOREF_DN_AN, _SOREF_DN_AP,
)
from ._backends import (
    _N_AIR, SOI_N_EFF_CENTER, SOI_DN_D_LAMBDA, SOI_ALPHA_DB_PER_UM, DB_TO_NP,
)
from ._cml import PASSIVITY_TOL, RECIPROCITY_TOL

# 光电协同常数 (CODATA 2018)
ELECTRON_CHARGE = 1.602176634e-19
PLANCK_CONSTANT = 6.62607015e-34
SPEED_OF_LIGHT = 2.99792458e8

# 章节1-5: Lumerical FDTD3D/MODE/CHARGE/INTERCONNECT + Integration
from ._lumerical import (
    FDTD3DConfig, LumericalFDTDBackend, courant_dt_3d,
    ModeConfig, ModeSolver,
    CHARGEConfig, CHARGESimulator,
    INTERCONNECTConfig, INTERCONNECTSimulator,
    LumericalIntegration,
)

# 章节6-9: Tidy3D/GPUFDTD/MEEP/FDTD Simulator + SOI 解析模型
from ._backends import (
    Tidy3DConfig, Tidy3DBackend,
    GPUFDTDConfig, GPUFDTDEngine,
    MeepAvailability, check_meep_availability,
    MeepSimulationConfig, MeepAdjointResult, MeepAdjointBackend,
    FDTDBackend, FDTDConfig, FDTDResult,
    is_meep_available, is_tidy3d_available, compute_soi_waveguide_sparams,
)

# 章节10: Photoelectric CoSim
from ._cosim import (
    CoSimConfig, ModulatorSpec, PhotodetectorSpec, LaserSpec,
    PhotoelectricCoSim,
)

# 章节11: CML Compiler
from ._cml import (
    CMLMetadata, CMLComponent, CMLDiagnostics, CMLCompiler,
)


__version__ = "5.0.0"

__all__ = [
    # 常数
    "_C0", "_Q", "_KB", "_EPS0", "_EPS_SI", "_N_SILICON", "_N_SIO2",
    "_N_AIR", "_SOREF_DN_AN", "_SOREF_DN_AP",
    "SOI_N_EFF_CENTER", "SOI_DN_D_LAMBDA", "SOI_ALPHA_DB_PER_UM", "DB_TO_NP",
    "PASSIVITY_TOL", "RECIPROCITY_TOL",
    "ELECTRON_CHARGE", "PLANCK_CONSTANT", "SPEED_OF_LIGHT",
    # Lumerical FDTD
    "FDTD3DConfig", "LumericalFDTDBackend", "courant_dt_3d",
    # Lumerical MODE
    "ModeConfig", "ModeSolver",
    # Lumerical CHARGE
    "CHARGEConfig", "CHARGESimulator",
    # Lumerical INTERCONNECT
    "INTERCONNECTConfig", "INTERCONNECTSimulator",
    # Lumerical Integration
    "LumericalIntegration",
    # Tidy3D
    "Tidy3DConfig", "Tidy3DBackend",
    # GPUFDTD (纯 NumPy CPU, R04 合规)
    "GPUFDTDConfig", "GPUFDTDEngine",
    # MEEP
    "MeepAdjointBackend", "MeepSimulationConfig", "MeepAdjointResult",
    "MeepAvailability", "check_meep_availability",
    # FDTD Simulator
    "FDTDBackend", "FDTDConfig", "FDTDResult",
    "is_meep_available", "is_tidy3d_available", "compute_soi_waveguide_sparams",
    # Photoelectric CoSim
    "CoSimConfig", "ModulatorSpec", "PhotodetectorSpec", "LaserSpec",
    "PhotoelectricCoSim",
    # CML Compiler
    "CMLMetadata", "CMLComponent", "CMLDiagnostics", "CMLCompiler",
]
