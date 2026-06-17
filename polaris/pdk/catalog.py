"""器件清单注册表与检索 API（Task 7）。

提供统一的 ``DeviceCatalog`` 注册表，聚合四大平台（SOI/SiN/InP/LNOI）器件工厂，
支持按平台/类别/名称检索、序列化（JSON/YAML）与参数溯源校验（source.url 非空）。

设计参考光子 PDK 业界实践：
- gdsfactory 的 ``PDK`` 注册表（按 name 检索 cell 工厂）
  来源: https://gdsfactory.github.io/gdsfactory/
- IPKISS/Luceda PDK 的 ``pdk.cells`` 字典检索
  来源: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import asdict
from pathlib import Path

import yaml

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source


def _direction_to_str(d: Direction) -> str:
    return d.value


def _str_to_direction(s: str) -> Direction:
    return Direction(s)


def device_to_dict(device: Device) -> dict:
    """将 ``Device`` 序列化为可 JSON/YAML 序列化的字典。"""
    return {
        "device_id": device.device_id,
        "platform": device.platform,
        "category": device.category,
        "name": device.name,
        "ports": [
            {
                "name": p.name,
                "x": p.x,
                "y": p.y,
                "direction": _direction_to_str(p.direction),
                "waveguide_type": p.waveguide_type,
                "width": p.width,
            }
            for p in device.ports
        ],
        "bbox": asdict(device.bbox),
        "params": device.params,
        "source": asdict(device.source) if device.source else None,
        "constraints": device.constraints,
    }


def device_from_dict(data: dict) -> Device:
    """从字典反序列化为 ``Device``。"""
    ports = [
        Port(
            name=p["name"],
            x=p["x"],
            y=p["y"],
            direction=_str_to_direction(p["direction"]),
            waveguide_type=p["waveguide_type"],
            width=p["width"],
        )
        for p in data.get("ports", [])
    ]
    bbox = BoundingBox(**data["bbox"])
    source = Source(**data["source"]) if data.get("source") else None
    return Device(
        device_id=data["device_id"],
        platform=data["platform"],
        category=data["category"],
        name=data["name"],
        ports=ports,
        bbox=bbox,
        params=data.get("params", {}),
        source=source,
        constraints=data.get("constraints", {}),
    )


class DeviceCatalog:
    """器件清单注册表（按平台/类别/名称检索）。

    聚合四大平台器件工厂，支持实例化、检索与序列化。
    所有器件须通过溯源校验（``source.url`` 非空，禁止假数据）。
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Device]] = {}
        self._platforms: set[str] = set()

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------
    def register_platform(self, platform: str, factories: dict[str, Callable[[], Device]]) -> None:
        """注册某平台的器件工厂字典。"""
        for name, factory in factories.items():
            key = f"{platform}::{name}"
            self._factories[key] = factory
        self._platforms.add(platform)

    def register_all_builtin(self) -> "DeviceCatalog":
        """注册全部内置平台器件（SOI/SiN/InP/LNOI）。"""
        from polaris.pdk.inp import INP_DEVICES
        from polaris.pdk.lnoi import LNOI_DEVICES
        from polaris.pdk.sin import SIN_DEVICES
        from polaris.pdk.soi import SOI_DEVICES

        self.register_platform("SOI", SOI_DEVICES)
        self.register_platform("SiN", SIN_DEVICES)
        self.register_platform("InP", INP_DEVICES)
        self.register_platform("LNOI", LNOI_DEVICES)
        return self

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    @property
    def platforms(self) -> list[str]:
        return sorted(self._platforms)

    def names(self, platform: str | None = None) -> list[str]:
        """返回已注册器件名（可按平台过滤）。"""
        result = []
        for key in self._factories:
            plat, name = key.split("::", 1)
            if platform is None or plat == platform:
                result.append(name)
        return sorted(set(result))

    def get(self, name: str, platform: str | None = None) -> Device:
        """按名称实例化器件（可指定平台消歧）。"""
        if platform is not None:
            key = f"{platform}::{name}"
            if key not in self._factories:
                raise KeyError(f"器件未注册: {key}")
            return self._factories[key]()
        # 不指定平台时，若同名跨平台则报错要求消歧
        matches = [k for k in self._factories if k.endswith(f"::{name}")]
        if not matches:
            raise KeyError(f"器件未注册: {name}")
        if len(matches) > 1:
            plats = [k.split("::")[0] for k in matches]
            raise KeyError(f"器件 {name} 跨平台存在: {plats}，请指定 platform")
        return self._factories[matches[0]]()

    def list_devices(
        self,
        platform: str | None = None,
        category: str | None = None,
    ) -> list[Device]:
        """列出器件（可按平台/类别过滤）。"""
        result = []
        for key, factory in self._factories.items():
            plat, _ = key.split("::", 1)
            if platform is not None and plat != platform:
                continue
            dev = factory()
            if category is not None and dev.category != category:
                continue
            result.append(dev)
        return result

    def __iter__(self) -> Iterator[Device]:
        for factory in self._factories.values():
            yield factory()

    def __len__(self) -> int:
        return len(self._factories)

    # ------------------------------------------------------------------
    # 溯源校验（SubTask 7.3）
    # ------------------------------------------------------------------
    def validate_sources(self) -> list[str]:
        """校验所有器件 ``source.url`` 非空（禁止假数据）。

        Returns:
            违规器件的 ``device_id`` 列表（空列表表示全部通过）。
        """
        violations: list[str] = []
        for dev in self:
            if dev.source is None or not dev.source.url:
                violations.append(dev.device_id)
        return violations

    def assert_all_sourced(self) -> None:
        """断言所有器件溯源合规，否则抛出 ``ValueError``。"""
        violations = self.validate_sources()
        if violations:
            raise ValueError(f"以下器件缺少 source.url（禁止假数据）: {violations}")

    # ------------------------------------------------------------------
    # 序列化（SubTask 7.2）
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """序列化为字典（含全部器件）。"""
        return {
            "platforms": self.platforms,
            "devices": [device_to_dict(d) for d in self],
        }

    def to_json(self, path: str | Path | None = None) -> str:
        """序列化为 JSON 字符串（可写入文件）。"""
        text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def to_yaml(self, path: str | Path | None = None) -> str:
        """序列化为 YAML 字符串（可写入文件）。"""
        text = yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text


def build_default_catalog() -> DeviceCatalog:
    """构建包含全部内置平台器件的默认注册表。"""
    catalog = DeviceCatalog()
    catalog.register_all_builtin()
    return catalog
