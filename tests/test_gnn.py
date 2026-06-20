"""GNN 状态编码器测试（Task 10）。"""

from __future__ import annotations

import numpy as np

from polaris.engine.gnn import (
    EdgeEncoderConfig,
    EdgeGraphEncoder,
    EncoderConfig,
    GraphEncoder,
    StateEncoder,
    build_edge_features,
    build_node_features,
    edges_from_graph,
)
from polaris.engine.netlist import load_netlist
from polaris.nn import Tensor

YAML_NETLIST = """
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
  wg2: {component: strip_waveguide, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
"""


def test_graph_encoder_output_shape():
    enc = GraphEncoder(in_dim=6, hidden_dim=32, out_dim=32, num_layers=2)
    node_feats = Tensor(np.random.randn(3, 6))
    edges = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    out = enc(node_feats, edges)
    assert out.shape == (3, 32)


def test_state_encoder_output_shape():
    se = StateEncoder(
        node_feat_dim=6,
        grid_size=20,
        config=EncoderConfig(hidden_dim=32, out_dim=64),
    )
    node_feats = Tensor(np.random.randn(3, 6))
    edges = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    grid = Tensor(np.random.rand(20, 20))
    out = se(node_feats, edges, grid)
    assert out.shape == (64,)


def test_build_node_features():
    net, devices, _ = load_netlist(YAML_NETLIST)
    inst_ids = list(devices.keys())
    feats = build_node_features(devices, {}, inst_ids)
    assert feats.shape == (3, 6)
    # 第 4 列为 placed_flag，未放置时为 0
    assert np.all(feats[:, 3] == 0)


def test_edges_from_graph():
    net, devices, g = load_netlist(YAML_NETLIST)
    inst_ids = list(devices.keys())
    edges = edges_from_graph(g, inst_ids)
    # 2 条无向边 -> 4 条有向边
    assert edges.shape[0] == 2
    assert edges.shape[1] == 4


def test_graph_encoder_no_edges():
    enc = GraphEncoder(in_dim=4, hidden_dim=16, out_dim=16, num_layers=2)
    node_feats = Tensor(np.random.randn(2, 4))
    edges = np.zeros((2, 0), dtype=np.int64)
    out = enc(node_feats, edges)
    assert out.shape == (2, 16)


def test_edge_graph_encoder_output_shape():
    """edge-GNN 输出形状正确。"""
    enc = EdgeGraphEncoder(
        in_dim=6,
        edge_feat_dim=7,
        config=EdgeEncoderConfig(hidden_dim=32, out_dim=16, num_layers=2),
    )
    node_feats = Tensor(np.random.randn(3, 6))
    edge_index = np.array([[0, 1, 1, 2, 0, 2], [1, 0, 2, 1, 2, 0]], dtype=np.int64)
    edge_feats = Tensor(np.random.randn(6, 7))
    out = enc(node_feats, edge_index, edge_feats)
    assert out.shape == (3, 16)


def test_edge_graph_encoder_no_edges():
    """edge-GNN 无边时仍能正常前向。"""
    enc = EdgeGraphEncoder(
        in_dim=4,
        edge_feat_dim=7,
        config=EdgeEncoderConfig(hidden_dim=16, out_dim=16, num_layers=2),
    )
    node_feats = Tensor(np.random.randn(2, 4))
    edges = np.zeros((2, 0), dtype=np.int64)
    edge_feats = Tensor(np.zeros((0, 7)))
    out = enc(node_feats, edges, edge_feats)
    assert out.shape == (2, 16)


def test_edge_graph_encoder_residual():
    """edge-GNN 残差连接：输入输出维度一致时跳过连接生效。"""
    enc = EdgeGraphEncoder(
        in_dim=16,
        edge_feat_dim=7,
        config=EdgeEncoderConfig(hidden_dim=16, out_dim=16, num_layers=2),
    )
    node_feats = Tensor(np.random.randn(4, 16))
    edge_index = np.array([[0, 1, 2, 3], [1, 0, 3, 2]], dtype=np.int64)
    edge_feats = Tensor(np.random.randn(4, 7))
    out = enc(node_feats, edge_index, edge_feats)
    assert out.shape == (4, 16)


def test_build_edge_features_shape():
    """build_edge_features 输出形状 [E, 7]。"""
    net, devices, g = load_netlist(YAML_NETLIST)
    inst_ids = list(devices.keys())
    edges = edges_from_graph(g, inst_ids)
    placements = {
        iid: {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0} for iid in inst_ids
    }
    feats = build_edge_features(devices, placements, inst_ids, edges)
    assert feats.shape == (edges.shape[1], 7)


def test_build_edge_features_distance():
    """build_edge_features 距离特征正确计算。"""
    net, devices, g = load_netlist(YAML_NETLIST)
    inst_ids = list(devices.keys())
    edges = edges_from_graph(g, inst_ids)
    placements = {
        inst_ids[0]: {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0},
        inst_ids[1]: {"x": 100.0, "y": 50.0, "w": 10.0, "h": 5.0},
        inst_ids[2]: {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0},
    }
    feats = build_edge_features(devices, placements, inst_ids, edges)
    # 第 0 列是距离，至少有一条边距离 > 0
    assert np.any(feats[:, 0] > 0)


def test_edge_graph_encoder_backward():
    """edge-GNN 反向传播梯度可计算。"""
    enc = EdgeGraphEncoder(
        in_dim=4,
        edge_feat_dim=3,
        config=EdgeEncoderConfig(hidden_dim=8, out_dim=4, num_layers=1),
    )
    node_feats = Tensor(np.random.randn(3, 4), requires_grad=True)
    edge_index = np.array([[0, 1, 2], [1, 2, 0]], dtype=np.int64)
    edge_feats = Tensor(np.random.randn(3, 3), requires_grad=True)
    out = enc(node_feats, edge_index, edge_feats)
    loss = out.sum()
    loss.backward()
    # 检查梯度已传播到节点特征
    assert node_feats.grad is not None
    assert node_feats.grad.shape == (3, 4)
