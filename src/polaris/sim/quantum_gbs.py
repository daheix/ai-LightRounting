"""R35: Gaussian Boson Sampling（GBS）模块。

实现 Hafnian 函数与 GBS 输出概率计算。GBS 是基于高斯态的玻色采样
变体，使用 Hafnian 而非 Permanent 计算输出概率。

核心公式:
- Hafnian: Haf(A) = Σ_{M∈PM(2n)} Π_{(i,j)∈M} A_{i,j}
- GBS 概率: P(s) ∝ Haf(A_s) / sqrt(det(σ))

来源（学术诚信 R02）:
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Björklund, 2012, Hafnian 算法
  https://arxiv.org/abs/1203.5687
- Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
  https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009

🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

import numpy as np


def hafnian(matrix: np.ndarray) -> float:
    """Hafnian 函数计算（GBS 核心）。

    Haf(A) = Σ_{M∈PM(2n)} Π_{(i,j)∈M} A_{i,j}

    其中 PM(2n) 是 2n 元素的完美匹配。

    来源:
    - Björklund, 2012, Hafnian 算法
      https://arxiv.org/abs/1203.5687
    - Hamilton et al., PRL 2017, GBS
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501

    Args:
        matrix: 对称矩阵 [2n, 2n]。

    Returns:
        Hafnian 值。
    """
    A = np.asarray(matrix, dtype=float)
    n = A.shape[0]
    if n % 2 != 0:
        return 0.0
    if n == 0:
        return 1.0
    if n == 2:
        return A[0, 1]
    # 暴力法（仅用于小规模验证）
    # 遍历所有完美匹配
    total = 0.0
    # 生成所有完美匹配
    def _matchings(remaining: list[int]) -> list[list[tuple[int, int]]]:
        if not remaining:
            return [[]]
        first = remaining[0]
        rest = remaining[1:]
        result = []
        for i, partner in enumerate(rest):
            new_remaining = rest[:i] + rest[i + 1:]
            for m in _matchings(new_remaining):
                result.append([(first, partner)] + m)
        return result

    matchings = _matchings(list(range(n)))
    for matching in matchings:
        prod = 1.0
        for i, j in matching:
            prod *= A[i, j]
        total += prod
    return total


def gbs_probability(
    covariance_matrix: np.ndarray,
    output_state: tuple[int, ...],
) -> float:
    """Gaussian Boson Sampling 输出概率。

    P(s) ∝ Haf(A_s) / sqrt(det(σ))

    来源:
    - Hamilton et al., PRL 2017
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501

    Args:
        covariance_matrix: 协方差矩阵 [M, M]。
        output_state: 输出模式。

    Returns:
        输出概率（未归一化）。
    """
    sigma = np.asarray(covariance_matrix, dtype=float)
    M = sigma.shape[0]
    if len(output_state) != M:
        raise ValueError(
            f"输出模式数须 = {M}，得到 {len(output_state)}"
        )
    # 构造子矩阵 A_s: 取 output_state 中 s_i=1 对应的行列
    indices = [i for i, s in enumerate(output_state) if s > 0]
    if len(indices) == 0:
        return 1.0
    sub_matrix = sigma[np.ix_(indices, indices)]
    haf = hafnian(sub_matrix)
    # 归一化项（简化: 用行列式）
    det_sigma = np.linalg.det(sigma + np.eye(M) * 1e-10)
    return float(haf ** 2 / max(abs(det_sigma), 1e-10))


__all__ = [
    "gbs_probability",
    "hafnian",
]
