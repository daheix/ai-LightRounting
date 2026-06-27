# Checklist — 开发计划审核与文档同步更新

## 阶段一：审计报告与文档同步

- [ ] `docs/devplan_audit_report.md` 已生成，含 16 spec + 36 路标 + Sprint 0-7 真实状态
- [ ] 审计报告所有声明附 git log / 文件路径 / 测试结果作为证据（R02 学术诚信）
- [ ] `docs/roundmap_final_report.md` 得分从 9.5 修正为真实值（7.88），标注 13 模块缺失
- [ ] `docs/roundmap_stage3_report.md` 标注 R15/R16/R17 未实现
- [ ] `docs/roundmap_stage4_report.md` 标注 R19/R20/R21 未实现
- [ ] `docs/roundmap_stage5_report.md` 标注 R27/R28 未实现
- [ ] `AGENTS.md` §11 当前进度已刷新为真实状态（R01-R08 代码有/13 模块缺失）
- [ ] `docs/36-RoundMap.md` 每月路标状态标记（✅/⚠️/❌）已更新
- [ ] `docs/设计文档.md` 模块清单已同步（标注已实现/未实现）
- [ ] `操作记录.md` 已追加本轮审计记录

## 阶段二：P0 缺失模块实现

- [ ] `src/polaris/sim/picwave_backend.py` 已实现（R15 时域 + 非线性 Kerr/TPA/自由载流子）
- [ ] `tests/test_picwave_backend.py` ≥8 个测试全部通过
- [ ] 200 器件时域仿真 < 60 秒
- [ ] `src/polaris/sim/eme_backend.py` 已实现（R16 EME + 重叠积分 + S 矩阵级联）
- [ ] `tests/test_eme_backend.py` ≥6 个测试全部通过
- [ ] EME 与 S 参数级联交叉验证误差 < 1e-3
- [ ] 支持锥形/弯曲/交叉 ≥5 种结构
- [ ] `src/polaris/sim/photoelectric_cosim.py` 已实现（R17 VLSIR SPICE + Verilog-A + cocotb）
- [ ] `tests/test_photoelectric_cosim.py` ≥8 个测试全部通过
- [ ] ≥3 个 Verilog-A 光子模型（调制器/探测器/激光器）
- [ ] `src/polaris/sim/tidy3d_backend.py` 已实现（R27 云 API + 亚像素精度）
- [ ] `tests/test_tidy3d_backend.py` ≥8 个测试全部通过
- [ ] `src/polaris/inverse/adjoint_optimizer.py` 已实现（R28 伴随优化 + 自动微分）
- [ ] `tests/test_adjoint_optimizer.py` ≥8 个测试全部通过
- [ ] ≥3 个标准器件示例（MMI/光栅耦合器/模式转换器）
- [ ] P0 全部 5 模块文献引用 ≥5 URL（R02 学术诚信）
- [ ] P0 全部 5 模块无 fall-back 声明（R03）
- [ ] P0 全部 5 模块质量门禁通过 + git 提交合并 main（R08）

## 阶段三：P1 缺失模块实现

- [ ] `src/polaris/routing/gdsfactory_style.py` 已实现（R10 ≥5 种布线策略）
- [ ] `tests/test_gdsfactory_routing.py` ≥8 个测试全部通过
- [ ] 与 PoLaRIS A* 布线结果线长差距 < 10%
- [ ] `src/polaris/gui/layout_editor.py` 已实现（R19 Web GUI + 器件拖拽/DRC 高亮）
- [ ] `tests/test_layout_editor.py` ≥10 个测试全部通过
- [ ] `src/polaris/flow/design_intent.py` 已实现（R20 原理图→版图意图）
- [ ] `tests/test_design_intent.py` ≥8 个测试全部通过
- [ ] `src/polaris/routing/commercial_router.py` 已实现（R21 高级连接器 + 1nm 曲线）
- [ ] `tests/test_commercial_router.py` ≥8 个测试全部通过
- [ ] 500 器件布线成功率 ≥95%
- [ ] P1 全部 4 模块质量门禁通过 + git 提交合并 main

## 阶段四：P2 缺失模块实现

- [ ] `src/polaris/sim/lumerical_fdtd.py` 已实现（R31 3D FDTD 多物理场，R04 CPU）
- [ ] `tests/test_lumerical_fdtd.py` ≥10 个测试全部通过
- [ ] 与 Tidy3D 交叉验证误差 < 1e-3
- [ ] `src/polaris/sim/interconnect_backend.py` 已实现（R32 时频域联合）
- [ ] `tests/test_interconnect_backend.py` ≥8 个测试全部通过
- [ ] 1000 器件时频域仿真 < 5 分钟
- [ ] `src/polaris/rl/edge_gnn.py` 已实现（R34 Edge-GNN，R04 CPU）
- [ ] `tests/test_edge_gnn.py` ≥10 个测试全部通过
- [ ] Edge-GNN HPWL 优于 R-GCN ≥5%
- [ ] `src/polaris/rl/pretraining.py` 已实现（R35 预训练→微调，R04 CPU 单机）
- [ ] `tests/test_pretraining.py` ≥10 个测试全部通过
- [ ] 100+ PIC 块预训练数据集
- [ ] P2 全部 4 模块质量门禁通过 + git 提交合并 main

## 阶段五：2028 开发计划 Sprint 启动

- [ ] Sprint 0 Task 0.1 A04-FDE 状态已验证（已实现标 [x]，未实现列入后续）
- [ ] Sprint 1 Task 1.1-1.4（FDFD/RCWA/EME/Redheffer）状态已验证
- [ ] Sprint 2 Task 2.1-2.7（BPM/varFDTD/FDTD/HEAT/DDM/DRC/版图）状态已验证
- [ ] Sprint 3 Task 3.1-3.6（S参数/子网络/时域/频域/GUI/伴随）状态已验证
- [ ] Sprint 4 Task 4.1-4.10（GNN/PPO/AlphaChip/CNN/布线/伴随）状态已验证
- [ ] Sprint 5-7 Task 5.1-7.6（优化/量子/多物理/IO/平台）状态已验证
- [ ] `execute-2028-development-plan/tasks.md` 状态已更新（已实现标 [x]）

## 阶段六：最终验收与文档刷新

- [ ] `pytest tests/ -q` 全量回归 0 failed（允许 skipped）
- [ ] 质量门禁 `python scripts/quality_gate_baseline.py --check` 通过
- [ ] 测试数 ≥2568（对齐 36-RoundMap §9.2 累计预测）
- [ ] `docs/roundmap_final_report.md` 重写为真实最终得分
- [ ] `AGENTS.md` §11 更新为最终状态
- [ ] `docs/feature_gap_full_analysis.md` 覆盖率已更新
- [ ] `操作记录.md` 已追加最终验收记录
- [ ] 所有代码已提交合并 main 并推送远端（R08）
- [ ] R02 学术诚信：无虚假完成声明，所有声明有代码/测试/git 证据
- [ ] R03 无 fall-back：所有模块失败即 raise，无假数据兜底
- [ ] R04 不参与 GPU：FDTD/Edge-GNN/预训练均为 CPU 实现，标注 🚫不参与 GPU
