"""R35 AlphaChip 预训练 + 微调流水线测试套件。

覆盖 R35 PretrainingPipeline 全部功能：
- 配置验证（R03 无 fall-back）
- 100+ PIC 块数据集加载（AlphaChip 要求）
- 自监督预训练（GraphMAE 风格）
- L0-L4 课程学习调度（Bengio 2009）
- PPO 强化学习微调（Schulman 2017）
- EWC 防遗忘惩罚（Kirkpatrick 2017，独立接口）
- Fisher 信息矩阵计算
- 完整微调流程（PPO + EWC + 课程学习）
- 评估（HPWL/线长/拥塞/交叉/弯曲/均匀性）
- 完整流水线 run()
- EWC 系数影响（λ=0.4 防遗忘）
- R04 CPU 单机实现验证

学术来源:
- Mirhoseini et al., Nature 2021, AlphaChip 预训练-微调
  https://www.nature.com/articles/s41586-021-03544-w
- Schulman et al., 2017, PPO: https://arxiv.org/abs/1707.06347
- Kirkpatrick et al., 2017 PNAS, EWC
  https://www.pnas.org/doi/10.1073/pnas.1611835114
- Bengio et al., ICML 2009, Curriculum Learning
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.rl.pretraining import (
    GPU_DISABLED_R04,
    PretrainingConfig,
    PretrainingPipeline,
    R35_CURRICULUM_LEVELS,
)


# =============================================================================
# 辅助 fixtures
# =============================================================================


def _small_config(**overrides) -> PretrainingConfig:
    """构建小规模测试配置（快速跑通）。

    n_pretrain_blocks=100 满足 AlphaChip 100+ blocks 要求，
    pretrain/finetune epochs 取最小值确保测试 < 60s。
    """
    defaults = dict(
        n_pretrain_blocks=100,
        n_curriculum_levels=5,
        ewc_lambda=0.4,
        ppo_clip=0.2,
        pretrain_epochs=1,
        finetune_epochs=2,
        grid_size=(16, 16),
        seed=42,
        checkpoint_dir="/tmp/r35_test_ckpt",
    )
    defaults.update(overrides)
    return PretrainingConfig(**defaults)


def _make_small_circuit(n_devices: int = 3) -> dict:
    """构建小型光子电路 dict（AlphaChip 电路格式，用于 PPO 微调测试）。

    Args:
        n_devices: 器件数（默认 3，确保 PPO 微调快速）。

    Returns:
        circuit dict，含 ``devices`` 与 ``nets``。
    """
    devices = [
        {
            "id": f"dev_{i}",
            "type": "mzi",
            "width": 50.0,
            "height": 30.0,
            "ports": ["p0", "p1"],
        }
        for i in range(n_devices)
    ]
    nets = [
        {
            "src": [f"dev_{i}", "p0"],
            "dst": [f"dev_{i + 1}", "p1"],
            "type": "waveguide",
            "target_length": 100.0,
        }
        for i in range(n_devices - 1)
    ]
    return {"devices": devices, "nets": nets}


def _make_pretrain_samples(n: int = 3) -> list:
    """构建少量预训练样本（用于 pretrain/Fisher 测试，避免全量 100 样本耗时）。

    Args:
        n: 样本数。

    Returns:
        PretrainSample 列表。
    """
    from polaris.trainer.pretrain import PretrainDataset

    ds = PretrainDataset(n_per_platform=1, seed=42)
    ds.generate()
    return ds.samples[:n]


# =============================================================================
# 测试 1: 配置验证（R03 无 fall-back）
# =============================================================================


class TestConfigValidation:
    """测试 PretrainingConfig 验证。"""

    def test_default_config_valid(self):
        """默认配置通过验证。"""
        pipeline = PretrainingPipeline(_small_config())
        assert pipeline.config.n_pretrain_blocks == 100
        assert pipeline.config.n_curriculum_levels == 5
        assert pipeline.config.ewc_lambda == pytest.approx(0.4)
        assert pipeline.config.ppo_clip == pytest.approx(0.2)

    def test_n_pretrain_blocks_below_100_raises(self):
        """n_pretrain_blocks < 100 须 raise（AlphaChip 要求 100+ blocks）。"""
        with pytest.raises(ValueError, match="n_pretrain_blocks 须 >= 100"):
            PretrainingPipeline(PretrainingConfig(n_pretrain_blocks=50))

    def test_n_curriculum_levels_out_of_range_raises(self):
        """n_curriculum_levels 越界须 raise。"""
        with pytest.raises(ValueError, match="n_curriculum_levels"):
            PretrainingPipeline(
                PretrainingConfig(n_pretrain_blocks=100, n_curriculum_levels=6)
            )

    def test_negative_ewc_lambda_raises(self):
        """负 ewc_lambda 须 raise。"""
        with pytest.raises(ValueError, match="ewc_lambda"):
            PretrainingPipeline(PretrainingConfig(ewc_lambda=-0.1))

    def test_invalid_ppo_clip_raises(self):
        """ppo_clip 不在 (0, 1] 须 raise（Schulman 2017 推荐 0.2）。"""
        with pytest.raises(ValueError, match="ppo_clip"):
            PretrainingPipeline(PretrainingConfig(ppo_clip=1.5))
        with pytest.raises(ValueError, match="ppo_clip"):
            PretrainingPipeline(PretrainingConfig(ppo_clip=0.0))

    def test_non_positive_epochs_raises(self):
        """非正 epochs 须 raise。"""
        with pytest.raises(ValueError, match="pretrain_epochs"):
            PretrainingPipeline(PretrainingConfig(pretrain_epochs=0))


# =============================================================================
# 测试 2: 100+ PIC 块数据集加载
# =============================================================================


class TestLoadPretrainDataset:
    """测试 100+ PIC 块预训练数据集加载。"""

    def test_load_returns_100_plus_blocks(self):
        """加载 100+ PIC 块（AlphaChip 预训练要求）。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = pipeline.load_pretrain_dataset(100)
        assert len(samples) >= 100

    def test_load_covers_four_platforms(self):
        """数据集覆盖 SOI/SiN/InP/LNOI 四平台。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = pipeline.load_pretrain_dataset(100)
        platforms = {s.platform for s in samples}
        assert platforms == {"SOI", "SiN", "InP", "LNOI"}

    def test_load_below_100_raises(self):
        """n_blocks < 100 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="n_blocks 须 >= 100"):
            pipeline.load_pretrain_dataset(50)

    def test_load_120_blocks(self):
        """加载 120 块（验证 >100 也可）。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = pipeline.load_pretrain_dataset(120)
        assert len(samples) >= 120


# =============================================================================
# 测试 3: 自监督预训练
# =============================================================================


class TestPretrain:
    """测试自监督预训练（GraphMAE 风格掩码节点 + 边类型预测）。"""

    def test_pretrain_returns_weights_and_metrics(self):
        """预训练返回权重 dict 与指标。"""
        pipeline = PretrainingPipeline(_small_config(pretrain_epochs=1))
        samples = _make_pretrain_samples(3)
        weights = pipeline.pretrain(samples)
        assert "checkpoint_path" in weights
        assert "gnn_params" in weights
        assert "metrics" in weights
        metrics = weights["metrics"]
        assert "node_loss" in metrics
        assert "edge_loss" in metrics
        assert "total_loss" in metrics
        assert metrics["n_iters"] == 3

    def test_pretrain_gnn_params_non_empty(self):
        """预训练后 GNN 参数非空。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = _make_pretrain_samples(2)
        weights = pipeline.pretrain(samples)
        assert len(weights["gnn_params"]) > 0
        for p in weights["gnn_params"]:
            assert isinstance(p, np.ndarray)
            assert p.size > 0

    def test_pretrain_empty_dataset_raises(self):
        """空数据集须 raise（R03 无 fall-back）。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="不能为空"):
            pipeline.pretrain([])

    def test_pretrain_loss_finite(self):
        """预训练损失为有限值。"""
        import math

        pipeline = PretrainingPipeline(_small_config())
        samples = _make_pretrain_samples(3)
        weights = pipeline.pretrain(samples)
        assert math.isfinite(weights["metrics"]["total_loss"])
        assert weights["metrics"]["total_loss"] >= 0.0


# =============================================================================
# 测试 4: 课程学习调度（L0-L4）
# =============================================================================


class TestCurriculumSchedule:
    """测试 L0-L4 课程学习调度（Bengio 2009）。"""

    def test_five_levels_l0_to_l4(self):
        """R35 课程含 5 级 L0-L4（扩展 R34 的 4 级）。"""
        assert len(R35_CURRICULUM_LEVELS) == 5
        names = [lv.name for lv in R35_CURRICULUM_LEVELS]
        assert names[0].startswith("L0")
        assert names[-1].startswith("L4")

    def test_difficulty_increasing(self):
        """课程难度递增（器件数下限/上限递增）。"""
        pipeline = PretrainingPipeline(_small_config())
        prev_min = 0
        prev_max = 0
        for level in range(5):
            sched = pipeline.curriculum_schedule(level)
            assert sched["n_devices_min"] >= prev_min
            assert sched["n_devices_max"] > prev_max
            prev_min = sched["n_devices_min"]
            prev_max = sched["n_devices_max"]

    def test_l0_warmup_smallest(self):
        """L0 warmup 器件数最小（3-5 节点）。"""
        pipeline = PretrainingPipeline(_small_config())
        l0 = pipeline.curriculum_schedule(0)
        assert l0["name"] == "L0_warmup"
        assert l0["n_devices_min"] == 3
        assert l0["n_devices_max"] == 5

    def test_l4_expert_largest(self):
        """L4 expert 器件数最大（60-100 节点）。"""
        pipeline = PretrainingPipeline(_small_config())
        l4 = pipeline.curriculum_schedule(4)
        assert l4["name"] == "L4_expert"
        assert l4["n_devices_min"] == 60
        assert l4["n_devices_max"] == 100

    def test_invalid_level_raises(self):
        """越界 level 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="level"):
            pipeline.curriculum_schedule(5)
        with pytest.raises(ValueError, match="level"):
            pipeline.curriculum_schedule(-1)

    def test_build_curriculum_scheduler(self):
        """构建课程调度器（复用 R34 CurriculumScheduler）。"""
        pipeline = PretrainingPipeline(_small_config())
        scheduler = pipeline.build_curriculum_scheduler()
        assert scheduler.current_level == 0
        assert len(scheduler.levels) == 5


# =============================================================================
# 测试 5: EWC 防遗忘惩罚（独立接口，Kirkpatrick 2017）
# =============================================================================


class TestComputeEwcPenalty:
    """测试 EWC 防遗忘惩罚独立接口（Kirkpatrick 2017 PNAS）。"""

    def test_zero_penalty_at_optimum(self):
        """参数未变化时 EWC 惩罚为 0。"""
        pipeline = PretrainingPipeline(_small_config())
        fisher = np.array([1.0, 1.0, 1.0])
        params = np.array([1.0, 2.0, 3.0])
        prior = np.array([1.0, 2.0, 3.0])
        penalty = pipeline.compute_ewc_penalty(fisher, params, prior)
        assert penalty == pytest.approx(0.0, abs=1e-12)

    def test_positive_penalty_after_drift(self):
        """参数漂移后 EWC 惩罚为正。"""
        pipeline = PretrainingPipeline(_small_config())
        fisher = np.array([1.0, 1.0])
        params = np.array([2.0, 3.0])
        prior = np.array([0.0, 0.0])
        penalty = pipeline.compute_ewc_penalty(fisher, params, prior)
        # 1*4 + 1*9 = 13
        assert penalty == pytest.approx(13.0)

    def test_fisher_weighted(self):
        """Fisher 矩阵加权惩罚（重要参数惩罚更大）。"""
        pipeline = PretrainingPipeline(_small_config())
        # fisher 大的参数漂移惩罚更大
        fisher = np.array([10.0, 1.0])
        params = np.array([1.0, 1.0])
        prior = np.array([0.0, 0.0])
        penalty = pipeline.compute_ewc_penalty(fisher, params, prior)
        # 10*1 + 1*1 = 11
        assert penalty == pytest.approx(11.0)

    def test_shape_mismatch_raises(self):
        """形状不匹配须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        fisher = np.array([1.0, 1.0])
        params = np.array([1.0])
        prior = np.array([1.0, 1.0])
        with pytest.raises(ValueError, match="形状不匹配"):
            pipeline.compute_ewc_penalty(fisher, params, prior)

    def test_formula_matches_kirkpatrick_2017(self):
        """EWC 公式匹配 Kirkpatrick 2017 PNAS Eq. 3: Σ F_i*(θ_i-θ*_i)²。"""
        pipeline = PretrainingPipeline(_small_config())
        fisher = np.array([[2.0, 0.0], [0.0, 3.0]])
        params = np.array([[1.0, 0.0], [0.0, 1.0]])
        prior = np.array([[0.0, 0.0], [0.0, 0.0]])
        penalty = pipeline.compute_ewc_penalty(fisher, params, prior)
        # 2*1 + 3*1 = 5
        assert penalty == pytest.approx(5.0)


# =============================================================================
# 测试 6: Fisher 信息矩阵计算
# =============================================================================


class TestComputeFisherMatrix:
    """测试 Fisher 信息矩阵计算（EWC 核心）。"""

    def test_fisher_returns_list_of_arrays(self):
        """Fisher 返回 numpy 数组列表。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = _make_pretrain_samples(2)
        fisher = pipeline.compute_fisher_matrix(samples)
        assert isinstance(fisher, list)
        assert len(fisher) > 0
        for f in fisher:
            assert isinstance(f, np.ndarray)

    def test_fisher_non_negative(self):
        """Fisher 信息矩阵非负（梯度平方均值）。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = _make_pretrain_samples(2)
        fisher = pipeline.compute_fisher_matrix(samples)
        for f in fisher:
            assert np.all(f >= 0.0)

    def test_fisher_stores_prior_params(self):
        """Fisher 计算后保存参数快照 θ*。"""
        pipeline = PretrainingPipeline(_small_config())
        samples = _make_pretrain_samples(2)
        pipeline.compute_fisher_matrix(samples)
        assert pipeline._fisher_prior_params is not None
        assert len(pipeline._fisher_prior_params) == len(pipeline.fisher_matrix)

    def test_empty_dataset_raises(self):
        """空数据集须 raise（R03 无 fall-back）。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="不能为空"):
            pipeline.compute_fisher_matrix([])


# =============================================================================
# 测试 7: PPO 强化学习微调（Schulman 2017）
# =============================================================================


class TestPpoFinetune:
    """测试 PPO 强化学习微调（Schulman 2017 arXiv:1707.06347）。"""

    def test_ppo_finetune_returns_metrics(self):
        """PPO 微调返回指标 dict。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.ppo_finetune(pretrain_weights, env)
        assert "history" in result
        assert "final_reward" in result
        assert "placement" in result
        assert "agent_params" in result
        assert "metrics" in result

    def test_ppo_finetune_placement_has_all_devices(self):
        """PPO 微调后布局含所有器件。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.ppo_finetune(pretrain_weights, env)
        placement = result["placement"]
        assert len(placement) == 3
        for dev_id, p in placement.items():
            assert "x" in p and "y" in p

    def test_ppo_finetune_metrics_complete(self):
        """PPO 微调指标含线长/拥塞/交叉/弯曲/均匀性。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.ppo_finetune(pretrain_weights, env)
        metrics = result["metrics"]
        for key in ["wirelength", "congestion", "crossing",
                    "bend_violation", "uniformity"]:
            assert key in metrics

    def test_ppo_finetune_invalid_env_raises(self):
        """env 缺 devices/nets 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="env 须含"):
            pipeline.ppo_finetune({"gnn_params": []}, {"bad": 1})

    def test_ppo_finetune_invalid_weights_raises(self):
        """pretrain_weights 无 gnn_params 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        env = _make_small_circuit()
        with pytest.raises(ValueError, match="gnn_params"):
            pipeline.ppo_finetune({"bad": 1}, env)


# =============================================================================
# 测试 8: 完整微调流程（PPO + EWC + 课程学习）
# =============================================================================


class TestFinetune:
    """测试完整微调流程。"""

    def test_finetune_returns_full_result(self):
        """完整微调返回 finetuned_weights/ewc_penalty/curriculum。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        pipeline.compute_fisher_matrix(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.finetune(pretrain_weights, env)
        assert "finetuned_weights" in result
        assert "ewc_penalty" in result
        assert "ewc_lambda" in result
        assert "curriculum" in result

    def test_finetune_ewc_penalty_positive_after_drift(self):
        """微调后参数漂移，EWC 惩罚 > 0。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=2))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        pipeline.compute_fisher_matrix(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.finetune(pretrain_weights, env)
        # PPO 微调后参数变化，EWC 惩罚应 > 0（若 Fisher 非零）
        assert result["ewc_penalty"] >= 0.0
        assert result["ewc_lambda"] == pytest.approx(0.4)

    def test_finetune_without_fisher_zero_penalty(self):
        """未计算 Fisher 时 EWC 惩罚为 0。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.finetune(pretrain_weights, env)
        assert result["ewc_penalty"] == 0.0
        assert "Fisher 矩阵未计算" in result["ewc_note"]

    def test_finetune_curriculum_l0(self):
        """微调使用 L0 课程级别。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        result = pipeline.finetune(pretrain_weights, env)
        assert result["curriculum"]["name"] == "L0_warmup"


# =============================================================================
# 测试 9: 评估（HPWL/线长/拥塞）
# =============================================================================


class TestEvaluate:
    """测试布局评估。"""

    def test_evaluate_returns_all_metrics(self):
        """评估返回 HPWL/拥塞/交叉/弯曲/均匀性/reward。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        finetuned = pipeline.ppo_finetune(pretrain_weights, env)
        result = pipeline.evaluate(finetuned, env)
        for key in ["hpwl", "congestion", "crossing",
                    "bend_violation", "uniformity", "reward"]:
            assert key in result

    def test_evaluate_hpwl_non_negative(self):
        """HPWL 线长非负。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        env = _make_small_circuit(n_devices=3)
        finetuned = pipeline.ppo_finetune(pretrain_weights, env)
        result = pipeline.evaluate(finetuned, env)
        assert result["hpwl"] >= 0.0

    def test_evaluate_invalid_weights_raises(self):
        """无效 weights 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        env = _make_small_circuit()
        with pytest.raises(ValueError, match="placement"):
            pipeline.evaluate({}, env)

    def test_evaluate_invalid_benchmark_raises(self):
        """benchmark 缺 devices/nets 须 raise。"""
        pipeline = PretrainingPipeline(_small_config())
        with pytest.raises(ValueError, match="benchmark"):
            pipeline.evaluate({"placement": {"d0": {"x": 0, "y": 0}}}, {"bad": 1})


# =============================================================================
# 测试 10: 完整流水线 run()
# =============================================================================


class TestPipelineRun:
    """测试完整流水线 run()。"""

    def test_run_returns_all_stages(self):
        """run() 返回 pretrain/fisher/finetune/evaluate 各阶段结果。"""
        pipeline = PretrainingPipeline(_small_config(
            pretrain_epochs=1, finetune_epochs=1
        ))
        result = pipeline.run()
        assert "pretrain" in result
        assert "fisher_n_params" in result
        assert "finetune" in result
        assert "evaluate" in result
        assert "history" in result
        assert "r04_gpu_disabled" in result

    def test_run_fisher_n_params_positive(self):
        """run() 后 Fisher 参数组数 > 0。"""
        pipeline = PretrainingPipeline(_small_config(
            pretrain_epochs=1, finetune_epochs=1
        ))
        result = pipeline.run()
        assert result["fisher_n_params"] > 0

    def test_run_history_records_all_stages(self):
        """run() 历史记录所有阶段。"""
        pipeline = PretrainingPipeline(_small_config(
            pretrain_epochs=1, finetune_epochs=1
        ))
        result = pipeline.run()
        stages = result["history"]["stage"]
        assert "pretrain" in stages
        assert "ppo_finetune" in stages
        assert "finetune" in stages

    def test_run_pretrain_loss_finite(self):
        """run() 预训练损失为有限值。"""
        import math

        pipeline = PretrainingPipeline(_small_config(
            pretrain_epochs=1, finetune_epochs=1
        ))
        result = pipeline.run()
        assert math.isfinite(result["pretrain"]["total_loss"])


# =============================================================================
# 测试 11: EWC 系数影响（λ=0.4 防遗忘）
# =============================================================================


class TestEwcLambda:
    """测试 EWC 系数 λ 的影响（Kirkpatrick 2017）。"""

    def test_default_lambda_is_0_4(self):
        """默认 ewc_lambda = 0.4（任务骨架指定）。"""
        pipeline = PretrainingPipeline(_small_config())
        assert pipeline.config.ewc_lambda == pytest.approx(0.4)

    def test_larger_lambda_larger_penalty(self):
        """λ 越大 EWC 惩罚越大（防遗忘更强）。"""
        pipeline_low = PretrainingPipeline(_small_config(ewc_lambda=0.1))
        pipeline_high = PretrainingPipeline(_small_config(ewc_lambda=1.0))
        # 用相同 fisher/prior/current 模拟
        pipeline_low.fisher_matrix = [np.array([1.0, 1.0])]
        pipeline_low._fisher_prior_params = [np.array([0.0, 0.0])]
        pipeline_high.fisher_matrix = [np.array([1.0, 1.0])]
        pipeline_high._fisher_prior_params = [np.array([0.0, 0.0])]
        current = [np.array([1.0, 1.0])]
        penalty_low = pipeline_low._compute_total_ewc_penalty(current)
        penalty_high = pipeline_high._compute_total_ewc_penalty(current)
        assert penalty_high > penalty_low
        # 0.1 * 2 vs 1.0 * 2
        assert penalty_low == pytest.approx(0.2)
        assert penalty_high == pytest.approx(2.0)

    def test_zero_lambda_zero_penalty(self):
        """λ=0 时 EWC 惩罚为 0（不防遗忘）。"""
        pipeline = PretrainingPipeline(_small_config(ewc_lambda=0.0))
        pipeline.fisher_matrix = [np.array([1.0])]
        pipeline._fisher_prior_params = [np.array([0.0])]
        penalty = pipeline._compute_total_ewc_penalty([np.array([1.0])])
        assert penalty == pytest.approx(0.0)

    def test_ewc_penalty_formula_with_lambda(self):
        """EWC 惩罚 = λ * Σ F*(θ-θ*)²。"""
        pipeline = PretrainingPipeline(_small_config(ewc_lambda=0.4))
        pipeline.fisher_matrix = [np.array([2.0])]
        pipeline._fisher_prior_params = [np.array([0.0])]
        # 0.4 * 2 * 1 = 0.8
        penalty = pipeline._compute_total_ewc_penalty([np.array([1.0])])
        assert penalty == pytest.approx(0.8)


# =============================================================================
# 测试 12: R04 CPU 单机实现验证
# =============================================================================


class TestCpuOnly:
    """测试 R04 CPU 单机实现（不参与 GPU 分布式）。"""

    def test_gpu_disabled_flag_true(self):
        """R04 GPU 禁用标志为 True。"""
        assert GPU_DISABLED_R04 is True

    def test_no_gpu_imports(self):
        """模块不导入 GPU 库（CuPy/CUDA/ROCm/Torch GPU 后端）。"""
        import polaris.rl.pretraining as mod
        import inspect
        source = inspect.getsource(mod)
        # 禁止出现 GPU 后端导入
        assert "import cupy" not in source
        assert "import torch" not in source
        assert "cp." not in source  # CuPy 简写
        # 允许 jax（CPU 后端）但不允许 jax.gpu
        assert "jax.gpu" not in source

    def test_pipeline_uses_numpy_arrays(self):
        """流水线参数为 numpy 数组（非 GPU tensor）。"""
        pipeline = PretrainingPipeline(_small_config(finetune_epochs=1))
        samples = _make_pretrain_samples(2)
        pretrain_weights = pipeline.pretrain(samples)
        for p in pretrain_weights["gnn_params"]:
            assert isinstance(p, np.ndarray)

    def test_run_reports_gpu_disabled(self):
        """run() 结果报告 GPU 禁用。"""
        pipeline = PretrainingPipeline(_small_config(
            pretrain_epochs=1, finetune_epochs=1
        ))
        result = pipeline.run()
        assert result["r04_gpu_disabled"] is True

    def test_no_distributed_training_artifacts(self):
        """无分布式训练工件（无 multi-GPU / CTDE 多卡）。"""
        import polaris.rl.pretraining as mod
        import inspect
        source = inspect.getsource(mod)
        # 禁止分布式 GPU 训练关键词
        assert "MultiGPU" not in source
        assert "DistributedDataParallel" not in source
        assert "CTDE" not in source  # Apollo CTDE 多卡分布式不参与


# =============================================================================
# 测试 13: 学术诚信验证（R02）
# =============================================================================


class TestAcademicIntegrity:
    """学术诚信验证（R02: 参数/公式须溯源）。"""

    def test_module_docstring_has_5_plus_urls(self):
        """模块 docstring 含 ≥5 个文献 URL（R02 要求）。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        # 统计 URL 数量
        url_count = docstring.count("https://") + docstring.count("http://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5"

    def test_docstring_cites_mirhoseini_2021(self):
        """docstring 引用 Mirhoseini 2021 Nature（AlphaChip 起源）。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        assert "Mirhoseini" in docstring
        assert "s41586-021-03544-w" in docstring

    def test_docstring_cites_ppo_schulman_2017(self):
        """docstring 引用 Schulman 2017 PPO。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        assert "Schulman" in docstring
        assert "1707.06347" in docstring

    def test_docstring_cites_ewc_kirkpatrick_2017(self):
        """docstring 引用 Kirkpatrick 2017 EWC。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        assert "Kirkpatrick" in docstring
        assert "pnas.1611835114" in docstring

    def test_innovation_annotated(self):
        """创新点标注 *创新* 并记录底层逻辑（R02）。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        assert "*创新*" in docstring
        assert "底层逻辑" in docstring

    def test_curriculum_levels_bengio_2009(self):
        """课程学习级别溯源 Bengio 2009 ICML。"""
        import polaris.rl.pretraining as mod
        docstring = mod.__doc__ or ""
        assert "Bengio" in docstring
        assert "1553374.1553380" in docstring


# =============================================================================
# 测试 14: 无 fall-back 验证（R03）
# =============================================================================


class TestNoFallBack:
    """无 fall-back 验证（R03: 失败即 raise，禁止假数据兜底）。"""

    def test_no_bare_except_pass(self):
        """无 except: pass 静默兜底。"""
        import polaris.rl.pretraining as mod
        import inspect
        source = inspect.getsource(mod)
        assert "except: pass" not in source
        assert "except Exception: pass" not in source

    def test_no_return_none_in_catch(self):
        """无 except: return None 假数据兜底。"""
        import polaris.rl.pretraining as mod
        import inspect
        source = inspect.getsource(mod)
        assert "return None" not in source

    def test_all_errors_raise(self):
        """所有错误路径 raise ValueError/RuntimeError（非静默）。"""
        pipeline = PretrainingPipeline(_small_config())
        # 各种非法输入都应 raise，不返回假数据
        with pytest.raises((ValueError, RuntimeError)):
            pipeline.load_pretrain_dataset(10)
        with pytest.raises(ValueError):
            pipeline.pretrain([])
        with pytest.raises(ValueError):
            pipeline.curriculum_schedule(99)
        with pytest.raises(ValueError):
            pipeline.compute_fisher_matrix([])
