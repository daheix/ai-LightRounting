# Tasks

- [x] Task 1: 创建 flow 模块骨架与核心数据结构
  - [x] SubTask 1.1: 创建 `src/polaris/flow/__init__.py`，导出所有公开 API
  - [x] SubTask 1.2: 创建 `src/polaris/flow/job.py`，实现 Job dataclass + JobStatus 枚举 + JobState 状态机
  - [x] SubTask 1.3: 创建 `src/polaris/flow/stage.py`，实现 Stage + StageInput + StageOutput + 10 阶段定义
  - [x] SubTask 1.4: 创建 `src/polaris/flow/recipe.py`，实现 Recipe dataclass + YAML/JSON 序列化
  - [x] SubTask 1.5: 创建 `src/polaris/flow/workspace.py`，实现 Workspace 目录结构管理
  - [x] SubTask 1.6: 创建 `src/polaris/flow/tracker.py`，实现 JobTracker 查询 API

- [x] Task 2: 实现作业调度器（JobScheduler）
  - [x] SubTask 2.1: 创建 `src/polaris/flow/scheduler.py`，实现 JobScheduler + FIFO 队列 + worker 池
  - [x] SubTask 2.2: 实现作业状态转换（QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED）
  - [x] SubTask 2.3: 实现并行执行（ThreadPoolExecutor，max_workers 可配置）
  - [x] SubTask 2.4: 实现作业取消机制

- [x] Task 3: 实现 10 个标准化阶段的执行逻辑
  - [x] SubTask 3.1: 实现 stage1_pdk（PDK 器件目录展示）
  - [x] SubTask 3.2: 实现 stage2_circuit（电路规格定义）
  - [x] SubTask 3.3: 实现 stage3_placement（AI 布局，复用 _DefaultPlacer）
  - [x] SubTask 3.4: 实现 stage4_routing（智能布线，复用 _CurvyRouter/_DefaultRouter）
  - [x] SubTask 3.5: 实现 stage5_simulation（S 参数仿真，复用 _DefaultSimulator）
  - [x] SubTask 3.6: 实现 stage6_drc_lvs（DRC/LVS 验证，复用 ConstraintChecker）
  - [x] SubTask 3.7: 实现 stage7_gds（GDS 导出，复用现有 GDS 导出逻辑）
  - [x] SubTask 3.8: 实现 stage8_opto_electrical（光电协同）
  - [x] SubTask 3.9: 实现 stage9_quantum（量子光子验证）
  - [x] SubTask 3.10: 实现 stage10_inverse（逆向设计）

- [x] Task 4: 适配 IntegratedPipeline 支持阶段化执行
  - [x] SubTask 4.1: 在 `IntegratedPipeline` 新增 `run_as_stages(recipe, workspace) -> list[StageResult]` 方法
  - [x] SubTask 4.2: 保留同步 `run()` 方法向后兼容
  - [x] SubTask 4.3: 确保阶段间数据传递正确（上一阶段输出 → 下一阶段输入）

- [x] Task 5: 新增 Web API 作业管理端点
  - [x] SubTask 5.1: 实现 `POST /api/jobs`（提交作业）
  - [x] SubTask 5.2: 实现 `GET /api/jobs`（列出所有作业）
  - [x] SubTask 5.3: 实现 `GET /api/jobs/{job_id}`（查询作业详情）
  - [x] SubTask 5.4: 实现 `GET /api/jobs/{job_id}/status`（查询作业状态）
  - [x] SubTask 5.5: 实现 `POST /api/jobs/{job_id}/cancel`（取消作业）
  - [x] SubTask 5.6: 实现 `GET /api/jobs/{job_id}/stages/{stage_id}`（查询阶段结果）
  - [x] SubTask 5.7: 实现 `GET /api/jobs/{job_id}/report`（查询作业汇总报告）

- [x] Task 6: 编写完整测试套件
  - [x] SubTask 6.1: 创建 `tests/test_flow_job.py`，测试 Job/JobStatus/JobState
  - [x] SubTask 6.2: 测试 Recipe 序列化/反序列化
  - [x] SubTask 6.3: 测试 Workspace 目录结构创建
  - [x] SubTask 6.4: 测试 JobScheduler 提交/执行/取消
  - [x] SubTask 6.5: 测试 10 个阶段的执行与输出持久化
  - [x] SubTask 6.6: 测试 JobTracker 查询 API
  - [x] SubTask 6.7: 测试 Web API 作业管理端点

- [x] Task 7: 验证与文档同步
  - [x] SubTask 7.1: 运行完整测试套件，确保所有测试通过（66 passed: flow 58 + web_ui 8）
  - [x] SubTask 7.2: 更新 `docs/commercial_gap_analysis.md`，记录作业流程表达系统的商业对齐情况
  - [x] SubTask 7.3: 更新操作记录，记录本次工作

# Task Dependencies
- [Task 2] depends on [Task 1]（调度器依赖 Job/Stage 数据结构）
- [Task 3] depends on [Task 1]（阶段执行依赖 Stage/Workspace 数据结构）
- [Task 4] depends on [Task 3]（IntegratedPipeline 适配依赖阶段实现）
- [Task 5] depends on [Task 2]（Web API 依赖调度器）
- [Task 6] depends on [Task 4, Task 5]（测试依赖所有实现完成）
- [Task 7] depends on [Task 6]（验证依赖测试通过）
