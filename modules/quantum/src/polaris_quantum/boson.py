"""玻色采样（Boson Sampling）模块 — Aaronson-Arkhipov 量子优势 benchmark。

实现 Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)，
并基于此构建完整的玻色采样器：输入酉矩阵 U + 输入光子态 → 输出概率分布。

核心公式（Aaronson-Arkhipov 2011）:
    P(s|t) = |Per(U_{S,T})|² / (s_1! · ... · s_M! · t_1! · ... · t_M!)
其中 U_{S,T} 是按输出模式 S 重复行、按输入模式 T 重复列得到的 n×n 子矩阵，
n = Σ s_i = Σ t_i 为总光子数。

Glynn-Gray 公式:
    Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)
    δ_n = 1 固定，前 n-1 个分量遍历 ±1，共 2^(n-1) 项。复杂度 O(n·2^n)。
    与 Ryser 同阶但常数因子更小（无 (-1)^|S| 符号翻转）。

R03 合规: 概率和必须 = 1.0（误差 < 1e-6），失败即 raise，禁止兜底。

学术诚信（R02，≥5 文献 URL 溯源）:
- Aaronson & Arkhipov, "The Computational Complexity of Linear Optics",
  STOC 2011. URL: https://arxiv.org/abs/0910.4698
- Aaronson & Arkhipov, "BosonSampling is far from uniform",
  Quantum Inf. Comput. 14(15-16):1383-1423, 2014.
  URL: https://arxiv.org/abs/1309.7460
- Clifford & Clifford, "The Classical Complexity of Boson Sampling",
  SODA 2018, pp. 146-155. URL: https://arxiv.org/abs/1706.01260
- Clifford & Clifford, "Faster Classical Boson Sampling",
  arXiv:2005.04214, 2020. URL: https://arxiv.org/abs/2005.04214
- Wu et al., "A benchmark test for boson sampling with high-order loss",
  Natl. Sci. Rev. 5(5):701-708, 2018. URL: https://arxiv.org/abs/1809.07541
- Zhong et al. (Hefei Ji-Zhang), "Quantum computational advantage using photons",
  Science 370(6523):1460-1463, 2020. URL: https://arxiv.org/abs/2012.01625
- Glynn, "The permanent of a square matrix", Eur. J. Comb. 31(7):1887-1891, 2010.
  URL: https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund, "Counting Perfect Matchings as Fast as Ryser", 2012.
  URL: https://arxiv.org/abs/1203.5687

🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

import math
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


def _to_complex_matrix(unitary: Any) -> np.ndarray:
    """将 unitary（list of list of [real, imag]）转为 numpy 复矩阵。

    兼容 [real, imag] 二元组、复数、实数输入。R03: 非法输入 raise。

    Args:
        unitary: M×M 矩阵，元素为 [real, imag] / complex / real。

    Returns:
        M×M numpy complex 矩阵。

    Raises:
        RuntimeError: unitary 非 list/tuple / 非方阵 / 元素格式非法。
    """
    if not isinstance(unitary, (list, tuple)):
        raise RuntimeError(
            f"unitary 必须是 list/tuple，得到 {type(unitary).__name__}"
        )
    n = len(unitary)
    if n == 0:
        raise RuntimeError("unitary 不能为空")
    U = np.zeros((n, n), dtype=complex)
    for i in range(n):
        row = unitary[i]
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise RuntimeError(
                f"unitary 行 {i} 须为长度 {n} 的 list/tuple，"
                f"得到 {type(row).__name__} len="
                f"{len(row) if hasattr(row, '__len__') else '?'}"
            )
        for j in range(n):
            elem = row[j]
            if isinstance(elem, (list, tuple)):
                if len(elem) != 2:
                    raise RuntimeError(
                        f"unitary[{i}][{j}] 须为 [real, imag]，"
                        f"得到长度 {len(elem)}"
                    )
                U[i, j] = complex(float(elem[0]), float(elem[1]))
            elif isinstance(elem, complex):
                U[i, j] = elem
            else:
                U[i, j] = complex(float(elem))
    return U


def _generate_output_states(n_photons: int, n_modes: int) -> list[tuple[int, ...]]:
    """递归生成所有光子数守恒的输出模式（n_photons 分配到 n_modes 个模式）。"""
    if n_modes == 1:
        return [(n_photons,)]
    if n_photons == 0:
        return [tuple([0] * n_modes)]
    states: list[tuple[int, ...]] = []
    for first in range(n_photons + 1):
        for rest in _generate_output_states(n_photons - first, n_modes - 1):
            states.append((first,) + rest)
    return states


def _build_submatrix(
    U: np.ndarray,
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> np.ndarray:
    """构造子矩阵 U_{S,T}：行按输出模式重复，列按输入模式重复。"""
    M = U.shape[0]
    rows: list[int] = []
    for i in range(M):
        rows.extend([i] * output_state[i])
    cols: list[int] = []
    for j in range(M):
        cols.extend([j] * input_state[j])
    if not rows or not cols:
        raise RuntimeError("输入/输出光子数为 0，无法构造子矩阵")
    return U[np.ix_(rows, cols)]


def _boson_probability(
    U: np.ndarray,
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> float:
    """单输出模式概率: |Per(U_{S,T})|² / (Π s_i! · Π t_j!)。

    来源: Aaronson & Arkhipov, STOC 2011, eq.(1).
         URL: https://arxiv.org/abs/0910.4698
    """
    sub = _build_submatrix(U, input_state, output_state)
    per = permanent_glynn_gray(sub)
    norm = 1.0
    for s in output_state:
        norm *= math.factorial(s)
    for t in input_state:
        norm *= math.factorial(t)
    return float(abs(per) ** 2 / norm)


def boson_sampling(unitary: list, input_state: list) -> dict:
    """玻色采样: 输入酉矩阵 + 输入光子态 → 输出概率分布。

    P(s|t) = |Per(U_{S,T})|² / (s_1! · ... · s_M! · t_1! · ... · t_M!)

    遍历所有光子数守恒的输出模式，用 Glynn-Gray 公式计算 permanent，
    得到完整输出概率分布。

    R03: 概率和必须 = 1.0（误差 < 1e-6），失败 raise（输入非酉或算法错误）。

    来源: Aaronson & Arkhipov, STOC 2011.
         URL: https://arxiv.org/abs/0910.4698

    Args:
        unitary: M×M 酉矩阵，list of list of [real, imag]（与
            ``clements_unitary`` 输出格式一致）。
        input_state: 输入光子态 [n_1, ..., n_M]。

    Returns:
        {prob_distribution: list[float], prob_sum: float, n_outputs: int}
        - prob_distribution: 输出概率列表（按 _generate_output_states 顺序）。
        - prob_sum: 概率和（须 = 1.0，误差 < 1e-6）。
        - n_outputs: 输出模式数。

    Raises:
        RuntimeError: input_state 维度不匹配 / 含负值 / 概率和≠1.0。
    """
    U = _to_complex_matrix(unitary)
    M = U.shape[0]
    if len(input_state) != M:
        raise RuntimeError(
            f"input_state 长度 {len(input_state)} ≠ 模式数 {M}"
        )
    input_t = tuple(int(x) for x in input_state)
    if any(s < 0 for s in input_t):
        raise RuntimeError("input_state 不能含负值")
    n_photons = sum(input_t)
    if n_photons == 0:
        # 真空输入: 唯一输出（真空态）概率 1
        return {"prob_distribution": [1.0], "prob_sum": 1.0, "n_outputs": 1}

    output_states = _generate_output_states(n_photons, M)
    probs = [_boson_probability(U, input_t, out) for out in output_states]
    prob_sum = float(sum(probs))
    # R03: 禁止 fall-back，概率不归一即业务错误（输入非酉或算法实现错误）
    if abs(prob_sum - 1.0) > 1e-6:
        raise RuntimeError(
            f"玻色采样概率和 = {prob_sum} ≠ 1.0（误差 > 1e-6）；"
            f"输入酉矩阵可能非酉，或算法实现错误（R03 禁止兜底）"
        )
    return {
        "prob_distribution": probs,
        "prob_sum": prob_sum,
        "n_outputs": len(probs),
    }


__all__ = ["boson_sampling", "permanent_glynn_gray"]
