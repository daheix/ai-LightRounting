"""PPO 数据结构 — 配置、rollout buffer、转移、张量打包与 GAE 计算。

从 ``ppo_torch.py`` 拆分而来，降低单文件规模（规则 4.1）。

来源:
- Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
- SB3 RolloutBuffer: https://stable-baselines3.readthedocs.io/
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch


@dataclass
class PPOConfig:
    """PPO 超参数（与 Stable-Baselines3 默认值对齐 + 2025 增强技巧）。

    增强来源:
    - Basso et al., NeurIPS 2025, routing-aware floorplanning RL
      https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    - SB3 PPO 实现: https://stable-baselines3.readthedocs.io/
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
    # 2025 增强：价值函数 clip（防止价值估计异常导致策略崩溃）
    # 来源: SB3 PPO clip_vf 实现
    clip_vf: float = 0.0  # 0=禁用clip_vf（之前10.0导致value_loss恒等于100）
    # 2025 增强：学习率调度（cosine annealing + warmup）
    # 来源: Loshchilov & Hutter, 2017, SGDR
    #       https://arxiv.org/abs/1608.03983
    lr_schedule: str = "constant"  # constant / cosine / linear
    lr_warmup_steps: int = 0  # warmup 步数
    total_steps: int = 1000  # 总训练步数（用于 cosine 调度）


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


@dataclass
class Transition:
    """单步转移数据（将 store 的多个参数打包，降低函数参数个数）。

    Attributes:
        obs: 观测。
        action: 动作。
        reward: 奖励。
        logprob: 动作对数概率。
        value: 价值估计。
        done: 是否终止。
    """

    obs: object
    action: object
    reward: float
    logprob: float
    value: float
    done: bool


@dataclass
class BufferTensors:
    """将 rollout buffer 转换为 torch 张量后的打包容器。

    用于降低 PPO 更新函数的参数个数与圈复杂度。
    """

    obs: torch.Tensor
    actions: torch.Tensor
    logprobs: torch.Tensor
    values: torch.Tensor
    advantages: torch.Tensor
    returns: torch.Tensor


@dataclass
class AgentSpec:
    """PPO 智能体的形状规格（打包 load 类方法参数，降低参数个数）。

    Attributes:
        obs_dim: 观测维度。
        n_actions: 离散动作数。
        hidden_dim: 隐藏层维度。
    """

    obs_dim: int
    n_actions: int
    hidden_dim: int = 128


def compute_gae(
    rewards: list[float],
    values: list[float],
    dones: list[bool],
    last_value: float,
    config: PPOConfig | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """计算 GAE 优势与回报（与 SB3/CleanRL 一致）。

    来源: Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438

    Args:
        rewards: 每步奖励序列。
        values: 每步价值估计序列。
        dones: 每步终止标志序列。
        last_value: 最后一步的价值估计（bootstrap）。
        config: PPO 配置（提供 gamma 与 gae_lambda），None 时使用默认值。

    Returns:
        (优势数组, 回报数组)。
    """
    gamma = config.gamma if config else 0.99
    gae_lambda = config.gae_lambda if config else 0.95
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


__all__ = [
    "AgentSpec",
    "BufferTensors",
    "PPOConfig",
    "RolloutBuffer",
    "Transition",
    "compute_gae",
]
