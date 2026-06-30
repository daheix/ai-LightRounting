"""多 PDK 实例管理器（R315，激活/切换/快照/合并）。

基于 R09 的 PolarisPDKRegistry，扩展多 PDK 实例的运行时管理：
1. PDK 激活/切换: 类似 gdsfactory PDK.activate() 语义，但支持命名空间隔离
2. PDK 快照: 记录当前激活 PDK 状态，可恢复
3. PDK 合并: 将多个 PDK 合并为一个虚拟 PDK（含冲突检测）
4. PDK 元数据查询: 列出所有 PDK 的平台/工艺节点信息

R315 实现:
- MultiPDKManager: 多 PDK 实例管理器主类
- activate(name) -> None: 激活指定 PDK
- get_active() -> PolarisPDK: 获取当前激活 PDK
- snapshot() -> PDKSnapshot: 创建状态快照
- restore(snapshot) -> None: 恢复快照
- merge(name, pdk_names) -> PolarisPDK: 合并多个 PDK
- list_pdk_metadata() -> list[PDKMetadata]: 列出所有 PDK 元数据

设计模式（来源: Fowler 2002 PoEAA）:
- Active Record Pattern: 激活态管理（与 gdsfactory PDK.activate 对标）
- Memento Pattern: 快照/恢复机制
- Composite Pattern: 多 PDK 合并为虚拟 PDK

R03 合规:
- 激活不存在的 PDK raise KeyError（不静默 fall-back 到默认 PDK）
- 合并无冲突 PDK 时 raise ValueError（不静默跳过冲突组件）
- 快照恢复时版本不匹配 raise ValueError

R02 学术诚信:
- PDK 激活语义对标 gdsfactory PDK.activate
- 快照模式引用 Fowler 2002 + GoF Memento Pattern

来源:
- gdsfactory PDK activate: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.pdk.PDK.activate
- Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
- GoF Memento Pattern: https://en.wikipedia.org/wiki/Memento_pattern
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ubcpdk: https://github.com/gdsfactory/ubc

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from polaris.pdk.gdsfactory_pdk_bridge import (
    PolarisPDK,
    PolarisPDKRegistry,
)

logger = logging.getLogger(__name__)

__all__ = [
    "MultiPDKManager",
    "PDKMetadata",
    "PDKSnapshot",
]


@dataclass
class PDKMetadata:
    """PDK 元数据（R315）。

    Attributes:
        name: PDK 名称。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        process_node: 工艺节点（如 "220nm SOI"）。
        device_count: 已注册器件数。
        is_active: 是否当前激活。
    """

    name: str
    platform: str
    process_node: str
    device_count: int
    is_active: bool = False


@dataclass
class PDKSnapshot:
    """PDK 状态快照（R315，Memento Pattern）。

    记录当前激活 PDK 名称，用于后续恢复。

    Attributes:
        active_pdk_name: 快照时的激活 PDK 名（None 表示无激活）。
        registered_pdk_names: 快照时已注册的所有 PDK 名列表。
        created_at: 快照创建时间戳（由调用方注入，便于测试）。
    """

    active_pdk_name: str | None
    registered_pdk_names: list[str]
    created_at: float = 0.0


class MultiPDKManager:
    """多 PDK 实例管理器（R315）。

    在 PolarisPDKRegistry 基础上扩展运行时管理：
    - 激活/切换语义（对标 gdsfactory PDK.activate）
    - 状态快照/恢复（Memento Pattern）
    - 多 PDK 合并（Composite Pattern，含冲突检测）
    - PDK 元数据查询

    Attributes:
        registry: 底层 PolarisPDKRegistry 实例。
        _active_pdk_name: 当前激活 PDK 名（None 表示无激活）。

    设计:
    - 聚合 PolarisPDKRegistry，不继承（组合优于继承，Fowler 2002）
    - 激活态由本类管理，registry 仅负责注册/查询

    来源:
    - gdsfactory PDK activate: https://gdsfactory.github.io/gdsfactory/api.html
    - Fowler 2002 PoEAA: https://martinfowler.com/books/eaa.html
    - GoF Memento Pattern: https://en.wikipedia.org/wiki/Memento_pattern
    """

    def __init__(
        self,
        registry: PolarisPDKRegistry | None = None,
    ) -> None:
        """初始化多 PDK 管理器。

        Args:
            registry: 底层 PolarisPDKRegistry（None 创建新实例）。
        """
        self.registry: PolarisPDKRegistry = registry or PolarisPDKRegistry()
        self._active_pdk_name: str | None = None

    # =========================================================================
    # 注册代理（委托给 registry）
    # =========================================================================
    def register(self, name: str, pdk: PolarisPDK) -> None:
        """注册 PDK（委托给底层 registry）。

        Args:
            name: PDK 名称。
            pdk: PolarisPDK 实例。

        Raises:
            ValueError: name 已注册（由 registry 抛出）。
        """
        self.registry.register(name, pdk)
        logger.info("PDK 已注册: %s (platform=%s)", name, pdk.platform)

    def get(self, name: str) -> PolarisPDK:
        """获取 PDK（委托给底层 registry）。

        Args:
            name: PDK 名称。

        Returns:
            PolarisPDK 实例。

        Raises:
            KeyError: PDK 未注册。
        """
        return self.registry.get(name)

    def list_pdks(self) -> list[str]:
        """列出所有已注册 PDK 名（委托给底层 registry）。"""
        return self.registry.list_pdks()

    # =========================================================================
    # 激活/切换语义
    # =========================================================================
    def activate(self, name: str) -> None:
        """激活指定 PDK（R315，对标 gdsfactory PDK.activate）。

        激活语义：将指定 PDK 设为当前激活 PDK，后续操作默认使用该 PDK。
        与 gdsfactory 不同：PoLaRIS 支持命名空间隔离，多 PDK 可共存。

        Args:
            name: PDK 名称。

        Raises:
            KeyError: PDK 未注册（不静默 fall-back 到默认 PDK）。
        """
        if name not in self.registry.list_pdks():
            raise KeyError(
                f"PDK '{name}' 未注册，无法激活。"
                f"已注册 PDK: {self.registry.list_pdks()}"
            )
        self._active_pdk_name = name
        logger.info("PDK 已激活: %s", name)

    def deactivate(self) -> None:
        """取消激活当前 PDK（无激活 PDK 时无操作）。"""
        if self._active_pdk_name is not None:
            logger.info("PDK 已取消激活: %s", self._active_pdk_name)
        self._active_pdk_name = None

    def get_active(self) -> PolarisPDK:
        """获取当前激活的 PDK。

        Returns:
            激活的 PolarisPDK 实例。

        Raises:
            RuntimeError: 无激活 PDK（不静默 fall-back 到第一个 PDK）。
        """
        if self._active_pdk_name is None:
            raise RuntimeError(
                "无激活 PDK。请先调用 activate(name) 激活一个 PDK。"
                "禁止 fall-back 到默认 PDK（R03）。"
            )
        return self.registry.get(self._active_pdk_name)

    def get_active_name(self) -> str | None:
        """获取当前激活 PDK 名（无激活时返回 None）。"""
        return self._active_pdk_name

    def is_active(self, name: str) -> bool:
        """检查指定 PDK 是否当前激活。"""
        return self._active_pdk_name == name

    # =========================================================================
    # 状态快照/恢复（Memento Pattern）
    # =========================================================================
    def snapshot(self, created_at: float = 0.0) -> PDKSnapshot:
        """创建当前状态快照（R315，Memento Pattern）。

        Args:
            created_at: 快照创建时间戳（由调用方注入，便于测试）。

        Returns:
            PDKSnapshot 快照对象。

        来源:
        - GoF Memento Pattern: https://en.wikipedia.org/wiki/Memento_pattern
        """
        return PDKSnapshot(
            active_pdk_name=self._active_pdk_name,
            registered_pdk_names=self.registry.list_pdks(),
            created_at=created_at,
        )

    def restore(self, snapshot: PDKSnapshot) -> None:
        """从快照恢复状态（R315，Memento Pattern）。

        恢复语义：将激活态恢复到快照时的状态。
        注意：快照中记录的 PDK 必须在当前 registry 中存在。

        Args:
            snapshot: PDKSnapshot 快照对象。

        Raises:
            ValueError: 快照中的 PDK 在当前 registry 中不存在。
            TypeError: snapshot 不是 PDKSnapshot。
        """
        if not isinstance(snapshot, PDKSnapshot):
            raise TypeError(
                f"snapshot 必须是 PDKSnapshot，得到 {type(snapshot).__name__}"
            )
        current_pdks = set(self.registry.list_pdks())
        for pdk_name in snapshot.registered_pdk_names:
            if pdk_name not in current_pdks:
                raise ValueError(
                    f"快照中的 PDK '{pdk_name}' 在当前 registry 中不存在。"
                    f"快照恢复失败（R03: 禁止 fall-back）。"
                )
        if snapshot.active_pdk_name is not None:
            if snapshot.active_pdk_name not in current_pdks:
                raise ValueError(
                    f"快照中的激活 PDK '{snapshot.active_pdk_name}' "
                    f"在当前 registry 中不存在。"
                    f"快照恢复失败（R03: 禁止 fall-back）。"
                )
        self._active_pdk_name = snapshot.active_pdk_name
        logger.info(
            "PDK 状态已恢复: active=%s, registered=%s",
            self._active_pdk_name,
            snapshot.registered_pdk_names,
        )

    # =========================================================================
    # 多 PDK 合并（Composite Pattern，含冲突检测）
    # =========================================================================
    def merge(
        self,
        name: str,
        pdk_names: list[str],
        platform: str = "merged",
        process_node: str = "merged",
    ) -> PolarisPDK:
        """合并多个 PDK 为一个虚拟 PDK（R315，Composite Pattern）。

        合并语义：将多个 PDK 的 devices/layer_stack/cross_sections 合并到一个
        新的 PolarisPDK 中。组件名冲突时 raise ValueError（不静默跳过）。

        Args:
            name: 合并后的 PDK 名称。
            pdk_names: 要合并的 PDK 名列表。
            platform: 合并后 PDK 的平台标识（默认 "merged"）。
            process_node: 合并后 PDK 的工艺节点标识（默认 "merged"）。

        Returns:
            合并后的 PolarisPDK 实例。

        Raises:
            ValueError: pdk_names 为空 / pdk_names 中有未注册 PDK /
                组件名冲突（不静默跳过冲突组件）。
            TypeError: pdk_names 不是列表。

        来源:
        - GoF Composite Pattern: https://en.wikipedia.org/wiki/Composite_pattern
        """
        if not isinstance(pdk_names, (list, tuple)):
            raise TypeError(
                f"pdk_names 必须是列表或元组，得到 {type(pdk_names).__name__}"
            )
        if len(pdk_names) == 0:
            raise ValueError(
                "pdk_names 不能为空列表。合并至少需要一个 PDK。"
            )
        # 验证所有 PDK 已注册
        current_pdks = set(self.registry.list_pdks())
        for pn in pdk_names:
            if pn not in current_pdks:
                raise ValueError(
                    f"PDK '{pn}' 未注册，无法合并。"
                    f"已注册 PDK: {sorted(current_pdks)}"
                )

        # 收集所有组件，检测冲突
        merged_devices: dict[str, Any] = {}
        merged_cross_sections: dict[str, Any] = {}
        layer_stack: Any = None
        for pn in pdk_names:
            pdk = self.registry.get(pn)
            for comp_name, device in pdk.devices.items():
                if comp_name in merged_devices:
                    raise ValueError(
                        f"组件名冲突: '{comp_name}' 同时存在于 "
                        f"'{pn}' 和之前合并的 PDK 中。"
                        f"禁止 fall-back 跳过冲突组件（R03）。"
                    )
                merged_devices[comp_name] = device
            for xs_name, xs in pdk.cross_sections.items():
                if xs_name not in merged_cross_sections:
                    merged_cross_sections[xs_name] = xs
            if pdk.layer_stack is not None and layer_stack is None:
                layer_stack = pdk.layer_stack

        merged_pdk = PolarisPDK(
            name=name,
            platform=platform,
            process_node=process_node,
            devices=merged_devices,
            layer_stack=layer_stack,
            cross_sections=merged_cross_sections,
        )
        logger.info(
            "PDK 合并完成: %s (来自 %s, %d 器件)",
            name, pdk_names, len(merged_devices),
        )
        return merged_pdk

    # =========================================================================
    # PDK 元数据查询
    # =========================================================================
    def list_pdk_metadata(self) -> list[PDKMetadata]:
        """列出所有 PDK 的元数据（R315）。

        Returns:
            PDKMetadata 列表（按 PDK 名排序）。
        """
        result: list[PDKMetadata] = []
        for name in self.registry.list_pdks():
            pdk = self.registry.get(name)
            result.append(
                PDKMetadata(
                    name=name,
                    platform=pdk.platform,
                    process_node=pdk.process_node,
                    device_count=len(pdk.devices),
                    is_active=(self._active_pdk_name == name),
                )
            )
        return result

    def get_pdk_metadata(self, name: str) -> PDKMetadata:
        """获取指定 PDK 的元数据。

        Args:
            name: PDK 名称。

        Returns:
            PDKMetadata 元数据。

        Raises:
            KeyError: PDK 未注册。
        """
        if name not in self.registry.list_pdks():
            raise KeyError(
                f"PDK '{name}' 未注册。"
                f"已注册 PDK: {self.registry.list_pdks()}"
            )
        pdk = self.registry.get(name)
        return PDKMetadata(
            name=name,
            platform=pdk.platform,
            process_node=pdk.process_node,
            device_count=len(pdk.devices),
            is_active=(self._active_pdk_name == name),
        )

    # =========================================================================
    # 冲突检测（代理给 registry）
    # =========================================================================
    def detect_conflicts(
        self, other: MultiPDKManager | None = None
    ) -> list[Any]:
        """检测组件名冲突（代理给底层 registry）。

        Args:
            other: 另一个 MultiPDKManager（None 检测自身内部冲突）。

        Returns:
            PDKConflict 列表。
        """
        other_registry = other.registry if other is not None else None
        return self.registry.detect_conflicts(other_registry)
