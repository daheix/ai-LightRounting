"""SiEPIC 真实器件名映射测试（步骤2：对齐 ubcpdk 真实参数）。

验证 SiEPIC EBeam PDK 真实器件名（如 ``ebeam_y_1550``）与 PoLaRIS
器件名（如 ``y_branch``）的双向映射正确性。

来源:
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 真实版图验证: data/benchmarks/siepic_examples/RingResonator.gds
"""

from __future__ import annotations

from polaris.pdk.siepic_mapping import (
    POLARIS_TO_SIEPIC,
    SIEPIC_TO_POLARIS,
    polaris_to_siepic,
    siepic_to_polaris,
)


def test_siepic_to_polaris_y_branch():
    """ebeam_y_1550 应映射到 y_branch。"""
    assert siepic_to_polaris("ebeam_y_1550") == "y_branch"
    assert siepic_to_polaris("ebeam_y_te1550") == "y_branch"


def test_siepic_to_polaris_grating_coupler():
    """ebeam_gc_te1550 应映射到 grating_coupler_1d。"""
    assert siepic_to_polaris("ebeam_gc_te1550") == "grating_coupler_1d"
    assert siepic_to_polaris("gc_te1550") == "grating_coupler_1d"


def test_siepic_to_polaris_ring_resonator():
    """ebeam_dc_halfring_te1550 应映射到 ring_resonator。

    真实版图验证（RingResonator.gds）：使用 ebeam_dc_halfring_straight。
    """
    assert siepic_to_polaris("ebeam_dc_halfring_te1550") == "ring_resonator"
    assert siepic_to_polaris("ebeam_dc_halfring_straight") == "ring_resonator"


def test_siepic_to_polaris_unknown_returns_none():
    """未知 SiEPIC 器件名应返回 None。"""
    assert siepic_to_polaris("unknown_device") is None
    assert siepic_to_polaris("") is None


def test_polaris_to_siepic_y_branch():
    """y_branch 应映射到 ebeam_y_1550。"""
    assert polaris_to_siepic("y_branch") == "ebeam_y_1550"


def test_polaris_to_siepic_grating_coupler():
    """grating_coupler_1d 应映射到 ebeam_gc_te1550。"""
    assert polaris_to_siepic("grating_coupler_1d") == "ebeam_gc_te1550"


def test_polaris_to_siepic_unknown_returns_none():
    """未知 PoLaRIS 器件名应返回 None。"""
    assert polaris_to_siepic("unknown_device") is None


def test_mapping_is_consistent():
    """双向映射应一致：SIEPIC_TO_POLARIS 与 POLARIS_TO_SIEPIC 互逆。"""
    for siepic_name, polaris_name in SIEPIC_TO_POLARIS.items():
        # 每个 SiEPIC 名都应能映射回 PoLaRIS 名
        assert siepic_to_polaris(siepic_name) == polaris_name
    for polaris_name, siepic_name in POLARIS_TO_SIEPIC.items():
        # 每个 PoLaRIS 名都应能映射回 SiEPIC 名
        assert polaris_to_siepic(polaris_name) == siepic_name


def test_mapping_covers_core_siepic_devices():
    """映射应覆盖 SiEPIC EBeam PDK 的核心器件（至少 10 个）。"""
    # SiEPIC EBeam PDK 核心器件（从 RingResonator.gds/Simple_MZI.gds 提取）
    core_devices = [
        "ebeam_y_1550",
        "ebeam_gc_te1550",
        "ebeam_dc_te1550",
        "ebeam_dc_halfring_te1550",
        "ebeam_mmi_1x2_te_1550",
        "ebeam_mmi_2x2_te_1550",
        "ebeam_terminator_te1550",
        "ebeam_crossing_te1550",
        "ebeam_taper_te1550",
        "ebeam_wg_strip_1550",
    ]
    for device in core_devices:
        assert siepic_to_polaris(device) is not None, (
            f"核心 SiEPIC 器件 {device} 未在映射表中"
        )
