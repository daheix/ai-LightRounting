#!/usr/bin/env python3
"""代码质量门禁脚本（规则 4 强制执行）。

按照 project_rules.md 规则 4 的工业标准，检查代码文件的：
1. 文件大小（KB）与有效代码行数（SLOC）
2. 每个函数的有效代码行数
3. 每个函数的圈复杂度（McCabe，基于 AST 决策节点计数）
4. 函数参数个数
5. 类方法数
6. 嵌套深度

**0 警告 0 错误**才允许提交。任一违规（含警告）即返回非零退出码。

来源:
- Google Python Style Guide 函数长度: https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules.html#id17
- McCabe 圈复杂度: McCabe, "A Complexity Measure", IEEE TSE 1976, https://ieeexplore.ieee.org/document/1702388
- PEP 8 风格指南: https://peps.python.org/pep-0008/

用法:
    python scripts/code_quality_gate.py                 # 检查 src/polaris/
    python scripts/code_quality_gate.py src/polaris/     # 检查指定目录
    python scripts/code_quality_gate.py --json           # 输出 JSON 报告
    python scripts/code_quality_gate.py --staged         # 仅检查 git 暂存文件
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# =============================================================================
# 阈值定义（规则 4.1）
# =============================================================================

# 硬性上限（超过即门禁失败）
HARD_MAX_FILE_SIZE_KB = 120
HARD_MAX_FILE_SLOC = 800
HARD_MAX_FUNC_SLOC = 80
HARD_MAX_FUNC_COMPLEXITY = 15
HARD_MAX_FUNC_ARGS = 7
HARD_MAX_CLASS_METHODS = 30
HARD_MAX_NESTING = 5

# 警告阈值（超过即输出警告，同样阻断提交）
WARN_FILE_SIZE_KB = 80
WARN_FILE_SLOC = 500
WARN_FUNC_SLOC = 40
WARN_FUNC_COMPLEXITY = 10
WARN_FUNC_ARGS = 5
WARN_CLASS_METHODS = 20
WARN_NESTING = 4

# 跳过的目录名
_SKIP_DIRS = (
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
)


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
# 违规生成辅助函数
# =============================================================================


@dataclass
class MetricCheck:
    """单次指标检查的上下文。"""

    violations: list[Violation]
    filepath: str
    line: int
    name: str

    def check(self, metric: str, value: float) -> None:
        """检查指标值是否超阈值，超阈值则添加违规记录。"""
        limits = {
            "file_size_kb": (WARN_FILE_SIZE_KB, HARD_MAX_FILE_SIZE_KB),
            "file_sloc": (WARN_FILE_SLOC, HARD_MAX_FILE_SLOC),
            "func_sloc": (WARN_FUNC_SLOC, HARD_MAX_FUNC_SLOC),
            "cyclomatic_complexity": (WARN_FUNC_COMPLEXITY, HARD_MAX_FUNC_COMPLEXITY),
            "func_args": (WARN_FUNC_ARGS, HARD_MAX_FUNC_ARGS),
            "class_methods": (WARN_CLASS_METHODS, HARD_MAX_CLASS_METHODS),
            "nesting_depth": (WARN_NESTING, HARD_MAX_NESTING),
        }
        warn_limit, hard_limit = limits.get(metric, (0, 0))
        if value > hard_limit:
            self.violations.append(
                Violation(self.filepath, self.line, self.name, metric, value, hard_limit, "error")
            )
        elif value > warn_limit:
            self.violations.append(
                Violation(self.filepath, self.line, self.name, metric, value, warn_limit, "warning")
            )


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

    def analyze(self, tree: ast.AST) -> list[Violation]:
        """分析 AST 树，返回违规列表。"""
        self.violations = []
        self.visit(tree)
        return self.violations

    def _count_sloc(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """计算函数的有效代码行数（去除空行和纯注释行）。"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        sloc = 0
        for i in range(start_line - 1, min(end_line, len(self.source_lines))):
            line = self.source_lines[i].strip()
            if not line or line.startswith("#"):
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
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                complexity += 1
        return complexity

    def _calc_max_nesting(self, node: ast.AST, depth: int = 0) -> int:
        """计算最大嵌套深度。"""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            is_nested = isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try))
            child_depth = self._calc_max_nesting(child, depth + (1 if is_nested else 0))
            if child_depth > max_depth:
                max_depth = child_depth
        return max_depth

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str | None = None,
    ) -> None:
        """检查单个函数/方法的各项指标。"""
        full_name = f"{class_name}.{node.name}" if class_name else node.name
        mc = MetricCheck(self.violations, self.filepath, node.lineno, full_name)

        # 1. 有效代码行数
        mc.check("func_sloc", self._count_sloc(node))
        # 2. 圈复杂度
        mc.check("cyclomatic_complexity", self._calc_complexity(node))
        # 3. 参数个数
        n_args = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg:
            n_args += 1
        if node.args.kwarg:
            n_args += 1
        mc.check("func_args", n_args)
        # 4. 嵌套深度
        mc.check("nesting_depth", self._calc_max_nesting(node))

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
        MetricCheck(self.violations, self.filepath, node.lineno, node.name).check(
            "class_methods", len(methods)
        )
        for method in methods:
            self._check_function(method, class_name=node.name)
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
        if not stripped or stripped.startswith("#"):
            continue
        sloc += 1
    return sloc


def _check_file_size(report: FileReport, filepath: Path) -> None:
    """检查文件大小和有效代码行数。"""
    report.size_kb = filepath.stat().st_size / 1024.0
    mc = MetricCheck(report.violations, str(filepath), 0, filepath.name)
    mc.check("file_size_kb", report.size_kb)
    report.sloc = count_sloc(filepath.read_text(encoding="utf-8"))
    mc.check("file_sloc", report.sloc)


def check_file(filepath: Path) -> FileReport:
    """检查单个 Python 文件。"""
    report = FileReport(path=str(filepath), size_kb=0, sloc=0, violations=[])

    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        report.violations.append(Violation(str(filepath), 0, "<file>", "read_error", 0, 0, "error"))
        return report

    _check_file_size(report, filepath)

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        report.violations.append(
            Violation(str(filepath), e.lineno or 0, "<syntax>", "syntax_error", 0, 0, "error")
        )
        return report

    analyzer = CodeAnalyzer(str(filepath), source.splitlines())
    analyzer.analyze(tree)
    report.violations.extend(analyzer.violations)
    return report


def _is_test_file(path: Path) -> bool:
    """判断是否为测试文件（tests/ 目录下或 test_*.py 文件）。"""
    if "tests" in path.parts:
        return True
    return path.name.startswith("test_") or path.name.startswith("conftest")


def _should_skip_dir(root: str) -> bool:
    """判断目录是否应跳过。"""
    return any(skip in root for skip in _SKIP_DIRS)


def _collect_py_files_from_dir(path: Path, exclude_tests: bool, files: list[Path]) -> None:
    """从目录收集 Python 文件。"""
    for root, _dirs, filenames in os.walk(path):
        if _should_skip_dir(root):
            continue
        if exclude_tests and "tests" in Path(root).parts:
            continue
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = Path(root) / filename
            if exclude_tests and _is_test_file(filepath):
                continue
            files.append(filepath)


def find_python_files(paths: list[str], exclude_tests: bool = False) -> list[Path]:
    """查找指定路径下的所有 Python 文件。

    Args:
        paths: 要搜索的路径列表。
        exclude_tests: 是否排除测试文件（tests/ 目录和 test_*.py 文件）。
    """
    files: list[Path] = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            if not (exclude_tests and _is_test_file(path)):
                files.append(path)
        elif path.is_dir():
            _collect_py_files_from_dir(path, exclude_tests, files)
    return sorted(set(files))


def get_staged_python_files() -> list[Path]:
    """获取 git 暂存区中的 Python 文件列表（增量检查）。

    通过 `git diff --cached --name-only --diff-filter=ACM` 获取
    已暂存（staged）的新增/修改文件。
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files: list[Path] = []
    for line in result.stdout.strip().splitlines():
        path = Path(line)
        if path.suffix == ".py" and path.exists():
            files.append(path)
    return sorted(files)


# =============================================================================
# 报告输出
# =============================================================================

_METRIC_NAMES = {
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


def format_violation(v: Violation) -> str:
    """格式化单条违规为可读字符串。"""
    severity_icon = "ERROR" if v.severity == "error" else "WARN "
    metric_name = _METRIC_NAMES.get(v.metric, v.metric)
    return (
        f"  [{severity_icon}] {v.file}:{v.line} {v.name} | {metric_name}={v.value} (上限={v.limit})"
    )


def print_report(report: GateReport) -> int:
    """打印报告，返回违规总数（错误+警告）。"""
    print("=" * 70)
    print("PoLaRIS 代码质量门禁报告 (规则 4) — 0 警告 0 错误才通过")
    print("=" * 70)
    print(f"检查文件数: {report.files_checked}")
    print(f"总违规数:   {report.total_violations}")
    print(f"  错误:     {report.errors}")
    print(f"  警告:     {report.warnings}")
    print("-" * 70)

    for file_report in report.file_reports:
        if not file_report.violations:
            continue
        print(f"\n📄 {file_report.path}")
        print(f"   大小: {file_report.size_kb:.1f} KB | 有效行数: {file_report.sloc}")
        for v in file_report.violations:
            print(format_violation(v))

    print("\n" + "=" * 70)
    total = report.errors + report.warnings
    if total > 0:
        print(f"门禁失败: {report.errors} 个错误 + {report.warnings} 个警告")
        print("请按规则 4.2 流程重构拆分超标的文件/函数")
    else:
        print("门禁通过: 0 警告 0 错误")
    print("=" * 70)

    return total


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


def _build_report(files: list[Path]) -> GateReport:
    """构建门禁报告。"""
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
    return report


def main() -> int:
    """主入口，返回退出码（0=通过，1=有违规）。"""
    parser = argparse.ArgumentParser(description="PoLaRIS 代码质量门禁（规则 4 强制执行）")
    parser.add_argument(
        "paths", nargs="*", default=["src/polaris/"], help="要检查的目录或文件（默认 src/polaris/）"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式报告")
    parser.add_argument("--staged", action="store_true", help="增量模式：仅检查 git 暂存区文件")
    parser.add_argument(
        "--exclude-tests", action="store_true", default=True, help="排除测试文件，默认开启"
    )
    parser.add_argument("--include-tests", action="store_true", help="包含测试文件（覆盖默认排除）")
    args = parser.parse_args()

    if args.staged:
        files = get_staged_python_files()
        if not files:
            print("暂存区无 Python 文件，跳过质量门禁")
            return 0
        print(f"增量检查模式：检查 {len(files)} 个暂存文件")
    else:
        exclude_tests = args.exclude_tests and not args.include_tests
        files = find_python_files(args.paths, exclude_tests=exclude_tests)

    if not files:
        print("未找到 Python 文件")
        return 0

    report = _build_report(files)

    if args.json:
        print_json_report(report)
        return 1 if (report.errors + report.warnings) > 0 else 0

    total = print_report(report)
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
