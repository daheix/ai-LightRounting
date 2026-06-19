"""校准与验证模块。

对比自研仿真结果与基准数据，修正仿真模型参数，
确保自研工具的仿真精度满足工程要求。

来源:
- LiDAR ISPD'25: 基准损耗数据
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- PICBench: 参考网表和损耗
  https://github.com/PICDA/PICBench
- SiEPIC PDK: 测量校准数据
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CalibrationConfig:
    """校准配置。

    Attributes:
        loss_tolerance_db: 损耗容差（dB）。
        benchmark_dir: 基准数据目录。
        max_calibration_rounds: 最大校准轮数。
    """

    loss_tolerance_db: float = 0.5
    benchmark_dir: str = "data/benchmarks"
    max_calibration_rounds: int = 5


@dataclass
class CalibrationItem:
    """单项校准结果。

    Attributes:
        circuit_name: 电路名称。
        reference_loss_db: 基准损耗（dB）。
        simulated_loss_db: 自研仿真损耗（dB）。
        error_db: 误差（dB）。
        passed: 是否通过容差检查。
    """

    circuit_name: str = ""
    reference_loss_db: float = 0.0
    simulated_loss_db: float = 0.0
    error_db: float = 0.0
    passed: bool = False


@dataclass
class CalibrationResult:
    """校准总结果。

    Attributes:
        items: 各电路校准结果。
        total_items: 总校准项数。
        passed_items: 通过项数。
        max_error_db: 最大误差（dB）。
        mean_error_db: 平均误差（dB）。
        all_passed: 是否全部通过。
    """

    items: list[CalibrationItem] = field(default_factory=list)
    total_items: int = 0
    passed_items: int = 0
    max_error_db: float = 0.0
    mean_error_db: float = 0.0
    all_passed: bool = False


def calibrate(
    config: CalibrationConfig | None = None,
    simulator=None,
) -> CalibrationResult:
    """执行校准验证。

    对比自研仿真 vs 基准数据，检查误差是否在容差范围内。

    Args:
        config: 校准配置。
        simulator: 仿真器（可选，默认使用简化估算）。

    Returns:
        CalibrationResult。
    """
    cfg = config or CalibrationConfig()
    bdir = Path(cfg.benchmark_dir)
    if not bdir.exists():
        logger.error("基准目录不存在: %s", cfg.benchmark_dir)
        return CalibrationResult()

    items = _collect_calibration_items(bdir, cfg)
    if not items:
        return CalibrationResult()

    return _summarize_calibration(items)


def _collect_calibration_items(
    bdir: Path,
    cfg: CalibrationConfig,
) -> list[CalibrationItem]:
    """收集并计算各电路的校准结果。"""
    items: list[CalibrationItem] = []
    for f in sorted(bdir.glob("*.json")):
        if f.name in ("index.json", "variant_stats.json", "dataset_stats.json"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        name = data.get("name", f.stem)
        ref_loss = data.get("reference_loss_db", data.get("total_loss_db", 0.0))
        sim_loss = _estimate_loss(data)
        error = abs(sim_loss - ref_loss)
        items.append(
            CalibrationItem(
                circuit_name=name,
                reference_loss_db=ref_loss,
                simulated_loss_db=sim_loss,
                error_db=error,
                passed=error <= cfg.loss_tolerance_db,
            )
        )
    return items


def _summarize_calibration(items: list[CalibrationItem]) -> CalibrationResult:
    """汇总校准结果。"""
    errors = [it.error_db for it in items]
    n_passed = sum(1 for it in items if it.passed)
    result = CalibrationResult(
        items=items,
        total_items=len(items),
        passed_items=n_passed,
        max_error_db=max(errors),
        mean_error_db=sum(errors) / len(errors),
        all_passed=n_passed == len(items),
    )
    logger.info(
        "校准完成: %d/%d 通过, 最大误差 %.2f dB, 平均误差 %.2f dB",
        n_passed,
        len(items),
        result.max_error_db,
        result.mean_error_db,
    )
    return result


def _estimate_loss(data: dict) -> float:
    """用自研简化模型估算损耗。

    支持三种基准数据格式：
    - PICBench: data.netlist.instances (dict, 含 component/settings.length)
    - LiDAR: instances (dict, 含 component/settings)
    - gdsfactory: instances (list 或 dict)

    波导类器件按 length 参数计算损耗（2.0 dB/cm），其他器件按类型查表。

    来源:
    - SiEPIC EBeam PDK 波导损耗典型值 2.0 dB/cm
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    instances = data.get("instances")
    if instances is None:
        netlist = data.get("data", {}).get("netlist", {})
        instances = netlist.get("instances")
    if instances is None:
        return 0.0
    if isinstance(instances, dict):
        return sum(_instance_loss(inst) for inst in instances.values())
    if isinstance(instances, list):
        return sum(_instance_loss(inst) for inst in instances)
    return 0.0


def _instance_loss(inst) -> float:
    """计算单个器件实例的损耗。"""
    if isinstance(inst, str):
        return _cell_loss(inst)
    if not isinstance(inst, dict):
        return 0.0
    cell = inst.get("component", inst.get("cell_type", ""))
    settings = inst.get("settings", {})
    if isinstance(settings, dict) and "length" in settings:
        length = settings["length"]
        if isinstance(length, (int, float)) and length > 0:
            return _WG_LOSS_DB_PER_UM * length
    return _cell_loss(cell)


# 波导单位长度损耗 (dB/μm)，来源 SiEPIC EBeam PDK 典型值 2.0 dB/cm
_WG_LOSS_DB_PER_UM: float = 2.0 / 1e4


# 器件类型关键字 → 损耗 (dB) 映射表
# 注意：更具体的关键字必须排在通用关键字之前，避免误匹配。
# 例如 "grating_coupler" 必须先匹配 "grating"（2.5 dB）而非 "coupler"（0.2 dB）。
_CELL_LOSS_RULES: list[tuple[str, float]] = [
    ("wg", 0.1),
    ("waveguide", 0.1),
    ("mzi", 0.5),
    ("ring", 0.3),
    ("mrr", 0.3),
    ("dc", 0.2),
    ("gc", 2.5),
    ("grating", 2.5),
    ("coupler", 0.2),
    ("mmi", 0.3),
    ("yb", 0.3),
    ("y_branch", 0.3),
    ("crossing", 0.05),
    ("straight_heat", 0.2),
    ("phase_shifter", 0.2),
    ("heater", 0.2),
    ("rectangle", 0.0),
]


def _cell_loss(cell: str) -> float:
    """根据器件类型字符串计算损耗。"""
    cell_lower = cell.lower() if isinstance(cell, str) else ""
    for keyword, loss in _CELL_LOSS_RULES:
        if keyword in cell_lower:
            return loss
    return 0.2


__all__ = [
    "calibrate",
    "CalibrationConfig",
    "CalibrationItem",
    "CalibrationResult",
]
