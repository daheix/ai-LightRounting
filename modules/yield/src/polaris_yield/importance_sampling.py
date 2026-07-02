"""重要性采样 (Importance Sampling, IS) 稀有事件良率估计（polaris-yield 子模块）。

从 v4 ``polaris.sim.importance_sampling*`` 4 个子模块合并迁移；
R13 不保留 v4 兼容路径；R04 纯 NumPy/SciPy 实现。

## 核心功能

1. ``importance_sampling_yield``: 稀有事件良率估计 Ŷ = mean(𝟙_A · W)
2. ``importance_sampling_mean``: 期望估计 E_f[g(X)]
3. ``rare_event_yield``: MEAN_SHIFT 便捷接口
4. ``cross_entropy_importance_sampling``: CE 自适应迭代寻找最优 q*

## 偏置分布构造方法

- MEAN_SHIFT: ``q(x) = f(x - μ_shift)``
- VARIANCE_SCALING: ``q(x) = f(x/σ_s)/σ_s``
- EXPONENTIAL_TWIST: ``q_θ(x) ∝ exp(θᵀx)·f(x)`` (Siegmund 1976)
- MIXTURE: ``q(x) = (1-α)f(x) + α·h(x)`` (最稳健默认)
- CROSS_ENTROPY: Rubinstein 1997 自适应迭代

## 学术依据（R02 学术诚信，≥5 文献 URL）

- Glynn & Iglehart 1989, "Importance sampling for stochastic simulations",
  Management Science 35(11):1367-1392,
  https://doi.org/10.1287/mnsc.35.11.1367
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer Ch.4, https://doi.org/10.1007/978-0-387-21617-1
- Heidelberger 1995, "Fast simulation of rare events in queueing and
  reliability models", ACM TOMACS 5(1):43-85,
  https://doi.org/10.1145/270261.270264
- Bucklew 2004, "Introduction to Rare Event Simulation", Springer,
  https://doi.org/10.1007/b97468
- Siegmund 1976, "Importance Sampling in the Monte Carlo Study of
  Sequential Tests", Annals of Statistics 4(4):673-684,
  https://doi.org/10.1214/aos/1176343542
- Rubinstein 1997, "Optimization of computer simulation models with rare
  events", European J. Oper. Res. 99:89-112,
  https://doi.org/10.1016/S0377-2217(96)00385-2
- Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo Methods",
  Wiley, https://doi.org/10.1002/9781118014967
- Asmussen & Glynn 2007, "Stochastic Simulation: Algorithms and
  Analysis", Springer, https://doi.org/10.1007/978-0-387-69033-9
- Bogaerts et al. 2018, layout-aware photonic yield,
  https://fib.intec.ugent.be/download/pub_4125.pdf
- De Boer et al. 2005, "A Tutorial on the Cross-Entropy Method",
  Annals of Operations Research 134:19-67
- SciPy stats: https://docs.scipy.org/doc/scipy/reference/stats.html

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.special import logsumexp
from scipy.stats import norm, uniform

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类型
# ============================================================================


class BiasingMethod(Enum):
    """偏置分布构造方法。

    对标商业工具的稀有事件能力（多数商业工具无 IS，PoLaRIS 为差异化能力）。
    """

    MEAN_SHIFT = "mean_shift"
    VARIANCE_SCALING = "variance_scaling"
    EXPONENTIAL_TWIST = "exponential_twist"
    MIXTURE = "mixture"
    CROSS_ENTROPY = "cross_entropy"


@dataclass
class BiasingSpec:
    """偏置分布构造规格。

    Attributes:
        method: 偏置方法。
        mean_shift: MEAN_SHIFT / MIXTURE / CROSS_ENTROPY 用，每维偏移量。
        variance_scale: VARIANCE_SCALING 用，每维缩放因子 (>1 放大)。
        twist_theta: EXPONENTIAL_TWIST 用，每维扭转参数 θ。
        mixture_alpha: MIXTURE 用，混合权重 α ∈ (0, 1)。
        elite_ratio: CROSS_ENTROPY 用，elite 比例 ρ ∈ (0.01, 0.2)。
        n_iterations: CROSS_ENTROPY 用，自适应迭代次数。
        smoothing_alpha: CROSS_ENTROPY 用，参数平滑系数 ∈ [0.5, 0.9]。
    """

    method: BiasingMethod = BiasingMethod.MEAN_SHIFT
    mean_shift: list[float] | None = None
    variance_scale: list[float] | None = None
    twist_theta: list[float] | None = None
    mixture_alpha: float = 0.3
    elite_ratio: float = 0.1
    n_iterations: int = 5
    smoothing_alpha: float = 0.7


@dataclass
class ImportanceSamplingResult:
    """重要性采样估计结果。

    Attributes:
        yield_estimate: 良率/期望估计 Ŷ。
        std_error: 标准误差 SE = σ̂/√n。
        relative_error: 相对误差 RE = SE/|Ŷ|。
        ci_lower: 95% 置信区间下界。
        ci_upper: 95% 置信区间上界。
        effective_sample_size: ESS = (ΣW)²/ΣW²。
        speedup_vs_mc: 与朴素 MC 方差缩减比。
        n_samples: 实际样本数。
        n_failures: 失效样本数。
        n_evaluations: 总模型评估次数。
        biasing_method: 偏置方法名。
        log_weights: log 似然比数组。
        samples: 采样数组 (n_samples, d)。
        converged: CE 自适应收敛标志；其他方法为 None。
    """

    yield_estimate: float = 0.0
    std_error: float = 0.0
    relative_error: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    effective_sample_size: float = 0.0
    speedup_vs_mc: float = 0.0
    n_samples: int = 0
    n_failures: int = 0
    n_evaluations: int = 0
    biasing_method: str = ""
    log_weights: np.ndarray = field(default_factory=lambda: np.empty(0))
    samples: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    converged: bool | None = None


# ============================================================================
# 分布构造与采样辅助
# ============================================================================


def _build_univariate_distributions(
    specs: list[dict],
) -> list[norm | uniform]:
    """从规格列表构建一元 SciPy 分布对象列表。

    Raises:
        ValueError: 不支持的分布类型。
    """
    dists: list[norm | uniform] = []
    for i, spec in enumerate(specs):
        dist_type = spec.get("type", "")
        if dist_type == "norm":
            dists.append(
                norm(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
            )
        elif dist_type == "uniform":
            dists.append(
                uniform(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
            )
        else:
            raise ValueError(
                f"分布规格[{i}] 类型 '{dist_type}' 不支持。"
                f"支持: 'norm', 'uniform'。规格: {spec}"
            )
    return dists


def _sample_from_distributions(
    dists: list[norm | uniform],
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """从一元分布列表独立采样。"""
    d = len(dists)
    samples = np.empty((n_samples, d), dtype=float)
    for j in range(d):
        samples[:, j] = dists[j].rvs(size=n_samples, random_state=rng)
    return samples


def _logpdf_distributions(
    dists: list[norm | uniform], x: np.ndarray
) -> np.ndarray:
    """多元独立分布对数密度 log f(x) = Σⱼ log fⱼ(xⱼ)。"""
    x = np.asarray(x, dtype=float)
    n = x.shape[0]
    log_p = np.zeros(n, dtype=float)
    for j in range(len(dists)):
        log_p += dists[j].logpdf(x[:, j])
    return log_p


def _build_shifted_specs_as_dists(
    nominal_specs: list[dict],
    mean_shift: list[float] | None,
) -> list[norm | uniform]:
    """构造 loc += mean_shift[j] 的偏置分布列表。"""
    h_specs: list[dict] = []
    for j, spec in enumerate(nominal_specs):
        shift = float(mean_shift[j])
        new_spec = dict(spec)
        new_spec["loc"] = spec.get("loc", 0.0) + shift
        h_specs.append(new_spec)
    return _build_univariate_distributions(h_specs)


def _construct_biasing_distribution(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """根据偏置规格构造偏置分布列表（dispatch）。

    Raises:
        ValueError: 偏置参数缺失或无效。
    """
    method = biasing.method
    d = len(nominal_specs)

    if method == BiasingMethod.MEAN_SHIFT:
        if biasing.mean_shift is None or len(biasing.mean_shift) != d:
            raise ValueError(
                f"MEAN_SHIFT 需要 mean_shift 长度 = {d}，"
                f"得到 {biasing.mean_shift}"
            )
        return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)

    if method == BiasingMethod.VARIANCE_SCALING:
        if (
            biasing.variance_scale is None
            or len(biasing.variance_scale) != d
        ):
            raise ValueError(
                f"VARIANCE_SCALING 需要 variance_scale 长度 = {d}，"
                f"得到 {biasing.variance_scale}"
            )
        biasing_specs: list[dict] = []
        for j, spec in enumerate(nominal_specs):
            scale = float(biasing.variance_scale[j])
            if scale <= 0:
                raise ValueError(
                    f"variance_scale[{j}] 必须 > 0，得到 {scale}"
                )
            new_spec = dict(spec)
            new_spec["scale"] = spec.get("scale", 1.0) * scale
            biasing_specs.append(new_spec)
        return _build_univariate_distributions(biasing_specs)

    if method == BiasingMethod.EXPONENTIAL_TWIST:
        if biasing.twist_theta is None or len(biasing.twist_theta) != d:
            raise ValueError(
                f"EXPONENTIAL_TWIST 需要 twist_theta 长度 = {d}，"
                f"得到 {biasing.twist_theta}"
            )
        biasing_specs = []
        for j, spec in enumerate(nominal_specs):
            theta = float(biasing.twist_theta[j])
            biasing_specs.append(_twist_single_spec(spec, theta))
        return _build_univariate_distributions(biasing_specs)

    if method == BiasingMethod.MIXTURE:
        if biasing.mean_shift is None or len(biasing.mean_shift) != d:
            raise ValueError(
                f"MIXTURE 需要 mean_shift 长度 = {d}，"
                f"得到 {biasing.mean_shift}"
            )
        if not (0.0 < biasing.mixture_alpha < 1.0):
            raise ValueError(
                f"mixture_alpha 必须在 (0, 1)，得到 {biasing.mixture_alpha}"
            )
        return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)

    if method == BiasingMethod.CROSS_ENTROPY:
        if biasing.mean_shift is None or len(biasing.mean_shift) != d:
            raise ValueError(
                f"CROSS_ENTROPY 需要 mean_shift 作为初始 h 长度 = {d}，"
                f"得到 {biasing.mean_shift}"
            )
        return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)

    raise ValueError(f"不支持的偏置方法: {method}")


def _twist_single_spec(spec: dict, theta: float) -> dict:
    """对单个标称分布规格应用指数扭转 θ。

    - norm: q_θ = N(μ + σ²θ, σ)（Siegmund 1976, Glasserman 2003 Ch.4.4）
    - uniform: 退化为 loc += θ（工程近似）
    """
    dist_type = spec.get("type", "")
    if dist_type == "norm":
        mu = spec.get("loc", 0.0)
        sigma = spec.get("scale", 1.0)
        return {
            "type": "norm",
            "loc": mu + sigma * sigma * theta,
            "scale": sigma,
        }
    if dist_type == "uniform":
        new_spec = dict(spec)
        new_spec["loc"] = spec.get("loc", 0.0) + theta
        return new_spec
    raise ValueError(f"EXPONENTIAL_TWIST 不支持分布类型 '{dist_type}'")


def _sample_mixture(
    f_dists: list[norm | uniform],
    h_dists: list[norm | uniform],
    alpha: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """从混合分布 q = (1-α)f + α·h 采样。

    学术依据: Heidelberger 1995, DOI: 10.1145/270261.270264
    """
    mask = rng.random(n_samples) < alpha
    n_h = int(np.sum(mask))
    n_f = n_samples - n_h
    d = len(f_dists)
    samples = np.empty((n_samples, d), dtype=float)
    if n_f > 0:
        samples[~mask] = _sample_from_distributions(f_dists, n_f, rng)
    if n_h > 0:
        samples[mask] = _sample_from_distributions(h_dists, n_h, rng)
    return samples


def _logpdf_mixture(
    f_dists: list[norm | uniform],
    h_dists: list[norm | uniform],
    alpha: float,
    x: np.ndarray,
) -> np.ndarray:
    """混合分布 q = (1-α)f + α·h 的对数密度。

    log q(x) = logsumexp(log(1-α)+log f, log(α)+log h)
    """
    log_f = _logpdf_distributions(f_dists, x)
    log_h = _logpdf_distributions(h_dists, x)
    log_alpha = np.log(alpha)
    log_1_alpha = np.log(1.0 - alpha)
    stacked = np.vstack([log_1_alpha + log_f, log_alpha + log_h])
    return logsumexp(stacked, axis=0)


def _compute_log_weights(
    nominal_dists: list[norm | uniform],
    biasing_dists: list[norm | uniform],
    samples: np.ndarray,
    biasing: BiasingSpec,
) -> np.ndarray:
    """计算 log 似然比 log W = log f(x) - log q(x)。

    Raises:
        RuntimeError: 偏置分布支撑未覆盖失效区域（绝对连续违反）。
    """
    log_f = _logpdf_distributions(nominal_dists, samples)
    if biasing.method == BiasingMethod.MIXTURE:
        log_q = _logpdf_mixture(
            nominal_dists, biasing_dists, biasing.mixture_alpha, samples
        )
    else:
        log_q = _logpdf_distributions(biasing_dists, samples)
    log_w = log_f - log_q
    bad_mask = np.isinf(log_w) & (log_w < 0) & np.isfinite(log_f)
    if np.any(bad_mask):
        n_bad = int(np.sum(bad_mask))
        raise RuntimeError(
            f"偏置分布支撑未覆盖失效区域: {n_bad} 个样本 q.pdf(x)=0 但 "
            f"f.pdf(x)>0。绝对连续条件违反。禁止 fall-back（R03）。"
            f"建议增大 mean_shift 或使用 MIXTURE。"
        )
    return log_w


# ============================================================================
# 估计器辅助
# ============================================================================


def _validate_yield_params(
    nominal_dist: list[dict], n_samples: int, min_ess_ratio: float
) -> None:
    """校验 importance_sampling_yield 入参。"""
    if len(nominal_dist) == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if not (0.0 < min_ess_ratio < 1.0):
        raise ValueError(
            f"min_ess_ratio 必须在 (0, 1)，得到 {min_ess_ratio}"
        )


def _evaluate_failure_flags(
    failure_region: Callable[[np.ndarray], bool],
    samples: np.ndarray,
    context: str,
) -> np.ndarray:
    """评估每个样本的失效指示 g(x) = 𝟙_A(x)。"""
    n_samples = samples.shape[0]
    flags = np.empty(n_samples, dtype=bool)
    for i in range(n_samples):
        try:
            flags[i] = bool(failure_region(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"{context} 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e
    return flags


def _compute_weighted_yield_stats(
    weighted: np.ndarray, n_samples: int, n_failures: int
) -> tuple[float, float, float, float, float, float, float, float]:
    """计算加权良率估计统计量。

    Returns:
        (y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup)。
    """
    y_hat = float(np.mean(weighted))
    var_is = (
        float(np.var(weighted, ddof=1)) if n_samples > 1 else 0.0
    )
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0
    re = se / abs(y_hat) if abs(y_hat) > 0 else float("inf")
    ci_lower = y_hat - 1.96 * se
    ci_upper = y_hat + 1.96 * se
    sum_eff = float(np.sum(weighted))
    sum_eff2 = float(np.sum(weighted * weighted))
    ess = (sum_eff * sum_eff) / sum_eff2 if sum_eff2 > 0 else 0.0
    ess_ratio = ess / n_failures if n_failures > 0 else 0.0
    var_mc_single = y_hat * (1.0 - y_hat)
    speedup = var_mc_single / var_is if var_is > 0 else float("inf")
    return y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup


def _check_yield_quality(
    n_failures: int,
    ess_ratio: float,
    re: float,
    min_ess_ratio: float,
) -> None:
    """诊断 IS 良率估计质量，退化即 raise（R03）。"""
    if n_failures < 30:
        raise RuntimeError(
            f"失效样本数 {n_failures} < 30，统计意义不足。"
            f"建议: 增大 n_samples、增大 mean_shift 使 q 更偏向失效区、"
            f"或用 CROSS_ENTROPY 自适应寻找最优偏置。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < min_ess_ratio:
        raise RuntimeError(
            f"ESS 退化: ESS/n_failures = {ess_ratio:.4f} < 阈值 {min_ess_ratio}。"
            f"失效样本权重过度集中，IS 估计不可靠。"
            f"建议: 减小 mean_shift、使用 MIXTURE、或用 CROSS_ENTROPY 自适应。"
            f"禁止 fall-back（R03）。"
        )
    if re > 0.5:
        raise RuntimeError(
            f"相对误差 RE = {re:.4f} > 0.5，IS 估计不可靠。"
            f"建议: 增大 n_samples 或改进偏置分布。禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        logger.warning(
            "ESS/n_failures = %.4f, RE = %.4f 在边缘区间，建议改进偏置分布。",
            ess_ratio,
            re,
        )


# ============================================================================
# 公开 API: 重要性采样估计器
# ============================================================================


def importance_sampling_yield(
    failure_region: Callable[[np.ndarray], bool],
    nominal_dist: list[dict],
    biasing: BiasingSpec,
    n_samples: int = 10000,
    seed: int | None = None,
    min_ess_ratio: float = 0.01,
) -> ImportanceSamplingResult:
    """重要性采样稀有事件良率估计。

    使用偏置分布 q 偏向失效区域采样，似然比 W = f/q 修正权重，
    估计失效良率 Y = P(X ∈ A)。相比朴素 MC 可实现 10²-10⁴ 倍方差缩减。

    Args:
        failure_region: 失效区域指示函数 A: params -> bool（True=失效）。
        nominal_dist: 标称分布规格列表。
        biasing: 偏置分布构造规格。
        n_samples: 样本数（典型 10⁴-10⁵）。
        seed: 随机种子。
        min_ess_ratio: 最小 ESS/n 比，低于此值 raise。

    Returns:
        ImportanceSamplingResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: 偏置分布支撑不足 / ESS 退化 / 评估失败。

    学术依据:
    - Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    - Kroese, Taimre & Botev 2011, DOI: 10.1002/9781118014967
    """
    _validate_yield_params(nominal_dist, n_samples, min_ess_ratio)

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)
    q_dists = _construct_biasing_distribution(nominal_dist, biasing)

    if biasing.method == BiasingMethod.MIXTURE:
        samples = _sample_mixture(
            f_dists, q_dists, biasing.mixture_alpha, n_samples, rng
        )
    else:
        samples = _sample_from_distributions(q_dists, n_samples, rng)

    log_w = _compute_log_weights(f_dists, q_dists, samples, biasing)
    weights = np.exp(log_w)
    failure_flags = _evaluate_failure_flags(
        failure_region, samples, "failure_region"
    )
    n_failures = int(np.sum(failure_flags))
    weighted = failure_flags.astype(float) * weights

    (y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup) = (
        _compute_weighted_yield_stats(weighted, n_samples, n_failures)
    )
    _check_yield_quality(n_failures, ess_ratio, re, min_ess_ratio)

    return ImportanceSamplingResult(
        yield_estimate=y_hat, std_error=se, relative_error=re,
        ci_lower=ci_lower, ci_upper=ci_upper,
        effective_sample_size=ess, speedup_vs_mc=speedup,
        n_samples=n_samples, n_failures=n_failures,
        n_evaluations=n_samples, biasing_method=biasing.method.value,
        log_weights=log_w, samples=samples, converged=None,
    )


def importance_sampling_mean(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    biasing: BiasingSpec,
    n_samples: int = 10000,
    seed: int | None = None,
    min_ess_ratio: float = 0.01,
) -> ImportanceSamplingResult:
    """重要性采样估计 E_f[g(X)]。

    与 :func:`importance_sampling_yield` 相同算法，目标量为 E_f[g(X)]
    而非 P(X ∈ A)。ESS 基于权重 W（不依赖 g 符号）。

    Args:
        func: 性能函数 g: params -> scalar。
        nominal_dist: 标称分布规格列表。
        biasing: 偏置分布构造规格。
        n_samples: 样本数。
        seed: 随机种子。
        min_ess_ratio: 最小 ESS/n 比。

    Returns:
        ImportanceSamplingResult 含 yield_estimate = E_f[g(X)] 估计。

    Raises:
        ValueError: 参数无效。
        RuntimeError: 偏置分布支撑不足 / ESS 退化 / 评估失败。

    学术依据: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    """
    d = len(nominal_dist)
    _validate_yield_params(nominal_dist, n_samples, min_ess_ratio)
    if d == 0:
        raise ValueError("nominal_dist 不能为空")

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)
    q_dists = _construct_biasing_distribution(nominal_dist, biasing)

    if biasing.method == BiasingMethod.MIXTURE:
        samples = _sample_mixture(
            f_dists, q_dists, biasing.mixture_alpha, n_samples, rng
        )
    else:
        samples = _sample_from_distributions(q_dists, n_samples, rng)

    log_w = _compute_log_weights(f_dists, q_dists, samples, biasing)
    weights = np.exp(log_w)

    g_values = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        try:
            g_values[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e

    weighted = g_values * weights
    mu_hat = float(np.mean(weighted))
    var_is = float(np.var(weighted, ddof=1)) if n_samples > 1 else 0.0
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0
    re = se / abs(mu_hat) if abs(mu_hat) > 0 else float("inf")
    ci_lower = mu_hat - 1.96 * se
    ci_upper = mu_hat + 1.96 * se

    sum_w = float(np.sum(weights))
    sum_w2 = float(np.sum(weights * weights))
    ess = (sum_w * sum_w) / sum_w2 if sum_w2 > 0 else 0.0
    ess_ratio = ess / n_samples if n_samples > 0 else 0.0

    if ess_ratio < min_ess_ratio:
        raise RuntimeError(
            f"ESS 退化: ESS/n = {ess_ratio:.4f} < 阈值 {min_ess_ratio}。"
            f"权重过度集中，IS 估计不可靠。禁止 fall-back（R03）。"
        )
    if re > 0.5:
        raise RuntimeError(
            f"相对误差 RE = {re:.4f} > 0.5，IS 估计不可靠。禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        logger.warning(
            "ESS/n = %.4f, RE = %.4f 在边缘区间，建议改进偏置分布。",
            ess_ratio,
            re,
        )

    return ImportanceSamplingResult(
        yield_estimate=mu_hat, std_error=se, relative_error=re,
        ci_lower=ci_lower, ci_upper=ci_upper,
        effective_sample_size=ess, speedup_vs_mc=float("nan"),
        n_samples=n_samples, n_failures=0, n_evaluations=n_samples,
        biasing_method=biasing.method.value, log_weights=log_w,
        samples=samples, converged=None,
    )


def rare_event_yield(
    failure_region: Callable[[np.ndarray], bool],
    nominal_dist: list[dict],
    biasing_mean_shift: list[float],
    n_samples: int = 10000,
    seed: int | None = None,
) -> ImportanceSamplingResult:
    """稀有事件良率估计便捷接口（MEAN_SHIFT 偏置）。

    *创新*：PoLaRIS 差异化能力——商业工具（Calibre YieldOptimizer /
    Lumerical INTERCONNECT / Luceda Circuit Analyzer）均无稀有事件 IS。
    底层逻辑：偏置分布 q(x)=f(x-μ_shift) 把采样质量压向失效区域，
    似然比 W=f/q 修正权重，实现 10²-10⁴ 倍方差缩减。
    支持理论：Glynn & Iglehart 1989 似然比估计器 + Glasserman 2003 Ch.4。
    案例：应用于 PoLaRIS 良率分析，见 操作记录.md。

    Args:
        failure_region: 失效区域指示函数。
        nominal_dist: 标称分布规格列表。
        biasing_mean_shift: 每维偏移量（朝失效区域方向）。
        n_samples: 样本数。
        seed: 随机种子。

    Returns:
        ImportanceSamplingResult。

    学术依据:
    - 均值平移: Glasserman 2003, Ch.4.2, DOI: 10.1007/978-0-387-21617-1
    - 稀有事件良率: Heidelberger 1995, DOI: 10.1145/270261.270264
    """
    biasing = BiasingSpec(
        method=BiasingMethod.MEAN_SHIFT,
        mean_shift=list(biasing_mean_shift),
    )
    return importance_sampling_yield(
        failure_region=failure_region,
        nominal_dist=nominal_dist,
        biasing=biasing,
        n_samples=n_samples,
        seed=seed,
    )


# ============================================================================
# 交叉熵 (CE) 自适应 IS
# ============================================================================


def _validate_ce_params(
    nominal_dist: list[dict],
    n_samples: int,
    n_iterations: int,
    elite_ratio: float,
    smoothing_alpha: float,
) -> None:
    """校验 cross_entropy_importance_sampling 入参。"""
    if len(nominal_dist) == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if n_iterations < 1:
        raise ValueError(f"n_iterations 必须 >= 1，得到 {n_iterations}")
    if not (0.0 < elite_ratio < 1.0):
        raise ValueError(f"elite_ratio 必须在 (0, 1)，得到 {elite_ratio}")
    if not (0.0 <= smoothing_alpha <= 1.0):
        raise ValueError(
            f"smoothing_alpha 必须在 [0, 1]，得到 {smoothing_alpha}"
        )
    for j, spec in enumerate(nominal_dist):
        if spec.get("type", "") != "norm":
            raise ValueError(
                f"CROSS_ENTROPY 自适应参数更新仅支持 'norm' 分布，"
                f"维度 {j} 类型为 '{spec.get('type')}'。"
                f"建议先用 MEAN_SHIFT 或 MIXTURE。"
            )


def _init_ce_distribution(
    nominal_dist: list[dict], initial_mean_shift: list[float]
) -> tuple[np.ndarray, np.ndarray]:
    """初始化 CE 偏置分布 q 的均值/方差。"""
    q_means = np.array(
        [
            spec.get("loc", 0.0) + s
            for spec, s in zip(
                nominal_dist, initial_mean_shift, strict=True
            )
        ],
        dtype=float,
    )
    q_stds = np.array(
        [spec.get("scale", 1.0) for spec in nominal_dist], dtype=float
    )
    return q_means, q_stds


def _run_ce_iterations(
    failure_region: Callable[[np.ndarray], bool],
    rng: np.random.Generator,
    q_means: np.ndarray,
    q_stds: np.ndarray,
    n_samples: int,
    n_iterations: int,
    n_elite: int,
    smoothing_alpha: float,
    d: int,
) -> tuple[np.ndarray, np.ndarray, int, bool]:
    """执行 CE 自适应迭代。

    每轮: 采样 → 评估失效 → 选 elite → 高斯最大似然更新 → 平滑。
    收敛: elite 均值相对变化 < 1e-3。
    """
    total_evals = 0
    converged = False
    for it in range(n_iterations):
        samples = rng.normal(
            loc=q_means, scale=q_stds, size=(n_samples, d)
        )
        flags = _evaluate_failure_flags(
            failure_region, samples, f"CE 迭代 {it} failure_region"
        )
        total_evals += n_samples

        failure_idx = np.where(flags)[0]
        if len(failure_idx) == 0:
            logger.warning(
                "CE 迭代 %d/%d 无失效样本，q 未更新。"
                "建议增大 initial_mean_shift。",
                it + 1,
                n_iterations,
            )
            continue

        elite_idx = (
            failure_idx[:n_elite]
            if len(failure_idx) >= n_elite
            else failure_idx
        )
        elite_samples = samples[elite_idx]
        new_means = np.mean(elite_samples, axis=0)
        new_stds = np.maximum(
            np.std(elite_samples, axis=0, ddof=1), 1e-6
        )
        prev_means = q_means.copy()
        q_means = (
            smoothing_alpha * new_means + (1.0 - smoothing_alpha) * q_means
        )
        q_stds = (
            smoothing_alpha * new_stds + (1.0 - smoothing_alpha) * q_stds
        )

        if it > 0:
            mean_change = np.linalg.norm(new_means - prev_means) / (
                np.linalg.norm(prev_means) + 1e-12
            )
            if mean_change < 1e-3:
                converged = True
                logger.info(
                    "CE 在迭代 %d 收敛（mean_change=%.6f）。",
                    it + 1,
                    mean_change,
                )
                break
    return q_means, q_stds, total_evals, converged


def cross_entropy_importance_sampling(
    failure_region: Callable[[np.ndarray], bool],
    nominal_dist: list[dict],
    initial_mean_shift: list[float],
    n_samples: int = 5000,
    n_iterations: int = 5,
    elite_ratio: float = 0.1,
    smoothing_alpha: float = 0.7,
    seed: int | None = None,
    min_ess_ratio: float = 0.01,
) -> ImportanceSamplingResult:
    """交叉熵 (CE) 自适应重要性采样。

    *创新*：Rubinstein 1997 交叉熵方法的 PoLaRIS 实现。当失效区域几何
    未知时，CE 自适应迭代寻找最优偏置分布 q*，避免手动调参。
    底层逻辑：每轮采 n 样本 → 选 elite(失效前 ρ 分位) → 高斯最大似然
    更新 q → 平滑 θ_{t+1}←α·θ_{t+1}+(1-α)·θ_t → 用最终 q 跑 IS。
    支持理论：Rubinstein 1997 + De Boer et al. 2005 CE 教程 +
    Kroese, Taimre & Botev 2011 Ch.13。
    案例：应用于 PoLaRIS 稀有事件良率，见 操作记录.md。

    Args:
        failure_region: 失效区域指示函数。
        nominal_dist: 标称分布规格列表（仅 norm 支持自适应）。
        initial_mean_shift: 初始偏移方向。
        n_samples: 每轮迭代样本数。
        n_iterations: 迭代轮数。
        elite_ratio: elite 比例 ρ ∈ (0.01, 0.2)。
        smoothing_alpha: 平滑系数 α ∈ [0.5, 0.9]。
        seed: 随机种子。
        min_ess_ratio: 最终 IS 估计的最小 ESS/n 比。

    Returns:
        ImportanceSamplingResult 含 converged 标志。

    Raises:
        ValueError: 参数无效。
        RuntimeError: CE 迭代失败或最终 ESS 退化。

    学术依据:
    - Rubinstein 1997, DOI: 10.1016/S0377-2217(96)00385-2
    - Kroese, Taimre & Botev 2011, Ch.13, DOI: 10.1002/9781118014967
    - De Boer et al. 2005, "A Tutorial on the Cross-Entropy Method",
      Annals of Operations Research 134:19-67
    """
    _validate_ce_params(
        nominal_dist, n_samples, n_iterations, elite_ratio, smoothing_alpha
    )
    d = len(nominal_dist)

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)
    q_means, q_stds = _init_ce_distribution(nominal_dist, initial_mean_shift)
    n_elite = max(1, int(n_samples * elite_ratio))

    q_means, q_stds, total_evals, converged = _run_ce_iterations(
        failure_region, rng, q_means, q_stds, n_samples, n_iterations,
        n_elite, smoothing_alpha, d,
    )

    # 用最终 q 跑大批量 IS 估计
    final_specs = [
        {"type": "norm", "loc": float(q_means[j]), "scale": float(q_stds[j])}
        for j in range(d)
    ]
    q_dists = _build_univariate_distributions(final_specs)
    samples = _sample_from_distributions(q_dists, n_samples, rng)

    log_f = _logpdf_distributions(f_dists, samples)
    log_q = _logpdf_distributions(q_dists, samples)
    log_w = log_f - log_q

    bad_mask = np.isinf(log_w) & (log_w < 0) & np.isfinite(log_f)
    if np.any(bad_mask):
        n_bad = int(np.sum(bad_mask))
        raise RuntimeError(
            f"CE 最终 q 分布支撑不足: {n_bad} 个样本 q.pdf=0 但 f.pdf>0。"
            f"绝对连续条件违反。禁止 fall-back（R03）。"
        )

    weights = np.exp(log_w)
    flags = _evaluate_failure_flags(
        failure_region, samples, "最终 IS 估计 failure_region"
    )
    total_evals += n_samples
    n_failures = int(np.sum(flags))
    weighted = flags.astype(float) * weights

    (y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup) = (
        _compute_weighted_yield_stats(weighted, n_samples, n_failures)
    )

    # CE 最终质量诊断
    if n_failures < 30:
        raise RuntimeError(
            f"CE 最终失效样本数 {n_failures} < 30，统计意义不足。"
            f"建议: 增大 n_iterations、调整 elite_ratio、或改用 MIXTURE。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < min_ess_ratio:
        raise RuntimeError(
            f"CE 最终 IS 估计 ESS 退化: ESS/n_failures = {ess_ratio:.4f} "
            f"< 阈值 {min_ess_ratio}。禁止 fall-back（R03）。"
        )
    if re > 0.5:
        raise RuntimeError(
            f"CE 最终 IS 估计 RE = {re:.4f} > 0.5，不可靠。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        logger.warning(
            "CE 最终 ESS/n_failures = %.4f, RE = %.4f 边缘区间。",
            ess_ratio,
            re,
        )

    return ImportanceSamplingResult(
        yield_estimate=y_hat, std_error=se, relative_error=re,
        ci_lower=ci_lower, ci_upper=ci_upper,
        effective_sample_size=ess, speedup_vs_mc=speedup,
        n_samples=n_samples, n_failures=n_failures,
        n_evaluations=total_evals,
        biasing_method=BiasingMethod.CROSS_ENTROPY.value,
        log_weights=log_w, samples=samples, converged=converged,
    )


__all__ = [
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
    "cross_entropy_importance_sampling",
    "importance_sampling_mean",
    "importance_sampling_yield",
    "rare_event_yield",
]
