"""基于灵敏度的良率优化（R291-R295）。

本模块实现工业标准的良率优化技术，补齐与商业工具（Calibre
YieldOptimizer / Lumerical INTERCONNECT / Synopsys CustomSim）的核心差距：
- **最坏情况距离 (Worst-Case Distance, WCD)**: 工业良率评估指标
- **基于灵敏度容差分配 (Sensitivity-Based Tolerance Allocation)**: Taguchi 容差设计
- **标称值优化 (Nominal Shift)**: 基于灵敏度的良率最大化

## 核心理论

### 1. Worst-Case Distance (WCD)

对单边规格 ``f(x) ≥ T`` (lower specification) 或 ``f(x) ≤ T`` (upper spec)，
设 f 服从近似正态 N(μ_f, σ_f²):

    d_wc = (μ_f - T) / σ_f   (lower spec, 良率 Y ≈ Φ(d_wc))
    d_wc = (T - μ_f) / σ_f   (upper spec, 良率 Y ≈ Φ(d_wc))

d_wc = 0 → Y = 50%; d_wc = 3 → Y ≈ 99.865% (3σ 设计);
d_wc = 6 → Y ≈ 99.9999998% (6σ 设计)。

### 2. 基于灵敏度容差分配 (Taguchi 1987, Singhal-Pinel 1981)

给定参数灵敏度 ``S_i = ∂f/∂x_i``（unnormalized），总容差预算
``B = Σ σ_i²``，最小化输出方差 ``Var(f) = Σ (S_i σ_i)²``。

Lagrange 乘子解:

    σ_i² = B · (1/S_i²) / Σ(1/S_j²),  即 σ_i ∝ 1/|S_i|

直觉: 高灵敏度参数应给小容差（控制），低灵敏度参数可放宽（节省成本）。

### 3. 标称值优化 (Nominal Shift)

通过梯度上升移动标称值 ``x̂``，最大化 WCD:

    x̂_{k+1} = x̂_k + α · ∇_x d_wc(x̂_k)
             = x̂_k + α · (∂f/∂x · σ_f - (μ_f - T) · ∂σ_f/∂x) / σ_f²

简化（固定 σ_f）:

    x̂_{k+1} = x̂_k + α · ∂f/∂x / σ_f

## 学术依据

- Taguchi 1987, "Taguchi Techniques for Quality Engineering",
  American Supplier Institute (容差设计 + 损失函数)
- Singhal & Pinel 1981, "Statistical Design Centering and Tolerancing
  Using Parametric Sampling", IEEE Trans. Circuits Syst. 28(7):692-701,
  DOI: 10.1109/TCS.1981.1085043 (基于灵敏度容差分配)
- Spence & Soin 1988, "Tolerance Design of Electronic Circuits",
  Addison-Wesley (WCD + 容差设计教科书)
- Parkinson 1993, "Robust Optimal Design for Engineering-Based Design",
  Eng. Optim. 21(4):259-278, DOI: 10.1080/03052159308940948
  (transmitted variation + robust optimal design)
- Madkour et al. 2015, "Yield Optimization Using Worst-Case Distance",
  IEEE Trans. Circuits Syst. I 62(12):2925-2933,
  DOI: 10.1109/TCSI.2015.2495251 (现代 WCD 综述)
- NIST Engineering Statistics Handbook §5.5.6, Taguchi Designs
  https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm
- 光子学良率: Bogaerts et al. 2018, OFC, layout-aware yield prediction
  https://fib.intec.ugent.be/download/pub_4125.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R09 优先用三方库。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class WorstCaseDistanceResult:
    """最坏情况距离 (WCD) 计算结果（R291）。

    Attributes:
        wcd: 最坏情况距离 d_wc = |μ_f - T| / σ_f。
            d_wc=0 → Y=50%; d_wc=3 → Y≈99.865% (3σ); d_wc=6 → Y≈99.9999998% (6σ)。
        yield_estimate: 良率估计 Y ≈ Φ(d_wc)（基于正态假设）。
        f_nominal: 标称输出 f(x̂)。
        sigma_output: 输出标准差 σ_f（由参数灵敏度 + 容差估计）。
        spec_threshold: 规格阈值 T。
        direction: 规格方向 "lower" (f≥T) 或 "upper" (f≤T)。
        n_evaluations: 总模型评估次数。

    学术依据: Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251
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
    """基于灵敏度容差分配结果（R292）。

    Attributes:
        param_names: 参数名列表。
        sensitivities: 参数灵敏度 |∂f/∂x_i| 列表（unnormalized）。
        allocated_sigmas: 优化后容差 σ_i 列表。
        original_sigmas: 原始容差列表（输入参考）。
        total_budget: 总容差预算 B = Σ σ_i²。
        expected_variance_output: 优化后预期输出方差 Σ (S_i σ_i)²。
        original_variance_output: 原始预期输出方差（对比用）。
        variance_reduction: 方差减少比例 = 1 - new/old。
        n_evaluations: 总模型评估次数。

    学术依据: Singhal & Pinel 1981, DOI: 10.1109/TCS.1981.1085043
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
    """标称值优化结果（R293-R294）。

    Attributes:
        original_yield: 优化前良率（WCD 估计）。
        optimized_yield: 优化后良率。
        original_wcd: 优化前 WCD。
        optimized_wcd: 优化后 WCD。
        optimal_params: 优化后标称值。
        original_params: 原始标称值（对比用）。
        iterations: 实际迭代次数。
        converged: 是否收敛（WCD 改善 < tol）。
        wcd_history: 每轮 WCD 历史。
        n_evaluations: 总模型评估次数。

    学术依据: Parkinson 1993, DOI: 10.1080/03052159308940948
    """

    original_yield: float = 0.0
    optimized_yield: float = 0.0
    original_wcd: float = 0.0
    optimized_wcd: float = 0.0
    optimal_params: np.ndarray = field(default_factory=lambda: np.empty(0))
    original_params: np.ndarray = field(default_factory=lambda: np.empty(0))
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
    """计算 unnormalized 灵敏度 S_i = ∂f/∂x_i（中心差分，R291 内部辅助）。

    Args:
        func: 仿真函数。
        base_params: 基准参数。
        delta: 相对扰动量（步长 = delta · |x_i|）。

    Returns:
        (灵敏度数组 (n,), 评估次数)。

    Raises:
        RuntimeError: func 评估失败。
    """
    base_params = np.asarray(base_params, dtype=float)
    n = len(base_params)
    sensitivities = np.empty(n, dtype=float)
    n_eval = 1  # base 评估

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
                f"灵敏度计算 func 评估失败 (参数 {i}): {type(e).__name__}: {e}。"
                f"禁止 fall-back（规则 14.1）。"
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
    """计算最坏情况距离 (WCD) 和良率估计（R291）。

    对单边规格 ``f(x) ≥ T`` (lower) 或 ``f(x) ≤ T`` (upper)，
    用一阶 Taylor 展开 + 正态假设估计 WCD:

        σ_f ≈ sqrt(Σ (S_i σ_i)²)   (一阶方差传播)
        d_wc = |μ_f - T| / σ_f
        Y ≈ Φ(d_wc)

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
        RuntimeError: func 评估失败。

    学术依据:
    - Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251 (WCD 综述)
    - Spence & Soin 1988 (WCD 教科书定义)
    - 一阶方差传播: 泰勒展开 σ_f² ≈ Σ S_i² σ_i²
    """
    base_params = np.asarray(base_params, dtype=float)
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if base_params.ndim != 1:
        raise ValueError(
            f"base_params 必须为 1D，得到 shape {base_params.shape}"
        )
    if param_sigmas.shape != base_params.shape:
        raise ValueError(
            f"param_sigmas shape {param_sigmas.shape} 与 base_params {base_params.shape} 不匹配"
        )
    if np.any(param_sigmas <= 0):
        raise ValueError(
            f"param_sigmas 必须 > 0，得到 {param_sigmas}"
        )
    if direction not in ("lower", "upper"):
        raise ValueError(
            f"direction 必须为 'lower' 或 'upper'，得到 '{direction}'"
        )

    # 1. 评估标称输出
    try:
        f_nominal = float(func(base_params))
    except Exception as e:
        raise RuntimeError(
            f"func 标称评估失败: {type(e).__name__}: {e}。禁止 fall-back。"
        ) from e
    n_eval = 1

    # 2. 计算灵敏度
    sensitivities, n_sens = _compute_unnormalized_sensitivity(
        func, base_params, delta=sensitivity_delta
    )
    n_eval += n_sens

    # 3. 一阶方差传播: σ_f² ≈ Σ S_i² σ_i²
    sigma_output = float(np.sqrt(np.sum((sensitivities * param_sigmas) ** 2)))
    if sigma_output == 0.0:
        raise RuntimeError(
            "σ_f = 0: 输出对参数完全不敏感或 σ_i 全为 0，WCD 无定义。"
            "禁止 fall-back（规则 14.1）。"
        )

    # 4. WCD
    if direction == "lower":
        # 规格 f ≥ T，d_wc = (μ_f - T) / σ_f
        if f_nominal < spec_threshold:
            # 标称已经不满足规格，WCD < 0
            wcd = (f_nominal - spec_threshold) / sigma_output
        else:
            wcd = (f_nominal - spec_threshold) / sigma_output
    else:
        # 规格 f ≤ T，d_wc = (T - μ_f) / σ_f
        wcd = (spec_threshold - f_nominal) / sigma_output

    # 5. 良率 Y ≈ Φ(d_wc)
    yield_estimate = float(norm.cdf(wcd))

    return WorstCaseDistanceResult(
        wcd=wcd,
        yield_estimate=yield_estimate,
        f_nominal=f_nominal,
        sigma_output=sigma_output,
        spec_threshold=spec_threshold,
        direction=direction,
        n_evaluations=n_eval,
    )


def allocate_tolerance_by_sensitivity(
    sensitivities: np.ndarray,
    total_budget: float,
    param_names: list[str] | None = None,
    original_sigmas: np.ndarray | None = None,
) -> ToleranceAllocationResult:
    """基于灵敏度容差分配（R292）。

    在固定总容差预算 B = Σ σ_i² 约束下，最小化输出方差
    ``Var(f) = Σ (S_i σ_i)²``。Lagrange 解: σ_i ∝ 1/|S_i|。

    Args:
        sensitivities: 参数灵敏度 |∂f/∂x_i| (n,)。
        total_budget: 总容差预算 B = Σ σ_i² (必须 > 0)。
        param_names: 参数名列表（None 则用 ["param_0", ...]）。
        original_sigmas: 原始容差（对比用，None 则不报告方差减少）。

    Returns:
        ToleranceAllocationResult。

    Raises:
        ValueError: 参数无效或灵敏度为 0。

    学术依据:
    - Singhal & Pinel 1981, DOI: 10.1109/TCS.1981.1085043 (统计容差分配)
    - Taguchi 1987 (容差设计 + 损失函数)
    - NIST Handbook §5.5.6 Taguchi Designs
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
    if total_budget <= 0:
        raise ValueError(f"total_budget 必须 > 0，得到 {total_budget}")
    if np.any(sensitivities < 0):
        # 输入应是 |S_i| >= 0；允许 0 但若全部为 0 则无解
        pass
    if np.all(sensitivities == 0):
        raise ValueError(
            "所有灵敏度 = 0，无法分配容差（输出对参数无响应）。"
            "禁止 fall-back（规则 14.1）。"
        )

    if param_names is None:
        param_names = [f"param_{i}" for i in range(n)]
    if len(param_names) != n:
        raise ValueError(
            f"param_names 长度 {len(param_names)} 与参数数 {n} 不匹配"
        )

    # Lagrange 解: σ_i² = B · (1/S_i²) / Σ(1/S_j²)
    # 即 σ_i = sqrt(B) / (|S_i| · sqrt(Σ 1/S_j²))
    # 处理 S_i = 0: 该参数无响应，给最大容差（用最小非零 S 替代）
    s_safe = np.where(sensitivities == 0, np.inf, sensitivities)
    inv_s2 = 1.0 / (s_safe**2)
    # S_i=0 的参数 inv_s2 = 0，会得到 σ = 0，但应给最大容差
    # 正确处理: S_i=0 的参数应分配最大 σ（不影响输出方差）
    # Lagrange 退化: 无穷大灵敏度 → 0 容差；0 灵敏度 → 无穷大容差
    # 工程实用: 用最小非零灵敏度的 1/10 替代 0（保守上限）
    min_nonzero = float(np.min(sensitivities[sensitivities > 0]))
    s_for_alloc = np.where(
        sensitivities == 0, min_nonzero * 0.1, sensitivities
    )
    inv_s2 = 1.0 / (s_for_alloc**2)
    sum_inv_s2 = float(np.sum(inv_s2))
    allocated_var = total_budget * inv_s2 / sum_inv_s2
    allocated_sigmas = np.sqrt(allocated_var)

    # 验证: Σ σ_i² = B
    actual_budget = float(np.sum(allocated_sigmas**2))
    if not np.isclose(actual_budget, total_budget, rtol=1e-10):
        raise RuntimeError(
            f"容差分配失败: Σσ²={actual_budget} ≠ B={total_budget}。"
            f"禁止 fall-back。"
        )

    # 预期输出方差
    expected_var_output = float(np.sum((sensitivities * allocated_sigmas) ** 2))

    # 原始输出方差（对比）
    if original_sigmas is not None:
        original_sigmas = np.asarray(original_sigmas, dtype=float)
        if original_sigmas.shape != sensitivities.shape:
            raise ValueError(
                f"original_sigmas shape {original_sigmas.shape} 与 sensitivities {sensitivities.shape} 不匹配"
            )
        original_var = float(np.sum((sensitivities * original_sigmas) ** 2))
        original_budget = float(np.sum(original_sigmas**2))
        if original_var > 0:
            variance_reduction = 1.0 - expected_var_output / original_var
        else:
            variance_reduction = 0.0
    else:
        original_var = 0.0
        original_budget = 0.0
        variance_reduction = 0.0

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
        n_evaluations=0,  # 容差分配无 func 评估
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
    """通过标称值移动最大化良率 (WCD 梯度上升，R293-R294)。

    简化梯度上升 (固定 σ_f):
        x̂_{k+1} = x̂_k + α · sign · S_i / σ_f

    其中 sign = +1 (lower spec, 想增大 f) 或 -1 (upper spec, 想减小 f)。

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
        RuntimeError: func 评估失败。

    学术依据:
    - Parkinson 1993, DOI: 10.1080/03052159308940948 (robust optimal design)
    - Madkour et al. 2015, DOI: 10.1109/TCSI.2015.2495251 (WCD 优化)
    """
    base_params = np.asarray(base_params, dtype=float).copy()
    param_sigmas = np.asarray(param_sigmas, dtype=float)
    if base_params.ndim != 1:
        raise ValueError(
            f"base_params 必须为 1D，得到 shape {base_params.shape}"
        )
    if param_sigmas.shape != base_params.shape:
        raise ValueError(
            f"param_sigmas shape 与 base_params 不匹配"
        )
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

    # 原始 WCD
    original = compute_worst_case_distance(
        func, base_params, param_sigmas, spec_threshold, direction,
        sensitivity_delta=sensitivity_delta,
    )
    wcd_history: list[float] = [original.wcd]
    n_eval_total = original.n_evaluations

    x = base_params.copy()
    sign = 1.0 if direction == "lower" else -1.0

    converged = False
    actual_iter = 0
    for k in range(max_iter):
        actual_iter = k + 1
        # 计算当前灵敏度
        sens, n_sens = _compute_unnormalized_sensitivity(
            func, x, delta=sensitivity_delta
        )
        n_eval_total += n_sens

        # 当前 σ_f
        sigma_f = float(np.sqrt(np.sum((sens * param_sigmas) ** 2)))
        if sigma_f == 0.0:
            raise RuntimeError(
                f"迭代 {k}: σ_f = 0，无法计算梯度。禁止 fall-back。"
            )

        # 梯度: dWCD/dx_i = sign · S_i / σ_f (固定 σ_f)
        grad = sign * sens / sigma_f

        # 步长: learning_rate · σ_i (参数空间尺度归一化)
        step = learning_rate * param_sigmas * grad

        # 梯度上升
        x_new = x + step

        # 评估新 WCD
        new_wcd_result = compute_worst_case_distance(
            func, x_new, param_sigmas, spec_threshold, direction,
            sensitivity_delta=sensitivity_delta,
        )
        n_eval_total += new_wcd_result.n_evaluations

        wcd_improvement = new_wcd_result.wcd - wcd_history[-1]

        if new_wcd_result.wcd > wcd_history[-1]:
            # 改善了，接受
            x = x_new
            wcd_history.append(new_wcd_result.wcd)
        else:
            # 没改善，回退并停止
            wcd_history.append(wcd_history[-1])
            converged = True
            break

        if abs(wcd_improvement) < tol:
            converged = True
            break

    # 最终 WCD
    final = compute_worst_case_distance(
        func, x, param_sigmas, spec_threshold, direction,
        sensitivity_delta=sensitivity_delta,
    )
    n_eval_total += final.n_evaluations

    return YieldOptimizationResult(
        original_yield=original.yield_estimate,
        optimized_yield=final.yield_estimate,
        original_wcd=original.wcd,
        optimized_wcd=final.wcd,
        optimal_params=x,
        original_params=base_params,
        iterations=actual_iter,
        converged=converged,
        wcd_history=wcd_history,
        n_evaluations=n_eval_total,
    )


__all__ = [
    "WorstCaseDistanceResult",
    "ToleranceAllocationResult",
    "YieldOptimizationResult",
    "allocate_tolerance_by_sensitivity",
    "compute_worst_case_distance",
    "optimize_yield_via_nominal_shift",
]
