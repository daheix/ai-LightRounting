# 拆分超 800 行测试套件至 ≤800 行 Spec

## Why
PoLaRIS 项目 R11 质量门禁要求"文件 ≤800 行"，但 `modules/*/tests/` 目录扫描显示
有 **13 个测试套件文件超 800 行**（最长 1983L `test_gds_tools.py`）。这些文件职责混杂、
加载缓慢、单文件失败影响范围过大，违反 R11 门禁、阻碍后续维护与商业对齐。本 spec
系统拆分全部 13 个超长测试套件为多个 ≤800 行子文件（保持所有测试函数体不变，仅做物理
切分与 header 复制），并新增 `conftest.py` 沉淀共享 fixture（符合 pytest 最佳实践）。

## What Changes
- 拆分 13 个超 800 行测试套件为 40 个 ≤800 行子文件（共涉及 13 个子模块）
- 保持所有测试函数体（断言、参数、docstring）原样不变，仅做文件级物理切分
- 每个子文件保留原文件的完整 header（module docstring、学术文献 URL、import 语句、
  `sys.path` 注入、`pytest.importorskip` 行为），确保测试环境与导入行为一致
- 新增 `modules/gds_tools/tests/conftest.py` 沉淀 3 个共享 fixture
  （`klayout_db` / `test_gds` / `two_layer_gds`），供 `test_clip.py` / `test_density.py` /
  `test_loader.py` 共享，消除 fixture 复制
- 删除 13 个原始超长文件（拆分完成后用新文件替代，R13 §3 单一最新代码原则）
- 拆分模式（按测试类/功能前缀）：
  - **verify_advanced**：`test_drc_*` → `test_drc.py`；`test_lvs_*` → `test_lvs.py`；
    `test_drc_report_generator` / `test_drc_check_type_enum` / `test_drc_rule_dataclass_*` /
    `test_drc_result_dataclass` / `test_drc_rule_category_*` / `test_curvilinear_drc_rule_dataclass` /
    `test_drc_violation18_*` / `test_drc_ruleset_presets*` / `test_validate_ruleset_*` /
    `test_custom_ruleset_*` → `test_report.py`
  - **router_advanced**：`test_global_router_*` → `test_global_router.py`；
    `test_curvy_*` → `test_curvy.py`；`test_bundle_*` → `test_bundle.py`
  - **flow**：`test_*_stage*` / `test_stage*` / `test_pipeline*` → `test_stages.py`；
    `test_scheduler_*` → `test_scheduler.py`；其余 → `test_workspace.py`
  - **optimizer**：`test_lbfgs_*` → `test_lbfgs.py`；`test_nsga_*` → `test_nsga.py`；
    `test_topology_*` → `test_topology.py`
  - **trainer**：`test_ppo_*` → `test_ppo.py`；`test_pretrain_*` → `test_pretrain.py`；
    `test_transfer_*` → `test_transfer.py`
  - **gui**：`test_widget_*` / `test_canvas_*` → `test_widgets.py`；
    `test_web_*` → `test_web.py`；`test_dialog_*` / `test_macro_debugger_*` /
    `test_macro_ide_*` → `test_dialogs.py`
  - **gds_tools**：共享 fixture → `conftest.py`；`test_clip*` / `test_copy_layer` → `test_clip.py`；
    `test_density_*` → `test_density.py`；其余 → `test_loader.py`
  - **circuit**：`test_cascade_*` → `test_cascade.py`；`test_mna_*` → `test_mna.py`；
    `test_simulator_*` → `test_simulator.py`
  - **yield**：`test_mc_*` / `test_monte_carlo_*` → `test_mc.py`；
    `test_importance_*` → `test_importance.py`；`test_optimize_*` → `test_optimize.py`
  - **pdk_advanced**：`test_pcell_*` → `test_pcell.py`；`test_multi_pdk_*` → `test_multi_pdk.py`；
    `test_bridge_*` → `test_bridge.py`
  - **route**：`test_basic_*` / `test_route_circuit*` → `test_basic.py`；
    `test_curvy_*` → `test_curvy.py`；`test_drc_aware_*` → `test_drc_aware.py`
  - **inverse**：`test_adjoint_*` → `test_adjoint.py`；`test_fdtd_jax_*` → `test_fdtd_jax.py`；
    `test_showcase_*` → `test_showcase.py`
  - **parasitic**：`test_cap_*` → `test_cap.py`；`test_ind_*` → `test_ind.py`；
    `test_res_*` / `test_generate_*verilog_a*` → `test_res.py`
- 每拆分完一个模块立即 `git add <精确文件> → commit → push origin main`（R11）
- 拆分后 `find modules -path "*/tests/*.py" -exec wc -l {} \; | awk '$1>800' | wc -l` = 0
- 拆分后 `pytest --collect-only` 测试总数不减少（基准 662 tests collected）

## Impact
- Affected specs:
  - `split-long-functions-80-lines`（互补关系：本 spec 关注测试文件 ≤800 行，
    该 spec 关注源码函数 ≤80 行，两者共同满足 R11 质量门禁）
  - `audit-academic-integrity-deep`（拆分不得丢失原 docstring 中的文献 URL，R02 不变）
- Affected code（13 个子模块的 tests 目录）：
  - `modules/verify_advanced/tests/`（删 1 增 3：test_drc.py / test_lvs.py / test_report.py）
  - `modules/router_advanced/tests/`（删 1 增 3：test_global_router.py / test_curvy.py / test_bundle.py）
  - `modules/flow/tests/`（删 1 增 3：test_stages.py / test_scheduler.py / test_workspace.py）
  - `modules/optimizer/tests/`（删 1 增 3：test_lbfgs.py / test_nsga.py / test_topology.py）
  - `modules/trainer/tests/`（删 1 增 3：test_ppo.py / test_pretrain.py / test_transfer.py）
  - `modules/gui/tests/`（删 1 增 3：test_widgets.py / test_web.py / test_dialogs.py）
  - `modules/gds_tools/tests/`（删 1 增 4：conftest.py / test_clip.py / test_density.py / test_loader.py）
  - `modules/circuit/tests/`（删 1 增 3：test_cascade.py / test_mna.py / test_simulator.py）
  - `modules/yield/tests/`（删 1 增 3：test_mc.py / test_importance.py / test_optimize.py）
  - `modules/pdk_advanced/tests/`（删 1 增 3：test_pcell.py / test_multi_pdk.py / test_bridge.py）
  - `modules/route/tests/`（删 1 增 3：test_basic.py / test_curvy.py / test_drc_aware.py）
  - `modules/inverse/tests/`（删 1 增 3：test_adjoint.py / test_fdtd_jax.py / test_showcase.py）
  - `modules/parasitic/tests/`（删 1 增 3：test_cap.py / test_ind.py / test_res.py）

## ADDED Requirements

### Requirement: 所有测试文件 ≤800 行
PoLaRIS 全部 `modules/*/tests/**/*.py` 文件 SHALL 满足 `wc -l <= 800`。

#### Scenario: 文件行数扫描通过
- **WHEN** 运行 `find modules -path "*/tests/*.py" -exec wc -l {} \; | awk '$1>800' | wc -l`
- **THEN** 输出 `0`

### Requirement: 测试函数体保持原样
拆分 SHALL 保持所有测试函数（`test_*`）的函数体、断言、参数、docstring 完全不变，
仅做文件级物理切分。不允许在拆分过程中修改任何测试逻辑。

#### Scenario: 测试行为无回归
- **WHEN** 运行 `pytest --collect-only modules/`
- **THEN** 收集到的测试总数与拆分前一致（基准 662 tests collected）

### Requirement: 子文件保留完整 header
每个拆分产生的新文件 SHALL 保留原文件的完整 header，包括：
- module docstring（含 R02 学术文献 URL）
- `from __future__ import annotations`
- 所有 import 语句
- `sys.path` 注入逻辑（让测试既能从已安装包导入，也能从源码树导入）
- `pytest.importorskip` 行为（R03 禁止 fall-back，依赖缺失即跳过，不伪造）

#### Scenario: 导入行为一致
- **WHEN** 任一拆分后的子文件被 pytest 加载
- **THEN** import 行为、`sys.path`、`importorskip` 跳过策略与原文件完全一致

### Requirement: 共享 fixture 沉淀到 conftest.py
当一个测试模块拆分后多个子文件需要共享同一 fixture 时，SHALL 将该 fixture 沉淀到
该模块 `tests/conftest.py`，而非在每个子文件中复制。conftest.py 由 pytest 自动发现，
无需显式导入。

#### Scenario: gds_tools 共享 fixture
- **WHEN** `modules/gds_tools/tests/test_clip.py` / `test_density.py` / `test_loader.py` 运行
- **THEN** `klayout_db` / `test_gds` / `two_layer_gds` 三个 fixture 从 `conftest.py` 自动注入

### Requirement: 无 fall-back 无 TODO 残留
拆分过程中 SHALL：
- 不引入 `except: pass` / `return None` / `return []` 假数据（R03）
- 不引入 `TODO` / `FIXME` / `HACK` 注释（R05）
- 不丢失原 docstring 中的 R02 文献引用

### Requirement: 删除原始超长文件
拆分完成后 SHALL 删除 13 个原始超长文件，只保留拆分后的新文件（R13 §3 单一最新代码原则，
禁止多个版本并存）。

#### Scenario: 原文件已删除
- **WHEN** 列出 `modules/*/tests/` 目录
- **THEN** 不存在原始的 13 个超长文件（如 `test_gds_tools.py` / `test_verify_advanced.py` 等）

## MODIFIED Requirements
（无，本 spec 为测试文件质量收尾，不修改业务行为）

## REMOVED Requirements
（无）
