"""PoLaRIS KLM 线性光学量子计算子模块（polaris-klm）。

单一职责: KLM（Knill-Laflamme-Milburn）线性光学量子计算门仿真，
实现 Ralph 2002 简化 4-BS CNOT 电路（后选择成功率 1/9）。

v5.0 从旧 ``polaris-quantum`` 拆分而来（单一职责，R13 代码清理）。

稳定 API
--------
- ``klm_cnot() -> dict``

设计原则
--------
- 对外 API 返回 JSON-serializable dict（与 polaris-core/route 一致）
- 纯 NumPy/math 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 电路酉性校验失败 → raise
- 数值物理正确: success_prob=1/9, 电路酉性<1e-10

学术诚信（R02，≥5 文献 URL 溯源）:
- Knill, Laflamme, Milburn, Nature 409, 46 (2001), KLM 方案
  https://www.nature.com/articles/35051009
- Ralph, Langford, Bell, White, PRA 65, 062324 (2002), 简化 CNOT（1/9）
  https://doi.org/10.1103/PhysRevA.65.062324
- Hofmann & Takeuchi, PRA 66, 024308 (2002)
  https://doi.org/10.1103/PhysRevA.66.024308
- O'Brien et al., Nature 426, 264 (2003)
  https://doi.org/10.1038/nature02354
- Knill, PRA 66, 052306 (2002)
  https://doi.org/10.1103/PhysRevA.66.052306
"""

from __future__ import annotations

from polaris_klm.gates import klm_cnot

__version__ = "5.1.0"

__all__ = ["klm_cnot", "__version__"]
