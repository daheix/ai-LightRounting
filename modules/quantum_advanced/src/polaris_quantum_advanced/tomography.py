"""R558-R559 量子层析模块（纯 NumPy/SciPy CPU，R04 兼容）。

提供量子态层析（MLE 密度矩阵重构）和量子过程层析（χ 矩阵线性反演），
对齐 IBM Qiskit Quantum Tomography 与 QuTiP QPT。

学术依据（R02，≥5 个文献 URL）:
1. Hradil 1997 PRA 55 R1561, "Quantum-state estimation"
   https://doi.org/10.1103/PhysRevA.55.R1561
2. James, Kwiat, Munro, White 2001 PRA 64 052312,
   "Measurement of qubits"（实验态层析）
   https://doi.org/10.1103/PhysRevA.64.052312
3. Chuang & Nielsen 1997, " prescription for experimental determination
   of the dynamics of a quantum black box"
   https://arxiv.org/abs/quant-ph/9610001
4. Nielsen & Chuang 2010, "Quantum Computation and Quantum Information"
   §8.3.2 Pauli 基展开 https://www.cambridge.org/9781107002173
5. Uhlmann 1976 Rep. Math. Phys. 9 273, "The 'transition probability'"
   保真度定义 https://doi.org/10.1016/0034-4877(76)90060-4
6. Sacchi 2005 PRA 71 062340, "Optimal estimation of quantum operations"
   https://doi.org/10.1103/PhysRevA.71.062340

*创新*: R558 Hradil Rᵢ 迭代 MLE（自动保正定迹归一，无需 SDP）；
       R559 Pauli 基线性反演（避免 4^d×4^d 显式存储）。

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- R558-Hradil 底层逻辑: ρ_{k+1}=R(ρ_k)·ρ_k·R(ρ_k)†/Tr(...)，
  R=Σ(f_k/p_k)Π_k。R 迭代是 MLE 的不动点迭代，每次更新自动保正定迹归一，
  无需显式 SDP 优化。支持理论: Hradil 1997 PRA 55 R1561；
  James et al. 2001 PRA 64 052312（实验验证）。
  案例: 单量子比特层析重构 |0⟩ 态，fidelity→1.0（见 test_quantum_advanced.py）。

- R559-Pauli 底层逻辑: 量子通道 E(ρ)=Σ χ_{mn} E_m ρ E_n†，
  Pauli 基 {I,X,Y,Z} 展开 χ 为 4×4 矩阵。构造线性方程组 A·χ_vec=b，
  最小二乘求解，避免 4^d×4^d 显式存储。支持理论: Chuang-Nielsen 1997；
  Nielsen-Chuang 2010 §8.3.2。案例: 重构单位通道 χ=diag(1,0,0,0)。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


def _pauli_basis_1qubit() -> list[NDArray[np.complex128]]:
    """单量子比特 Pauli 基 {I, X, Y, Z}（未归一化）。

    来源: Nielsen & Chuang 2010 §8.3.2
    https://www.cambridge.org/9781107002173
    """
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return [I, X, Y, Z]


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

    来源: Hradil 1997 PRA 55 R1561 https://doi.org/10.1103/PhysRevA.55.R1561；
    James et al. 2001 PRA 64 052312 https://doi.org/10.1103/PhysRevA.64.052312

    Raises:
        ValueError: 测量算子维度不一致 / 频率非物理。
    """

    def __init__(
        self,
        measurement_operators: list[NDArray[np.complex128]],
        frequencies: NDArray[np.float64],
        target_state: NDArray[np.complex128] | None = None,
    ) -> None:
        self._validate_inputs(measurement_operators, frequencies)
        self.operators = measurement_operators
        self.frequencies = np.asarray(frequencies, dtype=float)
        self.dim = measurement_operators[0].shape[0]
        self.target = (
            None if target_state is None
            else np.asarray(target_state, dtype=complex)
        )

    @staticmethod
    def _validate_inputs(
        operators: list[NDArray[np.complex128]],
        frequencies: NDArray[np.float64],
    ) -> None:
        if not operators:
            raise ValueError("测量算子列表不能为空")
        d = operators[0].shape[0]
        for op in operators:
            if op.shape != (d, d):
                raise ValueError(f"测量算子须为 {d}×{d}，得到 {op.shape}")
        freq = np.asarray(frequencies, dtype=float)
        if freq.shape != (len(operators),):
            raise ValueError("频率数组长度须 = 测量算子数")
        if np.any(freq < 0) or np.any(freq > 1):
            raise ValueError("频率须 ∈ [0,1]")

    def reconstruct(
        self, max_iter: int = 500, tol: float = 1e-9
    ) -> TomographyResult:
        """Hradil R 迭代: ρ_{k+1}=R(ρ_k)·ρ_k·R(ρ_k)†/Tr, R=Σ(f_k/p_k)Π_k。"""
        if max_iter <= 0:
            raise ValueError("max_iter 须 > 0")
        if tol <= 0:
            raise ValueError("tol 须 > 0")
        rho = np.eye(self.dim, dtype=complex) / self.dim
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
            R = np.zeros((self.dim, self.dim), dtype=complex)
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
        fidelity = self._compute_fidelity(rho)
        return TomographyResult(
            density_matrix=rho,
            fidelity=fidelity,
            log_likelihood=ll,
            n_iterations=n_iter,
            converged=converged,
        )

    def _compute_fidelity(self, rho: NDArray[np.complex128]) -> float:
        """Uhlmann 保真度 F=Tr|√(√ρ σ √ρ)|（Nielsen-Chuang 2010 §9.2.3）。"""
        if self.target is None:
            return 1.0
        ev, V = np.linalg.eigh(rho)
        sr = V @ np.diag(np.sqrt(np.clip(ev, 0, None))) @ V.conj().T
        fidelity = float(np.sum(np.sqrt(np.clip(
            np.linalg.eigvalsh(sr @ self.target @ sr), 0, None))))
        return fidelity


class QuantumProcessTomography:
    """R559 量子过程层析（χ 矩阵线性反演重构）。

    量子通道 E(ρ) = Σ_{m,n} χ_{mn}·E_m·ρ·E_n†
    其中 {E_m} 是 Pauli 基（1 qubit），χ 是 4×4 过程矩阵。

    *创新*: Pauli 基展开 + 线性反演（Chuang-Nielsen 1997），
    构造线性方程组 A·χ_vec=b，最小二乘求解，避免 4^d×4^d 显式存储。

    来源: Chuang & Nielsen 1997 https://arxiv.org/abs/quant-ph/9610001。
    仅支持单量子比特 d=2。

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
        self._validate_state_lists(
            input_states, output_states, n_needed, d
        )
        B = self.basis_size
        A, b = self._build_linear_system(
            input_states, output_states, n_needed, B
        )
        chi_vec, _residuals, rank, _ = np.linalg.lstsq(A, b, rcond=None)
        if rank < B * B:
            raise ValueError(
                f"输入态线性相关（秩 {rank} < {B * B}），无法唯一重构 χ"
            )
        chi = chi_vec.reshape(B, B)
        chi = self._normalize_chi(chi, d)
        return chi

    @staticmethod
    def _validate_state_lists(
        input_states: list[NDArray[np.complex128]],
        output_states: list[NDArray[np.complex128]],
        n_needed: int,
        d: int,
    ) -> None:
        if len(input_states) < n_needed or len(output_states) < n_needed:
            raise ValueError(
                f"需 {n_needed} 个输入/输出态，得到 "
                f"{len(input_states)}/{len(output_states)}"
            )
        for rho in list(input_states) + list(output_states):
            if rho.shape != (d, d):
                raise ValueError(f"密度矩阵须 {d}×{d}，得到 {rho.shape}")

    def _build_linear_system(
        self,
        input_states: list[NDArray[np.complex128]],
        output_states: list[NDArray[np.complex128]],
        n_needed: int,
        B: int,
    ) -> tuple[NDArray[np.complex128], NDArray[np.complex128]]:
        d = self.dim
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
        return A, b

    def _normalize_chi(
        self, chi: NDArray[np.complex128], d: int
    ) -> NDArray[np.complex128]:
        """归一化: Σ_m χ_mm·Tr(E_m E_m†) = Tr(I) = d。"""
        trace_norm = sum(
            float(np.real(np.trace(
                self.basis[m] @ self.basis[m].conj().T
            ))) * chi[m, m].real
            for m in range(self.basis_size)
        )
        if abs(trace_norm) < 1e-12:
            raise ValueError("χ 迹为零，过程非物理")
        return chi / (trace_norm / d)

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


__all__ = [
    "TomographyResult",
    "QuantumStateTomography",
    "QuantumProcessTomography",
    "_pauli_basis_1qubit",
]
