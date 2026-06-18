"""DeviceCatalog 注册表与序列化测试（Task 7）。"""

from __future__ import annotations

import json

import pytest
import yaml

from polaris.pdk.catalog import (
    DeviceCatalog,
    _device_from_dict,
    _device_to_dict,
    build_default_catalog,
)


@pytest.fixture
def catalog():
    return build_default_catalog()


def test_catalog_has_all_platforms(catalog):
    assert set(catalog.platforms) == {"SOI", "SiN", "InP", "LNOI"}


def test_catalog_non_empty(catalog):
    assert len(catalog) > 0


def test_all_devices_have_source(catalog):
    """所有器件须有 source.url（禁止假数据）。"""
    violations = catalog.validate_sources()
    assert violations == [], f"器件缺少 source.url: {violations}"


def test_assert_all_sourced_passes(catalog):
    catalog.assert_all_sourced()


def test_list_devices_by_platform(catalog):
    soi = catalog.list_by_platform("SOI")
    sin = catalog.list_by_platform("SiN")
    assert len(soi) > 0
    assert len(sin) > 0
    assert all(d.platform == "SOI" for d in soi)
    assert all(d.platform == "SiN" for d in sin)


def test_list_devices_by_category(catalog):
    active = catalog.list_by_category("active")
    assert len(active) > 0
    assert all(d.category == "active" for d in active)


def test_search_combined(catalog):
    """search 支持平台+类别组合检索。"""
    soi_passive = catalog.search(platform="SOI", category="passive")
    assert len(soi_passive) > 0
    assert all(d.platform == "SOI" for d in soi_passive)
    assert all(d.category == "passive" for d in soi_passive)


def test_list_devices_alias(catalog):
    """list_devices 是 search 的别名，应等价。"""
    a = catalog.list_devices(platform="SOI")
    b = catalog.search(platform="SOI")
    assert [d.device_id for d in a] == [d.device_id for d in b]


def test_get_by_device_id(catalog):
    dev = catalog.get("soi_strip_waveguide")
    assert dev.name == "strip_waveguide"
    assert dev.platform == "SOI"


def test_get_by_name_with_platform(catalog):
    dev = catalog.get("strip_waveguide", platform="SOI")
    assert dev.name == "strip_waveguide"
    assert dev.platform == "SOI"


def test_get_missing_raises(catalog):
    with pytest.raises(KeyError):
        catalog.get("nonexistent_device_id")


def test_get_missing_name_raises(catalog):
    with pytest.raises(KeyError):
        catalog.get("nonexistent_name", platform="SOI")


def test_serialization_roundtrip(catalog):
    dev = catalog.list_all()[0]
    d = _device_to_dict(dev)
    dev_back = _device_from_dict(d)
    assert dev_back.device_id == dev.device_id
    assert dev_back.platform == dev.platform
    assert dev_back.name == dev.name
    assert len(dev_back.ports) == len(dev.ports)
    assert dev_back.source is not None
    assert dev_back.source.url == dev.source.url


def test_to_dict(catalog):
    data = catalog.to_dict()
    assert "devices" in data
    assert len(data["devices"]) == len(catalog)


def test_to_json(catalog, tmp_path):
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "devices" in data
    assert len(data["devices"]) == len(catalog)


def test_to_yaml(catalog, tmp_path):
    path = tmp_path / "catalog.yaml"
    catalog.to_yaml(str(path))
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "devices" in data
    assert len(data["devices"]) == len(catalog)


def test_from_json_roundtrip(catalog, tmp_path):
    """JSON 序列化→反序列化应完整重建所有器件。"""
    path = tmp_path / "catalog.json"
    catalog.to_json(str(path))
    catalog2 = DeviceCatalog.from_json(str(path))
    assert len(catalog2) == len(catalog)
    # 平台集合一致
    assert set(catalog2.platforms) == set(catalog.platforms)
    # 任意取一个器件对比
    dev1 = catalog.get("soi_strip_waveguide")
    dev2 = catalog2.get("soi_strip_waveguide")
    assert dev2.name == dev1.name
    assert dev2.platform == dev1.platform
    assert len(dev2.ports) == len(dev1.ports)


def test_iter_and_len(catalog):
    devices = list(catalog)
    assert len(devices) == len(catalog)
    assert all(hasattr(d, "device_id") for d in devices)


def test_names(catalog):
    names = catalog.names()
    assert len(names) > 0
    assert "strip_waveguide" in names


def test_names_by_platform(catalog):
    soi_names = catalog.names(platform="SOI")
    assert len(soi_names) > 0
    assert "strip_waveguide" in soi_names


def test_register_single_device():
    """register 单个器件应能被 get 检索到。"""
    from polaris.pdk.soi import make_strip_waveguide

    cat = DeviceCatalog()
    dev = make_strip_waveguide()
    cat.register(dev)
    assert len(cat) == 1
    assert cat.get("soi_strip_waveguide").name == "strip_waveguide"


def test_register_all_from_platform():
    """register_all_from_platform 应批量注册平台器件。"""
    from polaris.pdk.soi import SOI_DEVICES

    cat = DeviceCatalog()
    cat.register_all_from_platform("SOI", SOI_DEVICES)
    assert len(cat) == len(SOI_DEVICES)
    assert "SOI" in cat.platforms
