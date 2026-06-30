"""gdsfactory 插件注册机制（R308）。

将 PoLaRIS PCell 注册为 gdsfactory 可识别的 cell，实现 PoLaRIS 器件
反向接入 gdsfactory 生态。对标 gdsfactory `register_cells` / `get_component`
机制与 Luceda IPKISS PDK 互操作能力。

R308 实现:
1. PolarisCellRegistry: PoLaRIS cell 注册表（独立于 gdsfactory，可独立工作）
2. PolarisCellEntry: 注册条目（name/factory/params_schema/platform/category）
3. register_to_gdsfactory(): 将注册表导出为 gdsfactory cells 字典并注册到活跃 PDK
4. @register_polaris_cell 装饰器: 对标 @gf.cell，自动注册
5. get_polaris_cell(name, **kwargs): 便捷获取函数

R03 合规设计:
- gdsfactory 不可用时注册表仍可工作（注册/检索/序列化）
- 仅在调用 to_gdsfactory_cells() / register_to_gdsfactory() 时检查 gdsfactory
- 注册重复名称 raise ValueError（不静默覆盖）
- 工厂返回非 PCellMultiView raise TypeError
- 装饰器重复注册 raise ValueError

学术依据:
- gdsfactory register_cells: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.get_component
- gdsfactory PDK cells 注册: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
- gdsfactory @gf.cell 装饰器: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.cell
- IPKISS PDK 互操作: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Adapter Pattern (Gamma 1994): https://en.wikipedia.org/wiki/Adapter_pattern
- gdsfactory from_yaml: https://gdsfactory.github.io/gdsfactory/notebooks/07_yaml_component.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from polaris.pdk.pcell import PCellMultiView

if TYPE_CHECKING:
    from polaris.pdk.pcell_gdsfactory_bridge import PCellBridgeConfig

logger = logging.getLogger(__name__)

__all__ = [
    "PolarisCellEntry",
    "PolarisCellRegistry",
    "default_registry",
    "get_polaris_cell",
    "register_polaris_cell",
    "register_to_gdsfactory",
]


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class PolarisCellEntry:
    """PoLaRIS cell 注册条目（R308）。

    对标 gdsfactory PDK 的 cell 注册条目，每个条目记录工厂函数与元数据。

    Attributes:
        name: cell 名称（唯一键，如 "mzi_2x2"）。
        factory: 工厂函数，调用返回 PCellMultiView。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        category: 类别（passive/active/source/detector）。
        params_schema: 参数 schema（键名→默认值/类型描述）。
        description: 描述。
    """

    name: str
    factory: Callable[..., PCellMultiView]
    platform: str = "SOI"
    category: str = "passive"
    params_schema: dict[str, Any] = field(default_factory=dict)
    description: str = ""


# =============================================================================
# PoLaRIS cell 注册表
# =============================================================================
class PolarisCellRegistry:
    """PoLaRIS cell 注册表（R308）。

    独立于 gdsfactory 的 cell 注册表，支持:
    - 注册 PoLaRIS PCell 工厂函数
    - 按名称/平台/类别检索
    - 导出为 gdsfactory cells 字典（gdsfactory 可用时）
    - 注册到 gdsfactory 活跃 PDK

    设计对标:
    - gdsfactory PDK cells 注册表
      来源: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
    - DeviceCatalog 的 _devices / _by_name / _platforms 三级索引

    R03 合规:
    - 重复注册 raise ValueError（不静默覆盖）
    - 工厂返回非 PCellMultiView raise TypeError
    - 未知名检索 raise KeyError
    - gdsfactory 不可用时 to_gdsfactory_cells() raise ImportError
    """

    def __init__(self) -> None:
        self._entries: dict[str, PolarisCellEntry] = OrderedDict()
        self._by_platform: dict[str, set[str]] = {}

    @property
    def size(self) -> int:
        """已注册 cell 数量。"""
        return len(self._entries)

    @property
    def platforms(self) -> list[str]:
        """已注册平台列表（按字母排序）。"""
        return sorted(self._by_platform.keys())

    def register(
        self,
        name: str,
        factory: Callable[..., PCellMultiView],
        platform: str = "SOI",
        category: str = "passive",
        params_schema: dict[str, Any] | None = None,
        description: str = "",
    ) -> PolarisCellEntry:
        """注册 PoLaRIS cell 工厂。

        Args:
            name: cell 名称（唯一键）。
            factory: 工厂函数，调用返回 PCellMultiView。
            platform: 工艺平台。
            category: 类别。
            params_schema: 参数 schema。
            description: 描述。

        Returns:
            注册条目。

        Raises:
            ValueError: name 已注册 / name 为空。
            TypeError: factory 不可调用。
        """
        if not name or not name.strip():
            raise ValueError("cell 名称不能为空")
        if name in self._entries:
            raise ValueError(
                f"cell {name!r} 已注册，禁止重复注册（R03: 不静默覆盖）。"
                f"如需更新请先 unregister({name!r})"
            )
        if not callable(factory):
            raise TypeError(f"factory 必须可调用，得到 {type(factory).__name__}")

        entry = PolarisCellEntry(
            name=name,
            factory=factory,
            platform=platform,
            category=category,
            params_schema=dict(params_schema) if params_schema else {},
            description=description,
        )
        self._entries[name] = entry
        self._by_platform.setdefault(platform, set()).add(name)
        logger.info("注册 PoLaRIS cell %s (platform=%s, category=%s)",
                    name, platform, category)
        return entry

    def unregister(self, name: str) -> PolarisCellEntry:
        """注销已注册的 cell。

        Args:
            name: cell 名称。

        Returns:
            被移除的注册条目。

        Raises:
            KeyError: name 未注册。
        """
        if name not in self._entries:
            raise KeyError(f"cell {name!r} 未注册，无法注销")
        entry = self._entries.pop(name)
        platform_set = self._by_platform.get(entry.platform)
        if platform_set is not None:
            platform_set.discard(name)
            if not platform_set:
                del self._by_platform[entry.platform]
        return entry

    def get(self, name: str) -> PolarisCellEntry:
        """获取注册条目。

        Args:
            name: cell 名称。

        Returns:
            注册条目。

        Raises:
            KeyError: name 未注册。
        """
        if name not in self._entries:
            raise KeyError(
                f"cell {name!r} 未注册。可用: {sorted(self._entries.keys())[:10]}"
            )
        return self._entries[name]

    def create(self, name: str, **kwargs: Any) -> PCellMultiView:
        """调用工厂函数创建 PCell 实例。

        Args:
            name: cell 名称。
            **kwargs: 工厂函数参数。

        Returns:
            PCellMultiView 实例。

        Raises:
            KeyError: name 未注册。
            TypeError: 工厂返回值非 PCellMultiView（R03: 不静默兜底）。
        """
        entry = self.get(name)
        pcell = entry.factory(**kwargs)
        if not isinstance(pcell, PCellMultiView):
            raise TypeError(
                f"cell {name!r} 工厂返回类型 {type(pcell).__name__}，"
                f"期望 PCellMultiView（R03: 不静默兜底）"
            )
        return pcell

    def list_names(self, platform: str | None = None) -> list[str]:
        """列出已注册 cell 名称（按字母排序）。

        Args:
            platform: 过滤平台（None 表示全部）。

        Returns:
            cell 名称列表。
        """
        if platform is None:
            return sorted(self._entries.keys())
        names = self._by_platform.get(platform, set())
        return sorted(names)

    def list_all(self) -> list[PolarisCellEntry]:
        """列出全部注册条目。"""
        return list(self._entries.values())

    def list_by_platform(self, platform: str) -> list[PolarisCellEntry]:
        """按平台列出注册条目。"""
        names = self._by_platform.get(platform, set())
        return [self._entries[n] for n in sorted(names)]

    def list_by_category(self, category: str) -> list[PolarisCellEntry]:
        """按类别列出注册条目。"""
        return [e for e in self._entries.values() if e.category == category]

    def __contains__(self, name: str) -> bool:
        return name in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries.values())

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 JSON/YAML 导出）。"""
        return {
            "entries": [
                {
                    "name": e.name,
                    "platform": e.platform,
                    "category": e.category,
                    "params_schema": e.params_schema,
                    "description": e.description,
                }
                for e in self._entries.values()
            ]
        }

    # ==================================================================
    # gdsfactory 桥接（仅在调用时检查 gdsfactory 可用性）
    # ==================================================================
    def to_gdsfactory_cells(
        self,
        config: PCellBridgeConfig | None = None,
    ) -> dict[str, Callable]:
        """将注册表导出为 gdsfactory cells 字典。

        每个条目的工厂函数被包装为返回 gdsfactory Component 的函数。
        gdsfactory PDK 可通过 `pdk.register_cells(registry.to_gdsfactory_cells())`
        接入 PoLaRIS 器件。

        Args:
            config: PCell→gdsfactory 转换配置（None 用默认）。

        Returns:
            {cell_name: wrapped_factory} 字典，wrapped_factory(**kwargs) 返回 Component。

        Raises:
            ImportError: gdsfactory 未安装。
        """
        # 仅在此处检查 gdsfactory 可用性（R03: 不静默兜底）
        try:
            import gdsfactory as gf  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "gdsfactory 未安装，无法导出 gdsfactory cells。"
                "安装方式: pip install gdsfactory。"
                f"原始错误: {e}"
            ) from e

        from polaris.pdk.pcell_gdsfactory_bridge import pcell_to_gdsfactory_component

        cfg = config
        cells: dict[str, Callable] = {}

        for entry in self._entries.values():
            # 闭包捕获 entry，避免延迟绑定问题
            def _make_factory(ent: PolarisCellEntry, cfg=cfg):
                def _factory(**kwargs: Any):
                    pcell = self.create(ent.name, **kwargs)
                    return pcell_to_gdsfactory_component(pcell, cfg)
                _factory.__name__ = ent.name
                _factory.__doc__ = ent.description
                return _factory

            cells[entry.name] = _make_factory(entry)

        logger.info("导出 %d 个 PoLaRIS cell 为 gdsfactory cells", len(cells))
        return cells

    def register_to_gdsfactory(
        self,
        config: PCellBridgeConfig | None = None,
        pdk_name: str | None = None,
    ) -> int:
        """将注册表中的 cell 注册到 gdsfactory 活跃 PDK。

        Args:
            config: PCell→gdsfactory 转换配置。
            pdk_name: 目标 PDK 名（None 用当前活跃 PDK）。

        Returns:
            成功注册的 cell 数量。

        Raises:
            ImportError: gdsfactory 未安装。
            RuntimeError: PDK 不支持 register_cells 方法。
        """
        try:
            import gdsfactory as gf
            from gdsfactory.pdk import get_active_pdk
        except ImportError as e:
            raise ImportError(
                "gdsfactory 未安装，无法注册到 PDK。"
                f"原始错误: {e}"
            ) from e

        cells = self.to_gdsfactory_cells(config)
        if not cells:
            logger.warning("注册表为空，无 cell 注册到 gdsfactory PDK")
            return 0

        # 获取目标 PDK
        if pdk_name is not None:
            from gdsfactory.pdk import get_pdk
            pdk = get_pdk(pdk_name)
            pdk.activate()
        else:
            pdk = get_active_pdk()

        # gdsfactory PDK 的 register_cells 方法
        # 来源: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
        register_fn = getattr(pdk, "register_cells", None)
        if not callable(register_fn):
            raise RuntimeError(
                f"gdsfactory PDK {pdk.name!r} 不支持 register_cells 方法。"
                f"请使用 gdsfactory >= 7.0.0。"
            )

        register_fn(cells)
        logger.info("注册 %d 个 PoLaRIS cell 到 gdsfactory PDK %r",
                    len(cells), pdk.name)
        return len(cells)


# =============================================================================
# 模块级默认注册表与便捷函数
# =============================================================================
default_registry = PolarisCellRegistry()


def get_polaris_cell(name: str, **kwargs: Any) -> PCellMultiView:
    """从默认注册表获取 PCell 实例（便捷函数）。

    Args:
        name: cell 名称。
        **kwargs: 工厂函数参数。

    Returns:
        PCellMultiView 实例。

    Raises:
        KeyError: name 未注册。
        TypeError: 工厂返回值非 PCellMultiView。
    """
    return default_registry.create(name, **kwargs)


def register_polaris_cell(
    name: str | None = None,
    platform: str = "SOI",
    category: str = "passive",
    params_schema: dict[str, Any] | None = None,
    description: str = "",
    registry: PolarisCellRegistry | None = None,
):
    """装饰器: 注册 PoLaRIS cell 工厂（对标 @gf.cell）。

    用法:
        @register_polaris_cell(name="mzi_2x2", platform="SOI")
        def make_mzi(length: float = 100.0) -> PCellMultiView:
            pcell = PCellMultiView("mzi_2x2", {"length": length})
            ...
            return pcell

    Args:
        name: cell 名称（None 用函数名）。
        platform: 工艺平台。
        category: 类别。
        params_schema: 参数 schema。
        description: 描述（None 用函数 docstring）。
        registry: 目标注册表（None 用 default_registry）。

    Returns:
        装饰器函数。

    Raises:
        ValueError: name 已注册 / name 为空。
        TypeError: 被装饰对象不可调用。
    """
    # 注意: 不能用 `registry or default_registry`，因为 PolarisCellRegistry 定义了
    # __len__，空注册表 len()==0 会被当作 falsy，导致回退到 default_registry。
    # 必须用 `is not None` 显式判断（R05 Bug 必修）。
    reg = registry if registry is not None else default_registry

    def decorator(func: Callable[..., PCellMultiView]):
        cell_name = name or func.__name__
        desc = description if description else (func.__doc__ or "").strip()
        reg.register(
            name=cell_name,
            factory=func,
            platform=platform,
            category=category,
            params_schema=params_schema or {},
            description=desc,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> PCellMultiView:
            return func(*args, **kwargs)

        # 附加注册元数据
        wrapper.polaris_cell_name = cell_name
        wrapper.polaris_platform = platform
        wrapper.polaris_category = category
        return wrapper

    return decorator


def register_to_gdsfactory(
    config: PCellBridgeConfig | None = None,
    pdk_name: str | None = None,
    registry: PolarisCellRegistry | None = None,
) -> int:
    """将默认注册表的 cell 注册到 gdsfactory PDK（便捷函数）。

    Args:
        config: PCell→gdsfactory 转换配置。
        pdk_name: 目标 PDK 名（None 用当前活跃 PDK）。
        registry: 目标注册表（None 用 default_registry）。

    Returns:
        成功注册的 cell 数量。

    Raises:
        ImportError: gdsfactory 未安装。
        RuntimeError: PDK 不支持 register_cells。
    """
    # 显式判断 None，避免空注册表被当作 falsy（同 register_polaris_cell 修复）
    reg = registry if registry is not None else default_registry
    return reg.register_to_gdsfactory(config, pdk_name)
