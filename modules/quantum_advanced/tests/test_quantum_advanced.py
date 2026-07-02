"""polaris-quantum-advanced 子模块 smoke test。

覆盖核心 API:
- permanent_ryser（积和式）
- boson_sampling_prob（HOM 干涉）
- BB84Protocol（QKD 安全性）
- SteaneCode（量子纠错）
- QuantumCircuitSimulator（Bell 态）
- GaussianState（CV 高斯真空态）
- PhotonLossChannel（光子损耗保迹）
- DistributedPPOTrainer（PPO 合成模式 + 守门逻辑）

学术依据（R02）:
- Aaronson & Arkhipov, STOC 2011. https://arxiv.org/abs/0910.4698
- Bennett & Brassard 1984. https://doi.org/10.1145/358340.358342
- Steane 1996 PRL 77 793. https://doi.org/10.1103/PhysRevLett.77.793
- Knill, Laflamme, Milburn, Nature 2001. https://www.nature.com/articles/35051009
- Schulman et al., PPO, arXiv:1707.06347. https://arxiv.org/abs/1707.06347

合规: R03 禁止 fall-back / R04 纯 NumPy / R05 无假数据。
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import numpy as np
import pytest

# 将 src 加入 sys.path 以支持直接 pytest 运行（未 pip install 时）
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from polaris_quantum_advanced import (
    permanent_ryser,
    boson_sampling_prob,
    BB84Protocol,
    SteaneCode,
    QuantumCircuitSimulator,
    GaussianState,
    PhotonLossChannel,
    DistributedPPOConfig,
    DistributedPPOTrainer,
)


# =============================================================================
# 1. 积和式（Permanent）— Ryser 算法
# =============================================================================

def test_permanent_ryser_2x2_all_ones() -> None:
    """2×2 全 1 矩阵积和式 = 2（Per([[1,1],[1,1]]) = 1·1 + 1·1 = 2）。

    来源: Ryser 1963; Aaronson & Arkhipov STOC 2011.
    """
    M = np.ones((2, 2), dtype=np.float64)
    result = permanent_ryser(M)
    assert abs(result - 2.0) < 1e-10, f"全 1 矩阵积和式应为 2，实际 {result}"


def test_permanent_ryser_identity() -> None:
    """单位矩阵积和式 = 1（Per(I) = 1）。"""
    I = np.eye(3, dtype=np.float64)
    result = permanent_ryser(I)
    assert abs(result - 1.0) < 1e-10, f"单位矩阵积和式应为 1，实际 {result}"


# =============================================================================
# 2. 玻色采样 — HOM 干涉
# =============================================================================

def test_boson_sampling_hom_interference() -> None:
    """HOM 干涉: 50:50 BS 输入 |1,1⟩ → 输出 |2,0⟩/|0,2⟩ 各 0.5，|1,1⟩ 概率 0。

    Hong-Ou-Mandel 效应（PRL 59, 2044, 1987）:
    U = [[1,1],[1,-1]]/√2，输入 (1,1)：
    - P(2,0) = |Per(U_sub)|²/(2!·1!·1!) = 0.5
    - P(0,2) = 0.5
    - P(1,1) = 0（干涉相消）
    """
    U = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
    p_20 = boson_sampling_prob(U, (1, 1), (2, 0))
    p_02 = boson_sampling_prob(U, (1, 1), (0, 2))
    p_11 = boson_sampling_prob(U, (1, 1), (1, 1))

    assert abs(p_20 - 0.5) < 1e-10, f"P(2,0) 应为 0.5，实际 {p_20}"
    assert abs(p_02 - 0.5) < 1e-10, f"P(0,2) 应为 0.5，实际 {p_02}"
    assert abs(p_11) < 1e-10, f"P(1,1) 应为 0（HOM 相消），实际 {p_11}"
    assert abs(p_20 + p_02 + p_11 - 1.0) < 1e-10, "概率和应为 1"


# =============================================================================
# 3. BB84 量子密钥分发
# =============================================================================

def test_bb84_no_eavesdrop_is_secure() -> None:
    """BB84 无窃听: QBER < 11% 阈值，密钥安全。

    来源: Bennett & Brassard 1984; Shor & Preskill 2000.
    """
    protocol = BB84Protocol(key_length=32, seed=42)
    result = protocol.simulate(eavesdrop=False, channel_loss_db=3.0)
    assert result["qber"] < 0.11, f"无窃听 QBER 应 < 11%，实际 {result['qber']}"
    assert result["is_secure"] is True, "无窃听应判定安全"


def test_bb84_eavesdrop_detected() -> None:
    """BB84 intercept-resend 窃听: QBER ≈ 25%，超过 11% 阈值被检测。

    intercept-resend 物理模型: Eve 随机基矢 → 50% 不匹配 → 25% QBER。
    """
    protocol = BB84Protocol(key_length=32, seed=123)
    result = protocol.simulate(eavesdrop=True, channel_loss_db=0.0)
    assert result["qber"] > 0.11, f"窃听 QBER 应 > 11%，实际 {result['qber']}"
    assert result["is_secure"] is False, "窃听应判定不安全"


# =============================================================================
# 4. Steane [[7,4,3]] 量子纠错码
# =============================================================================

def test_steane_code_corrects_single_bit_flip() -> None:
    """Steane 码纠正单比特翻转错误。

    来源: Steane 1996 PRL 77 793. 编码 → 注入错误 → 纠正 → 恢复。
    """
    logical = np.array([1, 0, 1, 1], dtype=np.int64)
    encoded = SteaneCode.encode(logical)
    # 注入第 3 位翻转错误
    corrupted = encoded.copy()
    corrupted[2] = 1 - corrupted[2]
    corrected = SteaneCode.correct(corrupted)
    np.testing.assert_array_equal(
        corrected, encoded, "纠正后应恢复原始编码字"
    )


# =============================================================================
# 5. 量子电路仿真器 — Bell 态
# =============================================================================

def test_quantum_circuit_bell_state_measurement() -> None:
    """Bell 态 |Φ+⟩ = (|00⟩ + |11⟩)/√2 测量: |00⟩ 和 |11⟩ 各 ~50%。

    来源: Knill et al. Nature 2001; Clements et al. Optica 2016.
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.bell_state(qubit_a=0, qubit_b=1)
    counts = sim.measure(qubit=0, shots=2000)
    total = counts[0] + counts[1]
    assert total == 2000, f"测量总数应为 2000，实际 {total}"
    # Bell 态测量 qubit 0 应接近 50:50
    ratio = counts[0] / total
    assert 0.35 < ratio < 0.65, f"Bell 态 |0⟩ 比例应 ~0.5，实际 {ratio}"


# =============================================================================
# 6. CV 高斯真空态
# =============================================================================

def test_gaussian_vacuum_state() -> None:
    """单模真空态: V = I/2, d = 0, 满足不确定性关系 V+iΩ/2 ≥ 0。

    来源: Weedbrook et al. Rev Mod Phys 84, 621 (2012).
    """
    state = GaussianState.vacuum(n_modes=1)
    assert state.n_modes == 1, "模式数应为 1"
    np.testing.assert_allclose(
        state.covariance, 0.5 * np.eye(2), atol=1e-10,
        err_msg="真空态协方差矩阵应为 I/2",
    )
    np.testing.assert_allclose(
        state.mean, np.zeros(2), atol=1e-10,
        err_msg="真空态平均向量应为 0",
    )


# =============================================================================
# 7. 光子损耗通道 — CPTP 保迹
# =============================================================================

def test_photon_loss_channel_trace_preserving() -> None:
    """光子损耗通道保迹: Tr(ρ') ≈ Tr(ρ) = 1（Kraus 求和 CPTP 性质）。

    来源: Kok & Lovett 2010 §3.2; Carmichael 1993.
    """
    # 单光子态密度矩阵 |1⟩⟨1|
    rho = np.array([[0, 0], [0, 1]], dtype=np.complex128)
    channel = PhotonLossChannel(eta=0.8, n_max=5)
    rho_out = channel.apply(rho)
    trace = float(np.trace(rho_out).real)
    assert abs(trace - 1.0) < 1e-6, f"保迹 Tr(ρ') 应 ≈ 1，实际 {trace}"


# =============================================================================
# 8. 分布式 PPO — 合成模式训练
# =============================================================================

def test_distributed_ppo_synthetic_mode_trains() -> None:
    """PPO 合成测试模式: training_step 成功执行并返回训练统计。

    R05 v4.0-FAKE-ENV-P0: synthetic_env_mode=True 仅用于算法单元测试。
    来源: Schulman et al. PPO arXiv:1707.06347 (2017).
    """
    config = DistributedPPOConfig(
        synthetic_env_mode=True,
        n_workers=1,
        n_epochs=1,
        batch_size=16,
        n_devices_per_circuit=10,
    )
    trainer = DistributedPPOTrainer(config)
    result = trainer.training_step(n_episodes_per_worker=1)
    assert "mean_reward" in result, "训练结果应含 mean_reward"
    assert "mean_policy_loss" in result, "训练结果应含 mean_policy_loss"
    assert "n_policy_updates" in result, "训练结果应含 n_policy_updates"
    assert result["n_workers"] == 1, f"worker 数应为 1，实际 {result['n_workers']}"
    assert result["n_policy_updates"] > 0, "应有至少一次策略更新"


def test_distributed_ppo_guard_rejects_no_env() -> None:
    """PPO 守门逻辑: 未注入真实环境且 synthetic_env_mode=False → raise RuntimeError。

    R03 禁止 fall-back: 禁止用合成环境冒充真实环境训练。
    """
    config = DistributedPPOConfig(synthetic_env_mode=False)
    trainer = DistributedPPOTrainer(config)
    with pytest.raises(RuntimeError, match="未注入真实布局布线环境"):
        trainer.training_step(n_episodes_per_worker=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
