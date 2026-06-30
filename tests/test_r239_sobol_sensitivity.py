"""R239 Sobol 全局灵敏度分析测试。

验证 ``sobol_sensitivity_analysis()`` 的一阶/总效应 Sobol 指数计算、
参数交互效应识别、灵敏度排序功能。

测试用例对标 R239 验收标准:
- TR-239.1: 一阶灵敏度计算
- TR-239.2: 总灵敏度计算
- TR-239.3: 灵敏度排序正确

学术依据:
- Sobol 2001, DOI: 10.1007/BF02304730
- Saltelli et al. 2010, DOI: 10.1016/j.cpc.2009.09.018
- Ishigami & Homma 1990 (Ishigami 函数, 灵敏度分析基准)
  https://www.sciencedirect.com/science/article/pii/0377221790902908

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.monte_carlo import (
    SobolSensitivityResult,
    _build_distribution,
    _adapt_func_for_sobol,
    sobol_sensitivity_analysis,
)


# ============================================================================
# 解析解基准函数
# ============================================================================


def _linear_additive(x: np.ndarray) -> float:
    """线性可加模型 f(x) = x1 + 2*x2（无交互）。

    解析 Sobol 指数（x1, x2 独立标准正态）:
    - V(x1) = 1, V(2*x2) = 4, V(Y) = 5
    - S1 = 1/5 = 0.2, S2 = 4/5 = 0.8
    - S_T1 = S1 = 0.2, S_T2 = S2 = 0.8（无交互）
    """
    return float(x[0] + 2.0 * x[1])


def _multiplicative(x: np.ndarray) -> float:
    """乘积模型 f(x) = x1 * x2（纯交互）。

    解析 Sobol 指数（x1, x2 独立标准正态）:
    - E[Y] = 0, V(Y) = E[x1²]·E[x2²] = 1
    - S1 = 0, S2 = 0（一阶效应为 0）
    - S_T1 = S_T2 = 1（纯交互，总效应 = 1）
    - 交互效应 S_Ti - S_i = 1
    """
    return float(x[0] * x[1])


def _irrelevant_param(x: np.ndarray) -> float:
    """含无关参数模型 f(x) = x1（x2 无影响）。

    解析 Sobol 指数:
    - S1 = 1, S2 = 0
    - S_T1 = 1, S_T2 = 0
    """
    return float(x[0])


def _ishigami(x: np.ndarray) -> float:
    """Ishigami 函数（灵敏度分析经典基准）。

    f(x) = sin(x1) + a·sin(x2)² + b·x3⁴·sin(x1)

    参数: x1, x2, x3 ~ Uniform(-π, π), a=7, b=0.1

    解析 Sobol 指数（Saltelli 2010, Sobol 2001）:
    - S1 ≈ 0.3079 (主效应，含 x3 交互)
    - S2 ≈ 0.4424 (纯二阶效应)
    - S3 = 0 (x3 单独无影响，但与 x1 强交互)
    - S_T1 ≈ 0.5574, S_T2 ≈ 0.4424, S_T3 ≈ 0.2437

    来源: Ishigami & Homma 1990, Reliab. Eng. Syst. Saf.
    """
    a = 7.0
    b = 0.1
    return float(np.sin(x[0]) + a * np.sin(x[1]) ** 2 + b * x[2] ** 4 * np.sin(x[0]))


# ============================================================================
# TestSobolSensitivityResultDataclass: 数据结构测试
# ============================================================================


class TestSobolSensitivityResultDataclass:
    """SobolSensitivityResult dataclass 测试。"""

    def test_default_values(self):
        """默认值测试。"""
        result = SobolSensitivityResult()
        assert result.first_order == {}
        assert result.total_order == {}
        assert result.n_evaluations == 0
        assert result.param_names == []
        assert result.n_samples == 0

    def test_interaction_effects_property(self):
        """交互效应属性 = 总效应 - 一阶效应。"""
        result = SobolSensitivityResult(
            first_order={"a": 0.2, "b": 0.5},
            total_order={"a": 0.3, "b": 0.5},
            param_names=["a", "b"],
        )
        interactions = result.interaction_effects
        assert interactions["a"] == pytest.approx(0.1)
        assert interactions["b"] == pytest.approx(0.0)

    def test_rank_by_first_order(self):
        """按一阶指数降序排序。"""
        result = SobolSensitivityResult(
            first_order={"a": 0.2, "b": 0.8, "c": 0.5},
            total_order={"a": 0.2, "b": 0.8, "c": 0.5},
            param_names=["a", "b", "c"],
        )
        ranked = result.rank_by_first_order()
        assert ranked[0][0] == "b"
        assert ranked[1][0] == "c"
        assert ranked[2][0] == "a"

    def test_rank_by_total_order(self):
        """按总效应指数降序排序。"""
        result = SobolSensitivityResult(
            first_order={"a": 0.1, "b": 0.1, "c": 0.1},
            total_order={"a": 0.3, "b": 0.9, "c": 0.5},
            param_names=["a", "b", "c"],
        )
        ranked = result.rank_by_total_order()
        assert ranked[0][0] == "b"
        assert ranked[1][0] == "c"
        assert ranked[2][0] == "a"


# ============================================================================
# TestBuildDistribution: 分布构建测试
# ============================================================================


class TestBuildDistribution:
    """_build_distribution 辅助函数测试。"""

    def test_norm_distribution(self):
        """正态分布构建。"""
        dist = _build_distribution({"type": "norm", "loc": 1.0, "scale": 2.0})
        # ppf(0.5) 应等于 loc（中位数）
        assert dist.ppf(0.5) == pytest.approx(1.0)

    def test_uniform_distribution(self):
        """均匀分布构建。"""
        dist = _build_distribution({"type": "uniform", "loc": 0.0, "scale": 10.0})
        # ppf(0.5) 应等于 loc + scale/2 = 5.0
        assert dist.ppf(0.5) == pytest.approx(5.0)

    def test_default_loc_scale(self):
        """默认 loc/scale 值。"""
        norm_dist = _build_distribution({"type": "norm"})
        assert norm_dist.ppf(0.5) == pytest.approx(0.0)
        uniform_dist = _build_distribution({"type": "uniform"})
        assert uniform_dist.ppf(0.5) == pytest.approx(0.5)

    def test_unsupported_type_raises(self):
        """不支持的分布类型应 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="不支持的分布类型"):
            _build_distribution({"type": "exponential"})


# ============================================================================
# TestAdaptFuncForSobol: 函数适配器测试
# ============================================================================


class TestAdaptFuncForSobol:
    """_adapt_func_for_sobol 适配器测试。"""

    def test_batch_evaluation(self):
        """批量评估适配。"""
        # 标量函数 f(x) = x0 + x1
        scalar_func = lambda p: float(p[0] + p[1])  # noqa: E731
        batch_func = _adapt_func_for_sobol(scalar_func)
        # x shape (2, 3): 3 个样本，每个 2 维
        x = np.array([[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]])
        out = batch_func(x)
        assert out.shape == (3,)
        assert out[0] == pytest.approx(11.0)
        assert out[1] == pytest.approx(22.0)
        assert out[2] == pytest.approx(33.0)


# ============================================================================
# TestSobolLinearAdditive: 线性可加模型测试（TR-239.1 + TR-239.2）
# ============================================================================


class TestSobolLinearAdditive:
    """线性可加模型 f(x) = x1 + 2*x2 的 Sobol 指数验证。

    解析解: S1=0.2, S2=0.8, S_T1=0.2, S_T2=0.8（无交互）
    """

    def test_first_order_indices(self):
        """TR-239.1: 一阶 Sobol 指数与解析解误差 < 0.05。"""
        result = sobol_sensitivity_analysis(
            func=_linear_additive,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # S1 = 0.2, S2 = 0.8
        assert result.first_order["x1"] == pytest.approx(0.2, abs=0.05)
        assert result.first_order["x2"] == pytest.approx(0.8, abs=0.05)

    def test_total_order_indices(self):
        """TR-239.2: 总效应 Sobol 指数与解析解误差 < 0.05。"""
        result = sobol_sensitivity_analysis(
            func=_linear_additive,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # 无交互: S_T1 = S1 = 0.2, S_T2 = S2 = 0.8
        assert result.total_order["x1"] == pytest.approx(0.2, abs=0.05)
        assert result.total_order["x2"] == pytest.approx(0.8, abs=0.05)

    def test_no_interaction_for_additive(self):
        """线性可加模型无交互效应: S_Ti - S_i ≈ 0。"""
        result = sobol_sensitivity_analysis(
            func=_linear_additive,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        interactions = result.interaction_effects
        assert abs(interactions["x1"]) < 0.05
        assert abs(interactions["x2"]) < 0.05

    def test_ranking(self):
        """TR-239.3: 灵敏度排序 x2 > x1。"""
        result = sobol_sensitivity_analysis(
            func=_linear_additive,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        ranked = result.rank_by_total_order()
        assert ranked[0][0] == "x2"
        assert ranked[1][0] == "x1"

    def test_n_evaluations(self):
        """总评估次数 = N(k+2) = 1024*(2+2) = 4096。"""
        result = sobol_sensitivity_analysis(
            func=_linear_additive,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        assert result.n_evaluations == 4096
        assert result.n_samples == 1024


# ============================================================================
# TestSobolMultiplicative: 乘积模型测试（交互效应识别）
# ============================================================================


class TestSobolMultiplicative:
    """乘积模型 f(x) = x1 * x2 的 Sobol 指数验证。

    解析解: S1=0, S2=0, S_T1=1, S_T2=1（纯交互）
    """

    def test_first_order_zero(self):
        """纯交互模型一阶指数 ≈ 0。"""
        result = sobol_sensitivity_analysis(
            func=_multiplicative,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=2048,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # 一阶效应 ≈ 0（纯交互）
        assert abs(result.first_order["x1"]) < 0.1
        assert abs(result.first_order["x2"]) < 0.1

    def test_total_order_high(self):
        """纯交互模型总效应 ≈ 1。"""
        result = sobol_sensitivity_analysis(
            func=_multiplicative,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=2048,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # 总效应接近 1（纯交互）
        assert result.total_order["x1"] == pytest.approx(1.0, abs=0.15)
        assert result.total_order["x2"] == pytest.approx(1.0, abs=0.15)

    def test_interaction_effect_detected(self):
        """交互效应 S_T - S 应显著 > 0（识别参数交互）。"""
        result = sobol_sensitivity_analysis(
            func=_multiplicative,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=2048,
            param_names=["x1", "x2"],
            random_state=42,
        )
        interactions = result.interaction_effects
        # 交互效应应显著 > 0（这是 Sobol 全局灵敏度优于一阶摄动法的核心价值）
        assert interactions["x1"] > 0.5
        assert interactions["x2"] > 0.5


# ============================================================================
# TestSobolIrrelevantParam: 无关参数测试
# ============================================================================


class TestSobolIrrelevantParam:
    """含无关参数模型 f(x) = x1 的 Sobol 指数验证。

    解析解: S1=1, S2=0, S_T1=1, S_T2=0
    """

    def test_irrelevant_param_zero_indices(self):
        """无关参数的 S_i 和 S_Ti 都应 ≈ 0。"""
        result = sobol_sensitivity_analysis(
            func=_irrelevant_param,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # x2 无影响: S2 ≈ 0, S_T2 ≈ 0
        assert abs(result.first_order["x2"]) < 0.05
        assert abs(result.total_order["x2"]) < 0.05

    def test_dominant_param_full_effect(self):
        """主导参数 S1 ≈ 1, S_T1 ≈ 1。"""
        result = sobol_sensitivity_analysis(
            func=_irrelevant_param,
            param_distributions=[
                {"type": "norm", "loc": 0.0, "scale": 1.0},
                {"type": "norm", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        assert result.first_order["x1"] == pytest.approx(1.0, abs=0.05)
        assert result.total_order["x1"] == pytest.approx(1.0, abs=0.05)


# ============================================================================
# TestSobolIshigami: Ishigami 基准函数测试
# ============================================================================


class TestSobolIshigami:
    """Ishigami 函数测试（灵敏度分析经典基准）。

    解析解 (Saltelli 2010, Sobol 2001):
    - S1 ≈ 0.3079, S2 ≈ 0.4424, S3 = 0
    - S_T1 ≈ 0.5574, S_T2 ≈ 0.4424, S_T3 ≈ 0.2437

    来源: Ishigami & Homma 1990
    """

    @pytest.fixture
    def ishigami_result(self):
        """Ishigami 函数 Sobol 分析结果（n=4096 提高精度）。"""
        return sobol_sensitivity_analysis(
            func=_ishigami,
            param_distributions=[
                {"type": "uniform", "loc": -np.pi, "scale": 2 * np.pi},
                {"type": "uniform", "loc": -np.pi, "scale": 2 * np.pi},
                {"type": "uniform", "loc": -np.pi, "scale": 2 * np.pi},
            ],
            n_samples=4096,
            param_names=["x1", "x2", "x3"],
            random_state=42,
        )

    def test_x3_first_order_zero(self, ishigami_result):
        """x3 一阶效应 ≈ 0（x3 单独无影响）。"""
        # S3 = 0（解析解）
        assert abs(ishigami_result.first_order["x3"]) < 0.05

    def test_x3_total_order_nonzero(self, ishigami_result):
        """x3 总效应 > 0（x3 与 x1 强交互）。

        这是 Sobol 全局灵敏度分析的核心价值: 一阶摄动法会误判 x3 无影响，
        而 Sobol 总效应正确识别 x3 通过交互影响输出。
        """
        # S_T3 ≈ 0.2437（解析解）
        assert ishigami_result.total_order["x3"] > 0.1

    def test_x1_total_greater_than_first(self, ishigami_result):
        """x1 总效应 > 一阶效应（x1 与 x3 交互）。"""
        # S_T1 ≈ 0.5574 > S1 ≈ 0.3079
        assert ishigami_result.total_order["x1"] > ishigami_result.first_order["x1"]

    def test_x2_first_and_total_equal(self, ishigami_result):
        """x2 一阶 ≈ 总效应（x2 无交互）。"""
        # S2 ≈ S_T2 ≈ 0.4424
        diff = abs(ishigami_result.total_order["x2"] - ishigami_result.first_order["x2"])
        assert diff < 0.1

    def test_ranking_x2_dominant(self, ishigami_result):
        """TR-239.3: x2 一阶效应最大。"""
        ranked = ishigami_result.rank_by_first_order()
        assert ranked[0][0] == "x2"


# ============================================================================
# TestSobolInputValidation: 输入验证测试（R03 禁止 fall-back）
# ============================================================================


class TestSobolInputValidation:
    """输入参数验证测试。"""

    def test_empty_distributions_raises(self):
        """空分布列表应 raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0]),
                param_distributions=[],
                n_samples=1024,
            )

    def test_non_power_of_two_samples_raises(self):
        """n_samples 非 2 的幂应 raise（R03）。"""
        with pytest.raises(ValueError, match="2 的幂"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0]),
                param_distributions=[{"type": "norm"}],
                n_samples=1000,  # 非 2 的幂
            )

    def test_zero_samples_raises(self):
        """n_samples=0 应 raise。"""
        with pytest.raises(ValueError, match="2 的幂"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0]),
                param_distributions=[{"type": "norm"}],
                n_samples=0,
            )

    def test_negative_samples_raises(self):
        """负 n_samples 应 raise。"""
        with pytest.raises(ValueError, match="2 的幂"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0]),
                param_distributions=[{"type": "norm"}],
                n_samples=-512,
            )

    def test_param_names_length_mismatch_raises(self):
        """param_names 长度不匹配应 raise。"""
        with pytest.raises(ValueError, match="不匹配"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0] + p[1]),
                param_distributions=[
                    {"type": "norm"},
                    {"type": "norm"},
                ],
                n_samples=1024,
                param_names=["only_one"],  # 应该 2 个
            )

    def test_invalid_distribution_type_raises(self):
        """无效分布类型应 raise（R03）。"""
        with pytest.raises(ValueError, match="不支持的分布类型"):
            sobol_sensitivity_analysis(
                func=lambda p: float(p[0]),
                param_distributions=[{"type": "unknown"}],
                n_samples=1024,
            )


# ============================================================================
# TestSobolDefaultParamNames: 默认参数名测试
# ============================================================================


class TestSobolDefaultParamNames:
    """默认参数名生成测试。"""

    def test_default_param_names(self):
        """未提供 param_names 时自动生成 param_0, param_1, ..."""
        result = sobol_sensitivity_analysis(
            func=lambda p: float(p[0] + p[1]),
            param_distributions=[
                {"type": "norm"},
                {"type": "norm"},
            ],
            n_samples=512,
            random_state=42,
        )
        assert result.param_names == ["param_0", "param_1"]
        assert "param_0" in result.first_order
        assert "param_1" in result.first_order


# ============================================================================
# TestSobolReproducibility: 可复现性测试
# ============================================================================


class TestSobolReproducibility:
    """随机种子可复现性测试。"""

    def test_same_seed_same_result(self):
        """相同 random_state 应产生相同结果。"""
        kwargs = dict(
            func=_linear_additive,
            param_distributions=[{"type": "norm"}, {"type": "norm"}],
            n_samples=512,
            param_names=["x1", "x2"],
            random_state=123,
        )
        r1 = sobol_sensitivity_analysis(**kwargs)
        r2 = sobol_sensitivity_analysis(**kwargs)
        assert r1.first_order["x1"] == pytest.approx(r2.first_order["x1"])
        assert r1.total_order["x2"] == pytest.approx(r2.total_order["x2"])

    def test_uniform_distribution_supported(self):
        """均匀分布支持测试。"""
        # f(x) = x1（均匀分布），x2 无影响
        result = sobol_sensitivity_analysis(
            func=lambda p: float(p[0]),
            param_distributions=[
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
                {"type": "uniform", "loc": 0.0, "scale": 1.0},
            ],
            n_samples=1024,
            param_names=["x1", "x2"],
            random_state=42,
        )
        # x1 主导
        assert result.first_order["x1"] > 0.9
        assert abs(result.first_order["x2"]) < 0.05
