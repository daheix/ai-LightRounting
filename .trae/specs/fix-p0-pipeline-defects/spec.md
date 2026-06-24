# P0 级流水线缺陷修复 Spec

## Why

流程设计缺陷审查（Task 4）发现 3 个 P0 级缺陷，阻碍端到端流水线在大规模电路（500 器件）上可用：
1. 布局算法在大器件小画布场景产生器件重叠
2. 顺序布线障碍物累积导致大规模电路拥塞死锁
3. 5 项 DRC 规则（THERMAL/CROSSTALK/ENCLOSURE/NOTCH/PIN_MATCH）未实现或未调用

修复这 3 个 P0 缺陷是后续 1000 电路批量测试的前置条件——在坏流程上扩展电路无意义。

## What Changes

### P0-1: 修复 `_DefaultPlacer._place_random` 布局重叠
- 重写 `_place_random` 方法，增加重叠检测 + 合法化（推开重叠器件）+ 画布扩大重试（3 次，每次 ×1.5）
- 新增辅助函数：`_grid_place`、`_rects_overlap`、`_has_overlap`、`_legalize_overlaps`、`_find_nearest_free`
- 来源: DREAMPlace 合法化算法（TCAD 2020 §III.C）https://arxiv.org/abs/1904.03522

### P0-2: 修复 `_CurvyRouter.route` 顺序布线拥塞死锁
- 实现 rip-up and reroute 算法（最多 3 次迭代），来源: Lillis & Dutt, DAC 1999
- 优化障碍物半宽：grid_size*0.6 → waveguide_width/2 + min_spacing_um = 1.25μm
- 复用同一个 GridRouter 实例，降低 O(n²) 复杂度
- 将 `_CurvyRouter` 拆分到独立文件 `polaris.pipeline.curvy_router`（规则 7.1：文件 < 600 行）
- 将 `_DefaultSimulator` 拆分到 `polaris.pipeline.default_simulator`

### P0-3: 修复 5 项 DRC 规则缺失
- 在 `CheckContext` 添加 `canvas_w`、`canvas_h`、`pin_pairs` 字段
- 实现 `check_enclosure`（IHP SG25H5 PDK enclosure 规则）
- 实现 `check_notch`（KLayout DRC runset notch 规则，简化版）
- 实现 `check_pin_match`（SiEPIC EBeam PDK 端口方向约定）
- 在 `ConstraintChecker.check()` 调用全部 16 项 ViolationType 检查
- **修改 `SimLoop._check_constraints` 填充 CheckContext 缺失字段**（waveguide_widths/waveguide_lengths/device_areas/port_connections/canvas_w/canvas_h/pin_pairs）

## Impact
- Affected specs: optimize-pipeline-integrity-and-1000-circuits（Task 4 审查 → 本 spec 修复 → Task 12 引擎修复的前置）
- Affected code:
  - `src/polaris/pipeline/integrated.py`（P0-1 重写 _place_random + 拆分）
  - `src/polaris/pipeline/curvy_router.py`（P0-2 新建，rip-up and reroute）
  - `src/polaris/pipeline/default_simulator.py`（拆分 _DefaultSimulator）
  - `src/polaris/sim/constraint_types.py`（P0-3 CheckContext 扩展）
  - `src/polaris/sim/constraint_checks_geometry.py`（P0-3 新增 3 项检查函数）
  - `src/polaris/sim/constraint_checker.py`（P0-3 调用全部 16 项检查）
  - `src/polaris/sim/sim_loop.py`（P0-3 填充 CheckContext 字段）

## ADDED Requirements

### Requirement: 布局无重叠保证
系统 SHALL 保证 `_DefaultPlacer._place_random` 产生的布局无器件重叠，在大器件小画布场景下通过合法化 + 画布扩大重试消除重叠。

#### Scenario: 大器件小画布
- **WHEN** 器件尺寸超过网格单元尺寸
- **THEN** 合法化算法将重叠器件推开到最近空闲位置；若画布空间不足则扩大画布 ×1.5 重试，最多 3 次

### Requirement: 布线无拥塞死锁
系统 SHALL 通过 rip-up and reroute 算法避免顺序布线在大规模电路上的拥塞死锁，复用同一 GridRouter 实例降低复杂度。

#### Scenario: 大规模电路布线
- **WHEN** 顺序布线后存在未布线连接
- **THEN** 对每个未布线连接执行 rip-up（移除冲突路径）+ reroute（重新布线），最多 3 次迭代

### Requirement: DRC 16 项规则全覆盖
系统 SHALL 调用全部 16 项 ViolationType 检查函数，无静默跳过。`SimLoop._check_constraints` SHALL 填充 CheckContext 的所有可用字段。

#### Scenario: DRC 检查完整性
- **WHEN** 执行约束检查
- **THEN** THERMAL/CROSSTALK/ENCLOSURE/NOTCH/PIN_MATCH 等 5 项此前缺失的检查全部被调用，CheckContext 的 waveguide_widths/waveguide_lengths/device_areas/port_connections/canvas_w/canvas_h/pin_pairs 字段被正确填充

## MODIFIED Requirements

### Requirement: 端到端流水线
端到端流水线 SHALL 在大规模电路（500 器件）上稳定运行，MVP 5 次迭代成功率 >= 80%。

## REMOVED Requirements

### Requirement: 静默 fall-back 布线跳过
**Reason**: 违反规则 14.1（无 fall-back 设计）
**Migration**: 未布线连接收集后记录 warning 日志明确列出失败连接
