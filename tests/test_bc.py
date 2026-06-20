"""Behavior Cloning 单元测试（规则 10）。

测试 polaris.trainer.bc.BehaviorCloning / BehaviorCloningDiscrete 与
PPOAgent.pretrain / PPOAgentDiscrete.pretrain 接口。

来源:
- Pomerleau, NeurIPS 1989, ALVINN
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- pytest 最佳实践: https://docs.pytest.org/en/stable/explanation/goodpractices.html
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from polaris.trainer.bc import (  # noqa: E402
    BCConfig,
    BehaviorCloning,
    BehaviorCloningDiscrete,
)
from polaris.trainer.expert_dataset import (  # noqa: E402
    ACTION_DIM,
    OBS_DIM,
    ExpertDataset,
)
from polaris.trainer.ppo_buffers import PPOConfig  # noqa: E402
from polaris.trainer.ppo_networks import ActorCritic, ActorCriticDiscrete  # noqa: E402
from polaris.trainer.ppo_torch import PPOAgent, PPOAgentDiscrete  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXPERT_DIR = ROOT / "data" / "expert_demos"


@pytest.fixture
def dataset() -> ExpertDataset:
    """加载专家示范数据集 fixture。"""
    ds = ExpertDataset(str(EXPERT_DIR))
    ds.load()
    return ds


# ---------------------------------------------------------------------------
# BehaviorCloning（连续动作）
# ---------------------------------------------------------------------------


def test_bc_continuous_train_reduces_loss(dataset: ExpertDataset) -> None:
    """测试连续 BC 训练能降低损失。"""
    net = ActorCritic(obs_dim=OBS_DIM, action_dim=ACTION_DIM, hidden_dim=32)
    bc = BehaviorCloning(net, BCConfig(n_epochs=20, batch_size=8, lr=1e-3, log_every=100))
    metrics = bc.train(dataset)
    assert metrics["epoch"] == 20
    assert metrics["loss"] > 0
    # 训练后损失应低于初始损失
    initial_loss = bc.metrics[0]["loss"]
    final_loss = bc.metrics[-1]["loss"]
    assert final_loss < initial_loss, f"BC loss 未下降: {initial_loss} -> {final_loss}"


def test_bc_continuous_mse_loss(dataset: ExpertDataset) -> None:
    """测试 MSE 损失模式。"""
    net = ActorCritic(obs_dim=OBS_DIM, action_dim=ACTION_DIM, hidden_dim=16)
    bc = BehaviorCloning(net, BCConfig(n_epochs=5, batch_size=8, loss_type="mse", log_every=100))
    metrics = bc.train(dataset)
    assert metrics["mse"] > 0
    assert metrics["mse"] < 1.0  # 归一化动作的 MSE 应较小


def test_bc_continuous_nll_loss(dataset: ExpertDataset) -> None:
    """测试 NLL 损失模式。"""
    net = ActorCritic(obs_dim=OBS_DIM, action_dim=ACTION_DIM, hidden_dim=16)
    bc = BehaviorCloning(net, BCConfig(n_epochs=5, batch_size=8, loss_type="nll", log_every=100))
    metrics = bc.train(dataset)
    assert metrics["nll"] > 0


# ---------------------------------------------------------------------------
# BehaviorCloningDiscrete（离散动作）
# ---------------------------------------------------------------------------


def test_bc_discrete_train_reduces_loss() -> None:
    """测试离散 BC 训练能降低损失。"""
    obs_dim, n_actions = 16, 10
    net = ActorCriticDiscrete(obs_dim=obs_dim, n_actions=n_actions, hidden_dim=32)
    bc = BehaviorCloningDiscrete(net, BCConfig(n_epochs=20, batch_size=8, lr=1e-3, log_every=100))
    # 合成随机专家数据
    rng = np.random.default_rng(42)
    obs = rng.standard_normal((64, obs_dim)).astype(np.float32)
    actions = rng.integers(0, n_actions, size=(64,)).astype(np.int64)
    metrics = bc.train(obs, actions)
    assert metrics["epoch"] == 20
    initial_loss = bc.metrics[0]["loss"]
    final_loss = bc.metrics[-1]["loss"]
    assert final_loss < initial_loss, f"离散 BC loss 未下降: {initial_loss} -> {final_loss}"


def test_bc_discrete_accuracy_improves() -> None:
    """测试离散 BC 训练能提升准确率（在易学数据上）。"""
    obs_dim, n_actions = 8, 3
    net = ActorCriticDiscrete(obs_dim=obs_dim, n_actions=n_actions, hidden_dim=32)
    bc = BehaviorCloningDiscrete(net, BCConfig(n_epochs=30, batch_size=8, lr=1e-2, log_every=100))
    # 合成易学数据：obs[0] > 0 → action 1, obs[0] < 0 → action 0
    rng = np.random.default_rng(0)
    obs = rng.standard_normal((100, obs_dim)).astype(np.float32)
    actions = (obs[:, 0] > 0).astype(np.int64)
    bc.train(obs, actions)
    initial_acc = bc.metrics[0]["accuracy"]
    final_acc = bc.metrics[-1]["accuracy"]
    assert final_acc > initial_acc, f"准确率未提升: {initial_acc} -> {final_acc}"
    assert final_acc > 0.7, f"最终准确率过低: {final_acc}"


# ---------------------------------------------------------------------------
# PPOAgent.pretrain 接口
# ---------------------------------------------------------------------------


def test_ppo_agent_pretrain_continuous(dataset: ExpertDataset) -> None:
    """测试 PPOAgent.pretrain 接口（连续动作）。"""
    agent = PPOAgent(obs_dim=OBS_DIM, action_dim=ACTION_DIM, config=PPOConfig(), hidden_dim=32)
    obs, act = dataset.get_all()
    bc_cfg = BCConfig(n_epochs=5, batch_size=8, log_every=100)
    history = agent.pretrain(obs, act, config=bc_cfg)
    assert len(history) == 5
    assert history[-1]["loss"] > 0
    # 损失应下降
    assert history[-1]["loss"] < history[0]["loss"]


def test_ppo_agent_discrete_pretrain() -> None:
    """测试 PPOAgentDiscrete.pretrain 接口（离散动作）。"""
    obs_dim, n_actions = 16, 10
    agent = PPOAgentDiscrete(
        obs_dim=obs_dim, n_actions=n_actions, config=PPOConfig(), hidden_dim=32
    )
    rng = np.random.default_rng(42)
    obs = rng.standard_normal((32, obs_dim)).astype(np.float32)
    actions = rng.integers(0, n_actions, size=(32,)).astype(np.int64)
    bc_cfg = BCConfig(n_epochs=5, batch_size=8, log_every=100)
    history = agent.pretrain(obs, actions, config=bc_cfg)
    assert len(history) == 5
    assert history[-1]["loss"] > 0


def test_ppo_agent_pretrain_empty_data() -> None:
    """测试空数据集时 pretrain 不崩溃。"""
    agent = PPOAgent(obs_dim=OBS_DIM, action_dim=ACTION_DIM, config=PPOConfig(), hidden_dim=16)
    empty_obs = np.zeros((0, OBS_DIM), dtype=np.float32)
    empty_act = np.zeros((0, ACTION_DIM), dtype=np.float32)
    history = agent.pretrain(empty_obs, empty_act, config=BCConfig(n_epochs=5))
    assert len(history) == 1
    assert history[0]["loss"] == 0.0


# ---------------------------------------------------------------------------
# bc_loss 网络方法
# ---------------------------------------------------------------------------


def test_actor_critic_bc_loss() -> None:
    """测试 ActorCritic.bc_loss 方法。"""
    net = ActorCritic(obs_dim=8, action_dim=3, hidden_dim=16)
    obs = torch.randn(4, 8)
    actions = torch.randn(4, 3)
    # NLL 模式
    loss_nll, mse = net.bc_loss(obs, actions, loss_type="nll")
    assert loss_nll.dim() == 0  # 标量
    assert mse.dim() == 0
    assert float(loss_nll.detach()) > 0
    # MSE 模式
    loss_mse, _ = net.bc_loss(obs, actions, loss_type="mse")
    assert float(loss_mse.detach()) > 0


def test_actor_critic_discrete_bc_loss() -> None:
    """测试 ActorCriticDiscrete.bc_loss 方法。"""
    net = ActorCriticDiscrete(obs_dim=8, n_actions=5, hidden_dim=16)
    obs = torch.randn(4, 8)
    actions = torch.tensor([0, 1, 2, 3], dtype=torch.long)
    loss, acc = net.bc_loss(obs, actions)
    assert loss.dim() == 0
    assert acc.dim() == 0
    assert float(loss.detach()) > 0
    assert 0.0 <= float(acc.detach()) <= 1.0
