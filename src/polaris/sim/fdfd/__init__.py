"""sim/fdfd 包：FDFD 频域有限差分求解器（A05 聚类，P0 频域全波路径核心）。

按 A05-FDFD 算法文档实现：
- 2D TEz 标量波动方程 ∇·(P∇E_z) + k₀²Qε_r E_z = -iωμ₀QJ_z
- SC-PML（Shin & Fan 2012）拉伸坐标融入算子对角块（无辅助变量）
- 复对称稀疏线性系统 A·E = b（scipy.sparse.linalg.spsolve / cg / bicgstab）
- 与 FDE 共享 YeeGrid + ScPml 组件（ALGORITHMS.md 附录 C 共享底座）

子模块：
- solver.py   : FdfdSolver 主体（算子组装 + 求解 + H 回代）
- source.py   : 源项生成（平面波/偶极子/模式注入/高斯光束）
- sparam.py   : 端口 S 参数提取（模式重叠 + 能量守恒校验）

文献来源（≥5，规则 18 学术诚信）：
1. Shin & Fan 2012 JCP — https://doi.org/10.1016/j.jcp.2011.12.037
2. MaxwellFDFD（Shin MATLAB 包）— https://www.mit.edu/~wsshin/maxwellfdfd.html
3. Jaxwell（Fischbach，PoLaRIS 仅参考公式，规则 26 不参与 GPU）—
   https://jan-david-fischbach.github.io/jaxwell/
4. Gu et al 2014 IEEE TMTT（QMR-COCG/COCR 复对称求解）—
   https://doi.org/10.1109/TMTT.2014.2363835
5. Yee 1966 IEEE TAP — https://doi.org/10.1109/TAP.1966.1138693
6. SimWorks FDFD Solver — https://www.simworks.net/solver/FDFD
7. Simsek et al 2025 Sci. Rep.（mixed-field ring resonator）—
   https://doi.org/10.1038/s41598-025-18869-z

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from polaris.sim.fdfd.solver import (
    FdfdResult,
    FdfdSolver,
    FdfdSolverConfig,
    solve_fdfd,
)
from polaris.sim.fdfd.source import (
    DipoleSource,
    GaussianBeamSource,
    ModeSource,
    PlaneWaveSource,
    SourceType,
)
from polaris.sim.fdfd.sparam import (
    PortSpec,
    SParameters,
    extract_s_parameters,
    verify_energy_conservation,
)

__all__ = [
    "FdfdResult",
    "FdfdSolver",
    "FdfdSolverConfig",
    "solve_fdfd",
    "DipoleSource",
    "GaussianBeamSource",
    "ModeSource",
    "PlaneWaveSource",
    "SourceType",
    "PortSpec",
    "SParameters",
    "extract_s_parameters",
    "verify_energy_conservation",
]
