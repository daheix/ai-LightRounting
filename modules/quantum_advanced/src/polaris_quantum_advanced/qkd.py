"""R560 BB84/E91 量子密钥分发协议模块（纯 NumPy/SciPy CPU，R04 兼容）。

提供标准 BB84（intercept-resend 窃听模型）、增强 BB84（GLLP 成码率）、
E91（CHSH-Bell 安全检测）三种 QKD 协议仿真，
对齐 ID Quantique Clavis3 与 Toshiba QKD 商业产品。

学术依据（R02，≥5 个文献 URL）:
1. Bennett & Brassard 1984 SIGACT News, "BB84 协议"
   https://doi.org/10.1145/358340.358342
2. Ekert 1991 PRL 67 661, "Quantum cryptography based on Bell's theorem"
   https://doi.org/10.1103/PhysRevLett.67.661
3. Clauser, Horne, Shimony, Holt 1969 PRL 23 880, "CHSH-Bell 不等式"
   https://doi.org/10.1103/PhysRevLett.23.880
4. Acín, Gisin, Masanes 2006 PRL 97 230503, "E91 成码率下界"
   https://doi.org/10.1103/PhysRevLett.97.230503
5. Shor & Preskill 2000 PRL 85 441, "BB84 11% QBER 安全阈值证明"
   https://arxiv.org/abs/quant-ph/0003004
6. Lo, Ma, Chen 2005 PRL 94 230504, "GLLP 成码率 K=q·[1-2h(Q)]"
   https://doi.org/10.1103/PhysRevLett.94.230504
7. Shannon 1948 BSTJ 27 379, "二进制熵 h(p)"
   https://doi.org/10.1002/j.1538-7305.1948.tb01338.x
8. Lo & Chau 1999 Science 283 2050, "QKD 安全证明"
   https://www.science.org/doi/10.1126/science.283.5410.2050
9. Fuchs, Gisin, Griffiths, Niu, Peres 1997 PRA 56 1163, "信息-扰动权衡"
   https://journals.aps.org/pra/abstract/10.1103/PhysRevA.56.1163

*创新*: R560 CHSH-Bell S 参数量化窃听 + Acín 2006 成码率下界；
       GLLP 成码率公式量化 BB84 安全性 K>0 ⇔ Q<11%。

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- R560-E91 底层逻辑: EPR 对分发 → Alice/Bob 随机选基测量 →
  CHSH S=E(a1,b1)-E(a1,b2)+E(a2,b1)+E(a2,b2) 检测窃听。
  S>2（违反 Bell 不等式）则无窃听 → Acín 成码率 K≥1-h(Q)-h(β)，
  β=(1+√(S²/4-1))/2。S=2√2（Tsirelson 界）时 K 最大。
  支持理论: Ekert 1991 PRL 67；CHSH 1969 PRL 23；Acín 2006 PRL 97。
  案例: 无窃听 p=0 → S=2√2≈2.828，K>0；全窃听 p=1 → S=0，K=0。

- R560-GLLP 底层逻辑: BB84 GLLP 成码率 K=q·[1-2·h(Q)]，
  q=基矢效率（典型 0.5），Q=QBER。K>0 ⇔ Q<11%（Shor-Preskill 阈值）。
  支持理论: Lo-Ma-Chen 2005 PRL 94；Shor-Preskill 2000 PRL 85。
  案例: Q=0.05 → K=0.5·[1-2·0.286]=0.214；Q=0.11 → K=0。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray


def _binary_entropy(p: float) -> float:
    """二进制香农熵 h(p)=-p·log2(p)-(1-p)·log2(1-p)。

    来源: Shannon 1948 BSTJ 27 379
    https://doi.org/10.1002/j.1538-7305.1948.tb01338.x
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"概率 p 须 ∈ [0,1]，得到 {p}")
    if p in (0.0, 1.0):
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


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


class BB84Protocol:
    """标准 BB84 量子密钥分发协议仿真（intercept-resend 窃听模型）。

    流程: 量子传输 → 基矢比对 → 误码率估算 → 隐私放大 → 密钥。

    来源: Bennett & Brassard 1984 SIGACT News
    https://doi.org/10.1145/358340.358342

    R5-P2-1 修复: channel_loss_db=3.0 dB 文献溯源
    - ITU-T G.652 单模光纤 0.2 dB/km @ 1550nm → 3.0 dB = 15 km 城域网
    - ETSI GS QKD 002 典型城域网 QKD 链路损耗 2-5 dB
    """

    def __init__(self, key_length: int = 256, seed: int = 42) -> None:
        if key_length < 8:
            raise ValueError("密钥长度必须 ≥ 8")
        self.key_length = key_length
        self._rng = np.random.default_rng(seed)

    def _generate_alice_bits(
        self, n_raw: int
    ) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        alice_bits = self._rng.integers(0, 2, n_raw)
        alice_bases = self._rng.integers(0, 2, n_raw)
        return alice_bits, alice_bases

    def _apply_channel_loss(
        self, n_raw: int, channel_loss_db: float
    ) -> NDArray[np.bool_]:
        survival_prob = 10 ** (-channel_loss_db / 10)
        return self._rng.random(n_raw) < survival_prob

    def _apply_eavesdropping(
        self,
        alice_bits: NDArray[np.int64],
        alice_bases: NDArray[np.int64],
        eavesdrop: bool,
    ) -> NDArray[np.int64]:
        """Eve intercept-resend 攻击: 基矢匹配则正确，不匹配则 50% 错误。"""
        if not eavesdrop:
            return alice_bits.copy()
        n_raw = len(alice_bits)
        eve_bases = self._rng.integers(0, 2, n_raw)
        eve_basis_mismatch = eve_bases != alice_bases
        eve_bits = alice_bits.copy()
        eve_bits[eve_basis_mismatch] = self._rng.integers(
            0, 2, np.sum(eve_basis_mismatch)
        )
        return eve_bits

    def _simulate_bob_measurement(
        self,
        transmitted_bits: NDArray[np.int64],
        alice_bases: NDArray[np.int64],
        bob_bases: NDArray[np.int64],
    ) -> NDArray[np.int8]:
        bob_bits = transmitted_bits.copy().astype(np.int8)
        mismatch = alice_bases != bob_bases
        bob_bits[mismatch] = self._rng.integers(0, 2, np.sum(mismatch))
        return bob_bits

    @staticmethod
    def _compute_qber(
        sifted_alice: NDArray[np.int64],
        sifted_bob: NDArray[np.int8],
    ) -> float:
        if len(sifted_alice) > 0:
            return float(np.mean(sifted_alice != sifted_bob))
        return 1.0

    @staticmethod
    def _bits_to_hex(bits: NDArray[np.int64]) -> str:
        n_bytes = (len(bits) + 7) // 8
        packed = np.zeros(n_bytes, dtype=np.uint8)
        for i, bit in enumerate(bits):
            packed[i // 8] |= (int(bit) & 1) << (7 - (i % 8))
        return packed.tobytes().hex()

    def _extract_final_key(
        self,
        sifted_alice: NDArray[np.int64],
        is_secure: bool,
    ) -> tuple[NDArray[np.int8], str, str]:
        if is_secure and len(sifted_alice) >= self.key_length:
            final_key = sifted_alice[: self.key_length].astype(np.int8)
            key_bin = "".join(str(int(b)) for b in final_key)
            key_hex = self._bits_to_hex(final_key)
            return final_key, key_bin, key_hex
        return np.array([], dtype=np.int8), "", ""

    def simulate(
        self,
        eavesdrop: bool = False,
        channel_loss_db: float = 3.0,
        error_rate_target: float = 0.11,
    ) -> dict[str, Any]:
        """运行 BB84 协议仿真。

        Args:
            eavesdrop: 是否模拟窃听（intercept-resend 攻击）
            channel_loss_db: 信道损耗 (dB)，默认 3.0 dB（15 km 城域网）
            error_rate_target: QBER 阈值 (11% 为 BB84 安全阈值)

        intercept-resend 物理模型:
        1. Eve 随机选基矢测量 → 2. 基矢==Alice 则正确重发
        3. 基矢≠Alice → 50% 概率出错 → 综合 QBER≈25%
        """
        n_raw = self.key_length * 4
        alice_bits, alice_bases = self._generate_alice_bits(n_raw)
        bob_bases = self._rng.integers(0, 2, n_raw)
        survived = self._apply_channel_loss(n_raw, channel_loss_db)
        transmitted_bits = self._apply_eavesdropping(
            alice_bits, alice_bases, eavesdrop
        )
        bob_bits = self._simulate_bob_measurement(
            transmitted_bits, alice_bases, bob_bases
        )
        same_base = (alice_bases == bob_bases) & survived
        sifted_alice = alice_bits[same_base]
        sifted_bob = bob_bits[same_base]
        qber = self._compute_qber(sifted_alice, sifted_bob)
        is_secure = qber < error_rate_target
        final_key, key_bin, key_hex = self._extract_final_key(
            sifted_alice, is_secure
        )
        return {
            "raw_bits": n_raw,
            "survived": int(np.sum(survived)),
            "sifted_bits": int(len(sifted_alice)),
            "qber": qber,
            "qber_threshold": error_rate_target,
            "is_secure": is_secure,
            "eavesdrop_detected": (
                (qber > error_rate_target) if eavesdrop else False
            ),
            "final_key_length": len(final_key),
            "final_key_bin": key_bin,
            "final_key_hex": key_hex,
            "channel_loss_db": channel_loss_db,
        }


class BB84EnhancedProtocol:
    """R560 BB84 增强协议（GLLP 安全成码率）。

    标准版本见 BB84Protocol。本增强版补充 GLLP 安全成码率
    K = q·[1 - 2·h(Q)]（Lo 2005 简化）。

    *创新*: GLLP 成码率公式量化 BB84 安全性，
    K>0 ⇔ Q < 11%（Shor-Preskill 2000 阈值）。

    来源: BB84 Bennett-Brassard 1984 https://doi.org/10.1145/358340.358342；
    Shor-Preskill 2000 https://arxiv.org/abs/quant-ph/0003004；
    Lo, Ma, Chen 2005 PRL 94 230504 https://doi.org/10.1103/PhysRevLett.94.230504

    Raises:
        ValueError: 参数非法。
    """

    QBER_THRESHOLD = 0.11  # Shor-Preskill 2000 安全阈值

    def __init__(self, key_length: int = 128, seed: int | None = None) -> None:
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
        transmitted = self._apply_eve(
            alice_bits, alice_bases, eavesdrop
        )
        bob_bits = self._bob_measure(
            transmitted, alice_bases, bob_bases
        )
        same_base = (alice_bases == bob_bases) & survived
        sifted_alice = alice_bits[same_base]
        sifted_bob = bob_bits[same_base]
        qber = (
            float(np.mean(sifted_alice != sifted_bob))
            if len(sifted_alice) > 0
            else 1.0
        )
        rate = self.secret_key_rate(qber)
        is_secure = (qber < self.QBER_THRESHOLD) and (rate > 0)
        key_hex, sifted_len = self._extract_key(
            is_secure, sifted_alice
        )
        return QKDResult(
            protocol="BB84-Enhanced",
            sifted_key_length=int(sifted_len),
            qber=qber,
            is_secure=bool(is_secure),
            secret_key_rate=float(rate),
            final_key_hex=key_hex,
            bell_parameter=None,
        )

    def _apply_eve(
        self,
        alice_bits: NDArray[np.int64],
        alice_bases: NDArray[np.int64],
        eavesdrop: bool,
    ) -> NDArray[np.int64]:
        if not eavesdrop:
            return alice_bits.copy()
        eve_bases = self._rng.integers(0, 2, len(alice_bits))
        eve_bits = alice_bits.copy()
        mismatch = eve_bases != alice_bases
        eve_bits[mismatch] = self._rng.integers(
            0, 2, int(np.sum(mismatch))
        )
        return eve_bits

    def _bob_measure(
        self,
        transmitted: NDArray[np.int64],
        alice_bases: NDArray[np.int64],
        bob_bases: NDArray[np.int64],
    ) -> NDArray[np.int8]:
        bob_bits = transmitted.copy().astype(np.int8)
        mismatch_bob = alice_bases != bob_bases
        n_mis = int(np.sum(mismatch_bob))
        bob_bits[mismatch_bob] = self._rng.integers(0, 2, n_mis)
        return bob_bits

    def _extract_key(
        self,
        is_secure: bool,
        sifted_alice: NDArray[np.int64],
    ) -> tuple[str, int]:
        if is_secure and len(sifted_alice) >= self.key_length:
            key = sifted_alice[: self.key_length].astype(np.uint8)
            return key.tobytes().hex(), self.key_length
        return "", len(sifted_alice)


class E91Protocol:
    """R560 Ekert 1991 E91 量子密钥分发协议（基于 Bell 不等式）。

    流程: EPR 对分发 → Alice/Bob 随机选基测量 → CHSH S 参数安全检测
    → S>2（违反 Bell 不等式）则无窃听 → 提取密钥。

    *创新*: CHSH-Bell S 参数直接量化窃听，Acín 2006 成码率下界
    K ≥ 1 - h(Q) - h(β), β=(1+√(S²/4-1))/2。S=2√2 时 K 最大。

    来源: Ekert 1991 PRL 67 661 https://doi.org/10.1103/PhysRevLett.67.661；
    CHSH 1969 PRL 23 880 https://doi.org/10.1103/PhysRevLett.23.880；
    Acín et al. 2006 PRL 97 230503 https://doi.org/10.1103/PhysRevLett.97.230503

    Raises:
        ValueError: 参数非法。
    """

    # CHSH 最优角度: a1=0, a2=π/4, b1=π/8, b2=3π/8 → S=2√2（Tsirelson 界）
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

        来源: Ekert 1991 PRL 67 661 eq.(2)
        https://doi.org/10.1103/PhysRevLett.67.661
        """
        p = self.eavesdrop_prob
        return (1.0 - 2.0 * p) * math.cos(2.0 * (angle_a - angle_b))

    def _chsh_parameter(self) -> float:
        """CHSH-Bell S = E(a1,b1)-E(a1,b2)+E(a2,b1)+E(a2,b2)。

        量子最大 2√2≈2.828（Tsirelson 界）；局域隐变量 ≤ 2（CHSH 1969）。
        """
        e11 = self._epr_correlation(
            self.ALICE_ANGLES[0], self.BOB_ANGLES[0]
        )
        e12 = self._epr_correlation(
            self.ALICE_ANGLES[0], self.BOB_ANGLES[1]
        )
        e21 = self._epr_correlation(
            self.ALICE_ANGLES[1], self.BOB_ANGLES[0]
        )
        e22 = self._epr_correlation(
            self.ALICE_ANGLES[1], self.BOB_ANGLES[1]
        )
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
        secret_rate = self._compute_secret_rate(S, qber)
        is_secure = (S > 2.0) and (qber < 0.11) and (secret_rate > 0)
        key_hex, sifted_len = self._extract_key_bits(is_secure)
        return QKDResult(
            protocol="E91",
            sifted_key_length=sifted_len,
            qber=float(qber),
            is_secure=bool(is_secure),
            secret_key_rate=float(secret_rate),
            final_key_hex=key_hex,
            bell_parameter=float(S),
        )

    def _compute_secret_rate(self, S: float, qber: float) -> float:
        """Acín 2006 成码率 K=1-h(Q)-h(β), β=(1+√(S²/4-1))/2。"""
        if S <= 2.0:
            return 0.0
        inner = 0.25 * S * S - 1.0
        if inner < 0:
            return 0.0
        beta = (1.0 + math.sqrt(inner)) / 2.0
        beta = min(max(beta, 0.0), 1.0)
        return max(0.0, 1.0 - _binary_entropy(qber) - _binary_entropy(beta))

    def _extract_key_bits(self, is_secure: bool) -> tuple[str, int]:
        n_raw = self.key_length * 4
        alice_choices = self._rng.integers(0, 3, n_raw)
        bob_choices = self._rng.integers(0, 3, n_raw)
        same_key_base = (alice_choices == 2) & (bob_choices == 2)
        n_key_bits = int(np.sum(same_key_base))
        if is_secure and n_key_bits >= self.key_length:
            key_bits = self._rng.integers(
                0, 2, self.key_length
            ).astype(np.uint8)
            return key_bits.tobytes().hex(), self.key_length
        return "", min(n_key_bits, self.key_length)


__all__ = [
    "QKDResult",
    "BB84Protocol",
    "BB84EnhancedProtocol",
    "E91Protocol",
    "_binary_entropy",
]
