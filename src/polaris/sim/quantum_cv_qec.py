"""R551-R555 量子光子增强综合模块（纯 NumPy/SciPy CPU，R04 兼容）。

本模块为 PoLaRIS 量子光子计算提供增强能力，覆盖 R551-R555 + R556-R600：

- R551 连续变量（CV）量子计算：高斯态协方差矩阵表示 + 位移/压缩/旋转/
  分束器门 + 零差检测
- R552 量子纠错编码：三比特重复码 / Steane [[7,4,3]] 码 / 简化表面码
- R553 资源态生成：GHZ 态 / 1D 簇态 / NOON 态
- R554 噪声模型增强：光子损耗 / 相位噪声 / 探测器暗计数 + 效率
- R555 实验数据拟合接口：S 参数拟合 / 损耗提取 / 耦合效率提取
- R556-R600 量子游走 / QML 基础 / 优越性验证（本模块只含基础接口）

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Braunstein & van Loock 2005 Rev Mod Phys 77 513-577
   The quantum information of continuous variables
   https://doi.org/10.1103/RevModPhys.77.513
2. Weedbrook et al. 2012 Rev Mod Phys 84 621-669 Gaussian quantum information
   https://doi.org/10.1103/RevModPhys.84.621
3. Nielsen & Chuang 2010 Quantum Computation and Quantum Information
   Cambridge University Press https://www.cambridge.org/9781107002173
4. Shor 1995 PRA 52 R2493-R2496 Scheme for reducing decoherence
   https://doi.org/10.1103/PhysRevA.52.R2493
5. Steane 1996 PRL 77 793-797 Multiple-particle interference and quantum
   error correction https://doi.org/10.1103/PhysRevLett.77.793
6. Hein, Eisert, Briegel 2004 PRA 69 062311 Multi-party entanglement in
   graph states https://doi.org/10.1103/PhysRevA.69.062311
7. Kok & Lovett 2010 Introduction to Optical Quantum Information Processing
   Cambridge University Press https://www.cambridge.org/9780521191356
8. Knill, Laflamme, Milburn 2001 Nature 409 46-52 Linear optical QC
   https://doi.org/10.1038/35051009
9. O'Brien, Furusawa, Vuckovic 2009 Nat Photonics 3 687-695 Photonic QC
   https://doi.org/10.1038/nphoton.2009.229
10. Menicucci, Flammia, Pfister 2008 PRL 101 220501 One-way QC with CV
    cluster states https://doi.org/10.1103/PhysRevLett.101.220501

## *创新* 标注（R02）

- *创新* R551：用协方差矩阵 V + 平均向量 d 双量表示 CV 高斯态
  （Weedbrook 2012 §II），所有高斯门用辛变换 S + 位移 α 实现，
  避免显式 Hilbert 空间存储（指数降复杂度）。
- *创新* R552：Steane 码 [[7,4,3]] 用 stabilizer 形式实现，7 个稳定子
  生成元 S_i 直接构造投影到码空间的密度矩阵，避免 128×128 完全矩阵。
- *创新* R553：簇态用图态邻接矩阵 A 计算 V = (i/2)·[[0, I], [-I, 0]]
  + A · X-measurement 算法（Hein 2004 §III），无需逐个 CNOT。
- *创新* R554：光子损耗通道用 Kraus 算子 E_k = sqrt((1-η)^k / k!)·
  a^k·η^(n/2) 实现（Kok & Lovett 2010 §3.2），密度矩阵演化保持
  正定性，与 Beer-Lambert 定律 η=exp(-α·L) 一致。
- *创新* R555：S 参数拟合用 Nelder-Mead 简单x + 损耗物理约束
  |S_ij|² ≤ 1，避免非物理解。

## 规则依据

规则 14（非法输入 raise）/规则 18（学术诚信）/规则 26（GPU 不参与）

批次 10-B 拆分说明（2026-07-01）:
    原文件 1146 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 5 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.sim.quantum_cv_qec_cv: R551 GaussianState/DisplacementGate/
      SqueezingGate/RotationGate/BeamSplitterGate/HomodyneDetection
    - polaris.sim.quantum_cv_qec_qec: R552 ThreeQubitRepetitionCode/
      SteaneCode/BitFlipError/PhaseFlipError/SyndromeMeasurement/RecoveryOperation
    - polaris.sim.quantum_cv_qec_resources: R553 GHZState/ClusterState1D/
      NOONState/StateFidelity
    - polaris.sim.quantum_cv_qec_noise: R554 PhotonLossChannel/
      PhaseNoiseChannel/DetectorModel
    - polaris.sim.quantum_cv_qec_fitting: R555 FitResult/SParamFitter/
      LossExtractor/CouplingEfficiencyExtractor

来源:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.sim.quantum_cv_qec import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.sim.quantum_cv_qec_cv import (
    BeamSplitterGate,
    DisplacementGate,
    GaussianState,
    HomodyneDetection,
    RotationGate,
    SqueezingGate,
)
from polaris.sim.quantum_cv_qec_qec import (
    BitFlipError,
    PhaseFlipError,
    RecoveryOperation,
    SteaneCode,
    SyndromeMeasurement,
    ThreeQubitRepetitionCode,
)
from polaris.sim.quantum_cv_qec_resources import (
    ClusterState1D,
    GHZState,
    NOONState,
    StateFidelity,
)
from polaris.sim.quantum_cv_qec_noise import (
    DetectorModel,
    PhaseNoiseChannel,
    PhotonLossChannel,
)
from polaris.sim.quantum_cv_qec_fitting import (
    CouplingEfficiencyExtractor,
    FitResult,
    LossExtractor,
    SParamFitter,
)

__all__ = [
    # R551
    "GaussianState",
    "DisplacementGate",
    "SqueezingGate",
    "RotationGate",
    "BeamSplitterGate",
    "HomodyneDetection",
    # R552
    "ThreeQubitRepetitionCode",
    "SteaneCode",
    "BitFlipError",
    "PhaseFlipError",
    "SyndromeMeasurement",
    "RecoveryOperation",
    # R553
    "GHZState",
    "ClusterState1D",
    "NOONState",
    "StateFidelity",
    # R554
    "PhotonLossChannel",
    "PhaseNoiseChannel",
    "DetectorModel",
    # R555
    "SParamFitter",
    "LossExtractor",
    "CouplingEfficiencyExtractor",
    "FitResult",
]
