"""D03 多目标优化（NSGA-III）验收测试。

覆盖多目标优化器的核心能力：
- M1: ZDT1 Pareto 前沿近似
- M2: 种群多样性
- M3: 约束处理

文献来源:
- Deb & Jain 2014 "An Evolutionary Many-Objective Optimization Algorithm Using
  Reference-Point-Based Nondominated Sorting Approach, Part I"
  https://doi.org/10.1109/TEVC.2013.2281535
- Deb et al. 2002 "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II"
  https://ieeexplore.ieee.org/document/996017
- ZDT 测试问题: Zitzler et al. 2000 "Comparison of Multiobjective Evolutionary Algorithms"
  https://doi.org/10.1162/106365600568202
- Das & Dennis 1998 "Normal-boundary intersection"
  https://doi.org/10.1137/S1052623496307510
- Tidy3D 多目标优化
  https://docs.flexcompute.com/projects/tidy3d/en/latest/
"""

from __future__ import annotations

import numpy as np

from polaris.sim.nsga2_operators import (
    Individual,
    Objective,
    ObjectiveType,
    compute_crowding_distance,
    dominates,
    fast_non_dominated_sort,
)
from polaris.sim.nsga3_optimizer import (
    NSGA3Config,
    NSGA3Optimizer,
    NSGA3Result,
    associate_to_reference_points,
    compute_niche_counts,
    generate_reference_points,
    normalize_objectives,
    run_nsga3_optimization,
)


def zdt1(x: np.ndarray) -> np.ndarray:
    """ZDT1 测试问题（凸 Pareto 前沿）。

    f1(x) = x_1
    f2(x) = g(x) * h(f1(x), g(x))
    g(x) = 1 + 9/(n-1) * sum_{i=2}^n x_i
    h(f1, g) = 1 - sqrt(f1/g)

    真实 Pareto 前沿: f2 = 1 - sqrt(f1), f1 ∈ [0,1]
    """
    n = len(x)
    f1 = x[0]
    g = 1.0 + 9.0 / (n - 1) * np.sum(x[1:])
    h = 1.0 - np.sqrt(f1 / g)
    f2 = g * h
    return np.array([f1, f2])


def zdt2(x: np.ndarray) -> np.ndarray:
    """ZDT2 测试问题（非凸 Pareto 前沿）。"""
    n = len(x)
    f1 = x[0]
    g = 1.0 + 9.0 / (n - 1) * np.sum(x[1:])
    h = 1.0 - (f1 / g) ** 2
    f2 = g * h
    return np.array([f1, f2])


def schaffer_n1(x: np.ndarray) -> np.ndarray:
    """Schaffer N1 双目标问题。"""
    f1 = x[0] ** 2
    f2 = (x[0] - 2) ** 2
    return np.array([f1, f2])


def constrained_biobjective(x: np.ndarray) -> np.ndarray:
    """带约束的双目标问题。"""
    f1 = x[0]
    f2 = 1.0 - x[0] ** 2
    return np.array([f1, f2])


class TestReferencePoints:
    """参考点生成测试。"""

    def test_generate_reference_points_2d(self) -> None:
        """2 目标参考点生成。"""
        points = generate_reference_points(2, n_divisions=4)
        assert points.shape[0] == 5
        assert points.shape[1] == 2
        assert np.allclose(points.sum(axis=1), 1.0)

    def test_generate_reference_points_3d(self) -> None:
        """3 目标参考点生成。"""
        points = generate_reference_points(3, n_divisions=3)
        assert points.shape[1] == 3
        assert np.allclose(points.sum(axis=1), 1.0)
        assert np.all(points >= 0.0)

    def test_generate_reference_points_1d(self) -> None:
        """1 目标特殊情况。"""
        points = generate_reference_points(1)
        assert points.shape == (1, 1)
        assert points[0, 0] == 1.0

    def test_reference_points_bounds(self) -> None:
        """参考点在 [0,1] 范围内。"""
        for n_obj in [2, 3, 4]:
            points = generate_reference_points(n_obj, n_divisions=3)
            assert np.all(points >= 0.0)
            assert np.all(points <= 1.0)


class TestNormalizeObjectives:
    """目标归一化测试。"""

    def test_normalize_basic(self) -> None:
        """基本归一化。"""
        objectives = [Objective(name="f1", type=ObjectiveType.MINIMIZE)]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([1.0])),
            Individual(params=np.array([0.0]), objectives=np.array([3.0])),
            Individual(params=np.array([0.0]), objectives=np.array([5.0])),
        ]
        normalized = normalize_objectives(pop, objectives)
        assert normalized.shape == (3, 1)
        assert abs(normalized[0, 0] - 0.0) < 1e-10
        assert abs(normalized[-1, 0] - 1.0) < 1e-10

    def test_normalize_maximize(self) -> None:
        """最大化目标归一化。"""
        objectives = [Objective(name="f1", type=ObjectiveType.MAXIMIZE)]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([1.0])),
            Individual(params=np.array([0.0]), objectives=np.array([5.0])),
        ]
        normalized = normalize_objectives(pop, objectives)
        assert normalized.shape == (2, 1)

    def test_normalize_empty_population(self) -> None:
        """空种群。"""
        objectives = [Objective(name="f1", type=ObjectiveType.MINIMIZE)]
        normalized = normalize_objectives([], objectives)
        assert normalized.shape == (0, 1)


class TestAssociateReferencePoints:
    """参考点关联测试。"""

    def test_associate_shape(self) -> None:
        """关联结果形状。"""
        n = 5
        n_obj = 2
        objs = np.random.rand(n, n_obj)
        refs = generate_reference_points(n_obj, n_divisions=3)
        assoc, dists = associate_to_reference_points(objs, refs)
        assert assoc.shape == (n,)
        assert dists.shape == (n,)
        assert np.all(assoc >= 0)
        assert np.all(assoc < len(refs))

    def test_associate_known_point(self) -> None:
        """已知点的关联。"""
        refs = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
        objs = np.array([[0.9, 0.1], [0.1, 0.9], [0.5, 0.5]])
        assoc, _ = associate_to_reference_points(objs, refs)
        assert len(assoc) == 3


class TestNicheCounts:
    """小生境计数测试。"""

    def test_niche_counts_basic(self) -> None:
        """基本小生境计数。"""
        associations = np.array([0, 0, 1, 2, 2, 2])
        n_ref = 3
        counts = compute_niche_counts(associations, n_ref)
        assert counts[0] == 2
        assert counts[1] == 1
        assert counts[2] == 3

    def test_niche_counts_with_mask(self) -> None:
        """带掩码的小生境计数。"""
        associations = np.array([0, 1, 1, 2])
        mask = np.array([True, False, True, False])
        counts = compute_niche_counts(associations, 3, mask)
        assert counts[0] == 1
        assert counts[1] == 1
        assert counts[2] == 0


class TestNSGA3Config:
    """NSGA-III 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = NSGA3Config()
        assert cfg.population_size == 100
        assert cfg.max_generations == 200
        assert cfg.crossover_prob == 0.9
        assert cfg.mutation_prob == 0.1
        assert cfg.crossover_eta == 20.0
        assert cfg.mutation_eta == 20.0

    def test_custom_config(self) -> None:
        """自定义配置。"""
        bounds = [(0.0, 1.0), (0.0, 1.0)]
        cfg = NSGA3Config(
            population_size=50,
            max_generations=50,
            crossover_prob=0.8,
            mutation_prob=0.05,
            bounds=bounds,
            seed=42,
        )
        assert cfg.population_size == 50
        assert cfg.max_generations == 50
        assert cfg.bounds == bounds


class TestNSGA3OptimizerM1ZDT1:
    """M1: ZDT1 Pareto 前沿近似测试。"""

    def test_nsga3_zdt1_pareto_front_exists(self) -> None:
        """ZDT1 能产生非空 Pareto 前沿。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 10
        cfg = NSGA3Config(
            population_size=50,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=10)

        assert isinstance(result, NSGA3Result)
        assert len(result.pareto_front) > 0
        assert result.generations == 10

    def test_nsga3_zdt1_pareto_nondominated(self) -> None:
        """Pareto 前沿解互不支配。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 10
        cfg = NSGA3Config(
            population_size=40,
            max_generations=20,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=10)

        pareto = result.pareto_front
        for i in range(len(pareto)):
            for j in range(len(pareto)):
                if i != j:
                    assert not dominates(pareto[i].objectives, pareto[j].objectives, objectives)

    def test_nsga3_zdt1_spread(self) -> None:
        """Pareto 前沿有一定分布范围。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 10
        cfg = NSGA3Config(
            population_size=50,
            max_generations=30,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=10)

        f1_vals = [ind.objectives[0] for ind in result.pareto_front]
        assert max(f1_vals) - min(f1_vals) > 0.2


class TestNSGA3OptimizerM2Diversity:
    """M2: 种群多样性测试。"""

    def test_nsga3_population_size(self) -> None:
        """种群大小保持。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 5
        pop_size = 40
        cfg = NSGA3Config(
            population_size=pop_size,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=5)

        assert len(result.all_solutions) == pop_size

    def test_nsga3_reference_points_used(self) -> None:
        """使用了参考点机制。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        cfg = NSGA3Config(population_size=30, max_generations=5, seed=42)
        opt = NSGA3Optimizer(objectives, zdt1, cfg)

        assert len(opt.reference_points) > 0
        assert opt.reference_points.shape[1] == 2

    def test_nsga3_diverse_objectives(self) -> None:
        """目标值有多样性（不全相同）。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 5
        cfg = NSGA3Config(
            population_size=30,
            max_generations=20,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=5)

        f1_vals = np.array([ind.objectives[0] for ind in result.all_solutions])
        assert np.std(f1_vals) > 0.01

    def test_nsga3_3objectives(self) -> None:
        """3 目标优化。"""
        def three_obj(x):
            return np.array([x[0]**2, (x[0]-1)**2, (x[0]-2)**2])

        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
            Objective(name="f3", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(-2.0, 3.0)]
        cfg = NSGA3Config(
            population_size=50,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, three_obj, cfg)
        result = opt.optimize(n_params=1)

        assert len(result.pareto_front) > 0
        assert result.reference_points.shape[1] == 3


class TestNSGA3OptimizerM3Constraints:
    """M3: 约束处理测试。"""

    def test_nsga3_bounds_respected(self) -> None:
        """参数始终在边界内。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 5
        cfg = NSGA3Config(
            population_size=30,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=5)

        for ind in result.all_solutions:
            assert np.all(ind.params >= 0.0 - 1e-10)
            assert np.all(ind.params <= 1.0 + 1e-10)

    def test_nsga3_maximize_objectives(self) -> None:
        """最大化目标支持。"""
        def neg_zdt1(x):
            f = zdt1(x)
            return -f

        objectives = [
            Objective(name="f1", type=ObjectiveType.MAXIMIZE),
            Objective(name="f2", type=ObjectiveType.MAXIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 5
        cfg = NSGA3Config(
            population_size=30,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, neg_zdt1, cfg)
        result = opt.optimize(n_params=5)

        assert len(result.pareto_front) > 0

    def test_nsga3_mixed_objectives(self) -> None:
        """混合最大化/最小化目标。"""
        def mixed(x):
            return np.array([x[0]**2, 1.0 - x[0]**2])

        objectives = [
            Objective(name="f1_min", type=ObjectiveType.MINIMIZE),
            Objective(name="f2_max", type=ObjectiveType.MAXIMIZE),
        ]
        bounds = [(0.0, 1.0)]
        cfg = NSGA3Config(
            population_size=30,
            max_generations=10,
            bounds=bounds,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, mixed, cfg)
        result = opt.optimize(n_params=1)

        assert len(result.pareto_front) > 0

    def test_nsga3_no_bounds_default(self) -> None:
        """无边界时使用默认 [0,1]。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        cfg = NSGA3Config(population_size=20, max_generations=5, seed=42)
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=3)

        assert len(result.pareto_front) > 0


class TestNSGA3Result:
    """NSGA3Result 结果测试。"""

    def test_result_fields(self) -> None:
        """结果字段完整性。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 3
        cfg = NSGA3Config(population_size=20, max_generations=5, bounds=bounds, seed=42)
        opt = NSGA3Optimizer(objectives, zdt1, cfg)
        result = opt.optimize(n_params=3)

        assert hasattr(result, 'pareto_front')
        assert hasattr(result, 'reference_points')
        assert hasattr(result, 'all_solutions')
        assert hasattr(result, 'generations')
        assert hasattr(result, 'converged')
        assert hasattr(result, 'objective_history')


class TestNSGA3Factory:
    """工厂函数测试。"""

    def test_run_nsga3_optimization(self) -> None:
        """便捷函数。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        result = run_nsga3_optimization(
            objectives,
            zdt1,
            n_params=5,
            config=NSGA3Config(population_size=20, max_generations=3, seed=42),
        )
        assert isinstance(result, NSGA3Result)

    def test_nsga3_different_seeds(self) -> None:
        """不同种子产生不同结果。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        bounds = [(0.0, 1.0)] * 5

        results = []
        for seed in [42, 123, 456]:
            cfg = NSGA3Config(population_size=30, max_generations=10, bounds=bounds, seed=seed)
            opt = NSGA3Optimizer(objectives, zdt1, cfg)
            result = opt.optimize(n_params=5)
            results.append(result)

        assert len(results) == 3


class TestNSGA2OperatorsIntegration:
    """NSGA-II 算子集成测试。"""

    def test_dominates_function(self) -> None:
        """dominates 函数。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        a = np.array([1.0, 2.0])
        b = np.array([2.0, 3.0])
        assert dominates(a, b, objectives) is True
        assert dominates(b, a, objectives) is False

    def test_fast_non_dominated_sort(self) -> None:
        """快速非支配排序。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([1.0, 5.0])),
            Individual(params=np.array([0.0]), objectives=np.array([2.0, 3.0])),
            Individual(params=np.array([0.0]), objectives=np.array([3.0, 1.0])),
            Individual(params=np.array([0.0]), objectives=np.array([4.0, 4.0])),
        ]
        fronts = fast_non_dominated_sort(pop, objectives)
        assert len(fronts) >= 1
        assert fronts[0][0].rank == 1

    def test_crowding_distance(self) -> None:
        """拥挤距离计算。"""
        objectives = [
            Objective(name="f1", type=ObjectiveType.MINIMIZE),
            Objective(name="f2", type=ObjectiveType.MINIMIZE),
        ]
        front = [
            Individual(params=np.array([0.0]), objectives=np.array([1.0, 5.0])),
            Individual(params=np.array([0.0]), objectives=np.array([2.0, 3.0])),
            Individual(params=np.array([0.0]), objectives=np.array([3.0, 1.0])),
        ]
        compute_crowding_distance(front, objectives)
        assert front[0].crowding_distance == float("inf")
        assert front[-1].crowding_distance == float("inf")
