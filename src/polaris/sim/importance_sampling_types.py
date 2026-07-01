"""重要性采样 (IS) 数据类型定义（R261-R270，批次 10-B 拆分子模块）。

本子模块定义重要性采样所需的枚举与数据类：
- :class:`BiasingMethod`: 偏置分布构造方法枚举
- :class:`BiasingSpec`: 偏置分布构造规格
- :class:`ImportanceSamplingResult`: IS 估计结果

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

来源（拆分依据）:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html


## 补充文献（R02 学术诚信补齐）
- Ansys Lumerical 文档: https://optics.ansys.com/hc/en-us
- Lumerical CML Compiler: https://optics.ansys.com/hc/en-us/articles/360057929454-S-parameter-passive-workflow
- Nocedal & Wright 2006 Numerical Optimization Springer: https://doi.org/10.1007/978-0-387-40065-5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class BiasingMethod(Enum):
    """偏置分布构造方法（R261-R270）。

    对标商业工具的稀有事件能力（多数商业工具无 IS，PoLaRIS 为差异化能力）：
    - Calibre YieldOptimizer: LHS + 失效边界搜索，无似然比修正
    - Lumerical INTERCONNECT: layout-aware MC，无稀有事件 IS
    - Luceda Circuit Analyzer: MC + Corner + QMC，无 IS

    来源: Glynn & Iglehart 1989, DOI: 10.1287/mnsc.35.11.1367
    """

    MEAN_SHIFT = "mean_shift"  # 均值平移 f(x-μ_shift)
    VARIANCE_SCALING = "variance_scaling"  # 方差放大 f(x/σ_s)/σ_s
    EXPONENTIAL_TWIST = "exponential_twist"  # 指数扭转 q_θ(x) ∝ exp(θᵀx)f(x)
    MIXTURE = "mixture"  # 混合分布 (1-α)f + α·h
    CROSS_ENTROPY = "cross_entropy"  # 交叉熵自适应 (Rubinstein 1997)


@dataclass
class BiasingSpec:
    """偏置分布构造规格（R261-R270）。

    根据 ``method`` 选择对应的偏置参数。未使用的字段保持 None。

    Attributes:
        method: 偏置方法（见 :class:`BiasingMethod`）。
        mean_shift: MEAN_SHIFT / MIXTURE 用，每维偏移量 list[float]（长度 = d）。
            正值朝正方向偏置，负值朝负方向。
        variance_scale: VARIANCE_SCALING 用，每维缩放因子 list[float]（>1 放大）。
        twist_theta: EXPONENTIAL_TWIST 用，每维扭转参数 θ list[float]。
            对正态分布退化为均值平移 μ_shift = σ²·θ。
        mixture_alpha: MIXTURE 用，混合权重 α ∈ (0, 1)（典型 0.1-0.5）。
            ``q = (1-α)·f + α·h``，h 由 ``mean_shift`` 构造均值平移高斯。
        elite_ratio: CROSS_ENTROPY 用，elite 比例 ρ ∈ (0.01, 0.2)。
        n_iterations: CROSS_ENTROPY 用，自适应迭代次数（典型 5-10）。
        smoothing_alpha: CROSS_ENTROPY 用，参数平滑系数 ∈ [0.5, 0.9]。

    学术依据:
    - 均值平移/方差放大: Glasserman 2003, Ch.4.2-4.3
    - 指数扭转: Siegmund 1976, DOI: 10.1214/aos/1176343542
    - 混合分布: Heidelberger 1995, DOI: 10.1145/270261.270264
    - 交叉熵: Rubinstein 1997, DOI: 10.1016/S0377-2217(96)00385-2
    """

    method: BiasingMethod = BiasingMethod.MEAN_SHIFT
    mean_shift: list[float] | None = None
    variance_scale: list[float] | None = None
    twist_theta: list[float] | None = None
    mixture_alpha: float = 0.3
    elite_ratio: float = 0.1
    n_iterations: int = 5
    smoothing_alpha: float = 0.7


@dataclass
class ImportanceSamplingResult:
    """重要性采样估计结果（R261-R280）。

    Attributes:
        yield_estimate: 良率估计 Ŷ_IS = mean(𝟙_A · W)。
        std_error: 标准误差 SE = σ̂_IS / √n。
        relative_error: 相对误差 RE = SE / |Ŷ|。BRE (Bounded Relative Error)
            是稀有事件 IS 算法优劣的理论判据。
        ci_lower: 95% 置信区间下界（正态近似 Ŷ ± 1.96·SE）。
        ci_upper: 95% 置信区间上界。
        effective_sample_size: 有效样本大小 ESS = (ΣW)²/ΣW²。
            ESS/n > 0.5 良好；< 0.1 退化（应告警）。
        speedup_vs_mc: 与朴素 MC 方差缩减比 = Var_MC / Var_IS。
            > 1 表示 IS 有效；典型值 10²-10⁴。
        n_samples: 实际样本数。
        n_failures: 失效样本数（诊断用）。
        n_evaluations: 总模型评估次数（= n_samples × n_iterations for CE）。
        biasing_method: 偏置方法名字符串。
        log_weights: log 似然比数组 log W_i（诊断/重用）。
        samples: 采样数组 (n_samples, d)（诊断/可视化用）。
        converged: CROSS_ENTROPY 自适应收敛标志；其他方法为 None。

    学术依据:
    - RE / BRE: Juneja & Shahabuddin 2006 (Handbooks in OR&MS vol 13)
    - ESS: Kroese, Taimre & Botev 2011, DOI: 10.1002/9781118014967
    - 加速比: Glasserman 2003, Ch.4.1
    """

    yield_estimate: float = 0.0
    std_error: float = 0.0
    relative_error: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    effective_sample_size: float = 0.0
    speedup_vs_mc: float = 0.0
    n_samples: int = 0
    n_failures: int = 0
    n_evaluations: int = 0
    biasing_method: str = ""
    log_weights: np.ndarray = field(default_factory=lambda: np.empty(0))
    samples: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    converged: bool | None = None


__all__ = [
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
]
