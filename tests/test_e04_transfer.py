"""E04 迁移学习/预训练验收测试。

验证预训练加载、微调和域适应功能。

文献来源:
- Kirkpatrick et al., 2017, EWC (Elastic Weight Consolidation)
  https://www.pnas.org/doi/10.1073/pnas.1611835114
- Bengio et al., 2009, Curriculum Learning
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Mirhoseini et al., Nature 2021, AlphaChip 预训练-微调
  https://www.nature.com/articles/s41586-021-03544-w
- Hou et al., KDD 2022, GraphMAE 自监督图预训练
  https://arxiv.org/abs/2205.10803
- Loshchilov & Hutter, 2017, SGDR 余弦退火
  https://arxiv.org/abs/1608.03983
"""

import numpy as np
import pytest

from polaris.trainer.pretrain import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    CheckpointManager,
    CosineAnnealingLR,
    DataAugmentor,
    EdgeTypePredictionTask,
    MaskedNodePredictionTask,
    PLATFORM_PHYSICAL_PARAMS,
    PLATFORM_SOI,
    PretrainDataset,
    PretrainSample,
)
from polaris.trainer.transfer_learning import (
    DEFAULT_CURRICULUM,
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


class TestPretrainDataset:
    """PretrainDataset 预训练数据集测试。"""

    def test_platform_constants(self):
        """M1: 平台常量定义完整。"""
        assert "SOI" in ALL_PLATFORMS
        assert "SiN" in ALL_PLATFORMS
        assert "InP" in ALL_PLATFORMS
        assert "LNOI" in ALL_PLATFORMS
        assert len(ALL_PLATFORMS) == 4

    def test_physical_params(self):
        """M1: 平台物理参数来自公开文献。"""
        assert PLATFORM_SOI in PLATFORM_PHYSICAL_PARAMS
        soi = PLATFORM_PHYSICAL_PARAMS["SOI"]
        assert "n_eff" in soi
        assert "waveguide_loss_db_cm" in soi
        assert "min_bend_radius_um" in soi
        assert "wavelength_nm" in soi
        assert soi["min_bend_radius_um"] == 5.0

    def test_circuit_templates(self):
        """M1: 电路模板类型完整。"""
        assert "mzi_lattice" in CIRCUIT_TEMPLATES
        assert "splitter_tree" in CIRCUIT_TEMPLATES
        assert "switch_chain" in CIRCUIT_TEMPLATES
        assert "random" in CIRCUIT_TEMPLATES

    def test_init_default(self):
        """M1: 默认初始化。"""
        ds = PretrainDataset(n_per_platform=5, platforms=("SOI",), seed=42)
        assert ds.n_per_platform == 5
        assert len(ds.platforms) == 1
        assert len(ds.samples) == 0

    def test_generate_samples(self):
        """M1: 生成预训练样本。"""
        ds = PretrainDataset(n_per_platform=3, platforms=("SOI", "SiN"), seed=42)
        samples = ds.generate()
        assert len(samples) == 6
        assert all(isinstance(s, PretrainSample) for s in samples)

    def test_sample_fields(self):
        """M1: 样本包含所有必要字段。"""
        ds = PretrainDataset(n_per_platform=2, platforms=("SOI",), seed=42)
        samples = ds.generate()
        s = samples[0]
        assert s.circuit_name
        assert s.platform == "SOI"
        assert s.n_devices > 0
        assert s.node_feats.shape[0] == s.n_devices
        assert s.edge_index.shape[0] == 2
        assert isinstance(s.placements, dict)
        assert s.circuit_type in CIRCUIT_TEMPLATES

    def test_get_by_platform(self):
        """M1: 按平台筛选样本。"""
        ds = PretrainDataset(n_per_platform=2, platforms=("SOI", "SiN"), seed=42)
        ds.generate()
        soi_samples = ds.get_by_platform("SOI")
        sin_samples = ds.get_by_platform("SiN")
        assert len(soi_samples) == 2
        assert len(sin_samples) == 2
        assert all(s.platform == "SOI" for s in soi_samples)
        assert all(s.platform == "SiN" for s in sin_samples)

    def test_len(self):
        """M1: len 返回样本数。"""
        ds = PretrainDataset(n_per_platform=3, platforms=("SOI",), seed=42)
        ds.generate()
        assert len(ds) == 3

    def test_unknown_platform_raises(self):
        """R03: 未知平台生成时抛出异常。"""
        ds = PretrainDataset(n_per_platform=2, platforms=("UNKNOWN",), seed=42)
        with pytest.raises(ValueError):
            ds.generate()


class TestDataAugmentor:
    """DataAugmentor 数据增强测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        aug = DataAugmentor()
        assert aug.canvas_w == 1000.0
        assert aug.canvas_h == 1000.0

    def test_augment_returns_4(self):
        """M2: 4× 数据增强（原图+镜像+旋转90+旋转180）。"""
        aug = DataAugmentor(canvas_w=100.0, canvas_h=100.0)
        sample = PretrainSample(
            circuit_name="test",
            platform="SOI",
            n_devices=2,
            node_feats=np.random.randn(2, 10),
            edge_index=np.array([[0], [1]]),
            edge_feats=np.random.randn(1, 9),
            placements={"d1": {"x": 20.0, "y": 30.0}, "d2": {"x": 60.0, "y": 70.0}},
            circuit_type="random",
            variant_id=0,
        )
        augmented = aug.augment(sample)
        assert len(augmented) == 4

    def test_hflip_changes_x(self):
        """M2: 水平镜像改变 x 坐标。"""
        aug = DataAugmentor(canvas_w=100.0, canvas_h=100.0)
        sample = PretrainSample(
            circuit_name="test", platform="SOI", n_devices=1,
            node_feats=np.random.randn(1, 10),
            edge_index=np.zeros((2, 0), dtype=np.int64),
            edge_feats=np.zeros((0, 9)),
            placements={"d1": {"x": 20.0, "y": 30.0}},
        )
        result = aug._horizontal_flip(sample)
        assert result.placements["d1"]["x"] == 80.0
        assert result.placements["d1"]["y"] == 30.0

    def test_rotate_invalid_angle_raises(self):
        """R03: 无效旋转角度抛出异常。"""
        aug = DataAugmentor()
        sample = PretrainSample(
            circuit_name="test", platform="SOI", n_devices=1,
            node_feats=np.random.randn(1, 10),
            edge_index=np.zeros((2, 0), dtype=np.int64),
            edge_feats=np.zeros((0, 9)),
            placements={"d1": {"x": 0.0, "y": 0.0}},
        )
        with pytest.raises(ValueError):
            aug._rotate(sample, 45)


class TestCosineAnnealingLR:
    """CosineAnnealingLR 余弦退火学习率测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        lr = CosineAnnealingLR()
        assert lr.eta_max == 3e-4
        assert lr.eta_min == 1e-6
        assert lr.total_steps == 1000
        assert lr.warmup_steps == 0

    def test_lr_at_start(self):
        """M2: 初始学习率等于 eta_max。"""
        lr = CosineAnnealingLR(eta_max=1e-3, eta_min=1e-5, total_steps=100)
        assert lr.get_lr(0) == pytest.approx(1e-3, rel=0.01)

    def test_lr_at_end(self):
        """M2: 结束学习率接近 eta_min。"""
        lr = CosineAnnealingLR(eta_max=1e-3, eta_min=1e-5, total_steps=100)
        assert lr.get_lr(100) == pytest.approx(1e-5, rel=0.1)

    def test_lr_monotonic_decreasing(self):
        """M2: 学习率单调递减。"""
        lr = CosineAnnealingLR(total_steps=100)
        lrs = [lr.get_lr(i) for i in range(101)]
        for i in range(len(lrs) - 1):
            assert lrs[i] >= lrs[i + 1] - 1e-12

    def test_warmup_linear_increase(self):
        """M2: warmup 阶段线性增长。"""
        lr = CosineAnnealingLR(eta_max=1e-3, total_steps=100, warmup_steps=10)
        lr0 = lr.get_lr(0)
        lr5 = lr.get_lr(5)
        lr9 = lr.get_lr(9)
        assert lr5 > lr0
        assert lr9 > lr5

    def test_invalid_total_steps_raises(self):
        """R03: 无效 total_steps 抛出异常。"""
        with pytest.raises(ValueError):
            CosineAnnealingLR(total_steps=0)

    def test_invalid_warmup_raises(self):
        """R03: 无效 warmup_steps 抛出异常。"""
        with pytest.raises(ValueError):
            CosineAnnealingLR(total_steps=100, warmup_steps=200)

    def test_negative_step_raises(self):
        """R03: 负步数抛出异常。"""
        lr = CosineAnnealingLR(total_steps=100)
        with pytest.raises(ValueError):
            lr.get_lr(-1)


class TestMaskedNodePrediction:
    """MaskedNodePredictionTask 掩码节点预测测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        task = MaskedNodePredictionTask()
        assert task.mask_ratio == 0.15
        assert task.mask_value == 0.0

    def test_apply_mask(self):
        """M1: 掩码正确应用。"""
        task = MaskedNodePredictionTask(mask_ratio=0.5)
        rng = np.random.default_rng(42)
        feats = np.random.randn(10, 8)
        masked, mask_indices = task.apply_mask(feats, rng)
        assert masked.shape == feats.shape
        assert len(mask_indices) > 0
        assert np.all(masked[mask_indices] == 0.0)

    def test_compute_loss(self):
        """M1: MSE 损失计算正确。"""
        task = MaskedNodePredictionTask()
        pred = np.ones((10, 8))
        target = np.ones((10, 8)) * 2.0
        mask_indices = np.array([0, 1, 2])
        loss = task.compute_loss(pred, target, mask_indices)
        assert loss == pytest.approx(1.0, rel=1e-6)

    def test_empty_mask_loss_zero(self):
        """M1: 空掩码损失为 0。"""
        task = MaskedNodePredictionTask()
        loss = task.compute_loss(np.ones((5, 4)), np.ones((5, 4)), np.array([]))
        assert loss == 0.0

    def test_invalid_mask_ratio_raises(self):
        """R03: 无效 mask_ratio 抛出异常。"""
        with pytest.raises(ValueError):
            MaskedNodePredictionTask(mask_ratio=1.5)


class TestEdgeTypePrediction:
    """EdgeTypePredictionTask 边类型预测测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        task = EdgeTypePredictionTask()
        assert task.n_edge_types == 3

    def test_extract_labels(self):
        """M1: 从边特征提取标签。"""
        task = EdgeTypePredictionTask(n_edge_types=3)
        edge_feats = np.array([
            [0.5, 0.0, 1.0, 0.0, 0.0],
            [0.3, 0.0, 0.0, 1.0, 0.0],
        ])
        labels = task.extract_labels(edge_feats)
        assert labels.shape == (2,)
        assert labels[0] == 0
        assert labels[1] == 1

    def test_compute_loss(self):
        """M1: 交叉熵损失计算。"""
        task = EdgeTypePredictionTask(n_edge_types=3)
        logits = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
        labels = np.array([0, 1])
        loss = task.compute_loss(logits, labels)
        assert loss > 0.0
        assert loss < 1.0

    def test_empty_loss_zero(self):
        """M1: 空边损失为 0。"""
        task = EdgeTypePredictionTask()
        loss = task.compute_loss(np.zeros((0, 3)), np.array([]))
        assert loss == 0.0

    def test_invalid_n_types_raises(self):
        """R03: 无效边类型数抛出异常。"""
        with pytest.raises(ValueError):
            EdgeTypePredictionTask(n_edge_types=0)


class TestCurriculumScheduler:
    """CurriculumScheduler 课程学习调度器测试。"""

    def test_default_curriculum(self):
        """M1: 默认课程级别正确。"""
        assert len(DEFAULT_CURRICULUM) == 4
        assert DEFAULT_CURRICULUM[0].n_devices_min == 5
        assert DEFAULT_CURRICULUM[-1].n_devices_max == 100

    def test_init_default(self):
        """M1: 默认初始化。"""
        scheduler = CurriculumScheduler()
        assert scheduler.current_level == 0
        assert scheduler.current_epoch == 0

    def test_get_current_samples(self):
        """M2: 按当前级别筛选样本。"""
        scheduler = CurriculumScheduler()
        samples = [
            PretrainSample(
                circuit_name=f"t{i}", platform="SOI",
                n_devices=n, node_feats=np.random.randn(n, 10),
                edge_index=np.zeros((2, 0), dtype=np.int64),
                edge_feats=np.zeros((0, 9)),
                placements={},
            )
            for i, n in enumerate([5, 8, 15, 25, 60, 90])
        ]
        current = scheduler.get_current_samples(samples)
        assert len(current) == 2

    def test_step_progression(self):
        """M2: step 推进课程。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 1, 10, 2), CurriculumLevel("L2", 11, 20, 3)]
        )
        scheduler.step()
        assert scheduler.current_epoch == 1
        scheduler.step()
        assert scheduler.current_level == 1
        assert scheduler.current_epoch == 0

    def test_is_finished(self):
        """M2: 完成所有级别后 is_finished 为 True。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 1, 10, 1)]
        )
        assert not scheduler.is_finished()
        scheduler.step()
        assert scheduler.is_finished()

    def test_reset(self):
        """M2: reset 重置到初始状态。"""
        scheduler = CurriculumScheduler(
            levels=[CurriculumLevel("L1", 1, 10, 1)]
        )
        scheduler.step()
        assert scheduler.is_finished()
        scheduler.reset()
        assert scheduler.current_level == 0
        assert scheduler.current_epoch == 0

    def test_empty_levels_raises(self):
        """R03: 空级别列表抛出异常。"""
        with pytest.raises(ValueError):
            CurriculumScheduler(levels=[])


class TestFisherInformation:
    """FisherInformation Fisher 信息矩阵测试。"""

    def test_init_empty(self):
        """M1: 初始 Fisher 为空。"""
        fisher = FisherInformation()
        assert len(fisher.fisher) == 0
        assert len(fisher.params) == 0

    def test_empty_samples_raises(self):
        """R03: 空样本抛出异常。"""
        fisher = FisherInformation()
        with pytest.raises(ValueError):
            fisher.compute(None, [])


class TestEWCRegularizer:
    """EWCRegularizer EWC 正则化测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        ewc = EWCRegularizer()
        assert ewc.config.ewc_lambda == 100.0
        assert ewc.config.fisher_n_samples == 32

    def test_no_fisher_penalty_zero(self):
        """M1: 无 Fisher 时惩罚为 0。"""
        ewc = EWCRegularizer()
        from polaris.trainer.ppo import PPOAgent
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        penalty = ewc.compute_penalty(agent)
        assert penalty == 0.0


class TestPlatformTransferLearner:
    """PlatformTransferLearner 多平台迁移学习测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        learner = PlatformTransferLearner()
        assert learner.source_platform == "SOI"
        assert len(learner.target_platforms) == 3

    def test_invalid_source_raises(self):
        """R03: 无效源平台抛出异常。"""
        with pytest.raises(ValueError):
            PlatformTransferLearner(source_platform="UNKNOWN")

    def test_invalid_target_raises(self):
        """R03: 无效目标平台抛出异常。"""
        with pytest.raises(ValueError):
            PlatformTransferLearner(target_platforms=("UNKNOWN",))


class TestCheckpointManager:
    """CheckpointManager 检查点管理测试。"""

    def test_init_creates_dir(self, tmp_path):
        """M1: 初始化创建 checkpoint 目录。"""
        ckpt_dir = tmp_path / "checkpoints"
        manager = CheckpointManager(checkpoint_dir=ckpt_dir)
        assert ckpt_dir.exists()

    def test_save_requires_save_method(self):
        """R03: agent 无 save 方法抛出异常。"""
        manager = CheckpointManager()
        with pytest.raises(ValueError):
            manager.save_pretrained(object(), "test.json")

    def test_load_requires_load_method(self):
        """R03: agent 无 load 方法抛出异常。"""
        manager = CheckpointManager()
        with pytest.raises(ValueError):
            manager.load_pretrained(object(), "test.json")

    def test_load_nonexistent_raises(self, tmp_path):
        """R03: 不存在的 checkpoint 抛出异常。"""
        from polaris.trainer.ppo import PPOAgent
        manager = CheckpointManager(checkpoint_dir=tmp_path)
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        with pytest.raises(FileNotFoundError):
            manager.load_pretrained(agent, tmp_path / "nonexistent.json")

    def test_save_and_load(self, tmp_path):
        """M3: 保存和加载 checkpoint。"""
        from polaris.trainer.ppo import PPOAgent
        ckpt_path = tmp_path / "test_ckpt.json"
        manager = CheckpointManager(checkpoint_dir=tmp_path)
        agent1 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        manager.save_pretrained(agent1, ckpt_path, metadata={"test": "value"})
        assert ckpt_path.exists()
        agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        metadata = manager.load_pretrained(agent2, ckpt_path)
        assert "version" in metadata
        assert metadata["test"] == "value"

    def test_list_checkpoints(self, tmp_path):
        """M1: 列出所有 checkpoint。"""
        from polaris.trainer.ppo import PPOAgent
        manager = CheckpointManager(checkpoint_dir=tmp_path)
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        for i in range(3):
            manager.save_pretrained(agent, tmp_path / f"ckpt_{i}.json")
        ckpts = manager.list_checkpoints()
        assert len(ckpts) == 3


class TestFineTuner:
    """FineTuner 微调器测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        ft = FineTuner()
        assert ft.config.n_epochs == 50
        assert ft.config.use_ewc is True
        assert ft.config.use_cosine_schedule is True

    def test_empty_target_samples_raises(self):
        """R03: 空目标样本抛出异常。"""
        ft = FineTuner()
        from polaris.trainer.ppo import PPOAgent
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        with pytest.raises(ValueError):
            ft.finetune(agent, [])
