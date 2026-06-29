# 全 Bug 根因分析与彻底修复 Spec

## Why

PoLaRIS v3.3 学术诚信收官审查发现 **140 Bug**（已修 45，未修 **95**），分布在 17 个子包。用户质询"为什么发现了如此之多的 bug 和不足？"，并要求"详细分析以及解决掉所有的问题，每个问题都要确认排查网络检索修复完美解决"。

这反映出三层问题：
1. **根因层**：为什么会产生 95 个未修 Bug？是开发流程缺陷、审查方法变化、还是历史技术债累积？
2. **修复层**：5 P0 + 86 P1 + 4 P2 必须全部修复，每个修复方案需 WebSearch 权威文献验证
3. **预防层**：如何防止未来再次产生类似 Bug？

## What Changes

- **根因分析报告**: 在 `docs/学术诚信检查.md` §7 新增"§7 根因分析与流程改进"，分析 95 Bug 产生的 5 类根因（开发流程/审查方法/技术债/算法复杂度/历史遗留）
- **95 Bug 全部修复**: 按 17 子包分批修复，每个 Bug 修复流程: WebSearch 验证方案 → 代码修复 → 回归测试 → 文档同步
  - 5 P0 未修（Year 1 Q1 优先，168h）：#v3.3-VER-2 / Q-3 / Q-4 / AI-6 / SYS-3
  - 86 P1 未修（按子包聚类修复）：
    - P1-A 算法错误 18 项（含 P0 已修 2 项，剩 16 项）
    - P1-B R03 fall-back 33 项（verification/flow/pipeline/data/io/system）
    - P1-C 文档不符 8 项
    - P1-D "修复中"占位 27 项
  - 4 P2 未修（文献补充）
- **每个 Bug 修复要求**:
  - WebSearch 检索权威文献验证修复方案（来源: arXiv/IEEE/ACM/Nature/官方文档）
  - 代码修复遵循 R03（失败即 raise，禁止 fall-back）/ R04（纯 CPU）/ R05（回归测试）
  - 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15
  - docstring 含 ≥5 文献 URL（R02）
- **预防机制**: 新增 `docs/开发流程防Bug规范.md`（CI 前置审查 checklist + Bug 根因分类模板）
- **BREAKING**: 95 Bug 全部修复后，`docs/学术诚信检查.md` v3.3 → v4.0，综合评分 92% → 98%+

## Impact

- Affected specs:
  - `unify-academic-integrity-checks`（学术诚信基础，本 spec 续作）
  - `build-five-year-commercial-plan`（商业计划依赖 Bug 全修）
  - `fix-p0-pipeline-defects`（已完成的 P0 修复，本 spec 扩展至全部 Bug）
- Affected code: 17 子包 95 Bug 涉及的源码文件（约 50 个 .py 文件）
- Affected docs:
  - `docs/学术诚信检查.md`（v3.3 → v4.0，新增 §7 根因分析 + §5 Bug 状态全更新为"已修"）
  - `docs/开发流程防Bug规范.md`（新增）
  - `操作记录.md`（追加每批修复记录）
  - `商业活动计划表-五年.md`（更新 P0 未修数量 5→0）

## 数据来源与学术诚信（R02）

所有 Bug 修复方案必须 WebSearch 验证:
1. **算法错误修复**: WebSearch 检索原始论文（如 GAE 边界 → Schulman 2015 §3 / Scharfetter-Gummel 1969 / Cocorullo 1999 / Redheffer 1959）
2. **fall-back 修复**: 参考 Python 异常处理最佳实践（PEP 8 / Real Python / pytest 官方）
3. **文献补充**: WebSearch 检索缺失文献（如 quantum/qfdtd.py 补 5 篇量子 FDTD 文献）
4. **代码实现**: 每个修复后用 Read 验证，用 pytest 回归测试
5. 禁止凭经验/记忆直接修复（R01 方案检索规则）

## ADDED Requirements

### Requirement: 根因分析报告

系统 SHALL 在 `docs/学术诚信检查.md` 新增 §7 节，分析 95 Bug 产生的根因。

#### Scenario: 5 类根因识别
- **WHEN** 分析 95 Bug 的产生原因
- **THEN** 输出 5 类根因（每类含 Bug 数 / 典型案例 / 流程缺陷 / 改进措施）：
  1. **历史技术债累积**（约 30 Bug）：MVP 阶段快速迭代遗留，如 M4/M5/M6 硬编码 True
  2. **审查方法升级**（约 25 Bug）：v3.3 引入 Sub-Agent 并行审查 + 7 维度核查，发现旧审查未覆盖的假实现
  3. **算法复杂度高**（约 20 Bug）：FDTD/CPML/RCWA/伴随优化等复杂算法实现易错
  4. **跨子包集成缺陷**（约 15 Bug）：fall-back 静默吞异常，子包边界处理不一致
  5. **文献溯源不足**（约 5 Bug）：R02 ≥5 文献要求未严格执行

### Requirement: 95 Bug 全部修复

系统 SHALL 修复全部 95 未修 Bug，每个 Bug 修复遵循"WebSearch → 代码修复 → 回归测试 → 文档同步"四步流程。

#### Scenario: 5 P0 Bug 修复（Year 1 Q1 优先）
- **WHEN** 修复 #v3.3-VER-2 / Q-3 / Q-4 / AI-6 / SYS-3
- **THEN** 每个 P0 修复:
  - WebSearch 检索权威方案（如 KLM_CNOT → Knill Nature 2001 / 玻色采样 → Aaronson 2011）
  - 代码修复 + 回归测试（pytest 通过）
  - `docs/学术诚信检查.md` §5 状态更新为"已修"

#### Scenario: 86 P1 Bug 修复（按子包分批）
- **WHEN** 修复 P1-A 算法错误 16 项 + P1-B fall-back 33 项 + P1-C 文档 8 项 + P1-D 占位 27 项
- **THEN** 每批修复后:
  - 该子包全部 Bug 状态更新为"已修"
  - 回归测试全通过
  - 操作记录.md 追加该批修复记录

#### Scenario: 4 P2 Bug 修复（文献补充）
- **WHEN** 修复 #v3.3-4/5/6 + #v3.3-Q-6
- **THEN** 每个文件 docstring 补充 ≥5 文献 URL

### Requirement: 预防机制建立

系统 SHALL 新增 `docs/开发流程防Bug规范.md`，建立 5 类预防机制。

#### Scenario: CI 前置审查 checklist
- **WHEN** 新代码提交前
- **THEN** 强制执行 checklist（fall-back 扫描 / 文献 ≥5 / 回归测试 / 函数 ≤80 行）

#### Scenario: Bug 根因分类模板
- **WHEN** 未来发现新 Bug
- **THEN** 按根因分类（历史债/审查方法/算法复杂度/集成缺陷/文献不足）记录，预防同类复发

## MODIFIED Requirements

### Requirement: 学术诚信检查文档 v4.0
`docs/学术诚信检查.md` v3.3 → v4.0:
- §1 版本日志新增 v4.0 条目（95 Bug 全修，综合评分 98%+）
- §5 Bug 历史全部 140 Bug 状态更新为"已修"
- §6 综合评分 92% → 98%+
- 新增 §7 根因分析与流程改进
- 新增 §8 预防机制

## REMOVED Requirements

无（本 spec 为纯修复 + 新增预防，不删除既有功能）。

## 验收标准

- [ ] `docs/学术诚信检查.md` §7 根因分析含 5 类根因（每类含 Bug 数/案例/改进措施）
- [ ] 95 Bug 全部修复（5 P0 + 86 P1 + 4 P2），每个 Bug 在 §5 状态为"已修"
- [ ] 每个 Bug 修复含 WebSearch 文献验证（来源 URL 记录在 docstring）
- [ ] 每个 Bug 修复含回归测试（pytest 通过）
- [ ] `docs/开发流程防Bug规范.md` 存在，含 CI checklist + 根因分类模板
- [ ] `docs/学术诚信检查.md` v4.0 综合评分 ≥98%
- [ ] `商业活动计划表-五年.md` 更新 P0 未修数量 5→0
- [ ] 操作记录.md 追加每批修复记录
