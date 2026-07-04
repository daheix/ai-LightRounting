"""polaris-circuit: PoLaRIS 电路级仿真子模块（v5.0）。

本模块从 v4 旧包 polaris.sim 迁移并模块化，提供光子电路频域/时域/SPICE MNA/
系统级/电路互联全套仿真功能，纯 NumPy/SciPy 实现（R04 合规，不参与 GPU）。

================================================================
IPO 三段式说明（Input - Process - Output）
================================================================

Input（输入）:
    - 网表 dict: {instances, connections, ports}，SAX 兼容格式
    - 器件 S 参数模型函数 ModelFunc: (wl, **kwargs) -> SDict
    - 波长数组 np.ndarray（μm，光通信波段 0.5-2.0）
    - MNA 电路描述 MNACircuit: 节点 + R/C/L/V/I/D 元件列表
    - 时域输入信号 np.ndarray（复数）
    - 系统级参数: 调制格式(NRZ/PAM4/QAM16)、链路损耗、激光器参数
    - 频域 S 参数字典 SDict: {(port_out, port_in): ndarray}

Process（处理）:
    - 频域仿真: 子网络增长算法（Filipsson 1978）级联器件 S 参数
    - 群延迟: 中心差分 τ_g = dφ/dω
    - 条件数诊断: κ(S) = σ_max/σ_min 评估数值稳定性
    - SPICE MNA: 改进节点分析法 [G B; C D][v; i]=[I; E]，DC + 后向欧拉瞬态
    - 二极管: Shockley 模型 + Newton-Raphson 线性化
    - 系统级: Mason 信号流图增益公式 + TLLM 速率方程(RK4) + FFT/IFFT 频时耦合
    - 时域电路: TLLM 风格波导/MZI 传输 + Kerr/TPA 非线性
    - FDTD: 2D TMz Yee 网格 + PML 吸收边界（Berenger 1994）
    - BER 评估: Q-factor 法 + OSNR→BER（ITU-T G.977）

Output（输出）:
    - 电路级 S 参数字典 SDict: {(port_out, port_in): complex ndarray}
    - MNA DC 结果 MNADCResult: {node_voltages, vsource_currents}
    - MNA 瞬态结果 MNATransientResult: {time, node_voltages, vsource_currents}
    - 群延迟数组 np.ndarray（秒）
    - 时域输出信号 np.ndarray
    - BER/Q-factor/OSNR 标量
    - 频域→时域脉冲响应 dict（IFFT 转换）

================================================================
学术诚信文献溯源（R02，≥5 篇，均经 WebSearch 验证可访问）
================================================================
1. Pflüger et al. 2021, "Simphony: A Python-based simulator and S-parameter
   library for photonic integrated circuits", IEEE CiSE 23(4):74-85,
   https://arxiv.org/abs/2009.05146
2. Filipsson 1978, "A new general computer algorithm for S-matrix calculation
   of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
3. Ho, Ruehli, Brennan 1974, "The Modified Nodal Approach to Network
   Analysis", IEEE ISCAS, https://ieeexplore.ieee.org/document/1084079
4. Mason 1956, "Feedback Theory: Further Properties of Signal Flow Graphs",
   Proc. IRE 44(7):920-926, https://ieeexplore.ieee.org/document/4052034
5. Yee 1966, "Numerical solution of initial boundary value problems involving
   Maxwell's equations in isotropic media", IEEE TAP AP-14(3):302-307,
   https://ieeexplore.ieee.org/document/1138693
6. Berenger 1994, "A perfectly matched layer for the absorption of
   electromagnetic waves", J. Comput. Phys. 114(2):185-200,
   https://doi.org/10.1006/jcph.1994.1159
7. Lowery et al. 1987, "Transmission-line laser model",
   IEE Proc. J 134(5):281-289,
   https://digital-library.theiet.org/doi/abs/10.1049/ip-j-1.1987.0062
8. ITU-T G.977, "Characteristics of optical fibre submarine cable systems",
   https://www.itu.int/rec/T-REC-G.977
9. Golub & Van Loan 2013, "Matrix Computations", 4th ed., §2.3,
   https://www.press.jhu.edu/books/title/10876/matrix-computations
10. Chrostowski & Hochberg 2015, "Silicon Photonics Design", Cambridge,
    https://www.cambridge.org/core/books/silicon-photonics-design/

================================================================
创新点（标注 *创新*）
================================================================
- *创新* 频域→时域一键转换 to_time_domain(): VPI 需用户手动切换频域/时域，
  本函数提供统一 API，将 S(λ) 经频率重采样后 IFFT 为 h(t)。
  底层逻辑: LTI 系统频域-时域对偶（Oppenheim & Willsky §3）。
  支持理论: 任意脉冲激励可由 h(t) 与输入信号卷积得到。
- *创新* 子网络增长分母趋零检测: 当 |1-S_AB·S_BA|<1e-15 时告警退出
  （R03 禁止 fall-back），区别于 SAX 静默返回。
  底层逻辑: 谐振陷波点数值奇异，必须告警让业务处理。

================================================================
合规声明
================================================================
- R02 学术诚信: 所有参数/公式可溯源，本 docstring 含 10 篇文献 URL
- R03 禁止 fall-back: 失败即 raise，无 except 块静默空语句 / return None
- R04 不参与 GPU: 纯 NumPy/SciPy，无 CuPy/CUDA/JAX 后端
- R05 无 TODO/FIXME/HACK 残留
- R13 不保留 v4 兼容: 去除 sax 必装依赖、jax 后端，简化为纯 numpy 单后端
- 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15
"""

from __future__ import annotations

from polaris_circuit.backend_selector import (
    COND_NUM_FG_THRESHOLD,
    COND_NUM_KLU_THRESHOLD,
    compute_condition_number,
)
from polaris_circuit.cascade import cascade_circuit
from polaris_circuit.mna_spice import (
    MNACircuit,
    MNADCResult,
    MNASolver,
    MNATransientResult,
    run_mna_spice,
)
from polaris_circuit.models import (
    RingParams,
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris_circuit.simulator import (
    SPEED_OF_LIGHT,
    CircuitSimulator,
    WavelengthRange,
    default_models,
    group_delay,
)
from polaris_circuit.subcircuit import Connector, Subcircuit, Term
from polaris_circuit.system_level import (
    BerEvaluator,
    HybridSimulator,
    OpticalLink,
    SignalFlowGraph,
    TLLMLaser,
    TimeDomainSimulator,
    simulate_system_level,
    to_time_domain,
)
from polaris_circuit.time_domain_circuit import (
    C0,
    EPS0,
    FDTDSimulator,
    MU0,
    NonlinearModel,
    PMLBoundary,
    TimeDomainCircuitSimulator,
    YeeGrid,
    run_time_domain_circuit,
)
from polaris_circuit.types import ModelFunc, SArray, SDict

__version__ = "5.0.0"

__all__ = [
    # 版本
    "__version__",
    # 类型
    "SDict",
    "SArray",
    "ModelFunc",
    # 物理常量
    "SPEED_OF_LIGHT",
    "C0",
    "EPS0",
    "MU0",
    # 基础器件模型
    "RingParams",
    "waveguide_s",
    "y_branch_s",
    "directional_coupler_s",
    "ring_resonator_s",
    "mmi_1x2_s",
    "mmi_2x2_s",
    "grating_coupler_s",
    "crossing_s",
    "terminator_s",
    "phase_shifter_s",
    # 级联与条件数
    "cascade_circuit",
    "compute_condition_number",
    "COND_NUM_FG_THRESHOLD",
    "COND_NUM_KLU_THRESHOLD",
    # 频域仿真器
    "CircuitSimulator",
    "WavelengthRange",
    "default_models",
    "group_delay",
    # 子电路构建（SPICE 风格）
    "Term",
    "Connector",
    "Subcircuit",
    # MNA SPICE
    "MNACircuit",
    "MNASolver",
    "MNADCResult",
    "MNATransientResult",
    "run_mna_spice",
    # 系统级仿真
    "SignalFlowGraph",
    "TLLMLaser",
    "TimeDomainSimulator",
    "HybridSimulator",
    "OpticalLink",
    "BerEvaluator",
    "to_time_domain",
    "simulate_system_level",
    # 时域电路仿真
    "YeeGrid",
    "PMLBoundary",
    "FDTDSimulator",
    "NonlinearModel",
    "TimeDomainCircuitSimulator",
    "run_time_domain_circuit",
]
