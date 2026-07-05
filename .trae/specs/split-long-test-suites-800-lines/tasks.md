# Tasks — 拆分 13 个超 800 行测试套件至 ≤800 行

> 顺序按"模块独立 + 同模块聚合"组织。每完成一个子任务：
> 1. `wc -l` 验证新文件 ≤800 行
> 2. `pytest --collect-only modules/<m>/tests/` 验证测试数量不减少
> 3. `git add <精确文件>` → `commit -m "refactor: 拆分 <模块> 测试套件"` → `push origin main`
> 4. 追加 `操作记录.md`
>
> **状态：全部已完成**（commit 3e5470b0，一次性提交全部 40 个新文件 + 13 个删除 + 1 个 conftest）

## 阶段 1: 拆分 13 个测试套件

- [x] Task 1: verify_advanced 拆分为 test_drc.py / test_lvs.py / test_report.py
  - [x] SubTask 1.1: test_drc_* → test_drc.py（752 行，28 blocks）
  - [x] SubTask 1.2: test_lvs_* → test_lvs.py（617 行，23 blocks）
  - [x] SubTask 1.3: test_drc_report_generator / test_drc_check_type_enum / test_drc_rule_dataclass_* /
    test_drc_result_dataclass / test_drc_rule_category_* / test_curvilinear_drc_rule_dataclass /
    test_drc_violation18_* / test_drc_ruleset_presets* / test_validate_ruleset_* /
    test_custom_ruleset_* → test_report.py（565 行，25 blocks）
  - [x] SubTask 1.4: 删除 test_verify_advanced.py + 验证 collect 数量 + git commit

- [x] Task 2: router_advanced 拆分为 test_global_router.py / test_curvy.py / test_bundle.py
  - [x] SubTask 2.1: test_global_router_* → test_global_router.py（695 行，42 blocks）
  - [x] SubTask 2.2: test_curvy_* → test_curvy.py（586 行，42 blocks）
  - [x] SubTask 2.3: test_bundle_* → test_bundle.py（429 行，27 blocks）
  - [x] SubTask 2.4: 删除 test_router_advanced.py + 验证 + git commit

- [x] Task 3: flow 拆分为 test_stages.py / test_scheduler.py / test_workspace.py
  - [x] SubTask 3.1: test_*_stage* / test_stage* / test_pipeline* → test_stages.py（376 行，15 blocks）
  - [x] SubTask 3.2: test_scheduler_* → test_scheduler.py（358 行，9 blocks）
  - [x] SubTask 3.3: 其余 → test_workspace.py（754 行，27 blocks）
  - [x] SubTask 3.4: 删除 test_flow.py + 验证 + git commit

- [x] Task 4: optimizer 拆分为 test_lbfgs.py / test_nsga.py / test_topology.py
  - [x] SubTask 4.1: test_lbfgs_* → test_lbfgs.py（392 行）
  - [x] SubTask 4.2: test_nsga_* → test_nsga.py（384 行）
  - [x] SubTask 4.3: test_topology_* → test_topology.py（743 行，44 blocks）
  - [x] SubTask 4.4: 删除 test_optimizer.py + 验证 + git commit

- [x] Task 5: trainer 拆分为 test_ppo.py / test_pretrain.py / test_transfer.py
  - [x] SubTask 5.1: test_ppo_* → test_ppo.py（740 行，25 blocks）
  - [x] SubTask 5.2: test_pretrain_* → test_pretrain.py（392 行）
  - [x] SubTask 5.3: test_transfer_* → test_transfer.py（304 行）
  - [x] SubTask 5.4: 删除 test_trainer.py + 验证 + git commit

- [x] Task 6: gui 拆分为 test_widgets.py / test_web.py / test_dialogs.py
  - [x] SubTask 6.1: test_widget_* / test_canvas_* → test_widgets.py（718 行，18 blocks）
  - [x] SubTask 6.2: test_web_* → test_web.py（288 行）
  - [x] SubTask 6.3: test_dialog_* / test_macro_debugger_* / test_macro_ide_* → test_dialogs.py（247 行）
  - [x] SubTask 6.4: 删除 test_gui.py + 验证 + git commit

- [x] Task 7: gds_tools 拆分为 conftest.py / test_clip.py / test_density.py / test_loader.py
  - [x] SubTask 7.1: 共享 fixture（klayout_db / test_gds / two_layer_gds）→ conftest.py（145 行）
  - [x] SubTask 7.2: test_clip* / test_copy_layer → test_clip.py（439 行）
  - [x] SubTask 7.3: test_density_* → test_density.py（214 行）
  - [x] SubTask 7.4: 其余 → test_loader.py（534 行）
  - [x] SubTask 7.5: 删除 test_gds_tools.py + 验证 + git commit

- [x] Task 8: circuit 拆分为 test_cascade.py / test_mna.py / test_simulator.py
  - [x] SubTask 8.1: test_cascade_* → test_cascade.py（236 行）
  - [x] SubTask 8.2: test_mna_* → test_mna.py（459 行）
  - [x] SubTask 8.3: test_simulator_* → test_simulator.py（469 行）
  - [x] SubTask 8.4: 删除 test_circuit.py + 验证 + git commit

- [x] Task 9: yield 拆分为 test_mc.py / test_importance.py / test_optimize.py
  - [x] SubTask 9.1: test_mc_* / test_monte_carlo_* → test_mc.py（632 行）
  - [x] SubTask 9.2: test_importance_* → test_importance.py（232 行）
  - [x] SubTask 9.3: test_optimize_* → test_optimize.py（257 行）
  - [x] SubTask 9.4: 删除 test_yield.py + 验证 + git commit

- [x] Task 10: pdk_advanced 拆分为 test_pcell.py / test_multi_pdk.py / test_bridge.py
  - [x] SubTask 10.1: test_pcell_* → test_pcell.py（479 行）
  - [x] SubTask 10.2: test_multi_pdk_* → test_multi_pdk.py（347 行）
  - [x] SubTask 10.3: test_bridge_* → test_bridge.py（267 行）
  - [x] SubTask 10.4: 删除 test_pdk_advanced.py + 验证 + git commit

- [x] Task 11: route 拆分为 test_basic.py / test_curvy.py / test_drc_aware.py
  - [x] SubTask 11.1: test_basic_* / test_route_circuit* → test_basic.py（315 行）
  - [x] SubTask 11.2: test_curvy_* → test_curvy.py（383 行）
  - [x] SubTask 11.3: test_drc_aware_* → test_drc_aware.py（476 行）
  - [x] SubTask 11.4: 删除 test_route.py + 验证 + git commit

- [x] Task 12: inverse 拆分为 test_adjoint.py / test_fdtd_jax.py / test_showcase.py
  - [x] SubTask 12.1: test_adjoint_* → test_adjoint.py（521 行）
  - [x] SubTask 12.2: test_fdtd_jax_* → test_fdtd_jax.py（488 行）
  - [x] SubTask 12.3: test_showcase_* → test_showcase.py（154 行）
  - [x] SubTask 12.4: 删除 test_inverse.py + 验证 + git commit

- [x] Task 13: parasitic 拆分为 test_cap.py / test_ind.py / test_res.py
  - [x] SubTask 13.1: test_cap_* → test_cap.py（700 行，40 blocks）
  - [x] SubTask 13.2: test_ind_* → test_ind.py（196 行）
  - [x] SubTask 13.3: test_res_* / test_generate_*verilog_a* → test_res.py（150 行）
  - [x] SubTask 13.4: 删除 test_parasitic.py + 验证 + git commit

## 阶段 2: 最终验证与文档

- [x] Task 14: 文件行数全量扫描验证
  - [x] SubTask 14.1: 运行 `find modules -path "*/tests/*.py" -exec wc -l {} \; | awk '$1>800' | wc -l`
  - [x] SubTask 14.2: 输出 `0`（验证通过）

- [x] Task 15: pytest collect 数量验证
  - [x] SubTask 15.1: 运行 `pytest --collect-only modules/` 13 个模块
  - [x] SubTask 15.2: 收集到 662 tests collected（与基准一致，1 个 error 为 router_advanced
    的 gymnasium 环境依赖问题，与原文件行为一致，非拆分引入）

- [x] Task 16: 临时脚本清理与提交
  - [x] SubTask 16.1: 删除 `.tmp_split_tests.py`（任务完成后清理，不留垃圾）
  - [x] SubTask 16.2: `git add` 40 个新文件 + 13 个删除 + 1 个 conftest → commit → push origin main
  - [x] SubTask 16.3: commit 3e5470b0 已推送到 main 分支

# Task Dependencies

- Task 1-13 互相独立，可并行（不同模块）
- 实际执行采用一次性提交（40 个新文件 + 13 个删除 + 1 个 conftest 同一 commit）
- Task 14 依赖 Task 1-13 全部完成
- Task 15 依赖 Task 14
- Task 16 依赖 Task 15
