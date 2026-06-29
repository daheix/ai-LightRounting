#!/bin/bash
# ==============================================================================
# 3DTool 统一 AppImage (AppDir) 构建脚本
# ==============================================================================
# 构建一个自包含的 AppDir, 包含所有工具 (Python/C++/Fortran/Java/KiCad),
# 通过单一入口 AppRun <tool> [args] 调用, 不依赖任何外部环境配置。
#
# 产物:
#   /workspace/3dtool/3dtool-appimage/
#     ├── AppRun              # 统一入口: AppRun <tool> [args]
#     ├── bin/                # C/C++/Fortran 工具二进制
#     ├── lib/                # 全部共享 .so (合并去重 + soname 符号链接)
#     ├── python/             # Python 3.14 运行时 + 全部 pip 包
#     ├── share/kicad -> ...  # KiCad 资源 (符号链接)
#     ├── jre -> ...          # Java JRE (符号链接)
#     └── wheels -> ...       # wheels 目录 (符号链接, 供参考)
#
# 用法:
#   bash build_3dtool_appimage.sh
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# 路径定义
# ------------------------------------------------------------------------------
APPDIR="/workspace/3dtool/3dtool-appimage"
PYENV_ROOT="/root/.pyenv/versions/3.14.4"
PYENV_PY="${PYENV_ROOT}/bin/python3.14"
WHEELS_DIR="/workspace/3dtool/wheels"
SRC_3DTOOL="/workspace/3dtool"
KICAD_APPIMAGE="/workspace/3dtool/kicad-10.0.4-x86_64.AppImage"

APPDIR_PY="${APPDIR}/python/bin/python3.14"
SITE_PKGS="${APPDIR}/python/lib/python3.14/site-packages"

echo "============================================================"
echo " 3DTool 统一 AppImage 构建脚本"
echo "  APPDIR = ${APPDIR}"
echo "============================================================"

# ==============================================================================
# Step 1: 创建目录结构
# ==============================================================================
echo "[1/11] 创建目录结构..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}"/{bin,lib,python/lib,share}

# ==============================================================================
# Step 2: 复制 Python 运行时 (pyenv 3.14.4 -> AppDir/python)
# ==============================================================================
echo "[2/11] 复制 Python 3.14.4 运行时..."
cp -a "${PYENV_ROOT}/bin" "${APPDIR}/python/"
cp -a "${PYENV_ROOT}/lib/python3.14" "${APPDIR}/python/lib/"

# 复制 libpython3.14.so* 及 pyenv lib 中的 tbb/hwloc/tcm 到 AppDir/lib
# (python3.14 二进制的 RUNPATH 指向 pyenv lib; 用 LD_LIBRARY_PATH=AppDir/lib 覆盖,
#  使其自包含。libpython3.14.so.1.0 是 python 运行必需的)
echo "  复制 libpython3.14 / libtbb / libhwloc / libtcm (来自 pyenv lib)..."
for sofile in "${PYENV_ROOT}/lib"/lib*.so*; do
    [ -e "$sofile" ] || continue
    cp -an "$sofile" "${APPDIR}/lib/" 2>/dev/null || cp -a "$sofile" "${APPDIR}/lib/"
done

# 测试 python 是否可独立运行 (用 AppDir/lib 解析 libpython)
echo "  测试 Python 独立运行..."
if LD_LIBRARY_PATH="${APPDIR}/lib" PYTHONHOME="${APPDIR}/python" "${APPDIR_PY}" --version 2>&1; then
    echo "  ✓ Python 独立运行 OK"
else
    echo "  ✗ Python 独立运行失败, 尝试保留 pyenv RUNPATH (pyenv 仍存在时可工作)"
fi

# ==============================================================================
# Step 3: 安装全部 Python 包 (wheels + torch 分片 + 源码分发包)
# ==============================================================================
echo "[3/11] 安装 Python 包..."

# --- 3a. 解压 torch 分片 (cat 两个 part | tar xzf -) 得到 .whl ---
echo "  解压 torch 分片..."
TORCH_TMP="$(mktemp -d)"
cat "${WHEELS_DIR}/torch_cpu.tar.gz.part_a"* | tar xzf - -C "${TORCH_TMP}" 2>/dev/null || true
TORCH_WHL="$(ls "${TORCH_TMP}"/torch-*.whl 2>/dev/null | head -1 || true)"
if [ -n "${TORCH_WHL}" ]; then
    echo "  ✓ 解压得到 torch wheel: $(basename "${TORCH_WHL}")"
else
    echo "  ⚠ 未找到 torch wheel, 将尝试从 wheels 目录安装"
fi

# --- 3b. 安装全部 .whl (--no-deps: 所有依赖均以 wheel 形式存在, 避免触发
#       源码构建如 enable->chaco 需要 cython 离线不可得而整体失败) ---
echo "  安装全部 wheels (--no-deps, 依赖均以 wheel 存在)..."
INSTALL_LOG="$(mktemp)"
set +e
if [ -n "${TORCH_WHL}" ]; then
    LD_LIBRARY_PATH="${APPDIR}/lib" PYTHONHOME="${APPDIR}/python" \
      "${APPDIR_PY}" -m pip install --no-deps --no-index \
        --find-links "${WHEELS_DIR}" \
        --find-links "${TORCH_TMP}" \
        ${WHEELS_DIR}/*.whl "${TORCH_WHL}" >"${INSTALL_LOG}" 2>&1
else
    LD_LIBRARY_PATH="${APPDIR}/lib" PYTHONHOME="${APPDIR}/python" \
      "${APPDIR_PY}" -m pip install --no-deps --no-index \
        --find-links "${WHEELS_DIR}" \
        ${WHEELS_DIR}/*.whl >"${INSTALL_LOG}" 2>&1
fi
PIP_RC=$?
set -e
if [ ${PIP_RC} -eq 0 ]; then
    echo "  ✓ 全部 wheels 安装成功"
else
    echo "  ⚠ wheels 批量安装返回非零 (${PIP_RC}), 尾部日志:"
    tail -15 "${INSTALL_LOG}" | sed 's/^/    /'
fi
rm -f "${INSTALL_LOG}"

# --- 3c. 安装源码分发包 (逐个, 失败则记录但继续) ---
echo "  安装源码分发包..."
for sdist in PyIBIS-AMI-4.1.0.tar.gz empy-4.2.1.tar.gz enable-6.1.0.tar.gz \
             hierplace-1.1.0.tar.gz kinet2pcb-1.1.4.tar.gz parsec-3.17.tar.gz \
             skidl-2.2.3.tar.gz; do
    src="${WHEELS_DIR}/${sdist}"
    [ -f "$src" ] || continue
    echo "    -> ${sdist}"
    set +e
    SDIST_LOG="$(mktemp)"
    LD_LIBRARY_PATH="${APPDIR}/lib" PYTHONHOME="${APPDIR}/python" \
      "${APPDIR_PY}" -m pip install --no-deps --no-index --find-links "${WHEELS_DIR}" \
        "$src" >"${SDIST_LOG}" 2>&1
    SD_RC=$?
    set -e
    if [ ${SD_RC} -ne 0 ]; then
        echo "       ⚠ 安装失败 (rc=${SD_RC}, 离线缺构建依赖, 非关键):"
        tail -3 "${SDIST_LOG}" | sed 's/^/          /'
    fi
    rm -f "${SDIST_LOG}"
done

rm -rf "${TORCH_TMP}"

# 统计已安装包数
PKG_COUNT=$(ls "${SITE_PKGS}" 2>/dev/null | grep -c '\.dist-info' || true)
echo "  site-packages 中约 ${PKG_COUNT} 个 .dist-info"

# ==============================================================================
# Step 4: 复制 Python 扩展 CSXCAD / openEMS / pyNgspice (来自 pyToolInterface)
# ==============================================================================
echo "[4/11] 复制 Python 扩展 (CSXCAD/openEMS/pyNgspice)..."
PYTOOL="${SRC_3DTOOL}/pyToolInterface"
for pkg in CSXCAD openEMS pyNgspice; do
    if [ -d "${PYTOOL}/${pkg}" ]; then
        rm -rf "${SITE_PKGS}/${pkg}"
        cp -a "${PYTOOL}/${pkg}" "${SITE_PKGS}/${pkg}"
        echo "  ✓ ${pkg}"
    else
        echo "  ✗ ${pkg} 源目录缺失: ${PYTOOL}/${pkg}"
    fi
done

# ==============================================================================
# Step 5: 合并全部 .so 到 AppDir/lib (去重)
# ==============================================================================
echo "[5/11] 合并共享库 (.so)..."
merge_libs() {
    local srcdir="$1"
    local label="$2"
    local n=0
    for sofile in "${srcdir}"/lib*.so*; do
        [ -e "$sofile" ] || continue
        # cp -an: 归档 + 不覆盖 (去重); 若失败回退到 cp -a
        if cp -an "$sofile" "${APPDIR}/lib/" 2>/dev/null; then
            n=$((n + 1))
        else
            cp -a "$sofile" "${APPDIR}/lib/" 2>/dev/null && n=$((n + 1)) || true
        fi
    done
    echo "  ${label}: 处理 ${n} 个文件"
}
merge_libs "${SRC_3DTOOL}/lib" "3dtool/lib"
merge_libs "${SRC_3DTOOL}/openems/lib" "openems/lib"
merge_libs "${SRC_3DTOOL}/elmer/lib/elmersolver" "elmer/lib/elmersolver"

SO_COUNT=$(ls "${APPDIR}/lib"/lib*.so* 2>/dev/null | wc -l)
echo "  AppDir/lib 共 ${SO_COUNT} 个 .so 条目"

# ==============================================================================
# Step 6: 修复缺失的系统库
# ==============================================================================
echo "[6/11] 修复缺失系统库..."

# libtbb.so.12 / libhwloc.so.15 — 已在 Step 2 从 pyenv lib 复制, 确认存在
for lib in libtbb.so.12 libhwloc.so.15 libtbbmalloc.so.2; do
    if [ -e "${APPDIR}/lib/${lib}" ] || [ -L "${APPDIR}/lib/${lib}" ]; then
        echo "  ✓ ${lib} 已存在"
    else
        echo "  ⚠ ${lib} 仍缺失, 从 pyenv 补充"
        cp -an "${PYENV_ROOT}/lib/${lib}"* "${APPDIR}/lib/" 2>/dev/null || true
    fi
done

# libsz.so.2 / libaec.so.0 — 已在 3dtool/lib (Step 5 已复制), 确认
for lib in libsz.so.2 libaec.so.0; do
    if [ -e "${APPDIR}/lib/${lib}" ] || [ -L "${APPDIR}/lib/${lib}" ]; then
        echo "  ✓ ${lib} 已存在"
    else
        echo "  ⚠ ${lib} 缺失"
    fi
done

# libdouble-conversion.so.3 — 系统无此库, 需下载 .deb 提取
DC_LIB="${APPDIR}/lib/libdouble-conversion.so.3"
if [ -e "${DC_LIB}" ] || [ -L "${DC_LIB}" ]; then
    echo "  ✓ libdouble-conversion.so.3 已存在"
else
    echo "  libdouble-conversion.so.3 缺失, 尝试从文件系统查找..."
    DC_FOUND="$(find / -name "libdouble-conversion.so.3*" -not -path "/proc/*" -not -path "${APPDIR}/*" 2>/dev/null | head -1 || true)"
    if [ -n "${DC_FOUND}" ]; then
        cp -a "$(dirname "${DC_FOUND}")"/libdouble-conversion.so.3* "${APPDIR}/lib/" 2>/dev/null || true
        echo "  ✓ 从 ${DC_FOUND} 复制"
    else
        echo "  文件系统未找到, 从 Ubuntu 镜像下载 .deb..."
        DC_TMP="$(mktemp -d)"
        DC_DEB="${DC_TMP}/libdc3.deb"
        DC_URL="http://archive.ubuntu.com/ubuntu/pool/universe/d/double-conversion/libdouble-conversion3_3.3.0-1build1_amd64.deb"
        if curl -sfL -o "${DC_DEB}" "${DC_URL}" && [ -s "${DC_DEB}" ]; then
            if dpkg-deb -x "${DC_DEB}" "${DC_TMP}/extract" 2>/dev/null; then
                DC_REAL="$(find "${DC_TMP}/extract" -name "libdouble-conversion.so.3.*" -type f 2>/dev/null | head -1 || true)"
                if [ -n "${DC_REAL}" ]; then
                    cp -a "${DC_REAL}" "${APPDIR}/lib/"
                    DC_BASE="$(basename "${DC_REAL}")"
                    ln -sf "${DC_BASE}" "${APPDIR}/lib/libdouble-conversion.so.3"
                    echo "  ✓ 从 .deb 提取并安装 libdouble-conversion (${DC_BASE})"
                else
                    echo "  ✗ .deb 中未找到 .so"
                fi
            else
                echo "  ✗ dpkg-deb 解压失败"
            fi
        else
            echo "  ✗ 下载失败 (${DC_URL})"
        fi
        rm -rf "${DC_TMP}"
    fi
fi

# --- OpenMPI 运行时 + libevent (ElmerSolver_mpi 依赖) ---
# ElmerSolver -> ElmerSolver_mpi, 其依赖 libelmersolver.so -> libmpi_mpifh.so.40 /
# libopen-rte.so.40 / libopen-pal.so.40 (OpenMPI), 而 libopen-pal 又依赖
# libevent_core-2.1.so.7 / libevent_pthreads-2.1.so.7。系统未安装, 从 Ubuntu 镜像下载 .deb 提取。
fetch_deb_and_extract() {
    local url="$1" label="$2"
    local tmpd; tmpd="$(mktemp -d)"
    local deb="${tmpd}/pkg.deb"
    if curl -sfL -o "$deb" "$url" 2>/dev/null && [ -s "$deb" ]; then
        if dpkg-deb -x "$deb" "${tmpd}/extract" 2>/dev/null; then
            local n=0
            while IFS= read -r so; do
                cp -an "$so" "${APPDIR}/lib/" 2>/dev/null && n=$((n + 1)) || true
            done < <(find "${tmpd}/extract" -name "lib*.so*" 2>/dev/null)
            echo "  ✓ ${label}: 提取 ${n} 个 .so"
        else
            echo "  ⚠ ${label}: dpkg-deb 解压失败"
        fi
    else
        echo "  ⚠ ${label}: 下载失败 (${url})"
    fi
    rm -rf "$tmpd"
}

NEED_MPI=0
for lib in libmpi_mpifh.so.40 libopen-rte.so.40 libopen-pal.so.40 \
           libevent_core-2.1.so.7 libevent_pthreads-2.1.so.7; do
    if [ ! -e "${APPDIR}/lib/${lib}" ] && [ ! -L "${APPDIR}/lib/${lib}" ]; then
        NEED_MPI=1; break
    fi
done
if [ "${NEED_MPI}" = "1" ]; then
    echo "  ElmerSolver_mpi 依赖缺失, 下载 OpenMPI + libevent..."
    fetch_deb_and_extract "http://archive.ubuntu.com/ubuntu/pool/universe/o/openmpi/libopenmpi3t64_4.1.6-7ubuntu2_amd64.deb" "libopenmpi3t64"
    fetch_deb_and_extract "http://archive.ubuntu.com/ubuntu/pool/main/libe/libevent/libevent-core-2.1-7t64_2.1.12-stable-9ubuntu2_amd64.deb" "libevent-core"
    fetch_deb_and_extract "http://archive.ubuntu.com/ubuntu/pool/main/libe/libevent/libevent-pthreads-2.1-7t64_2.1.12-stable-9ubuntu2_amd64.deb" "libevent-pthreads"
fi

# ==============================================================================
# Step 7: 为所有 .so 创建 soname 符号链接
# ==============================================================================
echo "[7/11] 创建 soname 符号链接..."
SYMLINK_COUNT=0
for sofile in "${APPDIR}/lib"/lib*.so.*; do
    [ -f "$sofile" ] || continue
    [ -L "$sofile" ] && continue   # 跳过已是符号链接的
    soname=$(readelf -d "$sofile" 2>/dev/null | grep 'SONAME' | sed 's/.*\[\(.*\)\].*/\1/' || true)
    if [ -n "$soname" ]; then
        base=$(basename "$sofile")
        if [ "$soname" != "$base" ]; then
            ln -sf "$base" "${APPDIR}/lib/${soname}"
            SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
        fi
    fi
done
# 额外: VTK 9.1 库 soname 为 libXXX-9.1.so.1, 手动补全
for sofile in "${APPDIR}/lib"/libvtk*-9.1.so.9.1.0; do
    [ -f "$sofile" ] || continue
    base=$(basename "$sofile")
    soname="${base%.9.1.0}.1"
    if [ ! -e "${APPDIR}/lib/${soname}" ]; then
        ln -sf "$base" "${APPDIR}/lib/${soname}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done
echo "  创建/补全 ${SYMLINK_COUNT} 个 soname 符号链接"

# ==============================================================================
# Step 8: 复制 C/C++/Fortran 工具二进制
# ==============================================================================
echo "[8/11] 复制工具二进制..."
cp -a "${SRC_3DTOOL}/bin/ngspice"             "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ ngspice"       || echo "  ✗ ngspice"
cp -a "${SRC_3DTOOL}/openems/bin/openEMS"     "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ openEMS"       || echo "  ✗ openEMS"
cp -a "${SRC_3DTOOL}/openems/bin/nf2ff"       "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ nf2ff"         || echo "  ✗ nf2ff"
cp -a "${SRC_3DTOOL}/openems/bin/sar_calc"    "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ sar_calc"      || echo "  ✗ sar_calc"
cp -a "${SRC_3DTOOL}/elmer/bin/ElmerSolver"   "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ ElmerSolver"   || echo "  ✗ ElmerSolver"
cp -a "${SRC_3DTOOL}/elmer/bin/ElmerGrid"     "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ ElmerGrid"     || echo "  ✗ ElmerGrid"
# ElmerSolver 是指向 ElmerSolver_mpi 的符号链接, 需一并复制真实二进制
if [ -e "${SRC_3DTOOL}/elmer/bin/ElmerSolver_mpi" ]; then
    cp -a "${SRC_3DTOOL}/elmer/bin/ElmerSolver_mpi" "${APPDIR}/bin/" 2>/dev/null && echo "  ✓ ElmerSolver_mpi" || echo "  ✗ ElmerSolver_mpi"
fi
chmod +x "${APPDIR}/bin/"* 2>/dev/null || true

# ==============================================================================
# Step 9: 创建 share / jre / wheels 符号链接
# ==============================================================================
echo "[9/11] 创建符号链接 (share/jre/wheels)..."
ln -sf "${SRC_3DTOOL}/share/kicad" "${APPDIR}/share/kicad"
ln -sf "/root/.local/share/mise/installs/java/25.0.2" "${APPDIR}/jre"
ln -sf "${WHEELS_DIR}" "${APPDIR}/wheels"
echo "  ✓ share/kicad -> ${SRC_3DTOOL}/share/kicad"
echo "  ✓ jre -> /root/.local/share/mise/installs/java/25.0.2"
echo "  ✓ wheels -> ${WHEELS_DIR}"

# ==============================================================================
# Step 10: 写 AppRun 入口脚本
# ==============================================================================
echo "[10/11] 写 AppRun 入口脚本..."
cat > "${APPDIR}/AppRun" << 'APPRUN_EOF'
#!/bin/bash
# ==============================================================================
# 3DTool 统一 AppImage 入口脚本 (AppRun)
# ==============================================================================
# 自包含环境: 所有 .so / Python / 工具均在 APPDIR 内。
# 用法:
#   AppRun <tool> [args...]
# 工具:
#   ngspice openEMS nf2ff sar_calc ElmerSolver ElmerGrid  # 原生二进制
#   kicad kicad-cli                                        # 转发到 KiCad AppImage
#   python java                                            # 运行时
#   check                                                  # 环境自检
# ==============================================================================
set -euo pipefail

APPDIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export APPDIR

# 环境变量: 让所有依赖在 APPDIR 内解析
export LD_LIBRARY_PATH="${APPDIR}/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${APPDIR}/python/lib/python3.14/site-packages:${PYTHONPATH:-}"
export PYTHONHOME="${APPDIR}/python"
export PATH="${APPDIR}/bin:${APPDIR}/jre/bin:${PATH:-}"
export KICAD_SYMBOL_DIR="${APPDIR}/share/kicad/symbols"
export KICAD_FOOTPRINT_DIR="${APPDIR}/share/kicad/footprints"
export KICAD_DATA_DIR="${APPDIR}/share/kicad"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export ETS_TOOLKIT="${ETS_TOOLKIT:-null}"

APP_PYTHON="${APPDIR}/python/bin/python3.14"
KICAD_APPIMAGE="/workspace/3dtool/kicad-10.0.4-x86_64.AppImage"

cmd="${1:-check}"
case "$cmd" in
    check)
        echo "[AppRun] APPDIR=${APPDIR}"
        echo "[AppRun] Python=$(${APP_PYTHON} --version 2>&1)"
        # 检查每个工具二进制
        for t in ngspice openEMS nf2ff sar_calc ElmerSolver ElmerGrid; do
            [ -x "${APPDIR}/bin/${t}" ] && echo "  ✓ ${t}" || echo "  ✗ ${t} MISSING"
        done
        # 检查 Python 导入
        ${APP_PYTHON} -c "import numpy, scipy; print('  ✓ numpy/scipy')" 2>/dev/null || echo "  ✗ numpy/scipy import failed"
        ${APP_PYTHON} -c "import CSXCAD; from openEMS import openEMS; print('  ✓ CSXCAD/openEMS')" 2>/dev/null || echo "  ✗ CSXCAD/openEMS import failed"
        ${APP_PYTHON} -c "import torch; print('  ✓ torch', torch.__version__)" 2>/dev/null || echo "  ✗ torch import failed"
        ${APP_PYTHON} -c "import stable_baselines3; print('  ✓ stable_baselines3')" 2>/dev/null || echo "  ✗ stable_baselines3 import failed"
        ${APP_PYTHON} -c "import pyNgspice; print('  ✓ pyNgspice')" 2>/dev/null || echo "  ✗ pyNgspice import failed"
        # 检查 ldd
        echo "[AppRun] ldd checks:"
        for t in openEMS ElmerSolver ngspice; do
            missing=$(ldd "${APPDIR}/bin/${t}" 2>&1 | grep "not found" || true)
            [ -z "$missing" ] && echo "  ✓ ${t} deps OK" || echo "  ✗ ${t}: ${missing}"
        done
        echo "[AppRun] check done"
        ;;
    ngspice|openEMS|nf2ff|sar_calc|ElmerSolver|ElmerGrid)
        shift; exec "${APPDIR}/bin/${cmd}" "$@"
        ;;
    kicad|kicad-cli)
        shift; exec "$KICAD_APPIMAGE" "$cmd" "$@"
        ;;
    python|python3)
        shift; exec "$APP_PYTHON" "$@"
        ;;
    java)
        shift; exec "${APPDIR}/jre/bin/java" "$@"
        ;;
    *)
        echo "Usage: AppRun <tool> [args]" >&2
        echo "Tools: ngspice openEMS nf2ff sar_calc ElmerSolver ElmerGrid kicad kicad-cli python java check" >&2
        exit 1
        ;;
esac
APPRUN_EOF
chmod +x "${APPDIR}/AppRun"

# ==============================================================================
# Step 11: 验证
# ==============================================================================
echo "[11/11] 验证 (AppRun check)..."
echo "============================================================"
"${APPDIR}/AppRun" check
echo "============================================================"
echo " 构建完成: ${APPDIR}"
echo " 入口:     ${APPDIR}/AppRun <tool> [args]"
echo "============================================================"
