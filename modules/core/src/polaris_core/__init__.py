"""PoLaRIS 核心数据结构（polaris-core 子模块）。

提供稳定的 Python API（make_device/make_circuit/validate_circuit/Tensor），
其他子模块（place/route/sim/verify/export/pipe）依赖本模块。

设计原则:
- 对外 API 返回 JSON-serializable dict，不返回 dataclass（避免内部对象泄漏）
- dataclass 仅内部使用（specs.py）
- 禁止 fall-back（R03）：validate 失败 raise RuntimeError
- 纯 NumPy 实现（R04: 不参与 GPU）

来源:
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- TILOS MacroPlacement benchmark: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo PTC/oNoC 光子 benchmark: https://github.com/ASU-LOPE-Group/Apollo
- PyTorch autograd: https://pytorch.org/docs/stable/autograd.html
- SiEPIC PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from typing import Any

from polaris_core.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)
from polaris_core.tensor import Tensor

__version__ = "5.0.0"


def _require_keys(obj: dict, keys: tuple[str, ...], label: str) -> None:
    """校验 dict 包含必要键，缺失则 raise RuntimeError（R03: 禁止 fall-back）。

    Args:
        obj: 待校验 dict。
        keys: 必要键元组。
        label: 校验对象标签（用于错误信息）。
    """
    missing = [k for k in keys if k not in obj]
    if missing:
        raise RuntimeError(
            f"{label} 缺少必要字段: {missing}（已有字段: {list(obj.keys())}）"
        )


def _device_to_dict(dev: Any) -> dict:
    """将 DeviceSpec 或 device dict 转换为 JSON-serializable dict。

    Args:
        dev: DeviceSpec 实例或 device dict。

    Returns:
        JSON-serializable device dict（ports 转为 list of list）。

    Raises:
        RuntimeError: dev 类型非法。
    """
    if isinstance(dev, DeviceSpec):
        return {
            "name": dev.name,
            "device_type": dev.device_type,
            "width_um": float(dev.width_um),
            "height_um": float(dev.height_um),
            "ports": [list(p) for p in dev.ports],
            "params": dict(dev.params),
            "process_node": dev.process_node,
        }
    if isinstance(dev, dict):
        # 已是 dict，校验必要字段后重建（确保 JSON-serializable）
        _require_keys(dev, ("name", "device_type", "width_um", "height_um"), "device")
        return {
            "name": dev["name"],
            "device_type": dev["device_type"],
            "width_um": float(dev["width_um"]),
            "height_um": float(dev["height_um"]),
            "ports": [list(p) for p in dev.get("ports", [])],
            "params": dict(dev.get("params", {})),
            "process_node": dev.get("process_node"),
        }
    raise RuntimeError(
        f"device 必须是 DeviceSpec 或 dict，得到 {type(dev).__name__}"
    )


def make_device(
    name: str,
    device_type: str,
    width_um: float = 10.0,
    height_um: float = 10.0,
    ports: list | None = None,
    params: dict | None = None,
    process_node: str | None = None,
) -> dict:
    """创建器件规格，返回 JSON-serializable dict。

    Args:
        name: 器件实例名（如 "gc1"）。
        device_type: 器件类型（如 "grating_coupler"）。
        width_um: 器件宽度（μm）。
        height_um: 器件高度（μm）。
        ports: 端口列表 [(name, dx, dy, direction), ...]。
        params: 器件参数 dict。
        process_node: 工艺节点（如 "220nm SOI"）。

    Returns:
        JSON-serializable device dict。
    """
    spec = DeviceSpec(
        name=name,
        device_type=device_type,
        width_um=float(width_um),
        height_um=float(height_um),
        ports=[tuple(p) for p in (ports or [])],
        params=dict(params or {}),
        process_node=process_node,
    )
    return _device_to_dict(spec)


def make_circuit(
    name: str,
    devices: list,
    connections: list,
    canvas_w: float = 1000.0,
    canvas_h: float = 1000.0,
    process_node: str | None = None,
    optical_wavelength_nm: float = 1550.0,
) -> dict:
    """创建电路规格，返回 JSON-serializable dict。

    Args:
        name: 电路名（如 "MZI"）。
        devices: 器件列表（DeviceSpec 或 dict 均可）。
        connections: 连接列表 [(dev1, port1, dev2, port2), ...]。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        process_node: 工艺节点（如 "220nm SOI"）。
        optical_wavelength_nm: 工作波长（nm，默认 1550）。

    Returns:
        JSON-serializable circuit dict。
    """
    device_dicts = [_device_to_dict(d) for d in devices]
    conn_lists = [list(c) for c in connections]
    return {
        "name": name,
        "devices": device_dicts,
        "connections": conn_lists,
        "canvas_w": float(canvas_w),
        "canvas_h": float(canvas_h),
        "process_node": process_node,
        "optical_wavelength_nm": float(optical_wavelength_nm),
    }


def circuit_to_dict(circuit: Any) -> dict:
    """将 CircuitSpec 或 dict 转换为 JSON-serializable dict。

    已是 dict 则校验后重建返回（保证字段一致性与 JSON 可序列化）。

    Args:
        circuit: CircuitSpec 实例或 circuit dict。

    Returns:
        JSON-serializable circuit dict。

    Raises:
        RuntimeError: circuit 类型非法或 dict 缺少必要字段。
    """
    if isinstance(circuit, CircuitSpec):
        return {
            "name": circuit.name,
            "devices": [_device_to_dict(d) for d in circuit.devices],
            "connections": [list(c) for c in circuit.connections],
            "canvas_w": float(circuit.canvas_w),
            "canvas_h": float(circuit.canvas_h),
            "process_node": circuit.process_node,
            "optical_wavelength_nm": float(circuit.optical_wavelength_nm),
        }
    if isinstance(circuit, dict):
        _require_keys(
            circuit,
            ("name", "devices", "connections", "canvas_w", "canvas_h"),
            "circuit",
        )
        return {
            "name": circuit["name"],
            "devices": [_device_to_dict(d) for d in circuit["devices"]],
            "connections": [list(c) for c in circuit["connections"]],
            "canvas_w": float(circuit["canvas_w"]),
            "canvas_h": float(circuit["canvas_h"]),
            "process_node": circuit.get("process_node"),
            "optical_wavelength_nm": float(circuit.get("optical_wavelength_nm", 1550.0)),
        }
    raise RuntimeError(
        f"circuit 必须是 CircuitSpec 或 dict，得到 {type(circuit).__name__}"
    )


def _validate_circuit_devices(devices: list) -> None:
    """校验每个 device 的字段类型（R03: 失败即 raise）。"""
    for i, dev in enumerate(devices):
        if not isinstance(dev, dict):
            raise RuntimeError(
                f"circuit.devices[{i}] 必须是 dict，得到 {type(dev).__name__}"
            )
        _require_keys(
            dev,
            ("name", "device_type", "width_um", "height_um"),
            f"circuit.devices[{i}]",
        )
        if not isinstance(dev["name"], str):
            raise RuntimeError(f"circuit.devices[{i}].name 必须是 str")
        if not isinstance(dev["device_type"], str):
            raise RuntimeError(f"circuit.devices[{i}].device_type 必须是 str")
        if not isinstance(dev["width_um"], (int, float)):
            raise RuntimeError(f"circuit.devices[{i}].width_um 必须是 number")
        if not isinstance(dev["height_um"], (int, float)):
            raise RuntimeError(f"circuit.devices[{i}].height_um 必须是 number")
        ports = dev.get("ports", [])
        if not isinstance(ports, list):
            raise RuntimeError(f"circuit.devices[{i}].ports 必须是 list")
        params = dev.get("params", {})
        if not isinstance(params, dict):
            raise RuntimeError(f"circuit.devices[{i}].params 必须是 dict")


def _validate_circuit_connections(connections: list, dev_names: set) -> None:
    """校验连接引用的器件存在（防止悬空连接，R03: 失败即 raise）。"""
    for i, conn in enumerate(connections):
        if not isinstance(conn, (list, tuple)) or len(conn) != 4:
            raise RuntimeError(
                f"circuit.connections[{i}] 必须是长度 4 的 list/tuple "
                f"[dev1, port1, dev2, port2]"
            )
        dev1, _port1, dev2, _port2 = conn
        if dev1 not in dev_names:
            raise RuntimeError(
                f"circuit.connections[{i}] 引用了不存在的器件: {dev1}"
            )
        if dev2 not in dev_names:
            raise RuntimeError(
                f"circuit.connections[{i}] 引用了不存在的器件: {dev2}"
            )


def validate_circuit(circuit: dict) -> bool:
    """验证 circuit dict 结构完整性，失败 raise RuntimeError（R03: 禁止 fall-back）。

    校验项:
    - circuit 为 dict
    - 含必要字段: name(str), devices(list), connections(list),
      canvas_w(number), canvas_h(number), optical_wavelength_nm(number)
    - 每个 device 含必要字段: name(str), device_type(str),
      width_um(number), height_um(number), ports(list), params(dict)
    - 每条 connection 为长度 4 的 list/tuple，且引用的器件名存在

    Args:
        circuit: 待验证的 circuit dict。

    Returns:
        True（验证通过）。失败时 raise RuntimeError。

    Raises:
        RuntimeError: 结构不完整或类型不符。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    _require_keys(
        circuit,
        ("name", "devices", "connections", "canvas_w", "canvas_h"),
        "circuit",
    )
    if not isinstance(circuit["name"], str):
        raise RuntimeError("circuit.name 必须是 str")
    if not isinstance(circuit["devices"], list):
        raise RuntimeError("circuit.devices 必须是 list")
    if not isinstance(circuit["connections"], list):
        raise RuntimeError("circuit.connections 必须是 list")
    if not isinstance(circuit["canvas_w"], (int, float)):
        raise RuntimeError("circuit.canvas_w 必须是 number")
    if not isinstance(circuit["canvas_h"], (int, float)):
        raise RuntimeError("circuit.canvas_h 必须是 number")
    wl = circuit.get("optical_wavelength_nm", 1550.0)
    if not isinstance(wl, (int, float)):
        raise RuntimeError("circuit.optical_wavelength_nm 必须是 number")
    _validate_circuit_devices(circuit["devices"])
    dev_names = {d["name"] for d in circuit["devices"]}
    _validate_circuit_connections(circuit["connections"], dev_names)
    return True


__all__ = [
    "make_device",
    "make_circuit",
    "circuit_to_dict",
    "validate_circuit",
    "Tensor",
    "DeviceSpec",
    "CircuitSpec",
    "BenchmarkSource",
    "TargetMetric",
    "__version__",
]
