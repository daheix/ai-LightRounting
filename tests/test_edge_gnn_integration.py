"""Edge-GNN 集成测试（第4轮 P1-1）。

验证 EdgeGraphEncoder 已正确集成到训练流程：
- StateEncoder 支持 edge-GNN 模式
- FloorplanEnv 在 edge-GNN 模式下构建并传递边特征
- GNNPPOAgent 在 edge-GNN 模式下梯度能流回 EdgeGraphEncoder 参数

来源:
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training: https://github.com/google-research/circuit_training
"""

from __future__ import annotations

import numpy as np

from polaris.engine.gnn import (
    EdgeGraphEncoder,
    EncoderConfig,
    StateEncoder,
    build_edge_features,
)
from polaris.nn import Tensor


def test_encoder_config_use_edge_gnn_default_false():
    """测试 EncoderConfig.use_edge_gnn 默认为 False（向后兼容）。"""
    cfg = EncoderConfig()
    assert cfg.use_edge_gnn is False
    assert cfg.edge_feat_dim == 7


def test_state_encoder_default_mode_uses_graph_encoder():
    """测试默认模式用 GraphEncoder（R-GCN，向后兼容）。"""
    encoder = StateEncoder(node_feat_dim=8, grid_size=10)
    assert encoder.use_edge_gnn is False
    # 默认模式不应有 EdgeGraphEncoder
    assert not isinstance(encoder.gnn, EdgeGraphEncoder)


def test_state_encoder_edge_gnn_mode():
    """测试 edge-GNN 模式用 EdgeGraphEncoder。"""
    cfg = EncoderConfig(use_edge_gnn=True, edge_feat_dim=7)
    encoder = StateEncoder(node_feat_dim=8, grid_size=10, config=cfg)
    assert encoder.use_edge_gnn is True
    assert isinstance(encoder.gnn, EdgeGraphEncoder)


def test_state_encoder_forward_edge_gnn_mode():
    """测试 edge-GNN 模式前向输出维度正确。"""
    cfg = EncoderConfig(use_edge_gnn=True, out_dim=64)
    encoder = StateEncoder(node_feat_dim=8, grid_size=10, config=cfg)
    node_feats = Tensor(np.random.randn(5, 8))
    edge_index = np.array([[0, 1, 2], [1, 2, 3]])
    grid_feat = Tensor(np.random.randn(10, 10))
    edge_feats = Tensor(np.random.randn(3, 7))
    out = encoder(node_feats, edge_index, grid_feat, edge_feats)
    assert out.data.shape == (64,)


def test_state_encoder_forward_edge_gnn_without_edge_feats():
    """测试 edge-GNN 模式未提供边特征时用零特征兜底。"""
    cfg = EncoderConfig(use_edge_gnn=True, out_dim=64)
    encoder = StateEncoder(node_feat_dim=8, grid_size=10, config=cfg)
    node_feats = Tensor(np.random.randn(5, 8))
    edge_index = np.array([[0, 1], [1, 2]])
    grid_feat = Tensor(np.random.randn(10, 10))
    # 不传 edge_feats，应自动用零特征
    out = encoder(node_feats, edge_index, grid_feat)
    assert out.data.shape == (64,)


def test_state_encoder_backward_compatible():
    """测试默认模式（无 edge_feats）与修改前行为一致。"""
    encoder = StateEncoder(node_feat_dim=8, grid_size=10)
    node_feats = Tensor(np.random.randn(5, 8))
    edge_index = np.array([[0, 1], [1, 2]])
    grid_feat = Tensor(np.random.randn(10, 10))
    # 默认模式不传 edge_feats 应正常工作
    out = encoder(node_feats, edge_index, grid_feat)
    assert out.data.shape == (128,)  # 默认 out_dim=128


def test_build_edge_features_shape():
    """测试 build_edge_features 输出形状正确。"""
    from polaris.data.specs import DeviceSpec

    # DeviceSpec 无 category 字段，build_edge_features 用 getattr 兜底为 "other"
    devices = {
        "d1": DeviceSpec(name="d1", device_type="wg"),
        "d2": DeviceSpec(name="d2", device_type="mzi"),
    }
    placements = {
        "d1": {"x": 0, "y": 0, "w": 10, "h": 10},
        "d2": {"x": 20, "y": 0, "w": 10, "h": 10},
    }
    instance_ids = ["d1", "d2"]
    edge_index = np.array([[0], [1]])
    edge_feats = build_edge_features(devices, placements, instance_ids, edge_index)
    assert edge_feats.shape == (1, 7)  # 1 条边，7 维特征


def test_edge_gnn_gradient_flow():
    """测试 edge-GNN 模式梯度能流回 EdgeGraphEncoder 参数。"""
    cfg = EncoderConfig(use_edge_gnn=True, out_dim=32, hidden_dim=16)
    encoder = StateEncoder(node_feat_dim=4, grid_size=8, config=cfg)
    node_feats = Tensor(np.random.randn(3, 4))
    edge_index = np.array([[0, 1], [1, 2]])
    grid_feat = Tensor(np.random.randn(8, 8))
    edge_feats = Tensor(np.random.randn(2, 7))
    out = encoder(node_feats, edge_index, grid_feat, edge_feats)
    # 反向传播
    out.backward(np.ones_like(out.data))
    # 验证 EdgeGraphEncoder 参数有梯度
    has_grad = False
    for param in encoder.parameters():
        if param.grad is not None and np.any(param.grad != 0):
            has_grad = True
            break
    assert has_grad, "EdgeGraphEncoder 参数应有非零梯度"


def test_floorplan_env_edge_gnn_mode():
    """测试 FloorplanEnv 在 edge-GNN 模式下构建边特征。"""
    from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
    from polaris.engine.netlist import load_netlist

    # 构造 edge-GNN 模式的 StateEncoder
    # node_feat_dim=6 对齐 build_node_features 的 6 维输出：
    # [width, height, area, placed_flag, num_ports, category_id]
    cfg = EncoderConfig(use_edge_gnn=True, out_dim=32, hidden_dim=16)
    state_encoder = StateEncoder(node_feat_dim=6, grid_size=10, config=cfg)

    # 用 YAML 字符串构造网表（load_netlist 返回 net, devices, graph）
    # 器件名用 catalog 中注册的 strip_waveguide / mmi_1x2
    yaml_netlist = """
instances:
  wg1:
    component: strip_waveguide
    platform: SOI
  mmi1:
    component: mmi_1x2
    platform: SOI
connections:
  - [wg1, out, mmi1, in]
"""
    net, devices, _ = load_netlist(yaml_netlist)

    env_cfg = FloorplanEnvConfig(canvas_w=100, canvas_h=100, grid_size=10)
    env_cfg.state_encoder = state_encoder
    env = FloorplanEnv(net, devices, env_cfg)

    obs, _info = env.reset()
    # edge-GNN 模式应构建 edge_feats
    graph_features = obs.get("graph_features", {})
    assert "edge_feats" in graph_features, "edge-GNN 模式应构建 edge_feats"
    edge_feats = graph_features["edge_feats"]
    assert edge_feats.shape[1] == 7  # 7 维边特征


def test_floorplan_env_default_mode_no_edge_feats():
    """测试默认模式（无 edge-GNN）不构建 edge_feats（向后兼容）。"""
    from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
    from polaris.engine.netlist import load_netlist

    # 默认模式 StateEncoder
    # node_feat_dim=6 对齐 build_node_features 的 6 维输出
    state_encoder = StateEncoder(node_feat_dim=6, grid_size=10)

    yaml_netlist = """
instances:
  wg1:
    component: strip_waveguide
    platform: SOI
"""
    net, devices, _ = load_netlist(yaml_netlist)

    env_cfg = FloorplanEnvConfig(canvas_w=100, canvas_h=100, grid_size=10)
    env_cfg.state_encoder = state_encoder
    env = FloorplanEnv(net, devices, env_cfg)

    obs, _info = env.reset()
    graph_features = obs.get("graph_features", {})
    # 默认模式不应有 edge_feats
    assert "edge_feats" not in graph_features, "默认模式不应构建 edge_feats"


def test_gnn_graph_state_edge_feats_field():
    """测试 GNNGraphState 支持 edge_feats 字段。"""
    from polaris.trainer.gnn_ppo import GNNGraphState

    # 无 edge_feats（默认，向后兼容）
    gs1 = GNNGraphState(
        node_feats=np.zeros((3, 8)),
        edge_index=np.array([[0], [1]]),
        grid_feat=np.zeros((10, 10)),
    )
    assert gs1.edge_feats is None

    # 有 edge_feats
    gs2 = GNNGraphState(
        node_feats=np.zeros((3, 8)),
        edge_index=np.array([[0], [1]]),
        grid_feat=np.zeros((10, 10)),
        edge_feats=np.zeros((1, 7)),
    )
    assert gs2.edge_feats is not None
    assert gs2.edge_feats.shape == (1, 7)
