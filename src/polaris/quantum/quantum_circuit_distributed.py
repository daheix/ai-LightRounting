"""M6-R33/R35/R36: 量子电路仿真器 + multiprocessing 分布式 PPO + M6 交付清单。

对齐 Ansys Lumerical CML Compiler + 量子电路 + Google AlphaChip 分布式训练。

批次 10-B 拆分说明（2026-07-01）:
    原文件 1798 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 4 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.quantum.klm_helpers: KLM CNOT 物理仿真辅助函数
    - polaris.quantum.circuit_simulator: QuantumGateType / Qubit / QuantumCircuitSimulator
    - polaris.quantum.bb84_protocol: BB84Protocol
    - polaris.quantum.distributed_ppo: DistributedPPOConfig / WorkerStats /
      _BaseMLP / _PolicyNetwork / _ValueNetwork / DistributedPPOTrainer
    - polaris.quantum.m6_deliverable: M6Deliverable / RoadmapScoreSummary

R05 Bug 修复 v3.3-Q-6: 原引用 Ray RLlib 文献但实际用 multiprocessing.Pool，
文献虚标违反 R02 学术诚信。修复：删除 Ray 引用，替换为实际使用的
multiprocessing 文献，并在 DistributedPPOTrainer 注释中明确说明。

R5-P1-6: simulate_training_step deprecated 方法已删除（保留 R5-P1-6 回归测试约束）。

学术依据:
- Knill, Laflamme, Milburn, "A scheme for efficient quantum computation with linear optics",
  Nature 2001. URL: https://www.nature.com/articles/35051009
- Ralph, Langford, Bell, White, "Linear optical controlled-NOT gate in the
  coincidence basis", PRA 2002. URL: https://doi.org/10.1103/PhysRevA.65.062324
- Hofmann & Takeuchi, "Quantum phase gate for two qubits using single photons
  and linear optics", PRA 2002. URL: https://doi.org/10.1103/PhysRevA.66.024308
- O'Brien, Pryde, White, Ralph, Branning, "Demonstration of an all-optical
  quantum controlled-NOT gate", Nature 2003. URL: https://doi.org/10.1038/nature02354
- Knill, "Quantum gating using quantum interference", PRA 2002.
  URL: https://doi.org/10.1103/PhysRevA.66.052306
- Kok, Lovett, "Introduction to Optical Quantum Computing", Rev. Mod. Phys. 2007.
  URL: https://doi.org/10.1103/RevModPhys.79.135
- Clements et al., "Optimal design of universal linear optical unitary",
  Optica 2016. URL: https://doi.org/10.1364/OPTICA.3.001460
- Hong, Ou, Mandel, "Measurement of subpicosecond time intervals
  between two photons by interference", PRL 59, 2044 (1987)
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Kwiat et al. 1995 PRL 75(24) 4337（SPDC 单光子源相干长度）
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.75.4337
- Bouwmeester et al. 1997 Nature 390(6660) 575（HOM 实验相干长度测量）
  URL: https://www.nature.com/articles/37527
- BB84 量子密钥分发: Bennett & Brassard, SIGACT News 1984
  URL: https://doi.org/10.1145/358340.358342
- Lo & Chau 1999 Science 283(5410) 2050-2056
  URL: https://www.science.org/doi/10.1126/science.283.5410.2050
- Shor & Preskill 2000 PRL 85(2) 441-444（11% QBER 阈值证明）
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.85.441
- Fuchs et al. 1997 PRA 56(2) 1163（信息-扰动权衡）
  URL: https://journals.aps.org/pra/abstract/10.1103/PhysRevA.56.1163
- ITU-T G.652 单模光纤标准（0.2 dB/km @ 1550nm 衰减系数）
  URL: https://www.itu.int/rec/T-REC-G.652
- ETSI GS QKD 002 QKD 网络实施规范（城域网链路损耗 2-5 dB）
  URL: https://www.etsi.org/deliver/etsi_gs/QKD/001_099/002/
- AlphaChip Nature 2024: https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training (Google, JAX/Optax 分布式，非 Ray):
  https://github.com/google-research/circuit_training
- Python multiprocessing 标准库（本实现实际使用的并行后端）:
  https://docs.python.org/3/library/multiprocessing.html
- Schulman et al., PPO, arXiv 2017. URL: https://arxiv.org/abs/1707.06347
- Lumerical CML Compiler
  URL: https://optics.ansys.com/hc/en-us/articles/360037565953

KLM CNOT 门 (#v3.3-Q-3 修复, Ralph 2002 简化版方案):
- 4 模式电路: control, target, aux1, aux2 (Ralph 2002 简化版)
- 辅助光子: |1,1⟩_aux (2 个单光子源)
- 分束器网络: 4 个分束器 (θ₁=arccos√(2/3), θ₂=arccos√(2/3),
  θ₃=π/4, θ₄=arccos√(1/3))
- 后选择: 辅助模式各探测到 1 光子
- 成功概率: ~1/9 (Ralph 2002 PRA 65, 062324 简化 4-BS 电路实测)
  注: Knill 2001 Nature 原始 NS-gate 方案理论成功率 1/16，但本实现
  采用 Ralph 2002 简化电路（4 个分束器），成功率不同。
  R4-P0-5 文档修复: 原 docstring 误标 1/16 (Knill NS-gate)，与实际
  电路（Ralph 2002）不匹配，违反 R02 学术诚信（方案混用）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.quantum.quantum_circuit_distributed import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.quantum.klm_helpers import (
    _boson_probability,
    _klm_cnot_post_select_probability,
    _klm_cnot_unitary,
    _permanent_ryser,
)
from polaris.quantum.circuit_simulator import (
    Qubit,
    QuantumCircuitSimulator,
    QuantumGateType,
)
from polaris.quantum.bb84_protocol import BB84Protocol
from polaris.quantum.distributed_ppo import (
    DistributedPPOConfig,
    DistributedPPOTrainer,
    WorkerStats,
    _BaseMLP,
    _PolicyNetwork,
    _ValueNetwork,
)
from polaris.quantum.m6_deliverable import (
    M6Deliverable,
    RoadmapScoreSummary,
)

__all__ = [
    "BB84Protocol",
    "DistributedPPOConfig",
    "DistributedPPOTrainer",
    "M6Deliverable",
    "Qubit",
    "QuantumCircuitSimulator",
    "QuantumGateType",
    "RoadmapScoreSummary",
    "WorkerStats",
    "_BaseMLP",
    "_PolicyNetwork",
    "_ValueNetwork",
    "_boson_probability",
    "_klm_cnot_post_select_probability",
    "_klm_cnot_unitary",
    "_permanent_ryser",
]


# =============================================================================
# 6. 模块内冒烟测试（python -m polaris.quantum.quantum_circuit_distributed）
# =============================================================================

def _test() -> None:
    """冒烟测试（R605 拆分为子测试降低圈复杂度）。

    来源:
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      https://refactoring.com/catalog/extractFunction.html
    """
    _test_quantum_circuit()
    _test_bb84_qkd()
    _test_distributed_ppo()
    _test_m6_deliverable()
    _test_roadmap_score()
    print("\n所有测试通过 ✅")


def _test_quantum_circuit() -> None:
    """Test 1: 量子电路仿真器与多门验证（R605 Extract Method）。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    # Bell 态
    sim.bell_state(0, 1)
    sv = sim.state_vector
    # |Φ+⟩ = (|00⟩ + |11⟩)/√2
    assert abs(abs(sv[0]) - 1/np.sqrt(2)) < 1e-10
    assert abs(abs(sv[3]) - 1/np.sqrt(2)) < 1e-10
    assert abs(sv[1]) < 1e-10 and abs(sv[2]) < 1e-10
    # 测量
    counts = sim.measure(0, shots=1000)
    assert counts[0] + counts[1] == 1000
    # HOM dip
    visibility = sim.hom_dip(delay_um=0.0)
    assert visibility > 0.99
    # 门计数
    assert sim.gate_count >= 2  # H + CNOT
    print(f"量子电路: {sim.n_qubits} qubits, {sim.gate_count} gates, "
          f"Bell态 |Φ+⟩ OK, HOM V={visibility:.3f}")

    # 3+ 量子门验证
    sim2 = QuantumCircuitSimulator(n_qubits=2)
    sim2.apply_hadamard(0)
    sim2.apply_pauli_x(1)
    sim2.apply_klm_cz(0, 1)
    sim2.apply_phase_shifter(0, np.pi / 4)
    sim2.apply_beamsplitter(0, 1, 0.5)
    assert sim2.gate_count >= 5  # H + X + CZ + PS + BS ≥ 3 量子门
    print(f"量子门: H/X/CZ/PS/BS = {sim2.gate_count} 个门验证通过")


def _test_bb84_qkd() -> None:
    """Test 2: BB84 QKD 安全性验证（R605 Extract Method）。"""
    bb84 = BB84Protocol(key_length=128)
    # 无窃听
    result_clean = bb84.simulate(eavesdrop=False, channel_loss_db=3.0)
    assert result_clean["qber"] < 0.11
    assert result_clean["is_secure"]
    # 有窃听
    result_eve = bb84.simulate(eavesdrop=True, channel_loss_db=3.0)
    # 窃听应提高 QBER
    assert result_eve["qber"] > result_clean["qber"]
    print(f"QKD BB84: 无窃听QBER={result_clean['qber']:.1%} (安全), "
          f"有窃听QBER={result_eve['qber']:.1%} (检测到={result_eve['eavesdrop_detected']})")


def _test_distributed_ppo() -> None:
    """Test 3: 分布式 PPO 训练流程（R605 Extract Method）。"""
    # R05 v4.0-FAKE-ENV-P0: 冒烟测试需显式启用 synthetic_env_mode（算法测试用）
    config = DistributedPPOConfig(
        n_workers=4, n_devices_per_circuit=5000, synthetic_env_mode=True,
    )
    trainer = DistributedPPOTrainer(config)
    # 模拟训练（合成环境，仅验证 PPO 算法流程）
    # R5-P1-6 修复: 删除 deprecated simulate_training_step，直接调用 training_step。
    # n_episodes=100, total_workers=4 → per_worker=25
    step_result = trainer.training_step(25)
    assert step_result["n_workers"] == 4
    assert step_result["total_episodes"] >= 100
    # 渐进式扩展
    stages = trainer.progressive_scaling(target_devices=5000)
    assert len(stages) == 5
    assert stages[-1]["stage_devices"] == 5000
    rpt = trainer.report()
    assert rpt["n_workers"] >= 4
    assert rpt["total_devices_processed"] > 0
    print(f"分布式PPO: {rpt['n_workers']} workers, {rpt['total_episodes']} episodes, "
          f"{rpt['total_devices_processed']} 器件已处理, "
          f"best_reward={rpt['best_reward']:.2f}")


def _test_m6_deliverable() -> None:
    """Test 4: M6 交付检查（R605 Extract Method）。"""
    m6 = M6Deliverable()
    m6_rpt = m6.report()
    assert m6_rpt["total_items"] >= 25
    assert m6_rpt["completion_rate"] >= 0.9
    print(f"M6交付: {m6_rpt['passed_items']}/{m6_rpt['total_items']} 通过, "
          f"完成率={m6_rpt['completion_rate']:.1%}, "
          f"目标={m6_rpt['target_score']}")


def _test_roadmap_score() -> None:
    """Test 5: 全路标得分与基准数据得分（R605 Extract Method）。"""
    # R05 v4.0-FAKE-SCORE-P0: 删除原 9.2/10 虚标断言。无基准数据时得分为 None。
    scores = RoadmapScoreSummary.report()
    assert scores["milestones"]["M6_R36"] is None, (
        "无基准数据时 M6 得分应为 None（R02 拒绝虚标 9.2/10）"
    )
    assert scores["total_improvement"] is None
    assert scores["exceeds_industry_max"] is None
    print(f"路标得分: {scores['milestones']}")
    print(f"  总提升: {scores['total_improvement']}, "
          f"超越行业最高: {scores['exceeds_industry_max']}")

    # 提供完整基准数据时应能计算出合理得分
    benchmark = {
        "hpwl_improvement_pct": 15.0,
        "congestion_reduction_pct": 60.0,
        "drc_violation_count": 0,
        "runtime_seconds": 200.0,
        "device_count": 1000,
        "industry_benchmark_hpwl_pct": 10.0,
        "industry_benchmark_runtime_s": 300.0,
    }
    real_score = RoadmapScoreSummary.compute_score("M6_R36", benchmark)
    assert 0.0 <= real_score <= 10.0
    print(f"  M6 真实得分（基准数据）: {real_score:.2f}/10")


if __name__ == "__main__":
    _test()
