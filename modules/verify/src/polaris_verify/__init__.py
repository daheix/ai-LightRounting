"""PoLaRIS DRC/LVS 验证子模块（polaris-verify）。

提供稳定的 Python API（run_drc/run_lvs），对已布局电路执行 DRC 设计规则
检查与 LVS 网表一致性比对，输出违规清单、通过率、一致性结果与差异清单。

## 设计原则

- 对外 API 返回 JSON-serializable dict（与 polaris-core / polaris-place 一致）
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 校验失败 raise RuntimeError，不返回哨兵值
- DRC 规则阈值基于 SiEPIC EBeam PDK 真实工艺规则（R02 学术诚信，可溯源）

## DRC 规则（12 条，基于 SiEPIC EBeam PDK）

min_spacing 1.0μm / min_width 0.5μm / min_height 0.4μm / min_area 0.1μm² /
boundary / no_overlap / port_alignment(5μm) / port_direction /
port_connectivity / port_facing / density_max(80%) / density_min(0.01%)

## 来源（R02 学术诚信，≥5 个文献 URL）

- SiEPIC EBeam PDK DRC runset
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/books/silicon-photonics-design/
- KLayout DRC 文档
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS API
  https://www.klayout.org/doc-qt5/manual/lvs.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  https://doi.org/10.1109/DAC56929.2023.10247734
- Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则）
- Berg et al. 2014, "Computational Geometry", Springer（AABB 几何）
  https://doi.org/10.1007/978-3-540-77974-2
"""

from __future__ import annotations

from polaris_verify.drc import (
    DEFAULT_DRC_RULES,
    DRCEngine,
    DRCRule,
    DRCViolation,
    CheckType,
    run_drc_rules,
)
from polaris_verify.lvs import (
    LVSMismatch,
    LVSMismatchType,
    Netlist,
    compare_netlists,
    extract_netlist,
    run_lvs_check,
)

__version__ = "5.0.0"


def run_drc(circuit: dict, placements: dict) -> dict:
    """对已布局电路执行 DRC 设计规则检查，返回结果 dict。

    对 circuit + placements 运行 12 条 SiEPIC PDK DRC 规则（min_spacing /
    min_width / min_area / boundary / overlap / port_alignment 等），输出违规
    清单与通过率。

    Args:
        circuit: polaris-core 风格 circuit dict（含 name/devices/connections/
            canvas_w/canvas_h）。每个 device 含 ports 列表
            [(name, dx, dy, direction), ...]。
        placements: polaris-place 输出的布局结果 {name: {x, y, w, h}}，
            x/y 为器件左下角坐标 (μm)。

    Returns:
        DRC 结果 dict::

            {
                "n_rules": int,           # 规则总数（12）
                "n_violations": int,      # 违规总数
                "n_passed": int,          # 通过规则数（无违规的规则数）
                "pass_rate": float,       # 通过率 = n_passed / n_rules
                "violations": list[dict], # 违规清单
            }

        每个 violation dict 含:
            {rule_name, severity, message, device_name, location}

    Raises:
        RuntimeError: circuit/placements 结构非法（R03 禁止 fall-back）。
    """
    rules = DEFAULT_DRC_RULES
    engine = DRCEngine(rules)
    violations = engine.run(circuit, placements)
    # 统计通过的规则数（某规则无违规即视为通过）
    violated_rules = {v.rule_name for v in violations}
    n_passed = sum(1 for r in rules if r.name not in violated_rules)
    n_rules = len(rules)
    pass_rate = n_passed / n_rules if n_rules > 0 else 0.0
    return {
        "n_rules": n_rules,
        "n_violations": len(violations),
        "n_passed": n_passed,
        "pass_rate": pass_rate,
        "violations": [
            {
                "rule_name": v.rule_name,
                "severity": v.severity,
                "message": v.message,
                "device_name": v.device_name,
                "location": list(v.location),
            }
            for v in violations
        ],
    }


def run_lvs(circuit: dict, netlist: dict = None) -> dict:
    """对电路执行 LVS 网表比对，返回结果 dict。

    从 circuit 提取参考网表，与 netlist（提取网表）比对器件数/连接数一致性。
    当 ``netlist=None`` 时，参考网表与自身比对（验证 API 一致性，必然一致）。

    Args:
        circuit: polaris-core 风格 circuit dict（含 devices/connections）。
        netlist: 提取网表 dict（含 devices/connections），None 时用 circuit
            自身派生的网表（自比对）。

    Returns:
        LVS 结果 dict::

            {
                "is_consistent": bool,       # 是否完全一致
                "n_mismatches": int,         # 不匹配项数
                "mismatches": list[dict],    # 不匹配详情
                "n_devices": int,            # 参考网表器件数
                "n_connections": int,        # 参考网表连接数
            }

    Raises:
        RuntimeError: circuit/netlist 结构非法（R03 禁止 fall-back）。
    """
    return run_lvs_check(circuit, netlist)


__all__ = [
    "run_drc",
    "run_lvs",
    "DRCEngine",
    "DRCRule",
    "DRCViolation",
    "CheckType",
    "DEFAULT_DRC_RULES",
    "run_drc_rules",
    "Netlist",
    "LVSMismatch",
    "LVSMismatchType",
    "extract_netlist",
    "compare_netlists",
    "run_lvs_check",
    "__version__",
]
