"""PPO 智能体 — PyTorch 实现版。

torch 版 PPO，替代 polaris.nn 纯 NumPy 实现，训练速度提升 10-50x。
接口与 ppo.py 完全兼容，可无缝切换。

## 架构（第63轮 P2-1 拆分）

- ``ppo_agent_discrete.py``：PPOAgentDiscrete 类 + 权重迁移辅助函数
- ``ppo_torch.py``（本文件）：PPOAgent 类（连续动作）+ 重新导出

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

# BCConfig 与 BC 预训练辅助函数（避免在函数签名中展开 7+ 参数，规则 7.1；
# 同时避免本文件超过 500 行有效代码限制，规则 7.1）
from polaris.trainer.bc import (  # noqa: E402
    BCConfig,
    _run_bc_pretrain_continuous,
)
from polaris.trainer.ppo_agent_discrete import (
    PPOAgentDiscrete,
)
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


class PPOAgent:
    """PPO 智能体（actor-critic + clip + GAE + 2025 增强技巧）— PyTorch 版。

    复刻 Stable-Baselines3 ``PPO`` 核心训练循环，集成学习率调度、价值函数 clip、
    orthogonal 初始化。接口与 polaris.trainer.ppo.PPOAgent 完全兼容。

    来源: Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
          SB3 PPO: https://stable-baselines3.readthedocs.io/
          Loshchilov & Hutter, 2017, SGDR https://arxiv.org/abs/1608.03983
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
        """采样动作，返回 (action, logprob, value)。"""
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

    def bc_update(
        self,
        obs: torch.Tensor,
        expert_actions: torch.Tensor,
        loss_type: str = "nll",
        grad_clip: float = 1.0,
    ) -> dict:
        """单步 Behavior Cloning 更新（连续动作）。

        用专家示范数据监督学习策略网络，作为 PPO RL 微调的初始化。
        价值头不参与 BC 训练（PPO 阶段再学习）。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
              Ross & Bagnell, AISTATS 2011, DAgger https://arxiv.org/abs/1011.0686

        Args:
            obs: 观测张量 (batch, obs_dim)。
            expert_actions: 专家动作张量 (batch, action_dim)。
            loss_type: "nll"（负对数似然，默认）或 "mse"。
            grad_clip: 梯度裁剪最大范数。

        Returns:
            {loss, mse, nll} 指标字典。
        """
        self.optimizer.zero_grad()
        loss, mse_loss = self.ac.bc_loss(obs, expert_actions, loss_type=loss_type)
        loss.backward()
        nn.utils.clip_grad_norm_(self.ac.parameters(), grad_clip)
        self.optimizer.step()
        # nll 与 mse 的关系：loss_type=="mse" 时 loss==mse，nll 用 bc_loss 内部计算
        nll_val = float(loss.item()) if loss_type == "nll" else 0.0
        return {
            "loss": float(loss.item()),
            "mse": float(mse_loss.item()),
            "nll": nll_val,
        }

    def pretrain(
        self,
        expert_obs: np.ndarray,
        expert_actions: np.ndarray,
        config: BCConfig | None = None,
    ) -> list[dict]:
        """Behavior Cloning 预训练入口（连续动作）。

        在专家数据上监督学习策略网络，作为 PPO RL 微调的初始化。
        训练完成后调用 ``save()`` 保存检查点，再交给 PPO 训练循环微调。

        来源: Pomerleau, NeurIPS 1989, ALVINN
              https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

        Args:
            expert_obs: 专家观测数组 [N, obs_dim]。
            expert_actions: 专家动作数组 [N, action_dim]。
            config: BC 训练配置（None 用默认 BCConfig）。

        Returns:
            训练指标历史列表。
        """
        return _run_bc_pretrain_continuous(self, expert_obs, expert_actions, config)
