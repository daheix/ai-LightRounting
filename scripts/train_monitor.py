#!/usr/bin/env python3
"""训练监控守护脚本。

每60秒检查训练进度，写入日志，自动重启（如果挂了）。
不依赖人工干预。
"""

import json
import os
import subprocess
import time
from pathlib import Path

SAVE_DIR = Path("checkpoints/rl_2m")
PROGRESS_FILE = SAVE_DIR / "progress.json"
LOG_FILE = Path("docs/训练过程日志.md")
TOTAL = 2_000_000
MONITOR_LOG = Path("/tmp/train_monitor.log")


def check_process() -> bool:
    """检查训练进程是否存活。"""
    result = subprocess.run(
        ["pgrep", "-f", "train_2m.py"], capture_output=True, text=True
    )
    return result.returncode == 0


def restart_training() -> None:
    """重启训练进程。"""
    subprocess.run(
        ["pkill", "-f", "train_2m.py"], capture_output=True
    )
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
    """读取训练进度。"""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


def update_log(prog: dict) -> None:
    """更新训练日志。"""
    ep = prog.get("total_episodes_done", 0)
    t = prog.get("total_training_seconds", 1)
    pct = ep / TOTAL * 100
    speed = ep / t if t > 0 else 0
    eta = (TOTAL - ep) / speed / 3600 if speed > 0 else 0

    line = (
        f"| {time.strftime('%H:%M')} | {prog.get('batches_completed',0)} | "
        f"{ep:,} | {prog.get('placement_episodes',0):,} | "
        f"{prog.get('routing_episodes',0):,} | "
        f"{prog.get('best_placement_reward',0):.3f} | "
        f"{prog.get('best_routing_reward',0):.3f} | "
        f"{speed:.1f} | {t/60:.0f}min | {eta:.1f}h |"
    )

    # 追加到日志文件末尾
    with open(MONITOR_LOG, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {pct:.2f}% | {ep:,}ep | {speed:.1f}ep/s | ETA {eta:.1f}h\n")


def main() -> None:
    """主监控循环。"""
    print(f"监控启动，每60秒检查一次", flush=True)
    while True:
        try:
            # 检查进程
            if not check_process():
                print(f"[{time.strftime('%H:%M:%S')}] 训练进程已死，重启中...", flush=True)
                restart_training()
                time.sleep(10)
                continue

            # 读取进度
            prog = read_progress()
            if prog:
                ep = prog.get("total_episodes_done", 0)
                pct = ep / TOTAL * 100
                t = prog.get("total_training_seconds", 1)
                speed = ep / t if t > 0 else 0
                eta = (TOTAL - ep) / speed / 3600 if speed > 0 else 0
                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"{pct:.2f}% | {ep:,}ep | "
                    f"布局best={prog.get('best_placement_reward',0):.3f} | "
                    f"布线best={prog.get('best_routing_reward',0):.3f} | "
                    f"{speed:.1f}ep/s | ETA {eta:.1f}h",
                    flush=True,
                )
                update_log(prog)

                # 检查是否完成
                if ep >= TOTAL:
                    print("训练完成！", flush=True)
                    break

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 监控异常: {e}", flush=True)

        time.sleep(60)


if __name__ == "__main__":
    main()
