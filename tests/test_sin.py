"""氮化硅 SiN 平台器件库单元测试（Task 4）。

验证每个 SiN 器件工厂函数返回有效 Device，且：
- source.url 非空且以 http 开头（溯源校验，禁止假数据）
- params 字典非空（含关键电光参数）
- platform 为 SiN
- constraints 含最小间距与最小弯曲半径
"""

from __future__ import annotations

import pytest

from polaris.pdk import Device
from polaris.pdk.sin import SIN_DEVICES

# 所有 SiN 器件工厂函数名（与 SIN_DEVICES 键一致）
_ALL_DEVICE_KEYS = sorted(SIN_DEVICES.keys())


def test_sin_devices_registry_non_empty() -> None:
    """SIN_DEVICES 注册表应非空，且覆盖全部 14 个器件。"""
    assert len(SIN_DEVICES) == 14
    # 关键器件应在注册表中
    assert "sin_waveguide_lpcvd" in SIN_DEVICES
    assert "triplex_double_stripe" in SIN_DEVICES
    assert "sin_waveguide_damascene" in SIN_DEVICES
    assert "sin_ring_high_q" in SIN_DEVICES
    assert "sin_grating_coupler_1d" in SIN_DEVICES


@pytest.mark.parametrize("device_key", _ALL_DEVICE_KEYS)
def test_factory_returns_valid_device(device_key: str) -> None:
    """每个工厂函数应返回有效 Device 实例。"""
    factory = SIN_DEVICES[device_key]
    dev = factory()
    assert isinstance(dev, Device)
    assert dev.device_id == device_key
    assert dev.platform == "SiN"
    assert dev.name, "器件 name 应非空"
    assert dev.category in {"passive", "material"}


@pytest.mark.parametrize("device_key", _ALL_DEVICE_KEYS)
def test_device_source_url_valid(device_key: str) -> None:
    """每个器件的 source.url 须非空且以 http 开头（溯源校验）。"""
    dev = SIN_DEVICES[device_key]()
    assert dev.source is not None, f"{device_key} 缺少 source"
    assert dev.source.url, f"{device_key} 的 source.url 为空"
    assert dev.source.url.startswith("http"), f"{device_key} 的 url 非 http 开头"
    assert dev.source.title, f"{device_key} 的 source.title 为空"
    assert dev.source.authors, f"{device_key} 的 source.authors 为空"
    assert dev.source.year > 2000, f"{device_key} 的 source.year 异常"


@pytest.mark.parametrize("device_key", _ALL_DEVICE_KEYS)
def test_device_params_non_empty(device_key: str) -> None:
    """每个器件的 params 字典应非空（含关键电光参数）。"""
    dev = SIN_DEVICES[device_key]()
    assert dev.params, f"{device_key} 的 params 为空"
    assert len(dev.params) >= 3, f"{device_key} 的 params 项数过少"


@pytest.mark.parametrize("device_key", _ALL_DEVICE_KEYS)
def test_device_constraints_present(device_key: str) -> None:
    """每个器件的 constraints 应含最小间距与最小弯曲半径。"""
    dev = SIN_DEVICES[device_key]()
    assert "min_spacing_um" in dev.constraints, f"{device_key} 缺少 min_spacing_um"
    assert "min_bend_radius_um" in dev.constraints, f"{device_key} 缺少 min_bend_radius_um"
    # SiN 最小间距 2μm，最小弯曲半径 50-100μm
    assert dev.constraints["min_spacing_um"] == pytest.approx(2.0)
    assert dev.constraints["min_bend_radius_um"] >= 50.0


@pytest.mark.parametrize("device_key", _ALL_DEVICE_KEYS)
def test_device_bbox_valid(device_key: str) -> None:
    """每个器件的包围盒应有效（xmax>=xmin, ymax>=ymin）。"""
    dev = SIN_DEVICES[device_key]()
    assert dev.bbox.xmax >= dev.bbox.xmin, f"{device_key} 包围盒 x 无效"
    assert dev.bbox.ymax >= dev.bbox.ymin, f"{device_key} 包围盒 y 无效"


def test_waveguide_ports_west_east() -> None:
    """直波导器件应有 in(WEST)/out(EAST) 两端口。"""
    dev = SIN_DEVICES["sin_waveguide_lpcvd"]()
    assert len(dev.ports) == 2
    assert dev.ports[0].name == "in"
    assert dev.ports[1].name == "out"
    assert dev.ports[0].x == pytest.approx(0.0)
    assert dev.ports[1].x > 0.0


def test_ring_ports_in_through() -> None:
    """环谐振器应有 in/through 两端口。"""
    dev = SIN_DEVICES["sin_ring_high_q"]()
    assert len(dev.ports) == 2
    assert dev.ports[0].name == "in"
    assert dev.ports[1].name == "through"


def test_grating_coupler_ports() -> None:
    """光栅耦合器应有 fiber 与 out 端口。"""
    dev = SIN_DEVICES["sin_grating_coupler_1d"]()
    port_names = {p.name for p in dev.ports}
    assert "fiber" in port_names
    assert "out" in port_names


def test_material_devices_have_no_ports() -> None:
    """材料参数器件（material 类别）无端口。"""
    for key in ("sin_material", "sin_thermo_optic"):
        dev = SIN_DEVICES[key]()
        assert dev.ports == [], f"{key} 应无端口"
        assert dev.category == "material"


def test_sin_imec_waveguide_params_match_literature() -> None:
    """IMEC LPCVD/PECVD SiN 波导参数须与文献报告值一致（禁止假数据）。"""
    # IMEC LPCVD: <0.1 dB/cm，最低 2 dB/m，405-2500nm
    lpcvd = SIN_DEVICES["sin_waveguide_lpcvd"]()
    assert lpcvd.params["loss_db_cm"] == pytest.approx(0.1)
    assert lpcvd.params["loss_min_db_m"] == pytest.approx(2.0)
    assert lpcvd.params["wavelength_range_nm"] == "405-2500"

    # IMEC PECVD: <2 dB/cm
    pecvd = SIN_DEVICES["sin_waveguide_pecvd"]()
    assert pecvd.params["loss_db_cm"] == pytest.approx(2.0)


def test_sin_double_stripe_params_match_literature() -> None:
    """TriPleX/Twente 双条带波导与环参数须与文献报告值一致。"""
    # TriPleX: <0.1 dB/cm，最低 0.1 dB/m，光纤耦合 <0.5dB/facet
    triplex = SIN_DEVICES["triplex_double_stripe"]()
    assert triplex.params["loss_db_cm"] == pytest.approx(0.1)
    assert triplex.params["loss_min_db_m"] == pytest.approx(0.1)
    assert triplex.params["fiber_coupling_loss_db"] == pytest.approx(0.5)

    # Twente 双条带环: 0.095 dB/cm
    ring_ds = SIN_DEVICES["sin_ring_double_stripe"]()
    assert ring_ds.params["loss_db_cm"] == pytest.approx(0.095)


def test_sin_damascene_waveguide_params_match_literature() -> None:
    """Damascene 工艺 SiN 波导参数须与文献报告值一致。"""
    # Damascene: 0.157 dB/cm @1550nm，0.06 dB/cm @1580nm，400nm 厚
    dam = SIN_DEVICES["sin_waveguide_damascene"]()
    assert dam.params["loss_db_cm_1550nm"] == pytest.approx(0.157)
    assert dam.params["loss_db_cm_1580nm"] == pytest.approx(0.06)
    assert dam.params["core_thickness_nm"] == 400


def test_sin_ull_epfl_waveguide_params_match_literature() -> None:
    """UCSB ULL 与 EPFL 超低损耗波导参数须与文献报告值一致。"""
    # UCSB ULL: 1.2 dB/m @1590nm
    ull = SIN_DEVICES["sin_waveguide_ull"]()
    assert ull.params["loss_db_m"] == pytest.approx(1.2)

    # EPFL: <1 dB/m，Q>10⁷
    epfl = SIN_DEVICES["sin_waveguide_epfl"]()
    assert epfl.params["loss_db_m"] == pytest.approx(1.0)
    assert epfl.params["ring_q_factor"] >= 1.0e7


def test_sin_trench_visible_waveguide_params_match_literature() -> None:
    """Twente 沟槽与 Myongji 可见光波导参数须与文献报告值一致。"""
    # Twente 沟槽: 0.4 dB/cm，厚核 900nm
    trench = SIN_DEVICES["sin_waveguide_trench"]()
    assert trench.params["loss_db_cm"] == pytest.approx(0.4)
    assert trench.params["core_thickness_nm"] == 900

    # Myongji 可见光: 0.1 dB/cm
    vis = SIN_DEVICES["sin_waveguide_visible"]()
    assert vis.params["loss_db_cm"] == pytest.approx(0.1)


def test_sin_ring_resonator_params_match_literature() -> None:
    """Cornell 高 Q 微环谐振器参数须与文献报告值一致。"""
    # Cornell 高 Q: Q 37M（2.5μm）/ 67M（10μm）
    hq = SIN_DEVICES["sin_ring_high_q"]()
    assert hq.params["q_factor_2p5um"] == pytest.approx(3.7e7)
    assert hq.params["q_factor_10um"] == pytest.approx(6.7e7)


def test_sin_grating_coupler_params_match_literature() -> None:
    """三星光栅耦合器参数须与文献报告值一致。"""
    # 三星光栅: 2.1dB，57nm
    gc = SIN_DEVICES["sin_grating_coupler_1d"]()
    assert gc.params["coupling_loss_db"] == pytest.approx(2.1)
    assert gc.params["bandwidth_1db_nm"] == 57


def test_sin_material_params_match_literature() -> None:
    """SiN 材料本征参数须与文献报告值一致。"""
    # SiN 材料: Eg~5.1eV，n~2，损耗 0.045 dB/m，热膨胀 2.35e-6
    mat = SIN_DEVICES["sin_material"]()
    assert mat.params["bandgap_ev"] == pytest.approx(5.1)
    assert mat.params["refractive_index_1550nm"] == pytest.approx(2.0)
    assert mat.params["loss_db_m"] == pytest.approx(0.045)
    assert mat.params["thermal_expansion_per_k"] == pytest.approx(2.35e-6)


def test_sin_thermo_optic_params_match_literature() -> None:
    """SiN 热光系数须与文献报告值一致。"""
    # 热光系数: 0.2×10⁻⁴ /K = 2.0e-5
    to = SIN_DEVICES["sin_thermo_optic"]()
    assert to.params["thermo_optic_coefficient_per_k"] == pytest.approx(2.0e-5)


def test_sin_tsmc_waveguide_params_match_literature() -> None:
    """台积电 SiN 波导参数须与文献报告值一致。"""
    # 台积电波导: <0.23 dB/cm
    tsmc = SIN_DEVICES["sin_waveguide_tsmc"]()
    assert tsmc.params["loss_db_cm"] == pytest.approx(0.23)
