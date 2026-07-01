"""R556-R600 量子光子进阶模块（纯 NumPy/SciPy CPU，R04 兼容）。

提供 5 个进阶能力，对齐 IBM Qiskit + Xanadu Strawberry Fields + Perceval:
R556 大模式数玻色采样 / R557 HOM 干涉增强 / R558 量子态层析 /
R559 量子过程层析 / R560 BB84-E91 QKD 增强协议。

学术依据（R02，≥5 个文献 URL）:
1. Aaronson & Arkhipov 2011 STOC https://arxiv.org/abs/0910.4698
2. Clifford & Clifford 2018 SODA https://arxiv.org/abs/1706.01260
3. Hong-Ou-Mandel 1987 PRL 59 2044 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
4. Tichy 2015 PRA 91 022103 https://doi.org/10.1103/PhysRevA.91.022103
5. Hradil 1997 PRA 55 R1561 https://doi.org/10.1103/PhysRevA.55.R1561
6. James et al. 2001 PRA 64 052312 https://doi.org/10.1103/PhysRevA.64.052312
7. Chuang & Nielsen 1997 https://arxiv.org/abs/quant-ph/9610001
8. Ekert 1991 PRL 67 661 https://doi.org/10.1103/PhysRevLett.67.661
9. CHSH 1969 https://doi.org/10.1103/PhysRevLett.23.880; 10. Bennett-Brassard 1984 https://doi.org/10.1145/358340.358342
11. Shor-Preskill 2000 https://arxiv.org/abs/quant-ph/0003004; 12. Scarani 2009 https://arxiv.org/abs/0802.4155

*创新*: R556 Clifford-Clifford 逐光子采样 / R557 Tichy 双置换和 HOM / R558 Hradil Rᵢ MLE / R559 Pauli 线性反演 / R560 CHSH-Bell+Acín 成码率。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations

import numpy as np
from numpy.typing import ArrayLike, NDArray

# 复用现有 Ryser 积和式（quantum_permanent.py，纯 numpy 无 sax 依赖）
from polaris.sim.quantum_permanent import permanent_ryser


def _binary_entropy(p: float) -> float:
    """二进制香农熵 h(p)=-p·log2(p)-(1-p)·log2(1-p)。

    来源: Shannon 1948 https://doi.org/10.1002/j.1538-7305.1948.tb01338.x
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"概率 p 须 ∈ [0,1]，得到 {p}")
    if p in (0.0, 1.0):
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


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


def _pauli_basis_1qubit() -> list[NDArray[np.complex128]]:
    """单量子比特 Pauli 基 {I, X, Y, Z}（未归一化）。

    来源: Nielsen & Chuang 2010 §8.3.2 https://www.cambridge.org/9781107002173
    """
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return [I, X, Y, Z]


# ===========================================================================
# R556 大模式数玻色采样增强（Clifford-Clifford 逐光子采样）
# ===========================================================================


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

    来源: Clifford & Clifford 2018 SODA [模块级 URL #2]。

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
        """对给定输入态执行单次玻色采样。

        Clifford-Clifford 算法: 展开输入态为光子列表 → 逐光子按条件概率
        采样 → 输出模式直方图。
        """
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
                n_photons=0,
                n_modes=self.n_modes,
                n_steps=0,
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
            n_photons=n,
            n_modes=self.n_modes,
            n_steps=n,
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


# ===========================================================================
# R557 HOM 干涉增强（部分可分性 + 多光子 Tichy 算法）
# ===========================================================================


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

    来源: Hong-Ou-Mandel 1987 PRL 59 2044 [模块级 URL #3]；
    Tichy 2015 PRA 91 022103 [模块级 URL #4]。

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

    ξ=1: S=ones（全同/不可分，量子干涉最强），ξ=0: S=I（完全可分/经典，无干涉）。
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
        部分可分（0≤ξ<1）: Tichy 2015 双置换和
        P(s)=(1/Π s_i!) Σ_{σ,σ'} Π_i S_{σ(i),σ'(i)} Π_j U_{r_j,σ(j)} U*_{r_j,σ'(j)}
        ξ=1→S=ones（退化为 |Per|²），ξ=0→S=I（经典多项式分布）。
        """
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
        photons_in = [
            i for i, k in enumerate(input_state) for _ in range(k)
        ]
        probs: dict[tuple[int, ...], float] = {}
        if distinguishability == 1.0:
            for out_s in _generate_output_states(n, self.n_modes):
                rows = [i for i, s in enumerate(out_s) for _ in range(s)]
                u_sub = self.unitary[np.ix_(rows, photons_in)]
                per = permanent_ryser(u_sub)
                norm = 1.0
                for s in out_s:
                    norm *= math.factorial(s)
                probs[out_s] = float(abs(per) ** 2) / norm
        else:
            S_full = self._distinguishability_matrix(n, distinguishability)
            perms = list(permutations(range(n)))
            idx = np.arange(n)
            for out_s in _generate_output_states(n, self.n_modes):
                rows = [i for i, s in enumerate(out_s) for _ in range(s)]
                u_sub = self.unitary[np.ix_(rows, photons_in)]
                p_val = 0.0 + 0.0j
                for sigma in perms:
                    u_sig = u_sub[idx, sigma]
                    for sp in perms:
                        d_prod = complex(np.prod(S_full[sigma, sp]))
                        u_prod = complex(np.prod(u_sig * u_sub[idx, sp].conj()))
                        p_val += d_prod * u_prod
                norm = 1.0
                for s in out_s:
                    norm *= math.factorial(s)
                probs[out_s] = float(p_val.real) / norm
        total = sum(probs.values())
        if total <= 0.0:
            raise ValueError("HOM 输出概率总和为零，数值退化")
        probs = {k: v / total for k, v in probs.items()}
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
        return HOMResult(
            probabilities=probs,
            coincidence_probability=p_coinc,
            bunching_parameter=float(bunching),
            is_bunched=(bunching > 0.5),
        )

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


# ===========================================================================
# R558 量子态层析（Hradil R 迭代 MLE）
# ===========================================================================


@dataclass
class TomographyResult:
    """R558 量子态层析结果。"""

    density_matrix: NDArray[np.complex128]
    fidelity: float
    log_likelihood: float
    n_iterations: int
    converged: bool


class QuantumStateTomography:
    """R558 量子态层析（MLE 密度矩阵重构）。

    给定测量算子 {Π_k} 和观测频率 {f_k}，重构最可能的密度矩阵 ρ。

    *创新*: Hradil 1997 R 迭代 ρ_{k+1}=R(ρ_k)·ρ_k·R(ρ_k)†/Tr(...)，
    自动保正定迹归一，无需显式 SDP 优化。

    来源: Hradil 1997 [模块级 URL #5]；James et al. 2001 [模块级 URL #6]。

    Raises:
        ValueError: 测量算子维度不一致 / 频率非物理。
    """

    def __init__(
        self,
        measurement_operators: list[NDArray[np.complex128]],
        frequencies: NDArray[np.float64],
        target_state: NDArray[np.complex128] | None = None,
    ) -> None:
        if not measurement_operators:
            raise ValueError("测量算子列表不能为空")
        d = measurement_operators[0].shape[0]
        for op in measurement_operators:
            if op.shape != (d, d):
                raise ValueError(f"测量算子须为 {d}×{d}，得到 {op.shape}")
        freq = np.asarray(frequencies, dtype=float)
        if freq.shape != (len(measurement_operators),):
            raise ValueError("频率数组长度须 = 测量算子数")
        if np.any(freq < 0) or np.any(freq > 1):
            raise ValueError("频率须 ∈ [0,1]")
        self.operators = measurement_operators
        self.frequencies = freq
        self.dim = d
        self.target = (
            None if target_state is None
            else np.asarray(target_state, dtype=complex)
        )

    def reconstruct(
        self, max_iter: int = 500, tol: float = 1e-9
    ) -> TomographyResult:
        """Hradil R 迭代: ρ_{k+1}=R(ρ_k)·ρ_k·R(ρ_k)†/Tr, R=Σ(f_k/p_k)Π_k。"""
        if max_iter <= 0:
            raise ValueError("max_iter 须 > 0")
        if tol <= 0:
            raise ValueError("tol 须 > 0")
        d = self.dim
        rho = np.eye(d, dtype=complex) / d
        prev_ll = -np.inf
        converged = False
        n_iter = 0
        ll = -np.inf
        for n_iter in range(1, max_iter + 1):
            p_k = np.array(
                [np.trace(rho @ op).real for op in self.operators]
            )
            if np.any(p_k <= 0):
                raise ValueError(
                    f"Tr(ρ·Π_k)=0，测量算子不支撑当前态（迭代 {n_iter}）"
                )
            R = np.zeros((d, d), dtype=complex)
            for f, p, op in zip(self.frequencies, p_k, self.operators):
                R += (f / p) * op
            rho_new = R @ rho @ R.conj().T
            tr = np.trace(rho_new).real
            if tr <= 0:
                raise ValueError(f"迹非正（{tr}），迭代发散")
            rho_new /= tr
            ll = float(
                np.sum(self.frequencies * np.log(np.maximum(p_k, 1e-300)))
            )
            if abs(ll - prev_ll) < tol * (abs(prev_ll) + 1e-12):
                rho = rho_new
                converged = True
                break
            rho = rho_new
            prev_ll = ll
        fidelity = 1.0
        if self.target is not None:
            # Uhlmann 保真度 F=Tr|√(√ρ σ √ρ)|（Nielsen-Chuang 2010 §9.2.3）
            ev, V = np.linalg.eigh(rho)
            sr = V @ np.diag(np.sqrt(np.clip(ev, 0, None))) @ V.conj().T
            fidelity = float(np.sum(np.sqrt(np.clip(
                np.linalg.eigvalsh(sr @ self.target @ sr), 0, None))))
        return TomographyResult(
            density_matrix=rho,
            fidelity=fidelity,
            log_likelihood=ll,
            n_iterations=n_iter,
            converged=converged,
        )


# ===========================================================================
# R559 量子过程层析（χ 矩阵线性反演）
# ===========================================================================


class QuantumProcessTomography:
    """R559 量子过程层析（χ 矩阵线性反演重构）。

    量子通道 E(ρ) = Σ_{m,n} χ_{mn}·E_m·ρ·E_n†
    其中 {E_m} 是 Pauli 基（1 qubit），χ 是 4×4 过程矩阵。

    *创新*: Pauli 基展开 + 线性反演（Chuang-Nielsen 1997），
    构造线性方程组 A·χ_vec=b，最小二乘求解，避免 4^d×4^d 显式存储。

    来源: Chuang & Nielsen 1997 [模块级 URL #7]。仅支持单量子比特 d=2。

    Raises:
        ValueError: 输入/输出态非 2×2 / 数量不足。
    """

    def __init__(self, dim: int = 2) -> None:
        if dim != 2:
            raise ValueError("当前实现仅支持单量子比特（dim=2）")
        self.dim = dim
        self.basis = _pauli_basis_1qubit()
        self.basis_size = len(self.basis)  # 4

    def reconstruct(
        self,
        input_states: list[NDArray[np.complex128]],
        output_states: list[NDArray[np.complex128]],
    ) -> NDArray[np.complex128]:
        """线性反演重构 χ: E(ρ_j)=Σ χ_mn E_m ρ_j E_n† → A·χ_vec=b。"""
        d = self.dim
        n_needed = d * d
        if len(input_states) < n_needed or len(output_states) < n_needed:
            raise ValueError(
                f"需 {n_needed} 个输入/输出态，得到 "
                f"{len(input_states)}/{len(output_states)}"
            )
        for rho in list(input_states) + list(output_states):
            if rho.shape != (d, d):
                raise ValueError(f"密度矩阵须 {d}×{d}，得到 {rho.shape}")
        B = self.basis_size
        n_eq = n_needed * d * d
        A = np.zeros((n_eq, B * B), dtype=complex)
        b = np.zeros(n_eq, dtype=complex)
        row = 0
        for rho_in, rho_out in zip(input_states, output_states):
            for alpha in range(d):
                for beta in range(d):
                    b[row] = rho_out[alpha, beta]
                    for m in range(B):
                        for n in range(B):
                            term = (
                                self.basis[m] @ rho_in
                                @ self.basis[n].conj().T
                            )
                            A[row, m * B + n] = term[alpha, beta]
                    row += 1
        chi_vec, _residuals, rank, _ = np.linalg.lstsq(A, b, rcond=None)
        if rank < B * B:
            raise ValueError(
                f"输入态线性相关（秩 {rank} < {B * B}），无法唯一重构 χ"
            )
        chi = chi_vec.reshape(B, B)
        # 归一化: Σ_m χ_mm·Tr(E_m E_m†) = Tr(I) = d
        trace_norm = sum(
            float(np.real(np.trace(
                self.basis[m] @ self.basis[m].conj().T
            ))) * chi[m, m].real
            for m in range(B)
        )
        if abs(trace_norm) < 1e-12:
            raise ValueError("χ 迹为零，过程非物理")
        chi = chi / (trace_norm / d)
        return chi

    def apply_channel(
        self,
        chi: NDArray[np.complex128],
        rho: NDArray[np.complex128],
    ) -> NDArray[np.complex128]:
        """用 χ 矩阵应用通道 E(ρ) = Σ χ_mn E_m ρ E_n†。"""
        if chi.shape != (self.basis_size, self.basis_size):
            raise ValueError(
                f"χ 须 {self.basis_size}×{self.basis_size}，得到 {chi.shape}"
            )
        if rho.shape != (self.dim, self.dim):
            raise ValueError(
                f"ρ 须 {self.dim}×{self.dim}，得到 {rho.shape}"
            )
        out = np.zeros((self.dim, self.dim), dtype=complex)
        for m in range(self.basis_size):
            for n in range(self.basis_size):
                out += chi[m, n] * (
                    self.basis[m] @ rho @ self.basis[n].conj().T
                )
        return out

    def process_fidelity(
        self,
        chi: NDArray[np.complex128],
        chi_target: NDArray[np.complex128],
    ) -> float:
        """过程保真度 F_χ = Tr(χ†·χ_target)/√(Tr(χ†χ)·Tr(χ_target†χ_target))。"""
        if chi.shape != chi_target.shape:
            raise ValueError("χ 矩阵形状不匹配")
        num = float(np.real(np.trace(chi.conj().T @ chi_target)))
        den = float(np.real(np.trace(chi.conj().T @ chi))) * float(
            np.real(np.trace(chi_target.conj().T @ chi_target))
        )
        if den <= 0:
            raise ValueError("χ 范数非正，过程非物理")
        return num / math.sqrt(den)


# ===========================================================================
# R560 BB84/E91 QKD 增强协议
# ===========================================================================


@dataclass
class QKDResult:
    """R560 QKD 协议仿真结果。"""

    protocol: str
    sifted_key_length: int
    qber: float
    is_secure: bool
    secret_key_rate: float
    final_key_hex: str
    bell_parameter: float | None = None  # E91 的 CHSH S


class E91Protocol:
    """R560 Ekert 1991 E91 量子密钥分发协议（基于 Bell 不等式）。

    流程: EPR 对分发 → Alice/Bob 随机选基测量 → CHSH S 参数安全检测
    → S>2（违反 Bell 不等式）则无窃听 → 提取密钥。

    *创新*: CHSH-Bell S 参数直接量化窃听，Acín 2006 成码率下界
    K ≥ 1 - h(Q) - h(β), β=(1+√(S²/4-1))/2。S=2√2 时 K 最大。

    来源: Ekert 1991 [模块级 URL #8]；CHSH 1969 [模块级 URL #9]；
    Acín et al. 2006 PRL 97 230503 https://doi.org/10.1103/PhysRevLett.97.230503

    Raises:
        ValueError: 参数非法。
    """

    # Alice/Bob 基矢角度（弧度）: a1,a2 用于 CHSH；a3,b3 同基用于密钥提取
    # CHSH 最优: a1=0, a2=π/4, b1=π/8, b2=3π/8 → S=2√2（Tsirelson 界）
    ALICE_ANGLES = (0.0, math.pi / 4, math.pi / 2)
    BOB_ANGLES = (math.pi / 8, 3 * math.pi / 8, math.pi / 2)

    def __init__(
        self,
        key_length: int = 128,
        eavesdrop_prob: float = 0.0,
        seed: int | None = None,
    ) -> None:
        if key_length < 8:
            raise ValueError("密钥长度须 ≥ 8")
        if not 0.0 <= eavesdrop_prob <= 1.0:
            raise ValueError("eavesdrop_prob 须 ∈ [0,1]")
        self.key_length = key_length
        self.eavesdrop_prob = eavesdrop_prob
        self._rng = np.random.default_rng(seed)

    def _epr_correlation(self, angle_a: float, angle_b: float) -> float:
        """EPR 对 |Φ+⟩ 自旋相关 E(a,b)=cos(2(a-b))，窃听衰减 (1-2p)。

        来源: Ekert 1991 eq.(2)。
        """
        p = self.eavesdrop_prob
        return (1.0 - 2.0 * p) * math.cos(2.0 * (angle_a - angle_b))

    def _chsh_parameter(self) -> float:
        """CHSH-Bell S = E(a1,b1)-E(a1,b2)+E(a2,b1)+E(a2,b2)。

        量子最大 2√2≈2.828（Tsirelson 界）；局域隐变量 ≤ 2（CHSH 1969）。
        a1=ALICE[0]=0, a2=ALICE[1]=π/4, b1=BOB[0]=π/8, b2=BOB[1]=3π/8。
        """
        e11 = self._epr_correlation(self.ALICE_ANGLES[0], self.BOB_ANGLES[0])
        e12 = self._epr_correlation(self.ALICE_ANGLES[0], self.BOB_ANGLES[1])
        e21 = self._epr_correlation(self.ALICE_ANGLES[1], self.BOB_ANGLES[0])
        e22 = self._epr_correlation(self.ALICE_ANGLES[1], self.BOB_ANGLES[1])
        return e11 - e12 + e21 + e22

    def simulate(self) -> QKDResult:
        """运行 E91 协议仿真，返回含 S 参数、QBER、成码率、密钥。"""
        S = self._chsh_parameter()
        tsirelson = 2.0 * math.sqrt(2.0)
        if abs(S) > tsirelson + 1e-9:
            raise ValueError(
                f"CHSH S={S} 超过 Tsirelson 界 2√2≈{tsirelson}"
            )
        e_same = self._epr_correlation(
            self.ALICE_ANGLES[2], self.BOB_ANGLES[2]
        )
        qber = (1.0 - e_same) / 2.0
        if S > 2.0:
            inner = 0.25 * S * S - 1.0
            if inner < 0:
                secret_rate = 0.0
            else:
                beta = (1.0 + math.sqrt(inner)) / 2.0
                beta = min(max(beta, 0.0), 1.0)
                secret_rate = max(
                    0.0, 1.0 - _binary_entropy(qber) - _binary_entropy(beta)
                )
        else:
            secret_rate = 0.0
        is_secure = (S > 2.0) and (qber < 0.11) and (secret_rate > 0)
        n_raw = self.key_length * 4
        alice_choices = self._rng.integers(0, 3, n_raw)
        bob_choices = self._rng.integers(0, 3, n_raw)
        same_key_base = (alice_choices == 2) & (bob_choices == 2)
        n_key_bits = int(np.sum(same_key_base))
        if is_secure and n_key_bits >= self.key_length:
            key_bits = self._rng.integers(
                0, 2, self.key_length
            ).astype(np.uint8)
            key_hex = key_bits.tobytes().hex()
            sifted_len = self.key_length
        else:
            key_hex = ""
            sifted_len = min(n_key_bits, self.key_length)
        return QKDResult(
            protocol="E91",
            sifted_key_length=sifted_len,
            qber=float(qber),
            is_secure=bool(is_secure),
            secret_key_rate=float(secret_rate),
            final_key_hex=key_hex,
            bell_parameter=float(S),
        )


class BB84EnhancedProtocol:
    """R560 BB84 增强协议（GLLP 安全成码率）。

    标准版本见 polaris.quantum.bb84_protocol.BB84Protocol。本增强版补充
    GLLP 安全成码率 K = q·[1 - 2·h(Q)]（Lo 2005 简化）。

    *创新*: GLLP 成码率公式量化 BB84 安全性，
    K>0 ⇔ Q < 11%（Shor-Preskill 2000 阈值）。

    来源: BB84 [模块级 URL #10]；Shor-Preskill [模块级 URL #11]；
    Lo, Ma, Chen 2005 PRL 94 230504 https://doi.org/10.1103/PhysRevLett.94.230504

    Raises:
        ValueError: 参数非法。
    """

    QBER_THRESHOLD = 0.11  # Shor-Preskill 2000 安全阈值

    def __init__(
        self, key_length: int = 128, seed: int | None = None
    ) -> None:
        if key_length < 8:
            raise ValueError("密钥长度须 ≥ 8")
        self.key_length = key_length
        self._rng = np.random.default_rng(seed)

    def secret_key_rate(
        self, qber: float, basis_efficiency: float = 0.5
    ) -> float:
        """GLLP 安全成码率 K = q·[1 - 2·h(Q)]（Lo 2005 简化）。"""
        if not 0.0 <= qber <= 1.0:
            raise ValueError("QBER 须 ∈ [0,1]")
        if not 0.0 < basis_efficiency <= 1.0:
            raise ValueError("basis_efficiency 须 ∈ (0,1]")
        h_q = _binary_entropy(qber)
        return max(0.0, basis_efficiency * (1.0 - 2.0 * h_q))

    def simulate(
        self, eavesdrop: bool = False, channel_loss_db: float = 3.0
    ) -> QKDResult:
        """运行增强 BB84 协议仿真（intercept-resend 窃听模型）。"""
        if channel_loss_db < 0:
            raise ValueError("信道损耗须 ≥ 0 dB")
        n_raw = self.key_length * 4
        alice_bits = self._rng.integers(0, 2, n_raw)
        alice_bases = self._rng.integers(0, 2, n_raw)
        bob_bases = self._rng.integers(0, 2, n_raw)
        survival_prob = 10 ** (-channel_loss_db / 10.0)
        survived = self._rng.random(n_raw) < survival_prob
        if eavesdrop:
            eve_bases = self._rng.integers(0, 2, n_raw)
            eve_bits = alice_bits.copy()
            mismatch = eve_bases != alice_bases
            eve_bits[mismatch] = self._rng.integers(
                0, 2, int(np.sum(mismatch))
            )
            transmitted = eve_bits
        else:
            transmitted = alice_bits.copy()
        bob_bits = transmitted.copy()
        mismatch_bob = alice_bases != bob_bases
        n_mis = int(np.sum(mismatch_bob))
        bob_bits[mismatch_bob] = self._rng.integers(0, 2, n_mis)
        same_base = (alice_bases == bob_bases) & survived
        sifted_alice = alice_bits[same_base]
        sifted_bob = bob_bits[same_base]
        qber = (
            float(np.mean(sifted_alice != sifted_bob))
            if len(sifted_alice) > 0 else 1.0
        )
        rate = self.secret_key_rate(qber)
        is_secure = (qber < self.QBER_THRESHOLD) and (rate > 0)
        if is_secure and len(sifted_alice) >= self.key_length:
            key = sifted_alice[: self.key_length].astype(np.uint8)
            key_hex = key.tobytes().hex()
            sifted_len = self.key_length
        else:
            key_hex = ""
            sifted_len = len(sifted_alice)
        return QKDResult(
            protocol="BB84-Enhanced",
            sifted_key_length=int(sifted_len),
            qber=qber,
            is_secure=bool(is_secure),
            secret_key_rate=float(rate),
            final_key_hex=key_hex,
            bell_parameter=None,
        )


__all__ = [
    "BB84EnhancedProtocol",
    "BosonSampleResult",
    "E91Protocol",
    "HOMInterferometer",
    "HOMResult",
    "LargeScaleBosonSampler",
    "QKDResult",
    "QuantumProcessTomography",
    "QuantumStateTomography",
    "TomographyResult",
]
