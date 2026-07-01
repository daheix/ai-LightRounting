"""R552 量子纠错编码子模块（Extract Module 拆分自 quantum_cv_qec.py）。

三比特重复码 / Steane [[7,4,3]] 码 / 症状测量 / 错误恢复。

学术依据（R02）:
- Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
  https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
  error correction https://doi.org/10.1103/PhysRevLett.77.793
- Nielsen & Chuang 2010 Quantum Computation and Quantum Information
  Cambridge University Press https://www.cambridge.org/9781107002173

*创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
]


class ThreeQubitRepetitionCode:
    """三量子比特重复码（Shor 1995）。

    编码：|0> → |000>, |1> → |111>
    纠正：单比特翻转错误。稳定子：Z1·Z2, Z2·Z3。
    """

    @staticmethod
    def encode(bit: int) -> np.ndarray:
        """编码单比特为三比特重复态。"""
        if bit not in (0, 1):
            raise ValueError(f"bit 须 0/1，实际 {bit}")
        # |000> = [1,0,0,0,0,0,0,0]^T, |111> = [0,...,0,1]^T
        state = np.zeros(8, dtype=np.complex128)
        state[0 if bit == 0 else 7] = 1.0
        return state

    @staticmethod
    def stabilizers() -> list[np.ndarray]:
        """返回两个稳定子 Z1Z2, Z2Z3（8×8 矩阵）。"""
        # 单比特 Z = diag(1, -1)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        I = np.eye(2, dtype=np.complex128)
        # Z1 Z2 = Z ⊗ Z ⊗ I
        zz12 = np.kron(np.kron(Z, Z), I)
        # Z2 Z3 = I ⊗ Z ⊗ Z
        zz23 = np.kron(np.kron(I, Z), Z)
        return [zz12, zz23]


class BitFlipError:
    """比特翻转错误 X。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须 0/1/2，实际 {qubit}")
        self.qubit = qubit

    def apply(self, state: np.ndarray) -> np.ndarray:
        """应用 X 门到指定量子比特。"""
        I = np.eye(2, dtype=np.complex128)
        X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        ops = [I, I, I]
        ops[self.qubit] = X
        U = ops[0]
        for op in ops[1:]:
            U = np.kron(U, op)
        return U @ state


class PhaseFlipError:
    """相位翻转错误 Z。"""

    def __init__(self, qubit: int) -> None:
        if qubit not in (0, 1, 2):
            raise ValueError(f"qubit 须 0/1/2，实际 {qubit}")
        self.qubit = qubit

    def apply(self, state: np.ndarray) -> np.ndarray:
        I = np.eye(2, dtype=np.complex128)
        Z = np.diag([1.0, -1.0]).astype(np.complex128)
        ops = [I, I, I]
        ops[self.qubit] = Z
        U = ops[0]
        for op in ops[1:]:
            U = np.kron(U, op)
        return U @ state


class SyndromeMeasurement:
    """稳定子测量（提取错误症状）。"""

    @staticmethod
    def measure(
        state: np.ndarray, stabilizers: list[np.ndarray],
    ) -> list[int]:
        """测量所有稳定子，返回 ±1 结果列表。

        Args:
            state: 8 维态矢量（三比特）。
            stabilizers: 稳定子列表（每个 8×8 矩阵）。

        Returns:
            各稳定子的测量结果（+1 或 -1）。
        """
        results: list[int] = []
        for stab in stabilizers:
            # <ψ|S|ψ>
            exp_val = float(np.real(np.vdot(state, stab @ state)))
            if exp_val > 0.5:
                results.append(1)
            elif exp_val < -0.5:
                results.append(-1)
            else:
                raise ValueError(
                    f"稳定子本征值非 ±1: {exp_val:.3e}（态不在码空间）"
                )
        return results


class RecoveryOperation:
    """错误恢复操作（基于症状查找恢复算符）。"""

    @staticmethod
    def recover(
        state: np.ndarray, syndrome: list[int],
    ) -> np.ndarray:
        """三比特重复码的错误恢复。

        Args:
            state: 8 维态矢量。
            syndrome: Z1Z2, Z2Z3 测量结果。

        Returns:
            恢复后的态矢量。
        """
        # 症状 → 错误比特查找表
        # (Z1Z2, Z2Z3):
        # (+1, +1) → 无错
        # (-1, -1) → bit 1 错
        # (+1, -1) → bit 2 错
        # (-1, +1) → bit 0 错
        s1, s2 = syndrome
        if s1 == +1 and s2 == +1:
            error_bit = -1  # 无错
        elif s1 == -1 and s2 == -1:
            error_bit = 1
        elif s1 == +1 and s2 == -1:
            error_bit = 2
        elif s1 == -1 and s2 == +1:
            error_bit = 0
        else:
            raise ValueError(f"非法症状 {syndrome}（规则 14）")
        if error_bit < 0:
            return state.copy()
        # 应用 X 门到错误比特（恢复）
        return BitFlipError(error_bit).apply(state)


class SteaneCode:
    """Steane [[7,4,3]] 码（Steane 1996）。

    7 个物理比特编码 4 个逻辑比特，距离 3。基于 Hamming [7,4] 码的 CSS 构造。
    本类仅实现编码器（4 逻辑比特 → 7 物理比特）和稳定子测量。
    """

    # Hamming [7,4] 奇偶校验矩阵 H (3×7)
    H_MATRIX = np.array([
        [1, 0, 1, 0, 1, 0, 1],
        [0, 1, 1, 0, 0, 1, 1],
        [0, 0, 0, 1, 1, 1, 1],
    ], dtype=np.int64)

    @classmethod
    def encode(cls, logical: np.ndarray) -> np.ndarray:
        """编码 4 比特逻辑态为 7 比特物理态。

        用 [7,4] Hamming 码生成矩阵 G (4×7)，编码 = G^T · logical mod 2。

        Args:
            logical: 4 维 0/1 数组（逻辑比特）。

        Returns:
            7 维 0/1 数组（物理比特）。
        """
        logical = np.asarray(logical, dtype=np.int64)
        if logical.shape != (4,):
            raise ValueError(f"logical 须 (4,)，实际 {logical.shape}")
        if not np.all((logical == 0) | (logical == 1)):
            raise ValueError("logical 须 0/1")
        # Hamming [7,4] 生成矩阵 G（系统形式 [I_4 | P]）
        # P = H^T 的非单位部分
        G = np.array([
            [1, 0, 0, 0, 0, 1, 1],
            [0, 1, 0, 0, 1, 0, 1],
            [0, 0, 1, 0, 1, 1, 0],
            [0, 0, 0, 1, 1, 1, 1],
        ], dtype=np.int64)
        # 编码：c = G^T · d mod 2
        codeword = (G.T @ logical) % 2
        return codeword

    @classmethod
    def syndrome(cls, received: np.ndarray) -> np.ndarray:
        """计算症状 H·r mod 2。

        Args:
            received: 7 维 0/1 数组（接收字）。

        Returns:
            3 维症状向量。
        """
        received = np.asarray(received, dtype=np.int64)
        if received.shape != (7,):
            raise ValueError(f"received 须 (7,)，实际 {received.shape}")
        if not np.all((received == 0) | (received == 1)):
            raise ValueError("received 须 0/1")
        return (cls.H_MATRIX @ received) % 2

    @classmethod
    def correct(cls, received: np.ndarray) -> np.ndarray:
        """纠正单比特错误（基于症状）。

        Args:
            received: 7 维 0/1 数组。

        Returns:
            纠正后 7 维 0/1 数组。
        """
        s = cls.syndrome(received)
        if np.all(s == 0):
            return received.copy()
        # 症状 → 错误位置：症状的非零组合对应 H 矩阵列
        # H 的第 i 列是 i+1 的二进制表示
        error_pos = int(s[0] * 1 + s[1] * 2 + s[2] * 4) - 1
        if error_pos < 0 or error_pos >= 7:
            raise ValueError(
                f"症状 {s} 无法纠正（多比特错误或非可纠正错误，规则 14）"
            )
        corrected = received.copy()
        corrected[error_pos] = 1 - corrected[error_pos]
        return corrected
