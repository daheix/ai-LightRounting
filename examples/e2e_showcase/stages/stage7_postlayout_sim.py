"""阶段 7: 版图后仿真（含布线寄生）。

工业流程位置：布局（阶段 5）与布线（阶段 6）完成之后、DRC/LVS（阶段 8）
之前。基于真实布线几何重新评估链路损耗预算，对比原理图级（阶段 3）估算，
量化版图附加损耗（layout penalty）——这是工业光子设计"版图后验证"
的标准环节。

损耗预算模型来源（R02 学术诚信，所有参数可溯源）:
- Bogaerts et al. 2018 OFC, "Layout-Aware Yield Prediction of Photonic
  Circuits"（版图感知损耗/良率预算方法）
  https://fib.intec.ugent.be/download/pub_4125.pdf
- SiEPIC EBeam PDK: SOI strip waveguide 3.0 dB/cm、单弯 0.05 dB、
  单次交叉 0.3 dB（crossing_te1550 上界）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref et al. 1993, IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm 传播损耗基准）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, §3.3
  https://www.cambridge.org/9781107083456
- Pozar, "Microwave Engineering", 4th ed., §4（dB 域级联损耗可加和）
  https://www.wiley.com/en-us/Microwave+Engineering

合规: R02 学术诚信 / R03 禁止 fall-back（失败即 raise）/ R04 不参与 GPU。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from polaris_core import CircuitSpec, circuit_to_dict
from polaris_place import place_circuit
from polaris_route import route_circuit
from polaris_route.curvy import path_length

from stages.stage6_routing import _build_circuits

_logger = logging.getLogger("e2e_showcase")

# 损耗模型常数（来源见模块 docstring）
_PROPAGATION_LOSS_DB_CM = 3.0  # SOI strip 波导传播损耗（Soref 1993 / SiEPIC）
_BEND_LOSS_DB = 0.05  # 单弯损耗（SiEPIC EBeam PDK 保守上界）
_CROSSING_LOSS_DB = 0.3  # 单次交叉损耗（SiEPIC crossing_te1550 上界）


def _loss_budget_one_circuit(circuit: CircuitSpec) -> dict:
    """对单个电路计算版图后损耗预算（真实布线几何 + 紧凑模型）。

    流程:
    1. place_circuit + route_circuit 获取真实布线几何（与阶段 6 相同
       的确定性算法，结果一致）
    2. 器件损耗：polaris_flow 紧凑模型查表（SiEPIC 实测典型值，
       与主流水线 stage3/stage7 同一损耗表，保证跨模块一致）
    3. 互连损耗：实际布线路径总长度 × 3.0 dB/cm
    4. 弯曲损耗：实际弯曲数 × 0.05 dB
    5. 交叉损耗：实际交叉数 × 0.3 dB

    Args:
        circuit: 电路规格（含端口）。

    Returns:
        损耗预算 dict，含 device/waveguide/bend/crossing 分项、
        postlayout_loss_db、schematic_loss_db、layout_penalty_db。

    Raises:
        RuntimeError: 布局或布线失败（R03 禁止 fall-back）。
    """
    from polaris_flow.default_simulator import (
        _DefaultSimulator,
        supplement_waveguide_lengths,
    )

    circuit_dict = circuit_to_dict(circuit)
    placement_result = place_circuit(circuit_dict, mode="analytical")
    route_result = route_circuit(circuit_dict, placement_result["placements"], mode="curvy")
    paths = route_result["paths"]
    if not paths:
        raise RuntimeError(f"电路 {circuit.name} 布线失败：paths 为空（R03）")

    # 互连几何统计（真实布线路径）
    total_length_um = float(sum(path_length(p["points"]) for p in paths))
    n_bends = int(route_result["n_bends"])
    n_crossings = int(route_result["n_crossings"])

    # 器件损耗（紧凑模型查表，波导长度补充幂等）
    supplement_waveguide_lengths(circuit)
    simulator = _DefaultSimulator(mode="table")
    device_losses = simulator.device_loss_breakdown(circuit)
    device_loss_db = float(sum(item["loss_db"] for item in device_losses))

    # 版图后损耗预算（dB 域级联可加和，Pozar §4）
    waveguide_loss_db = total_length_um * _PROPAGATION_LOSS_DB_CM / 1e4
    bend_loss_db = n_bends * _BEND_LOSS_DB
    crossing_loss_db = n_crossings * _CROSSING_LOSS_DB
    postlayout_loss_db = (
        device_loss_db + waveguide_loss_db + bend_loss_db + crossing_loss_db
    )
    # 原理图级估算仅含器件损耗（无布线几何），版图附加 = 版图后 - 原理图
    schematic_loss_db = device_loss_db

    return {
        "name": circuit.name,
        "n_paths": len(paths),
        "total_length_um": round(total_length_um, 2),
        "n_bends": n_bends,
        "n_crossings": n_crossings,
        "device_loss_db": round(device_loss_db, 4),
        "waveguide_loss_db": round(waveguide_loss_db, 4),
        "bend_loss_db": round(bend_loss_db, 4),
        "crossing_loss_db": round(crossing_loss_db, 4),
        "schematic_loss_db": round(schematic_loss_db, 4),
        "postlayout_loss_db": round(postlayout_loss_db, 4),
        "layout_penalty_db": round(postlayout_loss_db - schematic_loss_db, 4),
    }


def run(output_dir: Path) -> dict:
    """执行阶段 7: 版图后仿真（含布线寄生）。

    对 3 个演示电路（MZI、Clements 4x4、量子占位）基于真实布线几何
    计算版图后损耗预算，报告写入 output_dir/reports/postlayout_loss_budget.json。

    Args:
        output_dir: 输出目录（含 reports/ 子目录）。

    Returns:
        阶段执行结果，含:
        - circuits: 3 电路损耗预算列表
        - max_layout_penalty_db: 最大版图附加损耗（dB）
        - report_path: 报告文件路径
    """
    _logger.info("阶段 7 开始: 版图后仿真（真实布线几何 + SiEPIC 紧凑模型）")
    reports_dir = Path(output_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    circuits = _build_circuits()
    results = [_loss_budget_one_circuit(circuit) for circuit in circuits]

    for r in results:
        _logger.info(
            "电路 %s: 版图后总损耗 %.4f dB（器件 %.4f + 波导 %.4f + 弯曲 %.4f "
            "+ 交叉 %.4f），版图附加 %.4f dB",
            r["name"], r["postlayout_loss_db"], r["device_loss_db"],
            r["waveguide_loss_db"], r["bend_loss_db"], r["crossing_loss_db"],
            r["layout_penalty_db"],
        )

    report_path = reports_dir / "postlayout_loss_budget.json"
    report = {
        "stage": 7,
        "stage_name": "版图后仿真",
        "loss_model": {
            "propagation_loss_db_cm": _PROPAGATION_LOSS_DB_CM,
            "bend_loss_db": _BEND_LOSS_DB,
            "crossing_loss_db": _CROSSING_LOSS_DB,
            "source": "SiEPIC EBeam PDK / Soref 1993（见模块 docstring）",
        },
        "circuits": results,
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    max_penalty = max(r["layout_penalty_db"] for r in results)
    _logger.info(
        "阶段 7 完成: %d 电路版图后仿真完成, 最大版图附加 %.4f dB",
        len(results), max_penalty,
    )

    return {
        "circuits": results,
        "max_layout_penalty_db": max_penalty,
        "report_path": str(report_path),
    }
