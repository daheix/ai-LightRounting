"""LVS（Layout Versus Schematic）网表比对引擎（polaris-lvs 子模块）。

从原 ``polaris-verify/src/polaris_verify/lvs.py`` 拆分而来（R13 代码清理：
禁止多个 vx 文件并存，新建立就彻底删除老的）。仅依赖 numpy（R04: 不参与 GPU）。

## Input → Process → Output 三段式

### Input
- ``circuit: dict`` — polaris-core 风格电路规格（含 devices/connections）
- ``netlist: dict | None`` — 提取网表（None 时自比对）

### Process
1. 从 circuit 提取参考网表（器件名+类型 + 拓扑连接）
2. 与提取网表比对: 器件集合差集 + 器件类型一致性 + 连接集合差集

### Output
不匹配列表 ``list[LVSMismatch]``，空列表表示 LVS clean / 完全一致

## LVS 流程

1. 从 circuit dict 提取参考网表（器件 + 连接关系）
2. 若提供 ``netlist`` 参数，将其作为提取网表（版图网表）
3. 比对两个网表，报告不匹配（缺失/多余器件、缺失/多余连接、器件类型不匹配）

## 光子电路 LVS 特点

与电子电路 LVS（MOS/BJT 器件提取）不同，光子电路 LVS 通过:
- 器件实例名 + 器件类型识别器件
- 连接关系（dev1.port1 ↔ dev2.port2）识别网表拓扑

## 设计原则

- 对外 API 返回 JSON-serializable dict（与 polaris-core 一致）
- 禁止 fall-back（R03）: 校验失败 raise RuntimeError，不返回哨兵值
- 当 ``netlist=None`` 时，参考网表与自身比对（验证 API 正确性，必然 consistent）

## 来源（R02 学术诚信，≥5 个文献 URL）
- KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK DEVREC 标准（器件识别层 layer 68）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory PDK 文档（网表提取）
  https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS（光子电路网表验证）
  https://www.lucedaphotonics.com/en/products/ipkiss
- Calibre nmLVS（工业 LVS 比对算法）
  https://eda.sw.siemens.com/en-US/calibre/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

__all__ = [
    "LVSMismatchType",
    "LVSMismatch",
    "Netlist",
    "extract_netlist",
    "compare_netlists",
    "run_lvs_check",
]


class LVSMismatchType(Enum):
    """LVS 不匹配类型（与 KLayout LVS 比对状态对应）。

    来源: KLayout LVS 比对状态
    https://www.klayout.org/doc-qt5/manual/lvs.html
    """

    MISSING_DEVICE = "missing_device"
    EXTRA_DEVICE = "extra_device"
    DEVICE_TYPE_MISMATCH = "device_type_mismatch"
    MISSING_CONNECTION = "missing_connection"
    EXTRA_CONNECTION = "extra_connection"


@dataclass
class LVSMismatch:
    """单个 LVS 不匹配项。

    Attributes:
        mtype: 不匹配类型。
        message: 描述信息。
        device_name: 相关器件名（可选）。
        net_name: 相关网名（可选）。
    """

    mtype: LVSMismatchType
    message: str
    device_name: str = ""
    net_name: str = ""


@dataclass
class Netlist:
    """网表结构（器件 + 连接）。

    Attributes:
        devices: 器件信息列表 [{name, device_type}, ...]。
        connections: 连接列表 [(dev1, dev2), ...]（无端口，仅拓扑）。
    """

    devices: list[dict] = field(default_factory=list)
    connections: list[tuple[str, str]] = field(default_factory=list)


def extract_netlist(circuit: dict) -> Netlist:
    """从 circuit dict 提取参考网表。

    Args:
        circuit: polaris-core 风格 circuit dict（含 devices/connections）。

    Returns:
        参考网表（器件名+类型列表 + 拓扑连接列表）。

    Raises:
        RuntimeError: circuit 结构非法（R03 禁止 fall-back）。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    if "devices" not in circuit or "connections" not in circuit:
        raise RuntimeError("circuit 缺少 devices/connections 字段")
    devices: list[dict] = []
    for dev in circuit["devices"]:
        if "name" not in dev or "device_type" not in dev:
            raise RuntimeError(
                f"器件缺 name/device_type 字段: {dev}（R03 禁止 fall-back）"
            )
        devices.append({"name": dev["name"], "device_type": dev["device_type"]})
    connections: list[tuple[str, str]] = []
    for conn in circuit["connections"]:
        if not isinstance(conn, (list, tuple)) or len(conn) != 4:
            raise RuntimeError(
                f"connection 必须是长度 4 的 list/tuple [dev1,port1,dev2,port2]，"
                f"得到: {conn}（R03 禁止 fall-back）"
            )
        connections.append((conn[0], conn[2]))
    return Netlist(devices=devices, connections=connections)


def compare_netlists(reference: Netlist, extracted: Netlist) -> list[LVSMismatch]:
    """比对参考网表与提取网表，返回不匹配列表。

    比对项:
    - 器件集合差集（缺失/多余器件）
    - 器件类型一致性（同名器件类型不匹配）
    - 连接集合差集（缺失/多余连接，连接归一化为有序对去重）

    Args:
        reference: 参考网表（来自 circuit）。
        extracted: 提取网表（来自版图或 netlist 参数）。

    Returns:
        不匹配列表（空列表表示 LVS clean / 完全一致）。
    """
    mismatches: list[LVSMismatch] = []
    mismatches.extend(_compare_devices(reference, extracted))
    mismatches.extend(_compare_connections(reference, extracted))
    return mismatches


def _compare_devices(reference: Netlist, extracted: Netlist) -> list[LVSMismatch]:
    """比对器件集合（缺失/多余/类型不匹配）。"""
    ref_map = {d["name"]: d["device_type"] for d in reference.devices}
    ext_map = {d["name"]: d["device_type"] for d in extracted.devices}
    mismatches: list[LVSMismatch] = []
    for name in ref_map.keys() - ext_map.keys():
        mismatches.append(LVSMismatch(
            mtype=LVSMismatchType.MISSING_DEVICE,
            message=f"参考网表有器件 '{name}' 但提取网表无",
            device_name=name,
        ))
    for name in ext_map.keys() - ref_map.keys():
        mismatches.append(LVSMismatch(
            mtype=LVSMismatchType.EXTRA_DEVICE,
            message=f"提取网表有器件 '{name}' 但参考网表无",
            device_name=name,
        ))
    for name in ref_map.keys() & ext_map.keys():
        if ref_map[name] != ext_map[name]:
            mismatches.append(LVSMismatch(
                mtype=LVSMismatchType.DEVICE_TYPE_MISMATCH,
                message=(f"器件 '{name}' 类型不匹配: "
                         f"参考={ref_map[name]} 提取={ext_map[name]}"),
                device_name=name,
            ))
    return mismatches


def _compare_connections(reference: Netlist, extracted: Netlist) -> list[LVSMismatch]:
    """比对连接集合（缺失/多余连接，归一化有序对去重）。"""
    ref_conns = {_normalize_conn(c) for c in reference.connections}
    ext_conns = {_normalize_conn(c) for c in extracted.connections}
    mismatches: list[LVSMismatch] = []
    for conn in ref_conns - ext_conns:
        mismatches.append(LVSMismatch(
            mtype=LVSMismatchType.MISSING_CONNECTION,
            message=f"参考网表有连接 {conn} 但提取网表无",
            net_name=f"{conn[0]}-{conn[1]}",
        ))
    for conn in ext_conns - ref_conns:
        mismatches.append(LVSMismatch(
            mtype=LVSMismatchType.EXTRA_CONNECTION,
            message=f"提取网表有连接 {conn} 但参考网表无",
            net_name=f"{conn[0]}-{conn[1]}",
        ))
    return mismatches


def _normalize_conn(conn: tuple[str, str]) -> tuple[str, str]:
    """连接归一化为有序对（dev 名字典序），消除方向差异。"""
    return tuple(sorted(conn))  # type: ignore[return-value]


def run_lvs_check(circuit: dict, netlist: dict | None = None) -> dict:
    """执行 LVS 网表比对，返回结果 dict。

    Args:
        circuit: polaris-core 风格 circuit dict。
        netlist: 提取网表 dict（含 devices/connections），None 时用 circuit
            自身派生的网表（自比对，验证 API 一致性）。

    Returns:
        LVS 结果 dict::

            {
                "is_consistent": bool,       # 是否完全一致（无不匹配）
                "n_mismatches": int,         # 不匹配项数
                "mismatches": list[dict],    # 不匹配详情
                "n_devices": int,            # 参考网表器件数
                "n_connections": int,        # 参考网表连接数
            }

    Raises:
        RuntimeError: circuit/netlist 结构非法（R03 禁止 fall-back）。
    """
    reference = extract_netlist(circuit)
    if netlist is None:
        # 自比对: 验证 extract_netlist + compare_netlists API 正确性
        extracted = reference
    else:
        extracted = _parse_netlist_dict(netlist)
    mismatches = compare_netlists(reference, extracted)
    return {
        "is_consistent": len(mismatches) == 0,
        "n_mismatches": len(mismatches),
        "mismatches": [
            {
                "type": m.mtype.value,
                "message": m.message,
                "device_name": m.device_name,
                "net_name": m.net_name,
            }
            for m in mismatches
        ],
        "n_devices": len(reference.devices),
        "n_connections": len(reference.connections),
    }


def _parse_netlist_dict(netlist: dict) -> Netlist:
    """将 netlist dict 解析为 Netlist 结构（R03: 结构非法 raise）。

    netlist dict 格式::

        {
            "devices": [{"name": str, "device_type": str}, ...],
            "connections": [[dev1, dev2], ...]  # 或 [[dev1,port1,dev2,port2], ...]
        }
    """
    if not isinstance(netlist, dict):
        raise RuntimeError(
            f"netlist 必须是 dict，得到 {type(netlist).__name__}"
        )
    if "devices" not in netlist or "connections" not in netlist:
        raise RuntimeError("netlist 缺少 devices/connections 字段")
    devices: list[dict] = []
    for dev in netlist["devices"]:
        if "name" not in dev or "device_type" not in dev:
            raise RuntimeError(
                f"netlist 器件缺 name/device_type 字段: {dev}（R03 禁止 fall-back）"
            )
        devices.append({"name": dev["name"], "device_type": dev["device_type"]})
    connections: list[tuple[str, str]] = []
    for conn in netlist["connections"]:
        if not isinstance(conn, (list, tuple)) or len(conn) < 2:
            raise RuntimeError(
                f"netlist connection 格式非法: {conn}（R03 禁止 fall-back）"
            )
        # 兼容 [dev1, dev2] 与 [dev1, port1, dev2, port2] 两种格式
        connections.append((str(conn[0]), str(conn[2] if len(conn) >= 4 else conn[1])))
    return Netlist(devices=devices, connections=connections)


# numpy 引用占位（保留依赖一致性，R04 纯 NumPy）
_ = np
