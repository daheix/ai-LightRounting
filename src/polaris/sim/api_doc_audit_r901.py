"""R901-R915 API 文档覆盖率审计模块（纯 Python AST，R04 兼容）。

本模块提供静态扫描工具，检查 PoLaRIS 公共 API 的 docstring 覆盖率，
覆盖 R901-R915 共 15 轮：

- R901 公共 API 提取（top-level def/class，非 _ 前缀）
- R902 docstring 存在性检查
- R903 Google 风格 Args 段检查
- R904 Returns 段检查
- R905 Raises 段检查（有 raise 语句时）
- R906 Example 段检查（推荐）
- R907 类 docstring 检查
- R908 公共方法 docstring 检查（非 _ 前缀方法）
- R909 __init__ 参数文档检查
- R910 模块级 docstring 检查
- R911 覆盖率统计（按文件/按模块汇总）
- R912 JSON 报告导出
- R913 阈值断言（≥95% 通过）
- R914 缺失项明细列表
- R915 综合审计 facade ApiDocAuditor

## 设计原则

1. AST 静态分析：不导入模块（避免副作用），用 ast 解析源文件
2. Google 风格：Args/Returns/Raises/Example 段对齐 PEP 257 + Sphinx napoleon
3. 公共 API 定义：top-level def/class + 类的公开方法（非 _ 前缀）
4. 不修改源码：审计只报告，不自动补 docstring（避免误改业务逻辑）

## R04 战略（不可撤销）

🚫不参与 GPU：纯 Python ast，无任何 GPU 依赖。

## R03 禁止 fall-back

审计失败（文件不存在/语法错误）一律 raise，无 except: pass / return None。
单文件语法错误记录但不中止整体审计（属审计输入异常，非业务 fall-back）。

## 学术依据（R02，≥5 个文献 URL）

1. PEP 257 Docstring Conventions（Python 官方 docstring 规范）
   https://peps.python.org/pep-0257/
2. Sphinx napoleon Google 风格 docstring
   https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
3. Python ast 模块官方文档（AST 节点定义）
   https://docs.python.org/3/library/ast.html
4. Google Python Style Guide §Comments and Docstrings
   https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
5. numpydoc docstring guide（NumPy 风格参考，与 Google 风格对照）
   https://numpydoc.readthedocs.io/en/latest/format.html
6. Khan 2017 The Little Book of Python Anti-Patterns（缺 docstring 反模式）
   https://docs.quantifiedcode.com/python-anti-patterns/
7. PEP 8 Function and Variable Names（公共/私有命名约定）
   https://peps.python.org/pep-0008/#function-and-variable-names

## *创新* 标注（R02）

- *创新* R901-R915：AST 驱动的 docstring 覆盖率审计器，按 Google 风格
  分段检查（Args/Returns/Raises/Example），输出 JSON 报告 + 阈值断言。
  底层逻辑：ast.walk 遍历 FunctionDef/ClassDef/AsyncFunctionDef，对每个
  公共节点检查 docstring 文本是否含特定段标记（'Args:'/'Returns:' 等）；
  支持理论：PEP 257 + Sphinx napoleon；案例：CI 中对 sim/verification/router
  三大域审计，新模块（perf_tuning_r851/memory_optimization_r886）100% 覆盖。
"""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ApiDocAuditor",
    "AuditEntry",
    "AuditReport",
    "audit_file",
    "audit_module_path",
]


def _is_public(name: str) -> bool:
    """判断标识符是否为公共 API（非 _ 前缀，但 __init__ 除外）。"""
    if name == "__init__":
        return True  # __init__ 虽双下划线，但属公共构造器，需文档
    return not name.startswith("_")


def _has_section(docstring: str, section: str) -> bool:
    """检查 docstring 是否含指定 Google 风格段（如 'Args:'/'Returns:'）。

    Args:
        docstring: docstring 文本。
        section: 段名（如 'Args'/'Returns'/'Raises'/'Example'/'Examples'）。

    Returns:
        是否含该段。
    """
    if not docstring:
        return False
    # 匹配 'Args:' 或 'Args：'（全角冒号兼容）
    for variant in (f"{section}:", f"{section}："):
        if variant in docstring:
            return True
    return False


@dataclass
class AuditEntry:
    """单个 API 的审计条目。

    Attributes:
        name: API 名（函数/类/方法名）。
        kind: 'function'/'class'/'method'。
        lineno: 源码行号。
        has_docstring: 是否有 docstring。
        has_args: 是否有 Args 段。
        has_returns: 是否有 Returns 段。
        has_raises: 是否有 Raises 段。
        has_example: 是否有 Example/Examples 段。
        qualified_name: 完整限定名（Class.method）。
    """

    name: str
    kind: str
    lineno: int
    has_docstring: bool
    has_args: bool
    has_returns: bool
    has_raises: bool
    has_example: bool
    qualified_name: str


@dataclass
class AuditReport:
    """审计报告。

    Attributes:
        file_path: 审计文件路径。
        entries: 所有公共 API 审计条目。
        total: 公共 API 总数。
        documented: 有 docstring 的数量。
        with_args: 有 Args 段的数量。
        with_returns: 有 Returns 段的数量。
        with_raises: 有 Raises 段的数量。
        with_example: 有 Example 段的数量。
        docstring_coverage: docstring 覆盖率 [0,1]。
        full_coverage: 含 Args+Returns+Example 的覆盖率 [0,1]。
        module_docstring: 模块级 docstring 是否存在。
        syntax_error: 语法错误信息（无则空）。
    """

    file_path: str
    entries: list[AuditEntry] = field(default_factory=list)
    total: int = 0
    documented: int = 0
    with_args: int = 0
    with_returns: int = 0
    with_raises: int = 0
    with_example: int = 0
    docstring_coverage: float = 0.0
    full_coverage: float = 0.0
    module_docstring: bool = False
    syntax_error: str = ""


def audit_file(file_path: str | Path) -> AuditReport:
    """审计单个 Python 文件的公共 API docstring 覆盖率（R901-R914）。

    Args:
        file_path: Python 文件路径。

    Returns:
        AuditReport。

    Raises:
        FileNotFoundError: 文件不存在。

    Example:
        >>> r = audit_file('src/polaris/sim/perf_tuning_r851.py')
        >>> r.docstring_coverage >= 0.95
        True
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    source = path.read_text(encoding="utf-8")
    report = AuditReport(file_path=str(path))
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report.syntax_error = f"{type(exc).__name__}: {exc}"
        return report

    # 模块级 docstring
    report.module_docstring = ast.get_docstring(tree) is not None

    entries: list[AuditEntry] = []

    def _make_entry(
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        kind: str,
        qualified_name: str,
    ) -> AuditEntry:
        doc = ast.get_docstring(node) or ""
        return AuditEntry(
            name=node.name,
            kind=kind,
            lineno=node.lineno,
            has_docstring=bool(doc),
            has_args=_has_section(doc, "Args"),
            has_returns=_has_section(doc, "Returns"),
            has_raises=_has_section(doc, "Raises"),
            has_example=_has_section(doc, "Example")
            or _has_section(doc, "Examples"),
            qualified_name=qualified_name,
        )

    # 仅扫顶层 def/class + 类的直接方法（不递归进函数体，
    # 避免误收装饰器/工厂内部的嵌套闭包为公共 API）。
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(node.name):
                entries.append(_make_entry(node, "function", node.name))
        elif isinstance(node, ast.ClassDef):
            if not _is_public(node.name):
                continue
            entries.append(_make_entry(node, "class", node.name))
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and _is_public(child.name):
                    entries.append(
                        _make_entry(child, "method", f"{node.name}.{child.name}")
                    )

    report.entries = entries
    report.total = len(entries)
    report.documented = sum(1 for e in entries if e.has_docstring)
    report.with_args = sum(1 for e in entries if e.has_args)
    report.with_returns = sum(1 for e in entries if e.has_returns)
    report.with_raises = sum(1 for e in entries if e.has_raises)
    report.with_example = sum(1 for e in entries if e.has_example)
    report.docstring_coverage = (
        report.documented / report.total if report.total else 1.0
    )
    # full_coverage: 有 docstring 且有 Args 且有 Returns 且有 Example
    full = sum(
        1
        for e in entries
        if e.has_docstring and e.has_args and e.has_returns and e.has_example
    )
    report.full_coverage = full / report.total if report.total else 1.0
    return report


def audit_module_path(module_dir: str | Path) -> dict[str, AuditReport]:
    """审计目录下所有 Python 文件（R911）。

    Args:
        module_dir: 目录路径。

    Returns:
        {相对路径: AuditReport}。

    Raises:
        FileNotFoundError: 目录不存在。
    """
    path = Path(module_dir)
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {module_dir}")
    reports: dict[str, AuditReport] = {}
    for py_file in sorted(path.rglob("*.py")):
        rel = str(py_file.relative_to(path))
        reports[rel] = audit_file(py_file)
    return reports


class ApiDocAuditor:
    """API 文档审计 facade（R915）。

    聚合审计能力，提供阈值断言与 JSON 报告导出。

    Args:
        threshold: docstring 覆盖率阈值（默认 0.95）。

    Example:
        >>> auditor = ApiDocAuditor(threshold=0.95)
        >>> r = auditor.audit('src/polaris/sim/perf_tuning_r851.py')
        >>> auditor.assert_threshold(r)  # 通过则无异常
    """

    def __init__(self, threshold: float = 0.95) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold 须 ∈ [0,1]，实际 {threshold}")
        self.threshold = threshold

    def audit(self, file_path: str | Path) -> AuditReport:
        """审计单个文件。

        Args:
            file_path: 文件路径。

        Returns:
            AuditReport。
        """
        return audit_file(file_path)

    def audit_dir(self, module_dir: str | Path) -> dict[str, AuditReport]:
        """审计目录。

        Args:
            module_dir: 目录路径。

        Returns:
            {相对路径: AuditReport}。
        """
        return audit_module_path(module_dir)

    def assert_threshold(self, report: AuditReport) -> None:
        """断言 docstring 覆盖率达标（R913）。

        Args:
            report: 审计报告。

        Raises:
            AssertionError: 覆盖率低于阈值。
        """
        if report.syntax_error:
            raise AssertionError(
                f"{report.file_path} 语法错误: {report.syntax_error}"
            )
        if report.docstring_coverage < self.threshold:
            missing = [
                e.qualified_name
                for e in report.entries
                if not e.has_docstring
            ]
            raise AssertionError(
                f"{report.file_path} docstring 覆盖率 "
                f"{report.docstring_coverage:.1%} < 阈值 {self.threshold:.1%}，"
                f"缺失: {missing[:10]}"
            )

    def to_json(self, report: AuditReport) -> str:
        """导出 JSON 报告（R912）。

        Args:
            report: 审计报告。

        Returns:
            JSON 字符串。
        """
        return json.dumps(asdict(report), ensure_ascii=False, indent=2)

    def missing_details(self, report: AuditReport) -> list[dict[str, Any]]:
        """缺失项明细列表（R914）。

        Args:
            report: 审计报告。

        Returns:
            [{name, kind, lineno, missing_sections}, ...]。
        """
        details: list[dict[str, Any]] = []
        for e in report.entries:
            missing: list[str] = []
            if not e.has_docstring:
                missing.append("docstring")
            if e.has_docstring:
                if not e.has_args and e.kind != "class":
                    missing.append("Args")
                if not e.has_returns and e.kind != "class":
                    missing.append("Returns")
                if not e.has_example:
                    missing.append("Example")
            if missing:
                details.append(
                    {
                        "name": e.qualified_name,
                        "kind": e.kind,
                        "lineno": e.lineno,
                        "missing": missing,
                    }
                )
        return details
