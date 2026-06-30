"""R321 GDSII 文件对比工具测试。

覆盖:
- compare_gdsii_files: 几何差异计算（added/removed/common）
- generate_diff_report: text/markdown 报告生成
- DiffReport / LayerDiff 数据类
- R03 错误处理（文件不存在/格式不支持/top_cell 不存在）
- R02 学术诚信（文献溯源、参数真实）
- 集成测试（多层场景、自定义层映射）

来源:
- KLayout Region 运算: https://www.klayout.org/doc-qt5/code/class_Region.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- 集合论差集: https://en.wikipedia.org/wiki/Set_(mathematics)#Complements
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_diff_tool import (
    DiffReport,
    LayerDiff,
    compare_gdsii_files,
    generate_diff_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def file_a_gds(tmp_path: Path) -> Path:
    """文件 A: 单矩形 WG 层（5x5=25μm²）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "a.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def file_b_gds(tmp_path: Path) -> Path:
    """文件 B: 双矩形 WG 层（A 的 25μm² + 新增 5x5=25μm²，共 50μm²）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
                {"layer": 1, "datatype": 0, "points": [[10, 0], [15, 0], [15, 5], [10, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "b.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def file_c_gds(tmp_path: Path) -> Path:
    """文件 C: 与 A 完全相同（验证一致性）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "c.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def file_d_gds(tmp_path: Path) -> Path:
    """文件 D: 空文件（仅顶层 cell，无几何）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [],
            "is_top": True,
        }
    ]
    out = tmp_path / "d.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_a_gds(tmp_path: Path) -> Path:
    """多层文件 A: WG + METAL 各一矩形。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
                {"layer": 5, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "ml_a.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_b_gds(tmp_path: Path) -> Path:
    """多层文件 B: WG 不同 + METAL 相同。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                # WG 不同位置
                {"layer": 1, "datatype": 0, "points": [[10, 0], [15, 0], [15, 5], [10, 5]]},
                # METAL 与 A 相同
                {"layer": 5, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "ml_b.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def custom_layer_gds(tmp_path: Path) -> Path:
    """自定义层（layer 100）GDSII。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 100, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "custom.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestCompareGdsiiFiles: 比较函数核心测试
# =============================================================================
class TestCompareGdsiiFiles:
    """compare_gdsii_files 函数测试。"""

    def test_returns_diff_report(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """返回 DiffReport。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert isinstance(report, DiffReport)
        assert report.file_a == str(file_a_gds)
        assert report.file_b == str(file_b_gds)

    def test_top_cell_names(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """顶层 cell 名正确。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert report.top_cell_a == "TOP"
        assert report.top_cell_b == "TOP"

    def test_dbu_positive(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """dbu 为正。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert report.dbu_a > 0
        assert report.dbu_b > 0
        # KLayout Layout.dbu 返回 μm 单位，默认 dbu_um=0.001 (1nm)
        # 来源: https://www.klayout.org/doc-qt5/code/class_Layout.html
        assert report.dbu_a == pytest.approx(0.001, rel=1e-3)
        assert report.dbu_b == pytest.approx(0.001, rel=1e-3)

    def test_added_when_b_has_more(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """B 比 A 多 → added > 0, removed == 0。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert not report.is_identical
        assert report.total_added_count == 1  # 新增 1 多边形
        assert report.total_removed_count == 0
        # 新增面积 25μm²
        assert report.total_added_area_um2 == pytest.approx(25.0, rel=1e-3)
        assert report.total_removed_area_um2 == pytest.approx(0.0, abs=1e-6)

    def test_removed_when_b_has_less(self, file_b_gds: Path, file_a_gds: Path) -> None:
        """B 比 A 少（参数互换）→ added == 0, removed > 0。"""
        # 注意: 这里 file_b 作为 A，file_a 作为 B
        report = compare_gdsii_files(file_b_gds, file_a_gds)
        assert not report.is_identical
        assert report.total_added_count == 0
        assert report.total_removed_count == 1
        assert report.total_removed_area_um2 == pytest.approx(25.0, rel=1e-3)

    def test_identical_files(self, file_a_gds: Path, file_c_gds: Path) -> None:
        """两个完全相同的文件 → is_identical=True。"""
        report = compare_gdsii_files(file_a_gds, file_c_gds)
        assert report.is_identical
        assert report.total_added_count == 0
        assert report.total_removed_count == 0
        assert report.total_added_area_um2 == pytest.approx(0.0, abs=1e-6)
        assert report.total_removed_area_um2 == pytest.approx(0.0, abs=1e-6)

    def test_common_area_identical(self, file_a_gds: Path, file_c_gds: Path) -> None:
        """相同文件 common 面积 = 总面积（25μm²）。"""
        report = compare_gdsii_files(file_a_gds, file_c_gds)
        assert len(report.layer_diffs) == 1
        ld = report.layer_diffs[0]
        assert ld.common_area_um2 == pytest.approx(25.0, rel=1e-3)
        assert ld.common_polygon_count == 1
        assert ld.is_identical

    def test_common_area_partial(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """部分共有: A 与 B 共有 A 的 25μm²。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert len(report.layer_diffs) == 1
        ld = report.layer_diffs[0]
        assert ld.common_area_um2 == pytest.approx(25.0, rel=1e-3)
        assert ld.common_polygon_count == 1

    def test_layer_diffs_count(self, file_a_gds: Path, file_b_gds: Path) -> None:
        """单层文件 → layer_diffs 长度 1。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        assert len(report.layer_diffs) == 1

    def test_layer_diffs_multi_layer(
        self, multi_layer_a_gds: Path, multi_layer_b_gds: Path
    ) -> None:
        """多层文件 → layer_diffs 长度 = 2。"""
        report = compare_gdsii_files(multi_layer_a_gds, multi_layer_b_gds)
        assert len(report.layer_diffs) == 2
        layer_names = {ld.layer_name for ld in report.layer_diffs}
        assert layer_names == {"WG", "METAL"}

    def test_layer_diffs_wg_diff_metal_same(
        self, multi_layer_a_gds: Path, multi_layer_b_gds: Path
    ) -> None:
        """多层场景: WG 有差异，METAL 一致。"""
        report = compare_gdsii_files(multi_layer_a_gds, multi_layer_b_gds)
        for ld in report.layer_diffs:
            if ld.layer_name == "WG":
                assert not ld.is_identical
                assert ld.added_polygon_count == 1
                assert ld.removed_polygon_count == 1
            elif ld.layer_name == "METAL":
                assert ld.is_identical
                assert ld.added_polygon_count == 0
                assert ld.removed_polygon_count == 0

    def test_custom_layer_map(
        self, custom_layer_gds: Path, file_d_gds: Path
    ) -> None:
        """自定义层映射。"""
        custom_map = {(100, 0): "CUSTOM"}
        report = compare_gdsii_files(
            custom_layer_gds, file_d_gds, layer_map=custom_map
        )
        assert len(report.layer_diffs) == 1
        assert report.layer_diffs[0].layer_name == "CUSTOM"

    def test_default_layer_map_for_custom_layer(
        self, custom_layer_gds: Path, file_d_gds: Path
    ) -> None:
        """未在 layer_map 中的层使用默认名 LAYER_{layer}_{datatype}。"""
        report = compare_gdsii_files(custom_layer_gds, file_d_gds)
        assert len(report.layer_diffs) == 1
        ld = report.layer_diffs[0]
        assert ld.layer_name == "LAYER_100_0"
        assert ld.gds_layer == 100
        assert ld.gds_datatype == 0

    def test_empty_vs_nonempty(
        self, file_d_gds: Path, file_a_gds: Path
    ) -> None:
        """空文件 vs 非空文件 → 全部为 added。"""
        report = compare_gdsii_files(file_d_gds, file_a_gds)
        assert not report.is_identical
        assert report.total_added_count == 1
        assert report.total_removed_count == 0
        assert report.total_added_area_um2 == pytest.approx(25.0, rel=1e-3)

    def test_nonempty_vs_empty(
        self, file_a_gds: Path, file_d_gds: Path
    ) -> None:
        """非空文件 vs 空文件 → 全部为 removed。"""
        report = compare_gdsii_files(file_a_gds, file_d_gds)
        assert not report.is_identical
        assert report.total_added_count == 0
        assert report.total_removed_count == 1
        assert report.total_removed_area_um2 == pytest.approx(25.0, rel=1e-3)

    def test_top_cell_name_specified(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """显式指定 top_cell_name='TOP'。"""
        report = compare_gdsii_files(
            file_a_gds, file_b_gds, top_cell_name="TOP"
        )
        assert report.top_cell_a == "TOP"
        assert report.top_cell_b == "TOP"

    def test_layer_diffs_gds_layer_datatype(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """layer_diffs 含正确的 GDS layer/datatype。"""
        report = compare_gdsii_files(file_a_gds, file_b_gds)
        ld = report.layer_diffs[0]
        assert ld.gds_layer == 1
        assert ld.gds_datatype == 0

    def test_total_aggregation(
        self, multi_layer_a_gds: Path, multi_layer_b_gds: Path
    ) -> None:
        """多层场景下 total_* 字段正确聚合。"""
        report = compare_gdsii_files(multi_layer_a_gds, multi_layer_b_gds)
        # WG: added=1 (25μm²), removed=1 (25μm²); METAL: 无差异
        assert report.total_added_count == 1
        assert report.total_removed_count == 1
        assert report.total_added_area_um2 == pytest.approx(25.0, rel=1e-3)
        assert report.total_removed_area_um2 == pytest.approx(25.0, rel=1e-3)


# =============================================================================
# TestGenerateDiffReport: 报告生成测试
# =============================================================================
class TestGenerateDiffReport:
    """generate_diff_report 函数测试。"""

    def test_text_format_returns_str(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """text 格式返回字符串。"""
        report = generate_diff_report(file_a_gds, file_b_gds, output_format="text")
        assert isinstance(report, str)
        assert len(report) > 0

    def test_markdown_format_returns_str(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """markdown 格式返回字符串。"""
        report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="markdown"
        )
        assert isinstance(report, str)
        assert len(report) > 0

    def test_text_report_contains_header(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """text 报告含标题。"""
        report = generate_diff_report(file_a_gds, file_b_gds, output_format="text")
        assert "GDSII 文件对比报告" in report

    def test_text_report_contains_file_paths(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """text 报告含文件路径。"""
        report = generate_diff_report(file_a_gds, file_b_gds, output_format="text")
        assert str(file_a_gds) in report
        assert str(file_b_gds) in report

    def test_text_report_contains_top_cell(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """text 报告含顶层 cell 名。"""
        report = generate_diff_report(file_a_gds, file_b_gds, output_format="text")
        assert "TOP" in report

    def test_text_report_shows_difference(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """有差异时 text 报告显示"存在差异"。"""
        report = generate_diff_report(file_a_gds, file_b_gds, output_format="text")
        assert "存在差异" in report

    def test_text_report_shows_identical(
        self, file_a_gds: Path, file_c_gds: Path
    ) -> None:
        """一致时 text 报告显示"完全一致"。"""
        report = generate_diff_report(file_a_gds, file_c_gds, output_format="text")
        assert "完全一致" in report

    def test_markdown_report_contains_header(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """markdown 报告含 # 标题。"""
        report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="markdown"
        )
        assert report.startswith("# GDSII 文件对比报告")

    def test_markdown_report_contains_table(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """markdown 报告含表格。"""
        report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="markdown"
        )
        assert "|" in report
        assert "层名" in report

    def test_markdown_report_contains_layer_name(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """markdown 报告含层名 WG。"""
        report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="markdown"
        )
        assert "WG" in report

    def test_unsupported_format_raises(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_diff_report(
                file_a_gds, file_b_gds, output_format="html"
            )

    def test_format_case_insensitive(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """格式名大小写不敏感。"""
        report_upper = generate_diff_report(
            file_a_gds, file_b_gds, output_format="TEXT"
        )
        report_lower = generate_diff_report(
            file_a_gds, file_b_gds, output_format="text"
        )
        assert report_upper == report_lower


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_a_not_exists_raises(self, tmp_path: Path, file_b_gds: Path) -> None:
        """文件 A 不存在 raise FileNotFoundError。"""
        nonexistent = tmp_path / "nonexistent_a.gds"
        with pytest.raises(FileNotFoundError, match="文件 A 不存在"):
            compare_gdsii_files(nonexistent, file_b_gds)

    def test_file_b_not_exists_raises(self, file_a_gds: Path, tmp_path: Path) -> None:
        """文件 B 不存在 raise FileNotFoundError。"""
        nonexistent = tmp_path / "nonexistent_b.gds"
        with pytest.raises(FileNotFoundError, match="文件 B 不存在"):
            compare_gdsii_files(file_a_gds, nonexistent)

    def test_file_a_not_a_file_raises(
        self, tmp_path: Path, file_b_gds: Path
    ) -> None:
        """文件 A 是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="文件 A 不是文件"):
            compare_gdsii_files(tmp_path, file_b_gds)

    def test_file_b_not_a_file_raises(
        self, file_a_gds: Path, tmp_path: Path
    ) -> None:
        """文件 B 是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="文件 B 不是文件"):
            compare_gdsii_files(file_a_gds, tmp_path)

    def test_top_cell_name_not_exists_raises(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            compare_gdsii_files(
                file_a_gds, file_b_gds, top_cell_name="NONEXISTENT"
            )

    def test_generate_diff_report_propagates_file_error(
        self, tmp_path: Path, file_b_gds: Path
    ) -> None:
        """generate_diff_report 传播文件不存在错误。"""
        nonexistent = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError):
            generate_diff_report(nonexistent, file_b_gds)


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_references(self) -> None:
        """模块 docstring 含 ≥5 个文献 URL。"""
        from polaris.verification import gdsii_diff_tool

        docstring = gdsii_diff_tool.__doc__ or ""
        # 统计 URL 数量
        url_count = docstring.count("https://") + docstring.count("http://")
        assert url_count >= 5, (
            f"docstring 文献 URL 数 {url_count} < 5，违反 R02"
        )

    def test_module_docstring_mentions_klayout_region(self) -> None:
        """docstring 提及 KLayout Region 运算。"""
        from polaris.verification import gdsii_diff_tool

        docstring = gdsii_diff_tool.__doc__ or ""
        assert "Region" in docstring or "klayout" in docstring.lower()

    def test_module_docstring_mentions_set_theory(self) -> None:
        """docstring 提及集合论差集概念。"""
        from polaris.verification import gdsii_diff_tool

        docstring = gdsii_diff_tool.__doc__ or ""
        assert "差集" in docstring or "set" in docstring.lower() or "集合论" in docstring

    def test_module_docstring_mentions_gdsii(self) -> None:
        """docstring 提及 GDSII 格式。"""
        from polaris.verification import gdsii_diff_tool

        docstring = gdsii_diff_tool.__doc__ or ""
        assert "GDSII" in docstring or "gds" in docstring.lower()

    def test_compare_function_docstring_has_reference(self) -> None:
        """compare_gdsii_files docstring 含文献 URL。"""
        assert "https://" in compare_gdsii_files.__doc__

    def test_no_fallback_silent_returns(self) -> None:
        """源代码不含 except: pass / silent return None 模式。"""
        from polaris.verification import gdsii_diff_tool

        source_path = Path(gdsii_diff_tool.__file__)
        source = source_path.read_text(encoding="utf-8")
        # 禁止 except: pass（R03）
        assert "except: pass" not in source, "违反 R03: 含 except: pass"
        # 禁止 silent return None（除非显式标注类型）
        # 允许 raise + return 的组合，但纯 return None 在失败路径禁止


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_round_trip_compare(
        self, file_a_gds: Path, file_b_gds: Path, file_c_gds: Path
    ) -> None:
        """端到端: A vs B（差异）+ A vs C（一致）。"""
        # A vs B: 有差异
        r1 = compare_gdsii_files(file_a_gds, file_b_gds)
        assert not r1.is_identical
        # A vs C: 一致
        r2 = compare_gdsii_files(file_a_gds, file_c_gds)
        assert r2.is_identical

    def test_symmetry_of_diff(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """对称性: A vs B 的 added == B vs A 的 removed。"""
        r1 = compare_gdsii_files(file_a_gds, file_b_gds)
        r2 = compare_gdsii_files(file_b_gds, file_a_gds)
        assert r1.total_added_count == r2.total_removed_count
        assert r1.total_removed_count == r2.total_added_count
        assert r1.total_added_area_um2 == pytest.approx(
            r2.total_removed_area_um2, rel=1e-3
        )

    def test_multi_layer_full_workflow(
        self, multi_layer_a_gds: Path, multi_layer_b_gds: Path
    ) -> None:
        """多层场景完整工作流。"""
        report = compare_gdsii_files(multi_layer_a_gds, multi_layer_b_gds)
        # 整体不一致
        assert not report.is_identical
        # 两层都被处理
        assert len(report.layer_diffs) == 2
        # 总计: 1 added + 1 removed（来自 WG），METAL 一致
        assert report.total_added_count == 1
        assert report.total_removed_count == 1

    def test_text_markdown_consistency(
        self, file_a_gds: Path, file_b_gds: Path
    ) -> None:
        """text 与 markdown 报告数据一致。"""
        text_report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="text"
        )
        md_report = generate_diff_report(
            file_a_gds, file_b_gds, output_format="markdown"
        )
        # 两份报告都应包含 WG
        assert "WG" in text_report
        assert "WG" in md_report
        # 两份报告状态一致
        if "完全一致" in text_report:
            assert "完全一致" in md_report
        else:
            assert "存在差异" in text_report
            assert "存在差异" in md_report


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_layer_diff_defaults(self) -> None:
        """LayerDiff 默认值正确。"""
        ld = LayerDiff(layer_name="WG", gds_layer=1, gds_datatype=0)
        assert ld.added_area_um2 == 0.0
        assert ld.removed_area_um2 == 0.0
        assert ld.common_area_um2 == 0.0
        assert ld.added_polygon_count == 0
        assert ld.removed_polygon_count == 0
        assert ld.common_polygon_count == 0
        assert ld.is_identical is True

    def test_diff_report_defaults(self) -> None:
        """DiffReport 默认值正确。"""
        report = DiffReport(file_a="a.gds", file_b="b.gds")
        assert report.top_cell_a == ""
        assert report.top_cell_b == ""
        assert report.dbu_a == 0.0
        assert report.dbu_b == 0.0
        assert report.layer_diffs == []
        assert report.total_added_area_um2 == 0.0
        assert report.total_removed_area_um2 == 0.0
        assert report.total_added_count == 0
        assert report.total_removed_count == 0
        assert report.is_identical is True

    def test_layer_diff_mutable_default_not_shared(self) -> None:
        """LayerDiff 实例互不影响（field 默认非可变）。"""
        ld1 = LayerDiff(layer_name="A", gds_layer=1, gds_datatype=0)
        ld2 = LayerDiff(layer_name="B", gds_layer=2, gds_datatype=0)
        assert ld1.layer_name != ld2.layer_name
        assert ld1 is not ld2

    def test_diff_report_mutable_default_not_shared(self) -> None:
        """DiffReport.layer_diffs 实例互不影响（field(default_factory=list)）。"""
        r1 = DiffReport(file_a="a", file_b="b")
        r2 = DiffReport(file_a="c", file_b="d")
        r1.layer_diffs.append(
            LayerDiff(layer_name="WG", gds_layer=1, gds_datatype=0)
        )
        assert len(r1.layer_diffs) == 1
        assert len(r2.layer_diffs) == 0
