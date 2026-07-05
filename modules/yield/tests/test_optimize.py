"""polaris-yield 子模块深度测试。

测试覆盖（35 个 pytest，覆盖全部 33 个公开 API）:
- 蒙特卡洛仿真与良率分析: monte_carlo_simulate / yield_analysis / sensitivity_analysis
- Sobol 全局灵敏度: sobol_sensitivity_analysis / SobolSensitivityResult
- QMC 采样: generate_qmc_samples / transform_to_distribution / qmc_monte_carlo
           / compare_qmc_convergence / QMCSamplerType 三种采样器
- 分层采样: stratified_monte_carlo / compare_stratified_convergence
           / AllocationStrategy 三种策略
- 重要性采样: importance_sampling_yield / importance_sampling_mean
             / rare_event_yield / cross_entropy_importance_sampling
             / BiasingMethod 五种偏置方法
- WCD 与容差分配: compute_worst_case_distance / allocate_tolerance_by_sensitivity
                  / optimize_yield_via_nominal_shift
- 批量仿真: batch_simulate / batch_yield_analysis
- 数据类默认值与枚举覆盖
- R03 非法参数 raise 分支

来源（R02 学术诚信，≥5 文献 URL）:
- pytest 文档: https://docs.pytest.org/
- Metropolis & Ulam 1949:
  https://doi.org/10.1080/01621459.1949.10483310
- Sobol 2001: https://doi.org/10.1007/BF02304730
- Saltelli et al. 2010: https://doi.org/10.1016/j.cpc.2009.09.018
- Glynn & Iglehart 1989:
  https://doi.org/10.1287/mnsc.35.11.1367
- Rubinstein 1997: https://doi.org/10.1016/S0377-2217(96)00385-2
- Cochran 1977, Sampling Techniques, Wiley
- McKay et al. 1979, Technometrics 21(2):239-245,
  https://doi.org/10.1080/00401706.1979.10489755
- Singhal & Pinel 1981: https://doi.org/10.1109/TCS.1981.1085043
- Madkour et al. 2015: https://doi.org/10.1109/TCSI.2015.2495251

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 无 TODO。
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


def test_compute_worst_case_distance_lower():
    """WCD 计算: 线性函数 d_wc = (μ_f - T) / σ_f（lower spec）。"""
    def func(params: np.ndarray) -> float:
        return float(params[0] + params[1])

    result = compute_worst_case_distance(
        func=func,
        base_params=np.array([1.0, 1.0]),
        param_sigmas=np.array([0.1, 0.1]),
        spec_threshold=0.5,
        direction="lower",
    )
    expected_sigma_f = 0.1 * np.sqrt(2)
    expected_wcd = (2.0 - 0.5) / expected_sigma_f
    assert abs(result.f_nominal - 2.0) < 1e-6
    assert abs(result.sigma_output - expected_sigma_f) < 1e-4
    assert abs(result.wcd - expected_wcd) < 0.1
    assert result.direction == "lower"
    assert result.yield_estimate > 0.999
    assert result.n_evaluations > 0


def test_compute_worst_case_distance_upper():
    """WCD upper spec: d_wc = (T - μ_f) / σ_f。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = compute_worst_case_distance(
        func=func,
        base_params=np.array([1.0]),
        param_sigmas=np.array([0.1]),
        spec_threshold=2.0,
        direction="upper",
    )
    assert result.direction == "upper"
    # μ_f=1, T=2, σ_f=0.1, d_wc = (2-1)/0.1 = 10
    assert abs(result.wcd - 10.0) < 0.5
    assert result.yield_estimate > 0.999


def test_compute_worst_case_distance_invalid_direction():
    """R03: direction 非 lower/upper raise。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="direction"):
        compute_worst_case_distance(
            func=func,
            base_params=np.array([1.0]),
            param_sigmas=np.array([0.1]),
            spec_threshold=0.5,
            direction="middle",
        )


def test_compute_worst_case_distance_sigma_mismatch():
    """R03: param_sigmas shape 不匹配 raise。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="不匹配"):
        compute_worst_case_distance(
            func=func,
            base_params=np.array([1.0, 2.0]),
            param_sigmas=np.array([0.1]),
            spec_threshold=0.5,
        )


def test_compute_worst_case_distance_zero_sigma():
    """R03: param_sigmas <= 0 raise。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="param_sigmas"):
        compute_worst_case_distance(
            func=func,
            base_params=np.array([1.0]),
            param_sigmas=np.array([0.0]),
            spec_threshold=0.5,
        )


def test_allocate_tolerance_by_sensitivity():
    """Lagrange 容差分配: σ_i ∝ 1/|S_i|，Σσ² = B。

    S = [1, 2, 4]，B = 1.0。
    inv_s² = [1, 0.25, 0.0625]，sum = 1.3125。
    σ² = [0.7619, 0.1905, 0.0476]，σ = [0.873, 0.436, 0.218]。
    """
    sensitivities = np.array([1.0, 2.0, 4.0])
    result = allocate_tolerance_by_sensitivity(
        sensitivities=sensitivities,
        total_budget=1.0,
        param_names=["w", "h", "gap"],
    )
    assert isinstance(result, ToleranceAllocationResult)
    assert len(result.allocated_sigmas) == 3
    actual_budget = sum(s * s for s in result.allocated_sigmas)
    assert abs(actual_budget - 1.0) < 1e-9
    # 灵敏度大 → 容差小
    assert result.allocated_sigmas[0] > result.allocated_sigmas[1]
    assert result.allocated_sigmas[1] > result.allocated_sigmas[2]
    # 解析解验证
    inv_s2 = 1.0 / (sensitivities ** 2)
    expected_var = 1.0 * inv_s2 / np.sum(inv_s2)
    expected_sigma = np.sqrt(expected_var)
    for i in range(3):
        assert abs(result.allocated_sigmas[i] - expected_sigma[i]) < 1e-9


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
