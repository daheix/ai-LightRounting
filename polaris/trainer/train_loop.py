"""训练循环（Task 15）。

PPO 训练循环：rollout 采集 → GAE 优势估计 → 多 epoch 小批量更新 →
指标记录（reward/loss/coverage/congestion）→ 断点续训（checkpoint）。

方法参考：
- Stable-Baselines3 ``PPO.learn()`` 训练循环
  来源: https://stable-baselines3.readthedocs.io/
- CleanRL ``ppo.py`` 单文件训练循环
  来源: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.trainer.dataset import DatasetConfig, generate_dataset
from polaris.trainer.ppo import PPOAgent, PPOConfig


@dataclass
class TrainConfig:
    """训练配置。"""

    ppo: PPOConfig = field(default_factory=PPOConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    num_episodes: int = 50
    rollout_steps: int = 64
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    hidden_dim: int = 64
    checkpoint_dir: str = "checkpoints"
    checkpoint_every: int = 10
    log_every: int = 1
    seed: int = 42


def _obs_to_vector(obs: dict) -> np.ndarray:
    """将 Gymnasium dict 观测展平为向量（供 PPO 使用）。"""
    parts = []
    for v in obs.values():
        arr = np.asarray(v, dtype=np.float64).flatten()
        parts.append(arr)
    return np.concatenate(parts)


def _infer_obs_dim(env) -> int:
    """推断观测向量维度。"""
    obs, _ = env.reset()
    return _obs_to_vector(obs).shape[0]


def train_floorplan(
    config: TrainConfig | None = None,
    agent: PPOAgent | None = None,
    verbose: bool = True,
) -> tuple[PPOAgent, list[dict]]:
    """训练布局 PPO 智能体。

    Args:
        config: 训练配置。
        agent: 预加载智能体（断点续训）。
        verbose: 是否打印进度。

    Returns:
        (训练后的 agent, 训练日志列表)。
    """
    config = config or TrainConfig()
    np.random.seed(config.seed)
    # 生成数据集
    netlists = generate_dataset(config.dataset)
    logs: list[dict] = []

    # 用第一个网表推断 obs/action 维度
    net0, devices0, _ = load_netlist(netlists[0])
    env0 = FloorplanEnv(
        net0, devices0,
        canvas_w=config.canvas_w, canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    obs_dim = _infer_obs_dim(env0)
    action_dim = int(np.prod(env0.action_space.shape))

    if agent is None:
        agent = PPOAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=config.ppo,
            hidden_dim=config.hidden_dim,
        )

    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    for ep in range(config.num_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        env = FloorplanEnv(
            net, devices,
            canvas_w=config.canvas_w, canvas_h=config.canvas_h,
            grid_size=config.grid_size,
        )
        obs, _ = env.reset()
        ep_reward = 0.0
        steps = 0
        for step in range(config.rollout_steps):
            obs_vec = _obs_to_vector(obs)
            # 适配维度（不同网表器件数不同，pad/truncate）
            if obs_vec.shape[0] < obs_dim:
                obs_vec = np.pad(obs_vec, (0, obs_dim - obs_vec.shape[0]))
            elif obs_vec.shape[0] > obs_dim:
                obs_vec = obs_vec[:obs_dim]
            action, logprob, value = agent.get_action(obs_vec)
            # 将连续动作离散化到 MultiDiscrete
            n_gw = env.grid_w
            n_gh = env.grid_h
            gx = int(np.clip(action[0], 0, 1) * (n_gw - 1)) if action_dim >= 1 else 0
            gy = int(np.clip(action[1] if action_dim > 1 else 0, 0, 1) * (n_gh - 1))
            rot = int(np.clip(action[2] if action_dim > 2 else 0, 0, 1) * 3)
            disc_action = np.array([gx, gy, rot])
            obs, reward, terminated, _, _ = env.step(disc_action)
            ep_reward += reward
            steps += 1
            agent.store(obs_vec, action, reward, logprob, value, terminated)
            if terminated:
                break
        # PPO 更新
        metrics = agent.update(last_value=0.0)
        log = {
            "episode": ep,
            "netlist": nl["name"],
            "ep_reward": ep_reward,
            "steps": steps,
            **metrics,
        }
        logs.append(log)
        if verbose and (ep % config.log_every == 0):
            print(
                f"ep {ep:3d} | reward {ep_reward:8.3f} | "
                f"policy {metrics['policy_loss']:.4f} | "
                f"value {metrics['value_loss']:.4f}"
            )
        # checkpoint
        if (ep + 1) % config.checkpoint_every == 0:
            agent.save(ckpt_dir / f"floorplan_ep{ep + 1}.json")

    agent.save(ckpt_dir / "floorplan_final.json")
    # 保存日志
    log_path = ckpt_dir / "floorplan_log.json"
    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    return agent, logs


def train_routing(
    config: TrainConfig | None = None,
    agent: PPOAgent | None = None,
    verbose: bool = True,
) -> tuple[PPOAgent, list[dict]]:
    """训练布线 PPO 智能体（先布局再布线）。"""
    from polaris.router.routing_env import RoutingEnv

    config = config or TrainConfig()
    np.random.seed(config.seed)
    netlists = generate_dataset(config.dataset)
    logs: list[dict] = []

    net0, devices0, _ = load_netlist(netlists[0])
    fp0 = FloorplanEnv(
        net0, devices0,
        canvas_w=config.canvas_w, canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    fp0.reset()
    for _ in range(len(devices0)):
        fp0.step(fp0.action_space.sample())
    env0 = RoutingEnv(
        net0, fp0.state.placements,
        canvas_w=config.canvas_w, canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    obs_dim = _infer_obs_dim(env0)
    action_dim = 3  # (dx, dy, detour)

    if agent is None:
        agent = PPOAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=config.ppo,
            hidden_dim=config.hidden_dim,
        )

    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    for ep in range(config.num_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        # 先布局（随机放置）
        fp = FloorplanEnv(
            net, devices,
            canvas_w=config.canvas_w, canvas_h=config.canvas_h,
            grid_size=config.grid_size,
        )
        fp.reset()
        for _ in range(len(devices)):
            fp.step(fp.action_space.sample())
        env = RoutingEnv(
            net, fp.state.placements,
            canvas_w=config.canvas_w, canvas_h=config.canvas_h,
            grid_size=config.grid_size,
        )
        obs, _ = env.reset()
        ep_reward = 0.0
        steps = 0
        for step in range(config.rollout_steps):
            obs_vec = _obs_to_vector(obs)
            if obs_vec.shape[0] < obs_dim:
                obs_vec = np.pad(obs_vec, (0, obs_dim - obs_vec.shape[0]))
            elif obs_vec.shape[0] > obs_dim:
                obs_vec = obs_vec[:obs_dim]
            action, logprob, value = agent.get_action(obs_vec)
            obs, reward, terminated, _, _ = env.step(action)
            ep_reward += reward
            steps += 1
            agent.store(obs_vec, action, reward, logprob, value, terminated)
            if terminated:
                break
        metrics = agent.update(last_value=0.0)
        log = {
            "episode": ep,
            "netlist": nl["name"],
            "ep_reward": ep_reward,
            "steps": steps,
            **metrics,
            **env.total_metrics(),
        }
        logs.append(log)
        if verbose and (ep % config.log_every == 0):
            print(
                f"ep {ep:3d} | reward {ep_reward:8.3f} | "
                f"loss_db {log.get('total_loss_db', 0):.3f} | "
                f"len {log.get('total_length_um', 0):.1f}"
            )
        if (ep + 1) % config.checkpoint_every == 0:
            agent.save(ckpt_dir / f"routing_ep{ep + 1}.json")

    agent.save(ckpt_dir / "routing_final.json")
    log_path = ckpt_dir / "routing_log.json"
    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    return agent, logs


def load_agent(path: str | Path, obs_dim: int, action_dim: int, hidden_dim: int = 64) -> PPOAgent:
    """从检查点加载智能体（断点续训）。"""
    agent = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, hidden_dim=hidden_dim)
    agent.load(path)
    return agent


__all__ = [
    "TrainConfig",
    "train_floorplan",
    "train_routing",
    "load_agent",
]
