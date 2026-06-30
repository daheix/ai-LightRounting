"""R329 GDSII 流片前预检查工具测试。

覆盖:
- tapeout_precheck: 综合检查（grid+health+hierarchy / 选择性 / pass/fail 判定）
- generate_tapeout_report: text/markdown 报告
- TapeoutReport: 数据类
- R03 错误处理（文件不存在 / grid_um<=0 / 未知检查项 / 空列表）
- R02 学术诚信（docstring URL ≥5 个 / __all__ / ALL_CHECKS）
- 集成测试（预检查后裁剪/扁平化 / off-grid 检测）

来源:
- KLayout DRC Reference:
  https://klayout.org/downloads/master/doc-qt5/about/drc_ref.html
- Calibre DRC:
  https://www.mentor.com/products/ic_nanometer_design/calibre-drc
- SiEPIC EBeam PDK:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout Layout.read:
  https://www.klayout.org/doc-qt5/code/class_Layout.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_tapeout_precheck import (
    ALL_CHECKS,
    TapeoutReport,
    generate_tapeout_report,
    tapeout_precheck,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def dirty_gds(tmp_path: Path) -> Path:
    """创建含 off-grid 顶点的 GDSII（grid 检查会失败）。

    TOP: on-grid 三角形 (0,0)-(10,0)-(5,5)
    CHILD: off-grid 三角形 (0,0)-(0.007,0)-(0.007,0.005)，实例化在 (20,0)
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [0.007, 0], [0.007, 0.005]],
                },
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 20.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "dirty.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def clean_gds(tmp_path: Path) -> Path:
    """创建干净的 GDSII（所有检查通过）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [10, 0], [5, 5]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "clean.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def empty_gds(tmp_path: Path) -> Path:
    """创建空 GDSII（无 cell）。"""
    import klayout.db as db

    ly = db.Layout()
    out = tmp_path / "empty.gds"
    ly.write(str(out))
    return out


# =============================================================================
# TestTapeoutPrecheck: 基本预检查
# =============================================================================
class TestTapeoutPrecheck:
    """tapeout_precheck 函数测试。"""

    def test_returns_report(self, clean_gds: Path) -> None:
        """返回 TapeoutReport。"""
        report = tapeout_precheck(clean_gds)
        assert isinstance(report, TapeoutReport)
        assert report.file_path == str(clean_gds)

    def test_default_all_checks(self, clean_gds: Path) -> None:
        """默认执行全部检查。"""
        report = tapeout_precheck(clean_gds)
        assert set(report.checks_run) == set(ALL_CHECKS.keys())

    def test_selective_checks(self, clean_gds: Path) -> None:
        """选择性执行检查项。"""
        report = tapeout_precheck(clean_gds, checks=["grid"])
        assert report.checks_run == ["grid"]
        assert report.grid_report is not None
        assert report.health_report is None
        assert report.hierarchy_report is None

    def test_selective_health(self, clean_gds: Path) -> None:
        """只执行 health 检查。"""
        report = tapeout_precheck(clean_gds, checks=["health"])
        assert report.health_report is not None
        assert report.grid_report is None

    def test_selective_hierarchy(self, clean_gds: Path) -> None:
        """只执行 hierarchy 检查。"""
        report = tapeout_precheck(clean_gds, checks=["hierarchy"])
        assert report.hierarchy_report is not None
        assert report.grid_report is None

    def test_clean_gds_passes(self, clean_gds: Path) -> None:
        """干净 GDSII 所有检查通过。"""
        report = tapeout_precheck(clean_gds)
        assert report.passed is True
        assert report.error_count == 0

    def test_dirty_gds_fails(self, dirty_gds: Path) -> None:
        """含 off-grid 的 GDSII 检查失败。"""
        report = tapeout_precheck(dirty_gds)
        assert report.passed is False
        assert report.grid_passed is False

    def test_grid_passed_logic(self, dirty_gds: Path) -> None:
        """grid_passed 逻辑正确。"""
        report = tapeout_precheck(dirty_gds, checks=["grid"])
        # dirty_gds 含 2 个 off-grid 顶点
        assert report.grid_passed is False
        assert report.grid_report.total_violations == 2

    def test_health_passed_logic(self, clean_gds: Path) -> None:
        """health_passed 逻辑正确。"""
        report = tapeout_precheck(clean_gds, checks=["health"])
        assert report.health_passed is True

    def test_hierarchy_passed_logic(self, dirty_gds: Path) -> None:
        """hierarchy_passed 逻辑正确（无循环引用）。"""
        report = tapeout_precheck(dirty_gds, checks=["hierarchy"])
        assert report.hierarchy_passed is True
        assert report.hierarchy_report.has_circular_reference is False

    def test_error_count_dirty(self, dirty_gds: Path) -> None:
        """dirty GDSII 错误数 = grid violations。"""
        report = tapeout_precheck(dirty_gds, checks=["grid"])
        assert report.error_count == 2

    def test_error_count_clean(self, clean_gds: Path) -> None:
        """clean GDSII 错误数为 0。"""
        report = tapeout_precheck(clean_gds)
        assert report.error_count == 0

    def test_top_cell_name_captured(self, dirty_gds: Path) -> None:
        """top_cell_name 被记录。"""
        report = tapeout_precheck(dirty_gds)
        assert report.top_cell_name == "TOP"

    def test_dbu_captured(self, clean_gds: Path) -> None:
        """dbu 被记录。"""
        report = tapeout_precheck(clean_gds)
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_passed_all_true_when_all_pass(
        self, clean_gds: Path
    ) -> None:
        """所有检查通过时 passed=True。"""
        report = tapeout_precheck(clean_gds)
        assert report.grid_passed is True
        assert report.health_passed is True
        assert report.hierarchy_passed is True
        assert report.passed is True

    def test_passed_false_when_grid_fails(
        self, dirty_gds: Path
    ) -> None:
        """grid 失败时 passed=False。"""
        report = tapeout_precheck(dirty_gds)
        assert report.grid_passed is False
        assert report.passed is False


# =============================================================================
# TestGenerateTapeoutReport: 报告生成
# =============================================================================
class TestGenerateTapeoutReport:
    """generate_tapeout_report 函数测试。"""

    def test_text_report(self, clean_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_tapeout_report(clean_gds, output_format="text")
        assert isinstance(report, str)
        assert "流片前预检查报告" in report
        assert "总体状态" in report
        assert "错误数" in report

    def test_markdown_report(self, clean_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_tapeout_report(clean_gds, output_format="markdown")
        assert isinstance(report, str)
        assert "# GDSII 流片前预检查报告" in report
        assert "**总体状态**" in report

    def test_text_contains_sections(self, clean_gds: Path) -> None:
        """text 报告含各检查节。"""
        report = generate_tapeout_report(clean_gds, output_format="text")
        assert "网格对齐检查" in report
        assert "结构健康检查" in report
        assert "层次完整性检查" in report

    def test_markdown_contains_status(self, dirty_gds: Path) -> None:
        """markdown 报告含失败状态。"""
        report = generate_tapeout_report(dirty_gds, output_format="markdown")
        assert "失败" in report

    def test_text_contains_error_count(self, dirty_gds: Path) -> None:
        """text 报告含错误数。"""
        report = generate_tapeout_report(dirty_gds, output_format="text")
        assert "错误数: 2" in report

    def test_unsupported_format(self, clean_gds: Path) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_tapeout_report(clean_gds, output_format="html")

    def test_report_with_selective_checks(
        self, clean_gds: Path
    ) -> None:
        """选择性检查的报告只含对应节。"""
        report = generate_tapeout_report(
            clean_gds, checks=["grid"], output_format="text"
        )
        assert "网格对齐检查" in report
        # health/hierarchy 未执行，不应出现
        assert "结构健康检查" not in report


# =============================================================================
# TestR03ErrorHandling: 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="GDSII 文件不存在"):
            tapeout_precheck(tmp_path / "nonexistent.gds")

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            tapeout_precheck(tmp_path)

    def test_grid_um_le_zero(self, clean_gds: Path) -> None:
        """grid_um <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="grid_um 必须 > 0"):
            tapeout_precheck(clean_gds, grid_um=0.0)

    def test_grid_um_negative(self, clean_gds: Path) -> None:
        """grid_um < 0 raise ValueError。"""
        with pytest.raises(ValueError, match="grid_um 必须 > 0"):
            tapeout_precheck(clean_gds, grid_um=-0.001)

    def test_unknown_check(self, clean_gds: Path) -> None:
        """未知检查项 raise ValueError。"""
        with pytest.raises(ValueError, match="未知的检查项"):
            tapeout_precheck(clean_gds, checks=["unknown"])

    def test_empty_checks_list(self, clean_gds: Path) -> None:
        """空 checks 列表 raise ValueError（禁止无意义操作）。"""
        with pytest.raises(ValueError, match="不能为空列表"):
            tapeout_precheck(clean_gds, checks=[])

    def test_unsupported_format_raises(
        self, clean_gds: Path
    ) -> None:
        """不支持的输出格式 raise ValueError（不静默兜底）。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_tapeout_report(clean_gds, output_format="xml")


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_urls_count(self) -> None:
        """模块 docstring 含 ≥5 个文献 URL。"""
        import polaris.verification.gdsii_tapeout_precheck as mod
        import re

        doc = mod.__doc__ or ""
        urls = re.findall(r"https?://[^\s)]+", doc)
        assert len(urls) >= 5, (
            f"docstring 应含 ≥5 个 URL，实际 {len(urls)} 个"
        )

    def test_all_exported(self) -> None:
        """__all__ 导出完整。"""
        import polaris.verification.gdsii_tapeout_precheck as mod

        assert set(mod.__all__) == {
            "TapeoutReport",
            "tapeout_precheck",
            "generate_tapeout_report",
        }

    def test_tapeout_report_is_dataclass(self) -> None:
        """TapeoutReport 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(TapeoutReport)

    def test_all_checks_constant(self) -> None:
        """ALL_CHECKS 常量含 3 个检查项。"""
        assert set(ALL_CHECKS.keys()) == {"grid", "health", "hierarchy"}

    def test_all_checks_has_descriptions(self) -> None:
        """ALL_CHECKS 每项有描述。"""
        for key, desc in ALL_CHECKS.items():
            assert isinstance(key, str)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_default_values(self) -> None:
        """TapeoutReport 默认值合理。"""
        report = TapeoutReport(file_path="a")
        assert report.dbu == 0.0
        assert report.top_cell_name == ""
        assert report.checks_run == []
        assert report.grid_report is None
        assert report.passed is True
        assert report.error_count == 0

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back。"""
        import polaris.verification.gdsii_tapeout_precheck as mod
        import inspect

        src = inspect.getsource(mod)
        assert "except: pass" not in src
        assert "except Exception: pass" not in src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_precheck_off_grid_detected(
        self, dirty_gds: Path
    ) -> None:
        """预检查检测到 off-grid 顶点。"""
        report = tapeout_precheck(dirty_gds, checks=["grid"])
        assert report.grid_report.total_violations == 2
        # 验证违规坐标
        for v in report.grid_report.violations:
            assert v.x_off_dbu == 2

    def test_precheck_then_clip(self, dirty_gds: Path, tmp_path: Path) -> None:
        """预检查后裁剪（修复 off-grid 后重检）。"""
        from polaris.verification.gdsii_clip_tool import clip_gdsii

        # 裁剪掉 CHILD 区域，只保留 TOP
        out = tmp_path / "clipped.gds"
        clip_gdsii(dirty_gds, out, (0.0, 0.0, 15.0, 10.0))
        # 裁剪后重新预检查
        report = tapeout_precheck(out, checks=["grid"])
        # TOP 三角形 on-grid，应通过
        assert report.passed is True
        assert report.error_count == 0

    def test_precheck_then_flatten(self, dirty_gds: Path, tmp_path: Path) -> None:
        """预检查后扁平化。"""
        from polaris.verification.gdsii_flattener import flatten_gdsii

        flat_out = tmp_path / "flat.gds"
        flatten_gdsii(dirty_gds, flat_out, levels=-1, prune=True)
        # 扁平后预检查，grid 仍应失败（off-grid 保留）
        report = tapeout_precheck(flat_out, checks=["grid"])
        assert report.passed is False
        assert report.error_count == 2

    def test_precheck_hierarchy_no_circular(
        self, dirty_gds: Path
    ) -> None:
        """层次检查无循环引用。"""
        report = tapeout_precheck(dirty_gds, checks=["hierarchy"])
        assert report.hierarchy_report.has_circular_reference is False
        assert report.hierarchy_report.total_cell_count == 2

    def test_precheck_clean_gds_all_pass(
        self, clean_gds: Path
    ) -> None:
        """干净 GDSII 所有检查通过。"""
        report = tapeout_precheck(clean_gds)
        assert report.grid_passed is True
        assert report.health_passed is True
        assert report.hierarchy_passed is True
        assert report.passed is True


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """TapeoutReport 数据类测试。"""

    def test_fields_complete(self) -> None:
        """TapeoutReport 字段完整。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(TapeoutReport)}
        expected = {
            "file_path",
            "dbu",
            "top_cell_name",
            "checks_run",
            "grid_report",
            "health_report",
            "hierarchy_report",
            "passed",
            "grid_passed",
            "health_passed",
            "hierarchy_passed",
            "error_count",
            "warning_count",
        }
        assert field_names == expected

    def test_construction(self) -> None:
        """TapeoutReport 可正常构造。"""
        report = TapeoutReport(
            file_path="in.gds",
            dbu=0.001,
            top_cell_name="TOP",
            checks_run=["grid"],
            passed=True,
            error_count=0,
        )
        assert report.file_path == "in.gds"
        assert report.dbu == 0.001
        assert report.checks_run == ["grid"]

    def test_repr(self) -> None:
        """TapeoutReport repr 可用。"""
        report = TapeoutReport(file_path="a")
        r = repr(report)
        assert "TapeoutReport" in r
        assert "file_path='a'" in r

    def test_equality(self) -> None:
        """TapeoutReport 相等比较。"""
        r1 = TapeoutReport(file_path="a")
        r2 = TapeoutReport(file_path="a")
        assert r1 == r2
        r3 = TapeoutReport(file_path="b")
        assert r1 != r3
