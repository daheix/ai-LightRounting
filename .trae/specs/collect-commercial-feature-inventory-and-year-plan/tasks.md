# Tasks

## 阶段一：商业产品功能点级清单收集（T01-T13）

- [ ] Task 1: 调研 Ansys Lumerical 功能点（T01）
  - [ ] SubTask 1.1: WebSearch/WebFetch Ansys Lumerical 官网（FDTD/MODE/INTERCONNECT/CML Compiler 四模块）
  - [ ] SubTask 1.2: 整理 FDTD 模块功能点（亚像素平滑/CPML/色散材料/各向异性/非线性/分布式 GPU/伴随优化/脚本 API 等）
  - [ ] SubTask 1.3: 整理 MODE 模块功能点（EME/有限差分/模式求解/扫描/重叠积分等）
  - [ ] SubTask 1.4: 整理 INTERCONNECT 模块功能点（时域/频域/光学逻辑门/量子电路/PRBS/Co-Sim 等）
  - [ ] SubTask 1.5: 整理 CML Compiler 功能点（PDK 编译/参数提取/模型验证等）
  - [ ] SubTask 1.6: 生成 `docs/commercial_feature_inventory/T01_lumerical.md`

- [ ] Task 2: 调研 Luceda IPKISS 功能点（T02）
  - [ ] SubTask 2.1: WebFetch Luceda IPKISS 官网（IPKISS 核心/Canvas/Design Flow）
  - [ ] SubTask 2.2: 整理功能点（参数化器件/智能布线/连接器/DRC/网表提取/LVS/GDS 导出/CAPHE 仿真/多 foundry PDK）
  - [ ] SubTask 2.3: 生成 `docs/commercial_feature_inventory/T02_ipkiss.md`

- [ ] Task 3: 调研 Synopsys OptoDesigner 功能点（T03）
  - [ ] SubTask 3.1: WebFetch Synopsys OptoDesigner 官网
  - [ ] SubTask 3.2: 整理功能点（Design Intent/自动布线/高级连接器/DRC 18 类规则/曲线感知/GDS 导出/多 foundry）
  - [ ] SubTask 3.3: 生成 `docs/commercial_feature_inventory/T03_optodesigner.md`

- [ ] Task 4: 调研 Flexcompute Tidy3D 功能点（T04）
  - [ ] SubTask 4.1: WebFetch Tidy3D 官网
  - [ ] SubTask 4.2: 整理功能点（GPU FDTD/亚像素/伴随优化/PSO/GA/拓扑优化/autograd/Web GUI/材料库）
  - [ ] SubTask 4.3: 生成 `docs/commercial_feature_inventory/T04_tidy3d.md`

- [ ] Task 5: 调研 VPIphotonics 功能点（T05）
  - [ ] SubTask 5.1: WebFetch VPIphotonics 官网（Design Suite/Component Maker/Transmission Maker）
  - [ ] SubTask 5.2: 整理功能点（时域/频域/TLM/BPM/非线性/光电协同/ADS 联合/多 foundry）
  - [ ] SubTask 5.3: 生成 `docs/commercial_feature_inventory/T05_vpiphotonics.md`

- [ ] Task 6: 调研 Siemens L-Edit Photonics 功能点（T06）
  - [ ] SubTask 6.1: WebFetch Siemens L-Edit Photonics 官网
  - [ ] SubTask 6.2: 整理功能点（版图编辑/GPIC PDK/SDL/Calibre 集成/GDSII/OASIS/曲线多边形/S-Edit）
  - [ ] SubTask 6.3: 生成 `docs/commercial_feature_inventory/T06_ledit_photonics.md`

- [ ] Task 7: 调研 Photon Design 功能点（T07）
  - [ ] SubTask 7.1: WebFetch Photon Design 官网（Aspic/FIMMPROP/OmniSim/PICWave/Kallistos）
  - [ ] SubTask 7.2: 整理功能点（FIMMPROP EME/OmniSim FDTD/FETD/PICWave 时域/Kallistos 优化）
  - [ ] SubTask 7.3: 生成 `docs/commercial_feature_inventory/T07_photon_design.md`

- [ ] Task 8: 调研 gdsfactory 功能点（T08）
  - [ ] SubTask 8.1: WebFetch gdsfactory GitHub 官方文档
  - [ ] SubTask 8.2: 整理功能点（参数化器件/YAML 层次化/route_fiber_array/get_bundle/KLayout DRC/GDSII/OASIS/43+ PDK/量子组件）
  - [ ] SubTask 8.3: 生成 `docs/commercial_feature_inventory/T08_gdsfactory.md`

- [ ] Task 9: 调研 KLayout 功能点（T09）
  - [ ] SubTask 9.1: WebFetch KLayout 官网
  - [ ] SubTask 9.2: 整理功能点（版图查看/编辑/DRC/LVS/tiled/hierarchical/deep mode/GDSII/OASIS/DXF/CIF/Gerber/DRM）
  - [ ] SubTask 9.3: 生成 `docs/commercial_feature_inventory/T09_klayout.md`

- [ ] Task 10: 调研 sax 功能点（T10）
  - [ ] SubTask 10.1: WebFetch sax GitHub
  - [ ] SubTask 10.2: 整理功能点（JAX S 参数/子网络增长/autograd 逆向/cocotb 联合/gdsfactory 集成）
  - [ ] SubTask 10.3: 生成 `docs/commercial_feature_inventory/T10_sax.md`

- [ ] Task 11: 调研 simphony 功能点（T11）
  - [ ] SubTask 11.1: WebFetch simphony GitHub
  - [ ] SubTask 11.2: 整理功能点（S 参数级联/SiEPIC 兼容/子电路/频率扫描/比 Lumerical 快 20×）
  - [ ] SubTask 11.3: 生成 `docs/commercial_feature_inventory/T11_simphony.md`

- [ ] Task 12: 调研 Cadence Innovus + Synopsys ICC2 功能点（T12）
  - [ ] SubTask 12.1: WebFetch Cadence Innovus 官网 + Synopsys ICC2 官网
  - [ ] SubTask 12.2: 整理 Innovus 功能点（GigaPlace/GigaOpt/PRO 全局-详细/ML DRC 闭合/AI 驱动 PPA/3nm 2nm）
  - [ ] SubTask 12.3: 整理 ICC2 功能点（多目标全局布局/Zroute/ML 拥塞/PrimeTime/PrimePower）
  - [ ] SubTask 12.4: 生成 `docs/commercial_feature_inventory/T12_cadence_synopsys.md`

- [ ] Task 13: 调研 Google AlphaChip + Circuit Training 功能点（T13）
  - [ ] SubTask 13.1: WebFetch AlphaChip Nature 论文 + Circuit Training GitHub
  - [ ] SubTask 13.2: 整理功能点（Edge-GNN/PPO/预训练/分布式/TPU v5-v7/Mediatek Dimensity）
  - [ ] SubTask 13.3: 生成 `docs/commercial_feature_inventory/T13_alphachip.md`

## 阶段二：PoLaRIS 自身功能点级清单

- [x] Task 14: 扫描 PoLaRIS 代码库生成功能点清单
  - [x] SubTask 14.1: 扫描 `src/polaris/` 所有模块（data/engine/pipeline/sim/nn/trainer/foundry/gds/quantum）
  - [x] SubTask 14.2: 扫描 `examples/e2e_showcase/stages/` 全流程 7 阶段
  - [x] SubTask 14.3: 扫描 `tests/` 统计测试覆盖（139 文件 / 3346 测试函数）
  - [x] SubTask 14.4: 每个功能点标注实现位置（文件:行号）+ 成熟度（生产可用/实验性/原型）
  - [x] SubTask 14.5: 生成 `docs/polaris_feature_inventory.md`

## 阶段三：全量差距分析

- [ ] Task 15: 生成全量逐点差距分析
  - [ ] SubTask 15.1: 对 T01-T13 每个功能点，标注 PoLaRIS 状态（✅/⚠️/❌/🚫）
  - [ ] SubTask 15.2: 统计每个工具的覆盖率（已有/部分/缺失/不适用 百分比）
  - [ ] SubTask 15.3: 列出 PoLaRIS 独家功能点（商业工具都没有的）
  - [ ] SubTask 15.4: 按优先级排序缺失功能点（P0/P1/P2/P3）
  - [ ] SubTask 15.5: 生成 `docs/feature_gap_full_analysis.md`

## 阶段四：一年开发计划（2026-06 到 2027-05）

- [ ] Task 16: 制定 12 个月开发计划
  - [ ] SubTask 16.1: 2026-06 计划（基线对齐月，固化已有能力）
  - [ ] SubTask 16.2: 2026-07 计划（P0 阻断级功能点）
  - [ ] SubTask 16.3: 2026-08 计划
  - [ ] SubTask 16.4: 2026-09 计划
  - [ ] SubTask 16.5: 2026-10 计划
  - [ ] SubTask 16.6: 2026-11 计划
  - [ ] SubTask 16.7: 2026-12 计划
  - [ ] SubTask 16.8: 2027-01 计划
  - [ ] SubTask 16.9: 2027-02 计划
  - [ ] SubTask 16.10: 2027-03 计划
  - [ ] SubTask 16.11: 2027-04 计划
  - [ ] SubTask 16.12: 2027-05 计划（一年验收月）
  - [ ] SubTask 16.13: 生成 `docs/year_plan_2026_06_2027_05.md`

## 阶段五：结果展示与记录

- [ ] Task 17: 汇总结果展示给用户
  - [ ] SubTask 17.1: 生成汇总报告（13 工具功能点总数、PoLaRIS 覆盖率、12 月计划摘要）
  - [ ] SubTask 17.2: 更新 `操作记录.md`
  - [ ] SubTask 17.3: 提交代码合并 main 分支

# Task Dependencies

- Task 14（PoLaRIS 清单）依赖 Task 1-13 完成（需要商业清单作为对比基准）
- Task 15（差距分析）依赖 Task 14 + Task 1-13 全部完成
- Task 16（一年计划）依赖 Task 15 完成
- Task 17（结果展示）依赖 Task 16 完成
- Task 1-13 之间可并行（13 个独立产品调研）
