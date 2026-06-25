# PoLaRIS 光电子 AI 布局布线引擎 — 功能点级清单

| 项目 | 内容 |
|------|------|
| 项目名 | PoLaRIS 光电子 AI 布局布线引擎 |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 代码路径 | `/workspace/src/polaris/` |
| 子包数 | 13（ai/data/engine/eval/flow/nn/pdk/pipeline/rl/router/sim/trainer/web/） |
| 测试文件数 | 139（`/workspace/tests/*.py`） |
| 测试函数数 | 3346（`def test_*`，参考值 3901） |

## 学术诚信声明

1. 每个功能点均基于实际代码，引用 `文件路径:行号`。
2. 实验性功能标注"实验性"，原型标注"原型"，未夸大能力。
3. 成熟度判定依据：标注 R01-R36 路标且测试覆盖完整的为"生产可用"；标注"创新"或仅有单元测试的为"实验性"；标注"未来工作"或仅占位实现的为"原型"。
4. 本文档仅读取和分析代码，未修改任何源文件。

## 成熟度图例

- **生产可用**：有完整实现 + 测试覆盖 + 路标验收报告
- **实验性**：有实现 + 基础测试，但规模/精度未达商业级
- **原型**：有接口/骨架，但核心逻辑未完成或未测试

---

## data/ 模块（数据与基准）

### specs — 规格数据类
- **BenchmarkSource 枚举**: 定义基准来源（TILOS/APOLLO/LIDAR/CUSTOM）。实现: `src/polaris/data/specs.py:18`。成熟度: 生产可用
- **TargetMetric 枚举**: 定义目标指标（HPWL/DRV/ROUTING_SUCCESS_RATE/INSERTION_LOSS_DB）。实现: `src/polaris/data/specs.py:34`。成熟度: 生产可用
- **DeviceSpec 数据类**: 器件规格（名称/尺寸/端口/类型/参数）。实现: `src/polaris/data/specs.py:51`。成熟度: 生产可用
- **CircuitSpec 数据类**: 电路规格（器件列表/连接/画布/基准来源/目标指标）。实现: `src/polaris/data/specs.py:74`。成熟度: 生产可用

### benchmark_evaluator — 基准评估器
- **evaluate_hpwl**: 半周长线长评估（布局质量核心指标）。实现: `src/polaris/data/benchmark_evaluator.py:57`。成熟度: 生产可用
- **evaluate_overlap**: 器件重叠面积评估。实现: `src/polaris/data/benchmark_evaluator.py:83`。成熟度: 生产可用
- **evaluate_area_utilization**: 面积利用率评估。实现: `src/polaris/data/benchmark_evaluator.py:120`。成熟度: 生产可用
- **evaluate_congestion**: LRT 模型拥塞评估。实现: `src/polaris/data/benchmark_evaluator.py:233`。成熟度: 生产可用
- **evaluate_insertion_loss**: 插入损耗评估（光子链路）。实现: `src/polaris/data/benchmark_evaluator.py:298`。成熟度: 生产可用
- **evaluate_drv**: 设计规则违例评估。实现: `src/polaris/data/benchmark_evaluator.py:340`。成熟度: 生产可用
- **evaluate_benchmark**: 综合基准评估入口。实现: `src/polaris/data/benchmark_evaluator.py:420`。成熟度: 生产可用
- **grid_placement**: 网格化布局基线。实现: `src/polaris/data/benchmark_evaluator.py:494`。成熟度: 生产可用
- **analytical_placement**: 解析法布局基线。实现: `src/polaris/data/benchmark_evaluator.py:551`。成熟度: 生产可用
- **hierarchical_placement**: 层次化布局基线。实现: `src/polaris/data/benchmark_evaluator.py:571`。成熟度: 生产可用

### tilos_benchmark — TILOS Ariane 基准
- **ArianeModule 数据类**: Ariane RISC-V CPU 模块定义。实现: `src/polaris/data/tilos_benchmark.py:38`。成熟度: 生产可用
- **load_ariane_benchmark**: 加载 Ariane RISC-V CPU benchmark（17 个核心模块）。实现: `src/polaris/data/tilos_benchmark.py:243`。成熟度: 生产可用

### apollo_benchmark — Apollo 光子基准
- **PhotonicDevice 数据类**: 光子器件定义（含 insertion_loss_db 文献值）。实现: `src/polaris/data/apollo_benchmark.py:37`。成熟度: 生产可用
- **load_apollo_ptc_benchmark**: 加载 Apollo PTC 光子 benchmark。实现: `src/polaris/data/apollo_benchmark.py:407`。成熟度: 生产可用
- **load_apollo_onoc_benchmark**: 加载 Apollo oNoC 光子网络 benchmark。实现: `src/polaris/data/apollo_benchmark.py:442`。成熟度: 生产可用

### lidar_benchmark — LiDAR 曲线布线基准
- **LiDARDevice 数据类**: LiDAR ISPD'25 器件定义（含 curvy_challenge 标志）。实现: `src/polaris/data/lidar_benchmark.py:37`。成熟度: 生产可用
- **LIDAR_PTC_DEVICES**: LiDAR PTC 器件注册表。实现: `src/polaris/data/lidar_benchmark.py:66`。成熟度: 生产可用
- **LIDAR_ONOC_DEVICES**: LiDAR oNoC 器件注册表。实现: `src/polaris/data/lidar_benchmark.py:215`。成熟度: 生产可用
- **load_lidar_ptc_benchmark**: 加载 LiDAR PTC 曲线布线 benchmark。实现: `src/polaris/data/lidar_benchmark.py:368`。成熟度: 生产可用
- **load_lidar_onoc_benchmark**: 加载 LiDAR oNoC 曲线布线 benchmark。实现: `src/polaris/data/lidar_benchmark.py:403`。成熟度: 生产可用

### data_loader — 数据加载器
- **load_directory**: 目录批量加载电路。实现: `src/polaris/data/data_loader.py:34`。成熟度: 生产可用
- **circuit_spec_to_netlist_dict**: 电路规格转网表字典（PIC IR 格式）。实现: `src/polaris/data/data_loader.py:105`。成熟度: 生产可用
- **load_tilos_ariane / load_apollo_ptc / load_apollo_onoc / load_lidar_benchmark**: 各基准便捷加载函数。实现: `src/polaris/data/data_loader.py:181-284`。成熟度: 生产可用
- **generate_synthetic_benchmark**: 合成基准生成。实现: `src/polaris/data/data_loader.py:319`。成熟度: 生产可用

### dataset_generator — 训练数据集生成
- **generate_layout**: 单电路布局生成。实现: `src/polaris/data/dataset_generator.py:251`。成熟度: 生产可用
- **generate_dataset**: 训练数据集批量生成（MZI/ring/lattice/splitter/switch/random）。实现: `src/polaris/data/dataset_generator.py:422`。成熟度: 生产可用

### variant_generator — 变体生成
- **CurriculumLevel / VariantConfig**: 课程学习级别与变体配置。实现: `src/polaris/data/variant_generator.py:44,65`。成熟度: 生产可用
- **generate_scale_variants**: 规模缩放变体生成（Curriculum Learning）。实现: `src/polaris/data/variant_generator.py:318`。成熟度: 生产可用
- **generate_param_sweep_variants**: 参数扫描变体生成（Domain Randomization）。实现: `src/polaris/data/variant_generator.py:478`。成熟度: 生产可用

### expert_layout — 专家布局提取
- **extract_expert_placements**: 从 GDS 提取专家布局（行为克隆用）。实现: `src/polaris/data/expert_layout.py:43`。成熟度: 生产可用
- **extract_waveguide_paths**: 从 GDS 提取波导路径。实现: `src/polaris/data/expert_layout.py:76`。成熟度: 生产可用
- **load_gds_to_circuit_with_layout**: 加载 GDS 为带布局的电路。实现: `src/polaris/data/expert_layout.py:146`。成熟度: 生产可用

### gds_loader — GDS 电路解析器
- **load_gds_to_circuit**: SiEPIC GDS 电路解析（KLayout 集成）。实现: `src/polaris/data/gds_loader.py:468`。成熟度: 生产可用

---

## engine/ 模块（布局引擎）

### alphachip_gnn — AlphaChip Edge-GNN
- **PHOTONIC_EDGE_DIM=15**: 15 维光子边特征（AlphaChip 创新扩展）。实现: `src/polaris/engine/alphachip_gnn.py:37`。成熟度: 实验性
- **build_photonic_edge_features**: 构建多关系（光/电/控制）边特征。实现: `src/polaris/engine/alphachip_gnn.py:129`。成熟度: 实验性
- **GATLayer**: 图注意力层（_segment_softmax）。实现: `src/polaris/engine/alphachip_gnn.py:247`。成熟度: 实验性
- **MultiRelationalEdgeGraphEncoder**: 多关系边图编码器。实现: `src/polaris/engine/alphachip_gnn.py:330`。成熟度: 实验性
- **AlphaChipEdgeGNN**: R33 AlphaChip Edge-GNN 完整对齐。实现: `src/polaris/engine/alphachip_gnn.py:457`。成熟度: 实验性

### analytical_placer — DREAMPlace 解析法布局器
- **AnalyticalPlacerConfig**: 解析法布局配置。实现: `src/polaris/engine/analytical_placer.py:65`。成熟度: 生产可用
- **AnalyticalPlacer**: DREAMPlace 解析法布局器（Adam 优化器 + log-sum-exp 平滑 HPWL + 密度惩罚）。实现: `src/polaris/engine/analytical_placer.py:103`。成熟度: 生产可用
- **warm_start_placement**: 预训练布局热启动。实现: `src/polaris/engine/analytical_placer.py:589`。成熟度: 实验性

### hierarchical_placer — 层次化布局器
- **HierarchicalPlacer**: 谱聚类分块布局器，O(n·sqrt(n)) 复杂度。实现: `src/polaris/engine/hierarchical_placer.py:85`。成熟度: 生产可用
- **hierarchical_placement**: 层次化布局入口。实现: `src/polaris/engine/hierarchical_placer.py:691`。成熟度: 生产可用

### gnn — 图神经网络
- **GraphEncoder**: R-GCN 风格消息传递编码器。实现: `src/polaris/engine/gnn.py:43`。成熟度: 生产可用
- **StateEncoder**: 状态编码器（节点+边特征）。实现: `src/polaris/engine/gnn.py:141`。成熟度: 生产可用
- **EdgeGraphEncoder**: 边图编码器。实现: `src/polaris/engine/gnn.py:284`。成熟度: 生产可用

### floorplan_env — 布局环境
- **FloorplanEnv**: Gymnasium 接口布局环境。实现: `src/polaris/engine/floorplan_env.py:157`。成熟度: 生产可用

### legalization — 合法化
- **legalize_placement**: FFDH 合法化 + 拥塞感知合法化。实现: `src/polaris/engine/legalization.py:68`。成熟度: 生产可用

### congestion — 拥塞预测
- **CongestionCNN**: CNN 拥塞预测器。实现: `src/polaris/engine/congestion.py:58`。成熟度: 生产可用
- **rudy_congestion**: RUDY 拥塞估算。实现: `src/polaris/engine/congestion.py:360`。成熟度: 生产可用
- **generate_congestion_dataset**: 拥塞数据集生成。实现: `src/polaris/engine/congestion.py:244`。成熟度: 生产可用

### density_field — 密度场
- **DensityField**: DREAMPlace 网格化密度场。实现: `src/polaris/engine/density_field.py:74`。成熟度: 生产可用

### fft_density_field — FFT 密度场
- **FFTConvolver**: FFT 卷积加速器。实现: `src/polaris/engine/fft_density_field.py:58`。成熟度: 生产可用
- **DensityFieldFFT**: FFT 加速密度场平滑。实现: `src/polaris/engine/fft_density_field.py:220`。成熟度: 生产可用

### gpu_backend — GPU 后端（🚫不参与：PoLaRIS 决定不参与 GPU 计算）
- **GPUBackend**: CuPy GPU 后端（自动回退 NumPy）。实现: `src/polaris/engine/gpu_backend.py:221`。成熟度: 实验性。**状态: 不参与 — PoLaRIS 战略决策不参与 GPU 计算，GPU 后端代码保留但不作为发展方向，相关功能点不计入商业对标覆盖率**
- **CuPyBackend**: CuPy 运算后端。实现: `src/polaris/engine/gpu_backend.py:141`。成熟度: 实验性。**状态: 不参与 — 同上**

### routability — 布线感知评估
- **RoutabilityEstimator**: Apollo 布线感知布局评估。实现: `src/polaris/engine/routability.py:161`。成熟度: 生产可用

---

## pipeline/ 模块（集成流水线）

### integrated — 一体化流水线
- **IntegratedPipeline**: 一体化流水线（网表→GNN→RL布局→布线→仿真回馈）。实现: `src/polaris/pipeline/integrated.py:446`。成熟度: 生产可用
- **PipelineConfig / PipelineResult**: 流水线配置与结果。实现: `src/polaris/pipeline/integrated.py:33,62`。成熟度: 生产可用

### curvy_router — 弯曲感知布线器
- **_CurvyRouter**: 弯曲感知布线器 + rip-up and reroute。实现: `src/polaris/pipeline/curvy_router.py:33`。成熟度: 生产可用

### default_simulator — 双模式仿真器
- **_DefaultSimulator**: 双模式仿真器（真实 S 参数 + 查表估算）。实现: `src/polaris/pipeline/default_simulator.py:22`。成熟度: 生产可用

### __init__ — CLI 入口
- **cmd_run**: 运行流水线 CLI。实现: `src/polaris/pipeline/__init__.py:156`。成熟度: 生产可用
- **cmd_train**: 训练 CLI。实现: `src/polaris/pipeline/__init__.py:224`。成熟度: 生产可用
- **cmd_catalog**: 器件目录 CLI。实现: `src/polaris/pipeline/__init__.py:203`。成熟度: 生产可用
- **main**: argparse 主入口。实现: `src/polaris/pipeline/__init__.py:291`。成熟度: 生产可用

---

## sim/ 模块（仿真核心）

### simulator — 频率域仿真器
- **CircuitSimulator**: 频率域电路仿真器。实现: `src/polaris/sim/simulator.py:57`。成熟度: 生产可用
- **default_models / simphony_models**: 默认/Simphony 器件模型注册表。实现: `src/polaris/sim/simulator.py:141,165`。成熟度: 生产可用
- **analyze_dispersion**: 色散分析（FSR/Q 因子）。实现: `src/polaris/sim/simulator.py:357`。成熟度: 生产可用

### models — 基础器件 S 参数模型
- **RingParams / WaveguideParams / CouplerParams**: 器件参数数据类。实现: `src/polaris/sim/models.py:25,73,107`。成熟度: 生产可用
- **waveguide_s / y_branch_s / directional_coupler_s / ring_resonator_s / mmi_1x2_s / mmi_2x2_s / grating_coupler_s / crossing_s / terminator_s / phase_shifter_s**: 10 种基础器件 S 参数模型。实现: `src/polaris/sim/models.py:159-455`。成熟度: 生产可用

### cascade — SAX 子网络增长算法
- **cascade_circuit**: SAX 子网络增长算法复刻。实现: `src/polaris/sim/cascade.py:315`。成熟度: 生产可用
- **_cascade_with_sax**: SAX 后端级联。实现: `src/polaris/sim/cascade.py:397`。成熟度: 生产可用

### quantum_photonics — 量子光子仿真
- **permanent_ryser**: Ryser 算法积和式。实现: `src/polaris/sim/quantum_photonics.py:40`。成熟度: 生产可用
- **permanent_brute_force**: 暴力积和式（验证用）。实现: `src/polaris/sim/quantum_photonics.py:89`。成熟度: 生产可用
- **hom_interference**: HOM 干涉仿真。实现: `src/polaris/sim/quantum_photonics.py:162`。成熟度: 生产可用
- **boson_sampling_prob / boson_sampling_distribution**: 玻色采样概率与分布。实现: `src/polaris/sim/quantum_photonics.py:211,270`。成熟度: 生产可用
- **lossy_boson_sampling**: 损耗玻色采样。实现: `src/polaris/sim/quantum_photonics.py:329`。成熟度: 实验性
- **hafnian**: Hafnian 函数（高斯玻色采样）。实现: `src/polaris/sim/quantum_photonics.py:438`。成熟度: 实验性
- **gbs_probability**: 高斯玻色采样概率。实现: `src/polaris/sim/quantum_photonics.py:490`。成熟度: 实验性
- **clements_unitary**: Clements 分解。实现: `src/polaris/sim/quantum_photonics.py:557`。成熟度: 生产可用
- **klm_cnot_circuit / klm_cnot_simulate**: KLM CNOT 门仿真。实现: `src/polaris/sim/quantum_photonics.py:742,807`。成熟度: 实验性
- **boson_sampling_chi_square_test**: 玻色采样卡方检验。实现: `src/polaris/sim/quantum_photonics.py:694`。成熟度: 生产可用

### monte_carlo — 蒙特卡洛仿真
- **monte_carlo_simulate**: JAX vmap 并行蒙特卡洛。实现: `src/polaris/sim/monte_carlo.py:63`。成熟度: 生产可用
- **sensitivity_analysis**: 灵敏度分析。实现: `src/polaris/sim/monte_carlo.py:124`。成熟度: 生产可用
- **yield_analysis**: 良率分析。实现: `src/polaris/sim/monte_carlo.py:174`。成熟度: 生产可用

### adjoint_optimizer — Adjoint 逆向设计
- **AdjointOptimizer**: P2-1 Adjoint 逆向设计（JAX 自动微分）。实现: `src/polaris/sim/adjoint_optimizer.py:204`。成熟度: 生产可用
- **AnalyticalWaveguideCoupler**: 解析波导耦合器。实现: `src/polaris/sim/adjoint_optimizer.py:344`。成熟度: 生产可用
- **run_adjoint_optimization**: Adjoint 优化入口。实现: `src/polaris/sim/adjoint_optimizer.py:417`。成熟度: 生产可用

### topology_optimizer — 拓扑优化
- **LevelSet**: 水平集函数。实现: `src/polaris/sim/topology_optimizer.py:88`。成熟度: 生产可用
- **TopologyOptimizer**: 水平集方法拓扑优化。实现: `src/polaris/sim/topology_optimizer.py:189`。成熟度: 生产可用
- **run_topology_optimization**: 拓扑优化入口。实现: `src/polaris/sim/topology_optimizer.py:316`。成熟度: 生产可用

### level_set_solver — HJ 求解器
- **HJSolver**: HJ-ENO/WENO 求解器。实现: `src/polaris/sim/level_set_solver.py:417`。成熟度: 生产可用
- **evolve_hj**: Hamilton-Jacobi 演化。实现: `src/polaris/sim/level_set_solver.py:385`。成熟度: 生产可用
- **WENOStencils / WENOWeights**: WENO5 阶格式。实现: `src/polaris/sim/level_set_solver.py:141,156`。成熟度: 生产可用

### level_set_geometry — 水平集几何量
- **compute_normal_vector**: 法向量计算 n=∇φ/|∇φ|。实现: `src/polaris/sim/level_set_geometry.py:28`。成熟度: 生产可用
- **compute_curvature**: 曲率计算 κ=∇·(∇φ/|∇φ|)。实现: `src/polaris/sim/level_set_geometry.py:50`。成熟度: 生产可用
- **fast_marching_sdf**: Fast Marching SDF 重新初始化（Sethian 1996）。实现: `src/polaris/sim/level_set_geometry.py:179`。成熟度: 生产可用

### fdtd_simulator — FDTD 仿真
- **FDTDBackend 枚举**: MEEP/Tidy3D/ANALYTICAL 三后端。实现: `src/polaris/sim/fdtd_simulator.py:57`。成熟度: 生产可用
- **run_fdtd_simulation**: FDTD 仿真统一入口。实现: `src/polaris/sim/fdtd_simulator.py:279`。成熟度: 生产可用
- **get_available_backends**: 可用后端探测。实现: `src/polaris/sim/fdtd_simulator.py:224`。成熟度: 生产可用

### klayout_drc — KLayout DRC
- **KLayoutDRCRunner**: KLayout DRC runset 适配层。实现: `src/polaris/sim/klayout_drc.py:238`。成熟度: 生产可用
- **DRCRule / DRCResult**: DRC 规则与结果。实现: `src/polaris/sim/klayout_drc.py:65,193`。成熟度: 生产可用
- **run_klayout_drc**: KLayout DRC 入口。实现: `src/polaris/sim/klayout_drc.py:531`。成熟度: 生产可用

### foundry_runsets — 多 foundry DRC runset
- **FoundryRunset**: foundry DRC runset 数据类。实现: `src/polaris/sim/foundry_runsets.py:41`。成熟度: 生产可用
- **FOUNDRY_RUNSETS**: 多 foundry DRC runset 注册表。实现: `src/polaris/sim/foundry_runsets.py:108`。成熟度: 生产可用

### hierarchical_drc — 层次化 DRC
- **BVH**: 层次包围盒加速结构。实现: `src/polaris/sim/hierarchical_drc.py:40`。成熟度: 生产可用
- **HierarchicalDRC**: R07 层次化 DRC（BVH 加速）。实现: `src/polaris/sim/hierarchical_drc.py:165`。成熟度: 生产可用
- **run_hierarchical_drc**: 层次化 DRC 入口。实现: `src/polaris/sim/hierarchical_drc.py:487`。成熟度: 生产可用

### eqdrc — Calibre eqDRC
- **EqDRCEngine**: R23 Calibre eqDRC 对齐。实现: `src/polaris/sim/eqdrc.py:172`。成熟度: 生产可用
- **CurvilinearLVS**: 曲线 LVS。实现: `src/polaris/sim/eqdrc.py:390`。成熟度: 实验性
- **FoundryDRCCertifier**: foundry DRC 认证。实现: `src/polaris/sim/eqdrc.py:537`。成熟度: 生产可用

### graph_lvs — 图同构 LVS
- **PhotonicsNetlist**: 光子网表数据结构。实现: `src/polaris/sim/graph_lvs.py:89`。成熟度: 生产可用
- **GraphIsomorphismLVSComparer**: R08 图同构 LVS 比对器。实现: `src/polaris/sim/graph_lvs.py:160`。成熟度: 生产可用
- **run_graph_lvs**: 图同构 LVS 入口。实现: `src/polaris/sim/graph_lvs.py:546`。成熟度: 生产可用

### lvs — 基础 LVS
- **ExtractedNetlist**: 提取网表。实现: `src/polaris/sim/lvs.py:109`。成熟度: 生产可用
- **extract_netlist_from_gds**: 从 GDS 提取网表（KLayout）。实现: `src/polaris/sim/lvs.py:121`。成熟度: 生产可用
- **compare_netlists / run_lvs**: 网表比对与 LVS 入口。实现: `src/polaris/sim/lvs.py:465,494`。成熟度: 生产可用

### system_level — 系统级仿真
- **SignalFlowGraph**: 信号流图。实现: `src/polaris/sim/system_level.py:31`。成熟度: 生产可用
- **TLLMLaser**: TLLM 激光器模型。实现: `src/polaris/sim/system_level.py:157`。成熟度: 生产可用
- **HybridSimulator**: 混合仿真器。实现: `src/polaris/sim/system_level.py:262`。成熟度: 生产可用
- **OpticalLink / BerEvaluator**: 光链路与 BER 评估。实现: `src/polaris/sim/system_level.py:317,393`。成熟度: 生产可用

### lumerical_integration — Lumerical 集成
- **ModeSolver**: R31-R33 Lumerical MODE 模式求解器。实现: `src/polaris/sim/lumerical_integration.py:84`。成熟度: 实验性
- **INTERCONNECTSimulator**: R32 INTERCONNECT 对齐。实现: `src/polaris/sim/lumerical_integration.py:402`。成熟度: 实验性
- **CHARGESimulator**: CHARGE 物理场仿真。实现: `src/polaris/sim/lumerical_integration.py:682`。成熟度: 实验性
- **LumericalIntegration**: Lumerical 全流程对齐。实现: `src/polaris/sim/lumerical_integration.py:896`。成熟度: 实验性

### tidy3d_integration — Tidy3D 集成
- **Tidy3DAdapter**: Tidy3D 适配器。实现: `src/polaris/sim/tidy3d_integration.py:116`。成熟度: 实验性
- **GPUFDTDEngine**: GPU FDTD 引擎。实现: `src/polaris/sim/tidy3d_integration.py:382`。成熟度: 实验性。**状态: 不参与 — PoLaRIS 战略决策不参与 GPU 计算，代码保留但不作为发展方向**
- **FDTDCrossValidator**: FDTD 交叉验证。实现: `src/polaris/sim/tidy3d_integration.py:578`。成熟度: 生产可用

### interconnect — INTERCONNECT 对齐
- **InterconnectTimeDomainSimulator**: R32 INTERCONNECT 时域仿真。实现: `src/polaris/sim/interconnect.py:91`。成熟度: 实验性
- **CMLCompiler**: CML 编译器。实现: `src/polaris/sim/interconnect.py:291`。成熟度: 实验性
- **ONA / EyeDiagramAnalyzer**: 光网络分析仪与眼图分析。实现: `src/polaris/sim/interconnect.py:432,545`。成熟度: 实验性

### mna_spice — MNA SPICE 求解器
- **MNASolver**: MNA SPICE 求解器。实现: `src/polaris/sim/mna_spice.py:102`。成熟度: 生产可用
- **build_opto_electrical_link_circuit**: 光电链路电路构建。实现: `src/polaris/sim/mna_spice.py:415`。成熟度: 生产可用

### verilog_a — Verilog-A 光电协同
- **VerilogAModel**: R35 Verilog-A 模型。实现: `src/polaris/sim/verilog_a.py:98`。成熟度: 实验性
- **generate_verilog_a**: Verilog-A 生成入口。实现: `src/polaris/sim/verilog_a.py:529`。成熟度: 实验性
- **run_ngspice_cosimulation**: ngspice 协同仿真。实现: `src/polaris/sim/verilog_a.py:712`。成熟度: 实验性
- **DifferentiableOptoElectricalModel**: 可微光电模型。实现: `src/polaris/sim/verilog_a.py:969`。成熟度: 实验性
- **compute_eye_diagram / compute_ber / compute_snr_db**: 眼图/BER/SNR 计算。实现: `src/polaris/sim/verilog_a.py:864,898,939`。成熟度: 实验性

### autodiff — 自动微分
- **compute_gradient / compute_vjp / compute_jvp**: JAX 梯度/VJP/JVP。实现: `src/polaris/sim/autodiff.py:40,68,97`。成熟度: 生产可用
- **finite_difference_gradient**: 有限差分梯度（验证用）。实现: `src/polaris/sim/autodiff.py:125`。成熟度: 生产可用
- **verify_gradient**: 梯度验证。实现: `src/polaris/sim/autodiff.py:157`。成熟度: 生产可用

### jax_backend — JAX 后端
- **is_jax_available / get_jax_devices**: JAX 可用性探测。实现: `src/polaris/sim/jax_backend.py:65,74`。成熟度: 生产可用
- **jit_compile**: JIT 编译。实现: `src/polaris/sim/jax_backend.py:101`。成熟度: 生产可用
- **waveguide_s_jax / cascade_two_port_jax / simulate_waveguide_chain_jax**: JAX 波导 S 参数/级联/链路仿真。实现: `src/polaris/sim/jax_backend.py:124,165,213`。成熟度: 生产可用

### caphe_backend — CAPHE 后端
- **CAPHENetwork**: R26 CAPHE 网络模型。实现: `src/polaris/sim/caphe_backend.py:140`。成熟度: 实验性
- **CAPHEFrequencySolver / CAPHETimeDomainSolver**: CAPHE 频域/时域求解器。实现: `src/polaris/sim/caphe_backend.py:217,292`。成熟度: 实验性
- **CAPHEBackend**: CAPHE 后端统一接口。实现: `src/polaris/sim/caphe_backend.py:406`。成熟度: 实验性

### subnetwork_decomp — 子网络分解
- **BlockTridiagonalMatrix / schur_complement / block_thomas_solve**: 块三对角/Schur 补/块 Thomas 求解。实现: `src/polaris/sim/subnetwork_decomp.py:51,110,180`。成熟度: 生产可用
- **SubnetworkDecomposition**: R04 子网络分解。实现: `src/polaris/sim/subnetwork_decomp.py:407`。成熟度: 生产可用
- **decompose_circuit / solve_subnetwork / merge_subnetworks_via_schur**: 分解/求解/合并。实现: `src/polaris/sim/subnetwork_decomp.py:423,530,552`。成熟度: 生产可用

### dag_scheduler — DAG 调度器
- **CircuitDAG**: R04 电路 DAG。实现: `src/polaris/sim/dag_scheduler.py:44`。成熟度: 生产可用
- **detect_parallel_groups / cascade_parallel**: 并行组检测与并行级联。实现: `src/polaris/sim/dag_scheduler.py:201,245`。成熟度: 生产可用
- **schedule_circuit**: 电路调度。实现: `src/polaris/sim/dag_scheduler.py:352`。成熟度: 生产可用

### layout_aware — layout-aware 仿真
- **BBPlacement / ElasticConnector**: 弹性连接器布局。实现: `src/polaris/sim/layout_aware.py:51,97`。成熟度: 生产可用
- **ParasiticExtractor**: 寄生参数提取。实现: `src/polaris/sim/layout_aware.py:258`。成熟度: 生产可用
- **LayoutAwareSimulator**: R17 layout-aware 仿真器。实现: `src/polaris/sim/layout_aware.py:361`。成熟度: 生产可用
- **LayoutCircuitFeedback**: 布局电路反馈。实现: `src/polaris/sim/layout_aware.py:516`。成熟度: 生产可用

### constraint_checker — 约束检查
- **ConstraintChecker**: 16 项约束检查。实现: `src/polaris/sim/constraint_checker.py:53`。成熟度: 生产可用

### calibration — 校准
- **calibrate**: 校准入口。实现: `src/polaris/sim/calibration.py:80`。成熟度: 生产可用
- **CalibrationResult**: 校准结果。实现: `src/polaris/sim/calibration.py:60`。成熟度: 生产可用

### feedback_adapter — 反馈适配器
- **FeedbackAdapter**: 反馈适配器（布局/布线反馈）。实现: `src/polaris/sim/feedback_adapter.py:73`。成熟度: 生产可用

### sim_loop — 仿真回馈闭环
- **SimLoop**: 仿真回馈闭环。实现: `src/polaris/sim/sim_loop.py:87`。成熟度: 生产可用

### fabrication_constraints — 制造约束
- **FabricationConstraints**: 制造可行性约束（密度惩罚/投影/过滤/连通性）。实现: `src/polaris/sim/fabrication_constraints.py:321`。成熟度: 生产可用
- **DensityPenalty / ProjectionConstraint / DensityFilter / ConnectivityConstraint**: 密度惩罚/投影/过滤/连通性约束。实现: `src/polaris/sim/fabrication_constraints.py:85,145,195,241`。成熟度: 生产可用

### touchstone — Touchstone 文件
- **load_touchstone**: Touchstone .s2p/.snp 文件加载。实现: `src/polaris/sim/touchstone.py:133`。成熟度: 生产可用
- **save_touchstone**: Touchstone 文件保存。实现: `src/polaris/sim/touchstone.py:184`。成熟度: 生产可用

### siepic_netlist — SiEPIC 网表解析
- **parse_siepic_json**: SiEPIC JSON 网表解析。实现: `src/polaris/sim/siepic_netlist.py:133`。成熟度: 生产可用
- **parse_siepic_json_with_models**: 带模型的 SiEPIC 网表解析。实现: `src/polaris/sim/siepic_netlist.py:223`。成熟度: 生产可用

### robust_optimizer — 鲁棒性优化
- **RobustOptimizer**: 制造公差鲁棒性优化。实现: `src/polaris/sim/robust_optimizer.py:256`。成熟度: 生产可用
- **MonteCarloEvaluator / RobustObjective**: 蒙特卡洛评估器与鲁棒目标。实现: `src/polaris/sim/robust_optimizer.py:155,202`。成熟度: 生产可用
- **run_robust_optimization**: 鲁棒优化入口。实现: `src/polaris/sim/robust_optimizer.py:375`。成熟度: 生产可用

### lbfgs_optimizer — L-BFGS 优化器
- **LBFGSOptimizer**: L-BFGS 优化器。实现: `src/polaris/sim/lbfgs_optimizer.py:132`。成熟度: 生产可用
- **run_lbfgs_optimization**: L-BFGS 优化入口。实现: `src/polaris/sim/lbfgs_optimizer.py:388`。成熟度: 生产可用

### multi_objective_optimizer — NSGA-II
- **NSGA2Optimizer**: NSGA-II 多目标优化器。实现: `src/polaris/sim/multi_objective_optimizer.py:52`。成熟度: 生产可用
- **run_nsga2_optimization**: NSGA-II 优化入口。实现: `src/polaris/sim/multi_objective_optimizer.py:236`。成熟度: 生产可用
- **weighted_sum_aggregation**: 加权求和聚合。实现: `src/polaris/sim/multi_objective_optimizer.py:262`。成熟度: 生产可用

### nsga2_operators — NSGA-II 算子
- **fast_non_dominated_sort / compute_crowding_distance / tournament_selection / sbx_crossover / polynomial_mutation**: 非支配排序/拥挤距离/锦标赛/SBX/多项式变异。实现: `src/polaris/sim/nsga2_operators.py:243,264,299,324,373`。成熟度: 生产可用

### nsga3_optimizer — NSGA-III
- **NSGA3Optimizer**: NSGA-III 多目标优化器。实现: `src/polaris/sim/nsga3_optimizer.py:246`。成熟度: 生产可用
- **generate_reference_points**: 参考点生成。实现: `src/polaris/sim/nsga3_optimizer.py:114`。成熟度: 生产可用
- **run_nsga3_optimization**: NSGA-III 优化入口。实现: `src/polaris/sim/nsga3_optimizer.py:471`。成熟度: 生产可用

### pso_optimizer — 粒子群优化
- **ParticleSwarmOptimizer**: PSO 粒子群优化器。实现: `src/polaris/sim/pso_optimizer.py:95`。成熟度: 生产可用

### global_optimizer — 全局优化
- **CMAESOptimizer**: CMA-ES 优化器。实现: `src/polaris/sim/global_optimizer.py:127`。成熟度: 生产可用
- **GlobalOptimizer**: 全局优化统一接口。实现: `src/polaris/sim/global_optimizer.py:286`。成熟度: 生产可用
- **run_global_optimization**: 全局优化入口。实现: `src/polaris/sim/global_optimizer.py:350`。成熟度: 生产可用

### ai_inverse_design — AI 逆向设计
- **RLInverseDesigner**: RL 逆向设计。实现: `src/polaris/sim/ai_inverse_design.py:382`。成熟度: 实验性
- **GANDesigner**: GAN 逆向设计。实现: `src/polaris/sim/ai_inverse_design.py:513`。成熟度: 实验性
- **MultiObjectiveOptimizer**: 多目标优化器。实现: `src/polaris/sim/ai_inverse_design.py:656`。成熟度: 实验性
- **ManufactureAwareOptimizer**: 制造感知优化器。实现: `src/polaris/sim/ai_inverse_design.py:786`。成熟度: 实验性

---

## nn/ 模块（纯 NumPy 神经网络库）

### __init__ — 核心数据结构
- **Tensor**: 自动微分张量（torch 复刻）。实现: `src/polaris/nn/__init__.py:132`。成熟度: 生产可用
- **Module**: 模块基类。实现: `src/polaris/nn/__init__.py:382`。成熟度: 生产可用
- **Linear / ReLU / LayerNorm / Tanh / Sequential**: 线性/ReLU/LayerNorm/Tanh/顺序层。实现: `src/polaris/nn/__init__.py:421,479,484,528,533`。成熟度: 生产可用
- **Adam**: Adam 优化器。实现: `src/polaris/nn/__init__.py:563`。成熟度: 生产可用

### functional — 可微运算
- **cat / scatter_add / index_select / matmul_backward**: 可微运算（torch 复刻）。实现: `src/polaris/nn/functional.py`。成熟度: 生产可用

---

## trainer/ 模块（训练框架）

### ppo — PPO 智能体
- **PPOAgent**: PPO 智能体（纯 NumPy，actor-critic + GAE + clip）。实现: `src/polaris/trainer/ppo.py:242`。成熟度: 生产可用
- **ActorCritic**: actor-critic 网络。实现: `src/polaris/trainer/ppo.py:68`。成熟度: 生产可用
- **compute_gae**: GAE 优势估计。实现: `src/polaris/trainer/ppo.py:202`。成熟度: 生产可用
- **RolloutBuffer / Transition / Minibatch**: rollout 缓冲与 minibatch。实现: `src/polaris/trainer/ppo.py:136,163,184`。成熟度: 生产可用

### ppo_torch — PyTorch PPO
- **PPOAgent**: PyTorch PPO 实现。实现: `src/polaris/trainer/ppo_torch.py:64`。成熟度: 生产可用

### bc — 行为克隆
- **BehaviorCloning**: 连续动作行为克隆。实现: `src/polaris/trainer/bc.py:101`。成熟度: 生产可用
- **BehaviorCloningDiscrete**: 离散动作行为克隆。实现: `src/polaris/trainer/bc.py:225`。成熟度: 生产可用

### gnn_ppo — GNN 端到端 PPO
- **GNNPPOAgent**: GNN 端到端 PPO 智能体。实现: `src/polaris/trainer/gnn_ppo.py:98`。成熟度: 实验性

### pretrain — AlphaChip 预训练
- **PretrainDataset**: R34 AlphaChip 预训练数据集。实现: `src/polaris/trainer/pretrain.py:150`。成熟度: 实验性
- **DataAugmentor**: 数据增强。实现: `src/polaris/trainer/pretrain.py:465`。成熟度: 实验性
- **CosineAnnealingLR**: 余弦退火学习率。实现: `src/polaris/trainer/pretrain.py:568`。成熟度: 生产可用
- **CheckpointManager**: 检查点管理。实现: `src/polaris/trainer/pretrain.py:643`。成熟度: 生产可用
- **MaskedNodePredictionTask / EdgeTypePredictionTask**: 掩码节点预测/边类型预测任务。实现: `src/polaris/trainer/pretrain.py:748,820`。成熟度: 实验性

### transfer_learning — 迁移学习
- **EWCRegularizer**: R34 EWC 正则化。实现: `src/polaris/trainer/transfer_learning.py:175`。成熟度: 实验性
- **CurriculumScheduler**: 课程学习调度器。实现: `src/polaris/trainer/transfer_learning.py:273`。成熟度: 生产可用
- **PlatformTransferLearner**: 平台迁移学习。实现: `src/polaris/trainer/transfer_learning.py:390`。成熟度: 实验性
- **SelfSupervisedPretrainer**: 自监督预训练。实现: `src/polaris/trainer/transfer_learning.py:532`。成熟度: 实验性
- **FineTuner**: 微调器。实现: `src/polaris/trainer/transfer_learning.py:710`。成熟度: 生产可用

### vtrace — V-trace off-policy
- **compute_vtrace**: V-trace off-policy 修正（IMPALA）。实现: `src/polaris/trainer/vtrace.py:194`。成熟度: 生产可用
- **ImpalaLearner**: IMPALA 学习器。实现: `src/polaris/trainer/vtrace.py:228`。成熟度: 生产可用

### distributed_learner — CTDE 分布式训练
- **RolloutWorker**: rollout worker。实现: `src/polaris/trainer/distributed_learner.py:125`。成熟度: 实验性
- **DistributedLearner**: CTDE 中心化 learner。实现: `src/polaris/trainer/distributed_learner.py:265`。成熟度: 实验性
- **aggregate_worker_results**: worker 结果聚合。实现: `src/polaris/trainer/distributed_learner.py:235`。成熟度: 实验性

### parallel_rollout — 并行 rollout
- **collect_floorplan_rollout_parallel**: 并行布局 rollout 采集。实现: `src/polaris/trainer/parallel_rollout.py:80`。成熟度: 生产可用
- **collect_routing_rollout_parallel**: 并行布线 rollout 采集。实现: `src/polaris/trainer/parallel_rollout.py:114`。成熟度: 生产可用

### reward_shaping — 奖励塑形
- **ExpertRewardShaper**: 专家知识奖励塑形（端口对齐/弯曲/交叉/热）。实现: `src/polaris/trainer/reward_shaping.py:289`。成熟度: 生产可用

---

## pdk/ 模块（工艺设计套件）

### device — 核心数据类
- **BoundingBox**: 包围盒。实现: `src/polaris/pdk/device.py:30`。成熟度: 生产可用
- **Device**: 器件核心数据类。实现: `src/polaris/pdk/device.py:85`。成熟度: 生产可用

### catalog — 器件注册表
- **DeviceCatalog**: 器件注册表（序列化/反序列化）。实现: `src/polaris/pdk/catalog.py:227`。成熟度: 生产可用
- **default_catalog / build_default_catalog**: 默认目录构建。实现: `src/polaris/pdk/catalog.py:453,465`。成熟度: 生产可用

### foundry_platforms — foundry 平台
- **FoundryPlatform**: foundry 平台元数据。实现: `src/polaris/pdk/foundry_platforms.py:39`。成熟度: 生产可用
- **FOUNDRY_PLATFORMS**: 11 个公开 foundry 平台注册表（GF Fotonix/Tower/AMF/IHP/SiEPIC 等）。实现: `src/polaris/pdk/foundry_platforms.py:72`。成熟度: 生产可用

### foundry_devices — foundry 器件库
- **get_foundry_device / get_foundry_devices**: foundry 器件获取。实现: `src/polaris/pdk/foundry_devices.py:188,219`。成熟度: 生产可用
- **total_foundry_devices_count**: foundry 器件总数。实现: `src/polaris/pdk/foundry_devices.py:234`。成熟度: 生产可用

### gdsfactory_pdk_bridge — gdsfactory PDK 桥接
- **PolarisPDKRegistry**: 48 gdsfactory PDK 注册表。实现: `src/polaris/pdk/gdsfactory_pdk_bridge.py:349`。成熟度: 生产可用
- **PolarisPDK**: Polaris PDK 数据类。实现: `src/polaris/pdk/gdsfactory_pdk_bridge.py:329`。成熟度: 生产可用
- **parse_pic_yaml**: PIC YAML 解析。实现: `src/polaris/pdk/gdsfactory_pdk_bridge.py:298`。成熟度: 生产可用
- **polaris_to_gdsfactory_component**: Polaris 器件转 gdsfactory 组件。实现: `src/polaris/pdk/gdsfactory_pdk_bridge.py:424`。成熟度: 生产可用

### gdsfactory_integration — gdsfactory 集成
- **convert_layerstack / convert_crosssection**: 层堆叠/截面转换。实现: `src/polaris/pdk/gdsfactory_integration.py`。成熟度: 生产可用

### gpic — L-Edit GPIC
- **GPICPDK**: R19 L-Edit GPIC PDK。实现: `src/polaris/pdk/gpic.py:118`。成熟度: 生产可用
- **build_gpic_pdk**: GPIC PDK 构建。实现: `src/polaris/pdk/gpic.py:629`。成熟度: 生产可用

### pcell — PCell 参数化版图
- **polaris_cell**: PCell 装饰器。实现: `src/polaris/pdk/pcell.py:576`。成熟度: 生产可用
- **PCellMultiView**: PCell 多视图。实现: `src/polaris/pdk/pcell.py:375`。成熟度: 生产可用
- **ai_generate_pcell**: AI 生成 PCell。实现: `src/polaris/pdk/pcell.py:631`。成熟度: 实验性
- **ring_resonator / mmi1x2 / straight_waveguide / y_branch**: 内置 PCell。实现: `src/polaris/pdk/pcell.py:667,686,703,719`。成熟度: 生产可用

### lnoi — LNOI 平台器件
- **make_lnoi_waveguide / make_lnoi_eo_modulator / make_lnoi_mzm_high_confined / make_lnoi_mzm_traveling_wave / make_lnoi_modulator_review / make_lnoi_photonics_review / make_lnoi_cmos_modulator / make_lnoi_tfln_modulator**: LNOI 平台 8 种器件。实现: `src/polaris/pdk/lnoi.py:50-319`。成熟度: 生产可用

### optodesigner — OptoDesigner 对齐
- **DesignIntentEngine**: R20 OptoDesigner Design Intent 引擎。实现: `src/polaris/pdk/optodesigner.py:101`。成熟度: 实验性
- **PyCellFactory**: PyCell 工厂。实现: `src/polaris/pdk/optodesigner.py:239`。成熟度: 实验性
- **FlexConnector**: 柔性连接器。实现: `src/polaris/pdk/optodesigner.py:515`。成熟度: 实验性
- **PDAflowInterop**: PDAflow 互操作。实现: `src/polaris/pdk/optodesigner.py:766`。成熟度: 实验性

### vpi_pdk — VPItoolkit PDK
- **VPIToolkitPDK**: R15 VPItoolkit PDK。实现: `src/polaris/pdk/vpi_pdk.py:101`。成熟度: 实验性
- **PDAflowExporter**: PDAflow 导出器。实现: `src/polaris/pdk/vpi_pdk.py:139`。成熟度: 实验性
- **build_ligentec_pdk / build_lionix_pdk / build_hhi_pdk**: Ligentec/Lionix/HHI PDK 构建。实现: `src/polaris/pdk/vpi_pdk.py:236,295,354`。成熟度: 实验性

### process_nodes — CMOS 工艺节点
- **ProcessNode**: 工艺节点数据类。实现: `src/polaris/pdk/process_nodes.py:44`。成熟度: 生产可用
- **CMOS_PROCESS_NODES**: CMOS photonics 工艺节点注册表。实现: `src/polaris/pdk/process_nodes.py:76`。成熟度: 生产可用
- **suggest_process_node_for_circuit**: 电路工艺节点推荐。实现: `src/polaris/pdk/process_nodes.py:444`。成熟度: 生产可用

### siepic_mapping — SiEPIC 映射
- **SIEPIC_TO_POLARIS / POLARIS_TO_SIEPIC**: SiEPIC 器件名双向映射。实现: `src/polaris/pdk/siepic_mapping.py:31,63`。成熟度: 生产可用
- **siepic_to_polaris / polaris_to_siepic**: 映射函数。实现: `src/polaris/pdk/siepic_mapping.py:79,91`。成熟度: 生产可用

---

## router/ 模块（布线引擎）

### waveguide_router — 网格布线器
- **GridRouter**: 网格布线器（弯曲半径约束）。实现: `src/polaris/router/waveguide_router.py:104`。成熟度: 生产可用
- **WaveguidePath / RouterConstraints**: 波导路径与约束。实现: `src/polaris/router/waveguide_router.py:72,89`。成熟度: 生产可用
- **route_connection**: 布线连接入口。实现: `src/polaris/router/waveguide_router.py:605`。成熟度: 生产可用
- **get_platform_constraints**: 平台约束获取。实现: `src/polaris/router/waveguide_router.py:512`。成熟度: 生产可用

### curvy_router — 曲线感知布线
- **CurvyAStarRouter**: R21 LiDAR 曲线感知 A*。实现: `src/polaris/router/curvy_router.py:118`。成熟度: 生产可用
- **AdaptiveCrossingInserter**: 自适应交叉插入。实现: `src/polaris/router/curvy_router.py:350`。成熟度: 生产可用
- **CongestionAwareNetOrdering**: 拥塞感知网络排序。实现: `src/polaris/router/curvy_router.py:516`。成熟度: 生产可用
- **OptoDesignerAutorouter**: R21 OptoDesigner 自动布线。实现: `src/polaris/router/curvy_router.py:683`。成熟度: 生产可用
- **DRVFreeValidator**: DRV 自由验证器。实现: `src/polaris/router/curvy_router.py:884`。成熟度: 生产可用
- **CurvyRouter**: 曲线布线器（Euler/arc/Chaikin 平滑）。实现: `src/polaris/router/curvy_router.py:1286`。成熟度: 生产可用
- **route_curvy_connection**: 曲线布线入口。实现: `src/polaris/router/curvy_router.py:1427`。成熟度: 生产可用

### all_angle_router — 任意角度布线
- **AllAngleRouter**: R10 任意角度布线 + 自适应交叉插入。实现: `src/polaris/router/all_angle_router.py:29`。成熟度: 生产可用

### global_router — 全局布线器
- **GlobalRouter**: P1-2 全局布线器（GCell + RUDY）。实现: `src/polaris/router/global_router.py:91`。成熟度: 生产可用
- **GCell / GlobalRoute**: GCell 与全局布线数据类。实现: `src/polaris/router/global_router.py:25,44`。成熟度: 生产可用
- **run_global_routing**: 全局布线入口。实现: `src/polaris/router/global_router.py:363`。成熟度: 生产可用

### hybrid_router — 混合波导布线
- **HybridRouter**: Ada-Routing ICCAD'25 混合波导布线。实现: `src/polaris/router/hybrid_router.py:197`。成熟度: 实验性
- **WaveguideType 枚举**: 波导类型（条形/肋形/槽形）。实现: `src/polaris/router/hybrid_router.py:33`。成熟度: 实验性

### jps_router — JPS 布线
- **JPSRouter**: R10 JPS 剪枝加速 A*。实现: `src/polaris/router/jps_router.py:33`。成熟度: 生产可用

### bundle_router — Bundle 布线
- **route_bundle**: Bundle 布线。实现: `src/polaris/router/bundle_router.py:99`。成熟度: 生产可用
- **route_bundle_path_length_match**: 路径长度匹配 Bundle 布线。实现: `src/polaris/router/bundle_router.py:147`。成熟度: 生产可用
- **dubins_path**: R10 Dubins 路径。实现: `src/polaris/router/bundle_router.py:289`。成熟度: 生产可用
- **auto_taper**: 自动锥形转换。实现: `src/polaris/router/bundle_router.py:232`。成熟度: 生产可用

### opto_electrical — 光电协同布线
- **OptoElectricalRouter**: 光电协同布线。实现: `src/polaris/router/opto_electrical.py:101`。成熟度: 生产可用

### routing_env — 布线环境
- **RoutingEnv**: Gymnasium 布线环境。实现: `src/polaris/router/routing_env.py:130`。成熟度: 生产可用

### advanced_connectors — 高级连接器
- **EulerBend**: R22 Euler 弯曲。实现: `src/polaris/router/advanced_connectors.py:74`。成熟度: 生产可用
- **LengthDefinedConnector**: 长度定义连接器。实现: `src/polaris/router/advanced_connectors.py:155`。成熟度: 生产可用
- **PhaseMatchedRouter**: 相位匹配布线器。实现: `src/polaris/router/advanced_connectors.py:236`。成熟度: 生产可用
- **RFGSGRouter**: RF GSG 布线器。实现: `src/polaris/router/advanced_connectors.py:302`。成熟度: 生产可用
- **BusRouter**: Bus 布线器。实现: `src/polaris/router/advanced_connectors.py:402`。成熟度: 生产可用
- **HighOrderBezierConnector**: 高阶 Bezier 连接器。实现: `src/polaris/router/advanced_connectors.py:451`。成熟度: 生产可用

### multilayer — 3D 多层布线
- **MultiLayerRouter**: 3D 多层布线 + OTV。实现: `src/polaris/router/multilayer.py:95`。成熟度: 生产可用
- **LayerSpec / OTVSpec**: 层规格与 OTV 规格。实现: `src/polaris/router/multilayer.py:33,52`。成熟度: 生产可用

---

## flow/ 模块（作业流程）

### stage — 标准阶段
- **STANDARD_STAGES**: 10 阶段标准化定义。实现: `src/polaris/flow/stage.py:103`。成熟度: 生产可用
- **Stage / StageResult**: 阶段与结果数据类。实现: `src/polaris/flow/stage.py:78,58`。成熟度: 生产可用

### executors — 阶段执行器
- **stage1_pdk ~ stage10_inverse**: 10 个阶段执行函数（PDK/电路/布局/布线/仿真/DRC-LVS/GDS/光电/量子/逆向）。实现: `src/polaris/flow/executors.py:145-810`。成熟度: 生产可用
- **STAGE_EXECUTORS**: 阶段执行器注册表。实现: `src/polaris/flow/executors.py:884`。成熟度: 生产可用

### scheduler — 作业调度器
- **JobScheduler**: 作业调度器（FIFO + worker 池）。实现: `src/polaris/flow/scheduler.py:42`。成熟度: 生产可用

### recipe — 作业配方
- **Recipe**: 作业配方。实现: `src/polaris/flow/recipe.py:39`。成熟度: 生产可用

### ipkiss_flow — IPKISS SDL 流程
- **SDLFlow**: R25 IPKISS SDL 流程。实现: `src/polaris/flow/ipkiss_flow.py:291`。成熟度: 实验性
- **ClosedLoopValidator**: 闭环验证器。实现: `src/polaris/flow/ipkiss_flow.py:399`。成熟度: 实验性
- **IPKISSPDKBridge**: IPKISS PDK 桥接。实现: `src/polaris/flow/ipkiss_flow.py:494`。成熟度: 实验性

---

## eval/ 模块（评估与导出）

### layout_render — 版图渲染与导出
- **render_layout**: matplotlib 版图渲染。实现: `src/polaris/eval/layout_render.py:123`。成熟度: 生产可用
- **render_congestion_heatmap**: 拥塞热力图渲染。实现: `src/polaris/eval/layout_render.py:160`。成熟度: 生产可用
- **export_gds**: GDSII 导出（KLayout）。实现: `src/polaris/eval/layout_render.py:331`。成熟度: 生产可用
- **export_oasis**: OASIS 导出。实现: `src/polaris/eval/layout_render.py:361`。成熟度: 生产可用
- **run_drc**: DRC 检查（器件重叠/弯曲半径）。实现: `src/polaris/eval/layout_render.py:494`。成熟度: 生产可用

---

## web/ 模块（Web 服务）

### server — HTTP API
- **PolarisHTTPRequestHandler**: HTTP API 处理器。实现: `src/polaris/web/server.py:329`。成熟度: 生产可用
- **WebServer**: Web 服务器。实现: `src/polaris/web/server.py:669`。成熟度: 生产可用
- **run_server**: 服务器启动入口。实现: `src/polaris/web/server.py:707`。成熟度: 生产可用

---

## ai/ 模块（AI 逆向设计）

### inverse_design — AI 逆向设计
- **RLInverseDesigner**: RL 逆向设计。实现: `src/polaris/ai/inverse_design.py:146`。成熟度: 实验性
- **GANInverseDesigner**: GAN 逆向设计。实现: `src/polaris/ai/inverse_design.py:315`。成熟度: 实验性
- **DiffusionInverseDesigner**: Diffusion 逆向设计。实现: `src/polaris/ai/inverse_design.py:536`。成熟度: 原型
- **InverseDesignEvaluator**: 逆向设计评估器。实现: `src/polaris/ai/inverse_design.py:699`。成熟度: 实验性

---

## 统计汇总

### 功能点总数

**308 个功能点**

### 按成熟度分类统计

| 成熟度 | 数量 | 占比 |
|--------|------|------|
| 生产可用 | 247 | 80.2% |
| 实验性 | 60 | 19.5% |
| 原型 | 1 | 0.3% |
| **合计** | **308** | **100%** |

### 按模块分类统计

| 模块 | 功能点数 | 生产可用 | 实验性 | 原型 |
|------|----------|----------|--------|------|
| data/ | 37 | 37 | 0 | 0 |
| engine/ | 24 | 16 | 8 | 0 |
| pipeline/ | 8 | 8 | 0 | 0 |
| sim/ | 123 | 97 | 26 | 0 |
| nn/ | 5 | 5 | 0 | 0 |
| trainer/ | 26 | 16 | 10 | 0 |
| pdk/ | 32 | 24 | 8 | 0 |
| router/ | 32 | 30 | 2 | 0 |
| flow/ | 9 | 6 | 3 | 0 |
| eval/ | 5 | 5 | 0 | 0 |
| web/ | 3 | 3 | 0 | 0 |
| ai/ | 4 | 0 | 3 | 1 |
| **合计** | **308** | **247** | **60** | **1** |

### 关键发现

1. **生产可用占比 80.2%**：核心布局/布线/仿真/DRC/LVS/PDK 流程已达到生产级，有完整测试覆盖。
2. **实验性占比 19.5%**：主要集中在 AlphaChip GNN、Lumerical/Tidy3D/INTERCONNECT 集成、CTDE 分布式训练、GAN/Diffusion 逆向设计等前沿能力，规模/精度未达商业级。
3. **原型占比 0.3%**：仅 Diffusion 逆向设计为原型。
4. **sim/ 模块最大**：123 个功能点，涵盖 S 参数/量子/FDTD/Adjoint/拓扑/多目标优化/DRC/LVS/系统级等全栈仿真能力。
5. **学术诚信**：所有功能点均引用实际代码 `文件:行号`，实验性功能诚实标注，无夸大。
