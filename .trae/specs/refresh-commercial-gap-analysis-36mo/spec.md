# 商业对比分析全面刷新 + 36个月里程碑规划 Spec

## Why

PoLaRIS 自 2026-06-20 启动以来已迭代至第 94 轮（截至 2026-06-22），累计完成 2330+ 测试、0 警告 0 错误质量门禁、9 foundry DRC runset、81 器件 PDK、Apollo/LiDAR/TILOS 三大公开 benchmark 移植。但现有 `docs/commercial_gap_analysis.md` 仍停留在第 79 轮的评分（综合 6.0/10，差距 -2.7），未反映第 80-94 轮的进展（INSERTION_LOSS_DB 评估、process_node 一致性、质量门禁零违规、器件损耗参数补全、DRV 评估等）。

用户要求：
1. 进行一次**完整的商业对比分析**，总结到今天（2026-06-22）为止的差距
2. **重新编写**相关对比文档（刷新而非新增，覆盖 `commercial_gap_analysis.md` 与 `industry_alignment_roadmap.md`）
3. 制定 **36 个月里程碑**，每个里程碑只做里程碑内的事情，不扩散、不超前
4. 刷新文档后更新版本号，依次累加（v1.0 → v2.0）
5. 先给用户看详细报告，再做下一步决定

## What Changes

- **BREAKING**: 完全覆盖重写 `docs/commercial_gap_analysis.md`（v1.0 → v2.0），反映第 80-94 轮进展
- **BREAKING**: 完全覆盖重写 `docs/industry_alignment_roadmap.md`（v1.0 → v2.0），加入 36 个月里程碑
- 新增 `docs/commercial_gap_analysis_v2.md` 详细报告（作为给用户审阅的独立报告文档）
- 刷新 `docs/roadmap.md` 版本号（v1.0 → v2.0），与 36 个月里程碑对齐
- 同步更新 `操作记录.md` 第 94 轮记录

## Impact

- Affected specs: 无（文档刷新，不涉及代码 spec）
- Affected code: 无代码改动，仅文档刷新
- Affected docs:
  - `docs/commercial_gap_analysis.md`（v1.0 → v2.0，覆盖重写）
  - `docs/industry_alignment_roadmap.md`（v1.0 → v2.0，覆盖重写）
  - `docs/roadmap.md`（v1.0 → v2.0，刷新版本号）
  - `docs/commercial_gap_analysis_v2.md`（新增详细报告）
  - `操作记录.md`（追加第 94 轮记录）

## 数据来源与学术诚信

所有评分、差距量化、里程碑目标均基于：
- 第 80-94 轮操作记录（`操作记录.md` 第 8393-8760 行）
- 现有 `docs/commercial_gap_analysis.md` v1.0 评分基线（6.0/10）
- 现有 `docs/industry_alignment_roadmap.md` v1.0 业界对照矩阵
- 商业工具公开文档（Lumerical/Luceda/Synopsys/Cadence/Tidy3D/gdsfactory）
- 学术前沿（AlphaChip Nature 2021/2024、Apollo arXiv 2025、LiDAR ISPD 2025、PhIDO arXiv 2025、DREAMPlace DAC 2019/TCAD 2020、TILOS MacroPlacement）

**禁止造假**：所有评分变更必须列出对应的轮次与具体改进内容，不得凭空调整分数。

---

## ADDED Requirements

### Requirement: 商业对比分析全面刷新（v2.0）

系统 SHALL 提供一份覆盖重写的商业对比分析文档（`docs/commercial_gap_analysis.md` v2.0），反映 2026-06-22 截至第 94 轮的真实状态。

#### 评分刷新规则

每个维度的评分变更必须满足：
1. 列出 v1.0 基线分数
2. 列出 v2.0 新分数
3. 列出分数变更的具体轮次与改进内容
4. 列出分数变更的文献/操作记录依据

#### 评分维度（10 项，与 v1.0 一致）

| 评估维度 | v1.0 分数 | v2.0 分数 | 变更依据 |
|----------|----------|----------|----------|
| 布局算法先进性 | 7/10 | 7/10 | 第 92 轮质量门禁零违规（无算法新进展，维持） |
| 布线算法完整度 | 6/10 | 6/10 | 第 94 轮 DRV 评估补全（评估完整性提升，算法本身无新进展，维持） |
| 仿真精度 | 5/10 | 5/10 | 无新进展（维持） |
| PDK 覆盖 | 4/10 | 4/10 | 无新进展（维持） |
| AI 能力 | 7/10 | 7/10 | 无新进展（维持） |
| 工艺节点支持 | 5/10 | 5/10 | 第 91 轮 process_node 一致性修复（数据质量提升，覆盖范围无变化，维持） |
| GDS/DRC/LVS 链路 | 4/10 | 4/10 | 无新进展（维持） |
| 性能规模 | 6/10 | 6/10 | 无新进展（维持） |
| 开源开放 | 9/10 | 9/10 | 无新进展（维持） |
| 文档与测试 | 8/10 | 9/10 | 第 92 轮质量门禁零违规 + 第 93 轮器件损耗参数补全 + 第 94 轮 DRV 评估（+1） |
| **综合得分** | **6.0/10** | **6.1/10** | **+0.1** |

#### Scenario: 用户审阅详细报告
- **WHEN** 用户要求查看商业对比分析详细报告
- **THEN** 系统提供 `docs/commercial_gap_analysis_v2.md`，包含完整评分矩阵、差距清单、36 个月里程碑
- **AND** 报告中每个评分变更均可溯源到具体轮次与操作记录

#### Scenario: 文档版本号累加
- **WHEN** 文档刷新完成
- **THEN** `docs/commercial_gap_analysis.md` 头部版本号从 v1.0 更新为 v2.0
- **AND** `docs/industry_alignment_roadmap.md` 头部版本号从 v1.0 更新为 v2.0
- **AND** `docs/roadmap.md` 头部版本号从 v1.0 更新为 v2.0

### Requirement: 36 个月里程碑规划

系统 SHALL 提供一份 36 个月（2026-07 至 2029-06）的里程碑规划，每个里程碑只做里程碑内的事情，不扩散、不超前。

#### 里程碑划分（6 个里程碑，每个 6 个月）

| 里程碑 | 时间窗 | 核心目标 | 严格边界 |
|--------|--------|----------|----------|
| **M1: v1.0 MVP** | 2026-07 ~ 2026-12 | 工业链路最小闭环（500 器件 + 3 foundry + DRC/LVS） | 仅做 P0-1/P0-2/P0-3 的最小子集，不碰 P1/P2 |
| **M2: v1.5 规模扩展** | 2027-01 ~ 2027-06 | 1000 器件规模 + 5 foundry PDK + 公开 benchmark 评估 | 仅做 P0-2 规模扩展 + P0-3 PDK 扩展 + P1-5 benchmark，不碰 AI 算法升级 |
| **M3: v2.0 AI 算法升级** | 2027-07 ~ 2027-12 | Edge-GNN + DREAMPlace GPU warm-start + Global-Detail 分层布线 | 仅做 P1-1/P1-2/P1-4，不碰逆向设计/光电协同 |
| **M4: v2.5 仿真精度提升** | 2028-01 ~ 2028-06 | MEEP FDTD 集成 + Tidy3D 云 API + S 参数校准流程 | 仅做 P0-4，不碰 GUI/LLM Agent |
| **M5: v3.0 商业化领先** | 2028-07 ~ 2028-12 | 逆向设计 + 光电协同仿真 + 5+ foundry 认证 | 仅做 P2-1/P2-2，不碰量子光子 |
| **M6: v3.5 生态扩展** | 2029-01 ~ 2029-06 | LLM Agent + 量子光子 PDK + KLayout 级 GUI | 仅做 P2-3/P2-4/P2-5 |

#### 里程碑纪律规则

1. **不扩散**：每个里程碑只完成该里程碑列出的任务，不得提前做下一里程碑的任务
2. **不超前**：不得在 M1 阶段做 M3 的 Edge-GNN，不得在 M2 阶段做 M4 的 FDTD
3. **版本号累加**：每完成一个里程碑，版本号累加（v1.0 → v1.5 → v2.0 → v2.5 → v3.0 → v3.5）
4. **里程碑验收**：每个里程碑结束前必须通过验收标准，未通过不得进入下一里程碑

#### Scenario: 里程碑边界严格执行
- **WHEN** 在 M1 阶段（2026-07 ~ 2026-12）
- **THEN** 只能做 P0-1（DRC/LVS）、P0-2（500 器件）、P0-3（3 foundry）的最小子集
- **AND** 不得做 Edge-GNN（M3）、FDTD（M4）、逆向设计（M5）、LLM Agent（M6）

#### Scenario: 里程碑验收
- **WHEN** M1 时间窗结束（2026-12）
- **THEN** 必须验证：500 器件规模跑通、3 foundry DRC runset 认证、LVS 完整闭环
- **AND** 验收通过后版本号从 v1.0 累加到 v1.5（进入 M2）

### Requirement: 文档刷新而非新增

系统 SHALL 覆盖重写现有对比文档，而非新增并行文档（除详细报告 `commercial_gap_analysis_v2.md` 外）。

#### 覆盖重写清单

| 文档 | 操作 | 版本号变更 |
|------|------|----------|
| `docs/commercial_gap_analysis.md` | 覆盖重写 | v1.0 → v2.0 |
| `docs/industry_alignment_roadmap.md` | 覆盖重写 | v1.0 → v2.0 |
| `docs/roadmap.md` | 覆盖重写（仅版本号+里程碑对齐） | v1.0 → v2.0 |
| `docs/commercial_gap_analysis_v2.md` | 新增（详细报告，供用户审阅） | v2.0 |
| `操作记录.md` | 追加（第 94 轮记录） | - |

#### Scenario: 文档覆盖重写
- **WHEN** 文档刷新完成
- **THEN** `docs/commercial_gap_analysis.md` 内容完全反映 v2.0 状态
- **AND** 不保留 v1.0 的过时评分（6.0/10 替换为 6.1/10）
- **AND** 头部标注"文档版本: v2.0，刷新日期: 2026-06-22"

---

## MODIFIED Requirements

### Requirement: 商业差距分析文档（v1.0 → v2.0）

v1.0 的评分基线（6.0/10）已过时，需刷新为 v2.0（6.1/10），并补充第 80-94 轮的具体进展。

**v1.0 → v2.0 变更点**：
1. 综合得分 6.0 → 6.1（+0.1，文档与测试维度提升）
2. 文档与测试 8 → 9（第 92 轮质量门禁零违规 + 第 93 轮器件损耗补全 + 第 94 轮 DRV 评估）
3. 新增 36 个月里程碑规划（M1-M6）
4. 新增第 80-94 轮进展记录
5. 刷新所有"已修复"标记

---

## REMOVED Requirements

### Requirement: v1.0 过时评分
**Reason**: v1.0 评分（6.0/10）未反映第 80-94 轮进展，已过时
**Migration**: 完全覆盖重写为 v2.0，评分刷新为 6.1/10，所有评分变更可溯源

### Requirement: v1.0 路线图（3/6/12-24 个月）
**Reason**: v1.0 路线图时间窗模糊（"3 个月"/"6-12 个月"/"12-24 个月"），不符合用户"36 个月里程碑，每个里程碑只做里程碑内的事情"的要求
**Migration**: 替换为 6 个 6 个月里程碑（M1-M6），每个里程碑有严格时间窗与边界
