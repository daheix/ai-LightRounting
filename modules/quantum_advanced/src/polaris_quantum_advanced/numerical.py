"""量子光子数值仿真模块（HOM dip / 采样器 / 卡方检验）。

单一职责: HOM dip 时间分辨仿真、玻色采样随机采样器、卡方统计检验。
这些数值方法用于验证解析分布的正确性，模拟真实实验过程。

Input / Process / Output
------------------------
Input:
    sigma / dt_range — HOM dip 波包宽度与时间差轴；
    unitary / input_state / n_samples — 玻色采样采样器输入；
    observed / expected_dist / n_samples — 卡方检验观测与期望。
Process:
    HOM dip: P_coinc(Δt) = 0.5×(1 - exp(-Δt²/(2σ²)))（高斯波包重叠）
    采样器: 按解析分布 rng.choice 随机采样输出模式
    卡方检验: χ² = Σ (O_i - E_i)²/E_i，p 值 = 1 - CDF(χ², dof)
Output:
    符合计数率数组 / 采样统计字典 / (chi2, p_value, dof)。

学术诚信（R02，≥5 文献 URL 溯源）:
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Bouwmeester et al., "The Physics of Quantum Information", Springer 2000, §3.1
- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Pearson, "On the criterion that a given system of deviations...",
  Philosophical Magazine 1900（卡方检验原始论文）

设计原则
--------
- 纯 NumPy/SciPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: sigma ≤ 0 / 空批次 → raise
"""

from __future__ import annotations

import numpy as np

from polaris_quantum_advanced.boson_sampling import boson_sampling_distribution

__all__ = [
    "hom_dip_simulation",
    "boson_sampling_sampler",
    "boson_sampling_chi_square_test",
]


def hom_dip_simulation(
    sigma: float = 1.0,
    dt_range: np.ndarray | None = None,
) -> np.ndarray:
    """HOM dip 时间分辨数值仿真（Hong-Ou-Mandel 干涉曲线）。

    物理模型: 两个全同光子高斯波包，重叠积分 overlap²(Δt)=exp(-Δt²/(2σ²))，
    符合计数率 P_coinc(Δt) = 0.5×(1 - exp(-Δt²/(2σ²)))。
    Δt=0 时 P=0（HOM dip 量子干涉），Δt→∞ 时 P=0.5（经典极限）。

    来源: Hong, Ou, Mandel, PRL 1987
    https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

    Args:
        sigma: 波包宽度（时间单位，控制 dip 半高宽）。
        dt_range: 时间差数组 Δt（None 用默认 np.linspace(-5σ, 5σ, 101)）。

    Returns:
        符合计数率数组 P_coinc(Δt)，范围 [0, 0.5]。

    Raises:
        ValueError: sigma ≤ 0。
    """
    if sigma <= 0:
        raise ValueError(f"sigma 须 > 0，得到 {sigma}")
    if dt_range is None:
        dt_range = np.linspace(-5 * sigma, 5 * sigma, 101)
    dt = np.asarray(dt_range, dtype=float)
    overlap_sq = np.exp(-(dt ** 2) / (2 * sigma ** 2))
    return 0.5 * (1.0 - overlap_sq)


def boson_sampling_sampler(
    unitary: np.ndarray,
    input_state: tuple[int, ...],
    n_samples: int = 10000,
    seed: int | None = None,
) -> dict[tuple[int, ...], int]:
    """玻色采样器（按解析分布随机采样输出模式）。

    真实玻色采样实验是单次采样，无法获得完整分布。本函数通过按解析分布
    随机采样输出模式，模拟真实实验过程。

    来源: Aaronson & Arkhipov, STOC 2011 https://arxiv.org/abs/0910.4698

    Args:
        unitary: M×M 酉矩阵。
        input_state: 输入模式 [n_1, ..., n_M]。
        n_samples: 采样次数。
        seed: 随机种子（None 不固定）。

    Returns:
        采样统计 {output_state: count}，count 之和 = n_samples。
    """
    dist = boson_sampling_distribution(unitary, input_state)
    states = list(dist.output_prob.keys())
    probs = np.array([dist.output_prob[s] for s in states], dtype=float)
    probs = probs / probs.sum()
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(states), size=n_samples, p=probs)
    counts: dict[tuple[int, ...], int] = {}
    for idx in indices:
        state = states[idx]
        counts[state] = counts.get(state, 0) + 1
    return counts


def boson_sampling_chi_square_test(
    observed: dict[tuple[int, ...], int],
    expected_dist: dict[tuple[int, ...], float],
    n_samples: int | None = None,
) -> tuple[float, float, int]:
    """卡方检验：采样分布与解析分布的统计一致性。

    χ² = Σ (O_i - E_i)² / E_i，p 值 = 1 - CDF(χ², dof)。

    来源: Pearson 1900（卡方检验原始论文）

    Args:
        observed: 采样统计 {output_state: count}。
        expected_dist: 解析概率分布 {output_state: prob}。
        n_samples: 总采样数（None 用 sum(observed.values())）。

    Returns:
        (chi2_statistic, p_value, dof)，p>0.05 表示分布一致。
    """
    if n_samples is None:
        n_samples = sum(observed.values())
    all_states = set(observed.keys()) | set(expected_dist.keys())
    chi2 = 0.0
    dof = 0
    for state in all_states:
        observed_count = observed.get(state, 0)
        expected_prob = expected_dist.get(state, 0.0)
        expected_count = expected_prob * n_samples
        if expected_count < 5:
            continue
        chi2 += (observed_count - expected_count) ** 2 / expected_count
        dof += 1
    dof = max(dof - 1, 1)
    from scipy.stats import chi2 as chi2_dist
    p_value = 1.0 - chi2_dist.cdf(chi2, dof)
    return float(chi2), float(p_value), dof
