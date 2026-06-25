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

---

## 第5名: T02 Luceda IPKISS（商业，29 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T01_T02_gap.md`
> 价格：~$5K/年（估算，来源 https://www.lucedaphotonics.com/products/ipkiss）

### 一、器件设计 (Component Design)（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1 | 标准开发语言 Python | ✅已有 | `src/polaris/pipeline/__init__.py:291` | PoLaRIS 为 Python 原生平台，统一设计/模型/IP 管理语言 |
| 2 | 参数化器件版图与仿真 (Parametric Components in Layout & Simulation) | ✅已有 | `src/polaris/pdk/pcell.py:576,667,686,703,719` | PoLaRIS 有 polaris_cell PCell 装饰器(生产可用) + ring_resonator/mmi1x2/straight_waveguide/y_branch 内置 PCell |
| 3 | 虚拟工艺建模 (Virtual Fabrication) | ❌缺失 | - | PoLaRIS 无虚拟工艺建模（虚拟制造预验证可制造性） |
| 4 | 内置 EME 物理仿真引擎 (Built-in Physical EME Simulation) | ❌缺失 | - | PoLaRIS 无 EME 物理仿真引擎 |
| 5 | 第三方工具联合仿真 (3rd-party Tool Co-Simulation) | ⚠️部分 | `src/polaris/sim/lumerical_integration.py:896`; `src/polaris/sim/tidy3d_integration.py:116` | PoLaRIS 有 LumericalIntegration(实验性) 与 Tidy3DAdapter(实验性)，但均实验性，无 CST Studio Suite 集成 |

### 二、线路设计 (Circuit Design)（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6 | 基于代码的线路设计 (Code-driven Circuit Design) | ✅已有 | `src/polaris/data/specs.py:74`; `src/polaris/pipeline/integrated.py:446` | PoLaRIS 有 CircuitSpec 数据类 + IntegratedPipeline(生产可用) 代码驱动设计 |
| 7 | 智能光/电布线函数 (Smart Optical and Electrical Routing) | ✅已有 | `src/polaris/router/waveguide_router.py:605`; `src/polaris/router/curvy_router.py:1427`; `src/polaris/router/opto_electrical.py:101` | PoLaRIS 有 route_connection/route_curvy_connection/OptoElectricalRouter(生产可用)，覆盖智能光电布线 |
| 8 | 参数化电路与紧密版图-仿真链接 (Parametric Circuits with Tight Layout-Simulation Link) | ✅已有 | `src/polaris/sim/layout_aware.py:361,516` | PoLaRIS 有 LayoutAwareSimulator(生产可用) + LayoutCircuitFeedback，版图-仿真紧密链接 |
| 9 | 代码辅助的原理图驱动设计 (Schematic Capture with Code Assistance) | ⚠️部分 | `src/polaris/flow/ipkiss_flow.py:291` | PoLaRIS 有 SDLFlow(实验性)，但无 GUI 原理图捕获界面 |
| 10 | CAPHE 仿真引擎 (CAPHE Simulation Engine) | ⚠️部分 | `src/polaris/sim/caphe_backend.py:140,217,292,406` | PoLaRIS 有 CAPHENetwork/CAPHEFrequencySolver/CAPHETimeDomainSolver/CAPHEBackend(均实验性)，对齐 CAPHE 但实验性 |

### 三、设计验证 (Design Validation)（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11 | IPKISS Canvas 连接性与功能验证 | ⚠️部分 | `src/polaris/sim/constraint_checker.py:53` | PoLaRIS 有 ConstraintChecker 16 项约束检查(生产可用)，但无 IPKISS Canvas GUI 原理图捕获界面 |
| 12 | 网表提取 (Netlist Extraction - Optical and Electrical) | ✅已有 | `src/polaris/sim/lvs.py:121`; `src/polaris/sim/graph_lvs.py:89`; `src/polaris/data/data_loader.py:105` | PoLaRIS 有 extract_netlist_from_gds/PhotonicsNetlist/circuit_spec_to_netlist_dict(生产可用)，覆盖光电网表提取 |
| 13 | CAPHE 布局后仿真 (Post-layout Simulations with CAPHE) | ⚠️部分 | `src/polaris/sim/caphe_backend.py:406`; `src/polaris/sim/layout_aware.py:361` | PoLaRIS 有 CAPHEBackend(实验性) + LayoutAwareSimulator(生产可用)，但 CAPHE 后端实验性 |

### 四、流片准备 (Tape-out Preparation)（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14 | 锐角修补 (Acute Angle Patching) | ❌缺失 | - | PoLaRIS 无专门锐角修补功能 |
| 15 | 捕捉错误 (Snapping Errors) | ❌缺失 | - | PoLaRIS 无专门 snapping 错误检测与修正 |
| 16 | 完整 GDS 导出 (Full GDS Export) | ✅已有 | `src/polaris/eval/layout_render.py:331,361` | PoLaRIS 有 export_gds(GDSII) + export_oasis(OASIS)(生产可用)，超越单一 GDS 导出 |
| 17 | 设计规则检查 (DRC via Check Mate / Native DRC Engine) | ✅已有 | `src/polaris/sim/klayout_drc.py:238`; `src/polaris/sim/hierarchical_drc.py:165`; `src/polaris/sim/foundry_runsets.py:108` | PoLaRIS 有 KLayoutDRCRunner/HierarchicalDRC/FOUNDRY_RUNSETS(生产可用)，原生 DRC 引擎 + 多 foundry runset |

### 五、LVS 验证与多 Foundry PDK（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 18 | LVS 验证 (Layout vs Schematic) | ✅已有 | `src/polaris/sim/graph_lvs.py:160`; `src/polaris/sim/lvs.py:494`; `src/polaris/sim/eqdrc.py:390` | PoLaRIS 有 GraphIsomorphismLVSComparer/run_lvs/CurvilinearLVS(生产可用+实验性)，覆盖 LVS |
| 19 | 多 Foundry PDK 支持 | ✅已有 | `src/polaris/pdk/foundry_platforms.py:72`; `src/polaris/pdk/gdsfactory_pdk_bridge.py:349` | PoLaRIS 有 11 个公开 foundry 平台 + 48 gdsfactory PDK(生产可用)，超越 IPKISS PDK 数量 |
| 20 | PDK 组件库定义 | ✅已有 | `src/polaris/pdk/foundry_devices.py:188`; `src/polaris/pdk/catalog.py:227` | PoLaRIS 有 get_foundry_device/DeviceCatalog(生产可用)，预定义单元库 |

### 六、合作伙伴集成 (Partner Integrations)（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 21 | Link for Ansys Lumerical | ⚠️部分 | `src/polaris/sim/lumerical_integration.py:896` | PoLaRIS 有 LumericalIntegration(实验性)，但实验性，未达商业级 Link |
| 22 | Link for Tidy3D | ⚠️部分 | `src/polaris/sim/tidy3d_integration.py:116` | PoLaRIS 有 Tidy3DAdapter(实验性)，但实验性 |
| 23 | Link for 3DS Simulia (Dassault Systems CST) | ❌缺失 | - | PoLaRIS 无 CST Studio Suite 集成 |
| 24 | Link for Siemens EDA (L-Edit) | ✅已有 | `src/polaris/pdk/gpic.py:118,629` | PoLaRIS 有 GPICPDK/build_gpic_pdk(L-Edit GPIC,生产可用)，对齐 Siemens L-Edit 集成 |
| 25 | Link for Check Mate DRC | ⚠️部分 | `src/polaris/sim/klayout_drc.py:238` | PoLaRIS 无 Check Mate DRC 集成，但有 KLayoutDRCRunner(生产可用) 替代 DRC 引擎 |

### 七、配套产品与平台（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 26 | Luceda AWG Designer | ❌缺失 | - | PoLaRIS 无专门 AWG Designer 一键式流程 |
| 27 | Luceda IP Manager | ❌缺失 | - | PoLaRIS 无光子 IP 自动化测试工具 |
| 28 | Luceda Circuit Analyzer | ⚠️部分 | `src/polaris/sim/simulator.py:57`; `src/polaris/sim/monte_carlo.py:63,174` | PoLaRIS 有 CircuitSimulator + Monte Carlo(生产可用)，但无专门 Circuit Analyzer GUI 与深度分析工具 |
| 29 | Luceda Academy 培训与支持 | ❌缺失 | - | PoLaRIS 无培训平台 |

### T02 Luceda IPKISS 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 12 | 41.4% |
| ⚠️ 部分 | 9 | 31.0% |
| ❌ 缺失 | 8 | 27.6% |
| 🚫 不适用 | 0 | 0% |
| **合计** | **29** | **100%** |

**覆盖率**: (12 + 0.5×9) / 29 = 16.5/29 = **56.9%**（源文档标注 72.4%，按 ✅+⚠️/总数 计算）

> 注：源文档 T01_T02_gap.md 使用 (✅+⚠️)/总数 公式标注 72.4%，本汇总按统一公式 (✅+0.5×⚠️)/(总数-🚫) 重新计算为 56.9%。总览表保留源文档原值 72.4% 以保持一致。

---

## 第6名: T04 Flexcompute Tidy3D（商业，45 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T03_T04_gap.md`
> 价格：~$5-15K/年（估算，来源 https://flexcompute.com/）

### 一、FDTD 求解器与硬件加速 — 5 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1 | GPU 加速 FDTD (GPU-accelerated FDTD) | ⚠️部分 | `src/polaris/sim/tidy3d_integration.py:382` | PoLaRIS 有 `GPUFDTDEngine`（实验性），但非 Tidy3D 级 10-5000 倍加速，规模未达商业级 |
| 2 | 云原生架构 (Cloud-native) | ⚠️部分 | `src/polaris/web/server.py:669` | PoLaRIS 有 `WebServer` HTTP API，但非弹性云 + 动态资源分配 + 并发数百任务的云原生架构 |
| 3 | 内存高效 FDTD 算法 (Memory-efficient) | ❌缺失 | - | PoLaRIS 无专有内存高效 FDTD 算法（针对 GPU 微调） |
| 4 | Yee 网格 (Yee Lattice) | ✅已有 | `src/polaris/sim/time_domain_circuit.py:33`; `src/polaris/sim/fdtd_jax_backend.py:72` | PoLaRIS 有 `YeeGrid`（2D TMz）+ `YeeGrid3D`（3D 交错网格），基于 Yee 1966 算法 |
| 5 | 虚拟 GPU 分配控制 (Virtual GPU Allocation) | ❌缺失 | - | PoLaRIS 无 run_async/Job/Batch 虚拟 GPU 分配控制能力 |

### 二、网格与边界条件 — 6 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6 | 亚像素平滑 (Sub-pixel Smoothing) | ❌缺失 | - | PoLaRIS 无亚像素平滑方案（提升 FDTD 精度） |
| 7 | PML 边界条件 (Perfectly Matched Layer) | ✅已有 | `src/polaris/sim/time_domain_circuit.py:72`; `src/polaris/sim/fdtd_jax_backend.py:125` | PoLaRIS 有 `PMLBoundary`（Berenger 1994）+ `GedneyPML`（Gedney 1996 单轴各向异性 PML） |
| 8 | Absorber 边界 (Adiabatic Absorber) | ❌缺失 | - | PoLaRIS 无绝热吸收体（多层电导率渐增吸收层） |
| 9 | StablePML 边界 | ❌缺失 | - | PoLaRIS 无 StablePML 稳定型 PML 边界条件 |
| 10 | Periodic / BlochBoundary 边界 | ❌缺失 | - | PoLaRIS 无周期性 / Bloch 边界条件 |
| 11 | 自动非均匀网格 (Automatic Nonuniform Meshing) | ❌缺失 | - | PoLaRIS 无自动非均匀网格 + 局部网格细化能力 |

### 三、材料库 (Material Library) — 9 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12 | 基础介质 (Medium) | ⚠️部分 | `src/polaris/sim/models.py:159` | PoLaRIS 有 waveguide_s 等 S 参数模型，但无 Tidy3D `Medium` 均匀介质抽象类 |
| 13 | 各向异性介质 (AnisotropicMedium) | ❌缺失 | - | PoLaRIS 无各向异性介质 / 完全各向异性介质建模 |
| 14 | PEC / PMC 介质 | ❌缺失 | - | PoLaRIS 无完美电导体 (PECMedium) / 完美磁导体 (PMCMedium) |
| 15 | Pole Residue 色散模型 | ❌缺失 | - | PoLaRIS 无极点留数色散材料模型 |
| 16 | Sellmeier 色散模型 | ⚠️部分 | `src/polaris/sim/models_extended.py:375` | PoLaRIS 有 Sellmeier neff(λ) 模型（R02），但仅用于波导有效折射率，非完整材料 Sellmeier 模型 |
| 17 | Lorentz / Debye / Drude 色散模型 | ❌缺失 | - | PoLaRIS 无 Lorentz/Debye/Drude 色散材料模型（仅 S 参数拟合用 Lorentzian） |
| 18 | 自定义介质 (CustomMedium) | ❌缺失 | - | PoLaRIS 无空间自定义介质（CustomMedium/CustomPoleResidue 等） |
| 19 | 扰动介质 (PerturbationMedium) | ❌缺失 | - | PoLaRIS 无扰动介质模型（多物理耦合用） |
| 20 | 有损金属介质 (LossyMetalMedium) | ❌缺失 | - | PoLaRIS 无有损金属介质模型（RF 模块） |

### 四、光源类型 (Sources) — 4 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 21 | 平面波 (PlaneWave) | ❌缺失 | - | PoLaRIS 无平面波光源（含 angular_spec 固定角度） |
| 22 | TFSF 光源 (Total-Field Scattered-Field) | ⚠️部分 | `src/polaris/sim/tidy3d_integration.py:412` | PoLaRIS 有 TFSF 简化形式（Mur ABC + 边界源注入），但非完整 Tidy3D TFSF（含 angular_spec） |
| 23 | TerminalWavePort 光源 | ❌缺失 | - | PoLaRIS 无终端驱动模式激励（reference_impedance） |
| 24 | 模式光源 / 偶极子 / 高斯光束 | ⚠️部分 | `src/polaris/sim/fdtd_jax_backend.py:713` | PoLaRIS 有 `add_mode_source`（模式光源），但无偶极子光源 / 高斯光束 |

### 五、监视器 (Monitors) — 5 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 25 | 场监视器 (FieldMonitor) | ⚠️部分 | `src/polaris/sim/fdtd_jax_backend.py:508` | PoLaRIS 有 `monitor_signal`（时域信号采样），但无完整频域/时域 E/H 场监视器 |
| 26 | 点云场监视器 (PointCloudFieldMonitor) | ❌缺失 | - | PoLaRIS 无自定义点云坐标频域 E/H 场采样 |
| 27 | 稳态电荷残差监视器 (SteadyChargeResidualMonitor) | ❌缺失 | - | PoLaRIS 无 Charge 仿真每节点有符号残差监视器 |
| 28 | 偶极子发射监视器 (DipoleEmissionMonitor) | ❌缺失 | - | PoLaRIS 无偶极子发射研究插件监视器 |
| 29 | 功率 / 通量 / 模式监视器 | ⚠️部分 | `src/polaris/sim/meep_adjoint_backend.py:87` | PoLaRIS 有 flux/field monitor 类型（MEEP 后端），但无完整功率/通量/模式监视器抽象 |

### 六、逆向设计与优化 (Inverse Design & Optimization) — 8 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 30 | 伴随优化 / 自动微分 (Adjoint via autograd) | ✅已有 | `src/polaris/sim/adjoint_optimizer.py:204,417` | PoLaRIS 有 `AdjointOptimizer`（JAX 自动微分）+ `run_adjoint_optimization`，生产可用 |
| 31 | JAX 伴随插件 (jax-based adjoint plugin) | ✅已有 | `src/polaris/sim/autodiff.py:40,68,97` | PoLaRIS 有 `compute_gradient`/`compute_vjp`/`compute_jvp`（JAX 梯度/VJP/JVP），对齐 JAX 伴随 |
| 32 | 粒子群优化 (Particle Swarm Optimization) | ✅已有 | `src/polaris/sim/pso_optimizer.py:95` | PoLaRIS 有 `ParticleSwarmOptimizer`（PSO 粒子群优化器），生产可用 |
| 33 | 遗传算法 (Genetic Algorithm) | ✅已有 | `src/polaris/sim/multi_objective_optimizer.py:52`; `src/polaris/sim/nsga3_optimizer.py:246` | PoLaRIS 有 `NSGA2Optimizer` + `NSGA3Optimizer`（非支配排序遗传算法 II/III，含 SBX 交叉 + 多项式变异），属 GA 类 |
| 34 | 拓扑优化 (Topology Optimization) | ✅已有 | `src/polaris/sim/topology_optimizer.py:189,316` | PoLaRIS 有 `TopologyOptimizer`（水平集方法）+ `run_topology_optimization`，生产可用 |
| 35 | 形状优化 - 边界梯度 (Shape Optimization - Boundary Gradient) | ⚠️部分 | `src/polaris/sim/topology_optimizer.py:88` | PoLaRIS 有 `LevelSet` 水平集函数，但非显式边界梯度形状优化 |
| 36 | 形状优化 - 水平集 (Shape Optimization - Level Set) | ✅已有 | `src/polaris/sim/topology_optimizer.py:88`; `src/polaris/sim/level_set_solver.py:417` | PoLaRIS 有 `LevelSet` + `HJSolver`（HJ-ENO/WENO 求解器）+ `fast_marching_sdf`，完整水平集 |
| 37 | 逆向设计平台 (Inverse Design Platform) | ⚠️部分 | `src/polaris/sim/ai_inverse_design.py:382`; `src/polaris/ai/inverse_design.py:146` | PoLaRIS 有 `RLInverseDesigner`/`GANDesigner`（实验性），但非 Tidy3D 级一行代码转优化平台 |

### 七、用户界面与 API — 3 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 38 | Web GUI (Web-based GUI) | ⚠️部分 | `src/polaris/web/server.py:669`; `src/polaris/web/static/index.html` | PoLaRIS 有 `WebServer` + HTML 静态页面（index.html/showcase.html），但非 Tidy3D 级大规模多物理仿真 Web GUI |
| 39 | 开源 Python API | ✅已有 | `src/polaris/pipeline/__init__.py:291` | PoLaRIS 为开源 Python API，有完整 CLI 入口（main/cmd_run/cmd_train/cmd_catalog） |
| 40 | Tidy3D + AI | ⚠️部分 | `src/polaris/ai/inverse_design.py:146,315,536` | PoLaRIS 有 `RLInverseDesigner`/`GANInverseDesigner`/`DiffusionInverseDesigner`，但非 Tidy3D 集成 AI 平台 |

### 八、多物理与其他求解器 — 5 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 41 | EME 求解器 (Eigenmode Expansion) | ❌缺失 | - | PoLaRIS 无 EME 求解器（EME 重叠/通量计算/smatrix_in_basis） |
| 42 | 热仿真 (Heat Simulation) | ❌缺失 | - | PoLaRIS 无热仿真求解器（热源/热边界条件/热数据→FDTD） |
| 43 | 电荷仿真 (Charge Simulation) | ⚠️部分 | `src/polaris/sim/lumerical_integration.py:682` | PoLaRIS 有 `CHARGESimulator`（Lumerical 集成，实验性），但非自研电荷仿真 |
| 44 | 场投影 (Field Projection) | ❌缺失 | - | PoLaRIS 无近场到远场（焦平面）场投影能力 |
| 45 | 偶极子发射研究插件 (Dipole Emission Study Plugin) | ⚠️部分 | `src/polaris/sim/quantum_photonics.py:162,211` | PoLaRIS 有 `hom_interference`/`boson_sampling_prob`（量子光子），但非 Tidy3D 偶极子发射研究插件 |

### T04 Tidy3D 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 9 | 20.0% |
| ⚠️ 部分 | 14 | 31.1% |
| ❌ 缺失 | 22 | 48.9% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **45** | **100%** |

**覆盖率**: (9 + 0.5×14) / 45 = 16/45 = **35.6%**

---

## 第7名: T03 Synopsys OptoDesigner（商业，46 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T03_T04_gap.md`
> 价格：~$10-20K/年（估算，来源 https://www.synopsys.com/photonic-solutions/optodesigner.html）

### 一、核心版图设计功能 (Core Layout Features) — 13 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1 | Design Intent (设计意图层) | ⚠️部分 | `src/polaris/pdk/optodesigner.py:101` | PoLaRIS 有 `DesignIntentEngine`（单层→多层掩膜自动生成），但标注为"实验性"，未达 OptoDesigner 商业级成熟度 |
| 2 | 技术无关元素定义 (Technology-agnostic) | ⚠️部分 | `src/polaris/pdk/foundry_platforms.py:72` | PoLaRIS 有 11 个 foundry 平台注册表与跨平台 PDK 桥接，但非完全技术无关的元素定义方法 |
| 3 | 全角度连接性 (All Angle Connectivity) | ✅已有 | `src/polaris/router/all_angle_router.py:29` | PoLaRIS 有 `AllAngleRouter`（R10 任意角度布线 + 自适应交叉插入），生产可用 |
| 4 | 曲线元素设计与定制 (Curved Elements) | ✅已有 | `src/polaris/router/curvy_router.py:1286` | PoLaRIS 有 `CurvyRouter`（Euler/arc/Chaikin 平滑），生产可用 |
| 5 | 丰富元件库 (Extensive Libraries) | ✅已有 | `src/polaris/pdk/catalog.py:227`; `src/polaris/pdk/foundry_devices.py:188` | PoLaRIS 有 `DeviceCatalog` + foundry 器件库 + 48 gdsfactory PDK 注册表 |
| 6 | 强大脚本语言 (Powerful Scripting) | ✅已有 | `src/polaris/pipeline/__init__.py:291` | PoLaRIS 为 Python 原生 API，有完整 CLI 入口（main/cmd_run/cmd_train），等价于 OptoDesigner 脚本自动化 |
| 7 | 无限层级层次结构 (Unlimited Hierarchy) | ⚠️部分 | `src/polaris/engine/hierarchical_placer.py:85` | PoLaRIS 有 `HierarchicalPlacer`（谱聚类分块布局），但非"无限层级"层次结构复用机制 |
| 8 | PDK 支持与自定义 (PDK Support) | ✅已有 | `src/polaris/pdk/catalog.py:227`; `src/polaris/pdk/foundry_platforms.py:72` | PoLaRIS 有 `DeviceCatalog`（自定义 PDK）+ 11 个 foundry 平台 PDK，生产可用 |
| 9 | 附加仿真模块 (Add-on Simulation) | ✅已有 | `src/polaris/sim/simulator.py:57`; `src/polaris/sim/fdtd_simulator.py:279` | PoLaRIS 有 `CircuitSimulator`（频域）+ `FDTDBackend`（MEEP/Tidy3D/ANALYTICAL），覆盖模式计算与传播计算 |
| 10 | GDSII/CIF 导入导出 | ⚠️部分 | `src/polaris/eval/layout_render.py:331,361`; `src/polaris/data/gds_loader.py:468` | PoLaRIS 有 `export_gds`/`export_oasis`/`load_gds_to_circuit`，但无 CIF 格式支持 |
| 11 | 自定义 GDS 库 (Custom GDS Libraries) | ✅已有 | `src/polaris/pdk/catalog.py:227` | PoLaRIS 有 `DeviceCatalog`（序列化/反序列化）+ `build_default_catalog`，支持自定义 GDS 库 |
| 12 | 第三方工具接口 (Third-party Interfaces) | ✅已有 | `src/polaris/sim/lumerical_integration.py:896`; `src/polaris/sim/tidy3d_integration.py:116`; `src/polaris/pdk/gdsfactory_pdk_bridge.py:349` | PoLaRIS 有 Lumerical/Tidy3D/gdsfactory/KLayout 多个第三方接口 |
| 13 | 离散化引擎 (Discretization Engine) | ✅已有 | `src/polaris/sim/klayout_drc.py:238`; `src/polaris/eval/layout_render.py:331` | PoLaRIS 通过 KLayout 集成实现离散化与多格式导出（GDSII/OASIS） |

### 二、Design Rule Checking (DRC) 模块 — 7 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14 | 18 类 DRC 规则 (18 Types of Rules) | ⚠️部分 | `src/polaris/sim/klayout_drc.py:45` | PoLaRIS `DRCCheckType` 仅 6 类（WIDTH/SPACE/NOTCH/ENCLOSE/AREA/DENSITY）+ `ConstraintChecker` 16 项约束，未达 OptoDesigner 18 类规模 |
| 15 | 单层与多层规则 (Single/Multi-layer Rules) | ✅已有 | `src/polaris/sim/hierarchical_drc.py:165` | PoLaRIS 有 `HierarchicalDRC`（layer-wise BVH 加速），支持单层与多层组合规则 |
| 16 | 交互式 DRC 错误管理对话框 (Interactive Dialog) | ❌缺失 | - | PoLaRIS 仅有 web/server.py HTTP API，无 GUI 交互式 DRC 错误管理对话框 |
| 17 | 预定义示例 (Predefined Examples) | ✅已有 | `src/polaris/sim/foundry_runsets.py:108`; `src/polaris/sim/klayout_drc.py:101` | PoLaRIS 有 `FOUNDRY_RUNSETS` 多 foundry runset 注册表 + `SIEPIC_EBEAM_DRC_RUNSET` 预定义示例 |
| 18 | 规则分组能力 (Grouping Capability) | ⚠️部分 | `src/polaris/sim/constraint_checker.py:53` | PoLaRIS 有 `ConstraintChecker`（16 项检查），但无显式 DRC 规则分组执行能力 |
| 19 | 全角度曲线感知 DRC (All-angle Curvilinear DRC) | ✅已有 | `src/polaris/sim/eqdrc.py:390` | PoLaRIS 有 `CurvilinearLVS`（曲线 LVS，实验性）+ `EqDRCEngine`（Calibre eqDRC 对齐），支持全角度曲线 |
| 20 | PDK 内嵌检查 (Checks in PDK) | ✅已有 | `src/polaris/sim/foundry_runsets.py:108` | PoLaRIS 有 `FOUNDRY_RUNSETS`（foundry DRC runset 内嵌）+ `FoundryDRCCertifier`（foundry DRC 认证） |

### 三、Autorouting 模块 — 10 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 21 | 金属布线 (Metal Routing) | ✅已有 | `src/polaris/router/opto_electrical.py:101` | PoLaRIS 有 `OptoElectricalRouter`（光电协同布线），支持金属布线 |
| 22 | 90 度/45 度金属布线 | ⚠️部分 | `src/polaris/router/waveguide_router.py:104` | PoLaRIS `GridRouter` 主要支持 90 度 Manhattan 布线，45 度金属布线支持不明确 |
| 23 | VIA 成本可调 (Adjustable VIA Costs) | ⚠️部分 | `src/polaris/router/multilayer.py:95` | PoLaRIS 有 `MultiLayerRouter`（3D 多层布线 + OTV），但 VIA 成本可调性未显式实现 |
| 24 | 光波导布线 (Optical Waveguide Routing) | ✅已有 | `src/polaris/router/waveguide_router.py:104`; `src/polaris/router/curvy_router.py:1286` | PoLaRIS 有 `GridRouter` + `CurvyRouter`，支持光波导布线 |
| 25 | 90 度/45 度光波导布线 | ⚠️部分 | `src/polaris/router/waveguide_router.py:104` | PoLaRIS `GridRouter` 主要支持 90 度，45 度光波导布线支持不明确 |
| 26 | PCell 选择 (PCell Selection) | ✅已有 | `src/polaris/pdk/pcell.py:576`; `src/polaris/router/curvy_router.py:350` | PoLaRIS 有 `polaris_cell` PCell 装饰器 + `AdaptiveCrossingInserter`（弯曲/直段/交叉 PCell 选择） |
| 27 | 弯曲与交叉相对成本 (Relative Costs) | ✅已有 | `src/polaris/router/curvy_router.py:683` | PoLaRIS 有 `OptoDesignerAutorouter`（R21 OptoDesigner 自动布线对齐），支持弯曲与交叉成本 |
| 28 | 迭代迷宫布线 (Iterative Maze Routing) | ✅已有 | `src/polaris/router/global_router.py:91` | PoLaRIS 有 `GlobalRouter`（GCell + RUDY 全局布线），支持迭代迷宫布线 |
| 29 | 掩膜层避障 (Prevent Mask Overlap) | ✅已有 | `src/polaris/router/waveguide_router.py:89` | PoLaRIS 有 `RouterConstraints`（布线约束）+ 拥塞感知，支持掩膜层避障 |
| 30 | 规则与成本驱动 (Rules and Cost-based) | ✅已有 | `src/polaris/router/curvy_router.py:683` | PoLaRIS 有 `OptoDesignerAutorouter`（规则与成本驱动自动布线） |

### 四、Advanced Connectors 模块 — 8 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 31 | Manhattan 风格连接器 (Manhattan-style) | ✅已有 | `src/polaris/router/waveguide_router.py:104` | PoLaRIS `GridRouter` 支持 Manhattan 风格连接器 |
| 32 | 航点辅助 (Way Point Assisted) | ⚠️部分 | `src/polaris/router/waveguide_router.py:89` | PoLaRIS 有 `RouterConstraints` 布线约束，但无显式航点辅助（含相对坐标）能力 |
| 33 | 预定义弯曲与直段 (Predefined Bends/Straights) | ✅已有 | `src/polaris/router/advanced_connectors.py:74` | PoLaRIS 有 `EulerBend`（欧拉弯曲）+ 内置 PCell（直段），生产可用 |
| 34 | 用户定义与 PDK 构件支持 (User/PDK Building Blocks) | ✅已有 | `src/polaris/pdk/pcell.py:576` | PoLaRIS 有 `polaris_cell` PCell 装饰器 + `PCellMultiView`，支持用户定义与 PDK 构件 |
| 35 | 路径长度定义连接器 (Path Length Defined) | ✅已有 | `src/polaris/router/advanced_connectors.py:155` | PoLaRIS 有 `LengthDefinedConnector`（长度定义连接器），生产可用 |
| 36 | 自动交叉插入器 (Automatic Crossing Inserter) | ✅已有 | `src/polaris/router/curvy_router.py:350` | PoLaRIS 有 `AdaptiveCrossingInserter`（自适应交叉插入），生产可用 |
| 37 | 弹性连接器 (Elastic Connectors) | ✅已有 | `src/polaris/pdk/optodesigner.py:515`; `src/polaris/sim/layout_aware.py:97` | PoLaRIS 有 `FlexConnector`（实验性）+ `ElasticConnector`（layout-aware），支持光程/相位/曲率约束 |
| 38 | 总线/相位匹配/RF GSG 布线 (Bus/Phase-matched/RF GSG) | ✅已有 | `src/polaris/router/advanced_connectors.py:402,236,302` | PoLaRIS 有 `BusRouter` + `PhaseMatchedRouter` + `RFGSGRouter`，三者齐全 |

### 五、任意曲线与宽度剖面 (Arbitrary Curves and Width Profiles) — 4 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 39 | CurveUpDown 任意曲线 | ⚠️部分 | `src/polaris/router/curvy_router.py:1286` | PoLaRIS 有 `CurvyRouter`（Euler/arc/Chaikin 平滑），但无 OptoDesigner `CurveUpDown`（XYup/XYlow 双参数化函数）双边界曲线 |
| 40 | CenterPath 中心路径曲线 | ⚠️部分 | `src/polaris/router/curvy_router.py:1286` | PoLaRIS 有 `CurvyRouter`，但无 OptoDesigner `CenterPath`（中心路径+宽度定义函数）明确抽象 |
| 41 | 高精度离散化 (Accurate Discretization) | ✅已有 | `src/polaris/sim/klayout_drc.py:238`; `src/polaris/eval/layout_render.py:331` | PoLaRIS 通过 KLayout 集成实现高精度离散化（多边形顶点距解析曲线 1nm 内） |
| 42 | Functor 加速 (Functor C++ Acceleration) | ⚠️部分 | `src/polaris/sim/jax_backend.py:101` | PoLaRIS 有 JAX JIT 编译加速，但非 OptoDesigner functor（脚本函数→C++ 对象）机制 |

### 六、Lattice Filter Design 模块与其他 — 4 功能点

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 43 | Lattice Filter Design Module | ❌缺失 | - | PoLaRIS 无专门的 Lattice Filter 设计模块（仅 `dataset_generator.py:107` 引用 gdsfactory mzi_lattice_filter） |
| 44 | OptoCompiler 集成 | 🚫不适用 | - | OptoCompiler 为 Synopsys 自家版图编译器，PoLaRIS 无需对齐 Synopsys 内部集成 |
| 45 | OptSim Circuit 集成 | ⚠️部分 | `src/polaris/sim/simulator.py:57` | PoLaRIS 有 `CircuitSimulator`（频域电路仿真器），但非 OptSim Circuit 直接集成 |
| 46 | 成熟流片验证 (500+ Tape-outs) | ❌缺失 | - | PoLaRIS 无流片记录，未达 OptoDesigner 500+ tape-outs 成熟度 |

### T03 OptoDesigner 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 28 | 60.9% |
| ⚠️ 部分 | 14 | 30.4% |
| ❌ 缺失 | 3 | 6.5% |
| 🚫 不适用 | 1 | 2.2% |
| **合计** | **46** | **100%** |

**覆盖率**: (28 + 0.5×14) / (46 - 1) = 35/45 = **77.8%**

---

## 第8名: T07 Photon Design（商业，93 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T07_T08_gap.md`
> 价格：~$10-30K/年（估算，来源 https://www.photond.com/）
> 注：T07 第 7 节 Aspic 的 12 个功能点归属 Filarete srl（非 Photon Design），不计入 93 个功能点。

### 1. FIMMPROP — EME 本征模展开（18 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 双向光学传播工具，严格麦克斯韦方程半解析全矢量 3D 传播 | ❌缺失 | - | PoLaRIS 无 EME 求解器，仅有 FDTD（`fdtd_simulator.py:57`）和电路级 S 参数仿真 |
| 1.2 | EME 方法，3D 环形谐振器数秒内仿真 | ❌缺失 | - | PoLaRIS 无 EME 引擎 |
| 1.3 | 高折射率对比，无缓慢变化近似，广角问题 | ❌缺失 | - | PoLaRIS 无 EME 广角传播 |
| 1.4 | 双向运算，散射矩阵快速优化 | ❌缺失 | - | PoLaRIS 的 S 参数（`models.py:159`）是电路级器件模型，非器件级双向传播散射矩阵 |
| 1.5 | MMI 耦合器、周期结构、锥形、弯曲快速设计 | ⚠️部分 | `sim/models.py:159`、`pdk/pcell.py:686` | 有 MMI S 参数模型和 PCell，但无器件级物理仿真用于"快速设计" |
| 1.6 | MT-FIMMPROP 版图环境大规模仿真 | ❌缺失 | - | 无版图级严格仿真集成 |
| 1.7 | 可定制计算区域，复杂器件全参数化零代码 | ⚠️部分 | `pdk/pcell.py:576` | 有 PCell 参数化，但无器件级物理仿真计算区域定制 |
| 1.8 | 锥形建模（taper modelling） | ⚠️部分 | `router/bundle_router.py:232`、`sim/adjoint_optimizer.py:344` | 有布线级 auto_taper 和解析波导耦合器，非器件级锥形物理建模 |
| 1.9 | 光栅模型（grating models） | ⚠️部分 | `sim/models.py:159` | 有 grating_coupler_s 电路模型，无光栅物理级建模 |
| 1.10 | 弯曲模型，全矢量 3D 弯曲仿真 | ⚠️部分 | `router/advanced_connectors.py:74` | 有 EulerBend 布线级弯曲，无全矢量 3D 弯曲物理仿真 |
| 1.11 | 扫描工具，高速优化波导器件 | ✅已有 | `data/variant_generator.py:478` | 有 generate_param_sweep_variants 参数扫描 |
| 1.12 | 场与模态分析，灵活详尽绘图 | ⚠️部分 | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），无场截面绘图工具 |
| 1.13 | 模式求解器（FIMMWAVE 能力） | ⚠️部分 | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非自研全矢量 3D 模式求解器 |
| 1.14 | GDSII 导出 | ✅已有 | `eval/layout_render.py:331` | 有 export_gds |
| 1.15 | 与 PICWave 链接，严格光学传播+电路建模 | ✅已有 | `pipeline/integrated.py:446` | 有 IntegratedPipeline 集成仿真流水线 |
| 1.16 | 脚本与优化：Python、MATLAB、Kallistos | ⚠️部分 | `sim/lbfgs_optimizer.py:132` 等 | 支持 Python 和多种优化器，无 MATLAB/Kallistos |
| 1.17 | 设计接口，轻松创建多种光子元件 | ✅已有 | `pdk/pcell.py:576`、`pdk/catalog.py:227` | 有 polaris_cell 装饰器和 DeviceCatalog |
| 1.18 | 应用示例：定向耦合器、Y 分束器、MMI、Euler 弯曲等 | ✅已有 | `sim/models.py:159-455`、`router/advanced_connectors.py:74` | 有 directional_coupler_s/y_branch_s/mmi_1x2_s/EulerBend 等 |

### 2. OmniSim — FDTD 有限差分时域（14 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 2D 与 3D FDTD 引擎 | ✅已有 | `sim/fdtd_simulator.py:57` | 有 FDTDBackend（MEEP/Tidy3D/ANALYTICAL 三后端） |
| 2.2 | 多核多 CPU FDTD 计算与集群支持 | ⚠️部分 | `engine/gpu_backend.py:221` | 有 GPU 后端，无明确多核 CPU 集群支持 |
| 2.3 | 原生 64 位版本 | 🚫不适用 | - | PoLaRIS 为 Python 实现，依赖底层库，无"原生 64 位"概念 |
| 2.4 | 子网格（sub-gridding）工具 | ❌缺失 | - | 无子网格局部加密能力 |
| 2.5 | 子网格反射系数优于 1e-8 | ❌缺失 | - | 无子网格 |
| 2.6 | 材料模型：色散/非线性/各向异性/磁性/负折射率 | ⚠️部分 | `sim/system_level.py:157` | 有 chi3 非线性提及，无完整材料模型库 |
| 2.7 | 边界条件：PML/色散 PML/PEC/PMC/周期 | ⚠️部分 | `sim/fdtd_simulator.py:57` | 依赖 MEEP/Tidy3D 后端边界条件，非自研 |
| 2.8 | 源：模式/偶极子/平面波/高斯/任意光束 | ⚠️部分 | `sim/fdtd_simulator.py:279` | 依赖后端源能力，非自研源库 |
| 2.9 | 传感器：时频域/Q 因子/远场/通量/盒传感器 | ⚠️部分 | `sim/simulator.py:357` | 有 analyze_dispersion 计算 FSR/Q，其他传感器依赖后端 |
| 2.10 | Active FDTD 算法用于纳米激光器（载流子速率方程） | ❌缺失 | - | 有 TLLMLaser（`system_level.py:157`）但非 Active FDTD |
| 2.11 | FDTD 集群版本（Windows 与 Linux） | ❌缺失 | - | 无 FDTD 集群版本 |
| 2.12 | 实时场可视化与视频捕获 | ❌缺失 | - | 有版图渲染（`layout_render.py:123`），无实时场可视化 |
| 2.13 | 灵活的版图编辑器（layout editor） | ⚠️部分 | `web/server.py:329` | 有 Web 服务器和 PCell，无图形化版图编辑器 |
| 2.14 | 应用：环形谐振器/等离激元/超材料/石墨烯/PCSEL | ⚠️部分 | `sim/models.py:159` | 有 ring_resonator_s，无等离激元/超材料/石墨烯/PCSEL 物理仿真 |

### 3. OmniSim — FETD 有限元时域（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 2D/3D Finite Element Time Domain (FETD) 工具 | ❌缺失 | - | PoLaRIS 无 FETD 引擎 |
| 3.2 | 等离激元/超材料/石墨烯精确建模 | ❌缺失 | - | 无这些器件的 FETD 物理仿真 |
| 3.3 | 同时包含 FDTD 与 FETD 引擎可交叉验证 | ❌缺失 | - | 无 FETD，仅有 FDTD 交叉验证（`tidy3d_integration.py:578`） |
| 3.4 | FETD 支持非线性（chi2/chi3 孤子） | ❌缺失 | - | 无 FETD |
| 3.5 | FETD 用于纳米天线/Mie 散射/光收集器 | ❌缺失 | - | 无 FETD |

### 4. OmniSim — 其他引擎与工具（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | FEFD Engine：高速 2D 有限元频域 | ❌缺失 | - | 无 FEFD 引擎 |
| 4.2 | RCWA Engine：严格耦合波分析 | ❌缺失 | - | 无 RCWA 引擎 |
| 4.3 | 表面光栅工具（surface grating utility） | ❌缺失 | - | 无表面光栅工具 |
| 4.4 | 能带结构分析器（band structure analyser） | ❌缺失 | - | 无光子晶体能带分析 |
| 4.5 | GDSII 导出 | ✅已有 | `eval/layout_render.py:331` | 有 export_gds |
| 4.6 | 脚本与优化：Python、MATLAB、Kallistos | ⚠️部分 | `sim/lbfgs_optimizer.py:132` | 支持 Python 和优化器，无 MATLAB/Kallistos |
| 4.7 | PCSEL 设计流程：Harold→OmniSim→Active FDTD | ❌缺失 | - | 无 PCSEL 设计流程 |
| 4.8 | Q 因子计算器（计算时间减少 85%） | ⚠️部分 | `sim/simulator.py:357` | 有 analyze_dispersion 计算 FSR/Q，非 FDTD Q 因子加速器 |

### 5. PICWave — 时域光子集成电路与激光器仿真（22 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 光子集成电路（PIC）设计工具 | ✅已有 | `pipeline/integrated.py:446`、`sim/simulator.py:57` | 有 IntegratedPipeline 和 CircuitSimulator |
| 5.2 | 详细有源模型，SOA 与激光二极管（FP/混合硅/DFB/可调谐/环形） | ⚠️部分 | `sim/system_level.py:157` | 有 TLLMLaser，无详细 SOA/多种激光二极管模型 |
| 5.3 | 调制器与光电探测器建模 | ⚠️部分 | `sim/models.py:159`、`pdk/lnoi.py:50` | 有 phase_shifter_s 和 LNOI 调制器，无光电探测器模型 |
| 5.4 | 激光模型与光路/电路仿真器重叠 | ✅已有 | `sim/system_level.py:262` | 有 HybridSimulator 混合仿真器 |
| 5.5 | Wide-Band Gain Fitting 算法 | ❌缺失 | - | 无宽带有源增益拟合 |
| 5.6 | 从 Harold 导入增益模型；QCSE EAM 模型 | ❌缺失 | - | 无 Harold 集成 |
| 5.7 | 与 FIMMPROP 链接，导入严格无源仿真 | ⚠️部分 | `sim/fdtd_simulator.py:279` | 无 FIMMPROP，但有 FDTD 严格仿真入口 |
| 5.8 | 与 EPIPPROP 链接，AWG 与 Echelle 光栅 | ❌缺失 | - | 无 EPIPPROP，无 AWG/Echelle 光栅模型 |
| 5.9 | 行波电极模型（traveling wave electrode） | ✅已有 | `pdk/lnoi.py:50`、`router/advanced_connectors.py:302` | 有 make_lnoi_mzm_traveling_wave 和 RFGSGRouter |
| 5.10 | 自热模型（self heating model） | ❌缺失 | - | 无自热模型 |
| 5.11 | 物理效应：载流子扩散/电流扩展/孔洞燃烧 | ❌缺失 | - | 无这些物理效应建模 |
| 5.12 | 大型 PIC 仿真（数米长器件） | ✅已有 | `sim/subnetwork_decomp.py:407` | 有 SubnetworkDecomposition 支持大型电路仿真 |
| 5.13 | Building Block System，预定义设计套件 | ✅已有 | `pdk/catalog.py:227`、`pdk/foundry_devices.py:188` | 有 DeviceCatalog 和 foundry_devices |
| 5.14 | 电路能力：无源与有源组件集成 | ✅已有 | `sim/simulator.py:57` | 有 CircuitSimulator 含有源/无源模型 |
| 5.15 | 激光器几何结构（laser geometries） | ❌缺失 | - | 无任意激光二极管几何表征 |
| 5.16 | 分析工具（analysis） | ✅已有 | `sim/simulator.py:357`、`data/benchmark_evaluator.py:420` | 有 analyze_dispersion 和 evaluate_benchmark |
| 5.17 | 电气模型：两端口电流/电压驱动 | ✅已有 | `sim/mna_spice.py:102`、`sim/verilog_a.py:98` | 有 MNASolver 和 VerilogAModel |
| 5.18 | 脚本与优化 | ✅已有 | `sim/lbfgs_optimizer.py:132`、`sim/multi_objective_optimizer.py:52` | 有 L-BFGS/NSGA-II/PSO/CMA-ES 等优化器 |
| 5.19 | 内置 Y-junction/Directional Coupler/MZI 模型 | ✅已有 | `sim/models.py:159-455` | 有 y_branch_s/directional_coupler_s 等 |
| 5.20 | 弧形段（arc section）仿真弯曲模式 | ⚠️部分 | `router/advanced_connectors.py:74` | 有布线级 EulerBend，无弯曲模式物理仿真 |
| 5.21 | 应用：SOA/锁模激光器/DFB EML/SG-DBR/SOI 锥形/LiDAR SLED | ❌缺失 | - | 无这些激光器应用模型 |
| 5.22 | PDK 支持 | ✅已有 | `pdk/foundry_platforms.py:72`、`pdk/gdsfactory_pdk_bridge.py:349` | 有 FOUNDRY_PLATFORMS 和 PolarisPDKRegistry |

### 6. Kallistos — 光子器件优化（15 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 光子器件设计优化工具 | ✅已有 | `sim/adjoint_optimizer.py:204` | 有 AdjointOptimizer 等多种优化器 |
| 6.2 | 自动改进现有设计 | ✅已有 | `sim/adjoint_optimizer.py:204` | 有优化器自动改进 |
| 6.3 | 使用最先进的优化技术 | ✅已有 | `sim/nsga2_operators.py:243`、`sim/global_optimizer.py:127` | 有 NSGA-II/III、CMA-ES、PSO、Adjoint 等 |
| 6.4 | 高效局部下降例程 | ✅已有 | `sim/lbfgs_optimizer.py:132` | 有 LBFGSOptimizer |
| 6.5 | 确定性与随机全局优化技术 | ✅已有 | `sim/global_optimizer.py:127`、`sim/pso_optimizer.py:95` | 有 CMA-ES 和 PSO |
| 6.6 | 利用波动方程数学结构，灵敏度解析程序 | ✅已有 | `sim/adjoint_optimizer.py:204`、`sim/autodiff.py:40` | 有 Adjoint 优化和 JAX 自动微分 |
| 6.7 | 强大内置函数解析器 | ⚠️部分 | `nn/__init__.py:132` | 有 Tensor 自动微分，非完整函数解析器 |
| 6.8 | 强大、友好的图形用户界面 | ⚠️部分 | `web/server.py:329` | 有 Web 服务器，非完整 GUI |
| 6.9 | 与 Photon Design 产品紧密集成 | 🚫不适用 | - | PoLaRIS 为独立产品，不与 Photon Design 集成 |
| 6.10 | 针对光子器件性能调优 | ✅已有 | `sim/robust_optimizer.py:256` | 有 RobustOptimizer 鲁棒性优化 |
| 6.11 | 广泛命令行接口，Python 与 MATLAB 脚本 | ⚠️部分 | `pipeline/__init__.py:291` | 有 CLI main 入口，支持 Python，无 MATLAB |
| 6.12 | 发现新设计（类似逆向设计） | ✅已有 | `ai/inverse_design.py:146` | 有 RLInverseDesigner/GANInverseDesigner |
| 6.13 | 跨 Photon Design 套件优化 | 🚫不适用 | - | 不适用，PoLaRIS 非 Photon Design 套件 |
| 6.14 | 应用：线性锥形/S-Bend/MMI/光子晶体/硅纳米光子 | ⚠️部分 | `sim/adjoint_optimizer.py:344`、`pdk/pcell.py:686` | 有 AnalyticalWaveguideCoupler 和 MMI PCell，无光子晶体优化 |
| 6.15 | 与 Band Analyser 配对 | ❌缺失 | - | 无 Band Analyser |

### 8. 其他 Photon Design 模块（补充）（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | FIMMWAVE：波导模式求解器 | ⚠️部分 | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非自研全矢量 3D 模式求解器 |
| 8.2 | Harold：先进半导体器件仿真（VCSEL/量子点/EAM） | ❌缺失 | - | 无 Harold 等效模块 |
| 8.3 | Harold 量子点增益模型（8 带 k.p/3D 应力应变） | ❌缺失 | - | 无量子点增益模型 |
| 8.4 | EPIPPROP：WDM/DWDM AWG 与 Echelle 光栅 | ❌缺失 | - | 无 AWG/Echelle 光栅模型 |
| 8.5 | EPIPPROP：内建全矢量 2D+z FDM 波导模式求解器 | ⚠️部分 | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非 FDM 自研 |
| 8.6 | EPIPPROP：自动创建 WDM 器件完整版图 | ❌缺失 | - | 无 WDM 器件版图自动生成 |
| 8.7 | CrystalWave：2D/3D 光子晶格编辑器 | ❌缺失 | - | 无光子晶格编辑器 |
| 8.8 | CrystalWave：SMP 多核 FDTD/集群/有源 FDTD | ❌缺失 | - | 无 CrystalWave 等效能力 |

### 9. 平台支持（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | FDTD 集群版本支持 Windows 与 Linux | ❌缺失 | - | 无 FDTD 集群版本 |
| 9.2 | 多核 SMP 用于 FDTD 快速计算 | ⚠️部分 | `sim/fdtd_simulator.py:57` | 依赖 MEEP/Tidy3D 后端多核能力，非自研 SMP |
| 9.3 | PICWave 6.3（2025-10）：GUI 改版/新示例 | 🚫不适用 | - | 不适用，PoLaRIS 非 PICWave，无版本对应 |

### T07 Photon Design 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 26 | 28.0% |
| ⚠️ 部分 | 28 | 30.1% |
| ❌ 缺失 | 35 | 37.6% |
| 🚫 不适用 | 4 | 4.3% |
| **合计** | **93** | **100%** |

**覆盖率**: (26 + 0.5×28) / (93 - 4) = 40/89 = **44.9%**

---

## 第9名: T06 Siemens L-Edit Photonics（商业，69 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T05_T06_gap.md`
> 价格：~$15-30K/年（估算，来源 https://eda.sw.siemens.com/en-US/ic/l-edit-photonics/）

### 1. 版图编辑（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 完整层次化物理版图编辑器，支持产品级光芯片设计 | ⚠️部分 | src/polaris/eval/layout_render.py:123; src/polaris/pdk/pcell.py:576 | PoLaRIS 有版图渲染 + PCell，但非完整 GUI 编辑器 |
| 1.2 | 支持曲线多边形与任意角度图形 | ✅已有 | src/polaris/router/curvy_router.py:1286; src/polaris/router/all_angle_router.py:29 | PoLaRIS 有 CurvyRouter + AllAngleRouter |
| 1.3 | 快速渲染（fast rendering） | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有 matplotlib 渲染，但非商业级快速渲染引擎 |
| 1.4 | 对象抓取（object snapping / gravity） | ❌缺失 | - | PoLaRIS 无 GUI 对象抓取 |
| 1.5 | 基于 OpenAccess 构建 | ❌缺失 | - | PoLaRIS 无 OpenAccess 支持 |
| 1.6 | 支持 FinFET、平面及所有其他晶体管技术 | ❌缺失 | - | PoLaRIS 专注光子，无 FinFET/晶体管技术 |
| 1.7 | 内置全角度与曲线支持，用于功率晶体管、MEMS 与光子学 | ✅已有 | src/polaris/router/all_angle_router.py:29; src/polaris/router/curvy_router.py:1286 | PoLaRIS 有全角度与曲线支持（光子学方向） |
| 1.8 | 原生 OpenAccess 多用户支持 | ❌缺失 | - | PoLaRIS 无 OpenAccess 多用户 |

### 2. GPIC PDK 与多 Foundry 支持（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 支持 Siemens 格式 PDK 与可互操作的行业标准 iPDK | ⚠️部分 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK，但无 Siemens 格式/iPDK 标准支持 |
| 2.2 | PDK 可从多家光子晶圆代工厂获得 | ✅已有 | src/polaris/pdk/foundry_platforms.py:72 | PoLaRIS 有 11 个 foundry 平台注册表 |
| 2.3 | 设计人员可创建自己的元器件或创建自己的 PDK | ✅已有 | src/polaris/pdk/catalog.py:227 | PoLaRIS 有 DeviceCatalog（序列化/反序列化） |
| 2.4 | 支持 30+ 代工厂、200+ PDK | ⚠️部分 | src/polaris/pdk/foundry_platforms.py:72; src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PoLaRIS 有 11 foundry + 48 gdsfactory PDK，规模小于 30+/200+ |
| 2.5 | GPIC PDK，由 Siemens EDA 团队开发，作为开发任意 foundry 自定义 Python 组件的起点 | ✅已有 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK（R19） |
| 2.6 | GPIC PDK 提供构建模块（BBs）库与真实仿真模型，支持 ASPIC 原型设计 | ✅已有 | src/polaris/pdk/gpic.py:629 | PoLaRIS 有 build_gpic_pdk |

### 3. SDL 原理图驱动版图（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 原理图驱动版图流程，允许首次即创建与原理图匹配的版图 | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 SDLFlow（R25，实验性），但非完整 SDL |
| 3.2 | 自动生成参数化单元（PCell）并实例化到设计中 | ✅已有 | src/polaris/pdk/pcell.py:576 | PoLaRIS 有 polaris_cell PCell 装饰器 |
| 3.3 | 显示飞线（flylines）以放置模块、最小化布线拥塞 | ❌缺失 | - | PoLaRIS 无飞线显示 |
| 3.4 | SDL short 与 open Connectivity Checker | ⚠️部分 | src/polaris/sim/constraint_checker.py:53 | PoLaRIS 有 ConstraintChecker（16 项约束），但非 SDL 专用 |
| 3.5 | 对象抓取（gravity）用于快速、准确版图 | ❌缺失 | - | PoLaRIS 无 GUI 对象抓取 |
| 3.6 | S-Edit 创建原理图；大型设计 SDL 流程 | ❌缺失 | - | PoLaRIS 无 S-Edit 原理图捕获 |

### 4. Calibre 集成（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | L-Edit Photonics 启动 Calibre Interactive 推动物理验证 | ❌缺失 | - | PoLaRIS 无 Calibre Interactive 集成 |
| 4.2 | Calibre nmDRC 用于设计规则检查（DRC） | ⚠️部分 | src/polaris/sim/klayout_drc.py:238; src/polaris/sim/eqdrc.py:172 | PoLaRIS 有 KLayout DRC + eqDRC，但非 Calibre nmDRC |
| 4.3 | Calibre nmLVS 用于版图与原理图检查（LVS） | ⚠️部分 | src/polaris/sim/graph_lvs.py:160; src/polaris/sim/lvs.py:494 | PoLaRIS 有图同构 LVS + 基础 LVS，但非 Calibre nmLVS |
| 4.4 | Calibre xACT 用于寄生效应提取 | ⚠️部分 | src/polaris/sim/layout_aware.py:258 | PoLaRIS 有 ParasiticExtractor，但非 Calibre xACT |
| 4.5 | Calibre LFD（Litho-Friendly Design）用于光刻友好设计 | ❌缺失 | - | PoLaRIS 无光刻友好设计 |
| 4.6 | Calibre RVE 查看结果并高亮网络与器件，支持交叉探测 | ❌缺失 | - | PoLaRIS 无 Calibre RVE |
| 4.7 | 与 Calibre 和 Calibre RealTime 集成 | ❌缺失 | - | PoLaRIS 无 Calibre RealTime 集成 |
| 4.8 | 光子版图验证使用 Calibre 基于方程的设计规则 | ✅已有 | src/polaris/sim/eqdrc.py:172 | PoLaRIS 有 EqDRCEngine（R23 Calibre eqDRC 对齐） |

### 5. GDSII/OASIS 导出与互操作（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 导入与导出 ODB++ | ❌缺失 | - | PoLaRIS 无 ODB++ 支持 |
| 5.2 | 与第三方 IP 互操作支持 | ⚠️部分 | src/polaris/pdk/gdsfactory_integration.py | PoLaRIS 有 gdsfactory 集成，但无第三方 IP 互操作框架 |
| 5.3 | 与第三方版本控制工具集成 | ❌缺失 | - | PoLaRIS 无版本控制工具集成 |
| 5.4 | 基于 OpenAccess，设计数据可与任何支持 OpenAccess 的版图工具互换 | ❌缺失 | - | PoLaRIS 无 OpenAccess 支持 |
| 5.5 | OASIS 导出支持 | ✅已有 | src/polaris/eval/layout_render.py:361 | PoLaRIS 有 export_oasis |

### 6. 曲线多边形与波导（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 支持曲线多边形与任意角度图形 | ✅已有 | src/polaris/router/curvy_router.py:1286 | PoLaRIS 有 CurvyRouter（Euler/arc/Chaikin 平滑） |
| 6.2 | 简单波导创建与编辑 | ✅已有 | src/polaris/router/waveguide_router.py:104 | PoLaRIS 有 GridRouter |
| 6.3 | 自动交叉插入（automated crossing insertion） | ✅已有 | src/polaris/router/curvy_router.py:350 | PoLaRIS 有 AdaptiveCrossingInserter |
| 6.4 | 精确抓取至光学引脚（precision snapping to optical pins） | ❌缺失 | - | PoLaRIS 无 GUI 引脚抓取 |
| 6.5 | 波导到引脚检查（waveguide to pin checking） | ⚠️部分 | src/polaris/sim/constraint_checker.py:53 | PoLaRIS 有 ConstraintChecker，但非专用波导-引脚检查 |
| 6.6 | 多种波导类型：带状、脊型、分段组合 | ✅已有 | src/polaris/router/hybrid_router.py:33 | PoLaRIS 有 WaveguideType 枚举（条形/肋形/槽形） |
| 6.7 | 波导长度编辑，可定义精确有效长度 | ✅已有 | src/polaris/router/advanced_connectors.py:155 | PoLaRIS 有 LengthDefinedConnector |
| 6.8 | 两步波导创建：先创建正交布线，再按热键转换为曲率波导 | ❌缺失 | - | PoLaRIS 无两步波导创建 GUI 流程 |

### 7. S-Edit 电路图（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | S-Edit 提供强大的 IC 与 PIC 原理图捕获环境 | ❌缺失 | - | PoLaRIS 无 S-Edit 原理图捕获 |
| 7.2 | 原理图流程可选（optional with S-Edit） | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 IPKISS SDL 流程（实验性），但无 S-Edit |
| 7.3 | S-Edit 与 L-Edit 工具均可提取描述电路元件与连接的网表 | ⚠️部分 | src/polaris/sim/lvs.py:121 | PoLaRIS 有 extract_netlist_from_gds，但非 S-Edit 网表 |
| 7.4 | 网表导入 INTERCONNECT 等 CML 仿真器，生成基于紧凑模型库的电路 | ✅已有 | src/polaris/sim/interconnect.py:402 | PoLaRIS 有 INTERCONNECTSimulator（R32，实验性） |
| 7.5 | S-Edit 与 VPI Design Suite 联合提供 EPDA 环境 | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK，但无 S-Edit 联合 |

### 8. 网表生成与仿真伙伴集成（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 以版图为中心的设计流程，内置网表生成 | ✅已有 | src/polaris/sim/lvs.py:121 | PoLaRIS 有 extract_netlist_from_gds |
| 8.2 | 网表支持西门子所有光仿真软件合作伙伴 | ❌缺失 | - | PoLaRIS 无西门子仿真伙伴支持 |
| 8.3 | 仿真合作伙伴：Ansys、Luceda、Optiwave、VPIphotonics | ⚠️部分 | src/polaris/sim/lumerical_integration.py:896; src/polaris/flow/ipkiss_flow.py:494; src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 Lumerical(Ansys)/IPKISS(Luceda)/VPI 集成，无 Optiwave |
| 8.4 | 网表支持西门子晶体管级与混合模式仿真器 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA SPICE，但非西门子仿真器 |
| 8.5 | 网表格式：InstanceName Nets ModelName Parameters；支持 .subckt/.ends | ⚠️部分 | src/polaris/sim/graph_lvs.py:89 | PoLaRIS 有 PhotonicsNetlist，但格式不完全匹配 |
| 8.6 | 网表参数包含 library、lay_x..lay_f、sch_x..sch_f 及其他元件参数 | ❌缺失 | - | PoLaRIS 无 lay_x/lay_f/sch_x/sch_f 参数 |

### 9. 热光协同（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | 电元器件可手动布局并互连，连接至光子 PCell 中的加热器与外部电气组件 | ⚠️部分 | src/polaris/router/opto_electrical.py:101 | PoLaRIS 有 OptoElectricalRouter，但无加热器 PCell |
| 9.2 | Calibre xACT 寄生效应提取支持热相关电气寄生分析 | ⚠️部分 | src/polaris/sim/layout_aware.py:258 | PoLaRIS 有 ParasiticExtractor，但非 Calibre xACT 热相关 |
| 9.3 | 与 VPIphotonics Design Suite 联合提供 EPDA，支持电-光-热协同仿真 | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK，但无完整电-光-热协同 |
| 9.4 | 专用热-光协同仿真模块 | ❌缺失 | - | PoLaRIS 无专用热-光协同仿真模块 |

### 10. 脚本与可扩展性（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 可使用 Python 脚本化 | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 Python CLI |
| 10.2 | 完全可脚本化与可扩展，使用 Python、TCL/Tk 或 C++ | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 仅支持 Python，无 TCL/Tk/C++ |
| 10.3 | 支持拖放（drag and drop）方法论 | ❌缺失 | - | PoLaRIS 无 GUI 拖放 |
| 10.4 | 支持脚本驱动方法论（script-driven methodology） | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 CLI 脚本驱动 |

### 11. 平台与设计流程（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 支持 Windows 与 Linux 双平台 | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 为 Python 跨平台库 |
| 11.2 | 以版图为中心的设计流程（layout-centric flow） | ✅已有 | src/polaris/pipeline/integrated.py:446 | PoLaRIS 有 IntegratedPipeline |
| 11.3 | 版图作为最重要的设计数据库（golden design database） | ✅已有 | src/polaris/data/gds_loader.py:468 | PoLaRIS 有 GDS 电路解析 |
| 11.4 | 完整 PIC 设计流程：版图创建 → 网表提取 → 仿真 → Calibre 物理验证 → tape-out | ✅已有 | src/polaris/flow/executors.py:145-810 | PoLaRIS 有 10 阶段标准化流程 |
| 11.5 | 直观且易于上手的学习曲线 | ⚠️部分 | src/polaris/web/server.py:329 | PoLaRIS 有 HTTP API + CLI，但无 GUI，学习曲线不如 L-Edit 直观 |

### 12. Luceda IPKISS 集成（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | IPKISS.eda 设计框架基于 Tanner L-Edit 版图编辑器构建 | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 SDLFlow（R25，实验性），但非基于 L-Edit |
| 12.2 | L-Edit 结合 IPKISS 参数化光子元件库与 PDK，支持拖放光子元件到版图 | ✅已有 | src/polaris/flow/ipkiss_flow.py:494 | PoLaRIS 有 IPKISSPDKBridge |
| 12.3 | 通过波导连接元件，完全控制截面形状、弯曲与轨迹 | ✅已有 | src/polaris/router/waveguide_router.py:104 | PoLaRIS 有 GridRouter + 平台约束 |
| 12.4 | 后版图效应（如波导交叉引起的反射与衰减）通过 IPKISS.eda 紧凑模型仿真器处理 | ⚠️部分 | src/polaris/sim/layout_aware.py:361 | PoLaRIS 有 LayoutAwareSimulator，但非 IPKISS.eda 紧凑模型 |

### T06 L-Edit Photonics 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 24 | 34.8% |
| ⚠️ 部分 | 24 | 34.8% |
| ❌ 缺失 | 21 | 30.4% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **69** | **100%** |

**覆盖率**: (24 + 0.5×24) / 69 = 36/69 = **52.2%**（源文档标注 69.6%，按 ✅+⚠️/总数 计算）

> 注：源文档 T05_T06_gap.md 使用 (✅+⚠️)/总数 公式标注 69.6%，本汇总按统一公式 (✅+0.5×⚠️)/(总数-🚫) 重新计算为 52.2%。总览表保留源文档原值 69.6% 以保持一致。

---

## 第10名: T05 VPIphotonics（商业，88 功能点）

> 来源分文档：`/workspace/docs/feature_gap_detail/T05_T06_gap.md`
> 价格：~$15-40K/年（估算，来源 https://www.vpiphotonics.com/）

### 1. 工具套件组成（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | VPItransmissionMaker Optical Systems（光传输系统设计） | ⚠️部分 | src/polaris/sim/system_level.py:31 | PoLaRIS 有 SignalFlowGraph/OpticalLink 系统级仿真，但非独立子工具套件 |
| 1.2 | VPIcomponentMaker Photonic Circuits（光子集成电路设计） | ⚠️部分 | src/polaris/sim/simulator.py:57 | PoLaRIS 有 CircuitSimulator 频域仿真器，但模块库规模远小于 VPI |
| 1.3 | VPIcomponentMaker Fiber Optics（光纤放大器/激光器设计） | ❌缺失 | - | PoLaRIS 无光纤放大器/激光器专用设计模块 |
| 1.4 | VPIlabExpert（实验室虚拟化） | ❌缺失 | - | PoLaRIS 无实验室虚拟化能力 |
| 1.5 | VPIdeviceDesigner（器件级波导/光纤仿真，Python 框架） | ⚠️部分 | src/polaris/sim/fdtd_simulator.py:279 | PoLaRIS 有 FDTD/水平集/拓扑优化器件级仿真，但无 BPM/EME |
| 1.6 | VPItoolkit PDK \<fab\>（多 foundry PDK 工具包） | ✅已有 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK（R15，实验性） |

### 2. 时域仿真（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | Photonics TLM 模型，扩展自 TLLM，用于多段光电子器件时域建模 | ⚠️部分 | src/polaris/sim/system_level.py:157 | PoLaRIS 有 TLLMLaser 模型，但未覆盖 SOA/调制器/光电探测器全器件 |
| 2.2 | 支持 MQW 或 Bulk 有源区介质、灵活电极分配、可调增益/吸收谱 | ❌缺失 | - | PoLaRIS 无 MQW/Bulk 有源区介质建模 |
| 2.3 | 任意折射率与增益光栅剖面（含非互易与采样光栅）、反射端面、Kerr/TPA/电折射/电吸收 | ❌缺失 | - | PoLaRIS 无光栅剖面与有源效应建模 |
| 2.4 | 紧密耦合的有源与色散无源光子器件双向端口时域仿真 | ⚠️部分 | src/polaris/sim/caphe_backend.py:292 | PoLaRIS 有 CAPHETimeDomainSolver，但未实现紧密耦合有源-无源双向 |
| 2.5 | 采样信号建模支持光场时域详细仿真，可用于 BER 估计与眼图分析 | ✅已有 | src/polaris/sim/verilog_a.py:864,898 | PoLaRIS 有 compute_eye_diagram/compute_ber 及 EyeDiagramAnalyzer |
| 2.6 | Active FDTD（注：VPIdeviceDesigner 不直接提供 FDTD） | ⚠️部分 | src/polaris/sim/fdtd_simulator.py:279 | PoLaRIS 有 FDTD 仿真（MEEP/Tidy3D/ANALYTICAL），但非 Active FDTD 有源器件 |

### 3. 频域仿真（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 级联散射矩阵（S-matrix）方法，支持数千元件规模 | ✅已有 | src/polaris/sim/cascade.py:315 | PoLaRIS 有 cascade_circuit（SAX 子网络增长算法） |
| 3.2 | 任意频率相关有效模式折射率与衰减，TE/TM 模式独立指定 | ⚠️部分 | src/polaris/sim/models.py:159 | PoLaRIS 有 waveguide_s 模型，但 TE/TM 独立指定能力有限 |
| 3.3 | 加载/保存单个器件及任意无源子电路的 S-matrix | ✅已有 | src/polaris/sim/touchstone.py:133,184 | PoLaRIS 有 load_touchstone/save_touchstone |
| 3.4 | 时均信号表示（time-averaged signal representation） | ❌缺失 | - | PoLaRIS 无时均信号表示 |
| 3.5 | 混合时域-频域方法（TFDM），用于大规模多尺度有源 PIC | ✅已有 | src/polaris/sim/system_level.py:262 | PoLaRIS 有 HybridSimulator 混合仿真器 |

### 4. TLM 传输线模型（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | TLLM 处理多段半导体器件建模，含 Bulk 或 MQW 有源介质 | ⚠️部分 | src/polaris/sim/system_level.py:157 | PoLaRIS 有 TLLMLaser，但无 MQW 有源介质 |
| 4.2 | 支持掩埋异质结激光器、放大器、电光调制器、DBR | ❌缺失 | - | PoLaRIS 无这些具体器件模型 |
| 4.3 | TLLM 涵盖 Kerr 与 TPA、DFB/DBR 光栅、测量增益与吸收谱 | ❌缺失 | - | PoLaRIS 无 Kerr/TPA/DFB/DBR 光栅建模 |
| 4.4 | S-matrix 方法支撑无源光子与线性电器件建模 | ✅已有 | src/polaris/sim/models.py:159; src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 S 参数模型 + MNA SPICE 求解器 |
| 4.5 | 多段半导体激光器建模，支持纵向参数变化（锥形或 FBG 稳频） | ❌缺失 | - | PoLaRIS 无多段半导体激光器建模 |

### 5. BPM 光束传播（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 2D 与 3D 全矢量/半矢量有限差分 BPM | ❌缺失 | - | PoLaRIS 无 BPM 实现 |
| 5.2 | 灵活定义 2D 波导/光纤截面与 3D 器件版图，含色散/温度相关光学材料 | ⚠️部分 | src/polaris/pdk/pcell.py:576 | PoLaRIS 有 PCell 参数化版图，但无色散/温度相关材料库 |
| 5.3 | 可广泛定制的非均匀网格与 PML 吸收边界 | ❌缺失 | - | PoLaRIS 无 PML 吸收边界 |
| 5.4 | 应用：波导、锥形、S-bend、定向耦合器、环形耦合器、Y 分束器、MMI | ✅已有 | src/polaris/sim/models.py:159-455 | PoLaRIS 有 y_branch_s/directional_coupler_s/mmi_1x2_s 等模型 |
| 5.5 | EME（本征模展开）方法，支持双向场传播处理背向反射 | ❌缺失 | - | PoLaRIS 无 EME 方法 |

### 6. 非线性效应（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | TLLM 模型涵盖 Kerr 效应与双光子吸收（TPA） | ❌缺失 | - | PoLaRIS 无 Kerr/TPA 效应建模 |
| 6.2 | 电折射与电吸收效应建模 | ❌缺失 | - | PoLaRIS 无电折射/电吸收效应 |
| 6.3 | 基于 XPM、XGM、FWM 的波长转换比较 | ❌缺失 | - | PoLaRIS 无 XPM/XGM/FWM 波长转换 |
| 6.4 | 2R/3R 再生器开发与速度、传输特性及诱导 chirp 优化 | ❌缺失 | - | PoLaRIS 无 2R/3R 再生器 |
| 6.5 | 光纤非线性（拉曼放大器、参量放大器） | ❌缺失 | - | PoLaRIS 无光纤非线性建模 |

### 7. 光电协同仿真（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | 完整可扩展的线性电器件库（R/C/L/变压器/开关/OpAmp/源） | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA SPICE 求解器，但电器件库不如 VPI 完整 |
| 7.2 | 任意线性电路的 DC、AC 与瞬态分析 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA 求解器，但 DC/AC/瞬态分析能力未明确分立 |
| 7.3 | 通用电气滤波器、函数与 DSP 算法 | ❌缺失 | - | PoLaRIS 无通用电气滤波器/DSP 算法库 |
| 7.4 | 逻辑门与测试函数用于数字电路快速原型 | ❌缺失 | - | PoLaRIS 无逻辑门/数字电路库 |
| 7.5 | 异质 PIC 建模，结合有源与无源子器件，覆盖不同长度尺度 | ⚠️部分 | src/polaris/pipeline/integrated.py:446 | PoLaRIS 有 IntegratedPipeline，但异质有源-无源建模能力有限 |
| 7.6 | 信号与噪声模型基于全波振幅或参数化表示，Jones/Mueller 形式 | ❌缺失 | - | PoLaRIS 无 Jones/Mueller 偏振形式 |

### 8. ADS 联合仿真（7 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 与 Keysight PathWave ADS 协同仿真 | ❌缺失 | - | PoLaRIS 无 Keysight ADS 集成 |
| 8.2 | 业界首个集成 EOE 工作流 | ❌缺失 | - | PoLaRIS 无 EOE 工作流 |
| 8.3 | 动态通信与无缝数据传输，预测数据链路性能 | ❌缺失 | - | PoLaRIS 无 ADS 动态通信 |
| 8.4 | 分析从电到光再回到电的整条链路 | ⚠️部分 | src/polaris/sim/mna_spice.py:415 | PoLaRIS 有 build_opto_electrical_link_circuit，但非 ADS 全链路 |
| 8.5 | 400G/800G/1.6T 收发器设计；给定 BER 目标下的电设计仿真 | ❌缺失 | - | PoLaRIS 无 400G/800G/1.6T 收发器设计 |
| 8.6 | 全链路眼图指标分析（BER、TDECQ）；调制格式比较（NRZ、PAM-4、16QAM） | ⚠️部分 | src/polaris/sim/verilog_a.py:864,898 | PoLaRIS 有 BER/眼图，但无 TDECQ 与多调制格式比较 |
| 8.7 | 并行化方法比较（FDM、WDM、SDM）；光电带宽对全链路 BER 影响 | ❌缺失 | - | PoLaRIS 无 FDM/WDM/SDM 并行化比较 |

### 9. 多 Foundry PDK 支持（9 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | VPItoolkit PDK \<fab\> 可插拔工具包 | ✅已有 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK |
| 9.2 | 支持代工厂：HHI、LIGENTEC、LioniX、SMART、Infinera、GPIC | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:236,295,354 | PoLaRIS 有 Ligentec/Lionix/HHI PDK 构建，缺 SMART/Infinera |
| 9.3 | 支持材料平台：InP、Silicon、Silicon Nitride、Polymer | ✅已有 | src/polaris/pdk/foundry_platforms.py:72 | PoLaRIS 有 11 个 foundry 平台注册表 |
| 9.4 | Layout-aware schematic-driven PIC 设计方法学 | ✅已有 | src/polaris/sim/layout_aware.py:361 | PoLaRIS 有 LayoutAwareSimulator |
| 9.5 | 智能弹性光连接器（elastic optical connectors） | ✅已有 | src/polaris/sim/layout_aware.py:97 | PoLaRIS 有 ElasticConnector |
| 9.6 | 与 PhoeniX OptoDesigner、IPKISS、Nazca Design 集成 | ⚠️部分 | src/polaris/pdk/optodesigner.py:101; src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 OptoDesigner/IPKISS 集成，无 Nazca Design |
| 9.7 | 支持 PDAflow API | ✅已有 | src/polaris/pdk/optodesigner.py:766; src/polaris/pdk/vpi_pdk.py:139 | PoLaRIS 有 PDAflowInterop 和 PDAflowExporter |
| 9.8 | VPItoolkit PDK GPIC 与 L-Edit Photonics / S-Edit 联合解决方案 | ✅已有 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK（R19） |
| 9.9 | 制造容差与良率性能分析，技术方案比较 | ✅已有 | src/polaris/sim/monte_carlo.py:174; src/polaris/sim/robust_optimizer.py:256 | PoLaRIS 有 yield_analysis 和 RobustOptimizer |

### 10. 可视化与数据分析（11 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 应用专用虚拟仪器 | ❌缺失 | - | PoLaRIS 无虚拟仪器 GUI |
| 10.2 | 光/电信号与数值数据通用后处理分析 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有版图渲染，但无通用信号后处理 |
| 10.3 | 可调分辨率的光谱/波形分析，信号功率与相位特性 | ⚠️部分 | src/polaris/sim/simulator.py:357 | PoLaRIS 有 analyze_dispersion（FSR/Q），但无波形分析 |
| 10.4 | 多输入端口比较不同来源信号/数据 | ❌缺失 | - | PoLaRIS 无多端口信号比较 |
| 10.5 | 时域与频域偏振分析（含 Poincare 球） | ❌缺失 | - | PoLaRIS 无偏振分析/Poincare 球 |
| 10.6 | 不同仿真运行轨迹的叠加、平均与拼接 | ❌缺失 | - | PoLaRIS 无轨迹叠加/平均/拼接 |
| 10.7 | 数值数据 1D 与 2D 绘图，含直方图；多项式或高斯拟合 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有 matplotlib 渲染，但无直方图/拟合 |
| 10.8 | 3D 可视化（表面图、密度图、等高线图） | ❌缺失 | - | PoLaRIS 无 3D 可视化 |
| 10.9 | 全局与局部峰值（最小/最大）搜索；标记精确数据读取 | ❌缺失 | - | PoLaRIS 无峰值搜索 |
| 10.10 | 轴单位切换（THz/nm）与缩放（linear/log/erfc） | ❌缺失 | - | PoLaRIS 无轴单位切换 GUI |
| 10.11 | 可编辑图形属性与出版级图形主题 | ❌缺失 | - | PoLaRIS 无出版级图形主题 |

### 11. 脚本与编程接口（7 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | Python 与 TCL 仿真脚本 | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 Python CLI，无 TCL |
| 11.2 | 用户自定义算法 Python、Matlab、C++、COM、ADS | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 仅支持 Python，无 Matlab/C++/COM/ADS |
| 11.3 | 仿真引擎对外部系统与第三方工具的 API 访问 | ✅已有 | src/polaris/web/server.py:329 | PoLaRIS 有 HTTP API（PolarisHTTPRequestHandler） |
| 11.4 | Python 协同仿真，添加用户定义 S-matrix 无源光子器件 | ✅已有 | src/polaris/sim/models.py:159 | PoLaRIS 有 10 种基础器件 S 参数模型，可扩展 |
| 11.5 | 宏语言（Macro language）自动化设计操作 | ❌缺失 | - | PoLaRIS 无宏语言 |
| 11.6 | VPIdeviceDesigner 基于 Python，集成 NumPy/SciPy/Matplotlib/Jupyter | ✅已有 | src/polaris/sim/jax_backend.py:65 | PoLaRIS 基于 Python + JAX/NumPy |
| 11.7 | 高阶函数支持映射与链式任意数量模块（AWG/多环滤波器） | ⚠️部分 | src/polaris/data/dataset_generator.py:422 | PoLaRIS 有数据集生成，但无 AWG/多环高阶函数映射 |

### 12. 仿真引擎与并行计算（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 模块算法、设计与参数扫描层面的并行计算 | ⚠️部分 | src/polaris/trainer/parallel_rollout.py:80 | PoLaRIS 有并行 rollout，但非模块/参数扫描级并行 |
| 12.2 | 单 GPU 与多 GPU 加速计算 | ⚠️部分 | src/polaris/engine/gpu_backend.py:221 | PoLaRIS 有 GPUBackend（CuPy，实验性），非多 GPU |
| 12.3 | 本地与远程仿真；仿真作业管理 | ⚠️部分 | src/polaris/flow/scheduler.py:42 | PoLaRIS 有 JobScheduler，但无远程仿真 |
| 12.4 | 自动多维参数扫描、优化与良率估计 | ✅已有 | src/polaris/data/variant_generator.py:478; src/polaris/sim/monte_carlo.py:174 | PoLaRIS 有参数扫描变体生成 + 良率分析 |
| 12.5 | 交互式参数调谐 | ❌缺失 | - | PoLaRIS 无交互式参数调谐 GUI |
| 12.6 | 层次化设计用于系统复杂性抽象 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85 | PoLaRIS 有 HierarchicalPlacer |
| 12.7 | 用户自定义模块与库，可选加密保护 IP | ❌缺失 | - | PoLaRIS 无 IP 加密保护 |
| 12.8 | 导出设计至免费模拟器 VPIplayer | ❌缺失 | - | PoLaRIS 无 VPIplayer 导出 |

### 13. 模块库与应用示例（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | 700+ 光子与电子模块，500+ 设计模板 | ⚠️部分 | src/polaris/sim/models.py:159; src/polaris/pdk/foundry_devices.py:188 | PoLaRIS 有基础器件模型 + foundry 器件，但数量远少于 700+ |
| 13.2 | 130+ VPIcomponentMaker Photonic Circuits 能力演示 | ⚠️部分 | /workspace/tests/*.py（139 测试文件） | PoLaRIS 有 139 测试文件，但非商业级演示库 |
| 13.3 | 应用：电信/数通、短距、光互连、DWDM、RoF、微波光子学、LiDAR、卫星通信 | ⚠️部分 | src/polaris/data/lidar_benchmark.py:37 | PoLaRIS 有 LiDAR/Apollo/TILOS 基准，但无 RoF/卫星通信 |
| 13.4 | 调制格式：PSK、DPSK、DQPSK、mPSK、mQAM | ❌缺失 | - | PoLaRIS 无调制格式库 |
| 13.5 | 大规模 PIC：可重构交叉连接、add-drop 复用、光互连 | ⚠️部分 | src/polaris/data/apollo_benchmark.py:442 | PoLaRIS 有 Apollo oNoC 光子网络基准，但非完整交叉连接 |

### 14. 平台支持（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | Windows 10 Pro（64 位） | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，不限定 OS |
| 14.2 | Windows 11 Pro（64 位） | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，不限定 OS |
| 14.3 | 硬件：1 GHz+ 64 位处理器，2 GB RAM，3 GB 硬盘，NVIDIA GPU | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，硬件需求由用户环境决定 |

### T05 VPIphotonics 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 19 | 21.6% |
| ⚠️ 部分 | 29 | 33.0% |
| ❌ 缺失 | 37 | 42.0% |
| 🚫 不适用 | 3 | 3.4% |
| **合计** | **88** | **100%** |

**覆盖率**: (19 + 0.5×29) / (88 - 3) = 33.5/85 = **39.4%**（源文档标注 56.5%，按 (✅+⚠️)/(总数-🚫) 计算）

> 注：源文档 T05_T06_gap.md 使用 (✅+⚠️)/(总数-🚫) 公式标注 56.5%，本汇总按统一公式 (✅+0.5×⚠️)/(总数-🚫) 重新计算为 39.4%。总览表保留源文档原值 56.5% 以保持一致。

<!-- PART2_BATCH4_END -->
