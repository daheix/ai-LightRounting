"""PoLaRIS 逆向设计模块（R28 伴随优化；R09 单文件版本重构）。

基于密度法拓扑优化的伴随逆向设计，对标 Tidy3D adjoint + lumopt 拓扑优化能力。

子模块:
- topology_adjoint_optimizer: 密度法伴随优化器（JAX autograd + 锥形滤波 + sigmoid 投影）
  （R09 重构：原 adjoint_optimizer.py 改名为 topology_adjoint_optimizer.py，
   类名 AdjointOptimizer → TopologyAdjointOptimizer 以消除与
   sim/shape_adjoint_optimizer.py 和 sim/ai_inverse_design_adjoint.py 的命名冲突）

学术来源（R02 学术诚信）:
- Tidy3D adjoint: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/AdjointPlugin.html
- lumopt: https://github.com/pcrost/lumopt
- Molesky 2018: https://arxiv.org/abs/1809.07731
- Piggott 2017: https://www.nature.com/articles/nphoton.2017.102
"""

from polaris.inverse.topology_adjoint_optimizer import (
    ModeOverlapObjective,
    OptimizerConfig,
    TopologyAdjointOptimizer,
    TopologyOptimizationResult,
    example_grating_coupler,
    example_mmi_1x2,
    example_mode_converter,
)

__all__ = [
    "TopologyAdjointOptimizer",
    "ModeOverlapObjective",
    "OptimizerConfig",
    "TopologyOptimizationResult",
    "example_mmi_1x2",
    "example_grating_coupler",
    "example_mode_converter",
]
