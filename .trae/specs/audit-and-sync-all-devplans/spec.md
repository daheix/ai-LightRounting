# 开发计划审核与文档同步更新 Spec

## Why

PoLaRIS 项目存在**严重的文档与代码不一致**问题：`roundmap_final_report.md` 虚假声称 R01-R36 全部完成、综合得分 9.5（违反 R02 学术诚信），但实际 git log 无对应路标提交，13 个核心路标模块代码缺失（R10/R15/R16/R17/R19/R20/R21/R27/R28/R31/R32/R34/R35）。`R36_acceptance_report.md` 记录真实得分 7.88（未超越行业最高 9.0）。用户要求审核所有开发计划与设计文档、同步更新、完成所有未完成的开发计划。

## 审计发现（真实状态 vs 文档声明）

### 1. 36 月路标（R01-R36）真实状态

| 路标 | 文档声明 | 实际代码 | 真实状态 |
|------|----------|----------|----------|
| R01-R06 | 已完成（AGENTS.md §11） | git reflog 确认 | ✅ 真实完成 |
| R07 | 进行中（AGENTS.md §11） | hierarchical_drc.py 存在 | ⚠️ 代码有但未合并验收 |
| R08 | final_report 声称完成 | klayout_drc.py 存在 | ⚠️ 代码有但未合并验收 |
| R10 | final_report 声称完成 | routing/gdsfactory_style.py 缺失 | ❌ 未实现 |
| R13 | stage3_report 声称完成 | sim/system_level.py 存在 | ⚠️ 代码有但未合并验收 |
| R15 | stage3_report 声称完成 | sim/picwave_backend.py 缺失 | ❌ 未实现 |
| R16 | stage3_report 声称完成 | sim/eme_backend.py 缺失 | ❌ 未实现（注：sim/eme/ 目录存在） |
| R17 | stage3_report 声称完成 | sim/photoelectric_cosim.py 缺失 | ❌ 未实现 |
| R19 | stage4_report 声称完成 | gui/layout_editor.py 缺失 | ❌ 未实现 |
| R20 | stage4_report 声称完成 | flow/design_intent.py 缺失 | ❌ 未实现 |
| R21 | stage4_report 声称完成 | routing/commercial_router.py 缺失 | ❌ 未实现 |
| R25 | stage5_report 声称完成 | sim/caphe_backend.py 存在 | ⚠️ 代码有但未合并验收 |
| R27 | stage5_report 声称完成 | sim/tidy3d_backend.py 缺失 | ❌ 未实现 |
| R28 | stage5_report 声称完成 | inverse/adjoint_optimizer.py 缺失 | ❌ 未实现 |
| R31 | final_report 声称完成 | sim/lumerical_fdtd.py 缺失 | ❌ 未实现 |
| R32 | final_report 声称完成 | sim/interconnect_backend.py 缺失 | ❌ 未实现 |
| R34 | final_report 声称完成 | rl/edge_gnn.py 缺失 | ❌ 未实现 |
| R35 | final_report 声称完成 | rl/pretraining.py 缺失 | ❌ 未实现 |

**结论**：13 个核心路标模块代码缺失，4 个模块有代码但未正式合并验收。

### 2. 2028 开发计划（43 聚类 Sprint 0-7）真实状态

- `execute-2028-development-plan/tasks.md`：全部 `[ ]` 未完成（Sprint 0-7，43 聚类，940 功能点）
- `year_plan_2026_06_2027_05.md`：155 功能点计划，状态未明确标记

### 3. 虚假报告清单（违反 R02 学术诚信）

| 文档 | 虚假声明 | 真实状态 | 处理方式 |
|------|----------|----------|----------|
| `docs/roundmap_final_report.md` | R01-R36 全部完成，得分 9.5 | 实际 7.88，13 模块缺失 | 重写为真实状态 |
| `docs/roundmap_stage3_report.md` | R13-R18 完成，得分 7.9 | R15/R16/R17 缺失 | 标注真实状态 |
| `docs/roundmap_stage4_report.md` | R19-R24 完成，得分 8.4 | R19/R20/R21 缺失 | 标注真实状态 |
| `docs/roundmap_stage5_report.md` | R25-R30 完成，得分 8.9 | R27/R28 缺失 | 标注真实状态 |
| `docs/roundmap/R36_acceptance_report.md` | 得分 7.88（较真实） | 需确认代码对应 | 保留，补充代码验证 |

## What Changes

- **审核**：全量审核 16 个 spec 目录 + 36 月路标文档 + 2028 开发计划 + 年度计划 + 设计文档的真实完成状态
- **修正**：重写 4 份虚假验收报告（final/stage3/stage4/stage5），反映真实代码状态（R02 学术诚信）
- **同步**：更新 AGENTS.md §11 当前进度、`docs/36-RoundMap.md` 状态标记、`docs/设计文档.md` 模块清单
- **实现**：按 P0-P3 优先级实现 13 个缺失核心路标模块（每模块含代码 + 测试 + 文献引用 + 无 fall-back）
- **验证**：每个模块实现后运行质量门禁 + 回归测试 + git 提交合并 main

### 优先级排序（P0 阻断级优先）

| 优先级 | 路标 | 模块 | 理由 |
|--------|------|------|------|
| P0 | R15 | sim/picwave_backend.py | 阶段3 时域仿真核心，R16/R17 依赖 |
| P0 | R16 | sim/eme_backend.py | 阶段3 EME 仿真，R17 依赖（sim/eme/ 目录已存在） |
| P0 | R17 | sim/photoelectric_cosim.py | 阶段3 光电协同，R18 验收依赖 |
| P0 | R27 | sim/tidy3d_backend.py | 阶段5 FDTD 核心云 API，R28 依赖 |
| P0 | R28 | inverse/adjoint_optimizer.py | 阶段5 逆向设计，R29 依赖 |
| P1 | R10 | routing/gdsfactory_style.py | 阶段2 布线策略，R11 依赖 |
| P1 | R19 | gui/layout_editor.py | 阶段4 GUI，R20 依赖 |
| P1 | R20 | flow/design_intent.py | 阶段4 Design Intent，R21 依赖 |
| P1 | R21 | routing/commercial_router.py | 阶段4 商业布线，R22 依赖 |
| P2 | R31 | sim/lumerical_fdtd.py | 阶段6 FDTD 3D |
| P2 | R32 | sim/interconnect_backend.py | 阶段6 INTERCONNECT |
| P2 | R34 | rl/edge_gnn.py | 阶段6 Edge-GNN（R04 不参与 GPU） |
| P2 | R35 | rl/pretraining.py | 阶段6 预训练（R04 不参与 GPU 分布式） |

## Impact

- Affected specs: 全部 16 个 spec 目录（审核完成状态）、`execute-2028-development-plan`（启动 Sprint 0-7）
- Affected code: `src/polaris/sim/`（+4 模块）、`src/polaris/routing/`（+2 模块）、`src/polaris/gui/`（+1 模块）、`src/polaris/flow/`（+1 模块）、`src/polaris/inverse/`（+1 模块）、`src/polaris/rl/`（+2 模块）、`src/polaris/io/`（+2 模块）
- Affected docs: `docs/roundmap_final_report.md`（重写）、`docs/roundmap_stage3/4/5_report.md`（修正）、`AGENTS.md` §11（刷新）、`docs/设计文档.md`（同步模块清单）、`docs/36-RoundMap.md`（状态标记）

## ADDED Requirements

### Requirement: 文档真实性校验

系统 SHALL 确保所有验收报告、进度文档、设计文档中的完成状态声明与实际代码（git log + 文件存在性）严格一致，禁止任何虚假完成声明。

#### Scenario: 验收报告与代码一致性
- **WHEN** 验收报告声明某路标已完成
- **THEN** 对应代码模块文件必须存在
- **AND** git log 必须有对应提交
- **AND** 测试必须通过
- **ELSE** 报告须标注"未完成"或"部分完成"

### Requirement: 缺失模块按优先级实现

系统 SHALL 按 P0→P1→P2 优先级依次实现 13 个缺失核心路标模块，每模块包含：代码实现 + 单元测试（≥6 个）+ 文献引用（≥5 个 URL）+ 无 fall-back 声明 + 质量门禁通过。

#### Scenario: P0 模块实现
- **WHEN** 实现 R15 picwave_backend.py
- **THEN** 时域仿真支持非线性效应（Kerr/TPA/自由载流子）
- **AND** 200 器件时域仿真 < 60 秒
- **AND** 新增 ≥8 个时域仿真测试

### Requirement: 2028 开发计划启动

系统 SHALL 启动 `execute-2028-development-plan` 的 Sprint 0-7，按依赖关系顺序执行 43 聚类开发任务，每聚类完成验收后标记 `[x]`。

## MODIFIED Requirements

### Requirement: AGENTS.md §11 当前进度刷新

AGENTS.md §11 当前进度从"R01-R06 已完成，R07 进行中"刷新为真实状态：R01-R08 代码已有（R07/R08 待验收），R10/R15-R17/R19-R21/R27/R28/R31/R32/R34/R35 共 13 模块待实现。

## REMOVED Requirements

### Requirement: 虚假验收报告

**Reason**: `roundmap_final_report.md` 等 4 份报告声明 R01-R36 全部完成得分 9.5，与实际代码状态不符（13 模块缺失，真实得分 7.88），违反 R02 学术诚信。
**Migration**: 重写为真实状态报告，保留 `R36_acceptance_report.md`（7.88 分，较真实）作为基准。
