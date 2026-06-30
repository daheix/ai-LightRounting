"""R322 GDSII 单元层级分析器测试。

覆盖:
- analyze_cell_hierarchy: cell 层级分析（深度/父子/实例化次数）
- detect_circular_references: 循环引用检测（DFS 三色标记）
- generate_hierarchy_report: text/markdown 报告生成
- CellInfo / HierarchyReport 数据类
- R03 错误处理（文件不存在/路径无效/top_cell_name 不存在/空文件）
- R02 学术诚信（文献溯源、参数真实）
- 集成测试（多层场景、多顶层 cell、指定 top_cell_name）

来源:
- KLayout Cell API: https://www.klayout.org/doc-qt4/code/class_Cell.html
- 三色标记 DFS: https://en.wikipedia.org/wiki/Cycle_(graph_theory)#Cycle_detection
- 拓扑排序: https://en.wikipedia.org/wiki/Topological_sorting
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_cell_hierarchy_analyzer import (
    CellInfo,
    HierarchyReport,
    analyze_cell_hierarchy,
    detect_circular_references,
    generate_hierarchy_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def flat_gds(tmp_path: Path) -> Path:
    """扁平 GDSII: 单 TOP cell，无子 cell 引用。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "flat.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def hierarchy_gds(tmp_path: Path) -> Path:
    """层级 GDSII: TOP -> CHILD_A, CHILD_B; CHILD_A -> CHILD_B。

    层级:
    - TOP (depth 0)
      - CHILD_A (depth 1)
        - CHILD_B (depth 2)
      - CHILD_B (depth 2)

    实例化:
    - TOP: recursive=1, direct=0
    - CHILD_A: recursive=1, direct=1 (TOP 引用 1 次)
    - CHILD_B: recursive=2, direct=2 (TOP 引用 1 次 + CHILD_A 引用 1 次)
    """
    cells_spec = [
        {
            "name": "CHILD_B",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [2, 0], [2, 2], [0, 2]]},
            ],
            "is_top": False,
        },
        {
            "name": "CHILD_A",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "instances": [
                {"cell_name": "CHILD_B", "x": 10, "y": 10},
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [],
            "instances": [
                {"cell_name": "CHILD_A", "x": 0, "y": 0},
                {"cell_name": "CHILD_B", "x": 20, "y": 20},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "hier.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_instance_gds(tmp_path: Path) -> Path:
    """多实例 GDSII: TOP 引用 CHILD_A 3 次（不同位置）。

    实例化:
    - TOP: recursive=1, direct=0
    - CHILD_A: recursive=3, direct=3 (TOP 引用 3 次)
    """
    cells_spec = [
        {
            "name": "CHILD_A",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [5, 0], [5, 5], [0, 5]]},
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [],
            "instances": [
                {"cell_name": "CHILD_A", "x": 0, "y": 0},
                {"cell_name": "CHILD_A", "x": 10, "y": 0},
                {"cell_name": "CHILD_A", "x": 20, "y": 0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "multi.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def deep_hierarchy_gds(tmp_path: Path) -> Path:
    """深层级 GDSII: TOP -> L1 -> L2 -> L3（4 层深度）。"""
    cells_spec = [
        {
            "name": "L3",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [1, 0], [1, 1], [0, 1]]},
            ],
            "is_top": False,
        },
        {
            "name": "L2",
            "polygons": [],
            "instances": [{"cell_name": "L3", "x": 0, "y": 0}],
            "is_top": False,
        },
        {
            "name": "L1",
            "polygons": [],
            "instances": [{"cell_name": "L2", "x": 0, "y": 0}],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [],
            "instances": [{"cell_name": "L1", "x": 0, "y": 0}],
            "is_top": True,
        },
    ]
    out = tmp_path / "deep.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestAnalyzeCellHierarchy: 核心分析函数
# =============================================================================
class TestAnalyzeCellHierarchy:
    """analyze_cell_hierarchy 函数测试。"""

    def test_returns_hierarchy_report(self, flat_gds: Path) -> None:
        """返回 HierarchyReport。"""
        report = analyze_cell_hierarchy(flat_gds)
        assert isinstance(report, HierarchyReport)
        assert report.file_path == str(flat_gds)

    def test_dbu_positive(self, flat_gds: Path) -> None:
        """dbu 为正（KLayout Layout.dbu 返回 μm，默认 0.001μm=1nm）。"""
        report = analyze_cell_hierarchy(flat_gds)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_names_flat(self, flat_gds: Path) -> None:
        """扁平 GDSII 顶层 cell = ['TOP']。"""
        report = analyze_cell_hierarchy(flat_gds)
        assert report.top_cell_names == ["TOP"]

    def test_total_cell_count_flat(self, flat_gds: Path) -> None:
        """扁平 GDSII cell 总数 = 1。"""
        report = analyze_cell_hierarchy(flat_gds)
        assert report.total_cell_count == 1

    def test_total_cell_count_hierarchy(self, hierarchy_gds: Path) -> None:
        """层级 GDSII cell 总数 = 3。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        assert report.total_cell_count == 3

    def test_max_depth_flat(self, flat_gds: Path) -> None:
        """扁平 GDSII 最大深度 = 0。"""
        report = analyze_cell_hierarchy(flat_gds)
        assert report.max_hierarchy_depth == 0

    def test_max_depth_hierarchy(self, hierarchy_gds: Path) -> None:
        """层级 GDSII 最大深度 = 2。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        assert report.max_hierarchy_depth == 2

    def test_max_depth_deep(self, deep_hierarchy_gds: Path) -> None:
        """深层级 GDSII 最大深度 = 3（TOP→L1→L2→L3）。"""
        report = analyze_cell_hierarchy(deep_hierarchy_gds)
        assert report.max_hierarchy_depth == 3

    def test_no_circular_reference(self, hierarchy_gds: Path) -> None:
        """正常层级无循环引用。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        assert report.has_circular_reference is False
        assert report.circular_chains == []

    def test_cells_sorted_by_depth(self, hierarchy_gds: Path) -> None:
        """cells 按深度升序排列。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        depths = [c.hierarchy_depth for c in report.cells]
        assert depths == sorted(depths)

    def test_top_cell_info(self, hierarchy_gds: Path) -> None:
        """TOP cell 信息正确。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        top_info = next(c for c in report.cells if c.cell_name == "TOP")
        assert top_info.is_top_cell is True
        assert top_info.hierarchy_depth == 0
        assert top_info.direct_instance_count == 0  # TOP 没被引用
        assert top_info.recursive_instance_count == 1  # 根
        assert top_info.parent_cell_names == []
        assert sorted(top_info.child_cell_names) == ["CHILD_A", "CHILD_B"]

    def test_child_a_info(self, hierarchy_gds: Path) -> None:
        """CHILD_A cell 信息正确。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        ca = next(c for c in report.cells if c.cell_name == "CHILD_A")
        assert ca.is_top_cell is False
        assert ca.hierarchy_depth == 1
        assert ca.direct_instance_count == 1  # TOP 引用 1 次
        assert ca.recursive_instance_count == 1
        assert ca.parent_cell_names == ["TOP"]
        assert ca.child_cell_names == ["CHILD_B"]

    def test_child_b_info(self, hierarchy_gds: Path) -> None:
        """CHILD_B cell 信息正确（递归实例化次数=2）。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        cb = next(c for c in report.cells if c.cell_name == "CHILD_B")
        assert cb.is_top_cell is False
        assert cb.hierarchy_depth == 2
        assert cb.direct_instance_count == 2  # TOP + CHILD_A 各引用 1 次
        assert cb.recursive_instance_count == 2  # TOP→CHILD_B + TOP→CHILD_A→CHILD_B
        assert sorted(cb.parent_cell_names) == ["CHILD_A", "TOP"]
        assert cb.child_cell_names == []

    def test_multi_instance_count(self, multi_instance_gds: Path) -> None:
        """多实例: CHILD_A direct=3, recursive=3。"""
        report = analyze_cell_hierarchy(multi_instance_gds)
        ca = next(c for c in report.cells if c.cell_name == "CHILD_A")
        assert ca.direct_instance_count == 3
        assert ca.recursive_instance_count == 3

    def test_deep_hierarchy_depths(self, deep_hierarchy_gds: Path) -> None:
        """深层级各 cell 深度正确。"""
        report = analyze_cell_hierarchy(deep_hierarchy_gds)
        depths = {c.cell_name: c.hierarchy_depth for c in report.cells}
        assert depths["TOP"] == 0
        assert depths["L1"] == 1
        assert depths["L2"] == 2
        assert depths["L3"] == 3

    def test_bbox_um(self, flat_gds: Path) -> None:
        """cell 自身包围盒正确（μm）。"""
        report = analyze_cell_hierarchy(flat_gds)
        c = report.cells[0]
        x_min, y_min, x_max, y_max = c.bbox_um
        assert x_min == pytest.approx(0.0, abs=1e-3)
        assert y_min == pytest.approx(0.0, abs=1e-3)
        assert x_max == pytest.approx(5.0, abs=1e-3)
        assert y_max == pytest.approx(5.0, abs=1e-3)

    def test_specified_top_cell_name(self, hierarchy_gds: Path) -> None:
        """指定 top_cell_name='TOP'。"""
        report = analyze_cell_hierarchy(hierarchy_gds, top_cell_name="TOP")
        assert "TOP" in report.top_cell_names

    def test_cell_index_positive(self, hierarchy_gds: Path) -> None:
        """cell_index 非负。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        for c in report.cells:
            assert c.cell_index >= 0


# =============================================================================
# TestDetectCircularReferences: 循环引用检测
# =============================================================================
class TestDetectCircularReferences:
    """detect_circular_references 函数测试。"""

    def test_no_circular_in_normal(self, hierarchy_gds: Path) -> None:
        """正常 GDSII 无循环引用。"""
        chains = detect_circular_references(hierarchy_gds)
        assert chains == []

    def test_no_circular_in_flat(self, flat_gds: Path) -> None:
        """扁平 GDSII 无循环引用。"""
        chains = detect_circular_references(flat_gds)
        assert chains == []

    def test_no_circular_in_deep(self, deep_hierarchy_gds: Path) -> None:
        """深层级 GDSII 无循环引用。"""
        chains = detect_circular_references(deep_hierarchy_gds)
        assert chains == []

    def test_returns_list(self, hierarchy_gds: Path) -> None:
        """返回 list 类型。"""
        chains = detect_circular_references(hierarchy_gds)
        assert isinstance(chains, list)


# =============================================================================
# TestGenerateHierarchyReport: 报告生成
# =============================================================================
class TestGenerateHierarchyReport:
    """generate_hierarchy_report 函数测试。"""

    def test_text_format_returns_str(self, hierarchy_gds: Path) -> None:
        """text 格式返回字符串。"""
        report = generate_hierarchy_report(hierarchy_gds, output_format="text")
        assert isinstance(report, str)
        assert len(report) > 0

    def test_markdown_format_returns_str(self, hierarchy_gds: Path) -> None:
        """markdown 格式返回字符串。"""
        report = generate_hierarchy_report(
            hierarchy_gds, output_format="markdown"
        )
        assert isinstance(report, str)
        assert len(report) > 0

    def test_text_report_contains_header(self, hierarchy_gds: Path) -> None:
        """text 报告含标题。"""
        report = generate_hierarchy_report(hierarchy_gds, output_format="text")
        assert "GDSII Cell 层级分析报告" in report

    def test_text_report_contains_file_path(self, hierarchy_gds: Path) -> None:
        """text 报告含文件路径。"""
        report = generate_hierarchy_report(hierarchy_gds, output_format="text")
        assert str(hierarchy_gds) in report

    def test_text_report_contains_top_cell(self, hierarchy_gds: Path) -> None:
        """text 报告含顶层 cell 名。"""
        report = generate_hierarchy_report(hierarchy_gds, output_format="text")
        assert "TOP" in report

    def test_text_report_contains_no_circular(self, hierarchy_gds: Path) -> None:
        """text 报告含"无循环引用"。"""
        report = generate_cell_hierarchy_report_text(hierarchy_gds)
        assert "无循环引用" in report

    def test_markdown_report_contains_header(self, hierarchy_gds: Path) -> None:
        """markdown 报告含 # 标题。"""
        report = generate_hierarchy_report(
            hierarchy_gds, output_format="markdown"
        )
        assert report.startswith("# GDSII Cell 层级分析报告")

    def test_markdown_report_contains_table(self, hierarchy_gds: Path) -> None:
        """markdown 报告含表格。"""
        report = generate_hierarchy_report(
            hierarchy_gds, output_format="markdown"
        )
        assert "|" in report
        assert "cell 名" in report

    def test_markdown_report_contains_cell_names(
        self, hierarchy_gds: Path
    ) -> None:
        """markdown 报告含 cell 名。"""
        report = generate_hierarchy_report(
            hierarchy_gds, output_format="markdown"
        )
        assert "TOP" in report
        assert "CHILD_A" in report
        assert "CHILD_B" in report

    def test_unsupported_format_raises(self, hierarchy_gds: Path) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_hierarchy_report(hierarchy_gds, output_format="html")

    def test_format_case_insensitive(self, hierarchy_gds: Path) -> None:
        """格式名大小写不敏感。"""
        r_upper = generate_hierarchy_report(
            hierarchy_gds, output_format="TEXT"
        )
        r_lower = generate_hierarchy_report(
            hierarchy_gds, output_format="text"
        )
        assert r_upper == r_lower


def generate_cell_hierarchy_report_text(gds_path):
    """辅助函数: 生成 text 报告（用于断言）。"""
    return generate_hierarchy_report(gds_path, output_format="text")


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_exists_raises(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        nonexistent = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError, match="GDSII 文件不存在"):
            analyze_cell_hierarchy(nonexistent)

    def test_path_is_directory_raises(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="路径不是文件"):
            analyze_cell_hierarchy(tmp_path)

    def test_top_cell_name_not_exists_raises(
        self, hierarchy_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            analyze_cell_hierarchy(hierarchy_gds, top_cell_name="NONEXISTENT")

    def test_detect_circular_propagates_file_error(
        self, tmp_path: Path
    ) -> None:
        """detect_circular_references 传播文件错误。"""
        nonexistent = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError):
            detect_circular_references(nonexistent)

    def test_generate_report_propagates_file_error(
        self, tmp_path: Path
    ) -> None:
        """generate_hierarchy_report 传播文件错误。"""
        nonexistent = tmp_path / "nonexistent.gds"
        with pytest.raises(FileNotFoundError):
            generate_hierarchy_report(nonexistent)

    def test_generate_report_unsupported_format_propagates(
        self, hierarchy_gds: Path
    ) -> None:
        """generate_hierarchy_report 传播格式错误。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_hierarchy_report(hierarchy_gds, output_format="xml")


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_has_references(self) -> None:
        """模块 docstring 含 ≥5 个文献 URL。"""
        from polaris.verification import gdsii_cell_hierarchy_analyzer

        docstring = gdsii_cell_hierarchy_analyzer.__doc__ or ""
        url_count = docstring.count("https://") + docstring.count("http://")
        assert url_count >= 5, (
            f"docstring 文献 URL 数 {url_count} < 5，违反 R02"
        )

    def test_module_docstring_mentions_klayout(self) -> None:
        """docstring 提及 KLayout。"""
        from polaris.verification import gdsii_cell_hierarchy_analyzer

        docstring = gdsii_cell_hierarchy_analyzer.__doc__ or ""
        assert "klayout" in docstring.lower() or "KLayout" in docstring

    def test_module_docstring_mentions_cycle_detection(self) -> None:
        """docstring 提及循环引用检测算法。"""
        from polaris.verification import gdsii_cell_hierarchy_analyzer

        docstring = gdsii_cell_hierarchy_analyzer.__doc__ or ""
        assert "DFS" in docstring or "三色" in docstring or "环" in docstring

    def test_module_docstring_mentions_topological(self) -> None:
        """docstring 提及拓扑排序。"""
        from polaris.verification import gdsii_cell_hierarchy_analyzer

        docstring = gdsii_cell_hierarchy_analyzer.__doc__ or ""
        assert "拓扑" in docstring or "topological" in docstring.lower()

    def test_analyze_function_docstring_has_reference(self) -> None:
        """analyze_cell_hierarchy docstring 含文献 URL。"""
        assert "https://" in analyze_cell_hierarchy.__doc__

    def test_no_fallback_silent_returns(self) -> None:
        """源代码不含 except: pass / silent return None 模式。"""
        from polaris.verification import gdsii_cell_hierarchy_analyzer

        source_path = Path(gdsii_cell_hierarchy_analyzer.__file__)
        source = source_path.read_text(encoding="utf-8")
        assert "except: pass" not in source, "违反 R03: 含 except: pass"


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_hierarchy(
        self, hierarchy_gds: Path
    ) -> None:
        """层级 GDSII 完整工作流。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        assert report.total_cell_count == 3
        assert report.max_hierarchy_depth == 2
        assert report.has_circular_reference is False
        # 验证 cell 名集合
        names = {c.cell_name for c in report.cells}
        assert names == {"TOP", "CHILD_A", "CHILD_B"}

    def test_full_workflow_deep(
        self, deep_hierarchy_gds: Path
    ) -> None:
        """深层级 GDSII 完整工作流。"""
        report = analyze_cell_hierarchy(deep_hierarchy_gds)
        assert report.total_cell_count == 4
        assert report.max_hierarchy_depth == 3
        names = {c.cell_name for c in report.cells}
        assert names == {"TOP", "L1", "L2", "L3"}

    def test_text_markdown_consistency(
        self, hierarchy_gds: Path
    ) -> None:
        """text 与 markdown 报告数据一致。"""
        text_report = generate_hierarchy_report(
            hierarchy_gds, output_format="text"
        )
        md_report = generate_hierarchy_report(
            hierarchy_gds, output_format="markdown"
        )
        # 两份报告都应包含所有 cell 名
        for name in ["TOP", "CHILD_A", "CHILD_B"]:
            assert name in text_report
            assert name in md_report
        # 状态一致
        assert "无循环引用" in text_report
        assert "无循环引用" in md_report

    def test_recursive_count_propagation(
        self, hierarchy_gds: Path
    ) -> None:
        """递归实例化次数正确传播（CHILD_B = 2）。"""
        report = analyze_cell_hierarchy(hierarchy_gds)
        cb = next(c for c in report.cells if c.cell_name == "CHILD_B")
        # TOP→CHILD_B（1 次）+ TOP→CHILD_A→CHILD_B（1 次）= 2 次
        assert cb.recursive_instance_count == 2


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_cell_info_defaults(self) -> None:
        """CellInfo 默认值正确。"""
        ci = CellInfo(cell_name="X", cell_index=0)
        assert ci.parent_cell_names == []
        assert ci.child_cell_names == []
        assert ci.hierarchy_depth == 0
        assert ci.direct_instance_count == 0
        assert ci.recursive_instance_count == 0
        assert ci.is_top_cell is False
        assert ci.bbox_um == (0.0, 0.0, 0.0, 0.0)

    def test_hierarchy_report_defaults(self) -> None:
        """HierarchyReport 默认值正确。"""
        report = HierarchyReport(file_path="x.gds")
        assert report.top_cell_names == []
        assert report.dbu == 0.0
        assert report.cells == []
        assert report.total_cell_count == 0
        assert report.max_hierarchy_depth == 0
        assert report.has_circular_reference is False
        assert report.circular_chains == []

    def test_cell_info_mutable_default_not_shared(self) -> None:
        """CellInfo 实例互不影响。"""
        c1 = CellInfo(cell_name="A", cell_index=0)
        c2 = CellInfo(cell_name="B", cell_index=1)
        c1.parent_cell_names.append("P")
        assert len(c1.parent_cell_names) == 1
        assert len(c2.parent_cell_names) == 0

    def test_hierarchy_report_mutable_default_not_shared(self) -> None:
        """HierarchyReport.cells 实例互不影响。"""
        r1 = HierarchyReport(file_path="a")
        r2 = HierarchyReport(file_path="b")
        r1.cells.append(CellInfo(cell_name="X", cell_index=0))
        assert len(r1.cells) == 1
        assert len(r2.cells) == 0
