"""粒子群优化器（PSO）—— 从 global_optimizer.py 拆分（第62轮 P2-1）。

通过群体智能搜索全局最优解，每个粒子根据自身历史最优和群体历史最优
更新速度和位置。

对标 scipy.optimize.differential_evolution 与商业 PSO 实现。

## 来源

- 粒子群优化: Kennedy & Eberhart 1995,
  https://ieeexplore.ieee.org/document/488968
- scipy.optimize.differential_evolution:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html


## 补充文献（R02 学术诚信补齐）
- Nocedal & Wright 2006 Numerical Optimization Springer: https://doi.org/10.1007/978-0-387-40065-5
- scipy.optimize 文档: https://docs.scipy.org/doc/scipy/reference/optimize.html
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np


@dataclass
class GlobalResult:
    """全局优化结果。

    Attributes:
        optimal_params: 最优参数。
        optimal_fom: 最优 FoM。
        fom_history: 每轮迭代的最优 FoM 历史。
        iterations: 实际迭代次数。
        converged: 是否收敛。
        method: 使用的优化方法。
    """

    optimal_params: np.ndarray
    optimal_fom: float = -float("inf")
    fom_history: list[float] = field(default_factory=list)
    iterations: int = 0
    converged: bool = False
    method: str = ""


@dataclass(frozen=True)
class PSOConfig:
    """粒子群优化配置。

    Attributes:
        num_particles: 粒子数量。
        inertia_weight: 惯性权重 w。
        cognitive_coef: 认知系数 c1（自我学习）。
        social_coef: 社会系数 c2（群体学习）。
        max_iterations: 最大迭代次数。
        convergence_threshold: 收敛阈值。
        seed: 随机种子。
    """

    num_particles: int = 30
    inertia_weight: float = 0.7
    cognitive_coef: float = 1.5
    social_coef: float = 1.5
    max_iterations: int = 100
    convergence_threshold: float = 1e-6
    seed: int = 42


@dataclass
class _PSOState:
    """PSO 迭代状态（降低 _pso_iteration 参数个数，规则 4.1）。

    Attributes:
        positions: 当前粒子位置。
        velocities: 当前粒子速度。
        personal_best: 个体最佳位置。
        personal_best_fom: 个体最佳 FoM。
        global_best: 全局最佳位置。
        global_best_fom: 全局最佳 FoM。
        lower: 下界。
        upper: 上界。
        rng: 随机数生成器。
    """

    positions: np.ndarray
    velocities: np.ndarray
    personal_best: np.ndarray
    personal_best_fom: np.ndarray
    global_best: np.ndarray
    global_best_fom: float
    lower: np.ndarray
    upper: np.ndarray
    rng: np.random.Generator


class ParticleSwarmOptimizer:
    """粒子群优化器（PSO）。

    通过群体智能搜索全局最优解，每个粒子根据自身历史最优和群体历史最优
    更新速度和位置。

    对标 scipy.optimize.differential_evolution 与商业 PSO 实现。

    来源:
        Kennedy & Eberhart 1995,
        https://ieeexplore.ieee.org/document/488968
    """

    def __init__(self, config: PSOConfig | None = None) -> None:
        """初始化 PSO 优化器。

        Args:
            config: PSO 配置。
        """
        self.config = config or PSOConfig()

    def _init_pso_bounds(
        self,
        initial_pos: np.ndarray,
        bounds: tuple[np.ndarray, np.ndarray] | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """初始化 PSO 参数边界。

        Args:
            initial_pos: 初始位置。
            bounds: 参数边界，None 表示自动。

        Returns:
            (lower, upper) 上下界。
        """
        if bounds is None:
            return initial_pos - 5.0, initial_pos + 5.0
        return bounds

    def _init_pso_particles(
        self,
        initial_pos: np.ndarray,
        lower: np.ndarray,
        upper: np.ndarray,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, np.ndarray]:
        """初始化 PSO 粒子位置和速度。

        Args:
            initial_pos: 初始位置（第一个粒子）。
            lower: 下界。
            upper: 上界。
            rng: 随机数生成器。

        Returns:
            (positions, velocities) 粒子位置和速度。
        """
        n = len(initial_pos)
        positions = np.zeros((self.config.num_particles, n))
        positions[0] = initial_pos
        for i in range(1, self.config.num_particles):
            positions[i] = rng.uniform(lower, upper)
        velocities = rng.uniform(
            -np.abs(upper - lower),
            np.abs(upper - lower),
            (self.config.num_particles, n),
        )
        return positions, velocities

    def _init_pso_state(
        self,
        initial_pos: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None,
    ) -> _PSOState:
        """初始化 PSO 状态。

        Args:
            initial_pos: 初始位置。
            fom_fn: FoM 评估函数。
            bounds: 参数边界。

        Returns:
            PSO 迭代状态对象。
        """
        rng = np.random.default_rng(self.config.seed)
        lower, upper = self._init_pso_bounds(initial_pos, bounds)
        positions, velocities = self._init_pso_particles(initial_pos, lower, upper, rng)
        personal_best = positions.copy()
        personal_best_fom = np.array([fom_fn(p) for p in positions])
        global_best_idx = int(np.argmax(personal_best_fom))
        global_best = personal_best[global_best_idx].copy()
        global_best_fom = personal_best_fom[global_best_idx]
        return _PSOState(
            positions=positions,
            velocities=velocities,
            personal_best=personal_best,
            personal_best_fom=personal_best_fom,
            global_best=global_best,
            global_best_fom=float(global_best_fom),
            lower=lower,
            upper=upper,
            rng=rng,
        )

    def _compute_pso_velocities(self, state: _PSOState) -> np.ndarray:
        """计算 PSO 粒子新速度。

        Args:
            state: PSO 迭代状态。

        Returns:
            新速度数组。
        """
        w = self.config.inertia_weight
        c1 = self.config.cognitive_coef
        c2 = self.config.social_coef
        n_particles = self.config.num_particles
        n = state.positions.shape[1]
        r1 = state.rng.uniform(0, 1, (n_particles, n))
        r2 = state.rng.uniform(0, 1, (n_particles, n))
        return (
            w * state.velocities
            + c1 * r1 * (state.personal_best - state.positions)
            + c2 * r2 * (state.global_best - state.positions)
        )

    def _update_pso_bests(
        self,
        state: _PSOState,
        positions: np.ndarray,
        foms: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """更新 PSO 个体最佳和全局最佳。

        Args:
            state: PSO 迭代状态。
            positions: 新粒子位置。
            foms: 新粒子 FoM。

        Returns:
            (personal_best, personal_best_fom, global_best, global_best_fom)。
        """
        improved = foms > state.personal_best_fom
        personal_best = state.personal_best.copy()
        personal_best_fom = state.personal_best_fom.copy()
        personal_best[improved] = positions[improved]
        personal_best_fom[improved] = foms[improved]
        current_best_idx = int(np.argmax(personal_best_fom))
        global_best = state.global_best
        global_best_fom = state.global_best_fom
        if personal_best_fom[current_best_idx] > global_best_fom:
            global_best = personal_best[current_best_idx].copy()
            global_best_fom = personal_best_fom[current_best_idx]
        return personal_best, personal_best_fom, global_best, float(global_best_fom)

    def _pso_iteration(
        self,
        state: _PSOState,
        fom_fn: Callable[[np.ndarray], float],
    ) -> _PSOState:
        """执行一次 PSO 迭代。

        Args:
            state: PSO 迭代状态。
            fom_fn: FoM 评估函数。

        Returns:
            更新后的 PSO 状态对象。
        """
        velocities = self._compute_pso_velocities(state)
        positions = state.positions + velocities
        positions = np.clip(positions, state.lower, state.upper)
        foms = np.array([fom_fn(p) for p in positions])
        personal_best, personal_best_fom, global_best, global_best_fom = (
            self._update_pso_bests(state, positions, foms)
        )
        return _PSOState(
            positions=positions,
            velocities=velocities,
            personal_best=personal_best,
            personal_best_fom=personal_best_fom,
            global_best=global_best,
            global_best_fom=global_best_fom,
            lower=state.lower,
            upper=state.upper,
            rng=state.rng,
        )

    def optimize(
        self,
        initial_pos: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> GlobalResult:
        """执行 PSO 优化。

        Args:
            initial_pos: 初始位置（单个粒子，其他粒子随机生成）。
            fom_fn: FoM 评估函数（最大化）。
            bounds: 参数边界 (lower, upper)，None 表示无边界。

        Returns:
            全局优化结果。
        """
        state = self._init_pso_state(initial_pos, fom_fn, bounds)
        history: list[float] = [state.global_best_fom]
        converged = False

        for _iteration in range(self.config.max_iterations):
            state = self._pso_iteration(state, fom_fn)
            history.append(state.global_best_fom)
            if len(history) > 1:
                improvement = abs(history[-1] - history[-2])
                if improvement < self.config.convergence_threshold:
                    converged = True
                    break

        return GlobalResult(
            optimal_params=state.global_best,
            optimal_fom=state.global_best_fom,
            fom_history=history,
            iterations=len(history),
            converged=converged,
            method="PSO",
        )


def create_pso_optimizer(
    config: PSOConfig | None = None,
) -> ParticleSwarmOptimizer:
    """工厂函数：创建 PSO 优化器。"""
    return ParticleSwarmOptimizer(config)
