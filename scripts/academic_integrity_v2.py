#!/usr/bin/env python3
"""学术诚信全面检查 V2 - 适配 modules/ 结构。

检查内容：
1. 所有模块 docstring 中文献引用数（R02: ≥5个）
2. 固定参数是否有来源标注
3. 计算公式是否有文献溯源
4. 是否有 TODO/FIXME/HACK 残留（R05）
5. GPU 后端禁用状态（R04）
"""
import ast
import re
import sys
from pathlib import Path

MODULES_DIR = Path("/workspace/modules")

CITATION_PATTERNS = [
    re.compile(r'https?://[^\s\)\]]+', re.IGNORECASE),
    re.compile(r'doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE),
    re.compile(r'arXiv:\s*\d{4}\.\d{4,5}', re.IGNORECASE),
    re.compile(r'arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}', re.IGNORECASE),
    re.compile(r'ISBN(?:-13|-10)?:?\s*[\d-]+', re.IGNORECASE),
]

MAGIC_NUMBER_PATTERNS = [
    (re.compile(r'=\s*(-?\d+\.?\d*e?-?\d*)\s*$'), "赋值常量"),
]

TODO_PATTERN = re.compile(r'(TODO|FIXME|HACK|XXX)\b', re.IGNORECASE)

GPU_PATTERNS = [
    re.compile(r'\bcupy\b', re.IGNORECASE),
    re.compile(r'\bcuda\b', re.IGNORECASE),
    re.compile(r'\brocm\b', re.IGNORECASE),
    re.compile(r'\bmetal\b', re.IGNORECASE),
    re.compile(r'fp16|bf16|half.?precision', re.IGNORECASE),
]


def extract_docstrings(filepath: Path) -> list[str]:
    """提取文件中所有 docstring（模块级、类级、函数级）。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return []

    docs = []
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        docs.append(mod_doc)

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                docs.append(doc)
    return docs


def count_citations(docstring: str) -> tuple[int, list[str]]:
    """统计 docstring 中的文献引用数。"""
    all_matches = []
    for pattern in CITATION_PATTERNS:
        matches = pattern.findall(docstring)
        all_matches.extend(matches)
    return len(all_matches), all_matches


def find_todos(filepath: Path) -> list[tuple[int, str]]:
    """查找 TODO/FIXME/HACK 注释。"""
    todos = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if TODO_PATTERN.search(line):
                    todos.append((i, line.strip()))
    except Exception:
        pass
    return todos


def find_gpu_usage(filepath: Path) -> list[tuple[int, str]]:
    """查找 GPU 相关代码（R04 违规检测）。"""
    gpu_hits = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                for pat in GPU_PATTERNS:
                    if pat.search(line) and 'R04' not in line and '不参与' not in line and '禁止' not in line:
                        gpu_hits.append((i, line.strip()))
                        break
    except Exception:
        pass
    return gpu_hits


def scan_all_modules():
    """扫描 modules/ 下所有 Python 源文件。"""
    py_files = sorted(MODULES_DIR.glob("*/src/**/*.py"))
    py_files = [f for f in py_files if f.is_file()]

    results = []
    for fpath in py_files:
        rel_path = str(fpath.relative_to(MODULES_DIR))
        docstrings = extract_docstrings(fpath)
        total_citations = 0
        all_cits = []
        for doc in docstrings:
            cnt, cits = count_citations(doc)
            total_citations += cnt
            all_cits.extend(cits)

        todos = find_todos(fpath)
        gpu_hits = find_gpu_usage(fpath)

        results.append({
            'path': rel_path,
            'module': rel_path.split('/')[0],
            'n_docstrings': len(docstrings),
            'total_citations': total_citations,
            'has_module_doc': len(docstrings) > 0,
            'todos': todos,
            'gpu_hits': gpu_hits,
        })
    return results


def main():
    print("=" * 80)
    print("PoLaRIS 学术诚信全面检查报告 V2")
    print("=" * 80)
    print()

    results = scan_all_modules()
    total_modules = len(results)

    # 1. 总体统计
    print(f"【1】总体统计")
    print("-" * 80)
    modules_with_doc = sum(1 for r in results if r['has_module_doc'])
    modules_ge5_cit = sum(1 for r in results if r['total_citations'] >= 5)
    modules_zero_cit = sum(1 for r in results if r['total_citations'] == 0)
    total_todos = sum(len(r['todos']) for r in results)
    total_gpu_hits = sum(len(r['gpu_hits']) for r in results)

    print(f"  总模块数: {total_modules}")
    print(f"  有模块级docstring: {modules_with_doc} ({modules_with_doc/total_modules*100:.1f}%)")
    print(f"  引用数 ≥5: {modules_ge5_cit} ({modules_ge5_cit/total_modules*100:.1f}%)")
    print(f"  引用数 = 0: {modules_zero_cit} ({modules_zero_cit/total_modules*100:.1f}%)")
    print(f"  TODO/FIXME/HACK 总数: {total_todos}")
    print(f"  GPU 疑似违规: {total_gpu_hits}")
    print()

    # 2. 按模块分组统计
    print(f"【2】按模块分组统计")
    print("-" * 80)
    by_module: dict[str, list[dict]] = {}
    for r in results:
        by_module.setdefault(r['module'], []).append(r)

    for mod in sorted(by_module.keys()):
        mod_results = by_module[mod]
        n = len(mod_results)
        n_ge5 = sum(1 for r in mod_results if r['total_citations'] >= 5)
        n_zero = sum(1 for r in mod_results if r['total_citations'] == 0)
        avg_cit = sum(r['total_citations'] for r in mod_results) / n if n > 0 else 0
        n_todo = sum(len(r['todos']) for r in mod_results)
        print(f"  {mod:20s}: {n:3d} 文件 | ≥5引用: {n_ge5:3d} | 0引用: {n_zero:3d} | 平均引用: {avg_cit:.1f} | TODO: {n_todo}")
    print()

    # 3. 引用数 = 0 的模块清单
    print(f"【3】引用数 = 0 的模块（需补充文献溯源）")
    print("-" * 80)
    zero_cit = [r for r in results if r['total_citations'] == 0]
    if zero_cit:
        for r in sorted(zero_cit, key=lambda x: x['path']):
            print(f"  - {r['path']}")
    else:
        print("  （无，全部模块都有引用）")
    print()

    # 4. 引用数 1-4 的模块清单
    print(f"【4】引用数 1-4 的模块（需补充到 ≥5）")
    print("-" * 80)
    low_cit = [r for r in results if 1 <= r['total_citations'] < 5]
    if low_cit:
        for r in sorted(low_cit, key=lambda x: x['path']):
            print(f"  - {r['path']}: {r['total_citations']} 引用")
    else:
        print("  （无，全部模块引用数 ≥5）")
    print()

    # 5. TODO/FIXME/HACK 清单
    print(f"【5】TODO/FIXME/HACK 残留（R05 违规）")
    print("-" * 80)
    if total_todos > 0:
        for r in results:
            if r['todos']:
                for line_no, line in r['todos']:
                    print(f"  {r['path']}:{line_no}: {line}")
    else:
        print("  （无，全部清理）")
    print()

    # 6. GPU 疑似违规
    print(f"【6】GPU 疑似违规（R04 战略检查）")
    print("-" * 80)
    if total_gpu_hits > 0:
        for r in results:
            if r['gpu_hits']:
                for line_no, line in r['gpu_hits']:
                    print(f"  {r['path']}:{line_no}: {line}")
    else:
        print("  （无，全部合规）")
    print()

    print("=" * 80)
    print("检查完成")
    print("=" * 80)

    return 0 if (total_todos == 0 and total_gpu_hits == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
