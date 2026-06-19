#!/usr/bin/env python3
"""持续RL训练脚本 — 2M轮一轮，跑完继续下一轮。

关键修复:
- PPOAgent 在启动时创建一次，跨所有批次持久化（修复每批重建导致知识丢失的 Bug）
- 断点续训：从 checkpoint 文件加载已有 agent
- 每 5 分钟自动保存 checkpoint + git commit

训练规模参考:
- Google Nature 2021: 6-24小时 TPU集群
  https://www.nature.com/articles/s41586-021-03544-w
- ChipFoundryServices: 10^4-10^6 episodes
  https://www.chipfoundryservices.com/topic/reinforcement-learning-chip-optimization
"""

from __future__ import annotations

import gc
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.router.routing_env import RoutingEnv
from polaris.trainer.dataset import DatasetConfig, generate_dataset
from polaris.trainer.train_loop import (
    _discretize_floorplan_action,
    _infer_obs_dim,
    _obs_to_vector,
    _pad_obs,
)

try:
    from polaris.trainer.ppo_torch import PPOAgent as _PPOAgent, PPOConfig as _PPOConfig, Transition  # noqa: I001

    USE_TORCH = True
    print("[加速] 使用 PyTorch PPO", flush=True)
except ImportError:
    from polaris.trainer.ppo import PPOAgent as _PPOAgent, PPOConfig as _PPOConfig, Transition  # noqa: I001

    USE_TORCH = False
    print("[模式] 使用 NumPy PPO", flush=True)

# ── 配置 ──────────────────────────────────────────────
EPISODES_PER_ROUND = 2_000_000  # 每轮2M
BATCH_SIZE = 200
SAVE_DIR = Path("checkpoints/rl_2m")
PROGRESS_FILE = SAVE_DIR / "progress.json"
COMMIT_INTERVAL = 300  # 5分钟
CKPT_EVERY = 1000  # 每1000 episode保存checkpoint

HIDDEN_DIM = 128  # torch 可高效处理 128 隐藏层
LR = 3e-4
ROLLOUT_STEPS = 16
CANVAS_W = 500.0
CANVAS_H = 500.0
GRID_SIZE = 10.0

PPO_CONFIG = _PPOConfig(
    lr=LR,
    gamma=0.99,
    gae_lambda=0.95,
    clip_eps=0.2,
    ent_coef=0.05,  # 增大熵系数（原0.01太小，探索不足）
    vf_coef=0.5,
    max_grad_norm=0.5,
    n_epochs=2,  # 减少更新轮数加速（原4→2，纯NumPy下4轮太慢）
    batch_size=64,
    clip_vf=0,  # 禁用 value clip（原 clip_vf=10 导致 value_loss=100）
    lr_schedule="cosine",
    total_steps=EPISODES_PER_ROUND,
)

DATASET_CFG = DatasetConfig(
    num_netlists=50,
    min_devices=3,
    max_devices=12,
    seed=42,
)


def load_progress() -> dict:
    """加载训练进度。"""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {
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


def save_progress(prog: dict) -> None:
    """保存训练进度。"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    if len(prog["recent_rewards"]) > 500:
        prog["recent_rewards"] = prog["recent_rewards"][-500:]
    PROGRESS_FILE.write_text(json.dumps(prog, indent=2), encoding="utf-8")


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


def _try_load_agent(ckpt_path: Path, obs_dim: int, action_dim: int) -> _PPOAgent | None:
    """尝试从 checkpoint 加载 agent，失败返回 None。"""
    if not ckpt_path.exists():
        return None
    try:
        agent = _PPOAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        agent.load(ckpt_path)
        print(f"  [续训] 已加载 {ckpt_path}", flush=True)
        return agent
    except Exception as e:
        print(f"  [续训] 加载失败，重新创建: {e}", flush=True)
        return None


def _infer_dims() -> tuple[int, int, int, list]:
    """推断布局和布线的 obs_dim/action_dim，返回 (obs_dim, action_dim, obs_dim_route, netlists)。"""
    netlists = generate_dataset(DATASET_CFG)
    net0, devices0, _ = load_netlist(netlists[0])

    # 布局维度
    env0 = FloorplanEnv(net0, devices0, canvas_w=CANVAS_W, canvas_h=CANVAS_H, grid_size=GRID_SIZE)
    obs_dim = _infer_obs_dim(env0)
    action_dim = int(np.prod(env0.action_space.shape))

    # 布线维度
    fp = FloorplanEnv(net0, devices0, canvas_w=CANVAS_W, canvas_h=CANVAS_H, grid_size=GRID_SIZE)
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

    return obs_dim, action_dim, obs_dim_route, netlists


def run_placement_batch(
    agent: _PPOAgent,
    netlists: list,
    batch_episodes: int,
    obs_dim: int,
    action_dim: int,
) -> dict:
    """运行一批布局训练（agent 持久化，不重建）。"""
    rewards = []
    plosses = []
    vlosses = []

    for ep in range(batch_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        env = FloorplanEnv(net, devices, canvas_w=CANVAS_W, canvas_h=CANVAS_H, grid_size=GRID_SIZE)
        obs, _ = env.reset()
        ep_reward = 0.0
        for _ in range(ROLLOUT_STEPS):
            obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
            action, logprob, value = agent.get_action(obs_vec)
            disc_action = _discretize_floorplan_action(action, env, action_dim)
            obs, reward, terminated, _, _ = env.step(disc_action)
            ep_reward += reward
            agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
            if terminated:
                break
        metrics = agent.update(last_value=0.0)
        rewards.append(ep_reward)
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
    agent: _PPOAgent,
    netlists: list,
    batch_episodes: int,
    obs_dim_route: int,
) -> dict:
    """运行一批布线训练（agent 持久化，不重建）。"""
    rewards = []
    plosses = []

    for ep in range(batch_episodes):
        nl = netlists[ep % len(netlists)]
        net, devices, _ = load_netlist(nl)
        # 先随机布局再创建布线环境
        fp = FloorplanEnv(net, devices, canvas_w=CANVAS_W, canvas_h=CANVAS_H, grid_size=GRID_SIZE)
        fp.reset()
        for _ in range(len(devices)):
            fp.step(fp.action_space.sample())
        rt_env = RoutingEnv(
            net, fp.state.placements, canvas_w=CANVAS_W, canvas_h=CANVAS_H, grid_size=GRID_SIZE
        )
        obs, _ = rt_env.reset()
        ep_reward = 0.0
        for _ in range(ROLLOUT_STEPS):
            obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim_route)
            action, logprob, value = agent.get_action(obs_vec)
            obs, reward, terminated, _, _ = rt_env.step(action)
            ep_reward += reward
            agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
            if terminated:
                break
        metrics = agent.update(last_value=0.0)
        rewards.append(ep_reward)
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
    print("PoLaRIS 持续RL训练（Agent 持久化版）", flush=True)
    print(f"每轮: {EPISODES_PER_ROUND:,} episodes, 跑完继续", flush=True)
    print(f"批次: {BATCH_SIZE} ep/batch", flush=True)
    print(f"隐藏层: {HIDDEN_DIM}, LR: {LR}, clip_vf: {PPO_CONFIG.clip_vf}", flush=True)
    print("=" * 60, flush=True)

    prog = load_progress()
    t0 = time.time()

    # ── 初始化：推断维度 + 创建/加载 agent（只做一次） ──
    print("\n[初始化] 推断观测/动作维度...", flush=True)
    obs_dim, action_dim, obs_dim_route, netlists = _infer_dims()
    print(
        f"  obs_dim={obs_dim}, action_dim={action_dim}, obs_dim_route={obs_dim_route}",
        flush=True,
    )

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # 布局 agent：优先从 checkpoint 加载
    placement_ckpt = SAVE_DIR / "placement_agent.json"
    placement_agent = _try_load_agent(placement_ckpt, obs_dim, action_dim)
    if placement_agent is None:
        placement_agent = _PPOAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        print("  [新建] placement_agent", flush=True)

    # 布线 agent：优先从 checkpoint 加载
    routing_ckpt = SAVE_DIR / "routing_agent.json"
    route_action_dim = 3  # (dx, dy, detour)
    routing_agent = _try_load_agent(routing_ckpt, obs_dim_route, route_action_dim)
    if routing_agent is None:
        routing_agent = _PPOAgent(
            obs_dim=obs_dim_route,
            action_dim=route_action_dim,
            config=PPO_CONFIG,
            hidden_dim=HIDDEN_DIM,
        )
        print("  [新建] routing_agent", flush=True)

    last_ckpt_ep = 0  # 上次保存 checkpoint 时的总 episode 数

    # ── 主循环 ──
    while True:  # 永不停止
        round_num = prog.get("rounds_completed", 0) + 1
        round_ep = 0

        print(f"\n{'#' * 60}", flush=True)
        print(
            f"# 第 {round_num} 轮训练开始 (总进度: {prog['total_episodes_done']:,}ep)",
            flush=True,
        )
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

            # ── 布局训练 ──
            bt0 = time.time()
            place_result = run_placement_batch(
                placement_agent, netlists, this_batch, obs_dim, action_dim
            )
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
                    }
                )

            print(
                f"  布局: avg={place_result['avg_reward']:.2f}, "
                f"best={place_result['best_reward']:.2f}, "
                f"ploss={place_result['avg_policy_loss']:.4f}, "
                f"vloss={place_result['avg_value_loss']:.2f}, "
                f"{bt_sec:.1f}s",
                flush=True,
            )

            # ── 布线训练（每5批1次） ──
            if batch_num % 20 == 0:  # 每20批1次布线（原5批太频繁，A*太慢）
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
                        }
                    )

                print(
                    f"  布线: avg={route_result['avg_reward']:.2f}, "
                    f"best={route_result['best_reward']:.2f}, "
                    f"ploss={route_result['avg_policy_loss']:.4f}, "
                    f"{rt_sec:.1f}s",
                    flush=True,
                )

            # ── 定期保存 checkpoint ──
            total_ep = prog["total_episodes_done"]
            if total_ep - last_ckpt_ep >= CKPT_EVERY:
                placement_agent.save(placement_ckpt)
                routing_agent.save(routing_ckpt)
                last_ckpt_ep = total_ep
                print(f"  [ckpt] 已保存 (ep={total_ep:,})", flush=True)

            prog["batches_completed"] = batch_num
            prog["total_training_seconds"] = time.time() - t0
            save_progress(prog)
            git_commit(prog)

            # 速度估算
            elapsed = time.time() - t0
            eps_done = prog["total_episodes_done"]
            if eps_done > 0:
                eps_per_sec = eps_done / elapsed
                print(
                    f"  速度: {eps_per_sec:.1f} ep/s | 总时间: {elapsed / 3600:.1f}h",
                    flush=True,
                )

        # 一轮2M完成
        prog["rounds_completed"] = round_num
        # 最终保存
        placement_agent.save(placement_ckpt)
        routing_agent.save(routing_ckpt)
        save_progress(prog)

        print(f"\n{'=' * 60}", flush=True)
        print(
            f"第 {round_num} 轮完成！ {round_ep:,}ep",
            flush=True,
        )
        print(
            f"布局best: {prog['best_placement_reward']:.3f} | "
            f"布线best: {prog['best_routing_reward']:.3f}",
            flush=True,
        )
        print(
            f"总进度: {prog['total_episodes_done']:,}ep | "
            f"总时间: {prog['total_training_seconds'] / 3600:.1f}h",
            flush=True,
        )
        print(f"自动开始第 {round_num + 1} 轮...", flush=True)
        print(f"{'=' * 60}", flush=True)

        del netlists
        gc.collect()
        # 重新生成数据集（下一轮用不同网表）
        netlists = generate_dataset(DATASET_CFG)


if __name__ == "__main__":
    main()
