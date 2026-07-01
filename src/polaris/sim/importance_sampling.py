"""重要性采样 (Importance Sampling, IS) 用于稀有事件良率估计（R261-R280）。

本模块为 PoLaRIS 引入稀有事件仿真 (Rare-Event Simulation) 能力，补齐与商业
工具（Calibre YieldOptimizer / Mentor Pompeii / Synopsys CustomSim /
Lumerical INTERCONNECT / Luceda Circuit Analyzer）的核心差距：**真正的稀有
事件方差减少**。当良率接近 99.999% 时，朴素 MC 需 10⁹ 样本才能采到失效事件，
IS 通过偏置分布 (biasing distribution) 把采样质量压向失效区域，并用似然比
(likelihood ratio) 修正权重，实现 10²–10⁴ 倍方差缩减。

## 关键文献索引（URL）

- Glynn & Iglehart 1989 似然比估计器: https://doi.org/10.1287/mnsc.35.11.1367
- Glasserman 2003 Monte Carlo Methods in Financial Engineering: https://doi.org/10.1007/978-0-387-21617-1
- Heidelberger 1995 稀有事件仿真综述: https://doi.org/10.1145/270261.270264
- Bucklew 2004 Rare Event Simulation: https://doi.org/10.1007/b97468
- Siegmund 1976 指数扭转鞍点法: https://doi.org/10.1214/aos/1176343542
- Rubinstein 1997 交叉熵方法: https://doi.org/10.1016/S0377-2217(96)00385-2
- Kroese, Taimre & Botev 2011 Handbook of Monte Carlo Methods: https://doi.org/10.1002/9781118014967
- Asmussen & Glynn 2007 Stochastic Simulation: https://doi.org/10.1007/978-0-387-69033-9
- Bogaerts et al. 2018 光子学良率: https://fib.intec.ugent.be/download/pub_4125.pdf
- SciPy stats 文档: https://docs.scipy.org/doc/scipy/reference/stats.html
- 交叉熵方法综述(中文): https://journals.nwpu.edu.cn/xbgydxxb/FileUp/HTML/20170327.htm

## 核心理论

设标称（工艺）分布为 ``f(x)``，失效区域为 ``A``，目标良率 ``Y = P(X ∈ A)``。
引入偏置分布 ``q(x)``（要求 ``q(x)>0`` 当 ``f(x)>0`` 且 ``x∈A``），则：

    Y = E_f[𝟙_A(X)] = E_q[𝟙_A(X) · W(X)],   W(X) = f(X)/q(X)

其中 ``W(X)`` 为似然比。IS 估计器（无偏）：

    Ŷ_IS = (1/n) Σᵢ 𝟙_A(Xᵢ) · W(Xᵢ),   Xᵢ ~ q

## 偏置分布构造方法

1. **均值平移 (MEAN_SHIFT)**: ``q(x) = f(x - μ_shift)``，对高斯退化为
   ``N(μ+μ_shift, Σ)``。
2. **方差放大 (VARIANCE_SCALING)**: ``q(x) = f(x/σ_s)/σ_s``，加厚尾部。
3. **指数扭转 (EXPONENTIAL_TWIST)**: ``q_θ(x) ∝ exp(θᵀx)·f(x)``，
   Siegmund 1976 鞍点法，对和过程失效渐近最优。
4. **混合分布 (MIXTURE)**: ``q(x) = (1-α)f(x) + α·h(x)``，最稳健默认选择。
5. **交叉熵 (CROSS_ENTROPY)**: Rubinstein 1997 自适应迭代寻找最优 ``q``。

## 数值稳定性

- 全程 log 域计算似然比: ``log W = log f(x) - log q(x)``
- 用 ``scipy.special.logsumexp`` 做加权求和
- 强制 ESS 诊断: ``ESS = (ΣW)²/ΣW²``，退化即 raise（R03 禁止 fall-back）

## 学术依据

- 似然比估计器: Glynn & Iglehart 1989, "Importance sampling for stochastic
  simulations", Management Science 35(11):1367-1392,
  DOI: 10.1287/mnsc.35.11.1367
- 方差减少系统讲解: Glasserman 2003, "Monte Carlo Methods in Financial
  Engineering", Springer Ch.4, DOI: 10.1007/978-0-387-21617-1
- 稀有事件仿真综述: Heidelberger 1995, "Fast simulation of rare events in
  queueing and reliability models", ACM TOMACS 5(1):43-85,
  DOI: 10.1145/270261.270264
- 大偏差理论视角: Bucklew 2004, "Introduction to Rare Event Simulation",
  Springer, DOI: 10.1007/b97468
- 现代稀有事件综述: Juneja & Shahabuddin 2006, "Rare-Event Simulation
  Techniques: An Introduction and Recent Advances", Handbooks in OR&MS vol 13
- 指数扭转: Siegmund 1976, "Importance Sampling in the Monte Carlo Study of
  Sequential Tests", Annals of Statistics 4(4):673-684,
  DOI: 10.1214/aos/1176343542
- 交叉熵方法: Rubinstein 1997, "Optimization of computer simulation models
  with rare events", European J. Oper. Res. 99:89-112,
  DOI: 10.1016/S0377-2217(96)00385-2
- 自适应 IS / ESS 诊断: Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo
  Methods", Wiley, DOI: 10.1002/9781118014967
- 现代教科书: Asmussen & Glynn 2007, "Stochastic Simulation: Algorithms and
  Analysis", Springer, DOI: 10.1007/978-0-387-69033-9
- 光子学良率工业标准: Bogaerts et al. 2018, "Layout-Aware Yield Prediction of
  Photonic Circuits", OFC, https://fib.intec.ugent.be/download/pub_4125.pdf
- SciPy stats 文档: https://docs.scipy.org/doc/scipy/reference/stats.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。

批次 10-B 拆分说明（2026-07-01）:
    原文件 1270 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 4 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.sim.importance_sampling_types: BiasingMethod/BiasingSpec/
      ImportanceSamplingResult 数据类
    - polaris.sim.importance_sampling_distributions: 分布构造与采样辅助
      (_build_univariate_distributions / _construct_biasing_distribution /
       _sample_mixture / _logpdf_mixture / _compute_log_weights 等)
    - polaris.sim.importance_sampling_estimators: 核心估计器
      (importance_sampling_yield / importance_sampling_mean / rare_event_yield
       含 ESS Bug 修复 v5.0-P2-R114)
    - polaris.sim.importance_sampling_cross_entropy: 交叉熵自适应 IS
      (cross_entropy_importance_sampling + _validate_ce_params /
       _init_ce_distribution / _run_ce_iterations / _ce_final_is_estimate)

来源:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.sim.importance_sampling import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.sim.importance_sampling_types import (
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
)
from polaris.sim.importance_sampling_estimators import (
    importance_sampling_mean,
    importance_sampling_yield,
    rare_event_yield,
)
from polaris.sim.importance_sampling_cross_entropy import (
    cross_entropy_importance_sampling,
)

__all__ = [
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
    "cross_entropy_importance_sampling",
    "importance_sampling_mean",
    "importance_sampling_yield",
    "rare_event_yield",
]
