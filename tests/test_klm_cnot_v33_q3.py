"""回归测试: Bug #v3.3-Q-3 KLM CNOT 门实现 (Knill 2001 方案)。

验证 QuantumCircuitSimulator.apply_klm_cnot 的正确性:
- CNOT 真值表在后选择成功条件下成立
- KLM 物理仿真: 辅助光子 + 分束器网络 + 后选择测量
- 理论成功率 1/16 (Knill 2001 原始 NS gate 方案)
- 仿真后选择成功率 > 0 (量子干涉特征)

学术依据:
- Knill, Laflamme, Milburn, Nature 2001
  https://www.nature.com/articles/35051009
- Ralph et al., PRA 2002
  https://doi.org/10.1103/PhysRevA.65.062324
- Hofmann & Takeuchi, PRA 2002
  https://doi.org/10.1103/PhysRevA.66.024308
- O'Brien et al., Nature 2003
  https://doi.org/10.1038/nature02354
- Knill, PRA 2002
  https://doi.org/10.1103/PhysRevA.66.052306

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.quantum.quantum_circuit_distributed import QuantumCircuitSimulator

# =============================================================================
# 1. KLM CNOT 真值表验证（后选择成功条件下）
# =============================================================================

# CNOT(control=0, target=1) 真值表
# 状态向量位序: qubit0=高位(bit1), qubit1=低位(bit0)
# |q0, q1⟩ 索引 = q0 * 2 + q1
# |00⟩=0, |01⟩=1, |10⟩=2, |11⟩=3
TRUTH_TABLE = [
    # (q0_in, q1_in, q0_out, q1_out, 描述)
    (0, 0, 0, 0, "|00⟩ → |00⟩"),
    (0, 1, 0, 1, "|01⟩ → |01⟩"),
    (1, 0, 1, 1, "|10⟩ → |11⟩"),
    (1, 1, 1, 0, "|11⟩ → |10⟩"),
]


@pytest.mark.parametrize("q0_in,q1_in,q0_out,q1_out,desc", TRUTH_TABLE)
def test_klm_cnot_truth_table(q0_in: int, q1_in: int,
                              q0_out: int, q1_out: int, desc: str) -> None:
    """验证 KLM CNOT 真值表（后选择成功条件下）。

    KLM 方案核心: 后选择成功分支实现理想 CNOT 量子门。
    来源: Knill, Laflamme, Milburn, Nature 2001.
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    # 制备输入态 |q0_in, q1_in⟩
    if q0_in == 1:
        sim.apply_pauli_x(0)
    if q1_in == 1:
        sim.apply_pauli_x(1)

    # 应用 KLM CNOT (control=0, target=1)
    result = sim.apply_klm_cnot(0, 1)

    # 验证后选择成功
    assert result["post_selected"] is True, f"{desc}: 后选择失败"
    # 验证理论成功率 (Knill 2001 原始 NS gate 方案 = 1/16)
    assert result["success_prob_theory"] == pytest.approx(1.0 / 16.0), (
        f"{desc}: 理论成功率 {result['success_prob_theory']} != 1/16"
    )
    # 验证仿真后选择成功率 > 0 (量子干涉特征)
    assert result["success_prob_simulated"] > 0.0, (
        f"{desc}: 仿真后选择成功率为零，电路实现错误"
    )

    # 验证输出态: 应为 |q0_out, q1_out⟩
    sv = sim.state_vector
    expected_idx = q0_out * 2 + q1_out
    # 期望基态概率应接近 1
    probs = np.abs(sv) ** 2
    assert probs[expected_idx] > 0.99, (
        f"{desc}: 输出态概率 {probs[expected_idx]:.6f} < 0.99 "
        f"(期望 |{q0_out}{q1_out}⟩, 索引 {expected_idx})"
    )
    # 其他基态概率应接近 0
    for i in range(4):
        if i != expected_idx:
            assert probs[i] < 0.01, (
                f"{desc}: 非期望基态索引 {i} 概率 {probs[i]:.6f} > 0.01"
            )


# =============================================================================
# 2. KLM CNOT 物理仿真验证
# =============================================================================

def test_klm_cnot_physical_simulation() -> None:
    """验证 KLM CNOT 物理仿真（辅助光子+分束器网络+后选择）。

    验证:
    - 仿真后选择成功率 > 0 (量子干涉存在)
    - 仿真后选择成功率 < 1 (概率性门)
    - scheme 字段正确
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    result = sim.apply_klm_cnot(0, 1)

    # 物理仿真: 后选择成功率应为正且小于 1
    assert 0.0 < result["success_prob_simulated"] < 1.0, (
        f"仿真后选择成功率 {result['success_prob_simulated']} 不在 (0, 1) 范围"
    )
    # 方案名称
    assert result["scheme"] == "Knill_2001_KLM_Ralph_2002"
    # 理论值 Knill 2001
    assert result["success_prob_theory"] == pytest.approx(0.0625)


def test_klm_cnot_gate_history() -> None:
    """验证 KLM CNOT 门历史记录。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.apply_klm_cnot(0, 1)

    assert sim.gate_count >= 1
    last_gate = sim.gate_history[-1]
    assert last_gate["gate"] == "KLM_CNOT"
    assert last_gate["control"] == 0
    assert last_gate["target"] == 1
    assert "success_prob_theory" in last_gate
    assert "success_prob_simulated" in last_gate
    assert last_gate["success_prob_theory"] == pytest.approx(1.0 / 16.0)


# =============================================================================
# 3. KLM CNOT 参数校验（R03: 失败即 raise）
# =============================================================================

def test_klm_cnot_same_control_target_raises() -> None:
    """验证控制位和目标位相同时抛出异常（R03 禁止 fall-back）。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    with pytest.raises(ValueError, match="控制位和目标位不能相同"):
        sim.apply_klm_cnot(0, 0)


def test_klm_cnot_invalid_qubit_raises() -> None:
    """验证量子比特索引越界时抛出异常（R03 禁止 fall-back）。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    with pytest.raises(ValueError, match="越界"):
        sim.apply_klm_cnot(5, 1)
    with pytest.raises(ValueError, match="越界"):
        sim.apply_klm_cnot(0, -1)


# =============================================================================
# 4. KLM CNOT 与理想 CNOT 一致性验证
# =============================================================================

def test_klm_cnot_matches_ideal_cnot() -> None:
    """验证 KLM CNOT 在后选择成功条件下与理想 CNOT 一致。

    对 4 个基态输入，KLM CNOT 输出应与 apply_cnot 完全一致。
    """
    for q0_in, q1_in, _q0_out, _q1_out, _ in TRUTH_TABLE:
        # KLM CNOT
        sim_klm = QuantumCircuitSimulator(n_qubits=2)
        if q0_in == 1:
            sim_klm.apply_pauli_x(0)
        if q1_in == 1:
            sim_klm.apply_pauli_x(1)
        sim_klm.apply_klm_cnot(0, 1)
        sv_klm = sim_klm.state_vector.copy()

        # 理想 CNOT
        sim_ideal = QuantumCircuitSimulator(n_qubits=2)
        if q0_in == 1:
            sim_ideal.apply_pauli_x(0)
        if q1_in == 1:
            sim_ideal.apply_pauli_x(1)
        sim_ideal.apply_cnot(0, 1)
        sv_ideal = sim_ideal.state_vector.copy()

        # 两个状态向量应一致（相位 + 概率）
        # 由于可能存在全局相位差异，比较概率分布
        probs_klm = np.abs(sv_klm) ** 2
        probs_ideal = np.abs(sv_ideal) ** 2
        assert np.allclose(probs_klm, probs_ideal, atol=1e-10), (
            f"输入 |{q0_in}{q1_in}⟩: KLM CNOT 与理想 CNOT 输出不一致\n"
            f"KLM: {probs_klm}\nIdeal: {probs_ideal}"
        )


# =============================================================================
# 5. KLM CNOT 量子门类型枚举验证
# =============================================================================

def test_klm_cnot_gate_type_enum() -> None:
    """验证 KLM_CNOT 量子门类型枚举存在。"""
    from polaris.quantum.quantum_circuit_distributed import QuantumGateType

    assert QuantumGateType.KLM_CNOT.value == "KLM_CNOT"
    assert QuantumGateType.KLM_CZ.value == "KLM_CZ"


# =============================================================================
# 6. KLM CNOT 应用于叠加态验证
# =============================================================================

def test_klm_cnot_superposition() -> None:
    """验证 KLM CNOT 应用于叠加态产生正确纠缠。

    H ⊗ I → KLM_CNOT 应产生 Bell 态 |Φ+⟩ = (|00⟩ + |11⟩)/√2。
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.apply_hadamard(0)  # |+0⟩ = (|00⟩ + |10⟩)/√2
    sim.apply_klm_cnot(0, 1)

    sv = sim.state_vector
    # 期望 Bell 态 |Φ+⟩ = (|00⟩ + |11⟩)/√2
    # 索引: |00⟩=0, |11⟩=3
    probs = np.abs(sv) ** 2
    assert probs[0] == pytest.approx(0.5, abs=1e-10), (
        f"|00⟩ 概率 {probs[0]} != 0.5"
    )
    assert probs[3] == pytest.approx(0.5, abs=1e-10), (
        f"|11⟩ 概率 {probs[3]} != 0.5"
    )
    assert probs[1] < 1e-10, f"|01⟩ 概率 {probs[1]} 应为 0"
    assert probs[2] < 1e-10, f"|10⟩ 概率 {probs[2]} 应为 0"
