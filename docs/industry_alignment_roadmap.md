# PoLaRIS 业界标准对齐分析与超越路线图

**创建日期**: 2026-06-20
**目标**: 对齐业界标准（AlphaChip/Apollo/LiDAR/PhIDO），制定超越路线图，支撑商业化

## 1. 业界标准对照矩阵

### 1.1 电子芯片 EDA 标准（AlphaChip 系）

| 维度 | AlphaChip (Google, Nature 2021) | Circuit Training (开源) | PoLaRIS 当前 | 差距 |
|------|--------------------------------|--------------------------|--------------|------|
| 状态编码 | Edge-GNN（基于边的 GNN） | GCN（图卷积） | R-GCN（节点消息传递） | ❌ 未实现 edge-based GNN |
| 训练算法 | PPO + 分布式 | PPO + TF-Agents | PPO（单机） + GNN-PPO | ⚠️ 无分布式训练 |
| 预训练范式 | 20+ TPU 块预训练 + 微调 | 支持预训练 | BC 预训练（28 SiEPIC 样本） | ⚠️ 预训练规模小 |
| Benchmark | Ariane RISC-V, MemPool, NVDLA | Ariane, NanGate45, ASAP7 | 自有 4 级课程 | ❌ 无公开 benchmark |
| 验证指标 | HPWL + 拥塞 + 密度 | 同 AlphaChip | 线长 + 拥塞 + DRC | ⚠️ 缺少密度 |
| 工业落地 | TPU v5/v6/Trillium, Axion, Dimensity | 学术复现 | 无 | ❌ 无工业落地 |

**来源**:
- Mirhoseini et al., "A graph placement methodology for fast chip design", Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training 开源: https://github.com/google-research/circuit_training
- TILOS MacroPlacement 评估: https://tilos-ai-institute.github.io/MacroPlacement/

### 1.2 光子芯片 EDA 标准（Apollo/LiDAR/PhIDO 系）

| 维度 | Apollo (ASU, 2025) | LiDAR (ASU, ISPD 2025) | PhIDO (Toronto, 2025) | PoLaRIS 当前 | 差距 |
|------|---------------------|------------------------|------------------------|--------------|------|
| 布局方法 | GPU 加速解析法 (DREAMPlace) | - | LLM Agent | RL (PPO+GNN) | ⚠️ 方法不同 |
| 布线方法 | - | Curvy A* + 拥塞感知 | gdsfactory river router | A* + 多层 | ⚠️ 缺少 curvy-aware |
| 规模 | 数千器件 (PTC) | 数千器件 (PTC/oNoC) | 118 测试电路 | 200 器件 | ❌ 规模小 10× |
| Benchmark | PTC + oNoC (开源) | PTC + oNoC (开源) | 118 自有 | 4 级课程 | ❌ 无公开 benchmark |
| 路由成功率 | 94.79% | DRV-free | - | 未量化 | ❌ 未量化 |
| 速度 | 分钟级 | 6.25× 加速 | - | 未量化 | ❌ 未量化 |
| 光子特性 | 弯曲感知线长 + 间距 | curvy A* + 交叉优化 | DRC + SAX 仿真 | 弯曲半径 + 拥塞 | ⚠️ 部分覆盖 |
| 仿真集成 | - | - | SAX | simphony + sax + pyCopy | ✅ 完整 |
| 开源 | ✅ GitHub | ✅ GitHub | ❌ | ✅ GitHub | ✅ 对齐 |

**来源**:
- Apollo: Zhou et al., "Automated Routing-Informed Placement for Large-Scale PICs", 2025, https://arxiv.org/abs/2504.18813
- LiDAR: Zhou et al., "Automated Curvy Waveguide Detailed Routing for Large-Scale PICs", ISPD 2025, https://dl.acm.org/doi/10.1145/3698364.3705355
- PhIDO: Sharma et al., "AI Agents for Photonic Integrated Circuit Design Automation", 2025, https://arxiv.org/abs/2508.14123

### 1.3 学术前沿综合评估

| 评估维度 | PoLaRIS 得分 | 业界领先 | 差距分析 |
|----------|-------------|----------|----------|
| 算法先进性 | 6/10 | AlphaChip edge-GNN | 用 R-GCN 而非 edge-GNN |
| 规模可扩展性 | 4/10 | Apollo 数千器件 | 200 器件 vs 数千器件 |
| 工业落地 | 2/10 | AlphaChip TPU | 无工业用户 |
| Benchmark 完整性 | 3/10 | Ariane/PTC/oNoC | 无公开 benchmark |
| 光子特性建模 | 7/10 | Apollo/LiDAR | 弯曲/交叉/间距部分覆盖 |
| 仿真集成 | 9/10 | PhIDO SAX | simphony+sax+pyCopy 完整 |
| 开源开放 | 9/10 | Apollo/LiDAR | ✅ 开源对齐 |
| 文档与测试 | 8/10 | 业界平均 | 944 测试 + 0 警告 |
| **综合得分** | **6.0/10** | **8.5/10** | **差距 2.5 分** |

## 2. 超越路线图（商业化路径）

### 2.1 短期目标（3 个月）：对齐业界标准

**目标**：达到 Apollo/LiDAR 2025 的技术水准

#### 2.1.1 打通端到端流水线（当前最大孤岛）
- **现状**：BC→GNN-PPO→CNN→真实环境 3 处孤岛未打通
- **目标**：1 条端到端流水线全部打通
- **关键工作**：
  1. `train_il_pipeline.py` 可选使用 `GNNPPOAgent`（打通 GNN-PPO↔训练流水线）
  2. `_run_lightweight_rl_loop` 改为调用 `FloorplanEnv` + `train_loop`（打通 BC↔真实 RL）
  3. CNN 拥塞图作为 obs 附加通道（打通 CNN↔RL 策略网络）

#### 2.1.2 引入公开 Benchmark
- **目标**：在 Ariane/PTC/oNoC 公开 benchmark 上验证
- **关键工作**：
  1. 移植 TILOS MacroPlacement 的 Ariane 测试用例
  2. 移植 Apollo 的 PTC/oNoC 光子 benchmark
  3. 量化路由成功率、线长、DRV、运行时间

#### 2.1.3 规模扩展到 1000 器件
- **现状**：200 器件（xlarge 级别）
- **目标**：1000 器件（对齐 Apollo/LiDAR）
- **关键工作**：
  1. 优化 `_scale_random_circuit()` 支持 1000 器件
  2. 优化 GNN 内存占用（子图采样）
  3. 优化 A* 布线网格规模

### 2.2 中期目标（6 个月）：差异化创新

**目标**：在光子特性上超越 Apollo/LiDAR

#### 2.2.1 光子物理感知 RL（差异化优势）
- **Apollo 用解析法，PoLaRIS 用 RL**：RL 能学习人类难以表达的物理直觉
- **关键创新**：
  1. 奖励函数集成 S 参数仿真（simphony/sax 实时反馈）
  2. 状态编码包含插入损耗热力图
  3. 动作空间支持弯曲半径优化（非仅位置）

#### 2.2.2 多平台 PDK 支持（差异化优势）
- **现状**：SOI/SiN/InP/LNOI 四平台 PDK
- **Apollo/LiDAR 仅支持单一平台**
- **关键工作**：
  1. 完善 LNOI 平台器件库
  2. 跨平台迁移学习
  3. 多平台 benchmark 对比

#### 2.2.3 预训练+微调范式（对齐 AlphaChip）
- **目标**：在 100+ 光子电路块上预训练，新电路微调
- **关键工作**：
  1. 扩展 ExpertDataset 到 100+ 专家样本
  2. 实现预训练权重迁移机制
  3. 量化预训练对微调速度的提升

### 2.3 长期目标（12 个月）：商业化落地

**目标**：首个开源光子 EDA 商业化产品

#### 2.3.1 产品化
- **企业版功能**：
  1. Web UI（基于 OpenPreview 暴露）
  2. 批量布局布线 API
  3. DRC 报告导出
  4. GDS/OASIS 导出
- **许可**：双许可（开源 AGPL + 商业许可）

#### 2.3.2 生态建设
- **Foundry 合作**：与 IMEC/AMF/AIM Photonics/CompoundTek/IHP/LioniX/NOEIC 对接
- **学术合作**：与 ASU/UToronto/SJTU 课题组合作
- **开源社区**：GitHub Star 目标 1000+

#### 2.3.3 性能指标（商业化门槛）
| 指标 | 目标 | 业界标准 | 超越点 |
|------|------|----------|--------|
| 路由成功率 | ≥ 95% | Apollo 94.79% | +0.21% |
| 1000 器件运行时间 | < 10 分钟 | LiDAR 6.25× 加速 | 对齐 |
| DRV 数量 | 0 | LiDAR DRV-free | 对齐 |
| 插入损耗 | 优于人工 10% | LiDAR 14% | 接近 |
| 支持平台数 | 4 | Apollo 1 | 4× |
| 开源 | ✅ | Apollo ✅ | 对齐 |

## 3. 技术债务清单（阻碍商业化）

### 3.1 高优先级（阻碍对齐）
1. **edge-GNN 未实现**：AlphaChip 核心创新，必须实现
2. **无公开 benchmark 验证**：无法证明性能，必须补齐
3. **规模限制 200 器件**：比业界小 10×，必须扩展
4. **端到端流水线孤岛**：3 处未打通，必须连通

### 3.2 中优先级（阻碍差异化）
5. **CNN 未接入策略网络**：DeepPlace 双视图未实现
6. **预训练规模小**：28 样本 vs AlphaChip 20+ 块
7. **无分布式训练**：单机 vs AlphaChip 分布式
8. **curvy-aware 布线缺失**：LiDAR 核心创新未实现

### 3.3 低优先级（阻碍生态）
9. **无 Web UI**：商业化必备
10. **无 Foundry 对接**：商业化必备
11. **无企业版功能**：商业化必备

## 4. 诚信声明

本分析基于 2026-06-20 的代码核查与学术前沿检索，如实声明：

1. **PoLaRIS 当前综合得分 6.0/10，业界领先 8.5/10，差距 2.5 分**
2. **最大差距**：无公开 benchmark 验证（3/10）、无工业落地（2/10）、规模小 10×（4/10）
3. **最大优势**：仿真集成完整（9/10）、开源开放（9/10）、文档测试完备（8/10）
4. **商业化可行性**：短期需对齐业界标准，中期靠光子物理感知 RL 差异化，长期靠多平台 PDK 生态
5. **风险声明**：若不补齐 benchmark 和规模，商业化将失败

## 5. 参考来源

### 学术论文
- Mirhoseini et al., "A graph placement methodology for fast chip design", Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- Zhou et al., "Apollo: Automated Routing-Informed Placement for Large-Scale PICs", 2025, https://arxiv.org/abs/2504.18813
- Zhou et al., "LiDAR: Automated Curvy Waveguide Detailed Routing for Large-Scale PICs", ISPD 2025, https://dl.acm.org/doi/10.1145/3698364.3705355
- Sharma et al., "AI Agents for Photonic Integrated Circuit Design Automation", 2025, https://arxiv.org/abs/2508.14123
- Cheng et al., "DeepPlace: Chip Placement with Deep Reinforcement Learning", NeurIPS 2021, https://openreview.net/pdf?id=uNYqDfPEDD8
- Basso et al., "Routing-aware floorplanning with RL", NeurIPS 2025, https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- Bengio et al., "Curriculum Learning", ICML 2009, https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Schulman et al., "Proximal Policy Optimization Algorithms", 2017, https://arxiv.org/abs/1707.06347
- Pomerleau, "ALVINN: An Autonomous Land Vehicle in a Neural Network", NeurIPS 1989, https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

### 开源仓库
- Circuit Training (AlphaChip): https://github.com/google-research/circuit_training
- TILOS MacroPlacement: https://tilos-ai-institute.github.io/MacroPlacement/
- Apollo: https://github.com/ScopeX-ASU/Apollo
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- SAX: https://flaport.github.io/sax/
- Simphony: https://simphonyphotonics.readthedocs.io/
