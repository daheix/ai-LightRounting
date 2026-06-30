"""R303 PDK 双向兼容层映射回归测试。

覆盖 R303 三个测试需求（TR-303.1/2/3）：
- TR-303.1: SiEPIC PDK 层映射正确
- TR-303.2: 自定义层映射支持
- TR-303.3: 映射配置文件化（YAML）

学术依据:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
- YAML 1.2 规范: https://yaml.org/spec/1.2.2/
- gdsfactory YAML 层映射: https://gdsfactory.github.io/gdsfactory/

R03 验证: 错误输入必须 raise，禁止 fall-back。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.pdk.gdsfactory_integration import (
    LayerMapConfig,
    build_layer_map_config,
    gdsfactory_to_polaris_layer,
    get_gdsfactory_generic_layer_map,
    get_siepic_layer_map,
    load_layer_map_from_yaml,
    merge_layer_maps,
    polaris_to_gdsfactory_layer,
    save_layer_map_to_yaml,
)


# ============================================================================
# TR-303.1: SiEPIC PDK 层映射正确
# ============================================================================


class TestTR3031SiEPICLayerMap:
    """TR-303.1: SiEPIC PDK 层映射正确。"""

    def test_siepic_layer_map_size(self):
        """SiEPIC 层映射含 13 个标准层。"""
        layer_map = get_siepic_layer_map()
        assert len(layer_map) == 13

    def test_siepic_wg_layer(self):
        """(1,0) → WG（波导核心层）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(1, 0)] == "WG"

    def test_siepic_slab150_layer(self):
        """(2,0) → SLAB150（150nm slab）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(2, 0)] == "SLAB150"

    def test_siepic_slab90_layer(self):
        """(3,0) → SLAB90（90nm slab）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(3, 0)] == "SLAB90"

    def test_siepic_devrec_layer(self):
        """(68,0) → DEVREC（器件识别层）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(68, 0)] == "DEVREC"

    def test_siepic_pin_layer(self):
        """(69,0) → PIN（端口标记层）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(69, 0)] == "PIN"

    def test_siepic_text_layer(self):
        """(10,0) → TEXT（文本标注层）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(10, 0)] == "TEXT"

    def test_siepic_floorplan_layer(self):
        """(80,0) → FLOORPLAN（平面规划层）。"""
        layer_map = get_siepic_layer_map()
        assert layer_map[(80, 0)] == "FLOORPLAN"

    def test_siepic_layer_map_returns_copy(self):
        """返回的是拷贝，修改不影响内部状态。"""
        map1 = get_siepic_layer_map()
        map1[(999, 0)] = "HACKED"
        map2 = get_siepic_layer_map()
        assert (999, 0) not in map2

    def test_gdsfactory_generic_layer_map(self):
        """gdsfactory generic PDK 层映射含 7 层。"""
        layer_map = get_gdsfactory_generic_layer_map()
        assert len(layer_map) == 7
        assert layer_map[(1, 0)] == "WG"
        assert layer_map[(68, 0)] == "DEVREC"

    def test_gdsfactory_to_polaris_layer_default(self):
        """GDSII→PoLaRIS: 用 SiEPIC 默认映射。"""
        assert gdsfactory_to_polaris_layer(1, 0) == "WG"
        assert gdsfactory_to_polaris_layer(68, 0) == "DEVREC"

    def test_gdsfactory_to_polaris_layer_unknown(self):
        """GDSII→PoLaRIS: 未知层返回默认名。"""
        name = gdsfactory_to_polaris_layer(200, 5)
        assert name == "LAYER_200_5"

    def test_polaris_to_gdsfactory_layer_default(self):
        """PoLaRIS→GDSII: 用 SiEPIC 默认映射。"""
        assert polaris_to_gdsfactory_layer("WG") == (1, 0)
        assert polaris_to_gdsfactory_layer("DEVREC") == (68, 0)

    def test_polaris_to_gdsfactory_layer_round_trip(self):
        """PoLaRIS→GDSII→PoLaRIS 往返一致。"""
        layer_map = get_siepic_layer_map()
        for (gds_layer, gds_datatype), name in layer_map.items():
            rt_name = gdsfactory_to_polaris_layer(gds_layer, gds_datatype)
            assert rt_name == name, f"往返不一致: {name}"


# ============================================================================
# TR-303.2: 自定义层映射支持
# ============================================================================


class TestTR3032CustomLayerMap:
    """TR-303.2: 自定义层映射支持。"""

    def test_merge_layer_maps_basic(self):
        """基础合并：custom 覆盖 base。"""
        base = {(1, 0): "WG", (68, 0): "DEVREC"}
        custom = {(1, 0): "MY_WG"}
        merged = merge_layer_maps(base, custom)
        assert merged[(1, 0)] == "MY_WG"
        assert merged[(68, 0)] == "DEVREC"

    def test_merge_layer_maps_add_new(self):
        """合并新增层。"""
        base = {(1, 0): "WG"}
        custom = {(200, 0): "NEW_LAYER"}
        merged = merge_layer_maps(base, custom)
        assert merged[(1, 0)] == "WG"
        assert merged[(200, 0)] == "NEW_LAYER"

    def test_merge_layer_maps_no_modify_input(self):
        """合并不修改输入。"""
        base = {(1, 0): "WG"}
        custom = {(2, 0): "SLAB"}
        merge_layer_maps(base, custom)
        assert base == {(1, 0): "WG"}
        assert custom == {(2, 0): "SLAB"}

    def test_merge_layer_maps_with_siepic(self):
        """与 SiEPIC 默认合并。"""
        siepic = get_siepic_layer_map()
        custom = {(1, 0): "MY_WG", (200, 0): "NEW"}
        merged = merge_layer_maps(siepic, custom)
        assert merged[(1, 0)] == "MY_WG"  # custom 覆盖
        assert merged[(68, 0)] == "DEVREC"  # base 保留
        assert merged[(200, 0)] == "NEW"  # 新增

    def test_gdsfactory_to_polaris_with_custom_map(self):
        """GDSII→PoLaRIS 用自定义映射。"""
        custom = {(1, 0): "MY_WG", (200, 0): "NEW"}
        assert gdsfactory_to_polaris_layer(1, 0, custom) == "MY_WG"
        assert gdsfactory_to_polaris_layer(200, 0, custom) == "NEW"

    def test_polaris_to_gdsfactory_with_custom_map(self):
        """PoLaRIS→GDSII 用自定义映射。"""
        custom = {(1, 0): "MY_WG", (200, 0): "NEW"}
        assert polaris_to_gdsfactory_layer("MY_WG", custom) == (1, 0)
        assert polaris_to_gdsfactory_layer("NEW", custom) == (200, 0)


# ============================================================================
# TR-303.3: 映射配置文件化（YAML）
# ============================================================================


class TestTR3033YAMLConfig:
    """TR-303.3: 映射配置文件化（YAML）。"""

    def test_save_yaml_basic(self, tmp_path):
        """保存 YAML 文件。"""
        layer_map = {(1, 0): "WG", (68, 0): "DEVREC"}
        yaml_path = tmp_path / "layers.yaml"
        result = save_layer_map_to_yaml(layer_map, yaml_path)
        assert Path(result).exists()
        assert Path(result).is_file()

    def test_load_yaml_basic(self, tmp_path):
        """加载 YAML 文件。"""
        layer_map = {(1, 0): "WG", (68, 0): "DEVREC"}
        yaml_path = tmp_path / "layers.yaml"
        save_layer_map_to_yaml(layer_map, yaml_path)
        loaded = load_layer_map_from_yaml(yaml_path)
        assert loaded == layer_map

    def test_yaml_round_trip(self, tmp_path):
        """YAML 往返一致性。"""
        siepic = get_siepic_layer_map()
        yaml_path = tmp_path / "siepic.yaml"
        save_layer_map_to_yaml(siepic, yaml_path)
        loaded = load_layer_map_from_yaml(yaml_path)
        assert loaded == siepic

    def test_yaml_create_parent_dir(self, tmp_path):
        """YAML 自动创建父目录。"""
        layer_map = {(1, 0): "WG"}
        yaml_path = tmp_path / "subdir" / "layers.yaml"
        save_layer_map_to_yaml(layer_map, yaml_path)
        assert yaml_path.exists()

    def test_yaml_returns_path_string(self, tmp_path):
        """YAML 保存返回路径字符串。"""
        layer_map = {(1, 0): "WG"}
        yaml_path = tmp_path / "layers.yaml"
        result = save_layer_map_to_yaml(layer_map, yaml_path)
        assert isinstance(result, str)
        assert result == str(yaml_path)

    def test_yaml_load_with_gdsfactory_map(self, tmp_path):
        """YAML 保存 gdsfactory generic PDK 后加载。"""
        gf_map = get_gdsfactory_generic_layer_map()
        yaml_path = tmp_path / "gdsfactory.yaml"
        save_layer_map_to_yaml(gf_map, yaml_path)
        loaded = load_layer_map_from_yaml(yaml_path)
        assert loaded == gf_map


# ============================================================================
# R03: 错误输入处理（禁止 fall-back）
# ============================================================================


class TestR03ErrorHandling:
    """R03: 错误输入必须 raise，禁止 fall-back。"""

    def test_polaris_to_gdsfactory_unknown_raises(self):
        """未知层名 raise ValueError（不返回默认值兜底）。"""
        with pytest.raises(ValueError, match="不存在"):
            polaris_to_gdsfactory_layer("NONEXISTENT_LAYER")

    def test_merge_layer_maps_invalid_base_type_raises(self):
        """base 不是 dict raise TypeError。"""
        with pytest.raises(TypeError, match="base 必须是 dict"):
            merge_layer_maps("not a dict", {(1, 0): "WG"})  # type: ignore

    def test_merge_layer_maps_invalid_custom_type_raises(self):
        """custom 不是 dict raise TypeError。"""
        with pytest.raises(TypeError, match="custom 必须是 dict"):
            merge_layer_maps({(1, 0): "WG"}, "not a dict")  # type: ignore

    def test_merge_layer_maps_empty_name_raises(self):
        """custom 含空层名 raise ValueError。"""
        with pytest.raises(ValueError, match="空字符串"):
            merge_layer_maps({(1, 0): "WG"}, {(2, 0): ""})

    def test_merge_layer_maps_whitespace_name_raises(self):
        """custom 含纯空白层名 raise ValueError。"""
        with pytest.raises(ValueError, match="空字符串"):
            merge_layer_maps({(1, 0): "WG"}, {(2, 0): "   "})

    def test_save_yaml_empty_map_raises(self, tmp_path):
        """保存空层映射 raise ValueError。"""
        with pytest.raises(ValueError, match="为空"):
            save_layer_map_to_yaml({}, tmp_path / "empty.yaml")

    def test_load_yaml_nonexistent_raises(self, tmp_path):
        """加载不存在的 YAML raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            load_layer_map_from_yaml(tmp_path / "nonexistent.yaml")

    def test_load_yaml_directory_raises(self, tmp_path):
        """加载目录路径 raise ValueError。"""
        with pytest.raises(ValueError, match="不是文件"):
            load_layer_map_from_yaml(tmp_path)

    def test_load_yaml_invalid_format_raises(self, tmp_path):
        """加载非 dict YAML raise ValueError。"""
        yaml_path = tmp_path / "invalid.yaml"
        yaml_path.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="必须是 dict"):
            load_layer_map_from_yaml(yaml_path)

    def test_load_yaml_empty_dict_raises(self, tmp_path):
        """加载空 dict YAML raise ValueError。"""
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("{}\n")
        with pytest.raises(ValueError, match="为空"):
            load_layer_map_from_yaml(yaml_path)

    def test_load_yaml_invalid_value_format_raises(self, tmp_path):
        """加载值不是 [layer, datatype] 的 YAML raise ValueError。"""
        yaml_path = tmp_path / "invalid_value.yaml"
        yaml_path.write_text("WG: not_a_list\n")
        with pytest.raises(ValueError, match="必须是"):
            load_layer_map_from_yaml(yaml_path)

    def test_load_yaml_non_int_value_raises(self, tmp_path):
        """加载值不是整数的 YAML raise ValueError。"""
        yaml_path = tmp_path / "non_int.yaml"
        yaml_path.write_text("WG: [abc, def]\n")
        with pytest.raises(ValueError, match="不是有效整数"):
            load_layer_map_from_yaml(yaml_path)

    def test_build_layer_map_config_invalid_base_raises(self):
        """build_layer_map_config 无效 base raise ValueError。"""
        with pytest.raises(ValueError, match="无效"):
            build_layer_map_config(base="invalid_base")


# ============================================================================
# LayerMapConfig 数据类测试
# ============================================================================


class TestLayerMapConfig:
    """LayerMapConfig 数据类测试。"""

    def test_layer_map_config_defaults(self):
        """LayerMapConfig 默认值。"""
        cfg = LayerMapConfig(layer_map={(1, 0): "WG"})
        assert cfg.source == "custom"
        assert cfg.merged_with_default is False

    def test_layer_map_config_custom_source(self):
        """LayerMapConfig 自定义 source。"""
        cfg = LayerMapConfig(layer_map={(1, 0): "WG"}, source="siepic")
        assert cfg.source == "siepic"

    def test_build_layer_map_config_siepic_default(self):
        """build 用 SiEPIC 默认（无 custom）。"""
        cfg = build_layer_map_config(base="siepic")
        assert cfg.source == "siepic"
        assert cfg.merged_with_default is False
        assert cfg.layer_map[(1, 0)] == "WG"

    def test_build_layer_map_config_gdsfactory_default(self):
        """build 用 gdsfactory 默认。"""
        cfg = build_layer_map_config(base="gdsfactory")
        assert cfg.source == "gdsfactory"
        assert cfg.merged_with_default is False
        assert cfg.layer_map[(1, 0)] == "WG"

    def test_build_layer_map_config_merge_siepic(self):
        """build 合并 SiEPIC + custom。"""
        custom = {(1, 0): "MY_WG"}
        cfg = build_layer_map_config(
            custom_map=custom, base="siepic", merge_base=True
        )
        assert cfg.source == "siepic+custom"
        assert cfg.merged_with_default is True
        assert cfg.layer_map[(1, 0)] == "MY_WG"
        assert cfg.layer_map[(68, 0)] == "DEVREC"

    def test_build_layer_map_config_no_merge(self):
        """build 不合并（仅用 custom）。"""
        custom = {(1, 0): "MY_WG"}
        cfg = build_layer_map_config(
            custom_map=custom, base="siepic", merge_base=False
        )
        assert cfg.source == "custom"
        assert cfg.merged_with_default is False
        assert cfg.layer_map == custom


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """R303 集成测试。"""

    def test_layer_map_importable_from_pdk_package(self):
        """层映射函数可从 polaris.pdk 顶层导入。"""
        from polaris.pdk import (
            build_layer_map_config,
            get_siepic_layer_map,
            gdsfactory_to_polaris_layer,
            polaris_to_gdsfactory_layer,
        )

        assert callable(get_siepic_layer_map)
        assert callable(gdsfactory_to_polaris_layer)
        assert callable(polaris_to_gdsfactory_layer)
        assert callable(build_layer_map_config)

    def test_full_workflow_custom_to_yaml_to_load(self, tmp_path):
        """完整工作流: 自定义映射 → YAML → 加载 → 使用。"""
        # 1. 构建自定义映射
        custom = {(1, 0): "MY_WG", (200, 0): "SPECIAL"}
        cfg = build_layer_map_config(
            custom_map=custom, base="siepic", merge_base=True
        )
        # 2. 保存到 YAML
        yaml_path = tmp_path / "workflow.yaml"
        save_layer_map_to_yaml(cfg.layer_map, yaml_path)
        # 3. 加载
        loaded = load_layer_map_from_yaml(yaml_path)
        # 4. 使用
        assert gdsfactory_to_polaris_layer(1, 0, loaded) == "MY_WG"
        assert gdsfactory_to_polaris_layer(200, 0, loaded) == "SPECIAL"
        assert polaris_to_gdsfactory_layer("DEVREC", loaded) == (68, 0)

    def test_bidirectional_mapping_consistency(self):
        """双向映射一致性: GDS→PoLaRIS→GDS 往返一致。"""
        siepic = get_siepic_layer_map()
        for (gds_layer, gds_datatype), expected_name in siepic.items():
            # GDS → PoLaRIS
            polaris_name = gdsfactory_to_polaris_layer(
                gds_layer, gds_datatype, siepic
            )
            assert polaris_name == expected_name
            # PoLaRIS → GDS
            rt_gds = polaris_to_gdsfactory_layer(polaris_name, siepic)
            assert rt_gds == (gds_layer, gds_datatype)


# ============================================================================
# 学术诚信: SiEPIC 层映射溯源
# ============================================================================


class TestAcademicIntegrity:
    """验证 R303 使用的 SiEPIC 层映射有据可查。"""

    def test_siepic_layer_count_matches_pdk(self):
        """SiEPIC 层映射含 13 层（与 SiEPIC EBeam PDK 一致）。

        来源: SiEPIC EBeam PDK
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        layer_map = get_siepic_layer_map()
        assert len(layer_map) == 13

    def test_siepic_wg_layer_is_layer_1(self):
        """SiEPIC WG 层是 (1, 0)。

        来源: SiEPIC EBeam PDK
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        layer_map = get_siepic_layer_map()
        assert layer_map[(1, 0)] == "WG"

    def test_siepic_devrec_layer_is_68(self):
        """SiEPIC DEVREC 层是 (68, 0)。

        来源: SiEPIC EBeam PDK
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        layer_map = get_siepic_layer_map()
        assert layer_map[(68, 0)] == "DEVREC"

    def test_siepic_pin_layer_is_69(self):
        """SiEPIC PIN 层是 (69, 0)。

        来源: SiEPIC EBeam PDK
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        layer_map = get_siepic_layer_map()
        assert layer_map[(69, 0)] == "PIN"

    def test_gdsfactory_generic_layer_count(self):
        """gdsfactory generic PDK 含 7 层。

        来源: gdsfactory generic PDK layer definitions
        https://gdsfactory.github.io/gdsfactory/
        """
        layer_map = get_gdsfactory_generic_layer_map()
        assert len(layer_map) == 7
