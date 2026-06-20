"""PPO Actor-Critic 网络 — PyTorch 实现。

从 ``ppo_torch.py`` 拆分而来，降低单文件规模（规则 4.1）。

来源:
- Engstrom et al., 2020, Implementation Matters in PPO
  https://arxiv.org/abs/2005.12729
- SB3 网络初始化: https://stable-baselines3.readthedocs.io/
- CleanRL discrete PPO: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


class ActorCritic(nn.Module):
    """Actor-Critic 网络（共享编码器 + 策略头 + 价值头）。

    复刻 SB3 ``ActorCriticPolicy``：共享特征提取器，分出
    ``action_net``（策略）与 ``value_net``（价值）。
    使用 orthogonal 初始化（与 SB3/CleanRL 一致）。

    来源:
    - Engstrom et al., 2020, Implementation Matters in PPO
      https://arxiv.org/abs/2005.12729
    - SB3 网络初始化: https://stable-baselines3.readthedocs.io/
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_dim: int = 64,
    ) -> None:
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.action_mean = nn.Linear(hidden_dim, action_dim)
        self.action_log_std = nn.Parameter(torch.zeros(action_dim))
        self.value_head = nn.Linear(hidden_dim, 1)
        # Orthogonal 初始化（与 SB3/CleanRL 一致）
        self._init_weights()

    def _init_weights(self) -> None:
        """Orthogonal 初始化所有线性层。"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0.0)
        # 策略头用较小 gain（SB3 默认 0.01）
        nn.init.orthogonal_(self.action_mean.weight, gain=0.01)
        nn.init.constant_(self.action_mean.bias, 0.0)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """前向传播，返回 (action_mean, value)。"""
        feats = self.shared(obs)
        mean = self.action_mean(feats)
        value = self.value_head(feats)
        return mean, value

    def get_action(self, obs_np: np.ndarray) -> tuple[np.ndarray, float, float]:
        """采样动作 + 返回 logprob + value（用于 rollout）。

        Args:
            obs_np: numpy 观测数组。

        Returns:
            (action_numpy, logprob_float, value_float)
        """
        obs_t = torch.as_tensor(obs_np, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            mean, value = self.forward(obs_t)
            std = torch.exp(self.action_log_std)
            dist = torch.distributions.Normal(mean, std)
            action = dist.sample()
            logprob = dist.log_prob(action).sum(dim=-1)
        action_np = action.cpu().numpy().flatten()
        lp = float(logprob.item())
        v = float(value.item())
        return action_np, lp, v

    def evaluate(
        self, obs: torch.Tensor, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """重新评估给定动作的 logprob + value + entropy（用于 PPO 更新）。

        Args:
            obs: 观测张量 (batch, obs_dim)。
            actions: 动作张量 (batch, action_dim)。

        Returns:
            (logprob, value, entropy) 均为张量。
        """
        mean, value = self.forward(obs)
        std = torch.exp(self.action_log_std)
        dist = torch.distributions.Normal(mean, std)
        logprob = dist.log_prob(actions).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        return logprob, value.squeeze(-1), entropy

    def bc_loss(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
        loss_type: str = "nll",
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """计算 Behavior Cloning 损失（连续动作）。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

        Args:
            obs: 观测张量 (batch, obs_dim)。
            expert_actions: 专家动作张量 (batch, action_dim)。
            loss_type: "nll"（负对数似然，默认）或 "mse"（均方误差）。

        Returns:
            (total_loss, mse_loss) 张量。
        """
        mean, _ = self.forward(obs)
        mse_loss = nn.functional.mse_loss(mean, expert_actions)
        if loss_type == "mse":
            return mse_loss, mse_loss
        std = torch.exp(self.action_log_std)
        dist = torch.distributions.Normal(mean, std)
        nll_loss = -dist.log_prob(expert_actions).sum(dim=-1).mean()
        return nll_loss, mse_loss


class ActorCriticDiscrete(nn.Module):
    """离散动作空间的 Actor-Critic 网络（用于 MultiDiscrete 环境）。

    将 MultiDiscrete 动作展平为单个 Categorical 分布。
    例如 MultiDiscrete([10,10,4]) → 400 个离散动作。

    来源:
    - SB3 MultiInputPolicy: https://stable-baselines3.readthedocs.io/
    - CleanRL discrete PPO: https://github.com/vwxyzjn/cleanrl
    """

    def __init__(self, obs_dim: int, n_actions: int, hidden_dim: int = 128):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.action_logits = nn.Linear(hidden_dim, n_actions)
        self.value_head = nn.Linear(hidden_dim, 1)
        self.n_actions = n_actions
        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0.0)
        nn.init.orthogonal_(self.action_logits.weight, gain=0.01)
        nn.init.constant_(self.action_logits.bias, 0.0)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        feats = self.shared(obs)
        logits = self.action_logits(feats)
        value = self.value_head(feats)
        return logits, value

    def get_action(self, obs_np: np.ndarray) -> tuple[int, float, float]:
        obs_t = torch.as_tensor(obs_np, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            logits, value = self.forward(obs_t)
            dist = torch.distributions.Categorical(logits=logits)
            action = dist.sample()
            logprob = dist.log_prob(action)
        return int(action.item()), float(logprob.item()), float(value.item())

    def evaluate(
        self, obs: torch.Tensor, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(obs)
        dist = torch.distributions.Categorical(logits=logits)
        logprob = dist.log_prob(actions.squeeze(-1))
        entropy = dist.entropy()
        return logprob, value.squeeze(-1), entropy

    def bc_loss(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """计算 Behavior Cloning 损失（离散动作，交叉熵）。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

        Args:
            obs: 观测张量 (batch, obs_dim)。
            expert_actions: 专家离散动作张量 (batch,) 或 (batch, 1)。

        Returns:
            (cross_entropy_loss, accuracy) 张量。
        """
        logits, _ = self.forward(obs)
        target = expert_actions.squeeze(-1).long()
        ce_loss = nn.functional.cross_entropy(logits, target)
        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            acc = (preds == target).float().mean()
        return ce_loss, acc


__all__ = ["ActorCritic", "ActorCriticDiscrete"]
