"""sim/fde 包：FDE 本征模求解器（A04 聚类，P0 求解器栈底座）。

按 A04-FDE 算法文档实现：
- 磁场形式矢量本征方程 ∇×(1/ε ∇×H) = k₀²H（数值稳定，无 spurious modes）
- Yee 网格离散 + scipy.sparse 稀疏算子
- scipy.sparse.linalg.eigs（Arnoldi）+ shift-invert 求前 K 个 β² 本征对
- SC-PML 复坐标拉伸吸收辐射模
- 功率归一化（1W 约定）+ 相位修正
- TE/TM 分数 + 模式损耗（dB/cm）+ 模式重叠积分

输出 Mode 数据类供 EME/FDFD/2.5D-FDTD/FDTD 模式注入零成本复用（A04 §11.2 创新）。

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE TAP — https://doi.org/10.1109/TAP.1966.1138693
2. Simsek 2025 arXiv:2503.17746 — https://arxiv.org/abs/2503.17746
3. Yu & Chang 2004 OSA — Yee-mesh FDE + PML
4. Shin & Fan 2012 JCP — https://doi.org/10.1016/j.jcp.2011.12.037
5. Xu et al 1994 IEE Proc-J — 全矢量 FDE
6. SimWorks FDE 官方文档 — https://www.simworks.net/en/solver/FDE
7. Lumerical MODE FDE — https://support.lumerical.com/hc/en-us/articles/360042800453

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from polaris.sim.fde.mode import Mode
from polaris.sim.fde.solver import FdeSolver, FdeSolverConfig, solve_waveguide

__all__ = ["Mode", "FdeSolver", "FdeSolverConfig", "solve_waveguide"]
