"""PPO 训练循环（polaris-trainer）。

迁移自 PoLaRIS v4 ``src/polaris/trainer/train_loop.py``，去除对 v4 旧包
（``polaris.engine.FloorplanEnv`` / ``polaris.router.RoutingEnv`` /
``polaris.trainer.dataset``）的硬依赖，改用**依赖注入**：调用方提供遵循
Gymnasium 协议的 env（或 env_factory），本模块提供可复用的 PPO 训练循环
（rollout 采集 → GAE 优势估计 → 多 epoch 小批量更新 → 指标记录 →
断点续训 checkpoint → 早停）。

## Env 协议（Gymnasium 兼容）

- ``env.reset()`` → ``(obs, info)``
- ``env.step(action)`` → ``(obs, reward, terminated, truncated, info)``
- ``obs`` 可为 dict（自动展平）或 array

## 依赖注入（R13 保持功能独立）

polaris-trainer 仅依赖 numpy，不捆绑具体 EDA 环境。调用方注入:
- 单 env 训练：``train_ppo(agent, env, config, ...)``
- 多 env（每轮换网表）训练：``train_with_env_factory(agent, env_factory, config, ...)``
  其中 ``env_factory(ep)`` 返回第 ep 轮的 env
- 连续→离散动作映射：``action_transform(action, env)`` 可选回调
  （布局场景用 ``discretize_floorplan_action``）

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
2. Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
3. Stable-Baselines3 PPO.learn() 训练循环
   https://stable-baselines3.readthedocs.io/
4. CleanRL ppo.py 单文件训练循环 https://github.com/vwxyzjn/cleanrl
5. Loshchilov & Hutter, 2017, SGDR 余弦退火 https://arxiv.org/abs/1608.03983
6. Apollo arXiv 2025, 布线感知布局反馈 https://arxiv.org/html/2504.18813v1
7. Nocedal & Wright 2006, Numerical Optimization Springer
   https://doi.org/10.1007/978-0-387-40065-5

来源: 迁移自 PoLaRIS v4 ``src/polaris/trainer/train_loop.py``（依赖注入重构）。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from polaris_trainer.ppo import PPOAgent, PPOConfig, Transition
from polaris_trainer.tensorboard_logger import TrainingLogger

# 动作变换回调类型：将 PPO 连续动作映射为 env 可接受的（如离散网格）动作
ActionTransform = Callable[[np.ndarray, object], np.ndarray]


@dataclass
class TrainConfig:
    """训练配置（env 无关，EDA 场景参数由调用方注入 env 时携带）。

    Attributes:
        ppo: PPO 超参数。
        num_episodes: 训练轮数。
        rollout_steps: 每轮采样步数。
        hidden_dim: 隐藏层维度。
        checkpoint_dir: 检查点目录。
        checkpoint_every: 每多少轮保存检查点。
        log_every: 每多少轮打印日志。
        seed: 随机种子。
        early_stop_patience: 早停耐心值（连续多少轮无改善则停止，0=禁用）。
        lr_schedule: 学习率调度（"constant"/"linear"/"cosine"）。
    """

    ppo: PPOConfig = field(default_factory=PPOConfig)
    num_episodes: int = 50
    rollout_steps: int = 64
    hidden_dim: int = 128
    checkpoint_dir: str = "checkpoints"
    checkpoint_every: int = 10
    log_every: int = 1
    seed: int = 42
    early_stop_patience: int = 50
    lr_schedule: str = "cosine"


def lr_scale(ep: int, total: int, schedule: str) -> float:
    """计算当前轮的学习率缩放因子（独立工具函数）。

    Args:
        ep: 当前轮次（0-based）。
        total: 总轮数。
        schedule: "constant" 返回 1.0；"linear" 线性衰减到 0；
            "cosine" 余弦衰减到 0。

    Returns:
        学习率缩放因子（0.0~1.0）。

    来源: Loshchilov & Hutter, 2017, SGDR https://arxiv.org/abs/1608.03983
    """
    if total <= 0:
        return 1.0
    if schedule == "linear":
        return max(0.0, 1.0 - ep / total)
    if schedule == "cosine":
        return 0.5 * (1.0 + math.cos(math.pi * ep / total))
    return 1.0


def obs_to_vector(obs) -> np.ndarray:
    """将 Gymnasium dict/array 观测展平为向量（供 PPO 使用）。"""
    if isinstance(obs, dict):
        parts = []
        for v in obs.values():
            parts.append(np.asarray(v, dtype=np.float64).flatten())
        return np.concatenate(parts)
    return np.asarray(obs, dtype=np.float64).flatten()


def infer_obs_dim(env) -> int:
    """推断观测向量维度（R03: env.reset 须返回 (obs, info)）。"""
    obs, _info = env.reset()
    return obs_to_vector(obs).shape[0]


def pad_obs(obs_vec: np.ndarray, obs_dim: int) -> np.ndarray:
    """将观测向量零填充/截断到固定维度。

    正常情况 obs_dim 应配置为数据集最大器件数对应维度；仅当超过硬性上限时
    才截断（避免网络输入维度不匹配），否则零填充保留所有器件信息。
    """
    if obs_vec.shape[0] < obs_dim:
        return np.pad(obs_vec, (0, obs_dim - obs_vec.shape[0]))
    if obs_vec.shape[0] > obs_dim:
        return obs_vec[:obs_dim]
    return obs_vec


def discretize_floorplan_action(action: np.ndarray, env) -> np.ndarray:
    """将连续动作离散化到 MultiDiscrete 网格动作 (gx, gy, rot)。

    需要 env 暴露 ``grid_w`` / ``grid_h`` 属性（布局环境约定）。
    """
    n_gw = getattr(env, "grid_w")
    n_gh = getattr(env, "grid_h")
    action_dim = action.shape[0]
    gx = int(np.clip(action[0], 0, 1) * (n_gw - 1)) if action_dim >= 1 else 0
    gy = int(np.clip(action[1] if action_dim > 1 else 0, 0, 1) * (n_gh - 1))
    rot = int(np.clip(action[2] if action_dim > 2 else 0, 0, 1) * 3)
    return np.array([gx, gy, rot])


def _collect_rollout(
    agent: PPOAgent,
    env,
    obs,
    obs_dim: int,
    rollout_steps: int,
    action_transform: ActionTransform | None,
) -> tuple[float, int, dict]:
    """采集 rollout，返回 (ep_reward, steps, last_info)。

    env.step 须返回 Gymnasium 5-tuple ``(obs, reward, terminated, truncated, info)``。
    last_info 用于提取 HPWL 等布局指标（供 TrainingLogger 记录）。
    """
    ep_reward = 0.0
    steps = 0
    last_info: dict = {}
    for _ in range(rollout_steps):
        obs_vec = pad_obs(obs_to_vector(obs), obs_dim)
        action, logprob, value = agent.get_action(obs_vec)
        env_action = action_transform(action, env) if action_transform else action
        obs, reward, terminated, _truncated, info = env.step(env_action)
        ep_reward += reward
        steps += 1
        if isinstance(info, dict):
            last_info = info
        agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
        if terminated:
            break
    return ep_reward, steps, last_info


def _check_early_stopping(
    ep_reward: float,
    best_reward: float,
    no_improve: int,
    patience: int,
    verbose: bool,
) -> tuple[float, int, bool]:
    """检查早停条件。

    Returns:
        (更新后的 best_reward, 更新后的 no_improve, 是否应停止训练)。
    """
    if ep_reward > best_reward:
        return ep_reward, 0, False
    new_no_improve = no_improve + 1
    if patience > 0 and new_no_improve >= patience:
        if verbose:
            print(f"早停：连续 {new_no_improve} 轮无改善，停止训练")
        return best_reward, new_no_improve, True
    return best_reward, new_no_improve, False


def _save_checkpoint(
    agent: PPOAgent,
    ckpt_dir: Path,
    prefix: str,
    ep: int,
    checkpoint_every: int,
) -> None:
    """按周期保存训练检查点。"""
    if (ep + 1) % checkpoint_every == 0:
        agent.save(ckpt_dir / f"{prefix}_ep{ep + 1}.json")


def _sync_lr_schedule(config: TrainConfig, agent: PPOAgent) -> None:
    """同步 TrainConfig 学习率调度到 PPOConfig（单一调度入口）。

    来源: Stable-Baselines3 PPO.learn() 内部 total_timesteps 调度
          https://stable-baselines3.readthedocs.io/
    """
    config.ppo.lr_schedule = config.lr_schedule
    config.ppo.total_steps = config.num_episodes
    agent.config.lr_schedule = config.lr_schedule
    agent.config.total_steps = config.num_episodes


def _finalize_training(
    agent: PPOAgent, logs: list[dict], ckpt_dir: Path, prefix: str
) -> None:
    """保存最终 checkpoint 与训练日志。"""
    agent.save(ckpt_dir / f"{prefix}_final.json")
    log_path = ckpt_dir / f"{prefix}_log.json"
    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def _log_progress(log: dict, log_every: int, verbose: bool, prefix: str) -> None:
    """打印轮次进度日志。"""
    if verbose and (log["episode"] % log_every == 0):
        print(
            f"[{prefix}] ep {log['episode']:3d} | reward {log['ep_reward']:8.3f} | "
            f"policy {log.get('policy_loss', 0):.4f} | "
            f"value {log.get('value_loss', 0):.4f} | "
            f"lr {log.get('lr', 0):.6f}"
        )


def train_ppo(
    agent: PPOAgent,
    env,
    config: TrainConfig | None = None,
    obs_dim: int | None = None,
    action_transform: ActionTransform | None = None,
    prefix: str = "ppo",
    verbose: bool = True,
    logger: TrainingLogger | None = None,
) -> tuple[PPOAgent, list[dict]]:
    """单 env PPO 训练循环（每轮 reset 同一 env）。

    Args:
        agent: PPO 智能体。
        env: Gymnasium 协议 env（reset/step）。
        config: 训练配置。
        obs_dim: 观测维度（None 时从 env 推断）。
        action_transform: 连续→env 动作映射回调（None=连续动作直传）。
        prefix: checkpoint/log 文件前缀。
        verbose: 是否打印进度。
        logger: 可选 TrainingLogger（记录 reward/HPWL/loss/lr 到 JSONL+TB）。

    Returns:
        (训练后的 agent, 训练日志列表)。
    """
    config = config or TrainConfig()
    np.random.seed(config.seed)
    _sync_lr_schedule(config, agent)
    obs_dim = obs_dim if obs_dim is not None else infer_obs_dim(env)
    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    logs: list[dict] = []
    best_reward = -float("inf")
    no_improve = 0
    for ep in range(config.num_episodes):
        obs, _info = env.reset()
        ep_reward, _steps, last_info = _collect_rollout(
            agent, env, obs, obs_dim, config.rollout_steps, action_transform
        )
        metrics = agent.update(last_value=0.0)
        hpwl = last_info.get("hpwl_um") if last_info else None
        log = {"episode": ep, "ep_reward": ep_reward, "lr": agent.optimizer.lr, **metrics}
        if hpwl is not None:
            log["hpwl_um"] = float(hpwl)
        logs.append(log)
        _log_progress(log, config.log_every, verbose, prefix)
        if logger is not None:
            logger.log_episode(ep, ep_reward, hpwl=hpwl, metrics=metrics,
                               lr=agent.optimizer.lr)
        best_reward, no_improve, should_stop = _check_early_stopping(
            ep_reward, best_reward, no_improve, config.early_stop_patience, verbose
        )
        if should_stop:
            break
        _save_checkpoint(agent, ckpt_dir, prefix, ep, config.checkpoint_every)

    _finalize_training(agent, logs, ckpt_dir, prefix)
    if logger is not None:
        logger.flush()
    return agent, logs


def train_with_env_factory(
    agent: PPOAgent,
    env_factory: Callable[[int], object],
    config: TrainConfig | None = None,
    obs_dim: int | None = None,
    action_transform: ActionTransform | None = None,
    prefix: str = "ppo",
    verbose: bool = True,
    logger: TrainingLogger | None = None,
) -> tuple[PPOAgent, list[dict]]:
    """多 env PPO 训练循环（每轮由 env_factory(ep) 创建新 env）。

    适用于每轮换网表的布局/布线训练。``env_factory(ep)`` 须返回遵循
    Gymnasium 协议的 env。

    Args:
        agent: PPO 智能体。
        env_factory: 工厂回调 ``env_factory(ep) -> env``。
        config: 训练配置。
        obs_dim: 观测维度（None 时从 env_factory(0) 推断）。
        action_transform: 连续→env 动作映射回调。
        prefix: checkpoint/log 文件前缀。
        verbose: 是否打印进度。
        logger: 可选 TrainingLogger（记录 reward/HPWL/loss/lr 到 JSONL+TB）。

    Returns:
        (训练后的 agent, 训练日志列表)。
    """
    config = config or TrainConfig()
    np.random.seed(config.seed)
    _sync_lr_schedule(config, agent)
    if obs_dim is None:
        obs_dim = infer_obs_dim(env_factory(0))
    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    logs: list[dict] = []
    best_reward = -float("inf")
    no_improve = 0
    for ep in range(config.num_episodes):
        env = env_factory(ep)
        obs, _info = env.reset()
        ep_reward, _steps, last_info = _collect_rollout(
            agent, env, obs, obs_dim, config.rollout_steps, action_transform
        )
        metrics = agent.update(last_value=0.0)
        hpwl = last_info.get("hpwl_um") if last_info else None
        log = {
            "episode": ep,
            "netlist": getattr(env, "name", f"env_{ep}"),
            "ep_reward": ep_reward,
            "lr": agent.optimizer.lr,
            **metrics,
        }
        if hpwl is not None:
            log["hpwl_um"] = float(hpwl)
        logs.append(log)
        _log_progress(log, config.log_every, verbose, prefix)
        if logger is not None:
            logger.log_episode(ep, ep_reward, hpwl=hpwl, metrics=metrics,
                               lr=agent.optimizer.lr)
        best_reward, no_improve, should_stop = _check_early_stopping(
            ep_reward, best_reward, no_improve, config.early_stop_patience, verbose
        )
        if should_stop:
            break
        _save_checkpoint(agent, ckpt_dir, prefix, ep, config.checkpoint_every)

    _finalize_training(agent, logs, ckpt_dir, prefix)
    if logger is not None:
        logger.flush()
    return agent, logs


def load_agent(
    path: str | Path, obs_dim: int, action_dim: int, hidden_dim: int = 64
) -> PPOAgent:
    """从检查点加载智能体（断点续训）。"""
    agent = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, hidden_dim=hidden_dim)
    agent.load(path)
    return agent


__all__ = [
    "TrainConfig",
    "ActionTransform",
    "train_ppo",
    "train_with_env_factory",
    "load_agent",
    "lr_scale",
    "obs_to_vector",
    "infer_obs_dim",
    "pad_obs",
    "discretize_floorplan_action",
]
