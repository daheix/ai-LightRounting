"""sim/grid 包：Yee 网格与 PML 共享组件（FDE/FDFD/2.5D-FDTD/FDTD 底座）。

按 A04-FDE 算法文档 §4-§5，本包提供：
- yee.YeeGrid：2D Yee 交错网格 + 稀疏差分算子
- pml.ScPml：Shin & Fan 2012 SC-PML 复坐标拉伸

规则依据：project_rules.md 规则 26（GPU 不参与）；python代码开发规则.md §4（向量化）
"""

from polaris.sim.grid.pml import ScPml, build_pml_stretch
from polaris.sim.grid.yee import GridSpec, YeeGrid

__all__ = ["GridSpec", "YeeGrid", "ScPml", "build_pml_stretch"]
