"""R556 大模式数玻色采样 + R557 HOM 干涉增强模块。

单一职责:
- R556 LargeScaleBosonSampler: Clifford-Clifford 2018 逐光子条件采样，
  支持模式数 >20（标准枚举法爆炸时仍可用）。
- R557 HOMInterferometer: 部分可分性 + 多光子 Tichy 双置换和 HOM 干涉。

*创新* R556: 不枚举所有输出态，第 k 个光子条件概率
P(m|S_{k-1}) ∝ |Per(U_sub(S+[m]))|²，由 Ryser 积和式计算，复杂度 O(M·n²·2^n)。
*创新* R557: 用 Hadamard 积 U_sub∘S_sub 统一描述全同/部分可分/完全可分，
ξ=1 退化为标准 HOM（凹陷=0），ξ=0 退化为经典（无凹陷）。

Input / Process / Output
------------------------
Input:
    unitary — M×M 酉矩阵；input_state — 输入模式；distinguishability — 可分性 ξ∈[0,1]。
Process:
    R556: 逐光子条件采样 P(m|S) ∝ |Per(U_sub)|²，rng.choice 抽取模式。
    R557: 全同(ξ=1) P(s)=|Per(U_sub)|²/Πs_i!；部分可分 Tichy 双置换和。
Output:
    BosonSampleResult / HOMResult（含概率分布、coincidence、bunching）。

学术诚信（R02，≥5 文献 URL 溯源）:
- Clifford & Clifford, SODA 2018, 逐光子玻色采样算法
  https://arxiv.org/abs/1706.01260
- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Tichy, PRA 91, 022103 (2015), 部分可分多光子干涉
  https://doi.org/10.1103/PhysRevA.91.022103
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537

设计原则
--------
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 非酉/概率全零/光子数过大 → raise
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from polaris_quantum_advanced.permanent import permanent_ryser

__all__ = [
    "BosonSampleResult",
    "LargeScaleBosonSampler",
    "HOMResult",
    "HOMInterferometer",
]


def _generate_output_states(
    n_photons: int, n_modes: int
) -> list[tuple[int, ...]]:
    """枚举 n_photons 个光子在 n_modes 个模式的所有输出态（递归）。"""
    if n_photons == 0:
        return [tuple([0] * n_modes)]
    if n_modes == 1:
        return [(n_photons,)]
    states: list[tuple[int, ...]] = []
    for k in range(n_photons + 1):
        for rest in _generate_output_states(n_photons - k, n_modes - 1):
            states.append((k,) + rest)
    return states


@dataclass
class BosonSampleResult:
    """R556 单次玻色采样结果。"""

    output_state: tuple[int, ...]
    n_photons: int
    n_modes: int
    n_steps: int  # 采样步数（= 光子数）


class LargeScaleBosonSampler:
    """R556 大模式数玻色采样增强（Clifford-Clifford 算法）。

    标准分布需枚举所有输出态（M 模式 n 光子共 C(M+n-1,n) 个），模式数 >20
    时光子数 ≥5 即爆炸。本采样器按 Clifford & Clifford 2018 SODA 算法
    逐光子条件采样，复杂度 O(M·n²·2^n)，支持 >20 模式。

    *创新*: 不枚举所有输出态，第 k 个光子条件概率
    P(m|S_{k-1}) ∝ |Per(U_sub(S+[m]))|²，由 Ryser 积和式计算。

    来源: Clifford & Clifford 2018 SODA https://arxiv.org/abs/1706.01260

    Raises:
        ValueError: 矩阵非方阵 / 非酉 / 维度 ≤0。
    """

    def __init__(self, unitary: ArrayLike, seed: int | None = None) -> None:
        U = np.asarray(unitary, dtype=complex)
        if U.ndim != 2 or U.shape[0] != U.shape[1]:
            raise ValueError(f"酉矩阵须为方阵，得到 {U.shape}")
        if U.shape[0] <= 0:
            raise ValueError("模式数须 ≥ 1")
        if not np.allclose(U @ U.conj().T, np.eye(U.shape[0]), atol=1e-8):
            raise ValueError("输入矩阵须为酉矩阵（U U† ≠ I）")
        self.unitary = U
        self.n_modes = U.shape[0]
        self._rng = np.random.default_rng(seed)

    def _build_submatrix(
        self, rows: list[int], cols: list[int]
    ) -> NDArray[np.complex128]:
        """按行/列索引列表（允许重复）构造子矩阵。"""
        row_arr = np.asarray(rows, dtype=int)[:, None]
        col_arr = np.asarray(cols, dtype=int)[None, :]
        return self.unitary[row_arr, col_arr]

    def sample(self, input_state: tuple[int, ...]) -> BosonSampleResult:
        """对给定输入态执行单次玻色采样（Clifford-Clifford 逐光子算法）。"""
        if len(input_state) != self.n_modes:
            raise ValueError(
                f"输入态维度须 = {self.n_modes}，得到 {len(input_state)}"
            )
        if any(n < 0 for n in input_state):
            raise ValueError("输入态含负光子数")
        photons: list[int] = []
        for mode, n in enumerate(input_state):
            photons.extend([mode] * n)
        n = len(photons)
        if n == 0:
            return BosonSampleResult(
                output_state=tuple([0] * self.n_modes),
                n_photons=0, n_modes=self.n_modes, n_steps=0,
            )
        chosen: list[int] = []
        cols_prefix: list[int] = []
        for k in range(n):
            cols_prefix.append(photons[k])
            probs = self._conditional_probs(chosen, cols_prefix)
            m_chosen = int(self._rng.choice(self.n_modes, p=probs))
            chosen.append(m_chosen)
        output = [0] * self.n_modes
        for m in chosen:
            output[m] += 1
        return BosonSampleResult(
            output_state=tuple(output),
            n_photons=n, n_modes=self.n_modes, n_steps=n,
        )

    def _conditional_probs(
        self, chosen: list[int], cols: list[int]
    ) -> NDArray[np.float64]:
        """条件概率 P(m|S) ∝ |Per(U_sub(S+[m],cols))|²，归一化。"""
        M = self.n_modes
        probs = np.zeros(M, dtype=np.float64)
        for m in range(M):
            sub = self._build_submatrix(chosen + [m], cols)
            probs[m] = float(abs(permanent_ryser(sub)) ** 2)
        total = probs.sum()
        if total <= 0.0:
            raise ValueError(
                f"条件概率全零（已选 {chosen}），输入态或酉矩阵数值退化"
            )
        return probs / total

    def sample_batch(
        self, input_state: tuple[int, ...], n_samples: int
    ) -> list[BosonSampleResult]:
        """批量采样。"""
        if n_samples <= 0:
            raise ValueError("n_samples 须 ≥ 1")
        return [self.sample(input_state) for _ in range(n_samples)]


@dataclass
class HOMResult:
    """R557 HOM 干涉结果。"""

    probabilities: dict[tuple[int, ...], float]
    coincidence_probability: float  # P(每个模式各 1 个光子)
    bunching_parameter: float  # 1 - P_coincidence/P_classical
    is_bunched: bool


class HOMInterferometer:
    """R557 Hong-Ou-Mandel 干涉精确仿真（部分可分 + 多光子）。

    标准 2 光子 HOM: 50:50 分束器输入 |1,1⟩，输出 |2,0⟩/|0,2⟩ 各 50%，
    |1,1⟩ 概率 0（HOM 凹陷）。

    *创新*: 用 Hadamard 积 U_sub∘S_sub 统一描述全同/部分可分/完全可分，
    ξ=1 退化为标准 HOM（凹陷=0），ξ=0 退化为经典（无凹陷）。

    来源: Hong-Ou-Mandel 1987 PRL 59 2044
    https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044;
    Tichy 2015 PRA 91 022103 https://doi.org/10.1103/PhysRevA.91.022103

    Raises:
        ValueError: 矩阵非方阵 / 非酉。
    """

    def __init__(self, unitary: ArrayLike) -> None:
        U = np.asarray(unitary, dtype=complex)
        if U.ndim != 2 or U.shape[0] != U.shape[1]:
            raise ValueError(f"酉矩阵须为方阵，得到 {U.shape}")
        if not np.allclose(U @ U.conj().T, np.eye(U.shape[0]), atol=1e-8):
            raise ValueError("输入矩阵须为酉矩阵")
        self.unitary = U
        self.n_modes = U.shape[0]

    def _distinguishability_matrix(
        self, n_photons: int, distinguishability: float
    ) -> NDArray[np.complex128]:
        """可分性内积矩阵 S_ij=ξ^|i-j|（Tichy 2015 eq. 12）。

        ξ=1: S=ones（全同/不可分），ξ=0: S=I（完全可分/经典）。
        """
        if not 0.0 <= distinguishability <= 1.0:
            raise ValueError("distinguishability 须 ∈ [0,1]")
        idx = np.arange(n_photons)
        return np.power(
            distinguishability, np.abs(idx[:, None] - idx[None, :])
        ).astype(complex)

    def interfere(
        self,
        input_state: tuple[int, ...],
        distinguishability: float = 1.0,
    ) -> HOMResult:
        """计算 HOM 干涉输出分布。

        全同（ξ=1）: P(s)=|Per(U_sub)|²/Π s_i!（Ryser 快速路径）。
        部分可分（0≤ξ<1）: Tichy 2015 双置换和。
        """
        n = self._validate_interfere_input(input_state, distinguishability)
        photons_in = [i for i, k in enumerate(input_state) for _ in range(k)]
        probs = self._compute_hom_probabilities(
            input_state, distinguishability, n, photons_in,
        )
        p_coinc, bunching = self._compute_bunching_metrics(
            input_state, n, probs,
        )
        return HOMResult(
            probabilities=probs,
            coincidence_probability=p_coinc,
            bunching_parameter=float(bunching),
            is_bunched=(bunching > 0.5),
        )

    def _validate_interfere_input(
        self,
        input_state: tuple[int, ...],
        distinguishability: float,
    ) -> int:
        """校验 interfere 输入参数，返回总光子数 n。"""
        if len(input_state) != self.n_modes:
            raise ValueError(
                f"输入态维度须 = {self.n_modes}，得到 {len(input_state)}"
            )
        if not 0.0 <= distinguishability <= 1.0:
            raise ValueError("distinguishability 须 ∈ [0,1]")
        n = sum(input_state)
        if n == 0:
            raise ValueError("HOM 干涉须至少 1 个光子")
        if n > 12:
            raise ValueError(f"光子数 {n} > 12，输出态枚举爆炸（R03 禁止兜底）")
        if distinguishability < 1.0 and n > 6:
            raise ValueError(
                f"部分可分（ξ<1）时光子数须 ≤ 6（双置换和 O((n!)²)），得到 {n}"
            )
        return n

    def _compute_hom_probabilities(
        self,
        input_state: tuple[int, ...],
        distinguishability: float,
        n: int,
        photons_in: list[int],
    ) -> dict[tuple[int, ...], float]:
        """计算 HOM 输出概率分布（全同 / 部分可分两条路径）。"""
        if distinguishability == 1.0:
            return self._hom_prob_identical(n, photons_in)
        return self._hom_prob_partial(n, photons_in, distinguishability)

    def _hom_prob_identical(
        self, n: int, photons_in: list[int],
    ) -> dict[tuple[int, ...], float]:
        """全同光子（ξ=1）: P(s)=|Per(U_sub)|²/Π s_i!（Ryser 快速路径）。"""
        probs: dict[tuple[int, ...], float] = {}
        for out_s in _generate_output_states(n, self.n_modes):
            rows = [i for i, s in enumerate(out_s) for _ in range(s)]
            u_sub = self.unitary[np.ix_(rows, photons_in)]
            per = permanent_ryser(u_sub)
            norm = 1.0
            for s in out_s:
                norm *= math.factorial(s)
            probs[out_s] = float(abs(per) ** 2) / norm
        return self._normalize_probs(probs)

    def _hom_prob_partial(
        self, n: int, photons_in: list[int], distinguishability: float,
    ) -> dict[tuple[int, ...], float]:
        """部分可分（0≤ξ<1）: Tichy 2015 双置换和（O((n!)²) 复杂度）。"""
        S_full = self._distinguishability_matrix(n, distinguishability)
        perms = list(permutations(range(n)))
        idx = np.arange(n)
        probs: dict[tuple[int, ...], float] = {}
        for out_s in _generate_output_states(n, self.n_modes):
            rows = [i for i, s in enumerate(out_s) for _ in range(s)]
            u_sub = self.unitary[np.ix_(rows, photons_in)]
            p_val = self._partial_perm_sum(u_sub, S_full, perms, idx)
            norm = 1.0
            for s in out_s:
                norm *= math.factorial(s)
            probs[out_s] = float(p_val.real) / norm
        return self._normalize_probs(probs)

    @staticmethod
    def _partial_perm_sum(
        u_sub: NDArray[np.complex128],
        S_full: NDArray[np.complex128],
        perms: list[tuple[int, ...]],
        idx: NDArray[np.int64],
    ) -> complex:
        """Σ_{σ,σ'} Π_i S_{σ(i),σ'(i)} Π_j U_{r_j,σ(j)} U*_{r_j,σ'(j)}。"""
        p_val = 0.0 + 0.0j
        for sigma in perms:
            u_sig = u_sub[idx, sigma]
            for sp in perms:
                d_prod = complex(np.prod(S_full[sigma, sp]))
                u_prod = complex(np.prod(u_sig * u_sub[idx, sp].conj()))
                p_val += d_prod * u_prod
        return p_val

    @staticmethod
    def _normalize_probs(
        probs: dict[tuple[int, ...], float],
    ) -> dict[tuple[int, ...], float]:
        """归一化概率分布（总和为零时 raise，禁止 fall-back）。"""
        total = sum(probs.values())
        if total <= 0.0:
            raise ValueError("HOM 输出概率总和为零，数值退化")
        return {k: v / total for k, v in probs.items()}

    def _compute_bunching_metrics(
        self,
        input_state: tuple[int, ...],
        n: int,
        probs: dict[tuple[int, ...], float],
    ) -> tuple[float, float]:
        """计算 coincidence 概率与 bunching 参数。"""
        if n <= self.n_modes:
            coincidence_state = tuple(
                1 if i < n else 0 for i in range(self.n_modes)
            )
            p_coinc = probs.get(coincidence_state, 0.0)
        else:
            p_coinc = 0.0
        p_classical = self._classical_coincidence(input_state)
        bunching = (
            1.0 - p_coinc / p_classical if p_classical > 0 else 0.0
        )
        return p_coinc, bunching

    def _classical_coincidence(self, input_state: tuple[int, ...]) -> float:
        """经典完全可分光子 coincidence 概率 = n!/M^n（多项式分布）。"""
        n = sum(input_state)
        if n > self.n_modes:
            return 0.0
        return math.factorial(n) / (self.n_modes ** n)

    def hom_dip_curve(
        self,
        delay_axis: NDArray[np.float64],
        photon_coherence_time: float = 1.0,
    ) -> NDArray[np.float64]:
        """标准 2 光子 HOM 凹陷曲线 P(τ)=0.5·(1-exp(-(τ/τ_c)²))。

        τ=0: P=0（全同重叠，HOM 凹陷）；|τ|→∞: P=0.5（经典）。
        来源: Tichy 2015 §II.A。
        """
        if photon_coherence_time <= 0:
            raise ValueError("相干时间须 > 0")
        tau = np.asarray(delay_axis, dtype=float)
        return 0.5 * (1.0 - np.exp(-(tau / photon_coherence_time) ** 2))
