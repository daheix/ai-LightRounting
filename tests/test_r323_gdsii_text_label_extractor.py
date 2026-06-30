"""R323 GDSII 文本标签提取器测试。

覆盖:
- extract_text_labels: 文本提取
- generate_text_label_report: text/markdown 报告
- layers_to_extract 过滤
- 递归子 cell 中的 text 提取
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- KLayout Shape API: https://www.klayout.org/doc-qt4/code/class_Shape.html
- KLayout Text class: https://www.klayout.de/doc-qt5/code/class_Text.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_text_label_extractor import (
    TextLabel,
    TextLabelReport,
    extract_text_labels,
    generate_text_label_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def single_text_gds(tmp_path: Path) -> Path:
    """创建含单个 TEXT 标签的 GDSII。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "texts": [
                {"layer": 10, "datatype": 0, "string": "device_MZI_1", "x": 5.0, "y": 2.5},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "single.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_text_gds(tmp_path: Path) -> Path:
    """创建含多 TEXT 标签的 GDSII（多层数个标签）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "texts": [
                {"layer": 10, "datatype": 0, "string": "device_MZI_1", "x": 5.0, "y": 2.5},
                {"layer": 11, "datatype": 0, "string": "pin_in", "x": 0.0, "y": 2.5},
                {"layer": 11, "datatype": 0, "string": "pin_out", "x": 10.0, "y": 2.5},
                {"layer": 69, "datatype": 0, "string": "pin_1_opt_in", "x": 0.0, "y": 2.5},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def no_text_gds(tmp_path: Path) -> Path:
    """创建不含任何 TEXT 标签的 GDSII（仅多边形）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "no_text.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def child_cell_text_gds(tmp_path: Path) -> Path:
    """创建子 cell 中含 TEXT 标签的 GDSII（验证递归遍历）。

    结构:
    - TOP cell（含 1 个 polygon 和 1 个 text 在 layer 10）
      - 实例化 CHILD cell
        - CHILD cell 含 1 个 text 在 layer 11
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [],
            "texts": [
                {"layer": 11, "datatype": 0, "string": "child_label", "x": 0.0, "y": 0.0},
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {"layer": 1, "datatype": 0, "points": [[0, 0], [10, 0], [10, 5], [0, 5]]},
            ],
            "texts": [
                {"layer": 10, "datatype": 0, "string": "top_label", "x": 5.0, "y": 2.5},
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 0.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "child_text.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def custom_layer_text_gds(tmp_path: Path) -> Path:
    """创建自定义层 GDSII（layer 100）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [],
            "texts": [
                {"layer": 100, "datatype": 0, "string": "custom", "x": 0.0, "y": 0.0},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "custom.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def empty_text_gds(tmp_path: Path) -> Path:
    """创建空字符串 text 的 GDSII。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [],
            "texts": [
                {"layer": 10, "datatype": 0, "string": "", "x": 0.0, "y": 0.0},
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "empty_text.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestExtractTextLabels: 基本提取
# =============================================================================
class TestExtractTextLabels:
    """extract_text_labels 函数测试。"""

    def test_returns_report(self, single_text_gds: Path) -> None:
        """返回 TextLabelReport。"""
        report = extract_text_labels(single_text_gds)
        assert isinstance(report, TextLabelReport)
        assert report.file_path == str(single_text_gds)
        assert report.top_cell_name == "TOP"
        assert report.dbu > 0

    def test_dbu_is_um(self, single_text_gds: Path) -> None:
        """dbu 单位为 μm（KLayout Layout.dbu 返回 μm，默认 0.001 = 1nm）。"""
        report = extract_text_labels(single_text_gds)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_single_text(self, single_text_gds: Path) -> None:
        """提取单个 TEXT 标签。"""
        report = extract_text_labels(single_text_gds)
        assert report.total_count == 1
        lbl = report.labels[0]
        assert lbl.text == "device_MZI_1"
        assert lbl.layer_name == "TEXT"  # SiEPIC (10,0) → TEXT
        assert lbl.gds_layer == 10
        assert lbl.gds_datatype == 0
        assert lbl.x_um == pytest.approx(5.0, abs=1e-3)
        assert lbl.y_um == pytest.approx(2.5, abs=1e-3)
        assert lbl.cell_name == "TOP"

    def test_multi_text_count(self, multi_text_gds: Path) -> None:
        """提取多个 TEXT 标签（4 个）。"""
        report = extract_text_labels(multi_text_gds)
        assert report.total_count == 4

    def test_multi_text_layers(self, multi_text_gds: Path) -> None:
        """多层数量统计正确。

        layer 10 = TEXT × 1
        layer 11 = LABEL × 2
        layer 69 = PIN × 1
        """
        report = extract_text_labels(multi_text_gds)
        assert report.layer_counts.get("TEXT") == 1
        assert report.layer_counts.get("LABEL") == 2
        assert report.layer_counts.get("PIN") == 1

    def test_multi_text_contents(self, multi_text_gds: Path) -> None:
        """提取所有文本内容。"""
        report = extract_text_labels(multi_text_gds)
        texts = {lbl.text for lbl in report.labels}
        assert texts == {"device_MZI_1", "pin_in", "pin_out", "pin_1_opt_in"}

    def test_no_text(self, no_text_gds: Path) -> None:
        """无 TEXT 标签的 GDSII。"""
        report = extract_text_labels(no_text_gds)
        assert report.total_count == 0
        assert report.labels == []
        assert report.layer_counts == {}

    def test_child_cell_text_recursion(self, child_cell_text_gds: Path) -> None:
        """递归提取子 cell 中的 TEXT 标签。

        TOP 含 1 个 text（top_label），CHILD 含 1 个 text（child_label）。
        begin_shapes_rec 应递归遍历所有子 cell 实例。
        """
        report = extract_text_labels(child_cell_text_gds)
        # 应提取出 2 个 text（TOP 自己的 + CHILD 实例中的）
        assert report.total_count == 2
        texts = {lbl.text for lbl in report.labels}
        assert texts == {"top_label", "child_label"}

    def test_child_cell_name(self, child_cell_text_gds: Path) -> None:
        """子 cell 中的 text 应反映其所属 cell 名。

        RecursiveShapeIterator.cell() 返回当前 shape 所在的 cell。
        """
        report = extract_text_labels(child_cell_text_gds)
        # top_label 在 TOP cell，child_label 在 CHILD cell
        cell_names = {lbl.text: lbl.cell_name for lbl in report.labels}
        assert cell_names["top_label"] == "TOP"
        assert cell_names["child_label"] == "CHILD"

    def test_cell_counts(self, child_cell_text_gds: Path) -> None:
        """按 cell 分组计数。"""
        report = extract_text_labels(child_cell_text_gds)
        assert report.cell_counts.get("TOP") == 1
        assert report.cell_counts.get("CHILD") == 1

    def test_custom_layer_name(self, custom_layer_text_gds: Path) -> None:
        """自定义层（不在 SiEPIC 标准层映射中）使用默认名。"""
        report = extract_text_labels(custom_layer_text_gds)
        assert report.total_count == 1
        lbl = report.labels[0]
        assert lbl.gds_layer == 100
        # SiEPIC 标准 layer_map 不含 (100,0)，应使用 LAYER_100_0
        assert lbl.layer_name == "LAYER_100_0"

    def test_custom_layer_map(self, custom_layer_text_gds: Path) -> None:
        """自定义 layer_map 覆盖默认。"""
        custom_map = {(100, 0): "MYLAYER"}
        report = extract_text_labels(
            custom_layer_text_gds, layer_map=custom_map
        )
        assert report.labels[0].layer_name == "MYLAYER"

    def test_layers_to_extract_filter(
        self, multi_text_gds: Path
    ) -> None:
        """layers_to_extract 过滤层（仅提取 LABEL 层）。"""
        report = extract_text_labels(
            multi_text_gds, layers_to_extract=["LABEL"]
        )
        assert report.total_count == 2
        for lbl in report.labels:
            assert lbl.layer_name == "LABEL"

    def test_layers_to_extract_multiple(
        self, multi_text_gds: Path
    ) -> None:
        """layers_to_extract 过滤多层。"""
        report = extract_text_labels(
            multi_text_gds, layers_to_extract=["TEXT", "PIN"]
        )
        assert report.total_count == 2
        layer_names = {lbl.layer_name for lbl in report.labels}
        assert layer_names == {"TEXT", "PIN"}

    def test_layers_to_extract_empty_result(
        self, multi_text_gds: Path
    ) -> None:
        """layers_to_extract 不匹配任何层时返回空。"""
        report = extract_text_labels(
            multi_text_gds, layers_to_extract=["NONEXISTENT"]
        )
        assert report.total_count == 0

    def test_layers_to_extract_unknown_layer_name(
        self, multi_text_gds: Path
    ) -> None:
        """layers_to_extract 含未知层名（无 raise，只是不匹配）。"""
        report = extract_text_labels(
            multi_text_gds, layers_to_extract=["UNKNOWN", "TEXT"]
        )
        # UNKNOWN 不在 layer_map 中，但 TEXT 在
        assert report.total_count == 1
        assert report.labels[0].layer_name == "TEXT"

    def test_top_cell_name_specified(
        self, single_text_gds: Path
    ) -> None:
        """指定 top_cell_name。"""
        report = extract_text_labels(
            single_text_gds, top_cell_name="TOP"
        )
        assert report.top_cell_name == "TOP"

    def test_labels_sorted(self, multi_text_gds: Path) -> None:
        """labels 按层号→datatype→y→x 排序。"""
        report = extract_text_labels(multi_text_gds)
        keys = [
            (lbl.gds_layer, lbl.gds_datatype, lbl.y_um, lbl.x_um)
            for lbl in report.labels
        ]
        assert keys == sorted(keys)

    def test_empty_text_string(self, empty_text_gds: Path) -> None:
        """空字符串 text 也应被提取。"""
        report = extract_text_labels(empty_text_gds)
        assert report.total_count == 1
        assert report.labels[0].text == ""

    def test_text_position_precision(
        self, single_text_gds: Path
    ) -> None:
        """text 位置精度（μm）。"""
        report = extract_text_labels(single_text_gds)
        lbl = report.labels[0]
        # 输入 x=5.0, y=2.5
        assert lbl.x_um == pytest.approx(5.0, abs=1e-3)
        assert lbl.y_um == pytest.approx(2.5, abs=1e-3)


# =============================================================================
# TestGenerateTextLabelReport: 报告生成
# =============================================================================
class TestGenerateTextLabelReport:
    """generate_text_label_report 函数测试。"""

    def test_text_format(self, single_text_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_text_label_report(
            single_text_gds, output_format="text"
        )
        assert isinstance(report, str)
        assert "GDSII 文本标签提取报告" in report
        assert "device_MZI_1" in report
        assert "TOP" in report

    def test_markdown_format(self, single_text_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_text_label_report(
            single_text_gds, output_format="markdown"
        )
        assert isinstance(report, str)
        assert "# GDSII 文本标签提取报告" in report
        assert "device_MZI_1" in report
        assert "|" in report  # markdown 表格

    def test_text_format_contains_counts(
        self, multi_text_gds: Path
    ) -> None:
        """text 报告含层和 cell 计数。"""
        report = generate_text_label_report(
            multi_text_gds, output_format="text"
        )
        assert "按层分组统计" in report
        assert "按 cell 分组统计" in report
        assert "TEXT:" in report
        assert "LABEL:" in report
        assert "PIN:" in report

    def test_markdown_format_contains_tables(
        self, multi_text_gds: Path
    ) -> None:
        """markdown 报告含表格。"""
        report = generate_text_label_report(
            multi_text_gds, output_format="markdown"
        )
        assert "| 层名 | 数量 |" in report
        assert "| cell 名 | 数量 |" in report
        assert "| 文本 | 层名 |" in report

    def test_empty_report(self, no_text_gds: Path) -> None:
        """无 text 时报告正常生成。"""
        report = generate_text_label_report(
            no_text_gds, output_format="text"
        )
        assert "文本标签总数: 0" in report

    def test_layers_to_extract_in_report(
        self, multi_text_gds: Path
    ) -> None:
        """报告内应用 layers_to_extract 过滤。"""
        report = generate_text_label_report(
            multi_text_gds,
            layers_to_extract=["LABEL"],
            output_format="text",
        )
        assert "pin_in" in report
        assert "pin_out" in report
        assert "device_MZI_1" not in report  # TEXT 层被过滤

    def test_invalid_format_raises(
        self, single_text_gds: Path
    ) -> None:
        """不支持的 output_format raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_text_label_report(
                single_text_gds, output_format="json"
            )

    def test_format_case_insensitive(
        self, single_text_gds: Path
    ) -> None:
        """output_format 大小写不敏感。"""
        r1 = generate_text_label_report(
            single_text_gds, output_format="TEXT"
        )
        r2 = generate_text_label_report(
            single_text_gds, output_format="text"
        )
        assert r1 == r2

    def test_report_contains_filename(
        self, single_text_gds: Path
    ) -> None:
        """text 报告含文件路径。"""
        report = generate_text_label_report(
            single_text_gds, output_format="text"
        )
        assert str(single_text_gds) in report

    def test_markdown_contains_dbu(
        self, single_text_gds: Path
    ) -> None:
        """markdown 报告含 dbu。"""
        report = generate_text_label_report(
            single_text_gds, output_format="markdown"
        )
        assert "dbu" in report
        assert "0.001" in report

    def test_text_format_contains_all_labels(
        self, multi_text_gds: Path
    ) -> None:
        """text 报告含所有标签。"""
        report = generate_text_label_report(
            multi_text_gds, output_format="text"
        )
        assert "device_MZI_1" in report
        assert "pin_in" in report
        assert "pin_out" in report
        assert "pin_1_opt_in" in report


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_found_raises(self) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="不存在"):
            extract_text_labels("/nonexistent/file.gds")

    def test_not_a_file_raises(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            extract_text_labels(tmp_path)

    def test_top_cell_not_found_raises(
        self, single_text_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            extract_text_labels(
                single_text_gds, top_cell_name="NONEXISTENT"
            )

    def test_invalid_format_raises(
        self, single_text_gds: Path
    ) -> None:
        """无效 output_format raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_text_label_report(
                single_text_gds, output_format="xml"
            )

    def test_no_silent_fallback_on_invalid_path(self) -> None:
        """无效路径不可静默 fall-back（R03）。

        验证: 不会返回 None/[]，而是 raise。
        """
        try:
            extract_text_labels("/nonexistent/path.gds")
            assert False, "应 raise FileNotFoundError 而非静默通过"
        except FileNotFoundError:
            pass

    def test_layer_counts_type(self, multi_text_gds: Path) -> None:
        """layer_counts 是 dict[str, int]，不是 None。"""
        report = extract_text_labels(multi_text_gds)
        assert isinstance(report.layer_counts, dict)
        assert isinstance(report.cell_counts, dict)
        for v in report.layer_counts.values():
            assert isinstance(v, int)
        for v in report.cell_counts.values():
            assert isinstance(v, int)


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信（R02）
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_contains_klayout_url(self) -> None:
        """模块 docstring 含 KLayout 官方文档 URL。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        assert "klayout.org" in mod.__doc__ or "klayout.de" in mod.__doc__

    def test_docstring_contains_text_class_url(self) -> None:
        """docstring 含 KLayout Text class URL。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        assert "class_Text" in mod.__doc__

    def test_docstring_contains_shape_class_url(self) -> None:
        """docstring 含 KLayout Shape class URL。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        assert "class_Shape" in mod.__doc__

    def test_docstring_contains_siepic_url(self) -> None:
        """docstring 含 SiEPIC PDK URL。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        assert "SiEPIC" in mod.__doc__

    def test_docstring_contains_gdsii_format_url(self) -> None:
        """docstring 含 GDSII 格式说明 URL。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        assert "GDS" in mod.__doc__

    def test_docstring_contains_at_least_5_urls(self) -> None:
        """docstring 含至少 5 个文献 URL（R02）。"""
        from polaris.verification import gdsii_text_label_extractor as mod
        url_count = mod.__doc__.count("http")
        assert url_count >= 5


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_text(self, multi_text_gds: Path) -> None:
        """完整工作流: 提取 → text 报告。"""
        report = extract_text_labels(multi_text_gds)
        assert report.total_count == 4
        text_report = generate_text_label_report(
            multi_text_gds, output_format="text"
        )
        assert "文本标签总数: 4" in text_report

    def test_full_workflow_markdown(
        self, multi_text_gds: Path
    ) -> None:
        """完整工作流: 提取 → markdown 报告。"""
        report = extract_text_labels(multi_text_gds)
        assert report.total_count == 4
        md_report = generate_text_label_report(
            multi_text_gds, output_format="markdown"
        )
        assert md_report.startswith("# GDSII 文本标签提取报告")

    def test_filter_then_report(
        self, multi_text_gds: Path
    ) -> None:
        """过滤后生成报告。"""
        report = generate_text_label_report(
            multi_text_gds,
            layers_to_extract=["PIN"],
            output_format="text",
        )
        assert "pin_1_opt_in" in report
        assert "device_MZI_1" not in report

    def test_child_cell_workflow(
        self, child_cell_text_gds: Path
    ) -> None:
        """子 cell 集成工作流。"""
        report = extract_text_labels(child_cell_text_gds)
        # TOP + CHILD 各 1 个 text
        assert report.total_count == 2
        assert "TOP" in report.cell_counts
        assert "CHILD" in report.cell_counts
        # 报告中应包含两个 cell 的统计
        text_report = generate_text_label_report(
            child_cell_text_gds, output_format="text"
        )
        assert "TOP" in text_report
        assert "CHILD" in text_report


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_text_label_fields(self) -> None:
        """TextLabel 字段完整性。"""
        lbl = TextLabel(
            text="hello",
            layer_name="TEXT",
            gds_layer=10,
            gds_datatype=0,
            x_um=1.5,
            y_um=2.5,
            cell_name="TOP",
        )
        assert lbl.text == "hello"
        assert lbl.layer_name == "TEXT"
        assert lbl.gds_layer == 10
        assert lbl.gds_datatype == 0
        assert lbl.x_um == 1.5
        assert lbl.y_um == 2.5
        assert lbl.cell_name == "TOP"

    def test_text_label_report_defaults(self) -> None:
        """TextLabelReport 默认值。"""
        report = TextLabelReport(file_path="/tmp/x.gds")
        assert report.file_path == "/tmp/x.gds"
        assert report.dbu == 0.0
        assert report.top_cell_name == ""
        assert report.labels == []
        assert report.total_count == 0
        assert report.layer_counts == {}
        assert report.cell_counts == {}

    def test_text_label_report_with_data(self) -> None:
        """TextLabelReport 含数据。"""
        lbl = TextLabel(
            text="x",
            layer_name="TEXT",
            gds_layer=10,
            gds_datatype=0,
            x_um=0.0,
            y_um=0.0,
            cell_name="TOP",
        )
        report = TextLabelReport(
            file_path="/tmp/y.gds",
            dbu=0.001,
            top_cell_name="TOP",
            labels=[lbl],
            total_count=1,
            layer_counts={"TEXT": 1},
            cell_counts={"TOP": 1},
        )
        assert report.dbu == 0.001
        assert report.top_cell_name == "TOP"
        assert len(report.labels) == 1
        assert report.layer_counts == {"TEXT": 1}

    def test_text_label_is_dataclass(self) -> None:
        """TextLabel 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(TextLabel)
        assert is_dataclass(TextLabelReport)
