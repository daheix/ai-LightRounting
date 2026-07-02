"""蒙特卡洛仿真与灵敏度分析（polaris-yield 子模块）。

从 v4 ``polaris.sim.monte_carlo`` 迁移；按 R04 移除 JAX 依赖，改用 NumPy
向量化实现等价并行；R13 不保留 v4 兼容路径。

## 核心功能

1. ``monte_carlo_simulate``: 参数扰动并行蒙特卡洛仿真
2. ``sensitivity_analysis``: 一阶摄动局部灵敏度（中心差分）
3. ``sobol_sensitivity_analysis``: Sobol 全局灵敏度（Saltelli 2010 采样）
4. ``yield_analysis``: 蒙特卡洛良率估计

## 学术依据（R02 学术诚信，≥5 文献 URL）

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
- Glasserman 2003, "Monte Carlo Methods in Financial Engineering",
  Springer, https://doi.org/10.1007/978-0-387-21617-1
- Fishman 1996, "Monte Carlo: Concepts, Algorithms, and Applications",
  Springer, https://doi.org/10.1007/978-1-4757-2553-7
- Robert & Casella 2004, "Monte Carlo Statistical Methods",
  Springer, https://doi.org/10.1007/978-1-4757-4145-2
- SciPy sobol_indices 文档:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯 NumPy/SciPy）/
R09 优先用三方库。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm, sobol_indices, uniform

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """蒙特卡洛仿真结果。

    Attributes:
        samples: 采样输出数组 (n_samples, ...)。
        mean: 输出均值。
        std: 输出标准差。
        min: 输出最小值。
        max: 输出最大值。
        percentile_95: 95 百分位。
        percentile_05: 5 百分位。
    """

    samples: np.ndarray
    mean: np.ndarray
    std: np.ndarray
    min: np.ndarray
    max: np.ndarray
    percentile_95: np.ndarray
    percentile_05: np.ndarray


def _evaluate_batch(
    func: Callable[[np.ndarray], np.ndarray | float],
    samples: np.ndarray,
) -> np.ndarray:
    """逐样本评估 func 并堆叠输出（R03 禁止 fall-back）。

    Args:
        func: 仿真函数 f(params: (d,)) -> scalar 或 array。
        samples: 参数样本 (n_samples, d)。

    Returns:
        输出数组 (n_samples, ...)。

    Raises:
        RuntimeError: func 评估异常。
    """
    n = samples.shape[0]
    outputs_list: list[np.ndarray] = []
    for i in range(n):
        try:
            out = func(samples[i])
            outputs_list.append(np.asarray(out, dtype=float))
        except Exception as e:
            raise RuntimeError(
                f"func 评估失败 (样本 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（R03）。"
            ) from e
    return np.stack(outputs_list, axis=0)


def monte_carlo_simulate(
    func: Callable[[np.ndarray], np.ndarray | float],
    base_params: np.ndarray,
    n_samples: int = 1000,
    sigma: float = 0.01,
    seed: int = 42,
) -> MonteCarloResult:
    """参数扰动蒙特卡洛仿真（NumPy 向量化并行）。

    参数扰动模型::

        params_i = base_params · (1 + σ · ε_i), ε_i ~ N(0, 1)

    Args:
        func: 仿真函数 f(params) -> output。
        base_params: 基准参数数组。
        n_samples: 采样数。
        sigma: 参数相对标准差（如 0.01 = 1%）。
        seed: 随机种子。

    Returns:
        MonteCarloResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败。

    学术依据: Metropolis & Ulam 1949, DOI: 10.1080/01621459.1949.10483310
    """
    base_params = np.asarray(base_params, dtype=float)
    if n_samples <= 0:
        raise ValueError(f"n_samples 必须 > 0，得到 {n_samples}")
    if sigma < 0:
        raise ValueError(f"sigma 必须 >= 0，得到 {sigma}")

    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 1.0, size=(n_samples, base_params.shape[0]))
    samples = base_params * (1.0 + sigma * noise)

    outputs = _evaluate_batch(func, samples)

    return MonteCarloResult(
        samples=outputs,
        mean=np.mean(outputs, axis=0),
        std=np.std(outputs, axis=0),
        min=np.min(outputs, axis=0),
        max=np.max(outputs, axis=0),
        percentile_95=np.percentile(outputs, 95, axis=0),
        percentile_05=np.percentile(outputs, 5, axis=0),
    )


def sensitivity_analysis(
    func: Callable[[np.ndarray], float],
    base_params: np.ndarray,
    param_names: list[str] | None = None,
    delta: float = 0.01,
) -> dict[str, float]:
    """参数敏感度分析（一阶摄动中心差分）。

    归一化敏感度::

        S_i = (f(p + Δp_i) - f(p - Δp_i)) / (2·Δp_i) · (p_i / f(p))

    Args:
        func: 仿真函数 f(params) -> scalar。
        base_params: 基准参数数组。
        param_names: 参数名列表。
        delta: 相对扰动量。

    Returns:
        {参数名: 敏感度} 字典。
    """
    base_params = np.asarray(base_params, dtype=float)
    n = len(base_params)
    if param_names is None:
        param_names = [f"param_{i}" for i in range(n)]
    if len(param_names) != n:
        raise ValueError(
            f"param_names 长度 {len(param_names)} 与参数数 {n} 不匹配"
        )

    sensitivities: dict[str, float] = {}
    base_output = float(func(base_params))

    for i in range(n):
        eps = delta * max(abs(base_params[i]), 1e-12)
        params_plus = base_params.copy()
        params_minus = base_params.copy()
        params_plus[i] += eps
        params_minus[i] -= eps
        out_plus = float(func(params_plus))
        out_minus = float(func(params_minus))
        if abs(base_params[i]) > 1e-15 and abs(base_output) > 1e-15:
            sens = (out_plus - out_minus) / (2 * eps) * (
                base_params[i] / base_output
            )
        else:
            sens = (out_plus - out_minus) / (2 * eps)
        sensitivities[param_names[i]] = float(sens)
    return sensitivities


def yield_analysis(
    func: Callable[[np.ndarray], float],
    base_params: np.ndarray,
    spec_func: Callable[[float], bool],
    n_samples: int = 1000,
    sigma: float = 0.01,
    seed: int = 42,
) -> dict[str, float]:
    """蒙特卡洛良率分析。

    Args:
        func: 仿真函数 f(params) -> output。
        base_params: 基准参数数组。
        spec_func: 规格函数 output -> bool（True = 满足规格）。
        n_samples: 采样数。
        sigma: 参数相对标准差。
        seed: 随机种子。

    Returns:
        {"yield": float, "n_pass": int, "n_total": int} 字典。
    """
    result = monte_carlo_simulate(func, base_params, n_samples, sigma, seed)
    pass_flags = np.array(
        [bool(spec_func(float(s))) for s in result.samples]
    )
    n_pass = int(np.sum(pass_flags))
    return {
        "yield": n_pass / n_samples,
        "n_pass": n_pass,
        "n_total": n_samples,
    }


# ============================================================================
# Sobol 全局灵敏度分析（Saltelli 2010 采样）
# ============================================================================


@dataclass
class SobolSensitivityResult:
    """Sobol 全局灵敏度分析结果。

    使用 Saltelli 2010 采样方案计算一阶和总效应 Sobol 指数。

    Attributes:
        first_order: 一阶 Sobol 指数 {参数名: S_i}。
        total_order: 总效应 Sobol 指数 {参数名: S_Ti}。
        first_order_values: 原始一阶指数数组 (k,)。
        total_order_values: 原始总效应指数数组 (k,)。
        n_evaluations: 总模型评估次数 N(k+2)。
        param_names: 参数名列表。
        n_samples: 基础样本数（必须为 2 的幂）。

    学术依据:
    - Sobol 2001, DOI: 10.1007/BF02304730
    - Saltelli et al. 2010, DOI: 10.1016/j.cpc.2009.09.018
    """

    first_order: dict[str, float] = field(default_factory=dict)
    total_order: dict[str, float] = field(default_factory=dict)
    first_order_values: np.ndarray = field(
        default_factory=lambda: np.array([])
    )
    total_order_values: np.ndarray = field(
        default_factory=lambda: np.array([])
    )
    n_evaluations: int = 0
    param_names: list[str] = field(default_factory=list)
    n_samples: int = 0

    @property
    def interaction_effects(self) -> dict[str, float]:
        """参数交互效应 S_Ti - S_i。"""
        return {
            name: float(self.total_order[name] - self.first_order[name])
            for name in self.param_names
        }

    def rank_by_first_order(self) -> list[tuple[str, float]]:
        """按一阶 Sobol 指数降序排序。"""
        return sorted(
            self.first_order.items(), key=lambda x: abs(x[1]), reverse=True
        )

    def rank_by_total_order(self) -> list[tuple[str, float]]:
        """按总效应 Sobol 指数降序排序。"""
        return sorted(
            self.total_order.items(), key=lambda x: abs(x[1]), reverse=True
        )


def _build_distribution(spec: dict):
    """从规格字典构建 SciPy 分布对象。

    Args:
        spec: 分布规格 {"type": "norm"|"uniform", "loc": ..., "scale": ...}。

    Returns:
        SciPy 冻结分布对象（带 ppf 方法）。

    Raises:
        ValueError: 不支持的分布类型。
    """
    dist_type = spec.get("type", "")
    if dist_type == "norm":
        return norm(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
    if dist_type == "uniform":
        return uniform(loc=spec.get("loc", 0.0), scale=spec.get("scale", 1.0))
    raise ValueError(
        f"不支持的分布类型: '{dist_type}'。支持: 'norm', 'uniform'。"
        f"规格: {spec}"
    )


def _adapt_func_for_sobol(
    func: Callable[[np.ndarray], float],
) -> Callable[[np.ndarray], np.ndarray]:
    """适配 PoLaRIS 标量函数为 SciPy sobol_indices 批量接口。

    SciPy sobol_indices 要求 func(x) 其中 x shape (d, n)，输出 shape (s, n)。

    Args:
        func: PoLaRIS 标量函数 f(params: (d,)) -> float。

    Returns:
        批量函数 f_batch(x: (d, n)) -> (n,)。
    """

    def _batch(x: np.ndarray) -> np.ndarray:
        n = x.shape[1]
        out = np.empty(n, dtype=float)
        for j in range(n):
            out[j] = float(func(x[:, j]))
        return out

    return _batch


def sobol_sensitivity_analysis(
    func: Callable[[np.ndarray], float],
    param_distributions: list[dict],
    n_samples: int = 1024,
    param_names: list[str] | None = None,
    random_state: int | None = None,
) -> SobolSensitivityResult:
    """Sobol 全局灵敏度分析（Saltelli 2010 采样）。

    Args:
        func: 仿真函数 f(params: (k,)) -> scalar。
        param_distributions: 参数分布规格列表。
        n_samples: 基础样本数 N，必须为 2 的幂（默认 1024）。
        param_names: 参数名列表，None 则用 ["param_0", ...]。
        random_state: 随机种子。

    Returns:
        SobolSensitivityResult。

    Raises:
        ValueError: n_samples 非 2 的幂，或参数分布规格无效。
        RuntimeError: SciPy sobol_indices 计算失败。

    学术依据:
    - Sobol 2001, DOI: 10.1007/BF02304730
    - Saltelli et al. 2010, DOI: 10.1016/j.cpc.2009.09.018
    - SciPy sobol_indices 文档:
      https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html
    """
    k = len(param_distributions)
    if k == 0:
        raise ValueError("param_distributions 不能为空")
    if n_samples <= 0 or (n_samples & (n_samples - 1)) != 0:
        raise ValueError(
            f"n_samples 必须为 2 的幂且 > 0，得到 {n_samples}。"
            f"建议: 512, 1024, 2048, 4096。"
        )
    if param_names is None:
        param_names = [f"param_{i}" for i in range(k)]
    if len(param_names) != k:
        raise ValueError(
            f"param_names 长度 {len(param_names)} 与参数数 {k} 不匹配"
        )

    dists = [_build_distribution(spec) for spec in param_distributions]
    batch_func = _adapt_func_for_sobol(func)

    try:
        result = sobol_indices(
            func=batch_func,
            n=n_samples,
            dists=dists,
            method="saltelli_2010",
            random_state=random_state,
        )
    except Exception as e:
        raise RuntimeError(
            f"SciPy sobol_indices 计算失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    first_order = np.asarray(result.first_order, dtype=float)
    total_order = np.asarray(result.total_order, dtype=float)
    if first_order.ndim == 2:
        first_order = first_order[0]
    if total_order.ndim == 2:
        total_order = total_order[0]

    n_eval = n_samples * (k + 2)
    return SobolSensitivityResult(
        first_order={param_names[i]: float(first_order[i]) for i in range(k)},
        total_order={param_names[i]: float(total_order[i]) for i in range(k)},
        first_order_values=first_order,
        total_order_values=total_order,
        n_evaluations=n_eval,
        param_names=list(param_names),
        n_samples=n_samples,
    )


__all__ = [
    "MonteCarloResult",
    "SobolSensitivityResult",
    "monte_carlo_simulate",
    "sensitivity_analysis",
    "sobol_sensitivity_analysis",
    "yield_analysis",
]
