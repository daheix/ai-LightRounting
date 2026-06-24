"""gdsfactory 集成模块测试（步骤4：生成真实参数化器件 GDS + 第2轮 PDK 桥接）。

验证 gdsfactory 集成模块的接口正确性，包括：
1. GDS 文件生成（generate_mzi_gds / generate_ring_resonator_gds / generate_component_gds）
2. PDK 桥接（gdsfactory_to_polaris_device / load_gdsfactory_pdk /
   list_gdsfactory_pdks / register_gdsfactory_pdk）—— 第2轮 P0-3

注：gdsfactory 8.18.0 锁定 pydantic<2.10，在 Python 3.14 环境下可能 import 失败
（上游版本锁定问题）。测试用 ``pytest.importorskip`` 跳过真实生成测试，
但降级行为测试始终运行。在 Python 3.10-3.13 环境下 gdsfactory 可正常使用。

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- 差距分析 P0-3: docs/commercial_gap_analysis.md
"""

from __future__ import annotations

import pytest

from polaris.pdk.gdsfactory_integration import (
    DeviceImportConfig,
    gdsfactory_to_polaris_device,
    generate_component_gds,
    generate_mzi_gds,
    generate_ring_resonator_gds,
    is_available,
    list_available_components,
    list_gdsfactory_pdks,
    load_gdsfactory_pdk,
    register_gdsfactory_pdk,
)
from polaris.pdk.port import Direction


def test_is_available_returns_bool():
    """is_available() 应返回 bool。"""
    result = is_available()
    assert isinstance(result, bool)


def test_generate_mzi_gds_unavailable_raises(tmp_path):
    """gdsfactory 不可用时 generate_mzi_gds 应 raise ImportError（违规 4 修复）。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    with pytest.raises(ImportError, match="gdsfactory 未安装"):
        generate_mzi_gds(str(tmp_path / "mzi.gds"))


def test_generate_ring_gds_unavailable_raises(tmp_path):
    """gdsfactory 不可用时 generate_ring_resonator_gds 应 raise ImportError（违规 4 修复）。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    with pytest.raises(ImportError, match="gdsfactory 未安装"):
        generate_ring_resonator_gds(str(tmp_path / "ring.gds"))


def test_generate_component_gds_unavailable_raises(tmp_path):
    """gdsfactory 不可用时 generate_component_gds 应 raise ImportError（违规 4 修复）。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    with pytest.raises(ImportError, match="gdsfactory 未安装"):
        generate_component_gds("straight", str(tmp_path / "wg.gds"))


def test_list_available_components_returns_list():
    """list_available_components 应返回列表（可能为空）。"""
    result = list_available_components()
    assert isinstance(result, list)


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_generate_mzi_gds_real(tmp_path):
    """gdsfactory 可用时应生成真实 MZI GDS 文件。"""
    output = generate_mzi_gds(str(tmp_path / "real_mzi.gds"), delta_length_um=50.0)
    assert output != "", "gdsfactory 可用时应返回文件路径"
    assert (tmp_path / "real_mzi.gds").exists(), "GDS 文件应存在"


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_generate_ring_gds_real(tmp_path):
    """gdsfactory 可用时应生成真实 Ring GDS 文件。"""
    output = generate_ring_resonator_gds(
        str(tmp_path / "real_ring.gds"), radius_um=5.0, gap_nm=200.0
    )
    assert output != "", "gdsfactory 可用时应返回文件路径"
    assert (tmp_path / "real_ring.gds").exists(), "GDS 文件应存在"


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_list_available_components_has_straight():
    """gdsfactory 可用时应列出 straight 等核心器件。"""
    components = list_available_components()
    assert len(components) > 0, "gdsfactory 可用时应返回非空器件列表"
    # 核心器件应存在
    assert "straight" in components, "straight 器件应可用"


# ==================== 第2轮 P0-3: PDK 桥接测试 ====================


def test_list_gdsfactory_pdks_returns_list():
    """list_gdsfactory_pdks 应返回列表。

    gdsfactory 已安装但 PDK 未激活时，list_gdsfactory_pdks 仍应返回
    内置 PDK 列表（如 generic），因为 list_gdsfactory_pdks 检查的是
    import 成功而非 PDK 激活状态。
    """
    pdks = list_gdsfactory_pdks()
    assert isinstance(pdks, list)
    # 检查 gdsfactory 是否可 import（而非 PDK 是否激活）
    try:
        import gdsfactory  # noqa: F401

        has_gf = True
    except ImportError:
        has_gf = False
    if not has_gf:
        assert len(pdks) == 0
    else:
        # gdsfactory 已安装时至少有 generic
        assert "generic" in pdks
        assert len(pdks) > 0


def test_load_gdsfactory_pdk_unavailable_returns_empty():
    """gdsfactory 不可用时 load_gdsfactory_pdk 应返回空字典。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    devices = load_gdsfactory_pdk("generic")
    assert isinstance(devices, dict)
    assert len(devices) == 0


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_load_gdsfactory_pdk_generic():
    """gdsfactory 可用时应加载 generic PDK 器件。"""
    devices = load_gdsfactory_pdk("generic", max_components=5)
    assert isinstance(devices, dict)
    assert len(devices) > 0, "generic PDK 应有可用器件"
    # 验证 Device 结构
    for _name, device in devices.items():
        assert device.device_id.startswith("generic_")
        assert device.platform == "SOI"
        assert device.process_node == "220nm SOI"
        assert device.bbox.xmax >= device.bbox.xmin
        assert device.bbox.ymax >= device.bbox.ymin


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_gdsfactory_to_polaris_device_straight():
    """测试 gdsfactory Component → PoLaRIS Device 转换。"""
    import gdsfactory as gf

    gf.get_active_pdk()
    component = gf.components.straight(length=10.0, width=0.5)
    device = gdsfactory_to_polaris_device(
        component=component,
        device_id="test_straight",
        config=DeviceImportConfig(
            platform="SOI",
            category="passive",
            name="straight",
            process_node="220nm SOI",
        ),
    )
    assert device.device_id == "test_straight"
    assert device.platform == "SOI"
    assert device.name == "straight"
    assert device.process_node == "220nm SOI"
    # straight 器件应有端口
    assert len(device.ports) >= 2
    # 包围盒应有效
    assert device.bbox.xmax > device.bbox.xmin
    # 端口应有有效朝向
    for port in device.ports:
        assert port.direction in (
            Direction.NORTH,
            Direction.SOUTH,
            Direction.EAST,
            Direction.WEST,
        )


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_gdsfactory_to_polaris_device_ring():
    """测试 ring 器件转换（验证端口提取）。"""
    import gdsfactory as gf

    gf.get_active_pdk()
    component = gf.components.ring_single(radius=5.0, gap=0.2)
    device = gdsfactory_to_polaris_device(
        component=component,
        device_id="test_ring",
        config=DeviceImportConfig(platform="SOI", category="passive"),
    )
    assert device.device_id == "test_ring"
    assert len(device.ports) >= 2  # ring 至少有 2 个端口


@pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
def test_register_gdsfactory_pdk_to_catalog():
    """测试将 gdsfactory PDK 器件注册到 DeviceCatalog。"""
    from polaris.pdk.catalog import DeviceCatalog

    catalog = DeviceCatalog()
    count = register_gdsfactory_pdk(catalog, "generic", max_components=5)
    assert count > 0, "应至少注册一个器件"
    # 验证 catalog 中有 gdsfactory 器件
    all_devices = catalog.list_all()
    gf_devices = [d for d in all_devices if d.device_id.startswith("generic_")]
    assert len(gf_devices) == count


def test_register_gdsfactory_pdk_unavailable_returns_zero():
    """gdsfactory 不可用时 register_gdsfactory_pdk 应返回 0。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    from polaris.pdk.catalog import DeviceCatalog

    catalog = DeviceCatalog()
    count = register_gdsfactory_pdk(catalog, "generic")
    assert count == 0
