"""PoLaRIS PDK 器件库管理（polaris-pdk 子模块，单一职责）。

v5.1 起 GDSII 导入导出已拆分到 polaris-gdsio 子模块；
本模块只保留 4 平台 36 器件的目录查询（list/find/get）。

设计原则:
- 对外 API 返回 JSON-serializable dict/list，不返回 dataclass 或内部对象
- 禁止 fall-back（R03）：器件未找到 raise RuntimeError
- 所有器件参数标注来源（SiEPIC EBeam PDK / Ligentec / Pattern Project / HyperLight）
- 纯数据结构（R04: 不参与 GPU，纯 NumPy/数据结构）

=== Input / Process / Output 三段式文档 ===

Input:
- platform: str       平台名（SOI/SiN/InP/LNOI）
- device_type: str    器件类型（如 "strip_waveguide"）

Process:
- 查询 4 平台 36 器件目录（SOI/SiN/InP/LNOI × 9 器件）
- 来源 PDK:
    * SOI  → SiEPIC EBeam PDK (220nm SOI)
    * SiN  → Ligentec ANR PDK (SiN TriPleX)
    * InP  → Pattern Project / JEPPIX InP generic
    * LNOI → HyperLight LNOI PDK (X-cut TFLN)
- 每个器件 params 含 pdk_reference 字段标注来源 PDK

Output:
- list_platforms: [{platform, foundry, process_node, device_count, device_names}, ...]
- get_device: {platform, device_type, name, category, foundry, process_node,
               params, source, ports, bbox_um}
- list_devices: list[device dict]

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec ANR PDK: https://www.ligentec.com/
- Pattern Project / JEPPIX InP: https://www.jeppix.eu/
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- Soares et al., "InP-Based Foundry PICs for Optical Interconnects",
  Appl. Sci. 2019, 9(8), 1588 — https://doi.org/10.3390/app9081588
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47 —
  https://doi.org/10.37188/lam.2025.047

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from polaris_pdk.catalog import get_device, list_devices, list_platforms

__version__ = "5.1.0"

__all__ = [
    "list_platforms",
    "get_device",
    "list_devices",
    "__version__",
]
