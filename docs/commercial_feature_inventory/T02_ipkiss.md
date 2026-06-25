# T02 Luceda IPKISS 商业光子 EDA 工具功能点清单

- **工具名称**: Luceda IPKISS (Luceda Photonics Design Platform)
- **厂商**: Luceda Photonics
- **官网 URL**: https://www.luceda.com/luceda-ipkiss/
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **学术诚信声明**: 本文档所有功能点均来源于 Luceda Photonics 官网及 Luceda Academy 公开文档，未公开项已明确标注。

---

## 一、器件设计 (Component Design)

- **标准开发语言 Python**: IPKISS 基于 Python 平台，为 PIC 设计、模型库与 IP 管理提供统一标准语言。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **参数化器件版图与仿真 (Parametric Components in Layout & Simulation)**: 支持参数化器件的版图与仿真，从单一平台进行设计开发以减少人为设计失误。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **虚拟工艺建模 (Virtual Fabrication)**: 支持虚拟工艺建模（虚拟制造），用于在设计阶段预验证可制造性。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **内置 EME 物理仿真引擎 (Built-in Physical EME Simulation)**: 内置本征模展开 (Eigenmode Expansion) 物理仿真引擎，用于器件级仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **第三方工具联合仿真 (3rd-party Tool Co-Simulation)**: 支持与 Ansys Lumerical、CST Studio Suite、Tidy3D 等第三方工具联合仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)

---

## 二、线路设计 (Circuit Design)

- **基于代码的线路设计 (Code-driven Circuit Design)**: 支持基于代码驱动的光子集成电路设计。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **智能光/电布线函数 (Smart Optical and Electrical Routing)**: 提供智能的光学与电学布线函数。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **参数化电路与紧密版图-仿真链接 (Parametric Circuits with Tight Layout-Simulation Link)**: 设计版图与线路模型紧密结合，支持参数化电路。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **代码辅助的原理图驱动设计 (Schematic Capture with Code Assistance)**: 支持代码辅助的原理图驱动设计。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **CAPHE 仿真引擎 (CAPHE Simulation Engine)**: 内置线路级仿真引擎 CAPHE，用于电路仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)

---

## 三、设计验证 (Design Validation)

- **IPKISS Canvas 连接性与功能验证**: 使用 IPKISS Canvas 进行连接性和功能验证，提供直观的原理图捕获界面。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **网表提取 (Netlist Extraction - Optical and Electrical)**: 支持光学和电学网表提取。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **CAPHE 布局后仿真 (Post-layout Simulations with CAPHE)**: 使用 CAPHE 进行布局后仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)

---

## 四、流片准备 (Tape-out Preparation)

- **锐角修补 (Acute Angle Patching)**: 支持锐角修补，确保制造合规性。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **捕捉错误 (Snapping Errors)**: 支持捕捉错误检测与修正。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **完整 GDS 导出 (Full GDS Export)**: 支持完整的 GDS 文件导出。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **设计规则检查 (DRC via Check Mate / Native DRC Engine)**: 通过集成 Spark Photonics 的 Check Mate DRC 工具进行设计规则检查；支持从代码运行 DRC (luceda.drc.run_drc()) 及在 IPKISS Layout visualizer 中通过 DRC 按钮运行。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/) ；[https://academy.lucedaphotonics.com/history/changelog](https://academy.lucedaphotonics.com/history/changelog)

---

## 五、LVS 验证与多 Foundry PDK

- **LVS 验证 (Layout vs Schematic)**: 2025.09 版本起增强 LVS 验证，用于流片就绪验证。来源: [https://stablewarez.com/shop/luceda-photonics-design-platform-2025-09-ipkiss/](https://stablewarez.com/shop/luceda-photonics-design-platform-2025-09-ipkiss/)
- **多 Foundry PDK 支持**: 支持多种 foundry PDK，包括 SiFab、Luceda PDK for SiEPIC、SiEPIC Shuksan、CORNERSTONE SiN、CORNERSTONE SOI 等，可构建和管理自有设计库。来源: [https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin](https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin) ；[https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **PDK 组件库定义**: PDK 提供预定义单元库（building blocks），支持波导布线、自定义器件定义、foundry 设计规则遵循。来源: [https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin](https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin)

---

## 六、合作伙伴集成 (Partner Integrations)

- **Link for Ansys Lumerical**: 与 Ansys Lumerical 集成，用于 FDTD 与 EME 仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **Link for Tidy3D**: 与 Tidy3D 集成，用于 FDTD 仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **Link for 3DS Simulia (Dassault Systems)**: 与 Dassault Systems Simulia (CST Studio Suite) 集成，用于 FDTD 仿真。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **Link for Siemens EDA**: 在 L-Edit GUI 中使用 IPKISS 的能力，支持从 Siemens L-Edit 编辑电路。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/) ；[https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin](https://academy.lucedaphotonics.com/pdks/cornerstone_sin/cornerstone_sin)
- **Link for Check Mate DRC**: 一行代码运行 DRC。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)

---

## 七、配套产品与平台

- **Luceda AWG Designer**: 阵列波导光栅设计器，一键式流程生成可制造的 AWG。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **Luceda IP Manager**: 光子 IP 自动化测试工具。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)
- **Luceda Circuit Analyzer**: PIC 设计深度分析工具，支持 Monte Carlo 等变异性评估。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/) ；[https://stablewarez.com/shop/luceda-photonics-design-platform-2025-09-ipkiss/](https://stablewarez.com/shop/luceda-photonics-design-platform-2025-09-ipkiss/)
- **Luceda Academy 培训与支持**: 提供免费培训、教程与应用实例，培训与支持服务包含在软件许可证中。来源: [https://www.luceda.com/luceda-ipkiss/](https://www.luceda.com/luceda-ipkiss/)

---

## 功能点统计

| 模块 | 功能点数量 |
|------|-----------|
| 器件设计 (Component Design) | 5 |
| 线路设计 (Circuit Design) | 5 |
| 设计验证 (Design Validation) | 3 |
| 流片准备 (Tape-out Preparation) | 4 |
| LVS 验证与多 Foundry PDK | 3 |
| 合作伙伴集成 (Partner Integrations) | 5 |
| 配套产品与平台 | 4 |
| **总计** | **29** |
