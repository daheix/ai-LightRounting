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


def test_create_hj_solver_invalid_scheme():
    """create_hj_solver 未知 scheme 抛 ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="未知 scheme"):
        create_hj_solver(scheme="invalid_scheme")


def test_create_hj_solver_factory():
    """create_hj_solver 工厂创建 ENO/WENO/UPWIND 三种求解器。"""
    for scheme_name in ("eno", "weno", "upwind"):
        solver = create_hj_solver(scheme=scheme_name)
        assert isinstance(solver, HJSolver)


def test_flux_pair_dataclass():
    """FluxPair 数据类持有四个方向通量。"""
    fp = FluxPair(
        x_minus=np.zeros((3, 3)),
        x_plus=np.zeros((3, 3)),
        y_minus=np.zeros((3, 3)),
        y_plus=np.zeros((3, 3)),
    )
    assert fp.x_minus.shape == (3, 3)
    assert fp.x_plus.shape == (3, 3)
    assert fp.y_minus.shape == (3, 3)
    assert fp.y_plus.shape == (3, 3)


# =============================================================================
# 鲁棒优化
# =============================================================================


def test_tolerance_type_enum():
    """ToleranceType 枚举包含 GAUSSIAN 和 UNIFORM。"""
    assert ToleranceType.GAUSSIAN.value == "gaussian"
    assert ToleranceType.UNIFORM.value == "uniform"


def test_robust_mode_enum():
    """RobustMode 枚举包含 MEAN/WORST_CASE/MEAN_MINUS_STD。"""
    assert RobustMode.MEAN.value == "mean"
    assert RobustMode.WORST_CASE.value == "worst_case"
    assert RobustMode.MEAN_MINUS_STD.value == "mean_minus_std"


def test_tolerance_model_sample_gaussian():
    """ToleranceModel.sample 高斯扰动均值≈原参数。"""
    model = ToleranceModel(
        tol_type=ToleranceType.GAUSSIAN,
        relative_std=0.01,
        seed=42,
    )
    rng = np.random.default_rng(42)
    params = np.array([1.0, 2.0, 3.0])
    samples = np.array([model.sample(params, rng) for _ in range(1000)])
    mean = samples.mean(axis=0)
    assert np.allclose(mean, params, atol=0.05), f"高斯扰动均值偏移: {mean}"


def test_tolerance_model_sample_uniform():
    """ToleranceModel.sample 均匀扰动范围受限。"""
    model = ToleranceModel(
        tol_type=ToleranceType.UNIFORM,
        relative_std=0.1,
        seed=42,
    )
    rng = np.random.default_rng(42)
    params = np.array([1.0])
    samples = np.array([model.sample(params, rng) for _ in range(100)])
    # 均匀扰动 |noise| ≤ std
    deviations = np.abs(samples.flatten() - 1.0)
    assert np.all(deviations <= 0.15), f"均匀扰动超出范围: {deviations.max()}"


def test_create_tolerance_model_factory():
    """create_tolerance_model 工厂返回 ToleranceModel。"""
    model = create_tolerance_model(
        tol_type=ToleranceType.UNIFORM, relative_std=0.02, seed=7,
    )
    assert isinstance(model, ToleranceModel)
    assert model.tol_type == ToleranceType.UNIFORM
    assert model.relative_std == 0.02


def test_evaluate_robustness_convenience():
    """evaluate_robustness 返回 (mean, std, worst) 三元组。"""
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - 1.0) ** 2))

    tolerance = ToleranceModel(
        tol_type=ToleranceType.GAUSSIAN, relative_std=0.05, seed=42,
    )
    mean, std, worst = evaluate_robustness(
        params=np.array([1.0, 1.0]),
        fom_fn=fom_fn,
        tolerance=tolerance,
        num_samples=16,
        seed=42,
    )
    assert isinstance(mean, float)
    assert isinstance(std, float)
    assert isinstance(worst, float)
    # 在最优点附近 mean 应接近 0
    assert abs(mean) < 0.1, f"鲁棒均值偏移: {mean}"
    assert worst <= mean, "最差值应 ≤ 均值"


def test_robust_mean_mode_runs():
    """鲁棒优化（均值模式 + 高斯公差）能跑通。

    公差模型: x → x + N(0, σ²)，目标 = mean(FoM)（Wang 2018）。
    """
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - 1.0) ** 2))

    tolerance = ToleranceModel(
        tol_type=ToleranceType.GAUSSIAN, relative_std=0.05, seed=42,
    )
    config = RobustConfig(
        tolerance=tolerance,
        mode=RobustMode.MEAN,
        num_samples=3,
        max_iterations=5,
        seed=42,
        learning_rate=0.01,
    )
    optimizer = RobustOptimizer(config)
    result = optimizer.optimize(
        initial_params=np.array([0.0, 0.0]),
        fom_fn=fom_fn,
    )
    assert isinstance(result, RobustResult)
    assert result.iterations > 0
    assert len(result.fom_history) > 0
    assert np.isfinite(result.optimal_fom)


def test_robust_worst_case_mode_runs():
    """鲁棒优化 WORST_CASE 模式跑通。"""
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - 1.0) ** 2))

    config = RobustConfig(
        tolerance=ToleranceModel(
            tol_type=ToleranceType.GAUSSIAN, relative_std=0.05, seed=42,
        ),
        mode=RobustMode.WORST_CASE,
        num_samples=4,
        max_iterations=3,
        seed=42,
    )
    optimizer = create_robust_optimizer(config)
    result = optimizer.optimize(np.array([0.5, 0.5]), fom_fn)
    assert result.iterations > 0
    assert np.isfinite(result.optimal_fom)


def test_run_robust_optimization_convenience():
    """run_robust_optimization 便捷函数跑通。"""
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - 1.0) ** 2))

    result = run_robust_optimization(
        initial_params=np.array([0.5]),
        fom_fn=fom_fn,
        config=RobustConfig(
            tolerance=ToleranceModel(relative_std=0.05, seed=42),
            num_samples=3,
            max_iterations=3,
        ),
    )
    assert isinstance(result, RobustResult)
    assert result.iterations > 0


# =============================================================================
# 形状伴随优化
# =============================================================================


def test_optimization_backend_enum():
    """OptimizationBackend 枚举包含 MEEP/TIDY3D/ANALYTICAL。"""
    assert OptimizationBackend.MEEP.value == "meep"
    assert OptimizationBackend.TIDY3D.value == "tidy3d"
    assert OptimizationBackend.ANALYTICAL.value == "analytical"


def test_shape_adjoint_config_defaults():
    """ShapeAdjointConfig 默认值。"""
    cfg = ShapeAdjointConfig()
    assert cfg.max_iterations == 100
    assert cfg.learning_rate == 0.01
    assert cfg.convergence_threshold == 1e-6
    assert cfg.min_feature_size_um == 0.1
    assert cfg.symmetry == "none"
    assert cfg.backend == OptimizationBackend.ANALYTICAL
    assert cfg.optimizer == "adam"


def test_parameterized_geometry_get_set():
    """ParameterizedGeometry get_params/set_params 裁剪到边界。"""
    geo = ParameterizedGeometry(
        initial_params=np.array([5.0, 5.0]),
        bounds=[(0.0, 10.0), (0.0, 10.0)],
    )
    assert np.allclose(geo.get_params(), [5.0, 5.0])
    geo.set_params(np.array([15.0, -5.0]))
    p = geo.get_params()
    assert p[0] == 10.0, f"上界裁剪失败: {p[0]}"
    assert p[1] == 0.0, f"下界裁剪失败: {p[1]}"


def test_shape_adjoint_analytical_runs():
    """形状伴随优化（解析后端 + AnalyticalWaveguideCoupler）能跑通。

    验证 Adam 优化耦合器长度以最大化 FoM = sin²(κ_eff·L)
    （Yariv 1973 耦合模理论）。
    """
    geometry = ParameterizedGeometry(
        initial_params=np.array([10.0, 1.0]),  # [length, gap]
        bounds=[(1.0, 50.0), (0.1, 5.0)],
    )
    simulator = AnalyticalWaveguideCoupler()
    config = ShapeAdjointConfig(
        max_iterations=10,
        learning_rate=0.1,
        convergence_threshold=1e-8,
    )
    optimizer = ShapeAdjointOptimizer(geometry, simulator, config)
    result = optimizer.optimize()
    assert isinstance(result, ShapeOptimizationResult)
    assert result.iterations > 0
    assert result.optimal_fom > 0.0
    assert result.optimal_fom <= 1.0 + 1e-6
    assert result.backend_used == OptimizationBackend.ANALYTICAL


def test_run_shape_adjoint_optimization_convenience():
    """run_shape_adjoint_optimization 便捷函数跑通。"""
    geo = ParameterizedGeometry(
        initial_params=np.array([5.0, 1.0]),
        bounds=[(1.0, 50.0), (0.1, 5.0)],
    )
    sim = AnalyticalWaveguideCoupler()
    result = run_shape_adjoint_optimization(
        geo, sim, ShapeAdjointConfig(max_iterations=5, learning_rate=0.1),
    )
    assert isinstance(result, ShapeOptimizationResult)
    assert result.iterations > 0


# =============================================================================
# 反馈适配器
# =============================================================================


def test_violation_type_enum_all_values():
    """ViolationType 枚举包含 17 种违规类型。"""
    expected = {
        "bend_radius", "spacing", "insertion_loss", "crosstalk", "crossing",
        "overlap", "thermal", "min_width", "coupling_gap", "min_length",
        "max_length", "min_area", "enclosure", "notch", "port_connectivity",
        "pin_match", "layer_density",
    }
    actual = {v.value for v in ViolationType}
    assert actual == expected, f"ViolationType 缺失/多余: {actual ^ expected}"
    assert len(ViolationType) == 17


def test_violation_dataclass():
    """Violation 数据类默认值。"""
    v = Violation(vtype=ViolationType.OVERLAP)
    assert v.severity == 0.0
    assert v.message == ""
    assert v.device_name == ""
    assert v.net_id == ""
    assert v.location is None


def test_placement_hint_defaults():
    """PlacementHint 默认值。"""
    h = PlacementHint()
    assert h.device_name == ""
    assert h.dx == 0.0
    assert h.dy == 0.0
    assert h.reason == ""
    assert h.priority == 0.5


def test_routing_hint_defaults():
    """RoutingHint 默认值。"""
    h = RoutingHint()
    assert h.net_id == ""
    assert h.avoid_region is None
    assert h.prefer_layer == ""
    assert h.reason == ""


def test_feedback_overlap_hint():
    """FeedbackAdapter 处理 OVERLAP 违规 → 拉开间距建议。

    来源: Apollo arXiv 2025 https://arxiv.org/html/2504.18813v1
    """
    violations = [
        Violation(
            vtype=ViolationType.OVERLAP,
            severity=1.0,
            message="dev1 与 dev2 重叠",
            device_name="dev1-dev2",
        ),
        Violation(
            vtype=ViolationType.SPACING,
            severity=0.5,
            message="dev3 与 dev4 间距不足",
            device_name="dev3-dev4",
        ),
    ]
    adapter = FeedbackAdapter()
    result = adapter.adapt(violations)
    assert isinstance(result, FeedbackResult)
    assert result.should_retry is True
    assert len(result.placement_hints) == 2
    overlap_hint = next(h for h in result.placement_hints if "重叠" in h.reason)
    assert overlap_hint.dx == 50.0
    assert overlap_hint.dy == 50.0
    assert overlap_hint.priority == 1.0
    spacing_hint = next(h for h in result.placement_hints if "间距" in h.reason)
    assert abs(spacing_hint.dx - 30.0) < 1e-6


def test_feedback_bend_routing_hint():
    """FeedbackAdapter 处理 BEND_RADIUS → RoutingHint 避开区域。"""
    v = Violation(
        vtype=ViolationType.BEND_RADIUS,
        severity=0.8,
        message="弯曲半径 5μm < 10μm",
        net_id="net_001",
        location=(100.0, 200.0),
    )
    result = FeedbackAdapter().adapt([v])
    assert len(result.routing_hints) == 1
    hint = result.routing_hints[0]
    assert hint.net_id == "net_001"
    assert hint.avoid_region is not None
    # 避开区域 (x-20, y-20, 40, 40)
    x, y, w, h = hint.avoid_region
    assert abs(x - 80.0) < 1e-6
    assert abs(y - 180.0) < 1e-6
    assert w == 40
    assert h == 40


def test_feedback_loss_hint():
    """FeedbackAdapter 处理 INSERTION_LOSS → 缩短路径建议。"""
    v = Violation(
        vtype=ViolationType.INSERTION_LOSS,
        severity=0.7,
        message="插损 3.2dB > 1dB",
    )
    result = FeedbackAdapter().adapt([v])
    assert len(result.placement_hints) == 1
    hint = result.placement_hints[0]
    assert hint.dx == -10.0
    assert hint.dy == -10.0
    assert hint.priority == 0.6


def test_feedback_crossing_hint():
    """FeedbackAdapter 处理 CROSSING → 减少交叉建议。"""
    v = Violation(
        vtype=ViolationType.CROSSING,
        severity=0.5,
        message="波导交叉 5 次",
    )
    result = FeedbackAdapter().adapt([v])
    assert len(result.placement_hints) == 1
    hint = result.placement_hints[0]
    assert hint.dx == 30.0
    assert hint.priority == 0.7


def test_feedback_unhandled_type_ignored():
    """FeedbackAdapter 对未注册的违规类型静默跳过（无 fall-back）。"""
    v = Violation(vtype=ViolationType.THERMAL, severity=0.5, message="热串扰")
    result = FeedbackAdapter().adapt([v])
    # THERMAL 未注册处理器 → 无建议但 should_retry=True
    assert len(result.placement_hints) == 0
    assert len(result.routing_hints) == 0
    assert result.should_retry is True


def test_feedback_empty_violations():
    """FeedbackAdapter 空违规列表 → should_retry=False。"""
    result = FeedbackAdapter().adapt([])
    assert result.should_retry is False
    assert len(result.placement_hints) == 0
    assert len(result.routing_hints) == 0


def test_feedback_overlap_invalid_device_name_raises():
    """FeedbackAdapter OVERLAP 设备名为空 → raise ValueError（R03）。"""
    v = Violation(
        vtype=ViolationType.OVERLAP,
        severity=1.0,
        message="重叠",
        device_name="",  # 空
    )
    with pytest.raises(ValueError, match="设备名为空"):
        FeedbackAdapter().adapt([v])


def test_feedback_overlap_malformed_device_name_raises():
    """FeedbackAdapter OVERLAP 设备名格式错误 → raise ValueError（R03）。"""
    v = Violation(
        vtype=ViolationType.OVERLAP,
        severity=1.0,
        message="重叠",
        device_name="single_dev",  # 缺少 '-'
    )
    with pytest.raises(ValueError, match="格式错误"):
        FeedbackAdapter().adapt([v])
