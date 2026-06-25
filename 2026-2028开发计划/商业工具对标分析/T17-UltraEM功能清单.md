# T17 杭州法动科技 UltraEM 功能点清单

> **学术诚信声明**：本文档所有功能点均来自公开来源（法动科技官网 faradynamics.com、官方宣传PDF、官方新闻稿、集创赛赛题、合作高校通报、第三方半导体媒体如EETrend/ElecFans/21IC/Sekorm等转载）。每个功能点均标注来源 URL。未公开或法动科技未涉及的能力（如光子/光电子EDA）明确标注"未公开/不涉及"。本文档不含任何臆造内容。

---

## 文档元信息

| 项目 | 内容 |
|---|---|
| 厂商 | 杭州法动科技有限公司（Faraday Dynamics, Ltd.） |
| 母公司 | 杭州泛利科技有限公司（全资控股） |
| 总部 | 杭州经济技术开发区（钱塘区）下沙白杨街道6号大街452号 |
| 官网 | https://faradynamics.com/ |
| 调研日期 | 2026-06-25 |
| 文档版本 | v1.0 |
| 调研对象 | UltraEM® 全家族 + 关联产品 SuperEM/FDSPICE/EMOptimizer/GrityDesigner |
| 类型 | 商业（国产，国家高新技术企业） |

---

## 产品概述

杭州法动科技有限公司（成立于 2017 年）是一家专业提供射频微波电子设计自动化（EDA）软件的国产厂商，拥有自主知识产权的"大容量、快速三维全波电磁仿真引擎"和"基于人工智能技术的高效系统级仿真引擎"。其旗舰产品 **UltraEM®** 是芯片级三维全波电磁仿真专家，用于分析射频/微波IC及高速数字IC版图的电磁场效应，与业界主流模拟芯片设计环境（Cadence Virtuoso、华大九天 Aether 等）无缝集成。围绕 UltraEM®，公司形成了 UltraEM Family、SuperEM Family、FDSPICE®、EMOptimizer®、GrityDesigner 五大产品线，覆盖芯片-封装-PCB 全流程电磁仿真与系统级联合仿真，并在国际上首创集成射频芯片"快速仿真"与"快速优化"设计范式（基于 AI 电磁大脑专利）。

来源：
- https://faradynamics.com/aboutus.html?introduce
- https://faradynamics.com/software.html?optimizer
- https://faradynamics.com/chip.html?chip_1

---

## 功能点清单

### 1. UltraEM 三维全波电磁仿真引擎（芯片级）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| UE-1.1 | 三维全波电磁仿真内核 | 自主研发的全球领先高效全波仿真内核，能同时保证仿真精度与效率，用于分析射频/微波IC及高速数字IC版图的电磁场效应 | https://faradynamics.com/chip.html?chip_1 |
| UE-1.2 | 版图编辑操作 | 支持版图编辑操作，提供美观易用的用户界面与强大的版图编辑能力 | https://faradynamics.com/software.html?optimizer |
| UE-1.3 | 内置 Example 库 | 软件内置仿真实例，便于用户上手学习 | https://faradynamics.com/aboutus.html?news |
| UE-1.4 | 参数化器件模型创建 | UltraEM® 可创建参数化 EM 模型（FCell），供 FDSPICE® / EMOptimizer® 调用进行电路仿真与优化 | https://faradynamics.com/software.html?optimizer |
| UE-1.5 | 与 Cadence Virtuoso 无缝集成 | UltraEM 菜单嵌入 Virtuoso Toolbar，支持从 Virtuoso 直接调用 UltraEM 进行版图仿真；支持 Back-annotate 将 snp 文件反标到原理图 Nport 器件 | https://www.faradynamics.com/downloads/Tutorial_UltraEM.pdf |
| UE-1.6 | 与华大九天 Aether 集成 | UltraEM® 201909 新版支持与华大九天的版图设计工具 Aether 集成 | https://faradynamics.com/aboutus.html?contact |
| UE-1.7 | Via Array 和 Dummy 结构仿真 | UltraEM® 201909 版新增准确快速仿真 via array 和 dummy 结构的能力 | https://faradynamics.com/aboutus.html?contact |
| UE-1.8 | NTN Layer 与 PGS 分析 | 支持 NTN（Non-Through-Substrate Via）层与 PGS（Patterned Ground Shield，接地屏蔽层）对器件 Q 值影响的仿真研究 | https://faradynamics.com/aboutus.html?news |
| UE-1.9 | 片上电感电磁隔离分析 | 提供 UltraEM® 的片上电感电磁隔离分析仿真算例 | https://m.elecfans.com/article/2204214.html |
| UE-1.10 | Label Pin 与 Rect Pin 一致性 | UltraEM® 支持电感和谐振频率计算中 Label Pin 与 Rect Pin 一致性处理 | https://m.elecfans.com/article/2158660.html |
| UE-1.11 | Corner Sweep 仿真 | UltraEM® 支持 Corner Sweep 仿真实例，覆盖工艺角分析 | https://m.elecfans.com/article/2114342.html |
| UE-1.12 | 工艺文件导入与叠层配置 | 支持导入多个工艺文件进行合适的叠层配置；可手动设置工艺 | https://www.sekorm.com/news/49294502.html |
| UE-1.13 | 工艺参数变量扫描 | 可将材料厚度、金属线宽、介电层物理参数设置为预定义变量，实现参数扫描；支持 Temperature/Corner 设置及扫描；支持 RPSQ 参数、Conductivity 或 Via 电阻设定；支持金属 Width 与 Spacing 变量 | https://www.sekorm.com/news/49294502.html |
| UE-1.14 | Pin/Pin 端口激励设置 | 支持添加 Pin 作为激励端口（Add Pin as Excitation Port），并提供 Pin 信息对话框管理 | https://www.faradynamics.com/downloads/Tutorial_UltraEM.pdf |
| UE-1.15 | Back-annotation（反标） | Back-annotate 对话框显示上一次版图仿真的 snp 文件与目标原理图，将 snp 文件导入目标 Nport 器件 | https://www.faradynamics.com/downloads/Tutorial_UltraEM.pdf |
| UE-1.16 | 仿真结果与实测对比验证 | 5G 带通滤波器（砷化镓工艺，3.3-4.2GHz）案例显示仿真结果与实测数据高度吻合，频偏小于 0.1GHz | https://faradynamics.com/downloads/files/芯片电磁仿真解决方案_宣传页.pdf |

### 2. UltraEM XC（与主流IC版图编辑器集成版）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| XU-2.1 | 与主流IC版图编辑器无缝集成 | UltraEM XC™ 是易于使用的芯片级电磁设计工具，与主流 IC 布局编辑器无缝集成；支持 Virtuoso Layout 的所有类型 | https://faradynamics.com/aboutus.html?news |
| XU-2.2 | MPI 分布式运算 | 2022 版新增 Mpi Command 输入框，对于较大算例可通过分布式运算将仿真频段分成几个不同部分同时进行仿真，进一步提高仿真效率 | https://faradynamics.com/aboutus.html?news |
| XU-2.3 | 端口自动读取 | UltraEM XC® 支持端口自动读取，可自动识别 Virtuoso 中的端口 | https://faradynamics.com/aboutus.html?news |
| XU-2.4 | 内置 Example | 软件内置 Example，便于快速上手 | https://faradynamics.com/aboutus.html?news |

### 3. UltraEM XA（国产EDA集成版）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| XA-3.1 | 与国产EDA版图工具集成 | UltraEM XA™ 为针对国产EDA版图工具（如华大九天Aether等）的集成版本，与 UltraEM XC™ 共享底层三维全波仿真引擎 | https://faradynamics.com/aboutus.html?contact |
| XA-3.2 | 国产EDA生态适配 | 配合国内自主可控EDA链，提供与国产模拟IC设计环境的集成能力（具体适配清单未公开） | 未公开（基于UltraEM 201909与Aether集成推断） |

### 4. SuperEM 三维全波电磁仿真引擎（封装/PCB/天线级）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| SE-4.1 | 高速PCB/微带天线/封装电磁仿真 | SuperEM® 是高速印刷电路板电路、微带天线、封装等的电磁仿真专家，领先的三维全波电磁仿真器，主要用于射频和高速电路等的设计领域 | https://mp.mwrf.net/handbook/lists/49.shtml |
| SE-4.2 | S参数/近场/辐射方向图仿真 | SuperEM® 可精确仿真 S 参数、近场、以及辐射方向图等数据 | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| SE-4.3 | FCell 模型构建天线单元 | SuperEM® 使用 FCell 模型构建天线单元，只需一次设计即可用于各种不同板材和尺寸的模型 | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| SE-4.4 | 贴片天线阵列完整设计流程 | SuperEM® 可适用于任何贴片天线阵列的完整设计流程，包括从仿真到调试的各个环节 | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| SE-4.5 | PCB 信号线电磁特性仿真 | SuperEM® 可对封装及电路板中的信号线仿真电磁特性、提取参数 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SE-4.6 | IR Drop 仿真 | SuperEM® 可对 PCB 中的电源和地网络仿真 IR Drop，与业界领先的 PCB 设计环境无缝集成，快速读取设计数据并设置仿真 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SE-4.7 | 电压/电流/功率损耗密度分布图 | SuperEM® IR Drop 案例可输出电压分布图、电流密度分布图、功率损耗密度分布图 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SE-4.8 | SuperEM XC 集成版 | SuperEM XC™ 为与主流封装/PCB设计环境集成的版本，与 UltraEM XC™ 同属 XC 系列 | https://faradynamics.com/software.html?optimizer |

### 5. 芯片-封装-PCB 联合仿真

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| CP-5.1 | 芯片-封装-PCB 一体化联合仿真 | 创新的联合电磁仿真算法，实现芯片-封装-PCB 一体化联合仿真 | https://www.sekorm.com/news/49294502.html |
| CP-5.2 | 多工艺叠层配置 | 支持工艺叠层功能配置，可以导入多个工艺文件进行合适的叠层配置 | https://www.sekorm.com/news/49294502.html |
| CP-5.3 | 三维 Wirebonding / TSV / BGA 模型 | 支持三维 wirebonding、TSV、BGA 模型 | https://www.sekorm.com/news/49294502.html |
| CP-5.4 | 层级式设计（SiP/AiP） | 支持层级式设计，高效赋能 SiP（System-in-Package）、AiP（Antenna-in-Package）等多种封装形式 | https://www.sekorm.com/news/49294502.html |
| CP-5.5 | 自适应精度联合仿真 | UltraEM® 支持与 SuperEM® 一起实现芯片-封装-PCB 自适应精度联合仿真 | https://faradynamics.com/software.html?optimizer |
| CP-5.6 | 芯片-封装联合仿真优化求解器 | 三维建模简单易用，并配有专门针对联合仿真的优化求解器，可大幅减少迭代次数，提高设计成功率，使芯片工程师在设计流程中随时评估封装性能 | https://faradynamics.com/downloads/files/芯片-封装联合仿真解决方案_宣传页.pdf |
| CP-5.7 | Bonding Wire 互连仿真 | 支持 QFN 等主流封装中芯片与封装部分采用 Bonding Wire 相连的联合仿真；可对比芯片不带封装和带封装两种应用场景的回波损耗与插入损耗 | https://faradynamics.com/downloads/files/芯片-封装联合仿真解决方案_宣传页.pdf |

### 6. AI 建模与高效优化（AI 电磁大脑）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AI-6.1 | AI 电磁大脑（核心专利） | "一种基于人工智能的电磁仿真方法及其电磁大脑"，专利号 ZL201711439836.1，授权公告号 CN108182316B；将电路元器件对应的几何、物理、激励三类数据放入全波电磁计算求解器，得到 S 参数信息，组成训练数据集导入卷积神经网络进行离线训练，得到基于 AI 的单元模型；与现有全波电磁仿真软件相比，计算效率提高千倍以上 | https://newsletter.eetrend.com/content/2025/100593022.html |
| AI-6.2 | 模拟电路快速仿真优化方法（专利） | "一种模拟电路的快速仿真优化方法及其系统"，专利号 ZL202210439728.9，授权公告号 CN114611449B；美国专利 US 12,197,839（2025.01.14授权）"Quick simulation and optimization method and system for analog circuits" | https://newsletter.eetrend.com/content/2025/100593022.html |
| AI-6.3 | 高质量训练数据生成 | 通过全球领先的电磁计算引擎 UltraEM®，实现高精度全波仿真与参数建模，为 AI 算法提供高质量训练数据 | https://newsletter.eetrend.com/content/2025/100593022.html |
| AI-6.4 | 标准化射频库单元（FCell） | 构建一套标准化的射频库单元，并借助 AI 技术完成高维参数空间的建模训练，使设计过程中的核心器件可以"模块化"和"可复用" | https://newsletter.eetrend.com/content/2025/100593022.html |
| AI-6.5 | 快速仿真与快速优化设计范式 | 设计人员可直接调用训练好的标准化单元，跳过传统电磁仿真中每次迭代都需重新建模与仿真的耗时过程，大幅加快仿真与优化流程，将现有射频 IC 设计效率提升至千倍以上 | https://newsletter.eetrend.com/content/2025/100593022.html |
| AI-6.6 | 卷积神经网络训练 | 将几何/物理/激励作为输入，S 参数作为输出，使用训练好的卷积神经网络进行电磁性能分析，得到对应器件的 S 参数结果；一旦完成 CNN 训练，无需再依靠全波电磁场求解器即可得到仿真结果 | https://xueqiu.com/9983210953/297855535 |
| AI-6.7 | 全局寻优避免局部极小 | FDSPICE® 的优化算法具有全局寻优避免掉入局部极小值的优点；支持多目标优化 | https://xueqiu.com/9983210953/297855535 |
| AI-6.8 | 优化迭代误差可视化 | 可显示不同迭代次数下的优化结果与目标值之间的误差，同时支持用户选取优化结果进行实现 | https://xueqiu.com/9983210953/297855535 |
| AI-6.9 | S/Y/Z 参数及后处理参数查看 | FDSPICE® 支持 S/Y/Z 参数及后处理参数查看，为用户提供全面的电路设计信息 | https://xueqiu.com/9983210953/297855535 |
| AI-6.10 | Python 库单元文件支持 | 用户使用 Python 语言编写库单元文件，导入 UltraEM® 的库中调用，用于 FCell 训练 | https://www.sekorm.com/news/share?newId=528506266 |
| AI-6.11 | AI 训练参数范围设置 | 进行 AI 训练参数范围设置（参数范围用","相隔）；点击 Run 完成训练后，点击 Download 下载 FCell 供 FDSPICE® 和其他法动软件工具使用 | https://www.sekorm.com/news/share?newId=528506266 |
| AI-6.12 | Generic Lib 内置 | 法动科技 EDA 工具中自带 generic lib，可供用户直接使用 | https://www.eetrend.com/content/2025/100589337.html |

### 7. EMOptimizer® 快速仿真与优化软件

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| EO-7.1 | 业界首款射频电路快速设计优化软件 | EMOptimizer® 是业界首款射频电路快速设计优化软件，将 FCell 用于电路设计，在保证较高精度的同时大大提升电路仿真和优化的速度 | https://faradynamics.com/downloads/files/模拟射频无源芯片解决方案_宣传页.pdf |
| EO-7.2 | 可复用机制 | 借鉴数字芯片的"单元库"概念，发展专门针对无源器件的标准化、可复用单元库/IP，设计时将"积木单元"搭建起来即可快速搭建新的设计电路 | https://www.sekorm.com/news/share?newId=53608772 |
| EO-7.3 | 参数化建模方法 | "参数化"建模方法是突破非常耗时的传统电磁仿真迭代瓶颈的关键利器，可以显著提升设计探索与优化的效率 | https://newsletter.eetrend.com/content/2025/100593022.html |
| EO-7.4 | 快速设计优化闭环 | 通过将可复用机制、参数化模型与高性能优化算法深度融合，EMOptimizer® 大幅提升设计闭环效率，显著降低流片风险和开发成本 | https://newsletter.eetrend.com/content/2025/100593022.html |
| EO-7.5 | 版图输出至 UltraEM 验证 | 将 EMOptimizer® 优化得到的版图输出到电磁仿真软件 UltraEM®，经电磁仿真验证结果达到设计规格要求 | https://faradynamics.com/downloads/files/模拟射频无源芯片解决方案_宣传页.pdf |
| EO-7.6 | 滤波器优化案例 | 优化前后对比：通带由 2.8-3.2GHz 增加到 2.6-3.2GHz，插入损耗由 1.8dB 减小到 1.1dB，回波损耗由 8.3dB 增加到 17.3dB | https://faradynamics.com/downloads/files/模拟射频无源芯片解决方案_宣传页.pdf |

### 8. FDSPICE® 系统级电路仿真设计平台（原 EMCompiler）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| FD-8.1 | 系统级电路仿真 | FDSPICE® 主要用于大规模模拟/射频、微波/毫米波、高速数字电路的系统级电路仿真以及参数优化 | https://xueqiu.com/9983210953/297855535 |
| FD-8.2 | 5G/5.5G 模拟射频电路系统仿真 | 面向 5G 和 5.5G 模拟/射频电路系统仿真与优化需求，提供更高精度、更强算力和更灵活的功能 | https://xueqiu.com/9983210953/297855535 |
| FD-8.3 | 可复用、可扩展及客户端 IP 支持 | FDSPICE® 四大创新功能点之一：可复用、可扩展及客户端 IP 强大支持 | https://xueqiu.com/9983210953/297855535 |
| FD-8.4 | 创新 AI 模型库快速仿真 | FDSPICE® 四大创新功能点之二：创新的 AI 模型库，快速得到仿真结果 | https://xueqiu.com/9983210953/297855535 |
| FD-8.5 | 优化结果与目标值误差可视化 | FDSPICE® 四大创新功能点之三：可显示不同迭代次数下的优化结果与目标值之间的误差，同时支持用户选取优化结果进行实现 | https://xueqiu.com/9983210953/297855535 |
| FD-8.6 | 原理图与版图联合仿真 | FDSPICE® 四大创新功能点之四：原理图与版图的联合仿真；FDSPICE® 通过调用 UltraEM/SuperEM 可进行原理图与版图的联合仿真 | https://xueqiu.com/9983210953/297855535 |
| FD-8.7 | 多目标参数化单元优化 | 优化功能可将 S/Y/Z 参数或任何使用"后处理公式"定义的物理量作为优化目标，对整个设计中所有的参数化单元进行优化，并且支持多目标优化 | https://xueqiu.com/9983210953/297855535 |
| FD-8.8 | 电磁与电路协同仿真 | UltraEM® 可以和 FDSPICE® 中的原理图仿真结合，实现电磁和电路的协同仿真，为广大的设计人员提供高精度电磁分析服务 | https://faradynamics.com/software.html?optimizer |
| FD-8.9 | FCell 导入与参数设置 | 用户在 FDSPICE® 导入 AI 训练得到的 FCell，放置 FCell 并连接电路图，双击导入的 FCell 设置参数 | https://www.sekorm.com/news/share?newId=528506266 |
| FD-8.10 | 优化目标及参数范围设置 | 使用 Optimization 功能优化电路，可设置电感内径等参数范围，设置优化目标（如插损在 1-3.5GHz 时小于 1dB） | https://www.sekorm.com/news/share?newId=528506266 |
| FD-8.11 | 优化前后结果对比 | 应用参数后再次仿真，可对比优化前后结果，验证是否达到期望指标 | https://www.sekorm.com/news/share?newId=528506266 |
| FD-8.12 | 丰富模型库文件 | FDSPICE® 提供丰富的模型和库文件，涵盖各种模拟/射频元件和电路结构，所有模型和库文件都经过严格验证 | https://www.sekorm.com/news/share?newId=528506266 |

### 9. GrityDesigner 先进封装 SI/PI 一站式 EDA 工具（2025年新推）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| GD-9.1 | 高性能全波电磁仿真引擎 | 采用混合格林函数与自适应算法，显著降低高密度介质中电磁场计算的复杂度，支持从低频到高频的精确仿真 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.2 | 高效区域分解方法 | 引入高效区域分解方法，支持三维异构封装（如 2.5D/3D IC）的快速仿真，通过并行计算技术实现大规模问题的求解效率 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.3 | 多尺度建模 | 结合多尺度建模技术，实现对 TSV、微凸点等关键互连结构的高精度电磁特性分析 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.4 | AI 驱动建模与优化 | 构建无源电路与几何参数之间的非线性映射模型，利用深度学习算法实现快速参数提取与优化，显著提升效率 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.5 | 有源器件实时建模 | 开发有源器件实时建模框架，结合机器学习方法，在保证精度的同时实现快速仿真，支持动态功耗分析与信号完整性评估 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.6 | AI 辅助设计空间探索 | 引入 AI 辅助设计空间探索，通过强化学习算法优化互连拓扑结构与参数配置 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.7 | 场-路协同仿真 | 建立统一的场-路协同仿真平台，实现从电磁场到电路行为的无缝衔接，以应对高密度互连系统设计的复杂性 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.8 | 三维异构集成设计支持 | 支持 2.5D/3D IC 等三维异构集成的复杂互连结构和信号传输路径仿真 | https://www.eetrend.com/content/2025/100596975.html |
| GD-9.9 | SI/PI 联合分析 | 一站式解决先进封装互连系统的信号完整性（SI）与电源完整性（PI）挑战，覆盖 IR Drop、地弹噪声、串扰等 | https://www.eetrend.com/content/2025/100596975.html |

### 10. 信号完整性（SI）与电源完整性（PI）解决方案

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| SI-10.1 | 信号完整性时域仿真 | 评估传输线上的波形和反射，采用 FDSPICE® 进行时域仿真 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.2 | 信号完整性频域仿真 | 评估信号的频率响应和带宽，采用 SuperEM® 仿真 S 参数曲线 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.3 | TDR（时域反射）分析 | 提供 TDR-电压结果，用于评估传输线阻抗失配与反射 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.4 | 眼图分析 | 提供码间串扰下的眼图结果分析 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.5 | 时间浴盆曲线 | 提供码间串扰下的时间浴盆曲线分析 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.6 | 电压浴盆曲线 | 提供码间串扰下的电压浴盆曲线分析 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.7 | 电源完整性（PI）分析 | 评估电源噪声和电源干扰对电路性能的影响，从而优化电源设计 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |
| SI-10.8 | 与业界PCB设计环境无缝集成 | 与业界领先的封装及电路板设计环境无缝集成，为广大的设计人员提供高精度分析服务 | https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf |

### 11. 贴片天线阵列设计解决方案

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| PA-11.1 | 贴片天线阵列完整流程 | SuperEM® 可适用于任何贴片天线阵列的完整设计流程，包括从仿真到调试的各个环节 | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| PA-11.2 | 参数化建模（FCell） | 使用 FCell 模型构建天线单元，只需一次设计即可用于各种不同板材和尺寸的模型 | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| PA-11.3 | 辐射方向图仿真 | 输出三维辐射方向图，计算扫描增益；4x4 阵列案例在 60 度内扫描增益为 14-15dBi | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| PA-11.4 | 端口耦合与回波损耗分析 | 仿真结果输出 S 参数，3.5GHz 频段回波损耗小于 10dB，端口之间耦合小于 15dB | https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf |
| PA-11.5 | 贴片天线匹配网络解决方案 | 提供贴片天线匹配网络设计解决方案（独立方案，与天线阵列方案互补） | https://faradynamics.com/index.html |

### 12. IPD 集成无源器件设计服务

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| IPD-12.1 | IPD 设计服务 | 充分发挥自主研发的 EDA 软件的优势，为用户提供集成无源器件 IPD 设计服务 | https://www.sekorm.com/news/49294502.html |
| IPD-12.2 | IPD 器件集成 | 把耦合器、移相器、变压器、滤波器、巴伦、衰减器、双工器等无源器件集成为小型化、高一致性的 IPD 器件 | https://www.sekorm.com/news/49294502.html |
| IPD-12.3 | LTCC 巴伦芯片全矩阵产品 | 法动科技设计研发中心运用"双国产化"理念，采用自主 EDA 工具全程应用 UltraEM 全波电磁仿真，开发 LTCC 巴伦芯片全矩阵系列产品；破解传统 Marchand 巴伦"尺寸大"和"带宽有限"难题；已获国家发明专利授权，理论模型与实验结果发表于高水平学术期刊 | https://m.elecfans.com/article/7146924.html |
| IPD-12.4 | 新型非对称宽边耦合结构 | UltraEM 软件引入新型非对称的宽边耦合结构，在极小芯片尺寸下大幅提升插损、幅度不平衡度及相位不平衡度等性能 | https://m.elecfans.com/article/7146924.html |

### 13. 模拟/射频有源芯片解决方案

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-13.1 | 模拟射频有源芯片解决方案 | 法动科技提供模拟射频有源芯片解决方案（与无源方案并列独立方案） | https://faradynamics.com/index.html |
| AC-13.2 | 功率放大器（PA）电磁仿真 | UltraEM-Virtuoso 设计流程教程以功率放大器设计为例，说明 UltraEM 如何在 Cadence Virtuoso 中仿真版图并将结果反标到 PA 原理图 | https://www.faradynamics.com/downloads/Tutorial_UltraEM.pdf |
| AC-13.3 | 有源电路与 AI 电磁大脑联合 | FDSPICE® 的 AI 电磁大脑可对模拟/射频高速电路进行精确仿真和分析，用于有源电路快速优化设计 | https://www.sekorm.com/news/share?newId=528506266 |

### 14. PDK 设计服务

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| PK-14.1 | PDK 设计服务 | 法动科技提供 PDK（Process Design Kit）设计服务 | https://faradynamics.com/index.html |
| PK-14.2 | EDA 软件设计外包服务 | 法动科技提供 EDA 软件外包服务（EDA Software Outsource Services） | https://faradynamics.com/index.html |

---

## 应用领域

| 编号 | 应用领域 | 描述 | 来源 URL |
|---|---|---|---|
| AP-1 | 移动通信（Mobile Phones） | 5G/5.5G 智能手机射频前端、Sub-6GHz 与毫米波频段 | https://faradynamics.com/aboutus.html?introduce |
| AP-2 | 物联网（Wireless Networks/IoT） | Wi-Fi、蓝牙、物联网无线通信模块 | https://faradynamics.com/aboutus.html?introduce |
| AP-3 | 雷达（Radars） | 毫米波雷达、汽车雷达 | https://faradynamics.com/aboutus.html?introduce |
| AP-4 | 卫星通信系统（Satellite Communication） | 卫星通信系统射频前端、NTN（Non-Terrestrial Network） | https://faradynamics.com/aboutus.html?introduce |
| AP-5 | 高速数字设计（High-speed Digital） | 高速数字IC、高速PCB信号完整性 | https://faradynamics.com/aboutus.html?introduce |
| AP-6 | 5G 基站 | 基站射频前端模组（华为、中兴5G基站方案参考） | https://m.elecfans.com/article/7146924.html |
| AP-7 | 航空航天与国防 | UltraEM® 2022 广泛适用航空航天和国防等领域 | https://faradynamics.com/aboutus.html?recruit |
| AP-8 | 汽车电子 | 车载复杂电磁环境应用（博世 EPS 系统位置反馈等参考案例） | https://m.elecfans.com/article/7146924.html |

---

## 产品版本

| 版本 | 发布时间 | 主要新增能力 | 来源 URL |
|---|---|---|---|
| UltraEM® V202007 | 2020年底前 | ① 芯片-封装-PCB 联合仿真（多工艺叠层、wirebonding/TSV/BGA、SiP/AiP）；② 先进工艺仿真（参数变量、Temperature/Corner、RPSQ/Conductivity/Via电阻、Width/Spacing）。同时 UltraEM/SuperEM/EMCompiler/UltraEM XC 升级至 V202007 | https://www.sekorm.com/news/49294502.html |
| UltraEM® 201909 | 2019.09 | 与华大九天版图设计工具 Aether 集成；准确快速仿真 via array 和 dummy 结构 | https://faradynamics.com/aboutus.html?contact |
| UltraEM® 2022 | 2022.05.12 | UltraEM XC® 增加 Mpi Command 输入框支持分布式运算；UltraEM XC® 支持端口自动读取；支持 Virtuoso Layout 所有类型；内置 Example | https://faradynamics.com/aboutus.html?news |
| UltraEM® 2022 系列 | 2022 年度 | 法动射频 EDA 2022 全新系列版本发布计划的一部分 | https://faradynamics.com/aboutus.html?news |
| EMOptimizer® 商用版 | 2023 年起 | 全球首款射频电路快速设计优化软件登陆中国市场；基于 AI 电磁大脑专利 | https://www.sekorm.com/news/share?newId=53608772 |
| GrityDesigner | 2025.12 | 一站式先进封装 SI/PI EDA 工具，破解高密度互连难题 | https://www.eetrend.com/content/2025/100596975.html |

---

## 客户案例与合作

| 编号 | 案例/合作 | 时间 | 描述 | 来源 URL |
|---|---|---|---|---|
| CC-1 | 工信部人才交流中心合作 | 2024.11.14 | 工信部人才交流中心等机构与法动科技签订合作协议；在全国集创赛上开辟"法动杯"模拟/射频新赛道 | https://faradynamics.com/aboutus.html?news |
| CC-2 | 重庆/四川 EDA 大赛 | 2023.12.27 | 法动射频 EDA 助力"重庆2023巴渝工匠杯集成电路EDA开发应用大赛"和"2023年四川省数字工匠大赛" | https://faradynamics.com/aboutus.html?news |
| CC-3 | 第九届集创赛"法动杯" | 2025.03-09 | 赛题《应用于Sub-6GHz 5G宽带射频芯片模组》，要求采用 EMOptimizer®/UltraEM®/FDSPICE® 设计 3.3-6GHz 射频芯片模组（宽带滤波器、匹配电路、Hybrid 90°耦合器）；总决赛圆满收官 | https://www.eetrend.com/content/2025/100589337.html |
| CC-4 | 杭州电子科技大学合作 | 2022.02.28 | 杭州电子科技大学联合法动科技，成功获批模拟EDA国家级专项基金重点项目 | https://faradynamics.com/aboutus.html?news |
| CC-5 | 江西工程学院校企培训 | 2026.03.28-29 | 江西工程学院与法动科技联合举办"基于UltraEM®、SuperEM®等EDA工具平台的模拟集成电路设计仿真实践"专题培训，50名本科生参加，完成7项实践任务 | https://dzxxgcxy.jxue.edu.cn/2026/0401/c310a45166/page.htm |
| CC-6 | A 轮融资 | 2022.06.29 | 法动科技完成 A 轮融资，由泰越资本领投，Huashan Capital（华山资本）等基金跟投，加速射频EDA赛道布局 | https://faradynamics.com/aboutus.html?news |
| CC-7 | A+ 轮融资 | 2023.01.31 | 法动科技再获 A+ 轮融资，兴橙资本投资；资金持续用于 UltraEM®/SuperEM® 快速迭代与 EMOptimizer® 优化完善 | https://www.sekorm.com/news/share?newId=53608772 |
| CC-8 | 国家高新技术企业认定 | 2020.12.01 | 法动科技被认定为"国家高新技术企业"；2018年获批"浙江省领军型创业团队" | https://www.sekorm.com/news/49294502.html |
| CC-9 | LTCC 巴伦芯片全矩阵量产 | 2025.10 | 法动科技设计研发中心全程应用 UltraEM 全波电磁仿真软件，开发 LTCC 巴伦芯片全矩阵系列产品；在"京北通宇"等电子商城全新上架 | https://m.elecfans.com/article/7146924.html |
| CC-10 | IME 2025 深圳射频微波及天线技术会议 | 2025.06 | 法动科技亮相 IME 2025 第四届深圳射频微波及天线技术会议 | https://m.elecfans.com/article/6773599.html |

---

## 学术诚信与创新能力声明

### 1. 数据来源声明

本清单所有功能点均来自以下公开来源（截至 2026-06-25）：
- 法动科技官网 https://faradynamics.com/ 及其下属页面（aboutus、software、chip、downloads等）
- 法动科技官方宣传PDF（芯片电磁仿真解决方案、芯片-封装联合仿真解决方案、贴片天线阵列设计解决方案、模拟射频无源芯片解决方案、信号及电源完整性解决方案）
- 法动科技官方 UltraEM-Virtuoso Design Flow 教程 PDF（Tutorial_UltraEM.pdf, Version 202002SP1）
- 第三方半导体媒体对法动科技产品发布与原创文章的转载（EETrend、ElecFans、21IC、Sekorm、Xueqiu、MP.RF 等）
- 合作高校通报（江西工程学院、杭州电子科技大学）
- 集创赛"法动杯"赛题官方解析
- 国家企业信用信息公示系统（工商信息、专利信息）

### 2. 专利来源（已核实）

| 专利号 | 名称 | 申请日 | 授权日 | 来源 |
|---|---|---|---|---|
| ZL201711439836.1 / CN108182316B | 一种基于人工智能的电磁仿真方法及其电磁大脑 | 2017.12.27 | 2021.12.07 | https://newsletter.eetrend.com/content/2025/100593022.html |
| ZL202210439728.9 / CN114611449B | 一种模拟电路的快速仿真优化方法及其系统 | 2022.04.25 | 2024.07.30 | https://newsletter.eetrend.com/content/2025/100593022.html |
| US 12,197,839 | Quick simulation and optimization method and system for analog circuits | 2024.09.03 | 2025.01.14 | https://newsletter.eetrend.com/content/2025/100593022.html |
| CN201810602897.3 | 基于深度学习的射频器件参数优化方法 | 2018.06.12 | 公开 | https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html |
| CN202411015080.8 | 基于电磁耦合深度学习模型的射频器件建模方法及装置 | 2024.07.26 | 已授权 | https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html |
| CN202510102078.2 | 一种适用于多尺度精细结构天线的混合电磁仿真方法 | 2025.01.22 | 已授权 | https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html |
| CN202610057000.8 | 以电磁场分布特性为核心导向的电磁场仿真自适应网格生成方法 | 2026.01 | 公开 | https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html |
| CN202610140435.9 | 基于神经网络的电磁场仿真网格自适应生成方法 | 2026.02.02 | 公开 | https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html |

### 3. 法动科技不涉及/未公开的能力（如实标注）

| 编号 | 能力 | 标注 | 说明 |
|---|---|---|---|
| NP-1 | 光子（光电子/光子集成回路 PIC）EDA | **不涉及** | 法动科技专注射频/微波/毫米波EDA，官网与公开资料均未提及光子/光电子EDA能力；其应用领域仅限电磁频谱的射频段 |
| NP-2 | 数字后端 EDA（布局布线、综合、签核） | **不涉及** | 法动科技不做数字后端，与 Cadence Innovus / Synopsys ICC2 等数字实现工具无竞争关系 |
| NP-3 | 模拟/射频 IC 全定制原理图与版图编辑器 | **未公开** | 法动科技与 Cadence Virtuoso / 华大九天 Aether 集成，自身不提供独立版图编辑器 |
| NP-4 | DRC/LVS 物理验证 | **未公开** | 公开资料未提及物理验证能力，依赖第三方版图工具完成验证 |
| NP-5 | 寄生参数提取（RC/RLCK Extraction） | **未公开** | 公开资料未明确提及独立 PEX 工具，但 UltraEM 可输出 S 参数模型供电路仿真使用 |
| NP-6 | 具体工艺节点 PDK 支持清单 | **未公开** | 仅公开 generic lib 自带，具体工艺 PDK（如 TSMC/SMIC/GaAs 厂商 PDK）适配清单未公开 |
| NP-7 | UltraEM XA 与 UltraEM XC 功能差异细节 | **未公开** | 官网仅列产品家族，XA 与 XC 的具体差异未详细公开 |
| NP-8 | GrityDesigner 商用版本号与定价 | **未公开** | GrityDesigner 于 2025 年 12 月发布，仍处于早期阶段 |
| NP-9 | EMOptimizer 定价 | **未公开** | 法动科技仅通过 service@faradynamics.com 提供商务咨询 |
| NP-10 | 第三方学术独立基准测试结果 | **未公开** | 公开资料中除法动科技自有的 5G 带通滤波器案例对比外，未见第三方独立基准测试报告 |

### 4. 创新能力说明（标注 *创新*）

- *创新* **AI 电磁大脑**：法动科技在全球范围内首创将数字集成电路"单元库"思想与 AI 建模技术深度融合，应用于射频集成无源芯片设计领域，构建"标准化射频库单元 + 卷积神经网络训练"的设计范式。底层逻辑：将电路元器件对应的几何/物理/激励三类数据放入全波电磁计算求解器得到 S 参数信息，组成训练数据集导入卷积神经网络进行离线训练，得到基于 AI 的单元模型（FCell）。案例支持：5G 带通滤波器、LC 滤波器优化、Sub-6GHz 5G 宽带射频芯片模组（集创赛赛题）。支持理论：卷积神经网络对高维参数空间的非线性映射能力 + 数字电路设计单元库的可复用思想。来源：专利 ZL201711439836.1 / CN108182316B；https://newsletter.eetrend.com/content/2025/100593022.html
- *创新* **可复用 + 参数化双核心理念**：法动科技自 2017 年起率先将"可复用"与"参数化"两大核心理念创造性引入射频集成无源芯片设计领域。底层逻辑：借鉴数字芯片的"单元库"概念，发展专门针对无源器件的标准化、可复用单元库/IP；"参数化"建模方法是突破非常耗时的传统电磁仿真迭代瓶颈的关键利器。支持理论：数字电路单元库设计方法学 + 参数化模型降阶方法。
- *创新* **芯片-封装-PCB 自适应精度联合仿真**：法动科技独创芯片-封装联合仿真流程，配有专门针对联合仿用的优化求解器，三维建模简单易用。底层逻辑：通过创新的联合电磁仿真算法将芯片级（UltraEM）与封装/PCB 级（SuperEM）仿真器协同，按不同精度需求自适应调度。支持理论：多尺度电磁仿真 + 区域分解法。

---

## 功能点统计

### 按模块分布

| 模块 | 功能点数 | 编号范围 |
|---|---|---|
| 1. UltraEM 三维全波电磁仿真引擎 | 16 | UE-1.1 ~ UE-1.16 |
| 2. UltraEM XC（集成版） | 4 | XU-2.1 ~ XU-2.4 |
| 3. UltraEM XA（国产EDA集成版） | 2 | XA-3.1 ~ XA-3.2 |
| 4. SuperEM 三维全波电磁仿真引擎 | 8 | SE-4.1 ~ SE-4.8 |
| 5. 芯片-封装-PCB 联合仿真 | 7 | CP-5.1 ~ CP-5.7 |
| 6. AI 建模与高效优化 | 12 | AI-6.1 ~ AI-6.12 |
| 7. EMOptimizer 快速仿真与优化 | 6 | EO-7.1 ~ EO-7.6 |
| 8. FDSPICE 系统级电路仿真 | 12 | FD-8.1 ~ FD-8.12 |
| 9. GrityDesigner 先进封装 SI/PI | 9 | GD-9.1 ~ GD-9.9 |
| 10. SI/PI 解决方案 | 8 | SI-10.1 ~ SI-10.8 |
| 11. 贴片天线阵列设计 | 5 | PA-11.1 ~ PA-11.5 |
| 12. IPD 集成无源器件设计服务 | 4 | IPD-12.1 ~ IPD-12.4 |
| 13. 模拟/射频有源芯片解决方案 | 3 | AC-13.1 ~ AC-13.3 |
| 14. PDK 设计服务 | 2 | PK-14.1 ~ PK-14.2 |
| **核心功能点小计** | **98** | |
| 应用领域 | 8 | AP-1 ~ AP-8 |
| 产品版本 | 6 | - |
| 客户案例与合作 | 10 | CC-1 ~ CC-10 |
| 不涉及/未公开能力 | 10 | NP-1 ~ NP-10 |
| **总计** | **132** | |

### 核心功能点分布（前14个模块，共98个）

- UltraEM 全家族（含 XC/XA）：22 个（占 22.4%）
- SuperEM 家族：8 个（占 8.2%）
- 联合仿真：7 个（占 7.1%）
- AI 建模与优化（含 EMOptimizer + FDSPICE AI 部分 + GrityDesigner AI）：27 个（占 27.6%）
- FDSPICE 系统级电路仿真：12 个（占 12.2%）
- GrityDesigner SI/PI：9 个（占 9.2%）
- SI/PI 解决方案：8 个（占 8.2%）
- 天线/IPD/有源/PDK：14 个（占 14.3%）

### 与商业对齐情况

| 维度 | 法动科技 UltraEM 全家族能力 | 国际对标 | 对齐情况 |
|---|---|---|---|
| 三维全波电磁仿真 | UltraEM/SuperEM（自研引擎） | Ansys HFSS / CST Studio Suite / Keysight EMPro | 部分对齐（仿真效率声称达或超越国际领先，但工艺节点认证、第三方基准测试未公开） |
| 芯片-封装-PCB 联合仿真 | UltraEM+SuperEM 自适应精度联合仿真 | ANSYS HFSS 3D Layout + RedHawk、Cadence Clarity 3D Solver | 部分对齐（自研联合算法、wirebonding/TSV/BGA 模型；具体精度对比未公开） |
| AI 建模与优化 | EMOptimizer + AI 电磁大脑 + FCell 单元库 | Cadence Cerebrus/JedAI、Synopsys DSO.ai | 创新路线不同：法动以"AI电磁大脑+可复用单元库"为特色，国际厂商以 RL/ML 优化为主 |
| 系统级电路仿真 | FDSPICE（基于 SPICE） | Synopsys PrimeSim HSPICE/FastSPICE、Cadence Spectre/Xcelium | 国产自研 SPICE 类工具，AI 加速为差异化卖点 |
| 先进封装 SI/PI | GrityDesigner（2025新推） | ANSYS RedHawk-SC、Cadence Sigrity、Siemens HyperLynx | 2025 年刚推出，与国际成熟产品尚有差距，但已具备混合格林函数+区域分解+场-路协同能力 |
| 光子/光电子 EDA | **不涉及** | Lumerical (Ansys)、VPIphotonics、Synopsys OptoCompiler、Cadence Curvy | 完全不对齐（业务范围不覆盖） |

---

## 调研结论

1. **UltraEM 全家族是国产射频/微波/毫米波 EDA 的代表性产品**，覆盖芯片级电磁仿真（UltraEM）、封装/PCB/天线级电磁仿真（SuperEM）、系统级电路仿真（FDSPICE）、AI 快速仿真与优化（EMOptimizer）、先进封装 SI/PI（GrityDesigner）五大产品线。

2. **AI 电磁大脑是核心创新点**，基于两项国家发明专利（CN108182316B、CN114611449B）与美国专利（US 12,197,839），通过卷积神经网络训练标准化射频库单元（FCell），实现"快速仿真"与"快速优化"设计范式，声称将射频 IC 设计效率提升千倍以上。

3. **可复用 + 参数化双核心理念**为法动科技在国际上首创，借鉴数字集成电路单元库思想，将射频无源器件的"积木单元"模块化、可复用。

4. **芯片-封装-PCB 一体化联合仿真**是差异化能力，支持三维 wirebonding/TSV/BGA 模型与 SiP/AiP 层级式设计。

5. **法动科技不涉及光子/光电子 EDA**，业务专注电磁频谱的射频段（含微波/毫米波）。如本项目关注光子 EDA 对齐，UltraEM 在光子部分无可对齐能力，应在光子相关功能清单中标注"不涉及"。

6. **学术诚信风险点**：法动科技官网未公开详细的第三方独立基准测试结果、具体工艺节点 PDK 认证清单、产品定价、UltraEM XA 与 XC 详细差异、GrityDesigner 商用版本号等信息，本清单对应位置已如实标注"未公开"。

---

## 参考来源汇总

- 法动科技官网首页：https://faradynamics.com/
- 公司介绍：https://faradynamics.com/aboutus.html?introduce
- 公司新闻：https://faradynamics.com/aboutus.html?news
- 招贤纳士：https://faradynamics.com/aboutus.html?recruit
- 联系我们：https://faradynamics.com/aboutus.html?contact
- 芯片电磁仿真解决方案：https://faradynamics.com/chip.html?chip_1
- EDA工具介绍：https://faradynamics.com/software.html?optimizer
- UltraEM-Virtuoso 设计流程教程：https://www.faradynamics.com/downloads/Tutorial_UltraEM.pdf
- 芯片电磁仿真解决方案PDF：https://faradynamics.com/downloads/files/芯片电磁仿真解决方案_宣传页.pdf
- 芯片-封装联合仿真解决方案PDF：https://faradynamics.com/downloads/files/芯片-封装联合仿真解决方案_宣传页.pdf
- 贴片天线阵列设计解决方案PDF：https://faradynamics.com/downloads/files/贴片天线阵列设计解决方案_宣传页.pdf
- 模拟射频无源芯片解决方案PDF：https://faradynamics.com/downloads/files/模拟射频无源芯片解决方案_宣传页.pdf
- 信号及电源完整性解决方案PDF：https://faradynamics.com/downloads/files/Signal%20Integrity%20and%20Power%20Integrity_宣传页.pdf
- EMOptimizer 创新文章（EETrend）：https://newsletter.eetrend.com/content/2025/100593022.html
- GrityDesigner 突破高密度互连（EETrend）：https://www.eetrend.com/content/2025/100596975.html
- 法动EDA电磁大脑赋能FDSPICE（雪球）：https://xueqiu.com/9983210953/297855535
- FDSPICE 实战篇（Sekorm）：https://www.sekorm.com/news/share?newId=528506266
- 法动科技A+轮融资（Sekorm）：https://www.sekorm.com/news/share?newId=53608772
- 法动科技国家高新技术企业（Sekorm）：https://www.sekorm.com/news/49294502.html
- LTCC巴伦芯片重塑射频技术（ElecFans）：https://m.elecfans.com/article/7146924.html
- 第九届集创赛"法动杯"赛题解析（EETrend）：https://www.eetrend.com/content/2025/100589337.html
- 江西工程学院校企培训：https://dzxxgcxy.jxue.edu.cn/2026/0401/c310a45166/page.htm
- 国产EDA突破FDSPICE（21IC）：https://www.21ic.com/a/987058.html
- 法动科技企业信息（水滴信用）：https://shuidi.cn/company-e9010244e289da606895079ce2f60be9.html
- 法动科技产品手册（mwrf）：https://mp.mwrf.net/handbook/lists/49.shtml
- 法动科技公众号文章集（ElecFans）：https://m.elecfans.com/user/5523632/
