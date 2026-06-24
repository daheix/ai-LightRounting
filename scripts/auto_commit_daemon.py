#!/usr/bin/env python3
"""6分钟自动提交守护进程 (V5: worktree + 与main时刻一致 + 零冲突)

最佳方案: git worktree + rsync + reset --soft origin/main
- 当前工作区完全不动 (无stash/checkout, 零干扰)
- 当前分支不产生任何commit (不写日志)
- 变更通过 rsync 同步到 worktree 目录
- 每次提交前 fetch origin main + reset --soft, 保持与main时刻一致
- trae/auto-commit 永远 = origin/main最新 + 当前工作区变更 (单commit)
- 零冲突: reset --soft 不会产生冲突, 工作区文件以rsync内容为准

流程:
  1. 检测当前工作区变更 (git status)
  2. 创建/更新 worktree: /tmp/ai-polaris-autocommit (trae/auto-commit分支)
  3. rsync 同步变更文件到 worktree (排除.git/build/运行时数据)
  4. git fetch origin main (获取main最新)
  5. git reset --soft origin/main (HEAD移到main最新, 保留工作区变更)
  6. git add -A + commit + push --force-with-lease origin trae/auto-commit
  7. 当前工作区保持不变, 继续AI开发

冲突解决机制 (自动, 零人工):
  - reset --soft origin/main 不会产生冲突 (只移动HEAD, 不动工作区)
  - 工作区文件以 rsync 同步的最新内容为准
  - push --force-with-lease 失败时: 重新fetch + reset + commit + push
  - 永远不会产生 merge conflict (因为不merge, 只reset)
"""
import os
import sys
import time
import subprocess
import shutil
from datetime import datetime

def _find_repo_root():
    p = os.path.dirname(os.path.abspath(__file__))
    while p != os.path.dirname(p):
        if os.path.isdir(os.path.join(p, ".git")):
            return p
        p = os.path.dirname(p)
    return os.path.dirname(os.path.abspath(__file__))

REPO_DIR = _find_repo_root()
DEV_BRANCH = None
SYNC_BRANCH = "trae/auto-commit"
WORKTREE_DIR = "/tmp/ai-polaris-autocommit"  # 独立worktree目录
INTERVAL_SECONDS = 360  # 6分钟
LOG_FILE = os.path.join(REPO_DIR, "auto_commit.log")

# rsync排除规则 (不同步的文件/目录)
RSYNC_EXCLUDES = [
    ".git",  # 排除.git(主仓库目录)和.git文件(worktree指针), 防止破坏worktree结构
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    "build/",  # 编译产物不同步
    "*.log",
    "/tmp/",
    ".trae/",  # spec文档不同步
    "auto_commit.log",  # 自身日志不同步
    "pids/",  # 进程pid文件
    "out/",  # 运行输出(大文件)
    "data/benchmarks/generated/",  # 生成的电路(大文件, 按需单独提交)
    "dump.rdb",  # redis快照
    ".ruff_cache/",
    ".mypy_cache/",
    "node_modules/",
    "*.egg-info/",
    ".tox/",
    ".coverage",
    "htmlcov/",
]


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd, cwd=REPO_DIR, timeout=60):
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 1, str(e)


def get_current_branch():
    rc, out = run("git branch --show-current")
    return out.strip() if rc == 0 else "unknown"


def has_changes():
    rc, out = run("git status --porcelain")
    return rc == 0 and len(out.strip()) > 0, out.strip()


def get_changed_files():
    """获取变更文件列表 (含untracked)"""
    rc, out = run("git status --porcelain")
    if rc != 0:
        return []
    files = []
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line[3:].strip().strip('"')
        files.append(parts)
    return files


def get_diff_summary(files):
    summary_parts = []
    for f in files:
        full_path = os.path.join(REPO_DIR, f)
        if not os.path.exists(full_path):
            summary_parts.append(f"  - {f} (删除)")
            continue
        rc, diff = run(f"git diff --stat -- {f}")
        if rc == 0 and diff.strip():
            summary_parts.append(f"  - {f}: {diff.split(chr(10))[-1].strip()}")
        else:
            summary_parts.append(f"  - {f} (新增/修改)")
    return "\n".join(summary_parts) if summary_parts else "  (无详细差异)"


def ensure_worktree():
    """确保 worktree 目录存在并指向 trae/auto-commit 分支。

    V5方案: worktree 基于origin/main创建 (因为每次提交前会reset --soft origin/main,
    所以初始基于哪里不重要, 但基于origin/main最符合设计意图)。
    """
    # 检查worktree是否已存在
    rc, out = run("git worktree list")
    if WORKTREE_DIR in out:
        # worktree已存在, 检查分支
        rc2, out2 = run(f"git -C {WORKTREE_DIR} branch --show-current")
        if out2.strip() == SYNC_BRANCH:
            return True
        # 分支不对, 删除重建
        run(f"git worktree remove {WORKTREE_DIR} --force")

    # 先fetch origin main, 确保origin/main引用最新
    run("git fetch origin main", timeout=60)

    # 基于origin/main创建worktree, 分支名为SYNC_BRANCH
    # (V5核心: trae/auto-commit永远基于origin/main最新 + 当前工作区变更)
    rc, out = run(
        f"git worktree add {WORKTREE_DIR} -B {SYNC_BRANCH} origin/main", timeout=60
    )
    if rc == 0:
        log(f"worktree已创建 (基于origin/main, 分支{SYNC_BRANCH})")
        return True
    log(f"worktree创建失败(基于origin/main): {out}")

    # 兜底: 基于当前HEAD创建
    rc, out = run(f"git worktree add {WORKTREE_DIR} -B {SYNC_BRANCH} HEAD", timeout=60)
    if rc == 0:
        log(f"worktree已创建 (基于HEAD, 分支{SYNC_BRANCH})")
        return True
    log(f"worktree创建失败: {out}")
    return False


def sync_to_worktree(files):
    """同步变更文件到 worktree 目录 (rsync)"""
    # 构建rsync排除参数
    exclude_args = " ".join(f"--exclude={e}" for e in RSYNC_EXCLUDES)

    # 整体同步 (保持目录结构一致)
    cmd = f"rsync -av --delete {exclude_args} {REPO_DIR}/ {WORKTREE_DIR}/"
    rc, out = run(cmd, timeout=120)
    if rc != 0:
        log(f"rsync同步失败: {out}")
        return False
    return True


def auto_commit_push():
    """V5: worktree方案 + 与main时刻保持一致 + 自动解决冲突"""
    global DEV_BRANCH
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed, status = has_changes()
    if not changed:
        log("无变更，等待下次检查")
        return False

    files = get_changed_files()
    diff_summary = get_diff_summary(files)
    current = get_current_branch()
    if DEV_BRANCH is None:
        DEV_BRANCH = current
        log(f"自动识别开发分支: {DEV_BRANCH}")

    # === 步骤1: 确保 worktree 存在 ===
    if not ensure_worktree():
        log("worktree准备失败, 跳过本次")
        return False

    # === 步骤2: rsync 同步变更到 worktree ===
    if not sync_to_worktree(files):
        return False
    log(f"已同步 {len(files)} 个文件到 worktree")

    # === 步骤3: fetch origin main, 保持与main一致 ===
    rc, out = run("git fetch origin main", timeout=60)
    if rc != 0:
        log(f"fetch origin main失败: {out}, 继续使用本地记录")
    else:
        log("已fetch origin main, 确保与main一致")

    # === 步骤4: 软重置到 origin/main (关键: 保持与main一致 + 零冲突) ===
    rc, out = run(f"git -C {WORKTREE_DIR} reset --soft origin/main", timeout=30)
    if rc != 0:
        log(f"reset --soft origin/main失败: {out}, 尝试reset --soft HEAD")
        run(f"git -C {WORKTREE_DIR} reset --soft HEAD", timeout=30)

    # === 步骤5: 在 worktree 中 add + commit ===
    run(f"git -C {WORKTREE_DIR} add -A")

    commit_msg = f"""auto: 6分钟守护进程同步 ({now})

变更文件 ({len(files)}个):
{diff_summary}

来源分支: {DEV_BRANCH} (未提交, 仅同步)
同步目标: {SYNC_BRANCH} (基于origin/main最新, 时刻与main一致)
方案: git worktree + rsync + reset --soft origin/main (零冲突)
"""
    rc, out = run(
        f'git -C {WORKTREE_DIR} commit -m "$(cat <<\'EOF\'\n{commit_msg}\nEOF\n)"'
    )
    if rc != 0:
        if "nothing to commit" in out or "no changes added" in out:
            log("worktree中无变更可提交 (可能已同步)")
            return False
        log(f"commit失败: {out}")
        return False

    # === 步骤6: force-with-lease push ===
    # 全量fetch确保所有tracking ref最新 (refspec已配置main + trae/auto-commit)
    # 兜底: 显式fetch trae/auto-commit到tracking ref (防止refspec丢失)
    run("git fetch origin", timeout=60)
    run(f"git fetch origin {SYNC_BRANCH}:refs/remotes/origin/{SYNC_BRANCH}", timeout=60)
    rc, out = run(
        f"git -C {WORKTREE_DIR} push --force-with-lease origin {SYNC_BRANCH}",
        timeout=120,
    )
    if rc != 0:
        log(f"push --force-with-lease失败: {out}")
        # 远端可能有新提交, 重新fetch + reset + push
        run("git fetch origin", timeout=60)
        run(f"git fetch origin {SYNC_BRANCH}:refs/remotes/origin/{SYNC_BRANCH}", timeout=60)
        run(f"git -C {WORKTREE_DIR} reset --soft origin/main", timeout=30)
        run(f"git -C {WORKTREE_DIR} add -A")
        rc, out = run(
            f'git -C {WORKTREE_DIR} commit -m "$(cat <<\'EOF\'\n{commit_msg}\nEOF\n)"'
        )
        rc, out = run(
            f"git -C {WORKTREE_DIR} push --force-with-lease origin {SYNC_BRANCH}",
            timeout=120,
        )
        if rc != 0:
            # 最终兜底: 使用--force (V5方案中trae/auto-commit是覆盖式同步分支, 覆盖是预期行为)
            log(f"force-with-lease仍失败, 改用--force: {out}")
            rc, out = run(
                f"git -C {WORKTREE_DIR} push --force origin {SYNC_BRANCH}",
                timeout=120,
            )
            if rc != 0:
                log(f"push失败(所有重试后): {out}")
                return False

    log(f"已同步到远端 {SYNC_BRANCH} (基于origin/main, 时刻与main一致, 零冲突)")
    return True


def main():
    global DEV_BRANCH
    DEV_BRANCH = get_current_branch()
    log("=== 6分钟自动提交守护进程启动 (V5 worktree+main一致) ===")
    log(f"仓库: {REPO_DIR}")
    log(f"开发分支(当前): {DEV_BRANCH} (零commit, 零干扰)")
    log(f"同步目标分支: {SYNC_BRANCH} (远端, 基于origin/main)")
    log(f"worktree目录: {WORKTREE_DIR}")
    log(f"检查间隔: {INTERVAL_SECONDS}秒")
    log(f"方案: git worktree + rsync + reset --soft origin/main")
    log(f"冲突解决: 自动(零人工), reset --soft不产生冲突, push失败则重新fetch+reset+push")

    while True:
        try:
            auto_commit_push()
        except Exception as e:
            log(f"[ERROR] 守护进程异常: {e}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
