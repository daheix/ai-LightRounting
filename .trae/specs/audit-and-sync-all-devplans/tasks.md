# Tasks — 开发计划审核与文档同步更新

> 依据：`spec.md` 审计发现（13 核心模块缺失 + 4 份虚假报告 + Sprint 0-7 未启动）
> 规则：R01 方案检索 / R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必须修复 / R07 操作记录 / R08 代码提交

---

## 阶段一：审计报告与文档同步（P0，立即执行）

- [ ] Task 1: 生成真实状态审计报告
  - [ ] SubTask 1.1: 编写 `docs/devplan_audit_report.md`，记录 16 spec + 36 路标 + Sprint 0-7 + 年度计划的真实完成状态
  - [ ] SubTask 1.2: 记录 13 缺失模块清单 + 4 份虚假报告清单 + 代码与文档不一致清单
  - [ ] SubTask 1.3: 所有声明附 git log / 文件路径 / 测试结果作为证据

- [ ] Task 2: 修正 4 份虚假验收报告（R02 学术诚信）
  - [ ] SubTask 2.1: 重写 `docs/roundmap_final_report.md`，得分从 9.5 修正为 7.88，标注 13 模块缺失
  - [ ] SubTask 2.2: 修正 `docs/roundmap_stage3_report.md`，标注 R15/R16/R17 未实现
  - [ ] SubTask 2.3: 修正 `docs/roundmap_stage4_report.md`，标注 R19/R20/R21 未实现
  - [ ] SubTask 2.4: 修正 `docs/roundmap_stage5_report.md`，标注 R27/R28 未实现
  - [ ] SubTask 2.5: 保留 `docs/roundmap/R36_acceptance_report.md`（7.88 分较真实），补充代码验证

- [ ] Task 3: 同步核心文档反映真实状态
  - [ ] SubTask 3.1: 更新 `AGENTS.md` §11 当前进度（R01-R08 代码有/13 模块缺失）
  - [ ] SubTask 3.2: 更新 `docs/36-RoundMap.md` 每月路标状态标记（✅/⚠️/❌）
  - [ ] SubTask 3.3: 同步 `docs/设计文档.md` 模块清单（标注已实现/未实现）
  - [ ] SubTask 3.4: 更新 `操作记录.md` 追加本轮审计记录

## 阶段二：P0 缺失模块实现（阶段3-5 核心，阻断级）

- [ ] Task 4: R15 PICWave 时域仿真后端
  - [ ] SubTask 4.1: 检索 PICWave 时域仿真方案（Photon Design 官网 + arXiv 时域光子电路）
  - [ ] SubTask 4.2: 实现 `src/polaris/sim/picwave_backend.py`（时域 + Kerr/TPA/自由载流子非线性）
  - [ ] SubTask 4.3: 200 器件时域仿真 < 60 秒
  - [ ] SubTask 4.4: 新增 `tests/test_picwave_backend.py` ≥8 个测试
  - [ ] SubTask 4.5: 文献引用 ≥5 URL + 无 fall-back 声明 + 质量门禁 + git 提交

- [ ] Task 5: R16 FIMMPROP EME 仿真后端
  - [ ] SubTask 5.1: 检索 EME 本征模展开方案（FIMMPROP 文档 + EME 算法论文）
  - [ ] SubTask 5.2: 实现 `src/polaris/sim/eme_backend.py`（模式求解 + 重叠积分 + S 矩阵级联，复用 sim/eme/ 目录）
  - [ ] SubTask 5.3: EME 与 S 参数级联交叉验证（误差 < 1e-3）
  - [ ] SubTask 5.4: 支持锥形/弯曲/交叉 ≥5 种结构
  - [ ] SubTask 5.5: 新增 `tests/test_eme_backend.py` ≥6 个测试 + 文献 ≥5 URL + git 提交

- [ ] Task 6: R17 光电协同仿真（SPICE 联合）
  - [ ] SubTask 6.1: 检索光电协同仿真方案（VPIphotonics + gdsfactory VLSIR + Verilog-A）
  - [ ] SubTask 6.2: 实现 `src/polaris/sim/photoelectric_cosim.py`（VLSIR SPICE 导出 + Verilog-A 光子模型 + cocotb 联合）
  - [ ] SubTask 6.3: ≥3 个 Verilog-A 光子模型（调制器/探测器/激光器）
  - [ ] SubTask 6.4: 新增 `tests/test_photoelectric_cosim.py` ≥8 个测试 + 文献 ≥5 URL + git 提交

- [ ] Task 7: R27 Tidy3D 云 API FDTD 后端
  - [ ] SubTask 7.1: 检索 Tidy3D 云 API 方案（Flexcompute 文档 + Tidy3D Changelog）
  - [ ] SubTask 7.2: 实现 `src/polaris/sim/tidy3d_backend.py`（云 API 调用 + 亚像素精度 + S 参数提取）
  - [ ] SubTask 7.3: FDTD 仿真速度验证（CPU 基线对比，R04 不参与 GPU）
  - [ ] SubTask 7.4: 新增 `tests/test_tidy3d_backend.py` ≥8 个测试 + 文献 ≥5 URL + git 提交

- [ ] Task 8: R28 伴随优化逆向设计
  - [ ] SubTask 8.1: 检索伴随优化方案（Tidy3D autograd 文档 + lumopt + adjoint 论文）
  - [ ] SubTask 8.2: 实现 `src/polaris/inverse/adjoint_optimizer.py`（自动微分 + 伴随方法）
  - [ ] SubTask 8.3: ≥3 个标准器件示例（MMI/光栅耦合器/模式转换器）
  - [ ] SubTask 8.4: 新增 `tests/test_adjoint_optimizer.py` ≥8 个测试 + 文献 ≥5 URL + git 提交

## 阶段三：P1 缺失模块实现（阶段2/4 商业对齐）

- [ ] Task 9: R10 gdsfactory 布线策略对齐
  - [ ] SubTask 9.1: 实现 `src/polaris/routing/gdsfactory_style.py`（≥5 种布线策略：route_fiber_array/get_bundle/route_sbend 等）
  - [ ] SubTask 9.2: 与 PoLaRIS A* 布线结果对比（线长差距 < 10%）
  - [ ] SubTask 9.3: 新增 `tests/test_gdsfactory_routing.py` ≥8 个测试 + git 提交

- [ ] Task 10: R19 L-Edit 风格 GUI 集成
  - [ ] SubTask 10.1: 实现 `src/polaris/gui/layout_editor.py`（Web + KLayout 集成，器件拖拽/旋转/删除）
  - [ ] SubTask 10.2: 布线结果实时可视化 + DRC 错误高亮
  - [ ] SubTask 10.3: 新增 `tests/test_layout_editor.py` ≥10 个测试 + git 提交

- [ ] Task 11: R20 OptoDesigner Design Intent 对齐
  - [ ] SubTask 11.1: 实现 `src/polaris/flow/design_intent.py`（原理图→版图意图自动生成）
  - [ ] SubTask 11.2: Design Intent 与 PDK 器件映射
  - [ ] SubTask 11.3: 新增 `tests/test_design_intent.py` ≥8 个测试 + git 提交

- [ ] Task 12: R21 OptoDesigner 自动布线模块
  - [ ] SubTask 12.1: 实现 `src/polaris/routing/commercial_router.py`（高级连接器 ≥5 种 + 任意曲线离散化 1nm）
  - [ ] SubTask 12.2: 500 器件布线成功率 ≥95%
  - [ ] SubTask 12.3: 新增 `tests/test_commercial_router.py` ≥8 个测试 + git 提交

## 阶段四：P2 缺失模块实现（阶段6 顶级对齐）

- [ ] Task 13: R31 Lumerical FDTD 3D 全波仿真
  - [ ] SubTask 13.1: 实现 `src/polaris/sim/lumerical_fdtd.py`（3D FDTD 多物理场，R04 CPU 实现）
  - [ ] SubTask 13.2: 与 Tidy3D 交叉验证（误差 < 1e-3）
  - [ ] SubTask 13.3: 新增 `tests/test_lumerical_fdtd.py` ≥10 个测试 + git 提交

- [ ] Task 14: R32 Lumerical INTERCONNECT 时频域
  - [ ] SubTask 14.1: 实现 `src/polaris/sim/interconnect_backend.py`（时频域联合仿真）
  - [ ] SubTask 14.2: 1000 器件时频域仿真 < 5 分钟
  - [ ] SubTask 14.3: 新增 `tests/test_interconnect_backend.py` ≥8 个测试 + git 提交

- [ ] Task 15: R34 AlphaChip Edge-GNN 实现
  - [ ] SubTask 15.1: 实现 `src/polaris/rl/edge_gnn.py`（基于边的 GNN，R04 CPU 实现）
  - [ ] SubTask 15.2: Edge-GNN 在 Ariane RISC-V benchmark 上 HPWL 优于 R-GCN ≥5%
  - [ ] SubTask 15.3: 新增 `tests/test_edge_gnn.py` ≥10 个测试 + git 提交

- [ ] Task 16: R35 AlphaChip 预训练 + 分布式
  - [ ] SubTask 16.1: 实现 `src/polaris/rl/pretraining.py`（预训练→微调，R04 CPU 单机实现）
  - [ ] SubTask 16.2: 100+ PIC 块预训练数据集
  - [ ] SubTask 16.3: 新增 `tests/test_pretraining.py` ≥10 个测试 + git 提交

## 阶段五：2028 开发计划 Sprint 启动

- [ ] Task 17: 启动 Sprint 0-1（P0 求解器底座）
  - [ ] SubTask 17.1: 验证 Sprint 0 Task 0.1 A04-FDE 是否已实现（sim/fde/ 目录检查）
  - [ ] SubTask 17.2: 验证 Sprint 1 Task 1.1-1.4（FDFD/RCWA/EME/Redheffer）是否已实现
  - [ ] SubTask 17.3: 已实现的标记 `[x]`，未实现的列入后续实现
  - [ ] SubTask 17.4: 更新 `execute-2028-development-plan/tasks.md` 状态

- [ ] Task 18: 启动 Sprint 2-3（P0 收尾 + P2 仿真级联）
  - [ ] SubTask 18.1: 验证 Sprint 2 Task 2.1-2.7（BPM/varFDTD/FDTD/HEAT/DDM/DRC/版图）
  - [ ] SubTask 18.2: 验证 Sprint 3 Task 3.1-3.6（S参数/子网络/时域/频域/GUI/伴随）
  - [ ] SubTask 18.3: 已实现的标记 `[x]`，未实现的列入后续实现

- [ ] Task 19: 启动 Sprint 4-7（P3-P6 ML/RL/优化/量子/多物理/平台）
  - [ ] SubTask 19.1: 验证 Sprint 4 Task 4.1-4.10（GNN/PPO/AlphaChip/CNN/布线/伴随）
  - [ ] SubTask 19.2: 验证 Sprint 5-7 Task 5.1-7.6（优化/量子/多物理/IO/平台）
  - [ ] SubTask 19.3: 已实现的标记 `[x]`，未实现的列入后续实现

## 阶段六：最终验收与文档刷新

- [ ] Task 20: 全量回归测试
  - [ ] SubTask 20.1: 运行 `pytest tests/ -q` 确认 0 failed
  - [ ] SubTask 20.2: 运行质量门禁 `python scripts/quality_gate_baseline.py --check`
  - [ ] SubTask 20.3: 统计测试数（目标 ≥2568，对齐 36-RoundMap §9.2）

- [ ] Task 21: 刷新全部文档为最终真实状态
  - [ ] SubTask 21.1: 重写 `docs/roundmap_final_report.md` 为真实最终得分
  - [ ] SubTask 21.2: 更新 `AGENTS.md` §11 当前进度为最终状态
  - [ ] SubTask 21.3: 更新 `docs/feature_gap_full_analysis.md` 覆盖率
  - [ ] SubTask 21.4: 追加 `操作记录.md` 最终验收记录

# Task Dependencies

- Task 2/3 依赖 Task 1（需审计报告才能修正文档）
- Task 4-8 (P0) 可并行（5 个模块无相互依赖）
- Task 9 依赖 Task 4（R10 布线策略需时域仿真验证）
- Task 10/11/12 可并行（GUI/Design Intent/商业布线独立）
- Task 13 依赖 Task 7（R31 Lumerical FDTD 与 R27 Tidy3D 交叉验证）
- Task 14 依赖 Task 13（R32 INTERCONNECT 依赖 R31 FDTD）
- Task 15/16 可并行（Edge-GNN/预训练独立，但 R35 依赖 R34）
- Task 17-19 可并行（Sprint 验证独立）
- Task 20-21 依赖 Task 1-19（全部完成后最终验收）
