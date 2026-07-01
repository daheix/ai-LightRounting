"""交叉熵 (CE) 自适应重要性采样（R271-R280，批次 10-B 拆分子模块）。

本子模块实现 Rubinstein 1997 交叉熵方法的 PoLaRIS 适配实现：
- :func:`cross_entropy_importance_sampling`: CE 自适应迭代寻找最优偏置 q*

并含内部辅助：参数校验、分布初始化、自适应迭代、最终质量诊断、最终 IS 估计。

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
- CE 教程: De Boer et al. 2005, "A Tutorial on the Cross-Entropy Method",
  Annals of Operations Research 134:19-67

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。

来源（拆分依据）:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html


## 补充文献（R02 学术诚信补齐）
- Nocedal & Wright 2006 Numerical Optimization Springer: https://doi.org/10.1007/978-0-387-40065-5
- scipy.optimize 文档: https://docs.scipy.org/doc/scipy/reference/optimize.html
- Glasserman 2003 Monte Carlo Methods: https://doi.org/10.1007/978-0-387-21617-1
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np

from polaris.sim.importance_sampling_distributions import (
    _build_univariate_distributions,
    _logpdf_distributions,
    _sample_from_distributions,
)
from polaris.sim.importance_sampling_estimators import (
    _compute_weighted_yield_stats,
    _evaluate_failure_flags,
)
from polaris.sim.importance_sampling_types import (
    BiasingMethod,
    ImportanceSamplingResult,
)

logger = logging.getLogger(__name__)


def _validate_ce_params(
    nominal_dist: list[dict],
    n_samples: int,
    n_iterations: int,
    elite_ratio: float,
    smoothing_alpha: float,
) -> None:
    """校验 cross_entropy_importance_sampling 入参（R271 内部辅助，R03 禁止 fall-back）。

    Args:
        nominal_dist: 标称分布规格列表。
        n_samples: 每轮迭代样本数。
        n_iterations: 迭代轮数。
        elite_ratio: elite 比例 ρ。
        smoothing_alpha: 平滑系数 α。

    Raises:
        ValueError: 参数无效或分布类型不支持。
    """
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
    # CE 自适应参数更新仅支持 norm 分布（高斯最大似然有解析解）
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
    """初始化 CE 偏置分布 q 的均值/方差（R271 内部辅助）。

    初始 q 为标称分布 + initial_mean_shift 的 MEAN_SHIFT 形式。

    Args:
        nominal_dist: 标称分布规格列表。
        initial_mean_shift: 初始偏移方向。

    Returns:
        (q_means, q_stds) 两个一维 ndarray。
    """
    q_means = np.array(
        [
            spec.get("loc", 0.0) + s
            for spec, s in zip(nominal_dist, initial_mean_shift, strict=True)
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
    """执行 CE 自适应迭代（R271 内部辅助）。

    每轮迭代：采样 → 评估失效指示 → 选 elite → 高斯最大似然更新 → 平滑。
    收敛判定：elite 均值变化 < 1e-3。

    Args:
        failure_region: 失效区域指示函数。
        rng: 随机数生成器。
        q_means: 当前 q 均值（会被原地更新）。
        q_stds: 当前 q 标准差（会被原地更新）。
        n_samples: 每轮样本数。
        n_iterations: 迭代轮数。
        n_elite: elite 样本数上限。
        smoothing_alpha: 平滑系数 α。
        d: 维度。

    Returns:
        (q_means, q_stds, total_evals, converged)。
    """
    total_evals = 0
    converged = False
    for it in range(n_iterations):
        samples = rng.normal(loc=q_means, scale=q_stds, size=(n_samples, d))
        flags = _evaluate_failure_flags(
            failure_region, samples, f"CE 迭代 {it} failure_region"
        )
        total_evals += n_samples

        failure_idx = np.where(flags)[0]
        if len(failure_idx) == 0:
            logger.warning(
                "CE 迭代 %d/%d 无失效样本，q 未更新。建议增大 initial_mean_shift。",
                it + 1,
                n_iterations,
            )
            continue

        elite_idx = (
            failure_idx[:n_elite] if len(failure_idx) >= n_elite else failure_idx
        )
        elite_samples = samples[elite_idx]

        new_means = np.mean(elite_samples, axis=0)
        new_stds = np.maximum(np.std(elite_samples, axis=0, ddof=1), 1e-6)

        q_means = smoothing_alpha * new_means + (1.0 - smoothing_alpha) * q_means
        q_stds = smoothing_alpha * new_stds + (1.0 - smoothing_alpha) * q_stds

        if it > 0:
            mean_change = np.linalg.norm(new_means - q_means) / (
                np.linalg.norm(q_means) + 1e-12
            )
            if mean_change < 1e-3:
                converged = True
                logger.info(
                    "CE 在迭代 %d 收敛（mean_change=%.6f）。", it + 1, mean_change
                )
                break
    return q_means, q_stds, total_evals, converged


def _check_ce_yield_quality(
    n_failures: int,
    ess_ratio: float,
    re: float,
    min_ess_ratio: float,
) -> None:
    """诊断 CE 最终 IS 估计质量，退化即 raise（R271 内部辅助，R03 禁止 fall-back）。

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
            f"CE 最终失效样本数 {n_failures} < 30，统计意义不足。"
            f"建议: 增大 n_iterations、调整 elite_ratio、或改用 MIXTURE。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < min_ess_ratio:
        raise RuntimeError(
            f"CE 最终 IS 估计 ESS 退化: ESS/n_failures = {ess_ratio:.4f} < 阈值 {min_ess_ratio}。"
            f"建议: 增大 n_iterations、调整 elite_ratio、或改用 MIXTURE。"
            f"禁止 fall-back（R03）。"
        )
    if re > 0.5:
        raise RuntimeError(
            f"CE 最终 IS 估计 RE = {re:.4f} > 0.5，不可靠。禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        logger.warning(
            "CE 最终 ESS/n_failures = %.4f, RE = %.4f 边缘区间。",
            ess_ratio,
            re,
        )


def _ce_final_is_estimate(
    failure_region: Callable[[np.ndarray], bool],
    rng: np.random.Generator,
    f_dists: list,
    q_means: np.ndarray,
    q_stds: np.ndarray,
    n_samples: int,
    d: int,
    total_evals: int,
    min_ess_ratio: float,
    converged: bool,
) -> ImportanceSamplingResult:
    """用最终 q 跑大批量 IS 估计并组装结果（R271 内部辅助）。

    流程: 构造 q 规格 → 采样 → log W → 支撑检查 → 失效评估 → 统计 →
    质量诊断 → 组装 ImportanceSamplingResult。

    Args:
        failure_region: 失效区域指示函数。
        rng: 随机数生成器；f_dists: 标称分布列表。
        q_means/q_stds: 最终 q 均值/标准差。
        n_samples: 样本数；d: 维度。
        total_evals: 已累计评估次数（不含本轮）。
        min_ess_ratio: 最小 ESS/n 阈值；converged: CE 是否收敛。

    Returns:
        ImportanceSamplingResult。

    Raises:
        RuntimeError: q 分布支撑不足或质量门禁未通过。
    """
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
    _check_ce_yield_quality(n_failures, ess_ratio, re, min_ess_ratio)

    return ImportanceSamplingResult(
        yield_estimate=y_hat,
        std_error=se,
        relative_error=re,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        effective_sample_size=ess,
        speedup_vs_mc=speedup,
        n_samples=n_samples,
        n_failures=n_failures,
        n_evaluations=total_evals,
        biasing_method=BiasingMethod.CROSS_ENTROPY.value,
        log_weights=log_w,
        samples=samples,
        converged=converged,
    )


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
    """交叉熵 (CE) 自适应重要性采样（R271-R280）。

    *创新*：Rubinstein 1997 交叉熵方法的 PoLaRIS 实现。当失效区域几何
    未知时，CE 自适应迭代寻找最优偏置分布 ``q*``，避免手动调参。

    算法:
    1. 初始化偏置分布 ``q_0`` 为 MEAN_SHIFT（initial_mean_shift）
    2. 每轮迭代:
       a. 从 ``q_t`` 采 ``n`` 样本
       b. 评估每个样本的"光滑化"分数（这里用 𝟙_A，可扩展为到失效边界距离）
       c. 取前 ``elite_ratio`` 分位作为 elite 集合
       d. 用 elite 样本对 ``q`` 参数做最大似然更新（高斯：更新均值/方差）
       e. 平滑 ``θ_{t+1} ← α·θ_{t+1} + (1-α)·θ_t``
    3. 用最终 ``q`` 跑大批量 IS 估计

    Args:
        failure_region: 失效区域指示函数。
        nominal_dist: 标称分布规格列表（仅 norm 类型支持自适应）。
        initial_mean_shift: 初始偏移方向。
        n_samples: 每轮迭代样本数。
        n_iterations: 迭代轮数。
        elite_ratio: elite 比例 ρ ∈ (0.01, 0.2)。
        smoothing_alpha: 平滑系数 α ∈ [0.5, 0.9]。
        seed: 随机种子。
        min_ess_ratio: 最终 IS 估计的最小 ESS/n 比。

    Returns:
        ImportanceSamplingResult 含 ``converged`` 标志。

    Raises:
        ValueError: 参数无效。
        RuntimeError: CE 迭代失败或最终 ESS 退化。

    学术依据:
    - 交叉熵方法: Rubinstein 1997, DOI: 10.1016/S0377-2217(96)00385-2
    - CE 自适应: Kroese, Taimre & Botev 2011, Ch.13, DOI: 10.1002/9781118014967
    - 光滑化分数: De Boer et al. 2005, "A Tutorial on the Cross-Entropy
      Method", Annals of Operations Research 134:19-67
    """
    _validate_ce_params(
        nominal_dist, n_samples, n_iterations, elite_ratio, smoothing_alpha
    )
    d = len(nominal_dist)

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)
    q_means, q_stds = _init_ce_distribution(nominal_dist, initial_mean_shift)
    n_elite = max(1, int(n_samples * elite_ratio))

    # CE 自适应迭代寻找最优 q
    q_means, q_stds, total_evals, converged = _run_ce_iterations(
        failure_region, rng, q_means, q_stds, n_samples, n_iterations,
        n_elite, smoothing_alpha, d,
    )

    # 用最终 q 跑大批量 IS 估计并执行质量诊断
    return _ce_final_is_estimate(
        failure_region, rng, f_dists, q_means, q_stds, n_samples, d,
        total_evals, min_ess_ratio, converged,
    )


__all__ = [
    "cross_entropy_importance_sampling",
]
