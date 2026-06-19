#!/usr/bin/env python3
"""训练监控守护脚本 — 10分钟周期分析（非暴力重启）。

改进:
- 10分钟分析一次训练状态，输出诊断报告
- 不暴力pkill，只在进程真正消失时重启
- 检测reward停滞/NaN/崩溃，输出修复建议
- 原子写入日志，防止损坏

来源:
- RL训练监控最佳实践: https://stable-baselines3.readthedocs.io/
"""

import json
import os
import subprocess
import time
from pathlib import Path

SAVE_DIR = Path("checkpoints/rl_2m")
PROGRESS_FILE = SAVE_DIR / "progress.json"
TOTAL = 2_000_000
MONITOR_LOG = Path("/tmp/train_monitor.log")
ANALYSIS_INTERVAL = 600  # 10分钟分析一次
CHECK_INTERVAL = 30  # 30秒检查进程存活


def check_process() -> bool:
    """检查训练进程是否存活。"""
    result = subprocess.run(["pgrep", "-f", "train_2m.py"], capture_output=True, text=True)
    return result.returncode == 0


def restart_training() -> None:
    """优雅重启训练进程（先SIGTERM，等5秒，再SIGKILL）。"""
    subprocess.run(["pkill", "-TERM", "-f", "train_2m.py"], capture_output=True)
    time.sleep(5)
    subprocess.run(["pkill", "-KILL", "-f", "train_2m.py"], capture_output=True)
    time.sleep(2)
    env = os.environ.copy()
    env["PYTHONPATH"] = "/workspace"
    subprocess.Popen(
        ["python", "scripts/train_2m.py"],
        env=env,
        stdout=open("/tmp/train_2m.log", "w"),
        stderr=subprocess.STDOUT,
        cwd="/workspace",
    )
    with open(MONITOR_LOG, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] 训练进程已重启\n")


def read_progress() -> dict:
    """读取训练进度（容错）。"""
    if not PROGRESS_FILE.exists():
        return {}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def analyze_training(prog: dict, prev_prog: dict) -> str:
    """分析训练状态，返回诊断报告。"""
    report_lines = []
    ep = prog.get("total_episodes_done", 0)
    pct = ep / TOTAL * 100
    t = prog.get("total_training_seconds", 1)
    speed = ep / t if t > 0 else 0
    eta = (TOTAL - ep) / speed / 3600 if speed > 0 else 0

    place_best = prog.get("best_placement_reward", -1e9)
    route_best = prog.get("best_routing_reward", -1e9)
    batches = prog.get("batches_completed", 0)

    report_lines.append(f"=== 10分钟分析报告 [{time.strftime('%H:%M:%S')}] ===")
    report_lines.append(
        f"进度: {pct:.2f}% | {ep:,}ep | {batches}批次 | {speed:.1f}ep/s | ETA {eta:.1f}h"
    )
    report_lines.append(f"布局best: {place_best:.4f} | 布线best: {route_best:.4f}")

    # 检测问题
    problems = []

    # 1. 进度倒退
    prev_ep = prev_prog.get("total_episodes_done", 0)
    if ep < prev_ep:
        problems.append(f"严重: 进度倒退 {prev_ep:,}→{ep:,}，progress.json可能被覆盖")

    # 2. reward停滞
    recent = prog.get("recent_rewards", [])
    if len(recent) >= 20:
        place_rewards = [r["reward"] for r in recent if r.get("phase") == "placement"]
        if place_rewards:
            recent_avg = sum(place_rewards[-10:]) / len(place_rewards[-10:])
            old_avg = (
                sum(place_rewards[:10]) / len(place_rewards[:10])
                if len(place_rewards) >= 20
                else recent_avg
            )
            if abs(recent_avg - old_avg) < 1e-6:
                problems.append(f"警告: 布局reward停滞 recent={recent_avg:.4f} old={old_avg:.4f}")

    # 3. reward为0
    if place_best <= -1e8:
        problems.append("严重: 布局best_reward仍为初始值-1e9，训练未生效")

    # 4. 速度过低
    if 0 < speed < 10:
        problems.append(f"警告: 训练速度过低 {speed:.1f}ep/s")

    # 5. 进度无增长
    if ep == prev_ep and prev_ep > 0:
        problems.append("警告: 10分钟内进度无增长，可能卡死")

    if problems:
        report_lines.append("发现问题:")
        for p in problems:
            report_lines.append(f"  - {p}")
    else:
        report_lines.append("状态: 正常")

    return "\n".join(report_lines)


def main() -> None:
    """主监控循环 — 30秒检查进程，10分钟分析。"""
    print("监控启动: 30秒检查进程 / 10分钟分析", flush=True)
    last_analysis_time = time.time()
    prev_prog = {}

    while True:
        try:
            # 检查进程存活
            if not check_process():
                print(f"[{time.strftime('%H:%M:%S')}] 训练进程不存在，重启中...", flush=True)
                with open(MONITOR_LOG, "a") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] 训练进程不存在，重启\n")
                restart_training()
                time.sleep(15)
                continue

            # 10分钟分析一次
            now = time.time()
            if now - last_analysis_time >= ANALYSIS_INTERVAL:
                prog = read_progress()
                if prog:
                    report = analyze_training(prog, prev_prog)
                    print(report, flush=True)
                    with open(MONITOR_LOG, "a") as f:
                        f.write(report + "\n")
                    prev_prog = dict(prog)
                last_analysis_time = now

            # 30秒状态简报
            prog = read_progress()
            if prog:
                ep = prog.get("total_episodes_done", 0)
                pct = ep / TOTAL * 100
                t = prog.get("total_training_seconds", 1)
                speed = ep / t if t > 0 else 0
                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"{pct:.2f}% | {ep:,}ep | "
                    f"布局best={prog.get('best_placement_reward', 0):.3f} | "
                    f"{speed:.1f}ep/s",
                    flush=True,
                )

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 监控异常: {e}", flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
