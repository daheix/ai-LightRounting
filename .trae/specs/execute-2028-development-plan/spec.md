# 2028 开发计划执行框架 Spec

## Why

PoLaRIS 已完成 985 功能点全量分析（43 聚类 / 940 有效功能点 / 去重比 34×）、43 份聚类算法文档（16480 行）、Python 代码开发规则、三方库清单（102 库四档分类）、auto-commit daemon 修复。现在需要一个**可执行的 2028 开发计划框架**，将 43 聚类按 P0-P6 优先级和依赖关系编排为可迭代的开发任务，作为后续所有开发工作的总纲。

与已有 spec 的区别：
- `build-36-month-roundmap`：R1-R36 逐月路标（2026-07 至 2029-06），粒度粗，纯规划文档
- `analyze-985-features-algorithm-logic`：985 功能点算法逻辑分析，已完成，纯分析文档
- 本 spec：**可执行的开发计划框架**，基于 43 聚类依赖关系编排迭代任务，每聚类对应算法文档 + 代码实现 + 验收标准，作为后续开发的入口

## What Changes

- 新增 `.trae/specs/execute-2028-development-plan/` 目录（本 spec 三件套）
- 定义 8 个迭代阶段（Sprint 0-7），每个 Sprint 对应一组聚类的开发任务
- 每个聚类任务包含：算法文档引用、代码实现路径、验收标准、依赖关系、网络资源核查
- 建立"聚类→代码模块→测试→验收"的完整可追溯链
- 网络资源核查：已验证 5 项关键技术方向（PoLaRIS EPDA 论文 / LiDAR / Apollo / FDTDX / PPO 路由）

## Impact

- Affected specs: `build-36-month-roundmap`（本 spec 为其执行层）、`analyze-985-features-algorithm-logic`（本 spec 引用其 43 聚类文档）
- Affected code: `src/polaris/sim/`（求解器）、`src/polaris/router/`（布线）、`src/polaris/ml/`（ML/RL）、`src/polaris/layout/`（版图）、`src/polaris/optimize/`（优化）、`src/polaris/quantum/`（量子）、`src/polaris/multiphysics/`（多物理）、`src/polaris/io/`（数据IO）、`src/polaris/platform/`（平台）
- Affected docs: `2026-2028开发计划/功能清单与实现/完整开发计划.md`（执行层补充）、`操作记录.md`

## 数据来源与学术诚信

所有任务编排基于：
1. `2026-2028开发计划/功能清单与实现/00-算法聚类清单.md`（43 聚类 / 940 功能点 / 优先级矩阵）
2. `2026-2028开发计划/功能清单与实现/完整开发计划.md`（三年开发计划 / 8 KPI / 26 创新点）
3. 43 份聚类算法文档（A01-J02，每份含物理模型/控制方程/离散化/边界条件/伪代码/LaTeX公式/文献来源/PoLaRIS实现/商业对照/创新点 11 章节）
4. `.trae/rules/project_rules.md`（规则 1/3/7/10/14/17/18/22/25/26）
5. `.trae/rules/python代码开发规则.md`（高级软件工程师 + 高级算法工程师双角色规范）
6. 网络资源核查（2026-06-25）：
   - arXiv:2507.22301 (2025-07) PoLaRIS EPDA 框架论文 — ASU Jiaqi Gu 团队
   - LiDAR (ISPD 2025, DOI:10.1145/3698364.3705355) curvy 波导 A* 布线 — 同团队
   - Apollo/PlANC (arXiv:2504.18813, 2025-04) GPU 加速 PIC 布局 — 同团队（PoLaRIS 规则 26 禁用 GPU，取 CPU 路径）
   - FDTDX 0.6.2 (2026-06-03, JOSS 08912) JAX FDTD 开源 — Leibniz University Hannover
   - PPO 路由 (OES 2026, DOI:10.29026/oes.2026.260005) 光子脉冲 RL — Xiamen University

**禁止造假**：所有聚类任务须对应算法文档章节，不得凭空编造验收标准。每聚类完成后须通过 7 项 checklist（功能覆盖/正确性/能量守恒/质量门禁/测试覆盖/学术诚信/无 fall-back）。

---

## ADDED Requirements

### Requirement: 8 阶段迭代开发框架（Sprint 0-7）

系统 SHALL 提供一个 8 阶段迭代开发框架，将 43 聚类按 P0-P6 优先级和依赖关系编排为可顺序执行的 Sprint，每个 Sprint 对应一组聚类的开发任务。

#### Sprint 编排

| Sprint | 时间 | 优先级 | 聚类 | 依赖 | 关键路径 |
|--------|------|--------|------|------|---------|
| Sprint 0 | 2026Q1 | P0 底座 | A04-FDE | 无 | 求解器栈底座（Yee 网格共享） |
| Sprint 1 | 2026Q1-Q2 | P0 求解器 | A05-FDFD, A01-RCWA, A02-EME, C03-Redheffer | Sprint 0 | 频域求解器 + S 矩阵级联 |
| Sprint 2 | 2026Q3-Q4 | P0 收尾 + P1 | A03-BPM, A06-2.5D-FDTD, A09-FDTD, A07-HEAT, A08-DDM, B01-B04 | Sprint 0-1 | 时域求解器 + 版图 DRC |
| Sprint 3 | 2027Q1-Q2 | P2 仿真级联 + GUI | B05, C01, C02, C04, C05, F01-Phase1-2 | Sprint 1-2 | 仿真级联底座 + 逆向设计起步 |
| Sprint 4 | 2027Q3-Q4 | P3 ML/RL + 布线 | D01-D05, E01-E04, F01-Phase3-5 | Sprint 3 | AlphaChip 对标 + 布线完善 |
| Sprint 5 | 2028Q1-Q2 | P4 优化 + 量子 | F02, F03, F04, G01, G02, G03 | Sprint 3-4 | 优化器套件 + 量子光子 |
| Sprint 6 | 2028Q3 | P5 多物理 | H01, H02 | Sprint 2, 5 | 电光/热光耦合 |
| Sprint 7 | 2028Q4 | P6 平台生态 | I01-I04, J01, J02 | Sprint 3-6 | 数据 IO + 平台集成 |

#### Scenario: Sprint 顺序执行
- **WHEN** 开发者启动某个 Sprint
- **THEN** 该 Sprint 的所有前置 Sprint 必须已完成（聚类验收通过）
- **AND** 该 Sprint 内的聚类可并行开发（无相互依赖时）

#### Scenario: 聚类验收可追溯
- **WHEN** 某聚类（如 A04-FDE）开发完成
- **THEN** 该聚类对应的算法文档章节（A04 文档 §9 PoLaRIS 实现）已实现
- **AND** 代码模块路径（`src/polaris/sim/fde/`）存在且通过质量门禁
- **AND** 7 项 checklist 全部通过（功能覆盖/正确性/能量守恒/质量门禁/测试覆盖/学术诚信/无 fall-back）

### Requirement: 每聚类任务的标准化结构

系统 SHALL 为 43 聚类中每个聚类定义一个标准化任务结构，包含算法文档引用、代码实现路径、验收标准、依赖关系、网络资源核查。

#### 任务结构

每个聚类任务包含：
1. **聚类 ID 与名称**：如 A04-FDE 本征模求解
2. **算法文档引用**：`2026-2028开发计划/功能清单与实现/A04-FDE本征模求解.md` §9 PoLaRIS 实现
3. **代码实现路径**：如 `src/polaris/sim/fde/`
4. **验收标准**：
   - 功能覆盖：✅+⚠️ 功能点占比 ≥80%（P0）/ ≥70%（P1-P6）
   - 正确性验证：解析基准或跨求解器对比误差达标
   - 能量守恒：TFSF 散射问题 Σ|R|²+Σ|T|²=1 偏差 ≤1e-3
   - 质量门禁：`python scripts/code_quality_gate.py` 0 警告 0 错误
   - 测试覆盖：核心模块 ≥90%，行覆盖 ≥80%
   - 学术诚信：文献溯源 URL ≥5 个，*创新* 点标注底层逻辑+支持理论+案例
   - 无 fall-back：禁止 try/except 回退、禁止假数据、禁止待办/修复标记
5. **依赖关系**：前置聚类 ID
6. **网络资源核查**：该聚类相关的最新论文/开源项目/商业文档

#### Scenario: 任务结构完整
- **WHEN** 开发者查看某个聚类任务（如 A04-FDE）
- **THEN** 任务定义包含算法文档引用、代码路径、7 项验收标准、依赖关系、网络资源
- **AND** 验收标准可量化（误差阈值、覆盖率百分比、URL 数量）

### Requirement: 关键路径与依赖管理

系统 SHALL 明确定义 43 聚类之间的依赖关系，确保关键路径上的聚类优先开发，非关键路径聚类可并行。

#### 关键路径

```
A04-FDE ──┬──→ A05-FDFD（共享 Yee 网格 + SC-PML）
          ├──→ A06-2.5D-FDTD（共享 FDE slab 模）
          ├──→ A09-FDTD（共享 Yee + 模式归一化）
          └──→ F01-伴随（FOM 模式匹配）

A01-RCWA ──┐
A02-EME  ──┴──→ C03-Redheffer（S 矩阵级联共享内核）

A07-HEAT ──┬──→ H02-热光效应（温度场→折射率）
A08-DDM  ──┴──→ H01-电光耦合（载流子→折射率→FDE）

A09-FDTD ──→ F01-伴随（时域 leapfrog 复用为伴随内核）
A05-FDFD ──→ F01-伴随（频域 SC-PML 算子构造 A）

B02-DRC ───→ F01-伴随（DRC 感知约束梯度惩罚）

D01-GNN ──┬──→ D05-AlphaChip（Edge-GNN 编码器）
D03-PPO ──┤
D04-奖励 ──┴──→ D05-AlphaChip（PPO 策略 + 课程学习）

C01-S 参数 ──→ F02-自动微分（JAX 可微 S 参数）
F02-自动微分 ──→ F01-伴随（JAX AD + 伴随法共生）

E01-A* ──┬──→ E02-通道布线（rip-up-reroute 基础）
         ├──→ E03-多层布线（层间通孔）
         └──→ E04-光电协同（光电联合代价）

I01-网表 ──→ J01-脚本 API（CircuitSpec 入口）
I02-可视化 ──→ J01-脚本 API（GUI 反馈）
I03-GDS导出 ──→ J02-商业生态（流片闭环）
```

**关键路径**：A04 → A09 → F01（求解器底座 → 逆向设计）；A01+A02 → C03（求解器 → 级联）；D01+D03+D04 → D05（ML 三件套 → AlphaChip 对标）。

#### Scenario: 依赖关系可追溯
- **WHEN** 开发者启动某聚类（如 A05-FDFD）
- **THEN** 该聚类的前置聚类（A04-FDE）已完成且验收通过
- **AND** 共享组件（Yee 网格）已提取为公共模块

### Requirement: 网络资源核查与更新

系统 SHALL 在每个 Sprint 启动前进行网络资源核查，更新该 Sprint 涉及聚类的最新论文、开源项目、商业文档。

#### 已核查资源（2026-06-25）

| 聚类 | 资源 | 来源 | URL |
|------|------|------|-----|
| A09-FDTD | PoLaRIS EPDA 框架论文 | arXiv:2507.22301 (2025-07) | https://arxiv.org/html/2507.22301v1/ |
| A09-FDTD | FDTDX 0.6.2 JAX FDTD | JOSS 08912 (2026-06) | https://pypi.org/project/fdtdx/ |
| E01-A* | LiDAR curvy 波导布线 | ISPD 2025 | https://dl.acm.org/doi/10.1145/3698364.3705355 |
| D05-AlphaChip | Apollo GPU 加速 PIC 布局 | arXiv:2504.18813 (2025-04) | https://arxiv.org/html/2504.18813v1 |
| D03-PPO | 光子脉冲 PPO 路由 | OES 2026 | https://www.oejournal.org/oes/en/article/pdf/preview/10.29026/oes.2026.260005.pdf |

#### Scenario: Sprint 启动前网络核查
- **WHEN** 启动 Sprint N
- **THEN** 对该 Sprint 涉及的聚类进行 WebSearch 核查最新资源
- **AND** 更新聚类算法文档的文献来源章节（如有新资源）
- **AND** 记录核查结果到 `操作记录.md`

### Requirement: 验收标准与质量门禁

系统 SHALL 为每个聚类定义量化验收标准，并通过质量门禁脚本自动检查。

#### 7 项通用验收标准（每聚类必过）

1. **功能覆盖**：✅+⚠️ 功能点占比 ≥80%（P0）/ ≥70%（P1-P6）
2. **正确性验证**：解析基准或跨求解器对比误差达标（如 FDTD vs Lumerical ≤0.5 dB）
3. **能量守恒**：TFSF 散射问题 Σ|R|²+Σ|T|²=1 偏差 ≤1e-3（规则 14，失败 raise）
4. **质量门禁**：`python scripts/code_quality_gate.py` 0 警告 0 错误（规则 17）
5. **测试覆盖**：核心模块 ≥90%，行覆盖 ≥80%（规则 10.1）
6. **学术诚信**：文献溯源 URL ≥5 个，*创新* 点标注底层逻辑+支持理论+案例（规则 18）
7. **无 fall-back**：禁止 try/except 回退、禁止假数据、禁止待办/修复标记（规则 14）

#### 聚类专项验收（示例）

- A04-FDE：SOI strip 波导 neff vs Lumerical 误差 ≤1e-4
- A09-FDTD：高斯脉冲误差 <1e-3，CPML 反射 ≤-60 dB，金 Drude 反射率 vs Palik <2%
- D05-AlphaChip：TILOS Ariane 基准 HPWL 对齐 Circuit Training 公开结果
- F01-伴随：SOI Y 分支梯度 vs 有限差分 CS 检验 ≤1e-3，GDSII 100% DRC 通过

#### Scenario: 聚类验收通过
- **WHEN** 某聚类完成开发
- **THEN** 运行 `python scripts/code_quality_gate.py` 通过
- **AND** 运行 `pytest tests/test_<cluster>.py --cov` 覆盖率达标
- **AND** 7 项通用验收标准 + 聚类专项验收全部通过
- **AND** 更新 `tasks.md` 中该聚类任务为 [x] 完成

#### Scenario: 聚类验收失败
- **WHEN** 某聚类验收标准未通过
- **THEN** 禁止标记为完成，必须修复后重新验收
- **AND** 记录失败原因到 `操作记录.md`
- **AND** 不得使用 fall-back 绕过（规则 14）

---

## MODIFIED Requirements

无（本 spec 为新增，不修改已有 spec）

## REMOVED Requirements

无（本 spec 不移除已有需求）
