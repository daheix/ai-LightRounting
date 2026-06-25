# T13 商业 EDA + AI 标杆功能清单：Google AlphaChip + Circuit Training

> **学术诚信声明**：本文档所有功能点均来自公开来源（Nature 论文、Nature 附录、DeepMind 官方博客、GitHub 仓库 README、DeepWiki 文档、第三方学术论文）。每个功能点均标注来源 URL。未公开信息明确标注"未公开"。本文档不含任何臆造内容。

---

## 文档元信息

| 项目 | 内容 |
|---|---|
| 工具名 | AlphaChip（含 Circuit Training 开源框架） |
| 厂商 | Google DeepMind / Google Research |
| 官网 URL | Nature 论文: https://www.nature.com/articles/s41586-021-03544-w <br> Nature 附录: https://www.nature.com/articles/s41586-024-08032-5 <br> DeepMind 博客: https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ <br> GitHub: https://github.com/google-research/circuit_training |
| 调研日期 | 2026-06-25 |
| 文档版本 | v1.0 |
| 调研员 | EDA + AI 标杆调研员 |

---

## 工具概述

AlphaChip 是 Google DeepMind 推出的强化学习方法，用于加速和优化芯片布局（floorplanning）设计。该方法源于 2020 年 arXiv 预印本（arxiv:2004.10746），2021 年正式发表于 Nature（s41586-021-03544-w），2024 年 9 月发布 Nature 附录并正式命名为 AlphaChip，同时开源预训练检查点。其开源实现为 Circuit Training 框架（github.com/google-research/circuit_training），基于 TF-Agents 与 TensorFlow 2.x 构建，支持分布式训练与多 GPU 数据收集。

AlphaChip 是首批用于解决真实世界工程问题的强化学习方法之一，已在 Google TPU v5e/v5p/Trillium（第六代）/Ironwood（第七代）以及 Axion CPU、MediaTek Dimensity 5G 等芯片中实际部署。

来源：
- https://www.nature.com/articles/s41586-021-03544-w
- https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/
- https://github.com/google-research/circuit_training

---

## 功能点清单

### 1. Edge-GNN 图神经网络架构

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-1.1 | Edge-based Graph Neural Network | 论文提出"基于边"的图卷积神经网络架构，能够学习芯片组件之间丰富的、可迁移的表示 | https://www.nature.com/articles/s41586-021-03544-w |
| AC-1.2 | 节点/边特征编码 | 状态包含网表信息（节点连接性）、每个节点的特征（宽度、高度）、每条边的特征（连接计数）、下一个待放置节点索引、网表属性（宏总数、标准单元簇数、线长计数、路由分配） | https://wenku.csdn.net/column/1a77rp99bf |
| AC-1.3 | 优于 GCN 的鲁棒性 | Edge-GNN 比 GCN（graph convolutional neural network）更抗过拟合，零样本（zero-shot）性能更高 | https://www.researchgate.net/publication/352267082_A_graph_placement_methodology_for_fast_chip_design |
| AC-1.4 | 跨芯片泛化 | Edge-GNN 学习互连芯片组件之间的关系，可在不同芯片间泛化，使 AlphaChip 随每次布局设计而改进 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 2. PPO 强化学习

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-2.1 | Proximal Policy Optimization (PPO) | RL 智能体由参数 θ 神经网络建模，使用 PPO 算法优化策略参数 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-2.2 | MDP 建模 | 将芯片布局表述为顺序马尔可夫决策过程（MDP）：状态=当前布局状态；行动=当前节点可放置的所有有效位置；状态转移=概率；奖励=最后行动的负加权和 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-2.3 | 策略梯度优化 | 通过最小化成本函数 J(θ, G) = (1/K) Σ E[R_{p,g}] 优化布局决策 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-2.4 | TF-Agents 实现 | Circuit Training 基于 TF-Agents 与 TensorFlow 2.x 实现 PPO，支持 eager execution | https://github.com/google-research/circuit_training |
| AC-2.5 | AlphaGo/AlphaZero 类比 | 类似 AlphaGo 与 AlphaZero，将芯片 floorplanning 视为一种游戏，从空白栅格开始每次放置一个电路元件 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 3. 预训练范式

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-3.1 | 预训练 + 微调两阶段 | 设计 TPU 布局时，先在前几代芯片块（片上/片间网络块、内存控制器、数据传输缓冲区）上预训练，再在当前 TPU 块上运行生成高质量布局 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-3.2 | 数据集规模效应 | 预训练数据集越大（2/5/20 块），测试块上的布局质量与泛化性能越好；最大数据集策略最抗过拟合 | https://www.researchgate.net/publication/352267082_A_graph_placement_methodology_for_fast_chip_design |
| AC-3.3 | 预训练检查点开源 | 2024 年 9 月发布预训练 checkpoint，分享模型权重，训练于 20 个 TPU 块 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-3.4 | 多网表预训练指南 | Circuit Training 仓库 docs/PRETRAINING.md 提供在多个网表上进行预训练的指令 | https://github.com/google-research/circuit_training |
| AC-3.5 | 经验积累改进 | 与以往方法不同，AlphaChip 在解决更多布局任务时变得更好更快，类似人类专家 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 4. 分布式训练

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-4.1 | 多 GPU 分布式训练 | Circuit Training 支持跨多个 GPU 的分布式训练 | https://github.com/google-research/circuit_training |
| AC-4.2 | 分布式数据收集 | 支持扩展到数百个 actor 进行数据收集；Nature 作者使用 512 个 collect jobs | https://arxiv.org/html/2302.11014v3 |
| AC-4.3 | Reverb Replay Buffer | 使用 Reverb Server 作为经验回放缓冲区 | https://deepwiki.com/google-research/circuit_training |
| AC-4.4 | Variable Container 策略分发 | 使用 Variable Container 进行策略分发 | https://deepwiki.com/google-research/circuit_training |
| AC-4.5 | 训练/收集独立扩展 | 数据收集与多 GPU 训练是独立进程，可分别优化 | https://arxiv.org/html/2302.11014v3 |
| AC-4.6 | 推荐配置 | Google 作者推荐 8-GPU 配置（global batch size=1024）以获得更稳定学习与更低策略梯度估计噪声 | https://arxiv.org/html/2302.11014v3 |

### 5. TPU 应用（v5e / v5p / Trillium / Ironwood）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-5.1 | TPU v5e 部署 | AlphaChip 在 TPU v5e 上放置 10 个块，线长较人类专家减少 3.2% | https://www.birow.com/ai-chipgyartasban |
| AC-5.2 | TPU v5p 部署 | AlphaChip 用于 TPU v5p（Cloud TPU v5p AI 加速器超级计算机）布局设计 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-5.3 | TPU Trillium (v6) 部署 | 第六代 TPU Trillium 上 AlphaChip 放置 25 个块，线长减少 6.2%；Trillium 峰值算力较前代提升近 5×，内存带宽翻倍，能效提升 67% | https://www.birow.com/ai-chipgyartasban |
| AC-5.4 | TPU Ironwood (v7) 部署 | 第七代 TPU Ironwood（用于 Gemini 开发）已通用化，AlphaChip 持续参与设计 | https://gigazine.net/gsc_news/en/20240927-google-computer-chip-design-ai-alphachip |
| AC-5.5 | 三代 TPU 块数增长 | 从 v5e → v5p → Trillium，AlphaChip 设计的芯片块数持续增长 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-5.6 | 三代 TPU 线长持续减少 | 与人类物理设计团队相比，AlphaChip 在三代 TPU 中的平均线长持续减少 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-5.7 | Axion CPU 部署 | AlphaChip 用于 Google Axion 处理器（基于 Arm 的通用数据中心 CPU）布局设计 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 6. MediaTek Dimensity 应用

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-6.1 | MediaTek 采用 AlphaChip | 联发科（MediaTek）扩展 AlphaChip 应用，加速其最先进芯片开发 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |
| AC-6.2 | Dimensity 5G 旗舰芯片 | 用于三星手机中的 MediaTek Dimensity 旗舰 5G 芯片，改善功耗、性能与面积 | https://c.m.163.com/news/a/JDBLEJAA05119734.html |
| AC-6.3 | MediaTek 高管背书 | MediaTek 高级副总裁 SR Tsai 公开表示"AlphaChip 的突破性 AI 方法革命化了芯片设计的关键阶段" | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 7. Circuit Training 开源框架

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-7.1 | 开源框架 | Circuit Training 是开源框架，复现 Nature 2021 论文方法 | https://github.com/google-research/circuit_training |
| AC-7.2 | CircuitEnv 环境 | 强化学习环境，将芯片布局建模为顺序决策问题 | https://deepwiki.com/google-research/circuit_training |
| AC-7.3 | PlacementCost (PLC) Client | 评估布局质量的库接口 | https://deepwiki.com/google-research/circuit_training |
| AC-7.4 | Action Space | 定义宏单元在网格上的可能放置位置 | https://deepwiki.com/google-research/circuit_training |
| AC-7.5 | Coordinate Descent Placer | 可选的后处理：精化宏单元布局的坐标下降放置器 | https://deepwiki.com/google-research/circuit_training |
| AC-7.6 | 端到端冒烟测试 | tools/e2e_smoke_test.sh 提供端到端冒烟测试 | https://github.com/google-research/circuit_training |
| AC-7.7 | Ariane RISC-V 教程 | docs/ARIANE.md 提供开源 Ariane RISC-V CPU 的训练教程 | https://github.com/google-research/circuit_training |

### 8. 宏单元布局（Macro Placement）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-8.1 | 顺序宏单元放置 | RL 智能体将网表的宏逐个放置到芯片画布上 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-8.2 | 网格化画布 | 画布定义为 m × n 网格，m 与 n 为网格行列数 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-8.3 | 6 小时内生成布局 | 论文声称 6 小时内自动生成芯片 floorplan，在功耗、性能、芯片面积等所有关键指标上优于或可比人类 | https://www.nature.com/articles/s41586-021-03544-w |
| AC-8.4 | 优于 RePlAce 与 SA | 论文报告结果优于 RePlAce 学术布局器与模拟退火（SA）元启发式 | https://www.researchgate.net/publication/352267082_A_graph_placement_methodology_for_fast_chip_design |
| AC-8.5 | 超人类布局 | 数小时内生成超人类或可比的芯片布局，而非数周或数月的人类努力 | https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ |

### 9. 标准单元布局（Standard Cell Placement）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-9.1 | 力导向粗布局 | 放置完所有宏后，使用力导向方法对标准单元簇进行粗布局 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-9.2 | DREAMPlace 集成 | Circuit Training 与 DREAMPlace 集成用于放置标准单元（芯片设计中较小的组件） | https://deepwiki.com/google-research/circuit_training |
| AC-9.3 | 标准单元分组 | docs/STANDARD_CELL_GROUPING.md 描述标准单元分组方法 | https://github.com/google-research/circuit_training |
| AC-9.4 | 混合方法 | 系统使用混合方法：强化学习用于宏单元布局，解析方法用于标准单元布局 | https://deepwiki.com/google-research/circuit_training |
| AC-9.5 | 商业 EDA 工具评估 | 评估流程：放置完成后，将宏对齐到电源网格、冻结宏位置，使用商业 EDA 工具放置标准单元并报告最终结果 | https://www.researchgate.net/publication/352267082_A_graph_placement_methodology_for_fast_chip_design |

### 10. 奖励函数设计

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-10.1 | 负加权和奖励 | 奖励 R_{p,g} = -Wirelength(p,g) - λ·Congestion(p,g) - γ·Density(p,g) | https://wenku.csdn.net/column/1a77rp99bf |
| AC-10.2 | 线长 (Wirelength) | 近似线长作为奖励的主要分量 | https://wenku.csdn.net/column/1a77rp99bf |
| AC-10.3 | 拥塞 (Congestion) | 路由拥塞作为奖励分量，权重 λ | https://wenku.csdn.net/column/1a77rp99bf |
| AC-10.4 | 密度 (Density) | 单元密度作为奖励分量，权重 γ | https://wenku.csdn.net/column/1a77rp99bf |
| AC-10.5 | 稀疏奖励结构 | 一个回合内除最后行动外所有中间行动奖励为 0；最后行动奖励等于近似线长、密度与路由拥塞的负加权和 | https://wenku.csdn.net/column/1a77rp99bf |

### 11. 算法扩展与生态影响

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-11.1 | 扩展到逻辑综合 | AlphaChip 已扩展到芯片设计流程的多个阶段，包括逻辑综合 | https://github.com/google-research/circuit_training |
| AC-11.2 | 扩展到 Macro 选择 | 扩展到宏单元选择阶段 | https://github.com/google-research/circuit_training |
| AC-11.3 | 扩展到时序优化 | 扩展到时序优化阶段 | https://github.com/google-research/circuit_training |
| AC-11.4 | 引发 AI for chips 研究热潮 | AlphaChip 引发了过去几年 AI for chips 领域的研究激增 | https://github.com/google-research/circuit_training |
| AC-11.5 | 跨 Alphabet 应用 | 用于 Alphabet 内部各种芯片的布局设计 | https://github.com/google-research/circuit_training |

### 12. 学术评估与可复现性

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| AC-12.1 | TILOS-AI MacroPlacement 基准 | TILOS-AI Institute 建立 MacroPlacement 公开基准，包含 Ariane、MemPool、NVDLA 等开源设计 | https://tilos-ai-institute.github.io/MacroPlacement/ |
| AC-12.2 | IEEE TCAD 评估论文 | "An Updated Assessment of Reinforcement Learning for Macro Placement" 被 IEEE TCAD 接收（2025 年 12 月） | https://tilos-ai-institute.github.io/MacroPlacement/ |
| AC-12.3 | 子 10nm 基准发布 | 发布 sub-10nm 公开基准：Google 7nm TSMC Ariane protobuf 的 LEF/DEF 与缩放变体，以及 ASAP7 7nm 研究使能套件 | https://arxiv.org/html/2302.11014v3 |
| AC-12.4 | CT 与 Nature 差异研究 | 学术评估指出 Circuit Training 实现与 Nature 论文之间存在差异 | https://arxiv.org/html/2302.11014v3 |
| AC-12.5 | SA 基线增强 | 增强模拟退火（SA）基线，使用 "go-with-the-winners" 元启发式与多线程实现 | https://arxiv.org/html/2302.11014v3 |

---

## 功能点统计

| 类别 | 子功能数 |
|---|---|
| 1. Edge-GNN 图神经网络架构 | 4 |
| 2. PPO 强化学习 | 5 |
| 3. 预训练范式 | 5 |
| 4. 分布式训练 | 6 |
| 5. TPU 应用（v5e/v5p/Trillium/Ironwood） | 7 |
| 6. MediaTek Dimensity 应用 | 3 |
| 7. Circuit Training 开源框架 | 7 |
| 8. 宏单元布局 | 5 |
| 9. 标准单元布局 | 5 |
| 10. 奖励函数设计 | 5 |
| 11. 算法扩展与生态影响 | 5 |
| 12. 学术评估与可复现性 | 5 |
| **T13 文档总计** | **62** |

---

## 参考来源汇总

1. https://www.nature.com/articles/s41586-021-03544-w （Nature 2021 原始论文）
2. https://www.nature.com/articles/s41586-024-08032-5 （Nature 2024 附录）
3. https://deepmind.google/discover/blog/how-alphachip-transformed-computer-chip-design/ （DeepMind 官方博客）
4. https://github.com/google-research/circuit_training （Circuit Training 开源仓库）
5. https://deepwiki.com/google-research/circuit_training （DeepWiki 文档）
6. https://www.researchgate.net/publication/352267082_A_graph_placement_methodology_for_fast_chip_design （ResearchGate 论文页）
7. https://wenku.csdn.net/column/1a77rp99bf （强化学习在芯片布局与分区中的应用）
8. https://arxiv.org/html/2302.11014v3 （An Updated Assessment of RL for Macro Placement）
9. https://tilos-ai-institute.github.io/MacroPlacement/ （TILOS-AI MacroPlacement 项目）
10. https://www.birow.com/ai-chipgyartasban （AlphaChip 综述）
11. https://c.m.163.com/news/a/JDBLEJAA05119734.html （DeepTech 深科技报道）
12. https://gigazine.net/gsc_news/en/20240927-google-computer-chip-design-ai-alphachip （Gigazine 报道）
13. https://discuss.pytorch.kr/t/alphachip-rl-feat-google/5291 （PyTorch Korea 技术解读）
14. https://hub.baai.ac.cn/view/40075 （新智元报道）
15. https://www.maginative.com/article/google-deepminds-alphachip-has-secretly-transformed-microchip-design-with-ai/ （Maginative 报道）

---

**文档结束** | 调研日期 2026-06-25 | 版本 v1.0
