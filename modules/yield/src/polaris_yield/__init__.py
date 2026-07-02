"""PoLaRIS 统计与良率分析子模块（polaris-yield）。

单一职责: 光电子 EDA 流程中的统计抽样、方差减少与良率分析，从 v4 旧包
``polaris.sim.{monte_carlo, batch_simulation, importance_sampling*,
qmc_sampling, stratified_sampling, yield_optimization}`` 迁移整合而来。

v5.0 子模块化拆分（R13 不保留 v4 兼容路径；R04 纯 NumPy/SciPy，移除 JAX 依赖）。

稳定 API
--------
- ``monte_carlo_simulate(func, base_params, ...)``: 蒙特卡洛仿真
- ``sobol_sensitivity_analysis(func, param_distributions, ...)``: Sobol 全局灵敏度
- ``yield_analysis(func, base_params, spec_func, ...)``: 蒙特卡洛良率
- ``generate_qmc_samples / qmc_monte_carlo``: QMC 准随机采样与仿真
- ``importance_sampling_yield / rare_event_yield``: 稀有事件良率 IS 估计
- ``cross_entropy_importance_sampling``: CE 自适应 IS
- ``stratified_monte_carlo``: 分层采样方差减少
- ``compute_worst_case_distance``: WCD 工业良率指标
- ``allocate_tolerance_by_sensitivity``: Taguchi 容差分配
- ``optimize_yield_via_nominal_shift``: 标称值良率优化
- ``batch_simulate / batch_yield_analysis``: 多场景批量仿真

设计原则
--------
- R02 学术诚信: 所有公式/参数可溯源（见各模块 docstring ≥5 文献 URL）
- R03 禁止 fall-back: 失败即 raise，无静默兜底
- R04 不参与 GPU: 纯 NumPy/SciPy 实现（monte_carlo 移除 JAX，向量化并行）
- R05 无 TODO/FIXME 残留
- R13 不保留 v4 兼容路径，单一最新实现
- 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15

学术诚信（R02，≥5 文献 URL 溯源）
---------------------------------
- Metropolis & Ulam 1949, "The Monte Carlo Method",
  J. Am. Stat. Assoc. 44(247):335-341,
  https://doi.org/10.1080/01621459.1949.10483310
- Sobol 2001, "Global sensitivity indices for nonlinear mathematical
  models and Monte Carlo estimates",
  https://doi.org/10.1007/BF02304730
- Saltelli et al. 2010, "Variance based sensitivity analysis of model
  output. Design and estimator for the total sensitivity index",
  Comput. Phys. Commun. 181(2):259-270,
  https://doi.org/10.1016/j.cpc.2009.09.018
- McKay, Beckman & Conover 1979, Technometrics 21(2):239-245,
  https://doi.org/10.1080/00401706.1979.10489755
- Sobol 1967, USSR Comput. Math. Math. Phys. 7(4):86-112,
  https://doi.org/10.1016/0041-5553(67)90144-9
- Halton 1960, Numer. Math. 2:84-90,
  https://doi.org/10.1007/BF01386213
- Niederreiter 1992, "Random Number Generation and Quasi-Monte Carlo
  Methods", SIAM, https://doi.org/10.1137/1.9781611970081
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer, https://doi.org/10.1007/978-0-387-21617-1
- Glynn & Iglehart 1989, "Importance sampling for stochastic
  simulations", Management Science 35(11):1367-1392,
  https://doi.org/10.1287/mnsc.35.11.1367
- Heidelberger 1995, "Fast simulation of rare events in queueing and
  reliability models", ACM TOMACS 5(1):43-85,
  https://doi.org/10.1145/270261.270264
- Bucklew 2004, "Introduction to Rare Event Simulation", Springer,
  https://doi.org/10.1007/b97468
- Siegmund 1976, "Importance Sampling in the Monte Carlo Study of
  Sequential Tests", Annals of Statistics 4(4):673-684,
  https://doi.org/10.1214/aos/1176343542
- Rubinstein 1997, "Optimization of computer simulation models with
  rare events", European J. Oper. Res. 99:89-112,
  https://doi.org/10.1016/S0377-2217(96)00385-2
- Kroese, Taimre & Botev 2011, "Handbook of Monte Carlo Methods",
  Wiley, https://doi.org/10.1002/9781118014967
- Asmussen & Glynn 2007, "Stochastic Simulation: Algorithms and
  Analysis", Springer, https://doi.org/10.1007/978-0-387-69033-9
- Cochran 1977, "Sampling Techniques", Wiley, 3rd ed.,
  https://www.wiley.com/en-us/Sampling+Techniques%2C+3rd+Edition-p-9780471162407
- Neyman 1934, "On the two different aspects of the representative
  method", JRSS, https://doi.org/10.2307/2342192
- Singhal & Pinel 1981, IEEE TCS 28(7):692-701,
  https://doi.org/10.1109/TCS.1981.1085043
- Parkinson 1993, Eng. Optim. 21(4):259-278,
  https://doi.org/10.1080/03052159308940948
- Madkour et al. 2015, IEEE TCAS-I 62(12):2925-2933,
  https://doi.org/10.1109/TCSI.2015.2495251
- Bogaerts et al. 2018, "Layout-Aware Yield Prediction of Photonic
  Circuits", OFC,
  https://fib.intec.ugent.be/download/pub_4125.pdf
- NIST Engineering Statistics Handbook §5.5.6 Taguchi Designs
  https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm
- SciPy sobol_indices 文档:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html
- SciPy QMC: https://docs.scipy.org/doc/scipy/reference/stats.qmc.html
"""

from __future__ import annotations

from polaris_yield.batch_simulation import (
    BatchScenarioResult,
    BatchSimulationResult,
    BatchYieldResult,
    batch_simulate,
    batch_yield_analysis,
)
from polaris_yield.importance_sampling import (
    BiasingMethod,
    BiasingSpec,
    ImportanceSamplingResult,
    cross_entropy_importance_sampling,
    importance_sampling_mean,
    importance_sampling_yield,
    rare_event_yield,
)
from polaris_yield.monte_carlo import (
    MonteCarloResult,
    SobolSensitivityResult,
    monte_carlo_simulate,
    sensitivity_analysis,
    sobol_sensitivity_analysis,
    yield_analysis,
)
from polaris_yield.qmc_sampling import (
    QMCConvergenceComparison,
    QMCMonteCarloResult,
    QMCSampleResult,
    QMCSamplerType,
    compare_qmc_convergence,
    generate_qmc_samples,
    qmc_monte_carlo,
    transform_to_distribution,
)
from polaris_yield.stratified_sampling import (
    AllocationStrategy,
    StratifiedSamplingResult,
    compare_stratified_convergence,
    stratified_monte_carlo,
)
from polaris_yield.yield_optimization import (
    ToleranceAllocationResult,
    WorstCaseDistanceResult,
    YieldOptimizationResult,
    allocate_tolerance_by_sensitivity,
    compute_worst_case_distance,
    optimize_yield_via_nominal_shift,
)

__version__ = "5.0.0"

__all__ = [
    # monte_carlo
    "MonteCarloResult",
    "SobolSensitivityResult",
    "monte_carlo_simulate",
    "sensitivity_analysis",
    "sobol_sensitivity_analysis",
    "yield_analysis",
    # qmc_sampling
    "QMCSamplerType",
    "QMCSampleResult",
    "QMCMonteCarloResult",
    "QMCConvergenceComparison",
    "generate_qmc_samples",
    "transform_to_distribution",
    "qmc_monte_carlo",
    "compare_qmc_convergence",
    # importance_sampling
    "BiasingMethod",
    "BiasingSpec",
    "ImportanceSamplingResult",
    "importance_sampling_yield",
    "importance_sampling_mean",
    "rare_event_yield",
    "cross_entropy_importance_sampling",
    # stratified_sampling
    "AllocationStrategy",
    "StratifiedSamplingResult",
    "stratified_monte_carlo",
    "compare_stratified_convergence",
    # yield_optimization
    "WorstCaseDistanceResult",
    "ToleranceAllocationResult",
    "YieldOptimizationResult",
    "compute_worst_case_distance",
    "allocate_tolerance_by_sensitivity",
    "optimize_yield_via_nominal_shift",
    # batch_simulation
    "BatchScenarioResult",
    "BatchSimulationResult",
    "BatchYieldResult",
    "batch_simulate",
    "batch_yield_analysis",
    # 元数据
    "__version__",
]
