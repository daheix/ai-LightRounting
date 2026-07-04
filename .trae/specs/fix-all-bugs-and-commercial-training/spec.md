# 全Bug修复+训练积累+商用达标 Spec

## Why
测试发现3个P0级Bug（Switch组件超时、组合电路DRC全返回-1、GDS解析器缺失）和4个P1级问题（矩阵拓扑DRC 0%、gdsfactory连接缺失、expert_demos无连接、ALIGN格式不兼容）。36路标R36验收得分7.88未达9.20目标。训练模块已有框架但未独立持续训练到商用水平。需全面修复Bug、补齐功能短板、独立训练模型至商用标准。

## What Changes
- 修复Switch组件60s超时Bug（149+组合电路失败根因）
- 修复组合电路DRC违规数=-1问题（4251个成功电路DRC全失败）
- 恢复GDS解析器（229个SiEPIC真实用例无法测试）
- 修复矩阵拓扑DRC 0%（端口坐标推断不准）
- 修复gdsfactory连接缺失（Jinja模板+无连接解析）
- 修复expert_demos连接反推（routes.json→netlist）
- 训练模块独立化：提取为可独立运行的训练管道
- 持续训练到商用水平：用448真实用例+10000组合电路训练布局布线模型
- 36路标遗漏排查与补齐

## Impact
- Affected specs: commercial-drc-audit-and-real-cases, fix-all-bugs-root-cause-analysis, complete-remaining-roadmap-tasks
- Affected code: modules/place/, modules/drc/, modules/gds_tools/, modules/gdsio/, modules/trainer/, modules/nn/, modules/flow/, scripts/

## ADDED Requirements

### Requirement: Switch组件超时修复
系统 SHALL 在60秒内完成含Switch器件的电路端到端流程，超时即报明确错误而非静默失败。

#### Scenario: Switch电路正常完成
- **WHEN** 测试含Switch的组合电路
- **THEN** 60秒内完成布局→布线→仿真→DRC→GDS全流程

#### Scenario: 超时明确报错
- **WHEN** 某电路确实超时
- **THEN** 返回明确TimeoutError含电路名和卡死阶段，不返回error=None

### Requirement: 组合电路DRC正确执行
系统 SHALL 对组合电路正确执行DRC检查并返回真实违规数，不返回-1。

#### Scenario: DRC正确运行
- **WHEN** 对组合电路执行DRC
- **THEN** 返回≥0的违规数（0表示通过），不返回-1

### Requirement: GDS解析器恢复
系统 SHALL 能解析SiEPIC GDS文件提取器件和连接关系，覆盖229个真实用例。

#### Scenario: GDS解析成功
- **WHEN** 读取SiEPIC GDS文件
- **THEN** 提取器件列表+连接关系，转为CircuitSpec

### Requirement: 独立训练管道
系统 SHALL 提供独立可运行的训练脚本，用真实用例+组合电路持续训练布局布线模型。

#### Scenario: 训练独立运行
- **WHEN** 执行训练脚本
- **THEN** 加载训练数据→训练PPO/GNN模型→保存checkpoint→汇报指标

#### Scenario: 训练到商用水平
- **WHEN** 训练完成
- **THEN** 模型在测试集上DRC通过率≥60%、布局成功率≥90%

## MODIFIED Requirements

### Requirement: DRC端口坐标推断
布局器 SHALL 使用PDK端口坐标库替代默认均匀分布推断，提升DRC通过率。

### Requirement: 36路标补齐
R36验收得分7.88 SHALL 提升至≥8.5，补齐遗漏的功能短板。
