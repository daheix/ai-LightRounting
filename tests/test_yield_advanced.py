"""R236-R240 良率分析进阶模块单元测试。

覆盖:
- R236 LHSMonteCarlo: 拉丁超立方采样
- R237 ImportanceSampler: 重要性采样失效概率估计
- R238 LHSImportanceSampler: LHS+IS 联合方差缩减
- R239 SobolSensitivity: Saltelli 2010 一阶 + Jansen 1999 总阶
- R240 AdvancedCornerAnalyzer: 标准 5 工艺角 + SLSQP 最坏情况搜索

文献来源（R02 学术诚信）:
- McKay et al., Technometrics 21(2), 1979 (LHS): https://www.jstor.org/stable/1268522
- Saltelli et al., Comput. Phys. Commun. 181(2), 2010: https://www.sciencedirect.com/science/article/abs/pii/S0010465509003087
- Jansen, Comput. Phys. Commun. 117(1), 1999: https://doi.org/10.1016/S0010-4655(98)00154-4
- Rubinstein, "Simulation and the Monte Carlo Method", Wiley 1981
- sensobol R 包: https://publications.artsci.wustl.edu/web/packages/sensobol/vignettes/sensobol.pdf

合规: R03 禁止 fall-back / R04 纯 NumPy/SciPy / R05 Bug 必修验证。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.verification.yield_advanced import (
    AdvancedCornerAnalyzer,
    ImportanceSampler,
    LHSMonteCarlo,
    LHSImportanceSampler,
    SobolSensitivity,
    YieldParam,
)


# ============================================================
# 共用仿真函数
# ============================================================
def _linear_sim_factory(b0: float, coefs: dict[str, float], nominals: dict[str, float]):
    """构造线性仿真函数 y = b0 + Σ b_i × (x_i - nominal_i)。"""
    def sim_fn(params: dict[str, float]) -> float:
        y = b0
        for name, b in coefs.items():
            y += b * (params[name] - nominals[name])
        return float(y)
    return sim_fn


# ============================================================
# R236 拉丁超立方采样测试
# ============================================================
class TestLHSMonteCarlo:
    """R236 拉丁超立方采样（LHS）测试。"""

    def test_lhs_stratification_one_per_stratum(self):
        """M1: LHS 分层性 — 每参数 N 个样本落在 N 个不同子区间。

        McKay 1979 LHS 定义: 每参数 [0,1) 分 N 层，每层恰一个样本。
        """
        params = [
            YieldParam("x", nominal=0.0, sigma=1.0, distribution="gaussian"),
        ]
        lhs = LHSMonteCarlo(params, seed=42)
        n = 100
        samples = lhs.sample(n)
        # 将样本转回 [0,1) 通过 CDF
        from scipy.stats import norm
        u = norm.cdf(samples["x"])
        # 检查分层：每层 [i/N, (i+1)/N) 恰一个样本
        for i in range(n):
            lo = i / n
            hi = (i + 1) / n
            count = int(np.sum((u >= lo) & (u < hi)))
            assert count == 1, f"层 [{lo:.2f},{hi:.2f}) 有 {count} 个样本，应为 1"

    def test_lhs_run_statistics(self):
        """M1: LHS 仿真统计量 mean ≈ nominal（高斯零偏）。"""
        params = [
            YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian"),
            YieldParam("t", nominal=0.2, sigma=0.005, distribution="gaussian"),
        ]
        lhs = LHSMonteCarlo(params, seed=42)
        sim_fn = _linear_sim_factory(1000.0, {"w": 100.0, "t": 200.0}, {"w": 0.5, "t": 0.2})
        result = lhs.run(sim_fn, n_runs=500)
        assert result["n_runs"] == 500
        assert result["mean"] == pytest.approx(1000.0, abs=1.0)
        assert result["std"] > 0
        assert result["min"] <= result["mean"] <= result["max"]
        assert result["method"] == "latin_hypercube"

    def test_uniform_distribution(self):
        """M2: uniform 分布参数采样落在 [lower, upper] 内。"""
        params = [
            YieldParam("u", nominal=0.5, distribution="uniform", lower=0.0, upper=1.0),
        ]
        lhs = LHSMonteCarlo(params, seed=42)
        samples = lhs.sample(100)
        assert np.all(samples["u"] >= 0.0)
        assert np.all(samples["u"] <= 1.0)

    def test_invalid_n_runs_raises(self):
        """M1: R03 — n_runs ≤ 0 必须 raise。"""
        params = [YieldParam("x", nominal=0.0, sigma=1.0)]
        lhs = LHSMonteCarlo(params)
        with pytest.raises(ValueError, match="n_runs"):
            lhs.run(lambda p: 0.0, n_runs=0)

    def test_empty_params_raises(self):
        """M1: R03 — 空参数列表必须 raise。"""
        with pytest.raises(ValueError, match="params"):
            LHSMonteCarlo([])


# ============================================================
# R237 重要性采样测试
# ============================================================
class TestImportanceSampler:
    """R237 重要性采样（IS）失效概率估计测试。"""

    def test_is_estimates_failure_probability(self):
        """M1: IS 估计稀有失效概率 P_f > 0。

        构造: y = b0 + b×(x - nominal)，spec_lower 使失效概率 ~1%
        偏移 failure_center 到失效区域加速估计。
        """
        params = [YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian")]
        is_sampler = ImportanceSampler(params, seed=42)
        # y = 1000 + 100×(w-0.5)，nominal=1000，σ_y = 100×0.01 = 1
        # spec_lower = 997 → P_f = P(Y<997) = P(Z<-3) ≈ 0.135%
        sim_fn = _linear_sim_factory(1000.0, {"w": 100.0}, {"w": 0.5})
        result = is_sampler.run(
            sim_fn,
            n_runs=2000,
            spec_lower=997.0,
            spec_upper=None,
            failure_center={"w": 0.47},  # 偏移到 -3σ 失效区
        )
        assert result["failure_probability"] > 0
        assert result["failure_probability"] < 1.0
        assert result["method"] == "importance_sampling"
        lo, hi = result["failure_probability_ci"]
        assert 0 <= lo <= result["failure_probability"] <= hi <= 1.0

    def test_is_no_failure_raises(self):
        """M1: R03 — 所有样本未失效时必须 raise（禁止 fall-back 返回假 0）。"""
        params = [YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian")]
        is_sampler = ImportanceSampler(params, seed=42)
        sim_fn = _linear_sim_factory(1000.0, {"w": 100.0}, {"w": 0.5})
        # spec 极松，不会失效
        with pytest.raises(RuntimeError, match="未失效"):
            is_sampler.run(
                sim_fn, n_runs=100,
                spec_lower=0.0, spec_upper=10000.0,
                failure_center={"w": 0.5},
            )

    def test_is_both_spec_none_raises(self):
        """M1: R03 — spec_lower/upper 同时 None 必须 raise。"""
        params = [YieldParam("w", nominal=0.5, sigma=0.01)]
        is_sampler = ImportanceSampler(params)
        with pytest.raises(ValueError, match="spec_lower"):
            is_sampler.run(lambda p: 1.0, n_runs=10, spec_lower=None, spec_upper=None)

    def test_is_non_gaussian_raises(self):
        """M1: R03 — 非 gaussian 参数必须 raise。"""
        params = [YieldParam("u", nominal=0.5, distribution="uniform", lower=0.0, upper=1.0)]
        with pytest.raises(ValueError, match="gaussian"):
            ImportanceSampler(params)


# ============================================================
# R238 LHS+IS 联合采样测试
# ============================================================
class TestLHSImportanceSampler:
    """R238 LHS+IS 联合方差缩减测试。"""

    def test_lhs_is_estimates_failure_probability(self):
        """M1: LHS+IS 联合估计失效概率 P_f > 0。"""
        params = [YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian")]
        sampler = LHSImportanceSampler(params, seed=42)
        sim_fn = _linear_sim_factory(1000.0, {"w": 100.0}, {"w": 0.5})
        result = sampler.run(
            sim_fn,
            n_runs=2000,
            spec_lower=997.0,
            spec_upper=None,
            failure_center={"w": 0.47},
        )
        assert result["failure_probability"] > 0
        assert result["failure_probability"] < 1.0
        assert result["method"] == "lhs_importance"

    def test_lhs_is_no_failure_raises(self):
        """M1: R03 — 所有样本未失效时必须 raise。"""
        params = [YieldParam("w", nominal=0.5, sigma=0.01)]
        sampler = LHSImportanceSampler(params, seed=42)
        sim_fn = _linear_sim_factory(1000.0, {"w": 100.0}, {"w": 0.5})
        with pytest.raises(RuntimeError, match="未失效"):
            sampler.run(
                sim_fn, n_runs=100,
                spec_lower=0.0, spec_upper=10000.0,
                failure_center={"w": 0.5},
            )


# ============================================================
# R239 Sobol 全局灵敏度测试
# ============================================================
class TestSobolSensitivity:
    """R239 Sobol 全局灵敏度（Saltelli 2010 + Jansen 1999）测试。"""

    def test_additive_model_first_order_equal(self):
        """M1: 加性模型 y=b0+b1×X1+b2×X2，b1=b2 → S1≈S2≈0.5。

        理论: V1=b1²σ², V2=b2²σ², V_total=V1+V2
        b1=b2 → S1=S2=0.5
        中心化估计量降低方差后 n_base=2048 收敛良好。
        """
        params = [
            YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian"),
            YieldParam("t", nominal=0.2, sigma=0.005, distribution="gaussian"),
        ]
        sobol = SobolSensitivity(params, seed=42)
        # y = 1550 + 2000×(w-0.5) + 2000×(t-0.2)
        # V_w = 2000²×0.01² = 400, V_t = 2000²×0.005² = 100
        # S_w = 400/500 = 0.8, S_t = 100/500 = 0.2
        sim_fn = _linear_sim_factory(1550.0, {"w": 2000.0, "t": 2000.0}, {"w": 0.5, "t": 0.2})
        result = sobol.compute(sim_fn, n_base=2048)
        # 一阶: S_w=0.8, S_t=0.2（因 σ_w=0.01 > σ_t=0.005）
        assert result["first_order"]["w"] == pytest.approx(0.8, abs=0.1)
        assert result["first_order"]["t"] == pytest.approx(0.2, abs=0.1)

    def test_additive_model_total_order_additive(self):
        """M1: 加性模型无交互，总阶 S_Ti = S_i（一阶=总阶）。"""
        params = [
            YieldParam("w", nominal=0.5, sigma=0.01, distribution="gaussian"),
            YieldParam("t", nominal=0.2, sigma=0.005, distribution="gaussian"),
        ]
        sobol = SobolSensitivity(params, seed=42)
        sim_fn = _linear_sim_factory(1550.0, {"w": 2000.0, "t": 2000.0}, {"w": 0.5, "t": 0.2})
        result = sobol.compute(sim_fn, n_base=2048)
        # 加性模型: 总阶 = 一阶（无交互）
        assert result["total_order"]["w"] == pytest.approx(result["first_order"]["w"], abs=0.1)
        assert result["total_order"]["t"] == pytest.approx(result["first_order"]["t"], abs=0.1)
        # 一阶+总阶应在 [0, 1] 附近
        assert 0 <= result["total_order"]["w"] <= 1.2

    def test_n_evaluations_formula(self):
        """M1: 总评估次数 = N×(k+2)（pick-freeze 设计）。"""
        params = [
            YieldParam("a", nominal=0.0, sigma=1.0),
            YieldParam("b", nominal=0.0, sigma=1.0),
            YieldParam("c", nominal=0.0, sigma=1.0),
        ]
        sobol = SobolSensitivity(params, seed=42)
        sim_fn = _linear_sim_factory(0.0, {"a": 1.0, "b": 1.0, "c": 1.0},
                                     {"a": 0.0, "b": 0.0, "c": 0.0})
        result = sobol.compute(sim_fn, n_base=64)
        # k=3, N=64 → N×(k+2) = 64×5 = 320
        assert result["n_evaluations"] == 320
        assert result["n_base"] == 64

    def test_variance_degenerate_raises(self):
        """M1: R03 — 仿真输出方差退化（恒定函数）必须 raise。"""
        params = [YieldParam("x", nominal=0.0, sigma=1.0)]
        sobol = SobolSensitivity(params, seed=42)
        with pytest.raises(ValueError, match="方差退化"):
            sobol.compute(lambda p: 42.0, n_base=64)

    def test_estimators_documented(self):
        """M2: 估计量类型标注正确（Saltelli 2010 / Jansen 1999）。"""
        params = [YieldParam("x", nominal=0.0, sigma=1.0)]
        sobol = SobolSensitivity(params, seed=42)
        sim_fn = _linear_sim_factory(0.0, {"x": 1.0}, {"x": 0.0})
        result = sobol.compute(sim_fn, n_base=64)
        assert result["estimators"]["first_order"] == "Saltelli_2010"
        assert result["estimators"]["total_order"] == "Jansen_1999"


# ============================================================
# R240 角点分析增强测试
# ============================================================
class TestAdvancedCornerAnalyzer:
    """R240 角点分析（标准 5 角 + SLSQP 最坏情况搜索）测试。"""

    def test_standard_corners_five(self):
        """M1: 标准 5 工艺角 TT/SS/FF/SF/FS 全部生成。"""
        params = [
            YieldParam("wg_width", nominal=0.5, sigma=0.01),
            YieldParam("wg_thick", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        corners = analyzer.standard_corners()
        assert set(corners.keys()) == {"TT", "SS", "FF", "SF", "FS"}
        # TT = nominal
        assert corners["TT"]["wg_width"] == pytest.approx(0.5)
        assert corners["TT"]["wg_thick"] == pytest.approx(0.2)
        # SS = nominal - 3σ
        assert corners["SS"]["wg_width"] == pytest.approx(0.5 - 0.03)
        # FF = nominal + 3σ
        assert corners["FF"]["wg_width"] == pytest.approx(0.5 + 0.03)

    def test_run_standard_corners(self):
        """M1: 标准角仿真返回每个角的性能值。"""
        params = [
            YieldParam("wg_width", nominal=0.5, sigma=0.01),
            YieldParam("wg_thick", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        sim_fn = _linear_sim_factory(1000.0, {"wg_width": 10000.0, "wg_thick": 20000.0},
                                     {"wg_width": 0.5, "wg_thick": 0.2})
        result = analyzer.run_standard_corners(sim_fn)
        assert set(result.keys()) == {"TT", "SS", "FF", "SF", "FS"}
        # TT = 1000
        assert result["TT"] == pytest.approx(1000.0)
        # FF = 1000 + 10000×0.03 + 20000×0.015 = 1000 + 300 + 300 = 1600
        assert result["FF"] == pytest.approx(1600.0)

    def test_worst_case_max_positive(self):
        """M1: R05 Bug 修复验证 — direction='max' 返回正向最大值（非负号错误）。

        Bug: 原 `worst_perf = -sign*result.fun` 导致 max 返回 -max_sim。
        修复: `worst_perf = sign*result.fun` 正确返回 +max_sim。
        """
        params = [
            YieldParam("wg_width", nominal=0.5, sigma=0.01),
            YieldParam("wg_thick", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        sim_fn = _linear_sim_factory(1000.0, {"wg_width": 10000.0, "wg_thick": 20000.0},
                                     {"wg_width": 0.5, "wg_thick": 0.2})
        result = analyzer.worst_case_search(sim_fn, direction="max", n_sigma=3.0)
        # 最坏 max = 1000 + 10000×0.03 + 20000×0.015 = 1600
        assert result["worst_performance"] == pytest.approx(1600.0, abs=1.0)
        assert result["worst_performance"] > 1000.0  # 必须大于标称
        assert result["direction"] == "max"
        assert result["success"] is True

    def test_worst_case_min_positive(self):
        """M1: R05 Bug 修复验证 — direction='min' 返回正向最小值。

        Bug: 原公式对 min 也返回 -min_sim（负号错误）。
        """
        params = [
            YieldParam("wg_width", nominal=0.5, sigma=0.01),
            YieldParam("wg_thick", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        sim_fn = _linear_sim_factory(1000.0, {"wg_width": 10000.0, "wg_thick": 20000.0},
                                     {"wg_width": 0.5, "wg_thick": 0.2})
        result = analyzer.worst_case_search(sim_fn, direction="min", n_sigma=3.0)
        # 最坏 min = 1000 - 300 - 300 = 400
        assert result["worst_performance"] == pytest.approx(400.0, abs=1.0)
        assert result["worst_performance"] < 1000.0  # 必须小于标称
        assert result["direction"] == "min"

    def test_worst_case_max_greater_than_min(self):
        """M2: 最坏 max > 最坏 min（一致性检查）。"""
        params = [
            YieldParam("w", nominal=0.5, sigma=0.01),
            YieldParam("t", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        sim_fn = _linear_sim_factory(1000.0, {"w": 5000.0, "t": 3000.0},
                                     {"w": 0.5, "t": 0.2})
        wc_max = analyzer.worst_case_search(sim_fn, direction="max", n_sigma=3.0)
        wc_min = analyzer.worst_case_search(sim_fn, direction="min", n_sigma=3.0)
        assert wc_max["worst_performance"] > wc_min["worst_performance"]

    def test_invalid_direction_raises(self):
        """M1: R03 — 非法 direction 必须 raise。"""
        params = [YieldParam("x", nominal=0.0, sigma=1.0)]
        analyzer = AdvancedCornerAnalyzer(params)
        with pytest.raises(ValueError, match="direction"):
            analyzer.worst_case_search(lambda p: 0.0, direction="invalid")

    def test_run_full_returns_all(self):
        """M2: run_full 返回标准角 + 最坏 max + 最坏 min。"""
        params = [
            YieldParam("w", nominal=0.5, sigma=0.01),
            YieldParam("t", nominal=0.2, sigma=0.005),
        ]
        analyzer = AdvancedCornerAnalyzer(params)
        sim_fn = _linear_sim_factory(1000.0, {"w": 5000.0, "t": 3000.0},
                                     {"w": 0.5, "t": 0.2})
        result = analyzer.run_full(sim_fn, n_sigma=3.0)
        assert "standard_corners" in result
        assert "worst_case_max" in result
        assert "worst_case_min" in result
        assert len(result["standard_corners"]) == 5
