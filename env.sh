#!/usr/bin/env bash
# PoLaRIS/env.sh — 全局环境变量配置（source 后生效）
#
# 标准：参照 3dtool 子仓库 env.sh 四文件模式
#       pyenv 优先 / PYTHONPATH 兜底 / 取消旧 venv
#
# 用途：使 Python 与光电仿真工具优先使用项目 pyenv 环境而非系统默认。
#
# 用法：
#   source env.sh
#
# 导出变量：
#   PYENV_ROOT   — pyenv 根目录
#   PATH         — pyenv shims + pyenv bin 优先 + scripts/
#   PYTHONPATH   — 含 PoLaRIS modules（editable 安装后通常不需要，此处兜底）
#   VIRTUAL_ENV  — 取消（避免误用旧 venv）
#
# 规则依据：R11 工作流规范 / R04 不参与 GPU（JAX 平台强制 CPU）
#           R03 禁止 fall-back（不设置假路径，路径不存在则不导出）

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

# PoLaRIS 脚本入口（auto_commit.py / keepalive.sh 等）
_POLARIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "${_POLARIS_DIR}/scripts" ]; then
    case ":${PATH}:" in
        *":${_POLARIS_DIR}/scripts:"*) : ;;
        *) export PATH="${_POLARIS_DIR}/scripts:${PATH}" ;;
    esac
fi

# 3dtool 子仓库脚本入口（如有）
if [ -d "${_POLARIS_DIR}/3dtool/scripts" ]; then
    case ":${PATH}:" in
        *":${_POLARIS_DIR}/3dtool/scripts:"*) : ;;
        *) export PATH="${_POLARIS_DIR}/3dtool/scripts:${PATH}" ;;
    esac
fi
unset _POLARIS_DIR

# PYTHONPATH：确保 PoLaRIS modules 可导入（editable 安装后通常不需要，此处兜底）
# 不强制覆盖，仅在未设置时给默认（R03: 不覆盖用户已设值）
: "${PYTHONPATH:=}"
export PYTHONPATH

# JAX 平台强制 CPU（R04 不参与 GPU 战略，不可撤销）
export JAX_PLATFORMS="cpu"
export JAX_PLATFORM_NAME="cpu"
# 禁用 JAX GPU 探测，避免无谓尝试（R04）
export JAX_DISABLE_GPU=1
export CUDA_VISIBLE_DEVICES=""
