"""polaris-quantum-advanced — PoLaRIS 高级量子计算子模块（v5.1.0）。

迁移自 v4 旧包 polaris.sim.quantum_advanced / polaris.quantum.* 的高级量子功能，
删除旧包依赖，纯 NumPy/SciPy 实现（R04 不参与 GPU）。

# =============================================================================
# IPO 三段式说明（Input-Process-Output）
# =============================================================================
#
# [Input] 输入:
#   - 玻色采样: 酉矩阵 U (M×M)、输入光子态 |s⟩、输出态 |t⟩
#   - GBS: 协方差矩阵 σ (2M×2M)、输出模式 s
#   - 含损玻色采样: 酉矩阵 U、输入态、光子损失率 η_loss
#   - QKD (BB84/E91): 密钥长度、窃听标志、信道损耗 (dB)
#   - 量子层析: 测量基投影数据、Pauli 基列表
#   - CV 高斯态: 模式数 N、协方差矩阵 V、平均向量 d
#   - QEC: 接收字 (7 维 0/1)、错误类型
#   - 量子电路: 量子比特数、门序列
#   - 分布式 PPO: 观测维度、动作维度、配置超参数
#
# [Process] 处理:
#   - Ryser 算法计算矩阵积和式 O(N·2^N)（Aaronson-Arkhipov 2011）
#   - 玻色采样概率 P(s)=|Per(U_{S,T})|²/(Πs_i!·Πn_j!)
#   - Hafnian 函数计算 GBS 概率（Hamilton 2017）
#   - 含损玻色采样: 二项分布混合 + 量子优越性阈值 N_detected≥√N
#   - BB84 intercept-resend 窃听模型 + Shor-Preskill 阈值 11%
#   - E91 CHSH-Bell S 参数 + Acín 2006 成码率下界
#   - Hradil R 迭代 MLE 量子态层析
#   - Pauli 线性反演量子过程层析（Chuang-Nielsen 1997）
#   - CV 高斯态协方差矩阵 + 辛形式 V+iΩ/2≥0（Weedbrook 2012）
#   - Steane [[7,4,3]] CSS 纠错码（Hamming [7,4] 校验矩阵）
#   - GHZ/Cluster/NOON 资源态 + 图态邻接矩阵
#   - Kraus 算子光子损耗通道（Beer-Lambert η=exp(-αL)）
#   - KLM CNOT 4-BS 简化电路（Ralph 2002）+ 后选择玻色采样
#   - 分布式 PPO: Actor-Critic + GAE + PPO-Clip（Schulman 2017）
#
# [Output] 输出:
#   - 玻色采样: 输出概率分布 dict、HOM 可见度
#   - GBS: Hafnian 平方概率
#   - 含损玻色采样: 损失后分布、量子优越性判定
#   - QKD: QBER、安全标志、最终密钥 hex、成码率
#   - 层析: 重建密度矩阵 ρ、过程矩阵 χ、保真度
#   - CV: 协方差矩阵、平均向量、不确定性校验
#   - QEC: 纠正后字、症状、错误位置
#   - 电路: 态矢量、测量计数、Bell 态、KLM CNOT 成功率
#   - PPO: 训练统计（mean_reward/policy_loss/value_loss）
#
# =============================================================================
# 学术依据（R02，≥5 文献 URL）
# =============================================================================
#
# - Aaronson & Arkhipov, "The Computational Complexity of Linear Optics",
#   STOC 2011. URL: https://arxiv.org/abs/0910.4698
# - Hamilton et al., "Gaussian Boson Sampling", PRL 119, 170501 (2017).
#   URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
# - García-Patrón et al., "Simulating Boson Sampling in Lossy Architectures",
#   Quantum 3, 169 (2019). URL: https://arxiv.org/abs/1712.10037
# - Bennett & Brassard, "Quantum Cryptography: Public Key Distribution
#   and Coin Tossing", 1984. URL: https://doi.org/10.1145/358340.358342
# - Ekert, "Quantum Cryptography Based on Bell's Theorem", PRL 67, 661 (1991).
#   URL: https://doi.org/10.1103/PhysRevLett.67.661
# - Shor & Preskill, "Simple Proof of Security of the BB84 QKD Protocol",
#   PRL 85, 441 (2000). URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.85.441
# - Acín et al., "Device-Independent Security of QKD Against Collective
#   Attacks", PRL 97, 230503 (2006).
#   URL: https://doi.org/10.1103/PhysRevLett.97.230503
# - Hradil, "Quantum-State Estimation", Phys Rev A 55, R1561 (1997).
#   URL: https://doi.org/10.1103/PhysRevA.55.R1561
# - Chuang & Nielsen, "Prescription for Experimental Determination of the
#   Dynamics of a Quantum Black Box", 1997.
#   URL: https://arxiv.org/abs/quant-ph/9610001
# - Weedbrook et al., "Gaussian Quantum Information", Rev Mod Phys 84, 621 (2012).
#   URL: https://doi.org/10.1103/RevModPhys.84.621
# - Steane, "Error Correcting Codes in Quantum Theory", PRL 77, 793 (1996).
#   URL: https://doi.org/10.1103/PhysRevLett.77.793
# - Knill, Laflamme, Milburn, "A scheme for efficient quantum computation
#   with linear optics", Nature 2001.
#   URL: https://www.nature.com/articles/35051009
# - Ralph, Langford, Bell, White, "Linear optical controlled-NOT gate in
#   the coincidence basis", PRA 2002.
#   URL: https://doi.org/10.1103/PhysRevA.65.062324
# - Hong, Ou, Mandel, "Measurement of subpicosecond time intervals
#   between two photons by interference", PRL 59, 2044 (1987).
#   URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
# - Schulman et al., "Proximal Policy Optimization Algorithms",
#   arXiv:1707.06347 (2017). URL: https://arxiv.org/abs/1707.06347
# - Schulman et al., "High-Dimensional Continuous Control Using
#   Generalized Advantage Estimation", ICLR 2016.
#   URL: https://arxiv.org/abs/1506.02438
# - Ryser, "Combinatorial Mathematics", 1963（积和式算法）.
# - Kok & Lovett, "Introduction to Optical Quantum Computing",
#   Rev Mod Phys 2007. URL: https://doi.org/10.1103/RevModPhys.79.135
# - Nelder & Mead, "A Simplex Method for Function Minimization",
#   Comput J 7, 308 (1965). URL: https://doi.org/10.1093/comjnl/7.4.308
#
# =============================================================================
# *创新* 标注（R02 学术诚信）
# =============================================================================
#
# *创新* 1: 模块化拆分 — 将 v4 单体 887 行 quantum_advanced.py 拆分为
#   16 个独立功能文件（permanent/boson_sampling/gbs/lossy/numerical/
#   advanced_sampling/tomography/qkd/cv_gates/qec/resources/noise/fitting/
#   klm_helpers/circuit_simulator/distributed_ppo），每个 ≤300 行，
#   满足函数≤80行 / 文件≤800行质量门禁。
#   底层逻辑：单一职责原则（SRP）+ Extract Module 重构模式（Fowler 2018）。
#   支持理论：软件工程模块化耦合度量（Parnas 1972）。
#
# *创新* 2: 依赖解耦 — 删除 v4 对 polaris.sim/polaris.quantum 旧包的
#   所有 import，改为同包内引用（polaris_quantum_advanced.*），实现
#   子模块自包含部署。
#   底层逻辑：依赖倒置 + 零外部耦合。
#   支持理论：微服务独立部署原则（Newman 2015）。
#
# *创新* 3: R05 v4.0-FAKE-ENV-P0 守门逻辑保留 — 分布式 PPO 训练器
#   默认拒绝用合成环境训练（synthetic_env_mode=False），必须注入真实
#   FloorplanEnv 或显式开启合成测试模式，防止用假数据冒充商业可用。
#   底层逻辑：R03 禁止 fall-back + 显式失败优于静默兜底。
#   支持理论：防御性编程 + 契约式设计（Meyer 1997）。
#
# 合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修 /
#       R13 不保留 v4 兼容（彻底迁移，无遗留）。
"""

from polaris_quantum_advanced.permanent import (
    permanent_ryser,
    permanent_brute_force,
)
from polaris_quantum_advanced.boson_sampling import (
    BosonSamplingResult,
    beamsplitter_unitary,
    hom_interference,
    boson_sampling_prob,
    boson_sampling_distribution,
)
from polaris_quantum_advanced.gbs import (
    hafnian,
    gbs_probability,
)
from polaris_quantum_advanced.lossy import (
    lossy_boson_sampling,
    quantum_advantage_threshold,
)
from polaris_quantum_advanced.numerical import (
    hom_dip_simulation,
    boson_sampling_sampler,
    boson_sampling_chi_square_test,
)
from polaris_quantum_advanced.advanced_sampling import (
    LargeScaleBosonSampler,
    HOMInterferometer,
)
from polaris_quantum_advanced.tomography import (
    TomographyResult,
    QuantumStateTomography,
    QuantumProcessTomography,
)
from polaris_quantum_advanced.qkd import (
    QKDResult,
    BB84Protocol,
    BB84EnhancedProtocol,
    E91Protocol,
)
from polaris_quantum_advanced.cv_gates import (
    GaussianState,
    DisplacementGate,
    SqueezingGate,
    RotationGate,
    BeamSplitterGate,
    HomodyneDetection,
)
from polaris_quantum_advanced.qec import (
    ThreeQubitRepetitionCode,
    BitFlipError,
    PhaseFlipError,
    SyndromeMeasurement,
    RecoveryOperation,
    SteaneCode,
)
from polaris_quantum_advanced.resources import (
    GHZState,
    ClusterState1D,
    NOONState,
    StateFidelity,
)
from polaris_quantum_advanced.noise import (
    PhotonLossChannel,
    PhaseNoiseChannel,
    DetectorModel,
)
from polaris_quantum_advanced.fitting import (
    FitResult,
    SParamFitter,
    LossExtractor,
    CouplingEfficiencyExtractor,
)
from polaris_quantum_advanced.klm_helpers import (
    _permanent_ryser,
    _klm_cnot_unitary,
    _klm_cnot_post_select_probability,
    _boson_probability,
)
from polaris_quantum_advanced.circuit_simulator import (
    QuantumGateType,
    Qubit,
    QuantumCircuitSimulator,
)
from polaris_quantum_advanced.distributed_ppo import (
    DistributedPPOConfig,
    WorkerStats,
    DistributedPPOTrainer,
)

__version__ = "5.1.0"

__all__ = [
    # permanent
    "permanent_ryser",
    "permanent_brute_force",
    # boson_sampling
    "BosonSamplingResult",
    "beamsplitter_unitary",
    "hom_interference",
    "boson_sampling_prob",
    "boson_sampling_distribution",
    # gbs
    "hafnian",
    "gbs_probability",
    # lossy
    "lossy_boson_sampling",
    "quantum_advantage_threshold",
    # numerical
    "hom_dip_simulation",
    "boson_sampling_sampler",
    "boson_sampling_chi_square_test",
    # advanced_sampling
    "LargeScaleBosonSampler",
    "HOMInterferometer",
    # tomography
    "TomographyResult",
    "QuantumStateTomography",
    "QuantumProcessTomography",
    # qkd
    "QKDResult",
    "BB84Protocol",
    "BB84EnhancedProtocol",
    "E91Protocol",
    # cv_gates
    "GaussianState",
    "DisplacementGate",
    "SqueezingGate",
    "RotationGate",
    "BeamSplitterGate",
    "HomodyneDetection",
    # qec
    "ThreeQubitRepetitionCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    "SteaneCode",
    # resources
    "GHZState",
    "ClusterState1D",
    "NOONState",
    "StateFidelity",
    # noise
    "PhotonLossChannel",
    "PhaseNoiseChannel",
    "DetectorModel",
    # fitting
    "FitResult",
    "SParamFitter",
    "LossExtractor",
    "CouplingEfficiencyExtractor",
    # klm_helpers
    "_permanent_ryser",
    "_klm_cnot_unitary",
    "_klm_cnot_post_select_probability",
    "_boson_probability",
    # circuit_simulator
    "QuantumGateType",
    "Qubit",
    "QuantumCircuitSimulator",
    # distributed_ppo
    "DistributedPPOConfig",
    "WorkerStats",
    "DistributedPPOTrainer",
]
