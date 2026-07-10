# PoLaRIS 架构讲解与技术/投资人汇报 PPT Spec

## Why

PoLaRIS 光电子 AI 布局布线引擎已完成 36 月路标（R1-R36）代码交付，综合得分 8.08/10，
33 子模块 / 289 源码文件 / 99,017 行 / 1,614 测试 passed / 3,031 文献 URL。
当前需要对外汇报：一是内部/学术场景的**技术架构讲解**（讲清楚系统设计与业务流程），
二是面向外部的**技术汇报 PPT**（对标商业产品能力），三是面向外部的**投资人汇报 PPT**
（讲清楚商业价值、市场、差距、路线）。三份交付物共享同一数据底稿，避免数据不一致。

## What Changes

- **新增架构讲解文档** `docs/architecture_overview.md`：完整架构设计 + 6 大业务流程图
  （Mermaid 流程图源码，GitHub 可渲染），作为 PPT 的数据底稿
- **新增技术汇报 PPT** `docs/decks/tech_report.html`：HTML slide deck（reveal.js 风格，
  纯 HTML+CSS+JS，浏览器可直接预览），15-20 页，侧重技术架构与能力
- **新增投资人汇报 PPT** `docs/decks/investor_pitch.html`：HTML slide deck，12-15 页，
  侧重市场/价值/差距/路线/团队
- **不改动任何现有代码**（纯文档产出，R11 main 分支提交）

### 格式选择依据
- 沙箱环境无 PowerPoint/Keynote，HTML slide deck 可通过 OpenPreview 直接浏览器预览
- HTML 格式便于版本控制（git diff 可读）、便于后续转 PDF、便于嵌入项目网站
- 架构讲解用 Markdown + Mermaid（GitHub 原生渲染流程图）

## Impact

- Affected specs: 无（纯新增文档，不修改现有 spec）
- Affected code: 无（不改动任何 .py 文件）
- Affected docs: 新增 3 个文件，不修改现有 docs/
- 数据底稿来源: `docs/final_defect_audit_report_2026_07.md`（15 维度得分）、
  `modules/README.md`（模块清单）、`docs/36-RoundMap.md`（路标）、
  `docs/commercial_tools_feature_matrix.md`（竞品对比）、代码 docstring（文献溯源）

## ADDED Requirements

### Requirement: 架构讲解文档
系统 SHALL 提供 `docs/architecture_overview.md`，包含：
1. 项目一句话定位 + 体量数据（33 模块/99K 行/1614 测试/3031 文献）
2. 模块分层图（6 层 × 12 分类，ASCII/Mermaid）
3. 10 阶段标准化流水线表（stage1-10 名称/输入/输出/子模块/文献）
4. 6 大业务流程图（Mermaid）：
   - 流程 A: 网表 → GDS 主流水线（CircuitSpec → place → route → drc → lvs → gds）
   - 流程 B: AI 布局布线流程（PPO 训练 → 推理 → 布局 → 布线）
   - 流程 C: 逆向设计流程（JAX adjoint → 拓扑优化 → level-set）
   - 流程 D: 量子光子验证流程（Clements mesh → HOM 干涉 → 玻色采样）
   - 流程 E: 光电协同流程（布局 → 寄生提取 → Verilog-A → Ngspice 联合仿真）
   - 流程 F: Web GUI 交互流程（showcase 11 阶段 + 编辑器双模式）
5. 15 维度得分表（v6.0 当前 vs R36 目标 vs 行业最高）
6. 关键文献来源表（每核心算法的论文出处 + URL）

#### Scenario: 架构讲解可读性
- **WHEN** 工程师阅读 `docs/architecture_overview.md`
- **THEN** 6 个 Mermaid 流程图在 GitHub 正常渲染
- **AND** 所有数据可溯源到代码 docstring 或 docs/ 审计文档
- **AND** 无假数据（R03 合规）

### Requirement: 技术汇报 PPT
系统 SHALL 提供 `docs/decks/tech_report.html`，15-20 页 slide deck，包含：
1. 封面（项目名 + 一句话定位 + 版本 v6.0 + 日期）
2. 项目体量（33 模块/99K 行/1614 测试/3031 文献/4 平台 PDK）
3. 模块分层架构图（6 层 × 12 分类）
4. 10 阶段标准化流水线图
5. 核心算法能力（布局 DREAMPlace/AlphaChip、布线 LiDAR curvy、逆向 JAX adjoint）
6. AI/ML 能力（PPO + AlphaChip RL + 迁移学习 + 22 expert demos）
7. 物理求解器矩阵（FDTD/FDE/FDFD/EME/BPM/RCWA/多物理场）
8. 验证能力（12 DRC 规则 + LVS + 图同构 + 层次化 DRC）
9. GUI 交互式编辑器（R19 LayoutEditor + KLayout 双模式）
10. 15 维度得分雷达图（HTML canvas/SVG 绘制）
11. 与商业工具对标（Lumerical/KLayout/gdsfactory/IPKISS）
12. 关键文献溯源（核心算法论文列表）
13. 路标进展（R1-R36 完成，6 阶段得分演进）
14. 诚实差距声明（5 未达标维度）
15. 封底（项目链接 + 开源许可）

#### Scenario: 技术 PPT 预览
- **WHEN** 用浏览器打开 `docs/decks/tech_report.html`
- **THEN** slide deck 支持键盘左右键翻页
- **AND** 雷达图/流程图在浏览器正确渲染
- **AND** 所有数字与 `final_defect_audit_report_2026_07.md` 一致

### Requirement: 投资人汇报 PPT
系统 SHALL 提供 `docs/decks/investor_pitch.html`，12-15 页 slide deck，包含：
1. 封面（项目名 + slogan + 日期）
2. 问题与机遇（光子芯片设计 EDA 工具被海外垄断，AI 驱动的新一代机会）
3. 解决方案（PoLaRIS 开源 AI 光电子 EDA，端到端 10 阶段流水线）
4. 产品演示（showcase 11 阶段截图位 + 交互式编辑器）
5. 技术壁垒（33 模块/99K 行/3031 文献/4 平台 PDK/JAX 逆向/AlphaChip RL）
6. 市场规模（硅光子市场规模 + EDA 市场规模，需引用公开数据源）
7. 竞争格局（对标 Lumerical/KLayout/gdsfactory，15 维度对比表）
8. 商业模式（开源 + 商业版 + MPW 流片服务 + 学术合作）
9. 路线图（3 波修复 8.08→8.22→8.48→8.86，1-24 月）
10. 团队（占位，待补充）
11. 融资计划（占位，待补充）
12. 诚实声明（综合得分 8.08，未达 9.20 目标，5 维度未达标）
13. 封底（联系方式 + 项目链接）

#### Scenario: 投资人 PPT 预览
- **WHEN** 用浏览器打开 `docs/decks/investor_pitch.html`
- **THEN** slide deck 视觉风格简洁专业（适合投资人阅读）
- **AND** 市场数据有公开来源标注（不编造数据，R02/R03 合规）
- **AND** 团队/融资占位页明确标注"待补充"

### Requirement: 数据一致性
所有三份交付物 SHALL 共享同一数据底稿，数字一致：
- 体量数据：33 模块 / 289 文件 / 99,017 行 / 1,614 passed / 3,031 URL
- 得分：综合 8.08/10，15 维度逐项一致
- 路标：R1-R36 完成，6 阶段演进 6.1→9.2 目标
- 差距：5 未达标（D07/D10/D11/D12/D15）

#### Scenario: 数据溯源
- **WHEN** 审核任一 PPT 中的数字
- **THEN** 可在 `final_defect_audit_report_2026_07.md` 或 `modules/README.md` 找到对应来源
- **AND** 无夸大无缩小（R02 学术诚信，R03 禁止假数据）
