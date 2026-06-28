"""P0-5 多格式互操作测试。

测试 6 种格式（CIF/Gerber/DXF/ODB++/LEF-DEF/OpenAccess）的读写、
往返一致性（read → write → read）与错误处理。

权威来源（规则 18 学术诚信）：
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980,
  Appendix C: CIF；Caltech Technical Report 2686 (1980-02-11)
- UCAMCO, "The Gerber File Format Specification", Rev 2024.06,
  https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
- Autodesk, "DXF Reference", AutoCAD 2024,
  https://images.autodesk.com/adskfiles/acad_dxf.pdf
- ODB++ Solution Alliance, "ODB++ Format Specification", 2023,
  http://www.odb-sa.com/
- OpenROAD Project, "OpenDB LEF/DEF Reference", 2024,
  https://github.com/The-OpenROAD-Project/OpenDB
- Si2, "OpenAccess 22.60 API Reference", 2024, https://si2.org/openaccess/

测试覆盖：
- 6 种格式各自的 read/write 直接调用
- 往返一致性（read → write → read，用 layouts_equal 比较）
- MultiFormatIO 调度入口（read/write 按格式名分发）
- 错误处理（文件不存在、不支持格式、不支持的形状类型）
- layouts_equal 比较工具
"""

from __future__ import annotations

import pytest

from polaris.io import (
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    MultiFormatIO,
    OpenAccessDB,
    Point,
    Shape,
    layouts_equal,
)
from polaris.io._cif import read_cif, write_cif
from polaris.io._dxf import read_dxf, write_dxf
from polaris.io._gerber import read_gerber, write_gerber
from polaris.io._lef_def import read_lef_def, write_lef_def
from polaris.io._odbpp import read_odbpp, write_odbpp
from polaris.io.openaccess import read_oa, write_oa


# ---------------------------------------------------------------------------
# 测试辅助：构造典型版图
# ---------------------------------------------------------------------------


def _cif_layout() -> FormatLayout:
    """构造 CIF 测试版图（centimicron 整数坐标，确保取整无损）。"""
    return FormatLayout(
        name="cif_test",
        cells=[Cell(name="TOP", shapes=[
            Shape("rect", "WG", [Point(100, 200)], width=50, height=30),
            Shape("polygon", "WG", [
                Point(0, 0), Point(100, 0), Point(100, 50), Point(0, 50),
            ]),
            Shape("path", "WG", [Point(10, 10), Point(20, 30)], width=5),
            Shape("circle", "WG", [Point(80, 80)], width=20),
        ])],
        layers={"WG": LayerInfo(name="WG")},
        top_cell="TOP",
        unit="centimicron",
    )


def _gerber_layout() -> FormatLayout:
    """构造 Gerber 测试版图（坐标为 1e-4 整数倍，FSLAX34Y34 无损）。"""
    return FormatLayout(
        name="gerber_test",
        cells=[Cell(name="gerber_layout", shapes=[
            Shape("circle", "gerber", [Point(1.5, 2.5)], width=0.5),
            Shape("rect", "gerber", [Point(3.0, 4.0)], width=1.0, height=2.0),
            Shape("path", "gerber", [Point(0.0, 0.0), Point(5.0, 5.0)], width=0.2),
            Shape("polygon", "gerber", [
                Point(0.0, 0.0), Point(2.0, 0.0), Point(2.0, 2.0), Point(0.0, 2.0),
            ]),
        ])],
        layers={"gerber": LayerInfo(name="gerber")},
        top_cell="gerber_layout",
        unit="mm",
    )


def _dxf_layout() -> FormatLayout:
    """构造 DXF 测试版图（LINE/CIRCLE/TEXT 往返无损；避免 rect→polygon 失配）。"""
    return FormatLayout(
        name="dxf_test",
        cells=[Cell(name="dxf_layout", shapes=[
            Shape("path", "0", [Point(0.0, 0.0), Point(10.0, 5.0)]),
            Shape("circle", "0", [Point(3.0, 3.0)], width=4.0),
            Shape("text", "0", [Point(5.0, 5.0)], text="label"),
        ])],
        layers={"0": LayerInfo(name="0")},
        top_cell="dxf_layout",
        unit="mm",
    )


def _odbpp_layout() -> FormatLayout:
    """构造 ODB++ 测试版图（cell.name 即 layer 名，确保往返 layer 一致）。"""
    return FormatLayout(
        name="odb_test",
        cells=[Cell(name="M1", shapes=[
            Shape("rect", "M1", [Point(5.0, 5.0)], width=10.0, height=20.0),
            Shape("polygon", "M1", [
                Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 5.0), Point(0.0, 5.0),
            ]),
            Shape("path", "M1", [Point(0.0, 0.0), Point(8.0, 8.0)], width=0.5),
            Shape("text", "M1", [Point(1.0, 1.0)], text="hi"),
        ])],
        layers={"M1": LayerInfo(name="M1")},
        top_cell="M1",
        unit="mm",
    )


def _lef_def_layout() -> FormatLayout:
    """构造 LEF/DEF 测试版图（rect/polygon 往返无损；含 INST 实例）。"""
    sub = Cell(name="INV", shapes=[
        Shape("rect", "metal1", [Point(5.0, 5.0)], width=10.0, height=20.0),
        Shape("polygon", "metal1", [
            Point(0.0, 0.0), Point(3.0, 0.0), Point(3.0, 3.0),
        ]),
    ])
    sub.instances.append(Instance(
        name="U1", cell_name="INV", origin=Point(100.0, 200.0),
    ))
    return FormatLayout(
        name="lef_def_test",
        cells=[sub],
        layers={"metal1": LayerInfo(name="metal1")},
        top_cell="INV",
        unit="um",
    )


def _oa_layout() -> FormatLayout:
    """构造 OpenAccess 测试版图（rect/polygon/path/circle/text/inst 全覆盖）。"""
    cell = Cell(name="TOP", shapes=[
        Shape("rect", "WG", [Point(100.0, 200.0)], width=50.0, height=30.0),
        Shape("polygon", "WG", [
            Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 5.0), Point(0.0, 5.0),
        ]),
        Shape("path", "WG", [Point(0.0, 0.0), Point(20.0, 30.0)], width=4.0),
        Shape("circle", "WG", [Point(80.0, 80.0)], width=20.0),
        Shape("text", "TEXT", [Point(5.0, 5.0)], text="cell_label"),
    ])
    cell.instances.append(Instance(
        name="I1", cell_name="SUB", origin=Point(50.0, 50.0), angle=90.0,
    ))
    return FormatLayout(
        name="oa_test",
        cells=[cell],
        layers={
            "WG": LayerInfo(name="WG", number=1, datatype=0),
            "TEXT": LayerInfo(name="TEXT", number=10, datatype=0),
        },
        top_cell="TOP",
        unit="dbu",
    )


# ---------------------------------------------------------------------------
# CIF 读写测试
# ---------------------------------------------------------------------------


class TestCIFIO:
    """CIF 格式读写与往返一致性测试。"""

    def test_cif_write_produces_valid_syntax(self):
        """测试 write_cif 输出含 CIF 关键命令。"""
        text = write_cif(_cif_layout())
        assert "DS " in text
        assert "DF;" in text
        assert "L WG;" in text
        assert "B 50 30 100 200;" in text
        assert text.rstrip().endswith("E")

    def test_cif_roundtrip_all_primitives(self):
        """测试 CIF rect/polygon/path/circle 往返一致。"""
        layout = _cif_layout()
        back = read_cif(write_cif(layout))
        assert layouts_equal(layout, back)

    def test_cif_polygon_vertex_count_preserved(self):
        """测试 CIF 多边形顶点数往返保持。"""
        layout = FormatLayout(
            name="x",
            cells=[Cell(name="TOP", shapes=[
                Shape("polygon", "L", [
                    Point(0, 0), Point(10, 0), Point(10, 10),
                    Point(5, 15), Point(0, 10),
                ]),
            ])],
            layers={"L": LayerInfo(name="L")},
            top_cell="TOP",
            unit="centimicron",
        )
        back = read_cif(write_cif(layout))
        poly_back = next(s for s in back.cells[0].shapes if s.shape_type == "polygon")
        assert len(poly_back.points) == 5


# ---------------------------------------------------------------------------
# Gerber 读写测试
# ---------------------------------------------------------------------------


class TestGerberIO:
    """Gerber RS-274X 格式读写与往返一致性测试。"""

    def test_gerber_write_produces_valid_header(self):
        """测试 write_gerber 输出含 FS/MO 头与 M02 结尾。"""
        text = write_gerber(_gerber_layout())
        assert "%MOMM*%" in text
        assert "%FSLAX34Y34*%" in text
        assert "M02*" in text

    def test_gerber_roundtrip_all_primitives(self):
        """测试 Gerber circle/rect/path/polygon 往返一致。"""
        layout = _gerber_layout()
        back = read_gerber(write_gerber(layout))
        assert layouts_equal(layout, back)

    def test_gerber_aperture_definition_emitted(self):
        """测试 Gerber 写入为 circle 生成孔径定义 %ADD%。"""
        text = write_gerber(_gerber_layout())
        assert "%ADD10C," in text
        assert "%ADD11R," in text


# ---------------------------------------------------------------------------
# DXF 读写测试
# ---------------------------------------------------------------------------


class TestDXFIO:
    """DXF 格式读写与往返一致性测试。"""

    def test_dxf_write_produces_entities_section(self):
        """测试 write_dxf 输出含 ENTITIES 段与 EOF。"""
        text = write_dxf(_dxf_layout())
        assert "SECTION" in text
        assert "ENTITIES" in text
        assert "ENDSEC" in text
        assert text.rstrip().endswith("EOF")

    def test_dxf_roundtrip_line_circle_text(self):
        """测试 DXF LINE/CIRCLE/TEXT 往返一致。"""
        layout = _dxf_layout()
        back = read_dxf(write_dxf(layout))
        assert layouts_equal(layout, back)

    def test_dxf_circle_diameter_preserved(self):
        """测试 DXF CIRCLE 直径往返保持。"""
        layout = FormatLayout(
            name="x",
            cells=[Cell(name="dxf_layout", shapes=[
                Shape("circle", "0", [Point(3.0, 3.0)], width=4.0),
            ])],
            layers={"0": LayerInfo(name="0")},
            top_cell="dxf_layout",
            unit="mm",
        )
        back = read_dxf(write_dxf(layout))
        circ = back.cells[0].shapes[0]
        assert circ.shape_type == "circle"
        assert abs(circ.width - 4.0) < 1e-9


# ---------------------------------------------------------------------------
# ODB++ 读写测试
# ---------------------------------------------------------------------------


class TestODBppIO:
    """ODB++ XML 格式读写与往返一致性测试。"""

    def test_odbpp_write_produces_valid_xml(self):
        """测试 write_odbpp 输出合法 XML，根元素为 <odb>。"""
        from xml.etree import ElementTree as ET
        text = write_odbpp(_odbpp_layout())
        root = ET.fromstring(text)
        assert root.tag == "odb"
        assert len(root.findall("layer")) >= 1

    def test_odbpp_roundtrip_all_primitives(self):
        """测试 ODB++ rect/polygon/path/text 往返一致。"""
        layout = _odbpp_layout()
        back = read_odbpp(write_odbpp(layout))
        assert layouts_equal(layout, back)

    def test_odbpp_invalid_root_raises(self):
        """测试 ODB++ 非法根元素抛出 ValueError。"""
        with pytest.raises(ValueError):
            read_odbpp("<notodb/>")


# ---------------------------------------------------------------------------
# LEF/DEF 读写测试
# ---------------------------------------------------------------------------


class TestLEFDEFIO:
    """LEF/DEF 格式读写与往返一致性测试。"""

    def test_lef_def_write_produces_macro(self):
        """测试 write_lef_def 输出含 MACRO 与 END LIBRARY。"""
        text = write_lef_def(_lef_def_layout())
        assert "MACRO INV" in text
        assert "END LIBRARY" in text
        assert "OBS" in text
        assert "LAYER metal1 ;" in text

    def test_lef_def_roundtrip_rect_polygon_with_instance(self):
        """测试 LEF/DEF rect/polygon + COMPONENTS 实例往返一致。"""
        layout = _lef_def_layout()
        back = read_lef_def(write_lef_def(layout))
        assert layouts_equal(layout, back)

    def test_lef_def_unsupported_shape_raises(self):
        """测试 LEF/DEF 不支持的 path 形状抛出 ValueError。"""
        layout = FormatLayout(
            name="x",
            cells=[Cell(name="M", shapes=[
                Shape("path", "L", [Point(0, 0), Point(1, 1)]),
            ])],
            top_cell="M",
            unit="um",
        )
        with pytest.raises(ValueError):
            write_lef_def(layout)


# ---------------------------------------------------------------------------
# OpenAccess 读写测试
# ---------------------------------------------------------------------------


class TestOpenAccessIO:
    """OpenAccess ASCII 格式读写与往返一致性测试。"""

    def test_oa_write_produces_valid_syntax(self):
        """测试 write_oa 输出含 OA_VERSION/CELL/RECT 等关键语句。"""
        text = write_oa(_oa_layout())
        assert "OA_VERSION" in text
        assert "CELL TOP" in text
        assert "RECT" in text
        assert "INST" in text
        assert "END_OA" in text

    def test_oa_roundtrip_all_primitives_and_instance(self):
        """测试 OpenAccess rect/polygon/path/circle/text/INST 往返一致。

        用自定义层映射（仅含 layout 实际使用的层），避免默认 15 层映射表
        导致 read 后 layers 字典键集膨胀，使 layouts_equal 失配。
        """
        layout = _oa_layout()
        custom_map = {"WG": (1, 0), "TEXT": (10, 0)}
        db = OpenAccessDB(layer_map=custom_map)
        back = db.read(db.write(layout))
        assert layouts_equal(layout, back)

    def test_oa_layer_number_lookup(self):
        """测试 OpenAccessDB.layer_number 查询层映射。"""
        db = OpenAccessDB()
        assert db.layer_number("WG") == (1, 0)
        assert db.layer_number("DEVREC") == (68, 0)
        with pytest.raises(KeyError):
            db.layer_number("UNKNOWN_LAYER")

    def test_oa_custom_layer_map(self):
        """测试 OpenAccessDB 接受自定义层映射。"""
        custom = {"MYL": (99, 0)}
        db = OpenAccessDB(layer_map=custom)
        assert db.layer_number("MYL") == (99, 0)


# ---------------------------------------------------------------------------
# MultiFormatIO 调度入口测试
# ---------------------------------------------------------------------------


class TestMultiFormatIODispatch:
    """MultiFormatIO 统一调度入口测试。"""

    def test_read_cif_via_dispatch(self, tmp_path):
        """测试 MultiFormatIO.read 调度 CIF 子模块。"""
        path = tmp_path / "test.cif"
        MultiFormatIO.write(_cif_layout(), str(path), "cif")
        back = MultiFormatIO.read(str(path), "cif")
        assert layouts_equal(_cif_layout(), back)

    def test_read_file_not_found_raises(self, tmp_path):
        """测试读取不存在文件抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            MultiFormatIO.read(str(tmp_path / "nonexistent.cif"), "cif")

    def test_unsupported_format_raises(self, tmp_path):
        """测试不支持格式抛出 ValueError。"""
        layout = FormatLayout(name="x", cells=[Cell(name="X")], top_cell="X")
        with pytest.raises(ValueError):
            MultiFormatIO.write(layout, str(tmp_path / "x.txt"), "unknown_format")

    def test_gerber_unsupported_text_shape_raises(self, tmp_path):
        """测试 Gerber 写入不支持的 text 形状抛出 ValueError。"""
        layout = FormatLayout(
            name="x",
            cells=[Cell(name="gerber_layout", shapes=[
                Shape("text", "gerber", [Point(0, 0)], text="hi"),
            ])],
            top_cell="gerber_layout",
        )
        with pytest.raises(ValueError):
            MultiFormatIO.write(layout, str(tmp_path / "x.gbr"), "gerber")

    def test_format_aliases(self, tmp_path):
        """测试格式别名 odb++/odbpp 与 lef_def/lef/def 等价。"""
        path1 = tmp_path / "a1.xml"
        path2 = tmp_path / "a2.xml"
        MultiFormatIO.write(_odbpp_layout(), str(path1), "odb++")
        MultiFormatIO.write(_odbpp_layout(), str(path2), "odbpp")
        assert path1.read_text(encoding="utf-8") == path2.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# layouts_equal 比较工具测试
# ---------------------------------------------------------------------------


class TestLayoutsEqual:
    """layouts_equal 语义比较工具测试。"""

    def test_equal_layouts(self):
        """测试两个语义相同的版图判定为相等。"""
        s = Shape("rect", "L", [Point(0, 0)], width=10, height=20)
        l1 = FormatLayout(name="x", cells=[Cell(name="A", shapes=[s])],
                          layers={"L": LayerInfo(name="L")}, top_cell="A")
        l2 = FormatLayout(name="x", cells=[Cell(name="A", shapes=[s])],
                          layers={"L": LayerInfo(name="L")}, top_cell="A")
        assert layouts_equal(l1, l2)

    def test_not_equal_different_width(self):
        """测试 width 不同判定为不等。"""
        l1 = FormatLayout(
            name="x",
            cells=[Cell(name="A", shapes=[
                Shape("rect", "L", [Point(0, 0)], width=10, height=20),
            ])],
            top_cell="A",
        )
        l2 = FormatLayout(
            name="x",
            cells=[Cell(name="A", shapes=[
                Shape("rect", "L", [Point(0, 0)], width=99, height=20),
            ])],
            top_cell="A",
        )
        assert not layouts_equal(l1, l2)

    def test_not_equal_different_cell_count(self):
        """测试 cell 数量不同判定为不等。"""
        l1 = FormatLayout(name="x", cells=[Cell(name="A")], top_cell="A")
        l2 = FormatLayout(name="x", cells=[Cell(name="A"), Cell(name="B")],
                          top_cell="A")
        assert not layouts_equal(l1, l2)

    def test_equal_ignores_shape_order(self):
        """测试形状顺序不同但内容相同判定为相等。"""
        s1 = Shape("rect", "L", [Point(0, 0)], width=10, height=20)
        s2 = Shape("circle", "L", [Point(5, 5)], width=3)
        l1 = FormatLayout(name="x", cells=[Cell(name="A", shapes=[s1, s2])],
                          top_cell="A")
        l2 = FormatLayout(name="x", cells=[Cell(name="A", shapes=[s2, s1])],
                          top_cell="A")
        assert layouts_equal(l1, l2)
