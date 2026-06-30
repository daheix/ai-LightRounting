#!/usr/bin/env bash
# 3dtool/install.sh — 沙箱环境一键恢复脚本
#
# 用途：沙箱重启后，site-packages 全部丢失，用本脚本从 3dtool/wheels/ 离线安装所有依赖。
#
# 使用方法：
#   bash 3dtool/install.sh
#
# 前置条件：
#   - Python 3.14+ 已安装（pyenv 管理）
#   - pip 可用
#
# 安装内容：
#   1. 所有第三方依赖 wheel（3dtool/wheels/*.whl）
#   2. pcb-parser 项目本身（editable 模式，从 pyproject.toml）
#
# 验证：
#   - import pcb_parser
#   - python -m pytest -q
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WHEELS_DIR="${SCRIPT_DIR}/wheels"

echo "========================================"
echo "  3dtool 环境恢复脚本"
echo "========================================"
echo "仓库目录: ${REPO_DIR}"
echo "wheel 目录: ${WHEELS_DIR}"
echo "Python: $(python --version 2>&1)"
echo "pip: $(pip --version 2>&1)"
echo ""

# 步骤1: 检查 wheel 目录
if [ ! -d "${WHEELS_DIR}" ] || [ -z "$(ls -A "${WHEELS_DIR}"/*.whl 2>/dev/null)" ]; then
    echo "[ERROR] wheel 目录不存在或为空: ${WHEELS_DIR}"
    echo "        请确认 3dtool/wheels/ 下有 .whl 文件"
    exit 1
fi

WHEEL_COUNT=$(ls "${WHEELS_DIR}"/*.whl 2>/dev/null | wc -l)
echo "[1/4] 发现 ${WHEEL_COUNT} 个 wheel 包"

# 步骤2: 离线安装所有 wheel
# gerbonara 依赖 quart（仅其可选 Web GUI 用），项目不使用该功能且 quart 未打包，
# 故 gerbonara 用 --no-deps 安装；其余 wheel 正常解析依赖。
echo ""
echo "[2/4] 离线安装所有 wheel（--no-index --find-links）..."
GERBONARA_WHL="${WHEELS_DIR}/gerbonara-"*.whl
# 先装除 gerbonara 外的所有 wheel
declare -a ALL_OTHER_WHEELS=()
for w in "${WHEELS_DIR}"/*.whl; do
    case "$(basename "$w")" in
        gerbonara-*) continue ;;
    esac
    ALL_OTHER_WHEELS+=("$w")
done
if [ ${#ALL_OTHER_WHEELS[@]} -gt 0 ]; then
    pip install --no-index --find-links="${WHEELS_DIR}" "${ALL_OTHER_WHEELS[@]}" 2>&1 | tail -5
fi
# gerbonara 单独 --no-deps 安装（quart 未打包，项目不使用其 Web 功能）
# 用 ls 展开通配符，避免 glob 未匹配时传入字面量
GERBONARA_WHL_EXPANDED=$(ls "${WHEELS_DIR}"/gerbonara-*.whl 2>/dev/null | head -1)
if [ -n "${GERBONARA_WHL_EXPANDED}" ]; then
    pip install --no-index --no-deps "${GERBONARA_WHL_EXPANDED}" 2>&1 | tail -3
fi
echo "[2/4] wheel 安装完成"

# 步骤3: 安装 pcb-parser 项目本身（editable）
echo ""
echo "[3/4] 安装 pcb-parser 项目（editable 模式）..."
cd "${REPO_DIR}"
if [ -f pyproject.toml ] || [ -f setup.py ]; then
    pip install -e . --no-deps 2>&1 | tail -3
    echo "[3/4] pcb-parser 安装完成"
else
    echo "[3/4] [WARN] ${REPO_DIR} 无 pyproject.toml/setup.py, 跳过 pcb-parser 安装"
fi

# 步骤4: 验证
echo ""
echo "[4/4] 验证安装..."
python -c "import pcb_parser; print('  [OK] pcb_parser 导入成功')" 2>/dev/null || echo "  [SKIP] pcb_parser 未安装 (无 pyproject.toml)"
python -c "import lark; print('  [OK] lark', lark.__version__)" || { echo "  [FAIL] lark 导入失败"; exit 1; }
python -c "import pydantic; print('  [OK] pydantic', pydantic.__version__)" || { echo "  [FAIL] pydantic 导入失败"; exit 1; }
python -c "import shapely; print('  [OK] shapely', shapely.__version__)" || { echo "  [FAIL] shapely 导入失败"; exit 1; }
python -c "import scipy; print('  [OK] scipy', scipy.__version__)" || { echo "  [FAIL] scipy 导入失败"; exit 1; }
python -c "import rtree; print('  [OK] rtree', rtree.__version__)" || { echo "  [FAIL] rtree 导入失败"; exit 1; }
python -c "import openpyxl; print('  [OK] openpyxl', openpyxl.__version__)" || { echo "  [FAIL] openpyxl 导入失败"; exit 1; }
python -c "import reportlab; print('  [OK] reportlab', reportlab.Version)" || { echo "  [FAIL] reportlab 导入失败"; exit 1; }
python -c "import yaml; print('  [OK] pyyaml', yaml.__version__)" || { echo "  [FAIL] pyyaml 导入失败"; exit 1; }
python -c "import olefile; print('  [OK] olefile', olefile.__version__)" || { echo "  [FAIL] olefile 导入失败"; exit 1; }
python -c "import unlzw3; print('  [OK] unlzw3')" || { echo "  [FAIL] unlzw3 导入失败"; exit 1; }

echo ""
echo "========================================"
echo "  环境恢复完成！"
echo "========================================"
echo ""

# 写入标记文件（沙箱重启后 /tmp 会被清空，标记消失则下次自动重装）
MARK_FILE="/tmp/.3dtool_installed"
echo "$(date -Iseconds) python=$(python --version 2>&1) wheels=${WHEEL_COUNT}" > "${MARK_FILE}"
echo "已写入标记: ${MARK_FILE}"

echo "下一步验证（可选）："
echo "  cd ${REPO_DIR}"
echo "  python -m ruff check src tests"
echo "  python -m mypy src/pcb_parser"
echo "  python -m pytest -q"
