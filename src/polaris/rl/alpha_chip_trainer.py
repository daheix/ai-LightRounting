"""R34-R35 路标：AlphaChip 训练器（PPO + GAE）。

本模块从 ``alpha_chip.py`` 拆分而来（facade 模式），提供
``AlphaChipTrainer``，基于 PPO clip + GAE 训练 AlphaChip 布局智能体。
外部 import 路径保持不变（``from polaris.rl.alpha_chip import
AlphaChipTrainer``）。

## 学术依据

- PPO 算法（Schulman 2017 arXiv:1707.06347）
  https://arxiv.org/abs/1707.06347
- GAE 优势估计（Schulman 2015 arXiv:1506.02438）
  https://arxiv.org/abs/1506.02438
- Sutton & Barto, 2018, "Reinforcement Learning: An Introduction" §13
  （策略梯度）
- Mirhoseini et al., Nature 2024, "AlphaChip":
  https://doi.org/10.1038/s41586-024-07714-9
- DREAMPlace RUDY 拥塞估计: https://arxiv.org/abs/2004.10746

## 架构统一（D05 Task 10）

D05 架构统一：复用 ``PPOAgent``（PPO clip + GAE），替代旧版自实现
简化版 REINFORCE + baseline。

## 来源

- 拆分自: ``src/polaris/rl/alpha_chip.py``（原文件 1096 行 → 拆分后 ≤800 行）
- 路标: R34-R35
- 架构统一: D05 Task 10
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from polaris.rl.alpha_chip_config import _GRID_CELL_SIZE, AlphaChipConfig
from polaris.trainer.ppo_buffers import Transition

if TYPE_CHECKING:
    from polaris.rl.alpha_chip_agent import AlphaChipAgent


class AlphaChipTrainer:
    """AlphaChip 训练器。

    D05 架构统一：复用 PPOAgent（PPO clip + GAE），替代旧版自实现
    简化版 REINFORCE + baseline。

    学术依据：
    - PPO 算法（Schulman 2017 arXiv:1707.06347）
    - GAE 优势估计（Schulman 2015 arXiv:1506.02438）
    - Sutton & Barto 2018 §13（策略梯度）
    """

    def __init__(self, agent: AlphaChipAgent, config: AlphaChipConfig) -> None:
        """初始化训练器。

        Args:
            agent: AlphaChip agent。
            config: AlphaChip 配置。
        """
        self.agent = agent
        self.config = config

    def collect_trajectory(self, circuit: dict) -> dict:
        """收集一条轨迹（D05: 复用 PPOAgent.store 存储连续动作转移）。

        顺序放置所有器件，记录每步状态/动作/奖励/对数概率/价值，
        并将连续动作转移存入 PPOAgent 缓冲区供 PPO 更新。

        Args:
            circuit: 电路描述 dict。

        Returns:
            轨迹 dict，含 states / actions / rewards / logprobs / values /
            final_reward / placement。
        """
        self.agent.circuit = circuit
        placement: dict[str, dict] = {}
        grid_h, grid_w = self.config.grid_size
        trajectory: dict[str, list] = {
            "states": [],
            "actions": [],
            "rewards": [],
            "logprobs": [],
            "values": [],
        }
        prev_reward = 0.0
        n_devs = len(circuit["devices"])
        for step, dev in enumerate(circuit["devices"]):
            state = self.agent._build_state(placement, circuit, dev)
            # D05: 连续动作采样 + 网格量化（连续动作存入 PPO 缓冲区）
            action_cont, logprob, value = self.agent._select_continuous_action(state)
            grid_action = self.agent._quantize_action(action_cont, state["mask"])
            self.agent._last_continuous_action = np.asarray(action_cont, dtype=np.float64)
            row = grid_action // grid_w
            col = grid_action % grid_w
            placement[dev["id"]] = {
                "x": float(col * _GRID_CELL_SIZE),
                "y": float(row * _GRID_CELL_SIZE),
                "rotation": 0,
            }
            # 增量奖励（当前布局总奖励 - 上一步）
            cur_reward = self.agent.compute_reward(placement)
            step_reward = cur_reward - prev_reward
            prev_reward = cur_reward
            done = step == n_devs - 1
            self.agent.ppo.store(
                Transition(
                    obs=np.asarray(state["embedding"], dtype=np.float64),
                    action=np.asarray(action_cont, dtype=np.float64),
                    reward=float(step_reward),
                    logprob=float(logprob),
                    value=float(value),
                    done=bool(done),
                )
            )
            trajectory["states"].append(state)
            trajectory["actions"].append(grid_action)
            trajectory["rewards"].append(float(step_reward))
            trajectory["logprobs"].append(logprob)
            trajectory["values"].append(value)
        final_reward = self.agent.compute_reward(placement)
        trajectory["final_reward"] = float(final_reward)
        trajectory["placement"] = placement
        return trajectory

    def update_policy(self, trajectories: list) -> dict:
        """PPO 策略更新（D05: 复用 PPOAgent.update）。

        替代旧版自实现 REINFORCE + baseline，使用 PPO clip + GAE
        （转移已由 collect_trajectory 存入 PPOAgent 缓冲区）。

        Args:
            trajectories: 轨迹列表。

        Returns:
            训练指标 dict，含 policy_loss / value_loss / n_updates。
        """
        # 最后一帧价值作为 bootstrap（GAE 末端价值估计）
        last_value = 0.0
        if trajectories and trajectories[-1]["values"]:
            last_value = float(trajectories[-1]["values"][-1])
        metrics = self.agent.ppo.update(last_value=last_value)
        return {
            "policy_loss": float(metrics.get("policy_loss", 0.0)),
            "value_loss": float(metrics.get("value_loss", 0.0)),
            "n_updates": len(trajectories),
        }

    def train(self, circuits: list, n_epochs: int = 100) -> dict:
        """训练 agent。

        Args:
            circuits: 电路列表。
            n_epochs: 训练轮数。

        Returns:
            训练历史 dict，含 epoch / reward / policy_loss / value_loss。
        """
        history: dict[str, list] = {
            "epoch": [],
            "reward": [],
            "policy_loss": [],
            "value_loss": [],
        }
        for epoch in range(n_epochs):
            trajectories = [self.collect_trajectory(c) for c in circuits]
            metrics = self.update_policy(trajectories)
            avg_reward = float(np.mean([t["final_reward"] for t in trajectories]))
            history["epoch"].append(epoch)
            history["reward"].append(avg_reward)
            history["policy_loss"].append(metrics["policy_loss"])
            history["value_loss"].append(metrics["value_loss"])
        return history

    def evaluate(self, circuit: dict) -> dict:
        """评估布局质量。

        Args:
            circuit: 电路描述 dict。

        Returns:
            评估结果 dict，含 placement / reward / 各项指标。
        """
        placement = self.agent.place(circuit)
        reward_result = self.agent.reward.compute(placement, circuit)
        return {
            "placement": placement,
            "reward": reward_result["reward"],
            **reward_result,
        }


__all__ = ["AlphaChipTrainer"]
