"""PoLaRIS 流水线验证阶段（阶段 5-6）。

包含 S 参数仿真（stage5）与 DRC/LVS 约束检查（stage6）。这两个阶段
负责对物理设计结果进行仿真验证与设计规则检查，确保版图满足光子学
设计约束。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- SiEPIC EBeam PDK strip waveguide 几何约定
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory 端到端流水线
  https://gdsfactory.github.io/gdsfactory/
- IPKISS Schematic-Driven Layout 流程
  https://docs.lucedaphotonics.com/

## 补充文献（R701-R750 学术诚信审核补齐，0 编造）

- KLayout DRC 引擎（开源光子/电子设计规则检查）
  https://www.klayout.de/manual/drc_engine.html
- Calibre Standard Verification Rule Format (SVRF)（Mentor/Siemens 商业 DRC 标准）
  https://docs.sw.siemens.com/en-US/doc/186265592
- OpenROAD KLayout integration（端到端验证流程参考）
  https://github.com/The-OpenROAD-Project/OpenROAD

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
# 阶段 5: S 参数仿真
# =============================================================================


def stage5_simulation(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 5: S 参数仿真。

    用 _DefaultSimulator 仿真（查表模式），返回总插入损耗与交叉数。

    波导长度推导：MZI/Ring 等预设电路的波导器件（strip_waveguide）在
    CircuitSpec 中未显式设置 ``length`` 参数。波导的物理长度由器件几何
    尺寸决定——光传播方向为器件较长维度（``max(width_um, height_um)``）。
    本阶段在调用仿真器前，为缺少 ``length`` 参数的波导器件补充该值，
    使仿真器能正确计算波导传输损耗（dB/cm × length_μm / 1e4）。

    来源: SiEPIC EBeam PDK strip waveguide 几何约定
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit", "placements", "routes"）。

    Returns:
        含 sparams/total_loss_db/n_crossings 的字典。
    """
    from polaris_flow.default_simulator import _DefaultSimulator

    circuit_dict = _require_input(prev_outputs, "circuit", 5)
    placements = _require_input(prev_outputs, "placements", 5)
    routes = _require_input(prev_outputs, "routes", 5)
    circuit = _circuit_from_dict(circuit_dict)

    logger.info("阶段 5: S 参数仿真（查表模式）")

    # 为缺少 length 参数的波导器件补充长度（基于器件物理尺寸）
    # 波导长度 = max(width_um, height_um)（光传播方向为较长维度）
    # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
    # https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    _WAVEGUIDE_TYPES = frozenset(
        {"waveguide", "straight", "strip_waveguide", "waveguide_bump$1"}
    )
    for dev in circuit.devices:
        if dev.device_type in _WAVEGUIDE_TYPES:
            has_length = any(
                k in dev.params for k in ("length", "wg_length", "length_um")
            )
            if not has_length:
                dev.params["length"] = float(max(dev.width_um, dev.height_um))

    simulator = _DefaultSimulator(mode="table")
    result = simulator.simulate(circuit, placements, routes)

    total_loss_db = float(result["total_loss_db"])
    n_crossings = int(result["n_crossings"])

    # sparams: 序列化仿真结果（含损耗分解）
    sparams = {
        "total_loss_db": total_loss_db,
        "n_crossings": n_crossings,
        "n_devices": len(circuit.devices),
        "n_connections": len(circuit.connections),
        "wavelength_nm": circuit.optical_wavelength_nm,
    }
    logger.info(
        "阶段 5 完成: 总损耗 %.4f dB, 交叉数 %d",
        total_loss_db, n_crossings,
    )

    return {
        "sparams": sparams,
        "total_loss_db": total_loss_db,
        "n_crossings": n_crossings,
    }


# =============================================================================
# 阶段 6: DRC/LVS 约束检查
# =============================================================================


def stage6_drc_lvs(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 6: DRC/LVS 约束检查。

    用 ConstraintChecker 检查布局布线结果是否满足光子学设计约束。

    Args:
        recipe: 作业配方（使用 recipe.sim_config.loss_target_db）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "placements", "routes",
            可选 "total_loss_db", "n_crossings"）。

    Returns:
        含 drc_report/lvs_passed 的字典。
    """
    raise ImportError(
        "stage_verification 需要 polaris_verify_advanced 子模块提供 "
        "ConstraintChecker/ConstraintConfig/CheckContext（v5.0 未迁移，R03 禁止 fall-back）"
    )

    placements = _require_input(prev_outputs, "placements", 6)
    routes = _require_input(prev_outputs, "routes", 6)

    logger.info("阶段 6: DRC/LVS 约束检查")

    # 从 recipe.sim_config 读取损耗目标
    loss_target_db = float(getattr(
        recipe.sim_config, "loss_target_db", 5.0
    ))
    config = ConstraintConfig(
        min_bend_radius_um=5.0,  # SOI 平台标准弯曲半径
        max_insertion_loss_db=loss_target_db,
    )
    checker = ConstraintChecker(config=config)

    # 构建检查上下文（含损耗与交叉数，来自阶段 5）
    total_loss_db = float(prev_outputs.get("total_loss_db", 0.0))
    n_crossings = int(prev_outputs.get("n_crossings", 0))
    circuit_dict = prev_outputs.get("circuit", {})
    canvas_w = float(circuit_dict.get("canvas_w", 0.0)) if circuit_dict else 0.0
    canvas_h = float(circuit_dict.get("canvas_h", 0.0)) if circuit_dict else 0.0
    ctx = CheckContext(
        total_loss_db=total_loss_db,
        n_crossings=n_crossings,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )

    violations = checker.check(placements=placements, paths=routes, context=ctx)
    # 序列化违规列表
    violation_list = [
        {
            "type": v.vtype.value,
            "severity": float(v.severity),
            "message": v.message,
            "device_name": v.device_name,
            "net_id": v.net_id,
            "location": list(v.location) if v.location else None,
        }
        for v in violations
    ]
    n_violations = len(violation_list)
    drc_passed = n_violations == 0

    # LVS: 简化为端口连接性检查（无器件网表不一致即视为通过）
    # 真实 LVS 需要版图提取网表与原理图网表对比，此处用 DRC 的端口连接性结果
    lvs_passed = drc_passed

    logger.info(
        "阶段 6 完成: DRC %s（%d 违规），LVS %s",
        "通过" if drc_passed else "失败", n_violations,
        "通过" if lvs_passed else "失败",
    )

    return {
        "drc_report": {
            "violations": violation_list,
            "n_violations": n_violations,
            "passed": drc_passed,
        },
        "lvs_passed": lvs_passed,
    }


__all__ = [
    "stage5_simulation",
    "stage6_drc_lvs",
]
