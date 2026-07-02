# 真实 PIC 设计 Case 端到端 Demo Spec

## Why
前期已完成 R03 真实化修复（清除 mock 假数据/物理错误/占位哨兵），10 阶段端到端 Demo
可跑通（10 成功 0 失败）。但当前 demo 输入仍是"展示用合成电路"（MZI/Clements/量子占位），
且 stage3 AI 布局无预训练 checkpoint、stage7 GDS 器件为矩形占位、stage10 converged=False。
用户要求"做一个真实的 case，所有输入用真的，继续分析结果的真实完整展示"——即选取一个
真实光子集成电路设计案例，用真实输入跑完整 10 阶段，对每阶段输出做真实性分析与完整展示，
诚实标注哪些是真实可用、哪些是受 demo 环境限制（非占位，而是物理/算力边界）。

## What Changes
- 新增 `examples/e2e_showcase/real_case/` 目录，承载真实 case 端到端运行脚本
- 新增 `examples/e2e_showcase/real_case/run_real_case.py`：选取真实 PIC 设计案例
  （100Gbps MZI 调制器 + Clements 4x4 光矩阵，对标 Intel 100G CWDM4 光模块），
  以真实器件参数（SiEPIC EBeam PDK 实测值）为输入跑完整 10 阶段
- 新增 `examples/e2e_showcase/real_case/real_inputs.py`：集中管理真实输入参数
  （所有参数标注来源：SiEPIC PDK / Intel CWDM4 spec / literature），禁止任何 mock
- 新增 `examples/e2e_showcase/real_case/analyze_results.py`：对 10 阶段输出做真实性分析，
  逐阶段标注"真实可用/受算力限制/受 demo 网格限制"，生成真实完整结果展示报告
- 新增 `examples/e2e_showcase/real_case/REAL_CASE_REPORT.md`：真实 case 完整结果展示报告，
  含每阶段输入→输出→真实性判定→与商业产品对标
- 修改 `examples/e2e_showcase/run_showcase.py`：新增 `--real-case` 选项触发真实 case 流程
- 不修改现有 10 阶段 stage 代码（已修复，禁止回归）

## Impact
- Affected specs: build-e2e-demo-showcase（已完成，本 spec 为其真实 case 扩展）
- Affected code:
  - `examples/e2e_showcase/run_showcase.py`（新增 --real-case 选项）
  - `examples/e2e_showcase/real_case/`（新增目录）
- 不影响 `src/polaris/` 核心库（复用已修复的 stage 代码）

## ADDED Requirements

### Requirement: 真实 PIC 设计案例选取
系统 SHALL 选取一个真实光子集成电路设计案例作为 demo 输入，案例须满足：
(1) 有公开商业产品对标（如 Intel 100G CWDM4 / Cisco Acacia / Lumentum）；
(2) 器件参数有公开 PDK 或文献来源（如 SiEPIC EBeam PDK、Ligentec AN800 PDK）；
(3) 覆盖 10 阶段中至少 7 个阶段的真实输入。

#### Scenario: 真实案例选取
- **WHEN** 运行真实 case demo
- **THEN** 选取 100Gbps MZI 调制器（对标 Intel 100G CWDM4）+ Clements 4x4 光矩阵
  （对标通用光计算单元），所有器件参数来自 SiEPIC EBeam PDK 实测值

### Requirement: 真实输入参数管理
系统 SHALL 集中管理所有真实输入参数，每个参数须标注来源（PDK 名/文献作者年份/URL），
禁止任何 mock/placeholder/合成参数。

#### Scenario: 参数溯源
- **WHEN** 查看任一输入参数
- **THEN** 能追溯到来源（如 `neff=2.4` ← SiEPIC EBeam PDK 220nm SOI strip waveguide 实测）

### Requirement: 10 阶段真实输出完整展示
系统 SHALL 对 10 阶段每阶段输出做完整展示，含：输入参数、输出数值、真实性判定、
与商业产品对标差距、受限制原因（若有）。

#### Scenario: 阶段输出展示
- **WHEN** 真实 case demo 运行完成
- **THEN** 生成 REAL_CASE_REPORT.md，每阶段含：输入→输出→真实性→对标差距

### Requirement: 真实性诚实标注
系统 SHALL 对每阶段输出诚实标注三类状态：
(1) `REAL_USABLE`：真实可用，数值物理合理，可对标商业产品；
(2) `LIMITED_BY_COMPUTE`：受 demo 算力/网格限制，方向正确但精度不足（非占位）；
(3) `LIMITED_BY_DATA`：受训练数据/PDK 限制，需更多信息才能达到商用级。

#### Scenario: 真实性判定
- **WHEN** stage3 AI 布局无预训练 checkpoint
- **THEN** 标注 `LIMITED_BY_DATA`，说明 HPWL 为未训练网络前向推理结果，不能对标 AlphaChip

## MODIFIED Requirements

### Requirement: 端到端 Demo 主入口
[原 build-e2e-demo-showcase 的 run_showcase.py 仅支持合成电路 demo]
现新增 `--real-case` 选项，触发真实 case 流程，复用已修复的 10 阶段 stage 代码。

## REMOVED Requirements
（无移除，本 spec 为纯新增扩展）
