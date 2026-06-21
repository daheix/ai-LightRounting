#!/usr/bin/env bash
# PoLaRIS 离线依赖一键安装脚本
#
# 用途：在沙箱/新环境中快速恢复全部第三方依赖，无需联网下载。
#       沙箱重启后只需执行本脚本，秒级完成安装。
#
# 原理：
#   1. 小 wheel（<24MB）直接存放在 3dtool/wheels/
#   2. 大 wheel（>24MB）经 gzip 压缩 + split 分卷存放在 3dtool/wheels/parts/
#   3. 安装时先合并分卷 → gunzip 还原 → pip install --no-index 离线安装
#
# 用法：
#   bash 3dtool/wheels/install.sh           # 安装全部依赖（默认）
#   bash 3dtool/wheels/install.sh --core    # 仅安装核心依赖
#   bash 3dtool/wheels/install.sh --check   # 仅检查环境，不安装
#
# 来源：
# - pip 离线安装: https://pip.pypa.io/en/stable/topics/repeatable-installs/
# - split 分卷: https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="${SCRIPT_DIR}"
PARTS_DIR="${SCRIPT_DIR}/parts"
TMP_DIR="${SCRIPT_DIR}/.tmp_restore"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $*"; }

# 全部依赖清单（统一安装，无核心/可选之分）
# 含 sax 完整依赖链：jax + jaxlib + optax + pydantic + pandas + xarray
ALL_PACKAGES=(
    numpy scipy networkx torch gymnasium matplotlib pyyaml
    klayout simphony sax
    pytest ruff mypy
)

# 核心依赖子集（--core 模式使用）
CORE_PACKAGES=(
    numpy scipy networkx torch gymnasium matplotlib pyyaml
)

# 开发依赖子集（--dev 模式使用）
DEV_PACKAGES=(
    pytest ruff mypy
)

# 解析命令行参数
MODE="all"
case "${1:-}" in
    --core)  MODE="core" ;;
    --check) MODE="check" ;;
    --dev)   MODE="dev" ;;
    --all|"") MODE="all" ;;
    *)
        echo "用法: bash $0 [--core|--all|--dev|--check]"
        echo "  --core   仅安装核心依赖（numpy/scipy/torch 等）"
        echo "  --all    安装全部依赖（默认）"
        echo "  --dev    仅安装开发依赖（pytest/ruff/mypy）"
        echo "  --check  仅检查环境，不安装"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "  PoLaRIS 离线依赖安装脚本"
echo "  模式: ${MODE}"
echo "  Wheel 目录: ${WHEELS_DIR}"
echo "============================================================"
echo ""

# 步骤 1：检查目录与文件
log_step "步骤 1: 检查 wheel 目录"
if [[ ! -d "${WHEELS_DIR}" ]]; then
    log_error "wheel 目录不存在: ${WHEELS_DIR}"
    exit 1
fi

WHEEL_COUNT=$(find "${WHEELS_DIR}" -maxdepth 1 -name "*.whl" | wc -l)
PART_COUNT=$(find "${PARTS_DIR}" -name "*.part_*" 2>/dev/null | wc -l)
log_info "发现 ${WHEEL_COUNT} 个 wheel 文件 + ${PART_COUNT} 个分卷片段"

if [[ ${WHEEL_COUNT} -eq 0 && ${PART_COUNT} -eq 0 ]]; then
    log_error "未发现任何 wheel 文件，请确认在项目根目录执行"
    exit 1
fi

# 步骤 2：还原分卷压缩的大 wheel
log_step "步骤 2: 还原分卷压缩的大 wheel"
if [[ ${PART_COUNT} -gt 0 ]]; then
    mkdir -p "${TMP_DIR}"
    # 按基础文件名分组还原
    for part_prefix in $(ls "${PARTS_DIR}"/*.part_aa 2>/dev/null | sed 's/\.part_aa$//' | sort -u); do
        base_name=$(basename "${part_prefix}")
        # 去掉 .gz 后缀得到原始 wheel 名
        wheel_name="${base_name%.gz}"
        output_file="${TMP_DIR}/${wheel_name}"

        log_info "还原: ${wheel_name}"
        cat "${part_prefix}".part_* | gunzip > "${output_file}"

        if [[ ! -s "${output_file}" ]]; then
            log_error "还原失败: ${wheel_name}"
            exit 1
        fi
        log_info "  → $(du -h "${output_file}" | cut -f1)"
    done
    log_info "分卷还原完成，临时 wheel 存放于 ${TMP_DIR}"
else
    log_info "无分卷片段，跳过还原"
fi

# 步骤 3：检查 Python 环境
log_step "步骤 3: 检查 Python 环境"
if ! command -v python3 &>/dev/null; then
    log_error "未找到 python3，请先安装 Python 3.9+"
    exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log_info "Python 版本: ${PY_VERSION}"

if ! python3 -c "import pip" &>/dev/null; then
    log_error "pip 未安装，请先安装 pip"
    exit 1
fi
log_info "pip 可用: $(python3 -m pip --version)"

# 步骤 4：构建 find-links 路径
FIND_LINKS="${WHEELS_DIR}"
if [[ -d "${TMP_DIR}" ]]; then
    FIND_LINKS="${WHEELS_DIR} ${TMP_DIR}"
fi

# 步骤 5：仅检查模式
if [[ "${MODE}" == "check" ]]; then
    log_step "步骤 5: 环境检查（仅检查，不安装）"
    echo ""
    echo "--- 全部依赖检查 ---"
    for pkg in "${ALL_PACKAGES[@]}"; do
        # pyyaml 的 import 名是 yaml
        import_name="${pkg}"
        [[ "${pkg}" == "pyyaml" ]] && import_name="yaml"
        if python3 -c "import ${import_name}" 2>/dev/null; then
            # 优先用 pip show 获取版本（避免 __version__ 上游 bug，如 simphony 0.7.3 报 0.6.0）
            ver=$(python3 -m pip show "${pkg}" 2>/dev/null | grep '^Version:' | cut -d' ' -f2 || echo "?")
            [[ -z "${ver}" ]] && ver=$(python3 -c "import ${import_name}; print(${import_name}.__version__)" 2>/dev/null || echo "?")
            echo "  ✅ ${pkg} ${ver}"
        else
            echo "  ❌ ${pkg} 未安装"
        fi
    done
    echo ""
    log_info "检查完成。如需安装，执行: bash $0 --all"
    exit 0
fi

# 步骤 6：离线安装
log_step "步骤 6: 离线安装依赖（模式: ${MODE}）"

INSTALL_ARGS="--no-index --find-links ${WHEELS_DIR}"
if [[ -d "${TMP_DIR}" ]]; then
    INSTALL_ARGS="--no-index --find-links ${WHEELS_DIR} --find-links ${TMP_DIR}"
fi

case "${MODE}" in
    core)
        log_info "安装核心依赖: ${CORE_PACKAGES[*]}"
        python3 -m pip install ${INSTALL_ARGS} "${CORE_PACKAGES[@]}"
        ;;
    dev)
        log_info "安装开发依赖: ${DEV_PACKAGES[*]}"
        python3 -m pip install ${INSTALL_ARGS} "${DEV_PACKAGES[@]}"
        ;;
    all)
        log_info "安装全部依赖（含传递依赖）"
        # 方案 1：先尝试正常安装（自动解析依赖）
        if ! python3 -m pip install ${INSTALL_ARGS} "${ALL_PACKAGES[@]}" 2>/dev/null; then
            log_warn "正常安装失败（可能因依赖版本冲突），改用 --no-deps 分步安装"
            # 方案 2：用 --no-deps 安装主包，再安装所有 wheel 中的传递依赖
            python3 -m pip install ${INSTALL_ARGS} --no-deps "${ALL_PACKAGES[@]}"
            # 安装所有 wheel 文件（覆盖传递依赖，--no-deps 避免版本冲突）
            log_info "安装传递依赖（wheel 目录全部 wheel）"
            ALL_WHEELS=$(find "${WHEELS_DIR}" -maxdepth 1 -name "*.whl" | sort)
            if [[ -d "${TMP_DIR}" ]]; then
                ALL_WHEELS="${ALL_WHEELS} $(find "${TMP_DIR}" -maxdepth 1 -name "*.whl" | sort)"
            fi
            # 过滤掉已安装的主包 wheel，只装传递依赖
            for whl in ${ALL_WHEELS}; do
                pkg_name=$(basename "${whl}" | sed 's/-[0-9].*//')
                # 跳过主包（已用 --no-deps 安装）
                case "${pkg_name}" in
                    numpy|scipy|networkx|torch|gymnasium|matplotlib|pyyaml|klayout|simphony|sax|pytest|ruff|mypy)
                        continue ;;
                esac
                python3 -m pip install ${INSTALL_ARGS} --no-deps "${whl}" 2>/dev/null || true
            done
        fi
        ;;
esac

# 步骤 7：安装本项目（开发模式）
log_step "步骤 7: 安装 PoLaRIS 项目（开发模式）"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 先安装构建工具（wheel + setuptools），离线安装项目需要
log_info "安装构建工具: wheel setuptools"
python3 -m pip install ${INSTALL_ARGS} wheel setuptools 2>/dev/null || \
    python3 -m pip install wheel setuptools 2>/dev/null || \
    log_warn "构建工具安装失败，尝试直接安装项目"

if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
    cd "${PROJECT_ROOT}"
    # --no-build-isolation 避免隔离环境找不到 wheel
    python3 -m pip install --no-build-isolation --no-deps -e .
    log_info "PoLaRIS 已安装（开发模式）"
else
    log_warn "未找到 pyproject.toml，跳过项目安装"
fi

# 步骤 8：清理临时文件
log_step "步骤 8: 清理临时还原文件"
if [[ -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
    log_info "已清理 ${TMP_DIR}"
fi

# 步骤 9：验证安装
log_step "步骤 9: 验证安装"
echo ""
echo "--- 全部依赖验证 ---"
for pkg in "${ALL_PACKAGES[@]}"; do
    import_name="${pkg}"
    [[ "${pkg}" == "pyyaml" ]] && import_name="yaml"
    if python3 -c "import ${import_name}" 2>/dev/null; then
        # 优先用 pip show 获取版本（避免 __version__ 上游 bug）
        ver=$(python3 -m pip show "${pkg}" 2>/dev/null | grep '^Version:' | cut -d' ' -f2 || echo "?")
        [[ -z "${ver}" ]] && ver=$(python3 -c "import ${import_name}; print(${import_name}.__version__)" 2>/dev/null || echo "?")
        echo "  ✅ ${pkg} ${ver}"
    else
        echo "  ❌ ${pkg} 安装失败"
    fi
done

echo ""
echo "--- 复刻品验证 ---"
if python3 -c "from pycopy.pyCopySiPANN import waveguide_s" 2>/dev/null; then
    echo "  ✅ pyCopySiPANN"
else
    echo "  ❌ pyCopySiPANN 验证失败"
fi

echo ""
if python3 -c "import polaris" 2>/dev/null; then
    echo "  ✅ polaris"
else
    echo "  ❌ polaris 未安装"
fi

echo ""
echo "============================================================"
log_info "安装完成！沙箱重启后只需执行: bash 3dtool/wheels/install.sh"
echo "============================================================"
echo ""
