# 深度优化+真实用例扩充+1000子任务 Spec

## Why
全模块深度优化后发现3个核心问题：1) 49个超80行函数未拆分（AGENTS.md §8违规）；2) 真实用例DRC通过率仅3.6%（数据集以单器件/演示文件为主+布局算法端口对齐不足）；3) real_board仅448个用例，需扩充到1000+。需全面拆分超长函数、改进DRC通过率、下载新真实用例。

## What Changes
- 拆分49个超80行函数（inverse/run_adjoint_optimization 201L, place/_align_d2_global 193L等）
- 拆分13个超800行测试套件文件
- 改进DRC通过率：PORT_ALIGNMENT弯曲波导补偿、DENSITY_MIN自适应画布
- 改进布局算法矩阵型拓扑端口对齐
- 下载10个新数据源（ubcpdk/cspdk/vtt/Luxtelligence/SiEPICfab Shuksan/gdsfactory-test-data/Apollo/Perceval/KLayout PCells/Quantum RF PDK）
- 补齐R36路标：pretrain.py + transfer_learning.py + D12逆向设计showcase
- 1000个子任务分类执行

## Impact
- Affected specs: comprehensive-module-optimization, fix-all-bugs-and-commercial-training
- Affected code: 全部36模块 + real_board/ + scripts/

## ADDED Requirements

### Requirement: 49个超80行函数全部拆分
全部业务代码src/下函数 SHALL ≤80行，超标函数全部拆分为子函数。

### Requirement: 真实用例DRC通过率提升
真实用例DRC通过率 SHALL 从3.6%提升到≥30%（通过弯曲波导补偿+端口对齐改进+补充多器件用例）。

### Requirement: 真实用例扩充到1000+
real_board/ SHALL 从448个扩充到1000+个真实用例，覆盖SOI/SiN/InP/LNOI多平台。

### Requirement: R36路标核心交付物补齐
pretrain.py和transfer_learning.py SHALL 实现并可用，D07 AI/ML得分7→9+。
