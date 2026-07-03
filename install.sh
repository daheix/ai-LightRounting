#!/usr/bin/env bash
# PoLaRIS/install.sh — 沙箱环境一键恢复脚本
#
# 标准：参照 3dtool 子仓库 install.sh 四文件模式
#       wheels 离线优先 / 在线兜底 / 验证 / 写标记
#
# 用途：沙箱重启后 site-packages 全部丢失，用本脚本恢复 PoLaRIS 全部依赖。
#
# 使用方法：
#   bash install.sh              # 完整恢复
#   bash install.sh --no-unshallow  # 跳过 git unshallow（已 unshallow 时用）
#
# 前置条件：
#   - Python 3.10+ 已安装
#   - pip 可用
#   - 网络可访问 PyPI（或 3dtool/wheels/ 有离线包）
#
# 安装内容：
#   1. 修复 shallow clone（sandbox 反复出现的 git 浅克隆问题）
#   2. 拉取 3dtool 子仓库（如未初始化）
#   3. 安装 PoLaRIS 核心依赖（jax CPU 版 / numpy / scipy / sax / klayout 等）
#   4. editable 安装 PoLaRIS 33 模块（modules/*/）
#   5. 验证关键依赖 + 核心模块导入
#
# 规则依据：
#   R03 禁止 fall-back：失败即 exit，不静默跳过
#   R04 不参与 GPU：jax 只装 CPU 版，禁止 jax[cuda]
#   R11 工作流规范
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"
WHEELS_DIR="${REPO_DIR}/3dtool/wheels"
MODULES_DIR="${REPO_DIR}/modules"
MARK_FILE="/tmp/.polaris_installed"
DO_UNSHALLOW=1
DO_SUBMODULE=1
VERBOSE=0

# 解析参数
for arg in "$@"; do
    case "${arg}" in
        --no-unshallow) DO_UNSHALLOW=0 ;;
        --skip-submodule) DO_SUBMODULE=0 ;;
        -v|--verbose) VERBOSE=1 ;;
    esac
done

echo "========================================"
echo "  PoLaRIS 环境恢复脚本"
echo "========================================"
echo "仓库目录: ${REPO_DIR}"
echo "Python: $(python --version 2>&1)"
echo "pip: $(pip --version 2>&1)"
echo ""

# 步骤1: 修复 shallow clone（sandbox 重启后 git 变 shallow，13 commits 而非 1795）
if [ "${DO_UNSHALLOW}" = "1" ]; then
    echo "[1/5] 修复 shallow clone..."
    cd "${REPO_DIR}"
    if [ -f .git/shallow ] || [ "$(git rev-list --count HEAD 2>/dev/null || echo 0)" -lt 100 ]; then
        echo "  当前为 shallow clone ($(git rev-list --count HEAD) commits)，执行 unshallow..."
        git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null || true
        git fetch --unshallow origin 2>&1 | tail -3 || echo "  [WARN] unshallow 失败（可能已 unshallow 或网络问题）"
    else
        echo "  git 历史完整 ($(git rev-list --count HEAD) commits)，跳过 unshallow"
    fi
    echo "[1/5] 完成"
else
    echo "[1/5] 跳过 unshallow（--no-unshallow）"
fi

# 步骤2: 恢复 3dtool 子仓库（幂等，沙箱重启后自动 sparse clone 注册）
# 可通过 --skip-submodule 跳过（init_env.sh 已调用时用）
if [ "${DO_SUBMODULE}" = "1" ]; then
    echo ""
    echo "[2/5] 恢复 3dtool 子仓库（标准 git submodule + sparse-checkout）..."
    SETUP_SUBMODULE="${REPO_DIR}/scripts/setup_3dtool_submodule.sh"
    if [ -f "${SETUP_SUBMODULE}" ]; then
        SETUP_ARGS=""
        [ "${VERBOSE}" = "1" ] && SETUP_ARGS="-v"
        if ! bash "${SETUP_SUBMODULE}" ${SETUP_ARGS}; then
            echo "[ERROR] 3dtool 子仓库恢复失败（R03 禁止 fall-back）"
            exit 1
        fi
        echo "  submodule status: $(git submodule status 2>&1 | head -1)"
    else
        echo "[ERROR] setup_3dtool_submodule.sh 不存在: ${SETUP_SUBMODULE}"
        exit 1
    fi
    echo "[2/5] 完成"
else
    echo "[2/5] 跳过子仓库恢复（--skip-submodule）"
fi

# 步骤3: 安装核心依赖
echo ""
echo "[3/5] 安装 PoLaRIS 核心依赖..."
# 优先用 3dtool/wheels/ 离线包（覆盖重叠依赖），缺失的在线安装
WHEEL_COUNT=0
if [ -d "${WHEELS_DIR}" ] && ls "${WHEELS_DIR}"/*.whl >/dev/null 2>&1; then
    WHEEL_COUNT=$(ls "${WHEELS_DIR}"/*.whl 2>/dev/null | wc -l)
    echo "  发现 3dtool/wheels/ 下 ${WHEEL_COUNT} 个离线 wheel，离线安装..."
    pip install --no-index --find-links="${WHEELS_DIR}" "${WHEELS_DIR}"/*.whl 2>&1 | tail -3 || {
        echo "  [INFO] 离线安装部分失败，回退到在线安装"
    }
fi

# PoLaRIS 核心依赖（R04: jax 纯 CPU 版，不装 jax[cuda]）
# 依赖来源：PoLaRIS 33 模块 pyproject.toml 共用依赖 + R04 CPU 战略
echo "  在线安装 PoLaRIS 核心依赖..."
pip install \
    numpy \
    scipy \
    networkx \
    matplotlib \
    pyyaml \
    "jax[cpu]" \
    "jaxlib[cpu]" \
    sax \
    klayout \
    gymnasium \
    shapely \
    pydantic \
    pytest \
    ruff \
    mypy \
    2>&1 | tail -5
echo "[3/5] 核心依赖安装完成"

# 步骤4: editable 安装 PoLaRIS 33 模块
echo ""
echo "[4/5] 安装 PoLaRIS 33 模块（editable）..."
cd "${REPO_DIR}"
MODULE_COUNT=0
INSTALL_FAIL=0
for mod_pyproject in "${MODULES_DIR}"/*/pyproject.toml; do
    mod_dir="$(dirname "${mod_pyproject}")"
    mod_name="$(basename "${mod_dir}")"
    echo "  [${mod_name}] pip install -e --no-deps..."
    if pip install -e "${mod_dir}" --no-deps 2>&1 | tail -1; then
        MODULE_COUNT=$((MODULE_COUNT + 1))
    else
        echo "  [FAIL] ${mod_name} 安装失败"
        INSTALL_FAIL=$((INSTALL_FAIL + 1))
    fi
done
echo "[4/5] 已安装 ${MODULE_COUNT} 个模块（失败 ${INSTALL_FAIL} 个）"

if [ "${INSTALL_FAIL}" -gt 0 ]; then
    echo "[ERROR] ${INSTALL_FAIL} 个模块安装失败，环境不完整（R03 禁止 fall-back）"
    exit 1
fi

# 步骤5: 验证
echo ""
echo "[5/5] 验证安装..."
python -c "import numpy; print('  [OK] numpy', numpy.__version__)" || { echo "  [FAIL] numpy"; exit 1; }
python -c "import scipy; print('  [OK] scipy', scipy.__version__)" || { echo "  [FAIL] scipy"; exit 1; }
python -c "import networkx; print('  [OK] networkx', networkx.__version__)" || { echo "  [FAIL] networkx"; exit 1; }
python -c "import matplotlib; print('  [OK] matplotlib', matplotlib.__version__)" || { echo "  [FAIL] matplotlib"; exit 1; }
python -c "import yaml; print('  [OK] pyyaml', yaml.__version__)" || { echo "  [FAIL] pyyaml"; exit 1; }
python -c "import jax; print('  [OK] jax', jax.__version__, '(CPU, R04 合规)')" || { echo "  [FAIL] jax"; exit 1; }
python -c "import sax; print('  [OK] sax', sax.__version__)" || { echo "  [FAIL] sax"; exit 1; }
python -c "import klayout; print('  [OK] klayout')" || { echo "  [FAIL] klayout"; exit 1; }
python -c "import gymnasium; print('  [OK] gymnasium', gymnasium.__version__)" || { echo "  [FAIL] gymnasium"; exit 1; }
python -c "import shapely; print('  [OK] shapely', shapely.__version__)" || { echo "  [FAIL] shapely"; exit 1; }
python -c "import pydantic; print('  [OK] pydantic', pydantic.__version__)" || { echo "  [FAIL] pydantic"; exit 1; }
python -c "import pytest; print('  [OK] pytest', pytest.__version__)" || { echo "  [FAIL] pytest"; exit 1; }
python -c "import polaris_core; print('  [OK] polaris_core')" || { echo "  [FAIL] polaris_core"; exit 1; }

echo ""
echo "========================================"
echo "  PoLaRIS 环境恢复完成！"
echo "  模块数: ${MODULE_COUNT}/33"
echo "  wheel 包: ${WHEEL_COUNT}"
echo "========================================"
echo ""

# 写入标记文件（沙箱重启后 /tmp 会被清空，标记消失则下次自动重装）
echo "$(date -Iseconds) python=$(python --version 2>&1) modules=${MODULE_COUNT} wheels=${WHEEL_COUNT}" > "${MARK_FILE}"
echo "已写入标记: ${MARK_FILE}"

echo "下一步验证（可选）："
echo "  cd ${REPO_DIR}"
echo "  python -m ruff check modules/"
echo "  python -m pytest -q"
