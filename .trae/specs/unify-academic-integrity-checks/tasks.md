# Tasks

## 阶段 1: 文档骨架建立

- [x] Task 1: 创建 `/workspace/docs/学术诚信检查.md` 骨架（文件头 + §1 版本日志 + §2 项目总览 + §3-§6 占位）
  - [x] SubTask 1.1: 写文件头（文档说明 + v3.0 版本号 + 日期 2026-06-28）
  - [x] SubTask 1.2: 写 §1 版本日志（v3.0 条目，标注本次范围=全项目首次统一）
  - [x] SubTask 1.3: 写 §2 项目总览（22 子包 / 357 文件 / 120,692 行统计表）

## 阶段 2: 历史发现合并

- [ ] Task 2: 合并 4 个旧文档的关键发现到 §5 Bug 与修复历史
  - [ ] SubTask 2.1: 提取 `20260627-mvp技术诚信学术审核.md` 的 bug 清单
  - [ ] SubTask 2.2: 提取 `academic_integrity_audit.md` v1.0/v2.0 的 bug 清单
  - [ ] SubTask 2.3: 提取 `academic_integrity_audit_v2.md` 的 43 聚类模块评分
  - [ ] SubTask 2.4: 提取 `devplan_audit_report.md` 的设计-代码分歧
  - [ ] SubTask 2.5: 去重 + 按版本号归档到 §5

## 阶段 3: 全项目逐子包审查（并行 Sub-Agent）

- [ ] Task 3: 审查 sim/ 子包（161 文件 58,325 行，分 12 个子目录）
  - [ ] SubTask 3.1: sim/fdtd/（Yee/CPML/TFSF/色散/子像素）
  - [ ] SubTask 3.2: sim/fde/ + sim/eme/ + sim/rcwa/ + sim/bpm/（模式求解器）
  - [ ] SubTask 3.3: sim/fdfd/ + sim/varfdtd/ + sim/fetd/（频域求解器）
  - [ ] SubTask 3.4: sim/ddm/ + sim/heat/ + sim/multiphysics/（多物理场）
  - [x] SubTask 3.5: sim/quantum_*.py（6 个量子模块）— 已审查 6 模块，修复 quantum_lossy.py R02 学术诚信违规（García-Patrón 论文年份/定理修正）
  - [x] SubTask 3.6: sim/ 顶层（lumerical_*/tidy3d_*/caphe_*/interconnect_*/cml_*）— 已审查 17 模块，修复 lumerical_mode/interconnect/charge 11 处 fall-back + charge R02 Soref 1987 溯源 + tidy3d_integration R04 合规声明
  - [ ] SubTask 3.7: sim/ 其他（verilog_a/mna_spice/monte_carlo/layout_aware 等）
- [ ] Task 4: 审查 pdk/ 子包（46 文件 13,167 行）
  - [ ] SubTask 4.1: pdk/ 顶层（catalog/foundry_*/module_library/awg_ip_materials 等）
  - [ ] SubTask 4.2: pdk/soi/ + pdk/sin/ + pdk/inp/（材料平台库）
  - [ ] SubTask 4.3: pdk/optodesigner_*.py（7 个 OptoDesigner 集成）
- [x] Task 5: 审查 trainer/ + rl/ 子包（38 文件 10,723 行，AI/ML 核心）
  - [x] SubTask 5.1: trainer/ppo*.py + bc.py + gnn_ppo.py（PPO/BC/GNN-PPO）— v3.1 完成，PPO-Clip 公式 4 文件一致 ✅
  - [x] SubTask 5.2: trainer/pretrain*.py + transfer_learning*.py（预训练/迁移学习）— v3.1 完成，EWC/课程学习/GraphMAE 文献溯源 ✅
  - [x] SubTask 5.3: rl/alpha_chip*.py + edge_gnn.py + pretraining.py（AlphaChip 对齐）— v3.1 完成，R-GCN+GAT+GlobalAttention 3 创新点验证 ✅，修复 Bug #v3.1-1（_build_action_mask 边界 +1 不一致）
- [x] Task 6: 审查 router/ + engine/ 子包（37 文件 13,990 行，布局布线）
  - [x] SubTask 6.1: router/curvy_*.py + advanced_connectors.py（曲线布线）
  - [x] SubTask 6.2: router/global_router.py + hybrid_router.py + multilayer.py（全局布线）
  - [x] SubTask 6.3: engine/gnn.py + alphachip_gnn.py + floorplan_env.py（布局引擎）
- [ ] Task 7: 审查 verification/ + verify/ + inverse/ 子包（7 文件 3,246 行）
  - [ ] SubTask 7.1: verification/drc_curvilinear_18rules.py + statistical_yield.py
  - [ ] SubTask 7.2: verify/calibre_interface.py
  - [ ] SubTask 7.3: inverse/adjoint_optimizer.py + topology_adjoint_optimizer.py
- [ ] Task 8: 审查 quantum/ + device/ + ai/ 子包（5 文件 2,615 行）
  - [ ] SubTask 8.1: quantum/quantum_circuit_distributed.py（已审，迁移结论）
  - [ ] SubTask 8.2: device/tcad_thermal_package.py（已审，迁移结论）
  - [ ] SubTask 8.3: ai/inverse_design.py
- [ ] Task 9: 审查 flow/ + pipeline/ + data/ 子包（39 文件 12,220 行）
  - [ ] SubTask 9.1: flow/stage*.py + scheduler.py + job.py（设计流程）
  - [ ] SubTask 9.2: pipeline/integrated.py + curvy_router.py + training.py
  - [ ] SubTask 9.3: data/dataset_generator.py + benchmark_*.py + specs.py
- [ ] Task 10: 审查 io/ + nn/ + gui/ + web/ + platform/ + eval/ + system/ 子包（23 文件 6,692 行）
  - [ ] SubTask 10.1: io/（GDS/OASIS/CIF/DXF/Gerber/LEF-DEF/ODB++/OpenAccess）
  - [ ] SubTask 10.2: nn/ + gui/ + web/（神经网络/GUI/Web）
  - [ ] SubTask 10.3: platform/ + eval/ + system/（教育/评估/系统）

## 阶段 4: 关键算法溯源

- [ ] Task 11: 写 §4 关键算法与公式溯源
  - [ ] SubTask 11.1: 数值方法（FDTD Yee 1966 / CPML Gedney 1996 / EME/RCWA/BPM）
  - [ ] SubTask 11.2: 量子算法（KLM Nature 2001 / HOM PRL 1987 / BB84 1984 / 玻色采样）
  - [ ] SubTask 11.3: AI/ML 算法（PPO Schulman 2017 / GAE 2016 / Adam 2015 / AlphaChip Nature 2021）
  - [ ] SubTask 11.4: 物理参数（CODATA 2018 / Si 折射率 / 等离子体色散 Soref 1987）

## 阶段 5: Bug 修复 + 文档归档

- [ ] Task 12: 修复审查中发现的新 Bug（如有）
  - [ ] SubTask 12.1: 记录每个 Bug 根因 + 修复方案 + 回归测试
  - [ ] SubTask 12.2: 同步修复到 §5 Bug 历史
- [ ] Task 13: 归档 4 个旧学术审核文档
  - [ ] SubTask 13.1: 在每个旧文档顶部追加归档声明
  - [ ] SubTask 13.2: 不删除旧文档内容（保留历史可追溯）
- [ ] Task 14: 写 §6 学术诚信声明 + 更新版本日志 v3.0 最终数据
  - [ ] SubTask 14.1: R02/R03/R05/R07 合规声明
  - [ ] SubTask 14.2: 总 bug 数 / 修复数 / 数据修正统计

## 阶段 6: 验证与提交

- [ ] Task 15: 全文档校验
  - [ ] SubTask 15.1: 检查所有子包是否覆盖（22/22）
  - [ ] SubTask 15.2: 检查所有公式溯源是否完整
  - [ ] SubTask 15.3: 检查无造假数据（所有数字真实可验证）
- [ ] Task 16: 提交代码 + 推送 main
  - [ ] SubTask 16.1: git add docs/学术诚信检查.md + 旧文档归档声明 + bug 修复
  - [ ] SubTask 16.2: commit + push origin main
- [ ] Task 17: 更新操作记录.md
  - [ ] SubTask 17.1: 追加本轮学术诚信统一审查记录

# Task Dependencies

- Task 1 → Task 2（先有骨架才能合并内容）
- Task 2 → Task 3-10（合并历史后开始新审查）
- Task 3-10 可并行（不同子包独立）
- Task 3-10 → Task 11（关键算法溯源依赖子包审查结论）
- Task 11 → Task 12（先溯源才发现新 bug）
- Task 12 → Task 13-14（修复后归档+声明）
- Task 13-14 → Task 15（验证）
- Task 15 → Task 16-17（提交）
