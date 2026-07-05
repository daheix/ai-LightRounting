# 光电子单位统一+深度优化+1000子任务 Spec

## Why
发现严重的单位不一致bug：pretrain.py/transfer_learning.py默认canvas_w=1.0（归一化），但specs.py默认1000.0μm，单位差1000倍导致训练特征失效。rl_pareto.py用width/height默认50/30μm但specs.py用width_um默认10μm，差5倍。波长nm/μm混用差1000倍。这些单位bug导致训练模型无法学到正确特征，必须立即修复。

## What Changes
- 修复pretrain.py canvas_w默认1.0→1000.0，归一化1e5→1000.0
- 修复transfer_learning.py同上
- 修复rl_pareto.py/rl_advanced.py width→width_um，默认50/30→raise KeyError
- 修复_CANVAS_SIZE_UM=3200→动态读取circuit canvas_w
- 统一波长换算：调用simphony前nm→μm
- 继续拆分42个超80行函数（split-long-functions-80-lines spec已创建）
- 继续下载更多真实用例
- 1000个子任务深度优化

## Impact
- Affected specs: deep-optimization-and-real-cases-expansion, split-long-functions-80-lines
- Affected code: trainer/pretrain.py, transfer_learning.py, rl_pareto.py, rl_advanced.py, core/specs.py

## ADDED Requirements

### Requirement: 光电子单位统一
全部模块 SHALL 使用统一单位制：尺寸μm、波长nm（对外接口）、画布μm、损耗dB、延迟ps。训练环境归一化常数与specs.py一致（1000.0μm）。

#### Scenario: 训练环境单位正确
- **WHEN** pretrain.py加载netlist
- **THEN** canvas_w默认1000.0μm（非1.0），归一化用/1000.0（非/1e5）

#### Scenario: RL奖励单位正确
- **WHEN** rl_pareto.py读取器件尺寸
- **THEN** 读取width_um字段（非width），缺失raise KeyError（不默认50μm）

### Requirement: 波长换算统一
调用simphony仿真器前 SHALL 显式换算 wl_um = optical_wavelength_nm / 1000.0。

### Requirement: 42个超80行函数拆分
全部业务代码src/下函数 SHALL ≤80行。

### Requirement: 真实用例持续扩充
real_board/ SHALL 持续下载新数据源，目标5000+用例。
