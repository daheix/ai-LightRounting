# T07 Photon Design + T08 gdsfactory 逐点差距分析

| 项目 | 内容 |
|------|------|
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 功能点总数 | 201（T07: 93 + T08: 108） |
| 对比基准 | PoLaRIS 光电子 AI 布局布线引擎（308 功能点） |
| PoLaRIS 代码路径 | `/workspace/src/polaris/` |

## 学术诚信声明

1. 每个功能点的 PoLaRIS 状态均基于 PoLaRIS 功能清单（`/workspace/docs/polaris_feature_inventory.md`）中实际引用的代码位置（`文件:行号`）判定。
2. 状态图例：✅已有（PoLaRIS 有对应实现）/ ⚠️部分（PoLaRIS 有相关能力但不完整或为实验性）/ ❌缺失（PoLaRIS 无对应实现）/ 🚫不适用（架构差异或产品定位不同）。
3. T07 第 7 节 Aspic 的 12 个功能点归属 Filarete srl（非 Photon Design），按 T07 文档说明不计入 93 个 Photon Design 功能点，本报告亦不逐点标注。
4. 覆盖率计算公式：`(✅ + 0.5×⚠️) / (总数 - 🚫)`。

---

## T07 Photon Design（93 功能点）

### 1. FIMMPROP — EME 本征模展开（18 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 双向光学传播工具，严格麦克斯韦方程半解析全矢量 3D 传播 | ❌ | - | PoLaRIS 无 EME 求解器，仅有 FDTD（`fdtd_simulator.py:57`）和电路级 S 参数仿真 |
| 1.2 | EME 方法，3D 环形谐振器数秒内仿真 | ❌ | - | PoLaRIS 无 EME 引擎 |
| 1.3 | 高折射率对比，无缓慢变化近似，广角问题 | ❌ | - | PoLaRIS 无 EME 广角传播 |
| 1.4 | 双向运算，散射矩阵快速优化 | ❌ | - | PoLaRIS 的 S 参数（`models.py:159`）是电路级器件模型，非器件级双向传播散射矩阵 |
| 1.5 | MMI 耦合器、周期结构、锥形、弯曲快速设计 | ⚠️ | `sim/models.py:159`、`pdk/pcell.py:686` | 有 MMI S 参数模型和 PCell，但无器件级物理仿真用于"快速设计" |
| 1.6 | MT-FIMMPROP 版图环境大规模仿真 | ❌ | - | 无版图级严格仿真集成 |
| 1.7 | 可定制计算区域，复杂器件全参数化零代码 | ⚠️ | `pdk/pcell.py:576` | 有 PCell 参数化，但无器件级物理仿真计算区域定制 |
| 1.8 | 锥形建模（taper modelling） | ⚠️ | `router/bundle_router.py:232`、`sim/adjoint_optimizer.py:344` | 有布线级 auto_taper 和解析波导耦合器，非器件级锥形物理建模 |
| 1.9 | 光栅模型（grating models） | ⚠️ | `sim/models.py:159` | 有 grating_coupler_s 电路模型，无光栅物理级建模 |
| 1.10 | 弯曲模型，全矢量 3D 弯曲仿真 | ⚠️ | `router/advanced_connectors.py:74` | 有 EulerBend 布线级弯曲，无全矢量 3D 弯曲物理仿真 |
| 1.11 | 扫描工具，高速优化波导器件 | ✅ | `data/variant_generator.py:478` | 有 generate_param_sweep_variants 参数扫描 |
| 1.12 | 场与模态分析，灵活详尽绘图 | ⚠️ | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），无场截面绘图工具 |
| 1.13 | 模式求解器（FIMMWAVE 能力） | ⚠️ | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非自研全矢量 3D 模式求解器 |
| 1.14 | GDSII 导出 | ✅ | `eval/layout_render.py:331` | 有 export_gds |
| 1.15 | 与 PICWave 链接，严格光学传播+电路建模 | ✅ | `pipeline/integrated.py:446` | 有 IntegratedPipeline 集成仿真流水线 |
| 1.16 | 脚本与优化：Python、MATLAB、Kallistos | ⚠️ | `sim/lbfgs_optimizer.py:132` 等 | 支持 Python 和多种优化器，无 MATLAB/Kallistos |
| 1.17 | 设计接口，轻松创建多种光子元件 | ✅ | `pdk/pcell.py:576`、`pdk/catalog.py:227` | 有 polaris_cell 装饰器和 DeviceCatalog |
| 1.18 | 应用示例：定向耦合器、Y 分束器、MMI、Euler 弯曲等 | ✅ | `sim/models.py:159-455`、`router/advanced_connectors.py:74` | 有 directional_coupler_s/y_branch_s/mmi_1x2_s/EulerBend 等 |

### 2. OmniSim — FDTD 有限差分时域（14 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 2D 与 3D FDTD 引擎 | ✅ | `sim/fdtd_simulator.py:57` | 有 FDTDBackend（MEEP/Tidy3D/ANALYTICAL 三后端） |
| 2.2 | 多核多 CPU FDTD 计算与集群支持 | ⚠️ | `engine/gpu_backend.py:221` | 有 GPU 后端，无明确多核 CPU 集群支持 |
| 2.3 | 原生 64 位版本 | 🚫 | - | PoLaRIS 为 Python 实现，依赖底层库，无"原生 64 位"概念 |
| 2.4 | 子网格（sub-gridding）工具 | ❌ | - | 无子网格局部加密能力 |
| 2.5 | 子网格反射系数优于 1e-8 | ❌ | - | 无子网格 |
| 2.6 | 材料模型：色散/非线性/各向异性/磁性/负折射率 | ⚠️ | `sim/system_level.py:157` | 有 chi3 非线性提及，无完整材料模型库 |
| 2.7 | 边界条件：PML/色散 PML/PEC/PMC/周期 | ⚠️ | `sim/fdtd_simulator.py:57` | 依赖 MEEP/Tidy3D 后端边界条件，非自研 |
| 2.8 | 源：模式/偶极子/平面波/高斯/任意光束 | ⚠️ | `sim/fdtd_simulator.py:279` | 依赖后端源能力，非自研源库 |
| 2.9 | 传感器：时频域/Q 因子/远场/通量/盒传感器 | ⚠️ | `sim/simulator.py:357` | 有 analyze_dispersion 计算 FSR/Q，其他传感器依赖后端 |
| 2.10 | Active FDTD 算法用于纳米激光器（载流子速率方程） | ❌ | - | 有 TLLMLaser（`system_level.py:157`）但非 Active FDTD |
| 2.11 | FDTD 集群版本（Windows 与 Linux） | ❌ | - | 无 FDTD 集群版本 |
| 2.12 | 实时场可视化与视频捕获 | ❌ | - | 有版图渲染（`layout_render.py:123`），无实时场可视化 |
| 2.13 | 灵活的版图编辑器（layout editor） | ⚠️ | `web/server.py:329` | 有 Web 服务器和 PCell，无图形化版图编辑器 |
| 2.14 | 应用：环形谐振器/等离激元/超材料/石墨烯/PCSEL | ⚠️ | `sim/models.py:159` | 有 ring_resonator_s，无等离激元/超材料/石墨烯/PCSEL 物理仿真 |

### 3. OmniSim — FETD 有限元时域（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 2D/3D Finite Element Time Domain (FETD) 工具 | ❌ | - | PoLaRIS 无 FETD 引擎 |
| 3.2 | 等离激元/超材料/石墨烯精确建模 | ❌ | - | 无这些器件的 FETD 物理仿真 |
| 3.3 | 同时包含 FDTD 与 FETD 引擎可交叉验证 | ❌ | - | 无 FETD，仅有 FDTD 交叉验证（`tidy3d_integration.py:578`） |
| 3.4 | FETD 支持非线性（chi2/chi3 孤子） | ❌ | - | 无 FETD |
| 3.5 | FETD 用于纳米天线/Mie 散射/光收集器 | ❌ | - | 无 FETD |

### 4. OmniSim — 其他引擎与工具（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | FEFD Engine：高速 2D 有限元频域 | ❌ | - | 无 FEFD 引擎 |
| 4.2 | RCWA Engine：严格耦合波分析 | ❌ | - | 无 RCWA 引擎 |
| 4.3 | 表面光栅工具（surface grating utility） | ❌ | - | 无表面光栅工具 |
| 4.4 | 能带结构分析器（band structure analyser） | ❌ | - | 无光子晶体能带分析 |
| 4.5 | GDSII 导出 | ✅ | `eval/layout_render.py:331` | 有 export_gds |
| 4.6 | 脚本与优化：Python、MATLAB、Kallistos | ⚠️ | `sim/lbfgs_optimizer.py:132` | 支持 Python 和优化器，无 MATLAB/Kallistos |
| 4.7 | PCSEL 设计流程：Harold→OmniSim→Active FDTD | ❌ | - | 无 PCSEL 设计流程 |
| 4.8 | Q 因子计算器（计算时间减少 85%） | ⚠️ | `sim/simulator.py:357` | 有 analyze_dispersion 计算 FSR/Q，非 FDTD Q 因子加速器 |

### 5. PICWave — 时域光子集成电路与激光器仿真（22 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | 光子集成电路（PIC）设计工具 | ✅ | `pipeline/integrated.py:446`、`sim/simulator.py:57` | 有 IntegratedPipeline 和 CircuitSimulator |
| 5.2 | 详细有源模型，SOA 与激光二极管（FP/混合硅/DFB/可调谐/环形） | ⚠️ | `sim/system_level.py:157` | 有 TLLMLaser，无详细 SOA/多种激光二极管模型 |
| 5.3 | 调制器与光电探测器建模 | ⚠️ | `sim/models.py:159`、`pdk/lnoi.py:50` | 有 phase_shifter_s 和 LNOI 调制器，无光电探测器模型 |
| 5.4 | 激光模型与光路/电路仿真器重叠 | ✅ | `sim/system_level.py:262` | 有 HybridSimulator 混合仿真器 |
| 5.5 | Wide-Band Gain Fitting 算法 | ❌ | - | 无宽带有源增益拟合 |
| 5.6 | 从 Harold 导入增益模型；QCSE EAM 模型 | ❌ | - | 无 Harold 集成 |
| 5.7 | 与 FIMMPROP 链接，导入严格无源仿真 | ⚠️ | `sim/fdtd_simulator.py:279` | 无 FIMMPROP，但有 FDTD 严格仿真入口 |
| 5.8 | 与 EPIPPROP 链接，AWG 与 Echelle 光栅 | ❌ | - | 无 EPIPPROP，无 AWG/Echelle 光栅模型 |
| 5.9 | 行波电极模型（traveling wave electrode） | ✅ | `pdk/lnoi.py:50`、`router/advanced_connectors.py:302` | 有 make_lnoi_mzm_traveling_wave 和 RFGSGRouter |
| 5.10 | 自热模型（self heating model） | ❌ | - | 无自热模型 |
| 5.11 | 物理效应：载流子扩散/电流扩展/孔洞燃烧 | ❌ | - | 无这些物理效应建模 |
| 5.12 | 大型 PIC 仿真（数米长器件） | ✅ | `sim/subnetwork_decomp.py:407` | 有 SubnetworkDecomposition 支持大型电路仿真 |
| 5.13 | Building Block System，预定义设计套件 | ✅ | `pdk/catalog.py:227`、`pdk/foundry_devices.py:188` | 有 DeviceCatalog 和 foundry_devices |
| 5.14 | 电路能力：无源与有源组件集成 | ✅ | `sim/simulator.py:57` | 有 CircuitSimulator 含有源/无源模型 |
| 5.15 | 激光器几何结构（laser geometries） | ❌ | - | 无任意激光二极管几何表征 |
| 5.16 | 分析工具（analysis） | ✅ | `sim/simulator.py:357`、`data/benchmark_evaluator.py:420` | 有 analyze_dispersion 和 evaluate_benchmark |
| 5.17 | 电气模型：两端口电流/电压驱动 | ✅ | `sim/mna_spice.py:102`、`sim/verilog_a.py:98` | 有 MNASolver 和 VerilogAModel |
| 5.18 | 脚本与优化 | ✅ | `sim/lbfgs_optimizer.py:132`、`sim/multi_objective_optimizer.py:52` | 有 L-BFGS/NSGA-II/PSO/CMA-ES 等优化器 |
| 5.19 | 内置 Y-junction/Directional Coupler/MZI 模型 | ✅ | `sim/models.py:159-455` | 有 y_branch_s/directional_coupler_s 等 |
| 5.20 | 弧形段（arc section）仿真弯曲模式 | ⚠️ | `router/advanced_connectors.py:74` | 有布线级 EulerBend，无弯曲模式物理仿真 |
| 5.21 | 应用：SOA/锁模激光器/DFB EML/SG-DBR/SOI 锥形/LiDAR SLED | ❌ | - | 无这些激光器应用模型 |
| 5.22 | PDK 支持 | ✅ | `pdk/foundry_platforms.py:72`、`pdk/gdsfactory_pdk_bridge.py:349` | 有 FOUNDRY_PLATFORMS 和 PolarisPDKRegistry |

### 6. Kallistos — 光子器件优化（15 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 光子器件设计优化工具 | ✅ | `sim/adjoint_optimizer.py:204` | 有 AdjointOptimizer 等多种优化器 |
| 6.2 | 自动改进现有设计 | ✅ | `sim/adjoint_optimizer.py:204` | 有优化器自动改进 |
| 6.3 | 使用最先进的优化技术 | ✅ | `sim/nsga2_operators.py:243`、`sim/global_optimizer.py:127` | 有 NSGA-II/III、CMA-ES、PSO、Adjoint 等 |
| 6.4 | 高效局部下降例程 | ✅ | `sim/lbfgs_optimizer.py:132` | 有 LBFGSOptimizer |
| 6.5 | 确定性与随机全局优化技术 | ✅ | `sim/global_optimizer.py:127`、`sim/pso_optimizer.py:95` | 有 CMA-ES 和 PSO |
| 6.6 | 利用波动方程数学结构，灵敏度解析程序 | ✅ | `sim/adjoint_optimizer.py:204`、`sim/autodiff.py:40` | 有 Adjoint 优化和 JAX 自动微分 |
| 6.7 | 强大内置函数解析器 | ⚠️ | `nn/__init__.py:132` | 有 Tensor 自动微分，非完整函数解析器 |
| 6.8 | 强大、友好的图形用户界面 | ⚠️ | `web/server.py:329` | 有 Web 服务器，非完整 GUI |
| 6.9 | 与 Photon Design 产品紧密集成 | 🚫 | - | PoLaRIS 为独立产品，不与 Photon Design 集成 |
| 6.10 | 针对光子器件性能调优 | ✅ | `sim/robust_optimizer.py:256` | 有 RobustOptimizer 鲁棒性优化 |
| 6.11 | 广泛命令行接口，Python 与 MATLAB 脚本 | ⚠️ | `pipeline/__init__.py:291` | 有 CLI main 入口，支持 Python，无 MATLAB |
| 6.12 | 发现新设计（类似逆向设计） | ✅ | `ai/inverse_design.py:146` | 有 RLInverseDesigner/GANInverseDesigner |
| 6.13 | 跨 Photon Design 套件优化 | 🚫 | - | 不适用，PoLaRIS 非 Photon Design 套件 |
| 6.14 | 应用：线性锥形/S-Bend/MMI/光子晶体/硅纳米光子 | ⚠️ | `sim/adjoint_optimizer.py:344`、`pdk/pcell.py:686` | 有 AnalyticalWaveguideCoupler 和 MMI PCell，无光子晶体优化 |
| 6.15 | 与 Band Analyser 配对 | ❌ | - | 无 Band Analyser |

### 8. 其他 Photon Design 模块（补充）（8 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | FIMMWAVE：波导模式求解器 | ⚠️ | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非自研全矢量 3D 模式求解器 |
| 8.2 | Harold：先进半导体器件仿真（VCSEL/量子点/EAM） | ❌ | - | 无 Harold 等效模块 |
| 8.3 | Harold 量子点增益模型（8 带 k.p/3D 应力应变） | ❌ | - | 无量子点增益模型 |
| 8.4 | EPIPPROP：WDM/DWDM AWG 与 Echelle 光栅 | ❌ | - | 无 AWG/Echelle 光栅模型 |
| 8.5 | EPIPPROP：内建全矢量 2D+z FDM 波导模式求解器 | ⚠️ | `sim/lumerical_integration.py:84` | 有 ModeSolver（实验性），非 FDM 自研 |
| 8.6 | EPIPPROP：自动创建 WDM 器件完整版图 | ❌ | - | 无 WDM 器件版图自动生成 |
| 8.7 | CrystalWave：2D/3D 光子晶格编辑器 | ❌ | - | 无光子晶格编辑器 |
| 8.8 | CrystalWave：SMP 多核 FDTD/集群/有源 FDTD | ❌ | - | 无 CrystalWave 等效能力 |

### 9. 平台支持（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | FDTD 集群版本支持 Windows 与 Linux | ❌ | - | 无 FDTD 集群版本 |
| 9.2 | 多核 SMP 用于 FDTD 快速计算 | ⚠️ | `sim/fdtd_simulator.py:57` | 依赖 MEEP/Tidy3D 后端多核能力，非自研 SMP |
| 9.3 | PICWave 6.3（2025-10）：GUI 改版/新示例 | 🚫 | - | 不适用，PoLaRIS 非 PICWave，无版本对应 |

### T07 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 26 | 28.0% |
| ⚠️ 部分 | 28 | 30.1% |
| ❌ 缺失 | 35 | 37.6% |
| 🚫 不适用 | 4 | 4.3% |
| **合计** | **93** | **100%** |

**T07 覆盖率**：`(26 + 0.5×28) / (93 - 4) = 40/89 = 44.9%`

**主要差距**：
- EME 本征模展开方法完全缺失（1.1-1.4, 1.6）
- FETD 有限元时域引擎完全缺失（3.1-3.5）
- FEFD/RCWA/能带分析等引擎缺失（4.1-4.4）
- Harold 半导体器件仿真完全缺失（8.2-8.3）
- EPIPPROP AWG/Echelle 光栅缺失（5.8, 8.4, 8.6）
- Active FDTD/PCSEL 设计流程缺失（2.10, 4.7）
- 详细有源激光器模型缺失（5.5-5.6, 5.10-5.11, 5.15, 5.21）

---

## T08 gdsfactory（108 功能点）

### 2.1 参数化器件（Parametric Cells, PCells）（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 参数化单元定义，`@gf.cell` 装饰器缓存 | ✅ | `pdk/pcell.py:576` | 有 polaris_cell PCell 装饰器 |
| 1.2 | Component 类，含多边形/端口元数据 | ✅ | `pdk/device.py:85` | 有 Device 核心数据类 |
| 1.3 | 函数式编程，KLayout C++ 几何引擎后端 | ✅ | `data/gds_loader.py:468` | 有 KLayout 集成 GDS 解析 |
| 1.4 | 内置组件库 `gf.components` | ✅ | `pdk/catalog.py:453`、`pdk/pcell.py:667-719` | 有 default_catalog 和内置 PCell（ring/mmi1x2/straight/y_branch） |

### 2.2 YAML 层次化设计（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | YAML Place and AutoRoute | ⚠️ | `pdk/gdsfactory_pdk_bridge.py:298` | 有 parse_pic_yaml，非完整 Place and AutoRoute |
| 2.2 | `from_yaml` 函数，支持 instances/placements/connections/routes/ports | ⚠️ | `pdk/gdsfactory_pdk_bridge.py:298` | 有 PIC YAML 解析，非完整 from_yaml 五段结构 |
| 2.3 | Pydantic 模型校验 | ❌ | - | PoLaRIS 使用 dataclass，无 Pydantic 模型校验 |
| 2.4 | Jinja2 模板支持（`.pic.yml`） | ❌ | - | 无 Jinja2 模板支持 |
| 2.5 | 网表提取 `get_netlist()`/`get_netlist_recursive()` | ✅ | `data/data_loader.py:105`、`sim/lvs.py:121` | 有 circuit_spec_to_netlist_dict 和 extract_netlist_from_gds |
| 2.6 | 层次化组装，单元实例化 | ✅ | `engine/hierarchical_placer.py:85` | 有 HierarchicalPlacer 层次化布局 |

### 2.3 route_fiber_array（光纤阵列路由）（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 光纤阵列路由 | ❌ | - | 无专门光纤阵列路由 |
| 3.2 | 边缘耦合器路由 | ❌ | - | 无专门边缘耦合器路由 |
| 3.3 | Pad 阵列路由 | ⚠️ | `router/opto_electrical.py:101` | 有 OptoElectricalRouter，无专门 Pad 阵列路由 |

### 2.4 get_bundle / route_bundle（7 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | route_bundle，bundle/river/bus 路由器 | ✅ | `router/bundle_router.py:99` | 有 route_bundle |
| 4.2 | route_bundle_all_angle，对角线任意角度 | ✅ | `router/all_angle_router.py:29` | 有 AllAngleRouter |
| 4.3 | route_bundle_electrical，低速 DC 电气端口 | ⚠️ | `router/opto_electrical.py:101` | 有 OptoElectricalRouter，非专门 wire_corner 电气路由 |
| 4.4 | 路径长度匹配 | ✅ | `router/bundle_router.py:147` | 有 route_bundle_path_length_match |
| 4.5 | 碰撞避免 | ✅ | `router/curvy_router.py:350` | 有 AdaptiveCrossingInserter 和 rip-up and reroute |
| 4.6 | 自动锥度 auto_taper | ✅ | `router/bundle_router.py:232` | 有 auto_taper |
| 4.7 | Dubins 路径 | ✅ | `router/bundle_router.py:289` | 有 dubins_path |

### 2.5 routing strategies（路由策略）（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | get_bundle_all_angle，非曼哈顿全角度 | ✅ | `router/all_angle_router.py:29` | 有 AllAngleRouter |
| 5.2 | route_astar，A* 算法（NetworkX astar_path） | ✅ | `router/curvy_router.py:118`、`router/jps_router.py:33` | 有 CurvyAStarRouter 和 JPSRouter |
| 5.3 | route_quad，U 形电气走线 | ❌ | - | 无 U 形电气走线策略 |
| 5.4 | 自定义横截面（CrossSection） | ✅ | `pdk/gdsfactory_integration.py` | 有 convert_crosssection |
| 5.5 | steps 语法，dx/dy/x/y 航点 | ❌ | - | 无 steps 航点语法 |

### 2.6 KLayout DRC 集成（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | KLayout C++ 几何引擎后端 | ✅ | `data/gds_loader.py:468`、`sim/klayout_drc.py:238` | 有 KLayout 集成 |
| 6.2 | DRC 验证 | ✅ | `sim/klayout_drc.py:238`、`sim/hierarchical_drc.py:165` | 有 KLayoutDRCRunner 和 HierarchicalDRC |
| 6.3 | LVS 验证 | ✅ | `sim/graph_lvs.py:160`、`sim/lvs.py:121` | 有 GraphIsomorphismLVSComparer 和 extract_netlist_from_gds |
| 6.4 | get_netlist (KLayout) 从 GDS 提取网表 | ✅ | `sim/lvs.py:121` | 有 extract_netlist_from_gds |
| 6.5 | klive 插件，KLayout 实时交互 | ❌ | - | 无 klive 插件 |

### 2.7 GDSII / OASIS 导出（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | GDSII 导出 `write_gds()` | ✅ | `eval/layout_render.py:331` | 有 export_gds |
| 7.2 | OASIS 导出 | ✅ | `eval/layout_render.py:361` | 有 export_oasis |
| 7.3 | STL 导出（3D 打印） | ❌ | - | 无 STL 导出 |
| 7.4 | GERBER 导出（PCB） | ❌ | - | 无 GERBER 导出 |
| 7.5 | flatten_offgrid_references | ❌ | - | 无 flatten_offgrid_references 选项 |

### 2.8 PDK 支持（43+ PDK）（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | 43+ foundry PDK | ✅ | `pdk/gdsfactory_pdk_bridge.py:349` | 有 PolarisPDKRegistry（48 gdsfactory PDK） |
| 8.2 | 开源光子 PDK（Cornerstone/SiEPIC/VTT/Luxtelligence） | ✅ | `pdk/siepic_mapping.py:31`、`pdk/foundry_platforms.py:72` | 有 SiEPIC 映射和 FOUNDRY_PLATFORMS（11 平台） |
| 8.3 | 开源 CMOS PDK（IHP/GF/SkyWater） | ✅ | `pdk/process_nodes.py:76` | 有 CMOS_PROCESS_NODES |
| 8.4 | NDA PDK（AIM/AMF/CompoundTek/HHI/Smart/Tower 等） | ⚠️ | `pdk/foundry_devices.py:188` | 有 foundry_devices 框架，NDA PDK 覆盖度未明确 |
| 8.5 | PDK 构建说明 | ✅ | `pdk/catalog.py:465`、`pdk/gpic.py:629` | 有 build_default_catalog 和 build_gpic_pdk |
| 8.6 | PDK 导入（固定 GDS 单元库） | ✅ | `pdk/gdsfactory_pdk_bridge.py:349` | 有 gdsfactory PDK 桥接导入 |

### 2.9 量子组件（Quantum Components）（10 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | QPDK 量子 PDK（超导量子 RF） | ❌ | - | 无超导量子 PDK |
| 9.2 | Transmon 量子比特 | ❌ | - | 无 Transmon 组件 |
| 9.3 | Fluxonium 量子比特 | ❌ | - | 无 Fluxonium 组件 |
| 9.4 | Unimon 量子比特 | ❌ | - | 无 Unimon 组件 |
| 9.5 | SQUID 结 | ❌ | - | 无 SQUID 结组件 |
| 9.6 | CPW 谐振器 | ❌ | - | 无 CPW 谐振器组件 |
| 9.7 | 叉指电容 | ❌ | - | 无叉指电容组件 |
| 9.8 | 量子测试芯片（tapeout-ready） | ❌ | - | 无量子测试芯片示例 |
| 9.9 | 量子分析 S 参数模型（SAX/JAX） | ⚠️ | `sim/quantum_photonics.py:40` | 有量子光子仿真（玻色采样/HOM），非超导量子比特 S 参数模型 |
| 9.10 | 量子工具集成（scQubits/QuTiP-QIP/Pymablock/NetKet） | ❌ | - | 无这些量子工具集成 |

### 2.10 SAX 集成（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | SAX 电路求解器（JAX） | ✅ | `sim/cascade.py:315` | 有 cascade_circuit SAX 子网络增长算法复刻 |
| 10.2 | 散射字典 SDict | ✅ | `sim/models.py:159`、`sim/cascade.py:397` | 有 S 参数模型和 _cascade_with_sax |
| 10.3 | 梯度优化 | ✅ | `sim/autodiff.py:40`、`sim/jax_backend.py:65` | 有 JAX 梯度和 JIT 编译 |
| 10.4 | 布局感知 Monte Carlo | ✅ | `sim/monte_carlo.py:63`、`sim/layout_aware.py:361` | 有 monte_carlo_simulate 和 LayoutAwareSimulator |
| 10.5 | 层次化电路仿真 | ✅ | `sim/subnetwork_decomp.py:407` | 有 SubnetworkDecomposition |
| 10.6 | FDTD S 参数模型拟合 | ✅ | `sim/fdtd_simulator.py:57` | 有 FDTDBackend 三后端 S 参数 |

### 2.11 Meep 集成（7 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | gmeep 插件，平面光子组件传输谱 | ✅ | `sim/fdtd_simulator.py:57` | 有 FDTDBackend.MEEP |
| 11.2 | 自动 S 参数提取（端口切换源） | ✅ | `sim/fdtd_simulator.py:279` | 有 run_fdtd_simulation 统一入口 |
| 11.3 | 2.5D 仿真模式 | ❌ | - | 无 2.5D 仿真模式 |
| 11.4 | 端口对称性加速仿真 | ❌ | - | 无端口对称性加速 |
| 11.5 | 多模仿真 | ❌ | - | 无明确多模仿真 |
| 11.6 | 多核/MPI 并行仿真 | ⚠️ | `sim/fdtd_simulator.py:57` | 依赖 MEEP 后端并行，非自研并行调度 |
| 11.7 | 伴随优化（Adjoint Optimization） | ✅ | `sim/adjoint_optimizer.py:204` | 有 AdjointOptimizer |

### 2.12 Tidy3D 集成（7 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | Tidy3D FDTD（GPU 快速） | ✅ | `sim/tidy3d_integration.py:116` | 有 Tidy3DAdapter |
| 12.2 | 材料数据库（色散材料） | ❌ | - | 无材料数据库 |
| 12.3 | Component Modeler（平面 Component 转 tidy3d 仿真） | ✅ | `sim/tidy3d_integration.py:116` | 有 Tidy3DAdapter |
| 12.4 | S 参数写入和文件缓存 | ✅ | `sim/touchstone.py:184` | 有 save_touchstone |
| 12.5 | 2D 和 3D 仿真绘图 | ✅ | `sim/fdtd_simulator.py:57` | 有 FDTD 2D/3D 后端 |
| 12.6 | 侵蚀/膨胀（Erosion/dilation）分析 | ❌ | - | 无侵蚀/膨胀分析 |
| 12.7 | 并行运行作业 | ⚠️ | `trainer/parallel_rollout.py:80` | 有并行 rollout，非 Tidy3D 作业并行 |

### 2.13 Lumerical 集成（5 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | Lumerical FDTD 接口自动计算 S 参数 | ✅ | `sim/lumerical_integration.py:896` | 有 LumericalIntegration |
| 13.2 | write_sparameters_lumerical（GUI/仿真/写入） | ⚠️ | `sim/lumerical_integration.py:402` | 有 INTERCONNECTSimulator（实验性），无完整 write_sparameters_lumerical |
| 13.3 | CSV/DAT 输出（Interconnect/Simphony） | ⚠️ | `sim/touchstone.py:184` | 有 Touchstone 保存，无专门 CSV/DAT 格式 |
| 13.4 | 层堆栈修改（厚度/折射率） | ✅ | `pdk/gdsfactory_integration.py` | 有 convert_layerstack |
| 13.5 | lumapi 集成 | ✅ | `sim/lumerical_integration.py:896` | 有 LumericalIntegration（实验性） |

### 2.14 cocotb 联合仿真（2 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | SPICE 协同仿真（piel 工具） | ✅ | `sim/verilog_a.py:712`、`sim/mna_spice.py:102` | 有 run_ngspice_cosimulation 和 MNASolver |
| 14.2 | 直接 cocotb 集成 | ❌ | - | 无 cocotb 集成 |

### 2.15 VLSIR SPICE 导出（6 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | VLSIR 网表导出（Spectre/SPICE/Xyce） | ❌ | - | 无 VLSIR 网表导出 |
| 15.2 | Spectre RF 网表导出 | ❌ | - | 无 Spectre RF 导出 |
| 15.3 | Xyce 网表导出 | ❌ | - | 无 Xyce 导出 |
| 15.4 | ngspice 网表导出 | ⚠️ | `sim/verilog_a.py:712` | 有 run_ngspice_cosimulation，无独立 ngspice 网表导出 |
| 15.5 | 分析类型支持（Op/Dc/Tran/Ac/Noise） | ⚠️ | `sim/mna_spice.py:102` | 有 MNASolver，分析类型覆盖度未明确 |
| 15.6 | kdb_vlsir 转换 | ❌ | - | 无 kdb_vlsir 转换 |

### 2.16 matplotlib 可视化（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 16.1 | Component `plot()` 方法 | ✅ | `eval/layout_render.py:123` | 有 render_layout |
| 16.2 | plot_sparameters | ❌ | - | 无专门 plot_sparameters |
| 16.3 | plot_netlist | ❌ | - | 无专门 plot_netlist |
| 16.4 | plot_slice 截面绘制 | ❌ | - | 无 plot_slice |

### 2.17 Jupyter Notebook 支持（3 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 17.1 | Notebook 驱动工作流 | ❌ | - | 无明确 Notebook 支持 |
| 17.2 | 交互式开发和可视化 | ⚠️ | `web/server.py:329` | 有 Web 服务器，非 Jupyter 交互 |
| 17.3 | rich_output（Rich 格式输出） | ❌ | - | 无 rich_output |

### 2.18 其他仿真器集成（9 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 18.1 | Femwell (FEM) | ❌ | - | 无 Femwell 集成 |
| 18.2 | Elmer (FEM) | ❌ | - | 无 Elmer 集成 |
| 18.3 | Palace (FEM) | ❌ | - | 无 Palace 集成 |
| 18.4 | MEOW (EME) | ❌ | - | 无 MEOW 集成 |
| 18.5 | DEVSIM (TCAD) | ❌ | - | 无 DEVSIM 集成 |
| 18.6 | MPB (Mode Solver) | ❌ | - | 无 MPB 集成 |
| 18.7 | Luminescent AI | ❌ | - | 无 Luminescent AI 集成 |
| 18.8 | FDTDz | ❌ | - | 无 FDTDz 集成 |
| 18.9 | GMSH 网格 | ❌ | - | 无 GMSH 集成 |

### 2.19 端到端设计流程（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 19.1 | 设计（布局、仿真、优化） | ✅ | `pipeline/integrated.py:446` | 有 IntegratedPipeline |
| 19.2 | 验证（DRC、DFM、LVS） | ✅ | `sim/klayout_drc.py:238`、`sim/graph_lvs.py:160` | 有 KLayoutDRCRunner 和 GraphIsomorphismLVSComparer |
| 19.3 | 验证（Validate，测试协议） | ✅ | `sim/constraint_checker.py:53` | 有 ConstraintChecker 16 项约束检查 |
| 19.4 | 元数据兼容（晶圆探针） | ⚠️ | `pdk/catalog.py:227` | 有 DeviceCatalog 元数据，无明确晶圆探针兼容元数据 |

### 2.20 GDSFactory+ 商业扩展（4 功能点）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 20.1 | GUI 界面（基于 VSCode） | ⚠️ | `web/server.py:329` | 有 Web 服务器，非 VSCode GUI |
| 20.2 | 原理图捕获 | ❌ | - | 无原理图捕获 |
| 20.3 | AI 助手辅助设计 | ✅ | `pdk/pcell.py:631` | 有 ai_generate_pcell |
| 20.4 | CLI 工具（test/bbox/build-pdk/export-spice/verify） | ✅ | `pipeline/__init__.py:291` | 有 main CLI 入口 |

### T08 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已有 | 49 | 45.4% |
| ⚠️ 部分 | 15 | 13.9% |
| ❌ 缺失 | 44 | 40.7% |
| 🚫 不适用 | 0 | 0.0% |
| **合计** | **108** | **100%** |

**T08 覆盖率**：`(49 + 0.5×15) / 108 = 56.5/108 = 52.3%`

**主要差距**：
- 量子组件（QPDK/Transmon/Fluxonium/Unimon/SQUID/CPW）完全缺失（9.1-9.8, 9.10）
- 其他仿真器集成（Femwell/Elmer/Palace/MEOW/DEVSIM/MPB/Luminescent/FDTDz/GMSH）完全缺失（18.1-18.9）
- VLSIR SPICE 导出（Spectre/Xyce/kdb_vlsir）缺失（15.1-15.3, 15.6）
- 可视化工具（plot_sparameters/plot_netlist/plot_slice）缺失（16.2-16.4）
- Jupyter Notebook 支持缺失（17.1, 17.3）
- 导出格式（STL/GERBER）缺失（7.3-7.4）
- YAML 高级特性（Pydantic/Jinja2）缺失（2.3-2.4）
- 路由策略（route_quad/steps 语法）缺失（5.3, 5.5）
- klive 插件缺失（6.5）

---

## 总体统计

| 工具 | ✅已有 | ⚠️部分 | ❌缺失 | 🚫不适用 | 合计 | 覆盖率 |
|------|--------|--------|--------|----------|------|--------|
| T07 Photon Design | 26 | 28 | 35 | 4 | 93 | 44.9% |
| T08 gdsfactory | 49 | 15 | 44 | 0 | 108 | 52.3% |
| **总计** | **75** | **43** | **79** | **4** | **201** | **48.5%** |

> 总覆盖率 = `(75 + 0.5×43) / (201 - 4) = 96.5/197 = 49.0%`

## 关键发现

### T07 Photon Design 差距分析
1. **物理级仿真引擎缺失严重**：EME（FIMMPROP）、FETD、FEFD、RCWA、能带分析器等核心物理求解器均缺失，PoLaRIS 主要依赖 MEEP/Tidy3D 后端做 FDTD，无自研严格传播工具。
2. **有源器件模型薄弱**：Harold 半导体器件仿真、详细 SOA/激光二极管模型、自热模型、载流子扩散等物理效应建模完全缺失。
3. **AWG/Echelle 光栅缺失**：EPIPPROP 的 WDM/DWDM 器件能力无对应实现。
4. **优化能力对齐良好**：Kallistos 的优化能力（L-BFGS/CMA-ES/PSO/NSGA-II/Adjoint）PoLaRIS 基本覆盖。
5. **PDK 与电路仿真对齐良好**：PICWave 的 PIC 设计、Building Block、PDK 支持 PoLaRIS 有对应实现。

### T08 gdsfactory 差距分析
1. **量子组件完全缺失**：QPDK 及所有超导量子比特组件（Transmon/Fluxonium/Unimon/SQUID/CPW）PoLaRIS 无对应实现，PoLaRIS 的量子能力集中在量子光子（玻色采样）而非超导量子。
2. **第三方仿真器集成缺失**：Femwell/Elmer/Palace/MEOW/DEVSIM/MPB/Luminescent/FDTDz/GMSH 等 9 个仿真器集成均缺失。
3. **核心布局布线对齐良好**：PCell、Bundle 路由、A*、Dubins、自动锥度、路径长度匹配等核心能力 PoLaRIS 已覆盖。
4. **KLayout DRC/LVS 集成对齐良好**：DRC、LVS、网表提取 PoLaRIS 有完整实现。
5. **SAX 集成对齐良好**：SAX 电路求解器、SDict、梯度优化、Monte Carlo、层次化电路 PoLaRIS 均有对应实现。
6. **可视化与 Notebook 支持薄弱**：matplotlib 专用绘图函数和 Jupyter 交互支持缺失。
7. **VLSIR SPICE 导出缺失**：Spectre/Xyce 网表导出能力缺失，仅有 ngspice 协同仿真。

### 优先补齐建议
1. **高优先级**（影响核心流程）：VLSIR SPICE 导出、可视化绘图函数、YAML Pydantic 校验
2. **中优先级**（扩展生态）：第三方仿真器集成（MEOW/MPB/Femwell）、STL/GERBER 导出、Jupyter 支持
3. **低优先级**（特定领域）：量子超导组件（QPDK）、EME/FETD/RCWA 物理引擎、Harold 有源器件仿真
