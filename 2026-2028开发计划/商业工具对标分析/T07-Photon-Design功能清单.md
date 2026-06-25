# T07 Photon Design 商业光子 EDA 工具功能点清单

| 项目 | 内容 |
|------|------|
| 工具名 | Photon Design 软件套件 |
| 厂商 | Photon Design Ltd（英国牛津） |
| 官网 URL | https://www.photond.com/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |

> 学术诚信声明：本文档所有功能点均来源于 Photon Design 官网公开页面，每个功能点均标注来源 URL。若官网未明确说明的内容，标注"未公开"。

> **重要归属说明（学术诚信纠正）**：任务清单将"Aspic"列为 Photon Design 的五个模块之一。经官网核实，**Aspic™ 并非 Photon Design 的产品**。Aspic 由 **Filarete srl**（意大利米兰，2008 年由 Politecnico di Milano 的 Andrea Melloni 教授创立）开发与商业化，官网为 http://www.aspicdesign.com/，介绍页见 https://photonics.deib.polimi.it/aspic/。本文档第 7 节按任务要求列出 Aspic 功能点，但明确标注其归属 Filarete srl，而非 Photon Design。Photon Design 真正的电路仿真模块为 **PICWave**。

---

## 1. FIMMPROP — EME 本征模展开（EigenMode Expansion）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 1.1 | 双向光学传播工具，采用严格的麦克斯韦方程求解半解析、全矢量 3D 传播 | https://photond.com/fimmprop |
| 1.2 | 先锋性的 EigenMode Expansion (EME) 方法，3D 环形谐振器可在数秒内仿真 | https://photond.com/fimmprop |
| 1.3 | 高折射率对比性能，无缓慢变化近似，模拟广角问题 | https://www.caxkernel.com/18377.html |
| 1.4 | 双向运算，模拟所有内反射；使用散射矩阵进行快速优化设计 | https://www.caxkernel.com/18377.html |
| 1.5 | MMI 耦合器、周期结构、锥形结构、弯曲结构的快速设计 | https://www.caxkernel.com/18377.html |
| 1.6 | MT-FIMMPROP：在版图环境中结合严格仿真，实现大规模仿真（如完整 MZM 在约 1 分钟内仿真） | https://photond.com/mt |
| 1.7 | 可定制计算区域（不含空区域），复杂器件全参数化几乎零代码 | https://photond.com/ |
| 1.8 | 锥形建模（taper modelling）：建模锥形与连续变化结构 | https://photond.com/fimmprop/features |
| 1.9 | 光栅模型（grating models）：建模光栅与周期结构 | https://photond.com/fimmprop/features |
| 1.10 | 弯曲模型（bend models）：全矢量 3D 弯曲仿真 | https://photond.com/fimmprop/features |
| 1.11 | 扫描工具（scanning tools）：高速优化波导器件 | https://photond.com/fimmprop/features |
| 1.12 | 场与模态分析（field and modal analysis）：灵活详尽的绘图工具绘制任意场截面 | https://photond.com/fimmprop/features |
| 1.13 | 模式求解器（mode solvers）：利用 FIMMWAVE 模式求解器能力 | https://photond.com/fimmprop/features |
| 1.14 | GDSII 导出：一键导出掩膜与版图 | https://photond.com/fimmprop/features |
| 1.15 | 与 PICWave 链接：结合严格光学传播分析与快速光子电路建模 | https://photond.com/fimmprop/features |
| 1.16 | 脚本与优化：使用 Python、MATLAB 与 Kallistos | https://photond.com/fimmprop/features |
| 1.17 | 设计接口（design interface）：轻松创建多种光子元件 | https://photond.com/fimmprop/features |
| 1.18 | 应用示例：定向耦合器、Y 分束器、MMI、锥形、Euler 弯曲、布拉格光栅、光纤锥形、点尺寸转换器、延迟线、级联 MMI/MZI | https://photond.com/fimmprop |

---

## 2. OmniSim — FDTD 有限差分时域

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 2.1 | 2D 与 3D FDTD（Finite Difference Time Domain）引擎，光子学最流行的传播算法 | https://photond.com/omnisim/features/fdtd-engine |
| 2.2 | 多核多 CPU FDTD 计算与集群（cluster）支持 | https://photond.com/omnisim/features/fdtd-engine |
| 2.3 | 原生 64 位版本， virtually unlimited memory | https://photond.com/omnisim/features/fdtd-engine |
| 2.4 | 独特的子网格（sub-gridding）工具，局部 2x/4x 或更高分辨率，4x 子网格可加速 3D 仿真达 64x | https://photond.com/omnisim/features/fdtd-engine |
| 2.5 | 子网格反射系数优于 1e-8（与牛津大学合作研发） | https://photond.com/omnisim/features/fdtd-engine |
| 2.6 | 材料模型：透明与损耗材料、Debye/Drude/Drude-Lorentz 色散模型、chi2/chi3 非线性、各向异性、磁性、负折射率 | https://photond.com/omnisim/features/fdtd-engine |
| 2.7 | 边界条件：六面高性能 PML、色散 PML、PEC/PMC/周期边界 | https://photond.com/omnisim/features/fdtd-engine |
| 2.8 | 源：模式激励、偶极子（含非相干偶极子体积）、平面波、高斯、任意光束；时间包络 CW/正弦脉冲/用户定义 | https://photond.com/omnisim/features/fdtd-engine |
| 2.9 | 传感器：时域与频域结果、Q 因子计算器（约 1/4 时间）、远场计算器、净/前/后向通量、盒传感器 | https://photond.com/omnisim/features/fdtd-engine |
| 2.10 | Active FDTD 算法用于纳米激光器（含载流子速率方程） | https://photond.com/omnisim/features/active-fdtd |
| 2.11 | FDTD 集群版本（Windows 与 Linux） | https://photond.com/omnisim/features/cluster-for-fdtd |
| 2.12 | 实时场可视化与视频捕获 | https://photond.com/omnisim/features/fdtd-engine |
| 2.13 | 灵活的版图编辑器（layout editor），设计任意光子器件 | https://photond.com/omnisim/introduction |
| 2.14 | 应用：环形谐振器、等离激元、超材料、石墨烯、非线性光学、PCSEL | https://photond.com/omnisim/applications |

---

## 3. OmniSim — FETD 有限元时域

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 3.1 | 2D/3D Finite Element Time Domain (FETD) 工具，Photon Design 独有 | https://photond.com/omnisim/introduction |
| 3.2 | 理想用于等离激元（plasmonics）、超材料（metamaterials）或石墨烯器件精确建模 | https://photond.com/omnisim/introduction |
| 3.3 | OmniSim 是唯一同时包含 FDTD 与 FETD 引擎的软件包，可交叉验证 | https://photond.com/omnisim/introduction |
| 3.4 | FETD 支持非线性（chi2 等离激元、chi3 孤子） | https://photond.com/omnisim/applications/nonlinear-optics |
| 3.5 | FETD 用于纳米天线、Mie 散射、光收集器等应用 | https://photond.com/omnisim/applications/plasmonics |

---

## 4. OmniSim — 其他引擎与工具

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 4.1 | FEFD Engine：高速 2D 有限元频域，理想用于快速原型与优化 | https://photond.com/omnisim/introduction |
| 4.2 | RCWA Engine：严格耦合波分析，用于周期结构、超材料、衍射光学元件 | https://photond.com/omnisim/features/rcwa-engine |
| 4.3 | 表面光栅工具（surface grating utility） | https://photond.com/omnisim/features/surface-grating-utility |
| 4.4 | 能带结构分析器（band structure analyser），产生光子晶体能带图与 Bloch 模式 | https://photond.com/omnisim/features/band-structure-analyser |
| 4.5 | GDSII 导出 | https://photond.com/omnisim/features/gdsii-export |
| 4.6 | 脚本与优化：Python、MATLAB 与 Kallistos | https://photond.com/omnisim/features/scripting-and-optimisation |
| 4.7 | PCSEL 设计流程：Harold 增益谱 → OmniSim 动态增益模型 → Active FDTD + Q 因子计算器 | https://photond.com/news-exhibitions/pcsel-design-flow-combine-laser-simulations-with-fdtd |
| 4.8 | Q 因子计算器：相比传统傅里叶变换方法，计算时间减少 85%，结果精度在 1% 以内 | https://photond.com/news-exhibitions/pcsel-design-flow-combine-laser-simulations-with-fdtd |

---

## 5. PICWave — 时域光子集成电路与激光器仿真

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 5.1 | 光子集成电路（PIC）设计工具，集成激光二极管与 SOA 模型、PIC 设计仿真工具、设计流程环境 | https://photond.com/picwave/introduction |
| 5.2 | 详细有源模型，仿真各类 SOA 与激光二极管：Fabry-Perot、混合硅激光器、DFB、可调谐激光器、环形激光器 | https://photond.com/picwave/introduction |
| 5.3 | 也可建模调制器与光电探测器 | https://photond.com/picwave/introduction |
| 5.4 | 激光模型与光路仿真器、电路仿真器重叠 | https://photond.com/picwave/introduction |
| 5.5 | Wide-Band Gain Fitting 算法，宽波长范围内获得准确结果 | https://photond.com/picwave/introduction |
| 5.6 | 从 Harold 直接导入增益模型；导入 QCSE EAM 模型 | https://photond.com/picwave/features/link-to-harold |
| 5.7 | 与 FIMMPROP 链接：导入严格无源仿真（光栅、定向耦合器、优化无损耗弯曲） | https://photond.com/picwave/features/link-to-fimmprop |
| 5.8 | 与 EPIPPROP 链接：导入 AWG 与 Echelle 光栅模型 | https://photond.com/picwave/features/link-to-epipprop |
| 5.9 | 行波电极模型（traveling wave electrode model），同步电气与光学传播（TFLN 调制器示例） | https://photond.com/picwave/applications/travel-wave-modulator |
| 5.10 | 自热模型（self heating model），高功率应用（如 LiDAR 锥形激光器）热翻转效应 | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |
| 5.11 | 物理效应建模：载流子扩散、电流扩展、孔洞燃烧（hole burning，混合硅激光器等复杂器件） | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |
| 5.12 | 大型 PIC 仿真：光在复杂扩展器件（有时数米长）中传播，远超传统 FDTD/FEM Maxwell 求解器 | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |
| 5.13 | Building Block System：使用预定义设计套件（design kits）由工业伙伴提供 | https://photond.com/picwave/features/building-block-system |
| 5.14 | 电路能力（circuit capabilities）：无源与有源组件集成 | https://photond.com/picwave/introduction/circuit-capabilities |
| 5.15 | 激光器几何结构（laser geometries）：表征任意激光二极管几何结构 | https://photond.com/picwave/features/laser-geometries |
| 5.16 | 分析工具（analysis）：仿真结果分析 | https://photond.com/picwave/features/analysis |
| 5.17 | 电气模型（electrical model）：含两端口电流/电压驱动 | https://photond.com/picwave/features/electrical-model |
| 5.18 | 脚本与优化（scripting and optimisation） | https://photond.com/picwave/features/scripting-optimisation |
| 5.19 | 内置 Y-junction、Directional Coupler、MZI 模型，可用物理波导截面定义端口模式，定义反射/损耗系数 | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |
| 5.20 | 弧形段（arc section）仿真弯曲模式，更清晰显示环形用于可调谐激光器与大型电路 | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |
| 5.21 | 应用：SOA、锁模激光器、DFB EML、SG-DBR 可调谐激光器、SOI 混合锥形激光器、模式跳变、LiDAR SLED、双稳态环形谐振器（chi3 非线性） | https://photond.com/picwave/applications |
| 5.22 | PDK 支持 | https://photond.com/ |

---

## 6. Kallistos — 光子器件优化

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 6.1 | 光子器件设计优化工具，提供一系列优化算法改进器件给定目标性能 | https://photond.com/kallistos |
| 6.2 | 自动改进现有设计 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.3 | 使用最先进的优化技术 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.4 | 高效局部下降例程，适合大型计算密集结构，相对少迭代找到最优 | https://photond.com/kallistos/features/optimization-algorithms |
| 6.5 | 确定性与随机全局优化技术，收敛慢但更可能找到全局最优 | https://photond.com/kallistos/features/optimization-algorithms |
| 6.6 | 利用波动方程数学结构，结合灵敏度计算解析程序，极快优化 | https://photond.com/kallistos/features/optimization-algorithms |
| 6.7 | 强大内置函数解析器，完全灵活性 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.8 | 强大、友好的图形用户界面 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.9 | 与 Photon Design 产品紧密集成 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.10 | 针对光子器件性能调优 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.11 | 广泛命令行接口，支持 Python 与 MATLAB 脚本 | https://www.photond.com/products/kallistos/kallistos_features_00.htm |
| 6.12 | 发现新设计（类似逆向设计输出），探索未考虑的设计 | https://photond.com/kallistos |
| 6.13 | 跨 Photon Design 套件优化：无源波导器件、多量子阱外延激光器、光子晶体激光器 | https://photond.com/kallistos |
| 6.14 | 应用：快速线性锥形设计（FIMMPROP，每分钟考虑数千锥形几何）、锥形全几何优化、S-Bend、MMI 耦合器、光子晶体、硅纳米光子学 | https://photond.com/kallistos/applications |
| 6.15 | 与 Band Analyser 配对，快速调谐晶格/原子/腔变量以支持所需激射波长 | https://photond.com/news-exhibitions/pcsel-design-flow-combine-laser-simulations-with-fdtd |

---

## 7. Aspic — 电路仿真（归属：Filarete srl，非 Photon Design）

> **学术诚信声明**：Aspic™ 是 **Filarete srl**（意大利米兰，2008 年由 Politecnico di Milano 的 Andrea Melloni 教授创立）的产品，**不是 Photon Design 的模块**。官网 http://www.aspicdesign.com/，介绍页 https://photonics.deib.polimi.it/aspic/。本节按任务要求列出，但归属以官方来源为准。

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 7.1 | 快速准确的光子集成电路分析、建模与设计仿真器 | https://photonics.deib.polimi.it/aspic/ |
| 7.2 | 基于模型的方法（model-based approach），电路由构建模块集合组成，无需物理级描述，高抽象层级 | https://photonics.deib.polimi.it/aspic/ |
| 7.3 | 计算简单器件与完整电路的光谱行为 | https://photonics.deib.polimi.it/aspic/ |
| 7.4 | 分析任意大型光路，含平面与混合构建模块 | https://photonics.deib.polimi.it/aspic/ |
| 7.5 | 合成复杂电路 | https://photonics.deib.polimi.it/aspic/ |
| 7.6 | 执行虚拟实验与"what if"分析 | https://photonics.deib.polimi.it/aspic/ |
| 7.7 | 导出电路用于掩膜版图生成 | https://photonics.deib.polimi.it/aspic/ |
| 7.8 | 比较测量与仿真以进行参数提取 | https://photonics.deib.polimi.it/aspic/ |
| 7.9 | 研究工艺容差影响 | https://photonics.deib.polimi.it/aspic/ |
| 7.10 | 基于 S-matrix 形式的电路导向仿真器，任意通用电路由基本光学构建模块集合组成 | https://spie.org/Documents/ETOP/2005/ETOP2005_100.pdf |
| 7.11 | 由 Filarete srl 商业化（Andrea Melloni 2008 年创立） | https://www.deib.polimi.it/eng/people/details/271042 |
| 7.12 | 与 PhoeniX Software 等 PDA 工具链集成（FP7 Europic/Paradigm/Helios 项目） | https://www.ecio-conference.org/wp-content/uploads/2016/05/2012/ECIO-2012_115.pdf |

---

## 8. 其他 Photon Design 模块（补充，官网列出）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 8.1 | FIMMWAVE：强大的波导模式求解器，任意 3D 波导全矢量求解 | https://photond.com/fimmwave |
| 8.2 | Harold：先进半导体器件仿真，用于有源光子学（VCSEL、量子点、EAM+ERM、2D 截面、导出 3D 激光仿真） | https://photond.com/harold |
| 8.3 | Harold 量子点增益模型：多层量子点外延吸收与增益谱仿真，8 带 k.p 与全 3D 应力应变模型，高温 LiDAR 应用 | https://photond.com/harold/features/quantum-dot-simulations |
| 8.4 | EPIPPROP：WDM/DWDM AWG 与 Echelle 光栅模型，3D 全矢量分级光栅仿真，分析衍射理论自由空间超快传播 | https://photond.com/epipprop |
| 8.5 | EPIPPROP：内建全矢量 2D+z 有限差分（FDM）波导模式求解器，支持多模波导与任意偏振 | https://www.caxkernel.com/18377.html |
| 8.6 | EPIPPROP：根据所需通道间距自动创建 WDM 器件完整版图并仿真光谱响应 | https://photond.com/epipprop |
| 8.7 | CrystalWave：专业 2D/3D 光子晶格编辑器，2D/3D FDTD/FETD 引擎、高速 FEFD 引擎、RCWA 引擎 | https://www.caxkernel.com/18377.html |
| 8.8 | CrystalWave：SMP 多核 FDTD 快速计算，FDTD 集群（Windows/Linux），有源 FDTD 用于光子晶体激光器 | https://www.caxkernel.com/18377.html |

---

## 9. 平台支持（Platform Support）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 9.1 | FDTD 集群版本支持 Windows 与 Linux | https://photond.com/omnisim/features/cluster-for-fdtd |
| 9.2 | 多核 SMP 用于 FDTD 快速计算 | https://www.caxkernel.com/18377.html |
| 9.3 | PICWave 6.3（2025 年 10 月发布）：GUI 全面改版、新标准示例（混合外延激光器、LiDAR 高功率锥形激光器）、FIMMPROP 环形谐振器链接 | https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples |

---

## 功能点总数统计

| 类别 | 功能点数 |
|------|----------|
| 1. FIMMPROP — EME 本征模展开 | 18 |
| 2. OmniSim — FDTD 有限差分时域 | 14 |
| 3. OmniSim — FETD 有限元时域 | 5 |
| 4. OmniSim — 其他引擎与工具 | 8 |
| 5. PICWave — 时域光子集成电路与激光器仿真 | 22 |
| 6. Kallistos — 光子器件优化 | 15 |
| 7. Aspic — 电路仿真（归属 Filarete srl，非 Photon Design） | 12 |
| 8. 其他 Photon Design 模块（补充） | 8 |
| 9. 平台支持 | 3 |
| **总计** | **105** |

> 注：第 7 节 Aspic 的 12 个功能点归属 Filarete srl，不应计入 Photon Design 产品功能点。若仅统计 Photon Design 自有产品，功能点数为 **93**。

---

## 参考来源汇总

1. Photon Design 官网首页 — https://photond.com/
2. FIMMPROP 产品页 — https://photond.com/fimmprop
3. FIMMPROP Features — https://photond.com/fimmprop/features
4. MT-FIMMPROP — https://photond.com/mt
5. OmniSim 产品页 — https://photond.com/omnisim
6. OmniSim FDTD Engine — https://photond.com/omnisim/features/fdtd-engine
7. OmniSim Active FDTD — https://photond.com/omnisim/features/active-fdtd
8. OmniSim Cluster for FDTD — https://photond.com/omnisim/features/cluster-for-fdtd
9. OmniSim RCWA Engine — https://photond.com/omnisim/features/rcwa-engine
10. OmniSim Band Structure Analyser — https://photond.com/omnisim/features/band-structure-analyser
11. OmniSim GDSII Export — https://photond.com/omnisim/features/gdsii-export
12. OmniSim Scripting and Optimisation — https://photond.com/omnisim/features/scripting-and-optimisation
13. PICWave 产品页 — https://photond.com/picwave
14. PICWave Introduction — https://photond.com/picwave/introduction
15. PICWave Features — https://photond.com/picwave/features
16. PICWave 6.3 发布说明 — https://photond.com/news-exhibitions/picwave-6-3-the-gui-overhaul-new-standard-examples
17. PICWave Travel Wave Modulator — https://photond.com/picwave/applications/travel-wave-modulator
18. Kallistos 产品页 — https://photond.com/kallistos
19. Kallistos Features — https://www.photond.com/products/kallistos/kallistos_features_00.htm
20. Kallistos Optimization Algorithms — https://photond.com/kallistos/features/optimization-algorithms
21. Kallistos Applications — https://photond.com/kallistos/applications
22. Harold 产品页 — https://photond.com/harold
23. Harold Quantum Dot Simulations — https://photond.com/harold/features/quantum-dot-simulations
24. EPIPPROP 产品页 — https://photond.com/epipprop
25. FIMMWAVE 产品页 — https://photond.com/fimmwave
26. PCSEL Design Flow — https://photond.com/news-exhibitions/pcsel-design-flow-combine-laser-simulations-with-fdtd
27. ASPIC 介绍页（Filarete srl） — https://photonics.deib.polimi.it/aspic/
28. Andrea Melloni 个人页（Filarete 创立） — https://www.deib.polimi.it/eng/people/details/271042
29. ASPIC SPIE 论文 — https://spie.org/Documents/ETOP/2005/ETOP2005_100.pdf
30. Photon Design 中文功能介绍 — https://www.caxkernel.com/18377.html
31. PDA 工作流论文（Aspic+PhoeniX） — https://www.ecio-conference.org/wp-content/uploads/2016/05/2012/ECIO-2012_115.pdf
