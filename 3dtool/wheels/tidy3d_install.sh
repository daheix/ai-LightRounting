#!/usr/bin/env bash
# Tidy3D 2.11.2 离线/在线安装脚本
# 安装到 3dtool/wheels/tidy3d/ 目录，供 PoLaRIS FDTD 后端使用
#
# 来源:
# - Tidy3D PyPI: https://pypi.org/project/tidy3d/
# - Tidy3D 文档: https://docs.flexcompute.com/projects/tidy3d/
#
# 用法:
#   bash 3dtool/wheels/tidy3d/install.sh
#
# 环境要求:
#   - Python 3.10-3.14（Tidy3D 2.11.2 支持）
#   - pip >= 23.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${SCRIPT_DIR}"

echo "[1/3] 安装 Tidy3D 2.11.2 到 ${TARGET_DIR} ..."
pip install --target="${TARGET_DIR}" tidy3d==2.11.2

echo "[2/3] 验证导入 ..."
PYTHONPATH="${TARGET_DIR}:${PYTHONPATH:-}" python -c "
import tidy3d as td
print('tidy3d version:', td.__version__)
print('C_0:', td.C_0)
print('OK')
"

echo "[3/3] 安装完成。"
echo "PoLaRIS FDTD 模块会自动将 ${TARGET_DIR} 加入 sys.path。"
echo "如需云端求解，设置环境变量 TIDY3D_API_KEY。"
