# T14 逍遥科技 PIC Studio 功能点清单

- **工具名称**: PIC Studio（光电芯片全流程设计平台）
- **厂商**: 天府逍遥（成都）科技有限公司 / 上海逍遥光电科技有限公司（Latitude Design Automation, LDA）
- **总部**: 上海/成都（成都市双流区兴隆街道天府海创园二号地块5号楼10楼2号，电话 028-81756623）
- **官网 URL**: https://www.latitudeda.com/
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **类型**: 商业（国产）
- **学术诚信声明**: 本文档所有功能点均来源于逍遥科技官网（latitudeda.com）公开文档与应用案例，未公开能力已明确标注"未公开"。厂商成立于 2021 年，拥有 30+ 项专利与软件著作权。

---

## 产品概述

PIC Studio 是逍遥科技（LDA）面向"特色工艺"半导体芯片的 EDA/PDA 全流程设计平台，覆盖光电子集成芯片（PIC）从元件级到系统级的完整设计流程，包含 pSim Plus、pLogic、Advanced SDL、PhotoCAD、pMaxwell、pVerify 等核心工具。平台与全球主要硅光 Foundry 的 PDK/ADK 紧密集成，支持 DRC/LVS/PEX 物理验证、版图后仿真、自动 AWG 设计与测试设计套件（TDK），致力于为光电芯片与系统创新"去风险"，提升一次流片成功率。LDA 同时提供 Power Studio、MEMS Studio、Meta Studio 等姊妹平台覆盖功率器件、MEMS 传感器、超构透镜等特色工艺方向。

来源: https://www.latitudeda.com/about/companyIntroduction ； https://www.latitudeda.com/document/1012 ； https://www.latitudeda.com/document/1016

---

## 功能点清单

### 1. PhotoCAD（光电芯片版图设计 - 代码驱动）

PhotoCAD 是 Python3 代码驱动的光电芯片版图设计环境，与传统 PDA 工具相比在灵活性、自动布线和 PDK 集成方面具备优势。

- **1.1 快速 PDK 设置**: 通过导入 CSV 文件自动生成 layers.py、display.py、layers.lyp 三个 PDK 文件，跳过手动设置，节省时间。来源: https://www.latitudeda.com/document/772
- **1.2 高速布局生成**: 通过计算结果缓存、重复单元合并、自定义布线算法等优化，布局生成速度提升 10 倍以上。来源: https://www.latitudeda.com/document/772
- **1.3 Python 参数化单元（PCell）设计**: 基于 Python 的参数化单元格设计，所有参数定义在单元格类中，布局在 build() 方法中通过添加实例、元素、端口实现。来源: https://www.latitudeda.com/document/772
- **1.4 智能布局拼接**: 支持分块构建布局后期智能拼接为完整布局，修改后只重建更新部分（增量重建），便于团队协作与设计迭代。来源: https://www.latitudeda.com/document/772
- **1.5 工艺迁移**: 导入 GDSII 并通过可配置层映像表映射工艺/层定义，导出时自动对齐端口，最小化修改即可将现有光电芯片迁移到新工艺。来源: https://www.latitudeda.com/document/772
- **1.6 光波导 Linker 自定义**: 在光波导 linker 功能上提供更高自定义能力，为复杂设计提供灵活性。来源: https://www.latitudeda.com/document/391
- **1.7 高级自动布线**: 支持 Auto-transition、Auto-bend、Auto-expand、Auto-taper 等功能，允许用户设定过点进行布线避让，达国际领先水平。来源: https://www.latitudeda.com/document/391
- **1.8 ADK（Assembly Design Kit）框架**: 在 PhotoCAD 中生成具有定义光学和电气接口的标准化芯片框架，自动放置和布线元件，光学波导布线与电气焊盘金属走线，支持光学相控阵（OPA）等复杂电路快速实现。来源: https://www.latitudeda.com/document/1016
- **1.9 完整 PDK 集成**: 对未预先建置的 Foundry PDK，用户可编辑 CSV 档导入 PDK 工艺层基于 Foundry 工艺进行版图设计。来源: https://www.latitudeda.com/document/391 ； https://www.latitudeda.com/solution/pdk/pdkSupport
- **1.10 一体化工具链**: 提供从布局到原理图、再到基于 SDL 的代码生成的完整工具链。来源: https://www.latitudeda.com/document/391
- **1.11 pSim 模拟能力集成**: 基于 pSim 提供时域、频域和眼图分析的强大模拟。来源: https://www.latitudeda.com/document/391
- **1.12 版图后仿真**: 通过集成 PhotoCAD 布局与 pSim 模拟引擎执行版图后模拟，验证实际布局实现是否符合预期性能。来源: https://www.latitudeda.com/document/1016

### 2. pSim / pSim Plus（光电链路/系统级仿真）

pSim 为光子电路电路级模拟器，pSim Plus 为光电融合系统级仿真器，pSim Plus V1.0.5 起支持高层次系统级仿真。

- **2.1 光子电路电路级仿真**: pSim 提供业界领先精度的元件建模与光电链路仿真。来源: https://www.latitudeda.com/document/495
- **2.2 光电全链路一体化仿真**: pSim Plus 采用创新的复合式集成仿真引擎，将传统分段仿真（电、光分段仿真再拼接）整合到单一软件平台，用户无需在多个平台之间切换即可完成完整仿真流程。来源: https://www.latitudeda.com/document/1014
- **2.3 多模型兼容**: 平台支持 DSP 高速 IO 端口（如 SERDES）、DSP 均衡算法模块、S 参数、光源、调制器、单模/多模光纤、探测器、TIA 等各类光电器件模型。来源: https://www.latitudeda.com/document/1014
- **2.4 IBIS-AMI / IBIS / Spice 模型支持**: 兼容高速 SERDES 端口的 IBIS-AMI 模型、I/O 端口的 IBIS 模型与集成电路的 Spice 模型，是解决光电协同仿真的关键。来源: https://www.latitudeda.com/document/1014
- **2.5 先进封装寄生效应分析**: 全面考虑先进封装中 RDL（重布线层）和 TSV（硅通孔）的 RLC 寄生效应，进行更贴近实际的仿真分析。来源: https://www.latitudeda.com/document/1014
- **2.6 非线性光纤模拟**: 利用 FiberNLS_PMD 进行非线性光纤模拟，支持 NLS 与 PMD 光纤模拟技术。来源: https://www.latitudeda.com/document/495
- **2.7 WDM 远距离传输**: 支持多信道波分复用（WDM）远距离传输与配置 FEC 编码的 PDM-QPSK 调制技术。来源: https://www.latitudeda.com/document/495
- **2.8 电子子系统建模**: 支持 Driver 电路模拟、TIA 电路模拟、RLCG 模拟电路仿真及第三方 snp 文件导入。来源: https://www.latitudeda.com/document/495
- **2.9 DSP 算法支持**: 支持前馈均衡（FFE）、前向纠错（FEC）等 DSP 算法。来源: https://www.latitudeda.com/document/495
- **2.10 TDECQ 信号品质评估**: 通过 TDECQ 评估信号品质并提供图形化输出分析。来源: https://www.latitudeda.com/document/495
- **2.11 器件自定义**: 支持导入 Python 文件定义单个器件、基于 Python 自建器件库导入、导入信号文件作为光/信号源。来源: https://www.latitudeda.com/document/495
- **2.12 多电平 BER 分析**: 多电平 BER 分析模块，支持高斯估计和蒙特卡洛估计。来源: https://www.latitudeda.com/document/495
- **2.13 眼图与星座图分析**: 大规模数据集的眼图展示与信号传输星座图展示。来源: https://www.latitudeda.com/document/495
- **2.14 版图后仿真无缝集成**: pSim Plus 实现 GDS 版图到版图后仿真的无缝集成，助力一次流片成功并降低成本。来源: https://www.latitudeda.com/document/776
- **2.15 光计算性能优化**: 平台包含优化功能，对于光计算应用的速度提升可达 13 倍。来源: https://www.latitudeda.com/document/1016
- **2.16 三种电极建模方法**: pSim Plus 支持阻抗匹配、S 参数分析和电路仿真三种电极建模方法。来源: https://www.latitudeda.com/document/804
- **2.17 光电协同联合仿真**: 通过 pSim Plus 支持电子和光学器件的全面联合仿真，可模拟组合光电线路（包括 RLC 效应和受控源）。来源: https://www.latitudeda.com/document/804

### 3. pLogic（光电原理图编辑器）

pLogic 是支持光电融合的原理图编辑器，作为 Advanced SDL 与 pSim 的前端入口。

- **3.1 拖放式可视化原理图设计**: 设计师可在 pLogic 中拖放器件形成可视化原理图。来源: https://www.latitudeda.com/document/48
- **3.2 PDK 符号库**: 提供带物理参数、光学和电气端口的 PDK 符号库，支持完整 PIC Studio 设计流程。来源: https://www.latitudeda.com/document/48
- **3.3 三合一控制面板**: pLogic 的 3-in-1 控制面板同时显示原理图、生成的绘图代码和版图，让用户完全掌控设计过程。来源: https://www.latitudeda.com/document/48
- **3.4 pSim 电路仿真驱动**: pLogic 可驱动 pSim 进行电子光子电路仿真。来源: https://www.latitudeda.com/document/48
- **3.5 Spice 电子电路仿真**: pLogic 可驱动 Spice 电子电路仿真，实现电子光子融合仿真与优化。来源: https://www.latitudeda.com/document/48

### 4. Advanced SDL（原理图驱动版图工具）

Advanced SDL 是基于 Python3 的原理图驱动版图（Schematic-Driven Layout）工具，桥接 pLogic 与 PhotoCAD。

- **4.1 原理图驱动版图（SDL）**: 设计师在 pLogic 中拖放器件形成可视化原理图，由 Advanced SDL 引擎生成标准 Python3 版图脚本，调用 PhotoCAD 生成版图，自动连接所有参数化器件、光波导和电子金属走线。来源: https://www.latitudeda.com/document/48
- **4.2 版图驱动原理图（LDS）**: 支持从 PhotoCAD Python3 版图脚本反向生成原理图打印机（schematic printer），便于设计师调试电路，让脚本驱动版图的工程师也能享用结合光子和电子电路的原理图工具。来源: https://www.latitudeda.com/document/48
- **4.3 参数化光电器件**: 支持参数化电子光子器件、光波导连接和电子金属走线，物理参数设置支持硅基光电子物理特性。来源: https://www.latitudeda.com/document/48
- **4.4 高度参数化曲线版图**: 通过经过量产验证的 PhotoCAD 版图引擎，便于创建高度参数化和曲线的电子光子融合电路版图，无需大型脚本。来源: https://www.latitudeda.com/document/48
- **4.5 物理验证流程集成**: Advanced SDL 支持原理图驱动设计的直接版图提取，用于器件级验证。来源: https://www.latitudeda.com/document/804

### 5. OpenLayout（图形界面版图工具）

OpenLayout 是 2024 年 7 月发布的图形化版图设计工具，专为特色工艺（功率器件、MEMS、光电子）量身打造。

- **5.1 所见即所得设计**: 采用所见即所得的设计方法，版图数据库与单元列表的多种呈现方式清晰展现设计层次。来源: https://www.latitudeda.com/document/770
- **5.2 拖拽式工具栏**: 集绘图、编辑、测量、DRC 等功能于一身的拖拽式工具栏，无需陡峭学习曲线即可上手。来源: https://www.latitudeda.com/document/770
- **5.3 灵活物件选择**: 提供单选、多选、局部选中与全局选中控制，便于在复杂阵列结构中修改。来源: https://www.latitudeda.com/document/770
- **5.4 工艺层设定与管理**: 允许设计师轻松定义和管理多个工艺层（如 PMUT 压电层、电极层），准确反映实际制程需求。来源: https://www.latitudeda.com/document/770
- **5.5 尺标测量功能**: 测量标尺功能通过简单鼠标滑动即可测试设计对象尺寸。来源: https://www.latitudeda.com/document/770
- **5.6 层显示/隐藏管理**: 直观的层管理界面，可快速切换不同工艺层可见性，便于检查层间关系。来源: https://www.latitudeda.com/document/770
- **5.7 多格式数据支持**: 支持 DXF、GDSII 等业界数据格式，轻松实现数据转换。来源: https://www.latitudeda.com/document/770
- **5.8 参数化版图单元生成器**: 内置参数化版图单元生成器，可定制场环、弹簧等异形结构，加速设计迭代。来源: https://www.latitudeda.com/document/770
- **5.9 特色工艺曲线布线**: 填补传统版图工具难以满足的功率器件、MEMS 等特色工艺产品的曲线布线需求。来源: https://www.latitudeda.com/document/770
- **5.10 多物理场耦合仿真接口**: 2024 升级支持多物理场仿真软件的接口，设计初期即可进行仿真验证。来源: https://www.latitudeda.com/document/770
- **5.11 材料库与制程管理**: 内置 MEMS 常用材料库，支持自定义材料参数。来源: https://www.latitudeda.com/document/770
- **5.12 3D 视图与编辑**: 提供 3D 视图，支持直接在 3D 视图中编辑 MEMS 组件。来源: https://www.latitudeda.com/document/770
- **5.13 功率器件专用 DRC/LVS**: 内置功率器件专用设计规则检查与版图电路一致性检查规则。来源: https://www.latitudeda.com/document/770
- **5.14 电气性能仿真接口**: 支持与 TCAD、SPICE 等电气性能仿真软件的接口。来源: https://www.latitudeda.com/document/770
- **5.15 高电压/大电流设计支持**: 提供特殊的高电压间距规则、大电流导线设计等。来源: https://www.latitudeda.com/document/770
- **5.16 与姊妹平台无缝衔接**: 可与 Power Studio、MEMS Studio 等多物理场建模、设计工具无缝衔接，实现从二维版图到三维模型再到多物理场仿真的完整设计流程。来源: https://www.latitudeda.com/document/770

### 6. pMaxwell（电磁求解器：FDTD + RCWA）

pMaxwell 是 PIC Studio 的元件级电磁求解器，集成 FDTD 与 RCWA 两种方法，位于 PIC Studio 设计流程的元件部分。

#### 6.A pMaxwell-FDTD（时域有限差分）

- **6.1 2D/3D 仿真**: 支持二维（2D）和三维（3D）仿真，为不同设计方案提供灵活性。来源: https://www.latitudeda.com/document/774
- **6.2 多种光源**: 提供平面波、波导模式和偶极光源，满足各种仿真需求。来源: https://www.latitudeda.com/document/774
- **6.3 边界条件**: 支持完全匹配层（PML）和周期性边界条件等，准确模拟光在器件边界的行为。来源: https://www.latitudeda.com/document/774
- **6.4 材料属性定义**: 允许用户定义并纳入不同材料的光学特性，实现逼真模拟。来源: https://www.latitudeda.com/document/774
- **6.5 分析监测工具**: 提供综合分析工具，包括功率通量、重叠积分、远场模式和 Poynting 矢量。来源: https://www.latitudeda.com/document/774
- **6.6 Python 脚本与自动化**: 支持使用 Python 编写脚本，自动执行重复性任务并执行参数扫描以进行优化。来源: https://www.latitudeda.com/document/774
- **6.7 电磁场和传输频谱计算**: 计算光子器件的电磁场分布和传输谱。来源: https://www.latitudeda.com/document/774
- **6.8 波导 S 参数计算**: 模拟波导器件的 S 参数，用于鉴定其在光路中的行为。来源: https://www.latitudeda.com/document/774
- **6.9 应用范围**: 广泛应用于波导器件、光栅结构、超表面、纳米光子器件的设计和仿真。来源: https://www.latitudeda.com/document/774
- **6.10 与 PIC Studio 集成**: 与 PIC Studio 软件套件中的其他工具无缝集成，促进全面设计工作流程。来源: https://www.latitudeda.com/document/774

#### 6.B pMaxwell-RCWA（严格耦合波分析）

- **6.11 严格耦合波分析**: 用于分析电磁波与周期性结构的相互作用，支持多层结构（输入层/输出层/中间层）。来源: https://www.latitudeda.com/document/629
- **6.12 参数扫描**: 支持对支柱高度和半径等参数执行扫描以优化结构。来源: https://www.latitudeda.com/document/629
- **6.13 现场电磁场计算**: 可计算结构内（如 xz 平面）的电场和磁场各分量。来源: https://www.latitudeda.com/document/629
- **6.14 1D/2D 可视化绘图**: 0.6 版新增 plot_1D、plot_2D 函数，支持 "real"/"image"/"abs" 数据类型可视化。来源: https://www.latitudeda.com/document/775
- **6.15 折射率监视器**: 0.6 版新增 GetEpsMu_xy/GetEpsMu_xz/GetEpsMu_yz 函数，获取指定界面的介电常数和磁导率。来源: https://www.latitudeda.com/document/775
- **6.16 CSV 数据导出**: 支持将传输数据保存为 CSV 文件用于后续分析。来源: https://www.latitudeda.com/document/629
- **6.17 傅立叶阶数控制**: 通过傅立叶展开截断阶数控制精度与计算时间。来源: https://www.latitudeda.com/document/629

### 7. pVerify（DRC 物理验证工具）

pVerify 是 PIC Studio 内的 DRC 物理验证工具，提供全面的设计规则检查功能。

- **7.1 最小宽度检查**: 确保没有特征比工艺定义的最小尺寸更窄，对波导尤为重要。来源: https://www.latitudeda.com/document/805
- **7.2 精确宽度检查**: 验证特定特征是否保持精确尺寸，对定向耦合器等依赖精确几何参数的器件重要。来源: https://www.latitudeda.com/document/805
- **7.3 间距检查**: 验证相邻特征之间是否存在足够分隔，防止制造问题和不需要的耦合效应。来源: https://www.latitudeda.com/document/805
- **7.4 面积检查**: 确保特征足够大可以可靠制造，对接触焊盘和金属结构重要。来源: https://www.latitudeda.com/document/805
- **7.5 层生成布尔运算**: 提供或、与、异或、A-B、B-A 等布尔运算支持复杂设计规则检查操作。来源: https://www.latitudeda.com/document/805
- **7.6 尺寸操作**: 提供正向和负向尺寸操作用于修改几何特征。来源: https://www.latitudeda.com/document/805
- **7.7 跨层包围/分隔检查**: 实现不同层之间的包围和分隔要求等扩展几何检查。来源: https://www.latitudeda.com/document/805
- **7.8 几何关系检查**: 包括不同层之间的内部、外部、不相交和重叠条件检查。来源: https://www.latitudeda.com/document/805
- **7.9 锐角检测与修复**: 提供锐角检测，支持用户自行决定自动修复或手动修复。来源: https://www.latitudeda.com/document/805 ； https://www.latitudeda.com/document/1016
- **7.10 密度检查**: 根据指定限制验证局部图形密度。来源: https://www.latitudeda.com/document/805
- **7.11 多设计流程集成**: 支持原理图驱动、版图驱动和 GDS 驱动方法的设计规则检查集成。来源: https://www.latitudeda.com/document/805
- **7.12 自定义验证规则**: 用户可基于层属性和几何约束定义自定义验证规则。来源: https://www.latitudeda.com/document/1016
- **7.13 基于 Windows 的设计流程**: 与基于 Windows 的设计流程无缝集成，所有设计人员都能使用，促进持续的设计验证。来源: https://www.latitudeda.com/document/805
- **7.14 业界签核工具兼容**: 与业界标准签核工具（如 Calibre）兼容。来源: https://www.latitudeda.com/document/805
- **7.15 LVS（版图对比原理图）**: 支持版图对比原理图验证，针对光电子集成芯片的 LVS 输出与应用场景。来源: https://www.latitudeda.com/document/804
- **7.16 PEX（寄生参数提取）**: 支持寄生参数提取，提供 PEX 开发方法和输出格式。来源: https://www.latitudeda.com/document/804
- **7.17 GDS2INFO 网表提取**: 支持从现有 GDS 文件提取连接信息和生成网表，适用于传统设计，不受限 PDK。来源: https://www.latitudeda.com/document/804
- **7.18 高效验证引擎**: 高效的验证引擎在保持 DRC 高准确性的同时实现快速周转。来源: https://www.latitudeda.com/document/805
- **7.19 早期阶段 DRC 验证**: 早期阶段的设计规则检查验证实现快速问题解决。来源: https://www.latitudeda.com/document/805

### 8. PIVOT（光子智能变量优化工具）

PIVOT（Photonic Intelligent Variable Optimization Tool）是 2024 年 11 月推出的、基于 pSim Plus 的光子智能变量优化扩展工具。

- **8.1 可视化配置**: 通过可视化配置实现简单操作，仅需 4 行代码即可启动优化流程。来源: https://www.latitudeda.com/document/971 ； https://www.latitudeda.com/document/972
- **8.2 灵活 API 接口**: 提供灵活的 API 接口，支持多种仿真软件平台对接，可作为高级优化模块无缝集成至多领域仿真工具。来源: https://www.latitudeda.com/document/971
- **8.3 优化中断恢复**: 支持优化中断后继续优化任务。来源: https://www.latitudeda.com/document/971
- **8.4 优化过程记录**: 完整保存优化过程便于分析。来源: https://www.latitudeda.com/document/971
- **8.5 多种并行框架**: 支持任务并行化处理。来源: https://www.latitudeda.com/document/971
- **8.6 丰富算子选择**: 提供丰富的算法选择，适配不同优化需求。来源: https://www.latitudeda.com/document/971
- **8.7 非梯度优化算法**: 当前版本采用非梯度优化算法，用户需在系统外部定义目标函数后输入系统。来源: https://www.latitudeda.com/document/971
- **8.8 高维参数空间构建**: 支持构建高维参数空间（如 12 维参数空间对应网络组件），采用二值参数（0/1 状态）。来源: https://www.latitudeda.com/document/971
- **8.9 实时优化反馈**: 实时显示设计参数演变、优化结果跟踪、性能指标和最终配置验证。来源: https://www.latitudeda.com/document/971
- **8.10 WDM 链路自动设计**: 基于微环的波分复用链路优化、自定义通道配置和自动生成复用结构。来源: https://www.latitudeda.com/document/971 ； https://www.latitudeda.com/document/972
- **8.11 可编程光子数字链路设计**: 自定义输出矩阵，根据用户需求生成最优链路参数。来源: https://www.latitudeda.com/document/971
- **8.12 光子晶体设计**: 支持电磁响应优化、基于指定参数的结构生成，可与 Ceviche 仿真框架集成。来源: https://www.latitudeda.com/document/971
- **8.13 经典优化应用**: 适用于曲线拟合应用、方程求解优化和参数空间探索等经典优化问题。来源: https://www.latitudeda.com/document/971
- **8.14 遗传算子配置**: 支持种群规模确定、变异率设定、迭代次数设置和遗传算子选择。来源: https://www.latitudeda.com/document/971

### 9. Power Studio（功率器件全流程设计）

Power Studio 是面向 SiC/GaN 功率器件的全流程设计自动化平台。

- **9.1 标准 PCell 设计**: 支持标准参数化单元（PCell）设计。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.2 工艺及器件建模（FEM）**: 支持工艺及器件建模（有限元）。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.3 三维界面模型**: 支持三维界面模型。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.4 统计分析**: 支持工艺/电源电压/温度分布/蒙特卡罗统计分析。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.5 DTCO 协同优化**: 支持设计与工艺协同优化（Design Technology Co-Optimization）。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.6 版图功耗分析**: 包含版图功耗分析工具。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.7 三维器件截面分析**: 包含三维器件截面分析工具。来源: https://www.latitudeda.com/solution/flow/Power%20Studio
- **9.8 产品线构成**: 由 pLogic、Advanced SDL、pLayout、pVerify、版图功耗分析工具、三维器件截面分析工具构成。来源: https://www.latitudeda.com/solution/flow/Power%20Studio

### 10. MEMS Studio（MEMS/传感器全流程设计）

MEMS Studio 是面向 MEMS 与智能传感器的全流程设计自动化平台。

- **10.1 标准 PCell 与 FEM 建模**: 支持标准参数化单元设计与工艺及器件建模（FEM）。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.2 阻尼计算**: 支持阻尼计算，针对 MEMS 振动器件关键参数。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.3 电特性仿真整合**: 支持电特性仿真整合。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.4 DTCO 协同优化**: 支持设计与工艺协同优化。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.5 多物理场有限元接口**: 提供多物理场优化接口及有限元分析工具。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.6 三维器件截面分析**: 包含三维器件截面分析工具。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.7 Chiplet Designer 热仿真**: Chiplet Designer 模块支持 2.5D Chiplet 集成的热仿真，支持三角形网格、制造过程（沉积层）配置、物理场设置与热分布可视化（热点识别、温度梯度、热界面、热均匀性分析）。来源: https://www.latitudeda.com/document/763
- **10.8 OCS 光线路交换仿真**: 支持基于 MEMS 的 Optical Circuit Switch（OCS）仿真，包含网格设置、几何结构、制造工艺配置、边界条件（电极配置、位移约束）和 Pull-in Voltage 位移仿真。来源: https://www.latitudeda.com/document/762
- **10.9 应用器件覆盖**: 支持 Vibratory Gyroscope、SAR RF Filter、BAW RF Filter、FBAR、PMUT、CMUT、Piezoelectric Pressure Sensor、Piezoresistive Pressure Sensor、RF Switch、Microphone、Tactile Sensor 等 11 类器件。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio
- **10.10 产品线构成**: 由 pLogic、Advanced SDL、pLayout、pVerify、多物理场优化接口及有限元分析工具、三维器件截面分析工具构成。来源: https://www.latitudeda.com/solution/flow/MEMS%20Studio

### 11. Meta Studio（超构透镜全流程设计）

Meta Studio 是超透镜（Metalens）设计、仿真和版图解决方案。

- **11.1 相位设计**: 用户可为各种超透镜应用创建自定义相位分布。来源: https://www.latitudeda.com/document/591
- **11.2 超原子结构设计**: 设计和优化构成超透镜的各个超原子结构（结构类型、几何参数、材料属性）。来源: https://www.latitudeda.com/document/591
- **11.3 焦平面与传播平面场分布**: 提供不同平面上光场分布的详细计算。来源: https://www.latitudeda.com/document/591
- **11.4 GDS 导出**: 通过 PhotoCAD 生成符合行业标准的 GDS 文件用于制造。来源: https://www.latitudeda.com/document/591 ； https://www.latitudeda.com/document/44
- **11.5 多算法集成**: 融合粒子群优化算法、物理光学、傅里叶光学、角谱衍射、FDTD 和 RCWA 等多种先进算法与理论模型。来源: https://www.latitudeda.com/document/591
- **11.6 超原子库自动优化**: 自动模拟和选择特定材料和频率下的最佳超原子结构。来源: https://www.latitudeda.com/document/591
- **11.7 正向设计流程**: 包含设计目标确定、超原子参数设计、超原子库优化、目标相位设计、仿真与验证等关键步骤。来源: https://www.latitudeda.com/document/591
- **11.8 逆向设计流程**: 支持定义优化成本函数、初始超表面设计、正向仿真评估、梯度计算与设计更新、最终验证等高级逆向设计过程。来源: https://www.latitudeda.com/document/591
- **11.9 双曲相位透镜**: 支持双曲相位透镜设计（如 633 nm 波长、30λ 直径、10λ 焦距、320 nm 超原子周期、4 级离散相位控制），结果与 Ansys FDTD 仿真高度一致。来源: https://www.latitudeda.com/document/591
- **11.10 无衍射锥透镜**: 支持无衍射锥透镜设计（如 633 nm 波长、30λ 直径、45° 锥角）。来源: https://www.latitudeda.com/document/591
- **11.11 超表面准直器**: 支持超表面准直器设计（如 905 nm 波长、28λ 直径、13° 出射角）。来源: https://www.latitudeda.com/document/591
- **11.12 超分辨率聚焦透镜**: 支持超分辨率聚焦透镜设计。来源: https://www.latitudeda.com/document/591
- **11.13 无衍射光束相位表面**: 支持无衍射光束相位表面设计。来源: https://www.latitudeda.com/document/591

### 12. 其他平台级工具与服务

- **12.1 AWG Wizard（阵列波导光栅自动设计）**: 自动化设计阵列波导光栅（AWG），支持 1×N、N×N 和 M×N AWG 配置的自动 GDS 生成，与 FDTD 协同模拟实现精确建模，提供用于快速性能估计的分析模块及工艺变异分析。来源: https://www.latitudeda.com/document/1016
- **12.2 TDK（测试设计套件）**: 弥合设计和制造验证差距，提供将布局端口与物理测试点关联的 JSON 映射文件、自动光纤对准和探针定位、不同器件类型的预编程测试序列以及实时数据收集和统计分析。来源: https://www.latitudeda.com/document/1016
- **12.3 闭环工作流程**: 设计、测试和模拟的集成创建闭环工作流程，在数据驱动的开发周期中连接 PhotoCAD、pSim Plus 和 TDK 平台，加速开发周期并提高良率。来源: https://www.latitudeda.com/document/1016
- **12.4 LDAcc 产业链助推计划**: 深圳逍遥科技为代工伙伴提供 LDAcc 计划，提供个性化技术咨询服务（工艺流程开发、器件建模、PDK 验证等），基于高度可扩展的工艺设计套件库、自动布局和仿真工具。来源: https://www.latitudeda.com/document/334
- **12.5 软件许可管理**: 使用 WIBU Information Systems GmbH（德国）的软件许可管理解决方案，所有已发布软件产品未发现漏洞或安全问题。来源: https://www.latitudeda.com/document/239
- **12.6 三个技术发展方向**: 逍遥科技当前专注于人工智能辅助光子设计、异构集成支持和跨晶圆厂合作三个方向。来源: https://www.latitudeda.com/document/1016

---

## PDK 生态

PIC Studio 支持全球主要硅光 Foundry 的 PDK，PhotoCAD 可一键导入工艺层完成 PDK 定制，并支持快速生成定制 PDK。

| Foundry | 工艺 | PDK 版本 | 发布时间 | 波导厚度 | 金属 | 波段 | 元件库 |
|---|---|---|---|---|---|---|---|
| IMECAS（微电子所） | Si | 2.1 | 2023-06 | 220nm | AlCu | C, O | Grating coupler, Crossing, MMI, Directional coupler, Y branch, Ring resonator, Polarization beam splitter, Arrayed Waveguide Grating, Photo detector, Modulator |
| IMECAS（微电子所） | SiN | 1.0 | 2023-06 | 200nm | Not available | C, O | Grating coupler, Crossing, MMI, Directional coupler, Y branch, Ring resonator |
| SITRI（工研院） | Si | 3.0 | 2023-03 | 220nm | AlCu | C, O | Grating coupler, Crossing, MMI, Directional coupler, Y branch, Ring resonator, Polarization beam splitter, Photo detector, Modulator |
| SITRI（工研院） | SiN | 3.0 | 2024-03 | 400nm | AlCu | C, O, Visible | Grating coupler, Edge Coupler, Crossing, MMI |
| IOPTEE（南智） | Lithium Niobate (LN) | 1.0 | 2024-06 | 薄膜 600nm / 脊波导 300nm | Au, NiCr | C | Grating coupler, Edge coupler, Mach-Zehnder interferometer |
| CORNERSTONE | SOI | 1 | 2024-05 | 220nm, 340nm, 500nm | HEATER | C, O | Grating Coupler, MMI, Crossing, Taper, Ysplitter |
| CORNERSTONE | SiN | 1 | 2024-05 | 300nm | HEATER | C, O | Grating Coupler, MMI |
| CORNERSTONE | Suspended-Si | 1 | 2024-05 | 500nm | None | 3800nm | Grating Coupler, Sbend |
| SiEPIC | Si | 1 | 2024-11 | 220nm | None | C, O | Edge Coupler, Grating Coupler, Y Branch, MMI, Crossing, Terminator |
| SiEPIC Shuksan | Si | 1 | 2024-11 | 220nm | TiW, Al | C, O | Waveguide Taper, Grating Coupler, DFB Laser, Y-splitter, 2x2 Splitter, Power Tap, Electrical Pad, Heater, Photonic Wire Bond, Terminator |
| TowerSemi | PH18 | 1 | 2024-11 | 220nm | Al, Cu | C, O | Grating Coupler, MMI, Crossing, Y-junction, Transition, Directional Coupler, Photodiode, Phase Shifter Diode, Bondpad |
| VTT | SOI | 1 | 2024-04 | 3 µm | Au, Al | C, O | Edge Coupler, MMI, Bend, Transition |

来源: https://www.latitudeda.com/solution/pdk/pdkSupport ； https://www.latitudeda.com/document/1016 （武粤光电、Tower Semiconductor、SiLTerra、南智光电等）

**ADK（Assembly Design Kit）支持**: PIC Studio 为 ADK 提供先进支持，用于准备光子设计进行封装和与其他元件集成。来源: https://www.latitudeda.com/document/1016

---

## 客户案例

- **诺基亚贝尔实验室 - Cell-free 大规模 MIMO 前传网络**: 用户成功案例，使用 PIC Studio 探索光子技术在 Cell-free 大规模 MIMO 前传网络中的应用。来源: https://www.latitudeda.com/document/1015
- **诺基亚贝尔实验室 - 全光循环神经网络**: 使用 PIC Studio 完成全光循环神经网络设计。来源: https://www.latitudeda.com/document/1010
- **诺基亚贝尔实验室 - 码间干扰均衡方案**: pSim Plus 光电链路均衡方案解析，克服码间干扰。来源: https://www.latitudeda.com/document/979
- **PhotoCAD 设计量子比特处理器**: 使用 PhotoCAD 进行量子比特处理器设计。来源: https://www.latitudeda.com/document/978
- **pSim Plus 可编程光子三角链路自动化配置**: 实现可编程光子三角链路的自动化配置。来源: https://www.latitudeda.com/document/942
- **pSim Plus 多通道级联硅微环计算光谱仪**: 基于多通道级联硅微环谐振器的计算光谱仪。来源: https://www.latitudeda.com/document/941
- **pSim Plus 光学神经网络 PAM 仿真**: 实现光学神经网络中的脉冲幅值调制技术仿真。来源: https://www.latitudeda.com/document/940
- **PhotoCAD 马赫曾德干涉仪光学卷积矩阵**: 使用 PhotoCAD 实现基于马赫曾德干涉仪的光学卷积矩阵单元。来源: https://www.latitudeda.com/document/758
- **MEMS Studio OCS 光线路交换**: 基于 MEMS 的 Optical Circuit Switch 仿真教程。来源: https://www.latitudeda.com/document/762
- **MEMS Studio Chiplet 热仿真**: MEMS Studio 进行 Chiplet 热仿真教程。来源: https://www.latitudeda.com/document/763

---

## 学术诚信声明

本文档所有功能点均来自逍遥科技官网（https://www.latitudeda.com/）公开文档、产品介绍、应用案例与 PDK 支持页面，调研日期为 2026-06-25。所有来源 URL 已在各功能点末尾明确标注。对于官网未明确公开的能力（如部分模块的精确版本号、内部算法实现细节、性能基准），本文档不做臆造或推测，未公开部分已在原文中保留"未公开"或"未明确"标注。

参考来源汇总:
- https://www.latitudeda.com/
- https://www.latitudeda.com/about/companyIntroduction
- https://www.latitudeda.com/solution
- https://www.latitudeda.com/solution/product
- https://www.latitudeda.com/solution/flow/PIC%20Studio
- https://www.latitudeda.com/solution/flow/Power%20Studio
- https://www.latitudeda.com/solution/flow/MEMS%20Studio
- https://www.latitudeda.com/solution/flow/Meta%20Studio
- https://www.latitudeda.com/solution/pdk/pdkSupport
- https://www.latitudeda.com/document/391 （PhotoCAD 重新定义光电子芯片版图设计）
- https://www.latitudeda.com/document/772 （PhotoCAD 疏通光电芯片版图设计痛点）
- https://www.latitudeda.com/document/1014 （pSim Plus 实现光电全链路一体化仿真）
- https://www.latitudeda.com/document/495 （pSim Plus V1.0.5 版本发布）
- https://www.latitudeda.com/document/776 （pSim Plus GDS 版图到版图后仿真）
- https://www.latitudeda.com/document/48 （Advanced SDL 原理图驱动版图生成）
- https://www.latitudeda.com/document/770 （OpenLayout 重磅发布）
- https://www.latitudeda.com/document/774 （pMaxwell-FDTD 综合指南）
- https://www.latitudeda.com/document/629 （pMaxwell-RCWA 综合指南）
- https://www.latitudeda.com/document/775 （pMaxwell RCWA 0.6 版新增可视化）
- https://www.latitudeda.com/document/805 （光电子集成芯片的设计规则检查）
- https://www.latitudeda.com/document/804 （硅基光电子集成芯片物理验证与光电协同设计）
- https://www.latitudeda.com/document/971 （PIVOT 重磅发布）
- https://www.latitudeda.com/document/972 （PIVOT 教程）
- https://www.latitudeda.com/document/591 （Meta Studio 全面的超透镜解决方案）
- https://www.latitudeda.com/document/44 （Meta Studio 设计全流程）
- https://www.latitudeda.com/document/1012 （PIC Studio 设计平台如何为光电芯片与系统创新"去风险"）
- https://www.latitudeda.com/document/1016 （PIC Studio 协同 Foundry 生态系加速硅光芯片全流程开发）
- https://www.latitudeda.com/document/334 （逍遥科技特色工艺产业链助推计划 LDAcc）
- https://www.latitudeda.com/document/239 （产品声明）
- https://www.latitudeda.com/document/586 （产品计划）
- https://www.latitudeda.com/document/762 （MEMS Studio OCS 仿真教程）
- https://www.latitudeda.com/document/763 （MEMS Studio Chiplet 热仿真教程）
- https://www.latitudeda.com/document/1015 （诺基亚贝尔实验室 Cell-free MIMO 前传网络）
- https://www.latitudeda.com/document/1010 （诺基亚贝尔实验室全光循环神经网络）
- https://www.latitudeda.com/document/979 （pSim Plus 光电链路均衡方案）
- https://www.latitudeda.com/document/978 （PhotoCAD 设计量子比特处理器）
- https://www.latitudeda.com/document/942 （pSim Plus 可编程光子三角链路）
- https://www.latitudeda.com/document/941 （pSim Plus 多通道级联硅微环计算光谱仪）
- https://www.latitudeda.com/document/940 （pSim Plus 光学神经网络 PAM 仿真）
- https://www.latitudeda.com/document/758 （PhotoCAD 马赫曾德干涉仪光学卷积矩阵单元）
