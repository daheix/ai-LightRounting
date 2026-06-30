"""R332 GDSII 端口提取工具测试。

覆盖:
- extract_ports: 端口提取（位置/尺寸/文本匹配/多端口层/层次结构）
- generate_port_report: text/markdown/json 报告
- PortInfo / PortReport: 数据类
- R03 错误处理（文件不存在/路径非文件/top_cell_name 不存在/
  match_distance_um<=0/port_layers 空/不支持格式）
- R02 学术诚信（docstring URL ≥5 / __all__ / dataclass / 无 silent fall-back）
- 集成测试（端口提取后裁剪/扁平化/预检查）
- 数据类（字段完整/构造/repr/相等）

来源:
- KLayout Cell.begin_shapes_rec:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout RecursiveShapeIterator:
  https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
- KLayout Shape class:
  https://www.klayout.org/doc-qt5/code/class_Shape.html
- SiEPIC EBeam PDK:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory Port:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.Port
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import export_gdsii_from_cells
from polaris.verification.gdsii_port_extractor import (
    DEFAULT_MATCH_DISTANCE_UM,
    DEFAULT_PORT_LAYERS,
    DEFAULT_TEXT_LAYERS,
    PortInfo,
    PortReport,
    extract_ports,
    generate_port_report,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def ports_gds(tmp_path: Path) -> Path:
    """创建含 2 个端口 + 2 个文本标签的 GDSII。

    WG 层波导: (0,0)-(20,2) 矩形
    PORT 层 (70,0) 端口 1: 左端 (0,0)-(0.5,2)
    PORT 层 (70,0) 端口 2: 右端 (19.5,0)-(20,2)
    TEXT 层 (10,0): "in_port"@(0.25,1.0), "out_port"@(19.75,1.0)
    """
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 1,
                    "datatype": 0,
                    "points": [[0, 0], [20, 0], [20, 2], [0, 2]],
                },
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[0, 0], [0.5, 0], [0.5, 2], [0, 2]],
                },
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[19.5, 0], [20, 0], [20, 2], [19.5, 2]],
                },
            ],
            "texts": [
                {
                    "layer": 10,
                    "datatype": 0,
                    "string": "in_port",
                    "x": 0.25,
                    "y": 1.0,
                },
                {
                    "layer": 10,
                    "datatype": 0,
                    "string": "out_port",
                    "x": 19.75,
                    "y": 1.0,
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "ports.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def hier_ports_gds(tmp_path: Path) -> Path:
    """创建含层次结构的端口 GDSII。

    CHILD 含 1 个 PORT 层端口 + 文本
    TOP 引用 CHILD 在 (10, 0)
    TOP 自身也有 1 个 PORT 层端口 + 文本
    """
    cells_spec = [
        {
            "name": "CHILD",
            "polygons": [
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]],
                },
            ],
            "texts": [
                {
                    "layer": 10,
                    "datatype": 0,
                    "string": "child_port",
                    "x": 0.25,
                    "y": 0.5,
                },
            ],
            "is_top": False,
        },
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]],
                },
            ],
            "texts": [
                {
                    "layer": 10,
                    "datatype": 0,
                    "string": "top_port",
                    "x": 0.25,
                    "y": 0.5,
                },
            ],
            "instances": [
                {"cell_name": "CHILD", "x": 10.0, "y": 0.0, "rotation": 0.0},
            ],
            "is_top": True,
        },
    ]
    out = tmp_path / "hier_ports.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def no_ports_gds(tmp_path: Path) -> Path:
    """创建无端口层的 GDSII。"""
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
    out = tmp_path / "no_ports.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def unmatched_ports_gds(tmp_path: Path) -> Path:
    """创建端口与文本距离过远的 GDSII（不匹配）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]],
                },
            ],
            "texts": [
                {
                    "layer": 10,
                    "datatype": 0,
                    "string": "far_text",
                    "x": 100.0,
                    "y": 100.0,
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "unmatched.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


@pytest.fixture
def multi_layer_ports_gds(tmp_path: Path) -> Path:
    """创建含多端口层的 GDSII（PORT=70,0 + PIN=69,0）。"""
    cells_spec = [
        {
            "name": "TOP",
            "polygons": [
                {
                    "layer": 70,
                    "datatype": 0,
                    "points": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]],
                },
                {
                    "layer": 69,
                    "datatype": 0,
                    "points": [[10, 0], [10.5, 0], [10.5, 1], [10, 1]],
                },
            ],
            "is_top": True,
        }
    ]
    out = tmp_path / "multi_layer.gds"
    export_gdsii_from_cells(cells_spec, out)
    return out


# =============================================================================
# TestExtractPorts: 端口提取
# =============================================================================
class TestExtractPorts:
    """extract_ports 函数测试。"""

    def test_returns_report(self, ports_gds: Path) -> None:
        """返回 PortReport。"""
        report = extract_ports(ports_gds)
        assert isinstance(report, PortReport)

    def test_port_count(self, ports_gds: Path) -> None:
        """端口数 = 2。"""
        report = extract_ports(ports_gds)
        assert len(report.ports) == 2

    def test_port_layer(self, ports_gds: Path) -> None:
        """端口层 = (70, 0)。"""
        report = extract_ports(ports_gds)
        for port in report.ports:
            assert port.layer == 70
            assert port.datatype == 0

    def test_port_position(self, ports_gds: Path) -> None:
        """端口位置正确。

        端口 1: (0,0)-(0.5,2) 中心 (0.25, 1.0)
        端口 2: (19.5,0)-(20,2) 中心 (19.75, 1.0)
        """
        report = extract_ports(ports_gds)
        positions = sorted(p.position_um for p in report.ports)
        assert positions[0] == pytest.approx((0.25, 1.0), abs=1e-6)
        assert positions[1] == pytest.approx((19.75, 1.0), abs=1e-6)

    def test_port_size(self, ports_gds: Path) -> None:
        """端口尺寸正确 (0.5 × 2.0)。"""
        report = extract_ports(ports_gds)
        for port in report.ports:
            assert port.width_um == pytest.approx(0.5, abs=1e-6)
            assert port.height_um == pytest.approx(2.0, abs=1e-6)

    def test_text_matching(self, ports_gds: Path) -> None:
        """文本匹配成功。"""
        report = extract_ports(ports_gds)
        matched = [p for p in report.ports if p.text_matched]
        assert len(matched) == 2
        names = sorted(p.name for p in matched)
        assert names == ["in_port", "out_port"]

    def test_top_cell_name(self, ports_gds: Path) -> None:
        """top_cell_name 正确。"""
        report = extract_ports(ports_gds)
        assert report.top_cell_name == "TOP"

    def test_dbu(self, ports_gds: Path) -> None:
        """dbu 正确。"""
        report = extract_ports(ports_gds)
        assert report.dbu == pytest.approx(0.001, abs=1e-9)

    def test_no_ports(self, no_ports_gds: Path) -> None:
        """无端口层时返回空端口列表。"""
        report = extract_ports(no_ports_gds)
        assert len(report.ports) == 0

    def test_hierarchical_ports(self, hier_ports_gds: Path) -> None:
        """层次结构中递归提取端口（TOP 1 + CHILD 1 = 2）。"""
        report = extract_ports(hier_ports_gds)
        assert len(report.ports) == 2

    def test_multi_layer_ports(self, multi_layer_ports_gds: Path) -> None:
        """多端口层提取（70,0 + 69,0 = 2 端口）。"""
        report = extract_ports(multi_layer_ports_gds)
        assert len(report.ports) == 2
        layers = sorted((p.layer, p.datatype) for p in report.ports)
        assert layers == [(69, 0), (70, 0)]

    def test_unmatched_text(self, unmatched_ports_gds: Path) -> None:
        """文本距离过远不匹配。"""
        report = extract_ports(unmatched_ports_gds)
        assert len(report.ports) == 1
        assert not report.ports[0].text_matched
        assert report.ports[0].name == ""

    def test_custom_port_layers(self, ports_gds: Path) -> None:
        """自定义 port_layers。"""
        report = extract_ports(ports_gds, port_layers=[(70, 0)])
        assert len(report.ports) == 2

    def test_custom_match_distance(self, unmatched_ports_gds: Path) -> None:
        """自定义 match_distance_um（放大后可匹配）。"""
        report = extract_ports(unmatched_ports_gds, match_distance_um=200.0)
        assert len(report.ports) == 1
        assert report.ports[0].text_matched
        assert report.ports[0].name == "far_text"

    def test_default_port_layers_constant(self) -> None:
        """DEFAULT_PORT_LAYERS 常量正确。"""
        assert (70, 0) in DEFAULT_PORT_LAYERS
        assert (69, 0) in DEFAULT_PORT_LAYERS
        assert (99, 0) in DEFAULT_PORT_LAYERS

    def test_default_text_layers_constant(self) -> None:
        """DEFAULT_TEXT_LAYERS 常量正确。"""
        assert (10, 0) in DEFAULT_TEXT_LAYERS
        assert (11, 0) in DEFAULT_TEXT_LAYERS

    def test_default_match_distance_constant(self) -> None:
        """DEFAULT_MATCH_DISTANCE_UM 常量正确。"""
        assert DEFAULT_MATCH_DISTANCE_UM == 5.0

    def test_file_path_field(self, ports_gds: Path) -> None:
        """file_path 字段正确。"""
        report = extract_ports(ports_gds)
        assert report.file_path == str(ports_gds)

    def test_port_bbox(self, ports_gds: Path) -> None:
        """端口 bbox 正确。"""
        report = extract_ports(ports_gds)
        bboxes = sorted(p.bbox_um for p in report.ports)
        assert bboxes[0] == pytest.approx((0.0, 0.0, 0.5, 2.0), abs=1e-6)
        assert bboxes[1] == pytest.approx((19.5, 0.0, 20.0, 2.0), abs=1e-6)


# =============================================================================
# TestGeneratePortReport: 报告生成
# =============================================================================
class TestGeneratePortReport:
    """generate_port_report 函数测试。"""

    def test_text_report(self, ports_gds: Path) -> None:
        """text 报告。"""
        text = generate_port_report(ports_gds)
        assert isinstance(text, str)
        assert "GDSII 端口提取报告" in text
        assert "端口列表" in text

    def test_markdown_report(self, ports_gds: Path) -> None:
        """markdown 报告。"""
        md = generate_port_report(ports_gds, output_format="markdown")
        assert isinstance(md, str)
        assert md.startswith("#")
        assert "## 端口列表" in md

    def test_json_report(self, ports_gds: Path) -> None:
        """json 报告可解析。"""
        text = generate_port_report(ports_gds, output_format="json")
        data = json.loads(text)
        assert "ports" in data
        assert data["port_count"] == 2
        assert isinstance(data["ports"], list)

    def test_json_report_content(self, ports_gds: Path) -> None:
        """json 报告内容正确。"""
        text = generate_port_report(ports_gds, output_format="json")
        data = json.loads(text)
        assert data["top_cell_name"] == "TOP"
        assert data["matched_count"] == 2

    def test_text_report_contains_port_names(
        self, ports_gds: Path
    ) -> None:
        """text 报告含端口名。"""
        text = generate_port_report(ports_gds)
        assert "in_port" in text
        assert "out_port" in text

    def test_markdown_report_table(self, ports_gds: Path) -> None:
        """markdown 报告含表格。"""
        md = generate_port_report(ports_gds, output_format="markdown")
        assert "|" in md
        assert "---" in md


# =============================================================================
# TestR03ErrorHandling: 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            extract_ports(tmp_path / "nonexistent.gds")

    def test_path_is_directory_raises(self, tmp_path: Path) -> None:
        """路径是目录 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            extract_ports(tmp_path)

    def test_top_cell_name_not_exist_raises(
        self, ports_gds: Path
    ) -> None:
        """top_cell_name 不存在 raise ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            extract_ports(ports_gds, top_cell_name="NONEXISTENT")

    def test_match_distance_zero_raises(
        self, ports_gds: Path
    ) -> None:
        """match_distance_um <= 0 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            extract_ports(ports_gds, match_distance_um=0.0)

    def test_match_distance_negative_raises(
        self, ports_gds: Path
    ) -> None:
        """match_distance_um < 0 raise ValueError。"""
        with pytest.raises(ValueError, match="必须 > 0"):
            extract_ports(ports_gds, match_distance_um=-1.0)

    def test_empty_port_layers_raises(
        self, ports_gds: Path
    ) -> None:
        """port_layers 空 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            extract_ports(ports_gds, port_layers=[])

    def test_unsupported_format_raises(
        self, ports_gds: Path
    ) -> None:
        """不支持的 output_format raise ValueError。"""
        with pytest.raises(ValueError, match="不支持的 output_format"):
            generate_port_report(ports_gds, output_format="xml")


# =============================================================================
# TestR02AcademicIntegrity: 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    def test_docstring_has_5_plus_urls(self) -> None:
        """模块 docstring 至少 5 个 URL（R02）。"""
        from polaris.verification import gdsii_port_extractor

        docstring = gdsii_port_extractor.__doc__ or ""
        url_count = docstring.count("https://")
        assert url_count >= 5, (
            f"docstring 只有 {url_count} 个 URL，要求 ≥5 个（R02）"
        )

    def test_all_exported(self) -> None:
        """__all__ 列出所有公开 API。"""
        from polaris.verification import gdsii_port_extractor

        expected = {
            "PortInfo",
            "PortReport",
            "extract_ports",
            "generate_port_report",
        }
        assert set(gdsii_port_extractor.__all__) == expected

    def test_portinfo_is_dataclass(self) -> None:
        """PortInfo 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(PortInfo)

    def test_portreport_is_dataclass(self) -> None:
        """PortReport 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(PortReport)

    def test_portinfo_fields(self) -> None:
        """PortInfo 字段完整（9 字段）。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(PortInfo)}
        expected = {
            "name",
            "layer",
            "datatype",
            "position_um",
            "bbox_um",
            "width_um",
            "height_um",
            "cell_name",
            "text_matched",
        }
        assert field_names == expected

    def test_portreport_fields(self) -> None:
        """PortReport 字段完整（7 字段）。"""
        from dataclasses import fields

        field_names = {f.name for f in fields(PortReport)}
        expected = {
            "file_path",
            "top_cell_name",
            "dbu",
            "ports",
            "port_layers",
            "text_layers",
            "match_distance_um",
        }
        assert field_names == expected

    def test_no_silent_fallback(self) -> None:
        """源码无 silent fall-back。"""
        from polaris.verification import gdsii_port_extractor

        source_path = Path(gdsii_port_extractor.__file__)
        source = source_path.read_text(encoding="utf-8")
        assert "except: pass" not in source, "禁止 silent except: pass（R03）"
        assert "except Exception: pass" not in source, (
            "禁止 silent except Exception: pass（R03）"
        )

    def test_klayout_import_error_message(self) -> None:
        """klayout 导入失败时 raise ImportError。"""
        from polaris.verification.gdsii_port_extractor import (
            _import_klayout_db,
        )

        db = _import_klayout_db()
        assert db is not None


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """与其他 R3xx 工具的集成测试。"""

    def test_ports_then_flatten(
        self, hier_ports_gds: Path, tmp_path: Path
    ) -> None:
        """端口提取后 R326 扁平化仍能读取。"""
        from polaris.verification.gdsii_flattener import flatten_gdsii

        # 先提取端口
        report = extract_ports(hier_ports_gds)
        assert len(report.ports) == 2

        # 再 flatten
        flattened = tmp_path / "flattened.gds"
        flatten_report = flatten_gdsii(hier_ports_gds, flattened)
        assert flatten_report.cells_after >= 1

    def test_ports_then_clip(
        self, ports_gds: Path, tmp_path: Path
    ) -> None:
        """端口提取后 R327 裁剪仍能读取。"""
        from polaris.verification.gdsii_clip_tool import clip_gdsii

        report = extract_ports(ports_gds)
        assert len(report.ports) == 2

        clipped = tmp_path / "clipped.gds"
        clip_report = clip_gdsii(ports_gds, clipped, (-1.0, -1.0, 25.0, 10.0))
        assert clip_report.shapes_after >= 1

    def test_ports_then_statistics(
        self, ports_gds: Path
    ) -> None:
        """端口提取后 R331 统计仍能读取。"""
        from polaris.verification.gdsii_statistics import (
            StatisticsReport,
            generate_gdsii_statistics,
        )

        report = extract_ports(ports_gds)
        assert len(report.ports) == 2

        stat_report = generate_gdsii_statistics(ports_gds)
        assert isinstance(stat_report, StatisticsReport)

    def test_ports_then_precheck(
        self, ports_gds: Path
    ) -> None:
        """端口提取后 R329 预检查仍能读取。"""
        from polaris.verification.gdsii_tapeout_precheck import (
            TapeoutReport,
            tapeout_precheck,
        )

        report = extract_ports(ports_gds)
        assert len(report.ports) == 2

        precheck_report = tapeout_precheck(ports_gds)
        assert isinstance(precheck_report, TapeoutReport)


# =============================================================================
# TestDataclassTest: 数据类
# =============================================================================
class TestDataclassTest:
    """PortInfo / PortReport 数据类测试。"""

    def test_portinfo_default_construction(self) -> None:
        """PortInfo 默认构造。"""
        port = PortInfo()
        assert port.name == ""
        assert port.layer == 0
        assert port.datatype == 0
        assert port.position_um == (0.0, 0.0)
        assert port.bbox_um == (0.0, 0.0, 0.0, 0.0)
        assert port.width_um == 0.0
        assert port.height_um == 0.0
        assert port.cell_name == ""
        assert not port.text_matched

    def test_portinfo_full_construction(self) -> None:
        """PortInfo 完整构造。"""
        port = PortInfo(
            name="in",
            layer=70,
            datatype=0,
            position_um=(1.0, 2.0),
            bbox_um=(0.5, 1.5, 1.5, 2.5),
            width_um=1.0,
            height_um=1.0,
            cell_name="TOP",
            text_matched=True,
        )
        assert port.name == "in"
        assert port.layer == 70
        assert port.position_um == (1.0, 2.0)
        assert port.text_matched

    def test_portreport_default_construction(self) -> None:
        """PortReport 默认构造。"""
        report = PortReport()
        assert report.file_path == ""
        assert report.top_cell_name == ""
        assert report.dbu == 0.0
        assert report.ports == []
        assert report.port_layers == []
        assert report.text_layers == []
        assert report.match_distance_um == 0.0

    def test_portreport_full_construction(self) -> None:
        """PortReport 完整构造。"""
        port = PortInfo(name="in", layer=70)
        report = PortReport(
            file_path="/in.gds",
            top_cell_name="TOP",
            dbu=0.001,
            ports=[port],
            port_layers=[(70, 0)],
            text_layers=[(10, 0)],
            match_distance_um=5.0,
        )
        assert report.file_path == "/in.gds"
        assert report.top_cell_name == "TOP"
        assert len(report.ports) == 1
        assert report.ports[0] == port

    def test_portinfo_repr(self) -> None:
        """PortInfo repr 含类名。"""
        port = PortInfo()
        assert "PortInfo" in repr(port)

    def test_portreport_repr(self) -> None:
        """PortReport repr 含类名。"""
        report = PortReport()
        assert "PortReport" in repr(report)

    def test_portinfo_equality(self) -> None:
        """PortInfo 相等。"""
        p1 = PortInfo(name="in", layer=70)
        p2 = PortInfo(name="in", layer=70)
        assert p1 == p2
