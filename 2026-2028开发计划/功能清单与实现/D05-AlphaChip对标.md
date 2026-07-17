# D05 — AlphaChip 对标：从网表图构建到光子器件放置的完整算法逻辑

| 项目 | 内容 |
|------|------|
| 聚类 ID | D05 |
| 类别 | ML / RL（机器学习与强化学习） |
| 覆盖功能点数 | 38（T13 AlphaChip 12 章节 + T12 Cadence/Synopsys 对标项） |
| 涉及工具 | T13 Google AlphaChip / Circuit Training、PoLaRIS、T12 Cadence Innovus + Synopsys ICC2（部分） |
| 状态分布 | ✅14 / ⚠️8 / ❌16（含 TPU/MediaTek 10 项 🚫不适用） |
| PoLaRIS 实现位置 | `modules/place/src/polaris_place/ppo_gnn.py`、`modules/trainer/src/polaris_trainer/ppo.py`、`v5.0 已移除（原 `modules/place/src/polaris_place/floorplan_env.py`，RL 环境并入训练流水线）`、`modules/place/src/polaris_place/analytical.py`、`modules/nn/src/polaris_nn/data/benchmark_evaluator.py` |
| 文档版本 | v1.0（2026-06-25） |
| 文档作者 | PoLaRIS 算法文档工程组 |
| 学术诚信声明 | 全部公式、文献来源、固定参数均明确标注；*创新* 点已显式标记并附底层逻辑与理论支持。 |

> 本文档对标 Google DeepMind AlphaChip（Mirhoseini et al., Nature 2021；Goldie & Mirhoseini 2024 Nature addendum）与开源实现 Circuit Training，给出 PoLaRIS 在光电子布局布线场景下的完整算法逻辑、核心公式与伪代码。光子版 AlphaChip 的关键差异：**器件级放置（macro placement 退化为器件放置）+ 多关系边图编码（光/电/控制三关系）+ GAT 注意力增强**，详见第 9 章。

---

## 1. 概述

### 1.1 AlphaChip 算法定位

AlphaChip 是 Google DeepMind 提出的基于深度强化学习的芯片布局方法，将芯片 floorplanning 视为序贯决策问题：从空白网格开始，每次放置一个电路模块（macro），所有模块放置完毕后依据最终布局质量给出奖励。其核心三件套为：

1. **Edge-GNN（基于边的图神经网络）**：编码 netlist 拓扑与已放置状态，输出可泛化的图嵌入；
2. **PPO（近端策略优化）策略网络**：基于 GNN 嵌入输出动作分布（放置到哪个网格）；
3. **预训练 + 微调**：在前代 TPU 多个模块上预训练，迁移到当前模块加速收敛。

AlphaChip 已用于 Google TPU v5e / v5p / Trillium 三代旗舰芯片及 Axion 数据中心 CPU，6 小时内生成超人/可比水平布局。

### 1.2 PoLaRIS 对标定位

PoLaRIS 是光电子 AI 布局布线引擎，将 AlphaChip 范式迁移到光子电路（PIC）。两者差异：

| 维度 | AlphaChip（电子） | PoLaRIS（光子） |
|------|------------------|----------------|
| 放置对象 | 宏单元 + 标准单元簇 | 光子器件（MZI、波导、调制器、探测器等） |
| 网表边类型 | 单一 net 类型 | 三关系：光波导 / 电信号 / 控制信号（*创新* R-GCN） |
| 边特征维度 | 7 维 | 15 维（波段、折射率、损耗、串扰、弯曲半径，*创新* R33） |
| 注意力机制 | 无显式注意力 | GAT 注意力层（*创新* R33） |
| 部署平台 | TPU v5e/v5p/Trillium | 100% CPU 纯 Python（规则 26：不参与 GPU） |
| 商业采用 | TPU/MediaTek Dimensity | 不适用（🚫，开源光子项目） |

---

## 2. 算法原理与整体流程

AlphaChip 的整体流程：**网表图构建 → Edge-GNN 编码 → PPO 策略采样 → 放置解码 → 代价评估 → 奖励反馈**。在 PoLaRIS 中扩展为：

```
光子网表（CircuitSpec）→ 器件-连接图构建（边特征 15 维）
    ↓
Edge-GNN 编码（多关系 + GAT + GlobalAttention）
    ↓
PPO Actor-Critic 采样动作（网格位置 + 旋转）
    ↓
FloorplanEnv 步进 + 放置代价评估（HPWL + 拥塞 + 密度 + 重叠 + 间距）
    ↓
DREAMPlace 解析法 warm-start（标准单元/小器件粗放置）
    ↓
奖励反馈 → GAE 优势估计 → PPO-clip 策略更新
    ↓
CheckpointManager 保存模型 → 迁移学习（EWC + 课程学习）
```

整体是典型的 **Model-free Policy Gradient RL** 范式，与 AlphaGo/AlphaZero 同源，但状态空间从棋盘替换为芯片/光子画布网格。

---

## 3. 网表图构建

### 3.1 从 netlist 到 graph

AlphaChip 将芯片 netlist（hypergraph，节点 = macro/standard cell cluster，超边 = net）转换为简单图：每条超边被拆分为两两相连的边。PoLaRIS 直接使用 `CircuitSpec.connections` 中已显式给出的器件-端口-器件二元连接，构建无向图。

### 3.2 节点特征

每个节点（光子器件）特征向量维度由 `polaris.engine.gnn` 定义，包括：器件类别 one-hot（passive/active/source/detector/modulator/heater/...）、宽高、端口数、当前是否已放置、当前位置（归一化）。

### 3.3 边特征（PoLaRIS 15 维 *创新* R33）

来源：`modules/place/src/polaris_place/ppo_gnn.py` `PHOTONIC_EDGE_DIM = 15`

| 索引 | 含义 | 来源 / 默认值 |
|------|------|---------------|
| [0] | 曼哈顿距离（μm） | 已放置时由 placement 中心坐标差计算 |
| [1] | 带宽需求 | min(源端口数, 宿端口数) |
| [2] | 优先级 | 默认 1.0 |
| [3-6] | 类型 one-hot(4) | passive-passive / passive-active / active-active / other |
| [7-9] | 波段 one-hot(3) | ITU-T G.694.1：C-band 1530-1565nm / L-band 1565-1625nm / O-band 1260-1360nm |
| [10] | 折射率差 Δn（归一化 [0,1]） | SiEPIC EBeam PDK strip neff=2.4 |
| [11] | 波导损耗（dB/cm，归一化 [0,1]，上限 10） | SiEPIC EBeam PDK strip 2.0 dB/cm |
| [12] | 串扰系数（-dB，归一化 [0,1]，上限 40） | SiEPIC EBeam PDK 间距 3μm 时 -30dB |
| [13] | 弯曲半径约束（μm，归一化 [0,1]，上限 50） | SiEPIC EBeam PDK 最小 5μm |
| [14] | net 关系类型 | 0=光波导 / 1=电信号 / 2=控制信号 |

*创新*：AlphaChip 仅 7 维（距离/带宽/优先级/类型 one-hot），PoLaRIS 扩展至 15 维，将光子物理特性（波段、折射率、损耗、串扰、弯曲半径）显式编码进边特征，使 GNN 能感知光子信号传输的物理约束。

### 3.4 多关系边推断

`_infer_net_relation`（`alphachip_gnn.py`）规则：
- 任一端含 `heater`/`tuner`/`thermal` 关键字 → 控制信号（关系 2）；
- 两端均 `active` 类 → 电信号（关系 1）；
- 其他 → 光波导（关系 0，默认）。

---

## 4. Edge-GNN 编码器架构

### 4.1 AlphaChip Edge-GNN 消息传递公式

AlphaChip Nature 2021 提出的 Edge-GNN 节点更新公式（伪 W = 节点变换、W_e = 边变换）：

```
msg_{j→i} = W_e · concat(h_j, e_{ji})
h_i^{(l+1)} = LayerNorm( W_self · h_i + (1/|N(i)|) · Σ_{j∈N(i)} msg_{j→i} + h_i )   # 残差
```

### 4.2 PoLaRIS 多关系扩展公式（*创新* R33）

来源：`MultiRelationalEdgeGraphEncoder`（`alphachip_gnn.py`），依据 Schlichtkrull et al. ESWC 2018 R-GCN。

为不同 net 关系（光/电/控制）学习独立的边变换矩阵 `W_edge[r]`：

```
msg_{j→i}^{(r)} = W_edge[r] · concat(h_j, e_{ji})
h_i^{(l+1)} = LayerNorm( W_self · h_i
                        + (1/|N(i)|) · Σ_{(j,r,e)∈N(i)} msg_{j→i}^{(r)}
                        + h_i )
```

*创新* 底层逻辑：光波导（低损耗、单模）与电信号（高速、阻抗匹配）与控制信号（热调谐、慢变）的物理特性差异巨大，单一 W_edge 无法捕捉；多关系变换借鉴知识图谱 R-GCN 思路，为每类关系学独立参数。理论支持：R-GCN 在关系预测任务上较单关系 GCN 平均提升 5-10%（Schlichtkrull 2018）。

### 4.3 GAT 注意力增强（*创新* R33）

来源：`GATLayer`（`alphachip_gnn.py`），依据 Veličković et al. ICLR 2018。

注意力计算公式：

```
α_{ij} = softmax_j( LeakyReLU( a^T · [W h_i ‖ W h_j ‖ e_{ij}] ) )
h_i'   = σ( Σ_{j∈N(i)} α_{ij} · W h_j )
```

PoLaRIS 在 Edge-GNN 层后交替堆叠 GAT 层（默认 num_layers=2），让高扇出节点（光源分配树、时钟/控制总线）的邻居重要性由注意力权重自适应学习，而非均等聚合。

### 4.4 图级读出：GlobalAttention

AlphaChip 原文使用 mean pooling；PoLaRIS 改用 GlobalAttention（*创新* R33，`alphachip_gnn.py`）：

```
gate_i  = softmax_i( v_gate^T · h_i )           # 节点重要性门控
h_graph = Σ_i gate_i · h_i                       # 加权聚合
h_out   = W_proj · h_graph                       # 输出投影
```

---

## 5. PPO 策略与价值网络

### 5.1 MDP 建模

来源：`FloorplanEnv`（`v5.0 已移除（原 `modules/place/src/polaris_place/floorplan_env.py`，RL 环境并入训练流水线）:157`），Gymnasium 接口。

| 要素 | 定义 |
|------|------|
| 状态 s_t | 当前画布占用栅格 + 已放置器件图嵌入（Edge-GNN 输出）+ 当前待放置器件 ID 嵌入 |
| 动作 a_t | (grid_row, grid_col, rotation) 三元组，rotation ∈ {0, 90, 180, 270} |
| 转移 T | 将当前器件放置到指定网格 + 旋转，更新画布占用 |
| 奖励 r_t | 0（中间步），终止步 r_T = −(w_wl·HPWL + w_cg·拥塞 + w_dn·密度 + w_ov·重叠 + w_sp·间距违规)（来源：`reward_shaping.py`） |
| 终止 | 所有器件放置完毕或非法动作 |

### 5.2 Actor-Critic 网络

来源：`ActorCritic`（`modules/trainer/src/polaris_trainer/ppo.py`）。

```
共享编码器：obs → Linear → ReLU → Linear → ReLU → feats
策略头：feats → Linear → action_mean (μ)        # 高斯均值
         action_log_std 为可学习参数 (σ)
价值头：feats → Linear → value (V(s))
动作采样：a ~ N(μ, σ²)
```

### 5.3 PPO 更新核心公式

来源：Schulman et al. 2017（https://arxiv.org/abs/1707.06347），`ppo.py` 实现。

**GAE 优势估计**（Schulman et al. 2015, https://arxiv.org/abs/1506.02438）：

```
δ_t      = r_t + γ · V(s_{t+1}) − V(s_t)
A_t^GAE  = Σ_{l=0}^{T-t} (γλ)^l · δ_{t+l}
R_t      = A_t^GAE + V(s_t)                     # 价值回归目标
```

**PPO-clip 策略损失**：

```
r_t(θ) = exp( log π_θ(a_t|s_t) − log π_θ_old(a_t|s_t) )
L_CLIP = − mean( min( r_t · A_t,  clip(r_t, 1−ε, 1+ε) · A_t ) )
```

**总损失**：

```
L = L_CLIP + c_vf · (V(s_t) − R_t)² − c_ent · H(π_θ)
```

PoLaRIS 默认超参（与 Stable-Baselines3 对齐）：γ=0.99, λ=0.95, ε=0.2, ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5, n_epochs=4, batch_size=64, lr=3e-4。来源：`PPOConfig`（`ppo.py`）。

### 5.4 与 AlphaChip TF-Agents 实现的差异

PoLaRIS 使用纯 NumPy + 自研 `polaris.nn` 模块复刻 PPO，非 TF-Agents。原因：规则 26 不参与 GPU/TF 重型依赖，保证 100% CPU 纯 Python 可运行；算法逻辑等价。

---

## 6. 放置代价函数

### 6.1 HPWL（半周长线长）

来源：`evaluate_hpwl`（`modules/nn/src/polaris_nn/data/benchmark_evaluator.py`），EDA 教材标准。

```
HPWL = Σ_{net} ( max(x_pins) − min(x_pins) + max(y_pins) − min(y_pins) )
```

PoLaRIS 简化为二元连接的曼哈顿距离之和（光子电路连接以二元为主，少数多端口器件展开为二元对）。

### 6.2 拥塞评估

来源：`evaluate_congestion`（`benchmark_evaluator.py`），LRT（Logistic Routing Trend）模型。

```
Congestion_b = Σ_n (usage_n(b) / capacity_b)
```

将画布划分为布线网格，对每个网格 bin 计算穿过该 bin 的 net 数量除以 bin 容量。

### 6.3 密度场

来源：`DensityField`（`modules/place/src/polaris_place/metrics.py`），DREAMPlace 网格化密度场。

```
ρ(x,y) = Σ_i area_i · K_σ(x − x_i, y − y_i)       # 高斯核卷积
```

K_σ 为带宽 σ 的高斯核，模拟 ePlace 电势场。

### 6.4 重叠与间距违规

来源：`floorplan_geometry.count_overlaps` / `count_spacing_violations`。

- 重叠：两器件 bbox 相交面积 > 0；
- 间距：两器件 bbox 间曼哈顿距离 < 最小间距规则（PDK 定义）。

### 6.5 终止步奖励（负加权和）

来源：`ExpertRewardShaper`（`v5.0 已移除（原 `modules/trainer/src/polaris_trainer/reward_shaping.py`，奖励整形未迁移）:289`），与 AlphaChip AC-10.1 一致：

```
r_T = −( w_wl · HPWL_norm + w_cg · Congestion_norm
       + w_dn · Density_norm + w_ov · Overlap_count
       + w_sp · Spacing_violation + w_th · Thermal_hotspot )
```

PoLaRIS 额外加入 `w_th`（热热点惩罚，*创新*，对激光器/调制器等热源器件间距加权）。

---

## 7. 标准单元放置与 DREAMPlace 集成

来源：`AnalyticalPlacer`（`modules/place/src/polaris_place/analytical.py`），DREAMPlace DAC 2019 / TCAD 2020。

**平滑 HPWL（log-sum-exp 近似）**（γ→0 时趋近真实 HPWL，DREAMPlace 默认 γ=4.0）：

```
WL_LSE(x) = γ · log( Σ_i exp(x_i / γ) ) − γ · log( Σ_i exp(−x_i / γ) )
```

**密度惩罚（ePlace 电势场，高斯核 K_σ 卷积）**：

```
D(x,y) = Σ_i area_i · K_σ(x − x_i, y − y_i)
min_{x,y}  WL_LSE(x,y) + (λ/2) · ∫ D(x,y)² dx dy
```

**Adam 优化器**（Kingma & Ba 2014）：`m_t = β_1·m_{t-1} + (1−β_1)·g_t`；`v_t = β_2·v_{t-1} + (1−β_2)·g_t²`；`θ_t = θ_{t-1} − lr·m_t / (√v_t + ε)`。

PoLaRIS 默认 lr=0.01, max_iter=200, density_weight=1e-3, gamma=4.0（`AnalyticalPlacerConfig`）。PoLaRIS 采用 AlphaChip 同款混合策略：RL 放置宏器件/光子器件，解析法 warm-start 小器件粗放置，再由 RL 微调。

---

## 8. PoLaRIS 光子版 AlphaChip 对标差异

| 差异点 | AlphaChip（电子） | PoLaRIS（光子） | 详见章节 |
|--------|------------------|----------------|----------|
| 放置对象 | macro + standard cell cluster | 器件级 PCell（MZI/波导/调制器/探测器），单层放置 + 力导向粗化 | 8.1 |
| 边类型 | 单一 net 类型 | 三关系 R-GCN（光/电/控制） | 3.3-3.4, 4.2 |
| 注意力 | 无显式注意力 | GAT 注意力层 | 4.3 |
| 图读出 | mean pooling | GlobalAttention 门控读出 | 4.4 |
| 代价扩展 | HPWL + 拥塞 + 密度 + 重叠 + 间距 | 额外：插入损耗 / 热热点 / 弯曲半径违规 / 端口对齐奖励（`benchmark_evaluator.py` 第 90 轮 + `reward_shaping.py`） | 6.5 |
| 平台 | TPU v5e/v5p/Trillium | 100% CPU 纯 Python | 规则 26 |

### 8.1 不适用项（🚫）

| 项 | 原因 |
|----|------|
| AC-4.1 多 GPU 分布式训练 | 规则 26：PoLaRIS 不参与 GPU 计算 |
| AC-4.6 8-GPU global batch=1024 | 同上 |
| AC-5.1-5.7 TPU 部署 | 开源光子项目无 TPU |
| AC-6.1-6.3 MediaTek 商业采用 | 无商业芯片部署 |

CPU 端保留 `DistributedLearner`（CTDE 中心化训练分布式执行，`distributed_learner.py`），覆盖 AC-4.2 / AC-4.5。

---

## 9. 端到端完整伪代码

```python
# === PoLaRIS AlphaChip 端到端流程（光子版） ===

# 1. 网表图构建
circuit = load_photonic_netlist("mzi_lattice.pic")            # CircuitSpec
devices, placements_init, instance_ids, edge_index = build_graph(circuit)
edge_feats = build_photonic_edge_features(                     # 15 维边特征
    devices, placements_init, instance_ids, edge_index,
    config=PhotonicEdgeFeatureConfig(default_wavelength_um=1.55))
edge_relations = edge_feats[:, 14].astype(int)                 # 多关系

# 2. Edge-GNN 编码器（多关系 + GAT + GlobalAttention）
gnn = AlphaChipEdgeGNN(in_dim=NODE_DIM, edge_feat_dim=15,
                       hidden_dim=64, out_dim=64, num_layers=2,
                       use_gat=True, use_multi_relation=True)
graph_emb = gnn(Tensor(node_feats), edge_index,
                Tensor(edge_feats), edge_relations)            # [out_dim]

# 3. PPO Actor-Critic
actor_critic = ActorCritic(obs_dim=64, action_dim=3, hidden_dim=64)  # (row, col, rot)
ppo_cfg = PPOConfig(lr=3e-4, gamma=0.99, gae_lambda=0.95,
                    clip_eps=0.2, n_epochs=4, batch_size=64)
optimizer = Adam(actor_critic.parameters(), lr=ppo_cfg.lr)

# 4. RL 环境
env = FloorplanEnv(circuit=circuit, canvas_w=1000, canvas_h=1000,
                   grid_size=10.0)

# 5. 预训练（前代网表）
pretrain_dataset = PretrainDataset(checkpoints_dir="ckpt/pretrain/")
for prev_netlist in pretrain_dataset:
    train_ppo_one_block(gnn, actor_critic, env, prev_netlist, ppo_cfg)
CheckpointManager.save(gnn, actor_critic, path="ckpt/alphachip_pretrain.ckpt")

# 6. 微调当前网表（EWC 防遗忘 + 课程学习）
finetuner = FineTuner(gnn, actor_critic, ewc=EWCRegularizer(lambda_=0.4))
curriculum = CurriculumScheduler(stages=[(10, "easy"), (50, "medium"), (200, "hard")])

# 7. 主训练循环
for stage_steps, stage_name in curriculum.stages:
    for rollout_idx in range(stage_steps):
        rollout = RolloutBuffer()
        obs, _ = env.reset()
        done = False
        while not done:
            # === Edge-GNN 编码当前状态 ===
            node_feats_t = env.observe_node_feats()
            edge_feats_t = env.observe_edge_feats()
            graph_emb_t = gnn(Tensor(node_feats_t), env.edge_index,
                              Tensor(edge_feats_t), env.edge_relations)
            # === PPO 采样动作 + 环境步进 ===
            action, logprob, value = actor_critic.get_action(graph_emb_t.data)
            obs, reward, done, info = env.step(action)
            rollout.append(obs=graph_emb_t.data, action=action,
                           reward=reward, logprob=logprob, value=value, done=done)
        # === GAE 优势估计 + PPO-clip 多 epoch 更新 ===
        rollout = compute_gae(rollout, gamma=ppo_cfg.gamma,
                              lambda_=ppo_cfg.gae_lambda)
        for epoch in range(ppo_cfg.n_epochs):
            for batch in minibatches(rollout, ppo_cfg.batch_size):
                new_logprob, new_value, entropy = actor_critic.evaluate(
                    batch.obs, batch.actions)
                ratio = np.exp(new_logprob − batch.logprobs)
                surr1 = ratio * batch.advantages
                surr2 = np.clip(ratio, 1−ppo_cfg.clip_eps, 1+ppo_cfg.clip_eps) \
                        * batch.advantages
                L_clip = −np.mean(np.minimum(surr1, surr2))
                L_vf   = np.mean((new_value − batch.returns) ** 2)
                L_ent  = np.mean(entropy)
                loss   = L_clip + ppo_cfg.vf_coef * L_vf − ppo_cfg.ent_coef * L_ent
                optimizer.zero_grad(); loss.backward()
                clip_grad_norm_(actor_critic, ppo_cfg.max_grad_norm)
                optimizer.step()
        finetuner.ewc_penalty_update()                          # EWC 防遗忘

# 8. DREAMPlace warm-start 小器件粗放置
placer = AnalyticalPlacer(config=AnalyticalPlacerConfig(
    gamma=4.0, density_weight=1e-3, learning_rate=0.01, max_iterations=200))
coarse_placements = placer.place(circuit, env.placements)       # 连续坐标

# 9. 评估
result = evaluate_benchmark(circuit, coarse_placements,
                            target_metric="HPWL")
print(f"HPWL={result.hpwl_um}μm  overlap={result.overlap_count}  "
      f"util={result.area_utilization:.2%}")
assert result.passed, "布局未达标，禁止带病提交（规则：禁止带病提交代码）"

# 10. 保存检查点
CheckpointManager.save(gnn, actor_critic, path="ckpt/alphachip_final.ckpt")
```

---

## 10. 学术评估与基准

### 10.1 TILOS MacroPlacement 基准（AC-12.1 ✅）

来源：`load_ariane_benchmark`（`modules/nn/src/polaris_nn/data/tilos_benchmark.py`）。PoLaRIS 加载 TILOS Ariane RISC-V 基准（17 模块），与 Circuit Training 公开结果对齐验证。

### 10.2 缺失项（待补齐）

| 项 | 状态 | 计划 |
|----|------|------|
| IEEE TCAD 评估论文（AC-12.2） | ❌ | 2027 Q1 投稿 |
| sub-10nm 基准发布（AC-12.3） | ❌ | 光子不适用，转 130nm/220nm SOI 基准 |
| CT 与 Nature 差异研究（AC-12.4） | ❌ | 2027 Q2 复现 |
| SA 基线增强（AC-12.5） | ❌ | 2026 Q4 实现 |

### 10.3 学术诚信承诺

所有数据来源标注至源文件行号；固定参数（SiEPIC EBeam PDK 默认值、PPO 超参）标注来源；*创新* 点（多关系边、GAT、光子物理代价）显式标记并附理论支持。

---

## 11. 文献与参考

| 编号 | 文献 | URL |
|------|------|-----|
| [1] | Mirhoseini et al., "A graph placement methodology for fast chip design", Nature 2021 | https://www.nature.com/articles/s41586-021-03544-w |
| [2] | Goldie & Mirhoseini, "How AlphaChip transformed computer chip design", DeepMind Blog 2024 | https://deepmind.google/blog/how-alphachip-transformed-computer-chip-design/ |
| [3] | Mirhoseini et al., Nature 2024 addendum（AlphaChip 模型权重开源） | https://www.nature.com/articles/s41586-024-08032-5 |
| [4] | Circuit Training 开源仓库（TF-Agents 实现） | https://github.com/google-research/circuit_training |
| [5] | Schulman et al., "Proximal Policy Optimization Algorithms", 2017 | https://arxiv.org/abs/1707.06347 |
| [6] | Schulman et al., "High-Dimensional Continuous Control Using GAE", 2015 | https://arxiv.org/abs/1506.02438 |
| [7] | Schlichtkrull et al., "Modeling Relational Data with GCN", ESWC 2018 | https://arxiv.org/abs/1703.06103 |
| [8] | Veličković et al., "Graph Attention Networks", ICLR 2018 | https://arxiv.org/abs/1710.10903 |
| [9] | Lin et al., "DREAMPlace: Deep Learning Toolkit-Enabled GPU Acceleration for Modern VLSI Placement", DAC 2019 | https://dl.acm.org/doi/10.1145/3316781.3317803 |
| [10] | TILOS-AI MacroPlacement 基准与复现 | https://tilos-ai-institute.github.io/MacroPlacement/ |
| [11] | ITU-T G.694.1 光通信波段划分（C/L/O-band） | https://www.itu.int/rec/T-REC-G.694.1 |
| [12] | SiEPIC EBeam PDK（边特征默认值来源） | https://github.com/SiEPIC/SiEPIC_EBeam_PDK |
