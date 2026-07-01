"""扫描 src/polaris/ 中所有 .py 文件的函数圈复杂度。

圈复杂度计数：函数起始 +1；if/elif/for/while/except/with/assert/and/or/条件表达式各 +1。
输出：复杂度 > 15 的函数列表（按复杂度降序）。
"""
import ast
import os
import sys


def cyclomatic_complexity(node: ast.AST) -> int:
    """计算 AST 节点的圈复杂度。"""
    cc = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.IfExp)):
            cc += 1
        elif isinstance(n, ast.For):
            cc += 1
        elif isinstance(n, (ast.While,)):
            cc += 1
        elif isinstance(n, ast.ExceptHandler):
            cc += 1
        elif isinstance(n, ast.With):
            cc += 1
        elif isinstance(n, ast.Assert):
            cc += 1
        elif isinstance(n, ast.BoolOp):
            cc += max(0, len(n.values) - 1)
        elif isinstance(n, ast.comprehension):
            cc += len(n.ifs)
    return cc


def scan_file(path: str):
    """扫描单文件，返回 [(name, lineno, cc, path), ...]。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = cyclomatic_complexity(node)
            results.append((node.name, node.lineno, cc, path))
    return results


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "src/polaris"
    all_results = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            all_results.extend(scan_file(p))
    high = [r for r in all_results if r[2] > 15]
    high.sort(key=lambda x: -x[2])
    print(f"TOTAL_FUNCS={len(all_results)} HIGH_CC_COUNT={len(high)}")
    for name, lineno, cc, path in high[:40]:
        print(f"{cc:4d}  {path}:{lineno}  {name}")


if __name__ == "__main__":
    main()
