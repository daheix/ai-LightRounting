"""gdsfactory PDK 桥接模块测试（R09 路标）。

验证 gdsfactory_pdk_bridge 模块：PDKInfo/注册表（48 PDK）、LayerStack/CrossSection
转换、.pic.yml YAML 解析、PolarisPDKRegistry（【创新】）、反向转换（【创新】）、
版本兼容检测（【创新】）、无 fall-back AST 检查（规则 14.1）。

gdsfactory 8.18.0 在 Python 3.14 不可用（pydantic<2.10 锁定），转换函数测试
验证 raise ImportError 行为。Python 3.10-3.13 下 gdsfactory 可用时转换测试自动启用。

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- 规则 14.1 无 fall-back / 规则 18 学术诚信: .trae/rules/project_rules.md
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.gdsfactory_pdk_bridge import (
    _HAS_GDSFACTORY,
    GDSFACTORY_PDK_REGISTRY,
    PDKConflict,
    PDKInfo,
    PicYamlConnection,
    PicYamlInstance,
    PicYamlRoute,
    PicYamlSpec,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    VersionCompatibility,
    check_gdsfactory_version_compatibility,
    convert_crosssection,
    convert_layerstack,
    parse_pic_yaml,
    polaris_to_gdsfactory_component,
)
from polaris.pdk.port import Direction, Port

# ==================== 1. PDKInfo + 注册表测试（规则 18 溯源） ====================


def test_pdk_info_creation_and_frozen():
    """PDKInfo 应正确创建且 frozen 不可变。"""
    info = PDKInfo(
        name="test", platform="SOI", process_node="220nm", import_name="t",
        layer_stack_name="ts", description="测试", source_url="https://example.com/",
    )
    assert info.name == "test" and info.source_url.startswith("https://")
    with pytest.raises((AttributeError, TypeError)):
        info.name = "y"  # type: ignore[misc]


def test_registry_has_48_pdks():
    """GDSFACTORY_PDK_REGISTRY 应包含 48 个 PDK（R09 要求 43+，实际交付 48）。"""
    assert len(GDSFACTORY_PDK_REGISTRY) == 48
    assert len(GDSFACTORY_PDK_REGISTRY) >= 43


@pytest.mark.parametrize("pdk_name", ["generic", "ubcpdk", "gf180mcu", "ihp", "skywater130"])
def test_registry_contains_key_pdks(pdk_name):
    """注册表应包含核心 PDK。"""
    assert pdk_name in GDSFACTORY_PDK_REGISTRY
    info = GDSFACTORY_PDK_REGISTRY[pdk_name]
    assert all([info.name, info.platform, info.process_node,
                info.import_name, info.layer_stack_name, info.description])


def test_registry_all_pdks_have_valid_source_url():
    """所有 PDK 必须有有效 source_url（规则 18 学术诚信，禁止假数据）。"""
    for name, info in GDSFACTORY_PDK_REGISTRY.items():
        assert info.source_url.startswith(("http://", "https://")), (
            f"PDK '{name}' source_url 无效: {info.source_url}")


def test_registry_generic_info():
    """generic PDK 元数据应正确。"""
    info = GDSFACTORY_PDK_REGISTRY["generic"]
    assert info.platform == "SOI" and info.import_name == "gdsfactory"


# ==================== 2. LayerStack/CrossSection dataclass 测试 ====================


def test_layer_and_section_dataclasses():
    """PolarisLayerLevel/PolarisLayerStack/PolarisSection/PolarisCrossSection 应正确创建。"""
    level = PolarisLayerLevel(
        layer="WG", thickness_nm=220.0, zmin_nm=0.0, material="Si",
        refractive_index=complex(3.476, 0.0),
    )
    assert level.sidewall_angle_deg == 0.0
    assert level.refractive_index == complex(3.476, 0.0)
    stack = PolarisLayerStack(name="generic", levels=[level])
    assert stack.name == "generic" and len(stack.levels) == 1
    sec = PolarisSection(width_um=0.5, offset_um=0.0, layer="WG")
    assert sec.ports is None and sec.hidden is False
    xs = PolarisCrossSection(name="strip", sections=[sec], width_um=0.5)
    assert xs.name == "strip" and len(xs.sections) == 1


# ==================== 3. convert_* 测试（规则 14.1 无 fall-back） ====================

@pytest.mark.skipif(_HAS_GDSFACTORY, reason="gdsfactory 已安装，跳过 ImportError 测试")
def test_convert_funcs_raise_import_error():
    """gdsfactory 不可用时 convert_* 必须 raise ImportError（规则 14.1）。"""
    with pytest.raises(ImportError, match="gdsfactory 不可用"):
        convert_layerstack(None)
    with pytest.raises(ImportError, match="gdsfactory 不可用"):
        convert_crosssection(None)


@pytest.mark.skipif(not _HAS_GDSFACTORY, reason="gdsfactory 未安装")
def test_convert_layerstack_real():
    """gdsfactory 可用时转换真实 LayerStack。

    gdsfactory 9.44.0 API: 需先激活 PDK，再用 pdk.get_layer_stack()。
    """
    import gdsfactory as gf

    gf.gpdk.PDK.activate()
    pdk = gf.get_active_pdk()
    result = convert_layerstack(pdk.get_layer_stack())
    assert isinstance(result, PolarisLayerStack) and len(result.levels) > 0


@pytest.mark.skipif(not _HAS_GDSFACTORY, reason="gdsfactory 未安装")
def test_convert_crosssection_real():
    """gdsfactory 可用时转换真实 CrossSection。"""
    import gdsfactory as gf

    result = convert_crosssection(gf.cross_section.strip())
    assert isinstance(result, PolarisCrossSection)


# ==================== 4. YAML 解析测试 ====================

def test_parse_pic_yaml_basic(tmp_path):
    """parse_pic_yaml 应正确解析 instances/placements/connections/ports。"""
    yaml_file = tmp_path / "test.pic.yml"
    yaml_file.write_text(
        "name: test_circuit\n"
        "instances:\n"
        "  mmi1:\n    component: mmi1x2\n    settings:\n      width_mmi: 4.5\n"
        "  wg1:\n    component: straight\n"
        "placements:\n"
        "  mmi1:\n    x: 0\n    y: 0\n"
        "  wg1:\n    x: 20\n    y: 10\n    rotation: 90\n    mirror: true\n"
        "connections:\n  mmi1,o2: wg1,o1\n"
        "ports:\n  o1: mmi1,o1\n",
        encoding="utf-8",
    )
    spec = parse_pic_yaml(yaml_file)
    assert spec.name == "test_circuit"
    assert len(spec.instances) == 2
    assert spec.instances[0].component == "mmi1x2"
    assert spec.instances[0].settings["width_mmi"] == 4.5
    wg1 = spec.instances[1]
    assert wg1.x == 20.0 and wg1.y == 10.0 and wg1.rotation == 90.0 and wg1.mirror is True
    assert len(spec.connections) == 1
    assert spec.connections[0].source == "mmi1,o2"
    assert spec.ports["o1"] == "mmi1,o1"


def test_parse_pic_yaml_routes(tmp_path):
    """parse_pic_yaml 应正确解析 routes 段。"""
    yaml_file = tmp_path / "routed.pic.yml"
    yaml_file.write_text(
        "name: routed\n"
        "instances:\n  mmi1:\n    component: mmi1x2\n  mmi2:\n    component: mmi1x2\n"
        "routes:\n  route1:\n    links:\n      mmi1,o2: mmi2,o1\n"
        "    settings:\n      strategy: auto\n",
        encoding="utf-8",
    )
    spec = parse_pic_yaml(yaml_file)
    assert len(spec.routes) == 1
    assert spec.routes[0].source == "mmi1,o2"
    assert spec.routes[0].strategy == "auto"


def test_parse_pic_yaml_errors(tmp_path):
    """parse_pic_yaml 应对错误输入 raise（规则 14.1 无 fall-back）。"""
    with pytest.raises(FileNotFoundError, match="文件不存在"):
        parse_pic_yaml("/nonexistent/file.pic.yml")
    bad = tmp_path / "bad.pic.yml"
    bad.write_text("invalid: yaml: [", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML 解析失败"):
        parse_pic_yaml(bad)
    lst = tmp_path / "list.pic.yml"
    lst.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="顶层应为字典"):
        parse_pic_yaml(lst)


def test_parse_pic_yaml_name_defaults_to_stem(tmp_path):
    """parse_pic_yaml 无 name 时应使用文件名 stem。"""
    yaml_file = tmp_path / "my_circuit.pic.yml"
    yaml_file.write_text("instances:\n  c1:\n    component: straight\n", encoding="utf-8")
    assert parse_pic_yaml(yaml_file).name == "my_circuit"


# ==================== 5. PolarisPDKRegistry 测试（【创新】） ====================

def _make_test_device(device_id: str = "test_dev") -> Device:
    """创建测试用 Device（真实数据）。"""
    return Device(
        device_id=device_id, platform="SOI", category="passive", name="straight",
        ports=[
            Port(name="o1", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type="strip", width=0.5),
            Port(name="o2", x=10.0, y=0.0, direction=Direction.EAST,
                 waveguide_type="strip", width=0.5),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-0.25, xmax=10.0, ymax=0.25),
    )


def test_polaris_pdk_and_conflict_creation():
    """PolarisPDK/PDKConflict 应正确创建。"""
    dev = _make_test_device()
    pdk = PolarisPDK(
        name="pdk1", platform="SOI", process_node="220nm SOI", devices={"straight": dev},
    )
    assert pdk.name == "pdk1" and "straight" in pdk.devices
    assert pdk.layer_stack is None and pdk.cross_sections == {}
    c = PDKConflict(pdk_names=["a", "b"], component_name="x", description="desc")
    assert c.pdk_names == ["a", "b"] and c.component_name == "x"


def test_registry_register_get_list():
    """PolarisPDKRegistry 应支持注册/获取/列表（排序）。"""
    registry = PolarisPDKRegistry()
    pdk = PolarisPDK(name="pdk1", platform="SOI", process_node="220nm")
    registry.register("pdk1", pdk)
    assert registry.get("pdk1") is pdk
    registry.register("zebra", PolarisPDK(name="z", platform="SOI", process_node="220nm"))
    registry.register("alpha", PolarisPDK(name="a", platform="SiN", process_node="300nm"))
    assert registry.list_pdks() == ["alpha", "pdk1", "zebra"]


def test_registry_register_duplicate_raises():
    """重复注册应 raise ValueError（规则 14.1 无 fall-back）。"""
    registry = PolarisPDKRegistry()
    registry.register("pdk1", PolarisPDK(name="pdk1", platform="SOI", process_node="220nm"))
    with pytest.raises(ValueError, match="已注册"):
        registry.register("pdk1", PolarisPDK(name="pdk1", platform="SOI", process_node="220nm"))


def test_registry_get_nonexistent_raises():
    """获取不存在的 PDK 应 raise KeyError。"""
    with pytest.raises(KeyError, match="未注册"):
        PolarisPDKRegistry().get("nonexistent")


def test_registry_detect_conflicts_internal():
    """detect_conflicts 应检测自身内部组件名冲突（【创新】命名空间隔离）。"""
    registry = PolarisPDKRegistry()
    dev = _make_test_device()
    registry.register("pdk1", PolarisPDK(
        name="pdk1", platform="SOI", process_node="220nm", devices={"straight": dev}))
    registry.register("pdk2", PolarisPDK(
        name="pdk2", platform="SiN", process_node="300nm", devices={"straight": dev}))
    conflicts = registry.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].component_name == "straight"
    assert "pdk1" in conflicts[0].pdk_names and "pdk2" in conflicts[0].pdk_names


def test_registry_detect_conflicts_none():
    """无冲突时 detect_conflicts 应返回空列表。"""
    registry = PolarisPDKRegistry()
    dev = _make_test_device()
    registry.register("pdk1", PolarisPDK(
        name="pdk1", platform="SOI", process_node="220nm", devices={"straight": dev}))
    registry.register("pdk2", PolarisPDK(
        name="pdk2", platform="SiN", process_node="300nm", devices={"bend": dev}))
    assert len(registry.detect_conflicts()) == 0


def test_registry_detect_conflicts_cross():
    """detect_conflicts 应检测跨注册表冲突（【创新】）。"""
    r1, r2 = PolarisPDKRegistry(), PolarisPDKRegistry()
    dev = _make_test_device()
    r1.register("pdk1", PolarisPDK(
        name="pdk1", platform="SOI", process_node="220nm", devices={"straight": dev}))
    r2.register("pdk2", PolarisPDK(
        name="pdk2", platform="SiN", process_node="300nm", devices={"straight": dev}))
    conflicts = r1.detect_conflicts(r2)
    assert len(conflicts) == 1 and conflicts[0].component_name == "straight"


# ==================== 6. 反向转换 + 版本兼容测试（【创新】） ====================

@pytest.mark.skipif(_HAS_GDSFACTORY, reason="gdsfactory 已安装，跳过 ImportError 测试")
def test_polaris_to_gdsfactory_component_raises_import_error():
    """gdsfactory 不可用时反向转换必须 raise ImportError（规则 14.1）。"""
    with pytest.raises(ImportError, match="gdsfactory 不可用"):
        polaris_to_gdsfactory_component(_make_test_device())


@pytest.mark.skipif(not _HAS_GDSFACTORY, reason="gdsfactory 未安装")
def test_polaris_to_gdsfactory_component_real():
    """gdsfactory 可用时反向转换应生成 Component。"""
    dev = _make_test_device("test_reverse")
    comp = polaris_to_gdsfactory_component(dev)
    assert comp.info["polaris_device_id"] == "test_reverse"
    assert comp.info["polaris_platform"] == "SOI"


def test_version_compatibility_creation_and_check():
    """VersionCompatibility 应正确创建，check 函数应返回完整报告。"""
    vc = VersionCompatibility(
        compatible=True, python_version="3.12.0", gdsfactory_version="8.18.0",
        reason="测试", recommended_action="建议",
    )
    assert vc.compatible is True and vc.python_version == "3.12.0"
    report = check_gdsfactory_version_compatibility()
    assert isinstance(report, VersionCompatibility)
    assert isinstance(report.compatible, bool)
    assert report.python_version and report.reason and report.recommended_action
    if sys.version_info >= (3, 14) and not _HAS_GDSFACTORY:
        assert report.compatible is False
        assert "pydantic" in report.reason or "3.14" in report.reason


# ==================== 7. 无 fall-back AST 检查（规则 14.1） ====================

def _read_module_source() -> str:
    """读取 gdsfactory_pdk_bridge.py 源码。"""
    module_path = (
        Path(__file__).parent.parent / "src" / "polaris" / "pdk" / "gdsfactory_pdk_bridge.py"
    )
    return module_path.read_text(encoding="utf-8")


def test_no_fallback_silent_except():
    """模块源码不应包含静默 except（except: pass / return None，规则 14.1）。"""
    tree = ast.parse(_read_module_source())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for stmt in node.body:
                if isinstance(stmt, ast.Pass):
                    violations.append(f"行 {node.lineno}: except pass（静默兜底）")
                elif isinstance(stmt, ast.Return) and stmt.value is None:
                    violations.append(f"行 {node.lineno}: except return None（静默兜底）")
    assert not violations, "发现 fall-back 静默兜底（规则 14.1 违规）:\n" + "\n".join(violations)


def test_convert_funcs_call_ensure_available():
    """convert_*/polaris_to_* 函数必须调用 _ensure_gdsfactory_available（确保 raise 路径）。"""
    tree = ast.parse(_read_module_source())
    convert_funcs = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
        and (n.name.startswith("convert_") or n.name.startswith("polaris_to_"))
    ]
    assert len(convert_funcs) >= 3, "应至少有 3 个 convert_*/polaris_to_* 函数"
    for func in convert_funcs:
        has_ensure = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "_ensure_gdsfactory_available"
            for n in ast.walk(func)
        )
        assert has_ensure, (
            f"函数 {func.name} 未调用 _ensure_gdsfactory_available（规则 14.1 违规）"
        )


# ==================== 8. 模块导出 + PicYaml dataclass 测试 ====================

def test_module_all_symbols_importable():
    """模块所有公开符号应可导入。"""
    from polaris.pdk import gdsfactory_pdk_bridge as mod

    expected = [
        "PDKInfo", "GDSFACTORY_PDK_REGISTRY", "PolarisLayerLevel", "PolarisLayerStack",
        "convert_layerstack", "PolarisSection", "PolarisCrossSection", "convert_crosssection",
        "PicYamlInstance", "PicYamlConnection", "PicYamlRoute", "PicYamlSpec", "parse_pic_yaml",
        "PolarisPDK", "PDKConflict", "PolarisPDKRegistry", "polaris_to_gdsfactory_component",
        "VersionCompatibility", "check_gdsfactory_version_compatibility",
    ]
    for sym in expected:
        assert hasattr(mod, sym), f"模块缺少公开符号: {sym}"


def test_pic_yaml_dataclasses_creation():
    """PicYaml* dataclass 应正确创建。"""
    inst = PicYamlInstance(component="mmi1x2")
    assert inst.component == "mmi1x2" and inst.settings == {} and inst.x == 0.0
    conn = PicYamlConnection(source="a,o1", destination="b,o2")
    assert conn.source == "a,o1"
    route = PicYamlRoute(source="a,o1", destination="b,o2")
    assert route.strategy == "auto"
    spec = PicYamlSpec(instances=[inst], connections=[conn], routes=[route], ports={"o1": "a,o1"})
    assert len(spec.instances) == 1 and spec.name == ""
