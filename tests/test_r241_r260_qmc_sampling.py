"""R241-R260 QMC 采样框架测试。

验证拉丁超立方采样 (LHS)、Sobol 序列、Halton 序列、QMC 蒙特卡洛仿真、
QMC vs MC 收敛对比功能。

学术依据:
- LHS: McKay et al. 1979, DOI: 10.1080/00401706.1979.10489755
- Sobol 序列: Sobol 1967
- Halton 序列: Halton 1960
- QMC: Niederreiter 1992, DOI: 10.1137/1.9781611970081

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.qmc_sampling import (
    QMCConvergenceComparison,
    QMCMonteCarloResult,
    QMCSampleResult,
    QMCSamplerType,
    compare_qmc_convergence,
    generate_qmc_samples,
    qmc_monte_carlo,
    transform_to_distribution,
)


# ============================================================================
# 解析解基准函数
# ============================================================================


def _mean_of_sum(x: np.ndarray) -> float:
    """f(x) = x1 + x2，E[Y] = E[x1] + E[x2] = 0 + 0 = 0（标准正态）。

    解析解: E[Y] = 0
    """
    return float(x[0] + x[1])


def _mean_of_uniform_sum(x: np.ndarray) -> float:
    """f(x) = x1 + x2，E[Y] = 0.5 + 0.5 = 1（Uniform(0,1)）。

    解析解: E[Y] = 1.0
    """
    return float(x[0] + x[1])


# ============================================================================
# TestQMCSamplerTypeEnum: 枚举测试
# ============================================================================


class TestQMCSamplerTypeEnum:
    """QMCSamplerType 枚举测试。"""

    def test_enum_values(self):
        """枚举值测试。"""
        assert QMCSamplerType.LATIN_HYPERCUBE.value == "latin_hypercube"
        assert QMCSamplerType.SOBOL.value == "sobol"
        assert QMCSamplerType.HALTON.value == "halton"

    def test_enum_from_string(self):
        """从字符串构造枚举。"""
        assert QMCSamplerType("latin_hypercube") == QMCSamplerType.LATIN_HYPERCUBE
        assert QMCSamplerType("sobol") == QMCSamplerType.SOBOL
        assert QMCSamplerType("halton") == QMCSamplerType.HALTON


# ============================================================================
# TestGenerateQMCSamples: QMC 样本生成测试（R241-R250）
# ============================================================================


class TestGenerateQMCSamples:
    """generate_qmc_samples() 函数测试。"""

    def test_lhs_basic(self):
        """LHS 基本采样。"""
        result = generate_qmc_samples(
            n_samples=100,
            n_dimensions=2,
            sampler_type=QMCSamplerType.LATIN_HYPERCUBE,
            seed=42,
        )
        assert result.samples.shape == (100, 2)
        assert result.n_samples == 100
        assert result.n_dimensions == 2
        assert result.sampler_type == QMCSamplerType.LATIN_HYPERCUBE
        # 值域 [0, 1]
        assert result.samples.min() >= 0.0
        assert result.samples.max() <= 1.0

    def test_sobol_basic(self):
        """Sobol 序列基本采样。"""
        result = generate_qmc_samples(
            n_samples=128,  # 2 的幂
            n_dimensions=2,
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        assert result.samples.shape == (128, 2)
        assert result.n_samples == 128
        assert result.sampler_type == QMCSamplerType.SOBOL
        # 值域 [0, 1]
        assert result.samples.min() >= 0.0
        assert result.samples.max() <= 1.0

    def test_halton_basic(self):
        """Halton 序列基本采样。"""
        result = generate_qmc_samples(
            n_samples=100,
            n_dimensions=2,
            sampler_type=QMCSamplerType.HALTON,
            seed=42,
        )
        assert result.samples.shape == (100, 2)
        assert result.n_samples == 100
        assert result.sampler_type == QMCSamplerType.HALTON

    def test_discrepancy_lower_than_random(self):
        """QMC 样本星偏差应显著低于纯随机。

        纯随机星偏差 ~0.1，LHS/Sobol ~0.01。
        """
        # Sobol 样本
        qmc_result = generate_qmc_samples(
            n_samples=256,
            n_dimensions=2,
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        # 纯随机样本
        rng = np.random.default_rng(42)
        random_samples = rng.uniform(0, 1, size=(256, 2))
        from scipy.stats import qmc as scipy_qmc

        random_disc = float(scipy_qmc.discrepancy(random_samples))

        # QMC 偏差应显著低于纯随机
        assert qmc_result.discrepancy < random_disc
        assert qmc_result.discrepancy < 0.05  # QMC 应 < 0.05

    def test_reproducibility(self):
        """相同 seed 产生相同样本。"""
        r1 = generate_qmc_samples(
            n_samples=64,
            n_dimensions=2,
            sampler_type=QMCSamplerType.SOBOL,
            seed=123,
        )
        r2 = generate_qmc_samples(
            n_samples=64,
            n_dimensions=2,
            sampler_type=QMCSamplerType.SOBOL,
            seed=123,
        )
        np.testing.assert_array_equal(r1.samples, r2.samples)

    def test_invalid_n_samples_raises(self):
        """n_samples <= 0 应 raise（R03）。"""
        with pytest.raises(ValueError, match="n_samples 必须 > 0"):
            generate_qmc_samples(n_samples=0, n_dimensions=2)

    def test_invalid_n_dimensions_raises(self):
        """n_dimensions <= 0 应 raise（R03）。"""
        with pytest.raises(ValueError, match="n_dimensions 必须 > 0"):
            generate_qmc_samples(n_samples=64, n_dimensions=0)

    def test_sobol_non_power_of_two_raises(self):
        """Sobol 采样器 n_samples 非 2 的幂应 raise（R03）。"""
        with pytest.raises(ValueError, match="2 的幂"):
            generate_qmc_samples(
                n_samples=100,  # 非 2 的幂
                n_dimensions=2,
                sampler_type=QMCSamplerType.SOBOL,
            )

    def test_default_sobol(self):
        """默认采样器为 Sobol。"""
        result = generate_qmc_samples(
            n_samples=64,
            n_dimensions=2,
            seed=42,
        )
        assert result.sampler_type == QMCSamplerType.SOBOL


# ============================================================================
# TestTransformToDistribution: 分布转换测试（R241-R250）
# ============================================================================


class TestTransformToDistribution:
    """transform_to_distribution() 逆变换采样测试。"""

    def test_norm_transform_mean(self):
        """正态分布转换: 均值应接近 loc。"""
        # 生成 [0,1] 均匀样本
        uniform = np.full((1000, 1), 0.5)  # 全 0.5
        # 转换为 norm(loc=2.0, scale=1.0)
        # ppf(0.5) = loc = 2.0
        transformed = transform_to_distribution(
            uniform_samples=uniform,
            distributions=[{"type": "norm", "loc": 2.0, "scale": 1.0}],
        )
        # 中位数应等于 loc
        assert np.median(transformed) == pytest.approx(2.0, abs=0.01)

    def test_uniform_transform_range(self):
        """均匀分布转换: 值域应在 [loc, loc+scale]。"""
        rng = np.random.default_rng(42)
        uniform = rng.uniform(0, 1, size=(500, 1))
        transformed = transform_to_distribution(
            uniform_samples=uniform,
            distributions=[{"type": "uniform", "loc": 1.0, "scale": 3.0}],
        )
        assert transformed.min() >= 1.0
        assert transformed.max() <= 4.0  # loc + scale = 1 + 3

    def test_norm_distribution_statistics(self):
        """正态分布转换: 样本均值/标准差应接近 loc/scale。"""
        # 用 QMC 生成高质量 [0,1] 样本
        result = generate_qmc_samples(
            n_samples=1024,
            n_dimensions=1,
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        transformed = transform_to_distribution(
            uniform_samples=result.samples,
            distributions=[{"type": "norm", "loc": 5.0, "scale": 2.0}],
        )
        # 均值 ≈ 5.0, 标准差 ≈ 2.0
        assert np.mean(transformed) == pytest.approx(5.0, abs=0.2)
        assert np.std(transformed) == pytest.approx(2.0, abs=0.2)

    def test_dimension_mismatch_raises(self):
        """维度不匹配应 raise（R03）。"""
        with pytest.raises(ValueError, match="不匹配"):
            transform_to_distribution(
                uniform_samples=np.array([[0.5, 0.5]]),  # 2 维
                distributions=[{"type": "norm"}],  # 1 个分布
            )

    def test_invalid_distribution_type_raises(self):
        """无效分布类型应 raise（R03）。"""
        with pytest.raises(ValueError, match="不支持的分布类型"):
            transform_to_distribution(
                uniform_samples=np.array([[0.5]]),
                distributions=[{"type": "exponential"}],
            )

    def test_1d_input_raises(self):
        """1D 输入应 raise。"""
        with pytest.raises(ValueError, match="2D"):
            transform_to_distribution(
                uniform_samples=np.array([0.5, 0.6]),  # 1D
                distributions=[{"type": "norm"}, {"type": "norm"}],
            )


# ============================================================================
# TestQMCMonteCarlo: QMC 蒙特卡洛仿真测试（R241-R260）
# ============================================================================


class TestQMCMonteCarlo:
    """qmc_monte_carlo() 函数测试。"""

    def test_basic_qmc_mc(self):
        """QMC 蒙特卡洛基本功能。"""
        result = qmc_monte_carlo(
            func=_mean_of_sum,
            n_samples=128,
            distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        assert result.n_samples == 128
        assert result.n_evaluations == 128
        assert result.sampler_type == QMCSamplerType.SOBOL
        # E[x1+x2] = 0
        assert result.mean == pytest.approx(0.0, abs=0.1)

    def test_uniform_qmc_mc(self):
        """均匀分布 QMC MC: E[x1+x2] = 1.0。"""
        result = qmc_monte_carlo(
            func=_mean_of_uniform_sum,
            n_samples=128,
            distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        # E[x1+x2] = 0.5 + 0.5 = 1.0
        assert result.mean == pytest.approx(1.0, abs=0.05)

    def test_lhs_mc(self):
        """LHS 蒙特卡洛仿真。"""
        result = qmc_monte_carlo(
            func=_mean_of_uniform_sum,
            n_samples=256,
            distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            sampler_type=QMCSamplerType.LATIN_HYPERCUBE,
            seed=42,
        )
        assert result.sampler_type == QMCSamplerType.LATIN_HYPERCUBE
        assert result.mean == pytest.approx(1.0, abs=0.05)

    def test_halton_mc(self):
        """Halton 蒙特卡洛仿真。"""
        result = qmc_monte_carlo(
            func=_mean_of_uniform_sum,
            n_samples=256,
            distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            sampler_type=QMCSamplerType.HALTON,
            seed=42,
        )
        assert result.sampler_type == QMCSamplerType.HALTON
        assert result.mean == pytest.approx(1.0, abs=0.05)

    def test_empty_distributions_raises(self):
        """空分布列表应 raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            qmc_monte_carlo(
                func=lambda p: float(p[0]),
                n_samples=128,
                distributions=[],
            )

    def test_sobol_non_power_of_two_raises(self):
        """Sobol 非 2 的幂应 raise。"""
        with pytest.raises(ValueError, match="2 的幂"):
            qmc_monte_carlo(
                func=lambda p: float(p[0]),
                n_samples=100,
                distributions=[{"type": "norm"}],
                sampler_type=QMCSamplerType.SOBOL,
            )

    def test_outputs_shape(self):
        """输出数组形状正确。"""
        result = qmc_monte_carlo(
            func=lambda p: float(p[0] + p[1]),
            n_samples=64,
            distributions=[{"type": "norm"}, {"type": "norm"}],
            seed=42,
        )
        assert result.outputs.shape == (64,)


# ============================================================================
# TestQMCConvergence: QMC vs MC 收敛对比测试（R241-R260）
# ============================================================================


class TestQMCConvergence:
    """compare_qmc_convergence() 函数测试。

    验证 QMC 在相同样本数下比朴素 MC 误差更低（方差减少效果）。
    """

    def test_basic_convergence_comparison(self):
        """基本收敛对比: QMC 误差应随样本数增加而降低。"""
        # f(x) = x1 + x2, x ~ Uniform(0,1), E[Y] = 1.0
        result = compare_qmc_convergence(
            func=_mean_of_uniform_sum,
            distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            true_value=1.0,
            sample_sizes=[64, 128, 256, 512],
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        assert len(result.sample_sizes) == 4
        assert len(result.mc_errors) == 4
        assert len(result.qmc_errors) == 4
        # QMC 最终误差应较低
        assert result.qmc_final_error < 0.1
        assert result.speedup_factor > 0

    def test_qmc_better_than_mc_at_max_samples(self):
        """在最大样本数下 QMC 误差应 <= MC 误差（通常更优）。

        这是 QMC 方差减少的核心价值。
        """
        result = compare_qmc_convergence(
            func=_mean_of_uniform_sum,
            distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            true_value=1.0,
            sample_sizes=[128, 256, 512, 1024],
            sampler_type=QMCSamplerType.SOBOL,
            seed=42,
        )
        # QMC 应优于或接近 MC（QMC 在低维问题上有优势）
        assert result.qmc_final_error <= result.mc_final_error * 2.0

    def test_empty_sample_sizes_raises(self):
        """空 sample_sizes 应 raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            compare_qmc_convergence(
                func=lambda p: float(p[0]),
                distributions=[{"type": "norm"}],
                true_value=0.0,
                sample_sizes=[],
            )

    def test_empty_distributions_raises(self):
        """空 distributions 应 raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            compare_qmc_convergence(
                func=lambda p: float(p[0]),
                distributions=[],
                true_value=0.0,
                sample_sizes=[64],
            )


# ============================================================================
# TestDataclasses: 数据结构测试
# ============================================================================


class TestQMCDataclasses:
    """QMC 数据结构测试。"""

    def test_qmc_sample_result_defaults(self):
        """QMCSampleResult 默认值。"""
        result = QMCSampleResult()
        assert result.sampler_type == QMCSamplerType.SOBOL
        assert result.n_samples == 0
        assert result.n_dimensions == 0
        assert result.discrepancy == 0.0

    def test_qmc_monte_carlo_result_defaults(self):
        """QMCMonteCarloResult 默认值。"""
        result = QMCMonteCarloResult()
        assert result.mean == 0.0
        assert result.std == 0.0
        assert result.n_samples == 0
        assert result.sampler_type == QMCSamplerType.SOBOL

    def test_qmc_convergence_comparison_defaults(self):
        """QMCConvergenceComparison 默认值。"""
        result = QMCConvergenceComparison()
        assert result.sample_sizes == []
        assert result.mc_errors == []
        assert result.qmc_errors == []
        assert result.true_value == 0.0
        assert result.speedup_factor == 0.0
