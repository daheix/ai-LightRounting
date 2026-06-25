# 全流程打通 Spec

## Why
端到端全流程（Web UI → 布局布线 → 仿真 → DRC → GDS → Showcase）存在 2 个阻断点：
1. `test_e2e_showcase.py` 因 `import torch` 硬依赖失败（环境无 torch）
2. `test_tilos_benchmark.py` 因 `grid_placement` 产生 11 个边界违规（DRV≠0）导致 `passed=False`

## What Changes
- 修复 `grid_placement`：当画布太小无法容纳所有模块时，自适应扩大画布，确保零边界违规
- 修复 `stage3_ai_placement.py`：torch 改为可选依赖，无 torch 时使用纯 numpy PPO 后端
- 修复 `test_evaluate_benchmark_passed_no_overlap`：测试逻辑对齐 `evaluate_benchmark` 的 `passed` 判定（HPWL < target AND DRV=0）

## Impact
- Affected code: `src/polaris/data/benchmark_evaluator.py`, `examples/e2e_showcase/stages/stage3_ai_placement.py`, `tests/test_tilos_benchmark.py`
- Affected specs: `build-e2e-demo-showcase`, `build-polaris-optical-pnr`

## ADDED Requirements
### Requirement: grid_placement 零边界违规
The system SHALL ensure `grid_placement` produces zero boundary violations for any circuit.

#### Scenario: 大模块小画布
- **WHEN** circuit 含 220×170μm 模块，画布 556×556μm，17 个模块
- **THEN** grid_placement 自适应扩大画布，所有模块在画布内，DRV boundary=0

### Requirement: stage3 torch 可选依赖
The system SHALL allow `stage3_ai_placement.py` to run without torch installed.

#### Scenario: 无 torch 环境
- **WHEN** torch 未安装
- **THEN** stage3 使用纯 numpy PPO 后端，不报 ImportError
