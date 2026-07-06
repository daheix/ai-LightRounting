"""扩展测试（从 test_pdk_advanced.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_pdk_advanced.py。
"""


from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_pdk_advanced as ppa  # noqa: E402
from polaris_pdk_advanced import (  # noqa: E402
    BoundingBox,
    DesignIntent,
    DesignIntentEngine,
    Device,
    Direction,
    FlexConnector,
    GDSFACTORY_PDK_REGISTRY,
    HierarchyDesign,
    MultiPDKManager,
    PCellCache,
    PCellMultiView,
    PDKSnapshot,
    PDAflowInterop,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    Port,
    PyCell,
    PyCellFactory,
    Source,
    TechnologyRule,
    TransformMatrix,
    VersionCompatibility,
    ai_generate_pcell,
    build_polaris_pdk_from_yaml,
    check_gdsfactory_version_compatibility,
    clear_pcell_cache,
    get_gdsfactory_pdk,
    list_gdsfactory_pdks,
    parse_pic_yaml,
    parse_pdk_yaml,
    polaris_cell,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)


# ===== gdsfactory_bridge 深度测试 =====


def _make_device(name: str) -> Device:
    """构造测试用 Device（直波导，2 端口）。"""
    return Device(
        device_id=name,
        platform="SOI",
        category="passive",
        name=name,
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type="strip", width=0.5),
            Port(name="out", x=10.0, y=0.0, direction=Direction.EAST,
                 waveguide_type="strip", width=0.5),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-0.25, xmax=10.0, ymax=0.25),
        params={"length": 10.0, "width": 0.5},
        source=Source(
            title="test", authors="test", year=2026,
            url="https://gdsfactory.github.io/gdsfactory/",
        ),
    )


def test_pycell_factory_ring_resonator():
    """PyCellFactory.ring_resonator 环谐振器 PyCell。"""
    factory = PyCellFactory()
    ring = factory.ring_resonator(radius=10.0, gap=0.2, width=0.5)
    assert ring.name == "ring_resonator"
    assert len(ring.polygons) == 2
    assert len(ring.ports) == 2
    assert ring.params["radius"] == 10.0


def test_pycell_factory_taper_ybranch_crossing_terminator():
    """PyCellFactory taper/y_branch/crossing/terminator PyCell。"""
    factory = PyCellFactory()
    taper = factory.taper(length=5.0, width1=0.5, width2=1.0)
    assert taper.name == "taper"
    assert len(taper.ports) == 2
    assert taper.params["width1"] == 0.5
    assert taper.params["width2"] == 1.0
    yb = factory.y_branch(length=10.0, width=0.5)
    assert yb.name == "y_branch"
    assert len(yb.ports) == 3
    crossing = factory.crossing(length=10.0, width=0.5)
    assert crossing.name == "crossing"
    assert len(crossing.polygons) == 2
    assert len(crossing.ports) == 4
    term = factory.terminator(length=5.0, width=0.5)
    assert term.name == "terminator"
    assert len(term.ports) == 1


def test_design_intent_engine_multi_layer_masks():
    """DesignIntentEngine 单层路径→多层掩膜自动生成。"""
    intent = DesignIntent(
        path=[(0.0, 0.0), (10.0, 0.0)], width=0.5, wg_type="strip"
    )
    rules = [
        TechnologyRule(layer=(1, 0), offset=0.0, purpose="WG"),
        TechnologyRule(layer=(2, 0), offset=0.1, purpose="SLAB"),
        TechnologyRule(layer=(3, 0), offset=0.2, purpose="METAL"),
    ]
    engine = DesignIntentEngine(rules)
    masks = engine.generate_masks(intent)
    assert len(masks) == 3
    assert (1, 0) in masks
    assert (2, 0) in masks
    assert (3, 0) in masks
    for layer, polys in masks.items():
        assert len(polys) == 1
        assert len(polys[0]) >= 4
    with pytest.raises(ValueError):
        DesignIntentEngine([])
    with pytest.raises(ValueError):
        engine.generate_masks(DesignIntent(path=[(0.0, 0.0)], width=0.5))


def test_design_intent_engine_add_rule():
    """DesignIntentEngine.add_rule 动态添加规则。"""
    engine = DesignIntentEngine([TechnologyRule(layer=(1, 0), offset=0.0)])
    assert len(engine.rules) == 1
    engine.add_rule(TechnologyRule(layer=(2, 0), offset=0.1, purpose="SLAB"))
    assert len(engine.rules) == 2
    intent = DesignIntent(path=[(0.0, 0.0), (5.0, 0.0)], width=0.5)
    masks = engine.generate_masks(intent)
    assert len(masks) == 2


def test_flex_connector_bezier_curve():
    """FlexConnector 贝塞尔曲线连接任意角度端口。"""
    fc = FlexConnector(
        start_port=(0.0, 0.0, 0.0, 0.5),
        end_port=(20.0, 10.0, 180.0, 0.5),
        path_type="bezier",
    )
    path = fc.compute_path(n_points=50)
    assert len(path) == 50
    assert np.allclose(path[0], [0.0, 0.0])
    assert np.allclose(path[-1], [20.0, 10.0])
    length = fc.compute_length()
    straight_dist = np.hypot(20.0, 10.0)
    assert length > straight_dist
    cell = fc.to_pycell()
    assert cell.name == "flex_connector"
    assert len(cell.polygons) == 1
    assert len(cell.ports) == 2
    with pytest.raises(ValueError):
        fc.compute_path(n_points=1)


def test_hierarchy_design_flatten_and_depth():
    """HierarchyDesign 层级嵌套 + flatten + depth。"""
    factory = PyCellFactory()
    wg = factory.straight(length=5.0, width=0.5)
    top = HierarchyDesign("top")
    top.add_instance(wg, position=(0.0, 0.0))
    top.add_instance(wg, position=(10.0, 0.0), rotation=0.0)
    sub = HierarchyDesign("sub")
    sub.add_instance(wg, position=(0.0, 5.0))
    top.add_sub_design(sub, position=(0.0, 0.0))
    assert top.hierarchy_depth() == 2
    assert top.instance_count == 3
    flat = top.flatten()
    assert flat.name == "top"
    assert len(flat.polygons) == 3
    assert len(flat.ports) == 6


def test_hierarchy_design_depth_3():
    """HierarchyDesign 3 层嵌套深度。"""
    factory = PyCellFactory()
    wg = factory.straight(length=5.0, width=0.5)
    top = HierarchyDesign("top")
    mid = HierarchyDesign("mid")
    bot = HierarchyDesign("bot")
    bot.add_instance(wg, position=(0.0, 0.0))
    mid.add_sub_design(bot, position=(0.0, 0.0))
    mid.add_instance(wg, position=(10.0, 0.0))
    top.add_sub_design(mid, position=(0.0, 0.0))
    assert top.hierarchy_depth() == 3
    assert top.instance_count == 1
    flat = top.flatten()
    assert len(flat.polygons) == 2


def test_pdaflow_interop_export_spt():
    """PDAflowInterop.export_spt 导出 SPT 文件。"""
    factory = PyCellFactory()
    wg = factory.straight(length=5.0, width=0.5)
    design = HierarchyDesign("test_design")
    design.add_instance(wg, position=(0.0, 0.0))
    interop = PDAflowInterop()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".spt", delete=False, encoding="utf-8"
    ) as f:
        spt_path = f.name
    try:
        result = interop.export_spt(design, spt_path)
        assert result == spt_path
        content = Path(spt_path).read_text(encoding="utf-8")
        assert "DESIGN test_design" in content
        assert "DEPTH" in content
        assert "PORT" in content
        assert "POLY" in content
    finally:
        Path(spt_path).unlink()
    empty_design = HierarchyDesign("empty")
    with pytest.raises(ValueError):
        interop.export_spt(empty_design, "/tmp/empty.spt")


# ===== _base 深度测试 =====


def test_device_rotate_and_translate():
    """Device 旋转/平移（返回新实例，原实例不变）。"""
    dev = _make_device("test_wg")
    original_x = dev.ports[0].x
    moved = dev.translate(10.0, 20.0)
    assert moved.ports[0].x == original_x + 10.0
    assert moved.ports[0].y == 20.0
    assert dev.ports[0].x == original_x
    rotated = dev.rotate(90.0)
    assert rotated.ports[0].direction == Direction.SOUTH
    with pytest.raises(ValueError):
        dev.rotate(45.0)


def test_device_footprint_and_rotate_180():
    """Device.footprint 返回宽×高，rotate(180) 朝向取反。"""
    dev = _make_device("test_wg")
    w, h = dev.footprint()
    assert w == 10.0
    assert h == 0.5
    rotated = dev.rotate(180.0)
    assert rotated.ports[0].direction == Direction.EAST
    assert rotated.ports[1].direction == Direction.WEST


def test_direction_enum_values():
    """Direction 枚举含四正方向。"""
    assert Direction.NORTH.value == "north"
    assert Direction.SOUTH.value == "south"
    assert Direction.EAST.value == "east"
    assert Direction.WEST.value == "west"


def test_source_frozen():
    """Source frozen=True 不可变。"""
    src = Source(title="test", authors="test", year=2026,
                 url="https://example.com")
    assert src.title == "test"
    assert src.year == 2026
    with pytest.raises(Exception):
        src.title = "modified"  # type: ignore[misc]


def test_pcell_multiview_observer():
    """PCellMultiView Observer Pattern 自动同步（*创新*）。"""
    cell = PCellMultiView(name="test", params={"platform": "SOI"})
    cell.add_port("in", 0.0, 0.0, "west", 0.5)
    cell.add_port("out", 10.0, 0.0, "east", 0.5)
    netlist = cell.get_netlist()
    assert "in" in netlist["ports"]
    assert "out" in netlist["ports"]
    cell.add_ref(PCellMultiView(name="sub"), x=5.0, y=5.0)
    assert len(cell.netlist_view.instances) == 1


def test_pcell_multiview_to_device():
    """PCellMultiView.to_device 转换为 Device。"""
    cell = PCellMultiView(name="test_wg", params={"platform": "SOI"})
    cell.add_polygon(np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]]), layer="WG")
    cell.add_port("in", 0.0, 0.0, "west", 0.5)
    device = cell.to_device()
    assert device.device_id == "test_wg"
    assert device.platform == "SOI"
    assert len(device.ports) == 1
    assert device.bbox.xmax == 10.0


# ===== 辅助函数 =====


