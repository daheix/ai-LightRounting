# T05 VPIphotonics + T06 Siemens L-Edit Photonics 逐点差距分析

调研日期: 2026-06-25 | 版本: v1.0 | 功能点总数: 157

## 学术诚信声明

1. 本文档基于实际读取的三份输入文档逐点比对：
   - `/workspace/docs/commercial_feature_inventory/T05_vpiphotonics.md`（88 功能点）
   - `/workspace/docs/commercial_feature_inventory/T06_ledit_photonics.md`（69 功能点）
   - `/workspace/docs/polaris_feature_inventory.md`（PoLaRIS 308 功能点，对比基准）
2. PoLaRIS 已有功能点必须引用实现位置（文件:行号），未实现标注 ❌。
3. 状态图例：✅已有（PoLaRIS 有对应实现且成熟度达生产可用/实验性）/ ⚠️部分（PoLaRIS 有相关能力但覆盖不全或仅为实验性）/ ❌缺失（PoLaRIS 无对应实现）/ 🚫不适用（平台/操作系统类，PoLaRIS 作为 Python 跨平台库不直接对标）。
4. 覆盖率 = (✅ + ⚠️) / (总数 - 🚫)。

---

## T05 VPIphotonics（88 功能点）

### 1. 工具套件组成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | VPItransmissionMaker Optical Systems（光传输系统设计） | ⚠️部分 | src/polaris/sim/system_level.py:31 | PoLaRIS 有 SignalFlowGraph/OpticalLink 系统级仿真，但非独立子工具套件 |
| 1.2 | VPIcomponentMaker Photonic Circuits（光子集成电路设计） | ⚠️部分 | src/polaris/sim/simulator.py:57 | PoLaRIS 有 CircuitSimulator 频域仿真器，但模块库规模远小于 VPI |
| 1.3 | VPIcomponentMaker Fiber Optics（光纤放大器/激光器设计） | ❌缺失 | - | PoLaRIS 无光纤放大器/激光器专用设计模块 |
| 1.4 | VPIlabExpert（实验室虚拟化） | ❌缺失 | - | PoLaRIS 无实验室虚拟化能力 |
| 1.5 | VPIdeviceDesigner（器件级波导/光纤仿真，Python 框架） | ⚠️部分 | src/polaris/sim/fdtd_simulator.py:279 | PoLaRIS 有 FDTD/水平集/拓扑优化器件级仿真，但无 BPM/EME |
| 1.6 | VPItoolkit PDK \<fab\>（多 foundry PDK 工具包） | ✅已有 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK（R15，实验性） |

### 2. 时域仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | Photonics TLM 模型，扩展自 TLLM，用于多段光电子器件时域建模 | ⚠️部分 | src/polaris/sim/system_level.py:157 | PoLaRIS 有 TLLMLaser 模型，但未覆盖 SOA/调制器/光电探测器全器件 |
| 2.2 | 支持 MQW 或 Bulk 有源区介质、灵活电极分配、可调增益/吸收谱 | ❌缺失 | - | PoLaRIS 无 MQW/Bulk 有源区介质建模 |
| 2.3 | 任意折射率与增益光栅剖面（含非互易与采样光栅）、反射端面、Kerr/TPA/电折射/电吸收 | ❌缺失 | - | PoLaRIS 无光栅剖面与有源效应建模 |
| 2.4 | 紧密耦合的有源与色散无源光子器件双向端口时域仿真 | ⚠️部分 | src/polaris/sim/caphe_backend.py:292 | PoLaRIS 有 CAPHETimeDomainSolver，但未实现紧密耦合有源-无源双向 |
| 2.5 | 采样信号建模支持光场时域详细仿真，可用于 BER 估计与眼图分析 | ✅已有 | src/polaris/sim/verilog_a.py:864,898 | PoLaRIS 有 compute_eye_diagram/compute_ber 及 EyeDiagramAnalyzer |
| 2.6 | Active FDTD（注：VPIdeviceDesigner 不直接提供 FDTD） | ⚠️部分 | src/polaris/sim/fdtd_simulator.py:279 | PoLaRIS 有 FDTD 仿真（MEEP/Tidy3D/ANALYTICAL），但非 Active FDTD 有源器件 |

### 3. 频域仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 级联散射矩阵（S-matrix）方法，支持数千元件规模 | ✅已有 | src/polaris/sim/cascade.py:315 | PoLaRIS 有 cascade_circuit（SAX 子网络增长算法） |
| 3.2 | 任意频率相关有效模式折射率与衰减，TE/TM 模式独立指定 | ⚠️部分 | src/polaris/sim/models.py:159 | PoLaRIS 有 waveguide_s 模型，但 TE/TM 独立指定能力有限 |
| 3.3 | 加载/保存单个器件及任意无源子电路的 S-matrix | ✅已有 | src/polaris/sim/touchstone.py:133,184 | PoLaRIS 有 load_touchstone/save_touchstone |
| 3.4 | 时均信号表示（time-averaged signal representation） | ❌缺失 | - | PoLaRIS 无时均信号表示 |
| 3.5 | 混合时域-频域方法（TFDM），用于大规模多尺度有源 PIC | ✅已有 | src/polaris/sim/system_level.py:262 | PoLaRIS 有 HybridSimulator 混合仿真器 |

### 4. TLM 传输线模型

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | TLLM 处理多段半导体器件建模，含 Bulk 或 MQW 有源介质 | ⚠️部分 | src/polaris/sim/system_level.py:157 | PoLaRIS 有 TLLMLaser，但无 MQW 有源介质 |
| 4.2 | 支持掩埋异质结激光器、放大器、电光调制器、DBR | ❌缺失 | - | PoLaRIS 无这些具体器件模型 |
| 4.3 | TLLM 涵盖 Kerr 与 TPA、DFB/DBR 光栅、测量增益与吸收谱 | ❌缺失 | - | PoLaRIS 无 Kerr/TPA/DFB/DBR 光栅建模 |
| 4.4 | S-matrix 方法支撑无源光子与线性电器件建模 | ✅已有 | src/polaris/sim/models.py:159; src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 S 参数模型 + MNA SPICE 求解器 |
| 4.5 | 多段半导体激光器建模，支持纵向参数变化（锥形或 FBG 稳频） | ❌缺失 | - | PoLaRIS 无多段半导体激光器建模 |

### 5. BPM 光束传播

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 2D 与 3D 全矢量/半矢量有限差分 BPM | ❌缺失 | - | PoLaRIS 无 BPM 实现 |
| 5.2 | 灵活定义 2D 波导/光纤截面与 3D 器件版图，含色散/温度相关光学材料 | ⚠️部分 | src/polaris/pdk/pcell.py:576 | PoLaRIS 有 PCell 参数化版图，但无色散/温度相关材料库 |
| 5.3 | 可广泛定制的非均匀网格与 PML 吸收边界 | ❌缺失 | - | PoLaRIS 无 PML 吸收边界 |
| 5.4 | 应用：波导、锥形、S-bend、定向耦合器、环形耦合器、Y 分束器、MMI | ✅已有 | src/polaris/sim/models.py:159-455 | PoLaRIS 有 y_branch_s/directional_coupler_s/mmi_1x2_s 等模型 |
| 5.5 | EME（本征模展开）方法，支持双向场传播处理背向反射 | ❌缺失 | - | PoLaRIS 无 EME 方法 |

### 6. 非线性效应

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | TLLM 模型涵盖 Kerr 效应与双光子吸收（TPA） | ❌缺失 | - | PoLaRIS 无 Kerr/TPA 效应建模 |
| 6.2 | 电折射与电吸收效应建模 | ❌缺失 | - | PoLaRIS 无电折射/电吸收效应 |
| 6.3 | 基于 XPM、XGM、FWM 的波长转换比较 | ❌缺失 | - | PoLaRIS 无 XPM/XGM/FWM 波长转换 |
| 6.4 | 2R/3R 再生器开发与速度、传输特性及诱导 chirp 优化 | ❌缺失 | - | PoLaRIS 无 2R/3R 再生器 |
| 6.5 | 光纤非线性（拉曼放大器、参量放大器） | ❌缺失 | - | PoLaRIS 无光纤非线性建模 |

### 7. 光电协同仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | 完整可扩展的线性电器件库（R/C/L/变压器/开关/OpAmp/源） | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA SPICE 求解器，但电器件库不如 VPI 完整 |
| 7.2 | 任意线性电路的 DC、AC 与瞬态分析 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA 求解器，但 DC/AC/瞬态分析能力未明确分立 |
| 7.3 | 通用电气滤波器、函数与 DSP 算法 | ❌缺失 | - | PoLaRIS 无通用电气滤波器/DSP 算法库 |
| 7.4 | 逻辑门与测试函数用于数字电路快速原型 | ❌缺失 | - | PoLaRIS 无逻辑门/数字电路库 |
| 7.5 | 异质 PIC 建模，结合有源与无源子器件，覆盖不同长度尺度 | ⚠️部分 | src/polaris/pipeline/integrated.py:446 | PoLaRIS 有 IntegratedPipeline，但异质有源-无源建模能力有限 |
| 7.6 | 信号与噪声模型基于全波振幅或参数化表示，Jones/Mueller 形式 | ❌缺失 | - | PoLaRIS 无 Jones/Mueller 偏振形式 |

### 8. ADS 联合仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 与 Keysight PathWave ADS 协同仿真 | ❌缺失 | - | PoLaRIS 无 Keysight ADS 集成 |
| 8.2 | 业界首个集成 EOE 工作流 | ❌缺失 | - | PoLaRIS 无 EOE 工作流 |
| 8.3 | 动态通信与无缝数据传输，预测数据链路性能 | ❌缺失 | - | PoLaRIS 无 ADS 动态通信 |
| 8.4 | 分析从电到光再回到电的整条链路 | ⚠️部分 | src/polaris/sim/mna_spice.py:415 | PoLaRIS 有 build_opto_electrical_link_circuit，但非 ADS 全链路 |
| 8.5 | 400G/800G/1.6T 收发器设计；给定 BER 目标下的电设计仿真 | ❌缺失 | - | PoLaRIS 无 400G/800G/1.6T 收发器设计 |
| 8.6 | 全链路眼图指标分析（BER、TDECQ）；调制格式比较（NRZ、PAM-4、16QAM） | ⚠️部分 | src/polaris/sim/verilog_a.py:864,898 | PoLaRIS 有 BER/眼图，但无 TDECQ 与多调制格式比较 |
| 8.7 | 并行化方法比较（FDM、WDM、SDM）；光电带宽对全链路 BER 影响 | ❌缺失 | - | PoLaRIS 无 FDM/WDM/SDM 并行化比较 |

### 9. 多 Foundry PDK 支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | VPItoolkit PDK \<fab\> 可插拔工具包 | ✅已有 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK |
| 9.2 | 支持代工厂：HHI、LIGENTEC、LioniX、SMART、Infinera、GPIC | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:236,295,354 | PoLaRIS 有 Ligentec/Lionix/HHI PDK 构建，缺 SMART/Infinera |
| 9.3 | 支持材料平台：InP、Silicon、Silicon Nitride、Polymer | ✅已有 | src/polaris/pdk/foundry_platforms.py:72 | PoLaRIS 有 11 个 foundry 平台注册表 |
| 9.4 | Layout-aware schematic-driven PIC 设计方法学 | ✅已有 | src/polaris/sim/layout_aware.py:361 | PoLaRIS 有 LayoutAwareSimulator |
| 9.5 | 智能弹性光连接器（elastic optical connectors） | ✅已有 | src/polaris/sim/layout_aware.py:97 | PoLaRIS 有 ElasticConnector |
| 9.6 | 与 PhoeniX OptoDesigner、IPKISS、Nazca Design 集成 | ⚠️部分 | src/polaris/pdk/optodesigner.py:101; src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 OptoDesigner/IPKISS 集成，无 Nazca Design |
| 9.7 | 支持 PDAflow API | ✅已有 | src/polaris/pdk/optodesigner.py:766; src/polaris/pdk/vpi_pdk.py:139 | PoLaRIS 有 PDAflowInterop 和 PDAflowExporter |
| 9.8 | VPItoolkit PDK GPIC 与 L-Edit Photonics / S-Edit 联合解决方案 | ✅已有 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK（R19） |
| 9.9 | 制造容差与良率性能分析，技术方案比较 | ✅已有 | src/polaris/sim/monte_carlo.py:174; src/polaris/sim/robust_optimizer.py:256 | PoLaRIS 有 yield_analysis 和 RobustOptimizer |

### 10. 可视化与数据分析

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 应用专用虚拟仪器 | ❌缺失 | - | PoLaRIS 无虚拟仪器 GUI |
| 10.2 | 光/电信号与数值数据通用后处理分析 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有版图渲染，但无通用信号后处理 |
| 10.3 | 可调分辨率的光谱/波形分析，信号功率与相位特性 | ⚠️部分 | src/polaris/sim/simulator.py:357 | PoLaRIS 有 analyze_dispersion（FSR/Q），但无波形分析 |
| 10.4 | 多输入端口比较不同来源信号/数据 | ❌缺失 | - | PoLaRIS 无多端口信号比较 |
| 10.5 | 时域与频域偏振分析（含 Poincare 球） | ❌缺失 | - | PoLaRIS 无偏振分析/Poincare 球 |
| 10.6 | 不同仿真运行轨迹的叠加、平均与拼接 | ❌缺失 | - | PoLaRIS 无轨迹叠加/平均/拼接 |
| 10.7 | 数值数据 1D 与 2D 绘图，含直方图；多项式或高斯拟合 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有 matplotlib 渲染，但无直方图/拟合 |
| 10.8 | 3D 可视化（表面图、密度图、等高线图） | ❌缺失 | - | PoLaRIS 无 3D 可视化 |
| 10.9 | 全局与局部峰值（最小/最大）搜索；标记精确数据读取 | ❌缺失 | - | PoLaRIS 无峰值搜索 |
| 10.10 | 轴单位切换（THz/nm）与缩放（linear/log/erfc） | ❌缺失 | - | PoLaRIS 无轴单位切换 GUI |
| 10.11 | 可编辑图形属性与出版级图形主题 | ❌缺失 | - | PoLaRIS 无出版级图形主题 |

### 11. 脚本与编程接口

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | Python 与 TCL 仿真脚本 | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 Python CLI，无 TCL |
| 11.2 | 用户自定义算法 Python、Matlab、C++、COM、ADS | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 仅支持 Python，无 Matlab/C++/COM/ADS |
| 11.3 | 仿真引擎对外部系统与第三方工具的 API 访问 | ✅已有 | src/polaris/web/server.py:329 | PoLaRIS 有 HTTP API（PolarisHTTPRequestHandler） |
| 11.4 | Python 协同仿真，添加用户定义 S-matrix 无源光子器件 | ✅已有 | src/polaris/sim/models.py:159 | PoLaRIS 有 10 种基础器件 S 参数模型，可扩展 |
| 11.5 | 宏语言（Macro language）自动化设计操作 | ❌缺失 | - | PoLaRIS 无宏语言 |
| 11.6 | VPIdeviceDesigner 基于 Python，集成 NumPy/SciPy/Matplotlib/Jupyter | ✅已有 | src/polaris/sim/jax_backend.py:65 | PoLaRIS 基于 Python + JAX/NumPy |
| 11.7 | 高阶函数支持映射与链式任意数量模块（AWG/多环滤波器） | ⚠️部分 | src/polaris/data/dataset_generator.py:422 | PoLaRIS 有数据集生成，但无 AWG/多环高阶函数映射 |

### 12. 仿真引擎与并行计算

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 模块算法、设计与参数扫描层面的并行计算 | ⚠️部分 | src/polaris/trainer/parallel_rollout.py:80 | PoLaRIS 有并行 rollout，但非模块/参数扫描级并行 |
| 12.2 | 单 GPU 与多 GPU 加速计算 | ⚠️部分 | src/polaris/engine/gpu_backend.py:221 | PoLaRIS 有 GPUBackend（CuPy，实验性），非多 GPU |
| 12.3 | 本地与远程仿真；仿真作业管理 | ⚠️部分 | src/polaris/flow/scheduler.py:42 | PoLaRIS 有 JobScheduler，但无远程仿真 |
| 12.4 | 自动多维参数扫描、优化与良率估计 | ✅已有 | src/polaris/data/variant_generator.py:478; src/polaris/sim/monte_carlo.py:174 | PoLaRIS 有参数扫描变体生成 + 良率分析 |
| 12.5 | 交互式参数调谐 | ❌缺失 | - | PoLaRIS 无交互式参数调谐 GUI |
| 12.6 | 层次化设计用于系统复杂性抽象 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85 | PoLaRIS 有 HierarchicalPlacer |
| 12.7 | 用户自定义模块与库，可选加密保护 IP | ❌缺失 | - | PoLaRIS 无 IP 加密保护 |
| 12.8 | 导出设计至免费模拟器 VPIplayer | ❌缺失 | - | PoLaRIS 无 VPIplayer 导出 |

### 13. 模块库与应用示例

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | 700+ 光子与电子模块，500+ 设计模板 | ⚠️部分 | src/polaris/sim/models.py:159; src/polaris/pdk/foundry_devices.py:188 | PoLaRIS 有基础器件模型 + foundry 器件，但数量远少于 700+ |
| 13.2 | 130+ VPIcomponentMaker Photonic Circuits 能力演示 | ⚠️部分 | /workspace/tests/*.py（139 测试文件） | PoLaRIS 有 139 测试文件，但非商业级演示库 |
| 13.3 | 应用：电信/数通、短距、光互连、DWDM、RoF、微波光子学、LiDAR、卫星通信 | ⚠️部分 | src/polaris/data/lidar_benchmark.py:37 | PoLaRIS 有 LiDAR/Apollo/TILOS 基准，但无 RoF/卫星通信 |
| 13.4 | 调制格式：PSK、DPSK、DQPSK、mPSK、mQAM | ❌缺失 | - | PoLaRIS 无调制格式库 |
| 13.5 | 大规模 PIC：可重构交叉连接、add-drop 复用、光互连 | ⚠️部分 | src/polaris/data/apollo_benchmark.py:442 | PoLaRIS 有 Apollo oNoC 光子网络基准，但非完整交叉连接 |

### 14. 平台支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | Windows 10 Pro（64 位） | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，不限定 OS |
| 14.2 | Windows 11 Pro（64 位） | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，不限定 OS |
| 14.3 | 硬件：1 GHz+ 64 位处理器，2 GB RAM，3 GB 硬盘，NVIDIA GPU | 🚫不适用 | - | PoLaRIS 为 Python 跨平台库，硬件需求由用户环境决定 |

### T05 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅已有 | 19 | 21.6% |
| ⚠️部分 | 29 | 33.0% |
| ❌缺失 | 37 | 42.0% |
| 🚫不适用 | 3 | 3.4% |
| **合计** | **88** | **100%** |

**覆盖率**: (19 + 29) / (88 - 3) = 48 / 85 = **56.5%**

**关键差距**:
1. **非线性效应（6.1-6.5）全部缺失**：Kerr/TPA/电折射/电吸收/XPM/XGM/FWM/拉曼/参量放大等核心光子非线性能力 PoLaRIS 完全未实现。
2. **BPM/EME 器件级仿真（5.1/5.3/5.5）缺失**：PoLaRIS 有 FDTD 但无 BPM/EME，器件级波导传播方法不全。
3. **ADS 联合仿真（8.1-8.7）大部分缺失**：PoLaRIS 无 Keysight ADS 集成，EOE 工作流缺失。
4. **可视化与数据分析（10.1-10.11）大部分缺失**：PoLaRIS 无虚拟仪器/偏振分析/3D 可视化/出版级图形。
5. **有源器件建模（2.2/2.3/4.2/4.3/4.5）缺失**：MQW/Bulk 有源区、光栅剖面、掩埋异质结激光器等未实现。

---

## T06 Siemens L-Edit Photonics（69 功能点）

### 1. 版图编辑

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 完整层次化物理版图编辑器，支持产品级光芯片设计 | ⚠️部分 | src/polaris/eval/layout_render.py:123; src/polaris/pdk/pcell.py:576 | PoLaRIS 有版图渲染 + PCell，但非完整 GUI 编辑器 |
| 1.2 | 支持曲线多边形与任意角度图形 | ✅已有 | src/polaris/router/curvy_router.py:1286; src/polaris/router/all_angle_router.py:29 | PoLaRIS 有 CurvyRouter + AllAngleRouter |
| 1.3 | 快速渲染（fast rendering） | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有 matplotlib 渲染，但非商业级快速渲染引擎 |
| 1.4 | 对象抓取（object snapping / gravity） | ❌缺失 | - | PoLaRIS 无 GUI 对象抓取 |
| 1.5 | 基于 OpenAccess 构建 | ❌缺失 | - | PoLaRIS 无 OpenAccess 支持 |
| 1.6 | 支持 FinFET、平面及所有其他晶体管技术 | ❌缺失 | - | PoLaRIS 专注光子，无 FinFET/晶体管技术 |
| 1.7 | 内置全角度与曲线支持，用于功率晶体管、MEMS 与光子学 | ✅已有 | src/polaris/router/all_angle_router.py:29; src/polaris/router/curvy_router.py:1286 | PoLaRIS 有全角度与曲线支持（光子学方向） |
| 1.8 | 原生 OpenAccess 多用户支持 | ❌缺失 | - | PoLaRIS 无 OpenAccess 多用户 |

### 2. GPIC PDK 与多 Foundry 支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 支持 Siemens 格式 PDK 与可互操作的行业标准 iPDK | ⚠️部分 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK，但无 Siemens 格式/iPDK 标准支持 |
| 2.2 | PDK 可从多家光子晶圆代工厂获得 | ✅已有 | src/polaris/pdk/foundry_platforms.py:72 | PoLaRIS 有 11 个 foundry 平台注册表 |
| 2.3 | 设计人员可创建自己的元器件或创建自己的 PDK | ✅已有 | src/polaris/pdk/catalog.py:227 | PoLaRIS 有 DeviceCatalog（序列化/反序列化） |
| 2.4 | 支持 30+ 代工厂、200+ PDK | ⚠️部分 | src/polaris/pdk/foundry_platforms.py:72; src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PoLaRIS 有 11 foundry + 48 gdsfactory PDK，规模小于 30+/200+ |
| 2.5 | GPIC PDK，由 Siemens EDA 团队开发，作为开发任意 foundry 自定义 Python 组件的起点 | ✅已有 | src/polaris/pdk/gpic.py:118 | PoLaRIS 有 GPICPDK（R19） |
| 2.6 | GPIC PDK 提供构建模块（BBs）库与真实仿真模型，支持 ASPIC 原型设计 | ✅已有 | src/polaris/pdk/gpic.py:629 | PoLaRIS 有 build_gpic_pdk |

### 3. SDL 原理图驱动版图

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 原理图驱动版图流程，允许首次即创建与原理图匹配的版图 | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 SDLFlow（R25，实验性），但非完整 SDL |
| 3.2 | 自动生成参数化单元（PCell）并实例化到设计中 | ✅已有 | src/polaris/pdk/pcell.py:576 | PoLaRIS 有 polaris_cell PCell 装饰器 |
| 3.3 | 显示飞线（flylines）以放置模块、最小化布线拥塞 | ❌缺失 | - | PoLaRIS 无飞线显示 |
| 3.4 | SDL short 与 open Connectivity Checker | ⚠️部分 | src/polaris/sim/constraint_checker.py:53 | PoLaRIS 有 ConstraintChecker（16 项约束），但非 SDL 专用 |
| 3.5 | 对象抓取（gravity）用于快速、准确版图 | ❌缺失 | - | PoLaRIS 无 GUI 对象抓取 |
| 3.6 | S-Edit 创建原理图；大型设计 SDL 流程 | ❌缺失 | - | PoLaRIS 无 S-Edit 原理图捕获 |

### 4. Calibre 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | L-Edit Photonics 启动 Calibre Interactive 推动物理验证 | ❌缺失 | - | PoLaRIS 无 Calibre Interactive 集成 |
| 4.2 | Calibre nmDRC 用于设计规则检查（DRC） | ⚠️部分 | src/polaris/sim/klayout_drc.py:238; src/polaris/sim/eqdrc.py:172 | PoLaRIS 有 KLayout DRC + eqDRC，但非 Calibre nmDRC |
| 4.3 | Calibre nmLVS 用于版图与原理图检查（LVS） | ⚠️部分 | src/polaris/sim/graph_lvs.py:160; src/polaris/sim/lvs.py:494 | PoLaRIS 有图同构 LVS + 基础 LVS，但非 Calibre nmLVS |
| 4.4 | Calibre xACT 用于寄生效应提取 | ⚠️部分 | src/polaris/sim/layout_aware.py:258 | PoLaRIS 有 ParasiticExtractor，但非 Calibre xACT |
| 4.5 | Calibre LFD（Litho-Friendly Design）用于光刻友好设计 | ❌缺失 | - | PoLaRIS 无光刻友好设计 |
| 4.6 | Calibre RVE 查看结果并高亮网络与器件，支持交叉探测 | ❌缺失 | - | PoLaRIS 无 Calibre RVE |
| 4.7 | 与 Calibre 和 Calibre RealTime 集成 | ❌缺失 | - | PoLaRIS 无 Calibre RealTime 集成 |
| 4.8 | 光子版图验证使用 Calibre 基于方程的设计规则 | ✅已有 | src/polaris/sim/eqdrc.py:172 | PoLaRIS 有 EqDRCEngine（R23 Calibre eqDRC 对齐） |

### 5. GDSII/OASIS 导出与互操作

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 导入与导出 ODB++ | ❌缺失 | - | PoLaRIS 无 ODB++ 支持 |
| 5.2 | 与第三方 IP 互操作支持 | ⚠️部分 | src/polaris/pdk/gdsfactory_integration.py | PoLaRIS 有 gdsfactory 集成，但无第三方 IP 互操作框架 |
| 5.3 | 与第三方版本控制工具集成 | ❌缺失 | - | PoLaRIS 无版本控制工具集成 |
| 5.4 | 基于 OpenAccess，设计数据可与任何支持 OpenAccess 的版图工具互换 | ❌缺失 | - | PoLaRIS 无 OpenAccess 支持 |
| 5.5 | OASIS 导出支持 | ✅已有 | src/polaris/eval/layout_render.py:361 | PoLaRIS 有 export_oasis |

### 6. 曲线多边形与波导

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 支持曲线多边形与任意角度图形 | ✅已有 | src/polaris/router/curvy_router.py:1286 | PoLaRIS 有 CurvyRouter（Euler/arc/Chaikin 平滑） |
| 6.2 | 简单波导创建与编辑 | ✅已有 | src/polaris/router/waveguide_router.py:104 | PoLaRIS 有 GridRouter |
| 6.3 | 自动交叉插入（automated crossing insertion） | ✅已有 | src/polaris/router/curvy_router.py:350 | PoLaRIS 有 AdaptiveCrossingInserter |
| 6.4 | 精确抓取至光学引脚（precision snapping to optical pins） | ❌缺失 | - | PoLaRIS 无 GUI 引脚抓取 |
| 6.5 | 波导到引脚检查（waveguide to pin checking） | ⚠️部分 | src/polaris/sim/constraint_checker.py:53 | PoLaRIS 有 ConstraintChecker，但非专用波导-引脚检查 |
| 6.6 | 多种波导类型：带状、脊型、分段组合 | ✅已有 | src/polaris/router/hybrid_router.py:33 | PoLaRIS 有 WaveguideType 枚举（条形/肋形/槽形） |
| 6.7 | 波导长度编辑，可定义精确有效长度 | ✅已有 | src/polaris/router/advanced_connectors.py:155 | PoLaRIS 有 LengthDefinedConnector |
| 6.8 | 两步波导创建：先创建正交布线，再按热键转换为曲率波导 | ❌缺失 | - | PoLaRIS 无两步波导创建 GUI 流程 |

### 7. S-Edit 电路图

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | S-Edit 提供强大的 IC 与 PIC 原理图捕获环境 | ❌缺失 | - | PoLaRIS 无 S-Edit 原理图捕获 |
| 7.2 | 原理图流程可选（optional with S-Edit） | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 IPKISS SDL 流程（实验性），但无 S-Edit |
| 7.3 | S-Edit 与 L-Edit 工具均可提取描述电路元件与连接的网表 | ⚠️部分 | src/polaris/sim/lvs.py:121 | PoLaRIS 有 extract_netlist_from_gds，但非 S-Edit 网表 |
| 7.4 | 网表导入 INTERCONNECT 等 CML 仿真器，生成基于紧凑模型库的电路 | ✅已有 | src/polaris/sim/interconnect.py:402 | PoLaRIS 有 INTERCONNECTSimulator（R32，实验性） |
| 7.5 | S-Edit 与 VPI Design Suite 联合提供 EPDA 环境 | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK，但无 S-Edit 联合 |

### 8. 网表生成与仿真伙伴集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 以版图为中心的设计流程，内置网表生成 | ✅已有 | src/polaris/sim/lvs.py:121 | PoLaRIS 有 extract_netlist_from_gds |
| 8.2 | 网表支持西门子所有光仿真软件合作伙伴 | ❌缺失 | - | PoLaRIS 无西门子仿真伙伴支持 |
| 8.3 | 仿真合作伙伴：Ansys、Luceda、Optiwave、VPIphotonics | ⚠️部分 | src/polaris/sim/lumerical_integration.py:896; src/polaris/flow/ipkiss_flow.py:494; src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 Lumerical(Ansys)/IPKISS(Luceda)/VPI 集成，无 Optiwave |
| 8.4 | 网表支持西门子晶体管级与混合模式仿真器 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | PoLaRIS 有 MNA SPICE，但非西门子仿真器 |
| 8.5 | 网表格式：InstanceName Nets ModelName Parameters；支持 .subckt/.ends | ⚠️部分 | src/polaris/sim/graph_lvs.py:89 | PoLaRIS 有 PhotonicsNetlist，但格式不完全匹配 |
| 8.6 | 网表参数包含 library、lay_x..lay_f、sch_x..sch_f 及其他元件参数 | ❌缺失 | - | PoLaRIS 无 lay_x/lay_f/sch_x/sch_f 参数 |

### 9. 热光协同

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | 电元器件可手动布局并互连，连接至光子 PCell 中的加热器与外部电气组件 | ⚠️部分 | src/polaris/router/opto_electrical.py:101 | PoLaRIS 有 OptoElectricalRouter，但无加热器 PCell |
| 9.2 | Calibre xACT 寄生效应提取支持热相关电气寄生分析 | ⚠️部分 | src/polaris/sim/layout_aware.py:258 | PoLaRIS 有 ParasiticExtractor，但非 Calibre xACT 热相关 |
| 9.3 | 与 VPIphotonics Design Suite 联合提供 EPDA，支持电-光-热协同仿真 | ⚠️部分 | src/polaris/pdk/vpi_pdk.py:101 | PoLaRIS 有 VPIToolkitPDK，但无完整电-光-热协同 |
| 9.4 | 专用热-光协同仿真模块 | ❌缺失 | - | PoLaRIS 无专用热-光协同仿真模块 |

### 10. 脚本与可扩展性

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 可使用 Python 脚本化 | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 Python CLI |
| 10.2 | 完全可脚本化与可扩展，使用 Python、TCL/Tk 或 C++ | ⚠️部分 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 仅支持 Python，无 TCL/Tk/C++ |
| 10.3 | 支持拖放（drag and drop）方法论 | ❌缺失 | - | PoLaRIS 无 GUI 拖放 |
| 10.4 | 支持脚本驱动方法论（script-driven methodology） | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 有 CLI 脚本驱动 |

### 11. 平台与设计流程

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 支持 Windows 与 Linux 双平台 | ✅已有 | src/polaris/pipeline/__init__.py:156 | PoLaRIS 为 Python 跨平台库 |
| 11.2 | 以版图为中心的设计流程（layout-centric flow） | ✅已有 | src/polaris/pipeline/integrated.py:446 | PoLaRIS 有 IntegratedPipeline |
| 11.3 | 版图作为最重要的设计数据库（golden design database） | ✅已有 | src/polaris/data/gds_loader.py:468 | PoLaRIS 有 GDS 电路解析 |
| 11.4 | 完整 PIC 设计流程：版图创建 → 网表提取 → 仿真 → Calibre 物理验证 → tape-out | ✅已有 | src/polaris/flow/executors.py:145-810 | PoLaRIS 有 10 阶段标准化流程 |
| 11.5 | 直观且易于上手的学习曲线 | ⚠️部分 | src/polaris/web/server.py:329 | PoLaRIS 有 HTTP API + CLI，但无 GUI，学习曲线不如 L-Edit 直观 |

### 12. Luceda IPKISS 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | IPKISS.eda 设计框架基于 Tanner L-Edit 版图编辑器构建 | ⚠️部分 | src/polaris/flow/ipkiss_flow.py:291 | PoLaRIS 有 SDLFlow（R25，实验性），但非基于 L-Edit |
| 12.2 | L-Edit 结合 IPKISS 参数化光子元件库与 PDK，支持拖放光子元件到版图 | ✅已有 | src/polaris/flow/ipkiss_flow.py:494 | PoLaRIS 有 IPKISSPDKBridge |
| 12.3 | 通过波导连接元件，完全控制截面形状、弯曲与轨迹 | ✅已有 | src/polaris/router/waveguide_router.py:104 | PoLaRIS 有 GridRouter + 平台约束 |
| 12.4 | 后版图效应（如波导交叉引起的反射与衰减）通过 IPKISS.eda 紧凑模型仿真器处理 | ⚠️部分 | src/polaris/sim/layout_aware.py:361 | PoLaRIS 有 LayoutAwareSimulator，但非 IPKISS.eda 紧凑模型 |

### T06 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅已有 | 24 | 34.8% |
| ⚠️部分 | 24 | 34.8% |
| ❌缺失 | 21 | 30.4% |
| 🚫不适用 | 0 | 0.0% |
| **合计** | **69** | **100%** |

**覆盖率**: (24 + 24) / 69 = 48 / 69 = **69.6%**

**关键差距**:
1. **GUI 编辑能力（1.4/1.5/1.8/3.3/3.5/3.6/6.4/6.8/10.3）缺失**：PoLaRIS 为命令行库，无对象抓取/飞线/拖放/S-Edit 原理图捕获等 GUI 能力。
2. **Calibre 集成（4.1/4.5/4.6/4.7）缺失**：PoLaRIS 有 eqDRC/LVS 对齐，但无 Calibre Interactive/LFD/RVE/RealTime 原生集成。
3. **OpenAccess/ODB++ 互操作（1.5/1.8/5.1/5.4）缺失**：PoLaRIS 无 OpenAccess 多用户与 ODB++ 支持。
4. **FinFET/晶体管技术（1.6）缺失**：PoLaRIS 专注光子，无 IC 晶体管技术支持。
5. **热-光协同专用模块（9.4）缺失**：PoLaRIS 有光电协同布线，但无专用热-光协同仿真模块。

---

## 总体对比汇总

| 工具 | 功能点数 | ✅已有 | ⚠️部分 | ❌缺失 | 🚫不适用 | 覆盖率 |
|------|----------|--------|--------|--------|----------|--------|
| T05 VPIphotonics | 88 | 19 | 29 | 37 | 3 | 56.5% |
| T06 Siemens L-Edit Photonics | 69 | 24 | 24 | 21 | 0 | 69.6% |
| **合计** | **157** | **43** | **53** | **58** | **3** | **62.7%** |

**总体覆盖率**: (43 + 53) / (157 - 3) = 96 / 154 = **62.3%**

### PoLaRIS 优势领域（相对商业工具）

1. **AI/RL 布局布线**：PoLaRIS 有 AlphaChip GNN、PPO、行为克隆等 AI 能力，商业工具无。
2. **量子光子学**：PoLaRIS 有玻色采样/HOM 干涉/Clements 分解等，VPI/L-Edit 无。
3. **逆向设计**：PoLaRIS 有 Adjoint 优化/拓扑优化/AI 逆向设计，商业工具无。
4. **多目标优化**：PoLaRIS 有 NSGA-II/NSGA-III/CMA-ES/PSO，商业工具无。

### PoLaRIS 主要差距（相对商业工具）

1. **有源器件建模**：MQW/Bulk 有源区、Kerr/TPA/电折射/电吸收等非线性效应完全缺失（T05 6.1-6.5）。
2. **BPM/EME 器件级仿真**：PoLaRIS 有 FDTD 但无 BPM/EME（T05 5.1/5.3/5.5）。
3. **GUI 编辑器**：PoLaRIS 无完整版图编辑器 GUI（T06 1.4/1.5/1.8/3.3/3.5/3.6）。
4. **Calibre 原生集成**：PoLaRIS 有对齐实现但无 Calibre 原生工具链（T06 4.1/4.5/4.6/4.7）。
5. **可视化与分析**：PoLaRIS 无虚拟仪器/偏振分析/3D 可视化/出版级图形（T05 10.1-10.11）。
6. **Keysight ADS 集成**：PoLaRIS 无 ADS 协同仿真（T05 8.1-8.7）。
7. **OpenAccess/ODB++ 互操作**：PoLaRIS 无行业标准 IC 数据互操作（T06 1.5/5.1/5.4）。

---

## 参考来源

1. T05 VPIphotonics 功能点清单: `/workspace/docs/commercial_feature_inventory/T05_vpiphotonics.md`
2. T06 Siemens L-Edit Photonics 功能点清单: `/workspace/docs/commercial_feature_inventory/T06_ledit_photonics.md`
3. PoLaRIS 功能点清单: `/workspace/docs/polaris_feature_inventory.md`
