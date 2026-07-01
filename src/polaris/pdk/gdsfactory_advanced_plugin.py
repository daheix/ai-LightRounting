"""R309 gdsfactory 插件接口 — 注册为第三方插件。

批次 10-B 拆分说明（2026-07-01）:
    从 gdsfactory_advanced.py 抽出 R309 插件注册模块。

来源（R02 学术诚信，≥5 文献 URL）:
1. gdsfactory PDK tutorial: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
2. gdsfactory PDK import: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
3. gdsfactory API: https://gdsfactory.github.io/gdsfactory/api.html
4. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
5. gdsfactory plugins: https://gdsfactory.github.io/gplugins/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

# gdsfactory 可选导入（R309 插件注册需要）。
try:  # pragma: no cover - 环境依赖
    import gdsfactory as gf

    _HAS_GDSFACTORY = True
except ImportError:  # pragma: no cover - 环境依赖
    gf = None  # type: ignore[assignment]
    _HAS_GDSFACTORY = False


@dataclass
class GDSFactoryPluginEntry:
    """gdsfactory 插件注册项（R309）。

    Attributes:
        name: 插件名（gdsfactory cell 名）。
        factory: 组件工厂回调（返回 gdsfactory.Component）。
        version: 插件版本。
        description: 描述。
        registered_with_pdk: 是否已注册到活跃 gdsfactory PDK。
    """

    name: str
    factory: Callable[..., Any]
    version: str
    description: str = ""
    registered_with_pdk: bool = False


# PoLaRIS 插件内部注册表（与 gdsfactory PDK 注册解耦）
_POLARIS_PLUGIN_REGISTRY: dict[str, GDSFactoryPluginEntry] = {}


def declare_plugin(
    name: str,
    factory: Callable[..., Any],
    version: str = "0.1.0",
    description: str = "",
) -> GDSFactoryPluginEntry:
    """声明 PoLaRIS 插件（仅加入内部注册表，不依赖 gdsfactory，R309）。

    Args:
        name: 插件名。
        factory: 组件工厂回调。
        version: 版本。
        description: 描述。

    Returns:
        GDSFactoryPluginEntry 实例。

    Raises:
        ValueError: name 为空或 factory 不可调用。
    """
    if not name:
        raise ValueError("插件名不能为空")
    if not callable(factory):
        raise ValueError(f"插件 {name!r} 的 factory 不可调用")
    entry = GDSFactoryPluginEntry(
        name=name, factory=factory, version=version, description=description
    )
    _POLARIS_PLUGIN_REGISTRY[name] = entry
    return entry


def register_as_gdsfactory_plugin(
    name: str,
    factory: Callable[..., Any],
    version: str = "0.1.0",
    description: str = "",
) -> GDSFactoryPluginEntry:
    """将 PoLaRIS 组件注册为 gdsfactory 第三方插件（R309，需 gdsfactory）。

    先加入内部注册表，再注册到活跃 gdsfactory PDK。

    Args:
        name: gdsfactory cell 名。
        factory: 组件工厂回调（返回 gdsfactory.Component）。
        version: 插件版本。
        description: 描述。

    Returns:
        GDSFactoryPluginEntry 实例（registered_with_pdk=True）。

    Raises:
        ImportError: gdsfactory 未安装（R03：不静默兜底）。
    """
    entry = declare_plugin(name, factory, version, description)
    if not _HAS_GDSFACTORY:
        raise ImportError(
            "gdsfactory 未安装，无法注册为 gdsfactory 插件。"
            "请执行 pip install gdsfactory 或检查 Python 版本兼容性。"
        )
    pdk = gf.get_active_pdk()  # type: ignore[union-attr]
    pdk.register_cells(**{name: factory})
    entry.registered_with_pdk = True
    logger.info("PoLaRIS 插件 %s v%s 已注册到 gdsfactory PDK", name, version)
    return entry


def list_registered_plugins() -> list[str]:
    """列出内部注册表中的插件名（R309，不依赖 gdsfactory）。"""
    return sorted(_POLARIS_PLUGIN_REGISTRY.keys())


def get_plugin(name: str) -> GDSFactoryPluginEntry:
    """获取插件注册项（R309）。

    Args:
        name: 插件名。

    Returns:
        GDSFactoryPluginEntry 实例。

    Raises:
        KeyError: 插件未注册（R03：不返回 None）。
    """
    if name not in _POLARIS_PLUGIN_REGISTRY:
        raise KeyError(f"插件未注册: {name!r}（可用: {list_registered_plugins()}）")
    return _POLARIS_PLUGIN_REGISTRY[name]


__all__ = [
    "GDSFactoryPluginEntry",
    "declare_plugin",
    "register_as_gdsfactory_plugin",
    "list_registered_plugins",
    "get_plugin",
]
