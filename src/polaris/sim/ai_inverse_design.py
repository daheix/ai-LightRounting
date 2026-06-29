"""R29 路标：AI 驱动光子逆向设计模块。

对标 lumopt + JAX adjoint 逆向设计，融合 Adjoint Method、强化学习（RL）、
生成对抗网络（GAN）与多目标优化，实现 AI 驱动的光子器件逆向设计。

## 模块组成

1. ``AdjointOptimizer`` — Adjoint Method 优化器（JAX 自动微分）
2. ``RLInverseDesigner`` — RL 驱动逆向设计（【创新】替代梯度优化）
3. ``GANDesigner`` — GAN 生成式逆向设计
4. ``MultiObjectiveOptimizer`` — 多目标优化器（Pareto 前沿，NSGA-II）
5. ``ManufactureAwareOptimizer`` — 制造感知优化器（最小特征尺寸 + 鲁棒性）

## 正向仿真物理模型

采用传输矩阵法（Transfer Matrix Method, TMM）计算多层堆叠的传输率，
作为可微正向仿真器。TMM 是薄膜光学的标准方法（Born & Wolf《Principles of Optics》），
完全可微，适合 JAX 自动微分。设计参数 θ∈[0,1]^N 映射为各层折射率
n_i = n_low + θ_i·(n_high - n_low)，优化目标为最大化/约束目标波长处的传输率。

## 学术依据

- Lalau-Keraly et al., "Adjoint shape optimization applied to electromagnetic design",
  Optics Express 2013, https://doi.org/10.1364/OE.21.0021693
- Piggott et al., "Inverse design and demonstration of a compact and broadband
  on-chip wavelength demultiplexer", Nature Photonics 2017,
  https://doi.org/10.1038/nphoton.2017.126
- Minkov et al., "Adjoint optimization of photonic devices with JAX autodiff",
  Optics Express 2018, https://doi.org/10.1364/OE.26.030935
- Goodfellow et al., "Generative Adversarial Networks", NIPS 2014,
  https://arxiv.org/abs/1406.2661
- Schulman et al., "Proximal Policy Optimization Algorithms", 2017,
  https://arxiv.org/abs/1707.06347
- Deb et al., "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II", 2002,
  https://ieeexplore.ieee.org/document/996017
- Hammond et al., "Photonic topology optimization with manufacturing constraints",
  Optics Express 2021, https://doi.org/10.1364/OE.432612

来源:
- lumopt: https://github.com/chriskeraly/lumopt
- JAX: https://jax.readthedocs.io/
- 传输矩阵法: Born & Wolf, Principles of Optics, Cambridge University Press

## 架构说明（facade 模式）

本文件为 facade 入口，实现已按功能拆分到子模块，外部 import 路径保持不变：
- ``ai_inverse_design_physics`` — TMM 可微正向仿真核心 + 物理常数 + JAX 检测
- ``ai_inverse_design_adjoint`` — AdjointConfig + AdjointOptimizer
- ``ai_inverse_design_rl`` — RLDesignConfig + RLInverseDesigner
- ``ai_inverse_design_optimizers`` — MultiObjectiveOptimizer + ManufactureAwareOptimizer
"""

from __future__ import annotations

from polaris.sim.ai_inverse_design_adjoint import (  # noqa: F401
    AdjointConfig,
    AdjointOptimizer,
    _transfer_matrix_transmission_jax,
)
from polaris.sim.ai_inverse_design_optimizers import (  # noqa: F401
    ManufactureAwareOptimizer,
    MultiObjectiveOptimizer,
)
from polaris.sim.ai_inverse_design_physics import (  # noqa: F401
    _HAS_JAX,
    N_AIR,
    N_SILICON,
    N_SIO2,
    _transfer_matrix_transmission,
)
from polaris.sim.ai_inverse_design_rl import (  # noqa: F401
    RLDesignConfig,
    RLInverseDesigner,
)

__all__ = [
    "AdjointConfig",
    "AdjointOptimizer",
    "RLDesignConfig",
    "RLInverseDesigner",
    "MultiObjectiveOptimizer",
    "ManufactureAwareOptimizer",
]
