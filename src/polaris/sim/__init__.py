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
        graph_lvs.py       — R08 图同构 LVS 比对器
        hierarchical_drc.py — R09 层次化 DRC 引擎
        layout_aware.py    — R17 layout-aware 仿真（BBPlacement/ElasticConnector/ParasiticExtractor）
        building_block.py  — R14 Building Block 抽象（ModelCard/TMatrix/s_to_t/t_to_s）
        eqdrc.py           — R23 Equation-driven DRC + CurvilinearLVS + FoundryDRCRunset
        cascade/           — R03 级联包（__init__.py 电路级 SAX + smatrix.py C03 Redheffer 矩阵级）
        rcwa/              — A01-RCWA 严格耦合波分析（1D/2D，Sprint 1 Task 1.2）

集成方式（遵守 project_rules.md 规则 2/3）：
1. 直接集成 simphony + sax（规则 2）
2. SiPANN 安装失败 → 纯 numpy 100% 复刻（规则 3）
3. Touchstone .s2p/.snp 文件支持
4. KLayout DRC/LVS 引擎直接集成（规则 4.1，klayout 活跃维护）
5. A01-RCWA + C03-Redheffer 矩阵级内核（Sprint 1，纯 NumPy/SciPy CPU）

来源:
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/
- SiPANN: https://sipann.readthedocs.io/
- Touchstone: https://en.wikipedia.org/wiki/Touchstone_file
- KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
- Moharam 1995 ETM: https://doi.org/10.1364/JOSAA.12.001077
- Li 1996 FFF: https://doi.org/10.1364/JOSAA.13.001870
- Victor Liu 2013 Redheffer: http://victorliu.info/pdfs/Scombine.pdf
"""

from polaris.sim.ai_inverse_design import (
    AdjointConfig,
    AdjointOptimizer,
    ManufactureAwareOptimizer,
    MultiObjectiveOptimizer,
    RLDesignConfig,
    RLInverseDesigner,
)
from polaris.sim.autodiff import (
    compute_gradient,
    compute_jvp,
    compute_vjp,
    finite_difference_gradient,
    optimize_waveguide_lengths,
    verify_gradient,
    waveguide_transmission_loss,
)
from polaris.sim.backend_selector import (
    StabilityReport,
    compute_condition_number,
    diagnose_stability,
    select_backend,
)
from polaris.sim.bpm import (
    BoundaryType,
    BpmConfig,
    BpmResult,
    BpmSolver,
    solve_bpm,
)
from polaris.sim.bpm import (
    Polarization as BpmPolarization,
)
from polaris.sim.building_block import (
    BBRegistry,
    BuildingBlock,
    ModelCard,
    TMatrix,
    VirtualExperiment,
    s_to_t,
    t_to_s,
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
from polaris.sim.cascade.smatrix import (
    BlockSMatrix,
    build_propagation_s,
    cascade_redheffer,
    redheffer_star_product,
)
from polaris.sim.cascade_backends import (
    CircuitMatrix,
    build_circuit_matrix,
    cascade_additive,
    cascade_auto,
    cascade_forward_only,
    cascade_klu,
    redheffer_star,
)
from polaris.sim.dag_scheduler import (
    CircuitDAG,
    cascade_parallel,
    create_dag,
    detect_parallel_groups,
    flat_circuit,
    schedule_circuit,
)
from polaris.sim.ddm import (
    DdmConfig,
    DdmResult,
    DdmSolver,
    GummelSolver,
    bernoulli,
    ddm_to_heat_joule,
    heat_to_ddm_mobility,
    sg_current_matrix,
    solve_ddm,
)
from polaris.sim.devs import (
    INFINITY,
    Accumulator,
    AtomicDEVS,
    Coordinator,
    CoupledDEVS,
    DEVSMessage,
    Generator,
    Queue,
    Simulator,
)
from polaris.sim.eme import (
    EmeCell,
    EmeConfig,
    EmeResult,
    EmeSolver,
    solve_eme,
)
from polaris.sim.eme import (
    build_interface_smatrix as eme_build_interface_smatrix,
)
from polaris.sim.eme import (
    build_propagation_smatrix as eme_build_propagation_smatrix,
)
from polaris.sim.eme import (
    overlap_matrix as eme_overlap_matrix,
)
from polaris.sim.eqdrc import (
    CurvilinearLVS,
    DRCReportGenerator,
    EqDRCEngine,
    EqDRCRule,
    EqDRCViolation,
    FoundryDRCCertifier,
    FoundryDRCRunset,
)
from polaris.sim.fde import (
    FdeSolver,
    FdeSolverConfig,
    Mode,
    solve_waveguide,
)
from polaris.sim.fdfd import (
    DipoleSource,
    FdfdResult,
    FdfdSolver,
    FdfdSolverConfig,
    GaussianBeamSource,
    ModeSource,
    PlaneWaveSource,
    PortSpec,
    SParameters,
    extract_s_parameters,
    solve_fdfd,
    verify_energy_conservation,
)
from polaris.sim.fdtd import (
    CpmlConfig,
    DftMonitor,
    DrudeParams,
    FdtdConfig,
    FdtdResult,
    FdtdSolver,
    GaussianPulse,
    SParamExtractor,
    TfsfBox,
    YeeGridFdtd,
    build_update_coefficients,
    courant_dt,
    solve_fdtd,
)
from polaris.sim.graph_lvs import (
    GraphIsomorphismLVSComparer,
    NetlistEdge,
    NetlistNode,
    PhotonicsLVSReport,
    PhotonicsNetlist,
    run_graph_lvs,
)
from polaris.sim.heat import (
    ADIABATIC,
    DN_DT_SI,
    K_SILICON,
    K_SIO2,
    SIGMA_SB,
    BcSpec,
    HeatConfig,
    HeatResult,
    HeatSolver,
    apply_boundary_conditions,
    ddm_to_heat,
    heat_to_fde,
    solve_heat,
)
from polaris.sim.heat import (
    BoundaryType as HeatBoundaryType,
)
from polaris.sim.hierarchical_drc import (
    HierarchicalDRC,
    run_hierarchical_drc,
)
from polaris.sim.jax_backend import (
    JAXConfig,
    benchmark_jit_vs_numpy,
    cascade_two_port_jax,
    enable_float64,
    get_jax_devices,
    is_jax_available,
    jit_compile,
    set_jax_backend,
    simulate_waveguide_chain_jax,
    waveguide_s_jax,
)
from polaris.sim.klayout_drc import (
    SIEPIC_EBEAM_DRC_RUNSET,
    DRCCheckType,
    DRCResult,
    DRCRule,
    KLayoutDRCRunner,
    run_klayout_drc,
)
from polaris.sim.layout_aware import (
    BBPlacement,
    ElasticConnector,
    LayoutAwareSimulator,
    LayoutCircuitFeedback,
    ParasiticExtractor,
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
from polaris.sim.rcwa import (
    FourierRule,
    GratingLayer1D,
    GratingLayer2D,
    LayerModes,
    Polarization,
    RcwaConfig1D,
    RcwaConfig2D,
    RcwaResult1D,
    RcwaResult2D,
    build_epsilon_inv_toeplitz_1d,
    build_epsilon_inv_toeplitz_2d,
    build_epsilon_toeplitz_1d,
    build_epsilon_toeplitz_2d,
    build_homogeneous_modes_1d,
    build_interface_smatrix,
    build_propagation_smatrix,
    fourier_coefficients_1d,
    fourier_coefficients_2d,
    select_rule,
    solve_layer_eigenmodes_1d,
    solve_rcwa_1d,
    solve_rcwa_2d,
    toeplitz_from_coefficients,
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
    FDTDCrossValidator,
    GPUFDTDConfig,
    GPUFDTDEngine,
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
from polaris.sim.fdtd_simulator import (
    FDTDBackend,
    FDTDConfig,
    FDTDResult,
    get_available_backends,
    is_meep_available,
    is_tidy3d_available,
    run_fdtd_simulation,
)
from polaris.sim.gdsfactory_cosim import (
    CircuitCoSimConfig,
    CircuitCoSimResult,
    CoSimConfig,
    CoSimResult,
    attach_metadata_to_component,
    build_s_matrix_from_sdict,
    build_sdict_from_s_matrix,
    cosim_to_gdsfactory_metadata,
    export_cosim_to_touchstone,
    export_circuit_cosim_to_touchstone,
    get_circuit_cosim_summary,
    get_cosim_summary,
    simulate_gdsfactory_circuit,
    simulate_gdsfactory_component,
)
from polaris.sim.types import ModelFunc, SDict, asarray, get_backend, get_xp, set_backend
from polaris.sim.varfdtd import (
    EffectiveIndexResult,
    VarFdtdConfig,
    VarFdtdResult,
    VarFdtdSolver,
    compute_effective_index,
    solve_varfdtd,
)
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
# ============================================================================
# R239-R300 良率分析与方差减少模块（C01+C02 子模块）
# ============================================================================
from polaris.sim.batch_simulation import (
    BatchScenarioResult,
    BatchSimulationResult,
    BatchYieldResult,
    batch_simulate,
    batch_yield_analysis,
)
from polaris.sim.importance_sampling import (
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
    cross_entropy_importance_sampling,
    importance_sampling_mean,
    importance_sampling_yield,
    rare_event_yield,
)
from polaris.sim.qmc_sampling import (
    QMCConvergenceComparison,
    QMCMonteCarloResult,
    QMCSampleResult,
    QMCSamplerType,
    compare_qmc_convergence,
    generate_qmc_samples,
    qmc_monte_carlo,
    transform_to_distribution,
)
from polaris.sim.stratified_sampling import (
    AllocationStrategy,
    StratifiedSamplingResult,
    compare_stratified_convergence,
    stratified_monte_carlo,
)
from polaris.sim.three_d_effects import (
    RoughnessScatteringLoss,
    SidewallAngleCorrection,
    correct_neff_for_sidewall_angle,
    mode_mismatch_loss_gaussian,
    sidewall_roughness_loss,
)
from polaris.sim.yield_optimization import (
    ToleranceAllocationResult,
    WorstCaseDistanceResult,
    YieldOptimizationResult,
    allocate_tolerance_by_sensitivity,
    compute_worst_case_distance,
    optimize_yield_via_nominal_shift,
)

__all__ = [
    # 类型
    "SDict",
    "ModelFunc",
    # A04-FDE 本征模求解器（Sprint 0 求解器栈底座，Yee 网格共享组件）
    "Mode",
    "FdeSolver",
    "FdeSolverConfig",
    "solve_waveguide",
    # A05-FDFD 频域有限差分（Sprint 1 频域全波路径核心，复用 FDE YeeGrid/ScPml）
    "FdfdResult",
    "FdfdSolver",
    "FdfdSolverConfig",
    "solve_fdfd",
    "DipoleSource",
    "GaussianBeamSource",
    "ModeSource",
    "PlaneWaveSource",
    "PortSpec",
    "SParameters",
    "extract_s_parameters",
    "verify_energy_conservation",
    # A09-FDTD 时域有限差分（Sprint 2 Task 2.3，Yee leapfrog + CPML + TFSF + ADE + DFT）
    "FdtdConfig",
    "FdtdResult",
    "FdtdSolver",
    "solve_fdtd",
    "YeeGridFdtd",
    "courant_dt",
    "build_update_coefficients",
    "CpmlConfig",
    "GaussianPulse",
    "TfsfBox",
    "DrudeParams",
    "DftMonitor",
    "SParamExtractor",
    # A08-DDM 漂移扩散（Sprint 2 Task 2.5，Scharfetter-Gummel + Gummel 迭代）
    "DdmConfig",
    "DdmResult",
    "DdmSolver",
    "solve_ddm",
    "GummelSolver",
    "bernoulli",
    "sg_current_matrix",
    "ddm_to_heat_joule",
    "heat_to_ddm_mobility",
    # A06-VarFDTD 有效折射率法（Sprint 2 Task 2.2，2.5D EIM + 2D Yee leapfrog）
    "VarFdtdConfig",
    "VarFdtdResult",
    "VarFdtdSolver",
    "solve_varfdtd",
    "compute_effective_index",
    "EffectiveIndexResult",
    # A07-HEAT 热传导求解器（Sprint 2 Task 2.4，傅里叶导热 + 5 类边界）
    "HeatConfig",
    "HeatResult",
    "HeatSolver",
    "solve_heat",
    "BcSpec",
    "HeatBoundaryType",
    "apply_boundary_conditions",
    "heat_to_fde",
    "ddm_to_heat",
    "ADIABATIC",
    "DN_DT_SI",
    "K_SILICON",
    "K_SIO2",
    "SIGMA_SB",
    # C03-Redheffer 矩阵级 S 矩阵级联（Sprint 1 Task 1.3，与字典级 redheffer_star 互补）
    "BlockSMatrix",
    "redheffer_star_product",
    "cascade_redheffer",
    "build_propagation_s",
    # A01-RCWA 严格耦合波分析（Sprint 1 Task 1.2，1D/2D 周期光栅）
    "FourierRule",
    "Polarization",
    "LayerModes",
    "GratingLayer1D",
    "RcwaConfig1D",
    "RcwaResult1D",
    "solve_rcwa_1d",
    "GratingLayer2D",
    "RcwaConfig2D",
    "RcwaResult2D",
    "solve_rcwa_2d",
    "select_rule",
    "fourier_coefficients_1d",
    "fourier_coefficients_2d",
    "toeplitz_from_coefficients",
    "build_epsilon_toeplitz_1d",
    "build_epsilon_inv_toeplitz_1d",
    "build_epsilon_toeplitz_2d",
    "build_epsilon_inv_toeplitz_2d",
    "solve_layer_eigenmodes_1d",
    "build_homogeneous_modes_1d",
    "build_interface_smatrix",
    "build_propagation_smatrix",
    # A02-EME 本征模展开（Sprint 1 Task 1.4，与 A04 FDE 共享模式数据结构）
    "EmeCell",
    "EmeConfig",
    "EmeResult",
    "EmeSolver",
    "solve_eme",
    "eme_overlap_matrix",
    "eme_build_interface_smatrix",
    "eme_build_propagation_smatrix",
    # A03-BPM 光束传播法（Sprint 2 Task 2.1，SVEA + Crank-Nicolson + ADI + TBC）
    "BpmConfig",
    "BpmResult",
    "BpmSolver",
    "solve_bpm",
    "BoundaryType",
    "BpmPolarization",
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
    "MultiObjectiveOptimizer",
    "ManufactureAwareOptimizer",
    # R14 Building Block 抽象（ModelCard/TMatrix/s_to_t/t_to_s）
    "BBRegistry",
    "BuildingBlock",
    "ModelCard",
    "TMatrix",
    "VirtualExperiment",
    "s_to_t",
    "t_to_s",
    # R17 layout-aware 仿真
    "BBPlacement",
    "ElasticConnector",
    "LayoutAwareSimulator",
    "LayoutCircuitFeedback",
    "ParasiticExtractor",
    # R23 Equation-driven DRC + CurvilinearLVS + FoundryDRCRunset
    "CurvilinearLVS",
    "DRCReportGenerator",
    "EqDRCEngine",
    "EqDRCRule",
    "EqDRCViolation",
    "FoundryDRCCertifier",
    "FoundryDRCRunset",
    # R08 图同构 LVS 比对器
    "GraphIsomorphismLVSComparer",
    "NetlistEdge",
    "NetlistNode",
    "PhotonicsLVSReport",
    "PhotonicsNetlist",
    "run_graph_lvs",
    # R09 层次化 DRC 引擎
    "HierarchicalDRC",
    "run_hierarchical_drc",
    # R26 CAPHE 电路仿真后端
    "CAPHENode",
    "CAPHENetwork",
    "CAPHEFrequencySolver",
    "CAPHETimeDomainSolver",
    "CAPHEBackend",
    # C01-MonteCarlo 统计公差分析（Sprint 3 Task 3.1）
    "MonteCarloResult",
    "monte_carlo_simulate",
    "sensitivity_analysis",
    "yield_analysis",
    "waveguide_transmission_mc",
    # C04-FDE 有限差分本征模（Sprint 3 Task 3.4）
    "FdeSolver",
    "FdeSolverConfig",
    "Mode",
    "solve_waveguide",
    # C05-DEVS 离散事件系统（Sprint 3 Task 3.5，Zeigler 经典 DEVS）
    "AtomicDEVS",
    "CoupledDEVS",
    "Simulator",
    "Coordinator",
    "DEVSMessage",
    "Generator",
    "Queue",
    "Accumulator",
    "INFINITY",
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
    # R03 级联后端集合（KLU + Redheffer 星积 + Additive + Forward-only + auto）
    "cascade_klu",
    "cascade_auto",
    "cascade_additive",
    "cascade_forward_only",
    "redheffer_star",
    "build_circuit_matrix",
    "CircuitMatrix",
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
    # 网表格式自动适配器（R01 创新点 3）
    "PolarNetlist",
    "adapt_netlist",
    "detect_format",
    "validate_netlist",
    # Touchstone 文件
    "load_touchstone",
    "save_touchstone",
    # FDTD 仿真统一接口（fdtd_simulator）
    "FDTDBackend",
    "FDTDConfig",
    "FDTDResult",
    "get_available_backends",
    "is_meep_available",
    "is_tidy3d_available",
    "run_fdtd_simulation",
    # R304 gdsfactory 联合仿真 - 组件级
    "CoSimConfig",
    "CoSimResult",
    "attach_metadata_to_component",
    "build_s_matrix_from_sdict",
    "cosim_to_gdsfactory_metadata",
    "export_cosim_to_touchstone",
    "get_cosim_summary",
    "simulate_gdsfactory_component",
    # R305 gdsfactory 联合仿真 - 电路级
    "CircuitCoSimConfig",
    "CircuitCoSimResult",
    "build_sdict_from_s_matrix",
    "export_circuit_cosim_to_touchstone",
    "get_circuit_cosim_summary",
    "simulate_gdsfactory_circuit",
    # 级联器
    "cascade_circuit",
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
    # 蒙特卡洛仿真
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
    # 时域电路仿真
    "FDTDSimulator",
    "NonlinearModel",
    "PMLBoundary",
    "TimeDomainCircuitSimulator",
    "YeeGrid",
    # 系统级仿真
    "BerEvaluator",
    "HybridSimulator",
    "OpticalLink",
    "SignalFlowGraph",
    "TimeDomainSimulator",
    "TLLMLaser",
    "to_time_domain",
    # R31-R33 Ansys Lumerical 全流程对齐
    "ModeConfig",
    "ModeSolver",
    "INTERCONNECTConfig",
    "INTERCONNECTSimulator",
    "CHARGEConfig",
    "CHARGESimulator",
    "LumericalIntegration",
    # ====================================================================
    # R241-R260 QMC 采样框架（LHS + Sobol + Halton + QMC 仿真 + 收敛对比）
    # ====================================================================
    "QMCConvergenceComparison",
    "QMCMonteCarloResult",
    "QMCSampleResult",
    "QMCSamplerType",
    "compare_qmc_convergence",
    "generate_qmc_samples",
    "qmc_monte_carlo",
    "transform_to_distribution",
    # ====================================================================
    # R261-R280 重要性采样稀有事件良率估计（5 种偏置 + CE 自适应）
    # ====================================================================
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
    "cross_entropy_importance_sampling",
    "importance_sampling_mean",
    "importance_sampling_yield",
    "rare_event_yield",
    # ====================================================================
    # R281-R290 分层采样方差减少（EQUAL/PROPORTIONAL/NEYMAN + 两阶段 Neyman）
    # ====================================================================
    "AllocationStrategy",
    "StratifiedSamplingResult",
    "compare_stratified_convergence",
    "stratified_monte_carlo",
    # ====================================================================
    # R291-R295 基于灵敏度良率优化（WCD + 容差分配 + 标称值优化）
    # ====================================================================
    "ToleranceAllocationResult",
    "WorstCaseDistanceResult",
    "YieldOptimizationResult",
    "allocate_tolerance_by_sensitivity",
    "compute_worst_case_distance",
    "optimize_yield_via_nominal_shift",
    # ====================================================================
    # R296-R298 批量仿真接口（多标称点 MC + 良率分析）
    # ====================================================================
    "BatchScenarioResult",
    "BatchSimulationResult",
    "BatchYieldResult",
    "batch_simulate",
    "batch_yield_analysis",
    # ====================================================================
    # R299 3D 效应修正（侧壁角 + 粗糙度散射 + 模式失配）
    # ====================================================================
    "RoughnessScatteringLoss",
    "SidewallAngleCorrection",
    "correct_neff_for_sidewall_angle",
    "mode_mismatch_loss_gaussian",
    "sidewall_roughness_loss",
]
