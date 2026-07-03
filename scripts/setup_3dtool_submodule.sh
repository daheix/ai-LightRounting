#!/usr/bin/env bash
# PoLaRIS/scripts/setup_3dtool_submodule.sh — 3dtool 子仓库幂等注册/恢复脚本（标准 git 命令）
#
# 标准：使用 git 官方 submodule 命令族 + sparse-checkout，不手动 clone/update-index
#
# 用途：沙箱重启后 .git/modules/3dtool 和 3dtool/ 目录内容会丢失（不被 git 跟踪），
#       本脚本用标准 git 命令幂等恢复子仓库 + sparse-checkout（跳过 1.6G 分片）。
#
# 为什么用 --filter=blob:none + sparse-checkout？
#   - 3dtool 仓库含 1.6G AppImage 分片（appimage-parts/），全量 checkout 磁盘爆
#   - --filter=blob:none: partial clone，历史 blob 按需拉取
#   - sparse-checkout: 工作区只保留 scripts/ tools/，跳过 appimage-parts/
#   - 组合后只占 232K（vs 全量 2.1G）
#
# 认证策略（CI 标准分层）：
#   - .gitmodules: 公开 URL（https://github.com/daheix/3dtool.git），可提交，不含 token
#   - .git/config: 本地 URL（https://x-access-token:TOKEN@github.com/daheix/3dtool），带认证
#   - git submodule update --init 优先用 .git/config 的 URL
#   - 参考: https://blog.csdn.net/qq_42746084/article/details/154796008 (CI 子模块处理)
#
# 调用方式：
#   bash scripts/setup_3dtool_submodule.sh          # 幂等恢复
#   bash scripts/setup_3dtool_submodule.sh -v       # 详细输出
#   bash scripts/setup_3dtool_submodule.sh --force  # 强制重新注册
#
# 规则依据：
#   R01 方案检索: 标准流程来自 git-scm.com 官方文档 + CI 最佳实践
#   R03 禁止 fall-back: 任何步骤失败即 exit 非零
#   R11 工作流规范
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUBMODULE_PATH="3dtool"
SUBMODULE_GITDIR="${REPO_DIR}/.git/modules/3dtool"
SUBMODULE_WORKTREE="${REPO_DIR}/${SUBMODULE_PATH}"
VERBOSE=0
FORCE=0

# sparse-checkout 只保留的目录（跳过 2.0G 的 3dtool/appimage-parts/）
# wheels/: 47 个 Python 3.14 cp314 离线 wheel（122M，含 numpy/scipy/jax 等）
# scripts/: 3dtool 工具脚本
# tools/: AppImage 打包脚本
SPARSE_DIRS="wheels scripts tools"

# 解析参数
for arg in "$@"; do
    case "${arg}" in
        -v|--verbose) VERBOSE=1 ;;
        --force) FORCE=1 ;;
    esac
done

log() { [ "${VERBOSE}" = "1" ] && echo "[setup_3dtool] $*" || true; }
err() { echo "[setup_3dtool][ERROR] $*" >&2; }

# 从主仓库 remote 推断 token（避免硬编码）
# 主仓库 URL 形如 https://x-access-token:ghu_xxx@github.com/daheix/ai-LightRounting
get_token() {
    local origin_url token
    origin_url=$(cd "${REPO_DIR}" && git config --get remote.origin.url 2>/dev/null || echo "")
    if echo "${origin_url}" | grep -q "x-access-token:"; then
        token=$(echo "${origin_url}" | sed -n 's|.*://x-access-token:\([^@]*\)@.*|\1|p')
        echo "${token}"
        return 0
    fi
    return 1
}

# 配置 .git/config 的 submodule.3dtool.url（带 token）
# CI 标准分层：.gitmodules 公开 URL + .git/config 带 token URL
setup_submodule_url() {
    local token
    if ! token=$(get_token); then
        err "无法从 remote.origin.url 推断 token（主仓库无 x-access-token 认证）"
        err "请手动: git config submodule.3dtool.url <带token的URL>"
        return 1
    fi
    git config submodule."${SUBMODULE_PATH}".url "https://x-access-token:${token}@github.com/daheix/3dtool"
    git config submodule."${SUBMODULE_PATH}".active true
    log "submodule.${SUBMODULE_PATH}.url 已配置（带 token）"
    return 0
}

# 健康检查：子仓库是否可用
# 健康标准：3dtool/ 有非 .git 的文件 + .git/modules/3dtool 存在 + 能 git rev-parse
submodule_healthy() {
    [ -d "${SUBMODULE_GITDIR}" ] || return 1
    [ -d "${SUBMODULE_WORKTREE}" ] || return 1
    local file_count
    file_count=$(find "${SUBMODULE_WORKTREE}" -maxdepth 1 -mindepth 1 ! -name '.git' 2>/dev/null | wc -l)
    [ "${file_count}" -gt 0 ] || return 1
    git --git-dir="${SUBMODULE_GITDIR}" rev-parse HEAD >/dev/null 2>&1 || return 1
    return 0
}

# 应用 sparse-checkout（只保留 scripts/ tools/，跳过 1.6G 分片）
apply_sparse_checkout() {
    cd "${SUBMODULE_WORKTREE}" || return 1
    git sparse-checkout init --cone
    git sparse-checkout set ${SPARSE_DIRS}
    cd "${REPO_DIR}" || return 1
    log "sparse-checkout 已应用: ${SPARSE_DIRS}"
    return 0
}

# 主逻辑
cd "${REPO_DIR}" || { err "无法进入 ${REPO_DIR}"; exit 1; }

# 步骤0: 检查 .gitmodules 是否存在
if [ ! -f "${REPO_DIR}/.gitmodules" ]; then
    err ".gitmodules 不存在，无子仓库配置"
    exit 1
fi

# 步骤1: 健康检查（非 --force 时）
if [ "${FORCE}" != "1" ] && submodule_healthy; then
    log "子仓库健康，跳过注册（HEAD: $(git --git-dir=${SUBMODULE_GITDIR} rev-parse --short HEAD)）"
    # 确保 sparse 规则生效（沙箱重启后规则可能丢失，但 gitdir 还在）
    if ! git --git-dir="${SUBMODULE_GITDIR}" config core.sparseCheckout >/dev/null 2>&1; then
        log "sparse 配置丢失，重新应用..."
        apply_sparse_checkout
    fi
    exit 0
fi

log "子仓库不健康或 --force，用标准 git 命令恢复..."

# 步骤2: 清理残留（--force 或损坏时）
log "清理残留..."
rm -rf "${SUBMODULE_WORKTREE}"
rm -rf "${SUBMODULE_GITDIR}"

# 步骤3: 配置带 token 的 submodule URL（CI 标准分层）
log "配置 submodule URL（带 token）..."
if ! setup_submodule_url; then
    exit 1
fi

# 步骤4: 标准命令 clone + init（--filter=blob:none partial clone）
# 参考: https://git-scm.com/docs/git-sparse-checkout/ + CI 最佳实践
log "git submodule update --init --filter=blob:none（partial clone）..."
if ! git submodule update --init --filter=blob:none "${SUBMODULE_PATH}" 2>&1 | tail -5; then
    err "git submodule update --init 失败"
    exit 1
fi

# 步骤5: 应用 sparse-checkout（只保留 scripts/ tools/，跳过 1.6G appimage-parts/）
log "应用 sparse-checkout（只保留 ${SPARSE_DIRS}）..."
if ! apply_sparse_checkout; then
    err "sparse-checkout 应用失败"
    exit 1
fi

# 步骤6: 验证
log "验证..."
if ! submodule_healthy; then
    err "恢复后健康检查失败"
    exit 1
fi

SUB_SHA=$(git --git-dir="${SUBMODULE_GITDIR}" rev-parse HEAD)
SUB_SHORT=$(git --git-dir="${SUBMODULE_GITDIR}" rev-parse --short HEAD)
FILE_COUNT=$(find "${SUBMODULE_WORKTREE}" -maxdepth 1 -mindepth 1 ! -name '.git' | wc -l)
SIZE=$(du -sh "${SUBMODULE_WORKTREE}" 2>/dev/null | cut -f1)

echo "[setup_3dtool] 子仓库恢复完成（标准 git 命令）"
echo "  HEAD:       ${SUB_SHORT} (${SUB_SHA})"
echo "  文件数:     ${FILE_COUNT}"
echo "  占用:       ${SIZE}（sparse: ${SPARSE_DIRS}）"
echo "  URL 分层:   .gitmodules=公开 / .git/config=带token"

# 步骤7: 校验 gitlink 与子仓库 HEAD 一致
INDEX_SHA=$(git ls-files --stage "${SUBMODULE_PATH}" 2>/dev/null | awk '{print $2}')
if [ -n "${INDEX_SHA}" ] && [ "${INDEX_SHA}" != "${SUB_SHA}" ]; then
    err "gitlink 不一致: index=${INDEX_SHA} vs submodule HEAD=${SUB_SHA}"
    err "请运行: git add 3dtool && git commit -m 'chore: 同步 3dtool 子仓库指针'"
    exit 1
fi
log "gitlink 一致: ${SUB_SHORT}"
exit 0
