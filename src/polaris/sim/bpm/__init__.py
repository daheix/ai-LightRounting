"""sim/bpm 包：BPM 光束传播法求解器（A03 聚类，P0 弱导波导长距离传播快速粗筛）。

按 A03-BPM 算法文档实现（Hadley 1992 TBC + Crank-Nicolson + Peaceman-Rachford ADI）：
- SVEA 抛物方程 a·∂ψ/∂z = ∇⊥²ψ + b·ψ（a=2i·k₀·n_ref，b=k₀²(n²-n_ref²)，A03 §3.2 公式 F1）
- 1D Crank-Nicolson 隐式步进（θ=0.5，二阶时间精度，无条件稳定，Thomas solve_banded O(N)）
- 2D ADI 分裂步进（Peaceman & Rachford 1955，两个半步各三对角）
- TBC 透明边界条件（Hadley 1992，反射 < 3e-8，A03 §5.1 公式 F4）
- TE/TM 半矢量 BPM（TM 含 n²·∂(n⁻²·∂/∂x)/∂x 界面调和平均，A03 §3.3 公式 F6）

子模块：
- operators.py     : 三对角差分算子构造（scipy.sparse.diags，向量化）
- boundary.py      : TBC 透明边界条件（Hadley 1992，外向波数估计 + 边界行修改）
- crank_nicolson.py: 1D Crank-Nicolson 步进（θ 加权隐式 + Thomas solve_banded）
- adi.py            : 2D ADI 分裂步进（Peaceman & Rachford 1955）
- solver.py         : BpmConfig/BpmResult/BpmSolver/solve_bpm 统一调度主体

定位（A03 §1）：弱导波导（SiO2/SiON/光纤/玻璃基 PLC）长距离传播快速粗筛求解器，
与 FDE（精确本征模）/ EME（高对比度双向）/ FDFD（频域全波）形成精度-速度梯度。

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 — TBC 核心文献，反射 3e-8 —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 — TBC 短文版本 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 — FD-BPM CN 三对角实现 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions for BPM — TBC 商业实现 —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM — CN + TBC + ADI 开源参考实现 —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy+scipy.sparse+scipy.linalg.solve_banded）
/python代码开发规则.md §4（向量化，z 步进主循环为唯一允许循环）
"""

from polaris.sim.bpm.adi import AdiStepper2D, adi_propagate_2d
from polaris.sim.bpm.boundary import (
    BoundaryType,
    apply_tbc_lhs_banded_inplace,
    apply_tbc_rhs_inplace,
    compute_tbc_reflection,
    estimate_kx_left,
    estimate_kx_right,
)
from polaris.sim.bpm.crank_nicolson import (
    CrankNicolsonStepper,
    crank_nicolson_propagate_1d,
)
from polaris.sim.bpm.operators import (
    Polarization,
    apply_rhs_operator,
    build_lhs_banded,
    build_tridiag_operator,
    build_tridiag_operator_te,
    build_tridiag_operator_tm,
    sparse_to_banded,
)
from polaris.sim.bpm.solver import (
    BpmConfig,
    BpmResult,
    BpmSolver,
    solve_bpm,
)

__all__ = [
    # operators.py
    "Polarization",
    "build_tridiag_operator",
    "build_tridiag_operator_te",
    "build_tridiag_operator_tm",
    "sparse_to_banded",
    "build_lhs_banded",
    "apply_rhs_operator",
    # boundary.py
    "BoundaryType",
    "estimate_kx_left",
    "estimate_kx_right",
    "apply_tbc_lhs_banded_inplace",
    "apply_tbc_rhs_inplace",
    "compute_tbc_reflection",
    # crank_nicolson.py
    "CrankNicolsonStepper",
    "crank_nicolson_propagate_1d",
    # adi.py
    "AdiStepper2D",
    "adi_propagate_2d",
    # solver.py
    "BpmConfig",
    "BpmResult",
    "BpmSolver",
    "solve_bpm",
]
