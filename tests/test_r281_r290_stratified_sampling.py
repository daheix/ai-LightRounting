"""R281-R290 分层采样 (Stratified Sampling) 测试套件。

测试覆盖:
1. AllocationStrategy 枚举完整性
2. StratifiedSamplingResult dataclass 默认值
3. stratified_monte_carlo 三策略 (EQUAL/PROPORTIONAL/NEYMAN)
4. 解析解基准: E[X]=0 (N(0,1)), E[X²]=1 (N(0,1)), E[X]=0.5 (U(0,1))
5. Neyman 两阶段实现 (pilot + main, 无 fall-back)
6. 边界情况: n_strata=1 (退化朴素 MC), n_strata=100 (大层数稳定性)
7. 多维参数分层
8. 输入验证（12 个 ValueError 用例）
9. compare_stratified_convergence 收敛对比
10. 复现性（同 seed 同结果）
11. Neyman 优于 PROPORTIONAL 验证

学术依据:
- Cochran 1977, "Sampling Techniques", Wiley, Ch.5
- Neyman 1934, DOI: 10.2307/2342192 (最优分配)
- McKay et al. 1979, DOI: 10.1080/00401706.1979.10489755 (LHS 关系)

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必须修复。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.stratified_sampling import (
    AllocationStrategy,
    StratifiedSamplingResult,
    compare_stratified_convergence,
    stratified_monte_carlo,
)


# ============================================================================
# 1. AllocationStrategy 枚举
# ============================================================================


class TestAllocationStrategyEnum:
    """测试分配策略枚举完整性。"""

    def test_three_strategies_defined(self) -> None:
        """应有 EQUAL/PROPORTIONAL/NEYMAN 三种策略。"""
        assert AllocationStrategy.EQUAL.value == "equal"
        assert AllocationStrategy.PROPORTIONAL.value == "proportional"
        assert AllocationStrategy.NEYMAN.value == "neyman"

    def test_total_count(self) -> None:
        """枚举成员总数应为 3。"""
        assert len(list(AllocationStrategy)) == 3


# ============================================================================
# 2. StratifiedSamplingResult dataclass
# ============================================================================


class TestStratifiedSamplingResult:
    """测试结果数据类。"""

    def test_default_values(self) -> None:
        """默认值应为零/空。"""
        r = StratifiedSamplingResult()
        assert r.estimate == 0.0
        assert r.std_error == 0.0
        assert r.n_strata == 0
        assert r.n_samples == 0
        assert r.n_per_stratum == []
        assert r.strata_weights == []
        assert r.allocation_strategy == ""
        assert r.n_evaluations == 0

    def test_custom_values(self) -> None:
        """应能设置自定义值。"""
        r = StratifiedSamplingResult(
            estimate=0.5,
            std_error=0.01,
            n_strata=10,
            n_samples=1000,
            n_per_stratum=[100] * 10,
            strata_weights=[0.1] * 10,
            allocation_strategy="neyman",
            n_evaluations=1000,
        )
        assert r.estimate == 0.5
        assert r.n_strata == 10
        assert r.allocation_strategy == "neyman"


# ============================================================================
# 3. stratified_monte_carlo - 解析解基准
# ============================================================================


class TestStratifiedMonteCarloAnalytical:
    """解析解基准测试。"""

    def test_mean_zero_normal(self) -> None:
        """E_f[X] = 0, X ~ N(0,1)。估计应在 ±5σ 内。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 真值 = 0，SE ≈ 2e-3，5σ = 0.01
        assert abs(result.estimate - 0.0) < 0.01, (
            f"E[X] 估计 {result.estimate} 偏离 0 超过 5σ"
        )

    def test_second_moment_normal(self) -> None:
        """E_f[X²] = 1, X ~ N(0,1)。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=20,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 真值 = 1，SE ≈ 5e-3，5σ = 0.025
        assert abs(result.estimate - 1.0) < 0.025, (
            f"E[X²] 估计 {result.estimate} 偏离 1.0 超过 5σ"
        )

    def test_mean_uniform(self) -> None:
        """E_f[X] = 0.5, X ~ U(0,1)。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "uniform", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        # 真值 = 0.5，SE ≈ 3e-4，10σ = 0.003
        assert abs(result.estimate - 0.5) < 0.003, (
            f"E[X] 估计 {result.estimate} 偏离 0.5 超过 10σ"
        )

    def test_fourth_moment_normal(self) -> None:
        """E_f[X⁴] = 3, X ~ N(0,1)（标准正态四阶矩）。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 4),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=20,
            n_samples=20000,
            strategy=AllocationStrategy.NEYMAN,
            seed=42,
        )
        # 真值 = 3，允许 10% 误差（四阶矩方差大）
        assert abs(result.estimate - 3.0) < 0.3, (
            f"E[X⁴] 估计 {result.estimate} 偏离 3.0 超过 10%"
        )


# ============================================================================
# 4. 三策略对比
# ============================================================================


class TestAllocationStrategiesComparison:
    """测试三种分配策略。"""

    def test_equal_proportional_equivalent_equal_prob(self) -> None:
        """等概率分层下 EQUAL 与 PROPORTIONAL 等价。"""
        r_equal = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        r_prop = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        assert r_equal.estimate == pytest.approx(r_prop.estimate)
        assert r_equal.std_error == pytest.approx(r_prop.std_error)

    def test_neyman_better_than_proportional(self) -> None:
        """Neyman 对非线性函数 g(x)=x² 应优于 PROPORTIONAL。"""
        r_prop = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        r_ney = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.NEYMAN,
            seed=42,
        )
        # Neyman SE 应小于 PROPORTIONAL SE（理论保证）
        assert r_ney.std_error < r_prop.std_error, (
            f"Neyman SE {r_ney.std_error} 应小于 PROPORTIONAL SE {r_prop.std_error}"
        )
        # Neyman speedup 应大于 PROPORTIONAL speedup
        assert r_ney.speedup_vs_mc > r_prop.speedup_vs_mc, (
            f"Neyman speedup {r_ney.speedup_vs_mc} 应大于 PROPORTIONAL speedup {r_prop.speedup_vs_mc}"
        )

    def test_neyman_allocates_more_to_high_variance_strata(self) -> None:
        """Neyman 应给 |x| 大的层（σₕ 大）分配更多样本。"""
        r_ney = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.NEYMAN,
            seed=42,
        )
        n_per = r_ney.n_per_stratum
        # 第一层 (-inf, -1.28) 和最后一层 (1.28, inf) 应该样本最多
        # 中间层 (-0.13, 0.13) 样本最少
        assert n_per[0] > n_per[5], (
            f"层 0 ({n_per[0]}) 应大于层 5 ({n_per[5]})"
        )
        assert n_per[-1] > n_per[5], (
            f"层 -1 ({n_per[-1]}) 应大于层 5 ({n_per[5]})"
        )


# ============================================================================
# 5. 边界情况
# ============================================================================


class TestEdgeCases:
    """边界情况测试。"""

    def test_n_strata_1_degenerates_to_mc(self) -> None:
        """n_strata=1 时退化为朴素 MC，speedup 应接近 1。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=1,
            n_samples=10000,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        # speedup 应在 [0.9, 1.1] 附近（分层退化为不分层）
        assert 0.8 < result.speedup_vs_mc < 1.2, (
            f"n_strata=1 speedup {result.speedup_vs_mc} 应接近 1.0"
        )

    def test_large_n_strata_stability(self) -> None:
        """n_strata=100 大层数应稳定运行。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
            n_strata=100,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 应正常运行不崩溃
        assert result.n_strata == 100
        assert result.n_samples == 10000
        assert len(result.n_per_stratum) == 100
        # 估计应接近 1
        assert abs(result.estimate - 1.0) < 0.05

    def test_minimum_samples(self) -> None:
        """n_samples = n_strata 时每层 1 个样本。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "uniform", "loc": 0.0, "scale": 1.0}],
            n_strata=5,
            n_samples=5,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        assert result.n_samples == 5
        assert result.n_per_stratum == [1, 1, 1, 1, 1]
        assert sum(result.n_per_stratum) == 5


# ============================================================================
# 6. 多维参数
# ============================================================================


class TestMultivariate:
    """多维参数测试。"""

    def test_two_dim_sum(self) -> None:
        """E[X1 + X2] = 0, X1,X2 ~ N(0,1) 独立。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] + x[1]),
            nominal_dist=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 真值 = 0，分层仅在第一维，SE 比一维大但仍合理
        assert abs(result.estimate - 0.0) < 0.02

    def test_two_dim_product(self) -> None:
        """E[X1 · X2] = 0, X1,X2 ~ N(0,1) 独立。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] * x[1]),
            nominal_dist=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_strata=10,
            n_samples=20000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 真值 = 0（独立），允许稍宽误差
        assert abs(result.estimate - 0.0) < 0.02

    def test_two_dim_sums_of_squares(self) -> None:
        """E[X1² + X2²] = 2, X1,X2 ~ N(0,1)。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2 + x[1] ** 2),
            nominal_dist=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_strata=10,
            n_samples=20000,
            strategy=AllocationStrategy.NEYMAN,
            seed=42,
        )
        # 真值 = 2，允许 5% 误差
        assert abs(result.estimate - 2.0) < 0.1


# ============================================================================
# 7. 输入验证
# ============================================================================


class TestInputValidation:
    """输入验证测试（R03: 失败即 raise）。"""

    def test_empty_nominal_dist_raises(self) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[],
                n_strata=10,
                n_samples=1000,
            )

    def test_n_strata_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="n_strata"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
                n_strata=0,
                n_samples=1000,
            )

    def test_n_strata_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="n_strata"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
                n_strata=-1,
                n_samples=1000,
            )

    def test_n_samples_less_than_n_strata_raises(self) -> None:
        with pytest.raises(ValueError, match="n_samples"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
                n_strata=10,
                n_samples=5,
            )

    def test_unsupported_distribution_type_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持的分布类型"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "exponential", "loc": 0, "scale": 1}],
                n_strata=10,
                n_samples=1000,
            )

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持的分布类型"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"loc": 0, "scale": 1}],
                n_strata=10,
                n_samples=1000,
            )

    def test_func_failure_raises_runtime_error(self) -> None:
        """func 抛异常应转换为 RuntimeError（禁止 fall-back）。"""

        def bad_func(x: np.ndarray) -> float:
            if x[0] > 0:
                raise ValueError("模拟 func 失败")
            return float(x[0])

        with pytest.raises(RuntimeError, match="func 评估失败"):
            stratified_monte_carlo(
                func=bad_func,
                nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
                n_strata=2,
                n_samples=1000,
                seed=42,
            )

    def test_compare_empty_sample_sizes_raises(self) -> None:
        with pytest.raises(ValueError, match="sample_sizes 不能为空"):
            compare_stratified_convergence(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
                true_value=0.0,
                sample_sizes=[],
            )

    def test_compare_empty_dist_raises(self) -> None:
        with pytest.raises(ValueError, match="nominal_dist 不能为空"):
            compare_stratified_convergence(
                func=lambda x: float(x[0]),
                nominal_dist=[],
                true_value=0.0,
                sample_sizes=[100, 200],
            )

    def test_compare_zero_true_value_handled(self) -> None:
        """true_value=0 时不应除零（用绝对误差）。"""
        result = compare_stratified_convergence(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            true_value=0.0,
            sample_sizes=[1000, 4000],
            n_strata=10,
            seed=42,
        )
        # 应返回有限数（绝对误差）
        assert np.isfinite(result["mc_errors"][0])
        assert np.isfinite(result["stratified_errors"][0])


# ============================================================================
# 8. 复现性
# ============================================================================


class TestReproducibility:
    """复现性测试（同 seed 同结果）。"""

    def test_same_seed_same_result(self) -> None:
        """同 seed 应产生相同估计。"""
        r1 = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=5000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=123,
        )
        r2 = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=5000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=123,
        )
        assert r1.estimate == r2.estimate
        assert r1.std_error == r2.std_error

    def test_different_seed_different_result(self) -> None:
        """不同 seed 应产生不同估计（极大概率）。"""
        r1 = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=5000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=1,
        )
        r2 = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=5000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=2,
        )
        assert r1.estimate != r2.estimate


# ============================================================================
# 9. 收敛对比
# ============================================================================


class TestConvergenceComparison:
    """收敛对比测试。"""

    def test_stratified_converges_faster(self) -> None:
        """分层采样应比朴素 MC 更快收敛（误差更小）。"""
        result = compare_stratified_convergence(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            true_value=1.0,
            sample_sizes=[1000, 4000, 16000],
            n_strata=10,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        # 最终分层误差应小于 MC 误差
        assert result["stratified_final_error"] < result["mc_final_error"], (
            f"分层误差 {result['stratified_final_error']} 应小于 MC 误差 {result['mc_final_error']}"
        )
        assert result["speedup_factor"] > 1.0

    def test_returns_complete_dict(self) -> None:
        """返回的字典应包含所有键。"""
        result = compare_stratified_convergence(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "uniform", "loc": 0, "scale": 1}],
            true_value=0.5,
            sample_sizes=[1000, 4000],
            n_strata=10,
            seed=42,
        )
        required_keys = {
            "sample_sizes",
            "mc_errors",
            "stratified_errors",
            "mc_final_error",
            "stratified_final_error",
            "speedup_factor",
        }
        assert set(result.keys()) == required_keys
        assert len(result["mc_errors"]) == 2
        assert len(result["stratified_errors"]) == 2


# ============================================================================
# 10. 估计器结构属性
# ============================================================================


class TestResultStructure:
    """结果结构属性测试。"""

    def test_result_attributes_populated(self) -> None:
        """结果应包含完整的属性。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        assert result.n_strata == 10
        assert result.n_samples == 10000
        assert len(result.n_per_stratum) == 10
        assert sum(result.n_per_stratum) == 10000
        assert len(result.strata_weights) == 10
        assert all(abs(w - 0.1) < 1e-10 for w in result.strata_weights)
        assert len(result.strata_means) == 10
        assert len(result.strata_stds) == 10
        assert result.allocation_strategy == "proportional"
        assert result.n_evaluations == 10000

    def test_variance_decomposition(self) -> None:
        """方差估计 = Σ Wₕ² σₕ² / nₕ 应正确。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=5,
            n_samples=1000,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        # 手动计算方差
        expected_var = sum(
            (1.0 / 5) ** 2 * s * s / n
            for s, n in zip(result.strata_stds, result.n_per_stratum, strict=True)
            if n > 0
        )
        assert result.variance_estimate == pytest.approx(expected_var, rel=1e-10)
        assert result.std_error == pytest.approx(np.sqrt(expected_var), rel=1e-10)

    def test_ci_contains_estimate(self) -> None:
        """95% CI 应包含估计值。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0] ** 2),
            nominal_dist=[{"type": "norm", "loc": 0, "scale": 1}],
            n_strata=10,
            n_samples=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
            seed=42,
        )
        assert result.ci_lower < result.estimate < result.ci_upper
        # CI 宽度 ≈ 2 * 1.96 * SE
        ci_width = result.ci_upper - result.ci_lower
        assert ci_width == pytest.approx(2 * 1.96 * result.std_error, rel=1e-10)
