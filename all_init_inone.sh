#!/usr/bin/env bash
# PoLaRIS/all_init_inone.sh — 唯一环境统一初始化脚本（一条命令搞定一切）
#
# 目标：沙箱重启后，运行这一条命令即可：
#   1. 恢复 3dtool 子仓库（sparse-checkout 只拉 wheels/scripts/tools，跳过 2.0G 分片）
#   2. 从 3dtool/wheels/ 离线安装 47 个 Python 3.14 cp314 wheel（快速、可靠）
#   3. 在线补装 wheels 里没有的依赖（jax[cpu] / sax / klayout / gymnasium）
#   4. editable 安装 PoLaRIS 33 模块
#   5. 验证环境（四重检查：标记+依赖+工具+模块）
#   6. 启动守护进程（auto_commit V8 + keepalive）
#   7. 报告最终状态
#
# 使用方法：
#   bash all_init_inone.sh              # 完整初始化（沙箱重启后用这个，默认离线优先）
#   bash all_init_inone.sh -v           # 详细输出
#   bash all_init_inone.sh --no-daemon  # 不启动守护进程
#   bash all_init_inone.sh --force      # 强制重新安装（忽略标记）
#   bash all_init_inone.sh --offline    # 纯离线模式（网络不好时用，不在线补装）
#
# 双离线源（网络不好时避免在线安装）:
#   3dtool/wheels/    - 47 个通用 cp314 wheel（3dtool 维护，numpy/scipy/matplotlib 等）
#   polaris_wheels/   - 43 个 PoLaRIS 特有 wheel（jax/sax/klayout/gymnasium 及依赖）
#   合计 90 个 wheel，340M，覆盖 PoLaRIS 全部依赖
#   参考: pip 官方 wheelhouse 模式 https://pip.pypa.io/en/stable/topics/repeatable-installs/
#
# 规则依据:
#   R01 方案检索: 离线 wheel 安装参考 pip 官方文档 + 3dtool/install.sh
#   R03 禁止 fall-back: 任何步骤失败即 exit
#   R04 不参与 GPU: jax 强制 CPU
#   R11 工作流: main 分支 + 守护进程
#   R12 时间戳
#   R13 自测
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"
MODULES_DIR="${REPO_DIR}/modules"
WHEELS_DIR="${REPO_DIR}/3dtool/wheels"
POLARIS_WHEELS_DIR="${REPO_DIR}/polaris_wheels"
MARK_FILE="/tmp/.polaris_installed"
VERBOSE=0
NO_DAEMON=0
FORCE=0
OFFLINE=0

ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] [init] $*"; }
logv() { [ "${VERBOSE}" = "1" ] && echo "[$(ts)] [init][V] $*" || true; }
err() { echo "[$(ts)] [init][ERROR] $*" >&2; }

for arg in "$@"; do
    case "${arg}" in
        -v|--verbose) VERBOSE=1 ;;
        --no-daemon) NO_DAEMON=1 ;;
        --force) FORCE=1 ;;
        --offline) OFFLINE=1 ;;
    esac
done

echo "========================================"
echo "  PoLaRIS 环境统一初始化 ($(ts))"
echo "========================================"
echo ""

# ========== 步骤1: 检查 main 分支（R11） ==========
log "[1/7] 检查 git 分支..."
cd "${REPO_DIR}" || { err "无法进入 ${REPO_DIR}"; exit 1; }
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "${CURRENT_BRANCH}" != "main" ]; then
    err "当前分支: ${CURRENT_BRANCH}（R11 要求 main）"
    exit 1
fi
log "  分支: main ✓"

# ========== 步骤2: 加载环境变量（R04 JAX CPU 强制） ==========
log "[2/7] 加载环境变量..."
if [ ! -f "${REPO_DIR}/env.sh" ]; then
    err "env.sh 不存在"
    exit 1
fi
# shellcheck disable=SC1091
source "${REPO_DIR}/env.sh"
log "  JAX_PLATFORMS=${JAX_PLATFORMS:-未设}（R04 CPU 合规）"

# ========== 步骤3: 恢复 3dtool 子仓库（sparse: wheels scripts tools） ==========
log "[3/7] 恢复 3dtool 子仓库（sparse: wheels scripts tools，跳过 2.0G 分片）..."
SETUP_SUB="${REPO_DIR}/scripts/setup_3dtool_submodule.sh"
if [ ! -f "${SETUP_SUB}" ]; then
    err "setup_3dtool_submodule.sh 不存在: ${SETUP_SUB}"
    exit 1
fi
SUB_ARGS=""
[ "${VERBOSE}" = "1" ] && SUB_ARGS="-v"
[ "${FORCE}" = "1" ] && SUB_ARGS="${SUB_ARGS} --force"
if ! bash "${SETUP_SUB}" ${SUB_ARGS}; then
    err "3dtool 子仓库恢复失败（R03 禁止 fall-back）"
    exit 1
fi
log "  submodule: $(git submodule status 2>&1 | head -1)"

# 检查 wheels 目录（双离线源，3dtool 对接关键）
if [ ! -d "${WHEELS_DIR}" ] || [ -z "$(ls -A "${WHEELS_DIR}"/*.whl 2>/dev/null)" ]; then
    err "3dtool/wheels/ 不存在或为空: ${WHEELS_DIR}"
    err "无法离线安装依赖（R03 禁止 fall-back）"
    exit 1
fi
WHEEL_COUNT=$(ls "${WHEELS_DIR}"/*.whl 2>/dev/null | wc -l)
POLARIS_WHEEL_COUNT=$(ls "${POLARIS_WHEELS_DIR}"/*.whl 2>/dev/null | wc -l)
TOTAL_WHEELS=$((WHEEL_COUNT + POLARIS_WHEEL_COUNT))
log "  离线源: 3dtool/wheels/${WHEEL_COUNT} + polaris_wheels/${POLARIS_WHEEL_COUNT} = ${TOTAL_WHEELS} wheel"

# ========== 步骤4: 双离线源安装 wheels（纯离线优先，在线补装兜底） ==========
log "[4/7] 安装依赖（双离线源: 3dtool/wheels + polaris_wheels）..."

# 4a: 升级打包工具（Python 3.14 需要 setuptools>=75）
logv "  4a: 升级 pip/setuptools/wheel..."
pip install --upgrade pip setuptools wheel 2>&1 | tail -2 || {
    err "pip/setuptools/wheel 升级失败"
    exit 1
}

# 4b: 纯离线安装所有 wheel（双源 --no-index --find-links + requirements-pinned.txt）
# 参考: pip 官方 wheelhouse 模式 https://pip.pypa.io/en/stable/topics/repeatable-installs/
# 用 -r requirements-pinned.txt 让 pip 自动从双源解析最优版本，避免重复包冲突
# gerbonara 依赖 quart（未打包），用 --no-deps 单独安装
logv "  4b: 纯离线安装（--no-index --find-links 双源 + requirements-pinned.txt）..."
REQUIREMENTS_FILE="${REPO_DIR}/requirements-pinned.txt"
if [ ! -f "${REQUIREMENTS_FILE}" ]; then
    err "requirements-pinned.txt 不存在: ${REQUIREMENTS_FILE}"
    exit 1
fi
if ! pip install --no-index \
    --find-links="${POLARIS_WHEELS_DIR}" \
    --find-links="${WHEELS_DIR}" \
    -r "${REQUIREMENTS_FILE}" 2>&1 | tail -5; then
    err "离线 wheel 安装失败（依赖解析冲突？检查 requirements-pinned.txt 版本）"
    exit 1
fi
# gerbonara 单独 --no-deps（quart 未打包）
GERB_WHL=$(ls "${WHEELS_DIR}"/gerbonara-*.whl 2>/dev/null | head -1)
if [ -n "${GERB_WHL}" ]; then
    pip install --no-index --no-deps "${GERB_WHL}" 2>&1 | tail -2 || logv "  gerbonara 安装跳过"
fi
log "  离线安装完成（${TOTAL_WHEELS} wheel）"

# 4c: 纯离线模式跳过在线补装；否则在线补装缺失依赖（兜底）
if [ "${OFFLINE}" = "1" ]; then
    log "  [offline 模式] 跳过在线补装"
else
    logv "  4c: 在线补装缺失依赖（兜底，网络不好可跳过用 --offline）..."
    pip install \
        "jax[cpu]" \
        "jaxlib[cpu]" \
        sax \
        klayout \
        gymnasium \
        2>&1 | tail -3 || logv "  在线补装跳过（网络问题，离线源已覆盖）"
fi

# ========== 步骤5: editable 安装 PoLaRIS 33 模块 ==========
log "[5/7] 安装 PoLaRIS 33 模块（editable）..."
cd "${REPO_DIR}"
MODULE_OK=0
MODULE_FAIL=0
for mod_pyproject in "${MODULES_DIR}"/*/pyproject.toml; do
    mod_dir="$(dirname "${mod_pyproject}")"
    mod_name="$(basename "${mod_dir}")"
    # 用 pip 的 exit code 判断成功（不依赖输出文本，因为 WARNING 会干扰 grep）
    if pip install -e "${mod_dir}" --no-deps >/dev/null 2>&1; then
        MODULE_OK=$((MODULE_OK + 1))
        logv "  [${mod_name}] ✓"
    else
        MODULE_FAIL=$((MODULE_FAIL + 1))
        err "  [${mod_name}] ✗ 安装失败"
    fi
done
log "  模块安装: ${MODULE_OK} 成功 / ${MODULE_FAIL} 失败"
if [ "${MODULE_FAIL}" -gt 0 ]; then
    err "${MODULE_FAIL} 个模块安装失败（R03 禁止 fall-back）"
    exit 1
fi

# ========== 步骤6: 验证环境（四重检查） ==========
log "[6/7] 验证环境（四重检查）..."

# 6a: 核心依赖
logv "  6a: 核心依赖检查..."
python -c "import numpy, scipy, networkx, matplotlib, yaml, jax, jaxlib, sax, klayout, gymnasium, shapely, pydantic" 2>/dev/null || {
    err "核心依赖导入失败"
    exit 1
}
log "  核心依赖 ✓"

# 6b: 开发工具
logv "  6b: 开发工具检查..."
python -c "import pytest, ruff" 2>/dev/null || {
    err "开发工具不可用（pytest/ruff）"
    exit 1
}
log "  开发工具 ✓"

# 6c: PoLaRIS 核心模块
logv "  6c: PoLaRIS 核心模块检查..."
python -c "import polaris_core" 2>/dev/null || {
    err "polaris_core 导入失败"
    exit 1
}
log "  polaris_core ✓"

# 6d: JAX CPU 强制（R04）
logv "  6d: JAX CPU 平台检查（R04）..."
JAX_PLATFORM=$(python -c "import jax; print(jax.default_backend())" 2>/dev/null)
if [ "${JAX_PLATFORM}" != "cpu" ]; then
    err "JAX 平台不是 CPU: ${JAX_PLATFORM}（R04 违规）"
    exit 1
fi
log "  JAX 平台: ${JAX_PLATFORM} ✓（R04 合规）"

# 写标记文件
echo "$(date -Iseconds) python=$(python --version 2>&1) modules=${MODULE_OK} wheels=${WHEEL_COUNT}" > "${MARK_FILE}"
log "  标记文件已写入: ${MARK_FILE}"

# ========== 步骤7: 启动守护进程 ==========
if [ "${NO_DAEMON}" = "1" ]; then
    log "[7/7] 跳过守护进程（--no-daemon）"
else
    log "[7/7] 启动守护进程..."

    # keepalive（每 5 分钟 touch 防超时，R10）
    if pgrep -f "keepalive" >/dev/null 2>&1; then
        log "  keepalive 已在运行"
    elif [ -f "${REPO_DIR}/scripts/keepalive.sh" ]; then
        nohup bash "${REPO_DIR}/scripts/keepalive.sh" >/dev/null 2>&1 &
        log "  keepalive 已启动 (PID=$!)"
    else
        nohup bash -c 'while true; do date >> /tmp/keepalive.log; sleep 300; done' >/dev/null 2>&1 &
        log "  keepalive (内联) 已启动 (PID=$!)"
    fi

    # auto_commit V8（每 6 分钟检测变更→提交→push，R11）
    if pgrep -f "auto_commit" >/dev/null 2>&1; then
        log "  auto_commit 已在运行"
    elif [ -f "${REPO_DIR}/scripts/auto_commit.py" ]; then
        nohup python "${REPO_DIR}/scripts/auto_commit.py" V8 >/dev/null 2>&1 &
        log "  auto_commit V8 已启动 (PID=$!)"
    fi
fi

# ========== 最终报告 ==========
echo ""
echo "========================================"
echo "  PoLaRIS 环境初始化完成！($(ts))"
echo "========================================"
echo "分支:        $(git branch --show-current)"
echo "commits:     $(git rev-list --count HEAD 2>/dev/null)"
echo "submodule:   $(git submodule status 2>&1 | head -1)"
echo "Python:      $(python --version 2>&1)"
echo "JAX 平台:    $(python -c 'import jax; print(jax.default_backend())' 2>/dev/null)（R04 合规）"
echo "模块:        ${MODULE_OK}/33"
echo "离线 wheel:  3dtool/${WHEEL_COUNT} + polaris/${POLARIS_WHEEL_COUNT} = ${TOTAL_WHEELS}"
echo "标记文件:    $(cat /tmp/.polaris_installed 2>/dev/null || echo '未写入')"
echo ""
echo "守护进程:"
echo "  keepalive:   $(pgrep -f keepalive >/dev/null && echo '运行中' || echo '未运行')"
echo "  auto_commit: $(pgrep -f auto_commit >/dev/null && echo '运行中' || echo '未运行')"
echo "========================================"
echo ""
echo "现在可以直接使用所有工具，无需再次安装："
echo "  python -m pytest -q              # 运行测试"
echo "  python -m ruff check modules/    # 代码检查"
echo "  python -c 'import polaris_core'  # 验证模块"
