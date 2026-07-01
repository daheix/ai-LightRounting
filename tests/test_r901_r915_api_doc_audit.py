"""R901-R915 API 文档覆盖率审计模块测试。

学术依据（R02，≥5 文献 URL）：
- PEP 257 Docstring Conventions https://peps.python.org/pep-0257/
- Sphinx napoleon Google 风格 https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
- Python ast 模块 https://docs.python.org/3/library/ast.html
- Google Python Style Guide https://google.github.io/styleguide/pyguide.html
- numpydoc docstring guide https://numpydoc.readthedocs.io/en/latest/format.html
- PEP 8 命名约定 https://peps.python.org/pep-0008/#function-and-variable-names
- Khan Python Anti-Patterns https://docs.quantifiedcode.com/python-anti-patterns/
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from polaris.sim.api_doc_audit_r901 import (
    ApiDocAuditor,
    AuditEntry,
    AuditReport,
    audit_file,
    audit_module_path,
)

SIM_DIR = Path(__file__).resolve().parents[1] / "src" / "polaris" / "sim"
PERF_TUNING = SIM_DIR / "perf_tuning_r851.py"
MEMORY_OPT = SIM_DIR / "memory_optimization_r886.py"


def test_audit_file_returns_report() -> None:
    """R901 audit_file 返回 AuditReport 且字段完整。"""
    report = audit_file(PERF_TUNING)
    assert isinstance(report, AuditReport)
    assert report.file_path.endswith("perf_tuning_r851.py")
    assert report.total > 0
    assert report.documented > 0
    assert 0.0 <= report.docstring_coverage <= 1.0
    assert 0.0 <= report.full_coverage <= 1.0
    assert isinstance(report.entries, list)
    assert all(isinstance(e, AuditEntry) for e in report.entries)


def test_audit_file_docstring_coverage_high_for_new_module() -> None:
    """R902-R906 新模块 perf_tuning_r851 docstring 覆盖率 ≥95%。"""
    report = audit_file(PERF_TUNING)
    assert report.docstring_coverage >= 0.95, (
        f"perf_tuning_r851 docstring 覆盖率 {report.docstring_coverage:.1%} < 95%"
    )


def test_audit_file_memory_optimization_high_coverage() -> None:
    """R902-R906 memory_optimization_r886 覆盖率 ≥95%。"""
    report = audit_file(MEMORY_OPT)
    assert report.docstring_coverage >= 0.95


def test_audit_file_nonexistent_raises() -> None:
    """R03 文件不存在 raise FileNotFoundError，无 fall-back。"""
    with pytest.raises(FileNotFoundError):
        audit_file("/nonexistent/path/xxx.py")


def test_audit_file_module_docstring_detected() -> None:
    """R910 模块级 docstring 检测。"""
    report = audit_file(PERF_TUNING)
    assert report.module_docstring is True


def test_audit_file_syntax_error_recorded(tmp_path) -> None:
    """R03 语法错误记录但不 raise（审计输入异常，非业务 fall-back）。"""
    bad = tmp_path / "bad.py"
    bad.write_text("def broken(:\n", encoding="utf-8")
    report = audit_file(bad)
    assert report.syntax_error != ""
    assert "SyntaxError" in report.syntax_error


def test_audit_file_detects_args_returns_sections(tmp_path) -> None:
    """R903-R904 Args/Returns 段检测。"""
    src = textwrap.dedent(
        '''
        def good_func(x):
            """有完整 docstring。

            Args:
                x: 输入。

            Returns:
                结果。

            Raises:
                ValueError: 非法。

            Example:
                >>> good_func(1)
                2
            """
            return x + 1


        def poor_func(y):
            """无段 docstring。"""
            return y
        '''
    )
    f = tmp_path / "sample.py"
    f.write_text(src, encoding="utf-8")
    report = audit_file(f)
    names = {e.name: e for e in report.entries}
    assert "good_func" in names
    assert names["good_func"].has_args is True
    assert names["good_func"].has_returns is True
    assert names["good_func"].has_raises is True
    assert names["good_func"].has_example is True
    assert names["poor_func"].has_args is False
    assert names["poor_func"].has_returns is False


def test_audit_file_class_methods_detected(tmp_path) -> None:
    """R907-R908 类与公开方法 docstring 检测。"""
    src = textwrap.dedent(
        '''
        class MyClass:
            """类 docstring。

            Args:
                a: 参数。
            """

            def public_method(self):
                """公开方法。

                Returns:
                    int。
                """
                return 1

            def _private_method(self):
                return 2
        '''
    )
    f = tmp_path / "cls.py"
    f.write_text(src, encoding="utf-8")
    report = audit_file(f)
    names = {e.name: e for e in report.entries}
    assert "MyClass" in names
    assert names["MyClass"].kind == "class"
    assert "public_method" in names
    assert names["public_method"].kind == "method"
    assert "_private_method" not in names  # 私有方法不计入公共 API


def test_audit_module_path_returns_dict() -> None:
    """R911 目录审计返回字典。"""
    reports = audit_module_path(SIM_DIR)
    assert isinstance(reports, dict)
    assert len(reports) > 0
    assert any(k.endswith("perf_tuning_r851.py") for k in reports)
    for k, r in reports.items():
        assert isinstance(k, str)
        assert isinstance(r, AuditReport)


def test_audit_module_path_nonexistent_raises() -> None:
    """R03 目录不存在 raise。"""
    with pytest.raises(FileNotFoundError):
        audit_module_path("/nonexistent/dir/xxx")


def test_auditor_threshold_pass() -> None:
    """R913 阈值断言通过场景。"""
    auditor = ApiDocAuditor(threshold=0.95)
    report = audit_file(PERF_TUNING)
    # 不 raise 即通过
    auditor.assert_threshold(report)


def test_auditor_threshold_fail(tmp_path) -> None:
    """R913 阈值断言失败场景。"""
    src = textwrap.dedent(
        '''
        def f1():
            """有 docstring。"""
            pass


        def f2():
            pass


        def f3():
            pass
        '''
    )
    f = tmp_path / "low.py"
    f.write_text(src, encoding="utf-8")
    auditor = ApiDocAuditor(threshold=0.95)
    report = audit_file(f)
    with pytest.raises(AssertionError):
        auditor.assert_threshold(report)


def test_auditor_invalid_threshold_raises() -> None:
    """R03 非法阈值 raise。"""
    with pytest.raises(ValueError):
        ApiDocAuditor(threshold=1.5)
    with pytest.raises(ValueError):
        ApiDocAuditor(threshold=-0.1)


def test_auditor_to_json_valid() -> None:
    """R912 JSON 报告导出有效。"""
    auditor = ApiDocAuditor()
    report = audit_file(PERF_TUNING)
    s = auditor.to_json(report)
    data = json.loads(s)
    assert data["file_path"].endswith("perf_tuning_r851.py")
    assert data["total"] > 0
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_auditor_missing_details_structure() -> None:
    """R914 缺失项明细结构正确。"""
    auditor = ApiDocAuditor()
    report = audit_file(PERF_TUNING)
    details = auditor.missing_details(report)
    assert isinstance(details, list)
    for d in details:
        assert "name" in d
        assert "kind" in d
        assert "lineno" in d
        assert "missing" in d
        assert isinstance(d["missing"], list)


def test_auditor_missing_details_on_poor_file(tmp_path) -> None:
    """R914 缺失项明细对低覆盖文件返回非空。"""
    src = textwrap.dedent(
        '''
        def f1(x):
            """只有 docstring 无段。

            无 Args/Returns/Example。
            """
            return x
        '''
    )
    f = tmp_path / "poor.py"
    f.write_text(src, encoding="utf-8")
    auditor = ApiDocAuditor()
    report = audit_file(f)
    details = auditor.missing_details(report)
    assert len(details) >= 1
    assert "Args" in details[0]["missing"]
    assert "Returns" in details[0]["missing"]
    assert "Example" in details[0]["missing"]


def test_has_section_fullwidth_colon() -> None:
    """R903-R906 全角冒号兼容（中英文混排）。"""
    from polaris.sim.api_doc_audit_r901 import _has_section

    assert _has_section("Args：参数", "Args") is True
    assert _has_section("Returns：结果", "Returns") is True
    assert _has_section("无段", "Args") is False
    assert _has_section("", "Args") is False


def test_is_public_naming() -> None:
    """R901 公共 API 命名判定。"""
    from polaris.sim.api_doc_audit_r901 import _is_public

    assert _is_public("foo") is True
    assert _is_public("_private") is False
    assert _is_public("__init__") is True  # 构造器例外
    assert _is_public("__double") is False
