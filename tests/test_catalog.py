"""DeviceCatalog 注册表与序列化测试（Task 7）。"""

from __future__ import annotations

import json

import pytest

from polaris.pdk.catalog import (
    DeviceCatalog,
    build_default_catalog,
    device_from_dict,
    device_to_dict,
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
    soi = catalog.list_devices(platform="SOI")
    sin = catalog.list_devices(platform="SiN")
    assert len(soi) > 0
    assert len(sin) > 0
    assert all(d.platform == "SOI" for d in soi)
    assert all(d.platform == "SiN" for d in sin)


def test_list_devices_by_category(catalog):
    active = catalog.list_devices(category="active")
    assert len(active) > 0
    assert all(d.category == "active" for d in active)


def test_get_by_name(catalog):
    dev = catalog.get("strip_waveguide", platform="SOI")
    assert dev.name == "strip_waveguide"


def test_get_cross_platform_requires_disambiguation(catalog):
    # strip_waveguide 可能跨平台存在
    with pytest.raises(KeyError):
        catalog.get("strip_waveguide")


def test_serialization_roundtrip(catalog):
    dev = catalog.list_devices()[0]
    d = device_to_dict(dev)
    dev_back = device_from_dict(d)
    assert dev_back.device_id == dev.device_id
    assert dev_back.platform == dev.platform
    assert dev_back.name == dev.name
    assert len(dev_back.ports) == len(dev.ports)


def test_to_json(catalog):
    js = catalog.to_json()
    data = json.loads(js)
    assert "platforms" in data
    assert "devices" in data
    assert len(data["devices"]) == len(catalog)


def test_to_yaml(catalog):
    ym = catalog.to_yaml()
    assert "platforms" in ym
    assert "devices" in ym
