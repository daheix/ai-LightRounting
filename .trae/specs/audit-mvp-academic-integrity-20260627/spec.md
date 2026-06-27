# MVP 技术诚信学术审核 Spec

## Why

MVP 版本交付前，需对全部代码（271 .py 文件 / 101894 行）和设计文档（90 .md 文件）进行技术诚信学术审核，确保：
- 物理常数、公式、算法实现真实可溯源（R02 学术诚信）
- 无 fall-back 假数据残留（R03 禁止 fall-back）
- 代码与设计文档保持一致（R07 操作记录）
- 发现的 Bug 立即修复（R05 Bug 必修）
- 质量门禁达标（R06 圈复杂度/行数/覆盖率）

## What Changes

- 全量扫描 fall-back/假数据/TODO/FIXME 残留
- 审核物理常数来源（CODATA 2018 等）
- 审核文献引用真实性（URL/作者/年份）
- 审核核心算法实现正确性（FDTD/EME/FDE/RCWA/BPM/Redheffer）
- 核查代码与设计文档一致性
- 网络检索权威资料解决分歧
- 生成审核报告 `20260627-mvp技术诚信学术审核.md`
- 修复发现的 Bug

## Impact

- Affected code: src/polaris/ 全部 271 个 .py 文件
- Affected docs: docs/ 全部 90 个 .md 文件
- 审核报告: 20260627-mvp技术诚信学术审核.md

## ADDED Requirements

### Requirement: 全量代码走读
系统 SHALL 对 src/polaris/ 下每一个 .py 文件进行走读，记录：
- 物理常数来源（CODATA/论文/开源仓库）
- 公式实现正确性（与文献对照）
- 文献引用真实性（URL 可访问性）
- fall-back/假数据/TODO 残留

### Requirement: 设计文档一致性
系统 SHALL 核查代码实现与 docs/设计文档.md 的一致性，记录分歧并网络检索权威资料评价，保留最优结果。

### Requirement: 审核报告
系统 SHALL 生成 `20260627-mvp技术诚信学术审核.md`，包含：
- 审核范围与方法
- 物理常数来源清单
- 文献引用真实性清单
- 算法实现正确性清单
- 代码-文档分歧清单
- Bug 清单与修复状态
- 质量门禁达标声明
- 无 fall-back 声明
