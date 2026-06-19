"""PPO 智能体 — PyTorch 实现版。

torch 版 PPO，替代 polaris.nn 纯 NumPy 实现，训练速度提升 10-50x。
接口与 ppo.py 完全兼容，可无缝切换。

来源:
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
- Stable-Baselines3 PPO: https://stable-baselines3.readthedocs.io/
- CleanRL PPO: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from polaris.trainer.ppo_buffers import (
    AgentSpec,
    BufferTensors,
    PPOConfig,
    RolloutBuffer,
    Transition,
    compute_gae,
)
from polaris.trainer.ppo_networks import ActorCritic, ActorCriticDiscrete

__all__ = [
    "AgentSpec",
    "ActorCritic",
    "ActorCriticDiscrete",
    "BufferTensors",
    "PPOAgent",
    "PPOAgentDiscrete",
    "PPOConfig",
    "RolloutBuffer",
    "Transition",
    "compute_gae",
]


class PPOAgentDiscrete:
    """离散动作空间的 PPO 智能体。

    接口与 PPOAgent 兼容，但使用 Categorical 分布代替 Gaussian。
    适用于 MultiDiscrete/Discrete 动作空间。

    来源:
    - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
    - Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
    - SB3 PPO: https://stable-baselines3.readthedocs.io/
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
        """
        agent = cls(spec.obs_dim, spec.n_actions, config, spec.hidden_dim)
        data = torch.load(path, weights_only=False)
        agent.network.load_state_dict(data["network"])
        agent.optimizer.load_state_dict(data["optimizer"])
        agent._total_steps = data.get("total_steps", 0)
        return agent


class PPOAgent:
    """PPO 智能体（actor-critic + clip + GAE + 2025 增强技巧）— PyTorch 版。

    复刻 Stable-Baselines3 ``PPO`` 的核心训练循环，并集成:
    - 学习率调度（cosine annealing + warmup）
    - 价值函数 clip
    - orthogonal 初始化

    接口与 polaris.trainer.ppo.PPOAgent 完全兼容，可无缝切换。

    来源:
    - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
    - SB3 PPO: https://stable-baselines3.readthedocs.io/
    - Loshchilov & Hutter, 2017, SGDR https://arxiv.org/abs/1608.03983
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
        self.optimizer = optim.Adam(self.ac.parameters(), lr=self.config.lr)
        self.buffer = RolloutBuffer()
        self.metrics: list[dict] = []
        self.current_step = 0  # 用于学习率调度

    def get_action(self, obs: np.ndarray):
        """采样动作。

        Args:
            obs: numpy 观测数组。

        Returns:
            (action_numpy, logprob_float, value_float)
        """
        return self.ac.get_action(obs)

    def _get_lr(self) -> float:
        """计算当前学习率（支持 constant/cosine/linear 调度）。

        来源: Loshchilov & Hutter, 2017, SGDR
              https://arxiv.org/abs/1608.03983
        """
        cfg = self.config
        if cfg.lr_schedule == "constant":
            return cfg.lr
        step = self.current_step
        if step < cfg.lr_warmup_steps:
            # linear warmup
            return cfg.lr * (step + 1) / max(1, cfg.lr_warmup_steps)
        progress = (step - cfg.lr_warmup_steps) / max(1, cfg.total_steps - cfg.lr_warmup_steps)
        progress = min(1.0, max(0.0, progress))
        if cfg.lr_schedule == "cosine":
            return cfg.lr * 0.5 * (1.0 + math.cos(math.pi * progress))
        # linear decay
        return cfg.lr * (1.0 - progress)

    def store(self, transition: Transition) -> None:
        """将单步转移数据存入缓冲区。"""
        self.buffer.obs.append(transition.obs)
        self.buffer.actions.append(transition.action)
        self.buffer.rewards.append(transition.reward)
        self.buffer.logprobs.append(transition.logprob)
        self.buffer.values.append(transition.value)
        self.buffer.dones.append(transition.done)

    def compute_advantages(self, last_value: float) -> None:
        """计算 GAE 优势并标准化。"""
        adv, ret = compute_gae(
            self.buffer.rewards,
            self.buffer.values,
            self.buffer.dones,
            last_value,
            self.config,
        )
        self.buffer.advantages = adv
        self.buffer.returns = ret
        # 标准化优势（与 SB3 一致）
        if len(adv) > 0 and adv.std() > 1e-8:
            self.buffer.advantages = (adv - adv.mean()) / (adv.std() + 1e-8)

    def _process_minibatch(self, mb: BufferTensors) -> dict:
        """处理单个小批量：前向 → 损失 → 反向 → 优化器步进，返回指标。"""
        self.optimizer.zero_grad()

        new_logprob, value_pred, entropy = self.ac.evaluate(mb.obs, mb.actions)

        # ratio = exp(new_logprob - old_logprob)
        ratio = torch.exp(new_logprob - mb.logprobs)

        # 策略损失（clip）
        surr1 = ratio * mb.advantages
        surr2 = (
            torch.clamp(
                ratio,
                1.0 - self.config.clip_eps,
                1.0 + self.config.clip_eps,
            )
            * mb.advantages
        )
        policy_loss = -torch.min(surr1, surr2).mean()

        # 价值损失（2025 增强：clip 防止异常）
        # 来源: SB3 PPO clip_vf
        if self.config.clip_vf > 0:
            # 直接 clip value_diff（与 NumPy 版一致）
            value_diff = mb.returns - value_pred
            value_diff = torch.clamp(value_diff, -self.config.clip_vf, self.config.clip_vf)
            value_loss = (value_diff**2).mean()
        else:
            value_loss = ((mb.returns - value_pred) ** 2).mean()

        # 熵奖励
        entropy_mean = entropy.mean()

        # 总损失
        loss = policy_loss + self.config.vf_coef * value_loss - self.config.ent_coef * entropy_mean

        loss.backward()
        nn.utils.clip_grad_norm_(self.ac.parameters(), self.config.max_grad_norm)
        self.optimizer.step()

        return {
            "loss": float(loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy_mean.item()),
        }

    def update(self, last_value: float = 0.0) -> dict:
        """PPO 更新（多 epoch 小批量）。"""
        self.compute_advantages(last_value)
        # 2025 增强：学习率调度
        # 来源: Loshchilov & Hutter, 2017, SGDR
        self.current_step += 1
        new_lr = self._get_lr()
        for pg in self.optimizer.param_groups:
            pg["lr"] = new_lr

        n = len(self.buffer)
        if n == 0:
            return {
                "loss": 0.0,
                "policy_loss": 0.0,
                "value_loss": 0.0,
                "entropy": 0.0,
            }

        tensors = self._stack_buffer_tensors()
        metrics_sum, n_updates = self._run_ppo_epochs(tensors, n)

        for k in metrics_sum:
            metrics_sum[k] /= max(1, n_updates)
        self.metrics.append(metrics_sum)
        self.buffer.clear()
        return metrics_sum

    def _stack_buffer_tensors(self) -> BufferTensors:
        """将 rollout buffer 转为 torch 张量（一次性，避免重复转换）。"""
        obs_np = np.array(self.buffer.obs, dtype=np.float32)
        actions_np = np.array(self.buffer.actions, dtype=np.float32)
        old_logprobs_np = np.array(self.buffer.logprobs, dtype=np.float32)
        advantages_np = self.buffer.advantages.astype(np.float32)
        returns_np = self.buffer.returns.astype(np.float32)
        values_np = np.array(self.buffer.values, dtype=np.float32)
        return BufferTensors(
            obs=torch.as_tensor(obs_np),
            actions=torch.as_tensor(actions_np),
            logprobs=torch.as_tensor(old_logprobs_np),
            values=torch.as_tensor(values_np),
            advantages=torch.as_tensor(advantages_np),
            returns=torch.as_tensor(returns_np),
        )

    def _run_ppo_epochs(self, tensors: BufferTensors, n: int) -> tuple[dict, int]:
        """跑多 epoch 小批量更新，返回指标累加和与更新次数。"""
        indices = np.arange(n)
        batch_size = min(self.config.batch_size, n)
        metrics_sum = {
            "loss": 0.0,
            "policy_loss": 0.0,
            "value_loss": 0.0,
            "entropy": 0.0,
        }
        n_updates = 0

        for _ in range(self.config.n_epochs):
            np.random.shuffle(indices)
            for start in range(0, n, batch_size):
                idx = indices[start : start + batch_size]
                mb = BufferTensors(
                    obs=tensors.obs[idx],
                    actions=tensors.actions[idx],
                    logprobs=tensors.logprobs[idx],
                    values=tensors.values[idx],
                    advantages=tensors.advantages[idx],
                    returns=tensors.returns[idx],
                )
                mb_metrics = self._process_minibatch(mb)
                for k in metrics_sum:
                    metrics_sum[k] += mb_metrics[k]
                n_updates += 1

        return metrics_sum, n_updates

    def save(self, path: str | Path) -> None:
        """保存检查点（JSON 格式，与 NumPy 版兼容）。"""
        params_list = []
        for p in self.ac.parameters():
            params_list.append(p.detach().cpu().numpy().tolist())
        state = {
            "config": self.config.__dict__,
            "obs_dim": self.obs_dim,
            "action_dim": self.action_dim,
            "params": params_list,
            "metrics": self.metrics,
        }
        Path(path).write_text(json.dumps(state), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """加载检查点（JSON 格式，与 NumPy 版兼容）。"""
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        params = list(self.ac.parameters())
        for p, data in zip(params, state["params"], strict=True):
            p_data = np.array(data, dtype=np.float32)
            p.data = torch.as_tensor(p_data)
        self.metrics = state.get("metrics", [])
