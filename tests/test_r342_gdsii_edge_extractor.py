"""R342 GDSII 边缘提取工具测试。

覆盖:
- extract_edges: 基本提取、长度过滤、方向过滤、统计、输出到新层
- generate_edge_report: text/markdown/json 报告
- R03 错误处理（禁止 fall-back）
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Edges class: https://www.klayout.org/doc-qt5/code/class_Edges.html
- KLayout Edge class: https://www.klayout.org/doc-qt5/code/class_Edge.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_edge_extractor import (
    EdgeExtractionReport,
    EdgeInfo,
    extract_edges,
    generate_edge_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_single_rect_gds(path: Path) -> Path:
    """创建单矩形 GDSII。

    layer (1,0): Box(0,0)-(2000,3000) = 2μm×3μm
    dbu = 0.001μm (1nm)
    边: 2 条 2μm (H) + 2 条 3μm (V) = 4 条，总长 10μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 2000, 3000))
    ly.write(str(path))
    return path


def _make_multi_rect_gds(path: Path) -> Path:
    """创建多矩形 GDSII（2 个不相交矩形）。

    layer (1,0):
    - Box(0,0)-(2000,2000) = 2μm×2μm (4 条 2μm 边)
    - Box(5000,5000)-(7000,7000) = 2μm×2μm (4 条 2μm 边)
    总: 8 条边，总长 16μm，全水平/垂直
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    top.shapes(li).insert(db.Box(0, 0, 2000, 2000))
    top.shapes(li).insert(db.Box(5000, 5000, 7000, 7000))
    ly.write(str(path))
    return path


def _make_diagonal_gds(path: Path) -> Path:
    """创建含对角边的 GDSII（45 度三角形）。

    layer (1,0): 三角形 (0,0)-(2000,0)-(0,2000)
    边:
    - (0,0)-(2000,0): H, 2μm
    - (2000,0)-(0,2000): D (对角), 2√2 ≈ 2.828μm
    - (0,2000)-(0,0): V, 2μm
    总: 3 条边，1H + 1V + 1D
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    pts = [db.Point(0, 0), db.Point(2000, 0), db.Point(0, 2000)]
    poly = db.Polygon(pts)
    top.shapes(li).insert(poly)
    ly.write(str(path))
    return path


def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII。

    - TOP cell
      - CHILD @ (0, 0)
    - CHILD cell
      - layer (1,0): Box(0,0)-(2000,2000) = 2μm×2μm
    边: 4 条 2μm 边，总长 8μm
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    child.shapes(li).insert(db.Box(0, 0, 2000, 2000))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(db.Point(0, 0))))
    ly.write(str(path))
    return path


def _make_empty_layer_gds(path: Path) -> Path:
    """创建含零面积多边形的 GDSII（layer (1,0) 有形状但面积为 0）。

    注: GDSII 格式不保留完全空的层，所以用零面积 Box 模拟"空"场景。
    KLayout 读取后该层存在但 begin_shapes_rec 不返回有效边。
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    top = ly.create_cell("TOP")
    # 插入一个零面积 Box，确保层被保留
    top.shapes(li).insert(db.Box(0, 0, 0, 0))
    ly.write(str(path))
    return path


@pytest.fixture
def single_rect_gds(tmp_path: Path) -> Path:
    """单矩形 GDSII。"""
    return _make_single_rect_gds(tmp_path / "rect.gds")


@pytest.fixture
def multi_rect_gds(tmp_path: Path) -> Path:
    """多矩形 GDSII。"""
    return _make_multi_rect_gds(tmp_path / "multi.gds")


@pytest.fixture
def diagonal_gds(tmp_path: Path) -> Path:
    """含对角边的 GDSII。"""
    return _make_diagonal_gds(tmp_path / "diag.gds")


@pytest.fixture
def hier_gds(tmp_path: Path) -> Path:
    """层次化 GDSII。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


@pytest.fixture
def empty_layer_gds(tmp_path: Path) -> Path:
    """空层 GDSII（零面积多边形）。"""
    return _make_empty_layer_gds(tmp_path / "empty.gds")


# =============================================================================
# TestExtractEdges: 基本提取
# =============================================================================
class TestExtractEdges:
    """extract_edges 函数测试。"""

    def test_returns_report(self, single_rect_gds: Path) -> None:
        """返回 EdgeExtractionReport。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert isinstance(report, EdgeExtractionReport)

    def test_input_path(self, single_rect_gds: Path) -> None:
        """input_path 正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.input_path == str(single_rect_gds)

    def test_dbu(self, single_rect_gds: Path) -> None:
        """dbu 正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, single_rect_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.top_cell_name == "TOP"

    def test_layer_recorded(self, single_rect_gds: Path) -> None:
        """层信息记录正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.layer == (1, 0)

    def test_no_output_by_default(self, single_rect_gds: Path) -> None:
        """默认不输出到 GDSII。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.output_path == ""
        assert report.layer_result == ()

    def test_total_edges_before(self, single_rect_gds: Path) -> None:
        """过滤前边数正确（2x3 矩形 = 4 条边）。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.total_edges_before == 4

    def test_total_edges_after_no_filter(self, single_rect_gds: Path) -> None:
        """无过滤时过滤后边数 == 过滤前。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.total_edges_after == 4
        assert report.total_edges_after == report.total_edges_before


# =============================================================================
# TestEdgeClassification: 边方向分类
# =============================================================================
class TestEdgeClassification:
    """边方向分类（H/V/D）测试。"""

    def test_horizontal_vertical_only(self, single_rect_gds: Path) -> None:
        """矩形只有水平/垂直边，无对角边。"""
        report = extract_edges(single_rect_gds, (1, 0))
        # 2x3 矩形: 2 条 H (2μm) + 2 条 V (3μm)
        assert report.horizontal_count == 2
        assert report.vertical_count == 2
        assert report.diagonal_count == 0

    def test_diagonal_edges(self, diagonal_gds: Path) -> None:
        """三角形有 1 条对角边。"""
        report = extract_edges(diagonal_gds, (1, 0))
        # 三角形 (0,0)-(2000,0)-(0,2000)
        # 边: (0,0)-(2000,0) H, (2000,0)-(0,2000) D, (0,2000)-(0,0) V
        assert report.total_edges_after == 3
        assert report.horizontal_count == 1
        assert report.vertical_count == 1
        assert report.diagonal_count == 1

    def test_orientation_in_samples(self, single_rect_gds: Path) -> None:
        """样本边的 orientation 字段正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        orientations = {e.orientation for e in report.sample_edges}
        assert orientations == {"H", "V"}

    def test_diagonal_orientation_in_samples(self, diagonal_gds: Path) -> None:
        """对角边样本的 orientation 字段为 'D'。"""
        report = extract_edges(diagonal_gds, (1, 0))
        diag_edges = [e for e in report.sample_edges if e.orientation == "D"]
        assert len(diag_edges) == 1
        # 对角边长度 ≈ 2√2 ≈ 2.828μm
        assert diag_edges[0].length_um == pytest.approx(2 * (2 ** 0.5), rel=1e-3)


# =============================================================================
# TestLengthFilter: 长度过滤
# =============================================================================
class TestLengthFilter:
    """长度过滤测试。"""

    def test_min_length_filter(self, single_rect_gds: Path) -> None:
        """min_length_um=2.5 过滤掉 2μm 边，保留 3μm 边。"""
        report = extract_edges(single_rect_gds, (1, 0), min_length_um=2.5)
        # 2x3 矩形: 2 条 2μm (H) + 2 条 3μm (V)
        # 过滤 >= 2.5μm: 保留 2 条 3μm
        assert report.total_edges_before == 4
        assert report.total_edges_after == 2

    def test_max_length_filter(self, single_rect_gds: Path) -> None:
        """max_length_um=2.5 过滤掉 3μm 边，保留 2μm 边。"""
        report = extract_edges(single_rect_gds, (1, 0), max_length_um=2.5)
        # 过滤 <= 2.5μm: 保留 2 条 2μm
        assert report.total_edges_before == 4
        assert report.total_edges_after == 2

    def test_min_max_length_filter(self, single_rect_gds: Path) -> None:
        """min=2, max=3 保留所有边。"""
        report = extract_edges(
            single_rect_gds, (1, 0), min_length_um=2.0, max_length_um=3.0
        )
        assert report.total_edges_after == 4

    def test_min_max_filter_empty(self, single_rect_gds: Path) -> None:
        """min=5, max=10 过滤后无边。"""
        report = extract_edges(
            single_rect_gds, (1, 0), min_length_um=5.0, max_length_um=10.0
        )
        assert report.total_edges_before == 4
        assert report.total_edges_after == 0

    def test_filter_recorded(self, single_rect_gds: Path) -> None:
        """过滤参数记录正确。"""
        report = extract_edges(
            single_rect_gds, (1, 0), min_length_um=1.5, max_length_um=2.5
        )
        assert report.min_length_um == pytest.approx(1.5)
        assert report.max_length_um == pytest.approx(2.5)


# =============================================================================
# TestOrientationFilter: 方向过滤
# =============================================================================
class TestOrientationFilter:
    """方向过滤测试。"""

    def test_filter_horizontal(self, single_rect_gds: Path) -> None:
        """orientation_filter='H' 只保留水平边。"""
        report = extract_edges(single_rect_gds, (1, 0), orientation_filter="H")
        assert report.total_edges_after == 2
        assert report.horizontal_count == 2
        assert report.vertical_count == 0
        assert report.diagonal_count == 0

    def test_filter_vertical(self, single_rect_gds: Path) -> None:
        """orientation_filter='V' 只保留垂直边。"""
        report = extract_edges(single_rect_gds, (1, 0), orientation_filter="V")
        assert report.total_edges_after == 2
        assert report.horizontal_count == 0
        assert report.vertical_count == 2
        assert report.diagonal_count == 0

    def test_filter_diagonal(self, diagonal_gds: Path) -> None:
        """orientation_filter='D' 只保留对角边。"""
        report = extract_edges(diagonal_gds, (1, 0), orientation_filter="D")
        assert report.total_edges_after == 1
        assert report.diagonal_count == 1

    def test_filter_lowercase(self, single_rect_gds: Path) -> None:
        """小写 'h' 也被接受（内部转大写）。"""
        report = extract_edges(single_rect_gds, (1, 0), orientation_filter="h")
        assert report.total_edges_after == 2
        assert report.orientation_filter == "H"

    def test_filter_empty_string(self, single_rect_gds: Path) -> None:
        """空字符串表示无过滤。"""
        report = extract_edges(single_rect_gds, (1, 0), orientation_filter="")
        assert report.total_edges_after == 4
        assert report.orientation_filter == ""


# =============================================================================
# TestStatistics: 统计
# =============================================================================
class TestStatistics:
    """统计测试。"""

    def test_total_length(self, single_rect_gds: Path) -> None:
        """总长度正确（2x3 矩形 = 10μm）。"""
        report = extract_edges(single_rect_gds, (1, 0))
        # 2*(2μm) + 2*(3μm) = 10μm
        assert report.total_length_um == pytest.approx(10.0, rel=1e-6)

    def test_min_max_avg_length(self, single_rect_gds: Path) -> None:
        """min/max/avg 边长正确。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.min_edge_length_um == pytest.approx(2.0, rel=1e-6)
        assert report.max_edge_length_um == pytest.approx(3.0, rel=1e-6)
        # avg = (2+3+2+3)/4 = 2.5
        assert report.avg_edge_length_um == pytest.approx(2.5, rel=1e-6)

    def test_empty_layer_stats(self, empty_layer_gds: Path) -> None:
        """零面积多边形统计：4 条零长度边，总长度 0。"""
        report = extract_edges(empty_layer_gds, (1, 0))
        # Box(0,0,0,0) 是零面积 Box，KLayout 保留为 4 条零长度边
        assert report.total_edges_before == 4
        assert report.total_edges_after == 4
        assert report.total_length_um == 0.0
        assert report.min_edge_length_um == 0.0
        assert report.max_edge_length_um == 0.0
        assert report.avg_edge_length_um == 0.0
        # 所有零长度边的 y1==y2==0，被分类为水平
        assert report.horizontal_count == 4
        assert report.vertical_count == 0
        assert report.diagonal_count == 0
        # 全部在 0-0.1μm 区间
        assert report.length_histogram["0-0.1μm"] == 4

    def test_length_histogram(self, single_rect_gds: Path) -> None:
        """长度直方图正确（4 条边都在 1-10μm 区间）。"""
        report = extract_edges(single_rect_gds, (1, 0))
        assert report.length_histogram["1-10μm"] == 4
        assert report.length_histogram["0-0.1μm"] == 0
        assert report.length_histogram["0.1-1μm"] == 0
        assert report.length_histogram["10-100μm"] == 0
        assert report.length_histogram["100μm+"] == 0

    def test_histogram_sums_to_total(self, single_rect_gds: Path) -> None:
        """直方图各 bin 之和等于总边数。"""
        report = extract_edges(single_rect_gds, (1, 0))
        total = sum(report.length_histogram.values())
        assert total == report.total_edges_after

    def test_multi_rect_stats(self, multi_rect_gds: Path) -> None:
        """2 个 2x2 矩形统计正确。"""
        report = extract_edges(multi_rect_gds, (1, 0))
        # 每个矩形 4 条 2μm 边，2 个矩形 = 8 条 16μm
        assert report.total_edges_after == 8
        assert report.total_length_um == pytest.approx(16.0, rel=1e-6)
        assert report.min_edge_length_um == pytest.approx(2.0, rel=1e-6)
        assert report.max_edge_length_um == pytest.approx(2.0, rel=1e-6)
        assert report.avg_edge_length_um == pytest.approx(2.0, rel=1e-6)


# =============================================================================
# TestOutputToLayer: 输出到新层
# =============================================================================
class TestOutputToLayer:
    """输出到新层测试。"""

    def test_output_to_layer(self, single_rect_gds: Path, tmp_path: Path) -> None:
        """输出边到新层。"""
        out = tmp_path / "out.gds"
        report = extract_edges(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
        )
        assert out.exists()
        assert report.output_path == str(out)
        assert report.layer_result == (2, 0)

    def test_output_file_has_result_layer(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """输出文件包含结果层。"""
        out = tmp_path / "out.gds"
        extract_edges(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
        )
        ly = db.Layout()
        ly.read(str(out))
        # 检查 (2,0) 层存在
        found = False
        for li in ly.layer_indices():
            info = ly.get_info(li)
            if int(info.layer) == 2 and int(info.datatype) == 0:
                found = True
                break
        assert found, "结果层 (2,0) 不存在"

    def test_output_file_has_edge_polygons(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """输出文件的结果层有 polygon（每条边转 1 个细矩形）。"""
        out = tmp_path / "out.gds"
        extract_edges(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
        )
        ly = db.Layout()
        ly.read(str(out))
        top = ly.top_cell()
        # 找到 (2,0) 层
        li_result = None
        for li in ly.layer_indices():
            info = ly.get_info(li)
            if int(info.layer) == 2 and int(info.datatype) == 0:
                li_result = int(li)
                break
        assert li_result is not None
        # 应该有 4 个 polygon（每条边 1 个）
        r = db.Region(top.begin_shapes_rec(li_result))
        assert r.count() == 4

    def test_filter_then_output(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """过滤后输出（只输出过滤后的边）。"""
        out = tmp_path / "out.gds"
        report = extract_edges(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
            min_length_um=2.5,  # 只保留 3μm 边
        )
        assert report.total_edges_after == 2

        ly = db.Layout()
        ly.read(str(out))
        top = ly.top_cell()
        li_result = None
        for li in ly.layer_indices():
            info = ly.get_info(li)
            if int(info.layer) == 2 and int(info.datatype) == 0:
                li_result = int(li)
                break
        assert li_result is not None
        r = db.Region(top.begin_shapes_rec(li_result))
        assert r.count() == 2


# =============================================================================
# TestHierarchical: 层次化
# =============================================================================
class TestHierarchical:
    """层次化 GDSII 测试。"""

    def test_hierarchical_edges(self, hier_gds: Path) -> None:
        """层次化 GDSII 边提取（递归遍历子 cell）。"""
        report = extract_edges(hier_gds, (1, 0))
        # CHILD 有 2x2 矩形 = 4 条 2μm 边
        assert report.total_edges_before == 4
        assert report.total_edges_after == 4
        assert report.total_length_um == pytest.approx(8.0, rel=1e-6)


# =============================================================================
# TestGenerateEdgeReport: 报告生成
# =============================================================================
class TestGenerateEdgeReport:
    """generate_edge_report 函数测试。"""

    def test_text_report(self, single_rect_gds: Path) -> None:
        """text 报告生成。"""
        s = generate_edge_report(single_rect_gds, (1, 0), output_format="text")
        assert isinstance(s, str)
        assert "GDSII 边缘提取报告" in s
        assert "过滤前边数" in s
        assert "总长度" in s

    def test_markdown_report(self, single_rect_gds: Path) -> None:
        """markdown 报告生成。"""
        s = generate_edge_report(single_rect_gds, (1, 0), output_format="markdown")
        assert isinstance(s, str)
        assert "# GDSII 边缘提取报告" in s
        assert "## 统计" in s
        assert "## 长度直方图" in s

    def test_json_report(self, single_rect_gds: Path) -> None:
        """json 报告生成。"""
        s = generate_edge_report(single_rect_gds, (1, 0), output_format="json")
        data = json.loads(s)
        assert data["total_edges_after"] == 4
        assert data["total_length_um"] == pytest.approx(10.0, rel=1e-6)
        assert data["horizontal_count"] == 2
        assert data["vertical_count"] == 2
        assert data["diagonal_count"] == 0

    def test_json_report_with_output(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """json 报告含输出层。"""
        out = tmp_path / "out.gds"
        s = generate_edge_report(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
            output_format="json",
        )
        data = json.loads(s)
        assert data["output_path"] == str(out)
        assert data["layer_result"] == [2, 0]

    def test_json_report_sample_edges(self, single_rect_gds: Path) -> None:
        """json 报告含样本边。"""
        s = generate_edge_report(single_rect_gds, (1, 0), output_format="json")
        data = json.loads(s)
        assert len(data["sample_edges"]) == 4
        e = data["sample_edges"][0]
        assert "x1_um" in e
        assert "y1_um" in e
        assert "x2_um" in e
        assert "y2_um" in e
        assert "length_um" in e
        assert "orientation" in e

    def test_text_report_contains_histogram(
        self, single_rect_gds: Path
    ) -> None:
        """text 报告含直方图。"""
        s = generate_edge_report(single_rect_gds, (1, 0), output_format="text")
        assert "长度直方图" in s
        assert "1-10μm" in s


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            extract_edges(tmp_path / "nonexistent.gds", (1, 0))

    def test_not_a_file(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            extract_edges(tmp_path, (1, 0))

    def test_invalid_layer_tuple(self, single_rect_gds: Path) -> None:
        """layer 不是 2 元组 raise ValueError。"""
        with pytest.raises(ValueError, match="必须是"):
            extract_edges(single_rect_gds, (1,))  # type: ignore

    def test_invalid_layer_out_of_range(self, single_rect_gds: Path) -> None:
        """layer 超出范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-999"):
            extract_edges(single_rect_gds, (1000, 0))

    def test_invalid_datatype_out_of_range(self, single_rect_gds: Path) -> None:
        """datatype 超出范围 raise ValueError。"""
        with pytest.raises(ValueError, match="0-255"):
            extract_edges(single_rect_gds, (1, 256))

    def test_output_without_layer_result(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """output_path 提供但 layer_result 未提供 raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="layer_result 必须提供"):
            extract_edges(single_rect_gds, (1, 0), output_path=out)

    def test_same_layer_and_result(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """layer == layer_result raise ValueError。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="不能相同"):
            extract_edges(
                single_rect_gds, (1, 0),
                output_path=out, layer_result=(1, 0),
            )

    def test_layer_not_found(self, single_rect_gds: Path) -> None:
        """层不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            extract_edges(single_rect_gds, (99, 99))

    def test_negative_min_length(self, single_rect_gds: Path) -> None:
        """min_length_um 为负 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为负"):
            extract_edges(single_rect_gds, (1, 0), min_length_um=-1.0)

    def test_negative_max_length(self, single_rect_gds: Path) -> None:
        """max_length_um 为负 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为负"):
            extract_edges(single_rect_gds, (1, 0), max_length_um=-1.0)

    def test_min_greater_than_max(self, single_rect_gds: Path) -> None:
        """min > max raise ValueError。"""
        with pytest.raises(ValueError, match="不能大于"):
            extract_edges(
                single_rect_gds, (1, 0),
                min_length_um=5.0, max_length_um=2.0,
            )

    def test_invalid_orientation_filter(self, single_rect_gds: Path) -> None:
        """orientation_filter 无效 raise ValueError。"""
        with pytest.raises(ValueError, match="orientation_filter"):
            extract_edges(single_rect_gds, (1, 0), orientation_filter="X")

    def test_invalid_max_samples(self, single_rect_gds: Path) -> None:
        """max_samples <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="max_samples"):
            extract_edges(single_rect_gds, (1, 0), max_samples=0)

    def test_invalid_max_samples_negative(self, single_rect_gds: Path) -> None:
        """max_samples 为负 raise ValueError。"""
        with pytest.raises(ValueError, match="max_samples"):
            extract_edges(single_rect_gds, (1, 0), max_samples=-1)

    def test_top_cell_not_found(self, single_rect_gds: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            extract_edges(single_rect_gds, (1, 0), top_cell_name="NONEXISTENT")

    def test_unsupported_format(self, single_rect_gds: Path) -> None:
        """不支持的输出格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_edge_report(single_rect_gds, (1, 0), output_format="xml")


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_module_docstring_exists(self) -> None:
        """模块有 docstring。"""
        from polaris.verification import gdsii_edge_extractor
        assert gdsii_edge_extractor.__doc__ is not None
        assert len(gdsii_edge_extractor.__doc__) > 100

    def test_module_docstring_has_api_facts(self) -> None:
        """docstring 含 KLayout API 关键事实。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        assert "db.Edges" in doc
        assert "begin_shapes_rec" in doc
        assert "edges.count()" in doc
        assert "edges.length()" in doc
        assert "edges.each()" in doc
        assert "edge.p1" in doc
        assert "with_length" in doc

    def test_module_docstring_has_references(self) -> None:
        """docstring 含 ≥5 个文献 URL。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        urls = [line for line in doc.split() if line.startswith("http")]
        assert len(urls) >= 5, f"只有 {len(urls)} 个 URL"

    def test_module_docstring_has_klayout_edges_url(self) -> None:
        """docstring 含 KLayout Edges class URL。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        assert "class_Edges.html" in doc

    def test_module_docstring_has_klayout_edge_url(self) -> None:
        """docstring 含 KLayout Edge class URL。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        assert "class_Edge.html" in doc

    def test_module_docstring_has_compliance(self) -> None:
        """docstring 含合规声明。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        assert "R01" in doc
        assert "R02" in doc
        assert "R03" in doc
        assert "R11" in doc

    def test_module_docstring_has_no_fallback(self) -> None:
        """docstring 含禁止 fall-back 说明。"""
        from polaris.verification import gdsii_edge_extractor
        doc = gdsii_edge_extractor.__doc__
        # R03 合规声明
        assert "R03" in doc

    def test_function_docstrings_have_source(self) -> None:
        """主函数 docstring 含来源 URL。"""
        from polaris.verification import gdsii_edge_extractor as m
        extract_src = m.extract_edges.__doc__ or ""
        assert "klayout.org" in extract_src
        assert "Edges" in extract_src or "Edge" in extract_src


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_no_output(self, single_rect_gds: Path) -> None:
        """完整工作流（不输出）：提取 + 过滤 + 统计。"""
        report = extract_edges(
            single_rect_gds, (1, 0),
            min_length_um=2.0,
            orientation_filter="V",
        )
        # 2x3 矩形: 只保留 >=2μm 的垂直边 = 2 条 3μm
        assert report.total_edges_after == 2
        assert report.vertical_count == 2
        assert report.total_length_um == pytest.approx(6.0, rel=1e-6)

    def test_full_workflow_with_output(
        self, single_rect_gds: Path, tmp_path: Path
    ) -> None:
        """完整工作流（输出）：提取 + 过滤 + 输出到新层。"""
        out = tmp_path / "out.gds"
        report = extract_edges(
            single_rect_gds, (1, 0),
            output_path=out, layer_result=(2, 0),
            orientation_filter="H",
        )
        assert out.exists()
        assert report.total_edges_after == 2
        assert report.horizontal_count == 2

    def test_diagonal_workflow(self, diagonal_gds: Path) -> None:
        """三角形对角边工作流。"""
        report = extract_edges(diagonal_gds, (1, 0))
        assert report.total_edges_after == 3
        assert report.diagonal_count == 1
        # 对角边长度 ≈ 2√2
        diag = [e for e in report.sample_edges if e.orientation == "D"][0]
        assert diag.length_um == pytest.approx(2 * (2 ** 0.5), rel=1e-3)

    def test_multi_rect_workflow(self, multi_rect_gds: Path) -> None:
        """多矩形工作流。"""
        report = extract_edges(multi_rect_gds, (1, 0))
        assert report.total_edges_after == 8
        assert report.total_length_um == pytest.approx(16.0, rel=1e-6)


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_edge_info_default(self) -> None:
        """EdgeInfo 默认值。"""
        e = EdgeInfo(
            x1_um=0.0, y1_um=0.0,
            x2_um=1.0, y2_um=0.0,
            length_um=1.0, orientation="H",
        )
        assert e.x1_um == 0.0
        assert e.x2_um == 1.0
        assert e.length_um == 1.0
        assert e.orientation == "H"

    def test_edge_extraction_report_default(self) -> None:
        """EdgeExtractionReport 默认值。"""
        r = EdgeExtractionReport()
        assert r.input_path == ""
        assert r.output_path == ""
        assert r.layer == (0, 0)
        assert r.layer_result == ()
        assert r.dbu == 0.0
        assert r.top_cell_name == ""
        assert r.min_length_um == 0.0
        assert r.max_length_um == 0.0
        assert r.orientation_filter == ""
        assert r.total_edges_before == 0
        assert r.total_edges_after == 0
        assert r.total_length_um == 0.0
        assert r.horizontal_count == 0
        assert r.vertical_count == 0
        assert r.diagonal_count == 0
        assert r.length_histogram == {}
        assert r.sample_edges == []

    def test_edge_extraction_report_mutable_defaults(self) -> None:
        """EdgeExtractionReport 可变默认值独立。"""
        r1 = EdgeExtractionReport()
        r2 = EdgeExtractionReport()
        r1.length_histogram["test"] = 1
        r1.sample_edges.append(EdgeInfo(0, 0, 1, 0, 1.0, "H"))
        assert "test" not in r2.length_histogram
        assert len(r2.sample_edges) == 0

    def test_edge_info_equality(self) -> None:
        """EdgeInfo 相等性。"""
        e1 = EdgeInfo(0, 0, 1, 0, 1.0, "H")
        e2 = EdgeInfo(0, 0, 1, 0, 1.0, "H")
        e3 = EdgeInfo(0, 0, 1, 0, 1.0, "V")
        assert e1 == e2
        assert e1 != e3
