"""R311 PDK YAML 默认模板生成器测试。

覆盖:
- list_supported_platforms 返回 4 个平台
- get_default_pdk_config 各平台配置完整性
- generate_default_pdk_yaml 生成的 YAML 可被 parse_pdk_yaml 解析
- save_default_pdk_yaml 文件保存往返
- R03 错误处理（未知平台 raise ValueError）
- R02 学术诚信（所有平台包含 source_url + 折射率溯源）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec AN800: https://www.ligentec.com/
- SMART Photonics: https://smartphotonics.nl/
- LuminousIC: https://www.luminousic.com/
- Palik, "Handbook of Optical Constants", 1997
- Luke et al., Optics Express 27(22), 2019, DOI:10.1364/OE.27.031276
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.pdk_yaml_templates import (
    generate_default_pdk_yaml,
    get_default_pdk_config,
    list_supported_platforms,
    save_default_pdk_yaml,
)
from polaris.pdk.yaml_pdk_config import (
    PDKYamlConfig,
    build_polaris_pdk_from_yaml,
    parse_pdk_yaml,
    validate_pdk_yaml,
)


# =============================================================================
# TestListSupportedPlatforms: 平台列表
# =============================================================================
class TestListSupportedPlatforms:
    """list_supported_platforms 测试。"""

    def test_returns_4_platforms(self) -> None:
        platforms = list_supported_platforms()
        assert len(platforms) == 4

    def test_contains_all_standard_platforms(self) -> None:
        platforms = list_supported_platforms()
        assert "SOI" in platforms
        assert "SiN" in platforms
        assert "InP" in platforms
        assert "LNOI" in platforms

    def test_sorted_alphabetically(self) -> None:
        platforms = list_supported_platforms()
        assert platforms == sorted(platforms)


# =============================================================================
# TestGetDefaultPdkConfig: 默认配置
# =============================================================================
class TestGetDefaultPdkConfig:
    """get_default_pdk_config 各平台配置测试。"""

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_config_has_required_fields(self, platform: str) -> None:
        cfg = get_default_pdk_config(platform)
        assert isinstance(cfg, PDKYamlConfig)
        assert cfg.name
        assert cfg.version
        assert cfg.platform == platform
        assert cfg.process_node
        assert cfg.description
        assert cfg.source_url  # R02 强制

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_config_has_layers(self, platform: str) -> None:
        cfg = get_default_pdk_config(platform)
        assert len(cfg.layers) >= 5  # 至少核心层 + 通用层

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_config_has_layer_stack(self, platform: str) -> None:
        cfg = get_default_pdk_config(platform)
        assert len(cfg.layer_stack) >= 2  # 核心层 + 金属层

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_config_has_cross_sections(self, platform: str) -> None:
        cfg = get_default_pdk_config(platform)
        assert len(cfg.cross_sections) >= 1  # 至少 strip
        assert "strip" in [xs.name for xs in cfg.cross_sections]

    def test_soi_specific_layers(self) -> None:
        """SOI 应包含 SLAB150 层（rib 波导）。"""
        cfg = get_default_pdk_config("SOI")
        layer_names = [l.name for l in cfg.layers]
        assert "WG" in layer_names
        assert "SLAB150" in layer_names

    def test_soi_specific_cross_sections(self) -> None:
        """SOI 应包含 rib 截面。"""
        cfg = get_default_pdk_config("SOI")
        xs_names = [xs.name for xs in cfg.cross_sections]
        assert "strip" in xs_names
        assert "rib" in xs_names

    def test_sin_no_slab(self) -> None:
        """SiN 平台不应包含 SLAB150。"""
        cfg = get_default_pdk_config("SiN")
        layer_names = [l.name for l in cfg.layers]
        assert "SLAB150" not in layer_names

    def test_soi_refractive_index(self) -> None:
        """SOI Si 折射率 3.476。"""
        cfg = get_default_pdk_config("SOI")
        wg_level = next(l for l in cfg.layer_stack if l.layer == "WG")
        assert wg_level.refractive_index_real == 3.476

    def test_sin_refractive_index(self) -> None:
        """SiN 折射率 2.0。"""
        cfg = get_default_pdk_config("SiN")
        sin_level = next(l for l in cfg.layer_stack if l.layer == "SiN")
        assert sin_level.refractive_index_real == 2.0

    def test_inp_refractive_index(self) -> None:
        """InP InGaAsP 折射率 3.17。"""
        cfg = get_default_pdk_config("InP")
        wg_level = next(l for l in cfg.layer_stack if l.layer == "WG")
        assert wg_level.refractive_index_real == 3.17

    def test_lnoi_refractive_index(self) -> None:
        """LNOI LiNbO3 寻常光折射率 2.211。"""
        cfg = get_default_pdk_config("LNOI")
        wg_level = next(l for l in cfg.layer_stack if l.layer == "WG")
        assert wg_level.refractive_index_real == 2.211


# =============================================================================
# TestGenerateDefaultPdkYaml: YAML 生成
# =============================================================================
class TestGenerateDefaultPdkYaml:
    """generate_default_pdk_yaml 测试。"""

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_generates_valid_yaml(self, platform: str, tmp_path: Path) -> None:
        """生成的 YAML 应可被 parse_pdk_yaml 解析。"""
        yaml_str = generate_default_pdk_yaml(platform)
        out = tmp_path / f"{platform.lower()}.yaml"
        out.write_text(yaml_str, encoding="utf-8")
        cfg = parse_pdk_yaml(out)
        assert cfg.platform == platform

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_yaml_passes_validation(self, platform: str) -> None:
        """生成的 YAML 应通过 validate_pdk_yaml。"""
        cfg = get_default_pdk_config(platform)
        errors = validate_pdk_yaml(cfg)
        assert errors == [], f"平台 {platform} 默认配置校验失败: {errors}"

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_yaml_builds_polaris_pdk(self, platform: str, tmp_path: Path) -> None:
        """生成的 YAML 应可被 build_polaris_pdk_from_yaml 构建为 PolarisPDK。"""
        yaml_str = generate_default_pdk_yaml(platform)
        out = tmp_path / f"{platform.lower()}_build.yaml"
        out.write_text(yaml_str, encoding="utf-8")
        pdk = build_polaris_pdk_from_yaml(out)
        assert pdk.platform == platform
        assert pdk.layer_stack is not None
        assert "strip" in pdk.cross_sections


# =============================================================================
# TestSaveDefaultPdkYaml: 文件保存
# =============================================================================
class TestSaveDefaultPdkYaml:
    """save_default_pdk_yaml 测试。"""

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_save_creates_file(self, platform: str, tmp_path: Path) -> None:
        out = save_default_pdk_yaml(platform, tmp_path / f"{platform}.yaml")
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_saved_file_round_trips(self, platform: str, tmp_path: Path) -> None:
        """保存的文件可被重新解析。"""
        out = save_default_pdk_yaml(platform, tmp_path / f"{platform}_rt.yaml")
        cfg = parse_pdk_yaml(out)
        assert cfg.platform == platform
        assert cfg.name

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """保存路径的父目录不存在时应自动创建。"""
        nested = tmp_path / "a" / "b" / "c" / "soi.yaml"
        out = save_default_pdk_yaml("SOI", nested)
        assert out.exists()


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试。"""

    def test_unknown_platform_get_config_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持的平台"):
            get_default_pdk_config("UNKNOWN")

    def test_unknown_platform_generate_yaml_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持的平台"):
            generate_default_pdk_yaml("UNKNOWN")

    def test_unknown_platform_save_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="不支持的平台"):
            save_default_pdk_yaml("UNKNOWN", tmp_path / "bad.yaml")

    def test_empty_platform_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持的平台"):
            get_default_pdk_config("")


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信测试。"""

    @pytest.mark.parametrize("platform", ["SOI", "SiN", "InP", "LNOI"])
    def test_all_platforms_have_source_url(self, platform: str) -> None:
        cfg = get_default_pdk_config(platform)
        assert cfg.source_url, f"平台 {platform} 缺少 source_url"

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 包含 ≥5 个文献 URL。"""
        from polaris.pdk import pdk_yaml_templates
        doc = pdk_yaml_templates.__doc__ or ""
        urls = [line for line in doc.split() if line.startswith("http")]
        assert len(urls) >= 5

    @pytest.mark.parametrize("platform,expected_url", [
        ("SOI", "SiEPIC"),
        ("SiN", "ligentec"),
        ("InP", "smartphotonics"),
        ("LNOI", "luminousic"),
    ])
    def test_platform_source_url_matches_vendor(self, platform: str, expected_url: str) -> None:
        """每个平台的 source_url 应指向对应厂商。"""
        cfg = get_default_pdk_config(platform)
        assert expected_url.lower() in cfg.source_url.lower()

    def test_refractive_index_documented(self) -> None:
        """折射率参数在模块 docstring 中有溯源。"""
        from polaris.pdk import pdk_yaml_templates
        doc = pdk_yaml_templates.__doc__ or ""
        # 应包含 refractiveindex.info 链接
        assert "refractiveindex.info" in doc


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_all_platforms_full_workflow(self, tmp_path: Path) -> None:
        """所有平台的完整工作流: 生成 → 保存 → 解析 → 构建。"""
        for platform in list_supported_platforms():
            # 生成
            yaml_str = generate_default_pdk_yaml(platform)
            # 保存
            out = tmp_path / f"{platform.lower()}_full.yaml"
            out.write_text(yaml_str, encoding="utf-8")
            # 解析
            cfg = parse_pdk_yaml(out)
            assert cfg.platform == platform
            # 校验
            errors = validate_pdk_yaml(cfg)
            assert errors == [], f"平台 {platform} 校验失败: {errors}"
            # 构建
            pdk = build_polaris_pdk_from_yaml(out)
            assert pdk.platform == platform
            assert pdk.layer_stack is not None
            assert "strip" in pdk.cross_sections

    def test_soi_pdk_can_register_cells(self, tmp_path: Path) -> None:
        """SOI 默认 PDK 应可加载后注册 cell。"""
        from polaris.pdk import PolarisCellRegistry, register_polaris_cell
        from polaris.pdk.pcell import PCellMultiView

        # 生成 SOI 默认配置
        out = save_default_pdk_yaml("SOI", tmp_path / "soi_for_cells.yaml")
        cfg = parse_pdk_yaml(out)

        # 注册一个 cell
        registry = PolarisCellRegistry()

        @register_polaris_cell(registry=registry, name="mzi", platform="SOI")
        def mzi(length: float = 100.0) -> PCellMultiView:
            return PCellMultiView(name="mzi", params={"length": length})

        assert registry.size == 1
        assert "mzi" in registry.list_names()
