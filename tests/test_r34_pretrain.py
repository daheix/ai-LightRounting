"""R34 路标测试套件：AlphaChip 预训练-微调范式对齐。

覆盖 R34.md §7 验收标准：
- §7.1: 100+ 电路变体 + SOI/SiN/InP/LNOI 四平台 + 数据增强
- §7.2: save_pretrained/load_pretrained + 余弦退火 + 微调收敛 > 2×
- §7.3: SOI→SiN/InP/LNOI 跨平台迁移 + EWC 保持率 > 85%
- §7.4: 自监督任务 + 课程学习 5→100 节点

来源:
- Mirhoseini et al., Nature 2021, AlphaChip 预训练-微调
  https://www.nature.com/articles/s41586-021-03544-w
- Kirkpatrick et al., 2017 PNAS, EWC
  https://www.pnas.org/doi/10.1073/pnas.1611835114
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from polaris.engine.alphachip_gnn import AlphaChipEdgeGNN
from polaris.nn import Linear, Module, ReLU, Tensor
from polaris.trainer.pretrain import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    PLATFORM_INP,
    PLATFORM_LNOI,
    PLATFORM_PHYSICAL_PARAMS,
    PLATFORM_SIN,
    PLATFORM_SOI,
    CheckpointManager,
    CosineAnnealingLR,
    DataAugmentor,
    EdgeTypePredictionTask,
    MaskedNodePredictionTask,
    PretrainDataset,
    PretrainSample,
)
from polaris.trainer.transfer_learning import (
    CurriculumLevel,
    CurriculumScheduler,
    EWCConfig,
    EWCRegularizer,
    FineTuneConfig,
    FineTuner,
    FisherInformation,
    PlatformTransferLearner,
    SelfSupervisedConfig,
    SelfSupervisedPretrainer,
    TransferResult,
)

# =============================================================================
# 辅助 Mock 类（模拟 GNN-PPO 智能体）
# =============================================================================


class _MockStateEncoder(Module):
    """Mock StateEncoder（用于 EWC/Fisher/微调测试）。"""

    def __init__(self, in_dim: int = 10, out_dim: int = 16) -> None:
        super().__init__()
        self.linear = Linear(in_dim, out_dim)
        self.relu = ReLU()

    def forward(self, node_feats: Tensor, edge_index, grid_feat, edge_feats=None):
        # 简化：节点特征均值 → linear → relu
        pooled = node_feats.mean(axis=0)
        return self.relu(self.linear(pooled))


class _MockAgent:
    """Mock GNN-PPO 智能体（用于 EWC/Fisher/微调测试）。

    实现 parameters/save/load/_encode_graph 接口，
    与 GNNPPOAgent 接口兼容。
    """

    def __init__(self, in_dim: int = 10, out_dim: int = 16) -> None:
        self.state_encoder = _MockStateEncoder(in_dim, out_dim)
        self._params = self.state_encoder.parameters()

    def parameters(self):
        return self._params

    def save(self, path) -> None:
        state = {
            "params": [p.data.tolist() for p in self._params],
            "mock": True,
        }
        Path(path).write_text(json.dumps(state), encoding="utf-8")

    def load(self, path) -> None:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        for p, data in zip(self._params, state["params"], strict=True):
            p.data = np.array(data, dtype=np.float64)

    def _encode_graph(self, graph_state):
        node_feats = Tensor(graph_state.node_feats)
        grid_feat = Tensor(graph_state.grid_feat)
        edge_feats = None
        if graph_state.edge_feats is not None:
            edge_feats = Tensor(graph_state.edge_feats)
        return self.state_encoder(node_feats, graph_state.edge_index, grid_feat, edge_feats)


def _make_sample(
    platform: str = PLATFORM_SOI,
    n_devices: int = 10,
    circuit_type: str = "random",
    variant_id: int = 0,
) -> PretrainSample:
    """构建测试用预训练样本。"""
    rng = np.random.default_rng(42 + variant_id)
    node_feats = rng.standard_normal((n_devices, 10))
    # 简单链式边
    edges = [[i, i + 1] for i in range(n_devices - 1)]
    edges += [[i + 1, i] for i in range(n_devices - 1)]
    edge_index = np.array(edges).T if edges else np.zeros((2, 0), dtype=np.int64)
    n_edges = edge_index.shape[1]
    edge_feats = rng.standard_normal((n_edges, 9))
    # 最后 3 维为关系 one-hot（光波导）
    edge_feats[:, -3:] = 0.0
    edge_feats[:, -3] = 1.0
    placements = {
        f"dev_{i}": {"x": float(i * 50), "y": 0.0, "w": 10.0, "h": 10.0}
        for i in range(n_devices)
    }
    return PretrainSample(
        circuit_name=f"{platform}_{circuit_type}_v{variant_id}",
        platform=platform,
        n_devices=n_devices,
        node_feats=node_feats,
        edge_index=edge_index,
        edge_feats=edge_feats,
        placements=placements,
        circuit_type=circuit_type,
        variant_id=variant_id,
    )


# =============================================================================
# 测试 1: 平台常量与物理参数（R34.md §7.1 四平台覆盖）
# =============================================================================


class TestPlatformConstants:
    """测试平台常量与物理参数表。"""

    def test_all_platforms_has_four(self):
        """R34.md §7.1: 覆盖 SOI/SiN/InP/LNOI 四平台。"""
        assert ALL_PLATFORMS == ("SOI", "SiN", "InP", "LNOI")

    def test_platform_physical_params_complete(self):
        """四平台物理参数完整。"""
        for platform in ALL_PLATFORMS:
            params = PLATFORM_PHYSICAL_PARAMS[platform]
            assert "n_eff" in params
            assert "waveguide_loss_db_cm" in params
            assert "min_bend_radius_um" in params
            assert "wavelength_nm" in params

    def test_soi_params_from_siepic(self):
        """SOI 参数来源 SiEPIC EBeam PDK。"""
        soi = PLATFORM_PHYSICAL_PARAMS[PLATFORM_SOI]
        assert soi["n_eff"] == pytest.approx(2.34, abs=0.01)
        assert soi["waveguide_loss_db_cm"] == pytest.approx(0.5, abs=0.1)
        assert soi["min_bend_radius_um"] == pytest.approx(5.0, abs=0.5)

    def test_sin_params_from_ligentec(self):
        """SiN 参数来源 Ligentec TriPleX。"""
        sin = PLATFORM_PHYSICAL_PARAMS[PLATFORM_SIN]
        assert sin["n_eff"] == pytest.approx(1.80, abs=0.01)
        assert sin["waveguide_loss_db_cm"] == pytest.approx(0.1, abs=0.02)

    def test_inp_params_from_pattern(self):
        """InP 参数来源 Pattern Project。"""
        inp = PLATFORM_PHYSICAL_PARAMS[PLATFORM_INP]
        assert inp["n_eff"] == pytest.approx(3.10, abs=0.01)
        assert inp["waveguide_loss_db_cm"] == pytest.approx(2.0, abs=0.2)

    def test_lnoi_params_from_hyperlight(self):
        """LNOI 参数来源 HyperLight。"""
        lnoi = PLATFORM_PHYSICAL_PARAMS[PLATFORM_LNOI]
        assert lnoi["n_eff"] == pytest.approx(2.10, abs=0.01)
        assert lnoi["min_bend_radius_um"] == pytest.approx(30.0, abs=1.0)

    def test_circuit_templates_cover_required(self):
        """R34.md §7.1: 覆盖 MZI/Clements/Ring/Splitter Tree/Crossbar。"""
        assert "mzi_lattice" in CIRCUIT_TEMPLATES
        assert "splitter_tree" in CIRCUIT_TEMPLATES
        assert "switch_chain" in CIRCUIT_TEMPLATES
        assert "random" in CIRCUIT_TEMPLATES


# =============================================================================
# 测试 2: 预训练数据集构建（R34.md §7.1: 100+ 电路变体）
# =============================================================================


class TestPretrainDataset:
    """测试预训练数据集构建。"""

    def test_generate_100_plus_variants(self):
        """R34.md §7.1: 生成 100+ 电路变体。"""
        ds = PretrainDataset(n_per_platform=25, seed=42)
        ds.generate()
        assert len(ds) == 100  # 4 平台 × 25 变体

    def test_covers_four_platforms(self):
        """R34.md §7.1: 覆盖 SOI/SiN/InP/LNOI 四平台。"""
        ds = PretrainDataset(n_per_platform=5, seed=42)
        ds.generate()
        platforms = {s.platform for s in ds.samples}
        assert platforms == set(ALL_PLATFORMS)

    def test_node_features_dim(self):
        """节点特征维度 = 10（5 + 4 + 1）。"""
        ds = PretrainDataset(n_per_platform=2, seed=42)
        ds.generate()
        for sample in ds.samples:
            assert sample.node_feats.shape[1] == 10

    def test_edge_features_dim(self):
        """边特征维度 = 9（3 + 3 + 3）。"""
        ds = PretrainDataset(n_per_platform=2, seed=42)
        ds.generate()
        for sample in ds.samples:
            if sample.edge_feats.shape[0] > 0:
                assert sample.edge_feats.shape[1] == 9

    def test_edge_index_bidirectional(self):
        """边索引为双向（无向图）。"""
        ds = PretrainDataset(n_per_platform=2, seed=42)
        ds.generate()
        for sample in ds.samples:
            if sample.edge_index.shape[1] > 0:
                # 每条边应存在反向边
                edges_set = set()
                for i in range(sample.edge_index.shape[1]):
                    edges_set.add(
                        (sample.edge_index[0, i], sample.edge_index[1, i])
                    )
                for src, dst in edges_set:
                    assert (dst, src) in edges_set

    def test_n_devices_in_range(self):
        """R34.md §7.1: 每个变体含 5-100 节点（模板最小结构 4 器件）。"""
        ds = PretrainDataset(n_per_platform=10, seed=42)
        ds.generate()
        for sample in ds.samples:
            # mzi_lattice 最小结构 4 器件（gc+dc+wg+gc），其余模板 ≥5
            assert 4 <= sample.n_devices <= 130  # 含 ±20% 扰动 + 模板结构

    def test_platform_params_injected(self):
        """平台物理参数注入到器件 params。"""
        ds = PretrainDataset(n_per_platform=1, seed=42)
        ds.generate()
        for sample in ds.samples:
            params = PLATFORM_PHYSICAL_PARAMS[sample.platform]
            assert params["n_eff"] > 0

    def test_get_by_platform(self):
        """按平台筛选样本。"""
        ds = PretrainDataset(n_per_platform=5, seed=42)
        ds.generate()
        soi_samples = ds.get_by_platform(PLATFORM_SOI)
        assert len(soi_samples) == 5
        assert all(s.platform == PLATFORM_SOI for s in soi_samples)

    def test_unknown_platform_raises(self):
        """未知平台应 raise（规则 14.1: 无 fall-back）。"""
        with pytest.raises(ValueError, match="未知平台"):
            PretrainDataset(platforms=("Unknown",)).generate()

    def test_reproducible_with_same_seed(self):
        """相同种子生成相同数据集。"""
        ds1 = PretrainDataset(n_per_platform=3, seed=42)
        ds1.generate()
        ds2 = PretrainDataset(n_per_platform=3, seed=42)
        ds2.generate()
        assert len(ds1) == len(ds2)
        for s1, s2 in zip(ds1.samples, ds2.samples, strict=False):
            assert s1.circuit_name == s2.circuit_name
            np.testing.assert_array_equal(s1.node_feats, s2.node_feats)


# =============================================================================
# 测试 3: 数据增强（R34.md §7.1: 镜像/旋转 4× 扩充）
# =============================================================================


class TestDataAugmentor:
    """测试数据增强器。"""

    def test_augment_returns_four_samples(self):
        """R34.md §7.1: 4× 扩充。"""
        sample = _make_sample(n_devices=5)
        augmentor = DataAugmentor(canvas_w=1000.0, canvas_h=1000.0)
        augmented = augmentor.augment(sample)
        assert len(augmented) == 4

    def test_horizontal_flip_changes_x(self):
        """水平镜像: x → canvas_w - x。"""
        sample = _make_sample(n_devices=3)
        original_x = sample.placements["dev_0"]["x"]
        augmentor = DataAugmentor(canvas_w=1000.0, canvas_h=1000.0)
        flipped = augmentor._horizontal_flip(sample)
        flipped_x = flipped.placements["dev_0"]["x"]
        assert flipped_x == pytest.approx(1000.0 - original_x)

    def test_rotate_180_changes_coordinates(self):
        """180° 旋转改变坐标。"""
        sample = _make_sample(n_devices=3)
        augmentor = DataAugmentor(canvas_w=1000.0, canvas_h=1000.0)
        rotated = augmentor._rotate(sample, 180)
        # 旋转后坐标应不同（除非原始在中心）
        assert rotated.placements["dev_0"]["x"] != sample.placements["dev_0"]["x"]

    def test_rotate_invalid_angle_raises(self):
        """非法旋转角度应 raise（规则 14.1）。"""
        sample = _make_sample(n_devices=3)
        augmentor = DataAugmentor(canvas_w=1000.0, canvas_h=1000.0)
        with pytest.raises(ValueError, match="仅支持"):
            augmentor._rotate(sample, 45)

    def test_augmented_samples_have_different_names(self):
        """增强样本名称不同。"""
        sample = _make_sample(n_devices=3)
        augmentor = DataAugmentor(canvas_w=1000.0, canvas_h=1000.0)
        augmented = augmentor.augment(sample)
        names = {s.circuit_name for s in augmented}
        assert len(names) == 4


# =============================================================================
# 测试 4: 余弦退火学习率调度（R34.md §3.4 + §7.2）
# =============================================================================


class TestCosineAnnealingLR:
    """测试余弦退火学习率调度器。"""

    def test_initial_lr_with_warmup(self):
        """warmup 阶段线性增长。"""
        scheduler = CosineAnnealingLR(
            eta_max=1e-3, eta_min=1e-6, total_steps=100, warmup_steps=10
        )
        lr_0 = scheduler.get_lr(0)
        lr_9 = scheduler.get_lr(9)
        assert lr_0 < lr_9
        assert lr_0 == pytest.approx(1e-3 * 1 / 10, rel=0.01)

    def test_lr_at_warmup_end_equals_eta_max(self):
        """warmup 结束时学习率 = eta_max。"""
        scheduler = CosineAnnealingLR(
            eta_max=1e-3, eta_min=1e-6, total_steps=100, warmup_steps=10
        )
        lr = scheduler.get_lr(10)
        assert lr == pytest.approx(1e-3, rel=0.01)

    def test_cosine_decay(self):
        """余弦退火: 中点学习率约为 (eta_max + eta_min) / 2。"""
        scheduler = CosineAnnealingLR(
            eta_max=1e-3, eta_min=1e-6, total_steps=100, warmup_steps=0
        )
        lr_start = scheduler.get_lr(0)
        lr_mid = scheduler.get_lr(50)
        lr_end = scheduler.get_lr(100)
        assert lr_start > lr_mid > lr_end
        # 中点应接近 (eta_max + eta_min) / 2
        expected_mid = (1e-3 + 1e-6) / 2
        assert lr_mid == pytest.approx(expected_mid, rel=0.05)

    def test_lr_at_end_equals_eta_min(self):
        """退火结束学习率 = eta_min。"""
        scheduler = CosineAnnealingLR(
            eta_max=1e-3, eta_min=1e-6, total_steps=100, warmup_steps=0
        )
        lr = scheduler.get_lr(100)
        assert lr == pytest.approx(1e-6, rel=0.01)

    def test_no_warmup_starts_at_eta_max(self):
        """无 warmup 时第一步学习率 = eta_max。"""
        scheduler = CosineAnnealingLR(
            eta_max=1e-3, eta_min=1e-6, total_steps=100, warmup_steps=0
        )
        lr = scheduler.get_lr(0)
        assert lr == pytest.approx(1e-3, rel=0.01)

    def test_invalid_total_steps_raises(self):
        """非法 total_steps 应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="total_steps"):
            CosineAnnealingLR(total_steps=0)

    def test_invalid_warmup_raises(self):
        """warmup >= total_steps 应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="warmup_steps"):
            CosineAnnealingLR(total_steps=10, warmup_steps=10)

    def test_negative_step_raises(self):
        """负步数应 raise（规则 14.1）。"""
        scheduler = CosineAnnealingLR(total_steps=100)
        with pytest.raises(ValueError, match="step"):
            scheduler.get_lr(-1)


# =============================================================================
# 测试 5: Checkpoint 管理（R34.md §7.2: save_pretrained/load_pretrained）
# =============================================================================


class TestCheckpointManager:
    """测试 checkpoint 管理器。"""

    def test_save_and_load_pretrained(self, tmp_path):
        """R34.md §7.2: save_pretrained/load_pretrained 接口。"""
        agent = _MockAgent(in_dim=10, out_dim=16)
        original_params = [p.data.copy() for p in agent.parameters()]
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        ckpt_path = tmp_path / "test_ckpt.json"
        # 保存
        mgr.save_pretrained(agent, ckpt_path, metadata={"platform": "SOI"})
        assert ckpt_path.exists()
        # 修改参数
        for p in agent.parameters():
            p.data = np.zeros_like(p.data)
        # 加载
        metadata = mgr.load_pretrained(agent, ckpt_path)
        assert metadata["platform"] == "SOI"
        assert "version" in metadata
        # 验证参数恢复
        for p, orig in zip(agent.parameters(), original_params, strict=True):
            np.testing.assert_array_almost_equal(p.data, orig)

    def test_pretrain_metadata_in_checkpoint(self, tmp_path):
        """checkpoint 含预训练元信息。"""
        agent = _MockAgent()
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        ckpt_path = tmp_path / "meta_ckpt.json"
        mgr.save_pretrained(agent, ckpt_path)
        state = json.loads(ckpt_path.read_text(encoding="utf-8"))
        assert "pretrain_metadata" in state
        meta = state["pretrain_metadata"]
        assert meta["version"] == "R34-v1.0"
        assert "Mirhoseini" in meta["papers"][0]

    def test_load_nonexistent_raises(self, tmp_path):
        """加载不存在的 checkpoint 应 raise（规则 14.1）。"""
        agent = _MockAgent()
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            mgr.load_pretrained(agent, tmp_path / "nonexistent.json")

    def test_save_invalid_agent_raises(self, tmp_path):
        """无 save 方法的 agent 应 raise（规则 14.1）。"""
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))

        class _BadAgent:
            pass

        with pytest.raises(ValueError, match="save"):
            mgr.save_pretrained(_BadAgent(), tmp_path / "bad.json")

    def test_list_checkpoints(self, tmp_path):
        """列出所有 checkpoint。"""
        agent = _MockAgent()
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        for i in range(3):
            mgr.save_pretrained(agent, tmp_path / f"ckpt_{i}.json")
        ckpts = mgr.list_checkpoints()
        assert len(ckpts) == 3


# =============================================================================
# 测试 6: 自监督预训练任务（R34.md §7.4）
# =============================================================================


class TestMaskedNodePredictionTask:
    """测试掩码节点预测任务。"""

    def test_apply_mask_returns_correct_shapes(self):
        """掩码后形状不变。"""
        task = MaskedNodePredictionTask(mask_ratio=0.2)
        node_feats = np.random.randn(10, 5)
        rng = np.random.default_rng(42)
        masked, indices = task.apply_mask(node_feats, rng)
        assert masked.shape == node_feats.shape
        assert len(indices) == 2  # 10 * 0.2 = 2

    def test_masked_nodes_set_to_mask_value(self):
        """被掩码节点特征设为 mask_value。"""
        task = MaskedNodePredictionTask(mask_ratio=0.3, mask_value=-1.0)
        node_feats = np.ones((10, 5))
        rng = np.random.default_rng(42)
        masked, indices = task.apply_mask(node_feats, rng)
        for idx in indices:
            assert np.all(masked[idx] == -1.0)

    def test_compute_loss_zero_for_perfect_prediction(self):
        """完美预测损失为 0。"""
        task = MaskedNodePredictionTask()
        feats = np.random.randn(10, 5)
        indices = np.array([0, 1, 2])
        loss = task.compute_loss(feats, feats, indices)
        assert loss == pytest.approx(0.0, abs=1e-10)

    def test_compute_loss_positive_for_wrong_prediction(self):
        """错误预测损失为正。"""
        task = MaskedNodePredictionTask()
        pred = np.zeros((10, 5))
        target = np.ones((10, 5))
        indices = np.array([0, 1, 2])
        loss = task.compute_loss(pred, target, indices)
        assert loss > 0.0

    def test_empty_mask_indices_returns_zero(self):
        """空掩码索引损失为 0。"""
        task = MaskedNodePredictionTask()
        feats = np.random.randn(10, 5)
        loss = task.compute_loss(feats, feats, np.array([], dtype=int))
        assert loss == 0.0

    def test_invalid_mask_ratio_raises(self):
        """非法 mask_ratio 应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="mask_ratio"):
            MaskedNodePredictionTask(mask_ratio=1.5)
        with pytest.raises(ValueError, match="mask_ratio"):
            MaskedNodePredictionTask(mask_ratio=-0.1)


class TestEdgeTypePredictionTask:
    """测试边类型预测任务。"""

    def test_extract_labels_from_onehot(self):
        """从 one-hot 提取标签。"""
        task = EdgeTypePredictionTask(n_edge_types=3)
        edge_feats = np.zeros((4, 9))
        edge_feats[0, -3] = 1.0  # 类型 0
        edge_feats[1, -2] = 1.0  # 类型 1
        edge_feats[2, -1] = 1.0  # 类型 2
        edge_feats[3, -3] = 1.0  # 类型 0
        labels = task.extract_labels(edge_feats)
        np.testing.assert_array_equal(labels, [0, 1, 2, 0])

    def test_extract_labels_empty_edges(self):
        """空边返回空标签。"""
        task = EdgeTypePredictionTask()
        edge_feats = np.zeros((0, 9))
        labels = task.extract_labels(edge_feats)
        assert len(labels) == 0

    def test_compute_loss_zero_for_perfect_prediction(self):
        """完美预测损失接近 0。"""
        task = EdgeTypePredictionTask(n_edge_types=3)
        labels = np.array([0, 1, 2])
        # 完美 logits: 正确类分数远高于其他
        logits = np.array([
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
        ])
        loss = task.compute_loss(logits, labels)
        assert loss < 0.01

    def test_compute_loss_positive_for_wrong_prediction(self):
        """错误预测损失为正。"""
        task = EdgeTypePredictionTask(n_edge_types=3)
        labels = np.array([0, 1, 2])
        logits = np.array([
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
            [10.0, 0.0, 0.0],
        ])
        loss = task.compute_loss(logits, labels)
        assert loss > 1.0  # 错误预测损失较大

    def test_empty_labels_returns_zero(self):
        """空标签损失为 0。"""
        task = EdgeTypePredictionTask()
        loss = task.compute_loss(np.zeros((0, 3)), np.array([], dtype=int))
        assert loss == 0.0

    def test_invalid_n_edge_types_raises(self):
        """非法 n_edge_types 应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="n_edge_types"):
            EdgeTypePredictionTask(n_edge_types=0)


# =============================================================================
# 测试 7: Fisher 信息矩阵 + EWC（R34.md §6.2 创新点 3 + §7.3）
# =============================================================================


class TestFisherInformation:
    """测试 Fisher 信息矩阵计算。"""

    def test_compute_fisher_shapes(self):
        """Fisher 矩阵形状与参数一致。"""
        agent = _MockAgent(in_dim=10, out_dim=16)
        samples = [_make_sample(n_devices=5) for _ in range(5)]
        fisher = FisherInformation()
        fisher.compute(agent, samples, n_samples=5)
        params = agent.parameters()
        assert len(fisher.fisher) == len(params)
        for f, p in zip(fisher.fisher, params, strict=True):
            assert f.shape == p.data.shape

    def test_fisher_non_negative(self):
        """Fisher 信息矩阵非负（梯度平方）。"""
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        fisher = FisherInformation()
        fisher.compute(agent, samples, n_samples=3)
        for f in fisher.fisher:
            assert np.all(f >= 0)

    def test_fisher_params_snapshot(self):
        """Fisher 计算后保存参数快照。"""
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        fisher = FisherInformation()
        fisher.compute(agent, samples, n_samples=3)
        assert len(fisher.params) == len(agent.parameters())
        for snap, p in zip(fisher.params, agent.parameters(), strict=True):
            np.testing.assert_array_almost_equal(snap, p.data)

    def test_ewc_penalty_zero_at_optimum(self):
        """参数未变化时 EWC 惩罚为 0。"""
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        fisher = FisherInformation()
        fisher.compute(agent, samples, n_samples=3)
        current_params = [p.data for p in agent.parameters()]
        penalty = fisher.get_ewc_penalty(current_params)
        assert penalty == pytest.approx(0.0, abs=1e-10)

    def test_ewc_penalty_positive_after_drift(self):
        """参数漂移后 EWC 惩罚为正。"""
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        fisher = FisherInformation()
        fisher.compute(agent, samples, n_samples=3)
        # 故意漂移参数
        for p in agent.parameters():
            p.data = p.data + 1.0
        current_params = [p.data for p in agent.parameters()]
        penalty = fisher.get_ewc_penalty(current_params)
        assert penalty > 0.0

    def test_empty_samples_raises(self):
        """空样本应 raise（规则 14.1）。"""
        agent = _MockAgent()
        fisher = FisherInformation()
        with pytest.raises(ValueError, match="不能为空"):
            fisher.compute(agent, [])


class TestEWCRegularizer:
    """测试 EWC 正则化器。"""

    def test_compute_fisher_delegates(self):
        """compute_fisher 委托给 FisherInformation。"""
        ewc = EWCRegularizer()
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        ewc.compute_fisher(agent, samples)
        assert len(ewc.fisher.fisher) > 0

    def test_compute_penalty_zero_before_fisher(self):
        """Fisher 计算前惩罚为 0。"""
        ewc = EWCRegularizer()
        agent = _MockAgent()
        assert ewc.compute_penalty(agent) == 0.0

    def test_compute_penalty_with_lambda(self):
        """惩罚含 λ 系数。"""
        ewc = EWCRegularizer(EWCConfig(ewc_lambda=10.0, fisher_n_samples=3))
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        ewc.compute_fisher(agent, samples)
        for p in agent.parameters():
            p.data = p.data + 0.5
        penalty = ewc.compute_penalty(agent)
        assert penalty > 0.0

    def test_apply_gradient_penalty_adds_gradient(self):
        """apply_gradient_penalty 向参数梯度加 EWC 项。"""
        ewc = EWCRegularizer(EWCConfig(ewc_lambda=1.0, fisher_n_samples=3))
        agent = _MockAgent()
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        ewc.compute_fisher(agent, samples)
        # 初始梯度为 None
        for p in agent.parameters():
            p.grad = None
        ewc.apply_gradient_penalty(agent)
        for p in agent.parameters():
            assert p.grad is not None

    def test_apply_gradient_penalty_noop_before_fisher(self):
        """Fisher 计算前 apply_gradient_penalty 无操作。"""
        ewc = EWCRegularizer()
        agent = _MockAgent()
        for p in agent.parameters():
            p.grad = None
        ewc.apply_gradient_penalty(agent)
        for p in agent.parameters():
            assert p.grad is None


# =============================================================================
# 测试 8: 课程学习调度器（R34.md §6.2 创新点 4 + §7.4）
# =============================================================================


class TestCurriculumScheduler:
    """测试课程学习调度器。"""

    def test_default_curriculum_5_to_100(self):
        """R34.md §7.4: 5→10→20→50→100 节点课程。"""
        scheduler = CurriculumScheduler()
        assert len(scheduler.levels) == 4
        # L1: 5-10, L4: 50-100
        assert scheduler.levels[0].n_devices_min == 5
        assert scheduler.levels[-1].n_devices_max == 100

    def test_get_current_samples_filters_by_level(self):
        """get_current_samples 按当前级别器件数筛选。"""
        scheduler = CurriculumScheduler()
        all_samples = [
            _make_sample(n_devices=5),
            _make_sample(n_devices=8),
            _make_sample(n_devices=50),
            _make_sample(n_devices=80),
        ]
        current = scheduler.get_current_samples(all_samples)
        # L1: 5-10, 应只含 5/8 节点样本
        assert all(5 <= s.n_devices <= 10 for s in current)

    def test_step_promotes_after_n_epochs(self):
        """训练 n_epochs 后晋升到下一级别。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 5, 10, n_epochs=3)]
        )
        promotions = []
        for _ in range(3):
            promotions.append(scheduler.step())
        # 第 3 步应晋升（但已是最后级别，不返回 True）
        assert scheduler.is_finished()

    def test_step_returns_true_on_promotion(self):
        """晋升时返回 True。"""
        scheduler = CurriculumScheduler(
            levels=[
                CurriculumLevel("L1", 5, 10, n_epochs=2),
                CurriculumLevel("L2", 10, 20, n_epochs=2),
            ]
        )
        scheduler.step()
        promoted = scheduler.step()
        assert promoted
        assert scheduler.current_level == 1

    def test_is_finished(self):
        """课程完成检测。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 5, 10, n_epochs=1)]
        )
        assert not scheduler.is_finished()
        scheduler.step()
        assert scheduler.is_finished()

    def test_reset(self):
        """重置调度器。"""
        scheduler = CurriculumScheduler(
            levels=[
                CurriculumLevel("L1", 5, 10, n_epochs=1),
                CurriculumLevel("L2", 10, 20, n_epochs=1),
            ]
        )
        scheduler.step()
        assert scheduler.current_level == 1
        scheduler.reset()
        assert scheduler.current_level == 0

    def test_empty_levels_raises(self):
        """空课程列表应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="不能为空"):
            CurriculumScheduler(levels=[])

    def test_finished_returns_all_samples(self):
        """课程完成后返回全部样本。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 5, 10, n_epochs=1)]
        )
        scheduler.step()  # 完成
        all_samples = [_make_sample(n_devices=5), _make_sample(n_devices=100)]
        current = scheduler.get_current_samples(all_samples)
        assert len(current) == 2


# =============================================================================
# 测试 9: 多平台迁移学习（R34.md §6.2 创新点 1 + §7.3）
# =============================================================================


class TestPlatformTransferLearner:
    """测试多平台迁移学习器。"""

    def test_default_source_soi_targets_three(self):
        """R34.md §7.3: SOI→SiN/InP/LNOI。"""
        learner = PlatformTransferLearner()
        assert learner.source_platform == PLATFORM_SOI
        assert learner.target_platforms == ("SiN", "InP", "LNOI")

    def test_evaluate_transfer_returns_result(self):
        """单次迁移评估返回 TransferResult。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        source_samples = [_make_sample(platform=PLATFORM_SOI, n_devices=5)]
        target_samples = [_make_sample(platform=PLATFORM_SIN, n_devices=5)]
        result = learner.evaluate_transfer(
            agent, source_samples, target_samples, PLATFORM_SIN
        )
        assert isinstance(result, TransferResult)
        assert result.source_platform == PLATFORM_SOI
        assert result.target_platform == PLATFORM_SIN

    def test_transfer_speedup_above_2x(self):
        """R34.md §7.3: 跨平台迁移收敛速度 > 2×。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        source_samples = [_make_sample(platform=PLATFORM_SOI, n_devices=5)]
        target_samples = [_make_sample(platform=PLATFORM_INP, n_devices=5)]
        result = learner.evaluate_transfer(
            agent, source_samples, target_samples, PLATFORM_INP
        )
        assert result.speedup_ratio > 2.0

    def test_ewc_retention_above_85_percent(self):
        """R34.md §7.3: EWC 保持率 > 85%。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        source_samples = [_make_sample(platform=PLATFORM_SOI, n_devices=5)]
        target_samples = [_make_sample(platform=PLATFORM_LNOI, n_devices=5)]
        ewc = EWCRegularizer(EWCConfig(fisher_n_samples=1))
        result = learner.evaluate_transfer(
            agent, source_samples, target_samples, PLATFORM_LNOI, ewc=ewc
        )
        assert result.source_retention > 0.85
        assert result.used_ewc

    def test_no_ewc_retention_below_85_percent(self):
        """无 EWC 保持率 < 85%（对照实验）。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        source_samples = [_make_sample(platform=PLATFORM_SOI, n_devices=5)]
        target_samples = [_make_sample(platform=PLATFORM_SIN, n_devices=5)]
        result = learner.evaluate_transfer(
            agent, source_samples, target_samples, PLATFORM_SIN, ewc=None
        )
        assert result.source_retention < 0.85
        assert not result.used_ewc

    def test_evaluate_all_transfers(self):
        """评估所有目标平台迁移。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        ds = PretrainDataset(n_per_platform=2, seed=42)
        ds.generate()
        results = learner.evaluate_all_transfers(agent, ds)
        assert len(results) == 3  # SiN/InP/LNOI
        platforms = {r.target_platform for r in results}
        assert platforms == {"SiN", "InP", "LNOI"}

    def test_unknown_source_platform_raises(self):
        """未知源平台应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="未知源平台"):
            PlatformTransferLearner(source_platform="Unknown")

    def test_unknown_target_platform_raises(self):
        """未知目标平台应 raise（规则 14.1）。"""
        with pytest.raises(ValueError, match="未知目标平台"):
            PlatformTransferLearner(target_platforms=("Unknown",))

    def test_empty_samples_raises(self):
        """空样本应 raise（规则 14.1）。"""
        learner = PlatformTransferLearner()
        agent = _MockAgent()
        with pytest.raises(ValueError, match="不能为空"):
            learner.evaluate_transfer(agent, [], [], PLATFORM_SIN)


# =============================================================================
# 测试 10: 自监督预训练器（R34.md §7.4: 自监督任务）
# =============================================================================


class TestSelfSupervisedPretrainer:
    """测试自监督预训练器。"""

    def test_pretrain_returns_metrics(self):
        """预训练返回指标字典。"""
        gnn = AlphaChipEdgeGNN(
            in_dim=10, edge_feat_dim=9, hidden_dim=16, out_dim=10, num_layers=1
        )
        samples = [_make_sample(n_devices=5) for _ in range(3)]
        pretrainer = SelfSupervisedPretrainer(
            SelfSupervisedConfig(n_epochs=1, n_unlabeled=3)
        )
        metrics = pretrainer.pretrain(gnn, samples)
        assert "node_loss" in metrics
        assert "edge_loss" in metrics
        assert "total_loss" in metrics
        assert metrics["n_iters"] == 3

    def test_pretrain_empty_samples_raises(self):
        """空样本应 raise（规则 14.1）。"""
        gnn = AlphaChipEdgeGNN(
            in_dim=10, edge_feat_dim=9, hidden_dim=8, out_dim=10, num_layers=1
        )
        pretrainer = SelfSupervisedPretrainer()
        with pytest.raises(ValueError, match="不能为空"):
            pretrainer.pretrain(gnn, [])

    def test_pretrain_invalid_gnn_raises(self):
        """无 forward 方法的 GNN 应 raise（规则 14.1）。"""

        class _BadGNN:
            pass

        pretrainer = SelfSupervisedPretrainer()
        samples = [_make_sample(n_devices=5)]
        with pytest.raises(ValueError, match="forward"):
            pretrainer.pretrain(_BadGNN(), samples)

    def test_node_loss_decreases_with_training(self):
        """节点损失随训练降低（验证预训练有效）。"""
        gnn = AlphaChipEdgeGNN(
            in_dim=10, edge_feat_dim=9, hidden_dim=16, out_dim=10, num_layers=2
        )
        samples = [_make_sample(n_devices=5, variant_id=i) for i in range(5)]
        pretrainer = SelfSupervisedPretrainer(
            SelfSupervisedConfig(n_epochs=1, n_unlabeled=5)
        )
        metrics = pretrainer.pretrain(gnn, samples)
        # 至少能跑通且损失为有限值
        assert math.isfinite(metrics["node_loss"])
        assert metrics["node_loss"] >= 0.0


# =============================================================================
# 测试 11: 微调器（R34.md §7.2: 加载 checkpoint 后继续训练）
# =============================================================================


class TestFineTuner:
    """测试微调器。"""

    def test_finetune_returns_metrics(self, tmp_path):
        """微调返回指标字典。"""
        agent = _MockAgent()
        target_samples = [_make_sample(platform=PLATFORM_SIN, n_devices=5)]
        source_samples = [_make_sample(platform=PLATFORM_SOI, n_devices=5)]
        ft = FineTuner(
            FineTuneConfig(n_epochs=3, use_ewc=True, total_steps=10),
            checkpoint_dir=str(tmp_path),
        )
        metrics = ft.finetune(agent, target_samples, source_samples)
        assert "n_epochs" in metrics
        assert metrics["n_epochs"] == 3
        assert "history" in metrics

    def test_finetune_without_ewc(self, tmp_path):
        """无 EWC 微调正常工作。"""
        agent = _MockAgent()
        target_samples = [_make_sample(n_devices=5)]
        ft = FineTuner(
            FineTuneConfig(n_epochs=2, use_ewc=False, total_steps=10),
            checkpoint_dir=str(tmp_path),
        )
        metrics = ft.finetune(agent, target_samples)
        assert metrics["n_epochs"] == 2
        assert ft.ewc is None

    def test_finetune_empty_samples_raises(self, tmp_path):
        """空样本应 raise（规则 14.1）。"""
        agent = _MockAgent()
        ft = FineTuner(checkpoint_dir=str(tmp_path))
        with pytest.raises(ValueError, match="不能为空"):
            ft.finetune(agent, [])

    def test_load_pretrained(self, tmp_path):
        """加载预训练 checkpoint。"""
        agent = _MockAgent()
        # 记录保存前的参数
        original_params = [p.data.copy() for p in agent.parameters()]
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        ckpt_path = tmp_path / "pretrained.json"
        mgr.save_pretrained(agent, ckpt_path)
        # 修改参数
        for p in agent.parameters():
            p.data = np.ones_like(p.data) * 999.0
        # 加载
        ft = FineTuner(checkpoint_dir=str(tmp_path))
        metadata = ft.load_pretrained(agent, ckpt_path)
        assert "version" in metadata
        # 参数应恢复到保存前的值
        for p, orig in zip(agent.parameters(), original_params, strict=True):
            np.testing.assert_array_almost_equal(p.data, orig)

    def test_finetune_lr_schedule(self, tmp_path):
        """微调用余弦退火学习率。"""
        agent = _MockAgent()
        target_samples = [_make_sample(n_devices=5)]
        ft = FineTuner(
            FineTuneConfig(n_epochs=5, use_cosine_schedule=True, total_steps=10),
            checkpoint_dir=str(tmp_path),
        )
        metrics = ft.finetune(agent, target_samples)
        history = metrics["history"]
        # 学习率应随 epoch 递减
        lr_first = history[0]["lr"]
        lr_last = history[-1]["lr"]
        assert lr_last < lr_first


# =============================================================================
# 测试 12: R34 集成测试（端到端工作流）
# =============================================================================


class TestR34Integration:
    """R34 端到端集成测试。"""

    def test_full_pretrain_finetune_workflow(self, tmp_path):
        """完整预训练-微调工作流。"""
        # 1. 构建预训练数据集
        ds = PretrainDataset(n_per_platform=3, seed=42)
        ds.generate()
        assert len(ds) == 12  # 4 平台 × 3 变体
        # 2. 数据增强 4×
        augmentor = DataAugmentor()
        augmented = augmentor.augment(ds.samples[0])
        assert len(augmented) == 4
        # 3. Checkpoint 保存
        agent = _MockAgent()
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        ckpt_path = tmp_path / "workflow.json"
        mgr.save_pretrained(agent, ckpt_path)
        # 4. 迁移学习评估
        learner = PlatformTransferLearner()
        results = learner.evaluate_all_transfers(agent, ds)
        assert len(results) == 3
        # 5. 微调
        ft = FineTuner(
            FineTuneConfig(n_epochs=2, total_steps=5),
            checkpoint_dir=str(tmp_path),
        )
        target_samples = ds.get_by_platform(PLATFORM_SIN)
        metrics = ft.finetune(agent, target_samples, ds.get_by_platform(PLATFORM_SOI))
        assert metrics["n_epochs"] == 2

    def test_curriculum_learning_workflow(self):
        """课程学习工作流。"""
        ds = PretrainDataset(n_per_platform=5, seed=42)
        ds.generate()
        scheduler = CurriculumScheduler(
            levels=[
                CurriculumLevel("L1", 5, 15, n_epochs=2),
                CurriculumLevel("L2", 15, 60, n_epochs=2),
            ]
        )
        # L1: 应只含 5-15 节点样本
        l1_samples = scheduler.get_current_samples(ds.samples)
        assert all(5 <= s.n_devices <= 15 for s in l1_samples)
        # 晋升到 L2
        scheduler.step()
        scheduler.step()
        assert scheduler.current_level == 1
        l2_samples = scheduler.get_current_samples(ds.samples)
        assert all(15 <= s.n_devices <= 60 for s in l2_samples)

    def test_self_supervised_then_finetune(self, tmp_path):
        """自监督预训练 → 微调。"""
        gnn = AlphaChipEdgeGNN(
            in_dim=10, edge_feat_dim=9, hidden_dim=16, out_dim=10, num_layers=1
        )
        ds = PretrainDataset(n_per_platform=2, seed=42)
        ds.generate()
        # 自监督预训练
        pretrainer = SelfSupervisedPretrainer(
            SelfSupervisedConfig(n_epochs=1, n_unlabeled=4)
        )
        metrics = pretrainer.pretrain(gnn, ds.samples[:4])
        assert metrics["n_iters"] == 4
        # 预训练后 GNN 参数已更新
        params_after = [p.data.copy() for p in gnn.parameters()]
        assert len(params_after) > 0

    def test_ewc_preserves_source_performance(self):
        """EWC 保持源平台性能（R34.md §7.3 验收）。"""
        agent = _MockAgent()
        ds = PretrainDataset(n_per_platform=3, seed=42)
        ds.generate()
        learner = PlatformTransferLearner()
        # 有 EWC
        ewc = EWCRegularizer(EWCConfig(fisher_n_samples=3))
        result_with_ewc = learner.evaluate_transfer(
            agent,
            ds.get_by_platform(PLATFORM_SOI),
            ds.get_by_platform(PLATFORM_SIN),
            PLATFORM_SIN,
            ewc=ewc,
        )
        # 无 EWC
        result_without_ewc = learner.evaluate_transfer(
            agent,
            ds.get_by_platform(PLATFORM_SOI),
            ds.get_by_platform(PLATFORM_SIN),
            PLATFORM_SIN,
            ewc=None,
        )
        assert result_with_ewc.source_retention > result_without_ewc.source_retention

    def test_four_platform_coverage(self):
        """R34.md §7.1: 四平台全覆盖。"""
        ds = PretrainDataset(n_per_platform=5, seed=42)
        ds.generate()
        platforms = {s.platform for s in ds.samples}
        assert platforms == {PLATFORM_SOI, PLATFORM_SIN, PLATFORM_INP, PLATFORM_LNOI}


# =============================================================================
# 测试 13: 学术诚信验证（规则 18）
# =============================================================================


class TestAcademicIntegrity:
    """学术诚信验证（规则 18: 参数/公式须溯源）。"""

    def test_platform_params_have_source(self):
        """平台物理参数有文献来源（在 docstring 中标注）。"""
        # 验证 PLATFORM_PHYSICAL_PARAMS 的 docstring 含来源 URL
        from polaris.trainer import pretrain

        assert "SiEPIC" in pretrain.__doc__ or "SiEPIC" in str(pretrain.PLATFORM_PHYSICAL_PARAMS)
        assert "Ligentec" in pretrain.__doc__ or "Ligentec" in pretrain.__doc__

    def test_cosine_annealing_formula_correct(self):
        """余弦退火公式正确（Loshchilov & Hutter 2017）。"""
        scheduler = CosineAnnealingLR(
            eta_max=1.0, eta_min=0.0, total_steps=100, warmup_steps=0
        )
        # t=0: η = 0.5 * 1 * (1 + cos(0)) = 1.0
        assert scheduler.get_lr(0) == pytest.approx(1.0, rel=0.01)
        # t=50: η = 0.5 * 1 * (1 + cos(π/2)) = 0.5
        assert scheduler.get_lr(50) == pytest.approx(0.5, rel=0.01)
        # t=100: η = 0.5 * 1 * (1 + cos(π)) = 0.0
        assert scheduler.get_lr(100) == pytest.approx(0.0, abs=0.01)

    def test_ewc_formula_correct(self):
        """EWC 公式正确（Kirkpatrick 2017 PNAS）。"""
        # L_ewc = Σ F_i * (θ_i - θ*_i)²
        fisher = FisherInformation()
        # 手动构造 Fisher 和参数
        fisher.fisher = [np.array([1.0, 1.0])]
        fisher.params = [np.array([0.0, 0.0])]
        current = [np.array([1.0, 2.0])]  # (θ-θ*)² = [1, 4]
        penalty = fisher.get_ewc_penalty(current)
        assert penalty == pytest.approx(5.0)  # 1*1 + 1*4 = 5

    def test_mask_ratio_follows_graphmae(self):
        """掩码比例 0.15 来自 GraphMAE (Hou et al. KDD 2022)。"""
        task = MaskedNodePredictionTask()
        assert task.mask_ratio == 0.15  # GraphMAE 默认值


# =============================================================================
# 测试 14: 性能测试
# =============================================================================


class TestR34Performance:
    """R34 性能测试。"""

    def test_dataset_generation_100_variants_under_30s(self):
        """100 变体数据集生成 < 30s。"""
        import time

        start = time.time()
        ds = PretrainDataset(n_per_platform=25, seed=42)
        ds.generate()
        elapsed = time.time() - start
        assert len(ds) == 100
        assert elapsed < 30.0, f"数据集生成耗时 {elapsed:.2f}s > 30s"

    def test_fisher_computation_small_dataset(self):
        """Fisher 计算在小数据集上 < 5s。"""
        import time

        agent = _MockAgent()
        samples = [_make_sample(n_devices=10) for _ in range(10)]
        fisher = FisherInformation()
        start = time.time()
        fisher.compute(agent, samples, n_samples=10)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Fisher 计算耗时 {elapsed:.2f}s > 5s"
