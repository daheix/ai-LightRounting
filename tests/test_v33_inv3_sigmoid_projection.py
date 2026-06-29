"""v3.3-INV-3 回归测试：三层 sigmoid 投影公式修复验证。

Bug 编号: #v3.3-INV-3
严重级别: P1
问题: 三层 sigmoid 投影公式错误，拓扑优化中材料密度投影函数不正确
影响: 逆向设计结果不可靠，二值化效果差

本测试验证:
1. 标准 tanh-sigmoid 投影公式正确性
2. 边界条件: ρ=0 → 0, ρ=1 → 1
3. 输出范围: 投影后值在 [0, 1] 内
4. 单调性: 投影函数单调递增
5. β 陡度: β 越大投影越陡峭（二值化越强）
6. 三层（三点）投影: eroded/nominal/dilated 的相对关系
7. 参数验证: 非法参数应 raise（R03 禁止 fall-back）

文献来源（R02 学术诚信）:
1. Sigmund 2001: https://doi.org/10.1007/s00158-005-0543-x
2. Bendsøe & Sigmund 2003: Topology Optimization (Springer)
3. Wang, Lazarov & Sigmund 2011: https://doi.org/10.1007/s00158-010-0602-y
4. Bourdin 2001: https://doi.org/10.1002/nme.116
5. Jensen & Sigmund 2011: https://doi.org/10.1364/OE.19.020152
6. Guest et al 2004: https://doi.org/10.1002/nme.901

合规: R03 失败即 raise，禁止假数据；R04 纯 CPU。
"""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("JAX_PLATFORMS", "cpu")

from polaris.inverse.topology_adjoint_optimizer import (  # noqa: E402
    ModeOverlapObjective,
    OptimizerConfig,
    TopologyAdjointOptimizer,
)


def _make_optimizer(h: int = 8, w: int = 12) -> TopologyAdjointOptimizer:
    """构造测试用优化器。"""
    sigma = 1.5
    x = np.arange(w) - (w - 1) / 2.0
    e_in = np.exp(-(x**2) / (2 * sigma**2)).astype(np.complex64)
    e_in = e_in / np.sqrt(np.sum(np.abs(e_in) ** 2))
    e_target = e_in.copy()
    objective = ModeOverlapObjective(e_in, e_target)
    config = OptimizerConfig()
    return TopologyAdjointOptimizer(config, objective, design_shape=(h, w))


class TestDensityProjectionBoundary:
    """投影函数边界条件测试（核心 Bug 验证）。"""

    def test_rho_zero_maps_to_zero(self) -> None:
        """ρ=0 时投影结果应为 0（标准投影必要性质）。"""
        opt = _make_optimizer()
        rho = np.array([0.0])
        result = opt.density_projection(rho, beta=10.0, eta=0.5)
        assert result[0] == pytest.approx(0.0, abs=1e-10), (
            f"ρ=0 应投影为 0，实际 {result[0]}"
        )

    def test_rho_one_maps_to_one(self) -> None:
        """ρ=1 时投影结果应为 1（标准投影必要性质）。"""
        opt = _make_optimizer()
        rho = np.array([1.0])
        result = opt.density_projection(rho, beta=10.0, eta=0.5)
        assert result[0] == pytest.approx(1.0, abs=1e-10), (
            f"ρ=1 应投影为 1，实际 {result[0]}"
        )

    def test_rho_eta_maps_to_half(self) -> None:
        """ρ=η 时投影结果应为 0.5（对称中心点）。"""
        opt = _make_optimizer()
        eta = 0.5
        rho = np.array([eta])
        result = opt.density_projection(rho, beta=10.0, eta=eta)
        assert result[0] == pytest.approx(0.5, abs=1e-10), (
            f"ρ=η 应投影为 0.5，实际 {result[0]}"
        )

    def test_output_within_unit_interval(self) -> None:
        """投影结果应始终在 [0, 1] 范围内。"""
        opt = _make_optimizer()
        np.random.seed(42)
        rho = np.random.rand(100)
        for beta in [1.0, 5.0, 10.0, 50.0]:
            result = opt.density_projection(rho, beta=beta, eta=0.5)
            assert np.all(result >= 0.0), f"beta={beta} 时存在 <0 的值"
            assert np.all(result <= 1.0), f"beta={beta} 时存在 >1 的值"

    def test_output_within_unit_interval_for_valid_input(self) -> None:
        """输入 ρ ∈ [0,1] 时投影结果应在 [0,1] 范围内。"""
        opt = _make_optimizer()
        rho = np.linspace(0.0, 1.0, 1000)
        for beta in [1.0, 5.0, 10.0, 50.0, 100.0]:
            result = opt.density_projection(rho, beta=beta, eta=0.5)
            assert np.all(result >= -1e-12), f"beta={beta} 时存在 <0 的值"
            assert np.all(result <= 1.0 + 1e-12), f"beta={beta} 时存在 >1 的值"


class TestDensityProjectionMonotonicity:
    """投影函数单调性测试。"""

    def test_monotonically_increasing(self) -> None:
        """投影函数应单调非递减。"""
        opt = _make_optimizer()
        rho = np.linspace(0.0, 1.0, 1000)
        for beta in [0.5, 1.0, 5.0, 10.0, 50.0, 100.0]:
            result = opt.density_projection(rho, beta=beta, eta=0.5)
            diffs = np.diff(result)
            assert np.all(diffs >= -1e-12), f"beta={beta} 时投影非单调递增"

    def test_different_eta_monotonic(self) -> None:
        """不同 η 值下投影均应单调。"""
        opt = _make_optimizer()
        rho = np.linspace(0.0, 1.0, 500)
        for eta in [0.3, 0.4, 0.5, 0.6, 0.7]:
            result = opt.density_projection(rho, beta=5.0, eta=eta)
            diffs = np.diff(result)
            assert np.all(diffs > 0), f"eta={eta} 时投影非严格递增"


class TestDensityProjectionBetaSteepness:
    """β 陡度特性测试（二值化强度）。"""

    def test_larger_beta_steeper(self) -> None:
        """β 越大，投影在 η 附近越陡峭。"""
        opt = _make_optimizer()
        eta = 0.5
        delta = 0.05
        rho = np.array([eta - delta, eta + delta])

        steepness_values = []
        for beta in [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]:
            result = opt.density_projection(rho, beta=beta, eta=eta)
            steepness = (result[1] - result[0]) / (2 * delta)
            steepness_values.append(steepness)

        for i in range(len(steepness_values) - 1):
            assert steepness_values[i + 1] > steepness_values[i], (
                f"β 增大时陡度应递增，beta={[1,2,5,10,20,50][i]} -> "
                f"{[1,2,5,10,20,50][i+1]}: {steepness_values[i]} -> {steepness_values[i+1]}"
            )

    def test_large_beta_approaches_heaviside(self) -> None:
        """β→∞ 时投影趋近于 Heaviside 阶跃函数（二值化）。"""
        opt = _make_optimizer()
        eta = 0.5
        beta = 100.0
        delta = 0.05
        rho = np.array([0.0, eta - delta, eta, eta + delta, 1.0])
        result = opt.density_projection(rho, beta=beta, eta=eta)

        assert result[0] < 1e-6, "ρ=0 时应趋近于 0"
        assert result[1] < 0.1, "ρ=η-δ 时应远小于 0.5"
        assert result[2] == pytest.approx(0.5, abs=1e-6), "ρ=η 时应为 0.5"
        assert result[3] > 0.9, "ρ=η+δ 时应远大于 0.5"
        assert result[4] > 1 - 1e-6, "ρ=1 时应趋近于 1"

    def test_small_beta_close_to_linear(self) -> None:
        """β→0 时投影应趋近于线性函数。"""
        opt = _make_optimizer()
        eta = 0.5
        rho = np.linspace(0.0, 1.0, 100)
        result = opt.density_projection(rho, beta=0.1, eta=eta)

        corr = np.corrcoef(rho, result)[0, 1]
        assert corr > 0.99, f"β 很小时应接近线性，相关系数 {corr}"


class TestDensityProjectionEta:
    """η 阈值参数测试。"""

    def test_eta_shifts_threshold(self) -> None:
        """η 增大时，投影=0.5 的阈值点应向 ρ 增大方向移动。"""
        opt = _make_optimizer()
        beta = 20.0
        rho_values = np.linspace(0.0, 1.0, 10000)

        thresholds = []
        for eta in [0.3, 0.4, 0.5, 0.6, 0.7]:
            result = opt.density_projection(rho_values, beta=beta, eta=eta)
            idx = np.argmin(np.abs(result - 0.5))
            threshold_rho = rho_values[idx]
            thresholds.append(threshold_rho)

        for i in range(len(thresholds) - 1):
            assert thresholds[i + 1] > thresholds[i], (
                f"η 增大时阈值应右移"
            )

    def test_larger_eta_more_eroded(self) -> None:
        """η 越大，投影结果越小（侵蚀效应）。"""
        opt = _make_optimizer()
        beta = 10.0
        rho_mid = np.array([0.5])

        results = []
        for eta in [0.3, 0.4, 0.5, 0.6, 0.7]:
            result = opt.density_projection(rho_mid, beta=beta, eta=eta)
            results.append(result[0])

        for i in range(len(results) - 1):
            assert results[i + 1] < results[i], (
                f"η 增大时投影值应递减"
            )


class TestThreeLayerProjection:
    """三层（三点）投影测试（Wang 2011 robust formulation）。"""

    def test_returns_three_projections(self) -> None:
        """应返回 eroded/nominal/dilated 三个投影。"""
        opt = _make_optimizer()
        rho = np.random.rand(8, 12)
        result = opt.three_layer_projection(rho, beta=10.0)
        assert "eroded" in result
        assert "nominal" in result
        assert "dilated" in result

    def test_eroded_less_than_nominal(self) -> None:
        """侵蚀投影应 ≤ 名义投影（材料更少）。"""
        opt = _make_optimizer()
        rho = np.random.rand(100)
        result = opt.three_layer_projection(rho, beta=10.0, eta_nominal=0.5, eta_shift=0.2)
        assert np.all(result["eroded"] <= result["nominal"] + 1e-12)

    def test_nominal_less_than_dilated(self) -> None:
        """名义投影应 ≤ 膨胀投影（材料更少）。"""
        opt = _make_optimizer()
        rho = np.random.rand(100)
        result = opt.three_layer_projection(rho, beta=10.0, eta_nominal=0.5, eta_shift=0.2)
        assert np.all(result["nominal"] <= result["dilated"] + 1e-12)

    def test_eroded_dilated_ordering(self) -> None:
        """三者关系: eroded ≤ nominal ≤ dilated。"""
        opt = _make_optimizer()
        rho = np.linspace(0.0, 1.0, 1000)
        result = opt.three_layer_projection(rho, beta=10.0, eta_nominal=0.5, eta_shift=0.2)
        assert np.all(result["eroded"] <= result["nominal"] + 1e-12)
        assert np.all(result["nominal"] <= result["dilated"] + 1e-12)

    def test_all_within_unit_interval(self) -> None:
        """三层投影结果都应在 [0, 1] 内。"""
        opt = _make_optimizer()
        rho = np.random.rand(50, 50)
        result = opt.three_layer_projection(rho, beta=10.0)
        for key in ["eroded", "nominal", "dilated"]:
            assert np.all(result[key] >= 0.0), f"{key} 存在 <0 的值"
            assert np.all(result[key] <= 1.0), f"{key} 存在 >1 的值"


class TestProjectionParameterValidation:
    """参数验证测试（R03 禁止 fall-back）。"""

    def test_beta_zero_raises(self) -> None:
        """beta=0 应 raise ValueError。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError, match="beta"):
            opt.density_projection(rho, beta=0.0)

    def test_beta_negative_raises(self) -> None:
        """beta<0 应 raise ValueError。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError, match="beta"):
            opt.density_projection(rho, beta=-1.0)

    def test_eta_zero_raises(self) -> None:
        """eta=0 应 raise ValueError。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError, match="eta"):
            opt.density_projection(rho, beta=1.0, eta=0.0)

    def test_eta_one_raises(self) -> None:
        """eta=1 应 raise ValueError。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError, match="eta"):
            opt.density_projection(rho, beta=1.0, eta=1.0)

    def test_three_layer_eta_shift_too_large_raises(self) -> None:
        """三层投影 eta_shift 过大导致超出边界应 raise。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError):
            opt.three_layer_projection(rho, beta=1.0, eta_nominal=0.5, eta_shift=0.6)

    def test_three_layer_eta_shift_zero_raises(self) -> None:
        """三层投影 eta_shift=0 应 raise。"""
        opt = _make_optimizer()
        rho = np.array([0.5])
        with pytest.raises(ValueError, match="eta_shift"):
            opt.three_layer_projection(rho, beta=1.0, eta_nominal=0.5, eta_shift=0.0)


class TestProjectionSymmetry:
    """投影函数对称性测试。"""

    def test_symmetry_around_eta(self) -> None:
        """关于 η 对称: proj(η + δ) + proj(η - δ) = 1。"""
        opt = _make_optimizer()
        eta = 0.5
        deltas = [0.05, 0.1, 0.2, 0.3, 0.4]
        for beta in [1.0, 5.0, 10.0]:
            for delta in deltas:
                rho_plus = np.array([eta + delta])
                rho_minus = np.array([eta - delta])
                p_plus = opt.density_projection(rho_plus, beta=beta, eta=eta)
                p_minus = opt.density_projection(rho_minus, beta=beta, eta=eta)
                assert p_plus[0] + p_minus[0] == pytest.approx(1.0, abs=1e-10), (
                    f"beta={beta}, delta={delta}: {p_plus[0]} + {p_minus[0]} != 1"
                )


class TestProjectionArrayInput:
    """数组输入兼容性测试。"""

    def test_1d_array(self) -> None:
        """1D 数组输入应正常工作。"""
        opt = _make_optimizer()
        rho = np.linspace(0, 1, 100)
        result = opt.density_projection(rho, beta=5.0)
        assert result.shape == rho.shape
        assert np.all(np.isfinite(result))

    def test_2d_array(self) -> None:
        """2D 数组输入应正常工作。"""
        opt = _make_optimizer()
        rho = np.random.rand(20, 30)
        result = opt.density_projection(rho, beta=5.0)
        assert result.shape == rho.shape
        assert np.all(np.isfinite(result))

    def test_scalar_input(self) -> None:
        """标量输入应返回标量结果。"""
        opt = _make_optimizer()
        result = opt.density_projection(0.5, beta=5.0)
        assert np.ndim(result) == 0 or result.shape == ()
        assert np.isfinite(float(result))


class TestProjectionJaxConsistency:
    """JAX 版本与 NumPy 版本投影一致性测试。"""

    def test_jax_matches_numpy(self) -> None:
        """JAX 密度链中的投影应与 NumPy 版本一致。"""
        import jax
        import jax.numpy as jnp

        opt = _make_optimizer()
        np.random.seed(42)

        h, w = 8, 12
        rho_raw = np.random.randn(h, w) * 2.0

        beta = 10.0
        rho_sigmoid = 1.0 / (1.0 + np.exp(-rho_raw))
        rho_f = opt.conic_filter(rho_sigmoid)
        expected = opt.density_projection(rho_f, beta=beta, eta=opt.config.eta)

        rho_p_jax = opt._density_chain_jax(jnp.asarray(rho_raw), beta)
        actual = np.asarray(rho_p_jax)

        np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
