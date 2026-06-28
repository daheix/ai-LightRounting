#!/usr/bin/env bash
# -*- mode: shell-script; -*-
#
# env_setup.sh — 3dtool 环境变量配置脚本
#
# 用途：
#   配置 POLARIS_3DTOOL_HOME、PATH、LD_LIBRARY_PATH、PYTHONPATH，
#   使工具链调用 3dtool 自带 Python 3.14 与原生仿真工具（ngspice 等）。
#
# 用法：
#   source scripts/env_setup.sh         # 配置环境（source 模式，推荐）
#   bash scripts/env_setup.sh --check   # 自检模式（直接执行）
#   bash scripts/env_setup.sh --help    # 显示帮助
#
# 来源：
#   - AGENTS.md §16 空间清理（保留 Python 开发所需工具）
#   - spec 阶段五：3dtool 工具链环境配置
#   - R03 禁止 fall-back：3dtool 未安装即 exit 1 / return 1，不静默兜底
#   - R08 代码提交纪律
#
# 参考：
#   - AppImage AppRun 规范: https://specifications.freedesktop.org/appimage-spec/latest/
#   - GNU coreutils split:  https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html
#   - GNU tar + gzip 管道:  https://www.gnu.org/software/tar/manual/html_node/Using-Gzip.html
#   - Linux ld.so(8):       https://man7.org/linux/man-pages/man8/ld.so.8.html
#   - Bash set 内建:        https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html

set -euo pipefail

# ===== 核心变量 =====
# AppImage 工作目录优先级：
#   1. 3dtool/3dtool-appimage（restore_3dtool_appimage.sh 的默认输出位置，README 推荐）
#   2. 3dtool/subrepo/3dtool/3dtool-appimage（子仓库内，兼容旧 spec 假设）
# 来源：3dtool/subrepo/3dtool/3dtool/README.md（daheix/3dtool 仓库）
POLARIS_3DTOOL_HOME="/workspace/3dtool/subrepo/3dtool"
if [ -x "/workspace/3dtool/3dtool-appimage/AppRun" ]; then
    POLARIS_3DTOOL_APPIMAGE="/workspace/3dtool/3dtool-appimage"
elif [ -x "${POLARIS_3DTOOL_HOME}/3dtool-appimage/AppRun" ]; then
    POLARIS_3DTOOL_APPIMAGE="${POLARIS_3DTOOL_HOME}/3dtool-appimage"
else
    # 默认值（--check 模式会报告未安装）
    POLARIS_3DTOOL_APPIMAGE="/workspace/3dtool/3dtool-appimage"
fi
POLARIS_3DTOOL_APPRUN="${POLARIS_3DTOOL_APPIMAGE}/AppRun"

# ===== 颜色定义（ANSI） =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ===== 工具函数 =====
_is_sourced() {
    [[ "${BASH_SOURCE[0]}" != "${0}" ]]
}

_echo_red()    { printf "${RED}%b${NC}\n" "$*"; }
_echo_green()  { printf "${GREEN}%b${NC}\n" "$*"; }
_echo_yellow() { printf "${YELLOW}%b${NC}\n" "$*"; }
_echo_blue()   { printf "${BLUE}%b${NC}\n" "$*"; }

_show_help() {
    cat <<'EOF'
env_setup.sh — 3dtool 环境变量配置

用法:
  source scripts/env_setup.sh          配置环境变量（source 模式，推荐）
  bash scripts/env_setup.sh --check    自检模式，检查 3dtool 安装并运行 AppRun check
  bash scripts/env_setup.sh --help     显示本帮助

配置的环境变量:
  POLARIS_3DTOOL_HOME       3dtool 子仓库根目录
  POLARIS_3DTOOL_APPIMAGE   AppImage 工作目录
  PATH                      追加 ${POLARIS_3DTOOL_APPIMAGE}/bin
  LD_LIBRARY_PATH           追加 ${POLARIS_3DTOOL_APPIMAGE}/lib
  PYTHONPATH                追加 ${POLARIS_3DTOOL_APPIMAGE}/python

示例:
  source scripts/env_setup.sh
  bash scripts/env_setup.sh --check
EOF
}

_check_installed() {
    [[ -x "${POLARIS_3DTOOL_APPRUN}" ]]
}

# ===== --check 模式 =====
run_check() {
    if ! _check_installed; then
        _echo_red "[ERROR] 3dtool 未安装，请先解阻塞 clone daheix/3dtool（当前 token 401）"
        _echo_yellow "[HINT]  期望路径: ${POLARIS_3DTOOL_APPRUN}"
        exit 1
    fi
    _echo_green "[OK] 3dtool 已安装: ${POLARIS_3DTOOL_APPRUN}"
    _echo_blue "[INFO] 运行 AppRun check ..."
    "${POLARIS_3DTOOL_APPRUN}" check
    exit 0
}

# ===== source 模式（默认，无参数） =====
run_setup() {
    if ! _check_installed; then
        _echo_red "[ERROR] 3dtool 未安装，请先解阻塞 clone daheix/3dtool（当前 token 401）"
        _echo_yellow "[HINT]  期望路径: ${POLARIS_3DTOOL_APPRUN}"
        if _is_sourced; then
            return 1
        else
            _echo_yellow "[HINT]  直接执行不会配置当前 shell，建议: source scripts/env_setup.sh"
            exit 1
        fi
    fi

    export POLARIS_3DTOOL_HOME
    export POLARIS_3DTOOL_APPIMAGE
    export PATH="${POLARIS_3DTOOL_APPIMAGE}/bin:${PATH}"
    export LD_LIBRARY_PATH="${POLARIS_3DTOOL_APPIMAGE}/lib:${LD_LIBRARY_PATH:-}"
    export PYTHONPATH="${POLARIS_3DTOOL_APPIMAGE}/python:${PYTHONPATH:-}"

    _echo_green "[INFO] 3dtool 环境已配置"
    _echo_blue "[INFO] POLARIS_3DTOOL_HOME=${POLARIS_3DTOOL_HOME}"
    _echo_blue "[INFO] POLARIS_3DTOOL_APPIMAGE=${POLARIS_3DTOOL_APPIMAGE}"
    _echo_blue "[INFO] PATH 前缀=${POLARIS_3DTOOL_APPIMAGE}/bin"

    # 工具版本信息（辅助输出，调用 AppRun check 获取汇总，失败告警不退出）
    # AppRun 不支持 --version，改用 check 输出最后两行汇总
    local check_out
    if check_out=$("${POLARIS_3DTOOL_APPRUN}" check 2>&1 | tail -2); then
        _echo_blue "[INFO] 工具自检: ${check_out}"
    else
        _echo_yellow "[WARN] AppRun check 调用失败（环境已配置，自检不可用）"
    fi

    if _is_sourced; then
        return 0
    else
        _echo_yellow "[WARN] 直接执行不会影响当前 shell 环境，建议: source scripts/env_setup.sh"
        exit 0
    fi
}

# ===== 主入口 =====
main() {
    local cmd="${1:-}"
    case "${cmd}" in
        --check)
            run_check
            ;;
        --help|-h)
            _show_help
            exit 0
            ;;
        "")
            run_setup
            ;;
        *)
            _echo_red "[ERROR] 未知参数: ${cmd}"
            _show_help
            exit 1
            ;;
    esac
}

main "$@"
