"""P2-2 制造约束测试（第35轮 P2-2 深化）。

验证密度惩罚、投影约束、密度滤波、连通性约束。

来源: commercial_gap_analysis.md P2-2 拓扑优化制造可行性
对标: Tidy3D/Lumerical 制造约束
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.fabrication_constraints import (
    ConnectivityConstraint,
    ConstraintMetrics,
    DensityFilter,
    DensityPenalty,
    FabricationConfig,
    FabricationConstraints,
    ProjectionConstraint,
    create_fabrication_constraints,
)


class TestFabricationConfig:
    """制造约束配置测试。"""

    def test_default_config(self):
        """默认配置。"""
        cfg = FabricationConfig()
        assert cfg.min_feature_size == 2.0
        assert cfg.density_penalty_weight == 0.05
        assert cfg.projection_strength == 5.0
        assert cfg.filter_sigma == 1.5
        assert cfg.connectivity_threshold == 3
        assert cfg.max_iterations == 10

    def test_custom_config(self):
        """自定义配置。"""
        cfg = FabricationConfig(
            min_feature_size=5.0,
            density_penalty_weight=0.1,
            projection_strength=10.0,
        )
        assert cfg.min_feature_size == 5.0
        assert cfg.density_penalty_weight == 0.1
        assert cfg.projection_strength == 10.0

    def test_frozen_dataclass(self):
        """frozen dataclass。"""
        cfg = FabricationConfig()
        with pytest.raises(AttributeError):
            cfg.min_feature_size = 10.0  # type: ignore[misc]


class TestConstraintMetrics:
    """约束指标测试。"""

    def test_default_metrics(self):
        """默认指标。"""
        m = ConstraintMetrics()
        assert m.density_penalty == 0.0
        assert m.grayness == 0.0
        assert m.min_feature_violation == 0
        assert m.connectivity_violation == 0

    def test_total_violation(self):
        """总违反量。"""
        m = ConstraintMetrics(
            density_penalty=0.5,
            min_feature_violation=2,
            connectivity_violation=1,
        )
        assert m.total_violation == pytest.approx(0.5 + 0.2 + 0.1)


class TestDensityPenalty:
    """密度惩罚测试。"""

    def test_binary_zero_penalty(self):
        """二值化密度无惩罚。"""
        penalty = DensityPenalty(weight=0.05)
        density = np.zeros((10, 10))
        assert penalty.compute_penalty(density) == 0.0
        density = np.ones((10, 10))
        assert penalty.compute_penalty(density) == 0.0

    def test_gray_max_penalty(self):
        """灰度密度最大惩罚。"""
        penalty = DensityPenalty(weight=0.05)
        density = np.full((10, 10), 0.5)
        # P = 0.05 * 100 * 4 * 0.5 * 0.5 = 5.0
        assert penalty.compute_penalty(density) == pytest.approx(5.0)

    def test_gradient_at_zero(self):
        """ρ=0 处梯度。"""
        penalty = DensityPenalty(weight=0.05)
        density = np.zeros((5, 5))
        grad = penalty.compute_gradient(density)
        # dP/dρ = 0.05 * 4 * (1 - 0) = 0.2
        assert np.allclose(grad, 0.2)

    def test_gradient_at_one(self):
        """ρ=1 处梯度。"""
        penalty = DensityPenalty(weight=0.05)
        density = np.ones((5, 5))
        grad = penalty.compute_gradient(density)
        # dP/dρ = 0.05 * 4 * (1 - 2) = -0.2
        assert np.allclose(grad, -0.2)

    def test_grayness_binary(self):
        """二值化灰度为 0。"""
        penalty = DensityPenalty()
        density = np.array([[0.0, 1.0], [1.0, 0.0]])
        assert penalty.compute_grayness(density) == 0.0

    def test_grayness_half(self):
        """ρ=0.5 灰度为 1。"""
        penalty = DensityPenalty()
        density = np.full((5, 5), 0.5)
        assert penalty.compute_grayness(density) == pytest.approx(1.0)


class TestProjectionConstraint:
    """投影约束测试。"""

    def test_project_zero(self):
        """ρ=0 投影后接近 0。"""
        proj = ProjectionConstraint(strength=10.0)
        density = np.zeros((5, 5))
        projected = proj.project(density)
        assert np.all(projected < 0.1)

    def test_project_one(self):
        """ρ=1 投影后接近 1。"""
        proj = ProjectionConstraint(strength=10.0)
        density = np.ones((5, 5))
        projected = proj.project(density)
        assert np.all(projected > 0.9)

    def test_project_half(self):
        """ρ=0.5 投影后为 0.5。"""
        proj = ProjectionConstraint(strength=10.0)
        density = np.full((5, 5), 0.5)
        projected = proj.project(density)
        assert np.allclose(projected, 0.5)

    def test_high_strength_binary(self):
        """高强度投影接近二值化。"""
        proj = ProjectionConstraint(strength=100.0)
        density = np.array([0.4, 0.6])
        projected = proj.project(density)
        assert projected[0] < 0.1
        assert projected[1] > 0.9

    def test_gradient_positive(self):
        """梯度非负。"""
        proj = ProjectionConstraint(strength=5.0)
        density = np.array([0.3, 0.5, 0.7])
        grad = proj.compute_gradient(density)
        assert np.all(grad >= 0)


class TestDensityFilter:
    """密度滤波测试。"""

    def test_filter_preserves_shape(self):
        """滤波保持形状。"""
        filt = DensityFilter(sigma=1.0)
        density = np.random.rand(10, 10)
        filtered = filt.filter(density)
        assert filtered.shape == density.shape

    def test_filter_smooths(self):
        """滤波平滑密度。"""
        filt = DensityFilter(sigma=2.0)
        # 单点突变
        density = np.zeros((10, 10))
        density[5, 5] = 1.0
        filtered = filt.filter(density)
        # 滤波后中心点值降低
        assert filtered[5, 5] < 1.0
        # 周围点值升高
        assert filtered[4, 5] > 0.0

    def test_filter_zero_sigma(self):
        """σ=0 不滤波。"""
        filt = DensityFilter(sigma=0.0)
        density = np.random.rand(5, 5)
        filtered = filt.filter(density)
        assert np.allclose(filtered, density)

    def test_filter_range(self):
        """滤波结果在合理范围。"""
        filt = DensityFilter(sigma=1.5)
        density = np.random.rand(20, 20)
        filtered = filt.filter(density)
        assert filtered.min() >= density.min() - 0.1
        assert filtered.max() <= density.max() + 0.1


class TestConnectivityConstraint:
    """连通性约束测试。"""

    def test_single_region(self):
        """单一连通区域。"""
        conn = ConnectivityConstraint()
        density = np.ones((10, 10))
        assert conn.count_isolated_regions(density) == 0

    def test_two_regions(self):
        """两个分离区域。"""
        conn = ConnectivityConstraint()
        density = np.zeros((10, 21))
        density[:10, :10] = 1.0
        density[:10, 11:] = 1.0
        # 中间有间隔（列 10）→ 2 个区域 → 1 个孤立
        assert conn.count_isolated_regions(density) == 1

    def test_empty_density(self):
        """空密度无区域。"""
        conn = ConnectivityConstraint()
        density = np.zeros((10, 10))
        assert conn.count_isolated_regions(density) == 0

    def test_four_quadrants(self):
        """四象限分离。"""
        conn = ConnectivityConstraint()
        density = np.zeros((11, 11))
        density[:5, :5] = 1.0
        density[:5, 6:] = 1.0
        density[6:, :5] = 1.0
        density[6:, 6:] = 1.0
        # 4 个区域 → 3 个孤立
        assert conn.count_isolated_regions(density) == 3


class TestFabricationConstraints:
    """制造约束集合测试。"""

    def test_creation_default(self):
        """默认创建。"""
        fc = FabricationConstraints()
        assert fc.config.min_feature_size == 2.0
        assert isinstance(fc.density_penalty, DensityPenalty)
        assert isinstance(fc.projection, ProjectionConstraint)
        assert isinstance(fc.density_filter, DensityFilter)
        assert isinstance(fc.connectivity, ConnectivityConstraint)

    def test_apply_constraints(self):
        """应用约束。"""
        fc = FabricationConstraints()
        density = np.random.rand(20, 20)
        constrained = fc.apply_constraints(density)
        assert constrained.shape == density.shape
        assert constrained.min() >= 0.0
        assert constrained.max() <= 1.0

    def test_compute_total_penalty(self):
        """计算总惩罚。"""
        fc = FabricationConstraints()
        density = np.full((10, 10), 0.5)
        penalty = fc.compute_total_penalty(density)
        assert penalty > 0.0

    def test_compute_total_gradient(self):
        """计算总梯度。"""
        fc = FabricationConstraints()
        density = np.full((10, 10), 0.5)
        grad = fc.compute_total_gradient(density)
        assert grad.shape == density.shape

    def test_evaluate(self):
        """评估指标。"""
        fc = FabricationConstraints()
        density = np.full((10, 10), 0.5)
        metrics = fc.evaluate(density)
        assert isinstance(metrics, ConstraintMetrics)
        assert metrics.grayness > 0.5
        assert metrics.density_penalty > 0.0

    def test_evaluate_binary(self):
        """二值化评估。"""
        fc = FabricationConstraints()
        density = np.zeros((10, 10))
        density[:5, :5] = 1.0
        metrics = fc.evaluate(density)
        assert metrics.grayness == 0.0
        assert metrics.density_penalty == 0.0


class TestFactoryFunction:
    """工厂函数测试。"""

    def test_create_default(self):
        """默认创建。"""
        fc = create_fabrication_constraints()
        assert isinstance(fc, FabricationConstraints)

    def test_create_with_config(self):
        """带配置创建。"""
        cfg = FabricationConfig(min_feature_size=5.0)
        fc = create_fabrication_constraints(cfg)
        assert fc.config.min_feature_size == 5.0


class TestCommercialGapReduction:
    """P2-2 商业差距缩减验证。"""

    def test_density_penalty_aligned_sigmund(self):
        """密度惩罚对齐 Sigmund 2007。"""
        penalty = DensityPenalty(weight=0.05)
        # P(ρ) = 4ρ(1-ρ)，Sigmund 2007 公式
        density = np.array([[0.0, 0.25, 0.5, 0.75, 1.0]])
        expected = 4.0 * density * (1.0 - density)
        # 每个元素的惩罚 = weight * 4 * ρ * (1-ρ)
        for i, d in enumerate(density[0]):
            assert penalty.compute_penalty(np.array([[d]])) == pytest.approx(
                0.05 * expected[0, i]
            )

    def test_projection_aligned_wang2011(self):
        """投影约束对齐 Wang 2011。"""
        proj = ProjectionConstraint(strength=10.0)
        # sigmoid(β*(ρ-0.5))，Wang 2011 公式
        density = np.array([0.0, 0.5, 1.0])
        projected = proj.project(density)
        assert projected[1] == pytest.approx(0.5)  # ρ=0.5 → 0.5
        assert projected[0] < 0.1  # ρ=0 → 接近 0
        assert projected[2] > 0.9  # ρ=1 → 接近 1

    def test_filter_aligned_lazarov2011(self):
        """密度滤波对齐 Lazarov & Sigmund 2011。"""
        filt = DensityFilter(sigma=1.5)
        # 高斯滤波，Lazarov 2011 方法
        density = np.zeros((20, 20))
        density[10, 10] = 1.0
        filtered = filt.filter(density)
        # 滤波后峰值降低，周围扩散
        assert filtered[10, 10] < 1.0
        assert filtered[9, 10] > 0.0
        assert filtered[11, 10] > 0.0

    def test_connectivity_aligned_tidy3d(self):
        """连通性约束对齐 Tidy3D。"""
        conn = ConnectivityConstraint()
        # Tidy3D 检测孤立区域
        density = np.zeros((20, 20))
        density[:10, :10] = 1.0  # 主区域
        density[15, 15] = 1.0  # 孤立点
        assert conn.count_isolated_regions(density) >= 1

    def test_min_feature_size_enforced(self):
        """最小特征尺寸约束。"""
        cfg = FabricationConfig(min_feature_size=3.0)
        fc = FabricationConstraints(cfg)
        # 创建小特征（1 个像素）
        density = np.zeros((20, 20))
        density[10, 10] = 1.0
        metrics = fc.evaluate(density)
        assert metrics.min_feature_violation > 0

    def test_full_pipeline_ready(self):
        """完整制造约束流水线就绪。"""
        fc = FabricationConstraints()
        density = np.random.rand(30, 30)
        # 1. 应用约束
        constrained = fc.apply_constraints(density)
        # 2. 评估指标
        metrics = fc.evaluate(constrained)
        # 3. 计算梯度
        grad = fc.compute_total_gradient(constrained)
        assert constrained.shape == density.shape
        assert isinstance(metrics, ConstraintMetrics)
        assert grad.shape == density.shape
