# 商业级作业流程表达系统 Spec

## Why

PoLaRIS 当前的流水线（`IntegratedPipeline.run()`）是单一同步函数调用，缺乏商业 EDA 软件的标准作业流程表达能力。商业光子 EDA（Luceda IPKISS、Cadence Virtuoso ADE-XL、Synopsys ICC2、Ansys Lumerical）均采用"作业（Job）+ 阶段（Stage）+ 状态机（State Machine）+ 调度器（Scheduler）"的异步作业模型，支持：

1. **作业提交与异步执行**：用户提交作业后立即返回 job_id，后台异步执行
2. **阶段化流水线**：作业分解为有序阶段（PDK 选择 → 电路规格 → 布局 → 布线 → 仿真 → DRC/LVS → GDS 导出），每阶段可独立检查
3. **状态机追踪**：作业有明确生命周期（queued → running → completed/failed/cancelled）
4. **结果可追溯**：每阶段产出持久化到磁盘，可回溯查询
5. **并行调度**：多个作业可并行执行，资源调度器分配计算节点

当前 PoLaRIS 的 `IntegratedPipeline.run()` 是阻塞同步调用，无法表达商业软件的作业流程。本 spec 旨在设计一套与 Luceda IPKISS / Cadence ADE-XL 对齐的作业流程表达系统。

## What Changes

- **新增** `polaris.flow.job` 模块：作业（Job）+ 阶段（Stage）+ 状态机（JobState）+ 调度器（JobScheduler）的完整异步作业模型
- **新增** `polaris.flow.recipe` 模块：作业配方（Recipe），将流水线配置抽象为可序列化的 YAML/JSON 配方
- **新增** `polaris.flow.workspace` 模块：作业工作空间（Workspace），管理作业的输入/输出/日志/报告目录结构
- **新增** `polaris.flow.tracker` 模块：作业追踪器（JobTracker），提供作业状态查询、历史记录、阶段结果检索 API
- **新增** `polaris.flow.stages` 模块：标准化阶段定义（10 个阶段，对齐 Luceda IPKISS 四步流程 + Cadence ADE-XL 阶段化）
- **修改** `polaris.pipeline.integrated`：`IntegratedPipeline` 改为可被 Job 调用的 Stage 执行器，保留同步 `run()` 向后兼容
- **修改** `polaris.web.server`：新增作业管理 REST API（提交/查询/取消/列表/阶段结果）
- **新增** `tests/test_flow_job.py`：作业流程表达系统的完整测试套件

### 商业软件对齐参考

| 商业软件 | 作业流程表达方式 | PoLaRIS 对齐实现 |
|---------|----------------|----------------|
| Luceda IPKISS | 四步流程（器件设计 → 线路设计 → 设计验证 → 流片准备），每步有明确输入输出 | 10 阶段标准化定义，每阶段有 StageInput/StageOutput dataclass |
| Cadence ADE-XL | `asimenv.xl -queue local -maxworkers 8 -project myDesign`，作业队列 + 资源调度 | JobScheduler + 并行 worker 池 + 作业队列 |
| Synopsys ICC2 | 阶段化 PnR（floorplan → placement → CTS → routing → optimization），每阶段可独立检查 | Stage 状态机 + 阶段间依赖 + 阶段结果持久化 |
| Ansys Lumerical | 作业提交到计算节点，异步轮询状态，结果归档 | Job 状态机（queued/running/completed/failed）+ 结果归档 |

## Impact

- **Affected specs**: 无（新增独立模块）
- **Affected code**:
  - 新增 `src/polaris/flow/__init__.py`（导出 Job/Stage/JobScheduler/Recipe/Workspace/JobTracker）
  - 新增 `src/polaris/flow/job.py`（Job + JobState + JobStatus 状态机）
  - 新增 `src/polaris/flow/stage.py`（Stage + StageInput + StageOutput + 10 阶段定义）
  - 新增 `src/polaris/flow/scheduler.py`（JobScheduler + worker 池 + 作业队列）
  - 新增 `src/polaris/flow/recipe.py`（Recipe + 序列化/反序列化）
  - 新增 `src/polaris/flow/workspace.py`（Workspace + 目录结构管理）
  - 新增 `src/polaris/flow/tracker.py`（JobTracker + 状态查询 + 历史记录）
  - 修改 `src/polaris/pipeline/integrated.py`（IntegratedPipeline 适配 Stage 执行器接口）
  - 修改 `src/polaris/web/server.py`（新增作业管理 REST API）
  - 新增 `tests/test_flow_job.py`

## ADDED Requirements

### Requirement: 作业（Job）模型

系统 SHALL 提供一个 `Job` dataclass，表示一个完整的 EPDA 作业，包含：
- 唯一 job_id（UUID 或时间戳格式）
- 作业配方（Recipe）引用
- 当前状态（JobStatus 枚举：QUEUED / RUNNING / COMPLETED / FAILED / CANCELLED）
- 阶段结果列表（每个 Stage 的执行结果）
- 提交时间、开始时间、结束时间
- 工作空间（Workspace）引用
- 错误信息（失败时）

#### Scenario: 创建作业
- **WHEN** 用户调用 `Job(recipe=recipe, workspace=workspace)` 创建作业
- **THEN** 系统生成唯一 job_id，状态为 QUEUED，提交时间为当前时间

#### Scenario: 作业状态转换
- **WHEN** 调度器开始执行作业
- **THEN** 状态从 QUEUED → RUNNING，记录开始时间
- **WHEN** 所有阶段成功完成
- **THEN** 状态从 RUNNING → COMPLETED，记录结束时间
- **WHEN** 某阶段失败
- **THEN** 状态从 RUNNING → FAILED，记录错误信息和结束时间
- **WHEN** 用户取消作业
- **THEN** 状态 → CANCELLED，记录结束时间

### Requirement: 阶段（Stage）模型

系统 SHALL 提供 10 个标准化阶段，对齐 Luceda IPKISS 四步流程 + 商业 EDA 阶段化设计：

| 阶段 ID | 阶段名称 | 对应 Luceda IPKISS 步骤 | 输入 | 输出 |
|--------|---------|----------------------|------|------|
| 1 | PDK 器件目录 | 器件设计 | platform | device_catalog.json |
| 2 | 电路规格定义 | 线路设计 | circuit_spec | circuit.json |
| 3 | AI 布局 | 线路设计 | circuit | placements.json |
| 4 | 智能布线 | 线路设计 | circuit + placements | routes.json |
| 5 | S 参数仿真 | 设计验证 | circuit + placements + routes | sparams.json |
| 6 | DRC/LVS 验证 | 设计验证 | placements + routes | drc_report.json |
| 7 | GDS 导出 | 流片准备 | placements + routes | layout.gds |
| 8 | 光电协同 | 设计验证 | circuit + placements | opto_electrical.json |
| 9 | 量子光子验证 | 设计验证 | circuit | quantum_report.json |
| 10 | 逆向设计 | 器件设计 | target_spec | inverse_design.json |

#### Scenario: 阶段执行
- **WHEN** 调度器执行阶段 N
- **THEN** 系统加载阶段 N 的输入（来自上一阶段输出或用户指定），执行阶段逻辑，持久化输出到工作空间，记录阶段状态

#### Scenario: 阶段依赖
- **WHEN** 阶段 N 依赖阶段 M（M < N）
- **THEN** 阶段 M 必须先完成（COMPLETED），否则阶段 N 标记为 BLOCKED

### Requirement: 作业调度器（JobScheduler）

系统 SHALL 提供一个 `JobScheduler`，支持：
- 作业队列（FIFO）
- 并行 worker 池（可配置 max_workers，默认 4）
- 作业状态转换
- 作业取消
- 资源限制（最大并发作业数）

#### Scenario: 提交作业
- **WHEN** 用户调用 `scheduler.submit(job)` 提交作业
- **THEN** 作业加入队列，状态为 QUEUED，返回 job_id

#### Scenario: 异步执行
- **WHEN** 有空闲 worker 且队列非空
- **THEN** 调度器从队列取出作业，分配给 worker，状态变为 RUNNING

#### Scenario: 并行执行
- **WHEN** 队列中有多个作业且有空闲 worker
- **THEN** 多个作业并行执行（最多 max_workers 个）

#### Scenario: 作业取消
- **WHEN** 用户调用 `scheduler.cancel(job_id)`
- **THEN** 作业状态变为 CANCELLED，worker 停止执行该作业

### Requirement: 作业配方（Recipe）

系统 SHALL 提供一个 `Recipe` dataclass，将流水线配置抽象为可序列化的配方：
- 电路规格（preset_id 或自定义 CircuitSpec）
- 平台（SOI/SiN/InP/LNOI）
- 布局算法（rl/analytical/ppo_gnn）
- 布线算法（curvy/diagonal/hybrid）
- 仿真配置（max_iterations, loss_target_db）
- 输出目录
- 启用的阶段列表（支持跳过某些阶段）

#### Scenario: 配方序列化
- **WHEN** 调用 `recipe.to_yaml()` 或 `recipe.to_json()`
- **THEN** 返回可持久化的字符串表示

#### Scenario: 配方反序列化
- **WHEN** 调用 `Recipe.from_yaml(yaml_str)` 或 `Recipe.from_json(json_str)`
- **THEN** 返回重建的 Recipe 对象

### Requirement: 工作空间（Workspace）

系统 SHALL 提供一个 `Workspace`，管理作业的目录结构：
```
<output_dir>/<job_id>/
├── inputs/          # 作业输入
├── logs/            # 作业日志（JSONL 格式）
├── stages/          # 各阶段输出
│   ├── stage1_pdk/
│   ├── stage2_circuit/
│   ├── ...
│   └── stage10_inverse/
├── reports/         # 汇总报告
├── gds/             # GDS 文件
└── job.json         # 作业元数据（状态、时间、配方）
```

#### Scenario: 工作空间初始化
- **WHEN** 创建 Workspace(output_dir, job_id)
- **THEN** 系统创建上述目录结构

#### Scenario: 阶段输出持久化
- **WHEN** 阶段 N 完成
- **THEN** 阶段输出写入 `stages/stageN_<name>/output.json`

### Requirement: 作业追踪器（JobTracker）

系统 SHALL 提供一个 `JobTracker`，支持：
- 查询作业状态（`get_status(job_id) -> JobStatus`）
- 查询作业详情（`get_job(job_id) -> Job`）
- 列出所有作业（`list_jobs(status=None) -> list[Job]`）
- 查询阶段结果（`get_stage_result(job_id, stage_id) -> StageOutput`）
- 查询作业历史（`get_history(job_id) -> list[StageResult]`）

#### Scenario: 状态查询
- **WHEN** 调用 `tracker.get_status(job_id)`
- **THEN** 返回当前作业状态（QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED）

#### Scenario: 阶段结果查询
- **WHEN** 调用 `tracker.get_stage_result(job_id, 3)`
- **THEN** 返回阶段 3（AI 布局）的输出结果（placements.json 内容）

### Requirement: Web API 作业管理端点

系统 SHALL 在 `polaris.web.server` 新增以下 REST API 端点：
- `POST /api/jobs` — 提交作业（接收 Recipe JSON，返回 job_id）
- `GET /api/jobs` — 列出所有作业（可选 status 过滤）
- `GET /api/jobs/{job_id}` — 查询作业详情
- `GET /api/jobs/{job_id}/status` — 查询作业状态
- `POST /api/jobs/{job_id}/cancel` — 取消作业
- `GET /api/jobs/{job_id}/stages/{stage_id}` — 查询阶段结果
- `GET /api/jobs/{job_id}/report` — 查询作业汇总报告

#### Scenario: 提交作业
- **WHEN** 客户端 POST /api/jobs，body 为 Recipe JSON
- **THEN** 服务器创建作业，返回 `{"job_id": "...", "status": "queued"}`

#### Scenario: 轮询状态
- **WHEN** 客户端 GET /api/jobs/{job_id}/status
- **THEN** 返回 `{"job_id": "...", "status": "running", "progress": "5/10"}`

## MODIFIED Requirements

### Requirement: IntegratedPipeline 适配

`IntegratedPipeline` SHALL 保留同步 `run()` 方法向后兼容，同时新增 `run_as_stages(recipe, workspace) -> list[StageResult]` 方法，支持被 JobScheduler 调用。

#### Scenario: 同步运行（向后兼容）
- **WHEN** 调用 `pipeline.run(circuit)`
- **THEN** 同步执行完整流水线，返回 PipelineResult（与现有行为一致）

#### Scenario: 阶段化运行
- **WHEN** 调用 `pipeline.run_as_stages(recipe, workspace)`
- **THEN** 按 Recipe 中启用的阶段列表顺序执行，每阶段输出持久化到 Workspace，返回阶段结果列表
