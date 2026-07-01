"""重要性采样分布构造与采样辅助（R261-R270，批次 10-B 拆分子模块）。

本子模块提供偏置分布的构造、采样、log 密度计算与似然比计算等内部辅助函数：
- :func:`_build_univariate_distributions`: 从规格构建一元 SciPy 分布
- :func:`_sample_from_distributions`: 从一元分布列表独立采样
- :func:`_logpdf_distributions`: 多元独立分布对数密度
- :func:`_construct_biasing_distribution`: 按 BiasingSpec 构造偏置分布
- :func:`_sample_mixture`: 混合分布采样 q = (1-α)f + α·h
- :func:`_logpdf_mixture`: 混合分布对数密度
- :func:`_compute_log_weights`: 计算对数似然比 log W = log f - log q

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

import numpy as np
from scipy.special import logsumexp
from scipy.stats import norm, uniform

from polaris.sim.importance_sampling_types import BiasingMethod, BiasingSpec


def _build_univariate_distributions(
    specs: list[dict],
) -> list[norm | uniform]:
    """从规格列表构建一元 SciPy 分布对象列表（R261 内部辅助）。

    Args:
        specs: 分布规格 [{"type":"norm"|"uniform","loc":,"scale":}, ...]。

    Returns:
        SciPy 冻结分布对象列表（带 rvs/logpdf 方法）。

    Raises:
        ValueError: 不支持的分布类型或缺少参数。

    学术依据: SciPy stats 冻结分布 API
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_continuous.html
    """
    dists: list[norm | uniform] = []
    for i, spec in enumerate(specs):
        dist_type = spec.get("type", "")
        if dist_type == "norm":
            dists.append(norm(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0)))
        elif dist_type == "uniform":
            dists.append(
                uniform(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
            )
        else:
            raise ValueError(
                f"分布规格[{i}] 类型 '{dist_type}' 不支持。支持: 'norm', 'uniform'。"
                f"规格: {spec}"
            )
    return dists


def _sample_from_distributions(
    dists: list[norm | uniform],
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """从一元分布列表独立采样（R261 内部辅助）。

    Args:
        dists: SciPy 冻结分布对象列表（每维一个）。
        n_samples: 样本数。
        rng: NumPy 随机数生成器。

    Returns:
        样本数组 (n_samples, d)。
    """
    d = len(dists)
    samples = np.empty((n_samples, d), dtype=float)
    for j in range(d):
        samples[:, j] = dists[j].rvs(size=n_samples, random_state=rng)
    return samples


def _logpdf_distributions(
    dists: list[norm | uniform],
    x: np.ndarray,
) -> np.ndarray:
    """计算多元独立分布的对数密度（R261 内部辅助）。

    log f(x) = Σⱼ log fⱼ(xⱼ)（独立性假设）。

    Args:
        dists: SciPy 冻结分布对象列表。
        x: 样本数组 (n_samples, d)。

    Returns:
        log 密度数组 (n_samples,)。
    """
    x = np.asarray(x, dtype=float)
    n = x.shape[0]
    log_p = np.zeros(n, dtype=float)
    for j in range(len(dists)):
        log_p += dists[j].logpdf(x[:, j])
    return log_p


def _construct_biasing_distribution(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """根据偏置规格构造偏置分布列表（R261-R270，dispatch + Extract Method）。

    对每个一元标称分布，按 ``biasing.method`` 构造对应的偏置分布:
    - MEAN_SHIFT: loc += mean_shift[j]
    - VARIANCE_SCALING: scale *= variance_scale[j]
    - EXPONENTIAL_TWIST: 对 norm 退化为 MEAN_SHIFT，μ_shift = σ²·θ
    - MIXTURE: 在 _logpdf_mixture / _sample_mixture 中单独处理
    - CROSS_ENTROPY: 在 importance_sampling_yield 中自适应迭代

    Args:
        nominal_specs: 标称分布规格列表。
        biasing: 偏置规格。

    Returns:
        偏置分布对象列表（MIXTURE/CROSS_ENTROPY 返回 h 分量）。

    Raises:
        ValueError: 偏置参数缺失或无效。
    """
    method = biasing.method
    if method == BiasingMethod.MEAN_SHIFT:
        return _construct_mean_shift(nominal_specs, biasing)
    if method == BiasingMethod.VARIANCE_SCALING:
        return _construct_variance_scaling(nominal_specs, biasing)
    if method == BiasingMethod.EXPONENTIAL_TWIST:
        return _construct_exponential_twist(nominal_specs, biasing)
    if method == BiasingMethod.MIXTURE:
        _validate_mixture_params(biasing, len(nominal_specs))
        return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)
    if method == BiasingMethod.CROSS_ENTROPY:
        _validate_cross_entropy_params(biasing, len(nominal_specs))
        return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)
    raise ValueError(f"不支持的偏置方法: {method}")


def _build_shifted_specs_as_dists(
    nominal_specs: list[dict],
    mean_shift: list[float] | None,
) -> list[norm | uniform]:
    """构造 loc += mean_shift[j] 的偏置分布列表（MEAN_SHIFT / MIXTURE / CROSS_ENTROPY 共用）。"""
    h_specs: list[dict] = []
    for j, spec in enumerate(nominal_specs):
        shift = float(mean_shift[j])
        new_spec = dict(spec)
        new_spec["loc"] = spec.get("loc", 0.0) + shift
        h_specs.append(new_spec)
    return _build_univariate_distributions(h_specs)


def _construct_mean_shift(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """构造 MEAN_SHIFT 偏置分布。"""
    d = len(nominal_specs)
    if biasing.mean_shift is None or len(biasing.mean_shift) != d:
        raise ValueError(
            f"MEAN_SHIFT 需要 mean_shift 长度 = {d}，"
            f"得到 {biasing.mean_shift}"
        )
    return _build_shifted_specs_as_dists(nominal_specs, biasing.mean_shift)


def _construct_variance_scaling(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """构造 VARIANCE_SCALING 偏置分布。"""
    d = len(nominal_specs)
    if biasing.variance_scale is None or len(biasing.variance_scale) != d:
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


def _construct_exponential_twist(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """构造 EXPONENTIAL_TWIST 偏置分布。

    - norm: q_θ = N(μ + σ²θ, σ)（Siegmund 1976, Glasserman 2003 Ch.4.4）
    - uniform: 退化为 loc += θ（工程近似，严格形式需数值求解）
    """
    d = len(nominal_specs)
    if biasing.twist_theta is None or len(biasing.twist_theta) != d:
        raise ValueError(
            f"EXPONENTIAL_TWIST 需要 twist_theta 长度 = {d}，"
            f"得到 {biasing.twist_theta}"
        )
    biasing_specs: list[dict] = []
    for j, spec in enumerate(nominal_specs):
        theta = float(biasing.twist_theta[j])
        biasing_specs.append(_twist_single_spec(spec, theta))
    return _build_univariate_distributions(biasing_specs)


def _twist_single_spec(spec: dict, theta: float) -> dict:
    """对单个标称分布规格应用指数扭转 θ（norm/uniform 两种支持类型）。"""
    dist_type = spec.get("type", "")
    if dist_type == "norm":
        # 指数扭转对正态: q_θ = N(μ + σ²θ, σ)
        # 来源: Siegmund 1976, Glasserman 2003 Ch.4.4
        mu = spec.get("loc", 0.0)
        sigma = spec.get("scale", 1.0)
        return {"type": "norm", "loc": mu + sigma * sigma * theta, "scale": sigma}
    if dist_type == "uniform":
        # 指数扭转对均匀分布无解析均值平移；退化为均值平移（loc += θ）
        # 这是工程近似，对均匀分布的指数扭转严格形式需数值求解
        new_spec = dict(spec)
        new_spec["loc"] = spec.get("loc", 0.0) + theta
        return new_spec
    raise ValueError(
        f"EXPONENTIAL_TWIST 不支持分布类型 '{dist_type}'"
    )


def _validate_mixture_params(biasing: BiasingSpec, d: int) -> None:
    """校验 MIXTURE 偏置参数（mean_shift 长度 + mixture_alpha 范围）。"""
    if biasing.mean_shift is None or len(biasing.mean_shift) != d:
        raise ValueError(
            f"MIXTURE 需要 mean_shift 长度 = {d}，"
            f"得到 {biasing.mean_shift}"
        )
    if not (0.0 < biasing.mixture_alpha < 1.0):
        raise ValueError(
            f"mixture_alpha 必须在 (0, 1)，得到 {biasing.mixture_alpha}"
        )


def _validate_cross_entropy_params(biasing: BiasingSpec, d: int) -> None:
    """校验 CROSS_ENTROPY 偏置参数（mean_shift / elite_ratio / n_iterations）。"""
    if biasing.mean_shift is None or len(biasing.mean_shift) != d:
        raise ValueError(
            f"CROSS_ENTROPY 需要 mean_shift 作为初始 h 长度 = {d}，"
            f"得到 {biasing.mean_shift}"
        )
    if not (0.0 < biasing.elite_ratio < 1.0):
        raise ValueError(
            f"elite_ratio 必须在 (0, 1)，得到 {biasing.elite_ratio}"
        )
    if biasing.n_iterations < 1:
        raise ValueError(
            f"n_iterations 必须 >= 1，得到 {biasing.n_iterations}"
        )


def _sample_mixture(
    f_dists: list[norm | uniform],
    h_dists: list[norm | uniform],
    alpha: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """从混合分布 q = (1-α)f + α·h 采样（R261 内部辅助）。

    Args:
        f_dists: 标称分布列表。
        h_dists: 偏置分布列表（h 分量）。
        alpha: 混合权重 α。
        n_samples: 样本数。
        rng: 随机数生成器。

    Returns:
        样本数组 (n_samples, d)。

    学术依据: Heidelberger 1995, DOI: 10.1145/270261.270264
    """
    # 每个 sample 以概率 α 来自 h，1-α 来自 f
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
    """计算混合分布 q = (1-α)f + α·h 的对数密度（R261 内部辅助）。

    log q(x) = logsumexp(log(1-α) + log f(x), log(α) + log h(x))

    Args:
        f_dists: 标称分布列表。
        h_dists: 偏置分布列表（h 分量）。
        alpha: 混合权重 α。
        x: 样本数组 (n_samples, d)。

    Returns:
        log 密度数组 (n_samples,)。
    """
    log_f = _logpdf_distributions(f_dists, x)
    log_h = _logpdf_distributions(h_dists, x)
    # log q = logsumexp(log(1-α)+log_f, log(α)+log_h)
    log_alpha = np.log(alpha)
    log_1_alpha = np.log(1.0 - alpha)
    # 堆叠为 (2, n) 用 logsumexp 沿 axis=0
    stacked = np.vstack([log_1_alpha + log_f, log_alpha + log_h])
    return logsumexp(stacked, axis=0)


def _compute_log_weights(
    nominal_dists: list[norm | uniform],
    biasing_dists: list[norm | uniform],
    samples: np.ndarray,
    biasing: BiasingSpec,
) -> np.ndarray:
    """计算 log 似然比 log W = log f(x) - log q(x)（R261 内部辅助）。

    对 MEAN_SHIFT / VARIANCE_SCALING / EXPONENTIAL_TWIST:
        log W = log f(x) - log q(x)
    对 MIXTURE:
        log W = log f(x) - log((1-α)f(x) + α·h(x))

    Args:
        nominal_dists: 标称分布列表。
        biasing_dists: 偏置分布列表。
        samples: 样本数组 (n_samples, d)。
        biasing: 偏置规格。

    Returns:
        log 似然比数组 (n_samples,)。
    """
    log_f = _logpdf_distributions(nominal_dists, samples)
    if biasing.method == BiasingMethod.MIXTURE:
        log_q = _logpdf_mixture(
            nominal_dists, biasing_dists, biasing.mixture_alpha, samples
        )
    else:
        log_q = _logpdf_distributions(biasing_dists, samples)
    log_w = log_f - log_q
    # 数值稳定性: 检查 q 撑不足（log_q = -inf 但 log_f 有限 → 违反绝对连续条件）
    bad_mask = np.isinf(log_w) & (log_w < 0) & np.isfinite(log_f)
    if np.any(bad_mask):
        n_bad = int(np.sum(bad_mask))
        raise RuntimeError(
            f"偏置分布支撑未覆盖失效区域: {n_bad} 个样本 q.pdf(x)=0 但 f.pdf(x)>0。"
            f"绝对连续条件违反。禁止 fall-back（R03）。"
            f"建议增大 mean_shift 或使用 MIXTURE。"
        )
    return log_w


__all__ = [
    "_build_univariate_distributions",
    "_sample_from_distributions",
    "_logpdf_distributions",
    "_construct_biasing_distribution",
    "_sample_mixture",
    "_logpdf_mixture",
    "_compute_log_weights",
]
