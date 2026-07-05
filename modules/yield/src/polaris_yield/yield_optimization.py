"""基于灵敏度的良率优化（polaris-yield 子模块）。

从 v4 ``polaris.sim.yield_optimization`` 迁移；R13 不保留 v4 兼容路径。

## 核心功能

1. ``compute_worst_case_distance``: 最坏情况距离 (WCD) + 良率估计
2. ``allocate_tolerance_by_sensitivity``: Taguchi 容差分配（Lagrange）
3. ``optimize_yield_via_nominal_shift``: 标称值优化（WCD 梯度上升）

## 核心理论

### 1. Worst-Case Distance (WCD)

对单边规格 f(x) ≥ T (lower) 或 f(x) ≤ T (upper)，f 近似正态 N(μ_f, σ_f²)::

    d_wc = (μ_f - T) / σ_f   (lower spec, Y ≈ Φ(d_wc))
    d_wc = (T - μ_f) / σ_f   (upper spec, Y ≈ Φ(d_wc))

d_wc=0 → Y=50%; d_wc=3 → Y≈99.865% (3σ); d_wc=6 → Y≈99.9999998% (6σ)。

### 2. 基于灵敏度容差分配 (Taguchi 1987, Singhal-Pinel 1981)

固定总容差预算 B = Σ σ_i²，最小化 Var(f) = Σ (S_i σ_i)²::

    σ_i² = B · (1/S_i²) / Σ(1/S_j²),  即 σ_i ∝ 1/|S_i|

### 3. 标称值优化 (Nominal Shift)

简化梯度上升 (固定 σ_f)::

    x̂_{k+1} = x̂_k + α · sign · S_i / σ_f

## 学术依据（R02 学术诚信，≥5 文献 URL）

- Taguchi 1987, "Taguchi Techniques for Quality Engineering",
  American Supplier Institute
- Singhal & Pinel 1981, "Statistical Design Centering and Tolerancing
  Using Parametric Sampling", IEEE TCS 28(7):692-701,
  https://doi.org/10.1109/TCS.1981.1085043
- Spence & Soin 1988, "Tolerance Design of Electronic Circuits",
  Addison-Wesley
- Parkinson 1993, "Robust Optimal Design for Engineering-Based Design",
  Eng. Optim. 21(4):259-278,
  https://doi.org/10.1080/03052159308940948
- Madkour et al. 2015, "Yield Optimization Using Worst-Case Distance",
  IEEE TCAS-I 62(12):2925-2933,
  https://doi.org/10.1109/TCSI.2015.2495251
- NIST Engineering Statistics Handbook §5.5.6 Taguchi Designs
  https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm
- Bogaerts et al. 2018, layout-aware photonic yield,
  https://fib.intec.ugent.be/download/pub_4125.pdf
- scipy.stats.norm: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html

合规: R02 / R03 / R04 / R09。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class WorstCaseDistanceResult:
    """最坏情况距离 (WCD) 计算结果。

    Attributes:
        wcd: 最坏情况距离 d_wc = |μ_f - T| / σ_f。
        yield_estimate: 良率估计 Y ≈ Φ(d_wc)。
        f_nominal: 标称输出 f(x̂)。
        sigma_output: 输出标准差 σ_f。
        spec_threshold: 规格阈值 T。
        direction: 规格方向 "lower" 或 "upper"。
        n_evaluations: 总模型评估次数。
    """

    wcd: float = 0.0
    yield_estimate: float = 0.0
    f_nominal: float = 0.0
    sigma_output: float = 0.0
    spec_threshold: float = 0.0
    direction: str = "lower"
    n_evaluations: int = 0


@dataclass
class ToleranceAllocationResult:
    """基于灵敏度容差分配结果。

    Attributes:
        param_names: 参数名列表。
        sensitivities: 参数灵敏度 |∂f/∂x_i| 列表。
        allocated_sigmas: 优化后容差 σ_i 列表。
        original_sigmas: 原始容差列表（输入参考）。
        total_budget: 总容差预算 B = Σ σ_i²。
        expected_variance_output: 优化后预期输出方差。
        original_variance_output: 原始预期输出方差。
        variance_reduction: 方差减少比例 = 1 - new/old。
        n_evaluations: 总模型评估次数。
    """

    param_names: list[str] = field(default_factory=list)
    sensitivities: list[float] = field(default_factory=list)
    allocated_sigmas: list[float] = field(default_factory=list)
    original_sigmas: list[float] = field(default_factory=list)
    total_budget: float = 0.0
    expected_variance_output: float = 0.0
    original_variance_output: float = 0.0
    variance_reduction: float = 0.0
    n_evaluations: int = 0


@dataclass
class YieldOptimizationResult:
    """标称值优化结果。

    Attributes:
        original_yield: 优化前良率。
        optimized_yield: 优化后良率。
        original_wcd: 优化前 WCD。
        optimized_wcd: 优化后 WCD。
        optimal_params: 优化后标称值。
        original_params: 原始标称值。
        iterations: 实际迭代次数。
        converged: 是否收敛。
        wcd_history: 每轮 WCD 历史。
        n_evaluations: 总模型评估次数。
    """

    original_yield: float = 0.0
    optimized_yield: float = 0.0
    original_wcd: float = 0.0
    optimized_wcd: float = 0.0
    optimal_params: np.ndarray = field(
        default_factory=lambda: np.empty(0)
    )
    original_params: np.ndarray = field(
        default_factory=lambda: np.empty(0)
    )
    iterations: int = 0
    converged: bool = False
    wcd_history: list[float] = field(default_factory=list)
    n_evaluations: int = 0


# ============================================================================
# 内部辅助
# ============================================================================


def _compute_unnormalized_sensitivity(
    func: Callable[[np.ndarray], float],
    base_params: np.ndarray,
    delta: float = 1e-4,
) -> tuple[np.ndarray, int]:
    """计算 unnormalized 灵敏度 S_i = ∂f/∂x_i（中心差分）。

    Raises:
        RuntimeError: func 评估失败。
    """
    base_params = np.asarray(base_params, dtype=float)
    n = len(base_params)
    sensitivities = np.empty(n, dtype=float)
    n_eval = 1

    base_output = float(func(base_params))
    for i in range(n):
        eps = delta * max(abs(base_params[i]), 1e-8)
        params_plus = base_params.copy()
        params_minus = base_params.copy()
        params_plus[i] += eps
        params_minus[i] -= eps
        try:
            out_plus = float(func(params_plus))
            out_minus = float(func(params_minus))
        except Exception as e:
            raise RuntimeError(
                f"灵敏度计算 func 评估失败 (参数 {i}): "
                f"{type(e).__name__}: {e}。禁止 fall-back（R03）。"
            ) from e
        sensitivities[i] = (out_plus - out_minus) / (2 * eps)
        n_eval += 2

    return sensitivities, n_eval


# ============================================================================
# 公开 API
# ============================================================================


def compute_worst_case_distance(
    func: Callable[[np.ndarray], float],
    base_params: np.ndarray,
    param_sigmas: np.ndarray,
    spec_threshold: float,
    direction: str = "lower",
    sensitivity_delta: float = 1e-4,
) -> WorstCaseDistanceResult:
    """计算最坏情况距离 (WCD) 和良率估计。

    Args:
        func: 仿真函数 f(params) -> scalar。
        base_params: 标称参数 x̂。
        param_sigmas: 每个参数的容差 σ_i (std dev)。
        spec_threshold: 规格阈值 T。
        direction: "lower" (f≥T 合格) 或 "upper" (f≤T 合格)。
        sensitivity_delta: 中心差分相对步长。

    Returns:
        WorstCaseDistanceResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败或 σ_f = 0。

    学术依据:
    - Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251
    - Spence & Soin 1988
    - 一阶方差传播: σ_f² ≈ Σ S_i² σ_i²
    """
    base_params = np.asarray(base_params, dtype=float)
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if base_params.ndim != 1:
        raise ValueError(
            f"base_params 必须为 1D，得到 shape {base_params.shape}"
        )
    if param_sigmas.shape != base_params.shape:
        raise ValueError(
            f"param_sigmas shape {param_sigmas.shape} 与 "
            f"base_params {base_params.shape} 不匹配"
        )
    if np.any(param_sigmas <= 0):
        raise ValueError(f"param_sigmas 必须 > 0，得到 {param_sigmas}")
    if direction not in ("lower", "upper"):
        raise ValueError(
            f"direction 必须为 'lower' 或 'upper'，得到 '{direction}'"
        )

    try:
        f_nominal = float(func(base_params))
    except Exception as e:
        raise RuntimeError(
            f"func 标称评估失败: {type(e).__name__}: {e}。禁止 fall-back。"
        ) from e
    n_eval = 1

    sensitivities, n_sens = _compute_unnormalized_sensitivity(
        func, base_params, delta=sensitivity_delta
    )
    n_eval += n_sens

    sigma_output = float(
        np.sqrt(np.sum((sensitivities * param_sigmas) ** 2))
    )
    if sigma_output == 0.0:
        raise RuntimeError(
            "σ_f = 0: 输出对参数完全不敏感或 σ_i 全为 0，WCD 无定义。"
            "禁止 fall-back（R03）。"
        )

    if direction == "lower":
        wcd = (f_nominal - spec_threshold) / sigma_output
    else:
        wcd = (spec_threshold - f_nominal) / sigma_output

    yield_estimate = float(norm.cdf(wcd))

    return WorstCaseDistanceResult(
        wcd=wcd, yield_estimate=yield_estimate, f_nominal=f_nominal,
        sigma_output=sigma_output, spec_threshold=spec_threshold,
        direction=direction, n_evaluations=n_eval,
    )


def _validate_allocation_inputs(
    sensitivities: np.ndarray,
    total_budget: float,
    param_names: list[str] | None,
    n: int,
) -> list[str]:
    """校验容差分配输入参数。"""
    if total_budget <= 0:
        raise ValueError(f"total_budget 必须 > 0，得到 {total_budget}")
    if np.any(sensitivities < 0):
        neg_indices = np.where(sensitivities < 0)[0].tolist()
        raise ValueError(
            f"sensitivities 必须为非负（|∂f/∂x_i|），"
            f"但索引 {neg_indices} 处为负值。"
            f"请上游调用 np.abs(sensitivities) 后再传入（R03 禁止 fall-back）。"
        )
    if np.all(sensitivities == 0):
        raise ValueError(
            "所有灵敏度 = 0，无法分配容差（输出对参数无响应）。"
            "禁止 fall-back（R03）。"
        )
    if param_names is None:
        param_names = [f"param_{i}" for i in range(n)]
    if len(param_names) != n:
        raise ValueError(
            f"param_names 长度 {len(param_names)} 与参数数 {n} 不匹配"
        )
    return param_names


def _compute_lagrange_sigmas(
    sensitivities: np.ndarray, total_budget: float
) -> np.ndarray:
    """Lagrange 容差分配 σ_i ∝ 1/|S_i|。

    处理 S_i=0: 用最小非零灵敏度的 1/10 替代（保守上限）。

    Raises:
        RuntimeError: Σσ² ≠ B（数值校验失败）。
    """
    min_nonzero = float(np.min(sensitivities[sensitivities > 0]))
    s_for_alloc = np.where(
        sensitivities == 0, min_nonzero * 0.1, sensitivities
    )
    inv_s2 = 1.0 / (s_for_alloc**2)
    sum_inv_s2 = float(np.sum(inv_s2))
    allocated_var = total_budget * inv_s2 / sum_inv_s2
    allocated_sigmas = np.sqrt(allocated_var)

    actual_budget = float(np.sum(allocated_sigmas**2))
    if not np.isclose(actual_budget, total_budget, rtol=1e-10):
        raise RuntimeError(
            f"容差分配失败: Σσ²={actual_budget} ≠ B={total_budget}。"
            f"禁止 fall-back。"
        )
    return allocated_sigmas


def _compute_variance_comparison(
    sensitivities: np.ndarray,
    allocated_sigmas: np.ndarray,
    original_sigmas: np.ndarray | None,
    expected_var_output: float,
) -> tuple[float, float, float]:
    """计算原始方差对比。

    Returns:
        (original_var, original_budget, variance_reduction)。
    """
    if original_sigmas is None:
        return 0.0, 0.0, 0.0
    original_sigmas = np.asarray(original_sigmas, dtype=float)
    if original_sigmas.shape != sensitivities.shape:
        raise ValueError(
            f"original_sigmas shape {original_sigmas.shape} 与 "
            f"sensitivities {sensitivities.shape} 不匹配"
        )
    original_var = float(np.sum((sensitivities * original_sigmas) ** 2))
    original_budget = float(np.sum(original_sigmas**2))
    if original_var > 0:
        variance_reduction = 1.0 - expected_var_output / original_var
    else:
        variance_reduction = 0.0
    return original_var, original_budget, variance_reduction


def allocate_tolerance_by_sensitivity(
    sensitivities: np.ndarray,
    total_budget: float,
    param_names: list[str] | None = None,
    original_sigmas: np.ndarray | None = None,
) -> ToleranceAllocationResult:
    """基于灵敏度容差分配（Lagrange 解 σ_i ∝ 1/|S_i|）。

    Args:
        sensitivities: 参数灵敏度 |∂f/∂x_i| (n,)。
        total_budget: 总容差预算 B = Σ σ_i² (> 0)。
        param_names: 参数名列表。
        original_sigmas: 原始容差（对比用，None 则不报告方差减少）。

    Returns:
        ToleranceAllocationResult。

    Raises:
        ValueError: 参数无效或灵敏度为 0。

    学术依据:
    - Singhal & Pinel 1981, DOI: 10.1109/TCS.1981.1085043
    - Taguchi 1987
    - NIST Handbook §5.5.6
      https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm
    """
    sensitivities = np.asarray(sensitivities, dtype=float)
    if sensitivities.ndim != 1:
        raise ValueError(
            f"sensitivities 必须为 1D，得到 shape {sensitivities.shape}"
        )
    n = len(sensitivities)
    if n == 0:
        raise ValueError("sensitivities 不能为空")

    param_names = _validate_allocation_inputs(
        sensitivities, total_budget, param_names, n
    )
    allocated_sigmas = _compute_lagrange_sigmas(sensitivities, total_budget)
    expected_var_output = float(
        np.sum((sensitivities * allocated_sigmas) ** 2)
    )
    original_var, original_budget, variance_reduction = (
        _compute_variance_comparison(
            sensitivities, allocated_sigmas, original_sigmas,
            expected_var_output,
        )
    )

    return ToleranceAllocationResult(
        param_names=list(param_names),
        sensitivities=[float(s) for s in sensitivities],
        allocated_sigmas=[float(s) for s in allocated_sigmas],
        original_sigmas=(
            [float(s) for s in original_sigmas]
            if original_sigmas is not None
            else []
        ),
        total_budget=total_budget,
        expected_variance_output=expected_var_output,
        original_variance_output=original_var,
        variance_reduction=float(variance_reduction),
        n_evaluations=0,
    )


def _validate_yield_shift_params(
    base_params: np.ndarray,
    param_sigmas: np.ndarray,
    direction: str,
    max_iter: int,
    learning_rate: float,
) -> tuple[np.ndarray, np.ndarray]:
    """校验 optimize_yield_via_nominal_shift 参数（R03 禁止 fall-back）。"""
    base_params = np.asarray(base_params, dtype=float).copy()
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if base_params.ndim != 1:
        raise ValueError(
            f"base_params 必须为 1D，得到 shape {base_params.shape}"
        )
    if param_sigmas.shape != base_params.shape:
        raise ValueError("param_sigmas shape 与 base_params 不匹配")
    if np.any(param_sigmas <= 0):
        raise ValueError(f"param_sigmas 必须 > 0，得到 {param_sigmas}")
    if direction not in ("lower", "upper"):
        raise ValueError(
            f"direction 必须为 'lower' 或 'upper'，得到 '{direction}'"
        )
    if max_iter < 1:
        raise ValueError(f"max_iter 必须 >= 1，得到 {max_iter}")
    if not 0 < learning_rate <= 1.0:
        raise ValueError(
            f"learning_rate 应在 (0, 1]，得到 {learning_rate}"
        )
    return base_params, param_sigmas


def _run_yield_shift_iter_loop(
    func: Callable[[np.ndarray], float],
    x: np.ndarray,
    param_sigmas: np.ndarray,
    spec_threshold: float,
    direction: str,
    max_iter: int,
    learning_rate: float,
    tol: float,
    sensitivity_delta: float,
    sign: float,
    wcd_history: list[float],
    n_eval_total: int,
) -> tuple[np.ndarray, list[float], int, bool, int]:
    """标称值优化主循环（WCD 梯度上升）。

    返回 (x, wcd_history, n_eval_total, converged, actual_iter)。
    """
    converged = False
    actual_iter = 0
    for k in range(max_iter):
        actual_iter = k + 1
        sens, n_sens = _compute_unnormalized_sensitivity(
            func, x, delta=sensitivity_delta
        )
        n_eval_total += n_sens
        sigma_f = float(np.sqrt(np.sum((sens * param_sigmas) ** 2)))
        if sigma_f == 0.0:
            raise RuntimeError(
                f"迭代 {k}: σ_f = 0，无法计算梯度。禁止 fall-back。"
            )
        grad = sign * sens / sigma_f
        step = learning_rate * param_sigmas * grad
        x_new = x + step
        new_wcd_result = compute_worst_case_distance(
            func, x_new, param_sigmas, spec_threshold, direction,
            sensitivity_delta=sensitivity_delta,
        )
        n_eval_total += new_wcd_result.n_evaluations
        wcd_improvement = new_wcd_result.wcd - wcd_history[-1]
        if new_wcd_result.wcd > wcd_history[-1]:
            x = x_new
            wcd_history.append(new_wcd_result.wcd)
        else:
            wcd_history.append(wcd_history[-1])
            converged = True
            break
        if abs(wcd_improvement) < tol:
            converged = True
            break
    return x, wcd_history, n_eval_total, converged, actual_iter


def _finalize_yield_shift(
    func: Callable[[np.ndarray], float],
    x: np.ndarray,
    param_sigmas: np.ndarray,
    spec_threshold: float,
    direction: str,
    sensitivity_delta: float,
    original: YieldOptimizationResult,
    wcd_history: list[float],
    n_eval_total: int,
    actual_iter: int,
    converged: bool,
    base_params: np.ndarray,
) -> YieldOptimizationResult:
    """最终 WCD 评估并组装 YieldOptimizationResult。"""
    final = compute_worst_case_distance(
        func, x, param_sigmas, spec_threshold, direction,
        sensitivity_delta=sensitivity_delta,
    )
    n_eval_total += final.n_evaluations
    return YieldOptimizationResult(
        original_yield=original.yield_estimate,
        optimized_yield=final.yield_estimate,
        original_wcd=original.wcd, optimized_wcd=final.wcd,
        optimal_params=x, original_params=base_params,
        iterations=actual_iter, converged=converged,
        wcd_history=wcd_history, n_evaluations=n_eval_total,
    )


def optimize_yield_via_nominal_shift(
    func: Callable[[np.ndarray], float],
    base_params: np.ndarray,
    param_sigmas: np.ndarray,
    spec_threshold: float,
    direction: str = "lower",
    max_iter: int = 50,
    learning_rate: float = 0.5,
    tol: float = 1e-4,
    sensitivity_delta: float = 1e-4,
) -> YieldOptimizationResult:
    """通过标称值移动最大化良率（WCD 梯度上升）。

    简化梯度上升 (固定 σ_f)::

        x̂_{k+1} = x̂_k + α · sign · S_i / σ_f

    sign = +1 (lower spec, 增大 f) 或 -1 (upper spec, 减小 f)。

    Args:
        func: 仿真函数。
        base_params: 初始标称值。
        param_sigmas: 参数容差 σ_i (固定)。
        spec_threshold: 规格阈值 T。
        direction: "lower" (f≥T) 或 "upper" (f≤T)。
        max_iter: 最大迭代次数。
        learning_rate: 学习率 α (0-1)。
        tol: 收敛阈值（WCD 改善 < tol 时停止）。
        sensitivity_delta: 中心差分相对步长。

    Returns:
        YieldOptimizationResult。

    Raises:
        ValueError: 参数无效。
        RuntimeError: func 评估失败或 σ_f = 0。

    学术依据:
    - Parkinson 1993, DOI: 10.1080/03052159308940948
    - Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251
    """
    base_params, param_sigmas = _validate_yield_shift_params(
        base_params, param_sigmas, direction, max_iter, learning_rate
    )
    original = compute_worst_case_distance(
        func, base_params, param_sigmas, spec_threshold, direction,
        sensitivity_delta=sensitivity_delta,
    )
    wcd_history: list[float] = [original.wcd]
    n_eval_total = original.n_evaluations
    x = base_params.copy()
    sign = 1.0 if direction == "lower" else -1.0
    x, wcd_history, n_eval_total, converged, actual_iter = _run_yield_shift_iter_loop(
        func, x, param_sigmas, spec_threshold, direction, max_iter,
        learning_rate, tol, sensitivity_delta, sign, wcd_history, n_eval_total,
    )
    return _finalize_yield_shift(
        func, x, param_sigmas, spec_threshold, direction,
        sensitivity_delta, original, wcd_history, n_eval_total,
        actual_iter, converged, base_params,
    )


__all__ = [
    "ToleranceAllocationResult",
    "WorstCaseDistanceResult",
    "YieldOptimizationResult",
    "allocate_tolerance_by_sensitivity",
    "compute_worst_case_distance",
    "optimize_yield_via_nominal_shift",
]
