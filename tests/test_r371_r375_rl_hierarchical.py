"""R371-R375 分层强化学习 HRL 测试。

覆盖:
- R371 GoalConditionedPolicy (Vezhnevets 2017 FeUdal)
- R372 Option (Sutton 1999)
- R373 OptionCritic (Bacon 2017)
- R374 HierarchicalAgent
- R375 HierarchicalTrainer
- R03/R02/R04 合规
- 集成测试
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.rl.rl_hierarchical import (
    GoalConditionedPolicy,
    GPU_DISABLED_R04,
    HierarchicalAgent,
    HierarchicalConfig,
    HierarchicalTrainer,
    Option,
    OptionCritic,
)


# =============================================================================
# fixtures
# =============================================================================

@pytest.fixture
def config() -> HierarchicalConfig:
    return HierarchicalConfig(
        n_options=3, n_actions=16, goal_dim=4,
        option_max_steps=5, seed=42,
    )


@pytest.fixture
def state_dim() -> int:
    return 8


@pytest.fixture
def policy(state_dim: int, config: HierarchicalConfig) -> GoalConditionedPolicy:
    return GoalConditionedPolicy(state_dim, config)


@pytest.fixture
def option_critic(state_dim: int, config: HierarchicalConfig) -> OptionCritic:
    return OptionCritic(3, state_dim, config)


@pytest.fixture
def agent(state_dim: int, config: HierarchicalConfig) -> HierarchicalAgent:
    return HierarchicalAgent(state_dim, config)


@pytest.fixture
def trainer(agent: HierarchicalAgent) -> HierarchicalTrainer:
    return HierarchicalTrainer(agent)


# =============================================================================
# R371 GoalConditionedPolicy 测试
# =============================================================================

class TestR371Policy:
    """R371 目标条件策略测试（Vezhnevets 2017）。"""

    def test_act_shape(self, policy: GoalConditionedPolicy, state_dim: int, config: HierarchicalConfig) -> None:
        s = np.zeros(state_dim)
        g = np.zeros(config.goal_dim)
        action, probs = policy.act(s, g)
        assert 0 <= action < config.n_actions
        assert probs.shape == (config.n_actions,)
        assert probs.sum() == pytest.approx(1.0)

    def test_act_state_dim_mismatch(self, policy: GoalConditionedPolicy, config: HierarchicalConfig) -> None:
        with pytest.raises(ValueError, match="state 维度"):
            policy.act(np.zeros(999), np.zeros(config.goal_dim))

    def test_act_goal_dim_mismatch(self, policy: GoalConditionedPolicy, state_dim: int) -> None:
        with pytest.raises(ValueError, match="goal 维度"):
            policy.act(np.zeros(state_dim), np.zeros(999))

    def test_act_with_mask(self, policy: GoalConditionedPolicy, state_dim: int, config: HierarchicalConfig) -> None:
        s = np.zeros(state_dim)
        g = np.zeros(config.goal_dim)
        mask = np.zeros(config.n_actions, dtype=bool)
        mask[0] = True
        action, probs = policy.act(s, g, action_mask=mask)
        assert action == 0  # 只允许 0
        assert probs[0] == pytest.approx(1.0)

    def test_act_mask_shape_mismatch(self, policy: GoalConditionedPolicy, state_dim: int, config: HierarchicalConfig) -> None:
        with pytest.raises(ValueError, match="mask"):
            policy.act(np.zeros(state_dim), np.zeros(config.goal_dim), np.zeros(999))

    def test_invalid_state_dim(self) -> None:
        with pytest.raises(ValueError):
            GoalConditionedPolicy(0)


# =============================================================================
# R372 Option 测试
# =============================================================================

class TestR372Option:
    """R372 Option 测试（Sutton 1999）。"""

    def test_can_initiate(self, state_dim: int, config: HierarchicalConfig) -> None:
        policy = GoalConditionedPolicy(state_dim, config)
        opt = Option(
            option_id=0,
            goal=np.zeros(config.goal_dim),
            initiation_mask=np.array([True, False, True]),
            policy=policy,
            termination_W=np.zeros(state_dim + 1),
        )
        assert opt.can_initiate(0) is True
        assert opt.can_initiate(1) is False

    def test_can_initiate_out_of_bounds(self, state_dim: int, config: HierarchicalConfig) -> None:
        policy = GoalConditionedPolicy(state_dim, config)
        opt = Option(
            option_id=0,
            goal=np.zeros(config.goal_dim),
            initiation_mask=np.array([True]),
            policy=policy,
            termination_W=np.zeros(state_dim + 1),
        )
        with pytest.raises(ValueError, match="越界"):
            opt.can_initiate(999)

    def test_termination_prob_in_range(self, state_dim: int, config: HierarchicalConfig) -> None:
        policy = GoalConditionedPolicy(state_dim, config)
        opt = Option(
            option_id=0,
            goal=np.zeros(config.goal_dim),
            initiation_mask=np.array([True]),
            policy=policy,
            termination_W=np.random.default_rng(0).normal(size=state_dim + 1),
        )
        s = np.random.default_rng(0).normal(size=state_dim)
        beta = opt.termination_prob(s)
        assert 0.0 <= beta <= 1.0

    def test_termination_prob_zero_weights(self, state_dim: int, config: HierarchicalConfig) -> None:
        """W=0 时 β=0.5（sigmoid(0)）。"""
        policy = GoalConditionedPolicy(state_dim, config)
        opt = Option(
            option_id=0,
            goal=np.zeros(config.goal_dim),
            initiation_mask=np.array([True]),
            policy=policy,
            termination_W=np.zeros(state_dim + 1),
        )
        beta = opt.termination_prob(np.zeros(state_dim))
        assert beta == pytest.approx(0.5)


# =============================================================================
# R373 OptionCritic 测试
# =============================================================================

class TestR373OptionCritic:
    """R373 Option-Critic 架构测试（Bacon 2017）。"""

    def test_init(self, option_critic: OptionCritic) -> None:
        assert option_critic.n_options == 3
        assert len(option_critic.options) == 3

    def test_select_option_in_range(self, option_critic: OptionCritic, state_dim: int) -> None:
        s = np.zeros(state_dim)
        opt = option_critic.select_option(s)
        assert 0 <= opt < 3

    def test_select_option_state_dim_mismatch(self, option_critic: OptionCritic) -> None:
        with pytest.raises(ValueError, match="state 维度"):
            option_critic.select_option(np.zeros(999))

    def test_q_value(self, option_critic: OptionCritic, state_dim: int) -> None:
        s = np.zeros(state_dim)
        q = option_critic.q_value(s, 0)
        assert isinstance(q, float)

    def test_q_value_invalid_option(self, option_critic: OptionCritic, state_dim: int) -> None:
        with pytest.raises(ValueError, match="option_id"):
            option_critic.q_value(np.zeros(state_dim), 999)

    def test_v_bar(self, option_critic: OptionCritic, state_dim: int) -> None:
        s = np.zeros(state_dim)
        v = option_critic.v_bar(s)
        assert isinstance(v, float)

    def test_update_termination(self, option_critic: OptionCritic, state_dim: int) -> None:
        s = np.zeros(state_dim)
        beta = option_critic.update_termination(s, 0)
        assert 0.0 <= beta <= 1.0

    def test_invalid_n_options(self, state_dim: int) -> None:
        with pytest.raises(ValueError):
            OptionCritic(0, state_dim)


# =============================================================================
# R374 HierarchicalAgent 测试
# =============================================================================

class TestR374Agent:
    """R374 分层智能体测试。"""

    def test_reset(self, agent: HierarchicalAgent) -> None:
        agent.reset()
        assert agent.current_option is None
        assert agent.option_step_count == 0

    def test_act_first_call(self, agent: HierarchicalAgent, state_dim: int) -> None:
        agent.reset()
        s = np.zeros(state_dim)
        result = agent.act(s)
        assert "option_id" in result
        assert "action" in result
        assert "probs" in result
        assert result["new_option"] is True

    def test_act_state_dim_mismatch(self, agent: HierarchicalAgent) -> None:
        with pytest.raises(ValueError, match="state 维度"):
            agent.act(np.zeros(999))

    def test_act_consecutive(self, agent: HierarchicalAgent, state_dim: int) -> None:
        """连续调用：option 可能持续或切换。"""
        agent.reset()
        s = np.zeros(state_dim)
        r1 = agent.act(s)
        r2 = agent.act(s)
        assert r1["option_id"] is not None
        assert r2["option_step"] >= 1

    def test_invalid_state_dim(self) -> None:
        with pytest.raises(ValueError):
            HierarchicalAgent(0)


# =============================================================================
# R375 HierarchicalTrainer 测试
# =============================================================================

class TestR375Trainer:
    """R375 分层训练器测试。"""

    def test_compute_smdp_advantages(self, trainer: HierarchicalTrainer) -> None:
        rewards = [1.0, 0.5]
        durations = [2, 3]
        values = [0.5, 0.5]
        advs = trainer.compute_smdp_advantages(rewards, durations, values)
        assert len(advs) == 2

    def test_compute_smdp_empty(self, trainer: HierarchicalTrainer) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            trainer.compute_smdp_advantages([], [], [])

    def test_compute_smdp_mismatch(self, trainer: HierarchicalTrainer) -> None:
        with pytest.raises(ValueError, match="option_rewards"):
            trainer.compute_smdp_advantages([1.0], [1, 2], [0.5])

    def test_update_option_policy(
        self, trainer: HierarchicalTrainer, state_dim: int
    ) -> None:
        states = [np.zeros(state_dim) for _ in range(3)]
        logprobs = np.array([0.0, 0.0, 0.0])
        advs = [1.0, 0.5, -0.5]
        loss = trainer.update_option_policy(states, logprobs, advs)
        assert isinstance(loss, float)

    def test_update_mismatch_states_logprobs(self, trainer: HierarchicalTrainer, state_dim: int) -> None:
        with pytest.raises(ValueError, match="logprobs"):
            trainer.update_option_policy(
                [np.zeros(state_dim)], np.array([0.0, 0.0]), [1.0]
            )

    def test_update_mismatch_states_advs(self, trainer: HierarchicalTrainer, state_dim: int) -> None:
        with pytest.raises(ValueError, match="advantages"):
            trainer.update_option_policy(
                [np.zeros(state_dim)], np.array([0.0]), [1.0, 2.0]
            )


# =============================================================================
# R03/R02/R04 合规
# =============================================================================

class TestCompliance:
    """合规测试。"""

    def test_r03_no_silent_fallback(self) -> None:
        from polaris.rl import rl_hierarchical as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_r02_5plus_urls(self) -> None:
        from polaris.rl import rl_hierarchical as mod
        assert mod.__doc__ is not None
        urls = [l for l in mod.__doc__.splitlines() if "http" in l or "sciencedirect" in l]
        assert len(urls) >= 5

    def test_r02_sutton_cited(self) -> None:
        from polaris.rl import rl_hierarchical as mod
        assert "Sutton" in mod.__doc__
        assert "Bacon" in mod.__doc__

    def test_r02_innovation_marked(self) -> None:
        from polaris.rl import rl_hierarchical as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src

    def test_r04_gpu_disabled(self) -> None:
        assert GPU_DISABLED_R04 is True

    def test_r04_no_gpu_imports(self) -> None:
        from polaris.rl import rl_hierarchical as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "import jax" not in src


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试：HRL 完整流程。"""

    def test_full_hrl_pipeline(
        self, state_dim: int, config: HierarchicalConfig
    ) -> None:
        """完整流程：reset → act → train。"""
        agent = HierarchicalAgent(state_dim, config)
        trainer = HierarchicalTrainer(agent)
        agent.reset()
        s = np.zeros(state_dim)
        # 多步交互
        rewards = []
        for _ in range(5):
            result = agent.act(s)
            rewards.append(1.0 if result["action"] == 0 else 0.0)
        # 训练
        advs = trainer.compute_smdp_advantages(
            rewards, [1] * len(rewards), [0.5] * len(rewards)
        )
        assert len(advs) == len(rewards)
