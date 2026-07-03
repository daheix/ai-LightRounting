#!/usr/bin/env bash
# PoLaRIS/scripts/restore_3dtool_selective.sh — 3dtool AppImage 按需拉取+选择性解包
#
# *创新*: 按需拉取 + 选择性解包（解决 2.0G 全量拉取磁盘爆问题）
#
# 创新逻辑:
#   - sparse-checkout 排除 appimage-parts/（工作区不占 2.0G）
#   - 用 git cat-file 从 partial clone 按需拉取单个 blob（只拉需要的组件）
#   - 按 manifest.json 选择性解包（跳过不需要的组件）
#   - 组件分层：核心（bin+lib+AppRun）+ 可选（kicad数据/jre/python）
#
# 底层理论:
#   - git partial clone 的 promisor remote 支持 git cat-file 按需拉取任意 blob
#     参考: https://git-scm.com/docs/partial-clone
#   - git sparse-checkout 排除目录不影响 git cat-file 访问该路径的 blob
#
# 3dtool AppImage 组件（2.0G，11 个组件）:
#   组件                    大小    分片数  PoLaRIS需要  用途
#   AppRun                  2.6K    0       ✓           AppImage 启动器
#   bin                     55M     0       ✓           30个工具(kicad/openEMS/ElmerSolver/ngspice)
#   lib                     354M    4       ✓           .so 共享库依赖
#   python-runtime          103M    0       ✗           沙箱有 pyenv 3.14
#   python-site-packages    735M    8       ✗           有 wheels 离线包
#   kicad-3dmodels          458M    5       可选        KiCad 3D 模型
#   kicad-symbols           23M     1       可选        KiCad 符号库
#   kicad-footprints        15M     0       可选        KiCad 封装库
#   kicad-demos             96M     1       ✗           KiCad 示例
#   kicad-misc              23M     0       可选        KiCad 杂项
#   jre                     222M    3       可选        Java 运行时
#
# 体积对比:
#   完整:           2.0G（全量拉取，磁盘爆）
#   核心(默认):     410M（AppRun + bin + lib）
#   +KiCad 数据:    471M（+ symbols + footprints + misc）
#   +3D 模型:       929M（+ 3dmodels）
#   +JRE:          1151M（+ jre）
#
# 用法:
#   bash scripts/restore_3dtool_selective.sh                    # 核心组件（默认）
#   bash scripts/restore_3dtool_selective.sh --with-kicad       # 核心 + KiCad 数据
#   bash scripts/restore_3dtool_selective.sh --with-3dmodels    # 核心 + KiCad + 3D 模型
#   bash scripts/restore_3dtool_selective.sh --with-jre         # 核心 + JRE
#   bash scripts/restore_3dtool_selective.sh --all              # 全部组件（2.0G）
#   bash scripts/restore_3dtool_selective.sh -v                 # 详细输出
#   bash scripts/restore_3dtool_selective.sh --force            # 强制重新解包
#
# 规则依据:
#   R01 方案检索: git partial clone https://git-scm.com/docs/partial-clone
#   R03 禁止 fall-back: 任何步骤失败即 exit
#   R05 Bug 必修
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUBMODULE_DIR="${REPO_DIR}/3dtool"
APPDIR="${REPO_DIR}/3dtool-appimage"
MANIFEST_PATH="3dtool/appimage-parts/manifest.json"
PARTS_PREFIX="3dtool/appimage-parts/"

VERBOSE=0
FORCE=0
WITH_KICAD=0
WITH_3DMODELS=0
WITH_JRE=0
ALL=0

for arg in "$@"; do
    case "${arg}" in
        -v|--verbose) VERBOSE=1 ;;
        --force) FORCE=1 ;;
        --with-kicad) WITH_KICAD=1 ;;
        --with-3dmodels) WITH_3DMODELS=1 ;;
        --with-jre) WITH_JRE=1 ;;
        --all) ALL=1 ;;
    esac
done

if [ "${ALL}" = "1" ]; then
    WITH_KICAD=1; WITH_3DMODELS=1; WITH_JRE=1
fi

ts() { date "+%H:%M:%S"; }
log() { echo "[$(ts)] [3dtool] $*"; }
logv() { [ "${VERBOSE}" = "1" ] && echo "[$(ts)] [3dtool][V] $*" || true; }
err() { echo "[$(ts)] [3dtool][ERROR] $*" >&2; }

# 确定需要的组件列表
declare -a WANTED=()
WANTED+=("AppRun")     # 启动器（2.6K，必装）
WANTED+=("bin")        # 30 个工具（55M，必装）
WANTED+=("lib")        # .so 依赖（354M，必装）
if [ "${WITH_KICAD}" = "1" ] || [ "${WITH_3DMODELS}" = "1" ]; then
    WANTED+=("kicad-symbols")
    WANTED+=("kicad-footprints")
    WANTED+=("kicad-misc")
fi
if [ "${WITH_3DMODELS}" = "1" ]; then
    WANTED+=("kicad-3dmodels")
fi
if [ "${WITH_JRE}" = "1" ]; then
    WANTED+=("jre")
fi

# 幂等检查：AppDir 已存在且 AppRun 可执行则跳过（除非 --force）
if [ "${FORCE}" != "1" ] && [ -x "${APPDIR}/AppRun" ]; then
    log "3dtool-appimage 已存在，跳过（--force 强制重装）"
    exit 0
fi

# 检查子仓库
if [ ! -d "${SUBMODULE_DIR}/.git" ] && [ ! -f "${SUBMODULE_DIR}/.git" ]; then
    err "3dtool 子仓库不存在，请先运行 setup_3dtool_submodule.sh"
    exit 1
fi

cd "${SUBMODULE_DIR}" || { err "无法进入 ${SUBMODULE_DIR}"; exit 1; }

# 读取 manifest.json 获取组件信息（文件/分片数/md5）
log "读取 manifest.json..."
if ! MANIFEST_JSON=$(git cat-file -p "HEAD:${MANIFEST_PATH}" 2>/dev/null); then
    err "无法读取 manifest.json（git cat-file 失败）"
    err "请确认 3dtool 子仓库已恢复且 partial clone 正常"
    exit 1
fi

# 解析 manifest 获取需要的组件信息
log "选择组件: ${WANTED[*]}"
echo "${MANIFEST_JSON}" | python3 -c "
import json, sys
m = json.load(sys.stdin)
for p in m['packages']:
    print(f\"{p['name']}|{p['file']}|{p['size']}|{p['md5']}|{p['sharded']}|{p['shard_count']}\")
" > /tmp/3dtool_manifest.txt

# 按需拉取 + 校验 + 解包
TMP_PARTS=$(mktemp -d /tmp/3dtool_parts.XXXXXX)
trap 'rm -rf "${TMP_PARTS}"' EXIT

mkdir -p "${APPDIR}"
TOTAL_SIZE=0
EXTRACTED=0

for entry in "${WANTED[@]}"; do
    # 从 manifest 查找组件信息
    line=$(grep "^${entry}|" /tmp/3dtool_manifest.txt)
    if [ -z "${line}" ]; then
        err "组件 ${entry} 不在 manifest 中"
        exit 1
    fi

    IFS='|' read -r name file size md5 sharded shard_count <<< "${line}"
    logv "  [${name}] ${file} size=${size} sharded=${sharded} shards=${shard_count}"

    # 按需拉取 blob（git cat-file 从 partial clone）
    BLOB_PATH="${PARTS_PREFIX}${file}"
    TMP_FILE="${TMP_PARTS}/${file}"
    mkdir -p "$(dirname "${TMP_FILE}")"

    if [ "${sharded}" = "True" ] || [ "${sharded}" = "true" ]; then
        # 分片包：拉取所有分片并合并
        # 分片命名: part_aa, part_ab, ..., part_ah（双字母，第二字母从 a 递增）
        logv "  [${name}] 拉取 ${shard_count} 个分片..."
        > "${TMP_FILE}"
        for i in $(seq 0 $((shard_count - 1))); do
            second_char=$(printf "\\$(printf '%03o' $((97 + i)))")
            shard_suffix="part_a${second_char}"
            SHARD_PATH="${BLOB_PATH}.${shard_suffix}"
            logv "    拉取 ${shard_suffix}..."
            if ! git cat-file -p "HEAD:${SHARD_PATH}" >> "${TMP_FILE}" 2>/dev/null; then
                err "拉取分片失败: ${SHARD_PATH}"
                exit 1
            fi
        done
    else
        # 非分片包：直接拉取
        logv "  [${name}] 拉取 ${file}..."
        if ! git cat-file -p "HEAD:${BLOB_PATH}" > "${TMP_FILE}" 2>/dev/null; then
            err "拉取失败: ${BLOB_PATH}"
            exit 1
        fi
    fi

    # md5 校验
    ACTUAL_MD5=$(md5sum "${TMP_FILE}" | awk '{print $1}')
    if [ "${ACTUAL_MD5}" != "${md5}" ]; then
        err "  [${name}] md5 校验失败（期望 ${md5}，实际 ${ACTUAL_MD5}）"
        exit 1
    fi
    logv "  [${name}] md5 校验通过"

    # 解包到 AppDir
    log "  [${name}] 解包 ($(numfmt --to=iec ${size} 2>/dev/null || echo ${size}))..."
    if ! tar xzf "${TMP_FILE}" -C "${APPDIR}" 2>/dev/null; then
        err "  [${name}] 解包失败"
        exit 1
    fi

    TOTAL_SIZE=$((TOTAL_SIZE + size))
    EXTRACTED=$((EXTRACTED + 1))
    rm -f "${TMP_FILE}"
done

# 设置可执行权限
chmod +x "${APPDIR}/AppRun" 2>/dev/null || true
chmod +x "${APPDIR}/bin/"* 2>/dev/null || true

# 校验 AppRun
if [ ! -x "${APPDIR}/AppRun" ]; then
    err "解包后 AppRun 不可执行: ${APPDIR}/AppRun"
    exit 1
fi

# 工具数量
TOOL_COUNT=$(ls "${APPDIR}/bin/"* 2>/dev/null | wc -l)

log "恢复完成:"
log "  AppDir:     ${APPDIR}"
log "  组件:       ${EXTRACTED} 个（${WANTED[*]}）"
log "  解包大小:   $(du -sh "${APPDIR}" 2>/dev/null | cut -f1)"
log "  工具数:     ${TOOL_COUNT}（bin/ 目录）"
log "  AppRun:     $([ -x "${APPDIR}/AppRun" ] && echo '可执行 ✓' || echo '不可执行 ✗')"

# 列出工具
if [ "${VERBOSE}" = "1" ] && [ -d "${APPDIR}/bin" ]; then
    logv "工具列表:"
    ls "${APPDIR}/bin/" 2>/dev/null | sed 's/^/    /'
fi

exit 0
