"""重要性采样 (Importance Sampling, IS) 用于稀有事件良率估计（R261-R280）。

本模块为 PoLaRIS 引入稀有事件仿真 (Rare-Event Simulation) 能力，补齐与商业
工具（Calibre YieldOptimizer / Mentor Pompeii / Synopsys CustomSim /
Lumerical INTERCONNECT / Luceda Circuit Analyzer）的核心差距：**真正的稀有
事件方差减少**。当良率接近 99.999% 时，朴素 MC 需 10⁹ 样本才能采到失效事件，
IS 通过偏置分布 (biasing distribution) 把采样质量压向失效区域，并用似然比
(likelihood ratio) 修正权重，实现 10²–10⁴ 倍方差缩减。

## 核心理论

设标称（工艺）分布为 ``f(x)``，失效区域为 ``A``，目标良率 ``Y = P(X ∈ A)``。
引入偏置分布 ``q(x)``（要求 ``q(x)>0`` 当 ``f(x)>0`` 且 ``x∈A``），则：

    Y = E_f[𝟙_A(X)] = E_q[𝟙_A(X) · W(X)],   W(X) = f(X)/q(X)

其中 ``W(X)`` 为似然比。IS 估计器（无偏）：

    Ŷ_IS = (1/n) Σᵢ 𝟙_A(Xᵢ) · W(Xᵢ),   Xᵢ ~ q

## 偏置分布构造方法

1. **均值平移 (MEAN_SHIFT)**: ``q(x) = f(x - μ_shift)``，对高斯退化为
   ``N(μ+μ_shift, Σ)``。
2. **方差放大 (VARIANCE_SCALING)**: ``q(x) = f(x/σ_s)/σ_s``，加厚尾部。
3. **指数扭转 (EXPONENTIAL_TWIST)**: ``q_θ(x) ∝ exp(θᵀx)·f(x)``，
   Siegmund 1976 鞍点法，对和过程失效渐近最优。
4. **混合分布 (MIXTURE)**: ``q(x) = (1-α)f(x) + α·h(x)``，最稳健默认选择。
5. **交叉熵 (CROSS_ENTROPY)**: Rubinstein 1997 自适应迭代寻找最优 ``q``。

## 数值稳定性

- 全程 log 域计算似然比: ``log W = log f(x) - log q(x)``
- 用 ``scipy.special.logsumexp`` 做加权求和
- 强制 ESS 诊断: ``ESS = (ΣW)²/ΣW²``，退化即 raise（R03 禁止 fall-back）

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
# 枚举与数据类
# ============================================================================


class BiasingMethod(Enum):
    """偏置分布构造方法（R261-R270）。

    对标商业工具的稀有事件能力（多数商业工具无 IS，PoLaRIS 为差异化能力）：
    - Calibre YieldOptimizer: LHS + 失效边界搜索，无似然比修正
    - Lumerical INTERCONNECT: layout-aware MC，无稀有事件 IS
    - Luceda Circuit Analyzer: MC + Corner + QMC，无 IS

    来源: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    """

    MEAN_SHIFT = "mean_shift"  # 均值平移 f(x-μ_shift)
    VARIANCE_SCALING = "variance_scaling"  # 方差放大 f(x/σ_s)/σ_s
    EXPONENTIAL_TWIST = "exponential_twist"  # 指数扭转 q_θ(x) ∝ exp(θᵀx)f(x)
    MIXTURE = "mixture"  # 混合分布 (1-α)f + α·h
    CROSS_ENTROPY = "cross_entropy"  # 交叉熵自适应 (Rubinstein 1997)


@dataclass
class BiasingSpec:
    """偏置分布构造规格（R261-R270）。

    根据 ``method`` 选择对应的偏置参数。未使用的字段保持 None。

    Attributes:
        method: 偏置方法（见 :class:`BiasingMethod`）。
        mean_shift: MEAN_SHIFT / MIXTURE 用，每维偏移量 list[float]（长度 = d）。
            正值朝正方向偏置，负值朝负方向。
        variance_scale: VARIANCE_SCALING 用，每维缩放因子 list[float]（>1 放大）。
        twist_theta: EXPONENTIAL_TWIST 用，每维扭转参数 θ list[float]。
            对正态分布退化为均值平移 μ_shift = σ²·θ。
        mixture_alpha: MIXTURE 用，混合权重 α ∈ (0, 1)（典型 0.1-0.5）。
            ``q = (1-α)·f + α·h``，h 由 ``mean_shift`` 构造均值平移高斯。
        elite_ratio: CROSS_ENTROPY 用，elite 比例 ρ ∈ (0.01, 0.2)。
        n_iterations: CROSS_ENTROPY 用，自适应迭代次数（典型 5-10）。
        smoothing_alpha: CROSS_ENTROPY 用，参数平滑系数 ∈ [0.5, 0.9]。

    学术依据:
    - 均值平移/方差放大: Glasserman 2003, Ch.4.2-4.3
    - 指数扭转: Siegmund 1976, DOI: 10.1214/aos/1176343542
    - 混合分布: Heidelberger 1995, DOI: 10.1145/270261.270264
    - 交叉熵: Rubinstein 1997, DOI: 10.1016/S0377-2217(96)00385-2
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
    """重要性采样估计结果（R261-R280）。

    Attributes:
        yield_estimate: 良率估计 Ŷ_IS = mean(𝟙_A · W)。
        std_error: 标准误差 SE = σ̂_IS / √n。
        relative_error: 相对误差 RE = SE / |Ŷ|。BRE (Bounded Relative Error)
            是稀有事件 IS 算法优劣的理论判据。
        ci_lower: 95% 置信区间下界（正态近似 Ŷ ± 1.96·SE）。
        ci_upper: 95% 置信区间上界。
        effective_sample_size: 有效样本大小 ESS = (ΣW)²/ΣW²。
            ESS/n > 0.5 良好；< 0.1 退化（应告警）。
        speedup_vs_mc: 与朴素 MC 方差缩减比 = Var_MC / Var_IS。
            > 1 表示 IS 有效；典型值 10²-10⁴。
        n_samples: 实际样本数。
        n_failures: 失效样本数（诊断用）。
        n_evaluations: 总模型评估次数（= n_samples × n_iterations for CE）。
        biasing_method: 偏置方法名字符串。
        log_weights: log 似然比数组 log W_i（诊断/重用）。
        samples: 采样数组 (n_samples, d)（诊断/可视化用）。
        converged: CROSS_ENTROPY 自适应收敛标志；其他方法为 None。

    学术依据:
    - RE / BRE: Juneja & Shahabuddin 2006 (Handbooks in OR&MS vol 13)
    - ESS: Kroese, Taimre & Botev 2011, DOI: 10.1002/9781118014967
    - 加速比: Glasserman 2003, Ch.4.1
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
# 内部辅助: 分布构造与采样
# ============================================================================


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


# ============================================================================
# 内部辅助: 偏置分布构造
# ============================================================================


def _construct_biasing_distribution(
    nominal_specs: list[dict],
    biasing: BiasingSpec,
) -> list[norm | uniform]:
    """根据偏置规格构造偏置分布列表（R261-R270）。

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
    d = len(nominal_specs)
    method = biasing.method

    if method == BiasingMethod.MEAN_SHIFT:
        if biasing.mean_shift is None or len(biasing.mean_shift) != d:
            raise ValueError(
                f"MEAN_SHIFT 需要 mean_shift 长度 = {d}，"
                f"得到 {biasing.mean_shift}"
            )
        biasing_specs: list[dict] = []
        for j, spec in enumerate(nominal_specs):
            shift = float(biasing.mean_shift[j])
            new_spec = dict(spec)
            new_spec["loc"] = spec.get("loc", 0.0) + shift
            biasing_specs.append(new_spec)
        return _build_univariate_distributions(biasing_specs)

    if method == BiasingMethod.VARIANCE_SCALING:
        if biasing.variance_scale is None or len(biasing.variance_scale) != d:
            raise ValueError(
                f"VARIANCE_SCALING 需要 variance_scale 长度 = {d}，"
                f"得到 {biasing.variance_scale}"
            )
        biasing_specs = []
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
            dist_type = spec.get("type", "")
            if dist_type == "norm":
                # 指数扭转对正态: q_θ = N(μ + σ²θ, σ)
                # 来源: Siegmund 1976, Glasserman 2003 Ch.4.4
                mu = spec.get("loc", 0.0)
                sigma = spec.get("scale", 1.0)
                new_spec = {"type": "norm", "loc": mu + sigma * sigma * theta, "scale": sigma}
            elif dist_type == "uniform":
                # 指数扭转对均匀分布无解析均值平移；退化为均值平移（loc += θ）
                # 这是工程近似，对均匀分布的指数扭转严格形式需数值求解
                new_spec = dict(spec)
                new_spec["loc"] = spec.get("loc", 0.0) + theta
            else:
                raise ValueError(
                    f"EXPONENTIAL_TWIST 不支持分布类型 '{dist_type}'"
                )
            biasing_specs.append(new_spec)
        return _build_univariate_distributions(biasing_specs)

    if method == BiasingMethod.MIXTURE:
        # MIXTURE 的 h 分量是 MEAN_SHIFT 构造的偏置分布
        # 实际采样与 logpdf 在 _sample_mixture / _logpdf_mixture 中处理
        if biasing.mean_shift is None or len(biasing.mean_shift) != d:
            raise ValueError(
                f"MIXTURE 需要 mean_shift 长度 = {d}，"
                f"得到 {biasing.mean_shift}"
            )
        if not (0.0 < biasing.mixture_alpha < 1.0):
            raise ValueError(
                f"mixture_alpha 必须在 (0, 1)，得到 {biasing.mixture_alpha}"
            )
        # 返回 h 分量（调用方需自行混合）
        h_specs = []
        for j, spec in enumerate(nominal_specs):
            shift = float(biasing.mean_shift[j])
            new_spec = dict(spec)
            new_spec["loc"] = spec.get("loc", 0.0) + shift
            h_specs.append(new_spec)
        return _build_univariate_distributions(h_specs)

    if method == BiasingMethod.CROSS_ENTROPY:
        # CE 初始分布用 MEAN_SHIFT 构造的 h（迭代中更新）
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
        h_specs = []
        for j, spec in enumerate(nominal_specs):
            shift = float(biasing.mean_shift[j])
            new_spec = dict(spec)
            new_spec["loc"] = spec.get("loc", 0.0) + shift
            h_specs.append(new_spec)
        return _build_univariate_distributions(h_specs)

    raise ValueError(f"不支持的偏置方法: {method}")


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


# ============================================================================
# 核心估计器
# ============================================================================


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

    算法:
    1. 构造标称分布 ``f`` 与偏置分布 ``q``
    2. 从 ``q`` 采 ``n`` 样本
    3. 计算每个样本的 ``log W = log f(x) - log q(x)``
    4. 计算每个样本的 ``g(x) = 𝟙_A(x)``（失效区域指示）
    5. 加权良率估计: ``Ŷ = mean(g · exp(log W))``
    6. 标准误差: ``SE = std(g · W) / √n``
    7. 加速比: ``Speedup = Y(1-Y)/Var_IS``（朴素 MC 方差 / IS 方差）
    8. ESS 诊断: ``ESS = (ΣW)² / ΣW²``，退化即 raise

    Args:
        failure_region: 失效区域指示函数 ``A: params -> bool``。
            True 表示该样本在失效区域。
        nominal_dist: 标称（工艺）分布规格列表
            [{"type":"norm"|"uniform","loc":,"scale":}, ...]。
        biasing: 偏置分布构造规格（见 :class:`BiasingSpec`）。
        n_samples: 样本数（典型 10⁴-10⁵）。
        seed: 随机种子（可复现性）。
        min_ess_ratio: 最小 ESS/n 比，低于此值 raise 告警（防止权重退化）。

    Returns:
        ImportanceSamplingResult 含良率估计 + 统计诊断。

    Raises:
        ValueError: 参数无效。
        RuntimeError: 偏置分布支撑不足 / ESS 退化 / 评估失败。
        RuntimeWarning: ESS/n 在 [0.05, 0.1) 之间（边缘可用）。

    学术依据:
    - 似然比估计器: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    - 稀有事件综述: Juneja & Shahabuddin 2006 (Handbooks in OR&MS vol 13)
    - ESS 诊断: Kroese, Taimre & Botev 2011, DOI: 10.1002/9781118014967
    - 加速比: Glasserman 2003, Ch.4.1, DOI: 10.1007/978-0-387-21617-1

    合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
    """
    d = len(nominal_dist)
    if d == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if not (0.0 < min_ess_ratio < 1.0):
        raise ValueError(f"min_ess_ratio 必须在 (0, 1)，得到 {min_ess_ratio}")

    rng = np.random.default_rng(seed)

    # 1. 构造标称分布 f 与偏置分布 q（h 分量）
    f_dists = _build_univariate_distributions(nominal_dist)
    q_dists = _construct_biasing_distribution(nominal_dist, biasing)

    # 2. 从 q 采样
    if biasing.method == BiasingMethod.MIXTURE:
        samples = _sample_mixture(
            f_dists, q_dists, biasing.mixture_alpha, n_samples, rng
        )
    else:
        samples = _sample_from_distributions(q_dists, n_samples, rng)

    # 3. 计算 log W
    log_w = _compute_log_weights(f_dists, q_dists, samples, biasing)
    weights = np.exp(log_w)

    # 4. 评估失效区域指示函数 g(x) = 𝟙_A(x)
    failure_flags = np.empty(n_samples, dtype=bool)
    for i in range(n_samples):
        try:
            failure_flags[i] = bool(failure_region(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"failure_region 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
            ) from e
    n_failures = int(np.sum(failure_flags))

    # 5. 加权良率估计: Ŷ = mean(g · W)
    weighted = failure_flags.astype(float) * weights
    y_hat = float(np.mean(weighted))

    # 6. 标准误差（无偏样本方差）
    if n_samples > 1:
        var_is = float(np.var(weighted, ddof=1))
    else:
        var_is = 0.0
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0

    # 7. 相对误差
    re = se / abs(y_hat) if abs(y_hat) > 0 else float("inf")

    # 8. 95% 置信区间（正态近似）
    ci_lower = y_hat - 1.96 * se
    ci_upper = y_hat + 1.96 * se

    # 9. ESS 诊断: 对良率估计（g=𝟙_A），ESS 基于有效贡献权重 g·W
    # ESS = (Σ(g·W))²/Σ(g·W)²，反映失效样本权重的均匀性。
    # ratio = ESS/n_failures：所有失效样本权重相等时 ratio=1，权重集中时 ratio<<1。
    # 注: 若基于全部 W，则 q 故意偏离 f（如 mean_shift 大）会让非失效样本权重
    # 跨数量级，ESS 极低，但这对良率估计不构成问题（非失效样本 g=0 不贡献）。
    # 来源: Kroese, Taimre & Botev 2011, Ch.9, DOI: 10.1002/9781118014967
    eff_weights = weighted  # g · W
    sum_eff = float(np.sum(eff_weights))
    sum_eff2 = float(np.sum(eff_weights * eff_weights))
    ess = (sum_eff * sum_eff) / sum_eff2 if sum_eff2 > 0 else 0.0
    ess_ratio = ess / n_failures if n_failures > 0 else 0.0

    # 诊断检查（R03 禁止 fall-back: 退化即 raise，不静默继续）
    # 1. 失效样本数: 至少 30 个才有统计意义（CLT 近似成立）
    if n_failures < 30:
        raise RuntimeError(
            f"失效样本数 {n_failures} < 30，统计意义不足。"
            f"建议: 增大 n_samples、增大 mean_shift 使 q 更偏向失效区、"
            f"或用 CROSS_ENTROPY 自适应寻找最优偏置。"
            f"禁止 fall-back（R03）。"
        )
    # 2. ESS 退化: ESS/n_failures < min_ess_ratio 表示失效样本权重严重集中
    if ess_ratio < min_ess_ratio:
        raise RuntimeError(
            f"ESS 退化: ESS/n_failures = {ess_ratio:.4f} < 阈值 {min_ess_ratio}。"
            f"失效样本权重过度集中，IS 估计不可靠。"
            f"建议: 减小 mean_shift、使用 MIXTURE、或用 CROSS_ENTROPY 自适应。"
            f"禁止 fall-back（R03）。"
        )
    # 3. 相对误差: RE > 0.5（50%）表示估计不可靠
    if re > 0.5:
        raise RuntimeError(
            f"相对误差 RE = {re:.4f} > 0.5，IS 估计不可靠。"
            f"建议: 增大 n_samples 或改进偏置分布。"
            f"禁止 fall-back（R03）。"
        )
    if ess_ratio < 0.3 or re > 0.1:
        # 边缘可用但需告警（不阻断，但记日志）
        logger.warning(
            "ESS/n_failures = %.4f, RE = %.4f 在边缘区间，建议改进偏置分布。",
            ess_ratio,
            re,
        )

    # 10. 加速比: Speedup = Var(Ŷ_MC) / Var(Ŷ_IS) = [Y(1-Y)/n] / [Var_q(g·W)/n]
    # = Y(1-Y) / Var_q(g·W)（n 约去）。var_is 是 Var_q(g·W)（单样本方差）。
    var_mc_single = y_hat * (1.0 - y_hat)  # 单样本伯努利方差
    speedup = var_mc_single / var_is if var_is > 0 else float("inf")

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
        n_evaluations=n_samples,
        biasing_method=biasing.method.value,
        log_weights=log_w,
        samples=samples,
        converged=None,
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
    if d == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if not (0.0 < min_ess_ratio < 1.0):
        raise ValueError(f"min_ess_ratio 必须在 (0, 1)，得到 {min_ess_ratio}")

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
    g_values = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        try:
            g_values[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
            ) from e

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
    d = len(nominal_dist)
    if d == 0:
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

    rng = np.random.default_rng(seed)
    f_dists = _build_univariate_distributions(nominal_dist)

    # 初始化 q 的均值/方差（用标称分布 + initial_mean_shift）
    q_means = np.array(
        [spec.get("loc", 0.0) + s for spec, s in zip(nominal_dist, initial_mean_shift, strict=True)],
        dtype=float,
    )
    q_stds = np.array(
        [spec.get("scale", 1.0) for spec in nominal_dist], dtype=float
    )

    n_elite = max(1, int(n_samples * elite_ratio))
    total_evals = 0
    converged = False

    # CE 迭代
    for it in range(n_iterations):
        # 从当前 q（独立正态）采样
        samples = rng.normal(loc=q_means, scale=q_stds, size=(n_samples, d))
        # 评估失效指示
        flags = np.empty(n_samples, dtype=bool)
        for i in range(n_samples):
            try:
                flags[i] = bool(failure_region(samples[i]))
            except Exception as e:
                raise RuntimeError(
                    f"CE 迭代 {it} 样本 {i} failure_region 评估失败: "
                    f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
                ) from e
        total_evals += n_samples

        # 选择 elite: 失效样本优先（最严格 elite = 失效样本）
        # 若失效样本 < n_elite，用失效样本 + 距离失效区最近的补足（这里简化为仅用失效样本）
        failure_idx = np.where(flags)[0]
        if len(failure_idx) == 0:
            logger.warning(
                "CE 迭代 %d/%d 无失效样本，q 未更新。建议增大 initial_mean_shift。",
                it + 1,
                n_iterations,
            )
            continue

        if len(failure_idx) >= n_elite:
            elite_idx = failure_idx[:n_elite]
        else:
            elite_idx = failure_idx

        elite_samples = samples[elite_idx]

        # 最大似然更新（高斯）: μ = mean(elite), σ = std(elite)
        new_means = np.mean(elite_samples, axis=0)
        new_stds = np.std(elite_samples, axis=0, ddof=1)
        # 防止 std 退化为 0
        new_stds = np.maximum(new_stds, 1e-6)

        # 平滑
        q_means = smoothing_alpha * new_means + (1.0 - smoothing_alpha) * q_means
        q_stds = smoothing_alpha * new_stds + (1.0 - smoothing_alpha) * q_stds

        # 收敛判定: elite 集合均值变化 < 1%
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

    # 用最终 q 跑 IS 估计
    # 构造 q 分布规格（norm + 自适应参数）
    final_specs = [
        {"type": "norm", "loc": float(q_means[j]), "scale": float(q_stds[j])}
        for j in range(d)
    ]
    q_dists = _build_univariate_distributions(final_specs)

    samples = _sample_from_distributions(q_dists, n_samples, rng)

    # 计算 log W = log f - log q（q 是独立正态，直接 logpdf）
    log_f = _logpdf_distributions(f_dists, samples)
    log_q = _logpdf_distributions(q_dists, samples)
    log_w = log_f - log_q

    # 检查 q 撑不足
    bad_mask = np.isinf(log_w) & (log_w < 0) & np.isfinite(log_f)
    if np.any(bad_mask):
        n_bad = int(np.sum(bad_mask))
        raise RuntimeError(
            f"CE 最终 q 分布支撑不足: {n_bad} 个样本 q.pdf=0 但 f.pdf>0。"
            f"绝对连续条件违反。禁止 fall-back（R03）。"
        )

    weights = np.exp(log_w)
    flags = np.empty(n_samples, dtype=bool)
    for i in range(n_samples):
        try:
            flags[i] = bool(failure_region(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"最终 IS 估计样本 {i} failure_region 评估失败: "
                f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
            ) from e
    total_evals += n_samples
    n_failures = int(np.sum(flags))

    weighted = flags.astype(float) * weights
    y_hat = float(np.mean(weighted))
    var_is = float(np.var(weighted, ddof=1)) if n_samples > 1 else 0.0
    se = float(np.sqrt(var_is / n_samples)) if var_is > 0 else 0.0
    re = se / abs(y_hat) if abs(y_hat) > 0 else float("inf")
    ci_lower = y_hat - 1.96 * se
    ci_upper = y_hat + 1.96 * se

    # ESS 诊断: 基于有效贡献权重 g·W（与 importance_sampling_yield 一致）
    sum_eff = float(np.sum(weighted))
    sum_eff2 = float(np.sum(weighted * weighted))
    ess = (sum_eff * sum_eff) / sum_eff2 if sum_eff2 > 0 else 0.0
    ess_ratio = ess / n_failures if n_failures > 0 else 0.0

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

    var_mc_single = y_hat * (1.0 - y_hat)  # 单样本伯努利方差
    speedup = var_mc_single / var_is if var_is > 0 else float("inf")

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


__all__ = [
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
    "cross_entropy_importance_sampling",
    "importance_sampling_mean",
    "importance_sampling_yield",
    "rare_event_yield",
]
