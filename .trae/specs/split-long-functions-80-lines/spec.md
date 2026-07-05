# 拆分超 80 行函数至 ≤80 行 Spec

## Why
PoLaRIS 项目 R11 质量门禁要求"函数 ≤80 行"，但 AST 扫描显示 `modules/*/src/`
仍有 **42 个函数超 80 行**（最长 259L `bend_compensate`，TOP 10 均 >125L）。这些函数
职责混杂、可读性差、难以单测，违反 R11 门禁、阻碍后续维护与商业对齐。本 spec 系统
拆分全部 42 个超长函数为多个 ≤80 行子函数（保持函数签名不变，子函数用 `_` 前缀）。

上一轮 `comprehensive-module-optimization` 已部分拆分（5 个 TOP 文件已完成：
inverse/adjoint.py、place/align.py、eme/solver.py、bpm/solver.py、route/__init__.py
的 route_circuit），但 AST 复扫发现仍有 42 个违规，需继续拆分直至 AST 扫描结果为 0。

## What Changes
- 拆分 42 个超 80 行函数为多个 ≤80 行子函数（共涉及 14 个子模块）
- 保持所有外部公共函数签名不变（向后兼容，不破坏调用方）
- 子函数统一用 `_` 前缀（表示内部使用，非公共 API）
- 拆分模式（按函数类型）：
  - **求解器函数**（solve_fdfd / simulate_*_fdtd）：按"参数校验 / 构建上下文 / 主循环 / 后处理"拆分
  - **布局函数**（_residual_pair_fix / _legalize / _try_*_move）：按"阶段 / 候选评估 / 结果选择"拆分
  - **布线函数**（bend_compensate）：按"参数校验 / 构建映射 / 拓扑处理循环 / 路径重生成"拆分
  - **GDS 工具函数**（clip_gdsii / multi_clip_gdsii / flatten_gdsii / scale_gdsii /
    transform_gdsii_geometry / extract_text_labels / compute_density_* /
    check_density_rules / check_area）：按"参数校验 / 核心逻辑 / 结果组装"拆分
  - **优化函数**（cross_entropy_importance_sampling / optimize_yield_via_nominal_shift）：
    按"初始化 / 主循环 / 收敛 / 后处理"拆分
  - **编排函数**（run_eda_flow / batch_simulate / cascade_circuit）：按"参数校验 / 阶段调度 / 结果汇总"拆分
  - **训练函数**（transfer_learn / pretrain / train_step / collect_rollout）：
    按"初始化 / 训练循环 / 检查点 / 收敛"拆分
  - **NN op 函数**（_multi_head_attention_op）：按"输入投影 / 注意力计算 / 输出投影"拆分
  - **验证函数**（validate_circuit / stage6_drc_lvs）：按"结构校验 / 语义校验 / 报告"拆分
  - **导入导出函数**（export_gds / import_gds / export_klayout_script / serialize_pdk_yaml）：
    按"参数校验 / 数据转换 / 序列化 / 写文件"拆分
- 每拆分完一个模块立即 `git add <精确文件> → commit → push origin main`（R11）
- 拆分后用 Python AST 重新扫描全部 `modules/*/src/` 目录，**超 80 行函数 = 0**
- 拆分后所有现有测试通过（无回归）

## Impact
- Affected specs:
  - `comprehensive-module-optimization`（上一轮已部分完成，本轮为遗留 42 个的彻底收尾）
  - `audit-academic-integrity-deep`（拆分不得改变物理公式/参数溯源，R02 不变）
- Affected code（14 个子模块，42 个函数）：
  - `modules/route/src/polaris_route/__init__.py`（bend_compensate 259L）
  - `modules/fdfd/src/polaris_fdfd/solver.py`（solve_fdfd 176L, build_helmholtz_operator 83L）
  - `modules/place/src/polaris_place/`（residual.py ×3, legalize.py ×2, metrics.py ×1）
  - `modules/gds_tools/src/polaris_gds_tools/`（gdsii_clip_tool.py ×2, gdsii_density_analyzer.py ×3,
    gdsii_text_label_extractor.py ×1, gdsii_drc_area.py ×1, gdsii_flattener.py ×1,
    gdsii_geometry_transformer.py ×1, gdsii_layout_scaler.py ×1）
  - `modules/trainer/src/polaris_trainer/`（transfer_learning.py, pretrain.py）
  - `modules/orchestrator/src/polaris_orchestrator/flow.py`
  - `modules/yield/src/polaris_yield/`（4 文件 5 函数）
  - `modules/fdtd/src/polaris_fdtd/`（waveguide.py, mmi.py）
  - `modules/quantum_advanced/src/polaris_quantum_advanced/rollout.py`
  - `modules/nn/src/polaris_nn/nn/attention.py`
  - `modules/multiphysics/src/polaris_multiphysics/tcad_thermal/solver.py`
  - `modules/core/src/polaris_core/__init__.py`
  - `modules/pdk_advanced/src/polaris_pdk_advanced/yaml_config.py`
  - `modules/gui/src/polaris_gui/layout_editor.py`
  - `modules/sparam/src/polaris_sparam/models.py`
  - `modules/gdsio/src/polaris_gdsio/`（exporter.py, importer.py）
  - `modules/flow/src/polaris_flow/`（inverse_design.py, stage_verification.py）
  - `modules/circuit/src/polaris_circuit/cascade.py`

## ADDED Requirements

### Requirement: 所有函数 ≤80 行
PoLaRIS 全部 `modules/*/src/**/*.py` 文件中的所有函数（含公共 API 与私有 `_` 前缀函数）
SHALL 满足 `end_lineno - lineno + 1 <= 80`。

#### Scenario: AST 扫描通过
- **WHEN** 运行 `python -c "import ast, os; ..."` 扫描全部 `modules/*/src/`
- **THEN** 输出 `total violations: 0`

### Requirement: 公共 API 向后兼容
拆分 SHALL 保持所有现有公共函数（无 `_` 前缀）的签名、返回值、异常类型完全不变。

#### Scenario: 调用方不受影响
- **WHEN** 任意外部代码调用 `route_circuit(circuit, placements)` / `solve_fdfd(...)` 等
- **THEN** 返回值结构、字段名、单位、类型与拆分前完全一致

### Requirement: 子函数用 _ 前缀
拆分产生的内部辅助函数 SHALL 以 `_` 前缀命名（如 `_validate_fdfd_params`、
`_build_fdfd_grid`、`_run_fdfd_iter`），表示模块内部使用，不导出至 `__all__`。

### Requirement: 无 fall-back 无 TODO 残留
拆分过程中 SHALL：
- 不引入 `except: pass` / `return None` / `return []` 假数据（R03）
- 不引入 `TODO` / `FIXME` / `HACK` 注释（R05）
- 物理公式与参数溯源注释保持原样，不丢失 R02 文献引用

### Requirement: 测试无回归
拆分 SHALL 保持所有现有测试通过。每个模块拆分后运行该模块的 pytest：
- `modules/<m>/tests/` 全部通过
- 关键数值结果（如 `solve_eme` 单段 T_dB、`solve_bpm` T_dB、`solve_slab_modes` neff）
  与拆分前一致至小数点后 4 位

## MODIFIED Requirements
（无，本 spec 为代码质量收尾，不修改业务行为）

## REMOVED Requirements
（无）
