#!/usr/bin/env bash
# 3dtool/ensure_env.sh — 环境自动检查与恢复（幂等，可重复执行）
#
# 用途：每次会话/工具调用前自动检查环境，缺失则自动恢复。
#       沙箱重启后 /tmp 标记消失，自动触发 install.sh。
#
# 调用方式：
#   bash 3dtool/ensure_env.sh        # 静默检查，缺失才恢复
#   bash 3dtool/ensure_env.sh -v     # 详细输出
#
# 自动触发场景：
#   1. /tmp/.3dtool_installed 标记不存在（沙箱重启后）
#   2. 关键依赖导入失败（lark/pydantic/shapely 等）
#   3. 工具命令找不到（ruff/mypy/pytest）
#
# 幂等性：已安装则直接返回 0，不重复安装。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MARK_FILE="/tmp/.3dtool_installed"
INSTALL_SCRIPT="${SCRIPT_DIR}/install.sh"
VERBOSE=0

# 解析参数
if [ "${1:-}" = "-v" ]; then
    VERBOSE=1
fi

log() {
    if [ "${VERBOSE}" = "1" ]; then
        echo "[ensure_env] $*"
    fi
}

# 条件1: 标记文件存在且非空
mark_exists() {
    if [ -f "${MARK_FILE}" ] && [ -s "${MARK_FILE}" ]; then
        return 0
    fi
    return 1
}

# 条件2: 关键依赖可导入（即使标记存在，也抽查依赖防止标记过期）
deps_ok() {
    python -c "import lark, pydantic, shapely, scipy, rtree, openpyxl, reportlab, olefile, unlzw3" 2>/dev/null
    return $?
}

# 条件3: 开发工具可用
tools_ok() {
    command -v ruff >/dev/null 2>&1 || return 1
    command -v mypy >/dev/null 2>&1 || return 1
    python -c "import pytest" 2>/dev/null || return 1
    return 0
}

# 主检查逻辑
need_install=0

if ! mark_exists; then
    log "标记文件不存在: ${MARK_FILE}（沙箱可能已重启）"
    need_install=1
elif ! deps_ok; then
    log "关键依赖导入失败，标记可能过期"
    need_install=1
elif ! tools_ok; then
    log "开发工具不可用"
    need_install=1
fi

if [ "${need_install}" = "0" ]; then
    log "环境正常，无需恢复（标记: $(cat "${MARK_FILE}" 2>/dev/null)）"
    exit 0
fi

# 需要恢复
echo "[ensure_env] 环境缺失，自动执行 ${INSTALL_SCRIPT} ..."
if [ ! -f "${INSTALL_SCRIPT}" ]; then
    echo "[ensure_env][ERROR] install.sh 不存在: ${INSTALL_SCRIPT}" >&2
    exit 1
fi

bash "${INSTALL_SCRIPT}"
rc=$?
if [ "${rc}" != "0" ]; then
    echo "[ensure_env][ERROR] install.sh 执行失败 (exit=${rc})" >&2
    exit "${rc}"
fi

echo "[ensure_env] 环境已自动恢复"
exit 0
