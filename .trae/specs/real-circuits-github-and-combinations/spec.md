# 真实用例上传GitHub与组合扩展测试 Spec

## Why

用户提出三项新需求：
1. **真实用例必须上传到 GitHub**：现有 327 个新下载用例 + 90 个之前真实板子数据共 417 个真实用例分散在 `data/benchmarks/` 多个子目录，未统一上传到 GitHub 仓库的原始数据目录，无法溯源与共享。
2. **真实板子数据必须测试并汇报**：417 个真实用例尚未端到端测试，无法验证商用版本对真实电路的鲁棒性。
3. **基于真实板子组合模拟更多测试电路**：真实板子的拓扑组合（MZI×Ring、Clements×WDM、Switch×Modulator 等）可程序化生成海量组合测试电路，覆盖真实场景的长尾分布，远比纯程序化生成更贴近商用。

## What Changes

### 方向一：统一真实用例目录并上传 GitHub
- 在仓库内建立 `data/real_circuits/` 统一目录（按来源分子目录：siepic/gdsfactory/picbench/lidar/align/expert_demos）
- 合并现有 417 个真实用例到统一目录
- 生成统一索引 `data/real_circuits/index.json`（含 name/source/format/path/origin_url/license）
- 提交到 git main 分支并推送 GitHub（PoLaRIS 仓库本身即 GitHub 仓库）

### 方向二：真实板子数据端到端测试与汇报
- 对全部真实用例执行端到端流水线测试（布局→布线→仿真→DRC→GDS）
- 真实用例需先转换为 PoLaRIS CircuitSpec 格式（GDS 用 klayout 解析，netlist JSON 直接解析）
- 汇报真实板子的成功率、DRC 通过率、平均损耗、平均耗时
- 与程序化用例对比，验证商用版本对真实电路的鲁棒性

### 方向三：基于真实板子组合模拟扩展测试电路
- 识别真实板子的拓扑组件（MZI、Ring、DC、MMI、Switch、Modulator、WDM 等）
- 实现组合生成器：从真实板子提取组件，程序化组合成新电路
  - 二元组合：MZI+Ring、Clements+WDM、Switch+Modulator 等
  - 多元组合：3-5 种拓扑组件混合
  - 规模扩展：单组件 ×N（N=2,4,8,16）阵列化
- 目标生成 ≥500 个组合测试电路
- 全量测试并汇报

## Impact
- Affected specs: commercial-drc-audit-and-real-cases（前置，DRC 修复已完成）
- Affected code:
  - `data/real_circuits/`（新增：统一真实用例目录）
  - `scripts/consolidate_real_circuits.py`（新增：合并真实用例到统一目录）
  - `scripts/convert_real_to_polaris.py`（扩展：GDS/netlist → CircuitSpec）
  - `scripts/test_real_circuits.py`（新增：真实用例端到端测试）
  - `scripts/generate_combination_circuits.py`（新增：基于真实板子组合生成）
  - `scripts/test_combination_circuits.py`（新增：组合电路测试）

## ADDED Requirements

### Requirement: 真实用例统一目录与 GitHub 上传
系统 SHALL 将所有真实用例统一到 `data/real_circuits/` 目录并提交到 GitHub：
1. 合并 417 个真实用例（siepic_examples/gf_*/picbench_*/lidar_*/real/expert_demos）
2. 按来源分子目录：siepic/gdsfactory/picbench/lidar/align/expert_demos
3. 统一索引 `data/real_circuits/index.json`，每条含 name/source/format/path/origin_url/license
4. 提交 git main 分支并 push origin main

#### Scenario: 真实用例统一
- **WHEN** 运行合并脚本
- **THEN** 417 个真实用例移至 `data/real_circuits/{source}/`
- **AND** 生成统一 index.json，可溯源每个用例的 GitHub origin URL

#### Scenario: GitHub 上传
- **WHEN** git add + commit + push origin main
- **THEN** 真实用例在 GitHub 仓库可见
- **AND** 仓库体积不超过 GitHub 单文件 100MB 限制

### Requirement: 真实板子端到端测试汇报
系统 SHALL 对全部真实用例执行端到端测试并汇报：
1. 真实用例转换为 CircuitSpec（GDS 用 klayout，netlist 直接解析）
2. 端到端流水线测试（布局→布线→仿真→DRC→GDS）
3. 汇报成功率、DRC 通过率、平均损耗、平均耗时
4. 与程序化用例对比

#### Scenario: 真实板子测试
- **WHEN** 对真实用例执行端到端测试
- **THEN** 汇报成功率、DRC 通过率、平均损耗、平均耗时
- **AND** 与程序化 1200 电路结果对比

### Requirement: 基于真实板子组合模拟扩展
系统 SHALL 基于真实板子拓扑组件组合生成 ≥500 个测试电路：
1. 从真实板子提取拓扑组件（MZI/Ring/DC/MMI/Switch/Modulator/WDM）
2. 二元组合（A+B）与多元组合（A+B+C+D）
3. 规模扩展（单组件 ×N 阵列化，N=2/4/8/16）
4. 全量测试并汇报

#### Scenario: 组合电路生成
- **WHEN** 运行组合生成器
- **THEN** 生成 ≥500 个组合电路到 `data/benchmarks/combinations/`
- **AND** 每个组合电路保留组件溯源（来自哪些真实板子）

#### Scenario: 组合电路测试
- **WHEN** 对组合电路执行端到端测试
- **THEN** 汇报成功率、DRC 通过率
- **AND** 识别失败组合并分析根因

## MODIFIED Requirements

### Requirement: 商用版测试集（含真实+组合+程序化）
商用版测试集 SHALL 包含：
- 真实用例 ≥400 个（已下载 417）
- 组合电路 ≥500 个（基于真实板子组合）
- 程序化电路 1200 个（已有）
- 总数 ≥2100 个

## REMOVED Requirements

### Requirement: 真实用例分散存储
**Reason**: 分散在 data/benchmarks/ 多个子目录无法统一溯源
**Migration**: 统一到 data/real_circuits/，保留原目录为符号链接或迁移记录
