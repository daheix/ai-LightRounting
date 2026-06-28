#!/usr/bin/env bash
# -*- mode: shell-script; -*-
#
# run_3dtool.sh — 3dtool AppRun 包装脚本
#
# 用途：
#   简化 3dtool 工具调用，统一通过 AppRun 入口执行原生仿真工具
#   （ngspice、klayout、openroad 等）。
#
# 用法：
#   bash scripts/run_3dtool.sh <tool> [args...]   # 执行指定工具
#   bash scripts/run_3dtool.sh                    # 默认执行 AppRun check
#   bash scripts/run_3dtool.sh check
#   bash scripts/run_3dtool.sh ngspice --version
#
# 来源：
#   - spec 阶段五：3dtool 工具链环境配置
#   - AGENTS.md §16 空间清理
#   - R03 禁止 fall-back：AppRun 不存在即 exit 1，不静默兜底
#
# 参考：
#   - AppImage AppRun:   https://specifications.freedesktop.org/appimage-spec/latest/
#   - Bash exec 内建:    https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html
#   - Bash set 内建:     https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html
#   - POSIX shell 参数:  https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html
#   - GNU coreutils:     https://www.gnu.org/software/coreutils/manual/coreutils.html

set -euo pipefail

# ===== 路径常量（自适应：优先 restore 脚本默认输出位置）=====
# 来源：3dtool/subrepo/3dtool/3dtool/README.md（daheix/3dtool 仓库）
if [ -x "/workspace/3dtool/3dtool-appimage/AppRun" ]; then
    POLARIS_3DTOOL_APPRUN="/workspace/3dtool/3dtool-appimage/AppRun"
elif [ -x "/workspace/3dtool/subrepo/3dtool/3dtool-appimage/AppRun" ]; then
    POLARIS_3DTOOL_APPRUN="/workspace/3dtool/subrepo/3dtool/3dtool-appimage/AppRun"
else
    POLARIS_3DTOOL_APPRUN="/workspace/3dtool/3dtool-appimage/AppRun"
fi

# ===== 颜色（ANSI） =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

_echo_red()    { printf "${RED}%b${NC}\n" "$*"; }
_echo_green()  { printf "${GREEN}%b${NC}\n" "$*"; }
_echo_yellow() { printf "${YELLOW}%b${NC}\n" "$*"; }
_echo_blue()   { printf "${BLUE}%b${NC}\n" "$*"; }

# ===== 前置检查（R03：禁止 fall-back，AppRun 不存在即退出） =====
if [[ ! -x "${POLARIS_3DTOOL_APPRUN}" ]]; then
    _echo_red "[ERROR] AppRun 不存在或不可执行: ${POLARIS_3DTOOL_APPRUN}"
    _echo_yellow "[HINT]  请先解阻塞 clone daheix/3dtool（当前 token 401）"
    exit 1
fi

# ===== 执行 =====
if [[ $# -eq 0 ]]; then
    _echo_blue "[INFO] 无参数，默认执行: AppRun check"
    exec "${POLARIS_3DTOOL_APPRUN}" check
fi

exec "${POLARIS_3DTOOL_APPRUN}" "$@"
