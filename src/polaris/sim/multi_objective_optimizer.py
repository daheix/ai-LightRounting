"""多目标优化 NSGA-II（P2-1 深化，第44轮）。

对标商业工具（Tidy3D / Lumerical / IC Compiler II）的多目标优化能力，
实现 NSGA-II（Non-dominated Sorting Genetic Algorithm II）算法，
支持 Pareto 前沿计算。

## 架构（第63轮 P2-1 拆分）

- ``nsga2_operators.py``：数据类 + 遗传操作算子函数
  （Individual/Objective/SBXConfig/NSGA2Config/ParetoResult +
   dominates/fast_non_dominated_sort/compute_crowding_distance/
   tournament_selection/sbx_crossover/polynomial_mutation）
- ``multi_objective_optimizer.py``（本文件）：NSGA2Optimizer 类 + 便捷函数

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
- Deb & Jain "An Evolutionary Many-Objective Optimization Algorithm Using
  Reference-Point-Based Nondominated Sorting Approach, Part I" 2014（NSGA-III）
- Tidy3D 多目标优化: https://docs.flexcompute.com/projects/tidy3d/en/latest/
"""

from __future__ import annotations

import numpy as np

from polaris.sim.nsga2_operators import (
    Individual,
    NSGA2Config,
    Objective,
    ObjectiveType,
    ParetoResult,
    SBXConfig,
    compute_crowding_distance,
    dominates,
    fast_non_dominated_sort,
    polynomial_mutation,
    sbx_crossover,
    tournament_selection,
)


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
            params = np.array([self.rng.uniform(lo, hi) for lo, hi in bounds])
            objectives = np.asarray(self.fom_fn(params), dtype=float)
            population.append(Individual(params=params, objectives=objectives))
        return population

    def _crossover_and_mutate(
        self,
        parent1: Individual,
        parent2: Individual,
        bounds: list[tuple[float, float]],
    ) -> tuple[np.ndarray, np.ndarray]:
        """SBX 交叉 + 多项式变异，生成两个子代参数。

        Args:
            parent1: 父代 1。
            parent2: 父代 2。
            bounds: 参数边界。

        Returns:
            (child1_params, child2_params) 两个子代参数。
        """
        sbx_cfg = SBXConfig(
            prob=self.config.crossover_prob,
            eta=self.config.crossover_eta,
            rng=self.rng,
        )
        child1_params, child2_params = sbx_crossover(
            parent1.params, parent2.params, bounds, sbx_cfg
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
        return child1_params, child2_params

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
            child1_params, child2_params = self._crossover_and_mutate(
                parent1, parent2, bounds
            )
            obj1 = np.asarray(self.fom_fn(child1_params), dtype=float)
            obj2 = np.asarray(self.fom_fn(child2_params), dtype=float)
            offspring.append(Individual(params=child1_params, objectives=obj1))
            if len(offspring) < n_offspring:
                offspring.append(Individual(params=child2_params, objectives=obj2))

        return offspring

    def _select_next_generation(self, combined: list[Individual]) -> list[Individual]:
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
        for _gen in range(self.config.max_generations):
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


def weighted_sum_aggregation(objectives_values: np.ndarray, objectives: list[Objective]) -> float:
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
    "SBXConfig",
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
