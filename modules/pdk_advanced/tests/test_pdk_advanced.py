"""polaris-pdk-advanced 子模块 smoke test（v5.1.0）。

覆盖 6 个核心模块的关键 API，验证迁移后功能完整可用：
- gdsfactory_bridge: 48 PDK 注册表查询 / PDK 互操作层注册 / R03 raise 行为
- pcell: @polaris_cell 装饰器缓存 / TransformMatrix 仿射变换 / 贝塞尔变换
- yaml_config: YAML 解析/序列化 roundtrip / 校验 / 构建 PolarisPDK
- multi_pdk_manager: 激活/快照/恢复（Memento）/ 合并（Composite）
- optodesigner: PyCellFactory / DesignIntentEngine 多层掩膜 / FlexConnector 贝塞尔
- _base: Device 旋转/平移

R03 合规验证: get_gdsfactory_pdk 未注册时 raise KeyError，禁止 fall-back。

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
- Synopsys OptoDesigner:
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
- Farin 2002 CAGD: https://www.elsevier.com/books/curves-and-surfaces-for-cagd/farin/978-0-12-460521-2
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
    PCellMultiView,
    PDKSnapshot,
    PolarisPDK,
    PolarisPDKRegistry,
    Port,
    PyCellFactory,
    Source,
    TechnologyRule,
    TransformMatrix,
    ai_generate_pcell,
    build_polaris_pdk_from_yaml,
    clear_pcell_cache,
    get_gdsfactory_pdk,
    list_gdsfactory_pdks,
    parse_pdk_yaml,
    polaris_cell,
    serialize_pdk_yaml,
    validate_pdk_yaml,
)


# ===== gdsfactory_bridge smoke test =====


def test_package_version_and_exports():
    """包版本与导出符号数符合预期（迁移完整性）。"""
    assert ppa.__version__ == "5.1.0"
    # __all__ 含 6 个子模块的公开符号 + __version__
    assert len(ppa.__all__) >= 50
    # 关键符号均已导出
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
    # 每个 PDK 含必要字段且 source_url 非空（R02 学术诚信）
    for info in pdks:
        assert "name" in info
        assert "platform" in info
        assert "process_node" in info
        assert "source_url" in info
        assert info["source_url"], f"PDK {info['name']} source_url 为空（违反 R02）"
    # 抽样验证关键 PDK 存在
    names = {p["name"] for p in pdks}
    for key in ("generic", "ubcpdk", "siepic", "gf180mcu", "ihp", "skywater130"):
        assert key in names, f"缺少关键 PDK: {key}"


def test_get_gdsfactory_pdk_known_and_unknown():
    """get_gdsfactory_pdk 已知 PDK 返回元数据，未知 PDK raise KeyError（R03）。"""
    info = get_gdsfactory_pdk("generic")
    assert info.name == "generic"
    assert info.platform == "SOI"
    assert info.source_url  # 非空
    # 未知 PDK raise KeyError（禁止 fall-back）
    with pytest.raises(KeyError):
        get_gdsfactory_pdk("nonexistent_pdk_12345")


def test_polaris_pdk_registry_register_and_conflict():
    """PolarisPDKRegistry 注册/查询/冲突检测（*创新* 互操作层）。"""
    reg = PolarisPDKRegistry()
    # 注册两个无冲突 PDK
    pdk_a = PolarisPDK(name="a", platform="SOI", process_node="220nm SOI",
                       devices={"wg_a": _make_device("wg_a")})
    pdk_b = PolarisPDK(name="b", platform="SiN", process_node="300nm SiN",
                       devices={"wg_b": _make_device("wg_b")})
    reg.register("a", pdk_a)
    reg.register("b", pdk_b)
    assert reg.list_pdks() == ["a", "b"]
    assert reg.get("a") is pdk_a
    # 重复注册 raise ValueError（R03）
    with pytest.raises(ValueError):
        reg.register("a", pdk_a)
    # 无冲突
    assert reg.detect_conflicts() == []
    # 构造冲突：两个 PDK 含同名组件
    pdk_c = PolarisPDK(name="c", platform="SOI", process_node="220nm SOI",
                       devices={"wg_a": _make_device("wg_a")})
    reg.register("c", pdk_c)
    conflicts = reg.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].component_name == "wg_a"
    assert set(conflicts[0].pdk_names) == {"a", "c"}


# ===== pcell smoke test =====


def test_polaris_cell_decorator_caches():
    """@polaris_cell 装饰器自动缓存，相同参数返回同一实例。"""
    clear_pcell_cache()

    @polaris_cell
    def straight(width: float = 0.5, length: float = 10.0) -> PCellMultiView:
        cell = PCellMultiView(name="straight",
                              params={"width": width, "length": length})
        cell.add_polygon(
            np.array([[0, -width / 2], [length, -width / 2],
                      [length, width / 2], [0, width / 2]]),
            layer="WG",
        )
        cell.add_port("in", 0, 0, "west", width)
        cell.add_port("out", length, 0, "east", width)
        return cell

    c1 = straight(width=0.5, length=10.0)
    c2 = straight(width=0.5, length=10.0)
    assert c1 is c2  # 缓存命中，同一实例
    # 不同参数返回不同实例
    c3 = straight(width=0.6, length=10.0)
    assert c3 is not c1
    # 类型校验：传错类型 raise TypeError（R03）
    with pytest.raises(TypeError):
        straight(width="not_a_float")  # type: ignore[arg-type]
    # Observer Pattern: add_port 同步到 netlist_view
    assert "in" in c1.get_netlist()["ports"]


def test_transform_matrix_affine_and_bezier():
    """TransformMatrix 仿射变换 + 贝塞尔曲线变换（*创新*）。"""
    # 单位矩阵
    m = TransformMatrix()
    p = m.apply(np.array([1.0, 2.0]))
    assert np.allclose(p, [1.0, 2.0])
    # 平移 + 旋转
    m2 = m.translate(10.0, 20.0).rotate(90.0)
    p2 = m2.apply(np.array([1.0, 0.0]))
    # 旋转 90°: (1,0)->(0,1)，再平移 (10,20) -> (10, 21)
    assert np.allclose(p2, [10.0, 21.0])
    # 逆变换
    inv = m2.inverse()
    p3 = inv.apply(p2)
    assert np.allclose(p3, [1.0, 0.0])
    # 贝塞尔变换（*创新*）：3 控制点二次贝塞尔
    cp = np.array([[0.0, 0.0], [1.0, 2.0], [2.0, 0.0]])
    pt_mid = TransformMatrix.bezier_transform(cp, 0.5)
    # B(0.5) = 0.25*P0 + 0.5*P1 + 0.25*P2 = (1.0, 1.0)
    assert np.allclose(pt_mid, [1.0, 1.0])
    # 奇异矩阵求逆 raise ValueError（R03）
    singular = TransformMatrix(a=0.0, b=0.0, c=0.0, d=0.0)
    with pytest.raises(ValueError):
        singular.inverse()


def test_ai_generate_pcell_templates():
    """ai_generate_pcell 模板匹配生成 4 种器件代码（*创新*）。"""
    # 环谐振器
    code_ring = ai_generate_pcell("半径5μm的环谐振器")
    assert "@polaris_cell" in code_ring
    assert "ring_resonator" in code_ring
    assert "radius: float = 5.0" in code_ring
    # MMI
    code_mmi = ai_generate_pcell("宽度0.5长度10的mmi")
    assert "mmi1x2" in code_mmi
    # 波导
    code_wg = ai_generate_pcell("width 0.5 length 10 waveguide")
    assert "straight_waveguide" in code_wg
    # Y 分支
    code_yb = ai_generate_pcell("width 0.5 的 Y 分支")
    assert "y_branch" in code_yb
    # 无法识别 raise ValueError（R03）
    with pytest.raises(ValueError):
        ai_generate_pcell("完全无法识别的器件描述 xyz123")


# ===== yaml_config smoke test =====


def test_yaml_pdk_roundtrip_and_validation():
    """YAML PDK 配置解析/序列化 roundtrip + 校验。"""
    yaml_content = """\
pdk:
  name: polaris_test
  version: "1.0.0"
  platform: SOI
  process_node: 220nm SOI
  description: 测试 PDK
  source_url: https://gdsfactory.github.io/gdsfactory/
layers:
  WG:
    gds_layer: 1
    gds_datatype: 0
    material: Si
    description: 波导层
  SLAB:
    gds_layer: 2
    gds_datatype: 0
    material: Si
    description: Slab 层
layer_stack:
  - layer: WG
    thickness_nm: 220.0
    zmin_nm: 0.0
    material: Si
    refractive_index: [3.476, 0.0]
  - layer: SLAB
    thickness_nm: 90.0
    zmin_nm: 0.0
    material: Si
cross_sections:
  strip:
    width_um: 0.5
    offset_um: 0.0
    sections:
      - width_um: 0.5
        offset_um: 0.0
        layer: WG
        ports: ["in", "out"]
cells:
  straight:
    platform: SOI
    category: passive
    params_schema:
      length: 10.0
      width: 0.5
    description: 直波导
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        yaml_path = f.name
    try:
        # 解析
        config = parse_pdk_yaml(yaml_path)
        assert config.name == "polaris_test"
        assert config.version == "1.0.0"
        assert config.platform == "SOI"
        assert len(config.layers) == 2
        assert len(config.layer_stack) == 2
        assert len(config.cross_sections) == 1
        assert len(config.cells) == 1
        # 折射率解析
        wg_level = next(ls for ls in config.layer_stack if ls.layer == "WG")
        assert wg_level.refractive_index_real == 3.476
        # 校验通过（无错误）
        errors = validate_pdk_yaml(config)
        assert errors == [], f"校验失败: {errors}"
        # 序列化 roundtrip
        yaml_str = serialize_pdk_yaml(config)
        assert "polaris_test" in yaml_str
        assert "220nm SOI" in yaml_str
        # 重新解析序列化结果，验证 roundtrip 一致
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f2:
            f2.write(yaml_str)
            yaml_path2 = f2.name
        try:
            config2 = parse_pdk_yaml(yaml_path2)
            assert config2.name == config.name
            assert config2.version == config.version
            assert len(config2.layers) == len(config.layers)
            assert len(config2.cells) == len(config.cells)
        finally:
            Path(yaml_path2).unlink()
    finally:
        Path(yaml_path).unlink()


def test_build_polaris_pdk_from_yaml():
    """从 YAML 构建 PolarisPDK（含 layer_stack + cross_sections）。"""
    yaml_content = """\
pdk:
  name: polaris_build
  version: "2.0.0"
  platform: SiN
  process_node: 300nm SiN
  source_url: https://www.ligentec.com/
layers:
  WG:
    gds_layer: 1
    gds_datatype: 0
    material: SiN
layer_stack:
  - layer: WG
    thickness_nm: 300.0
    zmin_nm: 0.0
    material: SiN
    refractive_index: [2.0, 0.0]
cross_sections:
  strip_sin:
    width_um: 1.0
    offset_um: 0.0
    sections:
      - width_um: 1.0
        offset_um: 0.0
        layer: WG
cells: {}
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        yaml_path = f.name
    try:
        pdk = build_polaris_pdk_from_yaml(yaml_path)
        assert pdk.name == "polaris_build"
        assert pdk.platform == "SiN"
        assert pdk.process_node == "300nm SiN"
        assert pdk.layer_stack is not None
        assert len(pdk.layer_stack.levels) == 1
        assert pdk.layer_stack.levels[0].material == "SiN"
        assert pdk.layer_stack.levels[0].refractive_index == complex(2.0, 0.0)
        assert "strip_sin" in pdk.cross_sections
        assert pdk.cross_sections["strip_sin"].width_um == 1.0
    finally:
        Path(yaml_path).unlink()


def test_yaml_validation_missing_source_url():
    """source_url 为空时校验失败（R02 学术诚信）。"""
    config = ppa.PDKYamlConfig(
        name="bad", version="1.0.0", platform="SOI",
        process_node="220nm SOI", source_url="",
    )
    errors = validate_pdk_yaml(config)
    assert any("source_url" in e for e in errors)


# ===== multi_pdk_manager smoke test =====


def test_multi_pdk_manager_activate_snapshot_restore():
    """MultiPDKManager 激活/快照/恢复（Memento Pattern）。"""
    mgr = MultiPDKManager()
    pdk1 = PolarisPDK(name="soi", platform="SOI", process_node="220nm SOI",
                      devices={"wg": _make_device("wg")})
    pdk2 = PolarisPDK(name="sin", platform="SiN", process_node="300nm SiN",
                      devices={"ring": _make_device("ring")})
    mgr.register("soi", pdk1)
    mgr.register("sin", pdk2)
    # 无激活时 get_active raise RuntimeError（R03）
    with pytest.raises(RuntimeError):
        mgr.get_active()
    # 激活 soi
    mgr.activate("soi")
    assert mgr.get_active_name() == "soi"
    assert mgr.is_active("soi")
    assert not mgr.is_active("sin")
    # 快照
    snap = mgr.snapshot(created_at=1000.0)
    assert isinstance(snap, PDKSnapshot)
    assert snap.active_pdk_name == "soi"
    # list_pdks 返回排序后的列表（sorted）
    assert snap.registered_pdk_names == ["sin", "soi"]
    assert snap.created_at == 1000.0
    # 切换激活到 sin
    mgr.activate("sin")
    assert mgr.get_active_name() == "sin"
    # 恢复快照
    mgr.restore(snap)
    assert mgr.get_active_name() == "soi"
    # 激活未注册 PDK raise KeyError（R03）
    with pytest.raises(KeyError):
        mgr.activate("nonexistent")


def test_multi_pdk_manager_merge_composite():
    """MultiPDKManager.merge 合并多 PDK（Composite Pattern，含冲突检测）。"""
    mgr = MultiPDKManager()
    pdk_a = PolarisPDK(name="a", platform="SOI", process_node="220nm",
                       devices={"wg_a": _make_device("wg_a"),
                                "ring": _make_device("ring")})
    pdk_b = PolarisPDK(name="b", platform="SiN", process_node="300nm",
                       devices={"wg_b": _make_device("wg_b")})
    mgr.register("a", pdk_a)
    mgr.register("b", pdk_b)
    # 合并无冲突 PDK
    merged = mgr.merge("merged", ["a", "b"])
    assert merged.name == "merged"
    assert len(merged.devices) == 3
    assert "wg_a" in merged.devices
    assert "wg_b" in merged.devices
    assert "ring" in merged.devices
    # 合并冲突 PDK raise ValueError（R03）
    pdk_c = PolarisPDK(name="c", platform="InP", process_node="200nm",
                       devices={"ring": _make_device("ring")})
    mgr.register("c", pdk_c)
    with pytest.raises(ValueError):
        mgr.merge("bad", ["a", "c"])
    # 空列表 raise ValueError（R03）
    with pytest.raises(ValueError):
        mgr.merge("empty", [])
    # 未注册 PDK raise ValueError（R03）
    with pytest.raises(ValueError):
        mgr.merge("bad", ["a", "nonexistent"])


# ===== optodesigner smoke test =====


def test_pycell_factory_straight_and_mmi():
    """PyCellFactory 生成 straight/mmi PyCell，含多边形与端口。"""
    factory = PyCellFactory()
    straight = factory.straight(length=10.0, width=0.5)
    assert straight.name == "straight"
    assert len(straight.polygons) == 1
    assert len(straight.ports) == 2
    assert straight.ports[0][0] == "in"
    assert straight.ports[1][0] == "out"
    assert straight.params["length"] == 10.0
    assert straight.metadata["source"]  # 非空溯源 URL
    mmi = factory.mmi_1x2(length=10.0, width=2.0)
    assert mmi.name == "mmi_1x2"
    assert len(mmi.polygons) == 1
    assert len(mmi.ports) == 3  # 1 in + 2 out
    # grating_coupler 参数校验（R03）
    with pytest.raises(ValueError):
        factory.grating_coupler(duty_cycle=1.5)
    with pytest.raises(ValueError):
        factory.grating_coupler(n_periods=0)


def test_design_intent_engine_multi_layer_masks():
    """DesignIntentEngine 单层路径→多层掩膜自动生成。"""
    intent = DesignIntent(
        path=[(0.0, 0.0), (10.0, 0.0)], width=0.5, wg_type="strip"
    )
    rules = [
        TechnologyRule(layer=(1, 0), offset=0.0, purpose="WG"),
        TechnologyRule(layer=(2, 0), offset=0.1, purpose="SLAB"),
        TechnologyRule(layer=(3, 0), offset=0.2, purpose="METAL"),
    ]
    engine = DesignIntentEngine(rules)
    masks = engine.generate_masks(intent)
    assert len(masks) == 3  # 三层掩膜
    assert (1, 0) in masks
    assert (2, 0) in masks
    assert (3, 0) in masks
    # 每层一个多边形
    for layer, polys in masks.items():
        assert len(polys) == 1
        assert len(polys[0]) >= 4  # 至少 4 个顶点构成闭合多边形
    # 空规则 raise ValueError（R03）
    with pytest.raises(ValueError):
        DesignIntentEngine([])
    # 路径点不足 raise ValueError（R03）
    with pytest.raises(ValueError):
        engine.generate_masks(DesignIntent(path=[(0.0, 0.0)], width=0.5))


def test_flex_connector_bezier_curve():
    """FlexConnector 贝塞尔曲线连接任意角度端口。"""
    fc = FlexConnector(
        start_port=(0.0, 0.0, 0.0, 0.5),
        end_port=(20.0, 10.0, 180.0, 0.5),
        path_type="bezier",
    )
    path = fc.compute_path(n_points=50)
    assert len(path) == 50
    # 起点 = start_port 前两坐标
    assert np.allclose(path[0], [0.0, 0.0])
    # 终点 = end_port 前两坐标
    assert np.allclose(path[-1], [20.0, 10.0])
    # 路径长度 > 直线距离（贝塞尔曲线弯绕）
    length = fc.compute_length()
    straight_dist = np.hypot(20.0, 10.0)
    assert length > straight_dist
    # 转 PyCell
    cell = fc.to_pycell()
    assert cell.name == "flex_connector"
    assert len(cell.polygons) == 1
    assert len(cell.ports) == 2
    # n_points < 2 raise ValueError（R03）
    with pytest.raises(ValueError):
        fc.compute_path(n_points=1)


def test_hierarchy_design_flatten_and_depth():
    """HierarchyDesign 层级嵌套 + flatten + depth。"""
    factory = PyCellFactory()
    wg = factory.straight(length=5.0, width=0.5)
    # 顶层设计
    top = HierarchyDesign("top")
    top.add_instance(wg, position=(0.0, 0.0))
    top.add_instance(wg, position=(10.0, 0.0), rotation=0.0)
    # 子设计（嵌套）
    sub = HierarchyDesign("sub")
    sub.add_instance(wg, position=(0.0, 5.0))
    top.add_sub_design(sub, position=(0.0, 0.0))
    # 层级深度 = 2（top + sub）
    assert top.hierarchy_depth() == 2
    assert top.instance_count == 3  # 2 PyCell + 1 子设计
    # flatten
    flat = top.flatten()
    assert flat.name == "top"
    # 3 个实例各 1 个多边形 = 3 个多边形
    assert len(flat.polygons) == 3
    # 3 个实例各 2 个端口 = 6 个端口
    assert len(flat.ports) == 6


# ===== _base smoke test =====


def test_device_rotate_and_translate():
    """Device 旋转/平移（返回新实例，原实例不变）。"""
    dev = _make_device("test_wg")
    original_x = dev.ports[0].x
    # 平移
    moved = dev.translate(10.0, 20.0)
    assert moved.ports[0].x == original_x + 10.0
    assert moved.ports[0].y == 20.0
    # 原实例不变
    assert dev.ports[0].x == original_x
    # 旋转 90°（逆时针，标准数学坐标系）
    rotated = dev.rotate(90.0)
    # 原 port "in" 方向 WEST，逆时针 90° 后方向 SOUTH
    # （_ROT90: WEST→SOUTH→EAST→NORTH→WEST，标准数学坐标系逆时针）
    assert rotated.ports[0].direction == Direction.SOUTH
    # 非直角旋转 raise ValueError（R03）
    with pytest.raises(ValueError):
        dev.rotate(45.0)


# ===== 辅助函数 =====


def _make_device(name: str) -> Device:
    """构造测试用 Device（直波导，2 端口）。"""
    return Device(
        device_id=name,
        platform="SOI",
        category="passive",
        name=name,
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
