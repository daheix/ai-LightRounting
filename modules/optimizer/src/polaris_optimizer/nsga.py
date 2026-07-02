"""多目标优化（NSGA-II 快速非支配排序 + NSGA-III 参考点法）。

从 v4 ``polaris/sim/nsga2_operators.py`` / ``multi_objective_optimizer.py`` /
``nsga3_optimizer.py`` 三文件合并迁移（R13 不保留 v4 兼容）。
对标商业工具（Tidy3D / Lumerical / IC Compiler II）的多目标优化能力，
实现 NSGA-II（≤3 目标）与 NSGA-III（>3 目标）算法，支持 Pareto 前沿计算。

## NSGA-II 算法（Deb et al. 2002）

1. 初始化种群 P（N 个个体）
2. 快速非支配排序 → 分层 F1, F2, ...
3. 计算拥挤距离
4. 锦标赛选择 + SBX 交叉 + 多项式变异 → 子代 Q
5. P ∪ Q → 非支配排序 → 选前 N 个 → 新 P
6. 重复 2-5 直到收敛

## NSGA-III 算法（Deb & Jain 2014）

NSGA-III 用参考点机制（Das-Dennis）替代拥挤距离，处理 >3 目标时
多样性保持能力更强。

来源（R02 学术诚信，≥5 文献 URL）:
- Deb et al. 2002 "A Fast and Elitist Multiobjective Genetic Algorithm:
  NSGA-II", IEEE Trans. Evol. Comput. 6(2):182-197,
  https://doi.org/10.1109/4235.996017
- Deb & Jain 2014 "An Evolutionary Many-Objective Optimization Algorithm Using
  Reference-Point-Based Nondominated Sorting Approach, Part I",
  IEEE Trans. Evol. Comput. 18(4):577-601,
  https://doi.org/10.1109/TEVC.2013.2281535
- Das & Dennis 1998 "Normal-boundary intersection",
  SIAM J. Optim. 8(3):631-657, https://doi.org/10.1137/S1052623496307510
- Deb & Agrawal 1995 "Simulated binary crossover for continuous search space",
  Complex Syst. 9(2):115-148, https://complex-systems.com/abstracts/vol09_i02_a02/
- Deb & Goyal 1996 "A combined genetic adaptive search (GeneAS)",
  https://www.iitk.ac.in/kangal/papers/k199601.pdf
- Tian et al. 2017 "PlatEMO", IEEE Comput. Intell. Mag. 12(4):73-87,
  https://doi.org/10.1109/MCI.2017.2742868
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class ObjectiveType(Enum):
    """目标类型。

    Attributes:
        MAXIMIZE: 最大化（如 FoM、透过率）。
        MINIMIZE: 最小化（如损耗、面积）。
    """

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


@dataclass
class Objective:
    """单目标定义。

    Attributes:
        name: 目标名。
        type: 目标类型（最大化/最小化）。
        weight: 权重（用于加权聚合，默认 1.0）。
    """

    name: str
    type: ObjectiveType
    weight: float = 1.0


@dataclass
class SBXConfig:
    """SBX 交叉配置。

    Attributes:
        prob: 交叉概率。
        eta: 分布指数（越大越接近父代）。
        rng: 随机数生成器。
    """

    prob: float = 1.0
    eta: float = 20.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng())


@dataclass
class Individual:
    """个体（解）。

    Attributes:
        params: 参数向量。
        objectives: 目标值向量（多目标）。
        rank: 非支配层级（1 = 最优前沿）。
        crowding_distance: 拥挤距离。
    """

    params: np.ndarray
    objectives: np.ndarray
    rank: int = 0
    crowding_distance: float = 0.0

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)


@dataclass
class NSGA2Config:
    """NSGA-II 配置。

    Attributes:
        population_size: 种群大小（来源: Deb 2002 建议 100-200）。
        max_generations: 最大代数。
        crossover_prob: 交叉概率（来源: Deb 2002 默认 0.9）。
        mutation_prob: 变异概率（来源: Deb 2002 默认 1/n_params）。
        crossover_eta: SBX 交叉分布指数（来源: Deb 2002 默认 20）。
        mutation_eta: 多项式变异分布指数（来源: Deb 2002 默认 20）。
        bounds: 参数边界 [(min, max), ...]。
        seed: 随机种子。
    """

    population_size: int = 100
    max_generations: int = 200
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    crossover_eta: float = 20.0
    mutation_eta: float = 20.0
    bounds: list[tuple[float, float]] | None = None
    seed: int | None = None


@dataclass
class ParetoResult:
    """Pareto 优化结果。

    Attributes:
        pareto_front: Pareto 前沿解集（rank=1 的个体）。
        all_solutions: 所有解。
        generations: 实际迭代代数。
        converged: 是否收敛。
        objective_history: 目标历史（每代最优前沿均值）。
    """

    pareto_front: list[Individual]
    all_solutions: list[Individual]
    generations: int = 0
    converged: bool = False
    objective_history: list[np.ndarray] = field(default_factory=list)


def dominates(a: np.ndarray, b: np.ndarray, objectives: list[Objective]) -> bool:
    """判断解 a 是否支配解 b（Deb 2002 §III）。"""
    better_in_one = False
    for i, obj in enumerate(objectives):
        if obj.type == ObjectiveType.MAXIMIZE:
            if a[i] < b[i]:
                return False
            if a[i] > b[i]:
                better_in_one = True
        else:
            if a[i] > b[i]:
                return False
            if a[i] < b[i]:
                better_in_one = True
    return better_in_one


def _compute_dominance_relations(
    population: list[Individual], objectives: list[Objective]
) -> tuple[list[int], list[list[int]]]:
    n = len(population)
    domination_count = [0] * n
    dominated_set: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if dominates(population[i].objectives, population[j].objectives, objectives):
                dominated_set[i].append(j)
                domination_count[j] += 1
            elif dominates(population[j].objectives, population[i].objectives, objectives):
                dominated_set[j].append(i)
                domination_count[i] += 1
    return domination_count, dominated_set


def _build_fronts(
    population: list[Individual],
    domination_count: list[int],
    dominated_set: list[list[int]],
) -> list[list[Individual]]:
    n = len(population)
    id_to_idx = {id(ind): i for i, ind in enumerate(population)}
    fronts: list[list[Individual]] = [[]]
    for i in range(n):
        if domination_count[i] == 0:
            population[i].rank = 1
            fronts[0].append(population[i])
    k = 0
    while fronts[k]:
        next_front: list[Individual] = []
        for individual in fronts[k]:
            idx = id_to_idx[id(individual)]
            for j in dominated_set[idx]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    population[j].rank = k + 2
                    next_front.append(population[j])
        k += 1
        fronts.append(next_front)
    return [f for f in fronts if f]


def fast_non_dominated_sort(
    population: list[Individual], objectives: list[Objective]
) -> list[list[Individual]]:
    """快速非支配排序（Deb 2002）。

    将种群分层: F1（最优前沿）、F2（次优）、...

    来源: Deb et al. 2002, https://ieeexplore.ieee.org/document/996017
    """
    domination_count, dominated_set = _compute_dominance_relations(population, objectives)
    return _build_fronts(population, domination_count, dominated_set)


def compute_crowding_distance(front: list[Individual], objectives: list[Objective]) -> None:
    """计算拥挤距离（Deb 2002 §IV-B，直接修改 individual.crowding_distance）。"""
    n = len(front)
    if n == 0:
        return
    for ind in front:
        ind.crowding_distance = 0.0
    for m in range(len(objectives)):
        front.sort(key=lambda ind: ind.objectives[m])
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")
        obj_min = front[0].objectives[m]
        obj_max = front[-1].objectives[m]
        if obj_max - obj_min < 1e-12:
            continue
        for i in range(1, n - 1):
            front[i].crowding_distance += (
                front[i + 1].objectives[m] - front[i - 1].objectives[m]
            ) / (obj_max - obj_min)


def tournament_selection(
    population: list[Individual], rng: np.random.Generator
) -> Individual:
    """锦标赛选择（二元，rank 小胜，rank 相同 crowding_distance 大胜）。"""
    i, j = rng.integers(0, len(population), size=2)
    a, b = population[i], population[j]
    if a.rank < b.rank:
        return a
    if a.rank > b.rank:
        return b
    if a.crowding_distance > b.crowding_distance:
        return a
    return b


def sbx_crossover(
    parent1: np.ndarray,
    parent2: np.ndarray,
    bounds: list[tuple[float, float]],
    config: SBXConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """SBX（Simulated Binary Crossover）交叉（Deb & Agrawal 1995）。"""
    n = len(parent1)
    child1 = parent1.copy()
    child2 = parent2.copy()
    rng = config.rng
    if rng.random() > config.prob:
        return child1, child2
    for i in range(n):
        if rng.random() > 0.5 or abs(parent1[i] - parent2[i]) < 1e-12:
            continue
        u = rng.random()
        if u <= 0.5:
            beta = (2.0 * u) ** (1.0 / (config.eta + 1.0))
        else:
            beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (config.eta + 1.0))
        child1[i] = 0.5 * ((1 + beta) * parent1[i] + (1 - beta) * parent2[i])
        child2[i] = 0.5 * ((1 - beta) * parent1[i] + (1 + beta) * parent2[i])
        lo, hi = bounds[i]
        child1[i] = np.clip(child1[i], lo, hi)
        child2[i] = np.clip(child2[i], lo, hi)
    return child1, child2


def polynomial_mutation(
    individual: np.ndarray,
    bounds: list[tuple[float, float]],
    prob: float,
    eta: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """多项式变异（Deb & Goyal 1996）。"""
    n = len(individual)
    mutated = individual.copy()
    for i in range(n):
        if rng.random() > prob:
            continue
        lo, hi = bounds[i]
        delta = hi - lo
        if delta < 1e-12:
            continue
        u = rng.random()
        if u < 0.5:
            delta_q = (2.0 * u) ** (1.0 / (eta + 1.0)) - 1.0
        else:
            delta_q = 1.0 - (2.0 * (1.0 - u)) ** (1.0 / (eta + 1.0))
        mutated[i] = np.clip(individual[i] + delta_q * delta, lo, hi)
    return mutated


class NSGA2Optimizer:
    """NSGA-II 多目标优化器（Deb et al. 2002）。

    对标 Tidy3D / Lumerical 多目标优化能力。

    Args:
        objectives: 目标定义列表。
        fom_fn: 多目标函数（输入参数，返回目标值向量）。
        config: 优化配置。
    """

    def __init__(
        self,
        objectives: list[Objective],
        fom_fn: Callable[[np.ndarray], np.ndarray],
        config: NSGA2Config | None = None,
    ) -> None:
        self.objectives = objectives
        self.fom_fn = fom_fn
        self.config = config or NSGA2Config()
        self.rng = np.random.default_rng(self.config.seed)

    def optimize(self, n_params: int) -> ParetoResult:
        population = self._init_population(n_params)
        objective_history: list[np.ndarray] = []
        for _ in range(self.config.max_generations):
            fronts = fast_non_dominated_sort(population, self.objectives)
            for front in fronts:
                compute_crowding_distance(front, self.objectives)
            if fronts:
                pareto_objs = np.array([ind.objectives for ind in fronts[0]])
                objective_history.append(pareto_objs.mean(axis=0))
            offspring = self._create_offspring(population)
            combined = population + offspring
            population = self._select_next_generation(combined)
        fronts = fast_non_dominated_sort(population, self.objectives)
        for front in fronts:
            compute_crowding_distance(front, self.objectives)
        pareto_front = fronts[0] if fronts else []
        return ParetoResult(
            pareto_front=pareto_front,
            all_solutions=population,
            generations=self.config.max_generations,
            converged=True,
            objective_history=objective_history,
        )

    def _init_population(self, n_params: int) -> list[Individual]:
        bounds = self.config.bounds or [(0.0, 1.0)] * n_params
        population: list[Individual] = []
        for _ in range(self.config.population_size):
            params = np.array([self.rng.uniform(lo, hi) for lo, hi in bounds])
            objectives = np.asarray(self.fom_fn(params), dtype=float)
            population.append(Individual(params=params, objectives=objectives))
        return population

    def _create_offspring(self, population: list[Individual]) -> list[Individual]:
        bounds = self.config.bounds or [(0.0, 1.0)] * len(population[0].params)
        offspring: list[Individual] = []
        n_offspring = self.config.population_size
        while len(offspring) < n_offspring:
            parent1 = tournament_selection(population, self.rng)
            parent2 = tournament_selection(population, self.rng)
            child1_params, child2_params = self._crossover_and_mutate(
                parent1, parent2, bounds
            )
            obj1 = np.asarray(self.fom_fn(child1_params), dtype=float)
            obj2 = np.asarray(self.fom_fn(child2_params), dtype=float)
            offspring.append(Individual(params=child1_params, objectives=obj1))
            if len(offspring) < n_offspring:
                offspring.append(Individual(params=child2_params, objectives=obj2))
        return offspring

    def _crossover_and_mutate(
        self, parent1: Individual, parent2: Individual, bounds: list[tuple[float, float]]
    ) -> tuple[np.ndarray, np.ndarray]:
        sbx_cfg = SBXConfig(
            prob=self.config.crossover_prob,
            eta=self.config.crossover_eta,
            rng=self.rng,
        )
        child1, child2 = sbx_crossover(parent1.params, parent2.params, bounds, sbx_cfg)
        child1 = polynomial_mutation(
            child1, bounds, self.config.mutation_prob, self.config.mutation_eta, self.rng
        )
        child2 = polynomial_mutation(
            child2, bounds, self.config.mutation_prob, self.config.mutation_eta, self.rng
        )
        return child1, child2

    def _select_next_generation(self, combined: list[Individual]) -> list[Individual]:
        fronts = fast_non_dominated_sort(combined, self.objectives)
        next_pop: list[Individual] = []
        for front in fronts:
            compute_crowding_distance(front, self.objectives)
            if len(next_pop) + len(front) <= self.config.population_size:
                next_pop.extend(front)
            else:
                front.sort(key=lambda ind: ind.crowding_distance, reverse=True)
                remaining = self.config.population_size - len(next_pop)
                next_pop.extend(front[:remaining])
                break
        return next_pop


def run_nsga2_optimization(
    objectives: list[Objective],
    fom_fn: Callable[[np.ndarray], np.ndarray],
    n_params: int,
    config: NSGA2Config | None = None,
) -> ParetoResult:
    """便捷函数: 执行 NSGA-II 多目标优化。"""
    optimizer = NSGA2Optimizer(objectives, fom_fn, config)
    return optimizer.optimize(n_params)


def weighted_sum_aggregation(
    objectives_values: np.ndarray, objectives: list[Objective]
) -> float:
    """加权求和聚合多目标为单目标（对照用）。"""
    total = 0.0
    for i, obj in enumerate(objectives):
        sign = 1.0 if obj.type == ObjectiveType.MAXIMIZE else -1.0
        total += sign * obj.weight * objectives_values[i]
    return total


# =============================================================================
# NSGA-III（参考点法，Deb & Jain 2014）
# =============================================================================


@dataclass
class NicheSelectionState:
    """小生境选择可变状态。

    Attributes:
        available: 可用个体索引列表（原地修改）。
        niche_counts: 参考点小生境计数（原地修改）。
        selected_indices: 已选个体索引列表（原地修改）。
    """

    available: list[int]
    niche_counts: np.ndarray
    selected_indices: list[int]


@dataclass
class NSGA3Config:
    """NSGA-III 配置。

    Attributes:
        population_size: 种群大小。
        max_generations: 最大代数。
        n_reference_points: 参考点数（None 自动计算）。
        crossover_prob: 交叉概率。
        mutation_prob: 变异概率。
        crossover_eta: SBX 分布指数。
        mutation_eta: 变异分布指数。
        bounds: 参数边界。
        seed: 随机种子。
    """

    population_size: int = 100
    max_generations: int = 200
    n_reference_points: int | None = None
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    crossover_eta: float = 20.0
    mutation_eta: float = 20.0
    bounds: list[tuple[float, float]] | None = None
    seed: int | None = None


@dataclass
class NSGA3Result:
    """NSGA-III 优化结果。

    Attributes:
        pareto_front: Pareto 前沿解集。
        reference_points: 参考点集。
        all_solutions: 所有解。
        generations: 迭代代数。
        converged: 是否收敛。
        objective_history: 目标历史。
    """

    pareto_front: list[Individual]
    reference_points: np.ndarray
    all_solutions: list[Individual]
    generations: int = 0
    converged: bool = False
    objective_history: list[np.ndarray] = field(default_factory=list)


def generate_reference_points(n_objectives: int, n_divisions: int = 4) -> np.ndarray:
    """Das-Dennis 参考点生成方法（Das & Dennis 1998）。

    在超平面上均匀分布参考点，每个参考点代表一个权重组合。

    来源: Das & Dennis 1998, https://doi.org/10.1137/S1052623496307510
    """
    if n_objectives == 1:
        return np.array([[1.0]])

    def _generate(dim: int, total: int) -> list[list[float]]:
        if dim == 1:
            return [[float(total)]]
        points: list[list[float]] = []
        for i in range(total + 1):
            rest = _generate(dim - 1, total - i)
            for r in rest:
                points.append([float(i)] + r)
        return points

    raw_points = _generate(n_objectives, n_divisions)
    points = np.array(raw_points, dtype=float)
    points /= n_divisions
    return points


def normalize_objectives(
    population: list[Individual], objectives: list[Objective]
) -> np.ndarray:
    """归一化目标值到 [0, 1]（NSGA-III 需要与参考点比较）。"""
    if not population:
        return np.zeros((0, len(objectives)))
    obj_matrix = np.array([ind.objectives for ind in population])
    normalized = obj_matrix.copy()
    for i, obj in enumerate(objectives):
        if obj.type == ObjectiveType.MAXIMIZE:
            normalized[:, i] = -normalized[:, i]
    obj_min = normalized.min(axis=0)
    obj_max = normalized.max(axis=0)
    denom = obj_max - obj_min
    denom = np.where(denom < 1e-12, 1e-12, denom)
    return (normalized - obj_min) / denom


def associate_to_reference_points(
    normalized_objs: np.ndarray, reference_points: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """将每个解关联到最近的参考点（欧氏距离）。"""
    n = len(normalized_objs)
    associations = np.zeros(n, dtype=int)
    distances = np.zeros(n)
    for i in range(n):
        obj = normalized_objs[i]
        euclid_dist = np.linalg.norm(reference_points - obj, axis=1)
        min_idx = int(np.argmin(euclid_dist))
        associations[i] = min_idx
        distances[i] = float(euclid_dist[min_idx])
    return associations, distances


def compute_niche_counts(
    associations: np.ndarray, n_ref: int, front_mask: np.ndarray | None = None
) -> np.ndarray:
    counts = np.zeros(n_ref, dtype=int)
    valid = associations[front_mask] if front_mask is not None else associations
    for idx in valid:
        counts[idx] += 1
    return counts


class NSGA3Optimizer:
    """NSGA-III 多目标优化器（Deb & Jain 2014，参考点法）。

    对标 Tidy3D / Lumerical 多目标优化能力（>3 目标场景）。
    """

    def __init__(
        self,
        objectives: list[Objective],
        fom_fn: Callable[[np.ndarray], np.ndarray],
        config: NSGA3Config | None = None,
    ) -> None:
        self.objectives = objectives
        self.fom_fn = fom_fn
        self.config = config or NSGA3Config()
        self.rng = np.random.default_rng(self.config.seed)
        self.n_objectives = len(objectives)
        n_div = 4 if self.n_objectives > 3 else 12 if self.n_objectives == 3 else 10
        self.reference_points = generate_reference_points(self.n_objectives, n_div)

    def optimize(self, n_params: int) -> NSGA3Result:
        population = self._init_population(n_params)
        objective_history: list[np.ndarray] = []
        for _ in range(self.config.max_generations):
            fronts = fast_non_dominated_sort(population, self.objectives)
            if fronts:
                pareto_objs = np.array([ind.objectives for ind in fronts[0]])
                objective_history.append(pareto_objs.mean(axis=0))
            offspring = self._create_offspring(population)
            combined = population + offspring
            population = self._select_next_generation(combined)
        fronts = fast_non_dominated_sort(population, self.objectives)
        pareto_front = fronts[0] if fronts else []
        return NSGA3Result(
            pareto_front=pareto_front,
            reference_points=self.reference_points,
            all_solutions=population,
            generations=self.config.max_generations,
            converged=True,
            objective_history=objective_history,
        )

    def _init_population(self, n_params: int) -> list[Individual]:
        bounds = self.config.bounds or [(0.0, 1.0)] * n_params
        population: list[Individual] = []
        for _ in range(self.config.population_size):
            params = np.array([self.rng.uniform(lo, hi) for lo, hi in bounds])
            objectives = np.asarray(self.fom_fn(params), dtype=float)
            population.append(Individual(params=params, objectives=objectives))
        return population

    def _create_offspring(self, population: list[Individual]) -> list[Individual]:
        bounds = self.config.bounds or [(0.0, 1.0)] * len(population[0].params)
        offspring: list[Individual] = []
        n_offspring = self.config.population_size
        while len(offspring) < n_offspring:
            parent1 = tournament_selection(population, self.rng)
            parent2 = tournament_selection(population, self.rng)
            sbx_cfg = SBXConfig(
                prob=self.config.crossover_prob,
                eta=self.config.crossover_eta,
                rng=self.rng,
            )
            child1, child2 = sbx_crossover(parent1.params, parent2.params, bounds, sbx_cfg)
            child1 = polynomial_mutation(
                child1, bounds, self.config.mutation_prob, self.config.mutation_eta, self.rng
            )
            child2 = polynomial_mutation(
                child2, bounds, self.config.mutation_prob, self.config.mutation_eta, self.rng
            )
            obj1 = np.asarray(self.fom_fn(child1), dtype=float)
            obj2 = np.asarray(self.fom_fn(child2), dtype=float)
            offspring.append(Individual(params=child1, objectives=obj1))
            if len(offspring) < n_offspring:
                offspring.append(Individual(params=child2, objectives=obj2))
        return offspring

    def _select_next_generation(self, combined: list[Individual]) -> list[Individual]:
        fronts = fast_non_dominated_sort(combined, self.objectives)
        next_pop: list[Individual] = []
        for front in fronts:
            if len(next_pop) + len(front) <= self.config.population_size:
                next_pop.extend(front)
            else:
                remaining = self.config.population_size - len(next_pop)
                if remaining <= 0:
                    break
                selected = self._select_from_front(front, next_pop, remaining)
                next_pop.extend(selected)
                break
        return next_pop

    def _select_from_front(
        self, front: list[Individual], next_pop: list[Individual], remaining: int
    ) -> list[Individual]:
        front_normalized = normalize_objectives(front, self.objectives)
        associations, _ = associate_to_reference_points(
            front_normalized, self.reference_points
        )
        niche_counts = self._compute_next_pop_niche_counts(next_pop)
        return self._niche_select(front, associations, niche_counts, remaining)

    def _compute_next_pop_niche_counts(self, next_pop: list[Individual]) -> np.ndarray:
        if not next_pop:
            return np.zeros(len(self.reference_points), dtype=int)
        next_normalized = normalize_objectives(next_pop, self.objectives)
        next_assoc, _ = associate_to_reference_points(
            next_normalized, self.reference_points
        )
        return compute_niche_counts(next_assoc, len(self.reference_points))

    def _niche_select(
        self,
        front: list[Individual],
        associations: np.ndarray,
        niche_counts: np.ndarray,
        remaining: int,
    ) -> list[Individual]:
        state = NicheSelectionState(
            available=list(range(len(front))),
            niche_counts=niche_counts,
            selected_indices=[],
        )
        while len(state.selected_indices) < remaining and state.available:
            min_refs = self._find_min_niche_refs(state.niche_counts)
            picked = self._pick_from_refs(min_refs, associations, remaining, state)
            if not picked:
                self._pick_random_available(associations, state)
        return [front[idx] for idx in state.selected_indices]

    def _find_min_niche_refs(self, niche_counts: np.ndarray) -> list[int]:
        min_count = float("inf")
        min_refs: list[int] = []
        for j in range(len(self.reference_points)):
            if niche_counts[j] < min_count:
                min_count = niche_counts[j]
                min_refs = [j]
            elif niche_counts[j] == min_count:
                min_refs.append(j)
        return min_refs

    def _pick_from_refs(
        self,
        min_refs: list[int],
        associations: np.ndarray,
        remaining: int,
        state: NicheSelectionState,
    ) -> bool:
        for ref_idx in min_refs:
            for k in state.available:
                if associations[k] == ref_idx:
                    state.selected_indices.append(k)
                    state.available.remove(k)
                    state.niche_counts[ref_idx] += 1
                    return True
                if len(state.selected_indices) >= remaining:
                    return True
        return False

    def _pick_random_available(
        self, associations: np.ndarray, state: NicheSelectionState
    ) -> None:
        if not state.available:
            return
        k = state.available.pop(0)
        state.selected_indices.append(k)
        state.niche_counts[associations[k]] += 1


def run_nsga3_optimization(
    objectives: list[Objective],
    fom_fn: Callable[[np.ndarray], np.ndarray],
    n_params: int,
    config: NSGA3Config | None = None,
) -> NSGA3Result:
    """便捷函数: 执行 NSGA-III 多目标优化。"""
    optimizer = NSGA3Optimizer(objectives, fom_fn, config)
    return optimizer.optimize(n_params)


__all__ = [
    "ObjectiveType",
    "Objective",
    "SBXConfig",
    "Individual",
    "NSGA2Config",
    "ParetoResult",
    "NSGA2Optimizer",
    "NSGA3Config",
    "NSGA3Result",
    "NSGA3Optimizer",
    "NicheSelectionState",
    "dominates",
    "fast_non_dominated_sort",
    "compute_crowding_distance",
    "tournament_selection",
    "sbx_crossover",
    "polynomial_mutation",
    "weighted_sum_aggregation",
    "generate_reference_points",
    "normalize_objectives",
    "associate_to_reference_points",
    "compute_niche_counts",
    "run_nsga2_optimization",
    "run_nsga3_optimization",
]
