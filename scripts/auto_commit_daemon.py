#!/usr/bin/env python3
"""6分钟自动提交守护进程 (V5: worktree + 与main时刻一致 + 零冲突 + 主动fast-forward main + 质量门禁)

最佳方案: git worktree + rsync + reset --soft origin/main + 主动fast-forward main
- 当前工作区完全不动 (无stash/checkout, 零干扰)
- 当前分支不产生任何commit (不写日志)
- 变更通过 rsync 同步到 worktree 目录
- 每次提交前 fetch origin main + reset --soft, 保持与main时刻一致
- trae/auto-commit 永远 = origin/main最新 + 当前工作区变更 (单commit)
- 零冲突: reset --soft 不会产生冲突, 工作区文件以rsync内容为准
- 保底机制: 主动 fast-forward main (V5架构保证零冲突, 失败放弃等待下次)
- 质量门禁: 提交前运行12电路门禁检查, 不通过禁止提交

流程:
  1. 检测当前工作区变更 (git status)
  2. 创建/更新 worktree: /tmp/ai-polaris-autocommit (trae/auto-commit分支)
  3. rsync 同步变更文件到 worktree (排除.git/build/运行时数据)
  4. git fetch origin (在worktree中, 获取main + trae/auto-commit引用)
  5. git reset --soft origin/main (HEAD移到main最新, 保留工作区变更)
  6. 质量门禁检查 (12电路, 不通过跳过本次提交)
  7. git add -A + commit + push --force-with-lease=trae/auto-commit:<sha>
  8. 主动 fast-forward main: git push origin trae/auto-commit:main (零冲突, 失败放弃)
  9. 当前工作区保持不变, 继续AI开发

冲突解决机制 (自动, 零人工):
  - reset --soft origin/main 不会产生冲突 (只移动HEAD, 不动工作区)
  - 工作区文件以 rsync 同步的最新内容为准
  - push --force-with-lease=<sha> 显式指定远端sha, 避免 stale info
  - 永远不会产生 merge conflict (因为不merge, 只reset + fast-forward)
"""
import os
import sys
import time
import subprocess
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

# rsync排除规则 (与 .gitignore 保持一致，只排除纯运行时缓存和临时文件)
# 原则：所有 git 跟踪的文件都必须同步，不得排除任何含跟踪文件的目录
RSYNC_EXCLUDES = [
    # === Git 结构（必须排除，防止破坏 worktree）===
    ".git",
    # === Python 缓存与产物（与 .gitignore 对齐）===
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.egg-info/",
    "dist/",
    "build/",
    # === 虚拟环境（与 .gitignore 对齐）===
    ".venv/",
    "venv/",
    # === 日志与临时文件 ===
    "*.log",  # 含 auto_commit.log 自身
    "/tmp/",
    # === 密钥与凭据（与 .gitignore 对齐）===
    ".env",
    "*.key",
    "credentials.json",
    # === IDE 文件（与 .gitignore 对齐）===
    ".idea/",
    ".vscode/",
    "*.swp",
    "*.swo",
    # === 运行时 PID（不提交）===
    "pids/",
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
    rc, out = run("git worktree list")
    if WORKTREE_DIR in out:
        rc2, out2 = run(f"git -C {WORKTREE_DIR} branch --show-current")
        if out2.strip() == SYNC_BRANCH:
            return True
        run(f"git worktree remove {WORKTREE_DIR} --force")

    # 基于origin/main创建worktree (V5核心设计)
    run("git fetch origin main", timeout=60)
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
    exclude_args = " ".join(f"--exclude={e}" for e in RSYNC_EXCLUDES)
    cmd = f"rsync -av --delete {exclude_args} {REPO_DIR}/ {WORKTREE_DIR}/"
    rc, out = run(cmd, timeout=120)
    if rc != 0:
        log(f"rsync同步失败: {out}")
        return False
    return True


def quality_gate_check() -> bool:
    """质量门禁检查: 12电路 (4平台×3规模) 端到端流水线。

    不通过则返回False, 禁止提交 (代码质量回退)。
    通过且优于基准则自动刷新基准。
    """
    rc, out = run("python scripts/quality_gate_baseline.py --check", timeout=600)
    if rc != 0:
        log(f"质量门禁未通过, 跳过本次提交 (代码质量回退)")
        log(f"门禁输出: {out[-500:]}")
        return False
    log("质量门禁通过, 允许提交")
    return True


def auto_commit_push():
    """V5: worktree方案 + 与main时刻保持一致 + 质量门禁 + 主动fast-forward main"""
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

    # === 步骤3: fetch origin (在worktree中执行), 保持与main一致 + 获取trae/auto-commit远端引用 ===
    # 必须在worktree中fetch, 否则 --force-with-lease 会因 stale info 失败
    rc, out = run(f"git -C {WORKTREE_DIR} fetch origin", timeout=60)
    if rc != 0:
        log(f"fetch origin失败: {out}, 继续使用本地记录")
    else:
        log("已fetch origin (worktree), 确保与main一致 + 获取trae/auto-commit引用")

    # === 步骤4: 软重置到 origin/main (关键: 保持与main一致 + 零冲突) ===
    rc, out = run(f"git -C {WORKTREE_DIR} reset --soft origin/main", timeout=30)
    if rc != 0:
        log(f"reset --soft origin/main失败: {out}, 尝试reset --soft HEAD")
        run(f"git -C {WORKTREE_DIR} reset --soft HEAD", timeout=30)

    # === 步骤5: 质量门禁检查 (提交前必须通过) ===
    if not quality_gate_check():
        return False

    # === 步骤6: 在 worktree 中 add + commit ===
    run(f"git -C {WORKTREE_DIR} add -A")

    commit_msg = f"""auto: 6分钟守护进程同步 ({now})

变更文件 ({len(files)}个):
{diff_summary}

来源分支: {DEV_BRANCH} (未提交, 仅同步)
同步目标: {SYNC_BRANCH} (基于origin/main最新, 时刻与main一致)
方案: git worktree + rsync + reset --soft origin/main (零冲突)
质量门禁: 通过 (12电路 4平台×3规模)
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

    # === 步骤7: force-with-lease push (显式指定远端sha, 避免stale info) ===
    rc, remote_ref = run("git ls-remote --heads origin trae/auto-commit", timeout=30)
    remote_sha = remote_ref.split()[0] if remote_ref.strip() else ""
    if remote_sha:
        push_cmd = f"git -C {WORKTREE_DIR} push --force-with-lease=trae/auto-commit:{remote_sha} origin {SYNC_BRANCH}"
    else:
        push_cmd = f"git -C {WORKTREE_DIR} push origin {SYNC_BRANCH}"
    rc, out = run(push_cmd, timeout=120)
    if rc != 0:
        log(f"push --force-with-lease失败: {out}")
        run(f"git -C {WORKTREE_DIR} fetch origin", timeout=60)
        run(f"git -C {WORKTREE_DIR} reset --soft origin/main", timeout=30)
        run(f"git -C {WORKTREE_DIR} add -A")
        rc, out = run(
            f'git -C {WORKTREE_DIR} commit -m "$(cat <<\'EOF\'\n{commit_msg}\nEOF\n)"'
        )
        rc2, remote_ref2 = run("git ls-remote --heads origin trae/auto-commit", timeout=30)
        remote_sha2 = remote_ref2.split()[0] if remote_ref2.strip() else ""
        if remote_sha2:
            push_cmd2 = f"git -C {WORKTREE_DIR} push --force-with-lease=trae/auto-commit:{remote_sha2} origin {SYNC_BRANCH}"
        else:
            push_cmd2 = f"git -C {WORKTREE_DIR} push origin {SYNC_BRANCH}"
        rc, out = run(push_cmd2, timeout=120)
        if rc != 0:
            log(f"push失败(重试后): {out}")
            return False

    log(f"已同步到远端 {SYNC_BRANCH} (基于origin/main, 时刻与main一致, 零冲突)")

    # === 步骤8: 主动 fast-forward main (最保底方案) ===
    try:
        fast_forward_main()
    except Exception as e:
        log(f"[WARN] fast-forward main 异常(放弃, 下次重试): {e}")

    return True


def fast_forward_main():
    """主动 fast-forward main 到 trae/auto-commit (最保底方案).

    原理:
    - V5 的 reset --soft origin/main 保证 trae/auto-commit 的 commit 父节点 = origin/main
    - 因此 origin/main merge trae/auto-commit 是 fast-forward, 零冲突
    - 禁止强制推送, 只用 fast-forward, 失败则放弃等待下次
    """
    rc, out = run("git ls-remote origin main", timeout=30)
    main_sha = out.split()[0] if out.strip() else ""
    if rc != 0 or not main_sha:
        log(f"fast-forward: 获取 origin/main sha 失败, 放弃: {out}")
        return False

    rc, out = run("git ls-remote origin trae/auto-commit", timeout=30)
    ac_sha = out.split()[0] if out.strip() else ""
    if rc != 0 or not ac_sha:
        log(f"fast-forward: 获取 origin/trae/auto-commit sha 失败, 放弃: {out}")
        return False

    run("git fetch origin main", timeout=60)
    run("git fetch origin trae/auto-commit", timeout=60)

    rc, out = run(f"git merge-base --is-ancestor {main_sha} {ac_sha}", timeout=10)
    if rc != 0:
        log(f"fast-forward: main 已被推进 (非祖先关系), 放弃等待下次. main={main_sha[:8]} ac={ac_sha[:8]}")
        return False

    if main_sha == ac_sha:
        return True

    rc, out = run(
        f"git push origin trae/auto-commit:main",
        timeout=120,
    )
    if rc != 0:
        log(f"fast-forward: push main 失败(放弃, 下次重试): {out}")
        return False

    log(f"fast-forward: main 已推进到 trae/auto-commit ({ac_sha[:8]}), 零冲突")
    return True


def main():
    global DEV_BRANCH
    DEV_BRANCH = get_current_branch()
    log("=== 6分钟自动提交守护进程启动 (V5 worktree+main一致+质量门禁+fast-forward) ===")
    log(f"仓库: {REPO_DIR}")
    log(f"开发分支(当前): {DEV_BRANCH} (零commit, 零干扰)")
    log(f"同步目标分支: {SYNC_BRANCH} (远端, 基于origin/main)")
    log(f"worktree目录: {WORKTREE_DIR}")
    log(f"检查间隔: {INTERVAL_SECONDS}秒")
    log(f"方案: git worktree + rsync + reset --soft origin/main + 质量门禁")
    log(f"冲突解决: 自动(零人工), reset --soft不产生冲突, push用显式sha避免stale")
    log(f"保底机制: 主动 fast-forward main (V5架构保证零冲突, 失败放弃等待下次)")
    log(f"质量门禁: 12电路 (4平台×3规模), 不通过禁止提交")

    while True:
        try:
            auto_commit_push()
        except Exception as e:
            log(f"[ERROR] 守护进程异常: {e}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
