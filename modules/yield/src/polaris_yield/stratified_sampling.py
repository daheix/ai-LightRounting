"""分层采样 (Stratified Sampling) 方差减少技术（polaris-yield 子模块）。

从 v4 ``polaris.sim.stratified_sampling`` 迁移；R13 不保留 v4 兼容路径。

## 核心理论

设参数空间 Ω 划分为 H 层 {Ω₁, ..., Ω_H}，层权重 Wₕ = P(X ∈ Ωₕ)。
分层估计器::

    μ̂_strat = Σₕ Wₕ · μ̂ₕ,   μ̂ₕ = (1/nₕ) Σ_{i∈Ωₕ} g(Xᵢ)

方差::

    Var(μ̂_strat) = Σₕ Wₕ² · σₕ²/nₕ  ≤  Var(μ̂_MC) = σ²/n

## 分配策略

1. EQUAL (等额): nₕ = n/H
2. PROPORTIONAL (比例): nₕ = n·Wₕ
3. NEYMAN (最优): nₕ = n·Wₕ·σₕ/Σ(Wⱼ·σⱼ)（两阶段 pilot 估计 σ̂ₕ）

## 学术依据（R02 学术诚信，≥5 文献 URL）

- Cochran 1977, "Sampling Techniques", Wiley, 3rd ed.,
  https://www.wiley.com/en-us/Sampling+Techniques%2C+3rd+Edition-p-9780471162407
- Neyman 1934, "On the two different aspects of the representative
  method", JRSS, https://doi.org/10.2307/2342192
- McKay, Beckman & Conover 1979, Technometrics 21(2):239-245,
  https://doi.org/10.1080/00401706.1979.10489755
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer Ch.4, https://doi.org/10.1007/978-0-387-21617-1
- Stein 1987, "Large sample properties of simulations using Latin
  hypercube sampling", Technometrics 29(2):143-151,
  https://doi.org/10.2307/1269887
- SciPy stats: https://docs.scipy.org/doc/scipy/reference/stats.html

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.stats import norm, uniform

logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    """分层样本分配策略。

    对标商业工具:
    - Calibre YieldOptimizer: LHS（等价 EQUAL + 拉丁化）
    - Lumerical INTERCONNECT: Stratified MC（PROPORTIONAL）
    - Luceda Circuit Analyzer: NEYMAN 最优分配
    """

    EQUAL = "equal"
    PROPORTIONAL = "proportional"
    NEYMAN = "neyman"


@dataclass
class StratifiedSamplingResult:
    """分层采样估计结果。

    Attributes:
        estimate: 估计值 μ̂_strat = Σ Wₕ·μ̂ₕ。
        std_error: 标准误差 SE = sqrt(Σ Wₕ²·σₕ²/nₕ)。
        relative_error: 相对误差 RE = SE/|μ̂|。
        ci_lower: 95% 置信区间下界。
        ci_upper: 95% 置信区间上界。
        n_strata: 层数 H。
        n_samples: 总样本数 n。
        n_per_stratum: 每层样本数列表。
        strata_weights: 层权重列表。
        strata_means: 层内均值列表。
        strata_stds: 层内标准差列表。
        variance_estimate: 估计器方差（= SE²）。
        variance_naive_mc: 朴素 MC 方差对比（= σ²/n）。
        speedup_vs_mc: 加速比 = Var_MC / Var_strat。
        allocation_strategy: 分配策略名。
        n_evaluations: 总模型评估次数。
    """

    estimate: float = 0.0
    std_error: float = 0.0
    relative_error: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    n_strata: int = 0
    n_samples: int = 0
    n_per_stratum: list[int] = field(default_factory=list)
    strata_weights: list[float] = field(default_factory=list)
    strata_means: list[float] = field(default_factory=list)
    strata_stds: list[float] = field(default_factory=list)
    variance_estimate: float = 0.0
    variance_naive_mc: float = 0.0
    speedup_vs_mc: float = 0.0
    allocation_strategy: str = ""
    n_evaluations: int = 0


# ============================================================================
# 内部辅助
# ============================================================================


def _build_distribution(spec: dict):
    """从规格字典构建 SciPy 一元分布对象。

    Raises:
        ValueError: 不支持的分布类型。
    """
    dist_type = spec.get("type", "")
    if dist_type == "norm":
        return norm(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
    if dist_type == "uniform":
        return uniform(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
    raise ValueError(
        f"不支持的分布类型: '{dist_type}'。支持: 'norm', 'uniform'。"
        f"规格: {spec}"
    )


def _compute_strata_bounds(
    dist, n_strata: int
) -> list[tuple[float, float]]:
    """计算使每层概率相等的层边界 bₖ = F⁻¹(k/H)。

    Raises:
        ValueError: n_strata < 1。
    """
    if n_strata < 1:
        raise ValueError(f"n_strata 必须 >= 1，得到 {n_strata}")

    probs = np.linspace(0.0, 1.0, n_strata + 1)
    probs_clipped = np.clip(probs, 1e-12, 1.0 - 1e-12)
    bounds = dist.ppf(probs_clipped)
    for k in range(1, len(bounds)):
        if bounds[k] <= bounds[k - 1]:
            bounds[k] = bounds[k - 1] + 1e-9
    return [(float(bounds[k]), float(bounds[k + 1])) for k in range(n_strata)]


def _sample_in_stratum(
    dist,
    lower: float,
    upper: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """在指定层 [lower, upper] 内逆变换采样。"""
    if n_samples == 0:
        return np.empty(0, dtype=float)
    p_lower = float(dist.cdf(lower))
    p_upper = float(dist.cdf(upper))
    if p_upper <= p_lower:
        mid = 0.5 * (lower + upper)
        return np.full(n_samples, mid, dtype=float)
    u = rng.uniform(p_lower, p_upper, size=n_samples)
    u = np.clip(u, 1e-12, 1.0 - 1e-12)
    return dist.ppf(u)


def _allocate_samples(
    n_total: int,
    n_strata: int,
    strategy: AllocationStrategy,
    strata_stds: list[float] | None = None,
) -> list[int]:
    """分配每层样本数。

    Raises:
        ValueError: 参数无效或 NEYMAN 缺少 strata_stds。

    学术依据:
    - EQUAL/PROPORTIONAL: Cochran 1977, Ch.5.5
    - NEYMAN: Neyman 1934, DOI: 10.2307/2342192
    """
    if n_total < n_strata:
        raise ValueError(
            f"n_total ({n_total}) 必须 >= n_strata ({n_strata})，"
            f"每层至少 1 个样本"
        )
    if strategy == AllocationStrategy.EQUAL:
        base = n_total // n_strata
        remainder = n_total - base * n_strata
        return [base + (1 if k < remainder else 0) for k in range(n_strata)]

    if strategy == AllocationStrategy.PROPORTIONAL:
        # 等概率分层下 Wₕ=1/H，PROPORTIONAL 退化为 EQUAL
        return _allocate_samples(n_total, n_strata, AllocationStrategy.EQUAL)

    if strategy == AllocationStrategy.NEYMAN:
        if strata_stds is None or len(strata_stds) != n_strata:
            raise ValueError(
                f"NEYMAN 需要 strata_stds 长度 = {n_strata}，"
                f"得到 {strata_stds}"
            )
        sigmas = np.array(strata_stds, dtype=float)
        sigmas_safe = np.maximum(sigmas, 1e-12)
        weights = sigmas_safe / np.sum(sigmas_safe)
        raw = n_total * weights
        n_per = np.maximum(np.floor(raw).astype(int), 1)
        diff = n_total - int(np.sum(n_per))
        if diff > 0:
            frac = raw - np.floor(raw)
            order = np.argsort(-frac)
            for i in range(diff):
                n_per[order[i % n_strata]] += 1
        elif diff < 0:
            frac = raw - np.floor(raw)
            order = np.argsort(frac)
            i = 0
            while diff < 0:
                idx = order[i % n_strata]
                if n_per[idx] > 1:
                    n_per[idx] -= 1
                    diff += 1
                i += 1
        return [int(x) for x in n_per]

    raise ValueError(f"不支持的分配策略: {strategy}")


def _sample_and_evaluate_stratum(
    func: Callable[[np.ndarray], float],
    dists: list,
    primary_dist,
    lower: float,
    upper: float,
    n_h: int,
    d: int,
    rng: np.random.Generator,
    stratum_idx: int,
) -> np.ndarray:
    """在指定层内采样并评估 func。

    Raises:
        RuntimeError: func 评估失败。
    """
    x_primary = _sample_in_stratum(primary_dist, lower, upper, n_h, rng)
    samples = np.empty((n_h, d), dtype=float)
    samples[:, 0] = x_primary
    for j in range(1, d):
        samples[:, j] = dists[j].rvs(size=n_h, random_state=rng)

    outputs = np.empty(n_h, dtype=float)
    for i in range(n_h):
        try:
            outputs[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (层 {stratum_idx}, 样本 {i}): "
                f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
            ) from e
    return outputs


def _validate_stratified_params(
    nominal_dist: list[dict], n_strata: int, n_samples: int
) -> None:
    """校验 stratified_monte_carlo 入参。"""
    if len(nominal_dist) == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_strata < 1:
        raise ValueError(f"n_strata 必须 >= 1，得到 {n_strata}")
    if n_samples < n_strata:
        raise ValueError(
            f"n_samples ({n_samples}) 必须 >= n_strata ({n_strata})，"
            f"每层至少 1 个样本"
        )


def _neyman_pilot_stage(
    func: Callable[[np.ndarray], float],
    dists: list,
    primary_dist,
    strata_bounds: list[tuple[float, float]],
    n_strata: int,
    n_pilot: int,
    d: int,
    rng: np.random.Generator,
) -> tuple[list[np.ndarray], list[float]]:
    """NEYMAN 阶段 1 pilot: EQUAL 分配采样并估计 σ̂ₕ。"""
    n_pilot_per = _allocate_samples(
        n_total=n_pilot, n_strata=n_strata, strategy=AllocationStrategy.EQUAL
    )
    pilot_outputs_per_stratum: list[np.ndarray] = []
    pilot_stds: list[float] = []
    for h, (lower, upper) in enumerate(strata_bounds):
        n_h = n_pilot_per[h]
        if n_h == 0:
            raise RuntimeError(
                f"pilot EQUAL 分配层 {h} 样本数为 0，违反约束。"
                f"n_pilot={n_pilot}, n_strata={n_strata}。禁止 fall-back。"
            )
        outs = _sample_and_evaluate_stratum(
            func, dists, primary_dist, lower, upper, n_h, d, rng, h
        )
        pilot_outputs_per_stratum.append(outs)
        pilot_stds.append(
            float(np.std(outs, ddof=1)) if n_h > 1 else 0.0
        )

    valid_stds = [s for s in pilot_stds if s > 0]
    if not valid_stds:
        pilot_stds_safe = [1.0] * n_strata
    else:
        median_std = float(np.median(valid_stds))
        pilot_stds_safe = [s if s > 0 else median_std for s in pilot_stds]
    return pilot_outputs_per_stratum, pilot_stds_safe


def _run_neyman_two_stage(
    func: Callable[[np.ndarray], float],
    dists: list,
    primary_dist,
    strata_bounds: list[tuple[float, float]],
    n_strata: int,
    n_samples: int,
    d: int,
    rng: np.random.Generator,
) -> tuple[list[float], list[float], list[int], list[float], int]:
    """NEYMAN 两阶段分层采样（Cochran 1977 Ch.5A）。"""
    n_pilot = max(5 * n_strata, int(np.ceil(0.1 * n_samples)))
    if n_pilot >= n_samples:
        n_pilot = n_samples
        n_main = 0
    else:
        n_main = n_samples - n_pilot

    pilot_outputs_per_stratum, pilot_stds_safe = _neyman_pilot_stage(
        func, dists, primary_dist, strata_bounds, n_strata, n_pilot, d, rng
    )

    if n_main > 0:
        n_main_per = _allocate_samples(
            n_total=n_main, n_strata=n_strata,
            strategy=AllocationStrategy.NEYMAN, strata_stds=pilot_stds_safe,
        )
    else:
        n_main_per = [0] * n_strata

    strata_means: list[float] = []
    strata_stds: list[float] = []
    n_per_stratum: list[int] = []
    all_outputs: list[float] = []
    n_evaluations = 0
    for h, (lower, upper) in enumerate(strata_bounds):
        pilot_outs = pilot_outputs_per_stratum[h]
        n_main_h = n_main_per[h]
        if n_main_h > 0:
            main_outs = _sample_and_evaluate_stratum(
                func, dists, primary_dist, lower, upper, n_main_h, d, rng, h
            )
            combined = np.concatenate([pilot_outs, main_outs])
        else:
            combined = pilot_outs
        n_total_h = len(combined)
        n_per_stratum.append(n_total_h)
        all_outputs.extend(combined.tolist())
        n_evaluations += n_total_h
        strata_means.append(float(np.mean(combined)))
        strata_stds.append(
            float(np.std(combined, ddof=1)) if n_total_h > 1 else 0.0
        )
    return strata_means, strata_stds, n_per_stratum, all_outputs, n_evaluations


def _run_single_stage(
    func: Callable[[np.ndarray], float],
    dists: list,
    primary_dist,
    strata_bounds: list[tuple[float, float]],
    n_strata: int,
    n_samples: int,
    strategy: AllocationStrategy,
    d: int,
    rng: np.random.Generator,
) -> tuple[list[float], list[float], list[int], list[float], int]:
    """EQUAL/PROPORTIONAL 单阶段分层采样。

    Raises:
        RuntimeError: 某层分配到 0 个样本（R03 禁止 fall-back）。
    """
    n_per_stratum = _allocate_samples(
        n_total=n_samples, n_strata=n_strata, strategy=strategy
    )
    strata_means: list[float] = []
    strata_stds: list[float] = []
    all_outputs: list[float] = []
    n_evaluations = 0
    for h, (lower, upper) in enumerate(strata_bounds):
        n_h = n_per_stratum[h]
        if n_h == 0:
            raise RuntimeError(
                f"分层 {h} (bounds=[{lower}, {upper})) 分配到 0 个样本，"
                f"无法估计该层统计量（R03 禁止 fall-back）。"
                f"请增大 n_samples (当前总样本={n_samples}, 层数={n_strata}) "
                f"或改用 NEYMAN 分配策略。"
            )
        outputs = _sample_and_evaluate_stratum(
            func, dists, primary_dist, lower, upper, n_h, d, rng, h
        )
        n_evaluations += n_h
        all_outputs.extend(outputs.tolist())
        strata_means.append(float(np.mean(outputs)))
        strata_stds.append(
            float(np.std(outputs, ddof=1)) if n_h > 1 else 0.0
        )
    return strata_means, strata_stds, n_per_stratum, all_outputs, n_evaluations


def _compute_stratified_estimate(
    strata_means: list[float],
    strata_stds: list[float],
    n_per_stratum: list[int],
    strata_weights: list[float],
    all_outputs: list[float],
    n_samples: int,
) -> tuple[float, float, float, float, float, float, float, float]:
    """合并分层估计与统计量。

    Returns:
        (estimate, std_error, relative_error, ci_lower, ci_upper,
        variance_estimate, var_naive_mc, speedup)。

    来源: Cochran 1977 Ch.5; Glasserman 2003 Ch.4
    """
    estimate = sum(
        w * m for w, m in zip(strata_weights, strata_means, strict=True)
    )
    variance_estimate = sum(
        w * w * (s * s / n_h)
        for w, s, n_h in zip(
            strata_weights, strata_stds, n_per_stratum, strict=True
        )
    )
    std_error = (
        float(np.sqrt(variance_estimate)) if variance_estimate > 0 else 0.0
    )
    relative_error = (
        std_error / abs(estimate) if abs(estimate) > 0 else float("inf")
    )
    ci_lower = estimate - 1.96 * std_error
    ci_upper = estimate + 1.96 * std_error
    all_outputs_arr = np.array(all_outputs, dtype=float)
    var_naive_mc = (
        float(np.var(all_outputs_arr, ddof=1)) / n_samples
        if n_samples > 1
        else 0.0
    )
    speedup = (
        var_naive_mc / variance_estimate
        if variance_estimate > 0
        else float("inf")
    )
    return (
        estimate, std_error, relative_error, ci_lower, ci_upper,
        variance_estimate, var_naive_mc, speedup,
    )


# ============================================================================
# 核心估计器
# ============================================================================


def stratified_monte_carlo(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    n_strata: int = 10,
    n_samples: int = 10000,
    strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
    seed: int | None = None,
) -> StratifiedSamplingResult:
    """分层蒙特卡洛仿真。

    将每维参数空间划分为 n_strata 等概率层，在每层内独立采样，
    层内均值加权合并总估计。对"层内方差小、层间方差大"的问题显著减少方差。

    NEYMAN 两阶段实现（无 fall-back，Cochran 1977 Ch.5A）:
    σₕ 未知 → 阶段 1 (pilot) 用 EQUAL 估计 σ̂ₕ → 阶段 2 (main) 用 σ̂ₕ 做
    Neyman 分配 → 合并两阶段样本计算层内均值/方差。

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        nominal_dist: 标称分布规格列表。
        n_strata: 层数 H。
        n_samples: 总样本数 n。
        strategy: 分配策略。
        seed: 随机种子。

    Returns:
        StratifiedSamplingResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败或某层分配到 0 样本。

    学术依据:
    - Cochran 1977, Ch.5 + Ch.5A
    - Neyman 1934, DOI: 10.2307/2342192
    - McKay et al. 1979, DOI: 10.1080/00401706.1979.10489755
    - Glasserman 2003, Ch.4, DOI: 10.1007/978-0-387-21617-1
    """
    _validate_stratified_params(nominal_dist, n_strata, n_samples)
    d = len(nominal_dist)

    rng = np.random.default_rng(seed)
    dists = [_build_distribution(spec) for spec in nominal_dist]
    primary_dist = dists[0]
    strata_bounds = _compute_strata_bounds(primary_dist, n_strata)
    strata_weights = [1.0 / n_strata] * n_strata

    common = (func, dists, primary_dist, strata_bounds, n_strata, n_samples)
    if strategy == AllocationStrategy.NEYMAN:
        result = _run_neyman_two_stage(*common, d, rng)
    else:
        result = _run_single_stage(*common, strategy, d, rng)
    strata_means, strata_stds, n_per_stratum, all_outputs, n_evaluations = (
        result
    )

    (estimate, std_error, relative_error, ci_lower, ci_upper,
     variance_estimate, var_naive_mc, speedup) = _compute_stratified_estimate(
        strata_means, strata_stds, n_per_stratum, strata_weights,
        all_outputs, n_samples,
    )

    return StratifiedSamplingResult(
        estimate=estimate, std_error=std_error,
        relative_error=relative_error, ci_lower=ci_lower,
        ci_upper=ci_upper, n_strata=n_strata, n_samples=n_evaluations,
        n_per_stratum=n_per_stratum, strata_weights=strata_weights,
        strata_means=strata_means, strata_stds=strata_stds,
        variance_estimate=variance_estimate,
        variance_naive_mc=var_naive_mc, speedup_vs_mc=speedup,
        allocation_strategy=strategy.value, n_evaluations=n_evaluations,
    )


def compare_stratified_convergence(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    true_value: float,
    sample_sizes: list[int],
    n_strata: int = 10,
    strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
    seed: int | None = None,
) -> dict:
    """对比分层采样与朴素 MC 的收敛速率。

    Args:
        func: 仿真函数。
        nominal_dist: 标称分布规格列表。
        true_value: 真值。
        sample_sizes: 样本数列表。
        n_strata: 层数。
        strategy: 分配策略。
        seed: 随机种子。

    Returns:
        dict 含 sample_sizes / mc_errors / stratified_errors /
        mc_final_error / stratified_final_error / speedup_factor。

    Raises:
        ValueError: 参数无效。

    学术依据: Glasserman 2003, Ch.4
    """
    if not sample_sizes:
        raise ValueError("sample_sizes 不能为空")
    d = len(nominal_dist)
    if d == 0:
        raise ValueError("nominal_dist 不能为空")

    rng = np.random.default_rng(seed)
    mc_errors: list[float] = []
    stratified_errors: list[float] = []

    for n in sample_sizes:
        mc_errors.append(_compute_mc_convergence_error(
            func, nominal_dist, n, rng, true_value,
        ))
        stratified_errors.append(_compute_stratified_convergence_error(
            func, nominal_dist, n_strata, n, strategy, seed, true_value,
        ))

    mc_final = mc_errors[-1]
    strat_final = stratified_errors[-1]
    speedup = mc_final / strat_final if strat_final > 0 else float("inf")

    return {
        "sample_sizes": list(sample_sizes),
        "mc_errors": mc_errors,
        "stratified_errors": stratified_errors,
        "mc_final_error": mc_final,
        "stratified_final_error": strat_final,
        "speedup_factor": speedup,
    }


def _compute_mc_convergence_error(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    n: int,
    rng: np.random.Generator,
    true_value: float,
) -> float:
    """单样本规模下朴素 MC 的相对误差（Extract Method，R11 质量门禁）。

    学术依据: Glasserman 2003, Ch.4。
    """
    d = len(nominal_dist)
    mc_samples = np.empty((n, d))
    for j in range(d):
        spec = nominal_dist[j]
        if spec.get("type") == "norm":
            mc_samples[:, j] = rng.normal(
                loc=spec.get("loc", 0.0),
                scale=spec.get("scale", 1.0),
                size=n,
            )
        else:
            mc_samples[:, j] = rng.uniform(
                low=spec.get("loc", 0.0),
                high=spec.get("loc", 0.0) + spec.get("scale", 1.0),
                size=n,
            )
    mc_outputs = np.array([float(func(mc_samples[i])) for i in range(n)])
    mc_mean = float(np.mean(mc_outputs))
    if true_value != 0:
        return abs(mc_mean - true_value) / abs(true_value)
    return abs(mc_mean - true_value)


def _compute_stratified_convergence_error(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    n_strata: int,
    n: int,
    strategy: AllocationStrategy,
    seed: int | None,
    true_value: float,
) -> float:
    """单样本规模下分层采样的相对误差（Extract Method，R11 质量门禁）。

    学术依据: Glasserman 2003, Ch.4。
    """
    strat_result = stratified_monte_carlo(
        func=func, nominal_dist=nominal_dist, n_strata=n_strata,
        n_samples=n, strategy=strategy, seed=seed,
    )
    if true_value != 0:
        return abs(strat_result.estimate - true_value) / abs(true_value)
    return abs(strat_result.estimate - true_value)


__all__ = [
    "AllocationStrategy",
    "StratifiedSamplingResult",
    "compare_stratified_convergence",
    "stratified_monte_carlo",
]
