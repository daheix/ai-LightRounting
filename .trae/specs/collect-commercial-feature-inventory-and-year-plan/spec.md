# 光电子商业工具功能点级清单收集 + PoLaRIS 一年开发计划 Spec

## Why

PoLaRIS 现有 `docs/commercial_tools_feature_matrix.md` 仅在 15 个**维度级别**（D01-D15）对比 13 个工具，粒度太粗，无法指导"每月开发对应功能点"的精细化排期。用户要求：

1. **网络官网调研**所有光电子商业产品，整理每个产品的**功能点级**清单（详细到每一个具体功能点，必须诚信，禁止臆造）
2. 与 PoLaRIS 自己的功能清单做**全量逐点对比**
3. 制定 **2026-06 到 2027-05 一年开发计划**，每个月对应明确的功能点交付

现有维度级矩阵（如"D03 仿真精度 = FDTD+EME+多物理场"）无法回答"Lumerical FDTD 支持哪些具体子功能（亚像素平滑/CPML 边界/色散材料/各向异性/非线性/分布式 GPU/伴随优化）PoLaRIS 缺哪些"这类问题。必须下沉到功能点级别。

## What Changes

- **新增** `docs/commercial_feature_inventory/T01_lumerical.md`（Ansys Lumerical 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T02_ipkiss.md`（Luceda IPKISS 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T03_optodesigner.md`（Synopsys OptoDesigner 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T04_tidy3d.md`（Flexcompute Tidy3D 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T05_vpiphotonics.md`（VPIphotonics 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T06_ledit_photonics.md`（Siemens L-Edit Photonics 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T07_photon_design.md`（Photon Design Aspic/PICWave/FIMMPROP/OmniSim 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T08_gdsfactory.md`（gdsfactory 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T09_klayout.md`（KLayout 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T10_sax.md`（sax 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T11_simphony.md`（simphony 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T12_cadence_synopsys.md`（Cadence Innovus + Synopsys ICC2 功能点级清单）
- **新增** `docs/commercial_feature_inventory/T13_alphachip.md`（Google AlphaChip + Circuit Training 功能点级清单）
- **新增** `docs/polaris_feature_inventory.md`（PoLaRIS 自身功能点级清单）
- **新增** `docs/feature_gap_full_analysis.md`（全量逐点差距分析：13 工具 × N 功能点 × PoLaRIS 有/无/部分）
- **新增** `docs/year_plan_2026_06_2027_05.md`（2026-06 到 2027-05 一年开发计划，每月对应功能点）
- **刷新** `操作记录.md`（追加本轮记录）

## Impact

- Affected specs: 
  - `refresh-commercial-gap-analysis-36mo`（本 spec 是其功能点级下沉补充，不冲突）
  - `build-36-month-roundmap`（一年计划是 36 个月路标的前 12 个月细化）
- Affected code: 无代码改动，纯文档与规划
- Affected docs: 见 What Changes 列表

## 数据来源与学术诚信

**强制规则**（用户明确要求"必须诚信"）：
1. 每个功能点必须标注来源 URL（官网文档/产品页/用户手册）
2. 禁止臆造功能点：若官网未明确说明，标注"未公开"而非猜测
3. 禁止夸大 PoLaRIS 能力：PoLaRIS 功能点必须基于实际代码（引用文件路径+行号）
4. 商业产品定价、用户规模等敏感数据标注"估算（来源 URL）"
5. 所有来源 URL 必须可访问（WebFetch 验证）

**数据来源**：
- 商业产品官网：Ansys/Luceda/Synopsys/Flexcompute/VPIphotonics/Siemens/Photon Design
- 开源项目仓库：gdsfactory/KLayout/sax/simphony GitHub
- 电子 EDA 厂商：Cadence/Synopsys 官网
- AI 标杆：Google DeepMind AlphaChip Nature 论文 + Circuit Training GitHub
- PoLaRIS 代码：`/workspace/src/polaris/`、`/workspace/examples/`、`/workspace/tests/`

## ADDED Requirements

### Requirement: 商业产品功能点级清单
系统 SHALL 为每个光电子商业工具（T01-T13）生成功能点级清单文档，每个功能点包含：
- 功能点名称（具体到子功能，如"FDTD 亚像素平滑"而非"仿真精度"）
- 功能描述（1-2 句话）
- 来源 URL（官网文档链接）
- PoLaRIS 对应能力（有/无/部分 + 引用代码路径）

#### Scenario: 功能点收集
- **WHEN** 调研 Ansys Lumerical 官网
- **THEN** 生成 `T01_lumerical.md`，包含 FDTD/MODE/INTERCONNECT/CML Compiler 各模块的子功能点
- **AND** 每个功能点标注来源 URL
- **AND** 未公开的能力标注"未公开"

### Requirement: PoLaRIS 自身功能点级清单
系统 SHALL 生成 PoLaRIS 自身功能点级清单，每个功能点包含：
- 功能点名称
- 功能描述
- 实现位置（文件路径:行号）
- 成熟度（生产可用/实验性/原型）

#### Scenario: PoLaRIS 功能盘点
- **WHEN** 扫描 PoLaRIS 代码库
- **THEN** 生成 `polaris_feature_inventory.md`
- **AND** 每个功能点引用具体代码位置
- **AND** 实验性功能标注"实验性"

### Requirement: 全量差距分析
系统 SHALL 生成全量逐点差距分析文档，对每个商业工具的每个功能点，标注 PoLaRIS 的状态：
- ✅ 已有（达到商业级）
- ⚠️ 部分（有实现但差距明显）
- ❌ 缺失（无实现）
- 🚫 不适用（光子工具 vs 电子工具）

#### Scenario: 差距分析
- **WHEN** 对比 13 工具功能点与 PoLaRIS
- **THEN** 生成 `feature_gap_full_analysis.md`
- **AND** 统计每个工具的覆盖率（已有/部分/缺失/不适用）
- **AND** 列出 PoLaRIS 的"独家功能点"（商业工具都没有的）

### Requirement: 一年开发计划
系统 SHALL 生成 2026-06 到 2027-05 的 12 个月开发计划，每个月包含：
- 月份（2026-06、2026-07、...、2027-05）
- 核心目标（1 句话）
- 交付功能点清单（从差距分析中选取优先级最高的）
- 验收标准（可量化）
- 依赖（前置月份）

#### Scenario: 月度计划
- **WHEN** 制定 2026-07 计划
- **THEN** 列出该月要交付的功能点（如"T01 FDTD 亚像素平滑、T03 OptoDesigner DRC 曲线感知"）
- **AND** 标注验收标准（如"通过 test_subpixel_smoothing.py"）
- **AND** 标注依赖（如"依赖 2026-06 的 S 参数框架"）

## 优先级排序原则

一年计划的功能点优先级遵循：
1. **P0 阻断级**：商业工具全有、PoLaRIS 完全缺失的核心能力（如 GDSII 导出曲线离散化）
2. **P1 差距级**：商业工具有、PoLaRIS 部分实现（如 RL 布局规模 200 vs 商业 500M+）
3. **P2 增强级**：PoLaRIS 已有但需提升到商业级（如 DRC 规则数 9 vs 商业 18 类）
4. **P3 创新级**：商业工具都没有、PoLaRIS 独家（如光子 AI 布局 AlphaChip 化）

## 范围边界

- **包含**：13 个工具的功能点收集 + PoLaRIS 功能盘点 + 全量差距 + 12 个月计划
- **不包含**：代码实现（本 spec 仅规划，实现由后续 spec 驱动）
- **不包含**：36 个月路标重写（本 spec 的 12 个月计划是 36 个月路标前 12 个月的细化，不冲突）
