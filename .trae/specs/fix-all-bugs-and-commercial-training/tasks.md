# Tasks

## 阶段1: P0 Bug修复（并行）

- [x] Task 1: 修复Switch组件超时Bug
  - [x] SubTask 1.1: 定位Switch器件在布局/布线哪个阶段卡死（读取test_10000日志+复现单电路）
  - [x] SubTask 1.2: 修复卡死根因（可能是Switch端口数过多导致A*路径搜索指数爆炸）
  - [x] SubTask 1.3: 超时返回明确错误（error不为None，含电路名+卡死阶段）
  - [x] SubTask 1.4: 回归测试：10个含Switch电路60秒内完成

- [ ] Task 2: 修复组合电路DRC违规数=-1
  - [ ] SubTask 2.1: 定位DRC引擎返回-1的代码路径（读取drc engine源码）
  - [ ] SubTask 2.2: 修复-1根因（GDS层映射缺失或DRC规则未匹配）
  - [ ] SubTask 2.3: 回归测试：100个组合电路DRC返回≥0的违规数

- [ ] Task 3: 恢复GDS解析器
  - [ ] SubTask 3.1: 用klayout.db读取SiEPIC GDS文件提取器件+连接
  - [ ] SubTask 3.2: GDS器件→CircuitSpec转换（器件类型/端口/位置）
  - [ ] SubTask 3.3: 回归测试：10个SiEPIC GDS文件解析成功

## 阶段2: P1 Bug修复（并行）

- [ ] Task 4: 修复矩阵拓扑DRC端口对齐
  - [ ] SubTask 4.1: 从PDK catalog获取真实端口坐标替代默认推断
  - [ ] SubTask 4.2: 回归测试：6种矩阵拓扑DRC通过率≥40%

- [ ] Task 5: 修复gdsfactory Jinja模板解析
  - [ ] SubTask 5.1: 实现Jinja-aware netlist parser（渲染%语法后解析YAML）
  - [ ] SubTask 5.2: 回归测试：9个Jinja yml文件解析成功

- [ ] Task 6: 修复expert_demos连接反推
  - [ ] SubTask 6.1: 从routes.json路径点列表反推器件连接关系
  - [ ] SubTask 6.2: 回归测试：10个expert_demos netlist连接数>0

## 阶段3: 训练管道独立化（并行）

- [ ] Task 7: 创建独立训练脚本
  - [ ] SubTask 7.1: 创建scripts/train_polaris.py独立训练入口
  - [ ] SubTask 7.2: 加载real_board/448真实用例作为训练集
  - [ ] SubTask 7.3: 加载data/benchmarks/combinations/作为增强训练集
  - [ ] SubTask 7.4: 训练PPO布局模型（接polaris_place）
  - [ ] SubTask 7.5: 训练GNN布线模型（接polaris_route）
  - [ ] SubTask 7.6: 保存checkpoint到models/checkpoints/

- [ ] Task 8: 训练循环与进度汇报
  - [ ] SubTask 8.1: 训练循环每100步汇报loss/reward/DRC通过率
  - [ ] SubTask 8.2: 训练到测试集DRC通过率≥60%或最大10000步
  - [ ] SubTask 8.3: 保存训练日志到out/training/

## 阶段4: 36路标遗漏排查与补齐

- [ ] Task 9: 36路标遗漏排查
  - [ ] SubTask 9.1: 逐项核查R1-R36验收报告，标记未达标项
  - [ ] SubTask 9.2: 综合得分7.88→8.5差距分析
  - [ ] SubTask 9.3: 补齐遗漏功能（如有）

## 阶段5: 全量回归测试与商用验证

- [ ] Task 10: 全量回归测试
  - [ ] SubTask 10.1: 448真实用例端到端测试（Bug修复后重跑）
  - [ ] SubTask 10.2: 10000组合电路端到端测试（Bug修复后重跑）
  - [ ] SubTask 10.3: 统计修复前后对比：成功率/DRC通过率/平均损耗

- [ ] Task 11: 商用达标验证
  - [ ] SubTask 11.1: 验证可测试真实用例成功率≥80%
  - [ ] SubTask 11.2: 验证组合电路DRC通过率≥40%
  - [ ] SubTask 11.3: 验证训练模型在测试集DRC通过率≥60%

## 阶段6: 文档与提交

- [ ] Task 12: 更新操作记录与文档
  - [ ] SubTask 12.1: 追加操作记录.md
  - [ ] SubTask 12.2: 更新36路标验收报告
  - [ ] SubTask 12.3: git commit + push origin main

# Task Dependencies
- Task 1/2/3 可并行（3个P0 Bug独立）
- Task 4/5/6 可并行（3个P1 Bug独立，依赖Task 2完成DRC引擎修复）
- Task 7/8 依赖Task 1-3完成（训练需要Bug修复后的流水线）
- Task 9 可并行（路标排查独立于代码修复）
- Task 10 依赖Task 1-6完成（全量回归需要所有Bug修复）
- Task 11 依赖Task 7/8/10完成（商用验证需要训练+回归）
- Task 12 依赖Task 10/11完成
