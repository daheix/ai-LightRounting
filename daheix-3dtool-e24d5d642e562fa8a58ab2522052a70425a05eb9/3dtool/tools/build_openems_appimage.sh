#!/bin/bash
# ==============================================================================
# OpenEMS AppImage 构建脚本
# ==============================================================================
# 将 OpenEMS + CSXCAD + 所有依赖 .so + Python 扩展 打包成一个自包含的
# AppImage 模式目录, 避免任何环境兼容性问题。
#
# 用法:
#   bash build_openems_appimage.sh
#
# 产物:
#   /workspace/3dtool/openems-appimage/
#     ├── AppRun              # 入口脚本 (设置 LD_LIBRARY_PATH / PYTHONPATH)
#     ├── bin/                # openEMS, nf2ff, sar_calc, openems_sim_worker.py
#     ├── lib/                # 所有 .so (openEMS 原生 + 全部依赖)
#     ├── python/             # CSXCAD/ + openEMS/ Python 包 (含 .so 扩展)
#     └── share/              # openEMS 共享数据
#
# 规则: project-rules.md — 工具环境不兼容时采用 AppImage 模式打包
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# 路径定义
# ------------------------------------------------------------------------------
SRC_OPENEMS="/workspace/3dtool/openems"           # openEMS 原生安装
SRC_3DTOOL_LIB="/workspace/3dtool/lib"            # 全部依赖 .so
SRC_TARBALL="/workspace/3dtool/tools_src/openEMS-Project.tar.gz"  # 含 Python 扩展
WORKER_SRC="/workspace/aidesigin/stage10_em_simulation/openems_sim_worker.py"

APPDIR="/workspace/3dtool/openems-appimage"       # AppImage 目录 (AppDir)

echo "============================================================"
echo " OpenEMS AppImage 构建脚本"
echo "  APPDIR = ${APPDIR}"
echo "============================================================"

# ------------------------------------------------------------------------------
# 0. 清理 & 创建目录结构
# ------------------------------------------------------------------------------
echo "[0/7] 创建目录结构..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}"/{bin,lib,share}
mkdir -p "${APPDIR}/python/CSXCAD"
mkdir -p "${APPDIR}/python/openEMS"

# ------------------------------------------------------------------------------
# 1. 复制 openEMS 原生二进制
# ------------------------------------------------------------------------------
echo "[1/7] 复制 openEMS 二进制..."
cp -a "${SRC_OPENEMS}/bin/openEMS"  "${APPDIR}/bin/"
cp -a "${SRC_OPENEMS}/bin/nf2ff"    "${APPDIR}/bin/"
cp -a "${SRC_OPENEMS}/bin/sar_calc" "${APPDIR}/bin/"
chmod +x "${APPDIR}/bin/"*

# ------------------------------------------------------------------------------
# 2. 复制 openEMS 原生 .so + 创建 soname 符号链接
# ------------------------------------------------------------------------------
echo "[2/7] 复制 openEMS 原生库..."
for sofile in "${SRC_OPENEMS}/lib"/lib*.so.*; do
    [ -f "$sofile" ] || continue
    cp -a "$sofile" "${APPDIR}/lib/"
done

# ------------------------------------------------------------------------------
# 3. 复制全部依赖 .so (vtk/hdf5/boost/tinyxml 等) + 创建 soname 符号链接
# ------------------------------------------------------------------------------
echo "[3/7] 复制依赖库 (vtk/hdf5/boost/...)..."
copied_deps=0
for sofile in "${SRC_3DTOOL_LIB}"/lib*.so.*; do
    [ -f "$sofile" ] || continue
    cp -a "$sofile" "${APPDIR}/lib/"
    copied_deps=$((copied_deps + 1))
done
echo "  复制了 ${copied_deps} 个依赖库"

# 为所有 .so 文件创建 soname 符号链接
# (readelf -d 读取 SONAME 字段, 创建 SONAME -> 实际文件 的符号链接)
echo "  创建 soname 符号链接..."
symlink_count=0
for sofile in "${APPDIR}/lib"/lib*.so.*; do
    [ -f "$sofile" ] || continue
    soname=$(readelf -d "$sofile" 2>/dev/null | grep 'SONAME' | sed 's/.*\[\(.*\)\].*/\1/' || true)
    if [ -n "$soname" ]; then
        basename=$(basename "$sofile")
        if [ "$soname" != "$basename" ]; then
            ln -sf "$basename" "${APPDIR}/lib/${soname}"
            symlink_count=$((symlink_count + 1))
        fi
    fi
done
echo "  创建了 ${symlink_count} 个 soname 符号链接"

# 额外: 为 VTK 库创建 .so.1 符号链接 (VTK 9.1 soname 格式: libXXX-9.1.so.1)
# readelf 可能未捕获所有情况, 手动补全
for sofile in "${APPDIR}/lib"/libvtk*-9.1.so.9.1.0; do
    [ -f "$sofile" ] || continue
    basename=$(basename "$sofile")
    soname="${basename%.9.1.0}.1"
    if [ ! -e "${APPDIR}/lib/${soname}" ]; then
        ln -sf "$basename" "${APPDIR}/lib/${soname}"
    fi
done

# 额外: 复制系统依赖库 (VTK 依赖 libtbb/libdouble-conversion/libhwloc, 不在 3dtool/lib 中)
echo "  复制系统依赖库 (libtbb/libdouble-conversion/libhwloc)..."
SYS_LIB_DIR="/usr/lib/x86_64-linux-gnu"
SYS_LIBS=(
    libtbb.so.12 libtbb.so.12.11
    libtbbmalloc.so.2 libtbbmalloc.so.2.11
    libtbbbind_2_5.so.3 libtbbbind_2_5.so.3.11
    libdouble-conversion.so.3 libdouble-conversion.so.3.1
    libhwloc.so.15 libhwloc.so.15.7.0
)
for libname in "${SYS_LIBS[@]}"; do
    src="${SYS_LIB_DIR}/${libname}"
    if [ -e "$src" ]; then
        cp -a "$src" "${APPDIR}/lib/"
    fi
done

# ------------------------------------------------------------------------------
# 4. 从 tarball 提取 Python 扩展 (CSXCAD + openEMS .so 文件)
# ------------------------------------------------------------------------------
echo "[4/7] 提取 Python 扩展 (CSXCAD + openEMS)..."
TMP_EXTRACT=$(mktemp -d)
tar -xzf "${SRC_TARBALL}" -C "${TMP_EXTRACT}" openEMS-Project/CSXCAD/python/ openEMS-Project/openEMS/python/

# CSXCAD: .py 源文件
for pyfile in __init__.py SmoothMeshLines.py __fallback_version__.py; do
    src="${TMP_EXTRACT}/openEMS-Project/CSXCAD/python/CSXCAD/${pyfile}"
    [ -f "$src" ] && cp -a "$src" "${APPDIR}/python/CSXCAD/"
done

# CSXCAD: .so 扩展 (cpython-314)
for sofile in "${TMP_EXTRACT}/openEMS-Project/CSXCAD/python/build/lib.linux-x86_64-cpython-314/CSXCAD/"*.so; do
    [ -f "$sofile" ] || continue
    cp -a "$sofile" "${APPDIR}/python/CSXCAD/"
done

# openEMS: .py 源文件
for pyfile in __init__.py physical_constants.py ports.py nf2ff.py utilities.py automesh.py sar_utils.py __fallback_version__.py; do
    src="${TMP_EXTRACT}/openEMS-Project/openEMS/python/openEMS/${pyfile}"
    [ -f "$src" ] && cp -a "$src" "${APPDIR}/python/openEMS/"
done

# openEMS: .so 扩展 (cpython-314)
for sofile in "${TMP_EXTRACT}/openEMS-Project/openEMS/python/build/lib.linux-x86_64-cpython-314/openEMS/"*.so; do
    [ -f "$sofile" ] || continue
    cp -a "$sofile" "${APPDIR}/python/openEMS/"
done

rm -rf "${TMP_EXTRACT}"

# 统计 Python 扩展
csxcad_so_count=$(ls "${APPDIR}/python/CSXCAD/"*.so 2>/dev/null | wc -l)
openems_so_count=$(ls "${APPDIR}/python/openEMS/"*.so 2>/dev/null | wc -l)
echo "  CSXCAD: ${csxcad_so_count} 个 .so 扩展"
echo "  openEMS: ${openems_so_count} 个 .so 扩展"

# ------------------------------------------------------------------------------
# 5. 复制 openEMS share 数据 (matlab 脚本等, 部分 Python API 可能引用)
# ------------------------------------------------------------------------------
echo "[5/7] 复制 share 数据..."
if [ -d "${SRC_OPENEMS}/share" ]; then
    cp -a "${SRC_OPENEMS}/share/"* "${APPDIR}/share/" 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# 6. 复制 openems_sim_worker.py (仿真 worker 脚本)
# ------------------------------------------------------------------------------
echo "[6/7] 复制仿真 worker 脚本..."
if [ -f "${WORKER_SRC}" ]; then
    cp -a "${WORKER_SRC}" "${APPDIR}/bin/"
fi

# ------------------------------------------------------------------------------
# 7. 创建 AppRun 入口脚本
# ------------------------------------------------------------------------------
echo "[7/7] 创建 AppRun 入口脚本..."
cat > "${APPDIR}/AppRun" << 'APPRUN_EOF'
#!/bin/bash
# ==============================================================================
# OpenEMS AppImage 入口脚本 (AppRun)
# ==============================================================================
# 自包含环境设置: LD_LIBRARY_PATH + PYTHONPATH
# 所有依赖 .so 和 Python 扩展均在 APPDIR 内, 不依赖外部环境。
#
# 用法:
#   AppRun openEMS [args...]          # 运行 openEMS 原生二进制
#   AppRun nf2ff [args...]            # 运行 nf2ff
#   AppRun sar_calc [args...]         # 运行 sar_calc
#   AppRun python -c "..."            # 运行 Python (带 CSXCAD/openEMS)
#   AppRun worker <input> <output>    # 运行 openems_sim_worker.py
#   AppRun check                      # 检查环境可用性
# ==============================================================================
set -euo pipefail

# 确定 APPDIR (AppRun 所在目录的绝对路径, 解析符号链接)
APPDIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export APPDIR

# 设置 LD_LIBRARY_PATH: APPDIR/lib 优先, 保留系统路径
export LD_LIBRARY_PATH="${APPDIR}/lib:${APPDIR}/lib/openems:${LD_LIBRARY_PATH:-}"

# 设置 PYTHONPATH: APPDIR/python 优先
export PYTHONPATH="${APPDIR}/python:${PYTHONPATH:-}"

# 设置 openEMS 环境变量
export OPENEMS_DIR="${APPDIR}"
export OPENEMS_BIN="${APPDIR}/bin/openEMS"

# 确定系统 Python (优先 3.14, 因为 .so 扩展为 cpython-314 编译)
SYS_PYTHON=""
for pybin in python3.14 python3.14.4 python3 python3.12; do
    if command -v "$pybin" &>/dev/null; then
        SYS_PYTHON="$pybin"
        break
    fi
done
if [ -z "$SYS_PYTHON" ]; then
    echo "[AppRun] ERROR: 未找到系统 Python (需要 3.14)" >&2
    exit 1
fi

# 子命令分发
cmd="${1:-check}"
case "$cmd" in
    check)
        # 检查环境可用性
        echo "[AppRun] APPDIR = ${APPDIR}"
        echo "[AppRun] Python = ${SYS_PYTHON} ($(${SYS_PYTHON} --version 2>&1))"
        echo "[AppRun] LD_LIBRARY_PATH = ${LD_LIBRARY_PATH}"
        echo "[AppRun] PYTHONPATH = ${PYTHONPATH}"
        echo ""
        echo "[AppRun] 检查 openEMS 二进制..."
        if [ -x "${APPDIR}/bin/openEMS" ]; then
            echo "  ✓ openEMS 二进制存在"
        else
            echo "  ✗ openEMS 二进制缺失"
            exit 1
        fi
        echo ""
        echo "[AppRun] 检查 Python 扩展..."
        ${SYS_PYTHON} -c "
import CSXCAD
from openEMS import openEMS, physical_constants
print('  ✓ CSXCAD 导入成功')
print('  ✓ openEMS 导入成功')
print(f'  ✓ physical_constants.C0 = {physical_constants.C0}')
" || {
            echo "  ✗ Python 扩展导入失败" >&2
            exit 1
        }
        echo ""
        echo "[AppRun] 检查 openEMS 二进制依赖..."
        ldd "${APPDIR}/bin/openEMS" 2>&1 | grep "not found" && {
            echo "  ✗ 存在未解析的依赖" >&2
            exit 1
        } || echo "  ✓ 所有依赖已解析"
        echo ""
        echo "[AppRun] ✓ OpenEMS AppImage 环境检查通过"
        ;;
    openEMS|nf2ff|sar_calc)
        shift
        exec "${APPDIR}/bin/${cmd}" "$@"
        ;;
    python)
        shift
        exec "${SYS_PYTHON}" "$@"
        ;;
    worker)
        # 运行 openems_sim_worker.py
        shift
        exec "${SYS_PYTHON}" "${APPDIR}/bin/openems_sim_worker.py" "$@"
        ;;
    *)
        # 默认: 尝试作为 openEMS 参数运行
        exec "${APPDIR}/bin/openEMS" "$@"
        ;;
esac
APPRUN_EOF
chmod +x "${APPDIR}/AppRun"

# ------------------------------------------------------------------------------
# 完成
# ------------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " ✓ OpenEMS AppImage 构建完成"
echo "  位置: ${APPDIR}"
echo "  入口: ${APPDIR}/AppRun"
echo ""
echo " 验证:"
echo "  ${APPDIR}/AppRun check"
echo "============================================================"
