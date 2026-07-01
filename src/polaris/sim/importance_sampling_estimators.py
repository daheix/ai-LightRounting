"""重要性采样核心估计器（R261-R280，批次 10-B 拆分子模块）。

本子模块实现重要性采样核心估计器：
- :func:`importance_sampling_yield`: 稀有事件良率估计 Ŷ = mean(𝟙_A · W)
- :func:`importance_sampling_mean`: 期望估计 E_f[g(X)]（含 ESS Bug 修复 v5.0-P2-R114）
- :func:`rare_event_yield`: MEAN_SHIFT 便捷接口

并含内部辅助：参数校验、失效指示评估、加权统计量、质量诊断（退化即 raise）。

## 学术依据

- 似然比估计器: Glynn & Iglehart 1989, "Importance sampling for stochastic
  simulations", Management Science 35(11):1367-1392,
  DOI: 10.1287/mnsc.35.11.1367
- 方差减少系统讲解: Glasserman 2003, "Monte Carlo Methods in Financial
  Engineering", Springer Ch.4, DOI: 10.1007/978-0-387-21617-1
- 稀有事件仿真综述: Heidelberger 1995, "Fast simulation of rare events in
  queueing and reliability models", ACM TOMACS 5(1):43-85,
  DOI: 10.1145/270261.270264
- 大偏差理论视角: Bucklew 2004, "Introduction to Rare Event Simulation",
  Springer, DOI: 10.1007/b97468
- 现代稀有事件综述: Juneja & Shahabuddin 2006, "Rare-Event Simulation
  Techniques: An Introduction and Recent Advances", Handbooks in OR&MS vol 13
- 指数扭转: Siegmund 1976, "Importance Sampling in the Monte Carlo Study of
  Sequential Tests", Annals of Statistics 4(4):673-684,
  DOI: 10.1214/aos/1176343542
- 交叉熵方法: Rubinstein 1997, "Optimization of computer simulation models
  with rare events", European J. Oper. Res. 99:89-112,
  DOI: 10.1016/S0377-2217(96)00385-2
- 自适应 IS / ESS 诊断: Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo
  Methods", Wiley, DOI: 10.1002/9781118014967
- 现代教科书: Asmussen & Glynn 2007, "Stochastic Simulation: Algorithms and
  Analysis", Springer, DOI: 10.1007/978-0-387-69033-9
- 光子学良率工业标准: Bogaerts et al. 2018, "Layout-Aware Yield Prediction of
  Photonic Circuits", OFC, https://fib.intec.ugent.be/download/pub_4125.pdf
- SciPy stats 文档: https://docs.scipy.org/doc/scipy/reference/stats.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。

来源（拆分依据）:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np

from polaris.sim.importance_sampling_distributions import (
    _build_univariate_distributions,
    _compute_log_weights,
    _construct_biasing_distribution,
    _logpdf_distributions,
    _sample_from_distributions,
    _sample_mixture,
)
from polaris.sim.importance_sampling_types import (
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
)

logger = logging.getLogger(__name__)


def _validate_yield_params(
    nominal_dist: list[dict], n_samples: int, min_ess_ratio: float
) -> None:
    """校验 importance_sampling_yield 入参（R261 内部辅助，R03 禁止 fall-back）。

    Args:
        nominal_dist: 标称分布规格列表。
        n_samples: 样本数。
        min_ess_ratio: 最小 ESS/n 比。

    Raises:
        ValueError: 参数无效。
    """
    if len(nominal_dist) == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if not (0.0 < min_ess_ratio < 1.0):
        raise ValueError(f"min_ess_ratio 必须在 (0, 1)，得到 {min_ess_ratio}")


def _evaluate_failure_flags(
    failure_region: Callable[[np.ndarray], bool],
    samples: np.ndarray,
    context: str,
) -> np.ndarray:
    """评估每个样本的失效区域指示 g(x) = 𝟙_A(x)（R261 内部辅助）。

    Args:
        failure_region: 失效区域指示函数 ``A: params -> bool``。
        samples: 样本数组 (n_samples, d)。
        context: 错误消息上下文（如 ``"failure_region"``、``"CE 迭代 0 样本"``）。

    Returns:
        bool 数组 (n_samples,)，True 表示样本在失效区域。

    Raises:
        RuntimeError: failure_region 评估异常（禁止 fall-back，规则 14.1）。
    """
    n_samples = samples.shape[0]
    flags = np.empty(n_samples, dtype=bool)
    for i in range(n_samples):
        try:
            flags[i] = bool(failure_region(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"{context} 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
            ) from e
    return flags


def _compute_weighted_yield_stats(
    weighted: np.ndarray, n_samples: int, n_failures: int
) -> tuple[float, float, float, float, float, float, float, float]:
    """计算加权良率估计统计量（R261 内部辅助）。

    计算项目：
    - 加权良率 ``Ŷ = mean(g·W)``
    - 标准误差 ``SE = std(g·W)/√n``
    - 相对误差 ``RE = SE/|Ŷ|``
    - 95% 置信区间（正态近似）
    - ESS 诊断: ``ESS = (Σ(g·W))²/Σ(g·W)²``
    - 加速比: ``Speedup = Y(1-Y)/Var_q(g·W)``

    ESS 基于有效贡献权重 g·W，反映失效样本权重的均匀性。
    来源: Kroese, Taimre & Botev 2011, Ch.9, DOI: 10.1002/9781118014967

    Args:
        weighted: 加权后的样本数组 (g·W)。
        n_samples: 样本数。
        n_failures: 失效样本数。

    Returns:
        (y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup)。
    """
    y_hat = float(np.mean(weighted))
    if n_samples > 1:
        var_is = float(np.var(weighted, ddof=1))
    else:
        var_is = 0.0
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0
    re = se / abs(y_hat) if abs(y_hat) > 0 else float("inf")
    ci_lower = y_hat - 1.96 * se
    ci_upper = y_hat + 1.96 * se
    sum_eff = float(np.sum(weighted))
    sum_eff2 = float(np.sum(weighted * weighted))
    ess = (sum_eff * sum_eff) / sum_eff2 if sum_eff2 > 0 else 0.0
    ess_ratio = ess / n_failures if n_failures > 0 else 0.0
    var_mc_single = y_hat * (1.0 - y_hat)  # 单样本伯努利方差
    speedup = var_mc_single / var_is if var_is > 0 else float("inf")
    return y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup


def _check_yield_quality(
    n_failures: int,
    ess_ratio: float,
    re: float,
    min_ess_ratio: float,
) -> None:
    """诊断 IS 良率估计质量，退化即 raise（R261 内部辅助，R03 禁止 fall-back）。

    检查项目：
    1. 失效样本数 >= 30（CLT 近似成立）
    2. ESS/n_failures >= min_ess_ratio（权重不集中）
    3. 相对误差 RE <= 0.5（估计可靠）
    4. 边缘区间（ESS/n < 0.3 或 RE > 0.1）记 warning

    Args:
        n_failures: 失效样本数。
        ess_ratio: ESS/n_failures。
        re: 相对误差。
        min_ess_ratio: 最小 ESS/n 阈值。

    Raises:
        RuntimeError: 任一质量门禁未通过。
    """
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
            f"建议: 增大 n_samples 或改进偏置分布。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        logger.warning(
            "ESS/n_failures = %.4f, RE = %.4f 在边缘区间，建议改进偏置分布。",
            ess_ratio,
            re,
        )


def importance_sampling_yield(
    failure_region: Callable[[np.ndarray], bool],
    nominal_dist: list[dict],
    biasing: BiasingSpec,
    n_samples: int = 10000,
    seed: int | None = None,
    min_ess_ratio: float = 0.01,
) -> ImportanceSamplingResult:
    """重要性采样稀有事件良率估计（R261-R280）。

    使用偏置分布 ``q`` 偏向失效区域采样，并用似然比 ``W = f/q`` 修正权重，
    估计失效良率 ``Y = P(X ∈ A)``。当良率接近 1（失效稀有）时，相比朴素 MC
    可实现 10²-10⁴ 倍方差缩减。

    算法: 构造 f/q → 从 q 采 n 样本 → ``log W = log f - log q`` →
    评估 ``g(x) = 𝟙_A(x)`` → 加权良率 ``Ŷ = mean(g·exp(log W))`` →
    ``SE = std(g·W)/√n`` → ``Speedup = Y(1-Y)/Var_IS`` →
    ``ESS = (ΣW)²/ΣW²`` 退化即 raise。

    Args:
        failure_region: 失效区域指示函数 ``A: params -> bool``（True=失效）。
        nominal_dist: 标称分布规格 [{"type":"norm"|"uniform","loc":,"scale":}, ...]。
        biasing: 偏置分布构造规格（见 :class:`BiasingSpec`）。
        n_samples: 样本数（典型 10⁴-10⁵）；seed: 随机种子（可复现性）。
        min_ess_ratio: 最小 ESS/n 比，低于此值 raise 告警（防止权重退化）。

    Returns:
        ImportanceSamplingResult 含良率估计 + 统计诊断。

    Raises:
        ValueError: 参数无效。
        RuntimeError: 偏置分布支撑不足 / ESS 退化 / 评估失败。

    学术依据:
    - 似然比估计器: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    - 稀有事件综述: Juneja & Shahabuddin 2006 (Handbooks in OR&MS vol 13)
    - ESS 诊断: Kroese, Taimre & Botev 2011, DOI: 10.1002/9781118014967
    - 加速比: Glasserman 2003, Ch.4.1, DOI: 10.1007/978-0-387-21617-1

    合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
    """
    _validate_yield_params(nominal_dist, n_samples, min_ess_ratio)

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)
    q_dists = _construct_biasing_distribution(nominal_dist, biasing)

    # 1. 从 q 采样（MIXTURE 走混合采样分支）
    if biasing.method == BiasingMethod.MIXTURE:
        samples = _sample_mixture(
            f_dists, q_dists, biasing.mixture_alpha, n_samples, rng
        )
    else:
        samples = _sample_from_distributions(q_dists, n_samples, rng)

    # 2. 计算似然比与失效指示，加权得到 g·W
    log_w = _compute_log_weights(f_dists, q_dists, samples, biasing)
    weights = np.exp(log_w)
    failure_flags = _evaluate_failure_flags(
        failure_region, samples, "failure_region"
    )
    n_failures = int(np.sum(failure_flags))
    weighted = failure_flags.astype(float) * weights

    # 3. 计算统计量并执行质量诊断（退化即 raise，R03 禁止 fall-back）
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


def _validate_is_mean_params(d: int, n_samples: int, min_ess_ratio: float) -> None:
    """校验 importance_sampling_mean 输入参数（R628 Extract Method）。"""
    if d == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if not (0.0 < min_ess_ratio < 1.0):
        raise ValueError(f"min_ess_ratio 必须在 (0, 1)，得到 {min_ess_ratio}")


def _evaluate_g_values(
    func: Callable[[np.ndarray], float], samples: np.ndarray, n_samples: int
) -> np.ndarray:
    """评估性能函数 g(x) 并收集结果（R628 Extract Method）。

    Raises:
        RuntimeError: func 评估失败（禁止 fall-back）。
    """
    g_values = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        try:
            g_values[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
            ) from e
    return g_values


def _check_is_mean_reliability(
    ess_ratio: float, re: float, min_ess_ratio: float
) -> None:
    """检查 IS 估计可靠性（ESS 退化 + 相对误差，R628 Extract Method）。

    Raises:
        RuntimeError: ESS 退化或相对误差过大。
    """
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


def importance_sampling_mean(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    biasing: BiasingSpec,
    n_samples: int = 10000,
    seed: int | None = None,
    min_ess_ratio: float = 0.01,
) -> ImportanceSamplingResult:
    """重要性采样估计 ``E_f[g(X)]``（R261-R280）。

    与 :func:`importance_sampling_yield` 相同的算法，但目标量为
    ``E_f[g(X)]`` 而非 ``P(X ∈ A)``。适用于非指示函数的方差减少估计
    （如传输功率均值、波长漂移均值）。

    Args:
        func: 性能函数 ``g: params -> scalar``。
        nominal_dist: 标称分布规格列表。
        biasing: 偏置分布构造规格。
        n_samples: 样本数。
        seed: 随机种子。
        min_ess_ratio: 最小 ESS/n 比。

    Returns:
        ImportanceSamplingResult 含 ``yield_estimate = E_f[g(X)]`` 估计。

    Raises:
        ValueError: 参数无效。
        RuntimeError: 偏置分布支撑不足 / ESS 退化 / 评估失败。

    学术依据: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    """
    d = len(nominal_dist)
    _validate_is_mean_params(d, n_samples, min_ess_ratio)

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

    # 评估 g(x)
    g_values = _evaluate_g_values(func, samples, n_samples)

    weighted = g_values * weights
    mu_hat = float(np.mean(weighted))

    if n_samples > 1:
        var_is = float(np.var(weighted, ddof=1))
    else:
        var_is = 0.0
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0
    re = se / abs(mu_hat) if abs(mu_hat) > 0 else float("inf")

    ci_lower = mu_hat - 1.96 * se
    ci_upper = mu_hat + 1.96 * se

    # ESS 诊断: 标准 ESS 基于权重 W（衡量权重均匀性，不依赖 g 符号）。
    # R05 Bug 修复 v5.0-P2-R114: 原代码 ESS 基于 g·W，对带符号 g 误判退化。
    # 当 g 是带符号性能函数（如相位偏差、波长漂移可正可负）时，
    # Σ(g·W) 可能因正负抵消而 ≈0，导致 ESS≈0 误判退化，
    # 使本来可靠的估计被错误拒绝。
    # 修复: 改用标准 ESS 定义（基于 W，不依赖 g 符号）。
    # 注: importance_sampling_yield 的 ESS 基于 g·W=𝟙_A·W（g≥0）无此问题，保留。
    # 文献: Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo Methods",
    #   Ch.9, DOI: 10.1002/9781118014967
    sum_w = float(np.sum(weights))
    sum_w2 = float(np.sum(weights * weights))
    ess = (sum_w * sum_w) / sum_w2 if sum_w2 > 0 else 0.0
    ess_ratio = ess / n_samples if n_samples > 0 else 0.0

    _check_is_mean_reliability(ess_ratio, re, min_ess_ratio)

    # 加速比: 需要从 f 直接采样计算 Var_f(g) 才能对比，本函数不计算（无 f 采样）
    # 设为 NaN 表示"未计算"，调用方可通过两次调用（朴素 MC vs IS）自行对比
    speedup = float("nan")

    return ImportanceSamplingResult(
        yield_estimate=mu_hat,
        std_error=se,
        relative_error=re,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        effective_sample_size=ess,
        speedup_vs_mc=speedup,
        n_samples=n_samples,
        n_failures=0,  # 非良率场景，无失效计数
        n_evaluations=n_samples,
        biasing_method=biasing.method.value,
        log_weights=log_w,
        samples=samples,
        converged=None,
    )


def rare_event_yield(
    failure_region: Callable[[np.ndarray], bool],
    nominal_dist: list[dict],
    biasing_mean_shift: list[float],
    n_samples: int = 10000,
    seed: int | None = None,
) -> ImportanceSamplingResult:
    """稀有事件良率估计便捷接口（R261-R280）。

    使用 MEAN_SHIFT 偏置的便捷封装，参数最简：只需提供偏移方向
    ``biasing_mean_shift`` 即可估计失效良率。适合 PoLaRIS 良率分析的
    标准调用路径（与 :func:`verification.statistical_yield.calculate_yield`
    互补）。

    *创新*：PoLaRIS 差异化能力——商业工具（Calibre YieldOptimizer /
    Lumerical INTERCONNECT / Luceda Circuit Analyzer）均无稀有事件 IS。

    Args:
        failure_region: 失效区域指示函数。
        nominal_dist: 标称分布规格列表。
        biasing_mean_shift: 每维偏移量（朝失效区域方向）。
        n_samples: 样本数。
        seed: 随机种子。

    Returns:
        ImportanceSamplingResult 含良率估计。

    Raises:
        ValueError: 参数无效。
        RuntimeError: ESS 退化或评估失败。

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


__all__ = [
    "importance_sampling_yield",
    "importance_sampling_mean",
    "rare_event_yield",
]
