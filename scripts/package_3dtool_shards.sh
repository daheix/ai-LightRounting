#!/usr/bin/env bash
# -*- mode: shell-script; -*-
#
# package_3dtool_shards.sh — 3dtool 新工具分片增量打包脚本
#
# 用途：
#   将 3dtool/subrepo/3dtool/ 下新增/变更的工具打包为分片压缩包，
#   仅上传新增分片，避免重复传输大体积工具二进制。
#
# 用法：
#   bash scripts/package_3dtool_shards.sh <tool_dir>   # 打包指定工具目录
#   bash scripts/package_3dtool_shards.sh --list       # 列出已打包工具
#   bash scripts/package_3dtool_shards.sh --help       # 显示帮助
#
# 打包流程：
#   tar cf - <tool_base> | gzip | split -b 24M - <prefix>.part_
#   分片命名: <tool_name>.tar.gz.part_aa, .part_ab, ...
#   输出目录: 3dtool/subrepo/3dtool/3dtool-appimage-parts/
#
# manifest.json 更新（追加，禁止整体重写）：
#   路径: 3dtool/subrepo/3dtool/3dtool-appimage-parts/manifest.json
#   条目: {"name", "shards", "size", "created"}
#
# 来源：
#   - spec 阶段六：分片增量上传
#   - R03 禁止 fall-back：tar/gzip/split 失败即 exit 1，禁止 || true
#   - R08 代码提交纪律：精确 git add，禁止 git add -A
#   - AGENTS.md §16 空间清理
#
# 参考：
#   - GNU split:          https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html
#   - GNU tar + gzip:     https://www.gnu.org/software/tar/manual/html_node/Using-Gzip.html
#   - JSON RFC 8259:      https://datatracker.ietf.org/doc/html/rfc8259
#   - ISO 8601:           https://www.iso.org/iso-8601-date-and-time-format.html
#   - git add:            https://git-scm.com/docs/git-add

set -euo pipefail

# ===== 路径常量 =====
POLARIS_3DTOOL_HOME="/workspace/3dtool/subrepo/3dtool"
PARTS_DIR="${POLARIS_3DTOOL_HOME}/3dtool-appimage-parts"
MANIFEST="${PARTS_DIR}/manifest.json"
SHARD_SIZE="24M"

# ===== 颜色（ANSI） =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

_echo_red()    { printf "${RED}%b${NC}\n" "$*"; }
_echo_green()  { printf "${GREEN}%b${NC}\n" "$*"; }
_echo_yellow() { printf "${YELLOW}%b${NC}\n" "$*"; }
_echo_blue()   { printf "${BLUE}%b${NC}\n" "$*"; }

# ===== 帮助 =====
_show_help() {
    cat <<'EOF'
package_3dtool_shards.sh — 3dtool 新工具分片增量打包

用法:
  bash scripts/package_3dtool_shards.sh <tool_dir>   打包指定工具目录
  bash scripts/package_3dtool_shards.sh --list       列出已打包工具
  bash scripts/package_3dtool_shards.sh --help       显示本帮助

行为:
  1. 将 <tool_dir> 通过 tar | gzip | split 打包为 ≤24MB 的分片
  2. 分片输出到 3dtool/subrepo/3dtool/3dtool-appimage-parts/
  3. 追加更新 manifest.json（不重写已有条目）
  4. git add 仅新增分片 + manifest.json（禁止 git add -A）

示例:
  bash scripts/package_3dtool_shards.sh 3dtool/subrepo/3dtool/3dtool-appimage/bin/newtool
  bash scripts/package_3dtool_shards.sh --list
EOF
}

# ===== 依赖检查（R03：缺依赖即退出，不 fall-back） =====
_require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        _echo_red "[ERROR] 缺少依赖命令: ${cmd}"
        exit 1
    fi
}

# ===== --list 模式 =====
list_packages() {
    _require_cmd python3
    if [[ ! -f "${MANIFEST}" ]]; then
        _echo_yellow "[INFO] manifest.json 不存在: ${MANIFEST}"
        _echo_yellow "[INFO] 已打包工具列表为空"
        exit 0
    fi
    _echo_blue "[INFO] 已打包工具清单（来源: ${MANIFEST}）:"
    python3 - "${MANIFEST}" <<'PYEOF'
import json, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    print(f"[ERROR] manifest.json 解析失败: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(data, dict):
    print("[ERROR] manifest.json 顶层不是 JSON 对象", file=sys.stderr)
    sys.exit(1)
pkgs = data.get("packages", [])
if not isinstance(pkgs, list):
    print("[ERROR] manifest.json 'packages' 不是数组", file=sys.stderr)
    sys.exit(1)
if not pkgs:
    print("[INFO] packages 数组为空")
else:
    for p in pkgs:
        name = p.get("name", "?")
        size = p.get("size", 0)
        created = p.get("created", "?")
        shards = p.get("shards", [])
        print(f"  - {name}: {len(shards)} 分片, {size} bytes, 创建于 {created}")
PYEOF
    exit 0
}

# ===== 打包模式 =====
package_tool() {
    local tool_dir="$1"

    _require_cmd tar
    _require_cmd gzip
    _require_cmd split
    _require_cmd python3
    _require_cmd stat
    _require_cmd date
    _require_cmd basename
    _require_cmd dirname

    # 校验工具目录存在（R03）
    if [[ ! -d "${tool_dir}" ]]; then
        _echo_red "[ERROR] 工具目录不存在: ${tool_dir}"
        exit 1
    fi

    # 解析工具名（取目录基名）
    local tool_name
    tool_name="$(basename "${tool_dir}")"
    if [[ -z "${tool_name}" ]]; then
        _echo_red "[ERROR] 无法从路径解析工具名: ${tool_dir}"
        exit 1
    fi

    # 创建分片输出目录
    if [[ ! -d "${PARTS_DIR}" ]]; then
        mkdir -p "${PARTS_DIR}"
        _echo_blue "[INFO] 创建分片目录: ${PARTS_DIR}"
    fi

    # 检查同名工具是否已打包（禁止重复，R03 不 fall-back）
    if [[ -f "${MANIFEST}" ]]; then
        local dup_check
        if ! dup_check=$(python3 - "${MANIFEST}" "${tool_name}" <<'PYEOF'
import json, sys
path, name = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    print(f"[ERROR] manifest.json 解析失败: {e}", file=sys.stderr)
    sys.exit(1)
for p in data.get("packages", []):
    if p.get("name") == name:
        print("dup")
        sys.exit(0)
print("ok")
PYEOF
); then
            _echo_red "[ERROR] manifest.json 重名检查失败（python 退出非 0）"
            exit 1
        fi
        if [[ "${dup_check}" != "ok" ]]; then
            _echo_red "[ERROR] 工具 '${tool_name}' 已在 manifest.json 中，禁止重复打包"
            _echo_yellow "[HINT]  如需重新打包，请先手动移除旧条目与分片文件"
            exit 1
        fi
    fi

    # 解析打包路径（在父目录中打包，避免绝对路径前缀）
    local abs_dir parent_dir tool_base
    abs_dir="$(cd "${tool_dir}" && pwd)"
    tool_base="$(basename "${abs_dir}")"
    parent_dir="$(dirname "${abs_dir}")"

    if [[ ! -d "${parent_dir}" ]]; then
        _echo_red "[ERROR] 父目录不存在: ${parent_dir}"
        exit 1
    fi

    local prefix="${PARTS_DIR}/${tool_name}.tar.gz.part_"
    _echo_blue "[INFO] 开始打包: ${tool_dir}"
    _echo_blue "[INFO] 工具名: ${tool_name}"
    _echo_blue "[INFO] 分片前缀: ${prefix}"
    _echo_blue "[INFO] 分片大小: ${SHARD_SIZE}"

    # tar | gzip | split 管道（pipefail 捕获任一失败，R03 禁止 || true）
    if ! (cd "${parent_dir}" && tar cf - "${tool_base}" | gzip | split -b "${SHARD_SIZE}" - "${prefix}"); then
        _echo_red "[ERROR] tar/gzip/split 管道失败"
        exit 1
    fi

    # 收集分片文件（nullglob 避免 glob 不匹配时传字面字符串）
    local shard_files=()
    shopt -s nullglob
    shard_files=("${prefix}"*)
    shopt -u nullglob

    if [[ ${#shard_files[@]} -eq 0 ]]; then
        _echo_red "[ERROR] 打包后未生成分片文件"
        exit 1
    fi

    # 按字典序排序（确保分片顺序稳定）
    mapfile -t shard_files < <(printf '%s\n' "${shard_files[@]}" | sort)

    # 计算总大小
    local total_size=0 sz
    local f
    for f in "${shard_files[@]}"; do
        sz=$(stat -c '%s' "${f}")
        total_size=$((total_size + sz))
    done

    # 生成 ISO8601 时间戳（UTC）
    local created
    created=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    _echo_green "[OK] 打包完成: ${tool_name}"
    _echo_blue "[INFO] 分片数: ${#shard_files[@]}"
    _echo_blue "[INFO] 总大小: ${total_size} bytes"

    # 提取分片基名
    local shard_basenames=()
    for f in "${shard_files[@]}"; do
        shard_basenames+=("$(basename "${f}")")
    done

    # 更新 manifest.json（追加，不重写）
    _update_manifest "${tool_name}" "${total_size}" "${created}" "${shard_basenames[@]}"

    # git add 精确文件（R08）
    _git_add_shards "${tool_name}"
}

# ===== 更新 manifest.json（追加条目，禁止整体重写） =====
_update_manifest() {
    local tool_name="$1"
    local size="$2"
    local created="$3"
    shift 3
    local shards=("$@")

    _echo_blue "[INFO] 更新 manifest.json: ${MANIFEST}"

    if ! python3 - "${MANIFEST}" "${tool_name}" "${size}" "${created}" "${shards[@]}" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
name = sys.argv[2]
size = int(sys.argv[3])
created = sys.argv[4]
shards = list(sys.argv[5:])

if os.path.exists(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERROR] manifest.json 解析失败: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print("[ERROR] manifest.json 顶层不是 JSON 对象", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data.get("packages", []), list):
        print("[ERROR] manifest.json 'packages' 不是数组", file=sys.stderr)
        sys.exit(1)
else:
    data = {"packages": []}

# 二次检查重名（防并发）
for p in data["packages"]:
    if p.get("name") == name:
        print(f"[ERROR] manifest.json 已存在同名条目: {name}", file=sys.stderr)
        sys.exit(1)

entry = {
    "name": name,
    "shards": shards,
    "size": size,
    "created": created,
}
data["packages"].append(entry)

try:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
except OSError as e:
    print(f"[ERROR] manifest.json 写入失败: {e}", file=sys.stderr)
    sys.exit(1)
print("[INFO] manifest.json 已追加条目: " + name)
PYEOF
then
        _echo_red "[ERROR] manifest.json 更新失败（python 退出非 0）"
        exit 1
    fi
    _echo_green "[OK] manifest.json 已更新"
}

# ===== git add 精确文件（R08：禁止 git add -A / git add .） =====
_git_add_shards() {
    local tool_name="$1"

    # 检查是否在 git 仓库内
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        _echo_yellow "[WARN] 当前不在 git 工作树内，跳过 git add（打包结果已保留在 ${PARTS_DIR}）"
        return 0
    fi

    # 精确添加分片文件
    local added=0
    local f
    for f in "${PARTS_DIR}/${tool_name}".tar.gz.part_*; do
        if [[ -f "${f}" ]]; then
            git add "${f}"
            added=$((added + 1))
        fi
    done

    if [[ ${added} -eq 0 ]]; then
        _echo_red "[ERROR] 未找到分片文件，git add 失败"
        exit 1
    fi

    # 精确添加 manifest.json
    if [[ -f "${MANIFEST}" ]]; then
        git add "${MANIFEST}"
    else
        _echo_red "[ERROR] manifest.json 不存在，无法 git add"
        exit 1
    fi

    _echo_green "[OK] git add 完成: ${added} 个分片 + manifest.json"
    _echo_yellow "[HINT]  请手动 commit: git commit -m \"feat(3dtool): 增量打包 ${tool_name}\""
}

# ===== 主入口 =====
main() {
    local cmd="${1:-}"
    case "${cmd}" in
        --help|-h)
            _show_help
            exit 0
            ;;
        --list)
            list_packages
            ;;
        "")
            _echo_red "[ERROR] 缺少参数"
            _show_help
            exit 1
            ;;
        --*)
            _echo_red "[ERROR] 未知选项: ${cmd}"
            _show_help
            exit 1
            ;;
        *)
            package_tool "$@"
            ;;
    esac
}

main "$@"
