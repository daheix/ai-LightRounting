"""矩阵积和式（Permanent）计算 — 玻色采样核心算子。

单一职责: Ryser 算法（O(N·2^N)）与暴力法（O(N!)，仅验证用）计算矩阵积和式。
积和式是玻色采样/GBS 输出概率的核心算子，本模块为 polaris-quantum-advanced
所有玻色采样类模块的公共底座（无外部 polaris 依赖）。

Input / Process / Output
------------------------
Input:
    matrix — n×n 方阵（复数或实数 ndarray）。
Process:
    Ryser 容斥原理: Per(A) = (-1)^n Σ_{S⊆[n], S≠∅} (-1)^|S| Π_i (Σ_{j∈S} A_{i,j})
    暴力法: 遍历 S_n 全排列 Π_i A_{i,σ(i)}（仅小规模验证）。
Output:
    积和式值（complex 或 float）。

学术诚信（R02，≥5 文献 URL 溯源）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样 #P-hard
  https://arxiv.org/abs/0910.4698
- Björklund, 2012, "Counting Perfect Matchings as Fast as Ryser"
  https://arxiv.org/abs/1203.5687
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Ryser, 1963, "Combinatorial Mathematics"（积和式容斥算法）

设计原则
--------
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 非方阵 → raise ValueError
"""

from __future__ import annotations

from itertools import permutations

import numpy as np

__all__ = ["permanent_ryser", "permanent_brute_force"]


def permanent_ryser(matrix: np.ndarray) -> complex | float:
    """Ryser 算法计算矩阵积和式（O(N·2^N)）。

    Per(A) = (-1)^n Σ_{S⊆[n], S≠∅} (-1)^|S| Π_{i=1}^n Σ_{j∈S} A_{i,j}

    来源: Ryser 1963; Aaronson & Arkhipov STOC 2011
    https://arxiv.org/abs/0910.4698

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
    total = 0.0
    for subset in range(1, 1 << n):
        k = bin(subset).count("1")
        sign = (-1) ** k
        cols = [j for j in range(n) if subset & (1 << j)]
        row_sums = A[:, cols].sum(axis=1)
        prod = np.prod(row_sums)
        total += sign * prod
    return (-1) ** n * total


def permanent_brute_force(matrix: np.ndarray) -> complex | float:
    """暴力法计算积和式（O(N!)，仅用于验证）。

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
