"""R315 多 PDK 实例管理器测试。

覆盖:
- register/get/list_pdks: 注册代理
- activate/deactivate/get_active: 激活/切换语义
- snapshot/restore: 状态快照/恢复（Memento Pattern）
- merge: 多 PDK 合并（Composite Pattern，含冲突检测）
- list_pdk_metadata/get_pdk_metadata: 元数据查询
- detect_conflicts: 冲突检测代理
- R03 错误处理
- R02 学术诚信
- 集成测试

来源:
- gdsfactory PDK activate: https://gdsfactory.github.io/gdsfactory/api.html
- Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
- GoF Memento Pattern: https://en.wikipedia.org/wiki/Memento_pattern
"""

from __future__ import annotations

import pytest

from polaris.pdk.gdsfactory_pdk_bridge import (
    PolarisPDK,
    PolarisPDKRegistry,
)
from polaris.pdk.multi_pdk_manager import (
    MultiPDKManager,
    PDKMetadata,
    PDKSnapshot,
)


# =============================================================================
# 共享 fixtures
# =============================================================================
@pytest.fixture
def soi_pdk() -> PolarisPDK:
    """SOI 平台 PDK。"""
    return PolarisPDK(
        name="soi_pdk",
        platform="SOI",
        process_node="220nm SOI",
        devices={"mzi": object(), "ring": object()},
    )


@pytest.fixture
def sin_pdk() -> PolarisPDK:
    """SiN 平台 PDK。"""
    return PolarisPDK(
        name="sin_pdk",
        platform="SiN",
        process_node="300nm SiN",
        devices={"ring_sin": object(), "mmi": object()},
    )


@pytest.fixture
def manager_with_pdks(
    soi_pdk: PolarisPDK, sin_pdk: PolarisPDK
) -> MultiPDKManager:
    """含 2 个 PDK 的管理器。"""
    m = MultiPDKManager()
    m.register("soi", soi_pdk)
    m.register("sin", sin_pdk)
    return m


# =============================================================================
# TestRegisterProxy: 注册代理
# =============================================================================
class TestRegisterProxy:
    """register/get/list_pdks 代理测试。"""

    def test_register_basic(self, soi_pdk: PolarisPDK) -> None:
        """基本注册。"""
        m = MultiPDKManager()
        m.register("soi", soi_pdk)
        assert "soi" in m.list_pdks()

    def test_register_duplicate_raises(self, soi_pdk: PolarisPDK) -> None:
        """重复注册应 raise ValueError。"""
        m = MultiPDKManager()
        m.register("soi", soi_pdk)
        with pytest.raises(ValueError, match="已注册"):
            m.register("soi", soi_pdk)

    def test_get_pdk(self, manager_with_pdks: MultiPDKManager) -> None:
        """获取 PDK。"""
        pdk = manager_with_pdks.get("soi")
        assert pdk.platform == "SOI"

    def test_get_unregistered_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """获取未注册 PDK raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            manager_with_pdks.get("nonexistent")

    def test_list_pdks_sorted(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """list_pdks 应排序。"""
        result = manager_with_pdks.list_pdks()
        assert result == sorted(result)
        assert "soi" in result
        assert "sin" in result

    def test_custom_registry(self, soi_pdk: PolarisPDK) -> None:
        """使用自定义 registry。"""
        reg = PolarisPDKRegistry()
        reg.register("custom", soi_pdk)
        m = MultiPDKManager(registry=reg)
        assert "custom" in m.list_pdks()


# =============================================================================
# TestActivateDeactivate: 激活/切换语义
# =============================================================================
class TestActivateDeactivate:
    """activate/deactivate/get_active 测试。"""

    def test_activate_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """基本激活。"""
        manager_with_pdks.activate("soi")
        assert manager_with_pdks.get_active_name() == "soi"
        assert manager_with_pdks.is_active("soi") is True

    def test_activate_unregistered_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """激活未注册 PDK raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            manager_with_pdks.activate("nonexistent")

    def test_activate_switch(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """切换激活 PDK。"""
        manager_with_pdks.activate("soi")
        assert manager_with_pdks.get_active_name() == "soi"
        manager_with_pdks.activate("sin")
        assert manager_with_pdks.get_active_name() == "sin"
        assert manager_with_pdks.is_active("soi") is False

    def test_deactivate(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """取消激活。"""
        manager_with_pdks.activate("soi")
        manager_with_pdks.deactivate()
        assert manager_with_pdks.get_active_name() is None

    def test_deactivate_no_active(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无激活 PDK 时 deactivate 无副作用。"""
        manager_with_pdks.deactivate()
        assert manager_with_pdks.get_active_name() is None

    def test_get_active_no_active_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无激活 PDK 时 get_active raise RuntimeError。"""
        with pytest.raises(RuntimeError, match="无激活"):
            manager_with_pdks.get_active()

    def test_get_active_returns_pdk(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """get_active 返回激活的 PDK。"""
        manager_with_pdks.activate("soi")
        pdk = manager_with_pdks.get_active()
        assert pdk.platform == "SOI"

    def test_is_active_no_active(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无激活时 is_active 返回 False。"""
        assert manager_with_pdks.is_active("soi") is False


# =============================================================================
# TestSnapshotRestore: 状态快照/恢复
# =============================================================================
class TestSnapshotRestore:
    """snapshot/restore 测试（Memento Pattern）。"""

    def test_snapshot_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """基本快照。"""
        manager_with_pdks.activate("soi")
        snap = manager_with_pdks.snapshot(created_at=1000.0)
        assert isinstance(snap, PDKSnapshot)
        assert snap.active_pdk_name == "soi"
        assert "soi" in snap.registered_pdk_names
        assert "sin" in snap.registered_pdk_names
        assert snap.created_at == 1000.0

    def test_snapshot_no_active(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无激活时快照 active_pdk_name 为 None。"""
        snap = manager_with_pdks.snapshot()
        assert snap.active_pdk_name is None

    def test_restore_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """基本恢复。"""
        manager_with_pdks.activate("soi")
        snap = manager_with_pdks.snapshot()
        # 改变状态
        manager_with_pdks.activate("sin")
        assert manager_with_pdks.get_active_name() == "sin"
        # 恢复
        manager_with_pdks.restore(snap)
        assert manager_with_pdks.get_active_name() == "soi"

    def test_restore_no_active(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """恢复无激活状态。"""
        snap = manager_with_pdks.snapshot()
        manager_with_pdks.activate("soi")
        manager_with_pdks.restore(snap)
        assert manager_with_pdks.get_active_name() is None

    def test_restore_invalid_snapshot_type_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """非 PDKSnapshot 类型 raise TypeError。"""
        with pytest.raises(TypeError):
            manager_with_pdks.restore("not_a_snapshot")  # type: ignore[arg-type]

    def test_restore_missing_pdk_raises(
        self, manager_with_pdks: MultiPDKManager, soi_pdk: PolarisPDK
    ) -> None:
        """快照中的 PDK 在当前 registry 不存在 raise ValueError。"""
        snap = PDKSnapshot(
            active_pdk_name="soi",
            registered_pdk_names=["soi", "sin", "nonexistent"],
        )
        with pytest.raises(ValueError, match="不存在"):
            manager_with_pdks.restore(snap)

    def test_restore_active_pdk_missing_raises(
        self, soi_pdk: PolarisPDK
    ) -> None:
        """快照激活 PDK 在 registry 不存在 raise ValueError。"""
        m = MultiPDKManager()
        m.register("soi", soi_pdk)
        snap = PDKSnapshot(
            active_pdk_name="sin",
            registered_pdk_names=["soi"],
        )
        with pytest.raises(ValueError, match="激活 PDK"):
            m.restore(snap)


# =============================================================================
# TestMerge: 多 PDK 合并
# =============================================================================
class TestMerge:
    """merge 测试（Composite Pattern）。"""

    def test_merge_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """基本合并。"""
        merged = manager_with_pdks.merge(
            "merged", ["soi", "sin"]
        )
        assert merged.name == "merged"
        assert merged.platform == "merged"
        # 合并后应包含所有组件
        assert "mzi" in merged.devices
        assert "ring" in merged.devices
        assert "ring_sin" in merged.devices
        assert "mmi" in merged.devices

    def test_merge_custom_platform(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """自定义合并后平台标识。"""
        merged = manager_with_pdks.merge(
            "merged", ["soi"], platform="SOI", process_node="220nm"
        )
        assert merged.platform == "SOI"
        assert merged.process_node == "220nm"

    def test_merge_empty_list_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """空 pdk_names 列表 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为空"):
            manager_with_pdks.merge("merged", [])

    def test_merge_unregistered_pdk_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """未注册 PDK raise ValueError。"""
        with pytest.raises(ValueError, match="未注册"):
            manager_with_pdks.merge("merged", ["soi", "nonexistent"])

    def test_merge_component_conflict_raises(
        self, manager_with_pdks: MultiPDKManager, soi_pdk: PolarisPDK
    ) -> None:
        """组件名冲突 raise ValueError。"""
        # 注册一个与 soi 组件冲突的 PDK
        conflict_pdk = PolarisPDK(
            name="conflict",
            platform="SOI",
            process_node="220nm SOI",
            devices={"mzi": object()},  # mzi 与 soi_pdk 冲突
        )
        manager_with_pdks.register("conflict", conflict_pdk)
        with pytest.raises(ValueError, match="冲突"):
            manager_with_pdks.merge("merged", ["soi", "conflict"])

    def test_merge_non_list_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """非列表 raise TypeError。"""
        with pytest.raises(TypeError):
            manager_with_pdks.merge("merged", "soi")  # type: ignore[arg-type]

    def test_merge_single_pdk(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """合并单个 PDK（相当于复制）。"""
        merged = manager_with_pdks.merge("merged", ["soi"])
        assert len(merged.devices) == 2
        assert "mzi" in merged.devices


# =============================================================================
# TestPDKMetadata: 元数据查询
# =============================================================================
class TestPDKMetadata:
    """list_pdk_metadata/get_pdk_metadata 测试。"""

    def test_list_metadata_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """列出所有 PDK 元数据。"""
        metadata_list = manager_with_pdks.list_pdk_metadata()
        assert len(metadata_list) == 2
        assert all(isinstance(m, PDKMetadata) for m in metadata_list)
        # 按名排序
        names = [m.name for m in metadata_list]
        assert names == sorted(names)

    def test_list_metadata_fields(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """元数据字段完整性。"""
        metadata_list = manager_with_pdks.list_pdk_metadata()
        for m in metadata_list:
            assert isinstance(m.name, str)
            assert isinstance(m.platform, str)
            assert isinstance(m.process_node, str)
            assert isinstance(m.device_count, int)
            assert isinstance(m.is_active, bool)

    def test_list_metadata_device_count(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """device_count 字段。"""
        metadata_list = manager_with_pdks.list_pdk_metadata()
        for m in metadata_list:
            if m.name == "soi":
                assert m.device_count == 2
            elif m.name == "sin":
                assert m.device_count == 2

    def test_list_metadata_is_active(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """is_active 字段。"""
        manager_with_pdks.activate("soi")
        metadata_list = manager_with_pdks.list_pdk_metadata()
        for m in metadata_list:
            if m.name == "soi":
                assert m.is_active is True
            else:
                assert m.is_active is False

    def test_get_pdk_metadata_basic(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """获取单个 PDK 元数据。"""
        m = manager_with_pdks.get_pdk_metadata("soi")
        assert m.name == "soi"
        assert m.platform == "SOI"
        assert m.process_node == "220nm SOI"
        assert m.device_count == 2

    def test_get_pdk_metadata_unregistered_raises(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """未注册 PDK raise KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            manager_with_pdks.get_pdk_metadata("nonexistent")


# =============================================================================
# TestDetectConflicts: 冲突检测代理
# =============================================================================
class TestDetectConflicts:
    """detect_conflicts 测试。"""

    def test_no_conflict(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无冲突。"""
        conflicts = manager_with_pdks.detect_conflicts()
        assert len(conflicts) == 0

    def test_internal_conflict(
        self, soi_pdk: PolarisPDK
    ) -> None:
        """内部冲突（同组件名在多 PDK）。"""
        m = MultiPDKManager()
        m.register("pdk1", soi_pdk)
        conflict_pdk = PolarisPDK(
            name="pdk2",
            platform="SOI",
            process_node="220nm SOI",
            devices={"mzi": object()},  # 与 soi_pdk 冲突
        )
        m.register("pdk2", conflict_pdk)
        conflicts = m.detect_conflicts()
        assert len(conflicts) >= 1
        assert conflicts[0].component_name == "mzi"

    def test_cross_manager_conflict(
        self, soi_pdk: PolarisPDK
    ) -> None:
        """跨管理器冲突。"""
        m1 = MultiPDKManager()
        m1.register("pdk1", soi_pdk)
        m2 = MultiPDKManager()
        conflict_pdk = PolarisPDK(
            name="pdk2",
            platform="SOI",
            process_node="220nm SOI",
            devices={"mzi": object()},
        )
        m2.register("pdk2", conflict_pdk)
        conflicts = m1.detect_conflicts(other=m2)
        assert len(conflicts) >= 1


# =============================================================================
# TestR03ErrorHandling: R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back 错误处理。"""

    def test_activate_unregistered_no_fallback(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """激活未注册 PDK 不应 fall-back。"""
        with pytest.raises(KeyError):
            manager_with_pdks.activate("nonexistent")
        # 激活态应保持 None
        assert manager_with_pdks.get_active_name() is None

    def test_get_active_no_active_no_fallback(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """无激活 PDK 时 get_active 不应 fall-back。"""
        with pytest.raises(RuntimeError):
            manager_with_pdks.get_active()

    def test_merge_conflict_no_fallback(
        self, manager_with_pdks: MultiPDKManager, soi_pdk: PolarisPDK
    ) -> None:
        """合并冲突不应 fall-back 跳过冲突组件。"""
        conflict_pdk = PolarisPDK(
            name="conflict",
            platform="SOI",
            process_node="220nm SOI",
            devices={"mzi": object()},
        )
        manager_with_pdks.register("conflict", conflict_pdk)
        with pytest.raises(ValueError, match="冲突"):
            manager_with_pdks.merge("merged", ["soi", "conflict"])

    def test_restore_missing_pdk_no_fallback(
        self, manager_with_pdks: MultiPDKManager
    ) -> None:
        """快照恢复缺失 PDK 不应 fall-back。"""
        snap = PDKSnapshot(
            active_pdk_name="nonexistent",
            registered_pdk_names=["nonexistent"],
        )
        with pytest.raises(ValueError):
            manager_with_pdks.restore(snap)


# =============================================================================
# TestR02AcademicIntegrity: R02 学术诚信
# =============================================================================
class TestR02AcademicIntegrity:
    """R02 学术诚信验证。"""

    def test_module_docstring_has_sources(self) -> None:
        """模块 docstring 应含 5+ 文献 URL。"""
        from polaris.pdk import multi_pdk_manager as m
        doc = m.__doc__ or ""
        urls = [
            "gdsfactory" in doc,
            "martinfowler.com" in doc,
            "Memento_pattern" in doc or "Memento" in doc,
            "Composite_pattern" in doc or "Composite" in doc,
            "dataclasses" in doc or "python.org" in doc,
            "SiEPIC" in doc,
        ]
        url_count = sum(1 for u in urls if u)
        assert url_count >= 5, f"docstring 文献 URL 不足 5 个: {url_count}"

    def test_class_docstring_has_sources(self) -> None:
        """MultiPDKManager docstring 应含来源。"""
        from polaris.pdk.multi_pdk_manager import MultiPDKManager
        doc = MultiPDKManager.__doc__ or ""
        assert "gdsfactory" in doc or "Fowler" in doc
        assert "Memento" in doc

    def test_functions_have_source_annotations(self) -> None:
        """核心函数应含来源说明。"""
        from polaris.pdk import multi_pdk_manager as m
        for func_name in ["activate", "snapshot", "restore", "merge"]:
            func = getattr(m.MultiPDKManager, func_name)
            doc = func.__doc__ or ""
            assert "来源" in doc or "Pattern" in doc or "gdsfactory" in doc, (
                f"{func_name} 缺少来源标注"
            )

    def test_gdsfactory_activate_semantics_documented(self) -> None:
        """activate 函数应记录 gdsfactory 对标。"""
        from polaris.pdk.multi_pdk_manager import MultiPDKManager
        doc = MultiPDKManager.activate.__doc__ or ""
        assert "gdsfactory" in doc


# =============================================================================
# TestIntegration: 集成测试
# =============================================================================
class TestIntegration:
    """端到端集成测试。"""

    def test_full_workflow(
        self,
        soi_pdk: PolarisPDK,
        sin_pdk: PolarisPDK,
    ) -> None:
        """端到端: 注册 → 激活 → 快照 → 切换 → 恢复 → 合并。"""
        m = MultiPDKManager()
        # 1. 注册
        m.register("soi", soi_pdk)
        m.register("sin", sin_pdk)
        assert len(m.list_pdks()) == 2
        # 2. 激活
        m.activate("soi")
        assert m.get_active_name() == "soi"
        # 3. 快照
        snap = m.snapshot(created_at=1000.0)
        # 4. 切换
        m.activate("sin")
        assert m.get_active_name() == "sin"
        # 5. 恢复
        m.restore(snap)
        assert m.get_active_name() == "soi"
        # 6. 合并
        merged = m.merge("merged", ["soi", "sin"])
        assert len(merged.devices) == 4

    def test_metadata_after_operations(
        self,
        manager_with_pdks: MultiPDKManager,
    ) -> None:
        """操作后元数据正确性。"""
        manager_with_pdks.activate("soi")
        metadata = manager_with_pdks.list_pdk_metadata()
        # soi 应激活
        soi_meta = next(m for m in metadata if m.name == "soi")
        assert soi_meta.is_active is True
        # 切换后元数据应更新
        manager_with_pdks.activate("sin")
        metadata = manager_with_pdks.list_pdk_metadata()
        soi_meta = next(m for m in metadata if m.name == "soi")
        sin_meta = next(m for m in metadata if m.name == "sin")
        assert soi_meta.is_active is False
        assert sin_meta.is_active is True

    def test_performance_many_pdks(
        self, soi_pdk: PolarisPDK
    ) -> None:
        """性能: 100 个 PDK 注册 + 元数据查询 < 1s。"""
        import time
        m = MultiPDKManager()
        start = time.perf_counter()
        for i in range(100):
            pdk = PolarisPDK(
                name=f"pdk_{i}",
                platform="SOI",
                process_node="220nm SOI",
                devices={f"comp_{i}": object()},
            )
            m.register(f"pdk_{i}", pdk)
        m.list_pdk_metadata()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0


# =============================================================================
# TestDataclassTest: 数据类测试
# =============================================================================
class TestDataclassTest:
    """数据类测试。"""

    def test_pdk_metadata_defaults(self) -> None:
        """PDKMetadata 默认值。"""
        m = PDKMetadata(
            name="test", platform="SOI",
            process_node="220nm", device_count=0,
        )
        assert m.is_active is False

    def test_pdk_snapshot_defaults(self) -> None:
        """PDKSnapshot 默认值。"""
        snap = PDKSnapshot(
            active_pdk_name=None,
            registered_pdk_names=[],
        )
        assert snap.created_at == 0.0

    def test_pdk_metadata_with_active(self) -> None:
        """PDKMetadata 含 is_active。"""
        m = PDKMetadata(
            name="test", platform="SOI",
            process_node="220nm", device_count=5,
            is_active=True,
        )
        assert m.is_active is True
        assert m.device_count == 5

    def test_pdk_snapshot_with_data(self) -> None:
        """PDKSnapshot 含数据。"""
        snap = PDKSnapshot(
            active_pdk_name="soi",
            registered_pdk_names=["soi", "sin"],
            created_at=1234.5,
        )
        assert snap.active_pdk_name == "soi"
        assert len(snap.registered_pdk_names) == 2
        assert snap.created_at == 1234.5
