#!/usr/bin/env bash
# PoLaRIS/init.sh — 极薄入口（调用 3dtool 共用机制 + PoLaRIS 特有包 + 33 模块 + 守护进程）
#
# 架构原则（用户强制）:
#   - 3dtool 是所有项目共用的唯一环境源，禁止项目单独维护 env/install/ensure
#   - 一条命令完整安装，要么成功要么失败，无任何兜底（R03）
#   - 无网无 pyenv 也能跑（3dtool 自带便携 Python 3.14 + 离线 wheel）
#
# 安装步骤:
#   1. 调用 3dtool/install.sh（便携 Python 3.14 + 47 基础 wheel，通用自举）
#   2. source 3dtool/env.sh（环境变量 + JAX CPU R04）
#   3. 解压 polaris-extras.tar.gz（jax/sax/klayout/gymnasium + 依赖，PoLaRIS 特有）
#   4. 验证 PoLaRIS 特有包（jax CPU 强制 R04）
#   5. editable 安装 33 模块
#   6. 启动守护进程（auto_commit V8 + keepalive）
#
# 使用:
#   bash init.sh              # 完整初始化（唯一命令）
#   bash init.sh --no-daemon  # 不启动守护进程
#
# 规则依据: R03 禁止 fall-back / R04 不参与 GPU / R11 工作流
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THREEDTOOL_DIR="${WORKSPACE}/3dtool"
EXTRAS_PARTS="${WORKSPACE}/polaris-extras.tar.gz.part_"
MARK_FILE="/tmp/.polaris_installed"
NO_DAEMON=0

[ "${1:-}" = "--no-daemon" ] && NO_DAEMON=1

fail() { echo "[polaris][ERROR] $*" >&2; exit 1; }
log() { echo "[polaris] $*"; }

# ============================================================
# 步骤 1: 调用 3dtool 通用自举（便携 Python + 47 基础 wheel）
# ============================================================
log "[1/6] 调用 3dtool 通用自举..."
bash "${THREEDTOOL_DIR}/install.sh"

# ============================================================
# 步骤 2: source 3dtool/env.sh（环境变量 + JAX CPU）
# ============================================================
log "[2/6] 加载 3dtool 环境变量..."
# shellcheck disable=SC1091
source "${THREEDTOOL_DIR}/env.sh"
[ -n "${THREEDTOOL_PYTHON:-}" ] || fail "THREEDTOOL_PYTHON 未设置"
SITE_PKG="${THREEDTOOL_DIR}/python-runtime/lib/python3.14/site-packages"

# ============================================================
# 步骤 3: 解压 PoLaRIS 特有包（分片合并 → 解压）
#   polaris-extras.tar.gz 原始 137M > GitHub 100M 限制，
#   拆成 part_00/part_01 提交，运行时 cat 合并解压
# ============================================================
log "[3/6] 合并分片并解压 PoLaRIS 特有包..."
ls "${EXTRAS_PARTS}"* >/dev/null 2>&1 || fail "polaris-extras 分片不存在: ${EXTRAS_PARTS}*"
cat "${EXTRAS_PARTS}"* | tar xz -C "${SITE_PKG}"

# ============================================================
# 步骤 4: 验证 PoLaRIS 特有包（jax CPU 强制 R04）
# ============================================================
log "[4/6] 验证 PoLaRIS 特有包（R04 CPU 强制）..."
"${THREEDTOOL_PYTHON}" -c "
import jax
assert jax.default_backend() == 'cpu', f'JAX 后端不是 CPU: {jax.default_backend()}（R04 违规）'
import jaxlib, sax, klayout, gymnasium
import ml_dtypes, opt_einsum, optax, pandas, sympy, xarray
print('PoLaRIS 特有包 + 依赖: OK')
" || fail "PoLaRIS 特有包验证失败"

# ============================================================
# 步骤 5: editable 安装 33 模块
# ============================================================
log "[5/6] editable 安装 33 模块..."
MODULE_COUNT=0
FAILED_MODULES=()
for mod_dir in "${WORKSPACE}"/modules/*/; do
    mod_name=$(basename "${mod_dir}")
    [ "${mod_name}" = "_c_abi" ] && continue
    [ -f "${mod_dir}pyproject.toml" ] || continue
    if "${THREEDTOOL_PYTHON}" -m pip install -e "${mod_dir}" --no-deps -q 2>/dev/null; then
        MODULE_COUNT=$((MODULE_COUNT + 1))
    else
        FAILED_MODULES+=("${mod_name}")
    fi
done
[ "${MODULE_COUNT}" -ge 30 ] || fail "模块安装不足: ${MODULE_COUNT}/33（失败: ${FAILED_MODULES[*]:-无}）"
log "  模块: ${MODULE_COUNT}/33"

# ============================================================
# 步骤 6: 启动守护进程（R11 工作流）
# ============================================================
if [ "${NO_DAEMON}" = "0" ]; then
    log "[6/6] 启动守护进程..."
    # auto_commit V8（6 分钟自动提交）
    if ! pgrep -f "auto_commit.*V8" >/dev/null 2>&1; then
        [ -f "${WORKSPACE}/scripts/auto_commit.py" ] && \
            nohup "${THREEDTOOL_PYTHON}" "${WORKSPACE}/scripts/auto_commit.py" V8 >/dev/null 2>&1 &
    fi
    # keepalive（5 分钟 touch 防超时）
    if ! pgrep -f "keepalive" >/dev/null 2>&1; then
        [ -f "${WORKSPACE}/scripts/keepalive.sh" ] && \
            nohup bash "${WORKSPACE}/scripts/keepalive.sh" >/dev/null 2>&1 &
    fi
fi

# 写标记
echo "$(date -Iseconds) python=${THREEDTOOL_PYTHON} modules=${MODULE_COUNT}" > "${MARK_FILE}"

log ""
log "=========================================="
log "  PoLaRIS 环境初始化完成"
log "=========================================="
log "Python: ${THREEDTOOL_PYTHON}"
log "模块: ${MODULE_COUNT}/33"
log "JAX 后端: cpu（R04 合规）"
log "标记: ${MARK_FILE}"
log "=========================================="
