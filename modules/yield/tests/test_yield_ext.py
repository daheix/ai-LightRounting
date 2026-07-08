"""扩展测试（从 test_yield.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_yield.py。
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

import polaris_yield  # noqa: E402
from polaris_yield import (  # noqa: E402
    AllocationStrategy,
    BatchScenarioResult,
    BatchSimulationResult,
    BatchYieldResult,
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
    MonteCarloResult,
    QMCConvergenceComparison,
    QMCMonteCarloResult,
    QMCSampleResult,
    QMCSamplerType,
    SobolSensitivityResult,
    StratifiedSamplingResult,
    ToleranceAllocationResult,
    WorstCaseDistanceResult,
    YieldOptimizationResult,
    allocate_tolerance_by_sensitivity,
    batch_simulate,
    batch_yield_analysis,
    compare_qmc_convergence,
    compare_stratified_convergence,
    compute_worst_case_distance,
    cross_entropy_importance_sampling,
    generate_qmc_samples,
    importance_sampling_mean,
    importance_sampling_yield,
    monte_carlo_simulate,
    optimize_yield_via_nominal_shift,
    qmc_monte_carlo,
    rare_event_yield,
    sensitivity_analysis,
    sobol_sensitivity_analysis,
    stratified_monte_carlo,
    transform_to_distribution,
    yield_analysis,
)


# ============================================================================
# 蒙特卡洛仿真与良率分析
# ============================================================================


def test_allocate_tolerance_negative_sensitivity():
    """R03: 灵敏度为负 raise（须上游 abs 处理）。"""
    with pytest.raises(ValueError, match="非负"):
        allocate_tolerance_by_sensitivity(
            sensitivities=np.array([1.0, -1.0, 2.0]),
            total_budget=1.0,
        )


def test_allocate_tolerance_all_zero():
    """R03: 所有灵敏度为 0 raise。"""
    with pytest.raises(ValueError, match="所有灵敏度 = 0"):
        allocate_tolerance_by_sensitivity(
            sensitivities=np.array([0.0, 0.0]),
            total_budget=1.0,
        )


def test_allocate_tolerance_invalid_budget():
    """R03: total_budget <= 0 raise。"""
    with pytest.raises(ValueError, match="total_budget"):
        allocate_tolerance_by_sensitivity(
            sensitivities=np.array([1.0, 2.0]),
            total_budget=0.0,
        )


def test_optimize_yield_via_nominal_shift():
    """标称值良率优化: WCD 梯度上升，WCD 应提升。"""
    def func(params: np.ndarray) -> float:
        return float(params[0] + params[1])

    result = optimize_yield_via_nominal_shift(
        func=func,
        base_params=np.array([0.6, 0.6]),
        param_sigmas=np.array([0.1, 0.1]),
        spec_threshold=0.5,
        direction="lower",
        max_iter=20,
        learning_rate=0.5,
    )
    assert isinstance(result, YieldOptimizationResult)
    assert result.optimized_wcd >= result.original_wcd - 1e-6
    assert result.iterations > 0
    assert len(result.wcd_history) > 0
    assert np.all(result.optimal_params >= result.original_params - 1e-6)


# ============================================================================
# 批量仿真
# ============================================================================


def test_batch_simulate():
    """批量仿真: 多标称点 MC，每场景均值 ≈ 标称输出。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = batch_simulate(
        func=func,
        base_params_list=[np.array([1.0]), np.array([2.0]), np.array([3.0])],
        param_sigmas=np.array([0.05]),
        n_samples=200,
        seed=42,
    )
    assert isinstance(result, BatchSimulationResult)
    assert isinstance(result.scenarios[0], BatchScenarioResult)
    assert result.n_scenarios == 3
    assert len(result.scenarios) == 3
    assert result.total_evaluations == 600
    for sid, expected_mean in enumerate([1.0, 2.0, 3.0]):
        sc = result.scenarios[sid]
        assert sc.scenario_id == sid
        assert abs(sc.mean - expected_mean) < 0.05
        assert sc.n_samples == 200
    assert result.execution_time_s >= 0.0


def test_batch_yield_analysis():
    """批量良率分析: 多场景良率计算。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    def spec_func(output: float) -> bool:
        return output >= 0.3

    result = batch_yield_analysis(
        func=func,
        base_params_list=[
            np.array([0.5]), np.array([1.0]), np.array([2.0]),
        ],
        param_sigmas=np.array([0.1]),
        spec_func=spec_func,
        n_samples=200,
        seed=42,
    )
    assert isinstance(result, BatchYieldResult)
    assert result.n_scenarios == 3
    assert len(result.yields) == 3
    assert result.total_evaluations == 600
    for y in result.yields:
        assert 0.0 <= y <= 1.0
    assert result.yields[0] <= result.yields[1] <= result.yields[2]


# ============================================================================
# 数据类与包级 API
# ============================================================================


def test_monte_carlo_result_dataclass():
    """MonteCarloResult 数据类字段可构造。"""
    samples = np.array([1.0, 2.0, 3.0])
    r = MonteCarloResult(
        samples=samples,
        mean=np.array(2.0),
        std=np.array(1.0),
        min=np.array(1.0),
        max=np.array(3.0),
        percentile_95=np.array(2.9),
        percentile_05=np.array(1.1),
    )
    assert r.samples.shape == (3,)
    assert float(r.mean) == 2.0


def test_package_version_and_api():
    """polaris_yield 包级 API 完整性。"""
    assert polaris_yield.__version__ == "5.0.0"
    # 核心函数存在
    assert callable(polaris_yield.monte_carlo_simulate)
    assert callable(polaris_yield.sobol_sensitivity_analysis)
    assert callable(polaris_yield.qmc_monte_carlo)
    assert callable(polaris_yield.stratified_monte_carlo)
    assert callable(polaris_yield.importance_sampling_yield)
    assert callable(polaris_yield.cross_entropy_importance_sampling)
    assert callable(polaris_yield.compute_worst_case_distance)
    assert callable(polaris_yield.allocate_tolerance_by_sensitivity)
    assert callable(polaris_yield.optimize_yield_via_nominal_shift)
    assert callable(polaris_yield.batch_simulate)
    assert callable(polaris_yield.batch_yield_analysis)
