# T05 VPIphotonics 商业光子 EDA 工具功能点清单

| 项目 | 内容 |
|------|------|
| 工具名 | VPIphotonics Design Suite™ |
| 厂商 | VPIphotonics GmbH（德国） |
| 官网 URL | https://www.vpiphotonics.com/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 当前主版本 | VPIphotonics Design Suite 11.6 |

> 学术诚信声明：本文档所有功能点均来源于 VPIphotonics 官网公开页面，每个功能点均标注来源 URL。若官网未明确说明的内容，标注"未公开"。

---

## 1. 工具套件组成

VPIphotonics Design Suite™ 由以下子工具组成：

| 序号 | 子工具 | 来源 URL |
|------|--------|----------|
| 1.1 | VPItransmissionMaker™ Optical Systems（光传输系统设计） | https://www.vpiphotonics.com/Tools/OpticalSystems/ |
| 1.2 | VPIcomponentMaker™ Photonic Circuits（光子集成电路设计） | https://www.vpiphotonics.com/Tools/PhotonicCircuits/ |
| 1.3 | VPIcomponentMaker™ Fiber Optics（光纤放大器/激光器设计） | https://www.vpiphotonics.com/Tools/FiberOptics/ |
| 1.4 | VPIlabExpert™（实验室虚拟化） | https://www.vpiphotonics.com/Tools/LabExpert |
| 1.5 | VPIdeviceDesigner™（器件级波导/光纤仿真，Python 框架） | https://www.vpiphotonics.com/Tools/DeviceDesigner/ |
| 1.6 | VPItoolkit™ PDK \<fab\>（多 foundry PDK 工具包） | https://www.vpiphotonics.com/Tools/PDK/ |

来源：https://www.vpiphotonics.com/Tools/DesignSuite/Features/

---

## 2. 时域仿真（Time-Domain Simulation）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 2.1 | Photonics TLM 模型，扩展自经典 Transmission-Line Laser Model (TLLM)，用于多段光电子器件（激光器、SOA、调制器、光电探测器）时域建模 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 2.2 | 支持 MQW 或 Bulk 有源区介质、灵活电极分配、可调增益/吸收谱、载流子动力学与 chirp 模型、自发辐射模型 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 2.3 | 任意折射率与增益光栅剖面（含非互易与采样光栅）、反射端面、Kerr、TPA、电折射、电吸收等多种效应 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 2.4 | 紧密耦合的有源与色散无源光子器件双向端口时域仿真（无人工延迟） | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 2.5 | 采样信号建模支持光场时域详细仿真，可用于 BER 估计与眼图分析 | https://www.vpiphotonics.com/Tools/OpticalSystems/ |
| 2.6 | Active FDTD（注：VPIdeviceDesigner 不直接提供 FDTD，时域主要依赖 TLLM 与采样信号） | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |

---

## 3. 频域仿真（Frequency-Domain Simulation）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 3.1 | 级联散射矩阵（S-matrix）方法，用于无源光子电路频域建模，支持数千元件规模 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 3.2 | 任意频率相关有效模式折射率与衰减，TE/TM 模式独立指定 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 3.3 | 加载/保存单个器件及任意无源子电路的 S-matrix，支持真实测量器件建模 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 3.4 | 时均信号表示（time-averaged signal representation），高效建模复杂系统而无需长时间仿真 | https://www.vpiphotonics.com/Tools/OpticalSystems/ |
| 3.5 | 混合时域-频域方法（TFDM），用于大规模多尺度有源光子集成电路高效建模 | https://www.vpiphotonics.com/Tools/PDK/ |

---

## 4. TLM 传输线模型（Transmission-Line Laser Model）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 4.1 | VPI Transmission-Line Laser Model (TLLM) 处理多段半导体器件建模，含 Bulk 或 MQW 有源介质 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 4.2 | 支持掩埋异质结激光器、放大器、电光调制器、分布布拉格反射器 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 4.3 | TLLM 涵盖 Kerr 与双光子吸收效应、DFB/DBR 光栅、测量增益与吸收谱、载流子动力学 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 4.4 | S-matrix 方法支撑无源光子与线性电器件建模（波导、定向耦合器、MMI、星形耦合器、微环谐振器、电阻、电容、电感、电压/电流源） | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 4.5 | 多段半导体激光器建模，支持纵向参数变化（锥形或 FBG 稳频激光器），含 MQW/Bulk、有源/DFB/DBR/无源段及反射界面 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |

---

## 5. BPM 光束传播（Beam Propagation Method）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 5.1 | VPIdeviceDesigner 提供 2D 与 3D 全矢量/半矢量有限差分 BPM 方案 | https://www.vpiphotonics.com/Tools/DeviceDesigner/ |
| 5.2 | 支持灵活定义 2D 波导/光纤截面与 3D 器件版图，含色散/温度相关光学材料 | https://www.vpiphotonics.com/Tools/DeviceDesigner/ |
| 5.3 | 可广泛定制的非均匀网格与完美匹配层（PML）吸收边界 | https://www.vpiphotonics.com/Tools/DeviceDesigner/ |
| 5.4 | 应用：波导、锥形、S-bend、定向耦合器、环形耦合器、Y 分束器、MMI 耦合器与反射器、波导偏振与模式转换器 | https://www.meetoptics.com/suppliers/vpiphotonics |
| 5.5 | EME（本征模展开）方法基于全矢量有限差分模式求解器，支持双向场传播处理背向反射 | https://www.meetoptics.com/suppliers/vpiphotonics |

---

## 6. 非线性效应（Nonlinear Effects）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 6.1 | TLLM 模型涵盖 Kerr 效应与双光子吸收（TPA）效应 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 6.2 | 电折射（electro-refractive）与电吸收（electro-absorption）效应建模 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 6.3 | 基于 XPM、XGM、FWM 的波长转换比较（速度、噪声、转换范围） | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 6.4 | 2R/3R 再生器开发与速度、传输特性及诱导 chirp 优化 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 6.5 | VPIcomponentMaker Fiber Optics 支持光纤非线性（拉曼放大器、参量放大器） | https://www.meetoptics.com/suppliers/vpiphotonics |

---

## 7. 光电协同仿真（Electrical-Optical Co-Simulation）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 7.1 | 完整可扩展的线性电器件库：电阻、电容、电感、变压器、理想开关、线性 OpAmp、理想回转器、独立/受控电流/电压源 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 7.2 | 任意线性电路的 DC、AC 与瞬态分析 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 7.3 | 通用电气滤波器、函数与 DSP 算法 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 7.4 | 逻辑门与测试函数用于数字电路快速原型 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 7.5 | 异质 PIC 建模，结合有源与无源子器件，覆盖不同长度尺度（μm 到 cm） | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 7.6 | 信号与噪声模型基于全波振幅或参数化表示，Jones 与/或 Mueller 形式用于偏振效应 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |

---

## 8. ADS 联合仿真（Keysight PathWave ADS Integration）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 8.1 | 与 Keysight PathWave Advanced Design System (ADS) 协同仿真，建模高级电子、数字、RF 与微波电路 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 8.2 | 业界首个集成 Electrical-Optical-Electrical (EOE) 工作流 | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |
| 8.3 | 动态通信与无缝数据传输，预测数据链路性能 | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |
| 8.4 | 分析从电到光再回到电的整条链路，跨越不同域 | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |
| 8.5 | 应用：400G/800G/1.6T 及以上下一代收发器设计；给定 BER 目标下的电设计仿真 | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |
| 8.6 | 全链路眼图指标分析（BER、TDECQ）；调制格式比较（NRZ、PAM-4、16QAM） | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |
| 8.7 | 并行化方法比较（FDM、WDM、SDM）；光电带宽对全链路 BER 影响研究 | https://www.vpiphotonics.com/Tools/ElectricalOptical/ |

---

## 9. 多 Foundry PDK 支持（Multi-Foundry PDK）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 9.1 | VPItoolkit PDK \<fab\> 可插拔工具包，扩展 VPIcomponentMaker Photonic Circuits 支持各 PIC 代工厂 PDK 构建模块 | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.2 | 支持代工厂：HHI、LIGENTEC、LioniX、SMART、Infinera、GPIC（通用） | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.3 | 支持材料平台：InP、Silicon、Silicon Nitride、Polymer | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.4 | Layout-aware schematic-driven PIC 设计方法学，支持 BB 物理位置与方向指定 | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.5 | 智能弹性光连接器（elastic optical connectors），实现图形化原理图捕获与自动波导布线结合 | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.6 | 与 PhoeniX OptoDesigner (Synopsys)、IPKISS (Luceda)、Nazca Design 集成进行版图、封装与 GDSII 掩膜生成 | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.7 | 支持 PDAflow API | https://www.vpiphotonics.com/Tools/PDK/ |
| 9.8 | VPItoolkit PDK GPIC 与 Siemens EDA L-Edit Photonics / S-Edit 联合解决方案，自动从版图生成完整光子电路原理图 | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |
| 9.9 | 制造容差与良率性能分析，技术方案比较 | https://www.vpiphotonics.com/Tools/PDK/ |

---

## 10. 可视化与数据分析（VPIphotonicsAnalyzers™）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 10.1 | 应用专用虚拟仪器 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.2 | 光/电信号与数值数据通用后处理分析 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.3 | 可调分辨率的光谱/波形分析，信号功率与相位特性 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.4 | 多输入端口比较不同来源信号/数据 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.5 | 时域与频域偏振分析（含 Poincare 球） | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.6 | 不同仿真运行轨迹的叠加、平均与拼接 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.7 | 数值数据 1D 与 2D 绘图，含直方图；多项式或高斯拟合 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.8 | 3D 可视化（表面图、密度图、等高线图） | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.9 | 全局与局部峰值（最小/最大）搜索；标记精确数据读取 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.10 | 轴单位切换（THz/nm）与缩放（linear/log/erfc） | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 10.11 | 可编辑图形属性与出版级图形主题 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |

---

## 11. 脚本与编程接口（Scripting & API）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 11.1 | Python 与 TCL 仿真脚本，用于高级仿真控制 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 11.2 | 支持用户自定义算法/设计的 Python、Matlab®、C++、COM、Keysight PathWave ADS | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 11.3 | 仿真引擎对外部系统与第三方工具的 API 访问 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 11.4 | Python 协同仿真，便于添加任意用户定义 S-matrix 的无源光子器件，支持外部模式求解器与波传播器集成 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 11.5 | 宏语言（Macro language）自动化设计操作 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 11.6 | VPIdeviceDesigner 基于 Python，集成 NumPy、SciPy、Matplotlib，Jupyter Notebook 环境 | https://www.vpiphotonics.com/Tools/DeviceDesigner/ |
| 11.7 | 高阶函数支持映射与链式任意数量模块（如 AWG 数百波导、多环滤波器） | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |

---

## 12. 仿真引擎与并行计算（Simulation Engine & Parallel Computing）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 12.1 | 模块算法、设计与参数扫描层面的并行计算 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.2 | 支持单 GPU 与多 GPU 加速计算（NVIDIA® 计算能力 ≥ 6.0，需双精度） | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.3 | 支持本地与远程仿真；仿真作业管理 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.4 | 自动多维参数扫描、优化与良率估计 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.5 | 交互式参数调谐 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.6 | 层次化设计用于系统复杂性抽象与仿真域接口 | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.7 | 用户自定义模块与库，可选加密保护 IP | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |
| 12.8 | 导出设计至免费模拟器 VPIplayer™ | https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |

---

## 13. 模块库与应用示例（Module Library & Demos）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 13.1 | 700+ 光子与电子模块，500+ 设计模板 | https://www.vpiphotonics.com/Tools/OpticalSystems/ |
| 13.2 | 130+ VPIcomponentMaker Photonic Circuits 能力演示 | https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/ |
| 13.3 | 应用：电信/数通、短距、光互连、超长距 DWDM、Radio-Over-Fiber、微波光子学、LiDAR、卫星通信 | https://www.meetoptics.com/suppliers/vpiphotonics |
| 13.4 | 调制格式：PSK、DPSK、DQPSK、mPSK、mQAM | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |
| 13.5 | 大规模 PIC：可重构交叉连接、add-drop 复用、光互连 | https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf |

---

## 14. 平台支持（Platform Support）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 14.1 | Windows® 10 Pro（64 位，周年更新或更高） | https://m.eeworld.com.cn/bbs_thread-1347549-1-1.html |
| 14.2 | Windows® 11 Pro（64 位） | https://m.eeworld.com.cn/bbs_thread-1347549-1-1.html |
| 14.3 | 硬件：1 GHz+ 64 位处理器，2 GB RAM（推荐更多），3 GB 硬盘空间，1024×768+ 显示，DirectX 9 图形，NVIDIA GPU（计算能力 ≥ 6.0） | https://m.eeworld.com.cn/bbs_thread-1347549-1-1.html |

---

## 功能点总数统计

| 类别 | 功能点数 |
|------|----------|
| 1. 工具套件组成 | 6 |
| 2. 时域仿真 | 6 |
| 3. 频域仿真 | 5 |
| 4. TLM 传输线模型 | 5 |
| 5. BPM 光束传播 | 5 |
| 6. 非线性效应 | 5 |
| 7. 光电协同仿真 | 6 |
| 8. ADS 联合仿真 | 7 |
| 9. 多 Foundry PDK 支持 | 9 |
| 10. 可视化与数据分析 | 11 |
| 11. 脚本与编程接口 | 7 |
| 12. 仿真引擎与并行计算 | 8 |
| 13. 模块库与应用示例 | 5 |
| 14. 平台支持 | 3 |
| **总计** | **88** |

---

## 参考来源汇总

1. VPIphotonics Design Suite Features — https://www.vpiphotonics.com/Tools/DesignSuite/Features/
2. VPIcomponentMaker Photonic Circuits Features — https://www.vpiphotonics.com/Tools/PhotonicCircuits/Features/
3. VPItransmissionMaker Optical Systems — https://www.vpiphotonics.com/Tools/OpticalSystems/
4. VPIdeviceDesigner — https://www.vpiphotonics.com/Tools/DeviceDesigner/
5. VPItoolkit PDK — https://www.vpiphotonics.com/Tools/PDK/
6. VPItoolkit PDK GPIC — https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/
7. Keysight ADS Interface — https://www.vpiphotonics.com/Tools/ElectricalOptical/
8. VPIphotonics DS Photonic Circuits PDF — https://www.vpiphotonics.com/Services/Downloads/DownloadArea/Files/VPIphotonics%20DS%20Photonic%20Circuits.pdf
9. MEETOPTICS Supplier Page — https://www.meetoptics.com/suppliers/vpiphotonics
10. VPIphotonics Design Suite 11.6 介绍 — https://m.eeworld.com.cn/bbs_thread-1347549-1-1.html
