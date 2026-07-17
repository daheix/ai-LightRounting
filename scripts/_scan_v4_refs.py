"""扫描功能清单与实现/ 44 文件中的 v4 路径引用，自动匹配 v5.0 模块位置。

输出：每个 v4 引用 → v5.0 候选（唯一/多选/无匹配），供映射表审查。
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace")
DOCS = ROOT / "2026-2028开发计划" / "功能清单与实现"
MODULES = ROOT / "modules"

# 建立 v5.0 文件索引: basename -> [相对路径列表]
v5_index: dict[str, list[str]] = defaultdict(list)
for py in MODULES.glob("*/src/polaris_*/*.py"):
    v5_index[py.name].append(str(py.relative_to(ROOT)))
# 二级子目录（如 polaris_nn/data/*.py）
for py in MODULES.glob("*/src/polaris_*/*/*.py"):
    v5_index[py.name].append(str(py.relative_to(ROOT)))

# 扫描所有 v4 引用
pat = re.compile(r"src/polaris/([a-zA-Z0-9_/]+\.py)")
refs: dict[str, set[str]] = defaultdict(set)  # v4路径 -> 出现的文件集合
for md in sorted(DOCS.glob("*.md")):
    text = md.read_text(encoding="utf-8")
    for m in pat.finditer(text):
        refs[f"src/polaris/{m.group(1)}"].add(md.name)

print(f"v4 .py 引用总数（去重）: {len(refs)}")
print()

unique_map: dict[str, str] = {}
multi: dict[str, list[str]] = {}
none_list: list[str] = []

for v4 in sorted(refs):
    base = v4.split("/")[-1]
    cands = v5_index.get(base, [])
    if len(cands) == 1:
        unique_map[v4] = cands[0]
    elif len(cands) > 1:
        multi[v4] = cands
    else:
        none_list.append(v4)

print(f"=== 唯一匹配 ({len(unique_map)}) ===")
for v4, v5 in sorted(unique_map.items()):
    print(f"  {v4}  ->  {v5}")

print(f"\n=== 多候选 ({len(multi)}) ===")
for v4, cands in sorted(multi.items()):
    print(f"  {v4}:")
    for c in cands:
        print(f"      {c}")

print(f"\n=== 无匹配 ({len(none_list)}) ===")
for v4 in none_list:
    print(f"  {v4}   [出现于: {', '.join(sorted(refs[v4]))[:80]}]")
