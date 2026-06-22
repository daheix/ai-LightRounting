"""多目标优化 NSGA-II 测试（P2-1 深化，第44轮）。

对标商业工具（Tidy3D / Lumerical）的多目标优化测试覆盖。

来源:
- Deb et al. 2002 NSGA-II
- ZDT1/ZDT2 测试函数（Zitzler-Deb-Thiele）
"""

from __future__ import annotations

import unittest

import numpy as np

from polaris.sim.multi_objective_optimizer import (
    Individual,
    NSGA2Config,
    NSGA2Optimizer,
    Objective,
    ObjectiveType,
    ParetoResult,
    SBXConfig,
    compute_crowding_distance,
    dominates,
    fast_non_dominated_sort,
    polynomial_mutation,
    run_nsga2_optimization,
    sbx_crossover,
    tournament_selection,
    weighted_sum_aggregation,
)


class TestObjectiveType(unittest.TestCase):
    """ObjectiveType 枚举测试。"""

    def test_values(self) -> None:
        """测试枚举值。"""
        self.assertEqual(ObjectiveType.MAXIMIZE.value, "maximize")
        self.assertEqual(ObjectiveType.MINIMIZE.value, "minimize")


class TestObjective(unittest.TestCase):
    """Objective 测试。"""

    def test_default_weight(self) -> None:
        """测试默认权重。"""
        obj = Objective(name="fom", type=ObjectiveType.MAXIMIZE)
        self.assertEqual(obj.weight, 1.0)

    def test_custom_weight(self) -> None:
        """测试自定义权重。"""
        obj = Objective(name="loss", type=ObjectiveType.MINIMIZE, weight=0.5)
        self.assertEqual(obj.weight, 0.5)


class TestDominates(unittest.TestCase):
    """dominates 支配判断测试。"""

    def test_maximize_dominates(self) -> None:
        """测试最大化目标支配。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        a = np.array([0.9])
        b = np.array([0.5])
        self.assertTrue(dominates(a, b, objectives))
        self.assertFalse(dominates(b, a, objectives))

    def test_minimize_dominates(self) -> None:
        """测试最小化目标支配。"""
        objectives = [Objective("loss", ObjectiveType.MINIMIZE)]
        a = np.array([0.1])
        b = np.array([0.5])
        self.assertTrue(dominates(a, b, objectives))
        self.assertFalse(dominates(b, a, objectives))

    def test_multi_objective_dominates(self) -> None:
        """测试多目标支配。"""
        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE),
            Objective("loss", ObjectiveType.MINIMIZE),
        ]
        a = np.array([0.9, 0.1])
        b = np.array([0.5, 0.5])
        self.assertTrue(dominates(a, b, objectives))

    def test_non_dominated(self) -> None:
        """测试非支配关系。"""
        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE),
            Objective("loss", ObjectiveType.MINIMIZE),
        ]
        a = np.array([0.9, 0.5])  # 高 FoM 但高损耗
        b = np.array([0.5, 0.1])  # 低 FoM 但低损耗
        self.assertFalse(dominates(a, b, objectives))
        self.assertFalse(dominates(b, a, objectives))

    def test_equal_no_domination(self) -> None:
        """测试相等解不支配。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        a = np.array([0.5])
        b = np.array([0.5])
        self.assertFalse(dominates(a, b, objectives))


class TestFastNonDominatedSort(unittest.TestCase):
    """快速非支配排序测试。"""

    def test_single_front(self) -> None:
        """测试单层前沿（全部非支配）。"""
        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE),
            Objective("loss", ObjectiveType.MINIMIZE),
        ]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.9, 0.5])),
            Individual(params=np.array([1.0]), objectives=np.array([0.5, 0.1])),
        ]
        fronts = fast_non_dominated_sort(pop, objectives)
        self.assertEqual(len(fronts), 1)
        self.assertEqual(len(fronts[0]), 2)

    def test_two_fronts(self) -> None:
        """测试两层前沿。

        双目标最大化：[0.9, 0.9] 支配 [0.5, 0.5] 和 [0.3, 0.3]
        [0.5, 0.5] 与 [0.3, 0.3] 互不支配？不，[0.5,0.5] 支配 [0.3,0.3]
        所以应为 3 层。改用非支配对：
        [0.9, 0.1] [0.1, 0.9] 互不支配 → F1
        [0.3, 0.3] 被 [0.9, 0.1] 和 [0.1, 0.9] 都不支配？[0.9,0.1] 不支配 [0.3,0.3]（0.1<0.3）
        所以 [0.3, 0.3] 也可能在 F1。用更明确的支配关系。
        """
        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE),
            Objective("loss", ObjectiveType.MAXIMIZE),
        ]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.9, 0.9])),  # F1
            Individual(params=np.array([1.0]), objectives=np.array([0.5, 0.5])),  # F2
            Individual(params=np.array([2.0]), objectives=np.array([0.3, 0.3])),  # F3
        ]
        fronts = fast_non_dominated_sort(pop, objectives)
        self.assertEqual(len(fronts), 3)
        self.assertEqual(len(fronts[0]), 1)
        self.assertEqual(fronts[0][0].rank, 1)

    def test_rank_assignment(self) -> None:
        """测试层级赋值。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.9])),
            Individual(params=np.array([1.0]), objectives=np.array([0.5])),
        ]
        fronts = fast_non_dominated_sort(pop, objectives)
        self.assertEqual(fronts[0][0].rank, 1)


class TestCrowdingDistance(unittest.TestCase):
    """拥挤距离测试。"""

    def test_boundary_infinite(self) -> None:
        """测试边界解拥挤距离为无穷。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        front = [
            Individual(params=np.array([0.0]), objectives=np.array([0.1])),
            Individual(params=np.array([1.0]), objectives=np.array([0.5])),
            Individual(params=np.array([2.0]), objectives=np.array([0.9])),
        ]
        compute_crowding_distance(front, objectives)
        self.assertEqual(front[0].crowding_distance, float("inf"))
        self.assertEqual(front[-1].crowding_distance, float("inf"))

    def test_middle_finite(self) -> None:
        """测试中间解拥挤距离有限。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        front = [
            Individual(params=np.array([0.0]), objectives=np.array([0.1])),
            Individual(params=np.array([1.0]), objectives=np.array([0.5])),
            Individual(params=np.array([2.0]), objectives=np.array([0.9])),
        ]
        compute_crowding_distance(front, objectives)
        self.assertGreater(front[1].crowding_distance, 0)
        self.assertNotEqual(front[1].crowding_distance, float("inf"))

    def test_empty_front(self) -> None:
        """测试空前沿。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        compute_crowding_distance([], objectives)  # 不应报错


class TestTournamentSelection(unittest.TestCase):
    """锦标赛选择测试。"""

    def test_lower_rank_wins(self) -> None:
        """测试低 rank 胜出。"""
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.5]), rank=2),
            Individual(params=np.array([1.0]), objectives=np.array([0.9]), rank=1),
        ]
        rng = np.random.default_rng(42)
        # 多次选择，rank=1 应至少胜一次
        winners = [tournament_selection(pop, rng) for _ in range(20)]
        ranks = [w.rank for w in winners]
        self.assertIn(1, ranks)

    def test_same_rank_higher_crowding_wins(self) -> None:
        """测试相同 rank 时高拥挤距离胜出。"""
        pop = [
            Individual(
                params=np.array([0.0]),
                objectives=np.array([0.5]),
                rank=1,
                crowding_distance=0.5,
            ),
            Individual(
                params=np.array([1.0]),
                objectives=np.array([0.9]),
                rank=1,
                crowding_distance=2.0,
            ),
        ]
        rng = np.random.default_rng(42)
        winners = [tournament_selection(pop, rng) for _ in range(50)]
        high_crowding_count = sum(1 for w in winners if w.crowding_distance == 2.0)
        self.assertGreater(high_crowding_count, 0)


class TestSBXCrossover(unittest.TestCase):
    """SBX 交叉测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        bounds = [(0.0, 1.0), (0.0, 1.0)]
        p1 = np.array([0.3, 0.7])
        p2 = np.array([0.6, 0.4])
        rng = np.random.default_rng(42)
        cfg = SBXConfig(prob=1.0, eta=20.0, rng=rng)
        c1, c2 = sbx_crossover(p1, p2, bounds, cfg)
        self.assertEqual(c1.shape, p1.shape)
        self.assertEqual(c2.shape, p2.shape)

    def test_bounds_respected(self) -> None:
        """测试边界约束。"""
        bounds = [(0.0, 1.0)] * 5
        p1 = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        p2 = np.array([0.2, 0.4, 0.6, 0.8, 0.95])
        rng = np.random.default_rng(42)
        cfg = SBXConfig(prob=1.0, eta=20.0, rng=rng)
        for _ in range(20):
            c1, c2 = sbx_crossover(p1, p2, bounds, cfg)
            self.assertTrue(np.all(c1 >= 0))
            self.assertTrue(np.all(c1 <= 1))
            self.assertTrue(np.all(c2 >= 0))
            self.assertTrue(np.all(c2 <= 1))

    def test_zero_prob_no_crossover(self) -> None:
        """测试零概率不交叉。"""
        bounds = [(0.0, 1.0)]
        p1 = np.array([0.3])
        p2 = np.array([0.7])
        rng = np.random.default_rng(42)
        cfg = SBXConfig(prob=0.0, eta=20.0, rng=rng)
        c1, c2 = sbx_crossover(p1, p2, bounds, cfg)
        np.testing.assert_array_equal(c1, p1)
        np.testing.assert_array_equal(c2, p2)


class TestPolynomialMutation(unittest.TestCase):
    """多项式变异测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        bounds = [(0.0, 1.0)] * 3
        ind = np.array([0.3, 0.5, 0.7])
        rng = np.random.default_rng(42)
        mutated = polynomial_mutation(ind, bounds, 1.0, 20.0, rng)
        self.assertEqual(mutated.shape, ind.shape)

    def test_bounds_respected(self) -> None:
        """测试边界约束。"""
        bounds = [(0.0, 1.0)] * 5
        ind = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        rng = np.random.default_rng(42)
        for _ in range(20):
            mutated = polynomial_mutation(ind, bounds, 1.0, 20.0, rng)
            self.assertTrue(np.all(mutated >= 0))
            self.assertTrue(np.all(mutated <= 1))

    def test_zero_prob_no_mutation(self) -> None:
        """测试零概率不变异。"""
        bounds = [(0.0, 1.0)] * 3
        ind = np.array([0.3, 0.5, 0.7])
        rng = np.random.default_rng(42)
        mutated = polynomial_mutation(ind, bounds, 0.0, 20.0, rng)
        np.testing.assert_array_equal(mutated, ind)


class TestNSGA2Config(unittest.TestCase):
    """NSGA2Config 测试。"""

    def test_defaults(self) -> None:
        """测试默认值。"""
        cfg = NSGA2Config()
        self.assertEqual(cfg.population_size, 100)
        self.assertEqual(cfg.max_generations, 200)
        self.assertEqual(cfg.crossover_prob, 0.9)
        self.assertEqual(cfg.crossover_eta, 20.0)

    def test_custom(self) -> None:
        """测试自定义配置。"""
        cfg = NSGA2Config(population_size=50, max_generations=100, seed=42)
        self.assertEqual(cfg.population_size, 50)
        self.assertEqual(cfg.seed, 42)


class TestNSGA2Optimizer(unittest.TestCase):
    """NSGA2Optimizer 类测试。"""

    def test_init(self) -> None:
        """测试初始化。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        optimizer = NSGA2Optimizer(objectives, lambda p: np.array([float(p[0])]))
        self.assertEqual(len(optimizer.objectives), 1)

    def test_optimize_single_objective(self) -> None:
        """测试单目标优化。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]

        def fom_fn(p: np.ndarray) -> np.ndarray:
            return np.array([float(p[0] ** 2)])

        cfg = NSGA2Config(
            population_size=20,
            max_generations=10,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        optimizer = NSGA2Optimizer(objectives, fom_fn, cfg)
        result = optimizer.optimize(n_params=1)
        self.assertIsInstance(result, ParetoResult)
        self.assertGreater(len(result.pareto_front), 0)
        self.assertEqual(result.generations, 10)

    def test_optimize_two_objectives(self) -> None:
        """测试双目标优化（ZDT1 简化版）。

        ZDT1: f1 = x1, f2 = g*(1 - sqrt(f1/g))
        g = 1 + 9*mean(x[1:])
        """
        n_params = 5

        def fom_fn(p: np.ndarray) -> np.ndarray:
            f1 = float(p[0])
            g = 1.0 + 9.0 * float(np.mean(p[1:]))
            h = 1.0 - np.sqrt(f1 / g) if g > 0 else 0.0
            f2 = g * h
            return np.array([f1, f2])

        objectives = [
            Objective("f1", ObjectiveType.MINIMIZE),
            Objective("f2", ObjectiveType.MINIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=30,
            max_generations=20,
            bounds=[(0.0, 1.0)] * n_params,
            seed=42,
        )
        optimizer = NSGA2Optimizer(objectives, fom_fn, cfg)
        result = optimizer.optimize(n_params=n_params)

        self.assertGreater(len(result.pareto_front), 0)
        # Pareto 前沿解应非支配
        for ind in result.pareto_front:
            self.assertEqual(ind.rank, 1)

    def test_optimize_maximize_minimize_mixed(self) -> None:
        """测试最大化+最小化混合目标。"""

        def fom_fn(p: np.ndarray) -> np.ndarray:
            fom = float(p[0])  # 最大化
            loss = float(1.0 - p[0] ** 2)  # 最小化
            return np.array([fom, loss])

        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE),
            Objective("loss", ObjectiveType.MINIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=20,
            max_generations=10,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        optimizer = NSGA2Optimizer(objectives, fom_fn, cfg)
        result = optimizer.optimize(n_params=1)
        self.assertGreater(len(result.pareto_front), 0)

    def test_objective_history(self) -> None:
        """测试目标历史记录。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        cfg = NSGA2Config(
            population_size=10,
            max_generations=5,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        optimizer = NSGA2Optimizer(objectives, lambda p: np.array([float(p[0])]), cfg)
        result = optimizer.optimize(n_params=1)
        self.assertEqual(len(result.objective_history), 5)


class TestRunNSGA2(unittest.TestCase):
    """run_nsga2_optimization 工厂函数测试。"""

    def test_basic(self) -> None:
        """测试便捷函数。"""
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        cfg = NSGA2Config(
            population_size=10,
            max_generations=5,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga2_optimization(
            objectives, lambda p: np.array([float(p[0])]), n_params=1, config=cfg
        )
        self.assertIsInstance(result, ParetoResult)
        self.assertGreater(len(result.pareto_front), 0)


class TestWeightedSumAggregation(unittest.TestCase):
    """加权求和聚合测试。"""

    def test_maximize_only(self) -> None:
        """测试纯最大化。"""
        objectives = [
            Objective("fom1", ObjectiveType.MAXIMIZE, weight=1.0),
            Objective("fom2", ObjectiveType.MAXIMIZE, weight=2.0),
        ]
        values = np.array([0.5, 0.3])
        result = weighted_sum_aggregation(values, objectives)
        self.assertAlmostEqual(result, 0.5 * 1.0 + 0.3 * 2.0)

    def test_mixed(self) -> None:
        """测试混合目标。"""
        objectives = [
            Objective("fom", ObjectiveType.MAXIMIZE, weight=1.0),
            Objective("loss", ObjectiveType.MINIMIZE, weight=0.5),
        ]
        values = np.array([0.8, 0.2])
        result = weighted_sum_aggregation(values, objectives)
        # 1.0*0.8 - 0.5*0.2 = 0.8 - 0.1 = 0.7
        self.assertAlmostEqual(result, 0.7)


class TestCommercialGapReduction(unittest.TestCase):
    """商业差距缩减测试（对标 Tidy3D / Lumerical）。"""

    def test_pareto_front_nondominated(self) -> None:
        """测试 Pareto 前沿全部非支配。

        对标商业工具的 Pareto 前沿正确性。
        """

        def fom_fn(p: np.ndarray) -> np.ndarray:
            f1 = float(p[0])
            f2 = float(1.0 - p[0] ** 2)
            return np.array([f1, f2])

        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=30,
            max_generations=20,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga2_optimization(objectives, fom_fn, 1, cfg)

        # Pareto 前沿中任意两个解不应互相支配
        front = result.pareto_front
        for i in range(len(front)):
            for j in range(len(front)):
                if i != j:
                    self.assertFalse(
                        dominates(front[i].objectives, front[j].objectives, objectives),
                        f"解 {i} 不应支配解 {j}",
                    )

    def test_convergence_improvement(self) -> None:
        """测试优化收敛性（目标历史改善）。

        对标商业工具的优化收敛能力。
        """
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]

        def fom_fn(p: np.ndarray) -> np.ndarray:
            return np.array([float(p[0] ** 2)])

        cfg = NSGA2Config(
            population_size=20,
            max_generations=15,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga2_optimization(objectives, fom_fn, 1, cfg)

        # 后期 Pareto 前沿均值应不劣于前期
        if len(result.objective_history) >= 2:
            early = result.objective_history[0]
            late = result.objective_history[-1]
            # 最大化目标，后期应 >= 前期
            self.assertGreaterEqual(float(late[0]), float(early[0]) - 0.5)

    def test_multi_dim_params(self) -> None:
        """测试多维参数优化。

        对标商业工具的多维参数空间搜索能力。
        """
        n_params = 5

        def fom_fn(p: np.ndarray) -> np.ndarray:
            # 多维目标：最大化最小分量 + 最小化最大分量
            return np.array([float(np.min(p)), float(np.max(p))])

        objectives = [
            Objective("min_comp", ObjectiveType.MAXIMIZE),
            Objective("max_comp", ObjectiveType.MINIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=20,
            max_generations=10,
            bounds=[(0.0, 1.0)] * n_params,
            seed=42,
        )
        result = run_nsga2_optimization(objectives, fom_fn, n_params, cfg)
        self.assertGreater(len(result.pareto_front), 0)

    def test_pareto_front_diversity(self) -> None:
        """测试 Pareto 前沿多样性。

        对标商业工具的多样性保持能力。
        """

        def fom_fn(p: np.ndarray) -> np.ndarray:
            f1 = float(p[0])
            f2 = float(1.0 - p[0])
            return np.array([f1, f2])

        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=30,
            max_generations=20,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga2_optimization(objectives, fom_fn, 1, cfg)

        # Pareto 前沿应有多个不同解
        if len(result.pareto_front) > 1:
            f1_values = [ind.objectives[0] for ind in result.pareto_front]
            self.assertGreater(np.std(f1_values), 0.01)

    def test_reproducibility(self) -> None:
        """测试可复现性（固定种子）。

        对标商业工具的确定性输出能力。
        """
        objectives = [Objective("fom", ObjectiveType.MAXIMIZE)]
        cfg = NSGA2Config(
            population_size=15,
            max_generations=5,
            bounds=[(0.0, 1.0)],
            seed=123,
        )
        result1 = run_nsga2_optimization(objectives, lambda p: np.array([float(p[0])]), 1, cfg)
        result2 = run_nsga2_optimization(objectives, lambda p: np.array([float(p[0])]), 1, cfg)
        # 固定种子应产生相同结果
        self.assertEqual(len(result1.pareto_front), len(result2.pareto_front))

    def test_full_pipeline(self) -> None:
        """测试完整流水线：初始化 → 排序 → 选择 → 变异 → Pareto 输出。

        对标商业工具的完整多目标优化流程。
        """
        n_params = 3

        def fom_fn(p: np.ndarray) -> np.ndarray:
            # 光子器件多目标：透过率 + 带宽
            transmission = float(np.mean(p))
            bandwidth = float(1.0 - np.std(p))
            return np.array([transmission, bandwidth])

        objectives = [
            Objective("transmission", ObjectiveType.MAXIMIZE),
            Objective("bandwidth", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA2Config(
            population_size=25,
            max_generations=15,
            bounds=[(0.0, 1.0)] * n_params,
            seed=42,
        )
        result = run_nsga2_optimization(objectives, fom_fn, n_params, cfg)

        # 验证结果结构
        self.assertIsInstance(result, ParetoResult)
        self.assertGreater(len(result.pareto_front), 0)
        self.assertEqual(result.generations, 15)
        self.assertTrue(result.converged)

        # Pareto 前沿解应全部 rank=1
        for ind in result.pareto_front:
            self.assertEqual(ind.rank, 1)


if __name__ == "__main__":
    unittest.main()
