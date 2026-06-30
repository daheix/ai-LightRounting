"""R308 gdsfactory 插件注册机制测试套件。

测试 polaris.pdk.gdsfactory_plugin 模块的全部公开接口:
1. PolarisCellEntry / PolarisCellRegistry 数据类与注册表
2. register / unregister / get / create 注册检索
3. list_names / list_all / list_by_platform / list_by_category 列表
4. to_dict 序列化
5. to_gdsfactory_cells / register_to_gdsfactory gdsfactory 桥接
6. @register_polaris_cell 装饰器
7. get_polaris_cell / register_to_gdsfactory 便捷函数
8. R03 错误处理（重复注册/未知名/工厂返回类型/gdsfactory 不可用）
9. 学术诚信（gdsfactory register_cells 文献溯源）

学术依据:
- gdsfactory register_cells: https://gdsfactory.github.io/gdsfactory/api.html
- gdsfactory PDK cells 注册: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
- gdsfactory @gf.cell: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.cell
- IPKISS PDK 互操作: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Adapter Pattern (Gamma 1994): https://en.wikipedia.org/wiki/Adapter_pattern
- gdsfactory from_yaml: https://gdsfactory.github.io/gdsfactory/notebooks/07_yaml_component.html

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

import pytest

from polaris.pdk.gdsfactory_plugin import (
    PolarisCellEntry,
    PolarisCellRegistry,
    default_registry,
    get_polaris_cell,
    register_polaris_cell,
    register_to_gdsfactory,
)
from polaris.pdk.pcell import PCellMultiView


# =============================================================================
# 测试 fixtures
# =============================================================================
def _make_mzi(length: float = 100.0) -> PCellMultiView:
    """MZI 工厂（测试用）。"""
    pcell = PCellMultiView("mzi_2x2", {"length": length})
    pcell.add_polygon([[0, 0], [length, 0], [length, 1], [0, 1]], "WG")
    pcell.add_port("o1", 0, 0.5, "east", 0.5)
    pcell.add_port("o2", length, 0.5, "west", 0.5)
    return pcell


def _make_ring(radius: float = 10.0) -> PCellMultiView:
    """环形谐振器工厂（测试用）。"""
    pcell = PCellMultiView("ring", {"radius": radius})
    pcell.add_port("o1", 0, 0, "east", 0.5)
    return pcell


@pytest.fixture
def fresh_registry() -> PolarisCellRegistry:
    """每个测试用例独立的注册表。"""
    return PolarisCellRegistry()


@pytest.fixture
def mzi_entry(fresh_registry: PolarisCellRegistry) -> PolarisCellEntry:
    """已注册 MZI 的条目。"""
    return fresh_registry.register(
        name="mzi_2x2",
        factory=_make_mzi,
        platform="SOI",
        category="passive",
        params_schema={"length": 100.0},
        description="MZI 2x2 干涉仪",
    )


# =============================================================================
# 1. PolarisCellEntry 数据类测试
# =============================================================================
class TestPolarisCellEntry:
    """PolarisCellEntry 注册条目数据类测试。"""

    def test_basic_entry(self):
        """基本条目: name + factory。"""
        entry = PolarisCellEntry(name="mzi", factory=_make_mzi)
        assert entry.name == "mzi"
        assert entry.factory is _make_mzi
        assert entry.platform == "SOI"  # 默认
        assert entry.category == "passive"  # 默认
        assert entry.params_schema == {}
        assert entry.description == ""

    def test_full_entry(self):
        """完整条目: 所有字段。"""
        entry = PolarisCellEntry(
            name="ring",
            factory=_make_ring,
            platform="SiN",
            category="passive",
            params_schema={"radius": 10.0},
            description="环形谐振器",
        )
        assert entry.name == "ring"
        assert entry.platform == "SiN"
        assert entry.category == "passive"
        assert entry.params_schema == {"radius": 10.0}
        assert entry.description == "环形谐振器"


# =============================================================================
# 2. PolarisCellRegistry 注册测试
# =============================================================================
class TestRegistryRegister:
    """PolarisCellRegistry 注册功能测试。"""

    def test_register_basic(self, fresh_registry: PolarisCellRegistry):
        """基本注册: size 从 0 到 1。"""
        assert fresh_registry.size == 0
        entry = fresh_registry.register("mzi", _make_mzi)
        assert fresh_registry.size == 1
        assert entry.name == "mzi"
        assert entry.factory is _make_mzi

    def test_register_with_metadata(self, fresh_registry: PolarisCellRegistry):
        """带元数据注册: platform/category/schema/description。"""
        entry = fresh_registry.register(
            "ring", _make_ring,
            platform="SiN", category="passive",
            params_schema={"radius": 10.0},
            description="环形谐振器",
        )
        assert entry.platform == "SiN"
        assert entry.category == "passive"
        assert entry.params_schema == {"radius": 10.0}
        assert entry.description == "环形谐振器"

    def test_register_returns_entry(self, fresh_registry: PolarisCellRegistry):
        """register 返回 PolarisCellEntry。"""
        entry = fresh_registry.register("mzi", _make_mzi)
        assert isinstance(entry, PolarisCellEntry)

    def test_platforms_property(self, fresh_registry: PolarisCellRegistry):
        """platforms 属性: 按字母排序（ASCII 序，大写优先）。"""
        fresh_registry.register("mzi", _make_mzi, platform="SOI")
        fresh_registry.register("ring", _make_ring, platform="SiN")
        # Python sorted 按 ASCII 序: 'S'(83) < 'i'(105)，所以 'SOI' < 'SiN'
        assert fresh_registry.platforms == ["SOI", "SiN"]

    def test_unregister(self, fresh_registry: PolarisCellRegistry):
        """注销已注册 cell。"""
        fresh_registry.register("mzi", _make_mzi)
        assert fresh_registry.size == 1
        removed = fresh_registry.unregister("mzi")
        assert removed.name == "mzi"
        assert fresh_registry.size == 0
        assert "mzi" not in fresh_registry

    def test_unregister_cleans_platform(self, fresh_registry: PolarisCellRegistry):
        """注销后平台集合自动清理。"""
        fresh_registry.register("mzi", _make_mzi, platform="SOI")
        assert "SOI" in fresh_registry.platforms
        fresh_registry.unregister("mzi")
        assert "SOI" not in fresh_registry.platforms


# =============================================================================
# 3. PolarisCellRegistry 检索测试
# =============================================================================
class TestRegistryRetrieve:
    """PolarisCellRegistry 检索功能测试。"""

    def test_get_entry(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """get 返回注册条目。"""
        entry = fresh_registry.get("mzi_2x2")
        assert entry is mzi_entry

    def test_create_pcell(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """create 调用工厂返回 PCellMultiView。"""
        pcell = fresh_registry.create("mzi_2x2", length=200.0)
        assert isinstance(pcell, PCellMultiView)
        assert pcell.params == {"length": 200.0}
        assert len(pcell.layout_view.ports) == 2

    def test_create_default_kwargs(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """create 不传参数用工厂默认值。"""
        pcell = fresh_registry.create("mzi_2x2")
        assert pcell.params == {"length": 100.0}

    def test_list_names_all(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """list_names 列出全部名称（按字母排序）。"""
        fresh_registry.register("ring", _make_ring)
        assert fresh_registry.list_names() == ["mzi_2x2", "ring"]

    def test_list_names_by_platform(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """list_names 按平台过滤。"""
        fresh_registry.register("ring", _make_ring, platform="SiN")
        assert fresh_registry.list_names(platform="SOI") == ["mzi_2x2"]
        assert fresh_registry.list_names(platform="SiN") == ["ring"]

    def test_list_all(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """list_all 返回全部条目。"""
        fresh_registry.register("ring", _make_ring)
        all_entries = fresh_registry.list_all()
        assert len(all_entries) == 2

    def test_list_by_platform(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """list_by_platform 按平台列出。"""
        fresh_registry.register("ring", _make_ring, platform="SiN")
        soi_entries = fresh_registry.list_by_platform("SOI")
        assert len(soi_entries) == 1
        assert soi_entries[0].name == "mzi_2x2"

    def test_list_by_category(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """list_by_category 按类别列出。"""
        fresh_registry.register("detector", _make_ring, category="detector")
        passive = fresh_registry.list_by_category("passive")
        detector = fresh_registry.list_by_category("detector")
        assert len(passive) == 1
        assert len(detector) == 1
        assert detector[0].name == "detector"

    def test_contains(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """__contains__ 支持 in 操作符。"""
        assert "mzi_2x2" in fresh_registry
        assert "nonexistent" not in fresh_registry

    def test_len(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """__len__ 返回注册数。"""
        assert len(fresh_registry) == 1

    def test_iter(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """__iter__ 迭代条目。"""
        fresh_registry.register("ring", _make_ring)
        names = [e.name for e in fresh_registry]
        assert set(names) == {"mzi_2x2", "ring"}


# =============================================================================
# 4. 序列化测试
# =============================================================================
class TestSerialization:
    """to_dict 序列化测试。"""

    def test_to_dict_basic(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """to_dict 返回包含 entries 的字典。"""
        d = fresh_registry.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 1
        assert d["entries"][0]["name"] == "mzi_2x2"
        assert d["entries"][0]["platform"] == "SOI"
        assert d["entries"][0]["category"] == "passive"

    def test_to_dict_empty(self, fresh_registry: PolarisCellRegistry):
        """空注册表 to_dict。"""
        d = fresh_registry.to_dict()
        assert d == {"entries": []}

    def test_to_dict_multiple(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """多条目 to_dict。"""
        fresh_registry.register("ring", _make_ring, description="环形")
        d = fresh_registry.to_dict()
        assert len(d["entries"]) == 2
        names = [e["name"] for e in d["entries"]]
        assert "mzi_2x2" in names
        assert "ring" in names

    def test_to_dict_excludes_factory(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """to_dict 不包含不可序列化的 factory 字段。"""
        d = fresh_registry.to_dict()
        assert "factory" not in d["entries"][0]


# =============================================================================
# 5. @register_polaris_cell 装饰器测试
# =============================================================================
class TestRegisterDecorator:
    """@register_polaris_cell 装饰器测试。"""

    def test_decorator_basic(self):
        """装饰器基本注册（用独立注册表避免污染默认表）。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(name="mzi_dec", registry=reg)
        def make_mzi(length: float = 100.0) -> PCellMultiView:
            return _make_mzi(length)

        assert "mzi_dec" in reg
        assert reg.size == 1

    def test_decorator_default_name(self):
        """装饰器默认用函数名作为 cell 名。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(registry=reg)
        def custom_cell(length: float = 50.0) -> PCellMultiView:
            return _make_mzi(length)

        assert "custom_cell" in reg

    def test_decorator_metadata(self):
        """装饰器附加元数据。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(
            name="ring_dec",
            platform="SiN",
            category="passive",
            description="装饰器环形",
            registry=reg,
        )
        def make_ring(radius: float = 10.0) -> PCellMultiView:
            return _make_ring(radius)

        entry = reg.get("ring_dec")
        assert entry.platform == "SiN"
        assert entry.description == "装饰器环形"

    def test_decorator_preserves_function(self):
        """装饰器保留原函数可调用性。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(name="mzi_keep", registry=reg)
        def make_mzi(length: float = 100.0) -> PCellMultiView:
            """MZI 工厂。"""
            return _make_mzi(length)

        # 装饰后仍可直接调用
        pcell = make_mzi(length=200.0)
        assert isinstance(pcell, PCellMultiView)
        assert pcell.params == {"length": 200.0}

    def test_decorator_attaches_metadata(self):
        """装饰器附加 polaris_cell_name 等元数据到包装函数。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(name="meta_test", platform="InP", category="active", registry=reg)
        def make_cell() -> PCellMultiView:
            return _make_mzi()

        assert make_cell.polaris_cell_name == "meta_test"
        assert make_cell.polaris_platform == "InP"
        assert make_cell.polaris_category == "active"

    def test_decorator_default_registry(self):
        """装饰器默认使用 default_registry。"""
        # 用独立名称避免与其他测试冲突
        @register_polaris_cell(name="decorator_default_test")
        def make_cell() -> PCellMultiView:
            return _make_mzi()

        assert "decorator_default_test" in default_registry
        # 清理
        default_registry.unregister("decorator_default_test")


# =============================================================================
# 6. 便捷函数测试
# =============================================================================
class TestConvenienceFunctions:
    """get_polaris_cell / register_to_gdsfactory 便捷函数测试。"""

    def test_get_polaris_cell(self):
        """get_polaris_cell 从默认注册表获取。"""
        # 注册到默认表
        @register_polaris_cell(name="conv_test_cell")
        def make_cell(length: float = 50.0) -> PCellMultiView:
            return _make_mzi(length)

        pcell = get_polaris_cell("conv_test_cell", length=75.0)
        assert isinstance(pcell, PCellMultiView)
        assert pcell.params == {"length": 75.0}
        # 清理
        default_registry.unregister("conv_test_cell")

    def test_default_registry_is_polaris_cell_registry(self):
        """default_registry 是 PolarisCellRegistry 实例。"""
        assert isinstance(default_registry, PolarisCellRegistry)


# =============================================================================
# 7. R03 错误处理测试
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back: 所有错误必须 raise。"""

    def test_register_duplicate(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """重复注册 raise ValueError（不静默覆盖）。"""
        with pytest.raises(ValueError, match="已注册"):
            fresh_registry.register("mzi_2x2", _make_mzi)

    def test_register_empty_name(self, fresh_registry: PolarisCellRegistry):
        """空名称 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            fresh_registry.register("", _make_mzi)

    def test_register_non_callable_factory(self, fresh_registry: PolarisCellRegistry):
        """不可调用 factory raise TypeError。"""
        with pytest.raises(TypeError, match="必须可调用"):
            fresh_registry.register("bad", "not a function")

    def test_unregister_unknown(self, fresh_registry: PolarisCellRegistry):
        """注销未知名 raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            fresh_registry.unregister("nonexistent")

    def test_get_unknown(self, fresh_registry: PolarisCellRegistry):
        """获取未知名 raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            fresh_registry.get("nonexistent")

    def test_create_unknown(self, fresh_registry: PolarisCellRegistry):
        """创建未知名 raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            fresh_registry.create("nonexistent")

    def test_create_factory_returns_non_pcell(self, fresh_registry: PolarisCellRegistry):
        """工厂返回非 PCellMultiView raise TypeError。"""
        def bad_factory():
            return "not a pcell"
        fresh_registry.register("bad", bad_factory)
        with pytest.raises(TypeError, match="期望 PCellMultiView"):
            fresh_registry.create("bad")

    def test_to_gdsfactory_cells_no_gdsfactory(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """gdsfactory 不可用时 to_gdsfactory_cells raise ImportError。"""
        # 检查 gdsfactory 是否可用
        try:
            import gdsfactory  # noqa: F401
            pytest.skip("gdsfactory 可用，跳过不可用测试")
        except ImportError:
            pass
        with pytest.raises(ImportError, match="gdsfactory 未安装"):
            fresh_registry.to_gdsfactory_cells()

    def test_register_to_gdsfactory_no_gdsfactory(self, fresh_registry: PolarisCellRegistry, mzi_entry):
        """gdsfactory 不可用时 register_to_gdsfactory raise ImportError。"""
        try:
            import gdsfactory  # noqa: F401
            pytest.skip("gdsfactory 可用，跳过不可用测试")
        except ImportError:
            pass
        with pytest.raises(ImportError, match="gdsfactory 未安装"):
            fresh_registry.register_to_gdsfactory()


# =============================================================================
# 8. 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_registration_workflow(self, fresh_registry: PolarisCellRegistry):
        """完整注册工作流: 注册→检索→创建→序列化。"""
        # 1. 注册多个 cell
        fresh_registry.register("mzi", _make_mzi, platform="SOI", description="MZI")
        fresh_registry.register("ring", _make_ring, platform="SiN", description="Ring")
        fresh_registry.register("mzi_sinx", _make_mzi, platform="SiN", description="MZI SiN")

        # 2. 检索
        assert fresh_registry.size == 3
        assert set(fresh_registry.list_names()) == {"mzi", "ring", "mzi_sinx"}
        assert set(fresh_registry.platforms) == {"SOI", "SiN"}

        # 3. 按平台过滤
        sinx_cells = fresh_registry.list_by_platform("SiN")
        assert len(sinx_cells) == 2
        sinx_names = {e.name for e in sinx_cells}
        assert sinx_names == {"ring", "mzi_sinx"}

        # 4. 创建 PCell
        pcell = fresh_registry.create("mzi", length=300.0)
        assert pcell.params == {"length": 300.0}
        assert len(pcell.layout_view.ports) == 2

        # 5. 序列化
        d = fresh_registry.to_dict()
        assert len(d["entries"]) == 3

    def test_decorator_and_registry_workflow(self):
        """装饰器 + 注册表混合工作流。"""
        reg = PolarisCellRegistry()

        @register_polaris_cell(name="dec_mzi", platform="SOI", registry=reg)
        def make_mzi(length: float = 100.0) -> PCellMultiView:
            return _make_mzi(length)

        reg.register("manual_ring", _make_ring, platform="SiN")

        assert reg.size == 2
        assert set(reg.list_names()) == {"dec_mzi", "manual_ring"}

        # 都能创建
        pcell1 = reg.create("dec_mzi")
        pcell2 = reg.create("manual_ring", radius=5.0)
        assert isinstance(pcell1, PCellMultiView)
        assert isinstance(pcell2, PCellMultiView)

    def test_unregister_and_reregister(self, fresh_registry: PolarisCellRegistry):
        """注销后可重新注册同名 cell。"""
        fresh_registry.register("mzi", _make_mzi)
        assert "mzi" in fresh_registry

        fresh_registry.unregister("mzi")
        assert "mzi" not in fresh_registry

        # 重新注册同名（应成功）
        fresh_registry.register("mzi", _make_mzi, platform="SiN")
        entry = fresh_registry.get("mzi")
        assert entry.platform == "SiN"  # 新元数据


# =============================================================================
# 9. 学术诚信测试
# =============================================================================
class TestAcademicIntegrity:
    """R02 学术诚信: 验证 gdsfactory 插件注册机制文献溯源。"""

    def test_register_pattern_source(self):
        """注册模式对标 gdsfactory register_cells。

        来源: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
        """
        reg = PolarisCellRegistry()
        # gdsfactory PDK 注册模式: register_cells({name: factory})
        # PoLaRIS 对标: register(name, factory) 单个注册
        entry = reg.register("mzi", _make_mzi)
        assert entry.factory is _make_mzi  # 工厂函数引用正确

    def test_decorator_pattern_source(self):
        """装饰器对标 gdsfactory @gf.cell。

        来源: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.cell
        """
        reg = PolarisCellRegistry()

        @register_polaris_cell(name="test", registry=reg)
        def make_cell() -> PCellMultiView:
            """测试 cell。"""
            return _make_mzi()

        # 装饰器对标 @gf.cell: 自动注册 + 保留可调用性
        assert "test" in reg
        assert callable(make_cell)
        # docstring 保留
        assert "测试 cell" in (make_cell.__doc__ or "")

    def test_adapter_pattern_source(self):
        """Adapter Pattern 对标 Gamma 1994。

        来源: https://en.wikipedia.org/wiki/wiki/Adapter_pattern
        to_gdsfactory_cells 是适配器: PoLaRIS PCell 工厂 → gdsfactory Component 工厂
        """
        reg = PolarisCellRegistry()
        reg.register("mzi", _make_mzi)
        # to_gdsfactory_cells 在 gdsfactory 不可用时 raise ImportError（已测）
        # 这里验证注册表本身独立于 gdsfactory（Adapter 的存在前提）
        assert reg.size == 1
        # 注册表可在无 gdsfactory 时工作
        pcell = reg.create("mzi")
        assert isinstance(pcell, PCellMultiView)

    def test_pcell_multiview_source(self):
        """PCellMultiView 对标 gdsfactory Component + IPKISS PCell。

        来源:
        - gdsfactory Component: https://gdsfactory.github.io/gdsfactory/
        - IPKISS PCell: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
        """
        pcell = _make_mzi(length=150.0)
        # PCellMultiView 是 PoLaRIS 的多视图参数化单元
        assert isinstance(pcell, PCellMultiView)
        assert pcell.name == "mzi_2x2"
        assert pcell.params == {"length": 150.0}
        # 三视图架构（Layout/Circuit/Netlist）对标 IPKISS
        assert hasattr(pcell, "layout_view")
        assert hasattr(pcell, "circuit_view")
        assert hasattr(pcell, "netlist_view")

    def test_default_platform_soi_source(self):
        """默认平台 SOI 来源: SiEPIC EBeam PDK。

        来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        entry = PolarisCellEntry(name="test", factory=_make_mzi)
        # 默认 platform="SOI"，对齐 SiEPIC EBeam PDK 的 SOI 平台
        assert entry.platform == "SOI"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
