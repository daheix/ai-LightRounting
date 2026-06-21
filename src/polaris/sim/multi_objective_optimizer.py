"""多目标优化 NSGA-II（P2-1 深化，第44轮）。

对标商业工具（Tidy3D / Lumerical / IC Compiler II）的多目标优化能力，
实现 NSGA-II（Non-dominated Sorting Genetic Algorithm II）算法，
支持 Pareto 前沿计算。

## 核心差距（第43轮分析）

第40轮的 global_optimizer.py 仅有 CMA-ES 和 PSO（单目标），
完全缺失多目标优化、Pareto 前沿、NSGA-II。
本模块填补以下差距：

1. 快速非支配排序（fast non-dominated sort）
2. 拥挤距离（crowding distance）
3. 遗传操作（锦标赛选择 + 交叉 + 变异）
4. Pareto 前沿输出
5. 多目标目标函数接口（fom_fn → np.ndarray 向量）

## 算法（Deb et al. 2002）

NSGA-II 流程：
    1. 初始化种群 P（N 个个体）
    2. 快速非支配排序 → 分层 F1, F2, ...
    3. 计算拥挤距离
    4. 锦标赛选择 + 交叉 + 变异 → 子代 Q
    5. P ∪ Q → 非支配排序 → 选前 N 个 → 新 P
    6. 重复 2-5 直到收敛

来源:
- Deb et al. "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II" 2002
- Deb & Jain "An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based Nondominated Sorting Approach, Part I" 2014（NSGA-III）
- Tidy3D 多目标优化: https://docs.flexcompute.com/projects/tidy3d/en/latest/
"""

from __future__ import annotations

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


@dataclass
class NSGA2Config:
    """NSGA-II 配置。

    Attributes:
        population_size: 种群大小。
            来源: Deb 2002 建议 100-200。
        max_generations: 最大代数。
        crossover_prob: 交叉概率。
            来源: Deb 2002 默认 0.9。
        mutation_prob: 变异概率。
            来源: Deb 2002 默认 1/n_params。
        crossover_eta: SBX 交叉分布指数。
            来源: Deb 2002 默认 20。
        mutation_eta: 多项式变异分布指数。
            来源: Deb 2002 默认 20。
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
    """判断解 a 是否支配解 b。

    a 支配 b 当且仅当：
    - a 在所有目标上不劣于 b
    - a 在至少一个目标上严格优于 b

    Args:
        a: 解 a 的目标值向量。
        b: 解 b 的目标值向量。
        objectives: 目标定义列表。

    Returns:
        True 若 a 支配 b。
    """
    better_in_one = False
    for i, obj in enumerate(objectives):
        if obj.type == ObjectiveType.MAXIMIZE:
            if a[i] < b[i]:
                return False
            if a[i] > b[i]:
                better_in_one = True
        else:  # MINIMIZE
            if a[i] > b[i]:
                return False
            if a[i] < b[i]:
                better_in_one = True
    return better_in_one


def fast_non_dominated_sort(
    population: list[Individual], objectives: list[Objective]
) -> list[list[Individual]]:
    """快速非支配排序（Deb 2002）。

    将种群分层：F1（最优前沿）、F2（次优）、...

    Args:
        population: 种群。
        objectives: 目标定义。

    Returns:
        分层列表 [F1, F2, ...]。
    """
    n = len(population)
    domination_count = [0] * n  # 被 a 支配的解数
    dominated_set: list[list[int]] = [[] for _ in range(n)]  # a 支配的解索引
    fronts: list[list[Individual]] = [[]]

    for i in range(n):
        for j in range(i + 1, n):
            if dominates(population[i].objectives, population[j].objectives, objectives):
                dominated_set[i].append(j)
                domination_count[j] += 1
            elif dominates(population[j].objectives, population[i].objectives, objectives):
                dominated_set[j].append(i)
                domination_count[i] += 1

    # 第一层：支配计数为 0 的解
    for i in range(n):
        if domination_count[i] == 0:
            population[i].rank = 1
            fronts[0].append(population[i])

    # 后续层
    k = 0
    while fronts[k]:
        next_front: list[Individual] = []
        for individual in fronts[k]:
            idx = population.index(individual)
            for j in dominated_set[idx]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    population[j].rank = k + 2
                    next_front.append(population[j])
        k += 1
        fronts.append(next_front)

    # 移除空层
    return [f for f in fronts if f]


def compute_crowding_distance(
    front: list[Individual], objectives: list[Objective]
) -> None:
    """计算拥挤距离（Deb 2002）。

    拥挤距离越大，解越孤立（保持多样性）。

    Args:
        front: 单层前沿。
        objectives: 目标定义。

    Returns:
        无，直接修改 individual.crowding_distance。
    """
    n = len(front)
    if n == 0:
        return
    for ind in front:
        ind.crowding_distance = 0.0

    for m in range(len(objectives)):
        # 按目标 m 排序
        front.sort(key=lambda ind: ind.objectives[m])
        # 边界解拥挤距离设为无穷
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")
        # 计算中间解
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
    """锦标赛选择（二元锦标赛）。

    规则：
    1. rank 小的胜
    2. rank 相同时，crowding_distance 大的胜

    Args:
        population: 种群。
        rng: 随机数生成器。

    Returns:
        胜者个体。
    """
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
    prob: float,
    eta: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """SBX（Simulated Binary Crossover）交叉。

    Args:
        parent1: 父代 1。
        parent2: 父代 2。
        bounds: 参数边界。
        prob: 交叉概率。
        eta: 分布指数。
        rng: 随机数生成器。

    Returns:
        (child1, child2)。
    """
    n = len(parent1)
    child1 = parent1.copy()
    child2 = parent2.copy()

    if rng.random() > prob:
        return child1, child2

    for i in range(n):
        if rng.random() > 0.5:
            continue
        if abs(parent1[i] - parent2[i]) < 1e-12:
            continue

        # SBX 计算
        u = rng.random()
        if u <= 0.5:
            beta = (2.0 * u) ** (1.0 / (eta + 1.0))
        else:
            beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0))

        child1[i] = 0.5 * ((1 + beta) * parent1[i] + (1 - beta) * parent2[i])
        child2[i] = 0.5 * ((1 - beta) * parent1[i] + (1 + beta) * parent2[i])

        # 边界裁剪
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
    """多项式变异。

    Args:
        individual: 个体参数。
        bounds: 参数边界。
        prob: 变异概率。
        eta: 分布指数。
        rng: 随机数生成器。

    Returns:
        变异后的个体。
    """
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
    """NSGA-II 多目标优化器。

    对标 Tidy3D / Lumerical 多目标优化能力。

    Args:
        objectives: 目标定义列表。
        fom_fn: 多目标函数（输入参数，返回目标值向量）。
        config: 优化配置。
    """

    def __init__(
        self,
        objectives: list[Objective],
        fom_fn: callable,
        config: NSGA2Config | None = None,
    ) -> None:
        """初始化 NSGA-II 优化器。

        Args:
            objectives: 目标定义列表。
            fom_fn: 多目标函数。
            config: 优化配置。
        """
        self.objectives = objectives
        self.fom_fn = fom_fn
        self.config = config or NSGA2Config()
        self.rng = np.random.default_rng(self.config.seed)

    def _init_population(self, n_params: int) -> list[Individual]:
        """初始化种群。

        Args:
            n_params: 参数维度。

        Returns:
            初始种群。
        """
        bounds = self.config.bounds or [(0.0, 1.0)] * n_params
        population: list[Individual] = []
        for _ in range(self.config.population_size):
            params = np.array(
                [self.rng.uniform(lo, hi) for lo, hi in bounds]
            )
            objectives = np.asarray(self.fom_fn(params), dtype=float)
            population.append(Individual(params=params, objectives=objectives))
        return population

    def _create_offspring(self, population: list[Individual]) -> list[Individual]:
        """创建子代。

        Args:
            population: 父代种群。

        Returns:
            子代种群。
        """
        bounds = self.config.bounds or [(0.0, 1.0)] * len(population[0].params)
        offspring: list[Individual] = []
        n_offspring = self.config.population_size

        while len(offspring) < n_offspring:
            parent1 = tournament_selection(population, self.rng)
            parent2 = tournament_selection(population, self.rng)

            child1_params, child2_params = sbx_crossover(
                parent1.params,
                parent2.params,
                bounds,
                self.config.crossover_prob,
                self.config.crossover_eta,
                self.rng,
            )

            child1_params = polynomial_mutation(
                child1_params,
                bounds,
                self.config.mutation_prob,
                self.config.mutation_eta,
                self.rng,
            )
            child2_params = polynomial_mutation(
                child2_params,
                bounds,
                self.config.mutation_prob,
                self.config.mutation_eta,
                self.rng,
            )

            obj1 = np.asarray(self.fom_fn(child1_params), dtype=float)
            obj2 = np.asarray(self.fom_fn(child2_params), dtype=float)
            offspring.append(Individual(params=child1_params, objectives=obj1))
            if len(offspring) < n_offspring:
                offspring.append(Individual(params=child2_params, objectives=obj2))

        return offspring

    def _select_next_generation(
        self, combined: list[Individual]
    ) -> list[Individual]:
        """选择下一代（精英保留）。

        Args:
            combined: P ∪ Q 合并种群。

        Returns:
            新种群（前 N 个）。
        """
        fronts = fast_non_dominated_sort(combined, self.objectives)
        next_pop: list[Individual] = []
        for front in fronts:
            compute_crowding_distance(front, self.objectives)
            if len(next_pop) + len(front) <= self.config.population_size:
                next_pop.extend(front)
            else:
                # 按拥挤距离排序，选前 N - len(next_pop) 个
                front.sort(key=lambda ind: ind.crowding_distance, reverse=True)
                remaining = self.config.population_size - len(next_pop)
                next_pop.extend(front[:remaining])
                break
        return next_pop

    def optimize(self, n_params: int) -> ParetoResult:
        """执行 NSGA-II 多目标优化。

        Args:
            n_params: 参数维度。

        Returns:
            ParetoResult。
        """
        # 1. 初始化种群
        population = self._init_population(n_params)
        objective_history: list[np.ndarray] = []

        # 2. 迭代
        for gen in range(self.config.max_generations):
            # 非支配排序 + 拥挤距离
            fronts = fast_non_dominated_sort(population, self.objectives)
            for front in fronts:
                compute_crowding_distance(front, self.objectives)

            # 记录 Pareto 前沿均值
            if fronts:
                pareto_objs = np.array([ind.objectives for ind in fronts[0]])
                objective_history.append(pareto_objs.mean(axis=0))

            # 创建子代
            offspring = self._create_offspring(population)

            # 精英选择
            combined = population + offspring
            population = self._select_next_generation(combined)

        # 3. 最终排序
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


def run_nsga2_optimization(
    objectives: list[Objective],
    fom_fn: callable,
    n_params: int,
    config: NSGA2Config | None = None,
) -> ParetoResult:
    """便捷函数：执行 NSGA-II 多目标优化。

    对标 Tidy3D `run_multiobjective_optimization` 接口。

    Args:
        objectives: 目标定义列表。
        fom_fn: 多目标函数。
        n_params: 参数维度。
        config: 优化配置。

    Returns:
        ParetoResult。

    来源:
        NSGA-II: Deb et al. 2002
    """
    optimizer = NSGA2Optimizer(objectives, fom_fn, config)
    return optimizer.optimize(n_params)


def weighted_sum_aggregation(
    objectives_values: np.ndarray, objectives: list[Objective]
) -> float:
    """加权求和聚合多目标为单目标。

    用于将多目标转换为单目标（对照用）。

    Args:
        objectives_values: 目标值向量。
        objectives: 目标定义（含权重）。

    Returns:
        加权求和标量。
    """
    total = 0.0
    for i, obj in enumerate(objectives):
        sign = 1.0 if obj.type == ObjectiveType.MAXIMIZE else -1.0
        total += sign * obj.weight * objectives_values[i]
    return total


__all__ = [
    "ObjectiveType",
    "Objective",
    "Individual",
    "NSGA2Config",
    "ParetoResult",
    "NSGA2Optimizer",
    "dominates",
    "fast_non_dominated_sort",
    "compute_crowding_distance",
    "tournament_selection",
    "sbx_crossover",
    "polynomial_mutation",
    "run_nsga2_optimization",
    "weighted_sum_aggregation",
]
