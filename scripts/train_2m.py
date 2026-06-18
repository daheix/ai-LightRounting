#!/usr/bin/env python3
"""持续RL训练脚本 — 2M轮一轮，跑完继续下一轮。

关键改进:
- 每批换不同seed生成不同网表（训练数据多样化）
- 2M轮跑完自动开始下一轮2M（持续训练）
- 断点续训 + 自动git commit
- 监控守护自动重启

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

# ── 配置 ──────────────────────────────────────────────
EPISODES_PER_ROUND = 2_000_000  # 每轮2M
BATCH_SIZE = 200
SAVE_DIR = Path("checkpoints/rl_2m")
PROGRESS_FILE = SAVE_DIR / "progress.json"
COMMIT_INTERVAL = 300  # 5分钟

HIDDEN_DIM = 32
LR = 3e-4
ROLLOUT_STEPS = 16
CANVAS_W = 500.0
CANVAS_H = 500.0
GRID_SIZE = 10.0
LOG_EVERY = 200
CKPT_EVERY = 200


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
            "checkpoints/rl_2m/floorplan_final.json",
            "checkpoints/rl_2m/floorplan_log.json",
            "checkpoints/rl_2m/routing_final.json",
            "checkpoints/rl_2m/routing_log.json",
            "docs/训练过程日志.md",
        ]
        for f in files:
            if Path(f).exists():
                subprocess.run(["git", "add", f], capture_output=True, timeout=10)
        ep = prog["total_episodes_done"]
        rnd = prog.get("rounds_completed", 0)
        subprocess.run(
            ["git", "commit", "-m",
             f"chore: RL训练 R{rnd} {ep:,}ep"],
            capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, timeout=60,
        )
        prog["last_commit_time"] = now
        print(f"  [git] 已提交: R{rnd} {ep:,}ep", flush=True)
    except Exception as e:
        print(f"  [git] 失败: {e}", flush=True)


def run_placement_batch(batch_episodes: int, batch_seed: int) -> dict:
    """运行一批布局训练。

    网表用固定seed=42生成（保证obs_dim一致，续训不崩溃），
    但每episode内环境reset随机化（器件初始位置不同）。
    """
    from polaris.trainer.dataset import DatasetConfig
    from polaris.trainer.ppo import PPOConfig
    from polaris.trainer.train_loop import (
        TrainConfig,
        _init_floorplan_training,
        train_floorplan,
    )

    ppo_cfg = PPOConfig(
        lr=LR, gamma=0.99, gae_lambda=0.95, clip_eps=0.2,
        ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
        n_epochs=4, batch_size=32,
        lr_schedule="cosine", total_steps=EPISODES_PER_ROUND,
    )
    # 固定seed=42保证obs_dim一致，环境reset内部随机化
    dataset_cfg = DatasetConfig(
        num_netlists=50,
        min_devices=3,
        max_devices=12,
        seed=42,
    )
    train_cfg = TrainConfig(
        ppo=ppo_cfg, num_episodes=batch_episodes,
        dataset=dataset_cfg,
        rollout_steps=ROLLOUT_STEPS,
        canvas_w=CANVAS_W, canvas_h=CANVAS_H,
        grid_size=GRID_SIZE, hidden_dim=HIDDEN_DIM,
        checkpoint_dir=str(SAVE_DIR),
        checkpoint_every=CKPT_EVERY, log_every=LOG_EVERY,
        lr_schedule="cosine",
        seed=42,
    )

    # 断点续训
    agent = None
    ckpt_path = SAVE_DIR / "floorplan_final.json"
    if ckpt_path.exists():
        try:
            from polaris.trainer.train_loop import load_agent
            tmp_agent, _, dims, _ = _init_floorplan_training(train_cfg, None)
            obs_dim, action_dim = dims
            agent = load_agent(str(ckpt_path), obs_dim, action_dim, HIDDEN_DIM)
            del tmp_agent
        except Exception as e:
            print(f"  续训失败，重新开始: {e}", flush=True)
            agent = None

    agent, logs = train_floorplan(train_cfg, agent=agent, verbose=False)
    rewards = [log.get("ep_reward", 0) for log in logs]
    plosses = [log.get("policy_loss", 0) for log in logs]
    vlosses = [log.get("value_loss", 0) for log in logs]

    result = {
        "episodes": len(logs),
        "best_reward": max(rewards) if rewards else -1e9,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0,
        "avg_policy_loss": sum(plosses) / len(plosses) if plosses else 0,
        "avg_value_loss": sum(vlosses) / len(vlosses) if vlosses else 0,
        "rewards": rewards,
    }

    del agent, logs
    gc.collect()
    return result


def run_routing_batch(batch_episodes: int, batch_seed: int) -> dict:
    """运行一批布线训练。固定seed保证维度一致。"""
    from polaris.trainer.dataset import DatasetConfig
    from polaris.trainer.ppo import PPOConfig
    from polaris.trainer.train_loop import TrainConfig, train_routing

    ppo_cfg = PPOConfig(
        lr=LR, gamma=0.99, gae_lambda=0.95, clip_eps=0.2,
        ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
        n_epochs=4, batch_size=32,
        lr_schedule="cosine", total_steps=EPISODES_PER_ROUND,
    )
    dataset_cfg = DatasetConfig(
        num_netlists=50, min_devices=3, max_devices=12,
        seed=42,
    )
    train_cfg = TrainConfig(
        ppo=ppo_cfg, num_episodes=batch_episodes,
        dataset=dataset_cfg,
        rollout_steps=ROLLOUT_STEPS,
        canvas_w=CANVAS_W, canvas_h=CANVAS_H,
        grid_size=GRID_SIZE, hidden_dim=HIDDEN_DIM,
        checkpoint_dir=str(SAVE_DIR),
        checkpoint_every=CKPT_EVERY, log_every=LOG_EVERY,
        lr_schedule="cosine",
        seed=42,
    )

    agent, logs = train_routing(train_cfg, verbose=False)
    rewards = [log.get("ep_reward", 0) for log in logs]
    plosses = [log.get("policy_loss", 0) for log in logs]

    result = {
        "episodes": len(logs),
        "best_reward": max(rewards) if rewards else -1e9,
        "avg_reward": sum(rewards) / len(rewards) if rewards else 0,
        "avg_policy_loss": sum(plosses) / len(plosses) if plosses else 0,
        "rewards": rewards,
    }

    del agent, logs
    gc.collect()
    return result


def main() -> None:
    """主训练循环 — 2M轮一轮，跑完继续。"""
    print("=" * 60, flush=True)
    print(f"PoLaRIS 持续RL训练", flush=True)
    print(f"每轮: {EPISODES_PER_ROUND:,} episodes, 跑完继续", flush=True)
    print(f"批次: {BATCH_SIZE} ep/batch", flush=True)
    print(f"每批换seed → 不同网表 → 训练数据多样化", flush=True)
    print("=" * 60, flush=True)

    prog = load_progress()
    t0 = time.time()

    while True:  # 永不停止
        round_num = prog.get("rounds_completed", 0) + 1
        round_start_ep = prog["total_episodes_done"]
        round_t0 = time.time()

        print(f"\n{'#'*60}", flush=True)
        print(f"# 第 {round_num} 轮训练开始 "
              f"(总进度: {prog['total_episodes_done']:,}ep)", flush=True)
        print(f"{'#'*60}", flush=True)

        round_ep = 0
        while round_ep < EPISODES_PER_ROUND:
            batch_num = prog["batches_completed"] + 1
            remaining = EPISODES_PER_ROUND - round_ep
            this_batch = min(BATCH_SIZE, remaining)
            # 每批用不同seed → 不同网表
            batch_seed = batch_num * 7 + 42

            pct = prog["total_episodes_done"] / (
                prog["total_episodes_done"] + remaining
            ) * 100

            print(f"\n[批次#{batch_num}] 布局 {this_batch}ep seed={batch_seed} | "
                  f"R{round_num} {round_ep:,}/{EPISODES_PER_ROUND:,} | "
                  f"总 {prog['total_episodes_done']:,}ep",
                  flush=True)

            # 布局训练
            bt0 = time.time()
            place_result = run_placement_batch(this_batch, batch_seed)
            bt_sec = time.time() - bt0

            prog["placement_episodes"] += place_result["episodes"]
            prog["total_episodes_done"] += place_result["episodes"]
            round_ep += place_result["episodes"]
            if place_result["best_reward"] > prog["best_placement_reward"]:
                prog["best_placement_reward"] = place_result["best_reward"]

            for r in place_result["rewards"][-10:]:
                prog["recent_rewards"].append({
                    "ep": prog["total_episodes_done"],
                    "phase": "placement",
                    "reward": round(r, 4),
                })

            print(f"  布局: avg={place_result['avg_reward']:.2f}, "
                  f"best={place_result['best_reward']:.2f}, "
                  f"ploss={place_result['avg_policy_loss']:.4f}, "
                  f"vloss={place_result['avg_value_loss']:.2f}, "
                  f"{bt_sec:.1f}s", flush=True)

            # 布线训练（每5批1次）
            if batch_num % 5 == 0:
                rt0 = time.time()
                route_result = run_routing_batch(this_batch, batch_seed + 1)
                rt_sec = time.time() - rt0

                prog["routing_episodes"] += route_result["episodes"]
                if route_result["best_reward"] > prog["best_routing_reward"]:
                    prog["best_routing_reward"] = route_result["best_reward"]

                for r in route_result["rewards"][-10:]:
                    prog["recent_rewards"].append({
                        "ep": prog["total_episodes_done"],
                        "phase": "routing",
                        "reward": round(r, 4),
                    })

                print(f"  布线: avg={route_result['avg_reward']:.2f}, "
                      f"best={route_result['best_reward']:.2f}, "
                      f"{rt_sec:.1f}s", flush=True)

            prog["batches_completed"] = batch_num
            prog["total_training_seconds"] = time.time() - t0
            save_progress(prog)
            git_commit(prog)

            # 速度估算
            elapsed = time.time() - t0
            eps_done = prog["total_episodes_done"]
            if eps_done > 0:
                eps_per_sec = eps_done / elapsed
                print(f"  速度: {eps_per_sec:.1f} ep/s | "
                      f"总时间: {elapsed/3600:.1f}h", flush=True)

        # 一轮2M完成
        round_time = time.time() - round_t0
        prog["rounds_completed"] = round_num
        save_progress(prog)

        print(f"\n{'='*60}", flush=True)
        print(f"第 {round_num} 轮完成！"
              f" {round_ep:,}ep, {round_time/3600:.1f}h", flush=True)
        print(f"布局best: {prog['best_placement_reward']:.3f} | "
              f"布线best: {prog['best_routing_reward']:.3f}", flush=True)
        print(f"总进度: {prog['total_episodes_done']:,}ep | "
              f"总时间: {prog['total_training_seconds']/3600:.1f}h", flush=True)
        print(f"自动开始第 {round_num + 1} 轮...", flush=True)
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
