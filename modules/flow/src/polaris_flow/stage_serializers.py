"""PoLaRIS 流水线阶段序列化辅助函数。

提供 CircuitSpec/DeviceSpec 与可 JSON 序列化字典之间的双向转换，
以及阶段间依赖输入校验。所有阶段执行器通过本模块共享同一份序列化
逻辑，避免重复实现导致行为不一致。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。原文件实现 10 个标准化
阶段执行函数，序列化辅助为多阶段共用部分，独立成模块以便复用与测试。

## 学术来源

- IPKISS Schematic-Driven Layout 流程
  https://docs.lucedaphotonics.com/
- gdsfactory 端到端流水线
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- Matres et al. 2024 GDSFactory paper: https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- gdsfactory PDK 文档: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
"""

from __future__ import annotations

from typing import Any

from polaris_core.specs import CircuitSpec, DeviceSpec


def _device_spec_to_dict(dev: DeviceSpec) -> dict[str, Any]:
    """将 DeviceSpec 序列化为可 JSON 序列化的字典。"""
    return {
        "name": dev.name,
        "device_type": dev.device_type,
        "width_um": dev.width_um,
        "height_um": dev.height_um,
        "ports": [list(p) for p in dev.ports],
        "params": dict(dev.params),
        "process_node": dev.process_node,
    }


def _device_spec_from_dict(data: dict[str, Any]) -> DeviceSpec:
    """从字典重建 DeviceSpec 对象。"""
    return DeviceSpec(
        name=data["name"],
        device_type=data["device_type"],
        width_um=data.get("width_um", 10.0),
        height_um=data.get("height_um", 10.0),
        ports=[tuple(p) for p in data.get("ports", [])],
        params=dict(data.get("params", {})),
        process_node=data.get("process_node"),
    )


def _circuit_to_dict(circuit: CircuitSpec) -> dict[str, Any]:
    """将 CircuitSpec 序列化为可 JSON 序列化的字典。"""
    return {
        "name": circuit.name,
        "devices": [_device_spec_to_dict(d) for d in circuit.devices],
        "connections": [list(c) for c in circuit.connections],
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "process_node": circuit.process_node,
        "optical_wavelength_nm": circuit.optical_wavelength_nm,
    }


def _circuit_from_dict(data: dict[str, Any]) -> CircuitSpec:
    """从字典重建 CircuitSpec 对象。"""
    return CircuitSpec(
        name=data["name"],
        devices=[_device_spec_from_dict(d) for d in data.get("devices", [])],
        connections=[tuple(c) for c in data.get("connections", [])],
        canvas_w=data.get("canvas_w", 1000.0),
        canvas_h=data.get("canvas_h", 1000.0),
        process_node=data.get("process_node"),
        optical_wavelength_nm=data.get("optical_wavelength_nm", 1550.0),
    )


def _require_input(prev_outputs: dict, key: str, stage_id: int) -> Any:
    """校验依赖输入是否存在，缺失时 raise ValueError。

    Args:
        prev_outputs: 之前所有阶段的输出字典。
        key: 所需输入的键名。
        stage_id: 当前阶段 ID（用于错误信息）。

    Returns:
        对应的输入值。

    Raises:
        ValueError: 输入缺失时。
    """
    if key not in prev_outputs:
        raise ValueError(
            f"阶段 {stage_id} 缺少依赖输入 '{key}'。"
            f"请确保前置阶段已执行并输出该键。"
            f"当前 prev_outputs 可用键: {list(prev_outputs.keys())}"
        )
    return prev_outputs[key]


__all__ = [
    "_device_spec_to_dict",
    "_device_spec_from_dict",
    "_circuit_to_dict",
    "_circuit_from_dict",
    "_require_input",
]
