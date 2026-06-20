# PoLaRIS 光弈 光电子 AI 智能布局布线引擎 — 长远规划 Roadmap

> **文档版本**：v1.0
> **创建日期**：2026-06-20
> **当前商业化就绪度**：4/10（较初始 2/10 提升，主要在 PDK/GDS/仿真可信化方面）
> **目标就绪度**：8/10（可对外发布 beta 版本）

---

## 1. 项目现状评估

### 1.1 已完成的核心能力

| 维度 | 状态 | 证据 |
|------|------|------|
| PDK 器件库 | ✅ 完整 | 81 个器件，SOI/SiN/InP/LNOI 四平台，全部溯源 |
| GDS 导出 | ✅ 真实兼容 | 已对齐 SiEPIC 真实版图格式（PIN 69,0 + DEVREC text） |
| 布局布线引擎 | ✅ 可用 | A* 410x 加速，端到端跑通 |
| 仿真系统 | ✅ 可用 | SimLoop 闭环 + simphony 验证一致 |
| 端到端流水线 | ✅ 跑通 | 网表→RL布局→RL布线→S参数仿真→GDS→DRC |
| 开源真实器件集成 | ✅ 完成 | SiEPIC GDS 例子 + ubcpdk 映射 + simphony 对比 + gdsfactory 集成 |
| 质量门禁体系 | ✅ 完善 | 19 条规则 + 0 警告 0 错误 + 847 测试通过 |

### 1.2 关键瓶颈：RL 训练不收敛

**训练数据**：965k episodes 后布局 reward 仍在 -15~-0.4 波动（最佳仅 1.32），布线 reward 出现 -10000 灾难值。

**根因诊断**（详见 [docs/optimization_log.md](optimization_log.md)）：

| 级别 | 问题 | 影响 |
|------|------|------|
| 致命 #1 | LR 调度按 sample 计数导致衰减到零 | 285k episodes 后 LR=1e-6（初始 1/300），700k episodes 无效训练 |
| 致命 #2 | 观测维度截断（obs_dim=113 基于 3 器件网表） | agent 对器件 4-12 完全"失明" |
| 致命 #3 | NumPy PPO logprob 缺失 1/var 和 -log(std) | action_log_std 永不更新，策略只能学"不要做什么" |
| 高 #4 | 布线 reward clipping 未在运行进程中生效 | -10000 灾难值摧毁价值函数 |
| 高 #5 | 奖励尺度失衡（惩罚主导 -22 vs 正向 +1） | agent 只能减少惩罚，无法增加收益 |
| 高 #6 | 布线 agent 更新频率过低（每 10k episodes 1 次） | 980k episodes 仅 98 次更新，远不够收敛 |

### 1.3 遗留技术债

- GNN 状态编码已实现但未真正接入训练（死代码）
- CNN 拥塞预测器无训练数据（随机权重）
- SimLoop 反馈未作为 RL reward shaping 项
- IntegratedPipeline 与 cmd_run 两条流水线未统一

---

## 2. 里程碑规划

### M1: 修复 RL 训练收敛（最高优先级）

**目标**：让布局布线 RL 真正可用，reward 稳定收敛。

**验收标准**：
- 布局 reward 在 100k episodes 内稳定上升至 ≥ 3.0（当前最佳 1.32）
- 布线 reward 在 50k episodes 内稳定上升至 ≥ -2.0（当前 -10000~-1）
- value_loss 单调下降至 < 1.0（当前 14-15）
- policy_loss 在 [-0.5, 0.5] 范围内稳定（当前 -0.01 极小或爆炸）

**任务分解**：

#### M1.1 修复 LR 调度 Bug（致命 #1）
- **文件**：[src/polaris/trainer/ppo_torch.py](file:///workspace/src/polaris/trainer/ppo_torch.py) 第 92 行
- **修复**：`_total_steps` 改为按 update 次数计数，或将 `total_steps` 配置为实际 sample 总数
- **验证**：训练 100k episodes 后 LR 仍 > 1e-4

#### M1.2 修复观测维度截断（致命 #2）
- **文件**：[src/polaris/trainer/train_loop.py](file:///workspace/src/polaris/trainer/train_loop.py) 第 111-117 行
- **修复**：`_pad_obs` 改为零填充（而非截断），obs_dim 取数据集最大器件数对应维度
- **验证**：12 器件网表的 obs 完整传入网络

#### M1.3 修复 NumPy PPO logprob（致命 #3）
- **文件**：[src/polaris/trainer/ppo.py](file:///workspace/src/polaris/trainer/ppo.py) 第 381-382 行
- **修复**：`new_lp = -0.5 * (diff*diff / var).sum(axis=-1) - log_std.sum()`
- **验证**：entropy 不再恒定 4.2568，action_log_std 有梯度更新

#### M1.4 修复奖励尺度失衡（高 #5）
- **文件**：[src/polaris/engine/floorplan_env.py](file:///workspace/src/polaris/engine/floorplan_env.py) 第 359-383 行
- **修复**：降低 overlap_penalty（10→2），提高 area_reward（1→5），或对 reward 做 tanh 归一化
- **验证**：正向 reward 与惩罚在同一量级

#### M1.5 重启训练进程使 reward clipping 生效（高 #4）
- **操作**：停止当前 train_2m.py 进程，修复后重启
- **验证**：布线 reward 不再出现 -10000 灾难值

#### M1.6 提高布线 agent 更新频率（高 #6）
- **文件**：[scripts/train_2m.py](file:///workspace/scripts/train_2m.py) 第 468 行
- **修复**：`batch_num % 20 == 0` → `batch_num % 2 == 0`
- **验证**：980k episodes 后布线更新次数 ≥ 1000

**依赖**：无（可立即开始）
**预估工作量**：3 个致命 bug 修复 + 3 个高优先级修复 + 重启训练验证

---

### M2: 建立基准验证体系

**目标**：用真实 SiEPIC GDS 例子 + simphony + gdsfactory 建立端到端可验证的基准测试套件，量化 PoLaRIS 与真实版图的差距。

**验收标准**：
- 至少 5 个真实 SiEPIC 电路（MZI/Ring/MMI）的端到端验证通过
- PoLaRIS 仿真损耗与 simphony 真实器件模型误差 < 1 dB
- PoLaRIS GDS 导出格式通过 SiEPIC KLayout verifier 验证
- 基准测试套件纳入 CI（每次 PR 自动运行）

**任务分解**：

#### M2.1 真实 SiEPIC GDS 电路解析
- **输入**：[data/benchmarks/siepic_examples/](file:///workspace/data/benchmarks/siepic_examples/) 的 6 个 GDS
- **任务**：用 klayout 提取 GDS 的 netlist（instances/connections/ports），转换为 PoLaRIS CircuitSpec
- **输出**：`data/benchmarks/siepic_netlists/*.json`

#### M2.2 端到端验证测试套件
- **任务**：对每个 SiEPIC 电路，运行 PoLaRIS 端到端流水线，对比：
  - GDS layer 结构（PIN/DEVREC/WG）
  - S 参数（与 simphony siepic 库对比）
  - 总插入损耗（与 SiEPIC 文献值对比）
- **输出**：`tests/test_siepic_e2e.py`

#### M2.3 gdsfactory 真实器件生成对比
- **任务**：用 gdsfactory 生成相同参数的 MZI/Ring GDS，对比 PoLaRIS 导出的 GDS 几何形状
- **输出**：`tests/test_gdsfactory_comparison.py`
- **注意**：gdsfactory import 失败时跳过

#### M2.4 基准性能回归测试
- **任务**：建立性能基准（网表解析/A*布线/GNN推理/GDS导出），纳入 CI
- **输出**：`scripts/performance_regression.py`

**依赖**：M1 完成（RL 可用后才能验证端到端质量）
**预估工作量**：4 个子任务

---

### M3: GNN/CNN/SimLoop 深度集成

**目标**：消除死代码，将 GNN 状态编码 + CNN 拥塞预测 + SimLoop 反馈真正接入训练流水线，实现设计文档中的 Phase 1-4 训练方法论。

**验收标准**：
- GNN StateEncoder 作为 PPO 策略网络的可训练参数联合训练
- CNN CongestionPredictor 有训练数据集和训练循环，输出非随机
- SimLoop 约束反馈作为 RL reward shaping 项接入 train_loop
- 训练日志显示 GNN/CNN/SimLoop 三个模块都在参与

**任务分解**：

#### M3.1 GNN 端到端联合训练
- **文件**：[src/polaris/trainer/gnn_ppo.py](file:///workspace/src/polaris/trainer/gnn_ppo.py)
- **任务**：GNNPPOAgent 已实现，需训练验证梯度正确流动
- **验证**：GNN 参数的 grad 非零，loss 单调下降

#### M3.2 CNN 拥塞预测器训练
- **文件**：[src/polaris/engine/congestion.py](file:///workspace/src/polaris/engine/congestion.py)
- **任务**：用 `generate_congestion_dataset` 生成训练数据，训练 CongestionCNN 至 loss < 0.1
- **输出**：`checkpoints/cnn_congestion/`

#### M3.3 SimLoop 反馈接入 RL reward
- **文件**：[src/polaris/trainer/train_loop.py](file:///workspace/src/polaris/trainer/train_loop.py)
- **任务**：每 N 步用 ConstraintChecker 检查布局约束违规，作为 reward shaping 项
- **验证**：训练日志显示 sim_feedback 字段

#### M3.4 统一两条流水线
- **任务**：IntegratedPipeline 与 cmd_run 合并为单一入口，消除重复代码
- **验证**：cmd_run 内部调用 IntegratedPipeline

**依赖**：M1 完成（RL 收敛后才能验证 GNN/CNN 集成效果）
**预估工作量**：4 个子任务

---

### M4: 商业化发布准备

**目标**：完善 publish/ 发布制品，让第三方能安装使用 PoLaRIS。

**验收标准**：
- `pip install polaris-photonic` 可一键安装
- 用户手册覆盖安装/快速开始/API 参考/示例
- 至少 4 个可运行示例（MZI/Ring/LiDAR/PICBench）
- wheel 包 < 50MB，无重型依赖

**任务分解**：

#### M4.1 wheel 打包与发布
- **任务**：`python -m build --wheel --outdir publish/wheels/`，验证可安装
- **输出**：`publish/wheels/polaris-0.1.0-py3-none-any.whl`

#### M4.2 用户手册
- **任务**：编写安装指南、快速开始、教程
- **输出**：`publish/docs/user_guide.md`

#### M4.3 API 参考
- **任务**：用 sphinx/mkdocs 自动生成 API 文档
- **输出**：`publish/docs/api_reference/`

#### M4.4 示例代码
- **任务**：4 个可运行示例（基础 MZI/Ring 谐振器/LiDAR 矩阵/PICBench 调制器）
- **输出**：`publish/examples/*.py`

#### M4.5 README 与品牌
- **任务**：完善 README.md，含功能列表/截图/性能对比
- **输出**：`README.md`

**依赖**：M1 + M2 完成（产品可用且有验证体系后才能发布）
**预估工作量**：5 个子任务

---

## 3. 优先级与依赖关系

```
M1 (修复 RL 训练收敛)  ← 最高优先级，无依赖
  ↓
M2 (基准验证体系)      ← 依赖 M1
  ↓
M3 (GNN/CNN/SimLoop)   ← 依赖 M1
  ↓
M4 (商业化发布)         ← 依赖 M1 + M2
```

**并行机会**：M2 和 M3 可在 M1 完成后并行推进。

---

## 4. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| M1 修复后训练仍不收敛 | 中 | 高 | 准备 Plan B：用 imitation learning 从 SiEPIC 真实布局学习 |
| gdsfactory 安装困难 | 中 | 低 | 已有 pyCopy 兜底 + SiEPIC 真实 GDS 例子 |
| GNN 联合训练梯度不稳定 | 高 | 中 | 先冻结 GNN 做 feature extractor，验证后再联合训练 |
| 商业化发布后发现兼容性问题 | 低 | 高 | M2 基准验证体系先行，CI 门禁保证质量 |

---

## 5. 成功指标

### 短期（M1 完成后）
- 布局 reward ≥ 3.0（100k episodes 内）
- 布线 reward ≥ -2.0（50k episodes 内）
- 训练日志显示 LR 稳定、loss 单调下降

### 中期（M2 + M3 完成后）
- 5 个真实 SiEPIC 电路端到端验证通过
- PoLaRIS 仿真损耗与 simphony 误差 < 1 dB
- GNN/CNN/SimLoop 三个模块都在训练中参与

### 长期（M4 完成后）
- `pip install polaris-photonic` 可一键安装
- 商业化就绪度 ≥ 8/10
- 至少 1 个外部用户成功使用 PoLaRIS 完成光子芯片设计

---

## 6. 参考来源

- PoLaRIS 设计文档：[docs/设计文档.md](设计文档.md)
- 性能基准报告：[docs/performance_benchmark.md](performance_benchmark.md)
- 训练过程日志：[docs/训练过程日志.md](训练过程日志.md)
- 优化日志：[docs/optimization_log.md](optimization_log.md)
- 项目规则：[.trae/rules/project_rules.md](../.trae/rules/project_rules.md)
- SiEPIC EBeam PDK：https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- simphony siepic 库：https://simphonyphotonics.readthedocs.io/en/stable/libs/siepic.html
- gdsfactory：https://gdsfactory.github.io/gdsfactory/
- PPO 算法参考：Schulman et al., "Proximal Policy Optimization Algorithms", arXiv 2017, https://arxiv.org/abs/1707.06347
- GAE 算法参考：Schulman et al., "High-Dimensional Continuous Control Using GAE", ICLR 2016, https://arxiv.org/abs/1506.02438
