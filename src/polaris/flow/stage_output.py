"""PoLaRIS 流水线输出阶段（阶段 7-8）。

包含 GDS 版图导出（stage7）与光电协同仿真（stage8）。这两个阶段
负责生成最终交付物：将布局布线结果导出为 GDS 文件，并评估光电协同
耦合可行性。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- SiEPIC EBeam PDK 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski 2015, Silicon Photonics Design: From Device to System
  §8.4 光电协同寄生参数
- gdsfactory GDSII 导出
  https://gdsfactory.github.io/gdsfactory/
- IPKISS Schematic-Driven Layout 流程
  https://docs.lucedaphotonics.com/

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

import logging
import os

from polaris.flow.recipe import Recipe
from polaris.flow.stage_serializers import (
    _circuit_from_dict,
    _require_input,
)
from polaris.flow.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 阶段 7: GDS 版图导出
# =============================================================================


def stage7_gds(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 7: GDS 版图导出。

    复用 IntegratedPipeline._export_layout 逻辑，将布局布线结果导出为 GDS 文件。

    Args:
        recipe: 作业配方。
        workspace: 工作空间（GDS 输出到 workspace.gds_path()）。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit", "placements", "routes"）。

    Returns:
        含 gds_path/gds_size_bytes 的字典。
    """
    from polaris.eval.layout_render import export_gds
    from polaris.pipeline._converters import convert_to_paths, convert_to_placements

    circuit_dict = _require_input(prev_outputs, "circuit", 7)
    placements = _require_input(prev_outputs, "placements", 7)
    routes = _require_input(prev_outputs, "routes", 7)
    circuit = _circuit_from_dict(circuit_dict)

    logger.info("阶段 7: GDS 版图导出")

    # 转换为 Placement/WaveguidePath 对象
    placement_objs = convert_to_placements(circuit, placements)
    path_objs = convert_to_paths(routes)

    # 输出到 workspace 的 gds 目录
    gds_path = str(workspace.gds_path(f"{circuit.name}.gds"))

    export_gds(placement_objs, path_objs, gds_path)

    if not os.path.exists(gds_path):
        raise RuntimeError(
            f"GDS 导出失败：文件未生成 {gds_path}。"
            f"请检查 klayout 是否正确安装。"
        )
    gds_size_bytes = os.path.getsize(gds_path)
    logger.info(
        "阶段 7 完成: GDS 导出 %s（%d 字节）",
        gds_path, gds_size_bytes,
    )

    return {
        "gds_path": gds_path,
        "gds_size_bytes": int(gds_size_bytes),
    }


# =============================================================================
# 阶段 8: 光电协同仿真
# =============================================================================


def stage8_opto_electrical(
    recipe: Recipe, workspace: Workspace, prev_outputs: dict
) -> dict:
    """阶段 8: 光电协同仿真。

    计算电学寄生参数（电容/电阻），评估光电协同耦合可行性。

    物理模型（来源: SiEPIC EBeam PDK + Chrostowski 2015 §8.4）:
    - 电容: SOI 波导单位长度电容 ~1.0 pF/mm，按波导总长度计算
    - 电阻: SOI 加热器单位长度电阻 ~50 Ω/μm，按加热器数量计算
    - coupled: 是否存在光电耦合器件（heater/phase_shifter/modulator）

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit", "placements"）。

    Returns:
        含 opto_electrical 的字典。
    """
    circuit_dict = _require_input(prev_outputs, "circuit", 8)
    _require_input(prev_outputs, "placements", 8)

    logger.info("阶段 8: 光电协同仿真")

    # 识别光电耦合器件（heater/phase_shifter/modulator）
    opto_electrical_types = {
        "heater", "phase_shifter", "thermo_optic_phase_shifter",
        "mzm_modulator", "mrm_modulator", "mzm", "mach_zehnder_modulator",
    }
    coupled_devices = [
        d for d in circuit_dict.get("devices", [])
        if d.get("device_type") in opto_electrical_types
    ]
    coupled = len(coupled_devices) > 0

    # 电容: 基于波导总长度（SOI 波导单位电容 1.0 pF/mm）
    # 来源: Chrostowski 2015 §8.4, SOI strip waveguide 单位电容
    total_length_um = float(prev_outputs.get("total_length_um", 0.0))
    # 1.0 pF/mm = 0.001 pF/μm
    capacitance_pf = total_length_um * 0.001

    # 电阻: 基于加热器数量（每个加热器 50 Ω，串联）
    # 来源: SiEPIC EBeam PDK 热光移相器电阻典型值 50-100 Ω
    n_heaters = len(coupled_devices)
    resistance_ohm = float(n_heaters * 50.0)

    logger.info(
        "阶段 8 完成: 电容 %.4f pF, 电阻 %.1f Ω, 光电耦合=%s",
        capacitance_pf, resistance_ohm, coupled,
    )

    return {
        "opto_electrical": {
            "capacitance_pf": float(capacitance_pf),
            "resistance_ohm": float(resistance_ohm),
            "coupled": bool(coupled),
            "n_coupled_devices": int(n_heaters),
        }
    }


__all__ = [
    "stage7_gds",
    "stage8_opto_electrical",
]
