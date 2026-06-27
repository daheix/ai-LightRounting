# PoLaRIS 36 个月逐月路标（R1-R36）

**文档版本**: v1.0
**创建日期**: 2026-06-22
**作者**: PoLaRIS 项目组
**目标**: 在 36 个月内（2026-07 ~ 2029-06）逐月追赶并超越最先进同行光子/电子 EDA 工具的所有功能，综合得分从 6.1/10 提升至 9.0/10 以上。

---

## 1. 路标总览

### 1.1 6 阶段 × 6 月 = 36 月表格

| 阶段 | 月份范围 | 日历区间 | 追赶对象 | 阶段目标 | 综合得分目标 |
|------|----------|----------|----------|----------|--------------|
| 阶段 1 | R1-R6 | 2026-07 ~ 2026-12 | sax + simphony | 电路仿真对齐 | 6.1 → 6.8 |
| 阶段 2 | R7-R12 | 2027-01 ~ 2027-06 | KLayout + gdsfactory | 版图/DRC/PDK 对齐 | 6.8 → 7.4 |
| 阶段 3 | R13-R18 | 2027-07 ~ 2027-12 | Aspic + VPIphotonics | 系统级仿真对齐 | 7.4 → 7.9 |
| 阶段 4 | R19-R24 | 2028-01 ~ 2028-06 | Siemens L-Edit + Synopsys OptoDesigner | 商业版图/DRC/布线对齐 | 7.9 → 8.4 |
| 阶段 5 | R25-R30 | 2028-07 ~ 2028-12 | Luceda IPKISS + Tidy3D | 全流程+FDTD+逆向设计对齐 | 8.4 → 8.8 |
| 阶段 6 | R31-R36 | 2029-01 ~ 2029-06 | Ansys Lumerical + AlphaChip | 顶级商业+AI 对齐 | 8.8 → 9.2 |

### 1.2 当前基线（第 94 轮，2026-06-22）

| 指标 | 当前值 | 来源 |
|------|--------|------|
| 综合得分 | 6.1/10 | `docs/commercial_tools_feature_matrix.md` 第 4.2 节 |
| 测试用例 | 2330 passed, 16 skipped | 第 93 轮操作记录 |
| 质量门禁 | 0 警告 0 错误 | 第 92 轮操作记录 |
| 器件库 | 81 个器件（全溯源） | 第 64 轮操作记录 |
| Foundry runset | 9 foundry（69+ 规则） | 第 64 轮操作记录 |
| Benchmark | 3 个（Apollo PTC/oNoC + LiDAR） | 第 24/26 轮操作记录 |
| 工艺平台 | SOI/SiN/InP/LNOI 四平台 | 第 64 轮操作记录 |

### 1.3 15 维度当前得分与目标

| 维度 | 当前 (R0) | R6 目标 | R12 目标 | R18 目标 | R24 目标 | R30 目标 | R36 目标 | 行业最高 |
|------|-----------|---------|----------|----------|----------|----------|----------|----------|
| D01 布局算法 | 6 | 6 | 7 | 7 | 8 | 8 | 9 | 9 |
| D02 布线算法 | 6 | 6 | 7 | 7 | 8 | 8 | 9 | 9 |
| D03 仿真精度 | 4 | 6 | 6 | 8 | 8 | 9 | 10 | 10 |
| D04 PDK 覆盖 | 5 | 5 | 8 | 8 | 8 | 9 | 9 | 9 |
| D05 DRC/LVS | 6 | 6 | 8 | 8 | 9 | 9 | 9 | 9 |
| D06 GDS 导出 | 7 | 7 | 9 | 9 | 9 | 9 | 9 | 9 |
| D07 AI/ML 能力 | 7 | 7 | 7 | 7 | 7 | 8 | 10 | 10 |
| D08 工艺节点 | 4 | 4 | 6 | 6 | 7 | 8 | 9 | 9 |
| D09 规模可扩展性 | 4 | 5 | 6 | 7 | 8 | 8 | 9 | 10 |
| D10 GUI | 2 | 2 | 5 | 5 | 7 | 7 | 8 | 9 |
| D11 光电协同 | 3 | 3 | 4 | 7 | 7 | 8 | 9 | 9 |
| D12 逆向设计 | 0 | 0 | 0 | 2 | 2 | 8 | 9 | 9 |
| D13 量子光子 | 0 | 0 | 2 | 2 | 2 | 2 | 7 | 7 |
| D14 开源许可 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| D15 用户规模 | 1 | 2 | 3 | 4 | 5 | 7 | 8 | 10 |
| **综合得分** | **6.1** | **6.8** | **7.4** | **7.9** | **8.4** | **8.8** | **9.2** | **9.0+** |

---

## 2. "从小到大逐个追赶"策略

### 2.1 策略原则

1. **从小到大**：先追赶功能单一的开源工具（sax/simphony），再追赶中等规模工具（KLayout/gdsfactory），最后追赶商业巨头（Lumerical/AlphaChip）
2. **逐个击破**：每个阶段聚焦 2 个工具，6 个月内完成对齐
3. **每月可验证**：每月交付一个可验证的功能点（测试/文档/代码）
4. **得分递增**：每阶段综合得分提升 0.5-0.6 分，36 个月从 6.1 提升至 9.2

### 2.2 工具复杂度排序

| 复杂度 | 工具 | 功能维度数 | 追赶难度 |
|--------|------|------------|----------|
| ★ | sax | 3（仿真/JAX/逆向） | 低 |
| ★ | simphony | 3（仿真/SiEPIC/学术） | 低 |
| ★★ | KLayout | 5（版图/DRC/LVS/GDS/GUI） | 中 |
| ★★ | gdsfactory | 8（版图/布线/仿真/PDK/DRC/GDS/光电/量子） | 中 |
| ★★★ | Aspic | 4（电路/器件/时域/优化） | 中高 |
| ★★★ | VPIphotonics | 6（系统/电路/PDK/光电/量子/GUI） | 中高 |
| ★★★★ | Siemens L-Edit | 5（版图/GUI/DRC/GDS/PDK） | 高 |
| ★★★★ | Synopsys OptoDesigner | 7（版图/布线/DRC/GDS/PDK/工艺/tape-out） | 高 |
| ★★★★★ | Luceda IPKISS | 9（版图/布线/仿真/DRC/GDS/PDK/光电/量子/GUI） | 极高 |
| ★★★★★ | Tidy3D | 5（FDTD/GPU/逆向/拓扑/Web） | 极高 |
| ★★★★★★ | Ansys Lumerical | 11（FDTD/MODE/INTERCONNECT/CML/逆向/量子/GUI/光电/工艺/规模/用户） | 顶级 |
| ★★★★★★ | AlphaChip | 5（edge-GNN/PPO/预训练/分布式/TPU） | 顶级 |

### 2.3 阶段-维度对应关系

| 阶段 | 追赶对象 | 主要提升维度 | 次要提升维度 |
|------|----------|--------------|--------------|
| 阶段 1 | sax + simphony | D03 仿真精度 | D07 AI/ML（JAX autograd） |
| 阶段 2 | KLayout + gdsfactory | D04 PDK, D05 DRC/LVS, D06 GDS, D10 GUI | D02 布线, D13 量子 |
| 阶段 3 | Aspic + VPIphotonics | D03 仿真精度, D11 光电协同 | D08 工艺节点 |
| 阶段 4 | L-Edit + OptoDesigner | D01 布局, D02 布线, D05 DRC, D10 GUI | D09 规模, D15 用户 |
| 阶段 5 | IPKISS + Tidy3D | D03 仿真精度, D04 PDK, D12 逆向设计 | D11 光电协同 |
| 阶段 6 | Lumerical + AlphaChip | D01 布局, D07 AI/ML, D09 规模, D13 量子 | D03 仿真精度 |

---

## 3. 阶段 1：R1-R6 追赶 sax + simphony（2026-07 ~ 2026-12）

**阶段目标**：电路仿真精度对齐 sax（JAX 加速 S 参数）和 simphony（S 参数级联），D03 仿真精度从 4/10 提升至 6/10。

### R1（2026-07）：sax S 参数模型格式兼容

> **状态**：✅ 已完成（阶段1，代码 `src/polaris/sim/sax_export.py` 已合并 main）

| 项目 | 内容 |
|------|------|
| **月份编号** | R1（2026-07） |
| **交付目标** | 实现 sax S 参数模型格式（SDict/Model）兼容，PoLaRIS 现有 10 个 S 参数模型可导出为 sax SDict 格式 |
| **追赶对象** | sax（T10） |
| **验收标准** | 1. 新增 `src/polaris/sim/sax_export.py` 模块；2. 10 个 pyCopySiPANN 模型可导出为 sax SDict；3. 新增 ≥5 个单元测试验证导出格式正确性；4. 与 sax `read_sdict` 接口互操作测试通过 |
| **依赖** | 无（基线状态） |
| **来源** | sax 文档 [U14]：https://gdsfactory.github.io/sax/ |

### R2（2026-08）：sax 子网络增长算法集成

> **状态**：✅ 已完成（阶段1，代码 `src/polaris/sim/subnetwork.py` 已合并 main）

| 项目 | 内容 |
|------|------|
| **月份编号** | R2（2026-08） |
| **交付目标** | 实现 sax 子网络增长（subnetwork growth）算法，支持大规模电路的递归 S 参数级联，电路规模从 200 器件扩展至 500 器件 |
| **追赶对象** | sax（T10） |
| **验收标准** | 1. 新增 `src/polaris/sim/subnetwork.py` 模块；2. 500 器件电路 S 参数级联 < 10 秒；3. 与 sax 原生子网络增长结果数值一致（误差 < 1e-6）；4. 新增 ≥8 个单元测试 |
| **依赖** | R1（sax 格式兼容） |
| **来源** | sax 文档 [U14]：https://gdsfactory.github.io/sax/ |

### R3（2026-09）：simphony S 参数级联对齐

> **状态**：✅ 已完成（阶段1，代码 `src/polaris/sim/simphony_backend.py` 已合并 main）

| 项目 | 内容 |
|------|------|
| **月份编号** | R3（2026-09） |
| **交付目标** | 对齐 simphony 的 S 参数级联接口，PoLaRIS SimLoop 可调用 simphony 后端进行电路仿真，并与 sax 后端结果交叉验证 |
| **追赶对象** | simphony（T11） |
| **验收标准** | 1. 新增 `src/polaris/sim/simphony_backend.py` 模块；2. simphony 后端与 sax 后端在 10 个标准电路上结果一致（误差 < 1e-4）；3. 新增 ≥6 个交叉验证测试；4. SimLoop 支持后端切换（sax/simphony/pyCopy） |
| **依赖** | R2（子网络增长） |
| **来源** | simphony arXiv [U15]：https://arxiv.org/pdf/2009.05146 |

### R4（2026-10）：JAX 加速集成

> **状态**：✅ 已完成（阶段1，代码 `src/polaris/sim/jax_backend.py` 已合并 main）

| 项目 | 内容 |
|------|------|
| **月份编号** | R4（2026-10） |
| **交付目标** | 集成 JAX 作为 S 参数仿真的可选后端，实现自动微分（autograd）支持，为后续逆向设计（D12）奠定基础 |
| **追赶对象** | sax（T10，JAX autograd 逆向） |
| **验收标准** | 1. 新增 `src/polaris/sim/jax_backend.py` 模块；2. JAX 后端在 200 器件电路上比 NumPy 后端快 ≥3×；3. 支持 autograd 梯度计算（≥3 个可微参数示例）；4. 新增 ≥6 个单元测试 |
| **依赖** | R3（simphony 后端） |
| **来源** | sax 文档 [U14]：JAX 加速 + autograd |

### R5（2026-11）：电路仿真 Benchmark 对比

> **状态**：✅ 已完成（阶段1，代码 `benchmarks/circuit_sim_benchmark.py` 已合并 main）

| 项目 | 内容 |
|------|------|
| **月份编号** | R5（2026-11） |
| **交付目标** | 建立电路仿真 benchmark 套件，在 10+ 标准电路上对比 PoLaRIS/sax/simphony 的精度与速度，生成对比报告 |
| **追赶对象** | sax + simphony（T10 + T11） |
| **验收标准** | 1. 新增 `benchmarks/circuit_sim_benchmark.py` 脚本；2. 覆盖 10+ 标准电路（MZI/MRR/MMI/Clements/OPA 等）；3. 精度对比误差 < 1e-4；4. 速度对比报告生成；5. 新增 ≥5 个 benchmark 回归测试 |
| **依赖** | R4（JAX 后端） |
| **来源** | simphony arXiv [U15] + sax 文档 [U14] |

### R6（2026-12）：阶段 1 完成 — 电路仿真对齐

> **状态**：✅ 已完成（阶段1 收尾，验收文档 `docs/roundmap_stage1_report.md`）

| 项目 | 内容 |
|------|------|
| **月份编号** | R6（2026-12） |
| **交付目标** | 阶段 1 收尾，PoLaRIS 电路仿真精度对齐 sax + simphony，D03 仿真精度从 4/10 提升至 6/10，综合得分从 6.1 提升至 6.8 |
| **追赶对象** | sax + simphony（T10 + T11） |
| **验收标准** | 1. 电路仿真三后端（sax/simphony/pyCopy）互操作；2. 500 器件电路仿真 < 10 秒；3. JAX 加速 ≥3×；4. benchmark 报告发布；5. 阶段 1 验收文档 `docs/roundmap_stage1_report.md` 发布；6. 综合得分自评 6.8/10 |
| **依赖** | R5（benchmark 对比） |
| **来源** | 本路标第 1.3 节 |

---

## 4. 阶段 2：R7-R12 追赶 KLayout + gdsfactory（2027-01 ~ 2027-06）

**阶段目标**：版图/DRC/PDK 对齐 KLayout（DRC/LVS/GDS）和 gdsfactory（PDK/布线/量子），D04 PDK 从 5/10 提升至 8/10，D05 DRC/LVS 从 6/10 提升至 8/10，D06 GDS 从 7/10 提升至 9/10。

### R7（2027-01）：gdsfactory PDK 桥接（43+ PDK 访问）

> **状态**：⚠️ 代码有，待验收（阶段2，`gdsfactory_integration.py` 存在但未正式合并验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R7（2027-01） |
| **交付目标** | 增强 `gdsfactory_integration.py`，桥接 gdsfactory 43+ PDK（含 NDA），PoLaRIS 可直接引用 gdsfactory 器件库 |
| **追赶对象** | gdsfactory（T08） |
| **验收标准** | 1. `gdsfactory_integration.py` 支持 43+ PDK 枚举；2. 至少 5 个开源 PDK（SiEPIC/GF180/SKY130/IHP/open_ebeam）可导入；3. 器件库从 81 扩展至 150+；4. 新增 ≥10 个 PDK 桥接测试 |
| **依赖** | R6（阶段 1 完成） |
| **来源** | gdsfactory CLEO 2026 论文 [U12]：https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf |

### R8（2027-02）：KLayout DRC 引擎深度集成

> **状态**：⚠️ 代码有，待验收（阶段2，`klayout_drc.py` 存在但未正式合并验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R8（2027-02） |
| **交付目标** | 深度集成 KLayout 0.30.9 DRC 引擎，支持 tiled/hierarchical/deep 模式，DRC runset 从 9 foundry/69 规则扩展至 12 foundry/120+ 规则 |
| **追赶对象** | KLayout（T09） |
| **验收标准** | 1. `klayout_drc.py` 支持 tiled/hierarchical/deep 三种模式；2. 新增 3 foundry runset（AIM/AMF/CompoundTek NDA 占位）；3. DRC 规则总数 ≥120；4. 新增 ≥8 个 DRC 引擎测试 |
| **依赖** | R7（gdsfactory PDK 桥接） |
| **来源** | KLayout 官网 [U13]：https://klayout.org + gdsfactory DRC 集成 [U23] |

### R9（2027-03）：KLayout LVS 增强

> **状态**：⏳ 待核查（阶段2，`lvs.py` 实现状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R9（2027-03） |
| **交付目标** | 增强 LVS 实现，支持层次化 LVS、深层次网表比对、波导路径追踪真实化，对齐 KLayout 原生 LVS API |
| **追赶对象** | KLayout（T09） |
| **验收标准** | 1. `lvs.py` 支持层次化 LVS（≥3 层）；2. 波导路径追踪准确率 ≥95%；3. 10 个标准电路 LVS 通过率 100%；4. 新增 ≥8 个 LVS 测试 |
| **依赖** | R8（KLayout DRC 深度集成） |
| **来源** | KLayout 官网 [U13] + Layout Verification ISPD 2024 [U26] |

### R10（2027-04）：gdsfactory 布线策略对齐

> **状态**：❌ 未实现（阶段2，`src/polaris/routing/gdsfactory_style.py` 缺失，Glob 核查 2026-06-27）

| 项目 | 内容 |
|------|------|
| **月份编号** | R10（2027-04） |
| **交付目标** | 对齐 gdsfactory routing strategies（route_fiber_array/get_bundle/route_sbend 等），PoLaRIS 布线器支持 gdsfactory 风格的布线 API |
| **追赶对象** | gdsfactory（T08） |
| **验收标准** | 1. 新增 `src/polaris/routing/gdsfactory_style.py` 模块；2. 实现 ≥5 种 gdsfactory 布线策略；3. 与 PoLaRIS A* 布线结果对比（线长差距 < 10%）；4. 新增 ≥8 个布线策略测试 |
| **依赖** | R9（KLayout LVS 增强） |
| **来源** | gdsfactory 文档 [U12]：routing strategies |

### R11（2027-05）：GDS/OASIS 导出精度提升（1nm 曲线）

> **状态**：⏳ 待核查（阶段2，GDS 导出精度提升状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R11（2027-05） |
| **交付目标** | GDS/OASIS 导出精度提升至 1nm 曲线离散化（对齐 OptoDesigner），支持任意曲线多边形、贝塞尔/样条曲线 |
| **追赶对象** | KLayout + gdsfactory（T09 + T08） |
| **验收标准** | 1. GDS 导出曲线精度 ≤1nm；2. 支持贝塞尔/样条/Euler 曲线；3. OASIS 导出通过 KLayout 验证；4. 新增 ≥6 个导出精度测试 |
| **依赖** | R10（gdsfactory 布线策略） |
| **来源** | KLayout 官网 [U13] + OptoDesigner [U04] |

### R12（2027-06）：阶段 2 完成 — 版图/DRC/PDK 对齐

> **状态**：⏳ 待核查（阶段2 收尾，因 R10 缺失导致阶段2未完整完成）

| 项目 | 内容 |
|------|------|
| **月份编号** | R12（2027-06） |
| **交付目标** | 阶段 2 收尾，PoLaRIS 版图/DRC/PDK 对齐 KLayout + gdsfactory，D04 PDK 5→8，D05 DRC/LVS 6→8，D06 GDS 7→9，D10 GUI 2→5，综合得分 6.8→7.4 |
| **追赶对象** | KLayout + gdsfactory（T09 + T08） |
| **验收标准** | 1. PDK 覆盖 12 foundry/150+ 器件；2. DRC 120+ 规则；3. LVS 层次化支持；4. GDS 1nm 曲线精度；5. 阶段 2 验收文档 `docs/roundmap_stage2_report.md` 发布；6. 综合得分自评 7.4/10 |
| **依赖** | R11（GDS 精度提升） |
| **来源** | 本路标第 1.3 节 |

---

## 5. 阶段 3：R13-R18 追赶 Aspic + VPIphotonics（2027-07 ~ 2027-12）

**阶段目标**：系统级仿真对齐 Aspic（PICWave 时域/FIMMPROP EME）和 VPIphotonics（系统级/光电协同），D03 仿真精度从 6/10 提升至 8/10，D11 光电协同从 3/10 提升至 7/10。

### R13（2027-07）：VPIphotonics 系统级仿真模型

> **状态**：⚠️ 代码有，待验收（阶段3，`src/polaris/sim/system_level.py` 存在但未正式合并验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R13（2027-07） |
| **交付目标** | 实现 VPIphotonics 风格的系统级仿真模型（频域/时域/TLM 非线性），支持光通信链路级仿真 |
| **追赶对象** | VPIphotonics（T05） |
| **验收标准** | 1. 新增 `src/polaris/sim/system_level.py` 模块；2. 支持频域/时域/TLM 三种模式；3. 至少 3 个光通信链路示例（NRZ/PAM4/QAM）；4. 新增 ≥8 个系统级仿真测试 |
| **依赖** | R12（阶段 2 完成） |
| **来源** | VPIphotonics Design Suite [U06]：https://www.vpiphotonics.com/Tools/DesignSuite/Features/ |

### R14（2027-08）：VPItoolkit PDK 对齐

> **状态**：⏳ 待核查（阶段3，VPI foundry 模型库状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R14（2027-08） |
| **交付目标** | 对齐 VPItoolkit PDK GPIC，支持 HHI/LIGENTEC/LioniX/SMART/Infinera 等 foundry 的系统级模型 |
| **追赶对象** | VPIphotonics（T05） |
| **验收标准** | 1. 新增 ≥3 个 VPI 风格 foundry 模型库（HHI/LIGENTEC/LioniX）；2. 系统级模型与电路级模型互操作；3. 新增 ≥6 个 PDK 模型测试 |
| **依赖** | R13（系统级仿真模型） |
| **来源** | VPItoolkit PDK GPIC [U21]：https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |

### R15（2027-09）：Aspic/PICWave 时域仿真

> **状态**：❌ 未实现（阶段3，`src/polaris/sim/picwave_backend.py` 缺失，Glob 核查 2026-06-27，P0 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R15（2027-09） |
| **交付目标** | 实现 PICWave 风格的时域光子电路仿真（FDTD 时域 + 非线性），支持大规模 PIC 时域分析 |
| **追赶对象** | Aspic/PICWave（T07） |
| **验收标准** | 1. 新增 `src/polaris/sim/picwave_backend.py` 模块；2. 时域仿真支持非线性效应（Kerr/TPA/自由载流子）；3. 200 器件时域仿真 < 60 秒；4. 新增 ≥8 个时域仿真测试 |
| **依赖** | R14（VPItoolkit PDK） |
| **来源** | Photon Design PICWave [U08][U11]：https://photond.com/ |

### R16（2027-10）：FIMMPROP EME 集成

> **状态**：❌ 未实现（阶段3，`src/polaris/sim/eme_backend.py` 缺失，Glob 核查 2026-06-27，P0 优先级；注：`sim/eme/` 目录存在）

| 项目 | 内容 |
|------|------|
| **月份编号** | R16（2027-10） |
| **交付目标** | 集成 FIMMPROP 风格的 EME（本征模展开）仿真，支持长距离波导/锥形/弯曲的精确传播仿真 |
| **追赶对象** | Aspic/FIMMPROP（T07） |
| **验收标准** | 1. 新增 `src/polaris/sim/eme_backend.py` 模块；2. EME 仿真精度与 S 参数级联交叉验证（误差 < 1e-3）；3. 支持锥形/弯曲/交叉等 ≥5 种结构；4. 新增 ≥6 个 EME 测试 |
| **依赖** | R15（PICWave 时域） |
| **来源** | Photon Design FIMMPROP [U11]：https://photond.com/fimmprop/introduction |

### R17（2027-11）：光电协同仿真（SPICE 联合）

> **状态**：❌ 未实现（阶段3，`src/polaris/sim/photoelectric_cosim.py` 缺失，Glob 核查 2026-06-27，P0 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R17（2027-11） |
| **交付目标** | 实现光电协同仿真，支持 VLSIR SPICE 导出 + Verilog-A 光子模型 + cocotb 数字联合仿真 |
| **追赶对象** | VPIphotonics + Aspic（T05 + T07） |
| **验收标准** | 1. 新增 `src/polaris/sim/photoelectric_cosim.py` 模块；2. 支持 VLSIR SPICE 网表导出；3. ≥3 个 Verilog-A 光子模型（调制器/探测器/激光器）；4. cocotb 联合仿真示例；5. 新增 ≥8 个光电协同测试 |
| **依赖** | R16（FIMMPROP EME） |
| **来源** | VPIphotonics [U06] + gdsfactory VLSIR [U12] |

### R18（2027-12）：阶段 3 完成 — 系统级仿真对齐

> **状态**：⏳ 待核查（阶段3 收尾，因 R15/R16/R17 缺失导致阶段3未完整完成）

| 项目 | 内容 |
|------|------|
| **月份编号** | R18（2027-12） |
| **交付目标** | 阶段 3 收尾，PoLaRIS 系统级仿真对齐 Aspic + VPIphotonics，D03 仿真精度 6→8，D11 光电协同 3→7，D08 工艺节点 6→6，综合得分 7.4→7.9 |
| **追赶对象** | Aspic + VPIphotonics（T07 + T05） |
| **验收标准** | 1. 系统级/时域/EME 三后端互操作；2. 光电协同仿真完整；3. 非线性效应支持；4. 阶段 3 验收文档 `docs/roundmap_stage3_report.md` 发布；5. 综合得分自评 7.9/10 |
| **依赖** | R17（光电协同仿真） |
| **来源** | 本路标第 1.3 节 |

---

## 6. 阶段 4：R19-R24 追赶 Siemens L-Edit + Synopsys OptoDesigner（2028-01 ~ 2028-06）

**阶段目标**：商业版图/DRC/布线对齐 L-Edit（GUI/Calibre 集成）和 OptoDesigner（Design Intent/自动布线/DRC 模块），D01 布局 6→8，D02 布线 6→8，D05 DRC/LVS 8→9，D10 GUI 5→7。

### R19（2028-01）：L-Edit 风格 GUI 集成

> **状态**：❌ 未实现（阶段4，`src/polaris/gui/layout_editor.py` 缺失，Glob 核查 2026-06-27，P1 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R19（2028-01） |
| **交付目标** | 实现 L-Edit 风格的版图编辑 GUI（基于 Web + KLayout 集成），支持交互式版图编辑、器件放置、布线可视化 |
| **追赶对象** | Siemens L-Edit（T06） |
| **验收标准** | 1. 新增 `polaris/gui/layout_editor.py` 模块；2. 支持器件拖拽放置/旋转/删除；3. 布线结果实时可视化；4. DRC 错误高亮显示；5. 新增 ≥10 个 GUI 集成测试 |
| **依赖** | R18（阶段 3 完成） |
| **来源** | Siemens L-Edit Photonics [U07]：https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |

### R20（2028-02）：OptoDesigner Design Intent 对齐

> **状态**：❌ 未实现（阶段4，`src/polaris/flow/design_intent.py` 缺失，Glob 核查 2026-06-27，P1 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R20（2028-02） |
| **交付目标** | 对齐 OptoDesigner Design Intent 流程（原理图驱动版图），支持从原理图自动生成版图意图 |
| **追赶对象** | Synopsys OptoDesigner（T03） |
| **验收标准** | 1. 新增 `src/polaris/flow/design_intent.py` 模块；2. 原理图→版图意图自动生成；3. Design Intent 与 PDK 器件映射；4. 新增 ≥8 个 Design Intent 测试 |
| **依赖** | R19（L-Edit GUI） |
| **来源** | Synopsys OptoDesigner [U04]：https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html |

### R21（2028-03）：OptoDesigner 自动布线模块

> **状态**：❌ 未实现（阶段4，`src/polaris/routing/commercial_router.py` 缺失，Glob 核查 2026-06-27，P1 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R21（2028-03） |
| **交付目标** | 对齐 OptoDesigner 自动布线模块（高级连接器 + 任意曲线离散化），PoLaRIS 布线器支持商业级自动布线 |
| **追赶对象** | Synopsys OptoDesigner（T03） |
| **验收标准** | 1. 新增 `src/polaris/routing/commercial_router.py` 模块；2. 高级连接器 ≥5 种（直/弯/锥形/交叉/分支）；3. 任意曲线离散化 1nm 精度；4. 500 器件布线成功率 ≥95%；5. 新增 ≥8 个布线测试 |
| **依赖** | R20（Design Intent） |
| **来源** | Synopsys OptoDesigner [U04] |

### R22（2028-04）：OptoDesigner DRC 模块（18 类规则）

> **状态**：⏳ 待核查（阶段4，18 类 DRC 规则实现状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R22（2028-04） |
| **交付目标** | 对齐 OptoDesigner DRC 模块的 18 类规则（曲线感知），DRC 规则总数从 120+ 扩展至 200+ |
| **追赶对象** | Synopsys OptoDesigner（T03） |
| **验收标准** | 1. 新增 18 类 DRC 规则（宽度/间距/面积/包围/密度/曲线等）；2. DRC 规则总数 ≥200；3. 曲线感知 DRC 检查；4. 新增 ≥10 个 DRC 规则测试 |
| **依赖** | R21（自动布线模块） |
| **来源** | Synopsys OptoDesigner DRC 模块 [U22]：https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html |

### R23（2028-05）：Calibre nmDRC/nmLVS 集成

> **状态**：⏳ 待核查（阶段4，`calibre_interface.py` 实现状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R23（2028-05） |
| **交付目标** | 集成 Calibre nmDRC/nmLVS/xACT（通过 Siemens EDA 接口），支持工业级 DRC/LVS 认证 |
| **追赶对象** | Siemens L-Edit（T06，Calibre 集成） |
| **验收标准** | 1. 新增 `src/polaris/verify/calibre_interface.py` 模块；2. Calibre nmDRC/nmLVS 接口适配；3. 至少 3 个 foundry runset 通过 Calibre 验证；4. 新增 ≥6 个 Calibre 集成测试 |
| **依赖** | R22（OptoDesigner DRC） |
| **来源** | Siemens + Samsung Foundry PIC 验证 [U27] |

### R24（2028-06）：阶段 4 完成 — 商业版图/DRC/布线对齐

> **状态**：⏳ 待核查（阶段4 收尾，因 R19/R20/R21 缺失导致阶段4未完整完成）

| 项目 | 内容 |
|------|------|
| **月份编号** | R24（2028-06） |
| **交付目标** | 阶段 4 收尾，PoLaRIS 商业版图/DRC/布线对齐 L-Edit + OptoDesigner，D01 布局 7→8，D02 布线 7→8，D05 DRC/LVS 8→9，D10 GUI 5→7，综合得分 7.9→8.4 |
| **追赶对象** | Siemens L-Edit + Synopsys OptoDesigner（T06 + T03） |
| **验收标准** | 1. GUI 交互式编辑；2. Design Intent 流程；3. 商业级自动布线；4. 200+ DRC 规则；5. Calibre 集成；6. 阶段 4 验收文档 `docs/roundmap_stage4_report.md` 发布；7. 综合得分自评 8.4/10 |
| **依赖** | R23（Calibre 集成） |
| **来源** | 本路标第 1.3 节 |

---

## 7. 阶段 5：R25-R30 追赶 Luceda IPKISS + Tidy3D（2028-07 ~ 2028-12）

**阶段目标**：全流程+FDTD+逆向设计对齐 IPKISS（CAPHE/15+ foundry PDK）和 Tidy3D（GPU FDTD/伴随优化/拓扑优化），D03 仿真精度 8→9，D04 PDK 8→9，D12 逆向设计 0→8。

### R25（2028-07）：IPKISS CAPHE 电路仿真对齐

> **状态**：⚠️ 代码有，待验收（阶段5，`src/polaris/sim/caphe_backend.py` 存在但未正式合并验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R25（2028-07） |
| **交付目标** | 对齐 IPKISS CAPHE 电路仿真引擎，支持光电联合仿真 + SPICE 导入，PoLaRIS SimLoop 支持 CAPHE 后端 |
| **追赶对象** | Luceda IPKISS（T02） |
| **验收标准** | 1. 新增 `src/polaris/sim/caphe_backend.py` 模块；2. CAPHE 后端与 sax/simphony 交叉验证（误差 < 1e-4）；3. SPICE 网表导入支持；4. 新增 ≥8 个 CAPHE 测试 |
| **依赖** | R24（阶段 4 完成） |
| **来源** | Luceda IPKISS [U03]：https://www.lucedaphotonics.com/luceda-photonics-design-platform |

### R26（2028-08）：IPKISS 15+ foundry PDK 对齐

> **状态**：⏳ 待核查（阶段5，15+ foundry PDK 覆盖状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R26（2028-08） |
| **交付目标** | 对齐 IPKISS 15+ foundry PDK（AIM/AMF/CompoundTek/IHP/SiEPIC/GF Fotonix/SMART/LioniX/Ligentec/Tower/OpenLight/III-V Labs/Cornerstone/VTT/Tyndall），PoLaRIS PDK 覆盖从 12 扩展至 15+ |
| **追赶对象** | Luceda IPKISS（T02） |
| **验收标准** | 1. 新增 ≥3 个 foundry PDK（Tower/OpenLight/Cornerstone）；2. PDK 总数 ≥15；3. 器件库扩展至 200+；4. 新增 ≥10 个 PDK 测试 |
| **依赖** | R25（CAPHE 后端） |
| **来源** | Luceda IPKISS [U03] + Luceda Academy [U29] |

### R27（2028-09）：Tidy3D GPU FDTD 云 API 集成

> **状态**：❌ 未实现（阶段5，`src/polaris/sim/tidy3d_backend.py` 缺失，Glob 核查 2026-06-27，P0 优先级；🚫不参与 GPU 加速部分，仅实现云 API 调用）

| 项目 | 内容 |
|------|------|
| **月份编号** | R27（2028-09） |
| **交付目标** | 集成 Tidy3D 云 API（SaaS 按用量），实现 GPU FDTD 10-5000× 加速，PoLaRIS 支持 FDTD 全波仿真 |
| **追赶对象** | Tidy3D（T04） |
| **验收标准** | 1. 新增 `src/polaris/sim/tidy3d_backend.py` 模块；2. Tidy3D 云 API 调用（需 API key）；3. FDTD 仿真速度比 CPU MEEP 快 ≥100×；4. 亚像素精度验证；5. 新增 ≥8 个 FDTD 测试 |
| **依赖** | R26（IPKISS PDK） |
| **来源** | Tidy3D [U05]：https://www.flexcompute.com/tidy3d/ + Tidy3D Changelog [U28] |

### R28（2028-10）：Tidy3D 伴随优化（逆向设计）

> **状态**：❌ 未实现（阶段5，`src/polaris/inverse/adjoint_optimizer.py` 缺失，Glob 核查 2026-06-27，P0 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R28（2028-10） |
| **交付目标** | 集成 Tidy3D 伴随优化（adjoint optimization），实现自动微分驱动的器件逆向设计，D12 逆向设计从 0 提升至 5/10 |
| **追赶对象** | Tidy3D（T04，伴随优化） |
| **验收标准** | 1. 新增 `src/polaris/inverse/adjoint_optimizer.py` 模块；2. 伴随优化收敛（≥3 个标准器件示例：MMI/光栅耦合器/模式转换器）；3. 优化后器件性能提升 ≥10%；4. 新增 ≥8 个逆向设计测试 |
| **依赖** | R27（Tidy3D FDTD） |
| **来源** | Tidy3D 伴随优化文档 [U09]：https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/Autograd1Intro.html |

### R29（2028-11）：Tidy3D 拓扑优化 + Level Set

> **状态**：⏳ 待核查（阶段5，`topology_optimizer.py` 实现状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R29（2028-11） |
| **交付目标** | 集成 Tidy3D 拓扑优化 + Level Set + PSO/GA，实现全套逆向设计能力，D12 逆向设计从 5 提升至 8/10 |
| **追赶对象** | Tidy3D（T04，拓扑/PSO/GA） |
| **验收标准** | 1. 新增 `src/polaris/inverse/topology_optimizer.py` 模块；2. 拓扑优化 + Level Set 实现；3. PSO/GA 全局优化；4. ≥3 个拓扑优化示例；5. 新增 ≥8 个拓扑优化测试 |
| **依赖** | R28（伴随优化） |
| **来源** | Tidy3D [U05][U09] |

### R30（2028-12）：阶段 5 完成 — 全流程+FDTD+逆向设计对齐

> **状态**：⏳ 待核查（阶段5 收尾，因 R27/R28 缺失导致阶段5未完整完成）

| 项目 | 内容 |
|------|------|
| **月份编号** | R30（2028-12） |
| **交付目标** | 阶段 5 收尾，PoLaRIS 全流程+FDTD+逆向设计对齐 IPKISS + Tidy3D，D03 仿真精度 8→9，D04 PDK 8→9，D12 逆向设计 0→8，D11 光电协同 7→8，综合得分 8.4→8.8 |
| **追赶对象** | Luceda IPKISS + Tidy3D（T02 + T04） |
| **验收标准** | 1. CAPHE 后端完整；2. 15+ foundry PDK；3. GPU FDTD 云端；4. 全套逆向设计（伴随/拓扑/PSO/GA）；5. 阶段 5 验收文档 `docs/roundmap_stage5_report.md` 发布；6. 综合得分自评 8.8/10 |
| **依赖** | R29（拓扑优化） |
| **来源** | 本路标第 1.3 节 |

---

## 8. 阶段 6：R31-R36 追赶 Ansys Lumerical + AlphaChip（2029-01 ~ 2029-06）

**阶段目标**：顶级商业+AI 对齐 Lumerical（FDTD/MODE/INTERCONNECT/CML/量子）和 AlphaChip（edge-GNN/PPO/预训练/分布式），D01 布局 8→9，D07 AI/ML 8→10，D09 规模 8→9，D13 量子 2→7，综合得分 8.8→9.2。

### R31（2029-01）：Lumerical FDTD 3D 全波仿真

> **状态**：❌ 未实现（阶段6，`src/polaris/sim/lumerical_fdtd.py` 缺失，Glob 核查 2026-06-27，P2 优先级；🚫不参与 GPU 加速部分）

| 项目 | 内容 |
|------|------|
| **月份编号** | R31（2029-01） |
| **交付目标** | 实现 Lumerical 级 FDTD 3D 全波仿真（多物理场 + GPU 加速），对齐 Lumerical FDTD 精度 |
| **追赶对象** | Ansys Lumerical（T01，FDTD） |
| **验收标准** | 1. 新增 `src/polaris/sim/lumerical_fdtd.py` 模块；2. 3D FDTD 多物理场（热/应力/电荷）；3. GPU 加速 ≥10×；4. 与 Tidy3D 交叉验证（误差 < 1e-3）；5. 新增 ≥10 个 FDTD 测试 |
| **依赖** | R30（阶段 5 完成） |
| **来源** | Ansys Lumerical [U01]：https://www.ansys.com/products/optics/interconnect |

### R32（2029-02）：Lumerical INTERCONNECT 时频域仿真

> **状态**：❌ 未实现（阶段6，`src/polaris/sim/interconnect_backend.py` 缺失，Glob 核查 2026-06-27，P2 优先级）

| 项目 | 内容 |
|------|------|
| **月份编号** | R32（2029-02） |
| **交付目标** | 对齐 Lumerical INTERCONNECT 时频域仿真，支持大规模 PIC 时频域联合分析 |
| **追赶对象** | Ansys Lumerical（T01，INTERCONNECT） |
| **验收标准** | 1. 新增 `src/polaris/sim/interconnect_backend.py` 模块；2. 时频域联合仿真；3. 1000 器件时频域仿真 < 5 分钟；4. 新增 ≥8 个 INTERCONNECT 测试 |
| **依赖** | R31（FDTD 3D） |
| **来源** | Ansys Lumerical 2026 R1 [U02] |

### R33（2029-03）：Lumerical CML Compiler PDK + 量子电路

> **状态**：⏳ 待核查（阶段6，`cml_compiler.py` + 量子电路实现状态未正式验收）

| 项目 | 内容 |
|------|------|
| **月份编号** | R33（2029-03） |
| **交付目标** | 对齐 Lumerical CML Compiler PDK 编译流程，并实现量子电路仿真器（QKD/量子门），D13 量子光子从 2 提升至 5/10 |
| **追赶对象** | Ansys Lumerical（T01，CML + 量子） |
| **验收标准** | 1. 新增 `src/polaris/sim/cml_compiler.py` 模块；2. CML 编译流程（S 参数→CML 模型）；3. 量子电路仿真器（≥3 个量子门示例）；4. QKD 示例；5. 新增 ≥10 个量子/CML 测试 |
| **依赖** | R32（INTERCONNECT） |
| **来源** | Ansys Lumerical [U01] |

### R34（2029-04）：AlphaChip Edge-GNN 实现

> **状态**：❌ 未实现（阶段6，`src/polaris/rl/edge_gnn.py` 缺失，Glob 核查 2026-06-27，P2 优先级；🚫不参与 GPU 分布式训练部分）

| 项目 | 内容 |
|------|------|
| **月份编号** | R34（2029-04） |
| **交付目标** | 实现 AlphaChip 风格的 Edge-GNN（基于边的图神经网络），替换现有 R-GCN，D01 布局算法从 8 提升至 9/10 |
| **追赶对象** | AlphaChip（T13，Edge-GNN） |
| **验收标准** | 1. 新增 `src/polaris/rl/edge_gnn.py` 模块；2. Edge-GNN 在 Ariane RISC-V benchmark 上 HPWL 优于 R-GCN ≥5%；3. 与 Circuit Training 开源代码交叉验证；4. 新增 ≥10 个 Edge-GNN 测试 |
| **依赖** | R33（CML + 量子） |
| **来源** | AlphaChip [U18]：https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ + Circuit Training [U18] |

### R35（2029-05）：AlphaChip 预训练 + 分布式训练

> **状态**：❌ 未实现（阶段6，`src/polaris/rl/pretraining.py` 缺失，Glob 核查 2026-06-27，P2 优先级；🚫不参与 GPU 多卡分布式部分，仅 CPU/单机实现）

| 项目 | 内容 |
|------|------|
| **月份编号** | R35（2029-05） |
| **交付目标** | 实现 AlphaChip 风格的预训练 + 微调范式 + 分布式 PPO 训练（Ray），D07 AI/ML 从 8 提升至 10/10，D09 规模从 8 提升至 9/10 |
| **追赶对象** | AlphaChip（T13，预训练 + 分布式） |
| **验收标准** | 1. 新增 `src/polaris/rl/pretraining.py` 模块；2. 100+ PIC 块预训练数据集；3. 预训练→微调速度提升 ≥3×；4. Ray 分布式 PPO（≥4 worker）；5. 5000 器件规模验证；6. 新增 ≥10 个预训练/分布式测试 |
| **依赖** | R34（Edge-GNN） |
| **来源** | AlphaChip [U18][U19] + Circuit Training [U18] |

### R36（2029-06）：阶段 6 完成 — 顶级商业+AI 对齐

> **状态**：⏳ 待核查（阶段6 收尾，因 R31/R32/R34/R35 缺失导致阶段6未完整完成；当前真实综合得分 7.88/10，非 9.5 虚假声明）

| 项目 | 内容 |
|------|------|
| **月份编号** | R36（2029-06） |
| **交付目标** | 阶段 6 收尾，PoLaRIS 顶级商业+AI 对齐 Lumerical + AlphaChip，D01 布局 8→9，D07 AI/ML 8→10，D09 规模 8→9，D13 量子 2→7，D03 仿真精度 9→10，综合得分 8.8→9.2，超越行业最高 9.0 |
| **追赶对象** | Ansys Lumerical + AlphaChip（T01 + T13） |
| **验收标准** | 1. FDTD 3D 全波 + INTERCONNECT 时频域；2. CML Compiler + 量子电路；3. Edge-GNN + 预训练 + 分布式；4. 5000 器件规模；5. 阶段 6 验收文档 `docs/roundmap_stage6_report.md` 发布；6. 综合得分自评 9.2/10（超越行业最高 9.0）；7. 所有 15 维度达到或超越最先进工具 |
| **依赖** | R35（预训练 + 分布式） |
| **来源** | 本路标第 1.3 节 |

---

## 9. 验收标准汇总

### 9.1 每月可验证标准汇总表

| 月份 | 交付目标 | 验收标准（可验证） | 测试数目标 |
|------|----------|---------------------|------------|
| R1 | sax S 参数格式兼容 | sax_export.py + 10 模型导出 + 5 测试 | +5 |
| R2 | sax 子网络增长 | subnetwork.py + 500 器件 < 10s + 8 测试 | +8 |
| R3 | simphony 级联对齐 | simphony_backend.py + 交叉验证 + 6 测试 | +6 |
| R4 | JAX 加速 | jax_backend.py + 3× 加速 + autograd + 6 测试 | +6 |
| R5 | 电路仿真 benchmark | benchmark 脚本 + 10 电路 + 5 测试 | +5 |
| R6 | 阶段 1 完成 | 三后端互操作 + 验收文档 | +0 |
| R7 | gdsfactory PDK 桥接 | 43+ PDK + 150 器件 + 10 测试 | +10 |
| R8 | KLayout DRC 深度集成 | 3 模式 + 120 规则 + 8 测试 | +8 |
| R9 | KLayout LVS 增强 | 层次化 LVS + 8 测试 | +8 |
| R10 | gdsfactory 布线策略 | 5 策略 + 8 测试 | +8 |
| R11 | GDS 1nm 曲线精度 | 1nm + 贝塞尔 + 6 测试 | +6 |
| R12 | 阶段 2 完成 | 12 foundry + 验收文档 | +0 |
| R13 | VPIphotonics 系统级 | system_level.py + 3 链路 + 8 测试 | +8 |
| R14 | VPItoolkit PDK | 3 foundry 模型 + 6 测试 | +6 |
| R15 | PICWave 时域 | picwave_backend.py + 非线性 + 8 测试 | +8 |
| R16 | FIMMPROP EME | eme_backend.py + 5 结构 + 6 测试 | +6 |
| R17 | 光电协同仿真 | photoelectric_cosim.py + Verilog-A + 8 测试 | +8 |
| R18 | 阶段 3 完成 | 三后端 + 光电协同 + 验收文档 | +0 |
| R19 | L-Edit GUI | layout_editor.py + 10 测试 | +10 |
| R20 | OptoDesigner Design Intent | design_intent.py + 8 测试 | +8 |
| R21 | OptoDesigner 自动布线 | commercial_router.py + 95% 成功率 + 8 测试 | +8 |
| R22 | OptoDesigner DRC 18 类 | 200 规则 + 曲线感知 + 10 测试 | +10 |
| R23 | Calibre 集成 | calibre_interface.py + 3 foundry + 6 测试 | +6 |
| R24 | 阶段 4 完成 | GUI + Design Intent + 验收文档 | +0 |
| R25 | IPKISS CAPHE 后端 | caphe_backend.py + SPICE 导入 + 8 测试 | +8 |
| R26 | IPKISS 15+ foundry PDK | 15 PDK + 200 器件 + 10 测试 | +10 |
| R27 | Tidy3D GPU FDTD | tidy3d_backend.py + 100× 加速 + 8 测试 | +8 |
| R28 | Tidy3D 伴随优化 | adjoint_optimizer.py + 3 器件 + 8 测试 | +8 |
| R29 | Tidy3D 拓扑优化 | topology_optimizer.py + 3 示例 + 8 测试 | +8 |
| R30 | 阶段 5 完成 | CAPHE + FDTD + 逆向设计 + 验收文档 | +0 |
| R31 | Lumerical FDTD 3D | lumerical_fdtd.py + 多物理场 + 10 测试 | +10 |
| R32 | INTERCONNECT 时频域 | interconnect_backend.py + 1000 器件 + 8 测试 | +8 |
| R33 | CML Compiler + 量子 | cml_compiler.py + 量子门 + 10 测试 | +10 |
| R34 | AlphaChip Edge-GNN | edge_gnn.py + Ariane + 10 测试 | +10 |
| R35 | 预训练 + 分布式 | pretraining.py + Ray + 5000 器件 + 10 测试 | +10 |
| R36 | 阶段 6 完成 | 全维度超越 + 验收文档 | +0 |

### 9.2 累计测试数预测

| 阶段 | 起始测试数 | 新增测试数 | 结束测试数 |
|------|------------|------------|------------|
| R0（基线） | - | - | 2330 |
| R1-R6（阶段 1） | 2330 | +30 | 2360 |
| R7-R12（阶段 2） | 2360 | +40 | 2400 |
| R13-R18（阶段 3） | 2400 | +36 | 2436 |
| R19-R24（阶段 4） | 2436 | +42 | 2478 |
| R25-R30（阶段 5） | 2478 | +42 | 2520 |
| R31-R36（阶段 6） | 2520 | +48 | 2568 |

---

## 10. 风险与依赖

### 10.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Tidy3D 云 API 费用超预算 | 中 | 高（R27-R29 阻塞） | 预留预算 + 开源 MEEP 备选（GPL） |
| Calibre 集成需 Siemens 授权 | 高 | 高（R23 阻塞） | 开源 KLayout DRC 替代 + 申请学术授权 |
| Edge-GNN 训练需 GPU | 高 | 中（R34-R35 受限） | 云 GPU 租用 + Colab 免费 GPU |
| 5000 器件规模内存不足 | 中 | 中（R35 阻塞） | 子图采样 + 分布式训练 |
| IPKISS PDK 需 NDA | 高 | 中（R26 部分阻塞） | 优先开源 PDK + 学术合作 |
| Lumerical 级 FDTD 精度难达 | 高 | 高（R31 阻塞） | 集成 Tidy3D/MEEP 而非自研 |

### 10.2 资源依赖

| 依赖 | 需求 | 获取方式 |
|------|------|----------|
| Tidy3D 云 API key | R27-R29 | Flexcompute 学术计划 |
| Calibre 学术授权 | R23 | Siemens 学术计划 |
| GPU 训练资源 | R34-R35 | 云 GPU + Colab + 学术合作 |
| foundry PDK NDA | R26/R14 | AIM/AMF/CompoundTek 学术合作 |
| 预训练数据集 | R35 | 自建 100+ PIC 块 + 公开数据集 |

### 10.3 外部合作依赖

| 合作方 | 合作内容 | 阶段 |
|--------|----------|------|
| Flexcompute | Tidy3D 云 API 学术计划 | 阶段 5 |
| Siemens EDA | Calibre 学术授权 | 阶段 4 |
| Luceda Photonics | IPKISS PDK 学术合作 | 阶段 5 |
| Ansys | Lumerical 学术合作 | 阶段 6 |
| ASU 课题组 | Apollo/LiDAR benchmark 合作 | 全程 |
| UToronto | PhIDO LLM Agent 合作 | 阶段 6 |
| IMEC/AMF/AIM | foundry PDK NDA | 阶段 2-5 |

---

## 11. 学术诚信声明

1. **基线真实**：本路标基线（第 94 轮，2026-06-22）基于真实状态：2330 测试/0 警告/81 器件/9 foundry/3 benchmark/综合 6.1/10，无造假。
2. **追赶对象真实**：所有追赶对象（13 个工具）的功能清单来自网络检索（2026-06-22），详见 `docs/commercial_tools_feature_matrix.md`。
3. **目标合理**：每月交付目标基于对标工具的真实功能，不夸大不缩小。
4. **验收可验证**：每月验收标准包含具体的代码模块、测试数量、性能指标，可独立验证。
5. **风险透明**：技术风险与资源依赖如实列出，不隐瞒。
6. **禁止 fall-back**：本路标不包含任何假数据或 fall-back 设计，所有交付目标须真实实现。
7. **来源标注**：所有追赶对象的功能项来源 URL 见 `docs/commercial_tools_feature_matrix.md` 第 6 节。

---

## 12. 参考文档

- `docs/commercial_tools_feature_matrix.md`（v1.0，2026-06-22）：13 工具 × 15 维度功能对比矩阵
- `docs/commercial_gap_analysis.md`（2026-06-21）：PoLaRIS 与商业工具差距分析
- `docs/industry_alignment_roadmap.md`（2026-06-20）：业界标准对齐路线图
- `操作记录.md` 第 93 轮（2026-06-22）：Apollo/LiDAR benchmark 器件插入损耗参数补全

---

**文档结束**
