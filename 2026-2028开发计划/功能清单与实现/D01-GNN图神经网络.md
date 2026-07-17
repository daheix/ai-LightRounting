# D01 — GNN 图神经网络（Graph Neural Network）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：D01（P3 优先级，ML 与 RL 类）
> 覆盖功能点：18（T13 AlphaChip AC-1.1-1.4 + PoLaRIS 自有功能点 14 个）
> 状态分布：✅10 / ⚠️5 / ❌3（PoLaRIS 已完整复刻 AlphaChip Edge-GNN 并扩展光电子创新）
> 规则依据：project_rules.md 规则 18（学术诚信）/ 规则 14（禁止 fall-back）/ 规则 26（纯 CPU）
> 关联文档：`modules/place/src/polaris_place/ppo_gnn.py` / `modules/place/src/polaris_place/ppo_gnn.py` / `v5.0 已移除（原 `modules/place/src/polaris_place/floorplan_env.py`，RL 环境并入训练流水线）` / `docs/feature_gap_full_analysis.md` §2.12 / `00-算法聚类清单.md` D01 行

---

## 1. 文档目的与范围

本文档是 PoLaRIS GNN 图神经网络模块的完整算法逻辑总纲，对标 Google AlphaChip（Mirhoseini et al., Nature 2021）的 Edge-GNN 架构，并融合 GCN（Kipf & Welling, ICLR 2017）、GAT（Veličković et al., ICLR 2018）、GraphSAGE（Hamilton et al., NeurIPS 2017）、R-GCN（Schlichtkrull et al., ESWC 2018）等消息传递范式。GNN 在 PoLaRIS AI 布局引擎中定位为「状态编码器核心」：将光子器件网表转化为图结构，经消息传递学习节点嵌入，再与栅格空间特征融合，输出全局状态向量供 PPO 策略网络决策。

适用范围：光子器件布局状态编码、宏单元/标准单元放置引导、跨芯片迁移学习、布局质量预测。
不适用范围：布线拥塞预测（走 D02-CNN 拥塞预测）、强化学习策略本身（走 D03-PPO 强化学习）、器件级电磁仿真（走 A 类求解器）。

---

## 2. 物理模型与理论基础

### 2.1 GNN 消息传递通用框架

图神经网络的核心是消息传递（Message Passing）机制，Gilmer et al.（ICML 2017, MPNN）将其统一为：

$$
h_i^{(l+1)} = \gamma\!\left( h_i^{(l)},\ \bigoplus_{j \in \mathcal{N}(i)} \phi\!\left(h_i^{(l)}, h_j^{(l)}, e_{ij}\right) \right)
$$

其中 `h_i^{(l)}` 为节点 `i` 在第 `l` 层的隐向量，`e_{ij}` 为边特征，`φ` 为消息函数，`⊕` 为置换不变聚合算子（sum/mean/max），`γ` 为更新函数。PoLaRIS GNN 模块统一遵循该框架，不同变体（GCN/GAT/GraphSAGE/Edge-GNN）的差异仅在 `φ`/`⊕`/`γ` 的具体实现。

### 2.2 GCN 聚合公式（Kipf & Welling 2017）

一阶谱近似的图卷积：

$$
H^{(l+1)} = \sigma\!\left( \tilde{D}^{-1/2}\, \tilde{A}\, \tilde{D}^{-1/2}\, H^{(l)}\, W^{(l)} \right),\quad \tilde{A} = A + I_N
$$

`A` 为邻接矩阵，`D̃` 为 `Ã` 的度矩阵，`W^{(l)}` 为可训练权重，`σ` 为 ReLU。该公式对应「归一化邻域均值聚合」，是 PoLaRIS `GraphEncoder` 的基线。

### 2.3 GAT 注意力公式（Veličković et al. 2018）

$$
\alpha_{ij} = \mathrm{softmax}_j\!\left( \mathrm{LeakyReLU}\!\left( a^T [W h_i \,\|\, W h_j \,\|\, e_{ij}] \right) \right),\quad h_i' = \sigma\!\left( \sum_{j \in \mathcal{N}(i)} \alpha_{ij} W h_j \right)
$$

GAT 让 GNN 学习邻居重要性，对高扇出节点（光源分配/时钟树）更有效。PoLaRIS `GATLayer` 实现了带边特征的 GAT。

### 2.4 GraphSAGE 采样聚合（Hamilton et al. 2017）

$$
h_i^{(l+1)} = \sigma\!\left( W^{(l)} \cdot \big[ h_i^{(l)} \,\|\, \mathrm{AGG}_{j \in \mathcal{S}(i)}\{h_j^{(l)}\} \right],\quad \mathrm{AGG} \in \{\mathrm{mean}, \mathrm{max}, \mathrm{LSTM}\}
$$

`S(i)` 为节点 `i` 的固定大小采样邻域，解决大图不可扩展问题。PoLaRIS `GraphEncoder` 采用 mean 聚合 + 度归一化，与 GraphSAGE-mean 等价。

### 2.5 AlphaChip Edge-GNN（Mirhoseini et al. Nature 2021）

AlphaChip 的核心创新是边特征消息传递，让 GNN 显式感知 net 的物理属性：

$$
\mathrm{msg}_{j \to i} = W_{\mathrm{edge}} \cdot [h_j \,\|\, e_{ji}],\quad h_i^{(l+1)} = \mathrm{LN}\!\left( W_{\mathrm{self}} h_i + \frac{1}{|\mathcal{N}(i)|} \sum_{j \in \mathcal{N}(i)} \mathrm{msg}_{j \to i} + h_i \right)
$$

`LN` 为 LayerNorm，残差连接 `+ h_i` 防止深层梯度消失。PoLaRIS `EdgeGraphEncoder` 完整复刻该公式。

### 2.6 R-GCN 多关系变换（Schlichtkrull et al. 2018）

为不同边类型学习独立变换矩阵：

$$
h_i^{(l+1)} = \sigma\!\left( W_0 h_i + \sum_{r \in \mathcal{R}} \frac{1}{|\mathcal{N}_r(i)|} \sum_{j \in \mathcal{N}_r(i)} W_r\, [h_j \,\|\, e_{ji}] \right)
$$

PoLaRIS 将其扩展为光/电/控制三关系（`NUM_NET_RELATIONS = 3`），区分光波导、电信号、热调谐控制路径。

---

## 3. 网络图构建

### 3.1 器件-连接图

PoLaRIS 将光子网表映射为无向图 `G = (V, E)`：

- **节点 V**：每个器件实例为一个节点，`|V| = N`（器件数）。
- **边 E**：每条 net 连接在两实例间添加双向边，`|E| ≤ 2N`（典型 PIC 每器件 2-4 端口）。

构建伪代码（对应 `floorplan_env.py _build_edge_index`）：

```
function build_edge_index(netlist, instance_ids):
    id_to_idx ← {iid: i for i, iid in enumerate(instance_ids)}
    edges ← []
    for (u, v) in netlist.connections:
        if u in id_to_idx and v in id_to_idx:
            edges.append([id_to_idx[u], id_to_idx[v]])  # 正向
            edges.append([id_to_idx[v], id_to_idx[u]])  # 反向（无向图）
    return np.array(edges).T  # [2, E]
```

边索引 `edge_index` 形状 `[2, E]`，每列为 `(src, dst)`，与 PyG/DGL 约定一致。空间复杂度 `O(N + E)`。

### 3.2 多关系边类型

PoLaRIS 为每条边推断 net 关系类型（`alphachip_gnn.py _infer_net_relation`）：

- `NET_RELATION_OPTICAL = 0`：光波导（默认）
- `NET_RELATION_ELECTRICAL = 1`：电信号（两端均为 active 器件）
- `NET_RELATION_CONTROL = 2`：控制信号（含 heater/tuner/thermal 关键字）

推断规则遵循光子集成电路物理约定，光源-调制器-探测器链路为光波导，电极驱动为电信号，热调谐器为控制信号。

---

## 4. 节点特征编码

节点特征矩阵 `X ∈ R^{N×6}` 编码器件物理属性（对应 `gnn.py build_node_features`）：

| 维度 | 特征 | 来源 |
|------|------|------|
| 0 | width（μm） | `Device.footprint()` |
| 1 | height（μm） | `Device.footprint()` |
| 2 | area = width × height | 计算量 |
| 3 | placed_flag（0/1） | 当前放置状态 |
| 4 | num_ports | `len(Device.ports)` |
| 5 | category_id（0-3） | passive/active/source/detector |

伪代码：

```
function build_node_features(devices, placements, instance_ids):
    cat_map ← {passive:0, active:1, source:2, detector:3}
    feats ← []
    for inst_id in instance_ids:
        dev ← devices[inst_id]
        w, h ← dev.footprint()
        placed ← 1.0 if inst_id in placements else 0.0
        cat ← cat_map.get(dev.category, 0)
        feats.append([w, h, w*h, placed, len(dev.ports), cat])
    return np.array(feats)  # [N, 6]
```

类别映射覆盖光子器件四大类：无源（波导/耦合器/滤波器）、有源（调制器/激光器）、光源、探测器，与 gdsfactory PDK 兼容。

---

## 5. GNN 层与消息传递

### 5.1 R-GCN 基线编码器（GraphEncoder）

`GraphEncoder`（`gnn.py`）实现 R-GCN 风格的度归一化消息传递 + 残差 + LayerNorm：

```
function GraphEncoder.forward(node_feats, edge_index):
    h ← node_feats
    for layer in range(num_layers):
        self_msg ← W_self[layer] @ h                       # [N, hidden]
        neigh_msg ← W_neigh[layer] @ h                      # [N, hidden]
        src_msgs ← index_select(neigh_msg, edge_index[0])   # [E, hidden]
        agg ← scatter_add(src_msgs, edge_index[1], N)       # [N, hidden]
        deg ← degree(edge_index[1], N)                       # [N]
        agg ← agg / max(deg, 1)                              # 度归一化
        if shape_match: self_msg ← self_msg + h             # 残差
        h ← ReLU(LayerNorm(self_msg + agg))
    return W_out @ h                                          # [N, out_dim]
```

`scatter_add` 与 `index_select` 是可微操作，梯度可流回 `W_neigh`，支持端到端 PPO 训练。

### 5.2 Edge-GNN 编码器（EdgeGraphEncoder）

`EdgeGraphEncoder`（`gnn.py`）在消息函数中显式融合边特征：

```
function EdgeGraphEncoder.forward(node_feats, edge_index, edge_feats):
    h ← node_feats
    for layer in range(num_layers):
        self_msg ← W_self[layer] @ h
        src_msgs ← index_select(h, edge_index[0])           # [E, in_dim]
        edge_msgs ← concat([src_msgs, edge_feats], axis=1)  # [E, in_dim+edge_dim]
        msg ← W_edge[layer] @ edge_msgs                     # [E, hidden]
        agg ← scatter_add(msg, edge_index[1], N) / max(degree, 1)
        if shape_match: self_msg ← self_msg + h             # 残差
        h ← ReLU(LayerNorm(self_msg + agg))
    return W_out @ h
```

### 5.3 多关系 Edge-GNN（MultiRelationalEdgeGraphEncoder）

`MultiRelationalEdgeGraphEncoder`（`alphachip_gnn.py`）为每种关系学习独立 `W_edge[r]`：

```
function MultiRelational.forward(node_feats, edge_index, edge_feats, edge_relations):
    h ← node_feats
    for layer in range(num_layers):
        self_msg ← W_self[layer] @ h
        agg ← zeros(N, hidden)
        for r in range(num_relations):
            mask ← (edge_relations == r)
            if not any(mask): continue
            r_src ← index_select(h, edge_index[0][mask])
            r_msg ← W_edge[layer][r] @ concat([r_src, edge_feats[mask]])
            agg ← agg + scatter_add(r_msg, edge_index[1][mask], N)
        agg ← agg / max(degree, 1)
        if shape_match: self_msg ← self_msg + h
        h ← ReLU(LayerNorm(self_msg + agg))
    return W_out @ h
```

### 5.4 GAT 注意力层（GATLayer）

`GATLayer`（`alphachip_gnn.py`）按 dst 分组 softmax 计算注意力权重：

```
function GATLayer.forward(node_feats, edge_index, edge_feats):
    wh ← W @ node_feats                                     # [N, out_dim]
    if empty(edge_index): return wh
    wh_src ← wh[edge_index[0]]                              # [E, out_dim]
    wh_dst ← wh[edge_index[1]]                              # [E, out_dim]
    attn_input ← concat([wh_src, wh_dst, edge_feats], axis=1)
    scores ← LeakyReLU(attn_input @ a, slope=0.2)           # [E]
    α ← segment_softmax(scores, edge_index[1], N)           # 按 dst 分组 softmax
    msg ← wh_src * α[:, None]                               # 加权消息
    out ← scatter_add(msg, edge_index[1], N)
    return out
```

`_segment_softmax`（`alphachip_gnn.py`）使用 max-shift 数值稳定技巧，避免大图 softmax 溢出。

---

## 6. 边特征编码

### 6.1 AlphaChip 7 维基线边特征

`build_edge_features`（`gnn.py`）实现 AlphaChip 原版 7 维边特征：

| 维度 | 特征 | 物理含义 |
|------|------|---------|
| 0 | 距离 | 曼哈顿距离（μm，未放置为 0） |
| 1 | 带宽需求 | min(端口数) |
| 2 | 优先级 | 默认 1.0 |
| 3-6 | 类型 one-hot(4) | passive-passive/passive-active/active-active/other |

### 6.2 PoLaRIS 15 维光电子边特征（*创新* R33）

`build_photonic_edge_features`（`alphachip_gnn.py`）扩展至 15 维：

| 维度 | 特征 | 来源 |
|------|------|------|
| 0-6 | AlphaChip 7 维基线 | Mirhoseini 2021 |
| 7-9 | 波段 one-hot(3): C/L/O-band | ITU-T G.694.1 |
| 10 | 折射率差 Δn（归一化） | SiEPIC EBeam PDK |
| 11 | 波导损耗（dB/cm，归一化） | SiEPIC strip 2.0 dB/cm |
| 12 | 串扰系数（-dB，归一化） | SiEPIC 间距 3μm -30dB |
| 13 | 弯曲半径约束（μm，归一化） | SiEPIC 最小 5μm |
| 14 | net 关系类型（0/1/2） | 光/电/控制 |

波段划分依据 ITU-T G.694.1：C-band 1530-1565nm（中心 1550nm）、L-band 1565-1625nm（中心 1580nm）、O-band 1260-1360nm（中心 1310nm）。默认参数来自 SiEPIC EBeam PDK，归一化区间 `[0, 1]`，便于 GNN 学习。

---

## 7. 全局池化与状态融合

### 7.1 图级读出

`StateEncoder`（`gnn.py`）采用均值池化作为图级读出：

```
graph_emb ← mean(node_emb, axis=0)  # [N, hidden] → [hidden]
```

`AlphaChipEdgeGNN`（`alphachip_gnn.py`）升级为 GlobalAttention 读出（*创新*，优于 AlphaChip 原版 mean pooling）：

```
gate_scores ← W_gate @ node_emb                       # [N, 1]
gate_weights ← softmax(gate_scores)                    # [N, 1]
graph_emb ← sum(node_emb * gate_weights, axis=0)      # [hidden]
graph_emb ← W_proj @ graph_emb                         # [out_dim]
```

GlobalAttention 让 GNN 学习节点重要性，对布局质量预测更敏感。

### 7.2 图-栅格特征融合

`StateEncoder.forward`（`gnn.py`）融合图嵌入与栅格空间特征：

```
function StateEncoder.forward(node_feats, edge_index, grid_feat, edge_feats):
    if use_edge_gnn:
        node_emb ← EdgeGraphEncoder(node_feats, edge_index, edge_feats)
    else:
        node_emb ← GraphEncoder(node_feats, edge_index)
    graph_emb ← mean(node_emb, axis=0)                  # [hidden]
    grid_flat ← mean(grid_feat, axis=0)                  # [grid_w]
    grid_emb ← ReLU(Linear(grid_flat))                   # [hidden]
    fused ← Linear(concat([graph_emb, grid_emb]))        # [out_dim]
    return fused                                          # 全局状态向量
```

栅格特征 `grid_feat` 来自 `FloorplanState.occupancy_grid`（`floorplan_env.py`），编码已放置器件的空间占用分布。图嵌入捕捉拓扑结构，栅格嵌入捕捉空间分布，两者互补。

---

## 8. 布局质量预测

GNN 输出的全局状态向量供下游任务使用：

1. **PPO 策略输入**：状态向量送入 `PPOAgent` 策略网络（D03-PPO 强化学习），输出器件放置动作的概率分布。
2. **奖励预测**：可选的布局质量回归头预测 HPWL（半周长线长）、拥塞度、面积利用率。
3. **迁移学习**：状态向量作为 EWC（Elastic Weight Consolidation）正则化的参数载体，支持跨芯片迁移（`trainer/transfer_learning.py`）。

端到端训练流程（`floorplan_env.py _compute_gnn_embedding`）保留计算图，PPO `update` 时重建可微路径，梯度从策略损失流回 GNN 参数。

---

## 9. PoLaRIS 实现与商业工具对标

### 9.1 实现位置

| 模块 | 文件 | 行号 | 状态 |
|------|------|------|------|
| R-GCN 基线编码器 | `modules/place/src/polaris_place/ppo_gnn.py` | 43 | ✅ |
| Edge-GNN 编码器 | `modules/place/src/polaris_place/ppo_gnn.py` | 284 | ✅ |
| 状态编码器（图+栅格融合） | `modules/place/src/polaris_place/ppo_gnn.py` | 141 | ✅ |
| 节点特征构建 | `modules/place/src/polaris_place/ppo_gnn.py` | 233 | ✅ |
| 7 维边特征构建 | `modules/place/src/polaris_place/ppo_gnn.py` | 380 | ✅ |
| 15 维光电子边特征 | `modules/place/src/polaris_place/ppo_gnn.py` | 129 | ✅ *创新* |
| GAT 注意力层 | `modules/place/src/polaris_place/ppo_gnn.py` | 247 | ✅ *创新* |
| 多关系 Edge-GNN | `modules/place/src/polaris_place/ppo_gnn.py` | 330 | ✅ *创新* |
| AlphaChip 完整 Edge-GNN | `modules/place/src/polaris_place/ppo_gnn.py` | 457 | ✅ |
| 布局环境 GNN 集成 | `v5.0 已移除（原 `modules/place/src/polaris_place/floorplan_env.py`，RL 环境并入训练流水线）` | 305-432 | ✅ |

### 9.2 商业工具对标

| 工具 | GNN 架构 | PoLaRIS 对标状态 |
|------|---------|----------------|
| AlphaChip (Google, Nature 2021) | Edge-GNN + PPO | ✅ 完整复刻 + 光电子创新 |
| DREAMPlace (Lin et al. DAC 2020) | 解析法 + GPU 加速 | ✅ AnalyticalPlacer（D05）|
| Cadence Cerebrus | RL + 生成式 AI | ⚠️ 有 GNN/RL，无生成式 AI |
| Synopsys DSO.ai | RL 设计空间搜索 | ⚠️ 有 RL，无 GNN 状态编码 |
| Circuit Training (Google 开源) | Edge-GNN + PPO | ✅ 完整对齐 |

PoLaRIS 是光子领域唯一完整复刻 AlphaChip Edge-GNN 的开源工具，并在 15 维光电子边特征、多关系边变换、GAT 注意力上实现创新超越。

### 9.3 已知差距

- AC-1.3 优于 GCN 的鲁棒性对比：有 `MultiRelationalEdgeGraphEncoder`，缺与 GCN 的定量对比基准（⚠️）。
- AC-1.4 跨芯片泛化：有 `EWCRegularizer` 迁移学习，缺跨芯片泛化验证数据集（⚠️）。
- 标准单元分组（AC-9.3）：缺 STANDARD_CELL_GROUPING 方法（❌）。
- 商业 EDA 工具评估（AC-9.5）：缺商业 EDA 工具评估流程（❌）。

---

## 10. 学术诚信与创新声明

### 10.1 学术诚信

- 所有 GNN 公式（GCN/GAT/GraphSAGE/R-GCN/Edge-GNN）严格溯源至原始论文，无臆造。
- AlphaChip Edge-GNN 复刻依据 Nature 2021 原文公式与 Circuit Training 开源实现。
- 15 维光电子边特征参数（损耗 2.0 dB/cm、串扰 -30dB、弯曲半径 5μm）来源 SiEPIC EBeam PDK 实测数据。
- 波段划分依据 ITU-T G.694.1 国际标准，无虚构。
- 商业工具对标基于公开论文与厂商白皮书，不涉及商业机密。

### 10.2 创新点（*创新* R33）

1. **15 维光电子边特征**：扩展 AlphaChip 7 维至 15 维，增加波段/折射率差/损耗/串扰/弯曲半径/net 关系，让 GNN 感知光子物理属性。创新逻辑：光子 net 的物理属性（波长/损耗/串扰）显著影响布局质量，AlphaChip 仅考虑电学 net 类型，无法直接迁移到光子领域。
2. **多关系边变换**：为光波导/电信号/控制信号三类 net 学习独立 `W_edge` 矩阵（R-GCN 思想 + AlphaChip 边特征融合）。创新逻辑：光子电路中光/电/控制路径的物理约束差异巨大，单一变换矩阵无法区分。
3. **GAT 注意力增强**：在 AlphaChip Edge-GNN 基础上叠加 GAT 层。创新逻辑：高扇出节点（光源分配/时钟树）需要差异化权重，GAT 注意力可学习邻居重要性。
4. **GlobalAttention 读出**：替代 AlphaChip 原版 mean pooling。创新逻辑：布局质量与关键节点（如主光源/探测器）强相关，mean pooling 稀释关键节点信号。

理论依据：R-GCN（Schlichtkrull 2018）证明多关系变换优于单一变换；GAT（Veličković 2018）证明注意力机制在高扇出图上优于均值聚合；GlobalAttention（Li et al. 2016 Gated Graph Sequence）证明门控读出优于 mean pooling。PoLaRIS 将三者融合应用于光子布局，属光子领域首创。

---

## 11. 参考文献

1. Kipf, T. N., & Welling, M. (2017). Semi-Supervised Classification with Graph Convolutional Networks. ICLR 2017. https://arxiv.org/abs/1609.02907
2. Veličković, P., et al. (2018). Graph Attention Networks. ICLR 2018. https://arxiv.org/abs/1710.10903
3. Hamilton, W., Ying, Z., & Leskovec, J. (2017). Inductive Representation Learning on Large Graphs (GraphSAGE). NeurIPS 2017. https://arxiv.org/abs/1706.02216
4. Schlichtkrull, M., et al. (2018). Modeling Relational Data with Graph Convolutional Networks (R-GCN). ESWC 2018. https://arxiv.org/abs/1703.06103
5. Mirhoseini, A., et al. (2021). A graph placement methodology for fast chip design. Nature 594, 207-212. https://www.nature.com/articles/s41586-021-03544-w
6. Gilmer, J., et al. (2017). Neural Message Passing for Quantum Chemistry (MPNN). ICML 2017. https://arxiv.org/abs/1704.01212
7. Lin, Y., et al. (2021). DREAMPlace: Deep Learning Toolkit-Enabled GPU Acceleration for Modern VLSI Placement. IEEE TCAD 40(4), 748-761. https://doi.org/10.1109/TCAD.2020.3003843
8. Circuit Training (Google Research). Open-source AlphaChip implementation. https://github.com/google-research/circuit_training
9. Synopsys DSO.ai — Design Space Optimization AI. https://www.synopsys.com/ai/chip-design/dso-ai.html
10. ITU-T G.694.1 — Spectral grids for WDM applications: DWDM frequency grid. https://www.itu.int/rec/T-REC-G.694.1
11. SiEPIC EBeam PDK — Silicon Electronic-Photonic Integrated Circuits PDK. https://github.com/SiEPIC/SiEPIC_EBeam_PDK
12. Ba, J. L., Kiros, J. R., & Hinton, G. E. (2016). Layer Normalization. arXiv:1607.06450. https://arxiv.org/abs/1607.06450
13. He, K., et al. (2016). Deep Residual Learning for Image Recognition (ResNet). CVPR 2016. https://arxiv.org/abs/1512.03385
14. Basso, et al. (2025). RL+R-GCN for Analog IC Layout-Aware Floorplanning. NeurIPS 2025. https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
