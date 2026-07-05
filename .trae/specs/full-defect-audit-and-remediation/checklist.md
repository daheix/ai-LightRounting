# 全量缺陷诚信审计+修复 Checklist

## 阶段1: 全量缺陷诚信审计

- [ ] R36差距分析报告完整阅读
- [ ] 36个路标真实状态逐项核查
- [ ] 本轮已修复项识别（pretrain/transfer_learning/D12 showcase）
- [ ] `docs/full_defect_audit_v2.md` 已生成

## 阶段2: 修复缺失验收文档

- [ ] `docs/roundmap_stage1_report.md` 已创建
- [ ] `docs/roundmap_stage2_report.md` 已创建
- [ ] `docs/roundmap_stage6_report.md` 已创建

## 阶段3: 修复R36验收报告v4路径

- [ ] 10个v4路径已更新为v5.0
- [ ] R31 "GPU加速≥10×" 违规验收点已删除
- [ ] R35 "Ray分布式PPO" 违规验收点已删除
- [ ] 综合得分已更新为v6.0

## 阶段4: 修复路标内部矛盾

- [ ] 4个自相矛盾已修复
- [ ] 6个文档间数据不一致已修复
- [ ] README索引与总览一致

## 阶段5: D07 AI/ML能力提升

- [ ] pretrain.py/transfer_learning.py已验证
- [ ] BC预训练+迁移学习showcase运行成功
- [ ] D07得分7→8+

## 阶段6: D12逆向设计提升

- [ ] D12 showcase已验证
- [ ] MMI/WDM/Y分支adjoint优化运行成功
- [ ] D12得分6→7+

## 阶段7: D10 GUI交互能力

- [ ] layout_editor.py交互功能增强
- [ ] D10得分4→6+

## 阶段8: D11光电协同

- [ ] Ngspice联合仿真实证
- [ ] D11得分7→8+

## 阶段9: D03仿真精度

- [ ] Lumerical FDTD交叉验证报告
- [ ] D03得分9→9+（保持）

## 阶段10: 综合报告与提交

- [ ] `docs/full_defect_remediation_report.md` 已生成
- [ ] 综合得分v6.0 ≥ 8.5
- [ ] 全量pytest回归通过
- [ ] 0超80行函数/0 except:pass/0 TODO
- [ ] 操作记录已追加
- [ ] 代码已提交到main并push
