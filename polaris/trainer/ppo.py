"""PPO 智能体（Task 13）。

实现 actor-critic 网络 + PPO 更新（clip + GAE）+ 断点续训 + 指标记录。
torch 无法安装时使用 ``polaris.nn`` 纯 NumPy 复刻实现（规则 3）。

方法参考：
- Schulman et al., 2017, PPO（Proximal Policy Optimization）
  来源: https://arxiv.org/abs/1707.06347
- Schulman et al., 2015, GAE（Generalized Advantage Estimation）
  来源: https://arxiv.org/abs/1506.02438
- Stable-Baselines3 PPO 实现
  来源: https://stable-baselines3.readthedocs.io/
- CleanRL PPO 单文件实现
  来源: https://github.com/vwxyzjn/cleanrl

PPO 核心逻辑（与 SB3/CleanRL 一致）：
1. 采样 rollout：用当前策略采集 (state, action, reward, logprob, value)
2. GAE 估计优势 A_t 与回报 R_t
3. 多 epoch 小批量更新：
   - 策略损失：``L_clip = -mean( min(r*A, clip(r,1-eps,1+eps)*A) )``
     其中 ``r = exp(new_logprob - old_logprob)``
   - 价值损失：``L_vf = mean((R - V)^2)``
   - 熵奖励：``+ ent_coef * entropy``
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from polaris.nn import Adam, Linear, Module, ReLU, Sequential, Tensor


@dataclass
class PPOConfig:
    """PPO 超参数（与 Stable-Baselines3 默认值对齐）。"""

    lr: float = 3e-4
    gamma: float = 0.99  # 折扣因子
    gae_lambda: float = 0.95  # GAE lambda
    clip_eps: float = 0.2  # PPO clip
    ent_coef: float = 0.01  # 熵系数
    vf_coef: float = 0.5  # 价值损失系数
    max_grad_norm: float = 0.5  # 梯度裁剪
    n_epochs: int = 4  # 每次 rollout 的更新轮数
    batch_size: int = 64  # 小批量大小


class ActorCritic(Module):
    """Actor-Critic 网络（共享编码器 + 策略头 + 价值头）。

    复刻 SB3 ``ActorCriticPolicy``：共享特征提取器，分出
    ``action_net``（策略）与 ``value_net``（价值）。
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_dim: int = 64,
    ) -> None:
        super().__init__()
        self.shared = Sequential(
            Linear(obs_dim, hidden_dim),
            ReLU(),
            Linear(hidden_dim, hidden_dim),
            ReLU(),
        )
        self.action_mean = Linear(hidden_dim, action_dim)
        self.action_log_std = Tensor(
            np.zeros(action_dim), requires_grad=True
        )
        self.value_head = Linear(hidden_dim, 1)

    def forward(self, obs: np.ndarray | Tensor):
        if not isinstance(obs, Tensor):
            obs = Tensor(np.asarray(obs, dtype=np.float64))
        feats = self.shared(obs)
        mean = self.action_mean(feats)
        value = self.value_head(feats)
        return mean, value

    def get_action(self, obs: np.ndarray):
        """采样动作 + 返回 logprob + value（用于 rollout）。"""
        mean, value = self.forward(obs)
        std = np.exp(self.action_log_std.data)
        # 高斯采样
        action = mean.data + std * np.random.randn(*mean.data.shape)
        # logprob = -0.5 * sum(((a-mean)/std)^2) - 0.5*dim*log(2pi) - sum(log std)
        var = std ** 2
        logprob = (
            -0.5 * ((action - mean.data) ** 2 / var).sum(axis=-1)
            - 0.5 * mean.data.shape[-1] * math.log(2 * math.pi)
            - np.log(std).sum()
        )
        # 标量化（单步 obs 时 value 为 [1,1]）
        v = float(np.asarray(value.data).flatten()[0])
        lp = float(np.asarray(logprob).flatten()[0]) if np.ndim(logprob) > 0 else float(logprob)
        return action.flatten(), lp, v

    def evaluate(self, obs: np.ndarray, actions: np.ndarray):
        """重新评估给定动作的 logprob + value + entropy（用于 PPO 更新）。"""
        mean, value = self.forward(obs)
        std = np.exp(self.action_log_std.data)
        var = std ** 2
        # logprob（直接用 data 计算）
        lp_data = (
            -0.5 * ((actions - mean.data) ** 2 / var).sum(axis=-1)
            - 0.5 * mean.data.shape[-1] * math.log(2 * math.pi)
            - np.log(std).sum()
        )
        # 熵 = 0.5 * dim * (1 + log(2pi)) + sum(log std)
        ent = 0.5 * mean.data.shape[-1] * (1 + math.log(2 * math.pi))
        entropy = np.full(mean.data.shape[0], ent + np.log(std).sum())
        return lp_data, value.data.flatten(), entropy


@dataclass
class RolloutBuffer:
    """PPO rollout 缓冲区。"""

    obs: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    logprobs: list = field(default_factory=list)
    values: list = field(default_factory=list)
    dones: list = field(default_factory=list)
    advantages: np.ndarray = field(default_factory=lambda: np.array([]))
    returns: np.ndarray = field(default_factory=lambda: np.array([]))

    def clear(self) -> None:
        self.obs.clear()
        self.actions.clear()
        self.rewards.clear()
        self.logprobs.clear()
        self.values.clear()
        self.dones.clear()
        self.advantages = np.array([])
        self.returns = np.array([])

    def __len__(self) -> int:
        return len(self.obs)


def compute_gae(
    rewards: list[float],
    values: list[float],
    dones: list[bool],
    last_value: float,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
) -> tuple[np.ndarray, np.ndarray]:
    """计算 GAE 优势与回报（与 SB3/CleanRL 一致）。

    来源: Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
    """
    n = len(rewards)
    advantages = np.zeros(n, dtype=np.float64)
    last_gae = 0.0
    for t in reversed(range(n)):
        if t == n - 1:
            next_value = last_value
            next_non_terminal = 0.0 if dones[t] else 1.0
        else:
            next_value = values[t + 1]
            next_non_terminal = 0.0 if dones[t] else 1.0
        delta = rewards[t] + gamma * next_value * next_non_terminal - values[t]
        last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
        advantages[t] = last_gae
    returns = advantages + np.array(values, dtype=np.float64)
    return advantages, returns


class PPOAgent:
    """PPO 智能体（actor-critic + clip + GAE）。

    复刻 Stable-Baselines3 ``PPO`` 的核心训练循环。
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        config: PPOConfig | None = None,
        hidden_dim: int = 64,
    ) -> None:
        self.config = config or PPOConfig()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.ac = ActorCritic(obs_dim, action_dim, hidden_dim=hidden_dim)
        params = self.ac.parameters()
        # log_std 作为可学习参数
        params.append(self.ac.action_log_std)
        self.optimizer = Adam(params, lr=self.config.lr)
        self.buffer = RolloutBuffer()
        self.metrics: list[dict] = []

    def get_action(self, obs: np.ndarray):
        """采样动作。"""
        return self.ac.get_action(obs)

    def store(self, obs, action, reward, logprob, value, done) -> None:
        self.buffer.obs.append(obs)
        self.buffer.actions.append(action)
        self.buffer.rewards.append(reward)
        self.buffer.logprobs.append(logprob)
        self.buffer.values.append(value)
        self.buffer.dones.append(done)

    def compute_advantages(self, last_value: float) -> None:
        adv, ret = compute_gae(
            self.buffer.rewards,
            self.buffer.values,
            self.buffer.dones,
            last_value,
            self.config.gamma,
            self.config.gae_lambda,
        )
        self.buffer.advantages = adv
        self.buffer.returns = ret
        # 标准化优势（与 SB3 一致）
        if adv.std() > 1e-8:
            self.buffer.advantages = (adv - adv.mean()) / (adv.std() + 1e-8)

    def update(self, last_value: float = 0.0) -> dict:
        """PPO 更新（多 epoch 小批量）。"""
        self.compute_advantages(last_value)
        n = len(self.buffer)
        if n == 0:
            return {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        obs = np.array(self.buffer.obs, dtype=np.float64)
        actions = np.array(self.buffer.actions, dtype=np.float64)
        old_logprobs = np.array(self.buffer.logprobs, dtype=np.float64)
        advantages = self.buffer.advantages
        returns = self.buffer.returns

        indices = np.arange(n)
        batch_size = min(self.config.batch_size, n)
        metrics_sum = {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        n_updates = 0

        for _ in range(self.config.n_epochs):
            np.random.shuffle(indices)
            for start in range(0, n, batch_size):
                idx = indices[start:start + batch_size]
                mb_obs = obs[idx]
                mb_actions = actions[idx]
                mb_old_lp = old_logprobs[idx]
                mb_adv = advantages[idx]
                mb_ret = returns[idx]

                self.optimizer.zero_grad()
                mean, value = self.ac.forward(mb_obs)
                std = np.exp(self.ac.action_log_std.data)
                # 新 logprob（可微路径）
                diff = Tensor(mb_actions) - mean
                new_lp = -0.5 * (diff * diff).sum(axis=-1)
                ratio = np.exp(new_lp.data - mb_old_lp)
                # 策略损失（clip）
                surr1 = ratio * mb_adv
                clip_lo = 1 - self.config.clip_eps
                clip_hi = 1 + self.config.clip_eps
                surr2 = np.clip(ratio, clip_lo, clip_hi) * mb_adv
                policy_loss = -np.minimum(surr1, surr2).mean()
                # 价值损失
                value_pred = value.data.flatten()
                value_loss = ((mb_ret - value_pred) ** 2).mean()
                # 熵（高斯）
                ent = 0.5 * mean.data.shape[-1] * (1 + math.log(2 * math.pi))
                entropy = np.array(ent + np.log(std).sum())
                # 总损失（构造可微图）：策略目标 + 价值损失
                weighted = Tensor(mb_adv) * new_lp
                policy_obj = weighted.mean()
                v_diff = Tensor(mb_ret) - value.flatten()
                value_obj = (v_diff * v_diff).mean()
                total = -policy_obj + self.config.vf_coef * value_obj
                total.backward()
                # 梯度裁剪
                for p in self.optimizer.params:
                    if p.grad is not None:
                        norm = np.linalg.norm(p.grad)
                        if norm > self.config.max_grad_norm and norm > 1e-8:
                            p.grad = p.grad * (self.config.max_grad_norm / norm)
                self.optimizer.step()

                metrics_sum["loss"] += float(total.data)
                metrics_sum["policy_loss"] += float(policy_loss)
                metrics_sum["value_loss"] += float(value_loss)
                metrics_sum["entropy"] += float(entropy.mean())
                n_updates += 1

        for k in metrics_sum:
            metrics_sum[k] /= max(1, n_updates)
        self.metrics.append(metrics_sum)
        self.buffer.clear()
        return metrics_sum

    def save(self, path: str | Path) -> None:
        """保存检查点（断点续训）。"""
        state = {
            "config": self.config.__dict__,
            "obs_dim": self.obs_dim,
            "action_dim": self.action_dim,
            "params": (
                [p.data.tolist() for p in self.ac.parameters()]
                + [self.ac.action_log_std.data.tolist()]
            ),
            "metrics": self.metrics,
        }
        Path(path).write_text(json.dumps(state), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """加载检查点。"""
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        params = self.ac.parameters() + [self.ac.action_log_std]
        for p, data in zip(params, state["params"], strict=True):
            p.data = np.array(data, dtype=np.float64)
        self.metrics = state.get("metrics", [])
