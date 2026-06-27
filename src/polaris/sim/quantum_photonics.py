"""R35: 量子光子电路仿真器（Facade，外部 API 入口）。

实现线性光学网络仿真、玻色采样概率分布计算、HOM 干涉验证、
Gaussian Boson Sampling 与可微分量子光子仿真。

本文件为 facade 模块，将原 941 行实现按功能拆分为 6 个子模块，
保持外部 import 路径 `from polaris.sim.quantum_photonics import X` 不变。

核心算法:
- Ryser 算法计算矩阵积和式（permanent），复杂度 O(N·2^N)
- HOM 干涉符合计数率计算
- 含光子损失的玻色采样（张量网络法）

子模块:
- quantum_permanent: 矩阵积和式（Ryser / 暴力法）
- quantum_boson_sampling: 线性光学网络、HOM 干涉、玻色采样分布
- quantum_lossy: 含光子损失的玻色采样、量子优越性阈值（*创新*）
- quantum_gbs: Gaussian Boson Sampling（Hafnian / GBS 概率）
- quantum_klm: KLM 量子门、Clements 分解、KLM CNOT 仿真（*创新*）
- quantum_numerical: HOM dip 数值仿真、采样器、卡方检验

来源（学术诚信 R02）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂度
  https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024, BosonSampling.jl
  https://arxiv.org/abs/2212.09537
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Hamilton et al., PRL 2017, Gaussian Boson Sampling
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- García-Patrón et al., arXiv 2024, 损失架构玻色采样
  https://arxiv.org/abs/1712.10037
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009
- Ryser, 1963, Combinatorial Mathematics（积和式算法）

🚫不参与 GPU（R04）：纯 NumPy/SciPy 实现。
"""

from __future__ import annotations

# Facade re-export：保持外部 `from polaris.sim.quantum_photonics import X` 路径不变
from polaris.sim.quantum_boson_sampling import (  # noqa: F401
    BosonSamplingResult,
    beamsplitter_unitary,
    boson_sampling_distribution,
    boson_sampling_prob,
    hom_interference,
)
from polaris.sim.quantum_gbs import (  # noqa: F401
    gbs_probability,
    hafnian,
)
from polaris.sim.quantum_klm import (  # noqa: F401
    clements_unitary,
    klm_cnot_circuit,
    klm_cnot_simulate,
    klm_cnot_success_probability,
    klm_hadamard_gate,
)
from polaris.sim.quantum_lossy import (  # noqa: F401
    lossy_boson_sampling,
    quantum_advantage_threshold,
)
from polaris.sim.quantum_numerical import (  # noqa: F401
    boson_sampling_chi_square_test,
    boson_sampling_sampler,
    hom_dip_simulation,
)
from polaris.sim.quantum_permanent import (  # noqa: F401
    permanent_brute_force,
    permanent_ryser,
)

__all__ = [
    "BosonSamplingResult",
    "beamsplitter_unitary",
    "boson_sampling_chi_square_test",
    "boson_sampling_distribution",
    "boson_sampling_prob",
    "boson_sampling_sampler",
    "clements_unitary",
    "gbs_probability",
    "hafnian",
    "hom_dip_simulation",
    "hom_interference",
    "klm_cnot_circuit",
    "klm_cnot_simulate",
    "klm_cnot_success_probability",
    "klm_hadamard_gate",
    "lossy_boson_sampling",
    "permanent_brute_force",
    "permanent_ryser",
    "quantum_advantage_threshold",
]
