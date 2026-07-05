# Checklist — 拆分 42 个超 80 行函数至 ≤80 行

## 阶段 1: TOP 10 最严重函数（>120L）

- [ ] route/__init__.py::bend_compensate 拆为 ≤80 行（_validate_bend_compensate_params /
  _build_incoming_per_d2 / _try_compensate_one_conn / _regenerate_paths_after_compensate）
- [ ] fdfd/solver.py::solve_fdfd 拆为 ≤80 行（_validate_fdfd_params / _build_fdfd_grid /
  _solve_fdfd_linear_system）
- [ ] place/residual.py::_residual_pair_fix 拆为 ≤80 行（_collect_residual_pair_context /
  _evaluate_residual_candidates / _apply_residual_pair_fix）
- [ ] gds_tools/gdsii_clip_tool.py::multi_clip_gdsii 拆为 ≤80 行
- [ ] gds_tools/gdsii_clip_tool.py::clip_gdsii 拆为 ≤80 行
- [ ] trainer/transfer_learning.py::transfer_learn 拆为 ≤80 行
- [ ] gds_tools/gdsii_density_analyzer.py::compute_layer_density 拆为 ≤80 行
- [ ] gds_tools/gdsii_text_label_extractor.py::extract_text_labels 拆为 ≤80 行
- [ ] orchestrator/flow.py::run_eda_flow 拆为 ≤80 行
- [ ] yield/importance_sampling_ce.py::cross_entropy_importance_sampling 拆为 ≤80 行

## 阶段 2: 严重函数（100-125L）

- [ ] place/legalize.py::_legalize 拆为 ≤80 行
- [ ] place/legalize.py::_find_nearest_legal_pos_1d 拆为 ≤80 行
- [ ] yield/yield_optimization.py::optimize_yield_via_nominal_shift 拆为 ≤80 行
- [ ] gds_tools/gdsii_drc_area.py::check_area 拆为 ≤80 行
- [ ] fdtd/waveguide.py::simulate_waveguide_fdtd 拆为 ≤80 行
- [ ] gds_tools/gdsii_flattener.py::flatten_gdsii 拆为 ≤80 行
- [ ] place/residual.py::_try_joint_move 拆为 ≤80 行
- [ ] gds_tools/gdsii_geometry_transformer.py::transform_gdsii_geometry 拆为 ≤80 行
- [ ] fdtd/mmi.py::simulate_mmi_fdtd 拆为 ≤80 行
- [ ] gds_tools/gdsii_density_analyzer.py::compute_density_map 拆为 ≤80 行
- [ ] quantum_advanced/rollout.py::collect_rollout 拆为 ≤80 行
- [ ] trainer/pretrain.py::pretrain 拆为 ≤80 行
- [ ] nn/attention.py::_multi_head_attention_op 拆为 ≤80 行
- [ ] gds_tools/gdsii_density_analyzer.py::check_density_rules 拆为 ≤80 行
- [ ] yield/importance_sampling.py::importance_sampling_mean 拆为 ≤80 行
- [ ] place/residual.py::_try_single_move 拆为 ≤80 行

## 阶段 3: 中等函数（81-94L）

- [ ] gds_tools/gdsii_layout_scaler.py::scale_gdsii 拆为 ≤80 行
- [ ] multiphysics/tcad_thermal/solver.py::thermal_crosstalk_matrix 拆为 ≤80 行
- [ ] yield/stratified_sampling.py::compare_stratified_convergence 拆为 ≤80 行
- [ ] core/__init__.py::validate_circuit 拆为 ≤80 行
- [ ] yield/batch_simulation.py::batch_simulate 拆为 ≤80 行
- [ ] pdk_advanced/yaml_config.py::serialize_pdk_yaml 拆为 ≤80 行
- [ ] gui/layout_editor.py::export_klayout_script 拆为 ≤80 行
- [ ] place/metrics.py::_tarjan_scc 拆为 ≤80 行
- [ ] sparam/models.py::directional_coupler_s 拆为 ≤80 行
- [ ] gdsio/exporter.py::export_gds 拆为 ≤80 行
- [ ] fdfd/solver.py::build_helmholtz_operator 拆为 ≤80 行
- [ ] flow/inverse_design.py::train_step 拆为 ≤80 行
- [ ] yield/yield_optimization.py::compute_worst_case_distance 拆为 ≤80 行
- [ ] circuit/cascade.py::cascade_circuit 拆为 ≤80 行
- [ ] gdsio/importer.py::import_gds 拆为 ≤80 行
- [ ] flow/stage_verification.py::stage6_drc_lvs 拆为 ≤80 行

## 通用质量门禁（每个函数拆分后必查）

- [ ] 拆分后函数行数 ≤80（AST 验证）
- [ ] 公共 API 函数签名不变（参数名 / 类型 / 默认值 / 返回结构）
- [ ] 子函数全部以 `_` 前缀命名（不导出至 `__all__`）
- [ ] 无 `except: pass` / `return None` / `return []` 假数据（R03）
- [ ] 无 `TODO` / `FIXME` / `HACK` 残留（R05）
- [ ] 物理公式 / 参数溯源注释完整保留（R02）
- [ ] 模块 pytest 全部通过，无回归
- [ ] 关键数值结果与拆分前一致至小数点后 4 位

## 最终验证

- [ ] AST 全量扫描 `modules/*/src/**/*.py`，输出 `total violations: 0`
- [ ] `pytest modules/` 全量测试通过
- [ ] 每个模块拆分后已 `git add <精确文件>` → commit → push origin main
- [ ] `操作记录.md` 已追加本轮拆分记录（轮次 / 文件 / 测试结果 / 规则依据）
- [ ] R11 V8 工作流：所有提交在 main 分支，无 --force，无 git add -A
