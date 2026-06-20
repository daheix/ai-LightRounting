"""gdsfactory 集成模块测试（步骤4：生成真实参数化器件 GDS）。

验证 gdsfactory 集成模块的接口正确性。gdsfactory import 失败时
（规则 5.3）测试用 ``pytest.importorskip`` 跳过真实生成测试，
但降级行为测试始终运行。

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import pytest

from polaris.pdk.gdsfactory_integration import (
    generate_component_gds,
    generate_mzi_gds,
    generate_ring_resonator_gds,
    is_available,
    list_available_components,
)


def test_is_available_returns_bool():
    """is_available() 应返回 bool。"""
    result = is_available()
    assert isinstance(result, bool)


def test_generate_mzi_gds_unavailable_returns_empty(tmp_path):
    """gdsfactory 不可用时 generate_mzi_gds 应返回空字符串。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    result = generate_mzi_gds(str(tmp_path / "mzi.gds"))
    assert result == "", "gdsfactory 不可用时应返回空字符串"


def test_generate_ring_gds_unavailable_returns_empty(tmp_path):
    """gdsfactory 不可用时 generate_ring_resonator_gds 应返回空字符串。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    result = generate_ring_resonator_gds(str(tmp_path / "ring.gds"))
    assert result == "", "gdsfactory 不可用时应返回空字符串"


def test_generate_component_gds_unavailable_returns_empty(tmp_path):
    """gdsfactory 不可用时 generate_component_gds 应返回空字符串。"""
    if is_available():
        pytest.skip("gdsfactory 已安装，跳过降级测试")
    result = generate_component_gds("straight", str(tmp_path / "wg.gds"))
    assert result == "", "gdsfactory 不可用时应返回空字符串"


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
