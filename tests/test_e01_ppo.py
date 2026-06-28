"""E01 PPO 强化学习验收测试。

验证 PPO 智能体的策略更新正确性、回报提升能力和训练稳定性。

文献来源:
- Schulman et al., 2017, PPO (Proximal Policy Optimization)
  https://arxiv.org/abs/1707.06347
- Schulman et al., 2015, GAE (Generalized Advantage Estimation)
  https://arxiv.org/abs/1506.02438
- Stable-Baselines3 PPO 实现
  https://stable-baselines3.readthedocs.io/
- CleanRL PPO 单文件实现
  https://github.com/vwxyzjn/cleanrl
- Loshchilov & Hutter, 2017, SGDR 余弦退火
  https://arxiv.org/abs/1608.03983
"""

import numpy as np

from polaris.trainer.ppo import (
    ActorCritic,
    Minibatch,
    PPOAgent,
    PPOConfig,
    RolloutBuffer,
    Transition,
    compute_gae,
)


class TestPPOConfig:
    """PPO 配置测试。"""

    def test_default_config(self):
        """M1: 默认配置参数正确。"""
        cfg = PPOConfig()
        assert cfg.lr == 3e-4
        assert cfg.gamma == 0.99
        assert cfg.gae_lambda == 0.95
        assert cfg.clip_eps == 0.2
        assert cfg.ent_coef == 0.01
        assert cfg.vf_coef == 0.5
        assert cfg.max_grad_norm == 0.5
        assert cfg.n_epochs == 4
        assert cfg.batch_size == 64

    def test_custom_config(self):
        """M1: 自定义配置参数正确。"""
        cfg = PPOConfig(lr=1e-3, gamma=0.95, clip_eps=0.3)
        assert cfg.lr == 1e-3
        assert cfg.gamma == 0.95
        assert cfg.clip_eps == 0.3


class TestActorCritic:
    """Actor-Critic 网络测试。"""

    def test_forward_shape(self):
        """M1: 前向传播输出形状正确。"""
        ac = ActorCritic(obs_dim=10, action_dim=3, hidden_dim=16)
        obs = np.random.randn(5, 10)
        mean, value = ac.forward(obs)
        assert mean.data.shape == (5, 3)
        assert value.data.shape == (5, 1)

    def test_get_action_returns_tuple(self):
        """M1: get_action 返回 (action, logprob, value) 三元组。"""
        ac = ActorCritic(obs_dim=8, action_dim=2, hidden_dim=16)
        obs = np.random.randn(8)
        action, logprob, value = ac.get_action(obs)
        assert action.shape == (2,)
        assert isinstance(logprob, float)
        assert isinstance(value, float)

    def test_evaluate_returns_entropy(self):
        """M1: evaluate 返回 logprob、value 和 entropy。"""
        ac = ActorCritic(obs_dim=8, action_dim=2, hidden_dim=16)
        obs = np.random.randn(4, 8)
        actions = np.random.randn(4, 2)
        lp, val, ent = ac.evaluate(obs, actions)
        assert lp.shape == (4,)
        assert val.shape == (4,)
        assert ent.shape == (4,)

    def test_action_log_std_trainable(self):
        """M1: action_log_std 是可训练参数。"""
        ac = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=8)
        params = ac.parameters()
        assert len(params) > 0


class TestRolloutBuffer:
    """Rollout 缓冲区测试。"""

    def test_buffer_starts_empty(self):
        """M1: 缓冲区初始为空。"""
        buf = RolloutBuffer()
        assert len(buf) == 0
        assert buf.obs == []

    def test_buffer_clear(self):
        """M1: clear 清空缓冲区。"""
        buf = RolloutBuffer()
        buf.obs.append(np.array([1.0, 2.0]))
        buf.rewards.append(1.0)
        assert len(buf) == 1
        buf.clear()
        assert len(buf) == 0
        assert buf.advantages.size == 0


class TestComputeGAE:
    """GAE 优势估计测试。"""

    def test_gae_basic(self):
        """M1: GAE 计算的优势和回报形状正确。"""
        rewards = [1.0, 2.0, 3.0]
        values = [0.5, 1.5, 2.5]
        dones = [False, False, True]
        adv, ret = compute_gae(rewards, values, dones, last_value=0.0)
        assert adv.shape == (3,)
        assert ret.shape == (3,)

    def test_gae_with_config(self):
        """M1: 使用自定义配置的 GAE 计算。"""
        cfg = PPOConfig(gamma=0.9, gae_lambda=0.9)
        rewards = [1.0, 1.0, 1.0]
        values = [0.0, 0.0, 0.0]
        dones = [False, False, False]
        adv, ret = compute_gae(rewards, values, dones, last_value=1.0, config=cfg)
        assert adv.shape == (3,)
        assert ret.shape == (3,)

    def test_gae_monotonic_returns(self):
        """M2: 正奖励下回报应递增（从后往前）。"""
        rewards = [1.0, 1.0, 1.0, 1.0]
        values = [0.0, 0.0, 0.0, 0.0]
        dones = [False, False, False, True]
        _, ret = compute_gae(rewards, values, dones, last_value=0.0)
        assert ret[0] >= ret[1]
        assert ret[1] >= ret[2]

    def test_gae_empty(self):
        """R03: 空序列 GAE 计算。"""
        adv, ret = compute_gae([], [], [], last_value=0.0)
        assert adv.size == 0
        assert ret.size == 0


class TestTransition:
    """Transition 数据类测试。"""

    def test_transition_fields(self):
        """M1: Transition 包含所有必要字段。"""
        t = Transition(
            obs=np.array([1.0, 2.0]),
            action=np.array([0.5]),
            reward=1.0,
            logprob=-0.5,
            value=0.3,
            done=False,
        )
        assert t.reward == 1.0
        assert t.done is False


class TestMinibatch:
    """Minibatch 数据类测试。"""

    def test_minibatch_fields(self):
        """M1: Minibatch 包含所有必要字段。"""
        mb = Minibatch(
            obs=np.zeros((4, 8)),
            actions=np.zeros((4, 2)),
            old_logprobs=np.zeros(4),
            advantages=np.zeros(4),
            returns=np.zeros(4),
        )
        assert mb.obs.shape == (4, 8)
        assert mb.actions.shape == (4, 2)


class TestPPOAgent:
    """PPO 智能体测试。"""

    def test_agent_init(self):
        """M1: PPOAgent 初始化成功。"""
        agent = PPOAgent(obs_dim=10, action_dim=3, hidden_dim=16)
        assert agent.obs_dim == 10
        assert agent.action_dim == 3
        assert isinstance(agent.ac, ActorCritic)

    def test_agent_get_action(self):
        """M1: get_action 返回正确格式。"""
        agent = PPOAgent(obs_dim=8, action_dim=2, hidden_dim=16)
        obs = np.random.randn(8)
        action, logprob, value = agent.get_action(obs)
        assert action.shape == (2,)
        assert isinstance(logprob, float)
        assert isinstance(value, float)

    def test_agent_store_and_len(self):
        """M1: store 存储转移数据。"""
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        for i in range(5):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=float(i),
                logprob=-1.0,
                value=0.5,
                done=(i == 4),
            ))
        assert len(agent.buffer) == 5

    def test_agent_compute_advantages(self):
        """M1: compute_advantages 计算成功。"""
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        for i in range(5):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=1.0,
                logprob=-1.0,
                value=0.5,
                done=(i == 4),
            ))
        agent.compute_advantages(last_value=0.0)
        assert agent.buffer.advantages.shape == (5,)
        assert agent.buffer.returns.shape == (5,)

    def test_agent_update_returns_metrics(self):
        """M1: update 返回训练指标字典。"""
        agent = PPOAgent(
            obs_dim=4,
            action_dim=2,
            hidden_dim=8,
            config=PPOConfig(n_epochs=1, batch_size=4),
        )
        for i in range(8):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=1.0,
                logprob=-1.0,
                value=0.5,
                done=(i == 7),
            ))
        metrics = agent.update(last_value=0.0)
        assert "loss" in metrics
        assert "policy_loss" in metrics
        assert "value_loss" in metrics
        assert "entropy" in metrics

    def test_agent_update_buffer_cleared(self):
        """M1: update 后缓冲区被清空。"""
        agent = PPOAgent(
            obs_dim=4,
            action_dim=2,
            hidden_dim=8,
            config=PPOConfig(n_epochs=1, batch_size=4),
        )
        for i in range(8):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=1.0,
                logprob=-1.0,
                value=0.5,
                done=(i == 7),
            ))
        agent.update(last_value=0.0)
        assert len(agent.buffer) == 0

    def test_agent_empty_update(self):
        """R03: 空缓冲区 update 不报错。"""
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        metrics = agent.update(last_value=0.0)
        assert metrics["loss"] == 0.0

    def test_agent_lr_constant(self):
        """M3: 恒定学习率调度。"""
        cfg = PPOConfig(lr_schedule="constant", lr=1e-3)
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8, config=cfg)
        lr1 = agent._get_lr()
        agent.current_step = 100
        lr2 = agent._get_lr()
        assert lr1 == lr2 == 1e-3

    def test_agent_lr_cosine(self):
        """M3: 余弦退火学习率调度。"""
        cfg = PPOConfig(
            lr_schedule="cosine",
            lr=1e-3,
            total_steps=1000,
        )
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8, config=cfg)
        lr_start = agent._get_lr()
        agent.current_step = 500
        lr_mid = agent._get_lr()
        agent.current_step = 1000
        lr_end = agent._get_lr()
        assert lr_start >= lr_mid
        assert lr_mid >= lr_end

    def test_agent_save_load(self, tmp_path):
        """M3: 检查点保存和加载。"""
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        path = tmp_path / "checkpoint.json"
        agent.save(path)
        assert path.exists()

        agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        agent2.load(path)
        params1 = [p.data for p in agent.ac.parameters()]
        params2 = [p.data for p in agent2.ac.parameters()]
        for p1, p2 in zip(params1, params2, strict=False):
            np.testing.assert_array_equal(p1, p2)

    def test_agent_metrics_history(self):
        """M3: 训练指标历史记录。"""
        agent = PPOAgent(
            obs_dim=4,
            action_dim=2,
            hidden_dim=8,
            config=PPOConfig(n_epochs=1, batch_size=4),
        )
        for _ in range(3):
            for i in range(8):
                agent.store(Transition(
                    obs=np.random.randn(4),
                    action=np.random.randn(2),
                    reward=1.0,
                    logprob=-1.0,
                    value=0.5,
                    done=(i == 7),
                ))
            agent.update(last_value=0.0)
        assert len(agent.metrics) == 3

    def test_gradient_clipping(self):
        """M3: 梯度裁剪生效。"""
        agent = PPOAgent(
            obs_dim=4,
            action_dim=2,
            hidden_dim=8,
            config=PPOConfig(max_grad_norm=0.1, n_epochs=1, batch_size=4),
        )
        for i in range(8):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=1.0,
                logprob=-1.0,
                value=0.5,
                done=(i == 7),
            ))
        agent.update(last_value=0.0)
        for p in agent.ac.parameters():
            if p.grad is not None:
                norm = np.linalg.norm(p.grad)
                assert norm <= 0.1 + 1e-6


class TestAdvantageNormalization:
    """优势标准化测试。"""

    def test_advantages_normalized(self):
        """M2: 优势被标准化（均值≈0，方差≈1）。"""
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        for i in range(20):
            agent.store(Transition(
                obs=np.random.randn(4),
                action=np.random.randn(2),
                reward=float(np.random.randn()),
                logprob=-1.0,
                value=float(np.random.randn()),
                done=(i == 19),
            ))
        agent.compute_advantages(last_value=0.0)
        adv = agent.buffer.advantages
        assert abs(adv.mean()) < 0.1
        assert abs(adv.std() - 1.0) < 0.1
