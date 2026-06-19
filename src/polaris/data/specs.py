"""PoLaRIS 光子电路规格数据类。

定义光子器件和电路的核心数据结构。

来源:
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeviceSpec:
    """器件规格。

    Attributes:
        name: 器件名称。
        device_type: 器件类型（mzi/ring/dc/mmi/heater/gc/wg/y_branch等）。
        width_um: 器件宽度（μm）。
        height_um: 器件高度（μm）。
        ports: 端口列表 [(name, dx, dy, direction), ...]。
        params: 器件参数。
    """

    name: str
    device_type: str
    width_um: float = 10.0
    height_um: float = 10.0
    ports: list[tuple[str, float, float, str]] = field(default_factory=list)
    params: dict = field(default_factory=dict)


@dataclass
class CircuitSpec:
    """电路规格。

    Attributes:
        name: 电路名称。
        devices: 器件列表。
        connections: 连接列表 [(dev1, port1, dev2, port2), ...]。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
    """

    name: str
    devices: list[DeviceSpec] = field(default_factory=list)
    connections: list[tuple[str, str, str, str]] = field(default_factory=list)
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0


__all__ = ["DeviceSpec", "CircuitSpec"]
