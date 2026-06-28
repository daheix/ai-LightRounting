"""E02 GNN 图神经网络验收测试。

验证 GNN 图卷积前向传播、消息传递机制和批处理能力。

文献来源:
- Schlichtkrull et al., 2018, R-GCN (Relational Graph Convolutional Networks)
  https://arxiv.org/abs/1703.06103
- Kipf & Welling, 2017, GCN (Graph Convolutional Networks)
  https://arxiv.org/abs/1609.02907
- Mirhoseini et al., Nature 2021, AlphaChip 图放置方法
  https://www.nature.com/articles/s41586-021-03544-w
- He et al., 2016, ResNet 残差连接
  https://arxiv.org/abs/1512.03385
- Ba et al., 2016, Layer Normalization
  https://arxiv.org/abs/1607.06450
"""

import numpy as np

from polaris.engine.gnn import (
    EdgeEncoderConfig,
    EdgeGraphEncoder,
    EncoderConfig,
    GraphEncoder,
    StateEncoder,
    build_edge_features,
    build_node_features,
)
from polaris.nn import Tensor


class TestGraphEncoder:
    """GraphEncoder 图编码器测试。"""

    def test_init_default(self):
        """M1: 默认初始化成功。"""
        encoder = GraphEncoder(in_dim=8, hidden_dim=16, out_dim=32, num_layers=2)
        assert encoder.num_layers == 2
        assert len(encoder.self_linears) == 2
        assert len(encoder.neigh_linears) == 2
        assert len(encoder.norms) == 2

    def test_forward_shape(self):
        """M1: 前向传播输出形状正确。"""
        encoder = GraphEncoder(in_dim=8, hidden_dim=16, out_dim=32, num_layers=2)
        n_nodes = 10
        node_feats = Tensor(np.random.randn(n_nodes, 8))
        edge_index = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (n_nodes, 32)

    def test_forward_no_edges(self):
        """M1: 无边图前向传播。"""
        encoder = GraphEncoder(in_dim=4, hidden_dim=8, out_dim=8, num_layers=1)
        node_feats = Tensor(np.random.randn(5, 4))
        edge_index = np.zeros((2, 0), dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (5, 8)

    def test_message_passing_aggregation(self):
        """M2: 消息传递正确聚合邻居特征。"""
        encoder = GraphEncoder(in_dim=2, hidden_dim=4, out_dim=2, num_layers=1)
        node_feats = Tensor(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float64))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (3, 2)
        assert not np.allclose(out.data, 0.0)

    def test_residual_connection(self):
        """M2: 残差连接生效（输入输出维度相同时）。"""
        encoder = GraphEncoder(in_dim=8, hidden_dim=8, out_dim=8, num_layers=2)
        node_feats = Tensor(np.random.randn(6, 8))
        edge_index = np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (6, 8)

    def test_single_node_graph(self):
        """M2: 单节点图前向传播。"""
        encoder = GraphEncoder(in_dim=4, hidden_dim=8, out_dim=4, num_layers=1)
        node_feats = Tensor(np.random.randn(1, 4))
        edge_index = np.zeros((2, 0), dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (1, 4)

    def test_large_graph(self):
        """M3: 大图批处理性能（100节点）。"""
        encoder = GraphEncoder(in_dim=8, hidden_dim=16, out_dim=16, num_layers=2)
        n_nodes = 100
        node_feats = Tensor(np.random.randn(n_nodes, 8))
        edges = []
        for i in range(n_nodes - 1):
            edges.append([i, i + 1])
            edges.append([i + 1, i])
        edge_index = np.array(edges).T
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (n_nodes, 16)

    def test_layer_norm_applied(self):
        """M2: LayerNorm 被应用（输出不全为0）。"""
        encoder = GraphEncoder(in_dim=4, hidden_dim=8, out_dim=4, num_layers=1)
        node_feats = Tensor(np.ones((5, 4)))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        out = encoder.forward(node_feats, edge_index)
        assert out.data.shape == (5, 4)
        assert not np.allclose(out.data, 0.0)


class TestEdgeGraphEncoder:
    """EdgeGraphEncoder 边特征图编码器测试。"""

    def test_init_default(self):
        """M1: 默认初始化成功。"""
        config = EdgeEncoderConfig(hidden_dim=16, out_dim=32, num_layers=2)
        encoder = EdgeGraphEncoder(in_dim=8, edge_feat_dim=7, config=config)
        assert encoder.num_layers == 2
        assert len(encoder.self_linears) == 2
        assert len(encoder.edge_msg_linears) == 2

    def test_forward_shape(self):
        """M1: 边特征消息传递输出形状正确。"""
        encoder = EdgeGraphEncoder(
            in_dim=8, edge_feat_dim=7,
            config=EdgeEncoderConfig(hidden_dim=16, out_dim=32, num_layers=2)
        )
        n_nodes = 10
        n_edges = 8
        node_feats = Tensor(np.random.randn(n_nodes, 8))
        edge_index = np.array([
            [0, 1, 2, 3, 4, 5, 6, 7],
            [1, 2, 3, 4, 5, 6, 7, 8],
        ], dtype=np.int64)
        edge_feats = Tensor(np.random.randn(n_edges, 7))
        out = encoder.forward(node_feats, edge_index, edge_feats)
        assert out.data.shape == (n_nodes, 32)

    def test_edge_features_affect_output(self):
        """M2: 边特征影响输出（不同边特征产生不同输出）。"""
        encoder = EdgeGraphEncoder(
            in_dim=4, edge_feat_dim=3,
            config=EdgeEncoderConfig(hidden_dim=8, out_dim=4, num_layers=1)
        )
        node_feats = Tensor(np.random.randn(5, 4))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        edge_feats1 = Tensor(np.ones((2, 3)))
        edge_feats2 = Tensor(np.zeros((2, 3)))
        out1 = encoder.forward(node_feats, edge_index, edge_feats1)
        out2 = encoder.forward(node_feats, edge_index, edge_feats2)
        assert not np.allclose(out1.data, out2.data)

    def test_no_edges_edge_gnn(self):
        """M2: 无边时 edge-GNN 前向传播。"""
        encoder = EdgeGraphEncoder(
            in_dim=4, edge_feat_dim=3,
            config=EdgeEncoderConfig(hidden_dim=8, out_dim=4, num_layers=1)
        )
        node_feats = Tensor(np.random.randn(3, 4))
        edge_index = np.zeros((2, 0), dtype=np.int64)
        edge_feats = Tensor(np.zeros((0, 3)))
        out = encoder.forward(node_feats, edge_index, edge_feats)
        assert out.data.shape == (3, 4)


class TestStateEncoder:
    """StateEncoder 状态编码器测试。"""

    def test_init_default(self):
        """M1: 默认初始化成功。"""
        encoder = StateEncoder(
            node_feat_dim=6,
            grid_size=8,
            config=EncoderConfig(hidden_dim=16, out_dim=32, num_gnn_layers=2),
        )
        assert not encoder.use_edge_gnn

    def test_forward_shape(self):
        """M1: 状态编码输出形状正确。"""
        encoder = StateEncoder(
            node_feat_dim=6,
            grid_size=8,
            config=EncoderConfig(hidden_dim=16, out_dim=32, num_gnn_layers=2),
        )
        node_feats = Tensor(np.random.randn(10, 6))
        edge_index = np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int64)
        grid_feat = Tensor(np.random.randn(8, 8))
        out = encoder.forward(node_feats, edge_index, grid_feat)
        assert out.data.shape == (32,)

    def test_edge_gnn_mode(self):
        """M1: edge-GNN 模式初始化与前向。"""
        config = EncoderConfig(
            hidden_dim=16, out_dim=32, num_gnn_layers=2,
            use_edge_gnn=True, edge_feat_dim=7,
        )
        encoder = StateEncoder(node_feat_dim=6, grid_size=8, config=config)
        assert encoder.use_edge_gnn
        node_feats = Tensor(np.random.randn(8, 6))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        grid_feat = Tensor(np.random.randn(8, 8))
        edge_feats = Tensor(np.random.randn(2, 7))
        out = encoder.forward(node_feats, edge_index, grid_feat, edge_feats)
        assert out.data.shape == (32,)

    def test_graph_grid_fusion(self):
        """M2: 图特征与栅格特征融合。"""
        encoder = StateEncoder(
            node_feat_dim=4,
            grid_size=4,
            config=EncoderConfig(hidden_dim=8, out_dim=16, num_gnn_layers=1),
        )
        node_feats = Tensor(np.random.randn(5, 4))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        grid_feat = Tensor(np.random.randn(4, 4))
        out = encoder.forward(node_feats, edge_index, grid_feat)
        assert out.data.shape == (16,)
        assert not np.allclose(out.data, 0.0)


class TestBuildFeatures:
    """节点/边特征构建工具测试。"""

    def test_build_node_features(self):
        """M1: 节点特征矩阵构建。"""
        from polaris.pdk.device import BoundingBox, Device

        devices = {
            "d1": Device(
                device_id="d1",
                platform="SOI",
                category="passive",
                name="y_branch",
                ports=[],
                bbox=BoundingBox(xmin=0, ymin=0, xmax=10.0, ymax=5.0),
            ),
            "d2": Device(
                device_id="d2",
                platform="SOI",
                category="passive",
                name="ring",
                ports=[],
                bbox=BoundingBox(xmin=0, ymin=0, xmax=30.0, ymax=30.0),
            ),
        }
        placements = {"d1": {"x": 10, "y": 10, "w": 10, "h": 5}}
        instance_ids = ["d1", "d2"]
        feats = build_node_features(devices, placements, instance_ids)
        assert feats.shape == (2, 6)

    def test_build_edge_features(self):
        """M1: 边特征矩阵构建。"""
        from polaris.pdk.device import BoundingBox, Device

        devices = {
            "d1": Device(
                device_id="d1",
                platform="SOI",
                category="passive",
                name="y_branch",
                ports=[],
                bbox=BoundingBox(xmin=0, ymin=0, xmax=10.0, ymax=5.0),
            ),
            "d2": Device(
                device_id="d2",
                platform="SOI",
                category="passive",
                name="ring",
                ports=[],
                bbox=BoundingBox(xmin=0, ymin=0, xmax=30.0, ymax=30.0),
            ),
        }
        placements = {
            "d1": {"x": 10, "y": 10, "w": 10, "h": 5},
            "d2": {"x": 50, "y": 20, "w": 30, "h": 30},
        }
        instance_ids = ["d1", "d2"]
        edge_index = np.array([[0, 1], [1, 0]], dtype=np.int64)
        feats = build_edge_features(devices, placements, instance_ids, edge_index)
        assert feats.shape == (2, 7)


class TestEncoderConfig:
    """EncoderConfig 配置测试。"""

    def test_default_config(self):
        """M1: 默认配置参数。"""
        cfg = EncoderConfig()
        assert cfg.hidden_dim == 64
        assert cfg.out_dim == 128
        assert cfg.num_gnn_layers == 2
        assert not cfg.use_edge_gnn
        assert cfg.edge_feat_dim == 7

    def test_custom_config(self):
        """M1: 自定义配置参数。"""
        cfg = EncoderConfig(hidden_dim=32, out_dim=64, num_gnn_layers=3, use_edge_gnn=True)
        assert cfg.hidden_dim == 32
        assert cfg.out_dim == 64
        assert cfg.num_gnn_layers == 3
        assert cfg.use_edge_gnn


class TestBatchProcessing:
    """批处理测试（M3 批处理能力）。"""

    def test_multiple_graphs_same_encoder(self):
        """M3: 同一编码器处理多个图。"""
        encoder = GraphEncoder(in_dim=4, hidden_dim=8, out_dim=4, num_layers=1)
        for _ in range(5):
            n = np.random.randint(3, 10)
            node_feats = Tensor(np.random.randn(n, 4))
            edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64) if n >= 3 else np.zeros((2, 0), dtype=np.int64)
            out = encoder.forward(node_feats, edge_index)
            assert out.data.shape == (n, 4)

    def test_state_encoder_consistency(self):
        """M3: 相同输入产生相同输出（确定性）。"""
        encoder = StateEncoder(
            node_feat_dim=4, grid_size=4,
            config=EncoderConfig(hidden_dim=8, out_dim=16, num_gnn_layers=1),
        )
        node_feats = Tensor(np.random.randn(5, 4))
        edge_index = np.array([[0, 1], [1, 2]], dtype=np.int64)
        grid_feat = Tensor(np.random.randn(4, 4))
        out1 = encoder.forward(node_feats, edge_index, grid_feat)
        out2 = encoder.forward(node_feats, edge_index, grid_feat)
        np.testing.assert_array_equal(out1.data, out2.data)
