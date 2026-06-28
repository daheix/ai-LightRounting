# 五年商业活动计划（PoLaRIS 商业化推进）Spec

## Why

PoLaRIS 已完成 v3.3 学术诚信收官审查（22 子包 / 357 文件 / 120,692 行 / 140 Bug 标注 / P0 全修 / 综合评分 92%），技术基线已接近商业可用门槛，但仍有大量模块不满足商业使用要求（详见 `docs/学术诚信检查.md` §3.1-§3.22 与 §5 Bug 历史）。

用户要求：
1. **再一次分析**哪些模块无法满足商业使用
2. **检索网络/商业工具/代码实际未实现的部分**，对照学术诚信报告与诚信原则
3. 若展开**商业活动**，还需要做哪些工作来推动商业化
4. 产出 `商业活动计划表-五年.md`

## What Changes

- **新增** `商业活动计划表-五年.md`（根目录，按用户指定文件名）：五年（60 个月，2026H2-2031H1）商业活动计划表
- 基于三大数据源交叉分析：
  1. `docs/学术诚信检查.md` v3.3（140 Bug + 22 子包完成度 + R02/R03/R04/R05 合规状态）
  2. 网络检索商业光子 EDA 工具功能矩阵（Lumerical/Luceda/Synopsys/Tidy3D/VPIphotonics/Siemens L-Edit/gdsfactory/KLayout/sax/simphony）
  3. 源码实际实现核查（grep/ls/read 验证功能是否真实存在）
- **BREAKING**: 不覆盖现有 `docs/36-RoundMap.md` / `docs/commercial_gap_analysis.md` / `docs/industry_alignment_roadmap.md`，本文件聚焦"商业活动"维度（营收/客户/市场/合作/融资/产品定价/销售渠道），与既有"技术路标"互补
- 同步更新 `操作记录.md` 追加本轮商业分析记录

## Impact

- Affected specs:
  - `refresh-commercial-gap-analysis-36mo`（技术差距分析，本 spec 引用其结论）
  - `build-36-month-roundmap`（36 月技术路标，本 spec 引用其里程碑）
  - `unify-academic-integrity-checks`（学术诚信基础，本 spec 引用其 Bug 清单）
- Affected code: 无代码改动，纯商业规划文档
- Affected docs:
  - `商业活动计划表-五年.md`（新增，根目录）
  - `操作记录.md`（追加本轮记录）

## 数据来源与学术诚信（R02）

所有商业数据必须真实可溯源：
1. **商业工具功能矩阵**: WebSearch + WebFetch 检索官方文档（Lumerical/Ansys、Luceda、Synopsys OptoDesigner、Tidy3D、VPIphotonics、Siemens L-Edit、Cadence Virtuoso、gdsfactory、KLayout、sax、simphony、OpenROAD）
2. **市场规模数据**: LightCounting / Yole / Omdia / MarketsandMarkets 公开报告
3. **学术诚信基础**: `docs/学术诚信检查.md` v3.3 的 140 Bug 清单 + 22 子包完成度评估
4. **代码实际实现核查**: 对每个声称"已实现"的功能，用 `grep`/`ls`/`Read` 验证源码真实存在
5. 禁止造假数据（R03 禁止 fall-back 同源原则）：所有市场预测数字必须标注来源或标注为"基于 X 假设的估算"

## ADDED Requirements

### Requirement: 五年商业活动计划表

系统 SHALL 提供一份五年（2026H2-2031H1，60 个月）商业活动计划表，覆盖以下维度：

#### Scenario: 商业化准备阶段（Year 1: 2026H2-2027H1）
- **WHEN** PoLaRIS 当前综合评分 92%，P0 Bug 已修但仍有 100+ 中低优先级 Bug
- **THEN** 计划表给出 Year 1 商业化准备任务：技术债清理 / 商业授权合规 / 首批客户 PoC / 定价模型 / 法律实体

#### Scenario: 早期客户与产品化阶段（Year 2: 2027H2-2028H1）
- **WHEN** 技术债基本清理完成，首批 PoC 客户反馈收集
- **THEN** 计划表给出 Year 2 任务：正式产品发布 / 3-5 早期付费客户 / 销售渠道建立 / 合作伙伴生态

#### Scenario: 规模化与市场扩张阶段（Year 3: 2028H2-2029H1）
- **WHEN** 产品已验证，早期客户稳定付费
- **THEN** 计划表给出 Year 3 任务：规模化销售 / 国际市场拓展 / 行业标准参与 / A 轮融资

#### Scenario: 行业领先与生态建设阶段（Year 4: 2029H2-2030H1）
- **WHEN** 营收达到一定规模，品牌认知建立
- **THEN** 计划表给出 Year 4 任务：行业领先地位 / 开发者生态 / 教育合作 / B 轮融资

#### Scenario: 退出准备与平台化阶段（Year 5: 2030H2-2031H1）
- **WHEN** 商业模式成熟，可持续盈利
- **THEN** 计划表给出 Year 5 任务：平台化转型 / IPO 或并购准备 / 全球化运营

### Requirement: 商业可行性差距分析

系统 SHALL 基于学术诚信检查报告，列出当前不满足商业使用的模块清单：

#### Scenario: 不满足商业使用的模块识别
- **WHEN** 分析 `docs/学术诚信检查.md` v3.3 的 140 Bug + 22 子包完成度
- **THEN** 输出"不满足商业使用模块清单"，每个模块标注：
  - 模块名 / Bug 数 / 严重度 / 商业影响 / 修复优先级 / 预估修复工时
  - 按 P0（阻断商业使用）/ P1（影响商业信誉）/ P2（优化项）分级

#### Scenario: 商业工具功能差距识别
- **WHEN** 检索 Lumerical/Luceda/Synopsys 等商业工具功能清单
- **THEN** 输出"功能差距矩阵"，每个差距标注：
  - 商业工具功能 / PoLaRIS 现状 / 差距大小 / 补齐优先级 / 预估工时

### Requirement: 商业活动五年时间表

系统 SHALL 提供五年商业活动时间表（60 个月，按季度粒度）：

#### Scenario: 季度粒度计划
- **WHEN** 制定五年计划
- **THEN** 每个季度（Q1-Q20）列出：
  - 技术里程碑（基于 36-RoundMap 与学术诚信 Bug 修复）
  - 商业里程碑（客户签约 / 营收目标 / 合作伙伴 / 融资）
  - 组织里程碑（团队扩张 / 关键岗位招聘）
  - 合规里程碑（License / IP / 认证）

### Requirement: 营收与融资预测

系统 SHALL 提供五年营收与融资预测（基于公开市场数据 + 合理假设）：

#### Scenario: 营收预测
- **WHEN** 预测 Year 1-5 营收
- **THEN** 每年给出：
  - 客户数假设（基于 LightCounting/Yole 市场规模 + 合理市占率）
  - ARPU 假设（基于商业工具定价 Lumerical ~$50k/seat/yr, Luceda ~$30k/seat/yr）
  - 营收预测（客户数 × ARPU，标注"基于 X 假设的估算"）
  - 增长率假设

#### Scenario: 融资预测
- **WHEN** 预测 Year 1-5 融资
- **THEN** 每年给出：
  - 融资轮次（种子 / Pre-A / A / B / Pre-IPO）
  - 融资金额（基于同行业可比公司）
  - 估值预测
  - 资金用途

## MODIFIED Requirements

### Requirement: 商业化文档体系
PoLaRIS 现有 `docs/36-RoundMap.md`（技术路标）+ `docs/commercial_gap_analysis.md`（技术差距）+ `docs/industry_alignment_roadmap.md`（行业对齐）。新增 `商业活动计划表-五年.md` 聚焦"商业活动"维度（营收/客户/市场/融资），与技术文档互补，不重叠不冲突。

## REMOVED Requirements

无（本 spec 为纯新增，不删除既有功能或文档）。

## 验收标准

- [ ] `商业活动计划表-五年.md` 存在于 `/workspace/` 根目录
- [ ] 文档含三大部分：①不满足商业使用模块清单 ②商业工具功能差距矩阵 ③五年商业活动时间表
- [ ] 所有市场数据标注来源（LightCounting/Yole/Omdia/官方文档）
- [ ] 所有预测数字标注"基于 X 假设的估算"
- [ ] 引用 `docs/学术诚信检查.md` v3.3 的 Bug 数据真实准确
- [ ] 引用 `docs/36-RoundMap.md` 的技术里程碑真实准确
- [ ] 操作记录.md 追加本轮商业分析记录
