"""文献溯源数据类（SubTask 2.3）。

每个器件的电光/几何参数都须附带 ``Source`` 以溯源至公开文献或工艺手册，
禁止使用未经检索核实的参数或假数据（见项目规则 1.1）。

溯源字段设计参考光子 PDK 业界实践：
- IPKISS/Luceda PDK 的文档体系要求每个器件/参数标注来源与工艺手册
  来源: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- gdsfactory 组件 metadata 中保留 foundry 与文献信息
  来源: https://pypi.org/project/gdsfactory/4.4.14/

补充文献（≥5，规则 R02 学术诚信）：
1. Luceda Photonics, "IPKISS / Cornerstone PDK documentation" —
   https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
2. gdsfactory, "Python library for photonics layout (PyPI)" —
   https://pypi.org/project/gdsfactory/4.4.14/
3. SiEPIC EBeam PDK, "Open-source Silicon Photonics PDK (MIT/UBC)" —
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
4. Chrostowski L, Hochberg M, "Silicon Photonics Design: From Devices
   to Systems," Cambridge University Press (2015) —
   https://www.cambridge.org/9781107085459
5. gdsfactory docs, "Component metadata and source tracking" —
   https://gdsfactory.github.io/gdsfactory/
6. Smart Photonics, "InP Photonics Foundry — Process Design Kit"
   (2024) — https://smartphotonics.nl/
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """文献来源（禁止假数据，每个参数须可溯源）。

    采用 ``frozen=True`` 使其不可变，便于作为器件 ``source`` 字段安全共享。

    Attributes:
        title: 文献/手册标题。
        authors: 作者或机构。
        year: 发表年份。
        url: 网址 URL（必填，溯源校验时须非空）。
        note: 备注（如 ``estimated`` 标注无可靠文献时的估算依据）。
    """

    title: str
    authors: str
    year: int
    url: str
    note: str = ""
