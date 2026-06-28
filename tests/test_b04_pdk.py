"""B04-PDK 验收测试：PDK 平台/器件目录。

测试 PDK 系统的核心功能：三平台（SOI/SiN/LN）LayerMap、
PCell 参数化生成、器件目录检索。

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
- LIGENTEC PDK: https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
- LNOI 平台: https://www.nanochemistrygroup.com/lnoi
- IPKISS PCell: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.pdk.catalog import DeviceCatalog, default_catalog
from polaris.pdk.layer_map import (
    POLARIS_CATEGORY_LAYER_MAP,
    POLARIS_GDS_LAYER_MAP,
    GDSLayer,
    get_category_layer_tuple,
    get_layer_tuple,
)
from polaris.pdk.pcell import (
    PCellMultiView,
    TransformMatrix,
    clear_pcell_cache,
    polaris_cell,
)
from polaris.pdk.port import Direction, Port


class TestSOILayerMap:
    """SOI 平台 LayerMap 测试。"""

    def test_soi_wg_layer(self):
        """测试 SOI 平台 WG 层 (220nm Si core)。"""
        wg = POLARIS_GDS_LAYER_MAP["WG"]
        assert wg.layer == 1
        assert wg.datatype == 0
        assert wg.fabricated is True
        assert "Silicon" in wg.purpose or "波导" in wg.purpose

    def test_soi_slab150_layer(self):
        """测试 SOI 平台 SLAB150 层。"""
        slab = POLARIS_GDS_LAYER_MAP["SLAB150"]
        assert slab.layer == 2
        assert slab.datatype == 0
        assert slab.fabricated is True

    def test_soi_slab90_layer(self):
        """测试 SOI 平台 SLAB90 层。"""
        slab90 = POLARIS_GDS_LAYER_MAP["SLAB90"]
        assert slab90.layer == 3
        assert slab90.datatype == 0

    def test_soi_ge_layer(self):
        """测试 SOI 平台 GE 层（锗探测器）。"""
        ge = POLARIS_GDS_LAYER_MAP["GE"]
        assert ge.layer == 5
        assert ge.datatype == 0
        assert ge.fabricated is True

    def test_soi_deeptrench_layer(self):
        """测试 SOI 平台 DEEPTRENCH 层。"""
        dt = POLARIS_GDS_LAYER_MAP["DEEPTRENCH"]
        assert dt.layer == 4
        assert dt.datatype == 0


class TestSiNLayerMap:
    """SiN 平台 LayerMap 测试。"""

    def test_sin_wgn_layer(self):
        """测试 SiN 平台 WGN 层（核心波导）。"""
        wgn = POLARIS_GDS_LAYER_MAP["WGN"]
        assert wgn.layer == 34
        assert wgn.datatype == 0
        assert wgn.fabricated is True
        assert "SiN" in wgn.purpose

    def test_sin_wgn_clad_layer(self):
        """测试 SiN 平台 WGN_CLAD 层（包层）。"""
        clad = POLARIS_GDS_LAYER_MAP["WGN_CLAD"]
        assert clad.layer == 36
        assert clad.datatype == 0
        assert clad.fabricated is True

    def test_sin_get_layer_tuple(self):
        """测试 SiN 层 get_layer_tuple。"""
        assert get_layer_tuple("WGN") == (34, 0)


class TestLNOILayerMap:
    """LNOI（薄膜铌酸锂）平台 LayerMap 测试。"""

    def test_ln_wg_layer_exists(self):
        """测试 LN 平台可使用 WG 层作为基础层。"""
        wg = POLARIS_GDS_LAYER_MAP["WG"]
        assert wg is not None
        assert isinstance(wg, GDSLayer)

    def test_ln_port_layer_exists(self):
        """测试 LN 平台端口层存在。"""
        port = POLARIS_GDS_LAYER_MAP["PORT"]
        assert port.datatype == 10
        assert port.fabricated is False

    def test_ln_devrec_layer_exists(self):
        """测试 LN 平台器件识别层存在。"""
        devrec = POLARIS_GDS_LAYER_MAP["DEVREC"]
        assert devrec.layer == 68
        assert devrec.datatype == 0


class TestVirtualLayers:
    """Virtual 层测试（不流片的验证/标记层）。"""

    def test_port_layer_virtual(self):
        """测试 PORT 层为 virtual 层。"""
        port = POLARIS_GDS_LAYER_MAP["PORT"]
        assert port.fabricated is False
        assert port.datatype == 10

    def test_devrec_layer_virtual(self):
        """测试 DEVREC 层为 virtual 层。"""
        devrec = POLARIS_GDS_LAYER_MAP["DEVREC"]
        assert devrec.fabricated is False

    def test_pin_layer_virtual(self):
        """测试 PIN 层为 virtual 层。"""
        pin = POLARIS_GDS_LAYER_MAP["PIN"]
        assert pin.fabricated is False
        assert pin.layer == 69

    def test_text_layer_exists(self):
        """测试 TEXT 层存在。"""
        text = POLARIS_GDS_LAYER_MAP["TEXT"]
        assert text.layer == 10
        assert text.datatype == 0

    def test_floorplan_layer_exists(self):
        """测试 FLOORPLAN 层存在。"""
        fp = POLARIS_GDS_LAYER_MAP["FLOORPLAN"]
        assert fp.layer == 99
        assert fp.datatype == 0


class TestLayerMapFunctions:
    """LayerMap 辅助函数测试。"""

    def test_get_layer_tuple_valid(self):
        """测试 get_layer_tuple 有效层名。"""
        assert get_layer_tuple("WG") == (1, 0)
        assert get_layer_tuple("GE") == (5, 0)

    def test_get_layer_tuple_invalid_raises(self):
        """测试 get_layer_tuple 无效层名抛 KeyError。"""
        with pytest.raises(KeyError):
            get_layer_tuple("NONEXISTENT_LAYER")

    def test_get_category_layer_tuple(self):
        """测试 get_category_layer_tuple。"""
        assert get_category_layer_tuple("passive") == (1, 0)
        assert get_category_layer_tuple("detector") == (5, 0)
        assert get_category_layer_tuple("source") == (110, 0)

    def test_category_map_contains_keys(self):
        """测试类别映射包含主要类别。"""
        assert "passive" in POLARIS_CATEGORY_LAYER_MAP
        assert "active" in POLARIS_CATEGORY_LAYER_MAP
        assert "detector" in POLARIS_CATEGORY_LAYER_MAP
        assert "source" in POLARIS_CATEGORY_LAYER_MAP
        assert "waveguide" in POLARIS_CATEGORY_LAYER_MAP
        assert "port" in POLARIS_CATEGORY_LAYER_MAP


class TestPCellParameterizedGeneration:
    """PCell 参数化生成测试。"""

    def test_pcell_multiview_init(self):
        """测试 PCellMultiView 初始化。"""
        cell = PCellMultiView(name="test_cell", params={"width": 0.5})
        assert cell.name == "test_cell"
        assert cell.params["width"] == 0.5
        assert cell.layout_view is not None
        assert cell.circuit_view is not None
        assert cell.netlist_view is not None

    def test_pcell_add_polygon(self):
        """测试 PCell 添加多边形。"""
        cell = PCellMultiView(name="wg_cell")
        pts = np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]])
        cell.add_polygon(pts, layer="WG")
        assert len(cell.layout_view.polygons) == 1
        assert cell.layout_view.polygons[0][1] == "WG"

    def test_pcell_add_port(self):
        """测试 PCell 添加端口。"""
        cell = PCellMultiView(name="test_cell")
        cell.add_port("in", 0.0, 0.0, direction="east", width=0.5)
        assert len(cell.layout_view.ports) == 1
        assert cell.layout_view.ports[0].name == "in"
        assert cell.layout_view.ports[0].direction == Direction.EAST

    def test_pcell_add_port_direction_enum(self):
        """测试 PCell 用 Direction 枚举添加端口。"""
        cell = PCellMultiView(name="test_cell")
        cell.add_port("out", 10.0, 0.0, direction=Direction.WEST, width=0.5)
        assert cell.layout_view.ports[0].direction == Direction.WEST

    def test_pcell_to_device(self):
        """测试 PCell 转换为 Device。"""
        cell = PCellMultiView(name="test_dev", params={"platform": "SOI", "category": "passive"})
        pts = np.array([[0, 0], [10, 0], [10, 1], [0, 1]])
        cell.add_polygon(pts, layer="WG")
        cell.add_port("in", 0.0, 0.5, "west", 0.5)
        cell.add_port("out", 10.0, 0.5, "east", 0.5)
        dev = cell.to_device()
        assert dev.device_id == "test_dev"
        assert dev.platform == "SOI"
        assert dev.category == "passive"
        assert len(dev.ports) == 2

    def test_pcell_get_netlist(self):
        """测试 PCell 获取网表。"""
        cell = PCellMultiView(name="test_cell")
        cell.add_port("in", 0.0, 0.0, "west")
        netlist = cell.get_netlist()
        assert "instances" in netlist
        assert "connections" in netlist
        assert "ports" in netlist


class TestPolarisCellDecorator:
    """@polaris_cell 装饰器测试。"""

    def test_polaris_cell_basic(self):
        """测试基本 @polaris_cell 装饰器。"""
        clear_pcell_cache()

        @polaris_cell
        def simple_wg(width: float = 0.5, length: float = 10.0) -> PCellMultiView:
            cell = PCellMultiView(
                name="simple_wg",
                params={"width": width, "length": length},
            )
            pts = np.array([
                [0, -width / 2], [length, -width / 2],
                [length, width / 2], [0, width / 2],
            ])
            cell.add_polygon(pts, layer="WG")
            cell.add_port("in", 0, 0, "west", width)
            cell.add_port("out", length, 0, "east", width)
            return cell

        result = simple_wg(width=0.5, length=10.0)
        assert isinstance(result, PCellMultiView)
        assert result.name is not None
        clear_pcell_cache()

    def test_polaris_cell_caching(self):
        """测试 @polaris_cell 缓存机制。"""
        clear_pcell_cache()

        @polaris_cell
        def cached_cell(radius: float = 5.0) -> PCellMultiView:
            cell = PCellMultiView(name="cached_cell", params={"radius": radius})
            return cell

        c1 = cached_cell(radius=5.0)
        c2 = cached_cell(radius=5.0)
        assert c1 is c2
        clear_pcell_cache()

    def test_polaris_cell_different_params(self):
        """测试不同参数生成不同 PCell。"""
        clear_pcell_cache()

        @polaris_cell
        def param_cell(width: float = 0.5) -> PCellMultiView:
            cell = PCellMultiView(name="param_cell", params={"width": width})
            return cell

        c1 = param_cell(width=0.5)
        c2 = param_cell(width=1.0)
        assert c1 is not c2
        clear_pcell_cache()

    def test_polaris_cell_type_validation(self):
        """测试 @polaris_cell 类型校验。"""
        clear_pcell_cache()

        @polaris_cell
        def typed_cell(width: float = 0.5) -> PCellMultiView:
            cell = PCellMultiView(name="typed_cell", params={"width": width})
            return cell

        with pytest.raises(TypeError):
            typed_cell(width="not_a_number")
        clear_pcell_cache()


class TestTransformMatrix:
    """TransformMatrix 仿射变换测试。"""

    def test_identity_matrix(self):
        """测试恒等变换。"""
        tm = TransformMatrix()
        pt = np.array([3.0, 4.0])
        result = tm.apply(pt)
        assert abs(result[0] - 3.0) < 1e-10
        assert abs(result[1] - 4.0) < 1e-10

    def test_translate(self):
        """测试平移变换。"""
        tm = TransformMatrix().translate(5.0, 3.0)
        pt = np.array([1.0, 2.0])
        result = tm.apply(pt)
        assert abs(result[0] - 6.0) < 1e-10
        assert abs(result[1] - 5.0) < 1e-10

    def test_scale(self):
        """测试缩放变换。"""
        tm = TransformMatrix().scale(2.0, 3.0)
        pt = np.array([1.0, 2.0])
        result = tm.apply(pt)
        assert abs(result[0] - 2.0) < 1e-10
        assert abs(result[1] - 6.0) < 1e-10

    def test_rotate_90(self):
        """测试 90 度旋转。"""
        tm = TransformMatrix().rotate(90.0)
        pt = np.array([1.0, 0.0])
        result = tm.apply(pt)
        assert abs(result[0]) < 1e-10
        assert abs(result[1] - 1.0) < 1e-10

    def test_inverse(self):
        """测试逆变换。"""
        tm = TransformMatrix().translate(5.0, 3.0).rotate(45.0).scale(2.0)
        inv = tm.inverse()
        pt = np.array([1.0, 2.0])
        transformed = tm.apply(pt)
        back = inv.apply(transformed)
        assert abs(back[0] - pt[0]) < 1e-8
        assert abs(back[1] - pt[1]) < 1e-8

    def test_singular_matrix_raises(self):
        """测试奇异矩阵求逆抛错。"""
        tm = TransformMatrix(a=0.0, d=0.0)
        with pytest.raises(ValueError):
            tm.inverse()

    def test_bezier_transform(self):
        """测试贝塞尔曲线变换。"""
        cp = np.array([[0.0, 0.0], [5.0, 5.0], [10.0, 0.0]])
        p0 = TransformMatrix.bezier_transform(cp, 0.0)
        p1 = TransformMatrix.bezier_transform(cp, 1.0)
        assert abs(p0[0]) < 1e-10
        assert abs(p0[1]) < 1e-10
        assert abs(p1[0] - 10.0) < 1e-10
        assert abs(p1[1]) < 1e-10


class TestDeviceCatalog:
    """器件目录检索测试。"""

    def test_catalog_init(self):
        """测试目录初始化。"""
        cat = DeviceCatalog()
        assert len(cat) == 0
        assert cat.platforms == []

    def test_catalog_register_and_get(self):
        """测试器件注册与检索。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        dev = Device(
            device_id="test_001",
            platform="SOI",
            category="passive",
            name="test_device",
            ports=[],
            bbox=BoundingBox(0, 0, 10, 5),
            params={"width": 0.5},
        )
        cat.register(dev)
        assert len(cat) == 1
        retrieved = cat.get("test_001")
        assert retrieved.device_id == "test_001"

    def test_catalog_get_by_platform_and_name(self):
        """测试按平台和名称检索。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        dev = Device(
            device_id="dev_001",
            platform="SOI",
            category="passive",
            name="mmi1x2",
            ports=[],
            bbox=BoundingBox(0, 0, 10, 5),
        )
        cat.register(dev)
        retrieved = cat.get("mmi1x2", platform="SOI")
        assert retrieved.name == "mmi1x2"

    def test_catalog_list_by_platform(self):
        """测试按平台列出器件。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        cat.register(Device(
            device_id="d1", platform="SOI", category="passive",
            name="d1", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d2", platform="SiN", category="passive",
            name="d2", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d3", platform="SOI", category="active",
            name="d3", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        soi_devices = cat.list_by_platform("SOI")
        assert len(soi_devices) == 2
        sin_devices = cat.list_by_platform("SiN")
        assert len(sin_devices) == 1

    def test_catalog_list_by_category(self):
        """测试按类别列出器件。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        cat.register(Device(
            device_id="d1", platform="SOI", category="passive",
            name="d1", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d2", platform="SOI", category="active",
            name="d2", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        passive = cat.list_by_category("passive")
        assert len(passive) == 1

    def test_catalog_search_combined(self):
        """测试平台+类别组合检索。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        cat.register(Device(
            device_id="d1", platform="SOI", category="passive",
            name="d1", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d2", platform="SOI", category="active",
            name="d2", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d3", platform="SiN", category="passive",
            name="d3", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        result = cat.search(platform="SOI", category="passive")
        assert len(result) == 1
        assert result[0].device_id == "d1"

    def test_catalog_get_invalid_raises(self):
        """测试检索不存在器件抛 KeyError。"""
        cat = DeviceCatalog()
        with pytest.raises(KeyError):
            cat.get("nonexistent")

    def test_default_catalog_not_empty(self):
        """测试默认目录非空。"""
        cat = default_catalog()
        assert len(cat) > 0
        assert "SOI" in cat.platforms

    def test_catalog_platforms_property(self):
        """测试 platforms 属性。"""
        from polaris.pdk.device import BoundingBox, Device

        cat = DeviceCatalog()
        cat.register(Device(
            device_id="d1", platform="SOI", category="passive",
            name="d1", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        cat.register(Device(
            device_id="d2", platform="SiN", category="passive",
            name="d2", ports=[], bbox=BoundingBox(0, 0, 1, 1),
        ))
        platforms = cat.platforms
        assert "SOI" in platforms
        assert "SiN" in platforms
        assert len(platforms) == 2


class TestPortAndDirection:
    """Port 和 Direction 测试。"""

    def test_direction_enum_values(self):
        """测试 Direction 枚举值。"""
        assert Direction.NORTH.value == "north"
        assert Direction.SOUTH.value == "south"
        assert Direction.EAST.value == "east"
        assert Direction.WEST.value == "west"

    def test_port_dataclass(self):
        """测试 Port 数据类。"""
        port = Port(
            name="in",
            x=0.0,
            y=5.0,
            direction=Direction.EAST,
            waveguide_type="strip",
            width=0.5,
        )
        assert port.name == "in"
        assert port.x == 0.0
        assert port.y == 5.0
        assert port.direction == Direction.EAST
        assert port.waveguide_type == "strip"
        assert port.width == 0.5
