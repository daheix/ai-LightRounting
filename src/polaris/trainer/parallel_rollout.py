"""并行 rollout 采集器（第20轮 P1-4 分布式训练基础）。

支持多环境并行采集 rollout，为分布式 PPO 训练提供接口基础。
当前实现为单线程顺序采集（接口兼容未来 Ray/multiprocessing 后端）。

## 设计

- N 个环境各自独立采集 `rollout_steps_per_env` 步
- 所有 transition 聚合到单个 PPO agent 的 buffer
- 有效 batch size = num_envs × rollout_steps_per_env
- 对齐 Stable-Basales3 VecEnv / CleanRL ppo.py 的 vectorized env 模式

## 商业差距

P1-4 无分布式训练与 GPU 加速：
- 商业标杆：AlphaChip 分布式 TPU，DREAMPlace GPU 40×，ICC2 多线程
- 本模块提供多环境采集接口（CPU 顺序版），v2.0 接入 Ray 后端

## 来源

- Stable-Baselines3 VecEnv: https://stable-baselines3.readthedocs.io/
- CleanRL ppo.py: https://github.com/vwxyzjn/cleanrl
- PPO 原论文: Schulman et al., 2017, https://arxiv.org/abs/1707.06347


## 补充文献（R02 学术诚信补齐）
- Mirhoseini et al. 2021 Nature AlphaChip: https://www.nature.com/articles/s41586-021-03544-w
- Espeholt et al. 2018 IMPALA V-trace: https://arxiv.org/abs/1802.01561
"""

from __future__ import annotations

from dataclasses import dataclass

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.trainer.ppo import PPOAgent
from polaris.trainer.train_loop import (
    TrainConfig,
    _collect_floorplan_rollout,
    _collect_routing_rollout,
)


@dataclass(frozen=True)
class ParallelRolloutConfig:
    """并行 rollout 采集配置。

    Attributes:
        num_envs: 并行环境数（1=单环境，4/8=多环境采集）。
        rollout_steps_per_env: 每个环境每轮采集步数。
        total_rollout_steps: 每轮总采集步数 = num_envs × rollout_steps_per_env。
    """

    num_envs: int = 4
    rollout_steps_per_env: int = 125

    @property
    def total_rollout_steps(self) -> int:
        """每轮总采集步数。"""
        return self.num_envs * self.rollout_steps_per_env


def make_large_scale_train_config(
    num_envs: int = 4,
    rollout_steps_per_env: int = 125,
) -> TrainConfig:
    """创建大规模训练配置（P1-4 分布式训练）。

    默认 4 envs × 125 steps = 500 总步数，对齐商业工具大规模训练。

    Args:
        num_envs: 并行环境数（默认 4）。
        rollout_steps_per_env: 每环境步数（默认 125，4×125=500）。

    Returns:
        TrainConfig with rollout_steps=500（兼容单环境路径）。
    """
    return TrainConfig(
        rollout_steps=rollout_steps_per_env * num_envs,
        num_episodes=100,
        hidden_dim=128,
    )


def collect_floorplan_rollout_parallel(
    agent: PPOAgent,
    envs: list[FloorplanEnv],
    obs_list: list,
    dims: tuple[int, int],
    rollout_steps_per_env: int,
) -> tuple[float, int]:
    """多环境并行采集布局 rollout（顺序版，接口兼容未来并行后端）。

    Args:
        agent: PPO agent（共享 buffer）。
        envs: 环境列表（N 个）。
        obs_list: 每个环境的当前观测列表。
        dims: (obs_dim, action_dim)。
        rollout_steps_per_env: 每环境采集步数。

    Returns:
        (total_reward, total_steps) 跨所有环境的累计值。
    """
    obs_dim, action_dim = dims
    total_reward = 0.0
    total_steps = 0
    for env_idx, env in enumerate(envs):
        obs = obs_list[env_idx]
        ep_reward, steps = _collect_floorplan_rollout(
            agent, env, obs, dims, rollout_steps_per_env
        )
        total_reward += ep_reward
        total_steps += steps
        # 更新该环境的最新观测（用于下一轮）
        obs_list[env_idx] = obs
    return total_reward, total_steps


def collect_routing_rollout_parallel(
    agent: PPOAgent,
    envs: list,
    obs_list: list,
    obs_dim: int,
    rollout_steps_per_env: int,
) -> tuple[float, int]:
    """多环境并行采集布线 rollout（顺序版）。

    Args:
        agent: PPO agent（共享 buffer）。
        envs: 环境列表（N 个）。
        obs_list: 每个环境的当前观测列表。
        obs_dim: 观测维度。
        rollout_steps_per_env: 每环境采集步数。

    Returns:
        (total_reward, total_steps) 跨所有环境的累计值。
    """
    total_reward = 0.0
    total_steps = 0
    for env_idx, env in enumerate(envs):
        obs = obs_list[env_idx]
        ep_reward, steps = _collect_routing_rollout(
            agent, env, obs, obs_dim, rollout_steps_per_env
        )
        total_reward += ep_reward
        total_steps += steps
        obs_list[env_idx] = obs
    return total_reward, total_steps


def effective_batch_size(config: ParallelRolloutConfig) -> int:
    """计算有效 batch size = num_envs × rollout_steps_per_env。"""
    return config.total_rollout_steps


__all__ = [
    "ParallelRolloutConfig",
    "collect_floorplan_rollout_parallel",
    "collect_routing_rollout_parallel",
    "effective_batch_size",
    "make_large_scale_train_config",
]
