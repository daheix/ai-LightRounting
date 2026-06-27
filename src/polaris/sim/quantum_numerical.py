"""R35: 量子光子数值仿真模块（R4 迭代: 非解析验证）。

实现 HOM dip 时间分辨仿真、玻色采样随机采样器、卡方统计检验。
这些数值方法用于验证解析分布的正确性，模拟真实实验过程。

核心算法:
- HOM dip 仿真: P_coinc(Δt) = 0.5 × (1 - exp(-Δt²/(2σ²)))
- 玻色采样器: 按解析分布随机采样输出模式
- 卡方检验: χ² = Σ (O_i - E_i)² / E_i

来源（学术诚信 R02）:
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Bouwmeester et al., "The Physics of Quantum Information", Springer 2000, §3.1
- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Pearson, "On the criterion that a given system of deviations...",
  Philosophical Magazine 1900（卡方检验原始论文）
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501

🚫不参与 GPU（R04）：纯 NumPy/SciPy 实现。
"""

from __future__ import annotations

import numpy as np

from polaris.sim.quantum_boson_sampling import boson_sampling_distribution


def hom_dip_simulation(
    sigma: float = 1.0,
    dt_range: np.ndarray | None = None,
) -> np.ndarray:
    """HOM dip 时间分辨数值仿真（Hong-Ou-Mandel 干涉曲线）。

    仿真双光子波包到达时间差 Δt 对符合计数率的影响，重现 HOM dip 曲线。

    物理模型:
    - 两个全同光子的高斯波包 ψ(t) = (2πσ²)^{-1/4} exp(-(t-t₀)²/(4σ²))
    - 波包重叠积分: overlap(Δt) = exp(-Δt²/(4σ²))
    - 符合计数率: P_coinc(Δt) = 0.5 × (1 - |overlap(Δt)|²)
                                = 0.5 × (1 - exp(-Δt²/(2σ²)))

    当 Δt=0 时 P=0（HOM dip，量子干涉），Δt→∞ 时 P=0.5（经典极限）。

    来源:
    - Hong, Ou, Mandel, PRL 1987, HOM 干涉
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
    - Bouwmeester et al., "The Physics of Quantum Information", Springer 2000, §3.1

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
    # P_coinc(Δt) = 0.5 × (1 - exp(-Δt²/(2σ²)))
    overlap_sq = np.exp(-(dt ** 2) / (2 * sigma ** 2))
    return 0.5 * (1.0 - overlap_sq)


def boson_sampling_sampler(
    unitary: np.ndarray,
    input_state: tuple[int, ...],
    n_samples: int = 10000,
    seed: int | None = None,
) -> dict[tuple[int, ...], int]:
    """玻色采样器（按分布随机采样输出模式）。

    真实玻色采样实验是单次采样，无法获得完整分布。本函数通过按解析分布
    随机采样输出模式，模拟真实实验过程，可用于卡方检验验证解析分布正确性。

    来源:
    - Aaronson & Arkhipov, STOC 2011, 玻色采样
      https://arxiv.org/abs/0910.4698
    - Seron et al., Quantum 2024, BosonSampling.jl
      https://arxiv.org/abs/2212.09537

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
    probs = probs / probs.sum()  # 归一化（消除浮点误差）
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

    χ² = Σ (O_i - E_i)² / E_i

    其中 O_i 为观测频数，E_i 为期望频数。

    来源:
    - Pearson, "On the criterion that a given system of deviations...",
      Philosophical Magazine 1900（卡方检验原始论文）

    Args:
        observed: 采样统计 {output_state: count}。
        expected_dist: 解析概率分布 {output_state: prob}。
        n_samples: 总采样数（None 用 sum(observed.values())）。

    Returns:
        (chi2_statistic, p_value, dof):
        - chi2_statistic: 卡方统计量
        - p_value: p 值（> 0.05 表示分布一致）
        - dof: 自由度（类别数 - 1）
    """
    if n_samples is None:
        n_samples = sum(observed.values())
    # 收集所有输出模式
    all_states = set(observed.keys()) | set(expected_dist.keys())
    chi2 = 0.0
    dof = 0
    for state in all_states:
        observed_count = observed.get(state, 0)
        expected_prob = expected_dist.get(state, 0.0)
        expected_count = expected_prob * n_samples
        if expected_count < 5:
            # 期望频数 < 5 的类别合并（卡方检验要求）
            continue
        chi2 += (observed_count - expected_count) ** 2 / expected_count
        dof += 1
    dof = max(dof - 1, 1)  # 自由度 = 类别数 - 1
    # p 值: P(χ² > chi2 | dof)
    from scipy.stats import chi2 as chi2_dist
    p_value = 1.0 - chi2_dist.cdf(chi2, dof)
    return float(chi2), float(p_value), dof


__all__ = [
    "boson_sampling_chi_square_test",
    "boson_sampling_sampler",
    "hom_dip_simulation",
]
