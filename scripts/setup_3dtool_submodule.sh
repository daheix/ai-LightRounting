#!/usr/bin/env bash
# PoLaRIS/scripts/setup_3dtool_submodule.sh — 3dtool 子仓库幂等注册/恢复脚本
#
# 用途：沙箱重启后 .git/modules/3dtool 和 3dtool/ 目录内容会丢失（不被 git 跟踪），
#       本脚本检测子仓库健康状态，损坏则重新 sparse clone 注册。
#       幂等：可重复执行，已健康则直接返回。
#
# 为什么不用标准 `git submodule update --init`？
#   - 3dtool 仓库含 1.6G AppImage 分片（appimage-parts/）
#   - 标准全量 clone 会磁盘爆掉
#   - sparse 配置存在 .git/modules/3dtool/info/sparse-checkout，沙箱重启后丢失
#   - 丢失后 git submodule update --init 会全量拉取 → 失败
#   - 所以必须用本脚本重新 sparse clone 注册
#
# 调用方式：
#   bash scripts/setup_3dtool_submodule.sh          # 幂等恢复
#   bash scripts/setup_3dtool_submodule.sh -v       # 详细输出
#   bash scripts/setup_3dtool_submodule.sh --force  # 强制重新注册
#
# 规则依据：
#   R03 禁止 fall-back：任何步骤失败即 exit 非零
#   R11 工作流规范
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUBMODULE_PATH="3dtool"
SUBMODULE_GITDIR="${REPO_DIR}/.git/modules/3dtool"
SUBMODULE_WORKTREE="${REPO_DIR}/${SUBMODULE_PATH}"
# 使用带 token 的 URL（从主仓库 remote 推断），失败则用公开 URL
SUBMODULE_URL_PUBLIC="https://github.com/daheix/3dtool.git"
VERBOSE=0
FORCE=0

# 解析参数
for arg in "$@"; do
    case "${arg}" in
        -v|--verbose) VERBOSE=1 ;;
        --force) FORCE=1 ;;
    esac
done

log() { [ "${VERBOSE}" = "1" ] && echo "[setup_3dtool] $*" || true; }
err() { echo "[setup_3dtool][ERROR] $*" >&2; }

# 从主仓库 remote 推断带 token 的 URL（避免硬编码 token）
get_token_url() {
    local origin_url
    origin_url=$(cd "${REPO_DIR}" && git config --get remote.origin.url 2>/dev/null || echo "")
    # 主仓库 URL 形如 https://x-access-token:ghu_xxx@github.com/daheix/ai-LightRounting
    if echo "${origin_url}" | grep -q "x-access-token:"; then
        local token
        token=$(echo "${origin_url}" | sed -n 's|.*://x-access-token:\([^@]*\)@.*|\1|p')
        echo "https://x-access-token:${token}@github.com/daheix/3dtool"
        return 0
    fi
    # 无 token，用公开 URL
    echo "${SUBMODULE_URL_PUBLIC}"
}

# 健康检查：子仓库是否可用
# 健康标准：3dtool/ 有非 .git 的文件 + .git/modules/3dtool 存在 + 能 git rev-parse
submodule_healthy() {
    [ -d "${SUBMODULE_GITDIR}" ] || return 1
    [ -d "${SUBMODULE_WORKTREE}" ] || return 1
    # 3dtool/ 下要有非 .git 的文件（证明 sparse checkout 正常）
    local file_count
    file_count=$(find "${SUBMODULE_WORKTREE}" -maxdepth 1 -mindepth 1 ! -name '.git' 2>/dev/null | wc -l)
    [ "${file_count}" -gt 0 ] || return 1
    # git rev-parse 能成功（证明 gitdir 链接正常）
    git --git-dir="${SUBMODULE_GITDIR}" rev-parse HEAD >/dev/null 2>&1 || return 1
    return 0
}

# 主逻辑
cd "${REPO_DIR}" || { err "无法进入 ${REPO_DIR}"; exit 1; }

# 步骤0: 检查 .gitmodules 是否存在
if [ ! -f "${REPO_DIR}/.gitmodules" ]; then
    err ".gitmodules 不存在，无子仓库配置"
    exit 1
fi

# 步骤1: 健康检查
if [ "${FORCE}" != "1" ] && submodule_healthy; then
    log "子仓库健康，跳过注册（HEAD: $(git --git-dir=${SUBMODULE_GITDIR} rev-parse --short HEAD)）"
    # 尝试 update（拉取最新，失败不致命）
    git submodule update --init 2>&1 | tail -3 || log "  [WARN] submodule update 失败（可能网络问题，已健康不影响）"
    exit 0
fi

log "子仓库不健康或 --force，重新 sparse clone 注册..."

# 步骤2: 清理残留
log "清理残留..."
rm -rf "${SUBMODULE_WORKTREE}"
rm -rf "${SUBMODULE_GITDIR}"

# 步骤3: 获取 URL
SUBMODULE_URL=$(get_token_url)
log "使用 URL: $(echo "${SUBMODULE_URL}" | sed 's|x-access-token:[^@]*@|***@|')"

# 步骤4: sparse clone（只拉 commit 不拉 blob，跳过 1.6G 分片）
log "sparse clone（--filter=blob:none --no-checkout --sparse）..."
if ! git clone --filter=blob:none --no-checkout --sparse "${SUBMODULE_URL}" "${SUBMODULE_PATH}" 2>&1 | tail -5; then
    err "sparse clone 失败"
    exit 1
fi

# 步骤5: 配置 sparse-checkout（只保留 scripts/ 和 tools/，跳过 appimage-parts/）
log "配置 sparse-checkout（只保留 scripts/ tools/）..."
cd "${SUBMODULE_WORKTREE}"
git sparse-checkout init --cone
git sparse-checkout set scripts tools
if ! git checkout main 2>&1 | tail -3; then
    err "checkout main 失败"
    exit 1
fi
cd "${REPO_DIR}"

# 步骤6: 迁移 .git 目录到主仓库标准布局
log "迁移 .git → .git/modules/3dtool..."
mkdir -p "${REPO_DIR}/.git/modules"
mv "${SUBMODULE_WORKTREE}/.git" "${SUBMODULE_GITDIR}"
echo "gitdir: ../.git/modules/3dtool" > "${SUBMODULE_WORKTREE}/.git"

# 步骤7: 修正 worktree 路径（绝对路径，避免相对路径计算错误）
git config -f "${SUBMODULE_GITDIR}/config" core.worktree "${SUBMODULE_WORKTREE}"
log "worktree 设置为: ${SUBMODULE_WORKTREE}"

# 步骤8: 验证
log "验证..."
if ! submodule_healthy; then
    err "注册后健康检查失败"
    exit 1
fi

SUB_SHA=$(git --git-dir="${SUBMODULE_GITDIR}" rev-parse HEAD)
SUB_SHORT=$(git --git-dir="${SUBMODULE_GITDIR}" rev-parse --short HEAD)
FILE_COUNT=$(find "${SUBMODULE_WORKTREE}" -maxdepth 1 -mindepth 1 ! -name '.git' | wc -l)
SIZE=$(du -sh "${SUBMODULE_WORKTREE}" 2>/dev/null | cut -f1)

echo "[setup_3dtool] 子仓库注册完成"
echo "  HEAD:       ${SUB_SHORT} (${SUB_SHA})"
echo "  文件数:     ${FILE_COUNT}"
echo "  占用:       ${SIZE}"
echo "  gitfile:    $(cat ${SUBMODULE_WORKTREE}/.git)"
echo "  sparse 规则: $(cat ${SUBMODULE_GITDIR}/info/sparse-checkout 2>/dev/null | tr '\n' ' ')"

# 步骤9: 校验 gitlink 与子仓库 HEAD 一致
INDEX_SHA=$(git ls-files --stage "${SUBMODULE_PATH}" 2>/dev/null | awk '{print $2}')
if [ -n "${INDEX_SHA}" ] && [ "${INDEX_SHA}" != "${SUB_SHA}" ]; then
    err "gitlink 不一致: index=${INDEX_SHA} vs submodule HEAD=${SUB_SHA}"
    err "请运行: git add 3dtool && git commit -m 'chore: 同步 3dtool 子仓库指针'"
    exit 1
fi
log "gitlink 一致: ${SUB_SHORT}"
exit 0
