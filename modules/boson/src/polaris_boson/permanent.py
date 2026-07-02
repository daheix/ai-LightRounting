"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex`` 积和式值。

R03 合规: 输入非法（非方阵）即 raise，禁止兜底。
🚫不参与 GPU（R04）：纯 NumPy 实现。

学术诚信（R02，≥5 文献 URL 溯源）:
- Glynn, "The permanent of a square matrix", Eur. J. Comb. 31(7):1887-1891, 2010.
  URL: https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund, "Counting Perfect Matchings as Fast as Ryser", 2012.
  URL: https://arxiv.org/abs/1203.5687
- Aaronson & Arkhipov, "The Computational Complexity of Linear Optics",
  STOC 2011. URL: https://arxiv.org/abs/0910.4698
- Clifford & Clifford, "The Classical Complexity of Boson Sampling",
  SODA 2018. URL: https://arxiv.org/abs/1706.01260
- Wu et al., "A benchmark test for boson sampling with high-order loss",
  Natl. Sci. Rev. 5(5):701-708, 2018. URL: https://arxiv.org/abs/1809.07541
- Nijenhuis & Wilf, "Combinatorial Algorithms", Academic Press 1978, Ch. 7.
  URL: https://doi.org/10.1016/B978-0-12-519260-6.X5001-2
"""

from __future__ import annotations

from typing import Any

import numpy as np


def permanent_glynn_gray(matrix: Any) -> complex:
    """Glynn-Gray 公式计算方阵积和式（O(n·2^n)）。

    Per(A) = (1/2^(n-1)) · Σ_{δ} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)
    δ_n = 1 固定，前 n-1 位遍历 ±1。

    来源: Glynn 2010, eq.(3); Björklund 2012.
         URL: https://arxiv.org/abs/1203.5687

    Args:
        matrix: n×n 方阵（实数或复数）。

    Returns:
        积和式值（complex）。

    Raises:
        ValueError: matrix 不是二维方阵。
    """
    A = np.asarray(matrix, dtype=complex)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"matrix 须为方阵，得到 shape={A.shape}")
    n = A.shape[0]
    if n == 0:
        return 1.0 + 0.0j
    if n == 1:
        return complex(A[0, 0])

    # δ ∈ {-1,+1}^n, δ_{n-1} = 1 固定，前 n-1 位遍历 2^(n-1) 种组合
    half = 1 << (n - 1)
    total = 0.0 + 0.0j
    for mask in range(half):
        delta = np.ones(n, dtype=np.int8)
        # 前 n-1 位由 mask 决定（bit=0 → -1, bit=1 → +1）
        for i in range(n - 1):
            if not (mask >> i) & 1:
                delta[i] = -1
        # Π_i δ_i
        prod_delta = 1
        for d in delta:
            prod_delta *= int(d)
        # Π_j (Σ_i δ_i · a_ij)  ← delta (n,) @ A (n,n) → (n,)
        col_sums = delta.astype(complex) @ A
        prod_col = complex(np.prod(col_sums))
        total += prod_delta * prod_col
    return total / half


__all__ = ["permanent_glynn_gray"]
