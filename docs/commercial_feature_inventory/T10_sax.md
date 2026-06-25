# T10 sax 功能点清单

## 文档信息

| 项目 | 内容 |
|---|---|
| 工具名 | sax (S-Matrices with Autograd and XLA) |
| 维护方 | Floris Laporte (flaport) |
| GitHub URL | https://github.com/flaport/sax |
| 官方文档 | https://flaport.github.io/sax/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 开源协议 | Apache-2.0 |
| 当前版本 | 0.18.0 |

> **学术诚信声明**：本文档所有功能点均来源于 sax 官方 GitHub 仓库、官方文档及 gplugins 集成文档。未在公开文档中明确说明的功能标注为"未公开"。

---

## 1. 工具概述

SAX 是一个基于 JAX 的散射参数（S-parameter）电路仿真器和优化器，用于频域仿真。该仿真器最初为光子集成电路（PIC）仿真开发，但实际上能够执行任何基于 S 参数的电路仿真。SAX 的目标是成为 JAX 的薄包装，提供一些基本的 S 参数电路仿真和优化工具。

- **来源**: https://flaport.github.io/sax/
- **GitHub**: https://github.com/flaport/sax

---

## 2. 功能点清单

### 2.1 JAX S 参数仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 1.1 | JAX 后端 | SAX 基于 JAX 构建，是 JAX 的薄包装，提供 S 参数电路仿真和优化 | https://flaport.github.io/sax/ |
| 1.2 | S 字典（SDict） | 核心数据结构为 SDict（`Dict[Tuple[str,str], float]`），映射端口组合到散射参数 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 1.3 | 函数式模型 | SAX 模型是返回 S 字典的函数（callables），保持 JAX 的函数式特性 | https://flaport.github.io/sax/ |
| 1.4 | 标准字典 | SAX 不定义特殊数据结构，尽量保持接近 JAX 的函数式特性，只需函数和标准 Python 字典 | https://flaport.github.io/sax/ |
| 1.5 | XLA 加速 | 基于 XLA（Accelerated Linear Algebra）编译加速 | https://flaport.github.io/sax/ |
| 1.6 | GPU 加速 | 通过 JAX 支持 GPU 加速，大型电路可获得显著加速 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 1.7 | 双精度支持 | 支持 JAX 双精度（double precision）配置 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |

### 2.2 子网络增长算法（Subnetwork Growth）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 2.1 | 子网络增长 | 通过级联设备散射参数（S 参数）实现，使用子网络增长算法 | https://arxiv.org/pdf/2009.05146 |
| 2.2 | Filipsson-Gunnar 后端 | 基于 Filipsson-Gunnar 论文的子网络增长后端 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 2.3 | 算法遍历 | Filipsson-Gunnar 后端算法遍历（Algorithm Walkthrough） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 2.4 | 算法改进 | Filipsson-Gunnar 后端算法改进（Algorithm Improvements） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 2.5 | reciprocal 函数 | `sax.reciprocal` 函数自动填充反向连接（前向连接的互易填充） | https://flaport.github.io/sax/ |

### 2.3 autograd 逆向（自动微分）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 3.1 | 自动微分 | 通过 JAX 支持自动微分（autograd），可获得函数值和梯度 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 3.2 | 梯度优化 | 在 SAX 中编写组件模型可获得梯度，用于电路优化 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 3.3 | MZI 优化 | 支持 MZI（马赫曾德干涉仪）优化示例 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 3.4 | 逆向设计 | 支持逆向设计（inverse design），与 Tidy3D adjoint 插件集成 | https://develop.d3nzcgsw5oo0x1.amplifyapp.com/tidy3d/examples/notebooks/AdjointPlugin11CircuitMZI/ |
| 3.5 | JAX 优化器 | 集成 `jax.example_libraries.optimizers` 进行优化 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |

### 2.4 cocotb 联合仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 4.1 | 直接 cocotb 集成 | 未公开（sax 官方文档未明确说明直接 cocotb 集成） | - |
| 4.2 | SPICE 协同仿真 | 通过 piel 等工具支持 SPICE 协同仿真，间接实现光电联合验证 | https://piel.readthedocs.io/en/latest/examples/04_spice_cosimulation/04_spice_cosimulation.html |

### 2.5 gdsfactory 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 5.1 | gplugins.sax | gdsfactory 通过 `gplugins.sax` 模块集成 SAX | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.2 | SAX gdsfactory 兼容性 | 提供 SAX gdsfactory 兼容性（SAX gdsfactory Compatibility） | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.3 | 布局感知 Monte Carlo | 支持布局感知 Monte Carlo 分析 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.4 | 紧凑 MZI | 支持紧凑 MZI 仿真 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.5 | 相移器模型 | 支持相移器模型（Phase shifter model） | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.6 | 层次化电路 | 支持层次化电路（Hierarchical circuits） | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.7 | FDTD S 参数模型 | 支持 FDTD S 参数模型拟合 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 5.8 | QPDK 集成 | 与 QPDK（量子 RF PDK）集成，提供分析 S 参数模型 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 5.9 | JAX 后端比较 | 支持跨 JAX 计算后端（CPU、GPU、NPU）的基准测试 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |

### 2.6 多端口器件

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 6.1 | 多端口 S 矩阵 | 支持多端口器件的 S 参数矩阵表示 | https://flaport.github.io/sax/ |
| 6.2 | 定向耦合器模型 | 提供定向耦合器（directional coupler）多端口模型示例 | https://flaport.github.io/sax/ |
| 6.3 | 端口组合 | S 字典键为端口组合（2-tuple），映射到散射参数 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 6.4 | 稀疏 S 矩阵 | 字典比（jax-）numpy 数组更适合表征 S 参数，因为 S 参数本质稀疏 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 6.5 | 字符串索引 | 字典允许字符串索引，在此上下文中使用更愉快 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |

### 2.7 频率扫描

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 7.1 | 波长扫描 | 支持波长扫描仿真，可定义波长数组进行仿真 | https://flaport.github.io/sax/ |
| 7.2 | 全局设置 | 全局设置可添加到电路调用的"根"，分发到所有同名参数的子组件 | https://flaport.github.io/sax/ |
| 7.3 | 嵌套设置 | 支持嵌套设置调用子组件 | https://flaport.github.io/sax/ |
| 7.4 | 频率分辨率 | 支持不同频率分辨率大小的基准测试 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |
| 7.5 | 多波长 S 参数 | 考虑多波长时，S 参数可为数组 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |

### 2.8 级联算法（Backends）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 8.1 | KLU 后端 | KLU 后端优于 Filipsson-Gunnar 后端，自 v0.10.0 起为默认后端（需安装 klujax） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.2 | KLU 理论背景 | KLU 后端基于 KLU 直接稀疏求解器，专为电路仿真问题设计 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.3 | 稀疏辅助函数 | KLU 后端提供稀疏辅助函数（Sparse Helper Functions） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.4 | KLU 算法遍历 | KLU 后端算法遍历（Algorithm Walkthrough） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.5 | KLU 算法改进 | KLU 后端算法改进（Algorithm Improvements） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.6 | Filipsson-Gunnar 后端 | 基于 Filipsson-Gunnar 论文的传统子网络增长后端 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.7 | Additive 后端 | 加性后端（Additive Backend），适用于特定场景 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.8 | Forward-only 后端 | 前向only后端，当电路中组件背反射低时高效，仅计算前向矩阵乘法 | https://gdsfactory.github.io/sax/nbs/examples/09_forward_only_backend/ |
| 8.9 | Forward-only 加速 | 随着电路复杂度增加，forward-only 后端加速更显著，只要无背反射结果保持准确 | https://gdsfactory.github.io/sax/nbs/examples/09_forward_only_backend/ |
| 8.10 | Sparse COO 后端 | 稀疏 COO（Coordinate）格式后端 | https://flaport.github.io/sax/ |
| 8.11 | 后端可互换 | SAX 允许轻松互换电路后端 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.12 | analyze_instances | 后端静态分析步骤：分析实例的"形状"（端口组合） | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.13 | analyze_circuit | 后端静态分析步骤：分析电路 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.14 | evaluate_circuit | 后端评估步骤：评估电路 | https://gdsfactory.github.io/sax/nbs/internals/03_backends/ |
| 8.15 | klujax 依赖 | KLU 后端依赖 klujax 库，未安装时性能下降并发出警告 | https://develop.d3nzcgsw5oo0x1.amplifyapp.com/tidy3d/examples/notebooks/AdjointPlugin11CircuitMZI/ |

### 2.9 电路构建

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 9.1 | sax.circuit | `sax.circuit()` 从网表构建电路，返回组件模型函数 | https://flaport.github.io/sax/ |
| 9.2 | 网表格式 | 网表包含 instances、connections、ports 三部分 | https://flaport.github.io/sax/ |
| 9.3 | YAML 电路 | 支持从 YAML 定义电路（circuit from yaml） | https://flaport.github.io/sax/ |
| 9.4 | 模型组合 | 组件模型可组合成电路，电路本身也是组件模型函数 | https://flaport.github.io/sax/ |

### 2.10 模型库

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 10.1 | 内置模型 | 提供内置模型（models），包括波导、耦合器等 | https://flaport.github.io/sax/ |
| 10.2 | RF 模型 | 提供 RF 模型（sax.models.rf） | https://flaport.github.io/sax/ |
| 10.3 | 模型拟合 | 支持模型拟合（sax.fit），包括对称、反对称、总拟合 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.4 | 参数化模型 | 支持参数化模型（Parametrized Models），如波导模型、耦合器模型 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.5 | 表面模型 | 支持表面模型（surface models） | https://flaport.github.io/sax/ |
| 10.6 | 所有模型 | 提供所有模型参考（all models） | https://flaport.github.io/sax/ |

### 2.11 仿真示例

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 11.1 | 快速开始 | 提供快速开始示例（quick start） | https://flaport.github.io/sax/ |
| 11.2 | 全通滤波器 | 提供全通滤波器示例（all pass filter） | https://flaport.github.io/sax/ |
| 11.3 | 多模仿真 | 支持多模仿真（multimode simulations） | https://flaport.github.io/sax/ |
| 11.4 | 薄膜仿真 | 支持薄膜仿真（thin film） | https://flaport.github.io/sax/ |
| 11.5 | 加性后端示例 | 提供加性后端示例（additive backend） | https://flaport.github.io/sax/ |
| 11.6 | 布局感知 | 支持布局感知仿真（layout aware） | https://flaport.github.io/sax/ |
| 11.7 | 稀疏 COO 示例 | 提供稀疏 COO 示例（sparse coo） | https://flaport.github.io/sax/ |
| 11.8 | 前向 only 示例 | 提供前向 only 后端示例（forward only backend） | https://flaport.github.io/sax/ |
| 11.9 | neff 色散 | 支持 neff 色散仿真（neff dispersion） | https://gdsfactory.github.io/sax/nbs/examples/09_forward_only_backend/ |

### 2.12 量子电路仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 12.1 | 量子电路仿真 | 支持基于 SAX 的量子电路仿真 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |
| 12.2 | 耦合谐振器电路 | 支持构建耦合谐振器电路进行仿真 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |
| 12.3 | OpenVINO NPU | 支持通过 OpenVINO 在 NPU 上编译和运行电路 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |
| 12.4 | JAXPR 导出 | 支持将电路导出为 JAX 表达式（JAXPR） | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |
| 12.5 | 后端检测 | 自动探测可用后端（CPU、GPU、OpenVINO），不可用时优雅跳过 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html |

### 2.13 LLM 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 13.1 | PICBench 基准 | SAX 被 PICBench 基准用于评估 LLM 生成 PIC 设计 | https://arxiv.org/pdf/2502.03159 |
| 13.2 | JSON 网表 | 给定指定输入/输出端口、所需组件、配置和详细互连的 JSON 网表，SAX 可高效执行数学分析 | https://arxiv.org/pdf/2502.03159 |

---

## 3. 功能点统计

| 类别 | 功能点数量 |
|---|---|
| JAX S 参数仿真 | 7 |
| 子网络增长算法 | 5 |
| autograd 逆向（自动微分） | 5 |
| cocotb 联合仿真 | 2 |
| gdsfactory 集成 | 9 |
| 多端口器件 | 5 |
| 频率扫描 | 5 |
| 级联算法（Backends） | 15 |
| 电路构建 | 4 |
| 模型库 | 6 |
| 仿真示例 | 9 |
| 量子电路仿真 | 5 |
| LLM 集成 | 2 |
| **总计** | **79** |

---

## 4. 参考来源

1. sax GitHub: https://github.com/flaport/sax
2. sax 官方文档: https://flaport.github.io/sax/
3. SAX Backends: https://gdsfactory.github.io/sax/nbs/internals/03_backends/
4. Forward-only Backend: https://gdsfactory.github.io/sax/nbs/examples/09_forward_only_backend/
5. SAX circuit simulator (gplugins): https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html
6. QPDK JAX Backend Comparison: https://gdsfactory.github.io/quantum-rf-pdk/notebooks/jax_backend_comparison.html
7. Tidy3D Inverse design with circuit simulation: https://develop.d3nzcgsw5oo0x1.amplifyapp.com/tidy3d/examples/notebooks/AdjointPlugin11CircuitMZI/
8. Simphony arXiv paper: https://arxiv.org/pdf/2009.05146
9. PICBench arXiv paper: https://arxiv.org/pdf/2502.03159
10. Photonics-Bootcamp MZI: https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html
11. piel SPICE cosimulation: https://piel.readthedocs.io/en/latest/examples/04_spice_cosimulation/04_spice_cosimulation.html
12. KLU Algorithm (ACM): https://dl.acm.org/doi/pdf/10.1145/1824801.1824814
