#!/usr/bin/env bash
# 3dtool/env.sh — 全局环境变量配置（source 后生效）
#
# 用途：使 Python 与仿真工具优先使用项目自带 pyenv 环境而非系统默认。
# 来源：spec init-py-env-and-3dtool-disk-cleanup Task 2 (R11 工程基础自动化)
#
# 用法：
#   source 3dtool/env.sh
#
# 导出变量：
#   PYENV_ROOT  — pyenv 根目录
#   PATH        — pyenv shims + pyenv bin 优先
#   PYTHONPATH  — 含 3dtool 工具入口（如有）
#   VIRTUAL_ENV — 取消（避免误用旧 venv）

# pyenv 根目录（兼容默认安装位置）
if [ -z "${PYENV_ROOT:-}" ]; then
    export PYENV_ROOT="${HOME}/.pyenv"
fi

# pyenv shims 必须在 PATH 最前，确保 `python` 命令走 pyenv 管理的版本
if [ -d "${PYENV_ROOT}/shims" ]; then
    case ":${PATH}:" in
        *":${PYENV_ROOT}/shims:"*) : ;;  # 已存在，不重复加
        *) export PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}" ;;
    esac
fi

# 取消可能残留的旧虚拟环境变量，避免误用
unset VIRTUAL_ENV

# 3dtool 工具入口（子模块内的可执行工具，如 future bin/）
_3DTOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "${_3DTOOL_DIR}/bin" ]; then
    case ":${PATH}:" in
        *":${_3DTOOL_DIR}/bin:"*) : ;;
        *) export PATH="${_3DTOOL_DIR}/bin:${PATH}" ;;
    esac
fi
unset _3DTOOL_DIR

# PYTHONPATH：确保 pcb_parser 可导入（editable 安装后通常不需要，此处兜底）
# 不强制覆盖，仅在未设置时给默认
: "${PYTHONPATH:=}"
export PYTHONPATH
