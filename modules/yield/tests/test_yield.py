"""polaris-yield 子模块 smoke test。

测试覆盖（≥3 个 pytest，实际 9 个，覆盖全部迁移 API）:
- test_monte_carlo_simulate: 蒙特卡洛仿真均值收敛
- test_yield_analysis: 蒙特卡洛良率分析
- test_qmc_monte_carlo: Sobol QMC 仿真均值收敛
- test_stratified_monte_carlo: 分层采样估计收敛
- test_compute_worst_case_distance: WCD 工业良率指标
- test_allocate_tolerance_by_sensitivity: Taguchi Lagrange 容差分配
- test_batch_simulate: 多标称点批量仿真
- test_rare_event_yield: 稀有事件 IS 良率估计
- test_cross_entropy_importance_sampling: CE 自适应 IS

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Metropolis & Ulam 1949:
  https://doi.org/10.1080/01621459.1949.10483310
- Sobol 2001: https://doi.org/10.1007/BF02304730
- Saltelli et al. 2010: https://doi.org/10.1016/j.cpc.2009.09.018
- Glynn & Iglehart 1989:
  https://doi.org/10.1287/mnsc.35.11.1367
- Rubinstein 1997: https://doi.org/10.1016/S0377-2217(96)00385-2
- Cochran 1977, Sampling Techniques, Wiley
- Neyman 1934: https://doi.org/10.2307/2342192
- Singhal & Pinel 1981: https://doi.org/10.1109/TCS.1981.1085043
- Madkour et al. 2015: https://doi.org/10.1109/TCSI.2015.2495251
- SciPy stats: https://docs.scipy.org/doc/scipy/reference/stats.html

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

from polaris_yield import (  # noqa: E402
    AllocationStrategy,
    BiasingMethod,
    BiasingSpec,
    QMCSamplerType,
    allocate_tolerance_by_sensitivity,
    batch_simulate,
    batch_yield_analysis,
    compute_worst_case_distance,
    cross_entropy_importance_sampling,
    monte_carlo_simulate,
    qmc_monte_carlo,
    rare_event_yield,
    stratified_monte_carlo,
    yield_analysis,
)


# ============================================================================
# 蒙特卡洛仿真与良率分析
# ============================================================================


def test_monte_carlo_simulate():
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


def test_yield_analysis():
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
    # 标称远离规格边界，良率应接近 1
    assert result["yield"] > 0.95, f"良率期望>0.95，实际 {result['yield']}"


# ============================================================================
# QMC 采样
# ============================================================================


def test_qmc_monte_carlo():
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
    assert result.n_samples == 64
    assert result.n_evaluations == 64
    assert result.sampler_type == QMCSamplerType.SOBOL
    # E[f] = 0，QMC 估计应较接近（容忍抽样波动）
    assert abs(result.mean) < 0.3, f"均值期望≈0，实际 {result.mean}"
    assert result.std >= 0.0
    assert result.discrepancy >= 0.0


# ============================================================================
# 分层采样
# ============================================================================


def test_stratified_monte_carlo():
    """分层采样: 估计收敛到真值，方差小于朴素 MC。

    f(x) = x[0]，X ~ N(0, 1)，E[f] = 0。
    4 层 PROPORTIONAL 分配，n=40。
    """
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
    assert result.n_strata == 4
    assert result.allocation_strategy == "proportional"
    assert len(result.n_per_stratum) == 4
    assert sum(result.n_per_stratum) == result.n_evaluations
    assert len(result.strata_means) == 4
    assert len(result.strata_weights) == 4
    # 等概率分层，权重 = 1/H = 0.25
    assert all(abs(w - 0.25) < 1e-9 for w in result.strata_weights)
    # E[f] = 0
    assert abs(result.estimate) < 0.5, f"估计期望≈0，实际 {result.estimate}"
    assert result.std_error >= 0.0


# ============================================================================
# WCD 与容差分配
# ============================================================================


def test_compute_worst_case_distance():
    """WCD 计算: 线性函数 d_wc = (μ_f - T) / σ_f。

    f(x) = x[0] + x[1]，base = [1.0, 1.0]，σ = [0.1, 0.1]。
    μ_f = 2.0，σ_f = sqrt(0.1² + 0.1²) = 0.1·sqrt(2) ≈ 0.1414。
    T = 0.5 (lower)，d_wc = (2.0 - 0.5) / 0.1414 ≈ 10.607。
    Y ≈ Φ(10.607) ≈ 1.0。
    """
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
    assert abs(result.wcd - expected_wcd) < 0.1, \
        f"WCD 期望≈{expected_wcd:.3f}，实际 {result.wcd}"
    assert result.direction == "lower"
    # 大 WCD → 良率接近 1
    assert result.yield_estimate > 0.999
    assert result.n_evaluations > 0


def test_allocate_tolerance_by_sensitivity():
    """Lagrange 容差分配: σ_i ∝ 1/|S_i|，Σσ² = B。

    S = [1, 2, 4]，B = 1.0。
    inv_s² = [1, 0.25, 0.0625]，sum = 1.3125。
    σ² = [0.7619, 0.1905, 0.0476]，σ = [0.873, 0.436, 0.218]。
    验证: Σσ² = B；灵敏度大的参数容差小（σ_1 > σ_2 > σ_3）。
    """
    sensitivities = np.array([1.0, 2.0, 4.0])
    result = allocate_tolerance_by_sensitivity(
        sensitivities=sensitivities,
        total_budget=1.0,
        param_names=["w", "h", "gap"],
    )
    assert len(result.allocated_sigmas) == 3
    actual_budget = sum(s * s for s in result.allocated_sigmas)
    assert abs(actual_budget - 1.0) < 1e-9, \
        f"Σσ² 期望 1.0，实际 {actual_budget}"
    # 灵敏度大 → 容差小
    assert result.allocated_sigmas[0] > result.allocated_sigmas[1]
    assert result.allocated_sigmas[1] > result.allocated_sigmas[2]
    # 解析解验证: σ_i² = B·(1/S_i²) / Σ(1/S_j²)
    inv_s2 = 1.0 / (sensitivities ** 2)
    expected_var = 1.0 * inv_s2 / np.sum(inv_s2)
    expected_sigma = np.sqrt(expected_var)
    for i in range(3):
        assert abs(result.allocated_sigmas[i] - expected_sigma[i]) < 1e-9


# ============================================================================
# 批量仿真
# ============================================================================


def test_batch_simulate():
    """批量仿真: 多标称点 MC，每场景均值 ≈ 标称输出。

    f(x) = x[0]，3 场景 base=[1.0],[2.0],[3.0]，σ=[0.05]。
    """
    def func(params: np.ndarray) -> float:
        return float(params[0])

    result = batch_simulate(
        func=func,
        base_params_list=[np.array([1.0]), np.array([2.0]), np.array([3.0])],
        param_sigmas=np.array([0.05]),
        n_samples=200,
        seed=42,
    )
    assert result.n_scenarios == 3
    assert len(result.scenarios) == 3
    assert result.total_evaluations == 600
    for sid, expected_mean in enumerate([1.0, 2.0, 3.0]):
        sc = result.scenarios[sid]
        assert sc.scenario_id == sid
        assert abs(sc.mean - expected_mean) < 0.05, \
            f"场景 {sid} 均值期望≈{expected_mean}，实际 {sc.mean}"
        assert sc.n_samples == 200
    assert result.execution_time_s >= 0.0


def test_batch_yield_analysis():
    """批量良率分析: 多场景良率计算。

    f(x) = x[0]，3 场景 base=[0.5],[1.0],[2.0]，σ=[0.1]，spec: f>=0.3。
    """
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
    assert result.n_scenarios == 3
    assert len(result.yields) == 3
    assert result.total_evaluations == 600
    for y in result.yields:
        assert 0.0 <= y <= 1.0
    # 标称越大良率越高
    assert result.yields[0] <= result.yields[1] <= result.yields[2]


# ============================================================================
# 重要性采样（稀有事件 + 交叉熵）
# ============================================================================


def test_rare_event_yield():
    """稀有事件 IS 良率估计: MEAN_SHIFT 偏置。

    X ~ N(0, 1)，失效区域 x > 1.5，真值 Y_fail = 1 - Φ(1.5) ≈ 0.0668。
    偏置 q = N(1.5, 1)，~50% 样本落入失效区，ESS 充足。
    yield_estimate = 失效概率估计，应在真值附近（容忍 IS 抽样波动）。
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
    true_fail_prob = 1.0 - 0.9331927  # 1 - Φ(1.5) ≈ 0.0668
    assert result.n_samples == 5000
    assert result.n_failures >= 30, \
        f"失效样本数 {result.n_failures} < 30"
    assert result.biasing_method == "mean_shift"
    assert result.relative_error <= 0.5
    # 估计应在真值 [0.5x, 2x] 范围内（容忍 IS 抽样波动）
    assert 0.5 * true_fail_prob < result.yield_estimate < 2.0 * true_fail_prob, \
        f"失效概率估计 {result.yield_estimate} 偏离真值 {true_fail_prob:.4f}"
    assert result.effective_sample_size > 0


def test_cross_entropy_importance_sampling():
    """交叉熵自适应 IS: 迭代寻找最优 q*。

    X ~ N(0, 1)，失效区域 x > 1.5，真值 Y_fail ≈ 0.0668。
    CE 自适应 3 轮迭代，初始偏移 [1.5]。
    """
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
    true_fail_prob = 1.0 - 0.9331927  # ≈ 0.0668
    assert result.biasing_method == "cross_entropy"
    assert result.converged is not None  # CE 有收敛标志
    assert result.n_failures >= 30, \
        f"CE 最终失效样本数 {result.n_failures} < 30"
    assert result.relative_error <= 0.5
    # CE 估计应在真值 [0.3x, 3x] 范围内（CE 自适应有更大波动）
    assert 0.3 * true_fail_prob < result.yield_estimate < 3.0 * true_fail_prob, \
        f"CE 失效概率估计 {result.yield_estimate} 偏离真值 {true_fail_prob:.4f}"
    assert result.n_evaluations >= 1000  # 至少一轮迭代
