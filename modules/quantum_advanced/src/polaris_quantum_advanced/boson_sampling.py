"""线性光学网络与玻色采样分布模块。

单一职责: 分束器酉矩阵、HOM 双光子干涉、玻色采样输出概率与完整分布计算。
本模块为 polaris-quantum-advanced 的玻色采样基础层，供 lossy/numerical/
advanced_sampling 等模块复用。

Input / Process / Output
------------------------
Input:
    unitary — M×M 酉矩阵；input_state/output_state — 模式光子数元组。
Process:
    分束器酉: U = [[cos θ, -e^{-iφ} sin θ], [e^{iφ} sin θ, cos θ]]
    玻色采样概率: P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)（Ryser 积和式）
    HOM 干涉: |1,1⟩ 经 50:50 BS → |2,0⟩/|0,2⟩ 各 50%，|1,1⟩ 概率 0。
Output:
    BosonSamplingResult（含完整输出概率分布）/ 概率字典。

学术诚信（R02，≥5 文献 URL 溯源）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
  https://arxiv.org/abs/0910.4698
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Reck et al., PRL 1994, 线性光学网络分解
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537

设计原则
--------
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 光子数不守恒 / 维度不匹配 → raise
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from polaris_quantum_advanced.permanent import permanent_ryser

__all__ = [
    "BosonSamplingResult",
    "beamsplitter_unitary",
    "boson_sampling_distribution",
    "boson_sampling_prob",
    "hom_interference",
]


@dataclass
class BosonSamplingResult:
    """玻色采样结果。

    Attributes:
        input_state: 输入光子态 [n_1, n_2, ..., n_M]。
        output_prob: 输出模式概率分布 {(s_1,...,s_M): prob}。
        unitary: 线性光学网络酉矩阵 [M, M]。
        n_photons: 总光子数。
        n_modes: 模式数。
    """

    input_state: tuple[int, ...]
    output_prob: dict[tuple[int, ...], float]
    unitary: np.ndarray
    n_photons: int
    n_modes: int


def beamsplitter_unitary(theta: float, phi: float = 0.0) -> np.ndarray:
    """分束器酉矩阵 U = [[cos θ, -e^{-iφ} sin θ], [e^{iφ} sin θ, cos θ]]。

    50:50 分束器: θ=π/4。
    来源: Reck et al., PRL 1994 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
    """
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([
        [c, -np.exp(-1j * phi) * s],
        [np.exp(1j * phi) * s, c],
    ], dtype=complex)


def hom_interference(
    unitary: np.ndarray | None = None,
    theta: float = math.pi / 4,
) -> dict[str, float]:
    """HOM 干涉仿真: |1,1⟩ 经 50:50 BS，|1,1⟩ 概率 0（HOM 凹陷）。

    来源: Hong, Ou, Mandel, PRL 1987
    https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

    Args:
        unitary: 2×2 酉矩阵（None 用 50:50 分束器）。
        theta: 分束器角度（unitary=None 时使用）。

    Returns:
        概率分布字典 {"(2,0)": p, "(0,2)": p, "(1,1)": p}。
    """
    if unitary is None:
        unitary = beamsplitter_unitary(theta)
    U = np.asarray(unitary, dtype=complex)
    if U.shape != (2, 2):
        raise ValueError(f"HOM 干涉需 2×2 酉矩阵，得到 {U.shape}")
    # |2,0⟩: 子矩阵取第 0 列两次
    sub_20 = np.array([[U[0, 0], U[0, 0]], [U[1, 0], U[1, 0]]])
    p_20 = abs(permanent_ryser(sub_20) / math.sqrt(math.factorial(2))) ** 2
    # |0,2⟩: 子矩阵取第 1 列两次
    sub_02 = np.array([[U[0, 1], U[0, 1]], [U[1, 1], U[1, 1]]])
    p_02 = abs(permanent_ryser(sub_02) / math.sqrt(math.factorial(2))) ** 2
    # |1,1⟩: 子矩阵取第 0,1 列各一次
    sub_11 = np.array([[U[0, 0], U[0, 1]], [U[1, 0], U[1, 1]]])
    p_11 = abs(permanent_ryser(sub_11)) ** 2
    return {"(2,0)": float(p_20), "(0,2)": float(p_02), "(1,1)": float(p_11)}


def boson_sampling_prob(
    unitary: np.ndarray,
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> float:
    """玻色采样特定输出概率 P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)。

    来源: Aaronson & Arkhipov, STOC 2011 https://arxiv.org/abs/0910.4698

    Raises:
        ValueError: 输入/输出光子数不匹配或维度不一致。
    """
    U = np.asarray(unitary, dtype=complex)
    M = U.shape[0]
    if len(input_state) != M or len(output_state) != M:
        raise ValueError(
            f"输入/输出模式数须 = {M}，得到 input={len(input_state)}, "
            f"output={len(output_state)}"
        )
    n_in = sum(input_state)
    n_out = sum(output_state)
    if n_in != n_out:
        raise ValueError(f"输入光子数 ({n_in}) 须 = 输出光子数 ({n_out})")
    if n_in == 0:
        return 1.0
    rows = []
    for i, s in enumerate(output_state):
        for _ in range(s):
            rows.append(U[i, :])
    cols = []
    for j, n in enumerate(input_state):
        for _ in range(n):
            cols.append(j)
    sub_matrix = np.array(rows)[:, cols]
    per = permanent_ryser(sub_matrix)
    norm = 1.0
    for s in output_state:
        norm *= math.factorial(s)
    for n in input_state:
        norm *= math.factorial(n)
    return abs(per) ** 2 / norm


def boson_sampling_distribution(
    unitary: np.ndarray,
    input_state: tuple[int, ...],
) -> BosonSamplingResult:
    """计算玻色采样完整输出分布（遍历所有光子数守恒输出态）。"""
    U = np.asarray(unitary, dtype=complex)
    M = U.shape[0]
    n_photons = sum(input_state)
    output_states = _generate_output_states(n_photons, M)
    output_prob = {
        out_state: boson_sampling_prob(U, input_state, out_state)
        for out_state in output_states
    }
    return BosonSamplingResult(
        input_state=input_state,
        output_prob=output_prob,
        unitary=U,
        n_photons=n_photons,
        n_modes=M,
    )


def _generate_output_states(
    n_photons: int, n_modes: int
) -> list[tuple[int, ...]]:
    """生成所有光子数守恒的输出模式（n_photons 分配到 n_modes 个模式）。"""
    if n_modes == 1:
        return [(n_photons,)]
    if n_photons == 0:
        return [tuple([0] * n_modes)]
    states = []
    for first in range(n_photons + 1):
        for rest in _generate_output_states(n_photons - first, n_modes - 1):
            states.append((first,) + rest)
    return states
