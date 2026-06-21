"""Foundry 平台高级器件库测试（第17轮 P0-3 深化）。

测试覆盖:
- 3 种高级器件类型（ring_resonator/directional_coupler/grating_coupler）
- 10 foundry × 3 器件 = 30 个高级器件完整性
- 器件几何/端口/参数/来源验证
- foundry 间器件差异化（SOI vs SiN）
- 错误处理

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic_pdk: https://github.com/gdsfactory/gdsfactory
- Luceda IPKISS PDK: https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
"""

from __future__ import annotations

import pytest

from polaris.pdk.foundry_devices_advanced import (
    get_foundry_advanced_device,
    get_foundry_advanced_devices,
    list_advanced_device_types,
    total_advanced_devices_count,
)
from polaris.pdk.foundry_platforms import FOUNDRY_PLATFORMS
from polaris.pdk.port import Direction

# -- 器件类型列表测试 --


def test_list_advanced_device_types():
    """测试 list_advanced_device_types 返回 3 种高级器件类型。"""
    types = list_advanced_device_types()
    assert types == sorted(types)
    assert "ring_resonator" in types
    assert "directional_coupler" in types
    assert "grating_coupler" in types
    assert len(types) == 3


def test_total_advanced_devices_count():
    """测试高级器件总数 = 10 foundry × 3 器件 = 30。"""
    total = total_advanced_devices_count()
    expected = len(FOUNDRY_PLATFORMS) * 3
    assert total == expected
    assert total >= 30


# -- 环谐振器测试 --


def test_ring_resonator_basic():
    """测试环谐振器基本属性。"""
    dev = get_foundry_advanced_device("AMF", "ring_resonator")
    assert dev.name == "ring_resonator"
    assert dev.category == "passive"
    assert dev.platform == "SOI"
    assert len(dev.ports) == 2
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out"}


def test_ring_resonator_geometry():
    """测试环谐振器几何尺寸。"""
    dev = get_foundry_advanced_device("AMF", "ring_resonator")
    amf = FOUNDRY_PLATFORMS["AMF"]
    expected_radius = amf.min_bend_radius_um * 2
    expected_size = expected_radius * 2 + amf.waveguide_width_um * 2
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert abs(dev.bbox.xmax - expected_size) < 1e-9
    assert abs(dev.bbox.ymax - expected_size) < 1e-9
    assert dev.params["ring_radius_um"] == expected_radius


def test_ring_resonator_fsr_soi():
    """测试 SOI 平台环谐振器 FSR 100GHz。"""
    dev = get_foundry_advanced_device("AMF", "ring_resonator")
    assert dev.params["fsr_ghz"] == 100.0
    assert dev.params["q_factor"] == 5000.0


def test_ring_resonator_fsr_sin():
    """测试 SiN 平台环谐振器 FSR 50GHz（SiN 折射率差小，FSR 更小）。"""
    dev = get_foundry_advanced_device("LIGENTEC", "ring_resonator")
    assert dev.params["fsr_ghz"] == 50.0
    assert dev.params["q_factor"] == 10000.0


# -- 定向耦合器测试 --


def test_directional_coupler_basic():
    """测试定向耦合器基本属性。"""
    dev = get_foundry_advanced_device("AMF", "directional_coupler")
    assert dev.name == "directional_coupler"
    assert dev.category == "passive"
    assert len(dev.ports) == 4
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in1", "in2", "out1", "out2"}


def test_directional_coupler_geometry():
    """测试定向耦合器几何尺寸。"""
    dev = get_foundry_advanced_device("AMF", "directional_coupler")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 30.0  # DC 长度 30μm
    assert dev.bbox.ymax == 5.0  # DC 宽度 5μm


def test_directional_coupler_coupling_gap_soi():
    """测试 SOI 平台 DC 耦合间隙 0.1μm。"""
    dev = get_foundry_advanced_device("AMF", "directional_coupler")
    assert dev.params["coupling_gap_um"] == 0.1
    assert dev.params["coupling_ratio"] == 0.5


def test_directional_coupler_coupling_gap_sin():
    """测试 SiN 平台 DC 耦合间隙 0.2μm（SiN 工艺限制）。"""
    dev = get_foundry_advanced_device("LIGENTEC", "directional_coupler")
    assert dev.params["coupling_gap_um"] == 0.2


# -- 光栅耦合器测试 --


def test_grating_coupler_basic():
    """测试光栅耦合器基本属性。"""
    dev = get_foundry_advanced_device("AMF", "grating_coupler")
    assert dev.name == "grating_coupler"
    assert dev.category == "passive"
    assert len(dev.ports) == 2
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "fiber"}


def test_grating_coupler_geometry():
    """测试光栅耦合器几何尺寸。"""
    dev = get_foundry_advanced_device("AMF", "grating_coupler")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 20.0  # GC 尺寸 20μm
    assert dev.bbox.ymax == 20.0


def test_grating_coupler_efficiency_soi():
    """测试 SOI 平台 GC 耦合效率 50%。"""
    dev = get_foundry_advanced_device("AMF", "grating_coupler")
    assert dev.params["coupling_efficiency"] == 0.5
    assert dev.params["insertion_loss_db"] == 1.5


def test_grating_coupler_efficiency_sin():
    """测试 SiN 平台 GC 耦合效率 30%（SiN 光栅效率略低）。"""
    dev = get_foundry_advanced_device("LIGENTEC", "grating_coupler")
    assert dev.params["coupling_efficiency"] == 0.3
    assert dev.params["insertion_loss_db"] == 3.0


def test_grating_coupler_fiber_port():
    """测试光栅耦合器 fiber 端口朝向 NORTH。"""
    dev = get_foundry_advanced_device("AMF", "grating_coupler")
    fiber_port = next(p for p in dev.ports if p.name == "fiber")
    assert fiber_port.direction == Direction.NORTH
    assert fiber_port.waveguide_type == "fiber"
    assert fiber_port.width == 10.4  # 光纤模场直径


# -- 多 foundry 完整性测试 --


def test_all_foundries_have_ring_resonator():
    """测试所有 foundry 都能生成环谐振器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_advanced_device(name, "ring_resonator")
        assert dev is not None
        assert dev.name == "ring_resonator"
        assert dev.process_node == FOUNDRY_PLATFORMS[name].process_node


def test_all_foundries_have_directional_coupler():
    """测试所有 foundry 都能生成定向耦合器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_advanced_device(name, "directional_coupler")
        assert dev is not None
        assert dev.name == "directional_coupler"


def test_all_foundries_have_grating_coupler():
    """测试所有 foundry 都能生成光栅耦合器。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_advanced_device(name, "grating_coupler")
        assert dev is not None
        assert dev.name == "grating_coupler"


def test_get_foundry_advanced_devices_returns_three():
    """测试 get_foundry_advanced_devices 返回 3 个器件。"""
    for name in FOUNDRY_PLATFORMS:
        devices = get_foundry_advanced_devices(name)
        assert len(devices) == 3
        device_names = {d.name for d in devices}
        assert device_names == {
            "ring_resonator",
            "directional_coupler",
            "grating_coupler",
        }


# -- foundry 间器件差异化测试 --


def test_soi_vs_sin_ring_fsr():
    """测试 SOI vs SiN 平台环谐振器 FSR 差异。"""
    amf = get_foundry_advanced_device("AMF", "ring_resonator")  # SOI
    lig = get_foundry_advanced_device("LIGENTEC", "ring_resonator")  # SiN
    # SiN 平台 FSR < SOI 平台（SiN 折射率差小）
    assert lig.params["fsr_ghz"] < amf.params["fsr_ghz"]


def test_soi_vs_sin_dc_coupling_gap():
    """测试 SOI vs SiN 平台 DC 耦合间隙差异。"""
    amf = get_foundry_advanced_device("AMF", "directional_coupler")  # SOI
    lig = get_foundry_advanced_device("LIGENTEC", "directional_coupler")  # SiN
    # SiN 平台耦合间隙 > SOI 平台（SiN 工艺限制）
    assert lig.params["coupling_gap_um"] > amf.params["coupling_gap_um"]


def test_soi_vs_sin_gc_efficiency():
    """测试 SOI vs SiN 平台 GC 耦合效率差异。"""
    amf = get_foundry_advanced_device("AMF", "grating_coupler")  # SOI
    lig = get_foundry_advanced_device("LIGENTEC", "grating_coupler")  # SiN
    # SiN 平台 GC 效率 < SOI 平台
    assert lig.params["coupling_efficiency"] < amf.params["coupling_efficiency"]


def test_device_source_nonempty():
    """测试所有高级器件都有非空 source。"""
    for name in FOUNDRY_PLATFORMS:
        for dev_type in ["ring_resonator", "directional_coupler", "grating_coupler"]:
            dev = get_foundry_advanced_device(name, dev_type)
            assert dev.source is not None
            assert len(dev.source.title) > 0
            assert dev.source.year == 2024


def test_device_process_node_consistency():
    """测试高级器件 process_node 与 foundry 平台一致。"""
    for name in FOUNDRY_PLATFORMS:
        foundry = FOUNDRY_PLATFORMS[name]
        for dev_type in ["ring_resonator", "directional_coupler", "grating_coupler"]:
            dev = get_foundry_advanced_device(name, dev_type)
            assert dev.process_node == foundry.process_node


# -- 错误处理测试 --


def test_get_foundry_advanced_device_invalid_foundry():
    """测试未知 foundry 抛 KeyError。"""
    with pytest.raises(KeyError, match="未知 foundry"):
        get_foundry_advanced_device("UNKNOWN_FOUNDRY", "ring_resonator")


def test_get_foundry_advanced_device_invalid_type():
    """测试未知高级器件类型抛 KeyError。"""
    with pytest.raises(KeyError, match="未知高级器件类型"):
        get_foundry_advanced_device("AMF", "unknown_type")


# -- 器件几何变换测试 --


def test_ring_resonator_translate():
    """测试环谐振器平移变换。"""
    dev = get_foundry_advanced_device("AMF", "ring_resonator")
    translated = dev.translate(50.0, 50.0)
    assert translated.bbox.xmin == 50.0
    assert translated.bbox.ymin == 50.0


def test_directional_coupler_rotate_180():
    """测试定向耦合器 180 度旋转变换。"""
    dev = get_foundry_advanced_device("AMF", "directional_coupler")
    rotated = dev.rotate(180)
    # 旋转后 in1 端口朝向应从 WEST 变为 EAST
    in1_port = next(p for p in rotated.ports if p.name == "in1")
    assert in1_port.direction == Direction.EAST
