#!/usr/bin/env python3
"""持续RL训练脚本 — 2M轮一轮，跑完继续下一轮。

关键改进:
- 离散PPO (Categorical分布) 替代连续PPO (Gaussian分布)
  MultiDiscrete([10,10,4]) 展平为 400 个离散动作
- Agent 持久化：启动时创建一次，跨所有批次复用
- 增量奖励：step()返回边际reward，PPO能学到每步贡献
- 断点续训 + 每5分钟自动git commit

来源:
- Google Nature 2021: https://www.nature.com/articles/s41586-021-03544-w
- ChipFoundryServices: https://www.chipfoundryservices.com/topic/reinforcement-learning-chip-optimization
"""

from __future__ import annotations

import gc
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
from polaris.engine.netlist import load_netlist
from polaris.router.routing_env import RoutingEnv
from polaris.trainer.dataset import DatasetConfig, generate_dataset
from polaris.trainer.reward_shaping import ExpertRewardShaper
from polaris.trainer.train_loop import (
    _infer_obs_dim,
    _obs_to_vector,
    _pad_obs,
)

try:
    from polaris.trainer.ppo_torch import (
        PPOAgentDiscrete as _PPOAgent,
    )
    from polaris.trainer.ppo_torch import (
        PPOConfig as _PPOConfig,
    )
    from polaris.trainer.ppo_torch import (
        Transition,
    )

    USE_TORCH = True
    print("[加速] 使用 PyTorch 离散PPO (Categorical)", flush=True)
except ImportError:
    from polaris.trainer.ppo import PPOAgent as _PPOAgent, PPOConfig as _PPOConfig, Transition  # noqa: I001

    USE_TORCH = False
    print("[模式] 使用 NumPy PPO", flush=True)

# ── 配置 ──────────────────────────────────────────────
EPISODES_PER_ROUND = 2_000_000
BATCH_SIZE = 500
SAVE_DIR = Path("checkpoints/rl_2m")
PROGRESS_FILE = SAVE_DIR / "progress.json"
COMMIT_INTERVAL = 300
CKPT_EVERY = 1000

HIDDEN_DIM = 128
LR = 3e-4
ROLLOUT_STEPS = 32
UPDATE_EVERY = 16  # 积累16个episode再更新PPO（保证buffer>=128样本）
CANVAS_W = 200.0
CANVAS_H = 200.0
GRID_SIZE = 20.0  # 10x10网格

PPO_CONFIG = _PPOConfig(
    lr=LR,
    gamma=0.99,
    gae_lambda=0.95,
    clip_eps=0.2,
    ent_coef=0.1,
    vf_coef=0.5,
    max_grad_norm=0.5,
    n_epochs=4,
    batch_size=64,  # 降低到64，适配小buffer
    clip_vf=0,
    lr_schedule="cosine",
    total_steps=EPISODES_PER_ROUND,
)

DATASET_CFG = DatasetConfig(
    num_netlists=50,
    min_devices=3,
    max_devices=12,
    seed=42,
)

# 专家知识奖励塑形器（ICLR'26 Expertise-Enhanced RL）
# 来源: https://openreview.net/forum?id=yqvNwfxRR6
# 注入光子学领域知识：端口对齐/弯曲半径/交叉/拥塞/热串扰
EXPERT_SHAPER = ExpertRewardShaper()

# 布局环境配置（注入专家奖励塑形器）
PLACE_ENV_CONFIG = FloorplanEnvConfig(
    canvas_w=CANVAS_W,
    canvas_h=CANVAS_H,
    grid_size=GRID_SIZE,
    expert_shaper=EXPERT_SHAPER,
)


def _flatten_multidiscrete(action_space) -> int:
    """MultiDiscrete([10,10,4]) → 10*10*4 = 400."""
    return int(np.prod(action_space.nvec))


def _flat_to_multidiscrete(flat_action: int, action_space) -> np.ndarray:
    """flat_action=243, MultiDiscrete([10,10,4]) → [2,4,3]."""
    nvec = action_space.nvec
    result = np.zeros(len(nvec), dtype=np.int64)
    remaining = flat_action
    for i in range(len(nvec) - 1, -1, -1):
        result[i] = remaining % nvec[i]
        remaining = remaining // nvec[i]
    return result


_DEFAULT_PROGRESS = {
    "total_episodes_done": 0,
    "placement_episodes": 0,
    "routing_episodes": 0,
    "best_placement_reward": -1e9,
    "best_routing_reward": -1e9,
    "total_training_seconds": 0.0,
    "batches_completed": 0,
    "last_commit_time": 0,
    "recent_rewards": [],
    "rounds_completed": 0,
}


def load_progress() -> dict:
    """加载训练进度（异常容错：文件损坏时返回默认值，不崩溃）。"""
    if not PROGRESS_FILE.exists():
        return dict(_DEFAULT_PROGRESS)
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        # 合并默认字段，防止旧版本缺字段
        merged = dict(_DEFAULT_PROGRESS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [警告] progress.json 损坏，使用默认值: {e}", flush=True)
        return dict(_DEFAULT_PROGRESS)


def save_progress(prog: dict) -> None:
    """保存训练进度（原子写入：先写临时文件再rename，防止崩溃损坏）。"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    if len(prog["recent_rewards"]) > 500:
        prog["recent_rewards"] = prog["recent_rewards"][-500:]
    tmp_path = PROGRESS_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(prog, indent=2), encoding="utf-8")
    tmp_path.replace(PROGRESS_FILE)  # 原子rename


def git_commit(prog: dict) -> None:
    """自动git提交。"""
    now = time.time()
    if now - prog["last_commit_time"] < COMMIT_INTERVAL:
        return
    try:
        files = [
            "checkpoints/rl_2m/progress.json",
            "checkpoints/rl_2m/placement_agent.json",
            "checkpoints/rl_2m/routing_agent.json",
        ]
        for f in files:
            if Path(f).exists():
                subprocess.run(["git", "add", f], capture_output=True, timeout=10)
        ep = prog["total_episodes_done"]
        rnd = prog.get("rounds_completed", 0)
        subprocess.run(
            ["git", "commit", "-m", f"chore: RL训练 R{rnd} {ep:,}ep"],
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True,
            timeout=60,
        )
        prog["last_commit_time"] = now
        print(f"  [git] 已提交: R{rnd} {ep:,}ep", flush=True)
    except Exception as e:
        print(f"  [git] 失败: {e}", flush=True)


def _try_load_agent(ckpt_path: Path, obs_dim: int, n_actions: int) -> _PPOAgent | None:
    """尝试从 checkpoint 加载 agent。

    Bug 修复: 原调用 _PPOAgent.load(path, obs_dim, n_actions, config, hidden_dim) 传 5 参数，
    但 PPOAgentDiscrete.load 签名为 load(path, config, spec)，导致续训失败。
    修复: 用 AgentSpec 打包 obs_dim/n_actions/hidden_dim，匹配正确签名。
    """
    if not ckpt_path.exists():
        return None
    try:
        from polaris.trainer.ppo_buffers import AgentSpec

        spec = AgentSpec(obs_dim=obs_dim, n_actions=n_actions, hidden_dim=HIDDEN_DIM)
        agent = _PPOAgent.load(ckpt_path, PPO_CONFIG, spec)
        print(f"  [续训] 已加载 {ckpt_path}", flush=True)
        return agent
    except Exception as e:
        print(f"  [续训] 加载失败，重新创建: {e}", flush=True)
        return None


def _try_load_routing_agent(ckpt_path: Path, obs_dim: int, action_dim: int):
    """尝试从 checkpoint 加载布线 agent（连续 PPO）。

    Bug 修复: 原代码根本未尝试加载 routing_ckpt，每次重启都从零开始。
    修复: 新增加载逻辑，匹配 PPOAgent.load(path) 签名。
    """
    if not ckpt_path.exists():
        return None
    try:
        from polaris.trainer.ppo_torch import PPOAgent as _PPOAgentCont

        agent = _PPOAgentCont(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        agent.load(ckpt_path)
        print(f"  [续训] 已加载 {ckpt_path}", flush=True)
        return agent
    except Exception as e:
        print(f"  [续训] 布线 agent 加载失败，重新创建: {e}", flush=True)
        return None


def _infer_dims() -> tuple[int, int, int, list]:
    """推断维度，返回 (obs_dim, n_actions_place, obs_dim_route, netlists)."""
    netlists = generate_dataset(DATASET_CFG)
    net0, devices0, _ = load_netlist(netlists[0])

    env0 = FloorplanEnv(net0, devices0, config=PLACE_ENV_CONFIG)
    obs_dim = _infer_obs_dim(env0)
    n_actions = _flatten_multidiscrete(env0.action_space)
    print(f"  布局: obs_dim={obs_dim}, n_actions={n_actions}", flush=True)
    print("  [专家奖励] ExpertRewardShaper 已启用 (ICLR'26)", flush=True)

    fp = FloorplanEnv(net0, devices0, config=PLACE_ENV_CONFIG)
    fp.reset()
    for _ in range(len(devices0)):
        fp.step(fp.action_space.sample())
    rt_env = RoutingEnv(
        net0,
        fp.state.placements,
        canvas_w=CANVAS_W,
        canvas_h=CANVAS_H,
        grid_size=GRID_SIZE,
    )
    obs_dim_route = _infer_obs_dim(rt_env)

    return obs_dim, n_actions, obs_dim_route, netlists


def run_placement_batch(
    agent: _PPOAgent,
    netlists: list,
    batch_episodes: int,
    obs_dim: int,
) -> dict:
    """运行一批布局训练（离散PPO + Agent持久化 + 多episode积累更新）。"""
    rewards = []
    plosses = []
    vlosses = []
    ep_count = 0

    for ep in range(batch_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        env = FloorplanEnv(net, devices, config=PLACE_ENV_CONFIG)
        obs, _ = env.reset()
        ep_reward = 0.0
        for _ in range(ROLLOUT_STEPS):
            obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
            flat_action, logprob, value = agent.get_action(obs_vec)
            disc_action = _flat_to_multidiscrete(flat_action, env.action_space)
            obs, reward, done, _, _ = env.step(disc_action)
            ep_reward += reward
            agent.store(Transition(obs_vec, flat_action, reward, logprob, value, done))
            if done:
                break
        rewards.append(ep_reward)
        ep_count += 1
        # 积累 UPDATE_EVERY 个episode再更新（保证buffer有足够样本）
        if ep_count >= UPDATE_EVERY:
            metrics = agent.update(last_value=0.0)
            plosses.append(metrics.get("policy_loss", 0))
            vlosses.append(metrics.get("value_loss", 0))
            ep_count = 0

    # 处理剩余buffer
    if ep_count > 0:
        metrics = agent.update(last_value=0.0)
        plosses.append(metrics.get("policy_loss", 0))
        vlosses.append(metrics.get("value_loss", 0))

    return {
        "episodes": len(rewards),
        "best_reward": max(rewards) if rewards else -1e9,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0,
        "avg_policy_loss": sum(plosses) / len(plosses) if plosses else 0,
        "avg_value_loss": sum(vlosses) / len(vlosses) if vlosses else 0,
        "rewards": rewards,
    }


def run_routing_batch(
    agent,
    netlists: list,
    batch_episodes: int,
    obs_dim_route: int,
) -> dict:
    """运行一批布线训练（多episode积累更新）。"""
    rewards = []
    plosses = []
    ep_count = 0

    for ep in range(batch_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        fp = FloorplanEnv(net, devices, config=PLACE_ENV_CONFIG)
        fp.reset()
        for _ in range(len(devices)):
            fp.step(fp.action_space.sample())
        rt_env = RoutingEnv(
            net,
            fp.state.placements,
            canvas_w=CANVAS_W,
            canvas_h=CANVAS_H,
            grid_size=GRID_SIZE,
        )
        obs, _ = rt_env.reset()
        ep_reward = 0.0
        for _ in range(ROLLOUT_STEPS):
            obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim_route)
            action, logprob, value = agent.get_action(obs_vec)
            obs, reward, done, _, _ = rt_env.step(action)
            ep_reward += reward
            agent.store(Transition(obs_vec, action, reward, logprob, value, done))
            if done:
                break
        rewards.append(ep_reward)
        ep_count += 1
        if ep_count >= UPDATE_EVERY:
            metrics = agent.update(last_value=0.0)
            plosses.append(metrics.get("policy_loss", 0))
            ep_count = 0

    if ep_count > 0:
        metrics = agent.update(last_value=0.0)
        plosses.append(metrics.get("policy_loss", 0))

    return {
        "episodes": len(rewards),
        "best_reward": max(rewards) if rewards else -1e9,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0,
        "avg_policy_loss": sum(plosses) / len(plosses) if plosses else 0,
        "rewards": rewards,
    }


def main() -> None:
    """主训练循环 — 2M轮一轮，跑完继续。"""
    print("=" * 60, flush=True)
    print("PoLaRIS 持续RL训练（离散PPO版）", flush=True)
    print(f"每轮: {EPISODES_PER_ROUND:,} episodes, 跑完继续", flush=True)
    print(f"批次: {BATCH_SIZE} ep/batch, 隐藏层: {HIDDEN_DIM}", flush=True)
    print("=" * 60, flush=True)

    prog = load_progress()
    t0 = time.time()

    print("\n[初始化] 推断维度...", flush=True)
    obs_dim, n_actions, obs_dim_route, netlists = _infer_dims()

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # 布局 agent（离散PPO）
    placement_ckpt = SAVE_DIR / "placement_agent.json"
    placement_agent = _try_load_agent(placement_ckpt, obs_dim, n_actions)
    if placement_agent is None:
        placement_agent = _PPOAgent(
            obs_dim=obs_dim,
            n_actions=n_actions,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        print("  [新建] placement_agent (离散PPO)", flush=True)

    # 布线 agent（连续PPO）
    from polaris.trainer.ppo_torch import PPOAgent as _PPOAgentCont

    routing_ckpt = SAVE_DIR / "routing_agent.json"
    route_action_dim = 3
    routing_agent = _try_load_routing_agent(routing_ckpt, obs_dim_route, route_action_dim)
    if routing_agent is None:
        routing_agent = _PPOAgentCont(
            obs_dim=obs_dim_route,
            action_dim=route_action_dim,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        print("  [新建] routing_agent (连续PPO)", flush=True)

    last_ckpt_ep = 0

    while True:
        round_num = prog.get("rounds_completed", 0) + 1
        round_ep = 0

        print(f"\n{'#' * 60}", flush=True)
        print(f"# 第 {round_num} 轮训练开始 (总: {prog['total_episodes_done']:,}ep)", flush=True)
        print(f"{'#' * 60}", flush=True)

        while round_ep < EPISODES_PER_ROUND:
            batch_num = prog["batches_completed"] + 1
            remaining = EPISODES_PER_ROUND - round_ep
            this_batch = min(BATCH_SIZE, remaining)

            print(
                f"\n[批次#{batch_num}] 布局 {this_batch}ep | "
                f"R{round_num} {round_ep:,}/{EPISODES_PER_ROUND:,} | "
                f"总 {prog['total_episodes_done']:,}ep",
                flush=True,
            )

            bt0 = time.time()
            place_result = run_placement_batch(placement_agent, netlists, this_batch, obs_dim)
            bt_sec = time.time() - bt0

            prog["placement_episodes"] += place_result["episodes"]
            prog["total_episodes_done"] += place_result["episodes"]
            round_ep += place_result["episodes"]
            if place_result["best_reward"] > prog["best_placement_reward"]:
                prog["best_placement_reward"] = place_result["best_reward"]

            for r in place_result["rewards"][-10:]:
                prog["recent_rewards"].append(
                    {
                        "ep": prog["total_episodes_done"],
                        "phase": "placement",
                        "reward": round(r, 4),
                    },
                )

            print(
                f"  布局: avg={place_result['avg_reward']:.2f}, "
                f"best={place_result['best_reward']:.2f}, "
                f"ploss={place_result['avg_policy_loss']:.4f}, "
                f"vloss={place_result['avg_value_loss']:.2f}, "
                f"{bt_sec:.1f}s",
                flush=True,
            )

            if batch_num % 20 == 0:
                rt0 = time.time()
                route_result = run_routing_batch(routing_agent, netlists, this_batch, obs_dim_route)
                rt_sec = time.time() - rt0

                prog["routing_episodes"] += route_result["episodes"]
                if route_result["best_reward"] > prog["best_routing_reward"]:
                    prog["best_routing_reward"] = route_result["best_reward"]

                for r in route_result["rewards"][-10:]:
                    prog["recent_rewards"].append(
                        {
                            "ep": prog["total_episodes_done"],
                            "phase": "routing",
                            "reward": round(r, 4),
                        },
                    )

                print(
                    f"  布线: avg={route_result['avg_reward']:.2f}, "
                    f"best={route_result['best_reward']:.2f}, "
                    f"{rt_sec:.1f}s",
                    flush=True,
                )

            total_ep = prog["total_episodes_done"]
            if total_ep - last_ckpt_ep >= CKPT_EVERY:
                placement_agent.save(str(placement_ckpt))
                routing_agent.save(str(routing_ckpt))
                last_ckpt_ep = total_ep
                print(f"  [ckpt] 已保存 (ep={total_ep:,})", flush=True)

            prog["batches_completed"] = batch_num
            prog["total_training_seconds"] = time.time() - t0
            save_progress(prog)
            git_commit(prog)

            elapsed = time.time() - t0
            eps_done = prog["total_episodes_done"]
            if eps_done > 0:
                eps_per_sec = eps_done / elapsed
                print(f"  速度: {eps_per_sec:.1f} ep/s | 总时间: {elapsed / 3600:.1f}h", flush=True)

        prog["rounds_completed"] = round_num
        placement_agent.save(str(placement_ckpt))
        routing_agent.save(str(routing_ckpt))
        save_progress(prog)

        print(f"\n{'=' * 60}", flush=True)
        print(f"第 {round_num} 轮完成！ {round_ep:,}ep", flush=True)
        print(
            f"布局best: {prog['best_placement_reward']:.3f} | "
            f"布线best: {prog['best_routing_reward']:.3f}",
            flush=True,
        )
        print(f"自动开始第 {round_num + 1} 轮...", flush=True)
        print(f"{'=' * 60}", flush=True)

        del netlists
        gc.collect()
        netlists = generate_dataset(DATASET_CFG)


if __name__ == "__main__":
    main()
