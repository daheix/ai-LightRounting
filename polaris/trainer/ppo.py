"""PPO 智能体（Task 13）。

实现 actor-critic 网络 + PPO 更新（clip + GAE）+ 断点续训 + 指标记录。
使用 ``polaris.nn`` 纯 NumPy 复刻实现（规则 3），不依赖 torch。

方法参考（来源 URL）：
- Schulman et al., 2017, PPO（Proximal Policy Optimization）
  来源: https://arxiv.org/abs/1707.06347
- Schulman et al., 2015, GAE（Generalized Advantage Estimation）
  来源: https://arxiv.org/abs/1506.02438
- Stable-Baselines3 PPO 实现
  来源: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
- CleanRL PPO 单文件实现（离散动作空间）
  来源: https://docs.cleanrl.dev/rl-algorithms/ppo/#ppopy
  来源: https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/ppo.py

PPO 核心逻辑（与 SB3/CleanRL 一致）：
1. 采样 rollout：用当前策略采集 (state, action, reward, logprob, value)
2. GAE 估计优势 A_t 与回报 R_t
3. 多 epoch 小批量更新：
   - 策略损失：``L_clip = -mean( min(r*A, clip(r,1-eps,1+eps)*A) )``
     其中 ``r = exp(new_logprob - old_logprob)``
   - 价值损失：``L_vf = mean((R - V)^2)``
   - 熵奖励：``+ ent_coef * entropy``
   - 总损失：``L = -min(r*adv, clipped*adv) + c1*value_loss - c2*entropy``
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from polaris.nn import Adam, Linear, Module, Sequential, Tanh, Tensor


# ---------------------------------------------------------------------------
# PPOConfig（与 Stable-Baselines3 默认值对齐，保留用于 train_loop 兼容）
# ---------------------------------------------------------------------------
@dataclass
class PPOConfig:
    """PPO 超参数（与 Stable-Baselines3 默认值对齐）。

    来源: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
    """

    lr: float = 3e-4
    gamma: float = 0.99  # 折扣因子
    gae_lambda: float = 0.95  # GAE lambda
    clip_eps: float = 0.2  # PPO clip
    ent_coef: float = 0.01  # 熵系数
    vf_coef: float = 0.5  # 价值损失系数
    max_grad_norm: float = 0.5  # 梯度裁剪
    n_epochs: int = 4  # 每次 rollout 的更新轮数
    batch_size: int = 64  # 小批量大小


# ---------------------------------------------------------------------------
# ActorCritic 网络（离散动作空间，复刻 CleanRL ppo.py Agent）
# ---------------------------------------------------------------------------
class ActorCritic(Module):
    """Actor-Critic 网络（共享编码器 + 策略头 + 价值头）。

    离散动作空间：actor 输出 logits，经 softmax 得到 Categorical 分布。
    复刻 CleanRL ``ppo.py`` 的 ``Agent``（共享 MLP 主干 + 分离头）。

    来源: https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/ppo.py
    """

    def __init__(
        self,
        state_dim: int,
        hidden_dim: int,
        action_dim: int,
    ) -> None:
        super().__init__()
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.action_dim = action_dim
        # 共享特征提取器（与 CleanRL/SB3 一致：Tanh 激活 + 2 层 MLP）
        self.shared = Sequential(
            Linear(state_dim, hidden_dim),
            Tanh(),
            Linear(hidden_dim, hidden_dim),
            Tanh(),
        )
        # actor: 输出动作 logits（pre-softmax）
        self.actor = Linear(hidden_dim, action_dim)
        # critic: 输出状态价值（标量）
        self.critic = Linear(hidden_dim, 1)

    def forward(self, state: np.ndarray | Tensor) -> tuple[Tensor, Tensor]:
        """前向传播。

        Args:
            state: 状态向量 ``[state_dim]`` 或 ``[batch, state_dim]``。

        Returns:
            (action_logits, value)：logits ``[batch, action_dim]``，
            value ``[batch, 1]``。
        """
        if not isinstance(state, Tensor):
            state = Tensor(np.asarray(state, dtype=np.float64))
        # 确保 2D（单步状态自动加 batch 维）
        if state.data.ndim == 1:
            state = Tensor(state.data.reshape(1, -1))
        feats = self.shared(state)
        action_logits = self.actor(feats)
        value = self.critic(feats)
        return action_logits, value

    def get_action(self, state: np.ndarray) -> tuple[int, float, float]:
        """采样动作并返回 (action, log_prob, value)。

        从 Categorical(logits) 分布中采样，用于 rollout 采集。

        Args:
            state: 单步状态向量 ``[state_dim]``。

        Returns:
            (action, log_prob, value)：离散动作索引、对数概率、状态价值。
        """
        logits, value = self.forward(state)
        logits_data = logits.data  # [1, action_dim]
        # 数值稳定的 softmax
        shifted = logits_data - logits_data.max(axis=-1, keepdims=True)
        exp = np.exp(shifted)
        probs = exp / exp.sum(axis=-1, keepdims=True)  # [1, action_dim]
        # 从 Categorical 分布采样
        action = int(np.random.choice(self.action_dim, p=probs[0]))
        log_prob = float(np.log(probs[0, action] + 1e-12))
        v = float(value.data.flatten()[0])
        return action, log_prob, v

    def evaluate(
        self,
        states: np.ndarray,
        actions: np.ndarray,
    ) -> tuple[Tensor, Tensor, Tensor]:
        """评估旧动作（返回 log_probs, values, entropy）。

        重新前向计算给定状态的 logits 与 value，然后计算给定动作的
        log_prob、value 和熵。返回可微 Tensor，用于 PPO 更新反向传播。

        Args:
            states: 状态批次 ``[batch, state_dim]``。
            actions: 动作批次 ``[batch]``（整数索引）。

        Returns:
            (log_probs, values, entropy)：均为可微 Tensor ``[batch]``。
        """
        logits, value = self.forward(states)
        # softmax → 概率（可微）
        probs = logits.softmax(axis=-1)  # [batch, action_dim]
        log_probs_all = probs.log()  # [batch, action_dim]
        # one-hot 编码动作，用于 gather log_prob
        batch = logits.data.shape[0]
        one_hot = np.zeros((batch, self.action_dim), dtype=np.float64)
        one_hot[np.arange(batch), actions] = 1.0
        # log_prob = sum(one_hot * log_probs_all, axis=-1)  [batch]
        log_probs = (Tensor(one_hot) * log_probs_all).sum(axis=-1)
        # values [batch]
        values = value.flatten()
        # 熵 = -sum(p * log(p), axis=-1)  [batch]
        entropy = -(probs * log_probs_all).sum(axis=-1)
        return log_probs, values, entropy


# ---------------------------------------------------------------------------
# GAE（广义优势估计）
# ---------------------------------------------------------------------------
def compute_gae(
    rewards: list[float] | np.ndarray,
    values: list[float] | np.ndarray,
    dones: list[bool] | np.ndarray,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
) -> list[float]:
    """计算广义优势估计（GAE）。

    与 Schulman et al., 2015 和 SB3/CleanRL 实现一致。
    最后一步的 bootstrap value 默认为 0.0（假设 episode 终止）。

    来源: https://arxiv.org/abs/1506.02438
    来源: https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/ppo.py

    Args:
        rewards: 每步奖励 ``[T]``。
        values: 每步状态价值估计 ``[T]``。
        dones: 每步是否终止 ``[T]``。
        gamma: 折扣因子。
        gae_lambda: GAE lambda。

    Returns:
        优势列表 ``[T]``。
    """
    rewards = list(rewards)
    values = list(values)
    dones = list(dones)
    n = len(rewards)
    advantages: list[float] = [0.0] * n
    last_gae = 0.0
    for t in reversed(range(n)):
        if t == n - 1:
            next_value = 0.0  # bootstrap value = 0（episode 终止）
            next_non_terminal = 0.0 if dones[t] else 1.0
        else:
            next_value = values[t + 1]
            next_non_terminal = 0.0 if dones[t] else 1.0
        delta = rewards[t] + gamma * next_value * next_non_terminal - values[t]
        last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
        advantages[t] = last_gae
    return advantages


# ---------------------------------------------------------------------------
# RolloutBuffer（经验回放缓冲区）
# ---------------------------------------------------------------------------
class RolloutBuffer:
    """PPO 经验回放缓冲区。

    存储 rollout 采集的 (state, action, reward, log_prob, value, done)，
    ``get()`` 返回 numpy 数组字典供 PPO 更新使用。
    """

    def __init__(self) -> None:
        self.states: list[np.ndarray] = []
        self.actions: list[int] = []
        self.rewards: list[float] = []
        self.log_probs: list[float] = []
        self.values: list[float] = []
        self.dones: list[bool] = []

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        log_prob: float,
        value: float,
        done: bool,
    ) -> None:
        """添加一条转移。"""
        self.states.append(np.asarray(state, dtype=np.float64))
        self.actions.append(int(action))
        self.rewards.append(float(reward))
        self.log_probs.append(float(log_prob))
        self.values.append(float(value))
        self.dones.append(bool(done))

    def get(self) -> dict[str, np.ndarray]:
        """返回所有数据为 numpy 数组字典。

        Returns:
            包含 states, actions, rewards, log_probs, values, dones 的字典。
        """
        return {
            "states": np.array(self.states, dtype=np.float64),
            "actions": np.array(self.actions, dtype=np.int64),
            "rewards": np.array(self.rewards, dtype=np.float64),
            "log_probs": np.array(self.log_probs, dtype=np.float64),
            "values": np.array(self.values, dtype=np.float64),
            "dones": np.array(self.dones, dtype=bool),
        }

    def clear(self) -> None:
        """清空缓冲区。"""
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.log_probs.clear()
        self.values.clear()
        self.dones.clear()

    def __len__(self) -> int:
        return len(self.states)


# ---------------------------------------------------------------------------
# PPOAgent（PPO 强化学习智能体）
# ---------------------------------------------------------------------------
class PPOAgent:
    """PPO 强化学习智能体（actor-critic + clip + GAE）。

    复刻 Stable-Baselines3 ``PPO`` 与 CleanRL ``ppo.py`` 的核心训练循环。

    来源: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
    来源: https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/ppo.py
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 3e-4,
        gamma: float = 0.99,
        clip_epsilon: float = 0.2,
        gae_lambda: float = 0.95,
        epochs: int = 10,
        batch_size: int = 64,
        hidden_dim: int = 64,
        ent_coef: float = 0.01,
        vf_coef: float = 0.5,
        max_grad_norm: float = 0.5,
    ) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        self.gae_lambda = gae_lambda
        self.epochs = epochs
        self.batch_size = batch_size
        self.ent_coef = ent_coef
        self.vf_coef = vf_coef
        self.max_grad_norm = max_grad_norm

        # Actor-Critic 网络
        self.ac = ActorCritic(state_dim, hidden_dim, action_dim)
        # 优化器（收集所有可学习参数）
        self.optimizer = Adam(self.ac.parameters(), lr=lr)
        # 经验回放缓冲区
        self.buffer = RolloutBuffer()
        # 训练指标历史
        self.metrics: list[dict[str, float]] = []

    def select_action(self, state: np.ndarray) -> int:
        """选择动作（推理模式）。

        贪心选择 logits 最大的动作，用于推理/评估（不采样、不记录梯度）。

        Args:
            state: 状态向量 ``[state_dim]``。

        Returns:
            离散动作索引。
        """
        logits, _ = self.ac.forward(state)
        return int(np.argmax(logits.data, axis=-1).flatten()[0])

    def update(self, trajectories: dict[str, np.ndarray]) -> dict[str, float]:
        """PPO 更新（多 epoch 小批量）。

        Args:
            trajectories: ``RolloutBuffer.get()`` 返回的字典，包含
                states, actions, rewards, log_probs, values, dones。

        Returns:
            训练指标字典（loss, policy_loss, value_loss, entropy）。
        """
        states = trajectories["states"]
        actions = trajectories["actions"]
        rewards = trajectories["rewards"]
        old_log_probs = trajectories["log_probs"]
        values = trajectories["values"]
        dones = trajectories["dones"]

        n = len(states)
        if n == 0:
            return {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        # GAE 优势估计
        advantages = np.array(
            compute_gae(rewards, values, dones, self.gamma, self.gae_lambda),
            dtype=np.float64,
        )
        # 回报 = 优势 + 价值
        returns = advantages + values
        # 标准化优势（与 SB3/CleanRL 一致）
        if advantages.std() > 1e-8:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        indices = np.arange(n)
        batch_size = min(self.batch_size, n)
        metrics_sum: dict[str, float] = {
            "loss": 0.0,
            "policy_loss": 0.0,
            "value_loss": 0.0,
            "entropy": 0.0,
        }
        n_updates = 0

        for _ in range(self.epochs):
            np.random.shuffle(indices)
            for start in range(0, n, batch_size):
                idx = indices[start : start + batch_size]
                mb_states = states[idx]
                mb_actions = actions[idx]
                mb_old_lp = old_log_probs[idx]
                mb_adv = advantages[idx]
                mb_ret = returns[idx]

                self.optimizer.zero_grad()

                # 评估旧动作（可微 Tensor）
                new_log_probs, value_pred, entropy = self.ac.evaluate(
                    mb_states, mb_actions
                )

                # 概率比 ratio = exp(new_log_prob - old_log_prob)
                ratio = (new_log_probs - Tensor(mb_old_lp)).exp()

                # 策略裁剪目标
                surr1 = ratio * Tensor(mb_adv)  # 可微
                # surr2 用 numpy 计算（裁剪后无梯度）
                ratio_data = ratio.data
                clip_lo = 1.0 - self.clip_epsilon
                clip_hi = 1.0 + self.clip_epsilon
                surr2_data = np.clip(ratio_data, clip_lo, clip_hi) * mb_adv
                # min 选择掩码：surr1 <= surr2 时梯度流经 surr1，否则为 0
                # （裁剪阻断梯度，与 CleanRL torch.clamp 行为一致）
                mask = (surr1.data <= surr2_data).astype(np.float64)
                policy_obj = (Tensor(mask) * surr1).mean()

                # 价值损失（MSE，可微）
                v_diff = Tensor(mb_ret) - value_pred
                value_loss = (v_diff * v_diff).mean()

                # 熵（可微，鼓励探索）
                entropy_mean = entropy.mean()

                # 总损失：L = -policy_obj + c1*value_loss - c2*entropy
                total_loss = (
                    -policy_obj
                    + self.vf_coef * value_loss
                    - self.ent_coef * entropy_mean
                )
                total_loss.backward()

                # 梯度裁剪（与 SB3/CleanRL 一致）
                for p in self.optimizer.params:
                    if p.grad is not None:
                        norm = np.linalg.norm(p.grad)
                        if norm > self.max_grad_norm and norm > 1e-8:
                            p.grad = p.grad * (self.max_grad_norm / norm)

                self.optimizer.step()

                # 记录指标（用 numpy 值）
                policy_loss_val = float(
                    -np.minimum(surr1.data, surr2_data).mean()
                )
                metrics_sum["loss"] += float(total_loss.data)
                metrics_sum["policy_loss"] += policy_loss_val
                metrics_sum["value_loss"] += float(value_loss.data)
                metrics_sum["entropy"] += float(entropy_mean.data)
                n_updates += 1

        for k in metrics_sum:
            metrics_sum[k] /= max(1, n_updates)
        self.metrics.append(metrics_sum)
        return metrics_sum

    def save(self, path: str | Path) -> None:
        """保存模型检查点（断点续训）。

        Args:
            path: 保存路径（JSON 文件）。
        """
        state: dict[str, Any] = {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "hyperparams": {
                "lr": self.lr,
                "gamma": self.gamma,
                "clip_epsilon": self.clip_epsilon,
                "gae_lambda": self.gae_lambda,
                "epochs": self.epochs,
                "batch_size": self.batch_size,
                "ent_coef": self.ent_coef,
                "vf_coef": self.vf_coef,
                "max_grad_norm": self.max_grad_norm,
            },
            "params": [p.data.tolist() for p in self.ac.parameters()],
            "metrics": self.metrics,
        }
        Path(path).write_text(json.dumps(state), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """加载模型检查点（断点续训）。

        Args:
            path: 检查点路径（JSON 文件）。
        """
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        params = self.ac.parameters()
        saved_params = state["params"]
        for p, data in zip(params, saved_params, strict=True):
            p.data = np.array(data, dtype=np.float64)
        self.metrics = state.get("metrics", [])


__all__ = [
    "ActorCritic",
    "PPOAgent",
    "PPOConfig",
    "RolloutBuffer",
    "compute_gae",
]
