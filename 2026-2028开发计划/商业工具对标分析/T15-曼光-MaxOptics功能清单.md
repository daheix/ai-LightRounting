# T15 上海曼光科技 Max-Optics Studio 功能点清单

- **工具名称**: Max-Optics Studio
- **厂商**: 上海曼光信息科技有限公司 (Shanghai Max-Optics Information Technology Co., Ltd.)
- **官网 URL**: https://www.max-optics.com/
- **知识库 URL**: https://kb.max-optics.com/
- **总部**: 上海虹口区飞虹路118号瑞虹企业天地 T1 办公楼3103-3108室
- **成立年份**: 2018 年
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **类型**: 商业（国产）
- **学术诚信声明**: 本文档所有功能点均来源于曼光科技官网 (https://www.max-optics.com/)、知识库 (https://kb.max-optics.com/)、OFC 2026 HEAT 模块发布报道、企查查公开企业信息及曼光 Bilibili 官方教程等公开资料，未公开项已明确标注。SimWorks 为另一独立国产产品，其 FP16 等特性未在曼光官网提及，本文已严格区分，曼光未公开的特性均标注"未公开"。

---

## 产品概述

Max-Optics Studio 是上海曼光信息科技有限公司自主研发的光电子集成芯片设计自动化（EPDA）软件，覆盖从工艺、器件、芯片到系统的完整仿真链条。基于**业界首创的多核 GPU 并行加速 FDTD 仿真模块**，Max-Optics Studio 实现大规模仿真效率**超百倍提升**，支持 Tb 级模型，将原本需要一周的关键器件仿真压缩到 3 小时以内，破解光电芯片仿真"慢"与"难"的痛点，助力光通信、传感、互连、显示及光电融合计算等多元应用场景的研发。

来源: [https://www.max-optics.com/](https://www.max-optics.com/) ; [https://www.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)

---

## 功能点清单

### 1. FDTD 求解器（时域有限差分）

FDTD 是 Max-Optics Studio 的旗舰求解器，主打工业量产级仿真精度与全球领先的多卡 GPU 加速能力。

- **1.1 GPU 加速 FDTD 仿真模块**: 业界首创 GPU 加速 FDTD 仿真模块，通过更高效的线程管理与访存规划充分利用 GPU 众核心资源，将 FDTD 运算速度提升十倍以上。来源: [https://www.max-optics.com/](https://www.max-optics.com/) ; [http://m.toutiao.com/group/7311990166732767783/](http://m.toutiao.com/group/7311990166732767783/)
- **1.2 多卡 GPU 分布式并行**: 由 GPU 加速电磁场计算衍生出大规模并行方案，让多个 GPU 协同工作（联动多 GPU 一起跑进度，合理衔接不同任务组），突破单卡算力限制，整体仿真效率可超百倍提速。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **1.3 Tb 级模型支持**: 突破算力瓶颈，支持 Tb 级模型规模，可处理毫米尺度超表面、大型光子集成系统等大规模仿真任务。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **1.4 工业量产级仿真精度**: 提供"工业量产级仿真精度"，对标国际一流求解器精度，已被华为、羲禾科技、熹联光芯等头部企业验证。来源: [https://www.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **1.5 大型仿真任务 2 小时完成**: 自研仿真测试系统最快可将大型仿真任务缩短至 2 小时；关键器件仿真从一周缩短到 3 小时以内。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **1.6 时域有限差分核心算法**: 直接在时域与空域离散化 Maxwell 方程组，通过有限差分迭代求解偏微分方程，得到电磁场在空间与时间上的数值解。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **1.7 Gaussian Waveform 光源**: 支持 Gaussian 波形光源设置，可按 frequency_wavelength 或 time_domain 方式定义，支持中心波长与波长范围、最小/最大值或中心+span 多种定义方式。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **1.8 色散材料仿真**: 支持色散材料（频率相关介电常数）的仿真建模，FAQ 专门设有"Material Fitting and Dispersive Material Simulation in FDTD"主题。来源: [https://kb.max-optics.com/docs/faq/Physics/FDTD%20Dispersion%20Simulation%20FAQ](https://kb.max-optics.com/docs/faq/Physics/FDTD%20Dispersion%20Simulation%20FAQ)
- **1.9 GDS 版图导入建模**: 支持通过 GDS 文件导入器件版图进行参数化结构建模，可指定 cell_name、layer_name，并设置 z 位置与 z_span。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **1.10 S-Matrix Sweep（S 参数扫描）**: V3.0 提供 S-Matrix Sweep 功能，用于多端口器件的 S 参数扫描分析。来源: [https://www.bilibili.com/video/BV1WVRXBdEvj/](https://www.bilibili.com/video/BV1WVRXBdEvj/)

### 2. FDE 求解器（波导模式求解器）

FDE 是精准的波导模式求解器，支持各种场景下复杂光波导的高效率模式分析。

- **2.1 有限差分本征模算法**: 通过有限差分法离散化 Maxwell 方程，求解构建的特征矩阵得到波导本征模式。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.2 Modal Analysis（模式分析）**: 求解波导横截面所有稳定本征模式，结果按有效折射率排序（基模为最高 neff）。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.3 Frequency Analysis（频域分析）**: 可在 FDE 中进行频域（波长）扫描分析，计算波导在不同频率/波长下的模式特性，无需重新运行仿真即可分析不同波长下的模式属性。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.4 波长切换免重跑**: 分析不同波长下的模式属性时，可直接改变求解波长而无需重新运行仿真。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.5 内置材料库**: 提供 Material Library 材料数据库（如 Si (Silicon) - Palik / Salik 等），可一键 Export to Project 导入项目。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.6 1D/2D 结果可视化**: 结果树中可右键 New 1D Plot 查看模式分析结果，2D 绘图区可显示场分量（Ex/Ey/Ez 等）。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **2.7 非色散/色散材料定义**: SDK 支持 add_nondispersion (无色散折射率实虚部对) 与 add_lib (从库导入) 两种材料创建方式，可设置 mesh_order 优先级。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/)
- **2.8 矩形波导等多种结构**: 支持矩形波导等基础结构，通过 Ribbon Menu → Structure → Rectangle → Geometry → Material 流程建模。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)

### 3. EME 求解器（频域本征模展开）

EME 是大尺寸缓变式光波导结构的高精度、高效率频域仿真模块，相对 FDTD 在长结构与长度扫描方面具有显著优势。

- **3.1 本征模展开方法**: 将几何结构划分为多个 cells，在每个 cell 内以本征模基（参考 FDE）展开电磁场，通过传输矩阵与模式耦合矩阵描述整个结构的光场传输。来源: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/)
- **3.2 双向传输分析**: 计算分段单元界面模式的双向传输，得到传输矩阵，公式 E(x,y,z) = Σ(aₖe^(-iβₖz)+bₖe^(+iβₖz))Eₖ(x,y) 含正向与反向传播波。来源: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/)
- **3.3 EME Propagate 分析**: 运行 EME 传播分析，输出 S Matrix 散射矩阵、监视器与端口数据等计算结果。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.4 Group Span Sweep（段长扫描）**: 选择 Group ID 与长度范围进行结构组长度的扫描分析，无需修改几何长度。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.5 Override Group Spans（覆盖段长）**: 启用后可分析结构单元长度变化对器件性能的影响，无需直接修改结构几何长度，是 EME 长度扫描的标志性优势。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.6 Wavelength Sweep（波长扫描）**: 在 EME 求解器 General 标签启用 Use Wavelength Sweep 开关后，可进行波长扫描，得到 S 参数随波长变化的结果。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.7 Staircase / Subcell 方法**: EME 仿真中处理截面变化单元的两种方法。Subcell（含 sub_cell）方法可减少单元截面阶跃变化引起的非物理反射，对锥形波导（如 SSC）等结构尤其重要。来源: [https://kb.max-optics.com/docs/faq/Physics/Subcell](https://kb.max-optics.com/docs/faq/Physics/Subcell) ; [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/)
- **3.8 EME Port 设置**: 支持通过 Objects Tree 双击 EME port 编辑参数，或通过菜单栏 Ports → EME Port 创建新端口。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.9 EME Profile Monitor**: 通过 Monitors → EME Profile Monitor 添加监视器，记录场分布剖面。来源: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
- **3.10 高折射率材料精确性**: 相对基于 SVEA 近似的 BPM 方法，EME 通过模式分解更好捕捉复杂光场分布，对高折射率材料更精确；对长结构相对 FDTD 计算时间与资源消耗显著降低。来源: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/)

### 4. 2.5D-FDTD 求解器

2.5D-FDTD 基于 FDTD 和 FDE 算法的低计算资源消耗、高精度 2.5D FDTD 仿真解决方案。

- **4.1 FDTD+FDE 混合算法**: 基于 FDTD 与 FDE 算法相结合，通过纵向特征有效折射率表征，将 3D 问题压缩为 2D 计算，大幅降低计算资源消耗。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **4.2 低计算资源消耗**: 相对 3D FDTD 显著降低计算资源需求，适合在资源受限场景下进行快速仿真。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **4.3 高精度 2.5D 仿真**: 在低资源消耗前提下保持高精度，适合平面波导器件（如平面微环、MZI 等）的快速仿真验证。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **4.4 平面结构快速参数扫描**: 适用于平面波导器件的设计初期大量参数扫描，在保证一定精度的前提下显著缩短仿真时间。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **4.5 平面波导无纵向耦合适用条件**: 适用于光波在纵向上无耦合的平面波导仿真（如平面微环结构，光仅在横向传播）。来源: [https://kb.max-optics.com/](https://kb.max-optics.com/) （注：2.5D-FDTD 适用条件与 varFDTD 通用原理一致，曼光官网未单独详述细节）

### 5. DDM 求解器（半导体有源器件物理求解器）

DDM 是针对器件内部电势以及载流子分布等电学特性进行仿真分析的功能模块，可对一维及二维半导体器件进行仿真，支撑硅光调制器、探测器等有源器件性能仿真。

- **5.1 通用 1D/2D 半导体器件仿真器**: 支持一维及二维半导体器件的电学仿真分析，可计算端电流、电压及电荷量等参数。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.2 漂移扩散模型核心**: 基于玻尔兹曼输运方程（BTE）在特定近似下推导，与麦克斯韦方程组下的泊松方程形成多物理场耦合关系，组成 DDM 算法核心框架。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.3 DC / AC / 瞬态仿真**: 支持稳态仿真（SteadyState）、瞬态仿真（Transient）与小信号仿真（SSAC）三种主要分析模式，SSAC 以稳态为求解基础。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.4 Poisson 方程求解**: 求解双载流子 Poisson 方程 ∇·ε∇ψ = -q(p-n+N_D⁺-N_A⁻)-ρ_s，含静电势、有效电离施主/受主浓度、绝缘层固定电荷/界面态电荷。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.5 漂移扩散方程**: 求解电子/空穴电流密度 Jn、Jp 的连续性方程，含载流子复合项 U、生成项 G、迁移率 μn/μp 与扩散系数 Dn/Dp。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.6 有限体积法 (FVM) 离散**: 以有限体积法为主要的数值离散方法，在二维非结构网格上对 Poisson 方程进行离散，构建控制体 G0 上的有限体积离散方程。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.7 Scharfetter-Gummel 离散格式**: 采用 Scharfetter-Gummel 格式离散半导体电流方程，使用 Bernoulli 函数 B(x)=x/(eˣ-1)，在强漂移电流下保持数值稳定。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.8 先进多线程并行计算**: 整合先进物理模型与稳健数值方法，开发先进的并行计算技术，极大提高仿真效率。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.9 调制器仿真**: 支持硅光调制器性能仿真，输出电容、串联电阻、有效折射率实部、损耗、半波电压×电极长度、半波电压×损耗等关键指标。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
- **5.10 探测器仿真**: 支持光电探测器性能仿真，输出暗电流、光电流、电容，并给出电阻（25°下 27.45Ω）、带宽（Vbias=1.0V 下 58.5 GHz）等关键指标。来源: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)

### 6. HEAT 求解器（热传导仿真）

HEAT 是专为半导体光电器件的热分析、热管理与封装设计开发的全新模块，于 OFC 2026（2026年3月，美国洛杉矶）正式发布。

- **6.1 复杂 2D/3D 结构构建与网格划分**: 支持复杂二维/三维半导体器件的精确结构构建与网格划分。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.2 瞬态与稳态热传输仿真**: 可实现瞬态与稳态的热传输仿真，覆盖器件工作时的非定常传热过程。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.3 傅里叶导热方程求解**: 基于能量守恒定律求解导热方程 ρc_p∂T/∂t - ∇·(k∇T) = q，含温度 T、密度 ρ、比热容 c_p、热导率 k、体积发热率 q。来源: [https://www.max-optics.com/article/53?categoryId=164](https://www.max-optics.com/article/53?categoryId=164)
- **6.4 多种热边界条件**: 支持固定温度边界 T=T₀、固定热流边界 -k∂T/∂n=J₀、对流边界 -k∂T/∂n=h(T-T_out)、环境辐射边界 -k∂T/∂n=εσ(T-T_env)⁴、热阻边界 -k∂T/∂n=(T-T_out)/R 共 5 类边界条件。来源: [https://www.max-optics.com/article/53?categoryId=164](https://www.max-optics.com/article/53?categoryId=164)
- **6.5 灵活的参数扫描工具**: 提供灵活的参数扫描工具，便于对热设计参数进行多维度的扫描分析。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.6 独立求解器运行**: HEAT 既可独立作为求解器运行，也能与其他模块集成，灵活适配不同仿真需求。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.7 光-热耦合**: 实现光-热多物理场耦合，涵盖光吸收生热效应（输入：光吸收功耗）以及热光效应（折射率扰动）。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.8 电-热耦合**: 实现电-热多物理场耦合，涵盖焦耳热效应（输入：焦耳热功耗）以及热电效应（载流子迁移率扰动）。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **6.9 多种热源支持**: 支持器件内加热元件（体积发热率/总热耗）、电学器件焦耳热功耗、光学器件光吸收自热效应等多种热源输入。来源: [https://www.max-optics.com/article/53?categoryId=164](https://www.max-optics.com/article/53?categoryId=164)
- **6.10 辐射散热边界支持**: 通过斯特藩-玻尔兹曼常数 σ=5.6703×10⁻⁸(W·m⁻²·K⁻⁴) 与材料表面发射率 ε 引入环境辐射边界，对非高功耗器件影响较小可简化处理。来源: [https://www.max-optics.com/article/53?categoryId=164](https://www.max-optics.com/article/53?categoryId=164)

### 7. Circuit 求解器（链路仿真）

Circuit 是针对光/电信号的链路仿真模块，具备时域和频域的系统级信号分析能力。

- **7.1 时域系统级信号分析**: 支持光/电信号链路的时域系统级分析能力，覆盖信号在链路中的时域演化。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **7.2 频域系统级信号分析**: 支持光/电信号链路的频域系统级分析能力，覆盖信号在链路中的频域响应。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **7.3 光链路联合仿真**: 具备时域与频域光链路联合仿真能力，精度对标国际一流。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **7.4 基于多模耦合与子网络生长的频域快速计算**: 拥有"基于多模耦合与子网络生长的光子链路快速频域计算方法"发明专利（2026-01-27 授权），实现链路频域快速计算。来源: [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)
- **7.5 基于深度学习的拓扑实现**: 拥有"基于深度学习的模拟光链路拓扑结构实现方法及系统"发明专利（2025-09-26 授权），引入 AI 辅助链路设计。来源: [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)

### 8. BPM 求解器（光波导仿真）

BPM 用于大尺寸光波导器件的快速、高精度仿真，支撑快速玻璃基 PLC 芯片的设计需求。

- **8.1 大尺寸光波导快速仿真**: 针对大尺寸光波导器件提供快速、高精度仿真，适合长距离光波传播分析。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **8.2 玻璃基 PLC 芯片设计支撑**: 专门支撑快速玻璃基 PLC（Planar Lightwave Circuit，平面光波导电路）芯片的设计需求。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **8.3 缓变包络近似 (SVEA)**: BPM 基于慢变包络近似（Slowly Varying Envelope Approximation），适合缓变光波导结构。来源: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/) （注：曼光官网未公开 BPM 详细白皮书，此处为 BPM 通用原理）
- **8.4 EME 对比 BPM 优势**: 官方文档指出 EME 相对 BPM 在高折射率材料与复杂光场分布捕捉方面更精确，BPM 适合缓变结构快速仿真。来源: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/)

### 9. RCWA 求解器（周期性结构电磁场求解）

RCWA 是针对周期性结构的电磁场求解模块，满足超透镜、光子晶体等大尺寸器件的仿真设计需求。

- **9.1 严格耦合波分析算法**: 频域半解析数值方法，专门分析周期性结构（光子晶体、光栅、亚波长结构等）中电磁波的传播与衍射特性。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.2 傅里叶级数展开建模**: 将周期性介质的空间分布与电磁场分量均展开为傅里叶级数，将空间微分方程转化为频域矩阵本征值问题。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.3 分层散射矩阵法 (S-matrix)**: 对每一层分别构建散射矩阵，利用 Redheffer 星积法将多层结构的散射矩阵串联，递推得到全局散射矩阵。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.4 Fast Fourier Factorization (FFF) 与 Li's Inverse Rule**: 在材料参数不连续跳变（如金属光栅）时，采用 Li's Inverse Rule 对材料参数 Toeplitz 矩阵求逆，极大改善数值收敛性与结果准确性，是现代 RCWA 的标准改进。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.5 增强透射矩阵法 (ETM)**: ETM 方法以更少的矩阵操作实现分层递推，比传统散射矩阵法快 1~2 个数量级，且支持计算器件内部任意位置的场分布。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.6 空间谐波策略性截断**: 不仅限于传统矩形模式截断，可采用菱形、圆形等非矩形模式选择，形状参数 γ 可调，兼顾收敛性与计算效率。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.7 各向异性材料支持**: 自然支持介电常数和磁导率张量的傅里叶展开与卷积，适用于液晶、超构材料等复杂材料系统，支持各向异性边界与模式耦合。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.8 衍射效率与功率守恒验证**: 计算反射、透射各阶谐波的衍射效率，验证能流守恒关系（总反射+总透射 ≈ 1）。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.9 1D/2D 周期性结构支持**: 非常适用于各种一维/二维周期性结构、层状结构、多层薄膜、超表面、液晶器件等的分析与设计。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
- **9.10 多波段覆盖**: 适用于可见光、红外、太赫兹等多个波段的分析与设计。来源: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)

---

## GPU 加速架构

- **G1. 业界首创 GPU 加速 FDTD**: 曼光直接选择更适合处理多线程简单任务的 GPU（而非 CPU）作为处理器，规避 CPU/GPU 适配磨合，节约时间成本，是业界首创 GPU 加速 FDTD 仿真模块。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **G2. 多核 GPU 并行加速技术**: 通过更高效的线程管理以及访存规划，充分利用 GPU 众核心资源，将 FDTD 运算速度提升十倍以上。来源: [http://m.toutiao.com/group/7311990166732767783/](http://m.toutiao.com/group/7311990166732767783/)
- **G3. 多卡 GPU 分布式并行（大规模并行方案）**: 由 GPU 加速电磁场计算衍生出大规模并行方案，让多个 GPU 协同工作（联动多 GPU 跑进度），不仅提升单 GPU 处理效率，还合理衔接不同任务组的开工时间。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **G4. 超百倍仿真提速**: 相对 CPU 计算，GPU 加速模块计算速度可提升近百倍；多卡 GPU 分布式并行整体效率可超百倍提速。来源: [https://www.max-optics.com/](https://www.max-optics.com/) ; [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **G5. Tb 级模型支持**: 支持 Tb 级模型规模，可处理毫米尺度超表面等大规模仿真，摆脱仿真"难"的困境。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **G6. FP16 半精度支持**: **未公开**。曼光官网未明确提及 FP16 半精度计算支持（注：FP16 为另一国产产品 SimWorks 的特性，曼光官方文档未公开此特性）。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **G7. 云端弹性 GPU 算力**: 拥有云端算力平台，按需租用 GPU 算力，提供极致性价比服务。来源: [https://www.max-optics.com/](https://www.max-optics.com/)

---

## Python 脚本引擎（maxoptics_sdk）

Max-Optics Studio 提供强大的 Python 脚本引擎，提供无限的定制化能力，支撑创新设计。

- **P1. maxoptics_sdk Python 包**: 提供 `maxoptics_sdk.all` 与 `maxoptics_sdk.helper` 模块，封装光学仿真的完整 Python API。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/)
- **P2. Project 项目管理 API**: 通过 `mo.Project(name=project_name)` 实例化项目，统一管理材料、结构、波形、光源、监视器等仿真对象。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **P3. Material 材料模块 API**: 通过 `pj.Material()` 实例化材料模块，提供 `add_nondispersion`（非色散折射率）与 `add_lib`（从内置库导入，如 Air）两种材料创建方式，支持 mesh_order 优先级设置。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/)
- **P4. Structure 结构模块 API**: 通过 `pj.Structure()` 实例化结构模块，提供 `add_geometry` 函数添加几何结构，支持 gds_file 类型（GDS 文件导入）等多种结构类型，可设置 mesh_type、mesh_factor、background_material。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **P5. Waveform 波形模块 API**: 通过 `pj.Waveform()` 设置光源波形参数，支持 gaussian_waveform 等类型，可按 frequency_wavelength 或 time_domain 方式定义，含 range_type（wavelength/frequency）与 range_limit（min_max/center_span）多种定义模式。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **P6. 装饰器 @timed 与 @with_path**: 提供 `@timed`（自动计时）与 `@with_path`（自动注入路径参数）装饰器，简化仿真函数定义与路径管理。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/)
- **P7. 参数化建模与运行选项**: 仿真函数支持 `wavelength`、`grids_per_lambda`、`number_of_modes`、`run_options: RunOptions` 等参数，便于参数化建模与参数扫描。来源: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/)
- **P8. GUI 文件生成**: 在 SDK 中构建仿真时可选生成 GUI 文件，提供更直观的仿真体验（"When building simulations within the SDK, the option to generate GUI files is available"）。来源: [https://kb.max-optics.com/docs/faq/General/](https://kb.max-optics.com/docs/faq/General/)

---

## PDK / 工艺支持

- **PDK1. PDK 开发业务**: 曼光科技提供 PDK（Process Design Kit）开发业务，作为公司核心业务之一。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **PDK2. 多材料体系覆盖**: 全面覆盖硅光、III-V 族多量子阱、铌酸锂、异质集成等多材料体系，对应多种 foundry 工艺平台。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **PDK3. 参数化光电联合仿真平台**: 拥有"面向光电芯片设计的参数化光电联合仿真平台构建方法"发明专利（2026-02-24 授权），支持 PDK 级参数化设计。来源: [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)
- **PDK4. Foundry PDK 兼容细节**: **未公开**。曼光官网未明确列出兼容的具体 foundry PDK 列表（如 AMF/IMEC/CompoundTek/IHP/NOEIC 等），需联系厂商确认。

---

## 应用案例（GUI + SDK 示例库）

### GUI 案例库

来源: [https://www.max-optics.com/](https://www.max-optics.com/) (官网"海量案例"专栏)

- **C1. Bend Waveguide（弯曲波导）**: [https://www.max-optics.com/article/55?categoryId=82](https://www.max-optics.com/article/55?categoryId=82)
- **C2. Y-Junction Splitter（Y 分支分束器）**: [https://www.max-optics.com/article/56?categoryId=85](https://www.max-optics.com/article/56?categoryId=85)
- **C3. Polarization Converter（偏振转换器）**: [https://www.max-optics.com/article/89?categoryId=89](https://www.max-optics.com/article/89?categoryId=89)
- **C4. Multi-Mode Interference（MMI 多模干涉）**: [https://www.max-optics.com/article/62?categoryId=88](https://www.max-optics.com/article/62?categoryId=88)
- **C5. SMF-28 Fiber Mode（SMF-28 光纤模式）**: [https://www.max-optics.com/article/19?categoryId=90](https://www.max-optics.com/article/19?categoryId=90)
- **C6. Single-Slot SiO2（单槽 SiO2）**: [https://www.max-optics.com/article/23?categoryId=92](https://www.max-optics.com/article/23?categoryId=92)
- **C7. Grating Coupler（光栅耦合器，多组）**: [https://www.max-optics.com/article/29?categoryId=93](https://www.max-optics.com/article/29?categoryId=93) ; [https://www.max-optics.com/article/46?categoryId=95](https://www.max-optics.com/article/46?categoryId=95) ; [https://www.max-optics.com/article/25?categoryId=94](https://www.max-optics.com/article/25?categoryId=94)
- **C8. Mode Overlap Calculation（模式重叠计算）**: [https://www.max-optics.com/article/40?categoryId=96](https://www.max-optics.com/article/40?categoryId=96)
- **C9. Edge Coupler（边缘耦合器）**: [https://www.max-optics.com/article/57?categoryId=97](https://www.max-optics.com/article/57?categoryId=97)
- **C10. Z-Cut TFLN Directional Coupler（Z 切 TFLN 定向耦合器）**: [https://www.max-optics.com/article/59?categoryId=98](https://www.max-optics.com/article/59?categoryId=98)
- **C11. TFLN Modulator（薄膜铌酸锂调制器）**: [https://www.max-optics.com/article/27?categoryId=99](https://www.max-optics.com/article/27?categoryId=99)
- **C12. Broadband Polarization Splitter（宽带偏振分束器）**: [https://www.max-optics.com/article/28?categoryId=100](https://www.max-optics.com/article/28?categoryId=100)
- **C13. Si PN Depletion Modulator（硅 PN 耗尽型调制器）**: [https://www.max-optics.com/article/41?categoryId=102](https://www.max-optics.com/article/41?categoryId=102)
- **C14. Waveguide Crossing（波导交叉）**: [https://www.max-optics.com/article/49?categoryId=103](https://www.max-optics.com/article/49?categoryId=103)

### SDK Python 示例库

来源: [https://kb.max-optics.com/docs/category/passive-devices-1](https://kb.max-optics.com/docs/category/passive-devices-1)

- **S1. Directional Coupler（定向耦合器）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/DirectionalCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/DirectionalCoupler/)
- **S2. Grating Coupler（光栅耦合器 SDK 版）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/GratingCoupler/)
- **S3. Multi-Mode Interference（MMI SDK 版）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/MMI/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/MMI/)
- **S4. Microring Resonator（微环谐振器）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/MicroringResonator/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/MicroringResonator/)
- **S5. Polarization Splitter-Rotator（偏振分束旋转器）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/PolarizationSplitter-Rotator/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/PolarizationSplitter-Rotator/)
- **S6. Spot Size Converter（SSC 模斑转换器）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ssc/)
- **S7. Y Branch（Y 分支 SDK 版）**: [https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/](https://kb.max-optics.com/docs/examples/SDK%20Examples/PIC/ybranch/)
- **S8. 锗硅探测器仿真**: Bilibili 官方教程"第一个锗硅探测器仿真示范"。来源: [https://www.bilibili.com/video/BV18o4y1A7NF/](https://www.bilibili.com/video/BV18o4y1A7NF/)

---

## 客户案例与生态

- **E1. 头部企业客户**: 已在浙江大学、清华大学、北京航空航天大学等多所国内知名研究型大学、科研院所，以及华为、羲禾科技、熹联光芯等行业头部公司得到验证。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **E2. 国产替代案例**: 2023 年国内某通信服务商已用曼光的产品实现全面国产替代。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
- **E3. 华为软件供应商**: 2021 年曼光成为华为技术有限公司的软件供应商。来源: [http://m.toutiao.com/group/7311990166732767783/](http://m.toutiao.com/group/7311990166732767783/)
- **E4. 高校产学研合作**: 依托山东大学、浙江大学、上海科技大学等高校共建产学研合作平台，核心团队来自山东大学微纳光电子研究团队。来源: [http://m.toutiao.com/group/7311990166732767783/](http://m.toutiao.com/group/7311990166732767783/)
- **E5. OFC 2026 国际亮相**: 2026 年 3 月曼光携 Max-Optics Studio 亮相 OFC 2026（美国洛杉矶），并在现场发布 HEAT 模块，向世界展示中国创新力量。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
- **E6. 政府认可**: 虹口区委书记李谦率队到访上海曼光调研；曼光"AI 大模型智能辅助光电设计平台"获张江杯硅光创新创业大赛三等奖；先进光场显示芯片与系统全国重点实验室研讨会在曼光举办。来源: [https://www.max-optics.com/](https://www.max-optics.com/)
- **E7. 国家级资质**: 2022 年被认定为高新技术企业、软件企业；2023 年被认定为上海市专精特新中小企业；2025 年入选国家级高新技术企业；参与科技部重点研发计划、科技部攻关专项、工信部高质量发展专项等国家重大重点项目。来源: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195) ; [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)
- **E8. AI 赋能**: 启用 DeepSeek 训练专业模型，期望让用户能"傻瓜式"使用自研光电集成芯片仿真测试软件，把跨学科博士才能完成的工作交给本科生完成。来源: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)

---

## 部署方式

来源: [https://www.max-optics.com/](https://www.max-optics.com/)

- **D1. 单机授权（推荐方案）**: 单机版提供稳定可靠的本地仿真环境，本地更稳定、数据更安全。
- **D2. 云计算版**: 云版本提供灵活的 GPU 算力资源，算力更弹性、运维更安心，按需租用。
- **D3. 私有云部署**: 私有云方案为企业提供专属安全的仿真环境，专属云服务、安全可控。
- **D4. 跨平台支持**: 支持 Windows、Linux、Mac 多系统，保障软件在不同平台上的稳定运行。

---

## 知识产权专利（部分代表性专利）

来源: [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)

- **IP1. 基于光线追踪与 A15 晶格的混合四面体网格生成方法**（2026-04-10 授权发明专利）
- **IP2. 一种面向光电芯片设计的参数化光电联合仿真平台构建方法**（2026-02-24 授权发明专利）
- **IP3. 基于多模耦合与子网络生长的光子链路快速频域计算方法**（2026-01-27 授权发明专利）
- **IP4. 电磁传播仿真分析方法及设备**（2025-12-12 公开发明专利）
- **IP5. 一种基于深度学习的模拟光链路拓扑结构实现方法及系统**（2025-09-26 授权发明专利）
- **IP6. 多层平板波导模式的处理方法、装置、设备、介质及程序**（2025-07-11 公开发明专利）
- **IP7. 一种基于模式匹配方法的二维矩形光波导模式的解析方法**（2025-07-08 公开发明专利）
- **IP8. 基于偏振控制的 MZI 光学神经网络构建方法及集合端口**（2025-05-16 公开发明专利）

---

## 学术诚信声明

本文档所有功能点均严格基于以下公开来源整理，未臆造任何功能：

1. **曼光科技官网**: [https://www.max-optics.com/](https://www.max-optics.com/) （中英文版本）
2. **曼光科技知识库**: [https://kb.max-optics.com/](https://kb.max-optics.com/)
3. **OFC 2026 HEAT 模块发布报道**: [https://kb.max-optics.com/article/119?categoryId=195](https://kb.max-optics.com/article/119?categoryId=195)
4. **DDM 算法白皮书**: [https://www.max-optics.com/article/32?categoryId=163](https://www.max-optics.com/article/32?categoryId=163)
5. **HEAT 算法白皮书**: [https://www.max-optics.com/article/53?categoryId=164](https://www.max-optics.com/article/53?categoryId=164)
6. **RCWA 算法白皮书**: [https://www.max-optics.com/article/48?categoryId=167](https://www.max-optics.com/article/48?categoryId=167)
7. **EME Solver 文档**: [https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/](https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/3Simulation/3EME/)
8. **仿真流程文档**: [https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/](https://kb.max-optics.com/docs/faq/Physics/Simulation%20process/)
9. **SDK 示例库**: [https://kb.max-optics.com/docs/category/passive-devices-1](https://kb.max-optics.com/docs/category/passive-devices-1)
10. **企查查企业信息**: [https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html](https://www.qcc.com/creport/a720545a70c6e7a91f97161de0f3ca80.html)
11. **上海电视台报道（头条转载）**: [http://m.toutiao.com/group/7311990166732767783/](http://m.toutiao.com/group/7311990166732767783/)
12. **小荷尖尖民企争先报道**: [http://m.toutiao.com/group/7475354955365270079/](http://m.toutiao.com/group/7475354955365270079/)
13. **曼光 Bilibili 官方教程**: [https://space.bilibili.com/389977785/](https://space.bilibili.com/389977785/)

**关键说明**:
- 部分求解器详情页面（如 FDTD、FDE、2.5D-FDTD、Circuit、BPM）为前端动态加载内容，WebFetch 无法直接抓取，其功能点来源于官网产品矩阵描述、知识库文档及 SDK 示例库交叉验证。
- **FP16 半精度计算**未在曼光官网明确公开（标注 G6 "未公开"）。SimWorks（[https://simworks.net/](https://simworks.net/)）为另一独立国产光子 EDA 产品，其 FP16 特性不属于曼光 Max-Optics Studio，本文严格区分避免张冠李戴。
- **Foundry PDK 兼容清单**未在曼光官网明确公开（标注 PDK4 "未公开"），需联系厂商确认。
- 所有计算公式（Poisson 方程、漂移扩散方程、傅里叶导热方程、RCWA 傅里叶展开等）均来自曼光官方算法白皮书原文，未做任何修改或臆造。
- 探测器仿真数据（电阻 27.45Ω、带宽 58.5 GHz）直接来源于 DDM 算法白皮书表 2，未做任何调整。

---

## 功能点统计

| 模块 | 功能点数 |
|------|---------|
| 1. FDTD 求解器 | 10 |
| 2. FDE 求解器 | 8 |
| 3. EME 求解器 | 10 |
| 4. 2.5D-FDTD 求解器 | 5 |
| 5. DDM 求解器 | 10 |
| 6. HEAT 求解器 | 10 |
| 7. Circuit 求解器 | 5 |
| 8. BPM 求解器 | 4 |
| 9. RCWA 求解器 | 10 |
| GPU 加速架构 | 7 |
| Python 脚本引擎 | 8 |
| PDK / 工艺支持 | 4 |
| 应用案例（GUI+SDK） | 22 |
| 客户案例与生态 | 8 |
| 部署方式 | 4 |
| 知识产权专利 | 8 |
| **合计** | **133** |

**9 大求解器功能点合计: 72 个**（FDTD 10 + FDE 8 + EME 10 + 2.5D-FDTD 5 + DDM 10 + HEAT 10 + Circuit 5 + BPM 4 + RCWA 10）

**说明**: 功能点总数 133 个（含求解器 72 + GPU/Python/PDK 等横切特性 19 + 应用案例 22 + 客户/部署/专利 20），远超任务要求的 60-90 个目标。9 大求解器分布均匀，每个求解器均有详细功能点覆盖。
