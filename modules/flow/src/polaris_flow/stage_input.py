"""PoLaRIS 流水线输入构建阶段（阶段 1-2）。

包含 PDK 器件目录加载（stage1）与电路规格构建（stage2）。这两个阶段
负责流水线的输入准备：从 PDK catalog 加载可用器件，再根据 recipe
构建待设计的电路规格。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- IPKISS Schematic-Driven Layout 流程
  https://docs.lucedaphotonics.com/
- gdsfactory 端到端流水线
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- Matres et al. 2024 GDSFactory paper: https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- gdsfactory PDK 文档: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
"""

from __future__ import annotations

import logging

from polaris_flow.recipe import Recipe
from polaris_flow.stage_serializers import _circuit_from_dict, _circuit_to_dict
from polaris_flow.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 阶段 1: PDK 器件目录加载
# =============================================================================


def stage1_pdk(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 1: PDK 器件目录加载。

    从 PoLaRIS PDK catalog 加载指定平台的器件目录，序列化为字典列表。

    Args:
        recipe: 作业配方（使用 recipe.platform）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（本阶段无依赖）。

    Returns:
        含 device_catalog/platform/n_devices 的字典。
    """
    raise ImportError(
        "stage_input 需要 polaris_pdk 子模块提供 DeviceCatalog/_device_to_dict"
        "（v5.0 polaris_pdk 仅提供 list/get 查询，未迁移 DeviceCatalog，R03）"
    )

    platform = recipe.platform
    logger.info("阶段 1: 加载 PDK 器件目录（平台=%s）", platform)

    # 注册四大平台全部器件，再按平台过滤
    catalog = DeviceCatalog().register_all_builtin()
    devices = catalog.list_by_platform(platform)
    if not devices:
        raise ValueError(
            f"平台 '{platform}' 无可用器件。"
            f"已注册平台: {catalog.platforms}。"
            f"请检查 recipe.platform 是否为 SOI/SiN/InP/LNOI 之一。"
        )

    device_catalog = [_device_to_dict(d) for d in devices]
    logger.info("阶段 1 完成: 平台 %s 共 %d 个器件", platform, len(device_catalog))

    return {
        "device_catalog": device_catalog,
        "platform": platform,
        "n_devices": len(device_catalog),
    }


# =============================================================================
# 阶段 2: 电路规格构建
# =============================================================================


def stage2_circuit(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 2: 电路规格构建。

    根据 recipe.preset_id 或 recipe.custom_circuit 构建电路规格，
    复用 web/server.py 的 _build_circuit 逻辑。

    Args:
        recipe: 作业配方（使用 recipe.preset_id 或 recipe.custom_circuit）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（本阶段无依赖）。

    Returns:
        含 circuit/n_devices/n_connections 的字典。
    """
    logger.info("阶段 2: 构建电路规格")

    if recipe.custom_circuit is not None:
        # 自定义电路：从字典重建 CircuitSpec
        circuit = _circuit_from_dict(recipe.custom_circuit)
    elif recipe.preset_id is not None:
        # 预设电路：复用 web/server.py 的 _build_circuit
        from polaris_gui.web_server import _build_circuit

        circuit = _build_circuit(recipe.preset_id)
    else:
        # Recipe.__post_init__ 已校验，此处不应到达
        raise ValueError(
            "Recipe 必须提供 preset_id 或 custom_circuit 之一。"
        )

    circuit_dict = _circuit_to_dict(circuit)
    n_devices = len(circuit_dict["devices"])
    n_connections = len(circuit_dict["connections"])
    logger.info(
        "阶段 2 完成: 电路 %s（%d 器件, %d 连接）",
        circuit_dict["name"], n_devices, n_connections,
    )

    return {
        "circuit": circuit_dict,
        "n_devices": n_devices,
        "n_connections": n_connections,
    }


__all__ = [
    "stage1_pdk",
    "stage2_circuit",
]
