# T11 simphony 功能点清单

## 文档信息

| 项目 | 内容 |
|---|---|
| 工具名 | simphony (A Simulator for Photonic Circuits) |
| 维护方 | BYU CamachoLab (Sequoia Ploeg, Hyrum Gunther, Ryan M. Camacho) |
| GitHub URL | https://github.com/BYUCamachoLab/simphony |
| 官方文档 | https://simphonyphotonics.readthedocs.io/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 开源协议 | MIT |
| 当前版本 | 0.7.3 (2025-10-28 发布) |

> **学术诚信声明**：本文档所有功能点均来源于 simphony 官方 GitHub 仓库、官方文档、PyPI 及 arXiv 论文。未在公开文档中明确说明的功能标注为"未公开"。

---

## 1. 工具概述

Simphony 是一个免费开源的光子集成电路（PIC）仿真工具箱，用 Python 实现。该工具箱快速且易于扩展；可编写插件以提供与现有布局工具的兼容性，并可轻松创建器件库而无需深入的编程知识。Simphony 通过级联设备散射参数（S 参数）实现，使用子网络增长算法，基准测试表明比 Lumerical INTERCONNECT 加速约 20 倍。

- **来源**: https://simphonyphotonics.readthedocs.io/en/stable/index.html
- **GitHub**: https://github.com/BYUCamachoLab/simphony
- **PyPI**: https://pypi.org/project/simphony/
- **arXiv 论文**: https://arxiv.org/pdf/2009.05146

---

## 2. 功能点清单

### 2.1 S 参数级联（Subnetwork Growth）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 1.1 | 子网络增长算法 | 通过级联设备散射参数实现，使用子网络增长算法（subnetwork growth algorithms） | https://arxiv.org/pdf/2009.05146 |
| 1.2 | 子网络增长例程 | 提供子网络增长例程（Subnetwork growth routines） | https://pypi.org/project/simphony/ |
| 1.3 | S 参数矩阵 | 使用 S 参数矩阵表示组件，Sij 表示端口 j 给定端口 i 激励的响应 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 1.4 | 端口约定 | 遵循 `(output, input)` 键约定，与 S 参数矩阵公式一致 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 1.5 | 紧凑模型 | 紧凑模型表示单个组件的相位和幅度响应函数，可拼接形成功能电路 | https://arxiv.org/pdf/2009.05146 |
| 1.6 | 频率相关 S 参数 | 设计用于处理频率相关 S 参数的组件，允许频率扫描仿真 | https://arxiv.org/pdf/2009.05146 |

### 2.2 SiEPIC 兼容

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 2.1 | SiEPIC 库 | 包含 SiEPIC 模型库（`simphony.libraries.siepic`） | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 2.2 | SiEPIC Ebeam PDK | 使用 SiEPIC Ebeam PDK 库（已包含在 simphony 中） | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 2.3 | SiEPIC-Tools 互操作 | 与 KLayout 的 SiEPIC-Tools 扩展可选互操作，可解析 SiEPIC-Tools 创建的电路描述 | https://arxiv.org/pdf/2009.05146 |
| 2.4 | KLayout 电路仿真 | 能够直接在 KLayout 中设计的电路上运行仿真 | https://arxiv.org/pdf/2009.05146 |
| 2.5 | grating_coupler 模型 | 提供 SiEPIC grating_coupler 模型 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 2.6 | Y-branch 模型 | 提供 SiEPIC Y-branch 模型（分光和合光） | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 2.7 | ebeam_terminator 模型 | 提供 SiEPIC ebeam_terminator_te1550 模型 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |

### 2.3 子电路（Subcircuit）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 3.1 | Subcircuit 类 | 提供 `Subcircuit` 类用于构建子电路 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 3.2 | 子电路模式 | 支持子电路模式（subcircuit pattern），创建从其他模型生成新模型的方法 | https://simphonyphotonics.readthedocs.io/en/latest/_sources/tutorials/filters.ipynb |
| 3.3 | add 方法 | `circuit.add()` 添加组件到子电路 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 3.4 | connect_many | `circuit.connect_many()` 批量连接子电路组件 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 3.5 | 引脚分配 | 支持为子电路元素分配引脚（pins） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 3.6 | 环形谐振器构建 | 支持使用子电路模式构建环形谐振器 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 3.7 | Add-Drop 滤波器 | 支持使用子电路模式构建 Add-Drop 滤波器 | https://simphonyphotonics.readthedocs.io/en/latest/_sources/tutorials/filters.ipynb |

### 2.4 频率扫描（Frequency Sweep）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 4.1 | SweepSimulation | 提供 `SweepSimulation` 进行频率扫描仿真 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 4.2 | 频率范围设置 | 可设置扫描的起始和结束频率（如 1500e-9 到 1600e-9） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 4.3 | 波长单位 | Simphony 接受以米为单位的波长值 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 4.4 | 数据提取 | `res1.data()` 提取仿真数据，可按引脚获取 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 4.5 | 频率相关仿真 | 支持频率相关 S 参数仿真，允许频率扫描 | https://arxiv.org/pdf/2009.05146 |
| 4.6 | Nf 频率点 | 紧凑模型可包含 Nf 频率点的 S 参数，散射矩阵大小为 Nf × N × N | https://arxiv.org/pdf/2009.05146 |

### 2.5 比 Lumerical 快 20×

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 5.1 | 20× 加速 | 基准测试表明比 Lumerical INTERCONNECT 加速约 20 倍 | https://arxiv.org/pdf/2009.05146 |
| 5.2 | 文档声明 | 官方文档声明子网络增长算法比其他光子建模软件快 20 倍 | https://simphonyphotonics.readthedocs.io/en/stable/index.html |
| 5.3 | 准确性比较 | 与 Lumerical INTERCONNECT 比较准确性和速度 | https://arxiv.org/pdf/2009.05146 |
| 5.4 | 商业工具替代 | 旨在为缺乏商业工具的研究人员和教育工作者提供有用工具 | https://arxiv.org/pdf/2009.05146 |

### 2.6 参数扫描（Parameter Sweep）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 6.1 | MonteCarloSweepSimulation | 提供 `MonteCarloSweepSimulation` 进行 Monte Carlo 频率扫描仿真 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 6.2 | Monte Carlo 运行 | 支持指定 Monte Carlo 运行次数（runs） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 6.3 | 参数扰动 | 支持通过字典映射要扰动的参数到标准差（nm） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 6.4 | 多参数变化 | 支持同时变化多个参数（如 width 和 thickness） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 6.5 | 理想值提取 | Monte Carlo 数据位置 0 处存储理想值 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 6.6 | 半径变化 | 支持仅变化环形谐振器半径等单个参数 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |

### 2.7 可视化（Visualization）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 7.1 | matplotlib 集成 | 推荐 matplotlib 库可视化仿真结果 | https://simphonyphotonics.readthedocs.io/en/stable/index.html |
| 7.2 | 传输谱绘制 | 支持绘制传输谱（频率 vs 幅度） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 7.3 | Monte Carlo 绘图 | 支持 Monte Carlo 仿真结果多曲线绘制 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 7.4 | 眼图绘制 | 支持眼图输出绘制 | https://latitudeda.com/document/346 |
| 7.5 | 图表标注 | 支持图表标注（xlabel、ylabel、title、legend 等） | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |

### 2.8 SiPANN 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 8.1 | SiPANN 库 | 包含 SiPANN 模型库（`simphony.libraries.sipann`） | https://simphonyphotonics.readthedocs.io/en/latest/_modules/simphony/libraries/sipann.html |
| 8.2 | SimphonyWrapper | `SiPANN.scee_int.SimphonyWrapper` 将 SCEE 模型包装为 simphony 兼容 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 8.3 | 神经网络模型 | SiPANN 利用机器学习仿真光子器件，比完整 FDTD 仿真更快且精度相似 | https://simphonyphotonics.readthedocs.io/en/latest/_modules/simphony/libraries/sipann.html |
| 8.4 | gap_func_symmetric | 提供对称定向耦合器模型（gap_func_symmetric） | https://simphonyphotonics.readthedocs.io/en/latest/libs/sipann.html |
| 8.5 | gap_func_antisymmetric | 提供反对称定向耦合器模型（gap_func_antisymmetric） | https://simphonyphotonics.readthedocs.io/en/latest/libs/sipann.html |
| 8.6 | 半环模型 | 提供半环（Half Ring）模型 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |
| 8.7 | SCEE 集成 | SiPANN.scee_int 模块包装 SCEE 产生的所有模型供 simphony 使用 | https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html |

### 2.9 SAX 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 9.1 | SAX 模型定义 | Simphony 使用 SAX 定义模型和仿真电路 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 9.2 | JAX 计算引擎 | SAX 使用 JAX 作为计算引擎 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 9.3 | GPU 加速 | 如果模型定义适当且有 GPU，JAX 可为大型电路提供加速 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 9.4 | CPU 兼容 | 否则在 CPU 上运行良好 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 9.5 | 双精度配置 | 需在 JAX 初始化前设置双精度（`jax_enable_x64`） | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 9.6 | jax.numpy | 使用 jax.numpy 作为 NumPy 的替代 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 9.7 | 可调用模型 | SAX（及 Simphony）中的模型是返回散射参数字典的"可调用对象"（函数） | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 9.8 | 默认参数 | SAX 中的模型必须在函数签名中具有默认参数，不允许位置参数 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |

### 2.10 电路定义

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 10.1 | 网表编写 | 支持编写网表（netlist）定义电路 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 10.2 | 可调用仿真 | 支持使用可调用对象（callables）进行仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 10.3 | 便捷类仿真 | 支持使用便捷类（convenience classes）进行仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 10.4 | SPICE 类方法 | 使用 SPICE 类方法定义光子电路 | https://pypi.org/project/simphony/ |
| 10.5 | 复杂仿真能力 | 提供复杂仿真能力（Complex simulation capabilities） | https://pypi.org/project/simphony/ |

### 2.11 量子仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 11.1 | 量子仿真器 | 提供 simphony 量子仿真器模拟光子电路 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.2 | 经典转量子 | 将电路的经典 S 参数转换为量子兼容形式 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.3 | 酉矩阵转换 | 通过添加额外真空态模式将 S 参数转换为酉矩阵以考虑损耗 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.4 | 均匀损耗假设 | 假设电路中任何损耗在所有端口上均匀分布 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.5 | 量子态 | 支持量子态（Quantum states）仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.6 | 高斯态 | 支持高斯态（Gaussian states）仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.7 | 量子谐振子 | 支持量子谐振子（Quantum harmonic oscillator）仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 11.8 | 海森堡不确定性 | 支持海森堡不确定性原理（Heisenberg uncertainty principle）仿真 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |

### 2.12 模型框架

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 12.1 | 可扩展框架 | 提供简单可扩展的框架定义光子组件紧凑模型 | https://pypi.org/project/simphony/ |
| 12.2 | 自定义组件 | 提供框架允许最终用户轻松包装或添加自定义组件 | https://arxiv.org/pdf/2009.05146 |
| 12.3 | 模型库 | 包含 SiEPIC 和 SiPANN 的模型库 | https://pypi.org/project/simphony/ |
| 12.4 | 预仿真组件 | 默认库中的许多紧凑模型是预仿真组件（固定参数） | https://arxiv.org/pdf/2009.05146 |
| 12.5 | 插件兼容 | 可编写插件以提供与现有布局工具的兼容性 | https://arxiv.org/pdf/2009.05146 |

### 2.13 平台与安装

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 13.1 | 跨平台 | 跨平台：在 Windows、MacOS 和 Linux 上运行 | https://pypi.org/project/simphony/ |
| 13.2 | Python 3 脚本 | 完全可使用 Python 3 脚本化 | https://pypi.org/project/simphony/ |
| 13.3 | pip 安装 | 可通过 pip 安装：`pip install simphony` | https://pypi.org/project/simphony/ |
| 13.4 | Python 3.9+ | 需要 Python >=3.9 | https://pypi.org/project/simphony/ |
| 13.5 | 可选依赖 | 提供可选额外依赖：cpu、gdsfactory、sipann、dev、doc、test | https://pypi.org/project/simphony/ |
| 13.6 | MIT 协议 | 在 MIT 协议下提供的免费开源软件 | https://pypi.org/project/simphony/ |

### 2.14 经典仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 14.1 | ClassicalSim | 提供 `ClassicalSim` 进行经典仿真 | https://simphonyphotonics.readthedocs.io/en/latest/_sources/tutorials/filters.ipynb |
| 14.2 | 线性 PIC 仿真 | 专为线性 PIC（光子集成电路）仿真设计 | https://arxiv.org/pdf/2009.05146 |
| 14.3 | 时域仿真潜力 | 支持时域仿真潜力（虽然尚未实现，可使用脉冲响应函数执行） | https://arxiv.org/pdf/2009.05146 |

### 2.15 教育与文档

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 15.1 | 在线文档 | 文档在线托管 | https://simphonyphotonics.readthedocs.io/en/stable/ |
| 15.2 | 教程 | 提供入门教程（Introduction to simphony） | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/intro.html |
| 15.3 | MZI 教程 | 提供 Mach-Zehnder 干涉仪教程 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html |
| 15.4 | Add-Drop 滤波器教程 | 提供 Add-Drop 滤波器教程 | https://simphonyphotonics.readthedocs.io/en/latest/_sources/tutorials/filters.ipynb |
| 15.5 | 量子仿真教程 | 提供量子仿真教程 | https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html |
| 15.6 | Photonics-Bootcamp | 与 Photonics-Bootcamp 集成提供教育内容 | https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html |
| 15.7 | 学术引用 | 提供学术引用格式（BibTeX） | https://simphonyphotonics.readthedocs.io/en/stable/index.html |
| 15.8 | 贡献指南 | 提供贡献指南（Contributing） | https://simphonyphotonics.readthedocs.io/en/stable/index.html |

---

## 3. 功能点统计

| 类别 | 功能点数量 |
|---|---|
| S 参数级联（Subnetwork Growth） | 6 |
| SiEPIC 兼容 | 7 |
| 子电路（Subcircuit） | 7 |
| 频率扫描（Frequency Sweep） | 6 |
| 比 Lumerical 快 20× | 4 |
| 参数扫描（Parameter Sweep） | 6 |
| 可视化（Visualization） | 5 |
| SiPANN 集成 | 7 |
| SAX 集成 | 8 |
| 电路定义 | 5 |
| 量子仿真 | 8 |
| 模型框架 | 5 |
| 平台与安装 | 6 |
| 经典仿真 | 3 |
| 教育与文档 | 8 |
| **总计** | **91** |

---

## 4. 参考来源

1. simphony GitHub: https://github.com/BYUCamachoLab/simphony
2. simphony 官方文档: https://simphonyphotonics.readthedocs.io/en/stable/index.html
3. simphony PyPI: https://pypi.org/project/simphony/
4. simphony arXiv 论文: https://arxiv.org/pdf/2009.05146
5. MZI 教程: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
6. 量子仿真教程: https://simphonyphotonics.readthedocs.io/en/stable/tutorials/quantum.html
7. Add-Drop 滤波器教程: https://simphonyphotonics.readthedocs.io/en/latest/_sources/tutorials/filters.ipynb
8. SiPANN simphony 集成: https://sipann.readthedocs.io/en/stable/tutorials/Simphony.html
9. simphony SiPANN 源码: https://simphonyphotonics.readthedocs.io/en/latest/_modules/simphony/libraries/sipann.html
10. Photonics-Bootcamp MZI: https://byucamacholab.github.io/Photonics-Bootcamp/pages/mzi.html
11. CamachoLab: https://camacholab.byu.edu/
12. 学术引用: S. Ploeg, H. Gunther and R. M. Camacho, "Simphony: An Open-Source Photonic Integrated Circuit Simulation Framework," Computing in Science & Engineering, vol. 23, no. 1, pp. 65-74, 2021, doi: 10.1109/MCSE.2020.3012099
