#!/bin/bash
# ==============================================================================
# 3dtool-appimage 分目录打包脚本 (v2.0 manifest 模式)
# ==============================================================================
# 将 3dtool-appimage/ 按目录拆分打包, 每个包带 md5+sha256 双校验,
# 大包(>95M)split 分片, 生成 manifest.json 清单。
#
# 设计目标:
#   - 增量更新: 装新 pip 包只刷 python-site-packages.tar.gz, 不重传全部
#   - 自包含: 软链接实体化 (tar -h), 解包即用
#   - 校验完整: manifest.json 记录每个包的 md5+sha256, restore 时校验
#
# 产物 (输出到 $OUTPUT_DIR):
#   manifest.json                    # 清单: 所有包的校验码+版本+分片信息
#   AppRun.tar.gz                    # 小包不分片
#   python-site-packages.tar.gz.part_aa~ax  # 大包分片 ≤95M
#   ...
#
# 用法:
#   bash pack_3dtool_appimage.sh                 # 打包全部
#   bash pack_3dtool_appimage.sh python-site-packages  # 只打包指定包 (增量)
#   bash pack_3dtool_appimage.sh --verify        # 校验已打包的包
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# 路径定义
# - SCRIPT_DIR: 脚本所在目录 (3dtool/tools/)
# - REPO_3DTOOL_DIR: submodule 内 3dtool/ 子目录 (含 appimage-parts/scripts/tools)
# - APPDIR: 待打包的 AppImage 工作目录, 默认 /workspace/3dtool/3dtool-appimage,
#           可用环境变量 APPDIR 覆盖
# - OUTPUT_DIR: 分片输出目录, 自动定位到 ${REPO_3DTOOL_DIR}/appimage-parts/
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_3DTOOL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APPDIR="${APPDIR:-/workspace/3dtool/3dtool-appimage}"
OUTPUT_DIR="${REPO_3DTOOL_DIR}/appimage-parts"
MANIFEST="$OUTPUT_DIR/manifest.json"
SHARD_SIZE="95M"  # 每个分片最大 95M (GitHub 单文件 100M 限制, 留余量)

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[pack]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[warn]${NC} $*" >&2; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }

# ------------------------------------------------------------------------------
# 包定义: name|source_path|shard(0=不分片, 1=分片)|exclude(可选, 空格分隔)
# 顺序: 小包在前, 大包在后 (便于增量打包时跳过未变更包)
# 软链接实体化: tar -h (dereference)
# ------------------------------------------------------------------------------
PACKAGES=(
  "AppRun|AppRun|0|"
  "bin|bin|0|"
  "lib|lib|1|"
  "python-runtime|python|0|python/lib/python3.14/site-packages"
  "python-site-packages|python/lib/python3.14/site-packages|1|"
  "kicad-3dmodels|share/kicad/3dmodels|1|"
  "kicad-symbols|share/kicad/symbols|1|"
  "kicad-footprints|share/kicad/footprints|0|"
  "kicad-demos|share/kicad/demos|1|"
  "kicad-misc|share/kicad/internat share/kicad/template share/kicad/resources share/kicad/scripting share/kicad/schemas share/kicad/plugins|0|"
  "jre|jre|1|"
)

# ------------------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------------------
compute_hash() {
  # 计算文件 md5+sha256, 输出 "md5 sha256"
  local file="$1"
  local md5 sha256
  md5=$(md5sum "$file" | awk '{print $1}')
  sha256=$(sha256sum "$file" | awk '{print $1}')
  echo "$md5 $sha256"
}

shard_file() {
  # 将大文件 split 成 ≤95M 分片, 返回分片数
  local file="$1"
  local prefix="${file}.part_"
  # 清理旧分片
  rm -f "${prefix}"*
  # split: 分片后缀 part_aa, part_ab, ... (与现有方案一致)
  split -b "$SHARD_SIZE" -a 2 "$file" "$prefix"
  # 重命名后缀: part_aa (split 默认就是 aa, ab, ... 无需重命名)
  ls "${prefix}"* | wc -l
}

# ------------------------------------------------------------------------------
# 打包单个包
# ------------------------------------------------------------------------------
pack_one() {
  local name="$1"
  local sources="$2"
  local shard_flag="$3"
  local exclude="${4:-}"

  local tarball="$OUTPUT_DIR/${name}.tar.gz"
  log "打包 $name → ${name}.tar.gz (源: $sources${exclude:+, 排除: $exclude})"

  # 切换到 AppDir, 使 tar 路径干净 (不含 AppDir 前缀)
  cd "$APPDIR"

  # 构建 exclude 参数 (每个 exclude 路径一个 --exclude)
  local exclude_args=""
  if [ -n "$exclude" ]; then
    for ex in $exclude; do
      exclude_args="$exclude_args --exclude=$ex"
    done
  fi

  # tar -h: 实体化软链接 (jre/wheels 解引用为实体文件)
  # -c: 创建, -z: gzip, -f: 文件
  # 若 sources 含空格(多路径), 用 tar 多参数
  # tar 退出码: 0=成功, 1=警告(如悬空软链接), 2=致命错误
  # 容忍退出码 0 和 1 (悬空软链接不影响有效文件打包)
  tar -czh $exclude_args -f "$tarball" $sources 2>/dev/null || rc=$?
  local rc=${rc:-0}
  if [ "$rc" -ge 2 ]; then
    err "打包失败: $name (源: $sources, tar exit=$rc)"
    cd - >/dev/null
    return 1
  fi
  if [ "$rc" -eq 1 ]; then
    warn "  $name: tar 有警告 (可能含悬空软链接, 不影响有效文件)"
  fi
  cd - >/dev/null

  local size
  size=$(stat -c%s "$tarball")
  log "  原始大小: $((size / 1024 / 1024))M"

  # 计算原始 tar.gz 的 hash (分片前)
  local hash md5 sha256
  hash=$(compute_hash "$tarball")
  md5=$(echo "$hash" | awk '{print $1}')
  sha256=$(echo "$hash" | awk '{print $2}')

  local sharded="false"
  local shard_count=0
  local shard_suffix=""

  if [ "$shard_flag" = "1" ]; then
    # 大包: split 分片, 删除原始 tar.gz
    shard_count=$(shard_file "$tarball")
    rm -f "$tarball"
    sharded="true"
    shard_suffix="part_aa"
    log "  分片: ${shard_count} 片 (每片 ≤${SHARD_SIZE})"
  fi

  # 输出 JSON 行 (供 generate_manifest 收集)
  # 格式: name|tarball_basename|size|md5|sha256|sharded|shard_count|shard_suffix
  local basename
  if [ "$sharded" = "true" ]; then
    basename="${name}.tar.gz"
  else
    basename="${name}.tar.gz"
  fi
  echo "${name}|${basename}|${size}|${md5}|${sha256}|${sharded}|${shard_count}|${shard_suffix}"
}

# ------------------------------------------------------------------------------
# 生成 manifest.json
# ------------------------------------------------------------------------------
generate_manifest() {
  # 从 stdin 读取多行 "name|basename|size|md5|sha256|sharded|shard_count|shard_suffix"
  local entries=()
  while IFS= read -r line; do
    entries+=("$line")
  done

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  {
    echo "{"
    echo "  \"version\": \"2.0.0\","
    echo "  \"schema\": \"3dtool-appimage-parts-v2\","
    echo "  \"packed_at\": \"${now}\","
    echo "  \"appimage_dir\": \"3dtool-appimage\","
    echo "  \"shard_size\": \"${SHARD_SIZE}\","
    echo "  \"packages\": ["
    local first=1
    for entry in "${entries[@]}"; do
      IFS='|' read -r name basename size md5 sha256 sharded shard_count shard_suffix <<< "$entry"
      if [ "$first" = "1" ]; then
        first=0
      else
        echo ","
      fi
      printf '    {"name":"%s","file":"%s","size":%s,"md5":"%s","sha256":"%s","sharded":%s,"shard_count":%s,"shard_suffix":"%s"}' \
        "$name" "$basename" "$size" "$md5" "$sha256" "$sharded" "$shard_count" "$shard_suffix"
    done
    echo ""
    echo "  ]"
    echo "}"
  } > "$MANIFEST"
  log "manifest.json 生成: $MANIFEST"
}

# ------------------------------------------------------------------------------
# 校验已打包的包
# ------------------------------------------------------------------------------
verify_packages() {
  log "校验 manifest.json 中所有包..."
  [ -f "$MANIFEST" ] || { err "manifest.json 不存在"; return 1; }

  local fail=0
  # 解析 manifest.json (用 python3 确保正确解析 JSON)
  cd "$OUTPUT_DIR"
  while IFS='|' read -r name file size md5 sha256 sharded shard_count; do
    if [ "$sharded" = "True" ] || [ "$sharded" = "true" ]; then
      # 分片包: 重组后校验
      log "校验分片包: $name (${shard_count}片)"
      local parts="${file}.part_"
      if ! ls ${parts}* >/dev/null 2>&1; then
        err "  ✗ 分片缺失: $name"
        fail=1; continue
      fi
      local actual_md5
      actual_md5=$(cat ${parts}* | md5sum | awk '{print $1}')
      if [ "$actual_md5" != "$md5" ]; then
        err "  ✗ md5 不匹配: $name (期望 $md5, 实际 $actual_md5)"
        fail=1
      else
        log "  ✓ $name md5 校验通过"
      fi
    else
      # 非分片包: 直接校验
      log "校验单文件包: $name"
      if [ ! -f "$file" ]; then
        err "  ✗ 文件缺失: $file"
        fail=1; continue
      fi
      local actual_md5
      actual_md5=$(md5sum "$file" | awk '{print $1}')
      if [ "$actual_md5" != "$md5" ]; then
        err "  ✗ md5 不匹配: $file (期望 $md5, 实际 $actual_md5)"
        fail=1
      else
        log "  ✓ $name md5 校验通过"
      fi
    fi
  done < <(python3 -c "
import json
with open('$MANIFEST') as f:
    m = json.load(f)
for p in m['packages']:
    print(f\"{p['name']}|{p['file']}|{p['size']}|{p['md5']}|{p['sha256']}|{p['sharded']}|{p['shard_count']}\")
")
  cd - >/dev/null
  return $fail
}

# ------------------------------------------------------------------------------
# 主逻辑
# ------------------------------------------------------------------------------
main() {
  local mode="${1:-all}"

  [ -d "$APPDIR" ] || { err "3dtool-appimage 不存在: $APPDIR"; exit 1; }
  mkdir -p "$OUTPUT_DIR"

  case "$mode" in
    --verify)
      verify_packages
      exit $?
      ;;
    all)
      log "全量打包 (${#PACKAGES[@]} 个包)..."
      ;;
    *)
      log "增量打包: $mode"
      ;;
  esac

  # 收集所有包的 manifest 条目
  local entries=()
  local total_size=0

  for pkg in "${PACKAGES[@]}"; do
    IFS='|' read -r name sources shard_flag exclude <<< "$pkg"

    # 增量模式: 只打包指定包
    if [ "$mode" != "all" ] && [ "$mode" != "$name" ]; then
      continue
    fi

    local entry
    entry=$(pack_one "$name" "$sources" "$shard_flag" "$exclude") || exit 1
    entries+=("$entry")

    local size
    size=$(echo "$entry" | awk -F'|' '{print $3}')
    total_size=$((total_size + size))
    echo ""
  done

  if [ "${#entries[@]}" -eq 0 ]; then
    err "未匹配任何包 (mode=$mode)"
    exit 1
  fi

  # 生成 manifest.json (仅当全量打包时, 增量打包需合并)
  if [ "$mode" = "all" ]; then
    printf '%s\n' "${entries[@]}" | generate_manifest
  elif [ ! -f "$MANIFEST" ]; then
    # 增量模式但 manifest 不存在 (首次): 用当前条目创建新 manifest
    log "manifest 不存在, 创建新 manifest (首次增量)"
    printf '%s\n' "${entries[@]}" | generate_manifest
  else
    # 增量打包: 更新 manifest.json 中对应包的条目
    log "增量更新 manifest.json: $mode"
    python3 -c "
import json, sys

entries = '''${entries[*]}'''.split('\n')
new_entry = None
for e in entries:
    if e:
        new_entry = e

if not new_entry:
    sys.exit('no entry')

name, file, size, md5, sha256, sharded, shard_count, shard_suffix = new_entry.split('|')

with open('$MANIFEST') as f:
    manifest = json.load(f)

# 更新或添加对应包
found = False
for i, p in enumerate(manifest['packages']):
    if p['name'] == name:
        manifest['packages'][i] = {
            'name': name, 'file': file, 'size': int(size),
            'md5': md5, 'sha256': sha256,
            'sharded': sharded == 'true', 'shard_count': int(shard_count),
            'shard_suffix': shard_suffix
        }
        found = True
        break
if not found:
    manifest['packages'].append({
        'name': name, 'file': file, 'size': int(size),
        'md5': md5, 'sha256': sha256,
        'sharded': sharded == 'true', 'shard_count': int(shard_count),
        'shard_suffix': shard_suffix
    })

manifest['packed_at'] = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
with open('$MANIFEST', 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f'manifest.json 已更新: {name}')
"
  fi

  log "========================================"
  log "打包完成!"
  log "  总大小: $((total_size / 1024 / 1024))M"
  log "  输出目录: $OUTPUT_DIR"
  log "  manifest: $MANIFEST"
  log "========================================"
}

main "$@"
