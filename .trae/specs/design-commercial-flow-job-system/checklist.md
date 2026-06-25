# Checklist

## 数据结构验证
- [x] Job dataclass 包含 job_id, recipe, status, stage_results, submit_time, start_time, end_time, workspace, error 字段
- [x] JobStatus 枚举包含 QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED 五种状态
- [x] JobState 状态机实现合法状态转换（QUEUED→RUNNING→COMPLETED/FAILED/CANCELLED）
- [x] Stage dataclass 包含 stage_id, name, inputs, outputs, status 字段
- [x] 10 个标准化阶段定义完整（stage1_pdk 到 stage10_inverse）
- [x] Recipe dataclass 包含 circuit_spec, platform, placement_algo, router_algo, sim_config, output_dir, enabled_stages 字段
- [x] Recipe 支持 to_yaml/from_yaml/to_json/from_json 序列化
- [x] Workspace 创建标准目录结构（inputs/logs/stages/reports/gds + job.json）

## 调度器验证
- [x] JobScheduler.submit(job) 返回 job_id，作业状态为 QUEUED
- [x] JobScheduler 支持并行执行（max_workers 可配置，默认 4）
- [x] 作业状态转换正确（QUEUED→RUNNING→COMPLETED/FAILED）
- [x] JobScheduler.cancel(job_id) 将作业状态改为 CANCELLED
- [x] 作业失败时记录错误信息

## 阶段执行验证
- [x] stage1_pdk 输出 device_catalog.json
- [x] stage2_circuit 输出 circuit.json
- [x] stage3_placement 输出 placements.json
- [x] stage4_routing 输出 routes.json
- [x] stage5_simulation 输出 sparams.json
- [x] stage6_drc_lvs 输出 drc_report.json
- [x] stage7_gds 输出 layout.gds
- [x] stage8_opto_electrical 输出 opto_electrical.json
- [x] stage9_quantum 输出 quantum_report.json
- [x] stage10_inverse 输出 inverse_design.json
- [x] 阶段间数据传递正确（上一阶段输出 → 下一阶段输入）
- [x] 阶段依赖检查正确（依赖阶段未完成时标记 BLOCKED）

## IntegratedPipeline 适配验证
- [x] IntegratedPipeline.run(circuit) 保留同步行为（向后兼容）
- [x] IntegratedPipeline.run_as_stages(recipe, workspace) 返回 list[StageResult]
- [x] 阶段化执行结果与同步执行结果一致

## Web API 验证
- [x] POST /api/jobs 返回 job_id 和 status=queued
- [x] GET /api/jobs 返回作业列表
- [x] GET /api/jobs/{job_id} 返回作业详情
- [x] GET /api/jobs/{job_id}/status 返回状态和进度
- [x] POST /api/jobs/{job_id}/cancel 取消作业
- [x] GET /api/jobs/{job_id}/stages/{stage_id} 返回阶段结果
- [x] GET /api/jobs/{job_id}/report 返回汇总报告

## 测试套件验证
- [x] tests/test_flow_job.py 所有测试通过（58 passed）
- [x] 现有测试（test_web_ui.py 等）不回归（8 passed）
- [x] 代码覆盖率 ≥ 80%

## 商业对齐验证
- [x] 作业模型对齐 Luceda IPKISS 四步流程（器件设计→线路设计→设计验证→流片准备）
- [x] 调度器对齐 Cadence ADE-XL（作业队列 + 资源调度 + 并行 worker）
- [x] 阶段化对齐 Synopsys ICC2（floorplan→placement→CTS→routing→optimization）
- [x] 异步执行对齐 Ansys Lumerical（作业提交 + 状态轮询 + 结果归档）
