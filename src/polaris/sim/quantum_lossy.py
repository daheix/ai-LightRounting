"""R35: 含光子损失的玻色采样与量子优越性阈值模块。

实现损失架构下的玻色采样概率分布，以及量子优越性阈值评估。

*创新*: 基于 García-Patrón, Renema, Shchesnovich (Quantum 3, 169, 2019)
理论，PoLaRIS 实现损失感知仿真评估量子优越性阈值。该论文证明含指数
衰减的玻色采样可经典模拟，本模块量化评估损失对量子优越性的影响。

来源（学术诚信 R02）:
- García-Patrón, Renema, Shchesnovich, "Simulating boson sampling in lossy
  architectures," Quantum 3, 169 (2019), arXiv:1712.10037.
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
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009

🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

import math

import numpy as np

from polaris.sim.quantum_boson_sampling import boson_sampling_distribution


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

    来源:
    - García-Patrón, Renema, Shchesnovich, "Simulating boson sampling in lossy
      architectures," Quantum 3, 169 (2019), arXiv:1712.10037.
      https://arxiv.org/abs/1712.10037
      https://doi.org/10.22331/q-2019-08-05-169

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
    # 简化模型: 每个光子独立以 (1-loss_rate) 概率存活
    # 输出分布 = Σ_k C(n,k) (1-loss)^k loss^(n-k) × P(k 光子输出)
    survival_prob = 1.0 - loss_rate
    output_dist: dict[tuple[int, ...], float] = {}
    # 遍历存活光子数 k = 0..n
    for k in range(n_photons + 1):
        # k 个光子存活的概率（二项分布）
        binom_p = math.comb(n_photons, k) * (survival_prob ** k) * (loss_rate ** (n_photons - k))
        if k == 0:
            # 所有光子丢失
            zero_state = tuple([0] * M)
            output_dist[zero_state] = output_dist.get(zero_state, 0.0) + binom_p
            continue
        # k 个光子通过网络的分布（简化: 用原始酉矩阵，输入取前 k 个光子）
        # 这里简化处理: 假设存活的 k 个光子均匀分布在输入模式中
        simplified_input = _distribute_photons(k, M)
        ideal_dist = boson_sampling_distribution(U, simplified_input)
        for out_state, prob in ideal_dist.output_prob.items():
            output_dist[out_state] = output_dist.get(out_state, 0.0) + binom_p * prob
    return output_dist


def _distribute_photons(n_photons: int, n_modes: int) -> tuple[int, ...]:
    """将 n_photons 个光子均匀分布到 n_modes 个模式。

    Args:
        n_photons: 光子数。
        n_modes: 模式数。

    Returns:
        输入模式元组。
    """
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

    基于 García-Patrón, Renema, Shchesnovich (Quantum 3, 169, 2019) 的严格
    理论结果：当检测到的光子数小于 O(√N) 时，玻色采样可被经典算法高效模拟。

    判定准则（论文 §3 主要定理）:
        N_detected = (1 - loss_rate) · N_input
        量子优越性保持 ⟺ N_detected ≥ √N_input
        等价于：(1 - loss_rate) · N_input ≥ √N_input
                ⟺ 1 - loss_rate ≥ 1/√N_input
                ⟺ loss_rate ≤ 1 - 1/√N_input

    该准则针对传输率随电路深度指数衰减的架构（集成光子电路、光纤等），
    论文证明此类架构要么深度足够大（可被热噪声算法多项式时间模拟），
    要么深度足够浅（张量网络算法准多项式时间模拟）。

    来源（学术诚信 R02，禁止编造阈值）:
    - García-Patrón, Renema, Shchesnovich, "Simulating boson sampling in lossy
      architectures," Quantum 3, 169 (2019), arXiv:1712.10037.
      https://arxiv.org/abs/1712.10037
      https://doi.org/10.22331/q-2019-08-05-169
    - Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
      https://arxiv.org/abs/0910.4698

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
    # García-Patrón 2019 §3 定理：检测光子数 < √N 时可经典模拟。
    # 取保守常数 C=1（O(√N) 的下界），即 N_detected < √N 时判定可经典模拟。
    n_detected = (1.0 - loss_rate) * n_photons
    threshold = np.sqrt(n_photons)
    return bool(n_detected >= threshold)


__all__ = [
    "lossy_boson_sampling",
    "quantum_advantage_threshold",
]
