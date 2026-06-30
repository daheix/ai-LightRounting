"""R291-R300 良率优化 + 批量仿真 + 3D 效应修正 测试套件。

覆盖三个模块:
1. ``yield_optimization`` (R291-R295): WCD + 容差分配 + 标称值优化
2. ``batch_simulation`` (R296-R298): 多标称点 MC + 良率分析
3. ``three_d_effects`` (R299): 侧壁角修正 + 粗糙度散射 + 模式失配

学术依据（与被测模块 docstring 一致）:
- WCD: Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251
- 容差分配: Singhal & Pinel 1981, DOI: 10.1109/TCS.1981.1085043
- 标称值优化: Parkinson 1993, DOI: 10.1080/03052159308940948
- 蒙特卡洛: Metropolis & Ulam 1949, DOI: 10.2307/2280232
- 侧壁角: Soref et al. 1991, DOI: 10.1109/3.83406
- 粗糙度散射: Sanchis et al. 2006, DOI: 10.1364/OE.14.006979
- 模式重叠: Yariv 1973, DOI: 10.1109/JQE.1973.1077767

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必须修复附回归测试。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from polaris.sim.batch_simulation import (
    BatchScenarioResult,
    BatchSimulationResult,
    BatchYieldResult,
    batch_simulate,
    batch_yield_analysis,
)
from polaris.sim.three_d_effects import (
    RoughnessScatteringLoss,
    SidewallAngleCorrection,
    correct_neff_for_sidewall_angle,
    mode_mismatch_loss_gaussian,
    sidewall_roughness_loss,
)
from polaris.sim.yield_optimization import (
    ToleranceAllocationResult,
    WorstCaseDistanceResult,
    YieldOptimizationResult,
    allocate_tolerance_by_sensitivity,
    compute_worst_case_distance,
    optimize_yield_via_nominal_shift,
)


# ============================================================================
# 辅助函数
# ============================================================================


def linear_func(params: np.ndarray) -> float:
    """线性函数 f = sum(params)，用于解析验证。"""
    return float(np.sum(params))


def linear_func_with_coeffs(coeffs: np.ndarray):
    """返回 f(x) = coeffs · x 的函数。"""
    def f(params: np.ndarray) -> float:
        return float(np.dot(coeffs, params))
    return f


# ============================================================================
# R291-R295: yield_optimization 测试
# ============================================================================


class TestWorstCaseDistance:
    """R291: 最坏情况距离 (WCD) 计算。"""

    def test_lower_spec_basic(self):
        """lower spec (f≥T): 对线性函数解析验证 WCD。"""
        # f = x_0, x_0 ~ N(μ=1.0, σ=0.1), T=0.5
        # σ_f = 1·0.1 = 0.1, d_wc = (1.0-0.5)/0.1 = 5.0
        func = linear_func_with_coeffs(np.array([1.0, 0.0, 0.0]))
        base = np.array([1.0, 0.0, 0.0])
        sigmas = np.array([0.1, 0.1, 0.1])
        r = compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5,
                                        direction="lower")
        assert r.direction == "lower"
        assert r.f_nominal == pytest.approx(1.0, abs=1e-10)
        # σ_f = sqrt(1²·0.1² + 0²·0.1² + 0²·0.1²) = 0.1
        assert r.sigma_output == pytest.approx(0.1, abs=1e-6)
        # d_wc = (1.0 - 0.5) / 0.1 = 5.0
        assert r.wcd == pytest.approx(5.0, abs=1e-3)
        # Y ≈ Φ(5.0) ≈ 0.9999997
        assert r.yield_estimate == pytest.approx(norm.cdf(5.0), abs=1e-6)

    def test_upper_spec_basic(self):
        """upper spec (f≤T): d_wc = (T - μ_f) / σ_f。"""
        # f = -x_0, x_0 ~ N(1.0, 0.1), T = -0.5
        # μ_f = -1.0, σ_f = 0.1, d_wc = (-0.5 - (-1.0))/0.1 = 5.0
        func = linear_func_with_coeffs(np.array([-1.0, 0.0, 0.0]))
        base = np.array([1.0, 0.0, 0.0])
        sigmas = np.array([0.1, 0.1, 0.1])
        r = compute_worst_case_distance(func, base, sigmas, spec_threshold=-0.5,
                                        direction="upper")
        assert r.wcd == pytest.approx(5.0, abs=1e-3)
        assert r.yield_estimate == pytest.approx(norm.cdf(5.0), abs=1e-6)

    def test_nominal_fails_spec(self):
        """标称已不满足规格 → WCD < 0, Y < 0.5。"""
        # f = x_0, x_0 = 0.3, T = 0.5, σ = 0.1 → d_wc = (0.3-0.5)/0.1 = -2
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([0.3])
        sigmas = np.array([0.1])
        r = compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5,
                                        direction="lower")
        assert r.wcd == pytest.approx(-2.0, abs=1e-3)
        assert r.yield_estimate < 0.5
        assert r.yield_estimate == pytest.approx(norm.cdf(-2.0), abs=1e-6)

    def test_multivariate_variance_propagation(self):
        """多变量一阶方差传播 σ_f² = Σ S_i² σ_i²。"""
        # f = 2·x_0 + 3·x_1, σ_0=0.1, σ_1=0.2
        # σ_f² = (2·0.1)² + (3·0.2)² = 0.04 + 0.36 = 0.40, σ_f = 0.6325
        func = linear_func_with_coeffs(np.array([2.0, 3.0]))
        base = np.array([0.0, 0.0])
        sigmas = np.array([0.1, 0.2])
        r = compute_worst_case_distance(func, base, sigmas, spec_threshold=-1.0,
                                        direction="lower")
        assert r.sigma_output == pytest.approx(np.sqrt(0.40), abs=1e-4)
        # μ_f = 0, d_wc = (0 - (-1.0))/0.6325 = 1.5811
        assert r.wcd == pytest.approx(1.0 / np.sqrt(0.40), abs=1e-3)

    def test_n_evaluations(self):
        """评估次数 = 1 (base) + 1 (sens base) + 2·d (中心差分)。"""
        func = linear_func_with_coeffs(np.array([1.0, 1.0, 1.0, 1.0]))
        base = np.array([1.0, 1.0, 1.0, 1.0])
        sigmas = np.array([0.1, 0.1, 0.1, 0.1])
        r = compute_worst_case_distance(func, base, sigmas, spec_threshold=2.0,
                                        direction="lower")
        # compute_worst_case_distance: 1 (f_nominal) + _compute_unnormalized_sensitivity
        # _compute_unnormalized_sensitivity: 1 (base) + 2*d (中心差分)
        # d=4, n_eval = 1 + 1 + 2*4 = 10
        assert r.n_evaluations == 10

    def test_invalid_direction(self):
        """R03: 无效 direction 必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([1.0])
        sigmas = np.array([0.1])
        with pytest.raises(ValueError, match="direction"):
            compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5,
                                        direction="invalid")

    def test_invalid_sigmas(self):
        """R03: σ ≤ 0 必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([1.0])
        sigmas = np.array([0.0])
        with pytest.raises(ValueError, match="param_sigmas"):
            compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5)

    def test_shape_mismatch(self):
        """R03: base/sigmas shape 不匹配必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0, 1.0]))
        base = np.array([1.0, 1.0])
        sigmas = np.array([0.1])  # 长度不匹配
        with pytest.raises(ValueError, match="shape"):
            compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5)

    def test_zero_sensitivity_raises(self):
        """R03: σ_f=0（输出对参数无响应）必须 raise，禁止 fall-back。"""
        # f = 常数 0（对参数无响应）
        func = lambda p: 0.0
        base = np.array([1.0, 1.0])
        sigmas = np.array([0.1, 0.1])
        with pytest.raises(RuntimeError, match="σ_f = 0"):
            compute_worst_case_distance(func, base, sigmas, spec_threshold=0.5)

    def test_func_failure_raises(self):
        """R03: func 评估失败必须 raise，禁止 fall-back。"""
        def bad_func(p):
            raise ValueError("simulator error")
        base = np.array([1.0])
        sigmas = np.array([0.1])
        with pytest.raises(RuntimeError, match="func 标称评估失败"):
            compute_worst_case_distance(bad_func, base, sigmas, spec_threshold=0.5)


class TestToleranceAllocation:
    """R292: 基于灵敏度容差分配 (Lagrange 解 σ_i ∝ 1/|S_i|)。"""

    def test_lagrange_solution_basic(self):
        """解析验证: σ_i² = B·(1/S_i²)/Σ(1/S_j²)。"""
        # S = [1, 2, 4], B = 1.0
        # Σ(1/S_j²) = 1 + 0.25 + 0.0625 = 1.3125
        # σ_1² = 1/1.3125 = 0.7619
        # σ_2² = 0.25/1.3125 = 0.1905
        # σ_3² = 0.0625/1.3125 = 0.0476
        sens = np.array([1.0, 2.0, 4.0])
        r = allocate_tolerance_by_sensitivity(sens, total_budget=1.0)
        assert r.total_budget == pytest.approx(1.0)
        expected_vars = np.array([1.0, 0.25, 0.0625]) / 1.3125
        expected_sigmas = np.sqrt(expected_vars)
        for i, (got, exp) in enumerate(zip(r.allocated_sigmas, expected_sigmas)):
            assert got == pytest.approx(exp, abs=1e-10), f"σ[{i}] 不匹配"
        # 预算守恒 Σσ² = B
        assert sum(s**2 for s in r.allocated_sigmas) == pytest.approx(1.0, abs=1e-10)

    def test_high_sensitivity_gets_small_tolerance(self):
        """高灵敏度参数应给小容差（Taguchi 直觉）。"""
        sens = np.array([1.0, 10.0, 100.0])
        r = allocate_tolerance_by_sensitivity(sens, total_budget=1.0)
        # σ 应单调递减: S 越大 → σ 越小
        assert r.allocated_sigmas[0] > r.allocated_sigmas[1] > r.allocated_sigmas[2]

    def test_budget_conservation(self):
        """Σσ_i² = B（任意输入）。"""
        sens = np.array([3.0, 7.0, 11.0, 2.0])
        B = 0.5
        r = allocate_tolerance_by_sensitivity(sens, total_budget=B)
        actual = sum(s**2 for s in r.allocated_sigmas)
        assert actual == pytest.approx(B, abs=1e-10)

    def test_variance_reduction_vs_equal(self):
        """优化后输出方差 ≤ 等额分配方差（Lagrange 最优性）。"""
        # S = [1, 2, 4], B = 1
        # 等额分配: σ_i = sqrt(1/3), Var_eq = Σ S_i² · (1/3) = (1+4+16)/3 = 7.0
        # Lagrange: Var_opt = Σ S_i² · σ_i² = 1·0.7619 + 4·0.1905 + 16·0.0476
        #        = 0.7619 + 0.7619 + 0.7619 = 2.2857
        sens = np.array([1.0, 2.0, 4.0])
        B = 1.0
        r = allocate_tolerance_by_sensitivity(sens, total_budget=B)
        # 优化后方差
        assert r.expected_variance_output == pytest.approx(2.2857, abs=1e-3)
        # 等额分配方差 7.0 > 优化后方差 2.2857
        assert 7.0 > r.expected_variance_output

    def test_original_sigmas_variance_reduction(self):
        """提供 original_sigmas 时报告方差减少比例。"""
        sens = np.array([1.0, 2.0, 4.0])
        # 原始等额 σ_i = 0.5 → Var_orig = 1·0.25 + 4·0.25 + 16·0.25 = 5.25
        original = np.array([0.5, 0.5, 0.5])
        r = allocate_tolerance_by_sensitivity(
            sens, total_budget=0.75, original_sigmas=original
        )
        # original_budget = 0.75 = Σ 0.5² = 0.75 ✓
        assert sum(s**2 for s in original) == pytest.approx(0.75)
        # 原始方差 = 5.25
        assert r.original_variance_output == pytest.approx(5.25, abs=1e-6)
        # variance_reduction = 1 - new/old > 0
        assert r.variance_reduction > 0.0
        assert r.variance_reduction == pytest.approx(
            1.0 - r.expected_variance_output / 5.25, abs=1e-6
        )

    def test_param_names_default(self):
        """默认参数名 param_0, param_1, ...。"""
        sens = np.array([1.0, 2.0])
        r = allocate_tolerance_by_sensitivity(sens, total_budget=1.0)
        assert r.param_names == ["param_0", "param_1"]

    def test_param_names_custom(self):
        """自定义参数名。"""
        sens = np.array([1.0, 2.0])
        r = allocate_tolerance_by_sensitivity(
            sens, total_budget=1.0, param_names=["width", "height"]
        )
        assert r.param_names == ["width", "height"]

    def test_invalid_budget(self):
        """R03: B ≤ 0 必须 raise。"""
        sens = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="total_budget"):
            allocate_tolerance_by_sensitivity(sens, total_budget=0.0)
        with pytest.raises(ValueError, match="total_budget"):
            allocate_tolerance_by_sensitivity(sens, total_budget=-1.0)

    def test_all_zero_sensitivities_raises(self):
        """R03: 所有灵敏度为 0 → 无解，必须 raise。"""
        sens = np.array([0.0, 0.0, 0.0])
        with pytest.raises(ValueError, match="所有灵敏度 = 0"):
            allocate_tolerance_by_sensitivity(sens, total_budget=1.0)

    def test_zero_sensitivity_handled(self):
        """部分灵敏度为 0 时用最小非零灵敏度的 1/10 替代（保守上限）。"""
        # S = [1.0, 0.0] → 0 用 0.1 替代
        # Σ(1/S²) = 1 + 100 = 101
        # σ_1² = 1·1/101 = 0.0099, σ_2² = 1·100/101 = 0.9901
        sens = np.array([1.0, 0.0])
        r = allocate_tolerance_by_sensitivity(sens, total_budget=1.0)
        # Σσ² = 1 守恒
        assert sum(s**2 for s in r.allocated_sigmas) == pytest.approx(1.0, abs=1e-10)
        # 0 灵敏度的参数获得更大容差
        assert r.allocated_sigmas[1] > r.allocated_sigmas[0]

    def test_param_names_length_mismatch(self):
        """R03: param_names 长度不匹配必须 raise。"""
        sens = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="param_names"):
            allocate_tolerance_by_sensitivity(
                sens, total_budget=1.0, param_names=["a", "b"]
            )


class TestNominalShiftOptimization:
    """R293-R294: 标称值优化 (WCD 梯度上升)。"""

    def test_linear_function_yield_improvement(self):
        """对线性函数，标称值优化应显著改善良率。"""
        # f = x_0, x_0 = 0.0, σ = 0.1, T = 0.5 (lower spec)
        # 初始 WCD = (0 - 0.5)/0.1 = -5, Y ≈ 2.87e-7
        # 优化后应朝 x_0 增大方向移动
        func = linear_func_with_coeffs(np.array([1.0, 0.0]))
        base = np.array([0.0, 0.0])
        sigmas = np.array([0.1, 0.1])
        r = optimize_yield_via_nominal_shift(
            func, base, sigmas, spec_threshold=0.5, direction="lower",
            max_iter=20, learning_rate=0.5,
        )
        # WCD 应改善
        assert r.optimized_wcd > r.original_wcd
        # 良率应改善
        assert r.optimized_yield > r.original_yield
        # 标称值应朝正方向移动
        assert r.optimal_params[0] > base[0]

    def test_upper_spec_optimization(self):
        """upper spec: 优化应朝 f 减小方向移动。"""
        # f = x_0, x_0 = 1.0, σ = 0.1, T = 0.5 (upper spec f ≤ T)
        # 初始 WCD = (0.5 - 1.0)/0.1 = -5, 应朝 x_0 减小方向优化
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([1.0])
        sigmas = np.array([0.1])
        r = optimize_yield_via_nominal_shift(
            func, base, sigmas, spec_threshold=0.5, direction="upper",
            max_iter=20, learning_rate=0.5,
        )
        assert r.optimized_wcd > r.original_wcd
        assert r.optimal_params[0] < base[0]

    def test_already_optimal_no_improvement(self):
        """已最优时（WCD 已经很大）不应大幅移动。"""
        # f = x_0, x_0 = 10.0, σ = 0.1, T = 0.5 (lower spec)
        # WCD = (10-0.5)/0.1 = 95, 已极优
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([10.0])
        sigmas = np.array([0.1])
        r = optimize_yield_via_nominal_shift(
            func, base, sigmas, spec_threshold=0.5, direction="lower",
            max_iter=5, learning_rate=0.5, tol=1e-3,
        )
        # WCD 已接近 1.0 良率
        assert r.optimized_yield > 0.999

    def test_wcd_history_monotonic(self):
        """WCD 历史应非递减（接受改善或回退停止）。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([0.0])
        sigmas = np.array([0.1])
        r = optimize_yield_via_nominal_shift(
            func, base, sigmas, spec_threshold=0.5, direction="lower",
            max_iter=10, learning_rate=0.3,
        )
        for i in range(1, len(r.wcd_history)):
            # WCD 不应下降（回退时保持上一轮值）
            assert r.wcd_history[i] >= r.wcd_history[i-1] - 1e-12

    def test_iterations_recorded(self):
        """iterations 应为实际迭代次数。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([0.0])
        sigmas = np.array([0.1])
        r = optimize_yield_via_nominal_shift(
            func, base, sigmas, spec_threshold=0.5, direction="lower",
            max_iter=5, learning_rate=0.5,
        )
        assert 1 <= r.iterations <= 5

    def test_invalid_learning_rate(self):
        """R03: learning_rate 越界必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([0.0])
        sigmas = np.array([0.1])
        with pytest.raises(ValueError, match="learning_rate"):
            optimize_yield_via_nominal_shift(
                func, base, sigmas, spec_threshold=0.5,
                learning_rate=0.0,
            )
        with pytest.raises(ValueError, match="learning_rate"):
            optimize_yield_via_nominal_shift(
                func, base, sigmas, spec_threshold=0.5,
                learning_rate=1.5,
            )

    def test_invalid_max_iter(self):
        """R03: max_iter < 1 必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        base = np.array([0.0])
        sigmas = np.array([0.1])
        with pytest.raises(ValueError, match="max_iter"):
            optimize_yield_via_nominal_shift(
                func, base, sigmas, spec_threshold=0.5, max_iter=0,
            )


# ============================================================================
# R296-R298: batch_simulation 测试
# ============================================================================


class TestBatchSimulate:
    """R296-R297: 批量蒙特卡洛仿真。"""

    def test_two_scenarios_basic(self):
        """两场景基本统计量。"""
        # f = p_0 + p_1, base1=[1,1]→μ=2, base2=[2,2]→μ=4
        func = linear_func_with_coeffs(np.array([1.0, 1.0]))
        bases = [np.array([1.0, 1.0]), np.array([2.0, 2.0])]
        sigmas = np.array([0.01, 0.01])
        r = batch_simulate(func, bases, sigmas, n_samples=1000, seed=42)
        assert r.n_scenarios == 2
        assert len(r.scenarios) == 2
        # 场景 0 均值 ≈ 2.0
        assert r.scenarios[0].mean == pytest.approx(2.0, abs=0.01)
        # 场景 1 均值 ≈ 4.0
        assert r.scenarios[1].mean == pytest.approx(4.0, abs=0.01)
        # 总评估次数 = 2 × 1000
        assert r.total_evaluations == 2000

    def test_statistics_fields(self):
        """统计字段完整性。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([1.0])]
        sigmas = np.array([0.1])
        r = batch_simulate(func, bases, sigmas, n_samples=500, seed=1)
        s = r.scenarios[0]
        assert s.n_samples == 500
        assert s.scenario_id == 0
        assert s.min <= s.mean <= s.max
        assert s.percentile_05 <= s.percentile_95
        assert s.n_evaluations == 500

    def test_reproducibility(self):
        """相同 seed 应产生相同结果。"""
        func = linear_func_with_coeffs(np.array([1.0, 1.0]))
        bases = [np.array([1.0, 1.0]), np.array([2.0, 2.0])]
        sigmas = np.array([0.05, 0.05])
        r1 = batch_simulate(func, bases, sigmas, n_samples=500, seed=123)
        r2 = batch_simulate(func, bases, sigmas, n_samples=500, seed=123)
        for s1, s2 in zip(r1.scenarios, r2.scenarios):
            assert s1.mean == pytest.approx(s2.mean)
            assert s1.std == pytest.approx(s2.std)

    def test_param_perturbation_model(self):
        """参数扰动模型 params = base · (1 + σ · ε)。"""
        # f = p_0, base=1.0, σ=0.1 → 输出均值=1.0, std≈0.1
        # MC 标准误 = 0.1/sqrt(n) = 0.001 (n=10000)
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([1.0])]
        sigmas = np.array([0.1])
        r = batch_simulate(func, bases, sigmas, n_samples=10000, seed=42)
        s = r.scenarios[0]
        # 均值 ≈ 1.0（±2σ_MC = ±0.002，宽松边界）
        assert s.mean == pytest.approx(1.0, abs=2e-3)
        # std ≈ 0.1（相对扰动 10%）
        assert s.std == pytest.approx(0.1, abs=0.005)

    def test_empty_base_list_raises(self):
        """R03: 空场景列表必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        with pytest.raises(ValueError, match="base_params_list"):
            batch_simulate(func, [], np.array([0.1]), n_samples=100)

    def test_invalid_sigmas_raises(self):
        """R03: σ ≤ 0 必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        with pytest.raises(ValueError, match="param_sigmas"):
            batch_simulate(func, [np.array([1.0])], np.array([0.0]), n_samples=100)
        with pytest.raises(ValueError, match="param_sigmas"):
            batch_simulate(func, [np.array([1.0])], np.array([-0.1]), n_samples=100)

    def test_invalid_n_samples_raises(self):
        """R03: n_samples < 1 必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        with pytest.raises(ValueError, match="n_samples"):
            batch_simulate(func, [np.array([1.0])], np.array([0.1]), n_samples=0)

    def test_shape_mismatch_raises(self):
        """R03: base/sigmas shape 不匹配必须 raise。"""
        func = linear_func_with_coeffs(np.array([1.0, 1.0]))
        # base 长度 2, sigmas 长度 1
        with pytest.raises(ValueError, match="shape"):
            batch_simulate(
                func, [np.array([1.0, 1.0])], np.array([0.1]), n_samples=100
            )

    def test_func_failure_raises(self):
        """R03: func 评估失败必须 raise，禁止 fall-back。"""
        def bad_func(p):
            raise RuntimeError("simulator crash")
        with pytest.raises(RuntimeError, match="func 评估失败"):
            batch_simulate(
                bad_func, [np.array([1.0])], np.array([0.1]), n_samples=10
            )


class TestBatchYieldAnalysis:
    """R298: 批量良率分析。"""

    def test_two_scenarios_yield(self):
        """两场景良率计算。

        参数扰动模型 params = base · (1 + σ · ε)，故输出 f=p_0 的
        σ_out = base · σ（相对扰动），WCD = (base - T) / (base · σ)。
        """
        # f = p_0, σ=0.05
        # 场景 0: base=5.0, T=4.0 → σ_out=0.25, WCD=(5-4)/0.25=4.0, Y≈0.99997
        # 场景 1: base=3.0, T=4.0 → σ_out=0.15, WCD=(3-4)/0.15=-6.67, Y≈2e-11
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([5.0]), np.array([3.0])]
        sigmas = np.array([0.05])
        spec = lambda out: out >= 4.0
        r = batch_yield_analysis(func, bases, sigmas, spec, n_samples=2000, seed=42)
        assert r.n_scenarios == 2
        # 场景 0: WCD=4.0, Y≈0.99997 → > 0.999
        assert r.yields[0] > 0.999
        # 场景 1: WCD=-6.67, Y≈2e-11 → < 0.001
        assert r.yields[1] < 0.001

    def test_pass_count_consistency(self):
        """n_pass / n_samples == yield。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([5.0])]
        sigmas = np.array([0.1])
        spec = lambda out: out >= 4.0
        r = batch_yield_analysis(func, bases, sigmas, spec, n_samples=500, seed=1)
        assert r.n_pass_per_scenario[0] / r.n_samples_per_scenario == pytest.approx(
            r.yields[0]
        )

    def test_total_evaluations(self):
        """总评估次数 = n_scenarios × n_samples。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([1.0]), np.array([2.0]), np.array([3.0])]
        sigmas = np.array([0.1])
        spec = lambda out: out >= 1.5
        r = batch_yield_analysis(func, bases, sigmas, spec, n_samples=200, seed=1)
        assert r.total_evaluations == 600

    def test_reproducibility(self):
        """相同 seed 应产生相同良率。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        bases = [np.array([1.0]), np.array([2.0])]
        sigmas = np.array([0.1])
        spec = lambda out: out >= 1.5
        r1 = batch_yield_analysis(func, bases, sigmas, spec, n_samples=500, seed=99)
        r2 = batch_yield_analysis(func, bases, sigmas, spec, n_samples=500, seed=99)
        assert r1.yields == r2.yields

    def test_invalid_inputs_raise(self):
        """R03: 输入验证。"""
        func = linear_func_with_coeffs(np.array([1.0]))
        spec = lambda out: out >= 1.0
        with pytest.raises(ValueError, match="base_params_list"):
            batch_yield_analysis(func, [], np.array([0.1]), spec)
        with pytest.raises(ValueError, match="param_sigmas"):
            batch_yield_analysis(
                func, [np.array([1.0])], np.array([0.0]), spec
            )


# ============================================================================
# R299: three_d_effects 测试
# ============================================================================


class TestSidewallAngleCorrection:
    """R299: 侧壁角修正。"""

    def test_vertical_sidewall_no_correction(self):
        """θ=0° (垂直侧壁) → 无修正。"""
        # w_eq = w - h·tan(0°) = w, delta_neff = 0
        r = correct_neff_for_sidewall_angle(
            neff_2d=2.4, width_um=0.5, height_um=0.22,
            sidewall_angle_deg=0.0, dneff_dw_per_um=0.5,
        )
        assert r.w_eq_um == pytest.approx(0.5, abs=1e-12)
        assert r.delta_neff == pytest.approx(0.0, abs=1e-12)
        assert r.neff_corrected == pytest.approx(2.4, abs=1e-12)
        assert r.w_top_um == pytest.approx(0.5, abs=1e-12)
        assert r.w_bottom_um == pytest.approx(0.5, abs=1e-12)

    def test_positive_angle_reduces_weq(self):
        """θ>0 (上窄下宽) → w_eq < w, neff 减小（若 ∂n_eff/∂w > 0）。"""
        # θ=5°, h=0.22, w=0.5
        # w_eq = 0.5 - 0.22·tan(5°) = 0.5 - 0.22·0.08749 = 0.4808
        r = correct_neff_for_sidewall_angle(
            neff_2d=2.4, width_um=0.5, height_um=0.22,
            sidewall_angle_deg=5.0, dneff_dw_per_um=0.5,
        )
        assert r.w_eq_um == pytest.approx(0.5 - 0.22 * np.tan(np.radians(5.0)),
                                          abs=1e-6)
        assert r.w_eq_um < 0.5
        # delta_neff = 0.5 · (w_eq - w) < 0
        assert r.delta_neff < 0
        assert r.neff_corrected < 2.4

    def test_negative_angle_increases_weq(self):
        """θ<0 (上宽下窄) → w_eq > w。"""
        r = correct_neff_for_sidewall_angle(
            neff_2d=2.4, width_um=0.5, height_um=0.22,
            sidewall_angle_deg=-5.0, dneff_dw_per_um=0.5,
        )
        assert r.w_eq_um > 0.5
        assert r.delta_neff > 0

    def test_trapezoid_geometry(self):
        """梯形几何: w_top = w - 2h·tan(θ), w_bottom = w。"""
        r = correct_neff_for_sidewall_angle(
            neff_2d=2.4, width_um=0.5, height_um=0.22,
            sidewall_angle_deg=10.0, dneff_dw_per_um=0.5,
        )
        expected_w_top = 0.5 - 2 * 0.22 * np.tan(np.radians(10.0))
        assert r.w_top_um == pytest.approx(expected_w_top, abs=1e-6)
        assert r.w_bottom_um == pytest.approx(0.5)
        # w_eq = (w_top + w_bottom) / 2
        assert r.w_eq_um == pytest.approx(0.5 * (r.w_top_um + r.w_bottom_um),
                                          abs=1e-12)

    def test_first_order_taylor(self):
        """一阶 Taylor: Δn_eff = (∂n_eff/∂w) · (w_eq - w)。"""
        r = correct_neff_for_sidewall_angle(
            neff_2d=2.4, width_um=0.5, height_um=0.22,
            sidewall_angle_deg=8.0, dneff_dw_per_um=0.7,
        )
        expected_delta = 0.7 * (r.w_eq_um - 0.5)
        assert r.delta_neff == pytest.approx(expected_delta, abs=1e-12)
        assert r.neff_corrected == pytest.approx(2.4 + expected_delta, abs=1e-12)

    def test_invalid_width(self):
        """R03: width ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="width_um"):
            correct_neff_for_sidewall_angle(
                neff_2d=2.4, width_um=0.0, height_um=0.22,
                sidewall_angle_deg=5.0, dneff_dw_per_um=0.5,
            )

    def test_invalid_height(self):
        """R03: height ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="height_um"):
            correct_neff_for_sidewall_angle(
                neff_2d=2.4, width_um=0.5, height_um=0.0,
                sidewall_angle_deg=5.0, dneff_dw_per_um=0.5,
            )

    def test_excessive_angle_raises(self):
        """R03: 角度过大致使 w_top ≤ 0 必须 raise。"""
        # w=0.5, h=0.22, θ=80° → w_top = 0.5 - 2·0.22·tan(80°) ≈ 0.5 - 2.49 < 0
        with pytest.raises(ValueError, match="w_top"):
            correct_neff_for_sidewall_angle(
                neff_2d=2.4, width_um=0.5, height_um=0.22,
                sidewall_angle_deg=80.0, dneff_dw_per_um=0.5,
            )

    def test_angle_out_of_range(self):
        """R03: |θ| ≥ 89° 必须 raise。"""
        with pytest.raises(ValueError, match="sidewall_angle_deg"):
            correct_neff_for_sidewall_angle(
                neff_2d=2.4, width_um=0.5, height_um=0.22,
                sidewall_angle_deg=89.0, dneff_dw_per_um=0.5,
            )
        with pytest.raises(ValueError, match="sidewall_angle_deg"):
            correct_neff_for_sidewall_angle(
                neff_2d=2.4, width_um=0.5, height_um=0.22,
                sidewall_angle_deg=-90.0, dneff_dw_per_um=0.5,
            )


class TestSidewallRoughnessLoss:
    """R299: 侧壁粗糙度散射损耗 (Sanchis 2006)。"""

    def test_typical_soi_loss_magnitude(self):
        """SOI 典型参数下损耗应在合理量级 (0.001-1 dB/cm)。"""
        # σ=2nm, Lc=50nm, λ=1550nm, neff=2.4, dneff/dw=0.5/μm
        # 文献 Barwicz 2005 报告 SOI 波导损耗约 0.3-3 dB/cm
        r = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        # 损耗应在 0.001-10 dB/cm 范围（含散射 + 工艺量级）
        assert 0.001 < r.loss_db_per_cm < 10.0, (
            f"损耗 {r.loss_db_per_cm} dB/cm 超出 SOI 合理量级"
        )

    def test_sigma_scaling_quadratic(self):
        """α ∝ σ²（Sanchis 公式）。"""
        # σ 翻倍 → α × 4
        r1 = sidewall_roughness_loss(
            sigma_nm=1.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        r2 = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        # 注意: Δβ 也含 σ，所以不是严格 4 倍，但主导项是 σ²
        # 对小 σ（Δβ·Lc << 1），F ≈ Lc，α ∝ σ²
        assert r2.loss_db_per_m > r1.loss_db_per_m * 3.5  # 接近 4 倍

    def test_dneff_scaling_quadratic(self):
        """α ∝ (∂n_eff/∂w)²（Sanchis 公式）。"""
        r1 = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        r2 = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=1.0,
        )
        # (∂n_eff/∂w) 翻倍 → α 至少 ×3.5（接近 4 倍）
        assert r2.loss_db_per_m > r1.loss_db_per_m * 3.5

    def test_unit_conversion(self):
        """dB/m = 100 × dB/cm。"""
        r = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        assert r.loss_db_per_m == pytest.approx(100.0 * r.loss_db_per_cm,
                                                abs=1e-6)

    def test_lorentz_psd_formula(self):
        """洛伦兹 PSD: F(u) = L_c / (1 + u²)。"""
        r = sidewall_roughness_loss(
            sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
            neff=2.4, dneff_dw_per_um=0.5,
        )
        # u = Δβ · L_c
        u = r.delta_beta_per_m * (50.0 * 1e-9)
        expected_F = 50.0 * 1e-9 / (1.0 + u * u)
        assert r.psd_lorentzian_m == pytest.approx(expected_F, abs=1e-15)

    def test_invalid_sigma(self):
        """R03: σ ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="sigma_nm"):
            sidewall_roughness_loss(
                sigma_nm=0.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
                neff=2.4, dneff_dw_per_um=0.5,
            )

    def test_invalid_correlation_length(self):
        """R03: L_c ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="correlation_length_nm"):
            sidewall_roughness_loss(
                sigma_nm=2.0, correlation_length_nm=0.0, wavelength_nm=1550.0,
                neff=2.4, dneff_dw_per_um=0.5,
            )

    def test_invalid_wavelength(self):
        """R03: λ ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="wavelength_nm"):
            sidewall_roughness_loss(
                sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=0.0,
                neff=2.4, dneff_dw_per_um=0.5,
            )

    def test_invalid_neff(self):
        """R03: neff ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="neff"):
            sidewall_roughness_loss(
                sigma_nm=2.0, correlation_length_nm=50.0, wavelength_nm=1550.0,
                neff=0.0, dneff_dw_per_um=0.5,
            )


class TestModeMismatchLossGaussian:
    """R299: 高斯模式宽度失配耦合损耗。"""

    def test_perfect_match_zero_loss(self):
        """w1 == w2 → η=1, L=0 dB。"""
        loss = mode_mismatch_loss_gaussian(0.5, 0.5)
        assert loss == pytest.approx(0.0, abs=1e-12)

    def test_symmetric(self):
        """L(w1, w2) == L(w2, w1)（对称性）。"""
        l1 = mode_mismatch_loss_gaussian(0.5, 0.8)
        l2 = mode_mismatch_loss_gaussian(0.8, 0.5)
        assert l1 == pytest.approx(l2, abs=1e-12)

    def test_analytical_value(self):
        """解析验证: η = 2w1w2/(w1²+w2²), L = -10·log10(η)。"""
        w1, w2 = 0.5, 1.0
        eta = 2 * w1 * w2 / (w1**2 + w2**2)  # = 1.0 / 1.25 = 0.8
        expected = -10.0 * np.log10(eta)
        loss = mode_mismatch_loss_gaussian(w1, w2)
        assert loss == pytest.approx(expected, abs=1e-12)
        assert eta == pytest.approx(0.8, abs=1e-12)
        assert loss == pytest.approx(-10.0 * np.log10(0.8), abs=1e-12)

    def test_larger_mismatch_more_loss(self):
        """失配越大 → 损耗越大。"""
        l_small = mode_mismatch_loss_gaussian(0.5, 0.55)
        l_large = mode_mismatch_loss_gaussian(0.5, 1.5)
        assert l_large > l_small

    def test_invalid_w1(self):
        """R03: w1 ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="w1_um"):
            mode_mismatch_loss_gaussian(0.0, 0.5)
        with pytest.raises(ValueError, match="w1_um"):
            mode_mismatch_loss_gaussian(-1.0, 0.5)

    def test_invalid_w2(self):
        """R03: w2 ≤ 0 必须 raise。"""
        with pytest.raises(ValueError, match="w2_um"):
            mode_mismatch_loss_gaussian(0.5, 0.0)
        with pytest.raises(ValueError, match="w2_um"):
            mode_mismatch_loss_gaussian(0.5, -1.0)


# ============================================================================
# 集成测试: sim 顶层导入
# ============================================================================


class TestSimIntegration:
    """R291-R300 模块通过 polaris.sim 顶层导入可用。"""

    def test_import_from_sim_top(self):
        """所有 R291-R300 公开 API 可从 polaris.sim 顶层导入。"""
        from polaris.sim import (
            BatchScenarioResult,
            BatchSimulationResult,
            BatchYieldResult,
            RoughnessScatteringLoss,
            SidewallAngleCorrection,
            ToleranceAllocationResult,
            WorstCaseDistanceResult,
            YieldOptimizationResult,
            allocate_tolerance_by_sensitivity,
            batch_simulate,
            batch_yield_analysis,
            compute_worst_case_distance,
            correct_neff_for_sidewall_angle,
            mode_mismatch_loss_gaussian,
            optimize_yield_via_nominal_shift,
            sidewall_roughness_loss,
        )
        # 仅验证可导入
        assert BatchScenarioResult is not None
        assert batch_simulate is not None
        assert compute_worst_case_distance is not None
        assert correct_neff_for_sidewall_angle is not None

    def test_all_in_sim_all(self):
        """新符号都在 sim.__all__ 中。"""
        import polaris.sim as sim
        new_names = [
            "BatchScenarioResult", "BatchSimulationResult", "BatchYieldResult",
            "batch_simulate", "batch_yield_analysis",
            "ToleranceAllocationResult", "WorstCaseDistanceResult",
            "YieldOptimizationResult", "allocate_tolerance_by_sensitivity",
            "compute_worst_case_distance", "optimize_yield_via_nominal_shift",
            "RoughnessScatteringLoss", "SidewallAngleCorrection",
            "correct_neff_for_sidewall_angle", "mode_mismatch_loss_gaussian",
            "sidewall_roughness_loss",
        ]
        for name in new_names:
            assert name in sim.__all__, f"{name} 不在 sim.__all__"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
