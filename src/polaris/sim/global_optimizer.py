"""全局优化器（第40轮 P2-1 深化，CMA-ES / 粒子群）。

实现全局优化算法用于逆向设计参数优化，对标 scipy.optimize.differential_evolution
和 cma.CMAEvolutionStrategy。

## 架构

- ``CMAESOptimizer``：CMA-ES 协方差矩阵自适应进化策略
- ``ParticleSwarmOptimizer``：粒子群优化（PSO）
- ``GlobalOptimizer``：统一接口（自动选择算法）

## 商业差距

P2-1 逆向设计深化：
- 商业标杆：scipy.optimize.differential_evolution, cma.CMAEvolutionStrategy
- L-BFGS 是局部优化器，容易陷入局部最优
- 全局优化器可跳出局部最优，找到更好的全局解

## 来源

- CMA-ES: Hansen & Ostermeier 2001,
  https://doi.org/10.1162/106365601750190398
- 粒子群优化: Kennedy & Eberhart 1995,
  https://ieeexplore.ieee.org/document/488968
- scipy.optimize.differential_evolution:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html
- cma package: https://github.com/CMA-ES/pycma
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import numpy as np


class GlobalMethod(Enum):
    """全局优化方法。

    Attributes:
        CMA_ES: CMA-ES 协方差矩阵自适应进化策略。
        PSO: 粒子群优化。
    """

    CMA_ES = "cma_es"
    PSO = "pso"


@dataclass(frozen=True)
class CMAESConfig:
    """CMA-ES 配置。

    Attributes:
        initial_std: 初始步长标准差。
        population_size: 种群大小（0 表示自动 4+3*ln(n)）。
        max_iterations: 最大迭代次数。
        convergence_threshold: 收敛阈值（标准差）。
        seed: 随机种子。
    """

    initial_std: float = 0.5
    population_size: int = 0
    max_iterations: int = 100
    convergence_threshold: float = 1e-6
    seed: int = 42


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


class CMAESOptimizer:
    """CMA-ES 协方差矩阵自适应进化策略。

    自适应进化策略，通过学习目标函数的协方差矩阵来引导搜索方向。
    适合非凸、多模态目标函数的全局优化。

    对标 cma.CMAEvolutionStrategy 与 scipy.optimize.differential_evolution。

    来源:
        Hansen & Ostermeier 2001,
        https://doi.org/10.1162/106365601750190398
    """

    def __init__(self, config: CMAESConfig | None = None) -> None:
        """初始化 CMA-ES 优化器。

        Args:
            config: CMA-ES 配置。
        """
        self.config = config or CMAESConfig()

    def optimize(
        self,
        initial_mean: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
    ) -> GlobalResult:
        """执行 CMA-ES 优化。

        Args:
            initial_mean: 初始均值（参数向量）。
            fom_fn: FoM 评估函数（最大化）。

        Returns:
            全局优化结果。
        """
        n = len(initial_mean)
        rng = np.random.default_rng(self.config.seed)
        lambda_ = (
            self.config.population_size
            if self.config.population_size > 0
            else int(4 + 3 * np.log(n))
        )
        mu = lambda_ // 2
        weights = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
        weights = weights / weights.sum()
        mueff = 1.0 / float(np.sum(weights ** 2))

        mean = initial_mean.copy()
        sigma = self.config.initial_std
        c_c = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
        c_s = (mueff + 2) / (n + mueff + 5)
        c_1 = 2 / ((n + 1.3) ** 2 + mueff)
        c_mu = min(
            1 - c_1,
            2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff),
        )
        d_s = 1 + 2 * max(0, np.sqrt((mueff - 1) / (n + 1)) - 1) + c_s
        p_c = np.zeros(n)
        p_s = np.zeros(n)
        b_mat = np.eye(n)
        d_mat = np.eye(n)
        c_mat = b_mat @ d_mat @ b_mat.T
        chi_n = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))

        history: list[float] = []
        best_fom = -float("inf")
        best_params = initial_mean.copy()
        converged = False

        for iteration in range(self.config.max_iterations):
            inv_sqrt_c = b_mat @ np.diag(1.0 / np.diag(d_mat)) @ b_mat.T
            samples = self._sample_population(
                mean, sigma, b_mat, d_mat, lambda_, rng
            )
            foms = np.array([fom_fn(s) for s in samples])
            sorted_idx = np.argsort(-foms)
            selected = samples[sorted_idx[:mu]]
            selected_weights = weights
            new_mean = np.sum(
                selected * selected_weights[:, np.newaxis], axis=0
            )
            y_w = (new_mean - mean) / sigma
            p_s = (1 - c_s) * p_s + np.sqrt(
                c_s * (2 - c_s) * mueff
            ) * inv_sqrt_c @ y_w
            h_sig = (
                float(np.linalg.norm(p_s))
                / np.sqrt(1 - (1 - c_s) ** (2 * (iteration + 1)))
                < (1.4 + 2 / (n + 1)) * chi_n
            )
            p_c = (1 - c_c) * p_c + h_sig * np.sqrt(
                c_c * (2 - c_c) * mueff
            ) * y_w
            delta_h = (1 - h_sig) * c_c * (2 - c_c)
            c_mat = (1 - c_1 - c_mu) * c_mat + c_1 * (
                np.outer(p_c, p_c) + delta_h * c_mat
            )
            for i in range(mu):
                yi = (selected[i] - mean) / sigma
                c_mat += c_mu * selected_weights[i] * np.outer(yi, yi)
            c_mat = (c_mat + c_mat.T) / 2
            eigvals, eigvecs = np.linalg.eigh(c_mat)
            eigvals = np.maximum(eigvals, 1e-20)
            b_mat = eigvecs
            d_mat = np.diag(np.sqrt(eigvals))
            sigma = sigma * np.exp(
                (c_s / d_s) * (np.linalg.norm(p_s) / chi_n - 1)
            )
            sigma = min(sigma, 1e10)
            mean = new_mean
            if foms[sorted_idx[0]] > best_fom:
                best_fom = foms[sorted_idx[0]]
                best_params = samples[sorted_idx[0]].copy()
            history.append(best_fom)
            if sigma < self.config.convergence_threshold:
                converged = True
                break

        return GlobalResult(
            optimal_params=best_params,
            optimal_fom=best_fom,
            fom_history=history,
            iterations=len(history),
            converged=converged,
            method="CMA-ES",
        )

    def _sample_population(
        self,
        mean: np.ndarray,
        sigma: float,
        b_mat: np.ndarray,
        d_mat: np.ndarray,
        lambda_: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """采样种群。"""
        n = len(mean)
        z = rng.standard_normal((lambda_, n))
        y = z @ d_mat @ b_mat.T
        return mean + sigma * y


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
        n = len(initial_pos)
        rng = np.random.default_rng(self.config.seed)
        w = self.config.inertia_weight
        c1 = self.config.cognitive_coef
        c2 = self.config.social_coef
        if bounds is None:
            lower = initial_pos - 5.0
            upper = initial_pos + 5.0
        else:
            lower, upper = bounds
        positions = np.zeros((self.config.num_particles, n))
        positions[0] = initial_pos
        for i in range(1, self.config.num_particles):
            positions[i] = rng.uniform(lower, upper)
        velocities = rng.uniform(
            -np.abs(upper - lower),
            np.abs(upper - lower),
            (self.config.num_particles, n),
        )
        personal_best = positions.copy()
        personal_best_fom = np.array(
            [fom_fn(p) for p in positions]
        )
        global_best_idx = int(np.argmax(personal_best_fom))
        global_best = personal_best[global_best_idx].copy()
        global_best_fom = personal_best_fom[global_best_idx]
        history: list[float] = [global_best_fom]
        converged = False

        for _iteration in range(self.config.max_iterations):
            r1 = rng.uniform(0, 1, (self.config.num_particles, n))
            r2 = rng.uniform(0, 1, (self.config.num_particles, n))
            velocities = (
                w * velocities
                + c1 * r1 * (personal_best - positions)
                + c2 * r2 * (global_best - positions)
            )
            positions = positions + velocities
            positions = np.clip(positions, lower, upper)
            foms = np.array([fom_fn(p) for p in positions])
            improved = foms > personal_best_fom
            personal_best[improved] = positions[improved]
            personal_best_fom[improved] = foms[improved]
            current_best_idx = int(np.argmax(personal_best_fom))
            if personal_best_fom[current_best_idx] > global_best_fom:
                global_best = personal_best[current_best_idx].copy()
                global_best_fom = personal_best_fom[current_best_idx]
            history.append(global_best_fom)
            if len(history) > 1:
                improvement = abs(history[-1] - history[-2])
                if improvement < self.config.convergence_threshold:
                    converged = True
                    break

        return GlobalResult(
            optimal_params=global_best,
            optimal_fom=global_best_fom,
            fom_history=history,
            iterations=len(history),
            converged=converged,
            method="PSO",
        )


class GlobalOptimizer:
    """统一全局优化器接口。

    根据 method 自动选择 CMA-ES 或 PSO。

    对标 scipy.optimize.minimize 统一接口。
    """

    def __init__(
        self,
        method: GlobalMethod = GlobalMethod.CMA_ES,
        cmaes_config: CMAESConfig | None = None,
        pso_config: PSOConfig | None = None,
    ) -> None:
        """初始化全局优化器。

        Args:
            method: 优化方法。
            cmaes_config: CMA-ES 配置。
            pso_config: PSO 配置。
        """
        self.method = method
        self.cmaes_config = cmaes_config or CMAESConfig()
        self.pso_config = pso_config or PSOConfig()

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> GlobalResult:
        """执行全局优化。

        Args:
            initial_params: 初始参数。
            fom_fn: FoM 评估函数（最大化）。
            bounds: 参数边界（仅 PSO 使用）。

        Returns:
            全局优化结果。
        """
        if self.method == GlobalMethod.CMA_ES:
            opt = CMAESOptimizer(self.cmaes_config)
            return opt.optimize(initial_params, fom_fn)
        opt = ParticleSwarmOptimizer(self.pso_config)
        return opt.optimize(initial_params, fom_fn, bounds)


def create_cmaes_optimizer(
    config: CMAESConfig | None = None,
) -> CMAESOptimizer:
    """工厂函数：创建 CMA-ES 优化器。"""
    return CMAESOptimizer(config)


def create_pso_optimizer(
    config: PSOConfig | None = None,
) -> ParticleSwarmOptimizer:
    """工厂函数：创建 PSO 优化器。"""
    return ParticleSwarmOptimizer(config)


def create_global_optimizer(
    method: GlobalMethod = GlobalMethod.CMA_ES,
    cmaes_config: CMAESConfig | None = None,
    pso_config: PSOConfig | None = None,
) -> GlobalOptimizer:
    """工厂函数：创建统一全局优化器。"""
    return GlobalOptimizer(method, cmaes_config, pso_config)


def run_global_optimization(
    initial_params: np.ndarray,
    fom_fn: Callable[[np.ndarray], float],
    method: GlobalMethod = GlobalMethod.CMA_ES,
    bounds: tuple[np.ndarray, np.ndarray] | None = None,
) -> GlobalResult:
    """工厂函数：运行全局优化。

    Args:
        initial_params: 初始参数。
        fom_fn: FoM 评估函数（最大化）。
        method: 优化方法。
        bounds: 参数边界（仅 PSO 使用）。

    Returns:
        全局优化结果。
    """
    opt = create_global_optimizer(method)
    return opt.optimize(initial_params, fom_fn, bounds)
