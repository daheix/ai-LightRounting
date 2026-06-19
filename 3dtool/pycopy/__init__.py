"""pycopy — 自研复刻工具统一包（规则 3）。

本包是所有 pyCopyxx 复刻工具的统一入口，每个子包对应一个开源工具的纯 Python 复刻。

子包:
- pyCopyTorch: torch 复刻（src/polaris/nn）
- pyCopySAX: sax 复刻（src/polaris/sim/cascade.py）
- pyCopySiPANN: SiPANN 复刻（src/polaris/sim/models.py）
- pyCopyKLayout: klayout DRC 复刻（src/polaris/sim/constraint_checker.py）
- pyCopyMEEP: meep FDTD 复刻（预留）
- pyCopyFemwell: femwell 复刻（预留）
- pyCopyMeow: meow 复刻（预留）
"""

__all__ = [
    "pyCopyTorch",
    "pyCopySAX",
    "pyCopySiPANN",
    "pyCopyKLayout",
    "pyCopyMEEP",
    "pyCopyFemwell",
    "pyCopyMeow",
]
