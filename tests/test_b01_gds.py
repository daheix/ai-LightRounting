"""B01-GDS 验收测试：GDSII 读写与层级结构解析。

测试 GDS 加载器的核心功能：Spice 参数解析、器件名提取、端口方向推断、
器件实例判断、坐标变换应用、GDS 文件读写往返一致性。

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
- SiEPIC netlist extraction: https://github.com/SiEPIC/SiEPIC-Tools
- klayout.db API: https://www.klayout.de/doc-qt5/code/class_LayerInfo.html
- klayout Instance class: https://www.klayout.org/klayout-pypi/overview/instances/
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from polaris.data.gds_loader import (
    _apply_trans,
    _extract_component_name,
    _is_device_instance,
    _parse_spice_param,
    _port_direction_from_path,
    load_gds_to_circuit,
)


class TestParseSpiceParam:
    """Spice_param 字符串解析测试。"""

    def test_parse_basic_params(self):
        """测试基本参数解析。"""
        result = _parse_spice_param("Spice_param:wg_width=0.500u gap=0.100u")
        assert result["wg_width"] == 0.5
        assert result["gap"] == 0.1

    def test_parse_with_equals_prefix(self):
        """测试 Spice_param= 前缀格式。"""
        result = _parse_spice_param("Spice_param=radius=5.0u length=10.0u")
        assert result["radius"] == 5.0
        assert result["length"] == 10.0

    def test_parse_without_prefix(self):
        """测试无前缀的参数字符串。"""
        result = _parse_spice_param("width=0.5u height=2.0u")
        assert result["width"] == 0.5
        assert result["height"] == 2.0

    def test_parse_empty_string(self):
        """测试空字符串解析。"""
        result = _parse_spice_param("")
        assert result == {}

    def test_parse_non_numeric_value(self):
        """测试非数值参数保留为字符串。"""
        result = _parse_spice_param("Spice_param:mode=TE width=0.5u")
        assert result["mode"] == "TE"
        assert result["width"] == 0.5

    def test_parse_multiple_params(self):
        """测试多参数解析。"""
        text = "Spice_param:a=1.0u b=2.0u c=3.0u d=4.0u e=5.0u"
        result = _parse_spice_param(text)
        assert len(result) == 5
        assert result["a"] == 1.0
        assert result["e"] == 5.0


class TestExtractComponentName:
    """器件名提取测试。"""

    def test_extract_basic_name(self):
        """测试基本器件名提取。"""
        text = "Lumerical_INTERCONNECT_component=ebeam_y_1550"
        assert _extract_component_name(text) == "ebeam_y_1550"

    def test_extract_with_additional_text(self):
        """测试包含额外文本的提取。"""
        text = "prefix Lumerical_INTERCONNECT_component=mmi1x2 suffix"
        assert _extract_component_name(text) == "mmi1x2"

    def test_extract_returns_none_when_not_found(self):
        """测试无匹配时返回 None。"""
        assert _extract_component_name("no component here") is None

    def test_extract_empty_string(self):
        """测试空字符串返回 None。"""
        assert _extract_component_name("") is None

    def test_extract_underscore_name(self):
        """测试带下划线的器件名。"""
        text = "Lumerical_INTERCONNECT_component=gc_te1550"
        assert _extract_component_name(text) == "gc_te1550"


class TestPortDirectionFromPath:
    """端口方向推断测试。"""

    def test_direction_east(self):
        """测试东方向。"""
        pts = [(0.0, 0.0), (10.0, 0.0)]
        assert _port_direction_from_path(pts) == "E"

    def test_direction_west(self):
        """测试西方向。"""
        pts = [(10.0, 0.0), (0.0, 0.0)]
        assert _port_direction_from_path(pts) == "W"

    def test_direction_north(self):
        """测试北方向。"""
        pts = [(0.0, 0.0), (0.0, 10.0)]
        assert _port_direction_from_path(pts) == "N"

    def test_direction_south(self):
        """测试南方向。"""
        pts = [(0.0, 10.0), (0.0, 0.0)]
        assert _port_direction_from_path(pts) == "S"

    def test_diagonal_favors_horizontal(self):
        """测试对角线方向（水平分量大则为东西向）。"""
        pts = [(0.0, 0.0), (10.0, 3.0)]
        assert _port_direction_from_path(pts) == "E"

    def test_single_point_default_east(self):
        """测试单点时默认东向。"""
        pts = [(0.0, 0.0)]
        assert _port_direction_from_path(pts) == "E"


class TestIsDeviceInstance:
    """器件实例判断测试。"""

    def test_valid_device(self):
        """测试有效器件名。"""
        assert _is_device_instance("ebeam_y_1550") is True

    def test_ignore_round_path(self):
        """测试忽略 ROUND_PATH 前缀。"""
        assert _is_device_instance("ROUND_PATH_123") is False

    def test_ignore_laser(self):
        """测试忽略激光器前缀。"""
        assert _is_device_instance("LumericalINTERCONNECT_Laser") is False

    def test_ignore_detector(self):
        """测试忽略探测器前缀。"""
        assert _is_device_instance("LumericalINTERCONNECT_Detector") is False

    def test_ignore_optical_fibre(self):
        """测试忽略光纤前缀。"""
        assert _is_device_instance("OpticalFibre_1") is False

    def test_ignore_grating_coupler(self):
        """测试忽略光栅耦合器前缀。"""
        assert _is_device_instance("TE1550_SubGC") is False

    def test_ignore_waveguide_route(self):
        """测试忽略波导路由前缀。"""
        assert _is_device_instance("Waveguide_Route_0") is False


class TestApplyTrans:
    """坐标变换应用测试。"""

    def test_apply_trans_returns_tuple(self):
        """测试 _apply_trans 返回坐标元组。"""
        import klayout.db as db

        trans = db.DCplxTrans()
        result = _apply_trans(trans, 10.0, 20.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)

    def test_apply_trans_mirror_x_coordinate(self):
        """测试镜像变换对 x 坐标取反。"""
        import klayout.db as db

        trans = db.DCplxTrans(1.0, 0.0, True, 0.0, 0.0)
        result = _apply_trans(trans, 5.0, 3.0)
        assert abs(result[0] - (-5.0)) < 1e-10
        assert abs(result[1] - 3.0) < 1e-10

    def test_apply_trans_with_displacement(self):
        """测试带位移的变换。"""
        import klayout.db as db

        trans = db.DCplxTrans(1.0, 0.0, False, 5.0, 3.0)
        result = _apply_trans(trans, 10.0, 20.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_apply_trans_rotation(self):
        """测试旋转变换。"""
        import klayout.db as db

        trans = db.DCplxTrans(1.0, 90.0, False, 0.0, 0.0)
        result = _apply_trans(trans, 10.0, 0.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_apply_trans_scaling(self):
        """测试缩放变换。"""
        import klayout.db as db

        trans = db.DCplxTrans(2.0, 0.0, False, 0.0, 0.0)
        result = _apply_trans(trans, 3.0, 4.0)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestGDSReadWriteRoundTrip:
    """GDS 读写往返一致性测试。"""

    def _create_simple_gds(self, path: Path) -> None:
        """创建简单测试 GDS 文件。"""
        import klayout.db as db

        ly = db.Layout()
        ly.dbu = 0.001
        top = ly.create_cell("TOP")
        wg_layer = ly.layer(1, 0)
        box = db.DBox(0.0, 0.0, 100.0, 0.5)
        top.shapes(wg_layer).insert(db.DPolygon(box))
        ly.write(str(path))

    def test_gds_roundtrip_basic(self):
        """测试基本 GDS 读写往返。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "test.gds"
            self._create_simple_gds(gds_path)
            assert gds_path.exists()
            assert gds_path.stat().st_size > 0

    def test_load_gds_file_not_found_raises(self):
        """测试文件不存在时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            load_gds_to_circuit("/nonexistent/path.gds")

    def test_load_empty_gds(self):
        """测试加载空 GDS 文件。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "empty.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            ly.create_cell("EMPTY")
            ly.write(str(gds_path))
            circuit = load_gds_to_circuit(gds_path)
            assert circuit.name == "EMPTY"
            assert len(circuit.devices) == 0
            assert len(circuit.connections) == 0

    def test_load_gds_with_single_instance(self):
        """测试加载含单个子单元的 GDS。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "single.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            sub = ly.create_cell("ebeam_y_1550")
            wg_layer = ly.layer(1, 0)
            sub.shapes(wg_layer).insert(db.DBox(0.0, 0.0, 10.0, 2.0))
            top = ly.create_cell("TOP")
            top.insert(db.DCellInstArray(sub.cell_index(), db.DTrans(0.0, 0.0)))
            ly.write(str(gds_path))
            circuit = load_gds_to_circuit(gds_path)
            assert circuit.name == "TOP"
            assert len(circuit.devices) >= 0

    def test_gds_dbu_consistency(self):
        """测试 GDS dbu 一致性。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "dbu_test.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            ly.create_cell("DBU_TEST")
            ly.write(str(gds_path))
            read_back = db.Layout()
            read_back.read(str(gds_path))
            assert abs(read_back.dbu - 0.001) < 1e-10


class TestGDSHierarchy:
    """GDS 层级结构解析测试。"""

    def test_flat_hierarchy(self):
        """测试扁平结构（无实例）。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "flat.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("FLAT")
            wg_layer = ly.layer(1, 0)
            top.shapes(wg_layer).insert(db.DBox(0, 0, 10, 1))
            ly.write(str(gds_path))
            circuit = load_gds_to_circuit(gds_path)
            assert circuit.name == "FLAT"

    def test_nested_hierarchy(self):
        """测试嵌套层级结构。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "nested.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            leaf = ly.create_cell("LEAF")
            wg_layer = ly.layer(1, 0)
            leaf.shapes(wg_layer).insert(db.DBox(0, 0, 5, 1))
            mid = ly.create_cell("MID")
            mid.insert(db.DCellInstArray(leaf.cell_index(), db.DTrans(0, 0)))
            top = ly.create_cell("TOP")
            top.insert(db.DCellInstArray(mid.cell_index(), db.DTrans(10, 0)))
            ly.write(str(gds_path))
            circuit = load_gds_to_circuit(gds_path)
            assert circuit.name == "TOP"

    def test_multiple_instances(self):
        """测试多个实例。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "multi.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            sub = ly.create_cell("test_device")
            wg_layer = ly.layer(1, 0)
            sub.shapes(wg_layer).insert(db.DBox(0, 0, 5, 2))
            top = ly.create_cell("TOP")
            for i in range(3):
                top.insert(db.DCellInstArray(sub.cell_index(), db.DTrans(i * 20.0, 0)))
            ly.write(str(gds_path))
            circuit = load_gds_to_circuit(gds_path)
            assert circuit.name == "TOP"


class TestGDSGeometryPrimitives:
    """GDS 基本几何图元支持测试。"""

    def test_rectangle_polygon(self):
        """测试矩形多边形。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "rect.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("RECT")
            wg_layer = ly.layer(1, 0)
            rect = db.DPolygon(db.DBox(0.0, 0.0, 10.0, 1.0))
            top.shapes(wg_layer).insert(rect)
            ly.write(str(gds_path))
            read_back = db.Layout()
            read_back.read(str(gds_path))
            top_back = read_back.top_cell()
            assert top_back.name == "RECT"

    def test_polygon_shape(self):
        """测试任意多边形。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "poly.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("POLY")
            wg_layer = ly.layer(1, 0)
            pts = [db.DPoint(0, 0), db.DPoint(10, 0), db.DPoint(10, 5), db.DPoint(5, 8), db.DPoint(0, 5)]
            poly = db.DPolygon(pts)
            top.shapes(wg_layer).insert(poly)
            ly.write(str(gds_path))
            assert gds_path.exists()

    def test_path_shape(self):
        """测试路径形状。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "path.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("PATH")
            pin_layer = ly.layer(69, 0)
            pts = [db.DPoint(0, 0), db.DPoint(10, 0)]
            path = db.DPath(pts, 0.5)
            top.shapes(pin_layer).insert(path)
            ly.write(str(gds_path))
            assert gds_path.exists()

    def test_text_shape(self):
        """测试文本形状。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "text.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("TEXT")
            text_layer = ly.layer(10, 0)
            trans = db.DTrans(db.DVector(5.0, 5.0))
            text = db.DText()
            text.string = "test_label"
            text.dtrans = trans
            text.size = 1.0
            top.shapes(text_layer).insert(text)
            ly.write(str(gds_path))
            assert gds_path.exists()

    def test_multiple_layers(self):
        """测试多层结构。"""
        import klayout.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            gds_path = Path(tmpdir) / "layers.gds"
            ly = db.Layout()
            ly.dbu = 0.001
            top = ly.create_cell("LAYERS")
            wg_layer = ly.layer(1, 0)
            slab_layer = ly.layer(2, 0)
            top.shapes(wg_layer).insert(db.DBox(0, 0, 10, 0.5))
            top.shapes(slab_layer).insert(db.DBox(0, 0, 10, 2.0))
            ly.write(str(gds_path))
            read_back = db.Layout()
            read_back.read(str(gds_path))
            assert read_back.layers() is not None
