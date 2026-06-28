"""B05 EDA 接口验收测试（IPKISS/GDSFactory 桥接）。

覆盖验收标准：
- M1: IPKISS/GDSFactory 桥接
- M2: 格式转换
- M3: 回读一致性

学术来源:
- IPKISS PCell + View 架构: https://docs.lucedaphotonics.com/
- IPKISS SDL 流程: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- SAX 网表格式: https://flaport.github.io/sax/
- Chrostowski & Hochberg, Silicon Photonics Design, Cambridge 2015
"""

from __future__ import annotations

import pytest

from polaris.flow.ipkiss_flow import (
    CircuitModelView,
    ClosedLoopValidator,
    IPKISSPCell,
    IPKISSView,
    LayoutView,
    NetlistView,
    SDLFlow,
)
from polaris.pdk.gdsfactory_pdk_bridge import (
    GDSFACTORY_PDK_REGISTRY,
    PDKConflict,
    PDKInfo,
    PicYamlConnection,
    PicYamlInstance,
    PicYamlSpec,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    check_gdsfactory_version_compatibility,
    parse_pic_yaml,
)

# =============================================================================
# M1: IPKISS/GDSFactory 桥接测试
# =============================================================================


class TestIPKISSBridge:
    """IPKISS 风格桥接测试。"""

    def test_ipkiss_pcell_with_views(self):
        """IPKISSPCell 支持多视图。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0})
        assert isinstance(cell.netlist_view, NetlistView)
        assert isinstance(cell.layout_view, LayoutView)
        assert isinstance(cell.circuit_model_view, CircuitModelView)

    def test_ipkiss_view_base_class(self):
        """IPKISSView 基类正确。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide")
        view = IPKISSView(cell)
        assert view.cell is cell
        with pytest.raises(NotImplementedError):
            view.generate()

    def test_sdl_flow_basic(self):
        """SDLFlow 基本功能。"""
        sdl = SDLFlow()
        cell = IPKISSPCell(name="wg1", cell_type="waveguide")
        sdl.add_cell(cell)
        assert "wg1" in sdl.cells

    def test_sdl_flow_build_schematic(self):
        """SDLFlow 构建原理图网表。"""
        sdl = SDLFlow()
        instances = {"wg1": "waveguide", "wg2": "waveguide"}
        connections = {"wg1,out": "wg2,in"}
        ports = {"in": "wg1,in", "out": "wg2,out"}
        netlist = sdl.build_schematic(instances, connections, ports)
        assert netlist["instances"] == instances
        assert netlist["connections"] == connections
        assert netlist["ports"] == ports

    def test_sdl_flow_set_placement(self):
        """SDLFlow 设置器件放置。"""
        sdl = SDLFlow()
        placement = {"wg1": (0.0, 0.0), "wg2": (100.0, 0.0)}
        sdl.set_placement(placement)
        assert sdl.placement["wg1"] == (0.0, 0.0)
        assert sdl.placement["wg2"] == (100.0, 0.0)

    def test_sdl_flow_generate_layout(self):
        """SDLFlow 生成版图。"""
        sdl = SDLFlow()
        sdl.add_cell(IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 50.0}))
        sdl.build_schematic(
            {"wg1": "waveguide"},
            {},
            {"in": "wg1,in", "out": "wg1,out"},
        )
        sdl.set_placement({"wg1": (10.0, 10.0)})
        layout = sdl.generate_layout()
        assert "instances" in layout
        assert "routes" in layout
        assert "wg1" in layout["instances"]

    def test_sdl_flow_export_gds(self):
        """SDLFlow 导出 GDS 风格数据。"""
        sdl = SDLFlow()
        sdl.add_cell(IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 50.0}))
        sdl.build_schematic({"wg1": "waveguide"}, {}, {"in": "wg1,in"})
        sdl.set_placement({"wg1": (0.0, 0.0)})
        gds_data = sdl.export_gds()
        assert "layers" in gds_data
        assert "bbox" in gds_data
        assert "WG" in gds_data["layers"]

    def test_closed_loop_validator_passed(self):
        """闭环验证器通过场景。"""
        validator = ClosedLoopValidator()
        schematic = {
            "instances": {"wg1": "waveguide"},
            "connections": {},
            "ports": {"in": "wg1,in"},
        }
        validator.set_schematic(schematic)
        extracted = {
            "instances": {"wg1": "waveguide"},
            "connections": {},
            "ports": {"in": "wg1,in"},
        }
        validator.extracted = extracted
        result = validator.validate()
        assert result["passed"] is True
        assert result["instance_match"] is True

    def test_closed_loop_validator_instance_mismatch(self):
        """闭环验证器检测实例不匹配。"""
        validator = ClosedLoopValidator()
        schematic = {
            "instances": {"wg1": "waveguide", "wg2": "waveguide"},
            "connections": {},
            "ports": {},
        }
        validator.set_schematic(schematic)
        extracted = {
            "instances": {"wg1": "waveguide"},
            "connections": {},
            "ports": {},
        }
        validator.extracted = extracted
        result = validator.validate()
        assert result["passed"] is False
        assert result["instance_match"] is False

    def test_closed_loop_validator_extract_from_layout(self):
        """从版图提取网表。"""
        sdl = SDLFlow()
        sdl.add_cell(IPKISSPCell(name="wg1", cell_type="waveguide"))
        sdl.build_schematic({"wg1": "waveguide"}, {}, {"in": "wg1,in"})
        sdl.set_placement({"wg1": (0.0, 0.0)})
        layout = sdl.generate_layout()
        validator = ClosedLoopValidator()
        extracted = validator.extract_from_layout(layout)
        assert "instances" in extracted
        assert "wg1" in extracted["instances"]


# =============================================================================
# M2: 格式转换测试
# =============================================================================


class TestFormatConversion:
    """格式转换测试。"""

    def test_gdsfactory_pdk_registry_not_empty(self):
        """gdsfactory PDK 注册表不为空。"""
        assert len(GDSFACTORY_PDK_REGISTRY) > 0
        assert "generic" in GDSFACTORY_PDK_REGISTRY

    def test_pdk_info_structure(self):
        """PDKInfo 数据结构正确。"""
        info = GDSFACTORY_PDK_REGISTRY["generic"]
        assert isinstance(info, PDKInfo)
        assert info.name == "generic"
        assert info.platform == "SOI"
        assert hasattr(info, "source_url")
        assert info.source_url.startswith("http")

    def test_polaris_layer_level(self):
        """PolarisLayerLevel 数据结构。"""
        level = PolarisLayerLevel(
            layer="WG",
            thickness_nm=220.0,
            zmin_nm=0.0,
            material="Si",
        )
        assert level.layer == "WG"
        assert level.thickness_nm == 220.0
        assert level.material == "Si"

    def test_polaris_layer_stack(self):
        """PolarisLayerStack 数据结构。"""
        levels = [
            PolarisLayerLevel(layer="WG", thickness_nm=220.0, zmin_nm=0.0, material="Si"),
            PolarisLayerLevel(layer="BOX", thickness_nm=2000.0, zmin_nm=-2000.0, material="SiO2"),
        ]
        stack = PolarisLayerStack(name="SOI_220nm", levels=levels)
        assert stack.name == "SOI_220nm"
        assert len(stack.levels) == 2

    def test_polaris_section(self):
        """PolarisSection 数据结构。"""
        sec = PolarisSection(width_um=0.5, offset_um=0.0, layer="WG")
        assert sec.width_um == 0.5
        assert sec.layer == "WG"

    def test_polaris_cross_section(self):
        """PolarisCrossSection 数据结构。"""
        sections = [PolarisSection(width_um=0.5, offset_um=0.0, layer="WG")]
        xs = PolarisCrossSection(name="strip_wg", sections=sections, width_um=0.5)
        assert xs.name == "strip_wg"
        assert len(xs.sections) == 1

    def test_pic_yaml_instance(self):
        """PicYamlInstance 数据结构。"""
        inst = PicYamlInstance(
            component="mmi1x2",
            settings={"width": 2.0},
            x=100.0,
            y=50.0,
            rotation=90.0,
        )
        assert inst.component == "mmi1x2"
        assert inst.x == 100.0
        assert inst.rotation == 90.0

    def test_pic_yaml_connection(self):
        """PicYamlConnection 数据结构。"""
        conn = PicYamlConnection(source="wg1,out", destination="wg2,in")
        assert conn.source == "wg1,out"
        assert conn.destination == "wg2,in"

    def test_pic_yaml_spec(self):
        """PicYamlSpec 数据结构。"""
        instances = [PicYamlInstance(component="wg1", x=0.0, y=0.0)]
        connections = [PicYamlConnection(source="wg1,in", destination="in")]
        routes = []
        ports = {"in": "wg1,in"}
        spec = PicYamlSpec(
            instances=instances,
            connections=connections,
            routes=routes,
            ports=ports,
            name="test",
        )
        assert spec.name == "test"
        assert len(spec.instances) == 1


# =============================================================================
# M3: 回读一致性与 PDK 注册表测试
# =============================================================================


class TestRoundTripAndRegistry:
    """回读一致性与 PDK 注册表测试。"""

    def test_polaris_pdk_creation(self):
        """PolarisPDK 创建。"""
        pdk = PolarisPDK(name="test_pdk", platform="SOI", process_node="220nm")
        assert pdk.name == "test_pdk"
        assert pdk.platform == "SOI"
        assert isinstance(pdk.devices, dict)

    def test_polaris_pdk_registry_register(self):
        """PolarisPDKRegistry 注册 PDK。"""
        registry = PolarisPDKRegistry()
        pdk = PolarisPDK(name="test_pdk", platform="SOI", process_node="220nm")
        registry.register("test_pdk", pdk)
        assert "test_pdk" in registry.list_pdks()

    def test_polaris_pdk_registry_duplicate_raises(self):
        """重复注册 PDK 抛出 ValueError。"""
        registry = PolarisPDKRegistry()
        pdk = PolarisPDK(name="test_pdk", platform="SOI", process_node="220nm")
        registry.register("test_pdk", pdk)
        with pytest.raises(ValueError, match="已注册"):
            registry.register("test_pdk", pdk)

    def test_polaris_pdk_registry_get(self):
        """PolarisPDKRegistry 获取 PDK。"""
        registry = PolarisPDKRegistry()
        pdk = PolarisPDK(name="test_pdk", platform="SOI", process_node="220nm")
        registry.register("test_pdk", pdk)
        retrieved = registry.get("test_pdk")
        assert retrieved.name == "test_pdk"

    def test_polaris_pdk_registry_get_missing_raises(self):
        """获取不存在 PDK 抛出 KeyError。"""
        registry = PolarisPDKRegistry()
        with pytest.raises(KeyError, match="未注册"):
            registry.get("nonexistent")

    def test_pdk_conflict_detection(self):
        """PDK 冲突检测。"""
        from polaris.pdk.device import BoundingBox, Device
        from polaris.pdk.port import Direction, Port

        registry1 = PolarisPDKRegistry()
        pdk1 = PolarisPDK(name="pdk_a", platform="SOI", process_node="220nm")
        port = Port(name="o1", x=0.0, y=0.0, direction=Direction.EAST, waveguide_type="optical", width=0.5)
        bbox = BoundingBox(xmin=0.0, ymin=0.0, xmax=10.0, ymax=10.0)
        dev = Device(device_id="shared_dev", name="shared", platform="SOI", category="passive", ports=[port], bbox=bbox)
        pdk1.devices["shared_dev"] = dev
        registry1.register("pdk_a", pdk1)

        pdk2 = PolarisPDK(name="pdk_b", platform="SOI", process_node="220nm")
        pdk2.devices["shared_dev"] = dev
        registry1.register("pdk_b", pdk2)

        conflicts = registry1.detect_conflicts()
        assert len(conflicts) >= 1
        assert isinstance(conflicts[0], PDKConflict)

    def test_version_compatibility_check(self):
        """gdsfactory 版本兼容性检查。"""
        result = check_gdsfactory_version_compatibility()
        assert hasattr(result, "compatible")
        assert hasattr(result, "python_version")
        assert hasattr(result, "reason")
        assert hasattr(result, "recommended_action")

    def test_layout_view_waveguide_bbox(self):
        """波导版图包围盒正确。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0, "width": 0.5})
        layout = cell.layout_view.generate()
        bbox = layout["bbox"]
        assert len(bbox) == 4
        assert bbox[2] >= 100.0

    def test_layout_view_ring_bbox(self):
        """环形谐振器版图包围盒正确。"""
        cell = IPKISSPCell(name="ring1", cell_type="ring_resonator", params={"radius": 10.0})
        layout = cell.layout_view.generate()
        bbox = layout["bbox"]
        assert len(bbox) == 4
        assert bbox[2] - bbox[0] >= 10.0

    def test_parse_pic_yaml_file_not_found(self):
        """解析不存在的 .pic.yml 抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            parse_pic_yaml("/nonexistent/path.pic.yml")
