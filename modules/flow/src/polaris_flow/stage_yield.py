"""PoLaRIS 流水线良率分析阶段（阶段 9）。

包含蒙特卡洛良率分析（stage9）。在电路仿真（stage3）与物理验证
（stage7/8）之后、GDS 流片导出（stage12）之前，评估工艺偏差对
电路插损规格的影响，预测制造良率——这是工业光子流片前的标准
签核（sign-off）环节。

## 工业流程依据

- IMEC/Luceda 光子 PDK 流程：蒙特卡洛角分析在 tape-out 前签核
  https://docs.lucedaphotonics.com/
- Synopsys OptoCompiler: yield/corner analysis 为流片前必备验证
  https://www.synopsys.com/photonic-solutions.html

## 学术来源（R02 学术诚信，≥5 文献 URL）

- Metropolis & Ulam 1949, "The Monte Carlo Method",
  J. Am. Stat. Assoc. 44(247):335-341,
  https://doi.org/10.1080/01621459.1949.10483310
- Bogaerts et al. 2018, "Layout-Aware Yield Prediction of Photonic
  Circuits", OFC（光子电路版图感知良率预测方法）
  https://fib.intec.ugent.be/download/pub_4125.pdf
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015,
  §9 制造偏差与工艺角（photonic process corners）
  https://www.cambridge.org/9781107083456
- Singhal & Pinel 1981, "Statistical design centering and tolerancing
  using parametric sampling", IEEE TCAS 28(7):692-701（参数中心良率设计）
  https://doi.org/10.1109/TCS.1981.1085043
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer（蒙特卡洛估计统计性质）
  https://doi.org/10.1007/978-0-387-21617-1
- SiEPIC EBeam PDK 器件损耗典型值
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 工艺偏差模型（*创新* 工程估算，底层逻辑记录）

每器件插入损耗独立高斯涨落：loss_i' = loss_i × (1 + σ·ε_i)，
ε_i ~ N(0,1)，σ = recipe.sim_config.yield_sigma_rel（默认 0.05）。

*创新* 标注与依据：
- 底层逻辑：光子 foundry PDK corner 模型通常以 ±3σ 给出器件插损
  工艺角范围；SiEPIC/AMF 等 SOI 平台报道的无源器件插损工艺角
  spread 典型量级为 ±10-15%（3σ）。取 1σ = 5% 对应 3σ = 15%，
  与 foundry corner 报道量级一致（Chrostowski 2015 §9.4 讨论的
  制造偏差量级）。
- 独立性假设：芯片级随机偏差（线宽粗糙、侧壁散射）在空间上
  弱相关，器件间独立假设为良率文献常用一阶近似
  （Bogaerts 2018 的相关性建模为高阶修正）。
- 该模型为工程估算而非编造数据：σ 可通过 recipe.sim_config.
  yield_sigma_rel 由用户按实际 PDK corner 数据标定。

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
3. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

import logging

import numpy as np

from polaris_flow.recipe import Recipe
from polaris_flow.stage_serializers import _require_input
from polaris_flow.workspace import Workspace

logger = logging.getLogger(__name__)


def stage9_yield(recipe: Recipe, workspace: Workspace, prev_outputs: dict) -> dict:
    """阶段 9: 蒙特卡洛良率分析（流片前签核）。

    基于 stage3 原理图仿真的逐器件损耗分解，对每个器件损耗施加
    独立高斯工艺偏差涨落，蒙特卡洛采样估计总插损分布，按
    recipe.sim_config.loss_target_db 规格统计良率。

    统计方法来源:
    - Metropolis & Ulam 1949（蒙特卡洛方法）
      https://doi.org/10.1080/01621459.1949.10483310
    - Bogaerts et al. 2018 OFC（光子电路良率预测框架）
      https://fib.intec.ugent.be/download/pub_4125.pdf

    Args:
        recipe: 作业配方（使用 sim_config.loss_target_db /
            yield_n_samples / yield_sigma_rel）。
        workspace: 工作空间。
        prev_outputs: 之前所有阶段的输出字典（依赖 "device_losses",
            "total_loss_db"——由 stage3 原理图仿真产出）。

    Returns:
        含 yield_report 的字典。

    Raises:
        ValueError: 依赖输入缺失（R03 告警，不伪造损耗数据）。
    """
    from polaris_yield import monte_carlo_simulate

    device_losses = _require_input(prev_outputs, "device_losses", 9)
    schematic_loss_db = float(_require_input(prev_outputs, "total_loss_db", 9))

    n_samples = int(recipe.sim_config.yield_n_samples)
    sigma_rel = float(recipe.sim_config.yield_sigma_rel)
    loss_target_db = float(recipe.sim_config.loss_target_db)

    logger.info(
        "阶段 9: 蒙特卡洛良率分析（%d 采样，σ=%.1f%%，规格 %.2f dB）",
        n_samples, sigma_rel * 100, loss_target_db,
    )

    # 每器件标称损耗向量为基准参数；总损耗 = 各器件损耗之和（线性叠加，
    # dB 域级联损耗可加和，来源: Pozar Microwave Engineering §4 级联网络）
    base_losses = np.array(
        [float(item["loss_db"]) for item in device_losses], dtype=float
    )

    def _total_loss(params: np.ndarray) -> float:
        """总插损 = 各器件损耗之和（dB 域级联可加）。"""
        return float(np.sum(params))

    mc_result = monte_carlo_simulate(
        _total_loss, base_losses,
        n_samples=n_samples, sigma=sigma_rel, seed=42,
    )

    samples = np.asarray(mc_result.samples, dtype=float)
    n_pass = int(np.sum(samples <= loss_target_db))
    yield_estimate = n_pass / n_samples

    yield_report = {
        "yield_estimate": float(yield_estimate),
        "n_pass": int(n_pass),
        "n_samples": int(n_samples),
        "mean_loss_db": float(np.mean(samples)),
        "std_loss_db": float(np.std(samples)),
        "p05_loss_db": float(np.percentile(samples, 5)),
        "p95_loss_db": float(np.percentile(samples, 95)),
        "schematic_loss_db": float(schematic_loss_db),
        "loss_target_db": float(loss_target_db),
        "sigma_rel": float(sigma_rel),
        "n_devices": int(len(base_losses)),
        "method": "monte_carlo_per_device_loss",
        "variation_model": (
            "loss_i' = loss_i × (1 + σ·ε_i), ε_i ~ N(0,1) 独立高斯涨落；"
            "σ=5% (1σ) 对应 3σ=15% 与 SOI foundry corner 插损 spread 量级一致"
            "（*创新* 工程估算，可经 yield_sigma_rel 按 PDK 数据标定）"
        ),
    }

    logger.info(
        "阶段 9 完成: 良率 %.2f%%（%d/%d 通过），损耗均值 %.4f dB，"
        "95 分位 %.4f dB（规格 %.2f dB）",
        yield_estimate * 100, n_pass, n_samples,
        yield_report["mean_loss_db"], yield_report["p95_loss_db"], loss_target_db,
    )

    return {"yield_report": yield_report}


__all__ = [
    "stage9_yield",
]
