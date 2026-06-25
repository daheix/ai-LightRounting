"""RCWA 严格耦合波分析（A01 聚类，1D/2D 周期光栅）。

包结构（A01 §5 完整流程，Sprint 1 Task 1.2）::

    polaris/sim/rcwa/
        __init__.py     — 包入口，统一导出
        fourier.py      — Li 1996 normal/inverse 傅里叶因子化 + Toeplitz 卷积矩阵
        layer.py        — 单层本征模（W/V/k_z）+ 界面/传播 S 矩阵构造
        solver_1d.py    — 1D RCWA 求解器（TE/TM 分离，Moharam 1995 ETM）
        solver_2d.py    — 2D 矢量 RCWA 求解器（Liu & Fan 2012 S4 公式）

与 C03-Redheffer 星积（``polaris.sim.cascade.smatrix``）共享 BlockSMatrix
内核，避免消逝波 $e^{|k_z| d}$ 在长结构中指数发散。

文献来源（≥5，规则 18 学术诚信）：
1. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
2. Li 1996 JOSA A 13, 1870 (FFF/Li's Inverse Rule) —
   https://doi.org/10.1364/JOSAA.13.001870
3. Lalanne & Morris 1996 JOSA A 13, 779 —
   https://doi.org/10.1364/JOSAA.13.000779
4. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
5. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/
6. Song 2025 Photonics 12(9), 943 (H-matrix) —
   https://www.mdpi.com/2304-6732/12/9/943

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy/SciPy）
"""

from polaris.sim.rcwa.fourier import (
    FourierRule,
    build_epsilon_inv_toeplitz_1d,
    build_epsilon_inv_toeplitz_2d,
    build_epsilon_toeplitz_1d,
    build_epsilon_toeplitz_2d,
    fourier_coefficients_1d,
    fourier_coefficients_2d,
    select_rule,
    toeplitz_from_coefficients,
)
from polaris.sim.rcwa.layer import (
    LayerModes,
    Polarization,
    build_homogeneous_modes_1d,
    build_interface_smatrix,
    build_propagation_smatrix,
    solve_layer_eigenmodes_1d,
)
from polaris.sim.rcwa.solver_1d import (
    GratingLayer1D,
    RcwaConfig1D,
    RcwaResult1D,
    solve_rcwa_1d,
)
from polaris.sim.rcwa.solver_2d import (
    GratingLayer2D,
    RcwaConfig2D,
    RcwaResult2D,
    solve_rcwa_2d,
)

__all__ = [
    # fourier.py（Li 1996 normal/inverse rule）
    "FourierRule",
    "select_rule",
    "fourier_coefficients_1d",
    "fourier_coefficients_2d",
    "toeplitz_from_coefficients",
    "build_epsilon_toeplitz_1d",
    "build_epsilon_inv_toeplitz_1d",
    "build_epsilon_toeplitz_2d",
    "build_epsilon_inv_toeplitz_2d",
    # layer.py（本征模 + 界面/传播 S 矩阵）
    "Polarization",
    "LayerModes",
    "solve_layer_eigenmodes_1d",
    "build_homogeneous_modes_1d",
    "build_interface_smatrix",
    "build_propagation_smatrix",
    # solver_1d.py
    "GratingLayer1D",
    "RcwaConfig1D",
    "RcwaResult1D",
    "solve_rcwa_1d",
    # solver_2d.py
    "GratingLayer2D",
    "RcwaConfig2D",
    "RcwaResult2D",
    "solve_rcwa_2d",
]
