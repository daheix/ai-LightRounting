#!/usr/bin/env python3
"""代码质量门禁脚本（规则 4 强制执行）。

按照 project_rules.md 规则 4 的工业标准，检查代码文件的：
1. 文件大小（KB）与有效代码行数（SLOC）
2. 每个函数的有效代码行数
3. 每个函数的圈复杂度（McCabe，基于 AST 决策节点计数）
4. 函数参数个数
5. 类方法数
6. 嵌套深度

任一硬性上限超标即返回非零退出码（CI 门禁失败）。

来源:
- Google Python Style Guide 函数长度: https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules.html#id17
- McCabe 圈复杂度: McCabe, "A Complexity Measure", IEEE TSE 1976, https://ieeexplore.ieee.org/document/1702388
- PEP 8 风格指南: https://peps.python.org/pep-0008/

用法:
    python scripts/code_quality_gate.py                 # 检查 polaris/ + tests/
    python scripts/code_quality_gate.py polaris/         # 检查指定目录
    python scripts/code_quality_gate.py --json           # 输出 JSON 报告
    python scripts/code_quality_gate.py --warnings       # 显示警告但不失败
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# =============================================================================
# 阈值定义（规则 4.1）
# =============================================================================

# 硬性上限（超过即门禁失败）
HARD_MAX_FILE_SIZE_KB = 120
HARD_MAX_FILE_SLOC = 2000
HARD_MAX_FUNC_SLOC = 80
HARD_MAX_FUNC_COMPLEXITY = 15
HARD_MAX_FUNC_ARGS = 7
HARD_MAX_CLASS_METHODS = 30
HARD_MAX_NESTING = 5

# 警告阈值（超过即输出警告，但不阻断）
WARN_FILE_SIZE_KB = 80
WARN_FILE_SLOC = 800
WARN_FUNC_SLOC = 40
WARN_FUNC_COMPLEXITY = 10
WARN_FUNC_ARGS = 5
WARN_CLASS_METHODS = 20
WARN_NESTING = 4


# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class Violation:
    """单条违规记录。"""

    file: str
    line: int
    name: str
    metric: str
    value: float
    limit: float
    severity: str  # "error" 或 "warning"


@dataclass
class FileReport:
    """单个文件的检查报告。"""

    path: str
    size_kb: float
    sloc: int
    violations: list[Violation] = field(default_factory=list)


@dataclass
class GateReport:
    """整体门禁报告。"""

    files_checked: int
    total_violations: int
    errors: int
    warnings: int
    file_reports: list[FileReport] = field(default_factory=list)


# =============================================================================
# AST 分析器
# =============================================================================


class CodeAnalyzer(ast.NodeVisitor):
    """基于 AST 的代码分析器。

    分析每个函数/方法的：
    - 有效代码行数（SLOC）
    - 圈复杂度（决策节点数 + 1）
    - 参数个数
    - 嵌套深度
    """

    # 增加圈复杂度的 AST 节点类型（决策点）
    DECISION_NODES = (
        ast.If,
        ast.For,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.Assert,
        ast.comprehension,
    )

    def __init__(self, filepath: str, source_lines: list[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.violations: list[Violation] = []
        self.class_methods: dict[str, int] = {}

    def analyze(self, tree: ast.AST) -> list[Violation]:
        """分析 AST 树，返回违规列表。"""
        self.violations = []
        self.class_methods = {}
        self.visit(tree)
        return self.violations

    def _count_sloc(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """计算函数的有效代码行数（去除空行和纯注释行）。"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        sloc = 0
        for i in range(start_line - 1, min(end_line, len(self.source_lines))):
            line = self.source_lines[i].strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            sloc += 1
        return sloc

    def _calc_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度（决策节点数 + 1）。

        来源: McCabe 1976, M = 判定节点数 + 1
        """
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, self.DECISION_NODES):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or 每个额外操作数增加一条路径
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                # 三元表达式 x if cond else y
                complexity += 1
        return complexity

    def _calc_max_nesting(self, node: ast.AST, depth: int = 0) -> int:
        """计算最大嵌套深度。"""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calc_max_nesting(child, depth + 1)
                if child_depth > max_depth:
                    max_depth = child_depth
            else:
                child_depth = self._calc_max_nesting(child, depth)
                if child_depth > max_depth:
                    max_depth = child_depth
        return max_depth

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str | None = None,
    ) -> None:
        """检查单个函数/方法的各项指标。"""
        func_name = node.name
        full_name = f"{class_name}.{func_name}" if class_name else func_name

        # 1. 有效代码行数
        sloc = self._count_sloc(node)
        if sloc > HARD_MAX_FUNC_SLOC:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="func_sloc",
                    value=sloc,
                    limit=HARD_MAX_FUNC_SLOC,
                    severity="error",
                )
            )
        elif sloc > WARN_FUNC_SLOC:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="func_sloc",
                    value=sloc,
                    limit=WARN_FUNC_SLOC,
                    severity="warning",
                )
            )

        # 2. 圈复杂度
        complexity = self._calc_complexity(node)
        if complexity > HARD_MAX_FUNC_COMPLEXITY:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="cyclomatic_complexity",
                    value=complexity,
                    limit=HARD_MAX_FUNC_COMPLEXITY,
                    severity="error",
                )
            )
        elif complexity > WARN_FUNC_COMPLEXITY:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="cyclomatic_complexity",
                    value=complexity,
                    limit=WARN_FUNC_COMPLEXITY,
                    severity="warning",
                )
            )

        # 3. 参数个数
        n_args = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg:
            n_args += 1
        if node.args.kwarg:
            n_args += 1
        if n_args > HARD_MAX_FUNC_ARGS:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="func_args",
                    value=n_args,
                    limit=HARD_MAX_FUNC_ARGS,
                    severity="error",
                )
            )
        elif n_args > WARN_FUNC_ARGS:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="func_args",
                    value=n_args,
                    limit=WARN_FUNC_ARGS,
                    severity="warning",
                )
            )

        # 4. 嵌套深度
        max_nesting = self._calc_max_nesting(node)
        if max_nesting > HARD_MAX_NESTING:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="nesting_depth",
                    value=max_nesting,
                    limit=HARD_MAX_NESTING,
                    severity="error",
                )
            )
        elif max_nesting > WARN_NESTING:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=full_name,
                    metric="nesting_depth",
                    value=max_nesting,
                    limit=WARN_NESTING,
                    severity="warning",
                )
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """访问函数定义。"""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """访问异步函数定义。"""
        self._check_function(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """访问类定义，检查方法数。"""
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        n_methods = len(methods)
        if n_methods > HARD_MAX_CLASS_METHODS:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=node.name,
                    metric="class_methods",
                    value=n_methods,
                    limit=HARD_MAX_CLASS_METHODS,
                    severity="error",
                )
            )
        elif n_methods > WARN_CLASS_METHODS:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=node.lineno,
                    name=node.name,
                    metric="class_methods",
                    value=n_methods,
                    limit=WARN_CLASS_METHODS,
                    severity="warning",
                )
            )

        # 检查每个方法
        for method in methods:
            self._check_function(method, class_name=node.name)

        # 继续访问类体内的其他节点（不重复访问方法）
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child)


# =============================================================================
# 文件检查
# =============================================================================


def count_sloc(source: str) -> int:
    """计算文件的有效代码行数（去除空行和纯注释行）。"""
    sloc = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        sloc += 1
    return sloc


def check_file(filepath: Path) -> FileReport:
    """检查单个 Python 文件。"""
    report = FileReport(
        path=str(filepath),
        size_kb=0,
        sloc=0,
        violations=[],
    )

    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=0,
                name="<file>",
                metric="read_error",
                value=0,
                limit=0,
                severity="error",
            )
        )
        return report

    # 文件大小
    file_size = filepath.stat().st_size
    report.size_kb = file_size / 1024.0
    if report.size_kb > HARD_MAX_FILE_SIZE_KB:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=0,
                name=filepath.name,
                metric="file_size_kb",
                value=round(report.size_kb, 1),
                limit=HARD_MAX_FILE_SIZE_KB,
                severity="error",
            )
        )
    elif report.size_kb > WARN_FILE_SIZE_KB:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=0,
                name=filepath.name,
                metric="file_size_kb",
                value=round(report.size_kb, 1),
                limit=WARN_FILE_SIZE_KB,
                severity="warning",
            )
        )

    # 有效代码行数
    report.sloc = count_sloc(source)
    if report.sloc > HARD_MAX_FILE_SLOC:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=0,
                name=filepath.name,
                metric="file_sloc",
                value=report.sloc,
                limit=HARD_MAX_FILE_SLOC,
                severity="error",
            )
        )
    elif report.sloc > WARN_FILE_SLOC:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=0,
                name=filepath.name,
                metric="file_sloc",
                value=report.sloc,
                limit=WARN_FILE_SLOC,
                severity="warning",
            )
        )

    # AST 分析
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        report.violations.append(
            Violation(
                file=str(filepath),
                line=e.lineno or 0,
                name="<syntax>",
                metric="syntax_error",
                value=0,
                limit=0,
                severity="error",
            )
        )
        return report

    source_lines = source.splitlines()
    analyzer = CodeAnalyzer(str(filepath), source_lines)
    analyzer.analyze(tree)
    report.violations.extend(analyzer.violations)

    return report


def find_python_files(paths: list[str]) -> list[Path]:
    """查找指定路径下的所有 Python 文件。"""
    files: list[Path] = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            for root, _dirs, filenames in os.walk(path):
                # 跳过 __pycache__、.git、venv 等
                if any(
                    skip in root
                    for skip in (
                        "__pycache__",
                        ".git",
                        "venv",
                        ".venv",
                        "node_modules",
                        ".mypy_cache",
                        ".ruff_cache",
                        ".pytest_cache",
                    )
                ):
                    continue
                for filename in filenames:
                    if filename.endswith(".py"):
                        files.append(Path(root) / filename)
    return sorted(set(files))


# =============================================================================
# 报告输出
# =============================================================================


def format_violation(v: Violation) -> str:
    """格式化单条违规为可读字符串。"""
    severity_icon = "ERROR" if v.severity == "error" else "WARN "
    metric_names = {
        "file_size_kb": "文件大小",
        "file_sloc": "文件有效行数",
        "func_sloc": "函数有效行数",
        "cyclomatic_complexity": "圈复杂度",
        "func_args": "参数个数",
        "class_methods": "类方法数",
        "nesting_depth": "嵌套深度",
        "syntax_error": "语法错误",
        "read_error": "读取错误",
    }
    metric_name = metric_names.get(v.metric, v.metric)
    return (
        f"  [{severity_icon}] {v.file}:{v.line} {v.name} | {metric_name}={v.value} (上限={v.limit})"
    )


def print_report(report: GateReport, show_warnings: bool) -> int:
    """打印报告，返回错误数。"""
    print("=" * 70)
    print("PoLaRIS 代码质量门禁报告 (规则 4)")
    print("=" * 70)
    print(f"检查文件数: {report.files_checked}")
    print(f"总违规数:   {report.total_violations}")
    print(f"  错误:     {report.errors}")
    print(f"  警告:     {report.warnings}")
    print("-" * 70)

    for file_report in report.file_reports:
        if not file_report.violations:
            continue
        errors = [v for v in file_report.violations if v.severity == "error"]
        if not show_warnings and not errors:
            continue
        print(f"\n📄 {file_report.path}")
        print(f"   大小: {file_report.size_kb:.1f} KB | 有效行数: {file_report.sloc}")
        for v in file_report.violations:
            if v.severity == "error" or show_warnings:
                print(format_violation(v))

    print("\n" + "=" * 70)
    if report.errors > 0:
        print(f"门禁失败: {report.errors} 个硬性违规需重构修复")
        print("请按规则 4.2 流程重构拆分超标的文件/函数")
    else:
        print("门禁通过: 无硬性违规")
        if report.warnings > 0:
            print(f"  (有 {report.warnings} 个警告，建议优化)")
    print("=" * 70)

    return report.errors


def print_json_report(report: GateReport) -> None:
    """输出 JSON 格式报告。"""
    data = {
        "files_checked": report.files_checked,
        "total_violations": report.total_violations,
        "errors": report.errors,
        "warnings": report.warnings,
        "files": [
            {
                "path": fr.path,
                "size_kb": round(fr.size_kb, 1),
                "sloc": fr.sloc,
                "violations": [asdict(v) for v in fr.violations],
            }
            for fr in report.file_reports
        ],
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


# =============================================================================
# 主入口
# =============================================================================


def main() -> int:
    """主入口，返回退出码（0=通过，1=有硬性违规）。"""
    parser = argparse.ArgumentParser(description="PoLaRIS 代码质量门禁（规则 4 强制执行）")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["polaris/", "tests/"],
        help="要检查的目录或文件（默认 polaris/ tests/）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式报告",
    )
    parser.add_argument(
        "--warnings",
        action="store_true",
        help="显示警告详情",
    )
    args = parser.parse_args()

    files = find_python_files(args.paths)
    if not files:
        print("未找到 Python 文件")
        return 0

    report = GateReport(files_checked=len(files), total_violations=0, errors=0, warnings=0)

    for filepath in files:
        file_report = check_file(filepath)
        report.file_reports.append(file_report)
        for v in file_report.violations:
            report.total_violations += 1
            if v.severity == "error":
                report.errors += 1
            else:
                report.warnings += 1

    if args.json:
        print_json_report(report)
        return 1 if report.errors > 0 else 0

    n_errors = print_report(report, show_warnings=args.warnings)
    return 1 if n_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
