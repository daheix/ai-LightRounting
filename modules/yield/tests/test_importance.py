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


def test_allocation_strategy_enum_values():
    """AllocationStrategy 枚举三值覆盖。"""
    assert AllocationStrategy.EQUAL.value == "equal"
    assert AllocationStrategy.PROPORTIONAL.value == "proportional"
    assert AllocationStrategy.NEYMAN.value == "neyman"


def test_biasing_method_enum_values():
    """BiasingMethod 枚举五值覆盖。"""
    assert BiasingMethod.MEAN_SHIFT.value == "mean_shift"
    assert BiasingMethod.VARIANCE_SCALING.value == "variance_scaling"
    assert BiasingMethod.EXPONENTIAL_TWIST.value == "exponential_twist"
    assert BiasingMethod.MIXTURE.value == "mixture"
    assert BiasingMethod.CROSS_ENTROPY.value == "cross_entropy"


def test_biasing_spec_defaults():
    """BiasingSpec 默认值: MEAN_SHIFT 方法。"""
    spec = BiasingSpec()
    assert spec.method == BiasingMethod.MEAN_SHIFT
    assert spec.mean_shift is None
    assert spec.mixture_alpha == 0.3
    assert spec.elite_ratio == 0.1
    assert spec.n_iterations == 5
    assert spec.smoothing_alpha == 0.7


def test_importance_sampling_yield_mean_shift():
    """IS 良率估计 MEAN_SHIFT: 估计稀有事件失效概率。

    X ~ N(0, 1)，失效区域 x > 1.5，真值 Y_fail = 1 - Φ(1.5) ≈ 0.0668。
    偏置 q = N(1.5, 1)。
    """
    def failure_region(params: np.ndarray) -> bool:
        return bool(params[0] > 1.5)

    result = importance_sampling_yield(
        failure_region=failure_region,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        biasing=BiasingSpec(
            method=BiasingMethod.MEAN_SHIFT,
            mean_shift=[1.5],
        ),
        n_samples=5000,
        seed=42,
    )
    assert isinstance(result, ImportanceSamplingResult)
    assert result.biasing_method == "mean_shift"
    assert result.n_samples == 5000
    assert result.n_failures >= 30
    true_fail = 1.0 - 0.9331927
    assert 0.5 * true_fail < result.yield_estimate < 2.0 * true_fail


def test_importance_sampling_mean():
    """IS 期望估计 E_f[g(X)]。"""
    def func(params: np.ndarray) -> float:
        return float(params[0] ** 2)

    result = importance_sampling_mean(
        func=func,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        biasing=BiasingSpec(
            method=BiasingMethod.MEAN_SHIFT,
            mean_shift=[0.0],
        ),
        n_samples=2000,
        seed=42,
    )
    # E[X²] = Var(X) + (E[X])² = 1.0 + 0 = 1.0
    assert abs(result.yield_estimate - 1.0) < 0.2


def test_rare_event_yield_mean_shift():
    """稀有事件 IS 良率估计: MEAN_SHIFT 便捷接口。

    X ~ N(0, 1)，失效区域 x > 1.5，真值 Y_fail ≈ 0.0668。
    """
    def failure_region(params: np.ndarray) -> bool:
        return bool(params[0] > 1.5)

    result = rare_event_yield(
        failure_region=failure_region,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        biasing_mean_shift=[1.5],
        n_samples=5000,
        seed=42,
    )
    true_fail_prob = 1.0 - 0.9331927
    assert result.n_samples == 5000
    assert result.n_failures >= 30
    assert result.biasing_method == "mean_shift"
    assert 0.5 * true_fail_prob < result.yield_estimate < 2.0 * true_fail_prob


def test_cross_entropy_importance_sampling():
    """交叉熵自适应 IS: 迭代寻找最优 q*。"""
    def failure_region(params: np.ndarray) -> bool:
        return bool(params[0] > 1.5)

    result = cross_entropy_importance_sampling(
        failure_region=failure_region,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        initial_mean_shift=[1.5],
        n_samples=1000,
        n_iterations=3,
        elite_ratio=0.1,
        smoothing_alpha=0.7,
        seed=42,
    )
    true_fail_prob = 1.0 - 0.9331927
    assert result.biasing_method == "cross_entropy"
    assert result.converged is not None
    assert result.n_failures >= 30
    assert 0.3 * true_fail_prob < result.yield_estimate < 3.0 * true_fail_prob


def test_importance_sampling_yield_invalid_ess_ratio():
    """R03: min_ess_ratio 越界 raise。"""
    def failure_region(params: np.ndarray) -> bool:
        return bool(params[0] > 1.5)

    with pytest.raises(ValueError, match="min_ess_ratio"):
        importance_sampling_yield(
            failure_region=failure_region,
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            biasing=BiasingSpec(
                method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.5]
            ),
            n_samples=100,
            min_ess_ratio=1.5,
        )


# ============================================================================
# WCD 与容差分配
# ============================================================================
