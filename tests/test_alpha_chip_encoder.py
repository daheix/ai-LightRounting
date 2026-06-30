"""AlphaChip 编码器单元测试。

覆盖：
- ``src/polaris/rl/alpha_chip_encoder.py``：PhotonicPlacementEncoder
  光子布局状态编码器（电路编码 / 布局编码 / 节点特征 / 边特征）

来源:
- Mirhoseini 2024 Nature, AlphaChip
  https://doi.org/10.1038/s41586-024-07714-9
- Gilmer et al., 2017, MPNN https://arxiv.org/abs/1704.01212
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.rl.alpha_chip_encoder import PhotonicPlacementEncoder


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

_SIMPLE_CIRCUIT = {
    "devices": [
        {"id": "d0", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["p0", "p1"]},
        {"id": "d1", "type": "ring", "width": 40.0, "height": 40.0, "ports": ["p0", "p1"]},
        {"id": "d2", "type": "mmi", "width": 60.0, "height": 20.0, "ports": ["p0", "p1", "p2", "p3"]},
    ],
    "nets": [
        {"src": ["d0", "p1"], "dst": ["d1", "p0"], "type": "waveguide", "target_length": 100.0},
        {"src": ["d1", "p1"], "dst": ["d2", "p0"], "type": "waveguide", "target_length": 100.0},
    ],
}

_SIMPLE_PLACEMENT = {
    "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
    "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
    "d2": {"x": 200.0, "y": 0.0, "rotation": 0},
}


# ---------------------------------------------------------------------------
# PhotonicPlacementEncoder 初始化
# ---------------------------------------------------------------------------


def test_encoder_init():
    """初始化后特征维度正确。"""
    encoder = PhotonicPlacementEncoder()
    assert encoder.node_feat_dim == 9  # type_one_hot(4) + width + height + n_ports + aspect + area
    assert encoder.edge_feat_dim == 4  # type_one_hot(3) + target_length


# ---------------------------------------------------------------------------
# compute_features
# ---------------------------------------------------------------------------


def test_compute_features_mzi():
    """MZI 节点特征。"""
    encoder = PhotonicPlacementEncoder()
    node = {"type": "mzi", "width": 50.0, "height": 30.0, "ports": ["p0", "p1"]}
    feat = encoder.compute_features(node)
    assert feat.shape == (9,)
    assert feat[0] == 1.0  # type=mzi → one-hot [0]
    assert feat[4] == 50.0  # width
    assert feat[5] == 30.0  # height
    assert feat[6] == 2.0  # n_ports


def test_compute_features_ring():
    """Ring 节点特征。"""
    encoder = PhotonicPlacementEncoder()
    node = {"type": "ring", "width": 40.0, "height": 40.0, "ports": ["p0"]}
    feat = encoder.compute_features(node)
    assert feat.shape == (9,)
    assert feat[1] == 1.0  # type=ring → one-hot [1]


def test_compute_features_unknown_type():
    """未知类型默认为 mzi。"""
    encoder = PhotonicPlacementEncoder()
    node = {"type": "unknown", "width": 50.0, "height": 30.0, "ports": []}
    feat = encoder.compute_features(node)
    assert feat[0] == 1.0  # 默认 mzi


def test_compute_features_missing_fields():
    """缺失字段使用默认值。"""
    encoder = PhotonicPlacementEncoder()
    node = {}
    feat = encoder.compute_features(node)
    assert feat.shape == (9,)
    assert feat[4] == 50.0  # 默认 width
    assert feat[5] == 30.0  # 默认 height


# ---------------------------------------------------------------------------
# _compute_edge_features
# ---------------------------------------------------------------------------


def test_compute_edge_features_waveguide():
    """Waveguide 边特征。"""
    encoder = PhotonicPlacementEncoder()
    edge = {"type": "waveguide", "target_length": 100.0}
    feat = encoder._compute_edge_features(edge)
    assert feat.shape == (4,)
    assert feat[0] == 1.0  # type=waveguide → one-hot [0]
    assert feat[3] == 100.0  # target_length


def test_compute_edge_features_crossing():
    """Crossing 边特征。"""
    encoder = PhotonicPlacementEncoder()
    edge = {"type": "crossing", "target_length": 50.0}
    feat = encoder._compute_edge_features(edge)
    assert feat[1] == 1.0  # type=crossing → one-hot [1]


def test_compute_edge_features_unknown_type():
    """未知类型默认为 waveguide。"""
    encoder = PhotonicPlacementEncoder()
    edge = {"type": "unknown", "target_length": 100.0}
    feat = encoder._compute_edge_features(edge)
    assert feat[0] == 1.0  # 默认 waveguide


# ---------------------------------------------------------------------------
# encode_circuit
# ---------------------------------------------------------------------------


def test_encode_circuit_basic():
    """电路编码返回正确结构。"""
    encoder = PhotonicPlacementEncoder()
    graph = encoder.encode_circuit(_SIMPLE_CIRCUIT)
    assert "node_feats" in graph
    assert "edge_index" in graph
    assert "edge_feats" in graph


def test_encode_circuit_node_feats_shape():
    """节点特征形状正确。"""
    encoder = PhotonicPlacementEncoder()
    graph = encoder.encode_circuit(_SIMPLE_CIRCUIT)
    # 3 个器件，9 维节点特征
    assert graph["node_feats"].shape == (3, 9)


def test_encode_circuit_edge_index():
    """边索引形状正确。"""
    encoder = PhotonicPlacementEncoder()
    graph = encoder.encode_circuit(_SIMPLE_CIRCUIT)
    # 2 条 nets，每条 1 条无向边（双向存储为 2 条有向边）
    assert graph["edge_index"].shape[0] == 2  # [2, E]
    assert graph["edge_index"].shape[1] == 2  # 2 条有向边


def test_encode_circuit_empty():
    """空电路返回正确结构。"""
    encoder = PhotonicPlacementEncoder()
    graph = encoder.encode_circuit({"devices": [], "nets": []})
    assert graph["node_feats"].shape == (0, 9)
    assert graph["edge_index"].shape == (2, 0)
    assert graph["edge_feats"].shape == (0, 4)


# ---------------------------------------------------------------------------
# encode_placement
# ---------------------------------------------------------------------------


def test_encode_placement_shape():
    """布局编码形状正确。"""
    encoder = PhotonicPlacementEncoder()
    feats = encoder.encode_placement(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    # 3 个器件，9+4=13 维（节点特征 + 位置特征）
    assert feats.shape == (3, 13)


def test_encode_placement_position_features():
    """已放置器件有位置信息。"""
    encoder = PhotonicPlacementEncoder()
    feats = encoder.encode_placement(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    # d0 在 (0,0)，is_placed=1
    assert feats[0, 9] == 0.0  # x
    assert feats[0, 10] == 0.0  # y
    assert feats[0, 11] == 0.0  # rotation
    assert feats[0, 12] == 1.0  # is_placed


def test_encode_placement_unplaced():
    """未放置器件位置为 0。"""
    encoder = PhotonicPlacementEncoder()
    placement = {"d0": {"x": 0.0, "y": 0.0, "rotation": 0}}
    feats = encoder.encode_placement(placement, _SIMPLE_CIRCUIT)
    # d1 和 d2 未放置
    assert feats[1, 9] == 0.0
    assert feats[1, 10] == 0.0
    assert feats[1, 12] == 0.0  # is_placed=0


def test_encode_placement_with_rotation():
    """有旋转的器件正确编码。"""
    encoder = PhotonicPlacementEncoder()
    placement = {"d0": {"x": 0.0, "y": 0.0, "rotation": 90}}
    feats = encoder.encode_placement(placement, _SIMPLE_CIRCUIT)
    assert feats[0, 11] == 90.0  # rotation


# ---------------------------------------------------------------------------
# 端到端测试
# ---------------------------------------------------------------------------


def test_encoder_consistency():
    """同一电路多次编码结果一致。"""
    encoder = PhotonicPlacementEncoder()
    graph1 = encoder.encode_circuit(_SIMPLE_CIRCUIT)
    graph2 = encoder.encode_circuit(_SIMPLE_CIRCUIT)
    assert np.allclose(graph1["node_feats"], graph2["node_feats"])
    assert np.array_equal(graph1["edge_index"], graph2["edge_index"])


def test_placement_encoding_idempotent():
    """同一布局多次编码结果一致。"""
    encoder = PhotonicPlacementEncoder()
    feats1 = encoder.encode_placement(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    feats2 = encoder.encode_placement(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert np.allclose(feats1, feats2)
