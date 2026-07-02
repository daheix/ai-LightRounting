"""KLM CNOT 物理仿真辅助函数（自包含，纯 NumPy/SciPy CPU，R04 兼容）。

学术依据（R02，≥5 个文献 URL）:
1. Knill, Laflamme, Milburn 2001 Nature 409 46-52,
   "A scheme for efficient quantum computation with linear optics"
   https://www.nature.com/articles/35051009
2. Ralph, Langford, Bell, White 2002 PRA 65 062324,
   "Linear optical controlled-NOT gate in the coincidence basis"
   https://doi.org/10.1103/PhysRevA.65.062324
3. Hofmann & Takeuchi 2002 PRA 66 024308,
   "Quantum phase gate for two qubits using single photons and linear optics"
   https://doi.org/10.1103/PhysRevA.66.024308
4. O'Brien et al. 2003 Nature 426 264-267,
   "Demonstration of an all-optical quantum controlled-NOT gate"
   https://doi.org/10.1038/nature02354
5. Knill 2002 PRA 66 052306, "Quantum gating using quantum interference"
   https://doi.org/10.1103/PhysRevA.66.052306
6. Aaronson & Arkhipov 2011 STOC, "The Computational Complexity of Linear Optics"
   https://arxiv.org/abs/0910.4698

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


def _permanent_ryser(matrix: NDArray[np.complex128]) -> complex:
    """Ryser 算法计算 n×n 矩阵积和式 (permanent)，复杂度 O(2^n · n)。

    perm(M) = (-1)^n · Σ_{S⊆[n], S≠∅} (-1)^|S| · Π_i (Σ_{j∈S} M_{ij})

    来源:
    - Ryser, "Combinatorial Mathematics", 1963.
    - Aaronson & Arkhipov, STOC 2011, 玻色采样 #P-hard。
      https://arxiv.org/abs/0910.4698

    Args:
        matrix: n×n 方阵。

    Returns:
        积和式值（复数）。
    """
    n = matrix.shape[0]
    if n == 0:
        return complex(1.0)
    total = complex(0.0)
    for subset in range(1, 1 << n):
        cols = [j for j in range(n) if subset & (1 << j)]
        col_sums = matrix[:, cols].sum(axis=1)
        prod = complex(1.0)
        for s in col_sums:
            prod *= s
        sign = 1 if (len(cols) % 2 == 0) else -1
        total += sign * prod
    return total * ((-1) ** n)


def _klm_cnot_unitary() -> NDArray[np.complex128]:
    """KLM CNOT 4 模式电路酉矩阵（Ralph 2002 简化版）。

    模式: control(0), target(1), aux1(2), aux2(3)
    分束器网络:
      BS1(control=0, aux1=2): θ₁ = arccos(√(2/3))
      BS2(target=1,  aux2=3): θ₂ = arccos(√(2/3))
      BS3(aux1=2,    aux2=3): θ₃ = π/4 (50:50)
      BS4(control=0, target=1): θ₄ = arccos(√(1/3))

    来源:
    - Ralph, Langford, Bell, White, PRA 2002.
      https://doi.org/10.1103/PhysRevA.65.062324
    - Knill, Laflamme, Milburn, Nature 2001.
      https://www.nature.com/articles/35051009

    Returns:
        4×4 酉矩阵。
    """
    theta1 = math.acos(math.sqrt(2.0 / 3.0))
    theta2 = math.acos(math.sqrt(2.0 / 3.0))
    theta3 = math.pi / 4
    theta4 = math.acos(math.sqrt(1.0 / 3.0))

    def beamsplitter(theta: float) -> NDArray[np.complex128]:
        return np.array([
            [np.cos(theta), 1j * np.sin(theta)],
            [1j * np.sin(theta), np.cos(theta)],
        ], dtype=np.complex128)

    def apply_bs(
        U: NDArray[np.complex128], theta: float, i: int, j: int,
    ) -> NDArray[np.complex128]:
        V = U.copy()
        V[[i, j], :] = beamsplitter(theta) @ U[[i, j], :]
        return V

    U = np.eye(4, dtype=np.complex128)
    U = apply_bs(U, theta1, 0, 2)
    U = apply_bs(U, theta2, 1, 3)
    U = apply_bs(U, theta3, 2, 3)
    U = apply_bs(U, theta4, 0, 1)
    return U


def _klm_cnot_post_select_probability() -> float:
    """计算 KLM CNOT 后选择成功率（输入 |1,1,1,1⟩，辅助模式各 1 光子）。

    玻色采样: P(output | input) = |Permanent(U_sub)|² / (Π n_i! · Π m_j!)
    后选择条件: aux1(模式2)=1 光子, aux2(模式3)=1 光子。

    来源:
    - Knill, Laflamme, Milburn, Nature 2001.
      https://www.nature.com/articles/35051009
    - Aaronson & Arkhipov, STOC 2011. https://arxiv.org/abs/0910.4698

    Returns:
        后选择成功率 (0, 1)。

    Raises:
        RuntimeError: 后选择成功率为零（电路实现错误）。
    """
    U = _klm_cnot_unitary()
    input_state = (1, 1, 1, 1)
    n_photons = sum(input_state)
    prob_total = 0.0
    for m0 in range(n_photons + 1):
        for m1 in range(n_photons - m0 + 1):
            for m2 in range(n_photons - m0 - m1 + 1):
                m3 = n_photons - m0 - m1 - m2
                if m2 != 1 or m3 != 1:
                    continue
                output_state = (m0, m1, m2, m3)
                prob_total += _boson_probability(
                    U, input_state, output_state
                )
    if prob_total <= 0.0:
        raise RuntimeError("KLM CNOT 后选择成功率为零，电路实现错误")
    return float(prob_total)


def _boson_probability(
    U: NDArray[np.complex128],
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> float:
    """玻色采样单输出态概率: |Permanent(U_sub)|² / (Π n_i! · Π m_j!)。

    U_sub 按输入/输出光子数重复行列构造。

    来源: Aaronson & Arkhipov, STOC 2011. https://arxiv.org/abs/0910.4698
    """
    n_modes = len(input_state)
    rows: list[int] = []
    for i in range(n_modes):
        rows.extend([i] * output_state[i])
    cols: list[int] = []
    for j in range(n_modes):
        cols.extend([j] * input_state[j])
    if len(rows) != len(cols) or len(rows) == 0:
        return 0.0
    U_sub = U[np.ix_(rows, cols)]
    perm = _permanent_ryser(U_sub)
    in_factorial = 1
    for n in input_state:
        in_factorial *= math.factorial(n)
    out_factorial = 1
    for m in output_state:
        out_factorial *= math.factorial(m)
    return float((abs(perm) ** 2) / (in_factorial * out_factorial))


__all__ = [
    "_permanent_ryser",
    "_klm_cnot_unitary",
    "_klm_cnot_post_select_probability",
    "_boson_probability",
]
