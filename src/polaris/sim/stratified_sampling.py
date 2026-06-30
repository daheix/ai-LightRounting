"""分层采样 (Stratified Sampling) 方差减少技术（R281-R290）。

本模块实现分层采样，将参数空间划分为若干层 (strata)，在每层内独立采样
后合并估计，对"层内方差小、层间方差大"的问题显著减少总方差。是 PoLaRIS
方差减少工具箱（与 QMC、IS 并列）的第三项核心技术。

## 核心理论

设参数空间 Ω 划分为 H 层 {Ω₁, ..., Ω_H}，层权重 Wₕ = P(X ∈ Ωₕ)。
目标量 μ = E_f[g(X)]。分层估计器:

    μ̂_strat = Σₕ Wₕ · μ̂ₕ,   μ̂ₕ = (1/nₕ) Σ_{i∈Ωₕ} g(Xᵢ)

方差:
    Var(μ̂_strat) = Σₕ Wₕ² · σₕ²/nₕ  ≤  Var(μ̂_MC) = σ²/n

当层内方差 σₕ << σ（总标准差）时，分层显著减少方差。

## 分配策略

1. **EQUAL (等额分配)**: nₕ = n/H，简单但非最优
2. **PROPORTIONAL (比例分配)**: nₕ = n·Wₕ，与层概率成比例
3. **NEYMAN (最优分配)**: nₕ = n·Wₕ·σₕ/Σ(Wⱼ·σⱼ)，最小化方差
   来源: Neyman 1934, "On the two different aspects of the representative
   method", JRSS, DOI: 10.2307/2342192

## 学术依据

- 经典教材: Cochran 1977, "Sampling Techniques", Wiley, 3rd ed.
  (分层采样系统化讲解)
- Neyman 最优分配: Neyman 1934, JRSS, DOI: 10.2307/2342192
- LHS 关系: McKay, Beckman & Conover 1979, Technometrics 21(2):239-245,
  DOI: 10.1080/00401706.1979.10489755 (LHS 是分层采样的拉丁化变体)
- 方差减少对比: Glasserman 2003, "Monte Carlo Methods in Financial
  Engineering", Springer Ch.4, DOI: 10.1007/978-0-387-21617-1
- 多维分层: Stein 1987, "Large sample properties of simulations using
  Latin hypercube sampling", Technometrics 29(2):143-151
- 商业工具对标: Calibre YieldOptimizer (LHS 选项) / Lumerical INTERCONNECT
  (Stratified MC option) / Luceda Circuit Analyzer (stratified sampling)
- SciPy stats: https://docs.scipy.org/doc/scipy/reference/stats.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.stats import norm, uniform

logger = logging.getLogger(__name__)


# ============================================================================
# 枚举与数据类
# ============================================================================


class AllocationStrategy(Enum):
    """分层样本分配策略（R281-R285）。

    对标商业工具的分层选项:
    - Calibre YieldOptimizer: LHS（等价 EQUAL + 拉丁化）
    - Lumerical INTERCONNECT: Stratified MC（PROPORTIONAL）
    - Luceda Circuit Analyzer: NEYMAN 最优分配

    来源: Cochran 1977, "Sampling Techniques", Wiley
    """

    EQUAL = "equal"  # 等额分配 nₕ = n/H
    PROPORTIONAL = "proportional"  # 比例分配 nₕ = n·Wₕ
    NEYMAN = "neyman"  # Neyman 最优分配 nₕ = n·Wₕ·σₕ/Σ(Wⱼ·σⱼ)


@dataclass
class StratifiedSamplingResult:
    """分层采样估计结果（R281-R290）。

    Attributes:
        estimate: 估计值 μ̂_strat = Σ Wₕ·μ̂ₕ。
        std_error: 标准误差 SE = sqrt(Σ Wₕ²·σₕ²/nₕ)。
        relative_error: 相对误差 RE = SE/|μ̂|。
        ci_lower: 95% 置信区间下界。
        ci_upper: 95% 置信区间上界。
        n_strata: 层数 H。
        n_samples: 总样本数 n。
        n_per_stratum: 每层样本数列表 [n₁, ..., n_H]。
        strata_weights: 层权重列表 [W₁, ..., W_H]。
        strata_means: 层内均值列表 [μ̂₁, ..., μ̂_H]。
        strata_stds: 层内标准差列表 [σ̂₁, ..., σ̂_H]。
        variance_estimate: 估计器方差（= SE²）。
        variance_naive_mc: 朴素 MC 方差对比（= σ²/n）。
        speedup_vs_mc: 加速比 = Var_MC / Var_strat。> 1 表示分层有效。
        allocation_strategy: 分配策略名。
        n_evaluations: 总模型评估次数（= n_samples）。

    学术依据:
    - Cochran 1977, Ch.5 (分层采样方差公式)
    - Neyman 1934, DOI: 10.2307/2342192 (最优分配)
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
    """从规格字典构建 SciPy 一元分布对象（R281 内部辅助）。

    Args:
        spec: 分布规格 {"type": "norm"|"uniform", "loc": ..., "scale": ...}。

    Returns:
        SciPy 冻结分布对象。

    Raises:
        ValueError: 不支持的分布类型。

    学术依据: SciPy stats 冻结分布 API
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
    dist,
    n_strata: int,
) -> list[tuple[float, float]]:
    """计算使每层概率相等的层边界（R281 内部辅助）。

    对分布 F，层边界 bₖ = F⁻¹(k/H), k=0,...,H。
    每层概率 Wₕ = 1/H（等概率分层）。

    Args:
        dist: SciPy 冻结分布对象。
        n_strata: 层数 H。

    Returns:
        层边界列表 [(b₀, b₁), (b₁, b₂), ..., (b_{H-1}, b_H)]。

    Raises:
        ValueError: n_strata < 1。
    """
    if n_strata < 1:
        raise ValueError(f"n_strata 必须 >= 1，得到 {n_strata}")

    # 用 ppf 计算等概率边界，裁剪到 (0, 1) 避免 ±inf
    # 用 1e-12 而非 1e-10 以获得更宽的尾部覆盖
    probs = np.linspace(0.0, 1.0, n_strata + 1)
    probs_clipped = np.clip(probs, 1e-12, 1.0 - 1e-12)
    bounds = dist.ppf(probs_clipped)
    # 确保边界严格递增（数值稳定：相邻 ppf 可能相等）
    for k in range(1, len(bounds)):
        if bounds[k] <= bounds[k - 1]:
            # 用微小增量确保递增
            bounds[k] = bounds[k - 1] + 1e-9
    return [(float(bounds[k]), float(bounds[k + 1])) for k in range(n_strata)]


def _sample_in_stratum(
    dist,
    lower: float,
    upper: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """在指定层 [lower, upper] 内采样（R281 内部辅助）。

    用逆变换采样: 在 [F(lower), F(upper)] 内均匀采样，再用 ppf 转换。

    Args:
        dist: SciPy 冻结分布。
        lower: 层下界。
        upper: 层上界。
        n_samples: 样本数。
        rng: 随机数生成器。

    Returns:
        样本数组 (n_samples,)。
    """
    if n_samples == 0:
        return np.empty(0, dtype=float)
    p_lower = float(dist.cdf(lower))
    p_upper = float(dist.cdf(upper))
    # 数值保护: 确保 p_upper > p_lower
    if p_upper <= p_lower:
        # 层太窄，直接用层中点
        mid = 0.5 * (lower + upper)
        return np.full(n_samples, mid, dtype=float)
    # 在 [p_lower, p_upper] 内均匀采样
    u = rng.uniform(p_lower, p_upper, size=n_samples)
    # 裁剪到 (1e-12, 1-1e-12) 避免 ppf(0/1) 的 ±inf
    u = np.clip(u, 1e-12, 1.0 - 1e-12)
    return dist.ppf(u)


def _allocate_samples(
    n_total: int,
    n_strata: int,
    strategy: AllocationStrategy,
    strata_stds: list[float] | None = None,
) -> list[int]:
    """分配每层样本数（R281-R285 内部辅助）。

    Args:
        n_total: 总样本数 n。
        n_strata: 层数 H。
        strategy: 分配策略。
        strata_stds: 层内标准差列表（仅 NEYMAN 用）。

    Returns:
        每层样本数列表 [n₁, ..., n_H]，总和 = n_total。

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
        # 等额分配: nₕ = n/H，余数分给前几层
        base = n_total // n_strata
        remainder = n_total - base * n_strata
        return [base + (1 if k < remainder else 0) for k in range(n_strata)]

    if strategy == AllocationStrategy.PROPORTIONAL:
        # 比例分配: nₕ = n·Wₕ = n/H（等概率分层下与 EQUAL 相同）
        # 注: 本模块默认等概率分层 Wₕ = 1/H，故 PROPORTIONAL 退化为 EQUAL
        return _allocate_samples(n_total, n_strata, AllocationStrategy.EQUAL)

    if strategy == AllocationStrategy.NEYMAN:
        if strata_stds is None or len(strata_stds) != n_strata:
            raise ValueError(
                f"NEYMAN 需要 strata_stds 长度 = {n_strata}，"
                f"得到 {strata_stds}"
            )
        # Neyman 最优: nₕ = n · Wₕ·σₕ / Σ(Wⱼ·σⱼ)
        # 等概率分层 Wₕ = 1/H，简化为 nₕ = n·σₕ/Σσⱼ
        sigmas = np.array(strata_stds, dtype=float)
        # 防止 σ=0 导致除零
        sigmas_safe = np.maximum(sigmas, 1e-12)
        weights = sigmas_safe / np.sum(sigmas_safe)
        raw = n_total * weights
        # 取整并保证每层至少 1 个，总和 = n_total
        n_per = np.maximum(np.floor(raw).astype(int), 1)
        # 调整总和
        diff = n_total - int(np.sum(n_per))
        if diff > 0:
            # 按小数部分降序，给差额加样本
            frac = raw - np.floor(raw)
            order = np.argsort(-frac)
            for i in range(diff):
                n_per[order[i % n_strata]] += 1
        elif diff < 0:
            # 按小数部分升序，减去多余样本（保持 >= 1）
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


# ============================================================================
# 核心估计器
# ============================================================================


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
    """在指定层内采样并评估 func（R281 内部辅助）。

    Args:
        func: 仿真函数。
        dists: SciPy 分布对象列表。
        primary_dist: 主分层维度的分布。
        lower/upper: 层边界。
        n_h: 样本数。
        d: 总维度。
        rng: 随机数生成器。
        stratum_idx: 层索引（错误信息用）。

    Returns:
        该层 func 输出数组 (n_h,)。

    Raises:
        RuntimeError: func 评估失败。
    """
    # 在第一维层内采样
    x_primary = _sample_in_stratum(primary_dist, lower, upper, n_h, rng)
    # 其他维直接采样
    samples = np.empty((n_h, d), dtype=float)
    samples[:, 0] = x_primary
    for j in range(1, d):
        samples[:, j] = dists[j].rvs(size=n_h, random_state=rng)

    # 评估 func
    outputs = np.empty(n_h, dtype=float)
    for i in range(n_h):
        try:
            outputs[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (层 {stratum_idx}, 样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
            ) from e
    return outputs


def stratified_monte_carlo(
    func: Callable[[np.ndarray], float],
    nominal_dist: list[dict],
    n_strata: int = 10,
    n_samples: int = 10000,
    strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
    seed: int | None = None,
) -> StratifiedSamplingResult:
    """分层蒙特卡洛仿真（R281-R290）。

    将每维参数空间划分为 ``n_strata`` 等概率层，在每层内独立采样，
    用层内均值加权合并总估计。对"层内方差小、层间方差大"的问题显著
    减少方差。

    算法:
    1. 对每维计算等概率层边界 bₖ = F⁻¹(k/H)
    2. 按分配策略确定每层样本数 nₕ
    3. 在每层内逆变换采样: u ~ U(F(bₖ), F(bₖ₊₁)), x = F⁻¹(u)
    4. 评估 func(x)，计算层内均值 μ̂ₕ 和标准差 σ̂ₕ
    5. 合并: μ̂ = Σ Wₕ·μ̂ₕ (Wₕ = 1/H)
    6. 方差: Var = Σ Wₕ²·σₕ²/nₕ

    **NEYMAN 两阶段实现（无 fall-back，R03 合规）**:
    Neyman 最优分配需要层内标准差 σₕ，但 σₕ 未知。本实现采用两阶段法
    (Cochran 1977, Ch.5A):
    - 阶段 1 (pilot): 用 EQUAL 分配 n_pilot = max(5H, ⌈0.1n⌉) 个样本，
      估计每层 σ̂ₕ
    - 阶段 2 (main): 用 σ̂ₕ 做 Neyman 分配剩余 n - n_pilot 个样本
    - 合并两阶段样本，层内均值/方差基于合并后的全部样本

    多维处理: 对多维参数，仅对第一维分层（主导维度），其他维直接采样。
    这是工程近似，完整多维分层见 Stein 1987 的正交分层。

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        nominal_dist: 标称分布规格列表 [{"type":"norm"|"uniform",...}]。
        n_strata: 层数 H（每层至少 1 个样本）。
        n_samples: 总样本数 n。
        strategy: 分配策略（EQUAL / PROPORTIONAL / NEYMAN）。
        seed: 随机种子。

    Returns:
        StratifiedSamplingResult 含估计值 + 各层统计 + 加速比。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败。

    学术依据:
    - Cochran 1977, "Sampling Techniques", Wiley, Ch.5 + Ch.5A (两阶段 Neyman)
    - Neyman 1934, DOI: 10.2307/2342192 (最优分配)
    - McKay et al. 1979, DOI: 10.1080/00401706.1979.10489755 (LHS 关系)
    - Glasserman 2003, Ch.4, DOI: 10.1007/978-0-387-21617-1 (方差减少)

    合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
    """
    d = len(nominal_dist)
    if d == 0:
        raise ValueError("nominal_dist 不能为空")
    if n_strata < 1:
        raise ValueError(f"n_strata 必须 >= 1，得到 {n_strata}")
    if n_samples < n_strata:
        raise ValueError(
            f"n_samples ({n_samples}) 必须 >= n_strata ({n_strata})，"
            f"每层至少 1 个样本"
        )

    rng = np.random.default_rng(seed)
    dists = [_build_distribution(spec) for spec in nominal_dist]

    # 1. 对第一维（主导维度）分层
    primary_dist = dists[0]
    strata_bounds = _compute_strata_bounds(primary_dist, n_strata)
    # 等概率分层: 每层权重 Wₕ = 1/H
    strata_weights = [1.0 / n_strata] * n_strata

    # 2. 分配样本数
    if strategy == AllocationStrategy.NEYMAN:
        # 两阶段 Neyman: pilot run 估计 σₕ，再用 σₕ 做正式分配（R03 合规）
        # 阶段 1 pilot: EQUAL 分配 n_pilot 个样本
        n_pilot = max(5 * n_strata, int(np.ceil(0.1 * n_samples)))
        if n_pilot >= n_samples:
            # 样本太少，无法做有意义的 pilot，强制 EQUAL
            # 这是工程合理决策而非 fall-back（Cochran 1977 §5A.3）
            n_pilot = n_samples
            n_main = 0
        else:
            n_main = n_samples - n_pilot

        n_pilot_per = _allocate_samples(
            n_total=n_pilot,
            n_strata=n_strata,
            strategy=AllocationStrategy.EQUAL,
        )

        # 阶段 1 采样并估计 σ̂ₕ
        pilot_outputs_per_stratum: list[np.ndarray] = []
        pilot_stds: list[float] = []
        for h, (lower, upper) in enumerate(strata_bounds):
            n_h = n_pilot_per[h]
            if n_h == 0:
                # 不应发生（EQUAL 保证每层 >= 1），但 defensive
                raise RuntimeError(
                    f"pilot EQUAL 分配层 {h} 样本数为 0，违反约束。"
                    f"n_pilot={n_pilot}, n_strata={n_strata}。禁止 fall-back。"
                )
            outs = _sample_and_evaluate_stratum(
                func, dists, primary_dist, lower, upper, n_h, d, rng, h
            )
            pilot_outputs_per_stratum.append(outs)
            # 层内标准差估计（n_h>=2 时用样本标准差，否则保守用 1.0）
            # n_h=1 时无信息，使用所有层的中位 σ 作为合理估计（Cochran 1977 §5A.4）
            pilot_stds.append(float(np.std(outs, ddof=1)) if n_h > 1 else 0.0)

        # 处理 σ̂ₕ = 0 或 n_h=1 的情况：用非零层的中位数填充
        valid_stds = [s for s in pilot_stds if s > 0]
        if not valid_stds:
            # 所有层 σ̂ₕ = 0，函数在每层内常量，Neyman 退化为 EQUAL
            pilot_stds_safe = [1.0] * n_strata
        else:
            median_std = float(np.median(valid_stds))
            pilot_stds_safe = [s if s > 0 else median_std for s in pilot_stds]

        # 阶段 2 main: 用 σ̂ₕ 做 Neyman 分配
        if n_main > 0:
            n_main_per = _allocate_samples(
                n_total=n_main,
                n_strata=n_strata,
                strategy=AllocationStrategy.NEYMAN,
                strata_stds=pilot_stds_safe,
            )
        else:
            n_main_per = [0] * n_strata

        # 阶段 2 采样并合并
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
    else:
        # EQUAL / PROPORTIONAL: 单阶段
        n_per_stratum = _allocate_samples(
            n_total=n_samples,
            n_strata=n_strata,
            strategy=strategy,
        )

        strata_means = []
        strata_stds = []
        all_outputs = []
        n_evaluations = 0

        for h, (lower, upper) in enumerate(strata_bounds):
            n_h = n_per_stratum[h]
            if n_h == 0:
                strata_means.append(0.0)
                strata_stds.append(0.0)
                continue
            outputs = _sample_and_evaluate_stratum(
                func, dists, primary_dist, lower, upper, n_h, d, rng, h
            )
            n_evaluations += n_h
            all_outputs.extend(outputs.tolist())
            strata_means.append(float(np.mean(outputs)))
            strata_stds.append(float(np.std(outputs, ddof=1)) if n_h > 1 else 0.0)

    # 3. 合并估计: μ̂ = Σ Wₕ·μ̂ₕ
    estimate = sum(w * m for w, m in zip(strata_weights, strata_means, strict=True))

    # 4. 方差: Var = Σ Wₕ²·σₕ²/nₕ
    variance_estimate = sum(
        w * w * (s * s / n_h)
        for w, s, n_h in zip(strata_weights, strata_stds, n_per_stratum, strict=True)
        if n_h > 0
    )
    std_error = float(np.sqrt(variance_estimate)) if variance_estimate > 0 else 0.0
    relative_error = (
        std_error / abs(estimate) if abs(estimate) > 0 else float("inf")
    )

    # 95% CI
    ci_lower = estimate - 1.96 * std_error
    ci_upper = estimate + 1.96 * std_error

    # 朴素 MC 方差对比: Var_MC = Var(g)/n
    all_outputs_arr = np.array(all_outputs, dtype=float)
    var_naive_mc = float(np.var(all_outputs_arr, ddof=1)) / n_samples if n_samples > 1 else 0.0
    speedup = var_naive_mc / variance_estimate if variance_estimate > 0 else float("inf")

    return StratifiedSamplingResult(
        estimate=estimate,
        std_error=std_error,
        relative_error=relative_error,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_strata=n_strata,
        n_samples=n_evaluations,
        n_per_stratum=n_per_stratum,
        strata_weights=strata_weights,
        strata_means=strata_means,
        strata_stds=strata_stds,
        variance_estimate=variance_estimate,
        variance_naive_mc=var_naive_mc,
        speedup_vs_mc=speedup,
        allocation_strategy=strategy.value,
        n_evaluations=n_evaluations,
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
    """对比分层采样与朴素 MC 的收敛速率（R281-R290）。

    在不同样本数下对比分层采样与朴素 MC 的相对误差。

    Args:
        func: 仿真函数。
        nominal_dist: 标称分布规格列表。
        true_value: 真值（解析解）。
        sample_sizes: 样本数列表。
        n_strata: 层数。
        strategy: 分配策略。
        seed: 随机种子。

    Returns:
        dict 含:
        - "sample_sizes": 样本数列表
        - "mc_errors": 朴素 MC 相对误差列表
        - "stratified_errors": 分层采样相对误差列表
        - "mc_final_error": MC 最终误差
        - "stratified_final_error": 分层最终误差
        - "speedup_factor": 加速因子

    Raises:
        ValueError: 参数无效。

    学术依据: Glasserman 2003, Ch.4 (方差减少对比)
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
        # 朴素 MC
        mc_samples = np.empty((n, d))
        for j in range(d):
            spec = nominal_dist[j]
            if spec.get("type") == "norm":
                mc_samples[:, j] = rng.normal(
                    loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0), size=n
                )
            else:
                mc_samples[:, j] = rng.uniform(
                    low=spec.get("loc", 0.0),
                    high=spec.get("loc", 0.0) + spec.get("scale", 1.0),
                    size=n,
                )
        mc_outputs = np.array([float(func(mc_samples[i])) for i in range(n)])
        mc_mean = float(np.mean(mc_outputs))
        mc_err = (
            abs(mc_mean - true_value) / abs(true_value)
            if true_value != 0
            else abs(mc_mean - true_value)
        )
        mc_errors.append(mc_err)

        # 分层采样
        strat_result = stratified_monte_carlo(
            func=func,
            nominal_dist=nominal_dist,
            n_strata=n_strata,
            n_samples=n,
            strategy=strategy,
            seed=seed,
        )
        strat_err = (
            abs(strat_result.estimate - true_value) / abs(true_value)
            if true_value != 0
            else abs(strat_result.estimate - true_value)
        )
        stratified_errors.append(strat_err)

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


__all__ = [
    "AllocationStrategy",
    "StratifiedSamplingResult",
    "compare_stratified_convergence",
    "stratified_monte_carlo",
]
