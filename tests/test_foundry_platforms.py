"""P0-3 PDK 覆盖扩展测试（第13轮，第20轮扩展 LNOI）。

验证 11 个公开 foundry 平台元数据的正确性与完整性。

来源: commercial_gap_analysis.md P0-3 PDK 覆盖
"""

from __future__ import annotations

import pytest

from polaris.pdk.foundry_platforms import (
    FOUNDRY_PLATFORMS,
    foundry_platform_count,
    get_foundry_platform,
    list_foundry_platforms,
    list_foundry_platforms_by_material,
)


class TestFoundryPlatformsRegistry:
    """Foundry 平台注册表测试。"""

    def test_platform_count(self):
        """验证至少 11 个 foundry 平台已注册。"""
        assert foundry_platform_count() >= 11

    def test_list_platforms(self):
        """list_foundry_platforms 返回所有平台名。"""
        platforms = list_foundry_platforms()
        assert len(platforms) == foundry_platform_count()
        # 验证关键平台存在
        for name in ["AIM", "AMF", "CompoundTek", "IHP", "GF_Fotonix", "LIGENTEC", "LioniX"]:
            assert name in platforms

    def test_get_platform_by_name(self):
        """get_foundry_platform 按名查询。"""
        aim = get_foundry_platform("AIM")
        assert aim.foundry == "AIM Photonics"
        assert aim.material_platform == "SOI"
        assert aim.wafer_size_mm == 300

    def test_get_platform_not_found(self):
        """查询不存在的平台应抛出 KeyError。"""
        with pytest.raises(KeyError, match="不在注册表中"):
            get_foundry_platform("NonExistent")


class TestFoundryPlatformData:
    """Foundry 平台数据完整性测试。"""

    @pytest.mark.parametrize("name", list(FOUNDRY_PLATFORMS.keys()))
    def test_platform_has_required_fields(self, name):
        """每个平台必须有必填字段。"""
        fp = FOUNDRY_PLATFORMS[name]
        assert fp.name == name
        assert fp.foundry
        assert fp.process_node
        assert fp.material_platform
        assert fp.waveguide_width_um > 0
        assert fp.min_bend_radius_um > 0
        assert fp.waveguide_loss_db_cm >= 0
        assert fp.wafer_size_mm > 0
        assert len(fp.sources) > 0, f"{name} 缺少来源 URL"

    @pytest.mark.parametrize("name", list(FOUNDRY_PLATFORMS.keys()))
    def test_platform_sources_are_urls(self, name):
        """每个平台的来源必须是有效 URL。"""
        fp = FOUNDRY_PLATFORMS[name]
        for url in fp.sources:
            assert url.startswith("http"), f"{name} 来源 {url} 不是有效 URL"

    def test_soi_platforms(self):
        """SOI 材料平台至少 5 个。"""
        soi = list_foundry_platforms_by_material("SOI")
        assert len(soi) >= 5
        for name in ["AIM", "AMF", "CompoundTek", "IHP", "GF_Fotonix"]:
            assert name in soi

    def test_sin_platforms(self):
        """SiN 材料平台至少 2 个。"""
        sin = list_foundry_platforms_by_material("SiN")
        assert len(sin) >= 2
        assert "LIGENTEC" in sin
        assert "LioniX" in sin

    def test_hybrid_platforms(self):
        """Hybrid 材料平台至少 2 个。"""
        hybrid = list_foundry_platforms_by_material("Hybrid")
        assert len(hybrid) >= 2
        assert "Tower_OpenLight" in hybrid
        assert "Tyndall" in hybrid


class TestFoundryPlatformSpecific:
    """特定平台参数验证（对照公开文献）。"""

    def test_aim_photonics_params(self):
        """AIM Photonics 参数对照公开文献。"""
        aim = get_foundry_platform("AIM")
        assert aim.waveguide_width_um == pytest.approx(0.45)
        assert aim.min_bend_radius_um == pytest.approx(5.0)
        assert aim.waveguide_loss_db_cm == pytest.approx(0.25)
        assert aim.wafer_size_mm == 300

    def test_gf_fotonix_params(self):
        """GF Fotonix 参数对照公开文献。"""
        gf = get_foundry_platform("GF_Fotonix")
        assert "45nm" in gf.process_node
        assert gf.wafer_size_mm == 300
        # GF 微环调制器可达 1.5μm 弯曲半径
        assert gf.min_bend_radius_um == pytest.approx(1.5)

    def test_ihp_sg25h5_params(self):
        """IHP SG25H5 参数对照公开文献。"""
        ihp = get_foundry_platform("IHP")
        assert "0.25μm" in ihp.process_node
        assert "BiCMOS" in ihp.process_node
        assert ihp.wafer_size_mm == 200

    def test_ligentec_sin_params(self):
        """LIGENTEC SiN 参数对照公开文献。"""
        lig = get_foundry_platform("LIGENTEC")
        assert lig.material_platform == "SiN"
        assert lig.waveguide_loss_db_cm == pytest.approx(0.1)
        assert lig.waveguide_width_um == pytest.approx(0.8)

    def test_vtt_thick_soi_params(self):
        """VTT 厚膜 SOI 参数对照公开文献。"""
        vtt = get_foundry_platform("VTT")
        assert vtt.material_platform == "ThickSOI"
        assert vtt.min_bend_radius_um == pytest.approx(1.3)
        assert vtt.waveguide_width_um == pytest.approx(3.0)

    def test_compoundtek_90nm_node(self):
        """CompoundTek 90nm 工艺节点。"""
        ct = get_foundry_platform("CompoundTek")
        assert "90nm" in ct.process_node
        assert ct.waveguide_loss_db_cm == pytest.approx(0.43)


class TestFoundryPlatformIntegration:
    """Foundry 平台与 PoLaRIS 集成测试。"""

    def test_total_platform_coverage(self):
        """PDK 覆盖：4 内置 + 11 foundry = 15 平台。"""
        from polaris.pdk.catalog import _PLATFORM_DEFAULT_PROCESS_NODE

        builtin_count = len(_PLATFORM_DEFAULT_PROCESS_NODE)
        foundry_count = foundry_platform_count()
        total = builtin_count + foundry_count
        # 对齐 Luceda IPKISS 15+ PDK 目标
        assert total >= 15, f"总平台数 {total} < 15（目标对齐 IPKISS 15+）"
        print(f"\nPDK 覆盖: {builtin_count} 内置 + {foundry_count} foundry = {total} 平台")

    def test_foundry_platforms_immutable(self):
        """FoundryPlatform 是 frozen dataclass，不可变。"""
        aim = get_foundry_platform("AIM")
        with pytest.raises(AttributeError):
            aim.foundry = "Modified"  # type: ignore[misc]

    def test_material_platform_categories(self):
        """材料平台分类覆盖所有类别。"""
        all_materials = {fp.material_platform for fp in FOUNDRY_PLATFORMS.values()}
        # 应包含 SOI/SiN/Hybrid/ThickSOI/LNOI 等
        assert "SOI" in all_materials
        assert "SiN" in all_materials
        assert "Hybrid" in all_materials
        assert "LNOI" in all_materials

    def test_hyperlight_lnoi_platform(self):
        """HyperLight LNOI 平台元数据完整性（第20轮新增）。"""
        hl = get_foundry_platform("HyperLight")
        assert hl.foundry == "HyperLight Corporation"
        assert hl.material_platform == "LNOI"
        assert hl.wafer_size_mm == 100
        assert hl.waveguide_width_um == 0.8
        assert len(hl.sources) >= 2
