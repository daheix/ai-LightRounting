# 全量缺陷诚信审计+修复 Spec（基于R36差距分析）

## Why
R36差距分析报告（`docs/roundmap/R36_gap_analysis.md`）揭示36个路标中0个完全达标，19个存在严重问题。综合得分7.88距目标9.20差1.32分，主要失分在D07 AI/ML(0.30)、D12逆向设计(0.24)、D15用户规模(0.24)、D10 GUI(0.16)、D11光电协同(0.16)、D03仿真精度(0.10)。本轮再做一次全量诚信审计，参考路标、代码、网络资料，修复所有可修复缺陷。

## What Changes
- 修复3个缺失验收文档（stage1/stage2/stage6_report.md）
- 修复10个R36验收报告引用已删除的v4路径
- 修复4个路标内部自相矛盾
- 修复6个文档间数据不一致
- 补齐D07 AI/ML：已实现pretrain.py/transfer_learning.py（本轮R361修复），需更新R36验收
- 补齐D12逆向设计：已实现D12 showcase（commit），需更新R36验收
- 补齐D10 GUI：增强layout_editor.py交互能力
- 补齐D11光电协同：实证Ngspice联合仿真
- 补齐D03仿真精度：Lumerical FDTD交叉验证
- 修复R31/R35两个违规验收点（R04 GPU战略）
- 生成全量缺陷修复综合报告

## Impact
- Affected specs: audit-remaining-issues-and-drc-completeness、fix-unit-inconsistency-and-deep-optimization
- Affected code: modules/trainer/、modules/inverse/、modules/gui/、modules/parasitic/、docs/roundmap/
- 商业价值：综合得分7.88→8.5+，缩小与行业最高9.0的差距

## ADDED Requirements

### Requirement: 全量缺陷诚信审计
系统 SHALL 对照R36差距分析报告，逐项核查36个路标的真实状态，输出修复计划。

#### Scenario: 审计完成
- **WHEN** 运行全量审计
- **THEN** 输出每个路标的真实状态（✅/⚠️/❌）+ 修复优先级

### Requirement: 缺失验收文档补齐
系统 SHALL 补齐3个缺失验收文档：
- docs/roundmap_stage1_report.md
- docs/roundmap_stage2_report.md
- docs/roundmap_stage6_report.md

### Requirement: R36验收报告路径修复
R36验收报告中10个引用已删除v4路径 SHALL 更新为v5.0实际路径。

### Requirement: D07 AI/ML能力提升
基于本轮已实现的pretrain.py/transfer_learning.py（commit e2af0bdd等），D07得分 SHALL 从7→8+。

### Requirement: D12逆向设计提升
基于已实现的D12 showcase（MMI/WDM/Y分支adjoint优化），D12得分 SHALL 从6→7+。

### Requirement: 综合得分提升
修复后综合得分 SHALL 从7.88提升到8.5+（差距从1.32缩小到0.7以下）。

## MODIFIED Requirements

### Requirement: R36验收报告
更新为v6.0版本，反映v5.0架构实际状态 + 本轮修复成果。

## REMOVED Requirements
- R31 "GPU加速≥10×" 验收点（R04战略决策，禁止GPU）
- R35 "Ray分布式PPO（≥4 worker）" 验收点（R04，改用CPU多进程）
