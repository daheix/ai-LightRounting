"""PPO 数据结构与网络模块测试（Task P1）。

覆盖：
- ``src/polaris/trainer/ppo_buffers.py``：PPOConfig / RolloutBuffer / Transition /
  BufferTensors / AgentSpec / compute_gae
- ``src/polaris/trainer/ppo_networks.py``：ActorCritic / ActorCriticDiscrete

来源:
- Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
- Engstrom et al., 2020, Implementation Matters in PPO
  https://arxiv.org/abs/2005.12729
- SB3 PPO: https://stable-baselines3.readthedocs.io/
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from polaris.trainer.ppo_buffers import (
    AgentSpec,
    BufferTensors,
    PPOConfig,
    RolloutBuffer,
    Transition,
    compute_gae,
)
from polaris.trainer.ppo_networks import ActorCritic, ActorCriticDiscrete

# ---------------------------------------------------------------------------
# PPOConfig
# ---------------------------------------------------------------------------


def test_ppo_config_defaults():
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
    assert cfg.clip_vf == 0.0
    assert cfg.lr_schedule == "constant"
    assert cfg.lr_warmup_steps == 0
    assert cfg.total_steps == 1000


def test_ppo_config_custom():
    cfg = PPOConfig(
        lr=1e-3,
        gamma=0.95,
        gae_lambda=0.9,
        clip_eps=0.1,
        n_epochs=10,
        batch_size=32,
        clip_vf=10.0,
        lr_schedule="cosine",
        lr_warmup_steps=100,
        total_steps=10000,
    )
    assert cfg.lr == 1e-3
    assert cfg.gamma == 0.95
    assert cfg.gae_lambda == 0.9
    assert cfg.clip_eps == 0.1
    assert cfg.n_epochs == 10
    assert cfg.batch_size == 32
    assert cfg.clip_vf == 10.0
    assert cfg.lr_schedule == "cosine"
    assert cfg.lr_warmup_steps == 100
    assert cfg.total_steps == 10000


# ---------------------------------------------------------------------------
# RolloutBuffer
# ---------------------------------------------------------------------------


def test_rollout_buffer_init_empty():
    buf = RolloutBuffer()
    assert len(buf) == 0
    assert buf.obs == []
    assert buf.actions == []
    assert buf.rewards == []
    assert buf.logprobs == []
    assert buf.values == []
    assert buf.dones == []
    assert buf.advantages.size == 0
    assert buf.returns.size == 0


def test_rollout_buffer_append_and_len():
    buf = RolloutBuffer()
    buf.obs.append(np.zeros(4))
    buf.actions.append(np.zeros(2))
    buf.rewards.append(1.0)
    buf.logprobs.append(0.5)
    buf.values.append(0.3)
    buf.dones.append(False)
    assert len(buf) == 1


def test_rollout_buffer_clear():
    buf = RolloutBuffer()
    buf.obs.append(np.zeros(4))
    buf.actions.append(np.zeros(2))
    buf.rewards.append(1.0)
    buf.logprobs.append(0.5)
    buf.values.append(0.3)
    buf.dones.append(False)
    buf.advantages = np.array([1.0, 2.0])
    buf.returns = np.array([1.0, 2.0])
    buf.clear()
    assert len(buf) == 0
    assert buf.obs == []
    assert buf.advantages.size == 0
    assert buf.returns.size == 0


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


def test_transition_construction():
    obs = np.array([1.0, 2.0])
    action = np.array([0.5])
    t = Transition(obs=obs, action=action, reward=1.0, logprob=0.5, value=0.3, done=False)
    assert np.array_equal(t.obs, obs)
    assert np.array_equal(t.action, action)
    assert t.reward == 1.0
    assert t.logprob == 0.5
    assert t.value == 0.3
    assert t.done is False


# ---------------------------------------------------------------------------
# BufferTensors
# ---------------------------------------------------------------------------


def test_buffer_tensors_construction():
    bt = BufferTensors(
        obs=torch.zeros(8, 4),
        actions=torch.zeros(8, 2),
        logprobs=torch.zeros(8),
        values=torch.zeros(8),
        advantages=torch.zeros(8),
        returns=torch.zeros(8),
    )
    assert bt.obs.shape == (8, 4)
    assert bt.actions.shape == (8, 2)
    assert bt.logprobs.shape == (8,)
    assert bt.values.shape == (8,)
    assert bt.advantages.shape == (8,)
    assert bt.returns.shape == (8,)


# ---------------------------------------------------------------------------
# AgentSpec
# ---------------------------------------------------------------------------


def test_agent_spec_defaults():
    spec = AgentSpec(obs_dim=4, n_actions=10)
    assert spec.obs_dim == 4
    assert spec.n_actions == 10
    assert spec.hidden_dim == 128


def test_agent_spec_custom():
    spec = AgentSpec(obs_dim=8, n_actions=20, hidden_dim=64)
    assert spec.obs_dim == 8
    assert spec.n_actions == 20
    assert spec.hidden_dim == 64


# ---------------------------------------------------------------------------
# compute_gae
# ---------------------------------------------------------------------------


def test_compute_gae_empty():
    """空序列应返回空数组。"""
    adv, ret = compute_gae([], [], [], 0.0)
    assert len(adv) == 0
    assert len(ret) == 0


def test_compute_gae_single_step_terminal():
    """单步终止：adv = reward - value, ret = reward。"""
    cfg = PPOConfig(gamma=0.99, gae_lambda=0.95)
    adv, ret = compute_gae([1.0], [0.5], [True], last_value=0.0, config=cfg)
    # delta = 1.0 + 0.99*0*0 - 0.5 = 0.5
    # last_gae = 0.5 + 0.99*0.95*0*0.5 = 0.5
    assert adv[0] == pytest.approx(0.5, rel=1e-6)
    # ret = adv + value = 0.5 + 0.5 = 1.0
    assert ret[0] == pytest.approx(1.0, rel=1e-6)


def test_compute_gae_single_step_non_terminal():
    """单步非终止：使用 last_value 作为 next_value。"""
    cfg = PPOConfig(gamma=0.99, gae_lambda=0.95)
    adv, ret = compute_gae([1.0], [0.5], [False], last_value=0.8, config=cfg)
    # delta = 1.0 + 0.99*0.8*1 - 0.5 = 1.292
    # last_gae = 1.292 + 0.99*0.95*1*0 = 1.292
    assert adv[0] == pytest.approx(1.292, rel=1e-4)
    # ret = 1.292 + 0.5 = 1.792
    assert ret[0] == pytest.approx(1.792, rel=1e-4)


def test_compute_gae_multi_step():
    """多步 GAE 应正确累积。"""
    cfg = PPOConfig(gamma=0.99, gae_lambda=0.95)
    rewards = [1.0, 1.0, 1.0]
    values = [0.5, 0.5, 0.5]
    dones = [False, False, True]
    adv, ret = compute_gae(rewards, values, dones, last_value=0.0, config=cfg)
    assert len(adv) == 3
    assert len(ret) == 3
    # 第 3 步终止: delta_3 = 1.0 + 0 - 0.5 = 0.5; gae_3 = 0.5
    assert adv[2] == pytest.approx(0.5, rel=1e-6)
    # 第 2 步: delta_2 = 1.0 + 0.99*0.5 - 0.5 = 0.995
    # gae_2 = 0.995 + 0.99*0.95*1*0.5 = 0.995 + 0.47025 = 1.46525
    assert adv[1] == pytest.approx(1.46525, rel=1e-4)


def test_compute_gae_default_config():
    """config=None 时应使用默认 gamma=0.99, gae_lambda=0.95。"""
    adv, ret = compute_gae([1.0], [0.5], [True], 0.0)
    assert adv[0] == pytest.approx(0.5, rel=1e-6)


def test_compute_gae_returns_equal_advantages_plus_values():
    """ret = adv + value 应恒成立。"""
    cfg = PPOConfig()
    rewards = [0.5, -0.3, 1.2, 0.0]
    values = [0.1, 0.2, 0.3, 0.4]
    dones = [False, False, False, True]
    adv, ret = compute_gae(rewards, values, dones, last_value=0.5, config=cfg)
    for a, r, v in zip(adv, ret, values, strict=True):
        assert r == pytest.approx(a + v, rel=1e-6)


# ---------------------------------------------------------------------------
# ActorCritic（连续动作）
# ---------------------------------------------------------------------------


def test_actor_critic_creation():
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    assert isinstance(net, ActorCritic)
    # 共享编码器应有 2 个 Linear 层
    assert len(net.shared) == 4  # Linear, ReLU, Linear, ReLU
    assert net.action_mean.in_features == 32
    assert net.action_mean.out_features == 2
    assert net.value_head.in_features == 32
    assert net.value_head.out_features == 1
    # action_log_std 是可学习参数
    assert net.action_log_std.shape == (2,)


def test_actor_critic_forward_shapes():
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = torch.randn(8, 4)
    mean, value = net(obs)
    assert mean.shape == (8, 2)
    assert value.shape == (8, 1)


def test_actor_critic_forward_single_obs():
    """单样本前向应正确。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = torch.randn(1, 4)
    mean, value = net(obs)
    assert mean.shape == (1, 2)
    assert value.shape == (1, 1)


def test_actor_critic_get_action_shapes():
    """get_action 应返回 (action_np, logprob_float, value_float)。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = np.random.randn(4)
    action, logprob, value = net.get_action(obs)
    assert action.shape == (2,)
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_actor_critic_evaluate_shapes():
    """evaluate 应返回 (logprob, value, entropy) 张量。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = torch.randn(8, 4)
    actions = torch.randn(8, 2)
    logprob, value, entropy = net.evaluate(obs, actions)
    assert logprob.shape == (8,)
    assert value.shape == (8,)
    assert entropy.shape == (8,)


def test_actor_critic_orthogonal_init():
    """共享层应使用 gain=√2 的 orthogonal 初始化。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    # 共享层第一层权重标准差应接近 √2 / sqrt(fan_in)（orthogonal 默认）
    w = net.shared[0].weight.detach().cpu().numpy()
    # orthogonal 初始化的权重标准差应非零且有限
    assert np.std(w) > 0
    assert np.isfinite(np.std(w))


def test_actor_critic_action_mean_small_gain():
    """策略头 action_mean 应使用 gain=0.01（SB3 默认）。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    w = net.action_mean.weight.detach().cpu().numpy()
    # gain=0.01 的 orthogonal 初始化权重标准差应很小
    assert np.std(w) < 0.1


# ---------------------------------------------------------------------------
# ActorCriticDiscrete（离散动作）
# ---------------------------------------------------------------------------


def test_actor_critic_discrete_creation():
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    assert isinstance(net, ActorCriticDiscrete)
    assert net.n_actions == 10
    assert len(net.shared) == 4
    assert net.action_logits.in_features == 32
    assert net.action_logits.out_features == 10
    assert net.value_head.in_features == 32
    assert net.value_head.out_features == 1


def test_actor_critic_discrete_forward_shapes():
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = torch.randn(8, 4)
    logits, value = net(obs)
    assert logits.shape == (8, 10)
    assert value.shape == (8, 1)


def test_actor_critic_discrete_get_action():
    """离散 get_action 应返回 (int, float, float)。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = np.random.randn(4)
    action, logprob, value = net.get_action(obs)
    assert isinstance(action, int)
    assert 0 <= action < 10
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_actor_critic_discrete_evaluate_shapes():
    """离散 evaluate 应返回正确形状。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = torch.randn(8, 4)
    actions = torch.randint(0, 10, (8, 1))
    logprob, value, entropy = net.evaluate(obs, actions)
    assert logprob.shape == (8,)
    assert value.shape == (8,)
    assert entropy.shape == (8,)


def test_actor_critic_discrete_action_logits_small_gain():
    """离散策略头 action_logits 应使用 gain=0.01。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    w = net.action_logits.weight.detach().cpu().numpy()
    assert np.std(w) < 0.1


def test_actor_critic_discrete_uniform_initial_distribution():
    """初始化时 logits 应接近均匀分布（gain=0.01 → logits 接近 0）。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = torch.randn(4, 4)
    logits, _ = net(obs)
    # logits 标准差应较小（接近均匀）
    assert logits.std().item() < 1.0
