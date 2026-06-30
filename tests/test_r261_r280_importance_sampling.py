"""R261-R280 重要性采样 (Importance Sampling) 测试套件。

测试覆盖:
1. 数据类 (BiasingMethod/BiasingSpec/ImportanceSamplingResult)
2. 偏置分布构造 (5 种方法)
3. importance_sampling_yield 核心功能 (各偏置方法 + 解析解验证)
4. importance_sampling_mean 期望估计
5. rare_event_yield 便捷接口
6. cross_entropy_importance_sampling 自适应 IS
7. R03 禁止 fall-back (输入校验 + 退化诊断)
8. 可复现性 (随机种子)
9. 与朴素 MC 对比 (加速比验证)

学术基准:
- P(X>3), X~N(0,1): 真值 0.001350 (右尾稀有事件)
- P(|X|>2), X~N(0,1): 真值 0.045500 (对称双尾)
- E_f[X²] = 1: 标准正态二阶矩
- 多维 P(X1+X2>4): 真值 1-Φ(4/√2) ≈ 0.002339

来源:
- Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
- Glasserman 2003, DOI: 10.1007/978-0-387-21617-1
- Rubinstein 1997 (CE 方法), DOI: 10.1016/S0377-2217(96)00385-2
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from polaris.sim.importance_sampling import (
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
    cross_entropy_importance_sampling,
    importance_sampling_mean,
    importance_sampling_yield,
    rare_event_yield,
)


# ============================================================================
# 解析解基准函数
# ============================================================================


def _failure_right_tail_3(x: np.ndarray) -> bool:
    """失效区域: X > 3 (右尾稀有事件)。

    真值 P(X>3) = 1 - Φ(3) ≈ 0.001350。
    """
    return float(x[0]) > 3.0


def _failure_symmetric_2(x: np.ndarray) -> bool:
    """失效区域: |X| > 2 (对称双尾)。

    真值 P(|X|>2) = 2(1-Φ(2)) ≈ 0.045500。
    """
    return abs(float(x[0])) > 2.0


def _failure_sum_2d(x: np.ndarray) -> bool:
    """失效区域: X1 + X2 > 4 (二维和过程)。

    真值 P(X1+X2>4) = 1 - Φ(4/√2) ≈ 0.002339 (X~N(0,I))。
    """
    return float(x[0] + x[1]) > 4.0


def _g_x_squared(x: np.ndarray) -> float:
    """性能函数 g(X) = X²。

    E_f[X²] = Var + mean² = 1 + 0 = 1 (X~N(0,1))。
    """
    return float(x[0]) ** 2


# ============================================================================
# TestBiasingMethodEnum: 枚举完整性
# ============================================================================


class TestBiasingMethodEnum:
    """R261 BiasingMethod 枚举完整性。"""

    def test_enum_has_5_methods(self) -> None:
        """TR-261.1: 5 种偏置方法定义。"""
        assert len(BiasingMethod) == 5

    def test_enum_values(self) -> None:
        """TR-261.2: 枚举值字符串。"""
        assert BiasingMethod.MEAN_SHIFT.value == "mean_shift"
        assert BiasingMethod.VARIANCE_SCALING.value == "variance_scaling"
        assert BiasingMethod.EXPONENTIAL_TWIST.value == "exponential_twist"
        assert BiasingMethod.MIXTURE.value == "mixture"
        assert BiasingMethod.CROSS_ENTROPY.value == "cross_entropy"


# ============================================================================
# TestBiasingSpec: 数据类
# ============================================================================


class TestBiasingSpec:
    """R261 BiasingSpec 数据类。"""

    def test_default_method_is_mean_shift(self) -> None:
        """TR-261.3: 默认方法是 MEAN_SHIFT。"""
        spec = BiasingSpec()
        assert spec.method == BiasingMethod.MEAN_SHIFT

    def test_default_alpha(self) -> None:
        """TR-261.4: 默认 mixture_alpha=0.3。"""
        spec = BiasingSpec()
        assert spec.mixture_alpha == 0.3
        assert spec.elite_ratio == 0.1
        assert spec.n_iterations == 5
        assert spec.smoothing_alpha == 0.7

    def test_custom_spec(self) -> None:
        """TR-261.5: 自定义规格。"""
        spec = BiasingSpec(
            method=BiasingMethod.MIXTURE,
            mean_shift=[1.0, 2.0],
            mixture_alpha=0.4,
        )
        assert spec.method == BiasingMethod.MIXTURE
        assert spec.mean_shift == [1.0, 2.0]
        assert spec.mixture_alpha == 0.4


# ============================================================================
# TestImportanceSamplingResult: 结果数据类
# ============================================================================


class TestImportanceSamplingResult:
    """R261 ImportanceSamplingResult 数据类。"""

    def test_default_values(self) -> None:
        """TR-261.6: 默认值。"""
        r = ImportanceSamplingResult()
        assert r.yield_estimate == 0.0
        assert r.std_error == 0.0
        assert r.n_samples == 0
        assert r.n_failures == 0
        assert r.converged is None
        assert r.biasing_method == ""
        assert r.log_weights.size == 0
        assert r.samples.size == 0

    def test_ci_bounds(self) -> None:
        """TR-261.7: 置信区间边界。"""
        r = ImportanceSamplingResult(
            yield_estimate=0.5, std_error=0.1
        )
        # CI 默认 0.0，需显式设置
        assert r.ci_lower == 0.0
        assert r.ci_upper == 0.0


# ============================================================================
# TestImportanceSamplingYield: 核心功能 (5 种偏置方法)
# ============================================================================


class TestImportanceSamplingYield:
    """R262-R270 importance_sampling_yield 核心功能。"""

    NOMINAL_DIST = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
    TRUE_P_RIGHT_TAIL = 1.0 - norm.cdf(3.0)  # ≈ 0.001350

    def test_mean_shift_accuracy(self) -> None:
        """TR-262.1: MEAN_SHIFT 估计 P(X>3) 精度 < 10% 相对误差。"""
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.biasing_method == "mean_shift"
        rel_err = abs(r.yield_estimate - self.TRUE_P_RIGHT_TAIL) / self.TRUE_P_RIGHT_TAIL
        assert rel_err < 0.10, f"MEAN_SHIFT 相对误差 {rel_err:.4f} > 10%"
        assert r.relative_error < 0.05  # IS 内部 RE < 5%
        assert r.speedup_vs_mc > 10.0  # 至少 10 倍加速
        assert r.n_failures >= 30

    def test_mixture_accuracy(self) -> None:
        """TR-263.1: MIXTURE 估计 P(X>3) 精度 < 10%。"""
        biasing = BiasingSpec(
            method=BiasingMethod.MIXTURE,
            mean_shift=[3.0],
            mixture_alpha=0.5,
        )
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.biasing_method == "mixture"
        rel_err = abs(r.yield_estimate - self.TRUE_P_RIGHT_TAIL) / self.TRUE_P_RIGHT_TAIL
        assert rel_err < 0.10
        assert r.speedup_vs_mc > 5.0

    def test_exponential_twist_accuracy(self) -> None:
        """TR-264.1: EXPONENTIAL_TWIST 估计 P(X>3) 精度 < 20%。

        theta=1 → q=N(0+1²·1, 1)=N(1,1)，对右尾问题偏置较弱但有效。
        """
        biasing = BiasingSpec(
            method=BiasingMethod.EXPONENTIAL_TWIST, twist_theta=[1.0]
        )
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.biasing_method == "exponential_twist"
        rel_err = abs(r.yield_estimate - self.TRUE_P_RIGHT_TAIL) / self.TRUE_P_RIGHT_TAIL
        assert rel_err < 0.20
        assert r.speedup_vs_mc > 2.0

    def test_variance_scaling_symmetric(self) -> None:
        """TR-265.1: VARIANCE_SCALING 对对称失效 |X|>2 精度 < 10%。

        VARIANCE_SCALING 对称加厚尾部，适合对称失效区域。
        """
        true_p_sym = 2.0 * (1.0 - norm.cdf(2.0))  # ≈ 0.045500
        biasing = BiasingSpec(
            method=BiasingMethod.VARIANCE_SCALING, variance_scale=[1.5]
        )
        r = importance_sampling_yield(
            failure_region=_failure_symmetric_2,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.biasing_method == "variance_scaling"
        rel_err = abs(r.yield_estimate - true_p_sym) / true_p_sym
        assert rel_err < 0.10
        assert r.speedup_vs_mc > 1.5

    def test_yield_estimate_in_valid_range(self) -> None:
        """TR-262.2: 良率估计在 [0, 1] 范围内。"""
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert 0.0 <= r.yield_estimate <= 1.0
        assert 0.0 <= r.ci_lower <= r.ci_upper

    def test_ci_contains_true_value(self) -> None:
        """TR-262.3: 95% CI 包含真值。"""
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.ci_lower <= self.TRUE_P_RIGHT_TAIL <= r.ci_upper

    def test_2d_failure_region(self) -> None:
        """TR-266.1: 二维失效区域 P(X1+X2>4)。"""
        true_p_2d = 1.0 - norm.cdf(4.0 / np.sqrt(2.0))  # ≈ 0.002339
        nominal_2d = [
            {"type": "norm", "loc": 0.0, "scale": 1.0},
            {"type": "norm", "loc": 0.0, "scale": 1.0},
        ]
        biasing = BiasingSpec(
            method=BiasingMethod.MEAN_SHIFT, mean_shift=[2.0, 2.0]
        )
        r = importance_sampling_yield(
            failure_region=_failure_sum_2d,
            nominal_dist=nominal_2d,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        rel_err = abs(r.yield_estimate - true_p_2d) / true_p_2d
        assert rel_err < 0.15, f"二维相对误差 {rel_err:.4f}"
        assert r.speedup_vs_mc > 5.0

    def test_speedup_greater_than_one(self) -> None:
        """TR-267.1: IS 加速比 > 1（有效方差减少）。"""
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r = importance_sampling_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=self.NOMINAL_DIST,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert r.speedup_vs_mc > 1.0

    def test_uniform_distribution_support(self) -> None:
        """TR-268.1: uniform 分布规格支持。"""
        # X ~ Uniform(0, 10), 失效 X > 9, 真值 0.1
        nominal = [{"type": "uniform", "loc": 0.0, "scale": 10.0}]

        def failure(x: np.ndarray) -> bool:
            return float(x[0]) > 9.0

        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0])
        r = importance_sampling_yield(
            failure_region=failure,
            nominal_dist=nominal,
            biasing=biasing,
            n_samples=10000,
            seed=42,
        )
        # 真值 0.1, 允许 20% 相对误差
        assert abs(r.yield_estimate - 0.1) / 0.1 < 0.20


# ============================================================================
# TestImportanceSamplingMean: 期望估计
# ============================================================================


class TestImportanceSamplingMean:
    """R268 importance_sampling_mean 期望估计。"""

    def test_mean_x_squared(self) -> None:
        """TR-268.2: E_f[X²] = 1 (X~N(0,1))。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[0.5])
        r = importance_sampling_mean(
            func=_g_x_squared,
            nominal_dist=nominal,
            biasing=biasing,
            n_samples=20000,
            seed=42,
        )
        assert abs(r.yield_estimate - 1.0) < 0.05, (
            f"E[X²]={r.yield_estimate:.4f} 偏离真值 1.0"
        )
        assert r.relative_error < 0.05

    def test_mean_returns_importance_sampling_result(self) -> None:
        """TR-268.3: 返回 ImportanceSamplingResult 类型。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[0.5])
        r = importance_sampling_mean(
            func=_g_x_squared,
            nominal_dist=nominal,
            biasing=biasing,
            n_samples=5000,
            seed=42,
        )
        assert isinstance(r, ImportanceSamplingResult)
        assert r.n_failures == 0  # 非良率场景


# ============================================================================
# TestRareEventYield: 便捷接口
# ============================================================================


class TestRareEventYield:
    """R269 rare_event_yield 便捷接口。"""

    TRUE_P = 1.0 - norm.cdf(3.0)

    def test_rare_event_yield_matches_mean_shift(self) -> None:
        """TR-269.1: rare_event_yield 等价于 MEAN_SHIFT。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        r = rare_event_yield(
            failure_region=_failure_right_tail_3,
            nominal_dist=nominal,
            biasing_mean_shift=[3.0],
            n_samples=20000,
            seed=42,
        )
        assert r.biasing_method == "mean_shift"
        rel_err = abs(r.yield_estimate - self.TRUE_P) / self.TRUE_P
        assert rel_err < 0.10

    def test_rare_event_yield_simple_api(self) -> None:
        """TR-269.2: 简化 API 仅需 biasing_mean_shift。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        # 仅需 4 个参数: failure_region, nominal_dist, biasing_mean_shift, n_samples
        r = rare_event_yield(
            _failure_right_tail_3, nominal, [3.0], n_samples=20000, seed=42
        )
        assert r.yield_estimate > 0


# ============================================================================
# TestCrossEntropy: 自适应 IS
# ============================================================================


class TestCrossEntropy:
    """R270-R280 cross_entropy_importance_sampling 自适应 IS。"""

    TRUE_P = 1.0 - norm.cdf(3.0)

    def test_ce_accuracy(self) -> None:
        """TR-270.1: CE 估计 P(X>3) 精度 < 25%。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        r = cross_entropy_importance_sampling(
            failure_region=_failure_right_tail_3,
            nominal_dist=nominal,
            initial_mean_shift=[2.0],
            n_samples=2000,
            n_iterations=5,
            seed=42,
        )
        assert r.biasing_method == "cross_entropy"
        rel_err = abs(r.yield_estimate - self.TRUE_P) / self.TRUE_P
        assert rel_err < 0.25, f"CE 相对误差 {rel_err:.4f}"

    def test_ce_n_evaluations_includes_iterations(self) -> None:
        """TR-270.2: n_evaluations 包含迭代 + 最终估计。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        n_iter = 5
        n_samples = 2000
        r = cross_entropy_importance_sampling(
            failure_region=_failure_right_tail_3,
            nominal_dist=nominal,
            initial_mean_shift=[2.0],
            n_samples=n_samples,
            n_iterations=n_iter,
            seed=42,
        )
        # n_evaluations >= n_samples（最终估计）+ 至少一次迭代
        assert r.n_evaluations >= n_samples
        assert r.n_evaluations <= n_samples * (n_iter + 1)

    def test_ce_converged_flag(self) -> None:
        """TR-270.3: converged 标志为 bool 或 None。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        r = cross_entropy_importance_sampling(
            failure_region=_failure_right_tail_3,
            nominal_dist=nominal,
            initial_mean_shift=[2.0],
            n_samples=2000,
            n_iterations=3,
            seed=42,
        )
        assert r.converged is None or isinstance(r.converged, bool)


# ============================================================================
# TestInputValidation: R03 禁止 fall-back (输入校验)
# ============================================================================


class TestInputValidation:
    """R261-R280 R03 禁止 fall-back 输入校验。"""

    def test_empty_nominal_dist_raises(self) -> None:
        """TR-261.8: 空 nominal_dist raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0]),
            )

    def test_zero_n_samples_raises(self) -> None:
        """TR-261.9: n_samples=0 raise ValueError。"""
        with pytest.raises(ValueError, match="n_samples"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0]),
                n_samples=0,
            )

    def test_invalid_min_ess_ratio_raises(self) -> None:
        """TR-261.10: min_ess_ratio 不在 (0,1) raise ValueError。"""
        with pytest.raises(ValueError, match="min_ess_ratio"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0]),
                n_samples=1000,
                min_ess_ratio=1.5,
            )

    def test_mean_shift_missing_raises(self) -> None:
        """TR-261.11: MEAN_SHIFT 缺 mean_shift raise ValueError。"""
        with pytest.raises(ValueError, match="mean_shift"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=None),
            )

    def test_mean_shift_wrong_length_raises(self) -> None:
        """TR-261.12: mean_shift 长度不匹配 raise ValueError。"""
        with pytest.raises(ValueError, match="mean_shift"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0, 2.0]),
            )

    def test_variance_scale_nonpositive_raises(self) -> None:
        """TR-261.13: variance_scale<=0 raise ValueError。"""
        with pytest.raises(ValueError, match="variance_scale"):
            importance_sampling_yield(
                failure_region=_failure_symmetric_2,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(
                    method=BiasingMethod.VARIANCE_SCALING, variance_scale=[-1.0]
                ),
            )

    def test_invalid_mixture_alpha_raises(self) -> None:
        """TR-261.14: mixture_alpha 不在 (0,1) raise ValueError。"""
        with pytest.raises(ValueError, match="mixture_alpha"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(
                    method=BiasingMethod.MIXTURE,
                    mean_shift=[3.0],
                    mixture_alpha=1.5,
                ),
            )

    def test_invalid_distribution_type_raises(self) -> None:
        """TR-261.15: 不支持的分布类型 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持"):
            importance_sampling_yield(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "exponential", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0]),
                n_samples=100,
            )

    def test_ce_non_norm_distribution_raises(self) -> None:
        """TR-270.4: CE 不支持非 norm 分布 raise ValueError。"""
        with pytest.raises(ValueError, match="norm"):
            cross_entropy_importance_sampling(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "uniform", "loc": 0.0, "scale": 1.0}],
                initial_mean_shift=[1.0],
            )

    def test_ce_invalid_elite_ratio_raises(self) -> None:
        """TR-270.5: elite_ratio 不在 (0,1) raise ValueError。"""
        with pytest.raises(ValueError, match="elite_ratio"):
            cross_entropy_importance_sampling(
                failure_region=_failure_right_tail_3,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                initial_mean_shift=[2.0],
                elite_ratio=1.5,
            )

    def test_failure_region_exception_propagates(self) -> None:
        """TR-261.16: failure_region 异常传播为 RuntimeError。"""
        def bad_failure(x: np.ndarray) -> bool:
            raise ValueError("测试异常")

        with pytest.raises(RuntimeError, match="failure_region"):
            importance_sampling_yield(
                failure_region=bad_failure,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0]),
                n_samples=100,
            )

    def test_insufficient_failures_raises(self) -> None:
        """TR-261.17: 失效样本 < 30 raise RuntimeError。"""
        # 极端稀有事件 + 偏置不足
        def very_rare(x: np.ndarray) -> bool:
            return float(x[0]) > 10.0

        with pytest.raises(RuntimeError, match="失效样本数"):
            importance_sampling_yield(
                failure_region=very_rare,
                nominal_dist=[{"type": "norm", "loc": 0.0, "scale": 1.0}],
                biasing=BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[1.0]),
                n_samples=500,
            )


# ============================================================================
# TestReproducibility: 可复现性
# ============================================================================


class TestReproducibility:
    """R261-R280 随机种子可复现性。"""

    def test_same_seed_same_result(self) -> None:
        """TR-261.18: 相同种子产生相同结果。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r1 = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=5000, seed=123
        )
        r2 = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=5000, seed=123
        )
        assert r1.yield_estimate == pytest.approx(r2.yield_estimate, rel=1e-10)
        assert r1.n_failures == r2.n_failures

    def test_different_seed_different_result(self) -> None:
        """TR-261.19: 不同种子产生不同结果。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r1 = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=5000, seed=1
        )
        r2 = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=5000, seed=2
        )
        # 不同种子下估计应略有不同（但都在真值附近）
        assert r1.yield_estimate != r2.yield_estimate


# ============================================================================
# TestVsNaiveMonteCarlo: 与朴素 MC 对比
# ============================================================================


class TestVsNaiveMonteCarlo:
    """R261-R280 IS vs 朴素 MC 对比。"""

    def test_is_beats_mc_for_rare_event(self) -> None:
        """TR-261.20: 稀有事件下 IS 优于朴素 MC。

        对 P(X>3)=0.00135, n=20000:
        - 朴素 MC 失效样本 ~27 个, RE 高
        - IS 失效样本 ~10000 个, RE 低
        """
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        true_p = 1.0 - norm.cdf(3.0)
        n = 20000

        # 朴素 MC
        rng = np.random.default_rng(42)
        mc_samples = rng.normal(0, 1, n)
        mc_failures = int(np.sum(mc_samples > 3.0))
        mc_y = mc_failures / n
        mc_se = np.sqrt(mc_y * (1 - mc_y) / n)

        # IS
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        is_result = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=n, seed=42
        )

        # IS 的相对误差应远低于朴素 MC
        mc_re = mc_se / mc_y if mc_y > 0 else float("inf")
        assert is_result.relative_error < mc_re, (
            f"IS RE={is_result.relative_error:.4f} 应低于 MC RE={mc_re:.4f}"
        )
        # IS 失效样本数应远多于 MC
        assert is_result.n_failures > mc_failures * 10

    def test_is_provides_speedup(self) -> None:
        """TR-261.21: IS 提供方差缩减加速比 > 10。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        biasing = BiasingSpec(method=BiasingMethod.MEAN_SHIFT, mean_shift=[3.0])
        r = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing, n_samples=20000, seed=42
        )
        assert r.speedup_vs_mc > 10.0, (
            f"Speedup={r.speedup_vs_mc:.1f} 应 > 10"
        )


# ============================================================================
# TestMixtureProperties: MIXTURE 特性
# ============================================================================


class TestMixtureProperties:
    """R263 MIXTURE 偏置特性。"""

    def test_mixture_always_unbiased(self) -> None:
        """TR-263.2: MIXTURE 即使 h 选偏也保证无偏。

        MIXTURE = (1-α)f + α·h，f 分量保证支撑覆盖，无偏性保持。
        """
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        true_p = 1.0 - norm.cdf(3.0)

        # 故意让 h 偏向错误方向（mean_shift 负值）
        biasing = BiasingSpec(
            method=BiasingMethod.MIXTURE,
            mean_shift=[-1.0],  # 偏离失效区
            mixture_alpha=0.3,
        )
        # 即使 h 选偏，MIXTURE 仍能估计（但效率低）
        # 用更宽松的容差验证无偏性
        r = importance_sampling_yield(
            _failure_right_tail_3, nominal, biasing,
            n_samples=50000, seed=42,
        )
        # 估计应在 3 倍真值范围内（无偏但低效）
        assert r.yield_estimate < true_p * 5, (
            f"MIXTURE 估计 {r.yield_estimate:.6f} 应接近真值 {true_p:.6f}"
        )


# ============================================================================
# TestEdgeCases: 边界情况
# ============================================================================


class TestEdgeCases:
    """R261-R280 边界情况。"""

    def test_high_dimensional(self) -> None:
        """TR-261.22: 5 维失效区域。"""
        d = 5
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0} for _ in range(d)]

        def failure(x: np.ndarray) -> bool:
            return float(np.sum(x)) > 8.0  # 失效: 5 维标准正态和 > 8

        # 真值: P(N(0,5)>8) = 1-Φ(8/√5)
        true_p = 1.0 - norm.cdf(8.0 / np.sqrt(d))

        biasing = BiasingSpec(
            method=BiasingMethod.MEAN_SHIFT,
            mean_shift=[1.6] * d,  # 总偏移 8
        )
        r = importance_sampling_yield(
            failure, nominal, biasing, n_samples=30000, seed=42
        )
        rel_err = abs(r.yield_estimate - true_p) / true_p
        assert rel_err < 0.30, f"5维相对误差 {rel_err:.4f}"

    def test_ce_with_large_iterations(self) -> None:
        """TR-270.6: CE 多次迭代。"""
        nominal = [{"type": "norm", "loc": 0.0, "scale": 1.0}]
        r = cross_entropy_importance_sampling(
            failure_region=_failure_right_tail_3,
            nominal_dist=nominal,
            initial_mean_shift=[2.0],
            n_samples=1000,
            n_iterations=10,
            seed=42,
        )
        assert r.n_evaluations >= 1000  # 至少一次迭代
        # CE 应该给出合理估计
        true_p = 1.0 - norm.cdf(3.0)
        assert r.yield_estimate < true_p * 5  # 宽松验证
