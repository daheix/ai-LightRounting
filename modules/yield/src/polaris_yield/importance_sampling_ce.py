"""交叉熵 (CE) 自适应重要性采样（polaris-yield 子模块）。

从 v4 ``polaris.sim.importance_sampling_cross_entropy`` 迁移；
R13 不保留 v4 兼容路径。从 importance_sampling.py 拆分以符合
"文件 ≤800 行" 质量门禁（AGENTS.md §8）。

## 核心功能

``cross_entropy_importance_sampling``: CE 自适应迭代寻找最优偏置 q*

## 算法

1. 初始化偏置分布 q_0 为 MEAN_SHIFT（initial_mean_shift）
2. 每轮迭代:
   a. 从 q_t 采 n 样本
   b. 评估失效指示 𝟙_A(x)
   c. 取失效样本前 elite_ratio 作为 elite 集合
   d. 用 elite 样本对 q 做高斯最大似然更新（均值/方差）
   e. 平滑 θ_{t+1} ← α·θ_{t+1} + (1-α)·θ_t
3. 用最终 q 跑大批量 IS 估计，质量诊断（退化即 raise，R03）

## 学术依据（R02 学术诚信，≥5 文献 URL）

- 交叉熵方法: Rubinstein 1997, "Optimization of computer simulation
  models with rare events", European J. Oper. Res. 99:89-112,
  https://doi.org/10.1016/S0377-2217(96)00385-2
- CE 自适应: Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo
  Methods", Wiley Ch.13, https://doi.org/10.1002/9781118014967
- CE 教程: De Boer et al. 2005, "A Tutorial on the Cross-Entropy
  Method", Annals of Operations Research 134:19-67
- 似然比估计器: Glynn & Iglehart 1989,
  https://doi.org/10.1287/mnsc.35.11.1367
- 稀有事件综述: Heidelberger 1995,
  https://doi.org/10.1145/270261.270264
- 大偏差理论: Bucklew 2004, "Introduction to Rare Event Simulation",
  Springer, https://doi.org/10.1007/b97468
- 现代教科书: Asmussen & Glynn 2007,
  https://doi.org/10.1007/978-0-387-69033-9
- 光子学良率: Bogaerts et al. 2018,
  https://fib.intec.ugent.be/download/pub_4125.pdf

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np

from polaris_yield.importance_sampling import (
    BiasingMethod,
    ImportanceSamplingResult,
    _build_univariate_distributions,
    _compute_weighted_yield_stats,
    _evaluate_failure_flags,
    _logpdf_distributions,
    _sample_from_distributions,
)

logger = logging.getLogger(__name__)


def _validate_ce_params(
    nominal_dist: list[dict],
    n_samples: int,
    n_iterations: int,
    elite_ratio: float,
    smoothing_alpha: float,
) -> None:
    """校验 cross_entropy_importance_sampling 入参（R03 禁止 fall-back）。

    Raises:
        ValueError: 参数无效或分布类型不支持（CE 仅支持 norm）。
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
    """初始化 CE 偏置分布 q 的均值/方差。

    初始 q 为标称分布 + initial_mean_shift 的 MEAN_SHIFT 形式。
    """
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

    Returns:
        (q_means, q_stds, total_evals, converged)。
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


def _run_ce_final_is_estimation(
    failure_region: Callable[[np.ndarray], bool],
    f_dists: list,
    q_means: np.ndarray,
    q_stds: np.ndarray,
    n_samples: int,
    rng: np.random.Generator,
    d: int,
) -> dict:
    """运行 CE 最终 IS 估计，返回统计结果 dict（含 y_hat/se/re/ess 等）。"""
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
    n_failures = int(np.sum(flags))
    weighted = flags.astype(float) * weights
    (y_hat, se, re, ci_lower, ci_upper, ess, ess_ratio, speedup) = (
        _compute_weighted_yield_stats(weighted, n_samples, n_failures)
    )
    return {
        "samples": samples, "log_w": log_w, "n_failures": n_failures,
        "y_hat": y_hat, "se": se, "re": re, "ci_lower": ci_lower,
        "ci_upper": ci_upper, "ess": ess, "ess_ratio": ess_ratio,
        "speedup": speedup,
    }


def _check_ce_final_quality(is_data: dict, min_ess_ratio: float) -> None:
    """CE 最终质量诊断（退化即 raise，R03 禁止 fall-back）。"""
    n_failures = is_data["n_failures"]
    ess_ratio = is_data["ess_ratio"]
    re = is_data["re"]
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
            ess_ratio, re,
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
    """交叉熵 (CE) 自适应重要性采样。

    *创新*：Rubinstein 1997 交叉熵方法的 PoLaRIS 实现。当失效区域几何
    未知时，CE 自适应迭代寻找最优偏置分布 q*，避免手动调参。
    底层逻辑：每轮采 n 样本 → 选 elite(失效前 ρ 分位) → 高斯最大似然
    更新 q → 平滑 θ_{t+1}←α·θ_{t+1}+(1-α)·θ_t → 用最终 q 跑 IS。
    支持理论：Rubinstein 1997 + De Boer et al. 2005 CE 教程 +
    Kroese, Taimre & Botev 2011 Ch.13。
    案例：应用于 PoLaRIS 稀有事件良率，见 操作记录.md。

    Args:
        failure_region: 失效区域指示函数 A: params -> bool（True=失效）。
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

    is_data = _run_ce_final_is_estimation(
        failure_region, f_dists, q_means, q_stds, n_samples, rng, d
    )
    total_evals += n_samples
    _check_ce_final_quality(is_data, min_ess_ratio)
    return ImportanceSamplingResult(
        yield_estimate=is_data["y_hat"], std_error=is_data["se"],
        relative_error=is_data["re"], ci_lower=is_data["ci_lower"],
        ci_upper=is_data["ci_upper"], effective_sample_size=is_data["ess"],
        speedup_vs_mc=is_data["speedup"], n_samples=n_samples,
        n_failures=is_data["n_failures"], n_evaluations=total_evals,
        biasing_method=BiasingMethod.CROSS_ENTROPY.value,
        log_weights=is_data["log_w"], samples=is_data["samples"],
        converged=converged,
    )


__all__ = [
    "cross_entropy_importance_sampling",
]
