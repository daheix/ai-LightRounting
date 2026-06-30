"""R309 YAML PDK 配置系统测试。

覆盖:
- 数据类字段与默认值
- parse_pdk_yaml 解析（正常/异常路径）
- serialize_pdk_yaml 序列化
- validate_pdk_yaml 校验
- build_polaris_layer_stack / build_polaris_cross_section
- build_polaris_pdk_from_yaml 端到端
- R03 错误处理（不静默兜底）
- 学术诚信（溯源 URL）

来源:
- PyYAML: https://docs.python.org/3/library/yaml.html
- gdsfactory LayerStack: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
- gdsfactory CrossSection: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory from_yaml: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
- SemVer: https://semver.org
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from polaris.pdk.gdsfactory_pdk_bridge import (
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisSection,
)
from polaris.pdk.yaml_pdk_config import (
    PDKYamlConfig,
    YamlCellSpec,
    YamlCrossSectionSpec,
    YamlLayerLevelSpec,
    YamlLayerSpec,
    YamlSectionSpec,
    build_polaris_cross_section,
    build_polaris_layer_stack,
    build_polaris_pdk_from_yaml,
    parse_pdk_yaml,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)


# =============================================================================
# 测试用 YAML 样本
# =============================================================================
SAMPLE_YAML = """\
pdk:
  name: polaris_soi
  version: "1.0.0"
  platform: SOI
  process_node: "220nm SOI"
  description: PoLaRIS 220nm SOI PDK
  source_url: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

layers:
  WG:
    gds_layer: 1
    gds_datatype: 0
    material: Si
    description: 波导层
  SLAB150:
    gds_layer: 2
    gds_datatype: 0
    material: Si
    description: 150nm 板层

layer_stack:
  - layer: WG
    thickness_nm: 220
    zmin_nm: 0
    material: Si
    sidewall_angle_deg: 0
    refractive_index: [3.476, 0.0]
  - layer: SLAB150
    thickness_nm: 150
    zmin_nm: 0
    material: Si
    refractive_index_real: 3.476
    refractive_index_imag: 0.0

cross_sections:
  strip:
    width_um: 0.5
    offset_um: 0.0
    sections:
      - width_um: 0.5
        offset_um: 0.0
        layer: WG
        ports: [o1, o2]
  rib:
    width_um: 0.8
    sections:
      - width_um: 0.8
        offset_um: 0.0
        layer: WG
      - width_um: 2.0
        offset_um: 0.0
        layer: SLAB150

cells:
  mzi_2x2:
    platform: SOI
    category: passive
    params_schema:
      length_arm: 100.0
      gap: 0.3
    description: MZI 2x2 干涉仪
  y_branch:
    platform: SOI
    category: passive
    description: Y 分支
"""


@pytest.fixture
def sample_yaml_path(tmp_path: Path) -> Path:
    """生成临时 YAML 文件。"""
    p = tmp_path / "pdk.yaml"
    p.write_text(SAMPLE_YAML, encoding="utf-8")
    return p


# =============================================================================
# TestYamlLayerSpec: 层规格数据类
# =============================================================================
class TestYamlLayerSpec:
    """YamlLayerSpec 数据类测试。"""

    def test_required_fields(self) -> None:
        spec = YamlLayerSpec(name="WG", gds_layer=1, gds_datatype=0)
        assert spec.name == "WG"
        assert spec.gds_layer == 1
        assert spec.gds_datatype == 0

    def test_defaults(self) -> None:
        spec = YamlLayerSpec(name="WG", gds_layer=1, gds_datatype=0)
        assert spec.material == "unknown"
        assert spec.description == ""

    def test_with_optional_fields(self) -> None:
        spec = YamlLayerSpec(
            name="WG", gds_layer=1, gds_datatype=0,
            material="Si", description="波导层"
        )
        assert spec.material == "Si"
        assert spec.description == "波导层"


# =============================================================================
# TestYamlLayerLevelSpec: 层堆栈级别数据类
# =============================================================================
class TestYamlLayerLevelSpec:
    """YamlLayerLevelSpec 数据类测试。"""

    def test_required_fields(self) -> None:
        spec = YamlLayerLevelSpec(layer="WG", thickness_nm=220.0)
        assert spec.layer == "WG"
        assert spec.thickness_nm == 220.0

    def test_defaults(self) -> None:
        spec = YamlLayerLevelSpec(layer="WG", thickness_nm=220.0)
        assert spec.zmin_nm == 0.0
        assert spec.material == "unknown"
        assert spec.sidewall_angle_deg == 0.0
        assert spec.refractive_index_real is None
        assert spec.refractive_index_imag is None

    def test_with_refractive_index(self) -> None:
        spec = YamlLayerLevelSpec(
            layer="WG", thickness_nm=220.0,
            refractive_index_real=3.476,
            refractive_index_imag=0.0,
        )
        assert spec.refractive_index_real == 3.476
        assert spec.refractive_index_imag == 0.0


# =============================================================================
# TestYamlSectionSpec: 截面段数据类
# =============================================================================
class TestYamlSectionSpec:
    """YamlSectionSpec 数据类测试。"""

    def test_required_fields(self) -> None:
        spec = YamlSectionSpec(width_um=0.5, offset_um=0.0, layer="WG")
        assert spec.width_um == 0.5
        assert spec.offset_um == 0.0
        assert spec.layer == "WG"

    def test_defaults(self) -> None:
        spec = YamlSectionSpec(width_um=0.5, offset_um=0.0, layer="WG")
        assert spec.ports is None
        assert spec.hidden is False

    def test_with_ports(self) -> None:
        spec = YamlSectionSpec(
            width_um=0.5, offset_um=0.0, layer="WG",
            ports=("o1", "o2"), hidden=True,
        )
        assert spec.ports == ("o1", "o2")
        assert spec.hidden is True


# =============================================================================
# TestYamlCrossSectionSpec: 截面规格数据类
# =============================================================================
class TestYamlCrossSectionSpec:
    """YamlCrossSectionSpec 数据类测试。"""

    def test_required_name(self) -> None:
        spec = YamlCrossSectionSpec(name="strip")
        assert spec.name == "strip"

    def test_defaults(self) -> None:
        spec = YamlCrossSectionSpec(name="strip")
        assert spec.width_um == 0.0
        assert spec.offset_um == 0.0
        assert spec.sections == []

    def test_with_sections(self) -> None:
        section = YamlSectionSpec(width_um=0.5, offset_um=0.0, layer="WG")
        spec = YamlCrossSectionSpec(
            name="strip", width_um=0.5, sections=[section]
        )
        assert len(spec.sections) == 1
        assert spec.sections[0].layer == "WG"


# =============================================================================
# TestYamlCellSpec: cell 规格数据类
# =============================================================================
class TestYamlCellSpec:
    """YamlCellSpec 数据类测试。"""

    def test_required_name(self) -> None:
        spec = YamlCellSpec(name="mzi_2x2")
        assert spec.name == "mzi_2x2"

    def test_defaults(self) -> None:
        spec = YamlCellSpec(name="mzi_2x2")
        assert spec.platform == "SOI"
        assert spec.category == "passive"
        assert spec.params_schema == {}
        assert spec.description == ""

    def test_with_params(self) -> None:
        spec = YamlCellSpec(
            name="mzi_2x2", platform="SOI", category="passive",
            params_schema={"length_arm": 100.0, "gap": 0.3},
            description="MZI 2x2 干涉仪",
        )
        assert spec.params_schema["length_arm"] == 100.0
        assert spec.description == "MZI 2x2 干涉仪"


# =============================================================================
# TestPDKYamlConfig: 完整配置数据类
# =============================================================================
class TestPDKYamlConfig:
    """PDKYamlConfig 数据类测试。"""

    def test_required_fields(self) -> None:
        cfg = PDKYamlConfig(
            name="polaris_soi", version="1.0.0",
            platform="SOI", process_node="220nm SOI",
        )
        assert cfg.name == "polaris_soi"
        assert cfg.version == "1.0.0"
        assert cfg.platform == "SOI"
        assert cfg.process_node == "220nm SOI"

    def test_defaults_empty_lists(self) -> None:
        cfg = PDKYamlConfig(
            name="polaris_soi", version="1.0.0",
            platform="SOI", process_node="220nm SOI",
        )
        assert cfg.layers == []
        assert cfg.layer_stack == []
        assert cfg.cross_sections == []
        assert cfg.cells == []
        assert cfg.description == ""
        assert cfg.source_url == ""


# =============================================================================
# TestParsePdkYaml: YAML 解析
# =============================================================================
class TestParsePdkYaml:
    """parse_pdk_yaml 解析测试。"""

    def test_parse_full_sample(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        assert cfg.name == "polaris_soi"
        assert cfg.version == "1.0.0"
        assert cfg.platform == "SOI"
        assert cfg.process_node == "220nm SOI"
        assert cfg.description == "PoLaRIS 220nm SOI PDK"
        assert cfg.source_url == "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"
        assert len(cfg.layers) == 2
        assert len(cfg.layer_stack) == 2
        assert len(cfg.cross_sections) == 2
        assert len(cfg.cells) == 2

    def test_parse_layers(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        wg = next(l for l in cfg.layers if l.name == "WG")
        assert wg.gds_layer == 1
        assert wg.gds_datatype == 0
        assert wg.material == "Si"
        assert wg.description == "波导层"

    def test_parse_layer_stack_with_list_ri(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        wg_level = next(l for l in cfg.layer_stack if l.layer == "WG")
        assert wg_level.thickness_nm == 220
        assert wg_level.zmin_nm == 0
        assert wg_level.material == "Si"
        assert wg_level.refractive_index_real == 3.476
        assert wg_level.refractive_index_imag == 0.0

    def test_parse_layer_stack_with_scalar_ri(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        slab = next(l for l in cfg.layer_stack if l.layer == "SLAB150")
        assert slab.thickness_nm == 150
        assert slab.refractive_index_real == 3.476
        assert slab.refractive_index_imag == 0.0

    def test_parse_cross_sections(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        strip = next(xs for xs in cfg.cross_sections if xs.name == "strip")
        assert strip.width_um == 0.5
        assert len(strip.sections) == 1
        assert strip.sections[0].layer == "WG"
        assert strip.sections[0].ports == ("o1", "o2")

    def test_parse_cells(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        mzi = next(c for c in cfg.cells if c.name == "mzi_2x2")
        assert mzi.platform == "SOI"
        assert mzi.category == "passive"
        assert mzi.params_schema["length_arm"] == 100.0
        assert mzi.params_schema["gap"] == 0.3
        assert mzi.description == "MZI 2x2 干涉仪"

    def test_parse_minimal_yaml(self, tmp_path: Path) -> None:
        """最小 YAML（仅必填字段）。"""
        p = tmp_path / "minimal.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: minimal
              version: "0.1.0"
              platform: SiN
        """), encoding="utf-8")
        cfg = parse_pdk_yaml(p)
        assert cfg.name == "minimal"
        assert cfg.version == "0.1.0"
        assert cfg.platform == "SiN"
        assert cfg.process_node == ""
        assert cfg.layers == []
        assert cfg.cells == []


# =============================================================================
# TestSerializePdkYaml: YAML 序列化
# =============================================================================
class TestSerializePdkYaml:
    """serialize_pdk_yaml 序列化测试。"""

    def test_round_trip(self, sample_yaml_path: Path, tmp_path: Path) -> None:
        """序列化后重新解析应得到相同配置。"""
        cfg1 = parse_pdk_yaml(sample_yaml_path)
        yaml_str = serialize_pdk_yaml(cfg1)
        # 写入新文件并重新解析
        out = tmp_path / "round_trip.yaml"
        out.write_text(yaml_str, encoding="utf-8")
        cfg2 = parse_pdk_yaml(out)
        assert cfg2.name == cfg1.name
        assert cfg2.version == cfg1.version
        assert cfg2.platform == cfg1.platform
        assert cfg2.process_node == cfg1.process_node
        assert cfg2.source_url == cfg1.source_url
        assert len(cfg2.layers) == len(cfg1.layers)
        assert len(cfg2.layer_stack) == len(cfg1.layer_stack)
        assert len(cfg2.cross_sections) == len(cfg1.cross_sections)
        assert len(cfg2.cells) == len(cfg1.cells)

    def test_serialize_contains_pdk_section(self) -> None:
        cfg = PDKYamlConfig(
            name="test", version="1.0.0",
            platform="SOI", process_node="220nm SOI",
            description="测试 PDK",
            source_url="https://example.com",
        )
        s = serialize_pdk_yaml(cfg)
        assert "pdk:" in s
        assert "name: test" in s
        # PyYAML safe_dump 对 "1.0.0" 不加引号（YAML 解析为字符串，无需引号）
        assert "version: 1.0.0" in s
        assert "platform: SOI" in s

    def test_serialize_with_layers(self) -> None:
        cfg = PDKYamlConfig(
            name="test", version="1.0.0",
            platform="SOI", process_node="220nm SOI",
            layers=[YamlLayerSpec(name="WG", gds_layer=1, gds_datatype=0, material="Si")],
        )
        s = serialize_pdk_yaml(cfg)
        assert "layers:" in s
        assert "WG:" in s
        assert "gds_layer: 1" in s

    def test_serialize_with_layer_stack_ri(self) -> None:
        cfg = PDKYamlConfig(
            name="test", version="1.0.0",
            platform="SOI", process_node="220nm SOI",
            layer_stack=[YamlLayerLevelSpec(
                layer="WG", thickness_nm=220,
                refractive_index_real=3.476, refractive_index_imag=0.0,
            )],
        )
        s = serialize_pdk_yaml(cfg)
        assert "layer_stack:" in s
        # 复折射率以列表形式序列化
        assert "3.476" in s

    def test_serialize_empty_name_raises(self) -> None:
        cfg = PDKYamlConfig(name="", version="1.0.0", platform="SOI", process_node="")
        with pytest.raises(ValueError, match="name"):
            serialize_pdk_yaml(cfg)

    def test_serialize_empty_version_raises(self) -> None:
        cfg = PDKYamlConfig(name="test", version="", platform="SOI", process_node="")
        with pytest.raises(ValueError, match="version"):
            serialize_pdk_yaml(cfg)

    def test_serialize_empty_platform_raises(self) -> None:
        cfg = PDKYamlConfig(name="test", version="1.0.0", platform="", process_node="")
        with pytest.raises(ValueError, match="platform"):
            serialize_pdk_yaml(cfg)


# =============================================================================
# TestValidatePdkYaml: 配置校验
# =============================================================================
class TestValidatePdkYaml:
    """validate_pdk_yaml 校验测试。"""

    def test_valid_config(self, sample_yaml_path: Path) -> None:
        cfg = parse_pdk_yaml(sample_yaml_path)
        errors = validate_pdk_yaml(cfg)
        assert errors == []

    def test_empty_name(self) -> None:
        cfg = PDKYamlConfig(name="", version="1.0.0", platform="SOI", process_node="",
                            source_url="https://example.com")
        errors = validate_pdk_yaml(cfg)
        assert any("name" in e for e in errors)

    def test_empty_version(self) -> None:
        cfg = PDKYamlConfig(name="test", version="", platform="SOI", process_node="",
                            source_url="https://example.com")
        errors = validate_pdk_yaml(cfg)
        assert any("version" in e for e in errors)

    def test_empty_platform(self) -> None:
        cfg = PDKYamlConfig(name="test", version="1.0.0", platform="", process_node="",
                            source_url="https://example.com")
        errors = validate_pdk_yaml(cfg)
        assert any("platform" in e for e in errors)

    def test_empty_source_url_triggers_r02(self) -> None:
        """R02 学术诚信: source_url 必填。"""
        cfg = PDKYamlConfig(name="test", version="1.0.0", platform="SOI", process_node="",
                            source_url="")
        errors = validate_pdk_yaml(cfg)
        assert any("source_url" in e for e in errors)
        assert any("R02" in e or "溯源" in e for e in errors)

    def test_layer_stack_undefined_layer(self) -> None:
        """层堆栈引用未定义层。"""
        cfg = PDKYamlConfig(
            name="test", version="1.0.0", platform="SOI", process_node="",
            source_url="https://example.com",
            layers=[YamlLayerSpec(name="WG", gds_layer=1, gds_datatype=0)],
            layer_stack=[YamlLayerLevelSpec(layer="UNKNOWN", thickness_nm=220)],
        )
        errors = validate_pdk_yaml(cfg)
        assert any("UNKNOWN" in e for e in errors)

    def test_cross_section_undefined_layer(self) -> None:
        """截面引用未定义层。"""
        cfg = PDKYamlConfig(
            name="test", version="1.0.0", platform="SOI", process_node="",
            source_url="https://example.com",
            layers=[YamlLayerSpec(name="WG", gds_layer=1, gds_datatype=0)],
            cross_sections=[YamlCrossSectionSpec(
                name="bad", sections=[YamlSectionSpec(width_um=0.5, offset_um=0.0, layer="MISSING")]
            )],
        )
        errors = validate_pdk_yaml(cfg)
        assert any("MISSING" in e for e in errors)

    def test_duplicate_cell_names(self) -> None:
        """cell 名称重复。"""
        cfg = PDKYamlConfig(
            name="test", version="1.0.0", platform="SOI", process_node="",
            source_url="https://example.com",
            cells=[
                YamlCellSpec(name="dup"),
                YamlCellSpec(name="dup"),
            ],
        )
        errors = validate_pdk_yaml(cfg)
        assert any("重复" in e and "dup" in e for e in errors)


# =============================================================================
# TestBuildPolarisLayerStack: 构建 PolarisLayerStack
# =============================================================================
class TestBuildPolarisLayerStack:
    """build_polaris_layer_stack 测试。"""

    def test_build_simple(self) -> None:
        specs = [
            YamlLayerLevelSpec(layer="WG", thickness_nm=220, material="Si"),
            YamlLayerLevelSpec(layer="SLAB", thickness_nm=150, material="Si"),
        ]
        ls = build_polaris_layer_stack("test_ls", specs)
        assert isinstance(ls, PolarisLayerStack)
        assert ls.name == "test_ls"
        assert len(ls.levels) == 2
        assert ls.levels[0].layer == "WG"
        assert ls.levels[0].thickness_nm == 220
        assert ls.levels[0].material == "Si"

    def test_build_with_refractive_index(self) -> None:
        specs = [
            YamlLayerLevelSpec(
                layer="WG", thickness_nm=220,
                refractive_index_real=3.476,
                refractive_index_imag=0.0,
            ),
        ]
        ls = build_polaris_layer_stack("test_ls", specs)
        assert ls.levels[0].refractive_index == complex(3.476, 0.0)

    def test_build_with_real_only(self) -> None:
        """只指定实部，虚部默认 0。"""
        specs = [
            YamlLayerLevelSpec(
                layer="WG", thickness_nm=220,
                refractive_index_real=3.476,
            ),
        ]
        ls = build_polaris_layer_stack("test_ls", specs)
        assert ls.levels[0].refractive_index == complex(3.476, 0.0)

    def test_build_without_refractive_index(self) -> None:
        specs = [YamlLayerLevelSpec(layer="WG", thickness_nm=220)]
        ls = build_polaris_layer_stack("test_ls", specs)
        assert ls.levels[0].refractive_index is None

    def test_build_empty(self) -> None:
        ls = build_polaris_layer_stack("empty", [])
        assert ls.name == "empty"
        assert ls.levels == []


# =============================================================================
# TestBuildPolarisCrossSection: 构建 PolarisCrossSection
# =============================================================================
class TestBuildPolarisCrossSection:
    """build_polaris_cross_section 测试。"""

    def test_build_simple(self) -> None:
        spec = YamlCrossSectionSpec(
            name="strip", width_um=0.5,
            sections=[YamlSectionSpec(width_um=0.5, offset_um=0.0, layer="WG")],
        )
        xs = build_polaris_cross_section(spec)
        assert isinstance(xs, PolarisCrossSection)
        assert xs.name == "strip"
        assert xs.width_um == 0.5
        assert len(xs.sections) == 1
        assert xs.sections[0].layer == "WG"

    def test_build_with_ports(self) -> None:
        spec = YamlCrossSectionSpec(
            name="strip", width_um=0.5,
            sections=[YamlSectionSpec(
                width_um=0.5, offset_um=0.0, layer="WG",
                ports=("o1", "o2"), hidden=True,
            )],
        )
        xs = build_polaris_cross_section(spec)
        assert isinstance(xs.sections[0], PolarisSection)
        assert xs.sections[0].ports == ("o1", "o2")
        assert xs.sections[0].hidden is True

    def test_build_empty_sections(self) -> None:
        spec = YamlCrossSectionSpec(name="empty", width_um=0.5)
        xs = build_polaris_cross_section(spec)
        assert xs.sections == []


# =============================================================================
# TestBuildPolarisPdkFromYaml: 端到端构建
# =============================================================================
class TestBuildPolarisPdkFromYaml:
    """build_polaris_pdk_from_yaml 端到端测试。"""

    def test_build_full_pdk(self, sample_yaml_path: Path) -> None:
        pdk = build_polaris_pdk_from_yaml(sample_yaml_path)
        assert isinstance(pdk, PolarisPDK)
        assert pdk.name == "polaris_soi"
        assert pdk.platform == "SOI"
        assert pdk.process_node == "220nm SOI"
        # devices 留空，由 register_polaris_cell 填充
        assert pdk.devices == {}
        # layer_stack 构建
        assert pdk.layer_stack is not None
        assert len(pdk.layer_stack.levels) == 2
        # cross_sections 构建
        assert "strip" in pdk.cross_sections
        assert "rib" in pdk.cross_sections
        strip = pdk.cross_sections["strip"]
        assert isinstance(strip, PolarisCrossSection)
        assert strip.width_um == 0.5

    def test_build_layer_stack_refractive_index(self, sample_yaml_path: Path) -> None:
        pdk = build_polaris_pdk_from_yaml(sample_yaml_path)
        assert pdk.layer_stack is not None
        wg_level = next(l for l in pdk.layer_stack.levels if l.layer == "WG")
        assert wg_level.refractive_index == complex(3.476, 0.0)

    def test_build_minimal_yaml(self, tmp_path: Path) -> None:
        """最小 YAML（无 layer_stack/cross_sections）应构建成功。"""
        p = tmp_path / "min.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: min
              version: "1.0.0"
              platform: SOI
              process_node: 220nm SOI
              source_url: https://example.com
        """), encoding="utf-8")
        pdk = build_polaris_pdk_from_yaml(p)
        assert pdk.name == "min"
        assert pdk.layer_stack is None
        assert pdk.cross_sections == {}

    def test_build_missing_source_url_fails(self, tmp_path: Path) -> None:
        """缺 source_url 时校验失败。"""
        p = tmp_path / "no_url.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
              process_node: 220nm SOI
        """), encoding="utf-8")
        with pytest.raises(ValueError, match="校验失败"):
            build_polaris_pdk_from_yaml(p)


# =============================================================================
# TestR03ErrorHandling: R03 禁止 fall-back
# =============================================================================
class TestR03ErrorHandling:
    """R03 错误处理测试（所有异常路径不静默兜底）。"""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="不存在"):
            parse_pdk_yaml(tmp_path / "nonexistent.yaml")

    def test_yaml_syntax_error_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("pdk: { invalid: yaml: syntax: ]", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML 解析失败"):
            parse_pdk_yaml(p)

    def test_top_level_non_dict_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="顶层应为字典"):
            parse_pdk_yaml(p)

    def test_missing_pdk_section_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "no_pdk.yaml"
        p.write_text("layers: {}\n", encoding="utf-8")
        # pdk 段缺失时 _require_dict 会触发，但 data.get("pdk", {}) 返回 {}
        # 然后必填字段校验 raise KeyError
        with pytest.raises(KeyError, match="name"):
            parse_pdk_yaml(p)

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "no_version.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              platform: SOI
        """), encoding="utf-8")
        with pytest.raises(KeyError, match="version"):
            parse_pdk_yaml(p)

    def test_layer_missing_gds_layer_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_layer.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layers:
              WG:
                gds_datatype: 0
        """), encoding="utf-8")
        with pytest.raises(KeyError, match="gds_layer"):
            parse_pdk_yaml(p)

    def test_layer_gds_layer_non_int_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_type.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layers:
              WG:
                gds_layer: "1"
                gds_datatype: 0
        """), encoding="utf-8")
        with pytest.raises(TypeError, match="整数"):
            parse_pdk_yaml(p)

    def test_layer_stack_missing_thickness_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_ls.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layer_stack:
              - layer: WG
        """), encoding="utf-8")
        with pytest.raises(KeyError, match="thickness_nm"):
            parse_pdk_yaml(p)

    def test_layer_stack_bad_refractive_index_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_ri.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layer_stack:
              - layer: WG
                thickness_nm: 220
                refractive_index: 3.476
        """), encoding="utf-8")
        with pytest.raises(ValueError, match="real, imag"):
            parse_pdk_yaml(p)

    def test_section_missing_layer_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_section.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            cross_sections:
              strip:
                sections:
                  - width_um: 0.5
        """), encoding="utf-8")
        with pytest.raises(KeyError, match="layer"):
            parse_pdk_yaml(p)

    def test_section_bad_ports_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_ports.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            cross_sections:
              strip:
                sections:
                  - width_um: 0.5
                    layer: WG
                    ports: [o1]
        """), encoding="utf-8")
        with pytest.raises(ValueError, match="ports"):
            parse_pdk_yaml(p)

    def test_cell_params_schema_non_dict_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_cell.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            cells:
              mzi:
                params_schema: [1, 2, 3]
        """), encoding="utf-8")
        with pytest.raises(TypeError, match="params_schema"):
            parse_pdk_yaml(p)

    def test_layers_non_dict_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_layers.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layers:
              - WG
        """), encoding="utf-8")
        with pytest.raises(TypeError, match="layers"):
            parse_pdk_yaml(p)

    def test_layer_stack_non_list_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_ls_type.yaml"
        p.write_text(textwrap.dedent("""\
            pdk:
              name: test
              version: "1.0.0"
              platform: SOI
            layer_stack:
              WG: {thickness_nm: 220}
        """), encoding="utf-8")
        with pytest.raises(TypeError, match="layer_stack"):
            parse_pdk_yaml(p)


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """集成测试（端到端业务流程）。"""

    def test_round_trip_full(self, sample_yaml_path: Path, tmp_path: Path) -> None:
        """解析 → 序列化 → 再解析 应保持一致。"""
        cfg1 = parse_pdk_yaml(sample_yaml_path)
        yaml_str = serialize_pdk_yaml(cfg1)
        out = tmp_path / "round_trip.yaml"
        out.write_text(yaml_str, encoding="utf-8")
        cfg2 = parse_pdk_yaml(out)
        # 验证关键字段一致
        assert cfg2.name == cfg1.name
        assert cfg2.version == cfg1.version
        assert cfg2.platform == cfg1.platform
        assert cfg2.source_url == cfg1.source_url
        # layers 一致
        assert len(cfg2.layers) == len(cfg1.layers)
        wg1 = next(l for l in cfg1.layers if l.name == "WG")
        wg2 = next(l for l in cfg2.layers if l.name == "WG")
        assert wg2.gds_layer == wg1.gds_layer
        assert wg2.material == wg1.material
        # cells 一致
        mzi1 = next(c for c in cfg1.cells if c.name == "mzi_2x2")
        mzi2 = next(c for c in cfg2.cells if c.name == "mzi_2x2")
        assert mzi2.platform == mzi1.platform
        assert mzi2.params_schema == mzi1.params_schema

    def test_build_polaris_pdk_full(self, sample_yaml_path: Path) -> None:
        """端到端构建 PolarisPDK 完整测试。"""
        pdk = build_polaris_pdk_from_yaml(sample_yaml_path)
        # 验证 PDK 元数据
        assert pdk.name == "polaris_soi"
        assert pdk.platform == "SOI"
        assert pdk.process_node == "220nm SOI"
        # 验证 layer_stack
        assert pdk.layer_stack is not None
        assert len(pdk.layer_stack.levels) == 2
        wg_level = next(l for l in pdk.layer_stack.levels if l.layer == "WG")
        assert wg_level.thickness_nm == 220
        assert wg_level.material == "Si"
        assert wg_level.refractive_index == complex(3.476, 0.0)
        # 验证 cross_sections
        assert "strip" in pdk.cross_sections
        assert "rib" in pdk.cross_sections
        strip = pdk.cross_sections["strip"]
        assert strip.width_um == 0.5
        assert len(strip.sections) == 1
        assert strip.sections[0].ports == ("o1", "o2")


# =============================================================================
# TestAcademicIntegrity: 学术诚信 R02
# =============================================================================
class TestAcademicIntegrity:
    """学术诚信测试: 所有数据可溯源。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 包含 ≥5 个文献 URL。"""
        from polaris.pdk import yaml_pdk_config
        doc = yaml_pdk_config.__doc__ or ""
        # 统计 URL 数量
        urls = [line for line in doc.split() if line.startswith("http")]
        assert len(urls) >= 5, f"模块 docstring 应包含 ≥5 个 URL，实际 {len(urls)}"

    def test_polaris_layer_level_source(self) -> None:
        """PolarisLayerLevel 来源标注。"""
        from polaris.pdk.gdsfactory_pdk_bridge import PolarisLayerLevel
        doc = PolarisLayerLevel.__doc__ or ""
        assert "github.com/gdsfactory" in doc or "gdsfactory" in doc

    def test_polaris_layer_stack_source(self) -> None:
        """PolarisLayerStack 来源标注。"""
        from polaris.pdk.gdsfactory_pdk_bridge import PolarisLayerStack
        doc = PolarisLayerStack.__doc__ or ""
        assert "gdsfactory" in doc

    def test_polaris_cross_section_source(self) -> None:
        """PolarisCrossSection 来源标注。"""
        from polaris.pdk.gdsfactory_pdk_bridge import PolarisCrossSection
        doc = PolarisCrossSection.__doc__ or ""
        assert "gdsfactory" in doc

    def test_source_url_required_in_validation(self) -> None:
        """R02 学术诚信: validate_pdk_yaml 强制要求 source_url。"""
        cfg = PDKYamlConfig(
            name="test", version="1.0.0", platform="SOI", process_node="",
            source_url="",
        )
        errors = validate_pdk_yaml(cfg)
        assert any("source_url" in e for e in errors)

    def test_sample_yaml_has_source_url(self, sample_yaml_path: Path) -> None:
        """样例 YAML 必须包含 source_url（R02）。"""
        cfg = parse_pdk_yaml(sample_yaml_path)
        assert cfg.source_url == "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"
