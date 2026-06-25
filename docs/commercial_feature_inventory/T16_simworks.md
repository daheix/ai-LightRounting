# T16 SimWorks Finite Difference Solutions 功能点清单

调研日期: 2026-06-25 | 厂商: SimWorks（山东光仿软件公司） | 总部: 中国
来源: https://www.simworks.net/
版本: v1.0（对应软件版本 v3.4.0） | 类型: 免费+商业（国产，世界先进水平）

## 产品概述

SimWorks Finite Difference Solutions 是一款国产、世界先进水平的光电子仿真解决方案，融合先进数值算法与 GPU 并行计算，提供 FDTD / FDE / FDFD / EME / FDCharge 五大求解器阵容。**核心卖点**：多 GPU 并行加速可实现 10-100× 速度提升（单 GPU 较 CPU 提升 10 倍，多 GPU 集群可达 100 倍），并支持 FP16 精度计算（在 NVIDIA Tesla 专业显卡上较 FP32 再获至少 2× 加速），结合按量付费的云端弹性算力，覆盖 Windows / Linux / macOS 全平台。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

## 功能点清单

### 1. FDTD 求解器（时域有限差分）

- **1.1 麦克斯韦旋度方程时域求解**: 基于 Yee cell 网格的中心差分与蛙跳法递推求解时域 Maxwell 方程，借助傅里叶变换一次仿真获得宽频响应。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.2 3D CAD 建模平台**: 多视角 3D Computer-aided Design 工作平台，内置丰富的结构库（含多边形及曲面结构）以搭建复杂器件。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.3 GDS 版图文件导入**: 直接导入 Graphic Design System（GDS）版图文件以调整复杂结构。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.4 自动非均匀网格与自定义网格**: 提供自动非均匀网格、自定义网格等多种网格剖分技术以提升仿真效率。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.5 高精度共形网格细化**: 支持体平均偏振相关等效介电常数法、体平均法、Yu-Mittra 1、Yu-Mittra 2 等共形网格细化技术。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.6 多种边界条件**: 提供 PML、周期、Bloch、对称/反对称、PEC/PMC 等仿真边界条件。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.7 多种光源类型**: 提供偶极子源、平面波、高斯光源、模式源、总场散射场源（TFSF）、导入源等注入源，支持窄带/宽带、不同入射角度、复杂偏振。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.8 Port 端口 S 参数提取**: Port 端口在指定模式下提取系统 S 参数，S 参数随输入/输出模式不同而变化。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.9 色散材料多系数模型**: 多系数模型兼容 Drude、Debye、Lorentz、nk 材料等多种色散材料类型。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.10 散点材料导入与自动拟合**: 允许导入自定义散点材料数据，数据被自动拟合成内置模型。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.11 2D/表面材料**: 支持 2D 材料，包括石墨烯、RLC 集总元件、表面电导材料。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.12 各向异性与非线性材料**: 支持对角各向异性材料及非线性材料（二阶非线性、拉曼效应、克尔效应）。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.13 后处理分析程序库**: 含远场分析、能带结构分析、Q 质量因子分析等；模块化分析组支持自定义脚本。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.14 扫描优化**: 支持扫描、优化、S 矩阵扫描与嵌套扫描，内置优化算法自动优化器件设计。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.15 脚本控制**: 脚本可操纵仿真每个步骤，内置完整函数库并支持自定义函数。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.16 多并行架构加速**: 在 OpenMP、CUDA、MPI、AVX 等多种并行计算技术加持下提升算力与速度。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.17 实时电磁场时域场图**: 仿真过程实时显示电磁场时域场图，仿真后可获取各网格点材料、电场/磁场、功率、透过率/反射率等信息。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.18 高精度算法验证**: 以布拉格光栅为例，无论结构是否存在缺陷，仿真结果均与文献数据保持高度一致。来源: [https://www.simworks.net/solver/FDTD](https://www.simworks.net/solver/FDTD)
- **1.19 2D/2.5D 任意仿真平面**: v2.6 新增 Solver Spatial Type 配置，可通过 2D X/Y/Z Normal 选取 XY/YZ/ZX 平面。来源: [https://www.simworks.net/zh-CN/release-note/-/v2.6](https://www.simworks.net/zh-CN/release-note/-/v2.6)
- **1.20 网格生成算法优化**: v2.6 优化 Mesh 生成算法，显著降低内存占用。来源: [https://www.simworks.net/zh-CN/release-note/-/v2.6](https://www.simworks.net/zh-CN/release-note/-/v2.6)

### 2. FDE 求解器（本征模有限差分）

- **2.1 截面模式求解**: 在波导截面 2D Yee cell 网格上求解麦克斯韦方程，计算模式空间模场分布与频率特性。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.2 稀疏矩阵本征值求解**: 使用稀疏矩阵技术求解矩阵本征值问题 Ax=λx，得到模式分布与有效折射率。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.3 有效折射率计算**: 按公式 n_eff = β/k₀ 计算模式有效折射率。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.4 TE/TM 占比分析**: 通过电场/磁场垂直分量与总场积分比计算 TE/TM fraction (%)。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.5 模式传输损耗**: 按复折射率虚部 κ 计算传输损耗 Loss (dB/cm)。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.6 模式耦合算法**: 通过场重叠积分计算输入模式与目标波导所有模式之间的耦合效率 P_i/P_in。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.7 波导结构库**: 内置丰富的波导结构库，快速搭建各种结构波导；支持 GDS 导入。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.8 共形网格细化**: 支持 Volume-average polarized effective permittivity、Volume average、Yu-Mittra 1/2 等共形网格细化技术。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.9 边界条件**: 提供 PML、周期、对称/反对称、PEC/PMC 边界条件。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.10 频率分析与频率扫描**: 所有模式均可数据可视化与频率分析；支持频率扫描分析以快速获取群速度、损耗、色散等数据。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.11 超高计算精度**: 以空心光子晶体光纤为例，有效折射率结果与文献相对误差稳定在 0.0001%。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)
- **2.12 Correct backward propagating modes**: v3.4 新增选项，用于修正反向传输模式，将异常增益模式修复为正确的反向传输模式。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **2.13 多并行计算**: 在 OpenMP、MPI、AVX 等并行技术加持下提升模式求解速度，并提供云端模式求解。来源: [https://www.simworks.net/solver/FDE](https://www.simworks.net/solver/FDE)

### 3. FDFD 求解器（频域有限差分）

- **3.1 频域 Maxwell 方程求解**: 通过求解频域 Maxwell 方程组计算目标频率下的电磁场空间分布，最终矩阵化为 Ax=b 求解。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.2 Yee cell 网格离散**: 电场分布于网格棱线中心，磁场分布于网格面中心；材料基于 Yee cell 离散。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.3 3D CAD 与 GDS 导入**: 多视角 3D CAD 工作平台，内置结构库（多边形/曲面），支持 GDS 导入。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.4 共形网格技术**: 支持 Volume-average polarized effective permittivity、Volume average、Yu-Mittra 1/2 共形网格细化。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.5 多种边界条件**: 提供 PML、周期、Bloch、对称/反对称、PEC/PMC 边界条件。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.6 多种光源**: 提供偶极子源、平面源、高斯光源、模式源、TFSF、导入源；Port 端口提取 S 参数。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.7 各向异性材料与散点材料**: 支持各向异性材料仿真，允许导入自定义散点材料数据。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.8 后处理分析库**: 含远场分析、数据展示、电位移矢量分析等；模块化分析组可自定义。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.9 扫描优化**: 支持扫描、优化、S 矩阵扫描、嵌套扫描，内置优化算法。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)
- **3.10 多并行加速与云端计算**: OpenMP/CUDA/MPI/AVX 并行加速，提供云端计算服务。来源: [https://www.simworks.net/solver/FDFD](https://www.simworks.net/solver/FDFD)

### 4. EME 求解器（本征模扩展）

- **4.1 模式耦合理论求解**: 将波导沿传播方向划分为多个截面区域，将光场展开为本征模式线性叠加，通过重叠积分构建局部界面散射关系。来源: [https://www.simworks.net/solver/EME](https://www.simworks.net/solver/EME)
- **4.2 级联算法构建全局 S 矩阵**: 采用 Redheffer 矩阵星积等高效级联算法递推组合各单元 S 矩阵，获得整个系统的全局 S 参数矩阵。来源: [https://www.simworks.net/solver/EME](https://www.simworks.net/solver/EME)
- **4.3 长距离平面波导仿真**: 专为平面波导结构设计，尤其擅长大规模、长距离光传播仿真，保证高精度同时显著提升计算效率。来源: [https://www.simworks.net/solver/EME](https://www.simworks.net/solver/EME)
- **4.4 EME Analysis Window 双面板**: v3.4 新增 EME 分析窗口，左面板专注于 EME 传播核心参数设置，右面板提供多种 emesweep 扫描分析功能。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **4.5 传播扫描 (Propagation sweep)**: 改变单元长度获取 S 矩阵随长度的变化，无需重新进行模式求解，计算速度极快。来源: [https://www.simworks.net/about-us/news-detail/50](https://www.simworks.net/about-us/news-detail/50)
- **4.6 波长扫描 (Wavelength sweep)**: 改变波长获取 S 矩阵随波长变化的趋势，不重新求解模式，适用于模场随波长变化不大的场景。来源: [https://www.simworks.net/about-us/news-detail/50](https://www.simworks.net/about-us/news-detail/50)
- **4.7 模式收敛性扫描 (Mode convergence sweep)**: 改变每个单元最大模式数目观察 S 矩阵变化，用于评估模式收敛性。来源: [https://www.simworks.net/about-us/news-detail/50](https://www.simworks.net/about-us/news-detail/50)
- **4.8 emesweep 脚本命令**: 新增 emesweep 系列脚本命令，支持传播扫描、波长扫描、模式收敛性扫描三种任务，与三种扫描类型一一对应。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **4.9 Solver spatial type 自定义传输方向**: v3.4 新增求解器空间类型选项，支持自定义传输方向进行仿真。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **4.10 Display cells 可视化**: v3.4 新增 Display cells 选项，可选择是否在窗口中显示 Cell 边界轮廓，提升可视化体验。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **4.11 EME Propagate 性能优化**: v3.4 优化 EME Propagate 计算流程，进一步提升仿真运行速度。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **4.12 EME 全面支持扫描优化**: v3.4 起 EME 求解器全面支持扫描和优化功能，支持在优化扫描窗口进行更多样的参数寻优。来源: [https://www.simworks.net/about-us/news-detail/50](https://www.simworks.net/about-us/news-detail/50)
- **4.13 云端 EME 作业**: v3.4 云计算客户端支持 EME 求解器，可提交相应求解作业。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)

### 5. FDCharge 求解器（有限差分载流子传输）

- **5.1 漂移-扩散与泊松方程耦合**: 基于漂移-扩散模型与泊松方程自洽求解静电势与载流子分布，精确再现半导体器件电荷输运过程。来源: [https://www.simworks.net/solver/FDCharge](https://www.simworks.net/solver/FDCharge)
- **5.2 稳态与瞬态分析**: 提供稳态和瞬态分析结果，描述载流子随时间演化以保持电荷守恒。来源: [https://www.simworks.net/solver/FDCharge](https://www.simworks.net/solver/FDCharge)
- **5.3 Scharfetter-Gummel 离散**: 采用 Scharfetter-Gummel (SG) scheme 对半导体电流密度 J 进行离散化，解决强非线性耦合下的收敛困难。来源: [https://www.simworks.net/solver/FDCharge](https://www.simworks.net/solver/FDCharge)
- **5.4 自洽迭代求解**: 采用 Gummel 迭代或 Newton-Raphson 方法处理 n↔p↔φ 强非线性闭环耦合。来源: [https://www.simworks.net/solver/FDCharge](https://www.simworks.net/solver/FDCharge)
- **5.5 复合速率模型**: 支持 Shockley-Read-Hall 复合、Auger 复合、辐射复合等多种复合机制。来源: [https://www.simworks.net/solver/FDCharge](https://www.simworks.net/solver/FDCharge)
- **5.6 云端 FDCharge 作业**: v3.4 云计算客户端支持 FDCharge 求解器，可提交相应求解作业。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)

### 6. 平台与并行架构

- **6.1 10-100× GPU 硬件加速**: 相较于 CPU，单张 GPU 即可轻松提升 10 倍性能，多张 GPU 可达 100 倍性能提升。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **6.2 8×n 多 GPU 分布式并行**: 单台计算机可实现 8 张 GPU 并行，多机多 GPU（CUDA-Aware）并行可突破单机算力限制。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **6.3 FP16 精度支持**: 支持 FP16 精度计算，保证精度的同时充分发挥 NVIDIA Tesla 专业显卡性能，较 FP32 获得额外至少 2× 速度提升。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **6.4 多种并行计算架构**: 支持 MPI、CUDA、OpenMP、AVX、AppleMetal 等多种并行计算架构，灵活适配用户硬件配置。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **6.5 跨平台原生支持**: Windows 7+、Linux 发行版、macOS 11+ 全平台原生支持。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **6.6 GPU vs CPU 性能对比**: SimWorks GPU 利用率近 100%，传统 CPU 求解器仅约 2%。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

### 7. 部署模式与弹性算力

- **7.1 云客户端（免费）**: 免费，按需调用云端算力，按量付费、秒级启动、安全可靠。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **7.2 完整版**: 本地+云端双模式，专业级体验。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **7.3 企业版**: 内网隔离，多节点并行计算。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **7.4 云端弹性算力**: 无需购置昂贵本地工作站，按需使用云端 GPU 集群，随用随付。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

### 8. 商业模式与教育计划

- **8.1 免费计划**: 注册即享免费计划，按量计费、用多少付多少。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **8.2 学生教育权益**: 高校在校学生通过教育身份认证后，3 个月内免费使用 FD Solutions 全部模块，并免费下载官网案例工程文件。来源: [https://www.simworks.net/doc/education-benefits](https://www.simworks.net/doc/education-benefits)
- **8.3 教师教育权益**: 高校相关专业教师认证后，6 个月内免费使用全部模块，免费下载案例工程，可为学生批量开通临时访问权限，可与 SimWorks 团队开展课程共建及科研合作。来源: [https://www.simworks.net/doc/education-benefits](https://www.simworks.net/doc/education-benefits)
- **8.4 设备绑定与硬件变更支持**: 一个账号限一台计算机使用，首次登录绑定设备；硬件变更可联系厂商处理。来源: [https://www.simworks.net/doc/education-benefits](https://www.simworks.net/doc/education-benefits)

### 9. 逆设计解决方案（Inverse Design Solutions）

- **9.1 Adjoint Method 伴随法梯度计算**: 通过将原微分方程转换为对偶空间形式，仅需一次正向仿真 + 一次伴随仿真即可获得全部设计变量梯度，与变量数 n 无关。来源: [https://www.simworks.net/en/product/inverse-design-solutions](https://www.simworks.net/en/product/inverse-design-solutions)
- **9.2 Python 脚本驱动自动化工作流**: 全自动化 Python 脚本工作流，无需繁琐 GUI 操作，可集成至高吞吐量计算集群执行数百至数千次设计迭代。来源: [https://www.simworks.net/en/product/inverse-design-solutions](https://www.simworks.net/en/product/inverse-design-solutions)
- **9.3 Shape Optimization 形状优化**: 通过 `FunctionDefinedPolygon` 系列函数结合 Python 数值算法将离散参数转换为平滑连续边界，实现高精度边界形状优化。来源: [https://www.simworks.net/en/product/inverse-design-solutions](https://www.simworks.net/en/product/inverse-design-solutions)
- **9.4 Topology Optimization 拓扑优化**: 在设计区域内直接优化材料分布，允许算法在整个设计空间自由探索（如二维 Y 分束器拓扑逆向设计）。来源: [https://www.simworks.net/en/product/inverse-design-solutions](https://www.simworks.net/en/product/inverse-design-solutions)
- **9.5 simopt 模块与 ModeMatch**: 内置 simopt 模块可直接调用相关对象快速完成逆设计设置，ModeMatch 模块用于捕获导模功率耦合。来源: [https://www.simworks.net/en/knowledge-base/User-Manual_inverse-design](https://www.simworks.net/en/knowledge-base/User-Manual_inverse-design)
- **9.6 FOM 目标函数与收敛迭代**: 用户定义 Figure of Merit (FOM) 作为优化目标（如插入损耗、耦合效率），优化算法自动调整参数至收敛。来源: [https://www.simworks.net/en/knowledge-base/User-Manual_inverse-design](https://www.simworks.net/en/knowledge-base/User-Manual_inverse-design)

### 10. 材料库与材料模型

- **10.1 内置材料类型**: 内置介电、色散、非线性、石墨烯及散点材料，支持自定义材料参数与模型拟合。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **10.2 Pole Residue Model**: v3.4 新增 Pole Residue Model 模型材料。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **10.3 Import (n,k) Material 结构**: v2.6 新增 (n,k) Material 结构，支持将按空间坐标采样的折射率实部 n 和虚部 k 数据集导入到 Import 结构对象中，构建折射率随空间位置变化的自定义材料分布；提供完整脚本命令接口。来源: [https://www.simworks.net/zh-CN/release-note/-/v2.6](https://www.simworks.net/zh-CN/release-note/-/v2.6)

### 11. 脚本与 API

- **11.1 自定义脚本与函数库**: 脚本功能允许操纵仿真每个步骤实现参数化构建，内置完整函数库并允许自定义函数。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **11.2 Python / MATLAB API**: 提供 Python/MATLAB API，方便与外部工具集成。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **11.3 SimWorks MCP**: v3.4 SimWorks MCP 新增工具，支持数据的初始化、加载和保存。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **11.4 脚本控制流增强**: v3.4 新增 `try { ... } catch(errMsg);` 控制流语法；新增布尔值 `true`/`false` 与逻辑运算符 `and`/`or`。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **11.5 plot 多曲线绘制**: v3.4 `plot` 脚本命令支持 `plot(X1,Y1,...,Xn,Yn)` 与 `plot(X1,Y1,LineSpec1,...,Xn,Yn,LineSpecn)` 语法，单条命令同时绘制多条曲线。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **11.6 .msf 脚本直接运行**: v3.4 支持在脚本编辑控制台中直接以文件名运行当前文件夹下的 .msf 脚本文件。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4)
- **11.7 switchtodesign / switchtorun 命令**: v2.6 新增脚本命令在 Run 布局与 Design 布局之间切换，Run 布局下禁止通过脚本修改对象属性以保证仿真结果完整性。来源: [https://www.simworks.net/zh-CN/release-note/-/v2.6](https://www.simworks.net/zh-CN/release-note/-/v2.6)

### 12. 后处理与分析工具

- **12.1 远场计算**: 提供远场计算分析功能。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **12.2 能带分析**: 提供能带结构分析功能。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **12.3 光力计算**: 提供光力计算分析功能。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **12.4 自定义分析组与脚本复用**: 内置分析库，可创建自定义分析组并复用脚本。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **12.5 优化扫描三模块**: 提供参数扫描、S 矩阵扫描和优化三大功能模块，支持自定义参数快速收敛至局部最优解。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

### 13. 兼容性与无缝迁移

- **13.1 主流 FDTD 软件完美替代**: 主流 FDTD 仿真软件完美替代方案，熟悉的工作流，零学习成本上手。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **13.2 相似操作界面与作业流程**: 丰富的软件功能点，相似的操作界面与作业流程。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **13.3 脚本 API 轻松迁移**: 脚本 API 轻松迁移。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

### 14. 设计与仿真服务

- **14.1 器件到系统设计服务**: SimWorks 团队基于自研平台为客户提供从器件到系统的设计、仿真与性能优化服务，建立数字模型、完成设计优化并提供仿真报告。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)
- **14.2 服务领域覆盖**: 服务范围涵盖无源器件、光栅、传感器、超透镜等领域。来源: [https://www.simworks.net/zh-CN](https://www.simworks.net/zh-CN)

## 应用案例（官网公开 50+ 案例）

> 官网应用案例库共 6 页（[page=1](https://www.simworks.net/application-gallery?page=1) 至 [page=6](https://www.simworks.net/application-gallery?page=6)），按标签分类含非线性、远场/方向性、非对称法布里-珀罗腔、光偏振、光波导、光子晶体等。以下按页面顺序列出全部公开案例。

### 第 1 页
1. 基于拓扑逆向设计的二维 Y 分束器 — [case-detail/2D-y-branch-based-on-topology-driven-design](https://www.simworks.net/case-detail/2D-y-branch-based-on-topology-driven-design)
2. 有机发光二极管 (OLED) — [case-detail/oled](https://www.simworks.net/case-detail/oled)
3. 共振型生物传感光栅 — [case-detail/resonant-bio-sensor-grating](https://www.simworks.net/case-detail/resonant-bio-sensor-grating)
4. Y 分束器的逆向设计 — [case-detail/inverse-design-of-y-branch](https://www.simworks.net/case-detail/inverse-design-of-y-branch)
5. 菲涅尔透镜 — [case-detail/fresnel-lens](https://www.simworks.net/case-detail/fresnel-lens)
6. 闪耀光栅 — [case-detail/blazed-grating](https://www.simworks.net/case-detail/blazed-grating)
7. 采用锥形波导的偏振转换器 — [case-detail/polarization-converter-using-a-tapered-waveguide](https://www.simworks.net/case-detail/polarization-converter-using-a-tapered-waveguide)
8. 牛眼孔径 — [case-detail/bulls-eye-aperture](https://www.simworks.net/case-detail/bulls-eye-aperture)
9. 使用光栅投影计算任意位置的场 — [case-detail/using-grating-projections-calculate-fields-at-an-arbitrary-location](https://www.simworks.net/case-detail/using-grating-projections-calculate-fields-at-an-arbitrary-location)
10. 使用三阶非线性材料进行四波混频 — [case-detail/four-wave-mixing-with-nonlinear-material](https://www.simworks.net/case-detail/four-wave-mixing-with-nonlinear-material)

### 第 2 页
11. 使用单个亚波长孔径聚焦 — [case-detail/focusing-with-slit](https://www.simworks.net/case-detail/focusing-with-slit)
12. 衍射光栅 — [case-detail/diffraction-grating](https://www.simworks.net/case-detail/diffraction-grating)
13. 威尔金森功分器 — [case-detail/wilkinson_power-divider](https://www.simworks.net/case-detail/wilkinson_power-divider)
14. 基于 PB 相位的超透镜 — [case-detail/metalens-based-on-pb-phase](https://www.simworks.net/case-detail/metalens-based-on-pb-phase)
15. 使用交替相移掩模的光刻技术 — [case-detail/lithography-using-alternating-phase-shift-mask](https://www.simworks.net/case-detail/lithography-using-alternating-phase-shift-mask)
16. 负折射率传输线移相器 — [case-detail/negative-refractive-index-transmission-line-phase-shifter](https://www.simworks.net/case-detail/negative-refractive-index-transmission-line-phase-shifter)
17. 同轴馈电矩形贴片天线 — [case-detail/Coaxial-Fed-Rectangular-Patch-Antenna](https://www.simworks.net/case-detail/Coaxial-Fed-Rectangular-Patch-Antenna)
18. 宽带仿真中的模式源 — [case-detail/mode-source-in-broadband](https://www.simworks.net/case-detail/mode-source-in-broadband)
19. 能激发塔姆等离激元的光栅 — [case-detail/tamm-plasmon-polaritons-generated-by-bragg-grating](https://www.simworks.net/case-detail/tamm-plasmon-polaritons-generated-by-bragg-grating)
20. 硅纳米线阵列波导光栅 — [case-detail/si-based-arrayed-waveguide-grating](https://www.simworks.net/case-detail/si-based-arrayed-waveguide-grating)

### 第 3 页
21. 木堆晶格能带结构 — [case-detail/bandstructure-of-woodpile-lattice](https://www.simworks.net/case-detail/bandstructure-of-woodpile-lattice)
22. 硅基双直波导微环谐振腔 — [case-detail/silicon-based-double-straight-waveguide-microring-resonator](https://www.simworks.net/case-detail/silicon-based-double-straight-waveguide-microring-resonator)
23. 偏振分束的聚焦光栅耦合器 — [case-detail/focusing-polarization-splitting-grating-coupler](https://www.simworks.net/case-detail/focusing-polarization-splitting-grating-coupler)
24. 聚焦光栅 — [case-detail/focusing-grating-coupler](https://www.simworks.net/case-detail/focusing-grating-coupler)
25. 介质球的米氏散射 — [case-detail/mie-scattering](https://www.simworks.net/case-detail/mie-scattering)
26. 线栅偏振器 — [case-detail/wire-grid-polarizer](https://www.simworks.net/case-detail/wire-grid-polarizer)
27. 布拉格微腔 — [case-detail/bragg-microcavity](https://www.simworks.net/case-detail/bragg-microcavity)
28. 在石墨烯中激发表面等离激元 — [case-detail/exciting-the-surface-plasmon-polaritons-in-graphene](https://www.simworks.net/case-detail/exciting-the-surface-plasmon-polaritons-in-graphene)
29. SMF-28 光纤的模式计算 — [case-detail/smf-28-fiber-mode-calculation](https://www.simworks.net/case-detail/smf-28-fiber-mode-calculation)
30. 反射型滤色器 — [case-detail/reflective-color-filters](https://www.simworks.net/case-detail/reflective-color-filters)

### 第 4 页
31. 短线对结构的负折射率材料 — [case-detail/negative-index-metamaterial-using-wire-pairs](https://www.simworks.net/case-detail/negative-index-metamaterial-using-wire-pairs)
32. 纳米孔阵列 — [case-detail/nanohole-array](https://www.simworks.net/case-detail/nanohole-array)
33. 基于石墨烯的可调谐太赫兹超材料 — [case-detail/tunable-terahertz-metamaterials-based-on-graphene](https://www.simworks.net/case-detail/tunable-terahertz-metamaterials-based-on-graphene)
34. 回音壁模式微盘 — [case-detail/whispering-gallery-modes-of-a-microdisk](https://www.simworks.net/case-detail/whispering-gallery-modes-of-a-microdisk)
35. 太赫兹超材料 — [case-detail/thz-metamaterial](https://www.simworks.net/case-detail/thz-metamaterial)
36. 具有光子晶体结构的有机太阳能电池 — [case-detail/organic-solar-cell-with-pc-structure](https://www.simworks.net/case-detail/organic-solar-cell-with-pc-structure)
37. 二维周期性金属光子晶体平板 — [case-detail/2d-periodic-metallic-photonic-crystal-slabs](https://www.simworks.net/case-detail/2d-periodic-metallic-photonic-crystal-slabs)
38. 等离激元超材料红外吸收器 — [case-detail/plasma-metamaterial-infrared-absorber](https://www.simworks.net/case-detail/plasma-metamaterial-infrared-absorber)
39. 远场分析：方向性 — [case-detail/far-field-analysis-directivity](https://www.simworks.net/case-detail/far-field-analysis-directivity)
40. 高 Q 腔的场幅值校正 — [case-detail/correcting-field-amplitudes-for-high-q-cavities](https://www.simworks.net/case-detail/correcting-field-amplitudes-for-high-q-cavities)

### 第 5 页
41. 磁光波导的能带结构 — [case-detail/bandstructure-of-a-magneto-optical-waveguide](https://www.simworks.net/case-detail/bandstructure-of-a-magneto-optical-waveguide)
42. 体心立方晶格和面心立方晶格能带结构 — [case-detail/bandstructure-of-bcc-lattice-and-fcc-lattice](https://www.simworks.net/case-detail/bandstructure-of-bcc-lattice-and-fcc-lattice)
43. 3D 立方晶格能带结构 — [case-detail/bandstructure-of-3d-cubic-lattice](https://www.simworks.net/case-detail/bandstructure-of-3d-cubic-lattice)
44. 2D 三角晶格能带结构 — [case-detail/bandstructure-of-2d-triangular-lattice](https://www.simworks.net/case-detail/bandstructure-of-2d-triangular-lattice)
45. 2D 正方晶格能带结构 — [case-detail/bandstructure-of-2d-square-lattice](https://www.simworks.net/case-detail/bandstructure-of-2d-square-lattice)
46. 使用非线性材料产生谐波 — [case-detail/harmonic-generation-with-nonlinear-materials](https://www.simworks.net/case-detail/harmonic-generation-with-nonlinear-materials)
47. 多模干涉耦合器 — [case-detail/mmi-coupler](https://www.simworks.net/case-detail/mmi-coupler)
48. 基于 FDTD 的布拉格光栅 — [case-detail/bragg-grating-based-on-fdtd](https://www.simworks.net/case-detail/bragg-grating-based-on-fdtd)
49. Y 型分束器 — [case-detail/y-branch](https://www.simworks.net/case-detail/y-branch)
50. 平面太阳能电池的光学仿真 — [case-detail/planar-silicon-solar-cell](https://www.simworks.net/case-detail/planar-silicon-solar-cell)

### 第 6 页
51. 利用线缺陷的光子晶体光学开关 — [case-detail/photonic-crystal-optical-switch-using-line-defects](https://www.simworks.net/case-detail/photonic-crystal-optical-switch-using-line-defects)
52. 光子晶体布拉格光纤 — [case-detail/photonic-crystal-bragg-fiber](https://www.simworks.net/case-detail/photonic-crystal-bragg-fiber)

### 案例标签分类（来自官网应用领域）
- **非线性 (Nonlinear)**: [application-gallery?label=Nonlinear](https://www.simworks.net/application-gallery?page=1&label=Nonlinear)
- **远场/方向性 (Far_Field_Directivity)**: [application-gallery?label=Far_Field_Directivity](https://www.simworks.net/application-gallery?page=1&label=Far_Field_Directivity)
- **非对称法布里-珀罗腔 (Asymmetric_Fabry–Perot_Cavities)**: [application-gallery?label=Asymmetric_Fabry–Perot_Cavities](https://www.simworks.net/application-gallery?page=1&label=Asymmetric_Fabry%E2%80%93Perot_Cavities)
- **光偏振 (Optical_Polarization)**: [application-gallery?label=Optical_Polarization](https://www.simworks.net/application-gallery?page=1&label=Optical_Polarization)

## 客户与生态（来源：武汉光博会新闻报道）

- **典型客户**: 海思光电子、中科院上海光机所、华中科技大学、西湖大学、南方科技大学等老用户；武汉二元、天津华慧芯、杭州华芯光电等企业；香港中文大学、武汉理工、武汉工程大学等高校。来源: [https://www.simworks.net/about-us/news-detail/49](https://www.simworks.net/about-us/news-detail/49)

## 学术诚信声明

1. **数据来源**: 本文档所有功能点均来源于 SimWorks 官网（[https://www.simworks.net/](https://www.simworks.net/)）及其子页面（求解器页 / 应用案例页 / 发行说明页 / 教育计划页 / 新闻详情页 / 逆设计解决方案页），并逐项标注来源 URL，未参考任何二手资料。
2. **未公开项标注**: 凡官网未明确公开的细节（如具体定价、GPU 集群规模上限、具体优化算法名称等）一律未列入，避免臆造。
3. **版本基准**: 软件版本基线为 v3.4.0（发布日期 2026/5/29），同时引用 v2.6.0（2025/12/31）发行说明中已落地的功能。来源: [https://www.simworks.net/zh-CN/release-note/-/v3.4](https://www.simworks.net/zh-CN/release-note/-/v3.4) ；[https://www.simworks.net/zh-CN/release-note/-/v2.6](https://www.simworks.net/zh-CN/release-note/-/v2.6)
4. **应用案例计数**: 官网宣称 "50+" 应用案例，本清单实际枚举到第 6 页共 52 个公开案例链接，与官方宣传一致。
5. **厂商信息**: SimWorks 隶属山东光仿软件公司，国产自研，定位世界先进水平。来源: [https://www.simworks.net/about-us/news-detail/50](https://www.simworks.net/about-us/news-detail/50)
6. **禁止臆造**: 本调研严格遵循"基于官网/公开资料"原则，所有技术指标（如 10-100× 加速、FP16 2× 提升、有效折射率 0.0001% 相对误差等）均直接引用官网原文。
