#!/usr/bin/env bash
# PoLaRIS/init_env.sh — 完整环境初始化一站式脚本（拉取子仓库 + 安装 + 验证 + 守护进程）
#
# 标准：参照 3dtool 子仓库四文件模式，PoLaRIS 项目级整合入口
#
# 用途：fresh clone 或沙箱重启后，一键完成：
#   1. source env.sh（环境变量：pyenv / PATH / JAX CPU 强制）
#   2. 修复 shallow clone（sandbox 反复出现的 git 浅克隆问题）
#   3. 拉取 3dtool 子仓库（git submodule update --init）
#   4. 安装核心依赖（jax CPU / numpy / scipy / sax / klayout 等）
#   5. editable 安装 PoLaRIS 33 模块
#   6. 验证环境（四重检查）
#   7. 启动守护进程（auto_commit V8 每 6 分钟 + keepalive 每 5 分钟）
#
# 使用方法：
#   bash init_env.sh              # 完整初始化（推荐首次使用）
#   bash init_env.sh --quick      # 跳过 unshallow + submodule（已初始化时快速恢复）
#   bash init_env.sh --no-daemon  # 不启动守护进程
#   bash init_env.sh -v           # 详细输出
#
# 前置条件：
#   - git 已配置 remote origin（带 token 或公开仓库）
#   - Python 3.10+ + pip 可用
#   - 网络可访问 PyPI 和 GitHub
#
# 规则依据：
#   R03 禁止 fall-back：任何步骤失败即 exit，不静默跳过
#   R04 不参与 GPU：jax 强制 CPU
#   R11 工作流规范：main 分支 + 守护进程
#   R12 时间戳规范
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"
QUICK=0
NO_DAEMON=0
VERBOSE=0

# 时间戳（R12）
ts() { date "+%Y-%m-%d %H:%M:%S"; }

log() { echo "[$(ts)] [init_env] $*"; }
logv() { [ "${VERBOSE}" = "1" ] && echo "[$(ts)] [init_env][V] $*" || true; }
err() { echo "[$(ts)] [init_env][ERROR] $*" >&2; }

# 解析参数
for arg in "$@"; do
    case "${arg}" in
        --quick) QUICK=1 ;;
        --no-daemon) NO_DAEMON=1 ;;
        -v|--verbose) VERBOSE=1 ;;
        -h|--help)
            sed -n '2,30p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
    esac
done

echo "========================================"
echo "  PoLaRIS 环境初始化（$(ts)）"
echo "========================================"
echo "仓库: ${REPO_DIR}"
echo "参数: quick=${QUICK} no_daemon=${NO_DAEMON} verbose=${VERBOSE}"
echo ""

# 步骤0: 检查分支（R11: 必须在 main）
log "[0/7] 检查 git 分支..."
cd "${REPO_DIR}"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "${CURRENT_BRANCH}" != "main" ]; then
    err "当前分支: ${CURRENT_BRANCH}（R11 要求 main 分支）"
    err "请先: git checkout main"
    exit 1
fi
log "  分支: main ✓"

# 步骤1: source env.sh（环境变量）
log "[1/7] 加载环境变量..."
if [ -f "${REPO_DIR}/env.sh" ]; then
    # shellcheck disable=SC1091
    source "${REPO_DIR}/env.sh"
    log "  env.sh 已加载（PYENV_ROOT=${PYENV_ROOT:-未设}, JAX_PLATFORMS=${JAX_PLATFORMS:-未设}）"
else
    err "env.sh 不存在: ${REPO_DIR}/env.sh"
    exit 1
fi

if [ "${QUICK}" = "1" ]; then
    log "[quick 模式] 跳过 unshallow 和 submodule，直接安装依赖"
    # 跳到步骤4
    log "[2-3/7] 跳过（quick 模式）"
    SKIP_SUBMODULE=1
else
    SKIP_SUBMODULE=0
    # 步骤2: 修复 shallow clone
    log "[2/7] 修复 shallow clone..."
    cd "${REPO_DIR}"
    COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo 0)
    if [ "${COMMIT_COUNT}" -lt 100 ] || [ -f .git/shallow ]; then
        logv "  当前 ${COMMIT_COUNT} commits，执行 unshallow..."
        git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null || true
        git fetch --unshallow origin 2>&1 | tail -3 || {
            err "unshallow 失败（网络或权限问题）"
            exit 1
        }
        NEW_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo 0)
        log "  unshallow 完成: ${COMMIT_COUNT} → ${NEW_COUNT} commits"
    else
        log "  git 历史完整 (${COMMIT_COUNT} commits)，跳过"
    fi

    # 步骤3: 恢复 3dtool 子仓库（幂等 sparse clone 注册）
    # 不用 git submodule update --init（会全量拉 1.6G 爆磁盘）
    log "[3/7] 恢复 3dtool 子仓库（幂等 sparse clone 注册）..."
    SETUP_SUBMODULE="${REPO_DIR}/scripts/setup_3dtool_submodule.sh"
    if [ -f "${SETUP_SUBMODULE}" ]; then
        SETUP_ARGS=""
        [ "${VERBOSE}" = "1" ] && SETUP_ARGS="-v"
        if ! bash "${SETUP_SUBMODULE}" ${SETUP_ARGS}; then
            err "3dtool 子仓库恢复失败（R03 禁止 fall-back）"
            exit 1
        fi
        SUB_STATUS=$(git submodule status 2>&1 | head -1)
        log "  submodule: ${SUB_STATUS}"
    else
        err "setup_3dtool_submodule.sh 不存在: ${SETUP_SUBMODULE}"
        exit 1
    fi
fi

# 步骤4: 安装核心依赖 + 33 模块（调用 install.sh）
log "[4/7] 安装依赖与模块（调用 install.sh）..."
if [ "${QUICK}" = "1" ]; then
    INSTALL_ARGS="--no-unshallow"
else
    INSTALL_ARGS=""
fi
if [ "${VERBOSE}" = "1" ]; then
    INSTALL_ARGS="${INSTALL_ARGS} -v"
fi
if ! bash "${REPO_DIR}/install.sh" ${INSTALL_ARGS}; then
    err "install.sh 执行失败"
    exit 1
fi
log "  install.sh 完成"

# 步骤5: 验证环境（调用 ensure_env.sh）
log "[5/7] 验证环境（四重检查）..."
if ! bash "${REPO_DIR}/ensure_env.sh" -v; then
    err "ensure_env.sh 验证失败，环境不完整（R03 禁止 fall-back）"
    exit 1
fi
log "  环境验证通过 ✓"

# 步骤6: 启动守护进程
if [ "${NO_DAEMON}" = "1" ]; then
    log "[6/7] 跳过守护进程（--no-daemon）"
else
    log "[6/7] 启动守护进程..."

    # 6a: keepalive（每 5 分钟 touch 防超时，R10）
    if pgrep -f "keepalive" >/dev/null 2>&1; then
        log "  keepalive 已在运行"
    else
        if [ -f "${REPO_DIR}/scripts/keepalive.sh" ]; then
            nohup bash "${REPO_DIR}/scripts/keepalive.sh" >/dev/null 2>&1 &
            log "  keepalive 已启动 (PID=$!)"
        else
            # 兜底：内联保活
            nohup bash -c 'while true; do date >> /tmp/keepalive.log; sleep 300; done' >/dev/null 2>&1 &
            log "  keepalive (内联) 已启动 (PID=$!)"
        fi
    fi

    # 6b: auto_commit V8（每 6 分钟检测变更→提交→push，R11）
    if pgrep -f "auto_commit" >/dev/null 2>&1; then
        log "  auto_commit 已在运行"
    else
        if [ -f "${REPO_DIR}/scripts/auto_commit.py" ]; then
            nohup python "${REPO_DIR}/scripts/auto_commit.py" V8 >/dev/null 2>&1 &
            log "  auto_commit V8 已启动 (PID=$!)"
        else
            logv "  scripts/auto_commit.py 不存在，跳过"
        fi
    fi
fi

# 步骤7: 最终状态
log "[7/7] 最终状态检查..."
echo ""
echo "========================================"
echo "  PoLaRIS 环境初始化完成！($(ts))"
echo "========================================"
echo "分支:        $(git branch --show-current)"
echo "commits:     $(git rev-list --count HEAD 2>/dev/null)"
echo "submodule:   $(git submodule status 2>&1 | head -1)"
echo "Python:      $(python --version 2>&1)"
echo "JAX 平台:    ${JAX_PLATFORMS:-未设}（R04 CPU 合规）"
echo "标记文件:    $(cat /tmp/.polaris_installed 2>/dev/null || echo '未写入')"
echo ""
echo "常用命令:"
echo "  source env.sh                    # 加载环境变量"
echo "  bash ensure_env.sh -v            # 检查环境"
echo "  python -m pytest -q              # 运行测试"
echo "  python -m ruff check modules/    # 代码检查"
echo ""
echo "守护进程:"
echo "  keepalive:   $(pgrep -f keepalive >/dev/null && echo '运行中' || echo '未运行')"
echo "  auto_commit: $(pgrep -f auto_commit >/dev/null && echo '运行中' || echo '未运行')"
echo "========================================"
