"""PoLaRIS 玻色采样子模块（polaris-boson）。

单一职责: 线性光学玻色采样（Boson Sampling）量子优势 benchmark 仿真，
包含矩阵积和式（permanent）计算、玻色采样器、Clements 酉矩阵生成器、
HOM 双光子干涉（与玻色采样紧密相关的量子干涉现象）。

v5.0 从旧 ``polaris-quantum`` 拆分而来（单一职责，R13 代码清理）。

稳定 API
--------
- ``boson_sampling(unitary, input_state) -> dict``
- ``clements_unitary(n_modes=4, seed=42) -> list``
- ``hom_interference(theta=0.0) -> dict``
- ``permanent_glynn_gray(matrix) -> complex``

设计原则
--------
- 对外 API 返回 JSON-serializable dict/list（与 polaris-core/route 一致）
- 纯 NumPy/math 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 概率和≠1 / 酉性校验失败 → raise
- 数值物理正确: 玻色采样概率和=1, HOM dip=1, Clements 酉性<1e-10

学术诚信（R02，≥5 文献 URL 溯源）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Clements et al., Optica 2016, Clements 分解
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Glynn, Eur. J. Comb. 2010, 积和式算法
  https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund 2012, "Counting Perfect Matchings as Fast as Ryser"
  https://arxiv.org/abs/1203.5687
"""

from __future__ import annotations

from polaris_boson.clements import clements_unitary
from polaris_boson.hom import hom_interference
from polaris_boson.permanent import permanent_glynn_gray
from polaris_boson.sampler import boson_sampling

__version__ = "5.1.0"

__all__ = [
    "boson_sampling",
    "clements_unitary",
    "hom_interference",
    "permanent_glynn_gray",
    "__version__",
]
