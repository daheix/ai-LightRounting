"""GNN 状态编码器（Task 10）。

实现器件-连接图的图神经网络编码（消息传递 GNN），融合栅格空间特征。
torch 无法安装时，使用 ``polaris.nn`` 纯 NumPy 复刻实现（规则 3）。

方法参考：
- R-GCN（关系图卷积网络）Schlichtkrull et al., 2018
  来源: https://arxiv.org/abs/1703.06103
- Basso et al., NeurIPS 2025（RL+R-GCN 模拟 IC 布局感知 floorplanning）
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- PyTorch Geometric MessagePassing
  来源: https://pytorch-geometric.readthedocs.io/

消息传递公式（与 R-GCN/GraphSAGE 一致）::
    h_i^{l+1} = ReLU( W_self @ h_i^l + (1/|N|) * sum_{j in N(i)} W_neigh @ h_j^l )
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.nn import Linear, Module, ReLU, Sequential, Tensor


@dataclass
class StateEncoderConfig:
    """StateEncoder 超参数配置。

    Attributes:
        hidden_dim: 隐藏层维度。
        out_dim: 输出状态向量维度。
        num_gnn_layers: GNN 消息传递层数。
    """

    hidden_dim: int = 64
    out_dim: int = 128
    num_gnn_layers: int = 2


class GraphEncoder(Module):
    """器件-连接图 GNN 编码器（消息传递，复刻 R-GCN）。

    输入：节点特征矩阵 ``[N, in_dim]`` + 边列表 ``[2, E]``。
    输出：节点嵌入 ``[N, hidden_dim]``。

    采用 R-GCN 风格的消息传递：每个节点聚合邻居特征后经线性变换 + ReLU。
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
        dim = in_dim
        for _ in range(num_layers):
            self.self_linears.append(Linear(dim, hidden_dim))
            self.neigh_linears.append(Linear(dim, hidden_dim))
            dim = hidden_dim
        self.out_proj = Linear(hidden_dim, out_dim)
        self.relu = ReLU()

    def forward(self, node_feats: Tensor, edge_index: np.ndarray) -> Tensor:
        """前向消息传递。

        Args:
            node_feats: 节点特征 ``[N, in_dim]``。
            edge_index: 边索引 ``[2, E]``（每列 (src, dst)）。

        Returns:
            节点嵌入 ``[N, out_dim]``。
        """
        h = node_feats
        n = h.shape[0]
        for layer in range(self.num_layers):
            self_msg = self.self_linears[layer](h)  # [N, hidden]
            # 邻居聚合：对每条边 src->dst，将 src 特征累加到 dst
            neigh_msg = self.neigh_linears[layer](h)  # [N, hidden]
            agg = np.zeros((n, self.self_linears[layer].out_features))
            srcs = edge_index[0]
            dsts = edge_index[1]
            if len(srcs) > 0:
                np.add.at(agg, dsts, neigh_msg.data[srcs])
                # 度归一化（与 R-GCN 一致）
                deg = np.zeros(n)
                np.add.at(deg, dsts, 1.0)
                deg = np.maximum(deg, 1.0)
                agg = agg / deg[:, None]
            agg_t = Tensor(agg)
            h = self.relu(self_msg + agg_t)
        return self.out_proj(h)


class StateEncoder(Module):
    """状态编码器：融合图特征（GNN）与栅格空间特征。

    将器件连接图经 GNN 编码为节点嵌入，再与栅格空间特征（占用/拥塞）
    拼接，输出全局状态向量供 PPO 策略网络使用。

    参考 Basso et al. NeurIPS 2025：图特征 + 空间特征融合。
    """

    def __init__(
        self,
        node_feat_dim: int,
        grid_size: int,
        config: StateEncoderConfig | None = None,
        **kwargs,
    ) -> None:
        """初始化状态编码器。

        Args:
            node_feat_dim: 节点特征维度。
            grid_size: 栅格特征维度（grid_w）。
            config: 超参数配置；未提供时按 ``kwargs`` 构建默认配置。
            **kwargs: 向后兼容的旧关键字参数
                （``hidden_dim``/``out_dim``/``num_gnn_layers``）。
        """
        super().__init__()
        cfg = config or StateEncoderConfig(**kwargs)
        self.gnn = GraphEncoder(
            in_dim=node_feat_dim,
            hidden_dim=cfg.hidden_dim,
            out_dim=cfg.hidden_dim,
            num_layers=cfg.num_gnn_layers,
        )
        # 栅格特征展平后投影
        self.grid_proj = Sequential(Linear(grid_size, cfg.hidden_dim), ReLU())
        # 融合：图嵌入均值 + 栅格嵌入
        self.fuse = Sequential(Linear(cfg.hidden_dim * 2, cfg.out_dim), ReLU())

    def forward(
        self,
        node_feats: Tensor,
        edge_index: np.ndarray,
        grid_feat: Tensor,
    ) -> Tensor:
        """前向：GNN 编码图 + 投影栅格 + 融合。

        Args:
            node_feats: 节点特征 ``[N, node_feat_dim]``。
            edge_index: 边索引 ``[2, E]``。
            grid_feat: 栅格特征 ``[grid_h, grid_w]``。

        Returns:
            全局状态向量 ``[out_dim]``。
        """
        node_emb = self.gnn(node_feats, edge_index)  # [N, hidden]
        # 图级读出：均值池化
        graph_emb = node_emb.mean(axis=0)  # [hidden]
        # 栅格特征：行均值投影（降维）
        grid_flat = grid_feat.mean(axis=0)  # [grid_w]
        grid_emb = self.grid_proj(grid_flat)  # [hidden]
        # 融合（用 data 拼接计算，避免 autograd 拼接复杂性）
        fused_input = Tensor(np.concatenate([graph_emb.data, grid_emb.data]))
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


__all__ = [
    "GraphEncoder",
    "StateEncoder",
    "StateEncoderConfig",
    "build_node_features",
    "edges_from_graph",
]
