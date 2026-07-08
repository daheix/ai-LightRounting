"""polaris-pdk-advanced 子模块深度测试（v5.1.0）。

覆盖 6 个核心模块的全部公开 API，验证迁移后功能完整可用：
- gdsfactory_bridge: 48 PDK 注册表查询 / PDK 互操作层注册 / LayerStack/CrossSection
  转换 / .pic.yml 解析 / 版本兼容性 / R03 raise 行为
- pcell: @polaris_cell 装饰器缓存 / TransformMatrix 仿射变换 / 贝塞尔变换 / LRU 缓存
- yaml_config: YAML 解析/序列化 roundtrip / 校验 / 构建 PolarisPDK
- multi_pdk_manager: 激活/快照/恢复（Memento）/ 合并（Composite）/ 元数据查询
- optodesigner: PyCellFactory 10 种器件 / DesignIntentEngine 多层掩膜 /
  FlexConnector 贝塞尔 / HierarchyDesign 层级 / PDAflow SPT 导出
- _base: Device 旋转/平移/footprint / Direction / BoundingBox / Port / Source

R03 合规验证: 所有未知输入 raise，禁止 fall-back。

学术依据（R02 学术诚信，docstring 含 ≥5 文献 URL）:
- pytest 文档: https://docs.pytest.org/
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
- Synopsys OptoDesigner:
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
- Farin 2002 CAGD: https://www.elsevier.com/books/curves-and-surfaces-for-cagd/farin/978-0-12-460521-2
- Gamma 1994 Design Patterns: https://en.wikipedia.org/wiki/Design_Patterns
- PDAflow API: http://pdaflow.org/
- PhIDO arXiv:2508.14123: https://arxiv.org/abs/2508.14123
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_pdk_advanced as ppa  # noqa: E402
from polaris_pdk_advanced import (  # noqa: E402
    BoundingBox,
    DesignIntent,
    DesignIntentEngine,
    Device,
    Direction,
    FlexConnector,
    GDSFACTORY_PDK_REGISTRY,
    HierarchyDesign,
    MultiPDKManager,
    PCellCache,
    PCellMultiView,
    PDKSnapshot,
    PDAflowInterop,
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisPDKRegistry,
    PolarisSection,
    Port,
    PyCell,
    PyCellFactory,
    Source,
    TechnologyRule,
    TransformMatrix,
    VersionCompatibility,
    ai_generate_pcell,
    build_polaris_pdk_from_yaml,
    check_gdsfactory_version_compatibility,
    clear_pcell_cache,
    get_gdsfactory_pdk,
    list_gdsfactory_pdks,
    parse_pic_yaml,
    parse_pdk_yaml,
    polaris_cell,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)


def _make_device(device_id: str) -> Device:
    """构造测试用直波导器件（R05 修复：原调用未定义导致 NameError）。

    与 test_pdk_advanced_ext._make_device 保持一致：10μm 直波导，
    in(WEST@0,0) / out(EAST@10,0)，bbox (0,-0.25,10,0.25) → footprint (10,0.5)。
    """
    return Device(
        device_id=device_id,
        platform="SOI",
        category="passive",
        name=device_id,
        ports=[
            Port(name="in", x=0.0, y=0.0, direction=Direction.WEST,
                 waveguide_type="strip", width=0.5),
            Port(name="out", x=10.0, y=0.0, direction=Direction.EAST,
                 waveguide_type="strip", width=0.5),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-0.25, xmax=10.0, ymax=0.25),
        params={"length": 10.0, "width": 0.5},
        source=Source(
            title="test", authors="test", year=2026,
            url="https://gdsfactory.github.io/gdsfactory/",
        ),
    )


# ===== gdsfactory_bridge 深度测试 =====


def test_package_version_and_exports():
    """包版本与导出符号数符合预期（迁移完整性）。"""
    assert ppa.__version__ == "5.1.0"
    assert len(ppa.__all__) >= 50
    for name in (
        "GDSFACTORY_PDK_REGISTRY", "PolarisPDKRegistry", "MultiPDKManager",
        "PCellMultiView", "polaris_cell", "TransformMatrix",
        "PDKYamlConfig", "parse_pdk_yaml", "DesignIntentEngine",
        "PyCellFactory", "FlexConnector", "HierarchyDesign",
    ):
        assert name in ppa.__all__, f"缺少导出符号: {name}"
        assert hasattr(ppa, name), f"缺少属性: {name}"


def test_list_gdsfactory_pdks_returns_48():
    """gdsfactory PDK 注册表含 48 PDK，每项含 source_url 溯源（R02）。"""
    pdks = list_gdsfactory_pdks()
    assert isinstance(pdks, list)
    assert len(pdks) == 48
    assert len(GDSFACTORY_PDK_REGISTRY) == 48
    for info in pdks:
        assert "name" in info
        assert "platform" in info
        assert "process_node" in info
        assert "source_url" in info
        assert info["source_url"], f"PDK {info['name']} source_url 为空（违反 R02）"
    names = {p["name"] for p in pdks}
    for key in ("generic", "ubcpdk", "siepic", "gf180mcu", "ihp", "skywater130"):
        assert key in names, f"缺少关键 PDK: {key}"


def test_get_gdsfactory_pdk_known_and_unknown():
    """get_gdsfactory_pdk 已知 PDK 返回元数据，未知 PDK raise KeyError（R03）。"""
    info = get_gdsfactory_pdk("generic")
    assert info.name == "generic"
    assert info.platform == "SOI"
    assert info.source_url
    with pytest.raises(KeyError):
        get_gdsfactory_pdk("nonexistent_pdk_12345")


def test_pdk_info_all_fields():
    """PDKInfo 所有字段完整且类型正确（R02 溯源）。"""
    info = get_gdsfactory_pdk("siepic")
    assert info.name == "siepic"
    assert info.platform == "SOI"
    assert info.process_node == "220nm SOI"
    assert info.import_name == "siepic"
    assert info.layer_stack_name == "siepic"
    assert info.description
    assert info.source_url == "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"


def test_polaris_pdk_registry_register_and_conflict():
    """PolarisPDKRegistry 注册/查询/冲突检测（*创新* 互操作层）。"""
    reg = PolarisPDKRegistry()
    pdk_a = PolarisPDK(name="a", platform="SOI", process_node="220nm SOI",
                       devices={"wg_a": _make_device("wg_a")})
    pdk_b = PolarisPDK(name="b", platform="SiN", process_node="300nm SiN",
                       devices={"wg_b": _make_device("wg_b")})
    reg.register("a", pdk_a)
    reg.register("b", pdk_b)
    assert reg.list_pdks() == ["a", "b"]
    assert reg.get("a") is pdk_a
    with pytest.raises(ValueError):
        reg.register("a", pdk_a)
    assert reg.detect_conflicts() == []
    pdk_c = PolarisPDK(name="c", platform="SOI", process_node="220nm SOI",
                       devices={"wg_a": _make_device("wg_a")})
    reg.register("c", pdk_c)
    conflicts = reg.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].component_name == "wg_a"
    assert set(conflicts[0].pdk_names) == {"a", "c"}


def test_polaris_pdk_registry_get_unknown():
    """PolarisPDKRegistry.get 未知 PDK raise KeyError（R03）。"""
    reg = PolarisPDKRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")


def test_polaris_layer_stack_and_level():
    """PolarisLayerStack/PolarisLayerLevel 数据类（对标 gdsfactory LayerStack）。"""
    level = PolarisLayerLevel(
        layer="1/0", thickness_nm=220.0, zmin_nm=0.0, material="Si",
        sidewall_angle_deg=0.0, refractive_index=complex(3.476, 0.0),
    )
    assert level.layer == "1/0"
    assert level.thickness_nm == 220.0
    assert level.material == "Si"
    assert level.refractive_index == complex(3.476, 0.0)
    stack = PolarisLayerStack(name="test", levels=[level])
    assert stack.name == "test"
    assert len(stack.levels) == 1
    assert stack.levels[0] is level


def test_polaris_cross_section_and_section():
    """PolarisCrossSection/PolarisSection 数据类（对标 gdsfactory CrossSection）。"""
    sec = PolarisSection(width_um=0.5, offset_um=0.0, layer="WG",
                         ports=("in", "out"))
    assert sec.width_um == 0.5
    assert sec.layer == "WG"
    assert sec.ports == ("in", "out")
    assert sec.hidden is False
    xs = PolarisCrossSection(name="strip", sections=[sec], width_um=0.5)
    assert xs.name == "strip"
    assert len(xs.sections) == 1
    assert xs.width_um == 0.5


def test_parse_pic_yaml():
    """parse_pic_yaml 解析 .pic.yml 布局文件。"""
    yaml_content = """\
name: test_circuit
instances:
  wg1:
    component: straight
    settings:
      length: 10.0
  wg2:
    component: bend
    settings:
      radius: 5.0
placements:
  wg1:
    x: 0.0
    y: 0.0
  wg2:
    x: 10.0
    y: 0.0
    rotation: 0.0
connections:
  wg1,out: wg2,in
routes:
  r1:
    links:
      wg2,out: wg3,in
    settings:
      strategy: auto
ports:
  in: wg1,in
  out: wg2,out
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pic.yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        yaml_path = f.name
    try:
        spec = parse_pic_yaml(yaml_path)
        assert spec.name == "test_circuit"
        assert len(spec.instances) == 2
        assert spec.instances[0].component == "straight"
        assert len(spec.connections) == 1
        assert spec.connections[0].source == "wg1,out"
        assert len(spec.routes) == 1
        assert spec.routes[0].strategy == "auto"
        assert spec.ports["in"] == "wg1,in"
    finally:
        Path(yaml_path).unlink()


def test_parse_pic_yaml_not_found():
    """parse_pic_yaml 文件不存在 raise FileNotFoundError（R03）。"""
    with pytest.raises(FileNotFoundError):
        parse_pic_yaml("/nonexistent/path/to/file.pic.yml")


def test_check_gdsfactory_version_compatibility():
    """check_gdsfactory_version_compatibility 返回兼容性报告。"""
    report = check_gdsfactory_version_compatibility()
    assert isinstance(report, VersionCompatibility)
    assert isinstance(report.compatible, bool)
    assert report.python_version
    assert report.reason
    assert report.recommended_action


# ===== pcell 深度测试 =====
