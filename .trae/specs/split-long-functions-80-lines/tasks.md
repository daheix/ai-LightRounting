# Tasks — 拆分 42 个超 80 行函数至 ≤80 行

> 顺序按"严重度优先 + 同文件聚合"组织。每完成一个子任务：
> 1. AST 扫描该文件验证超 80 行函数 = 0
> 2. 运行该模块的 pytest 验证无回归
> 3. `git add <精确文件>` → `commit -m "refactor: 拆分 <模块> 超长函数"` → `push origin main`
> 4. 追加 `操作记录.md`

## 阶段 1: TOP 10 最严重函数（按行数降序，>120L）

- [ ] Task 1: route/__init__.py::bend_compensate (259L) → 拆分为 ≤80 行
  - [ ] SubTask 1.1: 拆出 `_validate_bend_compensate_params`（参数校验）
  - [ ] SubTask 1.2: 拆出 `_build_incoming_per_d2`（构建 device_map + incoming_per_d2 映射）
  - [ ] SubTask 1.3: 拆出 `_try_compensate_one_conn`（拓扑处理单连接：候选 A x 对齐 / 候选 B y 对齐）
  - [ ] SubTask 1.4: 拆出 `_regenerate_paths_after_compensate`（重路由由 + 统计交叉 + 计算损耗）
  - [ ] SubTask 1.5: 验证 AST + route 模块测试 + git commit

- [ ] Task 2: fdfd/solver.py::solve_fdfd (176L) → 拆分为 ≤80 行
  - [ ] SubTask 2.1: 拆出 `_validate_fdfd_params`（参数校验）
  - [ ] SubTask 2.2: 拆出 `_build_fdfd_grid`（构建网格 + Helmholtz 算子 + 源）
  - [ ] SubTask 2.3: 拆出 `_solve_fdfd_linear_system`（求解 + 提取场 / 透射）
  - [ ] SubTask 2.4: 验证 AST + fdfd 模块测试 + git commit

- [ ] Task 3: place/residual.py::_residual_pair_fix (154L) → 拆分为 ≤80 行
  - [ ] SubTask 3.1: 拆出 `_collect_residual_pair_context`（收集上下文）
  - [ ] SubTask 3.2: 拆出 `_evaluate_residual_candidates`（评估候选移动）
  - [ ] SubTask 3.3: 拆出 `_apply_residual_pair_fix`（应用最优候选）
  - [ ] SubTask 3.4: 验证 AST + place 模块测试 + git commit

- [ ] Task 4: gds_tools/gdsii_clip_tool.py::multi_clip_gdsii (150L) → 拆分为 ≤80 行
  - [ ] SubTask 4.1: 拆出 `_validate_multi_clip_params`
  - [ ] SubTask 4.2: 拆出 `_apply_multi_clip_one_region`（单区域裁剪核心）
  - [ ] SubTask 4.3: 拆出 `_assemble_multi_clip_result`
  - [ ] SubTask 4.4: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 5: gds_tools/gdsii_clip_tool.py::clip_gdsii (133L) → 拆分为 ≤80 行
  - [ ] SubTask 5.1: 拆出 `_validate_clip_params`
  - [ ] SubTask 5.2: 拆出 `_apply_clip_one_layer`（单层裁剪核心）
  - [ ] SubTask 5.3: 拆出 `_assemble_clip_result`
  - [ ] SubTask 5.4: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 6: trainer/transfer_learning.py::transfer_learn (132L) → 拆分为 ≤80 行
  - [ ] SubTask 6.1: 拆出 `_validate_transfer_learn_params`
  - [ ] SubTask 6.2: 拆出 `_run_transfer_learn_loop`（训练循环）
  - [ ] SubTask 6.3: 拆出 `_finalize_transfer_learn`（保存检查点 + 返回结果）
  - [ ] SubTask 6.4: 验证 AST + trainer 测试 + git commit

- [ ] Task 7: gds_tools/gdsii_density_analyzer.py::compute_layer_density (130L) → 拆分
  - [ ] SubTask 7.1: 拆出 `_validate_density_params` / `_accumulate_layer_density` / `_format_density_result`
  - [ ] SubTask 7.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 8: gds_tools/gdsii_text_label_extractor.py::extract_text_labels (127L) → 拆分
  - [ ] SubTask 8.1: 拆出 `_validate_text_label_params` / `_collect_text_elements` / `_format_text_labels`
  - [ ] SubTask 8.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 9: orchestrator/flow.py::run_eda_flow (126L) → 拆分为 ≤80 行
  - [ ] SubTask 9.1: 拆出 `_validate_eda_flow_inputs` / `_dispatch_eda_stages` / `_assemble_eda_flow_result`
  - [ ] SubTask 9.2: 验证 AST + orchestrator 测试 + git commit

- [ ] Task 10: yield/importance_sampling_ce.py::cross_entropy_importance_sampling (125L) → 拆分
  - [ ] SubTask 10.1: 拆出 `_validate_ce_params` / `_run_ce_iter_loop` / `_finalize_ce_result`
  - [ ] SubTask 10.2: 验证 AST + yield 模块测试 + git commit

## 阶段 2: 严重函数（100-125L）

- [ ] Task 11: place/legalize.py 两个函数 → 拆分（_legalize 125L, _find_nearest_legal_pos_1d 124L）
  - [ ] SubTask 11.1: 拆 _legalize → `_validate_legalize` / `_run_legalize_pass` / `_finalize_legalize`
  - [ ] SubTask 11.2: 拆 _find_nearest_legal_pos_1d → `_search_legal_pos_bin` / `_check_legal_pos_constraint`
  - [ ] SubTask 11.3: 验证 AST + place 测试 + git commit

- [ ] Task 12: yield/yield_optimization.py::optimize_yield_via_nominal_shift (124L) → 拆分
  - [ ] SubTask 12.1: 拆出 `_validate_yield_shift_params` / `_run_yield_shift_iter` / `_finalize_yield_shift`
  - [ ] SubTask 12.2: 验证 AST + yield 模块测试 + git commit

- [ ] Task 13: gds_tools/gdsii_drc_area.py::check_area (122L) → 拆分
  - [ ] SubTask 13.1: 拆出 `_validate_check_area_params` / `_check_one_polygon_area` / `_assemble_area_violations`
  - [ ] SubTask 13.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 14: fdtd/waveguide.py::simulate_waveguide_fdtd (115L) → 拆分
  - [ ] SubTask 14.1: 拆出 `_validate_waveguide_fdtd_params` / `_build_waveguide_fdtd_grid` / `_run_waveguide_fdtd_loop`
  - [ ] SubTask 14.2: 验证 AST + fdtd 模块测试 + git commit

- [ ] Task 15: gds_tools/gdsii_flattener.py::flatten_gdsii (112L) → 拆分
  - [ ] SubTask 15.1: 拆出 `_validate_flatten_params` / `_flatten_one_cell` / `_assemble_flatten_result`
  - [ ] SubTask 15.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 16: place/residual.py::_try_joint_move (112L) → 拆分
  - [ ] SubTask 16.1: 拆出 `_evaluate_joint_move_candidates` / `_apply_joint_move`
  - [ ] SubTask 16.2: 验证 AST + place 测试 + git commit

- [ ] Task 17: gds_tools/gdsii_geometry_transformer.py::transform_gdsii_geometry (108L) → 拆分
  - [ ] SubTask 17.1: 拆出 `_validate_transform_params` / `_apply_transform_one_polygon` / `_assemble_transformed_result`
  - [ ] SubTask 17.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 18: fdtd/mmi.py::simulate_mmi_fdtd (108L) → 拆分
  - [ ] SubTask 18.1: 拆出 `_validate_mmi_fdtd_params` / `_build_mmi_fdtd_grid` / `_run_mmi_fdtd_loop`
  - [ ] SubTask 18.2: 验证 AST + fdtd 模块测试 + git commit

- [ ] Task 19: gds_tools/gdsii_density_analyzer.py::compute_density_map (101L) → 拆分
  - [ ] SubTask 19.1: 拆出 `_build_density_grid` / `_accumulate_density_map` / `_format_density_map`
  - [ ] SubTask 19.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 20: quantum_advanced/rollout.py::collect_rollout (99L) → 拆分
  - [ ] SubTask 20.1: 拆出 `_validate_rollout_params` / `_run_rollout_episodes` / `_assemble_rollout_result`
  - [ ] SubTask 20.2: 验证 AST + quantum_advanced 测试 + git commit

- [ ] Task 21: trainer/pretrain.py::pretrain (99L) → 拆分
  - [ ] SubTask 21.1: 拆出 `_validate_pretrain_params` / `_run_pretrain_loop` / `_finalize_pretrain`
  - [ ] SubTask 21.2: 验证 AST + trainer 测试 + git commit

- [ ] Task 22: nn/attention.py::_multi_head_attention_op (97L) → 拆分
  - [ ] SubTask 22.1: 拆出 `_mha_input_projection` / `_mha_attention_compute` / `_mha_output_projection`
  - [ ] SubTask 22.2: 验证 AST + nn 模块测试 + git commit

- [ ] Task 23: gds_tools/gdsii_density_analyzer.py::check_density_rules (96L) → 拆分
  - [ ] SubTask 23.1: 拆出 `_validate_density_rules_params` / `_check_one_region_density` / `_assemble_density_violations`
  - [ ] SubTask 23.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 24: yield/importance_sampling.py::importance_sampling_mean (96L) → 拆分
  - [ ] SubTask 24.1: 拆出 `_validate_is_mean_params` / `_run_is_mean_samples` / `_finalize_is_mean`
  - [ ] SubTask 24.2: 验证 AST + yield 模块测试 + git commit

- [ ] Task 25: place/residual.py::_try_single_move (95L) → 拆分
  - [ ] SubTask 25.1: 拆出 `_evaluate_single_move_candidates` / `_apply_single_move`
  - [ ] SubTask 25.2: 验证 AST + place 测试 + git commit

## 阶段 3: 中等函数（81-94L）

- [ ] Task 26: gds_tools/gdsii_layout_scaler.py::scale_gdsii (94L) → 拆分
  - [ ] SubTask 26.1: 拆出 `_validate_scale_params` / `_scale_one_polygon` / `_assemble_scaled_result`
  - [ ] SubTask 26.2: 验证 AST + gds_tools 测试 + git commit

- [ ] Task 27: multiphysics/tcad_thermal/solver.py::thermal_crosstalk_matrix (93L) → 拆分
  - [ ] SubTask 27.1: 拆出 `_validate_thermal_params` / `_build_thermal_coupling_matrix` / `_format_thermal_result`
  - [ ] SubTask 27.2: 验证 AST + multiphysics 测试 + git commit

- [ ] Task 28: yield/stratified_sampling.py::compare_stratified_convergence (89L) → 拆分
  - [ ] SubTask 28.1: 拆出 `_run_stratified_one_strata` / `_compare_convergence_metrics`
  - [ ] SubTask 28.2: 验证 AST + yield 模块测试 + git commit

- [ ] Task 29: core/__init__.py::validate_circuit (87L) → 拆分
  - [ ] SubTask 29.1: 拆出 `_validate_circuit_structure` / `_validate_circuit_semantics` / `_format_validation_report`
  - [ ] SubTask 29.2: 验证 AST + core 测试 + git commit

- [ ] Task 30: yield/batch_simulation.py::batch_simulate (86L) → 拆分
  - [ ] SubTask 30.1: 拆出 `_validate_batch_params` / `_run_batch_one_sim` / `_assemble_batch_result`
  - [ ] SubTask 30.2: 验证 AST + yield 模块测试 + git commit

- [ ] Task 31: pdk_advanced/yaml_config.py::serialize_pdk_yaml (85L) → 拆分
  - [ ] SubTask 31.1: 拆出 `_validate_serialize_params` / `_convert_pdk_to_yaml_dict` / `_write_yaml_file`
  - [ ] SubTask 31.2: 验证 AST + pdk_advanced 测试 + git commit

- [ ] Task 32: gui/layout_editor.py::export_klayout_script (84L) → 拆分
  - [ ] SubTask 32.1: 拆出 `_validate_export_params` / `_build_klayout_script` / `_write_script_file`
  - [ ] SubTask 32.2: 验证 AST + gui 测试 + git commit

- [ ] Task 33: place/metrics.py::_tarjan_scc (84L) → 拆分
  - [ ] SubTask 33.1: 拆出 `_tarjan_strong_connect` / `_tarjan_finalize_scc`
  - [ ] SubTask 33.2: 验证 AST + place 测试 + git commit

- [ ] Task 34: sparam/models.py::directional_coupler_s (84L) → 拆分
  - [ ] SubTask 34.1: 拆出 `_validate_dc_params` / `_compute_dc_coupling_coeff` / `_assemble_dc_s_matrix`
  - [ ] SubTask 34.2: 验证 AST + sparam 测试 + git commit

- [ ] Task 35: gdsio/exporter.py::export_gds (83L) → 拆分
  - [ ] SubTask 35.1: 拆出 `_validate_export_gds_params` / `_build_gds_lib` / `_write_gds_file`
  - [ ] SubTask 35.2: 验证 AST + gdsio 测试 + git commit

- [ ] Task 36: fdfd/solver.py::build_helmholtz_operator (83L) → 拆分（与 Task 2 同文件，合并提交）
  - [ ] SubTask 36.1: 拆出 `_validate_helmholtz_params` / `_assemble_helmholtz_banded`
  - [ ] SubTask 36.2: 验证 AST + fdfd 测试 + git commit

- [ ] Task 37: flow/inverse_design.py::train_step (83L) → 拆分
  - [ ] SubTask 37.1: 拆出 `_validate_train_step_params` / `_run_train_step_forward` / `_apply_grad_update`
  - [ ] SubTask 37.2: 验证 AST + flow 测试 + git commit

- [ ] Task 38: yield/yield_optimization.py::compute_worst_case_distance (82L) → 拆分
  - [ ] SubTask 38.1: 拆出 `_validate_wcd_params` / `_compute_one_corner_distance` / `_select_worst_case`
  - [ ] SubTask 38.2: 验证 AST + yield 模块测试 + git commit

- [ ] Task 39: circuit/cascade.py::cascade_circuit (82L) → 拆分
  - [ ] SubTask 39.1: 拆出 `_validate_cascade_params` / `_cascade_one_stage` / `_assemble_cascade_result`
  - [ ] SubTask 39.2: 验证 AST + circuit 测试 + git commit

- [ ] Task 40: gdsio/importer.py::import_gds (81L) → 拆分
  - [ ] SubTask 40.1: 拆出 `_validate_import_gds_params` / `_parse_gds_lib` / `_build_circuit_from_gds`
  - [ ] SubTask 40.2: 验证 AST + gdsio 测试 + git commit

- [ ] Task 41: flow/stage_verification.py::stage6_drc_lvs (81L) → 拆分
  - [ ] SubTask 41.1: 拆出 `_validate_stage6_params` / `_run_drc_stage` / `_run_lvs_stage` / `_assemble_stage6_report`
  - [ ] SubTask 41.2: 验证 AST + flow 测试 + git commit

## 阶段 4: 最终验证与文档

- [ ] Task 42: AST 全量扫描验证
  - [ ] SubTask 42.1: 运行 AST 扫描 `modules/*/src/**/*.py`，输出 `total violations: 0`
  - [ ] SubTask 42.2: 若有遗漏，回到对应 Task 修复

- [ ] Task 43: 全模块测试无回归
  - [ ] SubTask 43.1: 运行 `pytest modules/` 全量测试，全部通过
  - [ ] SubTask 43.2: 关键数值结果（solve_eme T_dB / solve_bpm T_dB / solve_slab_modes neff /
    route_circuit loss / fdfd transmission）与拆分前一致至小数点后 4 位

- [ ] Task 44: 文档与提交收尾
  - [ ] SubTask 44.1: 更新 `操作记录.md`（每轮拆分记录：轮次 / 文件 / 测试结果 / 规则依据）
  - [ ] SubTask 44.2: `git add 操作记录.md` → commit → push origin main

# Task Dependencies

- Task 1-41 互相独立，可并行（不同模块/不同文件）
- 同文件多个函数（如 gdsii_density_analyzer.py 有 3 个、residual.py 有 3 个、yield 模块 5 个）
  建议同会话顺序处理以避免 merge 冲突
- Task 5 依赖 Task 4（同文件 clip_tool.py，先 multi 后 single 避免行号偏移）
- Task 36 可与 Task 2 合并提交（同文件 fdfd/solver.py）
- Task 42 依赖 Task 1-41 全部完成
- Task 43 依赖 Task 42
- Task 44 依赖 Task 43
