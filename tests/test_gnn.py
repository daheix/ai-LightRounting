"""GNN 状态编码器测试（Task 10）。"""

from __future__ import annotations

import numpy as np

from polaris.engine.gnn import (
    EncoderConfig,
    GraphEncoder,
    StateEncoder,
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
