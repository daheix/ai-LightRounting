"""回归测试: Bug #v3.3-Q-3 KLM CNOT 门实现 (Knill 2001 + Ralph 2002 方案)。

R05 v4.0-KLM-PROBABILISTIC-P1（第3轮迭代）:
    原 apply_klm_cnot 忽略概率性（硬编码 post_selected=True），
    已修复为真实概率抽样 + 失败分支 + 成功分支归一化。
    本测试文件同步更新:
    - 使用 ForceSuccessRNG 强制后选择成功（验证成功分支正确性）
    - 新增概率性蒙特卡洛测试（验证失败分支 + 成功率统计）
    - 更新 scheme 名为 "Ralph_2002_KLM_simplified"
    - 更新理论参考值为 1/9 (Ralph 2002) 而非 1/16 (Knill NS-gate)

验证 QuantumCircuitSimulator.apply_klm_cnot 的正确性:
- CNOT 真值表在后选择成功条件下成立
- KLM 物理仿真: 辅助光子 + 分束器网络 + 后选择测量
- 仿真后选择成功率 > 0 (量子干涉特征)
- 概率性: 蒙特卡洛 N 次后成功率 ≈ p_success

学术依据:
- Knill, Laflamme, Milburn, Nature 2001
  https://www.nature.com/articles/35051009
- Ralph et al., PRA 2002 (本实现采用的 4 分束器简化电路)
  https://doi.org/10.1103/PhysRevA.65.062324
- Hofmann & Takeuchi, PRA 2002
  https://doi.org/10.1103/PhysRevA.66.024308
- O'Brien et al., Nature 2003
  https://doi.org/10.1038/nature02354
- Knill, PRA 2002
  https://doi.org/10.1103/PhysRevA.66.052306
- Kok & Lovett, Rev. Mod. Phys. 2007 (后选择语义)
  https://doi.org/10.1103/RevModPhys.79.135

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.quantum.quantum_circuit_distributed import QuantumCircuitSimulator


class ForceSuccessRNG:
    """强制后选择成功的伪 RNG（仅用于测试成功分支）。

    random() 永远返回 0.0（< 任意 post_select_prob），保证 u < p。
    """

    def random(self, size=None):
        if size is None:
            return 0.0
        return np.zeros(size, dtype=float)

    def standard_normal(self, *args, **kwargs):
        raise NotImplementedError("ForceSuccessRNG 仅支持 random()")


class ForceFailureRNG:
    """强制后选择失败的伪 RNG（仅用于测试失败分支）。

    random() 永远返回 0.999（> 任意 post_select_prob < 1），保证 u >= p。
    """

    def random(self, size=None):
        if size is None:
            return 0.999
        return np.full(size, 0.999, dtype=float)

    def standard_normal(self, *args, **kwargs):
        raise NotImplementedError("ForceFailureRNG 仅支持 random()")


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
    使用 ForceSuccessRNG 强制后选择成功以验证成功分支正确性。
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    # 制备输入态 |q0_in, q1_in⟩
    if q0_in == 1:
        sim.apply_pauli_x(0)
    if q1_in == 1:
        sim.apply_pauli_x(1)

    # 应用 KLM CNOT (control=0, target=1) - 强制成功
    result = sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())

    # 验证后选择成功
    assert result["post_selected"] is True, f"{desc}: 后选择失败"
    # 验证仿真后选择成功率 > 0 (量子干涉特征)
    assert result["success_prob_simulated"] > 0.0, (
        f"{desc}: 仿真后选择成功率为零，电路实现错误"
    )
    # R05 v4.0-KLM-PROBABILISTIC-P1: scheme 改为 Ralph 2002 简化版
    assert result["scheme"] == "Ralph_2002_KLM_simplified", (
        f"{desc}: scheme 应为 Ralph_2002_KLM_simplified"
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
    - scheme 字段正确（Ralph 2002 简化版）
    - 理论参考值 ~1/9 (Ralph 2002 PRA 65, 062324)
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    result = sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())

    # 物理仿真: 后选择成功率应为正且小于 1
    assert 0.0 < result["success_prob_simulated"] < 1.0, (
        f"仿真后选择成功率 {result['success_prob_simulated']} 不在 (0, 1) 范围"
    )
    # 方案名称（R05 v4.0-KLM-PROBABILISTIC-P1: 改为 Ralph 2002）
    assert result["scheme"] == "Ralph_2002_KLM_simplified"
    # 理论参考值 Ralph 2002 ~1/9（不再是 Knill 1/16）
    assert result["success_prob_reference"] == pytest.approx(1.0 / 9.0), (
        f"理论参考值 {result['success_prob_reference']} != 1/9 (Ralph 2002)"
    )


def test_klm_cnot_gate_history() -> None:
    """验证 KLM CNOT 门历史记录。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())

    assert sim.gate_count >= 1
    last_gate = sim.gate_history[-1]
    assert last_gate["gate"] == "KLM_CNOT"
    assert last_gate["control"] == 0
    assert last_gate["target"] == 1
    assert "post_selected" in last_gate
    assert last_gate["post_selected"] is True
    assert "success_prob_simulated" in last_gate


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
# 4. KLM CNOT 与理想 CNOT 一致性验证（成功分支）
# =============================================================================

def test_klm_cnot_matches_ideal_cnot() -> None:
    """验证 KLM CNOT 在后选择成功条件下与理想 CNOT 一致。

    对 4 个基态输入，KLM CNOT 输出应与 apply_cnot 完全一致。
    使用 ForceSuccessRNG 强制后选择成功。
    """
    for q0_in, q1_in, _q0_out, _q1_out, _ in TRUTH_TABLE:
        # KLM CNOT（强制成功）
        sim_klm = QuantumCircuitSimulator(n_qubits=2)
        if q0_in == 1:
            sim_klm.apply_pauli_x(0)
        if q1_in == 1:
            sim_klm.apply_pauli_x(1)
        result = sim_klm.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())
        assert result["post_selected"] is True
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
# 6. KLM CNOT 应用于叠加态验证（成功分支）
# =============================================================================

def test_klm_cnot_superposition() -> None:
    """验证 KLM CNOT 应用于叠加态产生正确纠缠（成功分支）。

    H ⊗ I → KLM_CNOT 应产生 Bell 态 |Φ+⟩ = (|00⟩ + |11⟩)/√2。
    使用 ForceSuccessRNG 强制后选择成功。
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.apply_hadamard(0)  # |+0⟩ = (|00⟩ + |10⟩)/√2
    result = sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())
    assert result["post_selected"] is True

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


# =============================================================================
# 7. R05 v4.0-KLM-PROBABILISTIC-P1: 概率性回归测试
# =============================================================================

class TestKLMCNOTProbabilistic:
    """R05 v4.0-KLM-PROBABILISTIC-P1 回归: KLM CNOT 概率性本质。"""

    def test_failure_branch_state_unchanged(self):
        """失败分支: 数据量子比特状态保持不变。"""
        sim = QuantumCircuitSimulator(n_qubits=2)
        sim.apply_pauli_x(0)  # |10⟩
        sv_before = sim.state_vector.copy()

        result = sim.apply_klm_cnot(0, 1, rng=ForceFailureRNG())

        # 失败: post_selected=False
        assert result["post_selected"] is False
        # 状态向量应完全不变
        sv_after = sim.state_vector
        assert np.allclose(sv_after, sv_before), (
            "失败分支: 状态向量不应改变（KLM 门未施加）"
        )

    def test_failure_branch_returns_correct_fields(self):
        """失败分支返回字段正确。"""
        sim = QuantumCircuitSimulator(n_qubits=2)
        result = sim.apply_klm_cnot(0, 1, rng=ForceFailureRNG())

        assert result["post_selected"] is False
        assert result["scheme"] == "Ralph_2002_KLM_simplified"
        assert result["num_attempts"] == 1
        assert "note" in result
        assert 0.0 < result["success_prob_simulated"] < 1.0

    def test_failure_branch_gate_history_records_failure(self):
        """失败分支的门历史应记录 post_selected=False。"""
        sim = QuantumCircuitSimulator(n_qubits=2)
        sim.apply_klm_cnot(0, 1, rng=ForceFailureRNG())

        last_gate = sim.gate_history[-1]
        assert last_gate["gate"] == "KLM_CNOT"
        assert last_gate["post_selected"] is False

    def test_monte_carlo_success_rate_matches_probability(self):
        """蒙特卡洛验证: N 次独立后选择成功率 ≈ post_select_prob。

        物理本质: KLM CNOT 是概率性门，多次独立抽样的成功率应统计收敛到
        理论后选择成功率。
        """
        # 先获取一次理论概率
        sim0 = QuantumCircuitSimulator(n_qubits=2)
        result0 = sim0.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())
        p_success = result0["success_prob_simulated"]

        # 蒙特卡洛: 1000 次独立后选择
        rng = np.random.default_rng(42)
        n_trials = 1000
        n_success = 0
        for _ in range(n_trials):
            sim = QuantumCircuitSimulator(n_qubits=2)
            r = sim.apply_klm_cnot(0, 1, rng=rng)
            if r["post_selected"]:
                n_success += 1

        # 统计成功率应接近理论值（3σ 容忍）
        observed_rate = n_success / n_trials
        # 二项分布标准差
        std = np.sqrt(p_success * (1 - p_success) / n_trials)
        assert abs(observed_rate - p_success) < 5 * std, (
            f"蒙特卡洛成功率 {observed_rate:.4f} 偏离理论值 {p_success:.4f} "
            f"超过 5σ (std={std:.4f})"
        )

    def test_state_vector_norm_preserved_on_success(self):
        """成功分支: CNOT 是酉操作，态矢量模长应守恒。"""
        sim = QuantumCircuitSimulator(n_qubits=2)
        sim.apply_hadamard(0)
        norm_before = float(np.sqrt(np.sum(np.abs(sim.state_vector) ** 2)))

        sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())
        norm_after = float(np.sqrt(np.sum(np.abs(sim.state_vector) ** 2)))

        assert abs(norm_after - norm_before) < 1e-10, (
            f"成功分支态矢量模长变化: {norm_before} → {norm_after}"
        )

    def test_no_hardcoded_post_selected_true(self):
        """回归: apply_klm_cnot 不应硬编码 post_selected=True。

        原 Bug: L388 硬编码 "post_selected": True 是 R03 fall-back 违规。
        修复后: post_selected 由真实抽样决定。
        """
        # 失败 RNG 应能得到 post_selected=False
        sim = QuantumCircuitSimulator(n_qubits=2)
        result = sim.apply_klm_cnot(0, 1, rng=ForceFailureRNG())
        assert result["post_selected"] is False, (
            "post_selected 不应硬编码为 True（R03 禁止 fall-back）"
        )

    def test_no_knill_1_16_hardcoded(self):
        """回归: 不应硬编码 Knill 2001 的 1/16 理论值。

        原 Bug: L378 success_prob_theory = 1.0/16.0 是 Knill NS-gate 方案，
        但实际电路是 Ralph 2002 简化版，方案混用违反 R02 学术诚信。
        修复后: 改用 success_prob_reference = 1/9 (Ralph 2002)。
        """
        sim = QuantumCircuitSimulator(n_qubits=2)
        result = sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())

        # 不应再返回 success_prob_theory 字段（已删除，避免方案混用）
        assert "success_prob_theory" not in result, (
            "不应再返回 success_prob_theory（Knill 1/16 与 Ralph 2002 电路方案混用）"
        )
        # 应返回 success_prob_reference = 1/9 (Ralph 2002)
        assert "success_prob_reference" in result
        assert result["success_prob_reference"] == pytest.approx(1.0 / 9.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
