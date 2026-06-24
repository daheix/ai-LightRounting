# 36-RoundMap 详细技术交付文档（每路标一文件）Spec

## Why

`docs/36-RoundMap.md` 已制定 36 个月逐月路标（R1-R36），但每月仅含交付目标/验收标准/依赖的简要描述。用户要求为每个路标制定**详细的技术交付文档**（每个路标一个文件），包含：
1. **学术诚信**：学术论文追踪、公式推导、理论依据
2. **怎么能做得更好**：现有开源方案的缺点分析 + 改进计划
3. **100% 复刻 + 更优秀方案**：源代码解读分析 + 改进路线图
4. **权威资源调研**：基于用户提供的 6 大类权威资源清单（arXiv/IEEE/ACM/SpringerLink/USENIX/Stack Overflow/Hacker News/GitHub Discussions/IETF RFC/Google Research 等）

## What Changes

- 新增 `docs/roundmap/` 目录，存放 36 个路标详细技术文档
- 每个路标一个文件：`docs/roundmap/R01.md` 至 `docs/roundmap/R36.md`
- 每个文件含统一结构：学术论文追踪 / 公式与理论 / 开源方案缺点 / 源码解读 / 改进计划 / 权威资源引用
- 新增 `docs/roundmap/README.md` 索引文件

## Impact

- Affected specs: `build-36-month-roundmap`（本 spec 是其详细化补充）
- Affected code: 无代码改动，纯文档
- Affected docs:
  - `docs/roundmap/README.md`（新增索引）
  - `docs/roundmap/R01.md` ~ `docs/roundmap/R36.md`（新增 36 个文件）

## 数据来源与学术诚信

所有论文/公式/方案必须来自用户提供的 6 大类权威资源：
1. **国际顶会期刊**：arXiv / IEEE Xplore / ACM DL / SpringerLink / ScienceDirect / Nature CS / MDPI / USENIX / VLDB / SIGMOD
2. **工程师实战论坛**：Stack Overflow / Hacker News / Reddit / Dev.to / Medium / InfoQ / CodeProject
3. **开源官方社区**：GitHub Discussions / GitHub Issues / GitLab / Apache / CNCF
4. **国际标准**：IETF RFC / W3C / OASIS / OpenAPI / ISO-IEC
5. **大厂研究院**：Google Research / Meta Engineering / AWS Architecture / Microsoft Research / Cloudflare Blog / Netflix Tech
6. **垂直社区**：High Scalability / Database Internals / Distributed Systems Reading Group / Martin Fowler Blog

**权威优先级**：国际顶会论文 > 大厂官方工程博客 > 海外高赞社区实践 > 国内技术内容

**禁止造假**：所有论文须标注 arXiv ID / DOI / URL，所有公式须标注推导来源，所有源码解读须基于真实代码。

---

## ADDED Requirements

### Requirement: 每个路标详细技术交付文档

系统 SHALL 为 36-RoundMap 的每个路标（R1-R36）提供一份详细技术交付文档，每个路标一个独立文件。

#### 文件命名规则

- 路标文件：`docs/roundmap/R01.md` 至 `docs/roundmap/R36.md`（两位数字，零填充）
- 索引文件：`docs/roundmap/README.md`

#### 每个路标文档的统一结构

每个 `R{n}.md` 文件须包含以下 10 个章节：

```markdown
# R{n}（YYYY-MM）：{交付目标标题}

**路标编号**: R{n}
**月份**: YYYY-MM
**追赶对象**: {工具名}
**综合得分目标**: {当前} → {目标}
**文档版本**: v1.0
**创建日期**: 2026-06-22

## 1. 交付目标摘要
（该月交付的具体功能/改进，100-200 字）

## 2. 学术论文追踪
（该路标相关的 3-5 篇顶会/期刊论文，每篇含：标题/作者/会议/年份/arXiv ID 或 DOI/URL/核心贡献/对本路标的指导意义）

## 3. 公式与理论依据
（该路标涉及的数学公式，含：公式 LaTeX 表达/变量定义/推导来源/适用条件/数值示例）

## 4. 开源方案缺点分析
（现有开源工具的缺点，基于 GitHub Issues/Discussions/Stack Overflow 真实问题，每条含：问题描述/影响/来源 URL/根因分析）

## 5. 源代码解读分析
（PoLaRIS 现有相关代码的解读，含：文件路径/关键函数/当前实现逻辑/局限性/改进点）

## 6. 100% 复刻 + 更优秀方案
（如何 100% 复刻追赶对象的能力，并提出更优秀方案，含：复刻清单/改进点/创新点标注"创新"/预期收益）

## 7. 改进计划路线图
（该月内的改进步骤，含：步骤/依赖/验收标准/风险）

## 8. 权威资源引用
（本文件引用的所有权威资源 URL 列表，按 6 大类分类）

## 9. 交叉验证
（国外工程实践 + 学术论文原理 + 官方标准的三方交叉验证表）

## 10. 学术诚信声明
（所有数据来源可溯源，无造假，创新点已标注）
```

#### Scenario: 路标文档可溯源
- **WHEN** 用户查看某个路标文档（如 R01.md）
- **THEN** 文档含 3-5 篇论文（每篇有 arXiv ID/DOI/URL）
- **AND** 文档含数学公式（含 LaTeX 表达与推导来源）
- **AND** 文档含开源方案缺点（基于 GitHub Issues/Stack Overflow 真实问题）
- **AND** 文档含 PoLaRIS 源码解读（含文件路径与关键函数）
- **AND** 文档含权威资源引用（按 6 大类分类）

#### Scenario: 36 个路标文档完整
- **WHEN** 所有路标文档编写完成
- **THEN** `docs/roundmap/` 目录含 R01.md 至 R36.md 共 36 个文件
- **AND** 含 README.md 索引文件
- **AND** 每个文件含统一 10 章节结构

### Requirement: 索引文件

系统 SHALL 提供一个索引文件 `docs/roundmap/README.md`，汇总 36 个路标文档。

#### 索引文件结构

```markdown
# 36-RoundMap 详细技术交付文档索引

**文档版本**: v1.0
**创建日期**: 2026-06-22

## 路标总览
（6 阶段 × 6 月表格，含链接到每个 R{n}.md）

## 阶段 1：R1-R6 追赶 sax + simphony
- [R01](R01.md) - ...
- ...

## 阶段 2-6（同上）

## 权威资源清单
（用户提供的 6 大类权威资源列表）
```

#### Scenario: 索引可导航
- **WHEN** 用户打开 README.md
- **THEN** 可点击链接跳转到任意路标文档
- **AND** 含 6 大类权威资源清单

### Requirement: 学术诚信与交叉验证

每个路标文档须满足学术诚信要求：

1. **论文可溯源**：每篇论文标注 arXiv ID / DOI / URL
2. **公式可推导**：每个公式标注推导来源与适用条件
3. **源码可定位**：每段源码解读标注文件路径与行号
4. **缺点可验证**：每个开源方案缺点标注 GitHub Issue 编号或 Stack Overflow 链接
5. **创新点标注**：所有改进方案中的创新点标注"创新"标签并记录逻辑
6. **交叉验证**：国外工程实践 + 学术论文原理 + 官方标准三方验证

#### Scenario: 交叉验证表
- **WHEN** 查看路标文档第 9 章节
- **THEN** 含三方交叉验证表（工程实践/学术论文/官方标准）
- **AND** 三方结论一致或差异已说明

---

## MODIFIED Requirements

无（本 spec 为新增，不修改已有 spec）

## REMOVED Requirements

无（本 spec 不移除已有需求）
