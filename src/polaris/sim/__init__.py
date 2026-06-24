"""光子电路仿真模块（精确模型数据库与频率域仿真）。

目录结构：
    polaris/sim/
        __init__.py        — 包入口，统一导出
        types.py           — S 参数类型定义（SDict, ModelFunc）
        models.py          — 基础器件 S 参数模型（规则3复刻 SiPANN）
        touchstone.py      — Touchstone .s2p/.snp 文件加载/保存
        cascade.py         — S 参数级联器（子网络增长算法，规则3复刻 SAX）
        caphe_backend.py   — R26 CAPHE 电路仿真器对齐（节点抽象+频域消去+时域ODE）
        simulator.py       — CircuitSimulator 电路级频率域仿真器
        device_models.py   — 51 器件到 S 参数模型映射
        constraint_checker.py — 约束检查器（16 项 DRC 规则）
        klayout_drc.py     — KLayout DRC runset 适配层（第2轮 P0-1）
        lvs.py             — LVS 基础实现（第3轮 P0-1）

集成方式（遵守 project_rules.md 规则 2/3）：
1. 直接集成 simphony + sax（规则 2）
2. SiPANN 安装失败 → 纯 numpy 100% 复刻（规则 3）
3. Touchstone .s2p/.snp 文件支持
4. KLayout DRC/LVS 引擎直接集成（规则 4.1，klayout 活跃维护）

来源:
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/
- SiPANN: https://sipann.readthedocs.io/
- Touchstone: https://en.wikipedia.org/wiki/Touchstone_file
- KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
"""

from polaris.sim.ai_inverse_design import (
    AdjointConfig,
    AdjointOptimizer,
    GANDesigner,
    ManufactureAwareOptimizer,
    MultiObjectiveOptimizer,
    RLDesignConfig,
    RLInverseDesigner,
)
from polaris.sim.caphe_backend import (
    CAPHEFrequencySolver,
    CAPHENetwork,
    CAPHENode,
)
from polaris.sim.caphe_time_domain import (
    CAPHEBackend,
    CAPHETimeDomainSolver,
)
from polaris.sim.cascade import cascade_circuit
from polaris.sim.tidy3d_integration import (
    FDTDCrossValidator,
    GPUFDTDConfig,
    GPUFDTDEngine,
    Tidy3DAdapter,
    Tidy3DAsyncRunner,
    Tidy3DConfig,
)
from polaris.sim.klayout_drc import (
    SIEPIC_EBEAM_DRC_RUNSET,
    DRCCheckType,
    DRCResult,
    DRCRule,
    KLayoutDRCRunner,
    run_klayout_drc,
)
from polaris.sim.lumerical_integration import (
    CHARGEConfig,
    CHARGESimulator,
    INTERCONNECTConfig,
    INTERCONNECTSimulator,
    LumericalIntegration,
    ModeConfig,
    ModeSolver,
)
from polaris.sim.lvs import (
    ExtractedNetlist,
    LVSMismatch,
    LVSMismatchType,
    LVSReport,
    circuit_spec_to_netlist,
    compare_netlists,
    extract_netlist_from_gds,
    run_lvs,
)
from polaris.sim.models import (
    CouplerParams,
    RingParams,
    WaveguideParams,
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    validate_wavelength,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.models_extended import (
    add_drop_ring_s,
    attenuator_s,
    bend_s,
    circulator_s,
    combiner_s,
    detector_s,
    half_ring_s,
    isolator_s,
    mirror_s,
    modulator_s,
    reflector_s,
    sellmeier_neff,
    splitter_s,
    taper_s,
    unitary_s,
)
from polaris.sim.monte_carlo import (
    MonteCarloResult,
    monte_carlo_simulate,
    sensitivity_analysis,
    waveguide_transmission_mc,
    yield_analysis,
)
from polaris.sim.netlist_adapter import (
    PolarNetlist,
    adapt_netlist,
    detect_format,
    validate_netlist,
)
from polaris.sim.quantum_photonics import (
    BosonSamplingResult,
    beamsplitter_unitary,
    boson_sampling_chi_square_test,
    boson_sampling_distribution,
    boson_sampling_prob,
    boson_sampling_sampler,
    clements_unitary,
    gbs_probability,
    hafnian,
    hom_dip_simulation,
    hom_interference,
    klm_cnot_circuit,
    klm_cnot_simulate,
    klm_cnot_success_probability,
    klm_hadamard_gate,
    lossy_boson_sampling,
    permanent_brute_force,
    permanent_ryser,
    quantum_advantage_threshold,
)
from polaris.sim.siepic_netlist import (
    SIEPIC_PORT_MAP,
    SIEPIC_TYPE_MAP,
    parse_siepic_json,
    parse_siepic_json_with_models,
)
from polaris.sim.simulator import (
    CircuitSimulator,
    WavelengthRange,
    analyze_dispersion,
    default_models,
    group_delay,
    simphony_models,
)
from polaris.sim.subcircuit import (
    Connector,
    Subcircuit,
    Term,
)
from polaris.sim.subnetwork_decomp import (
    BlockTridiagonalMatrix,
    SubnetworkCache,
    SubnetworkDecomposition,
    block_thomas_solve,
    build_block_tridiagonal_from_chain,
    cascade_adaptive,
    decompose_circuit,
    detect_block_tridiagonal,
    merge_subnetworks_via_schur,
    schur_complement,
    select_strategy,
    solve_subnetwork,
)
from polaris.sim.system_level import (
    BerEvaluator,
    HybridSimulator,
    OpticalLink,
    SignalFlowGraph,
    TimeDomainSimulator,
    TLLMLaser,
    to_time_domain,
)
from polaris.sim.tidy3d_integration import (
    Tidy3DAdapter,
    Tidy3DAsyncRunner,
    Tidy3DConfig,
)
from polaris.sim.time_domain_circuit import (
    FDTDSimulator,
    NonlinearModel,
    PMLBoundary,
    TimeDomainCircuitSimulator,
    YeeGrid,
)
from polaris.sim.touchstone import load_touchstone, save_touchstone
from polaris.sim.types import ModelFunc, SDict, asarray, get_backend, get_xp, set_backend
from polaris.sim.verilog_a import (
    DEFAULT_DETECTOR_RESPONSIVITY,
    DEFAULT_LOAD_RESISTANCE_OHM,
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_OPTICAL_TIMESTEP_S,
    DEFAULT_SPICE_TIMESTEP_S,
    DEFAULT_WAVELENGTH_UM,
    DEVICE_TYPE_DETECTOR,
    DEVICE_TYPE_DIRECTIONAL_COUPLER,
    DEVICE_TYPE_GRATING_COUPLER,
    DEVICE_TYPE_MMI_1X2,
    DEVICE_TYPE_MMI_2X2,
    DEVICE_TYPE_MODULATOR,
    DEVICE_TYPE_PHASE_SHIFTER,
    DEVICE_TYPE_RING,
    DEVICE_TYPE_WAVEGUIDE,
    DEVICE_TYPE_Y_BRANCH,
    SUPPORTED_DEVICE_TYPES,
    CoSimulationResult,
    DifferentiableOptoElectricalModel,
    PAM4Signal,
    SPICESimulationConfig,
    VerilogAModel,
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_detector_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_modulator_verilog_a,
    generate_pam4_signal,
    generate_ring_verilog_a,
    generate_spice_netlist,
    generate_verilog_a,
    generate_waveguide_verilog_a,
    optimize_opto_electrical_link,
    run_ngspice_cosimulation,
    save_verilog_a,
)

__all__ = [
    # 类型
    "SDict",
    "ModelFunc",
    # 双后端支持（R01 创新点）
    "set_backend",
    "get_backend",
    "get_xp",
    "asarray",
    # 参数集合（规则 4：降低函数参数个数）
    "RingParams",
    "WaveguideParams",
    "CouplerParams",
    "WavelengthRange",
    # R29 AI 驱动光子逆向设计
    "AdjointConfig",
    "AdjointOptimizer",
    "RLDesignConfig",
    "RLInverseDesigner",
    "GANDesigner",
    "MultiObjectiveOptimizer",
    "ManufactureAwareOptimizer",
    # R26 CAPHE 电路仿真后端
    "CAPHENode",
    "CAPHENetwork",
    "CAPHEFrequencySolver",
    "CAPHETimeDomainSolver",
    "CAPHEBackend",
    # R27+R28 Tidy3D 集成与 GPU FDTD 引擎
    "Tidy3DConfig",
    "Tidy3DAdapter",
    "Tidy3DAsyncRunner",
    "GPUFDTDConfig",
    "GPUFDTDEngine",
    "FDTDCrossValidator",
    # 基础器件 S 参数模型
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
    # R02 新增 SiEPIC 模型
    "half_ring_s",
    "add_drop_ring_s",
    "sellmeier_neff",
    # 扩展器件 S 参数模型（R01 步骤 7）
    "taper_s",
    "modulator_s",
    "detector_s",
    "splitter_s",
    "combiner_s",
    "attenuator_s",
    "circulator_s",
    "isolator_s",
    "mirror_s",
    "reflector_s",
    "unitary_s",
    "bend_s",
    # 参数 schema 验证（R01 创新点 2）
    "validate_wavelength",
    # 双后端自动切换（R01 创新点 1）
    "compute_condition_number",
    "select_backend",
    "diagnose_stability",
    "StabilityReport",
    # 网表格式自动适配器（R01 创新点 3）
    "PolarNetlist",
    "adapt_netlist",
    "detect_format",
    "validate_netlist",
    # Touchstone 文件
    "load_touchstone",
    "save_touchstone",
    # 级联器
    "cascade_circuit",
    # R03 级联后端集合（KLU + Redheffer 星积 + Additive + Forward-only + auto）
    "cascade_klu",
    "cascade_auto",
    "cascade_additive",
    "cascade_forward_only",
    "redheffer_star",
    "build_circuit_matrix",
    "CircuitMatrix",
    # R04 子网络分解（块三对角 + Schur 补 + 自适应策略 + 增量缓存）
    "BlockTridiagonalMatrix",
    "SubnetworkDecomposition",
    "SubnetworkCache",
    "schur_complement",
    "block_thomas_solve",
    "detect_block_tridiagonal",
    "build_block_tridiagonal_from_chain",
    "decompose_circuit",
    "solve_subnetwork",
    "merge_subnetworks_via_schur",
    "select_strategy",
    "cascade_adaptive",
    # R04 DAG 调度器（DAG 创建 + 拓扑排序 + 并行调度）
    "CircuitDAG",
    "create_dag",
    "flat_circuit",
    "detect_parallel_groups",
    "cascade_parallel",
    "schedule_circuit",
    # R05 JAX 加速集成（JIT + 自动微分 + 蒙特卡洛 + GPU）
    "JAXConfig",
    "is_jax_available",
    "get_jax_devices",
    "enable_float64",
    "jit_compile",
    "waveguide_s_jax",
    "cascade_two_port_jax",
    "simulate_waveguide_chain_jax",
    "benchmark_jit_vs_numpy",
    "set_jax_backend",
    "compute_gradient",
    "compute_vjp",
    "compute_jvp",
    "finite_difference_gradient",
    "verify_gradient",
    "waveguide_transmission_loss",
    "optimize_waveguide_lengths",
    "MonteCarloResult",
    "monte_carlo_simulate",
    "sensitivity_analysis",
    "yield_analysis",
    "waveguide_transmission_mc",
    # 仿真器
    "CircuitSimulator",
    "default_models",
    "simphony_models",
    # R02 群延迟和色散分析
    "group_delay",
    "analyze_dispersion",
    # R02 simphony 兼容 API
    "Term",
    "Connector",
    "Subcircuit",
    # R02 SiEPIC JSON 网表解析器
    "parse_siepic_json",
    "parse_siepic_json_with_models",
    "SIEPIC_TYPE_MAP",
    "SIEPIC_PORT_MAP",
    # KLayout DRC（第2轮 P0-1）
    "DRCCheckType",
    "DRCResult",
    "DRCRule",
    "KLayoutDRCRunner",
    "SIEPIC_EBEAM_DRC_RUNSET",
    "run_klayout_drc",
    # LVS（第3轮 P0-1）
    "ExtractedNetlist",
    "LVSMismatch",
    "LVSMismatchType",
    "LVSReport",
    "circuit_spec_to_netlist",
    "compare_netlists",
    "extract_netlist_from_gds",
    "run_lvs",
    # R31-R33 Ansys Lumerical 全流程对齐
    "ModeConfig",
    "ModeSolver",
    "INTERCONNECTConfig",
    "INTERCONNECTSimulator",
    "CHARGEConfig",
    "CHARGESimulator",
    "LumericalIntegration",
]
