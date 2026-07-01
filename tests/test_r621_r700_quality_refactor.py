"""R621-R700 代码质量重构回归测试。

验证 Extract Method 重构后函数行为保持不变：
- api_doc_audit_r901.py: _make_audit_entry / _collect_audit_entries / _compute_coverage_stats
- default_simulator.py: _cross_2d / _segments_properly_intersect / _build_path_segments / _count_path_crossings

学术依据（R02，≥5 文献 URL）：
- Martin Fowler, "Refactoring: Improving the Design of Existing Code,"
  2nd ed., Addison-Wesley, 2018 — https://martinfowler.com/books/refactoring.html
- Beck K, "Implementation Patterns," Addison-Wesley, 2007
- PEP 257 Docstring Conventions — https://peps.python.org/pep-0257/
- Bentley-Ottmann 线段相交算法 — https://en.wikipedia.org/wiki/Bentley%E2%80%93Ottmann_algorithm
- Cormen et al., "Introduction to Algorithms," 3rd ed., MIT Press, 2009, §33.1
- Python ast 模块 — https://docs.python.org/3/library/ast.html
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"


def _load_module(name: str, rel_path: str):
    """通过 importlib 直接加载模块文件，绕过 polaris.sim.__init__ 的 sax 依赖。

    Args:
        name: 模块注册名。
        rel_path: 相对 src 的路径。

    Returns:
        已加载的模块对象。
    """
    full = SRC / rel_path
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def audit_mod():
    """加载 api_doc_audit_r901 模块。"""
    return _load_module("api_doc_audit_r901_r621", "polaris/sim/api_doc_audit_r901.py")


@pytest.fixture(scope="module")
def sim_mod():
    """加载 default_simulator 模块。"""
    return _load_module("default_simulator_r621", "polaris/pipeline/default_simulator.py")


# =============================================================================
# api_doc_audit_r901 重构回归测试
# =============================================================================


class TestAuditFileRefactor:
    """audit_file Extract Method 重构回归测试。"""

    def test_audit_file_still_returns_report(self, audit_mod):
        """R621 重构后 audit_file 仍返回正确 AuditReport。"""
        target = SRC / "polaris" / "sim" / "perf_tuning_r851.py"
        if not target.exists():
            pytest.skip(f"目标文件不存在: {target}")
        report = audit_mod.audit_file(target)
        assert report.total > 0
        assert report.documented > 0
        assert 0.0 <= report.docstring_coverage <= 1.0
        assert 0.0 <= report.full_coverage <= 1.0

    def test_collect_audit_entries_returns_list(self, audit_mod):
        """_collect_audit_entries 返回 AuditEntry 列表。"""
        source = '"""mod."""\ndef public_fn(x):\n    """doc."""\n    return x\n'
        tree = audit_mod.ast.parse(source)
        entries = audit_mod._collect_audit_entries(tree)
        assert len(entries) == 1
        assert entries[0].name == "public_fn"
        assert entries[0].kind == "function"
        assert entries[0].has_docstring is True

    def test_collect_audit_entries_skips_private(self, audit_mod):
        """_collect_audit_entries 跳过私有函数。"""
        source = (
            '"""mod."""\n'
            'def public_fn(x):\n    """doc."""\n    return x\n'
            'def _private_fn(x):\n    return x\n'
        )
        tree = audit_mod.ast.parse(source)
        entries = audit_mod._collect_audit_entries(tree)
        assert len(entries) == 1
        assert entries[0].name == "public_fn"

    def test_collect_audit_entries_includes_class_methods(self, audit_mod):
        """_collect_audit_entries 包含类的公共方法。"""
        source = (
            '"""mod."""\n'
            'class Foo:\n    """doc."""\n'
            '    def bar(self):\n        """doc."""\n        return 1\n'
            '    def _baz(self):\n        return 2\n'
        )
        tree = audit_mod.ast.parse(source)
        entries = audit_mod._collect_audit_entries(tree)
        names = [e.name for e in entries]
        assert "Foo" in names
        assert "bar" in names
        assert "_baz" not in names

    def test_compute_coverage_stats_fills_report(self, audit_mod):
        """_compute_coverage_stats 正确填充 report 字段。"""
        entries = [
            audit_mod.AuditEntry(
                name="f1", kind="function", lineno=1,
                has_docstring=True, has_args=True, has_returns=True,
                has_raises=False, has_example=True, qualified_name="f1",
            ),
            audit_mod.AuditEntry(
                name="f2", kind="function", lineno=10,
                has_docstring=False, has_args=False, has_returns=False,
                has_raises=False, has_example=False, qualified_name="f2",
            ),
        ]
        report = audit_mod.AuditReport(file_path="test.py")
        audit_mod._compute_coverage_stats(report, entries)
        assert report.total == 2
        assert report.documented == 1
        assert report.with_args == 1
        assert report.with_returns == 1
        assert report.with_example == 1
        assert report.docstring_coverage == 0.5
        assert report.full_coverage == 0.5

    def test_compute_coverage_stats_empty_entries(self, audit_mod):
        """_compute_coverage_stats 空条目时覆盖率为 1.0。"""
        report = audit_mod.AuditReport(file_path="empty.py")
        audit_mod._compute_coverage_stats(report, [])
        assert report.total == 0
        assert report.docstring_coverage == 1.0
        assert report.full_coverage == 1.0

    def test_make_audit_entry_parses_docstring_sections(self, audit_mod):
        """_make_audit_entry 正确解析 docstring 的 Args/Returns/Example 段。"""
        source = (
            'def fn(x):\n'
            '    """Summary.\n\n'
            '    Args:\n        x: 参数。\n\n'
            '    Returns:\n        结果。\n\n'
            '    Example:\n        >>> fn(1)\n    """\n'
            '    return x\n'
        )
        tree = audit_mod.ast.parse(source)
        node = tree.body[0]
        entry = audit_mod._make_audit_entry(node, "function", "fn")
        assert entry.has_docstring is True
        assert entry.has_args is True
        assert entry.has_returns is True
        assert entry.has_example is True
        assert entry.has_raises is False

    def test_audit_file_syntax_error_records(self, audit_mod, tmp_path):
        """audit_file 语法错误时记录 syntax_error 而非崩溃。"""
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(:\n", encoding="utf-8")
        report = audit_mod.audit_file(bad)
        assert report.syntax_error != ""
        assert "SyntaxError" in report.syntax_error

    def test_audit_file_missing_file_raises(self, audit_mod):
        """audit_file 文件不存在时 raise FileNotFoundError（R03 无 fall-back）。"""
        with pytest.raises(FileNotFoundError):
            audit_mod.audit_file("/nonexistent/path/file.py")


# =============================================================================
# default_simulator 重构回归测试
# =============================================================================


class TestCountPathCrossingsRefactor:
    """_count_path_crossings Extract Method 重构回归测试。"""

    def test_cross_2d_positive(self, sim_mod):
        """_cross_2d 左转返回正值。"""
        # o=(0,0), a=(1,0), b=(0,1) → 左转 → 正值
        result = sim_mod._cross_2d((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
        assert result > 0

    def test_cross_2d_negative(self, sim_mod):
        """_cross_2d 右转返回负值。"""
        # o=(0,0), a=(0,1), b=(1,0) → 右转 → 负值
        result = sim_mod._cross_2d((0.0, 0.0), (0.0, 1.0), (1.0, 0.0))
        assert result < 0

    def test_cross_2d_collinear(self, sim_mod):
        """_cross_2d 共线返回 0。"""
        result = sim_mod._cross_2d((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
        assert result == 0.0

    def test_segments_properly_intersect_crossing(self, sim_mod):
        """_segments_properly_intersect 交叉线段返回 True。"""
        # X 形交叉
        p1, p2 = (0.0, 0.0), (10.0, 10.0)
        p3, p4 = (0.0, 10.0), (10.0, 0.0)
        assert sim_mod._segments_properly_intersect(p1, p2, p3, p4) is True

    def test_segments_properly_intersect_parallel(self, sim_mod):
        """_segments_properly_intersect 平行线段返回 False。"""
        p1, p2 = (0.0, 0.0), (10.0, 0.0)
        p3, p4 = (0.0, 5.0), (10.0, 5.0)
        assert sim_mod._segments_properly_intersect(p1, p2, p3, p4) is False

    def test_segments_properly_intersect_shared_endpoint(self, sim_mod):
        """_segments_properly_intersect 共享端点不算相交（返回 False）。"""
        # 共享端点 (5,5)，d 值为 0，不满足严格异号
        p1, p2 = (0.0, 0.0), (5.0, 5.0)
        p3, p4 = (5.0, 5.0), (10.0, 0.0)
        assert sim_mod._segments_properly_intersect(p1, p2, p3, p4) is False

    def test_build_path_segments_normal(self, sim_mod):
        """_build_path_segments 正常展开线段。"""
        paths = {"a": [(0, 0), (1, 1), (2, 2)]}
        segs = sim_mod._build_path_segments(paths)
        assert len(segs) == 2
        assert segs[0][0] == "a"
        assert segs[1][0] == "a"

    def test_build_path_segments_skip_short(self, sim_mod):
        """_build_path_segments 跳过不足 2 点的路径。"""
        paths = {"a": [(0, 0)], "b": [(0, 0), (1, 1)]}
        segs = sim_mod._build_path_segments(paths)
        assert len(segs) == 1
        assert segs[0][0] == "b"

    def test_build_path_segments_empty(self, sim_mod):
        """_build_path_segments 空字典返回空列表。"""
        segs = sim_mod._build_path_segments({})
        assert segs == []

    def test_count_path_crossings_one_intersection(self, sim_mod):
        """_count_path_crossings 检测到 1 个交叉（X 形）。"""
        paths = {
            "a": [(0, 0), (10, 10)],
            "b": [(0, 10), (10, 0)],
        }
        assert sim_mod._count_path_crossings(paths) == 1

    def test_count_path_crossings_no_intersection(self, sim_mod):
        """_count_path_crossings 平行路径无交叉。"""
        paths = {
            "a": [(0, 0), (10, 0)],
            "b": [(0, 5), (10, 5)],
        }
        assert sim_mod._count_path_crossings(paths) == 0

    def test_count_path_crossings_same_path_no_self_intersect(self, sim_mod):
        """_count_path_crossings 同一路径内线段不算交叉。"""
        paths = {"a": [(0, 0), (5, 5), (0, 5)]}
        assert sim_mod._count_path_crossings(paths) == 0

    def test_count_path_crossings_multiple(self, sim_mod):
        """_count_path_crossings 多条路径多交叉。"""
        paths = {
            "a": [(0, 0), (10, 10)],
            "b": [(0, 10), (10, 0)],
            "c": [(0, 5), (10, 5)],
        }
        # a-b 交叉, a-c 交叉, b-c 交叉 → 3
        assert sim_mod._count_path_crossings(paths) == 3

    def test_count_path_crossings_empty(self, sim_mod):
        """_count_path_crossings 空字典返回 0。"""
        assert sim_mod._count_path_crossings({}) == 0

    def test_count_path_crossings_float_coords(self, sim_mod):
        """_count_path_crossings 支持浮点坐标。"""
        paths = {
            "a": [(0.0, 0.0), (1.5, 1.5)],
            "b": [(0.0, 1.5), (1.5, 0.0)],
        }
        assert sim_mod._count_path_crossings(paths) == 1
