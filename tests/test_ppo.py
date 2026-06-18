"""PPO 智能体测试（Task 13）。"""

from __future__ import annotations

import numpy as np

from polaris.trainer.ppo import PPOAgent, PPOConfig, Transition, compute_gae


def test_ppo_agent_creation():
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    assert agent.obs_dim == 4
    assert agent.action_dim == 2


def test_get_action_shapes():
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = np.random.randn(4)
    action, logprob, value = agent.get_action(obs)
    assert action.shape == (2,)
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_compute_gae_simple():
    rewards = [1.0, 1.0, 1.0]
    values = [0.5, 0.5, 0.5]
    dones = [False, False, True]
    adv, ret = compute_gae(rewards, values, dones, last_value=0.0)
    assert len(adv) == 3
    assert len(ret) == 3


def test_ppo_update_runs():
    np.random.seed(0)
    agent = PPOAgent(
        obs_dim=4,
        action_dim=2,
        config=PPOConfig(lr=1e-3, n_epochs=2, batch_size=16),
        hidden_dim=32,
    )
    obs = np.random.randn(4)
    for _ in range(32):
        a, lp, v = agent.get_action(obs)
        agent.store(Transition(obs, a, -1.0, lp, v, False))
    metrics = agent.update(last_value=0.0)
    assert "policy_loss" in metrics
    assert "value_loss" in metrics
    assert len(agent.metrics) == 1


def test_ppo_save_load(tmp_path):
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    obs = np.random.randn(4)
    for _ in range(16):
        a, lp, v = agent.get_action(obs)
        agent.store(Transition(obs, a, -1.0, lp, v, False))
    agent.update(last_value=0.0)
    ckpt = tmp_path / "ppo.json"
    agent.save(ckpt)
    assert ckpt.exists()
    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    agent2.load(ckpt)
    # 加载后参数应一致
    p1 = agent.ac.parameters()[0].data
    p2 = agent2.ac.parameters()[0].data
    assert np.allclose(p1, p2)


def test_ppo_checkpoint_resume(tmp_path):
    """断点续训：加载后能继续训练。"""
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    ckpt = tmp_path / "ppo_resume.json"
    agent.save(ckpt)
    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=32)
    agent2.load(ckpt)
    obs = np.random.randn(4)
    for _ in range(16):
        a, lp, v = agent2.get_action(obs)
        agent2.store(Transition(obs, a, -1.0, lp, v, False))
    m = agent2.update(last_value=0.0)
    assert "policy_loss" in m
