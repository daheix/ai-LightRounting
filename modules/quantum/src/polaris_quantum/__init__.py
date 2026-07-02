"""PoLaRIS 量子光子仿真验证子模块（polaris-quantum）。

提供稳定的 Python API，对线性光学量子计算进行仿真验证:
- 玻色采样（Aaronson-Arkhipov 2011）: permanent 计算概率分布
- KLM CNOT 量子门（Knill 2001 / Ralph 2002）: 后选择成功率 1/9
- HOM 干涉（Hong-Ou-Mandel 1987）: 双光子量子干涉 dip
- Clements 酉矩阵（Clements 2016）: 通用 M×M 酉矩阵分解

## 设计原则

- 对外 API 返回 JSON-serializable dict/list（与 polaris-core/route 一致）
- 纯 NumPy/math 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 概率和≠1 / 酉性校验失败 / 后选择失败 → raise
- 数值物理正确: 玻色采样概率和=1, KLM=1/9, HOM dip=1, Clements 酉性<1e-10

## 稳定 API

- ``boson_sampling(unitary, input_state) -> dict``
- ``klm_cnot() -> dict``
- ``hom_interference(theta=0.0) -> dict``
- ``clements_unitary(n_modes=4, seed=42) -> list``

## 来源（R02 学术诚信，≥5 个文献 URL）

- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009
- Ralph et al., PRA 2002, 简化 KLM CNOT 门（成功率 1/9）
  https://doi.org/10.1103/PhysRevA.65.062324
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Clements et al., Optica 2016, Clements 分解
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Reck et al., PRL 1994, 线性光学网络分解
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Glynn, Eur. J. Comb. 2010, 积和式算法
  https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund 2012, "Counting Perfect Matchings as Fast as Ryser"
  https://arxiv.org/abs/1203.5687
"""

from __future__ import annotations

from polaris_quantum.boson import boson_sampling
from polaris_quantum.clements import clements_unitary
from polaris_quantum.hom import hom_interference
from polaris_quantum.klm import klm_cnot

__version__ = "5.0.0"

__all__ = [
    "boson_sampling",
    "klm_cnot",
    "hom_interference",
    "clements_unitary",
    "__version__",
]
