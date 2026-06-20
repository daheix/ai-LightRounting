#!/usr/bin/env python3
"""自动合并脚本：每5分钟将 trae/solo-agent-fk2qDL 合并到 main。

按标准流程（GitHub Flow）：fetch → merge → push，冲突时跳过并记录日志。
处理 git lock 冲突（训练进程也会 git commit）。

来源:
- GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

INTERVAL = 1200  # 20分钟（用户规则：自动提交代码间隔）
DEV_BRANCH = "trae/solo-agent-fk2qDL"
MAIN_BRANCH = "main"
LOG_FILE = Path("/workspace/checkpoints/rl_2m/auto_merge.log")
LOCK_FILE = Path("/workspace/.git/index.lock")
LOCK_WAIT_MAX = 60  # 最多等待 lock 60秒


def log(msg: str) -> None:
    """记录日志到文件和 stdout。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def wait_for_lock() -> None:
    """等待 git index.lock 释放，超时则强制删除。"""
    waited = 0
    while LOCK_FILE.exists() and waited < LOCK_WAIT_MAX:
        time.sleep(2)
        waited += 2
    if LOCK_FILE.exists():
        log(f"WARNING: lock 仍存在（等待 {waited}s），强制删除")
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass


def run_git(*args: str) -> tuple[int, str]:
    """执行 git 命令，返回 (returncode, output)。"""
    wait_for_lock()
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=120,
        cwd="/workspace",
    )
    output = result.stdout + result.stderr
    if output.strip():
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(output)
    return result.returncode, output


def get_rev(ref: str) -> str:
    """获取 git 引用的 commit hash。"""
    result = subprocess.run(
        ["git", "rev-parse", ref],
        capture_output=True,
        text=True,
        cwd="/workspace",
    )
    return result.stdout.strip()


def get_merge_base(a: str, b: str) -> str:
    """获取两个引用的 merge base。"""
    result = subprocess.run(
        ["git", "merge-base", a, b],
        capture_output=True,
        text=True,
        cwd="/workspace",
    )
    return result.stdout.strip()


def merge_cycle() -> None:
    """执行一次合并周期。"""
    log("=== 开始自动合并周期 ===")

    # 1. 切换到 main
    code, _ = run_git("checkout", MAIN_BRANCH)
    if code != 0:
        log(f"ERROR: 切换到 {MAIN_BRANCH} 失败，跳过本次")
        return

    # 2. 拉取远端 main 最新
    run_git("fetch", "origin", MAIN_BRANCH)
    code, _ = run_git("pull", "origin", MAIN_BRANCH)
    if code != 0:
        log("WARNING: pull main 失败，reset 到 origin/main")
        run_git("reset", "--hard", f"origin/{MAIN_BRANCH}")

    # 3. 拉取开发分支最新
    run_git("fetch", "origin", DEV_BRANCH)

    # 4. 检查开发分支是否有新提交
    remote_dev = get_rev(f"origin/{DEV_BRANCH}")
    merge_base = get_merge_base(MAIN_BRANCH, f"origin/{DEV_BRANCH}")

    if remote_dev == merge_base:
        log("开发分支无新提交，跳过合并")
    else:
        log(f"开发分支有新提交，开始合并: {remote_dev[:8]}")

        # 5. 合并开发分支
        code, output = run_git("merge", DEV_BRANCH, "--no-edit")
        if code != 0:
            log("ERROR: 合并冲突，中止合并并跳过本次")
            run_git("merge", "--abort")
            run_git("checkout", DEV_BRANCH)
            return

        # 6. 推送到远端 main
        code, _ = run_git("push", "origin", MAIN_BRANCH)
        if code != 0:
            log("ERROR: push main 失败")
        else:
            log("OK: 合并并推送成功")

    # 7. 切回开发分支
    run_git("checkout", DEV_BRANCH)
    log(f"=== 周期结束，等待 {INTERVAL}s ===")


def main() -> None:
    """主循环：每 INTERVAL 秒执行一次合并。"""
    log(f"自动合并守护进程启动: {DEV_BRANCH} → {MAIN_BRANCH}, 间隔 {INTERVAL}s")
    while True:
        try:
            merge_cycle()
        except Exception as e:
            log(f"EXCEPTION: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
