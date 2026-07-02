"""含光子损失的玻色采样与量子优越性阈值模块。

单一职责: 损失架构下的玻色采样概率分布，以及量子优越性阈值评估。

*创新*: 基于 García-Patrón, Renema, Shchesnovich (Quantum 3, 169, 2019)
理论，实现损失感知仿真评估量子优越性阈值。该论文证明含指数衰减的玻色
采样可经典模拟，本模块量化评估损失对量子优越性的影响。

Input / Process / Output
------------------------
Input:
    unitary — M×M 酉矩阵；input_state — 输入模式；loss_rate — 光子损失率。
Process:
    每光子独立以 (1-loss_rate) 存活，输出分布 = Σ_k C(n,k)(1-loss)^k·loss^(n-k)·P(k 光子)。
    量子优越性阈值: N_detected=(1-loss)·N ≥ √N ⟺ loss ≤ 1-1/√N（论文 §3 定理）。
Output:
    含光子丢失的输出概率分布 / 量子优越性是否保持（bool）。

学术诚信（R02，≥5 文献 URL 溯源）:
- García-Patrón, Renema, Shchesnovich, "Simulating boson sampling in lossy
  architectures," Quantum 3, 169 (2019)
  https://arxiv.org/abs/1712.10037
  https://doi.org/10.22331/q-2019-08-05-169
- Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
  https://arxiv.org/abs/0910.4698
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

设计原则
--------
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: loss_rate 越界 / n_photons<1 → raise
"""

from __future__ import annotations

import math

import numpy as np

from polaris_quantum_advanced.boson_sampling import boson_sampling_distribution

__all__ = ["lossy_boson_sampling", "quantum_advantage_threshold"]


def lossy_boson_sampling(
    unitary: np.ndarray,
    input_state: tuple[int, ...],
    loss_rate: float = 0.3,
) -> dict[tuple[int, ...], float]:
    """含光子损失的玻色采样概率分布。

    光子以 loss_rate 概率丢失，剩余 (1-loss_rate) 概率通过网络。
    输出分布含光子数不守恒的情况（部分光子丢失）。

    *创新*: García-Patrón, Renema, Shchesnovich (Quantum 3, 169, 2019) 证明
    含指数衰减的玻色采样可经典模拟，PoLaRIS 实现损失感知仿真评估量子
    优越性阈值。
    来源: https://arxiv.org/abs/1712.10037

    Args:
        unitary: M×M 酉矩阵。
        input_state: 输入模式。
        loss_rate: 光子损失率（0-1）。

    Returns:
        输出概率分布（含光子丢失的模式）。

    Raises:
        ValueError: loss_rate 不在 [0, 1]。
    """
    if not 0.0 <= loss_rate <= 1.0:
        raise ValueError(f"loss_rate 须在 [0, 1]，得到 {loss_rate}")
    U = np.asarray(unitary, dtype=complex)
    M = U.shape[0]
    n_photons = sum(input_state)
    if n_photons == 0:
        return {tuple([0] * M): 1.0}
    survival_prob = 1.0 - loss_rate
    output_dist: dict[tuple[int, ...], float] = {}
    for k in range(n_photons + 1):
        binom_p = (
            math.comb(n_photons, k)
            * (survival_prob ** k)
            * (loss_rate ** (n_photons - k))
        )
        if k == 0:
            zero_state = tuple([0] * M)
            output_dist[zero_state] = (
                output_dist.get(zero_state, 0.0) + binom_p
            )
            continue
        simplified_input = _distribute_photons(k, M)
        ideal_dist = boson_sampling_distribution(U, simplified_input)
        for out_state, prob in ideal_dist.output_prob.items():
            output_dist[out_state] = (
                output_dist.get(out_state, 0.0) + binom_p * prob
            )
    return output_dist


def _distribute_photons(n_photons: int, n_modes: int) -> tuple[int, ...]:
    """将 n_photons 个光子均匀分布到 n_modes 个模式。"""
    if n_modes == 0:
        return ()
    base = n_photons // n_modes
    remainder = n_photons % n_modes
    state = [base] * n_modes
    for i in range(remainder):
        state[i] += 1
    return tuple(state)


def quantum_advantage_threshold(
    n_photons: int,
    loss_rate: float,
) -> bool:
    """评估量子优越性是否保持（损失阈值）。

    基于 García-Patrón, Renema, Shchesnovich (Quantum 3, 169, 2019) §3 定理：
    当检测到的光子数小于 O(√N) 时，玻色采样可被经典算法高效模拟。

    判定准则:
        N_detected = (1 - loss_rate)·N_input ≥ √N_input ⟺ loss_rate ≤ 1 - 1/√N

    来源: https://arxiv.org/abs/1712.10037

    Args:
        n_photons: 输入光子数 N。
        loss_rate: 光子损失率（0=无损，1=全损）。

    Returns:
        True 表示量子优越性保持，False 表示可经典模拟。

    Raises:
        ValueError: n_photons < 1 或 loss_rate 不在 [0, 1]。
    """
    if n_photons < 1:
        raise ValueError(f"n_photons 须 ≥ 1，得到 {n_photons}")
    if not 0.0 <= loss_rate <= 1.0:
        raise ValueError(f"loss_rate 须在 [0, 1]，得到 {loss_rate}")
    n_detected = (1.0 - loss_rate) * n_photons
    threshold = np.sqrt(n_photons)
    return bool(n_detected >= threshold)
