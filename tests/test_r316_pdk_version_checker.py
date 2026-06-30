"""R316 PDK 版本兼容性检测器测试。

覆盖:
- check_python_compatibility: Python 版本检测
- check_numpy_compatibility: NumPy 版本检测
- check_klayout_compatibility: KLayout 版本检测
- check_pdk_version_compatibility: PDK YAML 版本检测
- run_full_compatibility_check: 端到端检测
- format_compatibility_report: 报告渲染
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- KLayout: https://www.klayout.de/
- NumPy: https://numpy.org/doc/stable/
- SemVer: https://semver.org/
"""

from __future__ import annotations

import sys

import pytest

from polaris.pdk.pdk_version_checker import (
    CompatibilityCheck,
    CompatibilityLevel,
    CompatibilityReport,
    check_klayout_compatibility,
    check_numpy_compatibility,
    check_pdk_version_compatibility,
    check_python_compatibility,
    format_compatibility_report,
    run_full_compatibility_check,
)


# =============================================================================
# TestCheckPythonCompatibility: Python 版本检测
# =============================================================================
class TestCheckPythonCompatibility:
    """check_python_compatibility 测试。"""

    def test_returns_check_object(self) -> None:
        """应返回 CompatibilityCheck 对象。"""
        result = check_python_compatibility()
        assert isinstance(result, CompatibilityCheck)
        assert result.name == "python_version"

    def test_current_version_matches_sys(self) -> None:
        """当前版本应匹配 sys.version_info。"""
        result = check_python_compatibility()
        expected = (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        assert result.current_version == expected

    def test_py314_warning(self) -> None:
        """Python 3.14+ 应 WARNING。"""
        result = check_python_compatibility()
        if sys.version_info >= (3, 14):
            assert result.level == CompatibilityLevel.WARNING
            assert "pydantic" in result.message

    def test_py310_to_313_ok(self) -> None:
        """Python 3.10-3.13 应 OK。"""
        result = check_python_compatibility()
        if (3, 10) <= sys.version_info[:2] <= (3, 13):
            assert result.level == CompatibilityLevel.OK


# =============================================================================
# TestCheckNumpyCompatibility: NumPy 版本检测
# =============================================================================
class TestCheckNumpyCompatibility:
    """check_numpy_compatibility 测试。"""

    def test_returns_check_object(self) -> None:
        """应返回 CompatibilityCheck 对象。"""
        result = check_numpy_compatibility()
        assert isinstance(result, CompatibilityCheck)
        assert result.name == "numpy_version"

    def test_current_version_matches_np(self) -> None:
        """当前版本应匹配 numpy.__version__。"""
        import numpy as np
        result = check_numpy_compatibility()
        assert result.current_version == np.__version__

    def test_modern_numpy_ok(self) -> None:
        """现代 NumPy（>=1.24）应 OK。"""
        result = check_numpy_compatibility()
        import numpy as np
        np_tuple = tuple(int(x) for x in np.__version__.split(".")[:2])
        if np_tuple >= (1, 24):
            assert result.level == CompatibilityLevel.OK


# =============================================================================
# TestCheckKlayoutCompatibility: KLayout 版本检测
# =============================================================================
class TestCheckKlayoutCompatibility:
    """check_klayout_compatibility 测试。"""

    def test_returns_check_object(self) -> None:
        """应返回 CompatibilityCheck 对象。"""
        try:
            import klayout  # noqa: F401
        except ImportError:
            pytest.skip("klayout 未安装")
        result = check_klayout_compatibility()
        assert isinstance(result, CompatibilityCheck)
        assert result.name == "klayout_version"

    def test_modern_klayout_ok(self) -> None:
        """现代 KLayout（>=0.28）应 OK。"""
        try:
            import klayout
        except ImportError:
            pytest.skip("klayout 未安装")
        result = check_klayout_compatibility()
        kl_version = getattr(klayout, "__version__", "0.0.0")
        kl_tuple = tuple(int(x) for x in kl_version.split(".")[:2])
        if kl_tuple >= (0, 28):
            assert result.level == CompatibilityLevel.OK


# =============================================================================
# TestCheckPdkVersionCompatibility: PDK YAML 版本检测
# =============================================================================
class TestCheckPdkVersionCompatibility:
    """check_pdk_version_compatibility 测试。"""

    def test_dict_input_supported_version(self) -> None:
        """dict 输入，版本在支持列表中。"""
        data = {"name": "test_pdk", "version": "1.0.0"}
        result = check_pdk_version_compatibility(data)
        assert result.level == CompatibilityLevel.OK
        assert result.current_version == "1.0.0"

    def test_dict_input_unsupported_version(self) -> None:
        """dict 输入，版本不在支持列表中。"""
        data = {"name": "test_pdk", "version": "2.0.0"}
        result = check_pdk_version_compatibility(
            data, supported_versions=["1.0.0"]
        )
        assert result.level == CompatibilityLevel.WARNING
        assert "2.0.0" in result.message

    def test_custom_supported_versions(self) -> None:
        """自定义支持版本列表。"""
        data = {"name": "test_pdk", "version": "2.0.0"}
        result = check_pdk_version_compatibility(
            data, supported_versions=["2.0.0", "3.0.0"]
        )
        assert result.level == CompatibilityLevel.OK

    def test_missing_version_field_raises(self) -> None:
        """缺少 version 字段 raise ValueError。"""
        data = {"name": "test_pdk"}  # 无 version
        with pytest.raises(ValueError, match="缺少 version"):
            check_pdk_version_compatibility(data)

    def test_invalid_version_string_raises(self) -> None:
        """无效版本字符串 raise ValueError。"""
        data = {"name": "test_pdk", "version": "invalid"}
        with pytest.raises(ValueError, match="无效"):
            check_pdk_version_compatibility(data)

    def test_file_not_found_raises(self, tmp_path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_pdk_version_compatibility(
                tmp_path / "nonexistent.yaml"
            )

    def test_yaml_file_input(self, tmp_path) -> None:
        """YAML 文件输入。"""
        import yaml
        yaml_path = tmp_path / "pdk.yaml"
        yaml_path.write_text(
            "name: test_pdk\nversion: 1.0.0\n", encoding="utf-8"
        )
        result = check_pdk_version_compatibility(yaml_path)
        assert result.level == CompatibilityLevel.OK
        assert result.current_version == "1.0.0"


# =============================================================================
# TestRunFullCompatibilityCheck: 端到端检测
# =============================================================================
class TestRunFullCompatibilityCheck:
    """run_full_compatibility_check 测试。"""

    def test_basic_report(self) -> None:
        """基本报告。"""
        report = run_full_compatibility_check(timestamp=1000.0)
        assert isinstance(report, CompatibilityReport)
        assert report.timestamp == 1000.0
        # 至少包含 Python + NumPy + KLayout
        names = [c.name for c in report.checks]
        assert "python_version" in names
        assert "numpy_version" in names
        # KLayout 未安装时为 WARNING 占位
        assert "klayout_version" in names

    def test_with_pdk_yaml(self) -> None:
        """含 PDK YAML 检测。"""
        data = {"name": "test_pdk", "version": "1.0.0"}
        report = run_full_compatibility_check(pdk_yaml_path=data)
        names = [c.name for c in report.checks]
        assert "pdk_version" in names

    def test_overall_level_calculation(self) -> None:
        """总体级别计算。"""
        report = run_full_compatibility_check()
        levels = [c.level for c in report.checks]
        if CompatibilityLevel.ERROR in levels:
            assert report.overall_level == CompatibilityLevel.ERROR
            assert report.passed is False
        elif CompatibilityLevel.WARNING in levels:
            assert report.overall_level == CompatibilityLevel.WARNING
            assert report.passed is True
        else:
            assert report.overall_level == CompatibilityLevel.OK
            assert report.passed is True

    def test_no_pdk_yaml_skips_pdk_check(self) -> None:
        """无 PDK YAML 时跳过 PDK 检测。"""
        report = run_full_compatibility_check()
        names = [c.name for c in report.checks]
        assert "pdk_version" not in names


# =============================================================================
# TestFormatCompatibilityReport: 报告渲染
# =============================================================================
class TestFormatCompatibilityReport:
    """format_compatibility_report 测试。"""

    def test_text_format(self) -> None:
        """text 格式。"""
        report = run_full_compatibility_check()
        text = format_compatibility_report(report, "text")
        assert isinstance(text, str)
        assert "PoLaRIS 兼容性检测报告" in text
        assert "总体级别" in text

    def test_markdown_format(self) -> None:
        """markdown 格式。"""
        report = run_full_compatibility_check()
        md = format_compatibility_report(report, "markdown")
        assert isinstance(md, str)
        assert "# PoLaRIS 兼容性检测报告" in md
        assert "| 级别 |" in md

    def test_format_case_insensitive(self) -> None:
        """格式参数大小写不敏感。"""
        report = run_full_compatibility_check()
        r1 = format_compatibility_report(report, "TEXT")
        r2 = format_compatibility_report(report, "text")
        assert r1 == r2

    def test_unsupported_format_raises(self) -> None:
        """不支持格式 raise ValueError。"""
        report = run_full_compatibility_check()
        with pytest.raises(ValueError, match="不支持"):
            format_compatibility_report(report, "xml")

    def test_invalid_report_type_raises(self) -> None:
        """非 CompatibilityReport raise TypeError。"""
        with pytest.raises(TypeError):
            format_compatibility_report("not_a_report", "text")  # type: ignore[arg-type]


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理。"""

    def test_pdk_missing_version_raises(self) -> None:
        """PDK 缺 version 字段 raise ValueError。"""
        with pytest.raises(ValueError):
            check_pdk_version_compatibility({"name": "test"})

    def test_invalid_version_raises(self) -> None:
        """无效版本字符串 raise ValueError。"""
        with pytest.raises(ValueError):
            check_pdk_version_compatibility(
                {"name": "test", "version": "abc"}
            )

    def test_unsupported_format_raises(self) -> None:
        """不支持格式 raise ValueError。"""
        report = run_full_compatibility_check()
        with pytest.raises(ValueError):
            format_compatibility_report(report, "yaml")


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信验证。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 应含 5+ 文献 URL。"""
        from polaris.pdk import pdk_version_checker as m
        doc = m.__doc__ or ""
        urls = [
            "gdsfactory" in doc,
            "klayout" in doc,
            "numpy.org" in doc,
            "semver.org" in doc,
            "python.org" in doc,
            "SiEPIC" in doc,
        ]
        url_count = sum(1 for u in urls if u)
        assert url_count >= 5, f"docstring 文献 URL 不足 5 个: {url_count}"

    def test_functions_have_source_annotations(self) -> None:
        """核心函数应含来源说明。"""
        from polaris.pdk import pdk_version_checker as m
        for func_name in [
            "check_python_compatibility",
            "check_numpy_compatibility",
            "check_klayout_compatibility",
            "check_pdk_version_compatibility",
        ]:
            func = getattr(m, func_name)
            doc = func.__doc__ or ""
            assert "来源" in doc or "gdsfactory" in doc or "numpy" in doc, (
                f"{func_name} 缺少来源标注"
            )

    def test_py314_pydantic_issue_documented(self) -> None:
        """Python 3.14 pydantic 问题应记录。"""
        from polaris.pdk import pdk_version_checker as m
        src = m.check_python_compatibility.__doc__ or ""
        assert "pydantic" in src.lower() or "3.14" in src

    def test_semver_reference(self) -> None:
        """应引用 SemVer 规范。"""
        from polaris.pdk import pdk_version_checker as m
        doc = m.__doc__ or ""
        assert "semver" in doc.lower()


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_workflow(self) -> None:
        """端到端: 检测 → 报告 → 渲染。"""
        # 1. 检测
        report = run_full_compatibility_check(timestamp=1234.5)
        assert isinstance(report, CompatibilityReport)
        # 2. 渲染（两种格式）
        for fmt in ["text", "markdown"]:
            output = format_compatibility_report(report, fmt)
            assert isinstance(output, str)
            assert len(output) > 0

    def test_with_pdk_yaml_full_workflow(self, tmp_path) -> None:
        """含 PDK YAML 的完整工作流。"""
        import yaml
        yaml_path = tmp_path / "pdk.yaml"
        yaml_path.write_text(
            "name: test_pdk\nversion: 1.0.0\n", encoding="utf-8"
        )
        report = run_full_compatibility_check(pdk_yaml_path=yaml_path)
        names = [c.name for c in report.checks]
        assert "pdk_version" in names
        # 渲染
        text = format_compatibility_report(report, "text")
        assert "pdk_version" in text

    def test_performance(self) -> None:
        """性能: 完整检测 < 2s。"""
        import time
        start = time.perf_counter()
        run_full_compatibility_check()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_compatibility_check_defaults(self) -> None:
        """CompatibilityCheck 默认值。"""
        c = CompatibilityCheck(
            name="test",
            level=CompatibilityLevel.OK,
            current_version="1.0.0",
        )
        assert c.name == "test"
        assert c.level == CompatibilityLevel.OK
        assert c.current_version == "1.0.0"
        assert c.required_version is None
        assert c.message == ""
        assert c.recommended_action == ""

    def test_compatibility_report_defaults(self) -> None:
        """CompatibilityReport 默认值。"""
        r = CompatibilityReport()
        assert r.checks == []
        assert r.overall_level == CompatibilityLevel.OK
        assert r.passed is True
        assert r.timestamp == 0.0

    def test_compatibility_level_enum_values(self) -> None:
        """CompatibilityLevel 枚举值。"""
        assert CompatibilityLevel.OK.value == "ok"
        assert CompatibilityLevel.WARNING.value == "warning"
        assert CompatibilityLevel.ERROR.value == "error"
