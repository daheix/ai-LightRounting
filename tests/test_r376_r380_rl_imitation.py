"""R376-R380 模仿学习测试。

覆盖:
- R376 BehavioralCloning (Pomerleau 1989)
- R377 GAILDiscriminator (Ho 2016)
- R378 DAgger (Ross 2011)
- R379 ExpertDataset
- R380 ImitationPipeline
- R03/R02/R04 合规
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.rl.rl_imitation import (
    BCConfig,
    BehavioralCloning,
    DAgger,
    ExpertDataset,
    GAILConfig,
    GAILDiscriminator,
    GPU_DISABLED_R04,
    ImitationPipeline,
)


# =============================================================================
# fixtures
# =============================================================================

@pytest.fixture
def bc_config() -> BCConfig:
    return BCConfig(state_dim=8, n_actions=16, n_epochs=5, batch_size=4, seed=42)


@pytest.fixture
def bc(bc_config: BCConfig) -> BehavioralCloning:
    return BehavioralCloning(bc_config)


@pytest.fixture
def expert_data() -> ExpertDataset:
    """10 条专家数据。"""
    ds = ExpertDataset()
    rng = np.random.default_rng(0)
    for _ in range(10):
        s = rng.normal(size=8)
        a = int(rng.integers(0, 16))
        ds.add(s, a)
    return ds


@pytest.fixture
def discriminator() -> GAILDiscriminator:
    return GAILDiscriminator(state_dim=8, n_actions=16, seed=42)


@pytest.fixture
def dagger(bc: BehavioralCloning) -> DAgger:
    return DAgger(bc)


@pytest.fixture
def pipeline() -> ImitationPipeline:
    return ImitationPipeline(
        BCConfig(state_dim=8, n_actions=16, n_epochs=3, batch_size=4, seed=42),
        GAILConfig(state_dim=8, n_actions=16, seed=42),
    )


# =============================================================================
# R379 ExpertDataset 测试
# =============================================================================

class TestR379Dataset:
    """R379 专家数据集测试。"""

    def test_add(self) -> None:
        ds = ExpertDataset()
        ds.add(np.zeros(8), 0)
        assert len(ds) == 1

    def test_extend(self) -> None:
        ds = ExpertDataset()
        states = [np.zeros(8), np.ones(8)]
        actions = [0, 1]
        ds.extend(states, actions)
        assert len(ds) == 2

    def test_extend_mismatch(self) -> None:
        ds = ExpertDataset()
        with pytest.raises(ValueError, match="≠"):
            ds.extend([np.zeros(8)], [0, 1])

    def test_get_states_empty(self) -> None:
        ds = ExpertDataset()
        with pytest.raises(ValueError, match="为空"):
            ds.get_states()

    def test_get_actions_empty(self) -> None:
        ds = ExpertDataset()
        with pytest.raises(ValueError, match="为空"):
            ds.get_actions()

    def test_get_states(self, expert_data: ExpertDataset) -> None:
        s = expert_data.get_states()
        assert s.shape == (10, 8)

    def test_get_actions(self, expert_data: ExpertDataset) -> None:
        a = expert_data.get_actions()
        assert a.shape == (10,)

    def test_sample_batch(self, expert_data: ExpertDataset) -> None:
        rng = np.random.default_rng(0)
        s, a = expert_data.sample_batch(5, rng)
        assert s.shape == (5, 8)
        assert a.shape == (5,)

    def test_sample_batch_too_large(self, expert_data: ExpertDataset) -> None:
        rng = np.random.default_rng(0)
        with pytest.raises(ValueError, match="batch_size"):
            expert_data.sample_batch(999, rng)

    def test_sample_batch_zero(self, expert_data: ExpertDataset) -> None:
        rng = np.random.default_rng(0)
        with pytest.raises(ValueError, match="batch_size"):
            expert_data.sample_batch(0, rng)

    def test_iterate_batches(self, expert_data: ExpertDataset) -> None:
        rng = np.random.default_rng(0)
        total = 0
        for s, a in expert_data.iterate_batches(3, rng):
            total += len(s)
        assert total == 10

    def test_iterate_empty(self) -> None:
        ds = ExpertDataset()
        rng = np.random.default_rng(0)
        with pytest.raises(ValueError, match="为空"):
            list(ds.iterate_batches(3, rng))


# =============================================================================
# R376 BehavioralCloning 测试
# =============================================================================

class TestR376BC:
    """R376 行为克隆测试（Pomerleau 1989）。"""

    def test_predict_shape(self, bc: BehavioralCloning) -> None:
        probs = bc.predict(np.zeros(8))
        assert probs.shape == (16,)
        assert probs.sum() == pytest.approx(1.0)

    def test_predict_state_dim_mismatch(self, bc: BehavioralCloning) -> None:
        with pytest.raises(ValueError, match="state 维度"):
            bc.predict(np.zeros(999))

    def test_predict_action(self, bc: BehavioralCloning) -> None:
        action = bc.predict_action(np.zeros(8))
        assert 0 <= action < 16

    def test_compute_loss(self, bc: BehavioralCloning) -> None:
        states = np.zeros((4, 8))
        actions = np.zeros(4, dtype=np.int64)
        loss = bc.compute_loss(states, actions)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_compute_loss_state_dim_mismatch(self, bc: BehavioralCloning) -> None:
        with pytest.raises(ValueError, match="state_dim"):
            bc.compute_loss(np.zeros((4, 999)), np.zeros(4))

    def test_compute_loss_states_actions_mismatch(self, bc: BehavioralCloning) -> None:
        with pytest.raises(ValueError, match="≠"):
            bc.compute_loss(np.zeros((4, 8)), np.zeros(3))

    def test_compute_loss_1d_states(self, bc: BehavioralCloning) -> None:
        with pytest.raises(ValueError, match="2D"):
            bc.compute_loss(np.zeros(8), np.zeros(1))

    def test_update_step(self, bc: BehavioralCloning) -> None:
        states = np.random.default_rng(0).normal(size=(4, 8))
        actions = np.array([0, 1, 2, 3])
        loss = bc.update_step(states, actions)
        assert isinstance(loss, float)

    def test_train(self, bc: BehavioralCloning, expert_data: ExpertDataset) -> None:
        losses = bc.train(expert_data)
        assert len(losses) == 5  # n_epochs=5

    def test_train_empty(self, bc: BehavioralCloning) -> None:
        with pytest.raises(ValueError, match="为空"):
            bc.train(ExpertDataset())

    def test_loss_decreases(self, bc: BehavioralCloning) -> None:
        """训练后 loss 应下降。"""
        rng = np.random.default_rng(0)
        ds = ExpertDataset()
        # 构造线性可分数据
        for i in range(50):
            s = np.zeros(8)
            s[0] = float(i % 4)
            ds.add(s, i % 4)
        losses = bc.train(ds)
        assert losses[-1] < losses[0]


# =============================================================================
# R377 GAILDiscriminator 测试
# =============================================================================

class TestR377GAIL:
    """R377 GAIL 判别器测试（Ho 2016）。"""

    def test_discriminate_in_range(self, discriminator: GAILDiscriminator) -> None:
        d = discriminator.discriminate(np.zeros(8), 0)
        assert 0.0 < d < 1.0

    def test_discriminate_state_mismatch(self, discriminator: GAILDiscriminator) -> None:
        with pytest.raises(ValueError, match="state 维度"):
            discriminator.discriminate(np.zeros(999), 0)

    def test_discriminate_action_out_of_range(self, discriminator: GAILDiscriminator) -> None:
        with pytest.raises(ValueError, match="action"):
            discriminator.discriminate(np.zeros(8), 999)

    def test_update_step(self, discriminator: GAILDiscriminator) -> None:
        exp_s = np.zeros((4, 8))
        exp_a = np.zeros(4, dtype=np.int64)
        pol_s = np.ones((4, 8))
        pol_a = np.ones(4, dtype=np.int64)
        loss = discriminator.update_step(exp_s, exp_a, pol_s, pol_a)
        assert loss >= 0.0

    def test_update_step_empty_expert(self, discriminator: GAILDiscriminator) -> None:
        with pytest.raises(ValueError, match="为空"):
            discriminator.update_step(
                np.zeros((0, 8)), np.zeros(0, dtype=np.int64),
                np.zeros((4, 8)), np.zeros(4, dtype=np.int64),
            )

    def test_invalid_state_dim(self) -> None:
        with pytest.raises(ValueError):
            GAILDiscriminator(0, 16)

    def test_invalid_n_actions(self) -> None:
        with pytest.raises(ValueError):
            GAILDiscriminator(8, 0)


# =============================================================================
# R378 DAgger 测试
# =============================================================================

class TestR378DAgger:
    """R378 DAgger 测试（Ross 2011）。"""

    def test_add_rollout(self, dagger: DAgger) -> None:
        states = [np.zeros(8), np.ones(8)]
        actions = [0, 1]
        dagger.add_rollout(states, actions)
        assert len(dagger.dataset) == 2

    def test_add_rollout_mismatch(self, dagger: DAgger) -> None:
        with pytest.raises(ValueError, match="≠"):
            dagger.add_rollout([np.zeros(8)], [0, 1])

    def test_train_iteration_empty(self, dagger: DAgger) -> None:
        with pytest.raises(ValueError, match="为空"):
            dagger.train_iteration()

    def test_train_iteration(self, dagger: DAgger) -> None:
        states = [np.zeros(8) for _ in range(10)]
        actions = [0] * 10
        dagger.add_rollout(states, actions)
        loss = dagger.train_iteration()
        assert isinstance(loss, float)


# =============================================================================
# R380 ImitationPipeline 测试
# =============================================================================

class TestR380Pipeline:
    """R380 模仿学习流水线测试。"""

    def test_pretrain_bc(self, pipeline: ImitationPipeline, expert_data: ExpertDataset) -> None:
        losses = pipeline.pretrain_bc(expert_data)
        assert len(losses) == 3  # n_epochs=3

    def test_pretrain_bc_empty(self, pipeline: ImitationPipeline) -> None:
        with pytest.raises(ValueError, match="为空"):
            pipeline.pretrain_bc(ExpertDataset())

    def test_gail_finetune(self, pipeline: ImitationPipeline, expert_data: ExpertDataset) -> None:
        pipeline.pretrain_bc(expert_data)
        rollouts = [(np.zeros(8), 0), (np.ones(8), 1)]
        losses = pipeline.gail_finetune(expert_data, rollouts, n_iters=3)
        assert len(losses) == 3

    def test_gail_finetune_empty_expert(self, pipeline: ImitationPipeline) -> None:
        with pytest.raises(ValueError, match="专家数据集"):
            pipeline.gail_finetune(ExpertDataset(), [(np.zeros(8), 0)])

    def test_gail_finetune_empty_rollouts(self, pipeline: ImitationPipeline, expert_data: ExpertDataset) -> None:
        with pytest.raises(ValueError, match="policy_rollouts"):
            pipeline.gail_finetune(expert_data, [])

    def test_dagger_iterate(self, pipeline: ImitationPipeline, expert_data: ExpertDataset) -> None:
        pipeline.pretrain_bc(expert_data)
        states = [np.zeros(8) for _ in range(5)]
        actions = [0] * 5
        loss = pipeline.dagger_iterate(states, actions)
        assert isinstance(loss, float)


# =============================================================================
# R03/R02/R04 合规
# =============================================================================

class TestCompliance:
    """合规测试。"""

    def test_r03_no_silent_fallback(self) -> None:
        from polaris.rl import rl_imitation as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_r02_5plus_urls(self) -> None:
        from polaris.rl import rl_imitation as mod
        assert mod.__doc__ is not None
        urls = [l for l in mod.__doc__.splitlines() if "http" in l or "papers.nips" in l]
        assert len(urls) >= 5

    def test_r02_pomerleau_cited(self) -> None:
        from polaris.rl import rl_imitation as mod
        assert "Pomerleau" in mod.__doc__
        assert "Ho" in mod.__doc__
        assert "Ross" in mod.__doc__

    def test_r02_innovation_marked(self) -> None:
        from polaris.rl import rl_imitation as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src

    def test_r04_gpu_disabled(self) -> None:
        assert GPU_DISABLED_R04 is True

    def test_r04_no_gpu_imports(self) -> None:
        from polaris.rl import rl_imitation as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "import jax" not in src
