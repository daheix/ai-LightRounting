# Tasks

## 阶段1: P0 49个超80行函数拆分（并行，按模块分批）

- [ ] Task 1: 拆分inverse超长函数（run_adjoint_optimization 201L）
- [ ] Task 2: 拆分place超长函数（_align_d2_global 193L + _residual_pair_fix 154L）
- [ ] Task 3: 拆分求解器超长函数（eme/solve_eme 192L + bpm/solve_bpm 187L + fdfd/solve_fdfd 176L + eme/solve_slab_modes 146L）
- [ ] Task 4: 拆分route/gds_tools超长函数（route_circuit 179L + multi_clip_gdsii 150L + clip_gdsii 133L等6个）
- [ ] Task 5: 拆分yield超长函数（3个超80行）
- [ ] Task 6: 拆分其余模块超长函数（gui/orchestrator/sparam/multiphysics等）

## 阶段2: P0 真实用例下载扩充（并行）

- [ ] Task 7: 下载gdsfactory生态PDK（ubcpdk+cspdk+vtt+gdsfactory-test-data，~200个用例）
- [ ] Task 8: 下载Luxtelligence LNOI PDK + SiEPICfab Shuksan PDK（~60个用例）
- [ ] Task 9: 下载Apollo benchmark + Perceval量子光子（~28个用例）
- [ ] Task 10: 下载KLayout PCells + Quantum RF PDK（~20个用例）
- [ ] Task 11: 合并新数据到real_board/，更新index.json和README

## 阶段3: P0 DRC通过率提升（并行）

- [x] Task 12: 实现PORT_ALIGNMENT弯曲波导补偿
  - [x] SubTask 12.1: 在route模块添加bend_compensate函数（端口偏差>10μm时自动插入S弯曲）
  - [x] SubTask 12.2: 验证gdsfactory用例DRC通过率0%→30%+（实测 48/60=80%）
- [x] Task 13: 改进DENSITY_MIN自适应画布
  - [x] SubTask 13.1: 根据器件总面积动态调整画布尺寸
  - [x] SubTask 13.2: 验证lidar大电路DRC通过率（实测 2/9=22.2%，从 0% 提升）
- [x] Task 14: 改进矩阵型拓扑端口对齐
  - [x] SubTask 14.1: 为Clements/Reck矩阵添加专用端口对齐策略
  - [ ] SubTask 14.2: 验证矩阵拓扑DRC 0%→40%+（已实现_align_matrix_grid，待矩阵型数据集验证）

## 阶段4: P1 R36路标补齐（并行）

- [x] Task 15: 实现pretrain.py（BC预训练）
  - [x] SubTask 15.1: 创建modules/trainer/src/polaris_trainer/pretrain.py（460行，已自测：10 demos/35 samples/final_loss=1.2375）
  - [x] SubTask 15.2: 用expert_demos三元组做行为克隆预训练（MSE损失+Adam，文献Pomerleau 1989/Ross 2011）
- [x] Task 16: 实现transfer_learning.py（迁移学习）
  - [x] SubTask 16.1: 创建modules/trainer/src/polaris_trainer/transfer_learning.py（454行，已自测：4参数加载/2冻结/4可训练/final_loss=0.8835）
  - [x] SubTask 16.2: 支持加载预训练模型+微调（fc1冻结+fc2/routing_head微调，文献Yosinski 2014/Pan 2010）
- [x] Task 17: D12逆向设计showcase
  - [x] SubTask 17.1: 用adjoint优化3个标准器件（MMI分束器/WDM滤波器/Y分支）（JAX jax.grad，文献Piggott 2015/Hughes 2018）
  - [x] SubTask 17.2: FoM≥10%记录到docs（3/3器件改善≥10dB：MMI 16.59dB/WDM 10.06dB/Y分支 10.92dB，docs/inverse_design_showcase.md）

## 阶段5: P1 13个超800行测试套件拆分（并行）

- [ ] Task 18: 拆分verify_advanced/tests（1841L→3文件）
- [ ] Task 19: 拆分router_advanced/tests（1420L→3文件）
- [ ] Task 20: 拆分flow/tests + optimizer/tests + trainer/tests
- [ ] Task 21: 拆分其余测试套件（gui/gds_tools/circuit/yield/pdk_advanced/route/inverse/parasitic）

## 阶段6: 全量回归测试与验证

- [ ] Task 22: 全量回归测试（1000+真实用例+200组合电路）
- [ ] Task 23: 质量门禁验证（0超80行函数/0超800行文件/0 except:pass/0 TODO）
- [ ] Task 24: DRC通过率验证（真实用例≥30%）
- [ ] Task 25: 操作记录更新+代码提交

# Task Dependencies
- Task 1-6 可并行（6批函数拆分独立）
- Task 7-11 可并行（5批下载独立，Task 11依赖7-10完成）
- Task 12-14 可并行（3个DRC改进独立）
- Task 15-17 可并行（3个R36补齐独立）
- Task 18-21 可并行（4批测试拆分独立）
- Task 22 依赖Task 1-17完成
- Task 23-25 依赖Task 22完成
