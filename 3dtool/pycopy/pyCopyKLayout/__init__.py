"""pyCopyKLayout — klayout DRC 纯 Python 100% 复刻（规则 3/21）。

复刻 KLayout 的 DRC 规则检查功能，包括弯曲半径/间距/插入损耗/串扰/
交叉/重叠/热串扰/最小宽度/耦合间隙 8 种违规检查。

原工具: KLayout https://www.klayout.de/ (GPL-2.0)
复刻位置: src/polaris/sim/constraint_checker.py
复刻功能: 8 种 DRC 规则检查

版本历史: 见 VERSION.md
- v1.0.0 (2026-06-21): 100% 复刻完成，6 个对比测试通过

来源:
- KLayout DRC: https://www.klayout.de/doc/about/drc.html
- SiEPIC EBeam PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from polaris.sim.constraint_checker import (
    CheckContext,
    ConstraintChecker,
    ConstraintConfig,
    Violation,
    ViolationType,
    check_bend_radius,
    check_coupling_gap,
    check_crossings,
    check_insertion_loss,
    check_min_width,
    check_overlap,
    check_spacing,
)

__version__ = "1.0.0"

__all__ = [
    "ConstraintChecker",
    "ConstraintConfig",
    "CheckContext",
    "Violation",
    "ViolationType",
    "check_bend_radius",
    "check_spacing",
    "check_insertion_loss",
    "check_crossings",
    "check_overlap",
    "check_min_width",
    "check_coupling_gap",
    "__version__",
]
