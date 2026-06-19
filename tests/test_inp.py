"""InP 平台器件库单元测试（Task 5）。

验证每个器件工厂函数返回有效 Device，且：
- source.url 非空且以 http 开头（溯源校验，禁止假数据）
- params 字典非空（含关键电光参数）
- ports 列表非空（含合理端口）
- bbox 为合理包围盒
- constraints 包含最小间距
"""

from __future__ import annotations

import pytest

from polaris.pdk import Device
from polaris.pdk.inp import INP_DEVICES

# 所有 InP 器件工厂函数名（与 INP_DEVICES 键一致）
_ALL_DEVICE_NAMES = list(INP_DEVICES.keys())


def test_inp_devices_dict_not_empty() -> None:
    """INP_DEVICES 字典应非空且包含 17 个器件。"""
    assert len(INP_DEVICES) == 17, f"期望 17 个器件，实际 {len(INP_DEVICES)}"


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_factory_returns_valid_device(device_name: str) -> None:
    """每个工厂函数应返回有效 Device 实例。"""
    factory = INP_DEVICES[device_name]
    dev = factory()
    assert isinstance(dev, Device), f"{device_name} 工厂未返回 Device 实例"
    assert dev.device_id, f"{device_name} 的 device_id 为空"
    assert dev.platform == "InP", f"{device_name} 的 platform 应为 InP"
    assert dev.category in ("passive", "active", "source", "detector"), (
        f"{device_name} 的 category 非法: {dev.category}"
    )
    assert dev.name, f"{device_name} 的 name 为空"


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_device_source_url_valid(device_name: str) -> None:
    """每个 Device 的 source.url 须非空且以 http 开头（溯源校验）。"""
    dev = INP_DEVICES[device_name]()
    assert dev.source is not None, f"{device_name} 的 source 为 None"
    assert dev.source.url, f"{device_name} 的 source.url 为空"
    assert dev.source.url.startswith("http"), (
        f"{device_name} 的 source.url 不以 http 开头: {dev.source.url}"
    )
    assert dev.source.title, f"{device_name} 的 source.title 为空"
    assert dev.source.authors, f"{device_name} 的 source.authors 为空"
    assert dev.source.year > 0, f"{device_name} 的 source.year 非法: {dev.source.year}"


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_device_params_not_empty(device_name: str) -> None:
    """每个 Device 的 params 字典须非空。"""
    dev = INP_DEVICES[device_name]()
    assert dev.params, f"{device_name} 的 params 字典为空"
    assert len(dev.params) > 0


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_device_ports_not_empty(device_name: str) -> None:
    """每个 Device 的 ports 列表须非空。"""
    dev = INP_DEVICES[device_name]()
    assert dev.ports, f"{device_name} 的 ports 列表为空"
    assert len(dev.ports) >= 1


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_device_bbox_valid(device_name: str) -> None:
    """每个 Device 的 bbox 须合法（xmin<xmax, ymin<ymax）。"""
    dev = INP_DEVICES[device_name]()
    assert dev.bbox.xmax > dev.bbox.xmin, f"{device_name} 的 bbox xmax<=xmin: {dev.bbox}"
    assert dev.bbox.ymax > dev.bbox.ymin, f"{device_name} 的 bbox ymax<=ymin: {dev.bbox}"


@pytest.mark.parametrize("device_name", _ALL_DEVICE_NAMES)
def test_device_constraints_present(device_name: str) -> None:
    """每个 Device 的 constraints 须包含最小间距约束。"""
    dev = INP_DEVICES[device_name]()
    assert "min_spacing_um" in dev.constraints, f"{device_name} 的 constraints 缺少 min_spacing_um"
    assert dev.constraints["min_spacing_um"] > 0


# ---------------------------------------------------------------------------
# 特定器件端口校验
# ---------------------------------------------------------------------------


def test_lasers_have_output_port() -> None:
    """激光器类器件须有 output 端口。"""
    laser_names = [
        "dfb_laser",
        "dbr_laser",
        "sgdbr_laser",
        "dfb_laser_oband",
        "dfb_laser_coherent",
        "imos_dfb_laser",
    ]
    for name in laser_names:
        dev = INP_DEVICES[name]()
        port_names = [p.name for p in dev.ports]
        assert "output" in port_names, f"{name} 缺少 output 端口"


def test_detector_has_in_and_electrical_ports() -> None:
    """探测器须有 in 与 electrical 端口。"""
    dev = INP_DEVICES["inp_photodetector"]()
    port_names = [p.name for p in dev.ports]
    assert "in" in port_names, "inp_photodetector 缺少 in 端口"
    assert "electrical" in port_names, "inp_photodetector 缺少 electrical 端口"


def test_soa_has_in_and_out_ports() -> None:
    """SOA 须有 in 与 out 端口。"""
    for name in ("soa", "soa_high_power"):
        dev = INP_DEVICES[name]()
        port_names = [p.name for p in dev.ports]
        assert "in" in port_names, f"{name} 缺少 in 端口"
        assert "out" in port_names, f"{name} 缺少 out 端口"


def test_waveguide_has_in_and_out_ports() -> None:
    """波导须有 in 与 out 端口。"""
    dev = INP_DEVICES["inp_waveguide"]()
    port_names = [p.name for p in dev.ports]
    assert "in" in port_names
    assert "out" in port_names


# ---------------------------------------------------------------------------
# 特定器件参数校验（真实文献参数核对）
# ---------------------------------------------------------------------------


def test_inp_waveguide_params() -> None:
    """InP 有源波导参数须符合文献（宽 1.5-2.5μm，SSC 模场 10×7μm）。"""
    dev = INP_DEVICES["inp_waveguide"]()
    assert "10x7" in dev.params["ssc_mode_field_um"]
    assert dev.params["width_range_um"] == "1.5-2.5"


def test_eam_modulator_bandwidth() -> None:
    """EAM 带宽须为 ~45GHz。"""
    dev = INP_DEVICES["eam_modulator"]()
    assert dev.params["bandwidth_ghz"] == pytest.approx(45.0)


def test_inp_photodetector_responsivity() -> None:
    """InP 光电探测器内部响应率须 >0.8 A/W。"""
    dev = INP_DEVICES["inp_photodetector"]()
    assert dev.params["responsivity_a_w"] >= 0.8


def test_soa_gain() -> None:
    """SOA 增益须为 ~4dB/100μm。"""
    dev = INP_DEVICES["soa"]()
    assert dev.params["gain_db_per_100um"] == pytest.approx(4.0)


def test_dfb_laser_output_power() -> None:
    """DFB 激光器输出功率须 >3mW。"""
    dev = INP_DEVICES["dfb_laser"]()
    assert dev.params["output_power_mw"] >= 3.0


def test_sgdbr_laser_tuning_range() -> None:
    """SGDBR 激光器调谐范围须为 1521-1565nm。"""
    dev = INP_DEVICES["sgdbr_laser"]()
    assert dev.params["tuning_range_nm"] == "1521-1565"
    assert dev.params["smsr_db"] >= 45.0


def test_inp_mzm_length() -> None:
    """InP MZM 长度须为 1mm。"""
    dev = INP_DEVICES["inp_mzm"]()
    assert dev.params["length_mm"] == pytest.approx(1.0)


def test_dfb_laser_oband_power() -> None:
    """O-band DFB 激光器输出功率须为 200-250mW。"""
    dev = INP_DEVICES["dfb_laser_oband"]()
    assert dev.params["output_power_mw"] == "200-250"


def test_soa_high_power_output() -> None:
    """超高功率 SOA 输出须 >1W。"""
    dev = INP_DEVICES["soa_high_power"]()
    assert dev.params["output_power_w"] >= 1.0
    assert dev.params["pce_percent"] == pytest.approx(25.0)


def test_dfb_laser_coherent_params() -> None:
    """Coherent BH DFB 激光器参数须符合文献（1311nm, 400mW, <200kHz）。"""
    dev = INP_DEVICES["dfb_laser_coherent"]()
    assert dev.params["wavelength_nm"] == pytest.approx(1311.0)
    assert dev.params["output_power_mw"] == pytest.approx(400.0)
    assert dev.params["linewidth_khz"] <= 200.0
    assert dev.params["rin_db_hz"] <= -145.0


def test_imos_dfb_laser_params() -> None:
    """IMOS DFB 激光器参数须符合文献（250μm, 600μW, 15GHz, 25Gbit/s）。"""
    dev = INP_DEVICES["imos_dfb_laser"]()
    assert dev.params["length_um"] == pytest.approx(250.0)
    assert dev.params["fiber_power_uw"] == pytest.approx(600.0)
    assert dev.params["bandwidth_ghz"] == pytest.approx(15.0)
    assert dev.params["data_rate_gbps"] == pytest.approx(25.0)


# ---------------------------------------------------------------------------
# 器件变换不变性校验（translate/rotate 后 source 不变）
# ---------------------------------------------------------------------------


def test_translate_preserves_source() -> None:
    """translate 后 source 字段应保持不变（溯源数据不可篡改）。"""
    dev = INP_DEVICES["dfb_laser"]()
    assert dev.source is not None
    moved = dev.translate(10.0, 20.0)
    assert moved.source is not None
    assert moved.source.url == dev.source.url


def test_rotate_preserves_source() -> None:
    """rotate 后 source 字段应保持不变。"""
    dev = INP_DEVICES["soa"]()
    assert dev.source is not None
    rot = dev.rotate(90)
    assert rot.source is not None
    assert rot.source.url == dev.source.url
