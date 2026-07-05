"""PDK 器件目录公共工具（polaris-pdk 子模块）。

从 ``catalog.py`` 拆分而来，包含平台元信息（_PLATFORM_META）和来源标注
构造函数（_src），供主 catalog.py 和4个平台子模块共享。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。
"""

from __future__ import annotations

from typing import Any

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


def _src(title: str, authors: str, year: int, url: str) -> dict[str, Any]:
    """构建来源标注 dict（R02 学术诚信，每个器件可溯源）。"""
    return {"title": title, "authors": authors, "year": year, "url": url}


__all__ = ["PLATFORM_META", "_src"]
