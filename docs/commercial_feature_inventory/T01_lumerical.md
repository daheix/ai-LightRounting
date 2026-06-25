# T01 Ansys Lumerical 商业光子 EDA 工具功能点清单

- **工具名称**: Ansys Lumerical
- **厂商**: Ansys (原 Lumerical Solutions)
- **官网 URL**: https://www.ansys.com/products/optics/ansys-lumerical
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **学术诚信声明**: 本文档所有功能点均来源于 Ansys 官网及 Ansys Optics 知识中心公开文档，未公开项已明确标注。

---

## 一、FDTD 模块功能点

Ansys Lumerical FDTD 是光子组件仿真的行业标准，集成 FDTD、RCWA、STACK 求解器于单一设计环境。

- **FDTD 求解器 (Finite Difference Time Domain)**: 三维时域有限差分求解器，直接求解 Maxwell 方程，支持任意色散材料与亚波长结构建模，是光子组件仿真的"gold-standard"。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **RCWA 求解器 (Rigorous Coupled-Wave Analysis)**: 严格耦合波分析求解器，用于周期性结构（如衍射光栅、超表面）的高效分析，支持 theta/phi 二维角度映射、可选择的反向传播模式定义。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd) ；[https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **STACK 求解器**: 用于多层薄膜结构分析，适用于 uLED、CMOS 图像传感器等多层涂层器件。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **亚像素平滑 / Conformal Mesh (共形网格)**: 高级共形网格算法 (conformal mesh)，在相对粗糙网格下仍可获得高精度结果，支持 PEC 材料的 "snap to PEC" 选项，2025 R2.3 中 PEC 网格化峰值内存降低约 40%。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd) ；[https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **PML 边界条件 (Perfectly Matched Layer)**: 完美匹配层吸收边界条件，用于截断开放仿真域。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **色散材料 (Dispersive Materials)**: 支持频率相关（色散）材料建模，包括各向异性材料与非线性材料。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **各向异性材料 (Anisotropic Materials)**: 支持各向异性材料建模。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **分布式 GPU / HPC / Cloud 计算**: 支持 HPC、GPU 和云端可扩展计算，支持 Ansys Cloud Burst Compute（Amazon EC2 G6e 实例，最多 8 块 NVIDIA L40S GPU），Enterprise 许可证支持持久求解器签出 (Persistent License Checkout) 以提升批处理效率。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd) ；[https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **伴随优化 / 逆向设计 (Adjoint Optimization / Inverse Design via Lumopt)**: 内置 Lumopt 伴随优化模块，支持梯度逆向设计；2025 R2.3 新增 PortTransmission 类，可直接使用 FDTD ports 作为 Figure of Merit，无需手动放置 DFT 监视器与 ModeMatch。来源: [https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **脚本 API (Scripting API)**: 支持 Lumerical 脚本语言、Python 与 MATLAB 自动化 API。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd) ；[https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **PyLumerical**: 2025 R2.3 引入的现代化 Python API，兼容 PyAnsys 生态，可通过 pip 安装，支持与 PyOptislang、PyAEDT、PySpeos 等集成。来源: [https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **材料库 (Material Library)**: 内置材料库，支持从测量数据导入材料参数。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **监视器 (Monitors)**: 支持多种监视器类型（DFT 监视器、时域监视器、功率监视器等），用于记录场、功率、模式等结果。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **光源类型 (Source Types)**: 支持多种光源类型，包括模式光源、平面波、高斯光束、偶极子等。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **Foundry 兼容与 PDK 支持**: 与 foundry PDK 兼容，支持定制化设计，可与 CML Compiler、Multiphysics 求解器、Speos、Zemax 及第三方 EPDA 工具协同。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)
- **多物理与多尺度工作流 (Multiphysics & Multiscale Workflows)**: 支持多物理与多尺度仿真工作流。来源: [https://www.ansys.com/products/optics/fdtd](https://www.ansys.com/products/optics/fdtd)

---

## 二、MODE 模块功能点

Ansys Lumerical MODE 是光波导与耦合器求解器，集成 FDE、varFDTD、EME 三种求解器。

- **FDE 求解器 (Finite Difference Eigenmode)**: 有限差分本征模求解器，用于任意截面波导/光纤的模式分析，可表征直波导与弯曲波导。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode) ；[https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction](https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction)
- **varFDTD 求解器 (2.5D Variational FDTD)**: 2.5D 变分 FDTD 求解器，以 2D FDTD 等效计算时间达到接近 3D FDTD 的精度，适用于宽带、全向光传播的波导器件仿真。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **EME 求解器 (Bidirectional Eigenmode Expansion)**: 双向本征模展开求解器，频域方法，完全矢量化和双向，计算成本随传播距离缩放性优异，适用于长锥形器与周期性器件；支持 CVCS (Continuously Varying Cross-sectional Subcell) 方法。来源: [https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction](https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction)
- **弯曲损耗分析 (Bend Loss Analysis)**: 支持波导弯曲损耗分析。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **各向异性材料 (Anisotropic Materials)**: 支持各向异性材料建模。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **螺旋波导 (Helical Waveguides)**: 支持螺旋波导分析。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **重叠分析 (Overlap Analysis)**: 支持模式重叠积分分析，用于计算模式耦合效率。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **磁光波导分析 (Magneto-optical Waveguide Analysis)**: 支持磁光波导分析。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **高级共形网格 (Advanced Conformal Mesh)**: 高级共形网格求解器，在粗糙网格下仍保持高精度。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **Foundry 兼容自动层构建器 (Foundry Compatible Automated Layer Builder)**: 与 foundry 兼容的自动化层构建器。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **温度与电荷密度剖面导入 (Spatially Varying Temperature and Charge Density Profile Import)**: 支持空间变化的温度和电荷密度剖面导入，用于多物理仿真。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **传播距离扫描 (Propagation Length Scan)**: EME 在分析模式下可任意改变各段传播距离而无需重复模式计算，非常适合器件长度扫描。来源: [https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction](https://optics.ansys.com/hc/en-us/articles/360034396614-MODE-EigenMode-Expansion-EME-solver-introduction)
- **OptoCompiler 集成**: 2026 R1 起 MODE 与 Synopsys OptoCompiler 直接集成。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)
- **PyLumerical 自动化**: 支持 PyLumerical Python API 自动化。来源: [https://www.ansys.com/en-in/products/optics/mode](https://www.ansys.com/en-in/products/optics/mode)

---

## 三、INTERCONNECT 模块功能点

Ansys Lumerical INTERCONNECT 是光子集成电路（PIC）仿真器，支持经典与量子 PIC 仿真。

- **时域分析 (Time Domain Analysis)**: 暂态样本模式 (Transient Sample Mode) 与暂态块模式 (Transient Block Mode) 仿真。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect) ；[https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **频域分析 (Frequency Domain Analysis)**: 支持频域分析。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **多模式 / 多通道 / 双向支持 (Multimode, Multichannel, Bidirectional)**: 支持多模式、多通道和双向光子电路仿真。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **混合信号表示 (Mixed Signal Representation)**: 支持混合信号表示。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **高级优化 (Advanced Optimization)**: 内置高级优化功能。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **参数扫描 (Parameter Sweeps)**: 支持自动参数扫描。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **统计分析 (Statistical Analysis)**: 支持 Monte Carlo 分析与 Corner 分析，评估工艺变异对电路功能的影响。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect) ；[https://simutechgroup.com/ansys-software/optical/ansys-lumerical-interconnect](https://simutechgroup.com/ansys-software/optical/ansys-lumerical-interconnect)
- **光子紧凑模型库 (Photonic Compact Model Library, CML)**: 内置光子紧凑模型库，支持被动与主动光电组件。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **量子光子电路仿真器 (qINTERCONNECT)**: 专用量子光子电路仿真器，2023 R2 性能提升使相同运行时间下通道/频率数翻倍，支持微环谐振腔中的自发四波混频。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **行波激光器模型 (Travelling Wave Laser Model)**: 内置行波激光器模型。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **电子-光子协同仿真 (Electronic-Photonic Co-Simulation)**: 支持电子-光子协同仿真，包括 Python 协同仿真 API (runitialize/runstep/setValue/getValue/runfinalize)。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect) ；[https://optics.ansys.com/hc/en-us/articles/360034936773](https://optics.ansys.com/hc/en-us/articles/360034936773)
- **EDA 互操作性 (EDA Interoperability)**: 支持 SDL、LVS、DRC 等设计工作流，与多个 EDA 平台兼容；2026 R1 起支持 Synopsys OptoCompiler/PrimeWave 中选择 INTERCONNECT 作为光子电路仿真器。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **层次化原理图编辑器 (Hierarchical Schematic Editor)**: 支持层次化系统设计。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **PIC 元件库 (PIC Element Libraries)**: 包含大量原始元件与 foundry 特定 PDK 元件。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **CML 开发与分发 (CML Development and Distribution)**: 支持加密黑盒 CML 组件，安全分发专有设计。来源: [https://simutechgroup.com/ansys-software/optical/ansys-lumerical-interconnect](https://simutechgroup.com/ansys-software/optical/ansys-lumerical-interconnect)
- **可视化与数据分析 (Visualization & Data Analysis)**: 内置可视化与数据分析工具，支持眼图、BER 估计等。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **非线性波导原始模型 (Non-Linear Waveguide Primitive Model)**: 支持 LiNbO3 非线性波导建模，支持短脉冲与 CW 泵浦及周期极化调谐。来源: [https://www.ansys.com/products/photonics/interconnect](https://www.ansys.com/products/photonics/interconnect)
- **封装与热管理多物理工作流**: 支持封装和热管理的多物理工作流。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **PyLumerical 自动化**: 支持 PyLumerical Python API 自动化。来源: [https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)

---

## 四、CML Compiler 模块功能点

Ansys Lumerical CML Compiler 用于光子 PDK 的紧凑模型库开发，从单一数据源自动生成 INTERCONNECT 与 Verilog-A 紧凑模型库。

- **版本控制 CML (Version-controlled CMLs)**: 自动、可复现地生成版本控制的紧凑模型库。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **模型加密 (Model Encryption for IP Protection)**: 模型加密以保护 IP。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **结构化输入模板与数据验证 (Structured Input Templates and Data Validation)**: 提供结构化输入模板与数据验证。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **自动化测试台生成 (Automated Testbench Generation)**: 自动生成测试台用于 QA 测试。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **跨平台模型生成 (Cross-platform Model Generation)**: 跨平台模型生成。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **INTERCONNECT 与 Verilog-A 模型**: 同时生成 INTERCONNECT 与 photonic Verilog-A 紧凑模型。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **测量数据模型校准 (Model Calibration using Measurement Data)**: 使用测量数据进行模型校准。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **固定与参数化模型 (Fixed and Parameterized Models)**: 支持固定模型与参数化模型。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **参数化与统计模型 (Parameterized and Statistical Models)**: 支持参数化与统计模型，可生成统计启用的库 (Statistical Enablement)。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **IBIS-AMI 降阶模型 (IBIS-AMI Reduced Order Models)**: 2026 R1 引入基于机器学习的 IBIS-AMI 降阶模型生成，用于信号完整性分析与高速接口仿真。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **内置模型数据编辑器 (Built-in Model Data Editor)**: 2026 R1 引入交互式 GUI，支持多标签页编辑、矩阵与向量编辑器。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **PyLumerical 自动化**: 2026 R1 起支持 PyLumerical 自动化工具。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)
- **自动化模型数据收集向导 (Automated Data Collection Wizards)**: 2025 R2.3 引入四个 GUI 向导，用于波导、s-parameter (固定)、s-parameter (参数化)、热相移器的快速紧凑模型生成。来源: [https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes](https://optics.ansys.com/hc/en-us/articles/46555216210707-2025-R2-3-Release-Notes)
- **命令行接口 (Command Line Interface)**: 通过 cml-compiler 命令行工具控制，支持 template/rename/delete/validate/library/install 等子命令。来源: [https://optics.ansys.com/hc/en-us/articles/360037138374-Command-line-interface](https://optics.ansys.com/hc/en-us/articles/360037138374-Command-line-interface)
- **单一数据源 (Single Data Source)**: 源数据可来自实验测量、2D/3D 物理仿真或二者结合。来源: [https://www.ansys.com/products/optics/cml-compiler](https://www.ansys.com/products/optics/cml-compiler)

---

## 功能点统计

| 模块 | 功能点数量 |
|------|-----------|
| FDTD | 16 |
| MODE | 14 |
| INTERCONNECT | 20 |
| CML Compiler | 15 |
| **总计** | **65** |
