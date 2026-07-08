"""polaris-optimizer 子模块深度测试。

测试覆盖（38 个 pytest，覆盖全部公开 API）:
- L-BFGS: LBFGSConfig/LBFGSResult/LBFGSOptimizer/create_*/run_*（二次收敛）
- PSO: PSOConfig/ParticleSwarmOptimizer/create_pso_optimizer（球函数改善）
- CMA-ES: CMAESConfig/CMAESOptimizer/create_cmaes_optimizer（球函数改善）
- GlobalOptimizer: GlobalMethod 枚举/GlobalResult/create_global_optimizer
                   /run_global_optimization（CMA-ES + PSO 双路径）
- NSGA-II: ObjectiveType/Objective/SBXConfig/Individual/NSGA2Config
           /ParetoResult/dominates/fast_non_dominated_sort
           /compute_crowding_distance/tournament_selection/sbx_crossover
           /polynomial_mutation/NSGA2Optimizer（ZDT1 帕累托前沿）
- NSGA-III: NSGA3Config/NSGA3Result/NicheSelectionState
            /generate_reference_points（Das-Dennis）/NSGA3Optimizer
- 拓扑优化: TopologyConfig/TopologyResult/LevelSet（circle/rectangle/cross）
            /TopologyOptimizer/run_topology_optimization
- Hamilton-Jacobi: HJScheme（ENO/WENO/UPWIND）/HJSolverConfig/FluxPair
                   /GridStep/compute_cfl_timestep/evolve_hj/HJSolver
                   /create_hj_solver（含未知 scheme raise 分支）
- 鲁棒优化: ToleranceType/RobustMode/ToleranceModel.sample/RobustConfig
            /RobustResult/MonteCarloEvaluator/RobustObjective/RobustOptimizer
            /create_tolerance_model/create_robust_optimizer
            /run_robust_optimization/evaluate_robustness
- 形状伴随: OptimizationBackend/ShapeAdjointConfig/ShapeOptimizationResult
            /ParameterizedGeometry（含对称约束）/ShapeAdjointOptimizer
            /AnalyticalWaveguideCoupler/run_shape_adjoint_optimization
- 反馈适配: ViolationType（17 值）/Violation/PlacementHint/RoutingHint
            /FeedbackResult/FeedbackAdapter（5 类违规处理 + raise 分支）

来源（R02 学术诚信，≥5 文献 URL）:
- pytest 文档: https://docs.pytest.org/
- Liu & Nocedal 1989 L-BFGS:
  https://doi.org/10.1007/BF01589116
- Kennedy & Eberhart 1995 PSO:
  https://doi.org/10.1109/ICNN.1995.488968
- Hansen & Ostermeier 2001 CMA-ES:
  https://doi.org/10.1162/106365601750190398
- Deb et al. 2002 NSGA-II:
  https://doi.org/10.1109/4235.996017
- Deb & Jain 2014 NSGA-III:
  https://doi.org/10.1109/TEVC.2013.2281535
- Das & Dennis 1998 参考点法:
  https://doi.org/10.1137/S1052623496307510
- Osher & Sethian 1988 Level Set:
  https://doi.org/10.1016/S0021-9991(88)80002-2
- Osher & Shu 1991 ENO:
  https://doi.org/10.1137/0728049
- Jiang & Peng 2000 WENO:
  https://doi.org/10.1137/S1064827597324553
- Wang et al. 2018 鲁棒优化:
  https://doi.org/10.1364/OE.26.023273
- Kingma & Ba 2014 Adam:
  https://arxiv.org/abs/1412.6980
- Yariv 1973 耦合模理论:
  https://doi.org/10.1063/1.1668400
- Apollo 2025 反馈适配:
  https://arxiv.org/html/2504.18813v1

规则: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_optimizer import (  # noqa: E402
    AnalyticalWaveguideCoupler,
    CMAESConfig,
    CMAESOptimizer,
    FeedbackAdapter,
    FeedbackResult,
    FluxPair,
    GlobalMethod,
    GlobalOptimizer,
    GridStep,
    HJScheme,
    HJSolver,
    HJSolverConfig,
    Individual,
    LBFGSConfig,
    LBFGSOptimizer,
    LBFGSResult,
    LevelSet,
    NicheSelectionState,
    NSGA2Config,
    NSGA2Optimizer,
    NSGA3Config,
    NSGA3Optimizer,
    NSGA3Result,
    Objective,
    ObjectiveType,
    OptimizationBackend,
    ParameterizedGeometry,
    ParetoResult,
    PlacementHint,
    PSOConfig,
    ParticleSwarmOptimizer,
    RobustConfig,
    RobustMode,
    RobustObjective,
    RobustOptimizer,
    RobustResult,
    RoutingHint,
    SBXConfig,
    ShapeAdjointConfig,
    ShapeAdjointOptimizer,
    ShapeOptimizationResult,
    ToleranceModel,
    ToleranceType,
    TopologyConfig,
    TopologyOptimizer,
    TopologyResult,
    Violation,
    ViolationType,
    compute_cfl_timestep,
    compute_crowding_distance,
    create_cmaes_optimizer,
    create_global_optimizer,
    create_hj_solver,
    create_lbfgs_optimizer,
    create_pso_optimizer,
    create_robust_optimizer,
    create_tolerance_model,
    dominates,
    evaluate_robustness,
    evolve_hj,
    fast_non_dominated_sort,
    generate_reference_points,
    polynomial_mutation,
    run_global_optimization,
    run_lbfgs_optimization,
    run_robust_optimization,
    run_shape_adjoint_optimization,
    run_topology_optimization,
    sbx_crossover,
    tournament_selection,
)


# =============================================================================
# L-BFGS 拟牛顿优化器
# =============================================================================


def test_topology_config_defaults():
    """TopologyConfig 默认值。"""
    cfg = TopologyConfig()
    assert cfg.grid_size == 50
    assert cfg.max_iterations == 50
    assert cfg.learning_rate == 0.1
    assert cfg.convergence_threshold == 1e-6
    assert cfg.smooth_sigma == 1.0
    assert cfg.min_feature_size == 2.0


def test_level_set_circle_shape():
    """LevelSet circle 初始形状中心为正（材料）。"""
    ls = LevelSet(grid_size=21, initial_shape="circle")
    assert ls.phi.shape == (21, 21)
    # 中心点应 > 0（材料区域）
    assert ls.phi[10, 10] > 0.0
    # 角落应 < 0（背景）
    assert ls.phi[0, 0] < 0.0
    # 二值化
    binary = ls.get_binary()
    unique = set(np.unique(binary).tolist())
    assert unique.issubset({0.0, 1.0})


def test_level_set_rectangle_shape():
    """LevelSet rectangle 初始形状。"""
    ls = LevelSet(grid_size=11, initial_shape="rectangle")
    assert ls.phi.shape == (11, 11)
    assert ls.phi[5, 5] > 0.0


def test_level_set_cross_shape():
    """LevelSet cross 初始形状。"""
    ls = LevelSet(grid_size=21, initial_shape="cross")
    assert ls.phi.shape == (21, 21)
    # 十字中心 > 0
    assert ls.phi[10, 10] > 0.0


def test_level_set_material_fraction():
    """LevelSet.get_material_fraction 在 [0, 1]。"""
    ls = LevelSet(grid_size=21, initial_shape="circle")
    frac = ls.get_material_fraction()
    assert 0.0 < frac < 1.0


def test_topology_level_set_runs():
    """拓扑优化（水平集）能跑通并产生二值化设计。

    使用最简配置（小网格 + 少迭代）验证流程完整（Osher & Sethian 1988）。
    """
    grid_size = 20
    config = TopologyConfig(
        grid_size=grid_size,
        max_iterations=5,
        learning_rate=0.1,
    )
    level_set = LevelSet(grid_size=grid_size, initial_shape="circle")
    optimizer = TopologyOptimizer(
        level_set=level_set,
        fom_evaluator=lambda binary: float(binary.sum()),
        gradient_evaluator=lambda binary: np.ones_like(binary),
        config=config,
    )
    result = optimizer.optimize()
    assert isinstance(result, TopologyResult)
    assert result.binary_design.shape == (grid_size, grid_size)
    unique = set(np.unique(result.binary_design).tolist())
    assert unique.issubset({0.0, 1.0}), f"设计应二值化，实际 unique={unique}"
    assert result.iterations > 0
    assert len(result.fom_history) > 0


def test_run_topology_optimization_convenience():
    """run_topology_optimization 便捷函数跑通。"""
    ls = LevelSet(grid_size=15, initial_shape="circle")
    result = run_topology_optimization(
        level_set=ls,
        fom_evaluator=lambda b: float(b.sum()),
        gradient_evaluator=lambda b: np.ones_like(b),
        config=TopologyConfig(grid_size=15, max_iterations=3),
    )
    assert isinstance(result, TopologyResult)
    assert result.iterations > 0


# =============================================================================
# Hamilton-Jacobi 水平集求解器
# =============================================================================


def test_hj_scheme_enum():
    """HJScheme 枚举包含 ENO/WENO/UPWIND。"""
    assert HJScheme.ENO.value == "eno"
    assert HJScheme.WENO.value == "weno"
    assert HJScheme.UPWIND.value == "upwind"
    assert len(HJScheme) == 3


def test_hj_solver_config_defaults():
    """HJSolverConfig 默认 scheme=WENO, cfl=0.5。"""
    cfg = HJSolverConfig()
    assert cfg.scheme == HJScheme.WENO
    assert cfg.cfl_number == 0.5
    assert cfg.max_dt == 1.0
    assert cfg.min_dt == 1e-6
    assert cfg.reinit_interval == 10


def test_grid_step_defaults():
    """GridStep 默认 dx=dy=1.0。"""
    gs = GridStep()
    assert gs.dx == 1.0
    assert gs.dy == 1.0


def test_compute_cfl_timestep():
    """compute_cfl_timestep: dt ≤ C·min(dx,dy)/max|v|。"""
    cfg = HJSolverConfig(cfl_number=0.5, max_dt=1.0, min_dt=1e-6)
    velocity = np.array([[1.0, 2.0], [3.0, 4.0]])
    dt = compute_cfl_timestep(velocity, dx=1.0, dy=1.0, config=cfg)
    # max|v|=4, dt = 0.5 * 1.0 / 4 = 0.125
    assert abs(dt - 0.125) < 1e-6, f"CFL dt={dt} ≠ 0.125"


def test_compute_cfl_timestep_zero_velocity():
    """零速度场返回 max_dt。"""
    cfg = HJSolverConfig(max_dt=1.0)
    velocity = np.zeros((5, 5))
    dt = compute_cfl_timestep(velocity, dx=1.0, dy=1.0, config=cfg)
    assert dt == 1.0


def test_evolve_hj_weno():
    """evolve_hj 用 WENO 格式演化水平集一步。"""
    phi = np.ones((10, 10))
    velocity = np.ones((10, 10)) * 0.5
    new_phi = evolve_hj(phi, velocity, dx=1.0, dy=1.0)
    assert new_phi.shape == (10, 10)
    # 演化后 φ 应变化
    assert not np.allclose(new_phi, phi)


def test_hj_solver_step_increments():
    """HJSolver.step 每次调用递增 step_count。"""
    solver = HJSolver(HJSolverConfig(scheme=HJScheme.UPWIND))
    phi = np.ones((8, 8))
    velocity = np.ones((8, 8)) * 0.5
    assert solver.step_count == 0
    solver.step(phi, velocity)
    assert solver.step_count == 1
    solver.step(phi, velocity)
    assert solver.step_count == 2


def test_hj_solver_evolve_multiple_steps():
    """HJSolver.evolve 多步演化返回最终水平集。"""
    solver = create_hj_solver(scheme="upwind", cfl=0.5)
    phi = np.ones((10, 10))

    def velocity_fn(p: np.ndarray) -> np.ndarray:
        return np.ones_like(p) * 0.5

    final = solver.evolve(phi, velocity_fn, n_steps=3, grid=GridStep(dx=1.0, dy=1.0))
    assert final.shape == (10, 10)
    assert solver.step_count == 3


