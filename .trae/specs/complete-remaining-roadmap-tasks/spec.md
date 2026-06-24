# 完成剩余路标任务 Spec

## Why
当前 PoLaRIS 项目有两个 spec 的任务未完成：
1. `optimize-pipeline-integrity-and-1000-circuits` 的 Task 11/12/14（测试报告、失败分析、文档同步）
2. `refresh-commercial-gap-analysis-36mo` 的全部 7 个任务（商业差距分析 v1.0 → v2.0 刷新）

批量测试已运行 227/1200 电路，0 失败，用户指示"测试够了"，需要基于已有测试结果生成报告并完成剩余文档刷新工作。

## What Changes
- 基于已有 227 个测试结果生成测试报告（Task 11）
- 完成失败电路根因分析（Task 12 剩余：0 失败，主要是已知布线成功率低问题记录）
- 完成商业差距分析 v2.0 刷新（7 个任务：数据收集、详细报告、3 个文档覆盖重写、操作记录、验证）
- 完成文档同步与操作记录（Task 14）
- 更新所有相关 spec 的 tasks.md 状态

## Impact
- Affected specs: `optimize-pipeline-integrity-and-1000-circuits`, `refresh-commercial-gap-analysis-36mo`
- Affected code: 无代码变更（纯文档与报告生成）
- Affected docs: `docs/commercial_gap_analysis.md`, `docs/commercial_gap_analysis_v2.md`, `docs/industry_alignment_roadmap.md`, `docs/roadmap.md`, `out/batch_test/report.md`, `操作记录.md`

## ADDED Requirements

### Requirement: 测试报告生成
系统 SHALL 基于已有批量测试结果生成结构化测试报告，包含总体统计、分拓扑/规模/平台统计、失败分析。

#### Scenario: 生成测试报告
- **WHEN** 运行 `python scripts/generate_test_report.py`
- **THEN** 生成 `out/batch_test/report.md` 和 `out/batch_test/stats.json`
- **AND** 报告包含：成功率、DRC通过率、平均损耗、平均耗时、P50/P95/P99
- **AND** 报告包含分拓扑/分规模/分平台统计表

### Requirement: 商业差距分析 v2.0
系统 SHALL 刷新商业差距分析文档为 v2.0，反映第 80-95 轮的改进。

#### Scenario: 刷新商业差距分析
- **WHEN** 完成商业差距分析刷新
- **THEN** `docs/commercial_gap_analysis.md` 版本号为 v2.0
- **AND** 评分从 6.0/10 刷新为 6.1/10
- **AND** 36 个月里程碑规划（M1-M6）替换原路线图
- **AND** 所有评分变更可溯源到具体轮次

## MODIFIED Requirements

### Requirement: 文档同步
文档同步 SHALL 更新操作记录、学术诚信审查文档、README，并提交代码到开发分支合并 main。

## REMOVED Requirements
无
