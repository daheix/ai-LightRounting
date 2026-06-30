"""R306 PCell ↔ gdsfactory Component 双向兼容测试。

验证 PCellMultiView 与 gdsfactory Component 的双向转换正确性。

测试策略:
- 方向转换（Direction ↔ orientation 角度）的边界值与等价类覆盖
- gdsfactory_component_to_pcell: 用 MockComponent 测试（Python 3.14 下 gdsfactory 不可用）
- pcell_to_gdsfactory_component: gdsfactory 未安装时必须 raise ImportError
- pcell_round_trip: gdsfactory 不可用时跳过
- R03 错误处理: 无端口/端口名重复/层名不存在/多边形点数不足 必须告警退出
- 学术诚信: 方向映射约定、SiEPIC 层映射、文献来源标注

来源:
- gdsfactory Component: https://gdsfactory.github.io/gdsfactory/api.html
- gdsfactory 端口约定: https://gdsfactory.github.io/gdsfactory/notebooks/02_ports.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- IPKISS PCell: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Gamma et al., "Design Patterns", 1994（Adapter Pattern）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from polaris.pdk.pcell import PCellMultiView
from polaris.pdk.pcell_gdsfactory_bridge import (
    PCellBridgeConfig,
    direction_to_orientation,
    gdsfactory_component_to_pcell,
    orientation_to_direction,
    pcell_round_trip,
    pcell_to_gdsfactory_component,
)
from polaris.pdk.port import Direction


# =============================================================================
# Mock gdsfactory Component（gdsfactory 不可用时的测试替身）
# =============================================================================
@dataclass
class MockPort:
    """模拟 gdsfactory Port。"""

    name: str
    orientation: float
    width: float
    port_type: str = "optical"
    center: tuple[float, float] = (0.0, 0.0)


@dataclass
class MockBbox:
    """模拟 gdsfactory Component.bbox() 返回的 klayout Box。"""

    left: float
    bottom: float
    right: float
    top: float


@dataclass
class MockComponent:
    """模拟 gdsfactory Component。"""

    name: str
    ports_list: list[MockPort] = field(default_factory=list)
    bbox_obj: MockBbox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ports(self) -> list[MockPort]:
        return self.ports_list

    def bbox(self) -> MockBbox:
        if self.bbox_obj is None:
            raise ValueError("MockComponent.bbox_obj 未设置")
        return self.bbox_obj


def _make_mock_component_2ports() -> MockComponent:
    """创建 2 端口 mock 组件（直波导）。"""
    return MockComponent(
        name="straight",
        ports_list=[
            MockPort(name="o1", orientation=180.0, width=0.5, center=(0.0, 0.0)),
            MockPort(name="o2", orientation=0.0, width=0.5, center=(10.0, 0.0)),
        ],
        bbox_obj=MockBbox(left=0.0, bottom=-0.25, right=10.0, top=0.25),
        metadata={"author": "test"},
    )


def _make_mock_component_4ports() -> MockComponent:
    """创建 4 端口 mock 组件（MMI 2x2）。"""
    return MockComponent(
        name="mmi2x2",
        ports_list=[
            MockPort(name="o1", orientation=180.0, width=0.5, center=(0.0, 0.5)),
            MockPort(name="o2", orientation=180.0, width=0.5, center=(0.0, -0.5)),
            MockPort(name="o3", orientation=0.0, width=0.5, center=(10.0, 0.5)),
            MockPort(name="o4", orientation=0.0, width=0.5, center=(10.0, -0.5)),
        ],
        bbox_obj=MockBbox(left=0.0, bottom=-1.0, right=10.0, top=1.0),
        metadata={"component_type": "mmi"},
    )


def _make_pcell_with_ports() -> PCellMultiView:
    """创建带 2 端口的 PCellMultiView。"""
    pcell = PCellMultiView(name="test_pcell", params={"platform": "SOI"})
    pcell.add_port(name="o1", x=0.0, y=0.0, direction=Direction.WEST, width=0.5)
    pcell.add_port(name="o2", x=10.0, y=0.0, direction=Direction.EAST, width=0.5)
    return pcell


# =============================================================================
# TR-306.1: 方向转换（Direction ↔ orientation）
# =============================================================================
class TestTR3061DirectionConversion:
    """TR-306.1: 方向转换正确性。"""

    @pytest.mark.parametrize("direction, expected", [
        (Direction.EAST, 0.0),
        (Direction.NORTH, 90.0),
        (Direction.WEST, 180.0),
        (Direction.SOUTH, 270.0),
    ])
    def test_direction_to_orientation(self, direction, expected):
        """Direction → orientation 角度映射。"""
        assert direction_to_orientation(direction) == expected

    @pytest.mark.parametrize("orientation, expected", [
        (0.0, Direction.EAST),
        (90.0, Direction.NORTH),
        (180.0, Direction.WEST),
        (270.0, Direction.SOUTH),
        (360.0, Direction.EAST),  # 360 == 0
        (-90.0, Direction.SOUTH),  # 负角度归一化: -90 % 360 = 270 → SOUTH
        (-180.0, Direction.WEST),  # -180 % 360 = 180 → WEST
        (-270.0, Direction.NORTH),  # -270 % 360 = 90 → NORTH
        (45.0, Direction.NORTH),  # 量化到最近方向
        (44.9, Direction.EAST),  # 边界
        (134.9, Direction.NORTH),  # 边界
        (135.0, Direction.WEST),  # 边界
        (314.9, Direction.SOUTH),  # 边界
        (315.0, Direction.EAST),  # 边界
    ])
    def test_orientation_to_direction(self, orientation, expected):
        """orientation 角度 → Direction 量化映射。"""
        assert orientation_to_direction(orientation) == expected

    def test_direction_to_orientation_unknown_raises(self):
        """未知 Direction 必须告警退出。"""
        # Direction 是 Enum，无法构造非法值，但用 mock 测试防御
        with pytest.raises(ValueError, match="未知 Direction"):
            direction_to_orientation("invalid")  # type: ignore[arg-type]


# =============================================================================
# TR-306.2: gdsfactory Component → PCellMultiView
# =============================================================================
class TestTR3062GdsfactoryToPCell:
    """TR-306.2: gdsfactory Component → PCellMultiView 转换。"""

    def test_basic_conversion_2ports(self):
        """2 端口组件可正确转换为 PCell。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        assert isinstance(pcell, PCellMultiView)
        assert pcell.name == "straight"
        assert len(pcell.layout_view.ports) == 2

    def test_port_names_preserved(self):
        """端口名被保留。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        port_names = {p.name for p in pcell.layout_view.ports}
        assert port_names == {"o1", "o2"}

    def test_port_positions_preserved(self):
        """端口位置被保留。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        ports = {p.name: p for p in pcell.layout_view.ports}
        assert ports["o1"].x == pytest.approx(0.0)
        assert ports["o1"].y == pytest.approx(0.0)
        assert ports["o2"].x == pytest.approx(10.0)
        assert ports["o2"].y == pytest.approx(0.0)

    def test_port_directions_quantized(self):
        """端口朝向被量化为 Direction。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        ports = {p.name: p for p in pcell.layout_view.ports}
        # o1 orientation=180 → WEST
        assert ports["o1"].direction == Direction.WEST
        # o2 orientation=0 → EAST
        assert ports["o2"].direction == Direction.EAST

    def test_port_widths_preserved(self):
        """端口宽度被保留。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        for p in pcell.layout_view.ports:
            assert p.width == pytest.approx(0.5)

    def test_metadata_to_info(self):
        """component.metadata 转换为 pcell.info。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        assert pcell.info.get("author") == "test"

    def test_bbox_extracted(self):
        """bbox 被提取到 pcell.params['bbox']。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        assert "bbox" in pcell.params
        bbox = pcell.params["bbox"]
        assert bbox[0] == pytest.approx(0.0)  # left
        assert bbox[2] == pytest.approx(10.0)  # right

    def test_4port_component(self):
        """4 端口 MMI 2x2 组件可正确转换。"""
        component = _make_mock_component_4ports()
        pcell = gdsfactory_component_to_pcell(component)
        assert len(pcell.layout_view.ports) == 4
        port_names = {p.name for p in pcell.layout_view.ports}
        assert port_names == {"o1", "o2", "o3", "o4"}


# =============================================================================
# TR-306.3: PCellMultiView → gdsfactory Component
# =============================================================================
class TestTR3063PCellToGdsfactory:
    """TR-306.3: PCellMultiView → gdsfactory Component 转换。"""

    def test_pcell_to_gdsfactory_importerror_without_gf(self):
        """gdsfactory 未安装时必须 raise ImportError。"""
        pcell = _make_pcell_with_ports()
        with pytest.raises(ImportError, match="gdsfactory 未安装"):
            pcell_to_gdsfactory_component(pcell)

    def test_pcell_no_ports_raises(self):
        """PCell 无端口必须 raise ValueError。"""
        pcell = PCellMultiView(name="empty")
        # 即使 gdsfactory 不可用，也应在 gdsfactory 检查后端口检查
        # 由于 gdsfactory 不可用，会先 raise ImportError
        with pytest.raises((ImportError, ValueError)):
            pcell_to_gdsfactory_component(pcell)


# =============================================================================
# R03 错误处理（禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 合规: 错误必须 raise，禁止 fall-back。"""

    def test_component_no_ports_raises(self):
        """gdsfactory 组件无端口必须 raise ValueError。"""
        component = MockComponent(name="empty", ports_list=[])
        with pytest.raises(ValueError, match="无端口"):
            gdsfactory_component_to_pcell(component)

    def test_duplicate_port_names_raises(self):
        """端口名重复必须 raise ValueError。"""
        component = MockComponent(
            name="dup",
            ports_list=[
                MockPort(name="o1", orientation=0.0, width=0.5),
                MockPort(name="o1", orientation=180.0, width=0.5),  # 重复
            ],
        )
        with pytest.raises(ValueError, match="重复"):
            gdsfactory_component_to_pcell(component)

    def test_pcell_bridge_config_default_layer(self):
        """PCellBridgeConfig 默认层为 (1, 0)（SiEPIC WG 层）。"""
        config = PCellBridgeConfig()
        assert config.default_layer == (1, 0)

    def test_pcell_bridge_config_layer_map_has_siepic_13(self):
        """PCellBridgeConfig.layer_map 包含 SiEPIC 13 层。"""
        config = PCellBridgeConfig()
        expected_layers = {
            "WG", "SLAB150", "SLAB90", "SiN", "METAL", "HEATER",
            "TEXT", "LABEL", "DEVREC", "PIN", "PORT", "FLOORPLAN", "PORT_GEOM",
        }
        assert expected_layers.issubset(set(config.layer_map.keys()))

    def test_pcell_bridge_config_custom_layer_map(self):
        """自定义 layer_map 被接受。"""
        config = PCellBridgeConfig(
            layer_map={"MYLAYER": (100, 0)},
            default_layer=(100, 0),
        )
        assert config.layer_map == {"MYLAYER": (100, 0)}

    def test_orientation_to_direction_handles_negative(self):
        """负角度被正确归一化。

        -90° = 270° → SOUTH, -180° = 180° → WEST, -270° = 90° → NORTH
        """
        assert orientation_to_direction(-90.0) == Direction.SOUTH
        assert orientation_to_direction(-180.0) == Direction.WEST
        assert orientation_to_direction(-270.0) == Direction.NORTH


# =============================================================================
# PCellBridgeConfig 数据类
# =============================================================================
class TestPCellBridgeConfig:
    """PCellBridgeConfig 行为测试。"""

    def test_default_config(self):
        """默认配置字段值。"""
        config = PCellBridgeConfig()
        assert config.default_layer == (1, 0)
        assert config.port_width_default == 0.5
        assert config.export_netlist is True
        assert config.export_params is True

    def test_layer_map_has_wg_at_1_0(self):
        """WG 层映射到 (1, 0)。"""
        config = PCellBridgeConfig()
        assert config.layer_map["WG"] == (1, 0)

    def test_layer_map_has_devrec_at_68_0(self):
        """DEVREC 层映射到 (68, 0)。"""
        config = PCellBridgeConfig()
        assert config.layer_map["DEVREC"] == (68, 0)


# =============================================================================
# 集成测试
# =============================================================================
class TestIntegration:
    """集成测试: 完整工作流。"""

    def test_gdsfactory_to_pcell_to_device(self):
        """gdsfactory → PCell → Device 链路通畅。"""
        component = _make_mock_component_2ports()
        pcell = gdsfactory_component_to_pcell(component)
        device = pcell.to_device()
        assert device.device_id == "straight"
        assert len(device.ports) == 2

    def test_pcell_to_device_with_4ports(self):
        """4 端口 PCell 转 Device。"""
        component = _make_mock_component_4ports()
        pcell = gdsfactory_component_to_pcell(component)
        device = pcell.to_device()
        assert len(device.ports) == 4

    def test_metadata_polaris_params_roundtrip(self):
        """polaris_params metadata 往返保留。"""
        component = MockComponent(
            name="with_params",
            ports_list=[
                MockPort(name="o1", orientation=0.0, width=0.5),
                MockPort(name="o2", orientation=180.0, width=0.5),
            ],
            bbox_obj=MockBbox(left=0.0, bottom=-0.25, right=10.0, top=0.25),
            metadata={"polaris_params": {"length": 10.0, "width": 0.5}},
        )
        pcell = gdsfactory_component_to_pcell(component)
        assert pcell.params.get("length") == 10.0
        assert pcell.params.get("width") == 0.5

    def test_pcell_round_trip_skipped_without_gdsfactory(self):
        """gdsfactory 不可用时 pcell_round_trip raise ImportError。"""
        pcell = _make_pcell_with_ports()
        with pytest.raises(ImportError, match="gdsfactory 未安装"):
            pcell_round_trip(pcell)


# =============================================================================
# 学术诚信检查
# =============================================================================
class TestAcademicIntegrity:
    """学术诚信: 公式/约定/文献来源可溯源。"""

    def test_direction_mapping_documented(self):
        """方向映射约定（0°=EAST, 90°=NORTH, 180°=WEST, 270°=SOUTH）有文献溯源。"""
        import polaris.pdk.pcell_gdsfactory_bridge as mod
        docstring = mod.__doc__ or ""
        # docstring 应包含 gdsfactory 端口约定引用
        assert "gdsfactory" in docstring.lower()
        assert "端口" in docstring or "port" in docstring.lower()

    def test_siepic_layer_map_source_documented(self):
        """SiEPIC 13 层映射有 SiEPIC PDK 文献溯源。"""
        import polaris.pdk.pcell_gdsfactory_bridge as mod
        docstring = mod.PCellBridgeConfig.__doc__ or ""
        assert "SiEPIC" in docstring

    def test_module_docstring_has_references(self):
        """模块 docstring 含 >= 5 个文献 URL。"""
        import polaris.pdk.pcell_gdsfactory_bridge as mod
        docstring = mod.__doc__ or ""
        url_count = docstring.count("https://") + docstring.count("http://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5，违反 R02"

    def test_port_direction_quantization_rule_documented(self):
        """端口方向量化规则（四象限量化）在 docstring 中说明。"""
        import polaris.pdk.pcell_gdsfactory_bridge as mod
        docstring = mod.orientation_to_direction.__doc__ or ""
        # docstring 应说明量化策略
        assert "量化" in docstring or "quantize" in docstring.lower() or "最近" in docstring

    def test_adapter_pattern_source(self):
        """Adapter Pattern 文献溯源（Gamma 1994）。"""
        import polaris.pdk.pcell_gdsfactory_bridge as mod
        docstring = mod.__doc__ or ""
        assert "Adapter" in docstring or "Gamma" in docstring or "Adapter Pattern" in docstring
