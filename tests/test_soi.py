"""硅光 SOI 平台器件库的单元测试（Task 3）。

验证每个器件工厂函数返回有效 ``Device``，且：
- ``source.url`` 非空并以 ``http`` 开头（溯源校验，禁止假数据）
- ``params`` 字典非空（含关键电光参数）
- ``ports``/``bbox``/``platform`` 等字段有效
"""

from __future__ import annotations

import pytest

from polaris.pdk import Device
from polaris.pdk.soi import SOI_DEVICES

# 所有器件工厂函数名（与 SOI_DEVICES 键一致，共 18 个）
_EXPECTED_DEVICE_NAMES = [
    "strip_waveguide",
    "rib_waveguide",
    "bend",
    "directional_coupler",
    "mmi_1x2",
    "mmi_2x2",
    "mzi",
    "ring_resonator",
    "grating_coupler_1d",
    "grating_coupler_2d",
    "edge_coupler",
    "y_branch",
    "crossing",
    "thermo_optic_phase_shifter",
    "mzm_modulator",
    "mrm_modulator",
    "ge_photodetector",
    "double_ring_filter",
]


def test_soi_devices_registry_complete() -> None:
    """SOI_DEVICES 应包含全部 18 个器件工厂函数。"""
    assert set(SOI_DEVICES.keys()) == set(_EXPECTED_DEVICE_NAMES)
    assert len(SOI_DEVICES) == 18


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_factory_returns_valid_device(name: str) -> None:
    """每个工厂函数应返回有效 Device（含必要字段）。"""
    factory = SOI_DEVICES[name]
    dev = factory()
    assert isinstance(dev, Device), f"{name} 工厂未返回 Device 实例"
    assert dev.platform == "SOI", f"{name} 平台应为 SOI"
    assert dev.name == name, f"{name} 器件 name 字段不匹配"
    assert dev.device_id, f"{name} device_id 为空"
    assert dev.category in {"passive", "active", "detector"}, (
        f"{name} category 非法: {dev.category}"
    )
    # 端口列表非空
    assert len(dev.ports) > 0, f"{name} 端口列表为空"
    # 包围盒有效（xmax>=xmin, ymax>=ymin）
    assert dev.bbox.xmax >= dev.bbox.xmin, f"{name} 包围盒 xmax<xmin"
    assert dev.bbox.ymax >= dev.bbox.ymin, f"{name} 包围盒 ymax<ymin"


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_device_source_url_non_empty(name: str) -> None:
    """每个 Device 的 source.url 须非空（溯源校验，禁止假数据）。"""
    dev = SOI_DEVICES[name]()
    assert dev.source is not None, f"{name} source 字段为 None"
    assert dev.source.url, f"{name} source.url 为空"


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_device_source_url_starts_with_http(name: str) -> None:
    """每个 Device 的 source.url 须以 http 开头。"""
    dev = SOI_DEVICES[name]()
    assert dev.source is not None, f"{name} source 字段为 None"
    assert dev.source.url.startswith("http"), (
        f"{name} source.url 不以 http 开头: {dev.source.url}"
    )


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_device_params_non_empty(name: str) -> None:
    """每个 Device 的 params 字典须非空（含关键电光参数）。"""
    dev = SOI_DEVICES[name]()
    assert dev.params, f"{name} params 字典为空"
    assert len(dev.params) > 0


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_device_source_has_metadata(name: str) -> None:
    """每个 Device 的 source 须含完整溯源元数据（title/authors/year）。"""
    dev = SOI_DEVICES[name]()
    assert dev.source is not None, f"{name} source 字段为 None"
    assert dev.source.title, f"{name} source.title 为空"
    assert dev.source.authors, f"{name} source.authors 为空"
    assert dev.source.year > 0, f"{name} source.year 非法: {dev.source.year}"


@pytest.mark.parametrize("name", _EXPECTED_DEVICE_NAMES)
def test_device_constraints_present(name: str) -> None:
    """每个 Device 的 constraints 须含设计约束。"""
    dev = SOI_DEVICES[name]()
    assert dev.constraints, f"{name} constraints 为空"


def test_active_devices_category() -> None:
    """主动器件（移相器/调制器）应为 active 类别。"""
    for name in ("thermo_optic_phase_shifter", "mzm_modulator", "mrm_modulator"):
        dev = SOI_DEVICES[name]()
        assert dev.category == "active", f"{name} 应为 active 类别"


def test_detector_category() -> None:
    """光电探测器应为 detector 类别。"""
    dev = SOI_DEVICES["ge_photodetector"]()
    assert dev.category == "detector"


def test_passive_devices_category() -> None:
    """被动器件应为 passive 类别。"""
    passive_names = [
        "strip_waveguide", "rib_waveguide", "bend", "directional_coupler",
        "mmi_1x2", "mmi_2x2", "mzi", "ring_resonator",
        "grating_coupler_1d", "grating_coupler_2d", "edge_coupler",
        "y_branch", "crossing", "double_ring_filter",
    ]
    for name in passive_names:
        dev = SOI_DEVICES[name]()
        assert dev.category == "passive", f"{name} 应为 passive 类别"


def test_samsung_sourced_devices_match_spec_params() -> None:
    """三星来源器件的关键参数须与 spec.md 核实值一致（禁止假数据）。"""
    # 1D Si 光栅耦合器：峰值耦合损耗 1.9dB，1-dB 带宽 27nm
    gc1d = SOI_DEVICES["grating_coupler_1d"]()
    assert gc1d.params["peak_coupling_loss_db"] == 1.9
    assert gc1d.params["bandwidth_1db_nm"] == 27
    # 2D Si 光栅耦合器：耦合损耗 2.4dB，1-dB 带宽 17nm
    gc2d = SOI_DEVICES["grating_coupler_2d"]()
    assert gc2d.params["coupling_loss_db"] == 2.4
    assert gc2d.params["bandwidth_1db_nm"] == 17
    # 微环调制器：垂直 PN 结效率 52 pm/V，带宽 74GHz/58GHz
    mrm = SOI_DEVICES["mrm_modulator"]()
    assert mrm.params["efficiency_pm_v"] == 52.0
    assert mrm.params["bandwidth_3db_ghz"] == 74.0
    assert mrm.params["bandwidth_6db_ghz"] == 58.0
    # 双环滤波器：drop 插损 <1.0dB，1-dB 带宽 105GHz
    drf = SOI_DEVICES["double_ring_filter"]()
    assert drf.params["drop_insertion_loss_db"] == 1.0
    assert drf.params["bandwidth_1db_ghz"] == 105.0


def test_tsmc_sourced_bend_params() -> None:
    """台积电来源弯曲波导参数须落在 spec.md 报告区间内。"""
    bend = SOI_DEVICES["bend"]()
    # 最小弯曲半径 2-6μm
    assert 2.0 <= bend.params["radius_um"] <= 6.0
    # 损耗 0.01-0.1 dB/90°
    assert 0.01 <= bend.params["loss_db_90"] <= 0.1


def test_strip_waveguide_params_in_spec_range() -> None:
    """条形波导参数须落在公开文献报告区间内。"""
    wg = SOI_DEVICES["strip_waveguide"]()
    # 厚 220nm，宽 450-500nm（单模），损耗 1-3 dB/cm
    assert wg.params["thickness_nm"] == 220
    assert 450 <= wg.params["width_nm"] <= 500
    assert 1.0 <= wg.params["loss_db_cm"] <= 3.0


def test_device_transforms_preserve_source() -> None:
    """器件平移/旋转变换后 source 字段须保持不变（溯源不可篡改）。"""
    dev = SOI_DEVICES["ring_resonator"]()
    moved = dev.translate(5.0, 5.0)
    rotated = dev.rotate(90)
    assert moved.source is dev.source
    assert rotated.source is dev.source
