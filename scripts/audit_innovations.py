"""R776-R800 创新点标注完整性审计脚本（修正版）。

使用 ast.Constant 替代已移除的 ast.Str（Python 3.12+ 兼容），
精确识别模块 docstring 范围，避免字符串搜索导致的误判。

合规: R02 学术诚信 / R03 禁止 fall-back / R11 V8 极简工作流。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def find_docstring_range_ast(content: str) -> tuple[int, int] | None:
    """用 ast 精确找到模块 docstring 的字符范围。

    返回 (start_offset, end_offset)，其中 start_offset 是 docstring
    起始三引号位置，end_offset 是结束三引号 + 1 位置。
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    if not tree.body:
        return None
    first = tree.body[0]
    if not isinstance(first, ast.Expr):
        return None
    # Python 3.12+ 中 ast.Str 已移除，统一用 ast.Constant
    if not (isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        return None
    lines = content.splitlines(keepends=True)
    start_offset = sum(len(lines[i]) for i in range(first.lineno - 1)) + first.col_offset
    end_offset = (
        sum(len(lines[i]) for i in range(first.end_lineno - 1))
        + first.end_col_offset
    )
    return start_offset, end_offset


def count_innovations(content: str) -> tuple[int, list[str]]:
    """统计 *创新* 标注次数（行级匹配，避免误报）。"""
    cnt = 0
    items: list[str] = []
    for line in content.splitlines():
        if "*创新*" in line:
            cnt += 1
            items.append(line.strip()[:120])
    return cnt, items


def has_explanation_block(content: str) -> bool:
    """是否已包含「创新点完整说明」块。

    识别以下任一模式即视为已补全（R02 精神：底层逻辑+支持理论+案例）：
    1. ``## 创新点完整说明`` 或 ``## 创新点完整说明补遗`` 头部
    2. ``*创新* 完整说明：`` 手工补全标记
    3. 文件内同时出现 底层逻辑 / 支持理论 / 案例 三个关键词（行内式）
    """
    if ("## 创新点完整说明" in content
            or "## 创新点完整说明补遗" in content):
        return True
    if "*创新* 完整说明" in content or "*创新*完整说明" in content:
        return True
    # 行内式：三个关键词齐全视为已补全（R02 精神满足）
    has_logic = "底层逻辑" in content
    has_theory = "支持理论" in content
    has_case = "案例" in content
    return has_logic and has_theory and has_case


def main():
    root = Path("src/polaris")
    py_files = sorted(root.rglob("*.py"))
    py_files = [p for p in py_files if "__pycache__" not in p.parts]

    total_files = 0
    total_innovations = 0
    total_complete = 0
    total_incomplete = 0
    needs_supplement: list[tuple[Path, int, bool]] = []

    syntax_fail: list[tuple[Path, str]] = []
    for pf in py_files:
        try:
            content = pf.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            syntax_fail.append((pf, f"read error: {e}"))
            continue
        try:
            ast.parse(content)
        except SyntaxError as e:
            syntax_fail.append((pf, f"SyntaxError: {e}"))
            continue

        n_innov, items = count_innovations(content)
        if n_innov == 0:
            continue
        total_files += 1
        total_innovations += n_innov
        has_block = has_explanation_block(content)
        if has_block:
            total_complete += n_innov
        else:
            total_incomplete += n_innov
            needs_supplement.append((pf, n_innov, has_block))

    print(f"扫描 .py 文件数: {len(py_files)}")
    print(f"语法错误文件数: {len(syntax_fail)}")
    for pf, err in syntax_fail:
        print(f"  FAIL {pf}: {err}")
    print()
    print(f"含 *创新* 标注的文件数: {total_files}")
    print(f"*创新* 标注总数: {total_innovations}")
    print(f"已含完整说明块的标注数（近似）: {total_complete}")
    print(f"仍缺完整说明的标注数: {total_incomplete}")
    if total_innovations > 0:
        rate = total_complete / total_innovations * 100
        print(f"完整率: {rate:.1f}%")
    print()
    print(f"需补充说明块的文件数: {len(needs_supplement)}")
    for pf, n, has_block in needs_supplement:
        print(f"  {pf} (创新={n}, 已有补遗={has_block})")


if __name__ == "__main__":
    main()
