# 100 轮商业 Bug 排查任务清单

> 规范文档: [.trae/specs/100-round-commercial-bug-investigation/spec.md](file:///workspace/.trae/specs/100-round-commercial-bug-investigation/spec.md)

---

## 主任务：100 轮迭代排查

### 批次 1: R6-R10（sim/ 仿真核心）
- [ ] R6: sim/fdtd_jax_backend.py + sim/fdtd_gpu_engine.py（FDTD 物理常数/数值稳定性）
- [ ] R7: sim/fde/solver.py（FDE 本征模求解/边界条件）
- [ ] R8: sim/rcwa/solver_1d.py + solver_2d.py（RCWA 衍射效率/能量守恒）
- [ ] R9: sim/bpm/*.py + sim/eme/*.py（ BPM/EME 数值方法）
- [ ] R10: sim/ 杂项（cascade_backends/subnetwork_decomp/dag_scheduler 综合评审）

### 批次 2: R11-R15（quantum/ 量子光子）
- [ ] R11: sim/quantum_photonics.py（玻色采样/Boson Sampling 物理公式）
- [ ] R12: sim/quantum_klm.py（KLM CNOT/Hadamard/BS 物理实现）
- [ ] R13: quantum/quantum_circuit_distributed.py（BB84/QKD 协议/HOM 干涉）
- [ ] R14: sim/quantum_lossy.py（GBS/损失感知/量子优越性阈值）
- [ ] R15: quantum/ 全部综合评审

### 批次 3: R16-R20（router/ 布局布线）
- [ ] R16: router/curvy_optodesigner.py（曲线路径/损耗计算/拥塞）
- [ ] R17: router/jps_path_router.py（JPS 跳点搜索/性能）
- [ ] R18: router/all_angle_router.py（全角度布线/DRC 约束）
- [ ] R19: router/global_router.py + multilayer.py（全局布线/多层调度）
- [ ] R20: router/ 全部综合评审

### 批次 4: R21-R25（pdk/ & foundry/）
- [ ] R21: pdk/foundry_siepic.py（SiEPIC PDK 器件参数溯源）
- [ ] R22: pdk/foundry_imec.py + pdk/foundry_puk_expanded.py
- [ ] R23: pdk/si_220nm.py + pdk/si_340nm.py（SOI 平台参数一致性）
- [ ] R24: pdk/sin_220nm.py + pdk/inp*.py（SiN/InP 平台）
- [ ] R25: pdk/ + foundry/ 全部综合评审

### 批次 5: R26-R30（rl/ & ai/ 强化学习）
- [ ] R26: rl/ppo_agent.py（PPO 损失函数/熵/GAE 公式）
- [ ] R27: rl/gnn_ppo.py（GNN 图神经网络/消息传递）
- [ ] R28: rl/edge_gnn.py（边特征 GNN/损失感知）
- [ ] R29: ai/alpha_chip_agent.py（AlphaChip 分布式训练）
- [ ] R30: rl/ + ai/ 全部综合评审

### 批次 6: R31-R35（device/ 器件模型）
- [ ] R31: device/tcad_thermal_package.py（热传导 FDM/边界条件）
- [ ] R32: device/modulator.py（等离子体色散/Vπ 计算）
- [ ] R33: device/detector.py（探测器响应度/带宽）
- [ ] R34: device/waveguide.py（波导色散/有效折射率）
- [ ] R35: device/ 全部综合评审

### 批次 7: R36-R40（sim/cascade/ 级联仿真）
- [ ] R36: sim/cascade_backends.py（S 参数矩阵/Redheffer 星形积）
- [ ] R37: sim/subnetwork_decomp.py（Schur 补/块三对角求解）
- [ ] R38: sim/dag_scheduler.py（DAG 调度/并行化）
- [ ] R39: sim/cml_compiler_full.py（CML 编译器/模型加载）
- [ ] R40: sim/ 全部综合评审

### 批次 8: R41-R45（verification/ 验证）
- [ ] R41: verification/drc_curvilinear_18rules.py（DRC 几何运算）
- [ ] R42: verification/pex_extractor.py（边缘电容/PEX 公式）
- [ ] R43: verification/monte_carlo.py（MC 良率/空间相关性）
- [ ] R44: verification/drc_rules.py（DRC 规则完整性）
- [ ] R45: verification/ 全部综合评审

### 批次 9: R46-R50（inverse_design/ 逆向设计）
- [ ] R46: inverse/ddpm_inverse.py（DDPM 逆向设计/损失函数）
- [ ] R47: inverse/wgan_inverse.py（WGAN 梯度惩罚/收敛性）
- [ ] R48: inverse/topology_optimizer.py（密度法/拓扑优化）
- [ ] R49: inverse/adjoint_optimizer.py（伴随法/敏感度）
- [ ] R50: inverse_design/ 全部综合评审

### 批次 10: R51-R55（flow/ & pipeline/）
- [ ] R51: flow/stage_base.py（流程基类/异常传播）
- [ ] R52: flow/routing_flow.py（布线流程编排）
- [ ] R53: pipeline/layout_pipeline.py（布局流水线）
- [ ] R54: pipeline/routing_pipeline.py（布线流水线）
- [ ] R55: flow/ + pipeline/ 全部综合评审

### 批次 11: R56-R60（data/ & io/）
- [ ] R56: data/apollo_benchmark.py（Apollo 基准数据一致性）
- [ ] R57: data/gds_reader.py + data/layout_writer.py（GDS 读写）
- [ ] R58: io/file_io.py + io/jsonl_format.py（文件 I/O 原子性）
- [ ] R59: data/ 全部综合（PDK 数据一致性）
- [ ] R60: io/ + data/ 全部综合评审

### 批次 12: R61-R65（inverse/topology/）
- [ ] R61: inverse/topology/mesh_generation.py（网格生成）
- [ ] R62: inverse/topology/sensitivity_analysis.py（敏感度分析）
- [ ] R63: inverse/topology/manufacturability.py（制造约束）
- [ ] R64: inverse/topology/*.py 杂项
- [ ] R65: inverse/topology/ 全部综合评审

### 批次 13: R66-R70（visualizer/ & gui/）
- [ ] R66: visualizer/layout_visualizer.py（版图可视化）
- [ ] R67: visualizer/waveform_plotter.py（波形绘制）
- [ ] R68: gui/klayout_integration.py（KLayout 集成）
- [ ] R69: gui/*.py 杂项
- [ ] R70: visualizer/ + gui/ 全部综合评审

### 批次 14: R71-R75（system/ & monitor/）
- [ ] R71: system/job_scheduler.py（作业调度/并发安全）
- [ ] R72: system/resource_manager.py（资源管理/内存泄漏）
- [ ] R73: monitor/performance_monitor.py（性能监控）
- [ ] R74: system/ + monitor/ 杂项
- [ ] R75: system/ + monitor/ 全部综合评审

### 批次 15: R76-R80（tests/ 测试覆盖）
- [ ] R76: tests/ 覆盖率分析（找出未覆盖模块）
- [ ] R77: tests/ 边界条件测试（空输入/零除/溢出）
- [ ] R78: tests/ 回归测试完整性（每模块有对应测试）
- [ ] R79: tests/ 性能测试基准（大规模电路）
- [ ] R80: tests/ 全部综合评审

### 批次 16: R81-R85（docs/ 文档一致性）
- [ ] R81: docs/ API 文档与代码签名一致性
- [ ] R82: docs/ 示例代码可执行性
- [ ] R83: docs/ changelog 版本号一致性
- [ ] R84: docs/ README 与实际功能一致性
- [ ] R85: docs/ 全部综合评审

### 批次 17: R86-R90（benchmark/ 基准测试）
- [ ] R86: benchmark/ Apollo benchmark 参数核查
- [ ] R87: benchmark/ SiEPIC benchmark 参数核查
- [ ] R88: benchmark/ IMEC benchmark 参数核查
- [ ] R89: benchmark/ 基准测试用例可执行性
- [ ] R90: benchmark/ 全部综合评审

### 批次 18: R91-R95（misc/ 杂项）
- [ ] R91: logger/ 日志配置与级别正确性
- [ ] R92: config/ 配置加载与环境变量
- [ ] R93: __init__.py 导出完整性
- [ ] R94: 全项目 import 依赖分析
- [ ] R95: misc/ 全部综合评审

### 批次 19: R96-R100（综合评审）
- [ ] R96: 全项目 R03 fall-back 最终扫描
- [ ] R97: 全项目 R02 学术诚信最终核查
- [ ] R98: 全项目物理公式最终逐行核查
- [ ] R99: 全项目测试覆盖率最终达标
- [ ] R100: 商业交付评审 + 五年计划最终更新

---

## 辅助任务

### 环境配置
- [ ] 启动 600 秒进度汇报守护进程
- [ ] 确认 auto_commit 每 6 分钟运行
- [ ] 确认 keepalive 每 5 分钟 touch 防超时

### 文档维护
- [ ] 操作记录.md 每轮同步
- [ ] 学术诚信检查.md 每 5 轮同步
- [ ] 商业活动计划表-五年.md 每 10 轮同步

### 质量门禁
- [ ] pytest --cov 覆盖率 ≥ 90%
- [ ] radon cc 圈复杂度 ≤ 15
- [ ] AST 扫描无 R03 fall-back
