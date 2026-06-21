"""GNN 状态编码器（Task 10 + 2025 增强 + edge-GNN 2026）。

实现器件-连接图的图神经网络编码（消息传递 GNN），融合栅格空间特征。
torch 无法安装时，使用 ``polaris.nn`` 纯 NumPy 复刻实现（规则 3）。

方法参考：
- R-GCN（关系图卷积网络）Schlichtkrull et al., 2018
  来源: https://arxiv.org/abs/1703.06103
- Basso et al., NeurIPS 2025（RL+R-GCN 模拟 IC 布局感知 floorplanning）
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- PyTorch Geometric MessagePassing
  来源: https://pytorch-geometric.readthedocs.io/

2025 增强（来源: Basso 2025 + GNN survey El Sayed 2025）:
- 残差连接: 每层 skip connection，防止深层梯度消失
  来源: He et al., 2016 ResNet https://arxiv.org/abs/1512.03385
- LayerNorm: 每层归一化，稳定训练
  来源: Ba et al., 2016 https://arxiv.org/abs/1607.06450
- 边特征: 支持边类型，不同连接用不同变换矩阵
  来源: R-GCN Schlichtkrull 2018 + Basso 2025 pin-enhanced graph

2026 edge-GNN（来源: AlphaChip Nature 2021 + Circuit Training）:
- 边特征消息传递: h_i^{l+1} = W_self @ h_i + sum_{(j,e) in N(i)} W_edge[e] @ (h_j || e)
- 来源: Mirhoseini et al., Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- 来源: Circuit Training, https://github.com/google-research/circuit_training

消息传递公式（与 R-GCN/GraphSAGE 一致，含残差 + LayerNorm）::

    h_i^{l+1} = LayerNorm( W_self @ h_i^l
                          + (1/|N|) * sum_{j in N(i)} W_neigh @ h_j^l
                          + h_i^l )  # 残差
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.nn import LayerNorm, Linear, Module, ReLU, Sequential, Tensor


class GraphEncoder(Module):
    """器件-连接图 GNN 编码器（消息传递，复刻 R-GCN + 2025 增强）。

    输入：节点特征矩阵 ``[N, in_dim]`` + 边列表 ``[2, E]``。
    输出：节点嵌入 ``[N, hidden_dim]``。

    采用 R-GCN 风格的消息传递 + 残差连接 + LayerNorm：
    每个节点聚合邻居特征后经线性变换 + ReLU + LayerNorm + 残差。
    """

    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 64,
        out_dim: int = 64,
        num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.num_layers = num_layers
        self.self_linears: list[Linear] = []
        self.neigh_linears: list[Linear] = []
        self.norms: list[LayerNorm] = []
        dim = in_dim
        for _ in range(num_layers):
            self.self_linears.append(Linear(dim, hidden_dim))
            self.neigh_linears.append(Linear(dim, hidden_dim))
            self.norms.append(LayerNorm(hidden_dim))
            dim = hidden_dim
        self.out_proj = Linear(hidden_dim, out_dim)
        self.relu = ReLU()

    def forward(self, node_feats: Tensor, edge_index: np.ndarray) -> Tensor:
        """前向消息传递（含残差 + LayerNorm）。

        Args:
            node_feats: 节点特征 ``[N, in_dim]``。
            edge_index: 边索引 ``[2, E]``（每列 (src, dst)）。

        Returns:
            节点嵌入 ``[N, out_dim]``。
        """
        from polaris.nn import index_select, scatter_add

        h = node_feats
        n = h.shape[0]
        for layer in range(self.num_layers):
            self_msg = self.self_linears[layer](h)  # [N, hidden]
            # 邻居聚合：对每条边 src->dst，将 src 特征累加到 dst
            neigh_msg = self.neigh_linears[layer](h)  # [N, hidden]
            srcs = edge_index[0]
            dsts = edge_index[1]
            hidden = self.self_linears[layer].out_features
            if len(srcs) > 0:
                # 可微 index_select + scatter_add：
                # 梯度路径 agg -> scatter_add -> src_msgs -> index_select
                #   -> neigh_msg -> neigh_linears 参数
                src_msgs = index_select(neigh_msg, srcs)  # [E, hidden]
                agg = scatter_add(src_msgs, dsts, n)  # [n, hidden]
                # 度归一化（与 R-GCN 一致）
                deg = np.zeros(n)
                np.add.at(deg, dsts, 1.0)
                deg = np.maximum(deg, 1.0)
                agg = agg * Tensor(1.0 / deg[:, None])
            else:
                agg = Tensor(np.zeros((n, hidden)))
            # 残差连接：当输入输出维度一致时加 skip
            if h.shape[-1] == self_msg.data.shape[-1]:
                self_msg = self_msg + h
            # LayerNorm + ReLU
            h = self.relu(self.norms[layer](self_msg + agg))
        return self.out_proj(h)


@dataclass
class EncoderConfig:
    """状态编码器超参配置（规则 4：参数分组降低函数参数数）。

    将 ``hidden_dim``/``out_dim``/``num_gnn_layers`` 聚合为单一配置对象，
    使 ``StateEncoder.__init__`` 参数数低于警告阈值。

    Attributes:
        hidden_dim: GNN 隐藏维度与栅格投影维度。
        out_dim: 融合层输出维度（全局状态向量维度）。
        num_gnn_layers: GNN 消息传递层数。
        use_edge_gnn: 是否启用 edge-GNN（AlphaChip 风格边特征消息传递）。
            默认 False（向后兼容）。True 时用 EdgeGraphEncoder 替代 GraphEncoder。
            来源: Mirhoseini et al., Nature 2021, P1-1 差距修复。
        edge_feat_dim: 边特征维度（仅 use_edge_gnn=True 时生效），默认 7
            （[距离, 带宽, 优先级, 类型 one-hot(4)]）。
    """

    hidden_dim: int = 64
    out_dim: int = 128
    num_gnn_layers: int = 2
    use_edge_gnn: bool = False
    edge_feat_dim: int = 7


class StateEncoder(Module):
    """状态编码器：融合图特征（GNN）与栅格空间特征。

    将器件连接图经 GNN 编码为节点嵌入，再与栅格空间特征（占用/拥塞）
    拼接，输出全局状态向量供 PPO 策略网络使用。

    参考 Basso et al. NeurIPS 2025：图特征 + 空间特征融合。

    第4轮 P1-1 增强：支持 edge-GNN 模式（AlphaChip 风格边特征消息传递），
    通过 ``EncoderConfig.use_edge_gnn=True`` 启用。启用后 GNN 编码器从
    ``GraphEncoder``（R-GCN）切换为 ``EdgeGraphEncoder``（edge-aware MPNN），
    使 GNN 能感知 net 的物理属性（线长/拥塞/优先级）。
    """

    def __init__(
        self,
        node_feat_dim: int,
        grid_size: int,
        config: EncoderConfig | None = None,
    ) -> None:
        super().__init__()
        cfg = config or EncoderConfig()
        self.use_edge_gnn = cfg.use_edge_gnn
        if cfg.use_edge_gnn:
            # edge-GNN 模式：用 EdgeGraphEncoder（AlphaChip 风格）
            self.gnn = EdgeGraphEncoder(
                in_dim=node_feat_dim,
                edge_feat_dim=cfg.edge_feat_dim,
                config=EdgeEncoderConfig(
                    hidden_dim=cfg.hidden_dim,
                    out_dim=cfg.hidden_dim,
                    num_layers=cfg.num_gnn_layers,
                ),
            )
        else:
            # 默认模式：R-GCN（向后兼容）
            self.gnn = GraphEncoder(
                in_dim=node_feat_dim,
                hidden_dim=cfg.hidden_dim,
                out_dim=cfg.hidden_dim,
                num_layers=cfg.num_gnn_layers,
            )
        # 栅格特征展平后投影
        self.grid_proj = Sequential(
            Linear(grid_size, cfg.hidden_dim),
            ReLU(),
        )
        # 融合：图嵌入均值 + 栅格嵌入
        self.fuse = Sequential(
            Linear(cfg.hidden_dim * 2, cfg.out_dim),
            ReLU(),
        )

    def forward(
        self,
        node_feats: Tensor,
        edge_index: np.ndarray,
        grid_feat: Tensor,
        edge_feats: Tensor | None = None,
    ) -> Tensor:
        """前向：GNN 编码图 + 投影栅格 + 融合。

        Args:
            node_feats: 节点特征 ``[N, node_feat_dim]``。
            edge_index: 边索引 ``[2, E]``。
            grid_feat: 栅格特征 ``[grid_h, grid_w]``。
            edge_feats: 边特征 ``[E, edge_feat_dim]``（仅 edge-GNN 模式需要）。

        Returns:
            全局状态向量 ``[out_dim]``。
        """
        from polaris.nn import cat

        if self.use_edge_gnn:
            if edge_feats is None:
                # edge-GNN 模式但未提供边特征，用零特征兜底
                n_edges = edge_index.shape[1] if edge_index.size > 0 else 0
                edge_feats = Tensor(np.zeros((n_edges, 7), dtype=np.float64))
            node_emb = self.gnn(node_feats, edge_index, edge_feats)
        else:
            node_emb = self.gnn(node_feats, edge_index)  # [N, hidden]
        # 图级读出：均值池化
        graph_emb = node_emb.mean(axis=0)  # [hidden]
        # 栅格特征：行均值投影（降维）
        grid_flat = grid_feat.mean(axis=0)  # [grid_w]
        grid_emb = self.grid_proj(grid_flat)  # [hidden]
        # 可微拼接（梯度从 fused_input 流回 graph_emb 和 grid_emb）
        fused_input = cat([graph_emb, grid_emb])  # [hidden*2]
        out = self.fuse(fused_input)
        return out


def build_node_features(
    devices: dict,
    placements: dict,
    instance_ids: list[str],
) -> np.ndarray:
    """构建节点特征矩阵（器件尺寸 + 放置状态）。

    特征：[width, height, area, placed_flag, num_ports, category_id]
    """
    cat_map = {"passive": 0, "active": 1, "source": 2, "detector": 3}
    feats = []
    for inst_id in instance_ids:
        dev = devices[inst_id]
        w, h = dev.footprint()
        placed = 1.0 if inst_id in placements else 0.0
        cat = cat_map.get(dev.category, 0)
        feats.append([w, h, w * h, placed, len(dev.ports), cat])
    return np.array(feats, dtype=np.float64)


def edges_from_graph(graph, instance_ids: list[str]) -> np.ndarray:
    """从 networkx 图提取边索引 ``[2, E]``。"""
    id_to_idx = {iid: i for i, iid in enumerate(instance_ids)}
    edges = []
    for u, v in graph.edges():
        if u in id_to_idx and v in id_to_idx:
            edges.append([id_to_idx[u], id_to_idx[v]])
            edges.append([id_to_idx[v], id_to_idx[u]])  # 无向 -> 双向
    if not edges:
        return np.zeros((2, 0), dtype=np.int64)
    return np.array(edges).T  # [2, E]


@dataclass
class EdgeEncoderConfig:
    """edge-GNN 超参配置（规则 4：参数分组降低函数参数数）。

    将 ``hidden_dim``/``out_dim``/``num_layers`` 聚合为单一配置对象，
    使 ``EdgeGraphEncoder.__init__`` 参数数低于警告阈值。

    Attributes:
        hidden_dim: 隐藏层维度。
        out_dim: 输出节点嵌入维度。
        num_layers: 消息传递层数。
    """

    hidden_dim: int = 64
    out_dim: int = 64
    num_layers: int = 2


class EdgeGraphEncoder(Module):
    """边特征图神经网络编码器（edge-GNN，复刻 AlphaChip 核心创新）。

    与 ``GraphEncoder`` 的区别：消息传递时显式融合边特征（边类型/距离/带宽），
    而非仅做节点特征聚合。这是 AlphaChip (Mirhoseini et al., Nature 2021) 的
    核心创新之一——通过边特征让 GNN 感知 net 的物理属性（线长/拥塞/优先级）。

    消息传递公式（edge-aware）::

        msg_{j->i} = W_edge @ concat(h_j, e_{ji})   # 边特征融合
        h_i^{l+1} = LayerNorm(W_self @ h_i
                              + (1/|N(i)|) * sum_{j in N(i)} msg_{j->i}
                              + h_i)  # 残差

    来源:
    - Mirhoseini et al., "A graph placement methodology for fast chip design",
      Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
    - Circuit Training (开源实现), https://github.com/google-research/circuit_training
    - Gilmer et al., "Neural Message Passing for Quantum Chemistry", ICML 2017,
      https://arxiv.org/abs/1704.01212 (MPNN 边特征消息传递框架)
    """

    def __init__(
        self,
        in_dim: int,
        edge_feat_dim: int,
        config: EdgeEncoderConfig | None = None,
    ) -> None:
        """初始化 edge-GNN。

        Args:
            in_dim: 节点输入特征维度。
            edge_feat_dim: 边特征维度（如 [距离, 带宽, 优先级, 类型 one-hot]）。
            config: 超参配置（hidden_dim/out_dim/num_layers），默认 ``EdgeEncoderConfig()``。
        """
        super().__init__()
        cfg = config or EdgeEncoderConfig()
        self.num_layers = cfg.num_layers
        self.self_linears: list[Linear] = []
        self.edge_msg_linears: list[Linear] = []
        self.norms: list[LayerNorm] = []
        dim = in_dim
        for _ in range(cfg.num_layers):
            self.self_linears.append(Linear(dim, cfg.hidden_dim))
            # 边消息：concat(h_j, e_{ji}) -> hidden_dim
            self.edge_msg_linears.append(Linear(dim + edge_feat_dim, cfg.hidden_dim))
            self.norms.append(LayerNorm(cfg.hidden_dim))
            dim = cfg.hidden_dim
        self.out_proj = Linear(cfg.hidden_dim, cfg.out_dim)
        self.relu = ReLU()

    def forward(
        self,
        node_feats: Tensor,
        edge_index: np.ndarray,
        edge_feats: Tensor,
    ) -> Tensor:
        """前向边特征消息传递（含残差 + LayerNorm）。

        Args:
            node_feats: 节点特征 ``[N, in_dim]``。
            edge_index: 边索引 ``[2, E]``（每列 (src, dst)）。
            edge_feats: 边特征 ``[E, edge_feat_dim]``。

        Returns:
            节点嵌入 ``[N, out_dim]``。
        """
        from polaris.nn import cat, index_select, scatter_add

        h = node_feats
        n = h.shape[0]
        for layer in range(self.num_layers):
            self_msg = self.self_linears[layer](h)  # [N, hidden]
            hidden = self.self_linears[layer].out_features
            srcs = edge_index[0]
            dsts = edge_index[1]
            if len(srcs) > 0:
                # 边特征消息传递：msg = W @ concat(h_src, e)
                src_msgs = index_select(h, srcs)  # [E, in_dim]
                edge_msgs = cat([src_msgs, edge_feats], axis=1)  # [E, in_dim+edge_dim]
                msg = self.edge_msg_linears[layer](edge_msgs)  # [E, hidden]
                agg = scatter_add(msg, dsts, n)  # [n, hidden]
                # 度归一化
                deg = np.zeros(n)
                np.add.at(deg, dsts, 1.0)
                deg = np.maximum(deg, 1.0)
                agg = agg * Tensor(1.0 / deg[:, None])
            else:
                agg = Tensor(np.zeros((n, hidden)))
            # 残差连接
            if h.shape[-1] == self_msg.data.shape[-1]:
                self_msg = self_msg + h
            h = self.relu(self.norms[layer](self_msg + agg))
        return self.out_proj(h)


def build_edge_features(
    devices: dict,
    placements: dict,
    instance_ids: list[str],
    edge_index: np.ndarray,
) -> np.ndarray:
    """构建边特征矩阵（AlphaChip 风格）。

    边特征: [距离, 带宽需求, 优先级, 类型_one_hot(4)]
    总维度: 1 + 1 + 1 + 4 = 7

    Args:
        devices: 器件字典 {inst_id: DeviceSpec}。
        placements: 放置位置 {inst_id: {"x", "y", "w", "h"}}。
        instance_ids: 实例 ID 列表（与节点索引对应）。
        edge_index: 边索引 ``[2, E]``。

    Returns:
        边特征矩阵 ``[E, 7]``。
    """
    n_edges = edge_index.shape[1]
    feats = np.zeros((n_edges, 7), dtype=np.float64)
    for i in range(n_edges):
        src_idx = edge_index[0, i]
        dst_idx = edge_index[1, i]
        src_id = instance_ids[src_idx]
        dst_id = instance_ids[dst_idx]
        # 距离特征（曼哈顿距离，未放置时为 0）
        if src_id in placements and dst_id in placements:
            p1 = placements[src_id]
            p2 = placements[dst_id]
            x1, y1 = p1["x"] + p1["w"] / 2, p1["y"] + p1["h"] / 2
            x2, y2 = p2["x"] + p2["w"] / 2, p2["y"] + p2["h"] / 2
            feats[i, 0] = abs(x1 - x2) + abs(y1 - y2)
        # 带宽需求（端口数代理，来源: AlphaChip net bandwidth）
        src_dev = devices.get(src_id)
        dst_dev = devices.get(dst_id)
        if src_dev and dst_dev:
            feats[i, 1] = min(len(src_dev.ports), len(dst_dev.ports))
        # 优先级（默认 1.0，可扩展）
        feats[i, 2] = 1.0
        # 类型 one-hot（4 类：passive-passive, passive-active, active-active, other）
        # getattr 兼容 DeviceSpec（无 category 字段）与 Device（有 category 字段）
        src_cat = getattr(src_dev, "category", "other") if src_dev else "other"
        dst_cat = getattr(dst_dev, "category", "other") if dst_dev else "other"
        type_idx = _edge_type_index(src_cat, dst_cat)
        feats[i, 3 + type_idx] = 1.0
    return feats


def _edge_type_index(src_cat: str, dst_cat: str) -> int:
    """计算边类型索引（0-3）。"""
    cats = {src_cat, dst_cat}
    if cats == {"passive"}:
        return 0
    if cats == {"active"}:
        return 1
    if "passive" in cats and "active" in cats:
        return 2
    return 3


__all__ = [
    "GraphEncoder",
    "EdgeGraphEncoder",
    "EdgeEncoderConfig",
    "StateEncoder",
    "EncoderConfig",
    "build_node_features",
    "build_edge_features",
    "edges_from_graph",
]
