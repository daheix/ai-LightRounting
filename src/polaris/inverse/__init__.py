"""PoLaRIS 逆向设计模块（R28 伴随优化）。

基于密度法拓扑优化的伴随逆向设计，对标 Tidy3D adjoint + lumopt 拓扑优化能力。

子模块:
- adjoint_optimizer: 密度法伴随优化器（JAX autograd + 锥形滤波 + sigmoid 投影）

学术来源（R02 学术诚信）:
- Tidy3D adjoint: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/AdjointPlugin.html
- lumopt: https://github.com/pcrost/lumopt
- Molesky 2018: https://arxiv.org/abs/1809.07731
- Piggott 2017: https://www.nature.com/articles/nphoton.2017.102
"""

from polaris.inverse.adjoint_optimizer import (
    AdjointOptimizer,
    ModeOverlapObjective,
    OptimizerConfig,
    OptimizationResult,
    example_grating_coupler,
    example_mmi_1x2,
    example_mode_converter,
)

__all__ = [
    "AdjointOptimizer",
    "ModeOverlapObjective",
    "OptimizerConfig",
    "OptimizationResult",
    "example_mmi_1x2",
    "example_grating_coupler",
    "example_mode_converter",
]
