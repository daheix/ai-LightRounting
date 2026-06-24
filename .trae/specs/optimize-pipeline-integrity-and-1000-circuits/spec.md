# 流程诚信审查与 1000 电路测试集优化 Spec

## Why

端到端业务流程已跑通（MVP 成功率 100%、DRC 通过率 100%），但流程中可能存在设计不合理、数据不真实、假数据造假等问题，影响学术诚信和商业对齐。同时，现有电路例子仅约 446 个（5 核心 demo + 71 benchmark + 10 expert + 360 variants），距离 1000 个目标尚有缺口，且场景复杂度不足，无法充分验证引擎在规模化、多样化电路上的鲁棒性。

## What Changes

### 方向一：流程诚信审查（找出并修复不合理设计、假数据、fall-back）
- 全量审查 `src/polaris/` 代码中的 fall-back / mock / fake / dummy / hardcode 数据
- 审查流程设计合理性：布局→布线→仿真→DRC→GDS 各环节是否有设计缺陷
- 审查物理参数真实性：所有固定参数是否来自公开 PDK / 论文，是否有编造
- 审查计算公式正确性：核心公式是否与原始文献一致
- 修复发现的所有问题（禁止 fall-back，失败必须 raise 告警）

### 方向二：电路例子扩展到 1000 个
- 基于已有 446 个电路，程序化生成 554+ 个新电路，总数达到 1000+
- 借鉴已有实际例子（SiEPIC EBeam PDK、gdsfactory、picbench、LiDAR benchmark）进行变种设计
- 借鉴网络公开例子（OpenROAD、Luceda IPKISS、Synopsys OptoDesigner 示例）进行变种设计
- 覆盖更多电路拓扑：MZI 阵列、Clements/Reck/Spanke 矩阵、Ring 滤波器组、WDM MUX/DEMUX、光开关矩阵、调制器阵列、量子光路等
- 覆盖更多规模梯度：4-500 器件，从简单到复杂
- 覆盖更多工艺平台：SOI / SiN / InP / LNOI

### 方向三：复杂场景测试
- 对 1000 个电路执行端到端流水线测试
- 统计成功率、DRC 通过率、平均损耗、平均耗时
- 识别失败电路并分析根因，修复引擎问题
- 生成测试报告和统计图表

## Impact
- Affected specs: audit-academic-integrity-deep（部分重叠，本 spec 范围更广）, build-e2e-demo-showcase
- Affected code:
  - `src/polaris/pipeline/integrated.py`（流程审查与修复）
  - `src/polaris/sim/`（仿真参数与公式审查）
  - `src/polaris/router/`（布线流程审查）
  - `src/polaris/engine/`（布局流程审查）
  - `src/polaris/data/specs.py`（电路规格定义）
  - `data/benchmarks/`（新增电路数据）
  - `scripts/`（电路生成与批量测试脚本）
  - `tests/`（新增测试用例）

## ADDED Requirements

### Requirement: 流程诚信审查
系统 SHALL 对 `src/polaris/` 全部代码进行诚信审查，识别并修复以下问题：
1. fall-back 设计（`except: pass`、`except: return None/[]`、静默跳过）
2. 假数据 / mock / fake / dummy / hardcode 值
3. 无来源的物理参数（未标注 PDK / 论文 URL）
4. 与原始文献不一致的计算公式
5. 流程设计缺陷（如布局算法产生重叠、布线算法产生不必要交叉）

#### Scenario: 发现 fall-back
- **WHEN** 代码中存在 `except: pass` 或静默返回假数据
- **THEN** 必须修改为 `raise` 或显式处理并记录日志，禁止静默兜底

#### Scenario: 参数无来源
- **WHEN** 物理参数未标注来源 PDK / 论文 URL
- **THEN** 必须补充来源注释，无法确认来源的参数必须标记为问题项

### Requirement: 1000 电路测试集
系统 SHALL 提供 1000+ 个电路例子，覆盖以下维度：
1. 电路拓扑：≥ 15 种（MZI、Ring、Clements、Reck、Spanke、MMI 阵列、DC 阵列、WDM、光开关、调制器、量子光路等）
2. 规模梯度：4-500 器件，至少 5 个规模档位
3. 工艺平台：SOI / SiN / InP / LNOI 至少 4 种
4. 来源多样性：基于 SiEPIC / gdsfactory / picbench / LiDAR / OpenROAD / IPKISS 变种

#### Scenario: 电路生成
- **WHEN** 运行电路生成脚本
- **THEN** 生成 1000+ 个合法 CircuitSpec JSON 文件，每个文件可被 `build_circuit_spec` 正确解析

#### Scenario: 批量测试
- **WHEN** 对 1000 个电路执行端到端流水线
- **THEN** 统计成功率、DRC 通过率、平均损耗、平均耗时，生成测试报告

### Requirement: 复杂场景测试报告
系统 SHALL 生成批量测试报告，包含：
1. 总体统计：成功率、DRC 通过率、平均损耗、平均耗时
2. 分拓扑统计：每种电路拓扑的测试结果
3. 分规模统计：每个规模档位的测试结果
4. 失败分析：失败电路的根因分类与修复建议

## MODIFIED Requirements

### Requirement: 端到端流水线
端到端流水线 SHALL 在 1000+ 个电路上稳定运行，成功率 ≥ 95%，DRC 通过率 ≥ 90%。

## REMOVED Requirements

### Requirement: 静默 fall-back
**Reason**: 违反规则 14.1（无 fall-back 设计），所有 fall-back 必须移除
**Migration**: 失败时 `raise` 告警，由调用方处理
