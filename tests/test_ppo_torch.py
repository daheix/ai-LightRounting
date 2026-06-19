"""PPO PyTorch 实现测试（Task P1）。

覆盖 ``src/polaris/trainer/ppo_torch.py`` 的 ``PPOAgent``（连续动作）
与 ``PPOAgentDiscrete``（离散动作）两个核心类，包括：
- 创建与配置
- get_action 返回形状
- store + update（GAE + clip + 价值损失）
- save/load 检查点（JSON 格式，与 NumPy 版兼容）
- 学习率调度（constant / cosine / linear + warmup）
- 空缓冲区 update 返回零值

来源:
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- SB3 PPO: https://stable-baselines3.readthedocs.io/
- CleanRL PPO: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from polaris.trainer.ppo_buffers import AgentSpec, PPOConfig, Transition
from polaris.trainer.ppo_networks import ActorCritic, ActorCriticDiscrete
from polaris.trainer.ppo_torch import PPOAgent, PPOAgentDiscrete

# ---------------------------------------------------------------------------
# PPOAgent（连续动作空间）
# ---------------------------------------------------------------------------


def test_ppo_agent_creation():
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    assert agent.obs_dim == 4
    assert agent.action_dim == 2
    assert isinstance(agent.config, PPOConfig)
    assert agent.current_step == 0
    assert len(agent.metrics) == 0


def test_ppo_agent_get_action_shapes():
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = np.random.randn(4)
    action, logprob, value = agent.get_action(obs)
    assert action.shape == (2,)
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_ppo_agent_store_and_update():
    """rollout → store → update 应返回包含 policy_loss/value_loss 的指标。"""
    np.random.seed(42)
    torch.manual_seed(42)
    agent = PPOAgent(
        obs_dim=4,
        action_dim=2,
        config=PPOConfig(lr=1e-3, n_epochs=2, batch_size=16),
        hidden_dim=32,
    )
    obs = np.random.randn(4)
    for _ in range(32):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    metrics = agent.update(last_value=0.0)
    assert "policy_loss" in metrics
    assert "value_loss" in metrics
    assert "entropy" in metrics
    assert "loss" in metrics
    assert len(agent.metrics) == 1
    # current_step 应在 update 后递增
    assert agent.current_step == 1
    # buffer 应被清空
    assert len(agent.buffer) == 0


def test_ppo_agent_update_empty_buffer():
    """空缓冲区 update 应返回零指标且不抛异常。"""
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    metrics = agent.update(last_value=0.0)
    assert metrics["loss"] == 0.0
    assert metrics["policy_loss"] == 0.0
    assert metrics["value_loss"] == 0.0
    assert metrics["entropy"] == 0.0


def test_ppo_agent_save_load(tmp_path):
    """JSON 检查点保存/加载，参数应一致。"""
    np.random.seed(0)
    torch.manual_seed(0)
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = np.random.randn(4)
    for _ in range(16):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    agent.update(last_value=0.0)

    ckpt = tmp_path / "ppo_torch.json"
    agent.save(ckpt)
    assert ckpt.exists()

    # JSON 格式校验
    state = json.loads(ckpt.read_text(encoding="utf-8"))
    assert state["obs_dim"] == 4
    assert state["action_dim"] == 2
    assert "params" in state
    assert "config" in state

    # 加载后参数应一致
    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    agent2.load(ckpt)
    p1 = list(agent.ac.parameters())[0].detach().cpu().numpy()
    p2 = list(agent2.ac.parameters())[0].detach().cpu().numpy()
    np.testing.assert_allclose(p1, p2, atol=1e-6)


def test_ppo_agent_checkpoint_resume(tmp_path):
    """断点续训：加载后能继续训练。"""
    np.random.seed(1)
    torch.manual_seed(1)
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    ckpt = tmp_path / "ppo_resume.json"
    agent.save(ckpt)

    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    agent2.load(ckpt)
    obs = np.random.randn(4)
    for _ in range(16):
        action, logprob, value = agent2.get_action(obs)
        agent2.store(Transition(obs, action, -1.0, logprob, value, False))
    metrics = agent2.update(last_value=0.0)
    assert "policy_loss" in metrics


# ---------------------------------------------------------------------------
# 学习率调度
# ---------------------------------------------------------------------------


def test_lr_schedule_constant():
    """constant 调度：学习率恒等于 config.lr。"""
    cfg = PPOConfig(lr=1e-3, lr_schedule="constant")
    agent = PPOAgent(obs_dim=4, action_dim=2, config=cfg, hidden_dim=16)
    assert agent._get_lr() == pytest.approx(1e-3)
    agent.current_step = 100
    assert agent._get_lr() == pytest.approx(1e-3)


def test_lr_schedule_cosine():
    """cosine 调度：学习率从 lr 衰减到 0 附近。"""
    cfg = PPOConfig(
        lr=1e-3,
        lr_schedule="cosine",
        lr_warmup_steps=0,
        total_steps=100,
    )
    agent = PPOAgent(obs_dim=4, action_dim=2, config=cfg, hidden_dim=16)
    # step=0 时 lr 接近最大值
    agent.current_step = 0
    lr_start = agent._get_lr()
    assert lr_start == pytest.approx(1e-3, rel=1e-4)
    # step=50 时 lr 应衰减
    agent.current_step = 50
    lr_mid = agent._get_lr()
    assert lr_mid < lr_start
    # step=100 时 lr 接近 0
    agent.current_step = 100
    lr_end = agent._get_lr()
    assert lr_end < lr_mid
    assert lr_end == pytest.approx(0.0, abs=1e-4)


def test_lr_schedule_linear():
    """linear 调度：学习率线性衰减到 0。"""
    cfg = PPOConfig(
        lr=1e-3,
        lr_schedule="linear",
        lr_warmup_steps=0,
        total_steps=100,
    )
    agent = PPOAgent(obs_dim=4, action_dim=2, config=cfg, hidden_dim=16)
    agent.current_step = 0
    assert agent._get_lr() == pytest.approx(1e-3, rel=1e-4)
    agent.current_step = 50
    assert agent._get_lr() == pytest.approx(5e-4, rel=1e-3)
    agent.current_step = 100
    assert agent._get_lr() == pytest.approx(0.0, abs=1e-4)


def test_lr_schedule_warmup():
    """warmup 阶段学习率线性增长。"""
    cfg = PPOConfig(
        lr=1e-3,
        lr_schedule="cosine",
        lr_warmup_steps=10,
        total_steps=100,
    )
    agent = PPOAgent(obs_dim=4, action_dim=2, config=cfg, hidden_dim=16)
    agent.current_step = 0
    lr_0 = agent._get_lr()
    agent.current_step = 5
    lr_5 = agent._get_lr()
    agent.current_step = 10
    lr_10 = agent._get_lr()
    # warmup 阶段应递增
    assert lr_0 < lr_5 < lr_10
    # warmup 结束时应等于 lr
    assert lr_10 == pytest.approx(1e-3, rel=1e-4)


def test_lr_schedule_applied_on_update():
    """update 后优化器学习率应被更新。"""
    cfg = PPOConfig(
        lr=1e-3,
        lr_schedule="cosine",
        lr_warmup_steps=0,
        total_steps=10,
    )
    agent = PPOAgent(obs_dim=4, action_dim=2, config=cfg, hidden_dim=16)
    obs = np.random.randn(4)
    for _ in range(8):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    agent.update(last_value=0.0)
    # current_step=1, progress=0.1, lr 应小于初始值
    lr_after = agent.optimizer.param_groups[0]["lr"]
    assert lr_after < 1e-3


# ---------------------------------------------------------------------------
# PPOAgentDiscrete（离散动作空间）
# ---------------------------------------------------------------------------


def test_ppo_agent_discrete_creation():
    agent = PPOAgentDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    assert agent.n_actions == 10
    assert isinstance(agent.config, PPOConfig)
    assert agent._total_steps == 0


def test_ppo_agent_discrete_get_action():
    """离散动作应为 int，logprob/value 为 float。"""
    np.random.seed(0)
    torch.manual_seed(0)
    agent = PPOAgentDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = np.random.randn(4)
    action, logprob, value = agent.get_action(obs)
    assert isinstance(action, int)
    assert 0 <= action < 10
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_ppo_agent_discrete_store_and_update():
    """离散 PPO rollout → store → update 应返回有效指标。"""
    np.random.seed(42)
    torch.manual_seed(42)
    agent = PPOAgentDiscrete(
        obs_dim=4,
        n_actions=10,
        config=PPOConfig(lr=1e-3, n_epochs=2, batch_size=16),
        hidden_dim=32,
    )
    obs = np.random.randn(4)
    for _ in range(32):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    metrics = agent.update(last_value=0.0)
    assert "policy_loss" in metrics
    assert "value_loss" in metrics
    assert "entropy" in metrics
    assert "loss" in metrics
    # 离散动作的熵应 > 0（未收敛前）
    assert metrics["entropy"] >= 0.0
    # buffer 应被清空
    assert len(agent.buffer) == 0
    # total_steps 应累加
    assert agent._total_steps == 32


def test_ppo_agent_discrete_update_empty_buffer():
    """空缓冲区 update 应返回零指标。"""
    agent = PPOAgentDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    metrics = agent.update(last_value=0.0)
    assert metrics["loss"] == 0
    assert metrics["policy_loss"] == 0
    assert metrics["value_loss"] == 0
    assert metrics["entropy"] == 0


def test_ppo_agent_discrete_save_load(tmp_path):
    """离散 PPO 检查点保存/加载（torch.save 格式）。"""
    np.random.seed(0)
    torch.manual_seed(0)
    agent = PPOAgentDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = np.random.randn(4)
    for _ in range(16):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    agent.update(last_value=0.0)

    ckpt = tmp_path / "ppo_discrete.pt"
    agent.save(ckpt)
    assert ckpt.exists()

    # 通过 load 类方法加载
    spec = AgentSpec(obs_dim=4, n_actions=10, hidden_dim=32)
    agent2 = PPOAgentDiscrete.load(ckpt, agent.config, spec)
    assert agent2.n_actions == 10
    # 加载后参数应一致
    p1 = list(agent.network.parameters())[0].detach().cpu().numpy()
    p2 = list(agent2.network.parameters())[0].detach().cpu().numpy()
    np.testing.assert_allclose(p1, p2, atol=1e-6)
    # total_steps 应一致
    assert agent2._total_steps == agent._total_steps


def test_ppo_agent_discrete_lr_schedule_cosine():
    """离散 PPO cosine 学习率调度。"""
    cfg = PPOConfig(
        lr=1e-3,
        lr_schedule="cosine",
        total_steps=100,
    )
    agent = PPOAgentDiscrete(obs_dim=4, n_actions=10, config=cfg, hidden_dim=16)
    # 跑一次 update 让 _total_steps 增加
    obs = np.random.randn(4)
    for _ in range(8):
        action, logprob, value = agent.get_action(obs)
        agent.store(Transition(obs, action, -1.0, logprob, value, False))
    agent.update(last_value=0.0)
    # _total_steps=8, progress=0.08, lr 应小于初始值
    lr_after = agent.optimizer.param_groups[0]["lr"]
    assert lr_after < 1e-3


# ---------------------------------------------------------------------------
# 网络模块（ActorCritic / ActorCriticDiscrete）
# ---------------------------------------------------------------------------


def test_actor_critic_forward_shapes():
    """ActorCritic 前向应返回 (mean, value) 正确形状。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = torch.randn(8, 4)
    mean, value = net(obs)
    assert mean.shape == (8, 2)
    assert value.shape == (8, 1)


def test_actor_critic_evaluate_shapes():
    """evaluate 应返回 (logprob, value, entropy) 正确形状。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = torch.randn(8, 4)
    actions = torch.randn(8, 2)
    logprob, value, entropy = net.evaluate(obs, actions)
    assert logprob.shape == (8,)
    assert value.shape == (8,)
    assert entropy.shape == (8,)


def test_actor_critic_orthogonal_init():
    """策略头应使用 gain=0.01 的 orthogonal 初始化（SB3 默认）。"""
    net = ActorCritic(obs_dim=4, action_dim=2, hidden_dim=32)
    # action_mean 权重标准差应较小（gain=0.01）
    w = net.action_mean.weight.detach().cpu().numpy()
    assert np.std(w) < 0.1


def test_actor_critic_discrete_forward_shapes():
    """ActorCriticDiscrete 前向应返回 (logits, value)。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = torch.randn(8, 4)
    logits, value = net(obs)
    assert logits.shape == (8, 10)
    assert value.shape == (8, 1)


def test_actor_critic_discrete_evaluate_shapes():
    """离散 evaluate 应返回 (logprob, value, entropy)。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = torch.randn(8, 4)
    actions = torch.randint(0, 10, (8, 1))
    logprob, value, entropy = net.evaluate(obs, actions)
    assert logprob.shape == (8,)
    assert value.shape == (8,)
    assert entropy.shape == (8,)


def test_actor_critic_discrete_get_action_in_range():
    """离散 get_action 应返回 [0, n_actions) 范围内的整数。"""
    net = ActorCriticDiscrete(obs_dim=4, n_actions=10, hidden_dim=32)
    obs = np.random.randn(4)
    for _ in range(20):
        action, logprob, value = net.get_action(obs)
        assert isinstance(action, int)
        assert 0 <= action < 10
        assert isinstance(logprob, float)
        assert isinstance(value, float)
