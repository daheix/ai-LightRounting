"""polaris-optimizer 子模块 smoke 测试。

测试覆盖（≥3 个 pytest）:
- test_lbfgs_quadratic_convergence: L-BFGS 收敛到二次函数极值
- test_pso_sphere_improvement: PSO 在球函数上 FoM 改善
- test_topology_level_set_runs: 拓扑优化水平集能跑通
- test_nsga2_zdt1_pareto: NSGA-II 在 ZDT1 上产生帕累托前沿
- test_robust_mean_mode_runs: 鲁棒优化（均值模式）能跑通
- test_shape_adjoint_analytical_runs: 形状伴随（解析后端）能跑通
- test_feedback_overlap_hint: FeedbackAdapter 处理 OVERLAP 违规
- test_density_adjoint_mmi_runs: 密度伴随 MMI 示例能跑通（需 JAX）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Liu & Nocedal 1989 L-BFGS: https://doi.org/10.1007/BF01589116
- Kennedy & Eberhart 1995 PSO:
  https://doi.org/10.1109/ICNN.1995.488968
- Deb et al. 2002 NSGA-II: https://doi.org/10.1109/4235.996017
- Zitzler-Deb-Thiele ZDT1 测试问题:
  https://doi.org/10.1109/4235.996017
- Osher & Sethian 1988 Level Set:
  https://doi.org/10.1016/S0021-9991(88)80002-2
- Piggott 2017 Nature Photonics:
  https://www.nature.com/articles/nphoton.2017.102
- Apollo 2025 反馈适配: https://arxiv.org/html/2504.18813v1
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
    FeedbackAdapter,
    LBFGSConfig,
    LBFGSOptimizer,
    LevelSet,
    NSGA2Config,
    NSGA2Optimizer,
    Objective,
    ObjectiveType,
    ParameterizedGeometry,
    PSOConfig,
    ParticleSwarmOptimizer,
    RobustConfig,
    RobustMode,
    RobustOptimizer,
    ShapeAdjointConfig,
    ShapeAdjointOptimizer,
    ToleranceModel,
    ToleranceType,
    TopologyConfig,
    TopologyOptimizer,
    Violation,
    ViolationType,
    dominates,
)


def test_lbfgs_quadratic_convergence():
    """L-BFGS 在二次函数 f(x) = -||x - x*||² 上最大化收敛。

    极大化二次函数 → 最优解 x* = [1, 1, 1]。
    L-BFGS 在二次函数上理论应快速收敛（Nocedal & Wright 2006 §7.1）。
    """
    x_star = np.array([1.0, 1.0, 1.0])

    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - x_star) ** 2))

    def grad_fn(x: np.ndarray) -> np.ndarray:
        return -2.0 * (x - x_star)

    optimizer = LBFGSOptimizer(
        LBFGSConfig(max_iterations=50, convergence_threshold=1e-6)
    )
    result = optimizer.optimize(
        initial_params=np.array([0.0, 0.0, 0.0]),
        fom_fn=fom_fn,
        grad_fn=grad_fn,
    )
    # 验证收敛到 x*
    assert result.converged, f"L-BFGS 未收敛，iterations={result.iterations}"
    err = float(np.linalg.norm(result.optimal_params - x_star))
    assert err < 1e-3, f"最优解误差 {err} ≥ 1e-3，params={result.optimal_params}"
    # FoM 应接近 0（极大值）
    assert abs(result.optimal_fom) < 1e-6, f"optimal_fom={result.optimal_fom}"


def test_pso_sphere_improvement():
    """PSO 在球函数 f(x) = -||x||² 上显著改善。

    极大化 → 最优解 x* = 0，FoM* = 0。
    PSO 收敛较慢但应显著改善（Kennedy & Eberhart 1995）。
    """
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum(x**2))

    config = PSOConfig(
        num_particles=20,
        max_iterations=50,
        seed=42,
    )
    optimizer = ParticleSwarmOptimizer(config)
    bounds = (
        np.array([-2.0, -2.0, -2.0]),
        np.array([2.0, 2.0, 2.0]),
    )
    result = optimizer.optimize(
        initial_pos=np.zeros(3),
        fom_fn=fom_fn,
        bounds=bounds,
    )
    # 最优 FoM 应改善（接近 0）
    assert result.optimal_fom >= -1.0, (
        f"PSO 最优 FoM {result.optimal_fom} 过差"
    )
    # 最优参数应接近原点
    err = float(np.linalg.norm(result.optimal_params))
    assert err < 1.5, f"PSO 最优参数离原点过远: ||x||={err}"


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
    assert result.binary_design.shape == (grid_size, grid_size), (
        f"设计形状错误: {result.binary_design.shape}"
    )
    # 二值化设计应为 0/1
    unique = set(np.unique(result.binary_design).tolist())
    assert unique.issubset({0.0, 1.0}), f"设计应二值化，实际 unique={unique}"
    assert result.iterations > 0
    assert len(result.fom_history) > 0


def test_nsga2_zdt1_pareto():
    """NSGA-II 在 ZDT1 测试问题上产生非支配帕累托前沿。

    ZDT1（Zitzler-Deb-Thiele 2000）:
        min f1 = x1
        min f2 = g(x) · [1 - sqrt(f1/g(x))]
        g(x) = 1 + 9/(n-1) · Σ x_i,  x_i ∈ [0,1]

    URL: https://doi.org/10.1109/4235.996017
    """
    n_params = 5

    def fom_fn(x: np.ndarray) -> np.ndarray:
        f1 = x[0]
        g = 1.0 + 9.0 / (n_params - 1) * float(np.sum(x[1:]))
        f2 = g * (1.0 - np.sqrt(max(f1, 0.0) / g))
        return np.array([f1, f2])

    objectives = [
        Objective(name="f1", type=ObjectiveType.MINIMIZE),
        Objective(name="f2", type=ObjectiveType.MINIMIZE),
    ]
    config = NSGA2Config(
        population_size=30,
        max_generations=10,
        bounds=[(0.0, 1.0)] * n_params,
        seed=42,
    )
    optimizer = NSGA2Optimizer(
        objectives=objectives,
        fom_fn=fom_fn,
        config=config,
    )
    result = optimizer.optimize(n_params=n_params)
    # 验证产生帕累托前沿
    assert len(result.pareto_front) > 0, "帕累托前沿为空"
    # 验证前沿中解为非支配（使用模块自带 dominates 函数）
    for i, ind_i in enumerate(result.pareto_front):
        for j, ind_j in enumerate(result.pareto_front):
            if i != j:
                # ind_j 不应支配 ind_i
                dominated_by_j = dominates(
                    ind_j.objectives, ind_i.objectives, objectives
                )
                assert not dominated_by_j, (
                    f"前沿解 {i} 被解 {j} 支配: "
                    f"{ind_i.objectives} vs {ind_j.objectives}"
                )


def test_robust_mean_mode_runs():
    """鲁棒优化（均值模式 + 高斯公差）能跑通。

    公差模型: x → x + N(0, σ²)，目标 = mean(FoM)（Wang 2018）。
    """
    def fom_fn(x: np.ndarray) -> float:
        return -float(np.sum((x - 1.0) ** 2))

    tolerance = ToleranceModel(
        tol_type=ToleranceType.GAUSSIAN,
        relative_std=0.05,
        seed=42,
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
    assert result.iterations > 0
    assert len(result.fom_history) > 0
    assert np.isfinite(result.optimal_fom), (
        f"optimal_fom 非有限: {result.optimal_fom}"
    )


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
    assert result.iterations > 0
    # FoM 应为正（sin² 在 [0,1]）
    assert result.optimal_fom > 0.0, f"optimal_fom={result.optimal_fom}"
    assert result.optimal_fom <= 1.0 + 1e-6


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
    assert result.should_retry is True
    assert len(result.placement_hints) == 2, (
        f"期望 2 个布局建议，实际 {len(result.placement_hints)}"
    )
    # OVERLAP → dx=dy=50
    overlap_hint = next(
        h for h in result.placement_hints if "重叠" in h.reason
    )
    assert overlap_hint.dx == 50.0
    assert overlap_hint.dy == 50.0
    assert overlap_hint.priority == 1.0
    # SPACING → dx=20*(1+0.5)=30
    spacing_hint = next(
        h for h in result.placement_hints if "间距" in h.reason
    )
    assert abs(spacing_hint.dx - 30.0) < 1e-6, f"spacing dx={spacing_hint.dx}"


def test_density_adjoint_mmi_runs():
    """密度法拓扑伴随优化 MMI 1×2 示例能跑通（需 JAX）。

    验证 JAX autograd + 锥形滤波 + tanh-sigmoid 投影流程完整。
    来源: Piggott 2017 https://www.nature.com/articles/nphoton.2017.102
    """
    pytest.importorskip(
        "jax",
        reason="density_adjoint 测试需要 JAX: pip install polaris-optimizer[density]",
    )
    from polaris_optimizer.density_adjoint import example_mmi_1x2

    result = example_mmi_1x2()
    assert "device" in result
    assert "result" in result
    assert "insertion_loss_db" in result
    topo_result = result["result"]
    assert topo_result.optimal_design.ndim == 2
    assert topo_result.iterations > 0
    # 二值化设计
    unique = set(np.unique(topo_result.optimal_design).tolist())
    assert unique.issubset({0.0, 1.0}), (
        f"设计应二值化，实际 unique={unique}"
    )
