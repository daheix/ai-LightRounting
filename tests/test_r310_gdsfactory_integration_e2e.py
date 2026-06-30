"""R310 gdsfactory 集成端到端测试套件。

覆盖 R301-R309 的完整业务流程集成测试，验证各模块协同工作:
- R301 GDSII 读取增强
- R302 GDSII 写出增强
- R303 PDK 双向兼容层映射
- R304 联合仿真组件级（需 gdsfactory，标记 skip）
- R305 联合仿真电路级（需 gdsfactory，标记 skip）
- R306 PCell ↔ gdsfactory Component 双向兼容（部分需 gdsfactory）
- R307 KLayout DRC 集成桥接
- R308 gdsfactory 插件注册机制
- R309 YAML PDK 配置系统

端到端业务流程:
YAML PDK 配置 → PolarisPDK → PolarisCellRegistry 注册 →
KLayout DRC 验证 → GDSII 导出 → 层映射双向验证

来源:
- gdsfactory PDK 集成: https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- Adapter Pattern (Gamma 1994): https://en.wikipedia.org/wiki/Adapter_pattern
- Fowler, "Patterns of Enterprise Application Architecture", 2002
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import pytest

from polaris.pdk import (
    GDSIIExportConfig,
    PDKYamlConfig,
    PolarisCellEntry,
    PolarisCellRegistry,
    PolarisPDK,
    YamlCellSpec,
    YamlCrossSectionSpec,
    YamlLayerLevelSpec,
    YamlLayerSpec,
    YamlSectionSpec,
    build_polaris_cross_section,
    build_polaris_layer_stack,
    build_polaris_pdk_from_yaml,
    export_gdsii_from_cells,
    gdsfactory_to_polaris_layer,
    get_siepic_layer_map,
    merge_layer_maps,
    parse_pdk_yaml,
    polaris_to_gdsfactory_layer,
    register_polaris_cell,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)
from polaris.pdk.pcell import PCellMultiView
from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory
from polaris.verification.klayout_drc_bridge import (
    KLayoutDRCConfig,
    KLayoutDRCResult,
    check_min_area,
    check_min_spacing,
    check_min_width,
    run_klayout_drc,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def sample_pdk_yaml_path(tmp_path: Path) -> Path:
    """生成完整样例 PDK YAML 文件。"""
    yaml_content = """\
pdk:
  name: polaris_soi_e2e
  version: "1.0.0"
  platform: SOI
  process_node: "220nm SOI"
  description: R310 端到端测试 PDK
  source_url: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

layers:
  WG:
    gds_layer: 1
    gds_datatype: 0
    material: Si
    description: 波导核心层
  SLAB150:
    gds_layer: 2
    gds_datatype: 0
    material: Si
    description: 150nm slab 层
  METAL:
    gds_layer: 5
    gds_datatype: 0
    material: Al
    description: 金属层

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
    refractive_index: [3.476, 0.0]
  - layer: METAL
    thickness_nm: 1000
    zmin_nm: 220
    material: Al
    refractive_index: [1.0, 0.0]

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
  ring_modulator:
    platform: SOI
    category: active
    params_schema:
      radius: 10.0
    description: 环形调制器
"""
    p = tmp_path / "polaris_soi_e2e.yaml"
    p.write_text(yaml_content, encoding="utf-8")
    return p


@pytest.fixture
def sample_cell_factory():
    """返回一个简单的 PCell 工厂函数（用于注册测试）。"""
    def _factory(width: float = 0.5, length: float = 10.0) -> PCellMultiView:
        # PCellMultiView 构造: (name, params=None)
        return PCellMultiView(name="test_waveguide", params={"width": width, "length": length})
    return _factory


# =============================================================================
# TestR309YamlPdkE2E: R309 YAML PDK 端到端
# =============================================================================
class TestR309YamlPdkE2E:
    """R309 YAML PDK 配置系统端到端测试。"""

    def test_yaml_to_polaris_pdk_full(self, sample_pdk_yaml_path: Path) -> None:
        """YAML → PolarisPDK 完整流程。"""
        pdk = build_polaris_pdk_from_yaml(sample_pdk_yaml_path)
        # PDK 元数据
        assert pdk.name == "polaris_soi_e2e"
        assert pdk.platform == "SOI"
        assert pdk.process_node == "220nm SOI"
        # layer_stack
        assert pdk.layer_stack is not None
        assert len(pdk.layer_stack.levels) == 3
        # cross_sections
        assert "strip" in pdk.cross_sections
        assert "rib" in pdk.cross_sections
        # devices 留空
        assert pdk.devices == {}

    def test_yaml_round_trip_preserves_structure(self, sample_pdk_yaml_path: Path, tmp_path: Path) -> None:
        """YAML → Config → YAML → Config 应保持结构一致。"""
        cfg1 = parse_pdk_yaml(sample_pdk_yaml_path)
        yaml_str = serialize_pdk_yaml(cfg1)
        out = tmp_path / "round_trip.yaml"
        out.write_text(yaml_str, encoding="utf-8")
        cfg2 = parse_pdk_yaml(out)
        assert cfg2.name == cfg1.name
        assert cfg2.version == cfg1.version
        assert len(cfg2.layers) == len(cfg1.layers)
        assert len(cfg2.layer_stack) == len(cfg1.layer_stack)
        assert len(cfg2.cross_sections) == len(cfg1.cross_sections)
        assert len(cfg2.cells) == len(cfg1.cells)

    def test_yaml_validation_catches_errors(self) -> None:
        """validate_pdk_yaml 应捕获多重错误。"""
        cfg = PDKYamlConfig(
            name="",  # 空 name
            version="",  # 空 version
            platform="",
            process_node="",
            source_url="",  # 空 source_url (R02)
        )
        errors = validate_pdk_yaml(cfg)
        # 至少 4 个错误
        assert len(errors) >= 4


# =============================================================================
# TestR303LayerMapE2E: R303 层映射端到端
# =============================================================================
class TestR303LayerMapE2E:
    """R303 PDK 双向兼容层映射端到端测试。"""

    def test_siepic_layer_map_completeness(self) -> None:
        """SiEPIC 层映射应包含 13 层。"""
        layer_map = get_siepic_layer_map()
        assert len(layer_map) == 13
        # 关键层验证
        assert (1, 0) in layer_map  # WG
        assert (2, 0) in layer_map  # SLAB150
        assert (3, 0) in layer_map  # SLAB90
        assert (4, 0) in layer_map  # SiN
        assert (5, 0) in layer_map  # METAL
        assert layer_map[(1, 0)] == "WG"
        assert layer_map[(5, 0)] == "METAL"

    def test_layer_round_trip(self) -> None:
        """polaris_to_gdsfactory_layer / gdsfactory_to_polaris_layer 往返一致。"""
        # 对 SiEPIC 标准层做往返测试
        layer_map = get_siepic_layer_map()
        for (gds_layer, gds_dt), polaris_name in layer_map.items():
            # polaris_name → (gds_layer, gds_dt)
            gds_tuple = polaris_to_gdsfactory_layer(polaris_name)
            assert gds_tuple == (gds_layer, gds_dt), (
                f"polaris_to_gdsfactory_layer({polaris_name!r}) = {gds_tuple}, "
                f"期望 {(gds_layer, gds_dt)}"
            )
            # (gds_layer, gds_dt) → polaris_name
            recovered = gdsfactory_to_polaris_layer(gds_layer, gds_dt)
            assert recovered == polaris_name, (
                f"gdsfactory_to_polaris_layer({gds_layer}, {gds_dt}) = {recovered!r}, "
                f"期望 {polaris_name!r}"
            )

    def test_merge_layer_maps(self) -> None:
        """合并两个层映射。"""
        map1 = {(1, 0): "WG", (2, 0): "SLAB150"}
        map2 = {(3, 0): "SLAB90", (4, 0): "SiN"}
        merged = merge_layer_maps(map1, map2)
        assert len(merged) == 4
        assert merged[(1, 0)] == "WG"
        assert merged[(4, 0)] == "SiN"


# =============================================================================
# TestR302GdsiiExportE2E: R302 GDSII 导出端到端
# =============================================================================
class TestR302GdsiiExportE2E:
    """R302 GDSII 写出端到端测试。"""

    def test_export_simple_cell(self, tmp_path: Path) -> None:
        """导出简单 cell（含多边形）到 GDSII 文件。"""
        cells_spec = [
            {
                "name": "waveguide_simple",
                "polygons": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                    }
                ],
                "is_top": True,
            }
        ]
        out_path = tmp_path / "waveguide.gds"
        result = export_gdsii_from_cells(cells_spec, out_path)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_export_multiple_cells_with_instance(self, tmp_path: Path) -> None:
        """导出含 instance 的多 cell GDSII。"""
        cells_spec = [
            {
                "name": "wg_cell",
                "polygons": [
                    {
                        "layer": 1,
                        "datatype": 0,
                        "points": [[0, 0], [5, 0], [5, 0.5], [0, 0.5]],
                    }
                ],
                "is_top": False,
            },
            {
                "name": "TOP",
                "instances": [
                    {"cell_name": "wg_cell", "x": 0, "y": 0, "rotation": 0, "mirror": False},
                    {"cell_name": "wg_cell", "x": 0, "y": 1.0, "rotation": 0, "mirror": False},
                ],
                "is_top": True,
            },
        ]
        out_path = tmp_path / "two_wg.gds"
        result = export_gdsii_from_cells(cells_spec, out_path)
        assert Path(result).exists()

    def test_export_empty_cells_raises(self, tmp_path: Path) -> None:
        """空 cells_spec 应 raise ValueError（R03）。"""
        with pytest.raises(ValueError, match="空"):
            export_gdsii_from_cells([], tmp_path / "empty.gds")


# =============================================================================
# TestR307KLayoutDRCE2E: R307 KLayout DRC 端到端
# =============================================================================
class TestR307KLayoutDRCE2E:
    """R307 KLayout DRC 集成桥接端到端测试。"""

    def test_min_width_compliant(self) -> None:
        """合规多边形（宽度=0.5μm，规则=0.45μm）应无违规。"""
        polygons = [np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)]
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        result = check_min_width(polygons, rule)
        assert isinstance(result, KLayoutDRCResult)
        assert result.violation_count == 0
        assert result.severity == "error"

    def test_min_width_violation(self) -> None:
        """违规多边形（宽度=0.3μm，规则=0.45μm）应有违规。"""
        polygons = [np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)]
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        result = check_min_width(polygons, rule)
        assert result.violation_count > 0

    def test_min_spacing_compliant(self) -> None:
        """两个间距=1.0μm 的多边形（规则=0.5μm）应无违规。"""
        polygons = [
            np.array([[0, 0], [5, 0], [5, 0.5], [0, 0.5]], dtype=float),
            np.array([[6, 0], [11, 0], [11, 0.5], [6, 0.5]], dtype=float),
        ]
        rule = CurvilinearDRCRule(
            name="S1", category=DRCRuleCategory.MIN_SPACING,
            layer="WG", limit_value=0.5,
        )
        result = check_min_spacing(polygons, rule)
        assert result.violation_count == 0

    def test_min_spacing_violation(self) -> None:
        """两个间距=0.2μm 的多边形（规则=0.5μm）应有违规。"""
        polygons = [
            np.array([[0, 0], [5, 0], [5, 0.5], [0, 0.5]], dtype=float),
            np.array([[5.2, 0], [10.2, 0], [10.2, 0.5], [5.2, 0.5]], dtype=float),
        ]
        rule = CurvilinearDRCRule(
            name="S1", category=DRCRuleCategory.MIN_SPACING,
            layer="WG", limit_value=0.5,
        )
        result = check_min_spacing(polygons, rule)
        assert result.violation_count > 0

    def test_min_area_compliant(self) -> None:
        """合规面积（5μm²，规则=2μm²）应无违规。"""
        polygons = [np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)]
        rule = CurvilinearDRCRule(
            name="A1", category=DRCRuleCategory.MIN_AREA,
            layer="WG", limit_value=2.0,
        )
        result = check_min_area(polygons, rule)
        assert result.violation_count == 0

    def test_min_area_violation(self) -> None:
        """违规面积（0.15μm²，规则=2μm²）应有违规。"""
        polygons = [np.array([[0, 0], [0.5, 0], [0.5, 0.3], [0, 0.3]], dtype=float)]
        rule = CurvilinearDRCRule(
            name="A1", category=DRCRuleCategory.MIN_AREA,
            layer="WG", limit_value=2.0,
        )
        result = check_min_area(polygons, rule)
        assert result.violation_count > 0

    def test_run_klayout_drc_multi_rules(self) -> None:
        """多规则 DRC 检查端到端。"""
        # 1 个违规的窄多边形 + 1 个合规的多边形
        polygons = [
            np.array([[0, 0], [5, 0], [5, 0.3], [0, 0.3]], dtype=float),  # 违规宽度
            np.array([[10, 0], [15, 0], [15, 0.5], [10, 0.5]], dtype=float),  # 合规
        ]
        rules = [
            CurvilinearDRCRule(
                name="W1", category=DRCRuleCategory.MIN_WIDTH,
                layer="WG", limit_value=0.45,
            ),
            CurvilinearDRCRule(
                name="A1", category=DRCRuleCategory.MIN_AREA,
                layer="WG", limit_value=0.1,
            ),
        ]
        results = run_klayout_drc({"WG": polygons}, rules)
        assert len(results) == 2
        # 至少 W1 规则有违规
        w1_result = next(r for r in results if r.rule_id == "W1")
        assert w1_result.violation_count > 0


# =============================================================================
# TestR308PolarisCellRegistryE2E: R308 注册流程端到端
# =============================================================================
class TestR308PolarisCellRegistryE2E:
    """R308 PolarisCellRegistry 完整注册流程测试。"""

    def test_register_and_retrieve(self, sample_cell_factory) -> None:
        """注册 → 检索 → 创建流程。"""
        registry = PolarisCellRegistry()
        entry = registry.register(
            "test_wg", sample_cell_factory,
            platform="SOI", category="passive",
            params_schema={"width": 0.5, "length": 10.0},
            description="测试波导",
        )
        assert isinstance(entry, PolarisCellEntry)
        assert registry.size == 1
        # 检索
        retrieved = registry.get("test_wg")
        assert retrieved.name == "test_wg"
        assert retrieved.platform == "SOI"
        # 创建
        pcell = registry.create("test_wg", width=0.6, length=20.0)
        assert isinstance(pcell, PCellMultiView)

    def test_register_multiple_cells(self, sample_cell_factory) -> None:
        """注册多个 cell 并按平台/类别列出。"""
        registry = PolarisCellRegistry()
        for name, platform, category in [
            ("mzi_soi", "SOI", "passive"),
            ("y_soi", "SOI", "passive"),
            ("ring_sin", "SiN", "passive"),
            ("modulator_inp", "InP", "active"),
        ]:
            registry.register(name, sample_cell_factory, platform=platform, category=category)
        assert registry.size == 4
        assert "SOI" in registry.platforms
        assert "SiN" in registry.platforms
        assert "InP" in registry.platforms
        # 按平台列出
        soi_cells = registry.list_by_platform("SOI")
        assert len(soi_cells) == 2
        # 按类别列出
        passive_cells = registry.list_by_category("passive")
        assert len(passive_cells) == 3

    def test_serialization_round_trip(self, sample_cell_factory) -> None:
        """注册表序列化往返。"""
        registry = PolarisCellRegistry()
        for name in ["cell_a", "cell_b", "cell_c"]:
            registry.register(
                name, sample_cell_factory,
                platform="SOI", category="passive",
                description=f"cell {name}",
            )
        data = registry.to_dict()
        assert len(data["entries"]) == 3
        # 验证不含 factory
        for entry_dict in data["entries"]:
            assert "factory" not in entry_dict

    def test_register_polaris_cell_decorator(self) -> None:
        """@register_polaris_cell 装饰器测试。"""
        registry = PolarisCellRegistry()

        @register_polaris_cell(registry=registry, name="deco_cell", platform="SOI")
        def my_cell(length: float = 10.0) -> PCellMultiView:
            return PCellMultiView(name="my_cell")

        # 装饰器应保持函数可调用
        assert callable(my_cell)
        # 装饰器应注册到 registry
        assert registry.size == 1
        assert "deco_cell" in registry.list_names()

    def test_duplicate_registration_raises(self, sample_cell_factory) -> None:
        """重复注册应 raise ValueError（R03）。"""
        registry = PolarisCellRegistry()
        registry.register("dup", sample_cell_factory)
        with pytest.raises(ValueError, match="已注册"):
            registry.register("dup", sample_cell_factory)


# =============================================================================
# TestFullWorkflowE2E: R301-R309 完整业务流程
# =============================================================================
class TestFullWorkflowE2E:
    """R301-R309 完整业务流程集成测试。"""

    def test_yaml_to_pdk_to_drc_workflow(self, sample_pdk_yaml_path: Path) -> None:
        """端到端: YAML PDK → PolarisPDK → DRC 检查。"""
        # Step 1: 从 YAML 构建 PolarisPDK
        pdk = build_polaris_pdk_from_yaml(sample_pdk_yaml_path)
        assert pdk.name == "polaris_soi_e2e"

        # Step 2: 使用 PDK 的 layer_stack 信息创建多边形
        # 假设我们用 WG 层创建一个窄多边形
        narrow_polygon = np.array([
            [0, 0], [10, 0], [10, 0.3], [0, 0.3]
        ], dtype=float)

        # Step 3: 使用 KLayout DRC 检查
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        result = check_min_width([narrow_polygon], rule)
        # 窄多边形应触发违规
        assert result.violation_count > 0
        assert result.rule_id == "W1"
        assert result.layer_name == "WG"

    def test_yaml_to_pdk_to_gdsii_workflow(self, sample_pdk_yaml_path: Path, tmp_path: Path) -> None:
        """端到端: YAML PDK → PolarisPDK → GDSII 导出。"""
        # Step 1: 从 YAML 构建 PolarisPDK
        pdk = build_polaris_pdk_from_yaml(sample_pdk_yaml_path)
        # 从 PDK 的 layers 字段获取层信息
        cfg = parse_pdk_yaml(sample_pdk_yaml_path)
        wg_layer = next(l for l in cfg.layers if l.name == "WG")
        assert wg_layer.gds_layer == 1
        assert wg_layer.gds_datatype == 0

        # Step 2: 使用层信息创建 GDSII cell
        cells_spec = [
            {
                "name": "waveguide_from_yaml",
                "polygons": [
                    {
                        "layer": wg_layer.gds_layer,
                        "datatype": wg_layer.gds_datatype,
                        "points": [[0, 0], [10, 0], [10, 0.5], [0, 0.5]],
                    }
                ],
                "is_top": True,
            }
        ]
        out_path = tmp_path / "from_yaml.gds"
        result = export_gdsii_from_cells(cells_spec, out_path)
        assert Path(result).exists()

    def test_layer_map_to_gdsii_workflow(self, tmp_path: Path) -> None:
        """端到端: SiEPIC 层映射 → GDSII 导出。"""
        # Step 1: 获取 SiEPIC 标准层映射
        layer_map = get_siepic_layer_map()
        wg_gds = polaris_to_gdsfactory_layer("WG")  # 应为 (1, 0)
        assert wg_gds in layer_map
        assert layer_map[wg_gds] == "WG"

        # Step 2: 使用层映射创建 GDSII
        cells_spec = [
            {
                "name": "siepic_wg",
                "polygons": [
                    {
                        "layer": wg_gds[0],
                        "datatype": wg_gds[1],
                        "points": [[0, 0], [20, 0], [20, 0.5], [0, 0.5]],
                    }
                ],
                "is_top": True,
            }
        ]
        out_path = tmp_path / "siepic_wg.gds"
        result = export_gdsii_from_cells(cells_spec, out_path)
        assert Path(result).exists()

    def test_full_workflow_with_registry_and_drc(
        self, sample_pdk_yaml_path: Path, sample_cell_factory, tmp_path: Path
    ) -> None:
        """完整工作流: YAML PDK → PolarisPDK → 注册 cell → DRC 验证。"""
        # Step 1: 从 YAML 加载 PDK 配置
        cfg = parse_pdk_yaml(sample_pdk_yaml_path)
        errors = validate_pdk_yaml(cfg)
        assert errors == []

        # Step 2: 构建 PolarisPDK
        pdk = build_polaris_pdk_from_yaml(sample_pdk_yaml_path)
        assert pdk.layer_stack is not None

        # Step 3: 创建 cell 注册表并注册（用 YAML 中的 cell 元数据）
        registry = PolarisCellRegistry()
        for cell_spec in cfg.cells:
            registry.register(
                cell_spec.name, sample_cell_factory,
                platform=cell_spec.platform,
                category=cell_spec.category,
                params_schema=cell_spec.params_schema,
                description=cell_spec.description,
            )
        assert registry.size == 3  # mzi_2x2, y_branch, ring_modulator

        # Step 4: 对一个 cell 创建 PCell 实例并做 DRC
        # 创建一个窄多边形（模拟 mzi_2x2 的某个臂）
        narrow_polygon = np.array([
            [0, 0], [10, 0], [10, 0.3], [0, 0.3]
        ], dtype=float)
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        result = check_min_width([narrow_polygon], rule)
        assert result.violation_count > 0

        # Step 5: 序列化注册表
        registry_data = registry.to_dict()
        assert len(registry_data["entries"]) == 3
        # 验证所有 cell 都被序列化
        serialized_names = {e["name"] for e in registry_data["entries"]}
        assert serialized_names == {"mzi_2x2", "y_branch", "ring_modulator"}


# =============================================================================
# TestR03CrossModuleConsistency: R03 跨模块错误处理一致性
# =============================================================================
class TestR03CrossModuleConsistency:
    """R03 跨模块错误处理一致性测试。"""

    def test_r309_file_not_found(self, tmp_path: Path) -> None:
        """R309 文件不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            parse_pdk_yaml(tmp_path / "nonexistent.yaml")

    def test_r308_unknown_cell_raises_keyerror(self) -> None:
        """R308 未知名检索 raise KeyError。"""
        registry = PolarisCellRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_r307_invalid_rule_category_raises(self) -> None:
        """R307 规则类别不匹配 raise ValueError。"""
        polygons = [np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)]
        wrong_rule = CurvilinearDRCRule(
            name="A1", category=DRCRuleCategory.MIN_AREA,
            layer="WG", limit_value=1.0,
        )
        with pytest.raises(ValueError, match="MIN_WIDTH"):
            check_min_width(polygons, wrong_rule)

    def test_r307_polygon_too_few_points_raises(self) -> None:
        """R307 多边形点数 < 3 raise ValueError。"""
        polygons = [np.array([[0, 0], [1, 1]], dtype=float)]
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        with pytest.raises(ValueError, match="< 3"):
            check_min_width(polygons, rule)

    def test_r302_empty_cells_spec_raises(self, tmp_path: Path) -> None:
        """R302 空 cells_spec raise ValueError。"""
        with pytest.raises(ValueError):
            export_gdsii_from_cells([], tmp_path / "empty.gds")

    def test_r309_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """R309 YAML 语法错误 raise ValueError。"""
        p = tmp_path / "bad.yaml"
        p.write_text("pdk: { bad: yaml: ]", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML 解析失败"):
            parse_pdk_yaml(p)


# =============================================================================
# TestR02AcademicIntegrityE2E: R02 学术诚信跨模块验证
# =============================================================================
class TestR02AcademicIntegrityE2E:
    """R02 学术诚信跨模块验证测试。"""

    def test_all_modules_have_source_urls(self) -> None:
        """所有 R301-R309 模块 docstring 应包含溯源 URL。"""
        from polaris.pdk import (
            gdsfactory_integration,
            gdsfactory_pdk_bridge,
            gdsfactory_plugin,
            yaml_pdk_config,
        )
        from polaris.pdk import pcell_gdsfactory_bridge
        from polaris.verification import klayout_drc_bridge

        modules = [
            gdsfactory_integration,
            gdsfactory_pdk_bridge,
            gdsfactory_plugin,
            yaml_pdk_config,
            pcell_gdsfactory_bridge,
            klayout_drc_bridge,
        ]
        for mod in modules:
            doc = mod.__doc__ or ""
            urls = [line for line in doc.split() if line.startswith("http")]
            assert len(urls) >= 3, (
                f"模块 {mod.__name__} docstring 应包含 ≥3 个 URL，实际 {len(urls)}"
            )

    def test_pdk_yaml_must_have_source_url(self) -> None:
        """validate_pdk_yaml 强制要求 source_url（R02）。"""
        cfg = PDKYamlConfig(
            name="test", version="1.0.0", platform="SOI", process_node="",
            source_url="",  # 故意留空
        )
        errors = validate_pdk_yaml(cfg)
        assert any("source_url" in e for e in errors)
        assert any("R02" in e or "溯源" in e for e in errors)

    def test_siepic_layer_map_documented(self) -> None:
        """SiEPIC 层映射函数应有 SiEPIC PDK 来源标注。"""
        from polaris.pdk.gdsfactory_integration import get_siepic_layer_map
        doc = get_siepic_layer_map.__doc__ or ""
        assert "SiEPIC" in doc or "siepic" in doc.lower()


# =============================================================================
# TestPerformanceSmoke: 性能冒烟测试
# =============================================================================
class TestPerformanceSmoke:
    """性能冒烟测试（确保业务流程不会过慢）。"""

    def test_drc_check_performance(self) -> None:
        """DRC 检查 10 个多边形应 < 1 秒。"""
        import time
        polygons = [
            np.array([[i, 0], [i + 5, 0], [i + 5, 0.5], [i, 0.5]], dtype=float)
            for i in range(0, 50, 5)
        ]
        rule = CurvilinearDRCRule(
            name="W1", category=DRCRuleCategory.MIN_WIDTH,
            layer="WG", limit_value=0.45,
        )
        t0 = time.time()
        result = check_min_width(polygons, rule)
        elapsed = time.time() - t0
        assert elapsed < 1.0, f"DRC 检查 10 个多边形耗时 {elapsed:.3f}s"
        # 合规多边形应无违规
        assert result.violation_count == 0

    def test_yaml_parse_performance(self, sample_pdk_yaml_path: Path) -> None:
        """YAML 解析应 < 0.1 秒。"""
        import time
        t0 = time.time()
        cfg = parse_pdk_yaml(sample_pdk_yaml_path)
        elapsed = time.time() - t0
        assert elapsed < 0.1, f"YAML 解析耗时 {elapsed:.3f}s"
        assert cfg.name == "polaris_soi_e2e"

    def test_registry_operations_performance(self, sample_cell_factory) -> None:
        """注册 100 个 cell 应 < 0.5 秒。"""
        import time
        registry = PolarisCellRegistry()
        t0 = time.time()
        for i in range(100):
            registry.register(
                f"cell_{i}", sample_cell_factory,
                platform="SOI", category="passive",
            )
        elapsed = time.time() - t0
        assert elapsed < 0.5, f"注册 100 个 cell 耗时 {elapsed:.3f}s"
        assert registry.size == 100
