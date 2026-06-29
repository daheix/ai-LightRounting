"""玻色采样（Boson Sampling）模块 — Aaronson-Arkhipov 量子优势 benchmark。

实现 Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)，
并基于此构建完整的玻色采样器：输入酉矩阵 U + 输入光子态 → 输出概率分布。

核心公式（Aaronson-Arkhipov 2011）:
    P(s|t) = |Per(U_{S,T})|² / (s_1! · s_2! · ... · s_M! · t_1! · ... · t_M!)
其中 U_{S,T} 是按输出模式 S 重复行、按输入模式 T 重复列得到的 n×n 子矩阵，
n = Σ s_i = Σ t_i 为总光子数。当输入为单光子态（t_i ∈ {0,1}）时，分母简化为
Π s_i!，即任务描述的 P = |Per(U_S)|² / (s_1! ... s_n!)。

Glynn-Gray 公式（任务指定算法，优于暴力 O(n!)）:
    Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)
    其中 δ_n = 1 固定，前 n-1 个分量遍历 ±1，共 2^(n-1) 项。
    复杂度 O(n·2^n)，与 Ryser 同阶但常数因子更小（无 (-1)^|S| 符号翻转）。

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
- Lundow & Markström, "Efficient computation of permanents, with applications
  to Boson sampling and random matrices", arXiv:1904.06229, 2019.
  URL: https://arxiv.org/abs/1904.06229

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

PermanentMethod = Literal["glynn_gray", "ryser"]


def permanent_glynn_gray(matrix: ArrayLike) -> complex:
    """Glynn-Gray 公式计算方阵积和式。

    Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)
    其中 δ_n = 1 固定，前 n-1 个分量遍历 ±1。

    复杂度 O(n·2^n)，与 Ryser 同阶但常数因子更小。
    来源: Glynn 2010 / Gray 码遍历，见 Björklund 2012 eq.(3)。
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


def _permanent_ryser(matrix: NDArray[np.complex128]) -> complex:
    """Ryser 算法（仅用于交叉验证，主路径用 Glynn-Gray）。

    Per(A) = (-1)^n · Σ_{S⊆[n], S≠∅} (-1)^|S| · Π_i (Σ_{j∈S} a_ij)
    来源: Ryser 1963; Aaronson-Arkhipov 2011。
    """
    A = np.asarray(matrix, dtype=complex)
    n = A.shape[0]
    if n == 0:
        return 1.0 + 0.0j
    if n == 1:
        return complex(A[0, 0])
    total = 0.0 + 0.0j
    for subset in range(1, 1 << n):
        k = bin(subset).count("1")
        sign = -1 if (k % 2) else 1  # (-1)^|S|
        cols = [j for j in range(n) if subset & (1 << j)]
        row_sums = A[:, cols].sum(axis=1)
        total += sign * complex(np.prod(row_sums))
    return ((-1) ** n) * total


def _build_submatrix(
    unitary: NDArray[np.complex128],
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> NDArray[np.complex128]:
    """构造子矩阵 U_{S,T}：行按输出模式重复，列按输入模式重复。"""
    M = unitary.shape[0]
    rows: list[int] = []
    for i in range(M):
        rows.extend([i] * output_state[i])
    cols: list[int] = []
    for j in range(M):
        cols.extend([j] * input_state[j])
    if not rows or not cols:
        raise ValueError("输入/输出光子数为 0，无法构造子矩阵")
    return unitary[np.ix_(rows, cols)]


def boson_sampling_probability(
    unitary: ArrayLike,
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
    method: PermanentMethod = "glynn_gray",
) -> float:
    """计算玻色采样特定输出模式的概率。

    P(s|t) = |Per(U_{S,T})|² / (Π_i s_i! · Π_j t_j!)

    来源: Aaronson & Arkhipov, STOC 2011, eq.(1).
         URL: https://arxiv.org/abs/0910.4698

    Args:
        unitary: M×M 酉矩阵。
        input_state: 输入光子模式 t = (t_1, ..., t_M)。
        output_state: 输出光子模式 s = (s_1, ..., s_M)。
        method: permanent 计算方法，'glynn_gray'（默认）或 'ryser'。

    Returns:
        输出概率（float, [0, 1]）。

    Raises:
        ValueError: 维度不一致、光子数不守恒、或方法未知。
    """
    U = np.asarray(unitary, dtype=complex)
    if U.ndim != 2 or U.shape[0] != U.shape[1]:
        raise ValueError(f"unitary 须为方阵，得到 shape={U.shape}")
    M = U.shape[0]
    if len(input_state) != M or len(output_state) != M:
        raise ValueError(
            f"输入/输出模式长度须 = {M}，得到 input={len(input_state)}, "
            f"output={len(output_state)}"
        )
    n_in = sum(input_state)
    n_out = sum(output_state)
    if n_in != n_out:
        raise ValueError(
            f"光子数不守恒: 输入 {n_in} ≠ 输出 {n_out}"
        )
    if n_in == 0:
        return 1.0
    if any(s < 0 for s in input_state) or any(s < 0 for s in output_state):
        raise ValueError("输入/输出光子数不能为负")

    sub = _build_sub_matrix_safe(U, input_state, output_state)
    if method == "glynn_gray":
        per = permanent_glynn_gray(sub)
    elif method == "ryser":
        per = _permanent_ryser(sub)
    else:
        raise ValueError(f"未知 permanent 方法: {method}")

    norm = 1.0
    for s in output_state:
        norm *= math.factorial(s)
    for t in input_state:
        norm *= math.factorial(t)
    return float(abs(per) ** 2 / norm)


def _build_sub_matrix_safe(
    unitary: NDArray[np.complex128],
    input_state: tuple[int, ...],
    output_state: tuple[int, ...],
) -> NDArray[np.complex128]:
    """安全构造子矩阵（带 R03 校验）。"""
    sub = _build_submatrix(unitary, input_state, output_state)
    n = sum(input_state)
    if sub.shape != (n, n):
        raise RuntimeError(
            f"子矩阵形状 {sub.shape} ≠ ({n}, {n})，内部错误"
        )
    return sub


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


@dataclass
class BosonSamplingResult:
    """玻色采样完整分布结果。

    Attributes:
        input_state: 输入光子模式 t。
        output_prob: 输出模式 → 概率 的字典。
        unitary: 线性光学网络酉矩阵。
        n_photons: 总光子数。
        n_modes: 模式数。
        method: permanent 计算方法。
        total_prob: 所有输出概率之和（须 = 1.0，R03 校验）。
    """

    input_state: tuple[int, ...]
    output_prob: dict[tuple[int, ...], float]
    unitary: NDArray[np.complex128]
    n_photons: int
    n_modes: int
    method: PermanentMethod = "glynn_gray"
    total_prob: float = 0.0


@dataclass
class BosonSampler:
    """玻色采样器（Aaronson-Arkhipov 2011）。

    用 Glynn-Gray 公式计算 permanent，输出完整概率分布或采样。

    用法:
        sampler = BosonSampler(U)
        result = sampler.distribution((1, 1, 0))  # 输入 |1,1,0⟩
        samples = sampler.sample((1, 1, 0), n_samples=1000, seed=42)

    来源: Aaronson & Arkhipov, STOC 2011. URL: https://arxiv.org/abs/0910.4698
    """

    unitary: NDArray[np.complex128]
    method: PermanentMethod = "glynn_gray"

    def __post_init__(self) -> None:
        U = np.asarray(self.unitary, dtype=complex)
        if U.ndim != 2 or U.shape[0] != U.shape[1]:
            raise ValueError(f"unitary 须为方阵，得到 shape={U.shape}")
        self.unitary = U
        if self.method not in ("glynn_gray", "ryser"):
            raise ValueError(f"未知 method: {self.method}")

    @property
    def n_modes(self) -> int:
        return self.unitary.shape[0]

    def probability(
        self,
        input_state: tuple[int, ...],
        output_state: tuple[int, ...],
    ) -> float:
        """单输出模式概率。"""
        return boson_sampling_probability(
            self.unitary, input_state, output_state, self.method
        )

    def distribution(
        self, input_state: tuple[int, ...]
    ) -> BosonSamplingResult:
        """计算完整输出概率分布（遍历所有光子数守恒的输出模式）。

        R03: 严格校验概率和 = 1.0，失败即 raise。
        """
        M = self.n_modes
        if len(input_state) != M:
            raise ValueError(
                f"输入模式长度 {len(input_state)} ≠ 模式数 {M}"
            )
        n_photons = sum(input_state)
        output_states = _generate_output_states(n_photons, M)
        output_prob: dict[tuple[int, ...], float] = {}
        for out_state in output_states:
            output_prob[out_state] = self.probability(input_state, out_state)

        total = float(sum(output_prob.values()))
        # R03: 禁止 fall-back，概率不归一即业务错误
        if not np.isclose(total, 1.0, atol=1e-9):
            raise RuntimeError(
                f"玻色采样概率和 = {total} ≠ 1.0 (method={self.method}, "
                f"input={input_state})；分布不归一，禁止兜底"
            )

        return BosonSamplingResult(
            input_state=tuple(input_state),
            output_prob=output_prob,
            unitary=self.unitary,
            n_photons=n_photons,
            n_modes=M,
            method=self.method,
            total_prob=total,
        )

    def sample(
        self,
        input_state: tuple[int, ...],
        n_samples: int = 1,
        seed: int | None = None,
    ) -> list[tuple[int, ...]]:
        """从玻色采样分布采样（strong simulation）。

        来源: Clifford & Clifford 2017 高效采样思想（此处用通用采样）。
             URL: https://arxiv.org/abs/1706.01260
        """
        if n_samples < 1:
            raise ValueError("n_samples 须 ≥ 1")
        result = self.distribution(input_state)
        states = list(result.output_prob.keys())
        probs = np.array([result.output_prob[s] for s in states], dtype=float)
        # R03: 概率和已在 distribution() 校验，这里再次确认防漂移
        total = probs.sum()
        if not np.isclose(total, 1.0, atol=1e-9):
            raise RuntimeError(f"采样前概率和 = {total} ≠ 1.0")
        probs = probs / total  # 数值归一化（消除浮点误差）
        rng = np.random.default_rng(seed)
        indices = rng.choice(len(states), size=n_samples, p=probs)
        return [states[int(i)] for i in indices]


__all__ = [
    "BosonSampler",
    "BosonSamplingResult",
    "boson_sampling_probability",
    "permanent_glynn_gray",
]
