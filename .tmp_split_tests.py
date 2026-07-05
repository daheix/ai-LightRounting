#!/usr/bin/env python3
"""拆分超800行的测试套件文件。R11 质量门禁: 文件<=800行。"""
import re
import sys
from pathlib import Path

WORKSPACE = Path('/workspace')


def match_name(name, patterns):
    for p in patterns:
        if p.endswith('*'):
            if name.startswith(p[:-1]):
                return True
        else:
            if name == p:
                return True
    return False


def parse_blocks(lines):
    header_end = len(lines)
    for i, line in enumerate(lines):
        if re.match(r'^(def test_|class Test|@pytest|@fixture)', line):
            header_end = i
            break
    header = lines[:header_end]
    block_starts = []
    for i in range(header_end, len(lines)):
        if re.match(r'^(def |class |@pytest|@fixture)', lines[i]):
            block_starts.append(i)
    blocks = []
    for idx, start in enumerate(block_starts):
        end = block_starts[idx + 1] if idx + 1 < len(block_starts) else len(lines)
        name = None
        for j in range(start, end):
            m = re.match(r'^(def|class)\s+(\w+)', lines[j])
            if m:
                name = m.group(2)
                break
        if name:
            blocks.append((name, start, end))
    return header, blocks


def split_one(config, dry_run=False):
    src = WORKSPACE / config['src']
    if not src.exists():
        print(f"SKIP: {src} 不存在")
        return False
    content = src.read_text()
    lines = content.split('\n')
    header, blocks = parse_blocks(lines)
    print(f"\n=== {src.relative_to(WORKSPACE)} ({len(lines)} lines, {len(blocks)} blocks) ===")
    assignments = {out_name: [] for out_name, _ in config['outputs']}
    unmatched = []
    for name, start, end in blocks:
        matched = False
        for out_name, patterns in config['outputs']:
            if match_name(name, patterns):
                assignments[out_name].append((name, start, end))
                matched = True
                break
        if not matched:
            unmatched.append(name)
    if unmatched:
        print(f"  WARNING 未归类: {unmatched}")
        return False
    total_assigned = sum(len(v) for v in assignments.values())
    if total_assigned != len(blocks):
        print(f"  WARNING 分配数不匹配: {total_assigned} vs {len(blocks)}")
        return False
    all_ok = True
    for out_name, out_blocks in assignments.items():
        out_lines = list(header)
        if out_lines and out_lines[-1] != '':
            out_lines.append('')
        for name, start, end in out_blocks:
            out_lines.extend(lines[start:end])
        while out_lines and out_lines[-1] == '':
            out_lines.pop()
        out_lines.append('')
        out_path = src.parent / out_name
        total_lines = len(out_lines)
        marker = " OK" if total_lines <= 800 else " OVER800!"
        print(f"  {out_name}: {len(out_blocks)} blocks, {total_lines} lines{marker}")
        if total_lines > 800:
            all_ok = False
        if not dry_run and all_ok:
            out_path.write_text('\n'.join(out_lines))
    return all_ok


SPLITS = [
    {
        'src': 'modules/verify_advanced/tests/test_verify_advanced.py',
        'outputs': [
            ('test_drc.py', [
                'test_eqdrc_*', 'test_foundry_drc_*', 'test_drc_*', 'test_klayout_drc_*',
                'test_run_klayout_drc*', 'test_bvh_*', 'test_row_partition',
                'test_hierarchical_drc_*', 'test_run_hierarchical_drc*',
                'test_curvilinear_drc_*', 'test_drc_rule_category_*',
                'test_curvilinear_drc_rule_*', 'test_drc_violation18_*',
                'test_drc_ruleset_*', 'test_validate_ruleset_*',
                'test_custom_ruleset_*', 'test_tiled_drc_*', 'test_deep_drc_*',
                'test_litho_*',
            ]),
            ('test_lvs.py', [
                'test_violation_type_*', 'test_lvs_mismatch_*',
                'test_extracted_netlist_*', 'test_netlist_node_*',
                'test_photonics_netlist_*', 'test_graph_isomorphism_*',
                'test_run_graph_lvs*', 'test_verify_waveguide_*',
                'test_equivalence_*', 'test_lvs_advanced_*',
                'test_connectivity_*', 'test_match_devices_*',
                'test_curvilinear_lvs_*', 'test_extract_connectivity_*',
                'test_hierarchical_lvs_*', '_make_3level_hierarchy',
            ]),
            ('test_report.py', [
                'test_module_import_and_version', 'test_gds_layer_*',
                'test_polaris_gds_layer_*', 'test_get_layer_*',
                'test_get_category_*', 'test_physical_constants',
                'test_layer_spec_*', 'test_layout_get_*',
                'test_parasitic_*', 'test_drc_report_generator',
                'test_generate_structured_error_report_*',
            ]),
        ],
    },
    {
        'src': 'modules/router_advanced/tests/test_router_advanced.py',
        'outputs': [
            ('test_global_router.py', [
                'test_jps_*', 'test_obstacle_grid_*', 'test_auto_grid_size_*',
                'test_platform_constraints*', 'test_get_platform_constraints*',
                'test_waveguide_path_*', 'test_router_constraints_*',
                'test_grid_router_*', 'test_route_connection_*',
                'test_global_router_*', 'test_gcell_*',
                'test_multilayer_router_*', 'test_otv_spec_*',
                'test_hybrid_router_*', 'test_waveguide_type_enum*',
                'test_opto_electrical_router_*', 'test_rip_reroute_*',
                'test_route_with_rip_reroute_*', 'test_routing_env_*',
                '_MockBBox', '_MockDevice', '_MockPlacement', 'np_zeros',
                'test_no_fallback_invalid_inputs', 'test_package_exports_complete',
            ]),
            ('test_curvy.py', [
                'test_all_angle_router_*', 'test_euler_bend_*',
                'test_curvy_astar_*', 'test_diagonal_router_*',
                'test_dubins_path_*', 'test_path_geometry_tools_*',
                'test_arc_bend_*', 'test_check_min_spacing*',
                'test_count_crossings*', 'test_equalize_length*',
                'test_path_loss*', 'test_curve_type_enum*',
                'test_adaptive_crossing_*', 'test_congestion_aware_*',
                'test_optodesigner_*', 'test_drv_free_validator_*',
                'test_high_order_bezier_*', 'test_commercial_router_*',
            ]),
            ('test_bundle.py', [
                'test_bundle_router_*', 'test_route_bundle_*',
                'test_auto_taper*', 'test_length_defined_connector_*',
                'test_phase_matched_router_*', 'test_rf_gsg_router_*',
                'test_bus_router_*', 'test_gf_router_*', 'test_gf_route_*',
            ]),
        ],
    },
    {
        'src': 'modules/flow/tests/test_flow.py',
        'outputs': [
            ('test_stages.py', [
                'test_module_import', 'test_job_status_enum',
                'test_job_state_*', 'test_job_lifecycle_*',
                'test_job_mark_*', 'test_job_generate_*',
                'test_stage_*', 'test_standard_stages_*',
                'test_get_stage_*', 'test_recipe_*',
            ]),
            ('test_scheduler.py', [
                'test_job_tracker_*', 'test_job_scheduler_*',
                'test_task_status_*', 'test_distributed_scheduler_*',
            ]),
            ('test_workspace.py', [
                'test_workspace_*', '_make_workspace',
                'test_ipkiss_*', 'test_netlist_view_*',
                'test_layout_view_*', 'test_circuit_model_view_*',
                'test_sdl_flow_*', 'test_closed_loop_*',
                'test_ipkiss_pdk_bridge_*',
                'test_design_intent_engine_*', '_make_intent_config',
                '_make_schematic', 'test_waveguide_simulator_*',
                'test_pdk_device_sampler_*',
                'test_rl_inverse_designer_*', 'test_gan_inverse_designer_*',
                'test_diffusion_inverse_designer_*', 'test_inverse_design_evaluator',
                'test_lazy_export_*', 'test_no_except_empty_body_r03',
            ]),
        ],
    },
    {
        'src': 'modules/optimizer/tests/test_optimizer.py',
        'outputs': [
            ('test_lbfgs.py', [
                'test_lbfgs_*', 'test_create_lbfgs_*',
                'test_run_lbfgs_*', 'test_pso_*', 'test_create_pso_*',
                'test_cmaes_*', 'test_create_cmaes_*', 'test_global_method_*',
                'test_create_global_*', 'test_run_global_*',
                'test_objective_*',
            ]),
            ('test_nsga.py', [
                'test_sbx_*', 'test_individual_*', 'test_nsga2_*',
                'test_dominates_*', 'test_fast_non_dominated_*',
                'test_compute_crowding_*', 'test_tournament_*',
                'test_polynomial_*', 'test_generate_reference_points*',
                'test_nsga3_*',
            ]),
            ('test_topology.py', [
                'test_topology_*', 'test_level_set_*', 'test_run_topology_*',
                'test_hj_*', 'test_grid_step_*', 'test_compute_cfl_*',
                'test_evolve_hj_*', 'test_create_hj_solver_*',
                'test_flux_pair_*', 'test_tolerance_*', 'test_robust_*',
                'test_create_tolerance_model_*', 'test_evaluate_robustness_*',
                'test_run_robust_*', 'test_optimization_backend_*',
                'test_shape_adjoint_*', 'test_parameterized_geometry_*',
                'test_run_shape_adjoint_*', 'test_violation_*',
                'test_placement_*', 'test_routing_hint_*', 'test_feedback_*',
            ]),
        ],
    },
    {
        'src': 'modules/trainer/tests/test_trainer.py',
        'outputs': [
            ('test_ppo.py', [
                'test_import_and_exports', 'test_module_constants',
                'test_ppo_config_*', 'test_rollout_buffer_*',
                'test_transition_*', 'test_actor_critic_*',
                'test_ppo_agent_*', 'test_ppo_save_load_*',
                'test_load_agent_*', 'test_compute_gae*',
                'test_lr_scale_*', 'test_obs_to_vector_*', 'test_pad_obs*',
                'test_infer_obs_dim*', 'test_discretize_*',
                'test_train_ppo_*', 'test_train_with_env_factory_*',
                'test_rl_advanced_env', 'test_large_scale_env_*',
                'test_ppo_adv_*', '_FakeEnv', '_make_circuit',
            ]),
            ('test_pretrain.py', [
                'test_pareto_*', 'test_pretrained_policy_*',
                'test_hybrid_placement_*', 'test_checkpoint_manager_*',
                'test_no_fallback_r03_r04',
            ]),
            ('test_transfer.py', [
                'test_parallel_rollout_*', '_make_mock_env_configs',
                'test_no_except_empty_body_r03',
            ]),
        ],
    },
    {
        'src': 'modules/gui/tests/test_gui.py',
        'outputs': [
            ('test_widgets.py', [
                'test_module_import_and_all', 'test_object_type_*',
                'test_evaluate_*', 'test_command_stack_*',
                'test_snap_engine_*', 'test_airline_router_*',
                'test_macro_debugger_*', 'test_macro_ide_*',
                'test_viewer_guard_*', 'test_layout_editor_*',
                'test_editor_config_*',
            ]),
            ('test_web.py', [
                'test_knowledge_graph_*', 'test_tfidf_*',
                'test_pagerank_*', 'test_irt3pl_*',
            ]),
            ('test_dialogs.py', [
                'test_lazy_export_*',
            ]),
        ],
    },
    {
        'src': 'modules/gds_tools/tests/test_gds_tools.py',
        'outputs': [
            ('test_clip.py', [
                'test_clip_*', 'test_multi_clip_*', 'test_delete_layers*',
                'test_merge_*', 'test_scale_*', 'test_analyze_cell_*',
                'test_detect_circular_*', 'test_rename_cells*',
                'test_boolean_*', 'test_transform_*', 'test_size_layer*',
                'test_compare_*', 'test_generate_diff_*',
                'test_tapeout_*', 'test_run_batch_*', 'test_check_area*',
                'test_discretize_*', 'test_bspline_*', 'test_catmull_rom_*',
                '_make_layout', '_make_simple_layout',
            ]),
            ('test_density.py', [
                'test_compute_layer_density*', 'test_compute_density_map*',
                'test_check_density_*', 'test_check_grid_*',
                'test_extract_*', 'test_analyze_layer_*',
                'test_analyze_cross_layer_*', 'test_list_isolated_*',
            ]),
            ('test_loader.py', [
                'test_gds', 'test_point_*', 'test_shape_*', 'test_instance_*',
                'test_cell_*', 'test_layer_info_*', 'test_format_layout_*',
                'test_layouts_equal_*', 'test_default_layer_map*',
                'test_supported_formats_*', 'test_openaccess_*',
                'test_version_*', 'test_exports_*', 'test_multi_format_*',
                'test_openaccess_db_*', 'test_render_*', 'test_export_oasis*',
                'test_atomic_write_*', 'test_generate_gdsii_statistics*',
                'test_generate_statistics_*', 'test_check_gdsii_health*',
                'test_flatten_*', 'test_generate_flatten_*',
            ]),
        ],
    },
    {
        'src': 'modules/circuit/tests/test_circuit.py',
        'outputs': [
            ('test_cascade.py', [
                'test_cascade_*', 'test_signal_flow_graph_*',
                'test_circuit_simulator_*',
            ]),
            ('test_mna.py', [
                'test_mna_*', 'test_time_domain_*', 'test_to_time_domain_*',
                'test_subcircuit_*', 'test_term_to_ref_*',
                'test_connector_to_connection_*', 'test_tllm_*',
                'test_yee_grid_*', 'test_pml_*', 'test_fdtd_*',
            ]),
            ('test_simulator.py', [
                'test_waveguide_*', 'test_y_branch_*', 'test_mmi_*',
                'test_directional_coupler_*', 'test_ring_*',
                'test_grating_coupler_*', 'test_phase_shifter_*',
                'test_crossing_*', 'test_terminator_*',
                'test_nonlinear_*', 'test_system_level_*',
                'test_optical_link_*', 'test_ber_*',
                'test_hybrid_simulator_*', 'test_group_delay_*',
                'test_compute_condition_number*', 'test_no_except_empty_body_r03',
            ]),
        ],
    },
    {
        'src': 'modules/yield/tests/test_yield.py',
        'outputs': [
            ('test_mc.py', [
                'test_monte_carlo_*', 'test_yield_analysis_*',
                'test_sensitivity_analysis_*', 'test_sobol_*',
                'test_qmc_*', 'test_generate_qmc_*',
                'test_transform_to_distribution_*', 'test_compare_qmc_*',
                'test_stratified_*', 'test_compare_stratified_*',
                'test_batch_*', 'test_monte_carlo_result_*',
                'test_package_version_*',
            ]),
            ('test_importance.py', [
                'test_biasing_*', 'test_importance_sampling_*',
                'test_rare_event_*', 'test_cross_entropy_*',
                'test_allocation_strategy_*',
            ]),
            ('test_optimize.py', [
                'test_compute_worst_case_*', 'test_allocate_tolerance_*',
                'test_optimize_yield_*',
            ]),
        ],
    },
    {
        'src': 'modules/pdk_advanced/tests/test_pdk_advanced.py',
        'outputs': [
            ('test_pcell.py', [
                'test_polaris_cell_decorator_*', 'test_transform_matrix_*',
                'test_pcell_cache_*', 'test_ai_generate_pcell_*',
                'test_yaml_pdk_*', 'test_build_polaris_pdk_*',
                'test_yaml_validation_*', 'test_pycell_factory_*',
                'test_pcell_multiview_*', '_make_device',
            ]),
            ('test_multi_pdk.py', [
                'test_multi_pdk_manager_*', 'test_design_intent_engine_*',
                'test_flex_connector_*', 'test_hierarchy_design_*',
                'test_pdaflow_*', 'test_device_*', 'test_direction_enum_*',
                'test_source_frozen*',
            ]),
            ('test_bridge.py', [
                'test_package_version_*', 'test_list_gdsfactory_pdks_*',
                'test_get_gdsfactory_pdk_*', 'test_pdk_info_*',
                'test_polaris_pdk_registry_*', 'test_polaris_layer_*',
                'test_polaris_cross_*', 'test_parse_pic_yaml*',
                'test_check_gdsfactory_*',
            ]),
        ],
    },
    {
        'src': 'modules/route/tests/test_route.py',
        'outputs': [
            ('test_basic.py', [
                'TestRouteConstants', 'TestCurveType', 'TestPathLength',
                'TestCountBends', 'TestCountCrossings', 'TestComputePathLoss',
                '_make_mzi_circuit',
            ]),
            ('test_curvy.py', [
                'TestCurvyRouteConfig', 'TestCurvyRouter',
                'TestGenerateArcBend', 'TestGenerateEulerBend',
                'TestSBendBezier',
            ]),
            ('test_drc_aware.py', [
                'TestRouteCircuitEndToEnd',
            ]),
        ],
    },
    {
        'src': 'modules/inverse/tests/test_inverse.py',
        'outputs': [
            ('test_adjoint.py', [
                'TestJaxAutograd', 'TestRunAdjointOptimization',
                'TestR05Regression', 'TestEpsilonRFromWidth', 'TestFomFn',
            ]),
            ('test_fdtd_jax.py', [
                'TestConstants', 'TestYeeGrid3D', 'TestGedneyPML',
                'TestDifferentiableFDTD', '_build_default_fdtd',
                '_default_source_monitor',
            ]),
            ('test_showcase.py', [
                'test_optimize_waveguide_width_full',
            ]),
        ],
    },
    {
        'src': 'modules/parasitic/tests/test_parasitic.py',
        'outputs': [
            ('test_cap.py', [
                'test_parasitic_capacitance_*', 'test_capacitor_*',
                'test_sparam_*', 'test_spice_*', 'test_spice_netlist_writer_*',
                'test_advanced_extractor_*', 'test_generate_*_verilog_a*',
                'test_verilog_a_*', 'test_save_verilog_a*',
                'test_spice_simulation_*', 'test_generate_spice_*',
                'test_co_simulation_*', 'test_differentiable_*',
                'test_optimize_*', 'test_package_api_*',
            ]),
            ('test_ind.py', [
                'test_parasitic_inductance_*', 'test_inductor_*',
                'test_device_type_*', 'test_supported_device_types_*',
                'test_default_physical_*',
            ]),
            ('test_res.py', [
                'test_parasitic_resistance_*', 'test_resistor_*',
            ]),
        ],
    },
]


def main():
    dry = '--dry' in sys.argv
    only = None
    for arg in sys.argv[1:]:
        if arg.startswith('--only='):
            only = int(arg.split('=')[1]) - 1
    all_ok = True
    for idx, config in enumerate(SPLITS):
        if only is not None and idx != only:
            continue
        ok = split_one(config, dry_run=dry)
        if not ok:
            all_ok = False
            print(f"  >>> FAILED: {config['src']}")
    print(f"\n{'ALL OK' if all_ok else 'HAS FAILURES'}")
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
