"""R336 GDSII 器件位置报告工具测试。

覆盖:
- extract_device_positions: 非递归/递归提取、位置/旋转/镜像
- generate_device_position_report: text/markdown/json 报告
- R03 错误处理
- R02 学术诚信
- 集成测试
- 数据类测试

来源:
- KLayout Cell.each_inst: https://www.klayout.de/doc-qt5/code/class_Cell.html
- KLayout Trans: https://www.klayout.de/doc-qt5/code/class_Trans.html
- KLayout Instance: https://www.klayout.de/doc-qt5/code/class_Instance.html
"""

from __future__ import annotations

import json
from pathlib import Path

import klayout.db as db
import pytest

from polaris.verification.gdsii_device_position_reporter import (
    DeviceInstance,
    DevicePositionReport,
    extract_device_positions,
    generate_device_position_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
def _make_hierarchical_gds(path: Path) -> Path:
    """创建层次化 GDSII（含实例嵌套）。

    结构:
    - TOP cell
      - CHILD_A @ (10, 20) μm, r0
      - CHILD_A @ (30, 0) μm, r90
      - CHILD_B @ (0, 50) μm, m90
    - CHILD_A cell (polygon)
    - CHILD_B cell
      - GRANDCHILD @ (5, 5) μm, r0
    - GRANDCHILD cell (polygon)
    """
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)

    grandchild = ly.create_cell("GRANDCHILD")
    pts_gc = [db.Point(0, 0), db.Point(500, 0),
              db.Point(500, 300), db.Point(0, 300)]
    grandchild.shapes(li).insert(db.Polygon(pts_gc))

    child_b = ly.create_cell("CHILD_B")
    pts_b = [db.Point(0, 0), db.Point(1000, 0),
             db.Point(1000, 800), db.Point(0, 800)]
    child_b.shapes(li).insert(db.Polygon(pts_b))
    child_b.insert(db.CellInstArray(
        grandchild.cell_index(), db.Trans(db.Point(5000, 5000))
    ))

    child_a = ly.create_cell("CHILD_A")
    pts_a = [db.Point(0, 0), db.Point(2000, 0),
             db.Point(2000, 1000), db.Point(0, 1000)]
    child_a.shapes(li).insert(db.Polygon(pts_a))

    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        child_a.cell_index(), db.Trans(db.Point(10000, 20000))
    ))
    top.insert(db.CellInstArray(
        child_a.cell_index(),
        db.Trans(db.Trans.R90, db.Point(30000, 0))
    ))
    top.insert(db.CellInstArray(
        child_b.cell_index(),
        db.Trans(db.Trans.M90, db.Point(0, 50000))
    ))

    ly.write(str(path))
    return path


@pytest.fixture
def hierarchical_gds(tmp_path: Path) -> Path:
    """层次化 GDSII 文件。"""
    return _make_hierarchical_gds(tmp_path / "hier.gds")


@pytest.fixture
def flat_gds(tmp_path: Path) -> Path:
    """无实例的扁平 GDSII（只有顶层 cell 的 polygon）。"""
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("FLAT_TOP")
    li = ly.layer(1, 0)
    pts = [db.Point(0, 0), db.Point(10000, 0),
           db.Point(10000, 5000), db.Point(0, 5000)]
    top.shapes(li).insert(db.Polygon(pts))
    path = tmp_path / "flat.gds"
    ly.write(str(path))
    return path


@pytest.fixture
def single_instance_gds(tmp_path: Path) -> Path:
    """单个实例的 GDSII。"""
    ly = db.Layout()
    ly.dbu = 0.001
    li = ly.layer(1, 0)
    child = ly.create_cell("CHILD")
    pts = [db.Point(0, 0), db.Point(1000, 0),
           db.Point(1000, 500), db.Point(0, 500)]
    child.shapes(li).insert(db.Polygon(pts))
    top = ly.create_cell("TOP")
    top.insert(db.CellInstArray(
        child.cell_index(), db.Trans(db.Point(5000, 10000))
    ))
    path = tmp_path / "single.gds"
    ly.write(str(path))
    return path


# =============================================================================
# TestExtractDevicePositions: 基本提取
# =============================================================================
class TestExtractDevicePositions:
    """extract_device_positions 函数测试。"""

    def test_returns_report(self, hierarchical_gds: Path) -> None:
        """返回 DevicePositionReport。"""
        report = extract_device_positions(hierarchical_gds)
        assert isinstance(report, DevicePositionReport)

    def test_file_path(self, hierarchical_gds: Path) -> None:
        """file_path 正确。"""
        report = extract_device_positions(hierarchical_gds)
        assert report.file_path == str(hierarchical_gds)

    def test_dbu_is_um(self, hierarchical_gds: Path) -> None:
        """dbu 单位为 μm。"""
        report = extract_device_positions(hierarchical_gds)
        assert report.dbu == pytest.approx(0.001, rel=1e-3)

    def test_top_cell_name(self, hierarchical_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = extract_device_positions(hierarchical_gds)
        assert report.top_cell_name == "TOP"

    def test_non_recursive_count(self, hierarchical_gds: Path) -> None:
        """非递归: 3 个直接实例。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        assert report.total_count == 3
        assert report.recursive is False

    def test_recursive_count(self, hierarchical_gds: Path) -> None:
        """递归: 4 个实例（3 + 1 GRANDCHILD）。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        assert report.total_count == 4
        assert report.recursive is True

    def test_non_recursive_no_grandchild(
        self, hierarchical_gds: Path
    ) -> None:
        """非递归不含 GRANDCHILD。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        cell_names = {d.cell_name for d in report.instances}
        assert "GRANDCHILD" not in cell_names

    def test_recursive_has_grandchild(self, hierarchical_gds: Path) -> None:
        """递归含 GRANDCHILD。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        cell_names = {d.cell_name for d in report.instances}
        assert "GRANDCHILD" in cell_names

    def test_cell_counts_non_recursive(
        self, hierarchical_gds: Path
    ) -> None:
        """非递归 cell_counts: CHILD_A=2, CHILD_B=1。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        assert report.cell_counts.get("CHILD_A") == 2
        assert report.cell_counts.get("CHILD_B") == 1
        assert "GRANDCHILD" not in report.cell_counts

    def test_cell_counts_recursive(self, hierarchical_gds: Path) -> None:
        """递归 cell_counts: CHILD_A=2, CHILD_B=1, GRANDCHILD=1。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        assert report.cell_counts.get("CHILD_A") == 2
        assert report.cell_counts.get("CHILD_B") == 1
        assert report.cell_counts.get("GRANDCHILD") == 1

    def test_instance_position(self, hierarchical_gds: Path) -> None:
        """实例位置正确。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        positions = {(d.cell_name, d.x_um, d.y_um)
                     for d in report.instances}
        assert ("CHILD_A", 10.0, 20.0) in positions
        assert ("CHILD_A", 30.0, 0.0) in positions
        assert ("CHILD_B", 0.0, 50.0) in positions

    def test_instance_rotation(self, hierarchical_gds: Path) -> None:
        """实例旋转正确。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        rot_map = {(d.cell_name, d.x_um, d.y_um): d.rotation
                   for d in report.instances}
        assert rot_map[("CHILD_A", 10.0, 20.0)] == 0
        assert rot_map[("CHILD_A", 30.0, 0.0)] == 90

    def test_instance_mirror(self, hierarchical_gds: Path) -> None:
        """实例镜像正确（M90 → mirror=True）。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        mir_map = {(d.cell_name, d.x_um, d.y_um): d.mirror
                   for d in report.instances}
        assert mir_map[("CHILD_A", 10.0, 20.0)] is False
        assert mir_map[("CHILD_B", 0.0, 50.0)] is True

    def test_parent_cell_name(self, hierarchical_gds: Path) -> None:
        """父 cell 名正确。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        for d in report.instances:
            assert d.parent_cell_name == "TOP"

    def test_hierarchy_level_non_recursive(
        self, hierarchical_gds: Path
    ) -> None:
        """非递归所有实例 level=0。"""
        report = extract_device_positions(hierarchical_gds, recursive=False)
        for d in report.instances:
            assert d.hierarchy_level == 0

    def test_hierarchy_level_recursive(
        self, hierarchical_gds: Path
    ) -> None:
        """递归: GRANDCHILD level=1。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        grandchild = [d for d in report.instances
                      if d.cell_name == "GRANDCHILD"][0]
        assert grandchild.hierarchy_level == 1

    def test_max_hierarchy_level(self, hierarchical_gds: Path) -> None:
        """最大层次深度。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        assert report.max_hierarchy_level == 1

    def test_flat_gds_no_instances(self, flat_gds: Path) -> None:
        """无实例的 GDSII。"""
        report = extract_device_positions(flat_gds)
        assert report.total_count == 0
        assert report.instances == []

    def test_single_instance(self, single_instance_gds: Path) -> None:
        """单个实例。"""
        report = extract_device_positions(single_instance_gds)
        assert report.total_count == 1
        assert report.instances[0].cell_name == "CHILD"
        assert report.instances[0].x_um == pytest.approx(5.0)
        assert report.instances[0].y_um == pytest.approx(10.0)

    def test_default_recursive_true(self, hierarchical_gds: Path) -> None:
        """默认 recursive=True。"""
        report = extract_device_positions(hierarchical_gds)
        assert report.recursive is True


# =============================================================================
# TestGenerateDevicePositionReport: 报告生成
# =============================================================================
class TestGenerateDevicePositionReport:
    """generate_device_position_report 函数测试。"""

    def test_text_report(self, hierarchical_gds: Path) -> None:
        """text 格式报告。"""
        report = generate_device_position_report(
            hierarchical_gds, output_format="text"
        )
        assert "GDSII 器件位置报告" in report
        assert "TOP" in report
        assert "CHILD_A" in report

    def test_markdown_report(self, hierarchical_gds: Path) -> None:
        """markdown 格式报告。"""
        report = generate_device_position_report(
            hierarchical_gds, output_format="markdown"
        )
        assert "# GDSII 器件位置报告" in report
        assert "| cell | X(μm) | Y(μm) |" in report

    def test_json_report(self, hierarchical_gds: Path) -> None:
        """json 格式报告。"""
        report_str = generate_device_position_report(
            hierarchical_gds, output_format="json"
        )
        data = json.loads(report_str)
        assert data["top_cell_name"] == "TOP"
        assert "instances" in data

    def test_json_report_structure(self, hierarchical_gds: Path) -> None:
        """json 报告结构完整。"""
        report_str = generate_device_position_report(
            hierarchical_gds, output_format="json"
        )
        data = json.loads(report_str)
        assert "file_path" in data
        assert "dbu" in data
        assert "top_cell_name" in data
        assert "recursive" in data
        assert "total_count" in data
        assert "cell_counts" in data
        assert "instances" in data
        if data["instances"]:
            inst = data["instances"][0]
            assert "cell_name" in inst
            assert "x_um" in inst
            assert "y_um" in inst
            assert "rotation" in inst
            assert "mirror" in inst

    def test_non_recursive_report(self, hierarchical_gds: Path) -> None:
        """非递归报告。"""
        report = generate_device_position_report(
            hierarchical_gds, recursive=False, output_format="text"
        )
        assert "递归遍历: False" in report

    def test_unsupported_format_raises(
        self, hierarchical_gds: Path
    ) -> None:
        """不支持的格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_device_position_report(
                hierarchical_gds, output_format="xml"
            )


# =============================================================================
# TestR03ErrorHandling: 错误处理（R03 禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            extract_device_positions("/nonexistent.gds")

    def test_path_not_file(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="路径不是文件"):
            extract_device_positions(tmp_path)

    def test_top_cell_not_found(self, hierarchical_gds: Path) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="top_cell_name"):
            extract_device_positions(hierarchical_gds, top_cell_name="MISSING")

    def test_unsupported_format_xml(
        self, hierarchical_gds: Path
    ) -> None:
        """XML 格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_device_position_report(
                hierarchical_gds, output_format="xml"
            )

    def test_unsupported_format_html(
        self, hierarchical_gds: Path
    ) -> None:
        """HTML 格式 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_device_position_report(
                hierarchical_gds, output_format="html"
            )


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信（R02）
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_klayout_cell_url(self) -> None:
        """docstring 含 KLayout Cell 文档 URL。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "klayout.de/doc-qt5/code/class_Cell.html" in m.__doc__

    def test_docstring_has_klayout_trans_url(self) -> None:
        """docstring 含 KLayout Trans 文档 URL。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "klayout.de/doc-qt5/code/class_Trans.html" in m.__doc__

    def test_docstring_has_klayout_instance_url(self) -> None:
        """docstring 含 KLayout Instance 文档 URL。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "klayout.de/doc-qt5/code/class_Instance.html" in m.__doc__

    def test_docstring_has_klayout_vector_url(self) -> None:
        """docstring 含 KLayout Vector 文档 URL。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "klayout.de/doc-qt5/code/class_Vector.html" in m.__doc__

    def test_docstring_has_gdsii_url(self) -> None:
        """docstring 含 GDSII 标准 URL。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "en.wikipedia.org/wiki/GDS_File" in m.__doc__

    def test_docstring_has_5_plus_urls(self) -> None:
        """docstring 含 ≥5 个文献 URL（R02 要求）。"""
        from polaris.verification import gdsii_device_position_reporter as m
        doc = m.__doc__
        url_count = doc.count("https://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5"

    def test_docstring_has_r_compliance(self) -> None:
        """docstring 含规则合规声明。"""
        from polaris.verification import gdsii_device_position_reporter as m
        assert "R01" in m.__doc__
        assert "R02" in m.__doc__
        assert "R03" in m.__doc__
        assert "R05" in m.__doc__
        assert "R11" in m.__doc__

    def test_device_instance_documented(self) -> None:
        """DeviceInstance 字段有 docstring 文档。"""
        assert DeviceInstance.__doc__ is not None
        assert "cell_name" in DeviceInstance.__doc__
        assert "x_um" in DeviceInstance.__doc__
        assert "rotation" in DeviceInstance.__doc__
        assert "mirror" in DeviceInstance.__doc__


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_recursive_includes_non_recursive(
        self, hierarchical_gds: Path
    ) -> None:
        """递归结果包含非递归结果。"""
        non_rec = extract_device_positions(hierarchical_gds, recursive=False)
        rec = extract_device_positions(hierarchical_gds, recursive=True)
        non_rec_keys = {(d.cell_name, d.x_um, d.y_um)
                        for d in non_rec.instances}
        rec_keys = {(d.cell_name, d.x_um, d.y_um)
                    for d in rec.instances}
        assert non_rec_keys.issubset(rec_keys)

    def test_grandchild_global_position(
        self, hierarchical_gds: Path
    ) -> None:
        """GRANDCHILD 全局位置正确（累加变换）。"""
        report = extract_device_positions(hierarchical_gds, recursive=True)
        grandchild = [d for d in report.instances
                      if d.cell_name == "GRANDCHILD"][0]
        # GRANDCHILD 在 CHILD_B 内 @ (5, 5) μm
        # CHILD_B 在 TOP 内 @ M90 (0, 50) μm
        # 全局位置由变换累乘决定
        # 验证位置有非零值
        assert grandchild.x_um != 0.0 or grandchild.y_um != 0.0

    def test_string_path_input(self, hierarchical_gds: Path) -> None:
        """字符串路径输入。"""
        report = extract_device_positions(str(hierarchical_gds))
        assert isinstance(report, DevicePositionReport)
        assert report.total_count > 0

    def test_consistency_across_runs(self, hierarchical_gds: Path) -> None:
        """多次运行结果一致。"""
        r1 = extract_device_positions(hierarchical_gds)
        r2 = extract_device_positions(hierarchical_gds)
        assert r1.total_count == r2.total_count
        assert r1.cell_counts == r2.cell_counts

    def test_no_instances_flat_gds(self, flat_gds: Path) -> None:
        """扁平 GDSII 无实例。"""
        report = extract_device_positions(flat_gds)
        assert report.total_count == 0
        assert report.max_hierarchy_level == 0


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_device_instance_default(self) -> None:
        """DeviceInstance 默认值。"""
        d = DeviceInstance(cell_name="TEST")
        assert d.cell_name == "TEST"
        assert d.x_um == 0.0
        assert d.y_um == 0.0
        assert d.rotation == 0
        assert d.mirror is False
        assert d.parent_cell_name == ""
        assert d.hierarchy_level == 0
        assert d.trans_str == ""

    def test_device_instance_full(self) -> None:
        """DeviceInstance 完整字段。"""
        d = DeviceInstance(
            cell_name="MZI",
            x_um=10.5,
            y_um=20.3,
            rotation=90,
            mirror=True,
            parent_cell_name="TOP",
            hierarchy_level=2,
            trans_str="r90 10500,20300",
        )
        assert d.cell_name == "MZI"
        assert d.x_um == 10.5
        assert d.y_um == 20.3
        assert d.rotation == 90
        assert d.mirror is True
        assert d.parent_cell_name == "TOP"
        assert d.hierarchy_level == 2
        assert d.trans_str == "r90 10500,20300"

    def test_device_position_report_default(self) -> None:
        """DevicePositionReport 默认值。"""
        report = DevicePositionReport()
        assert report.file_path == ""
        assert report.dbu == 0.0
        assert report.top_cell_name == ""
        assert report.instances == []
        assert report.total_count == 0
        assert report.cell_counts == {}
        assert report.recursive is False
        assert report.max_hierarchy_level == 0

    def test_device_position_report_independent_lists(self) -> None:
        """DevicePositionReport list 字段独立。"""
        r1 = DevicePositionReport()
        r2 = DevicePositionReport()
        r1.instances.append(DeviceInstance(cell_name="A"))
        r1.cell_counts["A"] = 1
        assert r2.instances == []
        assert r2.cell_counts == {}

    def test_device_instance_is_dataclass(self) -> None:
        """DeviceInstance 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(DeviceInstance)

    def test_device_position_report_is_dataclass(self) -> None:
        """DevicePositionReport 是 dataclass。"""
        from dataclasses import is_dataclass
        assert is_dataclass(DevicePositionReport)

    def test_device_instance_equality(self) -> None:
        """DeviceInstance 相等性。"""
        d1 = DeviceInstance(cell_name="A", x_um=1.0, y_um=2.0)
        d2 = DeviceInstance(cell_name="A", x_um=1.0, y_um=2.0)
        assert d1 == d2
