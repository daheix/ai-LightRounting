"""PoLaRIS A09-FDTD 时域有限差分包（A09 §1）。

2D TEz FDTD 完整流水线：Yee leapfrog + CPML + TFSF + Drude ADE + DFT 监视器 + S 参数。

模块组成：
- yee_grid    : Yee 交错网格与 leapfrog 更新系数（Yee 1966）
- cpml        : CPML 复坐标拉伸吸收边界（Roden & Gedney 2000）
- sources     : 时域源波形与偶极子软注入（Taflove 2005 §5.5）
- tfsf        : 总场/散射场边界 + 1D 辅助入射场（Schneider 2004）
- dispersive  : Drude ADE 色散更新（Taflove 2005 §9.3）
- monitor     : DFT 在线监视器与 S 参数提取（Taflove 2005 §5.3）
- subpixel    : 亚像素材料界面平滑（Yu-Mittra 2001 共形法）
- solver      : 主求解器，编排上述模块的时间步进

公开 API 别名说明（规则 9 单文件版本，复用现有高质量实现）：
- YeeGrid  → YeeGridFdtd（yee_grid.py 原名，保留以兼容）
- compute_cfl_dt → courant_dt（yee_grid.py 原名）
- GaussianSource → GaussianPulse（sources.py 原名）
现有 yee_grid.py/cpml.py/sources.py 经审阅质量达标，按规则 9 不重写、
仅复用其公开 API；本 __init__ 仅做聚合导出与命名对齐。

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove & Hagness 2005 Computational Electrodynamics —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Roden & Gedney 2000 CPML —
   https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
4. Moharam 1995 JOSA A 12(5) 1077-1086 —
   https://doi.org/10.1364/JOSAA.12.001077
5. Schneider 2004 IEEE Trans AP 52(12) 3280-3287 —
   https://doi.org/10.1109/TAP.2004.837541
6. Lumerical FDTD — https://www.lumerical.com/products/fdtd/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 9（单文件版本）/规则 14/规则 18/规则 26/§4
"""

from __future__ import annotations

from polaris.sim.fdtd.cpml import (
    CpmlBuffers,
    CpmlCoefficients,
    CpmlConfig,
    build_cpml,
    reflection_db,
    update_e_psi,
    update_h_psi,
)
from polaris.sim.fdtd.dispersive import (
    DrudeParams,
    apply_ade_drude,
    drude_ade_coefficients,
)
from polaris.sim.fdtd.monitor import DftMonitor, SParamExtractor, s_param_db
from polaris.sim.fdtd.solver import (
    FdtdConfig,
    FdtdResult,
    FdtdSolver,
    solve_fdtd,
)
from polaris.sim.fdtd.sources import (
    ContinuousWave,
    DipoleSource,
    GaussianPulse,
    RickerWavelet,
    Waveform,
    inject_dipole,
)
from polaris.sim.fdtd.subpixel import (
    SubpixelConfig,
    block_average,
    conformal_permittivity,
    harmonic_average_permittivity,
    smooth_permittivity,
    volume_average_permittivity,
)
from polaris.sim.fdtd.tfsf import (
    Incident1D,
    TfsfBox,
    apply_tfsf_correction,
    apply_tfsf_e_correction,
    apply_tfsf_h_correction,
)
from polaris.sim.fdtd.yee_grid import (
    YeeGridFdtd,
    build_update_coefficients,
    courant_dt,
)

# 命名对齐别名（保留原名同时提供任务规约的公开名）
YeeGrid = YeeGridFdtd
compute_cfl_dt = courant_dt
GaussianSource = GaussianPulse

__all__ = [
    # yee_grid（+ 别名）
    "YeeGridFdtd",
    "YeeGrid",
    "courant_dt",
    "compute_cfl_dt",
    "build_update_coefficients",
    # cpml
    "CpmlConfig",
    "CpmlCoefficients",
    "CpmlBuffers",
    "build_cpml",
    "update_h_psi",
    "update_e_psi",
    "reflection_db",
    # sources（+ 别名）
    "Waveform",
    "GaussianPulse",
    "GaussianSource",
    "ContinuousWave",
    "RickerWavelet",
    "DipoleSource",
    "inject_dipole",
    # tfsf
    "TfsfBox",
    "Incident1D",
    "apply_tfsf_correction",
    "apply_tfsf_h_correction",
    "apply_tfsf_e_correction",
    # dispersive
    "DrudeParams",
    "apply_ade_drude",
    "drude_ade_coefficients",
    # monitor
    "DftMonitor",
    "SParamExtractor",
    "s_param_db",
    # subpixel
    "SubpixelConfig",
    "block_average",
    "volume_average_permittivity",
    "harmonic_average_permittivity",
    "conformal_permittivity",
    "smooth_permittivity",
    # solver
    "FdtdConfig",
    "FdtdResult",
    "FdtdSolver",
    "solve_fdtd",
]
