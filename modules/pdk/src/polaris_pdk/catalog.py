"""PDK 器件目录主入口（polaris-pdk 子模块）。

本文件为 ``catalog`` 模块对外 API 入口，内部器件数据已按平台拆分为:
- ``catalog_soi``: SOI 平台 9 器件（SiEPIC EBeam PDK, 220nm SOI）
- ``catalog_sin``: SiN 平台 9 器件（Ligentec ANR PDK, SiN TriPleX）
- ``catalog_inp``: InP 平台 9 器件（Pattern Project / JEPPIX, InP generic）
- ``catalog_lnoi``: LNOI 平台 9 器件（HyperLight LNOI PDK, X-cut TFLN）
- ``catalog_common``: 公共工具（_src 来源标注 + _PLATFORM_META 平台元信息）

从 src/polaris/pdk/ 四大平台（SOI/SiN/InP/LNOI）迁移并精简为 36 个代表性器件，
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

设计原则:
- 纯数据结构（list[dict]），无内部对象泄漏，对外 API 返回 JSON-serializable dict
- 每个器件 params 含 ``pdk_reference`` 字段标注来源 PDK（SiEPIC EBeam PDK /
  Ligentec / Pattern Project / HyperLight）
- 禁止 fall-back（R03）：器件未找到 raise RuntimeError

平台与 foundry 来源标注:
- SOI  → SiEPIC EBeam PDK (220nm SOI), https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiN  → Ligentec ANR PDK (SiN TriPleX), https://www.ligentec.com/
- InP  → Pattern Project / JEPPIX InP generic, https://www.jeppix.eu/
- LNOI → HyperLight LNOI PDK (X-cut TFLN), https://hyperlightphotonics.com/

文献溯源（R02，均经 WebSearch 验证可访问）:
- SiEPIC EBeam PDK (UBC, MIT): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 三星 300mm 硅光平台 OFC 2026:
  https://cloud.tencent.com.cn/developer/article/2650050
- LioniX TriPleX SiN 波导技术:
  https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
- Ligentec ANR SiN PDK: https://www.ligentec.com/
- Soares et al., "InP-Based Foundry PICs for Optical Interconnects",
  Appl. Sci. 2019, 9(8), 1588 — https://doi.org/10.3390/app9081588
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47 —
  https://doi.org/10.37188/lam.2025.047
- Wang et al., Nature 2018, 562:101-104 — https://doi.org/10.1038/s41586-018-0551-y
- Zhu et al., Adv. Opt. Photonics 2021, 13:242-352 —
  https://doi.org/10.1364/AOP.411024

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。
"""

from __future__ import annotations

from typing import Any

from .catalog_common import PLATFORM_META as _PLATFORM_META
from .catalog_common import _src
from .catalog_inp import DEVICES_INP
from .catalog_lnoi import DEVICES_LNOI
from .catalog_sin import DEVICES_SIN
from .catalog_soi import DEVICES_SOI

# ---------------------------------------------------------------------------
# 36 器件目录（4 平台 × 9 器件，合并自各平台子模块）
# ---------------------------------------------------------------------------
# 每个器件 dict 字段:
#   platform / device_type / name / category / foundry / process_node
#   params（含 pdk_reference 标注来源 PDK）
#   source（文献溯源 dict）
#   ports（端口列表 [(name, x_um, y_um, direction), ...]）
#   bbox_um（包围盒 {xmin, ymin, xmax, ymax}）
_DEVICES: list[dict[str, Any]] = (
    list(DEVICES_SOI) + list(DEVICES_SIN) + list(DEVICES_INP) + list(DEVICES_LNOI)
)


# ---------------------------------------------------------------------------
# 检索索引（device_id = "platform::device_type"）
# ---------------------------------------------------------------------------
_INDEX: dict[str, dict[str, Any]] = {
    f"{d['platform']}::{d['device_type']}": d for d in _DEVICES
}


def list_platforms() -> list[dict[str, Any]]:
    """列出所有 PDK 平台（4 平台），返回 JSON-serializable dict 列表。

    每个平台 dict 含:
    - platform: 平台名（SOI/SiN/InP/LNOI）
    - foundry: foundry 名（SiEPIC/Ligentec/Pattern Project/HyperLight）
    - process_node: 工艺节点（如 "220nm SOI"）
    - device_count: 该平台器件数
    - device_names: 该平台器件类型名列表

    Returns:
        4 个平台信息的 dict 列表。
    """
    platforms: list[dict[str, Any]] = []
    for plat, meta in _PLATFORM_META.items():
        devs = [d for d in _DEVICES if d["platform"] == plat]
        platforms.append({
            "platform": plat,
            "foundry": meta["foundry"],
            "process_node": meta["process_node"],
            "device_count": len(devs),
            "device_names": [d["device_type"] for d in devs],
        })
    return platforms


def list_devices(platform: str) -> list[dict[str, Any]]:
    """列出指定平台的所有器件，返回 device dict 列表。

    Args:
        platform: 平台名（SOI/SiN/InP/LNOI）。

    Returns:
        该平台所有器件的 dict 列表（深拷贝，避免调用方修改内部数据）。

    Raises:
        RuntimeError: 平台不存在（R03 禁止 fall-back）。
    """
    if platform not in _PLATFORM_META:
        available = list(_PLATFORM_META.keys())
        raise RuntimeError(
            f"平台 '{platform}' 不存在（可用: {available}）"
        )
    return [_copy_device(d) for d in _DEVICES if d["platform"] == platform]


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
    if platform not in _PLATFORM_META:
        available = list(_PLATFORM_META.keys())
        raise RuntimeError(
            f"平台 '{platform}' 不存在（可用: {available}）"
        )
    key = f"{platform}::{device_type}"
    if key not in _INDEX:
        names = [d["device_type"] for d in _DEVICES if d["platform"] == platform]
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


__all__ = ["list_platforms", "list_devices", "get_device"]
