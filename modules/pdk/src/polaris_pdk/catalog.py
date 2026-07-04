"""PDK 器件目录主入口（polaris-pdk 子模块，facade 层）。

从 src/polaris/pdk/ 四大平台（SOI/SiN/InP/LNOI）迁移并精简为 36 个代表性器件，
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

v5.2 拆分（R11 质量门禁：文件 ≤800 行）:
- ``devices.py``: 36 器件纯数据结构（DEVICES + make_source）
- ``filters.py``: 平台元信息 + 查询逻辑（PLATFORM_META + list_devices + get_device）
- ``catalog.py``: 主入口 facade（list_platforms + 重新导出，保持 API 兼容）

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

from polaris_pdk.devices import DEVICES
from polaris_pdk.filters import PLATFORM_META, get_device, list_devices


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
    for plat, meta in PLATFORM_META.items():
        devs = [d for d in DEVICES if d["platform"] == plat]
        platforms.append({
            "platform": plat,
            "foundry": meta["foundry"],
            "process_node": meta["process_node"],
            "device_count": len(devs),
            "device_names": [d["device_type"] for d in devs],
        })
    return platforms


__all__ = ["list_platforms", "list_devices", "get_device"]
