"""批量仿真接口（R296-R298）。

对多个标称点（场景）批量执行蒙特卡洛仿真，统计每个场景的输出分布。
应用场景:
- 工艺角 (process corners) 扫描
- 温度扫描
- 参数网格扫描
- 多芯片统计平均

## 核心功能

1. **batch_simulate**: 多标称点批量 MC 仿真
2. **batch_yield_analysis**: 多标称点批量良率分析

## 学术依据

- 蒙特卡洛方法: Metropolis & Ulam 1949, "The Monte Carlo Method",
  J. Am. Stat. Assoc. 44(247):335-341, DOI: 10.2307/2280232
- 批量仿真工业实践: Synopsys CustomSim / Cadence Spectre 平角仿真
- Bogaerts et al. 2018, OFC, layout-aware yield prediction
  https://fib.intec.ugent.be/download/pub_4125.pdf
- NIST Engineering Statistics Handbook §6, Process Control
  https://www.itl.nist.gov/div898/handbook/

补充文献（≥5，规则 R02 学术诚信）：
1. Metropolis N, Ulam S, "The Monte Carlo Method," J. Am. Stat.
   Assoc. 44(247):335-341 (1949) — https://doi.org/10.2307/2280232
2. Bogaerts W et al., "Layout-aware yield prediction of photonic
   circuits" (2018) — https://fib.intec.ugent.be/download/pub_4125.pdf
3. NIST/SEMATECH, "e-Handbook of Statistical Methods, §6 Process
   Control" — https://www.itl.nist.gov/div898/handbook/
4. NumPy, "Random sampling (numpy.random) — Generator & PCG64" —
   https://numpy.org/doc/stable/reference/random/index.html
5. SciPy, "Statistical functions (scipy.stats) — percentile &
   distribution" — https://docs.scipy.org/doc/scipy/reference/stats.html
6. Chrostowski L, Hochberg M, "Silicon Photonics Design: From Devices
   to Systems," Cambridge University Press (2015) —
   https://www.cambridge.org/9781107085459

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class BatchScenarioResult:
    """单个场景的批量仿真结果（R296）。

    Attributes:
        scenario_id: 场景索引。
        base_params: 该场景的标称参数。
        mean: 输出均值。
        std: 输出标准差（ddof=1）。
        min: 输出最小值。
        max: 输出最大值。
        percentile_95: 95 百分位。
        percentile_05: 5 百分位。
        n_samples: 样本数。
        n_evaluations: 总模型评估次数。
    """

    scenario_id: int = 0
    base_params: np.ndarray = field(default_factory=lambda: np.empty(0))
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    percentile_95: float = 0.0
    percentile_05: float = 0.0
    n_samples: int = 0
    n_evaluations: int = 0


@dataclass
class BatchSimulationResult:
    """批量仿真结果（R296-R297）。

    Attributes:
        scenarios: 每个场景的结果列表。
        n_scenarios: 场景数。
        n_samples_per_scenario: 每个场景的样本数。
        total_evaluations: 总模型评估次数（= n_scenarios × n_samples）。
        execution_time_s: 总执行时间（秒）。
        param_sigmas: 参数相对标准差。
        seed: 随机种子。
    """

    scenarios: list[BatchScenarioResult] = field(default_factory=list)
    n_scenarios: int = 0
    n_samples_per_scenario: int = 0
    total_evaluations: int = 0
    execution_time_s: float = 0.0
    param_sigmas: np.ndarray = field(default_factory=lambda: np.empty(0))
    seed: int | None = None


@dataclass
class BatchYieldResult:
    """批量良率分析结果（R298）。

    Attributes:
        yields: 每个场景的良率列表。
        n_pass_per_scenario: 每个场景的通过样本数列表。
        n_samples_per_scenario: 每个场景的样本数。
        n_scenarios: 场景数。
        total_evaluations: 总模型评估次数。
        execution_time_s: 总执行时间（秒）。
        scenario_ids: 场景 ID 列表。
    """

    yields: list[float] = field(default_factory=list)
    n_pass_per_scenario: list[int] = field(default_factory=list)
    n_samples_per_scenario: int = 0
    n_scenarios: int = 0
    total_evaluations: int = 0
    execution_time_s: float = 0.0
    scenario_ids: list[int] = field(default_factory=list)


# ============================================================================
# 公开 API
# ============================================================================


def batch_simulate(
    func: Callable[[np.ndarray], float],
    base_params_list: list[np.ndarray],
    param_sigmas: np.ndarray,
    n_samples: int = 1000,
    seed: int | None = None,
) -> BatchSimulationResult:
    """批量蒙特卡洛仿真（多标称点，R296-R297）。

    对每个标称点运行 ``n_samples`` 个参数扰动样本，计算输出统计量。
    参数扰动模型:

        params_i = base · (1 + σ · ε_i), ε_i ~ N(0, 1)

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        base_params_list: 多个标称点列表，每个 shape (d,)。
        param_sigmas: 每个参数的相对标准差 (d,)，如 0.01 = 1%。
        n_samples: 每个场景的样本数。
        seed: 随机种子（每个场景用不同子种子，保证可复现）。

    Returns:
        BatchSimulationResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败。

    学术依据:
    - Metropolis & Ulam 1949, DOI: 10.2307/2280232 (蒙特卡洛方法)
    - Bogaerts et al. 2018 (光子学良率批量分析)
    """
    if not base_params_list:
        raise ValueError("base_params_list 不能为空")
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if param_sigmas.ndim != 1:
        raise ValueError(
            f"param_sigmas 必须为 1D，得到 shape {param_sigmas.shape}"
        )
    if np.any(param_sigmas <= 0):
        raise ValueError(
            f"param_sigmas 必须 > 0，得到 {param_sigmas}"
        )
    if n_samples < 1:
        raise ValueError(f"n_samples 必须 >= 1，得到 {n_samples}")

    d = len(param_sigmas)
    n_scenarios = len(base_params_list)
    rng = np.random.default_rng(seed)
    start_time = time.perf_counter()

    scenarios: list[BatchScenarioResult] = []
    total_eval = 0

    for sid, base in enumerate(base_params_list):
        base = np.asarray(base, dtype=float)
        if base.shape != (d,):
            raise ValueError(
                f"base_params_list[{sid}] shape {base.shape} 与 param_sigmas ({d},) 不匹配"
            )

        # 生成参数扰动: base · (1 + σ · ε)
        noise = rng.normal(0.0, 1.0, size=(n_samples, d))
        samples = base * (1.0 + param_sigmas * noise)

        # 评估 func
        outputs = np.empty(n_samples, dtype=float)
        for i in range(n_samples):
            try:
                outputs[i] = float(func(samples[i]))
            except Exception as e:
                raise RuntimeError(
                    f"func 评估失败 (场景 {sid}, 样本 {i}): "
                    f"{type(e).__name__}: {e}。禁止 fall-back（规则 14.1）。"
                ) from e
        total_eval += n_samples

        scenarios.append(
            BatchScenarioResult(
                scenario_id=sid,
                base_params=base,
                mean=float(np.mean(outputs)),
                std=float(np.std(outputs, ddof=1)) if n_samples > 1 else 0.0,
                min=float(np.min(outputs)),
                max=float(np.max(outputs)),
                percentile_95=float(np.percentile(outputs, 95)),
                percentile_05=float(np.percentile(outputs, 5)),
                n_samples=n_samples,
                n_evaluations=n_samples,
            )
        )

    elapsed = time.perf_counter() - start_time
    return BatchSimulationResult(
        scenarios=scenarios,
        n_scenarios=n_scenarios,
        n_samples_per_scenario=n_samples,
        total_evaluations=total_eval,
        execution_time_s=elapsed,
        param_sigmas=param_sigmas,
        seed=seed,
    )


def batch_yield_analysis(
    func: Callable[[np.ndarray], float],
    base_params_list: list[np.ndarray],
    param_sigmas: np.ndarray,
    spec_func: Callable[[float], bool],
    n_samples: int = 1000,
    seed: int | None = None,
) -> BatchYieldResult:
    """批量良率分析（R298）。

    对每个标称点运行 ``n_samples`` 个参数扰动样本，用 ``spec_func`` 检查
    每个样本是否满足规格，计算每个场景的良率。

    Args:
        func: 仿真函数 f(params) -> scalar。
        base_params_list: 多个标称点列表。
        param_sigmas: 每个参数的相对标准差。
        spec_func: 规格函数 output -> bool（True = 满足规格）。
        n_samples: 每个场景的样本数。
        seed: 随机种子。

    Returns:
        BatchYieldResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败。

    学术依据:
    - Metropolis & Ulam 1949, DOI: 10.2307/2280232
    - Bogaerts et al. 2018 (光子学良率预测)
    """
    if not base_params_list:
        raise ValueError("base_params_list 不能为空")
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if param_sigmas.ndim != 1:
        raise ValueError(
            f"param_sigmas 必须为 1D，得到 shape {param_sigmas.shape}"
        )
    if np.any(param_sigmas <= 0):
        raise ValueError(
            f"param_sigmas 必须 > 0，得到 {param_sigmas}"
        )
    if n_samples < 1:
        raise ValueError(f"n_samples 必须 >= 1，得到 {n_samples}")

    d = len(param_sigmas)
    n_scenarios = len(base_params_list)
    rng = np.random.default_rng(seed)
    start_time = time.perf_counter()

    yields: list[float] = []
    n_pass_list: list[int] = []
    sid_list: list[int] = []
    total_eval = 0

    for sid, base in enumerate(base_params_list):
        base = np.asarray(base, dtype=float)
        if base.shape != (d,):
            raise ValueError(
                f"base_params_list[{sid}] shape {base.shape} 与 param_sigmas ({d},) 不匹配"
            )

        noise = rng.normal(0.0, 1.0, size=(n_samples, d))
        samples = base * (1.0 + param_sigmas * noise)

        n_pass = 0
        for i in range(n_samples):
            try:
                out = float(func(samples[i]))
            except Exception as e:
                raise RuntimeError(
                    f"func 评估失败 (场景 {sid}, 样本 {i}): "
                    f"{type(e).__name__}: {e}。禁止 fall-back（规则 14.1）。"
                ) from e
            if spec_func(out):
                n_pass += 1
        total_eval += n_samples

        yields.append(n_pass / n_samples)
        n_pass_list.append(n_pass)
        sid_list.append(sid)

    elapsed = time.perf_counter() - start_time
    return BatchYieldResult(
        yields=yields,
        n_pass_per_scenario=n_pass_list,
        n_samples_per_scenario=n_samples,
        n_scenarios=n_scenarios,
        total_evaluations=total_eval,
        execution_time_s=elapsed,
        scenario_ids=sid_list,
    )


__all__ = [
    "BatchScenarioResult",
    "BatchSimulationResult",
    "BatchYieldResult",
    "batch_simulate",
    "batch_yield_analysis",
]
