"""器件数据结构与变换工具的单元测试（Task 2）。

覆盖 Device 创建与字段访问、translate 平移、rotate 90/180/270 度旋转
（端口坐标/朝向/包围盒同步更新）、footprint 尺寸、Source 溯源校验。
"""

from __future__ import annotations

import pytest

from polaris.pdk import BoundingBox, Device, Direction, Port, Source


def _make_device() -> Device:
    """构造一个用于测试的直波导器件（SOI strip，长 10μm，宽 0.5μm）。

    端口 in 朝 WEST（左端），out 朝 EAST（右端），便于验证旋转后朝向变换。
    """
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST, waveguide_type="strip", width=0.5),
        Port(
            name="out", x=10.0, y=0.0, direction=Direction.EAST, waveguide_type="strip", width=0.5
        ),
    ]
    bbox = BoundingBox(xmin=0.0, ymin=-0.25, xmax=10.0, ymax=0.25)
    return Device(
        device_id="wg1",
        platform="SOI",
        category="passive",
        name="straight_waveguide",
        ports=ports,
        bbox=bbox,
        params={"length_um": 10.0, "loss_db_cm": 2.0},
        source=Source(
            title="SOI strip waveguide loss",
            authors="latitudeda",
            year=2024,
            url="https://latitudeda.com",
        ),
        constraints={"min_bend_radius_um": 5.0},
    )


# ---------------------------------------------------------------------------
# 创建与字段访问
# ---------------------------------------------------------------------------
def test_device_creation_basic_fields() -> None:
    """Device 应正确创建并暴露基础标识字段与端口列表。"""
    dev = _make_device()
    assert dev.device_id == "wg1"
    assert dev.platform == "SOI"
    assert dev.category == "passive"
    assert dev.name == "straight_waveguide"
    assert len(dev.ports) == 2
    assert dev.ports[0].name == "in"
    assert dev.ports[1].name == "out"


def test_device_creation_bbox_and_params() -> None:
    """Device 应正确创建并暴露包围盒、参数、约束与溯源信息。"""
    dev = _make_device()
    assert dev.bbox.xmin == pytest.approx(0.0)
    assert dev.bbox.xmax == pytest.approx(10.0)
    assert dev.params["length_um"] == pytest.approx(10.0)
    assert dev.constraints["min_bend_radius_um"] == pytest.approx(5.0)
    assert dev.source is not None
    assert dev.source.title == "SOI strip waveguide loss"


def test_device_source_defaults_to_none() -> None:
    """未提供 source 时应默认为 None。"""
    dev = Device(
        device_id="d",
        platform="SOI",
        category="passive",
        name="x",
        ports=[],
        bbox=BoundingBox(0.0, 0.0, 1.0, 1.0),
    )
    assert dev.source is None
    assert dev.params == {}
    assert dev.constraints == {}


# ---------------------------------------------------------------------------
# translate 平移
# ---------------------------------------------------------------------------
def test_translate_preserves_original() -> None:
    """translate 不应修改原实例的端口坐标与包围盒。"""
    dev = _make_device()
    dev.translate(2.0, 3.0)
    # 原实例不变
    assert dev.ports[0].x == pytest.approx(0.0)
    assert dev.ports[1].x == pytest.approx(10.0)
    assert dev.bbox.xmin == pytest.approx(0.0)


def test_translate_updates_ports() -> None:
    """translate 应同步更新端口坐标，且朝向不变。"""
    moved = _make_device().translate(2.0, 3.0)
    # 平移后端口坐标
    assert moved.ports[0].x == pytest.approx(2.0)
    assert moved.ports[0].y == pytest.approx(3.0)
    assert moved.ports[1].x == pytest.approx(12.0)
    assert moved.ports[1].y == pytest.approx(3.0)
    # 朝向不变
    assert moved.ports[0].direction == Direction.WEST
    assert moved.ports[1].direction == Direction.EAST


def test_translate_updates_bbox() -> None:
    """translate 应同步平移包围盒。"""
    moved = _make_device().translate(2.0, 3.0)
    # 包围盒同步平移
    assert moved.bbox.xmin == pytest.approx(2.0)
    assert moved.bbox.ymin == pytest.approx(2.75)
    assert moved.bbox.xmax == pytest.approx(12.0)
    assert moved.bbox.ymax == pytest.approx(3.25)


def test_translate_returns_new_instance() -> None:
    """translate 应返回新实例（与原实例不同对象）。"""
    dev = _make_device()
    moved = dev.translate(1.0, 1.0)
    assert moved is not dev
    assert moved.ports is not dev.ports


# ---------------------------------------------------------------------------
# rotate 旋转
# ---------------------------------------------------------------------------
def test_rotate_90_ports() -> None:
    """逆时针 90 度：端口坐标与朝向正确变换，且原实例不变。"""
    dev = _make_device()
    rot = dev.rotate(90)

    # 原实例不变
    assert dev.ports[1].x == pytest.approx(10.0)
    assert dev.ports[1].direction == Direction.EAST

    # in (0,0) -> (0,0)，WEST -> SOUTH
    assert rot.ports[0].x == pytest.approx(0.0)
    assert rot.ports[0].y == pytest.approx(0.0)
    assert rot.ports[0].direction == Direction.SOUTH
    # out (10,0) -> (0,10)，EAST -> NORTH
    assert rot.ports[1].x == pytest.approx(0.0)
    assert rot.ports[1].y == pytest.approx(10.0)
    assert rot.ports[1].direction == Direction.NORTH


def test_rotate_90_bbox() -> None:
    """逆时针 90 度：包围盒由宽10高0.5变为宽0.5高10。"""
    rot = _make_device().rotate(90)
    # 包围盒：原 (0,-0.25,10,0.25) 宽10高0.5 -> 宽0.5高10
    assert rot.bbox.xmin == pytest.approx(-0.25)
    assert rot.bbox.ymin == pytest.approx(0.0)
    assert rot.bbox.xmax == pytest.approx(0.25)
    assert rot.bbox.ymax == pytest.approx(10.0)


def test_rotate_180_ports() -> None:
    """逆时针 180 度：端口坐标取反、朝向反向。"""
    rot = _make_device().rotate(180)
    # in (0,0) -> (0,0)，WEST -> EAST
    assert rot.ports[0].x == pytest.approx(0.0)
    assert rot.ports[0].y == pytest.approx(0.0)
    assert rot.ports[0].direction == Direction.EAST
    # out (10,0) -> (-10,0)，EAST -> WEST
    assert rot.ports[1].x == pytest.approx(-10.0)
    assert rot.ports[1].y == pytest.approx(0.0)
    assert rot.ports[1].direction == Direction.WEST


def test_rotate_180_bbox() -> None:
    """逆时针 180 度：包围盒尺寸不变（保形），平移到对侧。"""
    rot = _make_device().rotate(180)
    # 包围盒尺寸不变（180 度保形）
    assert rot.bbox.xmin == pytest.approx(-10.0)
    assert rot.bbox.ymin == pytest.approx(-0.25)
    assert rot.bbox.xmax == pytest.approx(0.0)
    assert rot.bbox.ymax == pytest.approx(0.25)


def test_rotate_270_ports() -> None:
    """逆时针 270 度（=顺时针 90 度）：端口坐标与朝向正确变换。"""
    rot = _make_device().rotate(270)
    # in (0,0) -> (0,0)，WEST -> NORTH
    assert rot.ports[0].x == pytest.approx(0.0)
    assert rot.ports[0].y == pytest.approx(0.0)
    assert rot.ports[0].direction == Direction.NORTH
    # out (10,0) -> (0,-10)，EAST -> SOUTH
    assert rot.ports[1].x == pytest.approx(0.0)
    assert rot.ports[1].y == pytest.approx(-10.0)
    assert rot.ports[1].direction == Direction.SOUTH


def test_rotate_270_bbox() -> None:
    """逆时针 270 度：包围盒由宽10高0.5变为宽0.5高10。"""
    rot = _make_device().rotate(270)
    # 包围盒：宽0.5高10
    assert rot.bbox.xmin == pytest.approx(-0.25)
    assert rot.bbox.ymin == pytest.approx(-10.0)
    assert rot.bbox.xmax == pytest.approx(0.25)
    assert rot.bbox.ymax == pytest.approx(0.0)


def test_rotate_returns_new_instance_and_preserves_original() -> None:
    """rotate 应返回新实例且不修改原实例。"""
    dev = _make_device()
    rot = dev.rotate(90)
    assert rot is not dev
    assert rot.ports is not dev.ports
    # 原实例端口未变
    assert dev.ports[1].x == pytest.approx(10.0)
    assert dev.ports[1].direction == Direction.EAST


def test_rotate_0_returns_equivalent_new_instance() -> None:
    """0 度旋转应返回等价的新实例。"""
    dev = _make_device()
    rot = dev.rotate(0)
    assert rot is not dev
    assert rot.ports is not dev.ports
    assert rot.ports[0].x == pytest.approx(dev.ports[0].x)
    assert rot.ports[0].direction == dev.ports[0].direction
    assert rot.bbox.xmin == pytest.approx(dev.bbox.xmin)


def test_rotate_360_equivalent_to_identity() -> None:
    """360 度旋转应等价于不旋转。"""
    dev = _make_device()
    rot = dev.rotate(360)
    assert rot.ports[1].x == pytest.approx(10.0)
    assert rot.ports[1].y == pytest.approx(0.0)
    assert rot.ports[1].direction == Direction.EAST
    assert rot.bbox.xmin == pytest.approx(0.0)
    assert rot.bbox.xmax == pytest.approx(10.0)


def test_rotate_negative_90_equivalent_to_270() -> None:
    """-90 度应等价于 270 度逆时针。"""
    dev = _make_device()
    rot = dev.rotate(-90)
    # out (10,0) -> (0,-10)，EAST -> SOUTH（与 270 度一致）
    assert rot.ports[1].x == pytest.approx(0.0)
    assert rot.ports[1].y == pytest.approx(-10.0)
    assert rot.ports[1].direction == Direction.SOUTH


def test_rotate_invalid_angle_raises() -> None:
    """非直角旋转应抛出 ValueError。"""
    dev = _make_device()
    with pytest.raises(ValueError):
        dev.rotate(45)
    with pytest.raises(ValueError):
        dev.rotate(33.3)


# ---------------------------------------------------------------------------
# footprint 尺寸
# ---------------------------------------------------------------------------
def test_footprint_returns_width_and_height() -> None:
    """footprint 应返回 (宽, 高)。"""
    dev = _make_device()
    width, height = dev.footprint()
    assert width == pytest.approx(10.0)
    assert height == pytest.approx(0.5)


def test_footprint_after_rotate_swaps_dimensions() -> None:
    """90 度旋转后宽高应互换。"""
    dev = _make_device()
    rot = dev.rotate(90)
    width, height = rot.footprint()
    assert width == pytest.approx(0.5)
    assert height == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Source 溯源校验
# ---------------------------------------------------------------------------
def test_source_url_non_empty() -> None:
    """Source 的 url 字段须非空（溯源校验，禁止假数据）。"""
    src = Source(
        title="SOI strip waveguide loss",
        authors="latitudeda",
        year=2024,
        url="https://latitudeda.com",
    )
    assert src.url, "source.url 必须非空"
    assert src.url.startswith("http")


def test_device_source_url_non_empty() -> None:
    """器件附带 source 时其 url 须非空。"""
    dev = _make_device()
    assert dev.source is not None
    assert dev.source.url, "器件 source.url 必须非空"
    assert dev.source.year == 2024
    assert dev.source.authors


def test_source_is_frozen() -> None:
    """Source 应为不可变（frozen），防止溯源数据被篡改。"""
    src = Source(title="t", authors="a", year=2020, url="https://example.com")
    # FrozenInstanceError 继承自 AttributeError
    with pytest.raises(AttributeError):
        src.url = "tampered"  # type: ignore[misc]
