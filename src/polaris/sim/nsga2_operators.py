"""NSGA-II 遗传操作算子与数据类型（从 multi_objective_optimizer.py 拆分，第63轮 P2-1）。

包含数据类（Individual/Objective/ObjectiveType/SBXConfig/NSGA2Config/ParetoResult）
和遗传操作算子函数（非支配排序、拥挤距离、锦标赛选择、SBX 交叉、多项式变异）。

来源（R02 学术诚信，均经 WebSearch 验证可访问）:
- Deb et al. 2002, "A Fast and Elitist Multiobjective Genetic Algorithm:
  NSGA-II", IEEE Trans. Evol. Comput. 6(2):182-197,
  https://doi.org/10.1109/4235.996017
- SBX (Simulated Binary Crossover): Deb & Agrawal 1995, "Simulated binary
  crossover for continuous search space", Complex Syst. 9(2):115-148,
  https://complex-systems.com/abstracts/vol09_i02_a02/
- 多项式变异: Deb & Goyal 1996, "A combined genetic adaptive search (GeneAS)
  for engineering design", Comput. Sci. Inform. 26:30-45,
  https://www.iitk.ac.in/kangal/papers/k199601.pdf
- 快速非支配排序: Deb et al. 2002 §III,
  https://ieeexplore.ieee.org/document/996017
- 拥挤距离: Deb et al. 2002 §IV-B,
  https://doi.org/10.1109/4235.996017
- PlatEMO 实现: Tian et al. 2017, IEEE Comput. Intell. Mag. 12(4):73-87,
  https://doi.org/10.1109/MCI.2017.2742868
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


@dataclass
class SBXConfig:
    """SBX 交叉配置（第58轮重构，降低参数个数）。

    封装 sbx_crossover 的配置参数，使函数签名从 6 参数降至 4 参数。

    Attributes:
        prob: 交叉概率。
        eta: 分布指数（越大越接近父代）。
        rng: 随机数生成器。
    """

    prob: float = 1.0
    eta: float = 20.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng())


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

    def __eq__(self, other: object) -> bool:
        """相等判断（基于 id，避免数组比较歧义）。"""
        return self is other

    def __hash__(self) -> int:
        """哈希（基于 id）。"""
        return id(self)


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


def _compute_dominance_relations(
    population: list[Individual],
    objectives: list[Objective],
) -> tuple[list[int], list[list[int]]]:
    """计算种群中所有个体对的支配关系。

    Args:
        population: 种群。
        objectives: 目标定义。

    Returns:
        (domination_count, dominated_set)：
        - domination_count[i] = 个体 i 被支配的次数
        - dominated_set[i] = 个体 i 支配的个体索引列表
    """
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
    """从支配关系构建 Pareto 前沿分层。

    Args:
        population: 种群。
        domination_count: 每个个体被支配的次数。
        dominated_set: 每个个体支配的个体索引列表。

    Returns:
        分层列表 [F1, F2, ...]。
    """
    n = len(population)
    id_to_idx = {id(ind): i for i, ind in enumerate(population)}
    fronts: list[list[Individual]] = [[]]

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
            idx = id_to_idx[id(individual)]
            for j in dominated_set[idx]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    population[j].rank = k + 2
                    next_front.append(population[j])
        k += 1
        fronts.append(next_front)

    # 移除空层
    return [f for f in fronts if f]


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

    来源: Deb et al., "A Fast and Elitist Multiobjective Genetic Algorithm:
        NSGA-II", IEEE TEVC 2002, https://ieeexplore.ieee.org/document/996017
    """
    domination_count, dominated_set = _compute_dominance_relations(population, objectives)
    return _build_fronts(population, domination_count, dominated_set)


def compute_crowding_distance(front: list[Individual], objectives: list[Objective]) -> None:
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


def tournament_selection(population: list[Individual], rng: np.random.Generator) -> Individual:
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
    config: SBXConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """SBX（Simulated Binary Crossover）交叉。

    Args:
        parent1: 父代 1。
        parent2: 父代 2。
        bounds: 参数边界。
        config: SBX 配置（prob/eta/rng）。

    Returns:
        (child1, child2)。
    """
    n = len(parent1)
    child1 = parent1.copy()
    child2 = parent2.copy()
    rng = config.rng

    if rng.random() > config.prob:
        return child1, child2

    for i in range(n):
        if rng.random() > 0.5:
            continue
        if abs(parent1[i] - parent2[i]) < 1e-12:
            continue

        # SBX 计算
        u = rng.random()
        if u <= 0.5:
            beta = (2.0 * u) ** (1.0 / (config.eta + 1.0))
        else:
            beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (config.eta + 1.0))

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


__all__ = [
    "SBXConfig",
    "ObjectiveType",
    "Objective",
    "Individual",
    "NSGA2Config",
    "ParetoResult",
    "dominates",
    "fast_non_dominated_sort",
    "compute_crowding_distance",
    "tournament_selection",
    "sbx_crossover",
    "polynomial_mutation",
]
