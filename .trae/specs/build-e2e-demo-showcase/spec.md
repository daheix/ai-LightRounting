# 端到端全流程 Demo Showcase Spec

## Why

PoLaRIS 已完成 36 个月路标（R01-R36），综合得分 9.27，但缺乏一个面向客户的端到端演示用例，将所有能力（布局/布线/仿真/DRC/LVS/GDS/AI/光电协同/量子光子）串联成一条完整可观看的工作流。客户需要看到"从需求输入到 GDS + 量子验证"的全链路实跑过程，第一步用结构化日志展示每一步的输入输出与中间产物，后续扩展为 Web 页面可视化。

## What Changes

- 新增 `examples/e2e_showcase/` 目录，承载端到端演示脚本与产物
- 新增 `examples/e2e_showcase/run_showcase.py`：主入口，按 9 个阶段顺序执行全流程，每阶段产出结构化日志（JSONL + 控制台彩色日志）
- 新增 `examples/e2e_showcase/stages/`：9 个阶段模块，每个阶段独立可运行、可验证
  - stage1_pdk_catalog.py：PDK 器件目录展示（R04/R08/R20 四平台）
  - stage2_circuit_spec.py：电路规格定义（MZI + Clements + 量子玻色采样电路）
  - stage3_ai_placement.py：AI 布局（R33 Edge-GNN + R34 预训练 checkpoint 加载）
  - stage4_routing.py：智能布线（R17 弹性连接器 + R19 曲线波导）
  - stage5_simulation.py：仿真验证（R31 FDTD + R32 INTERCONNECT 频域/时域）
  - stage6_drc_lvs.py：DRC/LVS 验证（R07 层次化 DRC + R08 图同构 LVS）
  - stage7_gds_export.py：GDS 导出（R06 GDSII + R22 OASIS）
  - stage8_opto_electrical.py：光电协同（R35 Verilog-A + SPICE + PAM4 眼图）
  - stage9_quantum_photonics.py：量子光子验证（R35 玻色采样 + HOM 干涉 + KLM）
- 新增 `examples/e2e_showcase/logging_config.py`：统一日志配置（控制台彩色 + JSONL 文件 + 阶段计时）
- 新增 `examples/e2e_showcase/report_generator.py`：汇总各阶段产物生成 Markdown 报告
- 新增 `examples/e2e_showcase/README.md`：演示说明与运行方式
- 扩展 `src/polaris/web/server.py`：新增 `/api/showcase/run` 端点触发全流程，`/api/showcase/report` 获取报告，`/api/showcase/stages/{id}` 获取单阶段结果
- 扩展 `src/polaris/web/static/`：新增 showcase 页面，分阶段卡片展示进度、日志流、产物预览
- 新增 `tests/test_e2e_showcase.py`：验证 9 个阶段独立运行与端到端串联

## Impact

- Affected specs: `build-36-month-roundmap`、`build-polaris-optical-pnr`（演示用例复用其能力）
- Affected code:
  - `src/polaris/pipeline/integrated.py`（复用 IntegratedPipeline）
  - `src/polaris/web/server.py`（新增 showcase API 端点）
  - `src/polaris/web/static/`（新增 showcase 前端页面）
  - `examples/e2e_showcase/`（新增演示目录）
  - `tests/test_e2e_showcase.py`（新增测试）

## ADDED Requirements

### Requirement: 端到端 Demo 主入口

系统 SHALL 提供 `examples/e2e_showcase/run_showcase.py` 主入口，按 9 个阶段顺序执行全流程，每阶段输出结构化日志。

#### Scenario: 客户运行全流程演示
- **WHEN** 用户执行 `python examples/e2e_showcase/run_showcase.py`
- **THEN** 系统依次执行 9 个阶段，每阶段在控制台打印彩色阶段头、输入摘要、关键中间产物、输出摘要、耗时
- **AND** 每阶段将结构化日志写入 `out/e2e_showcase/logs/showcase.jsonl`
- **AND** 全流程结束后生成 `out/e2e_showcase/report.md` 汇总报告

#### Scenario: 单阶段独立运行
- **WHEN** 用户执行 `python examples/e2e_showcase/run_showcase.py --stage 5`
- **THEN** 系统仅执行阶段 5（仿真验证），输出该阶段日志与产物

### Requirement: 阶段 1 PDK 器件目录展示

系统 SHALL 在阶段 1 展示四平台（SOI/SiN/InP/LNOI）PDK 器件目录，列出每平台器件数、典型器件参数、来源 foundry。

#### Scenario: 展示四平台 PDK
- **WHEN** 阶段 1 执行
- **THEN** 输出 SOI/SiN/InP/LNOI 四平台器件计数
- **AND** 列出每平台 3+ 代表器件及其关键参数（如 SOI 波导 neff=2.4）
- **AND** 标注器件来源（SiEPIC EBeam PDK / Ligentec / HyperLight / Pattern Project）

### Requirement: 阶段 2 电路规格定义

系统 SHALL 在阶段 2 定义 3 个演示电路规格：MZI 干涉仪、Clements 4x4 光矩阵、量子玻色采样电路。

#### Scenario: 定义 3 个演示电路
- **WHEN** 阶段 2 执行
- **THEN** 生成 3 个 CircuitSpec 实例
- **AND** MZI 含 5 器件（2 MMI + 2 波导臂 + 1 移相器）
- **AND** Clements 4x4 含 6 分束器 + 4 相移器
- **AND** 量子电路含 4 模玻色采样网络

### Requirement: 阶段 3 AI 布局

系统 SHALL 在阶段 3 使用 Edge-GNN + PPO 对 3 个电路执行 AI 布局，加载 R34 预训练 checkpoint（若存在），输出布局坐标与 HPWL。

#### Scenario: AI 布局生成
- **WHEN** 阶段 3 执行
- **THEN** 对每个电路生成布局坐标
- **AND** 计算 HPWL（半周长线长）指标
- **AND** 输出布局可视化 ASCII 预览
- **AND** 若 checkpoint 不存在则降级为解析布局并明确告警

### Requirement: 阶段 4 智能布线

系统 SHALL 在阶段 4 对布局结果执行智能布线，使用弹性连接器 + 曲线波导，输出波导路径与总损耗。

#### Scenario: 布线生成
- **WHEN** 阶段 4 执行
- **THEN** 对每个电路生成波导路径
- **AND** 计算总插入损耗（dB）
- **AND** 计算交叉数与弯曲数
- **AND** 输出路径几何 ASCII 预览

### Requirement: 阶段 5 仿真验证

系统 SHALL 在阶段 5 对布线结果执行频域 S 参数仿真 + 时域眼图仿真，输出 S 参数曲线与眼图指标。

#### Scenario: 频域仿真
- **WHEN** 阶段 5 执行
- **THEN** 对 MZI 电路计算 1500-1600nm 波长扫描的传输谱
- **AND** 输出谐振波长与消光比
- **AND** 对 Clements 计算酉矩阵传输

#### Scenario: 时域眼图
- **WHEN** 阶段 5 执行
- **THEN** 对 MZI 调制器生成 PAM4 眼图
- **AND** 计算眼图开口、BER、SNR

### Requirement: 阶段 6 DRC/LVS 验证

系统 SHALL 在阶段 6 对布局布线结果执行层次化 DRC + 图同构 LVS，输出违规清单与一致性报告。

#### Scenario: DRC 检查
- **WHEN** 阶段 6 执行
- **THEN** 执行 16 项 DRC 规则检查
- **AND** 输出违规清单（含坐标、规则名、严重度）
- **AND** 输出 DRC 通过率

#### Scenario: LVS 比对
- **WHEN** 阶段 6 执行
- **THEN** 提取网表并与原理图比对
- **AND** 输出一致性布尔结果与差异清单

### Requirement: 阶段 7 GDS 导出

系统 SHALL 在阶段 7 将布局布线结果导出为 GDSII 文件，并验证文件完整性。

#### Scenario: GDS 导出
- **WHEN** 阶段 7 执行
- **THEN** 生成 `out/e2e_showcase/gds/mzi.gds` 等文件
- **AND** 输出文件大小、结构数、层次数
- **AND** 验证 GDS 文件可被重新加载

### Requirement: 阶段 8 光电协同

系统 SHALL 在阶段 8 生成 Verilog-A 紧凑模型 + SPICE 网表 + PAM4 眼图，演示光电协同仿真能力。

#### Scenario: Verilog-A 生成
- **WHEN** 阶段 8 执行
- **THEN** 为 5+ 器件生成 Verilog-A 模型文件
- **AND** 生成 Ngspice 联合仿真网表
- **AND** 生成 PAM4 眼图与 BER

### Requirement: 阶段 9 量子光子验证

系统 SHALL 在阶段 9 执行玻色采样 + HOM 干涉 + KLM 量子门仿真，输出量子光子验证结果。

#### Scenario: 玻色采样
- **WHEN** 阶段 9 执行
- **THEN** 执行 4 光子 4 模玻色采样
- **AND** 输出概率分布与守恒验证
- **AND** 验证 HOM 干涉 |1,1⟩ 概率 = 0

#### Scenario: KLM 量子门
- **WHEN** 阶段 9 执行
- **THEN** 验证 KLM CNOT 成功率 = 0.25
- **AND** 验证 Hadamard 门酉性

### Requirement: 结构化日志

系统 SHALL 为每阶段输出结构化日志，含阶段 ID、阶段名、开始时间、结束时间、耗时、输入摘要、输出摘要、状态、错误信息（若有）。

#### Scenario: 日志格式
- **WHEN** 任意阶段执行
- **THEN** 控制台输出彩色阶段头（绿色表示开始、黄色表示进行中、红色表示失败、蓝色表示完成）
- **AND** JSONL 文件追加一行 JSON 日志
- **AND** 日志含 `stage_id`、`stage_name`、`status`、`duration_s`、`inputs`、`outputs` 字段

### Requirement: 汇总报告生成

系统 SHALL 在全流程结束后生成 Markdown 汇总报告，含 9 阶段执行状态表、关键指标、产物文件清单、ASCII 可视化。

#### Scenario: 报告生成
- **WHEN** 全流程结束
- **THEN** 生成 `out/e2e_showcase/report.md`
- **AND** 报告含 9 阶段状态表（阶段名/状态/耗时/关键指标）
- **AND** 报告含产物文件清单（GDS/Verilog-A/SPICE/日志）
- **AND** 报告含 ASCII 布局预览与 S 参数曲线

### Requirement: Web 页面展示

系统 SHALL 在 `src/polaris/web/server.py` 新增 showcase API 端点，并在 `static/` 新增 showcase 页面，分阶段卡片展示进度、日志流、产物预览。

#### Scenario: Web 触发全流程
- **WHEN** 客户访问 `/api/showcase/run` 并 POST 触发
- **THEN** 后台启动全流程
- **AND** 返回 `run_id` 供前端轮询进度

#### Scenario: Web 查看进度
- **WHEN** 客户访问 showcase 页面
- **THEN** 页面展示 9 个阶段卡片
- **AND** 每卡片显示状态（pending/running/done/failed）、耗时、关键指标
- **AND** 支持点击查看该阶段详细日志

## MODIFIED Requirements

### Requirement: Web Server 端点扩展

`src/polaris/web/server.py` 原有 `/api/presets`、`/api/run`、`/api/health` 端点保留，新增 3 个 showcase 端点：
- `POST /api/showcase/run`：触发全流程，返回 `run_id`
- `GET /api/showcase/report/{run_id}`：获取汇总报告
- `GET /api/showcase/stages/{run_id}/{stage_id}`：获取单阶段结果

## REMOVED Requirements

无移除项。
