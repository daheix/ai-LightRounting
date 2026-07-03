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


def test_monte_carlo_simulate_linear_mean():
    """蒙特卡洛仿真: 线性函数均值收敛到标称输出。

    f(x) = x[0] + x[1]，base = [1.0, 2.0]，σ = 0.01。
    E[f] = 3.0（一阶近似，二阶项 << 1）。
    """
    def func(params: np.ndarray) -> float:
        return float(params[0] + params[1])

    result = monte_carlo_simulate(
        func=func,
        base_params=np.array([1.0, 2.0]),
        n_samples=500,
        sigma=0.01,
        seed=42,
    )
    assert result.samples.shape == (500,)
    assert abs(result.mean - 3.0) < 0.05, f"均值期望≈3.0，实际 {result.mean}"
    assert result.std >= 0.0
    assert result.min <= result.mean <= result.max


def test_monte_carlo_simulate_percentile_ordering():
    """蒙特卡洛仿真: 5/95 百分位顺序与 min/max 一致。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = monte_carlo_simulate(
        func=func,
        base_params=np.array([1.0]),
        n_samples=200,
        sigma=0.2,
        seed=7,
    )
    assert result.percentile_05 <= result.percentile_95
    assert result.min <= result.percentile_05
    assert result.percentile_95 <= result.max


def test_monte_carlo_simulate_invalid_n_samples():
    """R03: n_samples <= 0 raise ValueError。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="n_samples"):
        monte_carlo_simulate(func, np.array([1.0]), n_samples=0)


def test_monte_carlo_simulate_invalid_sigma():
    """R03: sigma < 0 raise ValueError。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="sigma"):
        monte_carlo_simulate(func, np.array([1.0]), n_samples=10, sigma=-0.1)


def test_yield_analysis_high_yield():
    """蒙特卡洛良率分析: 良率在 [0, 1] 且与通过数一致。

    f(x) = x[0]，base = [1.0]，σ = 0.1，spec: f >= 0.5。
    标称 f=1.0，σ_f=0.1，Y ≈ Φ((1.0-0.5)/0.1) = Φ(5) ≈ 1.0。
    """
    def func(params: np.ndarray) -> float:
        return float(params[0])

    def spec_func(output: float) -> bool:
        return output >= 0.5

    result = yield_analysis(
        func=func,
        base_params=np.array([1.0]),
        spec_func=spec_func,
        n_samples=500,
        sigma=0.1,
        seed=42,
    )
    assert 0.0 <= result["yield"] <= 1.0
    assert result["n_pass"] == int(result["yield"] * result["n_total"])
    assert result["n_total"] == 500
    assert result["yield"] > 0.95, f"良率期望>0.95，实际 {result['yield']}"


def test_yield_analysis_zero_yield():
    """蒙特卡洛良率分析: 标称远离规格 → 良率近 0。

    f(x) = x[0]，base = [0.0]，σ = 0.01，spec: f >= 1.0。
    """
    def func(params: np.ndarray) -> float:
        return float(params[0])

    def spec_func(output: float) -> bool:
        return output >= 1.0

    result = yield_analysis(
        func=func,
        base_params=np.array([0.0]),
        spec_func=spec_func,
        n_samples=300,
        sigma=0.01,
        seed=42,
    )
    assert result["yield"] < 0.05


def test_sensitivity_analysis_linear():
    """灵敏度分析: 线性函数归一化灵敏度 = 1。"""
    def func(params: np.ndarray) -> float:
        return float(2.0 * params[0] + 3.0 * params[1])

    result = sensitivity_analysis(
        func=func,
        base_params=np.array([1.0, 1.0]),
        param_names=["x", "y"],
    )
    # f = 2x + 3y, S_x = (∂f/∂x)·(x/f) = 2·(1/5) = 0.4
    assert abs(result["x"] - 0.4) < 1e-4
    assert abs(result["y"] - 0.6) < 1e-4


def test_sensitivity_analysis_param_names_mismatch():
    """R03: param_names 长度不匹配 raise ValueError。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="param_names"):
        sensitivity_analysis(
            func=func,
            base_params=np.array([1.0, 2.0]),
            param_names=["only_one"],
        )


# ============================================================================
# Sobol 全局灵敏度分析
# ============================================================================


def test_sobol_sensitivity_analysis_linear():
    """Sobol 全局灵敏度: 线性函数 S_i = Var_i / Var_total = 1/k（等贡献）。

    f(x) = x[0] + x[1] + x[2]，X_i ~ U(0,1) 独立同分布。
    Var(X_i) = 1/12，Var(f) = 3/12 = 1/4，S_i = (1/12)/(1/4) = 1/3。
    """
    def func(params: np.ndarray) -> float:
        return float(np.sum(params))

    result = sobol_sensitivity_analysis(
        func=func,
        param_distributions=[
            {"type": "uniform", "loc": 0.0, "scale": 1.0},
            {"type": "uniform", "loc": 0.0, "scale": 1.0},
            {"type": "uniform", "loc": 0.0, "scale": 1.0},
        ],
        n_samples=256,
        param_names=["x", "y", "z"],
        random_state=42,
    )
    assert isinstance(result, SobolSensitivityResult)
    assert result.param_names == ["x", "y", "z"]
    assert result.n_samples == 256
    # 等贡献 → 一阶 Sobol ≈ 1/3
    for s in result.first_order.values():
        assert abs(s - 1.0 / 3.0) < 0.15, f"S_i 期望≈0.333，实际 {s}"
    # 线性可加 → 总效应 ≈ 一阶（无交互）
    for name in result.param_names:
        assert abs(result.total_order[name] - result.first_order[name]) < 0.2


def test_sobol_sensitivity_analysis_ranking():
    """Sobol 灵敏度排序: 大贡献参数排第一。"""
    def func(params: np.ndarray) -> float:
        return float(10.0 * params[0] + 1.0 * params[1])

    result = sobol_sensitivity_analysis(
        func=func,
        param_distributions=[
            {"type": "uniform", "loc": 0.0, "scale": 1.0},
            {"type": "uniform", "loc": 0.0, "scale": 1.0},
        ],
        n_samples=512,
        param_names=["big", "small"],
        random_state=42,
    )
    ranking = result.rank_by_first_order()
    assert ranking[0][0] == "big", f"期望 big 排第一，实际 {ranking}"
    assert ranking[-1][0] == "small"
    # 交互效应属性可访问
    interactions = result.interaction_effects
    assert set(interactions.keys()) == {"big", "small"}


def test_sobol_sensitivity_analysis_invalid_n_samples():
    """R03: n_samples 非 2 的幂 raise ValueError。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    with pytest.raises(ValueError, match="2 的幂"):
        sobol_sensitivity_analysis(
            func=func,
            param_distributions=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_samples=100,  # 非 2 幂
        )


def test_sobol_sensitivity_analysis_empty_distributions():
    """R03: 空分布列表 raise ValueError。"""
    def func(params: np.ndarray) -> float:
        return 0.0

    with pytest.raises(ValueError, match="param_distributions"):
        sobol_sensitivity_analysis(
            func=func,
            param_distributions=[],
            n_samples=128,
        )


# ============================================================================
# QMC 采样
# ============================================================================


def test_qmc_sampler_type_enum_values():
    """QMCSamplerType 枚举三值覆盖。"""
    assert QMCSamplerType.LATIN_HYPERCUBE.value == "latin_hypercube"
    assert QMCSamplerType.SOBOL.value == "sobol"
    assert QMCSamplerType.HALTON.value == "halton"


def test_generate_qmc_samples_sobol():
    """Sobol 采样: 样本形状与星偏差 ≥ 0。"""
    result = generate_qmc_samples(
        n_samples=64, n_dimensions=3,
        sampler_type=QMCSamplerType.SOBOL, seed=42,
    )
    assert isinstance(result, QMCSampleResult)
    assert result.samples.shape == (64, 3)
    assert result.n_samples == 64
    assert result.n_dimensions == 3
    assert result.sampler_type == QMCSamplerType.SOBOL
    assert result.discrepancy >= 0.0
    # 样本在 [0, 1]
    assert np.all(result.samples >= 0.0)
    assert np.all(result.samples <= 1.0)


def test_generate_qmc_samples_latin_hypercube():
    """LHS 采样: 非整数 n_samples 允许。"""
    result = generate_qmc_samples(
        n_samples=50, n_dimensions=2,
        sampler_type=QMCSamplerType.LATIN_HYPERCUBE, seed=42,
    )
    assert result.samples.shape == (50, 2)
    assert result.sampler_type == QMCSamplerType.LATIN_HYPERCUBE


def test_generate_qmc_samples_halton():
    """Halton 采样: 样本在 [0, 1]。"""
    result = generate_qmc_samples(
        n_samples=30, n_dimensions=2,
        sampler_type=QMCSamplerType.HALTON, seed=42,
    )
    assert result.samples.shape == (30, 2)
    assert np.all(result.samples >= 0.0) and np.all(result.samples <= 1.0)


def test_generate_qmc_samples_sobol_non_power_of_two():
    """R03: Sobol 采样器要求 n_samples 为 2 的幂。"""
    with pytest.raises(ValueError, match="2 的幂"):
        generate_qmc_samples(
            n_samples=100, n_dimensions=2,
            sampler_type=QMCSamplerType.SOBOL,
        )


def test_generate_qmc_samples_invalid_n():
    """R03: n_samples/n_dimensions <= 0 raise。"""
    with pytest.raises(ValueError, match="n_samples"):
        generate_qmc_samples(n_samples=0, n_dimensions=2)
    with pytest.raises(ValueError, match="n_dimensions"):
        generate_qmc_samples(n_samples=64, n_dimensions=0)


def test_transform_to_distribution_norm():
    """逆变换采样: norm 分布，均值收敛到 loc。"""
    uniform_samples = np.random.default_rng(42).uniform(
        1e-10, 1 - 1e-10, size=(1000, 1)
    )
    result = transform_to_distribution(
        uniform_samples=uniform_samples,
        distributions=[{"type": "norm", "loc": 5.0, "scale": 2.0}],
    )
    assert result.shape == (1000, 1)
    # 逆变换样本均值 ≈ loc
    assert abs(np.mean(result) - 5.0) < 0.2


def test_transform_to_distribution_dim_mismatch():
    """R03: 分布规格长度与样本维度不匹配 raise。"""
    uniform_samples = np.zeros((10, 2))
    with pytest.raises(ValueError, match="不匹配"):
        transform_to_distribution(
            uniform_samples=uniform_samples,
            distributions=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        )


def test_transform_to_distribution_unsupported_type():
    """R03: 不支持的分布类型 raise。"""
    uniform_samples = np.full((10, 1), 0.5)
    with pytest.raises(ValueError, match="不支持的分布类型"):
        transform_to_distribution(
            uniform_samples=uniform_samples,
            distributions=[{"type": "exponential", "loc": 0.0}],
        )


def test_qmc_monte_carlo_sobol():
    """Sobol QMC 仿真: 均值收敛到真值。

    f(x) = x[0]，X ~ N(0, 1)，E[f] = 0。
    Sobol n=64（2^6），相对朴素 MC 方差更小。
    """
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = qmc_monte_carlo(
        func=func,
        n_samples=64,
        distributions=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        sampler_type=QMCSamplerType.SOBOL,
        seed=42,
    )
    assert isinstance(result, QMCMonteCarloResult)
    assert result.n_samples == 64
    assert result.n_evaluations == 64
    assert result.sampler_type == QMCSamplerType.SOBOL
    assert abs(result.mean) < 0.3, f"均值期望≈0，实际 {result.mean}"
    assert result.std >= 0.0
    assert result.discrepancy >= 0.0


def test_qmc_monte_carlo_empty_distributions():
    """R03: 空分布列表 raise。"""
    def func(params: np.ndarray) -> float:
        return 0.0

    with pytest.raises(ValueError, match="distributions"):
        qmc_monte_carlo(func=func, n_samples=64, distributions=[])


def test_compare_qmc_convergence():
    """QMC vs 朴素 MC 收敛对比: QMC 误差随样本数下降。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = compare_qmc_convergence(
        func=func,
        distributions=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        true_value=0.0,
        sample_sizes=[64, 128, 256],
        sampler_type=QMCSamplerType.SOBOL,
        seed=42,
    )
    assert isinstance(result, QMCConvergenceComparison)
    assert result.sample_sizes == [64, 128, 256]
    assert len(result.mc_errors) == 3
    assert len(result.qmc_errors) == 3
    assert result.sampler_type == QMCSamplerType.SOBOL
    # 误差非负
    assert all(e >= 0.0 for e in result.mc_errors)
    assert all(e >= 0.0 for e in result.qmc_errors)


# ============================================================================
# 分层采样
# ============================================================================


def test_allocation_strategy_enum_values():
    """AllocationStrategy 枚举三值覆盖。"""
    assert AllocationStrategy.EQUAL.value == "equal"
    assert AllocationStrategy.PROPORTIONAL.value == "proportional"
    assert AllocationStrategy.NEYMAN.value == "neyman"


def test_stratified_monte_carlo_proportional():
    """分层采样 PROPORTIONAL: 估计收敛到真值，等权重 = 1/H。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = stratified_monte_carlo(
        func=func,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        n_strata=4,
        n_samples=40,
        strategy=AllocationStrategy.PROPORTIONAL,
        seed=42,
    )
    assert isinstance(result, StratifiedSamplingResult)
    assert result.n_strata == 4
    assert result.allocation_strategy == "proportional"
    assert len(result.n_per_stratum) == 4
    assert sum(result.n_per_stratum) == result.n_evaluations
    assert len(result.strata_means) == 4
    assert len(result.strata_weights) == 4
    # 等概率分层，权重 = 1/H = 0.25
    assert all(abs(w - 0.25) < 1e-9 for w in result.strata_weights)
    assert abs(result.estimate) < 0.5, f"估计期望≈0，实际 {result.estimate}"
    assert result.std_error >= 0.0


def test_stratified_monte_carlo_equal():
    """分层采样 EQUAL: 每层样本数 = n/H。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = stratified_monte_carlo(
        func=func,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        n_strata=5,
        n_samples=50,
        strategy=AllocationStrategy.EQUAL,
        seed=42,
    )
    assert result.allocation_strategy == "equal"
    assert all(n == 10 for n in result.n_per_stratum)


def test_compare_stratified_convergence():
    """分层采样 vs 朴素 MC 收敛对比: 误差非负。"""
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = compare_stratified_convergence(
        func=func,
        nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
        true_value=0.0,
        sample_sizes=[40, 80],
        n_strata=4,
        strategy=AllocationStrategy.PROPORTIONAL,
        seed=42,
    )
    assert isinstance(result, dict)
    assert "sample_sizes" in result
    assert "mc_errors" in result
    assert "stratified_errors" in result
    assert len(result["mc_errors"]) == 2


# ============================================================================
# 重要性采样
# ============================================================================


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
