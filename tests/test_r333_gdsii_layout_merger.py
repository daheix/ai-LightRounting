"""R333 GDSII 版图合并工具测试。

覆盖:
- merge_gdsii: 多文件合并、单文件合并、偏移、bbox
- generate_merge_report: text/markdown/json 报告
- R03 错误处理（空输入、文件不存在、参数不匹配）
- R02 学术诚信（数据类、文献引用）
- 集成测试（与 R323/R331 文本/统计工具联动）
- 数据类测试

来源:
- KLayout Layout.read: https://www.klayout.de/doc-qt5/code/class_Layout.html
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- KLayout Cell.each_inst: https://www.klayout.de/doc-qt5/code/class_Cell.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_layout_merger import (
    MergedCellInfo,
    MergeReport,
    generate_merge_report,
    merge_gdsii,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_gds_with_cell(
    path: Path,
    cell_name: str,
    layer: int = 1,
    datatype: int = 0,
    polygons: list[list[list[int]]] | None = None,
    texts: list[dict] | None = None,
) -> Path:
    """用 KLayout 直接创建 GDSII 文件（含可选 polygon/text）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(cell_name)

    if polygons:
        li = ly.layer(layer, datatype)
        for pts in polygons:
            kpts = [db.Point(int(x), int(y)) for x, y in pts]
            top.shapes(li).insert(db.Polygon(kpts))

    if texts:
        for t in texts:
            li = ly.layer(t.get("layer", 10), t.get("datatype", 0))
            # db.Text 构造函数第二参数为 Trans（实测 KLayout 0.30.9）
            # 来源: https://www.klayout.de/doc-qt5/code/class_Text.html
            text = db.Text(
                t["string"],
                db.Trans(db.Point(int(t["x"] * 1000), int(t["y"] * 1000))),
            )
            top.shapes(li).insert(text)

    ly.write(str(path))
    return path


@pytest.fixture
def single_gds_a(tmp_path: Path) -> Path:
    """单 cell GDSII（CELL_A, layer 1）。"""
    return _make_gds_with_cell(
        tmp_path / "a.gds",
        "CELL_A",
        layer=1,
        polygons=[[[0, 0], [10000, 0], [10000, 5000], [0, 5000]]],
    )


@pytest.fixture
def single_gds_b(tmp_path: Path) -> Path:
    """单 cell GDSII（CELL_B, layer 2）。"""
    return _make_gds_with_cell(
        tmp_path / "b.gds",
        "CELL_B",
        layer=2,
        polygons=[[[0, 0], [8000, 0], [8000, 4000], [0, 4000]]],
    )


@pytest.fixture
def single_gds_c(tmp_path: Path) -> Path:
    """单 cell GDSII（CELL_C, layer 3）。"""
    return _make_gds_with_cell(
        tmp_path / "c.gds",
        "CELL_C",
        layer=3,
        polygons=[[[0, 0], [5000, 0], [5000, 3000], [0, 3000]]],
    )


@pytest.fixture
def gds_with_text(tmp_path: Path) -> Path:
    """带文本标签的 GDSII。"""
    return _make_gds_with_cell(
        tmp_path / "text.gds",
        "TOP_TEXT",
        layer=1,
        polygons=[[[0, 0], [10000, 0], [10000, 5000], [0, 5000]]],
        texts=[{"layer": 10, "datatype": 0, "string": "label_1", "x": 5.0, "y": 2.5}],
    )


@pytest.fixture
def empty_gds(tmp_path: Path) -> Path:
    """空 GDSII（只有 cell 名，无 shapes）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    ly.create_cell("EMPTY_TOP")
    path = tmp_path / "empty.gds"
    ly.write(str(path))
    return path


# =============================================================================
# TestMergeGdsii: 基本合并
# =============================================================================
class TestMergeGdsii:
    """merge_gdsii 函数测试。"""

    def test_returns_report(self, single_gds_a: Path, tmp_path: Path) -> None:
        """返回 MergeReport。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        assert isinstance(report, MergeReport)
        assert report.output_path == str(out)

    def test_default_top_cell_name(self, single_gds_a: Path, tmp_path: Path) -> None:
        """默认顶层 cell 名为 MERGED。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        assert report.top_cell_name == "MERGED"

    def test_custom_top_cell_name(self, single_gds_a: Path, tmp_path: Path) -> None:
        """自定义顶层 cell 名。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out, top_cell_name="CUSTOM")
        assert report.top_cell_name == "CUSTOM"

    def test_dbu_is_um(self, single_gds_a: Path, tmp_path: Path) -> None:
        """dbu 单位为 μm（0.001 = 1nm）。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_input_files_recorded(self, single_gds_a: Path, single_gds_b: Path,
                                  tmp_path: Path) -> None:
        """input_files 正确记录。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b], out)
        assert report.input_files == [str(single_gds_a), str(single_gds_b)]

    def test_two_files_merge(self, single_gds_a: Path, single_gds_b: Path,
                             tmp_path: Path) -> None:
        """两个文件合并。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b], out)
        assert len(report.merged_cells) == 2
        assert report.merged_cells[0].source_top_cell == "CELL_A"
        assert report.merged_cells[1].source_top_cell == "CELL_B"

    def test_three_files_merge(self, single_gds_a: Path, single_gds_b: Path,
                               single_gds_c: Path, tmp_path: Path) -> None:
        """三个文件合并。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b, single_gds_c], out)
        assert len(report.merged_cells) == 3
        cell_names = [mc.source_top_cell for mc in report.merged_cells]
        assert cell_names == ["CELL_A", "CELL_B", "CELL_C"]

    def test_total_instance_count_two(self, single_gds_a: Path, single_gds_b: Path,
                                      tmp_path: Path) -> None:
        """两文件合并后实例数为 2。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b], out)
        assert report.total_instance_count == 2

    def test_total_instance_count_three(self, single_gds_a: Path, single_gds_b: Path,
                                        single_gds_c: Path, tmp_path: Path) -> None:
        """三文件合并后实例数为 3。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b, single_gds_c], out)
        assert report.total_instance_count == 3

    def test_all_cell_count_two(self, single_gds_a: Path, single_gds_b: Path,
                                tmp_path: Path) -> None:
        """两文件合并后 layout cell 总数 = MERGED + 2 源 = 3。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b], out)
        assert report.all_cell_count == 3

    def test_wrapper_is_only_top_cell(self, single_gds_a: Path, single_gds_b: Path,
                                      tmp_path: Path) -> None:
        """合并后 wrapper 是唯一顶层 cell（用 KLayout 直接验证）。"""
        out = tmp_path / "out.gds"
        merge_gdsii([single_gds_a, single_gds_b], out, top_cell_name="MERGED")

        verify = db.Layout()
        verify.read(str(out))
        top_cells = [verify.cell(ci).name for ci in verify.each_top_cell()]
        assert top_cells == ["MERGED"]

    def test_all_source_cells_preserved(self, single_gds_a: Path, single_gds_b: Path,
                                        single_gds_c: Path, tmp_path: Path) -> None:
        """合并后所有源 cell 名都保留在 layout 中。"""
        out = tmp_path / "out.gds"
        merge_gdsii([single_gds_a, single_gds_b, single_gds_c], out)

        verify = db.Layout()
        verify.read(str(out))
        all_cells = {verify.cell(ci).name for ci in verify.each_cell_top_down()}
        assert "MERGED" in all_cells
        assert "CELL_A" in all_cells
        assert "CELL_B" in all_cells
        assert "CELL_C" in all_cells

    def test_default_offsets_zero(self, single_gds_a: Path, single_gds_b: Path,
                                  tmp_path: Path) -> None:
        """默认偏移全部 (0, 0)。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a, single_gds_b], out)
        for mc in report.merged_cells:
            assert mc.offset_um == (0.0, 0.0)

    def test_custom_offsets(self, single_gds_a: Path, single_gds_b: Path,
                            tmp_path: Path) -> None:
        """自定义偏移。"""
        out = tmp_path / "out.gds"
        offsets = [(10.0, 20.0), (30.0, 40.0)]
        report = merge_gdsii([single_gds_a, single_gds_b], out, offsets_um=offsets)
        assert report.merged_cells[0].offset_um == (10.0, 20.0)
        assert report.merged_cells[1].offset_um == (30.0, 40.0)

    def test_bbox_no_offset(self, single_gds_a: Path, tmp_path: Path) -> None:
        """无偏移时 bbox = 源 cell bbox。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        # CELL_A polygon: (0,0) - (10, 5) μm
        xmin, ymin, xmax, ymax = report.bounding_box_um
        assert xmin == pytest.approx(0.0, abs=1e-3)
        assert ymin == pytest.approx(0.0, abs=1e-3)
        assert xmax == pytest.approx(10.0, abs=1e-3)
        assert ymax == pytest.approx(5.0, abs=1e-3)

    def test_bbox_with_offset(self, single_gds_a: Path, single_gds_b: Path,
                              tmp_path: Path) -> None:
        """带偏移时 bbox 包含所有源 cell 的合并范围。"""
        out = tmp_path / "out.gds"
        # CELL_A: (0,0)-(10,5), CELL_B: (0,0)-(8,4) 偏移 (20, 0) → (20,0)-(28,4)
        offsets = [(0.0, 0.0), (20.0, 0.0)]
        report = merge_gdsii([single_gds_a, single_gds_b], out, offsets_um=offsets)
        xmin, ymin, xmax, ymax = report.bounding_box_um
        assert xmin == pytest.approx(0.0, abs=1e-3)
        assert ymin == pytest.approx(0.0, abs=1e-3)
        assert xmax == pytest.approx(28.0, abs=1e-3)
        assert ymax == pytest.approx(5.0, abs=1e-3)

    def test_bbox_with_y_offset(self, single_gds_a: Path, single_gds_b: Path,
                                tmp_path: Path) -> None:
        """Y 方向偏移 bbox。"""
        out = tmp_path / "out.gds"
        # CELL_A: (0,0)-(10,5), CELL_B: (0,0)-(8,4) 偏移 (0, 10) → (0,10)-(8,14)
        offsets = [(0.0, 0.0), (0.0, 10.0)]
        report = merge_gdsii([single_gds_a, single_gds_b], out, offsets_um=offsets)
        xmin, ymin, xmax, ymax = report.bounding_box_um
        assert xmin == pytest.approx(0.0, abs=1e-3)
        assert ymin == pytest.approx(0.0, abs=1e-3)
        assert xmax == pytest.approx(10.0, abs=1e-3)
        assert ymax == pytest.approx(14.0, abs=1e-3)

    def test_merged_cell_info_fields(self, single_gds_a: Path, tmp_path: Path) -> None:
        """MergedCellInfo 字段完整。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        mc = report.merged_cells[0]
        assert isinstance(mc, MergedCellInfo)
        assert mc.source_file == str(single_gds_a)
        assert mc.source_top_cell == "CELL_A"
        assert mc.offset_um == (0.0, 0.0)
        assert mc.cell_index >= 0
        assert mc.instance_count == 1

    def test_output_file_created(self, single_gds_a: Path, tmp_path: Path) -> None:
        """输出文件实际被创建。"""
        out = tmp_path / "out.gds"
        merge_gdsii([single_gds_a], out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_output_parent_dir_created(self, single_gds_a: Path,
                                       tmp_path: Path) -> None:
        """输出父目录自动创建。"""
        out = tmp_path / "subdir" / "deeper" / "out.gds"
        merge_gdsii([single_gds_a], out)
        assert out.exists()

    def test_string_path_input(self, single_gds_a: Path, tmp_path: Path) -> None:
        """字符串路径输入也可工作。"""
        out = str(tmp_path / "out.gds")
        report = merge_gdsii([str(single_gds_a)], out)
        assert isinstance(report, MergeReport)
        assert Path(report.output_path).exists()


# =============================================================================
# TestGenerateMergeReport: 报告生成
# =============================================================================
class TestGenerateMergeReport:
    """generate_merge_report 函数测试。"""

    def test_text_report(self, single_gds_a: Path, single_gds_b: Path,
                         tmp_path: Path) -> None:
        """text 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_merge_report(
            [single_gds_a, single_gds_b], out, output_format="text"
        )
        assert "GDSII 版图合并报告" in report
        assert "MERGED" in report
        assert "CELL_A" in report
        assert "CELL_B" in report

    def test_markdown_report(self, single_gds_a: Path, single_gds_b: Path,
                             tmp_path: Path) -> None:
        """markdown 格式报告。"""
        out = tmp_path / "out.gds"
        report = generate_merge_report(
            [single_gds_a, single_gds_b], out, output_format="markdown"
        )
        assert "# GDSII 版图合并报告" in report
        assert "|---|" in report
        assert "CELL_A" in report

    def test_json_report(self, single_gds_a: Path, single_gds_b: Path,
                         tmp_path: Path) -> None:
        """json 格式报告。"""
        out = tmp_path / "out.gds"
        report_str = generate_merge_report(
            [single_gds_a, single_gds_b], out, output_format="json"
        )
        data = json.loads(report_str)
        assert data["top_cell_name"] == "MERGED"
        assert len(data["merged_cells"]) == 2
        assert data["merged_cells"][0]["source_top_cell"] == "CELL_A"

    def test_json_report_bbox(self, single_gds_a: Path, tmp_path: Path) -> None:
        """json 报告 bbox 字段。"""
        out = tmp_path / "out.gds"
        report_str = generate_merge_report(
            [single_gds_a], out, output_format="json"
        )
        data = json.loads(report_str)
        assert "bounding_box_um" in data
        assert len(data["bounding_box_um"]) == 4

    def test_text_report_with_offsets(self, single_gds_a: Path, single_gds_b: Path,
                                      tmp_path: Path) -> None:
        """text 报告含偏移信息。"""
        out = tmp_path / "out.gds"
        report = generate_merge_report(
            [single_gds_a, single_gds_b], out,
            offsets_um=[(10.0, 20.0), (30.0, 40.0)],
            output_format="text",
        )
        assert "(10.00, 20.00)" in report
        assert "(30.00, 40.00)" in report

    def test_unsupported_format_raises(self, single_gds_a: Path,
                                       tmp_path: Path) -> None:
        """不支持的格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_merge_report([single_gds_a], out, output_format="xml")


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_empty_input_paths(self, tmp_path: Path) -> None:
        """空 input_paths raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="input_paths 不能为空"):
            merge_gdsii([], out)

    def test_empty_top_cell_name(self, single_gds_a: Path, tmp_path: Path) -> None:
        """空 top_cell_name raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="top_cell_name 不能为空"):
            merge_gdsii([single_gds_a], out, top_cell_name="")

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError):
            merge_gdsii([Path("/nonexistent.gds")], out)

    def test_offsets_length_mismatch(self, single_gds_a: Path, single_gds_b: Path,
                                     tmp_path: Path) -> None:
        """offsets_um 长度不匹配 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="offsets_um 长度"):
            merge_gdsii([single_gds_a, single_gds_b], out,
                        offsets_um=[(0.0, 0.0)])

    def test_offsets_length_zero(self, single_gds_a: Path, tmp_path: Path) -> None:
        """offsets_um 空列表但 input_paths 非空 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="offsets_um 长度"):
            merge_gdsii([single_gds_a], out, offsets_um=[])

    def test_path_not_file(self, tmp_path: Path) -> None:
        """路径是目录而非文件 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="路径不是文件"):
            merge_gdsii([tmp_path], out)

    def test_unsupported_format_xml(self, single_gds_a: Path, tmp_path: Path) -> None:
        """XML 格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_merge_report([single_gds_a], out, output_format="xml")

    def test_unsupported_format_html(self, single_gds_a: Path, tmp_path: Path) -> None:
        """HTML 格式 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_merge_report([single_gds_a], out, output_format="html")


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信（R02）
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_klayout_layout_url(self) -> None:
        """docstring 含 KLayout Layout 文档 URL。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "klayout.de/doc-qt5/code/class_Layout.html" in m.__doc__

    def test_docstring_has_klayout_cell_url(self) -> None:
        """docstring 含 KLayout Cell 文档 URL。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "klayout.de/doc-qt5/code/class_Cell.html" in m.__doc__

    def test_docstring_has_klayout_cellinstarray_url(self) -> None:
        """docstring 含 KLayout CellInstArray 文档 URL。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "klayout.de/doc-qt5/code/class_CellInstArray.html" in m.__doc__

    def test_docstring_has_klayout_trans_url(self) -> None:
        """docstring 含 KLayout Trans 文档 URL。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "klayout.de/doc-qt5/code/class_Trans.html" in m.__doc__

    def test_docstring_has_gdsii_wikipedia_url(self) -> None:
        """docstring 含 GDSII 标准 URL。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "en.wikipedia.org/wiki/GDS_File" in m.__doc__

    def test_docstring_has_5_plus_urls(self) -> None:
        """docstring 含 ≥5 个文献 URL（R02 要求）。"""
        from polaris.verification import gdsii_layout_merger as m
        doc = m.__doc__
        url_count = doc.count("https://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5"

    def test_docstring_has_r_compliance(self) -> None:
        """docstring 含规则合规声明。"""
        from polaris.verification import gdsii_layout_merger as m
        assert "R01" in m.__doc__
        assert "R02" in m.__doc__
        assert "R03" in m.__doc__
        assert "R05" in m.__doc__
        assert "R11" in m.__doc__

    def test_merge_report_field_documented(self) -> None:
        """MergeReport 字段有 docstring 文档。"""
        assert MergeReport.__doc__ is not None
        assert "output_path" in MergeReport.__doc__
        assert "top_cell_name" in MergeReport.__doc__
        assert "merged_cells" in MergeReport.__doc__
        assert "bounding_box_um" in MergeReport.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_merge_then_extract_text(self, gds_with_text: Path,
                                     single_gds_a: Path, tmp_path: Path) -> None:
        """合并后再用 R323 文本提取器提取文本。"""
        from polaris.verification.gdsii_text_label_extractor import (
            extract_text_labels,
        )

        out = tmp_path / "merged.gds"
        merge_gdsii([gds_with_text, single_gds_a], out)

        # 重新读入验证
        report = extract_text_labels(out)
        # gds_with_text 含 "label_1" 文本
        texts = {lbl.text for lbl in report.labels}
        assert "label_1" in texts

    def test_merge_then_statistics(self, single_gds_a: Path, single_gds_b: Path,
                                   tmp_path: Path) -> None:
        """合并后再用 R331 统计工具统计。"""
        from polaris.verification.gdsii_statistics import generate_gdsii_statistics

        out = tmp_path / "merged.gds"
        merge_gdsii([single_gds_a, single_gds_b], out)

        stats = generate_gdsii_statistics(out)
        # 应至少包含 layer 1 (CELL_A) 和 layer 2 (CELL_B)
        # StatisticsReport 字段: top_cell_names（复数）、total_cells
        assert "MERGED" in stats.top_cell_names
        # cell 总数 = MERGED + CELL_A + CELL_B = 3
        assert stats.total_cells == 3

    def test_merge_idempotent_single(self, single_gds_a: Path,
                                     tmp_path: Path) -> None:
        """单文件合并保持原 cell 结构。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([single_gds_a], out)
        assert report.total_instance_count == 1
        assert report.all_cell_count == 2  # MERGED + CELL_A

    def test_merge_with_text_gds(self, gds_with_text: Path, single_gds_b: Path,
                                 tmp_path: Path) -> None:
        """合并含文本标签的 GDSII 与普通 GDSII。"""
        out = tmp_path / "out.gds"
        report = merge_gdsii([gds_with_text, single_gds_b], out)
        assert report.total_instance_count == 2
        assert report.all_cell_count == 3  # MERGED + TOP_TEXT + CELL_B

    def test_merge_output_can_be_remerged(self, single_gds_a: Path,
                                          single_gds_b: Path, tmp_path: Path) -> None:
        """合并后的输出可再次作为合并输入。"""
        out1 = tmp_path / "out1.gds"
        merge_gdsii([single_gds_a, single_gds_b], out1, top_cell_name="MERGED_1")

        out2 = tmp_path / "out2.gds"
        report2 = merge_gdsii([out1], out2, top_cell_name="MERGED_2")
        assert report2.total_instance_count == 1
        assert report2.merged_cells[0].source_top_cell == "MERGED_1"


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_merged_cell_info_default(self) -> None:
        """MergedCellInfo 默认值。"""
        mc = MergedCellInfo(source_file="/test.gds")
        assert mc.source_file == "/test.gds"
        assert mc.source_top_cell == ""
        assert mc.offset_um == (0.0, 0.0)
        assert mc.cell_index == -1
        assert mc.instance_count == 1

    def test_merged_cell_info_full(self) -> None:
        """MergedCellInfo 完整字段。"""
        mc = MergedCellInfo(
            source_file="/a.gds",
            source_top_cell="CELL_A",
            offset_um=(10.0, 20.0),
            cell_index=5,
            instance_count=1,
        )
        assert mc.source_file == "/a.gds"
        assert mc.source_top_cell == "CELL_A"
        assert mc.offset_um == (10.0, 20.0)
        assert mc.cell_index == 5
        assert mc.instance_count == 1

    def test_merge_report_default(self) -> None:
        """MergeReport 默认值。"""
        report = MergeReport()
        assert report.output_path == ""
        assert report.top_cell_name == ""
        assert report.dbu == 0.0
        assert report.input_files == []
        assert report.merged_cells == []
        assert report.total_instance_count == 0
        assert report.all_cell_count == 0
        assert report.bounding_box_um == (0.0, 0.0, 0.0, 0.0)

    def test_merge_report_independent_lists(self) -> None:
        """MergeReport list 字段独立（不共享默认值）。"""
        r1 = MergeReport()
        r2 = MergeReport()
        r1.input_files.append("/a.gds")
        r1.merged_cells.append(MergedCellInfo(source_file="/a.gds"))
        assert r2.input_files == []
        assert r2.merged_cells == []

    def test_merged_cell_info_is_dataclass(self) -> None:
        """MergedCellInfo 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(MergedCellInfo)

    def test_merge_report_is_dataclass(self) -> None:
        """MergeReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(MergeReport)

    def test_merge_report_equality(self) -> None:
        """MergeReport 相等性。"""
        r1 = MergeReport(output_path="/a.gds", top_cell_name="M")
        r2 = MergeReport(output_path="/a.gds", top_cell_name="M")
        assert r1 == r2
