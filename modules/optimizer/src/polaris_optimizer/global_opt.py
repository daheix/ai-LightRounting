"""全局优化器（PSO 粒子群 + CMA-ES 协方差矩阵自适应进化策略）。

从 v4 ``polaris/sim/pso_optimizer.py`` 与 ``global_optimizer.py`` 合并迁移
（R13 不保留 v4 兼容）。对标 scipy.optimize.differential_evolution 与
cma.CMAEvolutionStrategy，用于逆向设计参数全局优化，跳出 L-BFGS 局部最优。

来源（R02 学术诚信，≥5 文献 URL）:
- Kennedy & Eberhart 1995 "Particle Swarm Optimization",
  IEEE ICNN, https://ieeexplore.ieee.org/document/488968
- Hansen & Ostermeier 2001 "Completely Derandomized Self-Adaptation in
  Evolutionary Strategies", Evol. Comput. 9(2):159-195,
  https://doi.org/10.1162/106365601750190398
- scipy.optimize.differential_evolution:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html
- cma package: https://github.com/CMA-ES/pycma
- Nocedal & Wright 2006 Numerical Optimization Springer:
  https://doi.org/10.1007/978-0-387-40065-5
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

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
    """PSO 迭代状态。"""

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
    """粒子群优化器（PSO，Kennedy & Eberhart 1995）。

    通过群体智能搜索全局最优解，每个粒子根据自身历史最优和群体历史最优
    更新速度和位置。对标 scipy.optimize.differential_evolution。
    """

    def __init__(self, config: PSOConfig | None = None) -> None:
        self.config = config or PSOConfig()

    def optimize(
        self,
        initial_pos: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> GlobalResult:
        state = self._init_state(initial_pos, fom_fn, bounds)
        history: list[float] = [state.global_best_fom]
        converged = False

        for _ in range(self.config.max_iterations):
            state = self._iterate(state, fom_fn)
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

    def _init_state(
        self,
        initial_pos: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None,
    ) -> _PSOState:
        rng = np.random.default_rng(self.config.seed)
        lower, upper = self._init_bounds(initial_pos, bounds)
        positions, velocities = self._init_particles(initial_pos, lower, upper, rng)
        personal_best = positions.copy()
        personal_best_fom = np.array([fom_fn(p) for p in positions])
        best_idx = int(np.argmax(personal_best_fom))
        return _PSOState(
            positions=positions,
            velocities=velocities,
            personal_best=personal_best,
            personal_best_fom=personal_best_fom,
            global_best=personal_best[best_idx].copy(),
            global_best_fom=float(personal_best_fom[best_idx]),
            lower=lower,
            upper=upper,
            rng=rng,
        )

    def _init_bounds(
        self,
        initial_pos: np.ndarray,
        bounds: tuple[np.ndarray, np.ndarray] | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if bounds is None:
            return initial_pos - 5.0, initial_pos + 5.0
        return bounds

    def _init_particles(
        self,
        initial_pos: np.ndarray,
        lower: np.ndarray,
        upper: np.ndarray,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, np.ndarray]:
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

    def _iterate(
        self, state: _PSOState, fom_fn: Callable[[np.ndarray], float]
    ) -> _PSOState:
        velocities = self._compute_velocities(state)
        positions = state.positions + velocities
        positions = np.clip(positions, state.lower, state.upper)
        foms = np.array([fom_fn(p) for p in positions])
        personal_best, personal_best_fom, global_best, global_best_fom = (
            self._update_bests(state, positions, foms)
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

    def _compute_velocities(self, state: _PSOState) -> np.ndarray:
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

    def _update_bests(
        self,
        state: _PSOState,
        positions: np.ndarray,
        foms: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        improved = foms > state.personal_best_fom
        personal_best = state.personal_best.copy()
        personal_best_fom = state.personal_best_fom.copy()
        personal_best[improved] = positions[improved]
        personal_best_fom[improved] = foms[improved]
        best_idx = int(np.argmax(personal_best_fom))
        global_best = state.global_best
        global_best_fom = state.global_best_fom
        if personal_best_fom[best_idx] > global_best_fom:
            global_best = personal_best[best_idx].copy()
            global_best_fom = personal_best_fom[best_idx]
        return personal_best, personal_best_fom, global_best, float(global_best_fom)


@dataclass(frozen=True)
class CMAESConfig:
    """CMA-ES 配置。

    Attributes:
        initial_std: 初始步长标准差。
        population_size: 种群大小（0 表示自动 4+3·ln(n)）。
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
class _CMAESConstants:
    c_c: float
    c_s: float
    c_1: float
    c_mu: float
    d_s: float
    chi_n: float


@dataclass
class _CMAESState:
    n: int
    rng: np.random.Generator
    lambda_: int
    mu: int
    weights: np.ndarray
    mueff: float
    mean: np.ndarray
    sigma: float
    c_c: float
    c_s: float
    c_1: float
    c_mu: float
    d_s: float
    p_c: np.ndarray
    p_s: np.ndarray
    b_mat: np.ndarray
    d_mat: np.ndarray
    c_mat: np.ndarray
    chi_n: float
    history: list[float]
    best_fom: float
    best_params: np.ndarray
    converged: bool


class CMAESOptimizer:
    """CMA-ES 协方差矩阵自适应进化策略（Hansen & Ostermeier 2001）。

    自适应进化策略，通过学习目标函数的协方差矩阵来引导搜索方向。
    适合非凸、多模态目标函数的全局优化。对标 cma.CMAEvolutionStrategy。
    """

    def __init__(self, config: CMAESConfig | None = None) -> None:
        self.config = config or CMAESConfig()

    def optimize(
        self,
        initial_mean: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
    ) -> GlobalResult:
        state = self._init_state(initial_mean)
        for iteration in range(self.config.max_iterations):
            done = self._step(iteration, state, fom_fn)
            if done:
                break
        return GlobalResult(
            optimal_params=state.best_params,
            optimal_fom=state.best_fom,
            fom_history=state.history,
            iterations=len(state.history),
            converged=state.converged,
            method="CMA-ES",
        )

    def _compute_constants(self, n: int, mueff: float) -> _CMAESConstants:
        c_c = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
        c_s = (mueff + 2) / (n + mueff + 5)
        c_1 = 2 / ((n + 1.3) ** 2 + mueff)
        c_mu = min(1 - c_1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff))
        d_s = 1 + 2 * max(0, np.sqrt((mueff - 1) / (n + 1)) - 1) + c_s
        chi_n = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n**2))
        return _CMAESConstants(c_c=c_c, c_s=c_s, c_1=c_1, c_mu=c_mu, d_s=d_s, chi_n=chi_n)

    def _init_state(self, initial_mean: np.ndarray) -> _CMAESState:
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
        mueff = 1.0 / float(np.sum(weights**2))
        consts = self._compute_constants(n, mueff)
        return _CMAESState(
            n=n, rng=rng, lambda_=lambda_, mu=mu, weights=weights, mueff=mueff,
            mean=initial_mean.copy(), sigma=self.config.initial_std,
            c_c=consts.c_c, c_s=consts.c_s, c_1=consts.c_1, c_mu=consts.c_mu,
            d_s=consts.d_s, p_c=np.zeros(n), p_s=np.zeros(n),
            b_mat=np.eye(n), d_mat=np.eye(n), c_mat=np.eye(n),
            chi_n=consts.chi_n, history=[], best_fom=-float("inf"),
            best_params=initial_mean.copy(), converged=False,
        )

    def _step(
        self, iteration: int, s: _CMAESState, fom_fn: Callable[[np.ndarray], float]
    ) -> bool:
        inv_sqrt_c = s.b_mat @ np.diag(1.0 / np.diag(s.d_mat)) @ s.b_mat.T
        samples = self._sample_population(s)
        foms = np.array([fom_fn(sample) for sample in samples])
        sorted_idx = np.argsort(-foms)
        selected = samples[sorted_idx[: s.mu]]
        new_mean = np.sum(selected * s.weights[:, np.newaxis], axis=0)
        y_w = (new_mean - s.mean) / s.sigma
        s.p_s = (1 - s.c_s) * s.p_s + np.sqrt(s.c_s * (2 - s.c_s) * s.mueff) * inv_sqrt_c @ y_w
        h_sig = (
            float(np.linalg.norm(s.p_s)) / np.sqrt(1 - (1 - s.c_s) ** (2 * (iteration + 1)))
            < (1.4 + 2 / (s.n + 1)) * s.chi_n
        )
        s.p_c = (1 - s.c_c) * s.p_c + h_sig * np.sqrt(s.c_c * (2 - s.c_c) * s.mueff) * y_w
        delta_h = (1 - h_sig) * s.c_c * (2 - s.c_c)
        s.c_mat = (1 - s.c_1 - s.c_mu) * s.c_mat + s.c_1 * (
            np.outer(s.p_c, s.p_c) + delta_h * s.c_mat
        )
        for i in range(s.mu):
            yi = (selected[i] - s.mean) / s.sigma
            s.c_mat += s.c_mu * s.weights[i] * np.outer(yi, yi)
        s.c_mat = (s.c_mat + s.c_mat.T) / 2
        eigvals, eigvecs = np.linalg.eigh(s.c_mat)
        eigvals = np.maximum(eigvals, 1e-20)
        s.b_mat = eigvecs
        s.d_mat = np.diag(np.sqrt(eigvals))
        s.sigma = s.sigma * np.exp((s.c_s / s.d_s) * (np.linalg.norm(s.p_s) / s.chi_n - 1))
        s.sigma = min(s.sigma, 1e10)
        s.mean = new_mean
        if foms[sorted_idx[0]] > s.best_fom:
            s.best_fom = foms[sorted_idx[0]]
            s.best_params = samples[sorted_idx[0]].copy()
        s.history.append(s.best_fom)
        if s.sigma < self.config.convergence_threshold:
            s.converged = True
            return True
        return False

    def _sample_population(self, s: _CMAESState) -> np.ndarray:
        n = len(s.mean)
        z = s.rng.standard_normal((s.lambda_, n))
        y = z @ s.d_mat @ s.b_mat.T
        return s.mean + s.sigma * y


class GlobalMethod(Enum):
    """全局优化方法。

    Attributes:
        CMA_ES: CMA-ES 协方差矩阵自适应进化策略。
        PSO: 粒子群优化。
    """

    CMA_ES = "cma_es"
    PSO = "pso"


class GlobalOptimizer:
    """统一全局优化器接口（按 method 自动选择 CMA-ES 或 PSO）。

    对标 scipy.optimize.minimize 统一接口。
    """

    def __init__(
        self,
        method: GlobalMethod = GlobalMethod.CMA_ES,
        cmaes_config: CMAESConfig | None = None,
        pso_config: PSOConfig | None = None,
    ) -> None:
        self.method = method
        self.cmaes_config = cmaes_config or CMAESConfig()
        self.pso_config = pso_config or PSOConfig()

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        bounds: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> GlobalResult:
        if self.method == GlobalMethod.CMA_ES:
            return CMAESOptimizer(self.cmaes_config).optimize(initial_params, fom_fn)
        return ParticleSwarmOptimizer(self.pso_config).optimize(initial_params, fom_fn, bounds)


def create_pso_optimizer(config: PSOConfig | None = None) -> ParticleSwarmOptimizer:
    return ParticleSwarmOptimizer(config)


def create_cmaes_optimizer(config: CMAESConfig | None = None) -> CMAESOptimizer:
    return CMAESOptimizer(config)


def create_global_optimizer(
    method: GlobalMethod = GlobalMethod.CMA_ES,
    cmaes_config: CMAESConfig | None = None,
    pso_config: PSOConfig | None = None,
) -> GlobalOptimizer:
    return GlobalOptimizer(method, cmaes_config, pso_config)


def run_global_optimization(
    initial_params: np.ndarray,
    fom_fn: Callable[[np.ndarray], float],
    method: GlobalMethod = GlobalMethod.CMA_ES,
    bounds: tuple[np.ndarray, np.ndarray] | None = None,
) -> GlobalResult:
    opt = create_global_optimizer(method)
    return opt.optimize(initial_params, fom_fn, bounds)


__all__ = [
    "GlobalResult",
    "PSOConfig",
    "ParticleSwarmOptimizer",
    "CMAESConfig",
    "CMAESOptimizer",
    "GlobalMethod",
    "GlobalOptimizer",
    "create_pso_optimizer",
    "create_cmaes_optimizer",
    "create_global_optimizer",
    "run_global_optimization",
]
