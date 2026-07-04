"""PDK 器件查询/过滤逻辑（polaris-pdk 子模块，查询层）。

从 catalog.py 拆分而来（R11 质量门禁：文件 ≤800 行）。本文件包含
平台元信息（PLATFORM_META）与器件查询函数（list_devices / get_device），
基于 devices.DEVICES 数据构建索引并对外提供 JSON-serializable dict。

设计原则:
- 禁止 fall-back（R03）：平台/器件未找到 raise RuntimeError，不返回假数据
- 查询返回深拷贝，避免调用方修改内部数据
- 纯数据结构（R04 不参与 GPU）

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from typing import Any

from polaris_pdk.devices import DEVICES

# ---------------------------------------------------------------------------
# 平台元信息（foundry / 工艺节点 / 来源 URL）
# ---------------------------------------------------------------------------
# 来源:
# - SiEPIC EBeam PDK: 220nm SOI, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# - Ligentec ANR: SiN TriPleX, https://www.ligentec.com/
# - Pattern Project / JEPPIX: InP generic, https://www.jeppix.eu/
# - HyperLight: LNOI X-cut, https://hyperlightphotonics.com/
PLATFORM_META: dict[str, dict[str, str]] = {
    "SOI": {
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "pdk": "SiEPIC EBeam PDK",
        "url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    },
    "SiN": {
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "pdk": "Ligentec ANR PDK",
        "url": "https://www.ligentec.com/",
    },
    "InP": {
        "foundry": "Pattern Project",
        "process_node": "InP generic",
        "pdk": "Pattern Project InP PDK",
        "url": "https://www.jeppix.eu/",
    },
    "LNOI": {
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "pdk": "HyperLight LNOI PDK",
        "url": "https://hyperlightphotonics.com/",
    },
}


# ---------------------------------------------------------------------------
# 检索索引（device_id = "platform::device_type"）
# ---------------------------------------------------------------------------
_INDEX: dict[str, dict[str, Any]] = {
    f"{d['platform']}::{d['device_type']}": d for d in DEVICES
}


def list_devices(platform: str) -> list[dict[str, Any]]:
    """列出指定平台的所有器件，返回 device dict 列表。

    Args:
        platform: 平台名（SOI/SiN/InP/LNOI）。

    Returns:
        该平台所有器件的 dict 列表（深拷贝，避免调用方修改内部数据）。

    Raises:
        RuntimeError: 平台不存在（R03 禁止 fall-back）。
    """
    if platform not in PLATFORM_META:
        available = list(PLATFORM_META.keys())
        raise RuntimeError(
            f"平台 '{platform}' 不存在（可用: {available}）"
        )
    return [_copy_device(d) for d in DEVICES if d["platform"] == platform]


def get_device(platform: str, device_type: str) -> dict[str, Any]:
    """获取指定平台的指定器件，返回 device dict。

    Args:
        platform: 平台名（如 "SOI"）。
        device_type: 器件类型（如 "grating_coupler"）。

    Returns:
        器件规格 dict（含 params 来源标注、source 文献溯源、ports、bbox_um）。

    Raises:
        RuntimeError: 平台或器件不存在（R03 禁止 fall-back，不返回假数据）。
    """
    if platform not in PLATFORM_META:
        available = list(PLATFORM_META.keys())
        raise RuntimeError(
            f"平台 '{platform}' 不存在（可用: {available}）"
        )
    key = f"{platform}::{device_type}"
    if key not in _INDEX:
        names = [d["device_type"] for d in DEVICES if d["platform"] == platform]
        raise RuntimeError(
            f"器件 '{device_type}' 不在平台 {platform} 中（可用: {names}）"
        )
    return _copy_device(_INDEX[key])


def _copy_device(d: dict[str, Any]) -> dict[str, Any]:
    """深拷贝器件 dict（含嵌套 params/source/bbox_um/ports）。"""
    return {
        "platform": d["platform"],
        "device_type": d["device_type"],
        "name": d["name"],
        "category": d["category"],
        "foundry": d["foundry"],
        "process_node": d["process_node"],
        "params": dict(d["params"]),
        "source": dict(d["source"]),
        "ports": [list(p) for p in d["ports"]],
        "bbox_um": dict(d["bbox_um"]),
    }


__all__ = ["PLATFORM_META", "list_devices", "get_device"]
