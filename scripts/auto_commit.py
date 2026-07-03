#!/usr/bin/env python3
"""自动提交守护进程 V8（极简版，仅 main 分支）。

V8 设计原则（用户 2026-06-28 明确指示）：
  - 直接在 main 分支开发，直接提交 main 分支
  - 不搞各种备份、不切换分支、不用 worktree
  - 删除所有 dev 同步/合并逻辑
  - 修改所有监控脚本版本，统一在 main 分支提交

V7 → V8 变更（R09 单文件版本升级，删除 V7 老逻辑）：
  - 删除 worktree 机制（/tmp/ai-polaris-autocommit）
  - 删除 dev 分支同步逻辑
  - 删除 auto_merge 集成
  - 删除 18 项复杂校验（保留必要的安全校验）
  - 仅保留：检测变更 → git add 精确文件 → commit → push origin main

工作原理：
  1. 检查当前分支是否为 main（不是则告警退出）
  2. git status 检测工作区变更
  3. 无变更则跳过（不创建空提交）
  4. git add 精确文件（禁止 git add -A / git add .）
  5. 生成提交信息（含变更文件清单 + diff stat）
  6. git commit + git push origin main
  7. 失败则告警退出（禁止 fall-back，R03）

安全校验（5 项必要校验）：
  1. 当前分支必须为 main
  2. 禁止 git add -A / git add .（精确添加）
  3. 禁止 --force / --force-with-lease
  4. 删除文件数 > 10 则告警（防误删）
  5. 提交信息含变更文件清单（可追溯）

来源:
- 用户指示: 2026-06-28 "直接在 main 分支上开发，直接提交 main 分支"
- Conventional Commits: https://www.conventionalcommits.org/
- Git push: https://git-scm.com/docs/git-push
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

# 配置
INTERVAL_SECONDS = 9 * 60  # 9 分钟轮询（用户规则 v3）
REPO_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_DIR / "auto_commit.log"
MAIN_BRANCH = "main"
MAX_DELETED_FILES = 10  # 删除文件阈值（防误删）

# 日志配置（循环日志，R05 磁盘有限，循环保留 100MB）
# 总上限 = maxBytes × (backupCount + 1) = 50 MB × 2 = 100 MB
# 来源：用户规则 2026-06-29 "运行日志循环保留 100M"
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("auto_commit")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    LOG_FILE, maxBytes=50 * 1024 * 1024, backupCount=1, encoding="utf-8"
)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)


def run_git(args: list[str]) -> tuple[int, str, str]:
    """执行 git 命令，返回 (returncode, stdout, stderr)。"""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_branch() -> str:
    """获取当前分支名。"""
    code, out, _ = run_git(["branch", "--show-current"])
    if code != 0:
        raise RuntimeError("获取当前分支失败")
    return out.strip()


def get_changed_files() -> list[str]:
    """获取工作区变更文件列表（精确，不删除）。"""
    code, out, _ = run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain=v1"]
    )
    if code != 0:
        raise RuntimeError("git status 失败")
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        filepath = line[3:].strip()
        # 跳过删除文件（单独处理）
        if status[0] == "D" or status[1] == "D":
            continue
        # 跳过未跟踪文件中的 disabled 脚本
        if filepath.endswith(".disabled"):
            continue
        files.append(filepath)
    return files


def get_deleted_files() -> list[str]:
    """获取已删除文件列表。"""
    code, out, _ = run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain=v1"]
    )
    if code != 0:
        raise RuntimeError("git status 失败")
    deleted = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        filepath = line[3:].strip()
        if status[0] == "D" or status[1] == "D":
            deleted.append(filepath)
    return deleted


def get_diff_stat(files: list[str]) -> str:
    """获取变更统计。"""
    if not files:
        return ""
    code, out, _ = run_git(["diff", "--stat"] + files)
    if code != 0:
        return "(diff stat 不可用)"
    return out


def commit_and_push(files: list[str], deleted: list[str]) -> bool:
    """提交并推送变更到 main 分支。"""
    if not files and not deleted:
        logger.info("无变更，跳过提交")
        return False

    # 安全校验：删除文件数
    if len(deleted) > MAX_DELETED_FILES:
        logger.warning(
            "删除文件数 %d 超过阈值 %d，放弃提交（防误删）",
            len(deleted),
            MAX_DELETED_FILES,
        )
        return False

    # git add 精确文件（禁止 git add -A / git add .）
    all_files = files + deleted
    for f in all_files:
        code, _, err = run_git(["add", f])
        if code != 0:
            logger.error("git add %s 失败: %s", f, err)

    # 生成提交信息
    diff_stat = get_diff_stat(files)
    files_list = "\n".join(f"  - {f}" for f in all_files)
    deleted_list = ""
    if deleted:
        deleted_list = "\n删除文件:\n" + "\n".join(
            f"  - {f}" for f in deleted
        )

    commit_msg = (
        f"chore(auto): 自动提交 {len(all_files)} 个文件变更\n\n"
        f"变更文件:\n{files_list}{deleted_list}\n"
        f"\ndiff stat:\n{diff_stat}\n\n"
        f"来源: auto_commit.py V8（main 分支直接提交）"
    )

    # commit
    code, out, err = run_git(
        ["commit", "-m", commit_msg]
    )
    if code != 0:
        logger.error("git commit 失败: %s", err)
        return False

    # push origin main（禁止 --force）
    code, out, err = run_git(["push", "origin", MAIN_BRANCH])
    if code != 0:
        logger.error("git push origin main 失败: %s", err)
        return False

    logger.info("提交并推送成功: %d 文件", len(all_files))
    return True


def main_loop() -> None:
    """主循环。"""
    logger.info("=== auto_commit V8 启动（仅 main 分支）===")

    while True:
        try:
            # 校验当前分支
            branch = get_current_branch()
            if branch != MAIN_BRANCH:
                logger.error(
                    "当前分支 %s 不是 %s，告警退出", branch, MAIN_BRANCH
                )
                sys.exit(1)

            # 检测变更
            files = get_changed_files()
            deleted = get_deleted_files()

            if files or deleted:
                logger.info(
                    "检测到变更: %d 修改, %d 删除", len(files), len(deleted)
                )
                commit_and_push(files, deleted)
            else:
                logger.info("无变更，等待下次轮询")

        except Exception as e:
            logger.error("主循环异常: %s", e, exc_info=True)

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main_loop()
