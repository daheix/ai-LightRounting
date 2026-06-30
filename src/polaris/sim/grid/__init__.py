"""sim/grid 包：Yee 网格与 PML 共享组件（FDE/FDFD/2.5D-FDTD/FDTD 底座）。

按 A04-FDE 算法文档 §4-§5，本包提供：
- yee.YeeGrid：2D Yee 交错网格 + 稀疏差分算子
- pml.ScPml：Shin & Fan 2012 SC-PML 复坐标拉伸

规则依据：project_rules.md 规则 26（GPU 不参与）；python代码开发规则.md §4（向量化）

参考文献：
[1] Yee K S. Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media[J]. IEEE Transactions on Antennas and Propagation, 1966, 14(3): 302-307. https://doi.org/10.1109/TAP.1966.1138693
[2] Berenger J P. A perfectly matched layer for the absorption of electromagnetic waves[J]. Journal of Computational Physics, 1994, 114(2): 185-200. https://doi.org/10.1006/jcph.1994.1159
[3] Shin W, Fan S. Choice of the perfectly matched layer for the frequency-domain finite-difference method[J]. Journal of Computational Physics, 2012, 231(9): 3406-3431. https://doi.org/10.1016/j.jcp.2011.12.037
[4] Gedney S D. An anisotropic perfectly matched layer-absorbing medium for the truncation of FDTD lattices[J]. IEEE Transactions on Antennas and Propagation, 1996, 44(12): 1630-1639. https://doi.org/10.1109/8.546249
[5] Roden J A, Gedney S D. Convolution PML (CPML): An efficient FDTD implementation of the CFS-PML for arbitrary media[J]. Microwave and Optical Technology Letters, 2000, 27(5): 334-339. https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
[6] Taflove A, Hagness S C. Computational electrodynamics: The finite-difference time-domain method[M]. 3rd ed. Artech House, 2005. https://us.artechhouse.com/Computational-Electrodynamics-The-Finite-Difference-Time-Domain-Method-Third-Edition-P1397.aspx
"""

from polaris.sim.grid.pml import ScPml, build_pml_stretch
from polaris.sim.grid.yee import GridSpec, YeeGrid

__all__ = ["GridSpec", "YeeGrid", "ScPml", "build_pml_stretch"]
