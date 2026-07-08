#!/bin/bash
# ==============================================================================
# restore_3dtool_appimage.sh - 跨仓库恢复统一 AppDir (3dtool-appimage)
# ==============================================================================
# 从本仓库 3dtool/appimage-parts/ 下的分片压缩包解压恢复统一 AppDir
# 统一 AppDir 含全部工具 (Python3.14 + C++ + Fortran + Java + KiCad + .so)
# 解压后通过 AppRun <tool> [args] 调用, 自包含不依赖外部环境
#
# 支持两种模式 (自动检测):
#   v2 (manifest): 按 manifest.json 分目录校验+解包 (推荐, 增量更新)
#   v1 (legacy):   整体分片 cat | tar xzf (向后兼容)
#
# 用法 (在主仓库 ai-ddr5 工作目录中执行):
#   bash 3dtool/subrepo/3dtool/scripts/restore_3dtool_appimage.sh 3dtool/3dtool-appimage
#   # 参数1=目标 AppDir 路径 (默认 ./3dtool-appimage)
# ==============================================================================
set -euo pipefail

# 本仓库 3dtool/ 子目录 (脚本在 3dtool/scripts/ 下, 上两级即 3dtool/)
_3DTOOL_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_PARTS_DIR="${_3DTOOL_REPO_DIR}/appimage-parts"
_MANIFEST="${_PARTS_DIR}/manifest.json"
_PART_PREFIX="${_PARTS_DIR}/3dtool-appimage.tar.gz.part_"

# 目标 AppDir: 参数1 指定, 默认当前工作目录下的 3dtool-appimage/
# 转为绝对路径, 避免后续 cd 后相对路径失效 (R05 bug 修复)
_APPDIR_RAW="${1:-${PWD}/3dtool-appimage}"
_APPDIR="$(cd "$(dirname "${_APPDIR_RAW}")" && pwd)/$(basename "${_APPDIR_RAW}")"
_APPRUN="${_APPDIR}/AppRun"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[restore]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[restore]${NC} $*" >&2; }
err()  { echo -e "${RED}[restore 错误]${NC} $*" >&2; }

# 1. 已存在且完整则跳过 (幂等)
if [ -x "$_APPRUN" ]; then
    log "3dtool-appimage 已存在 ($_APPRUN), 跳过恢复"
    exit 0
fi

# 2. 检查分片目录
if [ ! -d "$_PARTS_DIR" ]; then
    err "分片目录不存在: $_PARTS_DIR"
    err "请确认已完整 clone daheix/3dtool 仓库"
    exit 1
fi
mkdir -p "$(dirname "$_APPDIR")"

# ==============================================================================
# v2: manifest 模式 (分目录校验+解包)
# ==============================================================================
restore_v2() {
    log "v2 manifest 模式: 按 manifest.json 分目录校验+解包"

    [ -f "$_MANIFEST" ] || { err "manifest.json 不存在"; return 1; }

    # 解析 manifest, 逐包校验
    log "阶段1: 校验所有包的 md5..."
    if ! _verify_all_packages; then
        err "包校验失败, 请重新 clone 仓库或检查分片完整性"
        return 1
    fi

    # 逐包解包
    log "阶段2: 逐包解包到 $_APPDIR ..."
    mkdir -p "$_APPDIR"
    if ! _extract_all_packages; then
        err "解包失败"
        return 1
    fi
    return 0
}

# 校验 manifest 中所有包
_verify_all_packages() {
    local fail=0
    cd "$_PARTS_DIR"
    while IFS='|' read -r name file size md5 sha256 sharded shard_count; do
        if [ "$sharded" = "True" ] || [ "$sharded" = "true" ]; then
            _verify_sharded "$name" "$file" "$md5" "$shard_count" || fail=1
        else
            _verify_single "$name" "$file" "$md5" || fail=1
        fi
    done < <(python3 -c "
import json
with open('$_MANIFEST') as f:
    m = json.load(f)
for p in m['packages']:
    print(f\"{p['name']}|{p['file']}|{p['size']}|{p['md5']}|{p['sha256']}|{p['sharded']}|{p['shard_count']}\")
")
    cd - >/dev/null
    return $fail
}

_verify_sharded() {
    local name="$1" file="$2" expected_md5="$3" count="$4"
    local parts="${file}.part_"
    if ! ls ${parts}* >/dev/null 2>&1; then
        err "  ✗ $name: 分片缺失 (${parts}*)"
        return 1
    fi
    local actual_count actual_md5
    actual_count=$(ls ${parts}* | wc -l)
    if [ "$actual_count" != "$count" ]; then
        err "  ✗ $name: 分片数不匹配 (期望 $count, 实际 $actual_count)"
        return 1
    fi
    actual_md5=$(cat ${parts}* | md5sum | awk '{print $1}')
    if [ "$actual_md5" != "$expected_md5" ]; then
        err "  ✗ $name: md5 不匹配 (期望 $expected_md5, 实际 $actual_md5)"
        return 1
    fi
    log "  ✓ $name: ${count}片 md5 校验通过"
    return 0
}

_verify_single() {
    local name="$1" file="$2" expected_md5="$3"
    if [ ! -f "$file" ]; then
        err "  ✗ $name: 文件缺失 ($file)"
        return 1
    fi
    local actual_md5
    actual_md5=$(md5sum "$file" | awk '{print $1}')
    if [ "$actual_md5" != "$expected_md5" ]; then
        err "  ✗ $name: md5 不匹配 (期望 $expected_md5, 实际 $actual_md5)"
        return 1
    fi
    log "  ✓ $name: md5 校验通过"
    return 0
}

# 解包所有包到 AppDir
_extract_all_packages() {
    cd "$_PARTS_DIR"
    while IFS='|' read -r name file size md5 sha256 sharded shard_count; do
        log "  解包: $name"
        if [ "$sharded" = "True" ] || [ "$sharded" = "true" ]; then
            # 分片包: cat parts | tar xzf - -C AppDir
            if ! cat "${file}.part_"* | tar xzf - -C "$_APPDIR" 2>/dev/null; then
                err "  ✗ $name 解包失败"
                cd - >/dev/null; return 1
            fi
        else
            # 非分片包: tar xzf file -C AppDir
            if ! tar xzf "$file" -C "$_APPDIR" 2>/dev/null; then
                err "  ✗ $name 解包失败"
                cd - >/dev/null; return 1
            fi
        fi
        log "  ✓ $name 解包完成"
    done < <(python3 -c "
import json
with open('$_MANIFEST') as f:
    m = json.load(f)
for p in m['packages']:
    print(f\"{p['name']}|{p['file']}|{p['size']}|{p['md5']}|{p['sha256']}|{p['sharded']}|{p['shard_count']}\")
")
    cd - >/dev/null
    return 0
}

# ==============================================================================
# v1: legacy 模式 (整体分片 cat | tar)
# ==============================================================================
restore_v1() {
    log "v1 legacy 模式: 整体分片合并解压"
    if ! ls "${_PART_PREFIX}"* >/dev/null 2>&1; then
        err "找不到分片: ${_PART_PREFIX}aa"
        return 1
    fi
    local count
    count=$(ls "${_PART_PREFIX}"* | wc -l)
    log "发现 $count 个分片, 合并解压..."
    local tar_parent
    tar_parent="$(dirname "$_APPDIR")"
    cd "$tar_parent"
    if ! cat "${_PART_PREFIX}"* | tar xzf -; then
        err "解压失败, 请检查分片完整性"
        cd - >/dev/null; return 1
    fi
    cd - >/dev/null
    return 0
}

# ==============================================================================
# 主逻辑: 检测模式并执行
# ==============================================================================
log "分片目录: $_PARTS_DIR"
log "目标 AppDir: $_APPDIR"

# 优先 v2 (manifest.json 存在), 回退 v1 (整体分片)
if [ -f "$_MANIFEST" ]; then
    if ! restore_v2; then
        err "v2 恢复失败"
        exit 1
    fi
elif ls "${_PART_PREFIX}"* >/dev/null 2>&1; then
    if ! restore_v1; then
        err "v1 恢复失败"
        exit 1
    fi
else
    err "未找到 manifest.json 也未找到整体分片, 仓库内容不完整"
    exit 1
fi

# 校验 AppRun 入口
if [ ! -x "$_APPRUN" ]; then
    err "解压后 AppRun 缺失或不可执行: $_APPRUN"
    chmod +x "$_APPRUN" 2>/dev/null || true
    if [ ! -x "$_APPRUN" ]; then
        err "AppRun 仍不可执行, 恢复失败"
        exit 1
    fi
fi

# 设置可执行权限 (git 不保留 +x)
chmod +x "${_APPDIR}/bin/"* 2>/dev/null || true
chmod +x "${_APPDIR}/python/bin/"* 2>/dev/null || true
chmod +x "${_APPDIR}/jre/bin/"* 2>/dev/null || true
chmod +x "${_APPDIR}/AppRun" 2>/dev/null || true

# 自检
log "恢复完成, 运行 AppRun check 验证..."
if bash "$_APPRUN" check >/dev/null 2>&1; then
    log "✅ 3dtool-appimage 恢复成功 (AppRun check 通过)"
else
    warn "AppRun check 有警告, 请手动运行: bash $_APPRUN check"
fi
exit 0
