#!/usr/bin/env python3
"""自动提交守护进程 V6（修复 V5 文件丢失 bug）。

V6 方案：reset --hard + 增量复制 + 12 项安全校验，彻底修复 V5 文件丢失 bug。

工作原理（保底机制，AI 工作区为准覆盖 main 同文件他人修改）：
1. worktree 先 git fetch origin main + reset --hard origin/main（工作区 = main 最新）
2. 只复制 REPO_DIR 中 git status 列出的变更文件到 worktree（增量，不 --delete）
3. 用 git -c core.quotepath=false status --porcelain=v1 -z 正确解析中文文件名/rename
4. commit 前校验：删除文件数 > 5 或删除行数 > 500 则放弃 push（防 V5 事故再现）
5. fast-forward main 多层保护：merge-base + refspec ff + push 后 SHA 校验

12 项安全校验：
 1. fetch origin main 返回码 → 放弃本次
 2. reset --hard origin/main 返回码 → 放弃本次
 3. core.quotepath=false + -z 解析 → 解析失败放弃
 4. shutil.copy2/copytree 成功率 → 失败数 > 0 放弃
 5. 符号链接 follow_symlinks=False
 6. 目标目录 makedirs(exist_ok=True)
 7. commit 前删除文件数 ≤ 5 → 超阈值放弃
 8. 删除行数 ≤ 500 → 超阈值放弃
 9. merge-base --is-ancestor 校验 → 非祖先放弃
10. refspec ff push (trae/auto-commit:main) → 远端拒绝非 ff
11. push 后 SHA 校验 (main == ac) → 不等告警
12. 禁止任何 --force 到 main

用法:
    nohup python3 scripts/auto_commit.py > /tmp/v6_autocommit.log 2>&1 &
日志: auto_commit.log（仓库根目录）

来源:
- V5 事故分析: 提交 89acb8b 删除 94 文件 +41559 行（rsync --delete + reset --soft）
- Git worktree: https://git-scm.com/docs/git-worktree
- Conventional Commits: https://www.conventionalcommits.org/
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

INTERVAL_SECONDS = 6 * 60  # 6 分钟轮询
REPO_DIR = Path(__file__).resolve().parent.parent
WORKTREE_DIR = Path("/tmp/ai-ddr5-autocommit")
LOG_FILE = REPO_DIR / "auto_commit.log"
MAIN_BRANCH = "main"
AC_BRANCH = "trae/auto-commit"  # 自动提交专用本地分支（对应远端 main）

# 删除阈值（防 V5 事故）
MAX_DELETED_FILES = 5
MAX_DELETED_LINES = 500

# 配置日志（同时输出到文件和控制台）
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("auto_commit_v6")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> tuple[int, str, str]:
    """运行命令，返回 (返回码, stdout, stderr)。失败不抛异常，由调用方检查返回码。"""
    try:
        r = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def ensure_worktree() -> bool:
    """确保 worktree 存在并基于 trae/auto-commit 分支。

    若 worktree 不存在则创建；已存在则复用。失败则返回 False。
    """
    # 检查 worktree 是否已注册
    code, out, _ = run(["git", "worktree", "list"], cwd=REPO_DIR)
    if code != 0:
        logger.error("校验 1 前置: git worktree list 失败")
        return False
    if str(WORKTREE_DIR) not in out:
        # worktree 不存在，创建
        # 先确保本地 trae/auto-commit 分支存在（基于 origin/main）
        run(["git", "fetch", "origin", MAIN_BRANCH], cwd=REPO_DIR)
        # 检查本地分支是否已存在
        code, _, _ = run(["git", "rev-parse", "--verify", AC_BRANCH], cwd=REPO_DIR)
        if code != 0:
            # 分支不存在，从 origin/main 创建
            code, _, err = run(
                ["git", "branch", AC_BRANCH, f"origin/{MAIN_BRANCH}"], cwd=REPO_DIR
            )
            if code != 0:
                logger.error("创建本地分支 %s 失败: %s", AC_BRANCH, err)
                return False
        # 创建 worktree
        code, out, err = run(
            ["git", "worktree", "add", str(WORKTREE_DIR), AC_BRANCH], cwd=REPO_DIR
        )
        if code != 0:
            # 可能目录已存在但未注册，尝试 prune 后重试
            run(["git", "worktree", "prune"], cwd=REPO_DIR)
            if WORKTREE_DIR.exists():
                shutil.rmtree(WORKTREE_DIR, ignore_errors=True)
            code, out, err = run(
                ["git", "worktree", "add", str(WORKTREE_DIR), AC_BRANCH], cwd=REPO_DIR
            )
            if code != 0:
                logger.error("创建 worktree 失败: %s", err)
                return False
        logger.info("worktree 已创建: %s", WORKTREE_DIR)
    return True


def get_changed_files() -> list[tuple[str, str, str]]:
    """获取 REPO_DIR 工作区的变更文件列表。

    使用 git -c core.quotepath=false status --porcelain=v1 -z 正确解析中文文件名/rename。

    Returns:
        [(status_code, src_path, dst_path), ...]，dst_path 仅 rename 有值。
        失败返回空列表。
    """
    code, out, err = run(
        ["git", "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z"],
        cwd=REPO_DIR,
    )
    if code != 0:
        logger.error("校验 3: git status 失败: %s", err)
        return []
    # -z 输出以 NUL 分隔；普通条目为 "XY path"，rename 为 "XY path\0path2"
    entries: list[tuple[str, str, str]] = []
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if not chunk:
            i += 1
            continue
        if len(chunk) < 3:
            i += 1
            continue
        xy = chunk[:2]
        path = chunk[3:]
        if path == "":
            i += 1
            continue
        # rename/copy 状态码首字符为 R/C，后跟原路径
        if xy[0] in ("R", "C"):
            i += 1
            dst = parts[i] if i < len(parts) else ""
            entries.append((xy, path, dst))
        else:
            entries.append((xy, path, ""))
        i += 1
    return entries


def classify_changes(entries: list[tuple[str, str, str]]) -> tuple[list[str], list[str], list[str]]:
    """将变更分类为 (新增, 修改, 删除) 文件列表。

    git status 状态码：
        - "A " 新增, "M " 修改, "D " 删除, "R " rename, "C " copy
        - "??" 未跟踪（视为新增）
    """
    added, modified, deleted = [], [], []
    for xy, src, _dst in entries:
        x, y = xy[0], xy[1]
        if x == "D" or y == "D":
            deleted.append(src)
        elif x == "?" or x == "A" or x == "C":
            added.append(src)
        elif x == "M" or x == "R":
            modified.append(src)
        else:
            modified.append(src)
    return added, modified, deleted


def copy_file_to_worktree(src_rel: str) -> bool:
    """将 REPO_DIR 中的单个文件增量复制到 WORKTREE_DIR。

    校验 4: copy2 成功率; 校验 5: 符号链接 follow_symlinks=False; 校验 6: makedirs(exist_ok=True)。
    """
    src_abs = REPO_DIR / src_rel
    dst_abs = WORKTREE_DIR / src_rel
    try:
        if not src_abs.exists():
            # 源文件不存在（可能是删除），跳过（删除由 git rm 处理）
            return True
        # 校验 6: 确保目标目录存在
        dst_abs.parent.mkdir(parents=True, exist_ok=True)
        if src_abs.is_symlink() or src_abs.is_dir():
            # 校验 5: 符号链接/目录用 copytree（不跟随符号链接）
            if src_abs.is_dir():
                shutil.copytree(src_abs, dst_abs, dirs_exist_ok=True, symlinks=True)
            else:
                # 符号链接文件
                shutil.copy2(src_abs, dst_abs, follow_symlinks=False)
        else:
            # 校验 4: 普通文件 copy2（保留元数据）
            shutil.copy2(src_abs, dst_abs)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("校验 4: 复制 %s 失败: %s", src_rel, e)
        return False


def count_deleted_lines(worktree_deleted: list[str]) -> int:
    """统计 worktree 中被删除文件的总行数（用于校验 8）。

    通过 git diff --numstat 获取删除行数。
    """
    if not worktree_deleted:
        return 0
    args = ["git", "diff", "--numstat", "HEAD", "--"] + worktree_deleted
    code, out, _ = run(args, cwd=WORKTREE_DIR)
    if code != 0:
        return 0
    total = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                # numstat 格式: added\tdeleted\tpath；删除文件 added=0
                total += int(parts[1])
            except ValueError:
                continue
    return total


def auto_commit_once() -> None:
    """执行一次 V6 自动提交流程（12 项安全校验）。"""
    # 获取变更文件
    entries = get_changed_files()
    if not entries:
        logger.info("无代码更新，等待下次轮询")
        return

    added, modified, deleted = classify_changes(entries)
    logger.info(
        "检测到变更: 新增 %d, 修改 %d, 删除 %d", len(added), len(modified), len(deleted)
    )

    if not ensure_worktree():
        logger.error("worktree 不可用，放弃本次")
        return

    # 校验 1: fetch origin main
    code, _, err = run(["git", "fetch", "origin", MAIN_BRANCH], cwd=WORKTREE_DIR)
    if code != 0:
        logger.error("校验 1 FAIL: fetch origin main 失败: %s", err)
        return
    logger.info("校验 1 PASS: fetch origin main")

    # 校验 2: reset --hard origin/main（worktree 工作区 = main 最新）
    code, out, err = run(["git", "reset", "--hard", f"origin/{MAIN_BRANCH}"], cwd=WORKTREE_DIR)
    if code != 0:
        logger.error("校验 2 FAIL: reset --hard 失败: %s", err)
        return
    logger.info("校验 2 PASS: reset --hard origin/main")

    # 增量复制变更文件到 worktree（不 --delete，防 V5 事故）
    failed = 0
    all_changed = added + modified
    for rel in all_changed:
        if not copy_file_to_worktree(rel):
            failed += 1
    # 处理删除：在 worktree 中 git rm
    for rel in deleted:
        code, _, _ = run(["git", "rm", "-f", "--", rel], cwd=WORKTREE_DIR)
        if code != 0:
            # 文件可能本就不在 worktree（reset --hard 后），忽略
            pass

    # 校验 4: 复制失败数检查
    if failed > 0:
        logger.error("校验 4 FAIL: %d 个文件复制失败，放弃本次", failed)
        return
    logger.info("校验 4 PASS: 全部文件复制成功")

    # 在 worktree 中 git add（精确添加变更文件，禁止 git add -A）
    add_args = ["git", "add", "--"]
    for rel in all_changed:
        add_args.append(rel)
    if all_changed:
        code, _, err = run(add_args, cwd=WORKTREE_DIR)
        if code != 0:
            logger.error("git add 失败: %s", err)
            return

    # 检查 worktree 是否有暂存变更
    code, out, _ = run(["git", "diff", "--cached", "--name-status"], cwd=WORKTREE_DIR)
    if not out.strip():
        logger.info("worktree 无暂存变更（可能已被 reset 覆盖），等待下次轮询")
        return

    # 统计 worktree 中的删除文件和删除行数（相对 HEAD）
    wt_added, wt_modified, wt_deleted = [], [], []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0] if parts[0] else " "
        path = parts[-1]
        if status == "D":
            wt_deleted.append(path)
        elif status in ("A", "C"):
            wt_added.append(path)
        else:
            wt_modified.append(path)

    # 校验 7: 删除文件数 ≤ 5
    if len(wt_deleted) > MAX_DELETED_FILES:
        logger.error(
            "校验 7 FAIL: 删除文件数 %d > %d，放弃 push（防 V5 事故）",
            len(wt_deleted),
            MAX_DELETED_FILES,
        )
        return
    logger.info("校验 7 PASS: 删除文件数 %d ≤ %d", len(wt_deleted), MAX_DELETED_FILES)

    # 校验 8: 删除行数 ≤ 500
    deleted_lines = count_deleted_lines(wt_deleted)
    if deleted_lines > MAX_DELETED_LINES:
        logger.error(
            "校验 8 FAIL: 删除行数 %d > %d，放弃 push（防 V5 事故）",
            deleted_lines,
            MAX_DELETED_LINES,
        )
        return
    logger.info("校验 8 PASS: 删除行数 %d ≤ %d", deleted_lines, MAX_DELETED_LINES)

    # 生成提交信息
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    summary = []
    if wt_added:
        summary.append(f"+{len(wt_added)} 新增")
    if wt_modified:
        summary.append(f"~{len(wt_modified)} 修改")
    if wt_deleted:
        summary.append(f"-{len(wt_deleted)} 删除")
    commit_msg = f"chore: 自动提交 [{timestamp}] ({', '.join(summary)})"

    # 提交
    code, _, err = run(
        ["git", "commit", "-m", commit_msg, "--allow-empty" if not all_changed and not wt_deleted else "--"],
        cwd=WORKTREE_DIR,
    )
    if code != 0 and "nothing to commit" not in err and "nothing to commit" not in (run(["git", "status", "--porcelain"], cwd=WORKTREE_DIR)[1]):
        logger.error("git commit 失败: %s", err)
        return
    logger.info("git commit 完成: %s", commit_msg)

    # 校验 9: merge-base --is-ancestor（trae/auto-commit 必须是 origin/main 的祖先才能 ff push）
    code, _, err = run(
        ["git", "merge-base", "--is-ancestor", f"origin/{MAIN_BRANCH}", "HEAD"],
        cwd=WORKTREE_DIR,
    )
    if code != 0:
        logger.error("校验 9 FAIL: HEAD 非 origin/main 后裔，放弃 ff push（防非快进）: %s", err)
        return
    logger.info("校验 9 PASS: HEAD 是 origin/main 的后裔（可 ff push）")

    # 校验 10: refspec ff push (trae/auto-commit:main)，禁止 --force（校验 12）
    code, out, err = run(
        ["git", "push", "origin", f"HEAD:{MAIN_BRANCH}"],
        cwd=WORKTREE_DIR,
    )
    if code != 0:
        logger.error("校验 10 FAIL: ff push 到远端 main 被拒绝（非快进）: %s", err)
        return
    logger.info("校验 10 PASS: ff push 到远端 main 成功")

    # 校验 11: push 后 SHA 校验 (本地 HEAD == 远端 main)
    code, local_sha, _ = run(["git", "rev-parse", "HEAD"], cwd=WORKTREE_DIR)
    code2, remote_sha, _ = run(["git", "rev-parse", f"origin/{MAIN_BRANCH}"], cwd=WORKTREE_DIR)
    local_sha = local_sha.strip()
    remote_sha = remote_sha.strip()
    if local_sha != remote_sha:
        logger.warning("校验 11 WARN: push 后 SHA 不一致 local=%s remote=%s", local_sha, remote_sha)
    else:
        logger.info("校验 11 PASS: push 后 SHA 一致 %s", local_sha[:12])

    logger.info("自动提交完成 ✓")


def main() -> None:
    """主循环：每 6 分钟自动提交一次。"""
    logger.info("=" * 60)
    logger.info("自动提交守护进程 V6 已启动")
    logger.info("  仓库: %s", REPO_DIR)
    logger.info("  worktree: %s", WORKTREE_DIR)
    logger.info("  本地分支: %s → 远端 %s", AC_BRANCH, MAIN_BRANCH)
    logger.info("  轮询间隔: %d 秒（%d 分钟）", INTERVAL_SECONDS, INTERVAL_SECONDS // 60)
    logger.info("  删除阈值: 文件 ≤ %d, 行数 ≤ %d", MAX_DELETED_FILES, MAX_DELETED_LINES)
    logger.info("  日志: %s", LOG_FILE)
    logger.info("=" * 60)

    while True:
        try:
            auto_commit_once()
        except Exception as e:  # noqa: BLE001
            logger.error("自动提交异常: %s", e)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
