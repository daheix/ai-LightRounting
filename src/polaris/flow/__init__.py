<<<<<<< HEAD
"""PoLaRIS 设计流程模块。

R25 路标：Luceda IPKISS 全流程对齐（PCell 多视图 + SDL 闭环）。

学术依据：Bogaerts et al., "The IPKISS photonic design framework", OFC 2016
URL: https://fotonica.intec.ugent.be/download/pub_3902.pdf
"""

from polaris.flow.ipkiss_flow import (
    ClosedLoopValidator,
    CircuitModelView,
=======
"""IPKISS 风格光子电路设计流程（R25 路标）。

对标 Luceda IPKISS 的 PCell + 多视图架构与 Schematic-Driven Layout 闭环验证。

来源:
- IPKISS: https://www.lucedaphotonics.com/products/ipkiss
"""

from polaris.flow.ipkiss_flow import (
    CircuitModelView,
    ClosedLoopValidator,
>>>>>>> trae/solo-agent-pkVjID
    IPKISSPCell,
    IPKISSPDKBridge,
    IPKISSView,
    LayoutView,
    NetlistView,
    SDLFlow,
)

__all__ = [
<<<<<<< HEAD
    "ClosedLoopValidator",
    "CircuitModelView",
    "IPKISSPCell",
    "IPKISSPDKBridge",
    "IPKISSView",
    "LayoutView",
    "NetlistView",
    "SDLFlow",
=======
    "IPKISSPCell",
    "IPKISSView",
    "NetlistView",
    "LayoutView",
    "CircuitModelView",
    "SDLFlow",
    "ClosedLoopValidator",
    "IPKISSPDKBridge",
>>>>>>> trae/solo-agent-pkVjID
]
