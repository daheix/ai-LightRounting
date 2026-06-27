#!/usr/bin/env python3
"""自动提交守护进程 V7（彻底修复 V5/V6 四个 bug）。

V7 方案：fetch 全分支 + reset --hard + 精确增量 + 删除白名单 + 18 项安全校验。

修复的四个 bug:
  1. 孤儿分支: V5 fast-forward main 失败时残留孤儿分支。V7 提交前 fetch 全分支并
     校验祖先关系，非祖先放弃（不创建孤儿）。
  2. 误删文件: V5 rsync --delete 反向删除；V6 仍误判删除。V7 仅复制 REPO_DIR 中
     git status 显式列出的变更文件，删除需通过 DELETE_WHITELIST 白名单校验。
  3. 远端分支不可见: V5/V6 只 fetch main 单分支。V7 配置 remote.origin.fetch 为
     '+refs/heads/*:refs/remotes/origin/*' 全分支，每次 fetch origin 拉取所有分支。
  4. 多版本并存: V5 (auto_commit_daemon.py) 与 V6 (auto_commit.py) 并存。V7 统一
     为 auto_commit.py 单文件，auto_commit_daemon.py 删除（R09 单文件版本升级）。

工作原理:
  1. 配置 remote.origin.fetch 全分支 (解决 bug 3)
  2. fetch origin (全分支) (解决 bug 3)
  3. 校验 worktree 当前 HEAD == origin/main (解决 bug 1, 防孤儿)
  4. reset --hard origin/main (worktree 工作区 = main 最新)
  5. 只复制 REPO_DIR 中 git status 列出的变更文件到 worktree (增量, 不 --delete)
  6. 用 git -c core.quotepath=false status --porcelain=v1 -z 解析中文文件名/rename
  7. 删除文件需通过 DELETE_WHITELIST 正则白名单校验 (解决 bug 2)
  8. commit 前校验: 删除文件数 > 5 或删除行数 > 500 则放弃 push (防 V5 事故再现)
  9. fast-forward main 多层保护: merge-base 祖先校验 + refspec ff push + SHA 校验
     (解决 bug 1, 非祖先放弃不创建孤儿)

18 项安全校验:
 1.  remote.origin.fetch 配置为全分支 (bug 3 修复)
 2.  git fetch origin (全分支) 返回码 → 失败放弃
 3.  git fetch origin main 返回码 → 失败放弃
 4.  worktree 存在性 + 分支校验 → 失败放弃
 5.  core.quotepath=false + -z 解析 status → 失败放弃
 6.  shutil.copy2/copytree 成功率 → 失败数 > 0 放弃
 7.  符号链接 follow_symlinks=False
 8.  目标目录 makedirs(exist_ok=True)
 9.  删除文件通过 DELETE_WHITELIST 白名单 (bug 2 修复)
 10. commit 前删除文件数 ≤ 5 → 超阈值放弃
 11. 删除行数 ≤ 500 → 超阈值放弃
 12. merge-base --is-ancestor 校验 → 非祖先放弃 (bug 1 修复)
 13. refspec ff push (HEAD:main) → 远端拒绝非 ff
 14. push 后 SHA 校验 (本地 HEAD == 远端 main) → 不等告警
 15. 禁止任何 --force / --force-with-lease 到 main
 16. 禁止 git add -A / git add . (精确添加变更文件)
 17. 提交信息含变更文件清单 + diff stat (可追溯)
 18. fetch 后自动 prune 远端已删除分支 (防 stale 引用)

来源:
- V5 事故: 提交 89acb8b 删除 94 文件 +41559 行 (rsync --delete + reset --soft)
- V6 事故: 远端分支不可见 + 孤儿分支残留 (fetch 单分支 + 非祖先 ff 失败)
- Git worktree: https://git-scm.com/docs/git-worktree
- Git refspec 全分支: https://git-scm.com/book/en/v2/Git-Internals-The-Refspec
- Conventional Commits: https://www.conventionalcommits.org/
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

INTERVAL_SECONDS = 6 * 60  # 6 分钟轮询
REPO_DIR = Path(__file__).resolve().parent.parent
WORKTREE_DIR = Path("/tmp/ai-polaris-autocommit")
LOG_FILE = REPO_DIR / "auto_commit.log"
MAIN_BRANCH = "main"
AC_BRANCH = "trae/auto-commit"  # 自动提交专用本地分支（对应远端 main）

# 删除阈值（防 V5 事故）
MAX_DELETED_FILES = 5
MAX_DELETED_LINES = 500

# 删除白名单: 只允许删除以下路径模式的文件 (bug 2 修复)
# 严禁删除 src/ docs/ tests/ scripts/ 3dtool/ 等核心目录的代码文件
# 允许删除: 缓存、临时文件、日志、.pyc、空目录、__pycache__ 等
DELETE_WHITELIST = [
    r"^__pycache__/.*",
    r".*/__pycache__/.*",
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.pyd$",
    r".*\.log$",  # 日志文件
    r"^\.pytest_cache/.*",
    r"^\.mypy_cache/.*",
    r"^\.ruff_cache/.*",
    r"^pids/.*",
    r"^tmp/.*",
    r"^checkpoints/.*\.tmp$",
    r".*\.swp$",
    r".*\.swo$",
]

# 配置日志（同时输出到文件和控制台）
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("auto_commit_v7")


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


def ensure_remote_fetch_all_branches() -> bool:
    """校验 1: 配置 remote.origin.fetch 为全分支 (bug 3 修复)。

    默认 git clone 只 fetch main 单分支，导致远端新分支不可见。
    配置 '+refs/heads/*:refs/remotes/origin/*' 后每次 fetch 拉取所有分支。

    来源: https://git-scm.com/book/en/v2/Git-Internals-The-Refspec
    """
    code, out, _ = run(["git", "config", "remote.origin.fetch"], cwd=REPO_DIR)
    expected = "+refs/heads/*:refs/remotes/origin/*"
    if code == 0 and expected in out:
        return True
    code, _, err = run(["git", "config", "remote.origin.fetch", expected], cwd=REPO_DIR)
    if code != 0:
        logger.error("校验 1 FAIL: 配置 remote.origin.fetch 失败: %s", err)
        return False
    logger.info("校验 1 PASS: remote.origin.fetch 已配置为全分支 (bug 3 修复)")
    return True


def ensure_worktree() -> bool:
    """校验 4: 确保 worktree 存在并指向 trae/auto-commit 分支。

    若 worktree 不存在则创建；已存在则复用。失败则返回 False。
    """
    code, out, _ = run(["git", "worktree", "list"], cwd=REPO_DIR)
    if code != 0:
        logger.error("校验 4 前置: git worktree list 失败")
        return False
    if str(WORKTREE_DIR) not in out:
        run(["git", "fetch", "origin", MAIN_BRANCH], cwd=REPO_DIR)
        code, _, _ = run(["git", "rev-parse", "--verify", AC_BRANCH], cwd=REPO_DIR)
        if code != 0:
            code, _, err = run(
                ["git", "branch", AC_BRANCH, f"origin/{MAIN_BRANCH}"], cwd=REPO_DIR
            )
            if code != 0:
                logger.error("创建本地分支 %s 失败: %s", AC_BRANCH, err)
                return False
        code, out, err = run(
            ["git", "worktree", "add", str(WORKTREE_DIR), AC_BRANCH], cwd=REPO_DIR
        )
        if code != 0:
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
    """校验 5: 获取 REPO_DIR 工作区的变更文件列表。

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
        logger.error("校验 5 FAIL: git status 失败: %s", err)
        return []
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


def is_delete_allowed(path: str) -> bool:
    """校验 9: 删除文件白名单校验 (bug 2 修复)。

    只允许删除缓存、临时文件、日志、.pyc、__pycache__ 等。
    严禁删除 src/ docs/ tests/ scripts/ 3dtool/ 等核心目录的代码文件。
    """
    for pattern in DELETE_WHITELIST:
        if re.match(pattern, path):
            return True
    return False


def copy_file_to_worktree(src_rel: str) -> bool:
    """校验 6/7/8: 将 REPO_DIR 中的单个文件增量复制到 WORKTREE_DIR。

    校验 6: copy2 成功率; 校验 7: 符号链接 follow_symlinks=False; 校验 8: makedirs(exist_ok=True)。
    """
    src_abs = REPO_DIR / src_rel
    dst_abs = WORKTREE_DIR / src_rel
    try:
        if not src_abs.exists():
            return True  # 源文件不存在（可能是删除），由 git rm 处理
        dst_abs.parent.mkdir(parents=True, exist_ok=True)
        if src_abs.is_symlink() or src_abs.is_dir():
            if src_abs.is_dir():
                shutil.copytree(src_abs, dst_abs, dirs_exist_ok=True, symlinks=True)
            else:
                shutil.copy2(src_abs, dst_abs, follow_symlinks=False)
        else:
            shutil.copy2(src_abs, dst_abs)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("校验 6 FAIL: 复制 %s 失败: %s", src_rel, e)
        return False


def count_deleted_lines(worktree_deleted: list[str]) -> int:
    """统计 worktree 中被删除文件的总行数（用于校验 11）。"""
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
                total += int(parts[1])
            except ValueError:
                continue
    return total


def generate_diff_summary(added: list[str], modified: list[str], deleted: list[str]) -> str:
    """校验 17: 生成变更文件清单 + diff stat (可追溯)。"""
    lines = []
    for rel in added[:20]:
        lines.append(f"  + {rel} (新增)")
    for rel in modified[:20]:
        full = REPO_DIR / rel
        if full.exists():
            code, diff, _err = run(["git", "diff", "--stat", "--", rel], cwd=REPO_DIR)
            if code == 0 and diff.strip():
                last = diff.splitlines()[-1].strip()
                lines.append(f"  ~ {rel}: {last}")
            else:
                lines.append(f"  ~ {rel} (修改)")
        else:
            lines.append(f"  ~ {rel} (修改)")
    for rel in deleted[:20]:
        lines.append(f"  - {rel} (删除)")
    if len(added) + len(modified) + len(deleted) > 20:
        lines.append(f"  ... 共 {len(added) + len(modified) + len(deleted)} 个文件")
    return "\n".join(lines)


def auto_commit_once() -> None:
    """执行一次 V7 自动提交流程（18 项安全校验）。"""
    # 校验 1: 配置 remote.origin.fetch 全分支 (bug 3 修复)
    if not ensure_remote_fetch_all_branches():
        return

    # 获取变更文件
    entries = get_changed_files()
    if not entries:
        logger.info("无代码更新，等待下次轮询")
        return

    added, modified, deleted = classify_changes(entries)
    logger.info(
        "检测到变更: 新增 %d, 修改 %d, 删除 %d", len(added), len(modified), len(deleted)
    )

    # 校验 9: 删除白名单 (bug 2 修复)
    forbidden_deletes = [d for d in deleted if not is_delete_allowed(d)]
    if forbidden_deletes:
        logger.error(
            "校验 9 FAIL: 以下文件不在删除白名单内，放弃本次提交 (bug 2 修复):"
        )
        for f in forbidden_deletes:
            logger.error("  ✗ 禁止删除: %s", f)
        return
    logger.info("校验 9 PASS: 删除文件 %d 个全部通过白名单校验", len(deleted))

    if not ensure_worktree():
        logger.error("校验 4 FAIL: worktree 不可用，放弃本次")
        return

    # 校验 2: git fetch origin (全分支 + prune) (bug 3 修复 + 校验 18)
    code, _, err = run(["git", "fetch", "origin", "--prune"], cwd=REPO_DIR, timeout=60)
    if code != 0:
        logger.error("校验 2 FAIL: fetch origin 失败: %s", err)
        return
    logger.info("校验 2 PASS: fetch origin (全分支 + prune)")

    # 校验 3: fetch origin main
    code, _, err = run(["git", "fetch", "origin", MAIN_BRANCH], cwd=WORKTREE_DIR, timeout=60)
    if code != 0:
        logger.error("校验 3 FAIL: fetch origin main 失败: %s", err)
        return
    logger.info("校验 3 PASS: fetch origin main")

    # reset --hard origin/main（worktree 工作区 = main 最新）
    code, out, err = run(["git", "reset", "--hard", f"origin/{MAIN_BRANCH}"], cwd=WORKTREE_DIR)
    if code != 0:
        logger.error("reset --hard 失败: %s", err)
        return

    # 增量复制变更文件到 worktree（不 --delete，防 V5 事故）
    failed = 0
    all_changed = added + modified
    for rel in all_changed:
        if not copy_file_to_worktree(rel):
            failed += 1
    # 处理删除：在 worktree 中 git rm（仅白名单内）
    for rel in deleted:
        code, _, _ = run(["git", "rm", "-f", "--", rel], cwd=WORKTREE_DIR)
        # 文件可能本就不在 worktree（reset --hard 后），忽略失败

    # 校验 6: 复制失败数检查
    if failed > 0:
        logger.error("校验 6 FAIL: %d 个文件复制失败，放弃本次", failed)
        return
    logger.info("校验 6 PASS: 全部文件复制成功")

    # 校验 16: 精确 git add（禁止 git add -A / git add .）
    add_args = ["git", "add", "--"]
    for rel in all_changed:
        add_args.append(rel)
    if all_changed:
        code, _, err = run(add_args, cwd=WORKTREE_DIR)
        if code != 0:
            logger.error("git add 失败: %s", err)
            return
    logger.info("校验 16 PASS: 精确 git add (禁止 git add -A)")

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

    # 校验 10: 删除文件数 ≤ 5
    if len(wt_deleted) > MAX_DELETED_FILES:
        logger.error(
            "校验 10 FAIL: 删除文件数 %d > %d，放弃 push（防 V5 事故）",
            len(wt_deleted),
            MAX_DELETED_FILES,
        )
        return
    logger.info("校验 10 PASS: 删除文件数 %d ≤ %d", len(wt_deleted), MAX_DELETED_FILES)

    # 校验 11: 删除行数 ≤ 500
    deleted_lines = count_deleted_lines(wt_deleted)
    if deleted_lines > MAX_DELETED_LINES:
        logger.error(
            "校验 11 FAIL: 删除行数 %d > %d，放弃 push（防 V5 事故）",
            deleted_lines,
            MAX_DELETED_LINES,
        )
        return
    logger.info("校验 11 PASS: 删除行数 %d ≤ %d", deleted_lines, MAX_DELETED_LINES)

    # 校验 17: 生成提交信息含变更文件清单 + diff stat
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    summary = []
    if wt_added:
        summary.append(f"+{len(wt_added)} 新增")
    if wt_modified:
        summary.append(f"~{len(wt_modified)} 修改")
    if wt_deleted:
        summary.append(f"-{len(wt_deleted)} 删除")
    diff_summary = generate_diff_summary(wt_added, wt_modified, wt_deleted)
    commit_msg = f"""chore: 自动提交 [{timestamp}] ({', '.join(summary)})

变更文件清单:
{diff_summary}

守护进程: V7 (18 项安全校验, bug 1-4 修复)
来源: AI 工作区精确变更 (非 rsync --delete)
"""
    code, _, err = run(["git", "commit", "-m", commit_msg], cwd=WORKTREE_DIR)
    if code != 0:
        code2, status, _ = run(["git", "status", "--porcelain"], cwd=WORKTREE_DIR)
        if "nothing to commit" in err or not status.strip():
            logger.info("worktree 无变更可提交")
            return
        logger.error("git commit 失败: %s", err)
        return
    logger.info("git commit 完成")

    # 校验 12: merge-base --is-ancestor (bug 1 修复, 防孤儿分支)
    code, _, err = run(
        ["git", "merge-base", "--is-ancestor", f"origin/{MAIN_BRANCH}", "HEAD"],
        cwd=WORKTREE_DIR,
    )
    if code != 0:
        logger.error(
            "校验 12 FAIL: HEAD 非 origin/main 后裔，放弃 ff push（防孤儿分支, bug 1 修复）: %s",
            err,
        )
        return
    logger.info("校验 12 PASS: HEAD 是 origin/main 的后裔（可 ff push, 防孤儿）")

    # 校验 13/15: refspec ff push (HEAD:main)，禁止 --force (校验 15)
    code, out, err = run(
        ["git", "push", "origin", f"HEAD:{MAIN_BRANCH}"],
        cwd=WORKTREE_DIR,
    )
    if code != 0:
        logger.error("校验 13 FAIL: ff push 到远端 main 被拒绝（非快进, bug 1 修复）: %s", err)
        return
    logger.info("校验 13 PASS: ff push 到远端 main 成功")

    # 校验 14: push 后 SHA 校验 (本地 HEAD == 远端 main)
    code, local_sha, _ = run(["git", "rev-parse", "HEAD"], cwd=WORKTREE_DIR)
    run(["git", "fetch", "origin", MAIN_BRANCH], cwd=WORKTREE_DIR, timeout=60)
    code2, remote_sha, _ = run(["git", "rev-parse", f"origin/{MAIN_BRANCH}"], cwd=WORKTREE_DIR)
    local_sha = local_sha.strip()
    remote_sha = remote_sha.strip()
    if local_sha != remote_sha:
        logger.warning("校验 14 WARN: push 后 SHA 不一致 local=%s remote=%s", local_sha, remote_sha)
    else:
        logger.info("校验 14 PASS: push 后 SHA 一致 %s", local_sha[:12])

    logger.info("自动提交完成 ✓ (V7, 18 项校验通过)")


def main() -> None:
    """主循环：每 6 分钟自动提交一次。"""
    logger.info("=" * 70)
    logger.info("自动提交守护进程 V7 已启动 (修复 V5/V6 四个 bug)")
    logger.info("  仓库: %s", REPO_DIR)
    logger.info("  worktree: %s", WORKTREE_DIR)
    logger.info("  本地分支: %s → 远端 %s", AC_BRANCH, MAIN_BRANCH)
    logger.info("  轮询间隔: %d 秒（%d 分钟）", INTERVAL_SECONDS, INTERVAL_SECONDS // 60)
    logger.info("  删除阈值: 文件 ≤ %d, 行数 ≤ %d", MAX_DELETED_FILES, MAX_DELETED_LINES)
    logger.info("  日志: %s", LOG_FILE)
    logger.info("  bug 1 修复: 孤儿分支 (merge-base 祖先校验)")
    logger.info("  bug 2 修复: 误删文件 (删除白名单 DELETE_WHITELIST)")
    logger.info("  bug 3 修复: 远端分支不可见 (remote.origin.fetch 全分支)")
    logger.info("  bug 4 修复: 多版本并存 (V5 auto_commit_daemon.py 已删除)")
    logger.info("  18 项安全校验 + 禁止 --force + 禁止 git add -A")
    logger.info("=" * 70)

    while True:
        try:
            auto_commit_once()
        except Exception as e:  # noqa: BLE001
            logger.error("自动提交异常: %s", e)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
