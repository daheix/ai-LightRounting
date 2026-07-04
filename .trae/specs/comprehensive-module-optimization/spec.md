# 全模块深度优化+真实用例100%准确率 Spec

## Why
真实用例测试93.1%成功率（排除ALIGN后），6个pipeline_failed是拓扑排序算法bug（Kahn算法把无向光子连接当有向边，遇环raise），19个是gdsfactory演示文件（无连接，非bug但需分类）。36模块扫描发现5处except:pass、75处return None、37处return []、23处TODO/FIXME、6个文件超800行、43个函数超80行、12个圈复杂度超15。需全面修复使真实用例达100%准确率，并优化所有模块质量。

## What Changes
- 修复6个pipeline_failed：用Tarjan SCC算法替代Kahn拓扑排序处理含环光子电路
- 分类19个gdsfactory演示文件：标记non_circuit_demo不计入失败率
- 清理5处except:pass + 75处return None + 37处return []（R03违规）
- 清理23处TODO/FIXME/HACK（R05违规）
- 拆分6个超800行文件（place/analytical.py 1480L, drc/engine.py 803L, gui/interactive.py 824L, gui/web_server.py 823L, pdk/catalog.py 936L, quantum_advanced/distributed_ppo.py 808L）
- 拆分43个超80行函数
- 降低12个圈复杂度>15函数
- 补充测试覆盖率不足的模块（multiphysics/nn/gds_tools等）

## Impact
- Affected specs: fix-all-bugs-and-commercial-training, commercial-drc-audit-and-real-cases
- Affected code: 全部36个模块 + scripts/test_real_circuits.py

## ADDED Requirements

### Requirement: 光子电路环拓扑支持
系统 SHALL 用Tarjan SCC+Condensation DAG替代Kahn算法，正确处理含反馈环的光子电路（MZI/Ring/Crossings）布局。

#### Scenario: MZI电路布局成功
- **WHEN** 输入含反馈环的MZI电路（如siepic MZI1.gds，3器件6连接）
- **THEN** 布局成功完成，不raise RuntimeError

#### Scenario: Crossings电路布局成功
- **WHEN** 输入含5端口Crossing的电路（如siepic Crossings.gds，5器件7连接）
- **THEN** 布局成功完成

### Requirement: gdsfactory演示文件分类
系统 SHALL 将无connections/routes/nets的gdsfactory演示文件标记为non_circuit_demo，不计入失败率。

#### Scenario: 演示文件正确分类
- **WHEN** 加载gdsfactory mirror_demo.pic.yml（0连接）
- **THEN** 标记为non_circuit_demo，不报spec_build_failed

### Requirement: R03零fall-back
全部36个模块 SHALL 零except:pass、零return None假数据、零return []假数据。

### Requirement: R05零TODO残留
全部36个模块 SHALL 零TODO/FIXME/HACK残留。

### Requirement: R11质量门禁达标
全部36个模块 SHALL 函数≤80行、文件≤800行、圈复杂度≤15。
