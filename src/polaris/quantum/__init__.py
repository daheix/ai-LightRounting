"""PoLaRIS 量子光子模块。

提供量子电路仿真器、BB84 QKD 协议、分布式 PPO 训练等能力，
对齐 Ansys Lumerical CML Compiler + 量子电路仿真器 + AlphaChip 分布式训练。

子模块:
- quantum_circuit_distributed: 量子电路 + BB84 QKD + 分布式 PPO + M6 交付清单

学术依据:
- Knill, Laflamme, Milburn 2001 (KLM 线性光学量子计算) Nature 409, 46-52
  URL: https://www.nature.com/articles/35051009
- Bennett & Brassard 1984 (BB84 量子密钥分发协议)
- Mirhoseini et al., "AlphaChip: A graph placement method for fast chip design",
  Nature 2021. URL: https://www.nature.com/articles/s41586-021-03544-w
- Ansys Lumerical CML Compiler
  URL: https://www.ansys.com/products/optics/interconnect

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from polaris.quantum.quantum_circuit_distributed import (
    BB84Protocol,
    DistributedPPOTrainer,
    M6Deliverable,
    QuantumCircuitSimulator,
    RoadmapScoreSummary,
)

__all__ = [
    "BB84Protocol",
    "DistributedPPOTrainer",
    "M6Deliverable",
    "QuantumCircuitSimulator",
    "RoadmapScoreSummary",
]
