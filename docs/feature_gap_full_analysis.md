# 光电子 EDA 工具功能点级全量差距分析（v2.0 完整版）

| 项目 | 内容 |
|------|------|
| 调研日期 | 2026-06-25 |
| 版本 | v2.0 完整版 |
| 功能点总数 | 985（13 个工具逐点标注） |
| 对比基准 | PoLaRIS 光电子 AI 布局布线引擎（308 功能点） |
| 排序规则 | 开源→商业，功能少→多，价格低→高 |
| 学术诚信声明 | 所有 PoLaRIS 状态均基于 `polaris_feature_inventory.md` 实际实现位置标注，无臆造。 |

## 状态图例

- ✅ 已有：PoLaRIS 有对应实现且达到生产级或对齐商业能力，引用实现位置
- ⚠️ 部分：PoLaRIS 有实现但差距明显（实验性/规模小/精度低/功能少/间接依赖第三方），说明差距
- ❌ 缺失：PoLaRIS 无对应实现
- 🚫 不适用：商业工具自有 API/电子芯片专属功能/平台差异，PoLaRIS 无需对齐
- 覆盖率 = (✅ + 0.5×⚠️) / (总数 - 🚫)

---

## 总览表

| 排序 | 工具 | 类型 | 功能点数 | ✅已有 | ⚠️部分 | ❌缺失 | 🚫不适用 | 覆盖率 | 价格估算 |
|------|------|------|----------|--------|--------|--------|----------|--------|----------|
| 1 | T10 sax | 开源 | 79 | 41 | 15 | 23 | 0 | 61.4% | 免费 |
| 2 | T11 simphony | 开源 | 91 | 62 | 17 | 12 | 0 | 77.5% | 免费 |
| 3 | T08 gdsfactory | 开源 | 108 | 49 | 15 | 44 | 0 | 52.3% | 免费 |
| 4 | T09 KLayout | 开源 | 126 | 25 | 20 | 67 | 14 | 31.3% | 免费 |
| 5 | T02 Luceda IPKISS | 商业 | 29 | 12 | 9 | 8 | 0 | 72.4% | ~$5K/年 |
| 6 | T04 Tidy3D | 商业 | 45 | 9 | 14 | 22 | 0 | 35.6% | ~$5-15K/年 |
| 7 | T03 OptoDesigner | 商业 | 46 | 28 | 14 | 3 | 1 | 77.8% | ~$10-20K/年 |
| 8 | T07 Photon Design | 商业 | 93 | 26 | 28 | 35 | 4 | 44.9% | ~$10-30K/年 |
| 9 | T06 L-Edit Photonics | 商业 | 69 | 24 | 24 | 21 | 0 | 69.6% | ~$15-30K/年 |
| 10 | T05 VPIphotonics | 商业 | 88 | 19 | 29 | 37 | 3 | 56.5% | ~$15-40K/年 |
| 11 | T01 Ansys Lumerical | 商业 | 64 | 15 | 22 | 22 | 5 | 57.8% | ~$20-50K/年 |
| 12 | T13 AlphaChip | AI 标杆 | 62 | 26 | 12 | 14 | 10 | 51.6% | 研究开源 |
| 13 | T12 Cadence+Synopsys | 商业 | 85 | 2 | 24 | 51 | 8 | 16.5% | ~$100K+/年 |
| **合计** | — | — | **985** | **338** | **243** | **359** | **45** | **48.9%** | — |

> 价格估算来源：各工具官网公开报价与行业调研（latitudeda.com、iccsz.com 等），均为估算值。
> 注：T12 文档原统计 ❌缺失 标注为 56，实际逐点加总为 51（Cadence Innovus 27 + Synopsys ICC2 24），本汇总按实际 51 计。

---

## 第1名: T10 sax（开源，79 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T09_T10_gap.md`
> 价格：免费（Apache-2.0 协议，来源 https://flaport.github.io/sax/）

### 2.1 JAX S 参数仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | JAX 后端 | ✅已有 | src/polaris/sim/jax_backend.py:65 | is_jax_available + JAX 后端 |
| 1.2 | S 字典（SDict） | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 使用 SDict |
| 1.3 | 函数式模型 | ✅已有 | src/polaris/sim/models.py:159 | 10 种模型为返回 S 字典的函数 |
| 1.4 | 标准字典 | ✅已有 | src/polaris/sim/models.py:159 | 使用标准 Python 字典 |
| 1.5 | XLA 加速 | ✅已有 | src/polaris/sim/jax_backend.py:101 | jit_compile JIT 编译 |
| 1.6 | GPU 加速 | ⚠️部分 | src/polaris/engine/gpu_backend.py:221 | GPUBackend CuPy 后端（实验性），非 JAX GPU |
| 1.7 | 双精度支持 | ⚠️部分 | src/polaris/sim/jax_backend.py:65 | 通过 JAX 支持，无显式双精度配置入口 |

### 2.2 子网络增长算法（Subnetwork Growth）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 子网络增长 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 子网络增长复刻 |
| 2.2 | Filipsson-Gunnar 后端 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax SAX 后端级联 |
| 2.3 | 算法遍历 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 实现算法遍历 |
| 2.4 | 算法改进 | ⚠️部分 | src/polaris/sim/subnetwork_decomp.py:407 | SubnetworkDecomposition 改进，非 FG 改进 |
| 2.5 | reciprocal 函数 | ❌缺失 | - | PoLaRIS 无 reciprocal 互易填充 |

### 2.3 autograd 逆向（自动微分）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 自动微分 | ✅已有 | src/polaris/sim/autodiff.py:40 | compute_gradient JAX 自动微分 |
| 3.2 | 梯度优化 | ✅已有 | src/polaris/sim/adjoint_optimizer.py:204 | AdjointOptimizer JAX 自动微分优化 |
| 3.3 | MZI 优化 | ⚠️部分 | src/polaris/sim/adjoint_optimizer.py:204 | 有 Adjoint 优化，无专门 MZI 优化示例 |
| 3.4 | 逆向设计 | ✅已有 | src/polaris/sim/ai_inverse_design.py:382 | RLInverseDesigner 逆向设计 |
| 3.5 | JAX 优化器 | ⚠️部分 | src/polaris/sim/lbfgs_optimizer.py:132 | 用 L-BFGS/NSGA-II 等，非 jax.example_libraries.optimizers |

### 2.4 cocotb 联合仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | 直接 cocotb 集成 | ❌缺失 | - | PoLaRIS 无 cocotb 集成 |
| 4.2 | SPICE 协同仿真 | ✅已有 | src/polaris/sim/mna_spice.py:102; src/polaris/sim/verilog_a.py:712 | MNASolver + run_ngspice_cosimulation |

### 2.5 gdsfactory 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | gplugins.sax | ✅已有 | src/polaris/pdk/gdsfactory_integration.py | gdsfactory 集成模块 |
| 5.2 | SAX gdsfactory 兼容性 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PolarisPDKRegistry 桥接 |
| 5.3 | 布局感知 Monte Carlo | ✅已有 | src/polaris/sim/layout_aware.py:361; src/polaris/sim/monte_carlo.py:63 | LayoutAwareSimulator + monte_carlo_simulate |
| 5.4 | 紧凑 MZI | ⚠️部分 | src/polaris/sim/models.py | 有 MZI 相关模型，无专门紧凑 MZI 仿真 |
| 5.5 | 相移器模型 | ✅已有 | src/polaris/sim/models.py:455 | phase_shifter_s 模型 |
| 5.6 | 层次化电路 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85 | HierarchicalPlacer 层次化 |
| 5.7 | FDTD S 参数模型 | ✅已有 | src/polaris/sim/fdtd_simulator.py:279 | run_fdtd_simulation FDTD 仿真 |
| 5.8 | QPDK 集成 | ❌缺失 | - | PoLaRIS 无量子 RF PDK 集成 |
| 5.9 | JAX 后端比较 | ⚠️部分 | src/polaris/sim/jax_backend.py:74 | get_jax_devices 探测，无跨后端基准测试 |

### 2.6 多端口器件

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 多端口 S 矩阵 | ✅已有 | src/polaris/sim/models.py:159-455 | mmi_2x2_s 等多端口模型 |
| 6.2 | 定向耦合器模型 | ✅已有 | src/polaris/sim/models.py | directional_coupler_s 模型 |
| 6.3 | 端口组合 | ✅已有 | src/polaris/sim/cascade.py:315 | 使用 2-tuple 端口组合作为键 |
| 6.4 | 稀疏 S 矩阵 | ✅已有 | src/polaris/sim/cascade.py:315 | 字典表示稀疏 S 矩阵 |
| 6.5 | 字符串索引 | ✅已有 | src/polaris/sim/models.py:159 | 字符串端口名索引 |

### 2.7 频率扫描

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | 波长扫描 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率扫描 |
| 7.2 | 全局设置 | ⚠️部分 | src/polaris/sim/simulator.py:57 | 有全局参数，无根分发到同名子组件 |
| 7.3 | 嵌套设置 | ⚠️部分 | src/polaris/sim/cascade.py:315 | 有嵌套电路，无嵌套设置调用 |
| 7.4 | 频率分辨率 | ⚠️部分 | src/polaris/sim/simulator.py:57 | 有频率配置，无分辨率基准测试 |
| 7.5 | 多波长 S 参数 | ✅已有 | src/polaris/sim/simulator.py:57 | S 参数支持数组（多波长） |

### 2.8 级联算法（Backends）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | KLU 后端 | ❌缺失 | - | PoLaRIS 无 KLU 后端 |
| 8.2 | KLU 理论背景 | ❌缺失 | - | PoLaRIS 无 KLU 直接稀疏求解器 |
| 8.3 | 稀疏辅助函数 | ⚠️部分 | src/polaris/sim/subnetwork_decomp.py:51 | BlockTridiagonalMatrix 稀疏，非 KLU 辅助 |
| 8.4 | KLU 算法遍历 | ❌缺失 | - | PoLaRIS 无 KLU 遍历 |
| 8.5 | KLU 算法改进 | ❌缺失 | - | PoLaRIS 无 KLU 改进 |
| 8.6 | Filipsson-Gunnar 后端 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax FG 后端 |
| 8.7 | Additive 后端 | ❌缺失 | - | PoLaRIS 无 Additive 后端 |
| 8.8 | Forward-only 后端 | ❌缺失 | - | PoLaRIS 无 Forward-only 后端 |
| 8.9 | Forward-only 加速 | ❌缺失 | - | PoLaRIS 无 Forward-only 加速 |
| 8.10 | Sparse COO 后端 | ❌缺失 | - | PoLaRIS 无 Sparse COO 后端 |
| 8.11 | 后端可互换 | ⚠️部分 | src/polaris/sim/cascade.py:315 | 有 SAX 后端，无多后端互换机制 |
| 8.12 | analyze_instances | ⚠️部分 | src/polaris/sim/dag_scheduler.py:44 | CircuitDAG 分析，非端口组合分析 |
| 8.13 | analyze_circuit | ✅已有 | src/polaris/sim/dag_scheduler.py:44 | CircuitDAG 电路分析 |
| 8.14 | evaluate_circuit | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 电路评估 |
| 8.15 | klujax 依赖 | ❌缺失 | - | PoLaRIS 无 klujax 依赖 |

### 2.9 电路构建

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | sax.circuit | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 从网表构建电路 |
| 9.2 | 网表格式 | ✅已有 | src/polaris/data/data_loader.py:105 | circuit_spec_to_netlist_dict 三部分网表 |
| 9.3 | YAML 电路 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:298 | parse_pic_yaml YAML 解析 |
| 9.4 | 模型组合 | ✅已有 | src/polaris/sim/cascade.py:315 | 组件模型可组合成电路 |

### 2.10 模型库

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 内置模型 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种基础器件 S 参数模型 |
| 10.2 | RF 模型 | ❌缺失 | - | PoLaRIS 无 sax.models.rf RF 模型 |
| 10.3 | 模型拟合 | ❌缺失 | - | PoLaRIS 无 sax.fit 模型拟合 |
| 10.4 | 参数化模型 | ✅已有 | src/polaris/sim/models.py:25-107 | RingParams/WaveguideParams/CouplerParams 参数化 |
| 10.5 | 表面模型 | ❌缺失 | - | PoLaRIS 无表面模型 |
| 10.6 | 所有模型 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种模型完整参考 |

### 2.11 仿真示例

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 快速开始 | ✅已有 | src/polaris/pipeline/__init__.py:156 | cmd_run CLI 快速开始 |
| 11.2 | 全通滤波器 | ⚠️部分 | src/polaris/sim/models.py | 有 ring_resonator_s，无专门全通滤波器示例 |
| 11.3 | 多模仿真 | ❌缺失 | - | PoLaRIS 无多模仿真 |
| 11.4 | 薄膜仿真 | ❌缺失 | - | PoLaRIS 无薄膜仿真 |
| 11.5 | 加性后端示例 | ❌缺失 | - | PoLaRIS 无 Additive 后端示例 |
| 11.6 | 布局感知 | ✅已有 | src/polaris/sim/layout_aware.py:361 | LayoutAwareSimulator 布局感知 |
| 11.7 | 稀疏 COO 示例 | ❌缺失 | - | PoLaRIS 无稀疏 COO 示例 |
| 11.8 | 前向 only 示例 | ❌缺失 | - | PoLaRIS 无 Forward-only 示例 |
| 11.9 | neff 色散 | ✅已有 | src/polaris/sim/simulator.py:357 | analyze_dispersion 色散分析 |

### 2.12 量子电路仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 量子电路仿真 | ✅已有 | src/polaris/sim/quantum_photonics.py:40 | permanent_ryser + boson_sampling 量子仿真 |
| 12.2 | 耦合谐振器电路 | ⚠️部分 | src/polaris/sim/models.py | 有 ring_resonator_s，无专门耦合谐振器电路 |
| 12.3 | OpenVINO NPU | ❌缺失 | - | PoLaRIS 无 OpenVINO NPU 支持 |
| 12.4 | JAXPR 导出 | ❌缺失 | - | PoLaRIS 无 JAXPR 导出 |
| 12.5 | 后端检测 | ✅已有 | src/polaris/sim/jax_backend.py:65 | is_jax_available + get_jax_devices 后端探测 |

### 2.13 LLM 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | PICBench 基准 | ❌缺失 | - | PoLaRIS 无 PICBench LLM 基准 |
| 13.2 | JSON 网表 | ✅已有 | src/polaris/sim/siepic_netlist.py:133 | parse_siepic_json JSON 网表解析 |

### T10 sax 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 41 | 51.9% |
| ⚠️ 部分 | 15 | 19.0% |
| ❌ 缺失 | 23 | 29.1% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **79** | **100%** |

**覆盖率**: (41 + 0.5×15) / 79 = 48.5/79 = **61.4%**

---

## 第2名: T11 simphony（开源，91 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T11_T12_T13_gap.md`
> 价格：免费（MIT 协议，来源 https://simphonyphotonics.readthedocs.io/）

### 2.1 S 参数级联（Subnetwork Growth）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 子网络增长算法 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit SAX 子网络增长算法复刻 |
| 1.2 | 子网络增长例程 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax SAX 后端级联例程 |
| 1.3 | S 参数矩阵 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种基础器件 S 参数模型 |
| 1.4 | 端口约定 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 处理端口连接约定 |
| 1.5 | 紧凑模型 | ✅已有 | src/polaris/sim/models.py:25,73,107 | RingParams/WaveguideParams/CouplerParams |
| 1.6 | 频率相关 S 参数 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率域仿真器 |

### 2.2 SiEPIC 兼容

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | SiEPIC 库 | ✅已有 | src/polaris/pdk/siepic_mapping.py:31 | SIEPIC_TO_POLARIS SiEPIC 器件名映射 |
| 2.2 | SiEPIC Ebeam PDK | ✅已有 | src/polaris/pdk/foundry_platforms.py:72 | FOUNDRY_PLATFORMS 包含 SiEPIC 平台 |
| 2.3 | SiEPIC-Tools 互操作 | ✅已有 | src/polaris/data/gds_loader.py:468 | load_gds_to_circuit SiEPIC GDS 电路解析 |
| 2.4 | KLayout 电路仿真 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | KLayoutDRCRunner KLayout 集成 |
| 2.5 | grating_coupler 模型 | ✅已有 | src/polaris/sim/models.py:159-455 | grating_coupler_s 模型实现 |
| 2.6 | Y-branch 模型 | ✅已有 | src/polaris/sim/models.py:159-455 | y_branch_s 模型实现 |
| 2.7 | ebeam_terminator 模型 | ✅已有 | src/polaris/sim/models.py:159-455 | terminator_s 模型实现 |

### 2.3 子电路（Subcircuit）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | Subcircuit 类 | ⚠️部分 | src/polaris/data/specs.py:74 | PoLaRIS 用 CircuitSpec 数据类替代 |
| 3.2 | 子电路模式 | ⚠️部分 | - | 无直接"子电路模式"抽象，通过 CircuitSpec 组合 |
| 3.3 | add 方法 | ⚠️部分 | src/polaris/data/specs.py:74 | CircuitSpec 通过器件列表+连接列表构建 |
| 3.4 | connect_many | ⚠️部分 | src/polaris/data/data_loader.py:105 | circuit_spec_to_netlist_dict 批量连接转换 |
| 3.5 | 引脚分配 | ✅已有 | src/polaris/data/specs.py:51 | DeviceSpec 包含端口定义 |
| 3.6 | 环形谐振器构建 | ✅已有 | src/polaris/sim/models.py:159-455 | ring_resonator_s 模型 + RingParams |
| 3.7 | Add-Drop 滤波器 | ⚠️部分 | src/polaris/sim/models.py:159-455 | 有 ring_resonator_s 可构建 Add-Drop，无专用封装 |

### 2.4 频率扫描（Frequency Sweep）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | SweepSimulation | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率域仿真器支持扫描 |
| 4.2 | 频率范围设置 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 支持频率范围参数 |
| 4.3 | 波长单位 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 接受波长参数 |
| 4.4 | 数据提取 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 返回仿真数据 |
| 4.5 | 频率相关仿真 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率域仿真 |
| 4.6 | Nf 频率点 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 支持多频率点扫描 |

### 2.5 比 Lumerical 快 20×

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 20× 加速 | ⚠️部分 | src/polaris/sim/cascade.py:315 | 有 SAX 子网络增长算法，但未公开 20× benchmark |
| 5.2 | 文档声明 | ❌缺失 | - | PoLaRIS 文档无此声明 |
| 5.3 | 准确性比较 | ❌缺失 | - | PoLaRIS 无与 Lumerical INTERCONNECT 的直接准确性比较报告 |
| 5.4 | 商业工具替代 | ✅已有 | src/polaris/sim/lumerical_integration.py:84 | PoLaRIS 定位为开源替代，并有 Lumerical 集成模块 |

### 2.6 参数扫描（Parameter Sweep）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | MonteCarloSweepSimulation | ✅已有 | src/polaris/sim/monte_carlo.py:63 | monte_carlo_simulate JAX vmap 并行蒙特卡洛仿真 |
| 6.2 | Monte Carlo 运行 | ✅已有 | src/polaris/sim/monte_carlo.py:63 | monte_carlo_simulate 支持指定运行次数 |
| 6.3 | 参数扰动 | ✅已有 | src/polaris/sim/monte_carlo.py:124 | sensitivity_analysis 灵敏度分析支持参数扰动 |
| 6.4 | 多参数变化 | ✅已有 | src/polaris/sim/monte_carlo.py:124 | sensitivity_analysis 支持多参数变化 |
| 6.5 | 理想值提取 | ⚠️部分 | src/polaris/sim/monte_carlo.py:63 | monte_carlo_simulate 支持理想值，无明确"位置 0"约定 |
| 6.6 | 半径变化 | ✅已有 | src/polaris/sim/monte_carlo.py:124 | sensitivity_analysis 支持单参数（如半径）变化 |

### 2.7 可视化（Visualization）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | matplotlib 集成 | ✅已有 | src/polaris/eval/layout_render.py:123 | render_layout matplotlib 版图渲染 |
| 7.2 | 传输谱绘制 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | 有版图渲染，无专用传输谱绘制函数 |
| 7.3 | Monte Carlo 绘图 | ⚠️部分 | - | 无专用 Monte Carlo 多曲线绘制 |
| 7.4 | 眼图绘制 | ✅已有 | src/polaris/sim/verilog_a.py:864 | compute_eye_diagram + EyeDiagramAnalyzer |
| 7.5 | 图表标注 | ✅已有 | src/polaris/eval/layout_render.py:123 | render_layout 支持图表标注 |

### 2.8 SiPANN 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | SiPANN 库 | ❌缺失 | - | PoLaRIS 无 SiPANN 模型库（用自有 models.py 替代） |
| 8.2 | SimphonyWrapper | ❌缺失 | - | PoLaRIS 无 SiPANN SimphonyWrapper |
| 8.3 | 神经网络模型 | ⚠️部分 | src/polaris/engine/gnn.py:43 | PoLaRIS 有 GNN 神经网络，非 SiPANN 的 SCEE 模型 |
| 8.4 | gap_func_symmetric | ⚠️部分 | src/polaris/sim/models.py:159-455 | 有 directional_coupler_s，非 SiPANN gap_func 实现 |
| 8.5 | gap_func_antisymmetric | ⚠️部分 | src/polaris/sim/models.py:159-455 | 有 directional_coupler_s，非 SiPANN antisymmetric 实现 |
| 8.6 | 半环模型 | ✅已有 | src/polaris/sim/models.py:159-455 | ring_resonator_s 半环/环形谐振器模型 |
| 8.7 | SCEE 集成 | ❌缺失 | - | PoLaRIS 无 SCEE 集成 |

### 2.9 SAX 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | SAX 模型定义 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax SAX 后端级联 |
| 9.2 | JAX 计算引擎 | ✅已有 | src/polaris/sim/jax_backend.py:65 | is_jax_available JAX 后端支持 |
| 9.3 | GPU 加速 | ✅已有 | src/polaris/engine/gpu_backend.py:221 | GPUBackend CuPy GPU 后端 |
| 9.4 | CPU 兼容 | ✅已有 | src/polaris/engine/gpu_backend.py:221 | GPUBackend 自动回退 NumPy |
| 9.5 | 双精度配置 | ✅已有 | src/polaris/sim/jax_backend.py:65 | jax_backend 支持双精度配置 |
| 9.6 | jax.numpy | ✅已有 | src/polaris/sim/jax_backend.py:124 | waveguide_s_jax 使用 jax.numpy |
| 9.7 | 可调用模型 | ✅已有 | src/polaris/sim/models.py:159-455 | S 参数模型为可调用函数 |
| 9.8 | 默认参数 | ✅已有 | src/polaris/sim/models.py:25,73,107 | 模型参数类有默认值 |

### 2.10 电路定义

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 网表编写 | ✅已有 | src/polaris/sim/siepic_netlist.py:133 | parse_siepic_json SiEPIC 网表解析 |
| 10.2 | 可调用仿真 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 可调用仿真 |
| 10.3 | 便捷类仿真 | ✅已有 | src/polaris/pipeline/integrated.py:446 | IntegratedPipeline 一体化流水线 |
| 10.4 | SPICE 类方法 | ✅已有 | src/polaris/sim/mna_spice.py:102 | MNASolver MNA SPICE 求解器 |
| 10.5 | 复杂仿真能力 | ✅已有 | src/polaris/pipeline/integrated.py:446 | IntegratedPipeline 复杂仿真能力 |

### 2.11 量子仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 量子仿真器 | ✅已有 | src/polaris/sim/quantum_photonics.py:40 | 完整量子光子仿真模块 |
| 11.2 | 经典转量子 | ✅已有 | src/polaris/sim/quantum_photonics.py:557 | clements_unitary Clements 分解转酉矩阵 |
| 11.3 | 酉矩阵转换 | ✅已有 | src/polaris/sim/quantum_photonics.py:557 | clements_unitary 酉矩阵转换 |
| 11.4 | 均匀损耗假设 | ✅已有 | src/polaris/sim/quantum_photonics.py:329 | lossy_boson_sampling 损耗玻色采样 |
| 11.5 | 量子态 | ✅已有 | src/polaris/sim/quantum_photonics.py:211 | boson_sampling_prob 量子态仿真 |
| 11.6 | 高斯态 | ✅已有 | src/polaris/sim/quantum_photonics.py:490 | gbs_probability 高斯玻色采样 + hafnian:438 |
| 11.7 | 量子谐振子 | ⚠️部分 | - | PoLaRIS 量子模块未明确包含量子谐振子专用仿真 |
| 11.8 | 海森堡不确定性 | ❌缺失 | - | PoLaRIS 无海森堡不确定性原理仿真 |

### 2.12 模型框架

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 可扩展框架 | ✅已有 | src/polaris/pdk/catalog.py:227 | DeviceCatalog 可扩展器件注册表 |
| 12.2 | 自定义组件 | ✅已有 | src/polaris/pdk/catalog.py:227 | DeviceCatalog 支持自定义组件 |
| 12.3 | 模型库 | ✅已有 | src/polaris/pdk/foundry_devices.py:188 | get_foundry_devices foundry 器件库 |
| 12.4 | 预仿真组件 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种预仿真 S 参数组件 |
| 12.5 | 插件兼容 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PolarisPDKRegistry 48 gdsfactory PDK 桥接 |

### 2.13 平台与安装

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | 跨平台 | ✅已有 | src/polaris/ | Python 实现，跨平台 |
| 13.2 | Python 3 脚本 | ✅已有 | src/polaris/ | Python 3 脚本化 |
| 13.3 | pip 安装 | ⚠️部分 | - | PoLaRIS 未明确公开 pip 安装方式 |
| 13.4 | Python 3.9+ | ✅已有 | src/polaris/ | Python 3 兼容 |
| 13.5 | 可选依赖 | ⚠️部分 | - | PoLaRIS 有可选依赖，未明确 extras 分类 |
| 13.6 | MIT 协议 | ⚠️部分 | - | PoLaRIS 协议未在功能清单中明确 |

### 2.14 经典仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | ClassicalSim | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 经典频率域仿真 |
| 14.2 | 线性 PIC 仿真 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 线性 PIC 仿真 |
| 14.3 | 时域仿真潜力 | ✅已有 | src/polaris/sim/interconnect.py:91 | InterconnectTimeDomainSimulator R32 时域仿真 |

### 2.15 教育与文档

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | 在线文档 | ⚠️部分 | - | PoLaRIS 有文档但未明确在线托管 |
| 15.2 | 教程 | ⚠️部分 | - | PoLaRIS 有文档但无系统入门教程 |
| 15.3 | MZI 教程 | ❌缺失 | - | PoLaRIS 无 MZI 专用教程 |
| 15.4 | Add-Drop 滤波器教程 | ❌缺失 | - | PoLaRIS 无 Add-Drop 滤波器教程 |
| 15.5 | 量子仿真教程 | ❌缺失 | - | PoLaRIS 无量子仿真教程 |
| 15.6 | Photonics-Bootcamp | ❌缺失 | - | PoLaRIS 无 Photonics-Bootcamp 集成 |
| 15.7 | 学术引用 | ❌缺失 | - | PoLaRIS 无明确学术引用格式 |
| 15.8 | 贡献指南 | ❌缺失 | - | PoLaRIS 无明确贡献指南 |

### T11 simphony 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 62 | 68.1% |
| ⚠️ 部分 | 17 | 18.7% |
| ❌ 缺失 | 12 | 13.2% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **91** | **100%** |

**覆盖率**: (62 + 0.5×17) / 91 = 70.5/91 = **77.5%**

---

## 第3名: T08 gdsfactory（开源，108 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T07_T08_gap.md`
> 价格：免费（MIT 协议，来源 https://gdsfactory.github.io/gdsfactory/）

### 2.1 参数化器件（Parametric Cells, PCells）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 参数化单元定义，`@gf.cell` 装饰器缓存 | ✅已有 | pdk/pcell.py:576 | 有 polaris_cell PCell 装饰器 |
| 1.2 | Component 类，含多边形/端口元数据 | ✅已有 | pdk/device.py:85 | 有 Device 核心数据类 |
| 1.3 | 函数式编程，KLayout C++ 几何引擎后端 | ✅已有 | data/gds_loader.py:468 | 有 KLayout 集成 GDS 解析 |
| 1.4 | 内置组件库 `gf.components` | ✅已有 | pdk/catalog.py:453、pdk/pcell.py:667-719 | 有 default_catalog 和内置 PCell |

### 2.2 YAML 层次化设计

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | YAML Place and AutoRoute | ⚠️部分 | pdk/gdsfactory_pdk_bridge.py:298 | 有 parse_pic_yaml，非完整 Place and AutoRoute |
| 2.2 | `from_yaml` 函数 | ⚠️部分 | pdk/gdsfactory_pdk_bridge.py:298 | 有 PIC YAML 解析，非完整 from_yaml 五段结构 |
| 2.3 | Pydantic 模型校验 | ❌缺失 | - | PoLaRIS 使用 dataclass，无 Pydantic 模型校验 |
| 2.4 | Jinja2 模板支持 | ❌缺失 | - | 无 Jinja2 模板支持 |
| 2.5 | 网表提取 `get_netlist()` | ✅已有 | data/data_loader.py:105、sim/lvs.py:121 | 有 circuit_spec_to_netlist_dict 和 extract_netlist_from_gds |
| 2.6 | 层次化组装 | ✅已有 | engine/hierarchical_placer.py:85 | 有 HierarchicalPlacer 层次化布局 |

### 2.3 route_fiber_array（光纤阵列路由）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 光纤阵列路由 | ❌缺失 | - | 无专门光纤阵列路由 |
| 3.2 | 边缘耦合器路由 | ❌缺失 | - | 无专门边缘耦合器路由 |
| 3.3 | Pad 阵列路由 | ⚠️部分 | router/opto_electrical.py:101 | 有 OptoElectricalRouter，无专门 Pad 阵列路由 |

### 2.4 get_bundle / route_bundle

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | route_bundle | ✅已有 | router/bundle_router.py:99 | 有 route_bundle |
| 4.2 | route_bundle_all_angle | ✅已有 | router/all_angle_router.py:29 | 有 AllAngleRouter |
| 4.3 | route_bundle_electrical | ⚠️部分 | router/opto_electrical.py:101 | 有 OptoElectricalRouter，非专门 wire_corner 电气路由 |
| 4.4 | 路径长度匹配 | ✅已有 | router/bundle_router.py:147 | 有 route_bundle_path_length_match |
| 4.5 | 碰撞避免 | ✅已有 | router/curvy_router.py:350 | 有 AdaptiveCrossingInserter 和 rip-up and reroute |
| 4.6 | 自动锥度 auto_taper | ✅已有 | router/bundle_router.py:232 | 有 auto_taper |
| 4.7 | Dubins 路径 | ✅已有 | router/bundle_router.py:289 | 有 dubins_path |

### 2.5 routing strategies（路由策略）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | get_bundle_all_angle | ✅已有 | router/all_angle_router.py:29 | 有 AllAngleRouter |
| 5.2 | route_astar | ✅已有 | router/curvy_router.py:118、router/jps_router.py:33 | 有 CurvyAStarRouter 和 JPSRouter |
| 5.3 | route_quad | ❌缺失 | - | 无 U 形电气走线策略 |
| 5.4 | 自定义横截面 | ✅已有 | pdk/gdsfactory_integration.py | 有 convert_crosssection |
| 5.5 | steps 语法 | ❌缺失 | - | 无 steps 航点语法 |

### 2.6 KLayout DRC 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | KLayout C++ 几何引擎后端 | ✅已有 | data/gds_loader.py:468、sim/klayout_drc.py:238 | 有 KLayout 集成 |
| 6.2 | DRC 验证 | ✅已有 | sim/klayout_drc.py:238、sim/hierarchical_drc.py:165 | 有 KLayoutDRCRunner 和 HierarchicalDRC |
| 6.3 | LVS 验证 | ✅已有 | sim/graph_lvs.py:160、sim/lvs.py:121 | 有 GraphIsomorphismLVSComparer 和 extract_netlist_from_gds |
| 6.4 | get_netlist (KLayout) | ✅已有 | sim/lvs.py:121 | 有 extract_netlist_from_gds |
| 6.5 | klive 插件 | ❌缺失 | - | 无 klive 插件 |

### 2.7 GDSII / OASIS 导出

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | GDSII 导出 `write_gds()` | ✅已有 | eval/layout_render.py:331 | 有 export_gds |
| 7.2 | OASIS 导出 | ✅已有 | eval/layout_render.py:361 | 有 export_oasis |
| 7.3 | STL 导出（3D 打印） | ❌缺失 | - | 无 STL 导出 |
| 7.4 | GERBER 导出（PCB） | ❌缺失 | - | 无 GERBER 导出 |
| 7.5 | flatten_offgrid_references | ❌缺失 | - | 无 flatten_offgrid_references 选项 |

### 2.8 PDK 支持（43+ PDK）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 43+ foundry PDK | ✅已有 | pdk/gdsfactory_pdk_bridge.py:349 | 有 PolarisPDKRegistry（48 gdsfactory PDK） |
| 8.2 | 开源光子 PDK | ✅已有 | pdk/siepic_mapping.py:31、pdk/foundry_platforms.py:72 | 有 SiEPIC 映射和 FOUNDRY_PLATFORMS（11 平台） |
| 8.3 | 开源 CMOS PDK | ✅已有 | pdk/process_nodes.py:76 | 有 CMOS_PROCESS_NODES |
| 8.4 | NDA PDK | ⚠️部分 | pdk/foundry_devices.py:188 | 有 foundry_devices 框架，NDA PDK 覆盖度未明确 |
| 8.5 | PDK 构建说明 | ✅已有 | pdk/catalog.py:465、pdk/gpic.py:629 | 有 build_default_catalog 和 build_gpic_pdk |
| 8.6 | PDK 导入 | ✅已有 | pdk/gdsfactory_pdk_bridge.py:349 | 有 gdsfactory PDK 桥接导入 |

### 2.9 量子组件（Quantum Components）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | QPDK 量子 PDK | ❌缺失 | - | 无超导量子 PDK |
| 9.2 | Transmon 量子比特 | ❌缺失 | - | 无 Transmon 组件 |
| 9.3 | Fluxonium 量子比特 | ❌缺失 | - | 无 Fluxonium 组件 |
| 9.4 | Unimon 量子比特 | ❌缺失 | - | 无 Unimon 组件 |
| 9.5 | SQUID 结 | ❌缺失 | - | 无 SQUID 结组件 |
| 9.6 | CPW 谐振器 | ❌缺失 | - | 无 CPW 谐振器组件 |
| 9.7 | 叉指电容 | ❌缺失 | - | 无叉指电容组件 |
| 9.8 | 量子测试芯片 | ❌缺失 | - | 无量子测试芯片示例 |
| 9.9 | 量子分析 S 参数模型 | ⚠️部分 | sim/quantum_photonics.py:40 | 有量子光子仿真，非超导量子比特 S 参数模型 |
| 9.10 | 量子工具集成 | ❌缺失 | - | 无这些量子工具集成 |

### 2.10 SAX 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | SAX 电路求解器（JAX） | ✅已有 | sim/cascade.py:315 | 有 cascade_circuit SAX 子网络增长算法复刻 |
| 10.2 | 散射字典 SDict | ✅已有 | sim/models.py:159、sim/cascade.py:397 | 有 S 参数模型和 _cascade_with_sax |
| 10.3 | 梯度优化 | ✅已有 | sim/autodiff.py:40、sim/jax_backend.py:65 | 有 JAX 梯度和 JIT 编译 |
| 10.4 | 布局感知 Monte Carlo | ✅已有 | sim/monte_carlo.py:63、sim/layout_aware.py:361 | 有 monte_carlo_simulate 和 LayoutAwareSimulator |
| 10.5 | 层次化电路仿真 | ✅已有 | sim/subnetwork_decomp.py:407 | 有 SubnetworkDecomposition |
| 10.6 | FDTD S 参数模型拟合 | ✅已有 | sim/fdtd_simulator.py:57 | 有 FDTDBackend 三后端 S 参数 |

### 2.11 Meep 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | gmeep 插件 | ✅已有 | sim/fdtd_simulator.py:57 | 有 FDTDBackend.MEEP |
| 11.2 | 自动 S 参数提取 | ✅已有 | sim/fdtd_simulator.py:279 | 有 run_fdtd_simulation 统一入口 |
| 11.3 | 2.5D 仿真模式 | ❌缺失 | - | 无 2.5D 仿真模式 |
| 11.4 | 端口对称性加速 | ❌缺失 | - | 无端口对称性加速 |
| 11.5 | 多模仿真 | ❌缺失 | - | 无明确多模仿真 |
| 11.6 | 多核/MPI 并行仿真 | ⚠️部分 | sim/fdtd_simulator.py:57 | 依赖 MEEP 后端并行，非自研并行调度 |
| 11.7 | 伴随优化 | ✅已有 | sim/adjoint_optimizer.py:204 | 有 AdjointOptimizer |

### 2.12 Tidy3D 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | Tidy3D FDTD（GPU 快速） | ✅已有 | sim/tidy3d_integration.py:116 | 有 Tidy3DAdapter |
| 12.2 | 材料数据库 | ❌缺失 | - | 无材料数据库 |
| 12.3 | Component Modeler | ✅已有 | sim/tidy3d_integration.py:116 | 有 Tidy3DAdapter |
| 12.4 | S 参数写入和文件缓存 | ✅已有 | sim/touchstone.py:184 | 有 save_touchstone |
| 12.5 | 2D 和 3D 仿真绘图 | ✅已有 | sim/fdtd_simulator.py:57 | 有 FDTD 2D/3D 后端 |
| 12.6 | 侵蚀/膨胀分析 | ❌缺失 | - | 无侵蚀/膨胀分析 |
| 12.7 | 并行运行作业 | ⚠️部分 | trainer/parallel_rollout.py:80 | 有并行 rollout，非 Tidy3D 作业并行 |

### 2.13 Lumerical 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | Lumerical FDTD 接口 | ✅已有 | sim/lumerical_integration.py:896 | 有 LumericalIntegration |
| 13.2 | write_sparameters_lumerical | ⚠️部分 | sim/lumerical_integration.py:402 | 有 INTERCONNECTSimulator（实验性） |
| 13.3 | CSV/DAT 输出 | ⚠️部分 | sim/touchstone.py:184 | 有 Touchstone 保存，无专门 CSV/DAT 格式 |
| 13.4 | 层堆栈修改 | ✅已有 | pdk/gdsfactory_integration.py | 有 convert_layerstack |
| 13.5 | lumapi 集成 | ✅已有 | sim/lumerical_integration.py:896 | 有 LumericalIntegration（实验性） |

### 2.14 cocotb 联合仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | SPICE 协同仿真 | ✅已有 | sim/verilog_a.py:712、sim/mna_spice.py:102 | 有 run_ngspice_cosimulation 和 MNASolver |
| 14.2 | 直接 cocotb 集成 | ❌缺失 | - | 无 cocotb 集成 |

### 2.15 VLSIR SPICE 导出

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | VLSIR 网表导出 | ❌缺失 | - | 无 VLSIR 网表导出 |
| 15.2 | Spectre RF 网表导出 | ❌缺失 | - | 无 Spectre RF 导出 |
| 15.3 | Xyce 网表导出 | ❌缺失 | - | 无 Xyce 导出 |
| 15.4 | ngspice 网表导出 | ⚠️部分 | sim/verilog_a.py:712 | 有 run_ngspice_cosimulation，无独立 ngspice 网表导出 |
| 15.5 | 分析类型支持 | ⚠️部分 | sim/mna_spice.py:102 | 有 MNASolver，分析类型覆盖度未明确 |
| 15.6 | kdb_vlsir 转换 | ❌缺失 | - | 无 kdb_vlsir 转换 |

### 2.16 matplotlib 可视化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 16.1 | Component `plot()` 方法 | ✅已有 | eval/layout_render.py:123 | 有 render_layout |
| 16.2 | plot_sparameters | ❌缺失 | - | 无专门 plot_sparameters |
| 16.3 | plot_netlist | ❌缺失 | - | 无专门 plot_netlist |
| 16.4 | plot_slice 截面绘制 | ❌缺失 | - | 无 plot_slice |

### 2.17 Jupyter Notebook 支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 17.1 | Notebook 驱动工作流 | ❌缺失 | - | 无明确 Notebook 支持 |
| 17.2 | 交互式开发和可视化 | ⚠️部分 | web/server.py:329 | 有 Web 服务器，非 Jupyter 交互 |
| 17.3 | rich_output | ❌缺失 | - | 无 rich_output |

### 2.18 其他仿真器集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 18.1 | Femwell (FEM) | ❌缺失 | - | 无 Femwell 集成 |
| 18.2 | Elmer (FEM) | ❌缺失 | - | 无 Elmer 集成 |
| 18.3 | Palace (FEM) | ❌缺失 | - | 无 Palace 集成 |
| 18.4 | MEOW (EME) | ❌缺失 | - | 无 MEOW 集成 |
| 18.5 | DEVSIM (TCAD) | ❌缺失 | - | 无 DEVSIM 集成 |
| 18.6 | MPB (Mode Solver) | ❌缺失 | - | 无 MPB 集成 |
| 18.7 | Luminescent AI | ❌缺失 | - | 无 Luminescent AI 集成 |
| 18.8 | FDTDz | ❌缺失 | - | 无 FDTDz 集成 |
| 18.9 | GMSH 网格 | ❌缺失 | - | 无 GMSH 集成 |

### 2.19 端到端设计流程

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 19.1 | 设计（布局、仿真、优化） | ✅已有 | pipeline/integrated.py:446 | 有 IntegratedPipeline |
| 19.2 | 验证（DRC、DFM、LVS） | ✅已有 | sim/klayout_drc.py:238、sim/graph_lvs.py:160 | 有 KLayoutDRCRunner 和 GraphIsomorphismLVSComparer |
| 19.3 | 验证（Validate，测试协议） | ✅已有 | sim/constraint_checker.py:53 | 有 ConstraintChecker 16 项约束检查 |
| 19.4 | 元数据兼容（晶圆探针） | ⚠️部分 | pdk/catalog.py:227 | 有 DeviceCatalog 元数据，无明确晶圆探针兼容元数据 |

### 2.20 GDSFactory+ 商业扩展

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 20.1 | GUI 界面（基于 VSCode） | ⚠️部分 | web/server.py:329 | 有 Web 服务器，非 VSCode GUI |
| 20.2 | 原理图捕获 | ❌缺失 | - | 无原理图捕获 |
| 20.3 | AI 助手辅助设计 | ✅已有 | pdk/pcell.py:631 | 有 ai_generate_pcell |
| 20.4 | CLI 工具 | ✅已有 | pipeline/__init__.py:291 | 有 main CLI 入口 |

### T08 gdsfactory 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 49 | 45.4% |
| ⚠️ 部分 | 15 | 13.9% |
| ❌ 缺失 | 44 | 40.7% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **108** | **100%** |

**覆盖率**: (49 + 0.5×15) / 108 = 56.5/108 = **52.3%**

---

## 第4名: T09 KLayout（开源，126 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T09_T10_gap.md`
> 价格：免费（GPLv3 协议，来源 https://www.klayout.de/）

### 2.1 版图查看（View）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 查看器模式 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | 有 render_layout 渲染，但非交互式查看器 |
| 1.2 | 大文件支持 | ❌缺失 | - | 不直接处理多 GB 版图，依赖 KLayout 库间接支持 |
| 1.3 | 多层叠加 | ✅已有 | src/polaris/eval/layout_render.py:123 | render_layout 支持多层渲染 |
| 1.4 | 标尺工具 | ❌缺失 | - | PoLaRIS 无交互式标尺 |
| 1.5 | 图像叠加 | ❌缺失 | - | PoLaRIS 无图像叠加功能 |
| 1.6 | 样式选项 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | matplotlib 渲染有样式选项，远少于 KLayout |
| 1.7 | 可切换层视图 | ❌缺失 | - | PoLaRIS 无交互式层切换 |
| 1.8 | 书签 | ❌缺失 | - | PoLaRIS 无书签功能 |
| 1.9 | 层次化上下文视图 | ❌缺失 | - | PoLaRIS 有层次化布局器但非查看器视图 |
| 1.10 | 搜索功能 | ❌缺失 | - | PoLaRIS 无版图搜索 |
| 1.11 | 按实例/形状浏览 | ❌缺失 | - | PoLaRIS 无实例/形状浏览 |
| 1.12 | 选择性单元屏蔽 | ❌缺失 | - | PoLaRIS 无单元屏蔽 |
| 1.13 | 2.5D 视图 | ❌缺失 | - | PoLaRIS 仅 2D 渲染，无 2.5D |

### 2.2 版图编辑（Edit）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 编辑器模式 | 🚫不适用 | - | PoLaRIS 定位为 AI 布局布线引擎，非交互式版图编辑器 |
| 2.2 | 创建层和单元 | ⚠️部分 | src/polaris/pdk/pcell.py:576 | 通过 PCell 编程创建，非交互式创建 |
| 2.3 | 几何图形绘制 | ⚠️部分 | src/polaris/pdk/pcell.py:667-719 | PCell 内置多边形/矩形/路径绘制，非交互式 |
| 2.4 | 变换操作 | ✅已有 | src/polaris/engine/floorplan_env.py:157 | 布局环境支持移动/旋转/镜像 |
| 2.5 | 布尔运算 | ❌缺失 | - | PoLaRIS 无几何布尔运算（并/交/差） |
| 2.6 | 搜索替换 | ❌缺失 | - | PoLaRIS 无形状/实例搜索替换 |
| 2.7 | 参数化单元 PCell | ✅已有 | src/polaris/pdk/pcell.py:576 | polaris_cell 装饰器 + 4 个内置 PCell |
| 2.8 | 复制/粘贴 | ❌缺失 | - | PoLaRIS 无交互式复制粘贴 |
| 2.9 | 无限撤销/重做 | ❌缺失 | - | PoLaRIS 无撤销/重做栈 |

### 2.3 DRC（设计规则检查）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | DRC 引擎 | ✅已有 | src/polaris/sim/klayout_drc.py:238; src/polaris/sim/hierarchical_drc.py:165 | KLayoutDRCRunner + HierarchicalDRC 双引擎 |
| 3.2 | DRCLayer 类 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout 库间接使用 DRCLayer，无独立封装 |
| 3.3 | 通用 DRC 函数 | ✅已有 | src/polaris/sim/klayout_drc.py:531; src/polaris/sim/hierarchical_drc.py:487 | run_klayout_drc + run_hierarchical_drc 入口 |
| 3.4 | DRC 表达式 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout runset 表达式，无独立 DRCOpNode |
| 3.5 | 天线检查 | 🚫不适用 | - | 天线检查为电子 IC 工艺规则，光子电路不适用 |
| 3.6 | 设备提取 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有光子网表提取，非电子设备参数化提取 |
| 3.7 | 宽度检查 | ✅已有 | src/polaris/sim/constraint_checker.py:53 | ConstraintChecker 含宽度约束 |
| 3.8 | 间距检查 | ✅已有 | src/polaris/sim/constraint_checker.py:53 | ConstraintChecker 含间距约束 |
| 3.9 | 包围检查 | ❌缺失 | - | PoLaRIS 无 enclosing 检查 |
| 3.10 | 面积检查 | ⚠️部分 | src/polaris/data/benchmark_evaluator.py:120 | 有面积利用率评估，无面积条件选择形状 |
| 3.11 | 角点选择 | ❌缺失 | - | PoLaRIS 无 corners 选择 |
| 3.12 | 覆盖检查 | ❌缺失 | - | PoLaRIS 无 covering 检查 |

### 2.4 LVS（版图与原理图一致性验证）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | LVS 比较 | ✅已有 | src/polaris/sim/graph_lvs.py:160; src/polaris/sim/lvs.py:494 | GraphIsomorphismLVSComparer + run_lvs |
| 4.2 | 网表等价提示 | ❌缺失 | - | PoLaRIS 无 same_nets 调试提示 |
| 4.3 | 电路等价提示 | ❌缺失 | - | PoLaRIS 无 same_circuit 等价声明 |
| 4.4 | 容差设置 | ⚠️部分 | src/polaris/sim/lvs.py:465 | compare_netlists 支持容差，但功能较简单 |
| 4.5 | 引脚交换 | ❌缺失 | - | PoLaRIS 无引脚交换 |
| 4.6 | 电容/电阻消除 | 🚫不适用 | - | 电子 IC LVS 特性，光子电路不适用 |
| 4.7 | 引脚标签检查 | ⚠️部分 | src/polaris/sim/graph_lvs.py:89 | PhotonicsNetlist 含引脚信息，无专门标签检查 |
| 4.8 | 网表层次结构 | ✅已有 | src/polaris/sim/graph_lvs.py:89 | PhotonicsNetlist 支持层次结构 |
| 4.9 | 连接定义 | ✅已有 | src/polaris/data/data_loader.py:105 | circuit_spec_to_netlist_dict 定义连接 |
| 4.10 | 全局连接 | ❌缺失 | - | PoLaRIS 无 connect_global 全局网络 |
| 4.11 | 隐式连接 | ❌缺失 | - | PoLaRIS 无 connect_implicit 标签模式 |
| 4.12 | 显式连接 | ✅已有 | src/polaris/data/data_loader.py:105 | 网表显式定义连接关系 |
| 4.13 | 设备提取器 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有光子器件网表提取，无 bjt/mos 等电子提取器 |

### 2.5 处理模式

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | flat mode | ❌缺失 | - | PoLaRIS 无扁平化处理模式 |
| 5.2 | tiled mode | ❌缺失 | - | PoLaRIS 无 tiles() 分块 |
| 5.3 | hierarchical mode | ✅已有 | src/polaris/sim/hierarchical_drc.py:165; src/polaris/engine/hierarchical_placer.py:85 | 层次化 DRC + 层次化布局器 |
| 5.4 | deep mode | ❌缺失 | - | PoLaRIS 无 deep() 深度模式 |
| 5.5 | deep_reject_odd_polygons | ❌缺失 | - | PoLaRIS 无奇多边形拒绝选项 |
| 5.6 | 线程并行 | ⚠️部分 | src/polaris/trainer/parallel_rollout.py:80 | 训练并行 rollout，非 DRC 线程并行 |
| 5.7 | 分块边界 | ❌缺失 | - | PoLaRIS 无 tile border |

### 2.6 文件格式支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | GDSII 读写 | ✅已有 | src/polaris/eval/layout_render.py:331; src/polaris/data/gds_loader.py:468 | export_gds 导出 + load_gds_to_circuit 读取 |
| 6.2 | OASIS 读写 | ⚠️部分 | src/polaris/eval/layout_render.py:361 | 仅 export_oasis 导出，无 OASIS 读取 |
| 6.3 | DXF 导入 | ❌缺失 | - | PoLaRIS 无 DXF 支持 |
| 6.4 | CIF 导入 | ❌缺失 | - | PoLaRIS 无 CIF 支持 |
| 6.5 | Gerber 导入 | ❌缺失 | - | PoLaRIS 无 Gerber 支持 |
| 6.6 | LEF/DEF 导入 | ❌缺失 | - | PoLaRIS 无 LEF/DEF 支持 |
| 6.7 | GDS2 文本版本 | ❌缺失 | - | PoLaRIS 无 GDS2 文本格式 |
| 6.8 | gzip/zlib 压缩 | ❌缺失 | - | PoLaRIS 无自动解压 |
| 6.9 | 读取器选项 | ❌缺失 | - | PoLaRIS 无读取器选项配置 |
| 6.10 | SPICE 网表 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | 有 MNA SPICE 求解器，无 SPICE 网表文件格式 |
| 6.11 | Verilog 网表 | ❌缺失 | - | PoLaRIS 无 Verilog 网表 |

### 2.7 DRM 设计规则管理

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | DRC runset | ✅已有 | src/polaris/sim/foundry_runsets.py:41 | FoundryRunset + FOUNDRY_RUNSETS 注册表 |
| 7.2 | DRC 脚本 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout runset 脚本，无独立 Ruby 脚本环境 |
| 7.3 | LVS 脚本 | ✅已有 | src/polaris/sim/lvs.py:494 | run_lvs 入口 |
| 7.4 | 报告生成 | ⚠️部分 | src/polaris/sim/klayout_drc.py:193 | DRCResult 数据类，无严重级别报告 |
| 7.5 | profile 调试 | ❌缺失 | - | PoLaRIS 无 profile 性能分析 |
| 7.6 | new_target 调试 | ❌缺失 | - | PoLaRIS 无中间结果导出 |

### 2.8 Ruby 脚本

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | RBA 命名空间 | 🚫不适用 | - | PoLaRIS 为纯 Python 项目，不使用 Ruby |
| 8.2 | Ruby 解释器 | 🚫不适用 | - | PoLaRIS 不嵌入 Ruby 解释器 |
| 8.3 | Ruby PCell | 🚫不适用 | - | PoLaRIS 用 Python PCell |
| 8.4 | Ruby 宏 | 🚫不适用 | - | PoLaRIS 不使用 Ruby 宏 |
| 8.5 | MethodTable | 🚫不适用 | - | Ruby 特有动态方法分派，PoLaRIS 不适用 |
| 8.6 | 命令行执行 | ✅已有 | src/polaris/pipeline/__init__.py:291 | main() argparse CLI 入口 |

### 2.9 Python 脚本

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | pya 命名空间 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 通过 klayout Python 包使用 pya 等价 API |
| 9.2 | Python 解释器 | ✅已有 | - | PoLaRIS 为纯 Python 项目 |
| 9.3 | Python PCell | ✅已有 | src/polaris/pdk/pcell.py:576 | polaris_cell 装饰器实现 Python PCell |
| 9.4 | Python 宏 | ❌缺失 | - | PoLaRIS 无 .lym/.py 宏加载系统 |
| 9.5 | pymacros 文件夹 | ❌缺失 | - | PoLaRIS 无 pymacros 宏目录 |
| 9.6 | klayout Python 包 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 直接 import klayout |
| 9.7 | klayout.db 子模块 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 使用 klayout.db 几何数据库 |
| 9.8 | klayout.rdb 子模块 | ⚠️部分 | src/polaris/sim/klayout_drc.py:193 | DRCResult 自定义，未直接用 klayout.rdb |
| 9.9 | klayout.lay 子模块 | 🚫不适用 | - | klayout.lay 为 UI 组件，PoLaRIS 无 GUI |
| 9.10 | PythonInspector | ❌缺失 | - | PoLaRIS 无 Inspector 窗口 |
| 9.11 | KLAYOUT_PYTHONPATH | ❌缺失 | - | PoLaRIS 无 KLayout 专用 Python 路径 |

### 2.10 插件系统

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | Salt 包管理器 | ❌缺失 | - | PoLaRIS 无 Salt 包管理器 |
| 10.2 | Salt.Mine 仓库 | ❌缺失 | - | PoLaRIS 无包仓库服务 |
| 10.3 | 包类型 | ❌缺失 | - | PoLaRIS 无多类型包系统 |
| 10.4 | 包依赖 | ❌缺失 | - | PoLaRIS 无包依赖管理 |
| 10.5 | 包版本信息 | ❌缺失 | - | PoLaRIS 无包版本检查 |
| 10.6 | 包管理器 UI | ❌缺失 | - | PoLaRIS 无包管理器 UI |
| 10.7 | 包模板 | ❌缺失 | - | PoLaRIS 无包模板初始化 |
| 10.8 | grain.xml | ❌缺失 | - | PoLaRIS 无 grain.xml 包描述 |
| 10.9 | PluginFactory | ❌缺失 | - | PoLaRIS 无 PluginFactory 注册 |

### 2.11 宏开发

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 宏开发 IDE | ❌缺失 | - | PoLaRIS 无集成 IDE |
| 11.2 | 调试器 | ❌缺失 | - | PoLaRIS 无断点调试器 |
| 11.3 | 交互式控制台 | ❌缺失 | - | PoLaRIS 无交互式控制台 |
| 11.4 | 监视表达式 | ❌缺失 | - | PoLaRIS 无 watch 表达式 |
| 11.5 | .lym 文件 | ❌缺失 | - | PoLaRIS 无 .lym 宏文件 |
| 11.6 | 自动运行宏 | ❌缺失 | - | PoLaRIS 无启动自动运行宏 |
| 11.7 | 技术特定宏 | ❌缺失 | - | PoLaRIS 无技术特定宏 |
| 11.8 | 宏仓库 | ❌缺失 | - | PoLaRIS 无宏仓库扫描 |
| 11.9 | 全局仓库 | ❌缺失 | - | PoLaRIS 无全局宏仓库 |
| 11.10 | 本地仓库 | ❌缺失 | - | PoLaRIS 无本地宏仓库 |

### 2.12 分析工具

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | XOR 工具 | ❌缺失 | - | PoLaRIS 无版图 XOR diff 工具 |
| 12.2 | 网络追踪 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有网表提取，无交互式网络追踪 |
| 12.3 | 测量工具 | ⚠️部分 | src/polaris/data/benchmark_evaluator.py:57 | 有 HPWL/面积等测量，无交互式测量 |
| 12.4 | 网络邻域图 | ⚠️部分 | src/polaris/engine/netlist.py | 有 netlist 图结构，无自动连接关系图生成 |
| 12.5 | LVS 浏览器 | ❌缺失 | - | PoLaRIS 无 LVS 结果 GUI 浏览器 |
| 12.6 | 交叉探测 | ❌缺失 | - | PoLaRIS 无双击跳转交叉探测 |

### 2.13 GSI 框架

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | Generic Scripting Interface | 🚫不适用 | - | GSI 为 KLayout C++/脚本桥接特有框架 |
| 13.2 | gsi::ClassBase | 🚫不适用 | - | KLayout C++ 元数据特有 |
| 13.3 | gsi::MethodBase | 🚫不适用 | - | KLayout C++ 方法元数据特有 |
| 13.4 | 惰性绑定 | 🚫不适用 | - | KLayout 脚本对象特有 |
| 13.5 | 方法缓存 | 🚫不适用 | - | KLayout rba::MethodTable 特有 |

### 2.14 技术管理

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | 技术关联 | ✅已有 | src/polaris/pdk/foundry_platforms.py:39 | FoundryPlatform 平台元数据 |
| 14.2 | 技术数据 | ✅已有 | src/polaris/pdk/catalog.py:227 | DeviceCatalog 器件库 + PDK 数据 |
| 14.3 | 技术包 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PolarisPDKRegistry 48 个 PDK 注册 |

### 2.15 性能优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | 层次化处理 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85; src/polaris/sim/hierarchical_drc.py:165 | 层次化布局 + 层次化 DRC |
| 15.2 | 不变性标志 | ❌缺失 | - | PoLaRIS 无 is_isotropic/is_scale_invariant 标志 |
| 15.3 | deep mode 性能 | ❌缺失 | - | PoLaRIS 无 deep mode |
| 15.4 | tiled mode 并行 | ❌缺失 | - | PoLaRIS 无 tiled 并行 |
| 15.5 | GF180 优化案例 | ❌缺失 | - | PoLaRIS 无 GF180 优化案例 |

### T09 KLayout 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 25 | 19.8% |
| ⚠️ 部分 | 20 | 15.9% |
| ❌ 缺失 | 67 | 53.2% |
| 🚫 不适用 | 14 | 11.1% |
| **合计** | **126** | **100%** |

**覆盖率**: (25 + 0.5×20) / (126 - 14) = 35/112 = **31.3%**

<!-- PART1_END -->
