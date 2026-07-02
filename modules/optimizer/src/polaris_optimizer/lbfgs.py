"""L-BFGS 拟牛顿优化器（两循环递归 + Wolfe 线搜索）。

从 v4 ``polaris/sim/lbfgs_optimizer.py`` 迁移（R13 不保留 v4 兼容）。
实现 L-BFGS（Limited-memory BFGS）拟牛顿优化器，对标 lumopt/scipy L-BFGS。
用于 adjoint 逆向设计的二阶优化，收敛速度快于 Adam。

## L-BFGS 算法原理

L-BFGS 是 BFGS 的内存受限版本，只保存最近 m 次 (s, y) 对:
- s_k = x_{k+1} - x_k（参数差）
- y_k = ∇f_{k+1} - ∇f_k（梯度差）

两循环递归计算搜索方向 p = H · g（逆 Hessian 近似 H，最大化 FoM）。

来源（R02 学术诚信，≥5 文献 URL）:
- Liu & Nocedal 1989 "On the limited memory BFGS method for large scale
  optimization" https://doi.org/10.1007/BF01589116
- Nocedal & Wright 2006 Numerical Optimization Springer:
  https://doi.org/10.1007/978-0-387-40065-5
- scipy L-BFGS-B: https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html
- lumopt: https://github.com/chriskeraly/lumopt
- Lu & Vuckovic 2013 Nanophotonic computational design:
  https://doi.org/10.1364/OE.21.013351
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np


@dataclass
class _PointState:
    """当前点的函数值与梯度（降低 _line_search 参数个数）。"""

    fom: float
    grad: np.ndarray


@dataclass(frozen=True)
class LBFGSConfig:
    """L-BFGS 配置。

    Attributes:
        max_iterations: 最大迭代次数（来源: lumopt 默认 100）。
        memory_size: 历史记忆长度 m（来源: Nocedal 推荐 3-20，典型 10）。
        convergence_threshold: 收敛阈值（梯度范数 < 阈值则停止）。
        wolfe_c1: Wolfe 条件 c1（充分下降，来源: Nocedal 推荐 1e-4）。
        wolfe_c2: Wolfe 条件 c2（曲率条件，来源: Nocedal 推荐 0.9）。
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
    """L-BFGS 迭代状态。"""

    params: np.ndarray
    fom: float
    grad: np.ndarray


class LBFGSOptimizer:
    """L-BFGS 优化器（对标 lumopt/scipy L-BFGS）。

    两循环递归近似逆 Hessian，线搜索满足 Wolfe 条件，最大化 FoM。

    算法流程::
        1. 初始化参数 x, 梯度 g
        2. for k in range(max_iterations):
             a. 两循环递归计算搜索方向 p = H · g
             b. 线搜索满足 Wolfe 条件的步长 α
             c. 更新 x = x + α · p
             d. 计算新梯度 g_new
             e. 更新 (s, y) 历史
             f. 检查收敛 (||g|| < threshold)
        3. 返回最优参数
    """

    def __init__(self, config: LBFGSConfig | None = None) -> None:
        self.config = config or LBFGSConfig()
        self._s_history: deque = deque(maxlen=self.config.memory_size)
        self._y_history: deque = deque(maxlen=self.config.memory_size)
        self._rho_history: deque = deque(maxlen=self.config.memory_size)

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        grad_fn: Callable[[np.ndarray], np.ndarray],
    ) -> LBFGSResult:
        params, fom, grad, fom_hist, param_hist, grad_norm_hist = (
            self._init_state(initial_params, fom_fn, grad_fn)
        )
        state = _LBFGSIterState(params=params, fom=fom, grad=grad)
        converged = False
        iterations = 0

        for k in range(self.config.max_iterations):
            iterations = k + 1
            state, grad_norm = self._iterate(state, fom_fn, grad_fn)
            fom_hist.append(state.fom)
            param_hist.append(state.params.copy())
            grad_norm_hist.append(grad_norm)
            if grad_norm < self.config.convergence_threshold:
                converged = True
                break

        return LBFGSResult(
            optimal_params=state.params,
            optimal_fom=state.fom,
            fom_history=fom_hist,
            param_history=param_hist,
            gradient_norm_history=grad_norm_hist,
            iterations=iterations,
            converged=converged,
        )

    def _init_state(
        self,
        initial_params: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        grad_fn: Callable[[np.ndarray], np.ndarray],
    ) -> tuple:
        params = np.asarray(initial_params, dtype=np.float64).copy()
        fom = fom_fn(params)
        grad = grad_fn(params)
        fom_hist = [fom]
        param_hist = [params.copy()]
        grad_norm_hist = [float(np.linalg.norm(grad))]
        return params, fom, grad, fom_hist, param_hist, grad_norm_hist

    def _iterate(
        self,
        state: _LBFGSIterState,
        fom_fn: Callable[[np.ndarray], float],
        grad_fn: Callable[[np.ndarray], np.ndarray],
    ) -> tuple[_LBFGSIterState, float]:
        direction = self._compute_direction(state.grad)
        point = _PointState(fom=state.fom, grad=state.grad)
        alpha = self._line_search(state.params, direction, point, fom_fn)
        params_new = state.params + alpha * direction
        fom_new = fom_fn(params_new)
        grad_new = grad_fn(params_new)
        s = params_new - state.params
        y = grad_new - state.grad
        self._update_history(s, y)
        grad_norm = float(np.linalg.norm(grad_new))
        return _LBFGSIterState(params=params_new, fom=fom_new, grad=grad_new), grad_norm

    def _compute_direction(self, grad: np.ndarray) -> np.ndarray:
        """两循环递归计算搜索方向 p = H · g（最大化 FoM 上升方向）。"""
        q = grad.copy()
        alphas: list[float] = []
        for s, y, rho in zip(
            reversed(self._s_history),
            reversed(self._y_history),
            reversed(self._rho_history),
            strict=True,
        ):
            alpha = rho * float(np.dot(s, q))
            alphas.append(alpha)
            q = q - alpha * y
        gamma = self._compute_gamma()
        r = gamma * q
        for s, y, rho, alpha in zip(
            self._s_history,
            self._y_history,
            self._rho_history,
            reversed(alphas),
            strict=True,
        ):
            beta = rho * float(np.dot(y, r))
            r = r + s * (alpha - beta)
        return r

    def _compute_gamma(self) -> float:
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
        ys = float(np.dot(y, s))
        if abs(ys) < 1e-10:
            return
        self._s_history.append(s.copy())
        self._y_history.append(y.copy())
        self._rho_history.append(1.0 / ys)

    def _line_search(
        self,
        params: np.ndarray,
        direction: np.ndarray,
        state: _PointState,
        fom_fn: Callable[[np.ndarray], float],
    ) -> float:
        """Wolfe 条件线搜索（最大化 FoM: 充分上升 + 曲率条件）。"""
        alpha = self.config.line_search_init
        c1 = self.config.wolfe_c1
        gp = float(np.dot(state.grad, direction))
        for _ in range(self.config.line_search_max_iter):
            fom_new = fom_fn(params + alpha * direction)
            if fom_new >= state.fom + c1 * alpha * gp:
                return alpha
            alpha *= 0.5
        return alpha


def create_lbfgs_optimizer(config: LBFGSConfig | None = None) -> LBFGSOptimizer:
    return LBFGSOptimizer(config=config)


def run_lbfgs_optimization(
    initial_params: np.ndarray,
    fom_fn: Callable[[np.ndarray], float],
    grad_fn: Callable[[np.ndarray], np.ndarray],
    config: LBFGSConfig | None = None,
) -> LBFGSResult:
    optimizer = LBFGSOptimizer(config)
    return optimizer.optimize(initial_params, fom_fn, grad_fn)


__all__ = [
    "LBFGSConfig",
    "LBFGSResult",
    "LBFGSOptimizer",
    "create_lbfgs_optimizer",
    "run_lbfgs_optimization",
]
