# 商用版 DRC 误报审查与真实测试用例扩展 Spec

## Why

上一轮 1200 电路端到端测试发现：流水线成功率 100%，但 DRC 通过率仅 48%（576/1200）。6 种矩阵型拓扑（clements/reck/spanke/mmi_array/dc_array/polarization_array）共 480 个电路 DRC 全部失败，根因集中在 PORT_ALIGNMENT 规则（5μm 容差）对矩阵拓扑布局端口的误报。同时，现有 1200 个测试用例全部为程序化生成，真实开源用例仅约 80 个（SiEPIC GDS 10 + gdsfactory JSON 40 + picbench JSON 18 + LiDAR JSON 9），无法充分验证商用版本对真实电路的鲁棒性。商用发布要求所有问题必须优化完成，DRC 不得误报。

## What Changes

### 方向一：DRC 误报审查与修复
- 审查 12 条 DRC 规则对 1200 电路的误报情况（PORT_ALIGNMENT/PORT_FACING/DENSITY_MAX 等）
- 区分「真违规」与「规则过严/算法局限导致的误报」
- 修复布局算法使矩阵型拓扑端口对齐（提升 DRC 通过率至 ≥90%）
- 或调整 DRC 规则阈值至工艺合理区间（需文献支撑，非放宽放水）
- 输出 DRC 误报审查报告

### 方向二：网络真实测试用例扩展
- 从开源仓库下载真实电路用例（目标新增 ≥200 个真实用例）：
  - SiEPIC EBeam PDK 完整示例集（https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
  - gdsfactory 样例库（https://github.com/gdsfactory/gdsfactory）
  - picbench 基准全集（https://github.com/TiagoCavaco/picbench）
  - OpenROAD EPIC 基准（https://github.com/ALIGN-analoglayout/ALIGN）
  - Luceda IPKISS 公开示例
  - Synopsys OptoDesigner 公开教程示例
- 将真实用例转换为 PoLaRIS CircuitSpec 格式
- 真实用例 + 程序化用例总数 ≥ 1000（保持 1200+）

### 方向三：商用优化收尾
- 全量回归测试（真实用例 + 程序化用例）
- 成功率 ≥ 95%、DRC 通过率 ≥ 90%（商用门槛）
- 性能优化：大规模电路（XL）端到端耗时 ≤ 5s
- 生成商用版最终测试报告

## Impact
- Affected specs: optimize-pipeline-integrity-and-1000-circuits（前置，已完成的迭代基础）, audit-academic-integrity-deep
- Affected code:
  - `modules/place/src/polaris_place/`（布局算法改进，矩阵拓扑端口对齐）
  - `modules/drc/src/polaris_drc/engine.py`（DRC 规则阈值审查，误报修复）
  - `scripts/download_real_circuits.py`（新增：网络真实用例下载器）
  - `scripts/convert_real_to_polaris.py`（新增：真实用例格式转换器）
  - `scripts/batch_test_1000_circuits.py`（扩展：支持真实用例集）
  - `data/benchmarks/real/`（新增：真实用例存储目录）

## ADDED Requirements

### Requirement: DRC 误报审查
系统 SHALL 对 12 条 DRC 规则进行误报审查，区分真违规与误报：
1. 对 1200 电路的全部 DRC 违规分类（真违规 / 规则过严 / 算法局限 / 规则正确）
2. PORT_ALIGNMENT 规则对矩阵拓扑的误报根因分析
3. 修复布局算法或调整规则阈值（需文献支撑）
4. 误报率 ≤ 5%（商用门槛）

#### Scenario: PORT_ALIGNMENT 误报
- **WHEN** 矩阵型拓扑（clements/reck/spanke）布局后端口 dy > 5μm
- **AND** 布局算法无法对齐矩阵拓扑端口（算法局限非真违规）
- **THEN** 改进布局算法使端口对齐，或调整容差至工艺合理值（需文献）
- **AND** 修复后该拓扑 DRC 通过率 ≥ 90%

#### Scenario: 真违规识别
- **WHEN** 电路存在真实重叠/间距不足/方向非法
- **THEN** DRC 正确报告违规，不放宽规则
- **AND** 引擎修复使真违规数量下降

### Requirement: 网络真实用例下载与转换
系统 SHALL 提供从开源仓库下载真实电路用例的能力：
1. 支持 SiEPIC/gdsfactory/picbench/OpenROAD 等公开仓库
2. 下载 GDS/netlist/JSON 格式真实电路
3. 转换为 PoLaRIS CircuitSpec 格式
4. 真实用例总数 ≥ 200 个（新增）

#### Scenario: 真实用例下载
- **WHEN** 运行下载脚本
- **THEN** 从公开仓库下载 ≥ 200 个真实电路到 `data/benchmarks/real/`
- **AND** 每个用例可被转换为合法 CircuitSpec

#### Scenario: 真实用例转换
- **WHEN** 对下载的真实用例执行格式转换
- **THEN** 输出 PoLaRIS CircuitSpec JSON，可被 `build_circuit_spec` 解析
- **AND** 保留原始用例的拓扑结构（非程序化变种）

### Requirement: 商用版最终回归
系统 SHALL 在真实用例 + 程序化用例（≥1000 总数）上完成商用回归：
1. 端到端成功率 ≥ 95%
2. DRC 通过率 ≥ 90%
3. 大规模电路（XL）端到端耗时 ≤ 5s
4. 生成商用版最终测试报告

#### Scenario: 商用回归通过
- **WHEN** 对全部用例执行端到端测试
- **THEN** 成功率 ≥ 95% 且 DRC 通过率 ≥ 90%
- **AND** 生成 `docs/商用版最终测试报告.md`

## MODIFIED Requirements

### Requirement: 端到端流水线（商用版）
端到端流水线 SHALL 在 ≥1000 个电路（含 ≥200 真实用例）上稳定运行，成功率 ≥ 95%，DRC 通过率 ≥ 90%，XL 规模耗时 ≤ 5s。

## REMOVED Requirements

### Requirement: DRC 规则静默放宽
**Reason**: 禁止为提升通过率而静默放宽 DRC 规则阈值（违反 R03/R02）
**Migration**: 规则阈值调整必须有公开 PDK/论文来源支撑，并在代码 docstring 标注
