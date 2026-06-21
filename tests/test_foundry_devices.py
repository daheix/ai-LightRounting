"""Foundry 平台基础器件库测试（第16轮 P0-3 深化）。

测试覆盖:
- FoundryDeviceSpec dataclass
- 3 种器件类型（straight/mmi1x2/ybranch）工厂函数
- 10 foundry × 3 器件 = 30 个器件完整性
- 器件几何/端口/参数/来源验证
- foundry 间器件差异化（SOI vs SiN）
- 错误处理

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Luceda IPKISS PDK: https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
- IHP Open PDK: https://github.com/IHP-GmbH/IHP-Open-PDK
"""

from __future__ import annotations

import pytest

from polaris.pdk.foundry_devices import (
    FoundryDeviceSpec,
    get_foundry_device,
    get_foundry_devices,
    list_foundry_device_types,
    total_foundry_devices_count,
)
from polaris.pdk.foundry_platforms import FOUNDRY_PLATFORMS
from polaris.pdk.port import Direction

# -- FoundryDeviceSpec dataclass 测试 --


def test_foundry_device_spec_dataclass():
    """测试 FoundryDeviceSpec dataclass。"""
    from polaris.pdk.source import Source

    src = Source(title="test", authors="test", year=2024, url="https://example.com")
    spec = FoundryDeviceSpec(
        foundry_name="AMF",
        device_type="straight",
        waveguide_width_um=0.4,
        length_um=10.0,
        insertion_loss_db=0.5,
        source=src,
    )
    assert spec.foundry_name == "AMF"
    assert spec.device_type == "straight"
    assert spec.waveguide_width_um == 0.4
    assert spec.insertion_loss_db == 0.5


def test_foundry_device_spec_frozen():
    """测试 FoundryDeviceSpec 是 frozen dataclass。"""
    spec = FoundryDeviceSpec(
        foundry_name="AMF",
        device_type="straight",
        waveguide_width_um=0.4,
        length_um=10.0,
        insertion_loss_db=0.5,
        source=__import__("polaris.pdk.source", fromlist=["Source"]).Source(
            title="t", authors="a", year=2024, url="https://example.com"
        ),
    )
    with pytest.raises((AttributeError, Exception)):
        spec.foundry_name = "MODIFIED"  # type: ignore[misc]


# -- 器件类型列表测试 --


def test_list_foundry_device_types():
    """测试 list_foundry_device_types 返回 3 种器件类型。"""
    types = list_foundry_device_types()
    assert types == sorted(types)
    assert "straight" in types
    assert "mmi1x2" in types
    assert "ybranch" in types
    assert len(types) == 3


def test_total_foundry_devices_count():
    """测试基础器件总数 = 10 foundry × 3 器件 = 30。"""
    total = total_foundry_devices_count()
    expected = len(FOUNDRY_PLATFORMS) * 3
    assert total == expected
    assert total >= 30  # 至少 10 foundry × 3 器件


# -- 直波导器件测试 --


def test_straight_waveguide_basic():
    """测试直波导器件基本属性。"""
    dev = get_foundry_device("AMF", "straight")
    assert dev.name == "straight_waveguide"
    assert dev.category == "passive"
    assert dev.platform == "SOI"
    assert len(dev.ports) == 2
    # 端口名和朝向
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out"}
    in_port = next(p for p in dev.ports if p.name == "in")
    out_port = next(p for p in dev.ports if p.name == "out")
    assert in_port.direction == Direction.WEST
    assert out_port.direction == Direction.EAST


def test_straight_waveguide_geometry():
    """测试直波导几何尺寸。"""
    dev = get_foundry_device("AMF", "straight")
    amf = FOUNDRY_PLATFORMS["AMF"]
    # bbox 应为 (0, 0, length, width)
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 10.0  # 默认 10μm 长
    assert dev.bbox.ymax == amf.waveguide_width_um
    # 波导宽度应与 foundry 平台一致
    assert dev.params["width_um"] == amf.waveguide_width_um


def test_straight_waveguide_loss():
    """测试直波导损耗计算。"""
    dev = get_foundry_device("AMF", "straight")
    amf = FOUNDRY_PLATFORMS["AMF"]
    expected_loss = 10.0 * amf.waveguide_loss_db_cm / 10000.0
    assert abs(dev.params["loss_db"] - expected_loss) < 1e-9


# -- MMI 1x2 器件测试 --


def test_mmi1x2_basic():
    """测试 MMI 1x2 器件基本属性。"""
    dev = get_foundry_device("AMF", "mmi1x2")
    assert dev.name == "mmi1x2"
    assert dev.category == "passive"
    assert len(dev.ports) == 3
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out1", "out2"}


def test_mmi1x2_geometry():
    """测试 MMI 1x2 几何尺寸。"""
    dev = get_foundry_device("AMF", "mmi1x2")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 20.0  # MMI 长度 20μm
    assert dev.bbox.ymax == 5.0  # MMI 宽度 5μm


def test_mmi1x2_insertion_loss_soi():
    """测试 SOI 平台 MMI 插损 0.5dB。"""
    dev = get_foundry_device("AMF", "mmi1x2")
    assert dev.params["insertion_loss_db"] == 0.5


def test_mmi1x2_insertion_loss_sin():
    """测试 SiN 平台 MMI 插损 0.8dB（SiN 工艺损耗略高）。"""
    dev = get_foundry_device("LIGENTEC", "mmi1x2")
    assert dev.params["insertion_loss_db"] == 0.8


# -- Y 分支器件测试 --


def test_ybranch_basic():
    """测试 Y 分支器件基本属性。"""
    dev = get_foundry_device("AMF", "ybranch")
    assert dev.name == "ybranch"
    assert dev.category == "passive"
    assert len(dev.ports) == 3
    port_names = {p.name for p in dev.ports}
    assert port_names == {"in", "out1", "out2"}


def test_ybranch_geometry():
    """测试 Y 分支几何尺寸。"""
    dev = get_foundry_device("AMF", "ybranch")
    assert dev.bbox.xmin == 0.0
    assert dev.bbox.ymin == 0.0
    assert dev.bbox.xmax == 10.0  # Y 分支长度 10μm
    assert dev.bbox.ymax == 5.0  # Y 分支宽度 5μm


def test_ybranch_insertion_loss_soi():
    """测试 SOI 平台 Y 分支插损 0.3dB。"""
    dev = get_foundry_device("AMF", "ybranch")
    assert dev.params["insertion_loss_db"] == 0.3


def test_ybranch_insertion_loss_sin():
    """测试 SiN 平台 Y 分支插损 0.5dB。"""
    dev = get_foundry_device("LIGENTEC", "ybranch")
    assert dev.params["insertion_loss_db"] == 0.5


# -- 多 foundry 器件完整性测试 --


def test_all_foundries_have_straight():
    """测试所有 foundry 都能生成直波导。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_device(name, "straight")
        assert dev is not None
        assert dev.name == "straight_waveguide"
        assert dev.process_node == FOUNDRY_PLATFORMS[name].process_node


def test_all_foundries_have_mmi1x2():
    """测试所有 foundry 都能生成 MMI 1x2。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_device(name, "mmi1x2")
        assert dev is not None
        assert dev.name == "mmi1x2"


def test_all_foundries_have_ybranch():
    """测试所有 foundry 都能生成 Y 分支。"""
    for name in FOUNDRY_PLATFORMS:
        dev = get_foundry_device(name, "ybranch")
        assert dev is not None
        assert dev.name == "ybranch"


def test_get_foundry_devices_returns_three():
    """测试 get_foundry_devices 返回 3 个器件。"""
    for name in FOUNDRY_PLATFORMS:
        devices = get_foundry_devices(name)
        assert len(devices) == 3
        device_names = {d.name for d in devices}
        assert device_names == {"straight_waveguide", "mmi1x2", "ybranch"}


# -- foundry 间器件差异化测试 --


def test_soi_vs_sin_waveguide_width():
    """测试 SOI vs SiN 平台波导宽度差异。"""
    amf = get_foundry_device("AMF", "straight")  # SOI
    lig = get_foundry_device("LIGENTEC", "straight")  # SiN
    # SiN 平台波导宽度通常大于 SOI
    assert lig.params["width_um"] > amf.params["width_um"]


def test_soi_vs_sin_mmi_loss():
    """测试 SOI vs SiN 平台 MMI 插损差异。"""
    amf = get_foundry_device("AMF", "mmi1x2")  # SOI
    lig = get_foundry_device("LIGENTEC", "mmi1x2")  # SiN
    # SiN 平台 MMI 插损 > SOI 平台
    assert lig.params["insertion_loss_db"] > amf.params["insertion_loss_db"]


def test_device_source_nonempty():
    """测试所有器件都有非空 source。"""
    for name in FOUNDRY_PLATFORMS:
        for dev_type in ["straight", "mmi1x2", "ybranch"]:
            dev = get_foundry_device(name, dev_type)
            assert dev.source is not None
            assert len(dev.source.title) > 0
            assert dev.source.year == 2024


def test_device_process_node_consistency():
    """测试器件 process_node 与 foundry 平台一致。"""
    for name in FOUNDRY_PLATFORMS:
        foundry = FOUNDRY_PLATFORMS[name]
        for dev_type in ["straight", "mmi1x2", "ybranch"]:
            dev = get_foundry_device(name, dev_type)
            assert dev.process_node == foundry.process_node


def test_device_platform_consistency():
    """测试器件 platform 与 foundry 材料平台一致。"""
    for name in FOUNDRY_PLATFORMS:
        foundry = FOUNDRY_PLATFORMS[name]
        for dev_type in ["straight", "mmi1x2", "ybranch"]:
            dev = get_foundry_device(name, dev_type)
            assert dev.platform == foundry.material_platform


# -- 错误处理测试 --


def test_get_foundry_device_invalid_foundry():
    """测试未知 foundry 抛 KeyError。"""
    with pytest.raises(KeyError, match="未知 foundry"):
        get_foundry_device("UNKNOWN_FOUNDRY", "straight")


def test_get_foundry_device_invalid_type():
    """测试未知器件类型抛 KeyError。"""
    with pytest.raises(KeyError, match="未知器件类型"):
        get_foundry_device("AMF", "unknown_type")


# -- 器件几何变换测试 --


def test_straight_waveguide_translate():
    """测试直波导平移变换。"""
    dev = get_foundry_device("AMF", "straight")
    translated = dev.translate(100.0, 200.0)
    assert translated.bbox.xmin == 100.0
    assert translated.bbox.ymin == 200.0
    # 端口坐标同步更新
    in_port = next(p for p in translated.ports if p.name == "in")
    assert in_port.x == 100.0


def test_straight_waveguide_rotate_90():
    """测试直波导 90 度旋转变换。"""
    dev = get_foundry_device("AMF", "straight")
    rotated = dev.rotate(90)
    # 旋转后 bbox 应交换宽高（近似）
    assert rotated.bbox.xmax <= dev.bbox.ymax + 1e-9
    # 端口朝向应旋转
    in_port = next(p for p in rotated.ports if p.name == "in")
    # 原 WEST 旋转 90 度后应为 SOUTH
    assert in_port.direction == Direction.SOUTH
