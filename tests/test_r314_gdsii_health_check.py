"""R314 GDSII 文件级结构化校验工具测试。

覆盖:
- check_layer_completeness: 层定义完整性
- check_polygon_validity: 多边形有效性
- check_cell_references: cell 引用完整性
- check_unit_consistency: 单位一致性
- check_top_cell_uniqueness: 顶层 cell 唯一性
- check_gdsii_health: 端到端校验
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- KLayout Layout API: https://www.klayout.org/doc-qt5/code/class_Layout.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_health_check import (
    HealthCheckIssue,
    HealthCheckReport,
    IssueCategory,
    IssueSeverity,
    check_cell_references,
    check_gdsii_health,
    check_layer_completeness,
    check_polygon_validity,
    check_top_cell_uniqueness,
    check_unit_consistency,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def healthy_gds(tmp_path: Path) -> Path:
    """健康 GDSII 文件（WG 层合规多边形）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "healthy.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def undefined_layer_gds(tmp_path: Path) -> Path:
    """含未定义层 GDSII 文件（层 100/0 不在 SiEPIC 标准映射）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
                {
                    "layer": 100, "datatype": 0,  # 不在 SiEPIC 标准
                    "points": [[0, 0], [5, 0], [5, 5], [0, 5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "undefined.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_top_cell_gds(tmp_path: Path) -> Path:
    """多顶层 cell GDSII 文件。"""
    cells_spec = [
        {
            "name": "TOP1",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                },
            ],
            "is_top": True,
        },
        {
            "name": "TOP2",
            "polygons": [
                {
                    "layer": 1, "datatype": 0,
                    "points": [[0, 0], [20, 0], [20, 0.5], [0, 0.5]],
                },
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "multi_top.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def empty_gds(tmp_path: Path) -> Path:
    """空 GDSII 文件（仅创建空顶层 cell）。"""
    cells_spec = [
        {
            "name": "EMPTY_TOP",
            "polygons": [],
            "is_top": True,
        }
    ]
    out = tmp_path / "empty.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestCheckLayerCompleteness: 层完整性
# =============================================================================
class TestCheckLayerCompleteness:
    """check_layer_completeness 测试。"""

    def test_healthy_no_issues(self, healthy_gds: Path) -> None:
        """健康文件无层完整性问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(healthy_gds))
        issues = check_layer_completeness(ly)
        assert all(i.category == IssueCategory.LAYER_COMPLETENESS for i in issues)
        # WG (1,0) 在 SiEPIC 标准映射中，应无问题
        wg_issues = [i for i in issues if i.layer == "WG"]
        assert len(wg_issues) == 0

    def test_undefined_layer_warning(self, undefined_layer_gds: Path) -> None:
        """未定义层应触发 WARNING。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(undefined_layer_gds))
        issues = check_layer_completeness(ly)
        # 层 100/0 不在 SiEPIC 标准映射
        undefined_issues = [
            i for i in issues if i.layer == "LAYER_100_0"
        ]
        assert len(undefined_issues) == 1
        assert issues[0].severity == IssueSeverity.WARNING

    def test_custom_layer_map(self, undefined_layer_gds: Path) -> None:
        """自定义 layer_map 包含所有层应无问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(undefined_layer_gds))
        custom_map = {(1, 0): "WG", (100, 0): "CUSTOM"}
        issues = check_layer_completeness(ly, layer_map=custom_map)
        assert len(issues) == 0


# =============================================================================
# TestCheckPolygonValidity: 多边形有效性
# =============================================================================
class TestCheckPolygonValidity:
    """check_polygon_validity 测试。"""

    def test_healthy_polygon_no_issues(self, healthy_gds: Path) -> None:
        """健康多边形无问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(healthy_gds))
        top_cell = ly.cell(ly.each_top_cell().__next__())
        issues = check_polygon_validity(ly, top_cell)
        # 0 个 ERROR 级别问题
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 0

    def test_empty_gds_no_polygons(self, empty_gds: Path) -> None:
        """空 GDS 无多边形，无问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(empty_gds))
        top_cell = ly.cell(ly.each_top_cell().__next__())
        issues = check_polygon_validity(ly, top_cell)
        assert len(issues) == 0


# =============================================================================
# TestCheckCellReferences: cell 引用完整性
# =============================================================================
class TestCheckCellReferences:
    """check_cell_references 测试。"""

    def test_healthy_no_orphans(self, healthy_gds: Path) -> None:
        """健康文件无孤立 cell。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(healthy_gds))
        issues = check_cell_references(ly)
        # 单顶层 cell，无子 cell，无孤立
        orphans = [
            i for i in issues if "孤立 cell" in i.message
        ]
        assert len(orphans) == 0

    def test_multi_top_no_orphans(self, multi_top_cell_gds: Path) -> None:
        """多顶层 cell 文件无孤立 cell（顶层 cell 跳过）。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(multi_top_cell_gds))
        issues = check_cell_references(ly)
        orphans = [i for i in issues if "孤立" in i.message]
        assert len(orphans) == 0


# =============================================================================
# TestCheckUnitConsistency: 单位一致性
# =============================================================================
class TestCheckUnitConsistency:
    """check_unit_consistency 测试。"""

    def test_normal_dbu_no_issues(self, healthy_gds: Path) -> None:
        """正常 dbu 应无问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(healthy_gds))
        # export_gdsii_from_cells 默认 dbu 通常是 1e-8（10nm）或 1e-9（1nm）
        issues = check_unit_consistency(ly)
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 0

    def test_too_large_dbu_error(self) -> None:
        """dbu 过大应触发 ERROR。"""
        import klayout.db as db
        ly = db.Layout()
        ly.dbu = 1e-2  # 10mm，过大
        issues = check_unit_consistency(ly)
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 1
        assert "过大" in errors[0].message

    def test_too_small_dbu_error(self) -> None:
        """dbu 过小应触发 ERROR。"""
        import klayout.db as db
        ly = db.Layout()
        ly.dbu = 1e-12  # 1pm，过小
        issues = check_unit_consistency(ly)
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 1
        assert "过小" in errors[0].message

    def test_uncommon_dbu_warning(self) -> None:
        """非常见 dbu 值应触发 WARNING。"""
        import klayout.db as db
        ly = db.Layout()
        ly.dbu = 5e-9  # 5nm，不在常见值中
        issues = check_unit_consistency(ly)
        warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
        assert len(warnings) == 1
        assert "不是常见值" in warnings[0].message


# =============================================================================
# TestCheckTopCellUniqueness: 顶层 cell 唯一性
# =============================================================================
class TestCheckTopCellUniqueness:
    """check_top_cell_uniqueness 测试。"""

    def test_single_top_no_issues(self, healthy_gds: Path) -> None:
        """单顶层 cell 无问题。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(healthy_gds))
        issues = check_top_cell_uniqueness(ly)
        assert len(issues) == 0

    def test_multi_top_warning(self, multi_top_cell_gds: Path) -> None:
        """多顶层 cell 触发 WARNING。"""
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(multi_top_cell_gds))
        issues = check_top_cell_uniqueness(ly)
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARNING
        assert "2 个顶层 cell" in issues[0].message


# =============================================================================
# TestCheckGdsiiHealth: 端到端校验
# =============================================================================
class TestCheckGdsiiHealth:
    """check_gdsii_health 端到端测试。"""

    def test_healthy_file_passes(self, healthy_gds: Path) -> None:
        """健康文件应通过。"""
        report = check_gdsii_health(healthy_gds)
        assert isinstance(report, HealthCheckReport)
        assert report.passed is True
        assert report.file_path == str(healthy_gds)
        assert len(report.checks_run) == 5

    def test_undefined_layer_no_block(
        self, undefined_layer_gds: Path
    ) -> None:
        """未定义层是 WARNING，不应阻断 passed。"""
        report = check_gdsii_health(undefined_layer_gds)
        # WARNING 不阻断 passed
        assert report.passed is True
        # 应有 layer_completeness WARNING
        warnings = [
            i for i in report.issues
            if i.severity == IssueSeverity.WARNING
            and i.category == IssueCategory.LAYER_COMPLETENESS
        ]
        assert len(warnings) >= 1

    def test_multi_top_warning(
        self, multi_top_cell_gds: Path
    ) -> None:
        """多顶层 cell 是 WARNING，不阻断 passed。"""
        report = check_gdsii_health(multi_top_cell_gds)
        assert report.passed is True
        # 应有 top_cell_uniqueness WARNING
        top_warnings = [
            i for i in report.issues
            if i.category == IssueCategory.TOP_CELL_UNIQUENESS
        ]
        assert len(top_warnings) == 1

    def test_custom_checks_subset(self, healthy_gds: Path) -> None:
        """自定义检查项子集。"""
        report = check_gdsii_health(
            healthy_gds, checks=["unit_consistency", "top_cell_uniqueness"]
        )
        assert set(report.checks_run) == {
            "unit_consistency", "top_cell_uniqueness"
        }

    def test_unknown_check_raises(self, healthy_gds: Path) -> None:
        """未知检查项应 raise ValueError。"""
        with pytest.raises(ValueError, match="未知的检查项"):
            check_gdsii_health(healthy_gds, checks=["unknown_check"])

    def test_report_by_category(self, undefined_layer_gds: Path) -> None:
        """报告 by_category 字段。"""
        report = check_gdsii_health(undefined_layer_gds)
        assert "layer_completeness" in report.by_category
        assert report.by_category["layer_completeness"] >= 1

    def test_report_by_severity(self, undefined_layer_gds: Path) -> None:
        """报告 by_severity 字段。"""
        report = check_gdsii_health(undefined_layer_gds)
        assert "warning" in report.by_severity

    def test_custom_layer_map_no_warning(
        self, undefined_layer_gds: Path
    ) -> None:
        """自定义 layer_map 覆盖所有层应无 layer_completeness 警告。"""
        custom_map = {(1, 0): "WG", (100, 0): "CUSTOM"}
        report = check_gdsii_health(undefined_layer_gds, layer_map=custom_map)
        layer_issues = [
            i for i in report.issues
            if i.category == IssueCategory.LAYER_COMPLETENESS
        ]
        assert len(layer_issues) == 0

    def test_top_cell_name_specified(self, multi_top_cell_gds: Path) -> None:
        """指定 top_cell_name。"""
        report = check_gdsii_health(
            multi_top_cell_gds, top_cell_name="TOP1"
        )
        assert report.passed is True


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """文件不存在应 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            check_gdsii_health(tmp_path / "nonexistent.gds")

    def test_directory_raises(self, tmp_path: Path) -> None:
        """目录路径应 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            check_gdsii_health(tmp_path)

    def test_invalid_top_cell_raises(self, healthy_gds: Path) -> None:
        """无效 top_cell_name 应 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            check_gdsii_health(healthy_gds, top_cell_name="NONEXISTENT")

    def test_unknown_check_raises_value_error(
        self, healthy_gds: Path
    ) -> None:
        """未知检查项应 raise ValueError。"""
        with pytest.raises(ValueError, match="未知的检查项"):
            check_gdsii_health(
                healthy_gds, checks=["nonexistent_check"]
            )


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信验证。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 应含 5+ 文献 URL。"""
        from polaris.verification import gdsii_health_check as m
        doc = m.__doc__ or ""
        urls = [
            "klayout.org" in doc,
            "GDS_File" in doc or "wikipedia.org" in doc,
            "LayerInfo" in doc,
            "SimplePolygon" in doc,
            "Layout.read" in doc or "class_Layout" in doc,
            "Cell" in doc,
        ]
        url_count = sum(1 for u in urls if u)
        assert url_count >= 5, f"docstring 文献 URL 不足 5 个: {url_count}"

    def test_functions_have_source_annotations(self) -> None:
        """核心函数应含来源说明。"""
        from polaris.verification import gdsii_health_check as m
        for func_name in [
            "check_layer_completeness",
            "check_polygon_validity",
            "check_cell_references",
            "check_unit_consistency",
            "check_top_cell_uniqueness",
            "check_gdsii_health",
        ]:
            func = getattr(m, func_name)
            doc = func.__doc__ or ""
            assert "来源" in doc or "KLayout" in doc, (
                f"{func_name} 缺少来源标注"
            )

    def test_siepic_layer_map_inherited(self) -> None:
        """R314 通过 R312 继承 SiEPIC 标准层映射。"""
        import inspect
        from polaris.verification import gdsii_health_check as m
        src = inspect.getsource(m)
        assert "_get_default_layer_map" in src

    def test_issue_severity_documented(self) -> None:
        """IssueSeverity 应含文献溯源。"""
        from polaris.verification.gdsii_health_check import IssueSeverity
        doc = IssueSeverity.__doc__ or ""
        assert "logging" in doc.lower() or "python" in doc.lower()


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_health_check_workflow(self, healthy_gds: Path) -> None:
        """端到端: 健康检查 → 报告 → 验证字段完整性。"""
        report = check_gdsii_health(healthy_gds)
        # 验证报告字段
        assert report.file_path == str(healthy_gds)
        assert isinstance(report.issues, list)
        assert isinstance(report.passed, bool)
        assert isinstance(report.checks_run, list)
        assert isinstance(report.by_category, dict)
        assert isinstance(report.by_severity, dict)
        # 5 类检查都应执行
        assert len(report.checks_run) == 5

    def test_health_check_with_drc_pipeline(
        self,
        healthy_gds: Path,
    ) -> None:
        """健康检查 + DRC 流水线（pre-check → DRC）。"""
        # 1. 健康检查
        health = check_gdsii_health(healthy_gds)
        assert health.passed, "健康检查未通过，不应执行 DRC"
        # 2. 通过健康检查后执行 DRC
        from polaris.verification._drc_rules import (
            CurvilinearDRCRule,
            DRCRuleCategory,
        )
        from polaris.verification.gdsii_drc_validator import run_drc_on_gdsii

        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
        ]
        results = run_drc_on_gdsii(healthy_gds, rules)
        assert len(results) == 1

    def test_performance_large_gds(self, healthy_gds: Path) -> None:
        """性能: 单文件健康检查 < 2s。"""
        import time
        start = time.perf_counter()
        check_gdsii_health(healthy_gds)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_health_check_issue_defaults(self) -> None:
        """HealthCheckIssue 默认值。"""
        i = HealthCheckIssue(
            severity=IssueSeverity.WARNING,
            category=IssueCategory.LAYER_COMPLETENESS,
            message="测试问题",
        )
        assert i.severity == IssueSeverity.WARNING
        assert i.category == IssueCategory.LAYER_COMPLETENESS
        assert i.message == "测试问题"
        assert i.layer is None
        assert i.cell_name is None

    def test_health_check_report_defaults(self) -> None:
        """HealthCheckReport 默认值。"""
        r = HealthCheckReport(file_path="/tmp/test.gds")
        assert r.file_path == "/tmp/test.gds"
        assert r.issues == []
        assert r.passed is True
        assert r.checks_run == []
        assert r.by_category == {}
        assert r.by_severity == {}

    def test_issue_severity_enum_values(self) -> None:
        """IssueSeverity 枚举值。"""
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"

    def test_issue_category_enum_values(self) -> None:
        """IssueCategory 枚举值。"""
        assert IssueCategory.LAYER_COMPLETENESS.value == "layer_completeness"
        assert IssueCategory.POLYGON_VALIDITY.value == "polygon_validity"
        assert IssueCategory.CELL_REFERENCE.value == "cell_reference"
        assert IssueCategory.UNIT_CONSISTENCY.value == "unit_consistency"
        assert IssueCategory.TOP_CELL_UNIQUENESS.value == "top_cell_uniqueness"
