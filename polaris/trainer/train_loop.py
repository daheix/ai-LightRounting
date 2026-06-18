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
from polaris.trainer.ppo import PPOAgent, PPOConfig, Transition


@dataclass
class TrainConfig:
    """训练配置。

    Attributes:
        ppo: PPO 超参数。
        dataset: 数据集配置。
        num_episodes: 训练轮数。
        rollout_steps: 每轮采样步数。
        canvas_w: 画布宽（μm）。
        canvas_h: 画布高（μm）。
        grid_size: 网格大小（μm）。
        hidden_dim: 隐藏层维度。
        checkpoint_dir: 检查点目录。
        checkpoint_every: 每多少轮保存检查点。
        log_every: 每多少轮打印日志。
        seed: 随机种子。
        early_stop_patience: 早停耐心值（连续多少轮无改善则停止，0=禁用）。
        lr_schedule: 学习率调度（"constant"=恒定，"linear"=线性衰减）。
    """

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
    early_stop_patience: int = 0  # 0=禁用早停
    lr_schedule: str = "constant"  # "constant" 或 "linear"


def _lr_scale(ep: int, total: int, schedule: str) -> float:
    """计算当前轮的学习率缩放因子。

    Args:
        ep: 当前轮次（0-based）。
        total: 总轮数。
        schedule: "constant" 返回 1.0；"linear" 从 1.0 线性衰减到 0。

    Returns:
        学习率缩放因子（0.0~1.0）。
    """
    if schedule == "linear":
        if total <= 0:
            return 1.0
        return max(0.0, 1.0 - ep / total)
    return 1.0


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


def _pad_obs(obs_vec: np.ndarray, obs_dim: int) -> np.ndarray:
    """将观测向量 pad/truncate 到固定维度（适配不同网表器件数）。"""
    if obs_vec.shape[0] < obs_dim:
        return np.pad(obs_vec, (0, obs_dim - obs_vec.shape[0]))
    if obs_vec.shape[0] > obs_dim:
        return obs_vec[:obs_dim]
    return obs_vec


def _apply_lr_scale(agent: PPOAgent, lr_scale: float, base_lr: float) -> None:
    """根据缩放因子调整优化器学习率（线性衰减等）。"""
    if lr_scale < 1.0 and hasattr(agent, "optimizer"):
        agent.optimizer.lr = base_lr * lr_scale


def _discretize_floorplan_action(
    action: np.ndarray, env: FloorplanEnv, action_dim: int
) -> np.ndarray:
    """将连续动作离散化到 MultiDiscrete 网格动作 (gx, gy, rot)。"""
    n_gw = env.grid_w
    n_gh = env.grid_h
    gx = int(np.clip(action[0], 0, 1) * (n_gw - 1)) if action_dim >= 1 else 0
    gy = int(np.clip(action[1] if action_dim > 1 else 0, 0, 1) * (n_gh - 1))
    rot = int(np.clip(action[2] if action_dim > 2 else 0, 0, 1) * 3)
    return np.array([gx, gy, rot])


def _collect_floorplan_rollout(
    agent: PPOAgent,
    env: FloorplanEnv,
    obs,
    dims: tuple[int, int],
    rollout_steps: int,
) -> tuple[float, int]:
    """采集布局 rollout，将连续动作离散化后与环境交互，返回 (ep_reward, steps)。"""
    obs_dim, action_dim = dims
    ep_reward = 0.0
    steps = 0
    for _ in range(rollout_steps):
        obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
        action, logprob, value = agent.get_action(obs_vec)
        disc_action = _discretize_floorplan_action(action, env, action_dim)
        obs, reward, terminated, _, _ = env.step(disc_action)
        ep_reward += reward
        steps += 1
        agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
        if terminated:
            break
    return ep_reward, steps


def _collect_routing_rollout(
    agent: PPOAgent,
    env,
    obs,
    obs_dim: int,
    rollout_steps: int,
) -> tuple[float, int]:
    """采集布线 rollout，直接使用连续动作与环境交互，返回 (ep_reward, steps)。"""
    ep_reward = 0.0
    steps = 0
    for _ in range(rollout_steps):
        obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
        action, logprob, value = agent.get_action(obs_vec)
        obs, reward, terminated, _, _ = env.step(action)
        ep_reward += reward
        steps += 1
        agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
        if terminated:
            break
    return ep_reward, steps


def _log_floorplan_progress(log: dict, log_every: int, verbose: bool) -> None:
    """打印布局训练的轮次进度日志。"""
    if verbose and (log["episode"] % log_every == 0):
        print(
            f"ep {log['episode']:3d} | reward {log['ep_reward']:8.3f} | "
            f"policy {log['policy_loss']:.4f} | "
            f"value {log['value_loss']:.4f} | "
            f"lr_scale {log['lr_scale']:.3f}"
        )


def _log_routing_progress(log: dict, log_every: int, verbose: bool) -> None:
    """打印布线训练的轮次进度日志。"""
    if verbose and (log["episode"] % log_every == 0):
        print(
            f"ep {log['episode']:3d} | reward {log['ep_reward']:8.3f} | "
            f"loss_db {log.get('total_loss_db', 0):.3f} | "
            f"len {log.get('total_length_um', 0):.1f}"
        )


def _check_early_stopping(
    ep_reward: float,
    best_reward: float,
    no_improve: int,
    patience: int,
    verbose: bool,
) -> tuple[float, int, bool]:
    """检查早停条件。

    Args:
        ep_reward: 当前轮奖励。
        best_reward: 历史最佳奖励。
        no_improve: 连续无改善轮数。
        patience: 早停耐心值（0=禁用）。
        verbose: 是否打印早停信息。

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


def _build_routing_env(net, devices, config: TrainConfig):
    """构建布线环境（先随机布局再创建 RoutingEnv）。

    来源: 先布局再布线的两阶段流程，参考 DREAMPlace 联合优化思路。
    """
    from polaris.router.routing_env import RoutingEnv

    fp = FloorplanEnv(
        net,
        devices,
        canvas_w=config.canvas_w,
        canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    fp.reset()
    for _ in range(len(devices)):
        fp.step(fp.action_space.sample())
    return RoutingEnv(
        net,
        fp.state.placements,
        canvas_w=config.canvas_w,
        canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )


def _init_floorplan_training(
    config: TrainConfig,
    agent: PPOAgent | None,
) -> tuple[PPOAgent, list, tuple[int, int], Path]:
    """初始化布局训练：生成数据集、推断维度、创建智能体与检查点目录。"""
    np.random.seed(config.seed)
    netlists = generate_dataset(config.dataset)
    net0, devices0, _ = load_netlist(netlists[0])
    env0 = FloorplanEnv(
        net0,
        devices0,
        canvas_w=config.canvas_w,
        canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    obs_dim = _infer_obs_dim(env0)
    action_dim = int(np.prod(env0.action_space.shape))
    dims = (obs_dim, action_dim)
    if agent is None:
        agent = PPOAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=config.ppo,
            hidden_dim=config.hidden_dim,
        )
    ckpt_dir = Path(config.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    return agent, netlists, dims, ckpt_dir


def _run_floorplan_episode(
    agent: PPOAgent,
    config: TrainConfig,
    netlists: list,
    ep: int,
    dims: tuple[int, int],
) -> tuple[dict, float]:
    """执行单轮布局训练，返回 (日志字典, 本轮奖励)。"""
    lr_scale = _lr_scale(ep, config.num_episodes, config.lr_schedule)
    _apply_lr_scale(agent, lr_scale, config.ppo.lr)
    nl = netlists[ep % len(netlists)]
    net, devices, _ = load_netlist(nl)
    env = FloorplanEnv(
        net,
        devices,
        canvas_w=config.canvas_w,
        canvas_h=config.canvas_h,
        grid_size=config.grid_size,
    )
    obs, _ = env.reset()
    ep_reward, steps = _collect_floorplan_rollout(agent, env, obs, dims, config.rollout_steps)
    metrics = agent.update(last_value=0.0)
    log = {
        "episode": ep,
        "netlist": nl["name"],
        "ep_reward": ep_reward,
        "steps": steps,
        "lr_scale": lr_scale,
        **metrics,
    }
    return log, ep_reward


def _run_routing_episode(
    agent: PPOAgent,
    config: TrainConfig,
    netlists: list,
    ep: int,
    obs_dim: int,
) -> dict:
    """执行单轮布线训练，返回日志字典。"""
    nl = netlists[ep % len(netlists)]
    net, devices, _ = load_netlist(nl)
    env = _build_routing_env(net, devices, config)
    obs, _ = env.reset()
    ep_reward, steps = _collect_routing_rollout(agent, env, obs, obs_dim, config.rollout_steps)
    metrics = agent.update(last_value=0.0)
    return {
        "episode": ep,
        "netlist": nl["name"],
        "ep_reward": ep_reward,
        "steps": steps,
        **metrics,
        **env.total_metrics(),
    }


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
    agent, netlists, dims, ckpt_dir = _init_floorplan_training(config, agent)
    logs: list[dict] = []
    best_reward = -float("inf")
    no_improve = 0

    for ep in range(config.num_episodes):
        log, ep_reward = _run_floorplan_episode(agent, config, netlists, ep, dims)
        logs.append(log)
        _log_floorplan_progress(log, config.log_every, verbose)
        best_reward, no_improve, should_stop = _check_early_stopping(
            ep_reward, best_reward, no_improve, config.early_stop_patience, verbose
        )
        if should_stop:
            break
        _save_checkpoint(agent, ckpt_dir, "floorplan", ep, config.checkpoint_every)

    agent.save(ckpt_dir / "floorplan_final.json")
    log_path = ckpt_dir / "floorplan_log.json"
    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    return agent, logs


def train_routing(
    config: TrainConfig | None = None,
    agent: PPOAgent | None = None,
    verbose: bool = True,
) -> tuple[PPOAgent, list[dict]]:
    """训练布线 PPO 智能体（先布局再布线）。"""
    config = config or TrainConfig()
    np.random.seed(config.seed)
    netlists = generate_dataset(config.dataset)
    logs: list[dict] = []

    net0, devices0, _ = load_netlist(netlists[0])
    env0 = _build_routing_env(net0, devices0, config)
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
        log = _run_routing_episode(agent, config, netlists, ep, obs_dim)
        logs.append(log)
        _log_routing_progress(log, config.log_every, verbose)
        _save_checkpoint(agent, ckpt_dir, "routing", ep, config.checkpoint_every)

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
