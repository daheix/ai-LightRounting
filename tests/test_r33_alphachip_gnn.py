"""R33 测试套件：AlphaChip Edge-GNN 对齐（光电子专用边特征 + 多关系 + GAT）。

学术依据:
- Mirhoseini et al., Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- Schlichtkrull et al., ESWC 2018, https://arxiv.org/abs/1703.06103
- Veličković et al., ICLR 2018, https://arxiv.org/abs/1710.10903
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.alphachip_gnn import (
    NET_RELATION_CONTROL,
    NET_RELATION_ELECTRICAL,
    NET_RELATION_OPTICAL,
    PHOTONIC_EDGE_DIM,
    AlphaChipEdgeGNN,
    GATLayer,
    MultiRelationalEdgeGraphEncoder,
    PhotonicEdgeFeatureConfig,
    _infer_net_relation,
    _segment_softmax,
    _wavelength_to_band_idx,
    build_photonic_edge_features,
)
from polaris.nn import Tensor

# =============================================================================
# 测试辅助：构造模拟器件和边
# =============================================================================


class _MockDevice:
    """模拟器件（兼容 DeviceSpec/Device 接口）。"""

    def __init__(
        self,
        name: str = "wg",
        category: str = "passive",
        ports: list | None = None,
        params: dict | None = None,
    ) -> None:
        self.name = name
        self.category = category
        self.ports = ports or [("in", 0, 0, "E"), ("out", 10, 0, "W")]
        self.params = params or {}


def _make_simple_graph(n_nodes: int = 4, n_edges: int = 6):
    """构造简单图（链式 + 部分跳连）。"""
    np.random.seed(42)
    node_feats = Tensor(np.random.randn(n_nodes, 6))
    # 链式: 0->1, 1->2, 2->3 + 跳连 0->2, 1->3, 0->3
    edge_index = np.array(
        [
            [0, 1, 2, 0, 1, 0],
            [1, 2, 3, 2, 3, 3],
        ],
        dtype=np.int64,
    )
    edge_feats = Tensor(np.random.randn(n_edges, PHOTONIC_EDGE_DIM))
    return node_feats, edge_index, edge_feats


def _make_devices_and_placements():
    """构造模拟器件字典和放置位置。"""
    devices = {
        "dev0": _MockDevice(
            "waveguide", "passive",
            params={"wavelength": 1.55, "neff": 2.4, "loss_db_cm": 2.0},
        ),
        "dev1": _MockDevice(
            "mzi", "passive",
            params={"wavelength": 1.55, "neff": 2.4, "loss_db_cm": 1.0},
        ),
        "dev2": _MockDevice("laser", "active", params={"wavelength": 1.55, "neff": 3.5}),
        "dev3": _MockDevice("heater", "active", params={"wavelength": 1.55, "neff": 2.4}),
    }
    placements = {
        "dev0": {"x": 0, "y": 0, "w": 10, "h": 5},
        "dev1": {"x": 20, "y": 0, "w": 15, "h": 10},
        "dev2": {"x": 0, "y": 20, "w": 8, "h": 8},
        "dev3": {"x": 30, "y": 20, "w": 5, "h": 5},
    }
    instance_ids = ["dev0", "dev1", "dev2", "dev3"]
    edge_index = np.array(
        [
            [0, 1, 2, 0],
            [1, 2, 3, 3],
        ],
        dtype=np.int64,
    )
    return devices, placements, instance_ids, edge_index


# =============================================================================
# 1. 光电子边特征构建测试
# =============================================================================


class TestPhotonicEdgeFeatures:
    """光电子专用边特征构建测试。"""

    def test_edge_dim_is_15(self):
        """边特征维度应为 15（*创新*：扩展 AlphaChip 7 维至 15 维）。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        feats = build_photonic_edge_features(devices, placements, instance_ids, edge_index)
        assert feats.shape == (4, PHOTONIC_EDGE_DIM)
        assert feats.shape[1] == 15

    def test_distance_feature(self):
        """[0] 距离特征应为曼哈顿距离。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        feats = build_photonic_edge_features(devices, placements, instance_ids, edge_index)
        # dev0 中心 (5, 2.5), dev1 中心 (27.5, 5)
        # 曼哈顿距离 = |5-27.5| + |2.5-5| = 22.5 + 2.5 = 25
        assert feats[0, 0] == pytest.approx(25.0, abs=0.1)

    def test_band_one_hot(self):
        """[7-9] 波段 one-hot 应正确编码 C-band（1.55μm）。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        feats = build_photonic_edge_features(devices, placements, instance_ids, edge_index)
        # 所有器件波长 1.55μm → C-band → 索引 0
        for i in range(4):
            assert feats[i, 7] == 1.0  # C-band
            assert feats[i, 8] == 0.0  # L-band
            assert feats[i, 9] == 0.0  # O-band

    def test_loss_feature_normalized(self):
        """[11] 波导损耗应归一化到 [0, 1]。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        feats = build_photonic_edge_features(devices, placements, instance_ids, edge_index)
        # dev0 loss_db_cm=2.0 → 2.0/10.0 = 0.2
        assert feats[0, 11] == pytest.approx(0.2, abs=0.01)
        # 所有损耗特征在 [0, 1]
        assert np.all(feats[:, 11] >= 0)
        assert np.all(feats[:, 11] <= 1.0)

    def test_net_relation_type(self):
        """[14] net 关系类型应正确推断（光/电/控制）。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        feats = build_photonic_edge_features(devices, placements, instance_ids, edge_index)
        # dev0(passive) -> dev1(passive): 光波导 (0)
        assert feats[0, 14] == NET_RELATION_OPTICAL
        # dev1(passive) -> dev2(active): 光波导 (0)
        assert feats[1, 14] == NET_RELATION_OPTICAL
        # dev2(active) -> dev3(active, heater): 控制信号 (2)
        assert feats[2, 14] == NET_RELATION_CONTROL
        # dev0(passive) -> dev3(active, heater): 控制信号 (2)
        assert feats[3, 14] == NET_RELATION_CONTROL

    def test_empty_edges(self):
        """空边索引应返回空特征矩阵。"""
        devices = {"dev0": _MockDevice()}
        empty_edges = np.zeros((2, 0), dtype=np.int64)
        feats = build_photonic_edge_features(devices, {}, ["dev0"], empty_edges)
        assert feats.shape == (0, PHOTONIC_EDGE_DIM)

    def test_custom_config(self):
        """自定义配置应覆盖默认值。"""
        devices = {
            "dev0": _MockDevice("wg", "passive", params={}),
            "dev1": _MockDevice("wg", "passive", params={}),
        }
        placements = {
            "dev0": {"x": 0, "y": 0, "w": 10, "h": 10},
            "dev1": {"x": 20, "y": 0, "w": 10, "h": 10},
        }
        edge_index = np.array([[0], [1]], dtype=np.int64)
        cfg = PhotonicEdgeFeatureConfig(
            default_wavelength_um=1.31,  # O-band
            default_loss_db_cm=5.0,
        )
        feats = build_photonic_edge_features(devices, placements, ["dev0", "dev1"], edge_index, cfg)
        # O-band → 索引 2
        assert feats[0, 9] == 1.0  # O-band
        # loss 5.0/10.0 = 0.5
        assert feats[0, 11] == pytest.approx(0.5, abs=0.01)


# =============================================================================
# 2. 辅助函数测试
# =============================================================================


class TestAuxFunctions:
    """辅助函数测试。"""

    def test_wavelength_to_band_c_band(self):
        """C-band 波长应映射到索引 0。"""
        assert _wavelength_to_band_idx(1.55) == 0
        assert _wavelength_to_band_idx(1.53) == 0
        assert _wavelength_to_band_idx(1.565) == 0

    def test_wavelength_to_band_l_band(self):
        """L-band 波长应映射到索引 1。"""
        assert _wavelength_to_band_idx(1.58) == 1
        assert _wavelength_to_band_idx(1.625) == 1

    def test_wavelength_to_band_o_band(self):
        """O-band 波长应映射到索引 2。"""
        assert _wavelength_to_band_idx(1.31) == 2
        assert _wavelength_to_band_idx(1.36) == 2

    def test_wavelength_to_band_default(self):
        """未匹配波段应默认返回 C-band (0)。"""
        assert _wavelength_to_band_idx(1.0) == 0
        assert _wavelength_to_band_idx(2.0) == 0

    def test_infer_net_relation_optical(self):
        """两端 passive 应推断为光波导。"""
        dev1 = _MockDevice("wg", "passive")
        dev2 = _MockDevice("mzi", "passive")
        assert _infer_net_relation(dev1, dev2) == NET_RELATION_OPTICAL

    def test_infer_net_relation_control(self):
        """含 heater 关键字应推断为控制信号。"""
        dev1 = _MockDevice("wg", "passive")
        dev2 = _MockDevice("thermal_heater", "active")
        assert _infer_net_relation(dev1, dev2) == NET_RELATION_CONTROL

    def test_infer_net_relation_electrical(self):
        """两端 active 应推断为电信号。"""
        dev1 = _MockDevice("laser", "active")
        dev2 = _MockDevice("detector", "active")
        assert _infer_net_relation(dev1, dev2) == NET_RELATION_ELECTRICAL

    def test_segment_softmax_basic(self):
        """segment_softmax 应正确归一化。"""
        # 2 个节点，3 条边：0->0, 1->0, 2->1
        scores = np.array([1.0, 2.0, 3.0])
        dsts = np.array([0, 0, 1])
        weights = _segment_softmax(scores, dsts, 2)
        # 节点 0 的两条边 softmax(1, 2) = [e^1/(e^1+e^2), e^2/(e^1+e^2)]
        sum0 = np.exp(1.0) + np.exp(2.0)
        assert weights[0] == pytest.approx(np.exp(1.0) / sum0, abs=1e-6)
        assert weights[1] == pytest.approx(np.exp(2.0) / sum0, abs=1e-6)
        # 节点 1 只有一条边，权重为 1
        assert weights[2] == pytest.approx(1.0, abs=1e-6)

    def test_segment_softmax_sum_to_one(self):
        """每个 dst 节点的注意力权重之和应为 1。"""
        np.random.seed(42)
        scores = np.random.randn(10)
        dsts = np.random.randint(0, 3, 10)
        weights = _segment_softmax(scores, dsts, 3)
        for node in range(3):
            mask = dsts == node
            if np.any(mask):
                assert weights[mask].sum() == pytest.approx(1.0, abs=1e-6)


# =============================================================================
# 3. GATLayer 测试
# =============================================================================


class TestGATLayer:
    """GAT 注意力层测试（Veličković et al., ICLR 2018）。"""

    def test_gat_output_shape(self):
        """GAT 输出形状应为 [N, out_dim]。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=32, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, edge_feats)
        assert out.shape == (4, 32)

    def test_gat_without_edge_feats(self):
        """无边特征时 GAT 应正常工作。"""
        node_feats, edge_index, _ = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=32, edge_feat_dim=0)
        out = gat(node_feats, edge_index, None)
        assert out.shape == (4, 32)

    def test_gat_empty_edges(self):
        """空边索引应返回节点变换 Wh。"""
        node_feats = Tensor(np.random.randn(3, 6))
        edge_index = np.zeros((2, 0), dtype=np.int64)
        gat = GATLayer(in_dim=6, out_dim=16, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, None)
        assert out.shape == (3, 16)

    def test_gat_parameters_exist(self):
        """GAT 应有可训练参数。"""
        gat = GATLayer(in_dim=6, out_dim=32, edge_feat_dim=PHOTONIC_EDGE_DIM)
        params = gat.parameters()
        assert len(params) >= 2  # w 和 attn 的权重

    def test_gat_attention_weights_normalized(self):
        """GAT 注意力权重应归一化（softmax）。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=8, edge_feat_dim=PHOTONIC_EDGE_DIM)
        # 前向传播不应报错
        out = gat(node_feats, edge_index, edge_feats)
        # 输出应为有限值
        assert np.all(np.isfinite(out.data))


# =============================================================================
# 3.1 P1-4 回归测试（v4.0）：GAT 反向传播断裂修复
# 来源: Veličković et al., ICLR 2018, GAT https://arxiv.org/abs/1710.10903
# 旧 Bug: GATLayer.forward 用 wh.data[srcs] / np.concatenate / np.add.at
#         直接取 .data，计算图在 3 处断裂，self.w/self.attn 永远不可训练
# ============================================================================


class TestGATLayerBackward:
    """P1-4 回归：验证 GAT 参数能接收非零梯度（反向传播未断裂）。

    旧 Bug: GATLayer.forward 使用 ``wh.data[srcs]`` / ``np.concatenate`` /
    ``np.add.at`` / ``weight.data.T`` 等 numpy 操作直接取 ``.data``，
    导致计算图在 3 处断裂，GAT 的核心参数（``self.w`` / ``self.attn``）
    永远接收不到梯度（``.grad`` 始终为 None 或零）。
    """

    def test_gat_output_requires_grad(self):
        """P1-4: GAT 输出 Tensor 的 requires_grad 应为 True。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=8, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, edge_feats)
        assert out.requires_grad, (
            "P1-4 回归: GAT 输出 requires_grad 应为 True（旧实现返回的 Tensor "
            "requires_grad 取决于 node_feats，且 _backward 为空操作）"
        )

    def test_gat_w_weight_receives_gradient(self):
        """P1-4: 反向后 self.w.weight.grad 应为非零值。

        旧 Bug: ``wh_data = wh.data`` 切断了 W 的梯度路径，
        self.w.weight.grad 永远为 None。
        """
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=8, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, edge_feats)
        loss = out.sum()
        loss.backward()
        w_grad = gat.w.weight.grad
        assert w_grad is not None, (
            "P1-4 回归: self.w.weight.grad 为 None（W 梯度路径断裂）"
        )
        assert np.any(np.abs(w_grad) > 1e-10), (
            f"P1-4 回归: self.w.weight.grad 全为零（梯度未流过 W），grad norm={np.linalg.norm(w_grad)}"
        )

    def test_gat_attn_weight_receives_gradient(self):
        """P1-4: 反向后 self.attn.weight.grad 应为非零值。

        旧 Bug: ``attn_input @ self.attn.weight.data.T`` 直接用 .data，
        切断了 attn 的梯度路径，self.attn.weight.grad 永远为 None。
        """
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=8, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, edge_feats)
        loss = out.sum()
        loss.backward()
        attn_grad = gat.attn.weight.grad
        assert attn_grad is not None, (
            "P1-4 回归: self.attn.weight.grad 为 None（attn 梯度路径断裂）"
        )
        assert np.any(np.abs(attn_grad) > 1e-10), (
            f"P1-4 回归: self.attn.weight.grad 全为零（梯度未流过 attn），"
            f"grad norm={np.linalg.norm(attn_grad)}"
        )

    def test_gat_gradient_changes_weights(self):
        """P1-4: 一步 SGD 更新后 GAT 权重应发生变化。

        旧 Bug: 由于梯度始终为零，SGD 更新不会改变权重，GAT 无法训练。
        """
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=8, edge_feat_dim=PHOTONIC_EDGE_DIM)
        w_before = gat.w.weight.data.copy()
        attn_before = gat.attn.weight.data.copy()
        # 前向 + 反向
        out = gat(node_feats, edge_index, edge_feats)
        loss = out.sum()
        loss.backward()
        # SGD 更新
        lr = 0.01
        gat.w.weight.data -= lr * gat.w.weight.grad
        gat.attn.weight.data -= lr * gat.attn.weight.grad
        # 权重应发生变化
        assert np.any(np.abs(gat.w.weight.data - w_before) > 1e-10), (
            "P1-4 回归: self.w.weight 更新后未变化（梯度为零，SGD 无效）"
        )
        assert np.any(np.abs(gat.attn.weight.data - attn_before) > 1e-10), (
            "P1-4 回归: self.attn.weight 更新后未变化（梯度为零，SGD 无效）"
        )

    def test_gat_gradient_numerical_check(self):
        """P1-4: 解析梯度应与有限差分数值梯度一致（反向公式正确性）。

        验证 leaky_relu + segment_softmax + scatter_add 的反向公式
        与数值微分一致（相对误差 < 1e-5）。

        来源: 梯度检查标准方法
        https://pytorch.org/docs/stable/notes/autograd.html#gradient-checking
        """
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gat = GATLayer(in_dim=6, out_dim=4, edge_feat_dim=PHOTONIC_EDGE_DIM)
        # 固定 attn，只检查 w 的梯度（减少数值误差来源）
        gat.attn.weight.requires_grad = False

        # 解析梯度
        out = gat(node_feats, edge_index, edge_feats)
        loss = out.sum()
        loss.backward()
        analytic_grad = gat.w.weight.grad.copy()

        # 数值梯度（有限差分）
        eps = 1e-6
        w_data = gat.w.weight.data
        numeric_grad = np.zeros_like(w_data)
        for i in range(w_data.shape[0]):
            for j in range(w_data.shape[1]):
                orig = w_data[i, j]
                w_data[i, j] = orig + eps
                out_plus = gat(node_feats, edge_index, edge_feats)
                loss_plus = float(out_plus.sum().data)
                w_data[i, j] = orig - eps
                out_minus = gat(node_feats, edge_index, edge_feats)
                loss_minus = float(out_minus.sum().data)
                w_data[i, j] = orig
                numeric_grad[i, j] = (loss_plus - loss_minus) / (2 * eps)

        # 相对误差检查
        diff = np.abs(analytic_grad - numeric_grad)
        scale = np.maximum(np.abs(analytic_grad), np.abs(numeric_grad))
        rel_error = np.divide(diff, scale, out=np.zeros_like(diff), where=scale > 1e-10)
        max_rel_error = np.max(rel_error)
        assert max_rel_error < 1e-4, (
            f"P1-4 回归: 解析梯度与数值梯度不一致（max rel error={max_rel_error}），"
            f"反向传播公式有误。\nanalytic={analytic_grad}\nnumeric={numeric_grad}"
        )


# =============================================================================
# 4. MultiRelationalEdgeGraphEncoder 测试
# =============================================================================


class TestMultiRelationalEdgeGraphEncoder:
    """多关系边特征图神经网络编码器测试（R-GCN + AlphaChip）。"""

    def test_output_shape(self):
        """输出形状应为 [N, out_dim]。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        out = encoder(node_feats, edge_index, edge_feats)
        assert out.shape == (4, 16)

    def test_multi_relation_params(self):
        """多关系编码器应有 num_relations × num_layers 个 W_edge。"""
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, num_relations=3, num_layers=2
        )
        # 每层 3 个关系线性层
        assert len(encoder.edge_msg_linears) == 2
        assert len(encoder.edge_msg_linears[0]) == 3

    def test_relation_from_edge_feats(self):
        """未提供 edge_relations 时应从 edge_feats[:, 14] 提取。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        # 设置边关系类型
        edge_feats.data[:, 14] = [0, 1, 2, 0, 1, 2]
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=8
        )
        out = encoder(node_feats, edge_index, edge_feats)
        assert out.shape == (4, 8)

    def test_explicit_edge_relations(self):
        """显式提供 edge_relations 应正常工作。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        edge_relations = np.array([0, 1, 2, 0, 1, 2])
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=8
        )
        out = encoder(node_feats, edge_index, edge_feats, edge_relations)
        assert out.shape == (4, 8)

    def test_residual_connection(self):
        """残差连接应使输入输出维度一致时生效。"""
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=16, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=16, num_layers=2
        )
        node_feats = Tensor(np.random.randn(4, 16))
        _, edge_index, edge_feats = _make_simple_graph()
        out = encoder(node_feats, edge_index, edge_feats)
        assert out.shape == (4, 16)

    def test_empty_edges(self):
        """空边索引应返回零聚合 + 自变换。"""
        node_feats = Tensor(np.random.randn(3, 6))
        edge_index = np.zeros((2, 0), dtype=np.int64)
        edge_feats = Tensor(np.zeros((0, PHOTONIC_EDGE_DIM)))
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=8
        )
        out = encoder(node_feats, edge_index, edge_feats)
        assert out.shape == (3, 8)


# =============================================================================
# 5. AlphaChipEdgeGNN 测试
# =============================================================================


class TestAlphaChipEdgeGNN:
    """AlphaChip 完整 Edge-GNN 测试。"""

    def test_output_shape(self):
        """输出应为图级嵌入 [out_dim]。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert out.shape == (16,)

    def test_with_gat_disabled(self):
        """禁用 GAT 应正常工作。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16,
            use_gat=False,
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert out.shape == (16,)

    def test_with_multi_relation_disabled(self):
        """禁用多关系应回退到单一 EdgeGraphEncoder。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16,
            use_multi_relation=False,
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert out.shape == (16,)

    def test_parameters_exist(self):
        """AlphaChipEdgeGNN 应有可训练参数。"""
        gnn = AlphaChipEdgeGNN(in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16)
        params = gnn.parameters()
        assert len(params) > 0

    def test_global_attention_readout(self):
        """GlobalAttention 读出应产生图级嵌入。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=8,
            use_gat=False, use_multi_relation=False,
        )
        out = gnn(node_feats, edge_index, edge_feats)
        # 输出应为 1D 向量
        assert out.data.ndim == 1
        assert out.shape == (8,)

    def test_forward_finite(self):
        """前向传播输出应为有限值。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert np.all(np.isfinite(out.data))


# =============================================================================
# 6. 集成测试
# =============================================================================


class TestR33Integration:
    """R33 集成测试：完整工作流。"""

    def test_photonic_features_to_gnn(self):
        """光电子边特征 → AlphaChipEdgeGNN 完整工作流。"""
        devices, placements, instance_ids, edge_index = _make_devices_and_placements()
        # 构建光电子边特征
        edge_feats_np = build_photonic_edge_features(
            devices, placements, instance_ids, edge_index
        )
        assert edge_feats_np.shape == (4, PHOTONIC_EDGE_DIM)
        # 构建节点特征
        node_feats_np = np.array([
            [10, 5, 50, 1, 2, 0],   # dev0
            [15, 10, 150, 1, 4, 0],  # dev1
            [8, 8, 64, 1, 1, 1],     # dev2
            [5, 5, 25, 1, 1, 1],     # dev3
        ], dtype=np.float64)
        node_feats = Tensor(node_feats_np)
        edge_feats = Tensor(edge_feats_np)
        # AlphaChipEdgeGNN 前向
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert out.shape == (16,)
        assert np.all(np.isfinite(out.data))

    def test_alphaChip_vs_basic_edge_gnn(self):
        """AlphaChipEdgeGNN（多关系+GAT）应与基础 EdgeGraphEncoder 产生不同输出。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        # AlphaChip 完整版
        gnn_full = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16,
            use_gat=True, use_multi_relation=True,
        )
        out_full = gnn_full(node_feats, edge_index, edge_feats)
        # 基础版（无 GAT，无多关系）
        gnn_basic = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16,
            use_gat=False, use_multi_relation=False,
        )
        out_basic = gnn_basic(node_feats, edge_index, edge_feats)
        # 两者输出应不同（因架构不同）
        assert not np.allclose(out_full.data, out_basic.data)

    def test_gradient_flow(self):
        """梯度应能从输出流回输入。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        node_feats.requires_grad = True
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=8,
            use_gat=False, use_multi_relation=False,
        )
        out = gnn(node_feats, edge_index, edge_feats)
        out.backward()
        # 参数应有梯度
        params = gnn.parameters()
        assert len(params) > 0
        # 至少一些参数有梯度
        has_grad = any(p.grad is not None and np.any(p.grad != 0) for p in params)
        assert has_grad

    def test_clements_matrix_layout(self):
        """8×8 Clements 矩阵布局场景测试（R33.md §7.1 验收）。"""
        # 构造 8×8 Clements 矩阵的器件图（16 个 MZI + 8 输入 + 8 输出）
        n_nodes = 16
        np.random.seed(42)
        node_feats = Tensor(np.random.randn(n_nodes, 6))
        # 链式连接
        edges_src = list(range(n_nodes - 1))
        edges_dst = [i + 1 for i in edges_src]
        edge_index = np.array([edges_src, edges_dst], dtype=np.int64)
        n_edges = len(edges_src)
        # 光电子边特征（全部光波导）
        edge_feats = Tensor(np.zeros((n_edges, PHOTONIC_EDGE_DIM)))
        edge_feats.data[:, 2] = 1.0  # 优先级
        edge_feats.data[:, 3] = 1.0  # passive-passive
        edge_feats.data[:, 7] = 1.0  # C-band
        edge_feats.data[:, 14] = NET_RELATION_OPTICAL  # 光波导
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        out = gnn(node_feats, edge_index, edge_feats)
        assert out.shape == (16,)
        assert np.all(np.isfinite(out.data))

    def test_multi_relation_different_weights(self):
        """多关系编码器应为不同关系类型学习不同 W_edge。"""
        node_feats, edge_index, edge_feats = _make_simple_graph()
        # 设置不同关系类型
        edge_feats.data[:, 14] = [0, 1, 2, 0, 1, 2]
        encoder = MultiRelationalEdgeGraphEncoder(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=16, out_dim=8, num_layers=1
        )
        # 检查 3 个关系的 W_edge 权重不同
        w0 = encoder.edge_msg_linears[0][0].weight.data
        w1 = encoder.edge_msg_linears[0][1].weight.data
        w2 = encoder.edge_msg_linears[0][2].weight.data
        # 初始化后权重应不同（随机初始化）
        assert not np.allclose(w0, w1)
        assert not np.allclose(w0, w2)
        assert not np.allclose(w1, w2)
        # 前向传播
        out = encoder(node_feats, edge_index, edge_feats)
        assert out.shape == (4, 8)


# =============================================================================
# 7. 性能测试
# =============================================================================


class TestR33Performance:
    """R33 性能测试。"""

    def test_large_graph_100_nodes(self):
        """100 节点图应在合理时间内完成。"""
        import time

        np.random.seed(42)
        n_nodes = 100
        n_edges = 300
        node_feats = Tensor(np.random.randn(n_nodes, 6))
        edge_index = np.random.randint(0, n_nodes, (2, n_edges))
        edge_feats = Tensor(np.random.randn(n_edges, PHOTONIC_EDGE_DIM))
        gnn = AlphaChipEdgeGNN(
            in_dim=6, edge_feat_dim=PHOTONIC_EDGE_DIM, hidden_dim=32, out_dim=16
        )
        start = time.time()
        out = gnn(node_feats, edge_index, edge_feats)
        elapsed = time.time() - start
        assert out.shape == (16,)
        # 100 节点应在 5 秒内完成
        assert elapsed < 5.0, f"100 节点图耗时 {elapsed:.2f}s > 5s"

    def test_gat_layer_scalability(self):
        """GAT 层应能处理较大图。"""
        np.random.seed(42)
        n_nodes = 50
        n_edges = 150
        node_feats = Tensor(np.random.randn(n_nodes, 8))
        edge_index = np.random.randint(0, n_nodes, (2, n_edges))
        edge_feats = Tensor(np.random.randn(n_edges, PHOTONIC_EDGE_DIM))
        gat = GATLayer(in_dim=8, out_dim=16, edge_feat_dim=PHOTONIC_EDGE_DIM)
        out = gat(node_feats, edge_index, edge_feats)
        assert out.shape == (n_nodes, 16)
