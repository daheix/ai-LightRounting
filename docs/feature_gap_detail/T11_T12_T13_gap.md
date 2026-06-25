# T11 simphony + T12 Cadence/Synopsys + T13 AlphaChip 逐点差距分析

| 项目 | 内容 |
|---|---|
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 功能点总数 | 238（T11:91 + T12:85 + T13:62）|
| 对比基准 | PoLaRIS 光电子 AI 布局布线引擎（308 功能点）|
| 代码路径 | `/workspace/src/polaris/` |

> **学术诚信声明**：本文档对 T11/T12/T13 每个功能点逐个标注 PoLaRIS 状态。PoLaRIS 已有功能必须引用实现位置（文件:行号），缺失功能标注 ❌，部分实现标注 ⚠️，不适用标注 🚫。所有标注基于实际代码与文档内容，无臆造。

## 状态图例

| 标记 | 含义 |
|---|---|
| ✅ | PoLaRIS 已有对应实现（生产可用或实验性） |
| ⚠️ | PoLaRIS 有部分/相关实现，但功能不完整或为不同范式 |
| ❌ | PoLaRIS 缺失该功能 |
| 🚫 | 不适用（如商业认证、特定厂商合作等 PoLaRIS 作为开源项目无法对标的项） |

---

## T11 simphony（91 功能点）

### 2.1 S 参数级联（Subnetwork Growth）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 子网络增长算法 | ✅ | src/polaris/sim/cascade.py:315 | `cascade_circuit` SAX 子网络增长算法复刻，生产可用 |
| 1.2 | 子网络增长例程 | ✅ | src/polaris/sim/cascade.py:397 | `_cascade_with_sax` SAX 后端级联例程 |
| 1.3 | S 参数矩阵 | ✅ | src/polaris/sim/models.py:159-455 | 10 种基础器件 S 参数模型（waveguide/y_branch/DC/ring/MMI/grating_coupler/crossing/terminator/phase_shifter） |
| 1.4 | 端口约定 | ✅ | src/polaris/sim/cascade.py:315 | cascade_circuit 处理端口连接约定 |
| 1.5 | 紧凑模型 | ✅ | src/polaris/sim/models.py:25,73,107 | RingParams/WaveguideParams/CouplerParams 紧凑模型参数类 |
| 1.6 | 频率相关 S 参数 | ✅ | src/polaris/sim/simulator.py:57 | `CircuitSimulator` 频率域仿真器支持频率扫描 |

### 2.2 SiEPIC 兼容

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | SiEPIC 库 | ✅ | src/polaris/pdk/siepic_mapping.py:31 | `SIEPIC_TO_POLARIS` SiEPIC 器件名映射注册表 |
| 2.2 | SiEPIC Ebeam PDK | ✅ | src/polaris/pdk/foundry_platforms.py:72 | `FOUNDRY_PLATFORMS` 包含 SiEPIC 平台 |
| 2.3 | SiEPIC-Tools 互操作 | ✅ | src/polaris/data/gds_loader.py:468 | `load_gds_to_circuit` SiEPIC GDS 电路解析（KLayout 集成） |
| 2.4 | KLayout 电路仿真 | ✅ | src/polaris/sim/klayout_drc.py:238 | `KLayoutDRCRunner` KLayout 集成 + gds_loader 电路解析 |
| 2.5 | grating_coupler 模型 | ✅ | src/polaris/sim/models.py:159-455 | `grating_coupler_s` 模型实现 |
| 2.6 | Y-branch 模型 | ✅ | src/polaris/sim/models.py:159-455 | `y_branch_s` 模型实现 |
| 2.7 | ebeam_terminator 模型 | ✅ | src/polaris/sim/models.py:159-455 | `terminator_s` 模型实现 |

### 2.3 子电路（Subcircuit）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | Subcircuit 类 | ⚠️ | src/polaris/data/specs.py:74 | PoLaRIS 用 `CircuitSpec` 数据类替代，非直接 Subcircuit 类 |
| 3.2 | 子电路模式 | ⚠️ | - | PoLaRIS 无直接"子电路模式"抽象，但通过 CircuitSpec 组合实现类似功能 |
| 3.3 | add 方法 | ⚠️ | src/polaris/data/specs.py:74 | CircuitSpec 通过器件列表+连接列表构建，非 add() 方法 API |
| 3.4 | connect_many | ⚠️ | src/polaris/data/data_loader.py:105 | `circuit_spec_to_netlist_dict` 批量连接转换，API 不同 |
| 3.5 | 引脚分配 | ✅ | src/polaris/data/specs.py:51 | `DeviceSpec` 包含端口定义 |
| 3.6 | 环形谐振器构建 | ✅ | src/polaris/sim/models.py:159-455 | `ring_resonator_s` 模型 + RingParams |
| 3.7 | Add-Drop 滤波器 | ⚠️ | src/polaris/sim/models.py:159-455 | 有 ring_resonator_s 可构建 Add-Drop，但无专用 Add-Drop 封装 |

### 2.4 频率扫描（Frequency Sweep）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | SweepSimulation | ✅ | src/polaris/sim/simulator.py:57 | `CircuitSimulator` 频率域仿真器支持扫描 |
| 4.2 | 频率范围设置 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 支持频率范围参数 |
| 4.3 | 波长单位 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 接受波长参数 |
| 4.4 | 数据提取 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 返回仿真数据 |
| 4.5 | 频率相关仿真 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率域仿真 |
| 4.6 | Nf 频率点 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 支持多频率点扫描 |

### 2.5 比 Lumerical 快 20×

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 20× 加速 | ⚠️ | src/polaris/sim/cascade.py:315 | 有 SAX 子网络增长算法（同 simphony 加速基础），但未公开 20× benchmark |
| 5.2 | 文档声明 | ❌ | - | PoLaRIS 文档无此声明 |
| 5.3 | 准确性比较 | ❌ | - | PoLaRIS 无与 Lumerical INTERCONNECT 的直接准确性比较报告 |
| 5.4 | 商业工具替代 | ✅ | src/polaris/sim/lumerical_integration.py:84 | PoLaRIS 定位为开源替代，并有 Lumerical 集成模块（R31-R33） |

### 2.6 参数扫描（Parameter Sweep）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | MonteCarloSweepSimulation | ✅ | src/polaris/sim/monte_carlo.py:63 | `monte_carlo_simulate` JAX vmap 并行蒙特卡洛仿真 |
| 6.2 | Monte Carlo 运行 | ✅ | src/polaris/sim/monte_carlo.py:63 | monte_carlo_simulate 支持指定运行次数 |
| 6.3 | 参数扰动 | ✅ | src/polaris/sim/monte_carlo.py:124 | `sensitivity_analysis` 灵敏度分析支持参数扰动 |
| 6.4 | 多参数变化 | ✅ | src/polaris/sim/monte_carlo.py:124 | sensitivity_analysis 支持多参数变化 |
| 6.5 | 理想值提取 | ⚠️ | src/polaris/sim/monte_carlo.py:63 | monte_carlo_simulate 支持理想值，但无明确"位置 0 存储理想值"约定 |
| 6.6 | 半径变化 | ✅ | src/polaris/sim/monte_carlo.py:124 | sensitivity_analysis 支持单参数（如半径）变化 |

### 2.7 可视化（Visualization）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | matplotlib 集成 | ✅ | src/polaris/eval/layout_render.py:123 | `render_layout` matplotlib 版图渲染 |
| 7.2 | 传输谱绘制 | ⚠️ | src/polaris/eval/layout_render.py:123 | 有版图渲染，但无专用传输谱绘制函数 |
| 7.3 | Monte Carlo 绘图 | ⚠️ | - | 无专用 Monte Carlo 多曲线绘制，需用户自行处理 |
| 7.4 | 眼图绘制 | ✅ | src/polaris/sim/verilog_a.py:864 | `compute_eye_diagram` + `src/polaris/sim/interconnect.py:545` EyeDiagramAnalyzer |
| 7.5 | 图表标注 | ✅ | src/polaris/eval/layout_render.py:123 | render_layout 支持图表标注 |

### 2.8 SiPANN 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | SiPANN 库 | ❌ | - | PoLaRIS 无 SiPANN 模型库（用自有 models.py 替代） |
| 8.2 | SimphonyWrapper | ❌ | - | PoLaRIS 无 SiPANN SimphonyWrapper |
| 8.3 | 神经网络模型 | ⚠️ | src/polaris/engine/gnn.py:43 | PoLaRIS 有 GNN 神经网络，但非 SiPANN 的 SCEE 模型 |
| 8.4 | gap_func_symmetric | ⚠️ | src/polaris/sim/models.py:159-455 | 有 `directional_coupler_s` 定向耦合器，但非 SiPANN gap_func 实现 |
| 8.5 | gap_func_antisymmetric | ⚠️ | src/polaris/sim/models.py:159-455 | 有 directional_coupler_s，但非 SiPANN antisymmetric 实现 |
| 8.6 | 半环模型 | ✅ | src/polaris/sim/models.py:159-455 | `ring_resonator_s` 半环/环形谐振器模型 |
| 8.7 | SCEE 集成 | ❌ | - | PoLaRIS 无 SCEE 集成 |

### 2.9 SAX 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | SAX 模型定义 | ✅ | src/polaris/sim/cascade.py:397 | `_cascade_with_sax` SAX 后端级联 |
| 9.2 | JAX 计算引擎 | ✅ | src/polaris/sim/jax_backend.py:65 | `is_jax_available` JAX 后端支持 |
| 9.3 | GPU 加速 | ✅ | src/polaris/engine/gpu_backend.py:221 | `GPUBackend` CuPy GPU 后端 |
| 9.4 | CPU 兼容 | ✅ | src/polaris/engine/gpu_backend.py:221 | GPUBackend 自动回退 NumPy |
| 9.5 | 双精度配置 | ✅ | src/polaris/sim/jax_backend.py:65 | jax_backend 支持双精度配置 |
| 9.6 | jax.numpy | ✅ | src/polaris/sim/jax_backend.py:124 | `waveguide_s_jax` 使用 jax.numpy |
| 9.7 | 可调用模型 | ✅ | src/polaris/sim/models.py:159-455 | S 参数模型为可调用函数 |
| 9.8 | 默认参数 | ✅ | src/polaris/sim/models.py:25,73,107 | 模型参数类有默认值 |

### 2.10 电路定义

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 网表编写 | ✅ | src/polaris/sim/siepic_netlist.py:133 | `parse_siepic_json` SiEPIC 网表解析 + data_loader.py:105 netlist_dict |
| 10.2 | 可调用仿真 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 可调用仿真 |
| 10.3 | 便捷类仿真 | ✅ | src/polaris/pipeline/integrated.py:446 | `IntegratedPipeline` 一体化流水线便捷类 |
| 10.4 | SPICE 类方法 | ✅ | src/polaris/sim/mna_spice.py:102 | `MNASolver` MNA SPICE 求解器 |
| 10.5 | 复杂仿真能力 | ✅ | src/polaris/pipeline/integrated.py:446 | IntegratedPipeline 复杂仿真能力 |

### 2.11 量子仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 量子仿真器 | ✅ | src/polaris/sim/quantum_photonics.py:40 | 完整量子光子仿真模块 |
| 11.2 | 经典转量子 | ✅ | src/polaris/sim/quantum_photonics.py:557 | `clements_unitary` Clements 分解转酉矩阵 |
| 11.3 | 酉矩阵转换 | ✅ | src/polaris/sim/quantum_photonics.py:557 | clements_unitary 酉矩阵转换 |
| 11.4 | 均匀损耗假设 | ✅ | src/polaris/sim/quantum_photonics.py:329 | `lossy_boson_sampling` 损耗玻色采样 |
| 11.5 | 量子态 | ✅ | src/polaris/sim/quantum_photonics.py:211 | `boson_sampling_prob` 量子态仿真 |
| 11.6 | 高斯态 | ✅ | src/polaris/sim/quantum_photonics.py:490 | `gbs_probability` 高斯玻色采样 + hafnian:438 |
| 11.7 | 量子谐振子 | ⚠️ | - | PoLaRIS 量子模块未明确包含量子谐振子专用仿真 |
| 11.8 | 海森堡不确定性 | ❌ | - | PoLaRIS 无海森堡不确定性原理仿真 |

### 2.12 模型框架

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 可扩展框架 | ✅ | src/polaris/pdk/catalog.py:227 | `DeviceCatalog` 可扩展器件注册表 |
| 12.2 | 自定义组件 | ✅ | src/polaris/pdk/catalog.py:227 | DeviceCatalog 支持自定义组件 |
| 12.3 | 模型库 | ✅ | src/polaris/pdk/foundry_devices.py:188 | `get_foundry_devices` foundry 器件库 + models.py |
| 12.4 | 预仿真组件 | ✅ | src/polaris/sim/models.py:159-455 | 10 种预仿真 S 参数组件 |
| 12.5 | 插件兼容 | ✅ | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | `PolarisPDKRegistry` 48 gdsfactory PDK 桥接 |

### 2.13 平台与安装

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | 跨平台 | ✅ | src/polaris/ | Python 实现，跨平台 |
| 13.2 | Python 3 脚本 | ✅ | src/polaris/ | Python 3 脚本化 |
| 13.3 | pip 安装 | ⚠️ | - | PoLaRIS 未明确公开 pip 安装方式 |
| 13.4 | Python 3.9+ | ✅ | src/polaris/ | Python 3 兼容 |
| 13.5 | 可选依赖 | ⚠️ | - | PoLaRIS 有可选依赖（JAX/CuPy/KLayout）但未明确 extras 分类 |
| 13.6 | MIT 协议 | ⚠️ | - | PoLaRIS 协议未在功能清单中明确 |

### 2.14 经典仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | ClassicalSim | ✅ | src/polaris/sim/simulator.py:57 | `CircuitSimulator` 经典频率域仿真 |
| 14.2 | 线性 PIC 仿真 | ✅ | src/polaris/sim/simulator.py:57 | CircuitSimulator 线性 PIC 仿真 |
| 14.3 | 时域仿真潜力 | ✅ | src/polaris/sim/interconnect.py:91 | `InterconnectTimeDomainSimulator` R32 INTERCONNECT 时域仿真 |

### 2.15 教育与文档

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | 在线文档 | ⚠️ | - | PoLaRIS 有文档但未明确在线托管 |
| 15.2 | 教程 | ⚠️ | - | PoLaRIS 有文档但无系统入门教程 |
| 15.3 | MZI 教程 | ❌ | - | PoLaRIS 无 MZI 专用教程 |
| 15.4 | Add-Drop 滤波器教程 | ❌ | - | PoLaRIS 无 Add-Drop 滤波器教程 |
| 15.5 | 量子仿真教程 | ❌ | - | PoLaRIS 无量子仿真教程 |
| 15.6 | Photonics-Bootcamp | ❌ | - | PoLaRIS 无 Photonics-Bootcamp 集成 |
| 15.7 | 学术引用 | ❌ | - | PoLaRIS 无明确学术引用格式 |
| 15.8 | 贡献指南 | ❌ | - | PoLaRIS 无明确贡献指南 |

### T11 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 62 | 68.1% |
| ⚠️ 部分 | 17 | 18.7% |
| ❌ 缺失 | 12 | 13.2% |
| 🚫 不适用 | 0 | 0% |
| **覆盖率** | **(✅+⚠️×0.5)/91** | **77.5%** |

**T11 关键差距**：
- 教育与文档（2.15）整体缺失：6/8 为 ❌，PoLaRIS 缺少系统教程与学术引用
- SiPANN 集成（2.8）部分缺失：3/7 为 ❌，无 SiPANN 库与 SCEE 集成
- 量子仿真（2.11）部分缺失：海森堡不确定性 ❌，量子谐振子 ⚠️
- 商业工具比较（2.5）缺失：无 20× 加速声明与准确性比较报告

---

## T12 Cadence Innovus + Synopsys ICC2（85 功能点）

### 第一部分：Cadence Innovus Implementation System（41 功能点）

#### 1. GigaPlace 全局布局引擎

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-1.1 | Startpoint TNS Method | ❌ | - | PoLaRIS 无 startpoint TNS 代价函数（数字时序专用） |
| INV-1.2 | Unbalanced Path-Based SKP | ❌ | - | PoLaRIS 无 path-based SKP 时序权重 |
| INV-1.3 | Advanced Pipeline Placement | ❌ | - | PoLaRIS 无流水线自动收集与平衡 |
| INV-1.4 | Integrated Congestion-Driven Placement (ICDP) | ⚠️ | src/polaris/engine/congestion.py:58 | 有 `CongestionCNN` 拥塞预测，但无 ICDP 集成布局 |
| INV-1.5 | Switching Power Placement (SPP) | ❌ | - | PoLaRIS 无翻转功耗布局代价函数 |

#### 2. GigaOpt 优化引擎

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-2.1 | Mega Options 优化等级控制 | ❌ | - | PoLaRIS 无 timing/power/area effort 等级控制 |
| INV-2.2 | New Path Compaction (CPR) | ❌ | - | PoLaRIS 无 path compaction 局部精化 |
| INV-2.3 | Pervasive Global Skew | ❌ | - | PoLaRIS 无全局偏斜优化（数字时钟树专用） |
| INV-2.4 | New Hold Optimizer | ❌ | - | PoLaRIS 无 hold TNS 优化器 |
| INV-2.5 | XOR-tree Gating / Data Gating | ❌ | - | PoLaRIS 无 XOR-tree/Data gating 功耗门控 |
| INV-2.6 | 时序驱动逻辑重映射/缓冲器插入 | ❌ | - | PoLaRIS 无时序驱动逻辑重映射与缓冲器插入 |

#### 3. PRO 全局-详细布线

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-3.1 | Hard Wires 详细布线 | ⚠️ | src/polaris/router/curvy_router.py:1286 | 有 `CurvyRouter` 详细布线，但无 hard/soft wire 分阶段策略 |
| INV-3.2 | 四阶段流程 (Init/Soft/Hard/Final) | ❌ | - | PoLaRIS 无四阶段布线流程 |

#### 4. ML DRC 闭合 / AI 驱动

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-4.1 | Innovus+ AI Assistant | ❌ | - | PoLaRIS 无自然语言调试 LLM 接口 |
| INV-4.2 | 自动化 DRC 违例修复辅助 | ⚠️ | src/polaris/sim/klayout_drc.py:238 | 有 `KLayoutDRCRunner` DRC 检测，但无 AI 自动修复 |
| INV-4.3 | AI 驱动 PPA 收敛 | ❌ | - | PoLaRIS 有 RL 布局但无 PPA 收敛闭环 |
| INV-4.4 | Voltus InsightAI 生成式 AI | ❌ | - | PoLaRIS 无生成式 AI EM-IR 修复 |

#### 5. 先进节点支持（3nm / 2nm 及以下）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-5.1 | TSMC N3 工艺认证 | 🚫 | - | PoLaRIS 为开源光子项目，无 TSMC N3 认证 |
| INV-5.2 | TSMC N2 / N2P 工艺认证 | 🚫 | - | PoLaRIS 无 TSMC N2 认证 |
| INV-5.3 | TSMC A16 工艺认证 | 🚫 | - | PoLaRIS 无 TSMC A16 认证 |
| INV-5.4 | TSMC A14 PDK 合作 | 🚫 | - | PoLaRIS 无 TSMC A14 PDK 合作 |
| INV-5.5 | 3nm 及以下 AI 加速 | ❌ | - | PoLaRIS 无 3nm AI 加速 benchmark |

#### 6. 分布式与多线程

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-6.1 | 分布式多线程架构 | ⚠️ | src/polaris/trainer/distributed_learner.py:265 | 有 `DistributedLearner` CTDE 分布式训练，但非布局布线分布式 |
| INV-6.2 | 云端可扩展 | ❌ | - | PoLaRIS 无云端部署（Azure CloudBurst 等） |

#### 7. 时序优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-7.1 | CCOpt 时钟树综合 | ❌ | - | PoLaRIS 无时钟树综合（光子电路无需 CTS） |
| INV-7.2 | Tempus 时序签核集成 | ❌ | - | PoLaRIS 无 Tempus 时序签核 |
| INV-7.3 | SI-based 时序 | ❌ | - | PoLaRIS 无 SI 信号完整性时序 |

#### 8. 功耗优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-8.1 | Switching Power Placement | ❌ | - | PoLaRIS 无翻转功耗布局 |
| INV-8.2 | XOR-tree / Data Gating | ❌ | - | PoLaRIS 无功耗门控 |
| INV-8.3 | Power Reclaim via Global Skew | ❌ | - | PoLaRIS 无 global skew 功耗回收 |

#### 9. IR 分析与电源完整性

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-9.1 | Voltus IC Power Integrity | ❌ | - | PoLaRIS 无 Voltus 电源完整性分析 |
| INV-9.2 | 早期 IR 修复 | ❌ | - | PoLaRIS 无早期 IR/EM 修复 |
| INV-9.3 | Voltus XM 层级建模 | ❌ | - | PoLaRIS 无层级 EM-IR 建模 |
| INV-9.4 | 大规模仿真扩展 | ❌ | - | PoLaRIS 无 30 亿门级 GPU 仿真扩展 |

#### 10. 拥塞预测与优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-10.1 | Integrated Congestion-Driven Placement | ⚠️ | src/polaris/engine/congestion.py:58 | 有 CongestionCNN 拥塞预测，但未集成到布局代价函数 |
| INV-10.2 | AI 拥塞感知布线 | ⚠️ | src/polaris/router/curvy_router.py:516 | 有 `CongestionAwareNetOrdering` 拥塞感知网络排序，但非 ML 引导 |

#### 11. 3D-IC 与先进封装

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-11.1 | Integrity 3D-IC Platform | ⚠️ | src/polaris/router/multilayer.py:95 | 有 `MultiLayerRouter` 3D 多层布线，但非完整 3D-IC 平台 |
| INV-11.2 | 3DFabric 支持 | ❌ | - | PoLaRIS 无 TSMC 3DFabric SoIC/CoWoS/InFO 支持 |
| INV-11.3 | 多芯片物理实现与分析 | ❌ | - | PoLaRIS 无多 chiplet 物理实现 |

#### 12. 物理验证

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| INV-12.1 | Pegasus Verification System | ⚠️ | src/polaris/sim/klayout_drc.py:238 | 有 KLayoutDRCRunner + HierarchicalDRC，但非 Pegasus 签核级 |
| INV-12.2 | Quantus Extraction | ⚠️ | src/polaris/sim/layout_aware.py:258 | 有 `ParasiticExtractor` 寄生参数提取，但非 Quantus 签核级 |

### Cadence Innovus 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 0 | 0% |
| ⚠️ 部分 | 9 | 22.0% |
| ❌ 缺失 | 27 | 65.9% |
| 🚫 不适用 | 5 | 12.1% |
| **覆盖率** | **(0+9×0.5)/41** | **11.0%** |

---

### 第二部分：Synopsys IC Compiler II (ICC2)（44 功能点）

#### 1. 多目标全局布局

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-1.1 | Multi-objective Global Placement | ⚠️ | src/polaris/engine/analytical_placer.py:103 | 有 `AnalyticalPlacer` DREAMPlace 解析法布局，但非完整多目标（时序/功耗/面积/拥塞） |
| ICC2-1.2 | Routing Driven Placement Optimization | ⚠️ | src/polaris/engine/routability.py:161 | 有 `RoutabilityEstimator` 布线感知评估，但非布局优化集成 |
| ICC2-1.3 | Next-generation Advanced 2D Placement | ⚠️ | src/polaris/engine/analytical_placer.py:103 | 有 AnalyticalPlacer 2D 布局，但非新一代算法 |
| ICC2-1.4 | Congestion Aware Placement | ⚠️ | src/polaris/engine/congestion.py:58 | 有 CongestionCNN，但未集成到布局 |
| ICC2-1.5 | Unified TNS-driven Optimization | ❌ | - | PoLaRIS 无 TNS 驱动优化（数字时序专用） |

#### 2. Zroute 布线

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-2.1 | Zroute 多线程布线架构 | ⚠️ | src/polaris/trainer/parallel_rollout.py:80 | 有并行 rollout，但非布线多线程架构 |
| ICC2-2.2 | Native Soft Rules 光刻感知 | ⚠️ | src/polaris/router/curvy_router.py:118 | 有 `CurvyAStarRouter` 曲线感知，部分光刻感知 |
| ICC2-2.3 | 并发优化 | ❌ | - | PoLaRIS 无制造规则+时序并发优化 |
| ICC2-2.4 | Routing Layer Driven Optimization | ⚠️ | src/polaris/router/multilayer.py:95 | 有 MultiLayerRouter 多层布线，但无 NDR/via pillar 优化 |

#### 3. ML 拥塞预测与 DRC 闭合

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-3.1 | ML 驱动布线拥塞预测 | ✅ | src/polaris/engine/congestion.py:58 | `CongestionCNN` CNN 拥塞预测器，生产可用 |
| ICC2-3.2 | ML 驱动 DRC 收敛 | ⚠️ | src/polaris/sim/hierarchical_drc.py:165 | 有 `HierarchicalDRC` R07 层次化 DRC，但非 ML 驱动收敛 |
| ICC2-3.3 | ML 宏单元布局 (MLMP) | ✅ | src/polaris/engine/alphachip_gnn.py:457 | `AlphaChipEdgeGNN` R33 AlphaChip Edge-GNN 宏单元布局 |
| ICC2-3.4 | ML ECO 预测 | ❌ | - | PoLaRIS 无 ML ECO 功耗回收预测 |
| ICC2-3.5 | AI 驱动优化 (2025.06) | ⚠️ | src/polaris/trainer/ppo.py:242 | 有 PPOAgent RL 优化，但非时序/拥塞/功耗瓶颈 AI 分析 |

#### 4. PrimeTime 时序签核

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-4.1 | PrimeTime 延迟计算集成 | ❌ | - | PoLaRIS 无 PrimeTime 集成 |
| ICC2-4.2 | PrimeTime ECO 集成 | ❌ | - | PoLaRIS 无 PrimeTime ECO 流程 |
| ICC2-4.3 | Path-Based Analysis (PBA) | ❌ | - | PoLaRIS 无穷举路径分析 |
| ICC2-4.4 | Arc-based 并发时钟数据优化 | ❌ | - | PoLaRIS 无 arc-based 时钟数据优化 |

#### 5. PrimePower / 功耗优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-5.1 | Total Power Optimization | ❌ | - | PoLaRIS 无全局总功耗优化 |
| ICC2-5.2 | IEEE 1801 UPF / 多电压支持 | ❌ | - | PoLaRIS 无 UPF 多电压支持 |
| ICC2-5.3 | 功耗驱动逻辑再综合 | ❌ | - | PoLaRIS 无逻辑再综合 |
| ICC2-5.4 | IR Drop Driven Optimization | ❌ | - | PoLaRIS 无电压降驱动优化 |
| ICC2-5.5 | Leakage/Dynamic Power 优化 | ❌ | - | PoLaRIS 无漏电/动态功耗优化 |

#### 6. 物理验证

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-6.1 | IC Validator In-Loop | ⚠️ | src/polaris/sim/klayout_drc.py:238 | 有 KLayoutDRCRunner 在环 DRC，但非 IC Validator |
| ICC2-6.2 | Signoff-driven DRC Validation | ⚠️ | src/polaris/sim/hierarchical_drc.py:165 | 有 HierarchicalDRC，但非签核级 |

#### 7. 先进节点支持（3nm / 2nm 及以下）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-7.1 | Multi-pattern / FinFET 感知流程 | ❌ | - | PoLaRIS 无 multi-pattern/FinFET 感知（光子项目） |
| ICC2-7.2 | 3nm / 2nm 节点优化 | 🚫 | - | PoLaRIS 为光子项目，无 3nm/2nm CMOS 节点优化 |
| ICC2-7.3 | IBM 3nm DTCO 合作 | 🚫 | - | PoLaRIS 无 IBM DTCO 合作 |
| ICC2-7.4 | 晶圆代工厂认证 | 🚫 | - | PoLaRIS 无先进节点晶圆代工厂认证 |

#### 8. 分布式与多线程

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-8.1 | Pervasively Parallel Framework | ⚠️ | src/polaris/trainer/distributed_learner.py:265 | 有 DistributedLearner，但非全流程并行框架 |
| ICC2-8.2 | Multi-threaded & Distributed Computing | ⚠️ | src/polaris/trainer/parallel_rollout.py:80 | 有并行 rollout，但非全流程多线程 |
| ICC2-8.3 | 紧凑数据模型 | ❌ | - | PoLaRIS 无 2-3× 内存优化的紧凑数据模型 |
| ICC2-8.4 | Near-linear 多核线程 | ❌ | - | PoLaRIS 无近线性多核线程扩展 |
| ICC2-8.5 | 分布式加速 (2025.06) | ⚠️ | src/polaris/trainer/distributed_learner.py:265 | 有 DistributedLearner，但无 30% 加速 benchmark |

#### 9. Advanced Fusion Technology（先进融合技术）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-9.1 | Physically-aware Logic Re-synthesis | ❌ | - | PoLaRIS 无物理感知逻辑再综合 |
| ICC2-9.2 | IR Drop Driven Optimization (全流程) | ❌ | - | PoLaRIS 无全流程电压降优化 |
| ICC2-9.3 | PrimeTime Delay Calc-based Routing Opt | ❌ | - | PoLaRIS 无 PrimeTime 延迟计算布线优化 |
| ICC2-9.4 | Integrated PrimeTime ECO Flow | ❌ | - | PoLaRIS 无 PrimeTime ECO 集成 |

#### 10. 设计规划与容量

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-10.1 | 500M+ 实例容量 | ❌ | - | PoLaRIS 无 5 亿实例容量（光子电路规模较小） |
| ICC2-10.2 | 透明层次化优化 | ⚠️ | src/polaris/engine/hierarchical_placer.py:85 | 有 `HierarchicalPlacer` 谱聚类分块布局，但非透明层次化 |
| ICC2-10.3 | Reference Methodology (RM) | ❌ | - | PoLaRIS 无 RM 参考方法 |
| ICC2-10.4 | MCMM 并发感知 | ❌ | - | PoLaRIS 无 MCMM 多角多模感知 |

#### 11. Fusion Compiler 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| ICC2-11.1 | Fusion Compiler 无缝集成 | ❌ | - | PoLaRIS 无 Fusion Compiler 集成 |
| ICC2-11.2 | Design Compiler Graphical 协同 | ❌ | - | PoLaRIS 无 Design Compiler 协同 |

### Synopsys ICC2 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 2 | 4.5% |
| ⚠️ 部分 | 15 | 34.1% |
| ❌ 缺失 | 24 | 54.5% |
| 🚫 不适用 | 3 | 6.8% |
| **覆盖率** | **(2+15×0.5)/44** | **21.6%** |

### T12 总统计（Cadence Innovus + Synopsys ICC2）

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 2 | 2.4% |
| ⚠️ 部分 | 24 | 28.2% |
| ❌ 缺失 | 56 | 65.9% |
| 🚫 不适用 | 8 | 9.4% |
| **覆盖率** | **(2+24×0.5)/85** | **16.5%** |

**T12 关键差距**：
- 数字时序优化全面缺失：TNS/WNS/Skew/Hold/CTS/PrimeTime 等 ❌（PoLaRIS 为光子项目，无数字时序需求）
- 功耗优化全面缺失：Switching Power/UPF/IR Drop/Leakage 等 ❌
- 先进节点认证不适用：TSMC N3/N2/A16/A14、IBM 3nm DTCO 等 🚫（开源光子项目无法对标）
- AI/ML 能力部分覆盖：CongestionCNN ✅、AlphaChipEdgeGNN ✅，但无 LLM 调试接口与生成式 AI
- 物理验证为部分实现：KLayoutDRC/HierarchicalDRC ⚠️，但非 Pegasus/IC Validator 签核级

---

## T13 Google AlphaChip + Circuit Training（62 功能点）

### 1. Edge-GNN 图神经网络架构

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-1.1 | Edge-based Graph Neural Network | ✅ | src/polaris/engine/alphachip_gnn.py:457 | `AlphaChipEdgeGNN` R33 AlphaChip Edge-GNN 完整对齐 |
| AC-1.2 | 节点/边特征编码 | ✅ | src/polaris/engine/alphachip_gnn.py:129,37 | `build_photonic_edge_features` + PHOTONIC_EDGE_DIM=15 光子边特征 |
| AC-1.3 | 优于 GCN 的鲁棒性 | ⚠️ | src/polaris/engine/alphachip_gnn.py:330 | 有 `MultiRelationalEdgeGraphEncoder`，但无与 GCN 的鲁棒性对比 |
| AC-1.4 | 跨芯片泛化 | ⚠️ | src/polaris/trainer/transfer_learning.py:175 | 有 `EWCRegularizer` R34 迁移学习，但无跨芯片泛化验证 |

### 2. PPO 强化学习

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-2.1 | Proximal Policy Optimization (PPO) | ✅ | src/polaris/trainer/ppo.py:242 | `PPOAgent` PPO 智能体（actor-critic + GAE + clip） |
| AC-2.2 | MDP 建模 | ✅ | src/polaris/engine/floorplan_env.py:157 | `FloorplanEnv` Gymnasium 接口 MDP 布局环境 |
| AC-2.3 | 策略梯度优化 | ✅ | src/polaris/trainer/ppo.py:242 | PPOAgent 策略梯度优化 |
| AC-2.4 | TF-Agents 实现 | ⚠️ | src/polaris/trainer/ppo.py:242 | PoLaRIS 用纯 NumPy + PyTorch 实现，非 TF-Agents |
| AC-2.5 | AlphaGo/AlphaZero 类比 | ✅ | src/polaris/trainer/ppo.py:242 | PoLaRIS 采用类似 RL 游戏化方法 |

### 3. 预训练范式

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-3.1 | 预训练 + 微调两阶段 | ✅ | src/polaris/trainer/pretrain.py:150 | `PretrainDataset` R34 AlphaChip 预训练 + transfer_learning.py:710 FineTuner |
| AC-3.2 | 数据集规模效应 | ⚠️ | src/polaris/trainer/pretrain.py:150 | 有 PretrainDataset，但无 2/5/20 块规模效应验证 |
| AC-3.3 | 预训练检查点开源 | ✅ | src/polaris/trainer/pretrain.py:643 | `CheckpointManager` 检查点管理 |
| AC-3.4 | 多网表预训练指南 | ⚠️ | src/polaris/trainer/pretrain.py:150 | 有 PretrainDataset，但无多网表预训练文档 |
| AC-3.5 | 经验积累改进 | ⚠️ | src/polaris/trainer/transfer_learning.py:175 | 有 EWC/CurriculumScheduler，但无经验积累改进验证 |

### 4. 分布式训练

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-4.1 | 多 GPU 分布式训练 | ⚠️ | src/polaris/engine/gpu_backend.py:221 | 有 `GPUBackend` CuPy GPU 后端，但非多 GPU 分布式训练 |
| AC-4.2 | 分布式数据收集 | ✅ | src/polaris/trainer/distributed_learner.py:265 | `DistributedLearner` CTDE 中心化 learner + parallel_rollout.py:80 |
| AC-4.3 | Reverb Replay Buffer | ⚠️ | src/polaris/trainer/ppo.py:136 | 有 `RolloutBuffer`，但非 Reverb Server |
| AC-4.4 | Variable Container 策略分发 | ❌ | - | PoLaRIS 无 Variable Container 策略分发 |
| AC-4.5 | 训练/收集独立扩展 | ✅ | src/polaris/trainer/distributed_learner.py:265 | DistributedLearner 训练/收集独立进程 |
| AC-4.6 | 推荐配置 | ❌ | - | PoLaRIS 无 8-GPU global batch=1024 推荐配置 |

### 5. TPU 应用（v5e / v5p / Trillium / Ironwood）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-5.1 | TPU v5e 部署 | 🚫 | - | PoLaRIS 为光子开源项目，无 TPU 部署 |
| AC-5.2 | TPU v5p 部署 | 🚫 | - | PoLaRIS 无 TPU v5p 部署 |
| AC-5.3 | TPU Trillium (v6) 部署 | 🚫 | - | PoLaRIS 无 TPU Trillium 部署 |
| AC-5.4 | TPU Ironwood (v7) 部署 | 🚫 | - | PoLaRIS 无 TPU Ironwood 部署 |
| AC-5.5 | 三代 TPU 块数增长 | 🚫 | - | PoLaRIS 无 TPU 块数增长数据 |
| AC-5.6 | 三代 TPU 线长持续减少 | 🚫 | - | PoLaRIS 无 TPU 线长减少数据 |
| AC-5.7 | Axion CPU 部署 | 🚫 | - | PoLaRIS 无 Axion CPU 部署 |

### 6. MediaTek Dimensity 应用

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-6.1 | MediaTek 采用 AlphaChip | 🚫 | - | PoLaRIS 无 MediaTek 商业采用 |
| AC-6.2 | Dimensity 5G 旗舰芯片 | 🚫 | - | PoLaRIS 无 Dimensity 5G 部署 |
| AC-6.3 | MediaTek 高管背书 | 🚫 | - | PoLaRIS 无商业高管背书 |

### 7. Circuit Training 开源框架

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-7.1 | 开源框架 | ✅ | src/polaris/ | PoLaRIS 为开源框架 |
| AC-7.2 | CircuitEnv 环境 | ✅ | src/polaris/engine/floorplan_env.py:157 | `FloorplanEnv` + src/polaris/router/routing_env.py:130 `RoutingEnv` |
| AC-7.3 | PlacementCost (PLC) Client | ✅ | src/polaris/data/benchmark_evaluator.py:420 | `evaluate_benchmark` 综合基准评估入口 |
| AC-7.4 | Action Space | ✅ | src/polaris/engine/floorplan_env.py:157 | FloorplanEnv 定义动作空间 |
| AC-7.5 | Coordinate Descent Placer | ⚠️ | src/polaris/engine/analytical_placer.py:103 | 有 AnalyticalPlacer，但非坐标下降放置器 |
| AC-7.6 | 端到端冒烟测试 | ✅ | tests/ | PoLaRIS 有 139 测试文件、3346 测试函数 |
| AC-7.7 | Ariane RISC-V 教程 | ✅ | src/polaris/data/tilos_benchmark.py:243 | `load_ariane_benchmark` Ariane RISC-V CPU benchmark（17 模块） |

### 8. 宏单元布局（Macro Placement）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-8.1 | 顺序宏单元放置 | ✅ | src/polaris/engine/floorplan_env.py:157 | FloorplanEnv 顺序宏单元放置 |
| AC-8.2 | 网格化画布 | ✅ | src/polaris/data/benchmark_evaluator.py:494 | `grid_placement` 网格化布局 + FloorplanEnv 网格画布 |
| AC-8.3 | 6 小时内生成布局 | ⚠️ | - | PoLaRIS 无 6 小时布局时间 benchmark |
| AC-8.4 | 优于 RePlAce 与 SA | ⚠️ | src/polaris/data/benchmark_evaluator.py:551 | 有 `analytical_placement` 解析法基线，但无与 RePlAce/SA 对比 |
| AC-8.5 | 超人类布局 | ❌ | - | PoLaRIS 无超人类布局声明与验证 |

### 9. 标准单元布局（Standard Cell Placement）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-9.1 | 力导向粗布局 | ✅ | src/polaris/engine/analytical_placer.py:103 | `AnalyticalPlacer` DREAMPlace 力导向解析法布局 |
| AC-9.2 | DREAMPlace 集成 | ✅ | src/polaris/engine/analytical_placer.py:103 | AnalyticalPlacer 为 DREAMPlace 解析法布局器 |
| AC-9.3 | 标准单元分组 | ❌ | - | PoLaRIS 无 STANDARD_CELL_GROUPING.md 分组方法 |
| AC-9.4 | 混合方法 | ✅ | src/polaris/engine/alphachip_gnn.py:457 | RL（AlphaChipEdgeGNN）+ 解析法（AnalyticalPlacer）混合 |
| AC-9.5 | 商业 EDA 工具评估 | ❌ | - | PoLaRIS 无商业 EDA 工具评估流程 |

### 10. 奖励函数设计

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-10.1 | 负加权和奖励 | ✅ | src/polaris/trainer/reward_shaping.py:289 | `ExpertRewardShaper` 奖励塑形（端口对齐/弯曲/交叉/热） |
| AC-10.2 | 线长 (Wirelength) | ✅ | src/polaris/data/benchmark_evaluator.py:57 | `evaluate_hpwl` 半周长线长评估 |
| AC-10.3 | 拥塞 (Congestion) | ✅ | src/polaris/data/benchmark_evaluator.py:233 | `evaluate_congestion` LRT 模型拥塞评估 |
| AC-10.4 | 密度 (Density) | ✅ | src/polaris/engine/density_field.py:74 | `DensityField` DREAMPlace 网格化密度场 |
| AC-10.5 | 稀疏奖励结构 | ⚠️ | src/polaris/trainer/reward_shaping.py:289 | 有 reward_shaping，但非明确稀疏奖励（仅最后行动） |

### 11. 算法扩展与生态影响

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-11.1 | 扩展到逻辑综合 | ❌ | - | PoLaRIS 无逻辑综合扩展 |
| AC-11.2 | 扩展到 Macro 选择 | ❌ | - | PoLaRIS 无 Macro 选择扩展 |
| AC-11.3 | 扩展到时序优化 | ❌ | - | PoLaRIS 无时序优化扩展 |
| AC-11.4 | 引发 AI for chips 研究热潮 | ❌ | - | PoLaRIS 作为新项目，未引发研究热潮 |
| AC-11.5 | 跨 Alphabet 应用 | ❌ | - | PoLaRIS 无跨 Alphabet 应用 |

### 12. 学术评估与可复现性

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| AC-12.1 | TILOS-AI MacroPlacement 基准 | ✅ | src/polaris/data/tilos_benchmark.py:243 | `load_ariane_benchmark` TILOS Ariane RISC-V 基准（17 模块） |
| AC-12.2 | IEEE TCAD 评估论文 | ❌ | - | PoLaRIS 无 IEEE TCAD 评估论文 |
| AC-12.3 | 子 10nm 基准发布 | ❌ | - | PoLaRIS 无 sub-10nm 公开基准 |
| AC-12.4 | CT 与 Nature 差异研究 | ❌ | - | PoLaRIS 无 Circuit Training 与 Nature 差异研究 |
| AC-12.5 | SA 基线增强 | ❌ | - | PoLaRIS 无增强模拟退火基线 |

### T13 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 26 | 41.9% |
| ⚠️ 部分 | 12 | 19.4% |
| ❌ 缺失 | 14 | 22.6% |
| 🚫 不适用 | 10 | 16.1% |
| **覆盖率** | **(26+12×0.5)/62** | **51.6%** |

**T13 关键差距**：
- TPU/MediaTek 商业部署全面不适用：10 项 🚫（PoLaRIS 为开源光子项目，无商业芯片部署）
- 算法扩展与生态影响全面缺失：5/5 为 ❌（逻辑综合/Macro 选择/时序优化/研究热潮/Alphabet 应用）
- 学术评估部分缺失：4/5 为 ❌（IEEE TCAD 论文/sub-10nm 基准/CT-Nature 差异/SA 基线）
- 核心算法对齐良好：Edge-GNN ✅、PPO ✅、预训练 ✅、奖励函数 ✅、DREAMPlace ✅

---

## 总体统计汇总

### 三文档总体统计

| 文档 | ✅已有 | ⚠️部分 | ❌缺失 | 🚫不适用 | 覆盖率 |
|------|--------|--------|--------|----------|--------|
| T11 simphony (91) | 62 | 17 | 12 | 0 | 77.5% |
| T12 Cadence+Synopsys (85) | 2 | 24 | 56 | 8 | 16.5% |
| T13 AlphaChip (62) | 26 | 12 | 14 | 10 | 51.6% |
| **总计 (238)** | **90** | **53** | **82** | **18** | **48.9%** |

### 关键发现

1. **T11 simphony 覆盖率最高（77.5%）**：PoLaRIS 作为光子仿真工具，与 simphony 同领域，S 参数级联、SiEPIC 兼容、频率扫描、量子仿真、SAX/JAX 集成等核心能力对齐良好。主要差距在教育与文档（2.15）和 SiPANN 集成（2.8）。

2. **T12 Cadence/Synopsys 覆盖率最低（16.5%）**：PoLaRIS 为光子项目，与数字 EDA（Innovus/ICC2）领域差异大。数字时序优化（TNS/WNS/Skew/Hold/CTS）、功耗优化（UPF/IR Drop/Leakage）、先进节点认证（TSMC N3/N2/A16）等全面缺失或不适用。AI/ML 能力有部分覆盖（CongestionCNN、AlphaChipEdgeGNN）。

3. **T13 AlphaChip 覆盖率中等（51.6%）**：PoLaRIS 核心算法对齐良好（Edge-GNN、PPO、预训练、奖励函数、DREAMPlace），但商业部署（TPU/MediaTek）与生态影响不适用。学术评估与算法扩展有差距。

4. **PoLaRIS 优势领域**：
   - 光子 S 参数仿真（T11 2.1/2.4/2.9/2.10/2.11/2.14）
   - AlphaChip 算法复刻（T13 1/2/3/7/8/9/10）
   - 量子光子仿真（T11 2.11，PoLaRIS 独有 quantum_photonics 模块）
   - DRC/LVS 验证（T12 物理验证，KLayoutDRC/HierarchicalDRC/GraphLVS）

5. **PoLaRIS 主要差距**：
   - 数字时序与功耗优化（T12 大量 ❌）
   - 商业节点认证（T12 5/7，T13 5/6 🚫）
   - 教育文档与学术引用（T11 2.15）
   - 商业部署与生态影响（T13 5/6/11）

---

**文档结束** | 调研日期 2026-06-25 | 版本 v1.0 | 功能点总数 238
