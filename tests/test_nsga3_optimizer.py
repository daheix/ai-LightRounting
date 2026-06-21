"""NSGA-III 参考点法多目标优化测试（P2-1 深化，第46轮）。

对标商业工具（Tidy3D / Lumerical）的多目标优化测试覆盖。

来源:
- Deb & Jain 2014 NSGA-III
- Das & Dennis 1998 参考点生成
"""

from __future__ import annotations

import unittest

import numpy as np

from polaris.sim.multi_objective_optimizer import Individual, Objective, ObjectiveType
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


class TestGenerateReferencePoints(unittest.TestCase):
    """参考点生成测试。"""

    def test_single_objective(self) -> None:
        """测试单目标。"""
        points = generate_reference_points(1, 4)
        self.assertEqual(points.shape, (1, 1))

    def test_two_objectives(self) -> None:
        """测试双目标。"""
        points = generate_reference_points(2, 4)
        # n_points = C(2+4-1, 4) = 5
        self.assertEqual(points.shape, (5, 2))
        # 每行和为 1
        for row in points:
            self.assertAlmostEqual(row.sum(), 1.0, places=6)

    def test_three_objectives(self) -> None:
        """测试三目标。"""
        points = generate_reference_points(3, 4)
        # n_points = C(3+4-1, 4) = 15
        self.assertEqual(points.shape, (15, 3))
        for row in points:
            self.assertAlmostEqual(row.sum(), 1.0, places=6)

    def test_four_objectives(self) -> None:
        """测试四目标。"""
        points = generate_reference_points(4, 3)
        # n_points = C(4+3-1, 3) = 20
        self.assertEqual(points.shape, (20, 4))

    def test_normalized(self) -> None:
        """测试归一化（和为 1）。"""
        points = generate_reference_points(3, 5)
        sums = points.sum(axis=1)
        np.testing.assert_array_almost_equal(sums, 1.0, decimal=6)


class TestNormalizeObjectives(unittest.TestCase):
    """目标归一化测试。"""

    def test_empty(self) -> None:
        """测试空种群。"""
        result = normalize_objectives([], [Objective("f", ObjectiveType.MAXIMIZE)])
        self.assertEqual(result.shape, (0, 1))

    def test_min_max_normalize(self) -> None:
        """测试 min-max 归一化。"""
        objectives = [Objective("f", ObjectiveType.MINIMIZE)]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.0])),
            Individual(params=np.array([1.0]), objectives=np.array([1.0])),
            Individual(params=np.array([2.0]), objectives=np.array([2.0])),
        ]
        result = normalize_objectives(pop, objectives)
        self.assertEqual(result.shape, (3, 1))
        # 归一化后 [0, 0.5, 1]
        np.testing.assert_array_almost_equal(result[:, 0], [0.0, 0.5, 1.0])

    def test_maximize_inverted(self) -> None:
        """测试最大化目标反转。"""
        objectives = [Objective("f", ObjectiveType.MAXIMIZE)]
        pop = [
            Individual(params=np.array([0.0]), objectives=np.array([0.0])),
            Individual(params=np.array([1.0]), objectives=np.array([2.0])),
        ]
        result = normalize_objectives(pop, objectives)
        # 最大化反转后：[-0, -2]，min=-2, max=0
        # 归一化：(0-(-2))/(0-(-2))=1, (-2-(-2))/(0-(-2))=0
        # 即原值 0 → 1, 原值 2 → 0
        self.assertAlmostEqual(result[0, 0], 1.0, places=6)
        self.assertAlmostEqual(result[1, 0], 0.0, places=6)


class TestAssociateToReferencePoints(unittest.TestCase):
    """参考点关联测试。"""

    def test_basic_association(self) -> None:
        """测试基本关联。"""
        ref_points = np.array([[1.0, 0.0], [0.0, 1.0]])
        objs = np.array([[0.9, 0.1], [0.1, 0.9]])
        assoc, dist = associate_to_reference_points(objs, ref_points)
        # 第一个解应关联到第一个参考点
        self.assertEqual(assoc[0], 0)
        self.assertEqual(assoc[1], 1)
        self.assertGreater(dist[0], 0)

    def test_empty(self) -> None:
        """测试空输入。"""
        ref_points = np.array([[1.0, 0.0]])
        objs = np.zeros((0, 2))
        assoc, dist = associate_to_reference_points(objs, ref_points)
        self.assertEqual(len(assoc), 0)
        self.assertEqual(len(dist), 0)


class TestComputeNicheCounts(unittest.TestCase):
    """小生境计数测试。"""

    def test_basic(self) -> None:
        """测试基本计数。"""
        associations = np.array([0, 0, 1, 2, 0])
        counts = compute_niche_counts(associations, 3)
        self.assertEqual(counts[0], 3)
        self.assertEqual(counts[1], 1)
        self.assertEqual(counts[2], 1)

    def test_with_mask(self) -> None:
        """测试带掩码的计数。"""
        associations = np.array([0, 0, 1, 2, 0])
        mask = np.array([True, False, True, True, False])
        counts = compute_niche_counts(associations, 3, mask)
        self.assertEqual(counts[0], 1)
        self.assertEqual(counts[1], 1)
        self.assertEqual(counts[2], 1)


class TestNSGA3Config(unittest.TestCase):
    """NSGA3Config 测试。"""

    def test_defaults(self) -> None:
        """测试默认值。"""
        cfg = NSGA3Config()
        self.assertEqual(cfg.population_size, 100)
        self.assertEqual(cfg.max_generations, 200)
        self.assertIsNone(cfg.n_reference_points)

    def test_custom(self) -> None:
        """测试自定义。"""
        cfg = NSGA3Config(population_size=50, max_generations=100, seed=42)
        self.assertEqual(cfg.population_size, 50)
        self.assertEqual(cfg.seed, 42)


class TestNSGA3Optimizer(unittest.TestCase):
    """NSGA3Optimizer 类测试。"""

    def test_init(self) -> None:
        """测试初始化。"""
        objectives = [Objective("f", ObjectiveType.MAXIMIZE)]
        opt = NSGA3Optimizer(objectives, lambda p: np.array([float(p[0])]))
        self.assertEqual(len(opt.objectives), 1)
        self.assertGreater(len(opt.reference_points), 0)

    def test_optimize_single_objective(self) -> None:
        """测试单目标优化。"""
        objectives = [Objective("f", ObjectiveType.MAXIMIZE)]
        cfg = NSGA3Config(
            population_size=20,
            max_generations=10,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, lambda p: np.array([float(p[0] ** 2)]), cfg)
        result = opt.optimize(n_params=1)
        self.assertIsInstance(result, NSGA3Result)
        self.assertGreater(len(result.pareto_front), 0)

    def test_optimize_two_objectives(self) -> None:
        """测试双目标优化。"""
        n_params = 3

        def fom_fn(p: np.ndarray) -> np.ndarray:
            f1 = float(p[0])
            f2 = float(1.0 - p[0] ** 2)
            return np.array([f1, f2])

        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA3Config(
            population_size=20,
            max_generations=10,
            bounds=[(0.0, 1.0)] * n_params,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, fom_fn, cfg)
        result = opt.optimize(n_params=n_params)
        self.assertGreater(len(result.pareto_front), 0)

    def test_optimize_four_objectives(self) -> None:
        """测试四目标优化（NSGA-III 优势场景）。"""

        def fom_fn(p: np.ndarray) -> np.ndarray:
            return np.array(
                [
                    float(p[0]),
                    float(p[1]),
                    float(1.0 - p[0]),
                    float(1.0 - p[1]),
                ]
            )

        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
            Objective("f3", ObjectiveType.MAXIMIZE),
            Objective("f4", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA3Config(
            population_size=30,
            max_generations=10,
            bounds=[(0.0, 1.0)] * 2,
            seed=42,
        )
        opt = NSGA3Optimizer(objectives, fom_fn, cfg)
        result = opt.optimize(n_params=2)
        self.assertGreater(len(result.pareto_front), 0)
        self.assertGreater(len(result.reference_points), 0)

    def test_reference_points_generated(self) -> None:
        """测试参考点生成。"""
        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
            Objective("f3", ObjectiveType.MAXIMIZE),
        ]
        opt = NSGA3Optimizer(objectives, lambda p: np.array([0.0, 0.0, 0.0]))
        # 三目标用 12 划分，n_points = C(3+12-1, 12) = 91
        self.assertEqual(opt.reference_points.shape[1], 3)


class TestRunNSGA3(unittest.TestCase):
    """run_nsga3_optimization 工厂函数测试。"""

    def test_basic(self) -> None:
        """测试便捷函数。"""
        objectives = [Objective("f", ObjectiveType.MAXIMIZE)]
        cfg = NSGA3Config(
            population_size=10,
            max_generations=5,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga3_optimization(
            objectives, lambda p: np.array([float(p[0])]), 1, cfg
        )
        self.assertIsInstance(result, NSGA3Result)
        self.assertGreater(len(result.pareto_front), 0)


class TestCommercialGapReduction(unittest.TestCase):
    """商业差距缩减测试（对标 Tidy3D / Lumerical）。"""

    def test_many_objectives_support(self) -> None:
        """测试多目标支持（>3 目标）。

        NSGA-III 的核心优势场景。
        """

        def fom_fn(p: np.ndarray) -> np.ndarray:
            return np.array(
                [
                    float(p[0]),
                    float(p[1]),
                    float(p[2]),
                    float(1.0 - p[0]),
                    float(1.0 - p[1]),
                ]
            )

        objectives = [
            Objective(f"f{i}", ObjectiveType.MAXIMIZE) for i in range(5)
        ]
        cfg = NSGA3Config(
            population_size=40,
            max_generations=15,
            bounds=[(0.0, 1.0)] * 3,
            seed=42,
        )
        result = run_nsga3_optimization(objectives, fom_fn, 3, cfg)
        self.assertGreater(len(result.pareto_front), 0)
        # 5 目标应有较多参考点
        self.assertGreater(len(result.reference_points), 10)

    def test_pareto_front_nondominated(self) -> None:
        """测试 Pareto 前沿非支配性。"""
        from polaris.sim.multi_objective_optimizer import dominates

        def fom_fn(p: np.ndarray) -> np.ndarray:
            f1 = float(p[0])
            f2 = float(1.0 - p[0] ** 2)
            return np.array([f1, f2])

        objectives = [
            Objective("f1", ObjectiveType.MAXIMIZE),
            Objective("f2", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA3Config(
            population_size=30,
            max_generations=15,
            bounds=[(0.0, 1.0)],
            seed=42,
        )
        result = run_nsga3_optimization(objectives, fom_fn, 1, cfg)

        front = result.pareto_front
        for i in range(len(front)):
            for j in range(len(front)):
                if i != j:
                    self.assertFalse(
                        dominates(front[i].objectives, front[j].objectives, objectives)
                    )

    def test_reference_point_diversity(self) -> None:
        """测试参考点多样性。"""
        objectives = [
            Objective(f"f{i}", ObjectiveType.MAXIMIZE) for i in range(3)
        ]
        opt = NSGA3Optimizer(objectives, lambda p: np.array([0.0, 0.0, 0.0]))
        # 参考点应均匀分布
        points = opt.reference_points
        # 每个参考点和为 1
        sums = points.sum(axis=1)
        np.testing.assert_array_almost_equal(sums, 1.0, decimal=6)
        # 参考点应不同
        unique_points = np.unique(points, axis=0)
        self.assertEqual(len(unique_points), len(points))

    def test_reproducibility(self) -> None:
        """测试可复现性。"""
        objectives = [Objective("f", ObjectiveType.MAXIMIZE)]
        cfg = NSGA3Config(
            population_size=15,
            max_generations=5,
            bounds=[(0.0, 1.0)],
            seed=123,
        )
        r1 = run_nsga3_optimization(
            objectives, lambda p: np.array([float(p[0])]), 1, cfg
        )
        r2 = run_nsga3_optimization(
            objectives, lambda p: np.array([float(p[0])]), 1, cfg
        )
        self.assertEqual(len(r1.pareto_front), len(r2.pareto_front))

    def test_full_pipeline(self) -> None:
        """测试完整流水线。"""
        n_params = 3

        def fom_fn(p: np.ndarray) -> np.ndarray:
            return np.array([float(np.mean(p)), float(1.0 - np.std(p))])

        objectives = [
            Objective("transmission", ObjectiveType.MAXIMIZE),
            Objective("uniformity", ObjectiveType.MAXIMIZE),
        ]
        cfg = NSGA3Config(
            population_size=25,
            max_generations=10,
            bounds=[(0.0, 1.0)] * n_params,
            seed=42,
        )
        result = run_nsga3_optimization(objectives, fom_fn, n_params, cfg)

        self.assertIsInstance(result, NSGA3Result)
        self.assertGreater(len(result.pareto_front), 0)
        self.assertEqual(result.generations, 10)
        self.assertTrue(result.converged)
        self.assertGreater(len(result.reference_points), 0)


if __name__ == "__main__":
    unittest.main()
