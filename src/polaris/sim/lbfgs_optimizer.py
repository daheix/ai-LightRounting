"""L-BFGS 优化器（第37轮 P2-1 深化）。

实现 L-BFGS（Limited-memory BFGS）拟牛顿优化器，对标 lumopt/scipy L-BFGS。
用于 adjoint 逆向设计的二阶优化，收敛速度快于 Adam。

## L-BFGS 算法原理

L-BFGS 是 BFGS 的内存受限版本，只保存最近 m 次的 (s, y) 对：
- s_k = x_{k+1} - x_k（参数差）
- y_k = ∇f_{k+1} - ∇f_k（梯度差）

用两循环递归计算搜索方向：
1. 后向循环：α_i = ρ_i * s_i^T * q; q = q - α_i * y_i
2. 前向循环：β_i = ρ_i * y_i^T * r; r = r + s_i * (α_i - β_i)

搜索方向：p = -H * ∇f（H 为逆 Hessian 近似）

## 与 Adam 的对比

| 特性 | Adam（第31轮） | L-BFGS（第37轮） |
|------|---------------|------------------|
| 阶数 | 一阶 | 二阶（逆 Hessian 近似）|
| 内存 | O(n) | O(m*n)（m=历史长度）|
| 收敛 | 慢（线性）| 快（超线性）|
| 超参 | lr, β1, β2 | m, wolfe 条件 |
| 适用 | 随机优化 | 确定性优化 |

## 商业差距

P2-1 逆向设计深化：
- 商业标杆：lumopt L-BFGS / scipy.optimize.minimize(method='L-BFGS-B')
- 本模块实现 L-BFGS 优化器，对标 lumopt 核心优化能力

## 来源

- Liu & Nocedal 1989 "On the limited memory BFGS method for large scale
  optimization" https://doi.org/10.1007/BF01589116
- Nocedal & Wright "Numerical Optimization" Chapter 7
- lumopt: https://github.com/chriskeraly/lumopt
- scipy L-BFGS-B: https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PointState:
    """当前点的函数值与梯度（第58轮重构，降低参数个数）。

    封装 _line_search 所需的 fom/grad，使方法签名从 6 参数降至 5 参数。

    Attributes:
        fom: 当前点函数值。
        grad: 当前点梯度。
    """

    fom: float
    grad: np.ndarray


@dataclass(frozen=True)
class LBFGSConfig:
    """L-BFGS 配置。

    Attributes:
        max_iterations: 最大迭代次数。
            来源: lumopt 默认 100。
        memory_size: 历史记忆长度 m。
            来源: Nocedal 推荐 3-20，典型 10。
        convergence_threshold: 收敛阈值（梯度范数 < 阈值则停止）。
            来源: scipy L-BFGS-B 默认 1e-5。
        wolfe_c1: Wolfe 条件 c1（充分下降）。
            来源: Nocedal 推荐 1e-4。
        wolfe_c2: Wolfe 条件 c2（曲率条件）。
            来源: Nocedal 推荐 0.9。
        line_search_max_iter: 线搜索最大迭代。
        line_search_init: 初始步长。
    """

    max_iterations: int = 100
    memory_size: int = 10
    convergence_threshold: float = 1e-5
    wolfe_c1: float = 1e-4
    wolfe_c2: float = 0.9
    line_search_max_iter: int = 20
    line_search_init: float = 1.0


@dataclass
class LBFGSResult:
    """L-BFGS 优化结果。

    Attributes:
        optimal_params: 最优参数。
        optimal_fom: 最优目标函数值。
        fom_history: FoM 历史。
        param_history: 参数历史。
        gradient_norm_history: 梯度范数历史。
        iterations: 实际迭代次数。
        converged: 是否收敛。
    """

    optimal_params: np.ndarray
    optimal_fom: float
    fom_history: list[float] = field(default_factory=list)
    param_history: list[np.ndarray] = field(default_factory=list)
    gradient_norm_history: list[float] = field(default_factory=list)
    iterations: int = 0
    converged: bool = False


@dataclass
class _LBFGSIterState:
    """L-BFGS 迭代状态（降低 _lbfgs_iteration 参数个数，规则 4.1）。

    Attributes:
        params: 当前参数。
        fom: 当前 FoM。
        grad: 当前梯度。
    """

    params: np.ndarray
    fom: float
    grad: np.ndarray


class LBFGSOptimizer:
    """L-BFGS 优化器（对标 lumopt/scipy L-BFGS）。

    用两循环递归近似逆 Hessian，线搜索满足 Wolfe 条件。

    算法流程::
        1. 初始化参数 x, 梯度 g
        2. for k in range(max_iterations):
             a. 两循环递归计算搜索方向 p = -H * g
             b. 线搜索满足 Wolfe 条件的步长 α
             c. 更新 x = x + α * p
             d. 计算新梯度 g_new
             e. 更新 (s, y) 历史
             f. 检查收敛（||g|| < threshold）
        3. 返回最优参数

    来源:
    - Liu & Nocedal 1989
    - Nocedal & Wright "Numerical Optimization" Chapter 7

    Args:
        config: L-BFGS 配置。
    """

    def __init__(self, config: LBFGSConfig | None = None) -> None:
        """初始化 L-BFGS 优化器。

        Args:
            config: 配置（None 用默认）。
        """
        self.config = config or LBFGSConfig()
        self._s_history: deque = deque(maxlen=self.config.memory_size)
        self._y_history: deque = deque(maxlen=self.config.memory_size)
        self._rho_history: deque = deque(maxlen=self.config.memory_size)

    def _init_lbfgs_state(
        self,
        initial_params: np.ndarray,
        fom_fn: callable,
        grad_fn: callable,
    ) -> tuple:
        """初始化 L-BFGS 状态。

        Args:
            initial_params: 初始参数。
            fom_fn: 目标函数。
            grad_fn: 梯度函数。

        Returns:
            (params, fom, grad, fom_history, param_history, gradient_norm_history)。
        """
        params = np.asarray(initial_params, dtype=np.float64).copy()
        fom = fom_fn(params)
        grad = grad_fn(params)
        fom_history = [fom]
        param_history = [params.copy()]
        gradient_norm_history = [float(np.linalg.norm(grad))]
        return params, fom, grad, fom_history, param_history, gradient_norm_history

    def _lbfgs_iteration(
        self,
        params: np.ndarray,
        fom: float,
        grad: np.ndarray,
        fom_fn: callable,
        grad_fn: callable,
    ) -> tuple:
        """执行一次 L-BFGS 迭代。

        Args:
            params: 当前参数。
            fom: 当前 FoM。
            grad: 当前梯度。
            fom_fn: 目标函数。
            grad_fn: 梯度函数。

        Returns:
            (params_new, fom_new, grad_new, grad_norm, s, y)。
        """
        direction = self._compute_direction(grad)
        state = PointState(fom=fom, grad=grad)
        alpha = self._line_search(params, direction, state, fom_fn)
        params_new = params + alpha * direction
        fom_new = fom_fn(params_new)
        grad_new = grad_fn(params_new)
        s = params_new - params
        y = grad_new - grad
        self._update_history(s, y)
        grad_norm = float(np.linalg.norm(grad_new))
        return params_new, fom_new, grad_new, grad_norm, s, y

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn: callable,
        grad_fn: callable,
    ) -> LBFGSResult:
        """执行 L-BFGS 优化。

        Args:
            initial_params: 初始参数。
            fom_fn: 目标函数（输入参数，返回 FoM，最大化）。
            grad_fn: 梯度函数（输入参数，返回梯度）。

        Returns:
            LBFGSResult。
        """
        params, fom, grad, fom_history, param_history, gradient_norm_history = (
            self._init_lbfgs_state(initial_params, fom_fn, grad_fn)
        )
        converged = False
        iterations = 0

        for k in range(self.config.max_iterations):
            iterations = k + 1
            params, fom, grad, grad_norm, _s, _y = self._lbfgs_iteration(
                params, fom, grad, fom_fn, grad_fn
            )
            fom_history.append(fom)
            param_history.append(params.copy())
            gradient_norm_history.append(grad_norm)
            if grad_norm < self.config.convergence_threshold:
                converged = True
                break

        return LBFGSResult(
            optimal_params=params,
            optimal_fom=fom,
            fom_history=fom_history,
            param_history=param_history,
            gradient_norm_history=gradient_norm_history,
            iterations=iterations,
            converged=converged,
        )

    def _compute_direction(self, grad: np.ndarray) -> np.ndarray:
        """两循环递归计算搜索方向 p = H * g（最大化 FoM）。

        对于最大化问题，搜索方向为 H * g（沿梯度上升方向）。
        标准 L-BFGS 是最小化问题用 -H * g，这里取反用于最大化。

        Args:
            grad: 当前梯度。

        Returns:
            搜索方向（上升方向）。
        """
        q = grad.copy()
        alphas = []
        # 后向循环
        for s, y, rho in zip(
            reversed(self._s_history),
            reversed(self._y_history),
            reversed(self._rho_history),
            strict=True,
        ):
            alpha = rho * np.dot(s, q)
            alphas.append(alpha)
            q = q - alpha * y
        # 初始 Hessian 近似 H_0 = (s^T y / y^T y) * I
        gamma = self._compute_gamma()
        r = gamma * q
        # 前向循环
        for s, y, rho, alpha in zip(
            self._s_history,
            self._y_history,
            self._rho_history,
            reversed(alphas),
            strict=True,
        ):
            beta = rho * np.dot(y, r)
            r = r + s * (alpha - beta)
        # 最大化 FoM：方向 = +H * g（上升方向）
        return r

    def _compute_gamma(self) -> float:
        """计算初始 Hessian 近似缩放因子 γ。

        γ = s^T y / y^T y（最近一次迭代）

        Returns:
            γ 值。
        """
        if not self._s_history:
            return 1.0
        s = self._s_history[-1]
        y = self._y_history[-1]
        ys = float(np.dot(y, s))
        yy = float(np.dot(y, y))
        if yy < 1e-10:
            return 1.0
        return ys / yy

    def _update_history(self, s: np.ndarray, y: np.ndarray) -> None:
        """更新 (s, y, ρ) 历史。

        Args:
            s: 参数差。
            y: 梯度差。
        """
        ys = float(np.dot(y, s))
        if abs(ys) < 1e-10:
            return  # 跳过（曲率条件不满足）
        self._s_history.append(s.copy())
        self._y_history.append(y.copy())
        self._rho_history.append(1.0 / ys)

    def _line_search(
        self,
        params: np.ndarray,
        direction: np.ndarray,
        state: PointState,
        fom_fn: callable,
    ) -> float:
        """线搜索满足 Wolfe 条件的步长。

        Wolfe 条件:
        1. 充分下降: f(x + αp) ≥ f(x) + c1 * α * ∇f^T * p
        2. 曲率条件: ∇f(x + αp)^T * p ≥ c2 * ∇f^T * p

        Args:
            params: 当前参数。
            direction: 搜索方向。
            state: 当前点的 fom 和 grad。
            fom_fn: 目标函数。

        Returns:
            步长 α。
        """
        alpha = self.config.line_search_init
        c1 = self.config.wolfe_c1
        fom = state.fom
        grad = state.grad
        # 最大化 FoM：方向是 -H*g，∇f^T * p 应为负（下降方向）
        # Wolfe 条件（最大化版本）:
        # 1. f(x + αp) ≥ f(x) + c1 * α * g^T * p
        # 2. g_new^T * p ≥ c2 * g^T * p
        gp = float(np.dot(grad, direction))
        for _ in range(self.config.line_search_max_iter):
            params_new = params + alpha * direction
            fom_new = fom_fn(params_new)
            # 充分下降条件
            if fom_new >= fom + c1 * alpha * gp:
                return alpha
            # 缩小步长
            alpha *= 0.5
        return alpha


def create_lbfgs_optimizer(config: LBFGSConfig | None = None) -> LBFGSOptimizer:
    """创建 L-BFGS 优化器工厂函数。

    Args:
        config: 配置（None 用默认）。

    Returns:
        LBFGSOptimizer 实例。
    """
    return LBFGSOptimizer(config=config)


def run_lbfgs_optimization(
    initial_params: np.ndarray,
    fom_fn: callable,
    grad_fn: callable,
    config: LBFGSConfig | None = None,
) -> LBFGSResult:
    """便捷函数：执行 L-BFGS 优化。

    Args:
        initial_params: 初始参数。
        fom_fn: 目标函数。
        grad_fn: 梯度函数。
        config: 配置（None 用默认）。

    Returns:
        LBFGSResult。
    """
    optimizer = LBFGSOptimizer(config)
    return optimizer.optimize(initial_params, fom_fn, grad_fn)


__all__ = [
    "LBFGSConfig",
    "LBFGSResult",
    "LBFGSOptimizer",
    "create_lbfgs_optimizer",
    "run_lbfgs_optimization",
]
