# Tasks

## 阶段1: 全量缺陷诚信审计（参考R36差距分析）

- [ ] Task 1: 重读R36差距分析报告
  - [ ] SubTask 1.1: Read `/workspace/docs/roundmap/R36_gap_analysis.md` 完整内容
  - [ ] SubTask 1.2: 核查36个路标当前真实状态（代码存在性+验收报告）
  - [ ] SubTask 1.3: 识别本轮已修复项（pretrain.py/transfer_learning.py/D12 showcase等）
- [ ] Task 2: 生成全量缺陷清单
  - [ ] SubTask 2.1: 创建 `docs/full_defect_audit_v2.md`
  - [ ] SubTask 2.2: 按36个路标逐项标注真实状态+修复优先级

## 阶段2: 修复缺失验收文档（P0学术诚信）

- [ ] Task 3: 创建stage1/stage2/stage6验收文档
  - [ ] SubTask 3.1: 创建 `docs/roundmap_stage1_report.md`（R1-R6验收）
  - [ ] SubTask 3.2: 创建 `docs/roundmap_stage2_report.md`（R7-R12验收）
  - [ ] SubTask 3.3: 创建 `docs/roundmap_stage6_report.md`（R31-R36验收）

## 阶段3: 修复R36验收报告v4路径（P0学术诚信）

- [ ] Task 4: 更新R36验收报告
  - [ ] SubTask 4.1: 修复10个v4路径为v5.0实际路径
  - [ ] SubTask 4.2: 删除R31 "GPU加速≥10×" 违规验收点（R04）
  - [ ] SubTask 4.3: 删除R35 "Ray分布式PPO" 违规验收点（R04）
  - [ ] SubTask 4.4: 更新综合得分为v6.0（反映pretrain/D12 showcase修复）

## 阶段4: 修复路标内部矛盾与数据不一致（P0学术诚信）

- [ ] Task 5: 修复36-RoundMap.md
  - [ ] SubTask 5.1: 修复4个自相矛盾（§0.1 vs §4-6）
  - [ ] SubTask 5.2: 修复6个文档间数据不一致
  - [ ] SubTask 5.3: 修复README索引与总览不一致

## 阶段5: 补齐D07 AI/ML能力（P1，0.30加权分差）

- [ ] Task 6: 验证pretrain.py/transfer_learning.py已实现
  - [ ] SubTask 6.1: 确认commit e2af0bdd等已push
  - [ ] SubTask 6.2: 运行BC预训练+迁移学习showcase
  - [ ] SubTask 6.3: 更新D07得分为8+

## 阶段6: 补齐D12逆向设计（P1，0.24加权分差）

- [ ] Task 7: 验证D12 showcase已实现
  - [ ] SubTask 7.1: 确认 `modules/inverse/src/polaris_inverse/showcase.py` 存在
  - [ ] SubTask 7.2: 运行MMI/WDM/Y分支adjoint优化showcase
  - [ ] SubTask 7.3: 更新D12得分为7+

## 阶段7: 补齐D10 GUI交互能力（P2，0.16加权分差）

- [ ] Task 8: 增强layout_editor.py
  - [ ] SubTask 8.1: Read现有 `modules/gui/src/polaris_gui/layout_editor.py`
  - [ ] SubTask 8.2: 添加交互式编辑功能（拖拽/缩放/选择）
  - [ ] SubTask 8.3: 更新D10得分为6+

## 阶段8: 补齐D11光电协同（P2，0.16加权分差）

- [ ] Task 9: 实证Ngspice联合仿真
  - [ ] SubTask 9.1: 检查Ngspice是否可用
  - [ ] SubTask 9.2: 运行Verilog-A + Ngspice联合仿真showcase
  - [ ] SubTask 9.3: 更新D11得分为8+

## 阶段9: 补齐D03仿真精度（P3，0.10加权分差）

- [ ] Task 10: Lumerical FDTD交叉验证
  - [ ] SubTask 10.1: 检索Lumerical公开benchmark数据
  - [ ] SubTask 10.2: 运行PoLaRIS FDTD对标
  - [ ] SubTask 10.3: 生成精度对比报告

## 阶段10: 综合报告与提交

- [ ] Task 11: 生成全量缺陷修复综合报告
  - [ ] SubTask 11.1: 创建 `docs/full_defect_remediation_report.md`
  - [ ] SubTask 11.2: 含36路标状态+15维度得分+修复成果
  - [ ] SubTask 11.3: 更新综合得分为v6.0
- [ ] Task 12: 提交与验证
  - [ ] SubTask 12.1: 全量pytest回归
  - [ ] SubTask 12.2: git add精确文件→commit→push
  - [ ] SubTask 12.3: 更新操作记录

# Task Dependencies
- Task 1-2 独立（审计）
- Task 3-5 可并行（文档修复）
- Task 6-9 可并行（4个维度补齐）
- Task 10 依赖Task 6-9
- Task 11-12 依赖Task 1-10
