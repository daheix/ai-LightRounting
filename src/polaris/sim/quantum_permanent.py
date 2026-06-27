"""R35: 矩阵积和式（Permanent）计算 — 玻色采样核心模块。

实现 Ryser 算法（O(N·2^N)）和暴力法（O(N!)，仅用于验证）。
积和式是玻色采样输出概率的核心算子。

公式:
    Per(A) = Σ_{σ∈S_n} Π_{i=1}^n A_{i,σ(i)}

Ryser 算法（inclusion-exclusion）:
    Per(A) = (-1)^n Σ_{S⊆[n]} (-1)^|S| Π_{i=1}^n Σ_{j∈S} A_{i,j}

来源（学术诚信 R02）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
  https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Ryser, 1963, Combinatorial Mathematics（积和式算法）
- Björklund, 2012, "Counting Perfect Matchings as Fast as Ryser"
  https://arxiv.org/abs/1203.5687
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009

🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

from itertools import permutations

import numpy as np


def permanent_ryser(matrix: np.ndarray) -> complex | float:
    """Ryser 算法计算矩阵积和式。

    Per(A) = Σ_{σ∈S_n} Π_{i=1}^n A_{i,σ(i)}

    Ryser 算法复杂度 O(N·2^N)，优于暴力 O(N!)。

    公式（ inclusion-exclusion）:
        Per(A) = (-1)^n Σ_{S⊆[n]} (-1)^|S| Π_{i=1}^n Σ_{j∈S} A_{i,j}

    来源:
    - Ryser, 1963, Combinatorial Mathematics
    - Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
    - Björklund, 2012, "Counting Perfect Matchings as Fast as Ryser"
      https://arxiv.org/abs/1203.5687

    Args:
        matrix: 方阵 [N, N]。

    Returns:
        积和式值（complex 或 float）。

    Raises:
        ValueError: matrix 不是方阵。
    """
    A = np.asarray(matrix)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"matrix 须为方阵，得到 {A.shape}")
    n = A.shape[0]
    if n == 0:
        return 1.0
    if n == 1:
        return A[0, 0]
    # Ryser 算法：遍历 [1, 2^n - 1] 的所有非空子集
    # Per(A) = (-1)^n Σ_{S≠∅} (-1)^|S| Π_{i=1}^n Σ_{j∈S} A_{i,j}
    total = 0.0
    for subset in range(1, 1 << n):
        # 计算 subset 的元素个数 |S|
        k = bin(subset).count("1")
        # 符号因子 (-1)^|S|
        sign = (-1) ** k
        # 行和的乘积
        cols = [j for j in range(n) if subset & (1 << j)]
        row_sums = A[:, cols].sum(axis=1)
        prod = np.prod(row_sums)
        total += sign * prod
    return (-1) ** n * total


def permanent_brute_force(matrix: np.ndarray) -> complex | float:
    """暴力法计算积和式（仅用于验证，O(N!)）。

    Args:
        matrix: 方阵 [N, N]。

    Returns:
        积和式值。
    """
    A = np.asarray(matrix)
    n = A.shape[0]
    if n == 0:
        return 1.0
    total = 0.0
    for perm in permutations(range(n)):
        prod = 1.0
        for i, j in enumerate(perm):
            prod *= A[i, j]
        total += prod
    return total


__all__ = [
    "permanent_brute_force",
    "permanent_ryser",
]
