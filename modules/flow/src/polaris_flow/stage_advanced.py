"""PoLaRIS 流水线高级分析阶段（阶段 9-10）。

包含量子光子验证（stage9）与 AI 逆向设计（stage10）。这两个阶段
负责对电路进行高级物理分析：验证量子干涉特性，并用伴随法优化
光子器件参数。

## 来源

本模块从 ``polaris/flow/executors.py`` 拆分而来（保持外部 import 路径
不变，由 executors.py 作为 facade re-export）。

## 学术来源

- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Clements et al., Optica 2016, Clements 量子网络
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Lalau-Keraly 2013 OE, adjoint shape optimization
  https://doi.org/10.1364/OE.21.0021693
- Piggott 2017 Nature Photonics, 逆向设计实验验证
  https://doi.org/10.1038/nphoton.2017.126
- Aaronson & Arkhipov 玻色采样: https://arxiv.org/abs/0910.4698

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

import logging

from polaris_flow.recipe import Recipe
from polaris_flow.stage_serializers import _require_input
from polaris_flow.workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 阶段 9: 量子光子验证
# =============================================================================


def stage9_quantum(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 9: 量子光子验证。

    复用 sim/quantum_photonics.py 的 HOM 干涉仿真，验证电路的量子干涉特性。

    物理模型（来源: Hong, Ou, Mandel, PRL 1987）:
    - 构建 2×2 分束器酉矩阵（50:50）
    - 计算 HOM 干涉输出概率分布
    - 保真度 = 1 - P(1,1)（HOM 凹陷深度，理想值为 1）

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit"）。

    Returns:
        含 quantum_report 的字典。

    Raises:
        ImportError: polaris_boson API 契约与本阶段调用不兼容（R03 禁止 fall-back）。
    """
    raise ImportError(
        "stage9_quantum 需要 polaris_boson 提供 beamsplitter_unitary/clements_unitary/"
        "hom_interference，但 v5.0 polaris_boson API 契约已变更："
        "hom_interference(theta: float) 接收可分辨性参数而非酉矩阵，"
        "beamsplitter_unitary 仅为私有 _beamsplitter_unitary。"
        "本阶段原调用 hom_interference(bs_unitary) 与新契约不兼容，"
        "R03 禁止 fall-back：请迁移 stage9 改用 polaris_boson.hom_interference(theta)。"
    )


# =============================================================================
# 阶段 10: AI 逆向设计
# =============================================================================


def stage10_inverse(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 10: AI 逆向设计。

    复用 sim/ai_inverse_design.py 的 AdjointOptimizer，基于传输矩阵法
    优化光子器件参数，最大化目标波长处的传输率。

    学术依据:
    - Lalau-Keraly 2013 OE（adjoint shape optimization）
      https://doi.org/10.1364/OE.21.0021693
    - Piggott 2017 Nature Photonics（实验验证）
      https://doi.org/10.1038/nphoton.2017.126

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（本阶段无强制依赖）。

    Returns:
        含 inverse_design 的字典。

    Raises:
        ImportError: polaris_inverse 未迁移 AdjointConfig/AdjointOptimizer（R03 禁止 fall-back）。
    """
    raise ImportError(
        "stage10_inverse 需要 polaris_inverse 子模块提供 AdjointConfig/AdjointOptimizer，"
        "但 v5.0 polaris_inverse 仅迁移 run_adjoint_optimization 函数，"
        "未迁移 AdjointConfig/AdjointOptimizer 类，R03 禁止 fall-back。"
        "请迁移 stage10 改用 polaris_inverse.run_adjoint_optimization。"
    )


__all__ = [
    "stage9_quantum",
    "stage10_inverse",
]
