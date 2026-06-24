# 深度学术诚信审核与关键人物分析 Spec

## Why
PoLaRIS 36 月路标已全部完成（综合得分 9.5），但在商业交付前需要进行一轮全新的、彻底的、全方位的学术诚信检查。需要验证所有数据来源的真实性、固定参数的依据、计算公式的正确性，并分析关键论文作者（人物）的学术背景以确认引用的权威性。用户规则明确要求"再来一轮全新的彻底的全方位的学术诚信检查；所有的数据的来源，为什么，固定参数，计算公式，全部列表做好详细记录来源"。

## What Changes
- 对 R01-R36 全部模块进行深度学术诚信审核（数据来源/固定参数/计算公式/人物背景）
- 检索网络验证所有引用论文/URL 的真实性与可达性
- 分析关键论文作者（人物）的学术背景与权威性
- 生成学术诚信审核报告（含数据来源清单、参数依据清单、公式推导清单、人物背景清单）
- 修复审核中发现的问题（如有）
- 全部记录到操作记录.md

## Impact
- Affected specs: build-polaris-optical-pnr（依赖其交付物）
- Affected code: src/polaris/ 全部模块（sim/pdk/router/rl/engine/trainer/eval）
- Affected docs: docs/roundmap/R01-R36.md, 操作记录.md

## ADDED Requirements

### Requirement: 深度数据来源验证
系统 SHALL 对所有模块中引用的数据来源（论文 DOI/URL、官方文档 URL）进行网络可达性验证，并记录验证结果。

#### Scenario: 论文 URL 验证
- **WHEN** 审核脚本检查某个论文 URL
- **THEN** 记录 URL 是否可达、HTTP 状态码、是否含期望内容

#### Scenario: 参数来源验证
- **WHEN** 审核某个固定参数（如 n_Si=3.48）
- **THEN** 记录参数值、来源文献、文献可达性、参数是否在文献报告区间内

### Requirement: 计算公式正确性验证
系统 SHALL 对所有模块中的计算公式进行推导来源验证，确认公式与原始文献一致。

#### Scenario: 公式验证
- **WHEN** 审核某个公式（如 CFL 条件）
- **THEN** 记录公式内容、推导来源文献、文献中原始公式、一致性结论

### Requirement: 关键人物学术背景分析
系统 SHALL 对关键引用论文的作者进行学术背景分析，确认引用的权威性。

#### Scenario: 人物分析
- **WHEN** 分析某个关键作者（如 K. S. Yee, Berenger, Mirhoseini）
- **THEN** 记录作者所属机构、H-index、主要贡献、被引次数、是否领域权威

### Requirement: 审核报告生成
系统 SHALL 生成结构化学术诚信审核报告，包含：数据来源清单、固定参数清单、计算公式清单、关键人物清单、问题修复记录。

#### Scenario: 报告生成
- **WHEN** 审核完成
- **THEN** 报告保存到 docs/academic_integrity_audit.md，并追加到操作记录.md

## MODIFIED Requirements

### Requirement: 学术诚信（原有）
在原有学术诚信审核基础上，增加深度网络验证、人物背景分析、公式逐条核对，从"自检"升级为"网络交叉验证"。

## REMOVED Requirements
无
