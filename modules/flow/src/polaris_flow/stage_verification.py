"""PoLaRIS 流水线仿真与验证阶段（阶段 3、7、8）。

包含原理图级电路仿真（stage3，版图前）、版图后仿真（stage7，含布线
寄生）与 DRC/LVS 约束检查（stage8）。这三个阶段对齐工业界
"先仿真后版图、版图后再验证"的标准光电子设计流程：

    原理图捕获 → 原理图电路仿真（stage3）→ 布局布线 →
    版图后仿真（stage7）→ DRC/LVS 物理验证（stage8）

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- SiEPIC EBeam PDK strip waveguide 几何约定与损耗典型值
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory 端到端流水线
  https://gdsfactory.github.io/gdsfactory/
- IPKISS Schematic-Driven Layout 流程（原理图仿真先于版图）
  https://docs.lucedaphotonics.com/
- Synopsys OptoCompiler schematic-driven 设计流程
  https://www.synopsys.com/photonic-solutions.html
- KLayout DRC 引擎（开源光子/电子设计规则检查）
  https://www.klayout.de/manual/drc_engine.html
- Calibre Standard Verification Rule Format (SVRF)（Mentor/Siemens 商业 DRC 标准）
  https://docs.sw.siemens.com/en-US/doc/186265592
- OpenROAD KLayout integration（端到端验证流程参考）
  https://github.com/The-OpenROAD-Project/OpenROAD
- Bogaerts et al. 2018, "Layout-Aware Yield Prediction of Photonic
  Circuits", OFC（版图后损耗预算：互连损耗+交叉损耗）
  https://fib.intec.ugent.be/download/pub_4125.pdf

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

import logging

from polaris_flow.recipe import Recipe
from polaris_flow.stage_serializers import (
    _circuit_from_dict,
    _require_input,
)
from polaris_flow.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 阶段 3: 原理图级电路仿真（版图前）
# =============================================================================


def stage3_simulation(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 3: 原理图级电路仿真（版图前，工业流程"先仿真后版图"）。

    用 _DefaultSimulator.simulate_schematic 基于器件紧凑模型（查表
    S 参数/损耗）计算原理图级总插入损耗。本阶段在布局布线之前执行，
    仅依赖电路规格，输出不含交叉数（原理图无布线几何，交叉数未定义，
    由 stage7 版图后仿真基于真实布线统计）。

    工业流程依据:
    - Luceda IPKISS: schematic capture → circuit simulation → layout
      https://docs.lucedaphotonics.com/
    - Synopsys OptoCompiler: 原理图仿真先于物理实现
      https://www.synopsys.com/photonic-solutions.html

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit"）。

    Returns:
        含 sparams/total_loss_db/device_losses 的字典。
    """
    from polaris_flow.default_simulator import (
        _DefaultSimulator,
        supplement_waveguide_lengths,
    )

    circuit_dict = _require_input(prev_outputs, "circuit", 3)
    circuit = _circuit_from_dict(circuit_dict)

    logger.info("阶段 3: 原理图级电路仿真（紧凑模型查表，版图前）")

    # 为缺少 length 参数的波导器件补充长度（基于器件物理尺寸）
    # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
    n_supplemented = supplement_waveguide_lengths(circuit)

    simulator = _DefaultSimulator(mode="table")
    result = simulator.simulate_schematic(circuit)

    total_loss_db = float(result["total_loss_db"])
    device_losses = result["device_losses"]

    # sparams: 序列化原理图仿真结果（含逐器件损耗分解）
    sparams = {
        "total_loss_db": total_loss_db,
        "n_devices": len(circuit.devices),
        "n_connections": len(circuit.connections),
        "wavelength_nm": circuit.optical_wavelength_nm,
        "level": "schematic",
    }
    logger.info(
        "阶段 3 完成: 原理图总损耗 %.4f dB（%d 器件，补充波导长度 %d 个）",
        total_loss_db, len(device_losses), n_supplemented,
    )

    return {
        "sparams": sparams,
        "total_loss_db": total_loss_db,
        "device_losses": device_losses,
    }


# =============================================================================
# 阶段 7: 版图后仿真（含布线寄生）
# =============================================================================


def stage7_postlayout_sim(
    recipe: Recipe, workspace: Workspace, prev_outputs: dict
) -> dict:
    """阶段 7: 版图后仿真（含布线互连损耗与交叉损耗）。

    在布局布线完成后，基于真实布线几何重新评估链路损耗预算：
    - 器件损耗：与 stage3 原理图一致（紧凑模型查表）
    - 互连损耗：布线路径总长度 × SOI 波导损耗系数 3.0 dB/cm
    - 交叉损耗：实际布线交叉数 × SiEPIC 交叉插损 0.2 dB

    损耗预算模型来源:
    - Bogaerts et al. 2018 OFC, "Layout-Aware Yield Prediction of
      Photonic Circuits"（版图感知损耗/良率预算方法）
      https://fib.intec.ugent.be/download/pub_4125.pdf
    - SiEPIC EBeam PDK: SOI strip waveguide 3.0 dB/cm、
      ebeam_crossing4 交叉插损 0.2 dB
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit",
            "routes", "total_length_um", "total_loss_db"）。

    Returns:
        含 postlayout_loss_db/loss_budget/n_crossings 的字典。
    """
    from polaris_flow.default_simulator import (
        _DefaultSimulator,
        _count_path_crossings,
        supplement_waveguide_lengths,
    )

    circuit_dict = _require_input(prev_outputs, "circuit", 7)
    routes = _require_input(prev_outputs, "routes", 7)
    total_length_um = float(_require_input(prev_outputs, "total_length_um", 7))
    schematic_loss_db = float(_require_input(prev_outputs, "total_loss_db", 7))
    circuit = _circuit_from_dict(circuit_dict)

    logger.info("阶段 7: 版图后仿真（含布线寄生）")

    # 器件损耗（与原理图一致的紧凑模型查表，波导长度补充幂等）
    supplement_waveguide_lengths(circuit)
    simulator = _DefaultSimulator(mode="table")
    device_loss_db = float(simulator.simulate_schematic(circuit)["total_loss_db"])

    # 互连损耗: 布线路径总长度 × 3.0 dB/cm（SOI strip，SiEPIC 典型值）
    # 3.0 dB/cm = 3.0 / 1e4 dB/μm
    interconnect_loss_db = total_length_um * 3.0 / 1e4

    # 交叉损耗: 实际布线交叉数 × 0.2 dB（SiEPIC ebeam_crossing4）
    n_crossings = _count_path_crossings(routes)
    crossing_loss_db = n_crossings * 0.2

    postlayout_loss_db = device_loss_db + interconnect_loss_db + crossing_loss_db

    loss_budget = {
        "device_loss_db": float(device_loss_db),
        "interconnect_loss_db": float(interconnect_loss_db),
        "crossing_loss_db": float(crossing_loss_db),
        "postlayout_loss_db": float(postlayout_loss_db),
        "schematic_loss_db": float(schematic_loss_db),
        "layout_penalty_db": float(postlayout_loss_db - schematic_loss_db),
    }
    logger.info(
        "阶段 7 完成: 版图后总损耗 %.4f dB（器件 %.4f + 互连 %.4f + 交叉 %.4f），"
        "交叉数 %d，版图附加 %.4f dB",
        postlayout_loss_db, device_loss_db, interconnect_loss_db,
        crossing_loss_db, n_crossings, loss_budget["layout_penalty_db"],
    )

    return {
        "postlayout_loss_db": float(postlayout_loss_db),
        "loss_budget": loss_budget,
        "n_crossings": int(n_crossings),
    }


# =============================================================================
# 阶段 8: DRC/LVS 约束检查
# =============================================================================


def stage8_drc_lvs(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 8: DRC/LVS 约束检查。

    R391 修复: 原依赖 polaris_verify_advanced.ConstraintChecker（v5.0 未迁移），
    改为调用 polaris_drc.run_drc + polaris_lvs.run_lvs 稳定 API。

    DRC 规则来源: SiEPIC EBeam PDK DRC runset
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        recipe: 作业配方（使用 recipe.sim_config.loss_target_db）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit", "placements"）。

    Returns:
        含 drc_report/lvs_passed 的字典。
    """
    from polaris_drc import run_drc
    from polaris_lvs import run_lvs

    circuit_dict = _require_input(prev_outputs, "circuit", 8)
    placements = _require_input(prev_outputs, "placements", 8)

    logger.info("阶段 8: DRC/LVS 约束检查")

    # DRC: 设计规则检查（间距/宽度/弯曲半径/端口对齐等）
    drc_result = run_drc(circuit_dict, placements)
    n_violations = drc_result.get("n_violations", 0)
    drc_passed = n_violations == 0

    # LVS: 版图与原理图一致性比对
    # R05 修复: run_lvs 返回契约键为 "is_consistent"（polaris_lvs.compare.
    # run_lvs_check docstring），原读 "passed" 键导致 lvs_passed 永远 False。
    lvs_result = run_lvs(circuit_dict)
    lvs_passed = lvs_result["is_consistent"]

    logger.info(
        "阶段 8 完成: DRC %s（%d 违规），LVS %s",
        "通过" if drc_passed else "失败", n_violations,
        "通过" if lvs_passed else "失败",
    )

    return {
        "drc_report": {
            "violations": drc_result.get("violations", []),
            "n_violations": int(n_violations),
            "passed": bool(drc_passed),
        },
        "lvs_passed": bool(lvs_passed),
    }


__all__ = [
    "stage3_simulation",
    "stage7_postlayout_sim",
    "stage8_drc_lvs",
]
