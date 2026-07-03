#!/usr/bin/env bash
# PoLaRIS/ensure_env.sh — 环境自动检查与恢复（幂等，可重复执行）
#
# 标准：参照 3dtool 子仓库 ensure_env.sh 四文件模式
#       标记文件 / 三重检查 / 失败触发 install.sh / 幂等
#
# 用途：每次会话/工具调用前自动检查环境，缺失则自动恢复。
#       沙箱重启后 /tmp 标记消失，自动触发 install.sh。
#
# 调用方式：
#   bash ensure_env.sh          # 静默检查，缺失才恢复
#   bash ensure_env.sh -v       # 详细输出
#
# 自动触发场景（任一条件失败即恢复）：
#   1. /tmp/.polaris_installed 标记不存在（沙箱重启后）
#   2. 关键依赖导入失败（numpy/scipy/jax/sax/klayout 等）
#   3. 开发工具不可用（pytest/ruff/mypy）
#   4. PoLaRIS 核心模块不可导入（polaris_core）
#
# 幂等性：已安装则直接返回 0，不重复安装。
#
# 规则依据：R03 禁止 fall-back（失败即退出告警，不静默兜底）
#           R11 工作流规范
#           R04 不参与 GPU（仅 CPU JAX）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARK_FILE="/tmp/.polaris_installed"
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
# 依赖来源：PoLaRIS 33 模块共用核心依赖
#   - numpy/scipy/networkx/matplotlib：数值计算与图论
#   - pyyaml：配置
#   - jax/jaxlib：自动微分（CPU 版，R04 合规）
#   - sax：电路仿真
#   - klayout（klm）：版图
#   - gymnasium：强化学习
#   - shapely：几何
#   - pydantic：数据模型
deps_ok() {
    python -c "import numpy, scipy, networkx, matplotlib, yaml, jax, jaxlib, sax, klayout, gymnasium, shapely, pydantic" 2>/dev/null
    return $?
}

# 条件3: 开发工具可用
tools_ok() {
    command -v pytest >/dev/null 2>&1 || return 1
    python -c "import pytest" 2>/dev/null || return 1
    python -c "import ruff" 2>/dev/null || return 1
    return 0
}

# 条件4: PoLaRIS 核心模块可导入
polaris_ok() {
    python -c "import polaris_core" 2>/dev/null
    return $?
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
elif ! polaris_ok; then
    log "PoLaRIS 核心模块不可导入"
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
