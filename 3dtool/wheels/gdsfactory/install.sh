#!/bin/bash
# gdsfactory 8.18.0 离线安装脚本
# 沙箱重启后一键恢复 gdsfactory 环境
# 用法: bash 3dtool/wheels/gdsfactory/install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== gdsfactory 8.18.0 离线安装 ==="
echo "wheel 目录: $SCRIPT_DIR"

# 1. 安装所有 wheel（--no-deps 避免联网解析）
pip install --no-deps --no-index --find-links="$SCRIPT_DIR" \
    gdsfactory==8.18.0 \
    kfactory==0.21.6 \
    2>&1 | tail -5

# 2. 安装依赖 wheel
pip install --no-deps --no-index --find-links="$SCRIPT_DIR" \
    toolz loguru pydantic-settings pydantic-extra-types qrcode rectpack \
    typer watchdog freetype-py mapbox_earcut trimesh attrs graphviz \
    scikit-image ipykernel types-PyYAML ruamel.yaml ruamel.yaml.string \
    rectangle-packer pure-eval shellingham annotated-doc python-dotenv \
    imageio lazy-loader tifffile tomli 2>&1 | tail -5

# 3. 验证
python -c "
import gdsfactory as gf
from importlib.metadata import version
v = version('gdsfactory')
print(f'gdsfactory 版本: {v}')
c = gf.components.straight(length=10, width=0.5)
print(f'直线波导验证: {c.name}, 端口数: {len(c.ports)}')
print('=== gdsfactory 安装验证通过 ===')
"

echo "完成!"
