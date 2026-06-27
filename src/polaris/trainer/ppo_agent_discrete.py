"""PPO 离散动作空间智能体（从 ppo_torch.py 拆分，第63轮 P2-1）。

包含 PPOAgentDiscrete 类和权重迁移辅助函数。
接口与 PPOAgent 兼容，但使用 Categorical 分布代替 Gaussian。

来源:
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- Stable-Baselines3 PPO: https://stable-baselines3.readthedocs.io/
- Pomerleau, NeurIPS 1989, ALVINN
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from polaris.trainer.bc import (
    BCConfig,
    _run_bc_pretrain_discrete,
)
from polaris.trainer.ppo_buffers import (
    AgentSpec,
    BufferTensors,
    PPOConfig,
    RolloutBuffer,
    Transition,
    compute_gae,
)
from polaris.trainer.ppo_networks import ActorCriticDiscrete


def _migrate_weight_tensor(old_tensor: torch.Tensor, new_tensor: torch.Tensor) -> torch.Tensor:
    """迁移权重张量到新形状（输入维度变化时）。

    当 checkpoint 的 obs_dim 与当前不一致（如 113 → 249），按 min(old, new)
    复制重叠部分，新增维度保持初始化值（零），截断维度丢弃尾部。

    来源: 神经网络权重迁移标准做法（迁移学习/在线学习）
    """
    result = new_tensor.clone()
    # 取各维度最小值作为复制范围
    slices = tuple(slice(0, min(o, n)) for o, n in zip(old_tensor.shape, new_tensor.shape, strict=False))
    result[slices] = old_tensor[slices]
    return result


def _migrate_state_dict(
    saved_state: dict,
    new_state: dict,
) -> tuple[dict, int, int]:
    """迁移 checkpoint 的 state_dict 到新模型结构。

    当 checkpoint 的 obs_dim 与当前不一致时，自动 padding/截断权重，
    而非丢弃整个 checkpoint 从头训练。

    Args:
        saved_state: checkpoint 中的 network state_dict。
        new_state: 新模型的 state_dict（含初始化权重）。

    Returns:
        (migrated_state, n_migrated, n_skipped)
    """
    migrated = 0
    skipped = 0
    for key, new_tensor in new_state.items():
        if key not in saved_state:
            skipped += 1
            continue
        old_tensor = saved_state[key]
        if old_tensor.shape == new_tensor.shape:
            new_state[key] = old_tensor
        elif old_tensor.dim() == new_tensor.dim() and old_tensor.dim() >= 2:
            new_state[key] = _migrate_weight_tensor(old_tensor, new_tensor)
            migrated += 1
        else:
            skipped += 1
    return new_state, migrated, skipped


class PPOAgentDiscrete:
    """离散动作空间的 PPO 智能体。

    接口与 PPOAgent 兼容，但使用 Categorical 分布代替 Gaussian。

    来源: Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
          SB3 PPO: https://stable-baselines3.readthedocs.io/
    """

    def __init__(
        self,
        obs_dim: int,
        n_actions: int,
        config: PPOConfig | None = None,
        hidden_dim: int = 128,
    ):
        self.config = config or PPOConfig()
        self.network = ActorCriticDiscrete(obs_dim, n_actions, hidden_dim)
        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=self.config.lr)
        self.buffer = RolloutBuffer()
        self._total_steps = 0
        self.n_actions = n_actions

    def get_action(self, obs: np.ndarray) -> tuple[int, float, float]:
        return self.network.get_action(obs)

    def store(self, transition: Transition) -> None:
        self.buffer.obs.append(transition.obs)
        self.buffer.actions.append(np.array([transition.action]))
        self.buffer.rewards.append(transition.reward)
        self.buffer.logprobs.append(transition.logprob)
        self.buffer.values.append(transition.value)
        self.buffer.dones.append(transition.done)

    def update(self, last_value: float = 0.0) -> dict:
        if len(self.buffer) == 0:
            return {"loss": 0, "policy_loss": 0, "value_loss": 0, "entropy": 0}

        tensors = self._build_buffer_tensors(last_value)
        metrics = self._run_minibatch_updates(tensors)

        self._total_steps += 1  # M1.1 修复：按 update 次数计数（非 sample 数）
        self.buffer.clear()
        self._apply_lr_schedule()
        return metrics

    def _build_buffer_tensors(self, last_value: float) -> BufferTensors:
        """将 rollout buffer 转换为 torch 张量并计算 GAE 优势/回报。"""
        b_obs = torch.as_tensor(np.array(self.buffer.obs), dtype=torch.float32)
        b_actions = torch.as_tensor(np.array(self.buffer.actions), dtype=torch.long)
        b_logprobs = torch.as_tensor(np.array(self.buffer.logprobs), dtype=torch.float32)
        b_values = torch.as_tensor(np.array(self.buffer.values), dtype=torch.float32)
        b_dones = torch.as_tensor(np.array(self.buffer.dones), dtype=torch.float32)
        b_rewards = torch.as_tensor(np.array(self.buffer.rewards), dtype=torch.float32)

        advantages, returns = compute_gae(
            b_rewards.numpy().tolist(),
            b_values.numpy().tolist(),
            b_dones.numpy().tolist(),
            last_value,
            self.config,
        )
        b_advantages = torch.as_tensor(advantages, dtype=torch.float32)
        b_returns = torch.as_tensor(returns, dtype=torch.float32)

        # 归一化优势
        if b_advantages.numel() > 1:
            b_advantages = (b_advantages - b_advantages.mean()) / (b_advantages.std() + 1e-8)
        return BufferTensors(
            obs=b_obs,
            actions=b_actions,
            logprobs=b_logprobs,
            values=b_values,
            advantages=b_advantages,
            returns=b_returns,
        )

    def _run_minibatch_updates(self, tensors: BufferTensors) -> dict:
        """多 epoch 小批量更新，返回平均指标。"""
        total_loss_val = 0.0
        total_ploss = 0.0
        total_vloss = 0.0
        total_ent = 0.0
        n_updates = 0
        n_samples = len(self.buffer)
        mb_size = min(self.config.batch_size, n_samples)

        for _ in range(self.config.n_epochs):
            indices = np.arange(n_samples)
            np.random.shuffle(indices)
            for start in range(0, n_samples, mb_size):
                end = start + mb_size
                mb_idx = indices[start:end]
                mb_metrics = self._update_minibatch(tensors, mb_idx)
                total_loss_val += mb_metrics["loss"]
                total_ploss += mb_metrics["policy_loss"]
                total_vloss += mb_metrics["value_loss"]
                total_ent += mb_metrics["entropy"]
                n_updates += 1

        return {
            "loss": total_loss_val / max(1, n_updates),
            "policy_loss": total_ploss / max(1, n_updates),
            "value_loss": total_vloss / max(1, n_updates),
            "entropy": total_ent / max(1, n_updates),
        }

    def _update_minibatch(self, tensors: BufferTensors, mb_idx: np.ndarray) -> dict:
        """单个小批量的前向 → 损失 → 反向 → 优化器步进。"""
        b_obs = tensors.obs[mb_idx]
        b_actions = tensors.actions[mb_idx]
        b_logprobs = tensors.logprobs[mb_idx]
        b_values = tensors.values[mb_idx]
        b_advantages = tensors.advantages[mb_idx]
        b_returns = tensors.returns[mb_idx]

        new_logprob, new_value, entropy = self.network.evaluate(b_obs, b_actions)

        # PPO clip
        logratio = new_logprob - b_logprobs
        ratio = torch.exp(logratio)
        surr1 = ratio * b_advantages
        surr2 = (
            torch.clamp(
                ratio,
                1 - self.config.clip_eps,
                1 + self.config.clip_eps,
            )
            * b_advantages
        )
        policy_loss = -torch.min(surr1, surr2).mean()

        value_loss = self._compute_value_loss(new_value, b_returns, b_values)
        entropy_loss = -self.config.ent_coef * entropy.mean()
        loss = policy_loss + self.config.vf_coef * value_loss + entropy_loss

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.network.parameters(), self.config.max_grad_norm)
        self.optimizer.step()

        return {
            "loss": float(loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.mean().item()),
        }

    def _compute_value_loss(
        self,
        new_value: torch.Tensor,
        b_returns: torch.Tensor,
        b_values: torch.Tensor,
    ) -> torch.Tensor:
        """计算价值损失（支持 clip_vf）。"""
        if self.config.clip_vf <= 0:
            return 0.5 * ((new_value - b_returns).pow(2).mean())
        v_clipped = b_values + torch.clamp(
            new_value - b_values,
            -self.config.clip_vf,
            self.config.clip_vf,
        )
        v_loss1 = (new_value - b_returns).pow(2)
        v_loss2 = (v_clipped - b_returns).pow(2)
        return 0.5 * torch.max(v_loss1, v_loss2).mean()

    def _apply_lr_schedule(self) -> None:
        """根据 lr_schedule 调整优化器学习率。"""
        if self.config.lr_schedule == "cosine" and self.config.total_steps > 0:
            progress = min(1.0, self._total_steps / self.config.total_steps)
            new_lr = self.config.lr * 0.5 * (1 + np.cos(np.pi * progress))
            for pg in self.optimizer.param_groups:
                pg["lr"] = max(new_lr, 1e-6)
        elif self.config.lr_schedule == "linear" and self.config.total_steps > 0:
            progress = min(1.0, self._total_steps / self.config.total_steps)
            new_lr = self.config.lr * (1 - progress)
            for pg in self.optimizer.param_groups:
                pg["lr"] = max(new_lr, 1e-6)

    def save(self, path: str) -> None:
        torch.save(
            {
                "network": self.network.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "total_steps": self._total_steps,
                "n_actions": self.n_actions,
            },
            path,
        )

    @classmethod
    def load(
        cls,
        path: str,
        config: PPOConfig,
        spec: AgentSpec,
    ) -> PPOAgentDiscrete:
        """从检查点加载智能体。

        Args:
            path: 检查点文件路径。
            config: PPO 配置。
            spec: 智能体形状规格（obs_dim/n_actions/hidden_dim）。

        Bug 修复: 当 checkpoint 的 obs_dim 与当前 spec 不一致时（数据集变化导致），
        自动迁移权重（padding 零或截断），而非丢弃整个 checkpoint 从头训练。
        """
        agent = cls(spec.obs_dim, spec.n_actions, config, spec.hidden_dim)
        data = torch.load(path, weights_only=False)
        new_state = agent.network.state_dict()
        new_state, migrated, skipped = _migrate_state_dict(data["network"], new_state)
        agent.network.load_state_dict(new_state)
        # optimizer 状态可能与迁移后的网络不匹配，重建以避免 Adam moment 维度错误
        agent.optimizer = torch.optim.Adam(agent.network.parameters(), lr=agent.config.lr)
        agent._total_steps = data.get("total_steps", 0)
        if migrated > 0:
            print(
                f"  [迁移] {migrated} 个权重张量已迁移"
                f"（checkpoint obs_dim 与当前不一致），{skipped} 个跳过",
                flush=True,
            )
        return agent

    def bc_update(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
        grad_clip: float = 1.0,
    ) -> dict:
        """单步 Behavior Cloning 更新（离散动作，交叉熵）。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

        Args:
            obs: 观测张量 (batch, obs_dim)。
            expert_actions: 专家离散动作张量 (batch,) 或 (batch, 1)。
            grad_clip: 梯度裁剪最大范数。

        Returns:
            {loss, accuracy} 指标字典。
        """
        self.optimizer.zero_grad()
        loss, acc = self.network.bc_loss(obs, expert_actions)
        loss.backward()
        nn.utils.clip_grad_norm_(self.network.parameters(), grad_clip)
        self.optimizer.step()
        return {"loss": float(loss.item()), "accuracy": float(acc.item())}

    def pretrain(
        self,
        expert_obs: np.ndarray,
        expert_actions: np.ndarray,
        config: BCConfig | None = None,
    ) -> list[dict]:
        """Behavior Cloning 预训练入口（离散动作）。

        在专家数据上监督学习策略网络，作为 PPO RL 微调的初始化。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

        Args:
            expert_obs: 专家观测数组 [N, obs_dim]。
            expert_actions: 专家离散动作数组 [N] 或 [N, 1]。
            config: BC 训练配置（None 用默认 BCConfig）。

        Returns:
            训练指标历史列表。
        """
        return _run_bc_pretrain_discrete(self, expert_obs, expert_actions, config)


__all__ = [
    "PPOAgentDiscrete",
    "AgentSpec",
]
