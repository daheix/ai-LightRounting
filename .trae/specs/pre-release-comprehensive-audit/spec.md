# 商业发布前综合审查 Spec

## Why

PoLaRIS 光电子 AI 布局布线引擎即将进入商业发布阶段，当前综合得分 8.08/10（目标 9.20/10），5 个维度未达标。需要一次全面审核——走读每一行代码对应的每一个设计文档，彻底分析路标完成度，保证诚信审查、精度审查、一切标准满足商业发布标准。R01 检索（IEEE 1012-2024 / ISO 9001 / Google Eng Practices / Ansys FDTD 收敛 / FAIR 溯源 / gdsfactory CI）已给出 8 维度权威框架。

## What Changes

- **代码审查**: 走读全部 33 模块源码，对照设计文档验证一致性（函数≤80行/文件≤800行/圈复杂度≤15/0 except:pass/0 TODO）
- **文档审查**: 走读全部设计文档，验证每模块 docstring ≥5 URL、参数/公式可溯源、创新点标注 `*创新*`
- **精度审查**: DRC 误报率 ≤5%（R379 已修复 11.1%→0%）、FDTD PML 收敛、S 参数能量守恒、LVS 等价性
- **诚信审查**: 0 假数据、0 抄袭洗稿、0 选择性引用、PGR-DRC 领域误用已修正（R380）
- **路标审查**: 15 维度（D01-D15）逐维度对标商业产品，分析完成度与差距
- **综合报告**: 生成商业发布前综合审查报告，给出 GO/NO-GO 决策

## Impact

- Affected specs: audit-remaining-issues-and-drc-completeness / complete-remaining-roadmap-tasks / audit-academic-integrity-deep
- Affected code: 全部 33 模块源码（modules/*/src/）
- Affected docs: docs/final_defect_audit_report_2026_07.md / docs/drc_completeness_audit_report.md / docs/drc_100pct_accuracy_assessment.md / docs/36-RoundMap.md / 操作记录.md

## ADDED Requirements

### Requirement: 商业发布前综合审查
系统 SHALL 提供一份覆盖代码/文档/精度/诚信/路标 5 类的商业发布前综合审查报告，给出明确的 GO/NO-GO 决策。

#### Scenario: 代码审查通过
- **WHEN** 审查员走读全部 33 模块源码
- **THEN** 函数≤80行=0违规 / 文件≤800行=0违规 / 圈复杂度≤15=0违规 / 0 except:pass / 0 TODO/FIXME/HACK / 0 GPU违规

#### Scenario: 文档审查通过
- **WHEN** 审查员走读全部设计文档
- **THEN** 每模块 docstring ≥5 URL / 参数可溯源 / 公式可推导 / 创新点标注 / 代码与文档一致

#### Scenario: 精度审查通过
- **WHEN** 审查员运行精度验证
- **THEN** DRC误报率≤5% / FDTD PML收敛<2% / S参数能量守恒≤0.1% / LVS等价性100%

#### Scenario: 诚信审查通过
- **WHEN** 审查员执行学术诚信审查
- **THEN** 0假数据 / 0抄袭 / 0选择性引用 / PGR-DRC领域误用已修正 / 所有URL可访问

#### Scenario: 路标审查通过
- **WHEN** 审查员对标15维度路标
- **THEN** 综合得分≥9.20/10 / 达标维度≥13/15 / 对标AlphaChip/Apollo/LiDAR

#### Scenario: GO 决策
- **WHEN** 5 类审查全部通过
- **THEN** 输出"GO: 可商业发布（研发用途）"决策

#### Scenario: NO-GO 决策
- **WHEN** 任一类审查未通过
- **THEN** 输出"NO-GO"决策并列出阻断项与修复建议

## MODIFIED Requirements

### Requirement: 15维度路标完成度评估
基于 R379/R380 修复后状态重新评估：
- D05 DRC/LVS: 误报率 11.1%→0%（R379 修复），有效通过率 100%，得分 9→9.5
- D07 AI/ML: PPO+TILOS+TensorBoard 已实现（R377），得分 8→9
- D10 GUI: Web 交互式版图编辑器已实现（R377），得分 4→8
- D11 光电协同: Ngspice+10器件+PAM4 BER 已实现（R377），得分 7→9
- D12 逆向设计: 拓扑+level-set+3D 已实现（R377），得分 7→9
- D15 用户规模: 仍需论文+流片（长期任务），得分 2（不变）

### Requirement: 学术诚信审查
PGR-DRC 领域误用已修正（R380，9处全部标注领域澄清），光子学权威对标替换为 LiDAR 2.0 + Calibre eqDRC + Mohan DATE 2023。

## REMOVED Requirements

### Requirement: 100% DRC 准确度
**Reason**: R01/R09 检索证实商业研发工具不要求 100%（Mohan DATE 2023 ≤5% 误报即可），强行追求违反 R03。
**Migration**: 保留 100% 作为 tape-out sign-off 目标（长期），研发用途门槛 ≤5% 误报（已达标 0%）。
