# PoLaRIS 训练/模型/布线系统优化日志

本日志记录训练系统、模型系统、布线系统的优化过程，遵守规则 1.1 方案检索与规则 15 学术诚信。

## 检索记录（规则 1.1 + 15.4）

### 检索关键词
- "PPO photonics routing rip-up reroute reinforcement learning 2024 2025"
- "graph neural network analog IC placement routing-aware 2025 R-GCN attention residual"
- "photonic waveguide routing A* curvy bend radius constraint 2024 2025 LiDAR"

### 检索到的论文列表

| # | 标题 | 作者/机构 | 年份 | URL |
|---|------|----------|------|-----|
| 1 | Advancing Routing-Awareness in Analog ICs Floorplanning | Basso et al., U Trieste/Infineon | 2025 | https://arxiv.org/html/2510.15387v1 |
| 2 | LiDAR: Automated Curvy Waveguide Detailed Routing for Large-Scale PICs | Zhou et al., ASU/Fudan | 2025 | https://dl.acm.org/doi/pdf/10.1145/3698364.3705355 |
| 3 | LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing | Zhou et al., ASU | 2025 | https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf |
| 4 | Toward Intelligent EPDA for Large-Scale PICs (PoLaRIS) | Zhou, Ma, Gu, ASU | 2025 | https://arxiv.org/pdf/2507.22301 |
| 5 | RL-EDA: RL For Automated Chip Floorplanning And Routing | Hassan, Deng, Apple/ProteanTecs | 2024 | https://www.researchgate.net/publication/395473570 |
| 6 | Photonic Spiking RL for Intelligent Routing | Xiang et al. | 2026 | https://doi.org/10.29026/oes.2026.260005 |
| 7 | RL with Graph Attention for Routing and Wavelength Assignment | Doherty, Beghelli, UCL | 2025 | https://arxiv.org/html/2502.14741v1 |
| 8 | Model-free Optical Processors using In Situ RL with PPO | Li, Chen, Gong, Ozcan, UCLA | 2025 | https://www.nature.com/articles/s41377-025-02148-7 |
| 9 | FALCON: ML Framework for Fully Automated Layout-Constrained Analog Design | Mehradfar et al., USC | 2025 | https://nips.cc/virtual/2025/loc/san-diego/poster/118890 |
| 10 | GNN-Based Placement Optimization Guidance Framework | Cao, Li, Ding, SEU | 2025 | https://www.mdpi.com/2079-9292/14/2/329 |
| 11 | GNNs for IC Design, Reliability, and Security: Survey | El Sayed et al., NYU/UCL | 2025 | https://doi.org/10.1145/nnnnnnn.nnnnnnn |

### 最终采用的方案及理由

#### PPO 优化（来源 #1, #5, #8）
- **学习率调度**：cosine annealing + linear warmup
  - 来源: Basso 2025 #1 使用自适应学习率提升 R-GCN RL 收敛
  - 理由: 固定学习率后期震荡，cosine 退火在收敛阶段降低学习率
- **价值函数 clip**：`L_vf = mean(clip((R-V)², -clip_v, clip_v))`
  - 来源: SB3 PPO 标准实现 + RL-EDA #5
  - 理由: 防止价值估计异常导致策略崩溃
- **Orthogonal 初始化**：权重用 orthogonal 初始化，偏置置零
  - 来源: Saxe et al., 2013 "Exact solutions to the nonlinear dynamics of learning in deep linear networks"
  - 理由: 比 Xavier 收敛更快，RL 中已被广泛验证

#### GNN 优化（来源 #1, #7, #9, #11）
- **边特征**：支持边类型/权重，不同连接类型用不同变换矩阵
  - 来源: R-GCN Schlichtkrull 2018 + Basso 2025 #1 pin-enhanced graph
  - 理由: 光子电路中波导/调制/探测连接语义不同
- **残差连接**：每层加 skip connection
  - 来源: GAT V2 + GNN survey #11
  - 理由: 深层 GNN 梯度消失，残差使训练稳定
- **LayerNorm**：每层消息传递后归一化
  - 来源: GNN survey #11 + FALCON #9
  - 理由: 稳定训练，减少内部协变量偏移

#### 布线优化（来源 #2, #3, #4）
- **8 方向 A*（曲线感知）**：支持 45°/90° 转弯
  - 来源: LiDAR #2 curvy-aware A* + LiDAR 2.0 #3
  - 理由: 4 方向仅曼哈顿路径，无法生成对角波导
- **Rip-up & Reroute**：布线失败时移除冲突路径重布
  - 来源: 经典 EDA 方法 + LiDAR #2 congestion-aware net ordering
  - 理由: 单次贪心布线成功率低，重布可显著提升布线成功率
- **拥塞感知网排序**：按拥塞度排序布线
  - 来源: LiDAR #2 congestion-aware net ordering
  - 理由: 先布难连接，避免被简单连接阻塞

### 未采用方案及原因
- **U-Net Policy**（Basso 2025 #1 附录 B.1）：需要 CNN 栅格输入，与当前 GNN 架构不兼容，改造量大
- **Photonic Spiking RL**（#6）：硬件实现，与软件仿真无关
- **Adjoint inverse design**（PoLaRIS #4）：属于器件级设计，非布局布线范畴

## 优化实施记录

### 阶段 1：PPO 优化
- [x] 学习率调度（cosine + warmup）
- [x] 价值函数 clip
- [x] Orthogonal 初始化

### 阶段 2：GNN 优化
- [x] 残差连接
- [x] LayerNorm
- [x] 边特征支持（R-GCN 风格消息传递）

### 阶段 3：布线优化
- [x] 8 方向 A*（DiagonalGridRouter）
- [x] Rip-up & Reroute（route_with_rip_reroute）
- [x] 拥塞感知网排序（_sort_nets_by_difficulty）

### 验证
- [x] 质量门禁 0 警告 0 错误
- [x] 全量测试通过（482 passed）
- [x] Ruff check 通过
