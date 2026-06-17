"""器件清单注册表与检索 API 的单元测试（Task 7）。

覆盖 DeviceCatalog 的注册、按平台/类别/组合检索、to_dict/to_json/to_yaml
序列化、from_json 反序列化重建、validate_sources 溯源校验，以及
default_catalog 加载四大平台全部器件。
"""

from __future__ import annotations

import json

import pytest
import yaml

from polaris.pdk import (
    BoundingBox,
    Device,
    DeviceCatalog,
    Direction,
    Port,
    Source,
    default_catalog,
)
from polaris.pdk.inp import INP_DEVICES
from polaris.pdk.lnoi import LNOI_DEVICES
from polaris.pdk.sin import SIN_DEVICES
from polaris.pdk.soi import SOI_DEVICES

# ---------------------------------------------------------------------------
# 测试夹具：构造测试用器件
# ---------------------------------------------------------------------------

def _make_test_device(
    device_id: str = "test_wg",
    platform: str = "SOI",
    category: str = "passive",
) -> Device:
    """构造一个用于测试的直波导器件（含端口、包围盒、参数与来源）。"""
    ports = [
        Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
             waveguide_type="strip", width=0.5),
        Port(name="out", x=10.0, y=0.0, direction=Direction.EAST,
             waveguide_type="strip", width=0.5),
    ]
    return Device(
        device_id=device_id,
        platform=platform,
        category=category,
        name="strip_waveguide",
        ports=ports,
        bbox=BoundingBox(xmin=0.0, ymin=-0.25, xmax=10.0, ymax=0.25),
        params={"length_um": 10.0, "loss_db_cm": 2.0},
        source=Source(
            title="SOI strip waveguide loss",
            authors="latitudeda",
            year=2024,
            url="https://latitudeda.com",
        ),
        constraints={"min_bend_radius_um": 5.0},
    )


def _make_device_without_source(device_id: str = "no_src") -> Device:
    """构造一个无 source 的器件（用于 validate_sources 测试）。"""
    return Device(
        device_id=device_id,
        platform="SOI",
        category="passive",
        name="anonymous",
        ports=[],
        bbox=BoundingBox(0.0, 0.0, 1.0, 1.0),
    )


# ---------------------------------------------------------------------------
# 注册与检索单个器件
# ---------------------------------------------------------------------------

def test_register_and_get_single_device() -> None:
    """注册单个器件后应能按 device_id 检索到。"""
    catalog = DeviceCatalog()
    dev = _make_test_device()
    catalog.register(dev)

    retrieved = catalog.get("test_wg")
    assert retrieved is dev
    assert retrieved.device_id == "test_wg"
    assert retrieved.platform == "SOI"


def test_get_nonexistent_raises_keyerror() -> None:
    """检索不存在的 device_id 应抛出 KeyError。"""
    catalog = DeviceCatalog()
    with pytest.raises(KeyError):
        catalog.get("does_not_exist")


def test_register_overwrites_same_id() -> None:
    """重复注册同一 device_id 应覆盖旧器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="dup"))
    new_dev = _make_test_device(device_id="dup", platform="SiN")
    catalog.register(new_dev)
    assert catalog.get("dup").platform == "SiN"
    assert len(catalog.list_all()) == 1


# ---------------------------------------------------------------------------
# 批量注册平台器件
# ---------------------------------------------------------------------------

def test_register_all_from_platform_soi() -> None:
    """批量注册 SOI 平台器件应加载全部 18 个器件。"""
    catalog = DeviceCatalog()
    catalog.register_all_from_platform("SOI", SOI_DEVICES)
    soi_devices = catalog.list_by_platform("SOI")
    assert len(soi_devices) == 18
    # 每个器件 platform 字段应为 SOI
    for dev in soi_devices:
        assert dev.platform == "SOI"


def test_register_all_from_platform_preserves_device_ids() -> None:
    """批量注册后 device_id 应与工厂字典键对应。"""
    catalog = DeviceCatalog()
    catalog.register_all_from_platform("SOI", SOI_DEVICES)
    for name in SOI_DEVICES:
        dev = catalog.get(SOI_DEVICES[name]().device_id)
        assert dev.name == name


# ---------------------------------------------------------------------------
# 按平台/类别/组合检索
# ---------------------------------------------------------------------------

def test_list_by_platform() -> None:
    """按平台检索应只返回对应平台器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1", platform="SOI"))
    catalog.register(_make_test_device(device_id="d2", platform="SiN"))
    catalog.register(_make_test_device(device_id="d3", platform="InP"))

    assert len(catalog.list_by_platform("SOI")) == 1
    assert len(catalog.list_by_platform("SiN")) == 1
    assert len(catalog.list_by_platform("LNOI")) == 0


def test_list_by_category() -> None:
    """按类别检索应只返回对应类别器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1", category="passive"))
    catalog.register(_make_test_device(device_id="d2", category="active"))
    catalog.register(_make_test_device(device_id="d3", category="detector"))

    assert len(catalog.list_by_category("passive")) == 1
    assert len(catalog.list_by_category("active")) == 1
    assert len(catalog.list_by_category("source")) == 0


def test_list_all() -> None:
    """list_all 应返回全部已注册器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1"))
    catalog.register(_make_test_device(device_id="d2"))
    assert len(catalog.list_all()) == 2


def test_search_by_platform_only() -> None:
    """组合检索仅指定平台。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1", platform="SOI",
                                        category="passive"))
    catalog.register(_make_test_device(device_id="d2", platform="SiN",
                                        category="passive"))
    result = catalog.search(platform="SOI")
    assert len(result) == 1
    assert result[0].platform == "SOI"


def test_search_by_category_only() -> None:
    """组合检索仅指定类别。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1", platform="SOI",
                                        category="passive"))
    catalog.register(_make_test_device(device_id="d2", platform="SOI",
                                        category="active"))
    result = catalog.search(category="active")
    assert len(result) == 1
    assert result[0].category == "active"


def test_search_by_platform_and_category() -> None:
    """组合检索平台+类别应取交集。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1", platform="SOI",
                                        category="passive"))
    catalog.register(_make_test_device(device_id="d2", platform="SOI",
                                        category="active"))
    catalog.register(_make_test_device(device_id="d3", platform="SiN",
                                        category="passive"))

    result = catalog.search(platform="SOI", category="passive")
    assert len(result) == 1
    assert result[0].device_id == "d1"

    # 无匹配
    assert catalog.search(platform="LNOI", category="passive") == []


def test_search_no_filters_returns_all() -> None:
    """组合检索无过滤参数应返回全部器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device(device_id="d1"))
    catalog.register(_make_test_device(device_id="d2"))
    assert len(catalog.search()) == 2


# ---------------------------------------------------------------------------
# to_dict 序列化
# ---------------------------------------------------------------------------

def test_to_dict_structure() -> None:
    """to_dict 应返回含 devices 列表的字典，每个器件含完整字段。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    data = catalog.to_dict()

    assert "devices" in data
    assert len(data["devices"]) == 1
    dev_dict = data["devices"][0]
    # 含全部必要字段
    for field in ("device_id", "platform", "category", "name",
                  "ports", "bbox", "params", "source", "constraints"):
        assert field in dev_dict, f"to_dict 缺少字段 {field}"


def test_to_dict_serializes_port_and_source() -> None:
    """to_dict 应正确序列化 Port（含 direction）与 Source。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    dev_dict = catalog.to_dict()["devices"][0]

    # Port 序列化
    assert len(dev_dict["ports"]) == 2
    port_dict = dev_dict["ports"][0]
    assert port_dict["name"] == "in"
    assert port_dict["direction"] == "west"  # Direction.WEST.value
    assert port_dict["waveguide_type"] == "strip"

    # Source 序列化
    assert dev_dict["source"] is not None
    assert dev_dict["source"]["url"] == "https://latitudeda.com"
    assert dev_dict["source"]["year"] == 2024

    # BoundingBox 序列化
    assert dev_dict["bbox"]["xmin"] == pytest.approx(0.0)
    assert dev_dict["bbox"]["xmax"] == pytest.approx(10.0)


def test_to_dict_none_source() -> None:
    """source 为 None 的器件应序列化为 None。"""
    catalog = DeviceCatalog()
    catalog.register(_make_device_without_source())
    dev_dict = catalog.to_dict()["devices"][0]
    assert dev_dict["source"] is None


# ---------------------------------------------------------------------------
# to_json / to_yaml 序列化与文件写入
# ---------------------------------------------------------------------------

def test_to_json_writes_valid_json(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """to_json 应写入合法 JSON 文件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "devices" in data
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "test_wg"


def test_to_yaml_writes_valid_yaml(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """to_yaml 应写入合法 YAML 文件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    path = tmp_path / "catalog.yaml"
    catalog.to_yaml(str(path))

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "devices" in data
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "test_wg"


# ---------------------------------------------------------------------------
# from_json 反序列化重建
# ---------------------------------------------------------------------------

def test_from_json_rebuilds_devices(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """from_json 应重建 Device 对象（含 Port/Source/BoundingBox）。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    catalog.register(_make_device_without_source())
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))

    rebuilt = DeviceCatalog.from_json(str(path))
    assert len(rebuilt.list_all()) == 2

    # 重建的器件字段应与原始一致
    dev = rebuilt.get("test_wg")
    assert isinstance(dev, Device)
    assert dev.platform == "SOI"
    assert dev.category == "passive"
    assert dev.name == "strip_waveguide"
    # 端口重建（含 Direction 枚举）
    assert len(dev.ports) == 2
    assert dev.ports[0].name == "in"
    assert dev.ports[0].direction == Direction.WEST
    assert dev.ports[1].direction == Direction.EAST
    # 包围盒重建
    assert dev.bbox.xmin == pytest.approx(0.0)
    assert dev.bbox.xmax == pytest.approx(10.0)
    # Source 重建
    assert dev.source is not None
    assert dev.source.url == "https://latitudeda.com"
    assert dev.source.year == 2024
    # params / constraints 重建
    assert dev.params["loss_db_cm"] == pytest.approx(2.0)
    assert dev.constraints["min_bend_radius_um"] == pytest.approx(5.0)


def test_from_json_roundtrip_equality(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """JSON 往返后重建的器件应与原始器件相等（dataclass 相等性）。"""
    catalog = DeviceCatalog()
    original = _make_test_device()
    catalog.register(original)
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))

    rebuilt = DeviceCatalog.from_json(str(path))
    rebuilt_dev = rebuilt.get("test_wg")
    # dataclass 逐字段相等
    assert rebuilt_dev == original


def test_from_json_rebuilds_none_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """from_json 应正确重建 source 为 None 的器件。"""
    catalog = DeviceCatalog()
    catalog.register(_make_device_without_source())
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))

    rebuilt = DeviceCatalog.from_json(str(path))
    dev = rebuilt.get("no_src")
    assert dev.source is None


# ---------------------------------------------------------------------------
# validate_sources 溯源校验
# ---------------------------------------------------------------------------

def test_validate_sources_all_present() -> None:
    """所有器件 source.url 非空时 validate_sources 应返回空列表。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    assert catalog.validate_sources() == []


def test_validate_sources_detects_none_source() -> None:
    """source 为 None 的器件应被检出。"""
    catalog = DeviceCatalog()
    catalog.register(_make_test_device())
    catalog.register(_make_device_without_source())
    missing = catalog.validate_sources()
    assert "no_src" in missing
    assert "test_wg" not in missing


def test_validate_sources_detects_empty_url() -> None:
    """source.url 为空的器件应被检出。"""
    catalog = DeviceCatalog()
    catalog.register(Device(
        device_id="empty_url",
        platform="SOI",
        category="passive",
        name="x",
        ports=[],
        bbox=BoundingBox(0.0, 0.0, 1.0, 1.0),
        source=Source(title="t", authors="a", year=2020, url=""),
    ))
    missing = catalog.validate_sources()
    assert "empty_url" in missing


# ---------------------------------------------------------------------------
# default_catalog 加载四大平台所有器件
# ---------------------------------------------------------------------------

def test_default_catalog_loads_all_platforms() -> None:
    """default_catalog 应加载四大平台全部器件。"""
    catalog = default_catalog()
    # 四大平台均有器件
    assert len(catalog.list_by_platform("SOI")) == len(SOI_DEVICES)
    assert len(catalog.list_by_platform("SiN")) == len(SIN_DEVICES)
    assert len(catalog.list_by_platform("InP")) == len(INP_DEVICES)
    assert len(catalog.list_by_platform("LNOI")) == len(LNOI_DEVICES)


def test_default_catalog_total_count() -> None:
    """default_catalog 器件总数应等于四大平台器件数之和。"""
    catalog = default_catalog()
    expected = (len(SOI_DEVICES) + len(SIN_DEVICES)
                + len(INP_DEVICES) + len(LNOI_DEVICES))
    assert len(catalog.list_all()) == expected


def test_default_catalog_validate_sources_passes() -> None:
    """default_catalog 中所有器件 source.url 须非空（禁止假数据）。"""
    catalog = default_catalog()
    missing = catalog.validate_sources()
    assert missing == [], f"以下器件缺失来源: {missing}"


def test_default_catalog_search_combinations() -> None:
    """default_catalog 组合检索应返回正确数量。"""
    catalog = default_catalog()
    # SOI 被动器件
    soi_passive = catalog.search(platform="SOI", category="passive")
    for dev in soi_passive:
        assert dev.platform == "SOI"
        assert dev.category == "passive"
    # InP 光源器件
    inp_source = catalog.search(platform="InP", category="source")
    for dev in inp_source:
        assert dev.platform == "InP"
        assert dev.category == "source"
    assert len(inp_source) > 0


def test_default_catalog_serialization_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """default_catalog 经 JSON 往返后器件数与关键字段保持一致。"""
    catalog = default_catalog()
    path = tmp_path / "full_catalog.json"
    catalog.to_json(str(path))

    rebuilt = DeviceCatalog.from_json(str(path))
    assert len(rebuilt.list_all()) == len(catalog.list_all())
    # 抽查一个器件完整重建
    sample = catalog.list_all()[0]
    rebuilt_sample = rebuilt.get(sample.device_id)
    assert rebuilt_sample == sample
