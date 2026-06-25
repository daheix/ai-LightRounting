# 985 功能点算法逻辑全量分析 Spec

## Why

PoLaRIS 项目已完成 985 个功能点的差距标注（feature_gap_full_analysis.md），但缺乏每个功能点（尤其 359 个❌缺失 + 243 个⚠️部分）的**完整算法逻辑与实现路径**。用户要求：参考国际期刊/开源社区/标准智库，给每个功能点提供复杂公式的算法逻辑，标记共用同一算法的功能（去重聚类），建立完整开发计划，归档至 `2026-2028开发计划/功能清单与实现/`。

## What Changes

- 扫描 985 个功能点（T01-T17），建立功能编号 → 算法聚类映射
- 按"算法/实现聚类"去重分组（预计 30-50 个算法群组），同一算法的功能合并到一个文件
- 每个聚类文件：含完整算法逻辑、核心公式（LaTeX）、文献来源（arXiv/IEEE/GitHub URL）、PoLaRIS 实现路径、商业工具对照
- 文件名格式：`<功能编号前缀>-<完整功能名称>.md`（如 `R37-FDE本征模求解器.md`）
- 建立"算法去重矩阵"（哪些功能共用同一算法/实现）
- 建立"完整开发计划"（按算法聚类排期，标注依赖关系）
- 所有调研遵循"权威资源总清单"（arXiv/IEEE/ACM/GitHub/Stack Overflow 等），交叉验证，诚信标注

## Impact

- Affected specs: `analyze-third-party-library-inventory`（求解器公式手册为其子集）、`build-36-month-roundmap`（开发计划对齐）、`refresh-commercial-gap-analysis-36mo`（差距来源）
- Affected code: `src/polaris/`（已有功能算法核对）、`3dtool/ALGORITHMS.md`（求解器公式扩展）
- 新增目录：`2026-2028开发计划/功能清单与实现/`

## ADDED Requirements

### Requirement: 算法聚类去重分析
系统 SHALL 扫描 985 个功能点，按"底层算法/实现方法"聚类去重，输出"算法去重矩阵"，标注哪些功能点共用同一算法。

#### Scenario: 共用算法识别
- **WHEN** 多个功能点（如 T01 的 RCWA + T04 的 RCWA + T15 的 RCWA）使用同一算法
- **THEN** 合并到一个聚类文件，去重矩阵标注三方共用 RCWA 算法

### Requirement: 功能点算法逻辑文档
系统 SHALL 为每个算法聚类生成独立 .md 文件，文件名以功能编号前缀开头 + 完整功能名称。

#### Scenario: 复杂公式功能
- **WHEN** 功能点涉及复杂公式（如 Scharfetter-Gummel 离散化、Redheffer 星积）
- **THEN** 文档含：物理模型、控制方程、离散化方案、边界条件、核心公式（LaTeX）、文献来源（含 URL）、PoLaRIS 实现路径、商业工具对照、创新点

#### Scenario: 简单功能
- **WHEN** 功能点为简单工具调用（如 GDS 导出）
- **THEN** 文档含：功能描述、实现方法、依赖库、PoLaRIS 实现位置

### Requirement: 完整开发计划
系统 SHALL 基于算法聚类与依赖关系，建立完整开发计划（2026-2028），含排期、依赖、优先级。

### Requirement: 网络调研诚信
系统 SHALL 遵循"权威资源总清单"，所有算法公式经 arXiv/IEEE/ACM/GitHub 官方源核实，交叉验证（国外工程实践 + 学术论文 + 官方标准），禁止编造。

## MODIFIED Requirements

### Requirement: 文档归档位置
所有产出归档至 `2026-2028开发计划/功能清单与实现/`，文件名中文，以功能编号前缀开头。

## REMOVED Requirements

### Requirement: 逐功能点单文件
**Reason**: 985 个功能点逐个单文件过于碎片化，按算法聚类去重更合理
**Migration**: 同一算法的功能点合并到一个聚类文件，去重矩阵标注映射关系
