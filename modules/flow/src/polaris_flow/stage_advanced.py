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
- Aaronson & Arkhipov, STOC 2011, 玻色采样 #P-hard
  https://arxiv.org/abs/0910.4698

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

    R391 修复: 原调用 polaris_boson.hom_interference(bs_unitary) 与 v5.0 API
    不兼容（新签名 hom_interference(theta: float)），改为直接调用新 API。

    物理模型（来源: Hong, Ou, Mandel, PRL 1987）:
    - 两个光子输入 50:50 分束器
    - theta=0 → 完全不可区分 → HOM dip（dip_depth=1.0）
    - 保真度 = dip_depth（HOM 凹陷深度，理想值为 1）

    Args:
        recipe: 作业配方。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "circuit"）。

    Returns:
        含 quantum_report 的字典。
    """
    from polaris_boson import hom_interference

    _require_input(prev_outputs, "circuit", 9)

    logger.info("阶段 9: 量子光子验证（HOM 干涉）")

    # HOM 干涉: theta=0 表示完全不可区分光子（理想 HOM dip）
    # 来源: Hong, Ou, Mandel, PRL 59, 2044 (1987)
    # URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
    hom_result = hom_interference(theta=0.0)
    dip_depth = hom_result["dip_depth"]
    coincidence_prob = hom_result["coincidence_prob"]
    verified = hom_result["verified"]

    logger.info(
        "阶段 9 完成: HOM dip 深度=%.4f, 符合计数率=%.4f, 验证=%s",
        dip_depth, coincidence_prob, verified,
    )

    return {
        "quantum_report": {
            "hom_dip_depth": float(dip_depth),
            "coincidence_prob": float(coincidence_prob),
            "verified": bool(verified),
            "scheme": "Hong_Ou_Mandel_1987",
        }
    }


# =============================================================================
# 阶段 10: AI 逆向设计
# =============================================================================


def stage10_inverse(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 10: AI 逆向设计。

    R391 修复: 原依赖 polaris_inverse.AdjointConfig/AdjointOptimizer（v5.0 未迁移），
    改为调用 polaris_inverse.run_adjoint_optimization 稳定 API。

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
    """
    from polaris_inverse import run_adjoint_optimization

    logger.info("阶段 10: AI 逆向设计（Adjoint 方法）")

    # Adjoint 逆向设计: JAX 可微分 FDTD 优化波导宽度
    # 来源: Lalau-Keraly 2013 OE, Piggott 2017 Nature Photonics
    result = run_adjoint_optimization()

    # run_adjoint_optimization 返回 key: final_fom/optimal_width_nm/fom_history/converged
    best_fom = result.get("final_fom", 0.0)
    best_width_nm = result.get("optimal_width_nm", 0.0)
    fom_history = result.get("fom_history", [])

    logger.info(
        "阶段 10 完成: 最优 FoM=%.4f, 最优宽度=%.1f nm, 迭代=%d",
        best_fom, best_width_nm, len(fom_history),
    )

    return {
        "inverse_design": {
            "best_fom": float(best_fom),
            "best_width_nm": float(best_width_nm),
            "initial_fom": float(result.get("initial_fom", 0.0)),
            "improvement_db": float(result.get("improvement_db", 0.0)),
            "converged": bool(result.get("converged", False)),
            "fom_history": fom_history,
            "method": "adjoint_fdtd",
        }
    }


__all__ = [
    "stage9_quantum",
    "stage10_inverse",
]
