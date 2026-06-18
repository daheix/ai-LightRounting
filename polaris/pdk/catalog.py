"""光器件清单注册表与检索 API（Task 7）。

``DeviceCatalog`` 提供统一的器件注册、按平台/类别检索与序列化能力，
聚合 SOI/SiN/InP/LNOI 四大平台器件库。设计参考光子 PDK 业界最佳实践：

- gdsfactory PDK 的 ``register_cells`` / ``get_component`` 字典注册与按名检索
  模式（PDK 作为中央注册表，按字符串名解析器件）
  来源: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
- gdsfactory ``Pdk`` 类的 activate + 全局查找架构（模块级单例 + 字典存储）
  来源: https://deepwiki.com/gdsfactory/gdsfactory/2.5-process-design-kit-(pdk)-system
- IPKISS/Luceda PDK 的器件库管理与文档溯源体系（每个器件标注来源）
  来源: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone

序列化采用 JSON/YAML 双格式，支持 ``Device``/``Port``/``Source``/
``BoundingBox`` 完整重建（反序列化时恢复原始对象）。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import yaml

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source

# ---------------------------------------------------------------------------
# 序列化辅助函数（Device/Port/Source/BoundingBox ↔ dict）
# ---------------------------------------------------------------------------

def _port_to_dict(port: Port) -> dict[str, Any]:
    """将 Port 序列化为可 JSON/YAML 序列化的字典。"""
    return {
        "name": port.name,
        "x": port.x,
        "y": port.y,
        "direction": port.direction.value,
        "waveguide_type": port.waveguide_type,
        "width": port.width,
    }


def _port_from_dict(data: dict[str, Any]) -> Port:
    """从字典重建 Port 对象（含 Direction 枚举恢复）。"""
    return Port(
        name=data["name"],
        x=data["x"],
        y=data["y"],
        direction=Direction(data["direction"]),
        waveguide_type=data["waveguide_type"],
        width=data["width"],
    )


def _bbox_to_dict(bbox: BoundingBox) -> dict[str, float]:
    """将 BoundingBox 序列化为字典。"""
    return {
        "xmin": bbox.xmin,
        "ymin": bbox.ymin,
        "xmax": bbox.xmax,
        "ymax": bbox.ymax,
    }


def _bbox_from_dict(data: dict[str, Any]) -> BoundingBox:
    """从字典重建 BoundingBox 对象。"""
    return BoundingBox(
        xmin=data["xmin"],
        ymin=data["ymin"],
        xmax=data["xmax"],
        ymax=data["ymax"],
    )


def _source_to_dict(source: Source | None) -> dict[str, Any] | None:
    """将 Source 序列化为字典（None 时返回 None）。"""
    if source is None:
        return None
    return {
        "title": source.title,
        "authors": source.authors,
        "year": source.year,
        "url": source.url,
        "note": source.note,
    }


def _source_from_dict(data: dict[str, Any] | None) -> Source | None:
    """从字典重建 Source 对象（None 时返回 None）。"""
    if data is None:
        return None
    return Source(
        title=data["title"],
        authors=data["authors"],
        year=data["year"],
        url=data["url"],
        note=data.get("note", ""),
    )


def _device_to_dict(device: Device) -> dict[str, Any]:
    """将 Device 序列化为可 JSON/YAML 序列化的字典。

    包含 device_id, platform, category, name, ports, bbox, params,
    source, constraints 全部字段。
    """
    return {
        "device_id": device.device_id,
        "platform": device.platform,
        "category": device.category,
        "name": device.name,
        "ports": [_port_to_dict(p) for p in device.ports],
        "bbox": _bbox_to_dict(device.bbox),
        "params": dict(device.params),
        "source": _source_to_dict(device.source),
        "constraints": dict(device.constraints),
    }


def _device_from_dict(data: dict[str, Any]) -> Device:
    """从字典重建 Device 对象（含 Port/Source/BoundingBox 完整重建）。"""
    return Device(
        device_id=data["device_id"],
        platform=data["platform"],
        category=data["category"],
        name=data["name"],
        ports=[_port_from_dict(p) for p in data["ports"]],
        bbox=_bbox_from_dict(data["bbox"]),
        params=dict(data.get("params", {})),
        source=_source_from_dict(data.get("source")),
        constraints=dict(data.get("constraints", {})),
    )


# ---------------------------------------------------------------------------
# 序列化混入（将 to_dict/to_json/to_yaml/from_json 分离为独立 Mixin，
# 降低 DeviceCatalog 的方法数，满足规则 4.1 类方法数上限）
# ---------------------------------------------------------------------------


class CatalogSerializerMixin:
    """DeviceCatalog 序列化混入（JSON/YAML 导入导出）。

    将序列化能力分离为独立混入，降低 ``DeviceCatalog`` 的方法数（规则 4.1）。
    依赖宿主类提供 ``_devices`` 字典与 ``register`` 方法。

    设计参考 gdsfactory PDK 的序列化与重建模式
    （来源: https://gdsfactory.github.io/gdsfactory/）。
    """

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（含 device_id, platform, category, name, params, source 等）。

        Returns:
            形如 ``{"devices": [device_dict, ...]}`` 的字典，每个 device_dict
            包含完整字段，可被 JSON/YAML 序列化。
        """
        return {"devices": [_device_to_dict(d) for d in self._devices.values()]}

    def to_json(self, path: str) -> None:
        """导出为 JSON 文件。

        Args:
            path: 输出 JSON 文件路径。
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def to_yaml(self, path: str) -> None:
        """导出为 YAML 文件。

        Args:
            path: 输出 YAML 文件路径。
        """
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)

    @classmethod
    def from_json(cls, path: str) -> DeviceCatalog:
        """从 JSON 文件加载（重建 Device 对象）。

        反序列化时重建 ``Device``/``Port``/``Source``/``BoundingBox`` 对象，
        恢复 ``Direction`` 枚举。

        Args:
            path: JSON 文件路径。

        Returns:
            重建后的 ``DeviceCatalog`` 实例。
        """
        catalog = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for device_data in data.get("devices", []):
            catalog.register(_device_from_dict(device_data))
        return catalog


# ---------------------------------------------------------------------------
# DeviceCatalog 注册表
# ---------------------------------------------------------------------------

class DeviceCatalog(CatalogSerializerMixin):
    """光器件清单注册表，支持按平台/类别检索与序列化。

    以 ``device_id`` 为键存储 ``Device`` 对象，提供按平台（SOI/SiN/InP/LNOI）、
    按类别（passive/active/source/detector）及组合检索，并支持
    JSON/YAML 序列化与反序列化重建。

    设计参考 gdsfactory PDK 的 ``register_cells`` / ``get_component`` 字典注册
    与按名检索模式
    （来源: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html）。
    """

    def __init__(self) -> None:
        # device_id -> Device 实例（主存储）
        self._devices: dict[str, Device] = {}
        # "platform::name" -> Device 实例（按名+平台检索的辅助索引）
        self._by_name: dict[str, Device] = {}
        # 已注册平台集合
        self._platforms: set[str] = set()

    # -- 注册 --

    def register(self, device: Device) -> None:
        """注册器件（以 device_id 为键）。

        Args:
            device: 待注册的器件实例。
        """
        self._devices[device.device_id] = device
        self._by_name[f"{device.platform}::{device.name}"] = device
        self._platforms.add(device.platform)

    def register_all_from_platform(
        self, platform: str, factories: dict[str, Callable[[], Device]]
    ) -> None:
        """从平台器件工厂字典批量注册（如 SOI_DEVICES）。

        遍历工厂字典，调用每个工厂函数生成 ``Device`` 并注册到清单。
        ``platform`` 参数标识器件所属平台，与器件自身的 ``platform`` 字段一致。

        Args:
            platform: 平台名（SOI/SiN/InP/LNOI）。
            factories: 器件名 → 工厂函数的字典（如 ``SOI_DEVICES``）。
        """
        for factory in factories.values():
            device = factory()
            self.register(device)

    def register_platform(
        self, platform: str, factories: dict[str, Callable[[], Device]]
    ) -> None:
        """从平台器件工厂字典批量注册（``register_all_from_platform`` 的别名）。

        保留以兼容既有调用方。
        """
        self.register_all_from_platform(platform, factories)

    def register_all_builtin(self) -> DeviceCatalog:
        """注册四大平台（SOI/SiN/InP/LNOI）全部内置器件，返回 self 以支持链式调用。"""
        from polaris.pdk.inp import INP_DEVICES
        from polaris.pdk.lnoi import LNOI_DEVICES
        from polaris.pdk.sin import SIN_DEVICES
        from polaris.pdk.soi import SOI_DEVICES

        self.register_all_from_platform("SOI", SOI_DEVICES)
        self.register_all_from_platform("SiN", SIN_DEVICES)
        self.register_all_from_platform("InP", INP_DEVICES)
        self.register_all_from_platform("LNOI", LNOI_DEVICES)
        return self

    # -- 检索 --

    def get(self, device_id: str, platform: str | None = None) -> Device:
        """按 device_id 检索单个器件。

        当 ``platform`` 为 None 时，按 ``device_id`` 在实例表中检索；
        当提供 ``platform`` 时，将 ``device_id`` 视为器件名（name），
        按 ``平台::名`` 检索（兼容网表解析器按组件名 + 平台查找的用法）。

        Args:
            device_id: 器件唯一标识（或器件名，当提供 platform 时）。
            platform: 平台名过滤（None 表示按 device_id 检索）。

        Returns:
            对应的 ``Device`` 实例。

        Raises:
            KeyError: 器件不在注册表中。
        """
        if platform is not None:
            key = f"{platform}::{device_id}"
            try:
                return self._by_name[key]
            except KeyError:
                raise KeyError(
                    f"器件 '{device_id}' (平台 {platform}) 不在清单中"
                ) from None
        try:
            return self._devices[device_id]
        except KeyError:
            raise KeyError(f"器件 '{device_id}' 不在清单中") from None

    def list_by_platform(self, platform: str) -> list[Device]:
        """按平台检索（SOI/SiN/InP/LNOI）。

        Args:
            platform: 平台名。

        Returns:
            匹配平台的器件列表。
        """
        return [d for d in self._devices.values() if d.platform == platform]

    def list_by_category(self, category: str) -> list[Device]:
        """按类别检索（passive/active/source/detector）。

        Args:
            category: 器件类别。

        Returns:
            匹配类别的器件列表。
        """
        return [d for d in self._devices.values() if d.category == category]

    def list_all(self) -> list[Device]:
        """列出所有器件。

        Returns:
            注册表中所有器件的列表。
        """
        return list(self._devices.values())

    def list_devices(
        self, platform: str | None = None, category: str | None = None
    ) -> list[Device]:
        """按平台/类别组合检索（``search`` 的别名，兼容既有调用方）。"""
        return self.search(platform=platform, category=category)

    def search(
        self, platform: str | None = None, category: str | None = None
    ) -> list[Device]:
        """组合检索（平台+类别）。

        任一参数为 None 时表示该维度不过滤；两者均提供时取交集。

        Args:
            platform: 平台名过滤（None 表示不过滤）。
            category: 类别过滤（None 表示不过滤）。

        Returns:
            同时满足平台与类别条件的器件列表。
        """
        result = self.list_all()
        if platform is not None:
            result = [d for d in result if d.platform == platform]
        if category is not None:
            result = [d for d in result if d.category == category]
        return result

    # -- 平台/名称元信息 --

    @property
    def platforms(self) -> list[str]:
        """已注册平台列表（按字母排序）。"""
        return sorted(self._platforms)

    def names(self, platform: str | None = None) -> list[str]:
        """已注册器件名列表（可选按平台过滤，去重并排序）。"""
        result: list[str] = []
        for dev in self._devices.values():
            if platform is None or dev.platform == platform:
                result.append(dev.name)
        return sorted(set(result))

    # -- 迭代与长度 --

    def __iter__(self) -> Iterator[Device]:
        """迭代注册表中所有器件实例。"""
        return iter(self._devices.values())

    def __len__(self) -> int:
        """注册表中器件数量。"""
        return len(self._devices)

    # -- 来源溯源校验 --

    def validate_sources(self) -> list[str]:
        """校验所有器件的 source.url 非空，返回缺失来源的 device_id 列表。

        Returns:
            source 为 None 或 url 为空的 device_id 列表（空列表表示全部合规）。
        """
        missing: list[str] = []
        for device in self._devices.values():
            if device.source is None or not device.source.url:
                missing.append(device.device_id)
        return missing

    def assert_all_sourced(self) -> None:
        """断言所有器件 source.url 非空，否则抛出 ValueError。"""
        violations = self.validate_sources()
        if violations:
            raise ValueError(f"以下器件缺少 source.url: {violations}")


# ---------------------------------------------------------------------------
# 默认目录加载函数
# ---------------------------------------------------------------------------

def default_catalog() -> DeviceCatalog:
    """创建并加载包含四大平台所有器件的默认目录。

    从 SOI_DEVICES、SIN_DEVICES、INP_DEVICES、LNOI_DEVICES 加载所有器件，
    构建覆盖 SOI/SiN/InP/LNOI 四大平台的完整器件清单。

    Returns:
        包含四大平台全部器件的 ``DeviceCatalog`` 实例。
    """
    return DeviceCatalog().register_all_builtin()


def build_default_catalog() -> DeviceCatalog:
    """构建包含四大平台全部器件的默认目录（``default_catalog`` 的别名）。

    保留以兼容网表解析器等既有调用方。
    """
    return default_catalog()
