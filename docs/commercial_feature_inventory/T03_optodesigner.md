# T03 Synopsys OptoDesigner 商业光子 EDA 工具功能点清单

- **工具名称**: Synopsys OptoDesigner (Photonic Chip and Mask Layout)
- **厂商**: Synopsys
- **官网 URL**: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **学术诚信声明**: 本文档所有功能点均来源于 Synopsys 官网公开文档，未公开项已明确标注。

---

## 一、核心版图设计功能 (Core Layout Features)

- **Design Intent (设计意图层)**: 用户在单一层（design intent layer）上设计，软件自动生成实际生产所需的全部掩膜层，简化掩膜数据生成。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **技术无关元素定义 (Technology-agnostic Method)**: 支持技术无关的元素定义方法，可在不同技术之间移植相同设计。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **全角度连接性 (All Angle Connectivity)**: 全角度连接确保组件在需要时保持连接，元件间连接在变更时自动维护。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **曲线元素设计与定制 (Easy to Design and Customize Curved Elements)**: 易于设计与定制曲线元素。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **丰富元件库 (Extensive Libraries)**: 提供大量原始元件与组件的丰富库。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **强大脚本语言 (Powerful Scripting Language)**: 提供强大脚本语言以自动化所有设计任务。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **无限层级层次结构 (Unlimited Levels of Hierarchy)**: 支持无限层级层次结构，简化设计复用。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **PDK 支持与自定义 (Define Your Own PDK or Use Foundry PDKs)**: 可定义自有 PDK 或使用众多可用的 foundry PDK。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **附加仿真模块 (Add-on Simulation Modules)**: 提供模式计算与传播计算的强大附加仿真模块。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **GDSII/CIF 导入导出 (Import and Export to GDSII and CIF)**: 支持 GDSII 和 CIF 等格式的导入导出。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **自定义 GDS 库 (Define Your Own GDS Libraries)**: 通过广泛缓存能力定义自有 GDS 库。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **第三方工具接口 (Many Interfaces to Third-party Tools)**: 提供众多第三方工具接口。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **离散化引擎 (Discretization Engine)**: 强大的离散化引擎生成最终掩膜数据，支持多种导出格式。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)

---

## 二、Design Rule Checking (DRC) 模块

- **18 类 DRC 规则 (18 Types of Rules)**: 提供 18 类简单可配置的设计规则检查。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **单层与多层规则 (Single-layer and Multi-layer Rules)**: 规则可作用于单层或层组合，例如 A 与 B 之间的最小距离。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **交互式 DRC 错误管理对话框 (Interactive Dialog to Manage DRC Errors)**: 提供交互式对话框管理不同 DRC 错误。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **预定义示例 (Predefined Examples)**: 为广泛案例提供预定义示例。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **规则分组能力 (Grouping Capability)**: 可定义和执行 DRC 规则组，无需运行全部检查，可针对特定组加速工作。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **全角度曲线感知 DRC (All-angle Curvilinear DRC)**: DRC 检查在全角度下工作，不限于传统电子 Manhattan 类型设计，可处理曲线形状而无误报。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)
- **PDK 内嵌检查 (Checks Implemented in PDK)**: Foundry 可在 PDK 中实现检查；OptoDesigner 可对设计执行自动检查（如波导宽度与半径检查）。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html)

---

## 三、Autorouting 模块 (自动布线)

- **金属布线 (Metal Routing)**: 支持单层或多层金属布线，适用于 DC 与低速 RF 布线。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **90 度/45 度金属布线 (90-degree or 45-degree Metal Routing)**: 金属布线支持 90 度或 45 度路由。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **VIA 成本可调 (Adjustable Costs for VIAs)**: VIA 的成本可调。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **光波导布线 (Optical Waveguide Routing)**: 支持单层光子布线，适用于硅光子学等小弯曲半径技术。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **90 度/45 度光波导布线 (90-degree or 45-degree Optical Routing)**: 光波导布线支持 90 度或 45 度路由。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **PCell 选择 (PCell Selection for Bends/Straights/Crossings)**: 可为弯曲、直段和交叉选择 PCell，每个可以是任意（用户或 PDK 定义）PCell。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **弯曲与交叉相对成本 (Relative Costs for Bends and Crossings)**: 用户或 PDK 可指定弯曲和交叉的相对成本。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **迭代迷宫布线 (Iterative Maze Routing)**: 迭代迷宫布线旨在最小化全局成本。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **掩膜层避障 (Prevent Routing from Overlapping Specific Mask Layers)**: 防止布线与特定掩膜层重叠。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)
- **规则与成本驱动 (Rules and Cost-based)**: 自动布线模块基于规则与成本，可调整不同布线层与类型的规则和成本。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/autorouting.html)

---

## 四、Advanced Connectors 模块 (高级连接器)

- **Manhattan 风格连接器 (Manhattan-style Connectors)**: 提供 Manhattan 风格连接器。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **航点辅助 (Way Point Assisted)**: 支持航点辅助，包括相对坐标。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **预定义弯曲与直段 (Predefined Bends and Straights)**: 提供预定义弯曲与直段。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **用户定义与 PDK 构件支持 (Supports User-defined and PDK Building Blocks)**: 支持用户定义与 PDK 构件。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **路径长度定义连接器 (Path Length Defined Connectors)**: 支持路径长度定义的连接器，可约束光程长度与相位关系。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **自动交叉插入器 (Automatic Crossing Inserter)**: 自动波导或金属波导交叉放置。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **弹性连接器 (Elastic Connectors)**: 弹性连接器可连接掩膜版图中两个或多个点，考虑光程长度、相位关系和弯曲曲率等约束。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)
- **总线布线 / 相位匹配布线 / RF GSG 布线 (Bus Routing, Phase-matched Routing, RF GSG Routing)**: 支持总线布线、相位匹配布线、光程长度计算、自动波导/金属波导交叉放置及 RF GSG 布线。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html)

---

## 五、任意曲线与宽度剖面 (Arbitrary Curves and Width Profiles)

- **CurveUpDown 任意曲线**: 通过 XYup 与 XYlow 两个参数化函数（参数 t 从 0 到 1）描述任意上下曲线，输入/输出端口位于两端中点。来源: [https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html](https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html)
- **CenterPath 中心路径曲线**: 适用于具有明确中心路径的曲线，第一参数为中心路径曲线，第二参数为宽度定义（固定/线性/用户定义函数）。来源: [https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html](https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html)
- **高精度离散化 (Accurate Discretization to Polygons)**: 离散化算法确保所有掩膜多边形顶点位于距解析曲线给定距离内（通常 1 nm），曲线困难处顶点密度更高。来源: [https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html](https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html)
- **Functor 加速 (Functor C++ Acceleration)**: 使用 functor（如 { functor = sin(#) }）将脚本函数转换为 C++ 对象，求值速度比普通脚本函数快数个数量级。来源: [https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html](https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html)

---

## 六、Lattice Filter Design 模块与其他

- **Lattice Filter Design Module**: 晶格滤波器设计附加模块。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **OptoCompiler 集成**: OptoDesigner 作为 OptoCompiler 的版图设计驾驶舱，与 OptSim Circuit 协同；2026 R1 起 Lumerical INTERCONNECT/MODE/FDTD 与 OptoCompiler 直接集成。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html) ；[https://www.ansys.com/products/optics/interconnect](https://www.ansys.com/products/optics/interconnect)
- **OptSim Circuit 集成**: 当 PIC 原理图在 OptSim Circuit 中捕获并仿真后，可在 OptoDesigner 中调整设计。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)
- **成熟流片验证 (Mature Solution - 500+ Tape-outs)**: 过去三年中超过 500 次流片的可靠成熟解决方案。来源: [https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html](https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html)

---

## 功能点统计

| 模块 | 功能点数量 |
|------|-----------|
| 核心版图设计功能 (Core Layout Features) | 13 |
| DRC 模块 | 7 |
| Autorouting 模块 | 10 |
| Advanced Connectors 模块 | 8 |
| 任意曲线与宽度剖面 | 4 |
| Lattice Filter Design 模块与其他 | 4 |
| **总计** | **46** |
