#!/usr/bin/env bash
# ==============================================================================
# 仓库初始化脚本: 自动发现所有远端分支 (bug 3 修复)
# ==============================================================================
# 问题: 默认 git clone 只 fetch 单分支, 远端新分支不可见。
#   表现: git branch -a 只显示 main, 新创建的 dev/trae/auto-commit 等分支看不到。
#
# 修复: 配置 remote.origin.fetch 为全分支 refspec, 每次 fetch 拉取所有分支。
#   refspec: +refs/heads/*:refs/remotes/origin/*
#
# 安装位置:
#   - 仓库初始化: bash scripts/git_init_remote_visibility.sh
#   - 质量门禁: 集成到 quality_gate_pre_commit.sh 自动校验
#
# 来源:
# - Git Refspec: https://git-scm.com/book/en/v2/Git-Internals-The-Refspec
# - git fetch 文档: https://git-scm.com/docs/git-fetch
# ==============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

EXPECTED_FETCH="+refs/heads/*:refs/remotes/origin/*"

log() {
    echo "[git_init] $*"
}

fail() {
    echo "[git_init][ERROR] $*" >&2
    exit 1
}

# 1. 检查是否在 git 仓库内
git rev-parse --git-dir >/dev/null 2>&1 || fail "当前目录不是 git 仓库: $REPO_DIR"

# 2. 检查 origin 远端是否存在
git remote get-url origin >/dev/null 2>&1 || fail "origin 远端不存在"

# 3. 配置 remote.origin.fetch 为全分支 refspec (bug 3 修复)
CURRENT_FETCH=$(git config remote.origin.fetch 2>/dev/null || echo "")
if [ "$CURRENT_FETCH" != "$EXPECTED_FETCH" ]; then
    git config remote.origin.fetch "$EXPECTED_FETCH"
    log "已配置 remote.origin.fetch = $EXPECTED_FETCH (bug 3 修复)"
else
    log "remote.origin.fetch 已是全分支配置, 无需修改"
fi

# 4. fetch 全分支 + prune 已删除分支
log "fetch origin (全分支 + prune)..."
if ! git fetch origin --prune 2>&1; then
    fail "git fetch origin 失败"
fi

# 5. 列出所有远端分支 (验证可见性)
log "=== 远端所有分支 (现在全部可见) ==="
git branch -r | sed 's/^/  /'

# 6. 检查本地是否有过时的 remote-tracking 引用 (已 prune)
STALE=$(git branch -r --list 'origin/*' | wc -l)
log "本地 remote-tracking 引用数: $STALE"

log "✓ 仓库初始化完成 (远端分支全部可见)"
