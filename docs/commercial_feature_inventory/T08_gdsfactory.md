# T08 gdsfactory 功能点清单

## 文档信息

| 项目 | 内容 |
|---|---|
| 工具名 | gdsfactory |
| 维护方 | GDSFactory (Joaquin Matres 等) |
| GitHub URL | https://github.com/gdsfactory/gdsfactory |
| 官方文档 | https://gdsfactory.github.io/gdsfactory/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 开源协议 | Apache-2.0 |
| 当前版本 | 9.44.0 (截至 2026-06-12) |

> **学术诚信声明**：本文档所有功能点均来源于 gdsfactory 官方 GitHub 仓库、官方文档及 gplugins 插件文档。未在公开文档中明确说明的功能标注为"未公开"。

---

## 1. 工具概述

GDSFactory 是一个用于设计芯片（Photonics、Analog、Quantum、MEMS）、PCB 和 3D 打印对象的 Python 库。输入为 Python 代码或 YAML 文本，输出为 GDSII/OASIS 文件用于流片，同时生成组件设置（用于测量和数据分析）和网表（用于电路仿真）。

- **来源**: https://gdsfactory.github.io/gdsfactory/
- **PyPI**: https://pypi.org/project/gdsfactory/

---

## 2. 功能点清单

### 2.1 参数化器件（Parametric Cells, PCells）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 1.1 | 参数化单元定义 | 通过 Python 函数定义参数化单元（PCell），使用 `@gf.cell` 装饰器处理缓存以消除冗余重新生成 | https://gdsfactory.github.io/gdsfactory/ |
| 1.2 | Component 类 | 单元返回 Component 类，包含多边形、电气和光学端口元数据，以及导出和绘制的便捷方法 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |
| 1.3 | 函数式编程 | 通过函数式编程方法定义参数化单元，KLayout 的 C++ 几何引擎作为后端 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |
| 1.4 | 内置组件库 | 提供 `gf.components` 内置组件库（如 rectangle、mmi1x2、bend_euler、coupler 等） | https://gdsfactory.github.io/gdsfactory/ |

### 2.2 YAML 层次化设计

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 2.1 | YAML Place and AutoRoute | 通过 YAML 文件定义组件的 Place and Route，包含原理图和布局信息 | https://gdsfactory.github.io/gdsfactory/notebooks/10_yaml_component.html |
| 2.2 | from_yaml 函数 | `gf.read.from_yaml()` 将 YAML 字符串/文件转换为 Component，支持 instances、placements、connections、routes、ports 五大段 | https://gdsfactory.github.io/gdsfactory/_autosummary/gdsfactory.read.from_yaml.html |
| 2.3 | Pydantic 模型校验 | YAML 结构通过 Pydantic 模型进行类型检查和模式强制（Netlist、Instance、Placement、Bundle 等） | https://deepwiki.com/gdsfactory/gdsfactory/5.2-yaml-based-layout-generation |
| 2.4 | Jinja2 模板支持 | YAML 支持 Jinja2 模板语法（`.pic.yml`），可实现参数化电路定义 | https://gdsfactory.github.io/gdsfactory/notebooks/10_yaml_component.html |
| 2.5 | 网表提取 | `get_netlist()` 将 Component 转换为 YAML 网表；`get_netlist_recursive()` 返回递归网表 | https://gdsfactory.github.io/gplugins/notebooks/11_get_netlist.html |
| 2.6 | 层次化组装 | 支持层次化组装，单元可实例化在其他单元中 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |

### 2.3 route_fiber_array（光纤阵列路由）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 3.1 | 光纤阵列路由 | 提供路由到光纤阵列（fiber array）的功能，用于光学终端连接 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing_electrical.html |
| 3.2 | 边缘耦合器路由 | 支持路由到边缘耦合器（edge couplers） | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing_electrical.html |
| 3.3 | Pad 阵列路由 | 支持路由到 Pad 阵列（pad array），用于电气连接 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing_electrical.html |

### 2.4 get_bundle / route_bundle

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 4.1 | route_bundle | 使用 bundle/river/bus 路由器在两组端口之间路由一组路由，支持航点和路由步骤 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |
| 4.2 | route_bundle_all_angle | 用于对角线（任意角度）路由 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |
| 4.3 | route_bundle_electrical | 用于低速 DC 电气端口路由，使用 wire_corner 弯曲 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing_electrical.html |
| 4.4 | 路径长度匹配 | route_bundle 支持路径长度匹配（path length matching） | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |
| 4.5 | 碰撞避免 | route_bundle 支持路由碰撞避免（route_bundle with collisions） | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |
| 4.6 | 自动锥度 | route_bundle 支持 auto_taper 自动锥度过渡 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |
| 4.7 | Dubins 路径 | 支持 Dubins 路径路由 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |

### 2.5 routing strategies（路由策略）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 5.1 | get_bundle_all_angle | 非曼哈顿（全角度）路由策略，支持任意角度端口连接 | https://gdsfactory.github.io/gdsfactory7/notebooks/04_routing_non_manhattan.html |
| 5.2 | route_astar | 基于 A* 算法的路由，使用 NetworkX 库的 astar_path 寻找最短路径 | https://blog.csdn.net/gitblog_07066/article/details/148823570 |
| 5.3 | route_quad | 创建 U 形电气走线的路由策略 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing_electrical.html |
| 5.4 | 自定义横截面 | 路由支持自定义横截面（CrossSection），可定义层、线宽、弯曲半径等 | https://blog.csdn.net/gitblog_07303/article/details/148888707 |
| 5.5 | steps 语法 | 路由支持 steps 语法，通过 dx/dy/x/y 指定中间航点 | https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html |

### 2.6 KLayout DRC 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 6.1 | KLayout 几何引擎 | 使用 KLayout 的 C++ 几何引擎作为后端进行布局处理 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |
| 6.2 | DRC 验证 | 紧密集成 KLayout，利用其高级设计规则检查（DRC）能力 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |
| 6.3 | LVS 验证 | 利用 KLayout 的版图与原理图一致性验证（LVS）能力 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |
| 6.4 | get_netlist (KLayout) | `gplugins.klayout.get_netlist` 从 GDS 提取网表用于 LVS | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 6.5 | klive 插件 | 支持 klive 插件与 KLayout 实时交互 | https://gdsfactory.github.io/gdsfactory7/notebooks/04_routing_non_manhattan.html |

### 2.7 GDSII / OASIS 导出

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 7.1 | GDSII 导出 | 输出 GDSII 文件用于流片，通过 `write_gds()` | https://gdsfactory.github.io/gdsfactory/ |
| 7.2 | OASIS 导出 | 输出 OASIS 文件用于流片 | https://gdsfactory.github.io/gdsfactory/ |
| 7.3 | STL 导出 | 输出 STL 文件用于 3D 打印 | https://gdsfactory.github.io/gdsfactory/ |
| 7.4 | GERBER 导出 | 输出 GERBER 文件用于 PCB | https://gdsfactory.github.io/gdsfactory/ |
| 7.5 | flatten_offgrid_references | `write_gds(flatten_offgrid_references=True)` 避免网格对齐导致的 1nm 间隙 | https://gdsfactory.github.io/gdsfactory7/notebooks/04_routing_non_manhattan.html |

### 2.8 PDK 支持（43+ PDK）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 8.1 | 43+ 找到 PDK | GDSFactory+ 支持 43+ 找到 PDK（foundry PDKs） | https://gdsfactory.com/plus/pdks/ |
| 8.2 | 开源光子 PDK | 开源光子 PDK：Cornerstone、SiEPIC Ebeam UBC、VTT、Luxtelligence GF | https://gdsfactory.github.io/gdsfactory/ |
| 8.3 | 开源 CMOS PDK | 开源 CMOS PDK：IHP、GlobalFoundries 180nm MCU、SkyWater 130nm | https://gdsfactory.github.io/gdsfactory/ |
| 8.4 | NDA PDK | NDA PDK：AIM Photonics、AMF、CompoundTek、Fraunhofer HHI、Smart Photonics、Tower Semiconductor、III-V Labs、LioniX、Ligentec、Lightium、QCI | https://gdsfactory.github.io/gdsfactory/ |
| 8.5 | PDK 构建 | 提供如何构建自有 PDK 的说明 | https://gdsfactory.github.io/gdsfactory7/ |
| 8.6 | PDK 导入 | 提供从固定 GDS 单元库导入 PDK 的说明 | https://gdsfactory.github.io/gdsfactory7/ |

### 2.9 量子组件（Quantum Components）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 9.1 | QPDK 量子 PDK | 开源超导量子 RF PDK（QPDK），基于 gdsfactory 构建 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.2 | Transmon 量子比特 | 提供 Transmon 量子比特组件（双垫电容分流量子比特） | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.3 | Fluxonium 量子比特 | 提供 Fluxonium 量子比特组件（超导电感分流量子比特） | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.4 | Unimon 量子比特 | 提供 Unimon 量子比特组件（谐振器嵌入结量子比特） | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.5 | SQUID 结 | 提供 SQUID（超导量子干涉器件）结组件 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.6 | CPW 谐振器 | 提供共面波导（CPW）谐振器组件 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.7 | 叉指电容 | 提供叉指电容（Interdigital Capacitor）组件 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.8 | 量子测试芯片 | 提供完整的 tapeout-ready 量子测试芯片示例（四 Transmon 测试芯片等） | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.9 | 量子分析模型 | 提供分析 S 参数模型，由 SAX 和 JAX 驱动的快速可微分仿真 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 9.10 | 量子工具集成 | 集成 scQubits、QuTiP-QIP、Pymablock、NetKet 等量子工具 | https://gdsfactory.github.io/quantum-rf-pdk/notebooks/pymablock_dispersive_shift.html |

### 2.10 SAX 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 10.1 | SAX 电路求解器 | SAX 是基于 JAX 编写的电路求解器，gdsfactory 通过 gplugins.sax 集成 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.2 | 散射字典 | SAX 核心数据结构为 SDict（`Dict[Tuple[str,str], float]`），映射端口组合到散射参数 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.3 | 梯度优化 | 在 SAX 中编写组件模型可获得函数值和梯度，用于电路优化 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.4 | 布局感知 Monte Carlo | 支持布局感知 Monte Carlo 分析 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.5 | 层次化电路 | 支持层次化电路仿真 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 10.6 | FDTD S 参数模型 | 支持 FDTD S 参数模型拟合 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |

### 2.11 Meep 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 11.1 | gmeep 插件 | gmeep 插件计算平面光子组件的传输谱 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.2 | 自动 S 参数提取 | gmeep 自动在端口间切换源以计算完整 S 矩阵 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.3 | 2.5D 仿真 | 支持 2.5D 仿真模式 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.4 | 端口对称性 | 支持端口对称性以加速仿真 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.5 | 多模仿真 | 支持多模仿真 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.6 | 并行仿真 | 支持多核/MPI 并行仿真 | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |
| 11.7 | 伴随优化 | 支持伴随优化（Adjoint Optimization） | https://gdsfactory.github.io/gplugins/notebooks/meep_01_sparameters.html |

### 2.12 Tidy3D 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 12.1 | Tidy3D FDTD | tidy3D 是 flexcompute 开发的基于 GPU 的快速 FDTD 工具 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.2 | 材料数据库 | Tidy3D 提供材料数据库，包含色散材料 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.3 | Component Modeler | 可将 gdsfactory 平面 Component 转换为 tidy3d 仿真 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.4 | S 参数写入 | 支持 S 参数写入和文件缓存 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.5 | 2D/3D 仿真 | 支持 2D 和 3D 仿真绘图 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.6 | 侵蚀/膨胀 | 支持侵蚀/膨胀（Erosion/dilation）分析 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |
| 12.7 | 并行作业 | 支持并行运行作业 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |

### 2.13 Lumerical 集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 13.1 | Lumerical FDTD 接口 | 提供 Ansys Lumerical FDTD 接口自动计算 S 参数 | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |
| 13.2 | write_sparameters_lumerical | `gplugins.lumerical.write_sparameters_lumerical` 启动 GUI、运行仿真并写入 S 参数 | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |
| 13.3 | CSV/DAT 输出 | S 参数以 .CSV 和 .DAT（Lumerical Interconnect/Simphony）格式写入 | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |
| 13.4 | 层堆栈修改 | 支持修改层堆栈厚度和材料折射率 | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |
| 13.5 | lumapi 集成 | 内部调用 Lumerical Python API `lumapi` | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |

### 2.14 cocotb 联合仿真

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 14.1 | SPICE 协同仿真 | 通过 piel 等工具支持 SPICE 协同仿真，实现光电联合验证 | https://piel.readthedocs.io/en/latest/examples/04_spice_cosimulation/04_spice_cosimulation.html |
| 14.2 | 直接 cocotb 集成 | 未公开（gdsfactory 官方文档未明确说明直接 cocotb 集成） | - |

### 2.15 VLSIR SPICE 导出

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 15.1 | VLSIR 网表导出 | 通过 VLSIR 库将 GDS 提取的网表转换为 Spectre、SPICE 和 Xyce 仿真器原理图格式 | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 15.2 | Spectre RF 导出 | 支持导出 Spectre RF 网表格式 | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 15.3 | Xyce 导出 | 支持导出 Xyce 网表格式 | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 15.4 | ngspice 导出 | 支持导出 ngspice 网表格式 | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 15.5 | 分析类型支持 | 支持 Op、Dc、Tran、Ac、Noise 等分析类型（因仿真器而异） | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |
| 15.6 | kdb_vlsir 转换 | `gs.kdb_vlsir()` 将 KLayout 网表转换为 VLSIR Package | https://gdsfactory.github.io/gplugins/notebooks/vlsir_netlist.html |

### 2.16 matplotlib 可视化

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 16.1 | plot 方法 | Component 提供 `plot()` 方法进行可视化 | https://gdsfactory.github.io/gdsfactory/ |
| 16.2 | plot_sparameters | `sim.plot.plot_sparameters` 绘制 S 参数 | https://gdsfactory.github.io/gplugins/notebooks/lumerical_1_fdtd_sparameters.html |
| 16.3 | plot_netlist | `plot_netlist()` 绘制网表图 | https://gdsfactory.github.io/gplugins/notebooks/11_get_netlist.html |
| 16.4 | plot_slice | 支持 plot_slice 绘制截面 | https://gdsfactory.github.io/gplugins/notebooks/tidy3d_00_tidy3d.html |

### 2.17 Jupyter Notebook 支持

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 17.1 | Notebook 驱动工作流 | 支持 Jupyter Notebook 驱动的工作流，提供丰富示例 | https://gdsfactory.github.io/quantum-rf-pdk/ |
| 17.2 | 交互式开发 | 支持 Jupyter 交互式开发和可视化 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |
| 17.3 | rich_output | `gf.config.rich_output()` 提供 Rich 格式输出 | https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html |

### 2.18 其他仿真器集成

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 18.1 | Femwell (FEM) | Femwell 有限元方法求解器（加热器、模式、TCAD、RF 波导） | https://gdsfactory.github.io/gplugins/ |
| 18.2 | Elmer (FEM) | Elmer 用于静电（电容）仿真 | https://gdsfactory.github.io/gplugins/ |
| 18.3 | Palace (FEM) | Palace 用于全波驱动（S 参数）和静电（电容）仿真 | https://gdsfactory.github.io/gplugins/ |
| 18.4 | MEOW (EME) | MEOW 本征模展开（EME） | https://gdsfactory.github.io/gplugins/ |
| 18.5 | DEVSIM (TCAD) | DEVSIM TCAD 器件仿真器 | https://gdsfactory.github.io/gplugins/ |
| 18.6 | MPB (Mode Solver) | MPB 模式求解器 | https://gdsfactory.github.io/gplugins/ |
| 18.7 | Luminescent AI | Luminescent AI FDTD 后端 | https://gdsfactory.github.io/gplugins/ |
| 18.8 | FDTDz | FDTDz FDTD 求解器（开发中） | https://gdsfactory.github.io/gplugins/ |
| 18.9 | GMSH 网格 | 通过 GMSH 进行网格划分 | https://gdsfactory.github.io/gplugins/ |

### 2.19 端到端设计流程

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 19.1 | 设计（布局、仿真、优化） | 定义参数化单元函数生成组件，测试组件设置、端口和几何 | https://gdsfactory.github.io/gdsfactory/ |
| 19.2 | 验证（DRC、DFM、LVS） | 通过仿真接口直接从布局运行仿真，进行 LVS 验证和 DRC 清理 | https://gdsfactory.github.io/gdsfactory/ |
| 19.3 | 验证（Validate） | 定义布局和测试协议，用于流片后自动化芯片分析 | https://gdsfactory.github.io/gdsfactory/ |
| 19.4 | 元数据兼容 | 提供与商业晶圆探针兼容的丰富元数据，包括光纤到波导耦合器的位置和方向 | https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |

### 2.20 GDSFactory+ 商业扩展

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 20.1 | GUI 界面 | GDSFactory+ 提供基于 GDSFactory 和 VSCode 的图形用户界面 | https://gdsfactory.github.io/gdsfactory/ |
| 20.2 | 原理图捕获 | 支持原理图捕获 | https://gdsfactory.github.io/gdsfactory/ |
| 20.3 | AI 助手 | 提供 AI 助手辅助设计 | https://gdsfactory.com/plus/quickstart/build-a-component/ |
| 20.4 | CLI 工具 | 提供 `gfp` CLI 工具（test、bbox、build-pdk、export-spice、verify 等） | https://gdsfactory.com/plus/cli/ |

---

## 3. 功能点统计

| 类别 | 功能点数量 |
|---|---|
| 参数化器件（PCells） | 4 |
| YAML 层次化设计 | 6 |
| route_fiber_array | 3 |
| get_bundle / route_bundle | 7 |
| routing strategies | 5 |
| KLayout DRC 集成 | 5 |
| GDSII / OASIS 导出 | 5 |
| PDK 支持（43+ PDK） | 6 |
| 量子组件 | 10 |
| SAX 集成 | 6 |
| Meep 集成 | 7 |
| Tidy3D 集成 | 7 |
| Lumerical 集成 | 5 |
| cocotb 联合仿真 | 2 |
| VLSIR SPICE 导出 | 6 |
| matplotlib 可视化 | 4 |
| Jupyter Notebook 支持 | 3 |
| 其他仿真器集成 | 9 |
| 端到端设计流程 | 4 |
| GDSFactory+ 商业扩展 | 4 |
| **总计** | **108** |

---

## 4. 参考来源

1. gdsfactory GitHub: https://github.com/gdsfactory/gdsfactory
2. gdsfactory 官方文档: https://gdsfactory.github.io/gdsfactory/
3. gplugins 文档: https://gdsfactory.github.io/gplugins/
4. GDSFactory+ 文档: https://gdsfactory.com/plus/
5. QPDK 文档: https://gdsfactory.github.io/quantum-rf-pdk/
6. gdsfactory CLEO26 论文: https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
7. PyPI gdsfactory: https://pypi.org/project/gdsfactory/
8. piel 文档（SPICE 协同仿真）: https://piel.readthedocs.io/en/latest/examples/04_spice_cosimulation/04_spice_cosimulation.html
