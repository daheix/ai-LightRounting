#!/usr/bin/env python3
"""6 分钟自动提交代码后台脚本（用户规则：6分钟自动提交）。

每 6 分钟检查一次工作区：
1. 若有代码更新或新文件，自动提交到当前开发分支
2. 合并到 main 分支
3. 推送到远端 main 和开发分支
4. 切回开发分支继续开发

无代码更新则等待下次轮询。

用法:
    python3 scripts/auto_commit.py &
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

INTERVAL_SECONDS = 6 * 60  # 6 分钟（用户规则）
REPO_DIR = Path(__file__).resolve().parent.parent
DEV_BRANCH = "trae/solo-agent-MD19IE"
MAIN_BRANCH = "main"


def run(cmd: str, check: bool = True) -> tuple[int, str]:
    """运行 shell 命令，返回 (返回码, 输出)。"""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if check and result.returncode != 0:
        print(f"[ERROR] 命令失败: {cmd}")
        print(f"stderr: {result.stderr}")
    return result.returncode, result.stdout + result.stderr


def has_changes() -> bool:
    """检查工作区是否有未提交的改动。"""
    code, out = run("git status --porcelain", check=False)
    if code != 0:
        return False
    return bool(out.strip())


def current_branch() -> str:
    """获取当前分支名。"""
    _, out = run("git branch --show-current", check=False)
    return out.strip()


def auto_commit_once() -> None:
    """执行一次自动提交+合并+推送流程。"""
    if not has_changes():
        print(f"[{time.strftime('%H:%M:%S')}] 无代码更新，等待下次轮询")
        return

    # 生成提交信息（基于改动文件）
    _, diff = run("git status --porcelain", check=False)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"自动提交 [{timestamp}]\n\n改动文件:\n{diff[:500]}"

    # 在当前分支提交
    run("git add -A", check=False)
    run(f'git commit -m "{commit_msg}"', check=False)

    # 切到 main，拉取，合并开发分支
    orig_branch = current_branch()
    run(f"git checkout {MAIN_BRANCH}", check=False)
    run(f"git pull origin {MAIN_BRANCH}", check=False)
    run(f"git merge {DEV_BRANCH} --no-edit", check=False)
    run(f"git push origin {MAIN_BRANCH}", check=False)

    # 切回开发分支，合并 main，推送
    run(f"git checkout {DEV_BRANCH}", check=False)
    run(f"git merge {MAIN_BRANCH} --no-edit", check=False)
    run(f"git push origin {DEV_BRANCH}", check=False)

    print(f"[{time.strftime('%H:%M:%S')}] 自动提交并推送完成")


def main() -> None:
    """主循环：每 6 分钟自动提交一次（用户规则）。"""
    print(f"[{time.strftime('%H:%M:%S')}] 自动提交后台脚本已启动")
    print(f"  仓库: {REPO_DIR}")
    print(f"  开发分支: {DEV_BRANCH}")
    print(f"  主分支: {MAIN_BRANCH}")
    print(f"  轮询间隔: {INTERVAL_SECONDS} 秒（{INTERVAL_SECONDS // 60} 分钟）")

    while True:
        try:
            auto_commit_once()
        except Exception as e:
            print(f"[ERROR] 自动提交异常: {e}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
