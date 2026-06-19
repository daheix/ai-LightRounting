"""LNOI 薄膜铌酸锂平台器件库单元测试（Task 6）。

验证每个器件工厂函数返回有效 ``Device``，且：
- ``source.url`` 非空且以 ``http`` 开头（溯源校验，禁止假数据）
- ``params`` 字典非空（含关键电光参数）
- 平台为 LNOI，端口与包围盒合理
- 约束含最小弯曲半径（50-100μm）与最小间距
"""

from __future__ import annotations

import pytest

from polaris.pdk import Device
from polaris.pdk.lnoi import (
    LNOI_DEVICES,
    make_lnoi_cmos_modulator,
    make_lnoi_eo_modulator,
    make_lnoi_modulator_review,
    make_lnoi_mzm_high_confined,
    make_lnoi_mzm_traveling_wave,
    make_lnoi_photonics_review,
    make_lnoi_tfln_modulator,
    make_lnoi_waveguide,
)

# 全部 LNOI 器件工厂函数（用于参数化测试）
_ALL_FACTORIES = [
    make_lnoi_waveguide,
    make_lnoi_eo_modulator,
    make_lnoi_mzm_high_confined,
    make_lnoi_mzm_traveling_wave,
    make_lnoi_modulator_review,
    make_lnoi_photonics_review,
    make_lnoi_cmos_modulator,
    make_lnoi_tfln_modulator,
]


# ---------------------------------------------------------------------------
# 工厂函数返回有效 Device
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("factory", _ALL_FACTORIES, ids=lambda f: f.__name__)
def test_factory_returns_valid_device(factory) -> None:
    """每个工厂函数应返回有效 Device 实例。"""
    dev = factory()
    assert isinstance(dev, Device)
    assert dev.platform == "LNOI"
    assert dev.device_id
    assert dev.name
    assert dev.category in {"passive", "active", "source", "detector"}
    # 端口列表非空
    assert len(dev.ports) >= 2
    # 包围盒有效（xmax>xmin, ymax>ymin）
    assert dev.bbox.xmax > dev.bbox.xmin
    assert dev.bbox.ymax > dev.bbox.ymin


@pytest.mark.parametrize("factory", _ALL_FACTORIES, ids=lambda f: f.__name__)
def test_source_url_non_empty_and_http(factory) -> None:
    """每个 Device 的 source.url 须非空且以 http 开头。"""
    dev = factory()
    assert dev.source is not None, f"{dev.device_id} 缺少 source"
    assert dev.source.url, f"{dev.device_id} source.url 为空"
    assert dev.source.url.startswith("http"), (
        f"{dev.device_id} source.url 须以 http 开头，实际: {dev.source.url}"
    )
    # 文献溯源字段完整
    assert dev.source.title
    assert dev.source.authors
    assert dev.source.year > 0


@pytest.mark.parametrize("factory", _ALL_FACTORIES, ids=lambda f: f.__name__)
def test_params_non_empty(factory) -> None:
    """每个 Device 的 params 字典须非空。"""
    dev = factory()
    assert dev.params, f"{dev.device_id} params 为空"
    # 每个参数值须可转为字符串（含单位描述）
    for key, value in dev.params.items():
        assert key, f"{dev.device_id} params 含空键"
        assert value is not None, f"{dev.device_id} params[{key}] 为 None"


@pytest.mark.parametrize("factory", _ALL_FACTORIES, ids=lambda f: f.__name__)
def test_constraints_contain_bend_radius_and_spacing(factory) -> None:
    """约束须含最小弯曲半径（50-100μm）与最小间距。"""
    dev = factory()
    assert "min_bend_radius_um" in dev.constraints, f"{dev.device_id} 缺少 min_bend_radius_um 约束"
    bend = dev.constraints["min_bend_radius_um"]
    assert 50.0 <= bend <= 100.0, f"{dev.device_id} 弯曲半径 {bend} 不在 50-100μm 区间"
    assert "min_spacing_um" in dev.constraints, f"{dev.device_id} 缺少 min_spacing_um 约束"
    assert dev.constraints["min_spacing_um"] > 0


# ---------------------------------------------------------------------------
# 端口定义校验
# ---------------------------------------------------------------------------
def test_waveguide_has_in_out_ports() -> None:
    """波导器件须含 in/out 端口。"""
    dev = make_lnoi_waveguide()
    names = {p.name for p in dev.ports}
    assert "in" in names
    assert "out" in names


@pytest.mark.parametrize(
    "factory",
    [
        make_lnoi_eo_modulator,
        make_lnoi_mzm_high_confined,
        make_lnoi_mzm_traveling_wave,
        make_lnoi_modulator_review,
        make_lnoi_cmos_modulator,
        make_lnoi_tfln_modulator,
    ],
    ids=lambda f: f.__name__,
)
def test_modulator_has_rf_ports(factory) -> None:
    """调制器器件须含 in/out/rf_in/rf_out 端口。"""
    dev = factory()
    names = {p.name for p in dev.ports}
    assert "in" in names
    assert "out" in names
    assert "rf_in" in names
    assert "rf_out" in names


# ---------------------------------------------------------------------------
# 关键电光参数校验（禁止假数据，须来自文献）
# ---------------------------------------------------------------------------
def test_waveguide_loss_param() -> None:
    """LNOI 波导损耗 <0.4 dB/cm（来源: Liu et al. 2025）。"""
    dev = make_lnoi_waveguide()
    assert "loss_db_cm" in dev.params
    assert dev.params["loss_db_cm"] <= 0.4


def test_eo_modulator_params() -> None:
    """LNOI 电光调制器带宽 >110GHz，Vπ <3V。"""
    dev = make_lnoi_eo_modulator()
    assert "bandwidth_ghz" in dev.params
    assert dev.params["bandwidth_ghz"] >= 110
    assert "vpi_v" in dev.params
    assert dev.params["vpi_v"] <= 3


def test_mzm_high_confined_params() -> None:
    """高约束 MZM VπL 1.2 V·cm，带宽 >40GHz。"""
    dev = make_lnoi_mzm_high_confined()
    assert dev.params["vpi_l_v_cm"] == 1.2
    assert dev.params["bandwidth_ghz"] >= 40


def test_mzm_traveling_wave_params() -> None:
    """行波电极 MZM VπL 1.77 V·cm，光损耗 0.022 dB/cm。"""
    dev = make_lnoi_mzm_traveling_wave()
    assert dev.params["vpi_l_v_cm"] == 1.77
    assert dev.params["optical_loss_db_cm"] == 0.022


def test_modulator_review_params() -> None:
    """综述调制器 VπL<2 V·cm，双锥形耦合 <0.5dB/facet。"""
    dev = make_lnoi_modulator_review()
    assert dev.params["vpi_l_v_cm"] <= 2
    assert dev.params["coupling_loss_db_facet"] <= 0.5


def test_photonics_review_params() -> None:
    """集成光子学综述：透明窗口 0.4-5μm。"""
    dev = make_lnoi_photonics_review()
    assert dev.params["transparency_window_min_um"] <= 0.4
    assert dev.params["transparency_window_max_um"] >= 5


def test_cmos_modulator_source() -> None:
    """CMOS 兼容调制器来源为 Nature 2018。"""
    dev = make_lnoi_cmos_modulator()
    assert dev.source is not None
    assert dev.source.year == 2018
    assert "s41586-018-0551-y" in dev.source.url


# ---------------------------------------------------------------------------
# LNOI_DEVICES 汇总字典校验
# ---------------------------------------------------------------------------
def test_lnoi_devices_dict_complete() -> None:
    """LNOI_DEVICES 须汇总全部 8 个器件工厂函数。"""
    assert len(LNOI_DEVICES) == 8
    expected_keys = {
        "lnoi_waveguide",
        "lnoi_eo_modulator",
        "lnoi_mzm_high_confined",
        "lnoi_mzm_traveling_wave",
        "lnoi_modulator_review",
        "lnoi_photonics_review",
        "lnoi_cmos_modulator",
        "lnoi_tfln_modulator",
    }
    assert set(LNOI_DEVICES.keys()) == expected_keys


def test_lnoi_devices_all_callable() -> None:
    """LNOI_DEVICES 每个值须为可调用工厂函数。"""
    for name, factory in LNOI_DEVICES.items():
        assert callable(factory), f"{name} 不是可调用对象"
        dev = factory()
        assert isinstance(dev, Device), f"{name} 工厂未返回 Device"


def test_lnoi_devices_unique_device_ids() -> None:
    """LNOI_DEVICES 中各器件 device_id 须唯一。"""
    ids = [factory().device_id for factory in LNOI_DEVICES.values()]
    assert len(ids) == len(set(ids)), f"device_id 重复: {ids}"
