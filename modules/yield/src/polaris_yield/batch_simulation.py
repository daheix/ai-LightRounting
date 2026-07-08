"""批量仿真接口（polaris-yield 子模块）。

从 v4 ``polaris.sim.batch_simulation`` 迁移；R13 不保留 v4 兼容路径。

## 核心功能

1. ``batch_simulate``: 多标称点批量 MC 仿真
2. ``batch_yield_analysis``: 多标称点批量良率分析

应用场景: 工艺角扫描 / 温度扫描 / 参数网格扫描 / 多芯片统计平均。

## 学术依据（R02 学术诚信，≥5 文献 URL）

- Metropolis & Ulam 1949, "The Monte Carlo Method",
  J. Am. Stat. Assoc. 44(247):335-341,
  https://doi.org/10.2307/2280232
- Bogaerts et al. 2018, "Layout-aware yield prediction of photonic
  circuits" (2018),
  https://fib.intec.ugent.be/download/pub_4125.pdf
- NIST/SEMATECH, "e-Handbook of Statistical Methods, §6 Process
  Control", https://www.itl.nist.gov/div898/handbook/
- NumPy, "Random sampling (numpy.random) — Generator & PCG64",
  https://numpy.org/doc/stable/reference/random/index.html
- SciPy, "Statistical functions (scipy.stats)",
  https://docs.scipy.org/doc/scipy/reference/stats.html
- Chrostowski & Hochberg, "Silicon Photonics Design: From Devices to
  Systems", Cambridge University Press (2015),
  https://www.cambridge.org/9781107085459

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BatchScenarioResult:
    """单个场景的批量仿真结果。

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
    base_params: np.ndarray = field(
        default_factory=lambda: np.empty(0)
    )
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
    """批量仿真结果。

    Attributes:
        scenarios: 每个场景的结果列表。
        n_scenarios: 场景数。
        n_samples_per_scenario: 每个场景的样本数。
        total_evaluations: 总模型评估次数。
        execution_time_s: 总执行时间（秒）。
        param_sigmas: 参数相对标准差。
        seed: 随机种子。
    """

    scenarios: list[BatchScenarioResult] = field(default_factory=list)
    n_scenarios: int = 0
    n_samples_per_scenario: int = 0
    total_evaluations: int = 0
    execution_time_s: float = 0.0
    param_sigmas: np.ndarray = field(
        default_factory=lambda: np.empty(0)
    )
    seed: int | None = None


@dataclass
class BatchYieldResult:
    """批量良率分析结果。

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


def _validate_batch_params(
    base_params_list: list[np.ndarray],
    param_sigmas: np.ndarray,
    n_samples: int,
) -> int:
    """校验批量仿真入参，返回维度 d。"""
    if not base_params_list:
        raise ValueError("base_params_list 不能为空")
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if param_sigmas.ndim != 1:
        raise ValueError(
            f"param_sigmas 必须为 1D，得到 shape {param_sigmas.shape}"
        )
    if np.any(param_sigmas <= 0):
        raise ValueError(f"param_sigmas 必须 > 0，得到 {param_sigmas}")
    if n_samples < 1:
        raise ValueError(f"n_samples 必须 >= 1，得到 {n_samples}")
    return len(param_sigmas)


def _simulate_one_scenario(
    sid: int, base: np.ndarray, param_sigmas: np.ndarray, n_samples: int,
    d: int, rng: np.random.Generator, func: Callable[[np.ndarray], float],
) -> BatchScenarioResult:
    """对单个标称点执行 MC 仿真并返回统计结果（R03: 失败即 raise）。"""
    base = np.asarray(base, dtype=float)
    if base.shape != (d,):
        raise ValueError(
            f"base_params_list[{sid}] shape {base.shape} 与 "
            f"param_sigmas ({d},) 不匹配"
        )
    noise = rng.normal(0.0, 1.0, size=(n_samples, d))
    samples = base * (1.0 + param_sigmas * noise)
    outputs = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        try:
            outputs[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (场景 {sid}, 样本 {i}): "
                f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
            ) from e
    return BatchScenarioResult(
        scenario_id=sid, base_params=base,
        mean=float(np.mean(outputs)),
        std=(
            float(np.std(outputs, ddof=1)) if n_samples > 1 else 0.0
        ),
        min=float(np.min(outputs)),
        max=float(np.max(outputs)),
        percentile_95=float(np.percentile(outputs, 95)),
        percentile_05=float(np.percentile(outputs, 5)),
        n_samples=n_samples, n_evaluations=n_samples,
    )


def batch_simulate(
    func: Callable[[np.ndarray], float],
    base_params_list: list[np.ndarray],
    param_sigmas: np.ndarray,
    n_samples: int = 1000,
    seed: int | None = None,
) -> BatchSimulationResult:
    """批量蒙特卡洛仿真（多标称点）。

    对每个标称点运行 n_samples 个参数扰动样本，计算输出统计量。
    参数扰动模型::

        params_i = base · (1 + σ · ε_i), ε_i ~ N(0, 1)

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar。
        base_params_list: 多个标称点列表，每个 shape (d,)。
        param_sigmas: 每个参数的相对标准差 (d,)。
        n_samples: 每个场景的样本数。
        seed: 随机种子。

    Returns:
        BatchSimulationResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败。

    学术依据:
    - Metropolis & Ulam 1949, DOI: 10.2307/2280232
    - Bogaerts et al. 2018
    """
    d = _validate_batch_params(base_params_list, param_sigmas, n_samples)
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    n_scenarios = len(base_params_list)
    rng = np.random.default_rng(seed)
    start_time = time.perf_counter()
    scenarios: list[BatchScenarioResult] = []
    total_eval = 0
    for sid, base in enumerate(base_params_list):
        scenario, n_eval = _run_batch_one_scenario(
            sid, base, param_sigmas, n_samples, d, func, rng,
        )
        scenarios.append(scenario)
        total_eval += n_eval

    elapsed = time.perf_counter() - start_time
    return BatchSimulationResult(
        scenarios=scenarios, n_scenarios=n_scenarios,
        n_samples_per_scenario=n_samples, total_evaluations=total_eval,
        execution_time_s=elapsed, param_sigmas=param_sigmas, seed=seed,
    )


def _run_batch_one_scenario(
    sid: int,
    base: np.ndarray,
    param_sigmas: np.ndarray,
    n_samples: int,
    d: int,
    func: Callable[[np.ndarray], float],
    rng: np.random.Generator,
) -> tuple[BatchScenarioResult, int]:
    """单场景批量仿真（Extract Method，R11 质量门禁）。

    Returns:
        (scenario_result, n_evaluations)。
    """
    base = np.asarray(base, dtype=float)
    if base.shape != (d,):
        raise ValueError(
            f"base_params_list[{sid}] shape {base.shape} 与 "
            f"param_sigmas ({d},) 不匹配"
        )

    noise = rng.normal(0.0, 1.0, size=(n_samples, d))
    samples = base * (1.0 + param_sigmas * noise)

    outputs = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        try:
            outputs[i] = float(func(samples[i]))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (场景 {sid}, 样本 {i}): "
                f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
            ) from e

    scenario = BatchScenarioResult(
        scenario_id=sid, base_params=base,
        mean=float(np.mean(outputs)),
        std=(
            float(np.std(outputs, ddof=1))
            if n_samples > 1
            else 0.0
        ),
        min=float(np.min(outputs)),
        max=float(np.max(outputs)),
        percentile_95=float(np.percentile(outputs, 95)),
        percentile_05=float(np.percentile(outputs, 5)),
        n_samples=n_samples, n_evaluations=n_samples,
    )
    return scenario, n_samples


def batch_yield_analysis(
    func: Callable[[np.ndarray], float],
    base_params_list: list[np.ndarray],
    param_sigmas: np.ndarray,
    spec_func: Callable[[float], bool],
    n_samples: int = 1000,
    seed: int | None = None,
) -> BatchYieldResult:
    """批量良率分析。

    对每个标称点运行 n_samples 个参数扰动样本，用 spec_func 检查每个
    样本是否满足规格，计算每个场景的良率。

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
    - Bogaerts et al. 2018
    """
    d = _validate_batch_params(base_params_list, param_sigmas, n_samples)
    param_sigmas = np.asarray(param_sigmas, dtype=float)
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
                f"base_params_list[{sid}] shape {base.shape} 与 "
                f"param_sigmas ({d},) 不匹配"
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
                    f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
                ) from e
            if spec_func(out):
                n_pass += 1
        total_eval += n_samples

        yields.append(n_pass / n_samples)
        n_pass_list.append(n_pass)
        sid_list.append(sid)

    elapsed = time.perf_counter() - start_time
    return BatchYieldResult(
        yields=yields, n_pass_per_scenario=n_pass_list,
        n_samples_per_scenario=n_samples, n_scenarios=n_scenarios,
        total_evaluations=total_eval, execution_time_s=elapsed,
        scenario_ids=sid_list,
    )


__all__ = [
    "BatchScenarioResult",
    "BatchSimulationResult",
    "BatchYieldResult",
    "batch_simulate",
    "batch_yield_analysis",
]
