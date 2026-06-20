"""Behavior Cloning（行为克隆）实现。

用专家示范数据监督学习 PPO 策略网络，作为 RL 微调的初始化。
支持连续动作（MSE/NLL）与离散动作（CrossEntropy）两种模式。

方法:
- 连续动作 BC：最大化高斯策略对专家动作的对数似然（NLL 损失）
  L_bc = -E[log π(a_expert | s)]
- 离散动作 BC：交叉熵损失
  L_bc = -E[log p(a_expert | s)]

来源:
- Pomerleau, "ALVINN: An Autonomous Land Vehicle in a Neural Network",
  NeurIPS 1989, https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- Ross & Bagnell, "A Reduction of Imitation Learning to No-Regret Online Learning",
  AISTATS 2011 (DAgger), https://arxiv.org/abs/1011.0686
- Hester et al., "Deep Q-learning from Demonstrations" (DQfD),
  AAAI 2018, https://arxiv.org/abs/1704.03732
- Vecerik et al., "Leveraging Demonstrations for Deep Reinforcement Learning
  on Robotics Problems with Sparse Rewards" (DDPGfD),
  arXiv 2017, https://arxiv.org/abs/1707.08817
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from polaris.trainer.expert_dataset import ExpertDataset
from polaris.trainer.ppo_networks import ActorCritic, ActorCriticDiscrete

logger = logging.getLogger(__name__)


@dataclass
class BCConfig:
    """Behavior Cloning 配置。

    Attributes:
        lr: 学习率。
        n_epochs: 训练轮数。
        batch_size: 批量大小。
        loss_type: 损失类型，"mse"（均方误差）或 "nll"（负对数似然，默认）。
        weight_decay: 权重衰减（L2 正则）。
        grad_clip: 梯度裁剪最大范数。
        log_every: 每 N 步打印一次日志。
    """

    lr: float = 1e-3
    n_epochs: int = 50
    batch_size: int = 16
    loss_type: str = "nll"
    weight_decay: float = 1e-5
    grad_clip: float = 1.0
    log_every: int = 10


@dataclass
class EpochStats:
    """单个 epoch 的累计统计（用于减少 _record_epoch 参数个数，规则 7.1）。

    Attributes:
        loss: 累计损失。
        mse: 累计 MSE（连续动作）。
        nll: 累计 NLL（连续动作）。
        acc: 累计准确率（离散动作）。
        n_batches: 批量数。
    """

    loss: float = 0.0
    mse: float = 0.0
    nll: float = 0.0
    acc: float = 0.0
    n_batches: int = 0


@dataclass
class TrainState:
    """BC 预训练单 epoch 的上下文（减少辅助函数参数个数，规则 7.1）。

    Attributes:
        obs_t: 观测张量。
        action_t: 动作张量。
        indices: 样本索引数组（已 shuffle）。
        bs: 批量大小。
        cfg: BC 配置。
    """

    obs_t: torch.Tensor
    action_t: torch.Tensor
    indices: np.ndarray
    bs: int
    cfg: BCConfig


class BehaviorCloning:
    """Behavior Cloning 训练器（连续动作版，适配 ActorCritic）。

    用专家示范数据监督学习 ActorCritic 网络的策略头（action_mean + action_log_std），
    作为 PPO RL 微调的初始化。价值头不参与 BC 训练（PPO 阶段再学习）。

    来源:
    - Pomerleau, NeurIPS 1989, ALVINN
      https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
    - NLL 损失用于高斯策略: Sutton & Barto, Reinforcement Learning: An Introduction
      http://incompleteideas.net/book/RLbook2020.pdf

    Attributes:
        network: ActorCritic 网络（连续动作）。
        config: BC 配置。
        optimizer: Adam 优化器。
        metrics: 训练指标历史。
    """

    def __init__(
        self,
        network: ActorCritic,
        config: BCConfig | None = None,
    ) -> None:
        self.network = network
        self.config = config or BCConfig()
        self.optimizer = optim.Adam(
            network.parameters(),
            lr=self.config.lr,
            weight_decay=self.config.weight_decay,
        )
        self.metrics: list[dict] = []

    def train(self, dataset: ExpertDataset) -> dict:
        """在专家数据集上训练 BC 策略。

        Args:
            dataset: 专家示范数据集。

        Returns:
            最终训练指标 {epoch, loss, mse, nll}。
        """
        obs_all, action_all = dataset.get_all()
        n_samples = len(obs_all)
        if n_samples == 0:
            logger.warning("BC 训练跳过：专家数据集为空")
            return {"epoch": 0, "loss": 0.0, "mse": 0.0, "nll": 0.0}
        obs_t = torch.as_tensor(obs_all, dtype=torch.float32)
        action_t = torch.as_tensor(action_all, dtype=torch.float32)
        last_metrics = {"epoch": 0, "loss": 0.0, "mse": 0.0, "nll": 0.0}
        for epoch in range(self.config.n_epochs):
            indices = np.arange(n_samples)
            np.random.shuffle(indices)
            bs = min(self.config.batch_size, n_samples)
            stats = self._run_epoch(obs_t, action_t, indices, bs)
            last_metrics = self._record_epoch(epoch, stats)
        return last_metrics

    def _run_epoch(
        self,
        obs_t: torch.Tensor,
        action_t: torch.Tensor,
        indices: np.ndarray,
        bs: int,
    ) -> EpochStats:
        """单 epoch 训练，返回累计统计。"""
        stats = EpochStats()
        n_samples = len(obs_t)
        for start in range(0, n_samples, bs):
            end = min(start + bs, n_samples)
            idx = indices[start:end]
            loss, mse, nll = self._update_step(obs_t[idx], action_t[idx])
            stats.loss += loss
            stats.mse += mse
            stats.nll += nll
            stats.n_batches += 1
        return stats

    def _record_epoch(self, epoch: int, stats: EpochStats) -> dict:
        """记录 epoch 指标并打印日志，返回指标字典。"""
        n = max(1, stats.n_batches)
        metrics = {
            "epoch": epoch + 1,
            "loss": stats.loss / n,
            "mse": stats.mse / n,
            "nll": stats.nll / n,
        }
        self.metrics.append(metrics)
        if (epoch + 1) % self.config.log_every == 0:
            logger.info(
                "BC epoch %d/%d | loss %.6f | mse %.6f | nll %.6f",
                epoch + 1,
                self.config.n_epochs,
                metrics["loss"],
                metrics["mse"],
                metrics["nll"],
            )
        return metrics

    def _update_step(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
    ) -> tuple[float, float, float]:
        """单步 BC 更新，返回 (loss, mse, nll) 浮点值。"""
        self.optimizer.zero_grad()
        mean, _ = self.network.forward(obs)
        std = torch.exp(self.network.action_log_std)
        # MSE 损失（回归）
        mse_loss = nn.functional.mse_loss(mean, expert_actions)
        # NLL 损失（高斯负对数似然）
        dist = torch.distributions.Normal(mean, std)
        nll_loss = -dist.log_prob(expert_actions).sum(dim=-1).mean()
        # 总损失
        if self.config.loss_type == "mse":
            loss = mse_loss
        else:
            loss = nll_loss
        loss.backward()
        nn.utils.clip_grad_norm_(self.network.parameters(), self.config.grad_clip)
        self.optimizer.step()
        return float(loss.item()), float(mse_loss.item()), float(nll_loss.item())


class BehaviorCloningDiscrete:
    """Behavior Cloning 训练器（离散动作版，适配 ActorCriticDiscrete）。

    用专家示范数据监督学习 ActorCriticDiscrete 网络的策略头（logits），
    使用交叉熵损失。

    来源:
    - Pomerleau, NeurIPS 1989, ALVINN
      https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
    - 交叉熵损失: Goodfellow et al., Deep Learning, Ch. 6.2.2
      https://www.deeplearningbook.org/

    Attributes:
        network: ActorCriticDiscrete 网络。
        config: BC 配置。
        optimizer: Adam 优化器。
        metrics: 训练指标历史。
    """

    def __init__(
        self,
        network: ActorCriticDiscrete,
        config: BCConfig | None = None,
    ) -> None:
        self.network = network
        self.config = config or BCConfig()
        self.optimizer = optim.Adam(
            network.parameters(),
            lr=self.config.lr,
            weight_decay=self.config.weight_decay,
        )
        self.metrics: list[dict] = []

    def train(
        self,
        obs_all: np.ndarray,
        action_all: np.ndarray,
    ) -> dict:
        """在专家数据集上训练离散 BC 策略。

        Args:
            obs_all: 观测数组 [N, obs_dim]。
            action_all: 离散动作数组 [N] 或 [N, 1]。

        Returns:
            最终训练指标 {epoch, loss, accuracy}。
        """
        n_samples = len(obs_all)
        if n_samples == 0:
            logger.warning("离散 BC 训练跳过：数据集为空")
            return {"epoch": 0, "loss": 0.0, "accuracy": 0.0}
        obs_t = torch.as_tensor(obs_all, dtype=torch.float32)
        action_t = torch.as_tensor(action_all, dtype=torch.long).flatten()
        last_metrics = {"epoch": 0, "loss": 0.0, "accuracy": 0.0}
        for epoch in range(self.config.n_epochs):
            indices = np.arange(n_samples)
            np.random.shuffle(indices)
            bs = min(self.config.batch_size, n_samples)
            stats = self._run_epoch(obs_t, action_t, indices, bs)
            last_metrics = self._record_epoch(epoch, stats)
        return last_metrics

    def _run_epoch(
        self,
        obs_t: torch.Tensor,
        action_t: torch.Tensor,
        indices: np.ndarray,
        bs: int,
    ) -> EpochStats:
        """单 epoch 离散训练，返回累计统计。"""
        stats = EpochStats()
        n_samples = len(obs_t)
        for start in range(0, n_samples, bs):
            end = min(start + bs, n_samples)
            idx = indices[start:end]
            loss, acc = self._update_step(obs_t[idx], action_t[idx])
            stats.loss += loss
            stats.acc += acc
            stats.n_batches += 1
        return stats

    def _record_epoch(self, epoch: int, stats: EpochStats) -> dict:
        """记录 epoch 指标并打印日志，返回指标字典。"""
        n = max(1, stats.n_batches)
        metrics = {
            "epoch": epoch + 1,
            "loss": stats.loss / n,
            "accuracy": stats.acc / n,
        }
        self.metrics.append(metrics)
        if (epoch + 1) % self.config.log_every == 0:
            logger.info(
                "BC(离散) epoch %d/%d | loss %.6f | acc %.4f",
                epoch + 1,
                self.config.n_epochs,
                metrics["loss"],
                metrics["accuracy"],
            )
        return metrics

    def _update_step(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
    ) -> tuple[float, float]:
        """单步离散 BC 更新，返回 (loss, accuracy)。"""
        self.optimizer.zero_grad()
        logits, _ = self.network.forward(obs)
        loss = nn.functional.cross_entropy(logits, expert_actions)
        loss.backward()
        nn.utils.clip_grad_norm_(self.network.parameters(), self.config.grad_clip)
        self.optimizer.step()
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            acc = float((preds == expert_actions).float().mean().item())
        return float(loss.item()), acc


# =============================================================================
# PPOAgent / PPOAgentDiscrete 的 BC 预训练辅助函数
# =============================================================================
#
# 这两个函数封装 PPOAgent.pretrain / PPOAgentDiscrete.pretrain 的训练循环逻辑，
# 从 ppo_torch.py 中抽出以避免该文件超过 500 行有效代码限制（规则 7.1）。
# 通过 agent.bc_update() 调用 PPO 网络的 BC 更新接口，保持解耦。


def _run_bc_pretrain_continuous(
    agent,
    expert_obs: np.ndarray,
    expert_actions: np.ndarray,
    config: BCConfig | None = None,
) -> list[dict]:
    """连续动作 PPOAgent 的 BC 预训练循环。

    通过 agent.bc_update() 在专家数据上监督学习策略网络，
    作为 PPO RL 微调的初始化。

    Args:
        agent: PPOAgent 实例（需提供 bc_update 方法）。
        expert_obs: 专家观测数组 [N, obs_dim]。
        expert_actions: 专家动作数组 [N, action_dim]。
        config: BC 训练配置（None 用默认 BCConfig）。

    Returns:
        每个 epoch 的指标字典列表。
    """
    cfg = config or BCConfig()
    n_samples = len(expert_obs)
    if n_samples == 0:
        logger.warning("BC 预训练跳过：专家数据集为空")
        return [{"epoch": 0, "loss": 0.0, "mse": 0.0, "nll": 0.0}]
    obs_t = torch.as_tensor(expert_obs, dtype=torch.float32)
    action_t = torch.as_tensor(expert_actions, dtype=torch.float32)
    history: list[dict] = []
    bs = min(cfg.batch_size, n_samples)
    for epoch in range(cfg.n_epochs):
        indices = np.arange(n_samples)
        np.random.shuffle(indices)
        state = TrainState(obs_t, action_t, indices, bs, cfg)
        stats = _run_continuous_epoch(agent, state)
        history.append(_make_continuous_metrics(epoch, stats))
        _log_continuous_epoch(epoch, cfg, stats)
    return history


def _log_continuous_epoch(epoch: int, cfg: BCConfig, stats: EpochStats) -> None:
    """打印连续动作 BC epoch 日志。"""
    if (epoch + 1) % cfg.log_every == 0:
        logger.info(
            "BC预训练 epoch %d/%d | loss %.6f | mse %.6f | nll %.6f",
            epoch + 1,
            cfg.n_epochs,
            stats.loss / stats.n_batches,
            stats.mse / stats.n_batches,
            stats.nll / stats.n_batches,
        )


def _run_continuous_epoch(agent, state: TrainState) -> EpochStats:
    """单 epoch 连续动作 BC 训练，返回累计统计。"""
    stats = EpochStats()
    n_samples = len(state.obs_t)
    for start in range(0, n_samples, state.bs):
        end = min(start + state.bs, n_samples)
        idx = state.indices[start:end]
        m = agent.bc_update(
            state.obs_t[idx],
            state.action_t[idx],
            loss_type=state.cfg.loss_type,
            grad_clip=state.cfg.grad_clip,
        )
        stats.loss += m["loss"]
        stats.mse += m["mse"]
        stats.nll += m["nll"]
        stats.n_batches += 1
    return stats


def _make_continuous_metrics(epoch: int, stats: EpochStats) -> dict:
    """根据累计统计生成 epoch 指标字典。"""
    n = max(1, stats.n_batches)
    return {
        "epoch": epoch + 1,
        "loss": stats.loss / n,
        "mse": stats.mse / n,
        "nll": stats.nll / n,
    }


def _run_bc_pretrain_discrete(
    agent,
    expert_obs: np.ndarray,
    expert_actions: np.ndarray,
    config: BCConfig | None = None,
) -> list[dict]:
    """离散动作 PPOAgentDiscrete 的 BC 预训练循环。

    通过 agent.bc_update() 在专家数据上监督学习策略网络，
    作为 PPO RL 微调的初始化。

    Args:
        agent: PPOAgentDiscrete 实例（需提供 bc_update 方法）。
        expert_obs: 专家观测数组 [N, obs_dim]。
        expert_actions: 专家离散动作数组 [N] 或 [N, 1]。
        config: BC 训练配置（None 用默认 BCConfig）。

    Returns:
        每个 epoch 的指标字典列表。
    """
    cfg = config or BCConfig()
    n_samples = len(expert_obs)
    if n_samples == 0:
        logger.warning("BC 预训练跳过：专家数据集为空")
        return [{"epoch": 0, "loss": 0.0, "accuracy": 0.0}]
    obs_t = torch.as_tensor(expert_obs, dtype=torch.float32)
    action_t = torch.as_tensor(expert_actions, dtype=torch.long).flatten()
    history: list[dict] = []
    bs = min(cfg.batch_size, n_samples)
    for epoch in range(cfg.n_epochs):
        indices = np.arange(n_samples)
        np.random.shuffle(indices)
        state = TrainState(obs_t, action_t, indices, bs, cfg)
        stats = _run_discrete_epoch(agent, state)
        history.append(_make_discrete_metrics(epoch, stats))
        _log_discrete_epoch(epoch, cfg, stats)
    return history


def _log_discrete_epoch(epoch: int, cfg: BCConfig, stats: EpochStats) -> None:
    """打印离散动作 BC epoch 日志。"""
    if (epoch + 1) % cfg.log_every == 0:
        logger.info(
            "BC预训练(离散) epoch %d/%d | loss %.6f | acc %.4f",
            epoch + 1,
            cfg.n_epochs,
            stats.loss / stats.n_batches,
            stats.acc / stats.n_batches,
        )


def _run_discrete_epoch(agent, state: TrainState) -> EpochStats:
    """单 epoch 离散动作 BC 训练，返回累计统计。"""
    stats = EpochStats()
    n_samples = len(state.obs_t)
    for start in range(0, n_samples, state.bs):
        end = min(start + state.bs, n_samples)
        idx = state.indices[start:end]
        m = agent.bc_update(
            state.obs_t[idx],
            state.action_t[idx],
            grad_clip=state.cfg.grad_clip,
        )
        stats.loss += m["loss"]
        stats.acc += m["accuracy"]
        stats.n_batches += 1
    return stats


def _make_discrete_metrics(epoch: int, stats: EpochStats) -> dict:
    """根据累计统计生成离散 epoch 指标字典。"""
    n = max(1, stats.n_batches)
    return {
        "epoch": epoch + 1,
        "loss": stats.loss / n,
        "accuracy": stats.acc / n,
    }


__all__ = [
    "BCConfig",
    "BehaviorCloning",
    "BehaviorCloningDiscrete",
    "EpochStats",
]
