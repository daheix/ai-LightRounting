"""Foundry 平台有源器件库测试（第19轮 P0-3 深化）。

测试覆盖:
- 3 种有源器件类型（modulator/detector/phase_shifter）
- 10 foundry × 3 器件 = 30 个有源器件完整性
- 器件几何/端口/参数/来源验证
- foundry 间器件差异化（SOI vs SiN vs LNOI）
- 错误处理

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GF Fotonix: https://www.globalfoundries.com/en/press-release/globalfoundries-introduces-monolithic-photonics-platform
- LNOI: https://www.nanochemistrygroup.com/lnoi
"""

from __future__ import annotations

import pytest

from polaris.pdk.foundry_devices_active import (
    get_foundry_active_device,
    get_foundry_active_devices,
    list_active_device_types,
    total_active_devices_count,
)
from polaris.pdk.foundry_platforms import FOUNDRY_PLATFORMS
from polaris.pdk.port import Direction

# -- 器件类型列表测试 --


def test_list_active_device_types():
    """测试 list_active_device_types 返回 3 种有源器件类型。"""
    types = list_active_device_types()
    assert types == sorted(types)
    assert "modulator" in types
    assert "detector" in types
    assert "phase_shifter" in types
    assert len(types) == 3


def test_total_active_devices_count():
    """测试有源器件总数 = 10 foundry × 3 器件 = 30。"""
    total = total_active_devices_count()
    expected = len(FOUNDRY_PLATFORMS) * 3
    assert total == expected
    assert total >= 30


# -- 调制器测试 --


def test_modulator_basic():
    """测试调制器基本属性。"""
    dev = get_foundry_active_device("AMF", "modulator")
    assert dev.name == "modulator"
    assert dev.category == "active"
    assert dev.platform == "SOI"
    assert len(dev.ports) == 4
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out", "elec_in", "elec_out"}


def test_modulator_geometry():
    """测试调制器几何尺寸。"""
    dev = get_foundry_active_device("AMF", "modulator")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 100.0  # 调制器长度 100μm
    assert dev.bbox.ymax == 5.0  # 调制器宽度 5μm


def test_modulator_bandwidth_soi():
    """测试 SOI 平台调制器带宽 40GHz。"""
    dev = get_foundry_active_device("AMF", "modulator")
    assert dev.params["bandwidth_ghz"] == 40.0
    assert dev.params["vpi_l_v_cm"] == 1.0


def test_modulator_electrical_ports():
    """测试调制器电气端口朝向。"""
    dev = get_foundry_active_device("AMF", "modulator")
    elec_in = next(p for p in dev.ports if p.name == "elec_in")
    elec_out = next(p for p in dev.ports if p.name == "elec_out")
    assert elec_in.direction == Direction.SOUTH
    assert elec_out.direction == Direction.NORTH
    assert elec_in.waveguide_type == "electrical"


# -- 探测器测试 --


def test_detector_basic():
    """测试探测器基本属性。"""
    dev = get_foundry_active_device("AMF", "detector")
    assert dev.name == "detector"
    assert dev.category == "detector"
    assert len(dev.ports) == 3
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "elec_in", "elec_out"}


def test_detector_geometry():
    """测试探测器几何尺寸。"""
    dev = get_foundry_active_device("AMF", "detector")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 20.0  # 探测器长度 20μm
    assert dev.bbox.ymax == 10.0  # 探测器宽度 10μm


def test_detector_responsivity_soi():
    """测试 SOI 平台探测器响应度 0.9 A/W（Ge 探测器）。"""
    dev = get_foundry_active_device("AMF", "detector")
    assert dev.params["responsivity_a_w"] == 0.9
    assert dev.params["bandwidth_ghz"] == 50.0


def test_detector_responsivity_sin():
    """测试 SiN 平台探测器响应度 0.5 A/W（需外接 Ge）。"""
    dev = get_foundry_active_device("LIGENTEC", "detector")
    assert dev.params["responsivity_a_w"] == 0.5
    assert dev.params["bandwidth_ghz"] == 30.0


# -- 移相器测试 --


def test_phase_shifter_basic():
    """测试移相器基本属性。"""
    dev = get_foundry_active_device("AMF", "phase_shifter")
    assert dev.name == "phase_shifter"
    assert dev.category == "active"
    assert len(dev.ports) == 4
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out", "elec_in", "elec_out"}


def test_phase_shifter_geometry():
    """测试移相器几何尺寸。"""
    dev = get_foundry_active_device("AMF", "phase_shifter")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 50.0  # 移相器长度 50μm
    assert dev.bbox.ymax == 5.0  # 移相器宽度 5μm


def test_phase_shifter_vpi_l_soi():
    """测试 SOI 平台移相器 VπL 0.5 V·cm。"""
    dev = get_foundry_active_device("AMF", "phase_shifter")
    assert dev.params["vpi_l_v_cm"] == 0.5
    assert dev.params["power_mw"] == 20.0


# -- 多 foundry 完整性测试 --


def test_all_foundries_have_modulator():
    """测试所有 foundry 都能生成调制器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_active_device(name, "modulator")
        assert dev is not None
        assert dev.name == "modulator"
        assert dev.process_node == FOUNDRY_PLATFORMS[name].process_node


def test_all_foundries_have_detector():
    """测试所有 foundry 都能生成探测器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_active_device(name, "detector")
        assert dev is not None
        assert dev.name == "detector"


def test_all_foundries_have_phase_shifter():
    """测试所有 foundry 都能生成移相器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_active_device(name, "phase_shifter")
        assert dev is not None
        assert dev.name == "phase_shifter"


def test_get_foundry_active_devices_returns_three():
    """测试 get_foundry_active_devices 返回 3 个器件。"""
    for name in FOUNDRY_PLATFORMS:
        devices = get_foundry_active_devices(name)
        assert len(devices) == 3
        device_names = {d.name for d in devices}
        assert device_names == {"modulator", "detector", "phase_shifter"}


# -- foundry 间器件差异化测试 --


def test_soi_vs_sin_detector_responsivity():
    """测试 SOI vs SiN 平台探测器响应度差异。"""
    amf = get_foundry_active_device("AMF", "detector")  # SOI
    lig = get_foundry_active_device("LIGENTEC", "detector")  # SiN
    # SOI Ge 探测器响应度 > SiN（SiN 需外接 Ge）
    assert amf.params["responsivity_a_w"] > lig.params["responsivity_a_w"]


def test_soi_vs_sin_detector_bandwidth():
    """测试 SOI vs SiN 平台探测器带宽差异。"""
    amf = get_foundry_active_device("AMF", "detector")  # SOI
    lig = get_foundry_active_device("LIGENTEC", "detector")  # SiN
    # SOI 探测器带宽 > SiN
    assert amf.params["bandwidth_ghz"] > lig.params["bandwidth_ghz"]


def test_soi_vs_lnoi_modulator_bandwidth():
    """测试 SOI vs LNOI 平台调制器带宽差异。"""
    # 找一个 LNOI foundry（如果存在）
    lnoi_foundries = [
        n for n, f in FOUNDRY_PLATFORMS.items() if f.material_platform == "LNOI"
    ]
    if not lnoi_foundries:
        pytest.skip("无 LNOI 平台 foundry")
    soi_dev = get_foundry_active_device("AMF", "modulator")  # SOI
    lnoi_dev = get_foundry_active_device(lnoi_foundries[0], "modulator")  # LNOI
    # LNOI 调制器带宽 > SOI（Pockels 效应更快）
    assert lnoi_dev.params["bandwidth_ghz"] > soi_dev.params["bandwidth_ghz"]


def test_device_source_nonempty():
    """测试所有有源器件都有非空 source。"""
    for name in FOUNDRY_PLATFORMS:
        for dev_type in ["modulator", "detector", "phase_shifter"]:
            dev = get_foundry_active_device(name, dev_type)
            assert dev.source is not None
            assert len(dev.source.title) > 0
            assert dev.source.year == 2024


def test_device_process_node_consistency():
    """测试有源器件 process_node 与 foundry 平台一致。"""
    for name in FOUNDRY_PLATFORMS:
        foundry = FOUNDRY_PLATFORMS[name]
        for dev_type in ["modulator", "detector", "phase_shifter"]:
            dev = get_foundry_active_device(name, dev_type)
            assert dev.process_node == foundry.process_node


def test_device_category_correct():
    """测试有源器件 category 正确。"""
    for name in FOUNDRY_PLATFORMS:
        mod = get_foundry_active_device(name, "modulator")
        det = get_foundry_active_device(name, "detector")
        ps = get_foundry_active_device(name, "phase_shifter")
        assert mod.category == "active"
        assert det.category == "detector"
        assert ps.category == "active"


# -- 错误处理测试 --


def test_get_foundry_active_device_invalid_foundry():
    """测试未知 foundry 抛 KeyError。"""
    with pytest.raises(KeyError, match="未知 foundry"):
        get_foundry_active_device("UNKNOWN_FOUNDRY", "modulator")


def test_get_foundry_active_device_invalid_type():
    """测试未知有源器件类型抛 KeyError。"""
    with pytest.raises(KeyError, match="未知有源器件类型"):
        get_foundry_active_device("AMF", "unknown_type")


# -- 器件几何变换测试 --


def test_modulator_translate():
    """测试调制器平移变换。"""
    dev = get_foundry_active_device("AMF", "modulator")
    translated = dev.translate(100.0, 200.0)
    assert translated.bbox.xmin == 100.0
    assert translated.bbox.ymin == 200.0


def test_detector_rotate_90():
    """测试探测器 90 度旋转变换。"""
    dev = get_foundry_active_device("AMF", "detector")
    rotated = dev.rotate(90)
    # 旋转后 in 端口朝向应从 WEST 变为 SOUTH
    in_port = next(p for p in rotated.ports if p.name == "in")
    assert in_port.direction == Direction.SOUTH
