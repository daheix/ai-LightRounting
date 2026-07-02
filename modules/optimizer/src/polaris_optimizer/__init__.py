"""PoLaRIS 优化器子模块（polaris-optimizer）。

单一职责: 12 种光子学优化器的统一接口（拓扑/水平集/L-BFGS/PSO/CMA-ES/
NSGA-2/NSGA-3/鲁棒/多目标/密度伴随/形状伴随/反馈适配）。

v5.0 从旧 ``polaris.sim`` 与 ``polaris.inverse`` 拆分而来（单一职责，R13）。

## IPO 三段式设计

Input
-----
- ``initial_params``: 设计变量初值（numpy 1D float64）
- ``fom_fn``/``grad_fn``: 目标函数与梯度回调（adjoint 方法提供梯度）
- ``objectives``: 多目标函数列表（NSGA-II/III）
- ``violations``: 约束违规列表（FeedbackAdapter 输入）

Process
-------
- L-BFGS: 两循环递归 + Wolfe 线搜索（局部二阶拟牛顿）
- PSO: 粒子群（全局，Kennedy & Eberhart 1995）
- CMA-ES: 协方差矩阵自适应进化策略（全局，Hansen 2001）
- NSGA-II: 快速非支配排序 + 拥挤距离（多目标，Deb 2002）
- NSGA-III: 参考点法 + 小生境选择（多目标，Deb & Jain 2014）
- 拓扑优化: 水平集 + Hamilton-Jacobi（Osher & Sethian 1988）
- 鲁棒优化: 蒙特卡洛公差扰动（Wang 2018）
- 形状伴随: 参数化几何 + Adam（lumopt 风格）
- 密度伴随: JAX autograd + 锥形滤波 + sigmoid 投影（Piggott 2017）
- 反馈适配: 约束违规 → 布局布线建议（Apollo 2025）

Output
------
- ``OptimalResult``: 最优参数 + FoM 历史 + 收敛标志
- ``ParetoResult``: 帕累托前沿（多目标）
- ``FeedbackResult``: 布局/布线调整建议

## 设计原则

- 纯 NumPy/SciPy 实现（R04 不参与 GPU）
- 密度伴随子模块依赖 JAX（CPU 后端），可选 extra: ``polaris-optimizer[density]``
- 禁止 fall-back（R03）: 失败即 raise
- 学术诚信（R02）: 所有算法/参数标注文献来源

## 学术诚信（R02，≥5 文献 URL 溯源）

1. Liu & Nocedal 1989 L-BFGS:
   https://doi.org/10.1007/BF01589116
2. Kennedy & Eberhart 1995 PSO:
   https://doi.org/10.1109/ICNN.1995.488968
3. Hansen & Ostermeier 2001 CMA-ES:
   https://doi.org/10.1162/106365601750190398
4. Deb et al. 2002 NSGA-II:
   https://doi.org/10.1109/4235.996017
5. Deb & Jain 2014 NSGA-III:
   https://doi.org/10.1109/TEVC.2013.2281535
6. Osher & Sethian 1988 Level Set:
   https://doi.org/10.1016/S0021-9991(88)80002-2
7. Piggott 2017 Nature Photonics:
   https://www.nature.com/articles/nphoton.2017.102
8. Hughes 2018 autograd=adjoint:
   https://arxiv.org/abs/1811.01255
9. Wang et al. 2018 Robust photonic TO:
   https://doi.org/10.1364/OE.26.023273
10. Apollo 2025 布线感知反馈:
   https://arxiv.org/html/2504.18813v1
"""

from __future__ import annotations

from polaris_optimizer.feedback import (
    FeedbackAdapter,
    FeedbackResult,
    PlacementHint,
    RoutingHint,
    Violation,
    ViolationType,
)
from polaris_optimizer.global_opt import (
    CMAESConfig,
    CMAESOptimizer,
    GlobalMethod,
    GlobalOptimizer,
    GlobalResult,
    PSOConfig,
    ParticleSwarmOptimizer,
    create_cmaes_optimizer,
    create_global_optimizer,
    create_pso_optimizer,
    run_global_optimization,
)
from polaris_optimizer.lbfgs import (
    LBFGSConfig,
    LBFGSOptimizer,
    LBFGSResult,
    create_lbfgs_optimizer,
    run_lbfgs_optimization,
)
from polaris_optimizer.level_set import (
    FluxPair,
    GridStep,
    HJScheme,
    HJSolver,
    HJSolverConfig,
    compute_cfl_timestep,
    create_hj_solver,
    evolve_hj,
)
from polaris_optimizer.nsga import (
    Individual,
    NSGA2Config,
    NSGA2Optimizer,
    NSGA3Config,
    NSGA3Optimizer,
    NSGA3Result,
    NicheSelectionState,
    Objective,
    ObjectiveType,
    ParetoResult,
    SBXConfig,
    compute_crowding_distance,
    dominates,
    fast_non_dominated_sort,
    generate_reference_points,
    polynomial_mutation,
    sbx_crossover,
    tournament_selection,
)
from polaris_optimizer.robust import (
    MonteCarloEvaluator,
    RobustConfig,
    RobustMode,
    RobustObjective,
    RobustOptimizer,
    RobustResult,
    ToleranceModel,
    ToleranceType,
    create_robust_optimizer,
    create_tolerance_model,
    evaluate_robustness,
    run_robust_optimization,
)
from polaris_optimizer.shape_adjoint import (
    AnalyticalWaveguideCoupler,
    OptimizationBackend,
    ParameterizedGeometry,
    ShapeAdjointConfig,
    ShapeAdjointOptimizer,
    ShapeOptimizationResult,
    ForwardSimulator,
    run_shape_adjoint_optimization,
)
from polaris_optimizer.topology import (
    LevelSet,
    TopologyConfig,
    TopologyOptimizer,
    TopologyResult,
    run_topology_optimization,
)

__version__ = "5.0.0"

__all__ = [
    # 元信息
    "__version__",
    # L-BFGS
    "LBFGSConfig",
    "LBFGSResult",
    "LBFGSOptimizer",
    "create_lbfgs_optimizer",
    "run_lbfgs_optimization",
    # PSO + CMA-ES + Global
    "PSOConfig",
    "ParticleSwarmOptimizer",
    "CMAESConfig",
    "CMAESOptimizer",
    "GlobalMethod",
    "GlobalOptimizer",
    "GlobalResult",
    "create_pso_optimizer",
    "create_cmaes_optimizer",
    "create_global_optimizer",
    "run_global_optimization",
    # NSGA-II + NSGA-III
    "ObjectiveType",
    "Objective",
    "SBXConfig",
    "Individual",
    "NSGA2Config",
    "ParetoResult",
    "NSGA2Optimizer",
    "NSGA3Config",
    "NSGA3Result",
    "NSGA3Optimizer",
    "NicheSelectionState",
    "dominates",
    "fast_non_dominated_sort",
    "compute_crowding_distance",
    "tournament_selection",
    "sbx_crossover",
    "polynomial_mutation",
    "generate_reference_points",
    # 拓扑优化（水平集）
    "TopologyConfig",
    "TopologyResult",
    "LevelSet",
    "TopologyOptimizer",
    "run_topology_optimization",
    # Hamilton-Jacobi 求解器
    "FluxPair",
    "GridStep",
    "HJScheme",
    "HJSolverConfig",
    "HJSolver",
    "evolve_hj",
    "compute_cfl_timestep",
    "create_hj_solver",
    # 鲁棒优化
    "ToleranceType",
    "RobustMode",
    "ToleranceModel",
    "RobustConfig",
    "RobustResult",
    "MonteCarloEvaluator",
    "RobustObjective",
    "RobustOptimizer",
    "create_tolerance_model",
    "create_robust_optimizer",
    "run_robust_optimization",
    "evaluate_robustness",
    # 形状伴随
    "OptimizationBackend",
    "ForwardSimulator",
    "ShapeAdjointConfig",
    "ShapeOptimizationResult",
    "ParameterizedGeometry",
    "ShapeAdjointOptimizer",
    "AnalyticalWaveguideCoupler",
    "run_shape_adjoint_optimization",
    # 反馈适配
    "ViolationType",
    "Violation",
    "PlacementHint",
    "RoutingHint",
    "FeedbackResult",
    "FeedbackAdapter",
]
